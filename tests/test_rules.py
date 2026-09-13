from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from acidtoy.engine.combinator import generate, reroll_lane
from acidtoy.packs.hard_acid.rules import hard_fail


class TestHardAcid(unittest.TestCase):
    def test_twenty_seeds_legal(self) -> None:
        for seed in range(20):
            track = generate(seed, phrases=6)
            bad = hard_fail(track)
            self.assertEqual(bad, [], msg=f"seed {seed}: {bad}")
            self.assertGreaterEqual(track.bpm, 148)
            self.assertLessEqual(track.bpm, 155)
            self.assertGreaterEqual(len(track.acid), 1)
            self.assertLessEqual(len(track.acid), 2)
            self.assertNotEqual(track.phrases[0].kind, "peak")

    def test_reroll_acid_stays_legal(self) -> None:
        track = generate(3, phrases=4)
        reroll_lane(track, "acid0", salt=9)
        self.assertEqual(hard_fail(track), [])

    def test_kick_fourfloor(self) -> None:
        track = generate(0, phrases=4)
        kick = track.lane("kick")
        assert kick is not None
        for i in (0, 4, 8, 12):
            self.assertIsNotNone(kick.vel[i])
            self.assertGreaterEqual(kick.vel[i], 0.8)


if __name__ == "__main__":
    unittest.main()
