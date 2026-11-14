"""Map-only preview of the Polku hoitoon pilot map, for review before it joins the live site.

Runs map/map_server.py: the map page and data, the password-gated tools (route creator, hospital CT scenario, assumption scenarios) and the
chat endpoint. No sign-up form and no stored data. Links to other site pages redirect to the live site. Pages are marked noindex.

One-time setup (choose your own values; never paste them into chat or the repo):
    modal secret create polku-map-preview MAP_PASSWORD=<password>
    # later, to switch on the AI chat, add your Claude API key to the same secret:
    modal secret create polku-map-preview MAP_PASSWORD=<password> ANTHROPIC_API_KEY=<key> --force
Deploy (run the build script first so map/private/pilot_map_advanced.json exists):
    cd map && modal deploy preview_app.py
Remove after review:
    modal app stop polku-map-preview
"""
from pathlib import Path

import modal

MAP = Path(__file__).parent
REPO = MAP.parent

image = (
    modal.Image.debian_slim()
    .pip_install("fastapi[standard]", "anthropic")
    .add_local_dir(MAP, "/root/map", ignore=["**/__pycache__/**", "integration/**", "README.md"])
    .add_local_dir(REPO / "ct-sim/src/ctsim", "/root/ct-sim/src/ctsim", ignore=["**/__pycache__/**"])
    .add_local_dir(REPO / "ct-sim/data/routing", "/root/ct-sim/data/routing")
    .add_local_dir(REPO / "ct-sim/data/area", "/root/ct-sim/data/area")
    .add_local_dir(REPO / "ct-sim/data/ct_sites", "/root/ct-sim/data/ct_sites")
    .add_local_dir(REPO / "ct-sim/data/model", "/root/ct-sim/data/model")
    .add_local_file(REPO / "landing-page/regions.json", "/root/landing-page/regions.json")
    .add_local_dir(REPO / "landing-page/fonts", "/root/landing-page/fonts")
)

app = modal.App("polku-map-preview")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("polku-map-preview")],   # MAP_PASSWORD, and later ANTHROPIC_API_KEY
    max_containers=1,                                         # the rate limiters live in memory
    timeout=120,
)
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    import sys
    sys.path.insert(0, "/root/map")
    from map_server import create_app
    return create_app(Path("/root/map"), Path("/root/map/private/pilot_map_advanced.json").read_bytes())
