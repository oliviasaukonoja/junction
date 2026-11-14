#!/usr/bin/env python3
"""Build the pilot map data from files in this repository.

Outputs (map/):
  pilot_map.json                    public: what the default map view shows
  private/pilot_map_advanced.json   served only after the password check: assumption scenarios, v1 comparison, factor correlations.
                                    NOT committed to git (the repository is public); regenerate it with this script before deploying.

Run:  python3 ct-sim/docs/analysis/build_pilot_map_data.py     (needs the files written by fetch_pilot_inputs.py)

What changed from v1 (see the audit): road travel times (OpenStreetMap/OSRM) instead of straight line x 1.3; settlement points instead of
municipality centroids; county SMR (age-standardised, capped) instead of the crude all-age proxy; basic-education share aged 55-74 as a disadvantage
weight; a grid of assumption scenarios to show which stops are stable; hospital-invitation and bus areas kept apart.
The ctsim engine is used unchanged: the travel-time matrix is passed in as the distance matrix and the municipal weights are set after the world is built.

Every figure is observed (public source), modelled (observed data + assumptions) or an assumption. Nothing is a confirmed fact unless observed.
"""
import csv, hashlib, itertools, json, math, sys, time, urllib.request
from datetime import date
from pathlib import Path

CT = Path(__file__).resolve().parents[2]
REPO = CT.parent
sys.path.insert(0, str(CT / "src"))
from ctsim import routing as R, scenario as S   # noqa: E402

PRIORITY = {
    "HVA21": dict(fi="Lappi", sv="Lappland", en="Lapland", registry="Lapin hyvinvointialue", ct_county="Lappi"),
    "HVA10": dict(fi="Kymenlaakso", sv="Kymmenedalen", en="Kymenlaakso", registry="Kymenlaakson hyvinvointialue", ct_county="Kymenlaakso"),
    "HVA06": dict(fi="Satakunta", sv="Satakunta", en="Satakunta", registry="Satakunnan hyvinvointialue", ct_county="Satakunta"),
}
BASE = dict(gamma=1.0, lam=0.5, mu=0.15, spare=0.05)            # baseline weights / assumptions (all assumptions, see meta)
GRID = dict(gamma=[0.0, 0.5, 1.0], lam=[0.0, 0.5, 2.0], mu=[0.0, 0.15, 0.5], spare=[0.02, 0.05, 0.10])
T_HOSP = 45        # minutes: invitation area around a hospital CT (assumption)
T_FAR = 45         # minutes: a bus stop counts as "far from CT" beyond this (assumption)
SMR_CAP = (0.8, 1.3)
LEG_CACHE = CT / "data/routing/osrm_legs_cache.json"


def rd(p): return list(csv.DictReader(open(p, encoding="utf-8")))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


# ---- inputs ----------------------------------------------------------------------------------------------------------------
F = {k: CT / v for k, v in dict(
    municipalities="data/routing/municipalities.csv", county_indicators="data/area/county_indicators.csv", county_map="data/area/county_map.csv",
    ct_sites="data/ct_sites/ct_sites.csv", ct_waits="data/area/ct_waits_TEMPLATE.csv", registry="data/registry/cancer_registry_incidence_2020_2024.csv",
    oncology_waits="docs/wait_times_syopataudit_2023_2026.csv", education="data/area/municipal_education_55_74.csv", income="data/area/municipal_income_2024.csv",
    travel="data/routing/travel_matrix_priority.json", settlement="data/routing/settlement_points.csv", assumptions="data/model/assumptions.csv").items()}
F["smr"] = REPO / "landing-page/regions.json"
ind = {r["hva_code"]: r for r in rd(F["county_indicators"])}
smr_all = {r["name"]: r for r in json.load(open(F["smr"], encoding="utf-8"))}
cmap = {r["code"]: r["hva_code"] for r in rd(F["county_map"])}
edu = {r["code"]: num(r["basic_share"]) for r in rd(F["education"])}
edu_n = {r["code"]: num(r["persons_55_74"]) or 0 for r in rd(F["education"])}
inc = {r["code"]: (num(r["at_risk_of_poverty_rate_pct"]), num(r["median_disposable_cash_income_adults_eur"])) for r in rd(F["income"])}
reg_rows, wait_rows, ct_rows = rd(F["registry"]), rd(F["oncology_waits"]), rd(F["ct_sites"])
muni_csv = {r["code"]: r for r in rd(F["municipalities"])}
tm = json.load(open(F["travel"], encoding="utf-8"))
P = tm["points"]
ct_wait_known = [r for r in rd(F["ct_waits"]) if (r.get("ct_wait_weeks") or "").strip()]

ok_e = [(edu[c], edu_n[c]) for c in edu if edu[c] is not None]
edu_mean = sum(v * n for v, n in ok_e) / sum(n for _, n in ok_e)
edu_sd = math.sqrt(sum(n * (v - edu_mean) ** 2 for v, n in ok_e) / sum(n for _, n in ok_e))


def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v)
    for k, i in enumerate(o): r[i] = k
    return r
def corr(a, b):
    n = len(a); ma, mb = sum(a) / n, sum(b) / n
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))


# ---- world factory ------------------------------------------------------------------------------------------------------------
rows0 = {r["code"]: r for r in R.load()}
D_MIN = [[(v or 0) / 60.0 for v in row] for row in tm["durations_s"]]        # minutes; 1 minute = 1 "km" at the engine's 60 km/h


def make_world(gamma, lam, mu, spare):
    scn = {"objective": "weighted", "risk_model": "area", "ct_sites": "confirmed+likely", "routing": {"lam": lam, "spare_share": spare}}
    prm, params, cen = S.setup(scn)
    rows = []
    for i, p in enumerate(P):
        r = dict(rows0[p["code"]]); r["i"] = i; r["lat"], r["lon"] = p["lat"], p["lon"]; rows.append(r)
    fixed = S.fixed_names(scn)
    w = R.World(rows, prm, fixed, D=D_MIN, area=S.area_hook(scn, prm))
    for r in rows:                                                       # replace the engine's weight with the audited one
        pr = PRIORITY.get(cmap[r["code"]])
        smr = float(smr_all[pr["registry"]]["smr"]) if pr else 1.0
        need = min(max(smr, SMR_CAP[0]), SMR_CAP[1]) ** gamma
        z = ((edu.get(r["code"]) or edu_mean) - edu_mean) / edu_sd
        r["w"] = (1 + lam * min(r["f"] / 0.10, 3.0)) * need * (1 + mu * min(max(z, 0.0), 2.0))
    return w, rows, prm, cen, scn, fixed


def plan_county(w, rows, code):
    reg = {r["name"] for r in rows if r.get("county") == code}
    return w.evaluate(w.optimise(reg, "weighted")), reg


# ---- scenario grid ------------------------------------------------------------------------------------------------------------
grid_out, stop_seen, stop_days = [], {c: {} for c in PRIORITY}, {c: {} for c in PRIORITY}
keys = list(GRID)
combos = list(itertools.product(*[GRID[k] for k in keys]))
for combo in combos:
    pr = dict(zip(keys, combo))
    w, rows, prm, cen, scn, fixed = make_world(**pr)
    rec = dict(params=pr, counties={})
    for code in PRIORITY:
        ev, _ = plan_county(w, rows, code)
        rec["counties"][code] = dict(additional=round(ev["additional"]), days=round(ev["total_days"], 1), far=round(ev["add_far"]),
                                     stops=[[s["name"], round(s["days"], 1), round(s["additional"])] for s in ev["stop_detail"]])
        for s in ev["stop_detail"]:
            stop_seen[code][s["name"]] = stop_seen[code].get(s["name"], 0) + 1
            stop_days[code].setdefault(s["name"], []).append(s["days"])
    grid_out.append(rec)
N = len(combos)

# ---- baseline plan --------------------------------------------------------------------------------------------------------------
w, rows, prm, cen, scn, fixed = make_world(**BASE)
fixed_idx = [r["i"] for r in rows if r["name"] in fixed]
by_name = {r["name"]: r for r in rows}
ct_status = {}
for x in ct_rows:
    ct_status.setdefault(x["municipality"], []).append(x["ct_status"])
def town_status(n): return "confirmed" if "confirmed" in ct_status.get(n, []) else "likely"
for r in rows:
    j = min(fixed_idx, key=lambda k: w.D[r["i"]][k]); r["ct_town"], r["tt_ct"] = rows[j]["name"], w.D[r["i"]][j]

try: leg_cache = json.load(open(LEG_CACHE, encoding="utf-8"))
except Exception: leg_cache = {}
def rdp(pts, eps):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-12
    dm, im = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / L
        if d > dm: dm, im = d, i
    if dm > eps: return rdp(pts[:im + 1], eps)[:-1] + rdp(pts[im:], eps)
    return [pts[0], pts[-1]]
def leg(a, b):
    key = f"{a['lon']:.5f},{a['lat']:.5f};{b['lon']:.5f},{b['lat']:.5f}"
    if leg_cache.get(key) is None:
        try:
            r = json.load(urllib.request.urlopen(f"https://router.project-osrm.org/route/v1/driving/{key}?overview=full&geometries=geojson", timeout=60))
            rt = r["routes"][0]
            leg_cache[key] = dict(minutes=round(rt["duration"] / 60, 1), km=round(rt["distance"] / 1000, 1),
                                  coords=[[round(y, 4), round(x, 4)] for x, y in rdp([tuple(c) for c in rt["geometry"]["coordinates"]], 0.004)])
        except Exception:
            leg_cache[key] = None
        time.sleep(0.4)
    return leg_cache[key]

counties_out, muni_out = {}, []
nat_f = sum(r["f"] * r["pop"] for r in rows0.values()) / sum(r["pop"] for r in rows0.values())
for code, meta0 in PRIORITY.items():
    ev, reg = plan_county(w, rows, code)
    summ, reach, camp = S._area_summary(w, ev, rows, cen, prm, fixed, reg)
    cinfo = next(c for c in summ if c["hva_code"] == code)
    mem = [r for r in rows if r["name"] in reg]
    elig_c = sum(r["elig"] for r in mem)
    sm = smr_all[meta0["registry"]]
    assigned = dict(ev["muni_additional"])
    order = ev["order"]
    legs, route_ok = [], True
    for k in range(len(order)):
        a, b = by_name[order[k]], by_name[order[(k + 1) % len(order)]]
        L = leg(a, b) if len(order) > 1 else None
        if L is None and len(order) > 1: route_ok = False
        legs.append(dict(frm=a["name"], to=b["name"], minutes=(L or {}).get("minutes"), km=(L or {}).get("km"),
                         coords=(L or {}).get("coords") or [[a["lat"], a["lon"]], [b["lat"], b["lon"]]]))
    stops = []
    for k, s in enumerate(ev["stop_detail"], 1):
        row = by_name[s["name"]]
        cat = [by_name[n] for n in s["catchment"]]
        wsum = sum(r["pop"] for r in cat) or 1
        tt = row["tt_ct"]
        seen = stop_seen[code].get(s["name"], 0)
        dmin, dmax = min(stop_days[code].get(s["name"], [0])), max(stop_days[code].get(s["name"], [0]))
        kind = "ct_town" if tt < 15 else ("far" if tt >= T_FAR else "mid")
        flags = []
        if kind == "ct_town": flags.append("capacity_assumption")
        if town_status(row["ct_town"]) != "confirmed": flags.append("ct_unconfirmed")
        if seen / N < 0.9: flags.append("unstable")
        stops.append(dict(
            n=k, name=s["name"], lat=row["lat"], lon=row["lon"], days=round(s["days"], 1), scans=round(s["scans"]), additional=round(s["additional"]),
            catchment=s["catchment"], catchment_eligible=round(sum(r["elig"] for r in cat)), catchment_share_of_county=round(sum(r["elig"] for r in cat) / elig_c, 3),
            nearest_ct=row["ct_town"], tt_ct_min=round(tt), ct_status=town_status(row["ct_town"]), kind=kind,
            foreign_share=round(sum(r["f"] * r["pop"] for r in cat) / wsum, 3),
            basic_share=round(sum((edu.get(r["code"]) or edu_mean) * r["pop"] for r in cat) / wsum, 3),
            stability=dict(share=round(seen / N, 2), days_min=round(dmin, 1), days_max=round(dmax, 1)), flags=flags))
    elig_far = sum(s["catchment_eligible"] for s in stops if s["kind"] == "far")
    for r in mem:
        c = muni_csv[r["code"]]; pov, med = inc.get(r["code"], (None, None))
        near_ct = r["tt_ct"] <= T_HOSP
        bus = r["i"] in assigned
        cls = "hospital" if near_ct else ("bus" if bus else "none")      # exclusive: within T_HOSP minutes of a CT town = hospital pilot area; beyond it = bus area
        muni_out.append(dict(
            code=r["code"], name=r["name"], county=code, lat=r["lat"], lon=r["lon"], pop_all=int(c["pop_all"]), pop_50_74=r["pop"], eligible=round(r["elig"]),
            foreign_share=round(r["f"], 3), sparse_share=num(c["sparse_share"]), basic_share=edu.get(r["code"]), poverty_rate=pov, median_income=med,
            nearest_ct=r["ct_town"], tt_ct_min=round(r["tt_ct"]), ct_status=town_status(r["ct_town"]), cls=cls,
            bus_relief=bool(near_ct and bus), bus_stop=assigned.get(r["i"], (None, 0))[0], bus_additional=round(assigned.get(r["i"], (None, 0))[1], 1)))
    cm = [m for m in muni_out if m["county"] == code]
    lung = {s: next(x for x in reg_rows if x["area"] == meta0["registry"] and x["sex"] == s) for s in ("Miehet", "Naiset")}
    ow = [x for x in wait_rows if x["area"] == meta0["registry"]]
    ic = ind[code]
    ct_here = [x for x in ct_rows if x["county"].split(" (")[0] == meta0["ct_county"]]
    towns = sorted({x["municipality"] for x in ct_here})
    counties_out[code] = dict(
        code=code, names={k: meta0[k] for k in ("fi", "sv", "en")},
        facts=dict(pop_all=int(ic["pop_all"]), pop_50_74=int(ic["pop_50_74"]), lung_deaths_per_year=num(ic["lung_deaths_mean_2021_2025"]),
                   lung_deaths_per100k_crude=num(ic["lung_deaths_per_100k_crude"]), smoking_20_64=num(ic["smoking_20_64_pct"]), smoking_65plus=num(ic["smoking_65plus_pct"]),
                   smr=dict(deaths=sm["deaths"], expected=sm["expected"], smr=sm["smr"], lo=sm["lo"], hi=sm["hi"], rank=sm["rank"]),
                   lung_asr=dict(men=num(lung["Miehet"]["asr_lung_per100k_finland2014"]), women=num(lung["Naiset"]["asr_lung_per100k_finland2014"])),
                   lung_cases_2020_24=int(lung["Miehet"]["new_cases_lung_2020_2024"]) + int(lung["Naiset"]["new_cases_lung_2020_2024"]),
                   basic_share_55_74=round(sum((edu.get(r["code"]) or edu_mean) * edu_n.get(r["code"], 0) for r in mem) / max(1, sum(edu_n.get(r["code"], 0) for r in mem)), 3),
                   oncology_waits=[dict(year=x["year"], assess_over90=num(x["assess_pct_over90d"]), assess_months=int(x["assess_months_reported"]),
                                        treat_over90=num(x["treat_pct_over90d"]), treat_months=int(x["treat_months_reported"])) for x in ow]),
        model=dict(eligible=round(elig_c), annual_need=round(cinfo["annual_need"]), spare_scans=round(cinfo["spare"]), coverage_fixed=cinfo["coverage_fixed"],
                   coverage_with_bus=reach["coverage_with_truck"], ct_towns=cinfo["ct_towns"]),
        hospital=dict(
            towns=[dict(town=t, status=town_status(t), lat=by_name[t]["lat"], lon=by_name[t]["lon"],
                        sites=[dict(facility=x["facility"], type=x["facility_type"], status=x["ct_status"], scanners=(int(x["n_scanners"]) if x["n_scanners"] else None),
                                    evidence=x["evidence"], url=x["source_url"], date=x["source_date"] or None, note=x["notes"] or None) for x in ct_here if x["municipality"] == t],
                        invite_municipalities=[m["name"] for m in cm if m["nearest_ct"] == t and m["tt_ct_min"] <= T_HOSP],
                        invite_eligible=sum(m["eligible"] for m in cm if m["nearest_ct"] == t and m["tt_ct_min"] <= T_HOSP)) for t in towns if t in by_name],
            invite_eligible=sum(m["eligible"] for m in cm if m["tt_ct_min"] <= T_HOSP), beyond_eligible=sum(m["eligible"] for m in cm if m["tt_ct_min"] > T_HOSP)),
        bus=dict(stops=stops, order=order, legs=legs, route_from_osrm=route_ok, km_per_year=round(sum((l["km"] or 0) for l in legs) * prm["cycles"]),
                 working_days=round(ev["total_days"], 1), scans=round(ev["scans"]), additional=round(ev["additional"]), additional_far=round(ev["add_far"]),
                 eligible_in_far_catchments=elig_far, cost_per_additional_eur=round(w.cost(ev, cen)["per_additional"]),
                 days_in_ct_towns=round(sum(s["days"] for s in stops if s["kind"] == "ct_town"), 1), days_total_scanning=round(sum(s["days"] for s in stops), 1)),
        stability=dict(scenarios=N))
    print(meta0["en"], "| stops", len(stops), "| far stops", sum(1 for s in stops if s["kind"] == "far"), "| route from OSRM:", route_ok, "| additional", round(ev["additional"]))

json.dump(leg_cache, open(LEG_CACHE, "w", encoding="utf-8"), separators=(",", ":"))

# ---- v1 comparison (engine as audited: straight line x 1.3, crude mortality weight) ----------------------------------------------
v1 = {}
all_rows = R.load()
scn1 = {"objective": "weighted", "risk_model": "area", "ct_sites": "confirmed+likely", "routing": {"lam": 0.5}}
prm1, _, cen1 = S.setup(scn1)
w1 = R.World(all_rows, prm1, S.fixed_names(scn1), area=S.area_hook(scn1, prm1))
for code in PRIORITY:
    reg1 = {r["name"] for r in all_rows if r.get("county") == code}
    e1 = w1.evaluate(w1.optimise(reg1, "weighted"))
    v1[code] = dict(additional=round(e1["additional"]), days=round(e1["total_days"], 1), stops=[[s["name"], round(s["days"], 1), round(s["additional"])] for s in e1["stop_detail"]])

# ---- factor correlations (all municipalities) ----------------------------------------------------------------------------------------
cols = {"basic_share": [], "poverty": [], "median_income": [], "foreign_share": [], "sparse_share": []}
for code, m in muni_csv.items():
    pov, med = inc.get(code, (None, None)); e = edu.get(code)
    if None in (pov, med, e): continue
    for k, v in zip(cols, (e, pov, med, float(m["foreign_lang_share"] or 0), float(m["sparse_share"] or 0))): cols[k].append(v)
cor = {f"{a}|{b}": round(corr(rank(cols[a]), rank(cols[b])), 2) for a, b in itertools.combinations(cols, 2)}

# ---- write ----------------------------------------------------------------------------------------------------------------------
prm_show = {k: prm[k] for k in ("k_elig", "ct_per_1000", "spare_share", "wait0", "u0", "d0_fixed", "d0_mobile", "pool_km", "lam", "eligible_share", "work_days", "interval",
                                 "minority_factor_fixed", "minority_factor_mobile", "cycles", "setup_days") if k in prm}
nat_lung = {s: next(x for x in reg_rows if x["area"] == "Koko maa" and x["sex"] == s) for s in ("Miehet", "Naiset")}
meta = dict(
    generated=date.today().isoformat(), builder="ct-sim/docs/analysis/build_pilot_map_data.py", priority=list(PRIORITY), version=2,
    sources={k: dict(path=str(Path(p).relative_to(REPO)), sha256=sha(p)) for k, p in F.items()},
    planner_assumptions=prm_show, weights=dict(BASE, smr_cap=list(SMR_CAP), education_mean=round(edu_mean, 3), education_sd=round(edu_sd, 3)),
    thresholds=dict(hospital_invite_min=T_HOSP, far_stop_min=T_FAR),
    ct_sites_total=len(ct_rows), ct_towns_total=len(fixed), ct_sites_with_scanner_count=sum(1 for x in ct_rows if x["n_scanners"]), ct_waits_known=len(ct_wait_known),
    national_lung_asr=dict(men=num(nat_lung["Miehet"]["asr_lung_per100k_finland2014"]), women=num(nat_lung["Naiset"]["asr_lung_per100k_finland2014"])),
    national_foreign_share_50_74=round(nat_f, 3), national_basic_share_55_74=round(edu_mean, 3),
    travel=dict(source=tm["source"], fetched=tm["fetched"], limits=tm["limits"]),
    limits=["Hospital CT capacity is not verified for any site; free capacity is an assumption applied county-wide",
            "Eligible people are modelled from smoking rates and an assumed factor (no pack-year data), age band 50-74",
            "Lung mortality is known by wellbeing county only, not by municipality",
            "Settlement points are the main town of each municipality, not exact home locations; Hamina, Huittinen and Simo use centroids",
            "Waiting times for CT are not available by county; oncology queue data is a different measure"],
    risk_group=dict(age="50-74", pack_years=">=20", quit_years="<=15"))
ctt = [dict(town=rows[j]["name"], lat=rows[j]["lat"], lon=rows[j]["lon"], status=town_status(rows[j]["name"]), county=rows[j].get("county")) for j in fixed_idx]
pub = dict(meta=meta, counties=counties_out, municipalities=muni_out, ct_towns=sorted(ctt, key=lambda x: x["town"]))
(REPO / "map/pilot_map.json").write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
(REPO / "map/private").mkdir(parents=True, exist_ok=True)
adv = dict(generated=meta["generated"], grid=GRID, base=BASE, scenarios=grid_out, engine_v1=v1, correlations_spearman_municipalities=cor, n_municipalities_corr=len(cols["basic_share"]))
(REPO / "map/private/pilot_map_advanced.json").write_text(json.dumps(adv, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("wrote pilot_map.json", (REPO / "map/pilot_map.json").stat().st_size, "bytes; advanced", (REPO / "map/private/pilot_map_advanced.json").stat().st_size, "bytes;", N, "scenarios")
