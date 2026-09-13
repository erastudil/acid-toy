from __future__ import annotations

import random

from acidtoy.ir.models import Envelope, Phrase
from acidtoy.packs.hard_acid.dna import DNA


KINDS = ("intro", "drums_in", "acid_in", "peak", "break", "drop")


def _env(kind: str, bars: int, rng: random.Random) -> Envelope:
    closed = DNA["cutoff_closed"]
    scream = DNA["cutoff_scream"]
    if kind == "intro":
        return Envelope(closed, closed + 0.08, bars)
    if kind == "drums_in":
        return Envelope(closed, 0.22, bars)
    if kind == "acid_in":
        return Envelope(0.18, rng.uniform(0.45, 0.7), bars)
    if kind == "peak":
        return Envelope(rng.uniform(0.45, 0.6), scream, bars)
    if kind == "break":
        return Envelope(0.35, 0.12, bars)
    return Envelope(0.4, scream, bars)


def _drive(kind: str, rng: random.Random) -> float:
    lo, hi = DNA["drive_min"], DNA["drive_max"]
    if kind in ("intro", "drums_in"):
        return rng.uniform(lo, lo + 0.15)
    if kind == "break":
        return rng.uniform(lo, 0.55)
    if kind == "peak":
        return rng.uniform(0.72, hi)
    return rng.uniform(0.55, 0.82)


def _layers(kind: str) -> list[str]:
    if kind == "intro":
        return ["kick", "ch"]
    if kind == "drums_in":
        return ["kick", "ch", "clap", "oh"]
    if kind == "acid_in":
        return ["kick", "ch", "clap", "oh", "acid0"]
    if kind == "break":
        return ["ch", "oh", "acid0"]
    if kind == "peak":
        return ["kick", "ch", "clap", "oh", "perc", "acid0", "acid1"]
    return ["kick", "ch", "clap", "oh", "perc", "acid0", "acid1"]


def _bars(kind: str, rng: random.Random) -> int:
    if kind == "break":
        return rng.choice([8, 16])
    if kind == "intro":
        return 16
    return rng.choice([16, 16, 32])


def next_kind(prev: str | None, peak_run: int, rng: random.Random) -> str:
    if prev is None:
        return "intro"
    if prev == "intro":
        return "drums_in"
    if prev == "drums_in":
        return "acid_in"
    if prev == "acid_in":
        return rng.choice(["peak", "peak", "drop"])
    if prev == "break":
        return "drop"
    if peak_run >= 3:
        return "break"
    roll = rng.random()
    if roll < 0.18:
        return "break"
    if roll < 0.38:
        return "acid_in"
    if roll < 0.55:
        return "drop"
    return "peak"


def make_phrase(kind: str, rng: random.Random) -> Phrase:
    bars = _bars(kind, rng)
    return Phrase(
        kind=kind,
        bars=bars,
        layers=_layers(kind),
        cutoff=_env(kind, bars, rng),
        drive=_drive(kind, rng),
    )


def make_arc(rng: random.Random, n: int = 8) -> list[Phrase]:
    out: list[Phrase] = []
    prev = None
    peak_run = 0
    for _ in range(n):
        kind = next_kind(prev, peak_run, rng)
        if kind == "peak":
            peak_run += 1
        else:
            peak_run = 0
        out.append(make_phrase(kind, rng))
        prev = kind
    return out
