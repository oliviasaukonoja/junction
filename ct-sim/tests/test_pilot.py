import unittest

from ctsim import pilot


class SampleSize(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(pilot.n_per_arm(0.40, 0.15), 173)           # 80% power, two-sided 5%
        self.assertEqual(pilot.n_per_arm(0.40, 0.10), 388)

    def test_monotone(self):
        self.assertGreater(pilot.n_per_arm(0.4, 0.05), pilot.n_per_arm(0.4, 0.10))
        self.assertGreater(pilot.n_per_arm(0.4, 0.15, power=0.9), pilot.n_per_arm(0.4, 0.15, power=0.8))

    def test_rejects_bad_input(self):
        for args in ((0.4, 0.0), (0.0, 0.1), (0.95, 0.10)):
            with self.assertRaises(ValueError):
                pilot.n_per_arm(*args)

    def test_additionality_arithmetic(self):
        a = pilot.additionality(0.40, 0.55)
        self.assertAlmostEqual(a["additional_per_100_invitees"], 15)
        self.assertAlmostEqual(a["would_have_happened_anyway_per_100"], 40)
        self.assertAlmostEqual(a["additionality_share"], 0.15 / 0.55)


class Simulation(unittest.TestCase):
    def test_deterministic_unbiased_and_powered(self):
        a = pilot.simulate(250, 0.40, 0.15, reps=600, seed=5)
        self.assertEqual(a, pilot.simulate(250, 0.40, 0.15, reps=600, seed=5))
        self.assertAlmostEqual(a["mean_rd"], 0.15, delta=0.02)        # unbiased
        self.assertGreater(a["power"], 0.85)
        self.assertGreater(a["ci_coverage"], 0.90)

    def test_leakage_attenuates_the_estimate(self):
        clean = pilot.simulate(250, 0.40, 0.15, reps=600, seed=5)
        leaky = pilot.simulate(250, 0.40, 0.15, reps=600, seed=5, contamination=0.3)
        self.assertLess(leaky["mean_rd"], clean["mean_rd"] - 0.03)
        self.assertLess(leaky["power"], clean["power"])
        self.assertAlmostEqual(leaky["true_itt_rd"], 0.15 * 0.7, places=6)

    def test_before_after_counts_the_campaign_as_additional(self):
        b = pilot.before_after_bias(0.40, 0.15, 0.30)
        self.assertAlmostEqual(b["randomised_additional_per_100"], 15)
        self.assertAlmostEqual(b["overstatement_per_100"], 12)         # 0.40 * 0.30 * 100
        self.assertAlmostEqual(b["naive_additional_per_100"], 27)

    def test_design_table_written(self):
        import tempfile
        from pathlib import Path
        p = pilot.write_design_table(Path(tempfile.mkdtemp()) / "t.csv")
        self.assertGreater(len(p.read_text().splitlines()), 20)


if __name__ == "__main__":
    unittest.main()
