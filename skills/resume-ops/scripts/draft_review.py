#!/usr/bin/env python3
"""
draft_review.py: read a draft against the writing rules before the file is built.

parse_check, widow_check and build_resume catch mechanical faults. The writing
rules were left to discipline, and discipline is what fails on the twentieth
bullet of a long session.

Two levels:

  FAIL    a settled rule is broken. Fix the line.
  REVIEW  read the line again. Some of these are right as written.

A REVIEW flag is a prompt, not a defect. Changing good copy to clear one is a
worse failure than the flag. Read the line, decide, move on.

What no script can see: whether the candidate claims the level they worked at,
whether a stranger gets the line on one read, and whether any writer could
have written it about anyone. Those three decide the document.

Reads the v2 source JSON (role blocks carry fields, not text), a .docx, or a
plain .txt/.md resume. In a .docx a role is two lines, "Company, City, ST" and
"Title | Mon YYYY - Mon YYYY"; those lines are read as the role, never as prose.

A summary says in simpler form what the bullets below prove, so a summary
claim that repeats a role is the point. What gets flagged is a summary
sentence copied from a bullet word for word (REVIEW). A career total the
candidate confirmed, listed under "career_totals" in the JSON source, may sit
in the summary with no single role behind it.

Stdlib only.

Usage:
    python draft_review.py resume.json
    python draft_review.py resume.docx
"""

import difflib
import json
import re
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docx  # noqa: E402

WORD_CEILING = 25
SUMMARY_WORDS = (45, 75)
COPY_RUN = 8        # words in a row a summary sentence shares with one bullet
COPY_SHARE = 0.8    # or this share of the sentence's words, in order, from one bullet
COPY_MIN_WORDS = 6  # shorter sentences are not checked for copying

# ---------------------------------------------------------------- loading --

MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
DATE = r"(?:%s)[a-z]*\.?\s+\d{4}" % MONTHS
END = r"(?:%s|Present|Current|Now)" % DATE
DATES_LINE = re.compile(
    r"^(?P<left>.+?)\s*\|\s*(?P<start>%s)\s*(?:[-\u2013\u2014]+|to)\s*(?P<end>%s)\s*$"
    % (DATE, END), re.I)
PLACE_LINE = re.compile(r"^(?P<company>.+?),\s*(?P<city>[^,|]+),\s*(?P<state>[A-Z]{2})\s*$")

# Kinds that are prose but carry no special rule. A .docx cannot say "this
# paragraph is the headline", so both paths collapse them the same way.
PLAIN_KINDS = {"name", "headline", "contact", "earlier", "title", "meta", "label"}


def role_block(title, company, city="", state="", start="", end=""):
    meta = {"title": title.strip(), "company": company.strip(), "city": city.strip(),
            "state": state.strip(), "start": start.strip(), "end": end.strip()}
    return ("role", f"{meta['title']} @ {meta['company']}", meta)


def role_meta(block):
    """The role's fields, from the block's meta or parsed from its text."""
    if len(block) > 2 and block[2]:
        return block[2]
    text = block[1]
    m = DATES_LINE.match(text)
    if m:
        return {"title": m.group("left"), "company": "", "start": m.group("start"),
                "end": m.group("end"), "city": "", "state": ""}
    title, _, company = text.partition(" @ ")
    return {"title": title, "company": company, "start": "", "end": "", "city": "", "state": ""}


def text_blocks(text):
    """A plain-text or markdown resume as (kind, text) blocks."""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            out.append(("header", line.lstrip("#").strip()))
        elif re.match(r"^[-*\u2022\u00b7\u25aa\u25cf]\s+", line):
            out.append(("bullet", re.sub(r"^[-*\u2022\u00b7\u25aa\u25cf]\s+", "", line)))
        else:
            out.append((_docx.header_kind(line) or "para", line))
    return out


def collapse_roles(blocks):
    """Turn each role's two lines into one role block.

    Company first ("Company, City, ST" then "Title | dates") is the default
    layout. The older title-first layout ("Title" then "Company, City, ST |
    dates") is read too, so an existing resume still parses.
    """
    out = []
    for b in blocks:
        kind, text = b[0], b[1]
        m = DATES_LINE.match(text) if kind in ("para", "header") else None
        if not m:
            out.append(b)
            continue
        left = m.group("left").strip()
        place = PLACE_LINE.match(left)
        prev = out[-1] if out and out[-1][0] in ("para", "header") else None
        if place:                       # title first: the dates sit on the company line
            title = ""
            if prev and prev[0] == "para" and not PLACE_LINE.match(prev[1]):
                title = out.pop()[1]
            out.append(role_block(title, place.group("company"), place.group("city"),
                                  place.group("state"), m.group("start"), m.group("end")))
            continue
        company, city, state = "", "", ""
        if prev:
            pm = PLACE_LINE.match(prev[1])
            if pm:
                out.pop()
                company, city, state = pm.group("company"), pm.group("city"), pm.group("state")
        out.append(role_block(left, company, city, state, m.group("start"), m.group("end")))
    return out


def load(path):
    """The same blocks from .json, .docx, .txt or .md."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            sys.exit(f"Cannot read {path}: {e}")
        raw = []
        for b in data.get("blocks", []):
            kind = b.get("kind", "para")
            if kind == "role":
                raw.append(role_block(b.get("title", ""), b.get("company", ""), b.get("city", ""),
                                      b.get("state", ""), b.get("start", ""), b.get("end", "")))
            else:
                raw.append(("para" if kind in PLAIN_KINDS else kind, b.get("text", "") or ""))
    elif suffix == ".docx":
        raw = list(_docx.blocks(p))
    else:
        try:
            raw = text_blocks(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError as e:
            sys.exit(f"Cannot read {path}: {e}")
    return collapse_roles(raw)


def load_totals(path):
    """The confirmed career totals a JSON source lists under "career_totals".
    A .docx or text file cannot carry them, so it has none."""
    p = Path(path)
    if p.suffix.lower() != ".json":
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    totals = data.get("career_totals", []) if isinstance(data, dict) else []
    return [t for t in totals if isinstance(t, str) and t.strip()] if isinstance(totals, list) else []


# ------------------------------------------------------------- structure --

Blk = namedtuple("Blk", "n kind text section role")


def norm_header(text):
    return text.strip().strip(":").strip().lower()


def is_summary(sec):
    return sec.startswith("summ") or sec in (
        "profile", "professional summary", "executive summary", "career summary",
        "professional profile", "summary of qualifications")


def is_experience(sec):
    return "experience" in sec or "employment" in sec or sec in ("work history", "career history")


def is_skills(sec):
    return _docx.is_skills_section(sec)


def is_education(sec):
    return sec.startswith("educ")


def is_certs(sec):
    return "certif" in sec or "licen" in sec


def structure(blocks):
    """Each block with its section and, under Experience, the role above it."""
    out, sec, role = [], "", None
    for n, b in enumerate(blocks, 1):
        kind, text = b[0], b[1]
        if kind == "header":
            sec, role = norm_header(text), None
        elif kind == "role":
            role = role_meta(b)
        out.append(Blk(n, kind, text, sec, role if kind != "header" else None))
    return out


def sections(blocks):
    """(kind, text, section) for each block. Kept for callers of v1.6."""
    return [(b.kind, b.text, b.section) for b in structure(blocks)]


def role_label(role):
    if not role:
        return "role"
    if role.get("company"):
        return f"{role.get('title', '')} @ {role['company']}"
    return role.get("title", "") or "role"


# ------------------------------------------------------------ text tools --

QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'})


def plain(text):
    """Curly quotes read as straight ones. One character for one, so match
    positions do not move."""
    return text.translate(QUOTES)


def sentence_initial(text, pos):
    before = text[:pos].rstrip(" \t\"'([")
    return not before or before[-1] in ".!?:;\u2022" or before.endswith(("- ", "* "))


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'$])", text.strip()) if s]


# Exact terms of art that look like tells and are not. They are masked before
# any tell is matched. The rule is an allowlist of whole terms, not a list of
# exceptions per sentence: "comprehensive plan" is a planning document,
# "substantial completion" a construction contract milestone.
EXACT_TERMS = re.compile(r"""\b(?:
    comprehensive\s+(?:plans?|planning|exams?|examinations?|metabolic\s+panels?|
                      general\s+liability|care\s+plans?|assessments?)
  | statistically\s+significant | significant\s+figures | significance\s+level
  | substantial(?:ly)?\s+complet(?:e|ion) | substantial\s+evidence | substantial\s+compliance
  | leveraged\s+(?:buyouts?|finance|loans?|lending|recapitali[sz]ations?|ESOPs?)
  | (?:operating|financial|net|gross)\s+leverage | leverage\s+ratios?
  | robust\s+(?:regression|optimi[sz]ation|control|statistics|standard\s+errors?|estimators?)
  | very\s+(?:first|last|same|beginning|end|start|top|bottom)
  | extensive\s+(?:decay|damage|burns?|bleeding|disease|fibrosis|caries|scarring|necrosis|corrosion|erosion)
  | pivotal\s+(?:trials?|stud(?:y|ies)|phase|data|readouts?)
  | just[-\s]in[-\s]time
  | foster\s+(?:care|parents?|famil(?:y|ies)|youth|homes?|child(?:ren)?|placements?)
  | elevated\s+(?:blood|lactate|glucose|levels?|risk|temperatures?|heart\s+rates?|
                 pressures?|readings?|platforms?|walkways?|work)
  | (?:hard|disk|flash|thumb|test|blood|food|toy|clothing|donation)\s+drives?
  | drive[-\s]?(?:thru|through|train|shafts?|times?)
  | extensive\s+margin
  | seamless\s+(?:[\w-]+\s+)?(?:gutters?|pipes?|piping|tub(?:e|es|ing)|steel|flooring|siding)
  | significant\s+(?:deficienc(?:y|ies)|digits|figures)
  | foster(?:s|ed|ing)?\s+(?:\d+\s+)?(?:shelter\s+|rescue\s+)?(?:dogs?|cats?|kittens?|puppies|animals?|pets?|children|kids|youth|teens?)
  | elevat\w*\s+(?:[\w-]+\s+){0,6}?(?:\d+\s*(?:feet|ft|foot|inches)|above\s+(?:the\s+)?(?:base\s+)?flood)
)\b""", re.I | re.X)


def mask_terms(text):
    return EXACT_TERMS.sub(lambda m: re.sub(r"\S", "x", m.group(0)), text)


class Check:
    """One pattern. `proper_ok` skips a match that is a capitalized word in
    the middle of a sentence: "Rather Street" or "Foster City" is a name."""

    def __init__(self, name, level, pattern, fix, proper_ok=False, flags=re.I):
        self.name, self.level, self.fix, self.proper_ok = name, level, fix, proper_ok
        self.rx = re.compile(pattern, flags)

    def find(self, text, masked):
        for m in self.rx.finditer(masked):
            if self.proper_ok and text[m.start()].isupper() and not sentence_initial(text, m.start()):
                continue
            return m
        return None


FAIL, REVIEW = "FAIL", "REVIEW"

# --- the general AI-writing tells. R4 section 7 lists the classes ---------
TELLS = [
    Check("em dash", FAIL, r"\u2014|\u2015|\s--\s|\w--\w",
          "Use a period, a colon or a comma."),
    Check("negative corollary", FAIL,
          r"\bnot\s+(?:just|only|simply|merely)\b[^.!?]*?\bbut\b"
          r"|,\s*(?:and\s+)?not\s+(?:just|only|simply|merely)\b"
          r"|\b(?:is|are|was|were)\s+not\s+(?:just|only|merely|simply)\b"
          r"|\b(?:isn't|aren't|wasn't|weren't)\s+(?:just|only|merely|simply)\b"
          r"|\bnot\s+only\b|\bmore\s+than\s+(?:just|merely|simply)\b",
          "Say the second half straight. Drop the half it is set against."),
    Check("not about X, about Y", FAIL,
          r"\b(?:not|never|isn't|wasn't)\s+(?:really\s+|just\s+|only\s+)?about\b.{0,120}?\babout\b",
          "Say what it is. Cut what it is not."),
    Check("symmetrical negation", FAIL,
          r"\b(?:I'm|I\s+am|we're|we\s+are|(?:he|she|it|this|that)(?:'s|\s+is|\s+was))\s+not\s+"
          r"(?:just\s+)?(?:a|an|the)\b[^.!?;]{1,60}[.!?;]\s*(?:I'm|I\s+am|we're|we\s+are|"
          r"(?:he|she|it|this|that)(?:'s|\s+is|\s+was))\s+(?:a|an|the)\b"
          r"|(?:^|[.!?;]\s+)not\s+(?:just\s+)?(?:a|an|the)\s+(?!single\b|one\b)[^.!?;]{1,60}[.;!?]\s*"
          r"(?:but\s+)?(?:a|an|the)\s+\w+",
          "State what the person does, in its own terms. The mirror adds nothing."),
    Check("empty comparison", FAIL,
          r"\b(?:unlike|where|while|whereas)\s+(?:most|many|other|typical|the\s+average)\b(?!\s+of\b)"
          r"|\b(?:most|many)\s+(?!of\b)(?:\w+\s+){0,3}(?:do|does|don't|stop|stops|end|ends|hand|hands|"
          r"never|can't|cannot|only|struggle|fail|treat|see|work|operate|stay|stick)\b"
          r"|\bfew\s+(?:\w+\s+){0,3}(?:can|do|ever|are|have)\b"
          r"|\bone\s+of\s+(?:the\s+)?(?:few|only|rare)\b"
          r"|\b(?:a\s+)?rare\s+(?:mix|blend|combination|pairing|breed|ability)\b"
          r"|\bin\s+(?:an?\s+)?(?:industry|field|space|market|category|world|profession)\s+where\b"
          r"|\b(?:rare|uncommon|unusual|hard\s+to\s+find)\s+(?:in|among|for|combination)\b"
          r"|\bthe\s+(?:average|typical)\s+\w+\s+(?:does|is|has|works|stops)\b"
          r"|\bwhat\s+sets\s+\w+\s+apart\b|\bsets\s+(?:me|him|her|them|us)\s+apart\b",
          "Delete the unnamed group. The claim has to stand alone. A named competitor or "
          "a measured baseline is a real comparison and stays."),
    Check("throat-clearing opener", FAIL,
          r"(?:^|[.!?]\s+)(?:in\s+today's\b|in\s+(?:an?\s+|the\s+)?(?:ever[- ]\w+|increasingly\s+\w+|"
          r"rapidly\s+\w+|fast[- ](?:moving|paced|changing))\b|in\s+the\s+(?:current|modern|digital)\s+"
          r"(?:age|era|world|landscape|climate)\b|at\s+the\s+end\s+of\s+the\s+day\b|when\s+it\s+comes\s+to\b|"
          r"it\s+goes\s+without\s+saying\b|now\s+more\s+than\s+ever\b|in\s+a\s+world\s+where\b|"
          r"as\s+(?:a|an)\s+(?:seasoned|experienced|passionate|dedicated|results)\b|in\s+the\s+world\s+of\b)"
          r"|\bin\s+today's\s+(?:fast|ever|rapidly|competitive|digital|world|market|landscape|economy|"
          r"environment|climate)",
          "Start on the point. The first words are the claim."),
    Check("hedge", FAIL,
          r"\b(?:very|really|quite|somewhat)\b"
          r"|\bfairly\s+(?!(?:and|to|in|for|with|across|by|on|at)\b)[a-z]"
          r"|(?<!would\s)(?<!'d\s)\brather\b(?!\s+than\b)"
          r"|\ba\s+bit\b(?!-)"
          r"|(?<!\bthe\s)(?<!\bthat\s)(?<!\bthis\s)(?<!\ba\s)(?<!\bwhat\s)(?<!\bwhich\s)(?<!\bevery\s)"
          r"(?<!\bsome\s)(?<!\bany\s)(?<!\bone\s)(?<!\bof\s)\b(?:kind|sort)\s+of\b",
          "Cut it. The claim is stronger flat.", proper_ok=True),
    Check("sincerity word", REVIEW, r"\b(?:honestly|genuinely|truthfully|frankly)\b",
          "Saying it's honest doesn't make it more believable. Cut it.", proper_ok=True),
    Check("filler", FAIL, r"\b(?:actually|simply|literally|basically|just(?![-\s]in[-\s]time))\b",
          "Cut it. It changes nothing.", proper_ok=True),
    Check("vague size word", FAIL,
          r"\b(?:significant(?:ly)?|robust(?:ly)?|comprehensive(?:ly)?|powerful(?:ly)?|seamless(?:ly)?|"
          r"impactful|high[- ]impact|substantial(?:ly)?|extensive(?:ly)?)\b",
          "Replace it with the figure it stands in for.", proper_ok=True),
    Check("fluff verb", FAIL,
          r"\bleverag(?:e|es|ed|ing)\b|\bunlock(?:s|ed|ing)?\b|\bempower(?:s|ed|ing|ment)?\b"
          r"|\belevat(?:e|es|ed|ing)\b|\bstreamlin(?:e|es|ed|ing)\b|\bfoster(?:s|ed|ing)?\b"
          r"|\bspearhead(?:s|ed|ing)?\b|\borchestrat(?:e|es|ed|ing)\b|\b(?:super|turbo)charg(?:e|es|ed|ing)\b"
          r"|(?<![\w-])(?:drive|drives|driving|drove)\s+(?:[\w-]+\s+){0,2}?(?:growth|results|engagement|"
          r"adoption|alignment|change|innovation|value|impact|success|efficiency|efficiencies|excellence|"
          r"transformation|performance|outcomes|momentum|synergies|collaboration|accountability|"
          r"strateg(?:y|ies)|initiatives|improvements?|awareness)\b",
          "Use a plain verb that says what happened: led, built, ran, cut, grew, won.",
          proper_ok=True),
    Check("weak or passive claim", FAIL,
          r"\bcontribut(?:ed|ing|es)\s+to\b|\b(?:was|were|been|being)\s+involved\s+(?:in|with)\b"
          r"|\bplayed\s+an?\s+(?:\w+\s+)?role\b|\bcan\s+help\b|\bmay\s+be\s+able\s+to\b"
          r"|\bhelped\s+(?:to|with)\b|\b(?:was|were)\s+(?:a\s+)?part\s+of\b|\bparticipated\s+in\b"
          r"|\btasked\s+with\b|\b(?:was|were|am|is)\s+responsible\s+for\b"
          r"|(?:^|[.;]\s+)(?:responsible\s+for|duties\s+included|worked\s+on|assisted\s+(?:in|with))\b",
          "Say what you did and what came of it."),
    Check("latinate default", FAIL,
          r"\butili[sz](?:e|es|ed|ing)\b|\bcommenc(?:e|es|ed|ing)\b|\bendeavou?r(?:s|ed|ing)?\b"
          r"|\bascertain(?:s|ed|ing)?\b"
          r"|\bdemonstrat(?:e|es|ed|ing)\s+(?:[\w-]+\s+){0,2}?(?:ability|abilities|success|experience|expertise|"
          r"leadership|commitment|skills?|knowledge|proficiency|track\s+record|excellence|capabilit(?:y|ies))\b",
          "Use the plain word: use, start, try, find out, showed. A noun like "
          "'utilization' is a term of art and stays.", proper_ok=True),
    Check("cliche", FAIL,
          r"\bresults?[- ](?:driven|oriented|focused)\b|\bproven\s+track\s+record\b|\btrack\s+record\s+of\b"
          r"|\bpassionate\s+(?:about|for)\b|\bpassion\s+for\b|\bseasoned\b"
          r"|\bdynamic\s+(?:and\s+\w+\s+)?(?:leader|professional|team|self-starter|individual|executive|"
          r"manager|strategist|marketer|communicator|personality|go-getter|person)"
          r"|\bteam\s+player\b|\bgo[- ]getter\b|\bthought\s+leaders?\b(?!ship)|\bsynerg\w+"
          r"|\bworld[- ]class\b|\bholistic(?:ally)?\b|\bbest[- ]in[- ]class\b|\bcutting[- ]edge\b"
          r"|\bstate[- ]of[- ]the[- ]art\b|\bdetail[- ]oriented\b|\bself[- ]starter\b"
          r"|\b(?:out|outside)\s+(?:of\s+)?the\s+box\b|\bhit\s+the\s+ground\s+running\b"
          r"|\bwears?\s+many\s+hats\b|\bgame[- ]chang(?:er|ing)\b|\bmove\s+the\s+needle\b"
          r"|\bhard[- ]?working\b|\bhighly\s+motivated\b|\bstrategic\s+thinker\b|\bpeople\s+person\b"
          r"|\bwin[- ]win\b|\bvalue[- ]add(?:ed)?\b|\bgo[- ]to\s+(?:person|expert|resource)\b"
          r"|\bbridg(?:e|es|ed|ing)\s+the\s+gap\b",
          "Say the thing itself. Name the connection, the result, the number."),
    Check("from scratch", FAIL, r"\bfrom\s+(?:the\s+)?(?:scratch|ground\s+up)\b",
          "Redundant. 'Built the program' is complete."),
    Check("ending on air", FAIL,
          r",\s*(?:thereby\s+)?(?:delivering|driving|ensuring|unlocking|creating|providing|fueling|"
          r"fostering|enabling|maximizing|enhancing|boosting|promoting|generating|resulting\s+in|"
          r"leading\s+to)\s+(?:[a-z]+(?:-[a-z]+)?\s+){0,3}(?:excellence|value|alignment|synerg(?:y|ies)|"
          r"outcomes|results|success|efficienc(?:y|ies)|growth|transformation|innovation|change|"
          r"possibilities|potential|impact|engagement|satisfaction|performance|experiences?|"
          r"opportunities|momentum|collaboration|trust|visibility)"
          r"(?:\s+(?:for|to|across|with|among|in)\s+[a-z\s'-]{1,30})?\s*[.!]?\s*$",
          "The line closes on a quality, not a result. End on something a reader could "
          "check, or cut the phrase."),
    Check("whether setup", FAIL,
          r"\bwhether\s+(?:it's|it\s+is|you're|you\s+are|you|your|they're|we're)\b[^.]{0,80}?\bor\b"
          r"|(?:^|[.!?]\s+)whether\b[^.]{0,80}?\bor\b[^.]{0,60},",
          "Cut the setup. Say what was done, for whom."),
    Check("urgency coda or meta-statement", FAIL,
          r"\b(?:ready|eager|excited|thrilled|looking|hoping|keen|poised|seeking|aiming)\s+to\s+"
          r"(?:bring|contribute|join|apply|take|make|help|leverage|grow|learn|continue|deliver|lead|add|"
          r"support|use|build)\b"
          r"|\bseeking\s+(?:a|an)\s+(?:\w+\s+){0,3}(?:role|position|opportunity|opportunities|challenge)\b"
          r"|\b(?:I'm|I\s+am|I\s+would|I'd)\s+(?:excited|thrilled|eager|keen|delighted|honored|love)\b"
          r"|\bwould\s+(?:love|welcome)\s+(?:the\s+)?(?:opportunity|chance)\b"
          r"|\blooking\s+for\s+(?:a|an|my)\s+(?:new\s+)?(?:role|position|opportunity|challenge)\b"
          r"|\bnow\s+is\s+the\s+time\b|\bthe\s+time\s+is\s+now\b|\bto\s+be\s+(?:honest|candid|frank)\b"
          r"|\bcandidly\b|\bfull\s+disclosure\b|\blet\s+me\s+be\s+clear\b|\bmake\s+a\s+(?:real\s+)?difference\b",
          "A resume states what was done. What the candidate wants next belongs in a "
          "cover letter, if anywhere."),
    Check("indirect claim", FAIL,
          r"(?:^|[.;:!?,]\s+|\b(?:and|but|so)\s+)(?:that|this)\s+(?:is|was)\s+(?:the\s+work|"
          r"what\s+(?:I|we|great|good|real)|exactly|precisely|where\s+I|how\s+I|why\s+I)\b"
          r"|\bthat's\s+(?:the\s+work|what\s+I\s+do|exactly\s+what)\b"
          r"|\bwhich\s+is\s+(?:exactly|precisely)\s+what\b|\bis\s+what\s+I\s+do\b",
          "Say the thing: 'Ran the X for 12 years', not 'that is the work'."),
    Check("vague place", FAIL,
          r"\bseat\s+at\s+the\s+table\b|\bbrings?\s+(?:\w+\s+){0,4}to\s+the\s+table\b"
          r"|\b(?:voice|person|people|adult|smartest\s+\w+)\s+in\s+the\s+room\b|\bin\s+the\s+room\s+where\b"
          r"|\bat\s+the\s+(?:leadership|executive|decision|strategy)\s+table\b",
          "Name the real place or group: the board, the Tuesday ops review, the plant."),
    Check("LLM marker word", FAIL,
          r"\bdelv(?:e|es|ed|ing)\b|\bunderscor(?:e|es|ed|ing)\b|\bshowcas(?:ed|es|ing)\b|\bto\s+showcase\b"
          r"|\btapestry\b|\btestament\s+to\b|\brealms?\b|\bpivotal\b|\bmeticulous(?:ly)?\b"
          r"|\bintricat(?:e|ely|acies)\b|\bembark(?:s|ed|ing)?\b|\bbustling\b|\bmultifaceted\b"
          r"|\bever[- ](?:evolving|changing|shifting)\b"
          r"|\bnavigat(?:e|es|ed|ing)\s+(?:the\s+)?(?:complex|complexities|intricacies|nuances|challenges)\b"
          r"|\bharness(?:es|ed|ing)?\s+the\s+power\b|\bunwavering\b|\btransformative\b|\bparadigm\b"
          r"|\bdeep\s+dive\b|\bcommitment\s+to\s+excellence\b|\bvibrant\b",
          "A word models reach for and people rarely say. Use the plain one.", proper_ok=True),
    Check("amplified superlative", FAIL,
          r"\b(?:truly|incredibly|absolutely|extremely|deeply|genuinely|hugely|remarkably|uniquely)\s+"
          r"(?:one\s+of|the\s+(?:most|best|first|largest|highest|fastest)|innovative|unique|exceptional|"
          r"transformative|proud)\b",
          "Drop the amplifier. The flat claim lands harder and the number carries it."),
    Check("names a gap", FAIL,
          r"\b(?:have|has|had)\s+(?:not|never)\s+(?:used|worked|run|held|managed|led)\b"
          r"|\bno\s+(?:prior|direct|formal|professional)\s+experience\b"
          r"|\b(?:need|needs|have|has)\s+to\s+learn\b|\bstill\s+learning\b"
          r"|\bwhile\s+I\s+(?:have\s+not|haven't|lack)\b|\bon\s+paper\b|\bI\s+lack\b",
          "Never on a resume. It argues one side. The gap gets handled in the interview."),

    Check("threes for rhythm", REVIEW,
          r"(?:^|[\s,:;])(?:[a-z][\w-]*\s)?[a-z][\w-]*,\s+[a-z][\w-]*(?:\s[a-z][\w-]*)?,?\s+(?:and|or|&)\s+"
          r"[a-z][\w-]*(?:\s+(?:under|to|in|for|at|on|with|across|when)\s+[a-z\s'-]{1,30})?[.!]?\s*$"
          r"|^[A-Z][a-z]+ed,\s+[a-z]+ed,?\s+(?:and\s+)?[a-z]+ed\b"
          r"|^[A-Za-z][a-z-]+,\s+[a-z][a-z-]+,?\s+(?:and\s+)?[a-z][a-z-]+[.!]?$"
          r"|^[A-Z][a-z-]+,\s+[a-z][a-z-]+,\s+(?:and\s+)?[a-z][a-z-]+\s",
          "Three short items in a row read as rhythm, not fact. Keep the one that is "
          "proven, or name what each one produced.", flags=0),
    Check("hanging phrase", REVIEW,
          r"(?:^|[.!?;]\s+)(?:this|that|which|it)\s+(?:is|was|meant|means|led|allowed|enabled|gave|made|"
          r"makes|became|helped|resulted|kept|keeps|turned|let|lets|freed|put|brought|changed|saved|created)\b",
          "What does 'this' point to? Name the thing, then what it did."),
    Check("vague place", REVIEW, r"\b(?:in|into|around|across|at|to)\s+the\s+(?:room|table)\b",
          "Fine when the sentence builds the place. Otherwise name it."),
    Check("drawn-out construction", REVIEW,
          r"(?:^|[.!?;]\s+)what\s+(?:\w+\s+){1,5}(?:is|was)\s+(?!now\b|still\b)\w+"
          r"|(?:^|[.!?;]\s+)it\s+(?:is|was)\s+(?:the\s+|a\s+|an\s+|our\s+|their\s+)?(?:[\w-]+\s+){0,3}"
          r"[\w-]+\s+(?:that|who)\s+\w+"
          r"|\bthe\s+reason\s+(?:\w+\s+){0,6}(?:is|was)\s+(?:that|because)\b|\bthe\s+fact\s+that\b"
          r"|\bis\s+the\s+(?:part|piece|thing|reason)\s+(?:I|we|he|she|they|that)\b"
          r"|\b(?:has|have|had)\s+taught\s+(?:me|us|him|her|them)\b"
          r"|\bwhat\s+I(?:'ve|\s+have)?\s+(?:do|did|learned|found|bring)\s+is\b",
          "Put the subject first and let the verb do the work."),
    Check("latinate default", REVIEW,
          r"\bfacilitat(?:e|es|ed|ing)\b(?![^.]{0,50}\b(?:workshops?|sessions?|meetings?|retreats?|"
          r"trainings?|focus\s+groups?|sprints?|discussions?|dialogues?|classes|courses?|seminars?|"
          r"forums?|town\s+halls?|roundtables?|charrettes?|circles?|labs?|conversations?)\b)"
          r"|\bconstruct(?:ed|ing|s)?\b(?![^.]{0,40}\b(?:homes?|houses?|buildings?|bridges?|roads?|units?|"
          r"facilit(?:y|ies)|towers?|warehouses?|schools?|walls?|foundations?|decks?|pipelines?|plants?|"
          r"stores?|sites?|square\s+feet|sq\.?\s*ft|miles?|apartments?|offices?|hospitals?|additions?|"
          r"garages?|parking|dams?|tunnels?)\b)",
          "Fine when literal: facilitating a workshop, constructing a building. "
          "Otherwise use a plain verb: ran, built.", proper_ok=True),
    Check("soft verb", REVIEW,
          r"(?<![\w-])(?:drove|drives|driving|curat(?:e|ed|es|ing))\b",
          "Fine when literal (drove a truck). Otherwise use a plain verb.", proper_ok=True),
    Check("ends on an abstraction", REVIEW,
          r"\b(?:deliver|driv|ensur|provid|creat|unlock|achiev)\w*\s+(?:\w+\s+){0,2}(?:impact|excellence|"
          r"value|alignment|synergy|outcomes|results|success|efficiencies)[^.]{0,20}\.?\s*$",
          "Does the line close on something a reader could check? This is a shape, not a "
          "word list, so read the line."),
    Check("LLM marker word", REVIEW,
          r"\blandscape\b(?!\s+(?:architect\w*|design\w*|maintenance|crews?|contract\w*|install\w*|"
          r"plans?|lighting|irrigation|services?))",
          "Fine when it is land. Otherwise name the market or the field.", proper_ok=True),
    Check("borrowed framework", REVIEW,
          r"\bblue\s+ocean\b|\bgood\s+to\s+great\b|\bcross(?:ing|ed)?\s+the\s+chasm\b"
          r"|\bjobs?[- ]to[- ]be[- ]done\b|\bstart\s+with\s+why\b|\bgolden\s+circle\b|\bradical\s+candor\b"
          r"|\bextreme\s+ownership\b|\btipping\s+point\b|\bflywheel\b|\bfirst[- ]principles\b"
          r"|\bdisruptive\s+innovation\b|\binnovator's\s+dilemma\b|\bmoments?\s+of\s+truth\b"
          r"|\bhedgehog\s+concept\b",
          "Someone else's named framework. Attribute it, or say what you did in plain words."),
    Check("status tag at the end", REVIEW,
          r"[,;]\s*(?:now|since|later|currently|subsequently)\s+[\w-]+\s*(?:[,.]|$)",
          "A fact pinned on after the sentence ends reads as a footnote. Put it in the grammar."),
    Check("artifact count as evidence", REVIEW,
          r"\b\d+[- ](?:page|slide|word|deck)s?\b|\b\d+\s+deliverables\b",
          "That measures the document, not what it changed."),
]

# Wider forms of the same classes, added after a blind test set (v2.0).
TELLS += [
    Check("negative corollary", FAIL,
          r"\bas\s+more\s+than\s+(?:a|an|just)\b|\bgo(?:es)?\s+beyond\b|\bwent\s+beyond\b"
          r"|\bbeyond\s+(?:a|an|the|just)\s+[\w-]+(?:\s+[\w-]+){0,2}\s+(?:to|into)\b"
          r"|\b(?:took|take|takes|taking|moved|pushed|went|go|goes)\s+[\w\s'-]{0,40}?\bbeyond\s+[\w\s-]{1,40}?\s+(?:to|into)\b"
          r"|(?:^|[.!?;]\s+)more\s+than\s+(?:a|an)\s+[\w-]+(?:\s+[\w-]+)?\s*[,;:]\s*(?:a|an)\b",
          "Say the second half straight. Drop the half it is set against."),
    Check("symmetrical negation", FAIL,
          r"(?:^|[.!?;]\s+)less\s+[\w-]+(?:\s+[\w-]+)?,\s+more\s+[\w-]+"
          r"|(?:^|[.!?;]\s+)not\s+(?:a|an)\s+[\w-]+(?:\s+[\w-]+)?\s*[,:]\s*(?:but\s+)?(?:a|an)\s+\w+",
          "State what the person does, in its own terms. The mirror adds nothing."),
    Check("empty comparison", FAIL,
          r"\bunique\s+(?:blend|mix|combination|pairing)\b|\bcombination\s+(?:that\s+)?(?:most|few)\b"
          r"|\b(?:most|few|many)\s+(?:[\w-]+\s+){0,2}(?:lack|miss|overlook)\b|\bwhere\s+others\b",
          "Delete the unnamed group. The claim has to stand alone."),
    Check("throat-clearing opener", FAIL,
          r"(?:^|[.!?]\s+)(?:in\s+an?\s+(?:era|age|time|climate|market|environment|industry)\s+(?:of|where|when)"
          r"|at\s+a\s+time\s+(?:when|of)|as\s+(?:the\s+)?(?:industry|market|world|landscape|field)\s+"
          r"(?:evolves|changes|shifts|grows))\b",
          "Start on the point. The first words are the claim."),
    Check("hedge", FAIL,
          r"\bpretty\s+(?!penny\b)[a-z]+\b",
          "Cut it. The claim is stronger flat.", proper_ok=True),
    Check("filler", FAIL, r"\bessentially\b", "Cut it. It changes nothing.", proper_ok=True),
    Check("vague size word", FAIL,
          r"\bmeaningful(?:ly)?\b|\bconsiderabl[ey]\b|\bsizable\b",
          "Replace it with the figure it stands in for.", proper_ok=True),
    Check("weak or passive claim", FAIL,
          r"\bplayed\s+an?\s+(?:[\w-]+\s+)?part\s+in\b|\binstrumental\s+in\b",
          "Say what you did and what came of it."),
    Check("LLM marker word", FAIL, r"\bbolster(?:s|ed|ing)?\b",
          "A word models reach for and people rarely say. Use the plain one.", proper_ok=True),
    Check("fluff verb", REVIEW,
          r"\bharness(?:es|ed|ing)?\b|\brevolutioni[sz](?:e|es|ed|ing)\b|\bchampion(?:s|ed|ing)\b",
          "Use a plain verb that says what happened.", proper_ok=True),
    Check("latinate default", REVIEW, r"\bin\s+order\s+to\b|\bsubsequently\b",
          "'To' and 'then' do the same work.", proper_ok=True),
    Check("ending on air", REVIEW,
          r",\s*(?:creating|building|fostering|positioning|setting|paving|laying|driving|delivering|"
          r"ensuring|enabling|strengthening|supporting|cultivating)\s+(?:[\w-]+\s+){0,5}?(?:growth|success|"
          r"improvement|excellence|innovation|value|impact|culture|future|foundation|stage|way|efficiency|"
          r"alignment|outcomes|results|transformation)\b[^.,;]{0,30}[.!]?\s*$",
          "The line closes on a quality. End on something a reader could check."),
    Check("threes for rhythm", REVIEW,
          r"(?:^|[\s:;])[a-z][\w-]*(?:\s[a-z][\w-]*){0,2},\s+[a-z][\w-]*(?:\s[a-z][\w-]*){0,2},?\s+and\s+"
          r"[a-z][\w-]*(?:\s[a-z][\w-]*){0,2}\b",
          "Three items in a row can read as rhythm. Keep them only if each one is a real fact.",
          flags=0),
    Check("hanging phrase", REVIEW,
          r"\bwhich\s+(?:gave|made|meant|changed|allowed|let|freed|saved|kept|turned|brought|became)\b"
          r"|(?:^|[.!?]\s+)(?:that|this)\s+[a-z]+\s+(?:changed|made|meant|gave|allowed)\b"
          r"|\bmade\s+all\s+the\s+difference\b|\bchanged\s+everything\b",
          "What does it point to? Name the thing, then what it did."),
    Check("vague place", REVIEW,
          r"\bin\s+the\s+space\b(?!\s+(?:of|between|where|program|station|shuttle|center|allotted))",
          "Name the market or the field."),
    Check("LLM marker word", REVIEW,
          r"\bnavigat(?:e|es|ed|ing)\b(?!\s+(?:the\s+)?(?:ships?|vessels?|boats?|aircraft|planes?|rivers?|"
          r"trails?|routes?|roads?))",
          "Fine for ships and trails. Otherwise say what was done: ran, cleared, won.", proper_ok=True),
]

# Named literals of the hanging phrase: settled, so FAIL.
TELLS.append(Check("hanging phrase", FAIL,
                   r"\b(?:gave|give|gives|giving)\s+(?:the\s+)?(?:hours|time)\s+back\b"
                   r"|\bthe\s+work\s+that\s+wins\b",
                   "Name what was built and what it did, for whom."))


# --- counts and labels that name nothing (2.3.0) ------------------------------
# A count of abstract things names its set: what it was about or for.
# "Settled seven decisions" names nothing; "seven decisions on pricing and the
# launch date" does. A generic word ("key", "strategic", "core") is not a name.
# A count of concrete things (stores, interviews, employees) is scope and is not
# read here. The same goes for a label with nothing behind it ("key insights").
# references/writing.md, Name what you count.

def _wordset(text):
    return set(text.split())


SET_NUMBER_WORDS = ("two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
                    "fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty")
SET_COUNT = re.compile(rf"(?<![\d,.$])\d{{1,3}}(?:,\d{{3}})*\+?(?![\d,.]\d)"
                       rf"|\b(?i:{SET_NUMBER_WORDS})\b")
SET_WORD = re.compile(r"\s+([A-Za-z][\w'&-]*)")

# Nouns whose count needs a name for the set.
ABSTRACT_SETS = _wordset("""decisions directives priorities themes recommendations principles pillars
 goals needs initiatives tools findings insights objectives strategies problems issues opportunities
 ideas values areas services solutions takeaways learnings lessons imperatives tenets""")
# "six-pillar roadmap": a count joined to a unit, ending on a plan word.
SET_UNITS = _wordset("pillar point priority principle theme goal")
SET_HEADS = _wordset("""plan plans list order roadmap framework agenda checklist program strategy
 system model approach process playbook blueprint charter platform vision rubric scorecard matrix
 methodology""")
# Words that describe any set and so name none of them.
GENERIC_WORDS = _wordset("""key strategic strategy major critical core important main primary principal
 top big high-level high-priority priority essential fundamental guiding clear actionable measurable
 concrete specific overarching foundational central crucial vital bold new final initial early several
 different distinct various multiple separate standardized standard practical immediate quick long-term
 short-term near-term mid-term medium-term next future broad focused targeted tailored custom
 customized business plan planning development operating operational organizational organization
 growth improvement action project program leadership team company firm firm-wide company-wide
 enterprise overall general follow-up recommended proposed agreed shared common joint cross-functional
 annual quarterly monthly weekly open remaining outstanding additional other more further related
 relevant small simple smart effective successful innovative creative unique discrete defined
 documented written formal internal external global regional local national high-impact impactful
 meaningful significant powerful valuable tangible compelling fresh deep rich ranked prioritized
 numbered phased sequenced scored weighted detailed approved adopted updated revised draft""")
# Words that say whose set it was, not what it was about.
OWNER_WORDS = _wordset("""client clients team teams company companies firm firms business businesses
 organization organizations org leadership leaders executive executives exec execs senior board
 management managers stakeholders staff partners owner owners ceo cfo coo cto cmo cio president
 founders cofounders co-founders group department departments office offices project projects program
 programs work year years quarter quarters future growth success improvement improvements change
 changes plan plans strategy strategies effort efforts direction path way steps step progress outcomes
 results performance impact value efficiency alignment everyone practice practices district
 districts city cities county counties clinic clinics hospital hospitals school schools resort resorts
 hotel hotels store stores plant plants site sites region regions unit units agency agencies account
 accounts museum council committee community""")
PLAIN_VERBS = _wordset("""move moving moved drive driving drove improve improving improved grow growing
 grew help helping helped support supporting supported enable enabling enabled ensure ensuring ensured
 achieve achieving achieved deliver delivering delivered increase increasing increased boost boosting
 advance advancing advanced succeed change changing changed transform transforming transformed align
 aligning aligned strengthen strengthening shape shaping shaped guide guiding guided set sets setting
 make making made take taking took get getting got go going went keep keeping kept build building
 built create creating created define defining defined inform informing informed focus focusing
 focused address addressing addressed meet meeting met reach reaching reached win winning won lead
 leading led is are was were be been being has have had forward ahead""")
FUNCTION_WORDS = _wordset("""the a an its their his her our my your this that these those each every
 all both and or but of to for in on with by at from into onto as per than then so such via across
 over under about around within between among through including plus also only not no any some more
 most other own which who whom whose where when while what how why it them us they we he she
 couldn't can't didn't wasn't weren't won't isn't""")
TOPIC_PREP = r"(?:on|about|covering|regarding|concerning|spanning)"
PURPOSE_PREP = r"(?:for|to|of|in|across|around|over|toward|towards|within|behind|against)"
DETERMINER = re.compile(r"(?:the|a|an|its|their|his|her|our|my|your|this|that|these|those|each|"
                        r"every|all|[A-Za-z]+'s)\s", re.I)
LABEL_WORDS = _wordset("""key strategic actionable critical important valuable high-level core major
 clear deep rich fresh bold compelling crucial vital essential meaningful powerful relevant practical
 concrete tangible""")
LABEL_NOUNS = _wordset("""insights findings recommendations directives priorities learnings takeaways
 themes initiatives solutions decisions principles opportunities strategies objectives imperatives
 pillars""")
LABEL = re.compile(r"\b(?P<mod>[A-Za-z][\w-]*)(?=(?P<gap>\s+)(?P<noun>[a-z]+)\b)")


def content_words(phrase):
    """The words in a phrase that name a thing: not a function word, not a
    generic word, not an owner, not a plain verb, not another abstract noun.
    A capitalized acronym (IT, M&A) names a thing."""
    out = []
    for tok in re.findall(r"[A-Za-z][A-Za-z'&.\-]*", phrase):
        raw = tok.strip(".'-")
        if len(raw) >= 2 and (raw.isupper() or "&" in raw):
            out.append(raw)
            continue
        w = re.sub(r"'s$", "", raw.lower())
        if (len(w) < 3 or w in FUNCTION_WORDS or w in GENERIC_WORDS or w in OWNER_WORDS
                or w in PLAIN_VERBS or w in ABSTRACT_SETS or re.match(rf"(?:{SET_NUMBER_WORDS}|\d)", w)):
            continue
        out.append(w)
    return out


def _clause(rest, words=8):
    """The words up to the end of the clause, or up to a new counted phrase."""
    c = re.split(rf"[,;:.!?]\s|[,;:]|\s+(?:and\s+then|then)\s+"
                 rf"|\s+and\s+(?:a|an|the|\d+|(?i:{SET_NUMBER_WORDS}))\b", rest, maxsplit=1)[0]
    return " ".join(c.split()[:words])


def set_named(rest, depth=0):
    """What the words after a counted noun do. "named": they say what the set
    was about or for. "owner": they only say whose it was ("for the district").
    None: nothing names it."""
    if re.match(r"\s*[:(]", rest) or re.match(r"\s*,?\s*(?:including|such\s+as|like)\b", rest):
        return "named"
    sentence = re.split(r"(?<=[.;!?])\s", rest, maxsplit=1)[0]
    for m in re.finditer(r"\bfrom\s+([^,;.]{1,60}?)\s+to\s+([^,;.]{1,60})", sentence):
        if not re.search(r"\d", m.group(1) + m.group(2)):
            return "named"                             # a range: from valet parking to late checkout
    m = re.match(r"\s*,?\s*(?:that|which|who)\s+(.*)", rest, re.S)
    if m:
        return "named" if content_words(_clause(m.group(1), 10)) else None
    m = re.match(rf"\s+({TOPIC_PREP}|{PURPOSE_PREP})\s+(.*)", rest, re.S)
    if not m:
        return None
    prep, tail = m.group(1).lower(), m.group(2)
    obj = re.split(rf"\s+(?:{TOPIC_PREP}|{PURPOSE_PREP})\s+", _clause(tail), maxsplit=1)[0]
    if content_words(obj):
        if re.fullmatch(TOPIC_PREP, prep) or not DETERMINER.match(obj + " "):
            return "named"
        return "owner"
    if depth < 2:                                      # "of needs for the clinic": read the next phrase
        nxt = tail[len(obj):]
        if re.match(rf"\s+(?:{TOPIC_PREP}|{PURPOSE_PREP})\s", nxt):
            return set_named(nxt, depth + 1)
    return None


def _counted(t, pos, nouns=None, heads=None, max_words=3):
    """(words before the noun, end) for the first noun in `nouns` (or head in
    `heads`) within max_words after pos, or None."""
    words, p = [], pos
    for _ in range(max_words):
        m = SET_WORD.match(t, p)
        if not m:
            return None
        w = m.group(1)
        words.append(w)
        p = m.end()
        if w.lower() in (heads or nouns):
            return words[:-1], p
        if re.search(r"[,;:.]$", w):
            return None
    return None


def set_hits(text):
    """[(level, check name, start, end)] for each count or label that names
    nothing (FAIL) or names only its owner (REVIEW)."""
    t = plain(text)
    hits = []

    def judge(start, end, mods, kind):
        if content_words(" ".join(mods)):
            return
        verdict = set_named(t[end:])
        if verdict == "named":
            return
        if verdict == "owner":
            hits.append((REVIEW, "set named only by its owner", start, end))
        else:
            hits.append((FAIL, kind, start, end))

    for m in SET_COUNT.finditer(t):
        joined = re.match(r"-([a-z]+)\b", t[m.end():])
        if joined:
            if joined.group(1) in SET_UNITS:
                got = _counted(t, m.end() + joined.end(), heads=SET_HEADS)
                if got:
                    judge(m.start(), got[1], got[0], "count names nothing")
            continue
        got = _counted(t, m.end(), nouns=ABSTRACT_SETS)
        if not got:
            continue
        if re.search(r"\b(?:scored|allowed|conceded|kicked|saved|assisted)\s*$", t[:m.start()], re.I) \
                and t[:got[1]].rstrip().endswith("goals"):
            continue                                   # a sports record, not a set
        judge(m.start(), got[1], got[0], "count names nothing")

    for m in LABEL.finditer(t):
        mod, noun = m.group("mod"), m.group("noun")
        if mod.lower() not in LABEL_WORDS or noun not in LABEL_NOUNS:
            continue
        if mod[0].isupper() and not sentence_initial(t, m.start()):
            continue                                   # "the Strategic Initiatives Group" is a name
        if re.search(rf"(?:{SET_COUNT.pattern})\s*(?:[A-Za-z][\w'&-]*\s+)?$", t[:m.start()]):
            continue                                   # a count: read above
        end = m.end() + len(m.group("gap")) + len(noun)
        judge(m.start(), end, [], "label names nothing")
    return hits


class _Span:
    def __init__(self, start, end):
        self._s, self._e = start, end

    def start(self):
        return self._s

    def end(self):
        return self._e


class SetCheck(Check):
    """One verdict from set_hits(), reported at this check's level."""

    def __init__(self, name, level, fix):
        super().__init__(name, level, r"(?!)", fix)

    def find(self, text, masked):
        for level, name, start, end in set_hits(text):
            if level == self.level and name == self.name:
                return _Span(start, end)
        return None


TELLS += [
    SetCheck("count names nothing", FAIL,
             "Say what the set was about or for: \"seven decisions on pricing and the launch "
             "date\". \"Key\", \"strategic\" or \"core\" names nothing. If the evidence can't "
             "name the set, drop the count."),
    SetCheck("label names nothing", FAIL,
             "Say what they were, or what they were about: \"key insights on churn\", not "
             "\"key insights\"."),
    SetCheck("set named only by its owner", REVIEW,
             "\"For the regional sales team\" says whose set it was, not what it was about. "
             "Name the subject, or keep it if the owner says enough."),
]

# --- words the sentence already means (2.3.0) ----------------------------------
# references/writing.md, Words the sentence already means. "From scratch" has
# its own check above.
TELLS += [
    Check("redundant word", FAIL,
          r"\beach\s+and\s+every\b|\bend\s+results?\b|\bfinal\s+outcomes?\b"
          r"|\bpast\s+(?:history|experience)\b|\bfuture\s+plans\b|\badvance\s+planning\b"
          r"|\b(?:was|were)\s+able\s+to\b|\bcollaborat(?:e|es|ed|ing)\s+together\b"
          r"|\b(?:combin|merg)(?:e|es|ed|ing)\s+together\b|\bnew\s+innovations?\b"
          r"|\bcompletely\s+eliminat(?:e|es|ed|ing)\b",
          "The sentence means this without the extra words. \"Every\", \"result\", "
          "\"history\", \"plans\"; \"cut\", not \"was able to cut\"."),
    Check("redundant word", REVIEW,
          r"\b(?:[A-Za-z]+'s|its|their|his|her|our|my|your)\s+own\b|\bpersonally\b|\bsuccessfully\b"
          r"|\bactual\b(?![^.;]{0,40}\b(?:budgets?|forecasts?|plans?|estimates?|targets?|projections?)\b)"
          r"|\b(?:built|build(?:s|ing)?|creat(?:e|es|ed|ing)|launch(?:es|ed|ing)?|design(?:s|ed|ing)?"
          r"|develop(?:s|ed|ing)?|introduc(?:e|es|ed|ing)|establish(?:es|ed|ing)?|founded"
          r"|open(?:s|ed|ing)?)\s+(?:(?:a|an|the|its|their)\s+)?new\b",
          "The sentence usually means this without it. It stays when it tells one thing from "
          "another: \"its own P&L\" for a separate one, \"a new plant\" that replaced an old "
          "one, \"actual\" against budget."),
]

# Not tells. Used only to pick which checks run where.
LIST_ONLY = {"threes for rhythm", "hanging phrase", "drawn-out construction",
             "count names nothing", "label names nothing", "set named only by its owner"}
NOT_TELLS = {"no number and no named thing", "long bullet", "every metric is a percentage"}


# --- first person -----------------------------------------------------------
FIRST_PERSON = re.compile(
    r"(?<![\w'&-])(?:I(?:'m|'ve|'d|'ll)?|me|my|mine|we(?:'re|'ve|'d|'ll)?|our|ours|us|myself|ourselves|"
    r"Me|My|Mine|We(?:'re|'ve|'d|'ll)?|Our|Ours|Us)(?![\w&/-])")
ROMAN_CONTEXT = {"phase", "level", "type", "title", "part", "class", "tier", "stage", "grade",
                 "series", "war", "chapter", "section", "article", "schedule", "division",
                 "category", "model", "mark", "step", "unit", "vol", "volume", "book"}


def first_person(text):
    """First-person pronouns as words. Not 'US' the country, not a capitalized
    'Our' or 'My' inside a name ('Our Town Market'), not a noun 'mine'."""
    t = plain(text)
    hits = []
    for m in FIRST_PERSON.finditer(t):
        w = m.group(0)
        before = t[:m.start()]
        prev_raw = (re.findall(r"[A-Za-z]+", before)[-1:] or [""])[0]
        prev_word = prev_raw.lower() if prev_raw[:1].isupper() else ""
        after = t[m.end():]
        if w == "I":
            if prev_word in ROMAN_CONTEXT or re.match(r"\s*(?:and|or|&)\s+II\b", after):
                continue
        elif w.lower() in ("mine",):
            if not re.search(r"\b(?:of|is|was|were|are|be|been)\s+$", before, re.I):
                continue        # "a copper mine" is a noun
        elif w[0].isupper():
            if not sentence_initial(t, m.start()):
                continue        # a capitalized 'Our' mid-sentence is a name
            if re.match(r"\s+[A-Z][a-z]", after):
                continue        # 'Our Town Market' at the start of a line
        hits.append(w)
    return hits


# --- evidence, names and figures --------------------------------------------
FIGURE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:[KMB]\b|billion|million|thousand)?"
    r"|\b\d[\d,]*(?:\.\d+)?\s?(?:%|percent\b)"
    r"|\b\d[\d,]*(?:\.\d+)?(?![\d,.]*\+?\s*(?:years?|yrs?)\b)(?:(?:-|\s)[a-z][a-z-]*)?", re.I)
YEAR = re.compile(r"^(?:19[5-9]\d|20[0-4]\d)$")


def figures(text):
    """[(key, shown)] for each figure. Tenure ('11 years') and calendar years are
    scope, not evidence, and are left out."""
    out = []
    for m in FIGURE.finditer(plain(text)):
        shown = m.group(0).strip()
        num = re.search(r"\d[\d,]*(?:\.\d+)?", shown).group(0).replace(",", "")
        kind = "$" if shown.startswith("$") else "%" if re.search(r"%|percent", shown, re.I) else ""
        if not kind and YEAR.match(num):
            continue
        out.append(((num, kind), shown))
    return out


def figure_keys(text):
    return {k for k, _s in figures(text)}


def has_figure(key, keys):
    num, kind = key
    if kind:
        return key in keys
    return any(n == num for n, _k in keys)


GENERIC_CAPS = set("""
january february march april may june july august september october november december
jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday
saturday sunday present earlier summary experience education skills certifications
senior junior director manager supervisor lead chief head vice president officer engineer
nurse registered certified licensed professional associate assistant analyst specialist
coordinator technician consultant executive principal partner founder owner intern
north south east west northeast northwest southeast southwest midwest central
inc llc co corp ltd group company the a an and of for in on at to with by from
alabama alaska arizona arkansas california colorado connecticut delaware florida georgia
hawaii idaho illinois indiana iowa kansas kentucky louisiana maine maryland massachusetts
michigan minnesota mississippi missouri montana nebraska nevada hampshire jersey mexico york
carolina dakota ohio oklahoma oregon pennsylvania rhode island tennessee texas utah vermont
virginia washington wisconsin wyoming america american usa canada europe asia
level tier grade class phase stage ii iii iv vi vii viii
""".split())

CAP_WORD = re.compile(r"(?<![\w'&-])(?:[A-Z][a-z][\w'&-]*|[A-Z]{2,}[a-z]?s?|[A-Z][a-z]*[A-Z][\w'&-]*)"
                      r"(?:\.[A-Za-z]+)*(?![\w-])")


def name_runs(text, acronyms=True):
    """Runs of adjacent capitalized words, as (run, start). A run that opens a
    sentence loses its first word: that capital is grammar, not a name."""
    t = plain(text)
    words = [(m.group(0), m.start(), m.end()) for m in CAP_WORD.finditer(t)]
    runs, cur = [], []
    for w in words:
        if cur and re.fullmatch(r"\s+", t[cur[-1][2]:w[1]]):
            cur.append(w)
        else:
            if cur:
                runs.append(cur)
            cur = [w]
    if cur:
        runs.append(cur)
    out = []
    for run in runs:
        if sentence_initial(t, run[0][1]):
            run = run[1:]
        if not acronyms:
            run = [w for w in run if not re.fullmatch(r"[A-Z]{2,}s?", w[0])]
        run = [w for w in run if w[0].lower().strip(".'") not in GENERIC_CAPS]
        if run:
            out.append((" ".join(w[0] for w in run).strip(".,'"), run[0][1]))
    return out


def contains_name(name, text):
    return re.search(r"(?<![\w-])" + re.escape(name.lower()) + r"(?![\w-])", plain(text).lower())


# --- keyword strips, counts ---------------------------------------------------
STRIP_LABEL = re.compile(
    r"^\s*(?:specialt(?:y|ies)|specialities|skills?|core\s+(?:skills|competencies)|expertise|"
    r"areas\s+of\s+expertise|key\s+skills|tools|technologies|competencies|strengths|keywords|"
    r"proficiencies|highlights)\s*:", re.I)
FINITE = set("""
is are was were be been has have had do does did will would can could shall should may might
must led leads built builds ran runs cut cuts grew grows won wins made makes took takes set sets
kept keeps brought brings held holds sold sells wrote writes drove drives began begins rose rises
knows believes comes goes works helps serves spent spends turns moves opens raises saves gives
gave got gets found finds taught teaches thinks thought says said sees saw put puts leaves left
""".split())


def keyword_strip(sentence):
    s = sentence.strip()
    if STRIP_LABEL.match(s):
        return True
    if s.count(",") < 3:
        return False
    items = [i.strip() for i in re.split(r",|\band\b|;", s.rstrip(". ")) if i.strip()]
    if any(len(i.split()) > 5 for i in items):
        return False
    words = re.findall(r"[A-Za-z']+", s)
    if any(w.lower() in FINITE for w in words):
        return False
    if re.search(r"\b[A-Za-z]+ed\s+(?:the|a|an|\d|\$|over|across|into|from)\b", s):
        return False
    return True


COUNT = re.compile(r"\b(?P<n>(?i:two|three|four|five|six|seven|eight|nine)|[2-9])\s+"
                   r"(?:(?!(?:at|in|on|for|by|to|of|from|with|and|or|per|a|an|the)\b)[a-z][a-z-]*\s+){0,2}?"
                   r"(?P<noun>[a-z][a-z-]*s(?<!ss)(?<!us)(?<!is))\b")
NUMWORD = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
TIME_UNITS = {"years", "months", "weeks", "days", "hours", "minutes", "seconds", "decades",
              "times", "shifts", "percent", "points", "yrs"}


# --- bullets --------------------------------------------------------------------
COUNT_WORD = re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|ten|\d{1,2})\b", re.I)
INCLUDING = re.compile(r"\b(?:including|such as)\b", re.I)
PROPER = re.compile(r"(?<!^)(?<![.!?]\s)\b[A-Z][A-Za-z&'.-]{2,}")
DIGIT = re.compile(r"\d|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
                   r"twelve|dozen|twenty|thirty|forty|fifty|hundred|thousand|million)\b", re.I)
PERCENT_END = re.compile(r"\d+(?:\.\d+)?%[^.]*\.?\s*$")
SKILLS_LINE = re.compile(r"^\s*(?:key\s+|core\s+)?(?:skills?|tools?)(?:\s+used)?\s*:", re.I)
CONTACT = re.compile(r"@|\(\d{3}\)|\d{3}[-.\s]\d{3}[-.\s]\d{4}|linkedin\.com", re.I)

EVIDENCE_STOP = {"and", "or", "the", "a", "an", "of", "for", "to", "in", "on", "with", "at", "by",
                 "into", "from", "via", "using", "&"}


def stem(w):
    w = w.lower().strip(".")
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


def word_stems(text):
    return {stem(t) for t in re.findall(r"[a-z0-9][a-z0-9+#.&'/-]*[a-z0-9+#]|[a-z0-9]",
                                        plain(text).lower().replace("'s ", " "))}


def item_evidenced(item, bullets):
    """Every word of the item, whole, in one role bullet. Whole words: the v1.6
    four-letter stem let "Brand identity" pass on "iden" in "resident". A
    bracketed short form, "Customer experience (CX)", counts in either form."""
    inner = re.findall(r"\(([^)]*)\)", item)
    forms = [re.sub(r"\([^)]*\)", " ", item)] + inner
    for form in forms:
        words = [w for w in re.findall(r"[a-z0-9][a-z0-9+#.&'/-]*[a-z0-9+#]|[a-z0-9]", plain(form).lower())
                 if w not in EVIDENCE_STOP]
        if not words:
            continue
        need = {stem(w) for w in words}
        if any(need <= word_stems(b) for b in bullets):
            return True
    return False


# --- career totals and copies ----------------------------------------------
TOTAL_FILLER = EVIDENCE_STOP | {"more", "than", "over", "about", "nearly", "almost", "plus",
                                "across", "total", "career"}


def total_matchers(totals):
    """Each confirmed career total as (figure keys, counted words): "100+
    workshops" gives ({("100", "")}, {"workshop"})."""
    out = []
    for t in totals or ():
        keys = figure_keys(t)
        words = {stem(w) for w in re.findall(r"[a-z][a-z-]*", plain(t).lower())
                 if w not in TOTAL_FILLER}
        if keys and words:
            out.append((keys, words))
    return out


def is_confirmed_total(key, sentence, matchers):
    """A summary figure is a confirmed total when a listed total has the same
    figure and its counted noun sits in the same sentence."""
    stems = word_stems(sentence)
    return any(has_figure(key, keys) and words & stems for keys, words in matchers)


def copy_words(text):
    return [w.strip(".,;:'\"()") for w in
            re.findall(r"[a-z0-9$#][a-z0-9%$+.'&/#-]*", plain(text).lower())]


def copied_from(sentence, bullets):
    """(bullet, run, share) for the bullet a summary sentence copies word for
    word, or None. A copy shares COPY_RUN words in a row with one bullet, or
    COPY_SHARE of its words in order."""
    sw = copy_words(sentence)
    if len(sw) < COPY_MIN_WORDS:
        return None
    best = None
    for b in bullets:
        blocks = difflib.SequenceMatcher(None, sw, copy_words(b), autojunk=False).get_matching_blocks()
        run = max((m.size for m in blocks), default=0)
        share = sum(m.size for m in blocks) / len(sw)
        if (run >= COPY_RUN or share >= COPY_SHARE) and (best is None or (run, share) > best[1:]):
            best = (b, run, share)
    return best


# ------------------------------------------------------------------ review --

def tell_hits(text, list_like=False):
    """(level, name, hit, fix) for every tell in a line. `list_like` is True for
    the skills, education and contact lines, where lists are the point."""
    t = plain(text)
    masked = mask_terms(t)
    out, seen = [], set()
    for chk in TELLS:
        if list_like and chk.name in LIST_ONLY:
            continue
        m = chk.find(t, masked)
        if m and (chk.level, chk.name) not in seen:
            seen.add((chk.level, chk.name))
            hit = t[m.start():m.end()].strip(" ,;.") or t[m.start():m.end()]
            out.append((chk.level, chk.name, hit[:80], chk.fix))
    # a FAIL and a REVIEW under the same name: keep the FAIL
    fails = {n for lv, n, _h, _f in out if lv == FAIL}
    return [o for o in out if not (o[0] == REVIEW and o[1] in fails)]


def review(blocks, career_totals=()):
    """(fails, reviews), each a list of (block number, rule, hit, fix).
    `career_totals` are the totals the candidate confirmed ("100+ workshops");
    they may sit in the summary with no single role behind them."""
    fails, reviews = [], []
    totals = total_matchers(career_totals)

    def add(level, n, name, hit, fix):
        (fails if level == FAIL else reviews).append((n, name, hit, fix))

    marked = structure(blocks)
    first_header = next((b.n for b in marked if b.kind == "header"), None)
    employers = {b.role.get("company", "") for b in marked if b.kind == "role" and b.role}
    employer_words = {w.lower() for e in employers for w in re.findall(r"[\w'&.-]+", e)}
    role_bullets = [b for b in marked if b.kind == "bullet" and is_experience(b.section)]
    bullet_text = [b.text for b in role_bullets]
    earlier = [b.text for b in marked if b.kind == "para" and is_experience(b.section)]
    evidence_text = bullet_text + earlier
    evidence_keys = set().union(*[figure_keys(t) for t in evidence_text]) if evidence_text else set()
    other_text = evidence_text + [b.text for b in marked if b.kind == "role"] + \
        [" ".join((b.role or {}).get(k, "") for k in ("title", "company", "city")) for b in marked
         if b.kind == "role"] + \
        [b.text for b in marked if b.kind in ("para", "bullet") and (is_education(b.section) or is_certs(b.section))]

    # --- every prose line: tells and first person ---
    for b in marked:
        if b.kind in ("role", "header"):
            continue
        top = first_header is None or b.n < first_header
        if top and CONTACT.search(b.text):
            continue
        list_like = top or is_skills(b.section) or is_education(b.section) or is_certs(b.section)
        for level, name, hit, fix in tell_hits(b.text, list_like=list_like):
            add(level, b.n, name, hit, fix)
        if not top:
            fp = first_person(b.text)
            if fp:
                add(FAIL, b.n, "first person", ", ".join(dict.fromkeys(fp)),
                    "A resume is written without I, me, my, we or our. Start on the verb.")

    # --- bullets under Experience: shape ---
    for b in marked:
        if b.kind != "bullet" or is_skills(b.section) or is_summary(b.section):
            continue
        n = len(b.text.split())
        if n > WORD_CEILING:
            add(REVIEW, b.n, "long bullet", f"{n} words",
                "Two rendered lines is the rule. widow_check.py measures it after the render.")
        if COUNT_WORD.search(b.text) and INCLUDING.search(b.text):
            add(REVIEW, b.n, "counts more than it names", b.text[:60],
                "Name all of them, or drop the count and name the ones you have.")
        if not DIGIT.search(b.text) and not PROPER.search(b.text):
            add(REVIEW, b.n, "no number and no named thing", b.text[:60],
                "Anyone could have written this about anyone. Add the specific.")

    ends_pct = [b for b in role_bullets if PERCENT_END.search(b.text)]
    if role_bullets and len(ends_pct) * 3 > len(role_bullets):
        add(REVIEW, 0, "every metric is a percentage",
            f"{len(ends_pct)} of {len(role_bullets)} bullets end on one",
            "Mix in counts, dollars, headcount, time saved, rankings.")

    # --- Experience: per-role skills lines are retired ---
    for b in marked:
        if is_experience(b.section) and b.kind in ("para", "bullet") and SKILLS_LINE.match(b.text):
            add(FAIL, b.n, "skills line inside Experience", b.text[:60],
                "Per-role skills lines are retired. Write the skill into the bullet where "
                "it was used.")

    # --- Summary ---
    summ = [b for b in marked if is_summary(b.section) and b.kind in ("para", "bullet")]
    for b in summ:
        if b.kind == "bullet":
            add(FAIL, b.n, "bullet under Summary", b.text[:60],
                "The summary is prose only. Move the proof into the role that produced it.")
    if summ:
        first_n = summ[0].n
        text = " ".join(b.text for b in summ)
        sents = sentences(text)
        if sents and keyword_strip(sents[-1]):
            add(FAIL, summ[-1].n, "summary ends on a keyword strip", sents[-1][:60],
                "End on a sentence. Terms that matter go in the bullets where they were used.")
        for s in sents[:-1]:
            if STRIP_LABEL.match(s):
                add(FAIL, first_n, "summary ends on a keyword strip", s[:60],
                    "A labeled list is not a sentence. Put the terms in the bullets.")

        words = len(re.findall(r"\S+", text))
        lo, hi = SUMMARY_WORDS
        if not lo <= words <= hi:
            add(REVIEW, first_n, "summary length", f"{words} words",
                f"{lo} to {hi} words is the range. Four rendered lines at most.")

        # figures and named clients that live only here
        seen = set()
        for s in sents:
            for key, shown in figures(s):
                if key in seen or is_confirmed_total(key, s, totals):
                    continue
                seen.add(key)
                if not has_figure(key, evidence_keys):
                    add(FAIL, first_n, "evidence only in the Summary", shown,
                        "No role says where this came from, so it reads as unproven. Put it "
                        "in the role that produced it. The summary can point to it. If it is "
                        "a career total the candidate confirmed, list it under "
                        "\"career_totals\" in the JSON source.")
        other = " ".join(other_text)
        for name, _pos in name_runs(text, acronyms=False):
            if all(w.lower() in employer_words for w in name.split()):
                continue
            if not contains_name(name, other):
                add(FAIL, first_n, "evidence only in the Summary", name,
                    "A named client or credit with no role behind it reads as unproven. "
                    "Put it in the role that produced it.")

        # a summary restates what the bullets prove; it never copies one
        for s in sents:
            copy = copied_from(s, bullet_text)
            if copy:
                add(REVIEW, first_n, "summary copies a bullet",
                    f"{s[:50]} ({copy[1]} words in a row, {round(copy[2] * 100)}% of the "
                    f"sentence, from: {copy[0][:40]})",
                    "Say it shorter and at a higher level, in new words. The role keeps "
                    "the full wording.")

        # an unnamed count
        counted = set()
        for s in sents:
            for m in COUNT.finditer(s):
                noun = m.group("noun").lower()
                if noun in TIME_UNITS or m.group(0).lower() in counted:
                    continue
                n = NUMWORD.get(m.group("n").lower()) or int(m.group("n"))
                if len(name_runs(s)) < n:
                    counted.add(m.group(0).lower())
                    add(REVIEW, first_n, "unnamed count", m.group(0),
                        "The sentence counts more than it names. Name them, or drop the count.")

    # --- Skills: one line, and each item used in a role ---
    skills = [b for b in marked if is_skills(b.section) and b.kind in ("para", "bullet")]
    if len(skills) > 1:
        add(FAIL, skills[1].n, "more than one line under Skills", f"{len(skills)} lines",
            "Skills is one comma-separated line at most.")
    for b in skills:
        _label, colon, rest = b.text.partition(":")
        items = rest if colon and len(_label.split()) <= 3 else b.text
        for item in re.split(r"[,;]", items):
            item = item.strip(" .")
            if item and not item_evidenced(item, bullet_text):
                add(REVIEW, b.n, "skill in no role bullet", item,
                    "Put it in the bullet where you used it, or keep it here if it is minor.")
    return fails, reviews


# -------------------------------------------------------------------- main --

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if len(args) != 1:
        sys.exit(__doc__)
    blocks = load(args[0])
    if not blocks:
        sys.exit("Nothing to read.")
    fails, reviews = review(blocks, load_totals(args[0]))

    print("=" * 70)
    print("DRAFT REVIEW")
    print("=" * 70)
    if fails:
        print("\nFAIL: settled rules broken. Fix these.")
        print("-" * 70)
        for i, name, hit, fix in fails:
            where = f"block {i}" if i else "document"
            print(f"  {where}: {name}: \"{hit}\"")
            print(f"    {fix}")
    else:
        print("\nFAIL: none.")

    if reviews:
        print("\nREVIEW: read these again. Some are right as written.")
        print("-" * 70)
        for i, name, hit, fix in reviews:
            where = f"block {i}" if i else "document"
            print(f"  {where}: {name}: \"{hit}\"")
            print(f"    {fix}")
    else:
        print("\nREVIEW: none.")

    print("\n" + "=" * 70)
    print(f"{len(fails)} to fix, {len(reviews)} to read again.")
    print("No script sees whether the candidate claims the level they worked at,")
    print("whether a stranger gets the line on one read, or whether any writer could")
    print("have written it about anyone. Those three are still yours.")
    print("=" * 70)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
