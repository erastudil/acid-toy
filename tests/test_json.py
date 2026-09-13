from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from acidtoy.engine.combinator import generate
from acidtoy.ir.models import Track
from acidtoy.packs.hard_acid.rules import hard_fail


class TestJson(unittest.TestCase):
    def test_roundtrip(self) -> None:
        t = generate(11, phrases=5)
        t2 = Track.from_dict(t.to_dict())
        self.assertEqual(hard_fail(t2), [])
        self.assertEqual(t2.seed, 11)
        self.assertEqual(t2.bpm, t.bpm)
        self.assertEqual(len(t2.acid), len(t.acid))
        self.assertEqual(len(t2.phrases), 5)


if __name__ == "__main__":
    unittest.main()
