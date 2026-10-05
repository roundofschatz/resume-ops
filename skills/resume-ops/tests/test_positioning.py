#!/usr/bin/env python3
"""A positioning file from job-seeker-ops's candidate-positioning skill (2.4.0).

resume-ops reads the file when it's there and builds as before when it isn't.
The sample in fixtures/positioning is a made-up writer's file with its posting
and resume, saved as Markdown because the repository ignores .txt files. Each
test of the new behavior fails on 2.3.0, which had no positioning_check.py; the
last two guard the build without a file."""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import ROOT, SCRIPTS, run, write_docx  # noqa: E402

SAMPLE = Path(__file__).resolve().parent / "fixtures" / "positioning"
NAME = "positioning-switchgrass-freight-supply-chain-planning-analyst.md"


class PositioningCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        for f in SAMPLE.iterdir():
            shutil.copy(f, self.dir / f.name)
        self.file = self.dir / NAME

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, old, new):
        text = self.file.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, old)
        self.file.write_bytes(text.replace(old, new).encode("utf-8"))

    def test_a_confirmed_file_is_read_for_the_build(self):
        code, out = run("positioning_check.py", self.file, "--posting", self.dir / "posting.md")
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: use it", out)
        self.assertIn("posting.md is the copy the file was built from", out)
        self.assertIn("What the reader should believe: Dmitri finds the input behind a forecast miss", out)
        proofs = out.split("PROOFS FOR THE RESUME", 1)[1].split("REQUIREMENT MAP", 1)[0]
        self.assertIn("P1 Forecast error cut", proofs)
        self.assertNotIn("P3", proofs)             # marked for the letter only
        self.assertIn("WORDS TO USE: forecasting, demand planning", out)
        self.assertIn('Watch for: "new to freight"', out)
        self.assertIn("a working note, never on the page", out)

    def test_another_copy_of_the_posting_isnt_used(self):
        other = self.dir / "posting-again.md"
        other.write_text((self.dir / "posting.md").read_text(encoding="utf-8") + "\nApply by Friday.\n",
                         encoding="utf-8")
        code, out = run("positioning_check.py", self.file, "--posting", other)
        self.assertEqual(code, 1, out)
        self.assertIn("isn't the copy the file was built from", out)
        self.assertIn("Ask the candidate once", out)

    def test_the_same_posting_with_windows_line_endings_matches(self):
        crlf = self.dir / "posting-crlf.md"
        crlf.write_bytes((self.dir / "posting.md").read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        code, out = run("positioning_check.py", self.file, "--posting", crlf)
        self.assertEqual(code, 0, out)

    def test_an_unconfirmed_file_isnt_used(self):
        text = self.file.read_text(encoding="utf-8")
        text = re.sub(r"^- \*\*Confirmed:\*\*.*$", "- **Confirmed:** not yet", text, flags=re.M)
        self.file.write_bytes(text.encode("utf-8"))
        code, out = run("positioning_check.py", self.file)
        self.assertEqual(code, 1, out)
        self.assertIn("isn't confirmed yet", out)

    def test_an_unknown_format_stops(self):
        self.edit("Format: candidate-positioning 1", "Format: candidate-positioning 2")
        code, out = run("positioning_check.py", self.file)
        self.assertEqual(code, 2, out)
        self.assertIn("format 2", out)

    def test_a_file_missing_a_section_stops(self):
        self.edit("## 7. Keep off the page", "## Keep off the page")
        code, out = run("positioning_check.py", self.file)
        self.assertEqual(code, 2, out)
        self.assertIn("missing section(s) 7", out)

    def test_a_keep_off_phrase_on_the_built_resume_fails(self):
        docx = self.dir / "Dmitri-Okafor-Resume.docx"
        write_docx([
            {"kind": "name", "text": "Dmitri Okafor"},
            {"kind": "header", "text": "Experience"},
            {"kind": "role", "company": "Brightwell Grocers Distribution", "city": "Olathe", "state": "KS",
             "title": "Planning Analyst", "start": "Aug 2021", "end": "Present"},
            {"kind": "bullet", "text": "New to freight, but cut forecast error from 31% to 19% with SQL."},
        ], docx)
        code, out = run("positioning_check.py", self.file, "--resume", docx)
        self.assertEqual(code, 1, out)
        self.assertIn('FAIL: "new to freight" is on the page, from the keep-off list (Gap (R7))', out)

    def test_a_clean_resume_passes_and_lists_the_words_on_it(self):
        code, out = run("positioning_check.py", self.file, "--resume", self.dir / "resume.md")
        self.assertEqual(code, 0, out)
        self.assertIn("Words to use on the page: forecasting (4, word-form match), SQL (2)", out)
        self.assertIn("Words to use not on the page: demand planning", out)

    def test_the_skill_says_the_file_isnt_evidence_and_a_ruling_beats_it(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scripts/positioning_check.py", skill)
        self.assertIn("it isn't evidence", skill)
        tailoring = (ROOT / "references" / "tailoring.md").read_text(encoding="utf-8")
        section = tailoring.split("## A positioning file", 1)[1].split("\n## ", 1)[0]
        self.assertIn("A ruling beats it", section)
        self.assertIn("The keep-off list stays off", section)

    def test_the_review_offer_needs_a_positioning_file(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        line = next(l for l in skill.splitlines() if "submission review" in l)
        self.assertIn("When a positioning file was used", line)
        self.assertIn("Without a positioning file, neither appears", line)


class WithoutAFile(unittest.TestCase):
    """Without a positioning file, a build runs exactly as in 2.3.0."""

    def test_the_level_set_block_stays_at_six_lines(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        block = re.search(r"```\n(LEVEL SET:.*?)\n```", skill, re.S).group(1)
        self.assertEqual(len(block.splitlines()), 6, block)

    def test_no_other_script_reads_a_positioning_file(self):
        for script in sorted(SCRIPTS.glob("*.py")):
            if script.name == "positioning_check.py":
                continue
            text = script.read_text(encoding="utf-8").lower()
            # The word itself shows up in other senses ("first-person positioning");
            # what matters is that nothing else opens the file or calls its reader.
            for mark in ("positioning_check", "positioning file", "positioning-"):
                self.assertNotIn(mark, text, f"{script.name} mentions {mark}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
