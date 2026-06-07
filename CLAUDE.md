# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project identity

This is **getmemyjob** (brand) — repo name `getmybob`, local folder `healthtech-jobs`. A multi-user AI-matched job feed for senior healthcare-IT leadership roles, built and operated by a non-developer owner. Live at getmemyjob.officebeatllc.com (Cloudflare Pages project `getmemyjob`).

## Owner workflow constraints

- The owner works **web-only**: github.dev / github.com file editor + the GitHub Actions UI. Do not propose local CLI workflows, wrangler, or tool installs.
- GitHub Actions is the ops console. Almost every operational task (deploys, user admin, catalog growth, diagnostics) is a `workflow_dispatch` workflow in `.github/workflows/` — check there before inventing a new procedure.
- Workflows that need to report results commit logs back to the repo (e.g. `.refresh-debug/LAST_RUN.log` + `LAST_EXIT_CODE`) because raw Actions log URLs can be unreadable from the owner's environment. Follow this pattern for new workflows that need debuggability.

## Architecture (two halves)

**1. Static pipeline (this repo → Cloudflare Pages).** `refresh-jobs.yml` runs every 2 hours: it executes `fetch_jobs.py`, which pulls jobs from public ATS APIs, scores them per user, regenerates per-user dashboard HTML files (`geetu.html`, `amit-arora.html`, …), and commits everything (including `jobs.db`, a tracked SQLite file used for ghost-job/repost detection). Cloudflare Pages auto-deploys on push to `main`. The dashboards are fully static — all interactivity is inline JS that calls the Worker.

**2. Cloudflare Worker (`cool-darkness-dce5`, source: `worker_target.js`).** A single ~4,200-line file serving ~50 endpoints: auth (`/api/auth/*`), resume versioning + parsing, per-user `skills_profile` in KV (`user:{slug}:*` keys, `users:list` index), AI features (profile regeneration, prep, warm intros, interview prep, reranking), and an hourly `scheduled()` cron that sends digest emails. The KV layout is documented in the header comment of `worker_target.js`.

`fetch_jobs.py` (~1,900 lines) is the orchestrator after a phased split (see `docs/REFACTOR_PLAN_FETCH_JOBS.md`):

- `matcher/` — `scoring.py` (`score_job`; `SKILLS_PROFILE` is a module global that `fetch_jobs.py` sets before generating each user's dashboard), `canonical.py`, `catalogs.py` (loads/merges `healthtech_companies.json` + `vc_portfolio_companies.json`), `role_family.py`
- `scrapers/` — one module per ATS (greenhouse, lever, ashby, workday, …) sharing `scrapers/_http.py`
- `dashboard/` — `template.py` (`HTML_TEMPLATE`, rendered via `.format()`), `wizard.py` (`WIZARD_V3_BLOCK`, the 12-step first-login wizard), `help.py`
- `storage/` — `db.py` (SQLite schema), `profile.py`

Company catalogs: `companies.json` (per-ATS slug lists), `healthtech_companies.json`, `vc_portfolio_companies.json`, `workday_tenants.json`. Users come from `users.json` plus the Worker's `users:list`.

## Commands

```bash
# Full pipeline: fetch all jobs, score, regenerate all dashboards
python3 fetch_jobs.py

# Tests are standalone scripts (no pytest runner) — run individually:
python3 tests/test_unit.py
python3 tests/test_scoring.py            # score_job golden tests
python3 tests/test_match_goldens.py      # catches silent score=0 regressions
python3 tests/test_scrapers.py           # ATS parser fixtures
python3 tests/test_catalog_integrity.py  # dup slugs, bad atsHint, broken names
python3 tests/test_dashboard_js_syntax.py
python3 tests/test_wizard_v3.py

# Node tests (need: npm i jsdom)
node tests/test_e2e_dashboard.mjs
node tests/test_sprint_reminder.mjs
node tests/test_align_pool.mjs

# JS gate used by CI — extracts every <script> block and runs node -c
python3 scripts/validate_dashboard_js.py
```

CI: `test.yml` runs the Python suite on every push/PR; `js-syntax-gate.yml` runs the JS gate when `fetch_jobs.py`, `dashboard/**`, or the auth/account HTML pages change.

## Deploying the Worker

Never use wrangler or the Cloudflare dashboard editor. The flow is:

1. Edit `worker_target.js` and push to `main`.
2. Run the **"Manage Cloudflare Worker"** workflow (`manage-worker.yml`) with `mode=deploy`. It PUTs `worker_target.js` to the Worker's `/content` endpoint, preserving secrets and bindings.
3. `mode=dump` pulls the live Worker source into `worker_current.js` for review. `worker_current.js` is a snapshot — never edit it as source.

## Hard-won invariants (do not regress)

- **`.format()` templates**: `dashboard/template.py` renders with `.format()`, so every literal `{`/`}` in HTML/CSS/JS must be doubled (`{{ }}`). `wizard.py` is appended raw and uses single braces.
- **JS-in-Python escape bugs** are the top historical regression class ("all buttons break"). Any change touching embedded dashboard JS must pass `scripts/validate_dashboard_js.py` before shipping.
- **Every scraper must import `_strip_html`** (or its equivalent from `_http`). A missing import once silently broke 11 scrapers and left `jobs.db` stale for weeks — failures here are silent, not loud. `test_match_goldens.py` and `test_scrapers.py` exist to catch this class.
- **No caps on wizard/account profile fields**: titles, industries, and skills are uncapped, and `current` selections seed from the full resume pool. Do not reintroduce slicing/auto-trim in save paths.
- **`regenerateSkillsProfile` in the Worker must preserve** the user's existing `targetTitles`, `industries`, `keywords`, etc. across regeneration — the AI prompt has 5/5/15 caps that would otherwise wipe wizard picks on every resume change.
- **Digest emails render strong → good → borderline**, not raw score order.
- **Seniority targeting**: users target Director / VP / Principal-level roles, explicitly *not* CXO. The AI profile extractor tends to over-elevate seniority and over-broaden industries; `patch-profiles.yml` + `scripts/apply_profile_patches.py` is the bulk-correction path.

## Pre-deploy gates for dashboard changes

Before any change that touches dashboard generation ships: `test_scoring.py`, `test_catalog_integrity.py`, `validate_dashboard_js.py`, and a full `python3 fetch_jobs.py` run that produces valid HTML. For pure refactors, diff the generated `geetu.html` before vs. after — it should be byte-identical.
