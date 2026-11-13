"""Spec loading, number resolution (every number traced to a result file), table/chart models."""
import csv, json, math, os, re
import yaml
from jinja2 import Environment, StrictUndefined


class SpecError(Exception):
    pass


class Num:
    """A number that came from a result file (or is derived from such numbers)."""

    def __init__(self, name, value, text, dec, unit, source):
        self.name, self.value, self.dec, self.unit, self.source = name, value, dec, unit, source
        self.numtext = text
        self.text = text + unit

    def __str__(self):
        return self.text

    def __format__(self, spec):
        return format(self.value, spec) if spec else self.text

    def js(self):
        return {"v": self.value, "dec": self.dec, "unit": self.unit, "text": self.text}


def _fmt(value, fmt):
    if fmt in (None, "auto"):
        if isinstance(value, float) and not float(value).is_integer():
            s = f"{value:,.1f}" if abs(value) >= 100 else (f"{value:,.2f}" if abs(value) >= 1 else f"{value:.3g}")
        else:
            s = f"{int(value):,}"
    else:
        s = fmt.format(value)
    m = re.search(r"\.(\d+)$", s.replace(",", ""))
    return s, (len(m.group(1)) if m else 0)


def _load_file(root, rel):
    p = os.path.join(root, rel)
    if not os.path.isfile(p):
        raise SpecError(f"result file not found: {rel} (looked in {p})")
    if rel.endswith(".json"):
        with open(p) as f:
            return json.load(f)
    if rel.endswith(".csv"):
        with open(p, newline="") as f:
            return list(csv.DictReader(f))
    raise SpecError(f"unsupported result file type: {rel} (use .json or .csv)")


def dig(obj, path, where=""):
    """path like 'a.b.0.c'; for CSV (list of dicts) use 'rowkey=value.col' e.g. 'name=ours.tok_s'."""
    cur = obj
    for part in str(path).split("."):
        if isinstance(cur, list) and "=" in part:
            k, v = part.split("=", 1)
            hits = [r for r in cur if str(r.get(k)) == v]
            if not hits:
                raise SpecError(f"{where}: no row with {k}={v}")
            cur = hits[0]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                raise SpecError(f"{where}: bad index '{part}'")
        elif isinstance(cur, dict):
            if part not in cur:
                raise SpecError(f"{where}: key '{part}' missing (have: {', '.join(list(cur)[:8])})")
            cur = cur[part]
        else:
            raise SpecError(f"{where}: cannot descend into '{part}'")
    return cur


class Spec:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.root = os.path.dirname(self.path)
        with open(self.path) as f:
            self.d = yaml.safe_load(f) or {}
        self._files = {}
        self.n = {}
        self.env = Environment(undefined=StrictUndefined, keep_trailing_newline=False)
        self._resolve_numbers()

    # ---- files
    def file(self, rel):
        if rel not in self._files:
            self._files[rel] = _load_file(self.root, rel)
        return self._files[rel]

    # ---- numbers
    def _resolve_numbers(self):
        raw = self.d.get("numbers", {}) or {}
        pending = dict(raw)
        for name, c in raw.items():
            if isinstance(c, str):  # "file.json:path.to.key"
                f, _, p = c.partition(":")
                c = {"file": f, "path": p}
                pending[name] = c
            if "file" in c:
                where = f"numbers.{name}"
                val = dig(self.file(c["file"]), c["path"], where)
                try:
                    val = float(val)
                except (TypeError, ValueError):
                    raise SpecError(f"{where}: value {val!r} is not numeric")
                if val.is_integer() and "fmt" not in c:
                    val = int(val)
                txt, dec = _fmt(val, c.get("fmt"))
                self.n[name] = Num(name, val, txt, dec, c.get("unit", ""), f"{c['file']}:{c['path']}")
        for name, c in raw.items():  # derived
            if isinstance(c, dict) and "expr" in c:
                ns = {k: v.value for k, v in self.n.items()}
                try:
                    val = eval(c["expr"], {"__builtins__": {}, "abs": abs, "round": round, "min": min, "max": max, "math": math}, ns)
                except Exception as e:
                    raise SpecError(f"numbers.{name}: expr failed: {e}")
                txt, dec = _fmt(val, c.get("fmt"))
                self.n[name] = Num(name, val, txt, dec, c.get("unit", ""), f"derived: {c['expr']}")
            elif isinstance(c, dict) and "file" not in c:
                raise SpecError(f"numbers.{name}: needs file+path or expr")

    def render(self, text):
        """Render a string with jinja; `n.<name>` are sourced numbers. Undefined -> loud error."""
        if isinstance(text, list):
            return [self.render(x) for x in text]
        if isinstance(text, dict):
            return {k: self.render(v) for k, v in text.items()}
        if not isinstance(text, str):
            return text
        try:
            return self.env.from_string(text).render(n=self.n, spec=self.d)
        except Exception as e:
            raise SpecError(f"template error in {text[:60]!r}: {e}")

    def num(self, name):
        if name not in self.n:
            raise SpecError(f"unknown number '{name}' (define it under numbers:)")
        return self.n[name]

    # ---- tables
    def table_model(self, t):
        rows_src = None
        if "file" in t:
            data = self.file(t["file"])
            if "rows_path" in t:
                data = dig(data, t["rows_path"], f"table {t.get('id')}")
            if isinstance(data, dict):
                data = [dict(name=k, **v) if isinstance(v, dict) else {"name": k, "value": v} for k, v in data.items()]
            rows_src = data
            source = t["file"]
        else:
            rows_src, source = None, None
        cols = t["columns"]
        rows = []
        if rows_src is not None:
            for r in rows_src:
                out = []
                for c in cols:
                    if c["key"] not in r:
                        raise SpecError(f"table {t.get('id')}: column '{c['key']}' missing in {source}")
                    v = r[c["key"]]
                    out.append(self._cell(v, c))
                rows.append(out)
        else:  # inline rows may reference numbers
            for r in t["rows"]:
                rows.append([self._cell(self.render(v) if isinstance(v, str) else v, c) for v, c in zip(r, cols)])
        hl = t.get("highlight")
        hl_idx = None
        if hl is not None:
            for i, r in enumerate(rows):
                if str(r[0]) == str(hl):
                    hl_idx = i
        return {"id": t.get("id"), "title": t.get("title", ""), "head": [c["title"] for c in cols], "rows": rows,
                "highlight": hl_idx, "source": t.get("source", source), "align": [c.get("align", "left") for c in cols]}

    def _cell(self, v, c):
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return _fmt(v, c.get("fmt"))[0] + c.get("unit", "")
        return str(v)

    # ---- chart models (shared by SVG generator and the video)
    def chart_model(self, c):
        typ = c["type"]
        m = {"id": c.get("id"), "type": typ, "title": self.render(c.get("title", "")), "subtitle": self.render(c.get("subtitle", "")),
             "unit": c.get("unit", ""), "xlabel": c.get("xlabel", ""), "ylabel": c.get("ylabel", ""),
             "source": c.get("source"), "better": c.get("better", "higher")}
        sources = []
        if typ == "bar":
            bars = []
            if "items" in c:
                for it in c["items"]:
                    n = self.num(it["number"])
                    bars.append({"label": self.render(it["label"]), "value": n.value, "text": n.text, "dec": n.dec, "unit": n.unit,
                                 "hl": bool(it.get("highlight"))})
                    sources.append(n.source.split(':')[0] if not n.source.startswith('derived') else 'derived')
            else:
                data = self.file(c["file"])
                if "rows_path" in c:
                    data = dig(data, c["rows_path"], f"chart {c.get('id')}")
                sources.append(c["file"])
                for r in data:
                    for k in (c["label"], c["y"]):
                        if k not in r:
                            raise SpecError(f"chart {c.get('id')}: '{k}' missing in {c['file']}")
                    v = float(r[c["y"]])
                    txt, dec = _fmt(v, c.get("fmt"))
                    bars.append({"label": str(r[c["label"]]), "value": v, "text": txt + c.get("unit", ""), "dec": dec,
                                 "unit": c.get("unit", ""), "hl": str(r[c["label"]]) == str(c.get("highlight"))})
            m["bars"] = bars
        elif typ == "gbar":
            data = self.file(c["file"])
            if "rows_path" in c:
                data = dig(data, c["rows_path"], f"chart {c.get('id')}")
            sources.append(c["file"])
            cats, names = [], []
            for r in data:
                for k in (c["cat"], c["series"], c["y"]):
                    if k not in r:
                        raise SpecError(f"chart {c.get('id')}: '{k}' missing in {c['file']}")
                if str(r[c["cat"]]) not in cats:
                    cats.append(str(r[c["cat"]]))
                if str(r[c["series"]]) not in names:
                    names.append(str(r[c["series"]]))
            ser = []
            for nm in names:
                vals, texts = [], []
                for ct in cats:
                    hit = [r for r in data if str(r[c["cat"]]) == ct and str(r[c["series"]]) == nm]
                    if hit:
                        v = float(hit[0][c["y"]]); vals.append(v); texts.append(_fmt(v, c.get("fmt"))[0])
                    else:
                        vals.append(None); texts.append("")
                ser.append({"name": nm, "vals": vals, "texts": texts})
            m.update(cats=cats, series=ser, value_labels=c.get("value_labels", True))
        elif typ in ("line", "scatter"):
            data = self.file(c["file"])
            if "rows_path" in c:
                data = dig(data, c["rows_path"], f"chart {c.get('id')}")
            sources.append(c["file"])
            keys = [c["x"], c["y"]]
            for r in data:
                for k in keys:
                    if k not in r:
                        raise SpecError(f"chart {c.get('id')}: '{k}' missing in {c['file']}")
            if typ == "line":
                groups = {}
                for r in data:
                    groups.setdefault(str(r.get(c.get("series", "_"), "")) if c.get("series") else "", []).append((float(r[c["x"]]), float(r[c["y"]])))
                m["series"] = [{"name": k, "pts": sorted(v), "hl": k == str(c.get("highlight"))} for k, v in groups.items()]
            else:
                m["pts"] = []
                for r in data:
                    q = {"label": str(r.get(c.get("label", ""), "")) if c.get("label") else "", "x": float(r[c["x"]]),
                         "y": float(r[c["y"]]), "hl": str(r.get(c.get("label", ""), "")) == str(c.get("highlight"))}
                    if c.get("group"):
                        q["group"] = str(r.get(c["group"], ""))
                    for k in ("dx", "dy", "anchor"):
                        if k in r:
                            q[k] = r[k] if k == "anchor" else float(r[k])
                    m["pts"].append(q)
                for k in ("xscale", "yscale", "linthresh", "xlim", "ylim", "xticks", "yticks", "group_colors", "group_labels", "corner"):
                    if k in c:
                        m[k] = c[k]
        else:
            raise SpecError(f"chart {c.get('id')}: unknown type {typ}")
        m["sources"] = sorted(set(sources))
        return m

    def chart_by_id(self, cid):
        for c in self.d.get("charts", []) or []:
            if c.get("id") == cid:
                return self.chart_model(c)
        raise SpecError(f"unknown chart id '{cid}'")

    def table_by_id(self, tid):
        for t in self.d.get("tables", []) or []:
            if t.get("id") == tid:
                return self.table_model(t)
        raise SpecError(f"unknown table id '{tid}'")

    def diagram_by_id(self, did):
        from readme.diagram import layout
        for g in self.d.get("diagrams", []) or []:
            if g.get("id") == did:
                return layout(g, self.render)
        raise SpecError(f"unknown diagram id '{did}'")

    def public_strings(self):
        """All human-facing text, for leak + failed-run-story scans."""
        out = []

        def walk(o):
            if isinstance(o, str):
                out.append(o)
            elif isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk({k: v for k, v in self.d.items() if k != "numbers"})
        return out
