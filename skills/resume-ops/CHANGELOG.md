# Changelog

Every change to a rule bumps the version and adds a line here, the same day. A version number covers one state of the rules, never two.

## 2.1.1 (2026-09-28)

Published on GitHub as a Claude plugin. No rule changed.

- Packaged as a plugin with a marketplace file, so Claude can install it from the GitHub repo and pick up each new version without a manual upload. `.claude-plugin/plugin.json` holds the version, and the new `tests/test_version.py` fails when it, SKILL.md and this file disagree.
- The live-test rows name the form system, not the employer.
- Install steps match Claude's current menus (Customize, Skills and Customize, Plugins).

## 2.1.0 (2026-09-28)

After a second red team: three research passes on first-hand sources, a check of every cited source, and live tests on Greenhouse and Lever with a made-up resume.

**Sources**
- New `references/sources.md`: every source the skill cites, by ID, with its date, grade, URL, what it supports, a quote, and where it is used (101 outside sources, 5 live tests). Every outside fact in SKILL.md, the references and `detect_ats.py` cites an ID. New `tests/test_sources.py` fails on a missing, unused or mislisted ID.
- Corrected against the sources: the Princeton grader figures (98 to 99% with three differing qualifications, 82 to 93% with one); Greenhouse Talent Matching (Real Talent add-on, "Needs manual review" on opt-out, skills taken from anywhere in the resume); HiredScore sold as its own product; ADP's 2026 FAQ; LinkedIn Hiring Assistant grading employer-system applicants; SmartRecruiters and Paradox added; the hidden-text study measures prevalence, not detection; the California, Colorado and Illinois rules in full, plus California's FEHA rules; Workday's field list cited to the 2026 manual; Yale, Kellogg and Insight Global citations that didn't hold, dropped or narrowed; the ResumeGo gap test stated as run.

**File**
- `build_resume.py` writes every part Word writes (document properties, settings, web settings, font table, theme) and Word's standard styles. Lever's parser (Textkernel) refused the six-part file 2.0.1 wrote and parsed the same text saved as a complete Word file.
- `parse_check.py` warns when a DOCX lacks those parts.

**Layout and outline**
- The job title is bold as well as the company line (Ladders 2018 eye-tracking). `--plain-title` keeps the look the Workday tests used.
- The section outline is confirmed on the evidence and stated with it: Summary, Experience, Education, Certifications, Skills. Skills goes from optional to included whenever there is something concrete, one line at the end; the proof stays in the bullets. No Accomplishments or Highlights section.
- Company names keep a legal suffix without a comma ("Acme Inc."), which Greenhouse and RChilli say helps recognition.

**Titles and the record**
- New section in `readers.md`, The record check: background checks verify titles and dates against the employer's record; Lever flags work-history consistency; LinkedIn lets colleagues vouch for work history. A reorder of the formal title's own words is low risk; an added word is medium risk unless the formal title goes into the forms. The post-upload review and the brief now carry the formal title.
- New `profile_check.py`: compares the resume's titles, companies and dates with the candidate's LinkedIn jobs file (Positions.csv from LinkedIn's data download). No browser needed.

**Diagnosis**
- "No replies after twenty sends" becomes about fifty tailored sends: at recorded interview rates of 3 to 6%, zero in twenty happens by chance a third to half the time.

## 2.0.1 (2026-09-28)

Five edits after the v2.0 after test and the candidate's review.

- Summary: the one-repeat cap is retired. The summary says in simpler form what the bullets below prove, every claim has a job behind it, and nothing is copied from a bullet word for word (`writing.md`). `draft_review.py` no longer fails repeats; it flags a word-for-word copy for a second look (REVIEW).
- Years: the summary's years count the whole career, this year minus the year the career started; a posting's "N years in X" still counts only the jobs that did X (`writing.md`, `tailoring.md`).
- Career totals: a total the candidate confirmed that spans several jobs may stay in the summary with no single job behind it. Listed under `career_totals` in the JSON source, which `draft_review.py` reads (`writing.md`, `document.md`, `readers.md`, facts template).
- Skills: "Workday never fills skills" is gone. Each Workday site handles Skills its own way (none filled, suggested from the file, type-and-pick); check the Skills box every time and remove anything wrong (SKILL.md, `readers.md`, `document.md`, `detect_ats.py`).
- Blank company tip in the post-upload review: if a company comes back blank, look at the last bullet of the job above it and move it up or reword its end. A tip from one case, not a rule (`readers.md`).

## 2.0 (2026-09-28)

Rebuilt after a red-team review of 1.6: a before run on eight live postings, four research passes on 2025 to 2026 sources, and a live Workday upload test.

**Readers**
- Four readers instead of three: the application form, the AI grader, the recruiter, the hiring manager.
- Retired the claim that there is usually no machine score. Most major systems now sell AI grading; Workday HiredScore's A to D rule needs every required qualification met for an A or B.
- Removed the unsourced claim about what a resume's Skills header does in Workday, and every rule that rested on it (skills-cluster labels and delimiters, the five-header rationale).
- Removed other claims no primary source supports: a second, longer file for Workday; a Workday skills count; the upload filling the Skills box; parser accuracy figures; knockout questions always running first; a federal grade rule; one employer's upload-page instruction stated as Workday's own.

**Tailoring**
- The work order is a requirement check (new `requirement_check.py`): every required qualification is proven in a role line, written into the role where the work happened, or named as a gap. Replaces "the missing Tier 1 terms are the work order".

**Summary**
- Prose only, three to four lines, about 50 to 70 words. No career-level bullets, no keyword strip, implied first person, counts name what they count.
- Carries the posting's title language and one proof that answers the posting's top requirement; at most one claim repeats a role bullet.
- One belief sentence in the candidate's own words, without "I".

**Skills**
- Required tools go inside the bullet where they were used. The Skills section is optional and one line. Per-role "Skills:" lines are not used.

**Roles and layout**
- Company-first role layout, set by a live Workday test on 2026-09-28: 8 of 8 titles, companies, cities and dates right, against 2 of 8 fully right for the 1.6 layout.
- Titles carry no comma or parenthesis: Workday keeps only the text before either. A title with a qualifier is written descriptor first ("Supply Chain Senior Analyst").
- Every role gets a city and state. Every role in the last 15 years gets at least one bullet. Older roles go in one earlier-career line.
- Never three pages for a US private-sector resume.

**Process**
- The contact block is the first intake question.
- The post-upload form review is a required step, with one checklist for form-filling systems and a note for systems with no form.
- Rulings land the same day: general rules in the skill with a version bump, candidate rulings in the candidate's rulings file. The rulings template now holds build preferences as well as facts.

**References**
- Nine reference files cut to five, one rule in one place: `readers.md`, `document.md`, `writing.md`, `tailoring.md`, `intake.md`. Every source dated at the point of use. All examples are neutral and from mixed fields.

**Scripts**
- `detect_ats.py`: host, path and query-parameter patterns (gh_jid, ashby_jid, iis, Jibe, Eightfold, Rippling, Paycom, BrassRing, NEOGOV and more); names 30 of the 39 test links; reports form behavior and AI grading with doc dates; stale Workday note removed.
- `term_coverage.py`: finds "What you bring", "Qualifications" and other headings; job title forced into Tier 1; stable term list between runs; no tier dropped by the top-N cut; fixed false matches ("master" in "Master Plan", "10+", the employer's name); `--composite` for base resumes.
- `draft_review.py`: all 24 general AI-writing tell classes; exact industry terms pass ("utilization", "statistically significant", "substantial completion"); summary rules; first-person check; skills evidence from role bullets only, whole-word matching; tell fixture in `tests/fixtures/tells.json`.
- `build_resume.py`: v2 source format with structured `role` blocks; company-first layout; refuses comma titles, missing cities, empty recent roles, summary bullets, a second Skills line; tighter default spacing that holds two pages.
- `parse_check.py`: reports a structure check, not a Workday prediction; counts date formats only on date ranges; images fail.
- `widow_check.py`: matches lines that break at a hyphen or minus sign.
- `render_pdf.py`: writes the check PDF to a temp folder; no hard-coded container path.
- `corpus_triage.py`: finds roles and employers in two-line, one-line and heading formats; no more "one employer only" on every target; no invented bullet-count figure.
- Tests split per script; `python tests/run_tests.py` runs them all.

## 1.6 and earlier

No changelog was kept. The label 1.6 covered two opposite positions on the skills budget, and 1.5 covered two on the separate Workday file. That is why this file exists.
