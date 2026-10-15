from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

import numpy as np
try:
    import sounddevice as sd
except ImportError:
    sd = None

from acidtoy.engine.combinator import generate, next_phrases
from acidtoy.ir.models import Phrase, Track
from acidtoy.packs.hard_acid.dna import DNA
from acidtoy.render.drums import clap, hat, kick, kick_hz, perc_metal
from acidtoy.render.synth_303 import AcidVoice, midi_hz


@dataclass
class Meter:
    rms: float = 0.0
    kick: float = 0.0
    cutoff: float = 0.4
    drive: float = 0.7
    bpm: int = 152
    step: int = 0
    bar: int = 0
    phrase: str = "intro"
    seed: int = 0
    playing: bool = False
    volume: float = 0.85


def _phrase_at(phrases: list[Phrase], bar: float) -> Phrase | None:
    acc = 0.0
    for p in phrases:
        if bar < acc + p.bars:
            return p
        acc += p.bars
    return phrases[-1] if phrases else None


class LiveEngine:
    SR = 44100
    BLOCK = 512

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.meter = Meter()
        self.track: Track | None = None
        self._pending: Track | None = None
        self.playing = False
        self.volume = 0.85
        self.step = 0
        self.bar = 0
        self.pos = 0  # samples into current step
        self.voices = [AcidVoice(self.SR), AcidVoice(self.SR)]
        self.hits: dict[str, np.ndarray] = {}
        self.playheads: dict[str, int] = {}
        self.stream: sd.OutputStream | None = None
        self._built_key: int | None = None
        self._kick_env = 0.0
        self._duck = 1.0
        self._hp_x = [0.0, 0.0]
        self._hp_y = [0.0, 0.0]
        self.hit_gain = {}
        self._scratch = np.zeros(4096, dtype=np.float64)
        self._kick_bus = np.zeros(4096, dtype=np.float64)
        self._rest_bus = np.zeros(4096, dtype=np.float64)
        self.wave = np.zeros(512, dtype=np.float32)
        self.preset = "toxic"
        self._load_hits(45)

    def _load_hits(self, key_root: int) -> None:
        sr = self.SR
        self.hits = {
            "kick": kick(sr, freq=kick_hz(key_root)).astype(np.float32),
            "clap": clap(sr).astype(np.float32),
            "ch": hat(sr, False).astype(np.float32),
            "oh": hat(sr, True).astype(np.float32),
            "perc": perc_metal(sr).astype(np.float32),
        }
        self.playheads = {k: -1 for k in self.hits}
        self.hit_gain = {k: 1.0 for k in self.hits}
        self._built_key = key_root

    def load(self, seed: int | None = None, phrases: int = 12) -> Track:
        if seed is None:
            seed = time.time_ns() % 1_000_000_000
        track = generate(int(seed), phrases=phrases)
        with self.lock:
            if self.playing and self.track is not None:
                self._pending = track
            else:
                self._apply(track)
        return track

    def skip(self) -> Track:
        return self.load(None)

    def _apply(self, track: Track) -> None:
        self.track = track
        self.step = 0
        self.bar = 0
        acc = 0
        for p in track.phrases or []:
            if p.kind != "intro":
                self.bar = acc
                break
            acc += p.bars
        self.pos = 0
        self._duck = 1.0
        self._hp_x = [0.0, 0.0]
        self._hp_y = [0.0, 0.0]
        if track.key_root != self._built_key:
            self._load_hits(track.key_root)
        for v in self.voices:
            v.rest()
            v.amp = 0.0
        self.meter.seed = track.seed
        self.meter.bpm = track.bpm

    def start(self) -> None:
        if self.track is None:
            self.load(1)
        if self.stream is None:
            if sd is None:
                raise RuntimeError("sounddevice is not installed; live audio playback unavailable")
            self.stream = sd.OutputStream(
                samplerate=self.SR,
                channels=1,
                dtype="float32",
                blocksize=self.BLOCK,
                callback=self._callback,
            )
            self.stream.start()
        self.playing = True
        self.meter.playing = True

    def stop(self) -> None:
        self.playing = False
        self.meter.playing = False
        for v in self.voices:
            v.rest()

    def close(self) -> None:
        self.stop()
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def toggle(self) -> None:
        if self.playing:
            self.stop()
        else:
            self.start()

    def set_volume(self, v: float) -> None:
        self.volume = float(min(max(v, 0.0), 1.0))
        self.meter.volume = self.volume

    def feed_phrases(self) -> None:
        with self.lock:
            t = self.track
            bar = self.bar
        if t is None:
            return
        total = sum(p.bars for p in t.phrases) if t.phrases else 0
        if total - bar < 24:
            next_phrases(t, n=4, salt=bar)

    def _callback(self, outdata: np.ndarray, frames: int, _t, status) -> None:
        buf = outdata[:, 0]
        buf.fill(0.0)
        if not self.playing:
            self.meter.rms *= 0.9
            self.meter.kick *= 0.9
            return
        with self.lock:
            track = self.track
            pending = self._pending
        if track is None:
            return
        i = 0
        while i < frames:
            n = self._fill_step(buf, i, frames - i, track)
            i += n
            if pending is not None and self.pos == 0:
                with self.lock:
                    if self._pending is not None:
                        self._apply(self._pending)
                        self._pending = None
                        track = self.track
                        pending = None
        buf *= np.float32(self.volume)
        np.clip(buf, -1.0, 1.0, out=buf)
        w = self.wave
        take = min(frames, w.shape[0])
        if take:
            w[:-take] = w[take:]
            w[-take:] = buf[:take]
        m = self.meter
        m.rms = 0.85 * m.rms + 0.15 * float(np.sqrt(np.mean(buf * buf)))
        m.kick *= 0.92
        if self._kick_env > 0.5:
            m.kick = 1.0
        m.playing = True
        m.volume = self.volume
        if track:
            m.bpm = track.bpm
            m.seed = track.seed
            m.step = self.step
            m.bar = self.bar
        self._kick_env *= 0.85
        _ = status

    def _step_len(self, track: Track) -> int:
        q = self.SR * 60.0 / track.bpm / 4.0
        if self.step % 2 == 1:
            q += (track.swing - 0.5) * 2.0 * (self.SR * 60.0 / track.bpm / 4.0)
        return max(1, int(q))

    def _fill_step(self, buf: np.ndarray, i: int, remain: int, track: Track) -> int:
        slen = self._step_len(track)
        if self.pos == 0:
            self._trig(track)
        left = slen - self.pos
        n = remain if remain < left else left
        if n > len(self._scratch):
            n = len(self._scratch)
        phrase = _phrase_at(track.phrases, self.bar)
        layers = phrase.layers if phrase else ["kick", "ch", "clap", "oh", "perc", "acid0", "acid1"]
        cut = 0.45
        drive = 0.75
        if phrase:
            acc = 0
            local = 0.0
            for p in track.phrases:
                if self.bar < acc + p.bars:
                    local = self.bar - acc
                    break
                acc += p.bars
            cut = phrase.cutoff.at(local)
            drive = phrase.drive
        self.meter.cutoff = cut
        self.meter.drive = drive
        self.meter.phrase = phrase.kind if phrase else ""
        kick_bus = self._kick_bus[:n]
        rest = self._rest_bus[:n]
        kick_bus.fill(0.0)
        rest.fill(0.0)
        for name, hit in self.hits.items():
            if name not in layers:
                continue
            ph = self.playheads.get(name, -1)
            if ph < 0:
                continue
            take = n if n < (len(hit) - ph) else (len(hit) - ph)
            if take > 0:
                dest = kick_bus if name == "kick" else rest
                dest[:take] += hit[ph : ph + take] * self.hit_gain.get(name, 1.0)
                ph += take
            self.playheads[name] = ph if ph < len(hit) else -1
        for vi, voice in enumerate(self.voices):
            layer = "acid" + str(vi)
            if layer not in layers or vi >= len(track.acid):
                voice.rest()
            if voice.gate or voice.amp > 1e-4:
                chunk = voice.render(
                    n,
                    min(1.0, cut + vi * 0.08),
                    DNA["res_min"] + 0.12 + 0.08 * vi,
                    DNA["envmod"],
                    drive,
                    DNA["decay"],
                )
                if layer in layers:
                    grit = np.tanh(self._hpf_voice(chunk, vi) * 1.55)
                    rest += grit * (0.72 if vi == 0 else 0.52)
        self._duck += (1.0 - self._duck) * (1.0 - np.exp(-n / (0.055 * self.SR)))
        rest *= self._duck
        rest = np.tanh(rest * 1.08)
        mix = kick_bus * 1.45 + rest
        mix = np.clip(mix, -0.99, 0.99)
        buf[i : i + n] = mix.astype(np.float32)
        self.pos += n
        if self.pos >= slen:
            self.pos = 0
            self.step += 1
            if self.step >= 16:
                self.step = 0
                self.bar += 1
        return n

    def _trig(self, track: Track) -> None:
        phrase = _phrase_at(track.phrases, self.bar)
        layers = phrase.layers if phrase else []
        s = self.step

        def fire(name: str) -> None:
            lane = track.lane(name)
            if not lane or name not in layers:
                return
            vel = lane.vel[s] if s < len(lane.vel) else None
            if not vel:
                return
            gain = float(vel)
            if name == "kick":
                gain *= 1.85
                self._kick_env = 1.0
                self._duck = 0.26
            elif name == "clap":
                gain *= 0.5
            elif name in ("ch", "oh"):
                gain *= 0.16
            else:
                gain *= 0.28
            self.playheads[name] = 0
            self.hit_gain[name] = gain

        for name in ("kick", "clap", "ch", "oh", "perc"):
            fire(name)
        for vi, voice in enumerate(self.voices):
            layer = "acid" + str(vi)
            if layer not in layers or vi >= len(track.acid):
                voice.rest()
                continue
            pat = track.acid[vi]
            st = pat[s % len(pat)]
            if st.gate:
                voice.note(midi_hz(st.pitch), st.accent, st.slide)
            else:
                voice.rest()

    def _hpf_voice(self, x: np.ndarray, vi: int, fc: float = 115.0) -> np.ndarray:
        a = (1.0 / (2.0 * np.pi * fc)) / ((1.0 / (2.0 * np.pi * fc)) + 1.0 / self.SR)
        y = np.empty_like(x)
        px = self._hp_x[vi]
        py = self._hp_y[vi]
        for i, v in enumerate(x):
            py = a * (py + v - px)
            px = v
            y[i] = py
        self._hp_x[vi] = px
        self._hp_y[vi] = py
        return y
