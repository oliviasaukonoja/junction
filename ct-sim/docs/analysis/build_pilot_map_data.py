#!/usr/bin/env python3
"""Build the pilot map data (map/pilot_map.json and map/private/pilot_map_advanced.json) from files in this repository.

Run:  python3 ct-sim/docs/analysis/build_pilot_map_data.py      (inputs written by fetch_pilot_inputs.py are already in the repo)

Routes come from map/route_engine.py: the ctsim optimiser chooses stops and days; the engine orders them as an open path on OpenStreetMap road
times (no forced return to the start, a charge for driving past a stop that is visited on another leg) and recomputes distance, days and cost.
map/private/pilot_map_advanced.json is NOT committed (public repository); regenerate it with this script before deploying.
"""
import csv, hashlib, itertools, json, math, sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "map"))
import route_engine as E   # noqa: E402

CT = REPO / "ct-sim"
T_HOSP = E.DEFAULTS["hospital_minutes"]
GRID = dict(gamma=[0.0, 0.5, 1.0], lam=[0.0, 0.5, 2.0], mu=[0.0, 0.15, 0.5], spare=[0.02, 0.05, 0.10])
BASE = {k: E.DEFAULTS[k] for k in GRID}


def rd(p): return list(csv.DictReader(open(p, encoding="utf-8")))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]
num = E._num

F = {k: CT / v for k, v in dict(
    municipalities="data/routing/municipalities.csv", county_indicators="data/area/county_indicators.csv", county_map="data/area/county_map.csv",
    ct_sites="data/ct_sites/ct_sites.csv", registry="data/registry/cancer_registry_incidence_2020_2024.csv",
    oncology_waits="docs/wait_times_syopataudit_2023_2026.csv", education="data/area/municipal_education_55_74.csv", income="data/area/municipal_income_2024.csv",
    travel="data/routing/travel_matrix_priority.json", settlement="data/routing/settlement_points.csv",
    assumptions="data/model/assumptions.csv").items()}
F["smr"] = REPO / "landing-page/regions.json"
I = E.inputs()
ind = {r["hva_code"]: r for r in rd(F["county_indicators"])}
inc = {r["code"]: (num(r["at_risk_of_poverty_rate_pct"]), num(r["median_disposable_cash_income_adults_eur"])) for r in rd(F["income"])}
reg_rows, wait_rows, ct_rows = rd(F["registry"]), rd(F["oncology_waits"]), I["ct_rows"]

# ---- assumption grid: which stops are stable ------------------------------------------------------------------------------
keys = list(GRID); combos = list(itertools.product(*[GRID[k] for k in keys])); N = len(combos)
grid_out, seen, days = [], {c: {} for c in E.PRIORITY}, {c: {} for c in E.PRIORITY}
for combo in combos:
    pr = dict(zip(keys, combo)); rec = dict(params=pr, counties={})
    for code in E.PRIORITY:
        p = E.plan(dict(pr, counties=[code]), geometry=False)
        rec["counties"][code] = dict(additional=p["totals"]["additional"], days=p["totals"]["working_days"], stops=[[s["name"], s["days"], s["additional"]] for s in p["stops"]])
        for s in p["stops"]:
            seen[code][s["name"]] = seen[code].get(s["name"], 0) + 1; days[code].setdefault(s["name"], []).append(s["days"])
    grid_out.append(rec)

# ---- baseline routes and region data ---------------------------------------------------------------------------------------
w, rows, prm, cen, scn, fixed, fixed_idx = E.make_world(E.clean_spec({}))
by_name = {r["name"]: r for r in rows}
counties_out, muni_out = {}, []
for code, meta0 in E.PRIORITY.items():
    p = E.plan(dict(counties=[code]))
    for s in p["stops"]:
        n = seen[code].get(s["name"], 0)
        s["stability"] = dict(share=round(n / N, 2), days_min=min(days[code].get(s["name"], [0])), days_max=max(days[code].get(s["name"], [0])))
        if n / N < 0.9: s["flags"].append("unstable")
    assigned = {m: s["name"] for s in p["stops"] for m in s["catchment"]}
    mem = [r for r in rows if I["cmap"][r["code"]] == code]
    for r in mem:
        c = I["muni"][r["code"]]; pov, med = inc.get(r["code"], (None, None))
        muni_out.append(dict(code=r["code"], name=r["name"], county=code, lat=r["lat"], lon=r["lon"], pop_all=int(c["pop_all"]), pop_50_74=r["pop"], eligible=round(r["elig"]),
                             foreign_share=round(r["f"], 3), sparse_share=num(c["sparse_share"]), basic_share=I["edu"].get(r["code"]), poverty_rate=pov, median_income=med,
                             nearest_ct=r["ct_town"], tt_ct_min=round(r["tt_ct"]), ct_status=E.town_status(r["ct_town"]), bus_stop=assigned.get(r["name"])))
    sm = I["smr"][meta0["registry"]]; ic = ind[code]
    lung = {s: next(x for x in reg_rows if x["area"] == meta0["registry"] and x["sex"] == s) for s in ("Miehet", "Naiset")}
    ct_here = [x for x in ct_rows if x["county"].split(" (")[0] == meta0["ct_county"]]
    towns = sorted({x["municipality"] for x in ct_here})
    counties_out[code] = dict(
        code=code, names={k: meta0[k] for k in ("fi", "sv", "en")},
        facts=dict(pop_all=int(ic["pop_all"]), pop_50_74=int(ic["pop_50_74"]), lung_deaths_per_year=num(ic["lung_deaths_mean_2021_2025"]),
                   lung_deaths_per100k_crude=num(ic["lung_deaths_per_100k_crude"]), smoking_20_64=num(ic["smoking_20_64_pct"]), smoking_65plus=num(ic["smoking_65plus_pct"]),
                   smr=dict(deaths=sm["deaths"], expected=sm["expected"], smr=sm["smr"], lo=sm["lo"], hi=sm["hi"], rank=sm["rank"]),
                   lung_asr=dict(men=num(lung["Miehet"]["asr_lung_per100k_finland2014"]), women=num(lung["Naiset"]["asr_lung_per100k_finland2014"])),
                   lung_cases_2020_24=int(lung["Miehet"]["new_cases_lung_2020_2024"]) + int(lung["Naiset"]["new_cases_lung_2020_2024"]),
                   oncology_waits=[dict(year=x["year"], assess_over90=num(x["assess_pct_over90d"]), assess_months=int(x["assess_months_reported"]),
                                        treat_over90=num(x["treat_pct_over90d"]), treat_months=int(x["treat_months_reported"])) for x in wait_rows if x["area"] == meta0["registry"]]),
        model=p["counties"][code],
        hospital=dict(towns=[dict(town=t, status=E.town_status(t), lat=by_name[t]["lat"], lon=by_name[t]["lon"],
                                  sites=[dict(facility=x["facility"], type=x["facility_type"], status=x["ct_status"], scanners=(int(x["n_scanners"]) if x["n_scanners"] else None),
                                              evidence=x["evidence"], url=x["source_url"], date=x["source_date"] or None, note=x["notes"] or None) for x in ct_here if x["municipality"] == t])
                             for t in towns if t in by_name]),
        bus=dict(stops=p["stops"], legs=p["legs"], start=p["start"], end=p["end"], totals=p["totals"], overlap_km=p["overlap_km"], schematic_legs=p["schematic_legs"]),
        scenarios=N)
    print(meta0["en"], "|", p["start"], "->", p["end"], "|", p["totals"]["stops"], "stops |", p["totals"]["path_km"], "km/pass | overlap", p["overlap_km"], "km")

# ---- engine v1 for comparison (straight line x 1.3, crude mortality weight, closed tour) ----------------------------------------
R, S = E.R, E.S
all_rows = R.load()
scn1 = {"objective": "weighted", "risk_model": "area", "ct_sites": "confirmed+likely", "routing": {"lam": 0.5}}
prm1, _, cen1 = S.setup(scn1)
w1 = R.World(all_rows, prm1, S.fixed_names(scn1), area=S.area_hook(scn1, prm1))
v1 = {}
for code in E.PRIORITY:
    e1 = w1.evaluate(w1.optimise({r["name"] for r in all_rows if r.get("county") == code}, "weighted"))
    v1[code] = dict(additional=round(e1["additional"]), days=round(e1["total_days"], 1), stops=[[s["name"], round(s["days"], 1), round(s["additional"])] for s in e1["stop_detail"]])

# ---- correlations between municipal factors -------------------------------------------------------------------------------------
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v)
    for k, i in enumerate(o): r[i] = k
    return r
def corr(a, b):
    n = len(a); ma, mb = sum(a) / n, sum(b) / n
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
cols = {"basic_share": [], "poverty": [], "median_income": [], "foreign_share": [], "sparse_share": []}
for code, m in I["muni"].items():
    pov, med = inc.get(code, (None, None)); e = I["edu"].get(code)
    if None in (pov, med, e): continue
    for k, v in zip(cols, (e, pov, med, float(m["foreign_lang_share"] or 0), float(m["sparse_share"] or 0))): cols[k].append(v)
cor = {f"{a}|{b}": round(corr(rank(cols[a]), rank(cols[b])), 2) for a, b in itertools.combinations(cols, 2)}

# ---- write ------------------------------------------------------------------------------------------------------------------------
json.dump(I["legs"], open(E.LEG_CACHE, "w", encoding="utf-8"), separators=(",", ":"))
nat_lung = {s: next(x for x in reg_rows if x["area"] == "Koko maa" and x["sex"] == s) for s in ("Miehet", "Naiset")}
nat_f = sum(r["f"] * r["pop"] for r in I["rows0"].values()) / sum(r["pop"] for r in I["rows0"].values())
meta = dict(
    generated=date.today().isoformat(), builder="ct-sim/docs/analysis/build_pilot_map_data.py", priority=list(E.PRIORITY), version=3,
    sources={k: dict(path=str(Path(p).relative_to(REPO)), sha256=sha(p)) for k, p in F.items()},
    planner_assumptions={k: prm[k] for k in ("k_elig", "ct_per_1000", "spare_share", "wait0", "u0", "d0_fixed", "d0_mobile", "pool_km", "eligible_share", "work_days",
                                              "interval", "minority_factor_fixed", "minority_factor_mobile", "cycles", "setup_days", "driving_h") if k in prm},
    weights=dict(BASE, smr_cap=list(E.SMR_CAP), education_mean=round(I["edu_mean"], 3), education_sd=round(I["edu_sd"], 3)),
    thresholds=dict(hospital_invite_min=T_HOSP, far_stop_min=E.T_FAR),
    ct_sites_total=len(ct_rows), ct_towns_total=len(fixed), ct_sites_with_scanner_count=sum(1 for x in ct_rows if x["n_scanners"]),
    national_lung_asr=dict(men=num(nat_lung["Miehet"]["asr_lung_per100k_finland2014"]), women=num(nat_lung["Naiset"]["asr_lung_per100k_finland2014"])),
    national_foreign_share_50_74=round(nat_f, 3), national_basic_share_55_74=round(I["edu_mean"], 3),
    travel=dict(source=I["tm"]["source"], fetched=I["tm"]["fetched"]), scenarios=N, limits={k: list(v) for k, v in E.LIMITS.items()})
ctt = [dict(town=rows[j]["name"], lat=rows[j]["lat"], lon=rows[j]["lon"], status=E.town_status(rows[j]["name"]), county=I["cmap"][rows[j]["code"]]) for j in fixed_idx]
pub = dict(meta=meta, counties=counties_out, municipalities=muni_out, ct_towns=sorted(ctt, key=lambda x: x["town"]))
(REPO / "map/pilot_map.json").write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
(REPO / "map/private").mkdir(parents=True, exist_ok=True)
adv = dict(generated=meta["generated"], grid=GRID, base=BASE, scenarios=grid_out, engine_v1=v1, correlations_spearman_municipalities=cor, n_municipalities_corr=len(cols["basic_share"]))
(REPO / "map/private/pilot_map_advanced.json").write_text(json.dumps(adv, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("wrote map/pilot_map.json", (REPO / "map/pilot_map.json").stat().st_size, "bytes; advanced", (REPO / "map/private/pilot_map_advanced.json").stat().st_size, "bytes;", N, "scenarios")
