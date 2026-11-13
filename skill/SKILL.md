---
name: video-readme-maker
description: Use when starting a new project, writing or rewriting a README, making an explainer or demo video (with voice-over), or preparing a project to launch/publish. Turns a project's result files into a polished GitHub README (hero, badges, charts, diagrams, tables) and a narrated explainer video via the reusable toolkit at github.com/Bobliuuu/video-readme-maker.
---

# video-readme-maker

Reusable, data-driven toolkit: `spec.yml` + result files (JSON/CSV) -> README.md + assets + explainer.mp4 (voice-over, captions, music) + poster + preview.gif.

## Steps

1. Get the toolkit (never copy or re-implement it in the project):
   `[ -d ~/video-readme-maker ] && git -C ~/video-readme-maker pull || git clone https://github.com/Bobliuuu/video-readme-maker ~/video-readme-maker`
   Then once: `pip install -r ~/video-readme-maker/requirements.txt` and `cd ~/video-readme-maker/video && npm install`.
2. In the target project write `spec.yml` (copy `~/video-readme-maker/examples/demo/spec.yml` as the template; reference: the toolkit README).
   Every number must be declared under `numbers:` with `file:` + `path:` pointing at a real result file. No hand-typed numbers.
3. Run: `python3 ~/video-readme-maker/vrm.py all spec.yml` (`readme` or `video` alone also work; `--silent` for a fast no-voice slice; `vrm.py voices` shows which TTS engine will be used).
4. Apply the quality bar without asking the user: hero + H1 with emoji + badges + nav row; video block; results tables with sources; at least one chart and one architecture diagram; honest caveats; repo map; narration 40-90 s that explains the problem, idea, method, headline numbers, caveats.
   Public text shows ONLY current correct results: no failed-run stories, no IPs/hosts/keys (the generator lints; also run `~/.claude/skills/github-workflow/scan_leaks.sh` before commit/push).
5. If the toolkit lacks something (scene type, chart type, engine), improve it in `~/video-readme-maker` (commit + push to main, Conventional Commits) and re-run. Do not fork the logic into the project.
6. Verify: `python3 ~/video-readme-maker/vrm.py verify assets/explainer.mp4` (ffprobe size/duration/loudness, should be < 10 MB, about -16 LUFS); extract and LOOK at 3 frames
   (`ffmpeg -ss 5 -i assets/explainer.mp4 -frames:v 1 f1.png`, same at 50% and 90%); check README renders (hero, images, anchors, tables).
7. Voice: engine order is OpenAI TTS (needs OPENAI_API_KEY env or a key file; cents per video) > Kokoro local neural (`video/setup_voice.sh` once) > macOS `say`. Tell the user which engine was used.
8. Remind the user: GitHub renders a video inline only from a `https://github.com/user-attachments/assets/<id>` URL on its own line. That URL is created only by drag-dropping the mp4 into a GitHub issue/PR/README editor in the browser; it cannot be done by API. Until then the README uses the animated GIF preview linking to the mp4 (`video.url` empty). After the user supplies the URL, set `video.url` in spec.yml and re-run `vrm.py readme`.
