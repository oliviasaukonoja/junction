"""CT site list: compile researched rows into one table and expose it to the routing model.

Input : data/ct_sites/raw_group*.csv   (researched from public web sources, mostly via search summaries; see the notes and source_url columns)
        data/ct_sites/overrides.csv    (manual corrections applied on top, each with a reason)
Output: data/ct_sites/ct_sites.csv     (deduplicated, municipality names validated against the Statistics Finland table)
        data/ct_sites/ct_sites_unmatched.csv  (rows whose municipality name does not match; fix by hand)

There is no national open register of CT scanner locations that I could find. This list is therefore a researched
approximation: 'confirmed' = a source says the facility offers CT; 'likely' = inferred (reason in notes). Private
providers and mobile units are kept but flagged. Check it with the counties before quoting it.
"""
from __future__ import annotations

import csv
from pathlib import Path

from . import paths

DIR = paths.DATA / "ct_sites"
COLUMNS = ["county", "facility", "municipality", "facility_type", "ct_status", "n_scanners", "evidence", "source_url", "source_date", "notes"]
TYPES = {"university", "central", "regional", "health_centre", "private", "mobile"}
STATUS = {"confirmed", "likely"}


def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


def compile(raw_dir: Path | None = None, out_dir: Path | None = None, municipalities_csv: Path | None = None) -> dict:
    raw_dir = Path(raw_dir or DIR)
    out_dir = Path(out_dir or raw_dir)
    muni_path = Path(municipalities_csv or paths.MUNICIPALITIES_CSV)
    names = {_norm(r["name"]): r["name"] for r in csv.DictReader(open(muni_path, encoding="utf-8"))}

    rows, problems = [], []
    for f in sorted(raw_dir.glob("raw_group*.csv")):
        with open(f, encoding="utf-8", newline="") as fh:
            rd = csv.DictReader(fh)
            missing = [c for c in COLUMNS if c not in (rd.fieldnames or [])]
            if missing:
                problems.append(f"{f.name}: missing columns {missing}")
                continue
            for r in rd:
                r = {c: (r.get(c) or "").strip() for c in COLUMNS}
                r["source_file"] = f.name
                rows.append(r)

    good, unmatched, seen = [], [], set()
    for r in rows:
        if r["facility_type"] not in TYPES or r["ct_status"] not in STATUS:
            problems.append(f"{r['source_file']}: bad type/status for {r['facility']} ({r['facility_type']}/{r['ct_status']})")
            continue
        key = (_norm(r["facility"]), _norm(r["municipality"]))
        if key in seen:
            continue
        seen.add(key)
        canon = names.get(_norm(r["municipality"]))
        if canon is None:
            unmatched.append(r)
            continue
        r["municipality"] = canon
        good.append(r)

    overrides = []
    ov_path = raw_dir / "overrides.csv"
    if ov_path.exists():
        overrides = list(csv.DictReader(open(ov_path, encoding="utf-8", newline="")))
    for r in good + unmatched:
        r["counts_for_routing"] = "no" if r["facility_type"] in ("private", "mobile") else "yes"
        r["override_reason"] = ""
    for o in overrides:
        hit = [r for r in good if r["facility"].lower().startswith(o["facility"].strip().lower())]
        if not hit:
            problems.append(f"override matched nothing: {o['facility']}")
        for r in hit:
            r[o["field"]] = o["value"]
            r["override_reason"] = o["reason"]

    cols = COLUMNS + ["source_file", "counts_for_routing", "override_reason"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("ct_sites.csv", good), ("ct_sites_unmatched.csv", unmatched)):
        with open(out_dir / name, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(data)
    munis = {r["municipality"] for r in good if r["counts_for_routing"] == "yes"}
    conf = {r["municipality"] for r in good if r["counts_for_routing"] == "yes" and r["ct_status"] == "confirmed"}
    return dict(rows=len(good), unmatched=len(unmatched), municipalities=len(munis), confirmed_municipalities=len(conf), problems=problems)


def names(mode: str = "confirmed", path: Path | None = None) -> list[str]:
    """Municipality names with a public fixed CT, for routing. Mobile units, private providers and rows flagged
    counts_for_routing=no (dental, coronary-only) never count. Hybrid-only rows (PET/CT, SPECT/CT) are downgraded to 'likely'.

    mode: 'confirmed' | 'confirmed+likely'. (The placeholder list lives in routing.FIXED_SITE_NAMES.)
    """
    path = Path(path or DIR / "ct_sites.csv")
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; run `python -m ctsim ctsites` after the raw_group*.csv files exist")
    allowed = {"confirmed"} if mode == "confirmed" else {"confirmed", "likely"}
    if mode not in ("confirmed", "confirmed+likely"):
        raise ValueError("ct_sites mode must be 'confirmed' or 'confirmed+likely'")
    with open(path, encoding="utf-8") as fh:
        out = {r["municipality"] for r in csv.DictReader(fh) if r["ct_status"] in allowed and r.get("counts_for_routing", "yes") == "yes" and r["facility_type"] not in ("mobile", "private")}
    return sorted(out)
