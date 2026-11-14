import json
import threading
import unittest
import urllib.request
from http.server import HTTPServer

from ctsim import paths, scenario
from ctsim.server import Handler


class ScenarioTests(unittest.TestCase):
    def test_all_shipped_configs_run(self):
        files = sorted((paths.CONFIGS / "scenarios").glob("*.json"))
        self.assertGreaterEqual(len(files), 3)
        for f in files:
            out = scenario.run(scenario.load(f))
            self.assertGreater(out["outcomes"]["scans"], 0, f.name)
            self.assertLessEqual(out["route"]["working_days"], scenario.R.DEFAULT["work_days"] + 1e-6, f.name)
            self.assertTrue(all(s["lat"] is not None for s in out["route"]["stops"]))
            json.dumps(out)   # must be serialisable

    def test_same_scenario_same_hash_and_result(self):
        scn = {"name": "t", "region": {"base": "Tampere", "radius_km": 80}}
        a, b = scenario.run(scn), scenario.run(dict(scn))
        self.assertEqual(a["scenario_hash"], b["scenario_hash"])
        self.assertEqual(a["route"]["order"], b["route"]["order"])

    def test_layer_covers_every_municipality_and_matches_totals(self):
        out = scenario.run({"name": "t", "region": {"base": "Tampere", "radius_km": 100}})
        self.assertEqual(len(out["layer"]), 308)
        served = sum(m["additional"] for m in out["layer"])
        self.assertAlmostEqual(served, out["outcomes"]["additional"], delta=len(out["layer"]) * 0.05)   # per-row rounding only
        stops = {s["name"] for s in out["route"]["stops"]}
        self.assertTrue({m["stop"] for m in out["layer"] if m["stop"]} <= stops)

    def test_unknown_parameter_is_rejected(self):
        with self.assertRaises(KeyError):
            scenario.run({"name": "bad", "model": {"not_a_parameter": 1}})


class ServerTests(unittest.TestCase):
    def test_http_roundtrip(self):
        srv = HTTPServer(("127.0.0.1", 0), Handler)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            base = f"http://127.0.0.1:{port}"
            self.assertTrue(json.load(urllib.request.urlopen(base + "/health"))["ok"])
            self.assertEqual(len(json.load(urllib.request.urlopen(base + "/municipalities"))), 308)
            req = urllib.request.Request(base + "/scenario", data=json.dumps({"name": "x", "region": {"base": "Kajaani", "radius_km": 100}}).encode(),
                                         headers={"Content-Type": "application/json"})
            self.assertIn("route", json.load(urllib.request.urlopen(req)))
            bad = urllib.request.Request(base + "/scenario", data=b'{"model":{"zzz":1}}', headers={"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(bad)
            self.assertEqual(cm.exception.code, 400)
            page = urllib.request.urlopen(base + "/").read().decode()
            self.assertIn("Mobile CT screening planner", page)
            self.assertTrue(urllib.request.urlopen(base + "/vendor/leaflet.js").read().startswith(b"/* @preserve"))
            for evil in ("/vendor/../../src/ctsim/paths.py", "/vendor/%2e%2e/%2e%2e/pyproject.toml", "/vendor/../index.html.bak"):
                with self.assertRaises(urllib.error.HTTPError) as c2:
                    urllib.request.urlopen(base + evil)
                self.assertEqual(c2.exception.code, 404, evil)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
