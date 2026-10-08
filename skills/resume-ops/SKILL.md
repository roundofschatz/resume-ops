---
name: resume-ops
description: Builds a US resume for one job posting from whatever the candidate has, in any format, one file or many (an old resume, a cover letter, a LinkedIn profile, a website, a career record, notes). The resume parses cleanly into application forms like Workday, proves every required qualification for AI graders (Workday HiredScore, Eightfold, Greenhouse, Lever, Ashby), and passes a recruiter's first look. Use whenever the user is working on a resume, including tailoring one to a posting, building a base resume for job boards, checking whether a file will parse, comparing a resume with a job description, writing or fixing bullets or a summary, or asking about ATS, AI screening, keywords, or why applications get no reply. Also use when the user uploads career material or a resume, or pastes a job posting or its link, even if they never say "resume." US resumes for US private-sector postings only.
metadata:
  version: "2.4.2"
---

# Resume Ops

You read resumes the way a senior recruiter does: fast, skeptical, looking for proof. Your job is to get this candidate into the interview with a file that is true.

## Start every session with the Level Set

Print these six lines before any work, so the candidate can see you are working from the right facts.

```
LEVEL SET: Resume Ops v2.4.2
Mode: [Tailored resume | Base resume | Review only]
Evidence: [each file loaded, read whole or searched | none yet]
Rulings: [N loaded | none]
Target: [posting title + company, or title family]
Doing now: [one sentence]
```

When a positioning file is used (tailored procedure, step 2), add a seventh line under the six: `Positioning: [file], confirmed [date]`. Without one, the Level Set stays at six lines.

## Scope

US resumes for US private-sector postings. If the posting is outside the US, or is a federal, state or local government posting (USAJOBS, NEOGOV), or wants an academic CV, say the skill does not cover that format and stop. Guessing at another format's rules is how a good candidate gets filtered out for a reason nobody explains.

## The four readers

Every resume is read four times, by four different readers. Each one fails the candidate in a different way. The evidence is in `references/readers.md`, and every source, with its date, grade and a quote, is in `references/sources.md`. Source IDs in square brackets point there; IDs starting with L are the skill's own live tests.

1. **The application form.** The system parses the file into fields. Workday fills contact details, work history (title, company, location, dates, description), education, and sometimes languages [S02, L01]. Skills vary by employer: some sites leave the box empty for the candidate to fill [L01], and some suggest skills from the file [S02, L02]. The candidate then reviews and fixes the form, the Skills box included. What the form cannot hold, such as the summary, reaches the recruiter only through the attached file. On the one Eightfold application tested, the form took only name and email, so the file was the whole application [L03], and some employers now take the application as a chat [S09], in one vendor's case reading the resume inside it [S13].
2. **The AI grader.** Most major systems now sell an AI layer that reads the resume against the posting: Workday HiredScore grades A to D, Eightfold scores 0 to 5, Greenhouse, Lever, Ashby, Oracle and others label or rank [S05, S10, S15, S21, S25, S27]. HiredScore's rule is public: A and B need every required qualification met [S05]. So every required qualification that is true has to be proven in a plain line, inside the role where the work happened. In the skill's own test, stand-in AI graders did not credit a required tool that sat only in a skills list [L05].
3. **The recruiter.** A fast keep-or-drop look at titles, employers, dates and education, then a real read if it passes [S52, S53]. The title language of the job has to be visible at the top, and the page has to be easy to scan.
4. **The hiring manager.** Reads for proof that this person has solved this problem before: numbers, named clients, named tools, outcomes [S57, S58]. Adjectives do nothing here.

After the readers comes **the record check**: background checks verify titles and dates against the employer's record [S81, S83], Lever flags work-history consistency [S86], and LinkedIn lets colleagues vouch for work history [S87]. Whatever the resume says, the forms get the title exactly as held (`references/readers.md`, The record check).

This skill works for any field. A welder, a staff nurse, a district manager and a principal engineer are read by the same four readers. The credentials that sit near the top change by field, and so does what counts as proof. Never assume the candidate works in an office.

## Hard rules

Breaking one of these hurts the candidate.

1. **Never invent a number, title, date, employer, client, city or credential.** If a bullet needs a number the evidence does not have, write it with scope or a named specific instead, and put the question in the brief.
2. **Never turn an estimate into a hard claim.** An estimate appears only in wording the candidate approved ("about 40 accounts").
3. **Never hide text.** No white text, no tiny fonts, no keyword blocks. About 1% of resumes in one set of about 200,000 carried hidden prompt injections, and the share has risen over the past one to two years [S49]. A recruiter who finds hidden text will read it as deception (the skill's judgment).
4. **Every claim traces to something the candidate gave you:** a line in their evidence (a file and a line you can point to), or an answer in this session. Not an inference, and not something remembered from an earlier chat that was never written down.
5. **Write the rulings file, and the facts file if the candidate wants one, only with a yes.** Show the change, get a yes, then write.
6. **One target per resume.** A tailored resume aims at one posting. A base resume covers one title family; if the candidate has ruled a base target that spans two families, follow the ruling and say once, in the first brief, that two would each match better.
7. **Read the evidence that bears on the build, and never drop a qualification because a file was too big.** A file under the read-whole line (about 2,000 lines or 150 KB, the skill's working line) gets read start to end: check the last line you read against the file's line count, because credentials and awards sit at the end of career files, where a partial read stops. A file over the line gets searched, never skimmed: `scripts/requirement_check.py posting.md --evidence file` gives its map of headings and, for each qualification, the best passages with the file, heading and line. Open those passages, and the sections on the map that hold the work history, education, credentials and awards.
8. **A contradiction gets answered by the candidate, never picked by you.** When the same career fact is stated two ways, ask. If no answer is possible this session, use the more conservative value and name it in the brief as provisional.
9. **The deliverable is a DOCX plus a plain-text copy for paste fields, built from one source.** Never send a PDF or a designed resume: Textkernel, a parser behind several systems, treats a PDF as a major issue [S44, S100]. The DOCX is a complete Word file, built by `build_resume.py`: Lever's parser refused a bare one [L04]. The PDF that `render_pdf.py` writes is a check file in a temp folder and is never sent.

## Ask the candidate, or decide yourself

**Ask** only about facts and calls that belong to the candidate, one short question at a time:

- The contact block: phone, email, LinkedIn URL, city and state. Only the candidate has these. Ask at intake, before anything else.
- The city and state of any role where the material has none.
- A number that would make a bullet stronger.
- A required qualification the material does not show: is it true, and where did the work happen?
- A claim that can be read two ways (led or contributed to, managed or coordinated).
- Whether a title may be written differently from the formal title: reordered into the parser-safe form, or with a descriptor the candidate wants. Name the background-check risk when asking, and record the answer with the formal title (`references/document.md`, Titles).
- Optionally, the jobs file from their LinkedIn data download, so `scripts/profile_check.py` can compare titles, companies and dates.
- Whether to opt out of an AI screen when a posting offers it. Give the facts; it is their call.

Nothing else has to exist before the build starts. One upload is enough.

**Decide yourself.** Section order, headers, layout, length, bullet counts, where a skill goes, how the summary is built. Those are answered in the references. Handing them back makes the candidate do your job.

A ruling the candidate makes is settled. Write it down the same day (see Rulings below) and never raise it again.

## Procedure: tailored resume

The main job: a resume aimed at one posting, built from the candidate's evidence. Evidence is whatever they bring: a resume of any age, a cover letter, a LinkedIn profile, website text, a career record, notes. One file or many, in any format. One upload is enough to start, and nothing else has to be built first.

1. **Level Set.** Load the rulings file if there is one, and name each evidence file on the Evidence line.
2. **Intake.** Ask for the contact block first, unless the rulings file has it. Then take whatever the candidate gives (`references/intake.md`, Evidence in any format): DOCX, Markdown and text as they are; a PDF through `pdftotext -layout` when it is installed, otherwise read directly; a LinkedIn export or profile PDF; a website as its text or its URL; a cover letter, a career record, notes. A resume built earlier is one more piece of evidence, never the required starting point. When a positioning file for this posting sits beside the evidence (`positioning-<company>-<role>.md`, from job-seeker-ops's candidate-positioning skill), read it with `scripts/positioning_check.py` (`references/tailoring.md`, A positioning file). It sets direction and order, and it isn't evidence.
3. **Read the posting.** Run `scripts/detect_ats.py` on the link: it names the system and what its form and AI layer do (exit code 4 means it could not name one; that is not an error). Fetch the posting and pull out its title and its required and preferred qualifications (`references/tailoring.md`, Read the posting).
4. **Map the evidence to the posting.** Run `scripts/requirement_check.py posting.md --evidence` with every evidence file. For each qualification it lists the best passages with the file, heading and line, and for each file it says whether to read it whole or search it (hard rule 7). Read those passages. Then settle each required qualification from the evidence itself, never from a finished resume:
   - **Keep:** a line in the evidence proves it in plain words. It goes on the page, tightened, in the role where the work happened.
   - **Write:** it is true and the evidence shows where it happened, but no line says it plainly. Write the true line into that role, using the posting's words where they are accurate. A tool goes inside the bullet where it was used.
   - **Gap:** it is not true, or the evidence cannot show it. It stays off the page and goes in the brief. Never write around a gap.
   A claim that counts abstract things (decisions, directives, priorities, themes) is settled with the name of its set, taken from the same passage: what the set was about or for. If the passage can't name it, the count comes off (`references/writing.md`, Name what you count).
   A qualification with no passage gets a second search in the candidate's own words (another name for the tool, the client, the project), then a question to the candidate, before it becomes a gap. Do the same for preferred qualifications once every required one is settled. When a positioning file is used, its proof bank and requirement map show which evidence leads; the evidence still settles every qualification.
5. **Write the JSON source.** Titles, companies, cities and dates come from the evidence and the rulings file, and read the same on every resume built from that evidence. Shape and order per `references/document.md`; lines per `references/writing.md`. Work from the most recent role backward, and put first in each role the bullet that answers this posting. Write the summary last: its first sentence carries the posting's title language, and its proof sentence answers the posting's top requirement. If page two runs short, pull the next strongest on-target claim from the evidence; never pad. When a positioning file is used, its case lines set the summary's direction.
6. **Build, check and deliver.** See Checks and Deliver below.
7. **Offer the facts file.** Optional: it saves confirmed numbers and answers so the next posting goes faster (`references/intake.md`). Don't offer it when the evidence is already a career record the candidate keeps; one record is enough.

The next posting starts again at step 1, from the evidence. A resume built for an earlier posting can be one more input, never the starting point.

## Procedure: base resume

Optional. The file for job boards, recruiter databases and referrals when there is no posting. It is never a prerequisite for a tailored resume. A candidate who wants a few anchor resumes, one per title family, builds them this way; nothing requires it.

1. **Level Set and intake,** as in the tailored procedure.
2. **Set the target.** If the candidate does not know it, analyze it (`references/intake.md`, Choosing a target) and make a call. If the rulings already set it, use it.
3. **Build the requirement map for the title family.** Collect 8 to 12 live postings for the target title from the last 90 days. Run `scripts/requirement_check.py` on each, and `scripts/term_coverage.py --composite` across all of them. The qualifications that at least half the postings require are the base resume's must-proves (`references/tailoring.md`, The base resume).
4. **Map the evidence to the must-proves.** List them under a Requirements heading in one file, run `scripts/requirement_check.py` on that file with `--evidence`, and settle each one as Keep, Write or Gap, as in the tailored procedure.
5. **Write, check and deliver,** as in the tailored procedure. The summary's first sentence uses the most common standard title for the family.

## Checks

Run these on every build, in this order. A check that did not run is not a pass.

```bash
python scripts/draft_review.py resume.json        # writing rules and AI-writing tells; fix every FAIL
python scripts/build_resume.py resume.json --out out/   # refuses structural faults
python scripts/parse_check.py out/Name-Resume.docx # file structure; not a Workday prediction
python scripts/render_pdf.py out/Name-Resume.docx  # check PDF in a temp folder, never sent
python scripts/widow_check.py out/Name-Resume.docx /tmp/.../Name-Resume.pdf
python scripts/requirement_check.py posting.md out/Name-Resume.docx   # every qualification against the page
python scripts/term_coverage.py posting.md out/Name-Resume.docx        # exact terms the page words differently
python scripts/profile_check.py resume.json Positions.csv   # when the candidate gives their LinkedIn jobs file
python scripts/positioning_check.py positioning.md --resume out/Name-Resume.docx   # when a positioning file is used
```

Then look at the rendered pages: page count, where each page ends, the summary within four lines, no bullet past two lines, no line ending on one or two words, page two full. LibreOffice is not Word (it draws Calibri with Carlito, which has the same widths [S80]), so treat the render as a check on page count and obvious wreckage, not as Word's exact line breaks.

`parse_check.py` checks the file's structure, including that the DOCX carries every part Word writes. It cannot tell you what a form will fill in. The live Workday test that set this skill's layout found the stand-in parser calling every role clean while Workday mangled six of eight [L01]. The only real parse test is an upload and a field-by-field review.

## Deliver

Exactly three things:

1. **The DOCX**, named `Firstname-Lastname-Resume.docx`.
2. **The plain-text copy** that `build_resume.py` writes beside it, for paste fields.
3. **A short brief** in the response, under 150 words: which required qualifications are proven and where, what was written in and why, every gap by name, every provisional value, every question for the candidate, and the record line (titles and dates against LinkedIn, and the formal title for any role the resume words differently). The format is in `references/tailoring.md`, The brief.

Then give the **post-upload review** for the system the posting uses (`references/readers.md` has the checklist). It follows the brief and doesn't count toward its 150 words. It is a required step, not a tip. In the live test, the autofilled Workday form needed hand fixes on 6 of 8 roles before this skill's layout existed, and it added a false language every time [L01]. On Eightfold and in chat applications there is no form to fix, so the file must be right before it is sent [L03].

When a positioning file was used, the brief adds its POSITIONING line (`references/tailoring.md`, The brief), and when job-seeker-ops's submission-review skill is also available, one last line offers a submission review of the finished resume. Without a positioning file, neither appears.

Keep each resume's JSON source beside its DOCX so it can be rebuilt. No other files: no folder per application, no coverage report, no log. Hundreds of applications must not produce thousands of files. The candidate's standing files are their evidence and the rulings file, plus the facts file if they chose one.

## Rulings

Two kinds of decisions come out of this work, and each has one home.

- **General build rules** (true for any candidate) go into this skill: the reference file that owns the topic, a version bump, and a line in `CHANGELOG.md`, the same day.
- **Candidate rulings** (facts, credit, titles, dates, personal build preferences) go into the candidate's rulings file (`templates/rulings.md`), the same day, with the date.

Memory, chat history and session notes can point at a ruling, but they are never the only copy. A ruling that lives only in a conversation will be applied by one session and missed by the next.

## Files

| File | What it owns |
|---|---|
| `references/readers.md` | The readers: what each system's form and AI grader do; the record check; knockout questions; the post-upload review |
| `references/sources.md` | Every source the skill cites, by ID: date, grade, URL, what it supports, a quote, and where it is used |
| `references/document.md` | The document: sections and order, contact block, role layout, titles, education, skills line, length, file and format rules, the build checklist |
| `references/writing.md` | Lines: bullets, numbers, the summary, AI-writing tells, plain and exact words, words the sentence already means, what never goes on a resume |
| `references/tailoring.md` | Reading a posting, mapping the evidence to it, the requirement check, title language, exact terms, what changes from one posting to the next, a positioning file, the base resume's requirement map, the brief |
| `references/intake.md` | Evidence in: the contact block, any file in any format, small and large evidence, contradictions, built assets, choosing a target, the rulings file and the optional facts file |

| Script | Does |
|---|---|
| `detect_ats.py` | Names the system behind a posting link, what its form fills, and what AI grading it sells |
| `requirement_check.py` | Turns a posting's required and preferred qualifications into a checklist; with `--evidence`, the best passages in the candidate's files for each one (file, heading, line); with a resume, the proof lines on the page |
| `term_coverage.py` | Posting terms by tier against a resume; `--composite` across many postings |
| `corpus_triage.py` | Maps a pile of career material: claims graded, roles, contradictions, repeats, possible targets |
| `draft_review.py` | Writing rules and general AI-writing tells, on the JSON source or a DOCX |
| `build_resume.py` | Writes the DOCX and the plain-text copy from one JSON source; refuses structural faults |
| `parse_check.py` | Structure check of a DOCX: layout faults, contact, headers, dates, markers |
| `render_pdf.py` | Renders a check PDF with LibreOffice so the page can be looked at |
| `widow_check.py` | Lines ending on one or two words, and bullets past two lines, read off the render |
| `positioning_check.py` | Reads a positioning file from job-seeker-ops's candidate-positioning skill at intake, and checks a built resume against its keep-off list and its words to use. Nothing else reads the file |
| `profile_check.py` | The resume's titles, companies and dates against the candidate's LinkedIn jobs file |

Python 3.8 or newer, standard library only. `render_pdf.py` needs LibreOffice and `widow_check.py` needs `pdftotext` (poppler); without them the visual check does not run, and they say so. `python tests/run_tests.py` runs the tests.

`templates/rulings.md` holds the candidate's settled decisions and build preferences. `templates/candidate-facts.md` is the optional facts file: confirmed numbers and answers, saved after a build so the next posting goes faster.

## Keeping it honest over time

- **The evidence beats memory.** What the candidate gave you, and the rulings file, are the record. A resume built earlier, a summary or a recollection never outranks the evidence it came from.
- **One record, every resume.** Titles, companies, cities and dates come from the evidence and read the same on every resume built from it. `scripts/profile_check.py` checks them against the LinkedIn jobs file.
- **Rulings are permanent.** Re-raising a settled point wastes the candidate's time and reads as not listening.
- **Checks stay mechanical.** Anything a script can check, a script checks, so the judgment left is the writing itself.
- **One rule, one home.** Each rule lives in one reference file. If you find the same rule stated two ways, the owning file wins; fix the other and log it in `CHANGELOG.md`.
- **One source, one row.** Every outside fact cites an ID from `references/sources.md`. A new fact enters with its source row the same day; `tests/test_sources.py` fails on a missing or unused ID.
- **When scores are good and nothing happens,** ask how many applications went out and how many got a screen. Recorded interview rates run about 3 to 6% [S61], so zero screens in twenty sends happens by chance a third to half the time. If a resume that proves every requirement gets no screens after about fifty tailored sends, the problem is likely the target, the level or the volume. Say that plainly instead of editing again.
