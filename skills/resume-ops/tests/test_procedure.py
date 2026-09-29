#!/usr/bin/env python3
"""The skill's main job is a tailored resume built from the candidate's
evidence (2.2.0). From the first package through 2.1.1, SKILL.md made a base
resume a prerequisite ("If the candidate has no base resume, build it first,
whatever they asked for") and built every tailored resume from it. These tests
fail if that order comes back."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import ROOT  # noqa: E402

# Wording that makes a base resume a step before a tailored one.
PREREQUISITE = (
    (r"\bbuild (?:it|one|the base(?: resume)?|a base(?: resume)?) first\b", "builds a base resume first"),
    (r"\bbase resume first\b", "puts the base resume first"),
    (r"\b(?:if|when)\b[^.\n]{0,60}\bno base resume\b", "stops on a missing base resume"),
    (r"\bbuilt from (?:the|a|their) base\b", "builds the tailored resume from the base"),
    (r"\bfrom the base resume\b", "starts from the base resume"),
    (r"\b(?:regardless of|whatever) (?:what )?(?:they|the candidate) asked for\b", "overrides the ask"),
    (r"\bload\b[^.\n]{0,80}\bbase resume\b", "loads a base resume"),
)

FILES = ("SKILL.md", "references/tailoring.md", "references/intake.md", "README.md")
REPO_README = ROOT.parent.parent / "README.md"


def text(name):
    return (ROOT / name).read_text(encoding="utf-8")


def section(md, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", md, re.M | re.S)
    return m.group(1) if m else ""


class NothingComesFirst(unittest.TestCase):
    def test_no_file_makes_a_base_resume_a_prerequisite(self):
        paths = [ROOT / f for f in FILES] + ([REPO_README] if REPO_README.exists() else [])
        for p in paths:
            body = p.read_text(encoding="utf-8")
            for pattern, what in PREREQUISITE:
                m = re.search(pattern, body, re.I)
                self.assertIsNone(m, f"{p.name} {what}: {m.group(0) if m else ''!r}")

    def test_the_tailored_procedure_comes_first_and_starts_from_evidence(self):
        skill = text("SKILL.md")
        procs = re.findall(r"^## Procedure: (.+)$", skill, re.M)
        self.assertEqual(procs[0], "tailored resume", procs)
        body = section(skill, "Procedure: tailored resume")
        self.assertIn("evidence", body.lower())
        self.assertIn("requirement_check.py", body)
        self.assertIn("--evidence", body)

    def test_the_base_resume_is_an_option(self):
        body = section(text("SKILL.md"), "Procedure: base resume")
        self.assertRegex(body, r"never a prerequisite")

    def test_level_set_names_the_evidence(self):
        skill = text("SKILL.md")
        self.assertIn("Mode: [Tailored resume | Base resume | Review only]", skill)
        self.assertRegex(skill, r"\nEvidence: \[")
        self.assertNotIn("Facts file: [", skill)

    def test_description_leads_with_one_posting(self):
        skill = text("SKILL.md")
        desc = re.search(r"^description: (.+)$", skill, re.M).group(1)
        self.assertRegex(desc[:160], r"one (?:job )?posting", desc[:160])
        self.assertLessEqual(len(desc), 1024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
