# The document

What goes on the page, in what order, in what shape. How each line is written is in `references/writing.md`. Why the readers behave as they do is in `references/readers.md`. Source IDs in square brackets point to `references/sources.md`.

## Sections and order

1. Contact block (name, optional headline, contact line)
2. Summary
3. Experience
4. Education
5. Certifications (only if the candidate has any)
6. Skills (one line, whenever the candidate has concrete tools, software, methods or languages to list)

One resume, every reader. This outline is the one that serves parsers, AI graders, recruiters and hiring managers at once, and the evidence behind each choice is below.

- **Experience before Education** for anyone more than about a year out of school. The alumni and MBA guides lead with experience [S62, S68]. Textkernel needs both sections to exist and treats a missing one as fatal [S44]; no parser documents a required order. The one outcome dataset found no reliable difference between the two orders [S98].
- **No Accomplishments, Highlights or Key Achievements section.** Textkernel files such a section as a flat list outside the jobs, with no employer and no dates [S93]; skills get their dates from the job they sit in [S92, S94]; Workday's form has no field for them [S02]; and graders that weigh recency or check evidence per qualification need the claim tied to a job [S11, S05, S25]. Each achievement goes in the bullet of the job that produced it. The case for a separate section is editorial opinion [S97].
- **Skills last, one line.** The guides that place skills put them at the end: Harvard's template ends with skills and interests, and Yale and Kellogg end with an Additional section [S66, S63, S68]. The first look goes to titles, employers and dates [S52]. No source tests top against bottom. The line holds the posting's exact terms for search [S20, S24] and minor tools; the proof stays in the bullets (Skills, below).
- **A summary, short.** People and LLM graders read it; field matchers score only the skills, titles, dates, companies and years they extract [S16]; the one outcome dataset found no reliable interview effect either way [S98]. It costs four lines, so keep it, keep it short, and never let a claim live only there (`references/writing.md`, The summary).

These five headers and no others: **Summary, Experience, Education, Certifications, Skills,** each on its own line. Parsers find sections by their headers: Textkernel flags a section with no header, a header not on its own line, and nonstandard headers [S44]; Greenhouse fails "resumes without clear sections" [S14]; RChilli says one section per topic [S95]; and the career centers ask for standard titles [S96]. No vendor publishes its list of header names, so the standard words are the low-risk choice. An invented header ("Where I've Made a Dent", "Key Accomplishments", "Methodology") risks the parser putting that content in the wrong place, and a person looks for the standard words. Read any header on the way in; write these on the way out. `build_resume.py` refuses anything else.

Move Certifications above Experience when the field gates on a license: nursing, trades, transportation, accounting, security clearance. Move Education above Experience only for students and graduates within about a year. Never reorder to hide something. (These moves are the skill's judgment; no source tests them.)

## Contact block

First lines of the body, never in the page header or footer. Textkernel treats contact details anywhere but the top as a major issue [S44], and Greenhouse and RChilli miss contact details in a header, footer or text box [S14, S95].

```
Firstname Lastname
Optional headline: what the candidate does, for whom
City, ST | (555) 555-0134 | name@example.com | linkedin.com/in/handle
```

- The contact line is a fact only the candidate has. Ask for it at intake. A file with no phone fails `parse_check.py`.
- City and state only. No photo or age [S66], and no street address, birth date or marital status on a US resume (the skill's judgment).
- One phone, one email the candidate reads. A personal email is the safe default.
- LinkedIn as plain text. Workday did not fill the Websites field from it in the live tests; the post-upload review adds it by hand [L01, L02].
- One contact line works. RChilli advises against contact details on one or two lines [S95], but Workday filled name, phone, email and city from the one line [L01], and Lever's parser read every item on it [L04].
- The **headline** is optional. It describes the work and the field in plain words. Never a job title the candidate does not hold, never a row of keywords. The posting's title language goes in the summary's first sentence instead.

## Summary

A prose paragraph under the Summary header: three to four lines, about 50 to 70 words, no bullets. What goes in it and how it's written is in `references/writing.md`, The summary. `build_resume.py` refuses a bullet under Summary.

## Experience

### Role layout

Company first. This is the layout that filled every field right in the first live Workday test [L01], and 31 of 32 on a second site [L02]:

```
Company Name, City, ST                       (bold)
Job Title | Mon YYYY – Mon YYYY              (title bold, dates plain)
- Bullet
- Bullet
```

The company-first order comes from the Workday tests. The bold title comes from recruiter eye-tracking: top-rated resumes had bold job titles [S53]. The Workday tests ran with the title plain; the change is formatting only, the text is the same, and the post-upload review catches any field it moves. `build_resume.py --plain-title` rebuilds the tested look.

- **Every role gets a city and state.** A company line without a city broke a whole Workday entry. Use the office the candidate worked from; for a remote job, the candidate's own city. Never a state alone and never "Remote" alone. If the city is not in the material, ask.
- **Dates:** three-letter month and four-digit year, an en dash with a space each side, "Present" for the current role: `Mar 2018 – Present`. One format across the document. "Sep", not "Sept".
- **Promotions inside one company:** one role block per title, each with the same company line and its own dates. The newer role's first bullet can open "Promoted from ...". (Not yet live-tested.)
- **Concurrent roles:** both, with their real overlapping dates. Never adjust dates to hide an overlap.
- **Contract, consulting and agency work:** the employer or the candidate's own practice is the entry; clients are named inside the bullets. When the work came through a partner firm, name the firm that hired the candidate as the client, and name the end client only when the candidate says it is allowed.
- **More than one venture of the candidate's own:** ask which one carries the target's work. The answer goes in the rulings file.

### Titles

- **The candidate's real title.** Never change a past title to match a posting.
- **No comma and no parenthesis in a title.** Workday keeps only the text before either one [L01]. A title with a qualifier is written descriptor first, positional word after, with no punctuation and the same words: "Senior Analyst, Supply Chain" becomes "Supply Chain Senior Analyst"; "Nurse Manager, Cardiac ICU" becomes "Cardiac ICU Nurse Manager". This moves words that are already in the formal title. It adds none.
- **A word the employer never used** (a discipline added to a generic title, such as "Brand Strategy Senior Associate" for a formal "Senior Associate") is the candidate's call. Name the risk when asking: a background check returns the formal title and may note the difference [S81, S83]. Reorders are low risk; an added word is medium risk unless handled (`references/readers.md`, The record check).
- **Either way, the formal title goes into the forms.** In the post-upload review and on any background-check form, the candidate types the title exactly as held. The resume keeps the version the candidate approved.
- Ask about titles once, name the risk, and record the answer in the rulings file. A candidate who wants the exact punctuation keeps it: build with `--keep-title-punctuation` and fix the field by hand on every form.
- **Company names:** no comma, because the company line splits on commas. Keep a legal suffix when it's part of the name, written without the comma ("Acme Inc."): parsers recognize a company more reliably with it, and Greenhouse lists missing suffixes among its parse-failure causes [S95, S14].
- An internal title the market won't recognize ("Growth Ninja") stays as the title. The standard title language goes in the summary and in the role's first bullet. Adding it to the title itself is the candidate's call.

### Bullets

- **Every role in the last 15 years gets at least one bullet,** measured from the role's end date. Two empty roles in a row shifted a title onto the wrong Workday entry [L01], and a role with nothing under it reads as a job the candidate could not describe (the skill's judgment). `build_resume.py` refuses an empty recent role.
- **Three to four bullets for recent roles is the guide norm** [S62], fewer for older ones. Beyond that, evidence decides: rank every claim by how strongly it proves the target's requirements, then fill the page from the top of that ranking. Target relevance beats size; recency breaks ties.
- **Each role opens with its strongest proof for this target.** The first bullet of a role gets read; the fourth may not.
- One to two rendered lines per bullet (`references/writing.md`).

### Roles older than 15 years

One line at the end of Experience, as an `earlier` block. Stanford puts roles older than 15 to 20 years in a separate short section [S62], and Textkernel flags old work history [S44]:

```
Earlier career: Line Operator at Maumee Molding in Maumee, OH, 2004 to 2010.
```

Years written "2004 to 2010", not with a dash, so the line is not read as a second date format. Several old roles go in the same sentence. In the live test this line folded into the last role's description and created no false entry [L01].

An older role keeps a full entry with bullets only when it proves a required qualification that no newer role proves. The candidate may leave pre-15-year roles off entirely, as long as the last 15 years show no unexplained gap.

## Education

```
Degree, Field | Institution | Year
```

- One line per institution. Everything earned there on that line: degree first, then certificates, minors, honors, separated by semicolons. `Bachelor of Arts, Communication; Certificate in Public Relations | Example State University | 2012`. This shape parsed correctly in every live Workday upload [L01, L02].
- State every credential in full. Abbreviating someone's education deletes part of it.
- Keep the graduation year by default; Workday filled it correctly in the live tests [L01]. The candidate may drop it for a degree more than 20 years old [S67]; Stanford ties the same advice to age, over 50 [S62], and Textkernel's parser advice is to leave education dates off [S44]. It's the candidate's call.
- An unfinished degree: `Coursework toward BS, Mechanical Engineering | Example University | 2015 to 2017`. Never imply completion.
- GPA only for recent graduates, and only if strong.

## Certifications

```
Certification Name | Issuing Body | Year
```

License number and state where the field expects them (nursing, engineering, real estate, insurance). Expired ones come off or are marked expired. An exam already scheduled can be listed as `in progress, exam scheduled March 2027`; this is the only place a not-yet-held credential appears.

## Skills

Include it whenever the candidate has concrete tools, software, methods or languages to list; leave it off when there is nothing concrete. One line under the Skills header, at the end, items separated by commas: tools, software, methods and languages with a real level ("Spanish (professional working)"). `build_resume.py` refuses a second line. If the line ends on one or two words alone, reorder the items rather than dropping a true one.

- **The proof lives in the bullets.** Every tool the posting requires, and the candidate used, goes inside the bullet where it was used (`references/writing.md`, Bullets). Two parsers (Textkernel, Affinda) date a skill from the job it sits in [S92, S94], Textkernel's advice is to show skills "in the context of work history" [S44], and in the skill's own test stand-in AI graders did not credit a tool that sat only in a list [L05].
- **The line is for search and minor tools.** Recruiter search needs the exact term [S20, S24], field matchers pick up listed skills [S16], and HiredScore's talent search filters on skills [S101]. That is the line's job; it is never the proof.
- **Short.** More matched terms don't always raise a match score [S17], and keyword stuffing marked the worst-rated resumes in eye-tracking [S53].
- No soft skills, no ratings, no bars.
- Workday sites handle the Skills box their own way: some leave it empty for the candidate to fill [L01], some suggest skills from the file [S02, L02]. The Skills line does not fill it. The candidate checks the box during the post-upload review and removes anything wrong (`references/readers.md`).

## Everything else

Each has a home inside the five sections.

- **Awards and rankings:** in the bullet for the work that earned them, with the issuer and year.
- **Publications and talks:** in the bullet for the work they came from, as a result (who published it, who ran the event). Textkernel flags a publications section with little content [S44].
- **Patents:** in the bullet for the work.
- **Volunteer work:** a role in Experience when it has real scope and dates; otherwise off.
- **Languages:** on the Skills line with a level.
- **Memberships:** on the Skills line, or under Certifications where the field treats them as credentials.
- **Security clearance:** under Certifications, or on the contact line for defense work, where it is the first filter.
- **A method or tool the candidate built that others still use:** the authorship goes in a bullet at the employer where it was built, with who adopted it and how often it ran. The plain description, never a coined name nobody searches for.
- **An employment gap:** the candidate's call. One vendor field test found that a stated reason, in both the resume and the cover letter, raised callbacks from 4.3% to 6.8% [S54]. Never frame a gap as a shortcoming.

## Length

- **Under about 10 years of experience: one page.** **10 years and up: two pages.** About 70% of 418 hiring professionals accept two pages at 16 years [S56]. Stanford GSB and MIT cap at two pages [S62, S65]; Yale says one to two [S63]; Kellogg says usually one to two [S68].
- **Never three pages** for a US private-sector resume. 81% of the same survey called more than two pages excessive [S56].
- **Fill the pages you use.** 61% said a page that spills over hurts the candidate [S56]. A short page two is a material problem (the skill's judgment): go back to the evidence for the next strongest on-target claim before touching spacing.

## File and format

- **DOCX, a complete one.** Textkernel, a parser behind several systems, treats a PDF as a major issue [S44, S100]. The file carries every part Word writes: Lever's parser refused a six-part file and read the same text once those parts were added [L04, S89]. `build_resume.py` writes the full set, and `parse_check.py` warns when a file lacks it. A file edited in Word and saved again keeps the parts.
- **One column.** No tables, text boxes, columns, images, icons, charts, or content in page headers and footers [S14, S01, S44]. `parse_check.py` fails tables, text boxes, columns, images, hidden text and contact details in a header or footer; look for the rest on the render.
- **One font:** Calibri, Arial, Helvetica, Georgia, Garamond or Times New Roman, body 10 to 12 point. Margins at least 0.5 inch. The guides range from Times New Roman at 10 to 11 point with 0.5-inch margins [S63] to Calibri or Arial at 11 to 12 with 0.7 [S62].
- **Bold** for the name, the headline if there is one, section headers, each company line and each job title [S53]. Dates and bullets stay plain.
- **Standard bullets** from the normal list style. No special glyphs.
- **Filename:** `Firstname-Lastname-Resume.docx`. No dates, versions or company names in it.
- **The plain-text copy** comes from the same source, written by the build. Paste it into plain-text fields.
- **Name and email appear once,** at the top of page one. Repeating them on page two needs a forced page break, which lands differently in Word, Google Docs and LibreOffice. Stanford asks for it [S62]; the layout risk outweighs it (the skill's judgment).
- **Spacing default** (`build_resume.py`): 0.5-inch margins and tight paragraph spacing. In testing it held a 16-year career to two pages [L05]. Change words, not spacing, to fix a page break.

## The JSON source

`build_resume.py` builds both files from one source. A role is a structured block, so the layout is set in one place:

```json
{
  "name": "Dana Reyes",
  "blocks": [
    {"kind": "name", "text": "Dana Reyes"},
    {"kind": "contact", "text": "Toledo, OH | (419) 555-0134 | dana@example.com | linkedin.com/in/danareyes"},
    {"kind": "header", "text": "Summary"},
    {"kind": "para", "text": "Maintenance supervisor with 11 years ..."},
    {"kind": "header", "text": "Experience"},
    {"kind": "role", "company": "Brightline Tool", "city": "Toledo", "state": "OH",
     "title": "Maintenance Supervisor", "start": "Mar 2018", "end": "Present"},
    {"kind": "bullet", "text": "Maintained 22 CNC machines ..."},
    {"kind": "earlier", "text": "Earlier career: Line Operator at Maumee Molding in Maumee, OH, 2004 to 2010."},
    {"kind": "header", "text": "Education"},
    {"kind": "para", "text": "AAS, Industrial Maintenance | Owens Community College | 2009"},
    {"kind": "header", "text": "Skills"},
    {"kind": "para", "text": "Fiix, Allen-Bradley PLCs, hydraulics"}
  ]
}
```

Optional at the top level: `"career_totals": ["100+ workshops"]`, the career totals the candidate confirmed that may sit in the summary with no single job behind them (`references/writing.md`, The summary). `draft_review.py` reads it; the build ignores it.

Block kinds: `name`, `headline`, `contact`, `header`, `para`, `role`, `bullet`, `earlier`. The build refuses: a working marker (`[NEEDS NUMBER]`, `TK`, brackets); a header outside the five; a role missing a field; a date not in `Mon YYYY` form; a comma or parenthesis in a title or company; a recent role with no bullet; a bullet under Summary; more than one Skills line; a "Skills:" line inside Experience; more than one earlier-career line.

## Build checklist

- [ ] Contact line with city, phone, email, LinkedIn; in the body
- [ ] Summary is one prose paragraph, no bullets
- [ ] Every role: bold company line with city and state, bold title with no comma or parenthesis, `Mon YYYY` dates
- [ ] Every role in the last 15 years has at least one bullet; older roles in one earlier-career line
- [ ] Every required qualification that is true is proven in a role bullet (`references/tailoring.md`)
- [ ] Required tools inside the bullets where they were used; Skills is one line at the end (absent only when there is nothing concrete)
- [ ] No Accomplishments or Highlights section; each achievement in its job
- [ ] Education and certifications in full
- [ ] One page under about 10 years, two full pages at 10 and up, never three
- [ ] `draft_review.py`: no FAIL. `build_resume.py`: builds. `parse_check.py`: PASS. Render viewed. `widow_check.py`: clean. `profile_check.py`, when the candidate gives their LinkedIn jobs file: no FAIL.
