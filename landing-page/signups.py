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
    print("No sign-ups yet.")
    sys.exit(0)

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
cols = ["at", "product", "beta", "postcode", "lang", "eligible", "for", "src"]
print("  ".join(f"{c:<10}" for c in cols))
for r in sorted(rows, key=lambda r: r.get("at") or "", reverse=True):
    vals = [str(r.get(c, ""))[:16].replace("T", " ") for c in cols]
    print("  ".join(f"{v:<10}" for v in vals))

if "--csv" in sys.argv:
    fields = ["at", "product", "beta", "name", "contact", "postcode", "eligible", "lang", "for", "src", "consent"]
    with open("signups.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("\nWrote signups.csv (contains personal data: do not commit or share).")
