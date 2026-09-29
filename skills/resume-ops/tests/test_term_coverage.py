#!/usr/bin/env python3
"""term_coverage.py tests. Every posting, employer and resume here is invented."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import BLOCKS, SCRIPTS, run  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import term_coverage as tc  # noqa: E402

NURSE = """Senior Staff Nurse - Emergency Department
Required qualifications:
- Advanced Life Support (ALS) certification
- Demonstrated experience with clinical audit
Responsibilities:
You will lead triage decisions, manage patient flow, and support junior staff.
Triage experience is essential. Patient flow and triage are central to this role.
"""

WAREHOUSE = """Source: https://northwind.wd3.myworkdayjobs.com/External/job/Reno-NV/Warehouse-Operations-Manager_R0012345
System: Workday. Saved 2026-09-01.
Location: Reno, Nevada
Pay: $90,000 - $110,000
Type: Full time

Title: Warehouse Operations Manager

About Northwind
Northwind runs cold-chain warehouses for grocers across the West.

What you'll do
- Run inbound and outbound operations for a 300,000 square foot cold-chain site.
- Own slotting, cycle counts and labor planning in Manhattan WMS.
- Report dock-to-stock time and labor planning results to the regional director.
- Coach shift leads on labor planning and safety walks.

Minimum Qualifications
- 7+ years in warehouse operations, 3+ years leading shift supervisors
- Hands-on experience with a warehouse management system
- Bachelor's degree in supply chain or a related field, or equivalent experience

Preferred Qualifications
- Master's degree in operations management
- Lean Six Sigma Green Belt
- Experience with Power BI dashboards

Travel Requirements & Working Conditions
- Travel to sister sites in Sparks up to 10% of the time
"""


def terms_of(posting, tier=None):
    rows = tc.term_list(posting)
    return {t: tr for t, _s, tr, _sp in rows if tier is None or tr == tier}


class KeptFromV16(unittest.TestCase):
    def test_ngrams_do_not_cross_clauses(self):
        terms = tc.candidate_terms(NURSE)
        for junk in ("decisions manage", "manage patient flow and"):
            self.assertNotIn(junk, terms, junk)

    def test_central_unigram_survives(self):
        self.assertIn("triage", tc.candidate_terms(NURSE))

    def test_spread_counts_clauses(self):
        _s, _t, spread = tc.candidate_terms(NURSE)["triage"]
        self.assertGreaterEqual(spread, 3)

    def test_tiers_come_from_posting_sections(self):
        terms = tc.candidate_terms(NURSE)
        self.assertEqual(terms["clinical audit"][1], 1)
        self.assertEqual(terms["patient flow"][1], 3)

    def test_acronym_and_expansion_match_each_other(self):
        acros = tc.acronym_pairs(NURSE)
        self.assertEqual(acros.get("als"), "advanced life support")
        hits, _out, how = tc.find("als", tc.Resume.from_text("Certified in advanced life support."), acros)
        self.assertTrue(hits)
        self.assertIn("advanced life support", how)

    def test_word_forms_match(self):
        hits, _out, how = tc.find("strategies", tc.Resume.from_text("Wrote the pricing strategy."))
        self.assertTrue(hits)
        self.assertIn("word-form", how)


class Headings(unittest.TestCase):
    REQUIRED = ["Qualifications", "Minimum Qualifications", "Basic Qualifications", "Required Qualifications",
                "What you bring", "What You'll Need", "What We're Looking For", "Role Requirements",
                "Required Skills & Experience", "Requirements"]
    PREFERRED = ["Preferred Qualifications", "Nice to Have", "Bonus if you have", "Desired Skills", "Pluses"]

    def tier_of_item(self, heading):
        posting = f"Title: Line Cook\n\nAbout the kitchen\nA 90-seat bistro.\n\n{heading}\n- Food handler permit\n"
        return terms_of(posting).get("food handler permit")

    def test_required_headings(self):
        """v1.6 missed 'Qualifications', 'What you bring' and 'Role Requirements' (S1)."""
        for h in self.REQUIRED:
            for form in (h, h + ":", "## " + h, "**" + h + "**"):
                self.assertEqual(self.tier_of_item(form), 1, form)

    def test_preferred_headings(self):
        for h in self.PREFERRED:
            for form in (h, h + ":", "### " + h):
                self.assertEqual(self.tier_of_item(form), 2, form)

    def test_an_unknown_heading_ends_the_section(self):
        """'Travel Requirements & Working Conditions' is not a list of requirements."""
        terms = terms_of(WAREHOUSE)
        self.assertEqual(terms.get("sister sites"), 3)
        self.assertEqual(terms.get("sigma green belt"), 2)

    def test_inline_heading(self):
        posting = "Title: Line Cook\n\nRequirements: food handler permit and 2 years on a hot line.\n"
        self.assertEqual(terms_of(posting).get("food handler permit"), 1)

    def test_file_header_lines_are_skipped(self):
        """Source:, System:, Location:, Pay: and Type: describe the file, not the job."""
        terms = terms_of(WAREHOUSE)
        for junk in ("reno", "nevada", "saved", "full time", "workday"):
            self.assertNotIn(junk, terms, junk)


class TermList(unittest.TestCase):
    def test_job_title_is_forced_into_tier_1(self):
        """tailoring.md says the title is Tier 1; v1.6 left it in Tier 3 (X10)."""
        self.assertEqual(terms_of(WAREHOUSE).get("warehouse operations manager"), 1)
        self.assertEqual(terms_of(NURSE).get("senior staff nurse"), 1)

    def test_repeated_language_is_at_least_tier_2(self):
        """'labor planning' sits only under What you'll do, three times (X11)."""
        self.assertEqual(terms_of(WAREHOUSE).get("labor planning"), 2)

    def test_numeric_tokens_are_never_terms(self):
        terms = terms_of(WAREHOUSE)
        for t in terms:
            self.assertFalse(any(tc.breaker(w) for w in t.split()), t)
        self.assertNotIn("7+", terms)

    def test_employer_name_is_left_out(self):
        """v1.6 reported the employer's own name as a missing term (S3)."""
        self.assertEqual(tc.employer_names(WAREHOUSE), ["Northwind"])
        self.assertNotIn("northwind", terms_of(WAREHOUSE))

    def test_employer_from_a_board_path_or_company_line(self):
        board = "Source: https://job-boards.greenhouse.io/ridgelinefoods/jobs/123\n\nRidgeline Foods hires cooks.\n"
        self.assertEqual(tc.employer_names(board), ["Ridgeline Foods"])
        company = "Company: Ardent Labs\nTitle: Chemist\n\nArdent Labs makes coatings.\n"
        self.assertEqual(tc.employer_names(company), ["Ardent Labs"])
        bare = "Chemist\n\nAt Corvel we test coatings. Chemists at Corvel run 40 tests a day. Join Corvel today.\n"
        self.assertEqual(tc.employer_names(bare), ["Corvel"])

    def test_a_workday_site_path_is_not_the_employer(self):
        names = tc.employer_names(WAREHOUSE)
        self.assertFalse([n for n in names if "External" in n or "Reno" in n])

    def test_the_list_depends_on_the_posting_only(self):
        """drop_redundant used to look at the resume, so before and after runs had
        different denominators (S2)."""
        self.assertEqual(tc.term_list(WAREHOUSE), tc.term_list(WAREHOUSE))
        d = Path(tempfile.mkdtemp())
        (d / "p.md").write_text(WAREHOUSE, encoding="utf-8")
        (d / "a.txt").write_text("Experience\n- Ran slotting and cycle counts in Manhattan WMS.\n", encoding="utf-8")
        (d / "b.txt").write_text("Experience\n- Ran inbound operations.\n", encoding="utf-8")
        outs = []
        for r in ("a.txt", "b.txt"):
            code, out = run("term_coverage.py", d / "p.md", d / r)
            self.assertEqual(code, 0, out)
            outs.append(out.splitlines()[1].split("/")[1])
        self.assertEqual(outs[0], outs[1])

    def test_same_output_under_any_hash_seed(self):
        d = Path(tempfile.mkdtemp())
        (d / "p.md").write_text(WAREHOUSE, encoding="utf-8")
        (d / "r.txt").write_text("Experience\n- Ran slotting and cycle counts in Manhattan WMS.\n", encoding="utf-8")
        outs = []
        for seed in ("1", "2"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            r = subprocess.run([sys.executable, str(SCRIPTS / "term_coverage.py"), str(d / "p.md"),
                                str(d / "r.txt")], capture_output=True, text=True, env=env)
            outs.append(r.stdout)
        self.assertEqual(outs[0], outs[1])

    def test_every_tier_is_reported_and_top_is_per_tier(self):
        """v1.6 cut the tier-sorted list at 45 and dropped all of Tier 3 (S2)."""
        d = Path(tempfile.mkdtemp())
        (d / "p.md").write_text(WAREHOUSE, encoding="utf-8")
        (d / "r.txt").write_text("Experience\n- Ran inbound operations.\n", encoding="utf-8")
        code, out = run("term_coverage.py", d / "p.md", d / "r.txt", "--top", "2")
        self.assertEqual(code, 0, out)
        for tier in ("TIER 1", "TIER 2", "TIER 3"):
            self.assertIn(tier, out)
        self.assertIn("more (raise --top", out)
        n3 = sum(1 for t in terms_of(WAREHOUSE).values() if t == 3)
        self.assertIn(f"/{n3} covered", out)


class Matching(unittest.TestCase):
    def test_master_does_not_match_a_named_plan(self):
        """'master' matched 'Master Plan' in v1.6 (S3)."""
        r = tc.Resume.from_text("Experience\n- Wrote the Riverside Master Plan with 3 city agencies.\n")
        self.assertEqual(tc.find("master", r)[0], 0)

    def test_master_still_matches_a_degree(self):
        for line in ("Earned a Master's degree in logistics in 2015.", "Master of Science, Logistics | 2015"):
            r = tc.Resume.from_text("Education\n" + line + "\n")
            self.assertTrue(tc.find("master", r)[0], line)

    def test_a_named_term_matches_its_name(self):
        posting = "Title: Analyst\n\nRequirements\n- Experience with Power BI dashboards\n"
        r = tc.Resume.from_text("Experience\n- Built 12 Power BI dashboards for the ops team.\n")
        self.assertTrue(tc.find("power bi", r, {}, tc.proper_terms(posting))[0])

    def test_repeats_are_counted_outside_skills(self):
        """The v1.6 scoring rule counted repeats outside the Skills section (X12)."""
        r = tc.Resume.from_text("Experience\n- Ran cycle counts weekly.\nSkills\nCycle counts, Slotting\n")
        hits, outside, _how = tc.find("cycle counts", r)
        self.assertEqual((hits, outside), (2, 1))
        hits, outside, _how = tc.find("slotting", r)
        self.assertEqual((hits, outside), (1, 0))

    def test_a_skills_only_hit_is_marked(self):
        d = Path(tempfile.mkdtemp())
        (d / "p.md").write_text(WAREHOUSE, encoding="utf-8")
        (d / "r.txt").write_text("Experience\n- Ran inbound operations.\nSkills\nSlotting, Manhattan WMS\n",
                                 encoding="utf-8")
        _code, out = run("term_coverage.py", d / "p.md", d / "r.txt")
        self.assertIn("(only in Skills)", out)

    def test_a_json_source_reads(self):
        d = Path(tempfile.mkdtemp())
        (d / "p.md").write_text("Title: Maintenance Supervisor\n\nRequirements\n- CNC machines and hydraulics\n",
                                encoding="utf-8")
        (d / "r.json").write_text(json.dumps({"blocks": BLOCKS}), encoding="utf-8")
        code, out = run("term_coverage.py", d / "p.md", d / "r.json")
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"maintenance supervisor\s+\(\d+x\)")


class Composite(unittest.TestCase):
    def test_tiers_by_share_of_postings(self):
        a = "Title: Dispatcher\n\nRequirements\n- Route planning and fleet tracking\n"
        b = "Title: Dispatcher\n\nRequirements\n- Route planning and driver scheduling\n"
        c = "Title: Dispatcher\n\nRequirements\n- Route planning and fuel cards\n"
        comp = tc.composite_terms([a, b, c])
        self.assertEqual(comp["route planning"][1], 1)        # 3 of 3
        self.assertEqual(comp["fleet tracking"][1], 2)        # 1 of 3 is 33%
        d = "Title: Dispatcher\n\nRequirements\n- Route planning\n"
        comp = tc.composite_terms([a, b, c, d])
        self.assertEqual(comp["fleet tracking"][1], 3)        # 1 of 4 is 25%

    def test_composite_cli(self):
        d = Path(tempfile.mkdtemp())
        for n, extra in enumerate(("fleet tracking", "driver scheduling", "fuel cards")):
            (d / f"p{n}.md").write_text(f"Title: Dispatcher\n\nRequirements\n- Route planning and {extra}\n",
                                        encoding="utf-8")
        code, out = run("term_coverage.py", "--composite", *sorted(d.glob("p*.md")))
        self.assertEqual(code, 0, out)
        self.assertIn("COMPOSITE TERMS across 3 postings", out)
        self.assertIn("route planning", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
