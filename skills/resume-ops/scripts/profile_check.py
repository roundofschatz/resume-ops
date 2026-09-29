#!/usr/bin/env python3
"""
profile_check.py: compare the resume's jobs with the candidate's LinkedIn jobs.

Background checks verify titles and dates against the employer's record
[S81, S83], Lever flags work-history consistency [S86], and LinkedIn lets
colleagues vouch for work history [S87]. The resume and the profile should tell
the same story. This script needs no browser: it reads the jobs file from
LinkedIn's own data download (Positions.csv in current exports), or any CSV with
company, title, start and end columns, and lines it up with the resume.

  FAIL    the same job has different dates in the two places. Fix one.
  REVIEW  a title reads differently (a reorder, added words, or other words),
          or a job is in one place only. Often fine; the candidate decides.

A title the resume reorders for Workday, or a descriptor the candidate added,
is not wrong. The form's title field and any background-check form get the
title exactly as held (references/readers.md, The record check).

Stdlib only.

Usage:
    python profile_check.py resume.json Positions.csv
    python profile_check.py resume.docx Positions.csv

Exit codes: 0 no FAIL, 1 a date conflict, 2 the resume's jobs could not be read
(run it on the JSON source).
"""

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draft_review  # noqa: E402

MONTHS = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
SUFFIXES = {"inc", "llc", "ltd", "co", "corp", "corporation", "company", "plc", "lp", "llp"}
TITLE_STOP = {"of", "and", "the", "for", "a", "an"}
PRESENT = {"", "present", "current", "now"}


# ---------------------------------------------------------------- reading --

def month_year(value):
    """(year, month) from 'Mar 2021', 'March 2021', '2021-03', '03/2021' or
    '2021' (month None). None for present or blank."""
    v = (value or "").strip().lower().rstrip(".")
    if v in PRESENT:
        return None
    m = re.match(r"^([a-z]{3})[a-z]*\.?\s+(\d{4})$", v)
    if m and m.group(1) in MONTHS:
        return int(m.group(2)), MONTHS[m.group(1)]
    m = re.match(r"^(\d{4})-(\d{1,2})(?:-\d{1,2})?$", v)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d{1,2})/(\d{4})$", v)
    if m:
        return int(m.group(2)), int(m.group(1))
    m = re.match(r"^(\d{4})$", v)
    if m:
        return int(m.group(1)), None
    return "?"


def show(d):
    if d is None:
        return "Present"
    if d == "?":
        return "unreadable"
    y, m = d
    return f"{list(MONTHS)[m - 1].title()} {y}" if m else str(y)


def _col(header, *names):
    for i, h in enumerate(header):
        h = h.strip().lower()
        if any(n in h for n in names):
            return i
    return None


def read_profile(path):
    """[{company, title, start, end}] from a CSV. The header row is the first
    row with both a company and a title column; rows above it are skipped."""
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        sys.exit(f"Cannot read {path}: {e}")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")    # a CSV re-saved from Excel
    rows = list(csv.reader(text.splitlines()))
    for i, row in enumerate(rows):
        c, t = _col(row, "company", "employer", "organization"), _col(row, "title", "position")
        if c is not None and t is not None and c != t:
            s = _col(row, "start", "from", "began")
            e = _col(row, "finish", "end", "to ", "until")
            out = []
            for r in rows[i + 1:]:
                if len(r) <= max(c, t) or not (r[c].strip() or r[t].strip()):
                    continue

                def cell(j):
                    return r[j].strip() if j is not None and j < len(r) else ""
                out.append({"company": cell(c), "title": cell(t),
                            "start": month_year(cell(s)), "end": month_year(cell(e))})
            return out
    sys.exit(f"{path}: no header row with a company column and a title column.")


def read_resume(path):
    """[{company, title, start, end}] and the earlier-career text."""
    blocks = draft_review.load(path)
    roles, earlier = [], []
    for b in draft_review.structure(blocks):
        if b.kind == "role" and b.role:
            r = b.role
            roles.append({"company": r.get("company", ""), "title": r.get("title", ""),
                          "start": month_year(r.get("start", "")),
                          "end": month_year(r.get("end", ""))})
        elif b.kind == "para" and b.text.lower().startswith("earlier career"):
            earlier.append(b.text)
    return roles, " ".join(earlier)


# -------------------------------------------------------------- comparing --

def words(text):
    return re.findall(r"[a-z0-9+#]+", draft_review.plain(text).lower().replace("&", " and "))


def company_key(name):
    return [w for w in words(name) if w not in SUFFIXES]


def same_company(a, b):
    ka, kb = company_key(a), company_key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    small, big = sorted((ka, kb), key=len)
    return len(small) >= 2 and set(small) <= set(big)   # "Maumee" is not "Maumee Molding"


def title_verdict(resume_title, profile_title):
    """(level, note). Same words in the same order is a match."""
    r = [w for w in words(resume_title) if w not in TITLE_STOP]
    p = [w for w in words(profile_title) if w not in TITLE_STOP]
    if r == p:
        return "OK", "same"
    if sorted(r) == sorted(p):
        return "REVIEW", "same words, different order"
    added = [w for w in r if w not in p]
    dropped = [w for w in p if w not in r]
    if not dropped and added:
        return "REVIEW", "the resume adds: " + " ".join(added)
    if not added and dropped:
        return "REVIEW", "the resume leaves out: " + " ".join(dropped)
    return "REVIEW", "different words"


def date_gap(a, b):
    """Months between two (year, month) dates; year-only dates compare by year."""
    if a is None or b is None or a == "?" or b == "?":
        return 0 if a == b else None
    if a[1] is None or b[1] is None:
        return abs(a[0] - b[0]) * 12
    return abs((a[0] - b[0]) * 12 + (a[1] - b[1]))


def pair(roles, profile):
    """Pair resume roles with profile jobs at the same company, best pairs first:
    same title words before different ones, then the closest start date. Each
    job is used once, so a promotion missing from one side stays unpaired
    instead of stealing its neighbor's match."""
    options = []
    for ri, r in enumerate(roles):
        for pi, p in enumerate(profile):
            if not same_company(r["company"], p["company"]):
                continue
            same_words = sorted(words(r["title"])) == sorted(words(p["title"]))
            gap = date_gap(r["start"], p["start"])
            options.append((0 if same_words else 1, gap if gap is not None else 10 ** 6, ri, pi))
    taken_r, taken_p, match = set(), set(), {}
    for _w, _g, ri, pi in sorted(options):
        if ri in taken_r or pi in taken_p:
            continue
        taken_r.add(ri)
        taken_p.add(pi)
        match[ri] = pi
    pairs = [(r, profile[match[ri]] if ri in match else None) for ri, r in enumerate(roles)]
    return pairs, [p for pi, p in enumerate(profile) if pi not in taken_p]


EARLIER = re.compile(r"(?P<title>[^;:]+?)\s+at\s+(?P<company>.+?)(?:\s+in\s+[^;]+?)?,?\s+"
                     r"(?P<start>(?:19|20)\d{2})\s+to\s+(?P<end>(?:19|20)\d{2}|present)", re.I)


def earlier_jobs(text):
    """[{company, title, start, end}] from the earlier-career line, written as
    "Earlier career: Title at Company in City, ST, 2004 to 2010; ..."."""
    body = text.split(":", 1)[-1]
    out = []
    for clause in re.split(r";|\.(?=\s|$)", body):
        m = EARLIER.search(clause.strip())
        if m:
            out.append({"company": m.group("company").strip(), "title": m.group("title").strip(),
                        "start": month_year(m.group("start")), "end": month_year(m.group("end"))})
    return out


def compare(roles, profile, earlier=""):
    """[(level, where, note)] for every difference, plus a one-line summary."""
    out = []
    pairs, leftovers = pair(roles, profile)
    matched = 0
    for r, p in pairs:
        where = f"{r['title']} @ {r['company']}"
        if p is None:
            out.append(("REVIEW", where, "not on the LinkedIn profile"))
            continue
        clean = True
        level, note = title_verdict(r["title"], p["title"])
        if level != "OK":
            clean = False
            out.append((level, where, f"title: LinkedIn has \"{p['title']}\"; {note}"))
        for key, label in (("start", "start"), ("end", "end")):
            if r[key] != p[key]:
                if r[key] == "?" or p[key] == "?":
                    out.append(("REVIEW", where, f"{label} date unreadable: resume "
                                f"{show(r[key])}, LinkedIn {show(p[key])}"))
                elif date_gap(r[key], p[key]) == 0:
                    continue          # 2019 on one side, Jan 2019 on the other
                else:
                    out.append(("FAIL", where, f"{label} date: resume {show(r[key])}, "
                                f"LinkedIn {show(p[key])}"))
                clean = False
        matched += clean
    older = earlier_jobs(earlier) if earlier else []
    for p in leftovers:
        where = f"{p['title']} @ {p['company']}"
        line = next((e for e in older if same_company(e["company"], p["company"])), None)
        if line is None:
            out.append(("REVIEW", where, "on LinkedIn, not on the resume"))
            continue
        years = lambda d: d[0] if isinstance(d, tuple) else d   # noqa: E731
        if (years(line["start"]), years(line["end"])) != (years(p["start"]), years(p["end"])):
            out.append(("FAIL", where, f"years: the earlier-career line has {show(line['start'])} "
                        f"to {show(line['end'])}, LinkedIn has {show(p['start'])} to "
                        f"{show(p['end'])}"))
    fails = sum(1 for lv, _w, _n in out if lv == "FAIL")
    summary = (f"RECORD: {matched} of {len(roles)} resume jobs match LinkedIn exactly; "
               f"{fails} date conflict(s); "
               f"{sum(1 for lv, _w, _n in out if lv == 'REVIEW')} to review.")
    return out, summary


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(args) != 2:
        sys.exit(__doc__)
    roles, earlier = read_resume(args[0])
    if not roles or any(not r["company"] or r["start"] == "?" for r in roles):
        print(f"Could not read the jobs in {args[0]}: a job has no company or an unreadable "
              "date. Run this on the JSON source, or on a DOCX built by build_resume.py in "
              "the default layout.", file=sys.stderr)
        return 2
    profile = read_profile(args[1])
    out, summary = compare(roles, profile, earlier)
    print("=" * 70)
    print("PROFILE CHECK: resume jobs against LinkedIn jobs")
    print("=" * 70)
    for level in ("FAIL", "REVIEW"):
        rows = [o for o in out if o[0] == level]
        if rows:
            print(f"\n{level}")
            print("-" * 70)
            for _lv, where, note in rows:
                print(f"  {where}: {note}")
    print("\n" + summary)
    print("A title reordered for Workday, or with a descriptor the candidate chose, can")
    print("stay on the resume. Type the title exactly as held into the application's")
    print("title field and any background-check form.")
    print("=" * 70)
    return 1 if any(o[0] == "FAIL" for o in out) else 0


if __name__ == "__main__":
    sys.exit(main())
