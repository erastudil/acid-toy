from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from acidtoy.live import Meter
from acidtoy.viz import PRESETS, paint, to_ansi


class TestViz(unittest.TestCase):
    def test_presets_finite(self) -> None:
        m = Meter(rms=0.4, kick=1.0, cutoff=0.7, drive=0.9)
        for p in PRESETS:
            rgb = paint(16, 20, 0.5, m, p)
            self.assertEqual(rgb.shape[2], 3)
            self.assertTrue((rgb >= 0).all())
            ansi = to_ansi(rgb)
            self.assertIn("\x1b[", ansi)


if __name__ == "__main__":
    unittest.main()
