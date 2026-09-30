#!/usr/bin/env python3
"""
detect_ats.py: name the applicant tracking system behind a job posting URL.

The URL often says which system takes the application before anything is
fetched: the host, a path, or a query parameter the vendor adds. The resume
stays one file whatever the answer. What changes is what to check after the
upload, and whether an AI grading product may read the file.

Confidence:
  confirmed  the URL is on a host the vendor runs: its own, or a site it runs
             under a partner's name, checked live (sources.md, L06)
  inferred   a parameter, path or requisition number on the employer's own
             site points to the vendor
  unknown    no rule matches. A vendor's name in the host is reported as a
             lead, never a verdict: rippling-ats.com says Rippling and runs on
             HiringThing (L06).

A front end (Jibe, Radancy, a DirectEmployers .jobs site) is a career-site
layer, not the system behind it. When one is found, the apply link names the
real system.

Stdlib only.

Usage:
    python detect_ats.py https://acme.wd1.myworkdayjobs.com/careers/job/...
    python detect_ats.py --json <url>

Exit codes: 0 when a system is named, 4 when it is not. 4 is not an error:
check the apply link on the page.
"""

import argparse
import json
import re
import sys
from urllib.parse import parse_qs, urlparse

# What each vendor documents about grading. Dates are the vendor documents'
# own dates. Whether an employer has turned a feature on is not visible from
# outside. Source IDs point to references/sources.md.
AI_GRADING = {
    "Workday": "HiredScore grades A to D against the posting's required and preferred "
               "qualifications; a B needs every required one. Sold as its own product "
               "(HiredScore docs 2023-06-23; release notes updated 2025-08-22). Workday's "
               "own Candidate Skills Match score exists where set up; Workday plans to "
               "retire it (doc updated 2026-03-13).",      # [S05, S06, S07]
    "Eightfold": "Match score from 0 to 5 from job titles, work history, education, "
                 "skills and resume text; recent skills weigh more (Eightfold, 2025).",  # [S10, S11]
    "Greenhouse": "Talent Matching labels applicants Strong, Good, Partial or Limited match, "
                  "from skills, titles, dates, companies and years it extracts. Part of the "
                  "Real Talent add-on. Applicants who opt out show \"Needs manual review\" "
                  "and are not scored (Greenhouse support, updated 2026-09-09 and "
                  "2026-02-02).",                       # [S15, S16, S17, S18]
    "Lever": "Talent Fit ranks applicants against the job. Built in on current plans and "
             "turned on per account and per job (Lever pricing and Employ Academy, "
             "undated; ranking per Lever, 2025-06-26).",  # [S21, S22, S23]
    "Ashby": "AI-assisted application review marks each employer criterion met, not met "
             "or undecided, and can sort by the share met. An admin turns it on; "
             "candidates can opt out (Ashby docs; launched 2024-09-10).",  # [S25, S26]
    "Oracle Recruiting": "AI matching ratings, 0 to 5, for education, experience, skills "
                         "and profile. Opt-in for the employer (Oracle, 2026-09-03).",  # [S27]
    "Taleo": "Prescreening groups applicants by their answers to required and asset "
             "questions. A disqualifying answer can end the application (Oracle Taleo "
             "21B, 2021).",                             # [S28]
    "ADP": "Profile Relevance: excellent, good, fair or low match from experience, role "
           "history and skills. Applicants can opt out one job at a time; the score then "
           "shows Not Available (ADP FAQ, 2026-07-09).",  # [S29]
    "Breezy": "Candidate Match Score, 0 to 10. A legacy paid feature, only for existing "
              "subscribers (Breezy, 2025-09-04).",       # [S35]
    "SuccessFactors": "AI-assisted skills matching. A paid add-on that needs an SAP AI "
                      "Unit license (SAP Learning, undated). SAP also sells SmartRecruiters "
                      "for SAP SuccessFactors (2026-03-04).",  # [S39, S40]
    "SmartRecruiters": "Winston Match rates applicants very high, high, medium or low from "
                       "skills, experience, education and title. SAP-owned; sold with "
                       "SuccessFactors since 2026-03 (SmartRecruiters, modified 2026-03-30).",  # [S40, S41]
    "iCIMS": "iCIMS says its AI can \"Rank candidates based on skills and experience\" "
             "(iCIMS, 2026-09-21). Whether it is on by default is unknown.",  # [S34]
    "UKG": "UKG's solution guide names AI-based ranking. No detail found.",  # [S36]
    "Rippling": "Rippling Recruiting's Application Review screens applicants against "
                "criteria the employer defines and surfaces the top candidates. Admins turn "
                "Rippling's AI features on or off; the default is not stated (Rippling, "
                "undated and 2025-12-31).",               # [S37, S109, S110]
    "HiringThing": "AI Candidate Ranking scores every applicant against the job description "
                   "and ranks a shortlist; the hiring team can adjust the criteria and their "
                   "weights. Available to all partners and their clients since 2026-06-15. "
                   "Account admins can turn the AI features off (HiringThing, 2026-06-15; "
                   "blog undated).",                     # [S106, S107]
    "Paycom": "None found. Paycom sends knockout messages when answers miss the "
              "employer's requirements.",               # [S32]
    "BambooHR": "None found.",                           # [S42]
    "LinkedIn": "Hiring Assistant evaluates applicants against the hiring criteria, "
                "including applicants who came through the employer's own system. An "
                "add-on to LinkedIn Recruiter (LinkedIn, read 2026-09-28).",  # [S30, S31]
    "Indeed": "Smart Screening scores applications against the employer's criteria "
              "(Indeed, undated).",                     # [S38]
    "Typeform": "None. A person reads what you send.",  # the skill's judgment
    "NEOGOV": "Not covered here.",
}

# What the application form fills from the uploaded file, where known.
FORM = {
    "Workday": "The upload fills contact details, work history and education, and "
               "sometimes languages. Skills vary by employer: some sites leave the box "
               "empty for you to fill, some suggest skills from the file. "
               "Check the Skills box every time and remove anything wrong.",  # [S02, L01, L02]
    "Eightfold": "In a live test on 2026-09-28 the application showed no work-history "
                 "form. The file is the application. Some Eightfold employers now take "
                 "the application as a chat that reads the resume (Eightfold, "
                 "2026-07-15).",                        # [L03, S13]
    "Greenhouse": "Parses resumes a recruiter imports. The application form is the "
                  "employer's choice; on the one live form tested (2026-09-28) there were "
                  "no work-history fields.",            # [S14, L04]
    "Lever": "Parses companies, education and titles into searchable fields; its parser "
             "is Textkernel. In a live test (2026-09-28) it refused a bare six-part DOCX "
             "and parsed the same text saved as a complete Word file.",  # [S24, S88, L04]
    "Paycom": "Parses the file to pre-fill the form.",   # [S32]
    "Rippling": "Rippling Recruiting fills candidate information from an uploaded resume, "
                "in English and other languages (Rippling, 2025-04-30). Which fields is not "
                "stated. Check what the form filled after the upload.",  # [S108]
    "HiringThing": "Parses the resume into the recruiter's view of the applicant. No "
                   "HiringThing page says the application form fills from it (read "
                   "2026-09-30). Check what the form filled after the upload.",  # [S102, S105]
    "Typeform": "No parsing. The form is what you type.",
}

NOTE = {
    "Workday": "Check every parsed field after the upload: titles, companies, dates, "
               "languages, skills and websites. Type each title exactly as held. "
               "Screening questions can end the application "
               "where the employer set them up.",          # [S08, L01]
    "Eightfold": "Eightfold often sits on top of another system. The score reads the "
                 "whole file, so the proof for each requirement has to be in the jobs.",  # [S12, S10]
    "Jibe": "Jibe is iCIMS's career-site front end.",   # [S33]
    "NEOGOV": "A government posting. This skill does not cover government formats "
              "(federal and state applications have their own rules). Stop here.",
    "Typeform": "A form builder, not an applicant tracking system.",
    "LinkedIn": "May be a native LinkedIn post with its own screening, or a copy of the "
                "employer's posting. Find the employer's own posting and apply there if "
                "it exists.",
    "Indeed": "May be a direct employer post with Indeed's own screening, or a copy. "
              "Find the employer's own posting and apply there if it exists.",
    "HiringThing": "HiringThing runs job sites under partners' names and web addresses. "
                   "Check what the form filled after the upload. Screening questions can end "
                   "the application where the employer set them up.",  # [S102]
    "front end": "A front end. The applicant system behind it is unknown: check the "
                 "apply link.",
    None: "Nothing in the URL names the system. Check the apply link on the page.",
}

# (ats, host pattern, confidence, front end[, why]). First match wins.
HOSTS = [
    ("Workday", r"(?:^|\.)(?:myworkdayjobs|myworkdaysite)\.com$", "confirmed", None),
    ("iCIMS", r"(?:^|\.)icims\.com$", "confirmed", None),
    ("iCIMS", r"(?:^|\.)jibeapply\.com$", "inferred", "Jibe"),
    ("Greenhouse", r"(?:^|\.)greenhouse\.io$", "confirmed", None),
    ("Lever", r"^jobs\.(?:eu\.)?lever\.co$", "confirmed", None),
    ("Ashby", r"(?:^|\.)ashbyhq\.com$", "confirmed", None),
    ("Eightfold", r"(?:^|\.)eightfold(?:-eu|-gov)?\.ai$", "confirmed", None),   # [L06]
    ("Rippling", r"^ats\.rippling\.com$", "confirmed", None),
    # HiringThing's own hosts, and sites it runs under a partner's name.
    # [S102, S104]. rippling-ats.com is Rippling ATS: HiringThing's system, sold
    # by its partners under that name [S103], every board "Powered by
    # HiringThing" [L06]. It is not Rippling Recruiting (ats.rippling.com).
    ("HiringThing", r"(?:^|\.)(?:hiringthing|applicant-tracking|rippling-ats|prismhr-hire)\.com$",
     "confirmed", None),
    ("Breezy", r"(?:^|\.)breezy\.hr$", "confirmed", None),
    ("Paycom", r"(?:^|\.)paycomonline\.(?:net|com)$", "confirmed", None),
    ("Paycom", r"(?:^|\.)paycomdfw\.net$", "inferred", None),
    ("BrassRing", r"(?:^|\.)brassring\.com$", "confirmed", None),
    ("NEOGOV", r"(?:^|\.)governmentjobs\.com$|(?:^|\.)neogov\.com$|(?:^|\.)schooljobs\.com$",
     "confirmed", None),                                               # [S111]
    ("Typeform", r"(?:^|\.)typeform\.com$", "confirmed", None),
    ("UKG", r"^recruiting\d*\.ultipro\.com$|(?:^|\.)ultipro\.com$", "confirmed", None),
    ("ADP", r"^workforcenow\.adp\.com$|^myjobs\.adp\.com$", "confirmed", None),
    ("Taleo", r"(?:^|\.)taleo\.net$", "confirmed", None),
    ("Dayforce", r"(?:^|\.)dayforcehcm\.com$", "confirmed", None),
    ("SuccessFactors", r"(?:^|\.)successfactors\.(?:com|eu)$", "confirmed", None),
    ("SmartRecruiters", r"(?:^|\.)smartrecruiters\.com$", "confirmed", None),
    ("SmartRecruiters", r"^jobs\.sap\.com$", "inferred", None,
     "SAP's own career site, whose Apply links go to SmartRecruiters"),  # [L06]
    ("Workable", r"(?:^|\.)workable\.com$", "confirmed", None),
    ("BambooHR", r"(?:^|\.)bamboohr\.(?:com|co\.uk)$", "confirmed", None),
    ("Jobvite", r"(?:^|\.)jobvite\.com$", "confirmed", None),
    ("Paylocity", r"^recruiting\.paylocity\.com$", "confirmed", None),
    ("LinkedIn", r"(?:^|\.)linkedin\.com$", "confirmed", None),
    ("Indeed", r"(?:^|\.)indeed\.com$", "confirmed", None),
]
ORACLE_HOST = re.compile(r"(?:^|\.)oraclecloud\.com$")

# A partner's name on a HiringThing host, and what to know about it [S103, L06].
SOLD_AS = {
    "rippling-ats.com": ("Rippling ATS",
                         "Rippling ATS runs on HiringThing. It is a different product from "
                         "Rippling Recruiting (ats.rippling.com), so Rippling's own facts don't "
                         "apply."),
}

# Vendor names as they appear inside host names. An unmatched host that holds
# one gets a pointer, never a verdict: the name can belong to a product the
# vendor sells through someone else (L06). term_coverage.py reads this list too.
VENDOR_WORDS = {
    "workday": "Workday", "myworkdayjobs": "Workday", "myworkdaysite": "Workday",
    "icims": "iCIMS", "greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby",
    "ashbyhq": "Ashby", "eightfold": "Eightfold", "rippling": "Rippling",
    "hiringthing": "HiringThing", "breezy": "Breezy", "paycom": "Paycom",
    "paycomonline": "Paycom", "paycomdfw": "Paycom", "brassring": "BrassRing",
    "neogov": "NEOGOV", "typeform": "Typeform", "ukg": "UKG", "ultipro": "UKG",
    "adp": "ADP", "taleo": "Taleo", "dayforce": "Dayforce", "dayforcehcm": "Dayforce",
    "successfactors": "SuccessFactors", "smartrecruiters": "SmartRecruiters",
    "workable": "Workable", "bamboohr": "BambooHR", "jobvite": "Jobvite",
    "paylocity": "Paylocity", "oraclecloud": "Oracle Recruiting", "linkedin": "LinkedIn",
    "indeed": "Indeed", "jazzhr": "JazzHR", "recruitee": "Recruitee",
    "teamtailor": "Teamtailor", "pinpointhq": "Pinpoint", "glassdoor": "Glassdoor",
    "ziprecruiter": "ZipRecruiter",
}


def vendor_words(host):
    """Vendor names found as whole words in a host: "acme.rippling-ats.com"
    gives ["Rippling"]. Words split on dots, hyphens and digits, so "cleveland"
    never reads as Lever."""
    out = []
    for w in re.split(r"[._\-\d]+", (host or "").lower()):
        name = VENDOR_WORDS.get(w)
        if name and name not in out:
            out.append(name)
    return out


GENERIC_NOTE = ("Check what the form filled after the upload. Screening questions can end "
                "the application where the employer set them up.")


def result(ats, confidence, host, front_end=None, why=""):
    if ats:
        note = NOTE.get(ats, GENERIC_NOTE)
        if front_end and front_end in NOTE:
            note = f"{NOTE[front_end]} {note}"
    elif front_end:
        note = NOTE["front end"]
    else:
        note = NOTE[None]
    return {
        "ats": ats,
        "confidence": confidence,
        "front_end": front_end,
        "form": FORM.get(ats, "Unknown. Check what the form filled after the upload."
                         if ats else "Unknown."),
        "ai_grading": AI_GRADING.get(ats, "Not checked." if ats else "Unknown."),
        "note": note,
        "why": why,
        "host": host,
    }


def detect(url):
    u = urlparse(url if "//" in url else "//" + url)
    host = (u.hostname or "").lower()
    path = u.path or ""
    query = {k.lower(): v for k, v in parse_qs(u.query).items()}
    frag = (u.fragment or "").lower()

    for ats, pat, conf, front, *why in HOSTS:
        if re.search(pat, host):
            r = result(ats, conf, host, front, why[0] if why else
                       ("the vendor's own host" if conf == "confirmed" else "a host the vendor runs"))
            for domain, (name, note) in SOLD_AS.items():
                if host == domain or host.endswith("." + domain):
                    r["why"] = f"a HiringThing host, sold as {name}"
                    r["note"] = f"{note} {GENERIC_NOTE}"
            return r
    if ORACLE_HOST.search(host) and "/hcmui/candidateexperience" in path.lower():
        return result("Oracle Recruiting", "confirmed", host, None, "the vendor's own host")

    # the employer's own site: parameters and paths the vendors add
    if "gh_jid" in query:                     # [S19]
        return result("Greenhouse", "inferred", host, None, "the gh_jid parameter Greenhouse adds")
    if "ashby_jid" in query:
        return result("Ashby", "inferred", host, None, "the ashby_jid parameter Ashby adds")
    if "/careers-home/" in path.lower():
        return result("iCIMS", "inferred", host, "Jibe", "the /careers-home/ path of a Jibe site")
    if "iis" in query or "iisn" in query:
        return result("iCIMS", "inferred", host, None, "the iis source parameter iCIMS adds")
    if re.search(r"/v4/ats/", path, re.I):
        return result("Paycom", "inferred", host, None, "Paycom's /v4/ats/ path")
    if re.search(r"/careers/?(?:apply)?$", path) and "pid" in query:
        return result("Eightfold", "inferred", host, None, "the /careers?pid= path Eightfold uses")
    if re.search(r"/hcmUI/CandidateExperience", path, re.I):
        return result("Oracle Recruiting", "inferred", host, None, "Oracle's candidate path")
    if re.search(r"(?:^|[/_=-])R-?0\d{5,7}(?:[-_]\d+)?(?:$|[/?#])", path) \
            or re.search(r"(?:^|[/_=-])R-?0\d{5,7}\b", frag):
        r = result("Workday", "inferred", host, None,
                   "a Workday-style requisition number")
        r["note"] = ("Likely Workday (inferred from the requisition number). "
                     "Confirm on the apply link. " + NOTE["Workday"])
        return r

    # front ends: the system behind them is not in the URL
    if host.endswith(".jobs"):
        return result(None, "unknown", host, "DirectEmployers (.jobs site)", "a .jobs domain")
    if re.search(r"/job/[^/]+/[^/]+/\d+/\d+/?$", path):
        return result(None, "unknown", host, "Radancy TalentBrew", "Radancy's /job/<place>/<title>/<id>/<id> path")

    # a vendor's name in the host, with no rule for the host: a lead, not a verdict
    named = vendor_words(host)
    if named:
        r = result(None, "unknown", host, None, f"the host names {named[0]}; no rule here matches it")
        r["note"] = (f"The host names {named[0]}, but no rule here matches this host, so the "
                     "system behind it isn't confirmed. Check the page footer (\"Powered by\") "
                     "or the apply link.")
        return r
    return result(None, "unknown", host, None, "")


def main():
    ap = argparse.ArgumentParser(description="Name the applicant system behind a posting URL.")
    ap.add_argument("url")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    r = detect(args.url)
    if args.json:
        print(json.dumps(r, indent=2))
        return 0 if r["ats"] else 4

    name = r["ats"] or "unrecognized"
    print(f"ATS: {name}   ({r['confidence']}; {r['host']})")
    if r["why"]:
        print(f"  From:       {r['why']}")
    if r["front_end"]:
        print(f"  Front end:  {r['front_end']}")
    print(f"  Form:       {r['form']}")
    print(f"  AI grading: {r['ai_grading']}")
    print(f"  Note:       {r['note']}")
    return 0 if r["ats"] else 4


if __name__ == "__main__":
    sys.exit(main())
