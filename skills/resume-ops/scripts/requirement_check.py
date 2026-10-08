#!/usr/bin/env python3
"""
requirement_check.py: turn a posting's required and preferred qualifications
into a numbered checklist; given the candidate's evidence, find the passages
that could prove each one; given a resume, show where each one is proven.

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

Evidence is anything the candidate gave: career notes, a career record, an
old resume, a cover letter, a LinkedIn profile, website text. With --evidence,
each file (.md, .txt, .docx, or a PDF through pdftotext) is split on its
headings, and each qualification gets its best passages, each with the file,
the heading above it and the line, so the builder opens only those. A file past
the read-whole line (READ_WHOLE_LINES or READ_WHOLE_BYTES) is searched, not
read whole, and every qualification stays on the list either way. For a DOCX
the line is the paragraph number, empty paragraphs counted, as corpus_triage.py
counts them. For a PDF it is the line in pdftotext's text.

The builder finishes the Action column by hand: keep (the proof is there),
write into <role> (the work happened there and the page does not say it), or
gap (it is not true, so it is not written).

Stdlib only (a PDF needs pdftotext from poppler). Reads the posting the way
term_coverage.py does.

Usage:
    python requirement_check.py posting.md
    python requirement_check.py posting.md --evidence notes.md old-resume.docx
    python requirement_check.py posting.md resume.docx
    python requirement_check.py posting.md resume.json --evidence record.md --out checklist.md
"""

import argparse
import datetime
import math
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docx  # noqa: E402
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


def req_stem(t):
    """term_coverage's stem, plus one step: a doubled consonant left by -ing or
    -ed is halved, so "mapping" and "planned" meet "map" and "plan"."""
    s = tc.stem(t)
    if re.search(r"(?:ing|ed)$", t) and len(s) > 3 and s[-1] == s[-2] and s[-1] not in "aeiouyflsz":
        s = s[:-1]
    return s


def content_stems(text):
    out = set()
    for t, _s, _e in tc.tokens(text):
        if tc.noise(t) or tc.breaker(t) or len(t) < 2 or t in REQ_STOP:
            continue
        if len(t) == 2 and not re.fullmatch(r"[a-z]{2}", t):
            continue
        out.add(req_stem(t))
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


# ---------------------------------------------------------------- evidence --

# The skill's working line for reading a file whole. Past either, search it.
READ_WHOLE_LINES = 2000
READ_WHOLE_BYTES = 150_000
MAP_ROWS = 40          # headings shown on a file's map
TOP = 3                # passages per qualification
BOLD_LEVEL = 7         # a bold-only line is a heading below every numbered level

MD_ATX = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
MD_BOLD = re.compile(r"^\s*(?:\*\*|__)([^*_].{0,78}?)(?:\*\*|__)\s*:?\s*$")
BULLET_LINE = re.compile(r"^\s*(?:[-*+•·▪●]|\d{1,2}[.)])\s+")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[*_]*[A-Z0-9$])")
STYLE_HEAD = re.compile(r"^(?:heading\s*(\d)|title)$", re.I)
W = _docx.W


def clean_head(text):
    s = re.sub(r"^#+\s*", "", text.strip())
    s = s.strip("*_ ").strip()
    return re.sub(r"\s*:\s*$", "", s).strip("*_ ").strip()


def _text_heading(line, prev_blank):
    """Level for a heading line in plain text (a .txt or a PDF's text), else None."""
    s = line.strip()
    if not s or BULLET_LINE.match(s) or len(s) > 70 or len(s.split()) > 9:
        return None
    if re.search(r"[.,;]$", s):
        return None
    letters = re.sub(r"[^A-Za-z]", "", s)
    if letters and s.upper() == s and len(letters) >= 3 and not _docx.is_role_line(s):
        return 1
    if _docx.header_kind(s):
        return 1
    if prev_blank and s.endswith(":"):
        return 2
    return None


def _rows_text(lines, markdown):
    """[(line, kind, level, text)] with kind heading, body, bullet or blank."""
    rows, prev_blank = [], True
    for n, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s:
            rows.append((n, "blank", 0, ""))
            prev_blank = True
            continue
        level = None
        if markdown:
            m = MD_ATX.match(raw)
            if m:
                level = len(m.group(1))
            elif MD_BOLD.match(raw):
                level = BOLD_LEVEL
        else:
            level = _text_heading(raw, prev_blank)
        if level:
            rows.append((n, "heading", level, clean_head(s)))
        elif BULLET_LINE.match(raw):
            rows.append((n, "bullet", 0, BULLET_LINE.sub("", raw, count=1).strip()))
        else:
            rows.append((n, "body", 0, s))
        prev_blank = False
    return rows


def _is_bold(run):
    b = run.find(f"./{W}rPr/{W}b")
    return b is not None and b.get(f"{W}val", "true") not in ("0", "false")


def _rows_docx(path):
    """Paragraphs as rows. The line is the paragraph number, empty ones counted."""
    try:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as e:
        sys.exit(f"Cannot read {path} as a .docx: {e}")
    rows = []
    for n, para in enumerate(root.iter(f"{W}p"), 1):
        text = "".join(t.text or "" for t in para.iter(f"{W}t")).strip()
        if not text:
            rows.append((n, "blank", 0, ""))
            continue
        style = para.find(f"./{W}pPr/{W}pStyle")
        m = STYLE_HEAD.match(style.get(f"{W}val", "")) if style is not None else None
        runs = [r for r in para.iter(f"{W}r") if "".join(t.text or "" for t in r.iter(f"{W}t")).strip()]
        bold = bool(runs) and all(_is_bold(r) for r in runs)
        if m:
            rows.append((n, "heading", int(m.group(1) or 1), clean_head(text)))
        elif para.find(f".//{W}numPr") is not None:
            rows.append((n, "bullet", 0, text))
        elif _docx.header_kind(text):
            rows.append((n, "heading", 1, clean_head(text)))
        elif bold and len(text) <= 80 and len(text.split()) <= 12:
            rows.append((n, "heading", BOLD_LEVEL, clean_head(text)))
        else:
            rows.append((n, "body", 0, text))
    return rows


def _pdf_lines(path):
    exe = shutil.which("pdftotext")
    if not exe:
        sys.exit(f"{path}: pdftotext (poppler) is not installed. Read the PDF directly, save its "
                 "text as a .txt file, and pass that instead.")
    # -enc UTF-8: xpdf's pdftotext (the one Git for Windows ships) writes
    # Latin-1 by default, and reading that as UTF-8 drops dashes and accents.
    r = subprocess.run([exe, "-layout", "-enc", "UTF-8", str(path), "-"], capture_output=True,
                       text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        sys.exit(f"pdftotext could not read {path}: {r.stderr.strip()}")
    return r.stdout.splitlines()


def read_evidence(path):
    """{'name', 'lines', 'bytes', 'headings': [(line, level, text)], 'units': [...]}.

    A unit is one sentence: (line, trail, para, text), where trail is the
    tuple of headings above it and para numbers the paragraph it sits in."""
    p = Path(path)
    suffix = p.suffix.lower()
    if not p.exists():
        sys.exit(f"File not found: {path}")
    if suffix == ".docx":
        rows = _rows_docx(p)
    elif suffix == ".pdf":
        rows = _rows_text(_pdf_lines(p), markdown=False)
    else:
        text = p.read_text(encoding="utf-8", errors="ignore")
        rows = _rows_text(text.splitlines(), markdown=suffix in (".md", ".markdown"))
    size = sum(len(t.encode("utf-8")) + 1 for _n, _k, _l, t in rows)
    headings, units, trail, para = [], [], [], 0
    for n, kind, level, text in rows:
        if kind == "heading":
            while trail and trail[-1][0] >= level:
                trail.pop()
            trail.append((level, text, n))
            headings.append((n, level, text))
            para += 1
            continue
        if kind == "blank":
            para += 1
            continue
        if kind == "bullet" or suffix == ".docx":
            para += 1
        for s in SENTENCE.split(text):
            if s.strip():
                units.append((n, tuple(t for _l, t, _n in trail),
                              trail[-1][2] if trail else 0, para, s.strip()))
        if kind == "bullet":
            para += 1
    return {"name": p.name, "lines": len(rows), "bytes": size,
            "headings": headings, "units": units}


def over_the_line(ev):
    return ev["lines"] > READ_WHOLE_LINES or ev["bytes"] > READ_WHOLE_BYTES


def _windows(evs):
    """Every run of one to three sentences inside one paragraph."""
    out, order = [], 0
    for ev in evs:
        units = ev["units"]
        stems = [content_stems(u[4]) for u in units]
        heads = {}
        for i, u in enumerate(units):
            for size in (1, 2, 3):
                j = i + size
                if j > len(units) or units[j - 1][3] != u[3]:
                    break
                body = set().union(*stems[i:j])
                if u[1] not in heads:
                    heads[u[1]] = content_stems(" ".join(u[1][-2:]))
                out.append({"file": ev["name"], "line": u[0], "trail": u[1], "section": (ev["name"], u[2]),
                            "text": " ".join(x[4] for x in units[i:j]), "body": body, "sents": stems[i:j],
                            "head": heads[u[1]], "size": size, "order": order})
                order += 1
    return out


ITEM_CLAUSE = re.compile(r"\s*:\s*|" + tc.CLAUSE.pattern)
INDEX_HEAD = re.compile(r"^(?:index|contents|table of contents)$", re.I)


def item_clauses(item):
    """The parts of a list qualification ("journey mapping, service blueprints,
    Figma, or Miro"). Any one part, fully present, is a passage worth opening.
    A one-word part counts only when it is a name (capitalized past the first
    word), so "Figma" counts and "curiosity" does not."""
    out, first = [], True
    for part in ITEM_CLAUSE.split(item):
        if not part or not part.strip():
            continue
        stems = content_stems(part)
        if len(stems) >= 2:
            out.append(frozenset(stems))
        elif len(stems) == 1:
            words = [w for w in re.findall(r"[A-Za-z][\w+#.-]*", part)]
            named = [w for i, w in enumerate(words) if w[0].isupper() and not (first and i == 0)]
            if named:
                out.append(frozenset(stems))
        first = False
    return out


def snippet(text, matched, width=220, lead=()):
    """The passage, cut to `width` around the first word of `lead` (the words
    that matter most, in order), or else around the first matched word."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= width:
        return text
    toks = [(req_stem(t), s) for t, s, _e in tc.tokens(text)]
    start = next((s for want in lead for st, s in toks if st == want), None)
    if start is None:
        start = next((s for st, s in toks if st in matched), 0)
    start = max(0, start - 60)
    cut = text[start:start + width - 6].rstrip()
    return ("..." if start else "") + cut + "..."


def search_evidence(items, paths, top=TOP):
    """For each qualification, [{'file', 'line', 'heading', 'text', 'score'}]:
    the best passage from each of up to `top` sections, best first. An empty
    list means no passage shares enough of its words; the item still stands.

    A passage is a run of one to three sentences inside one paragraph. It is a
    candidate when it shares enough of the item's words (need_for), holds one
    whole part of a list item inside one sentence (item_clauses), or holds the item's rarest word
    in this evidence. Words score by how rare they are in the evidence; a whole
    part scores again, twice; the heading's words count half; an index or table
    of contents counts half."""
    evs = [p if isinstance(p, dict) else read_evidence(p) for p in paths]
    wins = _windows(evs)
    singles = [w for w in wins if w["size"] == 1]
    df = {}
    for w in singles:
        for s in w["body"]:
            df[s] = df.get(s, 0) + 1
    n = len(singles)
    idf = {s: math.log((n + 1) / (c + 1)) + 1 for s, c in df.items()}
    results = []
    for item in items:
        stems = content_stems(item)
        if not stems:
            results.append([])
            continue
        need = need_for(len(stems))
        clauses = item_clauses(item)
        rarest = max(stems, key=lambda s: (idf.get(s, 0.0), s))
        best = {}
        for w in wins:
            body = stems & w["body"]
            if not body:
                continue
            head = (stems & w["head"]) - body
            whole = [c for c in clauses if any(c <= s for s in w["sents"])]
            if len(body) + len(head) < need and not whole and rarest not in body:
                continue
            score = sum(idf.get(s, 1.0) for s in body) + 0.5 * sum(idf.get(s, 1.0) for s in head)
            score += 2 * sum(idf.get(s, 1.0) for c in whole for s in c)
            if w["trail"] and INDEX_HEAD.match(w["trail"][-1]):
                score *= 0.5
            key = (-round(score, 6), w["size"], w["order"])
            slot = (w["section"], frozenset(whole))
            if slot not in best or key < best[slot][0]:
                best[slot] = (key, w, body | head, frozenset(whole))
        ranked = sorted(best.values(), key=lambda x: x[0])
        # A list item's passages cover as many of its parts as they can (up to
        # six rows for a long list): first, again and again, the passage that
        # adds the rarest parts not yet covered; then the best of the rest.
        limit = max(top, min(6, len(clauses)))
        chosen, covered = [], set()

        def gain(c):
            return sum(idf.get(s, 1.0) for part in c[3] - covered for s in part)

        while len(chosen) < limit:
            pool = [c for c in ranked if c not in chosen]
            if not pool:
                break
            pick = max(pool, key=lambda c: (round(gain(c), 6), -c[0][0], -c[0][2]))
            if gain(pick) <= 0:
                break
            chosen.append(pick)
            covered |= pick[3]
        sections = {c[1]["section"] for c in chosen}
        for cand in ranked:
            if len(chosen) >= limit:
                break
            if cand[1]["section"] not in sections:
                chosen.append(cand)
                sections.add(cand[1]["section"])
        chosen.sort(key=lambda x: x[0])
        def lead(matched, whole):
            first = [s for part in sorted(whole, key=lambda p: -sum(idf.get(x, 1.0) for x in p))
                     for s in sorted(part, key=lambda x: -idf.get(x, 1.0))]
            return first + sorted(matched, key=lambda x: -idf.get(x, 1.0))

        results.append([{"file": w["file"], "line": w["line"], "heading": " > ".join(w["trail"]),
                         "text": snippet(w["text"], matched, lead=lead(matched, whole)),
                         "score": round(-key[0], 2)}
                        for key, w, matched, whole in chosen])
    return results


def evidence_map(ev, rows=MAP_ROWS):
    """The headings to show: every level down to the deepest that fits in `rows`."""
    heads = ev["headings"]
    shown = []
    for level in sorted({lv for _n, lv, _t in heads}):
        pick = [h for h in heads if h[1] <= level]
        if len(pick) > rows:
            break
        shown = pick
    if not shown and heads:
        top = min(lv for _n, lv, _t in heads)
        shown = [h for h in heads if h[1] == top][:rows]
    return shown, len(heads)


def evidence_cell(hits, item):
    if not hits:
        return "none found"
    parts = []
    for h in hits:
        trail = h["heading"].split(" > ")[-3:] if h["heading"] else []
        where = " > ".join(cell(t, 60) for t in trail)
        head = f', under "{where}"' if where else ""
        parts.append(f"{cell(h['file'], 60)}, line {h['line']}{head}: \"{cell(h['text'], 220)}\"")
    if YEARS.search(item):
        parts.append("Years: count them from the role dates, only the roles that did this work.")
    return "<br>".join(parts)


# ------------------------------------------------------------------ output --

def cell(text, limit=160):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit - 3].rstrip() + "..."
    return text.replace("|", "\\|")


def build(posting_path, resume_path=None, today=None, evidence=None, top=TOP):
    today = today or datetime.date.today()
    posting = tc.read_text(posting_path)
    q = qualifications(posting)
    title = tc.posting_title(posting) or Path(posting_path).stem
    lines, roles = resume_lines(resume_path) if resume_path else ([], [])
    evs = [read_evidence(p) for p in (evidence or [])]
    hits = {}
    if evs:
        items = q["required"] + q["preferred"]
        hits = dict(zip(items, search_evidence(items, evs, top)))

    out = [f"# Requirement checklist: {cell(title, 100)}", ""]
    out.append(f"Posting: {Path(posting_path).name}")
    if resume_path:
        out.append(f"Resume: {Path(resume_path).name}")
    for ev in evs:
        kb = max(1, round(ev["bytes"] / 1024))
        if over_the_line(ev):
            how = (f"Over the read-whole line ({READ_WHOLE_LINES:,} lines or "
                   f"{READ_WHOLE_BYTES // 1000} KB): search it. Open the passages below, and the "
                   "sections on the map that hold the work history, education and credentials.")
        else:
            how = "Under the read-whole line: read it all, start to end."
        out.append(f"Evidence: {ev['name']} ({ev['lines']:,} lines, {kb:,} KB). {how}")
    out += ["",
            "The status is a word-overlap guess, not a grade. Read every row and fill the "
            "Action column by hand: keep (the proof is there), write into <role> (the work "
            "happened there and the page does not say it), or gap (it is not true, so it is "
            "not written).", ""]
    if evs:
        out += ["The Evidence column lists the best passages for each qualification, with the "
                "file, the line and the heading above it. Open those lines; the proof comes from "
                "the evidence itself. A row with none found gets a second search in the "
                "candidate's own words (another name for the tool, the client, the project) "
                "before it is called a gap. No qualification is dropped because a file was too "
                "big to read.", ""]
        out += ["## Evidence map", ""]
        for ev in evs:
            shown, total = evidence_map(ev)
            out.append(f"### {ev['name']}")
            out.append("")
            if not shown:
                out += ["No headings found. Every passage below gives its line.", ""]
                continue
            out += ["| Line | Heading |", "|---|---|"]
            out += [f"| {n} | {cell(t, 120)} |" for n, _lv, t in shown]
            if total > len(shown):
                out += ["", f"{total - len(shown)} deeper headings not shown; the passages below "
                        "name them."]
            out.append("")
    if not q["required"]:
        out += ["No required-qualifications section found. Read the posting and list the "
                "requirements by hand.", ""]
    counts = {"LIKELY": 0, "WEAK": 0, "NONE": 0}
    ev_counts = {"found": 0, "none": 0}
    for kind, items, prefix in (("Required", q["required"], "R"), ("Preferred", q["preferred"], "P")):
        out.append(f"## {kind} ({len(items)})")
        out.append("")
        if not items:
            out.append("No preferred section in this posting." if kind == "Preferred"
                       else "None found.")
            out.append("")
            continue
        ev_head = " Evidence (file, line, heading) |" if evs else ""
        ev_rule = "---|" if evs else ""
        if resume_path:
            out.append(f"| # | Type | Qualification | Status | Proof line (section) |{ev_head} Action |")
            out.append(f"|---|---|---|---|---|{ev_rule}---|")
        elif evs:
            out.append(f"| # | Type | Qualification |{ev_head} Action |")
            out.append(f"|---|---|---|{ev_rule}---|")
        else:
            out.append("| # | Type | Qualification | Proof line (section) | Action |")
            out.append("|---|---|---|---|---|")
        for n, item in enumerate(items, 1):
            ev_cell = f" {evidence_cell(hits.get(item, []), item)} |" if evs else ""
            if evs:
                ev_counts["found" if hits.get(item) else "none"] += 1
            if not resume_path:
                if evs:
                    out.append(f"| {prefix}{n} | {kind} | {cell(item, 400)} |{ev_cell}  |")
                else:
                    out.append(f"| {prefix}{n} | {kind} | {cell(item, 400)} |  |  |")
                continue
            status, proof, notes = check(item, lines, roles, today)
            counts[status] += 1
            shown = "<br>".join(f"\"{cell(t)}\" ({cell(w, 80)})" for t, w in proof) or "none found"
            if notes:
                shown += "<br>" + " ".join(cell(x, 300) for x in notes)
            out.append(f"| {prefix}{n} | {kind} | {cell(item, 400)} | {status} | {shown} |{ev_cell}  |")
        out.append("")
    if q["moved"]:
        out.append(f"{q['moved']} clause(s) marked preferred inside a required item were moved to "
                   "Preferred.")
        out.append("")
    if evs:
        out.append(f"Evidence: {ev_counts['found']} of {ev_counts['found'] + ev_counts['none']} "
                   f"qualifications have passages; {ev_counts['none']} have none found. Word "
                   "overlap, not proof: read each passage before it goes on the page.")
        out.append("")
    if resume_path:
        out.append(f"First pass: {counts['LIKELY']} LIKELY, {counts['WEAK']} WEAK, "
                   f"{counts['NONE']} NONE. A guess from shared words. It is not what any grader "
                   "will decide.")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Posting qualifications as a checklist, with the "
                                 "passages in the evidence and the proof lines on a resume.")
    ap.add_argument("posting")
    ap.add_argument("resume", nargs="?", help="a draft or built resume (.json, .docx, .md, .txt)")
    ap.add_argument("--evidence", nargs="+", metavar="FILE",
                    help="the candidate's evidence: .md, .txt, .docx or .pdf, one or many")
    ap.add_argument("--top", type=int, default=TOP, help=f"passages per qualification (default {TOP})")
    ap.add_argument("--out", help="write the checklist to this file")
    args = ap.parse_args()
    text = build(args.posting, args.resume, evidence=args.evidence, top=args.top)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Checklist written to {args.out}")
        print("The status is a word-overlap guess, not a grade. Finish the Action column by hand.")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
