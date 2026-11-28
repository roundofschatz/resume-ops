#!/usr/bin/env python3
"""The half that argues the case (2.7.0). Before 2.7.0 every rule could only
take away: the hard rules stopped invented facts and the checks caught faults,
and nothing pushed a true claim to its full size. A session could follow every
rule and hand back a resume that was accurate and small. These tests fail if
the push comes back without its guard, or the guard without the push."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import ROOT  # noqa: E402


def text(name):
    return (ROOT / name).read_text(encoding="utf-8")


def section(md, heading, level="##"):
    m = re.search(rf"^{level} {re.escape(heading)}\s*$(.*?)(?=^{level} |\Z)", md, re.M | re.S)
    return m.group(1) if m else ""


class LargestTrueSize(unittest.TestCase):
    def test_the_size_rule_and_its_two_checks_sit_together(self):
        md = text("references/writing.md")
        heads = re.findall(r"^## (.+)$", md, re.M)
        i = heads.index("The largest true size")
        self.assertEqual(heads[i - 1], "Numbers")
        self.assertEqual(heads[i + 1], "When the client can't be named")
        body = section(md, "The largest true size")
        for needed in ("who the work served", "how far it reached", "what changed",
                       "never a stronger word", "**The next question.**", "**The reference.**",
                       "keeps the split", "claim the layer you worked at",
                       "never on a guess", "Never compute a share"):
            self.assertIn(needed, body, needed)
        for rid in ("S149", "S117", "S81", "S83"):
            self.assertIn(rid, body, rid)

    def test_the_hard_rule_against_invention_stands(self):
        self.assertIn("**Never invent a number, title, date, employer, client, city, or credential.**",
                      text("SKILL.md"))

    def test_the_write_step_points_at_it(self):
        body = section(text("SKILL.md"), "Procedure: tailored resume")
        self.assertIn("each claim at its largest true size", body)


class MakeTheCase(unittest.TestCase):
    def test_the_tailored_procedure_ranks_before_it_maps(self):
        body = section(text("SKILL.md"), "Procedure: tailored resume")
        steps = re.findall(r"^(\d)\. \*\*(.+?)\*\*", body, re.M)
        names = [s for _n, s in steps]
        self.assertEqual([n for n, _s in steps], [str(i) for i in range(1, len(steps) + 1)])
        case = next(i for i, s in enumerate(names) if s.startswith("Make the case"))
        mapping = next(i for i, s in enumerate(names) if s.startswith("Map the evidence"))
        write = next(i for i, s in enumerate(names) if s.startswith("Write the JSON"))
        self.assertLess(case, mapping)
        self.assertLess(mapping, write)
        self.assertIn("It never supplies the sentences", body)

    def test_the_base_procedure_ranks_the_must_proves(self):
        body = section(text("SKILL.md"), "Procedure: base resume")
        self.assertIn("Rank them by how many postings require them", body)
        self.assertIn("never the sentences", body)
        base = section(text("references/tailoring.md"), "The base resume: a requirement map for a title family")
        self.assertIn("Rank the must-proves by how many postings require them", base)
        self.assertIn("never from a template filled with the candidate's facts", base)
        self.assertNotIn("word cap", base)


class SearchTheWholeCareer(unittest.TestCase):
    def test_a_gap_waits_for_a_whole_career_search(self):
        for name in ("SKILL.md", "references/tailoring.md"):
            body = text(name)
            self.assertIn("then a search of the whole career for the same kind of work in other jobs", body, name)
            self.assertIn("A pattern counts only with the entries behind it named", body, name)
            self.assertIn("nothing in the evidence, read across the whole career, shows it", body, name)

    def test_years_in_a_field_name_their_roles(self):
        body = text("references/tailoring.md")
        self.assertIn("or a related field", body)
        self.assertIn("list the roles that make up the count", body)


class BlindReview(unittest.TestCase):
    def test_claimed_without_proof_means_write_it(self):
        body = section(text("SKILL.md"), "Deliver")
        self.assertIn("claimed without proof gets its proof written onto the page", body)
        self.assertIn("ask the candidate only when it doesn't", body)
        self.assertIn("One read is one sample", body)
        self.assertIn("never write past the evidence", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
