from __future__ import annotations

import math

import numpy as np


def kick_hz(root_midi: int) -> float:
    """fold key into the 48–58 Hz kick octave."""
    f = 440.0 * (2.0 ** ((root_midi - 69) / 12.0))
    while f > 58.0:
        f *= 0.5
    while f < 45.0:
        f *= 2.0
    if f < 45.0 or f > 62.0:
        f = 52.0
    return f


def kick(sr: int, freq: float = 52.0, dur: float = 0.42) -> np.ndarray:
    """dry sub + punch. never tanh the sub. never peak-normalize against the click."""
    n = int(sr * dur)
    t = np.arange(n, dtype=np.float64) / sr
    f = freq + (280.0 - freq) * np.exp(-t * 62.0)
    phase = np.cumsum(2.0 * math.pi * f / sr)
    body = np.sin(phase) * np.exp(-t * 14.0)
    body += 0.35 * np.sin(2.0 * phase) * np.exp(-t * 22.0)
    sub = np.sin(2.0 * math.pi * freq * t) * np.exp(-t * 5.2)
    click_n = max(1, int(0.006 * sr))
    rng = np.random.default_rng(909)
    click = np.zeros(n)
    click[:click_n] = rng.standard_normal(click_n) * np.linspace(1.0, 0.0, click_n)
    mid = np.tanh((body + click * 0.7) * 2.1) * 0.48
    x = sub * 1.12 + mid
    peak = float(np.max(np.abs(x)))
    if peak > 1.0:
        mid = mid * (1.0 / peak)
        x = sub * 1.12 + mid
        peak = float(np.max(np.abs(x)))
        if peak > 1.0:
            x = x / peak
    return x.astype(np.float64)


def clap(sr: int, dur: float = 0.22) -> np.ndarray:
    n = int(sr * dur)
    x = np.zeros(n, dtype=np.float64)
    rng = np.random.default_rng(909)
    delays = [0, int(0.012 * sr), int(0.024 * sr), int(0.038 * sr)]
    gains = [1.0, 0.85, 0.55, 0.35]
    burst = int(0.012 * sr)
    for d, g in zip(delays, gains):
        if d + burst > n:
            continue
        noise = rng.standard_normal(burst)
        env = np.linspace(1.0, 0.0, burst)
        x[d : d + burst] += noise * env * g
    t = np.arange(n) / sr
    x *= np.exp(-t * 18.0)
    x = np.tanh(x * 2.4)
    return x


def hat(sr: int, open_: bool, dur: float | None = None) -> np.ndarray:
    if dur is None:
        dur = 0.14 if open_ else 0.045
    n = int(sr * dur)
    rng = np.random.default_rng(808 if open_ else 801)
    x = rng.standard_normal(n)
    t = np.arange(n) / sr
    tau = 0.055 if open_ else 0.012
    x *= np.exp(-t / tau)
    x = _hp(x, sr, 7000.0)
    return np.tanh(x * (0.9 if open_ else 0.7)) * (0.55 if open_ else 0.4)


def perc_metal(sr: int, dur: float = 0.18) -> np.ndarray:
    n = int(sr * dur)
    t = np.arange(n, dtype=np.float64) / sr
    rng = np.random.default_rng(666)
    ping = np.sin(2 * np.pi * 1850 * t) * np.exp(-t * 28)
    ping += 0.4 * np.sin(2 * np.pi * 2730 * t) * np.exp(-t * 35)
    noise = rng.standard_normal(n) * np.exp(-t * 40)
    x = ping * 0.55 + _hp(noise, sr, 2500) * 0.5
    return np.tanh(x * 2.0)


def _hp(x: np.ndarray, sr: int, fc: float) -> np.ndarray:
    rc = 1.0 / (2 * np.pi * fc)
    a = rc / (rc + 1.0 / sr)
    y = np.zeros_like(x)
    prev_x = 0.0
    prev_y = 0.0
    for i, v in enumerate(x):
        prev_y = a * (prev_y + v - prev_x)
        prev_x = v
        y[i] = prev_y
    return y
