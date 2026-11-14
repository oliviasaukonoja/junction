#!/usr/bin/env python3
"""Merge Cancer Registry incidence (2020-24) with cancer deaths (2023-25, Statistics Finland) and oncology referrals/waits.
Usage: python3 incidence_crossref.py WAIT_CACHE_DIR  (needs deaths.json from wait_times_syopataudit.py and its output CSV)"""
import csv, itertools, json, sys
from pathlib import Path
C = Path(sys.argv[1]); ROOT = Path(__file__).resolve().parents[2]
inc = {}
for r in csv.DictReader(open(ROOT / "data/registry/cancer_registry_incidence_2020_2024.csv", encoding="utf-8")):
    inc.setdefault(r["area"], {})[r["sex"]] = r
def js(f):
    r = json.load(open(C / f)); ids = r["id"]
    cats = [list(r["dimension"][i]["category"]["index"]) for i in ids]
    return {tuple(cats[j][c[j]] for j in range(len(ids))): r["value"][k] for k, c in enumerate(itertools.product(*[range(s) for s in r["size"]]))}
deaths, pop = js("deaths.json"), js("pop.json")
GRP = {"Etelä-Karjala": ["Etelä-Karjalan hyvinvointialue"], "Etelä-Pohjanmaa": ["Etelä-Pohjanmaan hyvinvointialue"], "Etelä-Savo": ["Etelä-Savon hyvinvointialue"],
 "HUS (Uusimaa 4 + Helsinki)": ["Itä-Uudenmaan hyvinvointialue", "Keski-Uudenmaan hyvinvointialue", "Länsi-Uudenmaan hyvinvointialue", "Vantaan ja Keravan hyvinvointialue", "Helsingin kaupunki"],
 "Kainuu": ["Kainuun hyvinvointialue"], "Kanta-Häme": ["Kanta-Hämeen hyvinvointialue"], "Keski-Pohjanmaa": ["Keski-Pohjanmaan hyvinvointialue"], "Keski-Suomi": ["Keski-Suomen hyvinvointialue"],
 "Kymenlaakso": ["Kymenlaakson hyvinvointialue"], "Lappi": ["Lapin hyvinvointialue"], "Pirkanmaa": ["Pirkanmaan hyvinvointialue"], "Pohjanmaa": ["Pohjanmaan hyvinvointialue"],
 "Pohjois-Karjala": ["Pohjois-Karjalan hyvinvointialue"], "Pohjois-Pohjanmaa": ["Pohjois-Pohjanmaan hyvinvointialue"], "Pohjois-Savo": ["Pohjois-Savon hyvinvointialue"],
 "Päijät-Häme": ["Päijät-Hämeen hyvinvointialue"], "Satakunta": ["Satakunnan hyvinvointialue"], "Varsinais-Suomi": ["Varsinais-Suomen hyvinvointialue"]}
SF = {"Etelä-Karjalan hyvinvointialue": "HVA11", "Etelä-Pohjanmaan hyvinvointialue": "HVA16", "Etelä-Savon hyvinvointialue": "HVA12", "Itä-Uudenmaan hyvinvointialue": "HVA01",
 "Keski-Uudenmaan hyvinvointialue": "HVA02", "Länsi-Uudenmaan hyvinvointialue": "HVA03", "Vantaan ja Keravan hyvinvointialue": "HVA04", "Helsingin kaupunki": "HVA90",
 "Kainuun hyvinvointialue": "HVA20", "Kanta-Hämeen hyvinvointialue": "HVA07", "Keski-Pohjanmaan hyvinvointialue": "HVA18", "Keski-Suomen hyvinvointialue": "HVA15",
 "Kymenlaakson hyvinvointialue": "HVA10", "Lapin hyvinvointialue": "HVA21", "Pirkanmaan hyvinvointialue": "HVA08", "Pohjanmaan hyvinvointialue": "HVA17",
 "Pohjois-Karjalan hyvinvointialue": "HVA14", "Pohjois-Pohjanmaan hyvinvointialue": "HVA19", "Pohjois-Savon hyvinvointialue": "HVA13", "Päijät-Hämeen hyvinvointialue": "HVA09",
 "Satakunnan hyvinvointialue": "HVA06", "Varsinais-Suomen hyvinvointialue": "HVA05"}
wait = {}
for r in csv.DictReader(open(ROOT / "docs/wait_times_syopataudit_2023_2026.csv", encoding="utf-8")):
    if r["year"] == "2025": wait[r["area"]] = r
def wname(g): return "HUS" if g.startswith("HUS") else GRP[g][0]   # registry and THL use the same names outside HUS
fl = lambda x: float(x) if x not in ("", None) else None
rows = []
for g, parts in GRP.items():
    n = sum(int(inc[a][s]["new_cases_all_2020_2024"]) for a in parts for s in ("Miehet", "Naiset")) / 5
    nl = sum(int(inc[a][s]["new_cases_lung_2020_2024"]) for a in parts for s in ("Miehet", "Naiset")) / 5
    p23_25 = {y: sum(pop[(SF[a], "vaerak-vaesto", y)] for a in parts) for y in ("2023", "2024", "2025")}
    w = {a: sum(pop[(SF[b], "vaerak-vaesto", "2024")] for b in parts if b == a) for a in parts}; tw = sum(w.values())
    asr = lambda sex, k: sum(float(inc[a][sex][k]) * w[a] for a in parts) / tw   # population-weighted (approximation for HUS)
    d = sum(deaths[(SF[a], "04-21", y, "ksyylkm")] for a in parts for y in ("2023", "2024", "2025")) / 3
    wr = wait.get(wname(g))
    rows.append(dict(g=g, n=n, nl=nl, inc_rate=1e5 * n / (sum(p23_25.values()) / 3), asr_m=asr("Miehet", "asr_all_per100k_finland2014"), asr_f=asr("Naiset", "asr_all_per100k_finland2014"),
                     lung_m=asr("Miehet", "asr_lung_per100k_finland2014"), lung_f=asr("Naiset", "asr_lung_per100k_finland2014"), deaths=d, mir=d / n,
                     ref=fl(wr["referrals_ytd_at_year_end"]) if wr else None, h90=fl(wr["treat_pct_over90d"]) if wr else None))
nat = {s: inc["Koko maa"][s] for s in ("Miehet", "Naiset")}
tot_n = sum(int(nat[s]["new_cases_all_2020_2024"]) for s in nat) / 5
chk = sum(r["n"] for r in rows)
out = ["# Cancer incidence by welfare area (Finnish Cancer Registry, 2020-2024) next to deaths and oncology referrals", "",
       f"Annual new cases = five-year total / 5 (all sexes). National: {tot_n:,.0f} a year; sum of areas: {chk:,.0f} (the gap is mostly Åland and unassigned residence; not checked). Deaths: Statistics Finland, all cancers, 2023-25 average. "
       "Rates are age-standardised per 100,000 (Finland 2014 standard) for men (M) and women (F); lung = C33-34. HUS rates are population-weighted averages of its five areas (approximation).", "",
       "| Area | New cancers /yr | Lung /yr | All cancers ASR M / F | Lung ASR M / F | Cancer deaths /yr | Deaths per new case | Oncology referrals 2025 | Referrals per new case | Treat >90 d % (2025) |",
       "|---|--:|--:|---|---|--:|--:|--:|--:|--:|"]
for r in sorted(rows, key=lambda r: -r["n"]):
    out.append(f"| {r['g']} | {r['n']:,.0f} | {r['nl']:,.0f} | {r['asr_m']:.0f} / {r['asr_f']:.0f} | {r['lung_m']:.0f} / {r['lung_f']:.0f} | {r['deaths']:,.0f} | {r['mir']:.2f} | "
               f"{(f'{r['ref']:,.0f}' if r['ref'] else '–')} | {(f'{r['ref']/r['n']:.2f}' if r['ref'] else '–')} | {(f'{r['h90']:.0f}' if r['h90'] is not None else '–')} |")
out += ["", f"National lung ASR: M {nat['Miehet']['asr_lung_per100k_finland2014']}, F {nat['Naiset']['asr_lung_per100k_finland2014']}; all cancers M {nat['Miehet']['asr_all_per100k_finland2014']}, F {nat['Naiset']['asr_all_per100k_finland2014']}.", ""]
(ROOT / "docs/incidence_by_area_2020_2024.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
