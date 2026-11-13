#!/usr/bin/env bash
# One-time: local neural TTS fallback (Kokoro-82M via kokoro-onnx) in a venv under ~/.cache/video-readme-maker. ~350 MB download.
set -e
C="${VRM_CACHE:-$HOME/.cache/video-readme-maker}"; mkdir -p "$C/models"
if command -v uv >/dev/null; then uv venv "$C/venv" --python 3.12 -q || uv venv "$C/venv" -q; VIRTUAL_ENV="$C/venv" uv pip install -q kokoro-onnx soundfile numpy
else python3 -m venv "$C/venv"; "$C/venv/bin/pip" install -q kokoro-onnx soundfile numpy; fi
R=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s "$C/models/kokoro-v1.0.onnx" ] || curl -L -o "$C/models/kokoro-v1.0.onnx" $R/kokoro-v1.0.onnx
[ -s "$C/models/voices-v1.0.bin" ] || curl -L -o "$C/models/voices-v1.0.bin" $R/voices-v1.0.bin
echo "kokoro ready"
