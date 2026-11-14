#!/usr/bin/env python3
"""Cancer-care (Syöpätaudit, specialty 65) referrals, queues and cancer deaths per welfare area, 2023 onward.

Sources (public, downloaded fresh into a cache folder):
  * THL cube "Hoitoa ja hoidon tarpeen arviointia odottavat erikoisaloittain", filter erikoisala 862186 = 65 Syöpätaudit
    https://sampo.thl.fi/pivot/prod/fi/eshjono/jonotilanne
  * Statistics Finland StatFin 13u5 (deaths by underlying cause and welfare area) and 11ra (population, 65+ share)

Usage:  python3 wait_times_syopataudit.py CACHE_DIR OUT_DIR
Writes: OUT_DIR/wait_times_syopataudit_2023_2026.csv (long table) and .md (tables, flags, caveats)
"""
import csv, io, itertools, json, random, sys, time, urllib.request
from pathlib import Path

CACHE = Path(sys.argv[1] if len(sys.argv) > 1 else "wait_cache"); CACHE.mkdir(parents=True, exist_ok=True)
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "."); OUT.mkdir(parents=True, exist_ok=True)

THL = "https://sampo.thl.fi/pivot/prod/fi/eshjono/jonotilanne/fact_eshjono_jonotilanne.csv"
SYOPA = "erikoisala-862186"   # 65 Syöpätaudit
MEASURES = {  # THL measure id -> short name
    738214: "hoito_n", 738219: "hoito_gt90n", 738216: "hoito_gt180n",
    738222: "arv_n", 738227: "arv_gt90n", 738224: "arv_gt180n",
    980631: "lah_ytd", 980625: "lah_kasitelty_ytd", 980628: "lah_gt21n"}
NAT = "Kaikki hyvinvointialueet"
YEARS = ["2023", "2024", "2025", "2026"]   # 2026 = Jan-Sep only
# THL provider -> StatFin areas. HUS provides specialised care for Uusimaa's four areas and Helsinki.
MAP = {"Etelä-Karjalan hyvinvointialue": ["HVA11"], "Etelä-Pohjanmaan hyvinvointialue": ["HVA16"],
       "Etelä-Savon hyvinvointialue": ["HVA12"], "HUS": ["HVA01", "HVA02", "HVA03", "HVA04", "HVA90"],
       "Helsingin sosiaali-, terveys- ja pelastustoimi": [], "Kainuun hyvinvointialue": ["HVA20"],
       "Kanta-Hämeen hyvinvointialue": ["HVA07"], "Keski-Pohjanmaan hyvinvointialue": ["HVA18"],
       "Keski-Suomen hyvinvointialue": ["HVA15"], "Kymenlaakson hyvinvointialue": ["HVA10"],
       "Lapin hyvinvointialue": ["HVA21"], "Pirkanmaan hyvinvointialue": ["HVA08"],
       "Pohjanmaan hyvinvointialue": ["HVA17"], "Pohjois-Karjalan hyvinvointialue": ["HVA14"],
       "Pohjois-Pohjanmaan hyvinvointialue": ["HVA19"], "Pohjois-Savon hyvinvointialue": ["HVA13"],
       "Päijät-Hämeen hyvinvointialue": ["HVA09"], "Satakunnan hyvinvointialue": ["HVA06"],
       "Varsinais-Suomen hyvinvointialue": ["HVA05"],
       NAT: ["HVA%02d" % i for i in range(1, 22)] + ["HVA90"]}


def get(url, name, data=None):
    f = CACHE / name
    if not f.exists():
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
        f.write_bytes(urllib.request.urlopen(req, timeout=90).read()); time.sleep(0.3)
    return f.read_text(encoding="utf-8")


def thl_series(mid):
    t = get(f"{THL}?row=tuottaja-976329&column=ajankohta-976319&filter=measure-{mid}&filter={SYOPA}", f"thl_{mid}.csv")
    rows = list(csv.reader(io.StringIO(t.lstrip("﻿")), delimiter=";"))[1:]
    return {(r[0], r[1]): (float(r[2]) if r[2].strip() else None) for r in rows if len(r) > 2}


def jsonstat(text):
    r = json.loads(text); ids, size = r["id"], r["size"]
    cats = [list(r["dimension"][i]["category"]["index"]) for i in ids]
    return {tuple(cats[j][c[j]] for j in range(len(ids))): r["value"][k]
            for k, c in enumerate(itertools.product(*[range(s) for s in size]))}


areas_q = [f"HVA{i:02d}" for i in range(1, 22)] + ["HVA90"]
deaths = jsonstat(get("https://statfin.stat.fi/PXWeb/api/v1/fi/StatFin/ksyyt/13u5.px", "deaths.json", json.dumps({"query": [
    {"code": "alue_23_20260101", "selection": {"filter": "item", "values": areas_q}},
    {"code": "kuolinsyyt_1_20210101", "selection": {"filter": "item", "values": ["SSS", "04-21"]}},
    {"code": "timeperiod_y", "selection": {"filter": "item", "values": ["2023", "2024", "2025"]}},
    {"code": "contentscode", "selection": {"filter": "item", "values": ["ksyylkm"]}}],
    "response": {"format": "json-stat2"}}).encode()))
popd = jsonstat(get("https://statfin.stat.fi/PXWeb/api/v1/fi/StatFin/vaerak/11ra.px", "pop.json", json.dumps({"query": [
    {"code": "alue_23_20260101", "selection": {"filter": "item", "values": areas_q}},
    {"code": "contentscode", "selection": {"filter": "item", "values": ["vaerak-vaesto", "vaesto_yli64_p"]}},
    {"code": "timeperiod_y", "selection": {"filter": "item", "values": ["2023", "2024", "2025"]}}],
    "response": {"format": "json-stat2"}}).encode()))

D = {n: thl_series(m) for m, n in MEASURES.items()}
dates = sorted({k[0] for k in D["lah_ytd"] if k[0][-4:].isdigit() and k[0][-4:] >= "2023"}, key=lambda d: (d[-4:], d[3:5]))
AREAS = sorted(a for a in MAP if a != NAT) + [NAT]
yr = lambda d: d[-4:]
last_date = dates[-1]


def dsum(a, cause, y):
    codes = MAP[a]; return sum(deaths[(c, cause, y, "ksyylkm")] for c in codes) if codes else None
def pop(a, y):
    codes = MAP[a]; return sum(popd[(c, "vaerak-vaesto", y)] for c in codes) if codes else None
def p65(a, y):
    codes = MAP[a]
    if not codes: return None
    w = [popd[(c, "vaerak-vaesto", y)] for c in codes]; s = [popd[(c, "vaesto_yli64_p", y)] for c in codes]
    return sum(x * z for x, z in zip(w, s)) / sum(w)


def ytd(meas, a, y):
    ds = [d for d in dates if yr(d) == y and D[meas].get((d, a)) is not None]
    return (D[meas][(ds[-1], a)], ds[-1][3:5]) if ds else (None, None)


def stock(a, pre, ys):
    ds = [d for d in dates if yr(d) in ys]
    ok = [d for d in ds if D[pre + "_n"].get((d, a)) is not None]
    n = sum(D[pre + "_n"][d, a] for d in ok)
    g90 = sum(D[pre + "_gt90n"][d, a] for d in ok if D[pre + "_gt90n"].get((d, a)) is not None)
    ok180 = [d for d in ok if D[pre + "_gt180n"].get((d, a)) is not None]
    n180 = sum(D[pre + "_n"][d, a] for d in ok180)
    g180 = sum(D[pre + "_gt180n"][d, a] for d in ok180)
    return dict(months=len(ok), of=len(ds), mean=n / len(ok) if ok else None, pm=n,
                p90=100 * g90 / n if n else None, p180=100 * g180 / n180 if n180 else None)


R = {}
for a in AREAS:
    r = {}
    for y in YEARS:
        l, m = ytd("lah_ytd", a, y); k, _ = ytd("lah_kasitelty_ytd", a, y); g, _ = ytd("lah_gt21n", a, y)
        py = "2025" if y == "2026" else y
        r[y] = dict(lah=l, lah_month=m, gt21=(100 * g / k if k else None), arv=stock(a, "arv", [y]), hoito=stock(a, "hoito", [y]),
                    per1000=(1000 * l / pop(a, py) if l is not None and pop(a, py) else None))
    r["poolA"] = stock(a, "arv", YEARS); r["poolH"] = stock(a, "hoito", YEARS)
    R[a] = r

# ---- cancer deaths ---------------------------------------------------------------------------------------------
X = {}
for a in AREAS:
    if not MAP[a]: continue
    dd = {y: dsum(a, "04-21", y) for y in ("2023", "2024", "2025")}
    pp = {y: pop(a, y) for y in dd}
    X[a] = dict(d=dd, pop25=pp["2025"], rate=1e5 * sum(dd.values()) / sum(pp.values()), p65=p65(a, "2025"),
                share_all=100 * sum(dd.values()) / sum(dsum(a, "SSS", y) for y in dd))
natX = X[NAT]
# regression of crude cancer death rate on 65+ share across the 19 real areas (HUS merged; Kainuu included)
reg = [a for a in X if a != NAT]
mx = sum(X[a]["p65"] for a in reg) / len(reg); my = sum(X[a]["rate"] for a in reg) / len(reg)
slope = sum((X[a]["p65"] - mx) * (X[a]["rate"] - my) for a in reg) / sum((X[a]["p65"] - mx) ** 2 for a in reg)
icpt = my - slope * mx
res = {a: X[a]["rate"] - (icpt + slope * X[a]["p65"]) for a in reg}
sd = (sum(v * v for v in res.values()) / (len(reg) - 2)) ** 0.5
r2 = 1 - sum(v * v for v in res.values()) / sum((X[a]["rate"] - my) ** 2 for a in reg)

# ---- flags -----------------------------------------------------------------------------------------------------
nH, nA = R[NAT]["poolH"], R[NAT]["poolA"]
def wait_flag(p, nat, name):
    if p["months"] < 12: return "no usable data" if p["months"] == 0 else f"too sparse ({p['months']} mo)"
    if p["p90"] is not None and p["p90"] >= 2 * nat["p90"]:
        return "LONG" if p["pm"] >= 100 else "long? (tiny queue)"
    return ""
def persist(a, key):
    c = 0
    for y in YEARS:
        s, n = R[a][y][key], R[NAT][y][key]
        if s["months"] >= 6 and s["p90"] is not None and s["p90"] >= 2 * max(n["p90"], 1.0): c += 1
    return c
F = {}
for a in AREAS:
    if a == NAT: continue
    f = dict(H=wait_flag(R[a]["poolH"], nH, "H"), A=wait_flag(R[a]["poolA"], nA, "A"), pH=persist(a, "hoito"), pA=persist(a, "arv"))
    l25 = R[a]["2025"]["per1000"]; nat25 = R[NAT]["2025"]["per1000"]
    f["V"] = "" if l25 is None else ("HIGH" if l25 >= 1.5 * nat25 else ("LOW (under-reporting?)" if l25 <= 0.5 * nat25 else ""))
    if a in X:
        f["R"] = "HIGH" if X[a]["rate"] >= 1.15 * natX["rate"] else ""
        f["RA"] = "above" if res[a] > sd else ("below" if res[a] < -sd else "")
    F[a] = f
big_queue = sorted((a for a in AREAS if a != NAT and R[a]["poolH"]["mean"] is not None),
                   key=lambda a: -((R[a]["poolH"]["mean"] or 0) + (R[a]["poolA"]["mean"] or 0)))[:3]
big_deaths = sorted(X, key=lambda a: -sum(X[a]["d"].values()) if a != NAT else 1)[:3]


# ---- Spearman with permutation p -------------------------------------------------------------------------------
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r
def spearman(x, y):
    rx, ry = rank(x), rank(y); n = len(x); mx_, my_ = sum(rx) / n, sum(ry) / n
    return sum((a - mx_) * (b - my_) for a, b in zip(rx, ry)) / (sum((a - mx_) ** 2 for a in rx) * sum((b - my_) ** 2 for b in ry)) ** .5
def perm_p(x, y, n=20000, seed=1):
    rnd = random.Random(seed); obs = abs(spearman(x, y)); yy = list(y); c = 0
    for _ in range(n):
        rnd.shuffle(yy); c += abs(spearman(x, yy)) >= obs - 1e-12
    return (c + 1) / (n + 1)
corr = []
def add(label, getx, gety):
    ar = [a for a in reg if getx(a) is not None and gety(a) is not None]
    if len(ar) >= 6:
        x = [getx(a) for a in ar]; y = [gety(a) for a in ar]; corr.append((label, len(ar), spearman(x, y), perm_p(x, y)))
rate = lambda a: X[a]["rate"]
for lab, gx in [("Treatment queue >90 d share (pooled)", lambda a: R[a]["poolH"]["p90"] if R[a]["poolH"]["months"] >= 12 else None),
                ("Assessment queue >90 d share (pooled)", lambda a: R[a]["poolA"]["p90"] if R[a]["poolA"]["months"] >= 12 else None),
                ("Referrals per 1000 residents, 2025", lambda a: R[a]["2025"]["per1000"]),
                ("Mean treatment queue per 100k residents", lambda a: (R[a]["poolH"]["mean"] / pop(a, "2025") * 1e5) if R[a]["poolH"]["months"] >= 12 else None)]:
    add(lab + " vs crude cancer death rate", gx, rate)
    add(lab + " vs death rate beyond age structure", gx, lambda a: res[a])

# ---- write CSV ---------------------------------------------------------------------------------------------------
fmt = lambda v, n=1: "" if v is None else (f"{v:.{n}f}")
with open(OUT / "wait_times_syopataudit_2023_2026.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["area", "year", "referrals_ytd_at_year_end", "referrals_month_used", "referrals_per_1000", "pct_referrals_processed_over_21d",
                "assess_queue_mean", "assess_months_reported", "assess_pct_over90d", "assess_pct_over180d",
                "treat_queue_mean", "treat_months_reported", "treat_pct_over90d", "treat_pct_over180d"])
    for a in AREAS:
        for y in YEARS:
            q = R[a][y]
            w.writerow([a, y + (" (Jan-Sep)" if y == "2026" else ""), fmt(q["lah"], 0), q["lah_month"] or "", fmt(q["per1000"]), fmt(q["gt21"]),
                        fmt(q["arv"]["mean"]), q["arv"]["months"], fmt(q["arv"]["p90"]), fmt(q["arv"]["p180"]),
                        fmt(q["hoito"]["mean"]), q["hoito"]["months"], fmt(q["hoito"]["p90"]), fmt(q["hoito"]["p180"])])

# ---- write Markdown ----------------------------------------------------------------------------------------------
short = lambda a: a.replace(" hyvinvointialue", "").replace("Helsingin sosiaali-, terveys- ja pelastustoimi", "Helsinki (city)")
L = []
L += ["# Cancer care (Syöpätaudit) waits, referrals and cancer deaths by welfare area, 2023 to Sep 2026", "",
      f"Generated by `wait_times_syopataudit.py`. THL data last month: {last_date}. Deaths and population: Statistics Finland, latest year 2025.", "",
      "**What this is.** THL's specialised-care queue statistics for the oncology specialty only (65 Syöpätaudit), by the provider that reports them, "
      "set against Statistics Finland cancer deaths (ICD-10 C00-C97) by residence. Read the caveats at the end before using any flag.", "",
      "## 1. Per welfare area and year", "",
      "Referrals = lähetteet, cumulative from 1 Jan, taken at the last month of the year (2026 = to Sep). Queues are month-end stocks, averaged over the months the area reported "
      "(count of months in brackets). Shares are patient-weighted over those months. 'Assess' = waiting for hoidon tarpeen arviointi; 'Treat' = waiting for hoito (hoitoon pääsy).", "",
      "| Area | Year | Referrals | per 1000 | Referrals processed >21 d % | Assess queue (mo) | Assess >90 d % | Treat queue (mo) | Treat >90 d % | Treat >180 d % |",
      "|---|---|--:|--:|--:|--:|--:|--:|--:|--:|"]
for a in AREAS:
    for y in YEARS:
        q = R[a][y]
        L.append(f"| {short(a)} | {y}{' (Jan-Sep)' if y == '2026' else ''} | {fmt(q['lah'], 0) or '–'} | {fmt(q['per1000']) or '–'} | {fmt(q['gt21']) or '–'} | "
                 f"{fmt(q['arv']['mean'], 0) or '–'} ({q['arv']['months']}) | {fmt(q['arv']['p90'], 0) or '–'} | "
                 f"{fmt(q['hoito']['mean'], 0) or '–'} ({q['hoito']['months']}) | {fmt(q['hoito']['p90'], 0) or '–'} | {fmt(q['hoito']['p180'], 0) or '–'} |")
L += ["", "## 2. Flags and cross-reference with cancer deaths", "",
      f"National pooled >90-day share: treatment {nH['p90']:.1f}%, assessment {nA['p90']:.1f}% (2023-01 to {last_date[3:]}). "
      f"National crude cancer death rate 2023-25: {natX['rate']:.0f} per 100,000. Linear fit of crude rate on the 65+ share across the 19 areas: R² = {r2:.2f}, "
      f"residual SD = {sd:.0f}.", "",
      "| Area | Cancer deaths 2023 / 24 / 25 | Rate /100k | 65+ % | Rate vs age structure | Treat >90 d % (pooled) | Treat flag | Assess >90 d % (pooled) | Assess flag | Referrals /1000 (2025) | Volume flag |",
      "|---|---|--:|--:|---|--:|---|--:|---|--:|---|"]
for a in AREAS:
    if a == NAT: continue
    f = F[a]; x = X.get(a)
    th = R[a]["poolH"]; ta = R[a]["poolA"]
    def pf(flag, per): return (flag + (f" ({per} of 4 yrs)" if flag.startswith(("LONG", "long")) and per else "")) or "–"
    L.append(f"| {short(a)} | {' / '.join(str(x['d'][y]) for y in ('2023', '2024', '2025')) if x else '–'} | {f'{x['rate']:.0f}' + (' **HIGH**' if f.get('R') else '') if x else '–'} | "
             f"{f'{x['p65']:.1f}' if x else '–'} | {(f.get('RA') or 'in line') if x else '–'} | {fmt(th['p90']) or '–'} | {pf(f['H'], f['pH'])} | {fmt(ta['p90']) or '–'} | {pf(f['A'], f['pA'])} | "
             f"{fmt(R[a]['2025']['per1000']) or '–'} | {f['V'] or '–'}{' / LARGE QUEUE' if a in big_queue else ''}{' / LARGE CASELOAD (deaths)' if a in big_deaths else ''} |")
L += ["", "Flag rules (set before reading the results):",
      "- **LONG**: pooled share waiting >90 days is at least 2× the national pooled share, with at least 12 reported months and at least 100 patient-months. "
      "'long? (tiny queue)' = same ratio but fewer than 100 patient-months, so one or two patients move it. '(n of 4 yrs)' = calendar years in which the area was at least 2× the national share that year (≥6 reported months).",
      "- **Referral volume HIGH / LOW**: 2025 referrals per 1000 residents at least 1.5× or at most 0.5× the national figure.",
      "- **LARGE QUEUE**: three largest mean (assessment + treatment) queues. **LARGE CASELOAD**: three highest cancer death counts.",
      "- **Death rate HIGH**: crude rate at least 1.15× national. **Rate vs age structure**: above or below the 19-area regression line by more than one residual SD.",
      "", "## 3. Does a long wait go with more cancer deaths?", "",
      "Spearman rank correlation across areas (permutation p-value, 20,000 shuffles). Areas with fewer than 12 reported months for a measure are left out of that row.", "",
      "| Comparison | Areas | Spearman ρ | p |", "|---|--:|--:|--:|"]
for lab, n, rho, p in corr: L.append(f"| {lab} | {n} | {rho:+.2f} | {p:.2f} |")
L += ["", "## 4. Caveats and data quality", "",
      "1. **Specialty, not all cancer.** The queue data cover patients of the oncology specialty (radiotherapy, medical oncology). Cancer surgery sits in other specialties and is not here. Deaths cover all cancers.",
      "2. **Referral counts are not comparable across areas.** Per 1000 residents they range from under 1 (HUS, Pohjois-Karjala) to over 12 (Pohjanmaa) with similar cancer death rates, and some areas jump between years "
      "(Pirkanmaa 821 to 2,997; Etelä-Karjala 539 to 1,261; Kanta-Häme 772, 1,432, 823). That looks like differences in how referrals are registered, not in demand. Treat volume flags as a data-quality signal first.",
      "3. **Queues are tiny and noisy.** National treatment queue averages about 600 patients, half of them in HUS. Most areas have 2-25 patients in the queue, so a share like 17% means one or two people.",
      "4. **Missing data.** Kainuu and Helsinki city report nothing for this specialty (Helsinki residents are served by HUS: HUS population in THL, 1.76M, matches Uusimaa's four areas plus Helsinki). "
      "Assessment-queue data is missing for most months in Etelä-Karjala, Etelä-Savo, Keski-Pohjanmaa and most of Kymenlaakso, Keski-Suomi, Pohjanmaa and Varsinais-Suomi. "
      "Cells are blank in the THL export; I cannot tell whether blank means zero, suppressed or not reported.",
      "5. **Provider is not residence.** Queues are by the reporting provider, deaths by where the person lived. For HUS I summed Uusimaa's four areas and Helsinki; some areas buy care from others.",
      "6. **Deaths are not an outcome of these waits.** Cancer deaths in 2023-25 reflect diagnoses years earlier, age structure and cancer type. Crude rates are driven by age: the 65+ share explains much of the spread. Åland is excluded.",
      "7. **Correlations are across 15-19 areas, ecological and mostly not distinguishable from chance.** They show where to look, not cause.",
      "8. **Definitions** (what counts as a referral, when a queue clock starts) come from THL's cube measure names. I did not read THL's technical documentation for them.", "",
      "## 5. Reproduce", "",
      "`python3 wait_times_syopataudit.py CACHE_DIR OUT_DIR`. THL: `fact_eshjono_jonotilanne.csv?row=tuottaja-976329&column=ajankohta-976319&filter=measure-<id>&filter=erikoisala-862186` "
      "for measures " + ", ".join(f"{n}={m}" for m, n in MEASURES.items()) + ". StatFin tables `ksyyt/13u5` and `vaerak/11ra`."]
(OUT / "wait_times_syopataudit_2023_2026.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# ---- console summary ---------------------------------------------------------------------------------------------
print("big_queue", big_queue, "big_deaths", big_deaths, "r2", round(r2, 2), "sd", round(sd))
for a in AREAS:
    if a == NAT: continue
    print(short(a).ljust(22), F[a], (round(X[a]["rate"]), round(X[a]["p65"], 1), round(res[a])) if a in X else "")
for c in corr: print(c)
print("HUS pop 2023", pop("HUS", "2023"))
