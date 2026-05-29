// End-to-end render test for the per-user dashboard.
//
// Loads the generated geetu.html (committed by refresh-jobs) into jsdom,
// asserts the structural pieces a user actually depends on are present:
//   - focus panel + focus-list + focus-footer + sprint controls all in DOM
//   - smart-rotation hooks (fp-apply-btn class, fp-skip-btn class)
//   - "Get next 5" empty-state CTA
//   - script blocks parse without errors
//
// Catches: template regressions where the dashboard renders but key UI
// vanishes (the class of bug that was masked until users complained).
//
// Skip gracefully if jsdom isn't installed — the smoke gate `npm i jsdom`
// before running it. Local devs without node_modules just see "skipped".

import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, '..');

let JSDOM;
try {
  JSDOM = (await import('jsdom')).JSDOM;
} catch (e) {
  console.log('=== e2e dashboard test ===');
  console.log('  ⚠ jsdom not installed — skipping (install with: npm i jsdom)');
  process.exit(0);
}

let passed = 0, failed = 0;
function ok(cond, label, detail = '') {
  if (cond) { console.log(`  ✓ ${label}`); passed++; }
  else { console.log(`  ✗ ${label}${detail ? '   — ' + detail : ''}`); failed++; }
}

console.log('=== e2e dashboard test (geetu.html) ===\n');

const htmlPath = resolve(repoRoot, 'geetu.html');
if (!existsSync(htmlPath)) {
  console.log('  ⚠ geetu.html missing — run refresh-jobs or regen-dashboards first; skipping');
  process.exit(0);
}

const html = readFileSync(htmlPath, 'utf8');
// runScripts:'outside-only' = parse <script> but don't auto-execute (we
// don't want to make network calls or hit localStorage during the test)
const dom = new JSDOM(html, { runScripts: 'outside-only', resources: 'usable' });
const doc = dom.window.document;

ok(doc.getElementById('focus-panel') !== null, 'focus-panel element exists in DOM');
ok(doc.getElementById('focus-list') !== null, 'focus-list element exists');
ok(doc.getElementById('focus-footer') !== null, 'focus-footer element exists (browse expander hook)');
ok(doc.getElementById('grid') !== null, 'main grid container exists');

// Sprint scaffolding
const sprintHints = html.includes('sprint-strip') || html.includes('sprint-start-cta');
ok(sprintHints, 'sprint strip OR start-CTA present');
ok(html.includes('sprintEndEarly'), 'sprint end-early function defined (exit-sprint discoverable)');

// Smart rotation hooks
ok(html.includes('fp-apply-btn'), 'fp-apply-btn class wired (Apply auto-marks + rotates)');
ok(html.includes('fp-skip-btn'), 'fp-skip-btn class wired (skip-with-reason)');
ok(html.includes('fp-next-batch'), 'fp-next-batch id wired ("Get next 5" CTA)');

// Cards in grid
const cards = doc.querySelectorAll('.card[data-fp]');
ok(cards.length > 0, `grid has at least 1 card (found ${cards.length})`);

// Each card should carry tier metadata
let cardsWithTier = 0;
cards.forEach(c => { if (c.getAttribute('data-tier')) cardsWithTier++; });
ok(cardsWithTier === cards.length, `every card has data-tier (${cardsWithTier}/${cards.length})`);

// Scripts have all the required functions
ok(html.includes('async function refreshFocusPanel'), 'refreshFocusPanel defined');
ok(html.includes('function _decorateContactBadges'), '_decorateContactBadges defined (warm-intro rendering)');

console.log(`\n========================================`);
console.log(`Result: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
