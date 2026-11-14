import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ctsim import area, routing as R, scenario


def world(**routing):
    scn = {"name": "t", "ct_sites": "confirmed+likely", "routing": routing}
    prm, _, cen = scenario.setup(scn)
    return R.World(R.load(), prm, scenario.fixed_names(scn), area=scenario.area_hook(scn, prm)), prm


class AreaData(unittest.TestCase):
    def test_verified_inputs_loaded(self):
        A = area.load()
        self.assertEqual(len(A.counties), 23)
        deaths = sum(c["deaths"] for c in A.counties.values())
        self.assertTrue(2200 < deaths < 2500, deaths)                      # about 2,340 lung deaths a year (C32-C34)
        rank = sorted(A.counties.values(), key=lambda c: -c["rate50"])
        self.assertEqual(rank[0]["name"], "Lapland")                       # highest per 100k aged 50-74 in the extracted data
        self.assertEqual(rank[-1]["name"], "Vantaa and Kerava")
        self.assertEqual(len(A.county_of), 308)

    def test_eligible_estimate_is_plausible_and_varies(self):
        w, _ = world()
        total = sum(c["eligible"] for c in w.area_info.values())
        self.assertTrue(0.05 < total / 1_695_391 < 0.09, total)
        shares = [c["eligible"] / c["pop50"] for c in w.area_info.values()]
        self.assertGreater(max(shares) / min(shares), 1.5)                  # smoking differs by county, so eligibility does too

    def test_mortality_weights_priorities(self):
        w, _ = world()
        lap = next(r for r in w.rows if r["name"] == "Rovaniemi")
        van = next(r for r in w.rows if r["name"] == "Vantaa")
        self.assertGreater(lap["mort_index"], 1.2)
        self.assertLess(van["mort_index"], 0.9)
        w0 = R.World(R.load(), w.prm, scenario.fixed_names({"ct_sites": "confirmed+likely"}))
        self.assertGreater(lap["w"] / next(r for r in w0.rows if r["name"] == "Rovaniemi")["w"], 1.2)


class CampaignAndCapacity(unittest.TestCase):
    def reach(self, **routing):
        r = scenario.run({"name": "t", "region": {"base": "Tampere", "radius_km": 60}, "ct_sites": "confirmed+likely", "routing": routing})
        return r

    def test_priority_booking_protects_eligible_coverage(self):
        calm = self.reach(campaign_intensity=0.0)["reach"]["coverage_fixed_only"]
        prio = self.reach(campaign_intensity=3.0, triage=0.0, priority_eligible=True)["reach"]["coverage_fixed_only"]
        share = self.reach(campaign_intensity=3.0, triage=0.0, priority_eligible=False)["reach"]["coverage_fixed_only"]
        self.assertGreaterEqual(prio, calm * 0.99)                           # eligible people are booked first, so not crowded out
        self.assertLess(share, calm * 0.6)                                   # without priority the campaign crowds them out

    def test_triage_shrinks_ineligible_demand_and_waits(self):
        a = self.reach(campaign_intensity=2.0, triage=0.0)["campaign"]
        b = self.reach(campaign_intensity=2.0, triage=0.8)["campaign"]
        self.assertLess(b["demand_ineligible"], a["demand_ineligible"] * 0.3)
        self.assertLessEqual(b["longest_extra_wait"]["weeks"], a["longest_extra_wait"]["weeks"])

    def test_truck_never_reduces_coverage_and_outputs_are_complete(self):
        r = self.reach()
        self.assertGreaterEqual(r["reach"]["coverage_with_truck"], r["reach"]["coverage_fixed_only"])
        self.assertTrue(r["counties"] and r["risk_group"]["pack_years_min"] == 20)
        self.assertTrue(all("extra_wait_weeks" in c and "baseline_wait_is_data" in c for c in r["counties"]))
        self.assertTrue(all(c["baseline_wait_is_data"] is False for c in r["counties"]))   # no observed waits shipped

    def test_legacy_model_has_no_area_outputs(self):
        r = scenario.run({"name": "t", "region": {"base": "Tampere", "radius_km": 60}, "risk_model": "uniform"})
        self.assertIsNone(r["counties"])
        self.assertIsNone(r["reach"])

    def test_observed_waits_override_the_assumption(self):
        tmp = Path(tempfile.mkdtemp())
        for f in ("county_map.csv", "county_indicators.csv"):
            shutil.copy(area.AREA / f, tmp / f)
        with open(tmp / "ct_waits.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["hva_code", "county", "ct_wait_weeks", "source", "date"])
            w.writerow(["HVA21", "Lapland", "11", "test", "2026-11-01"])
        old = area.AREA
        area.AREA = tmp
        try:
            A = area.AreaData()
        finally:
            area.AREA = old
        self.assertEqual(A.waits, {"HVA21": 11.0})


class DataStatus(unittest.TestCase):
    def test_every_item_is_labelled_and_actionable(self):
        d = json.load(open(area.paths.DATA / "gap" / "indicators.json", encoding="utf-8"))
        kinds = {"verified", "proxy", "assumed", "gap"}
        self.assertGreaterEqual(len(d["data_status"]), 10)
        for it in d["data_status"]:
            self.assertIn(it["status"], kinds, it["item"])
            self.assertTrue(it["how"] and it["action"], it["item"])
        self.assertTrue(any(it["status"] == "gap" and "waiting" in it["item"].lower() for it in d["data_status"]))
        self.assertTrue(any(it["status"] == "gap" and "pack-year" in it["item"].lower() for it in d["data_status"]))


if __name__ == "__main__":
    unittest.main()
