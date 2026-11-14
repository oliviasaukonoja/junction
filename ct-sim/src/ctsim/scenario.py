"""Scenario runner: one JSON document in, one JSON-serialisable result out.

This is the unit that the CLI, the local server, the Modal function and the database all share.

Scenario schema (all keys optional except name):
{
  "name": "tampere-100km",
  "objective": "weighted" | "scans" | "additional",
  "region": {"base": "Tampere", "radius_km": 100} | null,      # null = whole country
  "risk_model": "area" (default) | "uniform",                    # area = smoking-based eligibility, mortality weights, county CT capacity; uniform = legacy
  "routing": {"lam": 0.5, "d0_fixed": 120, ...},                 # overrides of routing.DEFAULT
  "model": {"additionality": [0.15, 0.35, 0.6], ...},            # overrides of model.PARAMS (number or [lo, mid, hi])
  "fixed_sites": ["Helsinki", ...] | null,                       # explicit CT town list (wins over ct_sites)
  "ct_sites": "placeholder" | "confirmed" | "confirmed+likely",   # which CT list: placeholder (default) or the researched data/ct_sites/ct_sites.csv
  "monte_carlo": {"n": 2000, "seed": 1}                          # optional
}
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from . import area, ctsites
from . import model as M
from . import paths, routing as R

VERSION = "0.1.0"


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def scenario_hash(scn: dict) -> str:
    return hashlib.sha256(json.dumps(scn, sort_keys=True).encode()).hexdigest()[:12]


def data_fingerprint() -> dict:
    """Hash of the input table, so a stored run can be tied to the data it used."""
    p = paths.MUNICIPALITIES_CSV
    return {"municipalities_csv_sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16]} if p.exists() else {}


def setup(scn: dict) -> tuple[dict, dict, dict]:
    """(routing parameters, model parameter ranges, model central values) for a scenario."""
    prm = dict(R.DEFAULT, **scn.get("routing", {}))
    params = M.with_overrides(scn.get("model"))
    cen = M.central(params)
    prm["spd"] = M.unit(cen)["scans"] / cen["scan_days_per_year"]
    for k in ("k_elig", "ct_per_1000", "spare_share", "wait0", "spill_per_int"):     # area-model assumptions travel with prm so sweeps can vary them
        prm.setdefault(k, cen[k])
    prm["campaign_boost"] = prm["campaign_intensity"] * cen["uptake_boost_per_intensity"]
    return prm, params, cen


def area_hook(scn: dict, prm: dict):
    """The area model (smoking-based eligibility, mortality weights, county CT capacity) unless the scenario asks for the legacy uniform model."""
    if scn.get("risk_model", "area") == "uniform":
        return None
    return area.make_hook(intensity=prm["campaign_intensity"], triage=prm["triage"], priority=bool(prm["priority_eligible"]), gamma=prm["risk_gamma"])


def fixed_names(scn: dict) -> list[str]:
    """CT towns for a scenario: explicit 'fixed_sites' list, else researched list via 'ct_sites' mode, else the placeholder list."""
    if scn.get("fixed_sites"):
        return list(scn["fixed_sites"])
    if scn.get("ct_sites") in ("confirmed", "confirmed+likely"):
        return ctsites.names(scn["ct_sites"])
    if scn.get("ct_sites") not in (None, "placeholder"):
        raise ValueError("ct_sites must be 'placeholder', 'confirmed' or 'confirmed+likely'")
    return list(R.FIXED_SITE_NAMES)


def _area_summary(w, ev, rows, cen, prm, fixed: list[str], reg=None):
    """Per-county eligibility, capacity, waits and reach, plus national campaign totals. None for the legacy uniform model."""
    info = w.area_info
    if not info:
        return None, None, None
    add_c: dict = {}
    for i, (_, a) in ev["muni_additional"].items():
        add_c[rows[i]["county"]] = add_c.get(rows[i]["county"], 0.0) + a
    towns: dict = {}
    for r in rows:
        if r["name"] in fixed:
            towns.setdefault(r["county"], []).append(r["name"])
    interval = prm["interval"]
    in_reg = [r for r in rows if reg is None or r["name"] in reg]
    present = {r["county"] for r in in_reg}               # counties with at least one municipality in the area shown
    counties = []
    for c, i in info.items():
        if c not in present:
            continue
        need = i["eligible"] / interval
        base = sum(r["elig"] * r["u_fixed"] for r in rows if r["county"] == c) / interval
        with_truck = base + add_c.get(c, 0.0)
        counties.append(dict(
            hva_code=c, county=i["county"], eligible=round(i["eligible"]), pop50=i["pop50"], lung_deaths_per_100k_50_74=i["lung_deaths_per_100k_50_74"],
            mort_index=round(i["mort_index"], 3), smoking_20_64=i["smoking_20_64"], smoking_65plus=i["smoking_65plus"],
            ct_towns=sorted(towns.get(c, [])), volume=round(i["volume"]), spare=round(i["spare"]), demand_eligible=round(i["demand_eligible"]),
            demand_ineligible=round(i["demand_ineligible"]), served_share=round(i["served_share"], 3), shortfall=round(i["shortfall"]),
            extra_wait_weeks=round(i["extra_wait_weeks"], 1), baseline_wait_weeks=i["baseline_wait_weeks"], baseline_wait_is_data=i["baseline_wait_is_data"],
            wait_weeks=round(i["wait_weeks"], 1), annual_need=round(need), screened_fixed=round(base), screened_with_truck=round(with_truck),
            coverage_fixed=round(base / need, 3) if need else None, coverage_with_truck=round(with_truck / need, 3) if need else None))
    # reach is restricted to the municipalities in the area shown (whole country when no region is set)
    need = sum(r["elig"] for r in in_reg) / interval
    base = sum(r["elig"] * r["u_fixed"] for r in in_reg) / interval
    wtruck = base + sum(a for i_, (_, a) in ev["muni_additional"].items() if reg is None or rows[i_]["name"] in reg)
    need, base, wtruck = round(need), round(base), round(wtruck)
    reach = dict(scope=(f"{len(in_reg)} municipalities in the area" if reg is not None else "whole country"), eligible_persons=round(sum(r["elig"] for r in in_reg)), annual_scans_needed=need, screened_fixed_only=base, screened_with_truck=wtruck,
                 coverage_fixed_only=round(base / need, 3) if need else None, coverage_with_truck=round(wtruck / need, 3) if need else None)
    unit_scans = M.unit(cen)["scans"]
    worst = max(counties, key=lambda c: c["extra_wait_weeks"])
    short = sum(c["shortfall"] for c in counties)
    campaign = dict(intensity=prm["campaign_intensity"], triage=prm["triage"], priority_eligible=bool(prm["priority_eligible"]), uptake_boost=round(prm["campaign_boost"], 3),
                    demand_eligible=sum(c["demand_eligible"] for c in counties), demand_ineligible=sum(c["demand_ineligible"] for c in counties),
                    free_capacity=sum(c["spare"] for c in counties), shortfall=short, counties_with_extra_wait_over_4_weeks=sum(1 for c in counties if c["extra_wait_weeks"] > 4),
                    longest_extra_wait=dict(county=worst["county"], weeks=worst["extra_wait_weeks"]), truck_equivalents_of_shortfall=round(short / unit_scans, 1) if unit_scans else None)
    counties.sort(key=lambda c: -c["extra_wait_weeks"])
    return counties, reach, campaign


def run(scn: dict) -> dict:
    t0 = time.time()
    prm, params, cen = setup(scn)
    rows = R.load()
    w = R.World(rows, prm, fixed_names(scn), area=area_hook(scn, prm))
    reg = None
    if scn.get("region"):
        reg = R.region(w, scn["region"]["base"], scn["region"]["radius_km"])
    plan = w.optimise(reg, scn.get("objective", "weighted"))
    ev = w.evaluate(plan)
    cost = w.cost(ev, cen)
    fixed = fixed_names(scn)
    counties, reach, campaign = _area_summary(w, ev, rows, cen, prm, fixed, reg)
    out = dict(
        scenario=scn, scenario_hash=scenario_hash(scn), version=VERSION, data=data_fingerprint(),
        route=dict(order=ev["order"], km_per_year=ev["km"], working_days=ev["total_days"], scan_days=ev["scan_days"], stops=ev["stop_detail"]),
        outcomes=dict(scans=ev["scans"], additional=ev["additional"], additional_in_places_over_60km_from_ct=ev["add_far"],
                      additional_foreign_language_weighted=ev["add_minority"]),
        cost=dict(total_eur=cost["total"], per_scan_eur=cost["per_scan"], per_additional_eur=cost["per_additional"]),
        layer=[dict(code=r["code"], name=r["name"], lat=r["lat"], lon=r["lon"], pop=r["pop"], foreign_share=r["f"],
                    d_fixed_km=round(r["d_fixed"], 1), u_fixed=round(r["u_fixed"], 3),
                    in_region=(reg is None or r["name"] in reg),
                    eligible=round(r.get("elig", 0.0)), mort_index=round(r.get("mort_index", 1.0), 3), county=r.get("county"),
                    smoke_share=round(r.get("smoke_share", 0.0), 4),
                    stop=ev["muni_additional"].get(r["i"], (None, 0.0))[0],
                    additional=round(ev["muni_additional"].get(r["i"], (None, 0.0))[1], 1)) for r in rows],
        counties=counties, reach=reach, campaign=campaign, risk_group=area.RISK_GROUP if counties else None,
        warnings=[{"confirmed": "CT sites: researched list, confirmed only (check with counties)", "confirmed+likely": "CT sites: researched list incl. 'likely' (check with counties)"}.get(scn.get("ct_sites"), "Custom CT site list" if scn.get("fixed_sites") else "Placeholder CT site list"),
                  "Uptake curves, costs and eligible share are assumptions (see data/model/assumptions.csv)"]
                 + (["Eligible people = verified smoking prevalence x an assumed factor; CT volume, spare capacity and baseline waits are assumptions; no county CT wait data (see data/area/DATA_STATUS.json)"] if counties else []),
    )
    mc = scn.get("monte_carlo")
    if mc:
        rows_mc = M.monte_carlo(params, int(mc.get("n", 2000)), int(mc.get("seed", 1)))
        out["model_monte_carlo"] = [dict(zip(["scope", "metric", "central", "p5", "p50", "p95"], r)) for r in rows_mc]
    out["seconds"] = round(time.time() - t0, 3)
    return out
