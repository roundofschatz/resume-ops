#!/usr/bin/env python3
"""
requirement_check.py: turn a posting's required and preferred qualifications
into a numbered checklist, and, given a resume, show where each one is proven.

This is the tailoring work order. AI graders now read a posting's
qualifications one by one and look for evidence of each in the resume
(Workday HiredScore grades on required and preferred qualifications; LinkedIn
Hiring Assistant and Ashby check each criterion). The checklist puts every
qualification in front of the builder with the resume lines that might prove it.

The status is a word-overlap guess, not a grade:
  LIKELY  a bullet inside a role shares the key terms (a job title alone
          does not count)
  WEAK    only the summary, headline or skills line has them, which AI
          graders may not credit
  NONE    no line shares enough of them
Years items are checked against the role dates. Degree items are checked
against Education.

The builder finishes the Action column by hand: keep (the proof is there),
write into <role> (the work happened there and the page does not say it), or
gap (it is not true, so it is not written).

Stdlib only. Reads the posting the way term_coverage.py does.

Usage:
    python requirement_check.py posting.md
    python requirement_check.py posting.md resume.docx
    python requirement_check.py posting.md resume.json --out checklist.md
"""

import argparse
import datetime
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draft_review as dr  # noqa: E402
import term_coverage as tc  # noqa: E402

PREF_MARK = re.compile(r"\b(?:strongly\s+)?preferred\b|\b(?:is|are)\s+a\s+(?:big\s+|strong\s+)?"
                       r"(?:plus|bonus|signal)\b|\bnice\s+to\s+have\b|\bideally\b", re.I)
YEARS = re.compile(r"(\d+)\s*(?:\+|plus)?\s*(?:(?:-|\u2013|to)\s*\d+\s*)?\+?\s*(?:years?|yrs?)\b", re.I)
DEGREE = re.compile(r"\b(?:bachelor'?s?|master'?s?|mba|ph\.?d|doctorate|doctoral|"
                    r"associate'?s?\s+degree|degree)\b", re.I)
LEADER_ITEM = re.compile(r"\b(?:lead(?:ing|ership)?|manag(?:e|ing|ement)|supervis\w*|"
                         r"direct\s+reports|people\s+leader)\b", re.I)
LEADER_TITLE = re.compile(r"\b(?:director|manager|head|lead|supervisor|chief|vp|vice\s+president|"
                          r"president|principal|owner|founder|partner|superintendent|foreman|"
                          r"captain|officer)\b", re.I)
# Words that make an item about leading people, not about a field.
LEADER_STEMS = {"lead", "leadership", "leader", "manag", "management", "supervis", "supervisor",
                "people", "team", "develop", "direct", "report", "other"}
REQ_STOP = set("""
experience experienced years year ability able strong proven demonstrated skill skills knowledge
including degree excellent deep understanding hands-on familiarity expertise working exceptional
advanced comfort comfortable track record success successful curiosity curious relevant
professional progressive solid sound good great high highly level field practical
""".split())

MONTH = {m: i for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


# ------------------------------------------------------------------ posting --

def split_preferred(text):
    """A required item can carry a preferred clause: '... strongly preferred.'
    That sentence or comma clause moves to Preferred, word for word; the rest
    stays in Required, word for word."""
    text = text.strip()
    if not PREF_MARK.search(text):
        return [(text, False)]
    pieces = [p for p in re.split(r"(?<=[.;])\s+", text) if p]
    if len(pieces) == 1:
        return [(text, not re.search(r"\brequired\b", text, re.I))]
    out = []
    for p in pieces:
        if not PREF_MARK.search(p):
            out.append((p, False))
            continue
        clauses = re.split(r",\s+", p)
        marked = [c for c in clauses if PREF_MARK.search(c)]
        rest = [c for c in clauses if not PREF_MARK.search(c)]
        if rest and marked and PREF_MARK.search(clauses[0]):
            out.append((marked[0].rstrip(",;."), True))
            out.append((", ".join(rest), False))
        else:
            out.append((p, True))
    return out


def qualifications(posting):
    """{'required': [...], 'preferred': [...], 'moved': n}, verbatim, one per line."""
    req, pref, moved = [], [], []
    for text, tier, _bullet in tc.posting_lines(posting):
        text = text.strip()
        if not text or tier not in (1, 2):
            continue
        if tier == 2:
            pref.append(text)
            continue
        parts = split_preferred(text)
        req_parts = [p for p, is_pref in parts if not is_pref]
        if req_parts:
            req.append(" ".join(req_parts))
        moved += [p for p, is_pref in parts if is_pref]
    return {"required": req, "preferred": pref + moved, "moved": len(moved)}


# ------------------------------------------------------------------- resume --

def resume_lines(path):
    """[(text, where, kind, role)] for each line a qualification could be proven by."""
    blocks = dr.structure(dr.load(path))
    out, first_top = [], True
    roles = []
    for b in blocks:
        if b.kind == "header":
            continue
        if b.kind == "role":
            label = dr.role_label(b.role)
            roles.append({"meta": b.role, "label": label, "text": [b.role.get("title", "")]})
            out.append((label, f"role title: {label}", "title", roles[-1]))
            continue
        sec = b.section
        if not sec:
            if first_top or dr.CONTACT.search(b.text):
                first_top = False
                continue
            out.append((b.text, "headline", "headline", None))
        elif dr.is_summary(sec):
            for s in dr.sentences(b.text):
                out.append((s, "summary", "summary", None))
        elif dr.is_experience(sec):
            role = roles[-1] if roles else None
            if b.kind == "bullet":
                where = f"role: {role['label']}" if role else "experience"
                if role:
                    role["text"].append(b.text)
                out.append((b.text, where, "bullet", role))
            else:
                out.append((b.text, "earlier career", "earlier", None))
        elif dr.is_skills(sec):
            out.append((b.text, "skills", "skills", None))
        elif dr.is_education(sec):
            out.append((b.text, "education", "education", None))
        elif dr.is_certs(sec):
            out.append((b.text, "certifications", "certs", None))
        else:
            out.append((b.text, sec, "other", None))
    return out, roles


def content_stems(text):
    out = set()
    for t, _s, _e in tc.tokens(text):
        if tc.noise(t) or tc.breaker(t) or len(t) < 2 or t in REQ_STOP:
            continue
        if len(t) == 2 and not re.fullmatch(r"[a-z]{2}", t):
            continue
        out.add(tc.stem(t))
    return out


def need_for(n):
    return max(1, min(4, math.ceil(n / 3)))


# ------------------------------------------------------------ years, degree --

def month_index(text, today):
    s = text.strip().lower()
    if s in ("present", "current", "now", ""):
        return today.year * 12 + today.month - 1
    m = re.match(r"([a-z]{3})[a-z]*\.?\s+(\d{4})", s)
    if not m or m.group(1) not in MONTH:
        return None
    return int(m.group(2)) * 12 + MONTH[m.group(1)] - 1


def total_years(spans):
    """Union of [start, end] month spans, in years."""
    months, cur = 0, None
    for a, b in sorted(spans):
        if cur is None or a > cur[1]:
            if cur:
                months += cur[1] - cur[0] + 1
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur:
        months += cur[1] - cur[0] + 1
    return round(months / 12, 1)


def role_spans(roles, lines, today):
    spans = []
    for r in roles:
        a = month_index(r["meta"].get("start", ""), today)
        b = month_index(r["meta"].get("end", ""), today)
        if a is not None and b is not None and b >= a:
            spans.append((a, b, r))
    for text, _w, kind, _r in lines:
        if kind != "earlier":
            continue
        m = re.search(r"\b((?:19|20)\d{2})\s*(?:to|-|\u2013)\s*((?:19|20)\d{2}|present)\b", text, re.I)
        if m:
            a = int(m.group(1)) * 12
            b = month_index("present", today) if m.group(2).lower() == "present" else int(m.group(2)) * 12 + 11
            spans.append((a, b, None))
    return spans


def years_status(item, n_years, roles, lines, today):
    spans = role_spans(roles, lines, today)
    if not spans:
        return "NONE", ["No role dates found on the resume."]
    total = total_years([(a, b) for a, b, _r in spans])
    rest = YEARS.sub(" ", item)
    leader = LEADER_ITEM.search(rest) is not None
    field = content_stems(rest) - LEADER_STEMS
    relevant = []
    for a, b, r in spans:
        if r is None:
            continue
        ok_field = not field or len(field & content_stems(" ".join(r["text"]))) >= need_for(len(field))
        ok_leader = not leader or LEADER_TITLE.search(r["meta"].get("title", "")) is not None
        if ok_field and ok_leader:
            relevant.append((a, b, r))
    rel = total_years([(a, b) for a, b, _r in relevant]) if relevant else 0.0
    first = min(a for a, _b, _r in spans)
    since = datetime.date(first // 12, first % 12 + 1, 1).strftime("%b %Y")
    notes = [f"Asks for {n_years}+ years. The resume shows {total} years across all roles "
             f"(since {since}); {rel} years in roles that match"
             + (": " + "; ".join(r["label"] for _a, _b, r in relevant[:3]) if relevant else "") + "."]
    if rel >= n_years:
        return "LIKELY", notes
    if total >= n_years:
        return "WEAK", notes
    return "NONE", notes


def degree_level(text):
    t = text
    levels = []
    if re.search(r"\b(?:ph\.?d|doctor(?:ate|al)?)\b", t, re.I) or \
            re.search(r"(?:^|\|\s*|;\s*)(?:PhD|EdD|JD|MD|DNP)\b", t):
        levels.append(3)
    if re.search(r"\b(?:master'?s?|mba)\b", t, re.I) or \
            re.search(r"(?:^|\|\s*|;\s*)(?:MA|MS|MSc|MBA|MSN|MPH|MFA|MEd|M\.S\.|M\.A\.)\b", t):
        levels.append(2)
    if re.search(r"\bbachelor'?s?\b", t, re.I) or \
            re.search(r"(?:^|\|\s*|;\s*)(?:BA|BS|BSc|BBA|BFA|BSN|B\.S\.|B\.A\.)\b", t):
        levels.append(1)
    if re.search(r"\bassociate'?s?\b", t, re.I) or re.search(r"(?:^|\|\s*|;\s*)(?:AAS|AA|AS)\b", t):
        levels.append(0.5)
    return max(levels) if levels else None


def degree_status(item, lines):
    need = degree_level(item)
    if need is None:
        need = 1
    edu = [(t, w) for t, w, kind, _r in lines if kind in ("education", "certs")]
    best = None
    for t, w in edu:
        lv = degree_level(t)
        if lv is not None and (best is None or lv > best[0]):
            best = (lv, t, w)
    equivalent = re.search(r"\bequivalent\b", item, re.I)
    if best and best[0] >= need:
        return "LIKELY", [(best[1], best[2])], []
    if best:
        return "WEAK", [(best[1], best[2])], ["A degree is listed, below the level asked."]
    if equivalent:
        return "WEAK", [], ["No degree listed. The posting accepts equivalent experience."]
    return "NONE", [], ["No degree found in Education."]


# ---------------------------------------------------------------- matching --

def check(item, lines, roles, today):
    """(status, [(line, where)], notes) for one qualification."""
    stems = content_stems(item)
    scored = []
    for i, (text, where, kind, _r) in enumerate(lines):
        s = len(stems & content_stems(text))
        if s:
            rank = 0 if kind in ("bullet", "title") else 1 if kind == "summary" else 2
            scored.append((-s, rank, i, text, where, kind))
    scored.sort()
    need = need_for(len(stems))
    proof = [(t, w) for _s, _r, _i, t, w, _k in scored[:2]]
    in_role = any(-s >= need and k == "bullet" for s, _r, _i, _t, _w, k in scored)
    elsewhere = any(-s >= need and k in ("summary", "skills", "headline", "title") for s, _r, _i, _t, _w, k in scored)
    status = "LIKELY" if in_role else "WEAK" if elsewhere else "NONE"
    notes = []
    if status == "WEAK":
        notes.append("Only the summary, headline or skills line has it. AI graders may not credit that.")

    m = YEARS.search(item)
    if m:
        ystatus, ynotes = years_status(item, int(m.group(1)), roles, lines, today)
        status, notes = ystatus, ynotes + notes
    elif DEGREE.search(item):
        status, proof, notes = degree_status(item, lines)
    return status, proof, notes


# ------------------------------------------------------------------ output --

def cell(text, limit=160):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit - 3].rstrip() + "..."
    return text.replace("|", "\\|")


def build(posting_path, resume_path=None, today=None):
    today = today or datetime.date.today()
    posting = tc.read_text(posting_path)
    q = qualifications(posting)
    title = tc.posting_title(posting) or Path(posting_path).stem
    lines, roles = resume_lines(resume_path) if resume_path else ([], [])

    out = [f"# Requirement checklist: {cell(title, 100)}", ""]
    out.append(f"Posting: {Path(posting_path).name}")
    if resume_path:
        out.append(f"Resume: {Path(resume_path).name}")
    out += ["",
            "The status is a word-overlap guess, not a grade. Read every row and fill the "
            "Action column by hand: keep (the proof is there), write into <role> (the work "
            "happened there and the page does not say it), or gap (it is not true, so it is "
            "not written).", ""]
    if not q["required"]:
        out += ["No required-qualifications section found. Read the posting and list the "
                "requirements by hand.", ""]
    counts = {"LIKELY": 0, "WEAK": 0, "NONE": 0}
    for kind, items, prefix in (("Required", q["required"], "R"), ("Preferred", q["preferred"], "P")):
        out.append(f"## {kind} ({len(items)})")
        out.append("")
        if not items:
            out.append("No preferred section in this posting." if kind == "Preferred"
                       else "None found.")
            out.append("")
            continue
        if resume_path:
            out.append("| # | Type | Qualification | Status | Proof line (section) | Action |")
            out.append("|---|---|---|---|---|---|")
        else:
            out.append("| # | Type | Qualification | Proof line (section) | Action |")
            out.append("|---|---|---|---|---|")
        for n, item in enumerate(items, 1):
            if not resume_path:
                out.append(f"| {prefix}{n} | {kind} | {cell(item, 400)} |  |  |")
                continue
            status, proof, notes = check(item, lines, roles, today)
            counts[status] += 1
            shown = "<br>".join(f"\"{cell(t)}\" ({cell(w, 80)})" for t, w in proof) or "none found"
            if notes:
                shown += "<br>" + " ".join(cell(x, 300) for x in notes)
            out.append(f"| {prefix}{n} | {kind} | {cell(item, 400)} | {status} | {shown} |  |")
        out.append("")
    if q["moved"]:
        out.append(f"{q['moved']} clause(s) marked preferred inside a required item were moved to "
                   "Preferred.")
        out.append("")
    if resume_path:
        out.append(f"First pass: {counts['LIKELY']} LIKELY, {counts['WEAK']} WEAK, "
                   f"{counts['NONE']} NONE. A guess from shared words. It is not what any grader "
                   "will decide.")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Posting qualifications as a checklist, with proof lines.")
    ap.add_argument("posting")
    ap.add_argument("resume", nargs="?")
    ap.add_argument("--out", help="write the checklist to this file")
    args = ap.parse_args()
    text = build(args.posting, args.resume)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Checklist written to {args.out}")
        print("The status is a word-overlap guess, not a grade. Finish the Action column by hand.")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
