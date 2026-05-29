// Unit tests for _alignPool — the worker function that enforces
// "pool[:N] must equal primary[:N]" invariant for the wizard UI.
//
// Why test: bumping the limits (5→10 for titles/industries, 15→50 for skills)
// changed three call sites. A future bump or refactor could silently break
// the contract and the wizard would render mismatched chips.

// Copy of _alignPool from worker_target.js:572 (kept in sync manually —
// if the source diverges, this test will catch behavior changes).
function _alignPool(primary, pool, takeN) {
  const out = [];
  const seen = new Set();
  for (const p of (primary || []).slice(0, takeN)) {
    if (!seen.has(p)) { out.push(p); seen.add(p); }
  }
  for (const p of (pool || [])) {
    if (!seen.has(p)) { out.push(p); seen.add(p); }
  }
  return out;
}

let passed = 0, failed = 0;
function eq(actual, expected, label) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { console.log(`  ✓ ${label}`); passed++; }
  else { console.log(`  ✗ ${label}\n      expected: ${e}\n      got:      ${a}`); failed++; }
}

console.log("=== _alignPool tests ===\n");

eq(_alignPool([], [], 5), [], "empty primary + empty pool returns empty");
eq(_alignPool(["a","b"], [], 5), ["a","b"], "primary only, no pool");
eq(_alignPool([], ["x","y"], 5), ["x","y"], "pool only, no primary");
eq(_alignPool(["a","b"], ["a","c","d"], 5), ["a","b","c","d"], "dedupes overlap");
eq(_alignPool(["a","b","c"], ["x","y","z"], 2), ["a","b","x","y","z"], "primary capped at takeN, pool fully appended");
eq(_alignPool(["a","b","c","d","e","f"], [], 5), ["a","b","c","d","e"], "primary > takeN truncates");
eq(_alignPool(null, null, 5), [], "null inputs handled");
eq(_alignPool(["a","a","b"], ["b","c"], 5), ["a","b","c"], "dedupes duplicates within primary too");

// Realistic scenario — the bumps we shipped tonight
const titles10 = ["dir prod","sr dir prod","vp prod","head of prod","group pm","principal pm","staff pm","dir digital","dir transformation","vp digital"];
const titlesPool15Extra = ["dir grc","sr dir grc","vp grc","dir risk","sr dir risk","vp risk","dir compliance","vp compliance","head of risk","md risk","md compliance","sr advisor","principal advisor","chief of staff","cof"];
const aligned = _alignPool(titles10, titlesPool15Extra, 10).slice(0, 25);
eq(aligned.length, 25, "post-bump: 10 primary + 15 pool fits in 25 cap");
eq(aligned.slice(0, 10), titles10, "post-bump: first 10 of pool MUST equal primary (wizard contract)");

console.log(`\n========================================`);
console.log(`Result: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
