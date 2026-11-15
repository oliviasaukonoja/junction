"""Route engine for the pilot map. Used by the build script (baseline routes) and by the password-gated server tools (user-defined routes).

Differences from the plain ctsim tour:
  * A route is an OPEN path: it starts at one stop and ends at another. It is not forced back to its start. The bus runs the same path in
    the opposite direction on the next pass, so there is no empty drive back.
  * Stops are ordered to minimise road travel time (exact for up to 12 stops, multi-start 2-opt/or-opt above that) using OpenStreetMap road
    times, so the bus does not zig-zag between towns on one road.
  * Road legs come from OpenStreetMap routing (cached). `overlap` reports how much of the route re-uses road already driven.

The ctsim engine itself is unchanged: it chooses stops and working days; this module orders them and recomputes distance, days and cost.
Every output carries inputs and assumptions so the page can label them observed / modelled / assumption.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import sys
import time
import urllib.request
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CT = REPO / "ct-sim"
sys.path.insert(0, str(CT / "src"))
from ctsim import routing as R, scenario as S   # noqa: E402

PRIORITY = {
    "HVA21": dict(fi="Lappi", sv="Lappland", en="Lapland", registry="Lapin hyvinvointialue", ct_county="Lappi"),
    "HVA10": dict(fi="Kymenlaakso", sv="Kymmenedalen", en="Kymenlaakso", registry="Kymenlaakson hyvinvointialue", ct_county="Kymenlaakso"),
    "HVA06": dict(fi="Satakunta", sv="Satakunta", en="Satakunta", registry="Satakunnan hyvinvointialue", ct_county="Satakunta"),
}
DEFAULTS = dict(counties=["HVA21"], gamma=1.0, lam=0.5, mu=0.15, spare=0.05, work_days=200, interval=2.0, k_elig=0.8, ct_mode="confirmed+likely",
                start=None, exclude=[], hospital_minutes=45)
LIMITS = dict(gamma=(0.0, 2.0), lam=(0.0, 3.0), mu=(0.0, 1.0), spare=(0.01, 0.30), work_days=(20, 260), interval=(1.0, 3.0), k_elig=(0.3, 1.5), hospital_minutes=(15, 120))
SMR_CAP = (0.8, 1.3)
REGISTRY = {   # wellbeing services county -> name in landing-page/regions.json (SMR); Åland has none (weight 1.0)
    "HVA01": "Itä-Uudenmaan", "HVA02": "Keski-Uudenmaan", "HVA03": "Länsi-Uudenmaan", "HVA04": "Vantaan ja Keravan", "HVA05": "Varsinais-Suomen",
    "HVA06": "Satakunnan", "HVA07": "Kanta-Hämeen", "HVA08": "Pirkanmaan", "HVA09": "Päijät-Hämeen", "HVA10": "Kymenlaakson", "HVA11": "Etelä-Karjalan",
    "HVA12": "Etelä-Savon", "HVA13": "Pohjois-Savon", "HVA14": "Pohjois-Karjalan", "HVA15": "Keski-Suomen", "HVA16": "Etelä-Pohjanmaan",
    "HVA17": "Pohjanmaan", "HVA18": "Keski-Pohjanmaan", "HVA19": "Pohjois-Pohjanmaan", "HVA20": "Kainuun", "HVA21": "Lapin"}
REGISTRY = {k: v + " hyvinvointialue" for k, v in REGISTRY.items()} | {"HVA90": "Helsingin kaupunki"}
AREA_RADIUS = (30.0, 200.0)                       # km, ct-sim's region(): straight line x detour 1.3
AREA_TRAVEL = "estimate: straight line x 1.3 at 60 km/h (ct-sim national model), not OpenStreetMap road times"
T_FAR = 45
LEG_CACHE = CT / "data/routing/osrm_legs_cache.json"


def _rd(p): return list(csv.DictReader(open(p, encoding="utf-8")))
def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


@lru_cache(maxsize=1)
def inputs():
    tm = json.load(open(CT / "data/routing/travel_matrix_priority.json", encoding="utf-8"))
    edu = {r["code"]: _num(r["basic_share"]) for r in _rd(CT / "data/area/municipal_education_55_74.csv")}
    edu_n = {r["code"]: _num(r["persons_55_74"]) or 0 for r in _rd(CT / "data/area/municipal_education_55_74.csv")}
    ok = [(edu[c], edu_n[c]) for c in edu if edu[c] is not None]
    mean = sum(v * n for v, n in ok) / sum(n for _, n in ok)
    sd = math.sqrt(sum(n * (v - mean) ** 2 for v, n in ok) / sum(n for _, n in ok))
    try: legs = json.load(open(LEG_CACHE, encoding="utf-8"))
    except Exception: legs = {}
    ct_rows = _rd(CT / "data/ct_sites/ct_sites.csv")
    status = {}
    for x in ct_rows:
        status.setdefault(x["municipality"], []).append(x["ct_status"])
    return dict(
        tm=tm, durations=tm["durations_s"], distances=tm["distances_m"], points=tm["points"],
        edu=edu, edu_n=edu_n, edu_mean=mean, edu_sd=sd, legs=legs, ct_rows=ct_rows, ct_status=status,
        smr={r["name"]: r for r in json.load(open(REPO / "landing-page/regions.json", encoding="utf-8"))},
        cmap={r["code"]: r["hva_code"] for r in _rd(CT / "data/area/county_map.csv")},
        muni={r["code"]: r for r in _rd(CT / "data/routing/municipalities.csv")},
        rows0={r["code"]: r for r in R.load()})


def town_status(name: str) -> str:
    return "confirmed" if "confirmed" in inputs()["ct_status"].get(name, []) else "likely"


def clean_spec(spec: dict) -> dict:
    """Validate and clamp a user-defined specification. Raises ValueError with a readable message."""
    sp = dict(DEFAULTS)
    sp.update({k: v for k, v in (spec or {}).items() if k in DEFAULTS})
    cs = sp["counties"] if isinstance(sp["counties"], list) else [sp["counties"]]
    cs = [c for c in cs if c in PRIORITY]
    if not cs: raise ValueError("Choose at least one of the three regions")
    sp["counties"] = cs
    for k, (lo, hi) in LIMITS.items():
        try: sp[k] = min(max(float(sp[k]), lo), hi)
        except (TypeError, ValueError): raise ValueError(f"{k} must be a number")
    sp["work_days"] = int(sp["work_days"])
    if sp["ct_mode"] not in ("confirmed", "confirmed+likely"): sp["ct_mode"] = "confirmed+likely"
    names = {p["name"] for p in inputs()["points"]}
    sp["exclude"] = [n for n in (sp["exclude"] or []) if n in names][:60]
    if sp["start"] not in names: sp["start"] = None
    return sp


def make_world(sp: dict):
    I = inputs()
    scn = {"objective": "weighted", "risk_model": "area", "ct_sites": sp["ct_mode"],
           "routing": {"lam": sp["lam"], "spare_share": sp["spare"], "work_days": sp["work_days"], "interval": sp["interval"], "k_elig": sp["k_elig"]}}
    prm, params, cen = S.setup(scn)
    rows = []
    for i, p in enumerate(I["points"]):
        r = dict(I["rows0"][p["code"]]); r["i"] = i; r["lat"], r["lon"] = p["lat"], p["lon"]; rows.append(r)
    fixed = S.fixed_names(scn)
    D = [[(v or 0) / 60.0 for v in row] for row in I["durations"]]            # minutes, used as "km" at the engine's 60 km/h
    w = R.World(rows, prm, fixed, D=D, area=S.area_hook(scn, prm))
    _weights(w, rows, sp)
    fixed_idx = [r["i"] for r in rows if r["name"] in fixed]
    for r in rows:
        j = min(fixed_idx, key=lambda k: w.D[r["i"]][k]); r["ct_town"], r["tt_ct"] = rows[j]["name"], w.D[r["i"]][j]
    return w, rows, prm, cen, scn, fixed, fixed_idx


def _weights(w, rows, sp, nationwide=False):
    """The audited weight replaces the engine's. The three-region world uses SMR only for its own regions (as the published routes do);
    the national world uses every region's SMR."""
    I = inputs()
    for r in rows:
        hva = I["cmap"][r["code"]]
        reg = I["smr"].get(REGISTRY.get(hva, "")) if (nationwide or hva in PRIORITY) else None
        smr = float(reg["smr"]) if reg else 1.0
        need = min(max(smr, SMR_CAP[0]), SMR_CAP[1]) ** sp["gamma"]
        z = ((I["edu"].get(r["code"]) or I["edu_mean"]) - I["edu_mean"]) / I["edu_sd"]
        r["w"] = (1 + sp["lam"] * min(r["f"] / 0.10, 3.0)) * need * (1 + sp["mu"] * min(max(z, 0.0), 2.0))


def national_names() -> list[str]:
    return sorted(r["name"] for r in inputs()["muni"].values())


def name_hint(name) -> str:
    import difflib
    close = difflib.get_close_matches(str(name or ""), national_names(), n=3, cutoff=0.6)
    return f" Did you mean {', '.join(close)}?" if close else ""


def make_world_area(sp: dict):
    """ct-sim's national world: all 308 municipalities, straight-line distances x detour, minutes = km at 60 km/h. Used outside the three regions."""
    scn = {"objective": "weighted", "risk_model": "area", "ct_sites": sp["ct_mode"],
           "routing": {"lam": sp["lam"], "spare_share": sp["spare"], "work_days": sp["work_days"], "interval": sp["interval"], "k_elig": sp["k_elig"]}}
    prm, params, cen = S.setup(scn)
    rows = R.load()
    fixed = S.fixed_names(scn)
    w = R.World(rows, prm, fixed, area=S.area_hook(scn, prm))
    _weights(w, rows, sp, nationwide=True)
    fixed_idx = [r["i"] for r in rows if r["name"] in fixed]
    for r in rows:
        j = min(fixed_idx, key=lambda k: w.D[r["i"]][k]); r["ct_town"], r["tt_ct"] = rows[j]["name"], w.D[r["i"]][j]
    return w, rows, prm, cen, scn, fixed, fixed_idx


def clean_area_spec(spec: dict) -> dict:
    """Spec for a pilot around any municipality: {town, radius_km, start, exclude, ...}. Raises ValueError with a readable message."""
    names = set(national_names())
    town = (spec or {}).get("town")
    if town not in names: raise ValueError(f"'{town}' is not a Finnish municipality name in the data.{name_hint(town)}")
    sp = clean_spec(dict({k: v for k, v in spec.items() if k not in ("start", "exclude")}, counties=["HVA21"]))   # numbers clamped the same way
    try: radius = float(spec.get("radius_km") or 100)
    except (TypeError, ValueError): raise ValueError("radius_km must be a number")
    sp.update(counties=[], town=town, radius_km=min(max(radius, AREA_RADIUS[0]), AREA_RADIUS[1]), own_region_only=spec.get("own_region_only", True) is not False)
    sp["exclude"] = [n for n in (spec.get("exclude") or []) if n in names][:60]
    sp["start"] = spec.get("start") if spec.get("start") in names else None
    return sp


# ---------------------------------------------------------------------------------------------------------------------
# ordering: shortest open path through the stops
# ---------------------------------------------------------------------------------------------------------------------
def _path_len(order, D): return sum(D[order[i]][order[i + 1]] for i in range(len(order) - 1))


def _two_opt_open(order, D, fixed_start):
    n = len(order); best = _path_len(order, D); improved = True
    while improved:
        improved = False
        for i in range(1 if fixed_start else 0, n - 1):
            for j in range(i + 1, n):
                new = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                L = _path_len(new, D)
                if L + 1e-9 < best: order, best, improved = new, L, True
        for i in range(1 if fixed_start else 0, n):                              # or-opt: relocate one stop
            for j in range(0, n):
                if i == j or (fixed_start and j == 0): continue
                new = order[:i] + order[i + 1:]; new.insert(j, order[i])
                L = _path_len(new, D)
                if L + 1e-9 < best: order, best, improved = new, L, True
    return order, best


def _through_cost(D, idx):
    """Static leg cost = road time + a charge for every other stop the leg drives (almost) straight past. Such a stop is visited on some other leg,
    so the corridor is driven twice (for example Tornio to Simo passes Kemi, and Kemi is visited later): the charge is the extra distance re-driven."""
    C = {}
    for a in idx:
        for b in idx:
            if a == b: continue
            pen = 0.0
            for k in idx:
                if k in (a, b): continue
                if D[a][k] + D[k][b] <= D[a][b] + max(6.0, 0.12 * D[a][b]):
                    pen += 2 * min(D[a][k], D[k][b])
            C[(a, b)] = D[a][b] + pen
    return C


def order_path(D, idx, start=None):
    """Shortest open path over node indices `idx` (minutes matrix D), charging for through-town re-driving. Returns (order, charged cost)."""
    idx = list(idx)
    if len(idx) <= 1: return idx, 0.0
    C = _through_cost(D, idx)
    n0 = len(D)
    Ds = [[0.0] * n0 for _ in range(n0)]
    for a in idx:
        for b in idx:
            if a != b: Ds[a][b] = (C[(a, b)] + C[(b, a)]) / 2
    if len(idx) <= 11:                                                           # exact Held-Karp
        n = len(idx)
        dp = {}
        for s in range(n):
            if start is None or idx[s] == start: dp[(1 << s, s)] = (0.0, None)
        for mask in range(1, 1 << n):
            for last in range(n):
                if (mask, last) not in dp: continue
                cur = dp[(mask, last)][0]
                for nx in range(n):
                    if mask & (1 << nx): continue
                    key = (mask | (1 << nx), nx); v = cur + Ds[idx[last]][idx[nx]]
                    if key not in dp or v < dp[key][0]: dp[key] = (v, (mask, last))
        full = (1 << n) - 1
        last = min((l for l in range(n) if (full, l) in dp), key=lambda l: dp[(full, l)][0])
        total = dp[(full, last)][0]; seq = []; key = (full, last)
        while key: seq.append(idx[key[1]]); key = dp[key][1]
        return seq[::-1], total
    best = None
    for s in ([start] if start is not None else idx):
        order, left = [s], set(idx) - {s}
        while left:
            nx = min(left, key=lambda j: Ds[order[-1]][j]); order.append(nx); left.remove(nx)
        order, L = _two_opt_open(order, Ds, start is not None)
        if best is None or L < best[0]: best = (L, order)
    return best[1], best[0]


# ---------------------------------------------------------------------------------------------------------------------
# road legs (OpenStreetMap routing, cached) and the overlap check
# ---------------------------------------------------------------------------------------------------------------------
def _rdp(pts, eps):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-12
    dm, im = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / L
        if d > dm: dm, im = d, i
    return _rdp(pts[:im + 1], eps)[:-1] + _rdp(pts[im:], eps) if dm > eps else [pts[0], pts[-1]]


def get_leg(a: dict, b: dict, fetch=True, budget=None, fallback=None) -> dict:
    """Road geometry between two points. Uses the cache; fetches from the OSRM demo server when allowed; falls back to a straight line (schematic)."""
    I = inputs(); key = f"{a['lon']:.5f},{a['lat']:.5f};{b['lon']:.5f},{b['lat']:.5f}"
    leg = I["legs"].get(key)
    if leg is None and fetch and (budget is None or budget[0] > 0):
        if budget is not None: budget[0] -= 1
        try:
            r = json.load(urllib.request.urlopen(f"https://router.project-osrm.org/route/v1/driving/{key}?overview=full&geometries=geojson", timeout=12))
            rt = r["routes"][0]
            leg = dict(minutes=round(rt["duration"] / 60, 1), km=round(rt["distance"] / 1000, 1),
                       coords=[[round(y, 4), round(x, 4)] for x, y in _rdp([tuple(c) for c in rt["geometry"]["coordinates"]], 0.004)])
            I["legs"][key] = leg
            time.sleep(0.2)
        except Exception:
            leg = None
    if leg is None and fallback is not None:
        leg = dict(minutes=round(fallback, 1), km=round(fallback, 1), coords=[[a["lat"], a["lon"]], [b["lat"], b["lon"]]], schematic=True)
    if leg is None:
        ia, ib = a["i"], b["i"]
        leg = dict(minutes=round(I["durations"][ia][ib] / 60, 1), km=round(I["distances"][ia][ib] / 1000, 1), coords=[[a["lat"], a["lon"]], [b["lat"], b["lon"]]], schematic=True)
    return leg


def _seg_dist_km(p, a, b, lat0):
    k = math.cos(math.radians(lat0)) * 111.32
    px, py, ax, ay, bx, by = p[1] * k, p[0] * 110.57, a[1] * k, a[0] * 110.57, b[1] * k, b[0] * 110.57
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def overlap_km(legs: list[list[list[float]]], tol_km=0.6, skip_km=4.0) -> float:
    """Kilometres of road driven again: points sampled along each leg that lie within tol_km of an earlier leg, ignoring skip_km around the stops."""
    if len(legs) < 2: return 0.0
    def length(c): return sum(_hav(c[i - 1], c[i]) for i in range(1, len(c)))
    total = 0.0
    for k in range(1, len(legs)):
        c = legs[k]; L = length(c)
        if L < 1: continue
        samples, cum = [], 0.0
        for i in range(1, len(c)):
            seg = _hav(c[i - 1], c[i]); n = max(1, int(seg / 0.5))
            for s in range(n):
                f = (s + .5) / n; samples.append(((c[i - 1][0] + (c[i][0] - c[i - 1][0]) * f, c[i - 1][1] + (c[i][1] - c[i - 1][1]) * f), cum + seg * f))
            cum += seg
        hit = 0
        for pt, along in samples:
            if along < skip_km or L - along < skip_km: continue
            near = False
            for j in range(k):
                cc = legs[j]
                for q in range(1, len(cc)):
                    if _seg_dist_km(pt, cc[q - 1], cc[q], pt[0]) <= tol_km: near = True; break
                if near: break
            hit += near
        total += hit * 0.5
    return round(total, 1)


def _hav(a, b):
    p = math.pi / 180
    x = math.sin((b[0] - a[0]) * p / 2) ** 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


# ---------------------------------------------------------------------------------------------------------------------
# planning
# ---------------------------------------------------------------------------------------------------------------------
def plan(spec: dict, geometry=True, fetch=True, max_fetch=None) -> dict:
    """max_fetch limits new road lookups (server use); legs beyond it are drawn as straight lines and flagged schematic."""
    sp = clean_spec(spec)
    I = inputs()
    world = make_world(sp)
    rows = world[1]
    reg = {r["name"] for r in rows if I["cmap"][r["code"]] in sp["counties"] and r["name"] not in set(sp["exclude"])}
    return _plan_core(sp, world, reg, geometry, fetch, max_fetch, area=False)


def plan_area(spec: dict, geometry=True, fetch=True, max_fetch=None) -> dict:
    """A bus pilot around any municipality (e.g. Oulu): ct-sim's national model, municipalities within radius_km of the town."""
    sp = clean_area_spec(spec)
    world = make_world_area(sp)
    I = inputs()
    reg = R.region(world[0], sp["town"], sp["radius_km"]) - set(sp["exclude"])
    if sp["own_region_only"]:                                                    # a pilot is run by one wellbeing services county
        home = I["cmap"][next(r["code"] for r in world[1] if r["name"] == sp["town"])]
        reg = {n for n in reg if I["cmap"][next(r["code"] for r in world[1] if r["name"] == n)] == home}
    if len(reg) < 2: raise ValueError("Too few municipalities in that area; use a larger radius_km")
    out = _plan_core(sp, world, reg, geometry, fetch, max_fetch, area=True)
    out["area"] = dict(town=sp["town"], radius_km=sp["radius_km"], own_region_only=sp["own_region_only"], municipalities=len(reg), counties=out["spec"]["counties"], travel=AREA_TRAVEL,
                       names=sorted(reg))
    return out


def _plan_core(sp, world, reg, geometry, fetch, max_fetch, area):
    budget = [max_fetch] if max_fetch is not None else None
    I = inputs()
    w, rows, prm, cen, scn, fixed, fixed_idx = world
    by_name = {r["name"]: r for r in rows}
    if area: sp = dict(sp, counties=sorted({I["cmap"][by_name[n]["code"]] for n in reg}))
    ev = w.evaluate(w.optimise(reg, "weighted"))
    summ, reach, _ = S._area_summary(w, ev, rows, cen, prm, fixed, reg)
    elig_all = sum(r["elig"] for r in rows if r["name"] in reg) or 1
    detail = {s["name"]: s for s in ev["stop_detail"]}
    idx = [by_name[n]["i"] for n in detail]
    start = by_name[sp["start"]]["i"] if sp["start"] in detail else None
    order, _ = order_path(w.D, idx, start)
    if start is None and len(order) > 1 and w.D[order[0]][order[-1]] > w.D[order[-1]][order[0]] * 1.0001: order = order[::-1]
    names = [rows[i]["name"] for i in order]
    # legs, minutes, kilometres along the open path (one pass)
    legs = []
    for a, b in zip(order, order[1:]):
        fb = w.D[a][b] if area else None                                         # national world: straight-line estimate when no road leg
        L = get_leg(rows[a], rows[b], fetch=fetch, budget=budget, fallback=fb) if geometry else dict(minutes=round(fb, 1), km=round(fb, 1),
            coords=[[rows[a]["lat"], rows[a]["lon"]], [rows[b]["lat"], rows[b]["lon"]]], schematic=True) if area else dict(minutes=round(I["durations"][a][b] / 60, 1), km=round(I["distances"][a][b] / 1000, 1),
                                                                        coords=[[rows[a]["lat"], rows[a]["lon"]], [rows[b]["lat"], rows[b]["lon"]]], schematic=True)
        legs.append(dict(frm=rows[a]["name"], to=rows[b]["name"], minutes=L["minutes"], km=L["km"], coords=L["coords"], schematic=bool(L.get("schematic"))))
    path_min = sum(l["minutes"] for l in legs); path_km = sum(l["km"] for l in legs)
    passes = prm["cycles"]
    scan_days = sum(d["days"] for d in detail.values())
    drive_days = path_min * passes / (prm["driving_h"] * 60)
    setup_days = len(order) * passes * prm["setup_days"]
    ev2 = dict(ev, km=path_km * passes)
    cost = w.cost(ev2, cen)
    cinfo = {c["hva_code"]: c for c in summ}
    stops = []
    for k, n in enumerate(names, 1):
        s, row = detail[n], by_name[n]
        cat = [by_name[c] for c in s["catchment"]]
        wsum = sum(r["pop"] for r in cat) or 1
        tt = row["tt_ct"]
        kind = "ct_town" if tt < 15 else ("far" if tt >= T_FAR else "mid")
        flags = []
        if kind == "ct_town": flags.append("capacity_assumption")
        if town_status(row["ct_town"]) != "confirmed": flags.append("ct_unconfirmed")
        stops.append(dict(
            n=k, name=n, lat=row["lat"], lon=row["lon"], county=I["cmap"][row["code"]], days=round(s["days"], 1), scans=round(s["scans"]), additional=round(s["additional"]),
            catchment=s["catchment"], catchment_eligible=round(sum(r["elig"] for r in cat)), catchment_share=round(sum(r["elig"] for r in cat) / elig_all, 3),
            nearest_ct=row["ct_town"], tt_ct_min=round(tt), ct_status=town_status(row["ct_town"]), kind=kind,
            foreign_share=round(sum(r["f"] * r["pop"] for r in cat) / wsum, 3),
            basic_share=round(sum((I["edu"].get(r["code"]) or I["edu_mean"]) * r["pop"] for r in cat) / wsum, 3), flags=flags))
    eligible = round(reach["eligible_persons"]) if area else round(sum(c["eligible"] for c in summ if c["hva_code"] in sp["counties"]))
    out = dict(
        spec=sp, stops=stops, legs=legs, start=names[0] if names else None, end=names[-1] if names else None,
        totals=dict(stops=len(names), path_minutes=round(path_min), path_km=round(path_km), km_year=round(path_km * passes), passes=passes,
                    scan_days=round(scan_days, 1), drive_days=round(drive_days, 1), setup_days=round(setup_days, 1),
                    working_days=round(scan_days + drive_days + setup_days, 1), scans=round(ev["scans"]), additional=round(ev["additional"]),
                    additional_far=round(ev["add_far"]), eligible=eligible, eligible_far_catchments=sum(s["catchment_eligible"] for s in stops if s["kind"] == "far"),
                    days_in_ct_towns=round(sum(s["days"] for s in stops if s["kind"] == "ct_town"), 1),
                    cost_per_additional_eur=round(cost["per_additional"]), cost_total_eur=round(cost["total"]),
                    coverage_hospital_only=round(reach["coverage_fixed_only"], 3), coverage_with_bus=round(reach["coverage_with_truck"], 3)),
        counties={c: dict(eligible=round(cinfo[c]["eligible"]), annual_need=round(cinfo[c]["annual_need"]), spare_scans=round(cinfo[c]["spare"]),
                          coverage_fixed=cinfo[c]["coverage_fixed"], ct_towns=cinfo[c]["ct_towns"]) for c in sp["counties"] if c in cinfo})
    if geometry:
        out["overlap_km"] = overlap_km([l["coords"] for l in legs])
        out["schematic_legs"] = sum(1 for l in legs if l["schematic"])
    return out


# ---------------------------------------------------------------------------------------------------------------------
# hospital / clinic CT scenario: DEMAND side only (capacity data does not exist)
# ---------------------------------------------------------------------------------------------------------------------
def hospital_scenario(spec: dict) -> dict:
    """Size the invitation population around one CT town. Uses observed population and modelled eligibility and uptake.
    Reserved capacity is a user input (`slots_per_week`), never data. Returns demand per year and, if slots are given, the time to cover it."""
    I = inputs()
    town = spec.get("town")
    names = {p["name"] for p in I["points"]}
    inside = town in names and any(I["cmap"][p["code"]] in PRIORITY for p in I["points"] if p["name"] == town)
    if not inside: return _hospital_area(spec)
    sp = clean_spec(dict(spec, counties=spec.get("counties") or list(PRIORITY)))
    minutes = float(sp["hospital_minutes"]); slots = spec.get("slots_per_week")
    w, rows, prm, cen, scn, fixed, fixed_idx = make_world(sp)
    by = {r["name"]: r for r in rows}
    if town not in {rows[j]["name"] for j in fixed_idx}: raise ValueError("That town is not on the researched CT list")
    t = by[town]
    inc = []
    for r in rows:
        if I["cmap"][r["code"]] not in PRIORITY: continue
        d = I["durations"][t["i"]][r["i"]] / 60.0
        if d <= minutes and r["name"] not in set(sp["exclude"]) and r["ct_town"] == town:      # people whose nearest CT town is this one
            u = prm["u0"] * math.exp(-d / prm["d0_fixed"]) * (1 - r["f"] * (1 - prm["minority_factor_fixed"]))
            inc.append(dict(name=r["name"], minutes=round(d), eligible=round(r["elig"]), uptake=round(u, 3), scans_year=round(r["elig"] * u / prm["interval"], 1),
                            foreign_share=round(r["f"], 3), basic_share=I["edu"].get(r["code"]), lat=r["lat"], lon=r["lon"]))
    return _hospital_out(town, minutes, inc, prm, slots, travel="OpenStreetMap road times")


def _hospital_area(spec: dict) -> dict:
    """Hospital pilot around a CT town outside the three regions: ct-sim's national model, straight-line travel estimate."""
    I = inputs()
    town = spec.get("town")
    sp = clean_area_spec(dict(spec, town=town))
    w, rows, prm, cen, scn, fixed, fixed_idx = make_world_area(sp)
    if town not in fixed: raise ValueError(f"{town} is not on the researched CT list ({sp['ct_mode']}).")
    minutes = float(sp["hospital_minutes"]); slots = spec.get("slots_per_week")
    t = next(r for r in rows if r["name"] == town)
    inc = []
    for r in rows:
        d = w.D[t["i"]][r["i"]]                                                  # km at 60 km/h = minutes (estimate)
        if d <= minutes and r["name"] not in set(sp["exclude"]) and r["ct_town"] == town:
            u = prm["u0"] * math.exp(-d / prm["d0_fixed"]) * (1 - r["f"] * (1 - prm["minority_factor_fixed"]))
            inc.append(dict(name=r["name"], minutes=round(d), eligible=round(r["elig"]), uptake=round(u, 3), scans_year=round(r["elig"] * u / prm["interval"], 1),
                            foreign_share=round(r["f"], 3), basic_share=I["edu"].get(r["code"]), lat=r["lat"], lon=r["lon"], county=I["cmap"][r["code"]]))
    return _hospital_out(town, minutes, inc, prm, slots, travel=AREA_TRAVEL)


def _hospital_out(town, minutes, inc, prm, slots, travel):
    elig = sum(m["eligible"] for m in inc); scans = sum(m["scans_year"] for m in inc)
    out = dict(town=town, ct_status=town_status(town), minutes=minutes, travel=travel, municipalities=sorted(inc, key=lambda m: m["minutes"]),
               eligible=elig, invitations_per_year=round(elig / prm["interval"]), expected_scans_year=round(scans), expected_scans_week=round(scans / 52, 1),
               interval=prm["interval"], uptake_u0=prm["u0"], d0_fixed=prm["d0_fixed"],
               capacity=dict(verified=False, needed_data=["scanners and operating hours at this site", "annual CT volume and slots free for screening",
                                                          "radiologist reading capacity for low-dose CT", "referral and follow-up pathway (nodule clinic, biopsy)",
                                                          "site owner and contract (hospital or private clinic)", "cost per scan at this site"]))
    if slots:
        try: slots = float(slots)
        except (TypeError, ValueError): slots = None
    if slots and slots > 0:
        out["user_slots_per_week"] = slots
        out["weeks_to_cover_one_round"] = round(scans * prm["interval"] / slots) if scans else None
        out["share_of_demand_covered"] = round(min(1.0, slots * 52 / scans), 3) if scans else None
    return out
