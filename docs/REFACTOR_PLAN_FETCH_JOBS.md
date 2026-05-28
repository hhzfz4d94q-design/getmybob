# `fetch_jobs.py` Split — Migration Plan

**Status**: Deferred. Do NOT execute mid-sprint (risk: breaking Geetu's daily feed during her interview push).

**When**: After Geetu's 10-day sprint completes (target: 2026-06-09 or later).

## Why split

`fetch_jobs.py` is ~10,000 lines. Every edit requires sed/python regex on multi-line strings because the file is too big to reason about as a whole. Side effects observed during one night's work:

- Unicode `Saving…` vs `…` mismatch caused a silent edit failure
- `EDIT_KEY` undefined bug existed in production for ~30 minutes because symbol resolution wasn't checked
- The healthtech catalog merger had to be inserted by string match on a comment header — no compiler help

## Target structure

```
fetch_jobs.py            (~500 LOC — orchestrator only)
├── matcher/
│   ├── canonical.py        (~50 LOC — canonical_company, slugify)
│   ├── catalogs.py         (~150 LOC — load + merge VC / healthtech)
│   └── scoring.py          (~800 LOC — score_job)
├── scrapers/
│   ├── greenhouse.py / lever.py / ashby.py / ... (one per ATS)
│   └── runner.py
├── dashboard/
│   ├── template.py         (~200 LOC — HTML_TEMPLATE)
│   ├── wizard.py           (~3000 LOC — WIZARD_V3_BLOCK)
│   ├── sprint.py           (~400 LOC — strip + CTA + particle burst)
│   ├── contacts.py         (~200 LOC — contacts UI + hydration)
│   └── builder.py          (~400 LOC — generate_dashboard)
└── storage/
    ├── db.py               (~150 LOC — SCHEMA + get_conn)
    └── users.py
```

## Migration phases (each independently shippable + reversible)

### Phase 1 — pure leaves (3 hrs, low risk)
Move `canonical_company`, catalog loaders, then `score_job`. These are leaves with no module deps.

### Phase 2 — HTML templates (6 hrs, medium risk)
Move `HTML_TEMPLATE`, `WIZARD_V3_BLOCK`, sprint UI. Mechanical but the `.format()` placeholders must match new caller signatures.

### Phase 3 — scrapers (4 hrs, low risk)
Each scraper is already isolated. Move one per file.

### Phase 4 — orchestrator slim-down (1 hr, low risk)
`fetch_jobs.py` becomes the main loop only.

## Risk gates after every phase

1. `python3 tests/test_scoring.py` → 22/22 pass
2. `python3 tests/test_catalog_integrity.py` → 17/17 pass
3. `node tests/test_sprint_reminder.mjs` → 24/24 pass
4. `python3 scripts/validate_dashboard_js.py` → all scripts parse
5. `python3 fetch_jobs.py` runs + writes valid HTML
6. Diff `geetu.html` before vs after → byte-identical (pure refactor)

## Anti-goals

- Don't change scoring logic during the split
- Don't introduce a web framework
- Don't add a build step
- Don't convert to classes for class-sake

## Total estimate: 14 hours, 2-3 days, post-sprint
