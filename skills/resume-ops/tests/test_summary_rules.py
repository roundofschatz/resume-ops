#!/usr/bin/env python3
"""The summary rules and the serial comma, as the skill's own files state them
(2.5.0). The summary is a pitch: what the candidate does and for whom, the run
of work that matches the employer, and what they've built and led, up to about
110 words, voiced on a summary that worked. These tests fail if the old formula
(one result, a belief line, a 75-word cap) comes back, or if the skill's own
examples skip the serial comma."""
import re
import sys
import unittest

sys.path.insert(0, __import__("os").path.dirname(__file__))
from fixtures import ROOT, SCRIPTS  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import draft_review as dr  # noqa: E402

# The skill's own prose and examples. sources.md is left out: its quotes stay
# word for word, and the changelog keeps old entries as written.
FILES = ("SKILL.md", "README.md", "references/writing.md", "references/tailoring.md",
         "references/document.md", "references/intake.md", "references/readers.md",
         "templates/rulings.md", "templates/candidate-facts.md")

# Lines that show the comma missing on purpose, or that the check misreads.
ON_PURPOSE = ('"thanked the founders, Dana and Lee"', '"A, B and C"', '"In 2020, sales rose and costs fell"',
              "**A summary, short.** People and LLM graders",
              "evidence in any format, small and large")      # a file tree line that wraps


def text(name):
    return (ROOT / name).read_text(encoding="utf-8")


def summary_section():
    md = text("references/writing.md")
    return re.search(r"^## The summary\s*$(.*?)(?=^## )", md, re.M | re.S).group(1)


class SummaryRules(unittest.TestCase):
    def test_the_old_formula_is_gone(self):
        body = summary_section()
        for old in ("belief", "One sentence of belief", "No second role-level result",
                    "three to four lines", "50 to 70 words", "45 to 75"):
            self.assertNotIn(old, body, old)
        for name in FILES:
            self.assertNotRegex(text(name), r"(?i)belief sentence|proof sentence", name)

    def test_the_new_rules_are_stated(self):
        body = summary_section()
        for needed in ("110 words", "seven rendered lines", "Results belong in the bullets",
                       "voice model", "got an interview", "Never \"I\"", "has a job behind it",
                       "The years count the whole career"):
            self.assertIn(needed, body, needed)
        self.assertIn("45 to 110 words", body)

    def test_the_length_agrees_everywhere(self):
        self.assertEqual(dr.SUMMARY_WORDS, (45, 110))
        self.assertIn("up to about 110 words or seven rendered lines", text("references/document.md"))
        self.assertIn("the summary within seven lines", text("SKILL.md"))
        self.assertNotIn("summary within four lines", text("SKILL.md"))

    def test_the_skill_asks_for_a_summary_that_worked(self):
        ask = re.search(r"\*\*Ask\*\*(.*?)\*\*Decide yourself", text("SKILL.md"), re.S).group(1)
        self.assertIn("A summary that worked", ask)

    def test_the_examples_are_pitches_within_the_limit(self):
        examples = re.findall(r"^> (.+)$", summary_section(), re.M)
        self.assertGreaterEqual(len(examples), 3)
        for ex in examples:
            self.assertLessEqual(len(ex.split()), 110, ex)
            self.assertFalse(dr.first_person(ex), ex)
            fails = [h for h in dr.tell_hits(ex) if h[0] == dr.FAIL]
            self.assertFalse(fails, (ex, fails))


class SerialCommaInTheSkill(unittest.TestCase):
    def test_the_rule_is_in_writing_md(self):
        md = text("references/writing.md")
        self.assertIn("## The serial comma", md)
        self.assertIn('"strategists, designers, and interns"', md)

    def test_the_skills_own_lists_use_it(self):
        misses = []
        for name in FILES:
            for n, line in enumerate(text(name).splitlines(), 1):
                if any(p in line for p in ON_PURPOSE):
                    continue
                for lv, a, b in dr.serial_hits(line):
                    if lv == dr.FAIL:
                        misses.append(f"{name}:{n}: ...{line[max(0, a - 30):b]}")
        self.assertFalse(misses, "\n".join(misses))


if __name__ == "__main__":
    unittest.main(verbosity=2)
