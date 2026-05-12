# Setting up the AI key (one-time, ~5 minutes)

The "Prep Application" feature uses Claude (an AI model from Anthropic) to tailor Geetanjali's resume and write a cover letter per job. You need an API key for this. Total cost: about $0.05–$0.15 per application — so $20 in credits covers ~150 to 400 applications.

## Step 1 — Sign up

1. Go to **https://console.anthropic.com**
2. Sign up with your email (`amittarora@gmail.com` is fine).
3. Verify your email.

## Step 2 — Add credit

1. Once logged in, click **Plans & Billing** in the left sidebar.
2. Click **Add credits**.
3. Add **$20**. (This is more than enough to start — you can always add more later. Note: this is pre-paid usage, not a subscription.)

## Step 3 — Generate an API key

1. Click **API Keys** in the left sidebar.
2. Click **Create Key**.
3. Name it `healthtech-jobs` (so you remember what it's for).
4. **Copy the key** — it starts with `sk-ant-...`. You'll see it only once, so paste it somewhere safe immediately.

## Step 4 — Save the key in this project

1. Open Terminal (Cmd+Space → "Terminal").
2. Paste this command and hit Enter:

```
cd ~/Documents/Claude/Projects/"Ticky Sun"/healthtech-jobs && echo 'ANTHROPIC_API_KEY=sk-ant-PASTE-YOUR-KEY-HERE' > .env
```

3. **Important:** replace `sk-ant-PASTE-YOUR-KEY-HERE` with the actual key you copied in Step 3.

That's it. The key is now saved locally in a file called `.env` and the prep-application tool will pick it up automatically. The `.env` file stays on your computer — it never gets committed to GitHub or uploaded anywhere.

## How to verify it works

Run this to do a test call:

```
cd ~/Documents/Claude/Projects/"Ticky Sun"/healthtech-jobs && python3 prep_application.py --test
```

If the key works you'll see `OK: AI key is configured correctly`. If you see an error, double-check the key in `.env` — most likely it has a typo or got truncated.

## A note on cost

Per application: roughly $0.05–$0.15 (depending on resume + job description length). Anthropic charges per "token" (about ¾ of a word). $20 buys you somewhere between 150 and 400 application preps. You can monitor usage at **console.anthropic.com → Usage**.

If you run out, just add more credit on the Plans & Billing page.
