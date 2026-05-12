# HealthTech Jobs for Geetanjali

A personal job-tracker that pulls senior leadership healthcare IT roles from real companies' job boards and shows them in a clean dashboard. No scraping, no ghost jobs, no third-party recruiter spam.

## What it does

- Pulls jobs from **180+ healthcare and health-tech companies** (Oscar, Cedar, Cohere, Hinge, Komodo, Tempus, Veeva, Doximity, Moderna, Modern Health, Maven, Spring, Headspace, Pfizer, Merck, CVS Health, and many more) via their public ATS APIs (Greenhouse, Lever, Ashby, Workday)
- Filters for **senior leadership** (Director / Senior Director / Principal / VP / Head of) and **remote** roles
- Scores each job for relevance to Geetanjali's profile (healthcare IT, digital transformation, product portfolio, agile)
- Filter buttons for **Today / Last 7 days / Last 30 days / All** so you only see fresh listings
- Tracks every job over time so you can see **ghost jobs** (listed 30+ days — probably not really hiring) and **reposts**
- Generates a single HTML dashboard you open in your browser — works offline once generated

## How to use (Mac)

**First-time setup** — one minute:

1. Open Terminal (press Cmd+Space, type "Terminal", hit Enter)
2. Type this and hit Enter:
   ```
   cd ~/Documents/Claude/Projects/"Ticky Sun"/healthtech-jobs
   chmod +x run.sh
   ```

**To check for new jobs** — any time:

```
cd ~/Documents/Claude/Projects/"Ticky Sun"/healthtech-jobs
./run.sh
```

This fetches the latest jobs (takes ~2 minutes) and opens the dashboard in your browser. The dashboard shows the highest-scoring jobs first.

## Reading the dashboard

Each job card shows:
- **Score (0–100)** — higher = better match for Geetanjali's profile + more likely "real"
- **Senior** badge — title contains Director / VP / Principal / etc.
- **Remote** badge — listing mentions remote
- **New today** badge — listed today
- **This week** badge — listed within the last 7 days
- **Ghost? Nd** badge — listed more than 30 days ago (likely not actively hiring)
- **Seen N×** badge — we've spotted this same job N times across runs (frequent reposts can be a yellow flag)

Use the search box, the **Today / Last 7 days / Last 30 days / All** buttons, and the seniority dropdown at the top to narrow down.

## Adding more companies (to grow toward 500)

Open `companies.json` and add company slugs to the right list:

- A company's careers page URL `boards.greenhouse.io/cedar` → add `"cedar"` to the `greenhouse` list
- `jobs.lever.co/glooko` → add `"glooko"` to the `lever` list
- `jobs.ashbyhq.com/abridge` → add `"abridge"` to the `ashby` list

Good sources for more health-tech companies:
- Rock Health portfolio (rockhealth.com/companies)
- BuiltIn NYC Healthtech section
- Y Combinator's health-track companies
- CB Insights digital health 50

You don't need to verify each slug — the fetcher logs and skips any that don't return jobs.

## Why this is better than browsing LinkedIn

- **Only real openings** — these are pulled directly from each company's ATS, so if it's on the dashboard, the company actually has the role open
- **No staffing agencies** — only direct employer listings
- **Ghost-job detection** — we track how long each job has been open
- **One place to scan** — instead of 120 tabs

## What's not included (yet)

- LinkedIn / Indeed / Glassdoor — these block scrapers. To add them, we'd use a paid API service like Bright Data or Apify (~$30–100/month). Let me know if you want me to add that.
- Email alerts — could be added; right now you re-run when you want fresh data.
- UnitedHealth / Optum — they use a custom non-Workday portal that doesn't expose a clean public API. Worth checking those careers pages directly.
- Most Workday-based pharma is supported (Pfizer, Merck, CVS Health included). To add more Workday companies, look at their careers URL: `https://{tenant}.{wd1|wd5|...}.myworkdayjobs.com/{site}` — append the parts to the `workday` array in `companies.json`.

## Files in this folder

| File | What it is |
|---|---|
| `run.sh` | Run this to fetch jobs and open dashboard |
| `fetch_jobs.py` | The actual fetching + filtering logic |
| `companies.json` | List of companies to pull from (edit to add more) |
| `dashboard.html` | The dashboard (regenerated each run) |
| `jobs.db` | Local database of all jobs ever seen (so we can detect ghosts) |
| `README.md` | This file |
