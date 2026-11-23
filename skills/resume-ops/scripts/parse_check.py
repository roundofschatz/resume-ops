#!/usr/bin/env python3
"""
parse_check.py: a structure check of a .docx resume.

It reads the file the way a simple text reader does, prints the text in file
order, and flags layout that is known to break reading: tables, text boxes,
columns, images, contact details in the page header, hidden text, mixed date
formats, working markers, a missing phone or email.

This is a structure check of the file. It is not a prediction of what Workday
or any other system will fill in. The only real parse test is a live upload
and a field-by-field review of what the form filled in.

Stdlib only.

--repair writes a copy beside the file with the parts a Google Docs export
leaves out (document properties and web settings) added. Every other part is
copied byte for byte, so the text and the layout don't move, and the original
is never changed. Which missing part made Lever refuse a file wasn't isolated
(sources.md, L04), so the repair is a cheap precaution, not a proven fix.

Usage:
    python parse_check.py resume.docx
    python parse_check.py resume.docx --text-only    # just the text, in file order
    python parse_check.py resume.docx --repair       # writes resume-repaired.docx
    python parse_check.py resume.docx --repair --out fixed.docx

Exit codes: 0 no FAIL, 1 at least one FAIL.
"""

import argparse
import datetime
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docx  # noqa: E402

W = _docx.W
KNOWN_HEADERS = _docx.KNOWN_HEADERS
WRITE_HEADERS = _docx.WRITE_HEADERS
HEADERISH = _docx.HEADERISH
EMAIL_RE = _docx.EMAIL_RE
PHONE_RE = _docx.PHONE_RE

# Parts Word writes in every file. The standard needs only the main part, but
# Lever's parser refused a file without these and read the same text with them
# (sources.md, L04). Which one it needed was not isolated, so all are checked.
WORD_PARTS = ("docProps/core.xml", "docProps/app.xml", "word/styles.xml",
              "word/settings.xml", "word/webSettings.xml", "word/fontTable.xml",
              "word/theme/theme1.xml")

# The parts --repair can add. They hold no text and no layout, so adding them
# can't move a line. A missing styles, settings, font or theme part shapes the
# page, so the repair leaves those to a rebuild or a re-save in Word.
_PKG = "http://schemas.openxmlformats.org/package/2006"
_OFF = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REPAIRABLE = {
    "docProps/core.xml": (f"application/vnd.openxmlformats-package.core-properties+xml",
                          "_rels/.rels", f"{_PKG}/relationships/metadata/core-properties",
                          "docProps/core.xml"),
    "docProps/app.xml": ("application/vnd.openxmlformats-officedocument.extended-properties+xml",
                         "_rels/.rels", f"{_OFF}/extended-properties", "docProps/app.xml"),
    "word/webSettings.xml": ("application/vnd.openxmlformats-officedocument.wordprocessingml."
                             "webSettings+xml", "word/_rels/document.xml.rels",
                             f"{_OFF}/webSettings", "webSettings.xml"),
}

NOT_A_PREDICTION = (
    "This is a structure check of the file, not a prediction of what Workday or any "
    "other system will fill in. The only real parse test is a live upload and a "
    "field-by-field review of what the form filled in.")

# One date, classified by how it is written. "May 2017" is spelled the same
# short and long, so it is evidence of neither style and counts as nothing.
_FORMATS = [
    ("May YYYY", re.compile(r"^May\.?\s+(?:19|20)\d{2}$", re.I)),
    ("Mon YYYY", re.compile(r"^(?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?\s+(?:19|20)\d{2}$", re.I)),
    ("Month YYYY", re.compile(r"^(?:January|February|March|April|June|July|August|September|October|November|December)\s+(?:19|20)\d{2}$", re.I)),
    ("MM/YYYY", re.compile(r"^\d{1,2}/(?:19|20)\d{2}$")),
    ("MM/YY", re.compile(r"^\d{1,2}/\d{2}$")),
    ("YYYY only", re.compile(r"^(?:19|20)\d{2}$")),
]

SEPT = re.compile(r"\bSept\.?\s+(?:19|20)\d{2}\b", re.I)

# Working markers that must never reach a delivered file.
PLACEHOLDER_PATTERNS = [
    (re.compile(r"\[[^\]\n]{0,60}\]"), "square-bracketed text"),
    (re.compile(r"\b(?:TK|TBD|FIXME|PLACEHOLDER)\b"), "a working marker"),
    (re.compile(r"\bXX+\b"), "an XX placeholder"),
    (re.compile(r"lorem ipsum", re.I), "filler text"),
]


def date_format(date):
    for name, pat in _FORMATS:
        if pat.match(date.strip()):
            return None if name == "May YYYY" else name
    return None


def date_formats(lines):
    """Count date formats, only in lines that carry a date range: two dates
    joined by a dash, or a date and Present. A date in a sentence is not a
    second format, and neither is a range written with "to" inside a
    sentence, like the earlier-career line."""
    used = {}
    for ln in lines:
        for m in _docx.DASH_RANGE.finditer(ln):
            for part in (m.group("start"), m.group("end")):
                fmt = date_format(part)
                if fmt:
                    used[fmt] = used.get(fmt, 0) + 1
    return used


def check_structure(z):
    """Flag layout features that break or scramble reading."""
    findings = []
    names = z.namelist()
    doc = z.read("word/document.xml").decode("utf-8", "ignore")

    tbl_count = len(re.findall(r"<w:tbl[ >]", doc))
    if tbl_count:
        findings.append(("FAIL", f"{tbl_count} table(s) found. Cells get read across rows and "
                                 "come out scrambled. Rebuild as plain paragraphs."))

    txbx = len(re.findall(r"<w:txbxContent", doc)) + len(re.findall(r"<v:textbox", doc))
    if txbx:
        findings.append(("FAIL", f"{txbx} text box(es) found. Text inside a box is often "
                                 "skipped. Move it into the body."))

    cols = re.findall(r'<w:cols[^>]*w:num="(\d+)"', doc)
    multi = [c for c in cols if int(c) > 1]
    if multi:
        findings.append(("FAIL", f"{max(multi)}-column layout. Columns get read across and "
                                 "mixed together. Use one column."))

    media = [n for n in names if n.startswith("word/media/")]
    if media:
        findings.append(("FAIL", f"{len(media)} image(s) in the file. Workday's own guidance: "
                                 "resumes without images parse best. Take them out."))

    hdrs = [n for n in names if re.match(r"word/(header|footer)\d*\.xml", n)]
    for n in hdrs:
        try:
            r = ET.fromstring(z.read(n))
        except ET.ParseError:
            continue
        t = "".join((e.text or "") for e in r.iter(f"{W}t")).strip()
        if not t:
            continue
        if EMAIL_RE.search(t) or PHONE_RE.search(t):
            findings.append(("FAIL", f"Contact details in the page {n.split('/')[-1][:6]}: "
                                     f"\"{t[:70]}\". Text there is often skipped. Move it into "
                                     "the body, under the name."))
        else:
            findings.append(("WARN", f"Text in the page {n.split('/')[-1][:6]}: \"{t[:70]}\". "
                                     "Text there is often skipped. Move anything that matters "
                                     "into the body."))

    missing = [p for p in WORD_PARTS if p not in names]
    if missing:
        findings.append(("WARN", "The file is missing parts Word always writes ("
                                 + ", ".join(missing) + "). In a live test, Lever's parser "
                                 "refused a file missing these and read the same text once it "
                                 "was saved with them; which part mattered is not known "
                                 "(2026-09-28). Rebuild it with build_resume.py, or open it in "
                                 "Word and save it once."))

    if re.search(r'<w:vanish\s*/>', doc) or re.search(r'w:color[^>]*w:val="FFFFFF"', doc):
        findings.append(("FAIL", "Hidden or white text found. Remove it. Anyone who pastes "
                                 "the resume into a plain text box will see it."))
    return findings


def check_content(blks):
    findings = []
    lines = [t for _k, t in blks]
    body = "\n".join(lines)
    head = "\n".join(lines[:8])

    if not EMAIL_RE.search(head):
        loc = "later in the document" if EMAIL_RE.search(body) else "nowhere"
        findings.append(("FAIL", f"No email in the first 8 lines (found {loc}). Put it on "
                                 "the contact line under the name."))
    if not PHONE_RE.search(head):
        loc = "later in the document" if PHONE_RE.search(body) else "nowhere"
        findings.append(("FAIL", f"No phone number in the first 8 lines (found {loc}). Put "
                                 "it on the contact line under the name."))

    found, odd = [], []
    for ln in lines:
        if _docx.header_kind(ln) != "header":
            continue
        s = ln.strip().strip(":").lower()
        if s in KNOWN_HEADERS:
            found.append(ln.strip())
        else:
            odd.append(ln.strip())
    if not found:
        findings.append(("FAIL", "No standard section headers found. Use plain headers: "
                                 "\"Experience\", \"Education\", \"Summary\", \"Skills\", "
                                 "\"Certifications\"."))
    else:
        findings.append(("OK", f"Standard headers found: {', '.join(sorted(set(found)))}"))
        for h in sorted({h for h in found if h.strip(":").lower() not in WRITE_HEADERS}):
            findings.append(("WARN", f"\"{h}\" is a common header, but it is not one of the five "
                                     "this skill writes. Rename it: Summary, Experience, "
                                     "Education, Certifications or Skills."))
    for h in sorted(set(odd)):
        findings.append(("WARN", f"Non-standard header: \"{h}\". Use one of the five: Summary, "
                                 "Experience, Education, Certifications or Skills. Move its "
                                 "content under one of them."))

    used = date_formats(lines)
    if len(used) > 1:
        detail = ", ".join(f"{n} ({c}x)" for n, c in sorted(used.items()))
        findings.append(("FAIL", f"Mixed date formats in the date lines: {detail}. Use "
                                 "\"Mon YYYY\" everywhere, like \"Mar 2018 \u2013 Present\"."))
    elif used:
        (name, count), = used.items()
        findings.append(("OK", f"One date format in the date lines: {name} ({count} dates)."))
    else:
        findings.append(("WARN", "No date ranges found. Every job needs one, like "
                                 "\"Mar 2018 \u2013 Present\"."))
    for m in sorted(set(SEPT.findall(body))):
        findings.append(("WARN", f"\"{m}\" uses \"Sept\". Write \"Sep\"."))

    for r in _docx.roles(blks):
        if not r["state"]:
            who = r["company"] or r["title"] or f"{r['start']} \u2013 {r['end']}"
            findings.append(("WARN", f"The job \"{who}\" has no \"City, ST\" on its company "
                                     "line. Write it as \"Company, City, ST\"."))

    for pat, label in PLACEHOLDER_PATTERNS:
        for m in pat.finditer(body):
            snippet = m.group(0).replace("\n", " ")[:40]
            findings.append(("FAIL", f"Working marker in the document: {label} \"{snippet}\". "
                                     "Working notes go in the brief, never in the file."))

    words = len(body.split())
    findings.append(("OK", f"{len(lines)} text blocks, about {words} words."))
    return findings


def _insert_before(xml, closing, piece):
    at = xml.rfind(closing)
    if at < 0:
        raise ValueError(f"no {closing} in a package part")
    return xml[:at] + piece + xml[at:]


def _free_id(rels):
    used = set(re.findall(r'\bId="([^"]+)"', rels))
    n = 1
    while f"rIdRepair{n}" in used:
        n += 1
    return f"rIdRepair{n}"


def repair(path, out=None, when=None):
    """Write a copy of a .docx with the missing parts in REPAIRABLE added.
    Returns (copy path or None, parts added, missing parts it can't add)."""
    import build_resume as br    # the build writes the same parts for a new file

    src = Path(path)
    dest = Path(out) if out else src.with_name(f"{src.stem}-repaired{src.suffix}")
    with zipfile.ZipFile(src) as z:
        infos = z.infolist()
        data = {i.filename: z.read(i.filename) for i in infos}
    missing = [p for p in WORD_PARTS if p not in data]
    adding = [p for p in missing if p in REPAIRABLE]
    cannot = [p for p in missing if p not in REPAIRABLE]
    if not adding:
        return None, [], cannot

    first = next((t for _k, t in _docx.blocks(src) if t.strip()), "")
    name = first.strip() if re.fullmatch(r"[A-Za-z][\w.'-]*(?:\s+[A-Za-z][\w.'-]*){0,3}", first.strip()) else "Resume"
    when = when or datetime.datetime.now(datetime.timezone.utc)
    new_parts = {"docProps/core.xml": br.core_props(name, when),
                 "docProps/app.xml": br.app_props(),
                 "word/webSettings.xml": br.web_settings()}

    edited = {k: data[k].decode("utf-8") for k in ("[Content_Types].xml", "_rels/.rels",
                                                   "word/_rels/document.xml.rels") if k in data}
    for part in adding:
        ctype, rels_part, rtype, target = REPAIRABLE[part]
        if f'PartName="/{part}"' not in edited["[Content_Types].xml"]:
            edited["[Content_Types].xml"] = _insert_before(
                edited["[Content_Types].xml"], "</Types>",
                f'<Override PartName="/{part}" ContentType="{ctype}"/>')
        rels = edited.setdefault(rels_part, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                                 f'<Relationships xmlns="{_PKG}/relationships"></Relationships>')
        if f'Target="{target}"' not in rels:
            edited[rels_part] = _insert_before(
                rels, "</Relationships>",
                f'<Relationship Id="{_free_id(rels)}" Type="{rtype}" Target="{target}"/>')

    tmp = dest.with_name(dest.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", edited["[Content_Types].xml"].encode("utf-8"))
        for info in infos:
            if info.filename == "[Content_Types].xml":
                continue
            body = edited[info.filename].encode("utf-8") if info.filename in edited else data[info.filename]
            z.writestr(info, body)
        for name, body in edited.items():          # a relationships part the file didn't have
            if name not in data and name != "[Content_Types].xml":
                z.writestr(name, body.encode("utf-8"))
        for part in adding:
            z.writestr(part, new_parts[part])
    tmp.replace(dest)
    return dest, adding, cannot


def main():
    ap = argparse.ArgumentParser(description="Structure check of a .docx resume. " + NOT_A_PREDICTION)
    ap.add_argument("docx")
    ap.add_argument("--text-only", action="store_true", help="print only the text, in file order")
    ap.add_argument("--repair", action="store_true",
                    help="write a copy with the parts a Google Docs export leaves out, then check it")
    ap.add_argument("--out", help="where --repair writes the copy (default: <name>-repaired.docx)")
    args = ap.parse_args()

    if args.repair:
        _docx.open_docx(args.docx)          # a clear message if it isn't a .docx
        dest, added, cannot = repair(args.docx, args.out)
        print("=" * 68)
        print("REPAIR")
        print("=" * 68)
        if dest:
            print(f"Wrote {dest}")
            print("Added: " + ", ".join(added))
            print("Every other part is copied byte for byte. The original is unchanged.")
        else:
            print("Nothing to add: the file already has the parts --repair writes.")
        if cannot:
            print("Still missing, and not repairable here: " + ", ".join(cannot)
                  + ". These shape the page. Rebuild with build_resume.py, or open the file in "
                  "Word and save it once.")
        print()
        if not dest:
            return 0
        args.docx = str(dest)

    z = _docx.open_docx(args.docx)
    blks = _docx.blocks(args.docx)
    lines = [t for _k, t in blks]

    if args.text_only:
        print("\n".join(lines))
        return 0

    print("=" * 68)
    print("STRUCTURE CHECK")
    print(NOT_A_PREDICTION)
    print("=" * 68)
    print("\nTEXT IN FILE ORDER")
    print("-" * 68)
    for i, ln in enumerate(lines, 1):
        print(f"{i:>3}| {ln}")

    try:
        structure = check_structure(z)
    except KeyError:
        sys.exit(f"No word/document.xml in {args.docx}. Is this a .docx file?")
    findings = structure + check_content(blks)
    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]

    print("\n" + "=" * 68)
    print("FINDINGS")
    print("=" * 68)
    for level in ("FAIL", "WARN", "OK"):
        for lvl, msg in findings:
            if lvl == level:
                print(f"[{lvl:>4}] {msg}")

    print("\n" + "=" * 68)
    verdict = "FAIL" if fails else ("PASS WITH WARNINGS" if warns else "PASS")
    print(f"STRUCTURE CHECK: {verdict}   ({len(fails)} to fix, {len(warns)} warnings)")
    print(NOT_A_PREDICTION)
    print("=" * 68)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
