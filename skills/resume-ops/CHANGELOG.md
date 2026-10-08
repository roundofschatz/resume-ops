# Changelog

Every change to a rule bumps the version and adds a line here, the same day. A version number covers one state of the rules, never two.

## 2.4.2 (2026-10-08)

The owner's credit, a cleaned history and the first release tags. No rule changed.

**Credit**
- The README's Author section holds the owner's name and a LinkedIn link, without a job title or a city. On October 8 the owner asked for the same credit in plainspeak-writer, job-seeker-ops and resume-ops, and a title and a city go out of date and read like a bio.
- `.claude-plugin/plugin.json`: the author's link goes to the GitHub account, where the code lives, in place of LinkedIn. The README keeps the LinkedIn link.

**History**
- On October 8, at the owner's request, the repository's history was rewritten so that no commit holds the old made-up company name, since it belonged to a real company. 2.4.0's sample positioning file, its posting and `test_positioning.py` now use Switchgrass Freight Co. and the matching stamp hashes from the start, so the rename that 2.4.1 describes no longer shows in 2.4.1's diff. Every file in 2.4.1 is the same as before.
- 2.4.0 and 2.4.1 have new commit hashes: 2.4.0 is f51607b and 2.4.1 is 676503c. 2.1.1, 2.2.0 and 2.3.0 kept theirs. A project that pinned 2.4.0 or 2.4.1 by commit needs the new hash or a tag.
- The rewritten 2.4.0 passes its own tests, apart from the test on a real render that 2.4.1 fixed.

**Tags**
- Each release since 2.1.1 has a tag on the commit that released it, from v2.1.1 to v2.4.2, so another project can pin a version by name. job-seeker-ops pinned resume-ops by commit because there were none.

**Tests**
- The whole suite ran before and after the change (295 tests, 1 skipped), and passed both times.
- Every file this version changes passes plainspeak-writer 1.7's checker with no HARD hits.

## 2.4.1 (2026-10-08)

Two fixes. No rule changed.

**Scripts**
- `widow_check.py` asks `pdftotext` for UTF-8 (`-enc UTF-8`) and reads the output as UTF-8. On Windows, the `pdftotext` on the path can be the xpdf 4.00 build that comes with Git for Windows, and it writes Latin-1 unless told otherwise. It wrote the en dash in each role's dates as a soft hyphen, which the matcher drops, so every title and dates line came back COULD NOT MATCH and went unchecked. Poppler and xpdf both take the flag.
- `requirement_check.py` asks for UTF-8 the same way when it reads a PDF as evidence. It already read the output as UTF-8 and skipped any byte it couldn't read, so with xpdf, dashes and accented letters dropped out of the passages it quoted, with no warning.

**Tests**
- The made-up freight company in `tests/fixtures/positioning/` is now Switchgrass Freight Co., in the positioning file's name and text, the posting and `test_positioning.py`. The old made-up name turned out to belong to a real company. job-seeker-ops, where the sample comes from, made the same change in its 0.3.1. The stamp hashes for the posting and the notes file were worked out again (posting.md 5bc4bf94f8b5, positioning-notes.md 7a4cbb96790b), and they match job-seeker-ops's copies of both files. The resume's hash didn't change.
- Four new tests, each failing on 2.4.0. Two use a stand-in that answers the way xpdf does, so they fail before the fix on any machine. Two run the real `pdftotext` on a small PDF written by hand, so they need no LibreOffice. They fail on 2.4.0 where `pdftotext` is xpdf. The hand-written PDF helper moved to `tests/fixtures.py`, and its font now uses WinAnsiEncoding, so a line can hold an en dash or an accented letter.
- The whole suite ran before the change (291 tests, 1 skipped, 1 failure: `test_widow_check_on_a_real_render`, on Windows with xpdf's `pdftotext`) and after it (295 tests, 1 skipped, no failures).
- Every file this version changes passes plainspeak-writer 1.7's checker with no HARD hits, apart from code in the Python files: minus signs, command-line flags and the en dash in a test resume's dates. 2.4.0 had each of those hits, and none sits on a line this version changed.

## 2.4.0 (2026-10-05)

job-seeker-ops 0.2.0 adds candidate-positioning, which writes one positioning file per posting: the case for the candidate, a requirement map with the evidence behind each row, the proofs ranked for the posting, the words the candidate can claim, and what stays off the page. This version reads that file when it's there. Without it, nothing changes: no existing script reads the file, the Level Set stays at six lines, and the brief and the delivery are the same as in 2.3.0.

**Procedure**
- Intake looks for a positioning file for the posting beside the evidence and reads it with the new `positioning_check.py`. A file that isn't confirmed, or that was built from another copy of the posting, isn't used, and the brief says why.
- The file sets direction and order, and it isn't evidence. Its proof bank and requirement map show which evidence leads, its case lines set the summary's direction, and its words to use feed the term check. Every fact still comes from the evidence and the rulings file, and a ruling beats the file. The rules sit in `tailoring.md`, A positioning file, with a pointer from `intake.md`.
- With a file in use, the Level Set gets a seventh line and the brief gets a POSITIONING line. When job-seeker-ops's submission-review skill is also available, the delivery ends with one line offering a submission review.

**Scripts**
- New `positioning_check.py`. At intake it says whether the file can be used, checks that the posting is the copy the file was built from, and prints the case lines, the proofs marked for the resume, the requirement map, the words to use and the keep-off list. With `--resume`, it fails when a phrase from the keep-off list is on the built resume, and lists which words to use the page holds, matched with `term_coverage.py`'s own matcher. No existing script changed.

**Tests**
- New `tests/test_positioning.py`, with a sample positioning file and its posting and resume in `tests/fixtures/positioning/`, saved as Markdown since the repository ignores .txt files. Each test of the new behavior fails on 2.3.0. Two more guard the rest: the Level Set block stays at six lines, and no other script reads a positioning file.
- The whole suite ran before the change (279 tests, 3 skipped) and after it (291 tests, 3 skipped), and every test passed both times.
- Every file this version adds or changes passes plainspeak-writer 1.4.1's checker, and the 1.5 build's, with no HARD hits, apart from two date ranges in the sample resume, such as "Aug 2021 - Present". The sample is test writer B's resume from job-seeker-ops, kept byte for byte. The owner ruled on October 5 that a range outside prose may keep its dash, and the checker doesn't follow that ruling yet.

**Left for later**
- A check that one bullet doesn't repeat another word for word. On October 5 the owner ruled that no sentence repeats word for word within one piece, and `draft_review.py` only asks for a second look when the summary copies a bullet. Adding the check now would change a build that has no positioning file, so it waits for the next version.
- Whether resume-ops runs plainspeak-writer's checker in place of its own voice checks. Its own checks stay as they are for now.

## 2.3.0 (2026-09-30)

A live build on September 30 showed three faults. `detect_ats.py` couldn't name the system behind a job link on rippling-ats.com, and its note said nothing in the link named a system, though the host said "rippling". A bullet counted seven decisions and never said what they were about. Another said "own" where the sentence meant the same thing without it.

**Hosts**
- rippling-ats.com runs on HiringThing, which sells its system under partners' names; its partners sell this one as Rippling ATS. All six boards checked there say "Powered by HiringThing" (L06). `detect_ats.py` now names HiringThing, with HiringThing's own form and AI facts, on rippling-ats.com, hiringthing.com, applicant-tracking.com and prismhr-hire.com. Rippling's facts stay with Rippling Recruiting on ats.rippling.com. Had rippling-ats.com been added as Rippling, the check would have printed facts for the wrong product.
- A check of all 26 host rules against the links each vendor uses today found more: Eightfold's EU and government domains, NEOGOV's SchoolJobs site, and SAP's own job site, which now sends applicants to SmartRecruiters in place of SuccessFactors.
- A host that holds a vendor's name but matches no rule now says so and points to the page footer. It no longer says nothing in the link names the system, and it doesn't print that vendor's facts: this case shows the name can belong to someone else's product.
- `term_coverage.py` reads vendor names from the same list, as whole words inside a host word. It now finds the employer's name on links to ats.rippling.com, jobs.eu.lever.co and careers-<company>.icims.com. Before, it could list the employer's own name as a missing term.
- `readers.md` adds Rippling Recruiting and HiringThing: what each form fills from a resume, as far as the vendors say, and a row for each among the AI graders.

**Writing rules**
- Name what you count, rewritten. A count of abstract things (decisions, directives, priorities, themes and the like) names its set: what it was about or for. It doesn't need every item. "Key" and "strategic" name nothing. If the evidence can't name the set, the count comes off. A count of concrete things (stores, interviews, employees) is scope. The same rule covers a label like "key insights".
- The builder takes the name from the evidence while settling each claim (SKILL.md, step 4).
- `draft_review.py` fails a count that names nothing and a label built on a generic word, and flags a count for review when the words after it may only say whose set it was. Across 213 bullets from one candidate's past resumes and the 74 clean test sentences, it flagged no line wrongly.
- Words the sentence already means: a new section in `writing.md`. "Each and every", "was able to", "end result" and six more fail. "Own" after a possessive, "personally", "successfully", "actual" and "new" after a build verb are flagged for review, because each one sometimes changes the meaning ("its own P&L").

**Sources**
- New rows S102 to S111: HiringThing's white-label, partner, parsing and AI pages, Rippling's resume, screening and AI settings pages, and NEOGOV's SchoolJobs launch. L06 records the live host check. S37 now also backs Rippling's row among the AI graders.

**Tests**
- 19 new tests, each failing on 2.2.0: the new hosts, the note for an unmatched host that holds a vendor's name, the employer name on the three link shapes, counts and labels that name nothing, and redundant words.

## 2.2.0 (2026-09-28)

The procedure now matches what the skill is for: evidence in, a resume for one posting out. From the first package on September 11 through 2.1.1, SKILL.md made a base resume a prerequisite ("If the candidate has no base resume, build it first") and built every tailored resume from it. The red teams checked whether the rules were true. None checked the procedure against the intent.

**Procedure**
- The tailored resume is the main procedure, built from evidence: Level Set; intake (the contact block, then whatever the candidate gives, one file or many, in any format); read the posting; map the evidence to it; write, build, check and deliver.
- The base resume is an optional mode for job boards and referrals when there's no posting. Its 8-to-12-postings method stays. It's never a prerequisite.
- Every next posting starts from the evidence. A resume built earlier can be one more input, never the starting point.
- The facts file is optional, offered after the first build. When the evidence is already a career record the candidate keeps, no second copy is made.
- One record, every resume: titles, companies, cities and dates come from the evidence and read the same on every resume built from it. `profile_check.py` stays as the check.
- Level Set: Mode reads Tailored resume, Base resume or Review only, and an Evidence line names each file loaded in place of the facts-file line.
- Hard rule 7: a file under the read-whole line (about 2,000 lines or 150 KB) is read start to end; a file over it is searched. No qualification is dropped because a file was too big to read.

**Scripts**
- `requirement_check.py --evidence` reads evidence as well as a resume: Markdown, text, DOCX, and PDF through `pdftotext`. It splits each file on its headings, prints a map of them, and returns the best passages for each qualification with the file, heading and line. For a list qualification it looks for passages that cover different parts of the list.
- `build_resume.py` no longer writes an Application element in `docProps/app.xml`. It named the tool, and anyone who opened File, Properties in Word could see it. Every part the file had stays, and no part names the tool.

**Docs**
- The SKILL.md description, the Level Set, both procedures, `intake.md` (evidence in any format; small and large evidence), `tailoring.md` (what changes from one posting to the next, rewritten around evidence), the facts template and both READMEs.

**Tests**
- New: evidence search on Markdown, text, DOCX and PDF; no trace of the tool in any part of a built DOCX; SKILL.md makes nothing a prerequisite for a tailored resume.

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
- New section in `readers.md`, The record check: background checks verify titles and dates against the employer's record; Lever flags work-history consistency; LinkedIn lets colleagues vouch for work history. A reorder of the formal title's own words is low risk; an added word is medium risk unless the formal title goes into the forms. The post-upload review and the brief now show the formal title.
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
- Uses the posting's title language and one proof that answers the posting's top requirement; at most one claim repeats a role bullet.
- One belief sentence in the candidate's own words, without "I".

**Skills**
- Required tools go inside the bullet where they were used. The Skills section is optional and one line. Per-role "Skills:" lines are not used.

**Roles and layout**
- Company-first role layout, set by a live Workday test on 2026-09-28: 8 of 8 titles, companies, cities and dates right, against 2 of 8 fully right for the 1.6 layout.
- Titles have no comma or parenthesis: Workday keeps only the text before either. A title with a qualifier is written descriptor first ("Supply Chain Senior Analyst").
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

No changelog was kept. The label 1.6 covered two opposite positions on the skills budget, and 1.5 covered two on the separate Workday file. That's why this file exists.
