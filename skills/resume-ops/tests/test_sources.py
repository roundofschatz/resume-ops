#!/usr/bin/env python3
"""references/sources.md: every cited source has a row, every row is cited, and
each row says truthfully where it is used."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import ROOT  # noqa: E402

SOURCES = ROOT / "references" / "sources.md"
CITE = re.compile(r"\[((?:[SL]\d{2,3})(?:,\s*[SL]\d{2,3})*)\]")
ROW = re.compile(r"^\| ([SL]\d{2,3}) \|")


def cited_files():
    files = [ROOT / "SKILL.md", ROOT / "README.md"]
    files += sorted(p for p in (ROOT / "references").glob("*.md") if p.name != "sources.md")
    files += sorted((ROOT / "templates").glob("*.md"))
    files += sorted((ROOT / "scripts").glob("*.py"))
    return files


def citations():
    """{id: {file name, ...}} for every [S01]-style citation in the skill."""
    used = {}
    for f in cited_files():
        for m in CITE.finditer(f.read_text(encoding="utf-8")):
            for rid in re.split(r",\s*", m.group(1)):
                used.setdefault(rid, set()).add(f.name)
    return used


def rows():
    """{id: [cells]} from the tables in sources.md."""
    out = {}
    for line in SOURCES.read_text(encoding="utf-8").splitlines():
        if ROW.match(line):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
            out[cells[0]] = cells
    return out


class Sources(unittest.TestCase):
    def test_every_cited_id_has_a_row(self):
        missing = sorted(set(citations()) - set(rows()))
        self.assertFalse(missing, f"cited but not in sources.md: {missing}")

    def test_every_row_is_cited(self):
        unused = sorted(set(rows()) - set(citations()))
        self.assertFalse(unused, f"in sources.md but cited nowhere: {unused}")

    def test_used_in_matches_the_citations(self):
        used = citations()
        for rid, cells in rows().items():
            listed = {x.strip() for x in cells[-1].split(",") if x.strip()}
            self.assertEqual(listed, used.get(rid, set()), rid)

    def test_every_outside_source_is_complete(self):
        for rid, cells in rows().items():
            if rid.startswith("L"):
                self.assertEqual(len(cells), 7, rid)
                self.assertTrue(all(cells[:6]), rid)
                continue
            _id, source, date, grade, supports, quote, url, _used = cells
            self.assertTrue(source and date and grade and supports and quote, rid)
            self.assertTrue(url.startswith("https://"), rid)

    def test_ids_are_unique(self):
        seen = [ROW.match(l).group(1) for l in SOURCES.read_text(encoding="utf-8").splitlines()
                if ROW.match(l)]
        self.assertEqual(len(seen), len(set(seen)))


if __name__ == "__main__":
    unittest.main()
