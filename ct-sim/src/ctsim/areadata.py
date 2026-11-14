"""Area data from public APIs, all verified sources (the few derived columns are labelled as proxies):

  data/area/county_map.csv         municipality code -> wellbeing services county (THL Sotkanet region hierarchy, 308/308 matched)
  data/area/county_indicators.csv  per county: lung-cancer deaths (Statistics Finland 13u5, ICD-10 C32-C34, 2021-2025), daily-smoking
                                   prevalence (THL Sotkanet 4405 age 20-64 and 4406 age 65+), population from our municipality table
  data/area/national_ct_exams.csv  hospital CT examinations per 100,000 inhabitants (Eurostat hlth_co_exam), national only

Not available publicly as far as I found: pack-year distributions, CT scanners or CT volumes by county, CT waiting times by county,
screening capacity. Those are assumptions or gaps, listed in data/area/DATA_STATUS.json by `python -m ctsim area`.
"""
from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

from . import paths

AREA = paths.DATA / "area"
UA = {"User-Agent": "ctsim-research/0.1 (public aggregate data)"}

# Statistics Finland code, THL Sotkanet region id, short English name
COUNTIES = [
    ("HVA01", 961, "East Uusimaa"), ("HVA02", 966, "Central Uusimaa"), ("HVA03", 969, "West Uusimaa"), ("HVA04", 977, "Vantaa and Kerava"),
    ("HVA05", 978, "Southwest Finland"), ("HVA06", 976, "Satakunta"), ("HVA07", 963, "Kanta-Häme"), ("HVA08", 970, "Pirkanmaa"),
    ("HVA09", 975, "Päijät-Häme"), ("HVA10", 967, "Kymenlaakso"), ("HVA11", 957, "South Karelia"), ("HVA12", 959, "South Savo"),
    ("HVA13", 974, "North Savo"), ("HVA14", 972, "North Karelia"), ("HVA15", 965, "Central Finland"), ("HVA16", 958, "South Ostrobothnia"),
    ("HVA17", 971, "Ostrobothnia"), ("HVA18", 964, "Central Ostrobothnia"), ("HVA19", 973, "North Ostrobothnia"), ("HVA20", 962, "Kainuu"),
    ("HVA21", 968, "Lapland"), ("HVA90", 960, "Helsinki"), ("HVA91", 956, "Åland"),
]


def _get(url: str, data: bytes | None = None):
    req = urllib.request.Request(url, data=data, headers={**UA, **({"Content-Type": "application/json"} if data else {})})
    return json.load(urllib.request.urlopen(req, timeout=90))


def county_map() -> list[dict]:
    regions = _get("https://sotkanet.fi/rest/1.1/regions")
    by_id = {c[1]: c for c in COUNTIES}
    out = []
    for r in regions:
        if r["category"] != "KUNTA":
            continue
        parent = [m for m in r["memberOf"] if m in by_id]
        if len(parent) != 1:
            raise ValueError(f"municipality {r['code']} has {len(parent)} county parents")
        c = by_id[parent[0]]
        out.append(dict(code=r["code"], municipality=r["title"]["fi"], hva_code=c[0], county=c[2]))
    return sorted(out, key=lambda x: x["code"])


def lung_deaths() -> dict[str, dict]:
    """{hva_code: {year: (deaths, crude_rate_per_100k)}} for cause '11' (C32-C34), 2021-2025."""
    base = "https://statfin.stat.fi/PxWeb/api/v1/en/StatFin/ksyyt/13u5.px"
    meta = _get(base)
    var = {v["code"].split("_")[0]: v for v in meta["variables"]}
    areas = [c[0] for c in COUNTIES] + ["SSS"]
    q = {"query": [
        {"code": next(v["code"] for v in meta["variables"] if v["code"].startswith("alue")), "selection": {"filter": "item", "values": areas}},
        {"code": next(v["code"] for v in meta["variables"] if v["code"].startswith("kuolinsyyt")), "selection": {"filter": "item", "values": ["11"]}},
        {"code": "timeperiod_y", "selection": {"filter": "item", "values": ["2021", "2022", "2023", "2024", "2025"]}},
        {"code": "contentscode", "selection": {"filter": "all", "values": ["*"]}}], "response": {"format": "json-stat2"}}
    d = _get(base, json.dumps(q).encode())
    ids, size = d["id"], d["size"]
    cats = {k: list(d["dimension"][k]["category"]["index"]) for k in ids}
    import itertools
    out: dict = {}
    for i, key in enumerate(itertools.product(*[cats[k] for k in ids])):
        row = dict(zip(ids, key))
        area = next(v for k, v in row.items() if k.startswith("alue"))
        year = row["timeperiod_y"]
        info = row["contentscode"]
        val = d["value"][i]
        slot = out.setdefault(area, {}).setdefault(year, [None, None])
        slot[0 if info == "ksyylkm" else 1] = val   # ksyylkm = deaths, ksyycdr = crude rate per 100,000
    return out


def smoking() -> dict[int, dict]:
    """{sotkanet_region_id: {indicator: (year, value)}}: latest year per county for 4405 (20-64) and 4406 (65+)."""
    ids = {c[1] for c in COUNTIES}
    out: dict = {}
    for ind in (4405, 4406):
        rows = _get(f"https://sotkanet.fi/rest/1.1/json?indicator={ind}&years=2018&years=2020&years=2022&years=2024&genders=total")
        for r in rows:
            if r["region"] in ids and r["value"] is not None:
                cur = out.setdefault(r["region"], {}).get(ind)
                if cur is None or r["year"] > cur[0]:
                    out[r["region"]][ind] = (r["year"], r["value"])
    return out


def eurostat_ct_exams() -> list[dict]:
    d = _get("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/hlth_co_exam?format=JSON&lang=EN&geo=FI&unit=P_HTHAB")
    dims, size = d["id"], d["size"]
    lab = {k: list(d["dimension"][k]["category"]["index"]) for k in dims}
    out = []
    import itertools
    for i, key in enumerate(itertools.product(*[lab[k] for k in dims])):
        v = d["value"].get(str(i))
        if v is None:
            continue
        row = dict(zip(dims, key))
        if row["facility"] == "CT_SCAN":
            out.append(dict(year=int(row["time"]), providers=row["icha_hp"], per_100k=round(v, 1)))
    return sorted(out, key=lambda r: (r["providers"], r["year"]))


def build() -> dict:
    AREA.mkdir(parents=True, exist_ok=True)
    cmap = county_map()
    with open(AREA / "county_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["code", "municipality", "hva_code", "county"])
        w.writeheader(); w.writerows(cmap)
    # populations from our municipality table
    pop_all, pop50 = {}, {}
    code2h = {m["code"]: m["hva_code"] for m in cmap}
    with open(paths.MUNICIPALITIES_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            h = code2h[r["code"]]
            pop_all[h] = pop_all.get(h, 0) + int(r["pop_all"] or 0)
            pop50[h] = pop50.get(h, 0) + int(r["pop_50_74"])
    ld = lung_deaths()
    sm = smoking()
    rows = []
    for hva, sid, name in COUNTIES:
        yrs = ld.get(hva, {})
        deaths = [v[0] for v in yrs.values() if v[0] is not None]
        rates = [v[1] for v in yrs.values() if v[1] is not None]
        mean_deaths = sum(deaths) / len(deaths) if deaths else None
        s = sm.get(sid, {})
        s2064, s65 = s.get(4405), s.get(4406)
        rows.append(dict(
            hva_code=hva, county=name, pop_all=pop_all.get(hva, 0), pop_50_74=pop50.get(hva, 0),
            lung_deaths_mean_2021_2025=round(mean_deaths, 1) if mean_deaths is not None else "",
            lung_deaths_per_100k_crude=round(sum(rates) / len(rates), 1) if rates else "",
            lung_deaths_per_100k_aged_50_74_proxy=round(mean_deaths / pop50[hva] * 1e5, 1) if mean_deaths is not None and pop50.get(hva) else "",
            smoking_20_64_pct=s2064[1] if s2064 else "", smoking_20_64_year=s2064[0] if s2064 else "",
            smoking_65plus_pct=s65[1] if s65 else "", smoking_65plus_year=s65[0] if s65 else ""))
    with open(AREA / "county_indicators.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    es = eurostat_ct_exams()
    with open(AREA / "national_ct_exams.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "providers", "per_100k"])
        w.writeheader(); w.writerows(es)
    return dict(municipalities=len(cmap), counties=len(rows), eurostat_rows=len(es))
