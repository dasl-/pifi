"""
DPI-based RGB LED Matrix Driver for Raspberry Pi

Drop-in replacement for the hzeller rgbmatrix library, using the Pi's DPI
(Display Parallel Interface) hardware to drive HUB75 panels via GPIO.

Instead of CPU bit-banging (which consumes ~30-40% of a core), this driver
encodes the HUB75 protocol into a DPI framebuffer that the GPU scans out
automatically. CPU usage is only needed when updating frames.

Requirements:
- Raspberry Pi 3 (or 4) with vc4-kms-v3d and vc4-kms-dpi-generic overlays
- python3-kms++ (pykms) package
- Adafruit RGB Matrix HAT/Bonnet

config.txt:
    dtoverlay=vc4-kms-v3d
    dtoverlay=vc4-kms-dpi-generic,rgb888
    dtparam=hactive=128,hfp=1,hsync=1,hbp=1
    dtparam=vactive=64,vfp=1,vsync=1,vbp=1
    dtparam=clock-frequency=2000000

cmdline.txt (append to end of existing line):
    video=DPI-1:d
"""

import os
import mmap
import time
import numpy as np

try:
    import pykms
except ImportError:
    raise ImportError(
        "python3-kms++ is required. Install with: "
        "sudo apt-get install -y python3-kms++"
    )


class DpiMatrix:
    """
    DPI-driven HUB75 LED matrix controller.

    Uses 128x64 DPI framebuffer with XRGB8888 pixel format.
    Layout: 2 DPI rows per bitplane per scan address.
      - Data row (128 px): 64 panel pixels x 2 (CLK toggle)
      - Control row (128 px): latch (2 px) + OE (weighted) + padding

    With 2-bit color: 16 scans x 2 bits x 2 rows = 64 DPI rows.
    """

    # Adafruit HAT GPIO -> DPI byte/bit mapping
    # XRGB8888 memory layout: [Blue, Green, Red, X]
    # Blue byte  -> GPIO 4-11
    # Green byte -> GPIO 12-19
    # Red byte   -> GPIO 20-27

    # Data lines
    _R1_BLUE  = 1 << 1   # GPIO 5
    _G1_GREEN = 1 << 1   # GPIO 13
    _B1_BLUE  = 1 << 2   # GPIO 6
    _R2_GREEN = 1 << 0   # GPIO 12
    _G2_GREEN = 1 << 4   # GPIO 16
    _B2_RED   = 1 << 3   # GPIO 23

    # Control lines
    _OE_BLUE  = 1 << 0   # GPIO 4  (active LOW)
    _CLK_GREEN = 1 << 5  # GPIO 17
    _LAT_RED  = 1 << 1   # GPIO 21

    # Address lines
    _A_RED    = 1 << 2   # GPIO 22
    _B_RED    = 1 << 6   # GPIO 26
    _C_RED    = 1 << 7   # GPIO 27
    _D_RED    = 1 << 0   # GPIO 20

    def __init__(self, width=64, height=32, pwm_bits=2, brightness=100):
        self.panel_width = width
        self.panel_height = height
        self.pwm_bits = pwm_bits
        self._brightness = max(1, min(100, brightness))
        self.scan_rows = height // 2  # 16

        # DPI framebuffer dimensions
        # Minimum rows needed: scan_rows * pwm_bits * 2 (data + control per bitplane)
        # Plus 2 blanking rows to prevent ghost on address 0 during vblank
        self.dpi_width = 128
        self._scan_rows_needed = self.scan_rows * self.pwm_bits * 2 + 2

        # Control row layout: latch (2px) + OE + padding
        self._latch_pixels = 2
        self._oe_budget = self.dpi_width - self._latch_pixels  # 126 pixels!
        self._oe_per_bit = self._compute_oe_weights()

        # Address line LUT
        self._addr_red = np.zeros(self.scan_rows, dtype=np.uint8)
        for row in range(self.scan_rows):
            r = 0
            if row & 1: r |= self._A_RED
            if row & 2: r |= self._B_RED
            if row & 4: r |= self._C_RED
            if row & 8: r |= self._D_RED
            self._addr_red[row] = r

        # Bitmasks for each bitplane (MSB first)
        self._bitmasks = [1 << (7 - bit) for bit in range(self.pwm_bits)]

        # Pre-compute column index arrays for vectorized encoding
        self._even_cols = np.arange(0, self.dpi_width, 2)
        self._odd_cols = np.arange(1, self.dpi_width, 2)

        # Pre-compute row indices and OE column ranges per bitplane
        scans = np.arange(self.scan_rows)
        self._data_rows_per_bit = []
        self._ctrl_rows_per_bit = []
        self._oe_cols_per_bit = []
        for bit in range(self.pwm_bits):
            data_rows = scans * self.pwm_bits * 2 + bit * 2
            self._data_rows_per_bit.append(data_rows)
            self._ctrl_rows_per_bit.append(data_rows + 1)
            oe_len = self._oe_per_bit[bit]
            self._oe_cols_per_bit.append(
                np.arange(self._latch_pixels, self._latch_pixels + oe_len)
            )

        # Blanking rows: clock zeros into address 0 shift registers before vblank
        self._blank_data_row = self.scan_rows * self.pwm_bits * 2
        self._blank_ctrl_row = self._blank_data_row + 1

        # Init DRM
        self._init_drm()
        self._set_gpio_alt2()

        # Frame buffer
        self._frame_buf = np.zeros(
            (self.dpi_height, self.dpi_width, 4), dtype=np.uint8
        )

        self.clear_screen()
        print(f"DpiMatrix: {width}x{height}, {self.pwm_bits}-bit color, "
              f"DPI {self.dpi_width}x{self.dpi_height}, "
              f"OE weights: {self._oe_per_bit}")

    def _compute_oe_weights(self):
        total_weight = (1 << self.pwm_bits) - 1
        weights = []
        for bit in range(self.pwm_bits):
            w = 1 << (self.pwm_bits - 1 - bit)
            pixels = max(1, int(self._oe_budget * w / total_weight))
            weights.append(pixels)
        while sum(weights) > self._oe_budget:
            weights[weights.index(max(weights))] -= 1
        while sum(weights) < self._oe_budget:
            weights[0] += 1
        return weights

    def _init_blanking_rows(self):
        """Clock zeros into address 0's shift registers before vblank.

        During vblank all GPIOs go to 0, which enables OE on address 0.
        By blanking the shift registers, there's nothing to display.
        """
        buf = self._frame_buf
        even = self._even_cols
        odd = self._odd_cols
        bdr = self._blank_data_row
        bcr = self._blank_ctrl_row

        # Data row: clock 64 zeros at address 0 (OE disabled)
        buf[bdr, even, 0] = self._OE_BLUE
        buf[bdr, even, 1] = self._CLK_GREEN
        buf[bdr, even, 2] = 0
        buf[bdr, odd, 0] = self._OE_BLUE
        buf[bdr, odd, 1] = 0
        buf[bdr, odd, 2] = 0

        # Control row: latch the zeros, keep OE disabled
        buf[bcr, :, 0] = self._OE_BLUE
        buf[bcr, :, 1] = 0
        buf[bcr, :, 2] = 0
        buf[bcr, :, 3] = 0
        buf[bcr, 0, 2] = self._LAT_RED
        buf[bcr, 1, 2] = 0

    def _init_drm(self):
        self._card = pykms.Card("/dev/dri/card0")
        self._connector = None
        for conn in self._card.connectors:
            if "DPI" in conn.fullname:
                self._connector = conn
                break
        if not self._connector:
            raise RuntimeError("No DPI connector found")

        mode = self._connector.get_default_mode()
        if mode.hdisplay != self.dpi_width:
            raise RuntimeError(
                f"DPI hactive is {mode.hdisplay}, expected {self.dpi_width}"
            )
        if mode.vdisplay < self._scan_rows_needed:
            raise RuntimeError(
                f"DPI vactive is {mode.vdisplay}, need at least "
                f"{self._scan_rows_needed}. Update config.txt: "
                f"dtparam=vactive={self._scan_rows_needed}"
            )
        self.dpi_height = mode.vdisplay

        self._crtc = self._connector.get_possible_crtcs()[0]
        self._fb = pykms.DumbFramebuffer(
            self._card, self.dpi_width, self.dpi_height,
            pykms.PixelFormat.XRGB8888
        )
        self._stride = self._fb.stride(0)
        self._fb_size = self._fb.size(0)
        self._mmap = mmap.mmap(
            self._fb.fd(0), self._fb_size,
            mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE
        )
        self._crtc.set_mode(self._connector, self._fb, mode)
        time.sleep(0.3)

    def _set_gpio_alt2(self):
        os.system("for pin in $(seq 4 27); do pinctrl set $pin a2; done")

    def display_frame(self, frame):
        if hasattr(frame, 'shape'):
            print(f"[DPI] frame shape={frame.shape}, dtype={frame.dtype}, "
              f"min={frame.min()}, max={frame.max()}")
        else:
            print(f"[DPI] frame type={type(frame)}")

        if hasattr(frame, 'astype'):
            img = frame.astype(np.uint8)
        else:
            img = np.array(frame, dtype=np.uint8)

        # Handle size mismatch
        h, w = img.shape[:2]
        if h > self.panel_height:
            img = img[:self.panel_height]
        if w > self.panel_width:
            img = img[:, :self.panel_width]
        if h < self.panel_height or w < self.panel_width:
            padded = np.zeros(
                (self.panel_height, self.panel_width, 3), dtype=np.uint8
            )
            padded[:img.shape[0], :img.shape[1]] = img
            img = padded

        if self._brightness < 100:
            img = (img * (self._brightness / 100.0)).astype(np.uint8)

        self._encode_image(img)
        self._flush_frame()

    def _encode_image(self, img):
        buf = self._frame_buf
        addr = self._addr_red          # (scan_rows,)
        top = img[:self.scan_rows]     # (16, 64, 3)
        bot = img[self.scan_rows:]     # (16, 64, 3)
        even = self._even_cols         # (64,)
        odd = self._odd_cols           # (64,)

        for bit in range(self.pwm_bits):
            bitmask = self._bitmasks[bit]
            dr = self._data_rows_per_bit[bit]   # (16,) data row indices
            cr = self._ctrl_rows_per_bit[bit]   # (16,) control row indices
            oe_cols = self._oe_cols_per_bit[bit]

            # Test which pixels have this bit set -> uint8 0/1, shape (16, 64)
            top_r = ((top[:, :, 0] & bitmask) != 0).astype(np.uint8)
            top_g = ((top[:, :, 1] & bitmask) != 0).astype(np.uint8)
            top_b = ((top[:, :, 2] & bitmask) != 0).astype(np.uint8)
            bot_r = ((bot[:, :, 0] & bitmask) != 0).astype(np.uint8)
            bot_g = ((bot[:, :, 1] & bitmask) != 0).astype(np.uint8)
            bot_b = ((bot[:, :, 2] & bitmask) != 0).astype(np.uint8)

            # Map to GPIO bit positions in each DPI byte — (16, 64) uint8
            blue_d = top_r * self._R1_BLUE | top_b * self._B1_BLUE
            green_d = top_g * self._G1_GREEN | bot_r * self._R2_GREEN | bot_g * self._G2_GREEN
            red_d = bot_b * self._B2_RED

            # === DATA ROWS: even pixels (CLK high), odd pixels (CLK low) ===
            ar = addr[:, None]  # (16, 1) for broadcasting

            buf[dr[:, None], even, 0] = self._OE_BLUE | blue_d
            buf[dr[:, None], even, 1] = self._CLK_GREEN | green_d
            buf[dr[:, None], even, 2] = ar | red_d

            buf[dr[:, None], odd, 0] = self._OE_BLUE | blue_d
            buf[dr[:, None], odd, 1] = green_d
            buf[dr[:, None], odd, 2] = ar | red_d

            # === CONTROL ROWS: latch + OE ===
            buf[cr, :, 0] = self._OE_BLUE
            buf[cr, :, 1] = 0
            buf[cr, :, 2] = ar
            buf[cr, :, 3] = 0

            buf[cr, 0, 2] = addr | self._LAT_RED
            buf[cr, 1, 2] = addr

            buf[cr[:, None], oe_cols, 0] = 0  # OE active

            buf[cr, self.dpi_width - 1, 0] = self._OE_BLUE

    def _flush_frame(self):
        flat = self._frame_buf.tobytes()
        if self._stride == self.dpi_width * 4:
            self._mmap[0:len(flat)] = flat
        else:
            src_stride = self.dpi_width * 4
            for y in range(self.dpi_height):
                so = y * src_stride
                do = y * self._stride
                self._mmap[do:do + src_stride] = flat[so:so + src_stride]

    def set_brightness(self, brightness):
        self._brightness = max(1, min(100, brightness))

    def clear_screen(self):
        self._frame_buf[:, :, 0] = self._OE_BLUE
        self._frame_buf[:, :, 1] = 0
        self._frame_buf[:, :, 2] = 0
        self._frame_buf[:, :, 3] = 0
        self._init_blanking_rows()
        self._flush_frame()

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, value):
        self.set_brightness(value)

    @property
    def width(self):
        return self.panel_width

    @property
    def height(self):
        return self.panel_height


class DriverDpiMatrix:
    """Drop-in replacement for pifi's DriverRgbMatrix."""

    def __init__(self, clear_screen=True):
        try:
            from pifi.config import Config
            width = Config.get_or_throw('leds.display_width')
            height = Config.get_or_throw('leds.display_height')
            brightness = Config.get('leds.brightness', 100)
            pwm_bits = Config.get('dpi_matrix.pwm_bits', 2)
        except ImportError:
            width = 64
            height = 32
            brightness = 100
            pwm_bits = 2

        brightness = 100
        print("Initialized with", width, height, pwm_bits, brightness)
        self.__matrix = DpiMatrix(
            width=width, height=height,
            pwm_bits=pwm_bits, brightness=brightness,
        )
        self.__width = self.__matrix.width
        self.__height = self.__matrix.height
        if clear_screen:
            self.clear_screen()

    def display_frame(self, frame):
        self.__matrix.display_frame(frame)

    def set_brightness(self, brightness):
        self.__matrix.set_brightness(brightness)

    def clear_screen(self):
        self.__matrix.clear_screen()

    def can_multiple_driver_instances_coexist(self):
        return False


# =============================================================================
# Test helpers
# =============================================================================
def _solid(w, h, color):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :] = color
    return img

def _split(w, h):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:h//2, :, 0] = 255
    img[h//2:, :, 2] = 255
    return img

def _gradient(w, h):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    q = w // 4
    img[:, :q, 0] = 0
    img[:, q:q*2, 0] = 85
    img[:, q*2:q*3, 0] = 170
    img[:, q*3:, 0] = 255
    return img

def _stripes(w, h):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for x in range(w):
        if x % 6 < 2:   img[:, x, 0] = 255
        elif x % 6 < 4: img[:, x, 1] = 255
        else:            img[:, x, 2] = 255
    return img

def _checker(w, h):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        for x in range(w):
            if (x + y) % 2 == 0:
                img[y, x] = [255, 255, 255]
    return img

def _colorbars(w, h):
    colors = [
        [255,255,255],[255,255,0],[0,255,255],[0,255,0],
        [255,0,255],[255,0,0],[0,0,255],[0,0,0],
    ]
    img = np.zeros((h, w, 3), dtype=np.uint8)
    bw = w // len(colors)
    for i, c in enumerate(colors):
        x0 = i * bw
        x1 = x0 + bw if i < len(colors) - 1 else w
        img[:, x0:x1] = c
    return img


if __name__ == "__main__":
    print("=" * 60)
    print("DPI Matrix Driver Test — 128x64 mode, full 64 columns")
    print("=" * 60)

    matrix = DpiMatrix(width=64, height=32, pwm_bits=2, brightness=100)
    W, H = matrix.width, matrix.height

    for name, fn in [
        ("Solid RED",    lambda: _solid(W, H, [255,0,0])),
        ("Solid GREEN",  lambda: _solid(W, H, [0,255,0])),
        ("Solid BLUE",   lambda: _solid(W, H, [0,0,255])),
        ("WHITE",        lambda: _solid(W, H, [255,255,255])),
        ("Top R/Bot B",  lambda: _split(W, H)),
        ("Gradient",     lambda: _gradient(W, H)),
        ("RGB Stripes",  lambda: _stripes(W, H)),
        ("Checkerboard", lambda: _checker(W, H)),
        ("Color Bars",   lambda: _colorbars(W, H)),
    ]:
        print(f"\n--- {name} ---")
        matrix.display_frame(fn())
        time.sleep(3)

    print("\n--- Scrolling ---")
    for offset in range(W * 2):
        img = np.zeros((H, W, 3), dtype=np.uint8)
        for x in range(W):
            v = int(255 * ((x + offset) % W) / W)
            img[:, x, 0] = v
            img[:, x, 1] = 255 - v
        matrix.display_frame(img)
        time.sleep(0.05)

    matrix.clear_screen()
    print("Done!")
