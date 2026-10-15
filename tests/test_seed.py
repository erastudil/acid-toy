from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_generate(seed: int, json_path: Path) -> bytes:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "acidtoy", "generate", "--seed", str(seed), "--json", str(json_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=True,
    )
    return proc.stdout


class TestSeed(unittest.TestCase):
    def test_seed_7_same_bytes_twice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            a_json = Path(tmp) / "a.json"
            b_json = Path(tmp) / "b.json"
            a_out = run_generate(7, a_json)
            b_out = run_generate(7, b_json)
            self.assertTrue(a_out.strip())
            self.assertEqual(a_out, b_out)
            self.assertEqual(a_json.read_bytes(), b_json.read_bytes())


if __name__ == "__main__":
    unittest.main()
