"""Tiny local HTTP server (stdlib only) so a front end can call the engine during development.

  GET  /                -> web/index.html (the map front end); /vendor/* serves vendored Leaflet
  GET  /gap, /gapdata   -> the gap-finder page and its data (run `python -m ctsim gap` to rebuild the data)
  GET  /health          -> {"ok": true, "version": ...}
  GET  /municipalities  -> list with lat/lon, pop 50-74, foreign-language share
  POST /scenario        -> body = scenario JSON, returns the result JSON
  POST /ask             -> body = {"question": "...", "history": [...]}; needs the anthropic package and ANTHROPIC_API_KEY (503 otherwise)
  POST /readout         -> body = scenario JSON; rule-based two-minute summary, no API key needed
  POST /robust          -> body = {"scenario": {...}, "n": 60, "seed": 1}, returns the robustness sweep (n capped at 150)

The same scenario.run() is what the Modal function in api/modal_app.py wraps. No auth, no CORS restrictions beyond
'*': for local development only. Do not expose it publicly as is.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

from . import paths
from . import readout, robust
from . import routing as R
from . import scenario

WEB = paths.ROOT / "web"
MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".svg": "image/svg+xml", ".png": "image/png", ".json": "application/json"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, rel: str) -> None:
        base = WEB.resolve()
        p = (base / rel).resolve()
        if base not in p.parents or p.suffix not in MIME or not p.is_file():
            return self._send(404, {"error": "not found"})
        body = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", MIME[p.suffix])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _ask(self, body: dict) -> None:
        from . import analyst
        hist = body.get("history") or []
        if not isinstance(hist, list) or len(hist) > 12:
            return self._send(400, {"error": "history must be a list of at most 12 turns"})
        try:
            self._send(200, analyst.ask(str(body.get("question", "")), history=hist, use_cache=bool(body.get("use_cache"))))
        except analyst.AnalystUnavailable as e:
            self._send(503, {"error": str(e)})
        except ValueError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:   # SDK/network errors: report the class only, never request details
            self._send(502, {"error": f"analyst call failed ({type(e).__name__}). Check ANTHROPIC_API_KEY and network."})

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._static("index.html")
        elif path == "/gap":
            self._static("gap.html")
        elif path == "/gapdata":
            f = paths.DATA / "gap" / "gapdata.json"
            self._send(200, json.loads(f.read_text(encoding="utf-8"))) if f.exists() else self._send(404, {"error": "run `python -m ctsim gap` first"})
        elif path.startswith("/vendor/") or path in ("/app.js", "/style.css"):
            self._static(path.lstrip("/"))
        elif self.path == "/health":
            self._send(200, {"ok": True, "version": scenario.VERSION})
        elif self.path == "/municipalities":
            rows = [{k: r[k] for k in ("code", "name", "lat", "lon", "pop", "f")} for r in R.load()]
            self._send(200, rows)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path not in ("/scenario", "/robust", "/ask", "/readout"):
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > 100_000:
                return self._send(413, {"error": "scenario too large"})
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/scenario":
                return self._send(200, scenario.run(body))
            if self.path == "/ask":
                return self._ask(body)
            if self.path == "/readout":
                return self._send(200, readout.run(body))
            # /robust: {"scenario": {...}, "n": 60, "seed": 1}; capped so one request cannot tie the server up for long
            n_w = min(int(body.get("n", 60)), 150)
            workers = int(os.environ.get("CTSIM_WORKERS", "1"))   # >1 spreads the sweep over local processes
            mapper = robust.process_pool_mapper(workers) if workers > 1 else None
            self._send(200, robust.run(body["scenario"], n=max(n_w, 10), seed=int(body.get("seed", 1)), voi_n=min(int(body.get("voi_n", 20)), 30), mapper=mapper))
        except (KeyError, ValueError, StopIteration) as e:
            self._send(400, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *a):
        pass


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    print(f"ctsim server on http://{host}:{port}  (local development only)")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
