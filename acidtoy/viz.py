"""milkdrop-grade math in the terminal. dark. toxic. audio-reactive."""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip

from acidtoy.live import Meter

PRESETS = ("toxic", "tunnel", "julia", "waste", "grid")


def _rgb(x, y):
    return np.zeros((y.shape[0], x.shape[1], 3), dtype=np.float32)


def paint(h: int, w: int, t: float, meter: Meter, preset: str) -> np.ndarray:
    h = max(h, 2)
    w = max(w, 2)
    if h % 2:
        h += 1
    y = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    x = np.linspace(-1.0 * w / h, 1.0 * w / h, w, dtype=np.float32)[None, :]
    bass = meter.rms * 4.0 + meter.kick * 0.6
    cut = meter.cutoff
    kick = meter.kick
    name = preset if preset in PRESETS else "toxic"
    fn = {"toxic": _toxic, "tunnel": _tunnel, "julia": _julia, "waste": _waste, "grid": _grid}[name]
    rgb = fn(x, y, t, bass, cut, kick, meter.drive)
    if kick > 0.4:
        rgb = np.clip(rgb + kick * 0.18, 0, 1)
    return (rgb * 255).astype(np.uint8)


def _toxic(x, y, t, bass, cut, kick, drive):
    r = np.sqrt(x * x + y * y) + 1e-5
    a = np.arctan2(y, x)
    k = 3.2 + bass * 10.0
    v = (
        np.sin(x * k + t * 1.3)
        + np.sin(y * (k * 1.17) - t * 0.9)
        + np.sin(r * (7.0 + cut * 8.0) - t * 2.1 + a * (5 + 3 * drive))
    ) / 3.0
    v = 0.5 + 0.5 * v
    v = np.power(np.clip(v, 0, 1), 1.6)
    g = np.clip(v * 0.15 + (v ** 3) * 0.9, 0, 1)
    b = np.clip(v * 0.35 + (1 - r) * 0.2, 0, 1)
    rr = np.clip(v * 0.08 + kick * 0.4, 0, 1)
    violet = np.stack((rr * 0.4 + b * 0.55, g * 0.2 + b * 0.15, np.clip(0.4 + v * 0.8, 0, 1)), -1)
    toxic = np.stack((g * 0.35, g, g * 0.12), -1)
    rgb = violet * (1 - v)[..., None] + toxic * v[..., None]
    rgb *= (0.35 + 0.65 * v)[..., None]
    rgb[..., 0] *= 0.35
    return np.clip(rgb, 0, 1)


def _tunnel(x, y, t, bass, cut, kick, drive):
    r = np.sqrt(x * x + y * y) + 1e-5
    a = np.arctan2(y, x)
    z = 0.18 / r + t * (0.35 + bass)
    stripes = np.sin(z * (10 + cut * 14) + a * 8)
    walls = np.sin(a * 6 + t) * 0.5 + 0.5
    v = np.clip(0.5 + 0.5 * stripes, 0, 1) * walls
    v *= np.clip(1.2 - r, 0, 1)
    hole = np.clip(0.12 / r, 0, 1)
    rgb = _rgb(x, y)
    rgb[..., 0] = v * 0.55 + hole * 0.8
    rgb[..., 1] = v * 0.05
    rgb[..., 2] = v * 0.25 + hole * 0.3
    rgb *= 0.25 + drive * 0.5
    return np.clip(rgb, 0, 1)


def _julia(x, y, t, bass, cut, kick, drive):
    zx = x * (1.45 - bass * 0.3)
    zy = y * (1.45 - bass * 0.3)
    cx = -0.4 + 0.38 * math.sin(t * 0.23)
    cy = 0.6 * math.cos(t * 0.19 + cut)
    for _ in range(6):
        nx = zx * zx - zy * zy + cx
        zy = 2.0 * zx * zy + cy
        zx = nx
    m = np.sqrt(zx * zx + zy * zy)
    v = np.clip(1.2 - np.log(m + 1.0) * 0.55, 0, 1)
    rgb = _rgb(x, y)
    rgb[..., 0] = v * 0.35
    rgb[..., 1] = v * 0.08
    rgb[..., 2] = v * 0.85 + (1 - v) * 0.05
    rgb *= 0.4 + drive * 0.5
    return np.clip(rgb, 0, 1)


def _waste(x, y, t, bass, cut, kick, drive):
    r = np.sqrt(x * x + y * y) + 1e-5
    a = np.arctan2(y, x)
    sludge = np.sin(r * 9 - t * 1.6) * np.cos(a * 4 + t * 0.7)
    drip = np.sin(y * 12 + t * 2 + np.sin(x * 8 + t))
    v = 0.5 + 0.5 * (0.6 * sludge + 0.4 * drip)
    v = np.power(np.clip(v, 0, 1), 1.4)
    rgb = _rgb(x, y)
    rgb[..., 0] = v * 0.55 + kick * 0.2
    rgb[..., 1] = v * 0.95
    rgb[..., 2] = v * 0.08 + (1 - r) * 0.15 * cut
    rgb *= (0.3 + 0.7 * v * drive)[..., None]
    return np.clip(rgb, 0, 1)


def _grid(x, y, t, bass, cut, kick, drive):
    z = 0.35 + y * 0.85
    z = np.where(z < 0.08, 0.08, z)
    u = x / z
    v = (0.6 + 0.4 * math.sin(t * 0.2)) / z + t * (0.4 + bass)
    gx = np.abs(np.sin(u * (8 + cut * 10)))
    gy = np.abs(np.sin(v * 10))
    line = np.clip(1.0 - np.minimum(gx, gy) * 8.0, 0, 1)
    fog = np.clip(1.2 - z, 0, 1)
    rgb = _rgb(x, y)
    rgb[..., 0] = line * 0.45 * fog
    rgb[..., 1] = line * 0.12 * fog
    rgb[..., 2] = line * 0.95 * fog
    rgb += kick * 0.12
    rgb *= 0.35 + drive * 0.5
    return np.clip(rgb, 0, 1)


def to_ansi(rgb: np.ndarray) -> str:
    h, w, _ = rgb.shape
    if h % 2:
        rgb = rgb[:-1]
        h -= 1
    rows = []
    for y in range(0, h, 2):
        up = rgb[y]
        dn = rgb[y + 1]
        parts = []
        for x in range(w):
            a = up[x]
            b = dn[x]
            parts.append(
                f"\x1b[38;2;{a[0]};{a[1]};{a[2]}m\x1b[48;2;{b[0]};{b[1]};{b[2]}m▀"
            )
        parts.append("\x1b[0m")
        rows.append("".join(parts))
    return "\n".join(rows)


def _q(v: int) -> int:
    return int(v) & 0xF8


@lru_cache(maxsize=4096)
def _pair_style(r: int, g: int, b: int, r2: int, g2: int, b2: int) -> Style:
    return Style(
        color=f"#{r:02x}{g:02x}{b:02x}",
        bgcolor=f"#{r2:02x}{g2:02x}{b2:02x}",
    )


def strips_from_rgb(rgb: np.ndarray, width: int, height: int):

    h, w, _ = rgb.shape
    if h % 2:
        h -= 1
    rows = min(height, h // 2)
    cols = min(width, w)
    out = []
    for y in range(rows):
        up = rgb[y * 2]
        dn = rgb[y * 2 + 1]
        segs = []
        run = 1
        pr = pg = pb = pr2 = pg2 = pb2 = -1
        for x in range(cols):
            a = up[x]
            b = dn[x]
            r, g, bl = _q(a[0]), _q(a[1]), _q(a[2])
            r2, g2, b2 = _q(b[0]), _q(b[1]), _q(b[2])
            if r == pr and g == pg and bl == pb and r2 == pr2 and g2 == pg2 and b2 == pb2:
                run += 1
            else:
                if pr >= 0:
                    segs.append(Segment("▀" * run, _pair_style(pr, pg, pb, pr2, pg2, pb2)))
                pr, pg, pb, pr2, pg2, pb2 = r, g, bl, r2, g2, b2
                run = 1
        if pr >= 0:
            segs.append(Segment("▀" * run, _pair_style(pr, pg, pb, pr2, pg2, pb2)))
        if cols < width:
            segs.append(Segment(" " * (width - cols)))
        out.append(Strip(segs, width))
    while len(out) < height:
        out.append(Strip.blank(width))
    return out
