"""
Calmsight brain: the coach backend the glasses app talks to.

Deploy:   python3 -m modal deploy calmsight_brain.py
Dev mode: python3 -m modal serve calmsight_brain.py   (live reload, temporary URL)

Modal Secrets (exact names):
  gemini      -> GEMINI_API_KEY          (main voice of the coach, optional GEMINI_MODEL)
  anthropic-secret -> ANTHROPIC_API_KEY  (backup if Gemini fails)
  custom-secret    -> ELEVENLABS_API_KEY, ELEVEN_VOICE_ID
  calmsight-db     -> DATABASE_URL  (Aiven Postgres service URI)

How it learns (per person, per situation):
  * Technique choice = Thompson-sampling bandit. Each (user, situation, technique)
    has a Beta(success, fail) score. Success = fear drops >= 2 points (or to <= 3)
    by the next check-in after using that technique. New users start from what
    worked for other people with the same fear (population prior).
  * Safety guardrails decide WHICH techniques are allowed (e.g. fainters with
    needle fear never get breathing; they get applied tension / counting).
  * Pace = how many seconds this person usually needs per point of fear drop
    -> sets when the coach checks in next.
  * Talking style = learned from 1-tap feedback after each session
    (helpful / too much talking / too little) -> sets length + tone for Gemini.
"""
import os
import random
import re
import time
import uuid

import modal

app = modal.App("calmsight-brain")
COACH_VOICE = "PStJ2DzQnh8zxG5PDf1s"  # chosen ElevenLabs coach voice (library voice)
BACKUP_VOICE = "21m00Tcm4TlvDq8ikWAM"  # premade "Rachel": works on every plan
image = modal.Image.debian_slim().pip_install("fastapi[standard]", "httpx", "psycopg[binary]")

# Audio clips are short-lived binary blobs -> Modal Dict.
audio_store = modal.Dict.from_name("calmsight-audio", create_if_missing=True)


class Store:
    """Aiven Postgres (DATABASE_URL) with Modal Dict fallback.

    Tables:
      kv(ns, key, value jsonb)  -> profiles, sessions, history, learning, population
      outcomes                  -> every technique attempt (queryable analytics)
    """

    def __init__(self):
        self.conn = None
        self.fallback = {}

    def _db(self):
        url = os.environ.get("DATABASE_URL", "")
        if not url.startswith("postgres"):
            return None
        if self.conn is None or self.conn.closed:
            import psycopg
            self.conn = psycopg.connect(url, autocommit=True, connect_timeout=5)
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS kv (ns text, key text, value jsonb, "
                "updated_at timestamptz DEFAULT now(), PRIMARY KEY (ns, key))")
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS outcomes (id bigserial PRIMARY KEY, "
                "user_id text, fear text, situation text, technique text, "
                "rating_from int, rating_to int, worked boolean, seconds real, "
                "created_at timestamptz DEFAULT now())")
        return self.conn

    def _dict(self, ns):
        if ns not in self.fallback:
            self.fallback[ns] = modal.Dict.from_name(f"calmsight-{ns}", create_if_missing=True)
        return self.fallback[ns]

    def get(self, ns, key, default=None):
        try:
            db = self._db()
            if db:
                row = db.execute("SELECT value FROM kv WHERE ns=%s AND key=%s",
                                 (ns, key)).fetchone()
                return row[0] if row else default
        except Exception as e:  # noqa: BLE001
            print("db get failed, using Modal Dict:", e)
            self.conn = None
        return self._dict(ns).get(key, default)

    def set(self, ns, key, value):
        try:
            db = self._db()
            if db:
                from psycopg.types.json import Jsonb
                db.execute(
                    "INSERT INTO kv (ns, key, value) VALUES (%s, %s, %s) "
                    "ON CONFLICT (ns, key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()",
                    (ns, key, Jsonb(value)))
                return
        except Exception as e:  # noqa: BLE001
            print("db set failed, using Modal Dict:", e)
            self.conn = None
        self._dict(ns)[key] = value

    def pop(self, ns, key):
        try:
            db = self._db()
            if db:
                db.execute("DELETE FROM kv WHERE ns=%s AND key=%s", (ns, key))
                return
        except Exception as e:  # noqa: BLE001
            print("db pop failed:", e)
            self.conn = None
        self._dict(ns).pop(key, None)

    def log_outcome(self, uid, fear, situation, r):
        try:
            db = self._db()
            if db:
                db.execute(
                    "INSERT INTO outcomes (user_id, fear, situation, technique, rating_from, "
                    "rating_to, worked, seconds) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uid, fear, situation, r["tech"], r["from"], r["to"], r["worked"],
                     r.get("seconds")))
        except Exception as e:  # noqa: BLE001
            print("outcome log failed:", e)
            self.conn = None

    def backend(self):
        try:
            return "aiven-postgres" if self._db() else "modal-dict"
        except Exception:  # noqa: BLE001
            return "modal-dict"


store = Store()

# =============================================================== parsing
NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
STOP_WORDS = ("stop", "enough", "quit", "pause")
WARNING_WORDS = ("dizzy", "faint", "black out", "blacking", "can't breathe",
                 "cannot breathe", "chest pain", "pass out", "going to be sick")


def parse(text: str) -> dict:
    t = (text or "").lower()
    if any(w in t for w in WARNING_WORDS):
        return {"kind": "warning"}
    if any(re.search(rf"\b{w}\b", t) for w in STOP_WORDS):
        return {"kind": "stop"}
    m = re.search(r"\b(10|[0-9])\b", t)
    if m:
        return {"kind": "rating", "value": int(m.group(1))}
    # Spoken numbers only count in short answers ("eight", "about a six"),
    # so "this one is scary" is treated as conversation, not a rating of 1.
    if len(t.split()) <= 6 or re.search(r"\b(out of|i'?m at|about|maybe|like a|it'?s a)\b", t):
        for w, n in NUMBER_WORDS.items():
            if re.search(rf"\b{w}\b", t):
                return {"kind": "rating", "value": n}
    return {"kind": "unknown"}


SITUATIONS = {
    "spider": ("spider", "stepcloser"),
    "lift": ("lift", "elevator"),
    "injection": ("needle", "vaccin", "shot", "injection", "blood", "jab"),
    "scanner": ("mri", "scan", "ct"),
    "crowd": ("metro", "bus", "train", "crowd", "plane", "tunnel"),
    "speaking": ("speech", "presentation", "talk", "pitch", "meeting"),
}


def situation_key(text) -> str:
    t = (text or "").lower()
    for key, words in SITUATIONS.items():
        if any(w in t for w in words):
            return key
    return "other"


# =============================================================== learning
TECHNIQUES = ("breathing", "appliedTension", "grounding", "countWithMe")

# Starting beliefs from the evidence, before we know the person (alpha, beta).
# Each technique: how to coach it, how it looks on the lens, and spoken variants.
TECH = {
    "appliedTension": {"name": "Squeeze & hold", "visual": "squeeze",
        "how": "applied tension: tense legs, stomach and arms for about 10-15 seconds until the face feels warm, release for 20 seconds, repeat. Keeps blood pressure up so you don't faint.",
        "lines": ["Squeeze your thighs, stomach and fists hard. Hold… hold… and let go.",
                  "Press your knees together and make tight fists. Feel the warmth in your face. Hold it. Now release.",
                  "Tense everything below your chest like you're bracing. Ten seconds… and soften."]},
    "lookAway": {"name": "Eyes on one spot", "visual": "spot",
        "how": "choose one fixed spot away from the needle (a poster, a mark on the wall) and describe it in detail in your head.",
        "lines": ["Pick one spot on the wall, away from your arm. Tell me its colour and its shape.",
                  "Keep your eyes on one point in the room. Notice every detail of it, like you'll have to draw it later."]},
    "askNurse": {"name": "Say it out loud", "visual": "text",
        "how": "tell the nurse you are nervous; ask to lie down, to be told before it happens, or for numbing cream next time.",
        "lines": ["Tell the nurse: I'm nervous about needles. Ask if you can lie down. They hear this every day.",
                  "Say it to the nurse now: please tell me just before you start. You're allowed to ask."]},
    "breathing": {"name": "Long breath out", "visual": "breath",
        "how": "slow breathing with a longer exhale: in through the nose for 4, out through the mouth for 6.",
        "lines": ["Breathe in through your nose for four, and let it out slowly for six.",
                  "Let your breath out longer than you breathe in. In… two, three, four. Out… slowly."]},
    "grounding": {"name": "5 · 4 · 3 · 2 · 1", "visual": "list",
        "how": "5-4-3-2-1 grounding: name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste.",
        "lines": ["Name five things you can see right now. Out loud or in your head. Take your time.",
                  "Find four things you can touch. The wall, your sleeve, the floor under your feet."]},
    "findExit": {"name": "You can get out", "visual": "text",
        "how": "locate the door, the open-door button or alarm button; remind them the space opens and there is plenty of air.",
        "lines": ["Find the door-open button and the alarm button. Just look at them. You know where they are.",
                  "Notice the doors. They open in a moment. There is plenty of air in here, more than you need."]},
    "coldTouch": {"name": "Feel something cool", "visual": "text",
        "how": "touch something cool (metal handrail, wall, phone screen) and notice temperature and texture.",
        "lines": ["Put your hand on the cool handrail or the wall. Notice how cold it feels, and how solid.",
                  "Touch something metal near you. Feel the temperature. Stay with that feeling."]},
    "reframe": {"name": "It's a feeling", "visual": "text",
        "how": "name the fear as a feeling that rises and falls; it is uncomfortable, not dangerous; it peaks and passes.",
        "lines": ["This is a wave of fear. It feels big, but it isn't danger. It rises, and then it falls.",
                  "Say to yourself: this is anxiety, it's uncomfortable, and it passes. It always has."]},
    "countWithMe": {"name": "Count with me", "visual": "count",
        "how": "count slowly backwards from 20 together, or count floors, tiles or lights.",
        "lines": ["Count backwards from twenty with me. Twenty… nineteen… eighteen…",
                  "Count the lights on the ceiling, or the floors as we pass. One… two…"]},
    "humming": {"name": "Hum one note", "visual": "breath",
        "how": "hum one long low note on the out-breath; it slows the breath and the heart.",
        "lines": ["Hum one long, low note as you breathe out. Feel it in your chest.",
                  "Breathe in, and hum softly all the way out. Again."]},
}

ALLOWED = {
    "needles": ["appliedTension", "lookAway", "askNurse", "breathing", "countWithMe"],
    "needles_faint": ["appliedTension", "lookAway", "askNurse", "countWithMe"],
    "spaces": ["findExit", "grounding", "coldTouch", "reframe", "breathing", "countWithMe", "humming"],
    "spiders": ["breathing", "grounding", "reframe", "countWithMe"],
    "speaking": ["breathing", "grounding", "reframe", "humming"],
}

# Starting beliefs from the evidence, before we know the person (alpha, beta).
CLINICAL_PRIOR = {
    "needles": {"appliedTension": (4, 1), "lookAway": (3, 1), "askNurse": (2, 1),
                "breathing": (2, 1), "countWithMe": (2, 1)},
    "spaces": {"findExit": (3, 1), "grounding": (3, 1), "breathing": (3, 1),
               "reframe": (2, 1), "coldTouch": (2, 1), "countWithMe": (2, 1), "humming": (2, 1)},
    "spiders": {"breathing": (3, 1), "grounding": (3, 1), "reframe": (2, 1), "countWithMe": (2, 1)},
    "speaking": {"breathing": (3, 1), "grounding": (2, 1), "reframe": (3, 1), "humming": (2, 1)},
}
TECHNIQUES = tuple(TECH)


def allowed_techniques(profile: dict) -> list:
    """Safety guardrails: the bandit may only pick from these."""
    fear = profile.get("fear", "spaces")
    if fear == "needles" and profile.get("faint_history"):
        # Vasovagal fainting: relaxation/breathing can lower blood pressure further.
        return ALLOWED["needles_faint"]
    return ALLOWED.get(fear, ALLOWED["spaces"])


def prior(profile: dict, tech: str, pop: dict) -> tuple:
    a, b = CLINICAL_PRIOR.get(profile.get("fear", "needles"), {}).get(tech, (1, 1))
    pa, pb = pop.get(f"{profile.get('fear')}|{tech}", (0, 0))
    # Other people's results count, but less than this person's own.
    return a + 0.3 * pa, b + 0.3 * pb


def choose_technique(profile: dict, situation: str, stats: dict, pop: dict,
                     rng=random, avoid=()) -> dict:
    """Thompson sampling over allowed techniques. Returns choice + reason."""
    best, best_draw, scores = None, -1.0, {}
    options = [t for t in allowed_techniques(profile) if t not in avoid] or allowed_techniques(profile)
    for tech in options:
        pa, pb = prior(profile, tech, pop)
        s, f = stats.get(f"{situation}|{tech}", (0, 0))
        a, b = pa + s, pb + f
        draw = rng.betavariate(a, b)
        scores[tech] = {"expected": round(a / (a + b), 2), "tries": s + f,
                        "worked": s}
        if draw > best_draw:
            best, best_draw = tech, draw
    sc = scores[best]
    if sc["tries"]:
        reason = (f"{TECH[best]['name']} worked {sc['worked']} of {sc['tries']} times "
                  f"for you here")
    else:
        reason = f"{TECH[best]['name']}: a strong first choice for this fear"
    return {"technique": best, "reason": reason, "scores": scores}


MAX_LEVEL = 6


def recommend_level(action: str, rating, level):
    """Exposure ladder advice. The person always chooses; we only suggest."""
    if level is None:
        return None
    level = int(level)
    if action == "complete" and level < MAX_LEVEL:
        return {"level": level + 1, "advice": "ready", "text": f"Ready to try step {level + 1} when you choose."}
    if action == "complete":
        return {"level": level, "advice": "ready", "text": "You finished the hardest step. Repeat it whenever you like."}
    if action == "calm" and rating is not None and rating >= 9 and level > 1:
        return {"level": level - 1, "advice": "easier", "text": f"It's fine to go back to step {level - 1}. Stopping is also fine."}
    if action == "pause":
        return {"level": max(1, level - 1), "advice": "pause", "text": "Pause now. Come back only when you choose."}
    return {"level": level, "advice": "stay", "text": "Stay with this step for now."}


def outcome(prev_rating: int, new_rating: int) -> bool:
    return (prev_rating - new_rating) >= 2 or new_rating <= 3


def update_pace(pace: dict, prev_rating: int, new_rating: int, seconds: float) -> dict:
    drop = prev_rating - new_rating
    if drop > 0 and seconds > 0:
        per_point = seconds / drop
        n = pace.get("n", 0)
        avg = pace.get("sec_per_point", per_point)
        pace = {"n": n + 1, "sec_per_point": (avg * n + per_point) / (n + 1)}
    return pace


def next_check_in(pace: dict) -> int:
    # Check back after roughly the time a 2-point drop usually takes for them.
    spp = pace.get("sec_per_point")
    return 30 if not spp else int(max(15, min(90, 2 * spp)))


STYLE_WORDS = {-1: 15, 0: 28, 1: 45}
STYLE_TONE = {-1: "very brief, calm, almost no extra words",
              0: "warm and short",
              1: "warm, encouraging, a little more reassurance"}


def update_style(style: int, feedback: str) -> int:
    if feedback == "tooMuch":
        style -= 1
    elif feedback == "tooLittle":
        style += 1
    return max(-1, min(1, style))


# =============================================================== decisions
def decide(session: dict, profile: dict, parsed: dict, now: float) -> dict:
    """Rules decide the step; the bandit picks the technique inside 'calm'."""
    if parsed["kind"] == "warning":
        return {"action": "pause", "reason": "warningSign"}
    if parsed["kind"] == "stop":
        return {"action": "stop"}
    if parsed["kind"] != "rating":
        return {"action": "ask"}

    r = parsed["value"]
    if session.get("step_start") is None:
        session["step_start"] = r
    session["ratings"].append(r)
    session["times"].append(now)

    if r >= 7:
        return {"action": "calm", "rating": r}
    if r <= 3 or r <= session["step_start"] / 2:
        return {"action": "complete", "rating": r}
    prev = session["ratings"][-2] if len(session["ratings"]) > 1 else None
    return {"action": "stay", "rating": r, "praise": prev is not None and r < prev}


def learn_from_turn(session: dict, stats: dict, pace: dict, pop: dict, profile: dict):
    """Credit the last technique used with the newest rating."""
    last = session.get("pending")  # {"tech", "rating", "t"}
    if not last or not session["ratings"]:
        return stats, pace, pop
    new_r, new_t = session["ratings"][-1], session["times"][-1]
    ok = outcome(last["rating"], new_r)
    k = f"{session['situation']}|{last['tech']}"
    s, f = stats.get(k, (0, 0))
    stats[k] = (s + 1, f) if ok else (s, f + 1)
    pk = f"{profile.get('fear')}|{last['tech']}"
    ps, pf = pop.get(pk, (0, 0))
    pop[pk] = (ps + 1, pf) if ok else (ps, pf + 1)
    pace = update_pace(pace, last["rating"], new_r, new_t - last["t"])
    session.setdefault("results", []).append(
        {"tech": last["tech"], "from": last["rating"], "to": new_r, "worked": ok,
         "seconds": round(new_t - last["t"], 1)})
    session["pending"] = None
    return stats, pace, pop


# =============================================================== words
FALLBACK = {
    "start": "Hi {name}. I'm right here with you. How scared are you right now, from 0 to 10?",
    "ask": "Just tell me a number from 0 to 10. How scared are you?",
    "appliedTension": "{name}, squeeze your legs, your stomach and your fists. Hold it… hold… and release. How scared now, 0 to 10?",
    "breathing": "{name}, breathe in slowly for four… and out for six. Once more. How scared now, 0 to 10?",
    "grounding": "{name}, name three things you can see right now. You are safe. How scared now, 0 to 10?",
    "countWithMe": "{name}, count backwards from 20 with me, slowly. Twenty… nineteen… eighteen. How scared now, 0 to 10?",
    "stay_praise": "It's coming down, {name}. You're doing this. Stay with it. Number now?",
    "stay": "You're holding steady, {name}. Slow and easy. Number now?",
    "complete": "{name}, that's it. You went from {first} down to {last}. You did that yourself.",
    "pause": "Stop here, {name}. Tell the nurse or someone next to you that you feel faint, right now. Sit with your head low.",
    "stop": "Okay, stopping now. You did well, {name}.",
    "chat": "I hear you, {name}. I'm right here. On a scale from 0 to 10, how scared are you right now?",
}


def fallback_line(key: str, profile: dict, session: dict) -> str:
    rs = session.get("ratings") or [0]
    name = profile.get("name") or ""
    name = "" if name.lower() == "there" else name
    if key in TECH:
        used = session.get("lines_used", 0)
        text = TECH[key]["lines"][used % len(TECH[key]["lines"])] + " Then tell me your number."
        return (f"{name}, " + text[0].lower() + text[1:]) if name else text
    text = FALLBACK[key].format(name=name or "you", first=rs[0], last=rs[-1])
    return text.replace("you, ", "").replace(", you.", ".").replace("Hi you.", "Hi.").replace(" you.", ".") if not name else text


def build_prompt(base: str, profile: dict, style: int, memory: str, key: str,
                 session: dict = None) -> str:
    session = session or {}
    tech = TECH.get(key)
    task = (f"Coach this technique now: {tech['how']}" if tech else f"Say this: {base}")
    name = profile.get("name") if (profile.get("name") or "there").lower() != "there" else None
    recent = " | ".join(session.get("said", [])[-3:])
    return (
        "You are Calmsight, a warm, expert fear coach speaking into someone's ear through smart "
        "glasses, live, in the scary moment itself. Talk like a calm friend who knows exposure therapy.\n"
        f"Situation right now: {session.get('situationText') or session.get('situation') or 'unknown'}. "
        f"Fear: {profile.get('fear')}. Fear ratings so far: {session.get('ratings') or 'none'}.\n"
        f"{memory}\n{task}\n"
        "Make it concrete to THIS situation (e.g. lift: buttons, doors, floors; injection: nurse, arm, chair). "
        "One instruction at a time. Do not mention breathing unless the technique is breathing or humming. "
        f"Do not repeat these recent lines: {recent or 'none'}.\n"
        f"Spoken style, short sentences, no emojis, no lists, max {STYLE_WORDS[style]} words. "
        f"Tone: {STYLE_TONE[style]}. "
        + (f"Use the name {name} at most once. " if name else "Do not use any name. ")
        + "Never give medical advice beyond the technique. Return only the line."
    )


def chat_prompt(heard: str, profile: dict, session: dict, style: int, memory: str) -> str:
    rs = session.get("ratings") or []
    return (
        "You are Calmsight, a calm fear coach speaking into someone's ear through smart glasses. "
        f"The person just said: \"{heard}\". "
        f"Their fear: {profile.get('fear')}. Situation: {session.get('situationText') or session.get('situation')}. "
        f"Fear ratings so far: {rs or 'none yet'}. {memory}\n"
        "Reply in spoken style: acknowledge what they said in their own words, keep them grounded, "
        f"max {STYLE_WORDS[style]} words, no medical advice, no lists, no emojis. "
        + ("End by asking how scared they are from 0 to 10. " if not rs else
           "End by gently asking for their fear number now, 0 to 10. ")
        + "If they mention feeling faint, dizzy or unable to breathe, tell them to sit down and tell someone nearby right now. "
        f"Use their name ({profile.get('name')}) at most once. Return only the line."
    )


LLM_ERRORS = []


def llm_line(prompt: str, base: str) -> tuple:
    """Gemini first, Claude as backup, built-in line last. Returns (text, source)."""
    import httpx
    gk = os.environ.get("GEMINI_API_KEY")
    if gk:
        try:
            model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
            r = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": gk},
                json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=8)
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            t = "".join(x.get("text", "") for x in r.json()["candidates"][0]["content"]["parts"] if not x.get("thought")).strip()
            if t:
                return t, "gemini"
        except Exception as e:  # noqa: BLE001
            print("gemini failed:", e)
            LLM_ERRORS.append(f"gemini: {str(e)[:200]}")
    ak = os.environ.get("ANTHROPIC_API_KEY")
    if ak:
        try:
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ak, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5"),
                      "max_tokens": 150,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=6)
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            t = r.json()["content"][0]["text"].strip()
            if t:
                return t, "claude"
        except Exception as e:  # noqa: BLE001
            print("claude failed:", e)
            LLM_ERRORS.append(f"claude: {str(e)[:200]}")
    return base, "builtin"


def speak(text: str, base_url: str):
    key, voice = os.environ.get("ELEVENLABS_API_KEY"), os.environ.get("ELEVEN_VOICE_ID", COACH_VOICE)
    if not (key and voice):
        return None
    import httpx
    try:
        for v in dict.fromkeys([voice, BACKUP_VOICE]):
            r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{v}",
                           params={"output_format": "mp3_44100_128"},
                           headers={"xi-api-key": key},
                           json={"text": text, "model_id": "eleven_flash_v2_5"},
                           timeout=10)
            if r.status_code not in (401, 402, 403):
                break
            print("elevenlabs voice", v, "refused:", r.status_code, r.text[:200])
        r.raise_for_status()
        aid = uuid.uuid4().hex
        audio_store[aid] = r.content
        return f"{base_url}/audio/{aid}.mp3"
    except Exception as e:  # noqa: BLE001
        print("elevenlabs failed:", e)
        return None


# =============================================================== StepCloser voice
@app.function(image=image, secrets=[modal.Secret.from_name("custom-secret")], timeout=600)
def tts_many(texts: dict) -> dict:
    """Generate ElevenLabs MP3s for many prompts (keys stay in Modal)."""
    import httpx
    key, voice = os.environ["ELEVENLABS_API_KEY"], os.environ.get("ELEVEN_VOICE_ID", COACH_VOICE)
    out = {}
    for name, text in texts.items():
        r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                       params={"output_format": "mp3_44100_128"},
                       headers={"xi-api-key": key},
                       json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=60)
        if r.status_code in (401, 402, 403) and voice != BACKUP_VOICE:
            print("voice", voice, "refused:", r.status_code, r.text[:300])
            print("-> switching to premade backup voice", BACKUP_VOICE)
            voice = BACKUP_VOICE
            r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                           params={"output_format": "mp3_44100_128"},
                           headers={"xi-api-key": key},
                           json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=60)
        if r.status_code >= 400:
            print("ElevenLabs error:", r.status_code, r.text[:500])
        r.raise_for_status()
        out[name] = r.content
        print("voiced", name, len(r.content))
    return out


@app.local_entrypoint()
def voice_stepcloser(prompts: str = "../stepcloser/android/app/src/main/assets/web/prompts.mjs",
                     outdir: str = "../stepcloser/android/app/src/main/assets/web/audio"):
    """python3 -m modal run calmsight_brain.py::voice_stepcloser  -> replaces robotic clips."""
    import json
    import pathlib
    src = pathlib.Path(prompts).read_text()
    body = src[src.index("{"): src.rindex("}") + 1]
    body = re.sub(r"(\b[a-z0-9_]+)\s*:", r'"\1":', body)
    texts = json.loads(body)
    clips = tts_many.remote(texts)
    for name, data in clips.items():
        pathlib.Path(outdir, f"{name}.mp3").write_bytes(data)
    print(f"Wrote {len(clips)} ElevenLabs clips to {outdir}")


# =============================================================== api
@app.function(image=image,
              secrets=[modal.Secret.from_name("gemini"),
                       modal.Secret.from_name("anthropic-secret"),
                       modal.Secret.from_name("custom-secret"),   # ElevenLabs
                       modal.Secret.from_name("calmsight-db")])   # Aiven Postgres DATABASE_URL
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, Response

    api = FastAPI(title="Calmsight brain")
    api.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_methods=["*"], allow_headers=["*"])

    def base(req: Request) -> str:
        return str(req.base_url).rstrip("/").replace("http://", "https://")

    def get_profile(uid):
        return store.get("profiles", uid) or {"userId": uid, "name": "there",
                                     "fear": "needles", "faint_history": False}

    def get_learning(uid):
        return store.get("learning", uid) or {"stats": {}, "pace": {}, "style": 0}

    def memory_text(uid, situation):
        past = [h for h in store.get("history", uid, []) if h.get("situation") == situation] \
            or store.get("history", uid, [])
        if not past:
            return "First session."
        h = past[-1]
        return (f"Last time ({h.get('situation')}): fear went {h['first']} to "
                f"{h['last']} using {', '.join(h['techniques']) or 'talking'}.")

    def respond(req, uid, profile, session, decision, key, lrn):
        prompt = build_prompt(fallback_line(key, profile, session), profile,
                              lrn.get("style", 0),
                              memory_text(uid, session.get("situation")), key, session)
        line, source = llm_line(prompt, fallback_line(key, profile, session))
        session["said"] = (session.get("said", []) + [line])[-6:]
        session["lines_used"] = session.get("lines_used", 0) + 1
        rating = decision.get("rating")
        tech = TECH.get(decision.get("technique") or "")
        label = {"calm": tech["name"] if tech else "", "stay": "Keep going",
                 "complete": "You did it", "pause": "Tell the nurse",
                 "stop": "Stopped", "ask": "0 – 10?", "start": "0 – 10?"
                 }.get(decision["action"], "")
        return {**decision, "line": line, "lineSource": source,
                "audioUrl": speak(line, base(req)),
                "nextCheckInSec": next_check_in(lrn.get("pace", {})),
                "display": {"big": "" if rating is None else str(rating),
                            "label": label, "visual": tech["visual"] if tech else "text",
                            "showStop": decision["action"] not in ("stop", "complete")}}

    def finish(uid, session):
        if session.get("ratings"):
            past = store.get("history", uid, [])
            past.append({"first": session["ratings"][0], "last": session["ratings"][-1],
                         "techniques": sorted({r["tech"] for r in session.get("results", [])}
                                              | set(session.get("techniques", []))),
                         "situation": session.get("situation"), "at": time.time()})
            store.set("history", uid, past[-50:])
        store.pop("sessions", uid)

    @api.post("/profile")
    async def set_profile(body: dict):
        p = {"userId": body["userId"], "name": body.get("name", "there"),
             "fear": body.get("fear", "needles"),
             "faint_history": bool(body.get("faintHistory", False))}
        store.set("profiles", p["userId"], p)
        return p

    @api.post("/start")
    async def start(req: Request, body: dict):
        uid = body["userId"]
        profile = get_profile(uid)
        session = {"ratings": [], "times": [], "techniques": [], "step_start": None,
                   "situation": situation_key(body.get("situation")),
                   "situationText": body.get("situation"), "pending": None,
                   "level": body.get("level")}
        store.set("sessions", uid, session)
        out = respond(req, uid, profile, session, {"action": "start",
                      "situation": session["situation"]}, "start", get_learning(uid))
        return out

    @api.post("/turn")
    async def turn(req: Request, body: dict):
        uid = body["userId"]
        now = time.time()
        profile, lrn = get_profile(uid), get_learning(uid)
        session = store.get("sessions", uid) or {"ratings": [], "times": [], "techniques": [],
                                        "step_start": None, "situation": "other",
                                        "pending": None}
        pop = dict(store.get("population", "all", {}))
        if body.get("level") is not None:
            session["level"] = body.get("level")
        d = decide(session, profile, parse(body.get("text", "")), now)

        if d.get("rating") is not None:
            n_before = len(session.get("results", []))
            lrn["stats"], lrn["pace"], pop = learn_from_turn(
                session, lrn["stats"], lrn["pace"], pop, profile)
            for res in session.get("results", [])[n_before:]:
                store.log_outcome(uid, profile.get("fear"), session["situation"], res)

        if d["action"] == "ask" and (body.get("text") or "").strip():
            heard = body["text"].strip()
            sit = situation_key(heard)
            if sit != "other" and not session.get("ratings"):
                session["situation"], session["situationText"] = sit, heard
            d = {"action": "chat", "heard": heard}
            line, source = llm_line(chat_prompt(heard, profile, session, lrn.get("style", 0),
                                                memory_text(uid, session.get("situation"))),
                                    fallback_line("chat", profile, session))
            store.set("sessions", uid, session)
            last = (session.get("ratings") or [None])[-1]
            return {**d, "line": line, "lineSource": source, "audioUrl": speak(line, base(req)),
                    "nextCheckInSec": next_check_in(lrn.get("pace", {})), "nextStep": None,
                    "display": {"big": "" if last is None else str(last), "label": "Listening",
                                "showStop": True}}
        if d["action"] == "calm":
            res = session.get("results") or []
            avoid = {res[-1]["tech"]} if res and not res[-1]["worked"] else set()
            if session.get("techniques"):
                avoid.add(session["techniques"][-1]) if len(session["techniques"]) >= 2 and \
                    session["techniques"][-1] == session["techniques"][-2] else None
            pick = choose_technique(profile, session["situation"], lrn["stats"], pop, avoid=avoid)
            d.update(technique=pick["technique"], why=pick["reason"])
            session["techniques"].append(pick["technique"])
            session["pending"] = {"tech": pick["technique"], "rating": d["rating"], "t": now}
            key = pick["technique"]
        elif d["action"] == "stay":
            key = "stay_praise" if d.get("praise") else "stay"
        else:
            key = d["action"]

        store.set("learning", uid, lrn)
        store.set("population", "all", pop)
        out = respond(req, uid, profile, session, d, key, lrn)
        out["nextStep"] = recommend_level(d["action"], d.get("rating"), session.get("level"))
        if d["action"] in ("complete", "stop", "pause"):
            finish(uid, session)
        else:
            store.set("sessions", uid, session)
        return out

    @api.post("/stop")
    async def stop(body: dict):
        uid = body["userId"]
        profile = get_profile(uid)
        session = store.get("sessions", uid) or {"ratings": []}
        finish(uid, session)
        return {"action": "stop", "line": fallback_line("stop", profile, session),
                "audioUrl": None, "nextCheckInSec": None,
                "display": {"big": "", "label": "Stopped", "showStop": False}}

    @api.post("/feedback")
    async def feedback(body: dict):
        """After a session: 'helpful' | 'tooMuch' | 'tooLittle'."""
        uid = body["userId"]
        lrn = get_learning(uid)
        lrn["style"] = update_style(lrn.get("style", 0), body.get("feedback", "helpful"))
        store.set("learning", uid, lrn)
        return {"style": lrn["style"], "maxWords": STYLE_WORDS[lrn["style"]]}

    @api.get("/insights/{uid}")
    async def insights(uid: str):
        """What Calmsight has learned about this person (for the phone app + demo)."""
        profile, lrn = get_profile(uid), get_learning(uid)
        pop = store.get("population", "all", {})
        per_situation = {}
        for sit in list(SITUATIONS) + ["other"]:
            rows = []
            for tech in allowed_techniques(profile):
                pa, pb = prior(profile, tech, pop)
                s, f = lrn["stats"].get(f"{sit}|{tech}", (0, 0))
                if s + f:
                    rows.append({"technique": tech, "worked": s, "tries": s + f,
                                 "successRate": round((pa + s) / (pa + pb + s + f), 2)})
            if rows:
                per_situation[sit] = sorted(rows, key=lambda x: -x["successRate"])
        return {"profile": profile, "bestBySituation": per_situation,
                "paceSecPerPoint": round(lrn["pace"].get("sec_per_point", 0), 1) or None,
                "nextCheckInSec": next_check_in(lrn["pace"]),
                "talkingStyle": {-1: "brief", 0: "normal", 1: "more support"}[lrn.get("style", 0)],
                "sessions": store.get("history", uid, [])[-10:]}

    @api.get("/audio/{aid}.mp3")
    async def audio(aid: str):
        data = audio_store.get(aid)
        return Response(status_code=404) if data is None else Response(
            content=data, media_type="audio/mpeg")

    @api.get("/health")
    async def health():
        return {"ok": True, "storage": store.backend(),
                "gemini": os.environ.get("GEMINI_API_KEY", "none") not in ("", "none"),
                "claude": os.environ.get("ANTHROPIC_API_KEY", "none") not in ("", "none"),
                "elevenlabs": bool(os.environ.get("ELEVENLABS_API_KEY")),
                "voice": os.environ.get("ELEVEN_VOICE_ID", COACH_VOICE),
                "lastLlmErrors": LLM_ERRORS[-4:]}

    @api.get("/glasses", response_class=HTMLResponse)
    async def glasses_page():
        return GLASSES_PAGE

    @api.get("/", response_class=HTMLResponse)
    async def test_page():
        return TEST_PAGE

    return api


TEST_PAGE = """<!doctype html><meta name=viewport content="width=device-width">
<title>Calmsight test</title>
<style>body{font:15px system-ui;background:#000;color:#eee;max-width:760px;margin:24px auto;padding:0 16px}
input,select,button{font:inherit;padding:7px 10px;margin:3px 2px;border-radius:8px;border:1px solid #444;background:#111;color:#eee}
button{cursor:pointer}#row{display:flex;gap:20px;flex-wrap:wrap}
#glass{width:280px;height:280px;border:2px solid #333;border-radius:24px;display:flex;flex-direction:column;align-items:center;justify-content:center}
#big{font-size:96px;font-weight:700}#lbl{font-size:20px;color:#8cf}#why{font-size:12px;color:#888;margin-top:6px;text-align:center;padding:0 10px}
#log{white-space:pre-wrap;color:#aaa;font-size:13px;margin-top:10px}pre{background:#111;padding:10px;border-radius:8px;font-size:12px;overflow:auto;max-height:280px;flex:1;min-width:260px}</style>
<h2>Calmsight brain · test</h2>
<div>Name <input id=name value=Kristine size=10> Fear <select id=fear><option>needles<option>spaces<option>speaking</select>
<label><input type=checkbox id=faint> fainted before</label> <button onclick=saveProfile()>Save profile</button></div>
<div>Situation <input id=sit value="lift" size=14> <button onclick="go('/start',{situation:sit.value})">Start</button>
<input id=say placeholder='eight / I feel dizzy / stop' size=24><button onclick=send()>Send</button>
<button onclick="go('/stop',{})">Stop</button></div>
<div>After session: <button onclick="fb('helpful')">👍 helpful</button><button onclick="fb('tooMuch')">too much talking</button><button onclick="fb('tooLittle')">too little</button>
<button onclick=ins()>What has it learned?</button></div>
<div id=row><div><div id=glass><div id=big></div><div id=lbl></div><div id=why></div></div></div><pre id=learned>(insights)</pre></div>
<div id=log></div>
<script>
const uid='demo',H={'content-type':'application/json'};
const post=(p,b)=>fetch(p,{method:'POST',headers:H,body:JSON.stringify({userId:uid,...b})}).then(r=>r.json());
async function saveProfile(){await post('/profile',{name:name.value,fear:fear.value,faintHistory:faint.checked});note('profile saved')}
function note(t){log.textContent=t+'\\n'+log.textContent}
async function go(p,b){const j=await post(p,b);big.textContent=j.display.big;lbl.textContent=j.display.label;why.textContent=j.why||'';
note(`[${j.action}${j.technique?' · '+j.technique:''}] (${j.lineSource||'-'}) ${j.line}${j.nextCheckInSec?'  ⏱ '+j.nextCheckInSec+'s':''}`);
if(j.audioUrl){new Audio(j.audioUrl).play()}else{speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(j.line))}
if(['complete','stop','pause'].includes(j.action))ins()}
function send(){go('/turn',{text:say.value});say.value=''}
async function fb(f){const j=await post('/feedback',{feedback:f});note('style now: '+JSON.stringify(j));ins()}
async function ins(){learned.textContent=JSON.stringify(await fetch('/insights/'+uid).then(r=>r.json()),null,1)}
say.addEventListener('keydown',e=>{if(e.key==='Enter')send()});ins()
</script>"""


# Meta Ray-Ban Display web app: 600x600, black = transparent, arrows + Enter input.
GLASSES_PAGE = """<!doctype html><meta name=viewport content="width=600,height=600">
<title>Calmsight</title>
<style>html,body{margin:0;background:#000;color:#fff;font-family:system-ui;width:600px;height:600px;overflow:hidden}
#w{width:600px;height:600px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
#ring{width:300px;height:300px;border-radius:50%;border:6px solid #4fd1c5;display:flex;flex-direction:column;
align-items:center;justify-content:center;transition:transform 4s ease-in-out}
#big{font-size:140px;font-weight:700;line-height:1}#lbl{font-size:30px;color:#8cf;margin-top:6px}
#hint{font-size:24px;color:#aaa;margin-top:26px;max-width:520px}#line{font-size:26px;margin-top:14px;max-width:540px;color:#ddd}
.breathe{animation:b 10s ease-in-out infinite}@keyframes b{0%{transform:scale(.8)}40%{transform:scale(1.1)}100%{transform:scale(.8)}}
</style>
<div id=w><div id=ring><div id=big>5</div><div id=lbl>How scared?</div></div>
<div id=line></div><div id=hint>Swipe ▲▼ to rate · Press to send</div></div>
<script>
const uid=new URLSearchParams(location.search).get('u')||'demo';
const sit=new URLSearchParams(location.search).get('s')||'lift';
let rating=5,busy=false,ended=false;
const $=id=>document.getElementById(id);
const post=(p,b)=>fetch(p,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({userId:uid,...b})}).then(r=>r.json());
function say(j){$('line').textContent=j.line||'';
 const tts=()=>{try{speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(j.line))}catch(e){}};
 if(j.audioUrl){const a=new Audio(j.audioUrl);a.play().catch(tts)}else tts()}
function show(j){if(j.display){ if(j.display.big!=='')$('big').textContent=j.display.big; $('lbl').textContent=j.display.label||''}
 $('ring').classList.toggle('breathe',j.action==='calm');
 if(['complete','stop','pause'].includes(j.action)){ended=true;$('hint').textContent=j.action==='pause'?'Tell someone near you now':'Press to start again'}
 else $('hint').textContent='Swipe ▲▼ to rate · Press to send'}
async function call(p,b){if(busy)return;busy=true;try{const j=await post(p,b);show(j);say(j)}catch(e){$('line').textContent='Offline - breathe in 4, out 6.'}busy=false}
function start(){ended=false;rating=5;$('big').textContent=rating;call('/start',{situation:sit})}
addEventListener('keydown',e=>{
 if(e.key==='ArrowUp'||e.key==='ArrowRight'){rating=Math.min(10,rating+1);$('big').textContent=rating;$('lbl').textContent='How scared?'}
 else if(e.key==='ArrowDown'||e.key==='ArrowLeft'){rating=Math.max(0,rating-1);$('big').textContent=rating;$('lbl').textContent='How scared?'}
 else if(e.key==='Enter'||e.key===' '){ended?start():call('/turn',{text:String(rating)})}
});
history.pushState({c:1},'');addEventListener('popstate',()=>{post('/stop',{});speechSynthesis.cancel();$('lbl').textContent='Stopped';ended=true;history.pushState({c:1},'')});
start();
</script>"""
