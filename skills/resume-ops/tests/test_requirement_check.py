#!/usr/bin/env python3
"""requirement_check.py tests. The posting and the resume are invented."""
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import SCRIPTS, run  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import requirement_check as rc  # noqa: E402

POSTING = """Source: https://boards.greenhouse.io/lakeshoreclinics/jobs/42
Title: Clinic Operations Manager
Location: Madison, WI
Pay: $80,000 - $95,000

About the role
You will run day-to-day operations for 4 outpatient clinics.

What you bring:
- 5+ years in outpatient clinic operations, including 2+ years supervising front desk staff
- Bachelor's degree in health administration or equivalent experience
- Hands-on experience with Epic scheduling and patient intake workflows
- Budget ownership for a multi-site operation. Lean training strongly preferred.

Nice to have
- Spanish fluency
- Experience with Cerner revenue cycle reporting
"""

NO_PREFERRED = """Title: Line Cook

Requirements
- 2+ years on a hot line
- Food handler permit
"""

RESUME = {"blocks": [
    {"kind": "name", "text": "Jordan Okafor"},
    {"kind": "contact", "text": "Madison, WI | 608-555-0142 | jordan@example.com"},
    {"kind": "header", "text": "Summary"},
    {"kind": "para", "text": "Clinic operations manager with 9 years running outpatient sites. Speaks "
                             "Spanish with patients and families every day."},
    {"kind": "header", "text": "Experience"},
    {"kind": "role", "title": "Clinic Operations Manager", "company": "Lakeview Family Medicine",
     "city": "Madison", "state": "WI", "start": "Mar 2019", "end": "Aug 2025"},
    {"kind": "bullet", "text": "Ran daily operations for 3 outpatient clinics with 42 staff and a $6M budget."},
    {"kind": "bullet", "text": "Rebuilt Epic scheduling templates and patient intake workflows, cutting "
                               "check-in time from 11 minutes to 4."},
    {"kind": "bullet", "text": "Supervised 18 front desk staff across 3 sites."},
    {"kind": "role", "title": "Front Desk Supervisor", "company": "Northside Pediatrics",
     "city": "Madison", "state": "WI", "start": "Jan 2016", "end": "Feb 2019"},
    {"kind": "bullet", "text": "Supervised 6 front desk staff and hired 12 of them."},
    {"kind": "header", "text": "Education"},
    {"kind": "para", "text": "BS, Health Administration | Lakeshore State University | 2015"},
    {"kind": "header", "text": "Skills"},
    {"kind": "para", "text": "Epic, Lean, Spanish"},
]}

TODAY = datetime.date(2026, 9, 1)


class Extraction(unittest.TestCase):
    def test_items_come_out_verbatim_and_numbered(self):
        q = rc.qualifications(POSTING)
        self.assertEqual(q["required"], [
            "5+ years in outpatient clinic operations, including 2+ years supervising front desk staff",
            "Bachelor's degree in health administration or equivalent experience",
            "Hands-on experience with Epic scheduling and patient intake workflows",
            "Budget ownership for a multi-site operation.",
        ])
        self.assertEqual(q["preferred"], ["Spanish fluency", "Experience with Cerner revenue cycle reporting",
                                          "Lean training strongly preferred."])

    def test_file_header_lines_and_duties_are_not_qualifications(self):
        q = rc.qualifications(POSTING)
        joined = " ".join(q["required"] + q["preferred"])
        self.assertNotIn("Madison", joined)
        self.assertNotIn("day-to-day", joined)

    def test_no_preferred_section_is_said_plainly(self):
        out = rc.build(self.write(NO_PREFERRED), today=TODAY)
        self.assertIn("No preferred section in this posting.", out)
        self.assertIn("| R2 | Required | Food handler permit |", out)

    def test_other_headings_are_read_the_same_way(self):
        for head in ("Required Skills & Experience", "Basic Qualifications:", "## What We're Looking For"):
            posting = f"Title: Line Cook\n\n{head}\n- Food handler permit\n\nPluses\n- Pastry work\n"
            q = rc.qualifications(posting)
            self.assertEqual((q["required"], q["preferred"]), (["Food handler permit"], ["Pastry work"]), head)

    def write(self, text, name="posting.md"):
        d = Path(tempfile.mkdtemp())
        p = d / name
        p.write_text(text, encoding="utf-8")
        return p


class WithResume(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = Path(tempfile.mkdtemp())
        cls.posting = d / "posting.md"
        cls.posting.write_text(POSTING, encoding="utf-8")
        cls.resume = d / "resume.json"
        cls.resume.write_text(json.dumps(RESUME), encoding="utf-8")
        cls.lines, cls.roles = rc.resume_lines(cls.resume)

    def status(self, item):
        return rc.check(item, self.lines, self.roles, TODAY)

    def test_a_role_bullet_makes_it_likely(self):
        status, proof, _n = self.status("Hands-on experience with Epic scheduling and patient intake workflows")
        self.assertEqual(status, "LIKELY")
        self.assertIn("role: Clinic Operations Manager @ Lakeview Family Medicine", proof[0][1])

    def test_summary_or_skills_only_is_weak(self):
        status, proof, notes = self.status("Spanish fluency")
        self.assertEqual(status, "WEAK")
        self.assertTrue({w for _t, w in proof} <= {"summary", "skills"}, proof)
        self.assertIn("AI graders may not credit", " ".join(notes))

    def test_nothing_shared_is_none(self):
        self.assertEqual(self.status("Experience with Cerner revenue cycle reporting")[0], "NONE")

    def test_years_come_from_role_dates(self):
        status, _p, notes = self.status(
            "5+ years in outpatient clinic operations, including 2+ years supervising front desk staff")
        self.assertEqual(status, "LIKELY")
        self.assertIn("9.7 years across all roles", notes[0])
        self.assertIn("since Jan 2016", notes[0])

    def test_too_few_years_is_none(self):
        status, _p, notes = self.status("12+ years in clinic operations")
        self.assertEqual(status, "NONE")
        self.assertIn("Asks for 12+ years", notes[0])

    def test_degree_is_checked_in_education(self):
        status, proof, _n = self.status("Bachelor's degree in health administration or equivalent experience")
        self.assertEqual(status, "LIKELY")
        self.assertEqual(proof[0][1], "education")
        status, _p, notes = self.status("Master's degree in health administration")
        self.assertEqual(status, "WEAK")
        self.assertIn("below the level asked", notes[0])

    def test_checklist_output(self):
        out = rc.build(self.posting, self.resume, today=TODAY)
        self.assertIn("word-overlap guess, not a grade", out)
        self.assertIn("| # | Type | Qualification | Status | Proof line (section) | Action |", out)
        self.assertIn("write into <role>", out)
        self.assertIn("## Required (4)", out)
        self.assertIn("## Preferred (3)", out)
        self.assertNotIn(chr(0x2014), out)

    def test_cli_writes_the_file(self):
        out_path = self.posting.parent / "checklist.md"
        code, out = run("requirement_check.py", self.posting, self.resume, "--out", out_path)
        self.assertEqual(code, 0, out)
        self.assertIn("not a grade", out)
        self.assertIn("| R1 | Required |", out_path.read_text(encoding="utf-8"))

    def test_cli_without_a_resume(self):
        code, out = run("requirement_check.py", self.posting)
        self.assertEqual(code, 0, out)
        self.assertIn("| # | Type | Qualification | Proof line (section) | Action |", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
