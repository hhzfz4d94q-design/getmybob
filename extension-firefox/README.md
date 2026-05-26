# getmemyjob Helper — Chrome extension

Auto-fills job application forms on Greenhouse, Lever, Ashby, and Workday using your getmemyjob profile.

## What it does

When you click "Apply now" on a getmemyjob job and land on the ATS form page, this extension reads your stored resume/profile and pre-fills the standard fields (name, email, phone, LinkedIn, current company, work authorization). For custom free-text questions ("Why this company?", "Tell us about a project where..."), it adds a **"✨ Draft with AI from your resume"** button that calls our Worker `/prep` endpoint and pastes the tailored answer.

You still review and click Submit yourself — the extension never submits forms on your behalf.

## What it covers today

| ATS | Coverage | Notes |
|---|---|---|
| **Greenhouse** (Headway, Aledade, Spring Health, Cohere, etc.) | ~18 of 25 standard fields | Most reliable. AI-draft button on cover-letter and answer textareas. |
| **Lever** (BetterUp, Calm, H1, Datavant, etc.) | ~12 of 18 standard fields | Reliable. |
| **Ashby** (Linear, Replit, Ramp-adjacent startups) | ~10 of 15 standard fields | Field detection via label-text match because Ashby randomizes field names. |
| **Workday** (Wells Fargo, Citi, Pfizer, BlackRock, etc.) | ~6 of 30+ fields | Variable per tenant. Standard fields only. Workday's multi-page custom flows fill partially. |

EEO fields (race, gender, veteran, disability), salary expectations, and Workday-tenant custom questions are left blank for you to fill — those require explicit consent each time.

## Install (one time, ~2 minutes)

1. Download this folder (`/extension/`) to your computer, OR install from the `getmemyjob-helper.zip` file shared with you.
2. If you have a ZIP, unzip it to a folder you'll keep around (e.g. `~/getmemyjob-helper/`).
3. In Chrome, go to `chrome://extensions`.
4. Toggle **Developer mode** ON (top-right).
5. Click **Load unpacked**.
6. Select the folder.
7. The 🎯 getmemyjob Helper icon appears in your toolbar. Pin it (click the puzzle icon → pin).

## Sign in (one time)

1. Click the 🎯 icon in your toolbar.
2. Enter your **slug** (the part of your invite URL right before `?key=` — e.g. `geetu` if your URL is `https://getmemyjob.officebeatllc.com/geetu.html?key=…`).
3. Paste your **edit key** (the value after `?key=` in your invite URL).
4. Click **Sign in**. The extension fetches your skills profile + resume from our Worker and caches it locally.

The extension keeps your data in Chrome's local storage. It never sends form data anywhere except the target ATS.

## Use

1. On your getmemyjob dashboard, click **Apply now →** on any job.
2. The ATS apply page opens in a new tab.
3. Within ~1-2 seconds the extension fills the standard fields. You'll see a toast at the top-right: "Filled 18 fields ✓".
4. For free-text custom questions, click the **✨ Draft with AI** button next to the textarea. It generates a tailored answer based on your resume + the job's description.
5. Review everything. Solve any CAPTCHA. Click Submit.

## Troubleshooting

- **Toast says "Sign in via the extension popup first"** — open the extension popup and sign in.
- **Form is empty** — extension may have run before the form loaded. Hit "Refresh profile" in the popup, then reload the page.
- **Field is wrong** — your stored profile is wrong. Edit it on your getmemyjob dashboard (Resume → Profile tab), then click "Refresh profile" in the extension popup.
- **Workday gives me trouble** — Workday is hostile to automation. Standard fields work; custom-per-tenant fields don't.
- **My EEO/veteran/disability answers aren't filled** — by design. Those need explicit consent each time. We may add an opt-in setting in a future version.

## What it WILL NEVER do

- Submit forms on your behalf
- Solve CAPTCHAs
- Apply to LinkedIn jobs (LinkedIn blocks extensions)
- Apply to company-custom careers pages (Apple, Tesla, etc.)
- Send your data to anyone except the target ATS

## Version

0.1.0 — initial MVP. Built 2026-05-26.
