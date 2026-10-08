# Resume Ops

A Claude skill that builds and tailors US resumes for the four readers that decide who gets an interview: the application form, the AI grader, the recruiter and the hiring manager.

## Why it exists

Before a person sees a resume, the application form reads it and fills in the job history. In a live Workday test, every job title with a comma came back cut off at the comma, in every layout tried. The title-first layout got 2 of 8 jobs fully right. The company-first layout this skill uses got all 8 right.

Then an AI grader may score it. Workday's HiredScore gives an A or a B only when the resume meets every required qualification in the posting. In a test with stand-in AI graders, a required tool listed only under Skills, with no job behind it, got no credit.

Resume Ops is built on findings like these. It takes whatever you have about your work and builds a true resume for one posting, one that fills the form correctly and proves each requirement inside the job where you did the work.

## Install

This repository's marketplace, `roundofschatz`, lists all three of the author's Claude tools: resume-ops, [plainspeak-writer](https://github.com/roundofschatz/plainspeak-writer), which writes in a plain human voice, and [job-seeker-ops](https://github.com/roundofschatz/job-seeker-ops), which writes a cover letter from a candidate's confirmed case and has a blind reviewer read it. job-seeker-ops includes copies of resume-ops and plainspeak-writer. Install it for the whole set, or the other two on their own for a leaner one, but not both: with two copies installed, Claude sees two skills with the same job and may load either.

**Claude app (web or desktop).** This route can update itself.

1. Open **Customize**, then **Plugins**.
2. Choose **Add marketplace** and enter `roundofschatz/resume-ops`.
3. Install **resume-ops**. To get new versions without asking, turn on **Sync automatically** for the marketplace.

**Claude Code.**

```
/plugin marketplace add roundofschatz/resume-ops
/plugin install resume-ops@roundofschatz
```

For the whole set, install `job-seeker-ops@roundofschatz` instead. `plainspeak-writer@roundofschatz` installs the writing skill on its own.

**Upload by hand.** Zip the `skills/resume-ops` folder, with the folder itself inside the zip, and upload it under **Customize**, **Skills**. You'll need to upload again for each new version.

## Use it

Give Claude the link to one job posting and whatever you have about your work. One file is enough: an old resume, a cover letter, your LinkedIn profile, your website, a career record or a page of notes, in any format. Then say what you want:

- *Build me a resume for this posting.*
- *Here's my LinkedIn PDF. Tailor a resume to this job.*
- *Will this file parse?*
- *Why am I not getting replies?*

Each session opens with a short status block that names the version and the files it's working from, so you can check it before it writes anything.

## What it does

- Builds a resume for one posting from whatever you give it. Nothing has to exist first.
- Checks every required qualification in the posting against your files: proven in the job where you did the work, written into that job when your files show it, or named as a gap.
- Searches a large file for each qualification instead of reading it whole, and points to the file, heading and line behind each claim.
- Writes a Word file and a plain-text copy, then runs scripts that check the structure and flag AI-writing tells.
- Tells you what to fix in the application form after you upload.
- Keeps your titles and dates the same on every resume, and checks them against your LinkedIn jobs export before an employer does.
- Builds a base resume for job boards when you want one.
- Reads a positioning file from job-seeker-ops's candidate-positioning skill when you have one, to aim the summary and put the strongest proof first. It builds the same way without one.

Full detail on the scripts, file layout and tests: [`skills/resume-ops/README.md`](skills/resume-ops/README.md).

## Where the rules come from

Every claim about a hiring system, a study or a law cites a source in [`sources.md`](skills/resume-ops/references/sources.md): 101 outside sources and 5 live tests, each with its date, a grade for how strong it is, the URL and a short quote. A test fails if a rule cites a source that isn't listed. Where no source exists, the skill says the rule is its own judgment.

## Scope

US resumes for US private-sector jobs. For anything else, such as a government posting or an academic CV, the skill stops and says so. It writes from what you tell it and doesn't give legal or career advice.

## Changes

See the [changelog](skills/resume-ops/CHANGELOG.md).

## Author

Ryan Schatzman · [LinkedIn](https://www.linkedin.com/in/ryanschatzman)

## License

MIT. See [`LICENSE`](LICENSE).
