"""Server-side password gate for the pilot map's advanced tools.

The default map view is public. The interactive tools (layers, colours, thresholds, assumption scenarios) are unlocked in the browser, but the
protected data (assumption scenarios, engine comparison, factor correlations) is only returned by the server after the password check, so the gate
is not just a hidden button.

Setup (one time, by whoever owns the Modal workspace):
  add the key MAP_PASSWORD to the Modal secret that the website app already uses (named in app.py), or create a new secret and add it to the
  `secrets=[...]` list. Optional second key MAP_TOKEN_KEY signs tokens; without it a key is derived from the password.
  The password is never stored in this repository. If MAP_PASSWORD is not set, the unlock endpoint answers 503 and the tools stay locked.

Limits: tokens last 4 hours and live in the browser tab (sessionStorage); failed attempts are rate-limited in memory (the app runs one container);
anyone with the password can unlock; there are no per-user accounts.
"""
import hashlib
import hmac
import os
import time

TOKEN_TTL = 4 * 3600
MAX_FAILS, WINDOW = 5, 300
_fails: dict[str, list[float]] = {}


def configured() -> bool:
    return bool(os.environ.get("MAP_PASSWORD"))


def _key() -> bytes:
    return hashlib.sha256(("polku-map|" + (os.environ.get("MAP_TOKEN_KEY") or os.environ.get("MAP_PASSWORD", ""))).encode()).digest()


def check_password(p: str) -> bool:
    if not configured() or not isinstance(p, str):
        return False
    a = hashlib.sha256(p.encode()).digest()
    b = hashlib.sha256(os.environ["MAP_PASSWORD"].encode()).digest()
    return hmac.compare_digest(a, b)


def make_token(now: float | None = None) -> str:
    exp = int((now if now is not None else time.time()) + TOKEN_TTL)
    return f"{exp}.{hmac.new(_key(), str(exp).encode(), hashlib.sha256).hexdigest()}"


def valid_token(tok: str | None, now: float | None = None) -> bool:
    if not configured() or not tok or "." not in tok:
        return False
    exp, sig = tok.split(".", 1)
    if not exp.isdigit():
        return False
    good = hmac.new(_key(), exp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good) and int(exp) > (now if now is not None else time.time())


def throttled(ip: str, now: float | None = None) -> bool:
    t = now if now is not None else time.time()
    _fails[ip] = [x for x in _fails.get(ip, []) if t - x < WINDOW]
    return len(_fails[ip]) >= MAX_FAILS


def record_fail(ip: str, now: float | None = None) -> None:
    _fails.setdefault(ip, []).append(now if now is not None else time.time())


def register(api, advanced_json: bytes) -> None:
    """Add POST /api/map/unlock and GET /api/map/advanced to a FastAPI app."""
    from fastapi import Body, HTTPException, Request
    from fastapi.responses import Response

    @api.post("/api/map/unlock")
    def map_unlock(request: Request, body: dict = Body(...)):
        if not configured():
            raise HTTPException(503, "Advanced tools are not enabled")
        ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
        if throttled(ip):
            raise HTTPException(429, "Too many attempts, try again later")
        if not check_password(str(body.get("password", ""))[:200]):
            record_fail(ip)
            time.sleep(0.6)
            raise HTTPException(401, "Wrong password")
        return {"token": make_token(), "ttl_seconds": TOKEN_TTL}

    @api.get("/api/map/advanced")
    def map_advanced(request: Request):
        if not valid_token(request.headers.get("x-map-token")):
            raise HTTPException(401, "Locked")
        return Response(advanced_json, media_type="application/json", headers={"Cache-Control": "no-store"})
