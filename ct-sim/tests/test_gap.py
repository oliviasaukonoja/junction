import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from ctsim import gap
from ctsim.server import Handler


class GapData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = gap.build(Path(tempfile.mkdtemp()) / "g.json")

    def test_numbers_match_registry_tables(self):                  # figures quoted in the report
        L = self.d["groups"]["language"]
        self.assertEqual((L["breast"]["Domestic"], L["breast"]["Other/missing"]), (83.2, 60.8))
        self.assertEqual((L["colorectal"]["Domestic"], L["colorectal"]["Other/missing"]), (74.5, 53.4))
        self.assertEqual((L["cervical"]["Domestic"], L["cervical"]["Other/missing"]), (76.2, 56.3))
        E = self.d["groups"]["education"]
        self.assertEqual((E["breast"]["Primary education/unknown"], E["breast"]["Tertiary/higher education"]), (63.5, 85.9))
        self.assertEqual(self.d["national"], {"breast": 81.6, "colorectal": 73.5})

    def test_counties_and_tags(self):
        self.assertEqual(len(self.d["counties"]), 23)
        helsinki = next(c for c in self.d["counties"] if c["county"] == "City of Helsinki")
        self.assertEqual((helsinki["breast"], helsinki["colorectal"]), (74.3, 69.6))
        for r in self.d["recommendations"]:
            self.assertIn(r["tag"], ("S", "N", "A"))
            self.assertTrue(r["owner"] and r["evidence"] and r["kpi"], r["id"])
        for st in self.d["pathway"]:
            for it in st["items"]:
                self.assertIn(it["tag"], ("S", "N", "A"))

    def test_pages_served(self):
        gap.build()                                                   # writes data/gap/gapdata.json
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            self.assertIn("Cancer care gap finder", urllib.request.urlopen(base + "/gap").read().decode())
            self.assertEqual(json.load(urllib.request.urlopen(base + "/gapdata"))["year"], 2024)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
