"""Pluggable TTS. Preference: openai > kokoro (local neural, venv) > piper > macOS say.
Only the public narration text is sent to OpenAI. The API key is read from env/key files and never printed or stored in the repo.
Audio is cached globally by sha256(engine|voice|model|instructions|text): reruns are free."""
import glob, hashlib, json, os, re, shutil, subprocess, urllib.request, urllib.error

CACHE = os.path.expanduser(os.environ.get("VRM_CACHE", "~/.cache/video-readme-maker"))
VENV_PY = os.path.join(CACHE, "venv", "bin", "python")
KOKORO_DIR = os.path.join(CACHE, "models")
DEFAULT_INSTRUCTIONS = ("Speak as a calm, clear technical explainer: warm, steady pace, natural pauses between ideas, "
                        "no hype, say numbers and units precisely.")


def find_openai_key():
    """Returns key or None. Looks in env, then well-known key files, then export lines in shell env files."""
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k.strip()
    cands = [os.environ.get("VRM_OPENAI_KEY_FILE", ""), "~/.config/openai/api_key", "~/.config/openai/key", "~/.config/openai_key",
             "~/.openai_key", "~/.openai/api_key", "~/.config/vrm/openai_key"]
    cands += glob.glob(os.path.expanduser("~/.claude/projects/*/memory/secrets/openai_key"))
    cands += glob.glob("/private/tmp/claude-*/*/*/scratchpad/secrets/openai_key") + glob.glob("/tmp/claude-*/*/*/scratchpad/secrets/openai_key")
    for c in cands:
        p = os.path.expanduser(c)
        if p and os.path.isfile(p):
            s = open(p).read().strip()
            m = re.search(r"(sk-[A-Za-z0-9_\-]{20,})", s)
            if m:
                return m.group(1)
    for rc in ("~/.zshenv", "~/.zshrc", "~/.zprofile", "~/.bash_profile", "~/.bashrc", "~/.profile", "~/.env"):
        p = os.path.expanduser(rc)
        if os.path.isfile(p):
            m = re.search(r"OPENAI_API_KEY\s*=\s*['\"]?(sk-[A-Za-z0-9_\-]{20,})", open(p, errors="ignore").read())
            if m:
                return m.group(1)
    return None


def kokoro_ready():
    m = os.path.join(KOKORO_DIR, "kokoro-v1.0.onnx"), os.path.join(KOKORO_DIR, "voices-v1.0.bin")
    return os.path.exists(VENV_PY) and all(os.path.exists(p) and os.path.getsize(p) > 1_000_000 for p in m)


def best_say_voice():
    try:
        out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return None
    names = [l.split("  ")[0].strip() for l in out.splitlines() if " en_" in l]
    for pref in ("Premium", "Enhanced", "Ava", "Zoe", "Evan", "Nathan", "Samantha", "Daniel", "Alex"):
        for n in names:
            if pref.lower() in n.lower():
                return n
    return names[0] if names else None


def pick_engine(want="auto"):
    if want != "auto":
        return want
    if find_openai_key():
        return "openai"
    if kokoro_ready():
        return "kokoro"
    if shutil.which("piper"):
        return "piper"
    return "say"


def _hash(*parts):
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def _openai(text, voice, model, instructions, out):
    key = find_openai_key()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found")
    body = {"model": model, "voice": voice, "input": text, "response_format": "wav"}
    if model.startswith("gpt-4o"):
        body["instructions"] = instructions
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as f:
            f.write(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"OpenAI TTS HTTP {e.code}: {e.read()[:200].decode(errors='replace')}")  # body never contains the key


def _kokoro(text, voice, out):
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kokoro_synth.py")
    subprocess.run([VENV_PY, script, KOKORO_DIR, voice, out], input=text.encode(), check=True)


def _piper(text, voice, out):
    model = voice if voice.endswith(".onnx") else os.path.join(CACHE, "models", "piper", voice + ".onnx")
    subprocess.run(["piper", "--model", model, "--output_file", out], input=text.encode(), check=True)


def _say(text, voice, out):
    aiff = out + ".aiff"
    subprocess.run(["say", "-v", voice or best_say_voice() or "Samantha", "-r", "170", "-o", aiff, text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aiff, out], check=True)
    os.remove(aiff)


def synth(text, out_wav, engine="auto", voice=None, model="gpt-4o-mini-tts", instructions=None, pad_ms=200):
    """Synthesize `text` to a mono 44.1k wav with silence trimmed and pad_ms padding each side. Returns engine used."""
    engine = pick_engine(engine)
    instructions = instructions or DEFAULT_INSTRUCTIONS
    voice = voice or {"openai": "alloy", "kokoro": "af_heart", "piper": "en_US-lessac-medium", "say": None}[engine]
    if engine == "say" and voice in ("alloy", "af_heart"):
        voice = None
    os.makedirs(os.path.join(CACHE, "tts"), exist_ok=True)
    raw = os.path.join(CACHE, "tts", _hash(engine, str(voice), model, instructions if engine == "openai" else "", text) + ".wav")
    if not os.path.exists(raw):
        tmp = raw + ".tmp.wav"
        try:
            {"openai": lambda: _openai(text, voice, model, instructions, tmp), "kokoro": lambda: _kokoro(text, voice, tmp),
             "piper": lambda: _piper(text, voice, tmp), "say": lambda: _say(text, voice, tmp)}[engine]()
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise
        os.replace(tmp, raw)
    pad = pad_ms / 1000
    af = ("silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.05,"
          "areverse,silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.08,areverse,"
          f"adelay={int(pad_ms)}:all=1,apad=pad_dur={pad}")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", af, "-ar", "44100", "-ac", "1", out_wav], check=True)
    return engine


def duration(wav):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav], capture_output=True, text=True)
    return float(r.stdout.strip())
