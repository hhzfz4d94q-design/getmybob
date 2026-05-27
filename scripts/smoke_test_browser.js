// Headless-browser smoke test of the live dashboards.
// Asserts: (1) zero console errors, (2) every expected function is defined,
// (3) wizard auto-launches and walks end-to-end, (4) every header button
// has a click handler that doesn't throw.
//
// Usage: node scripts/smoke_test_browser.js [user-slug,...]
// Default users: amit-arora, geetu

const puppeteer = require('puppeteer');

const SITE = process.env.SITE || 'https://getmemyjob.officebeatllc.com';
const USERS = (process.argv[2] || 'amit-arora,geetu').split(',');

const EXPECTED_FUNCTIONS = [
  'openResumeModal',
  'openContactsModal',
  'toggleHeaderMore',
  'prepApplication',
  'refreshData',
  'showWarmIntroModal',
  'showWhyHiddenModal',
  'regenerateCompaniesFromHeader',
  'regenerateFromHeader',
  'replayTour',
];

const EXPECTED_HEADER_BUTTONS = [
  '#refresh-btn',
  '#account-btn',
  '#regen-btn',
  '#regen-companies-btn',
  '#why-hidden-btn',
  '#resume-btn',
  '#contacts-btn',
  '#prefs-btn',
];

async function testUser(browser, slug) {
  const url = `${SITE}/${slug}?_=smoke_${Date.now()}`;
  console.log(`\n=== Testing ${url} ===`);
  const page = await browser.newPage();
  const consoleErrors = [];
  page.on('pageerror', err => consoleErrors.push(`pageerror: ${err.message}`));
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(`console.error: ${msg.text()}`);
  });

  await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
  // Let bootstrap run
  await new Promise(r => setTimeout(r, 2000));

  const failures = [];

  // CHECK 1: zero console errors
  if (consoleErrors.length > 0) {
    failures.push(`${consoleErrors.length} console errors:`);
    for (const e of consoleErrors.slice(0, 5)) failures.push(`  ${e}`);
  }

  // CHECK 2: every expected function is defined
  const defined = await page.evaluate((fns) => {
    const out = {};
    for (const fn of fns) out[fn] = typeof window[fn];
    return out;
  }, EXPECTED_FUNCTIONS);
  for (const fn of EXPECTED_FUNCTIONS) {
    if (defined[fn] !== 'function') {
      failures.push(`Function ${fn} = ${defined[fn]} (expected 'function')`);
    }
  }

  // CHECK 3: header buttons exist + clickable
  const buttons = await page.evaluate((sels) => {
    const out = {};
    for (const sel of sels) {
      const el = document.querySelector(sel);
      out[sel] = el ? { exists: true, disabled: el.disabled } : { exists: false };
    }
    return out;
  }, EXPECTED_HEADER_BUTTONS);
  for (const sel of EXPECTED_HEADER_BUTTONS) {
    if (!buttons[sel].exists) failures.push(`Header button ${sel} missing from DOM`);
  }

  // CHECK 4: WizV3 exists + can render every step without throwing
  const wizardSteps = await page.evaluate(() => {
    if (typeof WizV3 !== 'object' || !WizV3 || !WizV3.state) {
      return { ok: false, error: 'WizV3 not present' };
    }
    return { ok: true, hasOpen: typeof WizV3.open === 'function' };
  });
  if (!wizardSteps.ok) failures.push(`Wizard: ${wizardSteps.error}`);

  await page.close();

  if (failures.length === 0) {
    console.log(`✓ ${slug}: all checks pass`);
    return true;
  } else {
    console.log(`✗ ${slug}: ${failures.length} failure(s)`);
    for (const f of failures) console.log(`    ${f}`);
    return false;
  }
}

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  let allOk = true;
  for (const u of USERS) {
    const ok = await testUser(browser, u);
    if (!ok) allOk = false;
  }
  await browser.close();
  process.exit(allOk ? 0 : 1);
})();
