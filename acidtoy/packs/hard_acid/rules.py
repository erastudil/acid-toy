from __future__ import annotations

from acidtoy.ir.models import Track
from acidtoy.packs.hard_acid.dna import DNA, midi_in_scale


class Violation(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


def hard_fail(track: Track) -> list[str]:
    bad: list[str] = []
    d = DNA
    if track.pack != "hard_acid":
        bad.append(f"pack {track.pack}")
    if not (d["bpm_min"] <= track.bpm <= d["bpm_max"]):
        bad.append(f"bpm {track.bpm}")
    if track.swing < d["swing_min"] or track.swing > d["swing_max"]:
        bad.append(f"swing {track.swing}")
    n_acid = len(track.acid)
    if n_acid < d["acid_voices_min"] or n_acid > d["acid_voices_max"]:
        bad.append(f"acid voices {n_acid}")
    for i, pat in enumerate(track.acid):
        if len(pat) not in d["acid_len"]:
            bad.append(f"acid[{i}] length {len(pat)}")
        gates = [s for s in pat if s.gate]
        if not gates:
            bad.append(f"acid[{i}] empty")
        for j, s in enumerate(pat):
            if s.slide and not s.gate:
                bad.append(f"acid[{i}] slide on rest step {j}")
            if s.gate and not midi_in_scale(s.pitch, track.key_root, track.scale):
                bad.append(f"acid[{i}] pitch {s.pitch} off-scale step {j}")
        if gates:
            dens = len(gates) / len(pat)
            if dens < 0.2 or dens > 0.95:
                bad.append(f"acid[{i}] density {dens:.2f}")
    kick = track.lane("kick")
    if kick is None:
        bad.append("no kick")
    else:
        if len(kick.vel) != 16:
            bad.append("kick length")
        for i in d["kick_on"]:
            v = kick.vel[i]
            if v is None or v < 0.8:
                bad.append(f"kick missing fourfloor at {i}")
    clap = track.lane("clap")
    if clap is not None:
        for i in d["clap_on"]:
            if clap.vel[i] is None:
                bad.append(f"clap missing {i}")
    perc = track.lane("perc")
    if perc is not None:
        hits = sum(1 for v in perc.vel if v)
        if hits > d["perc_max"]:
            bad.append(f"perc density {hits}")
    if track.phrases:
        if track.phrases[0].kind == "peak":
            bad.append("starts at peak")
    return bad


def check(track: Track) -> None:
    bad = hard_fail(track)
    if bad:
        raise Violation("; ".join(bad))
