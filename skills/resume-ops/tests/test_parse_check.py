#!/usr/bin/env python3
"""parse_check.py v2: a structure check, and plain about what it is not."""
import copy
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import SCRIPTS, run, BLOCKS, write_docx  # noqa: E402
sys.path.insert(0, str(SCRIPTS))
import parse_check  # noqa: E402

EN = "\u2013"


def role(bl, company):
    return next(b for b in bl if b.get("kind") == "role" and b.get("company") == company)


class ParseCheck(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def built(self, *extra):
        src = self.dir / "src.json"
        src.write_text(json.dumps({"name": "Dana Reyes", "blocks": BLOCKS}), encoding="utf-8")
        code, out = run("build_resume.py", src, "--out", self.dir, "--today", "2026-09", *extra)
        self.assertEqual(code, 0, out)
        return self.dir / "Dana-Reyes-Resume.docx"

    def written(self, bl, name="r.docx"):
        return write_docx(bl, self.dir / name)

    def add_parts(self, docx, parts):
        with zipfile.ZipFile(docx, "a") as z:
            for name, data in parts.items():
                z.writestr(name, data)
        return docx

    # -- verdict and wording

    def test_clean_build_passes(self):
        code, out = run("parse_check.py", self.built())
        self.assertEqual(code, 0, out)
        self.assertIn("STRUCTURE CHECK: PASS ", out)
        self.assertNotIn("missing parts Word always writes", out)

    def test_a_bare_package_is_a_warning(self):
        """v2.1: Lever's parser refused the six-part file v2.0 built (L04)."""
        bare = write_docx(copy.deepcopy(BLOCKS), self.dir / "bare.docx", bare=True)
        code, out = run("parse_check.py", bare)
        self.assertEqual(code, 0, out)
        self.assertIn("missing parts Word always writes (docProps/core.xml, docProps/app.xml, "
                      "word/styles.xml, word/settings.xml, word/webSettings.xml, "
                      "word/fontTable.xml, word/theme/theme1.xml)", out)
        self.assertIn("PASS WITH WARNINGS", out)

    def test_says_it_is_not_a_prediction_at_top_and_bottom(self):
        _code, out = run("parse_check.py", self.built())
        self.assertEqual(out.count("not a prediction of what Workday"), 2, out)
        self.assertIn("live upload", out)
        self.assertLess(out.index("not a prediction"), out.index("TEXT IN FILE ORDER"))
        for old in ("PARSE SAFETY", "what the system sees", "actually extracts"):
            self.assertNotIn(old, out)

    def test_international_phone_is_accepted(self):
        for number in ("+44 20 7123 4567", "+61 2 9374 4000", "+91 98765 43210",
                       "+353 1 234 5678", "(419) 555-0134", "+1 419 555 0134"):
            self.assertTrue(parse_check.PHONE_RE.search(number), number)

    # -- dates

    def test_a_date_in_a_sentence_is_not_a_second_format(self):
        """v1.6 counted every date in the text, so a month named in a bullet
        failed the file for mixed formats."""
        bl = copy.deepcopy(BLOCKS)
        bl.insert(9, {"kind": "bullet",
                      "text": "Opened the second paint line in September 2021 on schedule."})
        code, out = run("parse_check.py", self.written(bl))
        self.assertEqual(code, 0, out)
        self.assertNotIn("Mixed date formats", out)

    def test_mixed_formats_on_date_lines_fail(self):
        bl = copy.deepcopy(BLOCKS)
        role(bl, "Keller Plastics")["start"] = "June 2010"
        code, out = run("parse_check.py", self.written(bl))
        self.assertEqual(code, 1, out)
        self.assertIn("Mixed date formats", out)

    def test_sept_warns(self):
        bl = copy.deepcopy(BLOCKS)
        role(bl, "Keller Plastics")["start"] = "Sept 2010"
        code, out = run("parse_check.py", self.written(bl))
        self.assertEqual(code, 0, out)
        self.assertIn("[WARN] \"Sept 2010\" uses \"Sept\". Write \"Sep\".", out)

    def test_date_formats_count_only_range_lines(self):
        used = parse_check.date_formats([
            f"Maintenance Supervisor | Mar 2018 {EN} Present",
            "Earlier career: Line Operator, 2004 to 2010.",
            "Won the plant safety award in October 2019.",
            "AAS, Industrial Maintenance | Owens Community College | 2009",
        ])
        self.assertEqual(used, {"Mon YYYY": 1})

    # -- layout faults

    def test_images_fail(self):
        """The v1.6 scoring rule failed images; v1.6 only warned."""
        docx = self.add_parts(self.built(), {"word/media/image1.png": b"\x89PNG"})
        code, out = run("parse_check.py", docx)
        self.assertEqual(code, 1, out)
        self.assertIn("[FAIL] 1 image(s)", out)
        self.assertIn("without images", out)

    def test_contact_in_page_header_fails(self):
        hdr = ('<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               '<w:p><w:r><w:t>dana@example.com | (419) 555-0134</w:t></w:r></w:p></w:hdr>')
        docx = self.add_parts(self.built(), {"word/header1.xml": hdr})
        code, out = run("parse_check.py", docx)
        self.assertEqual(code, 1, out)
        self.assertIn("Contact details in the page header", out)

    def test_table_fails(self):
        docx = self.written(BLOCKS)
        with zipfile.ZipFile(docx) as z:
            parts = {n: z.read(n) for n in z.namelist()}
        parts["word/document.xml"] = parts["word/document.xml"].replace(
            b"<w:body>", b"<w:body><w:tbl><w:tr><w:tc><w:p/></w:tc></w:tr></w:tbl>")
        with zipfile.ZipFile(docx, "w") as z:
            for n, d in parts.items():
                z.writestr(n, d)
        code, out = run("parse_check.py", docx)
        self.assertEqual(code, 1, out)
        self.assertIn("table(s) found", out)

    def test_no_phone_and_no_email_fail(self):
        bl = copy.deepcopy(BLOCKS)
        bl[2]["text"] = "Toledo, OH | linkedin.com/in/danareyes"
        code, out = run("parse_check.py", self.written(bl))
        self.assertEqual(code, 1, out)
        self.assertIn("No email", out)
        self.assertIn("No phone number", out)

    def test_working_marker_fails(self):
        bl = copy.deepcopy(BLOCKS) + [{"kind": "para", "text": "Cut scrap [NEEDS NUMBER]."}]
        code, out = run("parse_check.py", self.written(bl))
        self.assertEqual(code, 1, out)
        self.assertIn("Working marker", out)

    # -- headers

    def test_non_standard_header_warns(self):
        bl = copy.deepcopy(BLOCKS) + [{"kind": "header", "text": "Key Accomplishments"},
                                      {"kind": "para", "text": "Plant safety award, 2019."}]
        code, out = run("parse_check.py", self.written(bl))
        self.assertEqual(code, 0, out)
        self.assertIn("[WARN] Non-standard header: \"Key Accomplishments\"", out)
        self.assertIn("PASS WITH WARNINGS", out)
        self.assertNotIn("map to a field", out)

    def test_no_headers_names_the_plain_ones(self):
        bl = [b for b in BLOCKS if b["kind"] != "header"]
        _code, out = run("parse_check.py", self.written(bl))
        self.assertIn("\"Experience\", \"Education\"", out)
        self.assertNotIn("Professional Experience", out)

    # -- roles

    def test_role_without_city_and_state_warns(self):
        bl = BLOCKS[:6] + [
            {"kind": "para", "text": "Brightline Tool"},
            {"kind": "para", "text": f"Maintenance Supervisor | Mar 2018 {EN} Present"},
            {"kind": "bullet", "text": "Trained 6 technicians on the new hydraulics procedure."},
        ] + BLOCKS[12:]
        code, out = run("parse_check.py", self.written(bl))
        self.assertEqual(code, 0, out)
        self.assertIn("[WARN] The job \"Brightline Tool\" has no \"City, ST\"", out)

    def test_every_built_layout_reads_city_and_state(self):
        for layout in ("company-first", "title-first", "one-line"):
            code, out = run("parse_check.py", self.built("--layout", layout))
            self.assertEqual(code, 0, f"{layout}: {out}")
            self.assertNotIn("City, ST", out, layout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
