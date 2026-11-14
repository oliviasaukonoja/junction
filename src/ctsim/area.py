"""Area model: who is eligible and at high risk where, and how much CT capacity exists for them (with a campaign on top).

Risk group (evidence-based definition, see RISK_GROUP): people aged 50-74 who currently smoke or quit within 15 years and have at
least 20 pack-years. This is the lung-cancer LDCT eligibility used by US 2021 guidance, inside the EU Council 2022 range (50-75, heavy
current/former smokers) and broader than the NLST/Oulu pilot (>=30 pack-years). Only lung cancer has randomised evidence that CT screening
reduces deaths (NELSON, NLST).

What is verified and what is assumed
  verified   lung-cancer deaths by wellbeing county (Statistics Finland 13u5, ICD-10 C32-C34, 2021-2025), daily-smoking prevalence by
             county (THL Sotkanet 4405 age 20-64, 4406 age 65+), population by municipality (Statistics Finland), municipality -> county
  proxy      smoking prevalence in 50-74 = age-weighted mix of the 20-64 and 65+ county figures; lung deaths per 100k aged 50-74 =
             all-age deaths / population 50-74 (the table has crude rates only)
  assumed    eligible persons per current daily smoker (k_elig), CT volume per 1000 inhabitants and the share of it free for screening,
             baseline CT waits, how much a campaign raises uptake, how many ineligible people it sends for a scan
  not found  Finnish pack-year distribution, CT scanners or volumes by county, CT waiting times by county, screening capacity.
             Put county waits in data/area/ct_waits.csv (hva_code, ct_wait_weeks, source, date) and they replace the assumed baseline.

Hook: a World calls make_hook(...)(rows, prm) after computing distances and fixed-site uptake; the hook replaces the uniform eligible
share with the smoking-based estimate, weights places by lung mortality, and scales fixed-site uptake down where the county's free CT
capacity cannot serve the demand (screening plus campaign spill-over).
"""
from __future__ import annotations

import csv
from functools import lru_cache

from . import paths

AREA = paths.DATA / "area"

RISK_GROUP = dict(
    name="Heavy current or recent former smokers, 50-74",
    age_min=50, age_max=74, pack_years_min=20, quit_years_max=15,
    basis=["US Preventive Services Task Force 2021 (50-80, >=20 pack-years, quit <=15 y)",
           "EU Council Recommendation 2022 (current/former heavy smokers, 50-75; stepwise, further research)",
           "NELSON (RR 0.76, 10-year) and NLST (20% reduction); Oulu pilot used >=15 cig/day x25y or >=10 x30y, age 50-74"],
    note="Individuals cannot be identified from public data; the model estimates how many such people live in each municipality.")


class AreaData:
    def __init__(self):
        self.county_of = {}
        for r in csv.DictReader(open(AREA / "county_map.csv", encoding="utf-8")):
            self.county_of[r["code"]] = r["hva_code"]
        self.counties = {}
        for r in csv.DictReader(open(AREA / "county_indicators.csv", encoding="utf-8")):
            f = lambda k: float(r[k]) if r[k] != "" else None
            self.counties[r["hva_code"]] = dict(name=r["county"], pop_all=int(r["pop_all"]), pop50=int(r["pop_50_74"]),
                                                deaths=f("lung_deaths_mean_2021_2025"), crude=f("lung_deaths_per_100k_crude"),
                                                rate50=f("lung_deaths_per_100k_aged_50_74_proxy"), smk2064=f("smoking_20_64_pct"), smk65=f("smoking_65plus_pct"))
        deaths = sum(c["deaths"] for c in self.counties.values())
        pop50 = sum(c["pop50"] for c in self.counties.values())
        self.national_rate50 = deaths / pop50 * 1e5
        for c in self.counties.values():
            c["mort_index"] = c["rate50"] / self.national_rate50
        self.waits = {}
        p = AREA / "ct_waits.csv"
        if p.exists():
            for r in csv.DictReader(open(p, encoding="utf-8")):
                if r.get("ct_wait_weeks"):
                    self.waits[r["hva_code"]] = float(r["ct_wait_weeks"])


@lru_cache(maxsize=1)
def load() -> AreaData:
    return AreaData()


def make_hook(intensity: float = 0.0, triage: float = 0.6, priority: bool = True, gamma: float = 1.0):
    """Return hook(rows, prm) -> info dict. intensity = campaign intensity (0 = no campaign), triage = share of ineligible
    campaign-driven demand filtered out before booking, priority = eligible people are booked first when capacity is short."""
    def hook(rows: list[dict], prm: dict) -> dict:
        A = load()
        interval = prm["interval"]
        by_c: dict[str, list[dict]] = {}
        for r in rows:
            c = A.county_of[r["code"]]
            cd = A.counties[c]
            young, old = r.get("p5064"), r.get("p6574")
            if young is None:                                  # municipality table without age columns: assume the national mix
                young, old = 0.6 * r["pop"], 0.4 * r["pop"]
            s = (young * cd["smk2064"] + old * cd["smk65"]) / max(young + old, 1) / 100.0
            r["county"] = c
            r["smoke_share"] = s
            r["elig"] = r["pop"] * s * prm["k_elig"]
            r["mort_index"] = cd["mort_index"]
            r["w"] = r["w"] * (cd["mort_index"] ** gamma)
            by_c.setdefault(c, []).append(r)
        info = {}
        for c, rs in by_c.items():
            cd = A.counties[c]
            elig = sum(r["elig"] for r in rs)
            pop = sum(r["pop"] for r in rs)
            demand_elig = sum(r["elig"] * r["u_fixed"] for r in rs) / interval              # scans per year if every fixed-site user were served
            demand_inel = max(pop - elig, 0.0) * prm["spill_per_int"] * intensity * (1 - triage)
            volume = cd["pop_all"] * prm["ct_per_1000"] / 1000.0
            spare = prm["spare_share"] * volume
            total = demand_elig + demand_inel
            if priority:
                rho = min(1.0, spare / demand_elig) if demand_elig > 0 else 1.0               # eligible people are booked first
            else:
                rho = min(1.0, spare / total) if total > 0 else 1.0                           # everyone shares the shortfall
            shortfall = max(0.0, total - spare)
            extra_wait = shortfall / (volume / 52.0) if volume > 0 else 0.0
            wait0 = A.waits.get(c, prm["wait0"])
            for r in rs:
                r["u_fixed"] *= rho
            info[c] = dict(county=cd["name"], eligible=elig, pop50=pop, demand_eligible=demand_elig, demand_ineligible=demand_inel, volume=volume,
                           spare=spare, served_share=rho, shortfall=shortfall, extra_wait_weeks=extra_wait, baseline_wait_weeks=wait0,
                           baseline_wait_is_data=c in A.waits, wait_weeks=wait0 + extra_wait, mort_index=cd["mort_index"],
                           lung_deaths_per_100k_50_74=cd["rate50"], smoking_20_64=cd["smk2064"], smoking_65plus=cd["smk65"])
        return info
    return hook
