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

- **Verbs.** Past tense for finished work; present tense for ongoing work in the current role. Plain verbs: led, built, ran, launched, cut, grew, won, wrote, designed, opened, hired, fixed. Never open with "Responsible for", "Duties included", "Helped with", "Worked on".
- **Implied first person.** No "I", "my", "we" or "our" anywhere on the page, and never "he" or "she" [S66, S67].
- **One to two rendered lines.** Two lines is the guide [S62]; about 25 words is this skill's working figure. The rule is two lines on the render, which `widow_check.py` measures. A third line is setup the reader doesn't need: keep the result, cut the context.
- **No line ends on one or two words alone.** Fix it by changing words until the line count changes, never with a manual break, a non-breaking space or a spacing tweak.
- **New evidence strengthens a line; it doesn't multiply lines.** Put the new fact into the bullet it proves.
- **The first bullet of a role is its strongest proof for this target,** not its main duty. The duty is what the reader already assumes from the title.
- **Name what you count.** A count of named things names them all or drops the number: "three clinics, including Eastside and Riverview" reads as if the writer couldn't name the third. A count of abstract things (decisions, directives, priorities, themes, recommendations, principles, pillars, goals, needs, initiatives, tools and the like) names the set: what it was about or for. It doesn't need every item. "Settled seven decisions" names nothing; "settled seven decisions on pricing and the launch date" does. The name has to be specific to the work: "seven key decisions" and "seven strategic decisions" still name nothing, and so does an owner alone ("five priorities for the district"). If the evidence can't name the set, drop the count. A count of concrete things (stores, employees, interviews, survey responses) is scope, and it stands as it is. `draft_review.py` fails a count that names nothing, and flags a count for review when the words after it may only say whose set it was.
- **A label is not content.** "Key insights", "strategic recommendations" and "the findings" stand in for something the reader never gets. Say what they were, or what they were about: "insights on churn". "The findings" can stay when the same line names the work they came from and what they became. `draft_review.py` fails a label built on a generic word ("key", "strategic", "actionable") with nothing behind it.
- **A page count is not a result.** "A 60-slide deck" measures the document. Use the figure the work was about (units, sites, people, dollars), or say that it got built.
- **Claim the layer you worked at.** On work several disciplines delivered, name the part that was the candidate's. The narrower claim is usually the more senior one, and it survives a reference check.
- **A status tag pinned to the end is not a result** ("now built", "since acquired"). Put it in the grammar or cut it.
- **Tools go inside the bullet where they were used.** "Rebuilt the preventive maintenance schedule in Fiix" proves the tool; "Fiix" on a list does not. Put the tool in the bullet for the work it was used on. If that work is true but missing from the page, write the bullet for the work; never write a bullet only to hold a tool name.
- **Vary the metric type.** A page where every bullet ends in a percentage reads as templated. Mix counts, dollars, time, rankings and adoption.

## Numbers

Every number traces to a line in the candidate's evidence or to an answer they gave. An "about" in the candidate's own writing is their wording; keep their hedge. The test for every number: **can the candidate defend it cold in an interview?** Where it came from, how it was measured, the baseline, what they did to move it.

- **Missing number:** write the bullet with scope or a named specific instead, and put the question in the brief. Never a working marker in the file; `build_resume.py` refuses them.
- **Real beats round.** "Cut the close from 11 days to 4" beats "cut close time about 65%".
- **For design, planning and product work, the result is often whether the thing exists.** Did it get built, did it open, who runs it now. Ask: candidates rarely volunteer it. Keep the causal claim honest.
- **No number at all:** scope works. Team size, client count, budget, markets, volume.
- **Numbers people forget they have:** team size and reports, budget owned, clients or sites or products, time against plan, volume per week, before and after on any metric, share of a total.

## When the client can't be named

Work down this ladder and stop at the first rung that is allowed:

1. **Named client, named work, result:** "Rebuilt the loyalty program for Harbor Grocers; enrollment up 31% in eight months."
2. **Named approach, sector, scale, result:** "Designed a three-stage intake process now used by five county clinics."
3. **Client type, scale, result:** "Top-three regional grocery chain: repositioned the store brand for two new markets." Last resort; use it for one or two bullets at most.

Never write around a restriction in a way that implies more access than the candidate had. The result is almost never the confidential part.

## The summary

A prose paragraph: three to four lines, about 50 to 70 words, no bullets. Stanford GSB says "Limit the summary to 4 lines plus bullet points" [S62]; Yale says fifty words or fewer [S63]. This skill keeps the four lines and drops the bullets: no study tests prose against bullets, and bullets under the summary repeated the roles below them in every resume of the skill's 2026 test [L05]. The one outcome dataset found no reliable interview effect from having a summary at all [S98], so keep it short and never let a claim live only there.

**What goes in it, in this order:**

1. **The title language of the target, years and domain, in one sentence.** "Operations director with 12 years running distribution for food and consumer-goods companies." For a tailored resume, use the posting's title words where they are honest; title match went with higher interview rates in one vendor's data [S60]. AI graders read the summary (`references/readers.md`). The years count the whole career: this year minus the year the career started (for most people, the year they finished school). The words beside that number have to fit the whole career too. A posting's "N years in X" is a different count, from only the jobs that did X (`references/tailoring.md`).
2. **The proof that answers the posting's top requirement,** with its number and its name, in a full sentence. The role states it in full; the summary states it shorter, as the headline, in new words. Change it per posting. On a base resume, it answers the requirement most postings in the family share (`references/tailoring.md`).
3. **What is true across the whole career,** not any one role: the kinds of places, the pattern of the work, or the employers themselves ("Ran distribution for three regional grocers: Harbor Foods, Valley Fresh and Ridge Market", each one a role below). No second role-level result. A career total the candidate confirmed fits here (see the rules below).
4. **One sentence of belief, in the candidate's own words, without "I".** No source tests it either way; it is here so the page sounds like a person, and the candidate decides whether to keep it. Write it as a plain statement: "The night-shift technician knows the machine better than the manual does." Ask the candidate for it once, write it in the rulings file, and use their wording. If they can't be asked this session, leave it out and ask in the brief; never write one for them. A summary of only numbers reads like a machine wrote it.

**Rules:**

- Full sentences. No colon lists, no "Specialties:" line, no keyword strip at the end.
- Implied first person: verbs with no subject ("Led", "Ran"), never "I", never third-person verbs ("Leads", "Has", "Believes"), never "A results-driven professional who". The opening title phrase ("Registered nurse with 9 years...") is the one sentence without a verb.
- Every count names what it counts ("three hospitals: Mercy, St. Luke's and County General") or drops the number.
- **The summary says in simpler form what the bullets below prove.** Every claim in it has a job behind it: every number, client and credential also appears in the role or section that holds it, because the form has no summary field [S02], field matchers score only extracted skills, titles, dates, companies and years [S16], and AI graders look for the proof inside the job [S05, S31]. Repeating what the roles prove is the summary's job.
- **Never copy a bullet word for word.** Restate the claim shorter and at a higher level. The role keeps the full wording.
- **One exception: a career total the candidate confirmed.** A total that spans several jobs (workshops run, stores opened, new nurses trained) may sit in the summary with no single job behind it, once the candidate confirms the number. Record it (the rulings file, or the facts file if the candidate keeps one) and list it under `career_totals` in the JSON source (`references/document.md`) so `draft_review.py` passes it. A total the candidate hasn't confirmed is an estimate (SKILL.md, hard rule 2).

**Examples** (different fields, same shape):

> Registered nurse with 9 years in emergency and critical care, most recently as charge nurse in a Level II trauma center. Led the sepsis bundle rollout at Mercy West that moved compliance from 54% to 91%. Worked charge shifts in the emergency departments at Mercy West and County General. A calm handoff saves more time than a fast one.

> Logistics manager with 11 years running regional distribution for grocery and consumer goods. Cut cost per case 18% in two years at a 220,000 sq ft site with 90 associates across three shifts. Ran distribution for three regional grocers: Harbor Foods, Valley Fresh and Ridge Market. The floor team finds the waste before the report does.

`draft_review.py` fails a bullet under Summary, a keyword strip, a first-person pronoun, and a figure or name found only in the summary, unless it is a listed career total. It asks you to re-read a summary outside 45 to 75 words, any count that names fewer items than it claims, and any summary sentence that copies a bullet word for word.

## AI-writing tells

A page can clear every rule and still read as generated. These are the general tells. The list is the skill's judgment: no survey with a stated sample ties these exact words to rejection, but HR workers do name generic content as a top reason to reject a resume [S58]. `draft_review.py` checks all of them: it fails the near-certain ones and flags the rest for a second read.

| Tell | Instead |
|---|---|
| Em dash for emphasis or drama; "--" as a dash | A period, colon or comma |
| "Not just X, but Y"; "X, not just Y"; "isn't just X; it's Y"; "not only X but Y" | Say Y |
| "It's not about X, it's about Y" | Say what it is |
| "I am not an X. I am the person who..." | State the capability in its own terms |
| A vague weaker group to stand above: "unlike most", "a rare blend of", "few can" | Delete the first half. A named competitor or a measured baseline is a real comparison and stays |
| Throat-clearing openers: "In today's fast-moving market" | Start with the point |
| Hedges: very, really, quite, rather, fairly, somewhat, a bit, kind of | Cut them |
| Filler: actually, just, simply, literally, basically; sincerity words: honestly, genuinely | Cut them |
| Vague size words: significant, robust, comprehensive, powerful, seamless, impactful, high-impact, substantial, extensive | The figure they stand in for |
| Fluff verbs: leverage, unlock, drive, empower, elevate, streamline, foster, spearhead, orchestrate | A plain verb with an object |
| Weak claims: contributed to, was involved in, played a role in, helped to, can help, may be able to | Say what the candidate did |
| Latinate defaults: utilize, commence, endeavor | Use, start, try |
| Cliches: results-driven, proven track record, passionate about, seasoned, dynamic, team player, go-getter, thought leader, world-class, best-in-class, cutting-edge, holistic, synergy, detail-oriented, self-starter | The evidence the cliche claims |
| "From scratch" | "Built the program" is complete |
| Ending on air: "driving operational excellence", "delivering transformational value" | End on something a reader could check, or end the sentence a clause earlier |
| Everything in threes for rhythm: "faster, simpler, smarter" | Keep the one that is proven |
| "Whether you're X or Y" setups | Cut |
| Urgency codas and meta-statements: "ready to bring this energy", "I state that plainly" | Cut |
| Indirect claims: "That is the work I have done" | Say it directly |
| Hanging phrases: "this allowed", "which gave the hours back" pointing at nothing | Name the thing and what it did |
| Vague places: "in the room", "at the table" | Name the place, or build it in the sentence |
| Drawn-out constructions: "X is the part I", "it has taught me where" | Subject first, then the claim |
| Model marker words: delve, underscore, showcase, tapestry, testament, realm, pivotal, meticulous, navigate the complexities, ever-evolving | Plain words |
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
| actual | it is set against a budget, plan or forecast |
| "new" after built, created, launched or opened | it tells a new thing from an old one: "built a new plant to replace the 1970s one" |
| in order to, the fact that | rarely; "to" and "that" do the same work |

## When you are revising, not writing

Change a line only to fix a broken rule, prove a requirement, or aim at the target. Don't rewrite a line that works because you would have written it differently. A resume that sounds like the person is the asset. If a line is clean but flat, say so and leave it: that fix belongs to the candidate.

## Never on a resume

- Anything the candidate lacks, is learning, or wants to grow into. A resume argues one side; the gap is handled in the interview.
- Apologies, hedges about level, self-criticism.
- Salary, references, reasons for leaving.
- Positioning lines with nothing to verify ("I turn complexity into clarity") as bullets. The one belief sentence in the summary is the exception, and it is the candidate's own words.

## Read it out loud before it ships

1. Does it sound like a person describing their work?
2. Does every claim land on a number, a name or a result?
3. Is there a line any competent writer could have written about anyone? Fix that one first.
