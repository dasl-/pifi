import numpy as np
import random
import math

from pifi.config import Config
from pifi.screensaver.screensaver import Screensaver


class TestPrint(Screensaver):
    """
    Camera test print — animated broadcast calibration patterns.

    Color bars, gradient ramps, geometric registration marks, and
    line frequency tests laid out in zones. A technical/industrial
    aesthetic that slowly animates and cycles.
    """

    # Classic SMPTE-ish color bars (full brightness)
    COLOR_BARS = [
        (191, 191, 191),  # white/gray
        (191, 191, 0),    # yellow
        (0, 191, 191),    # cyan
        (0, 191, 0),      # green
        (191, 0, 191),    # magenta
        (191, 0, 0),      # red
        (0, 0, 191),      # blue
    ]

    def __init__(self, led_frame_player=None):
        super().__init__(led_frame_player)

        self.__width = Config.get_or_throw('leds.display_width')
        self.__height = Config.get_or_throw('leds.display_height')

    def _setup(self):
        self.__time = 0.0

        # Pre-compute coordinate grids
        y = np.arange(self.__height, dtype=np.float64)
        x = np.arange(self.__width, dtype=np.float64)
        self.__gx, self.__gy = np.meshgrid(x, y)

        # Randomize layout: which zones go where
        self.__layout = random.choice(['standard', 'split', 'quad'])

        # Animation phase offsets
        self.__bar_scroll_speed = random.uniform(0.3, 0.8) * random.choice([-1, 1])
        self.__gradient_speed = random.uniform(0.2, 0.5)
        self.__pulse_speed = random.uniform(1.0, 2.0)
        self.__crosshair_center = (
            self.__width * random.uniform(0.3, 0.7),
            self.__height * random.uniform(0.3, 0.7),
        )

    def _tick(self, tick):
        self.__time += 0.015
        t = self.__time

        frame = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)
        w, h = self.__width, self.__height

        if self.__layout == 'standard':
            # Top 60%: color bars, bottom 20%: gradient, bottom 20%: line test
            bar_h = int(h * 0.55)
            grad_h = int(h * 0.22)

            self.__draw_color_bars(frame, 0, 0, w, bar_h, t)
            self.__draw_gradient_ramp(frame, 0, bar_h, w, grad_h, t)
            self.__draw_line_test(frame, 0, bar_h + grad_h, w, h - bar_h - grad_h, t)

        elif self.__layout == 'split':
            # Left half: color bars + grayscale, right half: geometry + gradient
            mid = w // 2
            bar_h = int(h * 0.65)

            self.__draw_color_bars(frame, 0, 0, mid, bar_h, t)
            self.__draw_grayscale_steps(frame, 0, bar_h, mid, h - bar_h, t)
            self.__draw_gradient_ramp(frame, mid, 0, w - mid, int(h * 0.4), t)
            self.__draw_line_test(frame, mid, int(h * 0.4), w - mid, h - int(h * 0.4), t)

        else:  # quad
            mid_x = w // 2
            mid_y = h // 2

            self.__draw_color_bars(frame, 0, 0, mid_x, mid_y, t)
            self.__draw_gradient_ramp(frame, mid_x, 0, w - mid_x, mid_y, t)
            self.__draw_grayscale_steps(frame, 0, mid_y, mid_x, h - mid_y, t)
            self.__draw_line_test(frame, mid_x, mid_y, w - mid_x, h - mid_y, t)

        # Overlay: crosshair / registration marks
        self.__draw_crosshair(frame, t)

        self._led_frame_player.play_frame(frame)

    def __draw_color_bars(self, frame, x0, y0, w, h, t):
        """Scrolling SMPTE-style color bars."""
        if w <= 0 or h <= 0:
            return

        region_x = self.__gx[y0:y0+h, x0:x0+w]
        scroll = t * self.__bar_scroll_speed * 5

        # Which bar each pixel falls into (7 bars, scrolling)
        bar_width = max(w / 7, 1)
        bar_idx = ((region_x - x0 + scroll) / bar_width).astype(np.int32) % 7

        for i, color in enumerate(self.COLOR_BARS):
            mask = bar_idx == i
            for c in range(3):
                frame[y0:y0+h, x0:x0+w, c][mask] = color[c]

    def __draw_gradient_ramp(self, frame, x0, y0, w, h, t):
        """Horizontal gradient that shifts hue over time."""
        if w <= 0 or h <= 0:
            return

        region_x = self.__gx[y0:y0+h, x0:x0+w]
        frac = (region_x - x0) / max(w - 1, 1)

        # Hue shifts over time
        hue_offset = t * self.__gradient_speed
        hue = (frac + hue_offset) % 1.0

        # HSV to RGB (vectorized)
        h6 = hue * 6.0
        hi = h6.astype(np.int32) % 6
        f = h6 - np.floor(h6)
        q = 1.0 - f
        t_val = f

        r = np.zeros_like(hue)
        g = np.zeros_like(hue)
        b = np.zeros_like(hue)

        for i in range(6):
            m = hi == i
            if i == 0:
                r[m] = 1.0; g[m] = t_val[m]; b[m] = 0.0
            elif i == 1:
                r[m] = q[m]; g[m] = 1.0; b[m] = 0.0
            elif i == 2:
                r[m] = 0.0; g[m] = 1.0; b[m] = t_val[m]
            elif i == 3:
                r[m] = 0.0; g[m] = q[m]; b[m] = 1.0
            elif i == 4:
                r[m] = t_val[m]; g[m] = 0.0; b[m] = 1.0
            else:
                r[m] = 1.0; g[m] = 0.0; b[m] = q[m]

        frame[y0:y0+h, x0:x0+w, 0] = (r * 220).astype(np.uint8)
        frame[y0:y0+h, x0:x0+w, 1] = (g * 220).astype(np.uint8)
        frame[y0:y0+h, x0:x0+w, 2] = (b * 220).astype(np.uint8)

    def __draw_grayscale_steps(self, frame, x0, y0, w, h, t):
        """Stepping grayscale blocks that pulse."""
        if w <= 0 or h <= 0:
            return

        num_steps = min(8, w)
        if num_steps <= 0:
            return

        region_x = self.__gx[y0:y0+h, x0:x0+w]
        step_idx = ((region_x - x0) / max(w, 1) * num_steps).astype(np.int32)
        step_idx = np.clip(step_idx, 0, num_steps - 1)

        # Base grayscale value per step
        pulse = 0.85 + 0.15 * math.sin(t * self.__pulse_speed)
        for i in range(num_steps):
            val = int((i / max(num_steps - 1, 1)) * 255 * pulse)
            mask = step_idx == i
            frame[y0:y0+h, x0:x0+w][mask] = val

    def __draw_line_test(self, frame, x0, y0, w, h, t):
        """Alternating line frequency test patterns."""
        if w <= 0 or h <= 0:
            return

        region_x = self.__gx[y0:y0+h, x0:x0+w]

        # Divide into frequency bands
        num_bands = min(4, w // 3)
        if num_bands <= 0:
            num_bands = 1

        band_w = w / num_bands
        band_idx = ((region_x - x0) / band_w).astype(np.int32)
        band_idx = np.clip(band_idx, 0, num_bands - 1)

        # Scroll offset
        scroll = t * 2.0

        for i in range(num_bands):
            freq = (i + 1) * 2  # increasing frequency per band
            pattern = ((region_x + scroll) * freq / w * math.pi)
            on = np.sin(pattern) > 0
            mask = (band_idx == i) & on

            brightness = 180
            frame[y0:y0+h, x0:x0+w, 0][mask] = brightness
            frame[y0:y0+h, x0:x0+w, 1][mask] = brightness
            frame[y0:y0+h, x0:x0+w, 2][mask] = brightness

    def __draw_crosshair(self, frame, t):
        """Pulsing crosshair / registration mark overlay."""
        cx, cy = self.__crosshair_center
        w, h = self.__width, self.__height

        # Slowly drift the center
        cx = cx + math.sin(t * 0.2) * w * 0.1
        cy = cy + math.cos(t * 0.15) * h * 0.1

        pulse = 0.5 + 0.5 * math.sin(t * self.__pulse_speed)
        brightness = int(200 * pulse)

        # Horizontal line
        iy = int(round(cy))
        if 0 <= iy < h:
            arm = max(2, w // 6)
            x_start = max(0, int(cx) - arm)
            x_end = min(w, int(cx) + arm + 1)
            # Thin crosshair - only draw if brightness is meaningful
            if brightness > 30:
                existing = frame[iy, x_start:x_end].astype(np.int16)
                overlay = np.full_like(existing, brightness)
                frame[iy, x_start:x_end] = np.clip(
                    np.maximum(existing, overlay), 0, 255
                ).astype(np.uint8)

        # Vertical line
        ix = int(round(cx))
        if 0 <= ix < w:
            arm = max(2, h // 4)
            y_start = max(0, int(cy) - arm)
            y_end = min(h, int(cy) + arm + 1)
            if brightness > 30:
                existing = frame[y_start:y_end, ix].astype(np.int16)
                overlay = np.full_like(existing, brightness)
                frame[y_start:y_end, ix] = np.clip(
                    np.maximum(existing, overlay), 0, 255
                ).astype(np.uint8)

        # Small circle at center
        r = max(1, min(w, h) // 8)
        dist = np.sqrt((self.__gx - cx) ** 2 + (self.__gy - cy) ** 2)
        ring = (np.abs(dist - r) < 0.8)
        if brightness > 30:
            frame[:, :, 0][ring] = np.maximum(frame[:, :, 0][ring], brightness)
            frame[:, :, 1][ring] = np.maximum(frame[:, :, 1][ring], brightness)
            frame[:, :, 2][ring] = np.maximum(frame[:, :, 2][ring], brightness)

    @classmethod
    def get_id(cls) -> str:
        return 'test_print'

    @classmethod
    def get_name(cls) -> str:
        return 'Test Print'

    @classmethod
    def get_description(cls) -> str:
        return 'Broadcast calibration patterns'
