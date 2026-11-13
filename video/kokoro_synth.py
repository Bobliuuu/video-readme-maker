"""Run inside the venv: python kokoro_synth.py <model_dir> <voice> <out.wav>  (text on stdin)."""
import sys, os
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
mdir, voice, out = sys.argv[1:4]
k = Kokoro(os.path.join(mdir, "kokoro-v1.0.onnx"), os.path.join(mdir, "voices-v1.0.bin"))
samples, sr = k.create(sys.stdin.read(), voice=voice, speed=1.0, lang="en-us")
sf.write(out, np.asarray(samples), sr)
