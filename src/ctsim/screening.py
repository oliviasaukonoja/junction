"""Cancer Registry screening statistics: download the three annual-statistics pages and extract every HTML table to CSV.

Source pages: https://stats.cancerregistry.fi/joukkistilastot/{breast,cervix,colorectal}.html (each ~8-10 MB).
Each table is written as <programme>_NN.csv plus <programme>_INDEX.tsv mapping file -> section > year.
Row 2 of each CSV is the N/% unit row. Known quirk: cervical county tables appear twice per year, unlabelled.
"""
from __future__ import annotations

import csv
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from . import paths

PROGRAMMES = ("breast", "cervix", "colorectal")
URL = "https://stats.cancerregistry.fi/joukkistilastot/{}.html"


class _P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heads: dict[int, str] = {}
        self.in_head = None
        self.tables: list[tuple[str, list[list[str]]]] = []
        self.stack: list[dict] = []
        self.cell = None
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if re.fullmatch(r"h[1-4]", tag):
            self.in_head = (int(tag[1]), "")
        if tag == "table":
            ctx = " > ".join(self.heads[k] for k in sorted(self.heads) if self.heads[k])
            self.stack.append({"ctx": ctx, "rows": [], "row": None})
        elif self.stack:
            t = self.stack[-1]
            if tag == "tr":
                t["row"] = []
            elif tag in ("td", "th"):
                self.cell = ""

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        if re.fullmatch(r"h[1-4]", tag) and self.in_head:
            lvl, txt = self.in_head
            self.heads[lvl] = re.sub(r"\s+", " ", txt).strip()
            for k in list(self.heads):
                if k > lvl:
                    del self.heads[k]
            self.in_head = None
        if self.stack:
            t = self.stack[-1]
            if tag in ("td", "th") and self.cell is not None:
                t["row"].append(re.sub(r"\s+", " ", self.cell).strip())
                self.cell = None
            elif tag == "tr" and t["row"] is not None:
                if t["row"]:
                    t["rows"].append(t["row"])
                t["row"] = None
            elif tag == "table":
                done = self.stack.pop()
                if done["rows"]:
                    self.tables.append((done["ctx"], done["rows"]))

    def handle_data(self, data):
        if self.skip:
            return
        if self.in_head:
            self.in_head = (self.in_head[0], self.in_head[1] + data)
        if self.cell is not None:
            self.cell += data


def extract(html: str, out_dir: Path, prefix: str) -> int:
    p = _P()
    p.feed(html)
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for i, (ctx, rows) in enumerate(p.tables, 1):
        name = f"{prefix}_{i:02d}.csv"
        with open(out_dir / name, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        index.append((name, ctx, len(rows), len(rows[0])))
    with open(out_dir / f"{prefix}_INDEX.tsv", "w", encoding="utf-8") as f:
        for r in index:
            f.write("\t".join(map(str, r)) + "\n")
    return len(index)


def fetch_all(out_dir: Path | None = None, programmes=PROGRAMMES) -> dict[str, int]:
    out_dir = Path(out_dir or paths.SCREENING)
    counts = {}
    for prog in programmes:
        req = urllib.request.Request(URL.format(prog), headers={"User-Agent": "ctsim-research/0.1 (public aggregate data refresh)"})
        html = urllib.request.urlopen(req, timeout=180).read().decode("utf-8", errors="ignore")
        counts[prog] = extract(html, out_dir, prog)
    return counts


def _find(index_file: Path, section: str, year: str) -> list[str]:
    hits = []
    for line in index_file.read_text(encoding="utf-8").splitlines():
        name, ctx, *_ = line.split("\t")
        if ctx.endswith(f"{section} > {year}"):
            hits.append(name)
    return hits


def county_table(year: str = "2024", out_csv: Path | None = None) -> list[list]:
    """Merge breast / cervical / colorectal participation by wellbeing services county for one year.

    Cervical county tables come as two unlabelled sub-tables; their invited and attended counts are summed
    (the combined national total matches the native-language table, 73.8%).
    """
    sec = "Wellbeing services counties > Screening process"
    d = paths.SCREENING

    def load(fn):
        return {r[0]: r for r in list(csv.reader(open(d / fn, encoding="utf-8")))[2:]}

    breast = load(_find(d / "breast_INDEX.tsv", sec, year)[0])
    crc = load(_find(d / "colorectal_INDEX.tsv", sec, year)[0])
    cx = [load(fn) for fn in _find(d / "cervix_INDEX.tsv", sec, year)]
    rows = []
    for k in breast:
        if k == "Total":
            continue
        ce = ""
        if cx and all(k in t for t in cx):
            inv = sum(int(t[k][1]) for t in cx)
            att = sum(int(t[k][2]) for t in cx)
            ce = round(100 * att / inv, 1) if inv else ""
        rows.append([k, breast[k][3], ce, crc[k][3] if k in crc else ""])
    for t in cx:   # counties only in the cervical table (Aland)
        for k in t:
            if k not in breast and k != "Total" and all(k in u for u in cx):
                inv = sum(int(u[k][1]) for u in cx)
                att = sum(int(u[k][2]) for u in cx)
                rows.append([k, "", round(100 * att / inv, 1), ""])
        break
    out_csv = Path(out_csv or paths.SCREENING / f"counties_participation_{year}.csv")
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["county", "breast_participation_pct", "cervical_participation_pct_combined_subtables", "colorectal_participation_pct"])
        w.writerows(rows)
    return rows
