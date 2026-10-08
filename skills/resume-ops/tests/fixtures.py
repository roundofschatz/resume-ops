"""Shared test fixtures for resume-ops. Stdlib only.

BLOCKS is a correct v2.0 source document: it should pass every check. If a
check fails on it, either the check or the fixture is wrong, and the fixture
test in test_draft_review.py says which.

write_docx() writes a minimal .docx straight from blocks, independent of
build_resume.py, so reader tests do not depend on the writer. It renders a
role the same way the build's default layout does: a company line, then a
"Title | dates" line.
"""

import locale
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run(script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


BLOCKS = [
    {"kind": "name", "text": "Dana Reyes"},
    {"kind": "headline", "text": "Maintenance and Reliability Leader for Discrete Manufacturing"},
    {"kind": "contact",
     "text": "Toledo, OH | (419) 555-0134 | dana@example.com | linkedin.com/in/danareyes"},
    {"kind": "header", "text": "Summary"},
    {"kind": "para",
     "text": "Maintenance supervisor with 11 years keeping CNC and hydraulic lines running in "
             "discrete manufacturing. Rebuilt the preventive maintenance schedule at Brightline "
             "Tool and cut unplanned downtime from 14 hours to 4 per week. The technician on "
             "the night shift knows the machine better than any manual, so training comes "
             "before new equipment."},
    {"kind": "header", "text": "Experience"},
    {"kind": "role", "company": "Brightline Tool", "city": "Toledo", "state": "OH",
     "title": "Maintenance Supervisor", "start": "Mar 2018", "end": "Present"},
    {"kind": "bullet",
     "text": "Maintained 22 CNC machines across two shifts and rebuilt the preventive "
             "maintenance schedule in Fiix, cutting unplanned downtime from 14 hours to 4 per week."},
    {"kind": "bullet", "text": "Trained 6 technicians on the new hydraulics procedure."},
    {"kind": "role", "company": "Keller Plastics", "city": "Findlay", "state": "OH",
     "title": "Maintenance Technician", "start": "Jun 2010", "end": "Feb 2018"},
    {"kind": "bullet",
     "text": "Rewired the ladder logic on 4 Allen-Bradley PLCs, ending a weekly jam on the "
             "blow-molding line."},
    {"kind": "earlier",
     "text": "Earlier career: Line Operator at Maumee Molding in Maumee, OH, 2004 to 2010."},
    {"kind": "header", "text": "Education"},
    {"kind": "para", "text": "AAS, Industrial Maintenance | Owens Community College | 2009"},
    {"kind": "header", "text": "Skills"},
    {"kind": "para", "text": "Fiix, Allen-Bradley PLCs, hydraulics"},
]

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _p(text, bullet=False, bold=False):
    num = ('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>' if bullet else "")
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return (f"<w:p><w:pPr>{num}</w:pPr><w:r>{rpr}"
            f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>')


def role_lines(b):
    """The default layout: company line, then title and dates."""
    return (f"{b['company']}, {b['city']}, {b['state']}",
            f"{b['title']} | {b['start']} – {b['end']}")


def write_docx(blocks, path, bare=False):
    """A small .docx of the blocks. `bare=True` leaves out the parts Word always
    writes (document properties and settings), like the v2.0 builder did."""
    body = []
    for b in blocks:
        k = b["kind"]
        if k == "role":
            first, second = role_lines(b)
            body.append(_p(first, bold=True))
            body.append(_p(second))
        elif k == "bullet":
            body.append(_p(b["text"], bullet=True))
        else:
            body.append(_p(b["text"], bold=k in ("name", "header")))
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document {W}><w:body>{"".join(body)}</w:body></w:document>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
          'officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
        if not bare:
            head = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            z.writestr("docProps/core.xml", head + '<cp:coreProperties xmlns:cp="http://schemas.'
                       'openxmlformats.org/package/2006/metadata/core-properties"/>')
            z.writestr("docProps/app.xml", head + '<Properties xmlns="http://schemas.openxmlformats'
                       '.org/officeDocument/2006/extended-properties"/>')
            for part, root in (("word/styles.xml", "styles"), ("word/settings.xml", "settings"),
                               ("word/webSettings.xml", "webSettings"),
                               ("word/fontTable.xml", "fonts")):
                z.writestr(part, head + f"<w:{root} {W}/>")
            z.writestr("word/theme/theme1.xml", head + '<a:theme xmlns:a="http://schemas.'
                       'openxmlformats.org/drawingml/2006/main" name="Office Theme"/>')
    return Path(path)


def tiny_pdf(lines):
    """A one-page PDF with one text line per entry, written by hand. The font
    uses WinAnsiEncoding, so a line can hold an en dash or an accented letter."""
    ops = "BT /F1 11 Tf 72 720 Td 14 TL " + " ".join(
        "(" + ln.replace("(", "[").replace(")", "]") + ") Tj T*" for ln in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(ops)} >>\nstream\n{ops}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    out, offsets = "%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("cp1252")


def xpdf_run(text):
    """A stand-in for subprocess.run that answers like the pdftotext Git for
    Windows ships (xpdf 4.00): `text` in Latin-1, with an en dash as byte 0xAD,
    unless the command asks for UTF-8 with -enc. Like subprocess.run, it
    decodes the output only when the caller asks for text."""
    def fake(cmd, **kw):
        utf8 = "-enc" in cmd and cmd[cmd.index("-enc") + 1] == "UTF-8"
        raw = text.encode("utf-8") if utf8 else text.replace("\u2013", "\xad").encode("latin-1")
        enc = kw.get("encoding")
        if not enc and kw.get("text"):
            enc = locale.getpreferredencoding(False)
        out = raw.decode(enc, kw.get("errors") or "strict") if enc else raw
        return subprocess.CompletedProcess(cmd, 0, out, "" if enc else b"")
    return fake
