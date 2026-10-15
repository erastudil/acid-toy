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


class TestCli(unittest.TestCase):
    def test_cli_generate_stdout(self) -> None:
        import io
        from contextlib import redirect_stdout
        from acidtoy.cli import main

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["generate", "--seed", "7", "--phrases", "3"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("hard_acid", output)
        self.assertIn("kick", output)
        self.assertIn("303-0", output)
        self.assertIn("arc", output)

    def test_cli_generate_json(self) -> None:
        import io, json, tempfile
        from contextlib import redirect_stdout
        from acidtoy.cli import main

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_path = f.name
        try:
            with redirect_stdout(io.StringIO()):
                code = main(["generate", "--seed", "12", "--phrases", "2", "--json", json_path])
            self.assertEqual(code, 0)
            data = json.loads(Path(json_path).read_text(encoding="utf-8"))
            self.assertEqual(data["seed"], 12)
            self.assertEqual(data["pack"], "hard_acid")
            self.assertGreaterEqual(data["bpm"], 148)
            self.assertLessEqual(data["bpm"], 155)
            self.assertIn("acid", data)
            self.assertIn("drums", data)
        finally:
            Path(json_path).unlink(missing_ok=True)

    def test_cli_wav_generation(self) -> None:
        import io, tempfile, wave
        from contextlib import redirect_stderr, redirect_stdout
        from acidtoy.cli import main

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = main(["wav", "--seed", "9", "--bars", "2", "--out", wav_path])
            self.assertEqual(code, 0)
            self.assertTrue(Path(wav_path).exists())
            with wave.open(wav_path, "rb") as w:
                self.assertEqual(w.getnchannels(), 1)
                self.assertEqual(w.getsampwidth(), 2)
                self.assertEqual(w.getframerate(), 44100)
                self.assertGreater(w.getnframes(), 0)
        finally:
            Path(wav_path).unlink(missing_ok=True)

    def test_cli_tui_graceful_missing_textual(self) -> None:
        import io
        from contextlib import redirect_stderr
        from acidtoy.cli import main

        err_buf = io.StringIO()
        saved_textual = sys.modules.get("textual")
        saved_tui = sys.modules.get("acidtoy.tui")
        try:
            sys.modules["textual"] = None  # type: ignore[assignment]
            sys.modules.pop("acidtoy.tui", None)
            with redirect_stderr(err_buf):
                code = main(["tui"])
        finally:
            if saved_textual is None:
                sys.modules.pop("textual", None)
            else:
                sys.modules["textual"] = saved_textual
            if saved_tui is not None:
                sys.modules["acidtoy.tui"] = saved_tui
        self.assertEqual(code, 1)
        self.assertIn("textual", err_buf.getvalue())


if __name__ == "__main__":
    unittest.main()
