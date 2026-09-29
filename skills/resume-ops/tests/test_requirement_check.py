#!/usr/bin/env python3
"""requirement_check.py tests. The posting and the resume are invented."""
import datetime
import json
import re
import shutil
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


# Career notes, not a resume: evidence goes in, the resume comes out (2.2.0).
EVIDENCE = """# Career notes: Jordan Okafor

## Roles
Clinic Operations Manager, Lakeview Family Medicine, Madison, WI, Mar 2019 to Aug 2025
Front Desk Supervisor, Northside Pediatrics, Madison, WI, Jan 2016 to Feb 2019

## Lakeview Family Medicine

### Epic rebuild, 2021
We had long waits at every front desk.
Rebuilt the Epic scheduling templates and the patient intake workflow for all three clinics. Check-in time fell from 11 minutes to 4.

### Money
Owned the $6M operating budget for the three outpatient clinics, a multi-site operation.

### Front desk
- Supervised 18 front desk staff across 3 sites.
- Ran the weekly huddle.

## Northside Pediatrics
Supervised 6 front desk staff and hired 12 of them.

## Education
BS, Health Administration, Lakeshore State University, 2015

## Languages
Speaks Spanish with patients and families every day.
"""


def tiny_pdf(lines):
    """A one-page PDF with one text line per entry, written by hand."""
    ops = "BT /F1 11 Tf 72 720 Td 14 TL " + " ".join(
        "(" + ln.replace("(", "[").replace(")", "]") + ") Tj T*" for ln in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(ops)} >>\nstream\n{ops}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = "%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


def line_of(text, needle):
    for n, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return n
    raise AssertionError(needle)


class Evidence(unittest.TestCase):
    """requirement_check.py reads evidence as well as a resume: it splits each
    file on its headings and returns, for each qualification, the best passages
    with the file, the heading and the line, so the builder opens only those."""

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp())
        cls.posting = cls.dir / "posting.md"
        cls.posting.write_text(POSTING, encoding="utf-8")
        cls.notes = cls.dir / "notes.md"
        cls.notes.write_text(EVIDENCE, encoding="utf-8")
        q = rc.qualifications(POSTING)
        cls.items = q["required"] + q["preferred"]
        cls.hits = rc.search_evidence(cls.items, [cls.notes])

    def hit(self, item):
        return self.hits[self.items.index(item)]

    def test_every_required_qualification_gets_file_heading_and_line(self):
        for item in rc.qualifications(POSTING)["required"]:
            found = self.hit(item)
            self.assertTrue(found, item)
            for h in found:
                self.assertEqual(h["file"], "notes.md")
                self.assertTrue(h["heading"], h)
                line = EVIDENCE.splitlines()[h["line"] - 1]
                self.assertIn(h["text"].split(".")[0][:30].lstrip("- "), line, (item, h))

    def test_the_passage_is_the_one_that_proves_it(self):
        epic = self.hit("Hands-on experience with Epic scheduling and patient intake workflows")[0]
        self.assertEqual(epic["line"], line_of(EVIDENCE, "Rebuilt the Epic scheduling"))
        self.assertIn("Epic rebuild, 2021", epic["heading"])
        self.assertIn("Lakeview Family Medicine", epic["heading"])
        budget = self.hit("Budget ownership for a multi-site operation.")[0]
        self.assertEqual(budget["line"], line_of(EVIDENCE, "Owned the $6M"))
        self.assertIn("Money", budget["heading"])
        degree = self.hit("Bachelor's degree in health administration or equivalent experience")[0]
        self.assertEqual(degree["line"], line_of(EVIDENCE, "BS, Health Administration"))

    def test_a_qualification_with_no_proof_has_no_passage_and_stays_listed(self):
        self.assertEqual(self.hit("Experience with Cerner revenue cycle reporting"), [])
        out = rc.build(self.posting, evidence=[self.notes], today=TODAY)
        self.assertIn("| P2 | Preferred | Experience with Cerner revenue cycle reporting |", out)
        self.assertIn("none found", out)

    def test_cli_with_evidence_and_no_resume(self):
        code, out = run("requirement_check.py", self.posting, "--evidence", self.notes)
        self.assertEqual(code, 0, out)
        self.assertIn("## Required (4)", out)
        for n in range(1, 5):
            self.assertIn(f"| R{n} | Required |", out)
        self.assertIn(f"notes.md, line {line_of(EVIDENCE, 'Rebuilt the Epic scheduling')}", out)
        self.assertIn("Epic rebuild, 2021", out)
        self.assertIn("## Evidence map", out)
        self.assertIn("read it all", out)

    def test_large_evidence_is_searched_and_nothing_is_dropped(self):
        big = self.dir / "record.md"
        filler = "\n".join(f"## Project {i}\nNotes on project {i}: site visits and a report.\n"
                           for i in range(900))
        big.write_text(filler + "\n" + EVIDENCE, encoding="utf-8")
        self.assertGreater(len(big.read_text(encoding="utf-8").splitlines()), rc.READ_WHOLE_LINES)
        out = rc.build(self.posting, evidence=[big], today=TODAY)
        self.assertIn("search it", out)
        self.assertEqual(len(re.findall(r"^\| [RP]\d+ \|", out, re.M)), len(self.items))
        epic = rc.search_evidence(self.items, [big])[2][0]
        text = big.read_text(encoding="utf-8")
        self.assertEqual(epic["line"], line_of(text, "Rebuilt the Epic scheduling"))

    def test_docx_and_text_evidence(self):
        from fixtures import BLOCKS, write_docx
        doc = write_docx(BLOCKS, self.dir / "old.docx")
        found = rc.search_evidence(["Rewired ladder logic on Allen-Bradley PLCs"], [doc])[0]
        self.assertTrue(found)
        self.assertEqual(found[0]["file"], "old.docx")
        self.assertIn("Keller Plastics", found[0]["heading"])
        txt = self.dir / "profile.txt"
        txt.write_text("EXPERIENCE\n\nLakeview Family Medicine\nRebuilt Epic scheduling templates.\n"
                       "\nEDUCATION\n\nBS, Health Administration\n", encoding="utf-8")
        found = rc.search_evidence(["Epic scheduling"], [txt])[0]
        self.assertEqual(found[0]["line"], 4)
        self.assertIn("EXPERIENCE", found[0]["heading"])

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext (poppler) is not installed")
    def test_pdf_evidence_goes_through_pdftotext(self):
        pdf = self.dir / "profile.pdf"
        pdf.write_bytes(tiny_pdf(["EXPERIENCE", "Lakeview Family Medicine",
                                  "Rebuilt Epic scheduling templates.", "EDUCATION",
                                  "BS, Health Administration"]))
        found = rc.search_evidence(["Epic scheduling"], [pdf])[0]
        self.assertEqual(found[0]["file"], "profile.pdf")
        self.assertIn("EXPERIENCE", found[0]["heading"])
        self.assertIn("Rebuilt Epic scheduling", found[0]["text"])

    def test_evidence_and_resume_together(self):
        resume = self.dir / "resume.json"
        resume.write_text(json.dumps(RESUME), encoding="utf-8")
        out = rc.build(self.posting, resume, evidence=[self.notes], today=TODAY)
        self.assertIn("| # | Type | Qualification | Status | Proof line (section) | Evidence (file, line, heading) | Action |", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
