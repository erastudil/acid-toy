"""dark 303. 4-pole tanh ladder. accent + slide. not a piano."""

from __future__ import annotations

import math

import numpy as np

from scipy.signal import lfilter

from acidtoy.ir.models import AcidStep
from acidtoy.packs.hard_acid.dna import DNA

CHUNK = 32


def _render_ladder(
    out: np.ndarray,
    n: int,
    sr: int,
    voice: "AcidVoice",
    cutoff: float,
    res: float,
    envmod: float,
    drive: float,
    decay: float,
    square: float,
) -> None:
    env_a = math.exp(-1.0 / (max(decay, 0.04) * sr * (0.55 if voice.accent else 1.0)))
    env_chunk = env_a ** CHUNK
    amp_rel = 0.997 ** CHUNK
    k = 3.2 + res * 1.1
    drive_g = 1.4 + drive * 2.8
    fc_min = 40.0
    fc_ratio = 4200.0 / 40.0
    s0, s1, s2, s3 = voice.s
    phase = voice.phase
    freq = voice.freq
    target = voice.target
    slide_a = voice.slide_a
    env = voice.env
    amp = voice.amp
    gate = voice.gate
    inv_sr = 1.0 / sr
    i0 = 0
    while i0 < n:
        m = n - i0 if n - i0 < CHUNK else CHUNK
        freq += (target - freq) * (1.0 - (1.0 - slide_a) ** m)
        if not gate:
            amp *= amp_rel if m == CHUNK else (0.997 ** m)
        env *= env_chunk if m == CHUNK else (env_a ** m)
        c = cutoff + env * envmod * 0.85
        if c < 0.0:
            c = 0.0
        elif c > 1.0:
            c = 1.0
        fc = fc_min * (fc_ratio ** c)
        ny = sr * 0.42
        if fc > ny:
            fc = ny
        g = math.tan(math.pi * fc * inv_sr)
        G = g / (1.0 + g)
        # saw for m samples
        ph = phase + np.arange(m, dtype=np.float64) * (freq * inv_sr)
        ph -= np.floor(ph)
        osc = 2.0 * ph - 1.0
        if square:
            osc = np.where(osc >= 0.0, 1.0, -1.0)
        phase = float(ph[-1] + freq * inv_sr)
        phase -= math.floor(phase)
        x = np.tanh(osc * drive_g - k * s3)
        b = np.array([G], dtype=np.float64)
        a = np.array([1.0, G - 1.0], dtype=np.float64)
        y, z0 = lfilter(b, a, x, zi=np.array([s0], dtype=np.float64))
        y = np.tanh(y)
        y, z1 = lfilter(b, a, y, zi=np.array([s1], dtype=np.float64))
        y = np.tanh(y)
        y, z2 = lfilter(b, a, y, zi=np.array([s2], dtype=np.float64))
        y = np.tanh(y)
        y, z3 = lfilter(b, a, y, zi=np.array([s3], dtype=np.float64))
        y = np.tanh(y)
        s0, s1, s2, s3 = float(z0[0]), float(z1[0]), float(z2[0]), float(z3[0])
        out[i0 : i0 + m] = y * amp * 0.78
        i0 += m
    voice.s[0], voice.s[1], voice.s[2], voice.s[3] = s0, s1, s2, s3
    voice.phase = phase
    voice.freq = freq
    voice.env = env
    voice.amp = amp


def midi_hz(n: int) -> float:
    return 440.0 * (2.0 ** ((n - 69) / 12.0))


class AcidVoice:
    def __init__(self, sr: int):
        self.sr = sr
        self.s = [0.0, 0.0, 0.0, 0.0]
        self.phase = 0.0
        self.freq = 55.0
        self.target = 55.0
        self.env = 0.0
        self.amp = 0.0
        self.gate = False
        self.accent = False
        self.slide_a = 1.0 - math.exp(-1.0 / ((DNA["slide_tau_ms"] / 1000.0) * sr))

    def note(self, freq: float, accent: bool, slide: bool) -> None:
        self.target = freq
        if not (slide and self.gate):
            self.freq = freq
        self.gate = True
        self.accent = accent
        self.env = 1.25 if accent else 0.85
        self.amp = 1.15 if accent else 0.82

    def rest(self) -> None:
        self.gate = False
        self.accent = False

    def render(
        self,
        n: int,
        cutoff: float,
        res: float,
        envmod: float,
        drive: float,
        decay: float,
        wave: str = "saw",
    ) -> np.ndarray:
        out = np.empty(n, dtype=np.float64)
        _render_ladder(
            out,
            n,
            self.sr,
            self,
            cutoff,
            res,
            envmod,
            drive,
            decay,
            1.0 if wave == "square" else 0.0,
        )
        return out


def render_pattern(
    steps: list[AcidStep],
    sr: int,
    bpm: int,
    swing: float,
    n_samples: int,
    cutoff_at: callable,
    drive: float,
    res: float | None = None,
) -> np.ndarray:
    voice = AcidVoice(sr)
    out = np.zeros(n_samples, dtype=np.float64)
    step_dur = (60.0 / bpm) / 4.0
    res = DNA["res_min"] + 0.18 if res is None else res
    envmod = DNA["envmod"]
    decay = DNA["decay"]
    L = len(steps)
    t = 0.0
    i0 = 0
    bar = 0.0
    sixteenth = 0
    while i0 < n_samples:
        idx = sixteenth % L
        st = steps[idx]
        swing_delay = 0.0
        if sixteenth % 2 == 1:
            swing_delay = (swing - 0.5) * 2.0 * step_dur
        dur = step_dur + swing_delay
        n = min(int(dur * sr), n_samples - i0)
        if n <= 0:
            break
        if st.gate:
            voice.note(midi_hz(st.pitch), st.accent, st.slide)
        else:
            voice.rest()
        cut = cutoff_at(bar)
        chunk = voice.render(n, cut, res, envmod, drive, decay)
        out[i0 : i0 + n] += chunk
        i0 += n
        t += dur
        sixteenth += 1
        bar = (sixteenth / 16.0)
    return out
