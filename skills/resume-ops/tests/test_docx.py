#!/usr/bin/env python3
"""_docx.py: the shared reader, its header detection and its role reader."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import SCRIPTS, BLOCKS, write_docx  # noqa: E402
sys.path.insert(0, str(SCRIPTS))
import _docx  # noqa: E402

EN = "\u2013"


class Headers(unittest.TestCase):
    def test_header_detection_matches_known_and_title_case(self):
        self.assertEqual(_docx.header_kind("Summary"), "header")
        self.assertEqual(_docx.header_kind("Professional Experience"), "header")
        self.assertEqual(_docx.header_kind("EDUCATION"), "header")
        # Title-case non-standard headers passed silently when the only
        # detection was ALL CAPS.
        self.assertEqual(_docx.header_kind("Key Accomplishments"), "header")
        self.assertEqual(_docx.header_kind("Career Highlights"), "header")
        self.assertEqual(_docx.header_kind("Methodology"), "header")

    def test_job_titles_are_not_headers(self):
        for title in ("Maintenance Supervisor", "Charge Nurse",
                      "Senior Staff Accountant", "Licensed Practical Nurse"):
            self.assertIsNone(_docx.header_kind(title), title)

    def test_role_lines_are_never_headers(self):
        """v1.6 read an all-caps company line or a short all-caps title line
        with dates as a section header."""
        for line in ("Brightline Tool, Toledo, OH", "BRIGHTLINE TOOL, TOLEDO, OH",
                     f"Maintenance Supervisor | Mar 2018 {EN} Present",
                     f"CNA | Jun 2019 {EN} Present", "RN | 2019 - 2021"):
            self.assertIsNone(_docx.header_kind(line), line)

    def test_skills_section_aliases(self):
        for s in ("skills", "core competencies", "technical skills", "areas of expertise"):
            self.assertTrue(_docx.is_skills_section(s), s)
        self.assertFalse(_docx.is_skills_section("experience"))

    def test_blocks_kinds_are_unchanged(self):
        """Other scripts read these three kinds and nothing else."""
        path = write_docx(BLOCKS, Path(tempfile.mkdtemp()) / "r.docx")
        kinds = {k for k, _t in _docx.blocks(path)}
        self.assertEqual(kinds, {"header", "bullet", "para"})
        self.assertIn("Brightline Tool, Toledo, OH", _docx.lines(path))


class Roles(unittest.TestCase):
    def test_company_first_pair(self):
        path = write_docx(BLOCKS, Path(tempfile.mkdtemp()) / "r.docx")
        roles = _docx.roles(_docx.blocks(path))
        got = [(r["company"], r["city"], r["state"], r["title"], r["start"], r["end"])
               for r in roles]
        self.assertEqual(got, [
            ("Brightline Tool", "Toledo", "OH", "Maintenance Supervisor", "Mar 2018", "Present"),
            ("Keller Plastics", "Findlay", "OH", "Maintenance Technician", "Jun 2010", "Feb 2018"),
        ])
        self.assertEqual({r["layout"] for r in roles}, {"company-first"})

    def test_title_first_pair(self):
        blks = [("header", "Experience"), ("para", "Charge Nurse"),
                ("para", f"Mercy General, Leeds, UK | Mar 2019 {EN} Present"),
                ("bullet", "Ran a 32-bed unit.")]
        (r,) = _docx.roles(blks)
        self.assertEqual((r["title"], r["company"], r["city"], r["state"], r["layout"]),
                         ("Charge Nurse", "Mercy General", "Leeds", "UK", "title-first"))

    def test_one_line_forms(self):
        for line, want in (
            (f"Staff Accountant | Harbor & Lane | Portland, ME | Jan 2016 {EN} Dec 2019",
             ("Staff Accountant", "Harbor & Lane", "Portland", "ME")),
            (f"Staff Accountant | Harbor & Lane, Portland, ME | Jan 2016 {EN} Dec 2019",
             ("Staff Accountant", "Harbor & Lane", "Portland", "ME")),
            ("Teacher | Lincoln Middle School, Tulsa - 2012 - 2018",
             ("Teacher", "Lincoln Middle School", "Tulsa", "")),
            (f"### Logistics Manager \u2014 Northgate Supply \u00b7 Dayton, OH \u00b7 Apr 2019 {EN} Present",
             ("Logistics Manager", "Northgate Supply", "Dayton", "OH")),
        ):
            r = _docx.read_role_line(line)
            self.assertIsNotNone(r, line)
            self.assertEqual((r["title"], r["company"], r["city"], r["state"]), want, line)

    def test_dates_in_parentheses_and_open_ends(self):
        r = _docx.read_role_line("### Northgate Supply (Sep 2025 \u2013 )")
        self.assertEqual((r["segments"], r["start"], r["end"]),
                         (["Northgate Supply"], "Sep 2025", "Present"))
        r = _docx.read_role_line("## Northgate Supply (January \u2013 December 2018)")
        self.assertEqual((r["start"], r["end"]), ("January", "December 2018"))

    def test_sentences_are_not_roles(self):
        for line in ("Earlier career: Line Operator at Maumee Molding in Maumee, OH, 2004 to 2010.",
                     f"Grew route volume 40% from Jan 2019 {EN} Mar 2020 by rebuilding the plan",
                     "Opened the second paint line in September 2021."):
            self.assertIsNone(_docx.read_role_line(line), line)

    def test_dates_under_education_are_not_jobs(self):
        blks = [("header", "Experience"), ("para", "Brightline Tool, Toledo, OH"),
                ("para", f"Maintenance Supervisor | Mar 2018 {EN} Present"),
                ("header", "Education"),
                ("para", f"AAS, Industrial Maintenance | Owens Community College | Aug 2007 {EN} May 2009")]
        self.assertEqual([r["company"] for r in _docx.roles(blks)], ["Brightline Tool"])

    def test_split_place(self):
        self.assertEqual(_docx.split_place("Brightline Tool, Toledo, OH"),
                         ("Brightline Tool", "Toledo", "OH"))
        self.assertEqual(_docx.split_place("Denver, CO"), ("", "Denver", "CO"))
        self.assertEqual(_docx.split_place("Acme Health, Leeds"), ("Acme Health", "Leeds", ""))
        self.assertEqual(_docx.split_place("Brightline Tool"), ("Brightline Tool", "", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
