#!/usr/bin/env python3
"""Fetch the observed inputs added for the pilot map and store them in the repository (so the builder runs offline).

Writes:
  data/area/municipal_education_55_74.csv   Statistics Finland 12bq (31.12.2025): share of people aged 55-74 whose highest level is basic education, by municipality
  data/area/municipal_income_2024.csv       Statistics Finland 14ww (2024): at-risk-of-poverty rate and median disposable cash income, by municipality (all ages)
  data/routing/settlement_points.csv        main settlement of each municipality (OpenStreetMap Nominatim), used instead of the geometric centroid,
                                            which for large rural municipalities lies far from where people live
  data/routing/travel_matrix_priority.json  OpenStreetMap road travel times and distances (OSRM public demo server, free-flow, no winter/ferry delays)
                                            between the 43 municipalities of Lapland, Kymenlaakso and Satakunta and the researched CT towns

Run:  python3 ct-sim/docs/analysis/fetch_pilot_inputs.py [--refresh]
Limits are written into each file's header or into the JSON `limits` field.
"""
import csv, itertools, json, sys, time, urllib.request
from datetime import date
from pathlib import Path

CT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CT / "src"))
from ctsim import routing as R, scenario as S   # noqa: E402

REFRESH = "--refresh" in sys.argv
PRIORITY = ("HVA21", "HVA10", "HVA06")
mun = list(csv.DictReader(open(CT / "data/routing/municipalities.csv", encoding="utf-8")))
cmap = {r["code"]: r["hva_code"] for r in csv.DictReader(open(CT / "data/area/county_map.csv", encoding="utf-8"))}


def post(url, q):
    req = urllib.request.Request(url, data=json.dumps(q).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def jsd(r):
    ids, size = r["id"], r["size"]
    cats = [list(r["dimension"][i]["category"]["index"]) for i in ids]
    return ids, {tuple(cats[j][c[j]] for j in range(len(ids))): r["value"][k] for k, c in enumerate(itertools.product(*[range(s) for s in size]))}


# ---- education 55-74 ------------------------------------------------------------------------------------------------------
edu_f = CT / "data/area/municipal_education_55_74.csv"
if REFRESH or not edu_f.exists():
    codes = ["KU" + m["code"] for m in mun]
    ages = ["55-59", "60-64", "65-69", "70-74"]
    ids, v = jsd(post("https://statfin.stat.fi/PXWeb/api/v1/en/StatFin/vkour/12bq.px", {"query": [
        {"code": "alue_23_20260101", "selection": {"filter": "item", "values": codes}},
        {"code": "ikaryhma_10_20180101", "selection": {"filter": "item", "values": ages}},
        {"code": "sukupuoli_9_20180101", "selection": {"filter": "item", "values": ["SSS"]}},
        {"code": "koulutusaste_17_20180101", "selection": {"filter": "item", "values": ["SSS", "9"]}},
        {"code": "timeperiod_y", "selection": {"filter": "item", "values": ["2025"]}},
        {"code": "contentscode", "selection": {"filter": "top", "values": ["1"]}}], "response": {"format": "json-stat2"}}))
    ix = {}
    for key, val in v.items():
        kv = dict(zip(ids, key)); ix[(kv["alue_23_20260101"], kv["ikaryhma_10_20180101"], kv["koulutusaste_17_20180101"])] = val
    with open(edu_f, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["code", "name", "persons_55_74", "basic_education_only_55_74", "basic_share", "source", "year"])
        for m in mun:
            k = "KU" + m["code"]
            tot = sum((ix.get((k, a, "SSS")) or 0) for a in ages); bas = sum((ix.get((k, a, "9")) or 0) for a in ages)
            w.writerow([m["code"], m["name"], tot, bas, round(bas / tot, 4) if tot else "", "Statistics Finland StatFin vkour/12bq (level 9 = basic education)", 2025])
    print("wrote", edu_f.relative_to(CT.parent))

# ---- income / poverty -----------------------------------------------------------------------------------------------------
inc_f = CT / "data/area/municipal_income_2024.csv"
if REFRESH or not inc_f.exists():
    codes = ["KU" + m["code"] for m in mun]
    ids, v = jsd(post("https://statfin.stat.fi/PXWeb/api/v1/en/StatFin/tjt/14ww.px", {"query": [
        {"code": "alue_23_20250101", "selection": {"filter": "item", "values": codes}},
        {"code": "contentscode", "selection": {"filter": "item", "values": ["rpt_aste", "hkturaha18_med"]}},
        {"code": "timeperiod_y", "selection": {"filter": "item", "values": ["2024"]}}], "response": {"format": "json-stat2"}}))
    ix = {}
    for key, val in v.items():
        kv = dict(zip(ids, key)); ix[(kv["alue_23_20250101"], kv["contentscode"])] = val
    with open(inc_f, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["code", "name", "at_risk_of_poverty_rate_pct", "median_disposable_cash_income_adults_eur", "source", "year"])
        for m in mun:
            k = "KU" + m["code"]
            w.writerow([m["code"], m["name"], ix.get((k, "rpt_aste"), ""), ix.get((k, "hkturaha18_med"), ""), "Statistics Finland StatFin tjt/14ww, all ages", 2024])
    print("wrote", inc_f.relative_to(CT.parent))

# ---- settlement points ----------------------------------------------------------------------------------------------------
sp_f = CT / "data/routing/settlement_points.csv"
def hav(a, b, c, d):
    import math
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))
if REFRESH or not sp_f.exists():
    import urllib.parse
    scn = {"ct_sites": "confirmed+likely"}
    rows0 = R.load()
    by0 = {r["name"]: r for r in rows0}
    need = [r for r in rows0 if cmap[r["code"]] in PRIORITY] + [by0[n] for n in S.fixed_names(scn) if n in by0 and cmap[by0[n]["code"]] not in PRIORITY]
    out = []
    for r in need:
        q = urllib.parse.urlencode({"q": r["name"] + ", Finland", "format": "jsonv2", "limit": 10, "countrycodes": "fi", "addressdetails": 0})
        req = urllib.request.Request("https://nominatim.openstreetmap.org/search?" + q, headers={"User-Agent": "polku-hoitoon-pilot-map/1.0 (open data research prototype)"})
        try:
            res = json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            res = []
        time.sleep(1.2)                                                     # Nominatim usage policy: at most one request per second
        def ok(x):
            return (x.get("category") == "boundary" and x.get("type") == "administrative" and x.get("addresstype") in ("city", "town", "municipality", "village")) \
                or (x.get("category") == "place" and x.get("type") in ("city", "town", "village", "suburb", "hamlet"))
        cand = [x for x in res if ok(x) and hav(r["lat"], r["lon"], float(x["lat"]), float(x["lon"])) <= 60]
        if cand:
            # administrative entries first (their coordinates are the municipality's admin centre), then settlement nodes; ties by Nominatim importance
            x = min(cand, key=lambda c: (0 if c.get("category") == "boundary" else 1, -float(c.get("importance", 0))))
            lat, lon, used = round(float(x["lat"]), 5), round(float(x["lon"]), 5), "nominatim:" + x["category"] + "/" + x["type"]
        else:
            lat, lon, used = r["lat"], r["lon"], "centroid (no settlement found within 60 km)"
        out.append([r["code"], r["name"], lat, lon, round(hav(r["lat"], r["lon"], lat, lon), 1), used])
        print(r["name"], used, out[-1][4], "km from centroid")
    with open(sp_f, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["code", "name", "lat", "lon", "km_from_centroid", "point_source"])
        w.writerows(out)
    print("wrote", sp_f.relative_to(CT.parent))
SETTLE = {r["code"]: (float(r["lat"]), float(r["lon"])) for r in csv.DictReader(open(sp_f, encoding="utf-8"))}

# ---- travel matrix --------------------------------------------------------------------------------------------------------
tm_f = CT / "data/routing/travel_matrix_priority.json"
if REFRESH or not tm_f.exists():
    scn = {"ct_sites": "confirmed+likely"}
    ct_names = S.fixed_names(scn)
    rows = R.load()
    by = {r["name"]: r for r in rows}
    code_county = {r["code"]: cmap[r["code"]] for r in rows}
    pts = [r for r in rows if code_county[r["code"]] in PRIORITY]
    seen = {r["name"] for r in pts}
    pts += [by[n] for n in ct_names if n in by and n not in seen]
    print(len(pts), "points")
    assert len(pts) <= 100, "OSRM demo table limit"
    for r in pts:
        if r["code"] in SETTLE: r["lat"], r["lon"] = SETTLE[r["code"]]
    coords = ";".join(f"{r['lon']:.5f},{r['lat']:.5f}" for r in pts)
    r = json.load(urllib.request.urlopen(f"https://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration,distance", timeout=180))
    assert r["code"] == "Ok", r.get("code")
    snap = [round(d.get("distance", 0)) for d in r["destinations"]]
    out = dict(
        source="OpenStreetMap road network via the OSRM public demo server (router.project-osrm.org), driving profile", fetched=date.today().isoformat(),
        points=[dict(code=p["code"], name=p["name"], lat=p["lat"], lon=p["lon"], county=code_county[p["code"]], snap_m=s) for p, s in zip(pts, snap)],
        durations_s=r["durations"], distances_m=r["distances"],
        limits=["Free-flow speeds from OSM tags: no winter conditions, traffic, ferries or opening hours", "Points are the main settlement of each municipality (OSM Nominatim) snapped to the nearest road, not exact home locations (snap_m shows the snap distance); where no settlement was found the municipality centroid is used",
                "OSRM demo server is for light use; terms should be checked before production use", "Not Digiroad: the national road database was not downloaded"])
    tm_f.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("wrote", tm_f.relative_to(CT.parent), tm_f.stat().st_size, "bytes; max snap", max(snap), "m")
