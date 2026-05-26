# Daily Email Digest — Setup (one-time, ~5 minutes)

The Worker now sends a 7am digest email to each user with their top-N (= dailyTarget) job picks. To make it actually fire, you need to:

## 1. Sign up for Resend (free tier covers 100 emails/day — plenty for alpha)

https://resend.com — sign up with your `amit.arora@officebeatllc.com` business address.

In their dashboard:
- **API Keys → Create API Key** — name it `getmemyjob-prod`. Copy the value (starts with `re_…`).
- **Domains → Add Domain** — add `officebeatllc.com`. Resend gives you a few DNS records (TXT for SPF/DKIM, MX optional). Add those to your DNS at Cloudflare. Wait 5-10 minutes for verification.

## 2. Add two Worker secrets

Go to the Cloudflare Dashboard → Workers & Pages → `cool-darkness-dce5` → Settings → Variables → **Secret variables → Add variable**:

- `RESEND_API_KEY` = the `re_…` value from step 1
- `DIGEST_FROM` = `getmemyjob <noreply@officebeatllc.com>` (or any address on a domain you verified)

## 3. Add the Cron Trigger

Same Worker → Settings → **Triggers → Cron Triggers → Add Cron Trigger**:

- Cron expression: `0 11 * * *`  (this is 11am UTC = 7am ET = 4am PT)

Save.

## 4. Test it manually

Once the secrets are set, call the trigger endpoint to send a digest right now:

```
curl -X POST "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/admin/digest-trigger?user=geetu" \
  -H "X-Admin-Key: <your-ADMIN_KEY>"
```

For all users at once:

```
curl -X POST "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/admin/digest-trigger" \
  -H "X-Admin-Key: <your-ADMIN_KEY>"
```

The response is JSON with `{ sent: N, total: M }`.

Geetu should get an email within a few seconds with her 5 picks of the day (or whatever her dailyTarget is set to).

## Operational notes

- The digest pulls today's top-N from `https://getmemyjob.officebeatllc.com/<slug>.html` — so it always reflects the latest refresh-jobs build.
- Users marked "applied" today are filtered out so she doesn't see what she already did.
- If you skip the Resend setup, the Worker scheduled handler logs `"missing secrets — skipping"` and quietly does nothing. No errors.
- Resend's free tier = 100 emails/day. For 5 alpha users that's ~150 emails/month — well under limit.
