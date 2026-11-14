import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from ctsim import readout
from ctsim.server import Handler


def fake(days=150, per_extra=500, scans=2000, extra=900, budget=200):
    return {"scenario": {"region": None, "routing": {"work_days": budget}, "ct_sites": "confirmed+likely"},
            "outcomes": {"scans": scans, "additional": extra, "additional_in_places_over_60km_from_ct": extra},
            "cost": {"per_scan_eur": 400, "per_additional_eur": per_extra},
            "route": {"stops": [{"name": "A", "additional": 500, "days": 3.0}, {"name": "B", "additional": 400, "days": 2.0}], "km_per_year": 3000, "working_days": days},
            "warnings": ["CT sites: researched list"]}


class Rules(unittest.TestCase):
    def test_each_branch(self):
        self.assertIn("under-used", readout.readout(fake(days=80)))
        self.assertIn("Costly", readout.readout(fake(per_extra=1500)))
        self.assertIn("well used and well targeted", readout.readout(fake(extra=1000)))
        self.assertIn("fully used, but only", readout.readout(fake(extra=200)))

    def test_always_carries_caveats_and_fact_ids(self):
        t = readout.readout(fake())
        for needle in ("**Caveats**", "[F19]", "[F20]", "not lives saved", "To reduce uncertainty", "rules of thumb"):
            self.assertIn(needle, t)

    def test_never_claims_lives_saved(self):
        t = readout.readout(fake()).lower()
        self.assertNotIn("lives saved:", t)
        self.assertNotIn("deaths avoided", t)


class EndToEnd(unittest.TestCase):
    def test_run_and_endpoint(self):
        r = readout.run({"name": "t", "region": {"base": "Tampere", "radius_km": 80}, "ct_sites": "confirmed+likely"})
        self.assertEqual(r["model"], "rule-based readout (no AI)")
        self.assertEqual(len(r["scenarios"]), 2)                 # the plan and the 'reach most people' alternative
        self.assertEqual(r["usage"]["api_calls"], 0)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/readout", data=json.dumps({"name": "x", "region": {"base": "Kajaani", "radius_km": 100}}).encode(),
                                         headers={"Content-Type": "application/json"})
            self.assertIn("Bottom line", json.load(urllib.request.urlopen(req))["answer"])
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
