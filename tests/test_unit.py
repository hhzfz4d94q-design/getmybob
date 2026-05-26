"""Unit tests for fetch_jobs.py helpers.

Run via:  python3 tests/test_unit.py
Exits non-zero on any failure.
"""
import os, sys, subprocess, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Import only the small helpers we care about — avoid executing the full file's main()
import importlib.util
spec = importlib.util.spec_from_file_location("fetch_jobs", os.path.join(ROOT, "fetch_jobs.py"))
mod = importlib.util.module_from_spec(spec)
# Override DB_PATH so importing doesn't try to open the real jobs.db
mod.__dict__["DB_PATH"] = "/tmp/_test_jobs.db"
spec.loader.exec_module(mod)

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

# --- _careers_root ---
print("Testing _careers_root:")
check("Workday URL → /tenant/site",
      mod._careers_root("https://jpmc.wd1.myworkdayjobs.com/jpmc/job/12345") == "https://jpmc.wd1.myworkdayjobs.com/jpmc")
check("Greenhouse URL → /slug",
      mod._careers_root("https://boards.greenhouse.io/headway/jobs/12345") == "https://boards.greenhouse.io/headway")
check("Lever URL → /slug",
      mod._careers_root("https://jobs.lever.co/calm/abcdef") == "https://jobs.lever.co/calm")
check("Ashby URL → /slug",
      mod._careers_root("https://jobs.ashbyhq.com/linear/job-xyz") == "https://jobs.ashbyhq.com/linear")
check("Unknown ATS → None",
      mod._careers_root("https://other-site.com/jobs/abc") is None)
check("Empty URL → None",
      mod._careers_root("") is None)
check("None URL → None",
      mod._careers_root(None) is None)

# --- detect_title_stage ---
print("Testing detect_title_stage:")
check("VP title → executive", mod.detect_title_stage("VP, Product Management") == "executive")
check("Director → senior", mod.detect_title_stage("Director of Engineering") == "senior")
check("Senior Manager → mid-career", mod.detect_title_stage("Senior Manager, Operations") == "mid-career")
check("Intern → internship", mod.detect_title_stage("Software Engineering Intern") == "internship")
check("New Grad → new-grad", mod.detect_title_stage("Software Engineer, New Grad") == "new-grad")
check("Bare 'Engineer' → None (ambiguous)", mod.detect_title_stage("Software Engineer") is None)

# --- stage_compatible ---
print("Testing stage_compatible:")
check("senior vs executive → True",  mod.stage_compatible("senior", "executive") is True)
check("senior vs internship → False", mod.stage_compatible("senior", "internship") is False)
check("executive vs mid-career → False", mod.stage_compatible("executive", "mid-career") is False)
check("missing → True (no-drop)", mod.stage_compatible(None, "senior") is True)

# --- is_recruiter_listing ---
print("Testing is_recruiter_listing:")
check("Robert Half company → True",
      mod.is_recruiter_listing({"company_name": "Robert Half", "description": ""}) is True)
check("TEKsystems company → True",
      mod.is_recruiter_listing({"company_name": "TEKsystems", "description": ""}) is True)
check("'our Fortune 500 client' in description → True",
      mod.is_recruiter_listing({"company_name": "Acme Corp", "description": "We're hiring for our Fortune 500 client in finance."}) is True)
check("Normal company → False",
      mod.is_recruiter_listing({"company_name": "Spring Health", "description": "Standard product role description"}) is False)

# --- GHOST_DAYS ---
print("Testing GHOST_DAYS:")
check("GHOST_DAYS is 14 (tightened from 30)", mod.GHOST_DAYS == 14)

# --- Multi-token title match (in score_job) ---
print("Testing score_job (multi-token title match):")
class _Profile(dict):
    pass

prev = mod.SKILLS_PROFILE
mod.SKILLS_PROFILE = {
    "primaryRole": "VP of Product Strategy",
    "seniorityTitles": ["vp", "director", "head of"],
    "targetTitles": ["vp product management", "director of product"],
    "industries": ["healthcare it", "digital health"],
    "keywords": ["product strategy", "transformation"],
    "matchWeights": {"titles": 50, "industries": 25, "skills": 25},
}
job_good = {"title": "VP Product Management", "description": "Healthcare IT leadership role focused on product strategy and transformation.", "location": "Remote", "company_name": "Spring Health"}
job_brand = {"title": "Director of Brand & Growth", "description": "Lead brand strategy.", "location": "Remote", "company_name": "Fitt"}

s_good = mod.score_job(job_good)
s_brand = mod.score_job(job_brand)
check(f"Real fit scores higher than brand-noise ({s_good} > {s_brand})", s_good > s_brand)
check(f"Brand title doesn't break 80 ({s_brand} <= 80)", s_brand <= 80)
mod.SKILLS_PROFILE = prev


# --- Role-family mismatch filter (2026-05-26) ---
print("\nTesting role-family mismatch filter:")

amit_profile = {
    "primaryRole": "Principal / Head of Cyber GRC, Enterprise Risk Management",
    "targetTitles": ["head of risk", "vp risk", "director of grc", "chief risk officer"],
}
geetu_profile = {
    "primaryRole": "Senior Director / VP of Digital Transformation & Product Strategy",
    "targetTitles": ["vp product management", "head of product", "director of product"],
}

# Amit (risk-grc) — engineering, COO, and clinical roles must mismatch
check("Amit: '.NET Engineer' is family-mismatch (drop)",
      mod._is_role_family_mismatch("Senior .NET Engineer", amit_profile))
check("Amit: 'Software Engineer' is family-mismatch",
      mod._is_role_family_mismatch("Software Engineer III", amit_profile))
check("Amit: 'Chief Operating Officer' is family-mismatch",
      mod._is_role_family_mismatch("Chief Operating Officer", amit_profile))
check("Amit: 'QA Lead' is family-mismatch",
      mod._is_role_family_mismatch("QA Lead - Banking", amit_profile))
check("Amit: 'Risk Director' is NOT a mismatch (same family)",
      not mod._is_role_family_mismatch("Risk Director, Capital Markets", amit_profile))
check("Amit: 'VP Compliance' is NOT a mismatch",
      not mod._is_role_family_mismatch("VP Compliance", amit_profile))

# Geetu (product/digital-transformation = OPEN_USER_FAMS) — should allow most things
# BUT operations-coo, engineering should still be filtered for product persona
geetu_strict = {"primaryRole": "VP of Product Management", "targetTitles": ["vp product"]}
check("Geetu (product): 'COO' is family-mismatch",
      mod._is_role_family_mismatch("Chief Operating Officer", geetu_strict))
check("Geetu (product): 'Software Engineer' is family-mismatch",
      mod._is_role_family_mismatch("Senior Software Engineer", geetu_strict))
check("Geetu (product): 'Sales Rep' is family-mismatch",
      mod._is_role_family_mismatch("Senior Sales Representative", geetu_strict))
check("Geetu (product): 'VP Product' is NOT a mismatch",
      not mod._is_role_family_mismatch("VP, Product Management", geetu_strict))
check("Geetu (product): 'Director of Product' is NOT a mismatch",
      not mod._is_role_family_mismatch("Director of Product Strategy", geetu_strict))

# Ambiguous titles should NOT be dropped (over-include)
check("Ambiguous 'Senior Lead' is NOT dropped (no clear family signal)",
      not mod._is_role_family_mismatch("Senior Lead", amit_profile))
check("Ambiguous 'Strategist' is NOT dropped",
      not mod._is_role_family_mismatch("Senior Strategist", amit_profile))

# --- HTML_TEMPLATE.format_map() with defaulting dict (catches Slice B/C/E brace bugs) ---
print("\nTesting HTML_TEMPLATE format_map (regression: single { in JS literal):")
import re
fj_src = open(os.path.join(ROOT, "fetch_jobs.py")).read()
m = re.search(r"^HTML_TEMPLATE\s*=\s*r?\"\"\"", fj_src, re.MULTILINE)
if m:
    end = fj_src.find('"""', m.end())
    template = fj_src[m.end():end]
    class _D(dict):
        def __missing__(self, k): return "<" + k + ">"
    try:
        rendered = template.format_map(_D())
        check(f"HTML_TEMPLATE.format_map() renders cleanly ({len(rendered):,} chars)", True)
    except Exception as e:
        check("HTML_TEMPLATE.format_map() renders cleanly", False, f"{type(e).__name__}: {str(e)[:200]}")
else:
    check("HTML_TEMPLATE anchor found", False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
