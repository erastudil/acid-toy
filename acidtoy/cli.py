from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def cmd_generate(args: argparse.Namespace) -> int:
    from acidtoy.engine.combinator import generate
    from acidtoy.grid import ascii_track

    track = generate(args.seed, phrases=args.phrases)
    print(ascii_track(track))
    if args.json:
        Path(args.json).write_text(json.dumps(track.to_dict(), indent=2), encoding="utf-8")
    return 0


def cmd_wav(args: argparse.Namespace) -> int:
    from acidtoy.engine.combinator import generate
    from acidtoy.grid import ascii_track
    from acidtoy.render.mix import render_track
    from acidtoy.render.wav import write_wav

    from acidtoy.ir.models import Envelope, Phrase

    track = generate(args.seed, phrases=args.phrases)
    print(ascii_track(track), file=sys.stderr)
    if not args.full:
        track.phrases = [
            Phrase(
                "peak",
                16,
                ["kick", "ch", "clap", "oh", "perc", "acid0", "acid1"],
                Envelope(0.48, 0.84, 16),
                0.86,
            )
        ]
    samples = render_track(track, bars=args.bars)
    out = write_wav(args.out, samples)
    print(out)
    return 0


def cmd_tui(_args: argparse.Namespace) -> int:
    from acidtoy.tui import run

    return run()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(prog="acidtoy")
    sub = p.add_subparsers(dest="cmd")

    t = sub.add_parser("tui")
    t.set_defaults(fn=cmd_tui)

    g = sub.add_parser("generate")
    g.add_argument("--seed", type=int, default=1)
    g.add_argument("--phrases", type=int, default=8)
    g.add_argument("--json", default="")
    g.set_defaults(fn=cmd_generate)

    w = sub.add_parser("wav")
    w.add_argument("--seed", type=int, default=1)
    w.add_argument("--phrases", type=int, default=4)
    w.add_argument("--bars", type=int, default=16)
    w.add_argument("--full", action="store_true")
    w.add_argument("--out", default=str(ROOT / "out" / "phrase.wav"))
    w.set_defaults(fn=cmd_wav)

    if not argv:
        return cmd_tui(argparse.Namespace())
    args = p.parse_args(argv)
    if not args.cmd:
        return cmd_tui(args)
    return args.fn(args)
