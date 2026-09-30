# The readers

What each reader does with a resume, what is known, and what is not. Every outside fact carries a source ID in square brackets; the source, its date, its grade and a quote are in `references/sources.md`. IDs starting with L are the skill's own live tests. Vendor features change fast: recheck a vendor row before quoting it to a candidate.

## 1. The application form

### Workday

- **What the parser fills.** Contact details, work experience (job title, company, location, dates, description), education and languages [S02]. Workday's older admin page says languages are not auto-filled [S01]; in the live tests one site added a language from a word in a bullet [L01]. Treat languages as varying by site.
- **Skills vary by employer.** Each Workday site handles the Skills box its own way: some leave it empty for the candidate to fill, and some suggest skills from the file [S02]. In the live tests, one Workday site left the box empty [L01] and another suggested 15 skills from the resume, two of them wrong ("Computer Programming", and "End-to-End Testing" from the words "end to end") [L02]. Check the Skills box on every application and remove anything wrong.
- **Format.** Workday says resumes without images parse best, and that parsing "can vary based on resume format and order of words" [S01].
- **The candidate edits the form** before submitting, and the employer decides which sections it shows. Earlier applications and the candidate's profile can preload the form at the same employer [S03, S04].
- **Some Workday upload pages tell applicants to put skills inside the job descriptions.** A candidate saw this on a live site in 2026. It is not in Workday's public docs, so treat it as that employer's instruction, not Workday's rule.
- **Not known:** whether a Workday recruiter's search reads the attached file or only the fields.

### What the live Workday uploads showed (2026-09-28)

One real resume went to a live Workday application ("Autofill with Resume") six times in different layouts, and every field was read back [L01]. Nothing was submitted.

- The first upload, in the title-first layout this skill used before v2.0, filled 8 of 8 roles but got only 2 fully right. Causes: a company line with no city; a comma inside a job title (Workday kept only the text before the comma); two roles in a row with no bullets; and the title line fusing into the company field.
- With a city and a bullet on every role, title-first still glued three titles to their companies. A one-line "Title | Company | City, ST | dates" layout did the same.
- **Company first worked:** a bold "Company, City, ST" line, then "Title | Mon YYYY – Mon YYYY". All 8 companies, cities and dates were right.
- **Workday keeps only the text before a comma or an opening parenthesis in a title,** in every layout. Written descriptor first with no punctuation ("Supply Chain Senior Analyst"), the whole title came back: 8 of 8 titles, companies, cities and dates right.
- A one-line "Earlier career: ..." sentence at the end of Experience folded into the last role's description. It did not create a false role.
- Education filled correctly every time from "Degree, Field | Institution | Year".
- Every upload added **Polish** as a language, from the word "polish" in a bullet. The Skills box stayed empty. The Websites section stayed empty although the LinkedIn URL was on the contact line.

On a second Workday site, the company-first file filled 31 of 32 role fields [L02]. The one blank company sat under a job whose last bullet ended on an award name and a city; with that bullet moved up, all 32 filled.

These are two sites and one resume. They set this skill's role order (`references/document.md`). In both tests the title line was plain; since v2.1 the title is bold as well (section 3). That change is formatting only, and the post-upload review catches any field it moves. `build_resume.py --plain-title` rebuilds the tested look, and `--layout` keeps the other two layouts for a re-test.

### Other systems

- **Greenhouse** fills fields from resumes a recruiter imports. Columns, tables, headers, footers, text boxes and graphics cause misses, files over 2.5 MB don't parse, and so do "resumes without clear sections" [S14]. On the one Greenhouse application form tested, there were no work-history fields and nothing filled from the file [L04].
- **Lever** searches parsed resume content plus company, school and title fields [S24]. Its resume parser is Textkernel [S88]. In a live test, Lever refused the six-part DOCX that `build_resume.py` 2.0.1 wrote, with an HTTP 422 error, which in Textkernel's API means the file could not be converted to text [S89]. The same text saved with the full set of parts Word writes parsed, with name, email, phone, city, LinkedIn and current company right [L04]. The file standard needs only the main part [S90], but Word writes document properties in every file [S91], and this parser was stricter than the standard [L04]. Since v2.1 the build writes the full set, and `parse_check.py` warns on a file without it.
- **Textkernel reaches past Lever.** It lists integrations with SAP SuccessFactors, Oracle Recruiting Cloud and SmartRecruiters [S100]. Which parser a given employer runs is not public, so a file that fails Textkernel may fail in more places than Lever.
- **Paycom** parses a resume to pre-fill the form [S32].
- **Rippling Recruiting** (ats.rippling.com) fills candidate information from an uploaded resume, in English and other languages. Rippling doesn't say which fields [S108].
- **HiringThing** runs job sites under its partners' names and web addresses [S102]. Rippling ATS, on rippling-ats.com, is one of them: HiringThing's partners sell it under that name [S103], and every board checked says "Powered by HiringThing" [L06]. It is a different product from Rippling Recruiting, so Rippling's facts don't apply to it. HiringThing parses a resume into the recruiter's view of the applicant; no HiringThing page says the application form fills from it [S105].
- **Eightfold:** on the one application tested, the form filled only first name, last name and email from the file, then went to Submit [L03]. No work-history, education or skills form: the file is the whole application.
- **Chat applications.** Some employers now take the application as a chat: Eightfold's Candidate Agent, which reads the resume inside the chat [S13], and Workday's Paradox, mainly for frontline roles [S09]. Answer a chat's questions as carefully as screening questions (section 6).
- **Front ends are not applicant systems.** Jibe (owned by iCIMS since 2019) [S33], Radancy TalentBrew and DirectEmployers `.jobs` sites sit in front of the real system; the last two were seen that way on live career sites. `detect_ats.py` says when it sees one.

### How much each system matters

In the 17,280 applications Huntr's users could trace to a system in April to June 2026: Greenhouse 23%, Workday 20%, Ashby 16%, Lever 6%, Workable 3%, SmartRecruiters 3% [S61]. Workday and SAP SuccessFactors run 52% of the Fortune 500 [S99]. Huntr's users lean toward tech, and it undercounts systems that sit behind an employer's own web address. Plan for Workday at large employers and Greenhouse, Ashby and Lever at tech and growth companies.

## 2. The AI grader

Nearly every major system now sells an AI layer that reads the resume against the posting and grades, labels or ranks candidates. It is almost always something the employer buys or turns on. **No source says what share of employers turn it on.** Two of eight postings in the skill's 2026 test said outright that they use AI screening, both with an opt-out [L05].

| System | What it outputs | On by default? | Source |
|---|---|---|---|
| Workday HiredScore | Grade A to D. A: all required qualifications, most preferred, match above a threshold. B: all required. C: most but not all required. D: does not meet most required. | Sold as its own product | [S05, S06, S79] |
| Workday Candidate Skills Match | Skills match score from skills on the application vs the requisition. Workday plans to retire it. | Employer sets it up | [S07] |
| Eightfold | Match score 0 to 5 from titles, work history, education, skills and resume text; recent skills weigh more | Core to the product | [S10, S11] |
| Greenhouse Talent Matching | Strong, Good, Partial or Limited match; "Needs manual review" for applicants who opt out. Scores only extracted data: skills (taken from anywhere in the resume), years, titles, dates, companies and a derived industry. More matched terms don't always raise the score. | Part of the Real Talent add-on | [S15, S16, S17, S18] |
| Lever Talent Fit | Ranks candidates against job requirements | Built in on current plans, turned on per account and per job | [S21, S22, S23] |
| Ashby AI-assisted review | Meets, does not meet or undecided per employer criterion; sorts by share met | An admin turns it on | [S25, S26] |
| Oracle Recruiting | Four 0-to-5 ratings: education, experience, skills, profile | Opt-in | [S27] |
| SmartRecruiters (SAP) | Very high, high, medium or low match from skills, experience, education and title | Not stated | [S40, S41] |
| iCIMS | Ranks candidates on skills and experience | Not stated | [S34] |
| ADP Profile Relevance | Excellent, good, fair or low match from experience, role history and skills; no cut-off; opt-out per job | Not stated | [S29] |
| LinkedIn Hiring Assistant | For each qualification, whether evidence was found, citing where; grades applicants from LinkedIn and from the employer's own system | Add-on to LinkedIn Recruiter | [S30, S31] |
| Rippling Recruiting | Application Review screens applicants against criteria the employer defines and surfaces the top candidates | Admins turn AI features on or off; default not stated | [S37, S109, S110] |
| HiringThing (also sold as Rippling ATS) | Scores every applicant against the job description and ranks a shortlist; the team can adjust the criteria and their weights | Available to all partners and their clients since 2026-06; admins can turn the AI features off for their account | [S106, S107] |

**What this changes for the resume.**

- **Prove every required qualification that is true, in a plain line, inside the role where it happened.** HiredScore's B grade needs every required qualification met [S05], and LinkedIn's and Ashby's graders look for evidence per qualification [S31, S25]. Frontier LLM graders picked the more qualified resume 98 to 99% of the time when three qualifications differed, and 82 to 93% when only one did [S45]. So a single unproven requirement is exactly where a grade drops.
- **A tool in a list is not proof.** Two parsers (Textkernel, Affinda) tie each skill to the job it appears in and date it from that job [S43, S92, S94], and Eightfold's recent-skill signal uses only skills from recent jobs [S11]. In the skill's own test, stand-in AI graders did not credit a required tool that sat only in a skills list [L05]. Field matchers do pick up a listed skill [S16], and recruiter search needs the exact term [S20], which is why a short Skills line still earns its place (`references/document.md`, Skills).
- **Nothing lives only in the summary,** except a career total the candidate confirmed (`references/writing.md`, The summary). LLM graders read the summary. Field matchers such as Greenhouse's score only extracted skills, titles, dates, companies and years [S16], so a claim that lives only in summary prose may not count there. About a third of the evidence the stand-in graders cited came from summaries [L05], so the summary carries the posting's title language and its top proof, stated again, in full, in the role.
- **Parse clean.** Extraction noise was the change that most often flipped a small LLM grader's decisions: 47% for one model [S46].
- **Don't tune to one model.** The same resume got a different verdict on 17 of 51 required items across three grader runs [L05]. Borderline cases flip between runs and procedures [S47]. Only a clear match is stable.
- **Don't try to sound like a chatbot.** An LLM grader preferred summaries written by the same model over human-written ones 67 to 82% of the time, and preferences between different models were mixed [S48]. You can't know which model grades you, and HR workers name generic content as a top reason to reject a resume [S58]. Clear, specific sentences serve both.

**Opt-outs and notices.** New York City's Local Law 144 requires a bias audit and notice to candidates, enforced since 2023-07-05 [S69]. Illinois requires notice when AI is used in hiring, in force 2026-01-01, with no opt-out; the state postponed its notice rules on 2026-06-02 and the law still applies [S70, S71]. California's privacy rules add a pre-use notice and access rights from 2027-01-01 for tools that replace or substantially replace human decisions; the opt-out doesn't apply if the employer offers a human appeal that can overturn the decision, or uses the tool only for hiring and it works without discriminating [S72, S73, S74]. California's civil-rights rules, in force since 2025-10-01, make discrimination through automated screening unlawful and require four years of records, with no notice or opt-out right [S75]. Colorado's SB 26-189, signed 2026-05-14 and effective 2027-01-01, adds a plain-language explanation within 30 days of an adverse decision, a right to correct data, and human review where commercially reasonable; there is no opt-out, and enforcement is on hold during a federal lawsuit [S76, S77, S78]. On Greenhouse an applicant who opts out is labeled "Needs manual review" and not scored [S16]; on ADP the score shows "Not Available" for that job [S29]. **No source shows whether opting out helps or hurts.** It is the candidate's call; give them these facts.

## 3. The recruiter

- **The first look is a keep-or-drop call, fast.** Vendor eye-tracking put it at about 6 seconds [S52] and 7.4 seconds [S53]. Recruiters report 10 seconds to a minute [S55]. Don't design around a precise number.
- **Eyes go first to titles, employers, dates and education** [S52]. Top-rated resumes had "bold job titles supported by bulleted lists of accomplishments", clear headings and white space; clutter, columns and long sentences hurt [S53]. That is why each role's company line and its job title are both bold: the company-first order comes from the Workday tests [L01, L02], and the bold title comes from this study.
- **Title match matters.** Resumes whose title matched the posting's went with far higher interview rates in one vendor's self-tracked data [S60] (correlational). Put the posting's title language in the summary's first sentence; never change a past title to match.
- **Many recruiters use AI to summarize resumes.** Of hiring managers who use AI, 37% use it to summarize resumes [S59]. In the skill's test, chatbot reads took their "strongest proof" from role bullets on 8 of 8 resumes [L05].
- **Recruiter search needs the exact term.** Greenhouse's search over stored applicants matches the exact keyword [S20]; Lever searches all parsed resume text [S24].

## 4. The hiring manager

- **Results over duties; quantify where you can; use scope where you can't.** The guides agree [S62, S63, S64]. "No measurable achievements" is a red flag for 44% of hiring managers in one vendor survey [S57].
- **Generic, templated text is what gets punished.** In one vendor survey of HR workers, 36% named generic content as a top reason to reject a resume, and 53% disliked templated messages with no relevance to the role [S58]. In the one blind test found, self-selected respondents spotted AI-written resumes at chance [S51]. A resume with no tell words can still read as generic; the fix is specific proof.
- **Clean writing pays.** Writing help raised hires 8% with no drop in employer satisfaction in a field experiment with about 481,000 job seekers, before generative AI [S50].

## 5. The record check

After the resume come checks against the record, and they compare titles and dates.

- **Background checks verify titles and dates** and note differences from what the candidate gave [S81, S82]. The Work Number returns the job title from the employer's payroll [S83].
- **Fraud screens check identity and work history:** Greenhouse's Real Talent checks identity and flags fraud signals [S18]; Lever flags work-history consistency, without saying what it compares against [S86]; LinkedIn now lets colleagues vouch for work history and employers remove false claims [S87]. Keeping LinkedIn and the resume consistent is the skill's judgment: both are in front of the same employer.
- **What gets compared** is what the candidate types into the application's title field and the background-check company's form, against the employer's record.
- **A title with the same words in a new order** ("Director, Creative Strategy" written "Creative Strategy Director") keeps every word of the formal title at the same level. Low risk: no source treats a reorder as a discrepancy, though none clears it either.
- **A title with a word the employer never used** ("Senior Associate" written "Brand Strategy Senior Associate") will come back from a verification as the formal title, and the difference may be noted. Medium risk unless handled.
- **How to handle both:** type the formal title, exactly as held, into the form's title field and any background-check form. Keep LinkedIn consistent with the resume (`scripts/profile_check.py`). If a report flags the title anyway, the candidate explains it during the notice the employer must give before acting on the report [S84]; the screening company keeps reporting what the employer confirmed, so the explanation goes to the employer [S85].

## 6. Knockout questions

Screening questions can end an application where the employer has set them up. Workday can auto-decline on questionnaire answers at a step the employer picks [S08]. Taleo can exit a candidate on a disqualifying answer [S28]. They are not always on and don't always run first, but the candidate can't see which ones are knockouts.

Tell the candidate: answer every screening question accurately and slowly. Count years of experience from the real dates and count everything that truly applies. A work-authorization or travel question is a question for them, not a resume line.

## 7. The post-upload review

Required on every application that autofills a form. The candidate reviews every field and fixes it before submitting.

For each role:
- [ ] Job title whole (not cut at a comma or parenthesis). Where the resume title differs from the formal title (reordered, or with a descriptor the candidate added), type the formal title here, exactly as held.
- [ ] Company name alone (no title glued to it)
- [ ] City and state
- [ ] Start and end dates; current role marked current
- [ ] A description present

Tip: if a company comes back blank, look at the last bullet of the job above it, and move that bullet up or reword its end. In one live test, a bullet ending on an award name and a city made Workday drop the next company; with the bullets reordered, every field filled [L02]. One case, so it's a tip, not a rule.

Then:
- [ ] Education: school, degree, field
- [ ] Languages: delete any the candidate does not speak. Workday read "polish" in a bullet as the language Polish [L01]; words like "Java", "Swift" or "Ruby" may trip it the same way (untested).
- [ ] Skills: check this box every time; each Workday site handles it its own way [S02, L02]. Remove anything wrong, then type the posting's required skills that are true, in the posting's words.
- [ ] Websites: add the LinkedIn URL. It did not fill from the contact line in the live tests [L01, L02].
- [ ] Certifications and any other optional field the candidate can truthfully fill
- [ ] Contact fields
- [ ] Any background-check form later on: titles exactly as held, dates as on the resume.

**Eightfold, chat applications and systems with no form:** there is nothing to fix after upload. Run every check in SKILL.md before sending.

## 8. What nobody knows yet

- How many employers turn AI grading on, and whether any filter on the grade.
- Whether Workday recruiters search the attached file's text.
- How iCIMS, SuccessFactors and Taleo parse today. SAP's help pages refused fetches, no public iCIMS parsing doc was found, and Taleo's public docs date from 2021 [S28].
- Whether exact posting wording beats a close synonym for an LLM grader. No public test.
- Whether an AI grader gives less credit to a skill that is only listed. The mechanism points that way [S11, S43]; no study isolates it.
- Which missing part made Lever refuse the six-part file [L04]. The full set fixes it; the single cause was not isolated.
- What Rippling Recruiting's and HiringThing's application forms fill from a resume. No live upload has been done on either.
