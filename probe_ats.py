"""
probe_ats.py — Slice A of the ATS-resolver work.

Fetches a user's skills_profile from the Worker, walks their `targetCompanies`,
and probes the public ATS endpoints (Greenhouse / Lever / Ashby / SmartRecruiters)
plus the Welcome to the Jungle job board to verify which one actually serves
jobs for that company. Prints a markdown report comparing what the AI guessed
(atsHint) against what we verified.

Usage:
    python probe_ats.py <user_slug>
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error

WORKER_URL = "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev"
TIMEOUT = 6  # seconds per probe
UA = "Mozilla/5.0 (compatible; getmemyjob-probe/1.0)"


# ---------------- slug helpers ----------------

def slug_variants(name: str):
    """Return ordered, de-duped slug guesses for a company name."""
    base = name.strip().lower().replace("&", "and")
    stripped = re.sub(r"[^\w\s-]", "", base)
    words = stripped.split()
    variants = [
        "".join(words),
        "-".join(words),
        "_".join(words),
        words[0] if words else stripped,
        stripped.replace(" ", ""),
    ]
    seen, out = set(), []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


# ---------------- network helpers ----------------

def http_get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status, resp.headers.get("content-type", ""), resp.read()


def http_get_json(url: str):
    try:
        status, ctype, body = http_get(url)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return None
    if status != 200 or "json" not in ctype.lower():
        return None
    try:
        return json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None


# ---------------- per-source probes ----------------

def probe_greenhouse(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    data = http_get_json(url)
    if isinstance(data, dict) and isinstance(data.get("jobs"), list) and len(data["jobs"]) > 0:
        return {"source": "greenhouse", "token": slug, "jobs": len(data["jobs"]), "url": url}
    return None


def probe_lever(slug):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    data = http_get_json(url)
    if isinstance(data, list) and len(data) > 0:
        return {"source": "lever", "token": slug, "jobs": len(data), "url": url}
    return None


def probe_ashby(slug):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    data = http_get_json(url)
    if isinstance(data, dict) and isinstance(data.get("jobs"), list) and len(data["jobs"]) > 0:
        return {"source": "ashby", "token": slug, "jobs": len(data["jobs"]), "url": url}
    return None


def probe_smartrecruiters(slug):
    """SR returns 200 + totalFound:0 for ANY slug, so 0 jobs is NOT a real hit.
    Only count it if at least one posting is actually present."""
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    data = http_get_json(url)
    if not isinstance(data, dict):
        return None
    total = data.get("totalFound", len(data.get("content", []) or []))
    if total > 0:
        return {"source": "smartrecruiters", "token": slug, "jobs": total, "url": url}
    return None


def probe_wttj(slug):
    """Welcome to the Jungle is a job-board, not an ATS. Confirm the page
    loads, looks like a real company page for this slug, and exposes at
    least one job link."""
    url = f"https://www.welcometothejungle.com/en/companies/{slug}"
    try:
        status, ctype, body = http_get(url)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return None
    if status != 200:
        return None
    html = body.decode("utf-8", errors="replace").lower()
    if "welcome to the jungle" not in html or slug.lower() not in html:
        return None
    job_links = set(re.findall(rf"/companies/{re.escape(slug.lower())}/jobs/[a-z0-9\-]+", html))
    if not job_links:
        return None
    return {"source": "wttj", "token": slug, "jobs": len(job_links), "url": url}


# --------- Workday ---------
# Workday is per-company. The AI's targetCompanies entries can carry an
# `atsUrl` like "capitalone.wd1.myworkdayjobs.com/External"; we use that
# hint when available, and fall back to a small set of common patterns.

WORKDAY_URL_RE = re.compile(
    r"^(?:https?://)?([a-z0-9-]+)\.wd(\d+)\.myworkdayjobs\.com/(?:wday/cxs/[^/]+/)?([^/?#]+)",
    re.IGNORECASE,
)


WORKDAY_TIMEOUT = 4  # tighter than the GET timeout; bad subdomains hang on DNS


def probe_workday(slug, ats_url=None):
    """Only probe Workday when the AI gave us an explicit atsUrl hint.
    Generic guessing across thousands of possible subdomains causes minutes
    of DNS timeouts and is rarely productive — better to leave a company
    as 'unknown' and surface it for manual atsUrl entry."""
    if not ats_url:
        return None
    m = WORKDAY_URL_RE.match(ats_url.strip())
    if not m:
        return None
    sub, n, site = m.groups()
    url = f"https://{sub.lower()}.wd{n}.myworkdayjobs.com/wday/cxs/{sub.lower()}/{site}/jobs"
    try:
        req = urllib.request.Request(
            url,
            method="POST",
            data=b'{"limit":1,"offset":0,"searchText":""}',
            headers={"User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=WORKDAY_TIMEOUT) as resp:
            if resp.status != 200:
                return None
            if "json" not in resp.headers.get("content-type", "").lower():
                return None
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return None
    total = body.get("total", 0) if isinstance(body, dict) else 0
    if total > 0:
        return {"source": "workday", "token": f"{sub}/{site}", "jobs": total, "url": url}
    return None


# (source-name, probe-fn) — checked in this order, with AI hint reordering
PROBES = [
    ("greenhouse", probe_greenhouse),
    ("lever", probe_lever),
    ("ashby", probe_ashby),
    ("smartrecruiters", probe_smartrecruiters),
    ("workday", probe_workday),
    ("wttj", probe_wttj),
]


def probe_company(name: str, ai_hint: str = "unknown", ats_url: str = None):
    """Try every (slug, source) combination until one returns a hit."""
    ordered = sorted(PROBES, key=lambda p: 0 if p[0] == ai_hint else 1)
    for slug in slug_variants(name):
        for source_name, fn in ordered:
            try:
                hit = fn(slug, ats_url) if source_name == "workday" else fn(slug)
            except TypeError:
                hit = fn(slug)
            if hit:
                return hit
        time.sleep(0.05)
    return {"source": "unknown", "token": None, "jobs": 0, "url": None}


# ---------------- main ----------------

def load_profile(user_slug: str):
    """The Worker returns {profile: {...}, user: "<slug>"}. Unwrap the
    inner profile so callers see the same shape regardless of envelope."""
    url = f"{WORKER_URL}/skills-profile?user={user_slug}"
    data = http_get_json(url)
    if not data:
        raise RuntimeError(f"Could not load profile for {user_slug} from {url}")
    if isinstance(data, dict) and isinstance(data.get("profile"), dict):
        return data["profile"]
    return data


def main():
    user_slug = sys.argv[1] if len(sys.argv) > 1 else "geetu"
    profile = load_profile(user_slug)
    targets = profile.get("targetCompanies", []) or []

    lines = []
    lines.append(f"# ATS resolution report — `{user_slug}`")
    lines.append("")
    lines.append(f"Target companies in profile: **{len(targets)}**")
    lines.append("")

    if not targets:
        lines.append("_No targetCompanies in this user's profile — nothing to probe._")
        lines.append("")
        lines.append("## Diagnostic dump")
        lines.append("")
        lines.append(f"Profile has **{len(profile)}** top-level keys:")
        lines.append("")
        lines.append("```")
        for k in sorted(profile.keys()):
            v = profile[k]
            if isinstance(v, list):
                shape = f"list[{len(v)}]"
                sample = (json.dumps(v[0]) if v else "[]")[:120]
            elif isinstance(v, dict):
                shape = f"dict[{len(v)} keys]"
                sample = json.dumps(list(v.keys()))[:120]
            elif isinstance(v, str):
                shape = f"str[{len(v)}]"
                sample = repr(v[:80])
            else:
                shape = type(v).__name__
                sample = repr(v)
            lines.append(f"{k:24s} {shape:18s} {sample}")
        lines.append("```")
        lines.append("")
        # Look for anything that looks like it could be a target-companies field
        target_keys = [k for k in profile if "target" in k.lower() or "compan" in k.lower()]
        if target_keys:
            lines.append("**Candidate target/company keys found:**")
            for k in target_keys:
                lines.append(f"- `{k}`: `{json.dumps(profile[k])[:200]}`")
        report = "\n".join(lines)
        print(report)
        with open("probe_report.md", "w", encoding="utf-8") as f:
            f.write(report + "\n")
        return

    lines.append("| Company | AI hint | Verified source | Token | Jobs | Match? |")
    lines.append("|---|---|---|---|---:|:---:|")

    resolved = 0
    disagreements = []
    by_source = {}
    for tc in targets:
        name = tc.get("name", "")
        ai_hint = (tc.get("atsHint") or "unknown").lower()
        ats_url = tc.get("atsUrl") or ""
        result = probe_company(name, ai_hint, ats_url)
        src = result["source"]
        match = "OK" if src == ai_hint else ("NEW" if src != "unknown" else "--")
        if src != "unknown":
            resolved += 1
            by_source[src] = by_source.get(src, 0) + 1
            if ai_hint not in ("unknown", "") and ai_hint != src:
                disagreements.append((name, ai_hint, src))
        lines.append(
            f"| {name} | {ai_hint} | {src} | "
            f"{result['token'] or '—'} | {result['jobs']} | {match} |"
        )

    rate = (resolved * 100 // len(targets)) if targets else 0
    lines.append("")
    lines.append(f"**Resolved: {resolved} / {len(targets)} ({rate}%)**")

    if by_source:
        lines.append("")
        lines.append("## Breakdown by source")
        lines.append("")
        for src, n in sorted(by_source.items(), key=lambda kv: -kv[1]):
            lines.append(f"- **{src}**: {n}")

    if disagreements:
        lines.append("")
        lines.append("## AI-vs-verified disagreements")
        lines.append("")
        for name, ai_hint, actual in disagreements:
            lines.append(f"- **{name}**: AI guessed `{ai_hint}`, actually `{actual}`")

    report = "\n".join(lines)
    print(report)
    with open("probe_report.md", "w", encoding="utf-8") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()
