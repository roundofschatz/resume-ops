#!/usr/bin/env python3
"""
positioning_check.py: read a positioning file from job-seeker-ops's
candidate-positioning skill, and check a built resume against it.

A positioning file holds the case for one candidate and one posting: what the
hiring team is buying, the case in four lines, the proofs ranked for the
posting, the words the candidate can claim, and what stays off the page. It
sets direction and order. It is not evidence: every fact on the resume still
comes from the candidate's own files (references/tailoring.md, A positioning
file). Nothing else in resume-ops reads it, so a build without one runs exactly
as before.

Usage:
    python positioning_check.py positioning-acme-planner.md
    python positioning_check.py positioning-acme-planner.md --posting posting.md
    python positioning_check.py positioning-acme-planner.md --resume out/Name-Resume.docx

At intake, it says whether the file can be used and prints what the build takes
from it. After the build, --resume fails when a phrase from the file's keep-off
list is on the page, and reports which of its words to use the page holds,
matched the way term_coverage.py matches terms.

Exit codes: 0 the file can be used, or the resume passes; 1 the file can't be
used, or a keep-off phrase is on the page; 2 the file can't be read. Stdlib only.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FORMAT = "1"
SECTION = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")
FIELD = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*(.*)$")
QUOTE = re.compile(r'"([^"]+)"')
CURLY = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})
CASE = ("What they want", "Where the candidate stands", "The story the evidence tells",
        "What the reader should believe")
TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".text", ".csv"}


class Unreadable(Exception):
    pass


def lines_of(path):
    data = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def file_hash(path, length=12):
    """The same hash the positioning file's stamp holds: a text file's line
    endings count as plain newlines, so a copy saved with CRLF still matches."""
    data = Path(path).read_bytes()
    if Path(path).suffix.lower() in TEXT_SUFFIXES:
        if data.startswith(b"\xef\xbb\xbf"):
            data = data[3:]
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()[:length]


def cells(line):
    inner = line.strip().strip("|")
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", inner)]


def rows_after_header(block, first_column):
    """Data rows of the first grid in block whose first header cell is first_column."""
    out, on = [], False
    for _n, text in block:
        if not text.strip().startswith("|"):
            if on:
                break
            continue
        row = cells(text)
        if not on:
            if row and row[0].lower() == first_column.lower():
                on = True
            continue
        if set("".join(row)) <= set("-: "):
            continue
        out.append(row)
    return out


def norm(text):
    text = text.translate(CURLY).lower()
    return re.sub(r"\s+", " ", text).strip()


class Positioning:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file():
            raise Unreadable(f"{self.path} doesn't exist.")
        self.lines = lines_of(self.path)
        fmt = next((re.match(r"^Format:\s*candidate-positioning\s+(\S+)", t.strip())
                    for t in self.lines if t.strip().startswith("Format:")), None)
        if not fmt:
            raise Unreadable(f"{self.path.name} has no format line, so it isn't a positioning file.")
        if fmt.group(1).rstrip(".") != FORMAT:
            raise Unreadable(f"{self.path.name} is format {fmt.group(1)}, and this resume-ops reads "
                             f"format {FORMAT}. Update resume-ops, or build without it.")
        self.sections = {}
        heads = [(n, m) for n, m in ((n, SECTION.match(t)) for n, t in enumerate(self.lines, 1)) if m]
        for i, (n, m) in enumerate(heads):
            end = heads[i+1][0] if i+1 < len(heads) else len(self.lines)+1
            self.sections[int(m.group(1))] = [(k, self.lines[k-1]) for k in range(n+1, end)]
        missing = [str(i) for i in range(1, 9) if i not in self.sections]
        if missing:
            raise Unreadable(f"{self.path.name} is missing section(s) {', '.join(missing)}. Run "
                             "candidate-positioning's check_positioning.py on it.")
        self.target = self.fields(1)
        self.stamp_fields = self.fields(8)
        self.case = self.read_case()
        self.proofs = self.read_proofs()
        self.rows = rows_after_header(self.sections[2], "#")
        self.terms = [r[0] for r in rows_after_header(self.sections[6], "Posting term") if r and r[0]]
        self.keep_off = self.read_keep_off()
        self.files = rows_after_header(self.sections[8], "File")

    def fields(self, number):
        out = {}
        for _n, text in self.sections.get(number, []):
            m = FIELD.match(text)
            if m:
                label = m.group(1).strip().rstrip(":").strip()
                out[label] = m.group(2).strip().lstrip(":").strip()
        return out

    def read_case(self):
        case = {}
        for _n, text in self.sections[4]:
            m = re.match(r"^\s*\d\.\s+(.*)$", text)
            if not m:
                continue
            body = m.group(1).replace("**", "")
            for label in CASE:
                if body.lower().startswith(label.lower()) and ":" in body:
                    case[label] = body.split(":", 1)[1].strip()
        return case

    def read_proofs(self):
        proofs, current = [], None
        for _n, text in self.sections[5]:
            m = re.match(r"^###\s+(P\d+)\.\s+(.+)$", text)
            if m:
                current = {"id": m.group(1), "name": m.group(2).strip()}
                proofs.append(current)
                continue
            f = FIELD.match(text)
            if current is not None and f:
                current[f.group(1).strip().rstrip(":").strip()] = f.group(2).strip()
        return proofs

    def read_keep_off(self):
        items = []
        for _n, text in self.sections[7]:
            m = re.match(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*(.*)$", text)
            if not m:
                continue
            rest = m.group(2)
            watch = []
            w = re.search(r"Watch for:\s*(.+)$", rest)
            if w:
                watch = QUOTE.findall(w.group(1).translate(CURLY))
            items.append({"kind": m.group(1).strip().rstrip(":"),
                          "text": re.sub(r"\s*Watch for:.*$", "", rest).strip(), "watch": watch})
        return items

    @property
    def confirmed(self):
        text = self.stamp_fields.get("Confirmed", "")
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", text)
        return m.group(1) if m else None

    def posting_row(self):
        return next((r for r in self.files if len(r) >= 4 and "posting" in r[1].lower()), None)

    def for_resume(self):
        return [p for p in self.proofs if p.get("Use on", "").lower().rstrip(".") in ("resume", "both")]


def intake(pos, posting):
    print(f"POSITIONING: {pos.path.name}")
    usable, reasons = True, []
    built = pos.stamp_fields.get("Built", "not given")
    if pos.confirmed:
        print(f"Format {FORMAT}. Confirmed {pos.confirmed}. Built {built}.")
    else:
        usable = False
        reasons.append("it isn't confirmed yet. Finish it with candidate-positioning first")
        print(f"Format {FORMAT}. Not confirmed. Built {built}.")
    row = pos.posting_row()
    if posting and row:
        now = file_hash(posting, len(row[3]))
        if now == row[3].lower():
            print(f"Posting: {Path(posting).name} is the copy the file was built from.")
        else:
            usable = False
            reasons.append(f"it was built from a different copy of the posting ({row[0]}). Ask the "
                           "candidate once whether to use it anyway or rebuild it first")
            print(f"Posting: {Path(posting).name} isn't the copy the file was built from ({row[0]}).")
    print()
    print("CASE (sets the summary's direction; never copied onto the page)")
    for label in ("What they want", "The story the evidence tells", "What the reader should believe",
                  "Where the candidate stands"):
        note = " (a working note, never on the page)" if label == "Where the candidate stands" else ""
        print(f"  {label}{note}: {pos.case.get(label, 'missing')}")
    print()
    print("PROOFS FOR THE RESUME, best first (the evidence still decides every fact)")
    lead = pos.for_resume()
    for p in lead:
        print(f"  {p['id']} {p['name']} | on the resume being sent: {p.get('On the resume being sent', '?')}"
              f" | {p.get('Source', 'no source')}")
        print(f"     {p.get('Result', '')}")
    if not lead:
        print("  None marked for the resume.")
    print()
    print("REQUIREMENT MAP (settle each one from the evidence, as always)")
    for r in pos.rows:
        if len(r) >= 8:
            print(f"  {r[0]} {r[3]}, {r[6]}, show on {r[7]}: {r[1]} | {r[5]}")
    print()
    print("WORDS TO USE: " + (", ".join(pos.terms) if pos.terms else "none"))
    print()
    print("KEEP OFF THE PAGE")
    for item in pos.keep_off:
        watch = (" Watch for: " + ", ".join(f'"{w}"' for w in item["watch"])) if item["watch"] else ""
        print(f"  {item['kind']}: {item['text']}{watch}")
    print()
    if usable:
        print("RESULT: use it")
        return 0
    print("RESULT: don't use it, because " + "; and ".join(reasons) + ".")
    return 1


def check_resume(pos, resume_path):
    import term_coverage as tc  # late import: only this mode needs the term matcher
    resume = tc.Resume.load(resume_path)
    print(f"POSITIONING CHECK: {Path(resume_path).name} against {pos.path.name}")
    fails = 0
    for item in pos.keep_off:
        for phrase in item["watch"]:
            target = norm(phrase)
            hit = next((ln["text"] for ln in resume.lines if target and target in norm(ln["text"])), None)
            if hit:
                fails += 1
                print(f"FAIL: \"{phrase}\" is on the page, from the keep-off list ({item['kind']}): {hit[:100]}")
    found, missing = [], []
    for term in pos.terms:
        hits, _outside, how = tc.find(tc.normalize(term), resume)
        if hits:
            found.append(f"{term} ({hits}, {how.strip(' ()')})" if how else f"{term} ({hits})")
        else:
            missing.append(term)
    print("Words to use on the page: " + (", ".join(found) if found else "none"))
    if missing:
        print("Words to use not on the page: " + ", ".join(missing) + ". Add one only where the "
              "evidence proves it, inside the line that shows the work.")
    print("RESULT: " + ("FAIL" if fails else "PASS"))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read a positioning file, or check a resume against it.")
    ap.add_argument("positioning", help="the positioning file")
    ap.add_argument("--posting", help="the posting this build uses, to check it's the same copy")
    ap.add_argument("--resume", help="a built resume (.docx, .json, .txt or .md) to check against the file")
    args = ap.parse_args(argv)
    try:
        pos = Positioning(args.positioning)
        if args.resume:
            return check_resume(pos, args.resume)
        return intake(pos, args.posting)
    except Unreadable as exc:
        print(f"The positioning file can't be used, because {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
