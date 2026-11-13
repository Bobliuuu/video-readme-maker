FONT = "ui-sans-serif,system-ui,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
DEFAULT = {"bg": "#0b0f17", "panel": "#131a26", "line": "#263044", "text": "#e6edf6", "muted": "#8a98ad",
           "accent": "#27c8e8", "accent2": "#ff6b6b", "accent3": "#f2c14e", "good": "#3ddc97"}


def theme(spec):
    t = dict(DEFAULT)
    t.update((spec.d.get("theme") or {}))
    return t


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
