"""Cost, capacity and outcome model for a mobile low-dose CT (LDCT) lung screening unit in Finland.

Every parameter is (low, central, high) with a source tag:
  SRC    = taken from a source found in this project (see docs/report for URLs; most read as search summaries only)
  MEM    = recalled from published trials, NOT re-verified -> verify before citing
  ASSUME = our own planning assumption with no source found; replace with quotes/data

Nothing here is a forecast. It shows which assumptions drive the answer.
Scenario files can override any parameter: a number sets all three values, a [low, central, high] list sets the range.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

from . import paths

# name: (low, central, high, unit, tag, note)
PARAMS: dict[str, tuple] = {
    # ---- population & eligibility
    "pop_50_74": (1_695_391, 1_695_391, 1_695_391, "persons", "SRC", "Statistics Finland table 11re, 31 Dec 2025 (data/routing/municipalities.csv)"),
    "eligible_share": (0.04, 0.07, 0.12, "share of 50-74", "ASSUME", "No Finnish pack-year analysis found. Oulu pilot used >=15 cig/d x25y or >=10 x30y, age 50-74. US 2021 criteria roughly double eligibility vs 2013"),
    "uptake_first": (0.30, 0.50, 0.72, "share of invited scanned", "SRC", "London invitation cohort 31% responded; Yorkshire trial 56.5-73.2% depending on reminder stage. Oulu 96.7% was volunteers - not used"),
    "interval_years": (1.0, 2.0, 2.0, "years between scans", "ASSUME", "NELSON-style ~2y vs NLST annual"),
    "repeat_adherence": (0.55, 0.66, 0.80, "share returning", "SRC", "Atrium Health mobile unit: 66% returned for 2nd scan"),
    # ---- clinical effect
    "baseline_mort_per1000py": (2.0, 3.3, 4.5, "lung deaths /1000 person-yr", "SRC", "NELSON control arm 3.30; Finnish eligible-group rate unknown (low/high are assumptions)"),
    "rate_ratio": (0.94, 0.76, 0.61, "RR lung-cancer death", "SRC", "NELSON 10y RR 0.76 (95% CI 0.61-0.94); NLST 20% reduction (CI 6.8-26.7). Women: 0.67 (CI 0.38-1.14) not significant"),
    "detect_rate_per_scan": (0.008, 0.010, 0.015, "cancers per scan", "MEM", "Trial prevalence-round yields ~1%; recalled, not re-verified"),
    # ---- throughput
    "slot_minutes": (30, 20, 15, "min per participant", "ASSUME", "Scan itself ~10 min per one UK source; add check-in, consent, smoking history"),
    "op_hours_per_day": (7.0, 7.5, 8.0, "hours", "ASSUME", ""),
    "scan_days_per_year": (120, 170, 200, "days", "ASSUME", "Winter (-25C), relocation days, servicing, holidays"),
    "fill_rate": (0.55, 0.75, 0.90, "booked slots attended", "ASSUME", "No-shows and empty slots at small stops"),
    # ---- capex (EUR)
    "capex_vehicle": (250_000, 400_000, 700_000, "EUR", "ASSUME", "Vehicle/trailer, shielding, power, heating. US sources: unit $300k-1.5M all-in"),
    "capex_scanner": (250_000, 350_000, 550_000, "EUR", "ASSUME", "US source: LDCT scanner $150-300k; mobile premium + install + QA"),
    "life_years": (6, 8, 10, "years", "ASSUME", ""),
    "discount_rate": (0.03, 0.03, 0.03, "rate", "ASSUME", "Common health-economics default"),
    "residual_share": (0.0, 0.10, 0.20, "share of capex", "ASSUME", ""),
    # ---- opex (EUR/yr)
    "scanner_service_share": (0.07, 0.10, 0.12, "of scanner price/yr", "ASSUME", "Typical service contract range"),
    "vehicle_maint": (10_000, 18_000, 30_000, "EUR/yr", "ASSUME", ""),
    "km_per_year": (20_000, 45_000, 70_000, "km", "ASSUME", "Depends on route design"),
    "eur_per_km": (0.5, 0.8, 1.2, "EUR/km", "ASSUME", "Diesel + generator/heating + tyres, heavy vehicle"),
    "insurance": (8_000, 14_000, 25_000, "EUR/yr", "ASSUME", ""),
    "fte": (3.0, 3.5, 4.5, "FTE", "ASSUME", "2 radiographers + driver/assistant + part-time coordinator/cessation nurse"),
    "salary_month": (3_400, 3_600, 4_000, "EUR/month", "SRC", "Radiographer: Duunitori 3,576 avg (wellbeing counties, 2024); Tyomarkkinatori median 3,557"),
    "oncost_mult": (1.30, 1.35, 1.45, "x", "ASSUME", "Employer on-costs"),
    "cover_factor": (1.00, 1.15, 1.25, "x", "ASSUME", "Sick/holiday cover"),
    "stops_per_year": (40, 60, 100, "stops", "ASSUME", ""),
    "cost_per_stop": (300, 600, 1_500, "EUR", "ASSUME", "Host site, heated shelter, power hook-up, signage"),
    # ---- per-scan variable (EUR)
    "read_minutes": (2.5, 4.0, 8.0, "min per scan", "ASSUME", "Incl. double reading where used"),
    "radiologist_hour": (110, 150, 220, "EUR/h", "ASSUME", "No Finnish radiologist cost found"),
    "admin_per_scan": (5, 10, 25, "EUR", "ASSUME", "Invitation, booking, IT, letters"),
    "p_extra_ct": (0.05, 0.10, 0.23, "per scan", "SRC", "NELSON: 9.2% had >=1 extra CT; NLST per-round false positive 23.3% (Lung-RADS lower)"),
    "cost_extra_ct": (150, 200, 300, "EUR", "ASSUME", ""),
    "p_workup": (0.015, 0.025, 0.05, "per scan", "SRC", "NELSON referral 2.1%"),
    "cost_workup": (2_000, 3_500, 6_000, "EUR", "ASSUME", "PET-CT, biopsy, MDT"),
    "p_incidental_secondary": (0.02, 0.04, 0.08, "per scan", "SRC", "SUMMIT: ~1 in 25 may need secondary-care review"),
    "cost_incidental_secondary": (200, 400, 800, "EUR", "ASSUME", ""),
    "p_incidental_primary": (0.03, 0.05, 0.08, "per scan", "SRC", "SUMMIT: ~1 in 20 need primary-care review"),
    "cost_incidental_primary": (50, 80, 150, "EUR", "ASSUME", ""),
    "cessation_per_scan": (20, 60, 150, "EUR", "ASSUME", "Brief advice/referral; not all smokers"),
    # ---- area model: eligibility, CT capacity, campaign (ctsim.area)
    "k_elig": (0.55, 0.80, 1.10, "eligible persons per current daily smoker aged 50-74", "ASSUME", "Eligible = current smokers with >=20 pack-years plus recent quitters; no Finnish pack-year data found, so this scales the verified smoking prevalence"),
    "ct_per_1000": (35, 60, 90, "CT exams per 1000 inhabitants per year", "SRC", "Eurostat hospital CT exams per 100k: 3,300-3,900 (2019-2021) vs 8,300-9,300 (2022-2024); series breaks, so a wide range"),
    "spare_share": (0.02, 0.05, 0.10, "share of CT volume free for screening", "ASSUME", "No data on spare CT capacity by county"),
    "wait0": (2, 4, 8, "weeks", "ASSUME", "Baseline CT wait; no county CT waiting-time data found. data/area/ct_waits.csv overrides it"),
    "uptake_boost_per_intensity": (0.1, 0.3, 0.6, "relative uptake uplift per unit of campaign intensity", "ASSUME", "Campaign effect on uptake among eligible people is unknown"),
    "spill_per_int": (0.01, 0.03, 0.08, "share of non-eligible people 50-74 seeking a scan per unit campaign intensity", "ASSUME", "Worried-well demand created by a campaign is unknown"),
    # ---- comparator and additionality
    "fixed_site_scan_cost": (80, 130, 200, "EUR", "ASSUME", "Marginal acquisition cost at an existing hospital CT with spare capacity. No Finnish figure found"),
    "additionality": (0.15, 0.35, 0.60, "share of mobile scans who would NOT attend a fixed site", "ASSUME", "The key unknown. Pilot must measure it"),
}


def with_overrides(overrides: dict | None = None) -> dict[str, tuple]:
    """Copy of PARAMS with scenario overrides applied (number -> fixed, [lo, mid, hi] -> range)."""
    out = dict(PARAMS)
    for k, v in (overrides or {}).items():
        if k not in out:
            raise KeyError(f"unknown model parameter: {k}")
        unit, tag, note = out[k][3:]
        if isinstance(v, (list, tuple)):
            if len(v) != 3:
                raise ValueError(f"{k}: expected [low, central, high]")
            lo, mid, hi = v
        else:
            lo = mid = hi = v
        out[k] = (lo, mid, hi, unit, "SCENARIO", f"override of: {note}")
    return out


def central(params: dict | None = None) -> dict[str, float]:
    return {k: v[1] for k, v in (params or PARAMS).items()}


def draw(params: dict, rng: random.Random) -> dict[str, float]:
    # random.triangular(low, high, mode); works for reversed ranges (low > high)
    return {k: (rng.triangular(v[0], v[2], v[1]) if v[0] != v[2] else v[1]) for k, v in params.items()}


def annuity(r: float, n: float) -> float:
    return r / (1 - (1 + r) ** -n) if r else 1 / n


def unit(p: dict) -> dict:
    """All results for ONE mobile unit under parameter set p."""
    per_day = p["op_hours_per_day"] * 60 / p["slot_minutes"]
    scans = p["scan_days_per_year"] * per_day * p["fill_rate"]
    capex = p["capex_vehicle"] + p["capex_scanner"]
    cap_annual = (capex - capex * p["residual_share"] / (1 + p["discount_rate"]) ** p["life_years"]) * annuity(p["discount_rate"], p["life_years"])
    staff = p["fte"] * p["salary_month"] * 12 * p["oncost_mult"] * p["cover_factor"]
    fixed = (cap_annual + p["capex_scanner"] * p["scanner_service_share"] + p["vehicle_maint"]
             + p["km_per_year"] * p["eur_per_km"] + p["insurance"] + staff
             + p["stops_per_year"] * p["cost_per_stop"])
    var = (p["read_minutes"] / 60 * p["radiologist_hour"] + p["admin_per_scan"]
           + p["p_extra_ct"] * p["cost_extra_ct"] + p["p_workup"] * p["cost_workup"]
           + p["p_incidental_secondary"] * p["cost_incidental_secondary"]
           + p["p_incidental_primary"] * p["cost_incidental_primary"] + p["cessation_per_scan"])
    cost_per_scan = fixed / scans + var
    a = p["additionality"]
    incr = fixed - (1 - a) * scans * p["fixed_site_scan_cost"] + a * scans * var
    cost_per_additional_scan = incr / (a * scans)
    persons_under_surveillance = scans * p["interval_years"]
    deaths_avoided_all = persons_under_surveillance * p["baseline_mort_per1000py"] / 1000 * (1 - p["rate_ratio"])
    deaths_avoided_add = deaths_avoided_all * a
    cancers_found = scans * p["detect_rate_per_scan"]
    cost_per_death_avoided = incr / deaths_avoided_add if deaths_avoided_add > 0 else float("inf")
    return dict(scans=scans, fixed=fixed, var=var, cost_per_scan=cost_per_scan, incr=incr,
                cost_per_additional_scan=cost_per_additional_scan,
                deaths_avoided_all=deaths_avoided_all, deaths_avoided_additional=deaths_avoided_add,
                cancers_found=cancers_found, cost_per_death_avoided=cost_per_death_avoided,
                cap_annual=cap_annual, staff=staff)


def national(p: dict) -> dict:
    elig = p["pop_50_74"] * p["eligible_share"]
    screened_persons = elig * p["uptake_first"]
    scans_per_year = screened_persons / p["interval_years"] * (0.5 + 0.5 * p["repeat_adherence"])
    person_years = screened_persons * 0.5 + screened_persons * 0.5 * p["repeat_adherence"]
    deaths_avoided = person_years * p["baseline_mort_per1000py"] / 1000 * (1 - p["rate_ratio"])
    cancers = scans_per_year * p["detect_rate_per_scan"]
    per_day = p["op_hours_per_day"] * 60 / p["slot_minutes"]
    cap = p["scan_days_per_year"] * per_day * p["fill_rate"]
    return dict(eligible=elig, screened=screened_persons, scans_year=scans_per_year, cancers_year=cancers,
                deaths_avoided_year=deaths_avoided, units_needed=scans_per_year / cap)


def _pct(xs: list, q: float) -> float:
    xs = sorted(xs)
    return xs[int(q * (len(xs) - 1))]


def monte_carlo(params: dict | None = None, n: int = 20_000, seed: int = 20261113) -> list[list]:
    """Rows [scope, metric, central, p5, p50, p95]."""
    params = params or PARAMS
    rng = random.Random(seed)
    c, nat = unit(central(params)), national(central(params))
    U = {k: [] for k in c}
    N = {k: [] for k in nat}
    for _ in range(n):
        d = draw(params, rng)
        u, nn = unit(d), national(d)
        for k in u:
            U[k].append(u[k])
        for k in nn:
            N[k].append(nn[k])
    rows = [["unit", k, c[k], _pct(U[k], .05), _pct(U[k], .5), _pct(U[k], .95)] for k in U]
    rows += [["national", k, nat[k], _pct(N[k], .05), _pct(N[k], .5), _pct(N[k], .95)] for k in N]
    return rows


def tornado(params: dict | None = None) -> list[list]:
    params = params or PARAMS
    base = central(params)
    torn = []
    for k, v in params.items():
        if v[0] == v[2]:
            continue
        res = []
        for val in (v[0], v[2]):
            p = dict(base)
            p[k] = val
            res.append(unit(p))
        torn.append([k, res[0]["cost_per_scan"], res[1]["cost_per_scan"], res[0]["cost_per_death_avoided"], res[1]["cost_per_death_avoided"]])
    torn.sort(key=lambda r: -abs(r[4] - r[3]) if (r[3] != float("inf") and r[4] != float("inf")) else 0)
    return torn


def sweep(params: dict, name: str, values: list[float]) -> list[dict]:
    out = []
    for v in values:
        p = central(params)
        p[name] = v
        out.append({name: v, **unit(p)})
    return out


def write_outputs(params: dict | None = None, out_dir: Path | None = None, n: int = 20_000, seed: int = 20261113) -> dict:
    """Write the CSVs that the report cites and return the central-case summary."""
    params = params or PARAMS
    out_dir = Path(out_dir or paths.MODEL_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)

    def w(name, header, rows):
        with open(out_dir / name, "w", newline="") as f:
            cw = csv.writer(f)
            cw.writerow(header)
            cw.writerows(rows)

    w("assumptions.csv", ["parameter", "low", "central", "high", "unit", "tag", "note"],
      [[k, *v[:3], *v[3:]] for k, v in params.items()])
    w("monte_carlo_summary.csv", ["scope", "metric", "central_case", "p5", "p50", "p95"], monte_carlo(params, n, seed))
    w("tornado.csv", ["parameter", "cost_per_scan_at_low", "cost_per_scan_at_high", "cost_per_death_avoided_at_low", "cost_per_death_avoided_at_high"], tornado(params))
    curve = [[r["fill_rate"], round(r["scans"]), round(r["cost_per_scan"]), round(r["cost_per_additional_scan"])]
             for r in sweep(params, "fill_rate", [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])]
    w("utilisation_curve.csv", ["fill_rate", "scans_per_year", "cost_per_scan_eur", "cost_per_additional_scan_eur_at_central_additionality"], curve)
    add = [[r["additionality"], round(r["cost_per_additional_scan"]), round(r["deaths_avoided_additional"], 1), round(r["cost_per_death_avoided"])]
           for r in sweep(params, "additionality", [0.1, 0.2, 0.35, 0.5, 0.7, 1.0])]
    w("additionality_sweep.csv", ["additionality", "cost_per_additional_scan_eur", "deaths_avoided_per_unit_year_additional_only", "cost_per_death_avoided_eur"], add)
    return {"unit": unit(central(params)), "national": national(central(params))}
