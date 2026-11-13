"""Tiny real benchmark: three ways to compute a dot product. Writes results/bench.json and results/scaling.csv."""
import csv, json, os, time
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True)


def t(fn, reps=5):
    best = 1e9
    for _ in range(reps):
        s = time.perf_counter(); fn(); best = min(best, time.perf_counter() - s)
    return best * 1000


def naive(a, b):
    s = 0.0
    for i in range(len(a)):
        s += a[i] * b[i]
    return s


def comp(a, b):
    return sum(x * y for x, y in zip(a, b))


N = 1_000_000
a, b = np.random.default_rng(0).random(N), np.random.default_rng(1).random(N)
al, bl = a.tolist(), b.tolist()
ref = float(np.dot(a, b))
runs = [("python loop", t(lambda: naive(al, bl)), naive(al, bl)), ("generator sum", t(lambda: comp(al, bl)), comp(al, bl)),
        ("numpy dot", t(lambda: np.dot(a, b)), float(np.dot(a, b)))]
rows = [{"name": n, "ms": round(ms, 3), "rel_err": abs(v - ref) / ref} for n, ms, v in runs]
json.dump({"n": N, "runs": rows, "summary": {"speedup": round(rows[0]["ms"] / rows[2]["ms"], 1), "elements": N,
           "max_rel_err": max(r["rel_err"] for r in rows)}}, open(f"{OUT}/bench.json", "w"), indent=1)
with open(f"{OUT}/scaling.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["elements", "series", "ms"])
    for n in (100_000, 250_000, 500_000, 1_000_000):
        x, y = a[:n], b[:n]; xl, yl = x.tolist(), y.tolist()
        w.writerow([n, "python loop", round(t(lambda: naive(xl, yl), 3), 3)])
        w.writerow([n, "numpy dot", round(t(lambda: np.dot(x, y), 3), 4)])
print("wrote results")
