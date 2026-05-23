# Wire the contact form to HubSpot — 60 seconds

The website code is ready. One step remains: create a form in HubSpot, copy its GUID, paste into two files.

## Step 1 — Create the form in HubSpot

1. Go to **Marketing → Lead Capture → Forms** in your HubSpot account
   (direct: https://app.hubspot.com/forms/51502417)
2. Click **Create form** (top right) → choose **Embedded form** → **Next**
3. Pick the **Blank template** → **Start**
4. From the left rail, drag these contact properties onto the form (in this order):
   - **First name** (required)
   - **Last name** (required)
   - **Email** (required)
   - **Company name**
   - **Job title**
   - **Message** (multi-line text)
5. **Form name** (top of screen): `OfficeBeat — Website Contact`
6. Click **Options** tab → set **Send a notification to** = `team@officebeatllc.com`
7. Click **Publish** (top right)

## Step 2 — Grab the Form GUID

After publishing, HubSpot will show an embed code. It contains a line like:
```
formId: "abc12345-6789-def0-1234-567890abcdef"
```
That long string is your **Form GUID**. Copy it.

Alternatively: the URL after publishing looks like
`https://app.hubspot.com/forms/51502417/editor/<FORM_GUID>/edit/form` — the GUID is the long string in the middle.

## Step 3 — Paste into two files

Open these files and replace `REPLACE_WITH_FORM_GUID` with your GUID:

- `Website/contact.html` — line ~197
- `Website/assess.html` — line ~359

Or just tell me the GUID and I'll do it.

## What happens next

- Visitor fills out contact form → submission lands as a new HubSpot **Contact** with all fields populated
- Practice + topic dropdowns get prepended to the message field as `[Practice: ...] [Topic: ...]` for context
- Visitor gets redirected to `thanks.html`
- You get a notification email at team@officebeatllc.com
- HubSpot tracking cookie (already installed) gives you full source attribution (which page they came from, UTM params, prior visits)

## Optional — Plausible analytics

The Plausible snippet is in every page commented out. To turn it on:
1. Sign up at https://plausible.io (~$9/mo for officebeatllc.com)
2. In each HTML file, uncomment the line:
   `<!-- <script defer data-domain="officebeatllc.com" src="https://plausible.io/js/script.js"></script> -->`
   (find with: `grep -l plausible Website/*.html`)
