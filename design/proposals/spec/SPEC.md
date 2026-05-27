# OfficeBeat × getmemyjob — Modernization Spec

**Status:** Proposal · ready for review
**Author drafted:** 2026-05-27
**Surface area:** Both sites (officebeatllc.com + getmemyjob.officebeatllc.com)
**Tone target:** Confident-modern (Linear / Notion / Vercel)

This document captures the design decisions for modernizing the two sites,
the artifacts produced as the spec, and a phased rollout plan. It's a
companion to:

```
/design/proposals/
├── tokens/tokens.css                ← single source of truth for color, type, space
├── prototypes/wizard-v4-prototype.html   ← interactive 4-step prototype
├── images/PHILOSOPHY.md             ← "Signal Field" visual language
├── images/01_gmj_bullseye.png       ← getmemyjob hero
├── images/02_gmj_dashboard_grid.png ← dashboard UI specimen
├── images/03_ob_signal_field.png    ← officebeat hero
├── images/04_ob_finance_card.png    ← Finance vertical card
└── images/05_ob_health_card.png     ← Healthcare vertical card
```

---

## 1. Why now

The 142-assertion E2E suite is green. The matcher works. The mobile fixes
shipped today closed the last UX gaps the test layer caught. What remains
unflattering is the visual layer — and it is the layer a stranger judges
first. The audit (see `/design/proposals/AUDIT.md`) surfaced three
underlying problems that no amount of further code-quality work will fix:

1. **Three sources of truth for design tokens.** `officebeat-site/assets/style.css`,
   `landing.html`, and `fetch_jobs.py` each define brand color and type
   differently. Landing.html literally renames `#5C5CD6` to "navy". Anyone
   touching design will guess wrong.
2. **Zero real imagery anywhere.** 0 hero photos, 0 illustrations, 0
   icons across the entire system. Marketing pages render as text-on-color
   blocks. Numbers and 3-letter glyphs ("ERM", "PM", "M&A") substitute
   for an icon system.
3. **The product feels different from the marketing site.** The
   dashboard's flat indigo header bar collides with the white logo bar
   above it. The wizard uses three different fonts of indigo gradient
   none of which match the marketing site's hero. A user arriving via
   `officebeat-site/index.html → getmemyjob.officebeatllc.com/landing.html
   → wizard → dashboard` experiences four distinct visual languages.

This spec proposes one design system, one visual language ("Signal Field"),
a redesigned wizard, and concrete imagery — all coherent across both sites.

---

## 2. Design decisions (locked)

| Question | Decision | Why |
|---|---|---|
| Visual tone | Confident-modern (Linear / Notion / Vercel) | Works for both sites — restrained enough for enterprise buyers on officebeat, modern enough for SaaS-fluent job seekers on getmemyjob. Avoids the "playful gradient mush" trap. |
| Wizard scope | Layout + interaction overhaul (keep 9 steps + save logic) | Step structure was just consolidated and stabilized. Don't re-litigate it. Modernize the visual + interaction layer only. |
| Imagery | Mix — hero photography + UI geometric | Photo for emotional connection on heroes, geometric Cairo-rendered art for product UI specimens and feature cards. Best of both. |
| Output | `/design/proposals/` in this repo + workspace folder | Versioned alongside code; reviewable as one PR; available on Amit's computer. |

These are the inputs every artifact below was built against.

---

## 3. The design system

**File:** `design/proposals/tokens/tokens.css` — 216 lines, single source of truth.

The system has three layers:

### a. Brand tokens — shared by both sites

`--brand-indigo: #5C5CD6` (preserved exactly), plus a calibrated scale of
indigo from `-50` through `-700` for surfaces, hovers, focus rings, and
the deep mark variant. Five status colors (track-applied, track-onsite,
track-offer, etc.) for the dashboard's kanban-style chips. Seven
neutral greys. Each token has a defined role and is referenced by name —
**no hex literals anywhere downstream.**

### b. Vertical accents — NEW

To solve the audit's "Finance vs Healthcare are visually indistinguishable"
issue, two secondary accents enter the system:

- `--vertical-finance: #1F2C6F` (deep navy) — gravitas, capital markets
- `--vertical-health:   #0E8C7A` (emerald-teal) — care, life sciences

Each pairs with a tint surface (`-50` variant). They are applied via a
`data-surface="finance"` attribute on `<body>`, not as overrides
scattered through CSS. One line of HTML changes the entire page's accent
without touching any other rule.

### c. Surface variants

Same mechanism: `data-surface="product"` flips the page background to
the warmer `--surface-soft`, signaling "this is the app, not the
marketing site". The dashboard gets this attribute, the marketing pages
don't.

The full token list (type scale, space scale 4px-base, radius, shadow,
motion, z-index ladder) is in `tokens.css` with inline rationale.

**What ships:** This one file replaces three competing definitions.

---

## 4. The visual language — "Signal Field"

**File:** `design/proposals/images/PHILOSOPHY.md`

The visual identity for both sites. Five-paragraph manifesto worth
reading in full, but the short version: both products extract meaning
from noise (the job market for getmemyjob, regulatory and operating
complexity for officebeat). The visual system makes that act of
attention legible.

White is the dominant material. Color is reserved — a single intentional
indigo per composition. Geometry is precise: concentric rings, rhythmic
bars, lattice grids, and rectilinear card architectures borrowed from
scientific observation. Typography is small, monolinear, almost ashamed
of itself. Every element earns its place. Nothing is glossed, beveled,
or made to feel "fun." The work is serious because what the products do
— careers, risk, care — is serious.

Five plates render this language:

| Plate | Subject | Use |
|---|---|---|
| `01_gmj_bullseye.png`       | Concentric target with 5 matched dots at the center, 60 candidate dots scattered through the noise floor | getmemyjob marketing hero / OG share image |
| `02_gmj_dashboard_grid.png` | 15-card grid with score chips and 3-bar match breakdowns | Marketing-page screenshot stand-in; in-app dashboard reference |
| `03_ob_signal_field.png`    | Spectrum of grey "noise" bars with 5 indigo "signal" peaks, callout on the TPRM peak | officebeat marketing hero |
| `04_ob_finance_card.png`    | Deep-navy field with a layered waveform; bottom strata lists 6 practices | Finance vertical landing card |
| `05_ob_health_card.png`     | Emerald field with a braided lattice and 5 node markers; bottom lists 6 practices | Healthcare vertical landing card |

Every plate is generated by `images/generate.py` (Python + Cairo). Re-runnable
on demand if copy changes; no Figma round-trip needed.

**What ships:** PNGs above + the Python source so future updates are a
re-run, not a redraw.

---

## 5. Hero photography (recommendation, not generated)

The "mix" decision means heroes get real photography. Canvas-design
generates the geometric UI specimens; for the people-and-place
photography, here is what to source rather than generate:

**officebeat hero:** A wide, calm photo of a serious workspace —
preferably one that reads as a financial-services boardroom or hospital
strategy room without being literal. Avoid stock-photo handshake
clichés. Recommended sources: Unsplash collections "boardroom",
"hospital architecture", "NYC interior"; or commission a single
half-day shoot of a real NYC consulting office. ~$800-1500 commissioned,
free from Unsplash with attribution.

**getmemyjob hero:** A photo of a focused person at a laptop in their
own space (kitchen table, café, home office). Diverse, mid-career,
slightly post-frustration. The geometric bullseye plate (`01_gmj_bullseye.png`)
overlays as a translucent panel at right.

Treatment in both cases: photo at 60-70% width, white panel containing
the headline at left, indigo accent line under the eyebrow. Use a 1px
overlay at 12% opacity to slightly desaturate and unify across photos.

**What ships in this phase:** Recommendations + the geometric heroes
that work as standalone hero treatments if photos aren't ready yet.

---

## 6. Wizard v4 — interaction overhaul

**File:** `design/proposals/prototypes/wizard-v4-prototype.html`

Open it in any browser. Click the four demo buttons at the top to walk
through Resume / Bullseye / Scoring / Done. The compositions and
interaction patterns are exactly what ships, scaled to fit one HTML file
without needing a server.

### What changes vs v3 (which is what's in production today)

**Step 2 — Resume upload.** Today: hidden file input behind a small
"Upload" button. v4: full-width drop zone with explicit file-type chips,
explicit local-parsing copy ("we parse locally, your file never leaves
your browser"), and a "paste text instead" affordance below the OR
divider. Bigger affordance, less ambiguity, instant trust signal.

**Step 3 — Bullseye.** Today: a 4-section vertical scroll across
titles → industries → skills → companies. v4: all four pickers visible
on one canvas (2×2 grid on desktop, stacked on mobile). The active
section is highlighted with a soft indigo glow. Counters use color to
signal state: indigo = picking, green = at cap, red = over cap. **The
new piece** is a **live Top-5 preview** at the bottom that re-renders
each time the user adds or removes a pick. The preview rows animate in
with a 60ms stagger so the cause-and-effect is immediately visible.
Users see the matcher react, which is the entire point of the wizard.

**Step 5 — Scoring tune.** Today: three sliders with a sum-to-100
check. v4: same three sliders, but next to a **live waterfall** showing
how a sample job (top match) scores under the current weights. Move a
slider, the bars and the final number animate. Users can finally
understand what "title weight 30" actually buys them.

**Step 9 — Done.** Today: a green checkmark and a "Finish" button. v4:
a confidence-building summary card showing top-match preview, average
top-5 score, warm-intro count, and corpus coverage. Reassures the user
the matcher actually works before they leave the wizard.

### Shared chrome improvements

- **Progress orb** in the rail brand mark — conic-gradient that fills as
  steps complete. Cheap, distinctive, replaces the abstract "step 3 of
  9" with a glanceable signal.
- **Step rail** uses a checkmark in a green pill for completed steps and
  an indigo pill for the current step. Hover highlights any step
  (already-supported jump-to behavior, just visually clarified).
- **Footer** keeps the existing Back / Skip / Continue layout but with
  the modernized button styles. Skip is correctly hidden on required
  steps (the test we hardened earlier).
- **Esc to close** with the inline reminder in the rail footer. Discoverable
  keyboard support.

### What does NOT change

- 9-step structure
- State management / persistence
- Save handlers / patchProfile
- Auth flow (the dual-key fix we shipped today stays)
- Mobile media-query strategy (already passing E2E)

The redesign is **scoped to the visual + interaction layer of the wizard
HTML/CSS rendered by `WIZARD_V3_BLOCK` in `fetch_jobs.py`.** No Python
logic changes. No worker changes.

**What ships:** The prototype is reference; production work is to port
its patterns into `WIZARD_V3_BLOCK` and `HTML_TEMPLATE`. Roughly 220
lines of CSS-in-Python-string get replaced/extended; one new helper
function for the live preview; one for the waterfall. The existing E2E
suite continues to gate the changes.

---

## 7. Cross-site polish (lower priority, included for completeness)

These come out of the audit and are worth queueing once the wizard +
tokens ship:

- **Real icon set everywhere** — Lucide (MIT-licensed, ~1KB per icon
  inline). Replaces emoji on `landing.html`, 3-letter glyphs on
  `finance.html` / `healthcare.html`, and digit-icons on
  `index.html`'s stat strip.
- **Componentize nav + footer.** Currently duplicated 60-line nav and
  25-line footer across ~25 marketing pages. One Cloudflare Pages
  Function (or a tiny build step) lets one edit ship everywhere.
- **Real mobile menu.** Marketing nav at ≤640px wraps to two rows of
  pills today. A proper hamburger drawer (shared via the
  componentization above) lands once.
- **Kill dead code:** wizard v2 markup in `HTML_TEMPLATE`, the unreachable
  `landing.html` sign-in modal, six near-empty stub pages
  (`cyber-risk.html` et al.).
- **Move dashboard CSS out of Python** to dashboard.css / wizard.css,
  importing `tokens.css`. ~440 lines of CSS-in-string become real CSS
  files with autocomplete and linting.
- **App-shell unification.** The dashboard's stacked white-logo-bar +
  flat-indigo-title-bar collapses into one cohesive header with logo,
  page title, and user menu on a single row.

These can ship piecemeal. None of them depend on Phase 1.

---

## 8. Rollout plan

### Phase 1 — Tokens + Wizard v4 (this week, ~3-4 hrs)

Goal: every pixel of the wizard ships against the unified design system.
Marketing site keeps its current style until Phase 2; for now we just
prove the tokens by deploying them in the highest-traffic product
surface.

Steps:
1. Drop `tokens.css` at `getmybob-repo/design/proposals/tokens/tokens.css`
   (already done — this PR).
2. Open a follow-up PR that:
   - Adds `<link rel="stylesheet" href="/design/tokens.css">` to
     `landing.html`, `account.html`, `login.html`, `signup.html`, and
     the `<head>` rendered by `HTML_TEMPLATE` in `fetch_jobs.py`.
   - Replaces hex literals in `fetch_jobs.py` WIZARD_V3_BLOCK with
     `var(--brand-indigo)` etc. Mechanical search-and-replace.
   - Ports the four prototype patterns into `WIZARD_V3_BLOCK`:
     dropzone, bullseye canvas, scoring waterfall, done card.
   - Updates the JS gate test if needed.
3. Run live E2E. Expect 142/142 still green; add ~5 new assertions for
   the new patterns (live-preview-renders, waterfall-updates,
   dropzone-accepts-drop).

### Phase 2 — Marketing site polish (next sprint, ~5-8 hrs)

Steps:
1. Replace `:root` in `officebeat-site/assets/style.css` with an
   `@import "/design/tokens.css"` (or copy the file in).
2. Add the vertical-accent data attributes to Finance and Healthcare
   pages.
3. Drop the geometric heroes (`03`/`04`/`05`) as actual SVG/PNG into
   `officebeat-site/assets/` and wire into respective page heroes.
4. Componentize nav + footer (Cloudflare Pages Function).
5. Hamburger drawer for the new shared nav.
6. Add Lucide icon set; replace text/digit "icons".
7. Sweep the 6 stub pages — fill or 301-redirect.

### Phase 3 — Photography + finishes (when ready, ~1 day)

Steps:
1. Commission or curate the two hero photos per the recommendations in
   §5. Drop into `assets/`.
2. Replace geometric heroes on the home and product pages with the
   photo + headline-card composition; keep geometric heroes on
   secondary pages (verticals, About, etc.) where photos would feel
   gratuitous.
3. Final cross-browser pass.

---

## 9. Success criteria

How we know this worked:

1. **All 142 existing E2E assertions still pass** after Phase 1 ships.
   (Hard gate.)
2. **New assertions** added for wizard v4 patterns (~5-8) pass.
3. **Lighthouse score** for `getmemyjob.officebeatllc.com/amit-arora`
   improves on Performance and Accessibility by ≥5 points each.
4. **Zero new hex literals** introduced anywhere (lint rule: forbid
   `#[0-9a-fA-F]{3,6}` outside `tokens.css`).
5. **One-line** vertical accent change — switching Finance from navy
   to a different blue means editing one line in `tokens.css`, not
   scattered overrides.
6. **Subjective:** Amit can show the dashboard to a healthcare exec
   without explaining "it's an early version."

---

## 10. What this spec does NOT cover

- Marketing copy. Voice, headlines, CTAs — separate exercise.
- Pricing page. The audit flagged it as a stub; needs business input.
- The Chrome extension UI. Hardware-keyed, different surface.
- Analytics / conversion tracking. Worth doing alongside Phase 2.
- Admin console redesign (`admin.html`). Low-traffic; tokens will
  cover the basics, fuller redesign later.

---

## Appendix A — Files in this proposal

| Path | Purpose |
|---|---|
| `design/proposals/spec/SPEC.md` | This document |
| `design/proposals/tokens/tokens.css` | The unified token system |
| `design/proposals/prototypes/wizard-v4-prototype.html` | Interactive wizard prototype, click through 4 steps |
| `design/proposals/images/PHILOSOPHY.md` | "Signal Field" manifesto |
| `design/proposals/images/generate.py` | Cairo source for the 5 plates — re-run to regenerate |
| `design/proposals/images/01_gmj_bullseye.png` | getmemyjob hero |
| `design/proposals/images/02_gmj_dashboard_grid.png` | Dashboard UI specimen |
| `design/proposals/images/03_ob_signal_field.png` | officebeat hero |
| `design/proposals/images/04_ob_finance_card.png` | Finance vertical |
| `design/proposals/images/05_ob_health_card.png` | Healthcare vertical |

## Appendix B — How this spec was built

A multi-stage pass with one agent: site audit (general-purpose subagent
reading both code bases) → token system (single CSS file with three
source-of-truth files retired) → interactive prototype (single-file
HTML, matches the vanilla-JS production stack) → philosophy and image
generation (Python Cairo, parametric, re-runnable) → this document.
Total elapsed: ~3 hours wall-clock.

The thinking and process behind each decision are in the git log of
`design/proposals/`. The audit findings are in
`design/proposals/AUDIT.md` (not committed yet — that was an in-session
subagent run; full text is available in the conversation log if anyone
wants it preserved alongside the spec).
