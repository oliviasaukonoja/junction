"""Keuhkodata AI analyst: an agent that analyses the open data itself, with tools, and whose numbers are checked.

How it works
- All region data (Statistics Finland SMR, THL smoking, the risk-group estimate, Cancer Registry screening participation,
  THL oncology waits, the Polku Labs pilot model) is loaded into one table of facts. Every value has an id and a source.
- Claude answers a decision-maker's question by calling tools over that table (rank regions, open a profile, compare,
  read the pilot model) and ends with a structured answer: findings that each cite fact ids, regions to highlight.
- Every number in a finding is checked against the facts the tools returned. A finding passes only if all its numbers
  are found there (rounding allowed). The page shows the check next to each finding.
- Without an API key (or if the API fails) the same tools run a fixed rule set for the preset questions, labelled
  "rule-based", so the page never depends on the API being up.
"""
from __future__ import annotations

import json
import re
import time

SIG_WORDS = {"hi": "significantly above national", "lo": "significantly below national", "ns": "not significantly different"}


def _num(x, nd=1):
    return None if x is None else round(float(x), nd)


class Data:
    def __init__(self, data_page: str, pilot_map: dict):
        i = data_page.index("const D = ") + len("const D = ")
        D, _ = json.JSONDecoder().raw_decode(data_page[i:])
        self.D, self.P = D, pilot_map
        names = D["names"]
        self.nom = {}
        m = re.search(r"const NOM=\{(.*?)\};", data_page)
        if m:
            for lg, body in re.findall(r"(\w+):\{([^}]*)\}", m.group(1)):
                self.nom[lg] = dict(re.findall(r"(HVA\d+):'([^']*)'", body))
        smoke = {r[0]: r[1] for r in D["smoke_reg"]}
        risk = {r[0]: r for r in D["risk"]}
        scr = {r[0]: r for r in D["scr_county"]}
        nom = {"HVA21": "Lapland", "HVA10": "Kymenlaakso", "HVA06": "Satakunta"}
        order = sorted(D["smr"], key=lambda r: -r[1])
        self.regions = {}
        for rank, r in enumerate(order, 1):
            c = r[0]
            en = nom.get(c) or names[c]["en"]
            sig = "hi" if r[2] > 1 else "lo" if r[3] < 1 else "ns"
            p = {
                "code": c, "name": en, "name_fi": names[c]["fi"], "name_sv": names[c]["sv"],
                "smr": r[1], "smr_lo": r[2], "smr_hi": r[3], "deaths_2021_2025": r[4], "expected_2021_2025": round(r[5]),
                "excess_deaths_5y": round(r[4] - r[5]), "excess_pct": round((r[1] - 1) * 100), "significance": SIG_WORDS[sig],
                "smr_rank": rank,
            }
            if c in smoke:
                p["daily_smokers_pct"] = smoke[c]
            if c in risk:
                p["risk_group_people"] = risk[c][1]
                p["pop_50_74"] = risk[c][2]
                p["risk_group_pct"] = round(risk[c][1] / risk[c][2] * 100, 1)
                p["ct_towns"] = risk[c][6]
            if c in scr:
                p["screening_breast_pct"], p["screening_colorectal_pct"], p["screening_cervical_pct"] = scr[c][1], scr[c][2], scr[c][3]
            pc = (pilot_map.get("counties") or {}).get(c)
            if pc:
                t = pc["bus"]["totals"]
                far = round(t["additional_far"] / t["additional"] * 100) if t.get("additional") else None
                p["pilot"] = {
                    "verdict": "bus pilot" if far is not None and far >= 25 else "hospital-CT invitations first",
                    "extra_participants_per_year": t["additional"], "share_of_extra_living_far_pct": far,
                    "coverage_hospital_ct_only_pct": round(t["coverage_hospital_only"] * 100),
                    "coverage_with_bus_pct": round(t["coverage_with_bus"] * 100),
                    "cost_per_extra_participant_eur": t["cost_per_additional_eur"], "bus_stops": t["stops"],
                }
                waits = [w for w in pc["facts"].get("oncology_waits", []) if w.get("assess_over90") is not None and w.get("assess_months", 0) >= 9]
                if waits:
                    w = waits[-1]
                    p["oncology_waits"] = {"period": w["year"], "assessment_over_90d_pct": w["assess_over90"], "treatment_over_90d_pct": w["treat_over90"]}
            else:
                p["pilot"] = None
            self.regions[c] = p
        self.national = {
            "smr": 1.0, "daily_smokers_pct": D["smoke_fi"], "risk_group_people": D["risk_nat"],
            "screening_breast_pct": D["scr_nat"]["breast"], "screening_colorectal_pct": D["scr_nat"]["colorectal"],
            "days_symptom_to_treatment_finland": 155, "days_symptom_to_treatment_denmark": 67, "days_symptom_to_treatment_sweden": 107,
            "patient_delay_days": 50, "primary_care_days": 41, "specialist_days": 58,
            "men_incidence_basic_vs_higher_education": 2.7, "men_5y_survival_finland_pct": D["nordsurv"]["men"]["Finland"],
            "men_5y_survival_norway_pct": D["nordsurv"]["men"]["Norway"],
            "screening_gap_other_language_points": round(D["scr_lang"]["breast"]["Domestic"] - D["scr_lang"]["breast"]["Other/missing"], 1),
            "uk_lung_checks_cancers_found": 5000, "uk_lung_checks_early_stage_pct": 76,
        }
        self.sources = {
            "smr": "Polku Labs calculation from Statistics Finland tables 13u5, 11az, 11s1 (2021–2025)",
            "excess": "Polku Labs calculation from Statistics Finland tables 13u5, 11az, 11s1 (2021–2025)",
            "deaths": "Statistics Finland, causes of death 2021–2025",
            "smoke": "THL Sotkanet (indicators 4408–4410)",
            "risk": "Polku Labs estimate: THL Sotkanet 4405/4406 × assumed factor 0.8 (assumption)",
            "scr": "Finnish Cancer Registry screening statistics 2024",
            "pilot": "Polku Labs pilot map (modelled; OSRM travel times; assumptions)",
            "waits": "THL access to specialist care, oncology (all cancers) 2023–2026",
            "path": "Yle MOT 2026 (Kuittinen et al., unpublished)",
            "edu": "Finnish Cancer Registry, Cancer 2022 (National Lung Cancer Programme 2026–2035)",
            "surv": "IHE Cancer Dashboard Finland 2026 via team notes",
            "uk": "NHS England / GOV.UK 2023",
        }

    # ---------- tools ----------
    INDICATORS = {
        "smr": ("smr", "smr"), "excess_deaths": ("excess_deaths_5y", "excess"), "daily_smokers": ("daily_smokers_pct", "smoke"),
        "risk_group_share": ("risk_group_pct", "risk"), "risk_group_people": ("risk_group_people", "risk"),
        "screening_breast": ("screening_breast_pct", "scr"), "screening_colorectal": ("screening_colorectal_pct", "scr"),
    }

    def rank_regions(self, indicator: str, highest_first: bool = True, limit: int = 8):
        if indicator not in self.INDICATORS:
            return {"error": f"unknown indicator; use one of {list(self.INDICATORS)}"}
        key, s = self.INDICATORS[indicator]
        rows = [(c, p[key]) for c, p in self.regions.items() if p.get(key) is not None]
        rows.sort(key=lambda x: x[1], reverse=highest_first)
        nat = {"smr": 1.0, "daily_smokers_pct": self.national["daily_smokers_pct"], "screening_breast_pct": self.national["screening_breast_pct"],
               "screening_colorectal_pct": self.national["screening_colorectal_pct"]}.get(key)
        out = [{"code": c, "name": self.regions[c]["name"], key: v, "significance": self.regions[c]["significance"]} if key == "smr"
               else {"code": c, "name": self.regions[c]["name"], key: v} for c, v in rows[: max(1, min(int(limit), 22))]]
        return {"indicator": indicator, "regions_compared": len(rows), "national": nat, "top": out, "source": self.sources[s]}

    def region_profile(self, code: str):
        p = self.regions.get(code)
        if not p:
            return {"error": "unknown region code"}
        return {**p, "sources": {k: self.sources[k] for k in ("smr", "smoke", "risk", "scr", "pilot", "waits")}}

    def compare_regions(self, codes: list):
        return {"regions": [self.region_profile(c) for c in codes[:5]]}

    def national_facts(self):
        return {**self.national, "sources": {k: self.sources[k] for k in ("path", "edu", "surv", "scr", "smoke", "uk")}}

    def run_tool(self, name, args):
        if name == "rank_regions":
            return self.rank_regions(args.get("indicator", "smr"), bool(args.get("highest_first", True)), args.get("limit", 8))
        if name == "region_profile":
            return self.region_profile(args.get("code", ""))
        if name == "compare_regions":
            return self.compare_regions(args.get("codes") or [])
        if name == "national_facts":
            return self.national_facts()
        return {"error": "unknown tool"}

    def codes_text(self):
        return ", ".join(f"{c} {p['name']}" for c, p in self.regions.items())


TOOLS = [
    {"name": "rank_regions", "description": "Rank all wellbeing services counties by one indicator. Returns the national value and the top regions with values. Indicators: smr (lung cancer deaths vs. age structure, 2021–2025, with significance), excess_deaths (deaths minus expected, 5 years), daily_smokers (%), risk_group_share (% of 50–74 estimated in the screening risk group; an assumption-based estimate), risk_group_people, screening_breast (% participation 2024), screening_colorectal.",
     "input_schema": {"type": "object", "properties": {"indicator": {"type": "string"}, "highest_first": {"type": "boolean"}, "limit": {"type": "integer"}}, "required": ["indicator"]}},
    {"name": "region_profile", "description": "Everything known about one region: SMR with 95% CI, deaths vs expected, smoking, estimated risk group, screening participation, CT towns, oncology waiting times (only for the three pilot regions), and the Polku Labs pilot model results (only Lapland HVA21, Kymenlaakso HVA10, Satakunta HVA06).",
     "input_schema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
    {"name": "compare_regions", "description": "Profiles of up to 5 regions side by side.",
     "input_schema": {"type": "object", "properties": {"codes": {"type": "array", "items": {"type": "string"}}}, "required": ["codes"]}},
    {"name": "national_facts", "description": "National context: days from symptoms to treatment (Finland 155, split patient/primary/specialist; Denmark 67), education gap, survival vs Norway, screening gap by language, UK lung health checks. These are national, not regional.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "final_answer", "description": "Finish. Give the answer for a non-technical decision-maker.",
     "input_schema": {"type": "object", "properties": {
         "answer": {"type": "string", "description": "2–3 plain sentences, the direct answer."},
         "findings": {"type": "array", "items": {"type": "object", "properties": {
             "text": {"type": "string", "description": "One finding, with its numbers exactly as the tools returned them (rounding allowed)."},
             "source": {"type": "string", "description": "The source label the tool returned for these numbers."}}, "required": ["text", "source"]}},
         "highlight": {"type": "array", "items": {"type": "string"}, "description": "Region codes to light up on the map, most important first (max 4)."},
         "select": {"type": "string", "description": "One region code to open in the brief, or empty."},
         "unknowns": {"type": "array", "items": {"type": "string"}, "description": "What the data cannot tell, briefly."}},
         "required": ["answer", "findings", "highlight"]}},
]

SYSTEM = """You are the analyst inside Keuhkodata, a lung cancer dashboard for Finnish wellbeing services counties.
You analyse the data yourself with the tools; never answer from memory. Typical work: rank all regions on the relevant indicators,
open the profiles of the strongest candidates, compare, then call final_answer.
Rules:
- Every number you write must come from a tool result (rounding allowed). No other numbers, no effect sizes, no costs that the tools did not return.
- Say "modelled" for pilot-model figures and "estimate" for the risk group. Say when a figure is national, not regional.
- SMR differences only count as a gap if the significance says "significantly above/below".
- Recommendations are the Polku Labs team's: bus pilot in Lapland (distance is the barrier), hospital-CT invitations first in Kymenlaakso and Satakunta. For other regions the team makes no recommendation; say so. You explain the evidence; you do not invent new actions.
- No advice about individual patients. Plain language. Answer in {language}.
Region codes: {codes}."""


# ---------- number check ----------
NUM = re.compile(r"(?<![\w.,])[−-]?\d{1,3}(?:[ \u00a0,]\d{3})+(?:\.\d+)?(?!\d)|(?<![\w.,])[−-]?\d+(?:[.,]\d+)?")


def _norm(tok: str):
    t = tok.replace(" ", "").replace(" ", "").replace("−", "-")
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t):          # 1,291
        t = t.replace(",", "")
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _collect(o, out):
    if isinstance(o, bool):
        return
    if isinstance(o, (int, float)):
        out.add(round(float(o), 2))
    elif isinstance(o, dict):
        for v in o.values():
            _collect(v, out)
    elif isinstance(o, (list, tuple)):
        for v in o:
            _collect(v, out)
    elif isinstance(o, str):
        for m in NUM.finditer(o):
            v = _norm(m.group(0))
            if v is not None:
                out.add(round(v, 2))


def allowed_numbers(results):
    base = set()
    _collect(results, base)
    ok = set(base)
    for v in base:
        ok.update({round(v), round(v, 1), round(v * 100), round(v * 100, 1), round((v - 1) * 100), round(abs((v - 1) * 100))})
    ok.update({2021, 2022, 2023, 2024, 2025, 2026, 2019, 50, 74, 95, 1, 2, 3, 4, 5, 1.0, 0})   # years, age band, list counts
    return ok


def check_text(text, ok):
    bad = []
    for m in NUM.finditer(text):
        v = _norm(m.group(0))
        if v is None:
            continue
        if not any(abs(v - a) <= 0.051 for a in ok):
            bad.append(m.group(0).strip())
    return bad


# ---------- agent ----------
def run_agent(data: Data, question: str, lang: str, api_key: str, post, model: str, region_hint: str | None = None):
    """post(url, headers, json, timeout) -> response with .status_code and .json(). Returns the answer dict or raises."""
    t0 = time.time()
    language = {"fi": "Finnish", "sv": "Swedish", "en": "English"}.get(lang, "English")
    system = SYSTEM.replace("{language}", language).replace("{codes}", data.codes_text())
    q = question if not region_hint else f"{question}\n(The user is looking at region {region_hint}.)"
    msgs = [{"role": "user", "content": q}]
    steps, results = [], []
    for _ in range(8):
        r = post("https://api.anthropic.com/v1/messages",
                 headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                 json={"model": model, "max_tokens": 2000, "system": system, "tools": TOOLS, "messages": msgs}, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"api {r.status_code}")
        body = r.json()
        blocks = body.get("content", [])
        msgs.append({"role": "assistant", "content": blocks})
        uses = [b for b in blocks if b.get("type") == "tool_use"]
        if not uses:
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
            return finish(data, {"answer": text, "findings": [], "highlight": []}, steps, results, t0, "ai")
        replies = []
        for u in uses:
            if u["name"] == "final_answer":
                return finish(data, u.get("input") or {}, steps, results, t0, "ai")
            res = data.run_tool(u["name"], u.get("input") or {})
            results.append(res)
            steps.append(describe(u["name"], u.get("input") or {}, res, data))
            replies.append({"type": "tool_result", "tool_use_id": u["id"], "content": json.dumps(res, ensure_ascii=False)})
        msgs.append({"role": "user", "content": replies})
    raise RuntimeError("no final answer")


def describe(name, args, res, data):
    if name == "rank_regions":
        return {"tool": name, "label": f"Ranked {res.get('regions_compared', 22)} regions by {args.get('indicator')}", "n": res.get("regions_compared", 0), "ind": args.get("indicator")}
    if name == "region_profile":
        return {"tool": name, "label": f"Opened profile: {data.regions.get(args.get('code'), {}).get('name', args.get('code'))}", "n": 1, "codes": [args.get("code")]}
    if name == "compare_regions":
        return {"tool": name, "label": "Compared " + ", ".join(data.regions.get(c, {}).get("name", c) for c in (args.get("codes") or [])), "n": len(args.get("codes") or []), "codes": list(args.get("codes") or [])}
    return {"tool": name, "label": "Read national context", "n": 1}


def finish(data, ans, steps, results, t0, mode):
    ok = allowed_numbers(results + [data.national])
    findings = []
    for f in ans.get("findings") or []:
        txt = str(f.get("text", "")).strip()
        if not txt:
            continue
        bad = check_text(txt, ok)
        findings.append({"text": txt, "source": str(f.get("source", "")), "verified": not bad, "unverified": bad})
    a_bad = check_text(str(ans.get("answer", "")), ok)
    hl = [c for c in (ans.get("highlight") or []) if c in data.regions][:4]
    sel = ans.get("select") if ans.get("select") in data.regions else (hl[0] if hl else None)
    nums = sum(len(NUM.findall(f["text"])) for f in findings)
    return {"mode": mode, "answer": str(ans.get("answer", "")).strip(), "answer_verified": not a_bad, "answer_unverified": a_bad,
            "findings": findings, "highlight": hl, "select": sel, "unknowns": [str(u) for u in (ans.get("unknowns") or [])][:4],
            "steps": steps, "seconds": round(time.time() - t0, 1), "numbers_checked": nums + len(NUM.findall(str(ans.get("answer", ""))))}


# ---------- rule-based fallback for the preset questions ----------
PRESETS = ["first_pilot", "distance", "smoking_mortality", "screening_reach"]

L10N = {
    "en": {
        "first_pilot": ("Lapland first: it has the highest significantly raised lung cancer mortality, and the pilot model shows distance is its barrier, so a bus pilot. Kymenlaakso and Satakunta are also significantly raised, but almost everyone there lives near a CT, so hospital-CT invitations come first.",
                        ["lung cancer pathway times by region are not published.", "real uptake of a lung CT invitation in Finland; the pilot measures it."]),
        "distance": ("Only Lapland: in the pilot model {lfar}% of the extra people a bus would reach live far from a CT, against {kfar}% in Kymenlaakso and {sfar}% in Satakunta.",
                     ["Travel times are modelled without winter conditions.", "Other regions are not modelled yet."]),
        "smoking_mortality": ("These regions have both significantly raised mortality and more daily smokers than the national {nat}%:",
                              ["Smoking is all adults, not only the 50–74 risk group.", "The risk group is an estimate (assumed factor)."]),
        "screening_reach": ("Breast screening participation is lowest in these regions (national {nat}%). Lung CT screening does not exist yet, so this shows where other screening reaches people worst:",
                            ["Lung CT uptake may differ from breast screening.", "Language and education gaps are national figures."]),
    },
    "fi": {
        "first_pilot": ("Lappi ensin: siellä keuhkosyöpäkuolleisuus on eniten ja merkitsevästi koholla, ja pilottimallin mukaan este on etäisyys, joten bussipilotti. Kymenlaakso ja Satakunta ovat myös merkitsevästi koholla, mutta lähes kaikki asuvat TT-laitteen lähellä, joten ensin sairaalan TT-kutsut.",
                        ["keuhkosyövän hoitopolun aikoja ei julkaista alueittain.", "kuinka moni Suomessa vastaa TT-kutsuun; pilotti mittaa sen."]),
        "distance": ("Vain Lapissa: pilottimallissa {lfar} % bussin tavoittamista lisäosallistujista asuu kaukana TT-laitteesta, Kymenlaaksossa {kfar} % ja Satakunnassa {sfar} %.",
                     ["Matka-ajat on mallinnettu ilman talviolosuhteita.", "Muita alueita ei ole vielä mallinnettu."]),
        "smoking_mortality": ("Näillä alueilla kuolleisuus on merkitsevästi koholla ja päivittäin tupakoivia on enemmän kuin koko maassa ({nat} %):",
                              ["Tupakointi koskee kaikkia aikuisia, ei vain 50–74-vuotiaita.", "Riskiryhmä on arvio (oletettu kerroin)."]),
        "screening_reach": ("Rintasyöpäseulontaan osallistutaan vähiten näillä alueilla (koko maa {nat} %). Keuhkojen TT-seulontaa ei vielä ole, joten tämä kertoo, missä muut seulonnat tavoittavat huonoiten:",
                            ["Keuhko-TT:n osallistuminen voi poiketa rintasyöpäseulonnasta.", "Kieli- ja koulutuserot ovat koko maan lukuja."]),
    },
    "sv": {
        "first_pilot": ("Lappland först: där är lungcancerdödligheten högst och signifikant förhöjd, och pilotmodellen visar att avståndet är hindret, alltså en busspilot. Kymmenedalen och Satakunta är också signifikant förhöjda, men nästan alla bor nära en DT, så inbjudningar till sjukhusets DT kommer först.",
                        ["tider i lungcancerns vårdkedja publiceras inte per område.", "hur många i Finland som tackar ja till en DT-inbjudan; piloten mäter det."]),
        "distance": ("Bara i Lappland: i pilotmodellen bor {lfar} % av bussens extra deltagare långt från en DT, mot {kfar} % i Kymmenedalen och {sfar} % i Satakunta.",
                     ["Restiderna är modellerade utan vinterförhållanden.", "Andra områden är inte modellerade ännu."]),
        "smoking_mortality": ("I dessa områden är dödligheten signifikant förhöjd och andelen dagligrökare högre än i hela landet ({nat} %):",
                              ["Rökningen gäller alla vuxna, inte bara 50–74-åringar.", "Riskgruppen är en uppskattning (antagen faktor)."]),
        "screening_reach": ("Deltagandet i bröstcancerscreening är lägst i dessa områden (hela landet {nat} %). DT-screening av lungorna finns ännu inte, så detta visar var annan screening når sämst:",
                            ["Deltagandet i lung-DT kan skilja sig från bröstscreening.", "Skillnaderna efter språk och utbildning är nationella siffror."]),
    },
}


def run_rules(data: Data, preset: str, lang: str):
    t0 = time.time()
    L = L10N.get(lang, L10N["en"])
    steps, results = [], []

    def tool(name, args):
        res = data.run_tool(name, args)
        results.append(res)
        steps.append(describe(name, args, res, data))
        return res

    def nm(c):
        return (data.nom.get(lang) or {}).get(c) or data.regions[c]["name"]
    F = []
    if preset == "first_pilot":
        rk = tool("rank_regions", {"indicator": "smr", "limit": 6})
        sig = [r["code"] for r in rk["top"] if r["significance"].startswith("significantly above")]
        for c in ("HVA21", "HVA10", "HVA06"):
            p = tool("region_profile", {"code": c})["pilot"]
            r = data.regions[c]
            F.append({"text": f"{nm(c)}: SMR {r['smr']} ({r['smr_lo']}–{r['smr_hi']}); {p['share_of_extra_living_far_pct']}% of the bus's extra participants live far from a CT (modelled); {p['verdict']}.",
                      "source": data.sources["smr"] + " · " + data.sources["pilot"]})
        ans, unk, hl = L["first_pilot"][0], L["first_pilot"][1], ["HVA21", "HVA10", "HVA06"]
        if "HVA01" in sig:
            r = data.regions["HVA01"]
            F.append({"text": f"{nm('HVA01')}: SMR {r['smr']} ({r['smr_lo']}–{r['smr_hi']}), also significantly raised; not in the pilot model yet, so no recommendation.", "source": data.sources["smr"]})
    elif preset == "distance":
        P = {c: tool("region_profile", {"code": c})["pilot"] for c in ("HVA21", "HVA10", "HVA06")}
        ans = L["distance"][0].format(lfar=P["HVA21"]["share_of_extra_living_far_pct"], kfar=P["HVA10"]["share_of_extra_living_far_pct"], sfar=P["HVA06"]["share_of_extra_living_far_pct"])
        for c, p in P.items():
            F.append({"text": f"{nm(c)}: hospital CT reaches {p['coverage_hospital_ct_only_pct']}% of the risk group's yearly need, with the bus {p['coverage_with_bus_pct']}% (modelled).", "source": data.sources["pilot"]})
        unk, hl = L["distance"][1], ["HVA21"]
    elif preset == "smoking_mortality":
        tool("rank_regions", {"indicator": "smr", "limit": 22})
        sk = tool("rank_regions", {"indicator": "daily_smokers", "limit": 22})
        nat = sk["national"]
        both = [c for c, p in data.regions.items() if p["significance"].startswith("significantly above") and (p.get("daily_smokers_pct") or 0) > nat]
        both.sort(key=lambda c: -data.regions[c]["smr"])
        for c in both:
            r = data.regions[c]
            F.append({"text": f"{nm(c)}: SMR {r['smr']}, daily smokers {r['daily_smokers_pct']}% (national {nat}%).", "source": data.sources["smr"] + " · " + data.sources["smoke"]})
        ans, unk, hl = L["smoking_mortality"][0].format(nat=nat), L["smoking_mortality"][1], both[:4]
    else:
        sc = tool("rank_regions", {"indicator": "screening_breast", "highest_first": False, "limit": 4})
        for r in sc["top"]:
            F.append({"text": f"{nm(r['code'])}: {r['screening_breast_pct']}% breast screening participation.", "source": data.sources["scr"]})
        nf = tool("national_facts", {})
        F.append({"text": f"Nationally, people whose native language is not Finnish, Swedish or Sámi take part about {nf['screening_gap_other_language_points']} points less.", "source": data.sources["scr"]})
        ans, unk, hl = L["screening_reach"][0].format(nat=sc["national"]), L["screening_reach"][1], [r["code"] for r in sc["top"]]
    if lang != "en":   # finding lines carry region names; translate the fixed phrases lightly
        F = [{**f, "text": _tr(f["text"], lang, data)} for f in F]
    out = finish(data, {"answer": ans, "findings": F, "highlight": hl, "unknowns": unk}, steps, results, t0, "rules")
    return out


_TR = {
    "fi": [("significantly raised", "merkitsevästi koholla"), ("of the bus's extra participants live far from a CT (modelled)", "bussin lisäosallistujista asuu kaukana TT-laitteesta (mallinnettu)"),
           ("hospital-CT invitations first", "sairaalan TT-kutsut ensin"), ("bus pilot", "bussipilotti"), ("also ", ""), ("not in the pilot model yet, so no recommendation", "ei vielä pilottimallissa, joten ei suositusta"),
           ("hospital CT reaches", "sairaalan TT tavoittaa"), ("of the risk group's yearly need, with the bus", "riskiryhmän vuositarpeesta, bussin kanssa"), ("(modelled)", "(mallinnettu)"),
           ("daily smokers", "päivittäin tupakoivia"), ("national", "koko maa"), ("breast screening participation", "osallistuu rintasyöpäseulontaan"),
           ("Nationally, people whose native language is not Finnish, Swedish or Sámi take part about", "Koko maassa muuta kuin suomea, ruotsia tai saamea äidinkielenään puhuvat osallistuvat noin"), ("points less", "prosenttiyksikköä harvemmin"),
           ],
    "sv": [("significantly raised", "signifikant förhöjd"), ("of the bus's extra participants live far from a CT (modelled)", "av bussens extra deltagare bor långt från en DT (modellerat)"),
           ("hospital-CT invitations first", "inbjudningar till sjukhusets DT först"), ("bus pilot", "busspilot"), ("also ", "också "), ("not in the pilot model yet, so no recommendation", "inte i pilotmodellen ännu, därför ingen rekommendation"),
           ("hospital CT reaches", "sjukhusets DT når"), ("of the risk group's yearly need, with the bus", "av riskgruppens årliga behov, med bussen"), ("(modelled)", "(modellerat)"),
           ("daily smokers", "dagligrökare"), ("national", "hela landet"), ("breast screening participation", "deltar i bröstcancerscreening"),
           ("Nationally, people whose native language is not Finnish, Swedish or Sámi take part about", "I hela landet deltar personer med annat modersmål än finska, svenska eller samiska cirka"), ("points less", "procentenheter mindre"),
           ],
}


def _tr(text, lang, data):
    for a, b in _TR.get(lang, []):
        text = text.replace(a, b)
    if lang in ("fi", "sv"):
        text = text.replace("% ", " % ").replace("%)", " %)").replace("%,", " %,").replace("%.", " %.")
    return text
