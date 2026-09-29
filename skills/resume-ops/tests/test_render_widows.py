#!/usr/bin/env python3
"""render_pdf.py and widow_check.py.

The matching tests use made-up rendered lines, so they run without
LibreOffice. The end-to-end tests skip when no renderer is installed.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import SCRIPTS, run, BLOCKS  # noqa: E402
sys.path.insert(0, str(SCRIPTS))
import render_pdf  # noqa: E402
import widow_check  # noqa: E402

SUMMARY = ("Maintenance supervisor with 11 years keeping CNC and hydraulic lines running in "
           "discrete manufacturing. Rebuilt the preventive maintenance schedule and cut "
           "unplanned downtime from 14 hours to 4 per week. Trains the night shift before "
           "buying new equipment.")


def check(blocks, lines):
    return widow_check.check(blocks, lines)


class Matching(unittest.TestCase):
    """widow_check.check() on synthetic rendered lines."""

    def test_hyphenated_word_broken_at_its_hyphen_matches(self):
        """v1.6 counted words, so "blow-" and "molding" were two words against
        one in the .docx, and the block came back COULD NOT MATCH."""
        blocks = [("bullet", "Rewired the ladder logic on 4 PLCs, ending a weekly jam on "
                             "the blow-molding line at the east plant.", "experience")]
        lines = ["\u2022 Rewired the ladder logic on 4 PLCs, ending a weekly jam on the blow-",
                 "molding line at the east plant."]
        widows, longs, unmatched, matched = check(blocks, lines)
        self.assertEqual((matched, unmatched), (1, []))
        self.assertEqual(widows, [])

    def test_minus_split_from_its_number_matches_and_counts(self):
        """A "-38%" broken after the minus. The last line holds one word, and
        that is a widow."""
        blocks = [("bullet", "Rebuilt the changeover checklist for all four presses, "
                             "cutting scrap -38%", "experience")]
        lines = ["\u2022 Rebuilt the changeover checklist for all four presses, cutting scrap -",
                 "38%"]
        widows, _longs, unmatched, matched = check(blocks, lines)
        self.assertEqual((matched, unmatched), (1, []))
        self.assertEqual([n for _t, n, _l in widows], [1])

    def test_leading_minus_on_a_continuation_line_is_kept(self):
        """v1.6 stripped a leading dash from every line as if it were a bullet."""
        blocks = [("bullet", "Rebuilt the changeover checklist for all four presses and "
                             "cut scrap -38% in the first quarter", "experience")]
        lines = ["\u2022 Rebuilt the changeover checklist for all four presses and cut scrap",
                 "-38% in the first quarter"]
        _w, _l, unmatched, matched = check(blocks, lines)
        self.assertEqual((matched, unmatched), (1, []))

    def test_hyphen_added_by_the_renderer_matches(self):
        blocks = [("para", "Scheduled preventive maintenance for 22 machines", "summary")]
        lines = ["Scheduled preventive mainte-", "nance for 22 machines"]
        _w, _l, unmatched, matched = check(blocks, lines)
        self.assertEqual((matched, unmatched), (1, []))

    def test_multi_line_summary_is_not_over_two_lines(self):
        """The v1.6 test used a one-line summary, so it could not fail."""
        blocks = [("header", "Summary", "summary"), ("para", SUMMARY, "summary")]
        words = SUMMARY.split()
        lines = ["Summary"] + [" ".join(words[i:i + 12]) for i in range(0, len(words), 12)]
        self.assertGreater(len(lines) - 1, 2)
        _w, longs, unmatched, matched = check(blocks, lines)
        self.assertEqual((matched, unmatched, longs), (2, [], []))

    def test_three_line_bullet_is_over_two_lines(self):
        words = SUMMARY.split()
        lines = ["\u2022 " + " ".join(words[:12])] + \
            [" ".join(words[i:i + 12]) for i in range(12, len(words), 12)]
        _w, longs, _u, _m = check([("bullet", SUMMARY, "experience")], lines)
        self.assertEqual([n for _t, n in longs], [len(lines)])

    def test_skills_line_is_exempt_from_the_two_line_cap(self):
        text = ", ".join(f"Tool {i}" for i in range(40))
        lines = [text[:60], text[60:120], text[120:]]
        _w, longs, unmatched, _m = check([("bullet", text, "skills")], lines)
        self.assertEqual((longs, unmatched), ([], []))

    def test_one_word_widow_is_found(self):
        blocks = [("bullet", "Trained 6 technicians on the new hydraulics procedure "
                             "across both shifts this year", "experience")]
        lines = ["\u2022 Trained 6 technicians on the new hydraulics procedure across both shifts this",
                 "year"]
        widows, _l, _u, _m = check(blocks, lines)
        self.assertEqual([n for _t, n, _l2 in widows], [1])

    def test_stray_line_between_blocks_is_skipped(self):
        blocks = [("header", "Experience", "experience"),
                  ("para", "Brightline Tool, Toledo, OH", "experience")]
        _w, _l, unmatched, matched = check(blocks, ["Experience", "2", "Brightline Tool, Toledo, OH"])
        self.assertEqual((matched, unmatched), (2, []))

    def test_different_text_does_not_match(self):
        _w, _l, unmatched, matched = check([("para", "Brightline Tool, Toledo, OH", "")],
                                           ["Keller Plastics, Findlay, OH"])
        self.assertEqual((matched, len(unmatched)), (0, 1))


class Render(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        src = self.dir / "src.json"
        src.write_text(json.dumps({"name": "Dana Reyes", "blocks": BLOCKS}), encoding="utf-8")
        run("build_resume.py", src, "--out", self.dir, "--today", "2026-09")
        self.docx = self.dir / "Dana-Reyes-Resume.docx"

    def test_no_container_path_is_hard_coded(self):
        self.assertFalse(hasattr(render_pdf, "BUNDLED"))
        self.assertIn(r"C:\Program Files\LibreOffice\program\soffice.exe",
                      render_pdf.INSTALL_PATHS)
        self.assertIn("/Applications/LibreOffice.app/Contents/MacOS/soffice",
                      render_pdf.INSTALL_PATHS)

    def test_no_renderer_exits_3_and_says_not_a_pass(self):
        if any(Path(p).is_file() for p in render_pdf.INSTALL_PATHS):
            self.skipTest("LibreOffice is installed in a fixed folder here")
        env = dict(os.environ, PATH=str(self.dir))
        r = subprocess.run([sys.executable, str(SCRIPTS / "render_pdf.py"), str(self.docx)],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("not a pass", (r.stdout + r.stderr).lower())

    def test_default_pdf_goes_to_a_temp_folder_not_beside_the_resume(self):
        code, out = run("render_pdf.py", self.docx)
        if code == 3:
            self.skipTest("no PDF renderer available")
        self.assertEqual(code, 0, out)
        pdf = Path(out.splitlines()[0])
        self.addCleanup(shutil.rmtree, pdf.parent, True)
        self.assertTrue(pdf.is_file(), out)
        self.assertTrue(pdf.parent.name.startswith("resume-ops-check-"), pdf)
        self.assertFalse((self.dir / "Dana-Reyes-Resume.pdf").exists())
        self.assertIn("check file", out)
        self.assertIn("Do not send it", out)

    def test_out_dir_is_kept(self):
        out_dir = self.dir / "render"
        code, out = run("render_pdf.py", self.docx, "--out-dir", out_dir)
        if code == 3:
            self.skipTest("no PDF renderer available")
        self.assertTrue((out_dir / "Dana-Reyes-Resume.pdf").is_file(), out)

    def test_widow_check_on_a_real_render(self):
        out_dir = self.dir / "render"
        code, _ = run("render_pdf.py", self.docx, "--out-dir", out_dir)
        if code != 0:
            self.skipTest("no PDF renderer available")
        _code, out = run("widow_check.py", self.docx, out_dir / "Dana-Reyes-Resume.pdf")
        if "pdftotext was not found" in out:
            self.skipTest("pdftotext not installed")
        self.assertNotIn("OVER TWO LINES", out)
        self.assertIn("0 not matched", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
