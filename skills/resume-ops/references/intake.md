# Intake

How the evidence arrives. Never by handing the candidate a blank form: a form longer than the resume it produces is where people quit. Whatever they already have is enough to start, and nothing has to be built before the resume they asked for.

## First question: the contact block

Ask for it before anything else. Only the candidate has it, and a resume without it fails the structure check and can't be reached.

> What phone, email, LinkedIn URL, and city and state should go at the top?

Then, as the build reaches each role: the city and state of any role where the material has none. Never guess a city.

Ask once, optionally, for the jobs file from LinkedIn's own data download (a file named Positions.csv in current exports; the script reads any CSV with company, title and date columns). `scripts/profile_check.py` compares it with the resume's titles, companies and dates, so the resume and the profile tell the same story before a background check compares titles and dates with the employer's record (`references/readers.md`, The record check). No browser or login is needed on this side. If the candidate would rather not, the brief's record line lists the titles and dates to check by hand.

**Titles.** When a title will be written differently from the formal title (a reorder for Workday, or a descriptor the candidate wants to add), ask once and name the risk: a background check returns the formal title. A reorder is low risk; an added word is medium risk unless the formal title goes into the forms (`references/document.md`, Titles). Record the answer and the formal title in the rulings file.

## Evidence in any format

Evidence is anything the candidate has written or can say about their work: a resume of any age, a cover letter, a LinkedIn profile, a website or portfolio page, a career record, performance reviews, project write-ups, notes, a brain dump. One file is enough to start. More files make the claims stronger; none of them has to be a finished resume, and none has to be built first. A positioning file from job-seeker-ops's candidate-positioning skill isn't evidence: it's read at intake for direction and order (`references/tailoring.md`, A positioning file).

| They give | How to read it |
|---|---|
| DOCX | As it is. The scripts read Word files directly. |
| PDF | `pdftotext -layout file.pdf file.txt` when poppler is installed (`requirement_check.py --evidence` runs it itself); otherwise read the PDF directly. A designed PDF can scramble the reading order, so check the text against the page. |
| LinkedIn | The profile saved as a PDF (read as a PDF), or the data download: Positions.csv holds titles, companies and dates, and `scripts/profile_check.py` reads it. |
| A website | Fetch the page and save its text, or have the candidate paste it. |
| Markdown, text, notes | As they are. |
| Nothing written | The conversation below. |

These times are the skill's working estimates.

| They have | Their time |
|---|---|
| A pile: old resumes, a LinkedIn export, reviews, write-ups, notes | 20 to 30 minutes reviewing |
| One file: a resume, a profile, a career record | 10 to 15 minutes answering gaps |
| Nothing written down | 20 to 30 minutes talking |

## Small evidence, large evidence

The read-whole line is about 2,000 lines or 150 KB of text (the skill's working line; `requirement_check.py` holds it as `READ_WHOLE_LINES` and `READ_WHOLE_BYTES`).

- **Under the line: read every line,** start to end, and check your last line against the file's line count. Credentials and awards carry no numbers and sit at the end of most files, which is exactly where a partial read stops.
- **Over the line: search it; don't read it whole.** `scripts/requirement_check.py posting.md --evidence file` splits the file on its headings, prints a map of them with line numbers, and for each qualification returns the best passages, each with the file, the heading above it and the line. Open only those passages, plus the sections on the map that hold the work history, education, credentials and awards. A qualification with no passage gets a second search in the candidate's own words (another name for the tool, the client, the project) and then a question. Never drop a qualification because the file was too big to read.

The search is word overlap. It finds where to look, not what is true: read each passage before a claim goes on the page, and take the claim from the passage, never from the search's summary of it.

### A pile of loose material

Rough, duplicated and contradictory are all fine. Finding the contradictions is half the value.

1. **Run `scripts/corpus_triage.py` on the whole file.** It splits the material into numbered claims with line numbers, grades each (A: a number and a named thing; B: one of the two; C: specific but nothing to check; D: assertion only; L: a keyword list), finds roles and employers, flags career facts stated more than one way, groups claims that name the same clients, pulls out internal names that need plain labels, sets aside self-description with nothing to verify, and suggests targets with how many employers show the proof.
2. **Then read the material yourself** (under the line, every line; over it, the passages and sections above). The triage is a map, not a reading. Credentials and awards grade low, so the triage sweeps them into their own table so none is dropped.
3. **The candidate touches three things:** the contradictions (usually 10 to 20 short answers, each settled once in the rulings file), the target when there is no posting (pick from the suggestions or name one), and importance on the shortlist (the script ranks how checkable a claim is; only the candidate can rank how much it matters). Do the ranking on the top 40 or so claims for the posting, not all of them. If the review runs past 30 minutes, cut the shortlist.

What the triage cannot do: it finds vocabulary, not career, so a word used constantly surfaces as a target whether or not it is the strongest work. It misses the line between self-description and method now and then. It can't tell an inflated verb from an accurate one: career material is written in sell voice, so ask about any verb doing heavy lifting.

A career record the candidate keeps, with one entry per project and its sources, doesn't need the triage: search it.

### One old resume

1. Run `scripts/parse_check.py` on it to see what it holds.
2. Carry the structure across: roles, titles, companies, cities, dates, education, certifications, tools.
3. Grade each bullet A to D.
4. Ask only about the gaps the posting needs: every C or D bullet that the posting depends on is one question ("what was the number here?", "which client was this?"). The candidate can see which line each answer fixes, so it goes fast.

### Conversation

Work backward from the most recent role. Four to six questions for recent roles, two for older ones:

1. What was the job, and what did you spend your time on?
2. What was the biggest thing you changed or built there?
3. How big was it? Team, budget, accounts, sites, volume.
4. What happened as a result? Push once for a number, then move on. For anything built, opened or launched: does it exist now, and what is it called?
5. What did you do there that nobody asked you to do? (This is usually the best material.)
6. Who were the clients, and can they be named publicly?

Chase a number once. "Roughly how many?" is fair; three rounds of pressing produces invented numbers. Write the question into the brief and move on; people remember mid-application. The answers are evidence: write them down in the session so each claim can point to one.

## Contradictions

When the same career fact appears two ways (years of experience, a team size, a revenue figure, a date), ask which is true. Each answer goes in the rulings file and is never asked again. Until it's answered, the value on the page is provisional and the brief names it. If nobody can answer this session, use the more conservative value.

## Things the candidate built that others still use

A method, tool, template, protocol or curriculum the candidate made and other people adopted. The grading scores it low because it reads as a definition with no number, but it's often the strongest differentiator in the pile. Ask three questions, nothing else:

1. **Where was it built?** The employer and year. That attaches it to a role.
2. **Who adopted it?** Other teams, other firms, a client, a department. Adoption by someone else is the proof.
3. **How many times has it run?** Sites, users, engagements, years.

One answer turns a definition into a claim. All three make it an A. On the page it goes in a bullet at the employer where it was built, described in plain words. A coined name nobody searches for stays off (`references/document.md`).

## Choosing a target

A posting sets the target for a tailored resume. This section is for a base resume, and for a candidate who asks which postings to aim at. If the candidate doesn't know their target, analyzing it is part of the job; don't hand the question back. Score each candidate target on six things. The material answers three; the other three need live postings. The cut-offs in the table (three grade-A claims, three employers, about 70% fit) are the skill's working thresholds.

| | From | Asks |
|---|---|---|
| Evidence | Material | How many grade-A claims? Under three, it's a story, not a case. |
| Repeatability | Material | How many different employers show the proof? One is an anecdote; three is a capability. |
| Recency | Material | How old is the newest strong proof? |
| Market size | Postings | How many open jobs, at what level and pay? |
| Title | Postings | Is there a standard title recruiters search for? If searching the work's plain name returns a different job or nothing, it's a strength inside another target, not a target. |
| Fit | Postings | What share of the required qualifications across 8 to 12 postings can the candidate truly prove? Below about 70%, they compete against better-fitting candidates every time. |

Then make three calls, plainly: **pick** (one target, with the reason), **runner-up** (a second target worth building for), and **recommend against** (the target that looks strongest from inside the material and fails on the market; name it and say why). Watch for the common trap: the candidate's most current, most repeatable work sits in a market that treats it as a task inside someone else's job. When material and market disagree that sharply, the market is where the jobs are.

The target is a ruling. Write it down; don't reopen it every session.

## The rulings file and the facts file

**The rulings file** (`templates/rulings.md`) holds decisions the candidate has made: the contact block, answers to contradictions, credit and naming rules, title forms (with each formal title as held), the target, and personal build preferences (the belief sentence, a section they want or don't want). Add each ruling the day it's made, dated. A later ruling that covers an earlier one closes it; note the reversal under the earlier one rather than deleting it. Never raise a ruled point again.

**The facts file** (`templates/candidate-facts.md`) is optional. Offer it after the first build: it saves the confirmed numbers and answers from that build, each tagged to its source line, so the next posting goes faster. Write it only with the candidate's yes. Once it exists it is one more piece of evidence, the most trusted one: every number carries a tag (confirmed, estimate for hedged wording only, or do-not-use), and a number there outranks the same number stated another way elsewhere.

If the evidence is already a career record the candidate keeps, don't create a second copy of it. New confirmed numbers go into that record, by the candidate's hand or with their yes, and the rulings file holds the decisions.

A general rule about how resumes should be built doesn't go in the candidate's rulings file. It goes in the skill (SKILL.md, Rulings).
