"""Map-only preview of the Polku hoitoon pilot map, for review before it joins the live site.

Serves /kartta (and /) plus its data and Leaflet, and the password gate for the advanced tools. It has no sign-up form, no AI analyst and no
volume, so it cannot touch live data. Links to other site pages redirect to the live site. Pages are marked noindex.

One-time setup (you choose the password; do not paste it into chat or the repo):
    modal secret create polku-map-preview MAP_PASSWORD=<your password>
Deploy:
    cd landing-page && modal deploy preview_app.py
Remove after review:
    modal app stop polku-map-preview
"""
from pathlib import Path

import modal

HERE = Path(__file__).parent
LIVE = "https://polkuhoitoon.fi"
LIVE_PATHS = {"sovellus", "ammattilaisille", "paattajille", "keuhkodata", "meista", "ukk", "palaute", "tietosuoja"}

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi[standard]")
    .add_local_file(HERE / "kartta.html", "/root/kartta.html")
    .add_local_file(HERE / "pilot_map.json", "/root/pilot_map.json")
    .add_local_file(HERE / "vendor/leaflet.js", "/root/leaflet.js")
    .add_local_file(HERE / "vendor/leaflet.css", "/root/leaflet.css")
    .add_local_file(HERE / "private/pilot_map_advanced.json", "/root/pilot_map_advanced.json")
    .add_local_file(HERE / "map_gate.py", "/root/map_gate.py")
)

app = modal.App("polku-map-preview")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("polku-map-preview")],   # holds MAP_PASSWORD
    max_containers=1,                                         # the failed-attempt limiter lives in memory
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    import sys

    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, RedirectResponse, Response

    sys.path.insert(0, "/root")
    import map_gate

    api = FastAPI(docs_url=None, redoc_url=None)
    page = Path("/root/kartta.html").read_text(encoding="utf-8")
    data = Path("/root/pilot_map.json").read_bytes()
    js = Path("/root/leaflet.js").read_bytes()
    css = Path("/root/leaflet.css").read_bytes()

    @api.middleware("http")
    async def noindex(request, call_next):
        resp = await call_next(request)
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        return resp

    @api.get("/", response_class=HTMLResponse)
    @api.get("/kartta", response_class=HTMLResponse)
    @api.get("/kartta/", response_class=HTMLResponse)
    def kartta():
        return HTMLResponse(page)

    @api.get("/pilot_map.json")
    def pilot_map():
        return Response(data, media_type="application/json", headers={"Cache-Control": "no-cache"})

    @api.get("/vendor/leaflet.js")
    def leaflet_js():
        return Response(js, media_type="application/javascript", headers={"Cache-Control": "public, max-age=86400"})

    @api.get("/vendor/leaflet.css")
    def leaflet_css():
        return Response(css, media_type="text/css", headers={"Cache-Control": "public, max-age=86400"})

    map_gate.register(api, Path("/root/pilot_map_advanced.json").read_bytes())

    @api.get("/{path:path}")
    def other(path: str):
        first = path.strip("/").split("/")[0]
        if first in LIVE_PATHS:
            return RedirectResponse(f"{LIVE}/{first}", status_code=302)
        raise HTTPException(404)

    return api
