"""Back-of-envelope estimate of lung-cancer deaths avoided per year by CT screening of the high-risk group in Finland.
Reproducible companion to docs/gap_analysis_and_cost.md. Not part of the simulator. Run: python3 -I docs/analysis/lives_saved_estimate.py

Two independent methods; each input is tagged S (sourced), M (recalled, verify) or A (assumption).
 Method 1, trial rates: eligible people x trial control mortality x effect (NELSON).
 Method 2, registry deaths: Finnish lung deaths aged 50-74 x share in the eligible group x coverage x effect.
Steady state after several rounds; the benefit appears years after screening starts. Assumes the trial effect transfers (it may not).
"""
import json, random, statistics, urllib.request

def stat_deaths():
    base = "https://statfin.stat.fi/PxWeb/api/v1/en/StatFin/ksyyt/11be.px"
    m = json.load(urllib.request.urlopen(base, timeout=60))
    code = {v["text"].split(" (")[0]: v["code"] for v in m["variables"]}
    cause, age = code["Underlying cause of death"], code["Age"]
    ages = ["50-54", "55-59", "60-64", "65-69", "70-74"]
    q = {"query": [{"code": cause, "selection": {"filter": "item", "values": ["C34"]}},
                   {"code": age, "selection": {"filter": "item", "values": ["SSS"] + ages}},
                   {"code": "timeperiod_y", "selection": {"filter": "item", "values": ["2021", "2022", "2023", "2024", "2025"]}},
                   {"code": "sukupuoli_9_20180101", "selection": {"filter": "item", "values": ["SSS"]}},
                   {"code": "contentscode", "selection": {"filter": "all", "values": ["*"]}}], "response": {"format": "json-stat2"}}
    d = json.load(urllib.request.urlopen(urllib.request.Request(base, json.dumps(q).encode(), {"Content-Type": "application/json"}), timeout=60))
    import itertools
    cats = {k: list(d["dimension"][k]["category"]["index"]) for k in d["id"]}
    out = {}
    for i, key in enumerate(itertools.product(*[cats[k] for k in d["id"]])):
        row = dict(zip(d["id"], key))
        a = next(v for k, v in row.items() if k.startswith("ikaryhma"))
        out[(a, row["timeperiod_y"])] = d["value"][i]
    return out

def tri(rng, lo, mid, hi):
    return rng.triangular(lo, hi, mid)

if __name__ == "__main__":
    d = stat_deaths()
    yrs = ["2021", "2022", "2023", "2024", "2025"]
    all_ages = statistics.fmean(d[("SSS", y)] for y in yrs)
    in5074 = statistics.fmean(sum(d[(a, y)] for a in ["50-54", "55-59", "60-64", "65-69", "70-74"]) for y in yrs)
    print(f"[S] Statistics Finland 11be, C34 lung deaths per year 2021-25: all ages {all_ages:.0f}; aged 50-74 {in5074:.0f} ({100*in5074/all_ages:.0f}%)")
    ELIG = 119_924            # [proxy] ctsim area model; see report 10.2
    rng = random.Random(1)
    m1, m2 = [], []
    for _ in range(20000):
        rr = tri(rng, 0.61, 0.76, 0.94)                         # [S] NELSON 10-y rate ratio and 95% CI
        uptake = tri(rng, 0.30, 0.50, 0.72)                    # [S range] London 31% responded, Yorkshire 56-73%
        adher = tri(rng, 0.55, 0.66, 0.80)                     # [S] 66% returned for a second scan (Atrium mobile); NELSON ~90%
        elig = ELIG * tri(rng, 0.7, 1.0, 1.4)                  # [A] eligible-count uncertainty (k_elig 0.55-1.1 around 0.8)
        cover = uptake * (0.5 + 0.5 * adher)                   # share of the group effectively screened over time
        base = tri(rng, 2.0, 3.3, 4.5)                         # [S] NELSON control 3.30 per 1000 person-years (volunteers); range [A]
        m1.append(elig * base / 1000 * cover * (1 - rr))
        share = tri(rng, 0.45, 0.60, 0.75)                     # [M/A] share of lung deaths aged 50-74 in people meeting >=20 pack-year criteria (US: about 57% of cases under 2021 criteria; verify)
        m2.append(in5074 * share * cover * (1 - rr))
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]
    for name, xs in (("Method 1, trial mortality rates", m1), ("Method 2, Finnish registry deaths", m2)):
        print(f"{name}: deaths avoided per year at steady state: median {q(xs,.5):.0f} (5th-95th {q(xs,.05):.0f}-{q(xs,.95):.0f})")
    print("Implied baseline mortality in the eligible group under method 2 (median inputs):",
          f"{in5074*0.60/ELIG*1000:.1f} per 1000 person-years vs NELSON control 3.3")
    print("Strategy target for scale: 10% fewer cancer deaths = about 1,330 a year (all cancers).")
