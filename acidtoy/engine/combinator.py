from __future__ import annotations

import copy
import random

from acidtoy.engine import mutate
from acidtoy.ir.models import Track
from acidtoy.packs.hard_acid.arrangement import make_arc
from acidtoy.packs.hard_acid.dna import DNA, SCALE_NAMES
from acidtoy.packs.hard_acid.families import ACID_FAMS, ACID_HIGH_FAMS, pick_drums
from acidtoy.packs.hard_acid.rules import Violation, check


def generate(seed: int, phrases: int = 8) -> Track:
    last_err = "unknown"
    for k in range(40):
        rng = random.Random(seed + k * 1_000_003)
        try:
            track = _attempt(rng, seed, phrases)
            check(track)
            return track
        except Violation as e:
            last_err = e.msg
            continue
    raise RuntimeError(f"combinator failed seed={seed}: {last_err}")


def _attempt(rng: random.Random, seed: int, phrases: int) -> Track:
    d = DNA
    bpm = rng.randint(d["bpm_min"], d["bpm_max"])
    root = rng.choice(d["keys"])
    scale_name = d["default_scale"] if rng.random() < 0.65 else rng.choice(SCALE_NAMES)
    degrees = list(d["scales"][scale_name])
    swing = rng.uniform(d["swing_min"], d["swing_max"])
    drums = pick_drums(rng)
    acid0 = rng.choice(ACID_FAMS)(rng, root, degrees)
    acid = [acid0]
    if rng.random() < 0.75:
        acid.append(rng.choice(ACID_HIGH_FAMS)(rng, root, degrees))
    for _ in range(rng.randint(1, 3)):
        mutate.walk_acid(acid[0], rng, root, degrees)
        if len(acid) > 1:
            mutate.walk_acid(acid[1], rng, root, degrees)
    return Track(
        pack="hard_acid",
        bpm=bpm,
        key_root=root,
        scale=degrees,
        seed=seed,
        swing=swing,
        acid=acid,
        drums=drums,
        phrases=make_arc(rng, phrases),
        character=d["character"],
    )


def reroll_lane(track: Track, lane: str, salt: int = 1) -> Track:
    from acidtoy.packs.hard_acid import families as F

    last = "reroll"
    for k in range(16):
        t = copy.deepcopy(track)
        rng = random.Random(track.seed * 1009 + salt * 17 + k * 13 + sum(ord(c) for c in lane))
        root = t.key_root
        degrees = list(t.scale)
        if lane == "kick":
            new = rng.choice(F.KICK_FAMS)(rng)
            t.drums = [new if d.name == "kick" else d for d in t.drums]
        elif lane == "clap":
            new = rng.choice(F.CLAP_FAMS)(rng)
            t.drums = [new if d.name == "clap" else d for d in t.drums]
        elif lane == "ch":
            new = rng.choice(F.CH_FAMS)(rng)
            t.drums = [new if d.name == "ch" else d for d in t.drums]
        elif lane == "oh":
            new = rng.choice(F.OH_FAMS)(rng)
            t.drums = [new if d.name == "oh" else d for d in t.drums]
        elif lane == "perc":
            new = rng.choice(F.PERC_FAMS)(rng)
            t.drums = [new if d.name == "perc" else d for d in t.drums]
        elif lane == "acid0":
            t.acid[0] = rng.choice(F.ACID_FAMS)(rng, root, degrees)
            mutate.walk_acid(t.acid[0], rng, root, degrees)
        elif lane == "acid1":
            pat = rng.choice(F.ACID_HIGH_FAMS)(rng, root, degrees)
            mutate.walk_acid(pat, rng, root, degrees)
            if len(t.acid) < 2:
                t.acid.append(pat)
            else:
                t.acid[1] = pat
        else:
            raise ValueError(lane)
        try:
            check(t)
            track.drums = t.drums
            track.acid = t.acid
            return track
        except Violation as e:
            last = e.msg
    raise RuntimeError(f"reroll {lane}: {last}")


def next_phrases(track: Track, n: int = 1, salt: int = 0) -> Track:
    rng = random.Random(track.seed + 7919 * (len(track.phrases) + 1) + salt)
    from acidtoy.packs.hard_acid.arrangement import make_phrase, next_kind

    prev = track.phrases[-1].kind if track.phrases else None
    peak_run = 0
    for p in reversed(track.phrases):
        if p.kind == "peak":
            peak_run += 1
        else:
            break
    for _ in range(n):
        kind = next_kind(prev, peak_run, rng)
        if kind == "peak":
            peak_run += 1
        else:
            peak_run = 0
        track.phrases.append(make_phrase(kind, rng))
        prev = kind
        if kind in ("drop", "peak", "acid_in") and rng.random() < 0.4:
            try:
                reroll_lane(track, "acid0", salt=len(track.phrases))
            except RuntimeError:
                pass
    return track
