// Pure-function unit test for buildSprintReminder.
// Run via:  node tests/test_sprint_reminder.mjs
import { buildSprintReminder } from '../worker_target.js';

let PASS = 0, FAIL = 0;
function check(label, cond, detail = '') {
  if (cond) { PASS++; console.log(`  ✓ ${label}`); }
  else { FAIL++; console.log(`  ✗ ${label}  (${detail})`); }
}

const SPRINT_START = '2026-05-27T00:00:00Z';
const NOW_DAY_3 = new Date('2026-05-29T13:00:00Z');  // 7am ET on day 3

const baseProfile = { sprintStart: SPRINT_START, sprintDays: 10, sprintDailyQuota: 3 };
const baseUser = { slug: 'geetu', name: 'Geetanjali Arora', email: 'geetua@gmail.com' };

console.log('buildSprintReminder tests:\n');

// 1. Day-N math is correct for day 3
{
  const r = buildSprintReminder({
    slug: 'geetu', userName: 'Geetanjali Arora',
    profile: baseProfile, tracker: {}, contacts: [], cards: [],
    now: NOW_DAY_3, ccEmail: '',
  });
  check('day 3 of 10 in subject', /Day 3 of 10/.test(r.subject), r.subject);
  check('meta.dayN === 3', r.meta.dayN === 3, `got ${r.meta.dayN}`);
  check('meta.quotaTotal === 30', r.meta.quotaTotal === 30, `got ${r.meta.quotaTotal}`);
  check('0% to goal when no applied', r.meta.pct === 0, `got ${r.meta.pct}`);
  check('cc empty by default', r.ccList.length === 0);
}

// 2. Tracker rollup counts only entries within sprint window
{
  const tracker = {
    'fp1': { status: 'applied', appliedAt: '2026-05-27T08:00:00Z' },   // day 1, before now
    'fp2': { status: 'applied', appliedAt: '2026-05-28T10:00:00Z' },   // day 2
    'fp3': { status: 'applied', appliedAt: '2026-05-29T05:00:00Z' },   // today (day 3)
    'fp4': { status: 'phone',   appliedAt: '2026-05-29T06:00:00Z' },   // today, status phone (counts)
    'fp5': { status: 'applied', appliedAt: '2026-05-26T08:00:00Z' },   // BEFORE sprintStart — excluded
    'fp6': { status: 'dismissed', appliedAt: '2026-05-28T08:00:00Z' }, // not a counted status
  };
  const r = buildSprintReminder({
    slug: 'geetu', userName: 'Geetu', profile: baseProfile,
    tracker, contacts: [], cards: [], now: NOW_DAY_3, ccEmail: '',
  });
  check('counts 4 in-window applies (excludes pre-sprint + dismissed)', r.meta.applied === 4, `got ${r.meta.applied}`);
  check('counts 2 today (one applied, one phone)', r.meta.todayApplied === 2, `got ${r.meta.todayApplied}`);
  check('counts 1 yesterday', r.meta.yesterdayApplied === 1, `got ${r.meta.yesterdayApplied}`);
}

// 3. Warm-intro picks rank above non-warm even at lower score
{
  const contacts = [{ company: 'Pfizer' }, { company: 'Pfizer' }, { company: 'BioReference' }];
  const cards = [
    { fp: 'a', score: 85, applyUrl: 'https://a', title: 'VP Eng', company: 'RandomCo' },
    { fp: 'b', score: 60, applyUrl: 'https://b', title: 'VP Product', company: 'Pfizer' },
    { fp: 'c', score: 70, applyUrl: 'https://c', title: 'Director', company: 'BioReference' },
  ];
  const r = buildSprintReminder({
    slug: 'geetu', userName: 'Geetu', profile: baseProfile,
    tracker: {}, contacts, cards, now: NOW_DAY_3, ccEmail: '',
  });
  // Pfizer (2 warm) and BioReference (1 warm) should come before RandomCo (0 warm).
  // Order among warm: by score → BioReference (70) before Pfizer (60).
  // Top-3 (dailyQuota=3) = [BioReference, Pfizer, RandomCo]
  const html = r.bodyHtml;
  const idxBio = html.indexOf('BioReference');
  const idxPfi = html.indexOf('Pfizer');
  const idxRnd = html.indexOf('RandomCo');
  check('BioReference (warm) ranks before RandomCo (cold higher score)', idxBio < idxRnd, `${idxBio} vs ${idxRnd}`);
  check('Pfizer (warm) ranks before RandomCo', idxPfi < idxRnd, `${idxPfi} vs ${idxRnd}`);
  check('warm-intro contact badge present', /🤝.*contact/.test(html));
}

// 4. Day-3-miss cc escalation fires on day 4+ when yesterday was empty
{
  const r3 = buildSprintReminder({
    slug: 'geetu', userName: 'Geetu', profile: baseProfile,
    tracker: {}, contacts: [], cards: [],
    now: new Date('2026-05-29T13:00:00Z'),  // day 3 — should NOT cc yet
    ccEmail: 'amit@example.com',
  });
  check('day 3 does NOT cc (escalation starts day 4)', r3.ccList.length === 0);

  const r4 = buildSprintReminder({
    slug: 'geetu', userName: 'Geetu', profile: baseProfile,
    tracker: {}, contacts: [], cards: [],
    now: new Date('2026-05-30T13:00:00Z'),  // day 4, yesterday=0
    ccEmail: 'amit@example.com',
  });
  check('day 4 with 0 yesterday → cc fires', r4.ccList.includes('amit@example.com'));

  // Day 4 but user DID apply yesterday — no escalation
  const r4ok = buildSprintReminder({
    slug: 'geetu', userName: 'Geetu', profile: baseProfile,
    tracker: { 'x': { status: 'applied', appliedAt: '2026-05-29T20:00:00Z' } },
    contacts: [], cards: [],
    now: new Date('2026-05-30T13:00:00Z'),
    ccEmail: 'amit@example.com',
  });
  check('day 4 with applied-yesterday → no cc', r4ok.ccList.length === 0);
}

// 5. Subject contains today + total applied
{
  const tracker = {
    'a': { status: 'applied', appliedAt: '2026-05-29T08:00:00Z' },
    'b': { status: 'applied', appliedAt: '2026-05-27T08:00:00Z' },
  };
  const r = buildSprintReminder({
    slug: 'geetu', userName: 'Geetu', profile: baseProfile,
    tracker, contacts: [], cards: [], now: NOW_DAY_3, ccEmail: '',
  });
  check('subject shows today/quota', /1\/3 today/.test(r.subject), r.subject);
  check('subject shows total/quotaTotal', /2\/30 total/.test(r.subject), r.subject);
}

// 6. First-name extraction works
{
  const r = buildSprintReminder({
    slug: 'geetu', userName: 'Geetanjali Arora', profile: baseProfile,
    tracker: {}, contacts: [], cards: [], now: NOW_DAY_3, ccEmail: '',
  });
  check('body greets first name', /Hi Geetanjali,/.test(r.bodyHtml));
}

// 7. Edge: empty tracker, empty contacts, empty cards → still renders without crashing
{
  const r = buildSprintReminder({
    slug: 'geetu', userName: 'Geetu', profile: baseProfile,
    tracker: {}, contacts: [], cards: [], now: NOW_DAY_3, ccEmail: '',
  });
  check('empty state renders', r.bodyHtml.includes('Day 3 of 10'));
  check('empty state: 0 jobs', /<b>0 jobs<\/b>/.test(r.bodyHtml));
}

console.log();
console.log('='.repeat(40));
console.log(`Result: ${PASS} passed, ${FAIL} failed`);
process.exit(FAIL === 0 ? 0 : 1);
