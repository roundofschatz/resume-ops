#!/usr/bin/env python3
"""
corpus_triage.py: turn a pile of career material into a triage report.

Reads whatever the candidate already wrote about themselves (old resumes, a
LinkedIn export, a brain dump, performance reviews) and does the mechanical
half of reading it: split it into claims, grade the evidence, find
contradictions, group duplicates, separate self-description from fact, and
suggest targets.

It does not decide anything. Everything it flags goes to a person.

Stdlib only.

Usage:
    python corpus_triage.py corpus.docx
    python corpus_triage.py corpus.txt --out triage.md
    python corpus_triage.py corpus.docx --targets 6
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docx  # noqa: E402

STOP = set("""
a an and are as at be been by for from has have i in is it its of on or that the
their they this to was were will with we you your our my me he she his her not
across into over under through been being had do does did can could would should
after before during while when where which who whom what how why all any each
more most other some such than then there these those been own same so too very
just also both few own out up down off again further once here now been
""".split())

# Words that mark a sentence as self-description rather than a fact. General
# first-person positioning only: a statement of who the writer is, what they
# believe, or how they work, with nothing in it to check.
VOICE_MARKERS = re.compile(
    r"\b(?:i am|i'm|i believe|i specialize|i thrive|i love|i bring|i help|i build|"
    r"i turn|i find|i make|passionate about|my approach|my philosophy|my passion|"
    r"my practice|my process|my method|my edge|my strength)\b", re.I)

MONEY = re.compile(r"\$\s?[\d,.]+\s?(?:[KMB]|billion|million|thousand)?\b", re.I)
# The word boundary belongs on the spelled-out form only. After "%" there is no
# word character, so a boundary there never holds and "40%" matched nothing.
PERCENT = re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|percent\b)", re.I)
# A number and the thing it counts, whatever the field. A nurse counts beds and
# admissions, a warehouse manager counts pallets, an engineer counts tickets:
# the unit is whatever word follows the figure. A bare four-digit year is a
# date, not a count.
COUNT = re.compile(
    r"(?<![\w$/-])(?!(?:19|20)\d{2}(?![\d,.]))"
    r"\d[\d,]*\+?(?:\.\d+)?\s?(?:sq\.?\s?ft|%)?\s+[a-z][a-z-]{2,}", re.I)
BARE_NUM = re.compile(r"(?<![\w$])\d[\d,]*(?:\.\d+)?(?![\w%])")

# Capitalized multi-word phrase: a proper noun candidate.
PROPER = re.compile(r"\b(?:[A-Z][A-Za-z&'\u2019.-]*\s?){1,4}\b")

# Standard credential notation, not coined names. "BSc (Hons)" is how the
# qualification is written in the UK, Ireland, Australia and elsewhere.
CREDENTIAL_PARENS = {"hons", "honors", "honours", "rn", "bsn", "msn", "np", "pa",
                     "cpa", "pe", "pmp", "mba", "phd", "md", "do", "dds", "jd",
                     "ret", "usa", "usn", "usaf", "usmc"}

COINED_TAIL = re.compile(
    r"\b(?:Model|Framework|Method|Methodology|System|Platform|Architecture|Engine|"
    r"Spectrum|Sequence|Profile|Target|Scoring|Arc|Protocol|Loop|Pyramid|Ladder|Map)\b")

# Common words that open a sentence. A capitalized word there is not a name.
LEADING_COMMON = {"the", "a", "an", "what", "let", "let's", "this", "that", "these",
                  "those", "our", "my", "their", "his", "her", "its", "your", "we",
                  "i", "it", "how", "why", "when", "where", "who", "each", "every",
                  "one", "and", "but", "so", "then", "here", "there"}

_NUM = (r"(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
        r"twenty-\w+|thirty)")
_ABOUT = r"(?:over |more than |nearly |almost |about |roughly |some )?"
# Phrases that claim a career length. "5 years" alone is any duration: a plan,
# a contract, a lease. Only these shapes say how long the career is.
CAREER_YEARS = [
    # "12 years of experience", "10+ years' nursing experience"
    re.compile(rf"\b{_ABOUT}(?P<n>{_NUM})\+?\s*years?['\u2019]?\s+(?:of\s+)?(?:[\w-]+\s+){{0,3}}?"
               r"experience\b", re.I),
    # "a 15-year career", "fifteen year nursing career"
    re.compile(rf"\b(?P<n>{_NUM})\+?[- ]year\s+(?:[\w-]+\s+){{0,2}}?career\b", re.I),
    # "a career spanning 16 years", "a career of more than 10 years"
    re.compile(rf"\bcareer\s+(?:of|spanning|covering)\s+{_ABOUT}(?P<n>{_NUM})\+?\s+years\b", re.I),
    # "nurse with 12 years in acute care", "supervisor with 11 years keeping lines running"
    re.compile(rf"\bwith\s+{_ABOUT}(?P<n>{_NUM})\+?\s+years\s+(?:in|as|leading|running|"
               r"managing|working|building|keeping|across)\b", re.I),
]
# "16 years in logistics", "8 years as a charge nurse", "10 years leading
# teams": a career length only when a career word sits close by.
YEARS_NEAR = re.compile(rf"\b{_ABOUT}(?P<n>{_NUM})\+?\s+years\s+(?:in|as|leading)\b", re.I)
TEAM_TOTAL = re.compile(r"\b(?:combined|collective|collectively|between us|together)\b", re.I)
CAREER_WORD = re.compile(r"\b(?:career|experience|professional|profession|industry|"
                         r"field)\b", re.I)

TIMES_CLAIM = re.compile(
    r"\b(?:(\d{1,2})x|(\d{1,2})|(once|twice|three|four|five|six|seven)) times?\b", re.I)

WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
           "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
           "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
           "nineteen": 19, "twenty": 20, "thirty": 30, "once": 1, "twice": 2}
_UNITS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
          "eight": 8, "nine": 9}

# Short lines with no number that the grader buries in C and D, and that are
# the content most often dropped from a finished resume.
CREDENTIAL = re.compile(
    r"\b(?:bachelor|master'?s?|mba|ph\.?\s?d|doctorate|associate of|b\.?[as]\.?|"
    r"m\.?[as]\.?|certificate|certificates|certification|certified|licen[sc]e|"
    r"licensed|accredit\w*|diploma|coursework toward|graduate of)\b", re.I)
RECOGNITION = re.compile(
    r"\b(?:award|awards|honou?rs?|best\s+\w+|ranked|winner|finalist|juried|medal|"
    r"gold|silver|prize)\b|#\d+", re.I)

# Words that group claims without naming a domain. Two bullets both measured in
# hours are not a target; two bullets both about distribution are. Used for
# grouping only: these still count as evidence everywhere else.
CLUSTER_STOP = set("""
hour hours day days week weeks month months year years quarter quarterly annual
annually daily weekly monthly time times cost costs rate rates total average
number numbers percent amount amounts budget
team teams staff people person process processes project projects program
programs work working role roles level levels group groups effort efforts
across over under within about first second third next last new old
""".split())

# A group of claims bigger than this did not come from one shared story. It
# came from a common word chaining unrelated claims together.
CLUSTER_CAP = 25

# A heading that opens with a filing code ("PROJ-2021-INTAKE") files an item.
# It is not a job title.
ITEM_ID = re.compile(r"[A-Z0-9]+(?:-[A-Z0-9]+)+")

MD_HEADING = re.compile(r"^\s*(#{1,6})\s+(.*\S)\s*$")
BULLET_START = re.compile(r"^\s*[-\u2022\u00b7*]\s+")
_SEGMENTS = re.compile(r"\s+[|\u00b7\u2014]\s+|\s+\u2013\s+|\s*\|\s*")


# ---------------------------------------------------------------- input

def read_any(path):
    if path.lower().endswith(".docx"):
        # keep_empty keeps paragraph numbering, so the line numbers in the
        # report point at the same places the candidate sees in Word.
        return "\n".join(t for _k, t in _docx.blocks(path, keep_empty=True))
    try:
        return open(path, encoding="utf-8", errors="ignore").read()
    except FileNotFoundError:
        sys.exit(f"File not found: {path}")


def clean(s):
    s = re.sub(r"\*+", "", s)
    s = s.replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip()


def to_int(word):
    w = word.lower().rstrip("+")
    if w.isdigit():
        return int(w)
    if w in WORDNUM:
        return WORDNUM[w]
    m = re.fullmatch(r"(twenty|thirty)-(\w+)", w)
    if m and m.group(2) in _UNITS:
        return WORDNUM[m.group(1)] + _UNITS[m.group(2)]
    return None


# ---------------------------------------------------------------- claims

class Claim:
    __slots__ = ("id", "line", "text", "section", "grade", "money", "pct",
                 "counts", "entities", "is_voice", "is_list", "employer", "role")

    def __init__(self, cid, line, text, section, employer="", role=""):
        self.id, self.line, self.text, self.section = cid, line, text, section
        self.employer, self.role = employer, role
        self.money = MONEY.findall(text)
        self.pct = PERCENT.findall(text)
        self.counts = COUNT.findall(text)
        self.entities = extract_entities(text)
        self.is_voice = bool(VOICE_MARKERS.search(text)) and not (self.money or self.pct)
        self.is_list = is_keyword_dump(text)
        self.grade = grade(self)


def extract_entities(text):
    out = set()
    for m in PROPER.finditer(text):
        p = m.group(0).strip(" .,;:")
        if len(p) < 3:
            continue
        words = p.split()
        # A short all-caps token is an acronym, and acronyms are how licensed and
        # technical fields name things: WMS, CNC, EMR, ALS, PLC, HVAC, GAAP.
        if len(words) == 1 and re.fullmatch(r"[A-Z]{2,6}", words[0]):
            out.add(p)
            continue
        if len(words) == 1 and (words[0].lower() in STOP or len(words[0]) < 4):
            continue
        # A single capitalized word at the start of the text is just the
        # first word of the sentence.
        if len(words) == 1 and m.start() == 0:
            continue
        out.add(p)
    return out


def is_keyword_dump(text):
    """A skills list is not a claim. Many separators, few verbs, no sentence."""
    verbs = len(re.findall(r"\b(?:led|built|ran|wrote|won|grew|cut|designed|created|"
                           r"launched|managed|delivered|shipped|drove|founded|invented|"
                           r"authored|developed|reversed|produced)\b", text, re.I))
    seps = text.count("\u00b7") + text.count(" | ") + text.count(";")
    if seps >= 4:
        return verbs <= 1
    # A comma-separated list with no verb and no sentence break.
    if text.count(",") >= 5 and verbs == 0 and not re.search(r"[.!?]\s", text):
        return True
    return False


BEFORE_AFTER = re.compile(
    r"\bfrom\s+[^,.;]{0,30}?\d[\d,.]*\s?%?[^,.;]{0,20}?\bto\s+[^,.;]{0,30}?\d"
    r"|\b\d[\d,.]*\s?%?\s*(?:to|\u2192|->)\s*\d[\d,.]*\s?%?", re.I)


def grade(c):
    """A: number and a named thing. B: one of the two. C: specific, no anchor.
    D: assertion only."""
    if c.is_list:
        return "L"
    has_num = bool(c.money or c.pct or c.counts)
    # A before-and-after pair counts as a named thing: it is a specific,
    # checkable outcome. Without this only work with brand names could reach A,
    # and "cut unplanned downtime from 9 hours to 2 per week" graded B.
    has_ent = bool(c.entities) or bool(BEFORE_AFTER.search(c.text))
    if has_num and has_ent:
        return "A"
    if has_num or (has_ent and len(c.text.split()) > 8):
        return "B"
    if c.is_voice:
        return "D"
    return "C" if len(c.text.split()) > 6 else "D"


# ---------------------------------------------------------------- sections and roles

def section_header(s):
    """The header text if this cleaned line is a section header, else None.

    A header is a whole line of at most 8 words that does not end in a period,
    has no quotes in it, and has no colon in the middle. Then it must be a
    known header or mostly capital letters. A quoted all-caps phrase inside a
    longer line is not a header.
    """
    if not s or len(s.split()) > 8 or s.endswith("."):
        return None
    if re.search(r"[\"\u201c\u201d]", s):
        return None
    if ":" in s.rstrip(":"):
        return None
    if _docx.is_role_line(s):
        return None
    if _docx.header_kind(s):
        return s.strip(":")
    letters = [ch for ch in s if ch.isalpha()]
    if letters and len(s) < 60 and sum(ch.isupper() for ch in letters) / len(letters) > 0.7:
        return s.strip(":")
    return None


def role_label(r):
    """'Title | Company, City, ST | Start - End', leaving out empty parts."""
    where = ", ".join(p for p in (r["company"], r["city"], r["state"]) if p)
    dates = f"{r['start']} - {r['end']}" if r.get("start") else ""
    return " | ".join(p for p in (r["title"], where, dates) if p)


def _heading_role(text):
    """A markdown heading read as a job, or None.

    '### Title | Company | City, ST | Mon YYYY - Mon YYYY' with separators, or
    '### Company (Mon YYYY - Mon YYYY)'. A heading with no dates is a job only
    when it names a place: '### Charge Nurse | Acme Health, Leeds, UK'.
    """
    r = _docx.read_role_line(text)
    if r is not None and r["segments"] and ITEM_ID.fullmatch(r["segments"][0]):
        return None
    if r is not None:
        if len(r["segments"]) == 1:
            seg = r["segments"][0]
            name, city, state = _docx.split_place(seg)
            if state or not _docx.looks_like_title(seg):
                r.update(company=name or seg, city=city, state=state)
            else:
                r["title"] = seg     # '### Staff Nurse, Jun 2014 - Feb 2019'
        return r if (r["company"] or r["title"]) else None
    body = _docx._clean_line(text)
    segs = [s.strip() for s in _SEGMENTS.split(body) if s.strip()]
    if segs and ITEM_ID.fullmatch(segs[0]):
        return None
    if len(segs) >= 2:
        name, city, state = _docx.split_place(", ".join(segs[1:]))
        if state:
            return {"title": segs[0], "company": name or segs[1], "city": city,
                    "state": state, "start": "", "end": "", "segments": segs}
    return None


def find_roles(lines):
    """Job entries written as plain lines (not markdown headings).

    Returns ({line index: role}, {line indexes that belong to a role below}).
    Reads the company-first pair, the title-first pair and the one-line form
    through the shared reader in _docx.py.
    """
    found, used = {}, set()
    prev = None
    for idx, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        if BULLET_START.match(s):
            prev = None
            continue
        if MD_HEADING.match(s):
            prev = idx
            continue
        r = _docx.read_role_line(s)
        if r is None:
            prev = idx
            continue
        if len(r["segments"]) == 1:
            p = lines[prev].strip() if prev is not None else ""
            pairable = (p and not MD_HEADING.match(p) and prev not in found
                        and len(p.split()) <= 12 and not p.endswith(".")
                        and not section_header(clean(p)))
            if pairable:
                r = _docx.pair_role(p, r)
                used.add(prev)
            else:
                seg = r["segments"][0]
                name, city, state = _docx.split_place(seg)
                if state or not _docx.looks_like_title(seg):
                    r.update(company=name or seg, city=city, state=state)
                else:
                    r["title"] = seg
        found[idx] = r
        prev = idx
    return found, used


def atomize(text):
    lines = text.splitlines()
    roles_at, role_parts = find_roles(lines)
    claims, section, cid = [], "(top)", 0
    employer, role, role_level = "", "", None
    pending_company = ""   # a '## Company' heading with no dates
    for i, raw in enumerate(lines, 1):
        idx = i - 1
        s = clean(raw)
        if not s or idx in role_parts:
            continue

        md = MD_HEADING.match(raw)
        if md:
            level, head = len(md.group(1)), clean(md.group(2))
            if role_level is not None and level > role_level:
                section = head          # a part of the job above: same employer
                continue
            r = _heading_role(md.group(2))
            if r:
                if not r["company"] and pending_company:
                    r["company"] = pending_company
                employer, role, role_level = r["company"], role_label(r), level
                section = role
            else:
                employer, role, role_level = "", "", None
                section = head
                known = _docx.header_kind(head) or head.lower().startswith("part ")
                pending_company = "" if known or len(head.split()) > 6 else head
            continue

        if idx in roles_at:
            r = roles_at[idx]
            if not r["company"] and pending_company:
                r["company"] = pending_company
            employer, role, role_level = r["company"], role_label(r), None
            section = role
            continue

        hdr = section_header(s)
        if hdr:
            section, employer, role, role_level = hdr, "", "", None
            continue

        body = re.sub(r"^[-\u2022\u00b7*]\s*", "", s)
        # Split long paragraphs into sentences; keep bullets whole.
        chunks = [body] if raw.strip().startswith(("-", "\u2022", "*")) else \
            [c.strip() for c in re.split(r"(?<=[.!?])\s+(?=[A-Z])", body)]
        for ch in chunks:
            if len(ch.split()) < 4:
                continue
            cid += 1
            claims.append(Claim(cid, i, ch, section, employer, role))
    return claims


# ---------------------------------------------------------------- checks

def career_years(text):
    """Every career-length claim in the text, as a Counter of years."""
    found = Counter()
    for line in text.splitlines():
        spans = {}
        for pat in CAREER_YEARS:
            for m in pat.finditer(line):
                # "35 years combined experience" is a team total, not a career.
                if TEAM_TOTAL.search(m.group(0)):
                    continue
                spans[m.start("n")] = m.group("n")
        for m in YEARS_NEAR.finditer(line):
            window = line[max(0, m.start() - 80): m.end() + 80]
            if CAREER_WORD.search(window):
                spans[m.start("n")] = m.group("n")
        for n in spans.values():
            v = to_int(n)
            if v and 1 <= v <= 60:
                found[v] += 1
    return found


def global_conflicts(text):
    """Career-level numbers stated more than one way."""
    out = []
    yrs = career_years(text)
    if len(yrs) > 1:
        out.append(("Years of experience", dict(sorted(yrs.items()))))

    tms = Counter()
    for m in TIMES_CLAIM.finditer(text):
        v = m.group(1) or m.group(2) or WORDNUM.get((m.group(3) or "").lower())
        if v and 1 <= int(v) <= 12:
            tms[int(v)] += 1
    if len(tms) > 1:
        out.append(("\"N times\" claims (practice builds, launches, and so on)",
                    dict(sorted(tms.items()))))
    return out


def _groups(ids, pairs, threshold):
    """Union-find over the claim pairs that share at least `threshold`."""
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b), n in pairs.items():
        if n >= threshold and a in parent and b in parent:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
    groups = defaultdict(list)
    for i in ids:
        groups[find(i)].append(i)
    return [g for g in groups.values() if len(g) >= 2]


def dup_clusters(all_claims, min_shared=2, cap=CLUSTER_CAP):
    """Group claims that name the same things. Catches the same event told
    twice in different words, which string similarity misses.

    Returns (groups, oversized). A group bigger than `cap` is split by asking
    for more shared names; what is still too big is dropped. `oversized`
    counts the groups that were too big, so the report can say so.
    """
    claims = [c for c in all_claims if not c.is_list]
    by_ent = defaultdict(set)
    for c in claims:
        for e in c.entities:
            by_ent[e].add(c.id)
    idx = {c.id: c for c in claims}
    pairs = Counter()
    for e, ids in by_ent.items():
        if len(ids) < 2 or len(ids) > 12:
            continue
        # A name in two or three claims is distinctive: a client or a project,
        # not a common word. Two claims sharing one are usually one story.
        weight = 2 if len(ids) <= 3 else 1
        ids = sorted(ids)
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                pairs[(ids[a], ids[b])] += weight

    linked = sorted({x for pair, n in pairs.items() if n >= min_shared for x in pair})
    todo = [(g, min_shared) for g in _groups(linked, pairs, min_shared)]
    final = []
    oversized = sum(1 for g, _t in todo if len(g) > cap)
    while todo:
        members, threshold = todo.pop()
        if len(members) <= cap:
            final.append(members)
        elif threshold < min_shared + 3:
            todo.extend((g, threshold + 1) for g in _groups(members, pairs, threshold + 1))

    out = []
    for members in final:
        cs = [idx[m] for m in sorted(members)]
        roles = {c.role or c.section for c in cs}
        nums = set()
        for c in cs:
            nums |= set(x.strip() for x in c.money + c.pct)
        out.append({
            "claims": cs,
            "cross_section": len(roles) > 1,
            "numeric_conflict": len(nums) > 1,
            "numbers": sorted(nums),
        })
    out.sort(key=lambda g: (not g["numeric_conflict"], not g["cross_section"], -len(g["claims"])))
    return out, oversized


def _strip_leading(name):
    words = name.split()
    while words and words[0].lower().strip("'") in LEADING_COMMON:
        words = words[1:]
    return " ".join(words)


def _is_name_like(phrase):
    """At least half the longer words capitalized, like a name or a title."""
    words = [w for w in re.findall(r"[A-Za-z][\w'-]*", phrase) if len(w) > 3]
    if not words:
        return False
    return sum(w[0].isupper() for w in words) * 2 >= len(words)


def coined_names(claims, skip=()):
    """Internal names a recruiter will never search for.

    A lone capitalized word is never reported: it is a first name, the first
    word of a sentence, or an ordinary noun. `skip` holds names known to be
    something else, like the employers.
    """
    skip_l = [s.lower() for s in skip if s]
    hits = Counter()
    where = defaultdict(set)

    def add(name, cid):
        name = _strip_leading(name.strip(" .,;:!?"))
        if len(name.split()) < 2:
            return
        low = name.lower()
        if any(low in s for s in skip_l):
            return
        hits[name] += 1
        where[name].add(cid)

    for c in claims:
        quoted = list(re.finditer(r"[\"\u201c]([A-Z][^\"\u201c\u201d\n]{2,60}?)[\"\u201d]", c.text))
        # A single quote only counts as a quote mark when no letter touches it
        # on the outside, so the apostrophe in "Let's" or "What's" is not one.
        quoted += list(re.finditer(r"(?<!\w)'([A-Z][^'\n]{2,60}?)'(?!\w)", c.text))
        for m in quoted:
            q = m.group(1)
            if len(q.split()) <= 6 and not q.rstrip().endswith(".") and _is_name_like(q):
                add(q, c.id)
        for e in c.entities:
            if COINED_TAIL.search(e):
                add(e, c.id)
        for m in re.finditer(r"\(([A-Z][A-Za-z]{1,5}(?:/[A-Z][A-Za-z]{1,4})?)\)", c.text):
            # references/document.md tells the candidate to write an
            # acronym in both forms: "Advanced Life Support (ALS)". An acronym
            # spelled out right before the bracket is a definition, not a
            # coined name. Nor is standard credential notation, or a
            # capitalized word in brackets.
            acro = m.group(1)
            if acro.lower() in CREDENTIAL_PARENS:
                continue
            if sum(ch.isupper() for ch in acro) < 2:
                continue
            before = c.text[:m.start()].rstrip()
            initials = "".join(w[0] for w in re.findall(r"[A-Za-z]+", before)[-len(acro):])
            if initials.upper() == acro.upper():
                continue
            if any(acro.lower() in s for s in skip_l):
                continue
            hits[acro] += 1
            where[acro].add(c.id)
    return [(n, k, sorted(where[n])[:4]) for n, k in hits.most_common()]


def credentials_and_recognitions(text):
    """Sweep the raw text, not the claim list. These lines carry no number, so
    the grader ranks them low and they vanish under everything else."""
    out = []
    for i, raw in enumerate(text.splitlines(), 1):
        s = clean(raw)
        if len(s) < 6:
            continue
        # A bare section header ("Awards", "Certifications") is not a credential.
        if _docx.header_kind(s):
            continue
        kind = "credential" if CREDENTIAL.search(s) else ("recognition" if RECOGNITION.search(s) else None)
        if kind:
            out.append((i, kind, s))
    return out


def phrases(text):
    """Significant words and the short phrases they sit in.

    A target is a vocabulary domain ("distribution", "triage", "entitlement"),
    not a repeated phrase. Well-written bullets do not repeat phrasing, so
    requiring an exact shared phrase found nothing on real material.
    """
    toks = [t for t in re.sub(r"[^a-z0-9 -]", " ", text.lower()).split() if t]
    # Split hyphenated compounds as well as keeping them whole: "cross-dock"
    # and "dock-to-stock" are the same domain.
    units = list(toks)
    for t in toks:
        if "-" in t:
            units.extend(p for p in t.split("-") if p)
    out = [t for t in units if len(t) >= 4 and t not in STOP and t not in CLUSTER_STOP]
    for n in (2, 3):
        for i in range(len(toks) - n + 1):
            g = toks[i:i + n]
            if any(w in STOP or len(w) < 3 for w in g):
                continue
            out.append(" ".join(g))
    return out


def employer_of(section):
    """The employer out of a role line or a section label.

    Reads 'Title | Company, City, ST | dates', 'Title | Company | City, ST |
    dates', 'Title | Company, City - dates', and the company-first date line
    'Company, City, ST | Mon YYYY - Mon YYYY'. Never returns a month or a year.
    """
    if "|" not in section:
        return ""
    segs = []
    for seg in section.split("|"):
        seg = seg.strip()
        # Drop a date range, or a lone trailing year, from the segment.
        seg = _docx.DATE_RANGE.sub("", seg)
        seg = re.sub(r"(?:\s[-\u2013\u2014]\s*|,\s*|\s)(?:19|20)\d{2}\s*$", "", seg)
        seg = seg.strip(" .\u00b7-\u2013\u2014,")
        if seg and not re.fullmatch(r"[\W\d]*", seg):
            segs.append(seg)
    if not segs:
        return ""
    if len(segs) == 1:
        name, _city, state = _docx.split_place(segs[0])
        if state or "," in segs[0] or not _docx.looks_like_title(segs[0]):
            return (name or segs[0])[:40]
        return ""
    name, _city, _state = _docx.split_place(segs[1])
    return (name or segs[1]).split(",")[0].strip()[:40]


def targets(claims, k=5):
    """Greedy set-cover over the strong-evidence claims. Weight by evidence and
    by recency (claims earlier in the file are taken as more recent)."""
    strong = [c for c in claims if c.grade in ("A", "B") and not c.is_voice and not c.is_list]
    if not strong:
        return []
    order = {c.id: i for i, c in enumerate(strong)}
    n = max(1, len(strong))
    wt = {c.id: (2.0 if c.grade == "A" else 1.0) * (1.0 + 0.6 * (1 - order[c.id] / n))
          for c in strong}

    pool = {c.id: set(phrases(c.text)) for c in strong}
    idx = {c.id: c for c in strong}
    remaining = set(pool)
    out = []
    dead = set()
    for _ in range(k):
        score = Counter()
        for cid in remaining:
            for p in pool[cid]:
                if p not in dead:
                    score[p] += wt[cid]
        if not score:
            break
        # Walk down the ranking rather than stopping at the first phrase that
        # does not group, so one unshared top phrase cannot end the analysis.
        top, members = None, []
        for cand, _s in score.most_common():
            m = [cid for cid in remaining if cand in pool[cid]]
            if len(m) >= 2:
                top, members = cand, m
                break
            dead.add(cand)
        if top is None:
            break
        sub = Counter()
        for cid in members:
            for p in pool[cid]:
                sub[p] += wt[cid]
        label = [p for p, _ in sub.most_common(6)]
        cs = [idx[c] for c in sorted(members, key=lambda x: -wt[x])]
        employers = {c.employer or employer_of(c.section) for c in cs}
        employers.discard("")
        newest = min((order[c.id] for c in cs), default=999)
        out.append({
            "terms": label,
            "claims": cs,
            "weight": round(sum(wt[c] for c in members), 1),
            "employers": sorted(employers),
            "a_count": sum(1 for c in cs if c.grade == "A"),
            "recency_rank": newest,
        })
        remaining -= set(members)
    out.sort(key=lambda t: -t["weight"])
    return out


# ---------------------------------------------------------------- report

def report(claims, text, k):
    L = []
    A = [c for c in claims if c.grade == "A"]
    B = [c for c in claims if c.grade == "B"]
    C = [c for c in claims if c.grade == "C"]
    D = [c for c in claims if c.grade == "D"]
    LST = [c for c in claims if c.grade == "L"]
    voice = [c for c in claims if c.is_voice]
    employers = sorted({c.employer for c in claims if c.employer})

    lines_in = len(text.splitlines())
    L.append("# Corpus triage\n")
    L.append(f"{len(text.split()):,} words and {lines_in:,} lines in. "
             f"{len(claims)} claims out. Last line read: {lines_in:,}.\n")
    L.append("The script read every line. Now read the file yourself, start to end, and check "
             "your last line against that number.\n")
    if employers:
        shown = ", ".join(employers[:12]) + (", ..." if len(employers) > 12 else "")
        L.append(f"Employers found: {len(employers)} ({shown}).\n")
    else:
        L.append("Employers found: 0. No job entries were recognized, so every target below "
                 "will read as one employer. Check how the jobs are written.\n")
    L.append("Nothing here is decided. Everything below goes to the candidate.\n")

    L.append("## Evidence grades\n")
    L.append("| Grade | Meaning | Count |")
    L.append("|---|---|---|")
    L.append(f"| A | number **and** a named thing | {len(A)} |")
    L.append(f"| B | one of the two | {len(B)} |")
    L.append(f"| C | specific, nothing to check it against | {len(C)} |")
    L.append(f"| D | assertion only | {len(D)} |")
    L.append(f"| L | keyword list, not a claim | {len(LST)} |")
    L.append("")
    L.append(f"A resume is built from grade A and B claims: **{len(A) + len(B)} claims** here "
             f"({len(A)} A, {len(B)} B). How many of them fit is the builder's call.\n")

    gc = global_conflicts(text)
    L.append("## Contradictions: answer these first\n")
    if gc:
        L.append("Career-level numbers stated more than one way. Every document "
                 "built later inherits whichever one gets picked.\n")
        for label, counts in gc:
            detail = ", ".join(f"**{v}** ({n}x)" for v, n in counts.items())
            L.append(f"- **{label}:** {detail}")
        L.append("")
    else:
        L.append("None found at career level.\n")

    dups, oversized = dup_clusters(claims)
    conflicted = [g for g in dups if g["numeric_conflict"] or g["cross_section"]]
    L.append("## Same thing said twice\n")
    if oversized:
        L.append(f"{oversized} group(s) had more than {CLUSTER_CAP} claims. A group that big "
                 "comes from a common word linking unrelated claims, not from one story told "
                 "twice, so it was split into smaller groups where the claims share more, and "
                 "the rest was left out.\n")
    if conflicted:
        L.append("Claims naming the same people, clients, or projects. A group "
                 "spanning two roles, or carrying two different numbers, may be a "
                 "live error.\n")
        for g in conflicted[:12]:
            flags = []
            if g["numeric_conflict"]:
                flags.append(f"**different numbers: {', '.join(g['numbers'][:12])}**")
            if g["cross_section"]:
                flags.append("**spans more than one role**")
            L.append(f"### Group of {len(g['claims'])}: {' / '.join(flags)}")
            for c in g["claims"][:4]:
                L.append(f"- `#{c.id}` *{c.section[:48]}*: {c.text[:190]}")
            L.append("")
    else:
        L.append("No conflicting groups found.\n")

    coined = coined_names(claims, skip=employers)
    L.append("## Internal names: translate or drop\n")
    if coined:
        L.append(f"{len(coined)} names found. A recruiter searches for none of them. "
                 "Each needs a plain-language label; the name itself goes in a side "
                 "column for interviews.\n")
        L.append("| Name | Times used | Plain-language label |")
        L.append("|---|---|---|")
        for n, cnt, _ids in coined[:30]:
            L.append(f"| {n} | {cnt} | _______ |")
        L.append("")
    else:
        L.append("None found.\n")

    L.append("## Self-description: not resume material\n")
    L.append(f"{len(voice)} lines are self-description with nothing to check. They do "
             "not belong on a resume. They are parked here so they stay out of the claims "
             "list and do not get recycled into bullets.\n")
    for c in voice[:6]:
        L.append(f"- `#{c.id}` {c.text[:150]}")
    if len(voice) > 6:
        L.append(f"- _...and {len(voice) - 6} more_")
    L.append("")

    ln = targets(claims, k)
    L.append("## Candidate targets\n")
    L.append("Greedy grouping over grade A and B claims, weighted by evidence and "
             "recency. **This is the corpus half only.** It cannot see how many jobs "
             "exist for a target or what they pay. Score each target against live postings "
             "before choosing: see `references/intake.md`.\n")
    L.append("Watch the employer count. Proof at one employer is an anecdote. "
             "Proof at three is a capability, and it is what makes a target defensible.\n")
    if not ln:
        L.append("**No targets grouped.** Nothing is wrong with the candidate. "
                 f"There are {len(A) + len(B)} grade A and B claims and no word is shared "
                 "by two or more of them, which grouping needs.\n")
        L.append("This is a corpus problem, not a targeting problem. Go back to the "
                 "material: ask for older resumes, project write-ups, reviews, anything "
                 "written down. If there is nothing more, run the interview path in "
                 "`references/intake.md` and choose the target with the "
                 "candidate directly, scored against live postings per "
                 "`references/intake.md`.\n")
    for i, t in enumerate(ln, 1):
        rep = len(t["employers"])
        rep_note = (f"**repeated across {rep} employers**" if rep >= 2
                    else "**one employer only: an anecdote, not a capability**")
        L.append(f"### Target {i}: weight {t['weight']} \u00b7 {len(t['claims'])} claims \u00b7 "
                 f"{t['a_count']} grade A \u00b7 {rep_note}")
        L.append(f"Terms: {', '.join(t['terms'])}")
        if t["employers"]:
            L.append(f"Employers: {', '.join(t['employers'])}")
        L.append("")
        for c in t["claims"][:5]:
            L.append(f"- `#{c.id}` [{c.grade}] {c.text[:170]}")
        L.append("")

    cr = credentials_and_recognitions(text)
    L.append("## Credentials and recognitions: check every one\n")
    L.append("Swept from the raw text, not the graded claims. These lines carry no number, "
             "so the grader ranks them weak and they disappear under the stronger-looking "
             "claims. They are also the content most often dropped from a finished resume. "
             "The sweep is loose on purpose: a false hit costs a glance, a missed "
             "certificate costs a credential.\n")
    if cr:
        L.append("| Line | Kind | Text |")
        L.append("|---|---|---|")
        for i, kind, s in cr[:60]:
            L.append(f"| {i} | {kind} | {s[:150]} |")
        if len(cr) > 60:
            L.append(f"\n_...and {len(cr) - 60} more._")
        L.append("")
    else:
        L.append("None found. If the candidate holds a degree, a license or an award, it is "
                 "not in this file. Ask.\n")

    L.append("## Strongest evidence, by section\n")
    by_sec = defaultdict(list)
    for c in A + B:
        by_sec[c.section].append(c)
    for sec, cs in by_sec.items():
        cs.sort(key=lambda c: (c.grade, -len(c.text)))
        L.append(f"### {sec[:70]}")
        for c in cs[:6]:
            L.append(f"- `#{c.id}` [{c.grade}] {c.text[:170]}")
        L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="Turn career material into a triage report.")
    ap.add_argument("corpus")
    ap.add_argument("--out", default=None)
    ap.add_argument("--targets", type=int, default=5)
    args = ap.parse_args()

    text = read_any(args.corpus)
    claims = atomize(text)
    if not claims:
        sys.exit("No claims found. Is the file empty?")
    out = report(claims, text, args.targets)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(out)
        print(f"Wrote {args.out} ({len(out.split())} words)")
    else:
        print(out)


if __name__ == "__main__":
    main()
