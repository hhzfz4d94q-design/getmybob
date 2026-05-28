"""Role family detection (data scientist vs data engineer, etc.).

Extracted from fetch_jobs.py 2026-05-28 (Phase 5).
"""
import re


ROLE_FAMILIES = {
    "engineering": ["software engineer", "software development engineer", "sde ",
                    "swe ", "backend engineer", "frontend engineer", "full stack",
                    "fullstack", "full-stack", ".net developer", ".net engineer",
                    "java developer", "python developer", "ruby developer", "go developer",
                    "rust developer", "ios developer", "android developer",
                    "mobile engineer", "devops engineer", "site reliability",
                    "platform engineer", "data engineer", "ml engineer", "ai engineer",
                    "infrastructure engineer", "security engineer", "principal engineer",
                    "staff engineer", "senior engineer", "lead engineer", "software developer",
                    "react developer", "vue developer", "angular developer", "engineering manager"],
    "qa": ["quality assurance", "qa lead", "qa manager", "qa engineer", "test lead",
           "test manager", "test engineer", "sdet", "automation engineer",
           "software development engineer in test", "test automation"],
    "sales-rep": ["sales rep", "sales representative", "sdr", "bdr", "account executive",
                  "sales executive", "account manager", "sales manager", "sales director",
                  "sales engineer", "field sales"],
    "marketing-ic": ["marketing manager", "marketing coordinator", "marketing director",
                     "marketing lead", "marketing analyst", "marketing specialist",
                     "vp marketing", "head of marketing", "chief marketing", "cmo",
                     "director of marketing", "director, marketing",
                     "demand generation", "content marketer", "growth marketer",
                     "performance marketer", "email marketer", "seo manager",
                     "ppc manager", "social media manager", "brand manager",
                     "brand director", "director of brand", "head of brand",
                     "vp brand", "brand strategy", "director, brand"],
    "design": ["ux designer", "ui designer", "graphic designer", "product designer", "visual designer",
               "brand designer", "interaction designer", "designer"],
    "operations-coo": ["chief operating officer", "coo", "general manager", "head of operations",
                       "vp operations", "operations executive"],
    "clinical": ["nurse", "physician", "doctor", "rn ", "nurse practitioner", "clinical specialist",
                 "medical director", "medical officer"],
    "recruiting-hr": ["recruiter", "talent acquisition", "talent partner", "people partner",
                      "hr business partner", "head of people"],
    "finance-ic": ["financial analyst", "accountant", "controller", "treasurer", "tax manager",
                   "fp&a analyst", "fp&a manager"],
    "legal-ic": ["paralegal", "associate counsel", "legal counsel"],
    "customer-success": ["customer success manager", "csm", "customer experience manager",
                          "cx manager", "customer support", "client support",
                          "client services", "client delivery", "client success",
                          "client experience", "client partner", "account success",
                          "professional services manager", "implementation specialist",
                          "implementation analyst", "delivery manager"],
    "data-analyst": ["data analyst", "business analyst", "research analyst"],
    # Below families are KEPT for our personas — listing them so user_fam detection works.
    "product": ["product manager", "product director", "vp product", "head of product",
                "chief product", "vp of product", "principal product manager", "product strategy",
                "product growth", "product operations", "product executive", "product leader",
                "product owner", "product lead"],
    "risk-grc": ["risk manager", "risk director", "vp risk", "head of risk", "chief risk",
                 "compliance", "audit", "governance", "grc", "credit risk", "operational risk",
                 "regulatory", "ciso", "cyber risk", "information security"],
    "digital-transformation": ["digital transformation", "transformation lead", "digital strategy",
                                "innovation", "chief digital"],
}

OPEN_USER_FAMS = set()  # no families are "open" — every recognized family enforces incompatibility

INCOMPATIBLE_PAIRS = set()

def _detect_role_family(title):
    """Return the role family of a job title, or None if ambiguous.
    Short tokens (≤4 chars) use word-boundary matching so 'coo' doesn't match
    'coord' / 'cool' etc."""
    if not title:
        return None
    t = " " + title.lower() + " "
    for fam in ("operations-coo", "engineering", "qa", "sales-rep", "marketing-ic",
                "design", "clinical", "recruiting-hr", "finance-ic", "legal-ic",
                "customer-success", "data-analyst", "risk-grc", "product",
                "digital-transformation"):
        for term in ROLE_FAMILIES.get(fam, []):
            tl = term.lower()
            if len(tl) <= 4 and " " not in tl:
                # word-boundary check for short single-token terms
                if re.search(r"(?<![a-z])" + re.escape(tl) + r"(?![a-z])", t):
                    return fam
            else:
                if tl in t:
                    return fam
    return None


def _user_role_family(profile):
    """Detect the user's role family from primaryRole + targetTitles.
    Order: most-specific PROFESSIONS first so digital-transformation doesn't
    win over product/risk/etc. when the user's role mentions both."""
    if not profile:
        return None
    primary = " " + (profile.get("primaryRole") or "").lower() + " "
    # Search order favors specific role families over digital-transformation
    for fam in ("risk-grc", "product", "engineering", "qa", "sales-rep",
                "marketing-ic", "design", "operations-coo", "clinical",
                "recruiting-hr", "finance-ic", "legal-ic", "customer-success",
                "data-analyst", "digital-transformation"):
        for term in ROLE_FAMILIES.get(fam, []):
            tl = term.lower()
            if len(tl) <= 4 and " " not in tl:
                if re.search(r"(?<![a-z])" + re.escape(tl) + r"(?![a-z])", primary):
                    return fam
            else:
                if tl in primary:
                    return fam
    # Fallback to top 5 targetTitles
    for tt in (profile.get("targetTitles") or [])[:5]:
        tl = " " + (tt or "").lower() + " "
        for fam in ("risk-grc", "product", "engineering", "operations-coo",
                    "qa", "design", "digital-transformation"):
            for term in ROLE_FAMILIES.get(fam, []):
                if term.lower() in tl:
                    return fam
    return None


def _is_role_family_mismatch(title, profile):
    """True if job's role family is FUNDAMENTALLY incompatible with the user's."""
    u = _user_role_family(profile)
    if not u or u in OPEN_USER_FAMS:
        return False
    j = _detect_role_family(title)
    if not j:
        return False
    return (u, j) in INCOMPATIBLE_PAIRS


