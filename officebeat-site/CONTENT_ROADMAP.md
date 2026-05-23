# OfficeBeat Website — Content, Flow & Look/Feel Roadmap

**Date:** 2026-05-22
**Working copy:** `~/Library/CloudStorage/OneDrive-AmitArora/Officebeat/Website/`

---

## TL;DR

The site has a strong skeleton — clear verticals, clean design language, a working contact funnel into HubSpot. What's missing is the **middle of the funnel**: pages that turn a curious visitor into a qualified inquiry. The fixes split into three buckets:

1. **More service depth pages** (like the new `treasury.html`) — one per major offering, for SEO and buyer confidence
2. **Trust and proof pages** — case studies, insights, individual practitioner bios — buyers don't trust the homepage alone
3. **Polish layer** — small look-and-feel upgrades that make the site feel like a top-tier boutique, not a template

I've done the Treasury Solutions page already. Below is everything else, prioritized.

---

## What's live now (post-2026-05-22 build)

| Page | Purpose | Status |
|---|---|---|
| `index.html` | Brand + verticals + featured offerings + Products + dark landscape + approach + testimonials | Live |
| `finance.html` | Finance vertical: why-it-matters + outcomes + 4-tab service catalog | Live |
| `healthcare.html` | Healthcare vertical: same structure as Finance | Live |
| `services.html` | Cross-vertical service catalog with tabs + Treasury feature | Live |
| `treasury.html` | **NEW** — Dedicated Treasury Solutions practice page | Live |
| `assess.html` | Risk Maturity Assessment lead magnet | Live (now wired to HubSpot) |
| `about.html` | Who we are + leaders + principles + Products mention | Live |
| `locations.html` | Office locations | Live |
| `contact.html` | Contact form (live HubSpot integration) | Live |
| `thanks.html` | Post-submission confirmation | Live |

---

## Recommended new pages — priority order

### Tier 1 — Builds trust and ranks in search (do these next)

**1. `case-study-bank-erm.html`** — A full case study built from the "Chris B., SVP, Medium-sized Bank" testimonial. Story arc: situation → complication → what we did → outcomes. Anonymized. ~1200 words.

**2. `case-study-credit-rating.html`** — Built from the "Alex D., CISO, Midsized Bank" testimonial — the $2M bond-interest savings story. This one's the money case study; it's what banking buyers actually want to read.

**3. `insights.html`** — Index page for thought-leadership pieces. Even with 4–6 short pieces (700–1200 words each) it changes how the site shows up in search. Topics to start: "What the FRB's TPRM guidance changes for community banks," "AI program governance for healthcare — the under-discussed risks," "Real-time payments: the operational risks you're not pricing in," "ERM at the $50M revenue mark — what to actually build first." Each piece is a separate HTML file linked from `insights.html`.

**4. `how-we-work.html`** — Removes anxiety for first-time consulting buyers. What's the first call like? Who shows up to meetings? How fast is the proposal? What does week 1 look like? A 4-step engagement model with timing and named deliverables.

**5. `tprm.html`** — Dedicated Third-Party Risk Management page. Same structure as `treasury.html`. TPRM is one of the highest-search-volume topics in your space and you have deep expertise here.

**6. `cyber-risk.html`** — Dedicated cyber / NIST CSF maturity page. Big regulatory tailwind. Match the treasury.html template.

### Tier 2 — Healthcare depth (when you're ready to push that vertical harder)

**7. `ehr-strategy.html`** — Dedicated EHR & SaaS product strategy page. Geetanjali's signature offering. High-value mid-market healthcare SaaS buyers.

**8. `ai-program-governance.html`** — AI governance for healthcare and finance, framed as risk-adjacent. This is where the puck is going.

**9. `digital-transformation.html`** — Healthcare digital transformation, Pfizer-scale lessons. Mid-market healthcare CIOs will eat this up.

### Tier 3 — Brand & team

**10. `amit-arora.html`** — Full practitioner bio with selected client list, speaking history, publications. Search-rankable for the name.

**11. `geetanjali-arora.html`** — Same.

**12. `careers.html`** — Even a simple "We're not hiring right now, but here's what we look for" page. Signals you're a real firm.

**13. `news.html`** — Press, podcast appearances, conference talks. Even one or two items make a difference.

### Tier 4 — Conversion infrastructure (smaller pages that punch above their weight)

**14. `pricing.html`** OR `engagement-models.html` — Buyers desperately want to know what things cost. Even ranges + "depends on" framing helps. Many will skip you if they have to ask.

**15. `faq.html`** — Cross-cutting FAQ. Anchor links so search results can deep-link.

**16. `partners.html`** — Frameworks you align to (COSO, ISO 31000, NIST CSF, FFIEC, HIPAA, NYDFS) + GRC platforms you implement (ServiceNow, Archer, MetricStream, Kyriba, GTreasury). Visual logo strip.

**17. `privacy.html` + `terms.html`** — Required for HubSpot form compliance and B2B credibility. Use a generator and adapt.

---

## Information architecture — recommended nav structure

The current nav has 7 items: Home, Finance, Healthcare, Products, Services, Locations, Contact. That's already at the edge of comfortable. Three options:

### Option A — Add Insights, keep Locations (8 items, tight)

```
Home  ·  Finance  ·  Healthcare  ·  Services  ·  Insights  ·  Products  ·  Locations  ·  Contact
```

### Option B — Mega-menu (recommended)

```
Home  ·  Verticals ▾  ·  Services ▾  ·  Insights  ·  About ▾  ·  Contact
```

Where the dropdowns are:

- **Verticals ▾** → Finance · Healthcare · Treasury · TPRM · Cyber · EHR Strategy · AI Governance
- **Services ▾** → Risk Maturity Assessment · Crisis Simulations · Continuous Advisory · BCP/DR · How We Work · Pricing
- **About ▾** → Who We Are · Amit Arora · Geetanjali Arora · Products · Locations · Careers · News

This keeps the top bar at 6 items, surfaces everything within one hover, and signals depth.

### Option C — Footer-heavy

Keep the current 7-item nav, but expand the footer into a full site map with all the new pages organized by section. Less effort, less visible, but works.

**Recommended:** Option B. Mega-menus are now expected on consultancy sites and don't add visual weight.

---

## Site flow — the journey we want visitors to take

```
LANDING (Home, finance.html, healthcare.html, treasury.html via search/referral)
   ↓
PROOF (case study OR insights piece OR specific service page)
   ↓
DIAGNOSTIC (Risk Maturity Assessment) OR DIRECT (Contact)
   ↓
THANKS → HubSpot lead → 1 business day response
```

The current site has the "Landing → Contact" path covered. What's missing is the **Proof** middle step. That's why case studies + insights are Tier 1.

Specific flow upgrades to add:

- **End every service page with a "Recommended next read" block.** Example: on `treasury.html`, link to the credit-rating case study and the "Real-time payments operational risks" insight piece.
- **Add a sticky "Take the Assessment" CTA** on long pages — pinned to bottom-right on desktop, slide-up on mobile. Currently visitors have to scroll back up to act.
- **Add scroll-progress indicator** on insight pages (a thin colored bar at the top). Visible signal of "you're 60% through, keep going."

---

## Look & feel upgrades

The current design language is good. These are small upgrades that add polish without redesigning.

### Visual polish

1. **Logo compression** — current PNG is 200 KB. Convert to SVG or compress to <30 KB. Single biggest perf win.
2. **Replace the orange Submit button** (HubSpot default) with the indigo brand button — HubSpot Forms lets you style this via the embed CSS overrides.
3. **Add subtle illustration accents** — practice-area icons currently use letter monograms (`$`, `+`, `RM`). Upgrading 6–10 to thin-line custom SVG icons (Heroicons or custom) feels notably more premium for ~2 hours of work.
4. **Hero photography** — the finance page has a banking-floor image strip. Add equivalent for healthcare (hospital corridor / clinical-tech) and treasury (trading floor / payments). Stock photography is fine if curated tightly.
5. **Practitioner photos** — currently the about page uses initials (`AA`, `GA`). Real headshots in the same circular treatment is a 10× trust improvement.
6. **Animated counter on stats** — when `35+`, `$15M+`, `20+` scroll into view, animate them from 0. Small touch, signals craft.
7. **Subtle scroll-reveal animations** — fade-in-from-below on section enter. Use `IntersectionObserver`, ~20 lines of JS.

### Typography & spacing

8. **Tighten the hero h1 line-height** — at 40px+ the current line-height feels loose; reduce by 0.05–0.1.
9. **Increase vertical rhythm between sections** to 96px on desktop (currently 64–80). Premium consulting sites tend toward more whitespace.
10. **Standardize all eyebrow tags to uppercase tracked letters** — already mostly there, just audit consistency.

### Components to add

11. **Trust logo strip** — even three or four anonymized client industries ("Banking · Healthcare SaaS · Asset Management") with subtle borders. If permitted, real client logos. Sits between hero and verticals.
12. **Testimonial slider** — current testimonials are static cards. A small carousel with 4–6 testimonials and pause-on-hover feels more dynamic.
13. **"As featured in" or "Frameworks we work with" strip** — COSO, ISO 31000, NIST CSF, HIPAA, NYDFS logos. Sits before footer.
14. **Inline calendar booking** — embed a Microsoft Bookings (free with M365) or Calendly link as a "Book a 60-minute consult" button on the contact page that opens an inline scheduler instead of an email exchange.

### Accessibility (WCAG AA quick wins)

15. Run a Lighthouse pass. Likely fixes: `aria-hidden` on decorative icons, button contrast on the orange variant, missing skip-to-content link.
16. Ensure all images have descriptive `alt` text (not just "OfficeBeat LLC" everywhere).

---

## Suggested 2-sprint plan

### Sprint 1 (next 2 weeks)

- Build `case-study-credit-rating.html` and `case-study-bank-erm.html` — biggest trust unlock
- Build `tprm.html` (cloned from treasury.html template)
- Build `how-we-work.html`
- Logo compression + image alt-text audit
- Add `privacy.html` + `terms.html` (compliance unblock for any future EU traffic)

### Sprint 2 (weeks 3–4)

- Stand up `insights.html` + write 4 articles (AI assisted, ~2 hours per article)
- Build `cyber-risk.html`
- Build `amit-arora.html` + `geetanjali-arora.html`
- Replace letter-monogram icons with custom SVG line icons
- Add real practitioner headshots

### Later

- Mega-menu nav rebuild (Option B above)
- Testimonial slider + trust strip + scroll-reveal animations
- Healthcare-specific deep pages (`ehr-strategy.html`, `ai-program-governance.html`)

---

## What's in this changeset

- `treasury.html` — new dedicated service page (full hero, services grid, FAQ, CTA)
- `finance.html` — Treasury Solutions card now links into `treasury.html` and has a "Explore →" affordance
- `services.html` — added a "Featured Practice Page: Treasury Solutions" block under Quick-start offerings
- `sitemap.xml` — Treasury page added
- This document — `CONTENT_ROADMAP.md`
