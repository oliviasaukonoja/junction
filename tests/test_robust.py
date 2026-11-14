import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from ctsim import robust, routing as R
from ctsim.server import Handler

SCN = {"name": "t", "region": {"base": "Tampere", "radius_km": 100}}


class RobustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = robust.run(SCN, n=16, seed=3, voi_n=6, n_sampled_plans=3)

    def test_deterministic_for_a_seed(self):
        again = robust.run(SCN, n=16, seed=3, voi_n=6, n_sampled_plans=3)
        self.assertEqual(json.dumps(self.r["plans"], sort_keys=True), json.dumps(again["plans"], sort_keys=True))
        self.assertEqual(self.r["recommended"], again["recommended"])
        self.assertNotEqual(self.r["stability"], robust.run(SCN, n=16, seed=4, voi_n=6, n_sampled_plans=3)["stability"])

    def test_frequencies_and_regrets_are_valid(self):
        for m in self.r["stability"]:
            self.assertTrue(0 <= m["select_freq"] <= 1 and 0 <= m["served_freq"] <= 1)
        for p in self.r["plans"]:
            self.assertTrue(0 <= p["mean_regret"] <= p["max_regret"] <= 1, p["name"])
            self.assertLessEqual(p["additional_p5"], p["additional_p95"])
        self.assertTrue(all(v["expected_regret_pct"] >= 0 for v in self.r["voi"]))

    def test_plans_sorted_and_recommended_is_best(self):
        keys = [(p["p90_regret"], p["mean_regret"]) for p in self.r["plans"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(self.r["recommended"], self.r["plans"][0]["name"])

    def test_plans_respect_budget_and_region(self):
        budget = R.DEFAULT["work_days"]
        for p in self.r["plans"]:
            self.assertLessEqual(p["days"], budget + 1e-6, p["name"])
        self.assertLessEqual(self.r["recommended_plan"]["days"], budget + 1e-6)

    def test_ct_sites_are_a_listed_source_of_uncertainty(self):
        self.assertIn("ct_sites", {v["param"] for v in self.r["voi"]})

    def test_result_is_independent_of_how_the_work_is_split(self):
        import pickle
        kw = dict(n=12, seed=3, voi_n=4, n_sampled_plans=3)

        def serialising_mapper(jobs):                     # what a remote mapper does: pickle jobs out and results back
            return [pickle.loads(pickle.dumps(robust.TASKS[k](*pickle.loads(pickle.dumps((scn, chunk, extra)))))) for k, scn, chunk, extra in jobs]

        ref = json.dumps(robust.run(SCN, chunk=8, **kw), sort_keys=True, default=str)
        for label, mapper, chunk in (("small chunks", None, 2), ("serialising", serialising_mapper, 3), ("process pool", robust.process_pool_mapper(2), 4)):
            got = json.dumps(robust.run(SCN, mapper=mapper, chunk=chunk, **kw), sort_keys=True, default=str)
            self.assertEqual(got, ref, label)

    def test_server_endpoint_and_cap(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/robust", data=json.dumps({"scenario": SCN, "n": 12, "voi_n": 4}).encode(),
                                         headers={"Content-Type": "application/json"})
            out = json.load(urllib.request.urlopen(req))
            self.assertIn("stability", out)
            bad = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}/robust", data=b'{"n": 12}', headers={"Content-Type": "application/json"})
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(bad)
            self.assertEqual(cm.exception.code, 400)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
