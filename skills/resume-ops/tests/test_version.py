#!/usr/bin/env python3
"""One version everywhere: SKILL.md's metadata, the Level Set line, the top of
CHANGELOG.md and, when the skill sits inside the plugin, .claude-plugin/plugin.json.
A plugin label that lags the skill leaves installed copies on the old version."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import ROOT  # noqa: E402

PLUGIN_JSON = ROOT.parent.parent / ".claude-plugin" / "plugin.json"


def skill_versions():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    meta = re.search(r'^\s*version:\s*"?([0-9][0-9.]*)"?\s*$', skill, re.M).group(1)
    level = re.search(r"LEVEL SET: Resume Ops v([0-9][0-9.]*)", skill).group(1)
    log = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    top = re.search(r"^## ([0-9][0-9.]*) ", log, re.M).group(1)
    return {"SKILL.md metadata": meta, "Level Set line": level, "CHANGELOG.md top entry": top}


class Version(unittest.TestCase):
    def test_skill_agrees_with_itself(self):
        v = skill_versions()
        self.assertEqual(len(set(v.values())), 1, v)

    def test_plugin_label_matches_the_skill(self):
        if not PLUGIN_JSON.exists():
            self.skipTest("not inside the plugin (uploaded as a bare skill)")
        v = skill_versions()
        plugin = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
        self.assertEqual(plugin, v["SKILL.md metadata"],
                         f"plugin.json says {plugin}, the skill says {v}")


if __name__ == "__main__":
    unittest.main()
