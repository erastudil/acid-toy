from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def write_wav(path: str | Path, samples: np.ndarray, sr: int = 44100) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.clip(samples, -1.0, 1.0)
    pcm = (x * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path
