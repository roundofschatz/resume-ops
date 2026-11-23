# Writing the lines

How every line on the page is written: bullets, numbers, the summary, and the tells that make a page read as generated. Where lines go is in `references/document.md`. Source IDs in square brackets point to `references/sources.md`; rules without one are the skill's own judgment.

## Two tests for every line

**Could someone who did not do this job have written it?** "Collaborated with cross-functional teams to drive results" could be written by anyone about anything. A line earns its place when it holds something only a person who was there would know: a number, a named client or tool, a constraint, an outcome.

**Would a stranger understand it on one read?** Not a colleague: someone who has never heard of the candidate's employers or their internal names. A line fails this test through internal vocabulary (a coined name or program nickname), undecoded proof (naming the document, not what it did), assumed context, or process shorthand. The fix is almost never a longer sentence. It is the outsider's word for the thing, and what came of it.

## Bullets

Shape: `[Verb] [specific thing] [for whom, at what scale], [result].` The result is the point.

- **Weak:** Responsible for maintaining company servers and resolving user issues.
- **Strong:** Migrated 40 on-prem servers to AWS over 5 months, cutting infrastructure cost 34% and median ticket time from 3 days to 6 hours.

The shape holds in every field:

- **Nursing:** Ran a 6-bed assignment on a 32-bed med-surg unit, precepted 11 new graduates over two years, and led the fall-prevention rollout that cut unit falls from 9 to 2 per quarter.
- **Finance:** Owned month-end close for 3 entities, cutting the cycle from 12 days to 5 and clearing two audits with no adjustments.
- **Trades:** Maintained 22 CNC machines across two shifts and cut unplanned downtime 41% by rebuilding the preventive maintenance schedule.
- **Teaching:** Taught 5 sections of Algebra II to 140 students and raised end-of-course pass rates from 61% to 82% over three years.

Rules:

- **Verbs.** Past tense for finished work, a finished project in the current role included; present tense for ongoing work in the current role [S128, S131, S132]. Present tense takes the base form, as if "I" came before it: "Run", "Build", "Lead", never "Runs", "Builds", "Leads", which is third person [S131, S133, S145]. Active voice: "Won the county contract", never "Hired by the county" [S66, S130, S132, S133]. Plain verbs: led, built, ran, launched, cut, grew, won, wrote, designed, opened, hired, fixed. Never open with "Responsible for", "Duties included", "Helped with", "Worked on". `draft_review.py` fails a third-person verb and flags a passive one.
- **Implied first person.** No "I", "my", "we", or "our" anywhere on the page, and never "he" or "she" [S66, S67, S127, S128, S129, S130]. One guide asks for third person in the summary [S144]; the rest, and this skill, don't.
- **No contractions.** "Did not", "who has", not "didn't", "who's" [S67, S133, S134]. A cover letter or a LinkedIn profile can contract. `draft_review.py` fails a contraction.
- **One to two rendered lines.** The guides agree on two lines at most [S62, S136, S137]. The render decides, and `widow_check.py` measures it. Before the render, `draft_review.py` flags a bullet past 35 words, about two lines at the build's default type and margins (a hint, the skill's judgment). A third line is setup the reader doesn't need: keep the result, cut the context.
- **No line ends on one or two words alone.** Fix it by changing words until the line count changes, never with a manual break, a non-breaking space, or a spacing tweak.
- **New evidence strengthens a line; it doesn't multiply lines.** Put the new fact into the bullet it proves.
- **The first bullet of a role is its strongest proof for this target,** not its main duty. The duty is what the reader already assumes from the title. This is the skill's judgment: no study tests bullet order. One found that where competency statements sat, across the resume and cover letter, made no difference to ratings [S116], and screeners in an eye-tracking lab looked at the whole resume [S113]. Leading with the strongest proof costs nothing.
- **Name what you count.** A count of named things names them all or drops the number: "three clinics, including Eastside and Riverview" reads as if the writer couldn't name the third. A count of abstract things (decisions, directives, priorities, themes, recommendations, principles, pillars, goals, needs, initiatives, tools, and the like) names the set: what it was about or for. It doesn't need every item. "Settled seven decisions" names nothing; "settled seven decisions on pricing and the launch date" does. The name has to be specific to the work: "seven key decisions" and "seven strategic decisions" still name nothing, and so does an owner alone ("five priorities for the district"). If the evidence can't name the set, drop the count. A count of concrete things (stores, employees, interviews, survey responses) is scope, and it stands as it is. `draft_review.py` fails a count that names nothing, and flags a count for review when the words after it may only say whose set it was.
- **A label is not content.** "Key insights", "strategic recommendations", and "the findings" stand in for something the reader never gets. Say what they were, or what they were about: "insights on churn". "The findings" can stay when the same line names the work they came from and what they became. `draft_review.py` fails a label built on a generic word ("key", "strategic", "actionable") with nothing behind it.
- **A page count is not a result.** "A 60-slide deck" measures the document. Use the figure the work was about (units, sites, people, dollars), or say that it got built.
- **Claim the layer you worked at.** On work several disciplines delivered, name the part that was the candidate's. The narrower claim is usually the more senior one, and it survives a reference check.
- **A status tag pinned to the end is not a result** ("now built", "since acquired"). Put it in the grammar or cut it.
- **Tools go inside the bullet where they were used.** "Rebuilt the preventive maintenance schedule in Fiix" proves the tool; "Fiix" on a list does not. Put the tool in the bullet for the work it was used on. If that work is true but missing from the page, write the bullet for the work; never write a bullet only to hold a tool name.
- **Vary the metric type.** A page where every bullet ends in a percentage reads as templated. Mix counts, dollars, time, rankings, and adoption.

## Numbers

Every number traces to a line in the candidate's evidence or to an answer they gave. An "about" in the candidate's own writing is their wording; keep their hedge. The test for every number: **can the candidate defend it cold in an interview?** Where it came from, how it was measured, the baseline, what they did to move it.

- **Missing number:** write the bullet with scope or a named specific instead, and put the question in the brief. Never a working marker in the file; `build_resume.py` refuses them.
- **Real beats round.** "Cut the close from 11 days to 4" beats "cut close time about 65%".
- **For design, planning and product work, the result is often whether the thing exists.** Did it get built, did it open, who runs it now. Ask: candidates rarely volunteer it. Keep the causal claim honest.
- **No number at all:** scope works. Team size, client count, budget, markets, volume.
- **Numbers people forget they have:** team size and reports, budget owned, clients or sites or products, time against plan, volume per week, before and after on any metric, share of a total.
- **Numerals for 10 and up:** "16 years", "130 employees". The guides agree on numerals from 10 up [S67, S126, S139, S145]. Under 10, a word or a numeral, used the same way throughout [S145]. Money and percentages always take numerals: "$2M", "5%" [S67]. Numerals catch the eye of a reader who is skimming [S139, S140]. `draft_review.py` flags a written-out number of 10 or more inside a sentence.
- **The number in the first line of the bullet,** where the sentence allows. Readers skimming a web page look hardest at the first words of each line [S141]. No resume study tests it (the skill's judgment).

## When the client can't be named

Work down this ladder and stop at the first rung that is allowed:

1. **Named client, named work, result:** "Rebuilt the loyalty program for Harbor Grocers; enrollment up 31% in eight months."
2. **Named approach, sector, scale, result:** "Designed a three-stage intake process now used by five county clinics."
3. **Client type, scale, result:** "Top-three regional grocery chain: repositioned the store brand for two new markets." Last resort; use it for one or two bullets at most.

Never write around a restriction in a way that implies more access than the candidate had. The result is almost never the confidential part.

## The summary

A prose paragraph of full sentences under the Summary header, up to four rendered lines, about 75 words, no bullets. It's the pitch: who the candidate is and why they fit this employer. Results belong in the bullets, each one in the job that produced it. A summary assembled from slots (title and years, one result, one pattern, a closing line) reads choppy and sells nothing, so don't build one that way.

No study tests a summary's length or form. Stanford GSB says "Limit the summary to 4 lines plus bullet points" [S62]; Yale says fifty words or fewer [S63]; the median of 23,191 summaries on one job platform was 64 words [S147]; the federal labor statistics office calls a summary optional [S125]; and the one outcome dataset found no reliable interview effect from having one [S98]. This skill drops the bullets: bullets under the summary repeated the roles below them in every resume of the skill's 2026 test [L05]. It holds the paragraph to four lines, about 75 words at the build's default type, because every source found points that short and none points longer, and every summary line pushes the first job, where screeners look longest [S113], further down page one. Two guides are not enough to make it a convention, so the limit is the skill's judgment until a test settles it, and it holds for every candidate (SKILL.md, Rulings: Evidence first). The test: the candidate's own callbacks, or a blind read through job-seeker-ops's submission-review of one resume with a 50-word and a 75-word summary. No claim may live only in the summary.

**What it covers.** Three things, in whatever order and number of sentences the evidence and the candidate's voice call for:

- What the candidate does, for whom, and what comes of it.
- The run of work that matches this employer, by name (clients, places, programs), with the career's years and the range of fields.
- What they've built and led: practices, teams, people trained, and kinds of products.

**Start from a summary that worked.** Before writing, ask whether the candidate has a summary that got an interview, or one they wrote themselves, and look for one in the evidence. Use it as the voice model: its sentence shapes, its rhythm, its words for the work. Take the shape, not the words. Drop anything a rule here or a candidate ruling bans, and any fact that has gone stale (an old year count, a title no longer held). Record which summary is the model in the rulings file. With no model, write from the evidence in plain, full sentences.

**Rules.** These protect the candidate. Everything else is the writer's call.

- **The posting's title language opens the summary,** where it's honest. Title match went with higher interview rates in one vendor's data [S60], and AI graders read the summary (`references/readers.md`). On a base resume, use the most common standard title for the family.
- **The years count the whole career:** this year minus the year the career started (for most people, the year they finished school). The words beside that number have to fit the whole career too. A posting's "N years in X" is a different count, from only the jobs that did X (`references/tailoring.md`).
- **Implied first person.** Never "I", "my", "we", or "our", and never "he" or "she" [S66, S128]. A sentence can be built on a noun phrase ("Logistics manager who runs..."), with a "who" clause where the voice calls for one, or open on a past-tense verb ("Built", "Led"). Never open a sentence on a third-person verb ("Leads", "Runs", "Builds", "Has"), and never "A results-driven professional who". Don't fix one by dropping the "s": "Run regional distribution for grocers" reads as an order. Rebuild the sentence on a noun phrase or a past-tense verb. `draft_review.py` fails a summary sentence that opens on a third-person verb.
- **No self-rating in front of the role:** "Customer-obsessed strategist", "Passionate leader". Lower-key self-promotion raised perceived fit in one experiment [S117], and hiring managers name self-labels such as "dynamic" and "self-motivated" as turn-offs [S123]. The work shows it. `draft_review.py` flags it (the skill's judgment).
- Full sentences. No colon lists, no "Specialties:" line, no keyword strip at the end.
- Every count names what it counts ("three regional grocers: Harbor Foods, Valley Fresh, and Ridge Market") or drops the number.
- **The summary says in simpler form what the bullets below prove.** Every name and number in it has a job behind it: every client, place, number, and credential also appears in the role or section that holds it, because the form has no summary field [S02], field matchers score only extracted skills, titles, dates, companies, and years [S16], and AI graders look for the proof inside the job [S05, S31]. Repeating what the roles prove is the summary's job.
- **Never copy a bullet word for word.** Restate the claim shorter and at a higher level. The role keeps the full wording.
- **One exception: a career total the candidate confirmed.** A total that spans several jobs (workshops run, stores opened, new nurses trained) may sit in the summary with no single job behind it, once the candidate confirms the number. Record it (the rulings file, or the facts file if the candidate keeps one) and list it under `career_totals` in the JSON source (`references/document.md`) so `draft_review.py` passes it. A total the candidate hasn't confirmed is an estimate (SKILL.md, hard rule 2).

**Examples.** Three fields, three different builds. They show range, not a template; the candidate's own model sets the shape.

> Logistics manager who runs regional distribution for grocers and consumer-goods makers, keeping shelves full through peak season at a lower cost per case. Eleven years in warehousing and transportation, most of them running cross-dock and cold-chain sites for three regional grocers: Harbor Foods, Valley Fresh, and Ridge Market. Site leader who has opened two distribution centers, built the safety program the Harbor network still runs, and trained 40 shift leads across three shifts.

> Emergency charge nurse with 9 years in emergency and critical care at two Level II trauma centers, Mercy West and County General. Led the sepsis bundle rollout at Mercy West and took it to County General when the two hospitals merged their protocols. Built the charge-nurse orientation both units use and precepted 11 new graduates who now work charge shifts.

> Controller for private manufacturers who closes the books fast enough for owners to run the business on this month's numbers. Fourteen years in accounting, the last eight leading finance at Brightline Tool and Keller Plastics through two acquisitions. Built the month-end close at both companies, hired and trained the teams of four and six that run them, and took both through audits with no adjustments.

`draft_review.py` fails a bullet under Summary, a keyword strip, a first-person pronoun, and a figure or name found only in the summary, unless it is a listed career total. It asks you to re-read a summary outside 45 to 75 words, any count that names fewer items than it claims, and any summary sentence that copies a bullet word for word. It never counts results.

## AI-writing tells

A page can clear every rule and still read as generated. These are the general tells. Why they matter is research: recruiters marked down applicants they suspected of using AI by 40.6%, whether or not AI was used [S118]; told that candidates used AI, recruiters valued human-written letters more [S119]; and people can't tell AI self-presentations from human ones and judge by cues that mislead them [S121]. All of these studies used cover letters and profiles, not resumes. Which words raise the suspicion is mostly unknown. One row is measured as a mark of AI text: the model marker words, which jumped in 15 million abstracts after ChatGPT [S122]. The em dash rose in one unreviewed study of preprints [S148], so it stays the skill's judgment. The clichés row rests on a survey of hiring managers [S123]. Every other row is the skill's judgment. `draft_review.py` checks all of them, fails the near-certain ones, flags the rest for a second read, and prints each check's evidence beside the finding. A new tell enters as a review flag, and becomes a fail only once a count shows AI drafts use it far more often than human-written resumes do.

| Tell | Instead |
|---|---|
| Em dash for emphasis or drama; "--" as a dash | A period, colon, or comma |
| "Not just X, but Y"; "X, not just Y"; "isn't just X; it's Y"; "not only X but Y" | Say Y |
| "It's not about X, it's about Y" | Say what it is |
| "I am not an X. I am the person who..." | State the capability in its own terms |
| A vague weaker group to stand above: "unlike most", "a rare blend of", "few can" | Delete the first half. A named competitor or a measured baseline is a real comparison and stays |
| Throat-clearing openers: "In today's fast-moving market" | Start with the point |
| Hedges: very, really, quite, rather, fairly, somewhat, a bit, kind of | Cut them |
| Filler: actually, just, simply, literally, basically; sincerity words: honestly, genuinely | Cut them |
| Vague size words: significant, robust, comprehensive, powerful, seamless, impactful, high-impact, substantial, extensive | The figure they stand in for |
| Fluff verbs: leverage, unlock, drive, empower, elevate, streamline, foster, spearhead, orchestrate | A plain verb with an object |
| Weak claims: was involved in, played a role in, helped to, can help, may be able to | Say what the candidate did. "Contributed to" is flagged, not failed: it's the honest verb when the candidate's part was one of several (Bullets, Claim the layer you worked at) |
| Latinate defaults: utilize, commence, endeavor | Use, start, try |
| Cliches: results-driven, proven track record, passionate about, seasoned, dynamic, team player, go-getter, thought leader, world-class, best-in-class, cutting-edge, holistic, synergy, detail-oriented, self-starter [S123] | The evidence the cliche claims. When the posting itself uses the term ("team player", "detail-oriented"), its exact words win [S20]: use it once, in a bullet that proves it, and pass it with `draft_review.py --allow` |
| A self-rating in front of the role: "customer-obsessed strategist", "passionate leader" | Let the work show it [S117] |
| "From scratch" | "Built the program" is complete |
| Ending on air: "driving operational excellence", "delivering transformational value" | End on something a reader could check, or end the sentence a clause earlier |
| Everything in threes for rhythm: "faster, simpler, smarter" | Keep the one that is proven. Flagged in the summary only: in bullets and the Skills line, a list of three is usually three facts |
| "Whether you're X or Y" setups | Cut |
| Urgency codas and meta-statements: "ready to bring this energy", "I state that plainly" | Cut |
| Indirect claims: "That is the work I have done" | Say it directly |
| Hanging phrases: "this allowed", "which gave the hours back" pointing at nothing | Name the thing and what it did |
| Vague places: "in the room", "at the table" | Name the place, or build it in the sentence |
| Drawn-out constructions: "X is the part I", "it has taught me where" | Subject first, then the claim |
| Model marker words: delve, underscore, showcase, realm, pivotal, meticulous [S122]; tapestry, testament, navigate the complexities, ever-evolving (the skill's judgment) | Plain words |
| "Bridge the gap" | Name the connection and what it produced |
| A borrowed framework used as if native | The candidate's own description, or credit it |

Two things no script can see: **one sentence shape repeated down the page** (real careers produce uneven sentences), and **whether any competent writer could have written the line about anyone.** Read for both.

A clean scan is not proof a page reads as human. In the one blind test found, self-selected respondents spotted AI-written resumes at chance [S51], and HR workers name generic content as a top reason to reject a resume [S58]. Specific proof is the fix.

## Plain word or exact word

The plain word wins by default: use over utilize, start over commence, show over demonstrate.

The exception matters more than the rule. In licensed and technical fields the longer word is often the exact word, and often the search term: reconciliation, titration, remediation, arbitration, calibration, utilization (a billing metric), substantial completion (a contract milestone), statistically significant, comprehensive plan (a planning document), leveraged buyout. Those stay. The test is whether a simpler word means the same thing. `draft_review.py` passes these exact terms.

## Words the sentence already means

A word the sentence means without it gets cut. "Built the program" is complete, so "from scratch" goes; it sits in the tells table because models reach for it. `draft_review.py` fails the phrases that are always redundant and flags for review the ones that sometimes matter.

| Always cut | Write |
|---|---|
| each and every | every |
| end result, final outcome | result, outcome |
| past history, past experience | history, experience |
| future plans, advance planning | plans, planning |
| was able to cut | cut |
| collaborated together, merged together | collaborated, merged |
| new innovation | the innovation, by name |
| completely eliminated | eliminated |

| Usually cut | Keep it when |
|---|---|
| "own" after a possessive: "the hotel's own staff" | it means a separate one: "gave each region its own P&L" |
| personally | it separates the candidate's part from a team's, though "closed 12 of the team's 40 deals" says it better |
| successfully | the verb doesn't carry the outcome; "appealed" doesn't, and "won 11 of 14 appeals" says it better |
| actual | it is set against a budget, plan, or forecast |
| "new" after built, created, launched, or opened | it tells a new thing from an old one: "built a new plant to replace the 1970s one" |
| in order to, the fact that | rarely; "to" and "that" do the same work |

## Commas in lists

Pick one style for a list of three or more, with or without a comma before the last "and" or "or", and use it on every line. Style guides split on it, so it's the candidate's call (the skill's judgment). A candidate who wants the serial comma records it in the rulings file, and `draft_review.py --serial-comma` fails a clear list without it.

## When you are revising, not writing

Change a line only to fix a broken rule, prove a requirement, or aim at the target. Don't rewrite a line that works because you would have written it differently. A resume that sounds like the person is the asset. If a line is clean but flat, say so and leave it: that fix belongs to the candidate.

## Never on a resume

- Anything the candidate lacks, is learning, or wants to grow into. A resume argues one side; the gap is handled in the interview.
- Apologies, hedges about level, self-criticism.
- Salary, references, reasons for leaving. No "References available upon request" [S146].
- Lines with nothing to verify ("turns complexity into clarity"), in the summary or a bullet. The summary's pitch names the work, the people it served, and the places it happened.

## Read it out loud before it ships

1. Does it sound like a person describing their work?
2. Does every claim land on a number, a name, or a result?
3. Is there a line any competent writer could have written about anyone? Fix that one first.

## Spelling

Zero errors. In a test with 445 recruiters, two spelling errors cut a resume's interview odds by 7.3 points and five cut them by 18.5, and the penalty grew with how much the job asked for writing [S112]. The test used none, two or five errors, so the cost of one is unknown; zero is the target because a fix costs nothing. `scripts/spell_check.py` lists every word its dictionary doesn't know and every doubled word, and fails on them. Fix each one, or add the candidate's names and terms to the word list in the rulings file. It also flags real words often typed for others ("manger", "form" for "from", "lead" in a past-tense bullet) for a second read. Read the page once more for the rest.
