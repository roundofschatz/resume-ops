#!/usr/bin/env python3
"""detect_ats.py tests. Every employer domain here is invented."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixtures import SCRIPTS, run  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import detect_ats  # noqa: E402

FIELDS = {"ats", "confidence", "front_end", "form", "ai_grading", "note", "why", "host"}


def ats(url):
    return detect_ats.detect(url)


class VendorHosts(unittest.TestCase):
    def test_workday_hosts_only(self):
        for url in ("https://acme.wd1.myworkdayjobs.com/en-US/careers/job/Denver/X_R-1",
                    "https://acme.wd5.myworkdaysite.com/recruiting/acme/careers",
                    "acme.myworkdayjobs.com/careers"):
            r = ats(url)
            self.assertEqual((r["ats"], r["confidence"]), ("Workday", "confirmed"), url)
        # Workday's own marketing and docs sites are not an applicant system.
        for url in ("https://www.workday.com/en-us/products.html", "https://doc.workday.com/admin"):
            self.assertIsNone(ats(url)["ats"], url)

    def test_lever_needs_the_jobs_host(self):
        self.assertEqual(ats("https://jobs.lever.co/acme/abc")["ats"], "Lever")
        self.assertIsNone(ats("https://www.lever.co/pricing")["ats"])

    def test_vendor_hosts(self):
        cases = {
            "https://boards.greenhouse.io/acme/jobs/1": "Greenhouse",
            "https://jobs.ashbyhq.com/acme/xyz": "Ashby",
            "https://careers-acme.icims.com/jobs/1/login": "iCIMS",
            "https://acme.eightfold.ai/careers/job/123": "Eightfold",
            "https://ats.rippling.com/acme-careers/jobs/abc": "Rippling",
            "https://acme-media.breezy.hr/p/abc123-account-director": "Breezy",
            "https://www.paycomonline.net/v4/ats/web.php/jobs/ViewJobDetails?job=1": "Paycom",
            "https://www.paycomdfw.net/v4/ats/web.php/portal/ABC/jobs/1": "Paycom",
            "https://sjobs.brassring.com/TGnewUI/Search/Home/Home?partnerid=1&siteid=2": "BrassRing",
            "https://acme.typeform.com/to/abc": "Typeform",
            "https://recruiting.ultipro.com/ACM1000/JobBoard/abc": "UKG",
            "https://recruiting2.ultipro.com/ACM1000/JobBoard/abc": "UKG",
            "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=1": "ADP",
            "https://abc.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/X/job/1": "Oracle Recruiting",
            "https://acme.taleo.net/careersection/2/jobdetail.ftl?job=1": "Taleo",
            "https://jobs.dayforcehcm.com/en-US/acme/CANDIDATEPORTAL/jobs/1": "Dayforce",
            "https://career5.successfactors.com/career?company=acme": "SuccessFactors",
            "https://acme.bamboohr.com/careers/12": "BambooHR",
        }
        for url, name in cases.items():
            r = ats(url)
            self.assertEqual(r["ats"], name, url)
            self.assertEqual(set(r), FIELDS, url)

    def test_government_postings_are_named_and_stopped(self):
        for url in ("https://www.governmentjobs.com/careers/somecounty/jobs/1/analyst",
                    "https://somecity.attract.neogov.com/jobs/1"):
            r = ats(url)
            self.assertEqual(r["ats"], "NEOGOV", url)
            self.assertIn("government", r["note"].lower())
            self.assertIn("does not cover", r["note"])

    def test_typeform_is_not_an_applicant_system(self):
        self.assertIn("not an applicant tracking system", ats("https://acme.typeform.com/to/x")["note"])


class EmployerDomains(unittest.TestCase):
    """v1.6 read only the hostname, so every one of these was 'unrecognized'."""

    def test_query_parameters(self):
        for url, name in (("https://www.acmeco.com/job-openings/5226387007/?gh_jid=5226387007", "Greenhouse"),
                          ("https://acmeco.com/careers/?ashby_jid=22bba1d4", "Ashby"),
                          ("https://jobs.acmeco.com/jobs/99347?iis=JOB+SLOTS&iisn=Board", "iCIMS")):
            r = ats(url)
            self.assertEqual((r["ats"], r["confidence"]), (name, "inferred"), url)

    def test_jibe_is_a_front_end_on_icims(self):
        for url in ("https://careers.acmeco.com/careers-home/jobs/30187", "https://acmeinc.jibeapply.com/jobs/5706"):
            r = ats(url)
            self.assertEqual((r["ats"], r["front_end"], r["confidence"]), ("iCIMS", "Jibe", "inferred"), url)

    def test_eightfold_on_a_custom_domain(self):
        r = ats("https://apply.acmeco.com/careers?pid=563")
        self.assertEqual((r["ats"], r["confidence"]), ("Eightfold", "inferred"))

    def test_workday_requisition_number(self):
        r = ats("https://jobs.acmeco.com/jobs/R0074793-7")
        self.assertEqual((r["ats"], r["confidence"]), ("Workday", "inferred"))
        self.assertIn("inferred from the requisition number", r["note"])

    def test_front_ends_leave_the_system_unknown(self):
        for url, front in (("https://acmeco.jobs/denver-co/planner/EA86D551/job/", "DirectEmployers"),
                           ("https://careers.acmeco.com/job/remote/planner/43250/100190441088", "Radancy")):
            r = ats(url)
            self.assertIsNone(r["ats"], url)
            self.assertIn(front, r["front_end"], url)
            self.assertIn("check the apply link", r["note"], url)


class Output(unittest.TestCase):
    def test_job_boards_may_be_native_posts(self):
        """v1.6 called these aggregator copies. Both host native posts with their
        own screening."""
        li = ats("https://www.linkedin.com/jobs/view/123")
        self.assertIn("native", li["note"])
        self.assertIn("Hiring Assistant", li["ai_grading"])
        ind = ats("https://www.indeed.com/viewjob?jk=abc")
        self.assertIn("Smart Screening", ind["ai_grading"])
        for r in (li, ind):
            self.assertIn("employer's own posting", r["note"])

    def test_form_and_grading_facts(self):
        wd = ats("https://acme.wd1.myworkdayjobs.com/x")
        # v2.0.1: each Workday site handles Skills its own way (one suggested
        # 15 from the file on 2026-09-28; another left the box empty).
        self.assertNotIn("never fills skills", wd["form"])
        self.assertIn("Skills vary by employer", wd["form"])
        self.assertIn("skills", wd["note"])
        self.assertIn("HiredScore", wd["ai_grading"])
        self.assertIn("its own product", wd["ai_grading"])
        self.assertIn("Type each title exactly as held", wd["note"])
        ef = ats("https://acme.eightfold.ai/careers/job/1")
        self.assertIn("no work-history form", ef["form"])
        self.assertIn("0 to 5", ef["ai_grading"])
        self.assertIn("An admin turns it on", ats("https://jobs.ashbyhq.com/acme/1")["ai_grading"])
        # v2.1: facts corrected against the vendors' 2026 docs (sources.md)
        self.assertIn("Winston Match", ats("https://jobs.smartrecruiters.com/Acme/123")["ai_grading"])
        self.assertIn("Needs manual review", ats("https://boards.greenhouse.io/acme/jobs/1")["ai_grading"])
        self.assertIn("one job at a time", ats("https://workforcenow.adp.com/x")["ai_grading"])
        self.assertIn("Textkernel", ats("https://jobs.lever.co/acme/1")["form"])
        self.assertIn("opt out", ats("https://workforcenow.adp.com/x")["ai_grading"])

    def test_every_named_grading_line_carries_a_date_or_says_none(self):
        for name, text in detect_ats.AI_GRADING.items():
            self.assertTrue(re.search(r"\b20\d\d\b|None|No detail|undated|Not covered", text), name)

    def test_retired_claims_are_gone(self):
        src = (SCRIPTS / "detect_ats.py").read_text(encoding="utf-8")
        for stale in ("different file", "structured_profile", "structured profile", "before anything else"):
            self.assertNotIn(stale, src, stale)

    def test_plain_output(self):
        code, out = run("detect_ats.py", "https://acme.wd1.myworkdayjobs.com/x")
        self.assertEqual(code, 0)
        self.assertNotIn(chr(0x2014), out)
        code, out = run("detect_ats.py", "--json", "https://jobs.lever.co/acme/1")
        self.assertEqual(json.loads(out)["ats"], "Lever")

    def test_unknown_host_is_not_an_error(self):
        code, out = run("detect_ats.py", "https://careers.acmeco.com/openings/x")
        self.assertEqual(code, 4)
        self.assertIn("unrecognized", out)
        self.assertIn("apply link", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
