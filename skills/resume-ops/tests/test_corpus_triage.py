#!/usr/bin/env python3
"""corpus_triage.py: grading, roles, sections, contradictions, groups, names."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import SCRIPTS  # noqa: E402
sys.path.insert(0, str(SCRIPTS))
import corpus_triage as ct  # noqa: E402

EN = "\u2013"

# Two employers, the same kind of work at both. Written in the layout this
# skill builds: company line, then "Title | dates".
TWO_JOBS = f"""EXPERIENCE
Northgate Supply, Dayton, OH
Logistics Manager | Apr 2019 {EN} Present
- Cut dock-to-stock time on the inbound dock from 3 days to 1 across 2 warehouses.
- Rebuilt the inbound dock schedule for 90 associates, cutting overtime 22%.
Tri-County Freight, Xenia, OH
Dispatch Supervisor | Jun 2012 {EN} Mar 2019
- Rebuilt the inbound dock schedule for 40 drivers, cutting detention fees 31%.
- Cut dock-to-stock time from 4 days to 2 at the Xenia inbound dock.
"""


def employers(text):
    return sorted({c.employer for c in ct.atomize(text) if c.employer})


class Grading(unittest.TestCase):
    def test_percent_is_detected(self):
        """The trailing \\b sat after '%', where a word boundary can never hold,
        so every percentage bullet graded D."""
        self.assertTrue(ct.PERCENT.findall("Grew revenue 40% at Acme Corp."))
        self.assertTrue(ct.PERCENT.findall("Cut errors by 7.5%."))
        self.assertTrue(ct.PERCENT.findall("Grew revenue 40 percent."))

    def test_percent_bullet_grades_a(self):
        self.assertEqual(ct.Claim(1, 1, "Grew revenue 40% at Acme Corp.", "x").grade, "A")

    def test_before_after_reaches_grade_a_without_a_proper_noun(self):
        c = ct.Claim(1, 1, "cut unplanned downtime from 14 hours to 4 per week", "x")
        self.assertEqual(c.grade, "A")

    def test_counts_are_field_neutral(self):
        for phrase in ("90 associates across three shifts",
                       "32-bed unit averaging 210 admissions",
                       "maintained 22 CNC machines",
                       "handled 500 tickets a month",
                       "moved 1,400 pallets a week",
                       "precepted 11 nurses",
                       "220,000 sq ft distribution center"):
            self.assertTrue(ct.COUNT.findall(phrase), phrase)

    def test_a_bare_year_is_not_a_count(self):
        self.assertFalse(ct.COUNT.findall("in 2019 the team shipped"))
        self.assertTrue(ct.COUNT.findall("2,100 hours of overtime"))

    def test_acronyms_count_as_named_things(self):
        self.assertIn("WMS", ct.extract_entities("Led the WMS implementation for 40 users"))

    def test_comma_separated_skill_dump_is_a_list(self):
        self.assertTrue(ct.is_keyword_dump(
            "Acute care, triage, IV therapy, wound care, patient education, Epic, audit"))
        self.assertFalse(ct.is_keyword_dump(
            "Led the rollout, cut errors, and trained the team on the new procedure."))


class Roles(unittest.TestCase):
    def test_company_first_roles_give_two_employers(self):
        """v1.6 read the date line as the role and took "Apr" and "Jun" as the
        employers, so every target said one employer only."""
        self.assertEqual(employers(TWO_JOBS), ["Northgate Supply", "Tri-County Freight"])
        top = ct.targets(ct.atomize(TWO_JOBS), 3)[0]
        self.assertEqual(top["employers"], ["Northgate Supply", "Tri-County Freight"])
        self.assertIn("repeated across 2 employers", ct.report(ct.atomize(TWO_JOBS), TWO_JOBS, 3))

    def test_title_first_roles(self):
        text = (f"Logistics Manager\nNorthgate Supply, Dayton, OH | Apr 2019 {EN} Present\n"
                "- Cut dock-to-stock time from 3 days to 1 across 2 warehouses.\n"
                f"Dispatch Supervisor\nTri-County Freight, Xenia, OH | Jun 2012 {EN} Mar 2019\n"
                "- Cut detention fees 31% for 40 drivers.\n")
        self.assertEqual(employers(text), ["Northgate Supply", "Tri-County Freight"])

    def test_one_line_roles(self):
        text = ("Staff Accountant | Harbor & Lane, Portland, ME - Jan 2016 - Dec 2019\n"
                "- Closed the books in 4 days instead of 9 for 12 entities.\n"
                "Senior Accountant | Bayside Credit Union | Portland, ME | Jan 2020 - Present\n"
                "- Cut reconciliation errors 40% across 30 branch accounts.\n")
        self.assertEqual(employers(text), ["Bayside Credit Union", "Harbor & Lane"])

    def test_markdown_role_headings(self):
        text = (f"### Charge Nurse \u2014 Mercy General \u00b7 Leeds, UK \u00b7 Mar 2019 {EN} Present\n"
                "- Ran a 32-bed unit averaging 210 admissions a month.\n"
                "## Harbor Clinic\n"
                f"### Staff Nurse, Jun 2014 {EN} Feb 2019\n"
                "- Precepted 11 newly qualified nurses over three years.\n")
        self.assertEqual(employers(text), ["Harbor Clinic", "Mercy General"])

    def test_sub_heading_keeps_the_employer(self):
        text = (f"### Northgate Supply (Apr 2019 {EN} Present)\n"
                "#### Inbound dock rebuild\n"
                "Cut dock-to-stock time from 3 days to 1 across 2 warehouses.\n")
        (claim,) = ct.atomize(text)
        self.assertEqual(claim.employer, "Northgate Supply")
        self.assertEqual(claim.section, "Inbound dock rebuild")

    def test_employer_comes_from_the_employer_field(self):
        self.assertEqual(ct.employer_of("Charge Nurse | Royal Infirmary, Manchester"),
                         "Royal Infirmary")
        self.assertEqual(ct.employer_of("Director of Operations | Acme Corp, Denver, CO - 2019"),
                         "Acme Corp")
        self.assertEqual(ct.employer_of("no pipe here"), "")

    def test_employer_is_never_a_month(self):
        """X18: on "Company, City, ST | Mon YYYY - Mon YYYY" v1.6 returned "Mar"."""
        self.assertEqual(ct.employer_of(f"Brightline Tool, Toledo, OH | Mar 2018 {EN} Present"),
                         "Brightline Tool")
        self.assertEqual(ct.employer_of(f"Teacher | Lincoln Middle School | Tulsa, OK | Aug 2012 {EN} May 2018"),
                         "Lincoln Middle School")
        self.assertEqual(ct.employer_of(f"Maintenance Supervisor | Mar 2018 {EN} Present"), "")

    def test_two_roles_at_one_company_is_one_employer(self):
        self.assertEqual(ct.employer_of("Charge Nurse | Acme Health, Leeds"),
                         ct.employer_of("Staff Nurse | Acme Health, Leeds"))


class Sections(unittest.TestCase):
    def test_quoted_all_caps_inside_a_line_is_not_a_section(self):
        """v1.6 took these lines as section names."""
        for line in ('Title: "2024-25 STRATEGIC PLANNING."',
                     'Both binders marked "PROPERTY OF THE DISTRICT."',
                     '"ANNUAL REVIEW"',
                     "THE AUDIT FOUND NO EXCEPTIONS IN ANY OF THE TWELVE BRANCHES"):
            self.assertIsNone(ct.section_header(ct.clean(line)), line)
        for line in ("EXPERIENCE", "Key Accomplishments", "Education:"):
            self.assertTrue(ct.section_header(line), line)

    def test_a_quoted_line_does_not_reset_the_employer(self):
        text = TWO_JOBS.replace(
            "- Rebuilt the inbound dock schedule for 90",
            'Title: "2024-25 DOCK PLAN."\n- Rebuilt the inbound dock schedule for 90')
        claims = ct.atomize(text)
        c = next(c for c in claims if "90 associates" in c.text)
        self.assertEqual(c.employer, "Northgate Supply")

    def test_section_headers_are_not_swept_as_credentials(self):
        self.assertEqual(ct.credentials_and_recognitions("Awards\nCertifications\n"), [])

    def test_line_count_matches_the_file(self):
        """v1.6 counted one line more than wc -l on a file ending in a newline."""
        out = ct.report(ct.atomize(TWO_JOBS), TWO_JOBS, 3)
        self.assertIn(f"{len(TWO_JOBS.splitlines())} lines in", out)


class Report(unittest.TestCase):
    def test_no_invented_fit_figure(self):
        out = ct.report(ct.atomize(TWO_JOBS), TWO_JOBS, 3)
        self.assertNotIn("20 bullets", out)
        self.assertNotIn("more than fits", out)
        self.assertNotIn("200", out)
        self.assertIn("builder's call", out)

    def test_report_renders_with_no_groups(self):
        text = "Ran the audit.\nBuilt the form.\n"
        self.assertIn("No targets grouped", ct.report(ct.atomize(text), text, 5))

    def test_report_has_no_em_dash(self):
        out = ct.report(ct.atomize(TWO_JOBS), TWO_JOBS, 3)
        self.assertNotIn("\u2014", out)


class Voice(unittest.TestCase):
    def test_person_specific_markers_are_gone(self):
        for line in ("The engine behind the new intake process was a shared tracker.",
                     "The constant is a weekly review with each shift lead.",
                     "One philosophy guided the rollout across every ward."):
            self.assertFalse(ct.VOICE_MARKERS.search(line), line)

    def test_general_self_description_is_voice(self):
        for line in ("I believe every student can learn algebra.",
                     "My approach starts with the night shift.",
                     "I am passionate about clean books."):
            self.assertTrue(ct.Claim(1, 1, line, "x").is_voice, line)


class Names(unittest.TestCase):
    def names(self, *texts):
        claims = [ct.Claim(i, i, t, "x") for i, t in enumerate(texts, 1)]
        return [n for n, _c, _w in ct.coined_names(claims)]

    def test_no_lone_words_from_apostrophes(self):
        """v1.6 read "What's" and "Let's" as quoted names "What" and "Let"."""
        names = self.names('Gave the talk "What\'s Next for Rural Clinics?" to 200 nurses.',
                           "Let's build the new roster together, said the director.",
                           "Dana wrote the 'Kiln Reset' checklist for all 4 kilns.")
        for bad in ("What", "Let", "Dana", "Kiln"):
            self.assertNotIn(bad, names)
        self.assertIn("Kiln Reset", names)

    def test_leading_common_word_is_dropped(self):
        self.assertIn("Growth Ladder", self.names("The Growth Ladder set pay steps for 40 aides."))
        self.assertNotIn("The Growth Ladder", self.names("The Growth Ladder set pay steps."))

    def test_standard_credential_parens_are_not_coined_names(self):
        names = self.names("BSc (Hons) Nursing, University of Leeds",
                           "Advanced Life Support (ALS), 2018",
                           "Signed off by the unit lead (Priya) in March.")
        for bad in ("Hons", "ALS", "Priya"):
            self.assertNotIn(bad, names)

    def test_employer_names_are_not_internal_names(self):
        claims = [ct.Claim(1, 1, "Rebuilt routing at Keller Map Systems for 40 trucks.", "x")]
        self.assertIn("Keller Map Systems", [n for n, _c, _w in ct.coined_names(claims)])
        self.assertEqual(ct.coined_names(claims, skip=["Keller Map Systems"]), [])


class Contradictions(unittest.TestCase):
    def test_only_career_length_counts(self):
        """v1.6 counted every "N years", so a 5-year plan contradicted a career."""
        text = ("Nurse with 12 years in acute care.\n"
                "Wrote the 5-year staffing plan and a 20-year lease review.\n"
                "Over 3 years the unit cut falls 40%.\n"
                "Our team brings 35 years combined experience.\n")
        self.assertEqual(ct.global_conflicts(text), [])

    def test_two_career_lengths_are_a_contradiction(self):
        text = "Accountant with 12 years of experience.\nA 15-year career in audit.\n"
        (label, counts), = ct.global_conflicts(text)
        self.assertEqual(label, "Years of experience")
        self.assertEqual(counts, {12: 1, 15: 1})

    def test_years_near_a_career_word(self):
        self.assertEqual(ct.career_years("Spent 16 years in the logistics industry."), {16: 1})
        self.assertEqual(ct.career_years("Spent 16 years in the attic."), {})


class Groups(unittest.TestCase):
    def test_clusters_form_on_shared_domain_words(self):
        text = ("Ran a 32-bed medical-surgical unit averaging 210 admissions a month.\n"
                "Led the sepsis rollout on the medical-surgical unit, 54% to 91%.\n")
        self.assertTrue(ct.targets(ct.atomize(text), 3))

    def test_unit_words_do_not_form_a_target(self):
        for w in ("hours", "quarter", "budget", "team"):
            self.assertIn(w, ct.CLUSTER_STOP)
        self.assertNotIn("hours", ct.phrases("cut 700 hours of overtime"))

    def test_hyphenated_compounds_split(self):
        self.assertIn("dock", ct.phrases("built the cross-dock process"))

    def test_same_story_twice_is_grouped(self):
        claims = [ct.Claim(1, 1, "Rebuilt the Fairview Clinic intake with Harlow Health.", "a"),
                  ct.Claim(2, 2, "Cut Fairview Clinic wait times 30% for Harlow Health.", "b")]
        groups, oversized = ct.dup_clusters(claims)
        self.assertEqual([len(g["claims"]) for g in groups], [2])
        self.assertEqual(oversized, 0)

    def test_a_chain_of_claims_is_capped(self):
        """v1.6 chained 1,031 claims into one group through shared words."""
        tag = [a + b for a in "BCDFGHJKLM" for b in "aeiou"]     # Ba, Be, Bi ...
        claims = [ct.Claim(i, i, f"Worked with Site {tag[i]} and Site {tag[i + 1]} on the line.", "x")
                  for i in range(40)]
        groups, oversized = ct.dup_clusters(claims)
        self.assertEqual(oversized, 1)
        self.assertTrue(all(len(g["claims"]) <= ct.CLUSTER_CAP for g in groups))
        out = ct.report(claims, "\n".join(c.text for c in claims), 3)
        self.assertIn("had more than 25 claims", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
