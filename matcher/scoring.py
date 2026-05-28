"""Scoring cluster — score_job + 13 helpers + supporting constants.

Extracted from fetch_jobs.py 2026-05-28 (Phase 2 of split refactor).

Design:
  - SKILLS_PROFILE lives here as a module global. fetch_jobs.py sets it
    via `matcher.scoring.SKILLS_PROFILE = profile` before generating each
    user's dashboard. This preserves the existing score_job(job) signature
    while keeping the scoring cluster self-contained.
  - canonical_company comes from matcher.canonical
  - HEALTHTECH_SET comes from matcher.catalogs (dynamically read each call
    so catalog reloads are seen)
  - WORKER_BASE_URL + COMPANY_STAGE_CACHE are module-level here; the worker
    URL is hard-coded (matches the prior inline default).
"""
import re
import math
from math import exp
from datetime import datetime, timezone

from matcher.canonical import canonical_company

# Worker URL for /company-stage cache lookups
WORKER_BASE_URL = "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev"

# Per-user state — fetch_jobs.py sets this before generating each dashboard.
SKILLS_PROFILE = None

# In-process company-stage cache (None means "checked, not cached server-side")
COMPANY_STAGE_CACHE = {}


def _healthtech_set():
    """Lazy import to avoid circular import at module load time."""
    try:
        from matcher.catalogs import HEALTHTECH_SET
        return HEALTHTECH_SET
    except ImportError:
        return set()


# Lazy bind to constants that still live in fetch_jobs.py (Phase 2 incomplete —
# fully extracting these into scoring.py is Phase 3 work). We resolve them on
# first call rather than at import time to avoid circular imports.
_LAZY_BOUND = False

def _bind_lazy_constants():
    """Pull constants from fetch_jobs that we haven't extracted yet."""
    global _LAZY_BOUND, IRRELEVANT_TITLE_TERMS, RECRUITER_BLURBS, RECRUITING_FIRMS_SET
    global SINGLE_WORD_FILTERS, STAGE_ORDER, TITLE_STAGE_EARLY, TITLE_STAGE_EXEC
    global TITLE_STAGE_INTERN, TITLE_STAGE_MID, TITLE_STAGE_NEWGRAD, TITLE_STAGE_SENIOR_IC
    global _CONSULTING_JD_PHRASES, _CONSULTING_NAME_PATTERNS, _JD_SECTION_HEADERS
    global _STAFFING_NAME_PATTERNS
    if _LAZY_BOUND:
        return
    import sys
    fj = sys.modules.get('fetch_jobs')
    if not fj:
        # fetch_jobs not loaded yet — try direct import (won't be circular here)
        import fetch_jobs as fj  # noqa
    IRRELEVANT_TITLE_TERMS = getattr(fj, 'IRRELEVANT_TITLE_TERMS', [])
    RECRUITER_BLURBS = getattr(fj, 'RECRUITER_BLURBS', [])
    RECRUITING_FIRMS_SET = getattr(fj, 'RECRUITING_FIRMS_SET', set())
    SINGLE_WORD_FILTERS = getattr(fj, 'SINGLE_WORD_FILTERS', set())
    STAGE_ORDER = getattr(fj, 'STAGE_ORDER', [])
    TITLE_STAGE_EARLY = getattr(fj, 'TITLE_STAGE_EARLY', set())
    TITLE_STAGE_EXEC = getattr(fj, 'TITLE_STAGE_EXEC', set())
    TITLE_STAGE_INTERN = getattr(fj, 'TITLE_STAGE_INTERN', set())
    TITLE_STAGE_MID = getattr(fj, 'TITLE_STAGE_MID', set())
    TITLE_STAGE_NEWGRAD = getattr(fj, 'TITLE_STAGE_NEWGRAD', set())
    TITLE_STAGE_SENIOR_IC = getattr(fj, 'TITLE_STAGE_SENIOR_IC', set())
    _CONSULTING_JD_PHRASES = getattr(fj, '_CONSULTING_JD_PHRASES', [])
    _CONSULTING_NAME_PATTERNS = getattr(fj, '_CONSULTING_NAME_PATTERNS', [])
    _JD_SECTION_HEADERS = getattr(fj, '_JD_SECTION_HEADERS', {})
    _STAFFING_NAME_PATTERNS = getattr(fj, '_STAFFING_NAME_PATTERNS', [])
    _LAZY_BOUND = True

# Pre-declare placeholders so module-level references don't NameError before binding
IRRELEVANT_TITLE_TERMS = []
RECRUITER_BLURBS = []
RECRUITING_FIRMS_SET = set()
SINGLE_WORD_FILTERS = set()
STAGE_ORDER = []
TITLE_STAGE_EARLY = set()
TITLE_STAGE_EXEC = set()
TITLE_STAGE_INTERN = set()
TITLE_STAGE_MID = set()
TITLE_STAGE_NEWGRAD = set()
TITLE_STAGE_SENIOR_IC = set()
_CONSULTING_JD_PHRASES = []
_CONSULTING_NAME_PATTERNS = []
_JD_SECTION_HEADERS = {}
_STAFFING_NAME_PATTERNS = []

SENIOR_TITLE_TERMS = [
    "vp", "vice president", "head of", "director", "sr director",
    "senior director", "principal", "chief", "lead", "executive"
]


RELEVANCE_TERMS = [
    "healthcare", "health", "clinical", "patient", "ehr", "emr",
    "digital transformation", "digital health", "product",
    "portfolio", "program", "platform", "saas", "ai", "agile",
    "scrum", "transformation", "operations", "delivery"
]


SCAM_TERMS = [
    "earn from home", "make money", "no experience needed",
    "commission only", "100% remote opportunity!!!", "$$$",
    "work from anywhere worldwide"
]


AGENCY_TERMS = [
    "our client", "client of ours", "leading client", "fortune 500 client",
    "contract to hire", "c2h", "w2 only", "1099 contract"
]


_ROLE_STOPWORDS = {
    "senior", "sr", "junior", "jr", "lead", "leader", "manager", "managers",
    "director", "directors", "head", "chief", "principal", "staff",
    "executive", "vp", "vice", "president", "of", "the", "and", "or", "for",
    "to", "at", "in", "on", "i", "ii", "iii", "iv", "level", "team", "group",
    "global", "us", "north", "america", "leads", "an", "a",
}


_INDUSTRY_STOPWORDS = {"and", "the", "for", "with", "of", "to", "in", "on",
                       "management", "services", "company", "industry",
                       # Weak cross-industry tokens — too generic to indicate
                       # real overlap. Without these, "consumer-banking" matched
                       # "direct-to-consumer", leaking Capital One PM jobs onto a
                       # healthcare-IT dashboard.
                       "consumer", "data", "digital", "technology", "tech",
                       "enterprise", "saas", "cloud", "global", "platform",
                       "solutions", "systems", "software", "ai", "ml",
                       "innovation", "products", "product", "strategy",
                       "operations", "service", "international", "north",
                       "america", "americas", "online", "mobile", "web",
                       "info", "information"}


def detect_title_stage(title):
    """Return the strongest seniority signal in the title, or None if ambiguous.
    Uses word-boundary matching so short tokens like 'cto' don't match 'director'.
    Checked from most-specific to least so 'Senior Director' is read as senior."""
    if not title:
        return None
    t = " " + title.lower() + " "
    def _hit(patterns):
        for p in patterns:
            if not p:
                continue
            p = p.strip()  # patterns like "senior " were authored with trailing space; strip for boundary regex
            if not p:
                continue
            try:
                if re.search(r"(?<![a-z])" + re.escape(p) + r"(?![a-z])", t):
                    return True
            except re.error:
                if p in t:
                    return True
        return False
    if _hit(TITLE_STAGE_INTERN):
        return "internship"
    if _hit(TITLE_STAGE_NEWGRAD):
        return "new-grad"
    if _hit(TITLE_STAGE_EXEC):
        return "executive"
    if _hit(TITLE_STAGE_SENIOR_IC):
        return "senior"
    if _hit(TITLE_STAGE_MID):
        return "mid-career"
    if _hit(TITLE_STAGE_EARLY):
        return "early-career"
    return None  # untagged — neutral



def days_since_posted(posted_at_iso):
    """Return days since the job was posted, or None if no date. Tolerant of
    multiple ISO formats and odd values. Caps at 999 to avoid silly numbers."""
    if not posted_at_iso:
        return None
    try:
        from datetime import datetime, timezone
        s = str(posted_at_iso)
        # Try a few common shapes
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s.split("+")[0].replace("Z","").strip(), fmt.replace("Z",""))
                dt = dt.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - dt
                d = max(0, int(delta.total_seconds() // 86400))
                return min(d, 999)
            except ValueError:
                pass
        # Fall through: not parseable
        return None
    except Exception:
        return None




def freshness_multiplier(posted_at_iso, company_name=None):
    """Smooth exponential decay with stage-aware lenience for small companies.
    Default decay (D+/public/unknown): exp(-d/21) — ~50% at 14d, ~5% at 60d
    Series B/C (mid):                  exp(-d/28) — ~60% at 14d, ~12% at 60d
    Seed/A (small):                    exp(-d/42) — ~72% at 14d, ~24% at 60d
    Smaller companies post less often and refresh less, so we don't punish
    stale listings as hard. Pull stage from worker /company-stage cache."""
    import math
    d = days_since_posted(posted_at_iso)
    if d is None:
        return 1.0
    # Choose decay constant based on funding stage
    decay = 21.0  # default
    if company_name:
        try:
            rec = _get_company_stage(company_name)
            stage = (rec and rec.get('stage') or '').lower()
            if stage in ('seed', 'series-a', 'bootstrapped'):
                decay = 42.0  # small / very small
            elif stage in ('series-b', 'series-c'):
                decay = 28.0  # mid
        except Exception:
            pass
    return math.exp(-d / decay)


_NEXT_STAGE = {
    "early-career": "mid-career",
    "mid-career":   "senior",
    "senior":       "executive",
    "executive":    "executive",  # already at top; same-stage match still valid
}



def trajectory_match(user_stage, job_stage):
    """Return one of: 'next' (one rung up — most desirable),
    'same' (lateral — fine), 'down' (regression), or None.
    Both args are stage strings from detect_title_stage / careerStage."""
    if not user_stage or not job_stage:
        return None
    u = STAGE_ORDER.get(user_stage)
    j = STAGE_ORDER.get(job_stage)
    if u is None or j is None:
        return None
    if j == u + 1:
        return "next"
    if j == u:
        return "same"
    if j < u:
        return "down"
    return None  # too far ahead — uncertain




def is_recruiter_listing(job):
    _bind_lazy_constants()
    name = (job.get("company_name") or "").strip().lower()
    if name in RECRUITING_FIRMS_SET:
        return True
    desc = (job.get("description") or "").lower()
    return any(b in desc for b in RECRUITER_BLURBS)



def _is_irrelevant_title(title):
    _bind_lazy_constants()
    t = (title or "").lower()
    if any(term in t for term in IRRELEVANT_TITLE_TERMS):
        return True
    # Word-boundary check for single-word filters
    for w in SINGLE_WORD_FILTERS:
        if re.search(r"\b" + re.escape(w) + r"\b", t):
            return True
    return False


# --- Positive title whitelist (Phase 4) -------------------------------
# Universal themes for senior healthcare-IT / digital-transformation / product
# leaders. A title MUST contain at least one of these (or a keyword from the
# skills profile) to be shown. This converts the dashboard from a blacklist
# model ("hide bad") to a whitelist model ("only show relevant").
POSITIVE_TITLE_THEMES = [
    # Product / portfolio
    "product", "portfolio", "platform",
    # Transformation / innovation / digital
    "transformation", "innovation", "digital", "modernization", "automation",
    # AI / ML / data product
    "ai", "artificial intelligence", "machine learning", "ml", "data product",
    # Implementation / delivery / enterprise programs
    "implementation", "deployment", "enterprise", "delivery",
    # Strategy + senior titles (typically real C-suite / VP roles)
    "strategy", "strategist", "officer", "chief", "general manager", "gm",
    # Healthcare-IT specifics
    "ehr", "emr", "saas", "health it", "health tech", "healthtech",
    "interoperability", "informatics",
    # Engineering leadership (very senior, not IC)
    "head of engineering", "vp engineering", "vp of engineering",
    "chief technology", "cto", "cio", "ciso", "cdo", "cpo",
    # Operations leadership (when not blacklisted as "strategic operations" etc.)
    "vp operations", "vp of operations", "head of operations",
    # Programs / portfolio (her core)
    "program management", "head of program", "vp programs", "vp of programs",
    "head of portfolio", "vp portfolio", "head of programs",
    # Finance / banking / fintech (added Slice B v2 so bank/fintech employers
    # actually surface relevant senior roles instead of being silently dropped
    # by a healthcare-only theme list).
    "finance", "financial", "banking", "investment", "investments", "wealth",
    "treasury", "trading", "trader", "lending", "credit", "underwriting",
    "compliance", "risk", "audit", "regulatory", "fintech", "payments",
    "asset management", "capital markets", "private banking",
    "investment banking", "wealth management", "portfolio management",
    "managing director", "principal", "head of risk",
]


_POSITIVE_THEME_RE = None



def classify_company_type(company_name, description):
    name = (company_name or "").lower()
    desc = (description or "")[:3000].lower()
    # Staffing signals are strongest — check first
    for p in _STAFFING_NAME_PATTERNS:
        if p in name:
            return "staffing"
    # Explicit consulting in name
    for p in _CONSULTING_NAME_PATTERNS:
        if p in name:
            return "consulting"
    # JD-language fallback: 3+ consulting phrases in JD → consulting
    hits = sum(1 for ph in _CONSULTING_JD_PHRASES if ph in desc)
    if hits >= 3:
        return "consulting"
    # If we have positive in-house signals
    if any(s in desc for s in ("our product", "our platform", "our team", "our mission", "we build", "we ship")):
        return "in-house"
    return "unknown"




def is_remote(job):
    blob = f"{job['location']} {job['title']} {job['description'][:500]}".lower()
    if "remote" in blob or "anywhere" in blob or "work from home" in blob:
        return True
    if "hybrid" in blob and "remote" in blob:
        return True
    return False




def is_senior(job):
    t = (job["title"] or "").lower()
    return any(term in t for term in SENIOR_TITLE_TERMS)


# Hiring-velocity cache: company_name (lower) -> int. Computed once per render
# from a single DB query in generate_dashboard; consulted by score_job.
HIRING_VELOCITY = {}




def hiring_velocity_boost(company_name):
    """Return +5 if company is 'actively scaling' (3+ senior roles posted in
    past 30 days), else 0."""
    if not company_name:
        return 0
    n = HIRING_VELOCITY.get(company_name.strip().lower(), 0)
    return 5 if n >= 3 else 0


# Company-stage cache (worker /company-stage endpoint) — populated lazily
# during render via _get_company_stage(). Maps company_name_lower -> dict or
# None for known-not-classified. Avoids a per-job network round-trip.
COMPANY_STAGE_CACHE = {}



def _get_company_stage(company_name):
    """Look up the company-stage record from worker KV. None if not cached."""
    if not company_name:
        return None
    key = company_name.strip().lower()
    if key in COMPANY_STAGE_CACHE:
        return COMPANY_STAGE_CACHE[key]
    try:
        import urllib.parse, urllib.request, json as _json
        url = f'{WORKER_BASE_URL}/company-stage?company={urllib.parse.quote(key)}'
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = _json.loads(resp.read().decode('utf-8', errors='replace'))
            if data.get('cached'):
                COMPANY_STAGE_CACHE[key] = data
                return data
    except Exception:
        pass
    COMPANY_STAGE_CACHE[key] = None
    return None


# Funding boost — split into two signals:
#   1. Active VC-backed stage tier (Series A-D / late-stage / series-e+):
#      these are companies that HAVE capital and ARE scaling. +3.
#   2. Recently funded (Claude knows the round closed in past ~24 months):
#      stronger 'hot right now' signal. +5 in addition to the stage boost.
# Combined max +8 for the hottest companies (series-c funded in 2024 etc).
_HOT_STAGES = {"series-a", "series-b", "series-c", "series-d", "series-e-plus", "late-stage-private"}



def recently_funded_boost(company_name):
    """Stage-tier + recency boost from worker /company-stage cache."""
    rec = _get_company_stage(company_name)
    if not rec:
        return 0
    boost = 0
    stage = (rec.get('stage') or '').lower()
    yr = rec.get('lastFundedApproxYear')
    # Tier boost: VC-backed stage = +3
    if stage in _HOT_STAGES:
        boost += 3
    # Recency boost: funded in the last ~24 months (per Claude's knowledge horizon)
    try:
        from datetime import datetime as _fdt
        now_y = _fdt.utcnow().year
        if yr and isinstance(yr, int) and (now_y - yr) <= 2:
            boost += 5
    except Exception:
        pass
    return boost


def parse_jd_sections(description):
    """Split a JD into responsibilities / requirements / nice_to_have sections.
    Returns dict with those three keys mapped to substrings (lowercased).
    A 'rest' key holds everything that didn't classify (intro paragraphs etc.).
    Heuristic: scan line-by-line for header phrases; assign subsequent lines to
    the active section until the next header or EOF.
    Conservative: if no headers found, returns {responsibilities: '', requirements: '',
    nice_to_have: '', rest: full_text}."""
    if not description:
        return {"responsibilities": "", "requirements": "", "nice_to_have": "", "rest": ""}
    lines = description.lower().split("\n")
    sections = {"responsibilities": [], "requirements": [], "nice_to_have": [], "rest": []}
    active = "rest"
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Header check: if a line is short-ish and starts/contains a header phrase
        if len(stripped) < 80:
            matched = None
            for key, phrases in _JD_SECTION_HEADERS.items():
                for ph in phrases:
                    if ph in stripped:
                        matched = key
                        break
                if matched:
                    break
            if matched:
                active = matched
                continue  # don't include the header itself in content
        sections[active].append(stripped)
    return {k: " ".join(v) for k, v in sections.items()}




def score_job(job):
    _bind_lazy_constants()
    """0-100 score. Higher = more relevant + more likely 'real'.
    Uses the AI-extracted skills profile when available; falls back to hardcoded keywords.
    Title / Industry / Skills weights come from profile.matchWeights (set via the wizard);
    defaults to titles=50, industries=25, skills=25 (sum to 100)."""
    s = 50
    blob = f"{job['title']} {job['description']}".lower()
    title = (job["title"] or "").lower()

    # Profile mismatch — bring to very low score so it won't appear
    if _is_irrelevant_title(job["title"]):
        return 0

    # E4: drop recruiter / staffing-agency listings — they are usually
    # generic "send your resume to our client" posts, not real openings.
    if is_recruiter_listing(job):
        return 0

    profile = SKILLS_PROFILE
    if profile:
        # E5 (2026-05-27, v2): hard-block ONLY user's explicit excludeCompanies.
        # The old default consulting list (Capco, Accenture, etc.) is now
        # surfaced as suggestions in the wizard rather than hard-coded — users
        # control consulting visibility via companySizeMix.consulting %.
        user_excl = set()
        for c in (profile.get("excludeCompanies") or []):
            if isinstance(c, str) and c.strip():
                user_excl.add(c.strip().lower())
        co = (job.get("company_name") or job.get("company_slug") or "").strip().lower()
        if co and co in user_excl:
            return 0
        for blocked in user_excl:
            if blocked and len(blocked) >= 4 and co.startswith(blocked + "-"):
                return 0


        # E1 (relaxed): stage filter removed — we no longer drop jobs by
        # seniority gap. Stage influence is only via the +6 score bonus at
        # the end of score_job for an exact-stage match.
        # AI-driven negative keywords — disqualify on title match.
        # Word-boundary + senior-context aware (2026-05-27):
        # - Keyword must appear as a STANDALONE TOKEN, not substring. Stops
        #   "assistant" from killing "Assistant Vice President", "staff" from
        #   killing "Chief of Staff", "associate" from killing "Associate Director", etc.
        # - If the title contains any seniority signal (VP / Director / Head of /
        #   Chief / Principal / Managing / etc.), DON'T block — those are real
        #   senior roles regardless of any junior-sounding word that follows.
        neg = profile.get("negativeKeywords", [])
        if neg:
            _title_tokens = set(re.findall(r"\b[a-z]+\b", title))
            _SENIOR_GUARD = {"vp","svp","evp","chief","cio","cto","cdo","coo","cfo","cro","cpo","ceo",
                             "principal","director","head","managing","executive","president","partner","lead","leader"}
            _title_has_senior = bool(_SENIOR_GUARD & _title_tokens)
            for n in neg:
                if not n: continue
                _n_tokens = set(re.findall(r"\b[a-z]+\b", n.lower()))
                if not _n_tokens or not _n_tokens.issubset(_title_tokens):
                    continue  # keyword not a real token match
                if _title_has_senior:
                    continue  # don't block senior-titled roles even if they contain a junior keyword
                return 0

        # --- User-configurable weights (sum to 100) ---
        weights = profile.get("matchWeights") or {}
        w_t = max(0, int(weights.get("titles", 50)))
        w_i = max(0, int(weights.get("industries", 25)))
        w_s = max(0, int(weights.get("skills", 25)))
        _wsum = w_t + w_i + w_s
        if _wsum <= 0:
            w_t, w_i, w_s, _wsum = 50, 25, 25, 100
        # Normalize to exact 100
        w_t = w_t * 100.0 / _wsum
        w_i = w_i * 100.0 / _wsum
        w_s = w_s * 100.0 / _wsum
        # Each component contributes up to (weight * 0.5) bonus points, so all
        # three combined max out at +50 on top of the 50 base = 100 from signals.

        # TITLE component (re-tuned 2026-05-26): require multi-token match
        # for full credit so generic single words ("director", "lead") don't
        # grant 37 free points to every Director-titled role. Specifically:
        # - targetTitle with ≥2 meaningful tokens (after stopwords): all must
        #   appear in the job title as whole tokens → strength 1.0
        # - 2-token partial match (one missing) → strength 0.5
        # - seniorityTitles-only match → 0.10 (fallback safety net)
        target_titles = profile.get("targetTitles", []) or []
        title_tokens = set(re.findall(r"[a-z]+", title))
        title_strength = 0.0
        partial = 0.0
        _STOP = {"of","the","a","an","and","or","for","to","at","in","on","with","by","as","is"}
        for t in target_titles:
            if not t: continue
            tt_tokens = [x for x in re.findall(r"[a-z]+", t.lower()) if x not in _STOP and len(x) > 1]
            if len(tt_tokens) < 2:
                continue  # ignore generic single-word targets like "director"
            matched = sum(1 for tk in tt_tokens if tk in title_tokens)
            if matched == len(tt_tokens):
                title_strength = 1.0
                break
            elif matched >= len(tt_tokens) - 1 and len(tt_tokens) >= 3:
                partial = max(partial, 0.5)
        if title_strength == 0.0 and partial > 0:
            title_strength = partial
        if title_strength == 0.0:
            sen_titles = profile.get("seniorityTitles", []) or SENIOR_TITLE_TERMS
            if any(t in title for t in sen_titles if t and len(t) > 1):
                title_strength = 0.10
        # RELEVANCE-FIRST (2026-05-27, v2): industry + skills are the dominant
        # signals. Titles vary wildly between companies for the same role
        # ("Head of GRC" vs "Director, Risk Strategy" vs "VP Compliance") so
        # title-matching is brittle. Industry + skill keywords are robust —
        # they capture the substantive fit regardless of titling convention.
        # Read signal-stability multipliers from profile.
        # Stability = how reliable each signal is as evidence.
        # Defaults: title 0.4 (brittle — wording varies), industry 1.0 (robust), skills 1.0 (robust).
        # User can tune via the wizard 'signal-stability' step.
        _stab = profile.get("signalStability") or {}
        title_stab = max(0.0, min(1.0, (_stab.get("title", 40) or 0) / 100.0))
        ind_stab = max(0.0, min(1.0, (_stab.get("industry", 100) or 0) / 100.0))
        skl_stab = max(0.0, min(1.0, (_stab.get("skills", 100) or 0) / 100.0))

        s += int(title_strength * w_t * title_stab)   # default 0.4 — title is a tiebreaker unless user cranks it up

        # INDUSTRY component: cap at 2 hits = full credit. Dominant signal.
        ind_hits = sum(1 for i in profile.get("industries", []) if i and i in blob)
        ind_strength = min(ind_hits / 2.0, 1.0)
        s += int(ind_strength * w_i * ind_stab)       # default 1.0 — full weight

        # SKILLS component: keywords + technologies + frameworks.
        # Section-weighted (2026-05-27): hits in 'requirements' count 3x;
        # 'responsibilities' 2x; 'rest' (intro/perks) 1x; 'nice_to_have' 0.5x.
        # Total weighted hits capped at 8 → strength 1.0.
        skl_terms = (profile.get("keywords", []) or []) + \
                    (profile.get("technologies", []) or []) + \
                    (profile.get("frameworks", []) or [])
        # Parse JD into sections (cached if already done)
        _secs = parse_jd_sections(job.get("description") or "")
        _weights = {"requirements": 3.0, "responsibilities": 2.0, "rest": 1.0, "nice_to_have": 0.5}
        weighted_hits = 0.0
        plain_hits = 0
        for k in skl_terms:
            if not k:
                continue
            for sec_name, sec_text in _secs.items():
                if k in sec_text:
                    weighted_hits += _weights.get(sec_name, 1.0)
                    plain_hits += 1
                    break  # count each skill once per JD
        # Fall back to plain blob match if section parsing yielded nothing
        if not any(_secs.values()):
            weighted_hits = sum(1 for k in skl_terms if k and k in blob)
        skl_strength = min(weighted_hits / 8.0, 1.0)
        kw_hits = plain_hits if plain_hits else sum(1 for k in skl_terms if k and k in blob)
        s += int(skl_strength * w_s * skl_stab)       # default 1.0 — full weight

        # PERFECT-MATCH BONUS (v2): fires when industry AND skills both hit
        # at high strength. Title is no longer required for the bonus —
        # if a job hits 2+ industries AND 5+ skills, it's a strong match
        # regardless of what they happen to call the role.
        if ind_strength >= 1.0 and skl_strength >= 1.0:
            s += 15

        # Penalty (2026-05-26): if NEITHER the title matched a targetTitle
        # NOR did keywords/specialties land any hits in the blob, this is a
        # genuinely-uncertain match. Push it down so real fits win the top.
        if title_strength == 0.0 and kw_hits == 0 and ind_hits == 0:
            s -= 18
    else:
        # Legacy path — used when Worker is unreachable
        if is_senior(job):
            s += 15
        hits = sum(1 for t in RELEVANCE_TERMS if t in blob)
        s += min(hits * 2, 20)

    # Remote bonus
    if is_remote(job):
        s += 10

    # Red flags
    if any(t in blob for t in SCAM_TERMS):
        s -= 40
    if any(t in blob for t in AGENCY_TERMS):
        s -= 20

    # Empty / very short description = suspicious
    if len(job["description"]) < 200:
        s -= 10

    # E1 (refined 2026-05-27): trajectory boost — value 'next-level' jobs MORE
    # than lateral ones because they're the move a senior candidate actually
    # wants. +10 for one rung up, +6 for lateral, -8 for a step down.
    if profile:
        _us = profile.get("targetStage") or _NEXT_STAGE.get(profile.get("careerStage") or "", None) or profile.get("careerStage")
        _js = detect_title_stage(job.get("title") or "")
        _user_now = profile.get("careerStage")
        traj = trajectory_match(_user_now, _js) if _user_now and _js else None
        if traj == "next":
            s += 10
        elif traj == "same":
            s += 6
        elif traj == "down":
            s -= 8

    # E8 (2026-05-27): hiring-velocity boost — companies actively scaling
    # (3+ senior postings in past 30 days) get +5 because they're more
    # likely to actually hire than companies with one stale evergreen posting.
    if profile:
        s += hiring_velocity_boost(job.get("company_name") or "")
        # E9 (2026-05-27): recently-funded boost — companies that raised in
        # the last 12 months are statistically more likely to hire senior
        # leaders. Source: worker /company-stage cache, populated by the
        # enrich-companies workflow (weekly).
        s += recently_funded_boost(job.get("company_name") or "")

    # E7 (2026-05-27, v2): consulting visibility is now user-controlled via
    # companySizeMix.consulting (0-100). Staffing stays hard-blocked (no one
    # asks for staffing-agency listings). In-house gets full credit.
    try:
        ctype = classify_company_type(job.get("company_name") or "", job.get("description") or "")
        if ctype == "staffing":
            return 0  # staffing-agency listings are blanket-blocked
        elif ctype == "consulting":
            # User-controlled multiplier: 0% = blocked, 100% = full credit.
            consulting_pct = 0
            try:
                mix = profile.get("companySizeMix") or {}
                consulting_pct = max(0, min(100, int(mix.get("consulting", 0) or 0)))
            except Exception:
                pass
            # Map 0..100 → 0.0..1.0 multiplier. At 0% behaves like the old hard-block.
            ctype_mult = consulting_pct / 100.0
            if s > 50:
                signal = s - 50
                s = 50 + signal * ctype_mult
            if ctype_mult == 0.0:
                return 0  # respect 0% as a true block
    except Exception:
        pass

    # E6 (2026-05-27): smooth freshness decay — multiplies the post-base
    # signal score by exp(-days/21). Replaces the prior binary recency boost.
    # A 3-day-old listing keeps ~87% of its score; a 30-day-old listing keeps ~24%.
    # Jobs with no posted_at get neutral (1.0) so we don't punish silent ATSes.
    fresh_mult = freshness_multiplier(job.get("posted_at"), job.get("company_name"))
    # Apply ONLY to the SIGNAL portion (above 50 base), so a zero-signal stale
    # job doesn't get pushed negative.
    if s > 50 and fresh_mult < 1.0:
        signal = s - 50
        s = 50 + signal * fresh_mult

    # Healthcare expansion boosts (added 2026-05-28) --------------------
    # Both small, additive, only fire when user opted into healthcare industries.
    # Stacking with warm-intro priority (+200 sprint sort) keeps these companies
    # at the top of the feed for users who match.
    # Uses canonical_company() so 'Bio-Reference Laboratories' and 'BioReference'
    # both match the same network entry.
    try:
        _co_raw = job.get("company_name") or job.get("company_slug") or ""
        _co_canon = canonical_company(_co_raw)
        if _co_canon and SKILLS_PROFILE:
            # (A) Network-seed boost
            net_co = set(canonical_company(c) for c in (SKILLS_PROFILE.get('networkCompanies') or []) if isinstance(c, str))
            if _co_canon in net_co:
                s += 5
            # (B) Curated healthtech catalog boost (gated on healthcare industries)
            _hts = _healthtech_set()
            if _hts and _co_canon in _hts:
                user_inds = ' '.join(str(i).lower() for i in (SKILLS_PROFILE.get('industries') or []))
                if any(kw in user_inds for kw in ('health', 'pharma', 'medic', 'bio', 'ehr', 'clinic', 'wellness', 'therapeut')):
                    s += 3
    except Exception:
        pass

    return max(0, min(100, int(s)))


# --- Storage -------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    fingerprint TEXT PRIMARY KEY,
    source TEXT,
    company_slug TEXT,
    company_name TEXT,
    external_id TEXT,
    title TEXT,
    location TEXT,
    url TEXT,
    posted_at TEXT,
    description TEXT,
    first_seen TEXT,
    last_seen TEXT,
    sightings INTEGER DEFAULT 1,
    remote INTEGER,
    senior INTEGER,
    score INTEGER,
    salary_range TEXT
);
CREATE INDEX IF NOT EXISTS idx_score ON jobs(score DESC);
CREATE INDEX IF NOT EXISTS idx_last_seen ON jobs(last_seen DESC);
"""




