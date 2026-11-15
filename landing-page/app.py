"""Polku hoitoon waitlist: bus page (/) + lung cancer data dashboard (/keuhkodata) + pilot map (/kartta) + sign-up API on Modal.
/sovellus redirects to / (the HTML file stays in the repo but is not served). /ammattilaisille is the professional
flagging view, linked from the footer only.

Deploy:      python3 ../ct-sim/docs/analysis/build_pilot_map_data.py   (creates map/private/pilot_map_advanced.json, not in git)
             modal deploy app.py
Secrets:     polku-ai holds ANTHROPIC_API_KEY (analyst + map chat) and MAP_PASSWORD (map advanced tools). Without them the
             analyst and map chat show their fallback messages and the map tools stay locked.
Sign-ups:    python signups.py   (reads the Modal Volume with your own Modal login)

There is deliberately no admin page on the website: sign-ups are only
readable by someone logged in to the Modal account.
"""
import json
import time
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

try:
    import modal
except ImportError:  # local run without Modal: see local_api() at the end
    modal = None

HERE = Path(__file__).parent
MAP = HERE.parent / "map"
REPO = HERE.parent
ADVANCED = MAP / "private/pilot_map_advanced.json"
if (modal is None or modal.is_local()) and not ADVANCED.exists():   # inside the container the file lives under /root/map
    raise SystemExit(f"Missing {ADVANCED}. Run: python3 ct-sim/docs/analysis/build_pilot_map_data.py (from the repo root), then deploy again.")

if modal:
    image = (
        modal.Image.debian_slim()
        .pip_install("fastapi[standard]", "anthropic")
        .add_local_file(HERE / "index.html", "/root/index.html")
        .add_local_file(HERE / "tietosuoja.html", "/root/tietosuoja.html")
        .add_local_file(HERE / "meista.html", "/root/meista.html")
        .add_local_file(HERE / "ukk.html", "/root/ukk.html")
        .add_local_file(HERE / "palaute.html", "/root/palaute.html")
        .add_local_file(HERE / "keuhkodata.html", "/root/keuhkodata.html")
        .add_local_file(HERE / "ammattilaisille.html", "/root/ammattilaisille.html")
        .add_local_file(HERE / "layout.js", "/root/layout.js")
        .add_local_file(HERE / "site.css", "/root/site.css")
        .add_local_dir(HERE / "assets", "/root/assets")
        .add_local_file(MAP / "kartta.html", "/root/kartta.html")
        .add_local_file(MAP / "pilot_map.json", "/root/pilot_map.json")
        .add_local_file(MAP / "vendor/leaflet.js", "/root/leaflet.js")
        .add_local_file(MAP / "vendor/leaflet.css", "/root/leaflet.css")
        .add_local_file(HERE / "team.jpg", "/root/team.jpg")
        .add_local_file(HERE / "regions.json", "/root/regions.json")
        .add_local_file(HERE / "ai_engine.py", "/root/ai_engine.py")
        .add_local_file(HERE / "vendor/chart.umd.js", "/root/chart.umd.js")
        .add_local_dir(HERE / "fonts", "/root/fonts")
        # map API (same layout as the repo, so map/route_engine.py finds ct-sim/ and landing-page/regions.json)
        .add_local_file(MAP / "map_server.py", "/root/map/map_server.py")
        .add_local_file(MAP / "route_engine.py", "/root/map/route_engine.py")
        .add_local_file(MAP / "map_gate.py", "/root/map/map_gate.py")
        .add_local_file(ADVANCED, "/root/map/private/pilot_map_advanced.json")
        .add_local_file(HERE / "regions.json", "/root/landing-page/regions.json")
        .add_local_dir(REPO / "ct-sim/src/ctsim", "/root/ct-sim/src/ctsim", ignore=["**/__pycache__/**"])
        .add_local_dir(REPO / "ct-sim/data/routing", "/root/ct-sim/data/routing")
        .add_local_dir(REPO / "ct-sim/data/area", "/root/ct-sim/data/area")
        .add_local_dir(REPO / "ct-sim/data/ct_sites", "/root/ct-sim/data/ct_sites")
        .add_local_dir(REPO / "ct-sim/data/model", "/root/ct-sim/data/model")
    )

    app = modal.App("vayla-waitlist")
    vol = modal.Volume.from_name("vayla-signups", create_if_missing=True)
else:
    vol = None

DATA = Path("/data/signups.jsonl")
FEEDBACK = Path("/data/feedback.jsonl")

LANGS = {"fi", "sv", "en", "ru", "et", "ar", "so", "uk"}
ELIG = {"yes", "no", "unsure"}
WHO = {"self", "relative"}
AGE = {"yes", "no"}
SMOKE = {"now", "former", "never"}
PRODUCTS = {"bus", "app"}


def build_api(src):
    """The website. src(name) gives the path of a bundled file: the image copy on Modal, the repo file locally."""
    from fastapi import Body, FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, RedirectResponse, Response

    api = FastAPI(docs_url=None, redoc_url=None)
    page = src("index.html").read_text(encoding="utf-8")
    priv_page = src("tietosuoja.html").read_text(encoding="utf-8")
    team_img = src("team.jpg").read_bytes()
    regions = json.loads(src("regions.json").read_text(encoding="utf-8"))
    ai_cache = {}
    ai_calls = []
    about_page = src("meista.html").read_text(encoding="utf-8")
    faq_page = src("ukk.html").read_text(encoding="utf-8")
    fb_page = src("palaute.html").read_text(encoding="utf-8")
    data_page = src("keuhkodata.html").read_text(encoding="utf-8")
    pro_page = src("ammattilaisille.html").read_text(encoding="utf-8")
    layout_script = src("layout.js").read_text(encoding="utf-8")
    site_css = src("site.css").read_bytes()
    ASSET_TYPES = {".js": "application/javascript", ".json": "application/json", ".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml"}
    assets = {f.name: f.read_bytes() for f in src("assets").iterdir() if f.suffix in ASSET_TYPES}
    map_page = src("kartta.html").read_text(encoding="utf-8")
    map_data = src("pilot_map.json").read_bytes()
    leaflet_js = src("leaflet.js").read_bytes()
    leaflet_css = src("leaflet.css").read_bytes()
    chart_js = src("chart.umd.js").read_bytes()
    fonts = {f.name: f.read_bytes() for f in src("fonts").iterdir() if f.suffix in (".woff2", ".css")}
    lock = threading.Lock()

    import sys
    sys.path.insert(0, str(src("map")))
    import map_server
    map_server.register_api(api, json.loads(map_data), src("map/private/pilot_map_advanced.json").read_bytes())


    def read_all():
        if not DATA.exists():
            return []
        with DATA.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    @api.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(page)

    @api.get("/layout.js")
    def layout():
        return Response(content=layout_script, media_type="application/javascript")

    @api.get("/site.css")
    def site_css_file():
        return Response(site_css, media_type="text/css", headers={"Cache-Control": "public, max-age=300"})

    @api.get("/assets/{name}")
    def asset_file(name: str):   # 3D hero script (bundled three.js), Finland outlines, still fallback image
        if name not in assets:
            raise HTTPException(status_code=404)
        return Response(assets[name], media_type=ASSET_TYPES[Path(name).suffix], headers={"Cache-Control": "public, max-age=3600"})

    @api.get("/kartta", response_class=HTMLResponse)
    @api.get("/kartta/", response_class=HTMLResponse)
    @api.get("/map", response_class=HTMLResponse)
    def map_index():
        return HTMLResponse(map_page)

    @api.get("/pilot_map.json")
    def pilot_map_json():
        return Response(map_data, media_type="application/json", headers={"Cache-Control": "public, max-age=300"})

    @api.get("/vendor/leaflet.js")
    def leaflet_js_file():
        return Response(leaflet_js, media_type="application/javascript", headers={"Cache-Control": "public, max-age=86400"})

    @api.get("/vendor/leaflet.css")
    def leaflet_css_file():
        return Response(leaflet_css, media_type="text/css", headers={"Cache-Control": "public, max-age=86400"})

    @api.get("/vendor/chart.umd.js")
    def chart_js_file():
        return Response(chart_js, media_type="application/javascript", headers={"Cache-Control": "public, max-age=86400"})

    @api.get("/fonts/{name}")
    def font_file(name: str):
        if name not in fonts:
            raise HTTPException(status_code=404)
        kind = "text/css" if name.endswith(".css") else "font/woff2"
        return Response(fonts[name], media_type=kind, headers={"Cache-Control": "public, max-age=" + ("300" if name.endswith(".css") else "604800")})

    @api.get("/sovellus")
    @api.get("/sovellus/")
    def app_index():
        return RedirectResponse(url="/", status_code=302)

    @api.get("/ammattilaisille", response_class=HTMLResponse)
    @api.get("/ammattilaisille/", response_class=HTMLResponse)
    @api.get("/pro", response_class=HTMLResponse)
    def pro_index():
        # Professional view (flagging concept). Linked from the footer only, kept apart from Keuhkodata.
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
C) Risk-group low-dose CT screening bus (age 50-74, heavy smokers), started as a pilot with randomised invitations so it measures whether the bus reaches people a hospital CT would not. Metric: share diagnosed at stage 1-2.
- Estimated risk group about 120,000 people nationally (7% of 50-74-year-olds): smoking rates times an assumed factor, because Finnish pack-year data does not exist. [Polku Labs estimate from THL Sotkanet; assumption]
- In Finnish cancer screening (breast, colorectal, cervical 2024), participation is about 20 points lower for people whose native language is not Finnish, Swedish or Sami, and lower with basic education; the lowest regional participation is in the capital region. These are other screening programmes, so whether distance or language is the bigger barrier for lung CT is not known; the pilot measures uptake by both. Lapland, the most remote region, has the highest excess lung cancer mortality. [Finnish Cancer Registry screening statistics 2024; Polku Labs SMR calculation]
RECOMMENDATIONS ARE MADE BY THE POLKU LABS TEAM, NOT BY YOU. The team's recommendation, shown on the page: bus pilot (C) in Lapland, where travel time is the barrier (47% of the people the bus would reach live more than an hour from a CT) [Polku Labs pilot map; modelled]. In Kymenlaakso and Satakunta start with hospital-CT invitations; a bus would mainly add capacity, which is an assumption. For other regions the team makes no recommendation; follow the metrics. Your job is to explain the gap and the evidence. Do not propose actions of your own; if asked what to do, restate this recommendation and say it is the team's recommendation."""

    # ---- AI analyst: an agent over the data with tools; numbers checked; rule-based fallback for the presets ----
    sys.path.insert(0, str(src("ai_engine.py").parent))
    import ai_engine
    ai_data = ai_engine.Data(data_page, json.loads(map_data))
    agent_cache = {}

    @api.post("/api/ai")
    def ai(body: dict = Body(...)):
        import httpx
        lang = body.get("lang") if body.get("lang") in ("fi", "sv", "en") else "en"
        preset = body.get("preset") if body.get("preset") in ai_engine.PRESETS else None
        question = str(body.get("question") or "").strip()[:400]
        region = body.get("region") if body.get("region") in ai_data.regions else None
        if not question and not preset:
            raise HTTPException(status_code=400, detail="ask a question")
        key = (preset, question, lang, region)
        if key in agent_cache:
            return {**agent_cache[key], "cached": True}
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        now = time.time()
        ai_calls[:] = [t for t in ai_calls if now - t < 3600]
        out = None
        if api_key and len(ai_calls) < 120:
            q = question or {"first_pilot": "Where should Finland's first lung cancer screening pilot go, and why?",
                             "distance": "In which regions is distance to a CT scanner the main barrier?",
                             "smoking_mortality": "Where are smoking and lung cancer mortality both high?",
                             "screening_reach": "Where does screening reach people worst?"}[preset]
            for model in (os.environ.get("POLKU_MODEL", "claude-sonnet-5-5"), "claude-haiku-5-5"):
                try:
                    out = ai_engine.run_agent(ai_data, q, lang, api_key, httpx.post, model, region)
                    ai_calls.append(now)
                    break
                except Exception as e:
                    print("ai agent error:", model, repr(e)[:300])
        if out is None and preset:
            out = ai_engine.run_rules(ai_data, preset, lang)
            out["offline"] = not api_key
        if out is None:
            raise HTTPException(status_code=503, detail="ai not configured" if not api_key else "ai unavailable")
        if len(agent_cache) > 300:
            agent_cache.clear()
        agent_cache[key] = out
        return out

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
            if vol:
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
            if vol:
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


if modal:
    @app.function(
        image=image,
        volumes={"/data": vol},
        secrets=[modal.Secret.from_name("polku-ai")],  # ANTHROPIC_API_KEY (analyst, map chat), MAP_PASSWORD (map tools)
        max_containers=1,  # one writer keeps the file consistent
    )
    @modal.concurrent(max_inputs=50)
    @modal.asgi_app()
    def web():
        return build_api(lambda name: Path("/root") / name)


LOCAL = {  # bundled name -> repo file, for local_api()
    "kartta.html": MAP / "kartta.html", "pilot_map.json": MAP / "pilot_map.json",
    "leaflet.js": MAP / "vendor/leaflet.js", "leaflet.css": MAP / "vendor/leaflet.css",
    "chart.umd.js": HERE / "vendor/chart.umd.js", "map": MAP,
}


def local_api():
    """Run the same website without Modal, reading the repo files. Sign-ups and feedback go to POLKU_DATA_DIR
    (default landing-page/.local-data, git-ignored). From landing-page/:  uvicorn app:local_api --factory --port 8000"""
    global DATA, FEEDBACK
    d = Path(os.environ.get("POLKU_DATA_DIR", HERE / ".local-data"))
    DATA, FEEDBACK = d / "signups.jsonl", d / "feedback.jsonl"

    def src(name):
        if name in LOCAL:
            return LOCAL[name]
        if name.startswith("map/"):
            return MAP / name[4:]
        return HERE / name
    return build_api(src)
