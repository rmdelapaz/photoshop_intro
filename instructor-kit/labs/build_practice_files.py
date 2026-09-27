#!/usr/bin/env python3
"""Generate every synthetic practice file for the Photoshop course labs.

Each lab README (labs/module-N/README.md) has a "Practice file specs" section; this
script implements those specs one function per file, grouped by module, and writes
the results into labs/module-N/practice/. Everything is drawn from scratch (no
photographs, no stock), so the output is safe to hand to enrolled learners.

Dependencies
    Python 3.9+
    Pillow >= 10.1   (PIL: Image, ImageDraw, ImageFilter, ImageFont, ImageCms, ImageEnhance)
    numpy  >= 1.20
    Fonts: DejaVu Sans / DejaVu Sans Bold if installed (Linux: fonts-dejavu-core);
           otherwise a common system sans (Arial / Helvetica) or Pillow's built-in font.

Usage (from instructor-kit/, or from anywhere; paths resolve from this file)
    python3 labs/build_practice_files.py              # build all modules
    python3 labs/build_practice_files.py --module 4   # build one module (repeatable)

Output is deterministic (fixed seeds per file) and idempotent: running it again
overwrites the same files with identical pixels. Each written file is printed.
"""

from __future__ import annotations

import argparse
import math
import sys
import zlib
from collections import namedtuple
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageEnhance, ImageFilter, ImageFont

LABS = Path(__file__).resolve().parent
KIT = LABS.parent
F32 = np.float32


def _fixed_srgb_icc() -> bytes:
    """LittleCMS's built-in sRGB profile, with its creation timestamp pinned (and the
    optional profile ID cleared) so that regenerated files are byte-identical."""
    icc = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    icc[24:36] = bytes.fromhex("07ea00010001000000000000")      # 2026-01-01 00:00:00
    icc[84:100] = bytes(16)
    return bytes(icc)


SRGB_ICC = _fixed_srgb_icc()
WRITTEN: list[Path] = []

# --------------------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------------------


def rng(name: str) -> np.random.Generator:
    """A fixed, per-file random generator (seed derived from the file's name)."""
    return np.random.default_rng(zlib.crc32(name.encode("utf-8")))


def hexc(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    return tuple(float(x) + (float(y) - float(x)) * t for x, y in zip(a, b))


def out_path(module: int, name: str, folder: str = "practice") -> Path:
    p = LABS / f"module-{module}" / folder / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _record(p: Path) -> None:
    WRITTEN.append(p)
    try:
        rel = p.relative_to(KIT)
    except ValueError:
        rel = p
    print(f"  wrote {rel}  ({p.stat().st_size / 1024:,.0f} KB)")


def to_u8(a: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(a), 0, 255).astype(np.uint8)


def save_jpg(img, module, name, quality=90, icc=True, dpi=72, subsampling=None):
    """Save an RGB float array / PIL image as a baseline JPEG (no EXIF)."""
    if isinstance(img, np.ndarray):
        img = Image.fromarray(to_u8(img))
    p = out_path(module, name)
    kw = dict(quality=quality, dpi=(dpi, dpi), optimize=True)
    if subsampling is not None:
        kw["subsampling"] = subsampling
    if icc:
        kw["icc_profile"] = SRGB_ICC
    img.save(p, "JPEG", **kw)
    _record(p)


def save_png(img, module, name, icc=True, dpi=72, folder="practice"):
    if isinstance(img, np.ndarray):
        img = Image.fromarray(to_u8(img))
    p = out_path(module, name, folder)
    kw = dict(optimize=True, dpi=(dpi, dpi))
    if icc:
        kw["icc_profile"] = SRGB_ICC
    img.save(p, "PNG", **kw)
    _record(p)


def save_txt(text: str, module: int, name: str) -> None:
    p = out_path(module, name)
    p.write_text(text, encoding="utf-8", newline="\n")
    _record(p)


# ---- fonts ---------------------------------------------------------------------------

_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF",
    "/usr/local/share/fonts", "/Library/Fonts", "/System/Library/Fonts/Supplemental",
    "C:/Windows/Fonts",
]


@lru_cache(maxsize=None)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf", "Helvetica-Bold.ttf"]
             if bold else ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf", "Helvetica.ttf"])
    for n in names:
        for cand in [n] + [f"{d}/{n}" for d in _FONT_DIRS]:
            try:
                return ImageFont.truetype(cand, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


# ---- gradients and noise -------------------------------------------------------------

def _interp(t: np.ndarray, stops) -> np.ndarray:
    pos = [s[0] for s in stops]
    cols = np.array([s[1] if not isinstance(s[1], str) else hexc(s[1]) for s in stops], float)
    return np.stack([np.interp(t, pos, cols[:, c]) for c in range(3)], -1).astype(F32)


def vgrad(w, h, stops, y0=0.0, y1=None):
    """Vertical gradient (h, w, 3). stops = [(t, color), ...] with t in 0..1 over y0..y1."""
    y1 = h if y1 is None else y1
    t = np.clip((np.arange(h, dtype=F32) + 0.5 - y0) / (y1 - y0), 0, 1)
    col = _interp(t, stops)
    return np.ascontiguousarray(np.broadcast_to(col[:, None, :], (h, w, 3)))


def hgrad(w, h, stops, x0=0.0, x1=None):
    x1 = w if x1 is None else x1
    t = np.clip((np.arange(w, dtype=F32) + 0.5 - x0) / (x1 - x0), 0, 1)
    col = _interp(t, stops)
    return np.ascontiguousarray(np.broadcast_to(col[None, :, :], (h, w, 3)))


def solid(w, h, color):
    c = hexc(color) if isinstance(color, str) else color
    return np.ones((h, w, 3), F32) * np.array(c, F32)


def coords(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    return xx + 0.5, yy + 0.5


def add_noise(img, sigma, r, mono=False, sigma_map=None):
    """Per-pixel Gaussian noise; mono=True adds the same value to R, G and B."""
    h, w = img.shape[:2]
    n = r.standard_normal((h, w, 1) if mono else (h, w, 3), dtype=F32) * F32(sigma)
    if sigma_map is not None:
        n = n * sigma_map[..., None]
    img += n
    np.clip(img, 0, 255, out=img)
    return img


def add_uniform_noise(img, amp, r):
    img += r.integers(-amp, amp + 1, img.shape).astype(F32)
    np.clip(img, 0, 255, out=img)
    return img


def smooth_wave(xs, base, amp, parts, phase=0.0):
    """Sum of sines normalised to +/- amp. parts = [(period, weight, phase), ...]."""
    y = np.zeros_like(xs, dtype=float)
    tw = sum(p[1] for p in parts)
    for period, weight, ph in parts:
        y += weight * np.sin(2 * np.pi * xs / period + ph + phase)
    return base + amp * y / tw


def blur_img(img: np.ndarray, radius: float) -> np.ndarray:
    return np.asarray(Image.fromarray(to_u8(img)).filter(ImageFilter.GaussianBlur(radius)), F32)


def quad_bezier(p0, p1, p2, n=64):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = (np.array(p, float) for p in (p0, p1, p2))
    pts = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
    return [tuple(p) for p in pts]


def convex_hull(points):
    pts = sorted(set((float(x), float(y)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def rand_color_near(r, c, spread):
    return tuple(int(np.clip(v + r.integers(-spread, spread + 1), 0, 255)) for v in c)


# --------------------------------------------------------------------------------------
# Supersampled drawing: Canvas -> Mask (alpha only) or Layer (RGBA), positioned anywhere
# --------------------------------------------------------------------------------------

Mask = namedtuple("Mask", "x y a")            # a: (h, w) float 0..1, top-left at (x, y)
Layer = namedtuple("Layer", "x y rgb a")      # rgb: (h, w, 3) float, a: (h, w) float 0..1


class Canvas:
    """A supersampled drawing surface in global pixel coordinates.

    box = (x0, y0, x1, y1) is the region covered (plus `pad` on every side, so later
    blurs are not clipped). mode "L" draws coverage/alpha; mode "RGBA" draws colored
    shapes (later shapes replace earlier ones). Downsampling with a box filter gives
    clean anti-aliasing.
    """

    def __init__(self, box, ss=3, mode="L", pad=0, resample=Image.BOX):
        self.resample = resample
        x0, y0, x1, y1 = box
        self.x0 = int(math.floor(x0 - pad))
        self.y0 = int(math.floor(y0 - pad))
        self.w = int(math.ceil(x1 + pad)) - self.x0
        self.h = int(math.ceil(y1 + pad)) - self.y0
        self.ss = ss
        self.mode = mode
        self.im = Image.new(mode, (self.w * ss, self.h * ss), 0 if mode == "L" else (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    # coordinate helpers
    def P(self, x, y):
        return ((x - self.x0) * self.ss, (y - self.y0) * self.ss)

    def B(self, x0, y0, x1, y1):
        a, b = self.P(x0, y0)
        c, d = self.P(x1, y1)
        return [min(a, c), min(b, d), max(a, c), max(b, d)]

    def _f(self, fill):
        if self.mode == "L":
            return int(round(fill if fill is not None else 255))
        if isinstance(fill, str):
            fill = hexc(fill)
        fill = tuple(int(round(v)) for v in fill)
        return fill if len(fill) == 4 else fill + (255,)

    # primitives
    def ellipse(self, cx, cy, rx, ry, fill=255):
        self.d.ellipse(self.B(cx - rx, cy - ry, cx + rx, cy + ry), fill=self._f(fill))

    def circle(self, cx, cy, r, fill=255):
        self.ellipse(cx, cy, r, r, fill)

    def rect(self, x0, y0, x1, y1, fill=255):
        self.d.rectangle(self.B(x0, y0, x1, y1), fill=self._f(fill))

    def rrect(self, x0, y0, x1, y1, r, fill=255):
        self.d.rounded_rectangle(self.B(x0, y0, x1, y1), radius=r * self.ss, fill=self._f(fill))

    def poly(self, pts, fill=255):
        self.d.polygon([self.P(x, y) for x, y in pts], fill=self._f(fill))

    def pieslice(self, cx, cy, r, a0, a1, fill=255):
        self.d.pieslice(self.B(cx - r, cy - r, cx + r, cy + r), a0, a1, fill=self._f(fill))

    def line(self, pts, width, fill=255, round_caps=False):
        w = max(1, int(round(width * self.ss)))
        self.d.line([self.P(x, y) for x, y in pts], fill=self._f(fill), width=w, joint="curve")
        if round_caps:
            for x, y in (pts[0], pts[-1]):
                self.circle(x, y, width / 2, fill)

    def text(self, x, y, s, fnt_size, bold=False, fill=255, anchor="la", **kw):
        f = font(int(round(fnt_size * self.ss)), bold)
        self.d.text(self.P(x, y), s, font=f, fill=self._f(fill), anchor=anchor, **kw)

    # results
    def _down(self):
        im = self.im
        if self.ss > 1:
            im = im.resize((self.w, self.h), self.resample)
        return im

    def mask(self, blur=0.0) -> Mask:
        im = self._down()
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        return Mask(self.x0, self.y0, np.asarray(im, F32) / 255.0)

    def layer(self, blur=0.0) -> Layer:
        im = self._down()  # Pillow premultiplies RGBA when resampling
        if blur:
            im = im.convert("RGBa").filter(ImageFilter.GaussianBlur(blur)).convert("RGBA")
        a = np.asarray(im, F32)
        return Layer(self.x0, self.y0, a[..., :3].copy(), a[..., 3] / 255.0)


def _slices(base_shape, x, y, shp):
    H, W = base_shape[:2]
    h, w = shp[:2]
    bx0, by0 = max(x, 0), max(y, 0)
    bx1, by1 = min(x + w, W), min(y + h, H)
    if bx0 >= bx1 or by0 >= by1:
        return None
    return ((slice(by0, by1), slice(bx0, bx1)),
            (slice(by0 - y, by1 - y), slice(bx0 - x, bx1 - x)))


def _color_for(color, base, m, sb, sm):
    if isinstance(color, np.ndarray) and color.ndim == 3:
        if color.shape[:2] == base.shape[:2]:
            return color[sb]
        return color[sm]
    c = hexc(color) if isinstance(color, str) else color
    return np.array(c, F32)


def paint(base, m: Mask, color, opacity=1.0):
    """Composite a flat color (or a color array) through a mask."""
    s = _slices(base.shape, m.x, m.y, m.a.shape)
    if s is None:
        return
    sb, sm = s
    a = (m.a[sm] * opacity)[..., None]
    base[sb] = base[sb] * (1 - a) + _color_for(color, base, m, sb, sm) * a


def darken(base, m: Mask, amount):
    """Multiply toward black: amount 0.6 = '60 % black' shadow."""
    s = _slices(base.shape, m.x, m.y, m.a.shape)
    if s is None:
        return
    sb, sm = s
    base[sb] = base[sb] * (1 - (m.a[sm] * amount)[..., None])


def over(base, L: Layer, opacity=1.0):
    s = _slices(base.shape, L.x, L.y, L.a.shape)
    if s is None:
        return
    sb, sm = s
    a = (L.a[sm] * opacity)[..., None]
    base[sb] = base[sb] * (1 - a) + L.rgb[sm] * a


def full_mask(m: Mask, w, h) -> np.ndarray:
    out = np.zeros((h, w), F32)
    s = _slices((h, w), m.x, m.y, m.a.shape)
    if s:
        out[s[0]] = m.a[s[1]]
    return out


def erode(a: np.ndarray, px: int) -> np.ndarray:
    im = Image.fromarray(to_u8(a * 255)).filter(ImageFilter.MinFilter(2 * px + 1))
    return np.asarray(im, F32) / 255.0


def soft_blob(c: Canvas, r, cx, cy, width, height, n=(3, 5), fill=255):
    """A cloud/leaf-like blob made of overlapping ellipses inside width x height."""
    for _ in range(int(r.integers(n[0], n[1] + 1))):
        ex = cx + r.uniform(-0.3, 0.3) * width
        ey = cy + r.uniform(-0.25, 0.2) * height
        c.ellipse(ex, ey, r.uniform(0.25, 0.45) * width, r.uniform(0.3, 0.5) * height, fill)


# ======================================================================================
# MODULE 0: Your First Win
# ======================================================================================

def m0_tilted_horizon():
    name = "l01-tilted-horizon.jpg"
    r = rng(name)
    W, H = 2400, 1600
    PX, PY = 120, 100                    # ~10 % larger canvas, cropped back after rotating
    CW, CH = W + 2 * PX, H + 2 * PY
    hz = 820 + PY
    img = np.empty((CH, CW, 3), F32)
    img[:hz] = vgrad(CW, hz, [(0, (70, 110, 170)), (1, (190, 205, 225))])
    img[hz:] = vgrad(CW, CH - hz, [(0, (40, 80, 120)), (1, (15, 35, 60))])

    sx, sy = 1650 + PX, 560 + PY
    c = Canvas((sx - 70, sy - 70, sx + 70, sy + 70), pad=90)
    c.circle(sx, sy, 70)
    paint(img, c.mask(blur=25), (250, 235, 190))

    # wave glints, denser near the horizon
    for i in range(40):
        y = hz + 6 + (CH - hz - 20) * r.random() ** 2.4
        x = r.uniform(0, CW)
        ln = r.uniform(60, 300) * (0.6 + 0.8 * (y - hz) / (CH - hz))
        th = r.uniform(1, 3)
        c = Canvas((x - ln / 2, y - 3, x + ln / 2, y + 3), pad=3)
        c.rrect(x - ln / 2, y - th / 2, x + ln / 2, y + th / 2, th / 2)
        paint(img, c.mask(blur=0.6), (90, 130, 170), r.uniform(0.4, 0.6))

    # sailboat on the horizon (level reference)
    bx = 700 + PX
    c = Canvas((bx - 60, hz - 90, bx + 60, hz + 10))
    c.poly([(bx - 45, hz - 12), (bx + 45, hz - 12), (bx + 34, hz + 2), (bx - 36, hz + 2)])
    c.poly([(bx - 2, hz - 74), (bx - 2, hz - 15), (bx - 40, hz - 15)])          # main sail
    c.poly([(bx + 3, hz - 66), (bx + 3, hz - 15), (bx + 30, hz - 15)])          # jib
    paint(img, c.mask(), (25, 30, 40))

    # flaw 1: 4 degrees clockwise, then crop back to size
    im = Image.fromarray(to_u8(img)).rotate(-4, resample=Image.BICUBIC, expand=False)
    img = np.asarray(im.crop((PX, PY, PX + W, PY + H)), F32).copy()
    # flaw 2: dark and flat
    img = 20 + img * 0.55
    # flaw 3: thumb in the frame
    c = Canvas((60 - 190, 1580 - 150, 60 + 190, 1580 + 150), ss=1, pad=130)
    c.ellipse(60, 1580, 190, 150)
    paint(img, c.mask(blur=40), (35, 25, 20))
    add_noise(img, 3, r)
    save_jpg(img, 0, name)


def m0_too_bright():
    name = "l01-too-bright.jpg"
    r = rng(name)
    W, H = 2400, 1600
    hz = int(H * 0.45)
    img = np.empty((H, W, 3), F32)
    img[:hz] = vgrad(W, hz, [(0, (175, 205, 235)), (1, (225, 235, 245))])
    img[hz:] = vgrad(W, H - hz, [(0, (95, 150, 70)), (1, (60, 110, 45))])

    for i in range(6):
        cw = r.uniform(200, 450)
        cx, cy = 200 + i * 380 + r.uniform(-60, 60), r.uniform(90, hz - 200)
        c = Canvas((cx - cw, cy - cw / 2, cx + cw, cy + cw / 2), ss=2, pad=60)
        soft_blob(c, r, cx, cy, cw, cw * 0.45)
        paint(img, c.mask(blur=30), (255, 255, 255), 0.9)

    # grass + flowers on one supersampled layer
    c = Canvas((0, hz - 20, W, H), ss=2, mode="RGBA")
    g0, g1 = (50, 100, 40), (120, 170, 80)
    for _ in range(2000):
        x, y = r.uniform(0, W), hz + (H - hz) * r.random() ** 0.8
        ln = r.uniform(8, 25) * (0.7 + 0.6 * (y - hz) / (H - hz))
        ang = math.radians(r.uniform(-25, 25))
        col = lerp(g0, g1, r.random())
        c.line([(x, y), (x + ln * math.sin(ang), y - ln * math.cos(ang))], 2, col)
    flowers = [(200, 60, 60), (230, 200, 60), (140, 80, 170), (240, 240, 240)]
    for _ in range(120):
        t = r.random() ** 1.7                                  # denser near the horizon
        y = hz + 20 + (H - hz - 40) * t
        x = r.uniform(10, W - 10)
        rad = 6 + 10 * t + r.uniform(-1.5, 1.5)
        col = flowers[int(r.integers(0, 4))]
        c.circle(x, y, max(6, min(16, rad)), col)
        c.circle(x, y, max(2, rad * 0.3), (200, 170, 60) if col != (230, 200, 60) else (190, 140, 40))
    over(img, c.layer())

    # tree, canopy crossing the horizon
    c = Canvas((1600, 500, 2060, 1010), ss=3)
    c.rect(1780, 740, 1820, 1000)
    paint(img, c.mask(), (80, 60, 40))
    c = Canvas((1600, 500, 2060, 1010), ss=3)
    for cx, cy, rad in [(1800, 700, 150), (1715, 770, 120), (1890, 765, 115)]:
        c.circle(cx, cy, rad)
    paint(img, c.mask(), (50, 100, 50))

    # the flaw: washed out
    img = img * 0.55 + 255 * 0.45
    im = ImageEnhance.Color(Image.fromarray(to_u8(img))).enhance(0.65)
    img = np.asarray(im, F32).copy()
    add_noise(img, 2, r)
    save_jpg(img, 0, name)


# ======================================================================================
# MODULE 1: Foundations
# ======================================================================================

def m1_washed_sky():
    name = "l02-washed-sky.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = vgrad(W, H, [(0, (205, 220, 235)), (1, (240, 243, 247))], 0, 1000)

    for i in range(7):
        cw = r.uniform(250, 600)
        cx, cy = 150 + i * 330 + r.uniform(-60, 60), r.uniform(120, 680)
        c = Canvas((cx - cw, cy - cw / 2, cx + cw, cy + cw / 2), ss=2, pad=80)
        soft_blob(c, r, cx, cy, cw, cw * 0.4)
        paint(img, c.mask(blur=35), (248, 249, 252))

    xs = np.arange(0, W + 9, 8)
    back = smooth_wave(xs, 900, 70, [(1700, 0.6, 0.8), (730, 0.4, 2.1)])
    front = smooth_wave(xs, 1050, 90, [(2100, 0.6, 2.5), (900, 0.4, 0.3)])
    land = np.zeros((H, W), F32)
    for ridge, cols in ((back, ((55, 85, 50), (48, 76, 44))), (front, ((40, 70, 38), (30, 55, 30)))):
        c = Canvas((0, 0, W, H), ss=2)
        c.poly(list(zip(xs, ridge)) + [(W + 8, H), (0, H)])
        m = c.mask()
        paint(img, m, vgrad(W, H, [(0, cols[0]), (1, cols[1])], 800, H))
        land = np.maximum(land, m.a)

    yf = float(np.interp(1650, xs, front))
    c = Canvas((1500, yf - 400, 1800, yf + 20), ss=3)
    c.rect(1635, yf - 180, 1665, yf + 15)
    trunk = c.mask()
    paint(img, trunk, (50, 40, 30))
    c = Canvas((1500, yf - 400, 1800, yf + 20), ss=3)
    for cx, cy, rad in [(1650, yf - 235, 105), (1588, yf - 190, 85), (1714, yf - 195, 92)]:
        c.circle(cx, cy, rad)
    canopy = c.mask()
    paint(img, canopy, (35, 60, 35))
    land = np.maximum(land, full_mask(trunk, W, H))
    land = np.maximum(land, full_mask(canopy, W, H))

    add_noise(img, 1, r, sigma_map=2 + 4 * land)       # sky sigma 2, land sigma 6
    save_jpg(img, 1, name)


def m1_spotlight_object():
    name = "l02-spotlight-object.jpg"
    r = rng(name)
    W, H = 2000, 1500
    img = solid(W, H, (120, 110, 100))
    c = Canvas((0, 0, W, H), ss=1, mode="RGBA")
    for _ in range(600):
        col = rand_color_near(r, (120, 110, 100), 25)
        x, y, s = r.uniform(0, W), r.uniform(0, H), r.uniform(10, 80)
        if r.random() < 0.5:
            c.rect(x, y, x + s, y + s * r.uniform(0.5, 1.5), col)
        else:
            c.circle(x, y, s / 2, col)
    over(img, c.layer())
    img = blur_img(img, 6)

    ty = int(H * 0.75)
    img[ty:] = vgrad(W, H - ty, [(0, (98, 77, 60)), (1, (84, 65, 51))])
    for _ in range(70):
        y0 = r.uniform(ty + 4, H)
        dv = r.uniform(-12, 12)
        col = tuple(np.clip(np.array((90, 70, 55)) + dv, 0, 255))
        xs = np.linspace(-20, W + 20, 60)
        ys = y0 + 3 * np.sin(xs / r.uniform(150, 400) + r.uniform(0, 6))
        c = Canvas((0, y0 - 6, W, y0 + 6), ss=2)
        c.line(list(zip(xs, ys)), r.uniform(1, 2.5))
        paint(img, c.mask(), col, 0.8)

    box = (700, 480, 1300, 1250)
    c = Canvas(box, ss=3, pad=40)
    c.ellipse(1000, 1210, 250, 22)                              # contact shadow on the table
    darken(img, c.mask(blur=14), 0.45)
    c = Canvas(box, ss=3, pad=40)
    c.ellipse(1000, 940, 210, 260)
    c.rect(930, 560, 1070, 720)
    c.ellipse(1000, 560, 88, 20)
    vase = c.mask()
    tc = np.array((175, 95, 60), F32)
    shade = hgrad(W, H, [(0, tc * 1.02), (0.5, tc), (1, tc * 0.72)], 790, 1210)
    paint(img, vase, shade)
    c = Canvas(box, ss=2, pad=40)
    c.rect(845, 540, 905, 1180)
    hl = c.mask(blur=20)
    paint(img, Mask(hl.x, hl.y, hl.a * vase.a), tuple(tc + 30))
    c = Canvas(box, ss=3, pad=40)
    c.ellipse(1000, 560, 60, 11)
    paint(img, c.mask(), (120, 62, 40))                         # dark opening of the neck

    img = 40 + img * 0.7                                        # the flaw: all equally dull
    add_noise(img, 3, r)
    save_jpg(img, 1, name)


def m1_subject_busy_bg():
    name = "l03-subject-busy-bg.jpg"
    r = rng(name)
    W, H = 2000, 1500
    img = solid(W, H, (150, 150, 150))
    c = Canvas((0, 0, W, H), ss=2, mode="RGBA")
    for _ in range(900):
        if r.random() < 0.6:
            hsv = (int(r.integers(0, 256)), int(r.integers(150, 256)), int(r.integers(120, 256)))
        else:
            hsv = (int(r.integers(0, 256)), int(r.integers(0, 50)), int(r.integers(40, 240)))
        col = Image.new("HSV", (1, 1), hsv).convert("RGB").getpixel((0, 0))
        x, y, s = r.uniform(-40, W), r.uniform(-40, H), r.uniform(15, 120)
        k = r.random()
        if k < 0.4:
            c.rect(x, y, x + s, y + s * r.uniform(0.4, 1.4), col)
        elif k < 0.75:
            c.circle(x, y, s / 2, col)
        else:
            a = r.uniform(0, math.pi)
            c.line([(x, y), (x + s * math.cos(a), y + s * math.sin(a))], r.uniform(6, 14), col)
    over(img, c.layer())

    box = (700, 450, 1500, 1150)
    c = Canvas(box, ss=3)
    c.rrect(740, 500, 1260, 1100, 40)
    body = c.mask().a
    c = Canvas(box, ss=3)
    c.circle(1330, 800, 150)
    outer = c.mask().a
    c = Canvas(box, ss=3)
    c.circle(1330, 800, 90)
    ring = np.clip(outer - c.mask().a, 0, 1)
    c = Canvas(box, ss=3)
    c.ellipse(1000, 530, 238, 38)
    rim = c.mask().a * body
    c = Canvas(box, ss=2, pad=0)
    c.rect(795, 545, 845, 1060)
    hl = c.mask(blur=15).a * body

    x0, y0 = c.x0, c.y0
    h, w = body.shape
    red = np.array((200, 40, 45), F32)
    xs = np.arange(w, dtype=F32) + x0
    shade = np.interp(xs, [740, 880, 1100, 1260], [0.78, 1.05, 0.95, 0.72]).astype(F32)
    rgb = np.ones((h, w, 3), F32) * red * np.where(body > 0, 1.0, 0.85)[..., None]
    rgb *= np.where(body[..., None] > 0, shade[None, :, None], 1.0)
    rgb = rgb * (1 - rim[..., None]) + np.array((120, 20, 25), F32) * rim[..., None]
    rgb = rgb * (1 - 0.35 * hl[..., None]) + 255 * 0.35 * hl[..., None]
    alpha = np.maximum(body, ring)
    alpha = np.asarray(Image.fromarray(to_u8(alpha * 255)).filter(ImageFilter.GaussianBlur(1.5)), F32) / 255
    over(img, Layer(x0, y0, rgb, alpha))
    add_noise(img, 3, r)
    save_jpg(img, 1, name)


def m1_calm_background():
    name = "l03-calm-background.jpg"
    r = rng(name)
    W, H = 2000, 1500
    X, Y = coords(W, H)
    d = np.hypot(X - 1000, Y - 650)
    t = np.clip(d / d.max(), 0, 1)[..., None]
    img = np.array((205, 215, 225), F32) * (1 - t) + np.array((120, 135, 150), F32) * t
    fy = np.clip((Y - 1140) / 120, 0, 1)
    fy = fy * fy * (3 - 2 * fy)
    img -= 20 * fy[..., None]
    add_noise(img, 1.5, r)
    save_jpg(img, 1, name)


def m1_fuzzy_subject():
    name = "l03-fuzzy-subject.jpg"
    r = rng(name)
    W, H = 2000, 1500
    img = vgrad(W, H, [(0, (70, 130, 60)), (1, (40, 90, 40))])
    c = Canvas((0, 0, W, H), ss=1, mode="RGBA")
    for _ in range(150):
        x, y = r.uniform(0, W), r.uniform(0, H)
        base = img[int(min(y, H - 1)), int(min(x, W - 1))]
        c.ellipse(x, y, r.uniform(20, 80), r.uniform(20, 80), rand_color_near(r, base, 20))
    over(img, c.layer())
    img = blur_img(img, 12)

    c = Canvas((900, 700, 1200, H), ss=3)
    c.line(quad_bezier((1000, 710), (1010, 1150), (1080, H + 20)), 14, round_caps=True)
    paint(img, c.mask(), (120, 150, 90))

    cx, cy = 1000, 650
    c = Canvas((cx - 350, cy - 350, cx + 350, cy + 350), ss=4)
    for _ in range(700):
        a = r.uniform(0, 2 * math.pi)
        ln = r.uniform(260, 330)
        ca, sa = math.cos(a), math.sin(a)
        tx, ty = cx + ln * ca, cy + ln * sa
        al = r.uniform(0.5, 0.85) * 255
        c.line([(cx + 50 * ca, cy + 50 * sa), (tx, ty)], 1, al)
        k = int(r.integers(4, 7))
        for j in range(k):                          # parachute tuft
            b = a + math.radians(-45 + 90 * j / (k - 1))
            tl = r.uniform(3, 4)
            c.line([(tx, ty), (tx + tl * math.cos(b), ty + tl * math.sin(b))], 1, al)
    paint(img, c.mask(blur=0.8), (245, 245, 240))

    c = Canvas((cx - 70, cy - 70, cx + 70, cy + 70), ss=3)
    c.circle(cx, cy, 60)
    paint(img, c.mask(), (200, 190, 160))
    c = Canvas((cx - 70, cy - 70, cx + 70, cy + 70), ss=3)
    for _ in range(90):
        rr, aa = 52 * math.sqrt(r.random()), r.uniform(0, 2 * math.pi)
        c.circle(cx + rr * math.cos(aa), cy + rr * math.sin(aa), r.uniform(2, 4))
    paint(img, c.mask(), (160, 145, 110), 0.7)
    add_noise(img, 2, r)
    save_jpg(img, 1, name)


def m1_other_scene():
    name = "l03-other-scene.jpg"
    r = rng(name)
    W, H = 2000, 1500
    img = vgrad(W, H, [(0, (250, 170, 90)), (0.55, (200, 90, 80)), (1, (80, 50, 90))], 0, 1050)
    X, Y = coords(W, 1100)
    d = np.hypot(X - 1400, Y - 980)
    glow = np.clip(1 - d / 600, 0, 1) ** 2 * 0.45
    img[:1100] = img[:1100] * (1 - glow[..., None]) + np.array((255, 190, 120), F32) * glow[..., None]
    c = Canvas((1300, 880, 1500, 1080), pad=50)
    c.circle(1400, 980, 90)
    paint(img, c.mask(blur=20), (255, 220, 150))
    xs = np.arange(0, W + 9, 8)
    ridge = 1050 - 40 * np.sin(np.pi * xs / W) + smooth_wave(xs, 0, 10, [(500, 1, 0.4), (230, 0.5, 1.1)])
    c = Canvas((0, 900, W, H), ss=2)
    c.poly(list(zip(xs, ridge)) + [(W + 8, H), (0, H)])
    paint(img, c.mask(), (40, 30, 45))
    add_noise(img, 2, r)
    save_jpg(img, 1, name)


def m1_dusty_sky():
    name = "l04-dusty-sky.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = vgrad(W, H, [(0, (95, 145, 205)), (1, (185, 210, 235))], 0, 1100)
    for i in range(5):
        cw = r.uniform(300, 520)
        cx, cy = 200 + i * 480 + r.uniform(-60, 60), r.uniform(150, 800)
        c = Canvas((cx - cw, cy - cw / 2, cx + cw, cy + cw / 2), ss=2, pad=60)
        soft_blob(c, r, cx, cy, cw, cw * 0.35)
        paint(img, c.mask(blur=30), (245, 248, 252), 0.75)

    # building: straight roofline at y = 1100
    img[1100:1450, 0:1500] = vgrad(1500, 350, [(0, (176, 156, 131)), (1, (160, 141, 117))])
    img[1100:1120, 0:1500] = (120, 105, 90)
    for i in range(8):
        wx = 1500 / 8 * (i + 0.5)
        img[1250:1390, int(wx - 50):int(wx + 50)] = (60, 70, 85)
        img[1386:1394, int(wx - 56):int(wx + 56)] = (140, 124, 104)       # sills
    img[1450:] = (80, 80, 85)

    # 28 dust spots in the sky only
    c = Canvas((0, 0, W, 1100), ss=3)
    placed = []
    while len(placed) < 28:
        x, y = r.uniform(30, W - 30), r.uniform(30, 1060)
        if abs(x - 1533) < 60 and y > 650 or math.hypot(x - 700, y - 380) < 90:
            continue
        if any(math.hypot(x - px, y - py) < 120 for px, py in placed):
            continue
        rad = r.uniform(4, 5) if len(placed) < 3 else r.uniform(4, 12)
        c.circle(x, y, rad, r.uniform(0.35, 0.7) * 255)
        placed.append((x, y))
    paint(img, c.mask(blur=1.5), (60, 60, 70))

    # bird
    c = Canvas((640, 340, 760, 420), ss=4)
    c.line([(665, 374), (676, 363), (689, 364), (700, 381), (711, 364), (724, 363), (735, 374)], 5)
    c.ellipse(700, 381, 5, 4)
    paint(img, c.mask(), (35, 35, 40))

    # utility pole, crossbar and a sagging wire to the top-left corner
    c = Canvas((0, 500, 1650, 1470), ss=3)
    c.rect(1520, 700, 1546, 1460)
    c.rect(1453, 740, 1613, 754)
    c.line(quad_bezier((1455, 747), (720, 720), (0, 520), 120), 4)
    paint(img, c.mask(), (55, 45, 40))
    add_noise(img, 3, r)
    save_jpg(img, 1, name)


def m1_photobomb():
    name = "l04-photobomb.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = np.empty((H, W, 3), F32)
    img[:640] = vgrad(W, 640, [(0, (120, 170, 220)), (1, (200, 220, 235))])
    img[640:900] = vgrad(W, 260, [(0, (40, 110, 150)), (1, (70, 140, 170))])
    img[900:] = vgrad(W, 700, [(0, (220, 202, 165)), (1, (210, 188, 148))])
    for _ in range(70):
        y = 646 + 250 * r.random() ** 1.3
        x, ln = r.uniform(0, W), r.uniform(60, 280)
        c = Canvas((x - ln / 2, y - 3, x + ln / 2, y + 3), pad=2)
        c.rrect(x - ln / 2, y - 1, x + ln / 2, y + 1, 1)
        paint(img, c.mask(blur=0.5), (170, 210, 225), r.uniform(0.3, 0.6))
    # sand texture before objects (total sand noise ~10)
    sand = img[900:]
    n = r.standard_normal((700, W, 1), dtype=F32) * 8 + r.standard_normal((700, W, 3), dtype=F32) * 5
    sand += n
    for _ in range(22):
        y0 = r.uniform(930, H)
        xs = np.linspace(-20, W + 20, 80)
        ys = y0 + 6 * np.sin(xs / r.uniform(90, 220) + r.uniform(0, 6))
        c = Canvas((0, y0 - 10, W, y0 + 10), ss=2)
        c.line(list(zip(xs, ys)), r.uniform(2, 4))
        paint(img, c.mask(blur=1.2), (170, 150, 112), r.uniform(0.25, 0.45))

    # umbrella (keep)
    c = Canvas((600, 1180, 1200, 1300), ss=2, pad=40)
    c.ellipse(900, 1238, 240, 36)
    darken(img, c.mask(blur=16), 0.35)
    c = Canvas((780, 880, 820, 1230), ss=3)
    c.rect(794, 900, 806, 1220)
    paint(img, c.mask(), (235, 235, 230))
    c = Canvas((570, 670, 1030, 910), ss=3, mode="RGBA")
    for k in range(8):
        col = (210, 45, 50) if k % 2 == 0 else (245, 240, 232)
        c.pieslice(800, 900, 220, 180 + k * 22.5, 180 + (k + 1) * 22.5 + 0.3, col)
    c.circle(800, 680, 9, (235, 235, 230))
    over(img, c.layer())

    # trash can (remove)
    c = Canvas((1760, 1260, 2060, 1320), ss=2, pad=30)
    c.poly([(1925, 1295), (1925, 1270), (2040, 1300), (2010, 1310)])
    darken(img, c.mask(blur=10), 0.4)
    c = Canvas((1760, 1050, 1940, 1300), ss=3)
    c.rect(1775, 1065, 1925, 1295)
    paint(img, c.mask(), hgrad(W, H, [(0, (120, 125, 130)), (1, (92, 96, 101))], 1775, 1925))
    c = Canvas((1760, 1050, 1940, 1300), ss=3)
    c.rrect(1765, 1055, 1935, 1081, 6)
    paint(img, c.mask(), (78, 82, 88))

    # photobomber (remove), cropped by the right edge
    c = Canvas((2200, 700, W, 1215), ss=3)
    c.circle(2320, 760, 45)
    c.rrect(2255, 810, 2385, 1195, 40)
    c.rrect(2360, 840, 2440, 1080, 30)                          # arm running off frame
    paint(img, c.mask(), (60, 50, 70))
    c = Canvas((2200, 1180, W, 1230), ss=2, pad=20)
    c.ellipse(2330, 1200, 90, 14)
    darken(img, c.mask(blur=8), 0.35)
    add_noise(img, 3, r)
    save_jpg(img, 1, name)


# ======================================================================================
# MODULE 2: Light & Color       (JPEG quality 92, no chroma subsampling)
# ======================================================================================

def _gray_card(img, x0, y0, x1, y1):
    w = (x1 - x0) / 3
    for k, v in enumerate((8, 118, 248)):
        img[y0:y1, int(round(x0 + k * w)):int(round(x0 + (k + 1) * w))] = v


def m2_flat_cast():
    name = "l05-flat-cast.jpg"
    r = rng(name)
    W, H = 2400, 1600
    hz = int(H * 0.55)
    img = np.empty((H, W, 3), F32)
    img[:hz] = vgrad(W, hz, [(0, (70, 130, 200)), (1, (200, 222, 240))])
    img[hz:] = vgrad(W, H - hz, [(0, (92, 150, 78)), (0.18, (70, 130, 60)), (1, (70, 130, 60))])
    add_noise(img[hz:], 6, r, mono=True)
    c = Canvas((1780, 190, 1920, 330), pad=20)
    c.circle(1850, 260, 70)
    paint(img, c.mask(blur=6), (250, 245, 225))

    c = Canvas((440, 460, 1160, 1090), ss=3)
    c.rect(500, 700, 1100, 1080)
    paint(img, c.mask(), (240, 240, 240))
    img[700:730, 500:1100] = 12                                         # shadow under the eave
    c = Canvas((440, 460, 1160, 1090), ss=3)
    c.poly([(460, 700), (1140, 700), (800, 470)])
    paint(img, c.mask(), (60, 60, 60))
    img[880:1080, 760:860] = 90
    for wx in (580, 920):
        img[790:900, wx:wx + 110] = (40, 55, 70)
    img[H - 140:] = 128
    _gray_card(img, 1700, 1180, 2200, 1420)
    c = Canvas((1700, 1120, 2200, 1175), ss=3)
    c.text(1950, 1150, "GRAY CARD", 36, bold=True, anchor="mm")
    paint(img, c.mask(), (25, 25, 25))

    img[..., 0] = img[..., 0] * 1.10 + 12
    img[..., 1] = img[..., 1] * 1.00 + 2
    img[..., 2] = img[..., 2] * 0.72
    np.clip(img, 0, 255, out=img)
    img = 45 + img * 0.60
    add_noise(img, 3, r, mono=True)
    save_jpg(img, 2, name, quality=92, subsampling=0)


def m2_green_indoor():
    name = "l05-green-indoor.jpg"
    r = rng(name)
    W, H = 2400, 1600
    ty = int(H * 0.6)
    img = np.empty((H, W, 3), F32)
    X, Y = coords(W, ty)
    vig = 1 - 0.06 * np.hypot((X - 1400) / 1400, (Y - 400) / 700) ** 2
    img[:ty] = solid(W, ty, (232, 230, 224)) * vig[..., None]
    img[150:750, 1500:2150] = 255
    img[170:730, 1520:2130] = vgrad(610, 560, [(0, (150, 190, 230)), (1, (215, 230, 245))])
    img[170:730, 1815:1835] = 255                                       # mullion
    tbl = vgrad(W, H - ty, [(0, (158, 106, 64)), (1, (142, 94, 56))])
    for y in range(8, H - ty, 18):
        tbl[y:y + 2] *= 0.85 + 0.05 * math.sin(y)
    img[ty:] = tbl
    add_noise(img[ty:], 8, r, mono=True)
    img[ty:ty + 5] *= 0.75

    for cx, cy, rx, ry, amt in ((720, 1085, 150, 22, 0.35), (1180, 1135, 240, 26, 0.3), (410, 1293, 120, 8, 0.25)):
        c = Canvas((cx - rx, cy - ry, cx + rx, cy + ry), ss=2, pad=30)
        c.ellipse(cx, cy, rx, ry)
        darken(img, c.mask(blur=12), amt)
    # plate
    c = Canvas((940, 990, 1410, 1140), ss=3)
    c.ellipse(1175, 1065, 225, 65)
    paint(img, c.mask(), (240, 240, 240))
    c = Canvas((940, 990, 1410, 1140), ss=3)
    c.ellipse(1175, 1060, 150, 40)
    paint(img, c.mask(blur=1.5), (222, 222, 222))
    # mug
    box = (580, 780, 920, 1100)
    shade = hgrad(W, H, [(0, (245, 245, 245)), (0.55, (245, 245, 245)), (1, (196, 196, 196))], 600, 820)
    c = Canvas(box, ss=3)
    c.line([(820 + 70 * math.cos(math.radians(a)), 950 + 80 * math.sin(math.radians(a)))
            for a in np.linspace(-75, 75, 40)], 24)
    paint(img, c.mask(), (205, 205, 205))
    c = Canvas(box, ss=3)
    c.rect(600, 820, 820, 1080)
    c.ellipse(710, 1080, 110, 14)
    c.ellipse(710, 820, 110, 22)
    paint(img, c.mask(), shade)
    c = Canvas(box, ss=3)
    c.ellipse(710, 822, 96, 15)
    paint(img, c.mask(), (200, 196, 190))
    _gray_card(img, 300, 1150, 520, 1290)

    img[..., 0] *= 0.86
    img[..., 1] = img[..., 1] * 1.06 + 8
    img[..., 2] *= 0.98
    img = np.clip(img, 0, 255) * 0.82
    add_noise(img, 4, r, mono=True)
    save_jpg(img, 2, name, quality=92, subsampling=0)


def m2_flat_landscape():
    name = "l06-flat-landscape.jpg"
    r = rng(name)
    W, H = 2400, 1600
    hz = H // 2
    img = np.empty((H, W, 3), F32)
    img[:hz] = vgrad(W, hz, [(0, (110, 160, 215)), (1, (210, 225, 240))])
    img[hz:] = vgrad(W, H - hz, [(0, (104, 150, 78)), (1, (88, 132, 64))])
    for i in range(5):
        cw = r.uniform(260, 480)
        cx, cy = 250 + i * 480 + r.uniform(-60, 60), r.uniform(110, 450)
        c = Canvas((cx - cw, cy - cw / 2, cx + cw, cy + cw / 2), ss=2, pad=50)
        soft_blob(c, r, cx, cy, cw, cw * 0.35)
        paint(img, c.mask(blur=25), (255, 255, 255), 0.9)
    xs = np.arange(0, W + 9, 8)
    for base, amp, col, parts in ((690, 90, (110, 130, 150), [(800, 1, 0.5), (330, 0.45, 2.0)]),
                                  (750, 55, (80, 100, 115), [(1100, 1, 2.8), (420, 0.5, 0.7)])):
        c = Canvas((0, 560, W, hz + 12), ss=2)
        c.poly(list(zip(xs, smooth_wave(xs, base, amp, parts))) + [(W + 8, hz + 10), (0, hz + 10)])
        paint(img, c.mask(), col)
    add_noise(img[hz:], 10, r, mono=True)
    c = Canvas((1300, 700, 1900, 1240), ss=3)
    c.rect(1580, 960, 1620, 1220)
    paint(img, c.mask(), (80, 55, 35))
    c = Canvas((1300, 700, 1900, 1240), ss=3)
    for cx, cy, rad in ((1600, 880, 150), (1490, 950, 130), (1712, 948, 138)):
        c.circle(cx, cy, rad)
    paint(img, c.mask(), (45, 100, 45))
    img = 70 + img * 0.45
    add_noise(img, 3, r, mono=True)
    save_jpg(img, 2, name, quality=92, subsampling=0)


def m2_tone_ramp():
    W, H = 2400, 800
    g = np.zeros((H, W), F32)
    g[:380] = np.round(np.arange(W, dtype=F32) / (W - 1) * 255)[None, :]
    g[380:420] = 128
    vals = [0, 26, 51, 77, 102, 128, 153, 179, 204, 230, 255]
    sw = W / 11
    for k, v in enumerate(vals):
        g[420:, int(round(k * sw)):int(round((k + 1) * sw))] = v
    im = Image.fromarray(g.astype(np.uint8)).convert("RGB")
    d = ImageDraw.Draw(im)
    for k, v in enumerate(vals):
        d.text(((k + 0.5) * sw, 610), f"{k * 10}%", font=font(40, True), anchor="mm",
               fill=(255, 255, 255) if v < 128 else (0, 0, 0))
    for x, word, anc in ((24, "shadows", "lm"), (W / 2, "midtones", "mm"), (W - 24, "highlights", "rm")):
        d.text((x, 400), word, font=font(28), anchor=anc, fill=(0, 0, 0))
    save_png(im, 2, "l06-tone-ramp.png")


def m2_badge_crisp():
    W = H = 1600
    cx = cy = 800
    X, Y = coords(W, H)
    d = np.hypot(X - cx, Y - cy)
    img = np.full((H, W, 3), 255, F32)
    xi, yi = np.meshgrid(np.arange(W), np.arange(H))
    hatch = ((xi + yi) % 4 == 0) & (d > 521) & (d < 659)
    img[hatch] = (20, 40, 90)
    c = Canvas((0, 0, W, H), ss=4)
    for rad in (700, 660, 520):
        c.circle(cx, cy, rad + 1)
        c.circle(cx, cy, rad - 1, 0)
    paint(img, c.mask(), (20, 40, 90))
    im = Image.fromarray(to_u8(img))
    dr = ImageDraw.Draw(im)
    dr.text((cx, 640), "Ps", font=font(575, True), anchor="mm", fill=(20, 115, 230))
    txt = "SMART OBJECT TEST · SCALE 30% → 100%"
    for y, size in ((900, 22), (940, 16), (970, 12)):
        dr.text((cx, y), txt, font=font(size, True), anchor="mm", fill=(20, 40, 90))
    img = np.asarray(im, F32).copy()
    ys, xs_ = np.mgrid[1030:1270, 680:920]
    img[1030:1270, 680:920] = (((xs_ // 2 + ys // 2) % 2) * 255)[..., None]
    save_png(img, 2, "l07-badge-crisp.png")


def m2_subject_busy_bg():
    name = "l07-subject-busy-bg.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = solid(W, H, (200, 195, 185))
    bw, bh, m = 160, 60, 6
    for row in range(H // bh + 1):
        off = -(bw // 2) * (row % 2)
        for col in range(W // bw + 2):
            x0, y0 = off + col * bw, row * bh
            base = np.array((150, 70, 50), F32) + r.uniform(-15, 15)
            base = base + r.uniform(-6, 6, 3)
            img[y0 + m // 2:y0 + bh - m // 2, max(0, x0 + m // 2):max(0, x0 + bw - m // 2)] = base
    add_noise(img, 8, r, mono=True)
    for _ in range(60):
        x, y, rad = r.uniform(20, W - 20), r.uniform(20, H / 2), r.uniform(6, 10)
        c = Canvas((x - rad, y - rad, x + rad, y + rad), ss=1, pad=30)
        c.circle(x, y, rad * 2.2)
        paint(img, c.mask(blur=10), (255, 220, 150), 0.35)
        c = Canvas((x - rad, y - rad, x + rad, y + rad), ss=3, pad=2)
        c.circle(x, y, rad)
        paint(img, c.mask(), (255, 235, 180))

    box = (900, 150, 1500, 1310)
    c = Canvas(box, ss=3)
    for fx, fy in ((1060, 330), (1200, 250), (1345, 345)):
        c.line(quad_bezier((1200, 600), ((1200 + fx) / 2, 420), (fx, fy), 40), 12)
    paint(img, c.mask(), (30, 80, 35))
    c = Canvas(box, ss=3)
    c.ellipse(1200, 1000, 200, 300)
    c.rect(1130, 560, 1270, 720)
    vase = c.mask()
    paint(img, vase, hgrad(W, H, [(0, (26, 152, 162)), (0.6, (20, 140, 150)), (1, (12, 100, 108))], 1000, 1400))
    c = Canvas(box, ss=3)
    c.rect(1075, 580, 1110, 1260)
    paint(img, Mask(vase.x, vase.y, c.mask().a * vase.a), (90, 200, 205))
    c = Canvas(box, ss=3)
    for fx, fy in ((1060, 330), (1200, 250), (1345, 345)):
        for k in range(8):
            a = 2 * math.pi * k / 8
            c.circle(fx + 55 * math.cos(a), fy + 55 * math.sin(a), 45)
    paint(img, c.mask(), (250, 200, 40))
    c = Canvas(box, ss=3)
    for fx, fy in ((1060, 330), (1200, 250), (1345, 345)):
        c.circle(fx, fy, 30)
    paint(img, c.mask(), (235, 120, 20))
    save_jpg(img, 2, name, quality=92, subsampling=0)


# ======================================================================================
# MODULE 3: Retouching          (2x supersampling + LANCZOS; marks and noise at final size)
# ======================================================================================

FACE_SKIN = (224, 178, 150)
FACE_W, FACE_H = 2000, 2400


def _hairline_y(x):
    t = (np.asarray(x, float) - 1000) / 360
    return 640 + 260 * t ** 2 + 10 * np.sin(np.asarray(x, float) / 45)


def _fc(box, ss=2):
    return Canvas(box, ss=ss, resample=Image.LANCZOS)


def _m(c: Canvas, blur=0.0) -> Mask:
    m = c.mask(blur)
    return Mask(m.x, m.y, np.clip(m.a, 0, 1))


def _face_base(variant: str):
    """Draw the shared illustrated face. variant: 'l08', 'l09' or 'l10'.

    Returns (img, skin_mask_full, hair_mask_full)."""
    W, H = FACE_W, FACE_H
    full = (0, 0, W, H)
    flat = variant == "l10"
    if flat:
        img = hgrad(W, H, [(0, (205, 212, 222)), (1, (140, 150, 165))])
    else:
        img = vgrad(W, H, [(0, (190, 200, 212)), (1, (150, 160, 175))])
    skin = np.array(FACE_SKIN, F32)
    shade = np.ones(W, F32) if flat else np.interp(np.arange(W), [600, 1400], [1.03, 0.95]).astype(F32)
    skin_arr = np.ascontiguousarray(np.broadcast_to((skin[None, :] * shade[:, None])[None], (H, W, 3)))
    hair_col = np.array((55, 40, 30), F32)
    hshade = np.interp(np.arange(W), [520, 1480], [1.13, 1.0] if flat else [1.0, 1.0]).astype(F32)
    hair_arr = np.ascontiguousarray(np.broadcast_to((hair_col[None, :] * hshade[:, None])[None], (H, W, 3)))

    c = _fc((500, 380, 1500, 1480))
    c.ellipse(1000, 930, 480, 540)
    hair_back = _m(c)
    paint(img, hair_back, hair_arr)

    c = _fc((840, 1440, 1160, 1960))
    c.rect(850, 1450, 1150, 1950)
    neck = _m(c)
    ys = np.arange(neck.a.shape[0]) + neck.y
    nshade = np.where(ys < 1570, 0.9, 1.0).astype(F32)
    neck_col = skin_arr[neck.y:neck.y + neck.a.shape[0], neck.x:neck.x + neck.a.shape[1]] * nshade[:, None, None]
    paint(img, neck, np.ascontiguousarray(neck_col))

    c = _fc((0, 1850, W, H))
    c.ellipse(1000, 2500, 900, 620)
    cloth = _m(c)
    paint(img, cloth, (60, 80, 110))

    c = _fc((540, 970, 1460, 1190))
    c.ellipse(600, 1080, 45, 90)
    c.ellipse(1400, 1080, 45, 90)
    ears = _m(c)
    paint(img, ears, skin_arr * 0.93)

    c = _fc((590, 590, 1410, 1650))
    c.ellipse(1000, 1120, 400, 520)
    face = _m(c)
    paint(img, face, skin_arr)

    xs = np.arange(540, 1461, 4)
    c = _fc((500, 380, 1500, 1480))
    c.poly([(540, 380)] + list(zip(xs, np.minimum(_hairline_y(xs), 1100))) + [(1460, 380)])
    front = _m(c)
    front = Mask(front.x, front.y, front.a * hair_back.a)
    paint(img, front, hair_arr)

    skin_m = np.maximum.reduce([full_mask(face, W, H), full_mask(ears, W, H), full_mask(neck, W, H)])
    skin_m *= 1 - full_mask(front, W, H)
    skin_m *= 1 - full_mask(cloth, W, H)
    hair_m = np.maximum(full_mask(hair_back, W, H) * (1 - np.maximum(full_mask(face, W, H), full_mask(ears, W, H))),
                        full_mask(front, W, H))

    # nose shadow + nostrils
    c = _fc((990, 990, 1080, 1230))
    c.line([(1025, 1010), (1045, 1210)], 8, round_caps=True)
    darken(img, _m(c, blur=4), 0.07 if flat else 0.15)
    c = _fc((940, 1220, 1060, 1250))
    c.ellipse(970, 1235, 13, 7)
    c.ellipse(1030, 1235, 13, 7)
    darken(img, _m(c), 0.4)

    # eyebrows
    c = _fc((740, 860, 1260, 930))
    for x0, x1 in ((760, 920), (1080, 1240)):
        c.line(quad_bezier((x0, 915), ((x0 + x1) / 2, 880), (x1, 913), 30), 14, round_caps=True)
    paint(img, _m(c), (70, 50, 40))

    # eyes
    white = (200, 195, 185) if flat else (235, 232, 225)
    feat = np.zeros((H, W), F32)
    for ex in (840, 1160):
        top = quad_bezier((ex - 75, 1000), (ex, 934), (ex + 75, 1000), 40)
        bot = quad_bezier((ex + 75, 1000), (ex, 1066), (ex - 75, 1000), 40)
        c = _fc((ex - 85, 955, ex + 85, 1045))
        c.poly(top + bot)
        ew = _m(c)
        paint(img, ew, white)
        c = _fc((ex - 85, 955, ex + 85, 1045))
        c.circle(ex, 1000, 32)
        paint(img, Mask(ew.x, ew.y, _m(c).a * ew.a), (90, 60, 40))
        c = _fc((ex - 85, 955, ex + 85, 1045))
        c.circle(ex, 1000, 14)
        paint(img, Mask(ew.x, ew.y, _m(c).a * ew.a), (15, 15, 15))
        c = _fc((ex - 85, 955, ex + 85, 1045))
        c.circle(ex - 9, 991, 5)
        paint(img, _m(c), (255, 255, 255))
        c = _fc((ex - 85, 955, ex + 85, 1045))
        c.line(top, 4)
        paint(img, _m(c), (45, 30, 25))
        feat = np.maximum(feat, full_mask(ew, W, H))

    # mouth
    c = _fc((880, 1300, 1120, 1410))
    c.poly(quad_bezier((890, 1345), (1000, 1305), (1110, 1345), 40) +
           quad_bezier((1110, 1345), (1000, 1432), (890, 1345), 40))
    lips = _m(c)
    paint(img, lips, (185, 95, 95))
    c = _fc((880, 1300, 1120, 1410))
    c.rrect(925, 1345, 1075, 1372, 10)
    teeth = Mask(lips.x, lips.y, _m(c).a * lips.a)
    paint(img, teeth, (220, 205, 160) if flat else (240, 235, 220))
    feat = np.maximum(feat, full_mask(lips, W, H))
    skin_m *= 1 - feat
    return img, skin_m, hair_m


def _freckles(r, n, region, avoid=(), fixed=()):
    """Random freckle centres inside an ellipse region = (cx, cy, rx, ry)."""
    cx, cy, rx, ry = region
    pts = [(x, y, 4.0) for x, y in fixed]
    while len(pts) < n:
        x, y = cx + r.uniform(-rx, rx), cy + r.uniform(-ry, ry)
        if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 > 1:
            continue
        if any(abs(x - ex) < 90 and abs(y - 1000) < 45 for ex in (840, 1160)):
            continue
        rad = r.uniform(3, 5)
        if any(math.hypot(x - ax, y - ay) < 25 + ar + rad for ax, ay, ar in avoid):
            continue
        if any(math.hypot(x - px, y - py) < 12 for px, py, _ in pts):
            continue
        pts.append((x, y, rad))
    return pts


def _paint_freckles(img, pts):
    for x, y, rad in pts:
        c = Canvas((x - rad, y - rad, x + rad, y + rad), ss=4, pad=2)
        c.circle(x, y, rad)
        paint(img, c.mask(blur=0.5), (175, 120, 90), 0.7)


def _permanent_features(img, r):
    c = Canvas((826, 1351, 844, 1369), ss=4, pad=2)
    c.circle(835, 1360, 9)
    paint(img, c.mask(), (90, 55, 40))
    c = Canvas((860, 1280, 1140, 1430), ss=3, pad=6)
    c.line(quad_bezier((900, 1290), (866, 1350), (885, 1420), 30), 4)
    c.line(quad_bezier((1100, 1290), (1134, 1350), (1115, 1420), 30), 4)
    darken(img, c.mask(blur=3), 0.13)


def _pores(img, skin_m, r, s1, s2):
    H, W = skin_m.shape
    n = r.standard_normal((H, W), dtype=F32) * s1
    n2 = r.standard_normal((H // 2, W // 2), dtype=F32) * s2
    n += np.asarray(Image.fromarray(n2).resize((W, H), Image.BILINEAR), F32)
    img += (n * skin_m)[..., None]
    np.clip(img, 0, 255, out=img)


def _gauss_patch(img, mask, cx, cy, radius, dr=0, dg=0, db=0):
    sig = radius / 2
    x0, x1 = int(max(cx - 4 * sig, 0)), int(min(cx + 4 * sig, img.shape[1]))
    y0, y1 = int(max(cy - 4 * sig, 0)), int(min(cy + 4 * sig, img.shape[0]))
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(F32)
    g = np.exp(-((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2) / (2 * sig * sig))
    g = g * (mask[y0:y1, x0:x1] if mask is not None else 1)
    img[y0:y1, x0:x1] += g[..., None] * np.array((dr, dg, db), F32)


def _hair_curve(img, p0, p1, p2, width):
    xs, ys = zip(p0, p1, p2)
    c = Canvas((min(xs), min(ys), max(xs), max(ys)), ss=4, pad=6)
    c.line(quad_bezier(p0, p1, p2, 80), width)
    paint(img, c.mask(blur=0.3), (50, 35, 25))


def _spot(img, skin_m, hair_m, x, y, rad):
    R = 1.6 * rad
    x0, x1, y0, y1 = int(x - R - 2), int(x + R + 3), int(y - R - 2), int(y + R + 3)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(F32)
    d = np.hypot(xx + 0.5 - x, yy + 0.5 - y)
    a = np.clip(1 - d / R, 0, 1) ** 0.9
    a = a * np.clip(skin_m[y0:y1, x0:x1] + 0.35 * hair_m[y0:y1, x0:x1], 0, 1)
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a[..., None]) + np.array((200, 90, 85), F32) * a[..., None]
    c = Canvas((x - rad, y - rad, x + rad, y + rad), ss=4, pad=3)
    c.d.arc(c.B(x - rad * 0.8, y - rad * 0.8, x + rad * 0.8, y + rad * 0.8), 190, 260, fill=255, width=6)
    paint(img, c.mask(blur=0.4), (236, 170, 160), 0.8)


L08_SPOTS = [(880, 760), (1010, 720), (1120, 790), (760, 1150), (820, 1240), (1220, 1130),
             (1180, 1260), (1270, 1190), (960, 1520), (1060, 1500)]
FRECKLE_REGION = (1000, 1110, 260, 90)


@lru_cache(maxsize=None)
def _l08_image():
    r = rng("l08-portrait-blemishes.jpg")
    img, skin_m, hair_m = _face_base("l08")
    radii = [float(r.uniform(7, 13)) for _ in L08_SPOTS]
    avoid = [(x, y, rr) for (x, y), rr in zip(L08_SPOTS, radii) if (x, y) != (1220, 1130)]
    fr = _freckles(r, 30, FRECKLE_REGION, avoid=avoid, fixed=[(1220, 1130)])
    _paint_freckles(img, fr)
    _permanent_features(img, r)
    for (x, y), rad in zip(L08_SPOTS, radii):
        _spot(img, skin_m, hair_m, x, y, rad)
    hl = []
    for x in (900, 1110):
        y = float(_hairline_y(x)) + 3.5
        _spot(img, skin_m, hair_m, x, y, 10)
        hl.append((x, y))
    _pores(img, skin_m, r, 7, 4)
    _hair_curve(img, (1150, 1050), (1320, 1130), (1330, 1320), 2)
    c = Canvas((990, 1555, 1010, 1575), ss=4, pad=2)
    for dx, dy, rr in ((-2, -1, 3), (2, -2, 2.5), (1, 2, 3), (-3, 2, 2)):
        c.circle(1000 + dx, 1565 + dy, rr)
    paint(img, c.mask(), (250, 250, 250))
    flaws = [(x, y, rr * 1.6 + 8) for (x, y), rr in zip(L08_SPOTS, radii)]
    flaws += [(x, y, 26) for x, y in hl]
    flaws += [(1275, 1170, 110), (1000, 1565, 20)]
    return img, flaws


def m3_portrait_blemishes():
    img, _ = _l08_image()
    save_jpg(img, 3, "l08-portrait-blemishes.jpg", quality=92, subsampling=0)


def m3_flaw_map():
    img, flaws = _l08_image()
    s = 0.5
    im = Image.fromarray(to_u8(img)).resize((1000, 1200), Image.LANCZOS)
    c = Canvas((0, 0, 1000, 1200), ss=3, mode="RGBA")
    red, green = (225, 30, 30, 255), (20, 160, 60, 255)

    def ring(x, y, rad, col, width=3):
        c.d.ellipse(c.B(x - rad, y - rad, x + rad, y + rad), outline=col, width=int(width * c.ss))

    for i, (x, y, rad) in enumerate(flaws, start=1):
        x, y, rad = x * s, y * s, max(rad * s, 12)
        ring(x, y, rad, red)
        lx, ly = x + rad * 0.75 + 9, y - rad * 0.75 - 9
        c.circle(lx, ly, 11, red)
        c.text(lx, ly, str(i), 14, bold=True, fill=(255, 255, 255), anchor="mm")
    ring(835 * s, 1360 * s, 16, green)
    for x in (888, 1112):
        c.d.ellipse(c.B(x * s - 16, 1290 * s - 6, x * s + 16, 1420 * s + 6), outline=green, width=3 * c.ss)
    cx, cy, rx, ry = FRECKLE_REGION
    for a0 in range(0, 360, 12):
        c.d.arc(c.B((cx - rx) * s - 6, (cy - ry) * s - 6, (cx + rx) * s + 6, (cy + ry) * s + 6),
                a0, a0 + 7, fill=green, width=3 * c.ss)
    c.rect(0, 0, 1000, 44, (255, 255, 255, 230))
    c.text(20, 22, "RED = temporary (heal)", 20, bold=True, fill=red, anchor="lm")
    c.text(330, 22, "GREEN = permanent (keep)", 20, bold=True, fill=green, anchor="lm")
    c.text(980, 22, "L08 flaw map · instructor only", 16, fill=(60, 60, 60, 255), anchor="rm")
    base = np.asarray(im, F32).copy()
    over(base, c.layer())
    save_png(base, 3, "l08-flaw-map-INSTRUCTOR.png", folder="instructor")


def m3_portrait_blotchy():
    name = "l09-portrait-blotchy.jpg"
    r = rng(name)
    img, skin_m, hair_m = _face_base("l09")
    for cx, cy, rad, d in (((800, 1180, 140, (22, -8, -6))), ((1200, 1180, 140, (22, -8, -6))),
                           ((1000, 800, 110, (15, -5, 0))), ((1000, 1215, 60, (25, -10, 0))),
                           ((1000, 1520, 90, (18, -4, 0))), ((720, 1400, 80, (-5, -15, 5))),
                           ((1160, 890, 90, (0, 8, -10)))):
        _gauss_patch(img, skin_m, cx, cy, rad, *d)
    _paint_freckles(img, _freckles(r, 30, FRECKLE_REGION))
    _permanent_features(img, r)
    _pores(img, skin_m, r, 8, 4)
    _hair_curve(img, (860, 700), (1040, 730), (1180, 860), 1.8)
    save_jpg(img, 3, name, quality=92, subsampling=0)


def m3_skin_swatch():
    name = "l09-skin-swatch.jpg"
    r = rng(name)
    W = H = 1200
    img = solid(W, H, FACE_SKIN)
    _gauss_patch(img, None, 350, 400, 200, 22, -8, 0)
    _gauss_patch(img, None, 820, 760, 160, 18, -6, 0)
    _gauss_patch(img, None, 600, 950, 120, 0, 8, -10)
    pts = []
    while len(pts) < 12:
        x, y = r.uniform(60, W - 60), r.uniform(60, H - 60)
        if all(math.hypot(x - px, y - py) > 60 for px, py, _ in pts):
            pts.append((x, y, r.uniform(3, 5)))
    _paint_freckles(img, pts)
    _pores(img, np.ones((H, W), F32), r, 8, 4)
    _hair_curve(img, (150, 1000), (650, 760), (1050, 700), 2)
    save_jpg(img, 3, name, quality=92, subsampling=0)


def m3_portrait_flat():
    name = "l10-portrait-flat.jpg"
    r = rng(name)
    img, skin_m, hair_m = _face_base("l10")
    _gauss_patch(img, skin_m, 800, 1120, 120, 12, 12, 12)          # sigma = 60 px
    _paint_freckles(img, _freckles(r, 30, FRECKLE_REGION))
    _permanent_features(img, r)
    _pores(img, skin_m, r, 6, 3)
    save_jpg(img, 3, name, quality=92, subsampling=0)


# ======================================================================================
# MODULE 4: Compositing
# ======================================================================================

FIG_BOX = (380, 300, 1220, 2270)
SKIN, HAIR, SHIRT, PANTS, SHOES = "#e0b08c", "#4a2e1c", "#2f6fe0", "#2c2f38", "#1b1b1f"


@lru_cache(maxsize=None)
def _figure_geometry():
    """Shared figure for l11-figure-on-green, the cutout reference and l12-indoor-warm.

    Returns (x0, y0, rgb, alpha, strands) in true (unlit) colors: rgb/alpha are the
    body, strands is the wispy-hair coverage mask (same box)."""
    r = rng("figure-geometry")
    c = Canvas(FIG_BOX, ss=3, mode="RGBA")
    for x0, x1 in ((590, 785), (815, 1010)):                     # trousers
        c.rrect(x0, 1380, x1, 2205, 24, PANTS)
    c.rrect(590, 2180, 770, 2250, 32, SHOES)
    c.rrect(830, 2180, 1010, 2250, 32, SHOES)
    for x0, x1, hx in ((425, 545, 482), (1055, 1175, 1118)):     # arms + hands
        c.circle(hx, 1402, 50, SKIN)
        c.rrect(x0, 720, x1, 1395, 55, SHIRT)
    c.rect(758, 600, 842, 730, SKIN)                             # neck
    c.rrect(540, 690, 1060, 1410, 80, SHIRT)                     # torso (520 x 720)
    c.ellipse(800, 473, 137, 143, HAIR)                          # hair cap (top at 330)
    c.ellipse(800, 492, 115, 145, SKIN)                          # head 230 x 290
    c.d.chord(c.B(800 - 128, 470 - 150, 800 + 128, 470 + 150), 188, 352, fill=c._f(HAIR))
    for ex in (758, 842):
        c.ellipse(ex, 505, 11, 8, "#3a2a22")
    c.line([(772, 575), (800, 584), (828, 575)], 5, "#b07060")
    L = c.layer()

    cs = Canvas(FIG_BOX, ss=3)
    for _ in range(260):
        t = r.uniform(0.88 * math.pi, 2.12 * math.pi)
        px, py = 800 + 128 * math.cos(t), 473 + 136 * math.sin(t)
        nx, ny = math.cos(t) / 137, math.sin(t) / 143
        nn = math.hypot(nx, ny)
        a = math.atan2(ny / nn, nx / nn) + math.radians(r.uniform(-18, 18))
        a = math.atan2(math.sin(a) + 0.35, math.cos(a))            # a little gravity
        ln = 30 + 90 * r.random() ** 1.8
        ex, ey = px + ln * math.cos(a), py + ln * math.sin(a)
        bend = r.uniform(-0.18, 0.18) * ln
        mx = (px + ex) / 2 - bend * math.sin(a)
        my = (py + ey) / 2 + bend * math.cos(a)
        cs.line(quad_bezier((px, py), (mx, my), (ex, ey), 14), r.uniform(1, 1.7), r.uniform(0.4, 0.8) * 255)
    S = cs.mask(blur=0.35)
    return L.x, L.y, L.rgb, L.a, S.a


def _lit(rgb, x0, lo, hi, from_right=True):
    xs = np.arange(rgb.shape[1], dtype=F32) + x0
    t = np.clip((xs - 420) / (1180 - 420), 0, 1)
    if not from_right:
        t = 1 - t
    f = lo + (hi - lo) * t
    return np.clip(rgb * f[None, :, None], 0, 255)


def _figure_on(bg, band_px, band_color, band_mix, strand_color, light):
    x0, y0, rgb, a, S = _figure_geometry()
    rgb = light(rgb.copy(), x0)
    inner = erode((a > 0.5).astype(F32), band_px)
    band = np.clip(a - inner, 0, 1)[..., None] * band_mix
    rgb = rgb * (1 - band) + np.array(band_color, F32) * band
    over(bg, Layer(x0, y0, rgb, a))
    paint(bg, Mask(x0, y0, S), strand_color)
    return bg


def m4_figure_on_green():
    name = "l11-figure-on-green.png"
    r = rng(name)
    W, H = 1600, 2400
    green = hexc("#3f9a3a")
    img = solid(W, H, green)
    for _ in range(50):
        cx, cy, rad = r.uniform(0, W), r.uniform(0, H), r.uniform(60, 200)
        c = Canvas((cx - rad, cy - rad, cx + rad, cy + rad), ss=1, pad=60)
        c.circle(cx, cy, rad)
        k = r.uniform(-0.22, 0.22)
        col = tuple(np.clip(np.array(green) * (1 + k), 0, 255))
        paint(img, c.mask(blur=25), col, 0.8)
    add_uniform_noise(img, 6, r)
    hair = np.array(hexc(HAIR), F32)
    strand_col = tuple(hair * 0.65 + np.array(green) * 0.35)
    _figure_on(img, 4, green, 0.5, strand_col,
               lambda rgb, x0: np.clip(_lit(rgb, x0, 0.88, 1.18) * 1.04, 0, 255))
    add_noise(img, 1.5, r)
    save_png(img, 4, name)


def m4_figure_cutout_reference():
    name = "l11-figure-cutout-reference.png"
    W, H = 1600, 2400
    x0, y0, rgb, a, S = _figure_geometry()
    rgb = np.clip(_lit(rgb.copy(), x0, 0.88, 1.18) * 1.04, 0, 255)
    hair = np.array(hexc(HAIR), F32)
    A = S + a * (1 - S)
    C = (hair * S[..., None] + rgb * (a * (1 - S))[..., None]) / np.maximum(A, 1e-6)[..., None]
    out = np.zeros((H, W, 4), F32)
    h, w = a.shape
    out[y0:y0 + h, x0:x0 + w, :3] = C
    out[y0:y0 + h, x0:x0 + w, 3] = A * 255
    out[..., :3] *= (out[..., 3:] > 0)
    save_png(Image.fromarray(to_u8(out), "RGBA"), 4, name)


def m4_pet_on_blue_wall():
    name = "l11-pet-on-blue-wall.png"
    r = rng(name)
    W, H = 1600, 1600
    blue = np.array(hexc("#2f5fbf"), F32)
    img = solid(W, H, blue)
    for x in range(160, W, 160):
        img[:, x] *= 0.92
    fy = H - 180
    img[fy:] = vgrad(W, 180, [(0, hexc("#8a7a66")), (1, (124, 109, 91))])
    add_uniform_noise(img, 5, r)

    c = Canvas((300, fy - 60, 1300, fy + 60), ss=2, pad=40)
    c.ellipse(820, fy + 8, 420, 36)
    darken(img, c.mask(blur=18), 0.45)

    box = (250, 180, 1350, 1560)
    tan, chest = hexc("#c89a64"), hexc("#e8cfa8")
    c = Canvas(box, ss=3, mode="RGBA")
    c.line(quad_bezier((1090, 1280), (1330, 1520), (880, 1440), 40), 70, tan, round_caps=True)
    c.poly([(598, 450), (628, 235), (745, 372)], tan)             # ears
    c.poly([(1002, 450), (972, 235), (855, 372)], tan)
    c.poly([(625, 410), (640, 290), (712, 380)], "#d99b8a")
    c.poly([(975, 410), (960, 290), (888, 380)], "#d99b8a")
    c.ellipse(800, 1020, 350, 410, tan)
    c.ellipse(800, 930, 170, 280, chest)
    c.circle(800, 560, 220, tan)
    c.ellipse(800, 640, 95, 70, chest)
    for ex in (720, 880):
        c.ellipse(ex, 540, 26, 30, "#2a2a22")
        c.circle(ex + 8, 530, 7, (240, 240, 230))
    c.poly([(780, 615), (820, 615), (800, 640)], "#5a3a30")
    L = c.layer()
    a = L.a.copy()
    rgb = L.rgb.copy()

    # outline band tinted 40 % toward the wall
    inner = erode((a > 0.5).astype(F32), 5)
    band = np.clip(a - inner, 0, 1)
    ys = np.arange(a.shape[0]) + L.y
    band[ys >= fy - 5] = 0
    rgb = rgb * (1 - 0.4 * band[..., None]) + blue * 0.4 * band[..., None]
    over(img, Layer(L.x, L.y, rgb, a))

    # fur fringe: hundreds of short outward strokes, tinted toward the wall
    sil = (a > 0.5).astype(F32)
    edge = (sil > 0) & (erode(sil, 1) == 0)
    eys, exs = np.nonzero(edge)
    keep = (eys + L.y) < fy - 15
    eys, exs = eys[keep], exs[keep]
    sb = np.asarray(Image.fromarray(to_u8(sil * 255)).filter(ImageFilter.GaussianBlur(6)), F32)
    gy, gx = np.gradient(sb)
    idx = r.choice(len(eys), size=1400, replace=False)
    cf = Canvas(box, ss=3, mode="RGBA")
    for i in idx:
        y, x = eys[i], exs[i]
        nx, ny = -gx[y, x], -gy[y, x]
        nn = math.hypot(nx, ny) or 1.0
        ang = math.atan2(ny / nn, nx / nn) + math.radians(r.uniform(-25, 25))
        ln = r.uniform(8, 30)
        px, py = x + L.x - 4 * math.cos(ang), y + L.y - 4 * math.sin(ang)
        col = np.array(rand_color_near(r, tan, 18), F32) * 0.6 + blue * 0.4
        cf.line([(px, py), (px + ln * math.cos(ang), py + ln * math.sin(ang))], 1,
                tuple(col) + (r.uniform(0.5, 0.9) * 255,))
    over(img, cf.layer(blur=0.3))
    save_png(img, 4, name)


def _posts_scene(kind: str):
    W, H = 2400, 1600
    hz = 1000
    posts = [(900, 1060, 110, 12), (1500, 1180, 220, 22), (500, 1450, 420, 40)]   # far to near
    if kind == "sunset":
        img = np.empty((H, W, 3), F32)
        img[:hz] = vgrad(W, hz, [(0, "#3b3f78"), (0.55, "#c0567a"), (1, "#f08a3c")])
        img[hz:] = vgrad(W, H - hz, [(0, (110, 72, 50)), (0.35, (84, 54, 39)), (1, "#4a2f22")])
        X, Y = coords(W, H)
        d = np.hypot(X - 1900, Y - 960)
        g = (np.clip(1 - d / 500, 0, 1) ** 1.6 * 0.6)[..., None]
        glow_col = np.array((255, 160, 80), F32)
        img = img * (1 - g) + glow_col * g
        c = Canvas((1800, 860, 2000, 1000), ss=3, pad=10)
        c.circle(1900, 960, 70)
        m = c.mask(blur=2)
        m.a[(np.arange(m.a.shape[0]) + m.y) >= hz] = 0            # half sunk
        paint(img, m, "#ffe2a0")
        path_col, haze_col, post_col = hexc("#8a5a3a"), np.array((200, 120, 90), F32), (46, 29, 20)
    else:
        img = np.empty((H, W, 3), F32)
        img[:hz] = vgrad(W, hz, [(0, "#9aa6b2"), (1, "#b8c2cc")])
        img[hz:] = vgrad(W, H - hz, [(0, (104, 112, 102)), (1, "#5d665a")])
        path_col, haze_col, post_col = (122, 124, 120), np.array((175, 184, 192), F32), (62, 60, 57)

    c = Canvas((700, hz, 1700, H), ss=2)
    c.poly([(750, H), (1650, H), (1200, hz)])
    paint(img, c.mask(), vgrad(W, H, [(0, lerp(path_col, (150, 110, 85) if kind == "sunset" else (140, 142, 138), 0.3)), (1, path_col)], hz, H))

    for x, base, h, w in posts:
        if kind == "sunset":
            L = 2.2 * h
            dx, dy = -L * 0.9, L * 0.35
            c = Canvas((x + dx - w * 2, base - 10, x + w, base + dy + 10), ss=2, pad=20)
            c.poly([(x - w / 2, base), (x + w / 2, base), (x + w / 2 + dx, base + dy + w * 0.4),
                    (x - w / 2 + dx - w * 0.6, base + dy)])
            darken(img, c.mask(blur=6), 0.45)
        else:
            c = Canvas((x - 3 * w - 40, base - 30, x + 3 * w + 40, base + 30), ss=1, pad=60)
            c.ellipse(x, base + 2, 2.5 * w + 0.12 * h, 0.5 * w + 6)
            darken(img, c.mask(blur=30), 0.15)

    ys = np.arange(hz, H, dtype=F32)
    ha = (0.4 * (1 - (ys - hz) / (H - hz)) ** 2)[:, None, None]
    img[hz:] = img[hz:] * (1 - ha) + haze_col * ha

    for x, base, h, w in posts:
        hz_amt = 0.4 * (1 - (base - hz) / (H - hz)) ** 2
        col = lerp(post_col, haze_col, hz_amt)
        c = Canvas((x - w, base - h - 4, x + w, base + 2), ss=3)
        c.rect(x - w / 2, base - h, x + w / 2, base)
        paint(img, c.mask(), col)
        if kind == "sunset":
            c = Canvas((x - w, base - h - 4, x + w, base + 2), ss=3)
            rw = max(2, w * 0.14)
            c.rect(x + w / 2 - rw, base - h, x + w / 2, base)
            paint(img, c.mask(blur=0.6), lerp((255, 150, 70), haze_col, hz_amt), 0.85)

    if kind == "sunset":
        img = 14 + img * 0.92
    else:
        img = 38 + img * 0.76
    return img


def m4_scene_sunset():
    name = "l12-scene-sunset.jpg"
    img = _posts_scene("sunset")
    add_noise(img, 2.5, rng(name))
    save_jpg(img, 4, name)


def m4_scene_overcast():
    name = "l12-scene-overcast.jpg"
    img = _posts_scene("overcast")
    add_noise(img, 2.5, rng(name))
    save_jpg(img, 4, name)


TUNGSTEN = np.array((1.0, 0.86, 0.62), F32)       # per-channel tungsten multipliers


def m4_subject_indoor_warm():
    name = "l12-subject-indoor-warm.png"
    r = rng(name)
    W, H = 1600, 2400
    X, Y = coords(W, H)
    d = np.hypot((X - 800) / 800, (Y - 1200) / 1200) / math.sqrt(2)
    img = solid(W, H, "#7a7a7a") * (1.05 - 0.3 * d ** 2)[..., None]
    orange = np.array(hexc("#ff9a3c"), F32)

    def tungsten(rgb, x0):
        rgb = _lit(rgb, x0, 0.8, 1.0, from_right=False)
        rgb = rgb * TUNGSTEN + orange * 0.1                             # ~30 % toward tungsten
        return np.clip((rgb - 118) * 1.35 + 118, 0, 255)

    hair = np.array(hexc(HAIR), F32)
    strand = tuple(np.clip(((hair * TUNGSTEN + orange * 0.1) - 118) * 1.35 + 118, 0, 255) * 0.8
                   + np.array(hexc("#7a7a7a")) * 0.2)
    _figure_on(img, 3, hexc("#7a7a7a"), 0.5, strand, tungsten)
    add_noise(img, 1.5, r)
    save_png(img, 4, name)


def m4_scene_hard_sun():
    name = "l13-scene-hard-sun.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = np.empty((H, W, 3), F32)
    img[:700] = vgrad(W, 700, [(0, "#6fa8e0"), (1, "#cfe3f5")])
    img[700:] = vgrad(W, 900, [(0, (222, 204, 166)), (1, "#d8c39a")])
    tex = r.standard_normal((900 // 3 + 1, W // 3 + 1), dtype=F32)
    tex = np.asarray(Image.fromarray(tex).resize((W, 900 + 3), Image.BICUBIC), F32)[:900]
    img[700:] += (tex * 5)[..., None]
    xs = np.arange(0, W + 9, 8)
    for base, amp, col, parts in ((560, 35, "#b8cbe0", [(900, 1, 0.3), (410, 0.5, 1.7)]),
                                  (615, 30, "#8fa98c", [(700, 1, 2.2), (330, 0.4, 0.9)]),
                                  (668, 22, "#5f8a4e", [(1100, 1, 4.0), (520, 0.5, 2.6)])):
        c = Canvas((0, 450, W, 720), ss=2)
        c.poly(list(zip(xs, smooth_wave(xs, base, amp, parts))) + [(W + 8, 712), (0, 712)])
        paint(img, c.mask(), col)

    def shadow(pts, v):
        hull = convex_hull(list(pts) + [(x + v[0], y + v[1]) for x, y in pts])
        xs_, ys_ = [p[0] for p in hull], [p[1] for p in hull]
        c = Canvas((min(xs_), min(ys_), max(xs_), max(ys_)), ss=3, pad=4)
        c.poly(hull)
        darken(img, c.mask(), 0.6)

    sdir = (-0.87, 0.49)
    crates = [(1700, 1050, 140), (600, 1300, 260)]
    for cx, base, s in crates:
        d = 0.3 * s
        dx, dy = d * 0.8, -d * 0.6
        fx0, fx1 = cx - s / 2, cx + s / 2
        foot = [(fx0, base), (fx1, base), (fx1 + dx, base + dy), (fx0 + dx, base + dy)]
        L = 0.8 * s
        shadow(foot, (sdir[0] * L, sdir[1] * L))
    L = 0.8 * 500
    shadow([(1192, 1400), (1208, 1400)], (sdir[0] * L, sdir[1] * L))

    for cx, base, s in crates:
        d = 0.3 * s
        dx, dy = d * 0.8, -d * 0.6
        fx0, fx1, top = cx - s / 2, cx + s / 2, base - s
        box = (fx0 - 2, top + dy - 2, fx1 + dx + 2, base + 2)
        haze = 0.12 if base < 1100 else 0.0
        for pts, col in (([(fx0, top), (fx1, top), (fx1 + dx, top + dy), (fx0 + dx, top + dy)], (228, 196, 146)),
                         ([(fx1, top), (fx1 + dx, top + dy), (fx1 + dx, base + dy), (fx1, base)], (201, 160, 106)),
                         ([(fx0, top), (fx1, top), (fx1, base), (fx0, base)], (150, 112, 70))):
            c = Canvas(box, ss=3)
            c.poly(pts)
            paint(img, c.mask(), lerp(col, (207, 227, 245), haze))
        c = Canvas(box, ss=3)
        for k in (1, 2):
            yy = top + s * k / 3
            c.rect(fx0 + 3, yy - s * 0.012, fx1 - 3, yy + s * 0.012)
        paint(img, c.mask(), lerp((112, 82, 50), (207, 227, 245), haze))
    c = Canvas((1188, 896, 1212, 1402), ss=3)
    c.rect(1192, 900, 1208, 1400)
    paint(img, c.mask(), (86, 70, 55))
    c = Canvas((1188, 896, 1212, 1402), ss=3)
    c.rect(1203, 900, 1208, 1400)
    paint(img, c.mask(), (170, 145, 115))
    add_noise(img, 2, r)
    save_jpg(img, 4, name)


# ======================================================================================
# MODULE 5: Design & Type
# ======================================================================================

POSTER_COPY = """POSTER BRIEF A: Summer Music Festival (the lesson's example)

Line 1 (title):      SUMMER
Line 2 (title):      MUSIC FESTIVAL
Line 3 (key detail): July 18 · Riverside Park
Line 4 (extras):     Live bands · Food trucks · All ages
Line 5 (fine print): TICKETS AT THE DOOR
Badge / path text:   EST · 2026 · LIVE
Sponsor:             Riverside Radio (logo: l16-sponsor-logo.png)

Document: 18 x 24 in at 150 ppi, dark background. Save as poster-working.psd.
Rules: every line its own type layer; 1st line boldly biggest; two fonts maximum;
one accent color on the most important line or a small "tickets" badge.

POSTER BRIEF B: Community Night Market (alternative)

Line 1 (title):      NIGHT MARKET
Line 2 (key detail): Friday, August 8 · 6 to 11 PM
Line 3 (place):      Old Town Square
Line 4 (extras):     Street food · Local makers · Live DJ
Line 5 (fine print): FREE ENTRY · FAMILY FRIENDLY
Badge / path text:   EVERY SECOND FRIDAY

Decide the reading order yourself before you size anything.
"""


def m5_poster_copy():
    save_txt(POSTER_COPY, 5, "l14-poster-copy.txt")


def m5_flat_type_before():
    W, H = 1800, 2400
    im = Image.new("RGB", (W, H), hexc("#14213d"))
    d = ImageDraw.Draw(im)
    f = font(64)
    lines = ["SUMMER", "MUSIC FESTIVAL", "July 18 · Riverside Park",
             "Live bands · Food trucks · All ages", "TICKETS AT THE DOOR"]
    for i, s in enumerate(lines):
        d.text((90, 90 + 72 * i), s, font=f, fill=(255, 255, 255))
    save_png(im, 5, "l14-flat-type-before.png")


def m5_pen_practice():
    W, H = 2400, 1600
    SS = 2
    c = Canvas((0, 0, W, H), ss=SS, mode="RGBA")
    c.rect(0, 0, W, H, (255, 255, 255))
    for x in (800, 1600):
        c.rect(x - 1, 0, x + 1, H, "#d6dee9")
    c.rect(0, 799, W, 801, "#d6dee9")
    gray, red, blue = "#8a94a3", "#e03131", "#31a8ff"

    def outline(pts, closed=True):
        pts = list(pts) + ([pts[0]] if closed else [])
        c.line(pts, 4, gray)

    def dots(pts):
        for x, y in pts:
            c.circle(x, y, 9, red)

    def arc(cx, cy, rad, a0, a1, n=48):
        return [(cx + rad * math.cos(math.radians(a)), cy + rad * math.sin(math.radians(a)))
                for a in np.linspace(a0, a1, n)]

    labels = ["LIGHTNING BOLT · 7 points · click only", "MOUNTAIN RANGE · 7 points · click only",
              "LEAF · 2 corners + 2 curves", "HEART · 4 points", "CLOUD · 5 bumps", "SOUNDWAVE · smooth"]
    centers = [(400 + 800 * (i % 3), 440 + 800 * (i // 3)) for i in range(6)]
    for (cx, cy), lab in zip(centers, labels):
        c.text(cx, cy - 360, lab, 28, fill=(40, 46, 56), anchor="mm")

    # 1 lightning bolt (7 points)
    cx, cy = centers[0]
    bolt = [(cx + 40, cy - 280), (cx - 140, cy + 30), (cx - 10, cy + 30), (cx - 80, cy + 280),
            (cx + 150, cy - 70), (cx + 20, cy - 70), (cx + 130, cy - 280)]
    outline(bolt); dots(bolt)
    # 2 mountain range (7 points: 3 peaks, closed along the bottom)
    cx, cy = centers[1]
    mtn = [(cx - 280, cy + 200), (cx - 170, cy - 60), (cx - 90, cy + 40), (cx + 10, cy - 230),
           (cx + 110, cy - 10), (cx + 190, cy - 110), (cx + 280, cy + 200)]
    outline(mtn); dots(mtn)
    # 3 leaf (2 corners + 2 curves)
    cx, cy = centers[2]
    tip, stem = np.array((cx + 200, cy - 200)), np.array((cx - 200, cy + 200))
    mid = (tip + stem) / 2
    nrm = np.array((1, 1)) / math.sqrt(2)
    side1 = quad_bezier(stem, mid + nrm * 330, tip, 64)
    side2 = quad_bezier(tip, mid - nrm * 330, stem, 64)
    outline(side1 + side2[1:])
    c.line([tuple(stem + (stem - tip) * 0.12), tuple(tip - (tip - stem) * 0.08)], 3, gray)
    dots([tuple(tip), tuple(stem), tuple(mid + nrm * 165), tuple(mid - nrm * 165)])
    # 4 heart
    cx, cy = centers[3]
    t = np.linspace(0, 2 * np.pi, 400)
    hx = 16 * np.sin(t) ** 3
    hy = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    sc = 17
    heart = list(zip(cx + hx * sc, cy - 20 + hy * sc))
    outline(heart)
    dots([(cx, cy - 20 - 5 * sc), (cx, cy - 20 + 17 * sc), (cx - 16 * sc, cy - 20 - 3.7 * sc),
          (cx + 16 * sc, cy - 20 - 3.7 * sc)])
    # 5 cloud (5 bumps on a flat bottom)
    cx, cy = centers[4]
    by = cy + 130
    bumps = [(cx - 200, by - 70, 90), (cx - 100, by - 170, 110), (cx + 30, by - 200, 120),
             (cx + 150, by - 140, 100), (cx + 220, by - 60, 70)]
    pts = []

    def circ_int(c1, c2):
        (x1, y1, r1), (x2, y2, r2) = c1, c2
        dd = math.hypot(x2 - x1, y2 - y1)
        a = (r1 ** 2 - r2 ** 2 + dd ** 2) / (2 * dd)
        hh = math.sqrt(max(r1 ** 2 - a ** 2, 0))
        mx, my = x1 + a * (x2 - x1) / dd, y1 + a * (y2 - y1) / dd
        p1 = (mx + hh * (y2 - y1) / dd, my - hh * (x2 - x1) / dd)
        p2 = (mx - hh * (y2 - y1) / dd, my + hh * (x2 - x1) / dd)
        return p1 if p1[1] < p2[1] else p2

    starts = [(cx - 280, by)] + [circ_int(bumps[i], bumps[i + 1]) for i in range(4)] + [(cx + 290, by)]
    starts[0] = (bumps[0][0] - math.sqrt(bumps[0][2] ** 2 - (by - bumps[0][1]) ** 2), by)
    starts[-1] = (bumps[4][0] + math.sqrt(bumps[4][2] ** 2 - (by - bumps[4][1]) ** 2), by)
    for i, (bx, byy, br) in enumerate(bumps):
        a0 = math.degrees(math.atan2(starts[i][1] - byy, starts[i][0] - bx))
        a1 = math.degrees(math.atan2(starts[i + 1][1] - byy, starts[i + 1][0] - bx))
        while a1 < a0:
            a1 += 360
        pts += arc(bx, byy, br, a0, a1, 60)[1:]
    outline(pts)
    dots(starts)
    # 6 soundwave (3 periods, open)
    cx, cy = centers[5]
    xs = np.linspace(cx - 280, cx + 280, 400)
    ys = cy - 130 * np.sin((xs - (cx - 280)) / 560 * 3 * 2 * np.pi)
    c.line(list(zip(xs, ys)), 4, gray)
    pk = [(cx - 280 + 560 / 12 * (1 + 2 * k), cy - 130 * (1 if k % 2 == 0 else -1)) for k in range(6)]
    for (px, py) in (pk[0], pk[3]):
        c.line([(px - 70, py), (px + 70, py)], 3, blue)
        c.circle(px - 70, py, 6, blue)
        c.circle(px + 70, py, 6, blue)
    dots(pk)
    L = c.layer()
    save_png(to_u8(L.rgb), 5, "l15-pen-practice.png")


def m5_logo_to_rebuild():
    W = H = 1200
    c = Canvas((0, 0, W, H), ss=3, mode="RGBA")
    c.rect(0, 0, W, H, (255, 255, 255))
    c.circle(600, 520, 300, "#f08a3c")
    c.circle(690, 450, 230, (255, 255, 255))
    c.rrect(280, 835, 920, 925, 45, "#14213d")
    # inset: 250 x 250 box, top-left (935, 935)
    bx, by, bs = 935, 935, 250
    c.rect(bx, by, bx + bs, by + bs, (160, 160, 160))
    c.rect(bx + 1, by + 1, bx + bs - 1, by + bs - 1, (255, 255, 255))
    c.text(bx + bs / 2, by + 20, "HOW IT'S BUILT", 17, bold=True, fill=(110, 110, 110), anchor="mm")
    s = 0.25
    ox, oy = bx + bs / 2 - 600 * s, by + 58 - 220 * s

    def dashed(pts, col, dash=7, gap=5):
        pts = np.array(pts, float)
        seg = np.hypot(*np.diff(pts, axis=0).T)
        dist = np.concatenate([[0], np.cumsum(seg)])
        tot, pos = dist[-1], 0.0
        while pos < tot:
            e = min(pos + dash, tot)
            tt = np.linspace(pos, e, 6)
            xs = np.interp(tt, dist, pts[:, 0])
            ys = np.interp(tt, dist, pts[:, 1])
            c.line(list(zip(xs, ys)), 1.6, col)
            pos += dash + gap

    def circ(cx_, cy_, rr):
        a = np.linspace(0, 2 * np.pi, 180)
        return list(zip(ox + (cx_ + rr * np.cos(a)) * s, oy + (cy_ + rr * np.sin(a)) * s))

    dashed(circ(600, 520, 300), "#f08a3c")
    dashed(circ(690, 450, 230), "#8a94a3")
    bar = []
    for (ccx, a0, a1) in ((875, -90, 90), (325, 90, 270)):
        a = np.radians(np.linspace(a0, a1, 30))
        bar += list(zip(ccx + 45 * np.cos(a), 880 + 45 * np.sin(a)))
    bar.append(bar[0])
    dashed([(ox + x * s, oy + y * s) for x, y in bar], "#14213d")
    save_png(to_u8(c.layer().rgb), 5, "l15-logo-to-rebuild.png")


def m5_hero_stage():
    name = "l16-hero-stage.jpg"
    r = rng(name)
    W, H = 2700, 3600
    img = vgrad(W, H, [(0, "#120a24"), (0.7, "#3a1a5e"), (1, (0, 0, 0))])
    beams = [(450, (255, 255, 255)), (1000, (170, 235, 255)), (1500, (255, 150, 230)),
             (2000, (255, 255, 255)), (2350, (170, 235, 255))]
    for i, (bx, col) in enumerate(beams):
        tx = bx + r.uniform(-900, 900)
        spread = r.uniform(260, 460)
        c = Canvas((0, 0, W, H), ss=1)
        c.poly([(bx - 12, -40), (bx + 12, -40), (tx + spread, 3000), (tx - spread, 3000)])
        paint(img, c.mask(blur=30), col, r.uniform(0.10, 0.18))
    c = Canvas((1350 - 900, 2900 - 250, 1350 + 900, 2900 + 250), ss=1, pad=260)
    c.ellipse(1350, 2900, 900, 250)
    paint(img, c.mask(blur=110), (255, 110, 110), 0.75)
    c = Canvas((1350 - 500, 2900 - 120, 1350 + 500, 2900 + 120), ss=1, pad=120)
    c.ellipse(1350, 2920, 500, 110)
    paint(img, c.mask(blur=80), (255, 170, 90), 0.5)

    c = Canvas((0, 2600, W, H), ss=2)
    n = 31
    for i in range(n):
        x = (i + 0.5) * W / n + r.uniform(-25, 25)
        rad = r.uniform(45, 60)
        hy = r.uniform(2960, 3160)
        c.circle(x, hy, rad)
        c.rrect(x - 2.5 * rad, hy + 0.9 * rad, x + 2.5 * rad, H + 80, rad * 1.1)
    for i in r.choice(n, size=7, replace=False):
        x = (i + 0.5) * W / n
        hy, side = 3040, (1 if r.random() < 0.5 else -1)
        sx, sy = x + side * 95, hy + 90
        ex, ey = sx + side * r.uniform(20, 90), hy - r.uniform(170, 260)
        c.line([(sx, sy), (ex, ey)], 24, round_caps=True)
        c.circle(ex, ey, 20)
    paint(img, c.mask(), (0, 0, 0))
    add_uniform_noise(img, 4, r)
    save_jpg(img, 5, name)


def m5_sponsor_logo():
    W = H = 800
    c = Canvas((0, 0, W, H), ss=4)
    c.circle(400, 330, 300)
    c.circle(400, 330, 272, 0)
    xs = np.linspace(400 - 215, 400 + 215, 300)
    ys = 330 - 55 * np.sin((xs - (400 - 215)) / 430 * 3 * 2 * np.pi)
    c.line(list(zip(xs, ys)), 12, round_caps=True)
    f = font(64 * 4, bold=True)
    txt, track = "RIVERSIDE RADIO", 8
    widths = [f.getlength(ch) / 4 for ch in txt]
    total = sum(widths) + track * (len(txt) - 1)
    x = 400 - total / 2
    bb = f.getbbox("RIVERSIDE RADIO", anchor="ls")
    base_y = 720 - (bb[1] + bb[3]) / 2 / 4
    for ch, wch in zip(txt, widths):
        c.d.text(c.P(x, base_y), ch, font=f, fill=255, anchor="ls")
        x += wch + track
    a = to_u8(c.mask().a * 255)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = a
    save_png(Image.fromarray(rgba, "RGBA"), 5, "l16-sponsor-logo.png")


# ======================================================================================
# MODULE 6: AI & Speed
# ======================================================================================

def m6_lake_sign():
    name = "l17-lake-sign.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = np.empty((H, W, 3), F32)
    img[:900] = vgrad(W, 900, [(0, "#7fbce8"), (1, "#cfe8f6")])
    img[900:950] = hexc("#6ea86a")
    img[950:] = vgrad(W, 650, [(0, "#3f7fae"), (1, "#2b6088")])
    c = Canvas((1870, 150, 2130, 410), pad=20)
    c.circle(2000, 280, 130)
    paint(img, c.mask(blur=6), "#fff4cf")
    c = Canvas((0, 820, W, 960), ss=3)
    xs = np.arange(0, W + 9, 8)
    c.poly(list(zip(xs, smooth_wave(xs, 880, 6, [(600, 1, 0), (170, 0.4, 1)]))) + [(W + 8, 952), (0, 952)])
    paint(img, c.mask(), "#6ea86a")
    c = Canvas((0, 820, 0.4 * W, 960), ss=3)
    for _ in range(9):
        x = r.uniform(40, 0.4 * W - 60)
        c.ellipse(x, 900, r.uniform(45, 110), r.uniform(22, 40))
    paint(img, c.mask(), "#4f8a4c")
    for _ in range(40):
        y, x, ln = r.uniform(965, 1590), r.uniform(0, W), r.uniform(60, 240)
        if 300 < x < 1100 and 1000 < y < 1400:
            x = r.uniform(1150, W)                                   # keep the add-space calm
        c = Canvas((x, y - 2, x + ln, y + 2), ss=2, pad=2)
        c.rect(x, y - 1, x + ln, y + 1)
        paint(img, c.mask(), "#5a95c2", 0.85)
    # the signpost (flaw)
    img[640:940, 1540:1570] = hexc("#5b4636")
    img[600:720, 1440:1670] = hexc("#c0392b")
    img[610:710, 1450:1660] = hexc("#e8e2d0")
    for k, (x1) in enumerate((1630, 1600, 1560)):
        y = 630 + k * 26
        img[y:y + 12, 1475:x1] = (85, 85, 88)
    add_noise(img, 4, r, mono=True)
    save_jpg(img, 6, name, quality=92)


def m6_three_distractions():
    name = "l17-three-distractions.jpg"
    r = rng(name)
    W, H = 2400, 1600
    img = np.empty((H, W, 3), F32)
    img[:700] = vgrad(W, 700, [(0, "#9cc9ee"), (1, "#e6f2fb")])
    img[700:900] = hexc("#3b86b5")
    img[900:] = vgrad(W, 700, [(0, "#e9d7a8"), (1, "#d6bf86")])
    for _ in range(30):
        y, x, ln = r.uniform(705, 895), r.uniform(0, W), r.uniform(80, 260)
        c = Canvas((x, y - 2, x + ln, y + 2), ss=2, pad=2)
        c.rect(x, y - 1, x + ln, y + 1)
        paint(img, c.mask(), (120, 175, 210), 0.6)
    # cone
    c = Canvas((380, 1250, 700, 1340), ss=2, pad=20)
    c.poly([(575, 1300), (430, 1300), (690, 1330), (610, 1300)])
    darken(img, c.mask(blur=8), 0.3)
    c = Canvas((420, 1070, 580, 1305), ss=3)
    c.poly([(425, 1300), (575, 1300), (500, 1080)])
    cone = c.mask()
    paint(img, cone, "#f28c28")
    c = Canvas((420, 1070, 580, 1305), ss=3)
    c.rect(400, 1160, 600, 1180)
    c.rect(400, 1225, 600, 1245)
    paint(img, Mask(cone.x, cone.y, c.mask().a * cone.a), (255, 255, 255))
    # trash can
    c = Canvas((1880, 1230, 2050, 1270), ss=2, pad=20)
    c.poly([(1880, 1250), (1880, 1230), (2010, 1255), (1990, 1265)])
    darken(img, c.mask(blur=8), 0.35)
    img[990:1250, 1700:1880] = hgrad(180, 260, [(0, (140, 145, 151)), (0.4, "#7d8288"), (1, (100, 105, 110))])
    img[975:1005, 1690:1890] = hexc("#5d6268")
    # power line
    xs = np.linspace(0, W, 400)
    ys = np.polyval(np.polyfit([0, 1200, 2400], [180, 300, 160], 2), xs)
    c = Canvas((0, 140, W, 320), ss=3)
    c.line(list(zip(xs, ys)), 5)
    paint(img, c.mask(), (0, 0, 0))
    add_noise(img, 5, r, mono=True)
    save_jpg(img, 6, name, quality=92)


def m6_tight_portrait():
    name = "l18-tight-portrait.jpg"
    r = rng(name)
    W, H = 1200, 1600
    img = np.empty((H, W, 3), F32)
    img[:880] = vgrad(W, 880, [(0, "#86b7e3"), (1, "#dcebf7")])
    img[880:] = vgrad(W, 720, [(0, "#4a86b3"), (1, "#2e5f86")])
    for pts, col in (([(-50, 760), (180, 610), (380, 700), (620, 600), (880, 690), (1080, 620), (1260, 700)], "#6f86a3"),
                     ([(-50, 800), (120, 700), (300, 760), (520, 660), (760, 740), (980, 670), (1260, 760)], "#5d7290")):
        c = Canvas((0, 560, W, 882), ss=3)
        c.poly(pts + [(1260, 881), (-50, 881)])
        paint(img, c.mask(), col)
    c = Canvas((960, 690, W, 1530), ss=3)
    c.rect(1025, 1250, 1072, 1520)
    c.rect(1088, 1250, 1135, 1520)
    paint(img, c.mask(), "#2c3e50")
    c = Canvas((960, 690, W, 1530), ss=3)
    c.rrect(1010, 820, 1150, 1260, 30)
    paint(img, c.mask(), "#c0392b")
    c = Canvas((960, 690, W, 1530), ss=3)
    c.circle(1080, 760, 60)
    paint(img, c.mask(), "#f0c8a0")
    add_noise(img, 4, r, mono=True)
    save_jpg(img, 6, name, quality=92)


def m6_horizon_strip():
    name = "l18-horizon-strip.jpg"
    r = rng(name)
    W, H = 900, 1200
    img = np.empty((H, W, 3), F32)
    img[:600] = vgrad(W, 600, [(0, "#f3b37a"), (1, "#fbe3c4")])
    img[600:] = vgrad(W, 600, [(0, "#6b8e4e"), (1, "#4d6b36")])
    c = Canvas((0, 600, W, H), ss=3)

    def rail_y(x, off=0):
        return 1100 + (760 - 1100) * x / 900 + off
    for x in range(0, 901, 90):
        c.rect(x - 4, rail_y(x, -70), x + 4, rail_y(x, 40))
    for off in (0, -48):
        c.line([(-10, rail_y(-10, off)), (W + 10, rail_y(W + 10, off))], 3)
    paint(img, c.mask(), "#4a3526")
    add_noise(img, 3, r, mono=True)
    save_jpg(img, 6, name, quality=92)


BATCH = [
    ("01", 4000, 3000, "#1473E6", "#31A8FF", "icc"),
    ("02", 3000, 4000, "#8e44ad", "#e056fd", "icc"),
    ("03", 2400, 2400, "#16a085", "#48c9b0", "icc"),
    ("04", 6000, 4000, "#d35400", "#f5b041", "icc"),
    ("05", 1600, 2400, "#2c3e50", "#5d6d7e", "none"),
    ("06", 5000, 2000, "#c0392b", "#f1948a", "icc"),
    ("07", 800, 600, "#27ae60", "#82e0aa", "icc"),
    ("08", 3000, 2000, "#7f8c8d", "#bdc3c7", "gray"),
]


def _batch_file(num, W, H, c0, c1, prof):
    c0, c1 = np.array(hexc(c0), F32), np.array(hexc(c1), F32)
    t = ((np.arange(W, dtype=F32)[None, :] / W + np.arange(H, dtype=F32)[:, None] / H) / 2)
    img = np.empty((H, W, 3), np.uint8)
    for ch in range(3):
        img[..., ch] = to_u8(c0[ch] + (c1[ch] - c0[ch]) * t)
    del t
    short = min(W, H)
    # circle, 20 % of the short edge, lower-left quadrant (analytic anti-aliasing)
    rad = 0.1 * short
    cx, cy = W * 0.2, H * 0.78
    x0, y0, x1, y1 = int(cx - rad - 2), int(cy - rad - 2), int(cx + rad + 3), int(cy + rad + 3)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(F32)
    a = np.clip(rad - np.hypot(xx + 0.5 - cx, yy + 0.5 - cy) + 0.5, 0, 1)[..., None]
    sub = img[y0:y1, x0:x1].astype(F32)
    img[y0:y1, x0:x1] = to_u8(sub * (1 - a) + 255 * a)
    b = 24
    img[:b], img[-b:], img[:, :b], img[:, -b:] = 255, 255, 255, 255
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    f = font(int(0.3 * short / 0.73), bold=True)
    d.text((W / 2, H / 2), num, font=f, fill=(255, 255, 255), anchor="mm",
           stroke_width=4, stroke_fill=(30, 30, 35))
    name = f"l19-batch-{num}.jpg"
    p = out_path(6, f"l19-input/{name}")
    if prof == "gray":
        im.convert("L").save(p, "JPEG", quality=92, dpi=(72, 72), optimize=True)
    elif prof == "none":
        im.save(p, "JPEG", quality=92, dpi=(72, 72), optimize=True)
    else:
        im.save(p, "JPEG", quality=92, dpi=(72, 72), optimize=True, icc_profile=SRGB_ICC)
    _record(p)


def m6_batch_inputs():
    for spec in BATCH:
        _batch_file(*spec)


def m6_watermark():
    W, H = 600, 150
    txt = "© PRACTICE"
    size = 96
    while True:
        f = font(size, bold=True)
        bb = f.getbbox(txt, anchor="mm")
        if bb[2] - bb[0] <= W - 24:
            break
        size -= 2
    fill = Image.new("L", (W, H), 0)
    ImageDraw.Draw(fill).text((W / 2, H / 2), txt, font=f, fill=255, anchor="mm")
    stroke = Image.new("L", (W, H), 0)
    ImageDraw.Draw(stroke).text((W / 2, H / 2), txt, font=f, fill=255, anchor="mm",
                                stroke_width=2, stroke_fill=255)
    fa = np.asarray(fill, F32) / 255
    ring = np.clip(np.asarray(stroke, F32) / 255 - fa, 0, 1)
    A = 140 * fa + 120 * ring
    col = 255 * fa / np.maximum(fa + ring, 1e-6)
    rgba = np.zeros((H, W, 4), F32)
    rgba[..., :3] = col[..., None]
    rgba[..., 3] = A
    rgba[..., :3] *= (A > 0)[..., None]
    save_png(Image.fromarray(to_u8(rgba), "RGBA"), 6, "l19-watermark.png")


# ======================================================================================
# MODULE 7: Capstone
# ======================================================================================

def m7_old_photo():
    name = "l21-backup-old-photo.jpg"
    r = rng(name)
    W, H = 2400, 1800
    img = np.empty((H, W, 3), F32)
    img[:1400] = vgrad(W, 1400, [(0, (120, 160, 205)), (1, (215, 225, 235))])
    img[1400:] = vgrad(W, 400, [(0, (110, 140, 80)), (1, (70, 95, 50))])
    c = Canvas((1860, 1000, 1940, 1420), ss=3)
    c.rect(1870, 950, 1930, 1410)
    paint(img, c.mask(), (95, 70, 50))
    c = Canvas((1620, 520, 2180, 1080), ss=3)
    c.circle(1900, 800, 260)
    paint(img, c.mask(), (60, 105, 60))
    c = Canvas((650, 520, 1550, 1420), ss=3)
    c.rect(700, 800, 1500, 1400)
    paint(img, c.mask(), (205, 190, 165))
    c = Canvas((650, 520, 1550, 1420), ss=3)
    c.poly([(660, 805), (1540, 805), (1100, 550)])
    paint(img, c.mask(), (120, 70, 60))
    img[1080:1400, 1040:1160] = (90, 60, 45)                         # door
    for wx in (820, 1260):
        img[950:1130, wx:wx + 140] = (70, 80, 95)                    # windows
        img[1036:1044, wx:wx + 140] = (205, 190, 165)
        img[950:1130, wx + 66:wx + 74] = (205, 190, 165)

    g = img @ np.array([0.299, 0.587, 0.114], F32)
    g = 70 + g * (205 - 70) / 255                                     # faded levels
    img = np.clip(np.stack([g * 1.0, g * 0.86, g * 0.66], -1), 0, 255)
    X, Y = coords(W, H)
    rr = np.hypot(X - W / 2, Y - H / 2) / math.hypot(W / 2, H / 2)
    ang = np.cos(np.arctan2(-(Y - H / 2), X - W / 2) - math.atan2(H / 2, W / 2))
    fade = 1 - 0.18 * rr ** 1.3 * np.clip(0.5 + 0.5 * ang, 0, 1) ** 1.5
    img *= fade[..., None]

    c = Canvas((0, 0, W, H), ss=2)
    for k in range(12):
        ln = r.uniform(300, 1500)
        if k < 2:
            x, y = r.uniform(760, 1440), r.uniform(700, 900)
        else:
            x, y = r.uniform(60, W - 60), r.uniform(0, H - ln * 0.6)
        a = math.radians(90 + r.uniform(-8, 8))
        pts = [(x + ln * t * math.cos(a) + 4 * math.sin(t * 9), y + ln * t * math.sin(a)) for t in np.linspace(0, 1, 30)]
        c.line(pts, r.uniform(1, 3), r.uniform(0.6, 0.95) * 255)
    paint(img, c.mask(blur=0.5), "#f4ecdc")
    for col in ("#3a2e22", "#f6eedf"):
        c = Canvas((0, 0, W, H), ss=2)
        for _ in range(75):
            c.circle(r.uniform(0, W), r.uniform(0, H), r.uniform(2, 6))
        paint(img, c.mask(blur=0.6), col, 0.9)

    b = 40
    img[:b], img[-b:], img[:, :b], img[:, -b:] = [hexc("#efe6d2")] * 4
    n = int(r.integers(10, 16))
    edge = [(0, 1550)]
    for i in range(1, n + 1):
        t = i / (n + 1)
        edge.append((260 * t + r.uniform(-18, 18), 1550 + 250 * t + r.uniform(-18, 18)))
    edge.append((260, 1800))
    c = Canvas((0, 1500, 320, H), ss=3)
    c.poly(edge + [(0, 1810)])
    paint(img, c.mask(), "#f8f4ea")
    add_noise(img, 7, r)
    save_jpg(img, 7, name, quality=92, dpi=300)


def m7_product():
    name = "l21-backup-product.jpg"
    r = rng(name)
    W = H = 2400
    img = vgrad(W, H, [(0, "#d9dcdf"), (1, "#c9cdd1")])
    c = Canvas((760, 1660, 1540, 1760), ss=1, pad=60)
    c.ellipse(1150, 1710, 390, 50)
    paint(img, c.mask(blur=25), "#9aa0a6")
    box = (740, 720, 1760, 1720)
    c = Canvas(box, ss=3)
    c.ellipse(1580, 1250, 140, 250)
    c.ellipse(1580, 1250, 70, 180, 0)
    paint(img, c.mask(), (40, 92, 160))
    c = Canvas(box, ss=3)
    c.rrect(800, 800, 1500, 1700, 60)
    body = c.mask()
    paint(img, body, hgrad(W, H, [(0, "#2f6db5"), (0.5, "#5b95d8"), (1, "#2f6db5")], 800, 1500))
    c = Canvas(box, ss=2)
    c.rect(930, 860, 970, 1640)
    hl = c.mask(blur=12)
    paint(img, Mask(hl.x, hl.y, hl.a * body.a), (255, 255, 255), 0.55)
    c = Canvas(box, ss=3)
    c.ellipse(1150, 800, 350, 40)
    paint(img, c.mask(), "#244f86")
    c = Canvas(box, ss=3)
    c.ellipse(1150, 803, 322, 28)
    paint(img, c.mask(), "#1b3c66")
    add_noise(img, 3, r, mono=True)
    save_jpg(img, 7, name, quality=92)


def m7_backdrop():
    name = "l21-backup-backdrop.jpg"
    r = rng(name)
    W, H = 3000, 2000
    ty = 1200
    img = np.empty((H, W, 3), F32)
    img[:ty] = vgrad(W, ty, [(0, "#f3e9dc"), (1, "#e2d2bd")])
    img[ty:] = hexc("#9b6a43")
    for k in range(30):
        y0 = ty + 10 + (1950 - ty - 10) * (k + r.uniform(0.1, 0.9)) / 30
        xs = np.linspace(-20, W + 20, 120)
        ys = y0 + 3 * np.sin(xs / r.uniform(180, 420) + r.uniform(0, 6))
        col = lerp(hexc("#86573a"), hexc("#b07d55"), r.random())
        c = Canvas((0, y0 - 8, W, y0 + 8), ss=2)
        c.line(list(zip(xs, ys)), r.uniform(1, 3))
        paint(img, c.mask(), col)
    img[1960:] = hexc("#b07d55")
    img[ty:ty + 4] *= 0.8
    f = np.linspace(1.0, 0.85, W, dtype=F32)
    img *= f[None, :, None]
    add_noise(img, 4, r, mono=True)
    save_jpg(img, 7, name, quality=92)


def m7_sky():
    name = "l21-backup-sky.jpg"
    r = rng(name)
    W, H = 3000, 2000
    img = vgrad(W, H, [(0, "#1e2a55"), (0.6, "#c65f6a"), (1, "#f2b56b")])
    for _ in range(25):
        cx, cy = r.uniform(-100, W + 100), r.uniform(0.3 * H, 0.9 * H)
        cw = r.uniform(250, 600)
        c = Canvas((cx - cw, cy - cw / 2, cx + cw, cy + cw / 2), ss=1, mode="RGBA", pad=70)
        for _ in range(int(r.integers(4, 9))):
            col = (255, 255, 255) if r.random() < 0.5 else (255, 215, 225)
            c.ellipse(cx + r.uniform(-0.45, 0.45) * cw, cy + r.uniform(-0.12, 0.12) * cw,
                      r.uniform(0.15, 0.35) * cw, r.uniform(0.06, 0.13) * cw,
                      col + (int(r.integers(90, 161)),))
        over(img, c.layer(blur=r.uniform(18, 30)))
    add_noise(img, 3, r, mono=True)
    save_jpg(img, 7, name, quality=92)


def _mockup(name, frame, opening):
    r = rng(name)
    W, H = 3000, 2000
    img = np.empty((H, W, 3), F32)
    img[:1650] = vgrad(W, 1650, [(0, "#e9e4dc"), (1, "#d8d1c5")])
    X, Y = coords(W, 1650)
    d = np.hypot((X - 1500) / 1300, (Y - 500) / 900)
    pool = (np.clip(1 - d, 0, 1) ** 2 * 60 / 255)[..., None]
    img[:1650] = img[:1650] * (1 - pool) + 255 * pool
    img[1650:] = vgrad(W, 350, [(0, (150, 118, 88)), (1, "#8a6a4e")])
    img[1650:1656] = hexc("#5e4a38")
    fx0, fy0, fx1, fy1 = frame
    c = Canvas(frame, ss=1, pad=90)
    c.rect(fx0 + 18, fy0 + 18, fx1 + 18, fy1 + 18)
    darken(img, c.mask(blur=30), 70 / 255)
    img[fy0:fy1, fx0:fx1] = hexc("#2b2b2b")
    img[fy0 + 40:fy1 - 40, fx0 + 40:fx1 - 40] = (250, 250, 247)
    ox0, oy0, ox1, oy1 = opening
    img[oy0:oy1, ox0:ox1] = hexc("#9a9a9a")
    add_noise(img, 2, r, mono=True)
    save_jpg(img, 7, name, quality=92)


def m7_mockup_wall():
    _mockup("l22-mockup-wall.jpg", (1050, 260, 1950, 1460), (1150, 360, 1850, 1360))


def m7_mockup_wall_landscape():
    # README gives frame y 380-1220, which cannot hold a 1000 x 700 opening with the same
    # 100 px frame + mat border; the frame grows to y 330-1270 so the opening stays 1000 x 700.
    _mockup("l22-mockup-wall-landscape.jpg", (900, 330, 2100, 1270), (1000, 450, 2000, 1150))


# ======================================================================================
# Registry and CLI
# ======================================================================================

MODULES = {
    0: [m0_tilted_horizon, m0_too_bright],
    1: [m1_washed_sky, m1_spotlight_object, m1_subject_busy_bg, m1_calm_background,
        m1_fuzzy_subject, m1_other_scene, m1_dusty_sky, m1_photobomb],
    2: [m2_flat_cast, m2_green_indoor, m2_flat_landscape, m2_tone_ramp, m2_badge_crisp,
        m2_subject_busy_bg],
    3: [m3_portrait_blemishes, m3_flaw_map, m3_portrait_blotchy, m3_skin_swatch, m3_portrait_flat],
    4: [m4_figure_on_green, m4_pet_on_blue_wall, m4_figure_cutout_reference, m4_scene_sunset,
        m4_scene_overcast, m4_subject_indoor_warm, m4_scene_hard_sun],
    5: [m5_poster_copy, m5_flat_type_before, m5_pen_practice, m5_logo_to_rebuild,
        m5_hero_stage, m5_sponsor_logo],
    6: [m6_lake_sign, m6_three_distractions, m6_tight_portrait, m6_horizon_strip,
        m6_batch_inputs, m6_watermark],
    7: [m7_old_photo, m7_product, m7_backdrop, m7_sky, m7_mockup_wall, m7_mockup_wall_landscape],
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--module", type=int, action="append", choices=sorted(MODULES),
                    help="build only this module (repeat for several)")
    args = ap.parse_args(argv)
    for mod in (args.module or sorted(MODULES)):
        print(f"Module {mod}:")
        for fn in MODULES[mod]:
            fn()
    total = sum(p.stat().st_size for p in WRITTEN)
    print(f"{len(WRITTEN)} files, {total / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
