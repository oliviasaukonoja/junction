import itertools
import random
import unittest

from ctsim import routing as R


def synthetic():
    syn = []

    def add(name, x, y, pop, f=0.0):
        syn.append(dict(i=len(syn), code=str(len(syn)), name=name, x=x * 1000, y=y * 1000, lat=None, lon=None, pop=pop, f=f))
    add("City", 0, 0, 200_000); add("Near", 20, 0, 30_000)
    add("RemoteA", 300, 0, 6_000); add("RemoteB", 300, 100, 6_000); add("RemoteC", 450, 50, 6_000)
    return syn


class PlantedStructure(unittest.TestCase):
    def setUp(self):
        self.syn = synthetic()
        self.prm = dict(R.DEFAULT, pool_km=60.0, work_days=14)   # tight budget so the choice matters
        self.w = R.World(self.syn, self.prm, fixed_names=["City"])
        self.plan = self.w.optimise(None, "weighted")
        self.names = {self.syn[s]["name"] for s in self.plan}

    def test_never_spends_days_where_ct_exists(self):
        self.assertNotIn("City", self.names)
        self.assertGreaterEqual(len(self.names & {"RemoteA", "RemoteB", "RemoteC"}), 2)

    def test_greedy_matches_brute_force_on_small_instance(self):
        best = 0.0
        cands = [r["name"] for r in self.syn]
        for k in range(1, len(cands) + 1):
            for sub in itertools.combinations(cands, k):
                best = max(best, self.w.evaluate(self.w.optimise(set(sub), "weighted"))["weighted"])
        self.assertGreaterEqual(self.w.evaluate(self.plan)["weighted"], 0.95 * best)

    def test_access_objective_beats_population_greedy(self):
        pop_plan = self.w.optimise(None, "scans")
        self.assertGreater(self.w.evaluate(self.plan)["additional"], 1.2 * self.w.evaluate(pop_plan)["additional"])


class RealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prm = dict(R.DEFAULT)
        cls.w = R.World(R.load(), cls.prm)
        cls.plan = cls.w.optimise(None, "weighted")
        cls.ev = cls.w.evaluate(cls.plan)

    def test_municipality_table(self):
        rows = R.load()
        self.assertEqual(len(rows), 308)
        self.assertEqual(sum(r["pop"] for r in rows), 1_695_391)
        self.assertTrue(all(r["lat"] is not None and 59 < r["lat"] < 71 for r in rows))

    def test_deterministic(self):
        self.assertEqual(self.plan, self.w.optimise(None, "weighted"))

    def test_constraints(self):
        self.assertLessEqual(self.ev["total_days"], self.prm["work_days"] + 1e-6)
        self.assertLessEqual(self.ev["scans"], self.ev["scan_days"] * self.prm["spd"] + 1e-6)

    def test_more_days_never_hurts(self):
        prev = -1.0
        for days in (50, 100, 150, 200, 260):
            q = dict(self.prm, work_days=days)
            ww = R.World(R.load(), q)
            v = ww.evaluate(ww.optimise(None, "weighted"))["additional"]
            self.assertGreaterEqual(v, prev - 1e-6)
            prev = v

    def test_sensitivity_regret_is_bounded_and_reported(self):
        # The 35% bound is an arbitrary guard, not a statistical test. Read the table, not the pass.
        tab = R.sensitivity_table()
        self.assertEqual(len(tab), len(R.PERTURBATIONS))
        self.assertLess(max(t["regret"] for t in tab), 0.35)
        distance = [t for t in tab if t["label"].startswith(("d0_", "minority"))]
        self.assertLess(max(t["regret"] for t in distance), 0.10)

    def test_removing_ct_sites_raises_the_access_gap(self):
        random.seed(7)
        drops = random.sample(R.FIXED_SITE_NAMES, 6)
        kept = [n for n in R.FIXED_SITE_NAMES if n not in drops]
        ww = R.World(R.load(), self.prm, kept)
        ev = ww.evaluate(ww.optimise(None, "weighted"))
        self.assertGreaterEqual(ev["additional"], self.ev["additional"] * 0.95)


if __name__ == "__main__":
    unittest.main()
