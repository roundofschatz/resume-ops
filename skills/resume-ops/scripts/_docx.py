#!/usr/bin/env python3
"""
_docx.py: one reader, shared by every script in this folder.

There used to be four copies of this, and they had drifted: one kept empty
paragraphs, one dropped them, one knew what a bullet was and one did not, and
none of them knew what a section header was. One reader, one answer.

It also holds the one role reader. parse_check.py and corpus_triage.py both
need to find job entries, and two readers would drift the same way.

Stdlib only.
"""

import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# The five this skill writes. references/document.md owns why.
WRITE_HEADERS = {"summary", "skills", "experience", "education", "certifications"}

# Headers a candidate's existing resume may use. Read these on the way in;
# write the five on the way out.
KNOWN_HEADERS = WRITE_HEADERS | {
    "professional summary", "executive summary", "profile",
    "core competencies", "technical skills", "key skills", "areas of expertise",
    "professional experience", "work experience", "employment history",
    "relevant experience", "licenses and certifications",
    "publications", "speaking", "volunteer experience", "awards", "honors",
    "projects",
}

# Short title-case lines that are headers rather than job titles. Without this
# list the only way to spot a non-standard header is ALL CAPS, which misses
# "Key Accomplishments" entirely. A job title is also a short title-case line,
# so a general rule would flag every role on the page.
HEADERISH = re.compile(
    r"^(?:key\s+|selected\s+|notable\s+|core\s+|other\s+|additional\s+)?"
    r"(?:accomplishments?|achievements?|highlights?|methodolog(?:y|ies)|frameworks?|"
    r"philosoph(?:y|ies)|competenc(?:y|ies)|expertise|awards?|honou?rs?|publications?|"
    r"presentations?|speaking|projects?|volunteer(?:ing|\s+experience)?|interests?|"
    r"activities|affiliations?|memberships?|languages?|references?|"
    r"proprietary\s+models?|career\s+highlights?)$", re.I)

# Contact details. Two phone shapes: North American, and any international
# number written with a country code and two to five groups.
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(
    r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
    r"|\+\d{1,3}[\s.-]?(?:\(?\d{1,5}\)?[\s.-]?){1,4}\d{2,5}")

# ---------------------------------------------------------------- dates

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_MON = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|"
        r"Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?")
_YEAR = r"(?:19|20)\d{2}"
_ONE_DATE = (rf"(?:{_MON}\s+{_YEAR}|\d{{1,2}}/(?:{_YEAR}|\d{{2}})|{_YEAR})")
_NOW = r"(?:Present|Current|Now|Today)"
_SEP = r"\s*(?:[-\u2013\u2014]|\bto\b)\s*"

# Two dates joined by a dash or "to", or a date and Present. A start with no
# year ("January - December 2018") and an open end ("Sep 2025 - ") are read
# too, because career notes are written that way.
DATE_RANGE = re.compile(
    rf"(?<![\w/])(?P<start>{_ONE_DATE}|{_MON}(?=\s*[-\u2013\u2014]\s*{_MON}\s+{_YEAR}))"
    rf"{_SEP}"
    rf"(?:(?P<end>{_ONE_DATE}|{_NOW})(?![\w/])|(?=\s*(?:\)|$)))",
    re.I)

# The same, but only with a dash between the two dates. A range written with
# "to" is usually a phrase in a sentence ("2004 to 2010"), not a date line.
DASH_RANGE = re.compile(
    rf"(?<![\w/])(?P<start>{_ONE_DATE})\s*[-\u2013\u2014]\s*(?P<end>{_ONE_DATE}|{_NOW})(?![\w/])",
    re.I)

_STATE_TAIL = re.compile(r",\s*[A-Z]{2}\s*$")

# Words that mark a line as a job title rather than a company. Used only to
# settle a two-line entry when nothing else says which line is which.
TITLE_WORDS = re.compile(
    r"\b(?:manager|director|supervisor|nurse|engineer|analyst|specialist|technician|"
    r"strategist|associate|coordinator|assistant|officer|lead|head|president|vice|"
    r"consultant|teacher|accountant|representative|executive|designer|developer|"
    r"intern|operator|administrator|clerk|planner|architect|scientist|advis[oe]r|"
    r"agent|chef|cook|driver|mechanic|electrician|instructor|professor|principal|"
    r"founder|co-founder|superintendent|foreman|therapist|pharmacist|physician|"
    r"counsel+or|attorney|paralegal|editor|writer|producer|buyer|controller|auditor|"
    r"bookkeeper|cashier|receptionist|secretary|aide|chief|ceo|cfo|coo|cto|vp|rn|"
    r"lpn|cna)\b", re.I)

# Section names that hold job entries. Dates under Education are not jobs.
_JOB_SECTIONS = re.compile(r"experience|employment|work history|career", re.I)


def open_docx(path):
    try:
        return zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError, OSError) as e:
        sys.exit(f"Cannot open {path}: {e}")


def _para_text(para):
    return "".join(t.text or "" for t in para.iter(f"{W}t")).strip()


def blocks(path, keep_empty=False):
    """Every paragraph in document order as (kind, text).

    kind is one of: header, bullet, para. Header detection matches the same
    strings parse_check.py matches, so the two scripts agree about what a
    section is.
    """
    z = open_docx(path)
    try:
        root = ET.fromstring(z.read("word/document.xml"))
    except KeyError:
        sys.exit(f"No word/document.xml in {path}. Is this a .docx file?")
    except ET.ParseError as e:
        sys.exit(f"The document.xml in {path} is broken: {e}")

    out = []
    for para in root.iter(f"{W}p"):
        text = _para_text(para)
        if not text and not keep_empty:
            continue
        if para.find(f".//{W}numPr") is not None:
            out.append(("bullet", text))
            continue
        out.append((header_kind(text) or "para", text))
    return out


def is_role_line(text):
    """True for a line that is part of a job entry: a company line ending in
    ", ST", or any line carrying a date range. A header never carries either."""
    t = text.strip()
    return bool(_STATE_TAIL.search(t) or DATE_RANGE.search(t))


def header_kind(text):
    """'header' if this line is a section header, else None."""
    if is_role_line(text):
        return None
    s = text.strip().strip(":").lower()
    if not (3 <= len(s) <= 40 and len(s.split()) <= 4):
        return None
    if s in KNOWN_HEADERS:
        return "header"
    if text.strip().isupper() or HEADERISH.match(s):
        return "header"
    return None


def lines(path):
    """Just the text, in the order a simple text reader gets it."""
    return [t for _k, t in blocks(path)]


def with_sections(blks):
    """(kind, text, section). section is the lowercased header above the block."""
    out, cur = [], ""
    for kind, text in blks:
        if kind == "header":
            cur = text.strip().strip(":").lower()
        out.append((kind, text, cur))
    return out


def is_skills_section(section):
    """Skills lines are exempt from the two-line bullet cap."""
    return section.startswith("skill") or section in (
        "core competencies", "technical skills", "key skills", "areas of expertise")


# ---------------------------------------------------------------- roles

def split_place(text):
    """'Name, City, ST' -> (name, city, state). Missing parts come back empty.

    'Denver, CO' alone is a place with no name. 'Acme, Leeds' is a name and a
    city with no state.
    """
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return "", "", ""
    if len(parts) >= 3 and re.fullmatch(r"[A-Z]{2}", parts[-1]):
        return ", ".join(parts[:-2]), parts[-2], parts[-1]
    if len(parts) == 2 and re.fullmatch(r"[A-Z]{2}", parts[-1]):
        return "", parts[0], parts[1]
    if len(parts) >= 2:
        return parts[0], ", ".join(parts[1:]), ""
    return parts[0], "", ""


def _clean_line(text):
    """Drop markdown heading marks, bold marks and bullet glyphs."""
    t = re.sub(r"^\s*#{1,6}\s*", "", text)
    t = t.replace("**", "").replace("__", "")
    return t.strip().strip("*_").strip()


def _dates(text):
    """(left, start, end) when the line ends in a date range, else None.

    The range may sit in a closing parenthesis: 'Company (Jan 2019 - May 2022)'.
    An open end reads as Present. A line ending in a period is a sentence, and
    a 'Label: text' line is a note, so neither is a job entry.
    """
    t = text.rstrip(" *")
    if t.endswith("."):
        return None
    paren = re.search(r"\s*\(([^()]*)\)\s*$", t)
    if paren and DATE_RANGE.search(paren.group(1)):
        inner = paren.group(1)
        found = list(DATE_RANGE.finditer(inner))
        left = t[:paren.start()]
    else:
        found = list(DATE_RANGE.finditer(t))
        if not found:
            return None
        last = found[-1]
        # The range must close the line. A range in the middle is a sentence.
        if t[last.end():].strip(" )|\u00b7-\u2013\u2014,"):
            return None
        left = t[:found[0].start()]
    start = found[0].group("start")
    end = found[-1].group("end") or "Present"
    left = re.sub(r"[\s|\u00b7,:(\-\u2013\u2014]+$", "", left)
    if ": " in left:
        return None
    return left.strip(), start.strip(), end.strip()


_SEGMENT_SPLIT = re.compile(r"\s+[|\u00b7\u2014]\s+|\s+\u2013\s+|\s*\|\s*")


def read_role_line(text):
    """Read one line that ends in a date range.

    Returns a dict with title, company, city, state, start, end and 'segments'
    (the text parts before the dates), or None when the line carries no date
    range at its end. With two or more segments the line is a one-line entry
    ('Title | Company | City, ST | dates'); with one it is the second line of
    a two-line entry and pair_role() settles it.
    """
    t = _clean_line(text)
    got = _dates(t)
    if not got:
        return None
    left, start, end = got
    if len(left.split()) > 16:
        return None
    segs = [s.strip() for s in _SEGMENT_SPLIT.split(left) if s.strip()] if left else []
    role = {"title": "", "company": "", "city": "", "state": "",
            "start": start, "end": end, "segments": segs, "layout": ""}
    if len(segs) >= 2:
        role["title"] = segs[0]
        name, city, state = split_place(", ".join(segs[1:]))
        if not name:
            # 'Title | City, ST | dates': the place with no company.
            name = segs[1] if len(segs) > 2 else ""
        role.update(company=name, city=city, state=state, layout="one-line")
    return role


def looks_like_title(text):
    return bool(TITLE_WORDS.search(text))


def pair_role(prev, role):
    """Settle a two-line entry: `prev` is the line above the date line.

    Company first:  'Company, City, ST'  then  'Title | Mon YYYY - Mon YYYY'
    Title first:    'Title'              then  'Company, City, ST | Mon YYYY - ...'
    """
    x = role["segments"][0] if role["segments"] else ""
    p = _clean_line(prev)
    p_name, p_city, p_state = split_place(p)
    x_name, x_city, x_state = split_place(x)
    if p_state:
        first = "company"
    elif x_state:
        first = "title"
    elif looks_like_title(x) and not looks_like_title(p):
        first = "company"
    elif looks_like_title(p) and not looks_like_title(x):
        first = "title"
    elif "," in p and "," not in x:
        first = "company"
    elif "," in x and "," not in p:
        first = "title"
    else:
        first = "company"
    out = dict(role)
    if first == "company":
        out.update(company=p_name or p, city=p_city, state=p_state, title=x,
                   layout="company-first")
    else:
        out.update(title=p, company=x_name or x, city=x_city, state=x_state,
                   layout="title-first")
    return out


def roles(blks):
    """Every job entry in a block list, in order.

    blks is a list of (kind, text) as blocks() returns. Each entry comes back
    as a dict: index (of its first line), company, city, state, title, start,
    end, layout. Reads the company-first pair this skill writes, the older
    title-first pair, and the one-line form. When the document has headers,
    only sections that hold jobs are read, so a degree with dates is not a job.
    """
    has_headers = any(k == "header" for k, _t in blks)
    section = ""
    out = []
    for i, (kind, text) in enumerate(blks):
        if kind == "header":
            section = text
            continue
        if kind == "bullet":
            continue
        if has_headers and not _JOB_SECTIONS.search(section):
            continue
        r = read_role_line(text)
        if r is None:
            continue
        start = i
        if len(r["segments"]) == 1:
            prev_ok = (i > 0 and blks[i - 1][0] == "para"
                       and not read_role_line(blks[i - 1][1])
                       and len(blks[i - 1][1].split()) <= 12)
            if prev_ok:
                r = pair_role(blks[i - 1][1], r)
                start = i - 1
            else:
                name, city, state = split_place(r["segments"][0])
                if state or not looks_like_title(r["segments"][0]):
                    r.update(company=name or r["segments"][0], city=city, state=state)
                else:
                    r["title"] = r["segments"][0]
                r["layout"] = "single"
        r["index"] = start
        out.append(r)
    return out
