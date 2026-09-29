#!/usr/bin/env python3
"""
build_resume.py: write the .docx and the plain-text paste version from one
source, so the two cannot drift.

Stdlib only. A .docx is a zip of XML, and this writes the parts by hand: every
part Word itself writes (document properties, settings, web settings, font
table, theme). Lever's parser refused the six-part file 2.0.1 wrote and read the
same text saved with the full set (sources.md, L04).

Each role is a bold "Company, City, ST" line, then the job title in bold and
the dates plain: "Title | Mon YYYY - Mon YYYY" (sources.md, L01, S53).

Usage:
    python build_resume.py resume.json [--out DIR] [--font Calibri]
                                       [--layout company-first] [--plain-title]
                                       [--keep-title-punctuation] [--today YYYY-MM]

Source format: a list of blocks in document order.

    {
      "name": "Jordan Ellis",
      "blocks": [
        {"kind": "name",     "text": "Jordan Ellis"},
        {"kind": "headline", "text": "Logistics Manager for Regional Distribution"},
        {"kind": "contact",  "text": "Dayton, OH | (937) 555-0188 | jordan@example.com"},
        {"kind": "header",   "text": "Summary"},
        {"kind": "para",     "text": "Logistics manager with 9 years ..."},
        {"kind": "header",   "text": "Experience"},
        {"kind": "role", "company": "Northgate Supply", "city": "Dayton", "state": "OH",
         "title": "Logistics Manager", "start": "Apr 2019", "end": "Present"},
        {"kind": "bullet",   "text": "Cut dock-to-stock time from 3 days to 1 ..."},
        {"kind": "earlier",  "text": "Earlier career: Dispatcher at Tri-County Freight in Xenia, OH, 2006 to 2010."},
        {"kind": "header",   "text": "Education"},
        {"kind": "para",     "text": "BS, Supply Chain Management | Wright State University | 2006"},
        {"kind": "header",   "text": "Skills"},
        {"kind": "para",     "text": "SAP EWM, Excel, forklift certification"}
      ]
    }

Block kinds: name, headline, contact, header, para, role, bullet, earlier.
A role has company, city, state, title, start and end, and no "text". The build
lays out its lines. Dates are "Mon YYYY"; end may be "Present".

The build refuses to run (BUILD REFUSED, exit 1, nothing written) on any of:

  - a working marker in any text, like [NEEDS NUMBER] or TBD
  - a header that is not Summary, Experience, Education, Certifications or Skills
  - a role missing a field, or a date not in "Mon YYYY" form
  - a comma or a parenthesis in a title (unless --keep-title-punctuation) or a
    company name
  - a role that ended in the last 15 years with no bullet under it
  - a bullet under Summary, more than one line under Skills, or a line in
    Experience that starts with "Skills:"
  - more than one earlier-career line, or one that is not at the end of
    Experience
  - the retired kinds title, meta and label

It warns, and still builds, when the contact line has no phone or no email.

Then check what it wrote:

    python scripts/parse_check.py Jordan-Ellis-Resume.docx
    python scripts/render_pdf.py Jordan-Ellis-Resume.docx
    python scripts/widow_check.py Jordan-Ellis-Resume.docx <the PDF path it printed>
"""

import argparse
import datetime
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docx  # noqa: E402

# The five. references/document.md owns why.
WRITE_HEADERS = _docx.WRITE_HEADERS

# references/document.md. Any other font substitutes on a machine that does
# not have it, and the substitute breaks lines in different places, which
# changes what widow_check.py measures on the render.
SAFE_FONTS = {"calibri", "arial", "helvetica", "georgia", "garamond",
              "times new roman"}

PLACEHOLDERS = [
    (re.compile(r"\[[^\]\n]{0,60}\]"), "square-bracketed text"),
    (re.compile(r"\b(?:TK|TBD|FIXME|PLACEHOLDER)\b"), "a working marker"),
    (re.compile(r"\bXX+\b"), "an XX placeholder"),
    (re.compile(r"lorem ipsum", re.I), "filler text"),
]

KINDS = ("name", "headline", "contact", "header", "para", "role", "bullet", "earlier")
ROLE_FIELDS = ("company", "city", "state", "title", "start", "end")

RETIRED = {
    "title": "Write each job as one \"role\" block with company, city, state, title, "
             "start and end. The build lays out the lines.",
    "meta": "Write each job as one \"role\" block with company, city, state, title, "
            "start and end. The build lays out the lines.",
    "label": "Skills is one line now: a single \"para\" under the Skills header. "
             "Labeled skill groups are gone.",
}

DATE_RE = re.compile(r"^(%s) ((?:19|20)\d{2})$" % "|".join(_docx.MONTHS))

# The role layout. The live Workday test on 2026-09-28 uploaded one resume in
# each layout. Company first filled 8 of 8 companies, titles, cities and dates.
# Title first and one line glued the title into the company field.
LAYOUTS = ("company-first", "title-first", "one-line")
DEFAULT_LAYOUT = "company-first"

# Sep 14 spacing spec. Half-point size, space before (pt), space after (pt), bold.
STYLE = {
    "name":       (32, 0, 3, True),
    "headline":   (21, 0, 3, True),
    "contact":    (21, 0, 3, False),
    "header":     (24, 6, 3, True),
    "para":       (21, 0, 2, False),
    "title-line": (21, 3, 2, True),
    "meta-line":  (21, 0, 2, False),
    "bullet":     (21, 0, 1, False),
}
# Margins in twentieths of a point. 720 is half an inch, on all four sides.
MARGIN = 720

NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


# ---------------------------------------------------------------- checks

def _ym(date, today):
    """'Mar 2018' -> months since year 0. 'Present' -> today."""
    if date == "Present":
        return today[0] * 12 + today[1]
    m = DATE_RE.match(date)
    return int(m.group(2)) * 12 + _docx.MONTHS.index(m.group(1)) + 1


def _date_problem(value, may_be_present):
    if may_be_present and value == "Present":
        return None
    if DATE_RE.match(value):
        return None
    if re.match(r"^Sept\b", value, re.I):
        return f"\"{value}\" uses \"Sept\". Write \"Sep\", like \"Sep 2021\"."
    allowed = "\"Mon YYYY\", like \"Mar 2018\""
    if may_be_present:
        allowed += ", or \"Present\""
    return (f"\"{value}\" is not in the right form. Use {allowed}. Months are "
            f"{' '.join(_docx.MONTHS)}.")


def _text_of(b):
    """Every string in a block that ends up on the page."""
    if b.get("kind") == "role":
        return [str(b.get(f, "")) for f in ROLE_FIELDS if isinstance(b.get(f), str)]
    t = b.get("text")
    return [t] if isinstance(t, str) else []


def check_blocks(blocks, keep_title_punctuation=False):
    """Per-block faults. Returns a list of reasons."""
    bad = []
    for i, b in enumerate(blocks, 1):
        if not isinstance(b, dict):
            bad.append(f"block {i}: not an object.")
            continue
        kind = b.get("kind")
        if kind in RETIRED:
            bad.append(f"block {i}: the \"{kind}\" kind is retired. {RETIRED[kind]}")
            continue
        if kind not in KINDS:
            bad.append(f"block {i}: unknown kind {kind!r}. Use one of: {', '.join(KINDS)}.")
            continue

        if kind == "role":
            if "text" in b:
                bad.append(f"block {i} (role): a role has no \"text\" field. Put the parts in "
                           "company, city, state, title, start and end.")
            missing = [f for f in ROLE_FIELDS
                       if not isinstance(b.get(f), str) or not b.get(f).strip()]
            if missing:
                bad.append(f"block {i} (role): missing {', '.join(missing)}. Every role needs "
                           "company, city, state, title, start and end.")
            for f, present_ok in (("start", False), ("end", True)):
                v = b.get(f)
                if isinstance(v, str) and v.strip():
                    why = _date_problem(v.strip(), present_ok)
                    if why:
                        bad.append(f"block {i} (role): {f} date {why}")
            for f in ("title", "company"):
                v = b.get(f)
                if f == "title" and keep_title_punctuation:
                    continue
                if isinstance(v, str) and re.search(r"[,()]", v):
                    if f == "title":
                        why = ("Workday keeps only the text before a comma or an opening "
                               "parenthesis in a title.")
                        fix = ("Write the title with the descriptor first and no punctuation: "
                               "\"Senior Analyst, Supply Chain\" becomes \"Supply Chain "
                               "Senior Analyst\". Or build with --keep-title-punctuation "
                               "and fix the form field by hand.")
                    else:
                        why = "The company line \"Company, City, ST\" splits on commas."
                        fix = ("Keep a legal suffix without the comma: \"Acme, Inc.\" "
                               "becomes \"Acme Inc.\".")
                    bad.append(f"block {i} (role): the {f} \"{v}\" has a comma or a parenthesis. "
                               f"{why} {fix}")
        else:
            text = b.get("text")
            if text is None:
                bad.append(f"block {i} ({kind}): no \"text\" field.")
                continue
            if not isinstance(text, str):
                bad.append(f"block {i} ({kind}): \"text\" is {type(text).__name__}, not a string.")
                continue
            if not text.strip():
                bad.append(f"block {i} ({kind}): \"text\" is empty.")
                continue
            if kind == "header" and text.strip().strip(":").lower() not in WRITE_HEADERS:
                bad.append(f"block {i}: header \"{text}\" is not one of the five. Move the "
                           "content into Summary, Experience, Education, Certifications or Skills.")

        for text in _text_of(b):
            for pat, label in PLACEHOLDERS:
                m = pat.search(text)
                if m:
                    bad.append(f"block {i}: {label} \"{m.group(0)[:40]}\". Working notes go in "
                               "the brief, never in the file.")
    return bad


def check_structure(blocks, today):
    """Faults in how the blocks sit together. Runs only on blocks that passed
    check_blocks, so every field it reads is there and well formed."""
    bad = []
    section = ""
    skills_lines = 0
    earlier = []          # block numbers of earlier-career lines
    misplaced = False     # reported the earlier line out of place already
    open_role = None      # [block number, block, bullets so far]
    roles = []

    def close_role():
        if open_role:
            roles.append(open_role)

    for i, b in enumerate(blocks, 1):
        kind = b["kind"]
        if kind == "header":
            close_role()
            open_role = None
            section = b["text"].strip().strip(":").lower()
            continue
        text = b.get("text", "")

        if (earlier and not misplaced and section == "experience"
                and kind in ("role", "bullet", "para")):
            bad.append(f"block {earlier[-1]}: the earlier-career line must be the last line "
                       "of Experience. Move it below the last role.")
            misplaced = True

        if section == "summary" and kind == "bullet":
            bad.append(f"block {i}: a bullet under Summary. The summary is prose only. "
                       "Write it as one \"para\".")
        if section == "skills" and kind in ("para", "bullet"):
            skills_lines += 1
        if section == "experience" and kind in ("para", "bullet") \
                and text.strip().lower().startswith("skills:"):
            bad.append(f"block {i}: a \"Skills:\" line inside Experience. Per-role skills "
                       "lines are not used. Put each tool in the bullet that shows the work. "
                       "The one Skills line is for minor tools.")
        if kind == "role":
            close_role()
            if section != "experience":
                bad.append(f"block {i}: a role outside Experience. Roles go under the "
                           "Experience header.")
            open_role = [i, b, 0]
            continue
        if kind == "bullet" and open_role:
            open_role[2] += 1
        if kind == "earlier":
            close_role()
            open_role = None
            if section != "experience":
                bad.append(f"block {i}: the earlier-career line is outside Experience. Put it "
                           "at the end of Experience.")
            earlier.append(i)
            if re.search(r"\b(?:19|20)\d{2}\s*[-\u2013\u2014]\s*(?:(?:19|20)\d{2}|Present)\b",
                         b.get("text") or ""):
                bad.append(f"block {i}: write the years on the earlier-career line as "
                           "\"2004 to 2010\", not with a dash. A dash range there reads as a "
                           "second date format next to the Mon YYYY roles.")
    close_role()

    if len(earlier) > 1:
        bad.append(f"blocks {', '.join(map(str, earlier))}: {len(earlier)} earlier-career "
                   "lines. Use one line for every role older than 15 years.")
    if skills_lines > 1:
        bad.append(f"Skills has {skills_lines} lines. Skills is one line: one \"para\" with "
                   "the tools, separated by commas.")

    now = today[0] * 12 + today[1]
    for n, b, bullets in roles:
        if bullets:
            continue
        if now - _ym(b["end"], today) <= 15 * 12:
            bad.append(f"block {n}: the role \"{b['title']}\" at {b['company']} ended in the "
                       "last 15 years and has no bullet under it. Add at least one bullet "
                       "that shows what you did there.")
    return bad


def contact_warnings(blocks):
    contact = " ".join(b.get("text", "") for b in blocks
                       if isinstance(b, dict) and b.get("kind") == "contact"
                       and isinstance(b.get("text"), str))
    out = []
    if not _docx.PHONE_RE.search(contact):
        out.append("The contact line has no phone number. Application forms ask for one. "
                   "Add it if the candidate gives one.")
    if not _docx.EMAIL_RE.search(contact):
        out.append("The contact line has no email address. Add one.")
    return out


def refuse(reasons):
    print("BUILD REFUSED\n")
    for line in reasons:
        print("  " + line)
    print("\nNothing was written.")
    sys.exit(1)


# ---------------------------------------------------------------- layout

def role_lines(b, layout=DEFAULT_LAYOUT, bold_title=True):
    """The lines a role block becomes, as (style, [(text, bold), ...]).

    company-first:  bold "Company, City, ST"   then  bold "Title" and " | Mon YYYY \u2013 Mon YYYY"
    title-first:    bold "Title"               then  "Company, City, ST | dates"
    one-line:       bold "Title", then " | Company | City, ST | dates" on the same line

    The title is bold because recruiters' eyes go to job titles first (Ladders
    eye-tracking, 2018, S53). `bold_title=False` keeps the company-only bold
    that the first live Workday test used (L01), for a side-by-side test.
    """
    place = f"{b['city'].strip()}, {b['state'].strip()}"
    dates = f"{b['start'].strip()} \u2013 {b['end'].strip()}"
    title, company = b["title"].strip(), b["company"].strip()
    if layout == "company-first":
        meta = ([(title, True), (f" | {dates}", False)] if bold_title
                else [(f"{title} | {dates}", False)])
        return [("title-line", [(f"{company}, {place}", True)]),
                ("meta-line", meta)]
    if layout == "title-first":
        return [("title-line", [(title, True)]),
                ("meta-line", [(f"{company}, {place} | {dates}", False)])]
    if layout == "one-line":
        return [("title-line", [(title, True), (f" | {company} | {place} | {dates}", False)])]
    raise ValueError(f"unknown layout {layout!r}")


def lines_of(blocks, layout, bold_title=True):
    """Every paragraph as (style, runs, block kind), in order. The .docx and the
    .txt are both written from this one list."""
    out = []
    for b in blocks:
        k = b["kind"]
        if k == "role":
            out.extend((s, runs, k) for s, runs in role_lines(b, layout, bold_title))
        elif k == "earlier":
            out.append(("para", [(b["text"], False)], k))
        else:
            out.append((k, [(b["text"], STYLE[k][3])], k))
    return out


def para_xml(style, runs):
    half, before, after, _bold = STYLE[style]
    num = ('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
           if style == "bullet" else "")

    def rpr(bold):
        return (f'<w:rPr>{"<w:b/>" if bold else ""}<w:sz w:val="{half}"/>'
                f'<w:szCs w:val="{half}"/></w:rPr>')

    body = "".join(f'<w:r>{rpr(bold)}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
                   for text, bold in runs)
    return ("<w:p><w:pPr>"
            f"{num}"
            f'<w:spacing w:before="{before * 20}" w:after="{after * 20}" w:line="240" '
            'w:lineRule="auto"/>'
            f"{rpr(runs[0][1])}"
            "</w:pPr>"
            f"{body}</w:p>")


def document(paras):
    body = "".join(para_xml(style, runs) for style, runs, _k in paras)
    sect = ('<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
            f'<w:pgMar w:top="{MARGIN}" w:right="{MARGIN}" w:bottom="{MARGIN}" '
            f'w:left="{MARGIN}" w:header="0" w:footer="0" w:gutter="0"/></w:sectPr>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document {NS}><w:body>{body}{sect}</w:body></w:document>')


SERIF_FONTS = {"georgia", "garamond", "times new roman"}
NS_R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
XML_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def styles(font):
    """The styles Word itself always writes: document defaults, Normal, the
    default character, table and list styles."""
    return (
        f'{XML_HEAD}<w:styles {NS}><w:docDefaults><w:rPrDefault><w:rPr>'
        f'<w:rFonts w:ascii="{font}" w:eastAsia="{font}" w:hAnsi="{font}" w:cs="{font}"/>'
        '<w:sz w:val="21"/><w:szCs w:val="21"/>'
        '<w:lang w:val="en-US" w:eastAsia="en-US" w:bidi="ar-SA"/>'
        '</w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
        '</w:pPr></w:pPrDefault></w:docDefaults>'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:qFormat/></w:style>'
        '<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont">'
        '<w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/>'
        '<w:unhideWhenUsed/></w:style>'
        '<w:style w:type="table" w:default="1" w:styleId="TableNormal">'
        '<w:name w:val="Normal Table"/><w:uiPriority w:val="99"/><w:semiHidden/>'
        '<w:unhideWhenUsed/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar>'
        '<w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/>'
        '</w:tblCellMar></w:tblPr></w:style>'
        '<w:style w:type="numbering" w:default="1" w:styleId="NoList">'
        '<w:name w:val="No List"/><w:uiPriority w:val="99"/><w:semiHidden/>'
        '<w:unhideWhenUsed/></w:style></w:styles>'
    )


def numbering(font):
    return (
        f'{XML_HEAD}<w:numbering {NS}>'
        '<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>'
        '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
        '<w:lvlText w:val="\u2022"/><w:lvlJc w:val="left"/>'
        '<w:pPr><w:ind w:left="360" w:hanging="216"/></w:pPr>'
        f'<w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:hint="default"/></w:rPr>'
        '</w:lvl></w:abstractNum>'
        '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'
    )


def settings():
    return (
        f'{XML_HEAD}<w:settings {NS}><w:zoom w:percent="100"/>'
        '<w:defaultTabStop w:val="720"/><w:characterSpacingControl w:val="doNotCompress"/>'
        '<w:compat><w:compatSetting w:name="compatibilityMode" '
        'w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
        '</w:settings>'
    )


def web_settings():
    return f'{XML_HEAD}<w:webSettings {NS}><w:optimizeForBrowser/><w:allowPNG/></w:webSettings>'


def font_table(font):
    family = "roman" if font.strip().lower() in SERIF_FONTS else "swiss"
    return (
        f'{XML_HEAD}<w:fonts {NS} {NS_R}>'
        f'<w:font w:name="{escape(font)}"><w:charset w:val="00"/>'
        f'<w:family w:val="{family}"/><w:pitch w:val="variable"/></w:font>'
        '</w:fonts>'
    )


def theme(font):
    """A small, valid Office theme. Word writes one in every file."""
    solid = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    colors = "".join(f'<a:{n}><a:srgbClr val="{v}"/></a:{n}>' for n, v in (
        ("dk2", "44546A"), ("lt2", "E7E6E6"), ("accent1", "4472C4"), ("accent2", "ED7D31"),
        ("accent3", "A5A5A5"), ("accent4", "FFC000"), ("accent5", "5B9BD5"),
        ("accent6", "70AD47"), ("hlink", "0563C1"), ("folHlink", "954F72")))
    face = (f'<a:latin typeface="{escape(font)}"/><a:ea typeface=""/><a:cs typeface=""/>')
    return (
        f'{XML_HEAD}<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'name="Office Theme"><a:themeElements><a:clrScheme name="Office">'
        '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
        '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
        f'{colors}</a:clrScheme>'
        f'<a:fontScheme name="Office"><a:majorFont>{face}</a:majorFont>'
        f'<a:minorFont>{face}</a:minorFont></a:fontScheme>'
        '<a:fmtScheme name="Office">'
        f'<a:fillStyleLst>{solid * 3}</a:fillStyleLst>'
        '<a:lnStyleLst>' + f'<a:ln w="6350">{solid}</a:ln>' * 3 + '</a:lnStyleLst>'
        '<a:effectStyleLst>' + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3 +
        '</a:effectStyleLst>'
        f'<a:bgFillStyleLst>{solid * 3}</a:bgFillStyleLst></a:fmtScheme>'
        '</a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>'
    )


def core_props(name, when):
    stamp = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    who = escape(name)
    return (
        f'{XML_HEAD}<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        f'<dc:title>{who} Resume</dc:title><dc:creator>{who}</dc:creator>'
        f'<cp:lastModifiedBy>{who}</cp:lastModifiedBy><cp:revision>1</cp:revision>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{stamp}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{stamp}</dcterms:modified>'
        '</cp:coreProperties>'
    )


def app_props():
    """Document properties Word writes. No Application element: File,
    Properties would show it to anyone who opens the file, and the file claims
    no program it was not made in."""
    return (
        f'{XML_HEAD}<Properties '
        'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Template>Normal.dotm</Template><TotalTime>0</TotalTime><DocSecurity>0</DocSecurity>'
        '<ScaleCrop>false</ScaleCrop><LinksUpToDate>false</LinksUpToDate>'
        '<SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged>'
        '</Properties>'
    )


_WML = "application/vnd.openxmlformats-officedocument.wordprocessingml"
CONTENT_TYPES = (
    f'{XML_HEAD}'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    f'<Override PartName="/word/document.xml" ContentType="{_WML}.document.main+xml"/>'
    f'<Override PartName="/word/styles.xml" ContentType="{_WML}.styles+xml"/>'
    f'<Override PartName="/word/numbering.xml" ContentType="{_WML}.numbering+xml"/>'
    f'<Override PartName="/word/settings.xml" ContentType="{_WML}.settings+xml"/>'
    f'<Override PartName="/word/webSettings.xml" ContentType="{_WML}.webSettings+xml"/>'
    f'<Override PartName="/word/fontTable.xml" ContentType="{_WML}.fontTable+xml"/>'
    '<Override PartName="/word/theme/theme1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
    '<Override PartName="/docProps/core.xml" '
    'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    '<Override PartName="/docProps/app.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
    '</Types>'
)

_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
ROOT_RELS = (
    f'{XML_HEAD}'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    f'<Relationship Id="rId3" Type="{_REL}/extended-properties" Target="docProps/app.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/'
    'relationships/metadata/core-properties" Target="docProps/core.xml"/>'
    f'<Relationship Id="rId1" Type="{_REL}/officeDocument" Target="word/document.xml"/>'
    '</Relationships>'
)

DOC_RELS = (
    f'{XML_HEAD}'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    f'<Relationship Id="rId1" Type="{_REL}/styles" Target="styles.xml"/>'
    f'<Relationship Id="rId2" Type="{_REL}/numbering" Target="numbering.xml"/>'
    f'<Relationship Id="rId3" Type="{_REL}/settings" Target="settings.xml"/>'
    f'<Relationship Id="rId4" Type="{_REL}/webSettings" Target="webSettings.xml"/>'
    f'<Relationship Id="rId5" Type="{_REL}/fontTable" Target="fontTable.xml"/>'
    f'<Relationship Id="rId6" Type="{_REL}/theme" Target="theme/theme1.xml"/>'
    '</Relationships>'
)

# Every part Word writes. The six-part file 2.0.1 wrote parsed on Workday but
# was refused by Lever's parser in a live test (L04); the same text saved with
# the full set parsed. The standard needs only the main part (S90); this parser
# was stricter.
PACKAGE_PARTS = (
    "[Content_Types].xml", "_rels/.rels", "docProps/core.xml", "docProps/app.xml",
    "word/_rels/document.xml.rels", "word/document.xml", "word/styles.xml",
    "word/numbering.xml", "word/settings.xml", "word/webSettings.xml",
    "word/fontTable.xml", "word/theme/theme1.xml",
)


def docx_bytes(paras, font, name="Resume", when=None):
    """Build the whole package in memory, so a fault cannot leave a half-written
    .docx on disk."""
    when = when or datetime.datetime.now(datetime.timezone.utc)
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "docProps/core.xml": core_props(name, when),
        "docProps/app.xml": app_props(),
        "word/_rels/document.xml.rels": DOC_RELS,
        "word/document.xml": document(paras),
        "word/styles.xml": styles(font),
        "word/numbering.xml": numbering(font),
        "word/settings.xml": settings(),
        "word/webSettings.xml": web_settings(),
        "word/fontTable.xml": font_table(font),
        "word/theme/theme1.xml": theme(font),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for part in PACKAGE_PARTS:
            z.writestr(part, parts[part])
    return buf.getvalue()


def text_bytes(paras):
    out = []
    for style, runs, _k in paras:
        t = "".join(text for text, _b in runs)
        if style == "header":
            out += ["", t.upper(), ""]
        elif style == "bullet":
            out.append("- " + t)
        else:
            out.append(t)
    return ("\n".join(out).strip() + "\n").encode("utf-8")


def write_both(files):
    """Write every file to a temp name first, then swap them all in. If any
    write fails, remove the temp files and leave the old files as they were,
    so the .docx and the .txt never come from two different runs."""
    temps = []
    try:
        for path, data in files:
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_bytes(data)
            temps.append((tmp, path))
    except OSError as e:
        for tmp, _p in temps:
            try:
                tmp.unlink()
            except OSError:
                pass
        sys.exit(f"Could not write the files: {e}. Nothing was changed.")
    for tmp, path in temps:
        os.replace(tmp, path)


def parse_today(value):
    if value is None:
        d = datetime.date.today()
        return d.year, d.month
    m = re.fullmatch(r"((?:19|20)\d{2})-(\d{1,2})", value.strip())
    if not m or not 1 <= int(m.group(2)) <= 12:
        sys.exit(f"--today must look like 2026-09, not \"{value}\".")
    return int(m.group(1)), int(m.group(2))


def main():
    ap = argparse.ArgumentParser(
        description="Write the .docx and the plain-text version of a resume from one "
                    "JSON source.")
    ap.add_argument("source", help="JSON source file")
    ap.add_argument("--out", default=".", help="output folder (default: here)")
    ap.add_argument("--font", default="Calibri")
    ap.add_argument("--layout", choices=LAYOUTS, default=DEFAULT_LAYOUT,
                    help="How each role's lines are laid out. company-first (the default) "
                         "puts a bold 'Company, City, ST' line above 'Title | Mon YYYY - "
                         "Mon YYYY'. The live Workday test on 2026-09-28 picked "
                         "company-first: it filled every company, title, city and date. "
                         "title-first and one-line glued the title into the company field "
                         "in that test. They are kept only so a later live test can "
                         "re-run them.")
    ap.add_argument("--plain-title", action="store_true",
                    help="company-first only: leave the job title plain, with bold on the "
                         "company line alone, as in the first live Workday test. The default "
                         "bolds the title too, because recruiters look at job titles first "
                         "(Ladders, 2018). Kept for a side-by-side upload test.")
    ap.add_argument("--keep-title-punctuation", action="store_true",
                    help="allow a comma or parenthesis in a title because the candidate chose it. "
                         "Workday will keep only the text before it, so the title field has to be "
                         "fixed by hand on every form.")
    ap.add_argument("--today", default=None, metavar="YYYY-MM",
                    help="the date the 15-year rule counts back from (default: today)")
    args = ap.parse_args()
    today = parse_today(args.today)

    try:
        data = json.loads(Path(args.source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        sys.exit(f"Cannot read {args.source}: {e}")

    if isinstance(data, list):
        blocks, name = data, None
    elif isinstance(data, dict):
        blocks, name = data.get("blocks"), data.get("name")
    else:
        blocks, name = None, None
    if not isinstance(blocks, list) or not blocks:
        sys.exit("No blocks in the source file. It needs a \"blocks\" list.")

    reasons = check_blocks(blocks, args.keep_title_punctuation)
    if reasons:
        refuse(reasons)
    reasons = check_structure(blocks, today)
    if reasons:
        refuse(reasons)

    for w in contact_warnings(blocks):
        print(f"WARNING: {w}", file=sys.stderr)
    if args.font.strip().lower() not in SAFE_FONTS:
        print(f"WARNING: \"{args.font}\" is not one of the fonts in "
              f"references/document.md ({', '.join(sorted(SAFE_FONTS))}). "
              "A machine without it swaps in another font, and that font breaks "
              "lines in different places.", file=sys.stderr)

    # Build both files completely before writing either one.
    if not name:
        name = next((b["text"] for b in blocks if b.get("kind") == "name"), "Resume")
    paras = lines_of(blocks, args.layout, bold_title=not args.plain_title)
    doc = docx_bytes(paras, args.font, name)
    txt = text_bytes(paras)

    stem = "-".join(name.split()) + "-Resume"
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_both([(out / f"{stem}.docx", doc), (out / f"{stem}.txt", txt)])
    print(f"{stem}.docx and {stem}.txt written from {len(blocks)} blocks in one source "
          f"(layout: {args.layout}).")
    print("Next: run parse_check.py, render_pdf.py, then widow_check.py.")


if __name__ == "__main__":
    main()
