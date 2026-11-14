import unittest

from ctsim import geo, model


class GeoTests(unittest.TestCase):
    def test_helsinki_centroid_roundtrip(self):
        lat, lon = geo.tm35fin_to_wgs84(390060, 6677093)   # Helsinki municipality centroid in EPSG:3067
        self.assertAlmostEqual(lat, 60.2, delta=0.2)
        self.assertAlmostEqual(lon, 24.95, delta=0.2)

    def test_central_meridian(self):
        lat, lon = geo.tm35fin_to_wgs84(500000, 7000000)   # on the 27E meridian
        self.assertAlmostEqual(lon, 27.0, places=6)


class ModelTests(unittest.TestCase):
    def test_central_case_reproduces_report(self):
        u = model.unit(model.central())
        self.assertAlmostEqual(u["scans"], 2868.75, places=1)
        self.assertAlmostEqual(u["cost_per_scan"], 372, delta=1)
        self.assertAlmostEqual(u["fixed"], 472_146, delta=5)

    def test_more_additionality_lowers_cost_per_additional_scan(self):
        rows = model.sweep(model.PARAMS, "additionality", [0.1, 0.35, 1.0])
        v = [r["cost_per_additional_scan"] for r in rows]
        self.assertTrue(v[0] > v[1] > v[2])

    def test_monte_carlo_is_seeded(self):
        a = model.monte_carlo(n=500, seed=3)
        b = model.monte_carlo(n=500, seed=3)
        self.assertEqual(a, b)

    def test_overrides(self):
        p = model.with_overrides({"eligible_share": 0.1, "additionality": [0.2, 0.3, 0.4]})
        self.assertEqual(p["eligible_share"][1], 0.1)
        self.assertEqual(p["additionality"][:3], (0.2, 0.3, 0.4))
        with self.assertRaises(KeyError):
            model.with_overrides({"nope": 1})


if __name__ == "__main__":
    unittest.main()
