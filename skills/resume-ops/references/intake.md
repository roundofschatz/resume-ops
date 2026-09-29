# Intake

How the facts arrive. Never by handing the candidate a blank form: a form longer than the resume it produces is where people quit. The facts file is an output of the first build, not a gate in front of it.

## First question: the contact block

Ask for it before anything else. Only the candidate has it, and a resume without it fails the structure check and can't be reached.

> What phone, email, LinkedIn URL, and city and state should go at the top?

Then, as the build reaches each role: the city and state of any role where the material has none. Never guess a city.

Ask once, optionally, for the jobs file from LinkedIn's own data download (a file named Positions.csv in current exports; the script reads any CSV with company, title and date columns). `scripts/profile_check.py` compares it with the resume's titles, companies and dates, so the resume and the profile tell the same story before a background check compares titles and dates with the employer's record (`references/readers.md`, The record check). No browser or login is needed on this side. If the candidate would rather not, the brief's record line lists the titles and dates to check by hand.

**Titles.** When a title will be written differently from the formal title (a reorder for Workday, or a descriptor the candidate wants to add), ask once and name the risk: a background check returns the formal title. A reorder is low risk; an added word is medium risk unless the formal title goes into the forms (`references/document.md`, Titles). Record the answer and the formal title in the rulings file.

## Three ways in

Ask what they already have. Most people have more than they think.

These times are the skill's working estimates.

| They have | Path | Their time |
|---|---|---|
| A pile: old resumes, a LinkedIn export, reviews, project write-ups, a brain dump | Material | 20 to 30 minutes reviewing |
| One current resume | One resume | 10 to 15 minutes answering gaps |
| Nothing written down | Conversation | 20 to 30 minutes talking |

### Material

Rough, duplicated and contradictory are all fine. Finding the contradictions is half the value.

1. **Run `scripts/corpus_triage.py` on the whole file.** It splits the material into numbered claims with line numbers, grades each (A: a number and a named thing; B: one of the two; C: specific but nothing to check; D: assertion only; L: a keyword list), finds roles and employers, flags career facts stated more than one way, groups claims that name the same clients, pulls out internal names that need plain labels, sets aside self-description with nothing to verify, and suggests targets with how many employers show the proof.
2. **Then read every line yourself,** start to end, and check your last line against the file's line count. The triage is a map, not a reading. Credentials and awards carry no numbers, so they grade low, and they sit at the end of most files, which is exactly where a partial read stops. The triage sweeps them into their own table so none is dropped.
3. **The candidate touches three things:** the contradictions (usually 10 to 20 short answers, each settled once in the rulings file), the target (pick from the suggestions or name one), and importance on the shortlist (the script ranks how checkable a claim is; only the candidate can rank how much it matters). Do the ranking on the top 40 or so claims for the chosen target, not all of them. If the review runs past 30 minutes, cut the shortlist.

What the triage cannot do: it finds vocabulary, not career, so a word used constantly surfaces as a target whether or not it is the strongest work. It misses the line between self-description and method now and then. It can't tell an inflated verb from an accurate one: career material is written in sell voice, so ask about any verb doing heavy lifting.

### One resume

1. Run `scripts/parse_check.py` on it to see what it holds.
2. Carry the structure across: roles, titles, companies, cities, dates, education, certifications, tools.
3. Grade each bullet A to D.
4. Ask only about the gaps: every C or D bullet is one question ("what was the number here?", "which client was this?"). The candidate can see which line each answer fixes, so it goes fast.

### Conversation

Work backward from the most recent role. Four to six questions for recent roles, two for older ones:

1. What was the job, and what did you spend your time on?
2. What was the biggest thing you changed or built there?
3. How big was it? Team, budget, accounts, sites, volume.
4. What happened as a result? Push once for a number, then move on. For anything built, opened or launched: does it exist now, and what is it called?
5. What did you do there that nobody asked you to do? (This is usually the best material.)
6. Who were the clients, and can they be named publicly?

Chase a number once. "Roughly how many?" is fair; three rounds of pressing produces invented numbers. Write the question into the brief and move on; people remember mid-application.

## Contradictions

When the same career fact appears two ways (years of experience, a team size, a revenue figure, a date), ask which is true. Each answer goes in the rulings file and is never asked again. Until it's answered, the value on the page is provisional and the brief names it. If nobody can answer this session, use the more conservative value.

## Things the candidate built that others still use

A method, tool, template, protocol or curriculum the candidate made and other people adopted. The grading scores it low because it reads as a definition with no number, but it's often the strongest differentiator in the pile. Ask three questions, nothing else:

1. **Where was it built?** The employer and year. That attaches it to a role.
2. **Who adopted it?** Other teams, other firms, a client, a department. Adoption by someone else is the proof.
3. **How many times has it run?** Sites, users, engagements, years.

One answer turns a definition into a claim. All three make it an A. On the page it goes in a bullet at the employer where it was built, described in plain words. A coined name nobody searches for stays off (`references/document.md`).

## Choosing a target

If the candidate doesn't know their target, analyzing it is part of the job; don't hand the question back. Score each candidate target on six things. The material answers three; the other three need live postings. The cut-offs in the table (three grade-A claims, three employers, about 70% fit) are the skill's working thresholds.

| | From | Asks |
|---|---|---|
| Evidence | Material | How many grade-A claims? Under three, it's a story, not a case. |
| Repeatability | Material | How many different employers show the proof? One is an anecdote; three is a capability. |
| Recency | Material | How old is the newest strong proof? |
| Market size | Postings | How many open jobs, at what level and pay? |
| Title | Postings | Is there a standard title recruiters search for? If searching the work's plain name returns a different job or nothing, it's a strength inside another target, not a target. |
| Fit | Postings | What share of the required qualifications across 8 to 12 postings can the candidate truly prove? Below about 70%, they compete against better-fitting candidates every time. |

Then make three calls, plainly: **pick** (one target for the base resume, with the reason), **runner-up** (a second base resume worth building), and **recommend against** (the target that looks strongest from inside the material and fails on the market; name it and say why). Watch for the common trap: the candidate's most current, most repeatable work sits in a market that treats it as a task inside someone else's job. When material and market disagree that sharply, the market is where the jobs are.

The target is a ruling. Write it down; don't reopen it every session.

## The facts file and the rulings file

**The facts file** (`templates/candidate-facts.md`) is written at the end of the first build, from the claims that made the page, each tagged to its source line, and only after the candidate says yes to it. From then on it's the record: nothing goes on a resume that isn't in it. Every number carries a tag: confirmed, estimate (hedged wording only, with approval), or do-not-use. It grows as the candidate applies: every new number, every answered question, every new piece of work goes in when it arrives.

**The rulings file** (`templates/rulings.md`) holds decisions the candidate has made: answers to contradictions, credit and naming rules, title forms (with each formal title as held), the target, and personal build preferences (the belief sentence, a section they want or don't want). Add each ruling the day it's made, dated. A later ruling that covers an earlier one closes it; note the reversal under the earlier one rather than deleting it. Never raise a ruled point again.

A general rule about how resumes should be built doesn't go in the candidate's rulings file. It goes in the skill (SKILL.md, Rulings).
