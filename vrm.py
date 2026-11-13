#!/usr/bin/env python3
"""video-readme-maker CLI.  python3 vrm.py readme|video|all <spec.yml> [--silent] [--engine openai|kokoro|say]"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser(prog="vrm")
    ap.add_argument("cmd", choices=["readme", "video", "all", "voices", "verify"])
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--silent", action="store_true", help="no TTS; estimated durations (fast vertical slice)")
    ap.add_argument("--engine", help="force TTS engine: openai|kokoro|piper|say")
    ap.add_argument("--no-render", action="store_true", help="resolve scenes/narration/audio only")
    ap.add_argument("--no-check", action="store_true", help="skip leak lint (not recommended)")
    a = ap.parse_args()
    from common.spec import SpecError
    from common.leaks import LeakError
    try:
        if a.cmd == "voices":
            from video import tts
            print("openai key:", "found" if tts.find_openai_key() else "not found", "| kokoro:", "ready" if tts.kokoro_ready() else "not installed (run video/setup_voice.sh)",
                  "| say voice:", tts.best_say_voice(), "| auto ->", tts.pick_engine())
            return
        if a.cmd == "verify":
            from video import build_video
            build_video.verify(a.spec); return
        if not a.spec:
            ap.error("spec required")
        if a.cmd == "readme":
            from readme import build_readme
            for p in build_readme.build(a.spec, check=not a.no_check):
                print("wrote", os.path.relpath(p))
        if a.cmd in ("video", "all"):
            from video import build_video
            build_video.build(a.spec, silent=a.silent, engine=a.engine, skip_render=a.no_render)
            if a.cmd == "all":  # README after the video so its block picks up the fresh preview gif
                from readme import build_readme
                for p in build_readme.build(a.spec, check=not a.no_check):
                    print("wrote", os.path.relpath(p))
    except (SpecError, LeakError) as e:
        print("ERROR:", e, file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
