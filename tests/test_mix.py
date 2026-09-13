from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from acidtoy.engine.combinator import generate
from acidtoy.ir.models import Envelope, Phrase
from acidtoy.render.mix import render_track, sum_buses


def _band_energy(x: np.ndarray, sr: int, lo: float, hi: float) -> float:
    spec = np.fft.rfft(x * np.hanning(len(x)))
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    m = (freqs >= lo) & (freqs < hi)
    return float(np.mean(np.abs(spec[m]) ** 2))


class TestMix(unittest.TestCase):
    def test_kick_survives_scream(self) -> None:
        kick = np.zeros(2048)
        kick[:200] = np.sin(np.linspace(0, 8 * np.pi, 200)) * 0.9
        rest = np.ones(2048) * 0.8
        mix = sum_buses(kick, rest)
        self.assertGreater(float(np.max(np.abs(mix[:200]))), 0.7)

    def test_floor_louder_than_air(self) -> None:
        track = generate(7, phrases=2)
        track.phrases = [
            Phrase(
                "peak",
                8,
                ["kick", "ch", "clap", "oh", "perc", "acid0", "acid1"],
                Envelope(0.5, 0.86, 8),
                0.9,
            )
        ]
        x = render_track(track, bars=8)
        sr = 44100
        floor = _band_energy(x, sr, 40.0, 90.0)
        air = _band_energy(x, sr, 2500.0, 8000.0)
        self.assertGreater(floor, air * 0.15)


if __name__ == "__main__":
    unittest.main()
