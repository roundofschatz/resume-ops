#!/usr/bin/env python3
"""
render_pdf.py: render a .docx to PDF so the page can be looked at.

The text checks cannot see the page. Page count, where each page breaks, a
bullet running past two lines, a header stranded at the foot of a page, a short
page two: only the render shows those.

The PDF is a check file. By default it goes into a new temporary folder, not
next to the resume, so it does not get sent by mistake. Send the .docx.

Looks for LibreOffice on PATH (soffice, libreoffice), then in the usual install
folders on Windows and macOS.

    python render_pdf.py resume.docx                  -> PDF in a temp folder; path printed
    python render_pdf.py resume.docx --out-dir build  -> PDF in build/

The first line printed is the PDF path, so a script can read it.

Exit codes: 0 rendered, 3 nothing could render it (not a pass: the visual
check did not run).

LibreOffice is not Word. Treat the render as a check on page count, spacing and
obvious damage, never as Word's exact page breaks.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

INSTALL_PATHS = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)


def candidates():
    """Every LibreOffice this machine has, once each."""
    seen = []
    for exe in ("soffice", "libreoffice"):
        found = shutil.which(exe)
        if found and found not in seen:
            seen.append(found)
    for p in INSTALL_PATHS:
        if Path(p).is_file() and p not in seen:
            seen.append(p)
    return seen


def main():
    ap = argparse.ArgumentParser(description="Render a .docx to a PDF check file.")
    ap.add_argument("docx")
    ap.add_argument("--out-dir", default=None,
                    help="folder for the PDF (default: a new temporary folder)")
    args = ap.parse_args()

    src = Path(args.docx).resolve()
    if not src.is_file():
        sys.exit(f"Not a file: {src}")
    if args.out_dir:
        out_dir = Path(args.out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="resume-ops-check-"))

    tried = []
    for exe in candidates():
        tried.append(exe)
        cmd = [exe, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(src)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as e:
            print(f"  {exe}: {e}", file=sys.stderr)
            continue
        pdf = out_dir / (src.stem + ".pdf")
        if pdf.is_file():
            print(pdf)
            print("This PDF is a check file for widow_check.py and for looking at the page. "
                  "Do not send it. Send the .docx.")
            print(f"Next: python widow_check.py \"{src}\" \"{pdf}\"")
            return 0
        print(f"  {exe} stopped with code {r.returncode}: "
              f"{(r.stderr or r.stdout).strip()[:200]}", file=sys.stderr)

    print("No PDF was made. Tried: " + (", ".join(tried) or "nothing (LibreOffice not found)"),
          file=sys.stderr)
    print("Install LibreOffice, or export a PDF from Word and pass it to widow_check.py.",
          file=sys.stderr)
    print("The visual check did not run. This is not a pass.", file=sys.stderr)
    if not args.out_dir:
        shutil.rmtree(out_dir, ignore_errors=True)
    return 3


if __name__ == "__main__":
    sys.exit(main())
