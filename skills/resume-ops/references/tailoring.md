# Tailoring

How a posting becomes a work order, and how the candidate's evidence answers it. The work order is a requirement check: every required qualification is proven, written in, or named as a gap. HiredScore's B grade needs every required qualification met [S05], and tailored applications reached interviews about 1.85 times as often in one vendor's tracked data, where interview rates peaked at 40 to 59% keyword coverage and fell above it [S61]. Source IDs point to `references/sources.md`.

## Read the posting

1. **Run `scripts/detect_ats.py` on the link.** It names the applicant system (or the front end in front of it), what its form fills from the file, and what AI grading it sells. That decides what the post-upload review looks like (`references/readers.md`).
2. **Fetch the posting and check it is the employer's own text:** the title, the requirements, the company's own words. Ask the candidate to paste it only when the fetch hits a login wall, a consent banner, a search results page or an aggregator's rewrite, and say which. A summarizing fetch or an aggregator copy loses exact wording; note that in the brief.
3. **Pull out:** the exact title; every required qualification, word for word; every preferred one; every named tool, certification and credential; and any phrase repeated three or more times. Note any AI-screening notice or opt-out; that is a question for the candidate.

## The requirement check

It runs twice: on the evidence before writing, and on the page after building.

**On the evidence.** `scripts/requirement_check.py posting.md --evidence notes.md record.md old-resume.docx` lists every required and preferred qualification from the posting's own headings. For each one it returns the best passages in the evidence, each with the file, the heading above it and the line; for a list qualification ("journey maps, service blueprints, Figma") it looks for passages that cover different parts of the list. It also prints a map of each file's headings and says whether the file is small enough to read whole or should be searched (`references/intake.md`, Small evidence, large evidence). The match is word overlap: it says where to look, and the proof comes from reading the passage.

**On the page.** `scripts/requirement_check.py posting.md out/Name-Resume.docx` gives each qualification up to two lines from the resume that share its words and a first guess: LIKELY, WEAK (only the summary, headline or skills line has it) or NONE. The guess is word overlap, not a grade. Finish the checklist by hand.

For every required qualification, one of three actions, with the proof taken from the evidence:

- **Keep.** A line in the evidence proves it, in words a grader would match to the qualification. It goes on the page in the role where the work happened. A title alone doesn't prove it, and neither does a skills list: a line has to show the work.
- **Write.** It is true, and the evidence shows where it happened, but no line says it plainly. Write the true line into that role. Use the posting's words where they are accurate ("patient throughput", "Epic", "Tableau dashboards").
- **Gap.** It is not true, or the evidence cannot show it. It stays off the page. It goes in the brief by name. Never write around a gap, never put the term in a list to catch a search, never hint at it.

A qualification with no passage gets a second search in the candidate's own words, then a question, before it is called a gap.

Then the preferred qualifications, the same way, once every required one is settled.

How to prove the common kinds:

- **Years of experience ("10+ years in X").** Count from the role dates, only the roles that did X. If the count falls short, it's a gap, not a rounding question. The summary's years are a different count: the whole career (`references/writing.md`, The summary). Never attach the career number to X unless the jobs that did X add up to it.
- **A degree.** Education shows it or it's a gap. "Or equivalent experience" is the candidate's call to argue in the application, not on the page.
- **A tool.** Inside the bullet where it was used. `requirement_check.py` marks a tool found only on the Skills line as WEAK for that reason.
- **Leading people.** Team size, who, and what came of it: "Built and led a team of 6 analysts." Mentoring counts when it names who was mentored and what they went on to do.
- **Behaviors ("executive presence", "influence without authority", "comfort with ambiguity").** A line that shows the behavior with a named audience or outcome: "Presented the three-year plan to the CFO and board; it was funded in full." Never the adjective itself.
- **Domain knowledge the candidate has from adjacent work.** Name the true overlap ("sold into hospital labs at two diagnostics clients"), or it's a gap.
- **Travel, work authorization, location, schedule.** Form questions, not resume lines. Leave them for the application.

## The top of the page

- **The summary's first sentence carries the posting's title language** where it is honest ("Director of Supply Chain" language for a supply chain strategy director). Never change a past title to match (`references/document.md`, Titles).
- **The summary's proof sentence answers the posting's top requirement,** the one the posting leads with or repeats most. It changes per posting. Running the same proofs on every resume is the failure to avoid.
- **Each role's first bullet is the one that answers this posting,** where the role has one. Reorder; don't rewrite what already works.

## Exact terms

After the requirement check, run `scripts/term_coverage.py posting resume`. It lists the posting's terms by tier (the job title and required-section terms first, then preferred and repeated terms, then everything else) and marks which the resume covers. Use it to catch a true qualification the page states in different words: a keyword search needs the string [S20], and one use of the posting's exact term, inside a proof line, serves both the search and the reader. It's a check, not a target: no score means anything by itself, and a term the candidate can't honestly claim stays off.

The term list depends only on the posting, so before and after runs share one denominator. If the employer's name shows up as a term, pass `--employer Name`.

## What changes from one posting to the next

Every tailored resume is built from the evidence, not edited from the last resume. A resume built for an earlier posting can be one more input; it is never the starting point, and its choices don't carry over.

**Changes per posting:** which claims make the page and in what order, the bullets written to prove this posting's requirements, the summary, the headline if there is one, the Skills line.

**Never changes between resumes built from the same evidence:** titles, companies, cities and dates. They come from the evidence and the rulings file (with each formal title as held), and they read the same on every resume, so the resumes, the profile and the employer's record tell one story (`references/readers.md`, The record check). `scripts/profile_check.py` checks them against the LinkedIn jobs file.

If the evidence can't prove about 70% of the required qualifications, the candidate competes against better-fitting people every time (`references/intake.md`, Choosing a target). Say so in the brief.

If page two comes up short, go back to the evidence for the next strongest claim for this posting before touching anything else.

## A positioning file

job-seeker-ops's candidate-positioning skill writes one positioning file per posting, `positioning-<company>-<role>.md`, beside the candidate's files. It holds the case for this posting, a requirement map with the evidence behind each row, the proofs ranked for the posting, the words the candidate can claim, and what stays off the page. When there's one for this posting, run `scripts/positioning_check.py positioning.md --posting posting.md` at intake. Without one, nothing in this section applies and the build runs as it always has.

- **Use it only when the script says to.** A file that isn't confirmed, or that was built from another copy of the posting, isn't used, and the brief says why. For another copy of the posting, ask the candidate once whether to use the file anyway.
- **It isn't evidence.** It sets direction and order. Every title, date, number and claim on the page still comes from the evidence and the rulings file, settled as Keep, Write or Gap. Where the file and the evidence disagree, the evidence wins and the brief names the difference.
- **A ruling beats it.** When the rulings file says otherwise, follow the ruling.
- **The case lines set the summary's direction.** The summary's proof sentence answers the file's first line, what the hiring team wants, and the summary aims at its fourth, what the reader should believe. The second line is a working note and never goes on the page.
- **The proof bank sets the order.** In each role, the first bullet is the proof the file ranks highest for that role, when the evidence proves it. A proof marked "On the resume being sent: no" goes on the page only when it's marked resume or both and the evidence proves it.
- **The words to use feed the term check.** They're the posting's terms the candidate can claim. After the build, `positioning_check.py --resume` lists the ones on the page, matched the way `term_coverage.py` matches terms. Add a missing one only inside the line that proves it.
- **The keep-off list stays off.** Gaps, the hiring team's concern and anything sensitive never go on the page, however they're framed. `positioning_check.py --resume` fails when one of the list's watch phrases shows up.

## The base resume: a requirement map for a title family

Optional, and never a prerequisite for a tailored resume. A base resume has no single posting to answer, so it answers the market. It's for job boards, recruiter databases and referrals when there is no posting, and for a candidate who wants a few anchor resumes.

1. Collect 8 to 12 live postings for the target title, same level, posted within 90 days. Fewer is fine when the market is thin; say how many. (These counts and the tiers below are the skill's working thresholds, not sourced figures.)
2. Run `requirement_check.py` on each. Group the required qualifications that recur across postings (they will be worded differently; group them by what they ask for).
3. Run `term_coverage.py --composite` across all of them. Terms in 60% or more of the postings are Tier 1 for the base; 30 to 59%, Tier 2.
4. The qualifications that at least half the postings require are the base resume's must-proves. List them under a Requirements heading in one file and run `requirement_check.py` on it with `--evidence`. Each one that is true for the candidate gets a proof line in a role. Each one they don't have gets named to them: if most postings require a credential they lack, that is a targeting problem, not a writing one.
5. The summary's first sentence uses the most common standard title for the family, and its proof sentence answers the must-prove that the most postings share.

A base resume stands alone: no cover letter, no posting-specific language, no company names of employers it's aimed at.

**Where it goes:** job boards (set Indeed to searchable, not private, unless the candidate has a reason), recruiter and staffing databases, and referrals when there is no specific posting. Re-upload after every edit; boards don't re-read a file changed on the candidate's computer. Recheck the requirement map every six months while searching.

## The brief

Under 150 words, in the response, delivered with the DOCX and the plain-text copy:

```
EVIDENCE: career-notes.md (read whole); record.md (searched).
REQUIREMENTS: 6 of 7 required proven (R4 Qualtrics: gap). 2 of 5 preferred.
WRITTEN IN: R2 team of 6 (Acme role); R5 dashboards in Tableau (Acme role).
GAPS: Qualtrics, SQL.
PROVISIONAL: "4 warehouses" (material says 4 and 5; asked).
QUESTIONS: opt out of the AI screen? (posting offers it)
RECORD: 8 of 8 jobs match LinkedIn (profile_check), or the titles and dates to check by hand; formal title for the forms: Senior Associate (Acme role).
SYSTEM: Workday. Post-upload review below.
CHECKS: draft_review 0 FAIL; structure PASS; 2 pages; 0 widows.
```

When a positioning file was used, add a line after RECORD: `POSITIONING: positioning-acme-planner.md (confirmed 2026-10-05); the evidence overrode nothing`, naming anything the evidence or a ruling overrode. Without a positioning file, the line doesn't appear.

Then the post-upload review checklist for that system (`references/readers.md`).

