"""Polku hoitoon waitlist: bus page (/) + app page (/sovellus) + professional page (/ammattilaisille) + sign-up API on Modal.

Deploy:      modal deploy app.py
Sign-ups:    python signups.py   (reads the Modal Volume with your own Modal login)

There is deliberately no admin page on the website: sign-ups are only
readable by someone logged in to the Modal account.
"""
import json
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
    .add_local_file(HERE / "team.jpg", "/root/team.jpg")
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
    max_containers=1,  # one writer keeps the file consistent
)
@modal.concurrent(max_inputs=50)
@modal.asgi_app()
def web():
    from fastapi import Body, FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, Response

    api = FastAPI(docs_url=None, redoc_url=None)
    page = Path("/root/index.html").read_text(encoding="utf-8")
    app_page = Path("/root/sovellus.html").read_text(encoding="utf-8")
    pro_page = Path("/root/ammattilaisille.html").read_text(encoding="utf-8")
    dm_page = Path("/root/paattajille.html").read_text(encoding="utf-8")
    priv_page = Path("/root/tietosuoja.html").read_text(encoding="utf-8")
    team_img = Path("/root/team.jpg").read_bytes()
    about_page = Path("/root/meista.html").read_text(encoding="utf-8")
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
        return HTMLResponse(dm_page)

    @api.get("/tietosuoja", response_class=HTMLResponse)
    @api.get("/tietosuoja/", response_class=HTMLResponse)
    def priv_index():
        return HTMLResponse(priv_page)

    @api.get("/meista", response_class=HTMLResponse)
    @api.get("/about", response_class=HTMLResponse)
    def about_index():
        return HTMLResponse(about_page)

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
