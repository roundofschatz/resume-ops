#!/usr/bin/env python3
"""
widow_check.py: flag any block whose last rendered line carries one or two
words alone, and any experience or summary bullet running past two lines.

A widow only exists after the text is laid out, so no check on extracted text
can see one. This reads the rendered PDF and matches its lines back to the
paragraphs in the .docx, which is why it needs both files.

Stdlib only. Uses `pdftotext`, which ships with poppler.

Usage:
    python render_pdf.py resume.docx        # prints the PDF path
    python widow_check.py resume.docx <that PDF path>

Exit codes: 0 clean, 1 findings, 2 could not match, 3 pdftotext missing.

A match failure is not a pass. It means the words in the PDF and the words in
the .docx did not line up, so the check could not run on those blocks.
"""

import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _docx  # noqa: E402

# Word and LibreOffice draw a list bullet as a glyph that is not in the
# document text. It only ever opens the first line of a bullet.
GLYPH = re.compile(r"^[\u2022\u00b7\u25cf\u25aa\u25e6\u2023\u2219\uf0b7]\s*")

WIDOW_MAX_WORDS = 2
# references/writing.md: two lines per bullet is the maximum. Only the
# render can count this.
MAX_LINES = 2
# How far ahead to look for the start of a block, past a stray line.
LOOKAHEAD = 12


def docx_blocks(path):
    """(kind, text, section) for every non-empty paragraph, in document order."""
    return _docx.with_sections(_docx.blocks(path))


def pdf_lines(path):
    # Ask for UTF-8 and read it as UTF-8. The pdftotext that Git for Windows
    # ships is xpdf 4.00, which writes Latin-1 by default: the en dash in a
    # role's dates came back as a soft hyphen, and no role line matched.
    # Poppler and xpdf both take -enc UTF-8.
    try:
        r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
                           capture_output=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print("pdftotext was not found. It comes with poppler "
              "(apt install poppler-utils, brew install poppler).", file=sys.stderr)
        print("The check did not run. This is not a pass.", file=sys.stderr)
        sys.exit(3)
    if r.returncode:
        sys.exit(f"pdftotext failed on {path}: {r.stderr.strip()}")
    return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]


def squash(s):
    """Text with every space removed and look-alike characters made the same,
    so a line break in the PDF and a space in the .docx compare equal."""
    s = unicodedata.normalize("NFKC", s).replace("\u00ad", "")
    return re.sub(r"\s+", "", s)


def match_at(text, lines, i):
    """Try to read the block `text` from lines[i:]. Returns the number of lines
    it spans, or None if the lines do not spell the block.

    Lines are compared with the spaces taken out, so it does not matter how
    the renderer split the words:
      - a hyphenated word broken at its hyphen ("blow-" then "molding") joins
        back to "blow-molding";
      - a minus sign left alone at the end of a line ("-" then "38%") joins
        back to "-38%";
      - a hyphen the renderer added at a break ("mainte-" then "nance") is
        dropped when the .docx has no hyphen there.
    """
    target = squash(text)
    if not target:
        return None
    got = ""
    j = i
    while j < len(lines) and len(got) < len(target):
        piece = squash(GLYPH.sub("", lines[j]) if j == i else lines[j])
        if target.startswith(got + piece):
            got += piece
        elif piece.endswith("-") and target.startswith(got + piece[:-1]):
            got += piece[:-1]
        else:
            return None
        j += 1
    return j - i if got == target else None


def last_line_words(line):
    """Words on a rendered line, counted the same way as in the .docx: split
    on spaces. A lone dash is not a word."""
    return len([w for w in GLYPH.sub("", line).split() if w.strip("-\u2013\u2014")])


def check(blocks, lines):
    """Match every block to its rendered lines.

    blocks: (kind, text, section) as docx_blocks() returns.
    lines:  the rendered lines, in order.
    Returns (widows, longs, unmatched, matched).
    """
    i, widows, longs, unmatched, matched = 0, [], [], [], 0
    for kind, text, section in blocks:
        used = None
        for start in range(i, min(i + LOOKAHEAD, len(lines))):
            used = match_at(text, lines, start)
            if used:
                i = start
                break
        if not used:
            unmatched.append(text)
            continue
        matched += 1
        last = lines[i + used - 1]
        i += used
        n = last_line_words(last)
        if used > 1 and n <= WIDOW_MAX_WORDS:
            widows.append((text, n, last))
        # A skills line runs to whatever the list needs, and the summary is
        # prose. The two-line cap governs bullets only.
        exempt = _docx.is_skills_section(section) or kind != "bullet"
        if used > MAX_LINES and not exempt:
            longs.append((text, used))
    return widows, longs, unmatched, matched


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    blocks, lines = docx_blocks(sys.argv[1]), pdf_lines(sys.argv[2])
    widows, longs, unmatched, matched = check(blocks, lines)

    for blk, n, last in widows:
        print(f"WIDOW ({n} word{'s' if n != 1 else ''}): ...{last.strip()[-60:]}")
    if widows:
        print("\nFix by changing the words until the line count changes. Never with a")
        print("non-breaking space, a manual line break, or a spacing change. Those show")
        print("up in the pasted text or break in a different place in another program.")
    for blk, n in longs:
        print(f"OVER TWO LINES ({n}): {blk[:70]}...")
    if longs:
        print("\nTwo lines is the most a bullet gets. Cut the setup and keep the result.")
    for blk in unmatched:
        print(f"COULD NOT MATCH: \"{blk[:60]}...\"")
    if unmatched:
        print("\nThose blocks were not checked. A page header or footer, a table or a")
        print("text box will do this. All three are layout faults anyway, so run")
        print("parse_check.py on the .docx.")

    print(f"\n{matched} block(s) matched, {len(unmatched)} not matched, "
          f"{len(widows)} widow(s), {len(longs)} bullet(s) over two lines.")
    if unmatched:
        return 2
    return 1 if (widows or longs) else 0


if __name__ == "__main__":
    sys.exit(main())
