"""Golden tests for score_job() — the core matching function.

These freeze EXPECTED score ranges for (profile, job) pairs covering the
matching axes. If a future scoring change breaks one of these ranges, the
test fails BEFORE we ship a worse Top-20 to users.

Score is 0-100. Ranges are intentionally wide (±10 points) so trivial tuning
doesn't break tests, but big regressions do.

Run via:  python3 tests/test_scoring.py
Exits non-zero on any failure.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fetch_jobs

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


# Amit's representative profile (senior risk/compliance/banking exec)
AMIT_PROFILE = {
    "targetTitles": ["vp of risk", "director of risk", "head of compliance"],
    "industries": ["fintech", "banking", "financial services"],
    "keywords": ["grc", "tprm", "third-party risk", "compliance", "credit risk",
                 "vendor management", "regulatory compliance", "core banking",
                 "enterprise risk", "audit"],
    "technologies": ["sox", "nist csf"],
    "frameworks": [],
    "negativeKeywords": ["intern", "junior", "entry level", "tester"],
    "seniorityLevel": "vp",
    "seniorityTitles": ["director", "vp", "vice president", "head of", "chief"],
    "matchWeights": {"titles": 30, "industries": 35, "skills": 35},
    "signalStability": {"title": 40, "industry": 100, "skills": 100},
    "careerStage": "director",
}


def score_with(profile, job):
    """Set SKILLS_PROFILE module global, then call score_job."""
    real = fetch_jobs.SKILLS_PROFILE
    fetch_jobs.SKILLS_PROFILE = profile
    try:
        # score_job reads job["title"], job["description"]; needs all keys defensively
        j = {
            "title": job.get("title", ""),
            "description": job.get("description", ""),
            "company_name": job.get("company_name", ""),
            "location": job.get("location", ""),
            "source": job.get("source", "test"),
            "salary_range": job.get("salary_range", ""),
        }
        return fetch_jobs.score_job(j)
    finally:
        fetch_jobs.SKILLS_PROFILE = real


# ----------------------------------------------------------------------
# Goldens — (label, job, profile, expected_min, expected_max)
# ----------------------------------------------------------------------
GOLDENS = [
    # 1. Perfect match: target title + industry + skills all hit
    ("perfect match — VP of Risk at fintech with GRC/TPRM",
     {"title": "VP of Risk",
      "company_name": "Stripe",
      "description": "Stripe is hiring a VP of Risk to lead our GRC and TPRM programs. "
                     "Own third-party risk and compliance across the fintech stack. "
                     "Work with core banking partners and vendor management teams."},
     AMIT_PROFILE, 75, 100),

    # 2. Industry + skills hit but title is generic (no title-match bonus)
    ("industry+skills match, generic title",
     {"title": "Senior Manager, Strategy",
      "company_name": "Acme Bank",
      "description": "Senior Manager at a banking firm. Lead GRC, TPRM, third-party risk, "
                     "and regulatory compliance across enterprise risk teams. Vendor management."},
     AMIT_PROFILE, 50, 100),

    # 3. Title hit but no industry + no skills (signal-stability dampens title)
    ("title match only, no industry/skills",
     {"title": "Director of Risk",
      "company_name": "Random Co",
      "description": "Lead some teams. No specific domain mentioned. Generic job description "
                     "padding text to reach the 200-char threshold so the short-desc penalty doesn't fire."},
     AMIT_PROFILE, 35, 70),

    # 4. Hard blocker — negative keyword hits standalone in title (without senior guard)
    ("hard blocker: 'tester' in title",
     {"title": "Senior Tester",
      "company_name": "Capco",
      "description": "We're hiring a Senior Tester for our QA team. Manual testing, "
                     "regression suites, exploratory testing across banking platforms."},
     AMIT_PROFILE, 0, 0),

    # 5. Negative keyword present but title is senior → SHOULD NOT block (senior guard)
    ("senior guard saves Director with 'tester' in body",
     {"title": "Director of Quality",
      "company_name": "Stripe",
      "description": "Director role overseeing test automation, compliance, GRC, and the banking platform. "
                     "Team includes testers and risk analysts. Fintech background preferred."},
     AMIT_PROFILE, 50, 95),

    # 6. Irrelevant title family — _is_irrelevant_title kicks in (returns 0 early)
    ("irrelevant title family: nurse",
     {"title": "Registered Nurse, ICU",
      "company_name": "Hospital Co",
      "description": "Provide bedside care in our 24-bed ICU. Triage, IV access, vent management. "
                     "Banking GRC compliance experience required (just kidding — this is irrelevant)."},
     AMIT_PROFILE, 0, 0),

    # 7. Remote bonus visible (no domain match, but remote)
    ("remote-only generic job gets +10 remote",
     {"title": "Director of Strategy",
      "company_name": "Random Co",
      "location": "Remote",
      "description": "Remote role. Pretty generic content for a strategy lead. "
                     "Long enough description to avoid the short-desc penalty being triggered "
                     "during scoring. We need at least 200 characters here for that to clear."},
     AMIT_PROFILE, 35, 75),

    # 8. Scam terms penalty
    ("scam terms zap the score",
     {"title": "VP of Risk",
      "company_name": "Sketchy LLC",
      "description": "Earn $5000/week from home! No experience needed. Pay your own training fees "
                     "and receive a Western Union deposit. MLM opportunity. Quick cash. GRC TPRM."},
     AMIT_PROFILE, 0, 60),

    # 9. Short description penalty (-10)
    ("short description (<200 chars) penalty",
     {"title": "VP of Risk",
      "company_name": "Stripe",
      "description": "GRC role. Apply now."},  # ~20 chars
     AMIT_PROFILE, 50, 95),

    # 10. Empty profile (legacy/fallback path)
    ("legacy path (no SKILLS_PROFILE): falls back to RELEVANCE_TERMS",
     {"title": "Senior Compliance Director",
      "company_name": "Goldman",
      "description": "Lead compliance for our global banking platform. Risk management, GRC, "
                     "audit, regulatory reporting. Long enough description to avoid short-desc penalty. "
                     "Padded out to reach the 200-char floor so we don't get the -10 penalty."},
     None, 40, 100),

    # 11. Consulting firm hard-block (Capco) — even a perfect-match JD scores 0
    ("Capco hard-block: consulting firm in default excludeCompanies",
     {"title": "VP of Risk",
      "company_name": "Capco",
      "description": "Lead GRC and TPRM engagements across our fintech and banking client base. "
                     "Third-party risk, regulatory compliance, vendor management. Capital markets advisory."},
     AMIT_PROFILE, 0, 0),

    # 12. User-extended excludeCompanies blocks too
    ("user excludeCompanies extends defaults",
     {"title": "VP of Risk",
      "company_name": "SomeOtherConsultancy",
      "description": "Lead GRC and TPRM engagements across our banking client base. "
                     "Third-party risk, regulatory compliance. Capital markets."},
     {**AMIT_PROFILE, "excludeCompanies": ["SomeOtherConsultancy"]}, 0, 0),

    # 13. Non-excluded company with same content still scores high
    ("Stripe (not in exclude list) with consulting-shaped JD still scores",
     {"title": "VP of Risk",
      "company_name": "Stripe",
      "description": "Lead GRC and TPRM at Stripe. Third-party risk, regulatory compliance, "
                     "vendor management. Capital markets, fintech. Padded enough for no penalty."},
     AMIT_PROFILE, 50, 100),
]

print("score_job() golden tests:\n")
for label, job, prof, lo, hi in GOLDENS:
    s = score_with(prof, job)
    ok = lo <= s <= hi
    detail = f"got {s}, expected [{lo},{hi}]"
    check(label, ok, detail)

# Sanity invariants
print("\nInvariants:")
s = score_with(AMIT_PROFILE, {"title": "", "description": ""})
check("empty job is clamped to [0,100]", 0 <= s <= 100, f"got {s}")

s_low = score_with(AMIT_PROFILE, {"title": "Junior Intern Tester", "description": "x"})
check("triple negative-keyword title scores 0", s_low == 0, f"got {s_low}")

# Idempotency: running score twice gives same result
s1 = score_with(AMIT_PROFILE, GOLDENS[0][1])
s2 = score_with(AMIT_PROFILE, GOLDENS[0][1])
check("score_job is deterministic (same job twice → same score)", s1 == s2, f"{s1} vs {s2}")

print()
print("=" * 40)
print(f"Result: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
