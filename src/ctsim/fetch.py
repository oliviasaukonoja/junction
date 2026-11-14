"""Refresh public inputs from Statistics Finland (PxWeb API + geoserver) and rebuild the municipality table.

Variable codes in PxWeb tables contain dates and change between releases, so they are discovered from table
metadata by prefix instead of being hard-coded. Table ids are parameters because Statistics Finland renames
tables (e.g. 15k6 -> 15k7) when it publishes a new year; check `list_tables()` if a fetch fails.

All data is public and aggregate. No personal data is used or sent.
"""
from __future__ import annotations

import csv
import itertools
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from . import geo, paths

API = "https://statfin.stat.fi/PxWeb/api/v1/en/StatFin/vaerak"
WFS = "https://geo.stat.fi/geoserver/tilastointialueet/wfs"
UA = {"User-Agent": "ctsim-research/0.1 (public aggregate data refresh)"}

TABLES = dict(population="11re", language="11rm", urban="15k6")


def _get(url: str, data: bytes | None = None, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, data=data, headers={**UA, **({"Content-Type": "application/json"} if data else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def list_tables() -> list[dict]:
    return json.loads(_get(f"{API}/"))


def meta(table: str) -> dict:
    return json.loads(_get(f"{API}/{table}.px"))


def _var(m: dict, prefix: str) -> dict:
    return next(v for v in m["variables"] if v["code"].startswith(prefix))


def query(table: str, selections: dict[str, list[str]], m: dict | None = None) -> dict:
    """selections maps a variable-code PREFIX to a list of values or ['*']; unspecified variables take their first value."""
    m = m or meta(table)
    q = []
    for v in m["variables"]:
        sel = next((s for p, s in selections.items() if v["code"].startswith(p)), None)
        if sel is None:
            sel = [v["values"][0]]
        q.append({"code": v["code"], "selection": {"filter": "all" if sel == ["*"] else "item", "values": sel}})
    body = json.dumps({"query": q, "response": {"format": "json-stat2"}}).encode()
    return json.loads(_get(f"{API}/{table}.px", body))


def jsonstat(d: dict) -> dict[tuple, float | None]:
    """json-stat2 -> {(label0, label1, ...): value} keyed by category CODES in dimension order."""
    idx = []
    for k in d["id"]:
        ix = d["dimension"][k]["category"]["index"]
        idx.append(list(ix.keys()) if isinstance(ix, dict) else list(ix))
    return {key: d["value"][i] for i, key in enumerate(itertools.product(*idx))}


def _dimpos(d: dict, prefix: str) -> int:
    return next(i for i, k in enumerate(d["id"]) if k.startswith(prefix))


def latest_year(m: dict) -> str:
    return _var(m, "timeperiod")["values"][-1]


def fetch_all(raw: Path | None = None, tables: dict | None = None) -> dict:
    """Download the four raw files and return metadata about what was fetched."""
    raw = Path(raw or paths.RAW)
    raw.mkdir(parents=True, exist_ok=True)
    tables = {**TABLES, **(tables or {})}
    info = {}

    m = meta(tables["population"])
    year = latest_year(m)
    ages = [v for v, t in zip(_var(m, "ikaryhma")["values"], _var(m, "ikaryhma")["valueTexts"]) if t.isdigit() and 50 <= int(t) <= 74]
    d = query(tables["population"], {"alue": ["*"], "ikaryhma": ages, "sukupuoli": ["SSS"], "timeperiod": [year]}, m)
    (raw / "pop_50_74.json").write_text(json.dumps(d))
    info["population"] = dict(table=tables["population"], year=year, updated=d.get("updated"))

    m = meta(tables["language"])
    d = query(tables["language"], {"alue": ["*"], "kieli": ["SSS", "02"], "sukupuoli": ["SSS"], "timeperiod": [latest_year(m)]}, m)
    (raw / "language.json").write_text(json.dumps(d))
    info["language"] = dict(table=tables["language"], year=latest_year(m), updated=d.get("updated"))

    m = meta(tables["urban"])
    vals = _var(m, "taajama")["values"]
    sel = [v for v in vals if re.fullmatch(r"KU\d+", v) or re.fullmatch(r"KU\d+HAJA", v)]
    d = query(tables["urban"], {"taajama": sel, "sukupuoli": ["SSS"], "ikaryhma": ["SSS"], "timeperiod": [latest_year(m)]}, m)
    (raw / "urban.json").write_text(json.dumps(d))
    info["urban"] = dict(table=tables["urban"], year=latest_year(m), updated=d.get("updated"))

    qs = urllib.parse.urlencode(dict(service="WFS", version="2.0.0", request="GetFeature", typeName="tilastointialueet:kunta4500k", outputFormat="application/json"))
    (raw / "kunta.json").write_bytes(_get(f"{WFS}?{qs}"))
    info["geometry"] = dict(layer="tilastointialueet:kunta4500k")
    (raw / "fetch_info.json").write_text(json.dumps(info, indent=2))
    return info


def _centroid(poly):
    ring = poly[0]
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        c = x0 * y1 - x1 * y0
        a += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a), abs(a)) if a else (ring[0][0], ring[0][1], 0)


def build(raw: Path | None = None) -> dict:
    """Join raw files into data/routing/municipalities.csv (centroids, lat/lon, population 50-74, language and sparse-area shares)."""
    raw = Path(raw or paths.RAW)
    geo_json = json.loads((raw / "kunta.json").read_text())
    cen = {}
    for f in geo_json["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        best = max((_centroid(p) for p in polys), key=lambda t: t[2])
        cen[f["properties"]["kunta"]] = (f["properties"]["nimi"], best[0], best[1], sum(_centroid(p)[2] for p in polys) / 1e6)

    pop_d = json.loads((raw / "pop_50_74.json").read_text())
    pop = jsonstat(pop_d)
    pa, ps, pi = _dimpos(pop_d, "alue"), _dimpos(pop_d, "sukupuoli"), _dimpos(pop_d, "ikaryhma")
    pop_by, pop_young, pop_old = {}, {}, {}
    for key, v in pop.items():
        if key[ps] == "SSS":
            pop_by[key[pa]] = pop_by.get(key[pa], 0) + (v or 0)
            tgt = pop_young if int(key[pi]) < 65 else pop_old
            tgt[key[pa]] = tgt.get(key[pa], 0) + (v or 0)
    year = list(pop_d["dimension"][next(k for k in pop_d["id"] if k.startswith("timeperiod"))]["category"]["index"])[0]

    lang_d = json.loads((raw / "language.json").read_text())
    lang = jsonstat(lang_d)
    la, lk = _dimpos(lang_d, "alue"), _dimpos(lang_d, "kieli")
    lang_by = {(key[la], key[lk]): v for key, v in lang.items()}

    urb_d = json.loads((raw / "urban.json").read_text())
    urb = jsonstat(urb_d)
    ut = _dimpos(urb_d, "taajama")
    urb_by = {key[ut]: v for key, v in urb.items()}

    rows = []
    for code, (name, x, y, km2) in sorted(cen.items()):
        k = "KU" + code
        tot, fo = lang_by.get((k, "SSS")), lang_by.get((k, "02"))
        t2, h = urb_by.get(k), urb_by.get(k + "HAJA")
        lat, lon = geo.tm35fin_to_wgs84(x, y)
        rows.append([code, name, round(x), round(y), round(lat, 5), round(lon, 5), round(km2, 1), pop_by.get(k, 0), tot, fo,
                     round(fo / tot, 4) if tot and fo is not None else "", t2, h, round((h or 0) / t2, 4) if t2 else "",
                     pop_young.get(k, 0), pop_old.get(k, 0)])
    paths.ROUTING.mkdir(parents=True, exist_ok=True)
    with open(paths.MUNICIPALITIES_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "name", "x_epsg3067", "y_epsg3067", "lat", "lon", "area_km2_approx", "pop_50_74", "pop_all", "pop_foreign_language",
                    "foreign_lang_share", "pop_all_urban_table", "pop_sparse", "sparse_share", "pop_50_64", "pop_65_74"])
        w.writerows(rows)
    return dict(municipalities=len(rows), pop_50_74=sum(r[7] for r in rows), year=year)
