"""Boxes + arrows from a small spec. layout() returns resolved geometry used by both the README SVG and the video."""
from .theme import FONT, MONO, esc

BW, BH, GX, GY, PAD = 270, 104, 130, 80, 40


def layout(g, render=lambda s: s):
    nodes = {}
    maxc = maxr = 0
    for n in g["nodes"]:
        c, r = n.get("col", 0), n.get("row", 0)
        maxc, maxr = max(maxc, c), max(maxr, r)
        x, y = PAD + c * (BW + GX), PAD + 40 + r * (BH + GY)
        nodes[n["id"]] = {"id": n["id"], "label": render(n["label"]), "sub": render(n.get("sub", "")), "kind": n.get("kind", "box"),
                          "x": x, "y": y, "w": BW, "h": BH, "col": c, "row": r}
    edges = []
    for e in g.get("edges", []):
        for k in ("from", "to"):
            if e[k] not in nodes:
                raise ValueError(f"diagram {g.get('id')}: edge references unknown node '{e[k]}'")
        a, b = nodes[e["from"]], nodes[e["to"]]
        if b["col"] > a["col"]:
            p0, p1 = (a["x"] + a["w"], a["y"] + a["h"] / 2), (b["x"], b["y"] + b["h"] / 2)
            mx = (p0[0] + p1[0]) / 2
            pts = [p0, (mx, p0[1]), (mx, p1[1]), p1]
        elif b["col"] < a["col"]:
            p0, p1 = (a["x"], a["y"] + a["h"] / 2), (b["x"] + b["w"], b["y"] + b["h"] / 2)
            mx = (p0[0] + p1[0]) / 2
            pts = [p0, (mx, p0[1]), (mx, p1[1]), p1]
        elif b["row"] > a["row"]:
            pts = [(a["x"] + a["w"] / 2, a["y"] + a["h"]), (b["x"] + b["w"] / 2, b["y"])]
        else:
            pts = [(a["x"] + a["w"] / 2, a["y"]), (b["x"] + b["w"] / 2, b["y"] + b["h"])]
        edges.append({"from": e["from"], "to": e["to"], "label": render(e.get("label", "")), "pts": pts})
    W = PAD * 2 + (maxc + 1) * BW + maxc * GX
    H = PAD + 40 + (maxr + 1) * BH + maxr * GY + PAD
    return {"id": g.get("id"), "title": render(g.get("title", "")), "w": W, "h": H, "nodes": list(nodes.values()), "edges": edges}


def _wrap(s, n):
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + ([cur] if cur else [])


def diagram_svg(m, th):
    kc = {"box": th["accent"], "store": th["accent3"], "accent": th["accent2"], "io": th["good"]}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {m["w"]} {m["h"]}" width="{m["w"]}" height="{m["h"]}" role="img" aria-label="{esc(m["title"])}">',
         f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{th["muted"]}"/></marker></defs>',
         f'<rect width="{m["w"]}" height="{m["h"]}" rx="16" fill="{th["bg"]}"/>',
         f'<text x="{PAD}" y="42" font-family="{FONT}" font-weight="700" font-size="22" fill="{th["text"]}">{esc(m["title"])}</text>']
    for e in m["edges"]:
        pts = " ".join(f"{x:.0f},{y:.0f}" for x, y in e["pts"])
        o.append(f'<polyline points="{pts}" fill="none" stroke="{th["muted"]}" stroke-width="2.2" marker-end="url(#ah)"/>')
        if e["label"]:
            (x0, y0), (x1, y1) = e["pts"][0], e["pts"][-1]
            o.append(f'<text x="{(x0+x1)/2:.0f}" y="{(y0+y1)/2-8:.0f}" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{th["muted"]}">{esc(e["label"])}</text>')
    for n in m["nodes"]:
        c = kc.get(n["kind"], th["accent"])
        o.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" rx="12" fill="{th["panel"]}" stroke="{c}" stroke-width="2"/>')
        o.append(f'<text x="{n["x"]+n["w"]/2}" y="{n["y"]+38}" text-anchor="middle" font-family="{FONT}" font-weight="700" font-size="19" fill="{th["text"]}">{esc(n["label"])}</text>')
        for i, ln in enumerate(_wrap(n["sub"], 32)[:2]):
            o.append(f'<text x="{n["x"]+n["w"]/2}" y="{n["y"]+62+i*18}" text-anchor="middle" font-family="{MONO}" font-size="13" fill="{th["muted"]}">{esc(ln)}</text>')
    o.append("</svg>")
    return "\n".join(o)
