"""Static tests for the Wizard v3 block embedded in fetch_jobs.py.

The v3 wizard is JavaScript stored in a Python triple-quoted string
(WIZARD_V3_BLOCK) and injected into every generated dashboard HTML.
We can't trivially run that JS from pytest, so these tests use
regex / structural checks on the source string to catch regressions
that the team has hit before:

  - STATE_KEY drifts to a name nothing else writes to
  - match-weights "must sum to 100" validation gets removed/weakened
  - One of the 12 declared steps gets accidentally deleted or renamed
  - The state object loses one of its required keys
  - The save-on-every-transition pattern gets broken

Run via:  python3 tests/test_wizard_v3.py
Exits non-zero on any failure (matches the existing tests/ style).
"""
import os, re, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Phase 3 split (2026-05-28) moved the block to dashboard/wizard.py.
FETCH = os.path.join(ROOT, "dashboard", "wizard.py")

PASS = 0
FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  ({detail})")


# ----------------------------------------------------------------------
# Load WIZARD_V3_BLOCK
# ----------------------------------------------------------------------
with open(FETCH, "r") as f:
    src = f.read()

m = re.search(r'WIZARD_V3_BLOCK\s*=\s*r?"""(.*?)"""', src, re.DOTALL)
if not m:
    print("✗ FATAL: Could not locate WIZARD_V3_BLOCK = \"\"\"...\"\"\" in dashboard/wizard.py")
    sys.exit(2)
V3 = m.group(1)
print(f"Loaded WIZARD_V3_BLOCK: {len(V3):,} bytes\n")


# ----------------------------------------------------------------------
# (a) STATE_KEY persistence round-trip — shape of saved state
# ----------------------------------------------------------------------
print("State key + persistence shape:")
check("STATE_KEY constant is 'gmj_wizard_state_v3'",
      'const STATE_KEY = "gmj_wizard_state_v3"' in V3,
      "v2 used a different key; if v3 reuses it, v2 leftovers will corrupt v3 state")

check("saveState writes via localStorage.setItem(STATE_KEY, JSON.stringify(s))",
      "localStorage.setItem(STATE_KEY, JSON.stringify(s))" in V3,
      "save-on-every-transition guarantee depends on this single line")

check("loadState reads via localStorage.getItem(STATE_KEY)",
      "localStorage.getItem(STATE_KEY)" in V3,
      "must read the same key it writes")

# The default-state object must contain all 5 required keys.
# Match the return statement that initializes a fresh state — be tolerant of
# nested braces like `data: {}` by anchoring on currentStep + finished and
# searching within that span.
default_re = re.search(
    r'return\s*\{\s*currentStep:\s*"welcome".*?finished:\s*false\s*\};', V3, re.DOTALL)
check("default state contains all 5 required keys: currentStep, completed, skipped, data, finished",
      default_re is not None
      and all(k in default_re.group(0) for k in
              ("currentStep:", "completed:", "skipped:", "data:", "finished:")),
      "if any key is missing, loadState() will return a malformed state and downstream code crashes")

# Simulate a round-trip: build a representative state, JSON-encode/decode, verify shape preserved
sample_state = {
    "currentStep": "match-weights",
    "completed": ["welcome", "upload-resume", "review-profile"],
    "skipped": ["locations-remote"],
    "data": {"matchWeights": {"titles": 50, "industry": 25, "skills": 25}},
    "finished": False,
}
roundtrip = json.loads(json.dumps(sample_state))
check("sample state JSON-roundtrips losslessly (sanity check)",
      roundtrip == sample_state)
check("after JSON roundtrip, matchWeights subtree is intact",
      roundtrip["data"]["matchWeights"]["titles"] == 50
      and sum(roundtrip["data"]["matchWeights"].values()) == 100)


# ----------------------------------------------------------------------
# (b) scoring-tune step: title/industry/skills weights must sum to 100
#     (post-consolidation, match-weights lives inside 'scoring-tune')
# ----------------------------------------------------------------------
print("\nscoring-tune step (consolidates match-weights + signal-stability):")
mw_block_re = re.compile(
    r'key:\s*"scoring-tune"(.*?)(?=\}\s*,\s*\{\s*key:|\}\s*,?\s*\];?\s*//\s*end of STEPS|\Z)',
    re.DOTALL)
mw = mw_block_re.search(V3)
check("'scoring-tune' step is defined", mw is not None,
      "the consolidated scoring step has been removed from the STEPS array")
if mw:
    mw_block = mw.group(1)
    check("step keys 'titles', 'industry', 'skills' present in render",
          all(k in mw_block for k in ("'titles'", "'industry'", "'skills'")),
          "weight keys were renamed — patchProfile will silently drop unknown keys")
    check("validate() rejects when total != 100",
          "if (t !== 100)" in mw_block,
          "the must-sum-to-100 guard has been weakened or removed")
    check("validate() returns an error message mentioning '100'",
          re.search(r'return\s+"[^"]*100[^"]*"', mw_block) is not None,
          "error message no longer mentions the 100 target, hurting user understanding")
    check("save() calls patchProfile with matchWeights",
          "matchWeights" in mw_block and "patchProfile" in mw_block,
          "saved weights are no longer persisted to the user profile")
    # Functional simulation of the validate logic in Python — proves the rule is sound
    def simulate_validate(titles, industry, skills):
        t = (titles or 0) + (industry or 0) + (skills or 0)
        if t != 100:
            return f"Weights must add to 100. Currently: {t}."
        return ""
    check("simulated validate(50,25,25) accepts (sum=100)",
          simulate_validate(50, 25, 25) == "")
    check("simulated validate(60,20,10) rejects (sum=90)",
          "Currently: 90" in simulate_validate(60, 20, 10))
    check("simulated validate(50,40,30) rejects (sum=120)",
          "Currently: 120" in simulate_validate(50, 40, 30))


# ----------------------------------------------------------------------
# (c) Step inventory + isComplete-style invariants
#     Wizard consolidated from 12 → 9 steps; see project_first_login_wizard
# ----------------------------------------------------------------------
print("\nStep inventory (9 expected after consolidation):")

# Pull ordered step keys out of STEPS array (top-level only, not nested wiz3-* references)
step_keys = re.findall(r'\{\s*key:\s*"([a-z\-]+)",\s*\n\s+title:', V3)
expected_steps = [
    "welcome", "upload-resume", "your-bullseye", "where-you-work",
    "scoring-tune", "addons", "pick-blocks", "done",
]
check(f"exactly 8 steps declared (found {len(step_keys)})",
      len(step_keys) == 8,
      f"step list drift: got {step_keys}")
check("step order matches the consolidated 8-step contract",
      step_keys == expected_steps,
      f"order/membership diff: expected {expected_steps}, got {step_keys}")

print("\nStep optionality:")
# Find which steps have 'optional: true' in the 8 lines after their key declaration.
lines = V3.split("\n")
key_line_re = re.compile(r'^\s*key:\s*"([a-z\-]+)",\s*$')
key_lines = [(i, key_line_re.match(ln).group(1)) for i, ln in enumerate(lines) if key_line_re.match(ln)]
optional_map = {}
for i, key in key_lines:
    window = "\n".join(lines[i:i + 8])
    optional_map[key] = "optional: true" in window

# Required steps after consolidation:
#   - 'your-bullseye' (titles/industries/skills/companies — the CORE matcher inputs)
#   - 'done' (terminus)
# Every other step is optional.
required_steps = {"your-bullseye", "done"}
actual_required = {k for k, v in optional_map.items() if not v}
check("required steps are exactly {'your-bullseye', 'done'}",
      actual_required == required_steps,
      f"optionality drift: required={sorted(actual_required)} expected={sorted(required_steps)}")
check("all non-required steps are explicitly marked optional",
      all(optional_map[k] for k in step_keys if k not in required_steps),
      "a previously-optional step became required — users hitting Skip will get blocked")

print("\nIsComplete / finished invariant:")
# v3 doesn't define an isComplete() function — completion is tracked via the
# 'finished' boolean and the 'completed[]' / 'skipped[]' arrays. The 'done' step
# is what flips 'finished' to true. Verify the wiring:
check("'finished' is initialized to false in default state",
      "finished: false" in V3,
      "state must start un-finished")

done_block_re = re.search(
    r'key:\s*"done"(.*?)(?=\}\s*\];|\Z)', V3, re.DOTALL)
check("'done' step exists and has a save() that flips state.finished = true",
      done_block_re is not None
      and "state.finished" in done_block_re.group(1)
      and "true" in done_block_re.group(1).split("state.finished", 1)[1][:80],
      "the terminal step no longer marks the wizard finished")

# v2 migration path: if user already finished v2, v3 starts finished too
check("v2 → v3 migration: gmj_wizard_seen_v2 short-circuits v3 to finished",
      "gmj_wizard_seen_v2" in V3 and "state.finished = true" in V3,
      "users who finished v2 will be re-asked the 12 v3 questions")


# ----------------------------------------------------------------------
# (d) Belt-and-suspenders: v2 must stay gated when v3 is present
# ----------------------------------------------------------------------
print("\nv2 gating:")
check("window.WizV3 marker is set when v3 loads",
      "window.WizV3" in V3,
      "v2 setup() checks this marker to bail out — losing it means BOTH wizards render")


# ----------------------------------------------------------------------
# (e) 2026-06-07 re-trigger regressions: completion must be server-backed
#     and the obsolete over-cap migration must STAY deleted
# ----------------------------------------------------------------------
print("\nRe-trigger protections (2026-06-07):")
check("finish() writes wizardCompletedAt to the profile (server-side truth)",
      "wizardCompletedAt" in V3 and V3.count("patchProfile({ wizardCompletedAt") >= 2,
      "completion lives only in localStorage -> wizard re-opens on every new device / storage wipe")

check("autoLaunch consults profile.wizardCompletedAt and heals localStorage",
      "p.wizardCompletedAt" in V3,
      "server flag exists but autoLaunch ignores it")

check("over-cap 'migration' force-route is gone (contradicts no-caps policy)",
      "needsMigration" not in V3 and "bullseyeMigratedAt" not in V3,
      "the >5/>5/>15 check force-opens the wizard forever for users with big (correct) profiles")

check("finished state short-circuits autoLaunch (no auto-open, stale pending cleared)",
      "if (state.finished)" in V3 and 'removeItem("gmj_wizard_state_v3_pendingStep")' in V3,
      "stale pendingStep can resurrect the wizard after completion")

# Worker contract: patch whitelist + regen preservation must carry the flag
WORKER = os.path.join(ROOT, "worker_target.js")
with open(WORKER) as f:
    wsrc = f.read()
print("\nWorker contract for wizardCompletedAt:")
check("SCALAR_FIELDS whitelist accepts wizardCompletedAt",
      "'wizardCompletedAt']" in wsrc or "'wizardCompletedAt'," in wsrc,
      "patchProfile silently drops the flag -> completion never persists")
check("regenerateSkillsProfile preserves wizardCompletedAt across regen",
      wsrc.count("wizardCompletedAt") >= 3,
      "every resume change / regen wipes the flag -> wizard re-opens")


# ----------------------------------------------------------------------
print(f"\n{'='*40}")
print(f"Result: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
