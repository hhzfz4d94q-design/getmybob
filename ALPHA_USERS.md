# Alpha users playbook

Multi-user dashboard. Each user has their own resume, skills profile, and
filtered job list at `https://getmyjob.officebeatllc.com/{slug}.html`.

The user registry lives in Cloudflare KV (`users:list`). The admin UI at
`/admin.html` is the easiest way to manage it.

## One-time setup

1. **Add `ADMIN_KEY` to the Cloudflare Worker.**
   Cloudflare → `cool-darkness-dce5` → Settings → Variables and Secrets
   → Add Secret → name `ADMIN_KEY`, value a long random string. Save it
   to a password manager — you'll enter it once per browser.

2. **Deploy the latest Worker** (Phase 6). It auto-bootstraps
   `users:list` from any existing `user:*:edit_key` keys on first call.

## Adding a new alpha user

1. Open `https://getmyjob.officebeatllc.com/admin.html`.
2. Enter `ADMIN_KEY` (stored in localStorage so you don't have to redo this).
3. In **Invite a new user**, type their name and email. Click
   **Create & invite**.
4. The Worker generates a random password, creates KV entries, and the
   admin page pops up a pre-filled invite email. Click **Open in email
   client** to send it via your default mail app (Apple Mail / Gmail web /
   Outlook), or **Copy to clipboard** if you'd rather paste somewhere
   else.
5. After the next dashboard refresh (every 6 hours, or click **Refresh
   data** on the dashboard), `{slug}.html` will be live.

## Managing existing users

In the same admin page:

- **Resend invite** — re-opens the same pre-filled email with their
  existing password. Use if they lost the original invite.
- **Delete** — removes the user and all their KV data (resume versions,
  skills profile, edit key). The default user (`geetu`) is protected.

## Cost guardrails

- Set a hard monthly cap at https://console.anthropic.com/settings/billing
  (recommended: $50/month for 5 alpha users).
- Per Prep Application click: ~$0.10–0.20.
- Per resume upload: ~$0.10 (parse + skills profile generation).
- KV / Worker / GitHub Pages: still free tier at this volume.

## Manual provisioning (fallback)

If the admin page doesn't work for some reason, you can always
provision via curl. Replace `ADMIN_KEY` with the secret.

```sh
# Create a user
curl -X POST https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/admin/users \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ADMIN_KEY" \
  -d '{"name":"Jane Doe","email":"jane@example.com"}'

# List all users
curl https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/admin/users \
  -H "X-Admin-Key: ADMIN_KEY"

# Delete a user
curl -X DELETE https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/admin/users \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ADMIN_KEY" \
  -d '{"slug":"jane-doe"}'
```
