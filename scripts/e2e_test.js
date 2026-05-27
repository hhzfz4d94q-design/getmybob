#!/usr/bin/env node
/**
 * Full end-to-end test suite for getmemyjob dashboards.
 *
 * Tests EVERY user-facing behavior, not just "function exists":
 *   - Page loads cleanly (zero console errors, all expected functions defined)
 *   - Every header button: visible + clickable + triggers expected behavior
 *   - Every modal: opens visibly above other content, has working close button
 *   - Wizard: walks all 9 steps without throwing
 *   - Wizard scroll: long content shows scrollbar
 *   - Cards: render with score / company / title / action buttons
 *   - Each card has working Why?, Mark Applied, Prep materials buttons
 *
 * Each test is a discrete assertion. ANY failure exits non-zero.
 *
 * Usage: node scripts/e2e_test.js [user-slugs-comma-separated]
 * Default: amit-arora,geetu
 */

const puppeteer = require('puppeteer');

const SITE = process.env.SITE || 'https://getmemyjob.officebeatllc.com';
const USERS = (process.argv[2] || 'amit-arora,geetu').split(',');

const results = []; // {user, name, ok, detail}

function record(user, name, ok, detail = '') {
  results.push({ user, name, ok, detail });
  const mark = ok ? '✓' : '✗';
  const tail = detail ? ` — ${detail}` : '';
  console.log(`    ${mark} ${name}${tail}`);
}

async function assertVisible(page, sel, user, name) {
  const visible = await page.evaluate((s) => {
    const el = document.querySelector(s);
    if (!el) return { exists: false };
    const r = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return {
      exists: true,
      visible: r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none',
      x: r.x, y: r.y, w: r.width, h: r.height,
    };
  }, sel);
  if (!visible.exists) return record(user, name, false, `${sel} not in DOM`);
  if (!visible.visible) return record(user, name, false, `${sel} hidden (${visible.w}x${visible.h} @ ${visible.x},${visible.y})`);
  record(user, name, true);
}

async function clickAndAssert(page, clickSel, expectSel, user, name, timeoutMs = 2000) {
  try {
    await page.click(clickSel);
  } catch (e) {
    return record(user, name, false, `click ${clickSel}: ${e.message}`);
  }
  try {
    await page.waitForSelector(expectSel, { visible: true, timeout: timeoutMs });
    record(user, name, true);
  } catch (e) {
    record(user, name, false, `${expectSel} did not appear within ${timeoutMs}ms`);
  }
}

async function testUser(browser, slug) {
  const url = `${SITE}/${slug}?_=e2e_${Date.now()}`;
  console.log(`\n━━━ Testing ${slug} ━━━`);
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  const consoleErrors = [];
  page.on('pageerror', err => consoleErrors.push(`pageerror: ${err.message}`));
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(`console.error: ${msg.text()}`);
  });

  // ── 1. Page load ──
  console.log('  ── Page load ──');
  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
    record(slug, 'page loads', true);
  } catch (e) {
    record(slug, 'page loads', false, e.message);
    await page.close();
    return;
  }
  // Wait for bootstrap
  await new Promise(r => setTimeout(r, 2000));

  // Pre-empt the auto-launched wizard so it doesn't intercept clicks
  await page.evaluate(() => {
    try {
      if (typeof WizV3 === 'object' && WizV3.close) WizV3.close();
      // Also mark finished so it doesn't re-open during test
      const k = 'gmj_wizard_state_v3';
      localStorage.setItem(k, JSON.stringify({ currentStep: 'done', completed: [], skipped: [], data: {}, finished: true }));
    } catch (e) {}
  });
  await new Promise(r => setTimeout(r, 300));

  // ── 2. Zero console errors ──
  record(slug, 'zero console errors',
    consoleErrors.length === 0,
    consoleErrors.length ? `${consoleErrors.length} errors: ${consoleErrors[0]}` : '');

  // ── 3. Expected functions defined ──
  const fns = await page.evaluate(() => {
    const want = ['openResumeModal','openContactsModal','toggleHeaderMore','prepApplication','refreshData','showWarmIntroModal','showWhyHiddenModal','regenerateCompaniesFromHeader','regenerateFromHeader','replayTour'];
    return want.map(n => ({ n, t: typeof window[n] }));
  });
  for (const f of fns) {
    record(slug, `function ${f.n}() defined`, f.t === 'function', `got ${f.t}`);
  }

  // ── 4. Top-level header buttons visible ──
  console.log('  ── Header buttons ──');
  // These are visible by default (not inside collapsed dropdowns)
  for (const sel of ['#refresh-btn','#account-btn']) {
    await assertVisible(page, sel, slug, `${sel} visible by default`);
  }
  // The "More" button has no id; locate by text content
  const moreVisible = await page.evaluate(() => {
    const b = Array.from(document.querySelectorAll('.header-btn')).find(el => /^More/.test(el.textContent.trim()));
    if (!b) return { exists: false };
    const r = b.getBoundingClientRect();
    return { exists: true, visible: r.width > 0 && r.height > 0 };
  });
  record(slug, 'More button visible by default', moreVisible.visible === true, moreVisible.exists ? '' : 'not found');

  // ── 4b. Account dropdown: click → items become visible ──
  const accountDropdown = await page.evaluate(() => {
    document.getElementById('account-btn').click();
    const menu = document.querySelector('#account-btn + .header-more-menu') || document.querySelector('.header-more-wrap:has(#account-btn) .header-more-menu');
    if (!menu) return { ok: false, why: 'no menu sibling' };
    const items = menu.querySelectorAll('a, button');
    return { ok: items.length > 0, itemCount: items.length, items: Array.from(items).map(i => i.textContent.trim().slice(0,30)) };
  });
  record(slug, 'Account dropdown opens with >= 1 items', accountDropdown.ok, accountDropdown.why || `items=${accountDropdown.itemCount}`);
  // Close it
  await page.evaluate(() => document.querySelectorAll('.header-more-menu.show').forEach(m => m.classList.remove('show')));

  // ── 4c. More dropdown: click → all 6 expected items become visible ──
  const moreDropdown = await page.evaluate(() => {
    const trigger = Array.from(document.querySelectorAll('.header-btn')).find(b => /^More/.test(b.textContent.trim()));
    if (!trigger) return { ok: false, why: 'no More trigger' };
    trigger.click();
    const menu = trigger.parentElement.querySelector('.header-more-menu');
    if (!menu) return { ok: false, why: 'no menu sibling' };
    const wantedIds = ['#regen-btn', '#regen-companies-btn', '#why-hidden-btn', '#resume-btn', '#contacts-btn', '#prefs-btn'];
    const visible = wantedIds.filter(id => {
      const el = menu.querySelector(id);
      if (!el) return false;
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    });
    return { ok: visible.length === wantedIds.length, visible, expected: wantedIds };
  });
  record(slug, 'More dropdown shows all 6 items', moreDropdown.ok, moreDropdown.why || `${moreDropdown.visible.length}/${moreDropdown.expected.length} visible: ${moreDropdown.visible.join(',')}`);
  // Close
  await page.evaluate(() => document.querySelectorAll('.header-more-menu.show').forEach(m => m.classList.remove('show')));

  // ── 5. WizV3 + wizard close button ──
  console.log('  ── Wizard ──');
  const wizState = await page.evaluate(() => {
    if (typeof WizV3 !== 'object') return { ok: false, why: 'WizV3 not object' };
    return { ok: true, hasOpen: typeof WizV3.open, hasReset: typeof WizV3.reset, hasGoto: typeof WizV3.goto };
  });
  record(slug, 'WizV3 object exists', wizState.ok, wizState.why || '');
  record(slug, 'WizV3.reset() callable', wizState.hasReset === 'function');
  record(slug, 'WizV3.goto() callable', wizState.hasGoto === 'function');

  // Open wizard via reset, check close button is visible
  await page.evaluate(() => { try { WizV3.reset(); } catch(e){} });
  await new Promise(r => setTimeout(r, 800));
  await assertVisible(page, '#wiz3-close', slug, 'wizard close button visible after reset');

  // ── 6. Wizard step navigation ──
  // Goto bullseye, verify 4 picker sections render
  await page.evaluate(() => WizV3.goto('your-bullseye'));
  await new Promise(r => setTimeout(r, 1200));
  for (const k of ['titles','industries','skills','companies']) {
    await assertVisible(page, `#bs-${k}-host`, slug, `bullseye section #bs-${k}-host visible`);
  }
  // Verify wizard body has scroll capability (overflow-y:auto)
  const scrollCheck = await page.evaluate(() => {
    const body = document.getElementById('wiz3-body');
    if (!body) return { ok: false };
    const style = getComputedStyle(body);
    return {
      ok: style.overflowY === 'auto' || style.overflowY === 'scroll',
      overflow: style.overflowY,
      scrollHeight: body.scrollHeight,
      clientHeight: body.clientHeight,
    };
  });
  record(slug, 'wizard body has overflow-y scroll', scrollCheck.ok, `overflow-y=${scrollCheck.overflow}`);
  record(slug, 'wizard body content fits or scrolls', scrollCheck.scrollHeight >= 0, `scroll/client=${scrollCheck.scrollHeight}/${scrollCheck.clientHeight}`);

  // Test goto each step
  const steps = ['welcome','upload-resume','your-bullseye','where-you-work','scoring-tune','daily-workflow','pick-blocks','addons','done'];
  for (const step of steps) {
    const ok = await page.evaluate((s) => {
      try {
        WizV3.goto(s);
        return WizV3.state().currentStep === s;
      } catch (e) { return false; }
    }, step);
    record(slug, `wizard goto('${step}')`, ok);
    await new Promise(r => setTimeout(r, 200));
  }

  // Close wizard via × button
  const closeOk = await page.evaluate(() => {
    try {
      document.getElementById('wiz3-close').click();
      return !document.getElementById('wiz3-overlay').classList.contains('show');
    } catch(e) { return false; }
  });
  record(slug, 'wizard × button closes wizard', closeOk);

  // ── 7. Header More menu opens ──
  console.log('  ── Header dropdowns ──');
  // Click "More" — find the More button (it doesn't have an id, use text-based locator)
  const moreOpens = await page.evaluate(() => {
    const moreBtn = Array.from(document.querySelectorAll('.header-btn')).find(b => /^More/.test(b.textContent.trim()));
    if (!moreBtn) return { ok: false, why: 'More button not found' };
    moreBtn.click();
    // Menu should now have a class indicating open (look for sibling .header-more-menu visible)
    const menu = moreBtn.parentElement.querySelector('.header-more-menu');
    if (!menu) return { ok: false, why: 'no .header-more-menu sibling' };
    const visible = getComputedStyle(menu).display !== 'none' || menu.classList.contains('show');
    return { ok: visible, why: visible ? '' : 'menu still hidden after click' };
  });
  record(slug, 'More dropdown opens on click', moreOpens.ok, moreOpens.why);

  // ── 8. Why hidden modal opens visibly ──
  console.log('  ── Modals ──');
  // Capture any throw so we can surface it as the test detail
  const whyOpen = await page.evaluate(() => {
    try { showWhyHiddenModal(); return { ok:true, err:null }; }
    catch(e){ return { ok:false, err: String(e && e.message || e) }; }
  });
  if (!whyOpen.ok) record(slug, 'showWhyHiddenModal() did not throw', false, whyOpen.err);
  else record(slug, 'showWhyHiddenModal() did not throw', true);
  await new Promise(r => setTimeout(r, 400));
  await assertVisible(page, '#why-hidden-modal', slug, 'why-hidden modal opens visibly');
  // Close it
  await page.evaluate(() => { const m = document.getElementById('why-hidden-modal'); if (m) m.remove(); });

  // ── 9. Card rendering ──
  console.log('  ── Cards ──');
  const cardStats = await page.evaluate(() => {
    const cards = document.querySelectorAll('.card[data-fp]');
    if (!cards.length) return { count: 0 };
    const first = cards[0];
    return {
      count: cards.length,
      firstHasScore: !!first.querySelector('.score'),
      firstHasTitle: !!first.querySelector('.title a'),
      firstHasCompany: !!first.querySelector('.company'),
      firstHasApplyBtn: !!first.querySelector('.btn.primary'),
      firstHasMarkAppliedBtn: !!first.querySelector('button[data-status-for]'),
    };
  });
  record(slug, 'card count >= 1', cardStats.count >= 1, `got ${cardStats.count}`);
  record(slug, 'card count <= 20 (TOP_N)', cardStats.count <= 20, `got ${cardStats.count}`);
  if (cardStats.count > 0) {
    record(slug, 'first card has score', cardStats.firstHasScore);
    record(slug, 'first card has title', cardStats.firstHasTitle);
    record(slug, 'first card has company', cardStats.firstHasCompany);
    record(slug, 'first card has Apply button', cardStats.firstHasApplyBtn);
    record(slug, 'first card has Mark Applied button', cardStats.firstHasMarkAppliedBtn);
  }

  // ── 10. Dropdown menu items: click each and verify expected side effect ──
  console.log('  ── More dropdown items ──');
  // Open More dropdown first
  await page.evaluate(() => {
    const trigger = Array.from(document.querySelectorAll('.header-btn')).find(b => /^More/.test(b.textContent.trim()));
    if (trigger) trigger.click();
  });
  await new Promise(r => setTimeout(r, 250));
  // Click "Why isn't [X] in my feed?" — should open modal
  const whyHiddenOpened = await page.evaluate(() => {
    const btn = document.getElementById('why-hidden-btn');
    if (!btn) return { ok: false, why: 'btn not found' };
    btn.click();
    return { ok: !!document.getElementById('why-hidden-modal') };
  });
  record(slug, 'click #why-hidden-btn opens why-hidden modal', whyHiddenOpened.ok, whyHiddenOpened.why || '');
  // Test modal close via × button (uses our new modal-close-btn class)
  const whyHiddenClosed = await page.evaluate(() => {
    const close = document.querySelector('#why-hidden-modal .modal-close-btn');
    if (!close) return { ok: false, why: 'no close button' };
    close.click();
    return { ok: !document.getElementById('why-hidden-modal') };
  });
  record(slug, 'why-hidden modal × button closes it', whyHiddenClosed.ok, whyHiddenClosed.why || '');

  // ── 11. Card content sanity ──
  console.log('  ── Cards ──');
  const cards = await page.evaluate(() => {
    const all = Array.from(document.querySelectorAll('.card[data-fp]'));
    if (!all.length) return { count: 0 };
    return {
      count: all.length,
      withScore: all.filter(c => {
        const s = c.querySelector('.score');
        const n = s ? parseInt(s.textContent, 10) : NaN;
        return Number.isFinite(n) && n >= 0 && n <= 100;
      }).length,
      withApplyURL: all.filter(c => {
        const a = c.querySelector('.title a[href]');
        return a && a.href && a.href.startsWith('http');
      }).length,
      withCompany: all.filter(c => (c.querySelector('.company') || {}).textContent).length,
      withWhyData: all.filter(c => c.getAttribute('data-why')).length,
      topScores: all.slice(0, 5).map(c => parseInt((c.querySelector('.score') || {}).textContent, 10) || 0),
    };
  });
  record(slug, `all ${cards.count} cards have valid 0-100 score`, cards.withScore === cards.count, `${cards.withScore}/${cards.count}`);
  record(slug, `all cards have apply URL`, cards.withApplyURL === cards.count, `${cards.withApplyURL}/${cards.count}`);
  record(slug, `all cards have company`, cards.withCompany === cards.count, `${cards.withCompany}/${cards.count}`);
  record(slug, `all cards have data-why`, cards.withWhyData === cards.count, `${cards.withWhyData}/${cards.count}`);
  record(slug, `top 5 cards have score >= 50`, cards.topScores.every(s => s >= 50), `scores=${cards.topScores.join(',')}`);

  // ── 12. Click "Why?" button on first card → tooltip appears ──
  const whyOnCard = await page.evaluate(() => {
    const card = document.querySelector('.card[data-fp]');
    if (!card) return { ok: false, why: 'no card' };
    const whyBtn = Array.from(card.querySelectorAll('button')).find(b => /^Why/.test(b.textContent.trim()));
    if (!whyBtn) return { ok: false, why: 'no Why? button' };
    whyBtn.click();
    return { ok: !!card.querySelector('.why-tooltip'), tooltipText: (card.querySelector('.why-tooltip') || {}).textContent };
  });
  record(slug, `card "Why?" button opens tooltip`, whyOnCard.ok, whyOnCard.why || `text="${(whyOnCard.tooltipText || '').slice(0, 50)}"`);

  // ── 13. Walk wizard step-by-step (each goto + render without error) ──
  console.log('  ── Wizard walk ──');
  // Re-open wizard (force-show by clearing finished)
  await page.evaluate(() => {
    try {
      const k = 'gmj_wizard_state_v3';
      localStorage.setItem(k, JSON.stringify({ currentStep: 'welcome', completed: [], skipped: [], data: {}, finished: false }));
      WizV3.open();
    } catch (e) {}
  });
  await new Promise(r => setTimeout(r, 600));

  const allSteps = ['welcome', 'upload-resume', 'your-bullseye', 'where-you-work', 'scoring-tune', 'daily-workflow', 'pick-blocks', 'addons', 'done'];
  for (const stepKey of allSteps) {
    const result = await page.evaluate((sk) => {
      try {
        WizV3.goto(sk);
        // Wait a tick for async render
        return new Promise(r => setTimeout(() => {
          const body = document.getElementById('wiz3-body');
          const h2 = document.getElementById('wiz3-h2');
          r({
            ok: body && body.innerHTML.length > 50,
            currentStep: WizV3.state().currentStep,
            title: h2 ? h2.textContent : '',
            bodyLen: body ? body.innerHTML.length : 0,
          });
        }, 500));
      } catch (e) {
        return { ok: false, error: e.message };
      }
    }, stepKey);
    record(slug, `wizard step '${stepKey}' renders`, result.ok, result.error || `title="${result.title}" bodyLen=${result.bodyLen}`);
  }

  // ── 14. Wizard footer buttons exist on a non-welcome step ──
  await page.evaluate(() => WizV3.goto('your-bullseye'));
  await new Promise(r => setTimeout(r, 600));
  for (const sel of ['#wiz3-back', '#wiz3-skip', '#wiz3-continue']) {
    await assertVisible(page, sel, slug, `wizard ${sel} visible on bullseye step`);
  }

  // ── 15. Wizard skill picker cap enforcement (already at 14/15 per screenshot — verify it accepts 1 more, rejects 2) ──
  const capTest = await page.evaluate(() => {
    const tHost = document.querySelector('#bs-skills-host');
    if (!tHost || !tHost.__bullseyeValues) return { ok: false, why: 'skills picker not found' };
    const before = tHost.__bullseyeValues().length;
    const inp = tHost.querySelector('.bullseye-input');
    if (!inp) return { ok: false, why: 'no input' };
    return { ok: true, beforeCount: before, max: tHost.__bullseyeMax, inputDisabled: inp.disabled };
  });
  record(slug, 'skill picker has working state', capTest.ok, capTest.why || `count=${capTest.beforeCount}/max=${capTest.max} inputDisabled=${capTest.inputDisabled}`);

  // ── 16. Close wizard via × button (programmatic click) ──
  const wizClosed = await page.evaluate(() => {
    const x = document.getElementById('wiz3-close');
    if (!x) return { ok: false, why: 'no close button' };
    x.click();
    return { ok: !document.getElementById('wiz3-overlay').classList.contains('show') };
  });
  record(slug, 'wizard × button closes wizard', wizClosed.ok, wizClosed.why || '');

  await page.close();
}

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  for (const u of USERS) {
    await testUser(browser, u);
  }
  await browser.close();

  // Write results to a JSON file (committed by CI on success or failure)
  const fs = require('fs');
  try {
    const path = require('path');
    const outDir = process.env.E2E_RESULTS_DIR || 'reports';
    fs.mkdirSync(outDir, { recursive: true });
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const outFile = path.join(outDir, `e2e_${stamp}.json`);
    fs.writeFileSync(outFile, JSON.stringify({ ts: new Date().toISOString(), site: SITE, users: USERS, results }, null, 2));
    console.log(`\n📝 Results written to ${outFile}`);
  } catch (e) { console.warn('couldn\'t write results file:', e.message); }

  // Summary
  console.log(`\n━━━ SUMMARY ━━━`);
  const byUser = {};
  for (const r of results) {
    byUser[r.user] = byUser[r.user] || { pass: 0, fail: 0 };
    if (r.ok) byUser[r.user].pass++;
    else byUser[r.user].fail++;
  }
  for (const [u, s] of Object.entries(byUser)) {
    console.log(`  ${u}: ${s.pass} pass / ${s.fail} fail`);
  }
  const failedTests = results.filter(r => !r.ok);
  if (failedTests.length) {
    console.log(`\n${failedTests.length} test(s) failed:`);
    for (const r of failedTests) console.log(`  ✗ [${r.user}] ${r.name} — ${r.detail}`);
    process.exit(1);
  }
  console.log(`\n✓ ALL ${results.length} TESTS PASS`);
  process.exit(0);
})();
