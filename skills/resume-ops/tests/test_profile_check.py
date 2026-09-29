#!/usr/bin/env python3
"""profile_check.py: the resume's jobs against the candidate's LinkedIn jobs file.
Every name and employer here is invented."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import BLOCKS, SCRIPTS, run  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import profile_check as pc  # noqa: E402

HEADER = "Company Name,Title,Description,Location,Started On,Finished On"


class ProfileCheck(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.src = self.dir / "resume.json"
        self.src.write_text(json.dumps({"name": "Dana Reyes", "blocks": copy.deepcopy(BLOCKS)}),
                            encoding="utf-8")

    def profile(self, *rows, preamble=""):
        p = self.dir / "Positions.csv"
        p.write_text("﻿" + preamble + HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
        return p

    def check(self, *rows, **kw):
        roles, earlier = pc.read_resume(self.src)
        return pc.compare(roles, pc.read_profile(self.profile(*rows, **kw)), earlier)

    def test_an_exact_match_is_clean(self):
        out, summary = self.check(
            'Brightline Tool Inc.,Maintenance Supervisor,,"Toledo, Ohio",Mar 2018,',
            "Keller Plastics,Maintenance Technician,,Findlay,Jun 2010,Feb 2018")
        self.assertEqual(out, [])
        self.assertIn("2 of 2 resume jobs match LinkedIn exactly; 0 date conflict(s)", summary)

    def test_a_reorder_and_an_added_word_are_reviews(self):
        out, _ = self.check("Brightline Tool,\"Supervisor, Maintenance\",,,Mar 2018,",
                            "Keller Plastics,Technician,,,Jun 2010,Feb 2018")
        notes = [n for lv, _w, n in out if lv == "REVIEW"]
        self.assertTrue(any("same words, different order" in n for n in notes), notes)
        self.assertTrue(any("the resume adds: maintenance" in n for n in notes), notes)
        self.assertFalse([o for o in out if o[0] == "FAIL"])

    def test_a_date_conflict_fails(self):
        out, summary = self.check("Brightline Tool,Maintenance Supervisor,,,Apr 2018,",
                                  "Keller Plastics,Maintenance Technician,,,Jun 2010,Feb 2018")
        self.assertIn(("FAIL", "Maintenance Supervisor @ Brightline Tool",
                       "start date: resume Mar 2018, LinkedIn Apr 2018"), out)
        self.assertIn("1 date conflict(s)", summary)

    def test_a_year_only_date_is_not_a_conflict(self):
        out, _ = self.check("Brightline Tool,Maintenance Supervisor,,,2018,",
                            "Keller Plastics,Maintenance Technician,,,2010,2018")
        self.assertFalse([o for o in out if o[0] == "FAIL"], out)

    def test_jobs_in_one_place_only(self):
        out, _ = self.check("Brightline Tool,Maintenance Supervisor,,,Mar 2018,",
                            "Keller Plastics,Maintenance Technician,,,Jun 2010,Feb 2018",
                            "Maumee Molding,Line Operator,,,Jan 2004,Mar 2010",
                            "Acme Foods,Intern,,,Jun 2003,Aug 2003")
        wheres = [w for _lv, w, _n in out]
        self.assertIn("Intern @ Acme Foods", wheres)
        self.assertNotIn("Line Operator @ Maumee Molding", wheres)    # the earlier line, same years
        out, _ = self.check("Brightline Tool,Maintenance Supervisor,,,Mar 2018,")
        self.assertIn(("REVIEW", "Maintenance Technician @ Keller Plastics", "not on the LinkedIn profile"), out)

    def test_the_earlier_career_line_is_checked_not_skipped(self):
        """Review finding: v2.1 drafts skipped any leftover job whose company
        appeared in the earlier line, whatever its years, and matched a city."""
        out, _ = self.check("Brightline Tool,Maintenance Supervisor,,,Mar 2018,",
                            "Keller Plastics,Maintenance Technician,,,Jun 2010,Feb 2018",
                            "Maumee Molding,Line Operator,,,Jan 1998,Dec 2001",
                            "Maumee,Consultant,,,Jan 2024,")
        self.assertIn(("FAIL", "Line Operator @ Maumee Molding", "years: the earlier-career line has "
                       "2004 to 2010, LinkedIn has Jan 1998 to Dec 2001"), out)
        self.assertIn(("REVIEW", "Consultant @ Maumee", "on LinkedIn, not on the resume"), out)

    def test_a_promotion_missing_from_linkedin_does_not_steal_a_match(self):
        bl = copy.deepcopy(BLOCKS)
        i = next(n for n, b in enumerate(bl) if b.get("company") == "Brightline Tool")
        bl[i]["start"] = "Mar 2021"
        lead = dict(bl[i], title="Maintenance Lead", start="Mar 2018", end="Feb 2021")
        bl[i + 3:i + 3] = [lead, {"kind": "bullet", "text": "Led 4 technicians on two shifts."}]
        self.src.write_text(json.dumps({"name": "Dana Reyes", "blocks": bl}), encoding="utf-8")
        out, _ = self.check("Brightline Tool,Maintenance Lead,,,Mar 2018,",
                            "Keller Plastics,Maintenance Technician,,,Jun 2010,Feb 2018")
        self.assertIn(("REVIEW", "Maintenance Supervisor @ Brightline Tool", "not on the LinkedIn profile"), out)
        self.assertIn(("FAIL", "Maintenance Lead @ Brightline Tool", "end date: resume Feb 2021, LinkedIn Present"), out)
        self.assertFalse([o for o in out if "start date" in o[2]], out)

    def test_unreadable_jobs_are_an_error_not_a_pass(self):
        from fixtures import write_docx
        docx = self.dir / "one-line.docx"
        write_docx([b for b in copy.deepcopy(BLOCKS) if b["kind"] != "role"] +
                   [{"kind": "para", "text": "Maintenance Supervisor at Brightline Tool, since 2018"}], docx)
        good = self.profile("Brightline Tool,Maintenance Supervisor,,,Mar 2018,")
        code, out = run("profile_check.py", docx, good)
        self.assertEqual(code, 2, out)
        self.assertIn("Could not read the jobs", out)

    def test_a_csv_saved_from_excel_reads(self):
        p = self.dir / "excel.csv"
        p.write_bytes((HEADER + "\nSoci\xe9t\xe9 G\xe9n\xe9rale,Analyst,,,Jan 2008,Dec 2009\n"
                       "Brightline Tool,Maintenance Supervisor,,,Mar 2018,\n").encode("cp1252"))
        rows = pc.read_profile(p)
        self.assertEqual(rows[0]["company"], "Soci\xe9t\xe9 G\xe9n\xe9rale")

    def test_rows_above_the_header_are_skipped(self):
        out, _ = self.check("Brightline Tool,Maintenance Supervisor,,,Mar 2018,",
                            "Keller Plastics,Maintenance Technician,,,Jun 2010,Feb 2018",
                            preamble="Notes:\nExported from LinkedIn\n\n")
        self.assertEqual(out, [])

    def test_dates_in_other_forms(self):
        self.assertEqual(pc.month_year("March 2021"), (2021, 3))
        self.assertEqual(pc.month_year("2021-03"), (2021, 3))
        self.assertEqual(pc.month_year("03/2021"), (2021, 3))
        self.assertEqual(pc.month_year("Present"), None)
        self.assertEqual(pc.month_year("soon"), "?")

    def test_cli_exit_codes(self):
        good = self.profile("Brightline Tool,Maintenance Supervisor,,,Mar 2018,",
                            "Keller Plastics,Maintenance Technician,,,Jun 2010,Feb 2018")
        code, out = run("profile_check.py", self.src, good)
        self.assertEqual(code, 0, out)
        self.assertIn("exactly as held", out)
        bad = self.profile("Brightline Tool,Maintenance Supervisor,,,Mar 2017,")
        code, out = run("profile_check.py", self.src, bad)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL", out)


if __name__ == "__main__":
    unittest.main()
