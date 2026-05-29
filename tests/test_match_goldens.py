"""Matching-quality canary using fetch_jobs.py's score_job (with all bindings).

What we're catching: NameError/import regressions in matcher/scoring.py that
silently make score_job return 0 for everything. This is the scoring-tier
analogue of the _strip_html bug — it would let bad refactors ship invisibly.

Uses fetch_jobs.py's initialization so all the lazy-bound constants and
COMPANY_INDUSTRIES populate correctly.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importing fetch_jobs triggers all the lazy-binding side effects
import fetch_jobs as fj

GEETU_PROFILE = {
    "seniorityTitles": ["director", "vp", "principal"],
    "targetTitles": ["director of product", "vp product", "head of product"],
    "industries": ["healthcare", "healthtech", "digital health"],
    "keywords": ["product management", "digital transformation", "ehr", "fhir"],
    "negativeKeywords": ["nurse", "physician"],
    "preferredLocations": ["New York", "Remote (US)"],
    "remotePreference": "hybrid",
}


def main():
    # Synthetic test jobs — varying tiers
    cases = [
        ("VP, Product Management — Care Delivery", "Devoted Health",
         "Remote (US)", "Lead product strategy for our value-based care platform. EHR integration, FHIR APIs.", "expect HIGH"),
        ("Director of Product, Telehealth Platform", "Cityblock Health",
         "New York, NY", "Own roadmap for our telehealth platform. Healthcare product leader.", "expect HIGH"),
        ("Registered Nurse — Acute Care", "Cleveland Clinic",
         "Cleveland, OH", "Provide bedside nursing care...", "expect LOW (negative-keyword)"),
        ("Senior Software Engineer", "Acme Corp",
         "San Francisco", "Build backend services. Java, Kotlin.", "expect LOW (no healthcare signal)"),
    ]

    passed = 0; failed = 0
    print("=== matching goldens (synthetic jobs) ===\n")

    if not hasattr(fj, "score_job"):
        print("  ✗ fetch_jobs.score_job not importable — scoring module broken")
        return 1

    for title, company, loc, desc, expectation in cases:
        job = {
            "title": title, "company": company, "location": loc, "description": desc,
            "company_name": company, "url": "", "source": "test", "posted_at": "2026-05-25",
        }
        try:
            fj._set_skills_profile(GEETU_PROFILE); score = fj.score_job(job)
        except Exception as e:
            print(f"  ✗ score_job crashed on '{title[:40]}': {type(e).__name__}: {e}")
            failed += 1
            continue
        tier = "HIGH" if score >= 70 else ("MED" if score >= 50 else "LOW")
        ok = (
            (expectation.startswith("expect HIGH") and tier == "HIGH") or
            (expectation.startswith("expect LOW") and tier == "LOW")
        )
        if ok:
            print(f"  ✓ [{score:3} {tier:4}] {title[:50]:50} — {expectation}")
            passed += 1
        else:
            print(f"  ✗ [{score:3} {tier:4}] {title[:50]:50} — {expectation}")
            failed += 1

    print(f"\n========================================")
    print(f"Result: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
