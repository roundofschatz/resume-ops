#!/usr/bin/env python3
"""draft_review.py tests. Every name, employer and number here is invented."""
import json
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import BLOCKS, FIXTURES, SCRIPTS, run, write_docx  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import draft_review as dr  # noqa: E402

EM = chr(0x2014)
ROLE = dr.role_block("Operations Manager", "Harbor Freightways", "Dayton", "OH", "Jan 2019", "Present")
NOT_A_CATCH = {"no number and no named thing", "long bullet", "every metric is a percentage"}


def as_bullet(text):
    return [("header", "Experience"), ROLE, ("bullet", text)]


def fail_names(blocks):
    return [n for _i, n, _h, _x in dr.review(blocks)[0]]


def review_names(blocks):
    return [n for _i, n, _h, _x in dr.review(blocks)[1]]


def resume(summary, bullets, skills=None, extra=()):
    blocks = [("para", "Avery Lindqvist"),
              ("para", "Denver, CO | 303-555-0100 | avery@example.com"),
              ("header", "Summary")]
    blocks += [("para", s) for s in ([summary] if isinstance(summary, str) else summary)]
    blocks += [("header", "Experience"), ROLE]
    blocks += [("bullet", b) for b in bullets]
    blocks += list(extra)
    if skills is not None:
        blocks += [("header", "Skills")] + [("para", s) for s in
                                            ([skills] if isinstance(skills, str) else skills)]
    return blocks


class Loading(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.json = self.dir / "src.json"
        self.json.write_text(json.dumps({"name": "Dana Reyes", "blocks": BLOCKS}), encoding="utf-8")
        self.docx = write_docx(BLOCKS, self.dir / "src.docx")

    def test_the_reference_fixture_is_clean(self):
        """BLOCKS models correct v2 output. If it breaks a rule, every test built
        on it measures the wrong thing."""
        fails, _ = dr.review(dr.load(self.json))
        self.assertFalse(fails, [(n, h) for _i, n, h, _x in fails])

    def test_json_and_docx_agree(self):
        """One document read two ways gives one verdict."""
        a = dr.review(dr.load(self.json))
        b = dr.review(dr.load(self.docx))
        self.assertEqual(sorted((i, n, h) for i, n, h, _f in a[0]), sorted((i, n, h) for i, n, h, _f in b[0]))
        self.assertEqual(sorted((i, n, h) for i, n, h, _f in a[1]), sorted((i, n, h) for i, n, h, _f in b[1]))

    def test_docx_role_lines_become_one_role(self):
        """v1.6 read the company line and the title line as two prose paragraphs."""
        blocks = dr.load(self.docx)
        roles = [b for b in blocks if b[0] == "role"]
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0][2]["company"], "Brightline Tool")
        self.assertEqual(roles[0][2]["title"], "Maintenance Supervisor")
        self.assertEqual(roles[0][2]["end"], "Present")
        self.assertFalse([b for b in blocks if b[0] == "para" and "Brightline Tool, Toledo" in b[1]])

    def test_role_lines_are_not_prose_checked(self):
        """'Robust Freight' opens its line, so a prose check calls it a vague
        size word, as v1.6 did. It is a company."""
        blocks = [dict(b) for b in BLOCKS]
        for b in blocks:
            if b.get("company") == "Keller Plastics":
                b["company"] = "Robust Freight"
        docx = write_docx(blocks, self.dir / "robust.docx")
        self.assertNotIn("vague size word", fail_names(dr.load(docx)))

    def test_title_first_layout_still_reads(self):
        blocks = dr.collapse_roles([("header", "Experience"), ("para", "Line Lead"),
                                    ("para", "Keller Plastics, Findlay, OH | Jun 2010 – Feb 2018")])
        self.assertEqual(blocks[1][0], "role")
        self.assertEqual(blocks[1][2]["title"], "Line Lead")
        self.assertEqual(blocks[1][2]["company"], "Keller Plastics")

    def test_docx_path_sees_sections(self):
        marked = dr.sections(dr.load(self.docx))
        self.assertTrue(any(s == "skills" for _k, _t, s in marked))

    def test_plain_text_resume_reads(self):
        txt = self.dir / "r.txt"
        txt.write_text("Summary\nShift lead with 6 years in cold-chain freight.\nExperience\n"
                       "Harbor Freightways, Dayton, OH\nOperations Manager | Jan 2019 – Present\n"
                       "- Cut dock-to-stock time from 9 hours to 4 across 3 docks.\n", encoding="utf-8")
        kinds = [b[0] for b in dr.load(txt)]
        self.assertEqual(kinds, ["header", "para", "header", "role", "bullet"])

    def test_cli_exit_codes(self):
        code, out = run("draft_review.py", self.json)
        self.assertEqual(code, 0, out)
        bad = self.dir / "bad.json"
        blocks = [dict(b) for b in BLOCKS] + [{"kind": "header", "text": "Experience"},
                                              {"kind": "bullet", "text": "Leveraged synergies across teams."}]
        bad.write_text(json.dumps({"blocks": blocks}), encoding="utf-8")
        code, out = run("draft_review.py", bad)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL", out)


class GeneralTells(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = json.loads((FIXTURES / "tells.json").read_text(encoding="utf-8"))

    def caught(self, text):
        f, r = dr.review(as_bullet(text))
        return [n for _i, n, _h, _x in f + r if n not in NOT_A_CATCH]

    def test_fixture_shape(self):
        by = defaultdict(int)
        for t in self.fx["tells"]:
            by[t["class"]] += 1
        self.assertEqual(len(by), 24, sorted(by))
        self.assertGreaterEqual(len(self.fx["tells"]), 44)
        self.assertTrue(all(n >= 2 for c, n in by.items() if c != "borrowed framework"), dict(by))
        self.assertGreaterEqual(len(self.fx["clean"]), 21)

    def test_at_least_80_percent_of_tells_are_caught(self):
        """v1.6 caught 13 of 44 (30%) on the red team's run."""
        per, missed = defaultdict(lambda: [0, 0]), []
        for t in self.fx["tells"]:
            per[t["class"]][0] += 1
            if self.caught(t["text"]):
                per[t["class"]][1] += 1
            else:
                missed.append(t)
        total = sum(v[0] for v in per.values())
        got = sum(v[1] for v in per.values())
        self.assertGreaterEqual(got / total, 0.80,
                                f"{got}/{total}; missed: {[(m['class'], m['text']) for m in missed]}")

    def test_at_most_one_clean_line_draws_a_fail(self):
        """v1.6 failed 8 of 11 exact-term sentences."""
        bad = [(c, fail_names(as_bullet(c))) for c in self.fx["clean"] if fail_names(as_bullet(c))]
        self.assertLessEqual(len(bad), 1, bad)

    def test_exact_terms_of_art_pass(self):
        for text in self.fx["clean"][:11]:
            self.assertFalse(fail_names(as_bullet(text)), text)

    def test_em_dash_and_double_hyphen_fail(self):
        """v1.6 only asked for a second read of an em dash."""
        for text in (f"Cut the backlog {EM} and kept it cut.", "Cut the backlog -- and kept it cut."):
            self.assertIn("em dash", fail_names(as_bullet(text)), text)

    def test_en_dash_in_a_date_range_is_fine(self):
        self.assertNotIn("em dash", fail_names(as_bullet("Ran the night shift, 2019 – 2021, for 3 plants.")))

    def test_utilization_is_a_noun_utilize_is_a_verb(self):
        self.assertNotIn("latinate default", fail_names(as_bullet("Raised fleet utilization from 61% to 78%.")))
        for verb in ("Utilized SQL to find 40 duplicate invoices.", "Utilizing 3 vendors, cut costs 9%.",
                     "Utilize the new scanner on every inbound pallet."):
            self.assertIn("latinate default", fail_names(as_bullet(verb)), verb)

    def test_a_capitalized_name_is_not_a_tell(self):
        for ok in ("Opened the store on Rather Street in 2019.", "Moved the lab to Foster City in 2021."):
            self.assertFalse(fail_names(as_bullet(ok)), ok)
        self.assertIn("hedge", fail_names(as_bullet("Rather quickly rebuilt 3 routes.")))

    def test_partitive_most_of_is_not_a_comparison(self):
        self.assertFalse(fail_names(as_bullet("Kept 2 lines running while most of the crew was out sick.")))
        self.assertIn("empty comparison",
                      fail_names(as_bullet("Unlike most planners, finished the route map in 2 days.")))

    def test_literal_facilitation_is_not_flagged(self):
        f, r = dr.review(as_bullet("Facilitated 12 planning workshops with 40 shop-floor staff."))
        self.assertFalse([n for _i, n, _h, _x in f + r if n == "latinate default"])


class KeptFromV16(unittest.TestCase):
    STRANDED = [
        ("header", "Summary"),
        ("para", "Registered Nurse with 12 years in acute care. Led the sepsis rollout "
                 "that moved compliance from 54% to 91%. Ran a 32-bed unit averaging "
                 "210 admissions a month."),
        ("header", "Experience"),
        ("bullet", "Precepted 11 newly qualified nurses over three years."),
    ]
    REDISTRIBUTED = [
        ("header", "Summary"),
        ("para", "Registered Nurse with 12 years in acute care."),
        ("header", "Experience"),
        ("bullet", "Led the sepsis rollout that moved compliance from 54% to 91% across two wards."),
        ("bullet", "Ran a 32-bed unit averaging 210 admissions a month."),
        ("bullet", "Precepted 11 newly qualified nurses over three years."),
    ]

    def test_evidence_only_in_the_summary_fails(self):
        fails, _ = dr.review(self.STRANDED)
        hits = [h for _i, n, h, _x in fails if n == "evidence only in the Summary"]
        for fig in ("54%", "91%", "32-bed", "210 admissions"):
            self.assertIn(fig, hits, fig)

    def test_tenure_is_not_orphaned_evidence(self):
        fails, _ = dr.review(self.STRANDED)
        self.assertFalse([h for _i, n, h, _x in fails if n == "evidence only in the Summary" and "year" in h])

    def test_redistributed_evidence_passes(self):
        fails, _ = dr.review(self.REDISTRIBUTED)
        self.assertFalse([f for f in fails if f[1] == "evidence only in the Summary"])

    def test_settled_rules_fail(self):
        for bad in ("Responsible for maintaining the line.", "Spearheaded the rollout.",
                    "Built the program from scratch.", "Helped to deliver the project.",
                    "Not just maintenance, but reliability engineering."):
            self.assertTrue(fail_names([("bullet", bad)]), bad)

    def test_invented_comparison_fails(self):
        for bad in ("Where most agencies hand off, stayed through implementation.",
                    "Unlike most candidates in this field, has run both sides.",
                    "Few practitioners can do both.",
                    "In an industry where rigor is rare, brought it.",
                    "The average manager stops at the report."):
            self.assertIn("empty comparison", fail_names([("bullet", bad)]), bad)

    def test_real_comparisons_and_ordinary_most_survive(self):
        for ok in ("Led the most recent role transition for the West region.",
                   "Cut most delays in the intake queue by rebuilding triage.",
                   "Managed most of the West region across four states.",
                   "Precepted 11 nurses, most of whom now run their own shifts.",
                   "Built few-shot prompt engineering into the review pipeline.",
                   "Rebuilt the team where the migration happened.",
                   "Cut defect rate to 0.4%, against a plant average of 2.1%."):
            self.assertFalse(fail_names([("bullet", ok)]), ok)

    def test_amplified_superlative_and_bridge_the_gap_fail(self):
        for bad in ("Truly one of the most innovative programs in the portfolio.",
                    "Genuinely unique approach to intake.",
                    "Bridged the gap between design and engineering."):
            self.assertTrue(fail_names([("bullet", bad)]), bad)

    def test_naming_a_gap_fails(self):
        for bad in ("Has not used Salesforce, but learns fast.",
                    "No prior experience in healthcare, though the skills transfer.",
                    "Still learning Kubernetes.", "On paper, light on retail."):
            self.assertIn("names a gap", fail_names([("bullet", bad)]), bad)

    def test_spelled_out_count_is_a_number(self):
        names = review_names([("header", "Experience"),
                              ("bullet", "Rebuilt the handover procedure, now standard across four sites.")])
        self.assertNotIn("no number and no named thing", names)

    def test_long_bullet_points_to_widow_check(self):
        text = ("Rebuilt the inbound receiving schedule for the regional distribution center so that "
                "every carrier had a fixed door and a fixed window and the dock never sat idle again.")
        hits = [(n, x) for _i, n, _h, x in dr.review(as_bullet(text))[1] if n == "long bullet"]
        self.assertTrue(hits)
        self.assertIn("widow_check", hits[0][1])
        self.assertIn("Two rendered lines", hits[0][1])


class Summary(unittest.TestCase):
    GOOD = ("Freight operations manager with 9 years running cross-dock sites for regional carriers. "
            "Cut dock-to-stock time from 9 hours to 4 at Harbor Freightways by giving each carrier a "
            "fixed door. Believes the night crew knows the building best, so the schedule starts "
            "with their notes.")
    BULLETS = ["Cut dock-to-stock time from 9 hours to 4 by giving each carrier a fixed door and window.",
               "Trained 14 dock leads on the new yard system, now used at 3 sites."]

    def test_a_good_summary_is_clean(self):
        fails, _ = dr.review(resume(self.GOOD, self.BULLETS))
        self.assertFalse(fails, [(n, h) for _i, n, h, _x in fails])

    def test_bullet_under_summary_fails(self):
        blocks = resume(self.GOOD, self.BULLETS)
        blocks.insert(4, ("bullet", "Cut dock-to-stock time from 9 hours to 4."))
        self.assertIn("bullet under Summary", fail_names(blocks))

    def test_keyword_strip_at_the_end_fails(self):
        for strip in ("Cross-docking, yard management, OSHA compliance, carrier relations.",
                      "Specialties: cross-docking, yard management and carrier relations."):
            names = fail_names(resume([self.GOOD, strip], self.BULLETS))
            self.assertIn("summary ends on a keyword strip", names, strip)

    def test_a_list_sentence_with_a_verb_is_not_a_strip(self):
        text = self.GOOD + " Ran sites in Ohio, Indiana, Kentucky and Michigan."
        self.assertNotIn("summary ends on a keyword strip", fail_names(resume(text, self.BULLETS)))

    def test_first_person_fails_anywhere(self):
        for bad in ("Cut dock time 40% after I rebuilt the door schedule.",
                    "Our team cut dock time 40% in 2022.",
                    "Rebuilt my region's carrier scorecard for 6 carriers."):
            self.assertIn("first person", fail_names(resume(self.GOOD, [bad])), bad)

    def test_pronoun_lookalikes_pass(self):
        for ok in ("Shipped to 14 US states within 48 hours.",
                   "Ran safety at a 400-person copper mine for 3 years.",
                   "Led the Phase I build of the 2-site warehouse network.",
                   "Stocked 22 aisles for Our Town Market in 2021."):
            self.assertNotIn("first person", fail_names(resume(self.GOOD, [ok])), ok)

    def test_repeating_what_the_bullets_prove_never_fails(self):
        """v2.0.1 retired the one-repeat cap. A summary says in simpler form what
        the bullets below prove, so two or more repeated claims are not a fault."""
        two = ("Freight operations manager with 9 years running cross-dock sites. Cut dock-to-stock time "
               "from 9 hours to 4 with fixed carrier doors. Trained 14 dock leads on the new yard system.")
        fails = fail_names(resume(two, self.BULLETS))
        self.assertFalse(fails, fails)
        names = fails + review_names(resume(two, self.BULLETS))
        self.assertNotIn("summary repeats the bullets", names)
        self.assertNotIn("summary repeats a bullet", names)

    def test_word_for_word_copy_is_a_review_not_a_fail(self):
        start = "Freight operations manager with 9 years running cross-dock sites for regional carriers. "
        copied = start + "Trained 14 dock leads on the new yard system, now used at 3 sites."
        restated = start + "Trained the 14 leads who now run the yard system."
        self.assertIn("summary copies a bullet", review_names(resume(copied, self.BULLETS)))
        self.assertNotIn("summary copies a bullet", fail_names(resume(copied, self.BULLETS)))
        self.assertFalse(fail_names(resume(copied, self.BULLETS)))
        self.assertNotIn("summary copies a bullet", review_names(resume(restated, self.BULLETS)))

    def test_a_shared_phrase_is_not_a_copy(self):
        """A roll-up line that names the employers shares a few words with each
        role. That is a summary doing its job, not a copy."""
        rollup = "Trained dock leads and cut dock time at every site on the new yard system."
        self.assertIsNone(dr.copied_from(rollup, self.BULLETS))
        self.assertIsNotNone(dr.copied_from(self.BULLETS[1], self.BULLETS))

    def test_named_client_only_in_the_summary_fails(self):
        text = self.GOOD + " Won the Pellworth Grocers account in 2022."
        fails = dr.review(resume(text, self.BULLETS))[0]
        self.assertIn("Pellworth Grocers", [h for _i, n, h, _x in fails if n == "evidence only in the Summary"])

    def test_employer_name_in_the_summary_is_not_orphaned(self):
        fails = dr.review(resume(self.GOOD, self.BULLETS))[0]
        self.assertFalse([h for _i, n, h, _x in fails if "Harbor" in h])

    def test_summary_length_is_a_review(self):
        self.assertIn("summary length", review_names(resume("Freight manager.", self.BULLETS)))
        self.assertNotIn("summary length", review_names(resume(self.GOOD, self.BULLETS)))

    def test_unnamed_count_is_a_review(self):
        unnamed = self.GOOD + " Opened distribution centers for four retailers."
        named = self.GOOD + " Opened distribution centers for two retailers, Pellworth and Arden."
        self.assertIn("unnamed count", review_names(resume(unnamed, self.BULLETS)))
        self.assertNotIn("unnamed count", review_names(resume(named, self.BULLETS)))


class CareerTotals(unittest.TestCase):
    """v2.0.1: a total the candidate confirmed that spans several jobs may sit in
    the summary with no single role behind it."""
    SUMMARY = ("Freight operations manager with 9 years running cross-dock sites for regional carriers. "
               "Cut dock-to-stock time at Harbor Freightways from 9 hours to 4. "
               "Ran 120+ safety workshops for drivers and dock crews.")
    BULLETS = Summary.BULLETS

    def orphans(self, totals=(), summary=None):
        fails = dr.review(resume(summary or self.SUMMARY, self.BULLETS), totals)[0]
        return [h for _i, n, h, _x in fails if n == "evidence only in the Summary"]

    def test_an_unlisted_total_still_fails(self):
        self.assertIn("120", self.orphans())

    def test_a_confirmed_total_passes(self):
        self.assertEqual(self.orphans(["120+ safety workshops"]), [])
        self.assertEqual(self.orphans(["120+ workshops"]), [])

    def test_a_total_covers_only_what_it_counts(self):
        self.assertIn("120", self.orphans(["120+ yard audits"]))
        other = self.SUMMARY + " Cut claims 40% in a year."
        self.assertIn("40%", self.orphans(["120+ safety workshops"], other))

    def test_the_json_source_carries_the_totals(self):
        d = Path(tempfile.mkdtemp())
        blocks = [{"kind": b[0] if b[0] in ("header", "bullet") else "para", "text": b[1]}
                  for b in resume(self.SUMMARY, self.BULLETS) if b[0] != "role"]
        blocks.insert(5, {"kind": "role", "company": "Harbor Freightways", "city": "Dayton",
                          "state": "OH", "title": "Operations Manager", "start": "Jan 2019", "end": "Present"})
        bare, listed = d / "bare.json", d / "listed.json"
        bare.write_text(json.dumps({"blocks": blocks}), encoding="utf-8")
        listed.write_text(json.dumps({"career_totals": ["120+ safety workshops"], "blocks": blocks}),
                          encoding="utf-8")
        self.assertEqual(dr.load_totals(listed), ["120+ safety workshops"])
        self.assertEqual(dr.load_totals(bare), [])
        code, out = run("draft_review.py", bare)
        self.assertEqual(code, 1, out)
        self.assertIn("career_totals", out)
        code, out = run("draft_review.py", listed)
        self.assertEqual(code, 0, out)


class Skills(unittest.TestCase):
    BULLETS = ["Rebuilt the reporting layer in SQL for 3 plants.",
               "Ran quarterly cycle counts in Manhattan WMS across 22 aisles."]

    def test_more_than_one_line_fails(self):
        blocks = resume(Summary.GOOD, self.BULLETS, skills=["SQL, Manhattan WMS", "Forklift certified"])
        self.assertIn("more than one line under Skills", fail_names(blocks))
        self.assertNotIn("more than one line under Skills",
                         fail_names(resume(Summary.GOOD, self.BULLETS, skills="SQL, Manhattan WMS")))

    def test_skills_line_inside_experience_fails(self):
        blocks = resume(Summary.GOOD, self.BULLETS, extra=[("para", "Skills: SQL, Manhattan WMS")])
        self.assertIn("skills line inside Experience", fail_names(blocks))

    def test_item_in_no_role_bullet_is_a_review(self):
        blocks = resume(Summary.GOOD, self.BULLETS, skills="SQL, GIS, Manhattan WMS")
        flagged = [h for _i, n, h, _x in dr.review(blocks)[1] if n == "skill in no role bullet"]
        self.assertEqual(flagged, ["GIS"])

    def test_the_summary_is_not_evidence(self):
        """v1.6 counted Summary text as evidence for a skill (X9)."""
        text = Summary.GOOD + " Known for lean scheduling."
        blocks = resume(text, self.BULLETS, skills="SQL, Lean scheduling")
        flagged = [h for _i, n, h, _x in dr.review(blocks)[1] if n == "skill in no role bullet"]
        self.assertIn("Lean scheduling", flagged)

    def test_whole_words_not_four_letter_stems(self):
        """v1.6 passed 'Brand identity' on 'iden' in 'resident' (S6)."""
        bullets = ["Surveyed 600 residents on the new park plan and presented results to the brand team."]
        blocks = resume(Summary.GOOD, bullets, skills="Brand identity")
        flagged = [h for _i, n, h, _x in dr.review(blocks)[1] if n == "skill in no role bullet"]
        self.assertIn("Brand identity", flagged)

    def test_word_forms_and_short_forms_count(self):
        bullets = ["Scheduled 85 drivers across 3 depots.", "Cut customer experience complaints 30%."]
        blocks = resume(Summary.GOOD, bullets, skills="Driver scheduling, Customer experience (CX)")
        self.assertFalse([h for _i, n, h, _x in dr.review(blocks)[1] if n == "skill in no role bullet"])


class NameTheSet(unittest.TestCase):
    """2.3.0: a count of abstract things names its set, what it was about or
    for, or the count comes off (references/writing.md, Name what you count).
    Before, only a count followed by "including" or "such as" was flagged, so a
    line that settled "seven decisions" and never said what they were shipped."""
    FAIL_NAME, OWNER = "count names nothing", "set named only by its owner"

    def flags(self, text):
        return fail_names(as_bullet(text)) + review_names(as_bullet(text))

    def test_a_count_that_names_nothing_fails_and_a_named_set_passes(self):
        bare = ("Ran a two-hour workshop with the founders of Ridgeline Tile that settled seven "
                "decisions, then built their pitch for a $2M raise.")
        named = ("Ran a two-hour workshop with the founders of Ridgeline Tile that settled seven "
                 "decisions on pricing and the launch date, then built their pitch for a $2M raise.")
        self.assertIn(self.FAIL_NAME, fail_names(as_bullet(bare)))
        self.assertNotIn(self.FAIL_NAME, self.flags(named))
        self.assertNotIn(self.OWNER, self.flags(named))

    def test_a_generic_word_is_not_a_name(self):
        for bad in ("Settled seven key decisions with the founders.",
                    "Settled seven strategic decisions with the founders.",
                    "Turned 40 interviews into 11 plan directives and wrote the council memo.",
                    "Ranked seven development priorities for the new owners.",
                    "Delivered 14 themes and 17 recommendations to the museum board.",
                    "Wrote 10 measurable goals."):
            self.assertIn(self.FAIL_NAME, fail_names(as_bullet(bad)), bad)

    def test_counts_of_concrete_things_are_scope(self):
        self.assertIn(self.FAIL_NAME, fail_names(as_bullet("Rolled out four new tools across the firm.")))
        for ok in ("Led 13 stakeholder interviews for Harbor Mutual.",
                   "Opened 4 stores in 18 months, each at break-even within a year.",
                   "Made 200 credit decisions a month on small-business loans.",
                   "Resolved 1,200 IT issues a month for 900 employees.",
                   "Scored 12 goals as captain of the club team."):
            self.assertNotIn(self.FAIL_NAME, self.flags(ok), ok)

    def test_a_range_a_list_or_a_subject_names_the_set(self):
        self.assertIn(self.FAIL_NAME, fail_names(as_bullet("Named five operating problems.")))
        for ok in ("Named five operating problems, from valet parking to late checkout.",
                   "Set three priorities: patient falls, sepsis screening and discharge speed.",
                   "Turned 40 interviews into 11 directives for rewriting the downtown gateway plan.",
                   "Set five pricing priorities for the regional sales team.",
                   "Settled seven decisions that set the brand's price, name and first buyer.",
                   "Ran a workshop for 40 ICU nurses that produced 12 pilot ideas, 5 of which went live."):
            flags = self.flags(ok)
            self.assertNotIn(self.FAIL_NAME, flags, ok)
            self.assertNotIn(self.OWNER, flags, ok)

    def test_the_hyphen_form(self):
        self.assertIn(self.FAIL_NAME,
                      fail_names(as_bullet("Built a six-pillar roadmap with short- and long-term steps.")))
        self.assertNotIn(self.FAIL_NAME,
                         self.flags("Built a 12-point safety checklist for the press line."))

    def test_an_owner_alone_gets_a_second_read(self):
        text = "Set five priorities for the regional sales team."
        self.assertIn(self.OWNER, review_names(as_bullet(text)))
        self.assertNotIn(self.FAIL_NAME, fail_names(as_bullet(text)))

    def test_a_label_with_nothing_behind_it_fails(self):
        for bad in ("Presented key insights to the executive team.",
                    "Delivered strategic recommendations to the board.",
                    "Turned the survey into actionable insights for leadership."):
            self.assertIn("label names nothing", fail_names(as_bullet(bad)), bad)
        for ok in ("Presented key insights on churn to the executive team.",
                   "Led the Strategic Initiatives Group for 3 years.",
                   "Built the key accounts program for 14 distributors."):
            self.assertNotIn("label names nothing", self.flags(ok), ok)

    def test_skills_and_education_lines_are_not_read_for_sets(self):
        blocks = resume(Summary.GOOD, Summary.BULLETS,
                        skills="Three core services, strategic recommendations, SQL")
        names = [n for _i, n, _h, _x in dr.review(blocks)[0]]
        self.assertNotIn(self.FAIL_NAME, names)
        self.assertNotIn("label names nothing", names)
        bad = resume(Summary.GOOD, Summary.BULLETS + ["Codified three core services and their deliverables."])
        self.assertIn(self.FAIL_NAME, fail_names(bad))


class WordsTheSentenceAlreadyMeans(unittest.TestCase):
    """2.3.0: a word the sentence means without it gets cut
    (references/writing.md, Words the sentence already means). Before, the
    review knew only "from scratch"."""

    def test_own_after_a_possessive_is_a_second_read(self):
        text = "Built a guest model whose four segments include the hotel's own front-desk staff."
        self.assertIn("redundant word", review_names(as_bullet(text)))
        needed = "Gave each region its own P&L and cut overhead 9%."
        self.assertNotIn("redundant word", fail_names(as_bullet(needed)))

    def test_always_redundant_phrases_fail(self):
        for bad in ("Reviewed each and every invoice over $5,000.",
                    "Was able to cut dock time from 9 hours to 4.",
                    "The end result was a 12% lift in repeat orders.",
                    "Wrote the future plans for 2 plants.",
                    "Collaborated together with 3 vendors on the rollout.",
                    "Drew on past experience in retail to open 3 stores.",
                    "Completely eliminated a backlog of 400 tickets."):
            self.assertIn("redundant word", fail_names(as_bullet(bad)), bad)

    def test_sometimes_needed_words_are_a_second_read(self):
        for text in ("Personally closed 12 of the team's 40 deals.",
                     "Successfully appealed 11 of 14 claim denials.",
                     "Cut actual cost per case 8% across 3 plants.",
                     "Built a new warehouse to replace the 1970s site."):
            self.assertIn("redundant word", review_names(as_bullet(text)), text)
            self.assertNotIn("redundant word", fail_names(as_bullet(text)), text)
        ok = "Reported actual spend against budget for 12 cost centers."
        self.assertNotIn("redundant word", fail_names(as_bullet(ok)) + review_names(as_bullet(ok)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
