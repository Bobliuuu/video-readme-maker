"""Run inside the venv: python kokoro_synth.py <model_dir> <voice> <out.wav> [speed]  (text on stdin).
Synthesises sentence by sentence and joins them with short natural pauses (longer after a paragraph break)."""
import sys, os, re
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
mdir, voice, out = sys.argv[1:4]
speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
k = Kokoro(os.path.join(mdir, "kokoro-v1.0.onnx"), os.path.join(mdir, "voices-v1.0.bin"))
text = sys.stdin.read().strip()
sents = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text) if s.strip()]
parts, sr = [], 24000
for i, s in enumerate(sents):
    x, sr = k.create(s.strip(), voice=voice, speed=speed, lang="en-us")
    x = np.asarray(x, dtype=np.float32)
    parts.append(x)
    if i < len(sents) - 1:
        parts.append(np.zeros(int(sr * (0.34 if s.rstrip().endswith((".", "!", "?")) else 0.15)), dtype=np.float32))
sf.write(out, np.concatenate(parts) if parts else np.zeros(sr // 10, dtype=np.float32), sr)
