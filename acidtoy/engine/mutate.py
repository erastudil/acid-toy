from __future__ import annotations

import random

from acidtoy.ir.models import AcidStep
from acidtoy.packs.hard_acid.dna import midi_in_scale


def walk_acid(
    steps: list[AcidStep], rng: random.Random, root: int, degrees: list[int]
) -> list[AcidStep]:
    op = rng.choice((_nudge, _toggle_accent, _toggle_gate, _toggle_slide, _oct_hop, _rotate))
    return op(steps, rng, root, degrees)


def _nudge(steps, rng, root, degrees):
    i = rng.randrange(len(steps))
    s = steps[i]
    if not s.gate:
        return steps
    pc = (s.pitch - root) % 12
    try:
        idx = degrees.index(pc)
    except ValueError:
        return steps
    idx = min(max(idx + rng.choice([-1, 1]), 0), len(degrees) - 1)
    octv = s.pitch - root - pc
    pitch = root + degrees[idx] + octv
    if midi_in_scale(pitch, root, degrees):
        steps[i] = AcidStep(pitch, True, s.accent, s.slide)
    return steps


def _toggle_accent(steps, rng, root, degrees):
    gated = [i for i, s in enumerate(steps) if s.gate]
    if not gated:
        return steps
    i = rng.choice(gated)
    s = steps[i]
    steps[i] = AcidStep(s.pitch, True, not s.accent, s.slide)
    return steps


def _toggle_gate(steps, rng, root, degrees):
    i = rng.randrange(len(steps))
    s = steps[i]
    if s.gate:
        steps[i] = AcidStep.rest()
    else:
        octv = rng.choice([0, 12, 24])
        deg = rng.choice(degrees)
        steps[i] = AcidStep(root + deg + octv, True, rng.random() < 0.3, False)
    return steps


def _toggle_slide(steps, rng, root, degrees):
    gated = [i for i, s in enumerate(steps) if s.gate]
    if not gated:
        return steps
    i = rng.choice(gated)
    s = steps[i]
    steps[i] = AcidStep(s.pitch, True, s.accent, not s.slide)
    return steps


def _oct_hop(steps, rng, root, degrees):
    gated = [i for i, s in enumerate(steps) if s.gate]
    if not gated:
        return steps
    i = rng.choice(gated)
    s = steps[i]
    delta = rng.choice([-12, 12, 12, 24])
    pitch = s.pitch + delta
    if 28 <= pitch <= 72 and midi_in_scale(pitch, root, degrees):
        steps[i] = AcidStep(pitch, True, s.accent or delta > 0, s.slide)
    return steps


def _rotate(steps, rng, root, degrees):
    k = rng.choice([1, 2, 4])
    steps[:] = steps[k:] + steps[:k]
    for i, s in enumerate(steps):
        if s.slide and not s.gate:
            steps[i] = AcidStep.rest()
    return steps
