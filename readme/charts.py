"""Pure-SVG charts (bar / line / scatter). Dark card so they read on both light and dark GitHub themes."""
from .theme import FONT, MONO, esc


def _nice(v):
    import math
    if v <= 0:
        return 1
    e = 10 ** math.floor(math.log10(v))
    for m in (1, 2, 2.5, 5, 10):
        if v <= m * e:
            return m * e
    return 10 * e


def _head(m, th, W, H):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(m["title"])}">',
         f'<rect width="{W}" height="{H}" rx="16" fill="{th["bg"]}"/>',
         f'<text x="32" y="44" font-family="{FONT}" font-weight="700" font-size="22" fill="{th["text"]}">{esc(m["title"])}</text>']
    if m.get("subtitle"):
        s.append(f'<text x="32" y="68" font-family="{MONO}" font-size="14" fill="{th["muted"]}">{esc(m["subtitle"])}</text>')
    return s


def _foot(m, th, W, H):
    note = ("lower is better" if m.get("better") == "lower" else "higher is better")
    src = ("source: " + ", ".join(m["sources"]) + " · ") if m.get("sources") else ""
    return f'<text x="{W-32}" y="{H-14}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{th["muted"]}">{esc(src + note)}</text>'


def bar_svg(m, th):
    bars = m["bars"]
    W, rowh = 980, 46
    H = 110 + rowh * len(bars) + 30
    s = _head(m, th, W, H)
    lw = min(380, max(120, 9 * max(len(b["label"]) for b in bars)))
    x0, x1 = 32 + lw, W - 150
    vmax = max(b["value"] for b in bars) or 1
    for i, b in enumerate(bars):
        y = 96 + i * rowh
        wbar = max(2, (x1 - x0) * b["value"] / vmax)
        col = th["accent"] if b["hl"] else th["line"]
        s.append(f'<text x="{32+lw-14}" y="{y+22}" text-anchor="end" font-family="{FONT}" font-size="15" fill="{th["text"] if b["hl"] else th["muted"]}" font-weight="{700 if b["hl"] else 400}">{esc(b["label"])}</text>')
        s.append(f'<rect x="{x0}" y="{y}" width="{wbar:.1f}" height="30" rx="6" fill="{col}"/>')
        s.append(f'<text x="{x0+wbar+10:.1f}" y="{y+21}" font-family="{MONO}" font-size="15" font-weight="700" fill="{th["text"]}">{esc(b["text"])}</text>')
    s.append(_foot(m, th, W, H))
    s.append("</svg>")
    return "\n".join(s)


def _axes(m, th, W, H, L, R, T, B, xmin, xmax, ymin, ymax):
    s = []
    for i in range(5):
        v = ymin + (ymax - ymin) * i / 4
        y = B - (B - T) * i / 4
        s.append(f'<line x1="{L}" x2="{R}" y1="{y:.0f}" y2="{y:.0f}" stroke="{th["line"]}" stroke-width="1"/>')
        s.append(f'<text x="{L-10}" y="{y+4:.0f}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{th["muted"]}">{v:,.4g}</text>')
        xv = xmin + (xmax - xmin) * i / 4
        s.append(f'<text x="{L+(R-L)*i/4:.0f}" y="{B+20}" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{th["muted"]}">{xv:,.4g}</text>')
    if m.get("xlabel"):
        s.append(f'<text x="{(L+R)/2}" y="{B+44}" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{th["muted"]}">{esc(m["xlabel"])}</text>')
    if m.get("ylabel"):
        s.append(f'<text x="14" y="{(T+B)/2}" transform="rotate(-90 14 {(T+B)/2})" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{th["muted"]}">{esc(m["ylabel"])}</text>')
    return s


def line_svg(m, th):
    W, H, L, R, T, B = 980, 460, 80, 940, 96, 380
    pal = [th["accent"], th["accent2"], th["accent3"], th["good"]]
    allp = [p for s in m["series"] for p in s["pts"]]
    xmin, xmax = min(p[0] for p in allp), max(p[0] for p in allp)
    ymin, ymax = min(0, min(p[1] for p in allp)), max(p[1] for p in allp) * 1.05
    xmax = xmax if xmax > xmin else xmin + 1
    s = _head(m, th, W, H) + _axes(m, th, W, H, L, R, T, B, xmin, xmax, ymin, ymax)
    for i, se in enumerate(m["series"]):
        c = pal[i % 4]
        pts = " ".join(f"{L+(R-L)*(x-xmin)/(xmax-xmin):.1f},{B-(B-T)*(y-ymin)/(ymax-ymin):.1f}" for x, y in se["pts"])
        s.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>')
        lx, ly = pts.split()[-1].split(",")
        if se["name"]:
            s.append(f'<text x="{float(lx)-6:.0f}" y="{float(ly)-12:.0f}" text-anchor="end" font-family="{FONT}" font-size="14" font-weight="700" fill="{c}">{esc(se["name"])}</text>')
    s += [_foot(m, th, W, H), "</svg>"]
    return "\n".join(s)


def scatter_svg(m, th):
    W, H, L, R, T, B = 980, 480, 80, 940, 96, 390
    pts = m["pts"]
    xmin, xmax = min(0, min(p["x"] for p in pts)), max(p["x"] for p in pts) * 1.08
    ymin, ymax = min(0, min(p["y"] for p in pts)), max(p["y"] for p in pts) * 1.08
    s = _head(m, th, W, H) + _axes(m, th, W, H, L, R, T, B, xmin, xmax, ymin, ymax)
    for p in pts:
        x, y = L + (R - L) * (p["x"] - xmin) / (xmax - xmin), B - (B - T) * (p["y"] - ymin) / (ymax - ymin)
        c = th["accent"] if p["hl"] else th["accent3"]
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{10 if p["hl"] else 7}" fill="{c}" fill-opacity=".9" stroke="{th["bg"]}" stroke-width="2"/>')
        if p["label"]:
            s.append(f'<text x="{x+14:.1f}" y="{y+5:.1f}" font-family="{FONT}" font-size="14" fill="{th["text"]}" font-weight="{700 if p["hl"] else 400}">{esc(p["label"])}</text>')
    s += [_foot(m, th, W, H), "</svg>"]
    return "\n".join(s)


def chart_svg(m, th):
    return {"bar": bar_svg, "line": line_svg, "scatter": scatter_svg}[m["type"]](m, th)
