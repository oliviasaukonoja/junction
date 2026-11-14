"""Gap-finder data: real Cancer Registry screening participation by county and group (2024) plus curated, tagged indicators.

`python -m ctsim gap` writes data/gap/gapdata.json, which the server and the Modal app serve at /gapdata for web/gap.html.
County and group numbers are read from data/screening (extracted from the registry's own tables); indicators.json is curated by hand.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from . import paths, pilot, scenario, screening

GAP = paths.DATA / "gap"


def _rows(fn: str) -> list[list[str]]:
    return list(csv.reader(open(paths.SCREENING / fn, encoding="utf-8")))[2:]


def _pct(rows, label, col):
    for r in rows:
        if r[0] == label and len(r) > col:
            return float(r[col])
    raise KeyError(label)


def _group(prefix: str, section: str, labels: list[str], pct_col: int, total_sex: bool) -> dict:
    fn = screening._find(paths.SCREENING / f"{prefix}_INDEX.tsv", section, "2024")[0]
    rows = _rows(fn)
    if total_sex:                                   # colorectal tables have a sex column; use the Total rows
        rows = [[r[0]] + r[2:] for r in rows if len(r) > 1 and r[1] == "Total"]
    return {"file": fn, **{lab: _pct(rows, lab, pct_col) for lab in labels}}


def build(out: Path | None = None) -> dict:
    counties = []
    for r in csv.DictReader(open(paths.SCREENING / "counties_participation_2024.csv", encoding="utf-8")):
        counties.append({"county": r["county"],
                         "breast": float(r["breast_participation_pct"]) if r["breast_participation_pct"] else None,
                         "cervical": float(r["cervical_participation_pct_combined_subtables"]) if r["cervical_participation_pct_combined_subtables"] else None,
                         "colorectal": float(r["colorectal_participation_pct"]) if r["colorectal_participation_pct"] else None})
    lang_labels = ["Domestic", "Other/missing"]
    edu_labels = ["Primary education/unknown", "Intermediate/secondary", "Tertiary/higher education"]
    groups = {
        "language": {"breast": _group("breast", "Population groups > Native language", lang_labels, 3, False),
                     "colorectal": _group("colorectal", "Population groups > Native language", lang_labels, 3, True),
                     "cervical": _group("cervix", "Population groups > Native language", lang_labels, 3, False)},
        "education": {"breast": _group("breast", "Population groups > Level of education", edu_labels, 3, False),
                      "colorectal": _group("colorectal", "Population groups > Level of education", edu_labels, 3, True)},
    }
    national = {"breast": _pct(_rows(screening._find(paths.SCREENING / "breast_INDEX.tsv", "Wellbeing services counties > Screening process", "2024")[0]), "Total", 3),
                "colorectal": _pct(_rows(screening._find(paths.SCREENING / "colorectal_INDEX.tsv", "Wellbeing services counties > Screening process", "2024")[0]), "Total", 3)}
    base = {"name": "gap", "region": None, "ct_sites": "confirmed+likely"}
    r0 = scenario.run(base)
    r2 = scenario.run({**base, "routing": {"campaign_intensity": 2.0, "triage": 0.6, "priority_eligible": True}})
    c2 = {c["hva_code"]: c for c in r2["counties"]}
    area_rows = []
    for c in r0["counties"]:
        area_rows.append(dict(hva_code=c["hva_code"], county=c["county"], eligible=c["eligible"], pop50=c["pop50"], lung_deaths_per_100k_50_74=c["lung_deaths_per_100k_50_74"],
                              mort_index=c["mort_index"], smoking_20_64=c["smoking_20_64"], smoking_65plus=c["smoking_65plus"], ct_towns=c["ct_towns"],
                              served_share_no_campaign=c["served_share"], extra_wait_no_campaign=c["extra_wait_weeks"], extra_wait_campaign_2=c2[c["hva_code"]]["extra_wait_weeks"],
                              baseline_wait_weeks=c["baseline_wait_weeks"], baseline_wait_is_data=c["baseline_wait_is_data"]))
    camp = dict(no_campaign=r0["campaign"], campaign_2=r2["campaign"])
    pil = dict(design=pilot.design_table(), example=dict(
        n_per_arm=pilot.n_per_arm(0.40, 0.15), additionality=pilot.additionality(0.40, 0.55),
        sim_clean=pilot.simulate(pilot.n_per_arm(0.40, 0.15), 0.40, 0.15, reps=600, seed=1),
        sim_leak=pilot.simulate(pilot.n_per_arm(0.40, 0.15), 0.40, 0.15, reps=600, seed=1, contamination=0.3),
        before_after=pilot.before_after_bias(0.40, 0.15, 0.30)))
    ind = json.loads((GAP / "indicators.json").read_text(encoding="utf-8"))
    data = {"year": 2024, "target_pct": 80, "national": national, "counties": counties, "groups": groups, "area": area_rows, "area_national": dict(eligible=r0["reach"]["eligible_persons"], campaign=camp, risk_group=r0["risk_group"]), "pilot": pil, **ind,
            "source": "Finnish Cancer Registry screening statistics 2024 (stats.cancerregistry.fi), extracted to data/screening; county cervical = sum of two unlabelled sub-tables"}
    out = Path(out or GAP / "gapdata.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data
