"""Simplified municipality outlines for the Keuhkodata 3D hero.

Input:  ct-sim/data/raw/kunta.json (Statistics Finland municipality boundaries 1:4 500 000, 2026, EPSG:3067, CC BY 4.0;
        fetched by the ct-sim data scripts, git-ignored) and ct-sim/data/area/county_map.csv (municipality -> wellbeing county).
Output: landing-page/assets/finland_3d.json  {"src":..., "scale":..., "m":[[code, hva, [ring, ...]], ...]}
        rings are flat integer lists [x0,y0,x1,y1,...] in km from the south-west corner, Douglas-Peucker simplified.
Run from the repo root: python3 ct-sim/docs/analysis/build_finland_3d.py
"""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOL = 1200.0          # metres
MIN_AREA = 4e6        # drop islands under 4 km2

def dp(pts, tol):
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop(); (x1, y1), (x2, y2) = pts[a], pts[b]; dx, dy = x2 - x1, y2 - y1; L = (dx * dx + dy * dy) ** .5 or 1e-9
        best, bi = 0, None
        for i in range(a + 1, b):
            x, y = pts[i]; d = abs(dy * (x - x1) - dx * (y - y1)) / L
            if d > best: best, bi = d, i
        if bi is not None and best > tol: keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]

def area(r): return abs(sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))) / 2

hva = {r["code"]: r["hva_code"] for r in csv.DictReader(open(ROOT / "ct-sim/data/area/county_map.csv", encoding="utf-8"))}
fc = json.load(open(ROOT / "ct-sim/data/raw/kunta.json", encoding="utf-8"))
polys = []
for f in fc["features"]:
    g = f["geometry"]; parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    polys.append((f["properties"]["kunta"], [p[0] for p in parts]))     # outer rings only
xs = [x for _, rs in polys for r in rs for x, _ in r]; ys = [y for _, rs in polys for r in rs for _, y in r]
x0, y0 = min(xs), min(ys)
out = []
for code, rings in polys:
    keep = []
    for r in rings:
        if area(r) < MIN_AREA: continue
        s = dp(r[:-1] if r[0] == r[-1] else r, TOL)
        if len(s) < 3: continue
        flat = []
        for x, y in s: flat += [round((x - x0) / 1000, 1), round((y - y0) / 1000, 1)]
        keep.append(flat)
    if not keep:  # tiny municipality: keep the largest ring anyway
        r = max(rings, key=area); s = dp(r[:-1], TOL / 4)
        keep = [[v for x, y in s for v in (round((x - x0) / 1000, 1), round((y - y0) / 1000, 1))]]
    out.append([code, hva.get(code, ""), keep])
missing = [c for c, h, _ in out if not h]
assert not missing, missing
dst = ROOT / "landing-page/assets/finland_3d.json"
json.dump({"src": "Statistics Finland, municipality boundaries 1:4 500 000 (2026), CC BY 4.0; simplified", "unit": "km, EPSG:3067 offset",
           "m": out}, open(dst, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
print(len(out), "municipalities", dst.stat().st_size // 1024, "KB")
