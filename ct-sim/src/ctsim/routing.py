"""Route/stop optimisation for ONE mobile LDCT unit in Finland (design test-bed, not a deployable planner).

REAL inputs : municipality centroids (Statistics Finland geoserver), population 50-74 (table 11re),
              foreign-language share (11rm, ALL ages - proxy for the 50-74 group), sparsely populated share (15k6),
              uptake ratio of 'other/missing native language' vs domestic in 2024 screening (Cancer Registry):
              breast 60.8/83.2=0.73, colorectal 53.4/74.5=0.72, cervical 56.3/76.2=0.74.
ASSUMED     : fixed-site CT towns (placeholder list), distance decay of uptake, uniform eligibility share,
              road km = 1.3 x straight line, 60 km/h, mobile-outreach minority factor. All are parameters and stress-tested.
Objective   : maximise equity-weighted ADDITIONAL participants/year (people not screened at a fixed site) subject to working days.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

from . import model as M
from . import paths

# PLACEHOLDER: towns with a hospital that plausibly has CT. REPLACE with a sourced THL/Hilmo/county list.
FIXED_SITE_NAMES = ["Helsinki", "Espoo", "Vantaa", "Tampere", "Turku", "Oulu", "Kuopio", "Jyväskylä", "Lahti", "Vaasa",
                    "Seinäjoki", "Pori", "Kouvola", "Lappeenranta", "Joensuu", "Kajaani", "Rovaniemi", "Kemi", "Kokkola",
                    "Mikkeli", "Hämeenlinna", "Savonlinna", "Hyvinkää", "Porvoo", "Lohja", "Iisalmi", "Varkaus", "Kotka",
                    "Salo", "Rauma", "Raahe", "Kuusamo", "Ylivieska", "Jämsä", "Kemijärvi", "Sotkamo", "Pietarsaari"]

DEFAULT = dict(eligible_share=0.07, interval=2.0, u0=0.50, d0_fixed=120.0, d0_mobile=25.0,
               minority_factor_fixed=0.73, minority_factor_mobile=0.90, detour=1.3, speed_kmh=60.0, driving_h=8.0,
               work_days=200, setup_days=0.5, cycles=2, pool_km=60.0, spd=16.9, lam=0.5, chunk=2.0,
               campaign_intensity=0.0, triage=0.6, priority_eligible=True, risk_gamma=1.0)   # campaign and risk levers (area model)


def load(path: Path | str | None = None) -> list[dict]:
    rows = []
    with open(path or paths.MUNICIPALITIES_CSV, encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f)):
            rows.append(dict(i=i, code=r["code"], name=r["name"], x=float(r["x_epsg3067"]), y=float(r["y_epsg3067"]),
                             lat=float(r["lat"]) if r.get("lat") else None, lon=float(r["lon"]) if r.get("lon") else None,
                             pop=int(r["pop_50_74"]), f=float(r["foreign_lang_share"] or 0),
                             p5064=int(r["pop_50_64"]) if r.get("pop_50_64") else None, p6574=int(r["pop_65_74"]) if r.get("pop_65_74") else None))
    return rows


class World:
    def __init__(self, rows: list[dict], prm: dict, fixed_names: list[str] | None = None, D: list[list[float]] | None = None, area=None):
        fixed_names = FIXED_SITE_NAMES if fixed_names is None else fixed_names
        self.rows, self.prm = rows, prm
        self.u0 = min(0.95, prm["u0"] * (1 + prm.get("campaign_boost", 0.0)))   # a campaign raises uptake for everyone, fixed site or truck
        n = len(rows)
        k = prm["detour"] / 1000
        # D can be passed in to reuse distances across many Worlds (same rows, same detour); rows themselves must be copied per World
        self.D = D if D is not None else [[math.hypot(a["x"] - b["x"], a["y"] - b["y"]) * k for b in rows] for a in rows]
        fixed = [r["i"] for r in rows if r["name"] in fixed_names]
        for r in rows:
            r["d_fixed"] = min(self.D[r["i"]][j] for j in fixed) if fixed else 1e9
            r["elig"] = r["pop"] * prm["eligible_share"]
            r["u_fixed"] = self.u0 * math.exp(-r["d_fixed"] / prm["d0_fixed"]) * (1 - r["f"] * (1 - prm["minority_factor_fixed"]))
            r["w"] = 1 + prm["lam"] * min(r["f"] / 0.10, 3.0)
        self.area_info = area(rows, prm) if area else None      # may replace eligible counts, weights and fixed-site uptake
        self.pool = {}   # candidate stop -> [(muni idx, mobile uptake)] where mobile uptake beats fixed-site uptake
        for s in range(n):
            pl = []
            for m in range(n):
                d = self.D[m][s]
                if d <= prm["pool_km"]:
                    u = self.u0 * math.exp(-d / prm["d0_mobile"]) * (1 - rows[m]["f"] * (1 - prm["minority_factor_mobile"]))
                    if u > rows[m]["u_fixed"]:
                        pl.append((m, u))
            self.pool[s] = pl

    def tour(self, idxs: list[int]):
        """closed tour length (km) and order via nearest neighbour + 2-opt"""
        if len(idxs) < 2:
            return 0.0, list(idxs)
        D = self.D
        order = [idxs[0]]
        left = set(idxs[1:])
        while left:
            nx = min(left, key=lambda j: D[order[-1]][j])
            order.append(nx)
            left.remove(nx)
        if len(order) > 3:
            imp = True
            while imp:
                imp = False
                for i in range(1, len(order) - 1):
                    for j in range(i + 1, len(order)):
                        a, b, c, d = order[i - 1], order[i], order[j], order[(j + 1) % len(order)]
                        if D[a][c] + D[b][d] + 1e-9 < D[a][b] + D[c][d]:
                            order[i:j + 1] = reversed(order[i:j + 1])
                            imp = True
        return sum(D[order[i]][order[(i + 1) % len(order)]] for i in range(len(order))), order

    def optimise(self, region: set[str] | None = None, objective: str = "weighted") -> dict[int, float]:
        prm, rows = self.prm, self.rows
        cand = [r["i"] for r in rows if region is None or r["name"] in region]
        inreg = set(cand)
        rem = {m: 1.0 for m in inreg}
        plan: dict[int, float] = {}
        order: list[int] = []
        used = 0.0
        spd = prm["spd"]
        while True:
            best = None
            for s in cand:
                pl = [(m, u) for m, u in self.pool[s] if m in inreg and rem[m] > 1e-9]
                if not pl:
                    continue
                arr = sum(rows[m]["elig"] * u / prm["interval"] * rem[m] for m, u in pl)
                if arr <= 0:
                    continue
                if objective == "scans":
                    g = 1.0
                else:
                    wt = (lambda m: rows[m]["w"]) if objective == "weighted" else (lambda m: 1.0)
                    g = sum(rows[m]["elig"] * (u - rows[m]["u_fixed"]) / prm["interval"] * rem[m] * wt(m) for m, u in pl) / arr
                usable = min(prm["chunk"], arr / spd)
                new = s not in plan
                extra_km = 0.0
                if new and order:
                    if len(order) == 1:
                        extra_km = 2 * self.D[order[0]][s] * prm["cycles"]
                    else:
                        extra_km = min(self.D[order[k]][s] + self.D[s][order[(k + 1) % len(order)]] - self.D[order[k]][order[(k + 1) % len(order)]]
                                       for k in range(len(order))) * prm["cycles"]
                cost_days = usable + (prm["cycles"] * prm["setup_days"] if new else 0) + extra_km / (prm["speed_kmh"] * prm["driving_h"])
                score = g * usable * spd / cost_days
                if best is None or score > best[0]:
                    best = (score, s, usable, cost_days, pl, arr, extra_km)
            if best is None:
                break
            score, s, usable, cost_days, pl, arr, ek = best
            if used + cost_days > prm["work_days"]:
                break
            if s not in plan:
                plan[s] = 0.0
                if len(order) < 2:
                    order.append(s)
                else:
                    k = min(range(len(order)), key=lambda k: self.D[order[k]][s] + self.D[s][order[(k + 1) % len(order)]] - self.D[order[k]][order[(k + 1) % len(order)]])
                    order.insert(k + 1, s)
            plan[s] += usable
            used += cost_days
            fr = min(1.0, usable * spd / arr)
            for m, u in pl:
                rem[m] *= (1 - fr)
        return plan

    def evaluate(self, plan: dict[int, float]) -> dict:
        prm, rows = self.prm, self.rows
        spd = prm["spd"]
        stops = [s for s, d in plan.items() if d > 0]
        load = {s: [] for s in stops}
        for m in range(len(rows)):
            best = None
            for s in stops:
                d = self.D[m][s]
                if d <= prm["pool_km"]:
                    u = self.u0 * math.exp(-d / prm["d0_mobile"]) * (1 - rows[m]["f"] * (1 - prm["minority_factor_mobile"]))
                    if best is None or u > best[0]:
                        best = (u, s)
            if best and best[0] > rows[m]["u_fixed"]:
                load[best[1]].append((m, best[0]))
        add = addw = addmin = addfar = scans = 0.0
        stop_rows = []
        muni = {}   # municipality index -> (stop name, additional participants per year)
        for s in stops:
            dem = sum(rows[m]["elig"] * u / prm["interval"] for m, u in load[s])
            cap = plan[s] * spd
            fr = min(1.0, cap / dem) if dem > 0 else 0
            s_add = s_scans = 0.0
            for m, u in load[s]:
                ex = rows[m]["elig"] * (u - rows[m]["u_fixed"]) / prm["interval"] * fr
                add += ex; addw += ex * rows[m]["w"]; addmin += ex * rows[m]["f"]
                if rows[m]["d_fixed"] > 60:
                    addfar += ex
                sc = rows[m]["elig"] * u / prm["interval"] * fr
                scans += sc; s_add += ex; s_scans += sc
                muni[m] = (rows[s]["name"], ex)
            stop_rows.append(dict(name=rows[s]["name"], code=rows[s]["code"], lat=rows[s]["lat"], lon=rows[s]["lon"],
                                  days=plan[s], scans=s_scans, additional=s_add, catchment=[rows[m]["name"] for m, _ in load[s]]))
        km, order = self.tour(stops)
        km *= prm["cycles"]
        scan_days = sum(plan[s] for s in stops)
        other = len(stops) * prm["cycles"] * prm["setup_days"] + km / (prm["speed_kmh"] * prm["driving_h"])
        by_idx = {rows[s]["name"]: sr for s, sr in zip(stops, stop_rows)}
        ev = dict(stops=len(stops), scans=scans, additional=add, weighted=addw, add_minority=addmin, add_far=addfar, km=km,
                  scan_days=scan_days, total_days=scan_days + other, order=[rows[s]["name"] for s in order],
                  stop_detail=[by_idx[rows[s]["name"]] for s in order], muni_additional=muni)
        ev.update(self.cost(ev))
        return ev

    def cost(self, ev: dict, model_params: dict | None = None) -> dict:
        p = model_params or M.central()
        base = M.unit(p)
        prm = self.prm
        fixed = base["fixed"] - p["km_per_year"] * p["eur_per_km"] - p["stops_per_year"] * p["cost_per_stop"] \
            + ev["km"] * p["eur_per_km"] + ev["stops"] * prm["cycles"] * p["cost_per_stop"]
        var = base["var"]
        total = fixed + ev["scans"] * var
        disp = (ev["scans"] - ev["additional"]) * (p["fixed_site_scan_cost"] + var)
        return dict(total=total, per_scan=total / ev["scans"] if ev["scans"] else float("nan"),
                    per_additional=(total - disp) / ev["additional"] if ev["additional"] else float("nan"))


def fmt(ev: dict) -> str:
    return (f"stops {ev['stops']:>2} | scans {ev['scans']:>5.0f} | additional {ev['additional']:>5.0f} ({100*ev['additional']/max(ev['scans'],1):>4.1f}%) "
            f"| >60km from CT {ev['add_far']:>5.0f} | km {ev['km']:>5.0f} | days {ev['total_days']:>5.1f} (scan {ev['scan_days']:>5.1f}) "
            f"| €/scan {ev['per_scan']:>4.0f} | €/additional {ev['per_additional']:>5.0f}")


def region(w: World, base: str, radius: float) -> set[str]:
    b = next(r for r in w.rows if r["name"] == base)
    return {r["name"] for r in w.rows if w.D[r["i"]][b["i"]] <= radius}


NATIONAL_SCENARIOS = [("A max scans (population-greedy)", "scans", 0.0), ("B max additional, no equity weight", "weighted", 0.0),
                      ("C max additional, equity weight 0.5", "weighted", 0.5), ("D max additional, equity weight 2.0", "weighted", 2.0)]
PILOTS = [("Helsinki metro (40km)", "Helsinki", 40), ("Kajaani 150km (Kainuu/N.Karelia)", "Kajaani", 150), ("Rovaniemi 150km (Lapland)", "Rovaniemi", 150),
          ("Seinäjoki 120km", "Seinäjoki", 120), ("Jyväskylä 120km", "Jyväskylä", 120), ("Tampere 100km", "Tampere", 100),
          ("Oulu 150km", "Oulu", 150), ("Kuopio 120km", "Kuopio", 120)]

PERTURBATIONS = [("d0_fixed=60", dict(d0_fixed=60)), ("d0_fixed=250", dict(d0_fixed=250)), ("d0_mobile=12", dict(d0_mobile=12)),
                 ("d0_mobile=50", dict(d0_mobile=50)), ("minority_mobile=0.80", dict(minority_factor_mobile=0.80)),
                 ("minority_mobile=1.0", dict(minority_factor_mobile=1.0)), ("eligible_share=0.04", dict(eligible_share=0.04)),
                 ("eligible_share=0.12", dict(eligible_share=0.12)), ("u0=0.3", dict(u0=0.3)), ("u0=0.72", dict(u0=0.72))]


def run_report(prm: dict | None = None, out_csv: Path | None = None, rows_path=None) -> list[list]:
    """Reproduce the national and pilot tables in the report; writes route_results.csv and returns the rows."""
    prm = dict(DEFAULT, **(prm or {}))
    out = []
    for label, obj, lam in NATIONAL_SCENARIOS:
        q = dict(prm, lam=lam)
        ww = World(load(rows_path), q)
        ev = ww.evaluate(ww.optimise(None, obj))
        out.append(["national", label, ev["stops"], round(ev["scans"]), round(ev["additional"]), round(ev["add_far"]), round(ev["km"]), round(ev["total_days"], 1), round(ev["per_scan"]), round(ev["per_additional"])])
    w = World(load(rows_path), prm)
    for label, base, rad in PILOTS:
        ev = w.evaluate(w.optimise(region(w, base, rad), "weighted"))
        out.append(["pilot", label, ev["stops"], round(ev["scans"]), round(ev["additional"]), round(ev["add_far"]), round(ev["km"]), round(ev["total_days"], 1), round(ev["per_scan"]), round(ev["per_additional"])])
    out_csv = Path(out_csv or paths.ROUTING / "route_results.csv")
    with open(out_csv, "w", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["scope", "scenario", "stops", "scans_per_year", "additional_participants_per_year", "additional_in_municipalities_over_60km_from_CT",
                     "km_per_year", "working_days_used", "cost_per_scan_eur", "cost_per_additional_participant_eur"])
        cw.writerows(out)
    return out


def sensitivity_table(prm: dict | None = None, rows_path=None) -> list[dict]:
    """Evaluate the central plan under perturbed assumptions vs the plan re-optimised for each."""
    prm = dict(DEFAULT, **(prm or {}))
    w = World(load(rows_path), prm)
    p1 = w.optimise(None, "weighted")
    central_names = {w.rows[s]["name"]: d for s, d in p1.items()}
    out = []
    for label, ch in PERTURBATIONS:
        q = dict(prm, **ch)
        ww = World(load(rows_path), q)
        idx = {r["name"]: r["i"] for r in ww.rows}
        e_c = ww.evaluate({idx[n]: d for n, d in central_names.items()})
        po = ww.optimise(None, "weighted")
        e_o = ww.evaluate(po)
        opt_names = {ww.rows[s]["name"] for s in po}
        jac = len(set(central_names) & opt_names) / len(set(central_names) | opt_names)
        out.append(dict(label=label, central_plan=e_c["additional"], reoptimised=e_o["additional"],
                        regret=1 - e_c["weighted"] / e_o["weighted"] if e_o["weighted"] else 0.0, jaccard=jac))
    return out
