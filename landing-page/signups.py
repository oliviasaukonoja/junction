"""Show Polku hoitoon sign-ups. Needs your own Modal login (modal setup).

    python signups.py          -> summary + table in the terminal (no contact details)
    python signups.py --csv    -> also writes signups.csv WITH names and contacts
"""
import csv
import json
import sys
from collections import Counter

import modal

vol = modal.Volume.from_name("vayla-signups")
try:
    raw = b"".join(vol.read_file("signups.jsonl")).decode("utf-8")
except Exception:
    raw = ""

rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
for r in rows:
    r.setdefault("product", "bus")

print(f"Total: {len(rows)}")
print("Interested in bus:", sum("bus" in (r.get("products") or [r["product"]]) for r in rows),
      "| app:", sum("app" in (r.get("products") or [r["product"]]) for r in rows),
      "| both:", sum(set(r.get("products") or []) == {"bus", "app"} for r in rows))
print("By language:", dict(Counter(r.get("lang") for r in rows)))
print("By source:  ", dict(Counter(r.get("src") for r in rows)))
print()
cols = ["at", "product", "beta", "postcode", "lang", "age", "smoke", "for", "src"]
print("  ".join(f"{c:<10}" for c in cols))
for r in sorted(rows, key=lambda r: r.get("at") or "", reverse=True):
    vals = [str(r.get(c, ""))[:16].replace("T", " ") for c in cols]
    print("  ".join(f"{v:<10}" for v in vals))

if "--csv" in sys.argv:
    fields = ["at", "product", "beta", "name", "contact", "postcode", "age", "smoke", "eligible", "lang", "for", "src", "consent"]
    with open("signups.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("\nWrote signups.csv (contains personal data: do not commit or share).")

print("\n--- Feedback ---")
try:
    fb = [json.loads(l) for l in b"".join(vol.read_file("feedback.jsonl")).decode("utf-8").splitlines() if l.strip()]
except Exception:
    fb = []
if not fb:
    print("No feedback yet.")
else:
    rated = [f["rating"] for f in fb if f.get("rating")]
    print(f"Total: {len(fb)}", f"| average rating: {sum(rated)/len(rated):.1f} ({len(rated)} ratings)" if rated else "")
    for f in sorted(fb, key=lambda f: f.get("at") or "", reverse=True):
        print(f"{f.get('at','')[:16].replace('T',' ')}  {f.get('page','')}  {f.get('rating') or '-'}/5  {f.get('lang','')}  {f.get('text','')}")
