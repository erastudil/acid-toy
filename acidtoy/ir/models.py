from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class AcidStep:
    pitch: int
    gate: bool
    accent: bool
    slide: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AcidStep":
        return cls(
            pitch=int(d["pitch"]),
            gate=bool(d["gate"]),
            accent=bool(d["accent"]),
            slide=bool(d["slide"]),
        )

    @classmethod
    def rest(cls) -> "AcidStep":
        return cls(pitch=0, gate=False, accent=False, slide=False)


@dataclass
class DrumLane:
    name: str
    vel: list[float | None]

    def to_dict(self) -> dict:
        return {"name": self.name, "vel": self.vel}

    @classmethod
    def from_dict(cls, d: dict) -> "DrumLane":
        vel = [None if v is None else float(v) for v in d["vel"]]
        return cls(name=str(d["name"]), vel=vel)


@dataclass
class Envelope:
    start: float
    end: float
    bars: int

    def at(self, bar: float) -> float:
        if self.bars <= 0:
            return self.end
        t = min(max(bar / self.bars, 0.0), 1.0)
        return self.start + (self.end - self.start) * t

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Envelope":
        return cls(start=float(d["start"]), end=float(d["end"]), bars=int(d["bars"]))


@dataclass
class Phrase:
    kind: str
    bars: int
    layers: list[str]
    cutoff: Envelope
    drive: float

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "bars": self.bars,
            "layers": list(self.layers),
            "cutoff": self.cutoff.to_dict(),
            "drive": self.drive,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Phrase":
        return cls(
            kind=str(d["kind"]),
            bars=int(d["bars"]),
            layers=list(d["layers"]),
            cutoff=Envelope.from_dict(d["cutoff"]),
            drive=float(d["drive"]),
        )


@dataclass
class Track:
    pack: str
    bpm: int
    key_root: int
    scale: list[int]
    seed: int
    swing: float
    acid: list[list[AcidStep]]
    drums: list[DrumLane]
    phrases: list[Phrase] = field(default_factory=list)
    character: str = "toxic"

    def lane(self, name: str) -> DrumLane | None:
        for d in self.drums:
            if d.name == name:
                return d
        return None

    def to_dict(self) -> dict:
        return {
            "pack": self.pack,
            "bpm": self.bpm,
            "key_root": self.key_root,
            "scale": list(self.scale),
            "seed": self.seed,
            "swing": self.swing,
            "character": self.character,
            "acid": [[s.to_dict() for s in pat] for pat in self.acid],
            "drums": [d.to_dict() for d in self.drums],
            "phrases": [p.to_dict() for p in self.phrases],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Track":
        return cls(
            pack=str(d["pack"]),
            bpm=int(d["bpm"]),
            key_root=int(d["key_root"]),
            scale=[int(x) for x in d["scale"]],
            seed=int(d["seed"]),
            swing=float(d["swing"]),
            character=str(d.get("character", "toxic")),
            acid=[[AcidStep.from_dict(s) for s in pat] for pat in d["acid"]],
            drums=[DrumLane.from_dict(x) for x in d["drums"]],
            phrases=[Phrase.from_dict(p) for p in d.get("phrases", [])],
        )
