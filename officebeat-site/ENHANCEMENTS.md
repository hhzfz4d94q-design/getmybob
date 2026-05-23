# OfficeBeat Website — Enhancement Recommendations

**Date:** 2026-05-22
**Working copy:** `~/Library/CloudStorage/OneDrive-AmitArora/Officebeat/Website/`
**Live source:** `~/Library/CloudStorage/OneDrive-AmitArora/Officebeat/getmemyjob/officebeat-site/` (current production)

## What's already done in this pass

1. Copied the live site into a dedicated `Website/` working folder.
2. Re-wired **every** mailto, contact form, and displayed email from `info@officebeatllc.com` to `team@officebeatllc.com` (matches the new shared mailbox).
3. Replaced the bare external "getmemyjob ↗" nav link with **Products** → `index.html#products`. getmemyjob is now positioned as an OfficeBeat product, not a random outbound link.
4. Added an **OfficeBeat Products** section to the home page with two cards: getmemyjob (alpha, with "An OfficeBeat Product" badge) and a placeholder for the in-development risk-ops tool with an early-access CTA.
5. Added a "Beyond consulting — we also build software" block to the About page that frames getmemyjob inside the OfficeBeat story.

---

## Tier 1 — Ship-this-week (conversion + credibility)

### 1. Replace mailto with a real form backend
The contact form currently opens the user's mail client (`window.location.href = 'mailto:...'`). Half of submissions die because the visitor uses Gmail in a browser, not Outlook, and the popup confuses them. Pick one of:
- **Formspree** or **Basin** (5 min, $10/mo) — point form action at their endpoint, get emails to team@ + a spam-protected dashboard.
- **Microsoft Power Automate** (free with M365) — trigger from form POST, file submissions in SharePoint, email team@.
- **Cloudflare Pages Functions** if you stay on the same host — POST handler that forwards via Resend/Postmark.

Add a real "Thank you" page (`thanks.html`) so you can wire Google Analytics / LinkedIn conversion tracking.

### 2. Add structured data (JSON-LD)
Zero SEO markup right now. Drop an `Organization` + `LocalBusiness` schema in `index.html` and `Person` schemas for Amit and Geetanjali in `about.html`. This is the single highest-ROI 30-minute change for search visibility.

### 3. Hook up analytics
No tracking installed. Add **Plausible** (privacy-first, $9/mo) or GA4 across all pages so you can see which pages convert, where visitors drop off, and whether the new Products section gets clicks.

### 4. Sitemap.xml + robots.txt
Neither exists. Both are 10-line files and required for Google Search Console submission.

### 5. Mobile-test the new Products section
The grid-2 cards I added inherit existing styles, but the badge pill ("An OfficeBeat Product") may wrap awkwardly on narrow screens. Open `index.html#products` at 375px width and verify.

---

## Tier 2 — Next sprint (positioning + lead quality)

### 6. Case studies, not just testimonials
You have two strong quotes ($2M bond interest savings, ERM transformation). Each deserves a full case-study page: situation, complication, what you did, outcomes, lessons. This is what enterprise risk buyers actually evaluate. Anonymize freely.

### 7. A real "Insights" or "Notes" section
A consultancy with no published thinking looks like a consultancy that doesn't have any. Even 4–6 short pieces (700–1200 words each) on topics like *"What the FRB's TPRM guidance actually changes for community banks"* would put you in search results for buyers actively shopping. AI-assisted drafting + your review is ~2 hours per piece.

### 8. Tighten the Risk Maturity Assessment funnel
Right now `assess.html` likely emails a result — verify it captures email, asks for company size & vertical, and triggers a follow-up sequence. The assessment is your best lead magnet; treat it like one.

### 9. Add a "What working with us looks like" page
Buyers want to know: what's the first call like? How long until a proposal? Who actually shows up to meetings? A short page with a 4-step engagement model removes anxiety for first-time consulting buyers.

### 10. getmemyjob deeper integration
Currently it's a card on home and about. Consider:
- A standalone `products.html` page that can grow as you add more products.
- A small "Featured in" or "Born from our healthcare practice" framing for getmemyjob (since the product idea came from real workforce mobility patterns Geetanjali saw).
- Decide: should getmemyjob users discover OfficeBeat consulting? Add a "An OfficeBeat product" badge in the getmemyjob app header that links back.

---

## Tier 3 — When you have bandwidth

### 11. Performance audit
- Logo PNG is **200 KB**. Compress to <30 KB (TinyPNG) or convert to SVG.
- Inline-load critical CSS for the hero section; defer the rest. Currently the entire `style.css` blocks render.
- Add `loading="lazy"` to any below-the-fold images.

### 12. Accessibility (WCAG AA)
- Run the site through Lighthouse / axe. Likely flags: button contrast on the `on-dark-primary` variant, missing `aria-label` on icon-only elements, form field `<label>` associations on assess.html.
- The "↗" arrow next to external links should be `aria-hidden="true"`.

### 13. SEO content depth
- Service pages (finance, healthcare, services) are strong but each could carry 2–3 industry-specific landing pages (e.g., `/finance/tprm-for-community-banks/`, `/healthcare/ai-program-governance/`). These are what rank.
- Add a meta keyword strategy — right now each page has solid `<title>` but identical-feeling descriptions. Vary by intent.

### 14. Trust signals
- Add LinkedIn icons next to leadership photos linking to your real profiles.
- "Frameworks we work with" logo strip: COSO, ISO 31000, NIST CSF, HIPAA, NYDFS. Visual reassurance for risk buyers.
- Bar association / professional memberships if any.

### 15. CRM wiring
Per memory, HubSpot is now the OfficeBeat CRM. Contact form submissions should land in HubSpot as new contacts with source attribution. Formspree/Basin both have native HubSpot integrations; Power Automate has a connector.

### 16. Booking link
Calendly or Microsoft Bookings link for the "Free 60-minute consultation" — let people self-serve onto your calendar instead of waiting for an email exchange. Bookings comes free with M365 once Exchange license is added.

---

## Tier 4 — Future product/brand work

### 17. Brand system documentation
Codify the color tokens (`--indigo`, `--lilac`, `--ink`, `--white`), spacing scale, type ramp, and component patterns into a single `BRAND.md` so future pages stay consistent. The visual language is already strong — it just isn't written down.

### 18. Multi-language?
If healthcare/finance clients in EMEA or LatAm matter, a Spanish or Portuguese mirror of the home page is a cheap differentiator. Skip if North America is the only target.

### 19. Status page / changelog
For getmemyjob (and the upcoming risk-ops product) — a simple status + changelog page builds product-buyer trust.

### 20. Newsletter
A monthly "Risk & Resilience Notes" newsletter — even 200 subscribers of risk officers is a meaningful lead source. Beehiiv or Substack, embed signup on `index.html` and at the end of every insight piece.

---

## Recommended next 5 actions (if you do nothing else)

1. **Switch contact form to Formspree or Power Automate** → submissions stop dying in mailto popups.
2. **Add JSON-LD structured data + sitemap + robots.txt** → Google can actually find and rank you.
3. **Install Plausible/GA4** → you'll know what's working.
4. **Compress the logo and run Lighthouse** → ~2x mobile speed improvement.
5. **Write two case-study pages** from the existing testimonials → buyers stay on the site longer and trust faster.

---

## Files modified in this pass

- `index.html` — nav (Products link), new Products section, all email → team@
- `about.html` — nav, new "Beyond consulting" section, email → team@
- `contact.html` — nav, contact form mailto target → team@, displayed email → team@
- `services.html`, `finance.html`, `healthcare.html`, `locations.html`, `assess.html` — nav, footer email → team@
- All `*.html` — `info@officebeatllc.com` → `team@officebeatllc.com` (19 instances)

No CSS changes — new sections reuse existing classes.
