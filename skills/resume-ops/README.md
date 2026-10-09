# Resume Ops

A Claude Skill that builds a US resume for one job posting from whatever the candidate has, for the four readers who use it: the application form that parses it, the AI grader that checks it against the posting, the recruiter who decides in seconds whether to keep reading, and the hiring manager who wants proof.

Version 2.4.4. See `CHANGELOG.md`.

## What it does

- Takes whatever the candidate already has as evidence (a resume of any age, a cover letter, a LinkedIn profile, website text, a career record, notes, or a conversation), one file or many, in any format. One upload is enough to start, and nothing has to be built first.
- Builds a resume for one posting from that evidence by checking every required qualification: proven in the role where the work happened, written in where the evidence shows it, or named as a gap. Never written around.
- Searches large evidence instead of reading it whole: for each qualification, the best passages with the file, heading and line.
- Builds a base resume for a title family, from a map of what live postings require, when the candidate wants one for job boards. Optional.
- Writes a complete Word DOCX and a plain-text copy from one JSON source, in a role layout that filled every title, company, city and date correctly in a live Workday test.
- Checks the draft for general AI-writing tells and for the rules it states, with scripts rather than judgment wherever a script can do it.
- Tells the candidate what to check in the application form after upload, because autofill makes mistakes the candidate has to fix before submitting.
- Compares the resume's titles, companies and dates with the candidate's LinkedIn jobs file, so the two tell the same story before a background check compares titles and dates with the employer's record.
- Reads a positioning file from job-seeker-ops's candidate-positioning skill when one sits beside the evidence, so the summary aims at the confirmed case and the strongest proof for the posting leads. Without one, it builds exactly as before.

It isn't a career coach, a cover-letter writer or an application tracker. One job: the resume.

## Scope

US resumes for US private-sector postings. It says so and stops for non-US postings, federal, state and local government postings, and academic CVs. Those formats have their own rules.

It works for any field. The examples cover nursing, trades, logistics, finance and teaching as well as office work.

## Install

The easiest route is the plugin, which updates itself. In the Claude app, open Customize, then Plugins, choose Add marketplace and enter `roundofschatz/job-seeker-ops`, then install resume-ops. In Claude Code:

```
/plugin marketplace add roundofschatz/job-seeker-ops
/plugin install resume-ops@roundofschatz
```

That marketplace lives in job-seeker-ops's repository and lists job-seeker-ops too, which includes a copy of this skill. Install one or the other, not both.

To install the skill on its own instead, copy this folder into `~/.claude/skills/` for Claude Code, or zip it (the zip must contain the folder itself) and upload it under Customize, Skills in the Claude app.

Then give it a posting link and whatever you have, and say what you want: *build me a resume for this posting*, *will this parse*, *why am I not getting replies*.

## Layout

```
SKILL.md                 the four readers, hard rules, the tailored and base procedures, checks, delivery
CHANGELOG.md
references/              loaded when a step needs them
  readers.md             what each system's form and AI grader do; the record check;
                         knockout questions; the post-upload review
  sources.md             every source the skill cites, by ID, with date, grade, URL, quote
  document.md            sections, role layout, titles, education, skills line, length, format
  writing.md             bullets, numbers, the summary, AI-writing tells, words the
                         sentence already means
  tailoring.md           reading a posting, mapping the evidence, the requirement check,
                         the base resume's map
  intake.md              the contact block, evidence in any format, small and large
                         evidence, contradictions, choosing a target
scripts/                 Python 3.8+, standard library only
templates/               the candidate's rulings file and the optional facts file
tests/                   python tests/run_tests.py
```

## Scripts

| Script | What it does |
|---|---|
| `detect_ats.py` | Names the system behind a posting link (host, path and query patterns), what its form fills, and what AI grading it sells |
| `requirement_check.py` | Turns a posting's required and preferred qualifications into a checklist. With `--evidence` (Markdown, text, DOCX, or PDF through `pdftotext`), the best passages for each one with the file, heading and line; with a resume, the proof lines on the page |
| `term_coverage.py` | Posting terms by tier against a resume; `--composite` across many postings for a base resume |
| `corpus_triage.py` | Maps a pile of career material: graded claims, roles and employers, contradictions, repeats, possible targets |
| `draft_review.py` | Writing rules and general AI-writing tells, on the JSON source or a DOCX |
| `build_resume.py` | Writes the DOCX and plain-text copy from one JSON source; refuses structural faults |
| `parse_check.py` | Structure check of a DOCX. Not a prediction of what any form will fill in |
| `render_pdf.py` | Renders a check PDF into a temp folder so the page can be looked at. Never a deliverable |
| `widow_check.py` | Lines ending on one or two words, and bullets over two lines, read off the render |
| `profile_check.py` | The resume's titles, companies and dates against the candidate's LinkedIn jobs file (Positions.csv from LinkedIn's data download) |
| `positioning_check.py` | Reads a positioning file from job-seeker-ops's candidate-positioning skill at intake; with `--resume`, checks a built resume against the file's keep-off list and its words to use |
| `_docx.py` | The shared DOCX reader. Not run directly |

Some steps need outside programs, and each says so rather than passing quietly:

| Step | Needs | Install |
|---|---|---|
| `render_pdf.py` | LibreOffice | `apt install libreoffice` / `brew install --cask libreoffice` / libreoffice.org |
| `widow_check.py`, and PDF evidence in `requirement_check.py` | `pdftotext` (poppler) | `apt install poppler-utils` / `brew install poppler` |

## Where the rules come from

Every claim about a system, a reader, a study or a law cites a source ID, like [S16], at the point of use. `references/sources.md` holds each source once: its date, grade (first-hand, study, survey, guide, opinion, secondary or live test), URL, what it supports, a short quote, and the files that use it. `tests/test_sources.py` fails if a cited ID has no row, a row is cited nowhere, or a row's "Used in" list is out of date. Where no source exists, the file says the rule is the skill's own judgment.

The role layout comes from live tests: real resumes uploaded to live Workday applications in several layouts, with every autofilled field read back, plus Greenhouse, Lever and Eightfold forms (September 2026). The section outline, the file format and the rest of the standard come from red-team reviews against vendor docs, parser documentation, studies, surveys and university guides, most from 2025 and 2026.

Numbers in this space are often quoted past what they prove. The "six-second scan" traces to one 2012 vendor study of 30 recruiters [S52]. No source says what share of employers turn on AI grading. Where the skill uses a working threshold (summary length, bullets per role), it says it's a guide.

## Not legal or career advice

The skill writes resumes from what the candidate tells it. It doesn't give legal, immigration or employment advice, and it can't predict how a particular employer's system is configured.

## Tests

```
python tests/run_tests.py
```

Every test for a fix fails on the version before the fix. `tests/fixtures/tells.json` holds the AI-writing tell sentences and clean exact-term sentences the draft review is measured against.

## Privacy

The scripts write resumes into whatever folder you point them at. `.gitignore` keeps DOCX, PDF, TXT and page images out of a repo so a real resume isn't committed by accident.

## License

MIT. See `LICENSE`.
