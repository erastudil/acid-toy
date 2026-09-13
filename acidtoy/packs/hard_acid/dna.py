"""hard acid techno DNA.

ear: query `hard acid techno`. donit mixes (toxic / 150+ / industrial 303).
ancestor: stay up forever. ceiling is not rumble-festival hard techno.
vibe: mescaline and cybercrime. darkest, hardest.
"""

from __future__ import annotations

DNA = {
    "name": "hard_acid",
    "bpm_min": 148,
    "bpm_max": 155,
    "bpm_default": 152,
    "swing_min": 0.50,
    "swing_max": 0.54,
    "keys": [45, 40, 38, 42, 43],  # A, E, D, F#, G  (MIDI bass octave)
    "scales": {
        "phrygian": [0, 1, 3, 5, 7, 8, 10],
        "natural_minor": [0, 2, 3, 5, 7, 8, 10],
        "minor_pent": [0, 3, 5, 7, 10],
    },
    "default_scale": "phrygian",
    "octaves": [0, 12, 24],
    "acid_voices_min": 1,
    "acid_voices_max": 2,
    "acid_len": (8, 12, 16),
    "density_min": 0.38,
    "density_max": 0.78,
    "accent_min": 0.18,
    "accent_max": 0.42,
    "slide_min": 0.08,
    "slide_max": 0.28,
    "kick_on": (0, 4, 8, 12),
    "clap_on": (4, 12),
    "oh_offbeats": (2, 6, 10, 14),
    "perc_max": 4,
    "phrase_bars": (16, 16, 32),
    "cutoff_closed": 0.14,
    "cutoff_scream": 0.88,
    "res_min": 0.74,
    "res_max": 0.94,
    "drive_min": 0.55,
    "drive_max": 0.96,
    "envmod": 0.86,
    "decay": 0.26,
    "acid_hpf_hz": 115.0,
    "slide_tau_ms": 80.0,
    "character": "toxic",
}

SCALE_NAMES = tuple(DNA["scales"].keys())
KEY_NAMES = {45: "A", 40: "E", 38: "D", 42: "F#", 43: "G"}


def midi_in_scale(pitch: int, root: int, degrees: list[int]) -> bool:
    if pitch <= 0:
        return True
    pc = (pitch - root) % 12
    return pc in degrees
