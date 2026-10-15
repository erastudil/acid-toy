from __future__ import annotations

import numpy as np

from acidtoy.ir.models import Phrase, Track
from acidtoy.packs.hard_acid.dna import DNA
from acidtoy.render.drums import clap, hat, kick, kick_hz, perc_metal
from acidtoy.render.synth_303 import render_pattern


def _place(buf: np.ndarray, hit: np.ndarray, at: int, gain: float) -> None:
    if at >= len(buf) or gain <= 0:
        return
    if at < 0:
        hit = hit[-at:]
        at = 0
    if len(hit) == 0:
        return
    n = min(len(hit), len(buf) - at)
    buf[at : at + n] += hit[:n] * gain


def _hpf(x: np.ndarray, sr: int, fc: float) -> np.ndarray:
    if len(x) == 0:
        return x
    rc = 1.0 / (2 * np.pi * fc)
    a = rc / (rc + 1.0 / sr)
    try:
        from scipy.signal import lfilter
        b = np.array([a, -a], dtype=np.float64)
        a_coeffs = np.array([1.0, -a], dtype=np.float64)
        return lfilter(b, a_coeffs, x)
    except ImportError:
        y = np.zeros_like(x)
        px = 0.0
        py = 0.0
        for i, v in enumerate(x):
            py = a * (py + v - px)
            px = v
            y[i] = py
        return y


def _delay(x: np.ndarray, sr: int, bpm: int, mix: float = 0.18) -> np.ndarray:
    steps = 3  # dotted 8th-ish 3/16
    dt = int((60.0 / bpm) * (steps / 4.0) * sr)
    y = np.zeros_like(x)
    if dt < 1 or dt >= len(x):
        return x
    y[dt:] = x[:-dt] * 0.45
    y[2 * dt :] += x[: -2 * dt] * 0.18
    return x + y * mix


def _phrase_for_bar(phrases: list[Phrase], bar: float) -> Phrase | None:
    acc = 0.0
    for p in phrases:
        if bar < acc + p.bars:
            return p
        acc += p.bars
    return phrases[-1] if phrases else None


def render_track(track: Track, sr: int = 44100, bars: int | None = None) -> np.ndarray:
    phrases = track.phrases or []
    total_bars = bars
    if total_bars is None:
        total_bars = sum(p.bars for p in phrases) if phrases else 16
    beat = 60.0 / track.bpm
    bar_s = beat * 4.0
    n = int(total_bars * bar_s * sr)
    kick_bus = np.zeros(n, dtype=np.float64)
    rest_drums = np.zeros(n, dtype=np.float64)
    kbuf = kick(sr, freq=kick_hz(track.key_root))
    cbuf = clap(sr)
    chbuf = hat(sr, False)
    ohbuf = hat(sr, True)
    pbuf = perc_metal(sr)
    step = beat / 4.0

    def lane_on(name: str, phrase: Phrase | None) -> bool:
        if phrase is None:
            return True
        return name in phrase.layers

    for bar_i in range(total_bars):
        phrase = _phrase_for_bar(phrases, bar_i)
        for s in range(16):
            t = (bar_i * 16 + s) * step
            if s % 2 == 1:
                t += (track.swing - 0.5) * 2.0 * step
            at = int(t * sr)
            if at >= n:
                break
            kick_l = track.lane("kick")
            clap_l = track.lane("clap")
            ch_l = track.lane("ch")
            oh_l = track.lane("oh")
            perc_l = track.lane("perc")
            if kick_l and lane_on("kick", phrase) and kick_l.vel[s]:
                _place(kick_bus, kbuf, at, kick_l.vel[s] * 1.55)
            if clap_l and lane_on("clap", phrase) and clap_l.vel[s]:
                _place(rest_drums, cbuf, at, clap_l.vel[s] * 0.55)
            if ch_l and lane_on("ch", phrase) and ch_l.vel[s]:
                _place(rest_drums, chbuf, at, ch_l.vel[s] * 0.22)
            if oh_l and lane_on("oh", phrase) and oh_l.vel[s]:
                _place(rest_drums, ohbuf, at, oh_l.vel[s] * 0.2)
            if perc_l and lane_on("perc", phrase) and perc_l.vel[s]:
                _place(rest_drums, pbuf, at, perc_l.vel[s] * 0.28)

    def cutoff_fn(voice: int):
        def at(bar: float) -> float:
            p = _phrase_for_bar(phrases, bar)
            if p is None:
                return 0.45
            local = bar
            acc = 0.0
            for ph in phrases:
                if bar < acc + ph.bars:
                    local = bar - acc
                    break
                acc += ph.bars
            c = p.cutoff.at(local)
            if voice == 1:
                c = min(1.0, c + 0.08)
            return c

        return at

    acid = np.zeros(n, dtype=np.float64)
    for vi, pat in enumerate(track.acid):
        layer = f"acid{vi}"

        chunk = render_pattern(
            pat,
            sr,
            track.bpm,
            track.swing,
            n,
            cutoff_fn(vi),
            drive=0.72 if vi == 0 else 0.8,
            res=DNA["res_min"] + 0.12 + 0.08 * vi,
        )
        mute = np.ones(n)
        if phrases:
            for bar_i in range(total_bars):
                p = _phrase_for_bar(phrases, bar_i)
                if p and layer not in p.layers:
                    a = int(bar_i * bar_s * sr)
                    b = int((bar_i + 1) * bar_s * sr)
                    mute[a:b] = 0.0
        g = 1.0 if vi == 0 else 0.72
        acid += chunk * mute * g

    acid = _hpf(acid, sr, DNA["acid_hpf_hz"])
    acid = np.tanh(acid * 1.65)
    acid = _delay(acid, sr, track.bpm, mix=0.14)
    rest = rest_drums + acid * 0.78
    mix = sum_buses(kick_bus, rest)
    return mix.astype(np.float32)


def sum_buses(kick: np.ndarray, rest: np.ndarray) -> np.ndarray:
    """kick owns the floor. clip the rest, never scale the sub to make the 303 fit."""
    if len(kick) == 0:
        return np.array([], dtype=np.float32)
    duck = 0.28 + 0.72 * (1.0 - np.clip(np.abs(kick) * 1.35, 0.0, 1.0))
    rest = np.tanh(rest * duck * 1.05)
    peak_k = float(np.max(np.abs(kick))) or 1.0
    if peak_k > 0.95:
        kick = kick * (0.95 / peak_k)
    mix = kick + rest
    return np.clip(mix, -0.99, 0.99)
