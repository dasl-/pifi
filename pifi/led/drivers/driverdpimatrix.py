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
    dtparam=hactive=256,hfp=0,hsync=1,hbp=0
    dtparam=vactive=256,vfp=1,vsync=1,vbp=1
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

    Uses 256xN DPI framebuffer with XRGB8888 pixel format.
    Layout: 2 DPI rows per bitplane per scan address.
      - Data row (256 px): 64 panel pixels x 2 (CLK toggle) + 128 px padding
      - Control row (256 px): settle + latch + OE + zero-clock + zero-latch

    The extra width allows control rows to clock zeros into the shift
    register and latch them after the OE period. This clears the output
    register before hblank, preventing ghost on address 0 (since DPI
    forces all GPIOs to 0 during blanking, enabling OE on address 0).
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
        # Width is 256 (not 128) to allow zeroing shift registers before hblank.
        # Minimum rows needed: scan_rows * pwm_bits * 2 (data + control per bitplane)
        # Plus 2 blanking rows to prevent ghost on address 0 during vblank
        self.dpi_width = 256
        self._data_clk_pixels = self.panel_width * 2  # 128: real panel data region
        self._scan_rows_needed = self.scan_rows * self.pwm_bits * 2 + 2

        # Control row layout:
        #   settle (2px) + latch (2px) + OE (weighted) +
        #   zero-clock (128px) + zero-latch (2px) + last-pixel-safety (1px)
        # The zero-clock + zero-latch clears the output register before hblank.
        self._settle_pixels = 2
        self._latch_pixels = 2
        self._zero_clk_pixels = self.panel_width * 2  # 128: clock 64 zeros
        self._zero_lat_pixels = 2
        self._oe_budget = (self.dpi_width - self._settle_pixels - self._latch_pixels
                           - self._zero_clk_pixels - self._zero_lat_pixels - 1)
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

        # Scan order: process address 0 last so its shift registers hold real
        # data for the fewest hblank periods before being blanked
        self._scan_order = np.array([*range(1, self.scan_rows), 0])

        # Bitmasks for each bitplane (MSB first)
        self._bitmasks = [1 << (7 - bit) for bit in range(self.pwm_bits)]

        # Pre-compute column index arrays for vectorized encoding
        # Only covers the first 128 DPI pixels (64 panel pixels × 2 CLK toggle)
        self._even_cols = np.arange(0, self._data_clk_pixels, 2)
        self._odd_cols = np.arange(1, self._data_clk_pixels, 2)

        # Pre-compute row indices, OE columns, and zero-clocking columns per bitplane
        scans = np.arange(self.scan_rows)
        self._data_rows_per_bit = []
        self._ctrl_rows_per_bit = []
        self._oe_cols_per_bit = []
        self._zero_even_cols_per_bit = []
        self._zero_odd_cols_per_bit = []
        self._zero_lat_col_per_bit = []
        for bit in range(self.pwm_bits):
            data_rows = scans * self.pwm_bits * 2 + bit * 2
            self._data_rows_per_bit.append(data_rows)
            self._ctrl_rows_per_bit.append(data_rows + 1)
            oe_len = self._oe_per_bit[bit]
            oe_start = self._settle_pixels + self._latch_pixels
            self._oe_cols_per_bit.append(
                np.arange(oe_start, oe_start + oe_len)
            )
            # Zero-clocking region: starts right after OE period
            zero_start = oe_start + oe_len
            self._zero_even_cols_per_bit.append(
                np.arange(zero_start, zero_start + self._zero_clk_pixels, 2)
            )
            self._zero_odd_cols_per_bit.append(
                np.arange(zero_start + 1, zero_start + self._zero_clk_pixels, 2)
            )
            self._zero_lat_col_per_bit.append(zero_start + self._zero_clk_pixels)

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

        # Control row: settle + latch the zeros, keep OE disabled
        s = self._settle_pixels
        buf[bcr, :, 0] = self._OE_BLUE
        buf[bcr, :, 1] = 0
        buf[bcr, :, 2] = 0
        buf[bcr, :, 3] = 0
        buf[bcr, s, 2] = self._LAT_RED
        buf[bcr, s + 1, 2] = 0

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
        order = self._scan_order
        addr = self._addr_red[order]           # (16,) reordered addresses
        top = img[order]                       # (16, 64, 3) reordered top rows
        bot = img[order + self.scan_rows]      # (16, 64, 3) reordered bottom rows
        even = self._even_cols         # (64,)
        odd = self._odd_cols           # (64,)

        for bit in range(self.pwm_bits):
            bitmask = self._bitmasks[bit]
            dr = self._data_rows_per_bit[bit]   # (16,) data row indices
            cr = self._ctrl_rows_per_bit[bit]   # (16,) control row indices
            oe_cols = self._oe_cols_per_bit[bit]
            zero_even = self._zero_even_cols_per_bit[bit]
            zero_odd = self._zero_odd_cols_per_bit[bit]
            zero_lat = self._zero_lat_col_per_bit[bit]

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

            # === DATA ROWS: first 128 px clock real data, rest is padding ===
            ar = addr[:, None]  # (16, 1) for broadcasting

            buf[dr[:, None], even, 0] = self._OE_BLUE | blue_d
            buf[dr[:, None], even, 1] = self._CLK_GREEN | green_d
            buf[dr[:, None], even, 2] = ar | red_d

            buf[dr[:, None], odd, 0] = self._OE_BLUE | blue_d
            buf[dr[:, None], odd, 1] = green_d
            buf[dr[:, None], odd, 2] = ar | red_d

            # === CONTROL ROWS: settle + latch + OE + zero-clock + zero-latch ===
            # Default: OE disabled, address set, all other signals low
            buf[cr, :, 0] = self._OE_BLUE
            buf[cr, :, 1] = 0
            buf[cr, :, 2] = ar
            buf[cr, :, 3] = 0

            # Pixels 0-1: address settling (address set, LAT low, OE disabled)
            # — lets address lines stabilize after hblank before LAT fires

            # Pixels 2-3: LAT pulse to latch real data
            s = self._settle_pixels
            buf[cr, s, 2] = addr | self._LAT_RED   # LAT high
            buf[cr, s + 1, 2] = addr                 # LAT low

            # OE active for weighted duration (displays real data)
            buf[cr[:, None], oe_cols, 0] = 0

            # Clock zeros into shift register (OE disabled, CLK toggle, no data)
            buf[cr[:, None], zero_even, 1] = self._CLK_GREEN

            # Latch zeros — clears output register before hblank
            buf[cr, zero_lat, 2] = addr | self._LAT_RED
            buf[cr, zero_lat + 1, 2] = addr

            # Last pixel: ensure OE disabled (held during hblank)
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


def _ghost_diagnostic(matrix):
    """Systematic ghost line diagnostic tests.

    Displays patterns to isolate the source of address 0 ghost.
    For each test, observe the bottom row (addr 0 top half)
    and middle row (addr 0 bottom half).
    """
    W, H = matrix.width, matrix.height
    scan = H // 2  # 16

    tests = []

    # Test 1: All black — is there a baseline ghost?
    def t1():
        return np.zeros((H, W, 3), dtype=np.uint8)
    tests.append(("1. ALL BLACK (any light on bottom/mid = baseline ghost)", t1))

    # Test 2: All white EXCEPT address 0 rows (img[0] and img[16] = black)
    # Ghost from other rows leaking into address 0?
    def t2():
        img = np.full((H, W, 3), 255, dtype=np.uint8)
        img[0, :, :] = 0      # addr 0 top half
        img[scan, :, :] = 0   # addr 0 bottom half
        return img
    tests.append(("2. ALL WHITE except addr 0 = BLACK (ghost = leak from others)", t2))

    # Test 3: ONLY address 0 rows are white, rest black
    # Does address 0 display correctly by itself?
    def t3():
        img = np.zeros((H, W, 3), dtype=np.uint8)
        img[0, :, :] = 255    # addr 0 top half
        img[scan, :, :] = 255 # addr 0 bottom half
        return img
    tests.append(("3. ONLY addr 0 = WHITE, rest BLACK (addr 0 displays correctly?)", t3))

    # Test 4: Each address gets a unique color (addr 0 = black)
    # What color does the ghost show? Tells us which address leaks.
    def t4():
        img = np.zeros((H, W, 3), dtype=np.uint8)
        colors = [
            [0,0,0],       # addr 0 = black
            [255,0,0],     # addr 1 = red
            [0,255,0],     # addr 2 = green
            [0,0,255],     # addr 3 = blue
            [255,255,0],   # addr 4 = yellow
            [0,255,255],   # addr 5 = cyan
            [255,0,255],   # addr 6 = magenta
            [255,128,0],   # addr 7 = orange
            [128,0,255],   # addr 8 = purple
            [255,255,255], # addr 9 = white
            [128,128,0],   # addr 10 = olive
            [0,128,128],   # addr 11 = teal
            [128,0,0],     # addr 12 = dark red
            [0,128,0],     # addr 13 = dark green
            [0,0,128],     # addr 14 = dark blue
            [128,128,128], # addr 15 = gray
        ]
        for addr in range(scan):
            img[addr, :, :] = colors[addr]        # top half
            img[addr + scan, :, :] = colors[addr]  # bottom half
        return img
    tests.append(("4. UNIQUE COLOR per address, addr 0 = BLACK (which color leaks?)", t4))

    # Test 5: Only adjacent rows lit (addr 1 = white, rest black)
    # Does proximity matter?
    def t5():
        img = np.zeros((H, W, 3), dtype=np.uint8)
        img[1, :, :] = 255
        img[1 + scan, :, :] = 255
        return img
    tests.append(("5. ONLY addr 1 = WHITE (does neighbor leak into addr 0?)", t5))

    # Test 6: Only far row lit (addr 8 = white, rest black)
    def t6():
        img = np.zeros((H, W, 3), dtype=np.uint8)
        img[8, :, :] = 255
        img[8 + scan, :, :] = 255
        return img
    tests.append(("6. ONLY addr 8 = WHITE (does distant row leak into addr 0?)", t6))

    for name, fn in tests:
        print(f"\n{'='*60}")
        print(name)
        print("Press Enter to continue...")
        matrix.display_frame(fn())
        input()

    matrix.clear_screen()
    print("\nDone!")


if __name__ == "__main__":
    import sys

    matrix = DpiMatrix(width=64, height=32, pwm_bits=4, brightness=100)
    W, H = matrix.width, matrix.height

    if len(sys.argv) > 1 and sys.argv[1] == 'ghost':
        _ghost_diagnostic(matrix)
    else:
        print("=" * 60)
        print("DPI Matrix Driver Test")
        print("=" * 60)

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
