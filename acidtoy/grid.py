from __future__ import annotations

from acidtoy.ir.models import AcidStep, Track
from acidtoy.packs.hard_acid.dna import KEY_NAMES


def _cells(vel: list[float | None]) -> str:
    out = []
    for v in vel:
        if v is None:
            out.append("-")
        elif v >= 0.85:
            out.append("X")
        elif v >= 0.45:
            out.append("x")
        else:
            out.append(".")
    return "".join(out)


def _acid_row(steps: list[AcidStep], root: int) -> str:
    names = "C C# D D# E F F# G G# A A# B".split()
    out = []
    for s in steps:
        if not s.gate:
            out.append("--")
            continue
        n = names[s.pitch % 12]
        mark = n
        if s.accent:
            mark = mark.upper() if mark != mark.upper() else mark
        if s.slide:
            mark += "~"
        else:
            mark += " "
        out.append(f"{mark:3}")
    return "".join(out)


def ascii_track(track: Track) -> str:
    key = KEY_NAMES.get(track.key_root, str(track.key_root))
    lines = [
        f"hard_acid  seed={track.seed}  {track.bpm}bpm  {key}  swing={track.swing:.2f}",
    ]
    for d in track.drums:
        lines.append(f"{d.name:4} |{_cells(d.vel)}|")
    for i, pat in enumerate(track.acid):
        lines.append(f"303-{i} |{_acid_row(pat, track.key_root)}|  len={len(pat)}")
    if track.phrases:
        arc = " → ".join(f"{p.kind}({p.bars})" for p in track.phrases)
        lines.append(f"arc  {arc}")
    return "\n".join(lines)
