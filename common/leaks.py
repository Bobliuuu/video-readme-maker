"""Pre-write safety scan: IPs, hostnames, keys/tokens; plus 'failed-run story' lint for public text."""
import os, re, subprocess

PATTERNS = {
    "ipv4": re.compile(r"\b(?!(?:127\.0\.0\.1|0\.0\.0\.0|255\.255\.\d+\.\d+)\b)(?:\d{1,3}\.){3}\d{1,3}\b"),
    "openai/anthropic key": re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),
    "github token": re.compile(r"\b(?:ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{20,}"),
    "aws key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "ec2/internal host": re.compile(r"\b[\w.-]*(?:\.compute(?:-\d)?\.amazonaws\.com|\.internal|\.lan|\.local)\b", re.I),
    "ssh target": re.compile(r"\bssh\s+(?:-\w+\s+)*[\w.-]+@[\w.-]+"),
}
FAILED_STORY = re.compile(
    r"\b(failed (?:run|attempt)s?|earlier attempts?|first attempt|didn'?t work|did not work|previous (?:run|attempt)s?|"
    r"we (?:had|hit) a bug|used to be broken|was broken)\b", re.I)


class LeakError(Exception):
    pass


def scan_text(text, label="text"):
    hits = []
    for name, rx in PATTERNS.items():
        for m in rx.finditer(text):
            s = m.group(0)
            if name == "ipv4" and any(int(p) > 255 for p in s.split(".")):
                continue
            if name == "ipv4" and re.fullmatch(r"\d+\.\d+\.\d+\.\d+", s) and re.search(r"v?\d+\.\d+\.\d+\.\d+", text[max(0, m.start()-1):m.start()+len(s)]) and text[max(0, m.start()-1):m.start()].lower() == "v":
                continue
            hits.append(f"{label}: {name}: {s[:6]}***")
    return hits


def check_public(strings, label="spec"):
    errs = []
    for s in strings:
        errs += scan_text(s, label)
        m = FAILED_STORY.search(s)
        if m:
            errs.append(f"{label}: failed-run story ('{m.group(0)}'): public text must show only current correct results")
    if errs:
        raise LeakError("refusing to write public output:\n  " + "\n  ".join(errs))


def external_scan(paths):
    """Call the user's scan_leaks.sh if present. Returns (ok, output)."""
    sh = os.path.expanduser("~/.claude/skills/github-workflow/scan_leaks.sh")
    if not os.path.isfile(sh) or not paths:
        return True, ""
    r = subprocess.run(["bash", sh, "paths", *paths], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()
