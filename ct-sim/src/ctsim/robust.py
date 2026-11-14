"""Robustness sweep: how much of a route plan survives when the assumptions are wrong?

The route optimiser depends on assumptions we cannot yet measure (eligible share, uptake, distance decay, minority
uptake with outreach, and which towns really have CT capacity). This module draws many plausible worlds, re-optimises in
each, and reports:

  stability   how often each municipality is chosen as a stop / actually served across worlds
  plans       candidate plans (central-optimal, consensus plans, sampled world-optimal plans) scored by REGRET:
              regret = 1 - benefit(plan in world) / benefit(best plan for that world)
  voi         expected regret from not knowing one parameter at a time (value of information in % of benefit):
              which unknown a pilot should measure first

Benefit = equity-weighted additional participants per year (the optimiser's objective).

Parallelism: the worlds are independent. run() draws every world's parameters in the driver (so the random stream, and therefore the
result, is identical however the work is spread), then hands jobs [(kind, scn, chunk, extra), ...] to a `mapper(jobs)` that returns one
result per job, in order. Two rounds: (1) planning worlds and value-of-information worlds together, (2) validation worlds, which need
the candidate plans from round 1. Mappers: sequential (default), process_pool_mapper(workers) on this machine, and the Modal mapper in
api/modal_app.py. Workers run the pure functions in TASKS.
Assumption ranges below are the same planning ranges used elsewhere in the project; they are not estimates of Finnish reality.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from concurrent.futures import ProcessPoolExecutor

from . import routing as R
from . import scenario as S

# parameter -> (low, central, high); same ranges as routing.PERTURBATIONS
UNCERTAIN = {
    "eligible_share": (0.04, 0.07, 0.12),
    "u0": (0.30, 0.50, 0.72),
    "d0_fixed": (60.0, 120.0, 250.0),
    "d0_mobile": (12.0, 25.0, 50.0),
    "minority_factor_mobile": (0.80, 0.90, 1.00),
    # area model (no effect when a scenario asks for risk_model 'uniform')
    "k_elig": (0.55, 0.80, 1.10),
    "ct_per_1000": (35.0, 60.0, 90.0),
    "spare_share": (0.02, 0.05, 0.10),
    "spill_per_int": (0.01, 0.03, 0.08),
}
SITE_DROPOUT = 0.15      # each world, a random 15% of the placeholder CT towns are assumed to have no usable capacity


def _pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))]


def _draw(rng, base, only=None):
    prm = dict(base)
    for k, (lo, mid, hi) in UNCERTAIN.items():
        if only is None or only == k:
            prm[k] = rng.triangular(lo, hi, mid)
    return prm


def _sites(rng, names, dropout, active=True):
    if not active:
        return list(names)
    keep = [n for n in names if rng.random() >= dropout]
    return keep or list(names)


_SWEEPS: dict = {}


def _sweep(scn: dict) -> "_Sweep":
    """One _Sweep per scenario per process (loading rows and distances costs ~0.1 s; workers handle many chunks)."""
    key = json.dumps(scn, sort_keys=True)
    if key not in _SWEEPS:
        if len(_SWEEPS) > 4:
            _SWEEPS.clear()
        _SWEEPS[key] = _Sweep(scn, 0)
    return _SWEEPS[key]


class _Sweep:
    def __init__(self, scn: dict, seed: int):
        self.scn = scn
        self.base, _, _ = S.setup(scn)
        self.rows0 = R.load()
        self.fixed0 = S.fixed_names(scn)
        self.objective = scn.get("objective", "weighted")
        self.rng = random.Random(seed)
        w0 = R.World([dict(r) for r in self.rows0], self.base, self.fixed0)
        self.D = w0.D
        self.region = R.region(w0, scn["region"]["base"], scn["region"]["radius_km"]) if scn.get("region") else None

    def world(self, prm, fixed):
        return R.World([dict(r) for r in self.rows0], prm, fixed, D=self.D, area=S.area_hook(self.scn, prm))

    def optimal(self, w):
        plan = w.optimise(self.region, self.objective)
        return plan, w.evaluate(plan)


def _fit_budget(w, plan, budget):
    """Drop the lowest-days stops until the plan fits the working-day budget in this world."""
    plan = {k: v for k, v in plan.items() if v > 0}
    while plan and w.evaluate(plan)["total_days"] > budget + 1e-9:
        plan.pop(min(plan, key=plan.get))
    return plan


# ------------------------------------------------------------------------------------------------ worker tasks (pure)
def _task_plan(scn: dict, specs: list[dict], extra=None) -> list[dict]:
    """Optimal plan in each world: {plan, weighted, additional, muni (index -> additional participants)}."""
    sw = _sweep(scn)
    out = []
    for sp in specs:
        plan, ev = sw.optimal(sw.world(sp["prm"], sp["fixed"]))
        out.append(dict(plan=plan, weighted=ev["weighted"], additional=ev["additional"], muni={i: a for i, (_, a) in ev["muni_additional"].items()}))
    return out


def _task_validate(scn: dict, specs: list[dict], cands: dict) -> list[dict]:
    """In each validation world: the heuristic optimum and every candidate plan's (weighted, additional)."""
    sw = _sweep(scn)
    out = []
    for sp in specs:
        w = sw.world(sp["prm"], sp["fixed"])
        opt = sw.optimal(w)[1]["weighted"]
        ben = {}
        for name, plan in cands.items():
            e = w.evaluate(plan)
            ben[name] = (e["weighted"], e["additional"])
        out.append(dict(opt=opt, ben=ben))
    return out


def _task_voi(scn: dict, specs: list[dict], central_plan: dict) -> list[tuple]:
    """(heuristic optimum, central plan benefit) in each world."""
    sw = _sweep(scn)
    out = []
    for sp in specs:
        w = sw.world(sp["prm"], sp["fixed"])
        out.append((sw.optimal(w)[1]["weighted"], w.evaluate(central_plan)["weighted"]))
    return out


TASKS = {"plan": _task_plan, "validate": _task_validate, "voi": _task_voi}


# ------------------------------------------------------------------------------------------------ mappers
def sequential_mapper(jobs: list) -> list:
    """jobs = [(kind, scn, chunk, extra), ...]; returns one result per job, in order."""
    return [TASKS[kind](scn, chunk, extra) for kind, scn, chunk, extra in jobs]


def _pool_call(job):
    kind, scn, chunk, extra = job
    return TASKS[kind](scn, chunk, extra)


def process_pool_mapper(workers: int | None = None):
    """Mapper that spreads jobs over local processes. Same results as the sequential mapper."""
    def mapper(jobs):
        with ProcessPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(_pool_call, jobs))
    return mapper


def _chunks(items: list, size: int) -> list:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _flat(results: list) -> list:
    return [x for part in results for x in part]


# ------------------------------------------------------------------------------------------------ driver
def run(scn: dict, n: int = 100, seed: int = 1, n_sampled_plans: int = 8, voi_n: int = 30, site_dropout: float = SITE_DROPOUT,
        mapper=None, chunk: int = 8) -> dict:
    mapper = mapper or sequential_mapper
    sw = _Sweep(scn, seed)
    base, rng = sw.base, sw.rng
    budget = base["work_days"]
    rows = sw.rows0

    # 0. draw EVERY world here, in the original order (planning, sample indices, validation, VOI), so results do not depend on the split
    plan_specs = []
    for _ in range(n):
        prm = _draw(rng, base)
        plan_specs.append(dict(prm=prm, fixed=_sites(rng, sw.fixed0, site_dropout)))
    sample_idx = rng.sample(range(n), min(n_sampled_plans, n))
    n_val = max(20, n // 2)
    val_specs = []
    for _ in range(n_val):
        prm = _draw(rng, base)
        val_specs.append(dict(prm=prm, fixed=_sites(rng, sw.fixed0, site_dropout)))
    params = list(UNCERTAIN) + ["ct_sites"]
    voi_specs = []
    for param in params:
        for _ in range(voi_n):
            prm = _draw(rng, base, only=None if param == "ct_sites" else param)
            if param == "ct_sites":
                prm = dict(base)
            voi_specs.append(dict(prm=prm, fixed=_sites(rng, sw.fixed0, site_dropout, active=(param == "ct_sites"))))

    # 1. round one: optimal plans in the planning worlds AND the VOI worlds (the VOI needs only the central plan), in one mapper call
    wc = sw.world(base, sw.fixed0)
    central_plan, _ = sw.optimal(wc)
    plan_jobs = [("plan", scn, c, None) for c in _chunks(plan_specs, chunk)]
    voi_jobs = [("voi", scn, c, central_plan) for c in _chunks(voi_specs, chunk)]
    out = mapper(plan_jobs + voi_jobs)
    planned = _flat(out[:len(plan_jobs)])
    voi_res = _flat(out[len(plan_jobs):])
    optimal_plans = [p["plan"] for p in planned]

    # 2. stability map
    sel = [0] * len(rows); served = [0] * len(rows); add = [0.0] * len(rows)
    for p in planned:
        for i, d in p["plan"].items():
            if d > 0:
                sel[i] += 1
        for i, a in p["muni"].items():
            if a > 0:
                served[i] += 1; add[i] += a
    stability = [dict(code=r["code"], name=r["name"], lat=r["lat"], lon=r["lon"], pop=r["pop"],
                      select_freq=round(sel[i] / n, 3), served_freq=round(served[i] / n, 3), mean_additional=round(add[i] / n, 1))
                 for i, r in enumerate(rows) if (sel[i] or served[i]) and (sw.region is None or r["name"] in sw.region)]
    stability.sort(key=lambda m: -m["select_freq"])

    # 3. candidate plans
    mean_days = [sum(p.get(i, 0.0) for p in optimal_plans) / n for i in range(len(rows))]
    cands = {"central-optimal": central_plan}
    for tau in (0.3, 0.5, 0.7):
        keep = {i: mean_days[i] / max(sel[i] / n, 1e-9) for i in range(len(rows)) if sel[i] / n >= tau}   # mean days when selected
        cands[f"consensus >= {int(tau*100)}%"] = _fit_budget(wc, keep, budget)
    for j in sample_idx:
        cands[f"world-optimal #{j}"] = optimal_plans[j]
    cands = {k: v for k, v in cands.items() if v}

    # 4. regret of each candidate on INDEPENDENT validation worlds (not used to build any plan)
    val = _flat(mapper([("validate", scn, c, cands) for c in _chunks(val_specs, chunk)]))
    # reference = best plan found in that world (heuristic optimum or any candidate), so regret is never negative
    ref = [max(v["opt"], max(v["ben"][name][0] for name in cands)) for v in val]
    plan_rows = []
    for name, plan in cands.items():
        regs = [1 - val[k]["ben"][name][0] / ref[k] if ref[k] > 0 else 0.0 for k in range(n_val)]
        adds = [val[k]["ben"][name][1] for k in range(n_val)]
        evc_ = wc.evaluate(plan)
        plan_rows.append(dict(name=name, stops=len([d for d in plan.values() if d > 0]),
                              mean_regret=statistics.fmean(regs), p90_regret=_pct(regs, .9), max_regret=max(regs),
                              additional_p5=_pct(adds, .05), additional_p50=_pct(adds, .5), additional_p95=_pct(adds, .95),
                              central_world_additional=evc_["additional"], km=evc_["km"], days=evc_["total_days"],
                              per_additional_eur=evc_["per_additional"]))
    plan_rows.sort(key=lambda r: (r["p90_regret"], r["mean_regret"]))
    best = plan_rows[0]["name"]
    evb = wc.evaluate(cands[best])
    evc = wc.evaluate(central_plan)

    # 5. value of information (worlds were evaluated in round one)
    voi = []
    for pi, param in enumerate(params):
        regs = []
        for opt, b in voi_res[pi * voi_n:(pi + 1) * voi_n]:
            top = max(opt, b)
            regs.append(1 - b / top if top > 0 else 0.0)
        voi.append(dict(param=param, expected_regret_pct=100 * statistics.fmean(regs), p90_regret_pct=100 * _pct(regs, .9)))
    voi.sort(key=lambda v: -v["expected_regret_pct"])

    def stops_of(ev):
        return [dict(name=s["name"], lat=s["lat"], lon=s["lon"], days=s["days"], scans=s["scans"], additional=s["additional"]) for s in ev["stop_detail"]]

    return dict(
        scenario=scn, n=n, seed=seed, site_dropout=site_dropout, uncertain=UNCERTAIN,
        n_validation=n_val, stability=stability, plans=plan_rows, recommended=best,
        recommended_plan=dict(order=evb["order"], stops=stops_of(evb), km=evb["km"], days=evb["total_days"], additional=evb["additional"], scans=evb["scans"]),
        central_plan=dict(order=evc["order"], stops=stops_of(evc), km=evc["km"], days=evc["total_days"], additional=evc["additional"], scans=evc["scans"]),
        voi=voi,
        optimal_benefit=dict(p5=_pct([p["additional"] for p in planned], .05), p50=_pct([p["additional"] for p in planned], .5), p95=_pct([p["additional"] for p in planned], .95)),
        notes=["Regret = 1 - benefit / benefit of the best plan found for that world (benefit = equity-weighted additional participants), measured on independent validation worlds that were not used to build any plan.",
               "Worlds vary eligible share, uptake, distance decay, minority uptake with outreach, and drop 15% of the placeholder CT towns.",
               "These ranges are planning ranges, not estimates of Finnish reality. VOI shows what a pilot should measure first, not true values."],
    )
