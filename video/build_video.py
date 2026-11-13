"""spec.yml -> narrated explainer video (+ srt, poster, preview gif). Scene durations derive from the narration audio."""
import json, os, re, shutil, subprocess, sys, wave
import numpy as np
from common.spec import Spec, SpecError
from common import leaks
from readme.theme import theme
from . import tts
from .make_music import make_music, SR

HERE = os.path.dirname(os.path.abspath(__file__))
LEAD, TAIL, MIN_DUR = 0.4, 0.6, 2.8


def movavg(x, k):
    """Centered moving average in O(n) (cumsum), so ducking stays fast on long tracks."""
    c = np.cumsum(np.insert(x.astype(np.float64), 0, 0))
    i = np.arange(len(x))
    lo, hi = np.clip(i - k // 2, 0, len(x)), np.clip(i + k // 2, 0, len(x))
    return ((c[hi] - c[lo]) / np.maximum(1, hi - lo)).astype(np.float32)


def sh(*a, **k):
    return subprocess.run(list(map(str, a)), check=True, **k)


def split_caption(text, maxc=96):
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    out = []
    for s in sents:
        while len(s) > maxc:
            cut = max(s.rfind(", ", 0, maxc), s.rfind(" ", 0, maxc))
            cut = cut if cut > 20 else maxc
            out.append(s[:cut + 1].strip().rstrip(",")); s = s[cut + 1:].strip()
        if s:
            out.append(s)
    return out


def resolve_scene(sp, s, idx):
    t = s["type"]
    o = {k: (sp.render(v) if isinstance(v, (str, list, dict)) and k not in ("code", "type", "chart", "table", "diagram", "number", "ratio") else v)
         for k, v in s.items()}
    o["id"] = f"s{idx:02d}_{t}"
    if t == "chart":
        o["chart"] = sp.chart_by_id(s["chart"])
    elif t == "table":
        o["table"] = sp.table_by_id(s["table"])
    elif t == "architecture":
        o["diagram"] = sp.diagram_by_id(s["diagram"])
    elif t == "stat":
        o["number"] = sp.num(s["number"]).js()
    elif t == "comparison":
        for side in ("left", "right"):
            o[side] = dict(o[side], number=sp.num(s[side]["number"]).js())
        if s.get("ratio"):
            o["ratio"] = sp.num(s["ratio"]).js()
    elif t == "results":
        o["items"] = [dict(label=sp.render(i["label"]), number=sp.num(i["number"]).js()) for i in s["items"]]
    elif t == "end":
        repo = sp.d["project"].get("repo")
        o.setdefault("title", sp.d["project"]["name"])
        o.setdefault("url", f"github.com/{repo}" if repo else "")
    elif t not in ("title", "problem", "idea", "caveats", "code", "terminal"):
        raise SpecError(f"unknown scene type '{t}'")
    return o


def srt_time(x):
    h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def build(spec_path, silent=False, engine=None, skip_render=False, fps=None, reuse_data=False):
    sp = Spec(spec_path)
    d = sp.d
    V = d["video"]
    th = theme(sp)
    out = os.path.join(sp.root, V.get("out_dir", "out/video"))
    adir = os.path.join(sp.root, d.get("assets_dir", "assets"))
    aud = os.path.join(out, "audio")
    os.makedirs(aud, exist_ok=True); os.makedirs(adir, exist_ok=True)
    scenes = [resolve_scene(sp, s, i + 1) for i, s in enumerate(V["scenes"])]
    leaks.check_public([sc.get("say", "") for sc in scenes], "narration")

    vcfg = V.get("voice", {}) or {}
    eng_want = engine or vcfg.get("engine", "auto")
    used = None
    for sc in scenes:
        say = (sc.get("say") or "").strip()
        sc["lead"] = LEAD
        if say and not silent:
            wav = os.path.join(aud, sc["id"] + ".wav")
            used = tts.synth(say, wav, engine=eng_want, voice=vcfg.get("voice"), model=vcfg.get("model", "gpt-4o-mini-tts"),
                             instructions=vcfg.get("instructions"), pad_ms=vcfg.get("pad_ms", 200))
            sc["audio"] = wav
            alen = tts.duration(wav)
        else:
            alen = (len(say.split()) / 2.7) if say else 0
        sc["alen"] = alen
        sc["dur"] = round(max(sc.get("min_dur", MIN_DUR), LEAD + alen + TAIL), 2)
        chunks = split_caption(say) if say else []
        tot = sum(len(c) for c in chunks) or 1
        t0, caps = LEAD, []
        for c in chunks:
            w = alen * len(c) / tot
            caps.append({"t0": round(t0, 3), "t1": round(t0 + w, 3), "text": c}); t0 += w
        sc["caps"] = caps
    if used:
        print(f"[voice] engine={used}")
    st = 0.0
    for sc in scenes:
        sc["start"] = st; st += sc["dur"]
    total = st
    meta = {"fps": fps or V.get("fps", 30), "width": 1920, "height": 1080, "name": d["project"]["name"], "theme": th, "captions": V.get("captions", True),
            "crf": V.get("render_crf", 17)}
    data = {"meta": meta, "scenes": [{k: v for k, v in sc.items() if k != "audio"} for sc in scenes]}
    dj = os.path.join(out, "data.json")
    json.dump(data, open(dj, "w"), indent=1)
    with open(os.path.join(out, "captions.srt"), "w") as f:
        n = 1
        for sc in scenes:
            for c in sc["caps"]:
                f.write(f"{n}\n{srt_time(sc['start']+c['t0'])} --> {srt_time(sc['start']+c['t1'])}\n{c['text']}\n\n"); n += 1
    shutil.copy(os.path.join(out, "captions.srt"), os.path.join(adir, "explainer.srt"))
    print(f"[video] {len(scenes)} scenes, {total:.1f}s")
    if skip_render:
        return data

    # ---- frames
    node = shutil.which("node") or sys.exit("node not found")
    if not os.path.isdir(os.path.join(HERE, "node_modules", "puppeteer-core")):
        sh("npm", "install", "--silent", cwd=HERE)
    shutil.rmtree(os.path.join(out, "seg"), ignore_errors=True)
    sh(node, os.path.join(HERE, "render.js"), "--data", dj, "--out", out, "--conc", V.get("concurrency", 4))
    sh(node, os.path.join(HERE, "render.js"), "--data", dj, "--out", out, "--stills", V.get("poster_at", round(scenes[0]["dur"] * .65, 1)))
    poster_src = [f for f in os.listdir(os.path.join(out, "stills"))][0]
    shutil.copy(os.path.join(out, "stills", poster_src), os.path.join(adir, "poster.png"))

    # ---- audio: voice track + ducked generated music
    voice = np.zeros(int((total + 1) * SR), dtype=np.float32)
    for sc in scenes:
        if sc.get("audio"):
            with wave.open(sc["audio"]) as w:
                x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
            s0 = int((sc["start"] + sc["lead"] - 0.2) * SR)  # tts wav already carries 0.2s pad
            s0 = max(0, s0)
            voice[s0:s0 + len(x)] += x[:len(voice) - s0]
    mix = None
    mus = V.get("music", True)
    if mus:
        m = make_music(total + 1, seed=d["project"]["name"])
        env = movavg(np.abs(voice), int(.25 * SR))
        env = np.clip(env / (np.percentile(env, 95) + 1e-9), 0, 1)
        env = movavg(env, int(.4 * SR))
        gain = (0.20 if used else 0.55) * (1 - 0.8 * np.clip(env, 0, 1))  # music sits ~ -14 dB, ducked a further ~14 dB under speech
        mix = m * gain[None, :m.shape[1]]
    if mix is None:
        mix = np.zeros((2, len(voice)), dtype=np.float32)
    mix[:, :len(voice)] += voice[None, :] * 0.9
    mix = np.clip(mix, -1, 1)
    mw = os.path.join(out, "mix.wav")
    with wave.open(mw, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype("<i2").tobytes())

    # ---- mux with loudness normalisation, size-capped video encode
    final = os.path.join(adir, "explainer.mp4")
    cap_mb = V.get("max_mb", 9.0)
    vbr = max(300, int(cap_mb * 8 * 1000 / total - 160))
    sh("ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(out, "video_silent.mp4"), "-i", mw,
       "-filter_complex", f"[1:a]atrim=0:{total:.2f},loudnorm=I=-16:TP=-1.5:LRA=11[a]", "-map", "0:v", "-map", "[a]",
       "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", f"{vbr}k", "-bufsize", f"{vbr*2}k", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", "-shortest", final)

    # ---- preview gif: whole video time-compressed to ~14 s
    gif = os.path.join(adir, "preview.gif")
    speed = max(1.0, total / 14)
    sh("ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(out, "video_silent.mp4"), "-vf",
       f"setpts=PTS/{speed:.3f},fps=8,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=4", "-loop", "0", gif)
    ok, msg = leaks.external_scan([final, gif, os.path.join(adir, "explainer.srt")])
    return verify(final, gif, total)


def verify(final, gif=None, total=None):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,duration:format=duration,size", "-of", "json", final],
                       capture_output=True, text=True)
    info = json.loads(r.stdout)
    e = subprocess.run(["ffmpeg", "-nostats", "-i", final, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", e)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)
    size = int(info["format"]["size"]) / 1e6
    print(f"[verify] {final}: {size:.2f} MB, {float(info['format']['duration']):.1f}s, streams={[(s['codec_name'], s.get('width')) for s in info['streams']]}, "
          f"integrated loudness={m[-1] if m else '?'} LUFS, true peak={tp[-1] if tp else '?'} dBFS")
    if gif and os.path.exists(gif):
        print(f"[verify] preview.gif {os.path.getsize(gif)/1e6:.2f} MB")
    if size > 10:
        print("[warn] video larger than 10 MB; lower video.max_mb or shorten scenes")
    return info
