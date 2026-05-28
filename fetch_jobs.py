#!/usr/bin/env python3
"""
HealthTech Jobs Fetcher
-----------------------
Pulls open roles from Greenhouse, Lever, and Ashby ATS APIs for a curated
list of healthcare / health-tech companies. Stores them in a local SQLite
database, scores each job for relevance to a senior healthcare-IT leader,
and generates a single-file HTML dashboard.

No scraping — only public ATS APIs (legal + reliable).
"""

import json
import os
import re
from matcher.canonical import canonical_company  # extracted Phase 1
# Scrapers — extracted to scrapers/ (Phase 4 of split refactor).
from scrapers._http import fetch_json
from scrapers.greenhouse import fetch_greenhouse
from scrapers.greenhouse import _extract_greenhouse_salary
from scrapers.lever import fetch_lever
from scrapers.lever import _extract_lever_salary
from scrapers.ashby import fetch_ashby
from scrapers.ashby import _extract_ashby_salary
from scrapers.workable import fetch_workable
from scrapers.icims import fetch_icims
from scrapers.smartrecruiters import fetch_smartrecruiters
from scrapers.pinpoint import fetch_pinpoint
from scrapers.teamtailor import fetch_teamtailor
from scrapers.recruitee import fetch_recruitee
from scrapers.wellfound import fetch_wellfound
from scrapers.trueup import fetch_trueup
from scrapers.workday import fetch_workday
from scrapers.wttj import fetch_wttj
from scrapers.remoteok import fetch_remoteok
from scrapers.yc import fetch_yc
from scrapers.hn_hiring import fetch_hn_hiring
from scrapers.healthecareers import fetch_healthecareers
from scrapers.himss import fetch_himss

# SOURCES dispatch — built here because it references all the per-ATS scrapers
SOURCES = {
    "greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby,
    "workable": fetch_workable, "workday": fetch_workday, "wttj": fetch_wttj,
    "icims": fetch_icims, "smartrecruiters": fetch_smartrecruiters,
    "pinpoint": fetch_pinpoint, "teamtailor": fetch_teamtailor,
    "recruitee": fetch_recruitee, "wellfound": fetch_wellfound,
    "trueup": fetch_trueup, "remoteok": fetch_remoteok, "yc": fetch_yc,
    "hn_hiring": fetch_hn_hiring, "healthecareers": fetch_healthecareers,
    "himss": fetch_himss,
}
# Scoring cluster — extracted to matcher/scoring.py (Phase 2 of split refactor).
# fetch_jobs.py keeps the names visible for backward compat with the rest of this file.
from matcher import scoring as _scoring
from matcher.scoring import (
    score_job, detect_title_stage, days_since_posted, freshness_multiplier,
    trajectory_match, is_recruiter_listing, classify_company_type,
    is_remote, is_senior, hiring_velocity_boost, recently_funded_boost,
    parse_jd_sections,
    SENIOR_TITLE_TERMS, RELEVANCE_TERMS, SCAM_TERMS, AGENCY_TERMS,
    # Phase 2.5: constants moved out of fetch_jobs.py into scoring.py
    IRRELEVANT_TITLE_TERMS, RECRUITER_BLURBS, RECRUITING_FIRMS_SET,
    SINGLE_WORD_FILTERS, STAGE_ORDER,
    TITLE_STAGE_EARLY, TITLE_STAGE_EXEC, TITLE_STAGE_INTERN,
    TITLE_STAGE_MID, TITLE_STAGE_NEWGRAD, TITLE_STAGE_SENIOR_IC,
)
# Underscore-prefixed re-exports
_CONSULTING_JD_PHRASES = _scoring._CONSULTING_JD_PHRASES
_CONSULTING_NAME_PATTERNS = _scoring._CONSULTING_NAME_PATTERNS
_JD_SECTION_HEADERS = _scoring._JD_SECTION_HEADERS
_STAFFING_NAME_PATTERNS = _scoring._STAFFING_NAME_PATTERNS
# Backward-compat aliases for underscore-prefixed names
_is_irrelevant_title = _scoring._is_irrelevant_title
_get_company_stage = _scoring._get_company_stage
_ROLE_STOPWORDS = _scoring._ROLE_STOPWORDS
_INDUSTRY_STOPWORDS = _scoring._INDUSTRY_STOPWORDS
COMPANY_STAGE_CACHE = _scoring.COMPANY_STAGE_CACHE

# SKILLS_PROFILE is per-user state. The moved score_job reads it via
# matcher.scoring.SKILLS_PROFILE. Keep a fetch_jobs-level copy too so the
# remaining ~50 SKILLS_PROFILE references in this file work unchanged.
SKILLS_PROFILE = None

def _set_skills_profile(profile):
    """Single setter that propagates to scoring module + local global."""
    global SKILLS_PROFILE
    SKILLS_PROFILE = profile
    _scoring.SKILLS_PROFILE = profile


# Catalog loaders + globals — extracted to matcher/catalogs.py (Phase 1).
from matcher import catalogs as _catalogs
_catalogs.load_vc_portfolio()
_catalogs.load_healthtech_catalog()
VC_PORTFOLIO_COMPANIES = _catalogs.VC_PORTFOLIO_COMPANIES
HEALTHTECH_COMPANIES = _catalogs.HEALTHTECH_COMPANIES
HEALTHTECH_SET = _catalogs.HEALTHTECH_SET
_load_vc_portfolio = _catalogs.load_vc_portfolio
_load_healthtech_catalog = _catalogs.load_healthtech_catalog
_merge_healthtech_catalog = _catalogs.merge_healthtech_catalog
_merge_vc_portfolio_companies = _catalogs.merge_vc_portfolio_companies

# Phase 5: storage + role_family extracted
from storage.db import (
    get_conn, upsert_job, fingerprint,
    _build_company_industries, _slugify_company_name, SCHEMA, DB_PATH,
)
from storage.profile import load_skills_profile, load_users, _careers_root
from matcher.role_family import (
    _detect_role_family, _user_role_family, _is_role_family_mismatch,
    ROLE_FAMILIES, OPEN_USER_FAMS, INCOMPATIBLE_PAIRS,
)
_merge_user_target_companies = _catalogs._merge_user_target_companies

import sqlite3
import sys
import time
from datetime import datetime, timezone
from hashlib import sha256
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Ghost job threshold (days). Listings older than this are flagged as
# possibly not actively hiring.
GHOST_DAYS = 14  # Tightened 2026-05-26 from 30 to cut stale 404-prone listings

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "jobs.db")
COMPANIES_PATH = os.path.join(ROOT, "companies.json")
DASHBOARD_PATH = os.path.join(ROOT, "index.html")

# --- Profile-specific scoring (tuned for Geetanjali Arora) ---------------

# Senior leadership signal — title must contain at least one of these

# Healthcare-IT / digital transformation relevance — bonus points

# Red flags — these subtract from score

# Staffing-agency / third-party recruiter giveaways

# Contract-employment signals — used to classify employment_type per job.
# Strong phrases unlikely to false-positive on full-time roles.
CONTRACT_STRONG_PHRASES = [
    "fractional", "interim",
    "1099", "c2c", "c2h", "w2 hourly",
    "consulting engagement", "contract role", "contract position",
    "contract-to-hire", "contract to hire",
    "fixed-term contract", "fixed term contract",
    "project-based engagement", "freelance",
    "12-month contract", "6-month contract", "3-month contract",
    "9-month contract", "18-month contract",
    "temporary contract", "temp contract",
]

# Title-only contract markers (more specific to avoid false positives)
CONTRACT_TITLE_MARKERS = [
    "fractional", "interim", "1099 ",
]

# Signals that indicate a permanent / full-time role
FULL_TIME_PHRASES = [
    "full-time", "full time", "permanent role", "permanent position",
    "401(k)", "401k", "stock options", "rsu", "vested over",
    "equity grant", "fully remote, full-time",
]


def detect_employment_type(job):
    """Return 'contract', 'full-time', or 'unknown' for a job."""
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    blob = title + " " + desc

    # Title-only contract markers — strong enough to classify on title alone
    for m in CONTRACT_TITLE_MARKERS:
        if m in title:
            return "contract"
    # Strong contract phrases anywhere
    for p in CONTRACT_STRONG_PHRASES:
        if p in blob:
            return "contract"
    # Otherwise, look for permanent / FTE signals
    for p in FULL_TIME_PHRASES:
        if p in blob:
            return "full-time"
    return "unknown"


# --- HTTP helpers --------------------------------------------------------

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HealthTechJobsFetcher/1.0"




# --- ATS adapters --------------------------------------------------------




































def _dbg_to_file(source_key, msg):
    """Write a diagnostic line to reports/{source}_debug.log so we can
    iterate on these scrapers when their HTML/JSON changes."""
    try:
        os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
        with open(os.path.join(ROOT, "reports", f"{source_key}_debug.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass













# --- Utilities -----------------------------------------------------------

def _strip_html(s):
    import html as _html_mod
    s = s or ""
    # Some sources pre-encode entities (&lt;p&gt;…). Decode first so the regex catches tags.
    s = _html_mod.unescape(_html_mod.unescape(s))
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:4000]


STOP_WORDS = {"of", "the", "and", "for", "a", "an", "to", "with", "in", "on", "at", "by", "or"}


# Titles that look healthcare-y but aren't a fit for Geetanjali's profile
# (senior product / digital transformation / IT in healthcare — NOT a clinician,
# pharmacist, nurse, medical affairs, or pure sales/marketing role).


# Single tokens that should match on word boundary only (so "sales" doesn't catch "salesforce")


# --- E1: Career-stage detection from job title --------------------------


def stage_compatible(user_stage, job_stage):
    """A job is compatible if it's within 1 step of the user's stage on either side.
    user_stage and job_stage are strings; missing values default to compatible (don't drop on no-signal)."""
    if not user_stage or not job_stage:
        return True
    u = STAGE_ORDER.get(user_stage)
    j = STAGE_ORDER.get(job_stage)
    if u is None or j is None:
        return True
    return abs(u - j) <= 1

# --- E4: Recruiter / staffing-agency listing detection ------------------
def _load_recruiting_firms_set():
    try:
        with open(os.path.join(ROOT, "companies.json"), "r", encoding="utf-8") as f:
            d = json.load(f)
        firms = d.get("_recruiting_firms", []) or []
        return {f.strip().lower() for f in firms if isinstance(f, str) and f.strip()}
    except Exception:
        return set()


def _build_positive_re():
    """Build a word-boundary regex from POSITIVE_TITLE_THEMES so substring bleed-through
    ('cto' matching 'director', 'product' matching 'production') is impossible."""
    global _POSITIVE_THEME_RE
    parts = []
    for theme in POSITIVE_TITLE_THEMES:
        # Allow flexible whitespace inside multi-word themes
        escaped = re.escape(theme).replace(r"\ ", r"\s+")
        parts.append(r"\b" + escaped + r"\b")
    _POSITIVE_THEME_RE = re.compile("|".join(parts), re.I)


# === Universal "never relevant" titles =====================================
# Bank back-office, IC engineering, pre-sales field roles, content production.
# Categories no user on this platform wants regardless of industry. Hard-
# excluded BEFORE the target-company override so e.g. "Branch Banking
# Regional Executive" at Wells Fargo is killed even when Wells is in the
# user's targetCompanies list.
NEVER_RELEVANT_TOKENS = [
    # Bank ops / branches / back-office
    "branch banking", "branch manager", "branch executive", "branch sales",
    "regional banking", "regional banking executive",
    "personal banker", "private banker", "relationship banker",
    "teller", "investment banking analyst", "investment banking associate",
    # Trading floor / markets ops
    "trading platforms support", "trading floor", "trade support",
    "front office trading",
    # KYC / AML / fraud / complaints ops
    "kyc operations", "kyc analyst", "kyc specialist",
    "anti-money laundering", "aml analyst", "aml ops", "aml officer",
    "complaints oversight", "fraud analyst", "fraud specialist",
    "fraud investigator",
    # Lending / credit ops
    "debit operations", "loan officer", "credit analyst", "credit officer",
    "mortgage banker", "mortgage processor", "auto loan officer", "underwriter",
    # Pre-sales / field / customer engineering
    "field cto", "field cio", "field engineer", "solutions engineer",
    "identity specialist", "solutions specialist",
    # Video / content production
    "video strategist", "video producer", "video editor",
    "content moderator", "social media coordinator",
    # IC engineers (engineering LEADERSHIP titles - VP/Head/Director of
    # Engineering - still pass the per-user role gate; only IC titles
    # are blocked here)
    "software engineer", "software developer", "data engineer",
    "backend engineer", "frontend engineer", "full stack engineer",
    "fullstack engineer", "qa engineer", "test engineer",
    "automation engineer", "systems engineer", "platform engineer",
    "infrastructure engineer", "security engineer", "site reliability",
    "devops engineer", "machine learning engineer", "ml engineer",
    "research scientist", "language engineering", "language engineer",
    # FinOps / IT ops noise
    "cloud finops", "finops engineer", "finops analyst",
    # Generic IC ops / claims
    "operations associate", "operations analyst", "operations specialist",
    "operations coordinator", "office coordinator",
    "claims processor", "claims analyst", "claims adjuster",
    # Logistics / warehouse / field service
    "logistics it", "logistics technician", "logistics technical lead",
    "warehouse associate", "warehouse manager",
]

_NEVER_RELEVANT_RE = None

def _build_never_re():
    global _NEVER_RELEVANT_RE
    parts = []
    for tok in NEVER_RELEVANT_TOKENS:
        escaped = re.escape(tok).replace(r"\ ", r"\s+")
        parts.append(r"\b" + escaped + r"\b")
    _NEVER_RELEVANT_RE = re.compile("|".join(parts), re.I)

def _is_never_relevant(title):
    """Universal hard-exclude. Applied before any other gate."""
    global _NEVER_RELEVANT_RE
    if _NEVER_RELEVANT_RE is None: _build_never_re()
    return bool(_NEVER_RELEVANT_RE.search(title or ""))


# Words that appear in any senior title but say nothing about which role


def _token_matches(needle, haystack_tokens):
    """A user-token matches a title-token if equal, OR if one is a
    prefix of the other AND the shorter token has >= 4 characters.
    Lets 'health' match 'healthcare' and 'inform' match 'informatics'
    without leaking short tokens like 'it' / 'hr'."""
    if needle in haystack_tokens:
        return True
    if len(needle) < 4:
        return False
    for ht in haystack_tokens:
        if len(ht) < 4:
            continue
        if needle.startswith(ht) or ht.startswith(needle):
            return True
    return False


def _matches_user_role(title, profile):
    """Relaxed per-user title gate. The title passes if ANY of:
      a) all tokens of one of the user's targetTitles match the title, OR
      b) primaryRole tokens match the title with a seniority indicator, OR
      c) the title contains at least one keyword/specialty/industry/regulation/
         framework/technology term from the user's profile.

    Goal: maximize volume of plausibly-relevant roles. We trust the LATER
    scoring + sort to push best fits to the top, rather than hard-dropping
    here. Users get hired by APPLYING — that needs many candidate jobs.
    """
    if not title or not profile:
        return False
    title_l = title.lower()
    title_tokens = set(re.findall(r"[a-z]+", title_l))
    if not title_tokens:
        return False

    # (a) Exact targetTitle token match
    for tt in (profile.get("targetTitles") or []):
        tt_l = (tt or "").lower().strip()
        if len(tt_l) < 3:
            continue
        tt_tokens = set(re.findall(r"[a-z]+", tt_l)) - _ROLE_STOPWORDS
        if not tt_tokens:
            continue
        if all(_token_matches(t, title_tokens) for t in tt_tokens):
            return True

    # (b) primaryRole tokens + seniority signal
    primary = (profile.get("primaryRole") or "").lower()
    primary_tokens = set(re.findall(r"[a-z]+", primary)) - _ROLE_STOPWORDS
    if primary_tokens and all(_token_matches(t, title_tokens) for t in primary_tokens):
        seniority_indicators = {
            "vp", "vice", "president", "director", "head", "chief",
            "principal", "staff", "senior", "sr", "lead", "executive",
            "ceo", "coo", "cto", "cio", "ciso", "cpo", "cdo",
            "manager", "associate", "analyst",
        }
        if seniority_indicators & title_tokens:
            return True

    # (c) Loose match — title contains any single keyword/specialty/etc.
    # This is the "get jobs faster, maximize volume" lever per Amit 2026-05-26.
    for field in ("keywords", "specialties", "regulations", "frameworks",
                  "technologies", "certifications"):
        for term in profile.get(field, []) or []:
            if not term:
                continue
            term_l = (term or "").lower().strip()
            if len(term_l) < 3:
                continue
            # Multi-word: substring match; single-word: word-boundary match.
            if " " in term_l or "-" in term_l:
                if term_l in title_l:
                    return True
            else:
                if re.search(r"\b" + re.escape(term_l) + r"\b", title_l):
                    return True

    return False


def _has_positive_theme(title, profile):
    """Title qualifies if it contains a positive domain theme OR any of the
    AI-extracted profile signals (keywords, specialties, targetTitles, regulations)."""
    global _POSITIVE_THEME_RE
    if _POSITIVE_THEME_RE is None:
        _build_positive_re()
    t = title or ""
    if _POSITIVE_THEME_RE.search(t):
        return True
    if profile:
        t_lower = t.lower()
        # Check across multiple richer profile fields
        for field in ("keywords", "specialties", "targetTitles", "regulations", "frameworks", "technologies"):
            for term in profile.get(field, []) or []:
                if not term:
                    continue
                term_l = term.lower()
                # Multi-word terms use substring match; single words use word boundaries
                if " " in term_l or "-" in term_l:
                    if term_l in t_lower:
                        return True
                else:
                    if re.search(r"\b" + re.escape(term_l) + r"\b", t_lower):
                        return True
    return False


# ============================================================
# F3: Seniority rank — maps a job title and a user's seniorityLevel
# to a 0..5 rank. Higher = more senior. Used to filter out jobs below
# the user's level.
# ============================================================
def _job_seniority_rank(title):
    t = (title or "").lower()
    if re.search(r"\b(ceo|cto|cio|coo|ciso|cpo|cdo|cfo|chief|founder|co-founder)\b", t):
        return 5
    if re.search(r"\b(svp|evp|senior vice president|executive vice president|vp|vice president)\b", t):
        return 4
    if re.search(r"\b(director|head of|managing director|general manager|gm)\b", t):
        return 3
    if re.search(r"\b(principal|staff|senior|sr|lead|architect)\b", t):
        return 2
    if re.search(r"\b(manager)\b", t):
        return 1
    return 0


def _user_min_seniority_rank(profile):
    if not profile:
        return 0
    sl = (profile.get("seniorityLevel") or "").lower()
    pr = (profile.get("primaryRole") or "").lower()
    blob = sl + " " + pr
    if not blob.strip():
        return 0
    # Use word-boundary regex (not substring) so "director" doesn't match "cto"
    def _has(*terms):
        for t in terms:
            if re.search(r"\b" + re.escape(t) + r"\b", blob):
                return True
        return False
    # Loosened (2026-05-26): each level returns one less than before, so a
    # VP sees Manager-level roles too, a Director sees Manager+, a Senior
    # sees ICs without title prefix. The goal is volume — landing a job
    # beats landing the PERFECT job 6 months from now. Final scoring still
    # ranks the best fits to the top.
    if _has("ceo", "cto", "cio", "coo", "ciso", "cpo", "cdo", "cfo", "chief", "founder"):
        return 3   # Chiefs still see Director+ as proper fits
    if _has("vp", "vice president", "svp", "evp"):
        return 2   # VPs see Senior IC + Manager
    if _has("director", "head of", "principal", "managing director"):
        return 1   # Directors see Manager+
    if _has("senior", "sr", "staff", "lead"):
        return 0   # Seniors see everything (rank 0 = no floor)
    return 0


# ============================================================
# F4: Salary filter helpers
# ============================================================
def _passes_salary_filter(salary_str, salary_max_parsed, profile, location=None, description=None):
    """Return True if this row should pass the salary gate based on user prefs.
    profile.salaryFloor (number) — hide jobs below this
    profile.hideNoSalary (bool)  — hide jobs whose salary_range is empty
    Empty strings/None disable the filter.

    Smarter (2026-05-27):
    - If ATS salary field is missing, try to extract from JD body
    - If JD is from a disclosure-required jurisdiction (NY/CA/WA/CO/IL) AND
      no salary visible, treat as 'company hid required disclosure' — soft fail
    """
    if not profile:
        return True
    hide_no_sal = bool(profile.get("hideNoSalary"))
    floor = profile.get("salaryFloor")
    try:
        floor_n = int(float(floor)) if floor else 0
    except (TypeError, ValueError):
        floor_n = 0
    has_salary = bool((salary_str or "").strip())
    # Body extraction fallback when ATS field is empty
    if not has_salary and description:
        try:
            lo, hi = _parse_salary_from_jd_body(description)
            if hi:
                salary_max_parsed = hi
                has_salary = True
        except Exception:
            pass
    if hide_no_sal and not has_salary:
        return False
    # Disclosure-required jurisdiction without visible salary = suspicious
    if hide_no_sal and not has_salary and location and _is_disclosure_required(location):
        return False
    if floor_n and has_salary and salary_max_parsed and salary_max_parsed < floor_n:
        return False
    return True


# ============================================================
# F1: Negative-title filter (server side mirror of user dismissals)
# ============================================================
def _matches_negative_title(title, profile):
    """Return True if the title matches any of the user's negativeTitles
    (subset-of-tokens match, prefix-aware, same as _matches_user_role)."""
    if not title or not profile:
        return False
    neg = profile.get("negativeTitles") or []
    if not neg:
        return False
    title_l = title.lower()
    title_tokens = set(re.findall(r"[a-z]+", title_l))
    if not title_tokens:
        return False
    for nt in neg:
        nt_l = (nt or "").lower().strip()
        if len(nt_l) < 3:
            continue
        nt_tokens = set(re.findall(r"[a-z]+", nt_l)) - _ROLE_STOPWORDS
        if not nt_tokens:
            continue
        if all(_token_matches(t, title_tokens) for t in nt_tokens):
            return True
    return False


def _normalize_title(title):
    """Lowercase, strip stop words, then concatenate alphanumerics so minor wording
    differences ('Director of Product' vs 'Director, Product') collapse to the same hash."""
    words = re.split(r"[^a-z0-9]+", (title or "").lower())
    return "".join(w for w in words if w and w not in STOP_WORDS)




# Heuristic company-type classifier (2026-05-27).
# Result is one of: 'consulting' | 'staffing' | 'in-house' | 'unknown'
# Used as a SOFT multiplier on score (consulting 0.45, staffing 0.0, in-house 1.0, unknown 1.0)
# instead of a hard binary exclude. Cheap + cacheable per company per session.

def company_type_multiplier(kind):
    return {"consulting": 0.45, "staffing": 0.0, "in-house": 1.0, "unknown": 1.0}.get(kind, 1.0)


def _load_recruiters_by_company():
    try:
        with open(os.path.join(ROOT, "recruiters.json"), "r", encoding="utf-8") as f:
            d = json.load(f)
        out = {}
        for k, v in (d.get("companies") or {}).items():
            if isinstance(k, str):
                out[k.strip().lower()] = v
        return out
    except Exception:
        return {}
RECRUITERS_BY_COMPANY = _load_recruiters_by_company()

DEFAULT_INDUSTRIES = ["healthcare", "digital-health"]


# --- Industry matching --------------------------------------------------


def _industry_tokens(industries):
    """Return a set of lowercase normalized tokens from a list of industry strings."""
    tokens = set()
    for s in industries or []:
        # Normalize: lowercase, replace separators with space
        norm = re.sub(r"[^a-z0-9]+", " ", str(s).lower())
        for word in norm.split():
            if len(word) > 2 and word not in _INDUSTRY_STOPWORDS:
                tokens.add(word)
    return tokens


def _industry_match(company_industries, user_industries):
    """Returns True if the company's industries overlap with the user's profile industries."""
    if not user_industries:
        return True  # No profile → show all
    if not company_industries:
        return False  # Untagged company → hide
    ct = _industry_tokens(company_industries)
    ut = _industry_tokens(user_industries)
    return bool(ct & ut)








# --- Role-family classification (2026-05-26) ----------------------------
# Drops jobs where the title's role family fundamentally mismatches the user's.
# Examples this catches:
#   - Amit (risk/GRC) sees "Capco .NET Engineer" → engineering ≠ risk → drop
#   - Geetu (product) sees "UltaHost COO" → operations-coo ≠ product → drop
#   - Either sees "Sales Rep" → sales ≠ their family → drop
# Note: when role-family is ambiguous we DO NOT drop — we prefer over-include.


# Families an exec might pivot INTO without being a literal title match.
# When user_fam is in the "open" set, allow any family.

# When job_fam is None (ambiguous), we never drop on family.
# When user_fam is None (ambiguous), we never drop on family.
# Engineering doesn't fit risk-grc / product / digital-transformation users
for u in ("risk-grc", "product", "digital-transformation", "marketing-ic", "sales-rep", "legal-ic"):
    for j in ("engineering", "qa", "clinical", "design"):
        INCOMPATIBLE_PAIRS.add((u, j))
# COO doesn't fit risk-grc / product / engineering / data-analyst users (executives but wrong family)
for u in ("risk-grc", "product", "engineering", "data-analyst", "marketing-ic"):
    INCOMPATIBLE_PAIRS.add((u, "operations-coo"))
# Engineering users shouldn't see risk-grc / sales / clinical
for u_fam, j_fams in [("engineering", ["sales-rep", "clinical", "marketing-ic"])]:
    for j in j_fams:
        INCOMPATIBLE_PAIRS.add((u_fam, j))
# Product users shouldn't see sales-rep / engineering / qa / clinical / marketing / customer-success
for u_fam, j_fams in [("product", ["sales-rep", "engineering", "qa", "clinical", "marketing-ic", "customer-success", "recruiting-hr", "finance-ic", "legal-ic"])]:
    for j in j_fams:
        INCOMPATIBLE_PAIRS.add((u_fam, j))
# Digital-transformation users behave like product execs — same drop set
for j in ("engineering", "qa", "sales-rep", "operations-coo", "clinical", "design", "marketing-ic", "customer-success", "recruiting-hr", "finance-ic", "legal-ic"):
    INCOMPATIBLE_PAIRS.add(("digital-transformation", j))









# --- Main pipeline -------------------------------------------------------







def run():
    with open(COMPANIES_PATH) as f:
        companies = json.load(f)

    _build_company_industries(companies)

    # Path 2: merge per-user target companies (AI-suggested) into the scrape list,
    # then refresh the industry mapping to include them. No-op if no user profile
    # has targetCompanies yet (i.e. before the Worker /parse-resume prompt update).
    _merge_user_target_companies(companies)
    # Path 3: merge VC-portfolio discovered companies — pool of startups/scaleups
    # surfaced by /admin/discover-vc-portfolio + the discover-vc-portfolio.yml
    # weekly workflow. Adds them to whichever ATS hint Claude assigned.
    _merge_vc_portfolio_companies(companies)
    _merge_healthtech_catalog(companies)
    _build_company_industries(companies)

    conn = get_conn()
    totals = {"greenhouse": 0, "lever": 0, "ashby": 0}
    failures = []

    totals["workday"] = 0
    for source, fetcher in SOURCES.items():
        entries = companies.get(source, [])
        print(f"\n[{source}] {len(entries)} companies")
        for i, entry in enumerate(entries, 1):
            # Backward compat: entry may be a slug string OR an object {slug, industries}
            if isinstance(entry, dict) and entry.get("slug"):
                fetch_arg = entry["slug"]
            elif isinstance(entry, dict):
                fetch_arg = entry  # workday-style
            else:
                fetch_arg = entry
            label = entry.get("name", entry.get("tenant", "?")) if isinstance(entry, dict) else entry
            try:
                jobs = fetcher(fetch_arg)
                if not jobs:
                    failures.append(f"{source}:{label}")
                    print(f"  [{i}/{len(entries)}] {label}: 0 jobs (slug may be invalid)")
                    continue
                for j in jobs:
                    upsert_job(conn, j)
                totals[source] = totals.get(source, 0) + len(jobs)
                print(f"  [{i}/{len(entries)}] {label}: {len(jobs)} jobs")
            except Exception as e:
                failures.append(f"{source}:{label} ({e})")
                print(f"  [{i}/{len(entries)}] {label}: ERROR — {e}")
            time.sleep(0.15)  # be polite

        conn.commit()

    print(f"\nTotals: {totals}")
    print(f"Failures: {len(failures)} (companies returned no data — likely bad slugs)")

    # Note: scoring used the LAST loaded skills profile during fetch. The dashboard
    # generation step re-loads each user's profile before filtering for that user,
    # so per-user views are correct even if scoring is global.
    generate_all_dashboards(conn)
    conn.close()



def _parse_salary_from_jd_body(description):
    """Extract salary range from common JD-body patterns when the ATS didn't
    expose a structured salary field. Looks for $NNN,NNN - $NNN,NNN, $NNNk – $NNNk,
    'base salary range', etc. Returns (min_dollars, max_dollars) or (0, 0)."""
    if not description:
        return (0, 0)
    text = description[:4000]  # bound the work; salary disclosures are near the top
    # Common patterns from Greenhouse / Lever / Ashby disclosures
    PATTERNS = [
        # $180,000 - $250,000 or $180,000–$250,000 (em-dash)
        r"\$(\d{2,3}(?:,\d{3})+)\s*[-\u2013\u2014to]+\s*\$(\d{2,3}(?:,\d{3})+)",
        # $180K - $250K
        r"\$(\d{2,3})\s*[Kk]\s*[-\u2013\u2014to]+\s*\$(\d{2,3})\s*[Kk]",
        # USD 180,000 - 250,000
        r"USD\s*(\d{2,3}(?:,\d{3})+)\s*[-\u2013\u2014to]+\s*(\d{2,3}(?:,\d{3})+)",
    ]
    for pat in PATTERNS:
        m = re.search(pat, text)
        if m:
            try:
                lo = int(m.group(1).replace(",", ""))
                hi = int(m.group(2).replace(",", ""))
                # If "K" pattern, scale up
                if "K" in pat:
                    lo *= 1000; hi *= 1000
                if 30_000 <= lo <= 2_000_000 and lo <= hi:
                    return (lo, hi)
            except (ValueError, IndexError):
                continue
    return (0, 0)


# Disclosure-required regions: jurisdictions where companies MUST post salary
# in the JD. If a JD from these markets is missing salary, that's a red flag.
_DISCLOSURE_LOCATIONS = (
    "new york", " ny,", " ny ", "nyc",
    "california", "san francisco", " sf,", " ca,", " ca ", "los angeles",
    "washington", " wa,", "seattle",
    "colorado", "denver",
    "illinois", "chicago",  # 2025 expansion
)

def _is_disclosure_required(location):
    """True if posting is in a jurisdiction with salary-disclosure law."""
    if not location: return False
    L = location.lower()
    return any(t in L for t in _DISCLOSURE_LOCATIONS)


def _parse_salary_max(salary_text):
    """Return the highest dollar value appearing in the salary string (in whole dollars), or 0."""
    if not salary_text:
        return 0
    best = 0
    for m in re.finditer(r"\$?\s?(\d{2,3}(?:,\d{3})+|\d{2,3}\s?k|\d{4,7})", salary_text, flags=re.IGNORECASE):
        raw = m.group(1).replace(",", "").replace(" ", "")
        try:
            if raw.lower().endswith("k"):
                val = int(float(raw[:-1]) * 1000)
            else:
                val = int(raw)
            if val > best:
                best = val
        except Exception:
            continue
    return best


def _location_remote_ok(r, user_locations, remote_pref):
    """Filter for user's location + remote preference.
    r[3] = loc (string), r[9] = remote (0|1).
    remote_pref: "remote-only" | "hybrid" | "onsite" | "any" | None"""
    job_loc = (r[3] or "").lower()
    is_remote_job = bool(r[9])
    pref = (remote_pref or "any").lower().strip()

    # Remote-only users: drop non-remote jobs
    if pref == "remote-only" and not is_remote_job:
        return False

    # Onsite-only users: drop fully-remote jobs (allow hybrid via location match)
    if pref == "onsite" and is_remote_job and not any(
        (loc or "").lower() in job_loc for loc in (user_locations or [])
    ):
        return False

    # If user listed specific locations, the job must either be remote OR match one of them
    if user_locations:
        normalized = [(loc or "").lower().strip() for loc in user_locations if loc]
        # "remote (us)" type entries effectively whitelist remote jobs
        wants_remote = any("remote" in loc for loc in normalized)
        location_match = any(loc and loc in job_loc for loc in normalized if "remote" not in loc)
        if not (is_remote_job and wants_remote) and not location_match:
            # Be permissive when remotePreference is "any" or "hybrid"
            if pref in ("remote-only", "onsite"):
                return False
            # For hybrid/any with no location match, still return True (soft filter elsewhere)
    return True


# ---------------------------------------------------------------------------
# Wizard v3 (2026-05-26) — clean self-contained replacement for the old wizard.
# Appended to dashboard HTML AFTER HTML_TEMPLATE.format() — no brace escaping.
# ---------------------------------------------------------------------------

from dashboard.wizard import WIZARD_V3_BLOCK  # extracted Phase 3


def generate_dashboard(conn, user_slug="geetu", user_name="Geetanjali Arora", output_path=None):
    """Generate the dashboard HTML for a specific user.
    output_path defaults to <user_slug>.html (or index.html for backward compat if slug='geetu')."""
    # Load this user's skills profile from the Worker (sets the global used by score_job)
    _set_skills_profile(load_skills_profile(user_slug))
    if SKILLS_PROFILE:
        _tc = SKILLS_PROFILE.get("targetCompanies", [])
        print(f"[diag:{user_slug}] loaded profile, targetCompanies len={len(_tc) if isinstance(_tc, list) else type(_tc).__name__}, first={(_tc[0] if (isinstance(_tc, list) and _tc) else None)}", flush=True)
    if SKILLS_PROFILE:
        print(f"[skills-profile:{user_slug}] {SKILLS_PROFILE.get('primaryRole','?')} "
              f"· {len(SKILLS_PROFILE.get('keywords', []))} keywords", flush=True)
    else:
        print(f"[skills-profile:{user_slug}] not available — using fallback themes only", flush=True)

    if output_path is None:
        output_path = os.path.join(ROOT, f"{user_slug}.html")

    rows = conn.execute("""
        SELECT fingerprint, company_name, title, location, url, posted_at, first_seen, last_seen,
               sightings, remote, senior, score, description, salary_range, employment_type, industries
        FROM jobs
        WHERE last_seen >= datetime('now', '-30 days')
        ORDER BY score DESC, last_seen DESC
        LIMIT 20000
    """).fetchall()

    # Populate HIRING_VELOCITY cache — count senior roles per company in past 30d
    global HIRING_VELOCITY
    HIRING_VELOCITY = {}
    try:
        velo_rows = conn.execute("""
            SELECT LOWER(TRIM(company_name)) AS co, COUNT(*) AS n
            FROM jobs
            WHERE last_seen >= datetime('now', '-30 days')
              AND senior = 1
            GROUP BY co
            HAVING n >= 3
        """).fetchall()
        for co, n in velo_rows:
            if co:
                HIRING_VELOCITY[co] = int(n)
        if HIRING_VELOCITY:
            print(f'[velocity] {len(HIRING_VELOCITY)} actively-scaling companies (3+ senior roles in 30d)', flush=True)
    except Exception as _e:
        print(f'[velocity] skipped: {_e}', flush=True)

    # Snapshot for the "why hidden?" debug tool — we'll diff against the
    # final kept rows after all filters + dedup + top-1000 cutoff run.
    _original_rows = list(rows)

    # PER-USER RE-SCORING (2026-05-26): score_job runs at scrape time with
    # SKILLS_PROFILE=None, so all the per-user title/keyword/stage logic in
    # score_job is dead during the scrape. To make per-user scoring actually
    # bite, re-run score_job for each row HERE with the now-loaded user
    # profile, and replace the DB score with the user-specific one.
    if SKILLS_PROFILE:
        _rescored = []
        for r in rows:
            # Build a job dict with every field score_job touches: title,
            # description, location, company_name. Defensive: r[*] may be None.
            _job = {
                "title":        r[2]  or "",
                "location":     r[3]  or "",
                "description":  r[12] or "",
                "company_name": r[1]  or "",
                "salary_range": r[13] or "",
            }
            try:
                new_score = score_job(_job)
            except Exception:
                new_score = r[11] or 0  # fall back to DB score on any error
            _row = list(r)
            _row[11] = new_score
            _rescored.append(tuple(_row))
        rows = _rescored

    # E5: Freshness boost — re-rank so jobs first-seen in the last 48h surface
    # above stale ones at similar score. This is the "get people jobs FASTER"
    # lever — today's posts at the top, 3-week-olds at the bottom.
    def _hours_old(ts):
        if not ts:
            return 9999
        try:
            from datetime import datetime as _dt, timezone as _tz
            dt = _dt.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_tz.utc)
            now = _dt.now(_tz.utc)
            return max(0, (now - dt).total_seconds() / 3600.0)
        except Exception:
            return 9999

    def _fresh_bonus(first_seen):
        # Relevance-first (2026-05-27): much stronger recency bias.
        # New postings get applications fast; week-old jobs are already in
        # the pile. Reward speed.
        h = _hours_old(first_seen)
        if h <= 24: return 25    # last day — huge bump (cuts to front)
        if h <= 72: return 15    # last 3 days — strong bump
        if h <= 168: return 6    # last week — small bump
        if h <= 336: return 0    # 1-2 weeks — neutral
        return -5                # 2+ weeks — gently push down

    # Re-sort: effective_score = score + fresh_bonus DESC; tiebreak on most-recent last_seen DESC.
    rows = sorted(rows, key=lambda r: (int(r[11] or 0) + _fresh_bonus(r[6]), r[7] or ""), reverse=True)
    # No profile → no jobs. User must upload resume first to see anything.
    if not SKILLS_PROFILE:
        rows = []
    # Hide jobs that aren't a fit (blacklist)
    rows = [r for r in rows if not _is_irrelevant_title(r[2])]

    # Combine the title-keyword whitelist, the industry filter, and a
    # target-company override into a single pass (Slice B v2). The previous
    # behavior required BOTH title-pass AND industry-pass, which over-filtered
    # senior roles at verified target companies whose titles didn't happen to
    # contain a healthcare-flavored theme word. New semantics:
    #
    #   pass IF (title matches user themes/keywords AND industry overlaps)
    #     OR (job is senior=1 AND its company is in user's targetCompanies)
    #
    # When the user has no industries set, the industry check is treated as
    # always-pass so the title gate alone applies.
    if SKILLS_PROFILE:
        user_industries = (SKILLS_PROFILE.get("industries", []) or []) + (SKILLS_PROFILE.get("specialties", []) or [])
        target_company_names = {
            (tc.get("name") if isinstance(tc, dict) else tc or "").strip().lower()
            for tc in (SKILLS_PROFILE.get("targetCompanies") or [])
            if (tc.get("name") if isinstance(tc, dict) else tc)
        }
        # Company-size preference (Slice B v3). Prefer the new companySizeMix
        # (object with %s for each size) — hard-exclude any size at 0%. Fall
        # back to the older companySizePreferences (array of picked sizes) so
        # we don't break profiles that haven't been re-saved yet.
        size_mix = SKILLS_PROFILE.get("companySizeMix") or {}
        if isinstance(size_mix, dict) and size_mix:
            size_prefs = {k.lower() for k, v in size_mix.items() if isinstance(v, (int, float)) and v > 0}
            if not size_prefs:
                size_prefs = {"startup", "midsize", "large"}
        else:
            prefs = SKILLS_PROFILE.get("companySizePreferences") or []
            size_prefs = {p.lower() for p in prefs if isinstance(p, str)} or {"startup", "midsize", "large"}
    else:
        user_industries = []
        target_company_names = set()
        size_prefs = {"startup", "midsize", "large"}

    # Load size lookup. Build a single map keyed by lowercased company_name and
    # by lowercased slug/tenant for fallback. Built once per dashboard.
    try:
        with open(COMPANIES_PATH) as _cf:
            _cdoc = json.load(_cf)
        _raw_sizes = _cdoc.get("_company_sizes") or {}
        _size_by_company = {}
        # 1. Workday entries: key by name (lowercase)
        for _e in _cdoc.get("workday", []):
            if isinstance(_e, dict) and _e.get("name") and _e["name"] in _raw_sizes:
                _size_by_company[_e["name"].lower()] = _raw_sizes[_e["name"]]
        # 2. Greenhouse/Lever/Ashby: slug -> tagged size. The DB stores
        #    company_name which may differ from slug, so we also keep the
        #    slug map and resolve at query time via _company_slug if needed.
        # For safety we store both name-lower and the slug itself.
        _slug_to_size = {k.lower(): v for k, v in _raw_sizes.items()}
        # 3. Staffing / recruiting firms — used for the "Recruiters: hide/show/only"
        #    dashboard toggle. Lowercased for case-insensitive match.
        _recruiter_names = {(s or "").strip().lower() for s in (_cdoc.get("_recruiting_firms") or [])}
    except Exception:
        _size_by_company = {}
        _slug_to_size = {}
        _recruiter_names = set()

    def _company_size(company_name, company_slug=""):
        """Best-effort lookup of size bucket for a job's company."""
        if not company_name:
            return None
        nm = company_name.strip().lower()
        if nm in _size_by_company:
            return _size_by_company[nm]
        if nm in _slug_to_size:
            return _slug_to_size[nm]
        slug = (company_slug or "").strip().lower()
        if slug and slug in _slug_to_size:
            return _slug_to_size[slug]
        return None


    def _passes_filters(r):
        title = r[2]
        company = (r[1] or "").strip().lower()
        senior_flag = r[10]
        salary_str = r[13]
        job_inds = (r[15] or "").split(",") if r[15] else []

        # Universal hard-exclude: bank back-office, IC engineers, pre-sales
        # field roles, content production. Applied BEFORE the target-company
        # override so e.g. "Branch Banking Regional Executive" at Wells Fargo
        # is killed even when Wells is in the user's targetCompanies list.
        if _is_never_relevant(title):
            return False

        # ROLE-FAMILY MISMATCH (2026-05-26): hard-drop jobs whose role family
        # is fundamentally incompatible with the user's primary role.
        # e.g. .NET Engineer for a risk-GRC exec, or COO for a product exec.
        if _is_role_family_mismatch(title, SKILLS_PROFILE):
            return False

        # F1: user dismissed similar titles before — hide.
        if SKILLS_PROFILE and _matches_negative_title(title, SKILLS_PROFILE):
            return False

        # F3 (disabled 2026-05-26): seniority floor turned off so users see
        # more roles. Score still rewards seniority-stage matches via the
        # E1 +6 bonus and the existing title-strength logic.

        # F4: salary floor + must-list-pay (only when user opted in).
        if SKILLS_PROFILE:
            smax = _parse_salary_max(salary_str)
            if not _passes_salary_filter(salary_str, smax, SKILLS_PROFILE):
                return False

        # Hard-filter by company-size preference when the user has selected
        # only some sizes. If size is unknown (untagged company), let it
        # through so we don't accidentally hide everything.
        if len(size_prefs) < 3:
            sz = _company_size(company)
            if sz is not None and sz not in size_prefs:
                return False

        # Title gate (2026-05-26 max-volume mode): the only hard cuts are
        # _is_never_relevant + _is_irrelevant_title + negativeKeywords. The
        # per-user title-match has become a SCORE INPUT, not a drop, so
        # users see the full pool of plausibly-relevant roles ordered by
        # fit. Goal per Amit: maximize volume so users apply faster.
        if not SKILLS_PROFILE:
            # No profile — fall back to the legacy broad-theme gate so the
            # dashboard is not literally empty.
            if not _has_positive_theme(title, None):
                return False
        # else: pass through — score_job decides ranking.

        # Target-company override: user explicitly named this employer, so
        # waive the industry-overlap check below. The title gate above
        # still had to pass.
        if senior_flag and company and company in target_company_names:
            return True

        if user_industries and job_inds:
            return _industry_match(job_inds, user_industries)
        return True  # no industry data on either side — title gate is enough

    rows = [r for r in rows if _passes_filters(r)]

    # Multi-location dedup: many enterprise employers (CVS, BMO, BofA) post
    # the same role in hundreds of stores/branches — separate fingerprints
    # because location is in the hash, but logically the same job. Collapse
    # to one card per (company, normalized title); record location count.
    _dedup = {}
    _location_counts = {}
    _order = []
    for r in rows:
        company_key = (r[1] or "").strip().lower()
        title_key = _normalize_title(r[2] or "")
        key = (company_key, title_key)
        if key in _dedup:
            _location_counts[key] += 1
            # Keep the row with the highest score
            if r[11] is not None and r[11] > (_dedup[key][11] or 0):
                _dedup[key] = r
        else:
            _dedup[key] = r
            _location_counts[key] = 1
            _order.append(key)
    rows = [_dedup[k] for k in _order]
    # Stash per-row location count so card rendering can show a "Nx locations" badge
    LOCATION_COUNTS = {(_dedup[k][0]): _location_counts[k] for k in _order}

    # Location + remote preference filter (Slice 2)
    if SKILLS_PROFILE:
        user_locations = SKILLS_PROFILE.get("preferredLocations", []) or []
        remote_pref = SKILLS_PROFILE.get("remotePreference") or (
            "remote-only" if SKILLS_PROFILE.get("remotePreferred") else "any"
        )
    else:
        user_locations = []
        remote_pref = "any"
    if user_locations or remote_pref not in ("any", None, ""):
        before_loc = len(rows)
        rows = [r for r in rows if _location_remote_ok(r, user_locations, remote_pref)]
        print(f"[location-remote:{user_slug}] filter pref={remote_pref!r} locs={user_locations[:3]} kept {len(rows)}/{before_loc}", flush=True)

    # Hide ghost jobs (listed > GHOST_DAYS) from default view
    def _not_ghost(r):
        posted_at, first_seen = r[5], r[6]
        ld = _days_old(posted_at) if posted_at else (_days_old(first_seen) if first_seen else 0)
        return ld is None or ld <= GHOST_DAYS
    rows = [r for r in rows if _not_ghost(r)]

    # Relevance-first top-50 (2026-05-27): cut from 1000 → 50. With heavy
    # wizard-pick weighting + recency bonus, the top 50 are the only jobs
    # that genuinely matter today. If user wants more, they can broaden
    # the bullseye via the wizard.
    TOP_N = 20  # was 50 — user asked for tighter feed
    rows = rows[:TOP_N]

    # ============================================================
    # WHY-HIDDEN TOOL — classify each dropped row with a reason code
    # so the dashboard's debug widget can answer "why isn't X in my feed?"
    # ============================================================
    _kept_fps = {r[0] for r in rows}
    _hidden_classified = []
    _SENIOR_GUARD_KW = {"vp","svp","evp","chief","cio","cto","cdo","coo","cfo","cro","cpo","ceo",
                        "principal","director","head","managing","executive","president","partner","lead","leader"}
    def _classify_hidden(r):
        title = (r[2] or "")
        title_l = title.lower()
        # 1) Hard blocklists
        if _is_irrelevant_title(title): return ("irrelevant_title", "")
        try:
            if _is_never_relevant(title): return ("never_relevant", "")
        except Exception: pass
        # 2) Role family mismatch (only if profile loaded)
        try:
            if SKILLS_PROFILE and _is_role_family_mismatch(title, SKILLS_PROFILE): return ("role_family_mismatch", "")
        except Exception: pass
        # 3) Negative keyword hit (word-boundary + senior-context aware, matches scorer)
        if SKILLS_PROFILE:
            neg = SKILLS_PROFILE.get("negativeKeywords") or []
            if neg:
                import re as _r2
                title_tokens = set(_r2.findall(r"\b[a-z]+\b", title_l))
                title_has_senior = bool(_SENIOR_GUARD_KW & title_tokens)
                if not title_has_senior:
                    for n in neg:
                        if not n: continue
                        n_tokens = set(_r2.findall(r"\b[a-z]+\b", n.lower()))
                        if n_tokens and n_tokens.issubset(title_tokens):
                            return ("negative_keyword", n)
        # 4) Salary floor
        salary_str = r[13]
        try:
            if SKILLS_PROFILE and not _passes_salary_filter(salary_str, _parse_salary_max(salary_str), SKILLS_PROFILE):
                return ("salary_floor", "")
        except Exception: pass
        # 5) Company size preference
        try:
            sz = _company_size((r[1] or "").strip().lower())
            if SKILLS_PROFILE and sz and 'size_prefs' in dir() and sz not in size_prefs:
                return ("company_size", sz)
        except Exception: pass
        # 6) Industry mismatch (only if not waived by target-company override)
        job_inds = (r[15] or "").split(",") if r[15] else []
        if SKILLS_PROFILE:
            user_inds = (SKILLS_PROFILE.get("industries", []) or []) + (SKILLS_PROFILE.get("specialties", []) or [])
            tc_names = {(tc.get("name") if isinstance(tc, dict) else tc or "").strip().lower()
                        for tc in (SKILLS_PROFILE.get("targetCompanies") or [])
                        if (tc.get("name") if isinstance(tc, dict) else tc)}
            co = (r[1] or "").strip().lower()
            if user_inds and job_inds:
                try:
                    if not _industry_match(job_inds, user_inds) and (r[10] != 1 or co not in tc_names):
                        return ("industry_mismatch", "")
                except Exception: pass
        # 7) Location / remote preference
        try:
            user_locs = (SKILLS_PROFILE.get("preferredLocations") or []) if SKILLS_PROFILE else []
            rp = (SKILLS_PROFILE.get("remotePreference") or "any") if SKILLS_PROFILE else "any"
            if (user_locs or rp not in ("any", None, "")) and not _location_remote_ok(r, user_locs, rp):
                return ("location", rp)
        except Exception: pass
        # 8) Ghost (too old)
        try:
            posted_at, first_seen = r[5], r[6]
            ld = _days_old(posted_at) if posted_at else (_days_old(first_seen) if first_seen else 0)
            if ld is not None and ld > GHOST_DAYS:
                return ("ghost", str(ld) + "d")
        except Exception: pass
        # 9) Default — passed all visible filters but got truncated/deduped
        return ("dedup_or_truncated", "")

    # Cap at first 2000 hidden rows by score (most "should have been seen") for HTML size
    _candidates = [r for r in _original_rows if r[0] not in _kept_fps]
    _candidates.sort(key=lambda r: -(int(r[11] or 0)))
    for r in _candidates[:2000]:
        reason, detail = _classify_hidden(r)
        _hidden_classified.append({
            "fp": r[0],
            "company": (r[1] or ""),
            "title": (r[2] or ""),
            "location": (r[3] or ""),
            "score": r[11] or 0,
            "reason": reason,
            "detail": detail,
        })

    hidden_jobs_json = json.dumps(_hidden_classified, separators=(",", ":"))
    print(f"[why-hidden:{user_slug}] classified {len(_hidden_classified)} hidden jobs (of {len(_original_rows) - len(rows)} total dropped)", flush=True)

    # Stats
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    senior_remote = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE senior=1 AND remote=1 AND last_seen >= datetime('now','-7 days')"
    ).fetchone()[0]
    ghost = conn.execute(
        f"SELECT COUNT(*) FROM jobs WHERE julianday(last_seen) - julianday(first_seen) > {GHOST_DAYS}"
    ).fetchone()[0]

    # F5: cross-company cluster — group by normalized title and stash a
    # list of *other* companies sharing the same title so the card can
    # render an "Also at X, Y, Z" badge.
    _xc_by_norm = {}
    for r in rows:
        key = _normalize_title(r[2] or "")
        if not key: continue
        cname = (r[1] or "").strip()
        if not cname: continue
        _xc_by_norm.setdefault(key, []).append(cname)
    # Dedup company names per key (preserve first-seen order)
    for k, lst in list(_xc_by_norm.items()):
        seen = set(); uniq = []
        for c in lst:
            cl = c.lower()
            if cl in seen: continue
            seen.add(cl); uniq.append(c)
        _xc_by_norm[k] = uniq

    # F5: pre-compute "why matched" per row.
    def _why_matched(r):
        if not SKILLS_PROFILE: return ""
        title = r[2] or ""; company = (r[1] or "").strip()
        title_tokens = set(re.findall(r"[a-z]+", title.lower()))
        reasons = []
        for tt in (SKILLS_PROFILE.get("targetTitles") or []):
            tt_tokens = set(re.findall(r"[a-z]+", (tt or "").lower())) - _ROLE_STOPWORDS
            if tt_tokens and all(_token_matches(t, title_tokens) for t in tt_tokens):
                reasons.append(f"matches your target title “{tt}”")
                break
        if not reasons:
            primary = (SKILLS_PROFILE.get("primaryRole") or "")
            if primary:
                reasons.append(f"matches your role “{primary}”")
        tcompanies = {c.get("name","").lower() for c in (SKILLS_PROFILE.get("targetCompanies") or [])}
        if company and company.lower() in tcompanies:
            reasons.append(f"{company} is on your target-companies list")
        job_inds = (r[15] or "").split(",") if r[15] else []
        ind_overlap = list(_industry_tokens(job_inds) & _industry_tokens(SKILLS_PROFILE.get("industries") or []))
        if ind_overlap:
            reasons.append("industry overlap: " + ", ".join(ind_overlap[:3]))
        return " • ".join(reasons) if reasons else "passed default gates"

    cards = []
    for r in rows:
        (fp, company, title, loc, url, posted_at, first_seen, last_seen,
         sightings, remote, senior, score, desc, salary, employment_type, _industries) = r
        emp = (employment_type or "unknown").lower()
        # "Listed" age — prefer the source's posted_at, fall back to first_seen
        listed_days = _days_old(posted_at) if posted_at else None
        if listed_days is None:
            listed_days = _days_old(first_seen) or 0
        ghost_flag = listed_days is not None and listed_days > GHOST_DAYS
        salary = (salary or "").strip()
        salary_max = _parse_salary_max(salary)
        badges = []
        if senior: badges.append('<span class="b senior">Senior</span>')
        if remote: badges.append('<span class="b remote">Remote</span>')
        if emp == "contract": badges.append('<span class="b contract">Contract</span>')
        if listed_days == 0: badges.append('<span class="b fresh">New today</span>')
        elif listed_days is not None and listed_days <= 7: badges.append('<span class="b week">This week</span>')
        _loc_count = LOCATION_COUNTS.get(fp, 1)
        if _loc_count > 1: badges.append(f'<span class="b multi-loc">{_loc_count} locations</span>')
        if ghost_flag: badges.append(f'<span class="b ghost">Ghost? {listed_days}d</span>')
        if sightings > 3: badges.append(f'<span class="b repost">Seen {sightings}×</span>')
        badge_html = " ".join(badges)
        salary_html = f'<div class="salary-row"><span class="salary">{_esc(salary)}</span></div>' if salary else ''

        _is_recr = 1 if (company or "").strip().lower() in _recruiter_names else 0
        _why = _why_matched(r)
        _norm_key = _normalize_title(title or "")
        _xc_others = [c for c in _xc_by_norm.get(_norm_key, []) if c.lower() != (company or "").lower()]
        _xc_count = len(_xc_others)
        _xc_label = ", ".join(_xc_others[:4]) + (f" +{_xc_count - 4} more" if _xc_count > 4 else "")
        _careers = _careers_root(url)
        if _careers:
            careers_fallback = f'<div class="careers-fallback" style="font-size:11.5px;color:#666;margin-top:6px;">If this listing is removed, browse <a href="{_careers}" target="_blank" rel="noopener" style="color:#5C5CD6;">all jobs at {_esc(company)}</a> on their ATS.</div>'
        else:
            careers_fallback = ''
        _comp_key = (company or "").strip().lower()
        _ri = (RECRUITERS_BY_COMPANY.get(_comp_key) or RECRUITERS_BY_COMPANY.get(_comp_key.replace(" ", "")))
        if _ri and _ri.get("linkedinSearch"):
            warm_intro_html = f'<a class="btn ghost-btn small warm-intro" href="{_ri["linkedinSearch"]}" target="_blank" rel="noopener" title="Find a warm intro on LinkedIn" style="background:#fef3e8;color:#b85c00;border-color:#f0c47a;">🤝 Warm intro</a>'
        else:
            warm_intro_html = ''
        # JUST-POSTED badge (2026-05-27): jobs ingested in last 24h get a
        # green pill. Differs from the older 'last 7d' bonus — this is the
        # 'you might be the first applicant' signal.
        _just_posted_badge = ''
        try:
            from datetime import datetime as _jpdt, timezone as _jptz
            if first_seen:
                _fs = _jpdt.fromisoformat(str(first_seen).replace('Z','+00:00'))
                if _fs.tzinfo is None: _fs = _fs.replace(tzinfo=_jptz.utc)
                _hrs = (_jpdt.now(_jptz.utc) - _fs).total_seconds() / 3600
                if _hrs < 24:
                    _just_posted_badge = ' · <span class="just-posted-badge" title="Posted in the last 24 hours — early applicants get more attention.">⚡ just posted</span>'
        except Exception:
            pass

        # REPOST detection (2026-05-27): if we first saw this fingerprint many
        # days BEFORE the JD's claimed posted_at, the JD was re-posted under a
        # new ID. Surface so user knows they may have applied before.
        _repost_days = None
        try:
            from datetime import datetime as _rdt, timezone as _rtz
            if first_seen and posted_at:
                _fs = _rdt.fromisoformat(str(first_seen).replace("Z", "+00:00"))
                _pa = _rdt.fromisoformat(str(posted_at).replace("Z", "+00:00"))
                if _fs.tzinfo is None: _fs = _fs.replace(tzinfo=_rtz.utc)
                if _pa.tzinfo is None: _pa = _pa.replace(tzinfo=_rtz.utc)
                # If posted_at is at least 30 days AFTER first_seen, it's a repost
                _gap = (_pa - _fs).days
                if _gap >= 30:
                    _repost_days = _gap
        except Exception:
            pass
        _repost_badge = f' · <span class="repost-badge" title="Re-posted {_repost_days} days after we first saw this job — you may have already seen / applied to it.">↻ re-posted {_repost_days}d after first sighting</span>' if _repost_days else ''

        cards.append(f"""
        <div class="card" data-fp="{fp}" data-score="{score}" data-senior="{senior}" data-remote="{remote}" data-employment="{emp}" data-listed-days="{listed_days if listed_days is not None else 9999}" data-salary-max="{salary_max}" data-last-seen="{last_seen or ''}" data-first-seen="{first_seen or ''}" data-recruiter="{_is_recr}" data-why="{_esc(_why)}" data-cluster-count="{_xc_count}" data-cluster-companies="{_esc(_xc_label)}" data-title-norm="{_norm_key}" data-repost-days="{_repost_days or ''}">
          <div class="row1">
            <div class="title"><a href="{url}" target="_blank">{_esc(title)}</a></div>
            <div class="score">{score}</div>
          </div>
          <div class="row2">
            <span class="company">{_esc(company)}</span> ·
            <span class="loc">{_esc(loc or 'Location N/A')}</span> ·
            <span class="age">{listed_days}d old</span>{_just_posted_badge}{_repost_badge}
          </div>
          {salary_html}
          <div class="badges" data-badges>{badge_html}</div>
          <div class="desc">{_esc(_strip_html(desc)[:300])}…</div>
          {f'<div class="why-inline" style="font-size:11.5px;color:#5C5CD6;margin-top:6px;font-style:italic;">→ Match: {_esc(_why)}</div>' if _why else ''}
          <div class="actions">
            <a class="btn primary" href="{url}" target="_blank" rel="noopener" onclick="applyAndOpen('{fp}', this, '{url}'); return true;">Apply now &rarr;</a>
            <button class="btn ghost-btn" onclick="prepApplication('{fp}', this)">Prep materials</button>
            <button class="btn track" onclick="cycleStatus('{fp}', this)" data-status-for="{fp}">Mark Applied</button>
            <button class="btn ghost-btn small followup" onclick="openFollowupFromCard('{fp}')" data-fp-followup="{fp}" style="display:none;" title="Draft a follow-up email">📨 Follow up</button>
            <button class="btn ghost-btn small interview" onclick="openInterviewPrepFromCard('{fp}')" data-fp-interview="{fp}" style="display:none;" title="Interview prep">🎯 Interview prep</button>
            {warm_intro_html}
            <button class="btn ghost-btn small" onclick="showWhyMatched('{fp}', this)" title="Why was this shown?">Why?</button>
            <button class="btn ghost-btn small dismiss" onclick="dismissJob('{fp}', this)" title="Not for me — hide and learn">×</button>
          </div>
          {careers_fallback}
        </div>""")

    # Derive a subtitle from the user's AI skills profile (industry-aware).
    if SKILLS_PROFILE:
        primary = (SKILLS_PROFILE.get("primaryRole") or "").strip()
        remote_pref = "Remote" if SKILLS_PROFILE.get("remotePreferred") else "On-site or remote"
        subtitle = (primary + " · " + remote_pref) if primary else remote_pref
    else:
        subtitle = "Awaiting resume upload — click Resume to get started"

    # Friendlier empty-state message depending on why we have 0 cards
    if cards:
        cards_html = "\n".join(cards)
    elif SKILLS_PROFILE and user_industries:
        cards_html = (
            f"<div style='padding:32px;max-width:640px;margin:30px auto;background:#fff;"
            f"border:1px solid #e2e5ea;border-radius:8px;line-height:1.55;'>"
            f"<h3 style='margin:0 0 10px 0;color:#5C5CD6;'>No matching jobs yet for {_esc(user_name)}</h3>"
            f"<p style='color:#555;font-size:14px;'>Your profile industries: "
            f"<strong>{_esc(', '.join(user_industries[:5]))}</strong>. "
            f"We haven't indexed companies in these industries yet. "
            f"Ask the admin to add relevant companies, or click <em>Resume</em> to update your profile.</p></div>"
        )
    elif not SKILLS_PROFILE:
        cards_html = (
            f"<div style='padding:32px;max-width:640px;margin:30px auto;background:#fff;"
            f"border:1px solid #e2e5ea;border-radius:8px;line-height:1.55;'>"
            f"<h3 style='margin:0 0 10px 0;color:#5C5CD6;'>Welcome, {_esc(user_name)}!</h3>"
            f"<p style='color:#555;font-size:14px;'>Click the <strong>Resume</strong> button (top-right) and "
            f"upload your resume as PDF or Word. The AI will read it and start matching jobs to your background. "
            f"Your tailored dashboard will appear here after the next refresh.</p></div>"
        )
    else:
        cards_html = "<p style='padding:24px;color:#666;'>No matches in the last 30 days. Click Refresh data to look again.</p>"

    # Auto-learn surface banner (2026-05-27): if the worker recently added
    # something to the user's blocklist via engagement learning, tell them.
    auto_learn_html = ''
    try:
        al = SKILLS_PROFILE and SKILLS_PROFILE.get('lastAutoLearn')
        if al and al.get('kind') == 'excludeCompany':
            _val = _esc(str(al.get('value') or ''))
            _ct = int(al.get('dismissCount') or 0)
            auto_learn_html = (
                '<div style="background:#EEEEF8;border:1px solid #BFBFEA;border-radius:8px;'
                'padding:10px 14px;margin:0 auto 10px;max-width:1400px;font-size:12.5px;'
                'color:#1F1B45;font-family:Inter,system-ui,sans-serif;">'
                f'<strong>↻ We auto-added <em>{_val}</em> to your blocklist</strong> '
                f'after {_ct} dismisses in 30 days. '
                '<a href="/account.html" style="color:#1817B5;font-weight:600;">Manage</a>'
                '</div>'
            )
    except Exception:
        pass

    # Relevance floor warning: if we couldn't fill 50 strong matches today,
    # surface a banner suggesting the user broaden the bullseye.
    RELEVANCE_FLOOR = 60
    strong_count = sum(1 for r in rows if (int(r[11] or 0) >= RELEVANCE_FLOOR))
    low_match_warning_html = ''
    if SKILLS_PROFILE and strong_count < 8 and len(rows) > 0:
        low_match_warning_html = (
            '<div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;padding:12px 16px;margin:0 auto 14px;max-width:1400px;font-size:13px;color:#78350f;font-family:Inter,system-ui,sans-serif;">'
            f'<strong>⚠️ Only {strong_count} strong match{"" if strong_count == 1 else "es"} today (score \u2265 {RELEVANCE_FLOOR}).</strong> '
            'Showing all ' + str(len(rows)) + ' jobs we have so the feed isn\'t empty, but consider broadening your bullseye '
            '(more target titles or industries) via the wizard to get more strong daily matches.'
            '</div>'
        )

    # --- Sprint mode (10-day push) ---------------------------------
    # If skills_profile.sprintStart is set, render a progress strip and
    # flag the dashboard so it sorts by sprint priority on first load.
    # Counter values are hydrated client-side after /tracker loads.
    sprint_strip_html = ''
    sprint_active_attr = 'false'
    sprint_start_cta_html = ''
    try:
        sp = (SKILLS_PROFILE or {}).get('sprintStart')
        if not sp:
            sprint_start_cta_html = (
                '<div id="sprint-start-cta" '
                'style="background:linear-gradient(135deg,#0B0828 0%,#1E146E 40%,#1817B5 100%);'
                'color:#fff;padding:18px 22px;border-radius:12px;margin:0 auto 14px;max-width:1400px;'
                'font-family:Inter,system-ui,sans-serif;box-shadow:0 4px 14px rgba(11,8,40,0.18);'
                'display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;">'
                '<div>'
                '<div style="font-size:15px;font-weight:700;letter-spacing:0.3px;">🎯 Ready to sprint?</div>'
                '<div style="font-size:13px;opacity:0.92;margin-top:4px;">10 days, 3 applications a day, warm-intro picks first. We\u2019ll email you a daily nudge with the 3 best matches.</div>'
                '</div>'
                '<button onclick="startSprintNow(this)" '
                'style="background:#fff;color:#1817B5;border:none;padding:12px 20px;border-radius:8px;font-weight:700;font-size:14px;cursor:pointer;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,0.18);">'
                'Start my 10-day sprint →</button>'
                '</div>'
            )
        if sp:
            from datetime import datetime as _spdt, timezone as _sptz
            start_dt = _spdt.fromisoformat(str(sp).replace('Z','+00:00'))
            now_dt = _spdt.now(_sptz.utc)
            sprint_days = int((SKILLS_PROFILE or {}).get('sprintDays', 10))
            daily_quota = int((SKILLS_PROFILE or {}).get('sprintDailyQuota', 3))
            day_n = max(1, min(sprint_days, int((now_dt - start_dt).days) + 1))
            quota_total = sprint_days * daily_quota
            sprint_active_attr = 'true'
            # Persist sprint params on the strip so JS can read them
            sprint_strip_html = (
                '<div id="sprint-strip" '
                f'data-sprint-start="{start_dt.isoformat()}" '
                f'data-sprint-days="{sprint_days}" '
                f'data-sprint-daily-quota="{daily_quota}" '
                f'data-sprint-quota-total="{quota_total}" '
                'style="background:linear-gradient(135deg,#0B0828 0%,#1E146E 40%,#1817B5 100%);'
                'color:#fff;padding:14px 20px;border-radius:12px;margin:0 auto 14px;max-width:1400px;'
                'font-family:Inter,system-ui,sans-serif;box-shadow:0 4px 14px rgba(11,8,40,0.18);">'
                '<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;">'
                '<div style="font-size:14px;font-weight:700;letter-spacing:0.5px;">'
                f'🎯 10-DAY SPRINT &mdash; Day <span id="sprint-day-n">{day_n}</span> of {sprint_days}'
                '</div>'
                f'<div style="font-size:13px;opacity:0.95;"><span id="sprint-applied-total">0</span> of {quota_total} applications</div>'
                '</div>'
                '<div style="margin-top:10px;height:8px;background:rgba(255,255,255,0.18);border-radius:6px;overflow:hidden;">'
                '<div id="sprint-progress-fill" style="height:100%;width:0%;background:linear-gradient(90deg,#7C7CF0,#A4A4FF);border-radius:6px;transition:width 0.4s;"></div>'
                '</div>'
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;font-size:12px;opacity:0.9;">'
                f'<span>Today: <span id="sprint-today-count">0</span> of {daily_quota}</span>'
                '<span><span id="sprint-pct">0</span>% to goal · <a href="/sprint.html?user=' + user_slug + '" style="color:#fff;text-decoration:underline;opacity:0.9;">live view →</a></span>'
                '</div>'
                '</div>'
            )
    except Exception as _sprint_err:
        sprint_strip_html = ''
        sprint_active_attr = 'false'

    html = HTML_TEMPLATE.format(
        total=total,
        senior_remote=senior_remote,
        ghost=ghost,
        generated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        shown=len(rows),
        cards=cards_html,
        user_slug=user_slug,
        user_name=_esc(user_name),
        subtitle=_esc(subtitle),
        has_profile_js=("true" if SKILLS_PROFILE else "false"),
        hidden_jobs_json=hidden_jobs_json,
        low_match_warning=(auto_learn_html + low_match_warning_html),
        sprint_strip=sprint_strip_html,
        sprint_active=sprint_active_attr,
        sprint_start_cta=sprint_start_cta_html,
    )
    # Some embedded emoji in HTML_TEMPLATE are stored as UTF-16 surrogate
    # pair literals (\ud83c\udfaf etc). Merge them into proper codepoints
    # so the output is valid UTF-8 (the browser refuses to parse JS that
    # contains lone surrogate bytes, which would silently break every
    # onclick on the page including the Preferences button).
    import re as _re
    def _merge_surrogates(s):
        return _re.sub(
            r"[\ud800-\udbff][\udc00-\udfff]",
            lambda m: chr(0x10000 + (ord(m.group(0)[0]) - 0xd800) * 0x400 + (ord(m.group(0)[1]) - 0xdc00)),
            s,
        )
    html = _merge_surrogates(html)
    # Wizard v3: append the self-contained block just before the LAST </body>.
    # CRITICAL: must use rsplit, not replace(..., 1). The FIRST </body> in the
    # rendered HTML is inside a JS template literal in _renderResumeForPrint
    # (which builds a complete <html>...</body></html> as a string for the
    # printable resume). Injecting there put a literal <script>...</script>
    # inside a JS template literal — the HTML parser then incorrectly closed
    # the page's main <script> at that </script>, leaving the template literal
    # unclosed → "Unexpected end of input" → ALL event handlers dead.
    # rsplit on the LAST </body> targets the actual page body close.
    if "</body>" in html:
        parts = html.rsplit("</body>", 1)
        html = parts[0] + WIZARD_V3_BLOCK + "\n</body>" + parts[1]
    else:
        html += WIZARD_V3_BLOCK
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDashboard written: {output_path}")


def generate_all_dashboards(conn):
    """Generate one dashboard per user in users.json.

    Note: index.html is the public-facing landing page (getmemyjob marketing
    page), NOT a dashboard. Users access their dashboards directly at
    /<slug>.html (e.g. /geetu.html for Geetanjali). This refresh job does not
    touch index.html or landing.html.
    """
    # Ensure COMPANY_INDUSTRIES is built (may not have been if called standalone)
    if not COMPANY_INDUSTRIES:
        try:
            with open(COMPANIES_PATH) as f:
                _build_company_industries(json.load(f))
        except Exception as e:
            print(f"[industries] could not load companies.json: {e}", flush=True)
    users = load_users()
    print(f"\n[multi-user] generating dashboards for {len(users)} users")
    for user in users:
        slug = user["slug"]
        name = user.get("name", slug)
        out = os.path.join(ROOT, f"{slug}.html")
        generate_dashboard(conn, user_slug=slug, user_name=name, output_path=out)


def _days_old(iso):
    if not iso: return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return None


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


from dashboard.template import HTML_TEMPLATE  # extracted Phase 3


if __name__ == "__main__":
    run()
