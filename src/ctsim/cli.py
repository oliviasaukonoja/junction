"""Command line: python -m ctsim <command>   (run from the ct-sim folder with PYTHONPATH=src, or pip install -e .)"""
from __future__ import annotations

import argparse
import json
import sys
import unittest

from . import analyst, areadata, ctsites, pilot, gap, readout as readout_mod, fetch, model, paths, robust, routing, scenario, screening


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ctsim", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download public inputs from Statistics Finland and rebuild the municipality table")
    sub.add_parser("build", help="rebuild municipality table from data/raw without downloading")
    s = sub.add_parser("screening", help="download Cancer Registry screening tables and extract CSVs")
    s.add_argument("--programmes", nargs="*", default=list(screening.PROGRAMMES))
    m = sub.add_parser("model", help="run cost/outcome model; writes data/model/*.csv")
    m.add_argument("--n", type=int, default=20_000)
    sub.add_parser("counties", help="merge screening participation by county for 2024 (needs data/screening)")
    sub.add_parser("sensitivity", help="regret of the central plan under perturbed assumptions; writes data/routing/sensitivity.csv")
    rb = sub.add_parser("robust", help="robustness sweep: stability map, plan regret, value of information; writes data/robust/*.csv")
    rb.add_argument("file", help="scenario JSON")
    rb.add_argument("--n", type=int, default=100)
    rb.add_argument("--seed", type=int, default=1)
    rb.add_argument("--workers", type=int, default=1, help="local processes for the sweep (same result as 1); for containers use modal run api/modal_app.py::robust_bench")
    rb.add_argument("--chunk", type=int, default=8, help="worlds per work unit")
    sub.add_parser("ctsites", help="compile data/ct_sites/raw_group*.csv into ct_sites.csv and report unmatched municipalities")
    ak = sub.add_parser("ask", help="ask the Claude analyst a question (needs `pip install anthropic` and ANTHROPIC_API_KEY)")
    ak.add_argument("question")
    ak.add_argument("--replay", action="store_true", help="use a recorded answer if one exists (CTSIM_ANALYST_RECORD=1 records)")
    rd = sub.add_parser("readout", help="rule-based two-minute summary of a scenario file (no API key, no AI)")
    rd.add_argument("file")
    sub.add_parser("gap", help="build data/gap/gapdata.json for the gap-finder page")
    pl = sub.add_parser("pilot", help="size the randomised-invitation pilot and show contamination and before/after bias")
    pl.add_argument("--p-a", type=float, default=0.40, help="uptake in the control arm (existing hospital CT)")
    pl.add_argument("--delta", type=float, default=0.15, help="uptake uplift from the mobile offer to detect")
    pl.add_argument("--power", type=float, default=0.80)
    pl.add_argument("--campaign-boost", type=float, default=0.30, help="relative uptake rise from a campaign, for the before/after comparison")
    sub.add_parser("area", help="refresh verified county data (lung deaths, smoking, CT exams) into data/area")
    sub.add_parser("routes", help="reproduce national and pilot route tables; writes data/routing/route_results.csv")
    sc = sub.add_parser("scenario", help="run a scenario JSON file and print the result JSON")
    sc.add_argument("file")
    sv = sub.add_parser("serve", help="local development server")
    sv.add_argument("--port", type=int, default=8000)
    sub.add_parser("tests", help="run the test suite")
    a = ap.parse_args(argv)

    if a.cmd == "fetch":
        print(json.dumps(fetch.fetch_all(), indent=2))
        print(fetch.build())
    elif a.cmd == "build":
        print(fetch.build())
    elif a.cmd == "screening":
        print(screening.fetch_all(programmes=a.programmes))
    elif a.cmd == "model":
        r = model.write_outputs(n=a.n)
        u, n = r["unit"], r["national"]
        print(f"one unit: {u['scans']:.0f} scans/yr, fixed €{u['fixed']:,.0f}, €{u['cost_per_scan']:.0f}/scan, €{u['cost_per_additional_scan']:.0f}/additional scan")
        print(f"national: eligible {n['eligible']:,.0f}, scans/yr {n['scans_year']:,.0f}, deaths avoided/yr {n['deaths_avoided_year']:.0f}")
        print(f"written to {paths.MODEL_OUT}")
    elif a.cmd == "counties":
        print(len(screening.county_table()), "counties written")
    elif a.cmd == "sensitivity":
        import csv
        tab = routing.sensitivity_table()
        with open(paths.ROUTING / "sensitivity.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["perturbation", "central_plan_additional", "reoptimised_additional", "regret_pct", "stop_set_overlap_jaccard"])
            for t in tab:
                w.writerow([t["label"], round(t["central_plan"]), round(t["reoptimised"]), round(100 * t["regret"], 1), round(t["jaccard"], 2)])
                print(f"{t['label']:<24} central {t['central_plan']:>5.0f} | reopt {t['reoptimised']:>5.0f} | regret {100*t['regret']:>5.1f}% | overlap {t['jaccard']:.2f}")
    elif a.cmd == "robust":
        import csv
        scn = scenario.load(a.file)
        mapper = robust.process_pool_mapper(a.workers) if a.workers > 1 else None
        r = robust.run(scn, n=a.n, seed=a.seed, mapper=mapper, chunk=a.chunk)
        out = paths.DATA / "robust"
        out.mkdir(parents=True, exist_ok=True)
        base = scn.get("name", "scenario")
        for suffix, rows in (("stability", r["stability"]), ("plans", r["plans"]), ("voi", r["voi"])):
            with open(out / f"{base}_{suffix}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        print(f"{base}: n={r['n']} planning worlds, {r['n_validation']} validation worlds; recommended: {r['recommended']}")
        for p in r["plans"][:6]:
            print(f"  {p['name']:<22} stops {p['stops']:>2} | regret mean {100*p['mean_regret']:>4.1f}% p90 {100*p['p90_regret']:>4.1f}% | extra/yr p5-p95 {p['additional_p5']:.0f}-{p['additional_p95']:.0f}")
        print("what to measure first (expected regret from not knowing it):")
        for v in r["voi"]:
            print(f"  {v['param']:<24} {v['expected_regret_pct']:>5.1f}% (p90 {v['p90_regret_pct']:.1f}%)")
        print(f"written to {out}")
    elif a.cmd == "ask":
        try:
            r = analyst.ask(a.question, use_cache=a.replay)
        except analyst.AnalystUnavailable as e:
            print(f"analyst unavailable: {e}")
            return 2
        print(r["answer"])
        print("\n--- scenarios run:")
        for sc in r["scenarios"]:
            print(" -", sc["label"], sc["summary"])
        u = r["usage"]
        print(f"--- {r['model']}{' (replayed)' if r['cached'] else ''}: {u['api_calls']} calls, {u['input']} in / {u['output']} out tokens, cache read {u['cache_read']}")
    elif a.cmd == "readout":
        print(readout_mod.run(scenario.load(a.file))["answer"])
    elif a.cmd == "gap":
        d = gap.build()
        print(f"{len(d['counties'])} counties, national breast {d['national']['breast']}% colorectal {d['national']['colorectal']}%; wrote {gap.GAP / 'gapdata.json'}")
    elif a.cmd == "pilot":
        n = pilot.n_per_arm(a.p_a, a.delta, power=a.power)
        ad = pilot.additionality(a.p_a, a.p_a + a.delta)
        print(f"baseline uptake {a.p_a:.0%}, uplift {a.delta:.0%}: {n} invitees per arm ({2*n} total) for {a.power:.0%} power")
        print(f"  additional scans per 100 invitees {ad['additional_per_100_invitees']:.0f}; would have happened anyway {ad['would_have_happened_anyway_per_100']:.0f}; additionality share {ad['additionality_share']:.0%}")
        for c in (0.0, 0.3):
            r = pilot.simulate(n, a.p_a, a.delta, reps=1000, contamination=c)
            print(f"  simulated, {c:.0%} of controls leak to the mobile offer: power {r['power']:.0%}, estimated uplift {r['mean_rd']:.3f} (true {r['true_itt_rd']:.3f}), CI coverage {r['ci_coverage']:.0%}")
        b = pilot.before_after_bias(a.p_a, a.delta, a.campaign_boost)
        print(f"  before/after with a campaign (+{a.campaign_boost:.0%} uptake): naive {b['naive_additional_per_100']:.0f} per 100 vs randomised {b['randomised_additional_per_100']:.0f} per 100 (overstates by {b['overstatement_per_100']:.0f})")
    elif a.cmd == "area":
        print(areadata.build())
    elif a.cmd == "ctsites":
        r = ctsites.compile()
        print(r)
    elif a.cmd == "routes":
        for r in routing.run_report():
            print(r)
    elif a.cmd == "scenario":
        print(json.dumps(scenario.run(scenario.load(a.file)), indent=2, ensure_ascii=False))
    elif a.cmd == "serve":
        from .server import serve
        serve(port=a.port)
    elif a.cmd == "tests":
        suite = unittest.defaultTestLoader.discover(str(paths.ROOT / "tests"), top_level_dir=str(paths.ROOT))
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
