# Deploying the dashboard to getmyjob.officebeatllc.com

Total time: about 15 minutes. Cost: **$0/month** (Cloudflare Pages free tier + you already own the domain).

**Architecture:**
1. **GitHub** stores the project. A scheduled GitHub Action runs the fetcher every 6 hours and commits the updated `dashboard.html`.
2. **Cloudflare Pages** auto-deploys the dashboard from your GitHub repo whenever new content is pushed.
3. **IONOS DNS** points `getmyjob.officebeatllc.com` to Cloudflare via a single CNAME record.

The "Prep Application" feature stays on Geetanjali's Mac (it needs the AI key, which we don't want to expose publicly). She'll keep using it locally; the hosted dashboard is for browsing fresh jobs from anywhere.

---

## Step 1 — Push the project to GitHub (5 min)

1. Go to **https://github.com/new** while signed in.
2. Repository name: `healthtech-jobs` (or whatever you want).
3. **Make it PRIVATE.** This is important — the project includes a list of companies you're tracking; keep it personal.
4. Don't check any of the init options. Click **Create repository**.
5. On the next screen, GitHub shows a "push existing repository" command block. Copy the URL from the top of the page (looks like `https://github.com/yourname/healthtech-jobs.git`).
6. Open Terminal and run:

```bash
cd ~/Documents/Claude/Projects/"Ticky Sun"/healthtech-jobs
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOURNAME/healthtech-jobs.git
git push -u origin main
```

Replace `YOURNAME/healthtech-jobs.git` with the actual URL from GitHub. The first time you push, GitHub may ask for credentials — use a personal access token (Settings → Developer settings → Personal access tokens → Generate new token → scope: `repo`).

**Verify:** Open `https://github.com/YOURNAME/healthtech-jobs` in a browser. You should see the files. **Check that `.env` is NOT in the file list** (the `.gitignore` keeps it local).

---

## Step 2 — Connect Cloudflare Pages (5 min)

1. Go to **https://dash.cloudflare.com** and sign up (free) if you don't have an account.
2. In the left sidebar: **Workers & Pages** → **Create application** → **Pages** → **Connect to Git**.
3. Authorize Cloudflare to access your GitHub. Select the `healthtech-jobs` repo.
4. Build settings:
   - **Project name:** `healthtech-jobs` (this becomes part of the temporary URL: `healthtech-jobs.pages.dev`)
   - **Production branch:** `main`
   - **Framework preset:** None
   - **Build command:** *(leave blank)*
   - **Build output directory:** `/`
5. Click **Save and Deploy**.
6. Wait ~30 seconds. When it finishes, you'll see your dashboard at `https://healthtech-jobs.pages.dev`. Open it in a browser to confirm.

---

## Step 3 — Point your subdomain at Cloudflare (5 min)

1. Back in Cloudflare Pages, click your project, then go to **Custom domains** → **Set up a custom domain**.
2. Enter: `getmyjob.officebeatllc.com`
3. Cloudflare shows you a CNAME record to add. Note the **target value** (it'll be `healthtech-jobs.pages.dev` or similar).
4. **Switch to IONOS:**
   - Log in at **https://my.ionos.com**
   - Click **Domains & SSL** → click on **officebeatllc.com**
   - Click **DNS** (or "DNS Settings")
   - Click **Add Record** and choose **CNAME**
   - **Host name:** `getmyjob`
   - **Points to:** the value Cloudflare gave you (e.g. `healthtech-jobs.pages.dev`)
   - **TTL:** 1 hour (default is fine)
   - Save.
5. Back in Cloudflare, the custom domain check will run automatically. It can take anywhere from 1 minute to an hour for DNS to propagate. When it shows "Active", you're done.
6. Visit **https://getmyjob.officebeatllc.com** in your browser. Cloudflare provisions SSL automatically.

---

## Step 4 — Turn on the auto-refresh (1 min)

This is already configured. The `.github/workflows/refresh-jobs.yml` file in your repo tells GitHub Actions to run the fetcher every 6 hours and commit the updated dashboard. Each commit triggers Cloudflare to redeploy. No further action needed.

**To confirm it's running:** in GitHub, go to your repo → **Actions** tab. After 6 hours (or trigger it manually via the "Run workflow" button), you should see a green check mark.

**To change the refresh frequency:** edit `.github/workflows/refresh-jobs.yml`, change the cron schedule (`0 */6 * * *` = every 6 hours; `0 */2 * * *` = every 2 hours; `0 8,12,16,20 * * *` = at 8 AM, noon, 4 PM, 8 PM UTC).

---

## How "Prep Application" works in the hosted world

When Geetanjali visits the hosted dashboard from her phone or laptop:
- She can **browse jobs**, filter, search, and track which ones she's applied to. The tracker uses her browser's local storage so it remembers state per device.
- The **"Prep Application"** button shows her the Terminal command to run on her Mac. She copies it, opens Terminal on her Mac, pastes, and the AI does its thing locally.

This keeps her API key (and her resume content) private — nothing ever leaves her Mac for the AI step. The hosted side is read-only and public-safe.

---

## What to do when you want to add more companies

1. Edit `companies.json` locally.
2. Run `./run.sh` to refresh.
3. Commit and push:
```bash
cd ~/Documents/Claude/Projects/"Ticky Sun"/healthtech-jobs
git add companies.json
git commit -m "Add more companies"
git push
```
The hosted version updates within ~30 seconds of the push.

---

## Troubleshooting

**Cloudflare custom domain stuck on "Pending"** — wait 15 minutes. If still stuck, double-check the CNAME target in IONOS matches exactly what Cloudflare showed.

**GitHub Action fails** — go to Actions tab, click the failed run, expand the error. Most common cause: a slug in `companies.json` is malformed JSON. Fix it locally, commit, push.

**Pushed `.env` by accident** — bad. Rotate the API key immediately (delete it in Anthropic console, create a new one), and remove the file from git history with `git rm --cached .env && git commit -m "remove env" && git push`. Add it to `.gitignore` if it isn't already.
