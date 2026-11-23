#!/usr/bin/env python3
"""spell_check.py (2.6.0): zero spelling errors before a resume goes out.
Every name, employer and number here is invented."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import SCRIPTS  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import draft_review as dr  # noqa: E402
import spell_check as sc  # noqa: E402

KNOWN = set("""rebuilt rebuild the a an for and of to in at on with by from team teams led lead
cut costs cost dock time hours carrier carriers scorecard yard system new trained leads manager
operations ran sites summary experience education skills managed public works plan county city
grew revenue up more than then report reports staff on-site site office opened""".split())


class FakeDictionary:
    name, where = "test list", "in memory"

    def unknown(self, words):
        return {w for w in words if w.lower() not in KNOWN}


ROLE = dr.role_block("Operations Manager", "Pellworth Freight", "Dayton", "OH", "Jan 2019", "Present")
PAST = dr.role_block("Operations Manager", "Arden Logistics", "Toledo", "OH", "Jan 2014", "Dec 2018")


def page(*bullets, role=ROLE):
    return [("para", "Avery Lindqvist"), ("para", "Dayton, OH | 303-555-0100 | avery@example.com"),
            ("header", "Experience"), role] + [("bullet", b) for b in bullets]


def found(blocks, allowed=frozenset()):
    bad, doubled, second = sc.check(blocks, FakeDictionary(), allowed)
    return [w for _n, w in bad], [w for _n, w in doubled], [w for _n, w in second]


class Words(unittest.TestCase):
    def test_a_misspelling_fails(self):
        bad, _d, _s = found(page("Rebuilt the carrier scorcard for the yard team."))
        self.assertEqual(bad, ["scorcard"])

    def test_names_acronyms_and_brands_pass(self):
        bad, _d, _s = found(page("Rebuilt the SQL scorecard for Kellbrook Grocers and BizzyPlanit."))
        self.assertEqual(bad, [])

    def test_the_name_contact_line_and_company_are_skipped(self):
        bad, _d, _s = found(page("Rebuilt the scorecard."))
        self.assertEqual(bad, [])

    def test_the_word_list_passes_a_term(self):
        bad, _d, _s = found(page("Rebuilt the glamping scorecard."), allowed={"glamping"})
        self.assertEqual(bad, [])

    def test_a_doubled_word_fails(self):
        _b, doubled, _s = found(page("Rebuilt the the scorecard."))
        self.assertEqual(doubled, ["the the"])

    def test_a_hyphen_prefix_is_not_a_word(self):
        bad, _d, _s = found(page("Rebuilt the on-site scorecard for the pre-construction team."))
        self.assertEqual(bad, ["construction"])     # not "pre"


class SecondReads(unittest.TestCase):
    def test_real_words_often_typed_for_others(self):
        _b, _d, second = found(page("Trained the new manger on the yard system.",
                                    "Grew revenue more then 12% in 2024."))
        self.assertTrue(any("manger" in s for s in second), second)
        self.assertTrue(any("then" in s for s in second), second)

    def test_lead_in_a_role_that_ended(self):
        _b, _d, second = found(page("Lead the dock team at 3 sites.", role=PAST))
        self.assertTrue(any(s.startswith("Lead") for s in second), second)
        _b, _d, second = found(page("Lead the dock team at 3 sites."))
        self.assertFalse(second)


class Dictionaries(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_a_hunspell_file_applies_its_rules(self):
        (self.dir / "t.aff").write_text("SET UTF-8\nPFX A Y 1\nPFX A 0 re .\nSFX S Y 1\nSFX S 0 s .\n",
                                        encoding="utf-8")
        (self.dir / "t.dic").write_text("2\nbuild/AS\nmanager/S\n", encoding="utf-8")
        d = sc.HunspellFile(str(self.dir / "t.dic"))
        self.assertEqual(d.unknown({"build", "builds", "rebuild", "rebuilds", "managers", "managr"}),
                         {"managr"})

    def test_no_dictionary_means_the_check_did_not_run(self):
        resume = self.dir / "r.md"
        resume.write_text("# Experience\n- Rebuilt the scorecard.\n", encoding="utf-8")
        with mock.patch.object(sc, "DIC_PLACES", ()), mock.patch.object(sc, "WORDS_FILE", "/nonexistent"), \
                mock.patch("shutil.which", return_value=None), mock.patch.dict(sys.modules, {"spellchecker": None}), \
                mock.patch.dict("os.environ", {"SPELL_CHECK_DIC": ""}), \
                mock.patch.object(sys, "argv", ["spell_check.py", str(resume)]):
            out = io.StringIO()
            with redirect_stdout(out):
                code = sc.main()
        self.assertEqual(code, 3)
        self.assertIn("not a pass", out.getvalue())

    def test_the_rulings_section_is_the_word_list(self):
        rulings = self.dir / "rulings.md"
        rulings.write_text("# Rulings\n\n## Build preferences\n\nglamping is not here\n\n"
                           "## Words the spell check passes\n\nNames, products, and terms of art.\n\n"
                           "- Example: Fiix\n- glamping, placemaking\n", encoding="utf-8")
        self.assertEqual(sc.load_word_list(rulings), {"fiix", "glamping", "placemaking"})
        plain_list = self.dir / "words.txt"
        plain_list.write_text("glamping\nplacemaking\n", encoding="utf-8")
        self.assertEqual(sc.load_word_list(plain_list), {"glamping", "placemaking"})


if __name__ == "__main__":
    unittest.main()
