#!/usr/bin/env python3
"""build_resume.py v2: the source format, the layout, the refusals."""
import copy
import json
import re
import sys
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import SCRIPTS, run, BLOCKS  # noqa: E402
sys.path.insert(0, str(SCRIPTS))
import build_resume  # noqa: E402
import _docx  # noqa: E402

EN = "\u2013"


def blocks():
    return copy.deepcopy(BLOCKS)


def index_of(bl, **match):
    for i, b in enumerate(bl):
        if all(b.get(k) == v for k, v in match.items()):
            return i
    raise KeyError(match)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.docx = self.dir / "Dana-Reyes-Resume.docx"
        self.txt = self.dir / "Dana-Reyes-Resume.txt"

    def _src(self, bl, name="Dana Reyes"):
        p = self.dir / "src.json"
        p.write_text(json.dumps({"name": name, "blocks": bl}), encoding="utf-8")
        return p

    def build(self, bl, *extra):
        return run("build_resume.py", self._src(bl), "--out", self.dir,
                   "--today", "2026-09", *extra)

    def refused(self, bl, *needles):
        code, out = self.build(bl)
        self.assertEqual(code, 1, out)
        self.assertIn("BUILD REFUSED", out)
        for n in needles:
            self.assertIn(n, out)
        self.assertFalse(self.docx.exists(), "a refused build wrote a file")
        return out


class Builds(Base):
    def test_builds_both_files_from_one_source(self):
        code, out = self.build(blocks())
        self.assertEqual(code, 0, out)
        self.assertTrue(self.docx.is_file())
        self.assertTrue(self.txt.is_file())

    def test_output_is_a_valid_docx(self):
        self.build(blocks())
        with zipfile.ZipFile(self.docx) as z:
            for part in ("[Content_Types].xml", "_rels/.rels", "word/document.xml",
                         "word/styles.xml", "word/numbering.xml"):
                self.assertIn(part, z.namelist(), part)

    def test_default_layout_is_company_first(self):
        """The live Workday test picked company first. v1.6 had no role kind."""
        self.build(blocks())
        lines = _docx.lines(self.docx)
        i = lines.index("Brightline Tool, Toledo, OH")
        self.assertEqual(lines[i + 1], f"Maintenance Supervisor | Mar 2018 {EN} Present")
        self.assertIn(f"Maintenance Technician | Jun 2010 {EN} Feb 2018", lines)

    def _runs(self, text):
        """(text, bold) for every run in the paragraph that holds `text`."""
        with zipfile.ZipFile(self.docx) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        for para in re.findall(r"<w:p>.*?</w:p>", xml):
            runs = re.findall(r"<w:r>(.*?)</w:r>", para)
            got = [("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", r)), "<w:b/>" in r) for r in runs]
            if text in "".join(t for t, _b in got):
                return got
        raise AssertionError(f"no paragraph holds {text!r}")

    def test_company_line_and_job_title_are_bold_dates_are_not(self):
        """v2.1: the title is bold too. Ladders' 2018 eye-tracking study found bold
        job titles in the resumes recruiters rated best (S53); v2.0 bolded the
        company line only."""
        self.build(blocks())
        self.assertTrue(all(b for _t, b in self._runs("Brightline Tool, Toledo, OH")))
        runs = self._runs("Maintenance Supervisor")
        self.assertEqual(runs[0], ("Maintenance Supervisor", True))
        self.assertEqual(runs[1], (f" | Mar 2018 {EN} Present", False))
        self.assertIn(f"Maintenance Supervisor | Mar 2018 {EN} Present", _docx.lines(self.docx))

    def test_plain_title_keeps_the_first_tested_look(self):
        code, out = self.build(blocks(), "--plain-title")
        self.assertEqual(code, 0, out)
        self.assertEqual(self._runs("Maintenance Supervisor"),
                         [(f"Maintenance Supervisor | Mar 2018 {EN} Present", False)])

    def test_the_package_has_every_part_word_writes(self):
        """v2.1: a six-part package parsed on Workday but Lever's parser refused
        it (L04); the same text saved with the full set of parts parsed."""
        self.build(blocks())
        with zipfile.ZipFile(self.docx) as z:
            names = z.namelist()
            for part in ("docProps/core.xml", "docProps/app.xml", "word/settings.xml",
                         "word/fontTable.xml", "word/webSettings.xml", "word/theme/theme1.xml"):
                self.assertIn(part, names)
            for n in names:
                ET.fromstring(z.read(n))       # every part is well-formed XML
            types = z.read("[Content_Types].xml").decode("utf-8")
            rels = z.read("word/_rels/document.xml.rels").decode("utf-8") + \
                z.read("_rels/.rels").decode("utf-8")
            for part in names:
                if part.endswith(".rels") or part == "[Content_Types].xml":
                    continue
                self.assertIn(f'PartName="/{part}"', types, part)
                self.assertIn(part.split("word/", 1)[-1], rels, part)
            core = z.read("docProps/core.xml").decode("utf-8")
        self.assertIn("<dc:creator>Dana Reyes</dc:creator>", core)

    def test_text_file_has_the_same_lines(self):
        self.build(blocks())
        txt = [ln[2:] if ln.startswith("- ") else ln
               for ln in self.txt.read_text(encoding="utf-8").splitlines() if ln.strip()]
        doc = _docx.lines(self.docx)
        self.assertEqual([t.lower() for t in txt], [t.lower() for t in doc])

    def test_other_layouts_can_still_be_built(self):
        code, out = self.build(blocks(), "--layout", "title-first")
        self.assertEqual(code, 0, out)
        lines = _docx.lines(self.docx)
        i = lines.index("Maintenance Supervisor")
        self.assertEqual(lines[i + 1], f"Brightline Tool, Toledo, OH | Mar 2018 {EN} Present")
        code, out = self.build(blocks(), "--layout", "one-line")
        self.assertEqual(code, 0, out)
        self.assertIn(f"Maintenance Supervisor | Brightline Tool | Toledo, OH | Mar 2018 {EN} Present",
                      _docx.lines(self.docx))

    def test_layout_help_names_the_live_test(self):
        _code, out = run("build_resume.py", "--help")
        self.assertIn("2026-09-28", out)
        self.assertIn("company-first", out)
        self.assertIn("glued the title into the company field", out)

    def test_spacing_is_the_sep_14_spec(self):
        """Half-inch margins on all four sides. v1.6 used 0.6 inch left and right."""
        self.build(blocks())
        with zipfile.ZipFile(self.docx) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        mar = re.search(r"<w:pgMar [^>]*/>", xml).group(0)
        for side in ("top", "right", "bottom", "left"):
            self.assertIn(f'w:{side}="720"', mar)
        self.assertEqual(build_resume.STYLE["bullet"], (21, 0, 1, False))
        self.assertEqual(build_resume.STYLE["header"], (24, 6, 3, True))
        self.assertEqual(build_resume.STYLE["title-line"], (21, 3, 2, True))

    def test_docstring_example_builds(self):
        """v1.6's own example used a header the build refuses."""
        m = re.search(r"\n    (\{\n.*?\n    \})\n", build_resume.__doc__, re.S)
        example = json.loads(m.group(1))
        p = self.dir / "example.json"
        p.write_text(json.dumps(example), encoding="utf-8")
        code, out = run("build_resume.py", p, "--out", self.dir, "--today", "2026-09")
        self.assertEqual(code, 0, out)

    def test_unsafe_font_warns_but_builds(self):
        code, out = self.build(blocks(), "--font", "Comic Sans MS")
        self.assertEqual(code, 0, out)
        self.assertIn("WARNING", out)

    def test_missing_phone_or_email_warns_but_builds(self):
        bl = blocks()
        bl[index_of(bl, kind="contact")]["text"] = "Toledo, OH | linkedin.com/in/danareyes"
        code, out = self.build(bl)
        self.assertEqual(code, 0, out)
        self.assertIn("no phone number", out)
        self.assertIn("no email", out)

    def test_old_role_with_no_bullet_builds(self):
        """The 15-year rule only covers recent roles."""
        bl = blocks()
        i = index_of(bl, kind="earlier")
        bl[i:i] = [{"kind": "role", "company": "Maumee Molding", "city": "Maumee",
                    "state": "OH", "title": "Line Operator", "start": "Jun 2004",
                    "end": "May 2010"}]
        bl.pop(index_of(bl, kind="earlier"))
        code, out = self.build(bl)
        self.assertEqual(code, 0, out)


class Refuses(Base):
    def test_refuses_a_working_marker(self):
        bl = blocks() + [{"kind": "bullet", "text": "Cut costs [NEEDS NUMBER] last year."}]
        self.refused(bl, "square-bracketed text")

    def test_refuses_a_working_marker_in_a_role_field(self):
        bl = blocks()
        bl[index_of(bl, kind="role", company="Keller Plastics")]["city"] = "TBD"
        self.refused(bl, "a working marker")

    def test_refuses_a_sixth_header(self):
        self.refused(blocks() + [{"kind": "header", "text": "Key Accomplishments"}],
                     "not one of the five")

    def test_retired_kinds_say_what_to_use(self):
        for kind, needle in (("title", "\"role\" block"), ("meta", "\"role\" block"),
                             ("label", "single \"para\"")):
            out = self.refused(blocks() + [{"kind": kind, "text": "Anything"}], needle)
            self.assertIn("retired", out)

    def test_role_missing_a_field(self):
        bl = blocks()
        del bl[index_of(bl, kind="role", company="Keller Plastics")]["state"]
        self.refused(bl, "missing state")

    def test_role_with_text_field(self):
        bl = blocks()
        bl[index_of(bl, kind="role", company="Keller Plastics")]["text"] = "Keller Plastics"
        self.refused(bl, "no \"text\" field")

    def test_dates_must_be_mon_yyyy(self):
        for start, needle in (("January 2019", "Mon YYYY"), ("2019", "Mon YYYY"),
                              ("03/2019", "Mon YYYY"), ("Present", "Mon YYYY"),
                              ("Sept 2019", "\"Sep\"")):
            bl = blocks()
            bl[index_of(bl, kind="role", company="Keller Plastics")]["start"] = start
            self.refused(bl, needle)
        bl = blocks()
        bl[index_of(bl, kind="role", company="Brightline Tool")]["end"] = "Current"
        self.refused(bl, "\"Present\"")

    def test_comma_in_title_is_refused_with_the_reason(self):
        bl = blocks()
        bl[index_of(bl, kind="role", company="Keller Plastics")]["title"] = \
            "Technician, Maintenance"
        out = self.refused(bl, "Workday keeps only the text before a comma",
                           "descriptor first")
        self.assertIn("\"Senior Analyst, Supply Chain\" becomes \"Supply Chain "
                      "Senior Analyst\"", out)

    def test_parenthesis_in_title_is_refused(self):
        bl = blocks()
        bl[index_of(bl, kind="role", company="Keller Plastics")]["title"] = \
            "Maintenance Technician (Nights)"
        self.refused(bl, "opening parenthesis")

    def test_a_comma_before_a_company_suffix_is_refused(self):
        """v2.1: the fix keeps the suffix, without the comma. Greenhouse and RChilli
        say a suffix helps a parser recognize a company (S14, S95)."""
        bl = blocks()
        bl[index_of(bl, kind="role", company="Keller Plastics")]["company"] = \
            "Keller Plastics, Inc."
        self.refused(bl, "Keep a legal suffix without the comma")

    def test_a_suffix_without_a_comma_builds(self):
        bl = blocks()
        bl[index_of(bl, kind="role", company="Keller Plastics")]["company"] = "Keller Plastics Inc."
        code, out = self.build(bl)
        self.assertEqual(code, 0, out)
        self.assertIn("Keller Plastics Inc., Findlay, OH", _docx.lines(self.docx))

    def test_recent_role_with_no_bullet(self):
        bl = blocks()
        i = index_of(bl, kind="role", company="Keller Plastics")
        del bl[i + 1]
        self.refused(bl, "last 15 years", "Maintenance Technician")

    def test_today_moves_the_15_year_line(self):
        bl = blocks()
        i = index_of(bl, kind="role", company="Keller Plastics")
        del bl[i + 1]
        code, out = run("build_resume.py", self._src(bl), "--out", self.dir,
                        "--today", "2034-01")
        self.assertEqual(code, 0, out)

    def test_bullet_under_summary(self):
        bl = blocks()
        bl.insert(index_of(bl, kind="header", text="Experience"),
                  {"kind": "bullet", "text": "Cut downtime from 14 hours to 4 per week."})
        self.refused(bl, "under Summary")

    def test_more_than_one_skills_line(self):
        bl = blocks() + [{"kind": "para", "text": "Lockout tagout, root cause analysis"}]
        self.refused(bl, "Skills has 2 lines")

    def test_skills_line_inside_experience(self):
        bl = blocks()
        i = index_of(bl, kind="role", company="Keller Plastics")
        bl.insert(i, {"kind": "para", "text": "Skills: Fiix, hydraulics"})
        self.refused(bl, "\"Skills:\" line inside Experience")

    def test_two_earlier_lines(self):
        bl = blocks()
        i = index_of(bl, kind="earlier")
        bl.insert(i, {"kind": "earlier", "text": "Earlier career: Stock Clerk, 2002 to 2004."})
        self.refused(bl, "2 earlier-career lines")

    def test_earlier_line_not_at_the_end(self):
        bl = blocks()
        e = bl.pop(index_of(bl, kind="earlier"))
        bl.insert(index_of(bl, kind="role", company="Keller Plastics"), e)
        self.refused(bl, "must be the last line of Experience")

    def test_earlier_line_outside_experience(self):
        bl = blocks()
        e = bl.pop(index_of(bl, kind="earlier"))
        bl.insert(index_of(bl, kind="header", text="Skills"), e)
        self.refused(bl, "outside Experience")

    def test_every_reason_is_listed(self):
        bl = blocks()
        bl[index_of(bl, kind="role", company="Keller Plastics")]["start"] = "Sept 2010"
        bl[index_of(bl, kind="role", company="Brightline Tool")]["title"] = "Supervisor, Maintenance"
        out = self.refused(bl)
        self.assertIn("\"Sep\"", out)
        self.assertIn("comma", out)


class WritesSafely(Base):
    def test_malformed_block_leaves_no_file_behind(self):
        code, out = self.build([{"kind": "bullet"}])
        self.assertEqual(code, 1, out)
        self.assertFalse(self.docx.exists())
        self.assertFalse(list(self.dir.glob("*.tmp")))

    def test_a_failed_rebuild_does_not_corrupt_a_good_build(self):
        self.build(blocks())
        good = self.docx.read_bytes()
        self.build([{"kind": "bullet", "text": 7}])
        self.assertEqual(self.docx.read_bytes(), good)

    def test_a_failed_text_write_leaves_both_old_files(self):
        """v1.6 replaced the .docx, then wrote the .txt. A failure between the
        two left a new .docx next to an old .txt."""
        self.build(blocks())
        old_doc, old_txt = self.docx.read_bytes(), self.txt.read_bytes()
        bl = blocks()
        bl[index_of(bl, kind="headline")]["text"] = "Reliability Engineer"
        (self.dir / "Dana-Reyes-Resume.txt.tmp").mkdir()   # the .txt cannot be written
        code, out = self.build(bl)
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.docx.read_bytes(), old_doc)
        self.assertEqual(self.txt.read_bytes(), old_txt)
        self.assertFalse((self.dir / "Dana-Reyes-Resume.docx.tmp").exists())



class EarlierLineDates(unittest.TestCase):
    def test_dash_year_range_on_the_earlier_line_is_refused(self):
        d = Path(tempfile.mkdtemp())
        blocks = [dict(b) for b in BLOCKS]
        for b in blocks:
            if b["kind"] == "earlier":
                b["text"] = "Earlier career: Line Operator at Maumee Molding in Maumee, OH, 2004 \u2013 2010."
        src = d / "src.json"
        src.write_text(json.dumps({"name": "Dana Reyes", "blocks": blocks}), encoding="utf-8")
        code, out = run("build_resume.py", src, "--out", d, "--today", "2026-09")
        self.assertEqual(code, 1, out)
        self.assertIn("2004 to 2010", out)



class KeepTitlePunctuation(unittest.TestCase):
    def test_candidate_can_keep_a_comma_title_by_choice(self):
        d = Path(tempfile.mkdtemp())
        blocks = [dict(b) for b in BLOCKS]
        for b in blocks:
            if b["kind"] == "role":
                b["title"] = "Supervisor, Maintenance"
                break
        src = d / "src.json"
        src.write_text(json.dumps({"name": "Dana Reyes", "blocks": blocks}), encoding="utf-8")
        code, out = run("build_resume.py", src, "--out", d, "--today", "2026-09")
        self.assertEqual(code, 1, out)
        code, out = run("build_resume.py", src, "--out", d, "--today", "2026-09",
                        "--keep-title-punctuation")
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
