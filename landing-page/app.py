"""Polku hoitoon waitlist: bus page (/) + app page (/sovellus) + professional page (/ammattilaisille) + lung cancer data dashboard (/keuhkodata) + sign-up API on Modal.

Deploy:      modal deploy app.py
Sign-ups:    python signups.py   (reads the Modal Volume with your own Modal login)

There is deliberately no admin page on the website: sign-ups are only
readable by someone logged in to the Modal account.
"""
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

import modal

HERE = Path(__file__).parent

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi[standard]")
    .add_local_file(HERE / "index.html", "/root/index.html")
    .add_local_file(HERE / "sovellus.html", "/root/sovellus.html")
    .add_local_file(HERE / "ammattilaisille.html", "/root/ammattilaisille.html")
    .add_local_file(HERE / "paattajille.html", "/root/paattajille.html")
    .add_local_file(HERE / "tietosuoja.html", "/root/tietosuoja.html")
    .add_local_file(HERE / "meista.html", "/root/meista.html")
    .add_local_file(HERE / "ukk.html", "/root/ukk.html")
    .add_local_file(HERE / "palaute.html", "/root/palaute.html")
    .add_local_file(HERE / "keuhkodata.html", "/root/keuhkodata.html")
    .add_local_file(HERE / "team.jpg", "/root/team.jpg")
    .add_local_file(HERE / "regions.json", "/root/regions.json")
)

app = modal.App("vayla-waitlist")
vol = modal.Volume.from_name("vayla-signups", create_if_missing=True)
DATA = Path("/data/signups.jsonl")
FEEDBACK = Path("/data/feedback.jsonl")

LANGS = {"fi", "sv", "en", "ru", "et", "ar", "so", "uk"}
ELIG = {"yes", "no", "unsure"}
WHO = {"self", "relative"}
AGE = {"yes", "no"}
SMOKE = {"now", "former", "never"}
PRODUCTS = {"bus", "app"}


@app.function(
    image=image,
    volumes={"/data": vol},
    secrets=[modal.Secret.from_name("polku-ai")],  # ANTHROPIC_API_KEY for the AI analyst
    max_containers=1,  # one writer keeps the file consistent
)
@modal.concurrent(max_inputs=50)
@modal.asgi_app()
def web():
    from fastapi import Body, FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, RedirectResponse, Response

    api = FastAPI(docs_url=None, redoc_url=None)
    page = Path("/root/index.html").read_text(encoding="utf-8")
    app_page = Path("/root/sovellus.html").read_text(encoding="utf-8")
    pro_page = Path("/root/ammattilaisille.html").read_text(encoding="utf-8")
    dm_page = Path("/root/paattajille.html").read_text(encoding="utf-8")
    priv_page = Path("/root/tietosuoja.html").read_text(encoding="utf-8")
    team_img = Path("/root/team.jpg").read_bytes()
    regions = json.loads(Path("/root/regions.json").read_text(encoding="utf-8"))
    ai_cache = {}
    ai_calls = []
    about_page = Path("/root/meista.html").read_text(encoding="utf-8")
    faq_page = Path("/root/ukk.html").read_text(encoding="utf-8")
    fb_page = Path("/root/palaute.html").read_text(encoding="utf-8")
    data_page = Path("/root/keuhkodata.html").read_text(encoding="utf-8")
    lock = threading.Lock()


    def read_all():
        if not DATA.exists():
            return []
        with DATA.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    @api.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(page)

    @api.get("/sovellus", response_class=HTMLResponse)
    @api.get("/sovellus/", response_class=HTMLResponse)
    def app_index():
        return HTMLResponse(app_page)

    @api.get("/ammattilaisille", response_class=HTMLResponse)
    @api.get("/ammattilaisille/", response_class=HTMLResponse)
    def pro_index():
        return HTMLResponse(pro_page)

    @api.get("/paattajille", response_class=HTMLResponse)
    @api.get("/paattajille/", response_class=HTMLResponse)
    def dm_index():
        return RedirectResponse(url="/keuhkodata", status_code=302)

    @api.get("/tietosuoja", response_class=HTMLResponse)
    @api.get("/tietosuoja/", response_class=HTMLResponse)
    def priv_index():
        return HTMLResponse(priv_page)

    @api.get("/meista", response_class=HTMLResponse)
    @api.get("/about", response_class=HTMLResponse)
    def about_index():
        return HTMLResponse(about_page)

    FACTS = """FACTS YOU MAY USE (cite the source tag in square brackets after each claim):
- Regional lung cancer deaths 2021-2025 (cause C32-C34) and SMR = observed / expected deaths, indirect age standardisation with national age-specific rates. [Tilastokeskus 13u5, 11az, 11s1; Polku Labs calculation]
- Finland: about 155 days from first symptoms to start of lung cancer treatment; patient 50+ days, primary care 41 days, specialist care 58 days. Sweden 107 days, Denmark 67 days. These are national figures from four hospitals (Kuopio, Tampere, Turku, Rovaniemi), NOT available per region. [Yle MOT 2026, Kuittinen et al., unpublished]
- Finland 5-year relative survival in lung cancer: men about 17%, women about 26%; by education men 13% (basic) vs 18% (tertiary), women 20% vs 30%. [National Lung Cancer Programme 2026-2035]
- 27% of patients were directed to curative treatment; stage information missing for almost half. [Cancer Society of Finland, quality registry lung cancer report 2019-2023]
- The national programme will define referral criteria and time limits for diagnostic steps, not yet published; it will assess risk-group screening. [National Lung Cancer Programme 2026-2035]
- England's Targeted Lung Health Check mobile CT units found over 5,000 lung cancers, 76% at stage 1-2. [NHS England / GOV.UK 2023]
- Expert interviews: symptoms go unnoticed because information is scattered across systems and doctors change; fear and low health literacy delay help-seeking; language is one barrier. [AstraZeneca expert interviews, Junction 2026]
POSSIBLE ACTIONS (Polku hoitoon concept, not yet piloted, no measured effect):
A) (Role not decided by the team; do not recommend it.) Flag + direct imaging referral in primary care when a smoker visits a third time with respiratory symptoms. Metric: days from first visit to imaging.
B) App: continuous symptom tracking in the patient's own language and a visible care path. Metric: time from symptoms to first visit, also by language group.
C) Risk-group low-dose CT screening bus (age 50-74, heavy smokers), started as a pilot with randomised invitations so it measures whether the bus reaches people a hospital CT would not. Metric: share diagnosed at stage 1-2.
- Estimated risk group about 120,000 people nationally (7% of 50-74-year-olds): smoking rates times an assumed factor, because Finnish pack-year data does not exist. [Polku Labs estimate from THL Sotkanet; assumption]
- In Finnish cancer screening (breast, colorectal, cervical 2024), participation is about 20 points lower for people whose native language is not Finnish, Swedish or Sami, and lower with basic education; the lowest regional participation is in the capital region. These are other screening programmes, so whether distance or language is the bigger barrier for lung CT is not known; the pilot measures uptake by both. Lapland, the most remote region, has the highest excess lung cancer mortality. [Finnish Cancer Registry screening statistics 2024; Polku Labs SMR calculation]
RECOMMENDATIONS ARE MADE BY THE POLKU LABS TEAM, NOT BY YOU. The team's rule, shown on the page: if the region's SMR is significantly above 1 (CI lower bound above 1), prioritise it for the risk-group screening bus pilot (C) and offer the app (B); if the difference is not significant, start with the app (B) and do not prioritise the bus; if significantly below 1, no extra measures, follow the metrics. Your job is to explain the gap and the evidence. Do not propose actions of your own; if asked what to do, restate the team's rule for this region and say it is the team's recommendation."""

    @api.get("/api/regions")
    def api_regions():
        return regions

    @api.post("/api/analyst")
    def analyst(body: dict = Body(...)):
        import time
        import httpx
        name = str(body.get("region", ""))
        reg = next((r for r in regions if r["name"] == name), None)
        if reg is None:
            raise HTTPException(status_code=400, detail="unknown region")
        lang = body.get("lang") if body.get("lang") in ("fi", "sv", "en") else "fi"
        question = str(body.get("question") or "").strip()[:300]
        key = (name, lang, question)
        if key in ai_cache:
            return {"text": ai_cache[key], "cached": True}
        now = time.time()
        ai_calls[:] = [t for t in ai_calls if now - t < 3600]
        if len(ai_calls) >= 120:  # protects the hackathon credits
            raise HTTPException(status_code=429, detail="rate limit")
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise HTTPException(status_code=503, detail="analyst not configured")
        language = {"fi": "Finnish", "sv": "Swedish", "en": "English"}[lang]
        system = (
            "You are an analyst helping a non-technical decision-maker in a Finnish wellbeing services county "
            "understand lung cancer care gaps. Use ONLY the facts and region data given. Never invent numbers, "
            "effect sizes or costs. If something is not in the facts, say that the data is not available. "
            "Say clearly when a figure is national rather than regional. Do not give medical advice about individuals. "
            f"Write in {language}, plain language, at most 170 words, no markdown symbols. "
            "End every claim that uses a fact with its source tag in square brackets.\n\n" + FACTS
        )
        task = question or (
            "Write a briefing with three short labelled parts: 1) the gap in this region compared with the national level, "
            "2) what national evidence says about delays along the care pathway (state clearly that it is national, not regional), "
            "3) what is not known about this region and which data would be needed. "
            "Never claim to know where in the pathway this region's gap emerges."
        )
        user = (
            f"Region: {reg['name']}. Lung cancer deaths 2021-2025: {reg['deaths']}; expected from age structure: "
            f"{reg['expected']}; SMR {reg['smr']} (95% CI {reg['lo']}-{reg['hi']}); rank {reg['rank']} of {len(regions)} "
            f"(1 = highest); crude mortality {reg['crude']} per 100,000 per year; population {reg['pop']}.\n\nTask: {task}"
        )
        text = ""
        for model in (os.environ.get("POLKU_MODEL", "claude-sonnet-5-5"), "claude-haiku-5-5"):
            try:
                r = httpx.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                    json={"model": model, "max_tokens": 1500, "system": system,
                          "messages": [{"role": "user", "content": user}]},
                    timeout=90,
                )
                if r.status_code != 200:
                    print("analyst http error:", model, r.status_code, r.text[:500])
                    continue
                data = r.json()
                text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
                if text:
                    break
                print("analyst empty answer:", model, "stop_reason=", data.get("stop_reason"),
                      "blocks=", [b.get("type") for b in data.get("content", [])], "usage=", data.get("usage"))
            except Exception as e:
                print("analyst error:", model, repr(e)[:300])
        if not text:
            raise HTTPException(status_code=502, detail="analyst unavailable")
        ai_calls.append(now)
        if len(ai_cache) > 500:  # keep memory bounded
            ai_cache.clear()
        ai_cache[key] = text
        return {"text": text, "cached": False}

    @api.get("/ukk", response_class=HTMLResponse)
    @api.get("/faq", response_class=HTMLResponse)
    def faq_index():
        return HTMLResponse(faq_page)

    @api.get("/palaute", response_class=HTMLResponse)
    @api.get("/feedback", response_class=HTMLResponse)
    def fb_index():
        return HTMLResponse(fb_page)

    @api.get("/keuhkodata", response_class=HTMLResponse)
    @api.get("/keuhkodata/", response_class=HTMLResponse)
    @api.get("/data", response_class=HTMLResponse)
    def data_index():
        return HTMLResponse(data_page)

    @api.get("/team.jpg")
    def team_jpg():
        return Response(team_img, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

    @api.post("/api/signup")
    def signup(body: dict = Body(...)):
        if body.get("website"):  # honeypot for bots
            return {"ok": True}
        contact = str(body.get("contact", "")).strip()[:120]
        postcode = str(body.get("postcode", "")).strip()
        if not contact or not re.fullmatch(r"\d{5}", postcode) or body.get("consent") is not True or body.get("privacy") is not True:
            raise HTTPException(status_code=400, detail="missing fields")
        raw = body.get("products")
        prods = sorted({p for p in raw if p in PRODUCTS}) if isinstance(raw, list) else []
        if not prods:
            prods = [body.get("product")] if body.get("product") in PRODUCTS else ["bus"]
        entry = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "name": str(body.get("name", "")).strip()[:60],
            "contact": contact,
            "postcode": postcode,
            "eligible": body.get("eligible") if body.get("eligible") in ELIG else "unsure",
            "lang": body.get("lang") if body.get("lang") in LANGS else "fi",
            "consent": True,
            "privacy": True,
            "for": body.get("for") if body.get("for") in WHO else "self",
            "age": body.get("age") if body.get("age") in AGE else "",
            "smoke": body.get("smoke") if body.get("smoke") in SMOKE else "",
            "products": prods,
            "product": "+".join(prods),
            "beta": body.get("beta") is True,
            "src": re.sub(r"[^a-z0-9._-]", "", str(body.get("src", "direct")).lower())[:40] or "direct",
        }
        with lock:
            DATA.parent.mkdir(parents=True, exist_ok=True)
            with DATA.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            vol.commit()
        return {"ok": True}


    @api.post("/api/feedback")
    def feedback(body: dict = Body(...)):
        if body.get("website"):  # honeypot
            return {"ok": True}
        rating = body.get("rating")
        rating = rating if isinstance(rating, int) and 1 <= rating <= 5 else None
        text = str(body.get("text") or "").strip()[:1000]
        if rating is None and not text:
            raise HTTPException(status_code=400, detail="empty")
        entry = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "page": body.get("page") if body.get("page") in PRODUCTS else "bus",
            "rating": rating,
            "text": text,
            "lang": body.get("lang") if body.get("lang") in LANGS else "fi",
            "src": re.sub(r"[^a-z0-9._-]", "", str(body.get("src", "direct")).lower())[:40] or "direct",
        }
        with lock:
            FEEDBACK.parent.mkdir(parents=True, exist_ok=True)
            with FEEDBACK.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            vol.commit()
        return {"ok": True}

    @api.get("/api/count")
    def count(product: str | None = None):
        # Public: total count only, no locations or personal data.
        with lock:
            rows = read_all()
        if product in PRODUCTS:
            rows = [r for r in rows if product in (r.get("products") or [r.get("product", "bus")])]
        return {"total": len(rows)}


    return api
