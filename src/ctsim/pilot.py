"""Randomised-invitation pilot: sample size, power and bias checks for measuring how many scans are genuinely additional.

Design in one line: eligible residents are randomised 1:1 (stratified) to
  A  invitation to book at an existing hospital CT (the standard pathway), or
  B  the same invitation plus an offered slot at a mobile or pop-up site near home.
Primary outcome: a completed screening scan within 6 months of invitation, verified from booking and imaging records.
  additional scans per 100 invitees = 100 x (p_B - p_A)             (intention-to-treat risk difference)
  would have happened anyway        = p_A                           (what arm B's invitees would have done without the offer)
  additionality share of B's scans  = (p_B - p_A) / p_B
A campaign hits both arms equally, so it cancels in the difference; a before/after comparison would count the campaign's effect as 'additional'.
These functions size the trial and show how contamination and a pre/post design would bias the answer. Inputs are planning values.
"""
from __future__ import annotations

import csv
import math
import random
import statistics
from pathlib import Path

from . import paths

Z = statistics.NormalDist()


def n_per_arm(p_a: float, delta: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Individuals per arm to detect risk difference `delta` over baseline `p_a` (two-sided test, normal approximation, no dropout inflation)."""
    p_b = p_a + delta
    if not (0 < p_a < 1 and 0 < p_b < 1) or delta == 0:
        raise ValueError("p_a and p_a + delta must be in (0, 1) and delta nonzero")
    pbar = (p_a + p_b) / 2
    za, zb = Z.inv_cdf(1 - alpha / 2), Z.inv_cdf(power)
    n = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p_a * (1 - p_a) + p_b * (1 - p_b))) ** 2 / delta ** 2
    return math.ceil(n)


def additionality(p_a: float, p_b: float) -> dict:
    rd = p_b - p_a
    return dict(additional_per_100_invitees=100 * rd, would_have_happened_anyway_per_100=100 * p_a, additionality_share=rd / p_b if p_b > 0 else float("nan"))


def simulate(n_arm: int, p_a: float, delta: float, reps: int = 2000, seed: int = 1, strata: int = 3, stratum_spread: float = 0.5,
             contamination: float = 0.0, alpha: float = 0.05) -> dict:
    """Monte Carlo of the stratified trial. Baseline uptake differs by stratum (spread = relative range, e.g. distance bands) with the same mean.

    contamination = share of arm A invitees who in fact get the mobile offer (leakage), which pulls the estimate towards zero.
    Returns power (lower CI bound above 0), mean estimated risk difference, CI coverage of the true difference, and the 'true' ITT difference.
    """
    rng = random.Random(seed)
    mult = [1 + stratum_spread * (2 * s / (strata - 1) - 1) for s in range(strata)] if strata > 1 else [1.0]
    pa = [min(0.95, p_a * m) for m in mult]
    pb = [min(0.95, p + delta) for p in pa]
    true_rd = statistics.fmean(pb) - statistics.fmean([(1 - contamination) * a + contamination * b for a, b in zip(pa, pb)])
    n_s = n_arm // strata
    w = n_s / (n_s * strata)
    za = Z.inv_cdf(1 - alpha / 2)
    hits = covered = 0
    rds = []
    for _ in range(reps):
        rd = var = 0.0
        for s in range(strata):
            p_ctrl = (1 - contamination) * pa[s] + contamination * pb[s]
            xa = sum(rng.random() < p_ctrl for _ in range(n_s))
            xb = sum(rng.random() < pb[s] for _ in range(n_s))
            qa, qb = xa / n_s, xb / n_s
            rd += w * (qb - qa)
            var += w * w * (qb * (1 - qb) / n_s + qa * (1 - qa) / n_s)
        se = math.sqrt(var) if var > 0 else 1e-9
        rds.append(rd)
        hits += (rd - za * se) > 0
        covered += (rd - za * se) <= true_rd <= (rd + za * se)
    return dict(n_per_arm=n_s * strata, power=hits / reps, mean_rd=statistics.fmean(rds), sd_rd=statistics.pstdev(rds), true_itt_rd=true_rd, ci_coverage=covered / reps)


def before_after_bias(p_a: float, delta: float, campaign_boost: float) -> dict:
    """What a naive before/after count reports versus the randomised answer when a campaign raises uptake for everyone."""
    p_pre = p_a
    p_post_no_truck = min(0.95, p_a * (1 + campaign_boost))
    p_post_truck_offer = min(0.95, p_post_no_truck + delta)
    return dict(naive_additional_per_100=100 * (p_post_truck_offer - p_pre), randomised_additional_per_100=100 * (p_post_truck_offer - p_post_no_truck),
                overstatement_per_100=100 * (p_post_no_truck - p_pre))


def design_table(p_as=(0.30, 0.40, 0.50), deltas=(0.05, 0.10, 0.15, 0.20), powers=(0.80, 0.90)) -> list[dict]:
    rows = []
    for p_a in p_as:
        for d in deltas:
            for pw in powers:
                n = n_per_arm(p_a, d, power=pw)
                rows.append(dict(baseline_uptake=p_a, uplift=d, power=pw, n_per_arm=n, total=2 * n, additionality_share=round(d / (p_a + d), 3)))
    return rows


def write_design_table(out: Path | None = None) -> Path:
    out = Path(out or paths.DATA / "pilot" / "design_table.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = design_table()
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return out
