import csv
import tempfile
import unittest
from pathlib import Path

from ctsim import ctsites, scenario

HEAD = "county,facility,municipality,facility_type,ct_status,n_scanners,evidence,source_url,source_date,notes\n"


class CtSitesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "raw_group1.csv").write_text(HEAD +
            "Pirkanmaa,Tays,Tampere,university,confirmed,6,has CT,http://x,2025,\n"
            "Pirkanmaa,Tays duplicate,Tampere,university,confirmed,,dup facility name differs,http://x,2025,\n"
            "Pirkanmaa,Tays,TAMPERE,university,confirmed,,same facility different case,http://x,2025,\n"
            "Lappi,Rovaniemi hospital,Rovaniemi,central,likely,,size,http://y,2024,inferred\n"
            "Lappi,Fake,Nowhereville,regional,confirmed,,x,http://z,2024,\n"
            "Pohjois-Pohjanmaa,Heart truck,Oulu,mobile,confirmed,1,travels,http://m,2024,\n"
            "Kainuu,Bad row,Kajaani,hospital?,confirmed,,x,http://k,2024,\n", encoding="utf-8")

    def test_compile_dedupes_validates_and_flags(self):
        r = ctsites.compile(self.tmp, self.tmp)
        self.assertEqual(r["unmatched"], 1)                              # Nowhereville
        self.assertTrue(any("bad type/status" in p for p in r["problems"]))
        rows = list(csv.DictReader(open(self.tmp / "ct_sites.csv", encoding="utf-8")))
        self.assertEqual(sorted({x["municipality"] for x in rows}), ["Oulu", "Rovaniemi", "Tampere"])
        self.assertEqual(len([x for x in rows if x["facility"] == "Tays"]), 1)

    def test_names_modes_and_mobile_exclusion(self):
        ctsites.compile(self.tmp, self.tmp)
        p = self.tmp / "ct_sites.csv"
        self.assertEqual(ctsites.names("confirmed", p), ["Tampere"])                 # mobile Oulu excluded, likely Rovaniemi excluded
        self.assertEqual(ctsites.names("confirmed+likely", p), ["Rovaniemi", "Tampere"])
        with self.assertRaises(ValueError):
            ctsites.names("everything", p)

    def test_overrides_and_private_exclusion(self):
        (self.tmp / "overrides.csv").write_text("facility,field,value,reason\nRovaniemi hospital,ct_status,confirmed,test\nNo such facility,ct_status,likely,x\n", encoding="utf-8")
        r = ctsites.compile(self.tmp, self.tmp)
        self.assertTrue(any("override matched nothing" in p for p in r["problems"]))
        self.assertEqual(ctsites.names("confirmed", self.tmp / "ct_sites.csv"), ["Rovaniemi", "Tampere"])    # override upgraded Rovaniemi
        rows = {x["facility"]: x for x in csv.DictReader(open(self.tmp / "ct_sites.csv", encoding="utf-8"))}
        self.assertEqual(rows["Heart truck"]["counts_for_routing"], "no")

    def test_scenario_rejects_bad_mode_and_explicit_list_wins(self):
        with self.assertRaises(ValueError):
            scenario.fixed_names({"ct_sites": "nope"})
        self.assertEqual(scenario.fixed_names({"fixed_sites": ["Oulu"], "ct_sites": "confirmed"}), ["Oulu"])
        self.assertIn("Helsinki", scenario.fixed_names({}))                         # placeholder default


if __name__ == "__main__":
    unittest.main()
