"""named pattern families. not random soup."""

from __future__ import annotations

import random

from acidtoy.ir.models import AcidStep, DrumLane
from acidtoy.packs.hard_acid.dna import DNA


def _vel(n: int, hits: dict[int, float]) -> list[float | None]:
    out: list[float | None] = [None] * n
    for i, v in hits.items():
        if 0 <= i < n:
            out[i] = v
    return out


def kick_fourfloor(_rng: random.Random) -> DrumLane:
    hits = {i: 1.0 for i in DNA["kick_on"]}
    return DrumLane("kick", _vel(16, hits))


def kick_fourfloor_ghost(rng: random.Random) -> DrumLane:
    hits = {i: 1.0 for i in DNA["kick_on"]}
    for i in (2, 6, 10, 14):
        if rng.random() < 0.12:
            hits[i] = rng.uniform(0.35, 0.55)
    return DrumLane("kick", _vel(16, hits))


def clap_backbeat(_rng: random.Random) -> DrumLane:
    hits = {i: 1.0 for i in DNA["clap_on"]}
    return DrumLane("clap", _vel(16, hits))


def clap_flam(rng: random.Random) -> DrumLane:
    hits = {i: 1.0 for i in DNA["clap_on"]}
    if rng.random() < 0.7:
        hits[3] = 0.4
    if rng.random() < 0.5:
        hits[11] = 0.35
    return DrumLane("clap", _vel(16, hits))


def ch_eighths(_rng: random.Random) -> DrumLane:
    hits = {i: 0.5 for i in range(0, 16, 2)}
    return DrumLane("ch", _vel(16, hits))


def ch_16ths(rng: random.Random) -> DrumLane:
    hits = {i: rng.uniform(0.22, 0.42) for i in range(16)}
    for i in DNA["kick_on"]:
        hits[i] = min(hits[i], 0.28)
    return DrumLane("ch", _vel(16, hits))


def oh_offbeats(_rng: random.Random) -> DrumLane:
    hits = {i: 0.55 for i in DNA["oh_offbeats"]}
    return DrumLane("oh", _vel(16, hits))


def oh_sparse(rng: random.Random) -> DrumLane:
    hits = {}
    for i in DNA["oh_offbeats"]:
        if rng.random() < 0.7:
            hits[i] = rng.uniform(0.4, 0.65)
    return DrumLane("oh", _vel(16, hits))


def perc_none(_rng: random.Random) -> DrumLane:
    return DrumLane("perc", [None] * 16)


def perc_industrial(rng: random.Random) -> DrumLane:
    hits: dict[int, float] = {}
    slots = [1, 3, 7, 9, 11, 13, 15]
    rng.shuffle(slots)
    n = rng.randint(1, DNA["perc_max"])
    for i in slots[:n]:
        hits[i] = rng.uniform(0.25, 0.55)
    return DrumLane("perc", _vel(16, hits))


KICK_FAMS = (kick_fourfloor, kick_fourfloor_ghost)
CLAP_FAMS = (clap_backbeat, clap_flam)
CH_FAMS = (ch_eighths, ch_16ths)
OH_FAMS = (oh_offbeats, oh_sparse)
PERC_FAMS = (perc_none, perc_industrial, perc_industrial)


def _pitch(root: int, degrees: list[int], octave: int, deg_i: int) -> int:
    return root + degrees[deg_i % len(degrees)] + octave


def _pattern(length: int, steps: list[AcidStep]) -> list[AcidStep]:
    if len(steps) != length:
        raise ValueError(f"acid length {len(steps)} != {length}")
    return steps


def acid_scream_16(rng: random.Random, root: int, degrees: list[int]) -> list[AcidStep]:
    steps: list[AcidStep] = []
    for i in range(16):
        if rng.random() > 0.72:
            steps.append(AcidStep.rest())
            continue
        octv = 12 if rng.random() < 0.55 else (24 if rng.random() < 0.35 else 0)
        deg = 0 if rng.random() < 0.4 else rng.randrange(len(degrees))
        if i % 4 == 0:
            deg = 0
            octv = 0 if rng.random() < 0.4 else 12
        steps.append(
            AcidStep(
                pitch=_pitch(root, degrees, octv, deg),
                gate=True,
                accent=rng.random() < 0.38,
                slide=rng.random() < 0.18,
            )
        )
    return _fix_slides(steps)


def acid_twelve(rng: random.Random, root: int, degrees: list[int]) -> list[AcidStep]:
    steps: list[AcidStep] = []
    for i in range(12):
        if rng.random() > 0.7:
            steps.append(AcidStep.rest())
            continue
        octv = 12 if rng.random() < 0.5 else 0
        deg = rng.choice([0, 0, 1, 4, 6]) % len(degrees)
        steps.append(
            AcidStep(
                pitch=_pitch(root, degrees, octv, deg),
                gate=True,
                accent=rng.random() < 0.33,
                slide=rng.random() < 0.22,
            )
        )
    return _fix_slides(steps)


def acid_oct_jumper(rng: random.Random, root: int, degrees: list[int]) -> list[AcidStep]:
    steps: list[AcidStep] = []
    for i in range(16):
        on = i % 4 == 0 or rng.random() < 0.28
        if not on:
            steps.append(AcidStep.rest())
            continue
        octv = 24 if i % 8 == 4 else (0 if i % 4 == 0 else 12)
        deg = 0 if i % 4 == 0 else rng.randrange(len(degrees))
        steps.append(
            AcidStep(
                pitch=_pitch(root, degrees, octv, deg),
                gate=True,
                accent=octv >= 12,
                slide=octv == 24 and rng.random() < 0.4,
            )
        )
    return _fix_slides(steps)


def acid_slide_worm(rng: random.Random, root: int, degrees: list[int]) -> list[AcidStep]:
    steps: list[AcidStep] = []
    deg = 0
    octv = 0
    for i in range(16):
        if rng.random() > 0.75:
            steps.append(AcidStep.rest())
            continue
        if rng.random() < 0.45:
            deg = min(max(deg + rng.choice([-1, 1, 1, 2]), 0), len(degrees) - 1)
        if rng.random() < 0.12:
            octv = 12 - octv
        steps.append(
            AcidStep(
                pitch=_pitch(root, degrees, octv, deg),
                gate=True,
                accent=rng.random() < 0.22,
                slide=rng.random() < 0.55,
            )
        )
    return _fix_slides(steps)


def acid_root_drone(rng: random.Random, root: int, degrees: list[int]) -> list[AcidStep]:
    fifth = 4 if len(degrees) > 4 else len(degrees) - 1
    steps: list[AcidStep] = []
    for i in range(16):
        if rng.random() > 0.62:
            steps.append(AcidStep.rest())
            continue
        deg = 0 if rng.random() < 0.7 else fifth
        octv = 0 if rng.random() < 0.75 else 12
        steps.append(
            AcidStep(
                pitch=_pitch(root, degrees, octv, deg),
                gate=True,
                accent=i % 4 == 0,
                slide=rng.random() < 0.12,
            )
        )
    return _fix_slides(steps)


def acid_phrygian_stab(rng: random.Random, root: int, degrees: list[int]) -> list[AcidStep]:
    b2_idx = degrees.index(1) if 1 in degrees else 1 % len(degrees)
    steps: list[AcidStep] = []
    for i in range(16):
        if i % 2 == 1 and rng.random() < 0.55:
            steps.append(AcidStep.rest())
            continue
        if rng.random() > 0.8:
            steps.append(AcidStep.rest())
            continue
        deg = 0 if rng.random() < 0.55 else b2_idx
        octv = 12 if rng.random() < 0.5 else 24
        steps.append(
            AcidStep(
                pitch=_pitch(root, degrees, octv, deg),
                gate=True,
                accent=True,
                slide=rng.random() < 0.15,
            )
        )
    return _fix_slides(steps)


ACID_FAMS = (
    acid_scream_16,
    acid_twelve,
    acid_oct_jumper,
    acid_slide_worm,
    acid_root_drone,
    acid_phrygian_stab,
)

ACID_HIGH_FAMS = (
    acid_scream_16,
    acid_oct_jumper,
    acid_phrygian_stab,
    acid_twelve,
)


def _fix_slides(steps: list[AcidStep]) -> list[AcidStep]:
    out: list[AcidStep] = []
    for s in steps:
        if not s.gate:
            out.append(AcidStep.rest())
        else:
            out.append(s)
    for i, s in enumerate(out):
        if s.slide and not s.gate:
            out[i] = AcidStep.rest()
    return out


def pick_drums(rng: random.Random) -> list[DrumLane]:
    ch_fn = rng.choice(CH_FAMS)
    oh_fn = oh_sparse if ch_fn is ch_16ths else rng.choice(OH_FAMS)
    return [
        rng.choice(KICK_FAMS)(rng),
        rng.choice(CLAP_FAMS)(rng),
        ch_fn(rng),
        oh_fn(rng),
        rng.choice(PERC_FAMS)(rng),
    ]
