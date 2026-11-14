"""Modal app for ctsim: the engine as functions, a parallel scenario sweep, and the map UI + API as one web endpoint.

  modal run   api/modal_app.py::smoke     # remote smoke test: runs a scenario on Modal, compares with the local result, fans out a sweep
  modal serve api/modal_app.py            # temporary dev URL for the web app (stops when you stop the command)
  modal deploy api/modal_app.py           # permanent PUBLIC URL, no authentication (see warning below)

WARNING: the web endpoint has no authentication and runs CPU work on request. n is capped, but anyone with the URL can use your credits.
Deploy only for the demo and `modal app stop ctsim` afterwards.

Only public aggregate data (municipality table, researched CT site list) and the front end are copied into the image.
"""
import sys
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))        # so add_local_python_source("ctsim") finds the package when run locally

app = modal.App("ctsim")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]")
    .env({"CTSIM_ROOT": "/root"})
    .add_local_python_source("ctsim")
    .add_local_file(ROOT / "data" / "routing" / "municipalities.csv", remote_path="/root/data/routing/municipalities.csv")
    .add_local_file(ROOT / "data" / "ct_sites" / "ct_sites.csv", remote_path="/root/data/ct_sites/ct_sites.csv")
    .add_local_file(ROOT / "data" / "gap" / "gapdata.json", remote_path="/root/data/gap/gapdata.json")
    .add_local_dir(ROOT / "web", remote_path="/root/web")
)


@app.function(image=image)
def run_one(scn: dict) -> dict:
    from ctsim import scenario
    return scenario.run(scn)


@app.function(image=image, timeout=600)
def robust_task(kind: str, scn: dict, specs: list, extra=None):
    """One chunk of simulated worlds. Pure function of its arguments, so containers can run any chunk in any order."""
    from ctsim import robust
    return robust.TASKS[kind](scn, specs, extra)


@app.function(image=image, timeout=900)
def run_robust(scn: dict, n: int = 100, seed: int = 1, voi_n: int = 20, chunk: int = 4) -> dict:
    """Robustness sweep with the worlds spread over containers. Same result as the local sequential run for the same seed:
    the driver draws every world here, so the random stream does not depend on how the work is split."""
    from ctsim import robust

    def modal_mapper(jobs):
        return list(robust_task.starmap(jobs))   # jobs = [(kind, scn, chunk, extra), ...]; results come back in order

    return robust.run(scn, n=n, seed=seed, voi_n=voi_n, mapper=modal_mapper, chunk=chunk)


@app.function(image=image, timeout=900)
def sweep(scenarios: list[dict]) -> list[dict]:
    """Fan out many scenarios in parallel containers, e.g. a grid of assumptions."""
    return list(run_one.map(scenarios))


@app.function(image=image, timeout=300)
@modal.asgi_app()
def web():
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    from ctsim import readout, robust, routing, scenario

    api = FastAPI(title="ctsim")

    @api.get("/health")
    def health():
        return {"ok": True, "version": scenario.VERSION}

    @api.get("/municipalities")
    def municipalities():
        return [{k: r[k] for k in ("code", "name", "lat", "lon", "pop", "f")} for r in routing.load()]

    @api.post("/scenario")
    def run(body: dict):
        try:
            return scenario.run(body)
        except (KeyError, ValueError, StopIteration) as e:
            raise HTTPException(400, f"{type(e).__name__}: {e}")

    @api.post("/readout")
    def run_readout(body: dict):
        try:
            return readout.run(body)
        except (KeyError, ValueError, StopIteration) as e:
            raise HTTPException(400, f"{type(e).__name__}: {e}")

    @api.post("/robust")
    def run_rb(body: dict):
        try:
            n = max(10, min(int(body.get("n", 60)), 400))     # parallel, so a higher cap than the local server
            return run_robust.remote(body["scenario"], n=n, seed=int(body.get("seed", 1)), voi_n=min(int(body.get("voi_n", 20)), 30))
        except (KeyError, ValueError, StopIteration) as e:
            raise HTTPException(400, f"{type(e).__name__}: {e}")

    api.mount("/vendor", StaticFiles(directory="/root/web/vendor"), name="vendor")

    @api.get("/")
    def index():
        return FileResponse("/root/web/index.html")

    @api.get("/gap")
    def gap_page():
        return FileResponse("/root/web/gap.html")

    @api.get("/gapdata")
    def gapdata():
        import json
        return json.load(open("/root/data/gap/gapdata.json", encoding="utf-8"))

    return api


@app.local_entrypoint()
def robust_bench(n: int = 100, national: bool = True, chunk: int = 4):
    """Compare the sweep run sequentially on this machine with the same sweep spread over Modal containers.
    Prints wall-clock times and whether the two results are identical."""
    import json
    import time

    from ctsim import robust

    scn = {"name": "bench", "region": None if national else {"base": "Tampere", "radius_km": 100}, "ct_sites": "confirmed+likely"}
    t = time.time()
    local = robust.run(scn, n=n, seed=1, voi_n=20)
    t_local = time.time() - t
    t = time.time()
    remote = run_robust.remote(scn, n=n, seed=1, voi_n=20, chunk=chunk)
    t_remote = time.time() - t
    t = time.time()
    remote2 = run_robust.remote(scn, n=n, seed=1, voi_n=20, chunk=chunk)       # containers are warm now
    t_warm = time.time() - t
    same = json.dumps(local, sort_keys=True, default=str) == json.dumps(remote, sort_keys=True, default=str)
    print(f"n={n} worlds ({'national' if national else 'Tampere 100 km'}), chunk={chunk}")
    print(f"  local sequential : {t_local:6.1f} s")
    print(f"  Modal, first run : {t_remote:6.1f} s  (includes container start)")
    print(f"  Modal, second run: {t_warm:6.1f} s")
    print(f"  results identical to local: {same}   (second run identical: {json.dumps(remote2, sort_keys=True, default=str) == json.dumps(remote, sort_keys=True, default=str)})")


@app.local_entrypoint()
def smoke():
    """Remote vs local equality check, then a small parallel sweep."""
    from ctsim import scenario

    scn = {"name": "modal-smoke", "region": {"base": "Tampere", "radius_km": 100}}
    remote = run_one.remote(scn)
    local = scenario.run(scn)
    same = remote["route"]["order"] == local["route"]["order"] and abs(remote["outcomes"]["additional"] - local["outcomes"]["additional"]) < 1e-6
    print(f"remote {remote['seconds']}s: {len(remote['route']['stops'])} stops, {remote['outcomes']['additional']:.0f} extra participants/yr, "
          f"data hash {remote['data']}")
    print(f"matches local result: {same}")

    grid = [{"name": f"elig-{e}", "region": scn["region"], "routing": {"eligible_share": e}} for e in (0.03, 0.05, 0.07, 0.09, 0.12)]
    for s, r in zip(grid, sweep.remote(grid)):
        print(f"  eligible_share={s['routing']['eligible_share']:.2f}: {r['outcomes']['additional']:.0f} extra/yr, {len(r['route']['stops'])} stops")
