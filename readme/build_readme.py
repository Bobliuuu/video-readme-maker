"""spec.yml -> README.md + assets (hero, charts, diagrams). Fails loudly on missing numbers/files."""
import os, re
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from common.spec import Spec, SpecError
from common import leaks
from .theme import theme
from .hero import hero_svg
from .charts import chart_svg
from .diagram import diagram_svg


def _badge(b):
    from urllib.parse import quote
    q = lambda s: quote(str(s).replace("-", "--").replace("_", "__"), safe="")
    url = f"https://img.shields.io/badge/{q(b['label'])}-{q(b['message'])}-{b.get('color','blue').lstrip('#')}"
    extra = []
    if b.get("logo"):
        extra.append(f"logo={quote(b['logo'])}&logoColor=white")
    if b.get("style"):
        extra.append(f"style={b['style']}")
    if extra:
        url += "?" + "&".join(extra)
    img = f"![{b['label']}: {b['message']}]({url})"
    return f"[{img}]({b['link']})" if b.get("link") else img


def _md_table(t):
    al = {"left": ":---", "right": "---:", "center": ":---:"}
    out = ["| " + " | ".join(t["head"]) + " |", "| " + " | ".join(al[a] for a in t["align"]) + " |"]
    for i, r in enumerate(t["rows"]):
        cells = [f"**{c}**" if (t["highlight"] == i and c) else c for c in r]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def build(spec_path, check=True):
    sp = Spec(spec_path)
    d, root = sp.d, sp.root
    th = theme(sp)
    proj = d["project"]
    adir = d.get("assets_dir", "assets")
    os.makedirs(os.path.join(root, adir), exist_ok=True)
    R = sp.render
    written = []

    def write(rel, text):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        written.append(p)

    # hero
    h = d.get("hero", {})
    title = R(h.get("title", proj["name"]))
    write(f"{adir}/hero.svg", hero_svg(title, R(h.get("subtitle", proj.get("tagline", ""))), [R(c) for c in h.get("chips", [])], th))

    def img_md(rel, alt):
        return f"<p align=\"center\"><img src=\"{rel}\" alt=\"{alt}\" width=\"100%\"></p>"

    def render_section(s, nested=False):
        parts = []
        if s.get("body"):
            parts.append(R(s["body"]).strip())
        if s.get("body_file"):  # verbatim markdown kept in the project (not templated), e.g. docs/readme/01-intro.md
            with open(os.path.join(root, s["body_file"])) as bf:
                parts.append(bf.read().strip())
        if s.get("highlights"):
            hl = s["highlights"]
            head = "| " + " | ".join(R(x["label"]) for x in hl) + " |"
            sep = "|" + "|".join(":---:" for _ in hl) + "|"
            row = "| " + " | ".join(f"**{sp.num(x['number']).text}**" for x in hl) + " |"
            parts.append("\n".join([head, sep, row]))
        for tid in s.get("tables", []) or []:
            t = sp.table_by_id(tid)
            block = (f"**{t['title']}**\n\n" if t["title"] else "") + _md_table(t)
            if t["source"]:
                block += f"\n\n<sub>Source: `{t['source']}`</sub>"
            parts.append(block)
        for cid in s.get("charts", []) or []:
            m = sp.chart_by_id(cid)
            write(f"{adir}/{cid}.svg", chart_svg(m, th))
            parts.append(img_md(f"{adir}/{cid}.svg", m["title"]))
        for gid in s.get("diagrams", []) or []:
            m = sp.diagram_by_id(gid)
            write(f"{adir}/{gid}.svg", diagram_svg(m, th))
            parts.append(img_md(f"{adir}/{gid}.svg", m["title"] or gid))
        for im in s.get("images", []) or []:
            w = im.get("width", "100%")
            parts.append(f'<p align="center"><img src="{im["src"]}" alt="{R(im.get("alt", ""))}" width="{w}"></p>')
        for dt in s.get("details", []) or []:
            inner = render_section(dt, nested=True)
            parts.append(f"<details>\n<summary>{R(dt['summary'])}</summary>\n\n{inner.strip()}\n\n</details>")
        if s.get("after"):
            parts.append(R(s["after"]).strip())
        return "\n\n".join(parts)

    secs, nav = [], []

    def add(sid, emoji, ttl, content):
        nav.append((emoji, ttl, sid))
        secs.append(f'<a id="{sid}"></a>\n\n## {emoji} {ttl}\n\n{content}')

    sdir = d.get("sections_dir")  # verbatim markdown files NN-name.md; first line "# [emoji] Title"; new files appear automatically
    if sdir:
        import glob
        for fp in sorted(glob.glob(os.path.join(root, sdir, "*.md"))):
            txt = open(fp).read().strip()
            m = re.match(r"#{1,2}\s+(.+)\n", txt + "\n")
            if not m:
                raise SpecError(f"{fp}: first line must be '# Title'")
            ttl = m.group(1).strip()
            em = ""
            m2 = re.match(r"^(\S+)\s+(.*)$", ttl)
            if m2 and not re.match(r"^[\w(]", m2.group(1)):
                em, ttl = m2.group(1), m2.group(2)
            sid = re.sub(r"[^a-z0-9]+", "-", ttl.lower()).strip("-")
            add(sid, em, ttl, txt[m.end():].strip())
    for s in d.get("sections", []) or []:
        sid = s.get("id") or re.sub(r"[^a-z0-9]+", "-", s["title"].lower()).strip("-")
        add(sid, s.get("emoji", ""), R(s["title"]), render_section(s))
    cmp_ = d.get("compare")
    if cmp_:
        add("compare", cmp_.get("emoji", "⚖️"), R(cmp_.get("title", "How it compares")), render_section(cmp_))
    qs = d.get("quickstart")
    if qs:
        body = []
        for q in qs:
            body.append((f"**{R(q['title'])}**\n\n" if q.get("title") else "") + "```bash\n" + q["shell"].strip() + "\n```")
        add("quick-start", "🚀", "Quick start", "\n\n".join(body))
    cav = d.get("caveats")
    if cav:
        add("caveats", "⚠️", "Honest caveats", "\n".join(f"- {R(c)}" for c in cav))
    rm = d.get("repo_map")
    if rm:
        rows = ["| Path | What it is |", "|---|---|"]
        for r in rm:
            if not os.path.exists(os.path.join(root, r["path"])) and not r.get("generated"):
                raise SpecError(f"repo_map: path '{r['path']}' does not exist (set generated: true if built later)")
            rows.append(f"| `{r['path']}` | {R(r['desc'])} |")
        add("repo-map", "🗺️", "Repo map", "\n".join(rows))

    # video block
    v = d.get("video", {}) or {}
    vb = ""
    if v:
        gif, mp4, url = v.get("gif", f"{adir}/preview.gif"), v.get("mp4", f"{adir}/explainer.mp4"), v.get("url")
        cap = R(v.get("caption", "")) if v.get("caption") else ""
        if url:
            if not re.match(r"https://github\.com/user-attachments/assets/[\w-]+$|https://", url):
                raise SpecError("video.url must be an https URL (GitHub user-attachments URL renders inline)")
            vb = (f"**{cap}**\n\n" if cap else "") + url + "\n"  # bare URL on its own line renders inline on GitHub
        elif os.path.exists(os.path.join(root, gif)):
            vb = (f"**{cap}**\n\n" if cap else "") + f"[![Explainer video preview (click for the mp4)]({gif})]({mp4})\n"
    navs = d.get("nav")
    nav_items = [(n.get("emoji", ""), n["label"], n["anchor"]) for n in navs] if navs else nav
    nav_md = " · ".join(f"[{e} {l}](#{a})".replace("[ ", "[") for e, l, a in nav_items)

    badges = " ".join(_badge({k: R(v) if isinstance(v, str) else v for k, v in b.items()}) for b in d.get("badges", []) or [])
    env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__))), undefined=StrictUndefined, keep_trailing_newline=True)
    md = env.get_template("README.md.j2").render(
        hero_path=f"{adir}/hero.svg", title=title, emoji=proj.get("emoji", ""), tagline=R(proj["tagline"]), badges=badges, nav=nav_md,
        video_block=vb, intro=(R(d.get("intro", "")).strip() + ("\n\n" + open(os.path.join(root, d["intro_file"])).read().strip() if d.get("intro_file") else "")).strip(), body="\n\n".join(secs), footer=R(d.get("footer", "")))
    md = re.sub(r"\n{3,}", "\n\n", md)
    if check:
        leaks.check_public(sp.public_strings() + [md], "README")
    write(d.get("readme_out", "README.md"), md)
    if check:
        ok, out = leaks.external_scan(written)
        if not ok:
            raise leaks.LeakError("scan_leaks.sh flagged generated files:\n" + out)
    return written
