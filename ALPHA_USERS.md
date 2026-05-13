# Alpha users playbook

This dashboard supports multiple users now. Each user has their own resume,
their own AI skills profile, and their own filtered job list. Per-user URLs
look like: `https://getmyjob.officebeatllc.com/jane.html`.

## One-time setup

1. **Add an `ADMIN_KEY` secret to the Cloudflare Worker.**
   In the Cloudflare dashboard → `cool-darkness-dce5` → Settings →
   Variables and Secrets → Add → name `ADMIN_KEY`, value a long random
   string (e.g. from a password manager). This protects the
   `/admin/users` endpoint.

2. **Make sure the latest Worker code is deployed** (Phase 5 file —
   `worker_phase5.js`). It auto-migrates Geetanjali's existing data to
   `user:geetu:*` on first read.

## Adding a new alpha user

Replace `JANE`, `PASSWORD`, `ADMIN_KEY` below with real values.

```sh
curl -X POST https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/admin/users \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ADMIN_KEY" \
  -d '{"slug":"jane","name":"Jane Doe","editKey":"PASSWORD"}'
```

Then add the user to `users.json` (top-level array):

```json
[
  { "slug": "geetu", "name": "Geetanjali Arora" },
  { "slug": "jane",  "name": "Jane Doe" }
]
```

Commit, push, and let the next 6-hour refresh generate `jane.html`. Or
click **Refresh data** to trigger immediately.

## Email template to the new user

> Hi Jane,
>
> I built a personal job-search dashboard tailored to your background.
> It pulls healthcare/tech roles from ~50 companies, ranks them against
> your resume, and one-clicks a tailored summary + cover letter +
> tailored resume per job.
>
> Your link: https://getmyjob.officebeatllc.com/jane.html
> Password (for resume upload): PASSWORD
>
> First time: click "Resume" top-right, enter the password, upload
> your resume as PDF or Word. The AI will parse it and start scoring
> jobs against your profile within minutes.
>
> Let me know if anything's off — I tune it.

## Removing a user

```sh
curl -X DELETE https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/admin/users \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ADMIN_KEY" \
  -d '{"slug":"jane"}'
```

Wipes all `user:jane:*` keys. Then remove from `users.json` and push.

## List all configured users

```sh
curl https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/admin/users \
  -H "X-Admin-Key: ADMIN_KEY"
```

## Cost guardrails

- Set a hard monthly cap in https://console.anthropic.com/settings/billing
  (recommended: $50/month for 5 alpha users).
- Each Prep Application click costs roughly $0.10–0.20.
- Each resume upload costs ~$0.05 to parse + ~$0.05 to generate skills profile.
- KV / Worker / GitHub Pages costs stay at $0 within free tier at this volume.
