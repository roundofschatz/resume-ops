#!/usr/bin/env python3
"""
term_coverage.py: list the terms a job posting uses, by tier, and check a
resume against them.

The term list comes from the posting alone, so a before and an after run on
the same posting share one denominator. Every tier is reported. --top only
limits how many terms are printed per tier; the counts always cover all of them.

Tiers:
  1  stated as required, plus the job title
  2  stated as preferred, or repeated in 3 or more places in the posting
  3  everywhere else (duties, about the role)

Stdlib only.

Usage:
    python term_coverage.py posting.md
    python term_coverage.py posting.md resume.docx
    python term_coverage.py posting.md resume.json --top 25
    python term_coverage.py --composite a.md b.md c.md [--resume base.docx]
    python term_coverage.py posting.md resume.docx --employer "Acme Health"

Composite mode reads several postings for one base resume. A term's tier is the
share of postings that use it: 60% or more is Tier 1, 30 to 59% Tier 2.

What this cannot do: tell whether the candidate can honestly claim a missing
term, or tell a synonym from a miss ("electronic patient records" against
"Epic" reads as a gap). Read references/tailoring.md and sort by hand before
writing.
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docx  # noqa: E402
import detect_ats  # noqa: E402  (one list of vendor names for both scripts)

STOP = set("""
a about above after again against all am an and any are aren as at be because been
before being below between both but by can cannot could couldn did didn do does
doesn doing don down during each few for from further had hadn has hasn have haven
having he her here hers herself him himself his how i if in into is isn it its itself
just me more most mustn my myself no nor not now of off on once only or other ought
our ours ourselves out over own same shan she should shouldn so some such than that
the their theirs them themselves then there these they this those through to too
under until up very was wasn we were weren what when where which while who whom why
will with won would wouldn you your yours yourself yourselves
will able across also within without including include includes etc via per
you'll we're we'll it's you're you've we've they're role position job company team work
working works opportunity candidate candidates applicant applicants required requirements
qualifications qualification preferred responsibilities duties experience years year new
strong excellent great good best ability abilities skill skills knowledge
understanding proven track record demonstrated ensure ensuring help helping
support supporting provide providing use using used well plus must may
equal employer opportunity diversity inclusion benefits salary range
apply application resume please contact email visit website learn
environment fast paced dynamic exciting passionate driven motivated
seeking seek looking reports reporting proficiency proficient familiarity
familiar equivalent role's join successful essential central minimum maximum
related similar comparable various multiple several other others e.g i.e
in-house like get make making want wants need needs every ideal ideally percent
""".split())

# Bigrams that start with one of these are usually verb fragments
# ("lead customer", "drive go-to-market") rather than searchable terms.
LEAD_VERBS = set("""
lead leads leading drive drives driving own owns owning manage manages managing
conduct conducts conducting present presents presenting partner partners
build builds building develop develops developing create creates creating
deliver delivers delivering execute executes executing support supports
demonstrate demonstrates contribute contributes
""".split())

BOILERPLATE = re.compile(
    r"equal opportunity|reasonable accommodation|e-verify|affirmative action|"
    r"regardless of race|protected veteran|drug[- ]free|background check|"
    r"benefits package|401\(?k\)?|paid time off|dental|vision insurance|"
    r"artificial intelligence \(ai\) tool|screening score|opt[- ]out|"
    r"use of (?:ai|artificial intelligence) in (?:our )?recruiting|"
    r"we may use ai tools", re.I)

# Lines at the top of a saved posting that describe the file, not the job.
HEADER_LABEL = re.compile(
    r"^\s*(?:source|system|note|location|pay|reference|type|salary|compensation|posted|"
    r"retrieved|req(?:uisition)?(?:\s+(?:id|number))?|job\s+id)\s*:", re.I)
TITLE_LABEL = re.compile(r"^\s*(?:job\s+)?title\s*:\s*(.+)$", re.I)
COMPANY_LABEL = re.compile(r"^\s*(?:company|employer|organi[sz]ation)\s*:\s*(.+)$", re.I)

# Headings. Matched against the whole heading line once markdown, bold marks
# and a trailing colon are gone.
TIER1_HEAD = re.compile(r"""^(?:
    (?:minimum|basic|required|key|essential|core|your|job|position|role|the|must[- ]have)\s+
        qualifications?(?:\s+(?:and|&)\s+(?:skills|experience|requirements|education))?
  | qualifications?(?:\s+(?:and|&)\s+(?:skills|experience|requirements|education))?
  | (?:(?:role|job|position|minimum|basic|key|the|your)\s+)?requirements?
        (?:\s+(?:and|&)\s+qualifications?)?
  | required\s+(?:skills|experience|knowledge|qualifications)
        (?:\s*(?:,|and|&)\s*(?:skills|experience|knowledge|abilities|qualifications|education))*
  | what\s+you(?:'ll|\s+will)?\s+(?:bring|need|have)(?:\s+to\s+(?:the\s+(?:table|role)|succeed))?
  | what\s+we(?:'re|\s+are)\s+looking\s+for(?:\s+in\s+you)?
  | who\s+you\s+are | about\s+you | you\s+(?:have|bring|are)
  | must[- ]haves? | must\s+have\s+(?:skills|qualifications)
  | (?:skills|experience|knowledge)\s*(?:,|and|&)\s*(?:skills|experience|qualifications|
        education|abilities)(?:\s*(?:,|and|&)\s*\w+)?
  | education\s+(?:and|&)\s+experience
)$""", re.X)
TIER2_HEAD = re.compile(r"""^(?:
    (?:preferred|desired|desirable|additional|bonus|nice[- ]to[- ]have)\s*
        (?:qualifications?|skills?|experience|requirements?|attributes|knowledge)?
        (?:\s*(?:,|and|&)\s*(?:qualifications?|skills?|experience|knowledge|education))?
  | nice\s+to\s+haves?
  | bonus(?:\s+points)?(?:\s+if\s+you(?:\s+have|'ve\s+got|\s+bring)?(?:\s+\w+)?)?
  | (?:it'?s\s+)?a\s+plus(?:\s+if(?:\s+you(?:\s+have)?)?)?
  | pluses | extra\s+credit | even\s+better\s+if(?:\s+you(?:\s+have)?)?
  | what\s+would\s+make\s+you\s+stand\s+out
)$""", re.X)
TIER3_HEAD = re.compile(r"""^(?:
    (?:(?:key|role|main|primary|job|core|your|essential)\s+)?(?:responsibilities|duties)
        (?:\s+(?:and|&)\s+\w+)?
  | what\s+you(?:'ll|\s+will)\s+(?:do|own|be\s+doing|work\s+on|achieve)
  | (?:about\s+)?the\s+(?:role|job|position|opportunity|team)(?:\s+.*)?
  | about\s+.{1,40} | job\s+(?:purpose|summary|description|overview)
  | (?:position\s+|role\s+)?(?:overview|summary) | day[- ]to[- ]day
  | in\s+this\s+role(?:,?\s+you\s+will)? | your\s+impact | the\s+impact\s+you'll\s+have
  | what\s+does\s+this\s+role\s+look\s+like\?? | who\s+we\s+are
  | our\s+(?:company|team|mission|values) | benefits | perks
  | compensation(?:\s+(?:and|&)\s+benefits)? | work\s+model.* | travel.* | location.*
)$""", re.X)
# A sub-heading inside a list keeps the tier it sits in.
SUB_HEAD = re.compile(r"^(?:education|experience|skills|technical(?:\s+skills)?|soft\s+skills|"
                      r"certifications?|licen[sc]es?(?:\s+(?:and|&)\s+certifications?)?|knowledge|"
                      r"abilities|tools|languages)$")

TIER_NAME = {1: "TIER 1: stated as required, plus the job title",
             2: "TIER 2: stated as preferred, or repeated in 3+ places",
             3: "TIER 3: everywhere else in the posting"}
COMPOSITE_NAME = {1: "TIER 1: in 60% or more of the postings",
                  2: "TIER 2: in 30 to 59% of the postings",
                  3: "TIER 3: in fewer than 30% of the postings"}

BULLET = re.compile(r"^\s*(?:[-*\u2022\u00b7\u25aa\u25cf\u2013]|\d{1,2}[.)])\s+")


# ------------------------------------------------------------------ reading --

def read_text(path):
    if str(path).lower().endswith(".docx"):
        return "\n".join(_docx.lines(path))
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        sys.exit(f"File not found: {path}")


def apos(text):
    return text.replace("\u2019", "'").replace("\u2018", "'")


def clean_heading(line):
    s = apos(line).strip()
    s = re.sub(r"^#+\s*", "", s)
    s = s.strip("*_ ").strip()
    s = re.sub(r"\s*:\s*$", "", s).strip("*_ ").strip()
    return re.sub(r"\s+", " ", s).lower()


def heading_tier(line, after_blank=True):
    """(tier, rest) when the line is a section heading, else (None, line).

    tier is 1 or 2 for a required or preferred heading, 3 for any other
    heading (it ends the section above it), and "sub" for a sub-heading that
    keeps the current tier. rest is text after an inline "Heading: text".
    """
    raw = line.strip()
    if not raw or BULLET.match(raw):
        return None, line
    s = clean_heading(raw)
    if len(s.split()) <= 8 and len(s) <= 70:
        if TIER2_HEAD.match(s):
            return 2, ""
        if TIER1_HEAD.match(s):
            return 1, ""
        if SUB_HEAD.match(s):
            return "sub", ""
        if TIER3_HEAD.match(s):
            return 3, ""
        marked = raw.endswith(":") or raw.startswith("#") or raw.startswith("**")
        looks = raw[0].isupper() and "." not in raw.rstrip("?") and (
            raw.endswith("?") or title_case(raw))
        if marked or (after_blank and looks):
            return 3, ""
    m = re.match(r"^\s*(?:#+\s*)?\**([^:]{3,60}?)\**\s*:\s+(\S.*)$", raw)
    if m:
        head = clean_heading(m.group(1))
        for rx, tier in ((TIER2_HEAD, 2), (TIER1_HEAD, 1), (TIER3_HEAD, 3)):
            if rx.match(head):
                return tier, m.group(2)
    return None, line


SMALL = {"of", "and", "the", "for", "in", "a", "an", "to", "at", "on", "with", "&", "or", "by"}


def title_case(line):
    words = [w for w in re.findall(r"[A-Za-z][\w'-]*", line) if w.lower() not in SMALL]
    if len(words) < 2:
        return bool(words) and words[0][0].isupper()
    return sum(w[0].isupper() for w in words) >= 0.8 * len(words)


def posting_lines(text):
    """[(line, tier, is_bullet)] for each body line of a posting, in order.

    File header lines (Source:, Location:, Pay: and the like), the title line,
    boilerplate and headings are consumed here. Every other reader of a
    posting goes through this, so they agree about what is required.
    """
    tier, out, after_blank = 3, [], True
    title = posting_title(text)
    for raw in apos(text).splitlines():
        line = raw.strip()
        if not line:
            after_blank = True
            continue
        was_blank, after_blank = after_blank, False
        if HEADER_LABEL.match(line) or TITLE_LABEL.match(line) or COMPANY_LABEL.match(line):
            continue
        if title and line == title and not out:
            continue
        if BOILERPLATE.search(line):
            continue
        t, rest = heading_tier(line, after_blank=was_blank)
        if t == "sub":
            continue
        if t is not None:
            tier = t
            if not rest:
                continue
            line = rest
        is_bullet = bool(BULLET.match(line))
        out.append((BULLET.sub("", line).strip(), tier, is_bullet))
    return out


def posting_title(text):
    first = None
    for raw in apos(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        m = TITLE_LABEL.match(line)
        if m:
            return m.group(1).strip()
        if first is None and not HEADER_LABEL.match(line) and not COMPANY_LABEL.match(line):
            first = line
    if first and len(first.split()) <= 12 and not first.endswith("."):
        return first
    return None


# ------------------------------------------------------------ employer name --

# Host words that belong to a vendor without naming it. Vendor names come from
# detect_ats.VENDOR_WORDS, read as whole words inside a host word, so
# "rippling-ats" is a vendor word and "cleveland" is not.
VENDOR_HOSTS = re.compile(r"^(?:jibeapply|governmentjobs|schooljobs|applytojob|applicant-tracking|"
                          r"prismhr-hire)$")
NOT_NAME = {"www", "jobs", "job", "careers", "career", "boards", "job-boards", "apply", "recruiting",
            "hr", "com", "org", "net", "io", "co", "ai", "us", "edu", "gov", "en", "en-us", "p",
            "careers-home", "external", "portal", "attract", "ats", "eu"}


def is_vendor_label(label):
    """True for a host word that belongs to a vendor: "greenhouse", and
    "rippling-ats", where the vendor's name is one of the joined words."""
    label = label.lower()
    return bool(VENDOR_HOSTS.match(label) or detect_ats.vendor_words(label))


def _squash(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _key(label):
    k = _squash(label)
    for suf in ("careers", "career", "jobs", "inc", "corp", "llc", "hr", "group", "co"):
        if k.endswith(suf) and len(k) - len(suf) >= 4:
            k = k[:-len(suf)]
            break
    return k


def employer_names(text, extra=()):
    """The employer's own name, so it is never reported as a missing term.

    From a "Company:" line, then the posting's Source URL (the host, or the
    board path on a vendor host). Only when neither is there, the most frequent
    capitalized name in the posting.
    """
    names = [n.strip() for n in extra if n.strip()]
    body = apos(text)
    for line in body.splitlines():
        m = COMPANY_LABEL.match(line.strip())
        if m:
            names.append(m.group(1).strip())
    keys = set()
    src = re.search(r"^\s*source\s*:\s*(\S+)", body, re.I | re.M)
    if src:
        u = urlparse(src.group(1) if "//" in src.group(1) else "//" + src.group(1))
        labels = [l for l in (u.hostname or "").split(".") if l]
        vendor = any(is_vendor_label(l) for l in labels)
        tenant = [re.sub(r"^(?:globalcareers|careers|career|jobs)-", "", l) for l in labels
                  if l not in NOT_NAME and not is_vendor_label(l)
                  and not re.fullmatch(r"wd\d+|\d+", l)]
        keys.update(_key(l) for l in tenant)
        if vendor and not tenant:      # boards.greenhouse.io/acme: the name is in the path
            seg = next((s for s in u.path.split("/") if s and s.lower() not in NOT_NAME), "")
            if seg and not re.search(r"\d{3,}", seg):
                keys.add(_key(seg))
    keys.discard("")
    body_only = "\n".join(l for l in body.splitlines() if not HEADER_LABEL.match(l.strip()))
    if keys:
        runs = cap_runs(body_only)
        for run in runs:
            words = run.split()
            for i in range(len(words)):
                for j in range(i + 1, min(len(words), i + 3) + 1):
                    cand = " ".join(words[i:j])
                    if _key(cand) in keys or _squash(cand) in keys:
                        names.append(cand)
    if not names and not src:
        top = most_frequent_name(body_only)
        if top:
            names.append(top)
    out = []
    for n in names:
        if n.lower() not in (o.lower() for o in out):
            out.append(n)
    return sorted(out, key=lambda s: (-len(s), s))


CAP = re.compile(r"(?<![\w'&-])[A-Z][A-Za-z0-9&'-]*[a-z][A-Za-z0-9&'-]*")


def cap_runs(text):
    out = []
    for line in text.splitlines():
        words = [(m.group(0), m.start(), m.end()) for m in CAP.finditer(line)]
        run = []
        for w in words:
            if run and re.fullmatch(r" ", line[run[-1][2]:w[1]]):
                run.append(w)
            else:
                if run:
                    out.append(" ".join(x[0] for x in run))
                run = [w]
        if run:
            out.append(" ".join(x[0] for x in run))
    return [re.sub(r"'s$", "", r) for r in out]


def most_frequent_name(text):
    counts = Counter()
    lower = set(re.findall(r"\b[a-z][a-z-]+\b", text))
    for line in text.splitlines():
        for m in CAP.finditer(line):
            w = re.sub(r"'s$", "", m.group(0))
            before = line[:m.start()].rstrip()
            if not before or before[-1] in ".!?:;-*\u2022":
                continue
            if w.lower() in lower or w.lower() in STOP:
                continue
            counts[w] += 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[0][0] if ranked and ranked[0][1] >= 3 else None


def strip_names(text, names):
    for n in names:
        text = re.sub(r"(?<![\w-])" + re.escape(n) + r"(?:'s)?(?![\w-])", " , ", text, flags=re.I)
    return text


# ------------------------------------------------------------------- tokens --

TOKEN = re.compile(r"[A-Za-z0-9]{1,2}/[A-Za-z0-9]{1,2}(?![A-Za-z0-9])"
                   r"|[A-Za-z0-9][A-Za-z0-9+#.'&-]*[A-Za-z0-9+#]|[A-Za-z0-9]")
NUMERIC = re.compile(r"^(?:[\d.,+%$/-]+|\d+(?:st|nd|rd|th|s|k|m|x|yrs?)?\+?)$")


def tokens(text):
    """[(token, start, end)]: lowercase, possessive gone, "&" read as "and"."""
    out = []
    for m in TOKEN.finditer(apos(text)):
        t = m.group(0).lower()
        t = re.sub(r"'s$|s'$", "", t)
        out.append((t, m.start(), m.end()))
    return out


def breaker(t):
    return NUMERIC.match(t) is not None


def stem(w):
    """Crude and lenient. 'strategies' and 'strategy' land on one string;
    'managing', 'manages' and 'manage' on another."""
    w = w.lower()
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    for suf in ("ing", "ed", "es"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            w = w[:-len(suf)]
            break
    else:
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
    if len(w) > 4 and w.endswith("e"):
        w = w[:-1]
    return w


def stem_phrase(p):
    return " ".join(stem(w) for w in p.split())


def normalize(text):
    return " ".join(t for t, _s, _e in tokens(text))


def acronym_pairs(text):
    """'Advanced Life Support (ALS)' -> {'als': 'advanced life support'}."""
    out = {}
    for m in re.finditer(r"([A-Za-z][A-Za-z\s]{4,60}?)\s*\(([A-Z][A-Za-z0-9]{1,7})\)", apos(text)):
        words = normalize(m.group(1)).split()
        n = len(re.sub(r"[^A-Z]", "", m.group(2))) or len(m.group(2))
        keep, big = [], 0
        for w in reversed(words):
            if big == n:
                break
            keep.insert(0, w)
            big += w not in SMALL
        out[m.group(2).lower()] = " ".join(keep)
    return out


# -------------------------------------------------------------------- terms --

# Qualifiers that pad a requirement without naming anything.
JUNK_PHRASE = re.compile(
    r"\b(?:or\s+)?(?:an?\s+)?(?:closely\s+)?related\s+(?:field|discipline|area|degree|industry)s?\b"
    r"|\bor\s+(?:an?\s+)?equivalent(?:\s+(?:practical|work|combination\s+of))?"
    r"(?:\s+(?:education\s+(?:and|&)\s+)?experience)?\b"
    r"|\bor\s+(?:similar|comparable)\b", re.I)

# Words that are verbs or adverbs on their own: a posting's grammar, not its terms.
VERB_WORDS = set("""
identify improve establish establishing execute executing translate translating define defining
collaborate collaborating engage understand evolve evolving shape shaping set bring move balance
adapt apply communicate ensure enable enabling connect connecting turn turns act serve serving
drive grow growing guide guiding stay work align aligning oversee overseeing advance advancing
""".split())
ADVERB = re.compile(r"^[a-z-]{3,}(?:ally|ively|ously|ently|antly|ately|fully|ly)$")
KEEP_LY = {"supply", "assembly", "family", "quarterly", "monthly", "weekly", "daily", "anomaly",
           "italy", "july", "reply", "apply", "rely", "ally", "early", "only"}


def noise(t):
    return t in STOP or t in VERB_WORDS or (ADVERB.match(t) is not None and t not in KEEP_LY)


CLAUSE = re.compile(r"\s*[,()\u2022|;]\s*|\s+(?:and|or|&)\s+|\s+[-\u2013\u2014]\s+")


def segments(posting, names=None):
    """(tokens, tier) for each clause of each body line. N-grams never cross one.

    Building n-grams over the whole document produced terms like 'department
    manchester', pairs that are adjacent only because one line ended there.
    """
    if names is None:
        names = employer_names(posting)
    out = []
    title = posting_title(posting)
    lines = [(title, 1, False)] if title else []
    lines += posting_lines(posting)
    for line, tier, _b in lines:
        line = JUNK_PHRASE.sub(" , ", strip_names(line, names))
        for sent in re.split(r"(?<=[.!?;:])\s+", line):
            for clause in CLAUSE.split(sent):
                toks = [t for t, _s, _e in tokens(clause)]
                if toks:
                    out.append((toks, tier))
    return out


def title_terms(posting, names=None):
    """The job title as terms: whole, or its parts when it is long."""
    title = posting_title(posting)
    if not title:
        return []
    title = strip_names(re.sub(r"\([^)]*\)", " ", title), names or [])
    whole = normalize(title)
    parts = [normalize(p) for p in re.split(r"[,|\u2013\u2014]|\s-\s", title)]
    out = [whole] if 0 < len(whole.split()) <= 6 else []
    out += [p for p in parts if 0 < len(p.split()) <= 6]
    return sorted(set(t for t in out if t), key=lambda t: (-len(t.split()), t))


def _scan(posting, names):
    scores, tiers, seen, occ = Counter(), {}, defaultdict(set), Counter()

    def note(term, add, tier, seg_id):
        scores[term] += add
        occ[term] += 1
        tiers[term] = min(tiers.get(term, 9), tier)
        seen[term].add(seg_id)

    for seg_id, (toks, tier) in enumerate(segments(posting, names)):
        for i, t in enumerate(toks):
            if not noise(t) and t not in LEAD_VERBS and len(t) > 2 and not breaker(t):
                note(t, 1, tier, seg_id)
        for n in (2, 3):
            for i in range(len(toks) - n + 1):
                parts = toks[i:i + n]
                if any(noise(p) or len(p) < 3 or breaker(p) for p in parts):
                    continue
                if parts[0] in LEAD_VERBS or parts[0] in VERB_WORDS:
                    continue
                note(" ".join(parts), n + 1, tier, seg_id)
    return scores, tiers, seen, occ


def candidate_terms(posting, names=None):
    """term -> (score, tier, spread), from the posting alone.

    spread is how many clauses the term appears in. It breaks ties before the
    alphabet does, and 3 or more promotes a term to at least Tier 2: language
    a posting repeats is language it cares about.
    """
    if names is None:
        names = employer_names(posting)
    scores, tiers, seen, _occ = _scan(posting, names)
    out = {}
    for t, s in scores.items():
        tier = tiers[t]
        if tier == 3 and len(seen[t]) >= 3:
            tier = 2
        out[t] = (s, tier, len(seen[t]))
    for t in title_terms(posting, names):
        s, _tier, spread = out.get(t, (len(t.split()) + 1, 1, 1))
        out[t] = (s, 1, spread)
    return out


def drop_redundant(terms, occ, keep=()):
    """Hide a shorter term that never appears outside one longer term.

    Decided from the posting only, never from the resume, so the list and the
    denominator are the same on every run against the same posting.
    """
    best = defaultdict(int)
    for t in terms:
        words = t.split()
        if len(words) < 2:
            continue
        for n in range(1, len(words)):
            for i in range(len(words) - n + 1):
                sub = " ".join(words[i:i + n])
                best[sub] = max(best[sub], occ.get(t, 0))
    return {t: v for t, v in terms.items()
            if t in keep or not (t in best and best[t] >= occ.get(t, 0))}


def term_list(posting, names=None):
    """[(term, score, tier, spread)] sorted. The denominator for this posting."""
    if names is None:
        names = employer_names(posting)
    terms = candidate_terms(posting, names)
    _s, _t, _seen, occ = _scan(posting, names)
    terms = drop_redundant(terms, occ, keep=set(title_terms(posting, names)))
    return sorted(((t, s, tier, spread) for t, (s, tier, spread) in terms.items()),
                  key=lambda r: (r[2], -r[3], -r[1], r[0]))


def proper_terms(posting):
    """Terms the posting writes as a name ("Power BI", "Qualtrics"). Only these
    may match inside a longer capitalized name on the resume."""
    out = set()
    for line, _tier, _b in posting_lines(posting):
        for m in re.finditer(r"(?:[A-Z][\w&'-]*)(?:\s+[A-Z][\w&'-]*)*", line):
            before = line[:m.start()].rstrip()
            if not before or before[-1] in ".!?:;":
                continue
            out.add(normalize(m.group(0)))
    return out


def composite_terms(postings):
    """term -> (postings using it, tier, total spread) across several postings."""
    n = len(postings)
    uses, spread = Counter(), Counter()
    for p in postings:
        for term, _score, _tier, sp in term_list(p):
            uses[term] += 1
            spread[term] += sp
    out = {}
    for t, u in uses.items():
        share = u / n
        tier = 1 if share >= 0.6 else 2 if share >= 0.3 else 3
        out[t] = (u, tier, spread[t])
    return out


# ------------------------------------------------------------------- resume --

class Resume:
    """The resume as lines, each knowing its section and whether it is a
    title-case line (a job title, header or degree line), where capitals are
    style and say nothing about names."""

    def __init__(self, lines):
        self.lines = []
        for text, section in lines:
            toks = tokens(text)
            self.lines.append({
                "text": apos(text), "skills": _docx.is_skills_section(section or ""),
                "titlecase": title_case(text), "toks": toks,
                "words": [t for t, _s, _e in toks], "stems": [stem(t) for t, _s, _e in toks]})

    @classmethod
    def from_text(cls, text):
        lines, section = [], ""
        for raw in text.splitlines():
            line = raw.strip().lstrip("#").strip()
            if not line:
                continue
            if _docx.header_kind(line):
                section = line.strip(":").lower()
            lines.append((line, section))
        return cls(lines)

    @classmethod
    def load(cls, path):
        import draft_review as dr  # late import: draft_review is a sibling reader
        blocks = dr.structure(dr.load(path))
        lines = []
        for b in blocks:
            if b.kind == "role" and b.role:
                r = b.role
                lines.append((", ".join(x for x in (r.get("title"), r.get("company"), r.get("city"))
                                        if x), b.section))
            else:
                lines.append((b.text, b.section))
        return cls(lines)


def _capitalized(line, i):
    raw = line["text"][line["toks"][i][1]:line["toks"][i][2]]
    return raw[:1].isupper()


def _adjacent(line, i, j):
    return re.fullmatch(r" ", line["text"][line["toks"][i][2]:line["toks"][j][1]]) is not None


def _in_longer_name(line, i, n):
    """True when tokens i..i+n sit inside a longer capitalized name, as
    "master" does inside "Master Plan". Title-case lines are exempt."""
    if line["titlecase"]:
        return False
    if not all(_capitalized(line, k) for k in range(i, i + n)):
        return False
    left = i > 0 and _capitalized(line, i - 1) and _adjacent(line, i - 1, i)
    right = i + n < len(line["toks"]) and _capitalized(line, i + n) and _adjacent(line, i + n - 1, i + n)
    return left or right


def _count(words, line, key, proper):
    n = len(words)
    hits = 0
    seq = line[key]
    for i in range(len(seq) - n + 1):
        if seq[i:i + n] == words and (proper or not _in_longer_name(line, i, n)):
            hits += 1
    return hits


def find(term, resume, acros=None, proper=()):
    """(hits, hits outside Skills, how). Exact, then word form, then the term's
    acronym or its expansion."""
    acros = acros or {}
    is_proper = term in proper
    for words, key, how in ((term.split(), "words", ""),
                            ([stem(w) for w in term.split()], "stems", " (word-form match)")):
        hits = outside = 0
        for line in resume.lines:
            h = _count(words, line, key, is_proper)
            hits += h
            outside += 0 if line["skills"] else h
        if hits:
            return hits, outside, how
    alt = acros.get(term) or next((a for a, full in sorted(acros.items()) if full == term), None)
    if alt:
        hits = outside = 0
        for line in resume.lines:
            h = _count(alt.split(), line, "words", True)
            hits += h
            outside += 0 if line["skills"] else h
        if hits:
            return hits, outside, f" (as \"{alt}\")"
    return 0, 0, ""


# --------------------------------------------------------------------- main --

def report(rows, names_by_tier, resume, acros, proper, top, header, extra_lines=()):
    REPEAT_PROMPT = 3
    by_tier = defaultdict(lambda: {"covered": [], "missing": []})
    overused = []
    for term, score, tier, spread in rows:
        if resume is None:
            by_tier[tier]["missing"].append((term, score, spread))
            continue
        hits, outside, how = find(term, resume, acros, proper)
        if hits:
            note = how + (" (only in Skills)" if outside == 0 else "")
            by_tier[tier]["covered"].append((term, score, hits, note))
            if outside > REPEAT_PROMPT and " " not in term:
                overused.append((term, outside))
        else:
            by_tier[tier]["missing"].append((term, score, spread))

    total = len(rows)
    cov = sum(len(v["covered"]) for v in by_tier.values())
    print("=" * 68)
    if resume is None:
        print(f"{header}: {total} terms from the posting")
    else:
        print(f"{header}: {cov}/{total} terms present")
    print("=" * 68)
    for line in extra_lines:
        print(line)
    for tier in (1, 2, 3):
        block = by_tier[tier]
        n = len(block["covered"]) + len(block["missing"])
        print("\n" + "-" * 68)
        if resume is None:
            print(f"{names_by_tier[tier]}: {n} terms")
        else:
            pct = round(100 * len(block["covered"]) / n) if n else 0
            print(f"{names_by_tier[tier]}: {len(block['covered'])}/{n} covered ({pct}%)")
        print("-" * 68)
        if not n:
            print("  (none)")
            continue
        if block["missing"]:
            if resume is not None:
                print("  MISSING")
            shown = block["missing"][:top] if top else block["missing"]
            for t, s, sp in shown:
                print(f"    {s:>4}  {t}")
            if len(shown) < len(block["missing"]):
                print(f"    ... and {len(block['missing']) - len(shown)} more (raise --top to see them)")
        if block["covered"]:
            print("  COVERED")
            shown = block["covered"][:top] if top else block["covered"]
            for t, s, h, how in shown:
                print(f"    {s:>4}  {t}  ({h}x){how}")
            if len(shown) < len(block["covered"]):
                print(f"    ... and {len(block['covered']) - len(shown)} more (raise --top to see them)")

    if overused:
        print("\n" + "-" * 68)
        print("REPEATED outside Skills (4+ mentions; read them aloud, a prompt not a limit)")
        print("-" * 68)
        for t, h in sorted(overused, key=lambda x: (-x[1], x[0])):
            print(f"  {h}x  {t}")
    print("\n" + "=" * 68)
    print("The work order is the requirement check (requirement_check.py). This list")
    print("catches exact terms: a true one belongs in the bullet where the work")
    print("happened. A term the candidate cannot claim is a gap to tell them about,")
    print("never something to write around.")
    print("=" * 68)


def main():
    ap = argparse.ArgumentParser(description="Posting terms by tier, checked against a resume.")
    ap.add_argument("files", nargs="+", help="posting [resume], or several postings with --composite")
    ap.add_argument("--composite", action="store_true", help="read every file as a posting")
    ap.add_argument("--resume", help="the resume to check in composite mode")
    ap.add_argument("--employer", action="append", default=[],
                    help="another name to leave out of the terms (repeatable)")
    ap.add_argument("--top", type=int, default=0,
                    help="print at most N terms per list in each tier (counts still cover all)")
    args = ap.parse_args()

    if args.composite:
        postings = [read_text(p) for p in args.files]
        resume_path = args.resume
        comp = composite_terms(postings)
        rows = sorted(((t, u, tier, sp) for t, (u, tier, sp) in comp.items()),
                      key=lambda r: (r[2], -r[1], -r[3], r[0]))
        acros, proper = {}, set()
        for p in postings:
            acros.update(acronym_pairs(p))
            proper |= proper_terms(p)
        resume = Resume.load(resume_path) if resume_path else None
        report(rows, COMPOSITE_NAME, resume, acros, proper, args.top,
               f"COMPOSITE TERMS across {len(postings)} postings",
               ["The score column is the number of postings that use the term."])
        return 0

    if len(args.files) > 2:
        ap.error("give one posting and one resume, or use --composite")
    posting = read_text(args.files[0])
    resume = Resume.load(args.files[1]) if len(args.files) == 2 else None
    names = employer_names(posting, args.employer)
    rows = term_list(posting, names)
    extra = []
    title = posting_title(posting)
    if title:
        extra.append(f"Job title (forced into Tier 1): {title}")
    if names:
        extra.append("Employer name left out of the terms: " + ", ".join(names) +
                     ". If the posting asks for it as a skill, check that by hand.")
    else:
        extra.append("No employer name found. Pass --employer NAME to leave it out.")
    top = most_frequent_name(posting)
    if top and top.lower() not in (n.lower() for n in names):
        extra.append(f"Most frequent name in the posting: {top}. If that is the employer, "
                     f"pass --employer \"{top}\".")
    if not any(t == 1 for _l, t, _b in posting_lines(posting)):
        extra.append("No required-qualifications heading found. Tier 1 holds only the title. "
                     "Read the posting and mark its requirements by hand.")
    extra.append("Tiers come from where each term sits in the posting, not from judgment.")
    report(rows, TIER_NAME, resume, acronym_pairs(posting), proper_terms(posting), args.top,
           "TERM COVERAGE", extra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
