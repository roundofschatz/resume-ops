# Resume Ops

A Claude skill that builds and tailors US resumes for the four readers that decide who gets an interview: the application form, the AI grader, the recruiter and the hiring manager.

## Why it exists

Before a person sees a resume, the application form reads it and fills in the job history. In a live Workday test, every job title with a comma came back cut off at the comma, in every layout tried. The title-first layout got 2 of 8 jobs fully right. The company-first layout this skill uses got all 8 right.

Then an AI grader may score it. Workday's HiredScore gives an A or a B only when the resume meets every required qualification in the posting. In a test with stand-in AI graders, a required tool listed only under Skills, with no job behind it, got no credit.

Resume Ops is built on findings like these. It turns your career material into a true resume that fills the form correctly and proves each requirement inside the job where you did the work.

## Install

**Claude app (web or desktop).** This route can update itself.

1. Open **Customize**, then **Plugins**.
2. Choose **Add marketplace** and enter `roundofschatz/resume-ops`.
3. Install **resume-ops**. To get new versions without asking, turn on **Sync automatically** for the marketplace.

**Claude Code.**

```
/plugin marketplace add roundofschatz/resume-ops
/plugin install resume-ops@roundofschatz
```

**Upload by hand.** Zip the `skills/resume-ops` folder, with the folder itself inside the zip, and upload it under **Customize**, **Skills**. You'll need to upload again for each new version.

## Use it

Give Claude whatever you have, such as old resumes or a LinkedIn export, and say what you want:

- *Build me a resume from this.*
- *Tailor my resume to this posting.*
- *Will this file parse?*
- *Why am I not getting replies?*

Each session opens with a short status block that names the version and the facts it's working from, so you can check it before it writes anything.

## What it does

- Builds a facts file from your material, then a base resume for a job family.
- Tailors a copy to one posting by checking every required qualification: proven on the page, written into the job where it happened, or named as a gap.
- Writes a Word file and a plain-text copy, then runs scripts that check the structure and flag AI-writing tells.
- Tells you what to fix in the application form after you upload.
- Checks your resume's titles and dates against your LinkedIn jobs export, so the two match before an employer checks them.

Full detail on the scripts, file layout and tests: [`skills/resume-ops/README.md`](skills/resume-ops/README.md).

## Where the rules come from

Every claim about a hiring system, a study or a law cites a source in [`sources.md`](skills/resume-ops/references/sources.md): 101 outside sources and 5 live tests, each with its date, a grade for how strong it is, the URL and a short quote. A test fails if a rule cites a source that isn't listed. Where no source exists, the skill says the rule is its own judgment.

## Scope

US resumes for US private-sector jobs. For anything else, such as a government posting or an academic CV, the skill stops and says so. It writes from what you tell it and doesn't give legal or career advice.

## Changes

See the [changelog](skills/resume-ops/CHANGELOG.md).

## Author

Built by Ryan Schatzman, a brand and customer experience strategist in Denver. [LinkedIn](https://www.linkedin.com/in/ryanschatzman)

## License

MIT. See [`LICENSE`](LICENSE).
