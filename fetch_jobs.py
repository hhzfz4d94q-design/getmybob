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
import sqlite3
import sys
import time
from datetime import datetime, timezone
from hashlib import sha256
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Ghost job threshold (days). Listings older than this are flagged as
# possibly not actively hiring.
GHOST_DAYS = 30

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "jobs.db")
COMPANIES_PATH = os.path.join(ROOT, "companies.json")
DASHBOARD_PATH = os.path.join(ROOT, "index.html")

# --- Profile-specific scoring (tuned for Geetanjali Arora) ---------------

# Senior leadership signal — title must contain at least one of these
SENIOR_TITLE_TERMS = [
    "vp", "vice president", "head of", "director", "sr director",
    "senior director", "principal", "chief", "lead", "executive"
]

# Healthcare-IT / digital transformation relevance — bonus points
RELEVANCE_TERMS = [
    "healthcare", "health", "clinical", "patient", "ehr", "emr",
    "digital transformation", "digital health", "product",
    "portfolio", "program", "platform", "saas", "ai", "agile",
    "scrum", "transformation", "operations", "delivery"
]

# Red flags — these subtract from score
SCAM_TERMS = [
    "earn from home", "make money", "no experience needed",
    "commission only", "100% remote opportunity!!!", "$$$",
    "work from anywhere worldwide"
]

# Staffing-agency / third-party recruiter giveaways
AGENCY_TERMS = [
    "our client", "client of ours", "leading client", "fortune 500 client",
    "contract to hire", "c2h", "w2 only", "1099 contract"
]


# --- HTTP helpers --------------------------------------------------------

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HealthTechJobsFetcher/1.0"


def fetch_json(url, timeout=15, data=None, method=None):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    else:
        body = None
    req = Request(url, headers=headers, data=body, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        return None
    except (URLError, TimeoutError):
        return None
    except Exception:
        return None


# --- ATS adapters --------------------------------------------------------

def _extract_greenhouse_salary(j):
    # Look in metadata (custom fields) and pay_input_ranges
    pir = j.get("pay_input_ranges") or []
    if pir:
        try:
            r = pir[0]
            mn, mx = r.get("min_cents"), r.get("max_cents")
            cur = (r.get("currency_type") or "USD").upper()
            sym = "$" if cur == "USD" else (cur + " ")
            if mn and mx:
                return f"{sym}{mn//100:,} - {sym}{mx//100:,}"
        except Exception:
            pass
    for item in j.get("metadata") or []:
        name = (item.get("name") or "").lower()
        if any(k in name for k in ["salary", "pay range", "pay band", "compensation"]):
            val = item.get("value")
            if val:
                return str(val)[:200]
    return ""


def fetch_greenhouse(slug):
    """Greenhouse public job board API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    data = fetch_json(url)
    if not data or "jobs" not in data:
        return []
    out = []
    for j in data["jobs"]:
        loc = (j.get("location") or {}).get("name") or ""
        out.append({
            "source": "greenhouse",
            "company_slug": slug,
            "company_name": slug.replace("-", " ").title(),
            "external_id": str(j.get("id")),
            "title": j.get("title", ""),
            "location": loc,
            "url": j.get("absolute_url", ""),
            "posted_at": j.get("updated_at") or j.get("first_published"),
            "description": _strip_html((j.get("content") or "")),
            "salary_range": _extract_greenhouse_salary(j),
        })
    return out


def _extract_lever_salary(j):
    sr = j.get("salaryRange") or {}
    mn, mx = sr.get("min"), sr.get("max")
    if mn and mx:
        cur = (sr.get("currency") or "USD").upper()
        sym = "$" if cur == "USD" else (cur + " ")
        interval = sr.get("interval") or ""
        suffix = f" / {interval}" if interval and interval.lower() != "per-year-salary" else ""
        try:
            return f"{sym}{int(mn):,} - {sym}{int(mx):,}{suffix}"
        except Exception:
            return f"{sym}{mn} - {sym}{mx}{suffix}"
    desc = j.get("salaryDescription") or ""
    return _strip_html(desc)[:200]


def fetch_lever(slug):
    """Lever public job board API."""
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    data = fetch_json(url)
    if not isinstance(data, list):
        return []
    out = []
    for j in data:
        loc = ((j.get("categories") or {}).get("location")) or ""
        out.append({
            "source": "lever",
            "company_slug": slug,
            "company_name": slug.replace("-", " ").title(),
            "external_id": str(j.get("id")),
            "title": j.get("text", ""),
            "location": loc,
            "url": j.get("hostedUrl", ""),
            "posted_at": (
                datetime.fromtimestamp(j["createdAt"] / 1000, tz=timezone.utc).isoformat()
                if j.get("createdAt") else None
            ),
            "description": _strip_html(j.get("descriptionPlain") or j.get("description") or ""),
            "salary_range": _extract_lever_salary(j),
        })
    return out


def _extract_ashby_salary(j):
    comp = j.get("compensation") or {}
    summary = comp.get("compensationTierSummary") or j.get("compensationTierSummary") or ""
    if summary:
        return _strip_html(summary)[:200]
    # Fall back to summary components if Ashby returns them
    components = comp.get("summaryComponents") or []
    parts = []
    for c in components:
        s = c.get("summary") or c.get("compensationType")
        if s:
            parts.append(str(s))
    return " · ".join(parts)[:200]


def fetch_ashby(slug):
    """Ashby public job board (HTML→JSON endpoint)."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    data = fetch_json(url)
    if not data or "jobs" not in data:
        return []
    out = []
    for j in data["jobs"]:
        loc = j.get("location") or ""
        out.append({
            "source": "ashby",
            "company_slug": slug,
            "company_name": (data.get("companyName") or slug).replace("-", " ").title(),
            "external_id": str(j.get("id")),
            "title": j.get("title", ""),
            "location": loc,
            "url": j.get("jobUrl", ""),
            "posted_at": j.get("publishedAt"),
            "description": _strip_html(j.get("descriptionHtml") or j.get("descriptionPlain") or ""),
            "salary_range": _extract_ashby_salary(j),
        })
    return out


def fetch_workday(entry):
    """Workday Cxs API. Entry: {name, tenant, subdomain, site}.
    Pages through results (Workday paginates at 20 per request)."""
    if not isinstance(entry, dict):
        return []
    tenant = entry.get("tenant")
    sub = entry.get("subdomain", "wd1")
    site = entry.get("site")
    name = entry.get("name", tenant)
    if not (tenant and site):
        return []
    base = f"https://{tenant}.{sub}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    out = []
    offset = 0
    page_size = 20
    while offset < 200:  # cap at 200 jobs per company to be polite
        payload = {"appliedFacets": {}, "limit": page_size, "offset": offset, "searchText": ""}
        data = fetch_json(api, data=payload, method="POST", timeout=20)
        if not data or "jobPostings" not in data:
            break
        postings = data["jobPostings"]
        if not postings:
            break
        for j in postings:
            ext_path = j.get("externalPath") or ""
            url = f"{base}{ext_path}" if ext_path else ""
            out.append({
                "source": "workday",
                "company_slug": tenant,
                "company_name": name,
                "external_id": j.get("bulletFields", [None])[0] or ext_path or j.get("title"),
                "title": j.get("title", ""),
                "location": j.get("locationsText", "") or j.get("locations", ""),
                "url": url,
                "posted_at": j.get("postedOn", ""),
                "description": "",  # Workday requires a second API call per job for full description
                "salary_range": "",  # Workday salary requires per-job detail call; skip for now
            })
        offset += page_size
        if offset >= (data.get("total") or 0):
            break
        time.sleep(0.2)
    return out


SOURCES = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby, "workday": fetch_workday}


# --- Utilities -----------------------------------------------------------

def _strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:4000]


STOP_WORDS = {"of", "the", "and", "for", "a", "an", "to", "with", "in", "on", "at", "by", "or"}


# Titles that look healthcare-y but aren't a fit for Geetanjali's profile
# (senior product / digital transformation / IT in healthcare — NOT a clinician,
# pharmacist, nurse, medical affairs, or pure sales/marketing role).
IRRELEVANT_TITLE_TERMS = [
    # Clinical practice roles (not IT/product)
    "clinical trial", "clinical research", "clinical operations",
    "clinical success", "clinical quality", "clinical educator",
    "clinical pharmacist", "clinical psychologist", "clinical specialist",
    "clinical lead",
    # Healthcare practitioners
    "pharmacy", "pharmacist", "nursing", "nurse practitioner",
    "registered nurse", "physician", "psychiatrist", "psychologist",
    "social worker", "behavioral therapist", "case manager",
    "care coordinator", "care manager",
    # Medical affairs (separate from product/IT)
    "medical affairs", "medical director", "medical writer",
    # Pure sales (Geetanjali is product/IT, not sales)
    "director of sales", "head of sales", "vp of sales",
    "vice president of sales", "vice president, sales",
    "sales director", "regional sales manager", "enterprise sales",
    "account executive",
    # Marketing (different focus from product)
    "marketing director", "head of marketing", "vp of marketing",
    "vp, marketing",
    # Other non-fit functions
    "general counsel", "compliance officer", "chief financial officer",
    "human resources",
]


def _is_irrelevant_title(title):
    t = (title or "").lower()
    return any(term in t for term in IRRELEVANT_TITLE_TERMS)


def _normalize_title(title):
    """Lowercase, strip stop words, then concatenate alphanumerics so minor wording
    differences ('Director of Product' vs 'Director, Product') collapse to the same hash."""
    words = re.split(r"[^a-z0-9]+", (title or "").lower())
    return "".join(w for w in words if w and w not in STOP_WORDS)


def fingerprint(job):
    """Stable hash so the same role across reposts/sources dedupes."""
    base = f"{job['company_slug']}|{_normalize_title(job['title'])}|{re.sub(r'[^a-z0-9]+', '', (job['location'] or '').lower())}"
    return sha256(base.encode()).hexdigest()[:16]


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


def score_job(job):
    """0-100 score. Higher = more relevant + more likely 'real'."""
    s = 50
    blob = f"{job['title']} {job['description']}".lower()

    # Profile mismatch — bring to very low score so it won't appear
    if _is_irrelevant_title(job["title"]):
        return 0

    # Seniority bonus
    if is_senior(job):
        s += 15

    # Healthcare/digital relevance
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

    return max(0, min(100, s))


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


def get_conn():
    # Self-heal: if the DB file exists but is corrupt/empty, wipe it and retry.
    for attempt in range(2):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.executescript(SCHEMA)
            # Migration: add salary_range to older DBs that don't have it
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN salary_range TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # column already exists
            return conn
        except sqlite3.DatabaseError:
            if attempt == 0 and os.path.exists(DB_PATH):
                try:
                    os.remove(DB_PATH)
                    for sidecar in (DB_PATH + "-journal", DB_PATH + "-wal", DB_PATH + "-shm"):
                        if os.path.exists(sidecar):
                            os.remove(sidecar)
                except OSError:
                    pass
            else:
                raise


def upsert_job(conn, job):
    fp = fingerprint(job)
    now = datetime.now(timezone.utc).isoformat()
    remote = 1 if is_remote(job) else 0
    senior = 1 if is_senior(job) else 0
    score = score_job(job)

    salary = job.get("salary_range") or ""
    cur = conn.execute("SELECT fingerprint, sightings FROM jobs WHERE fingerprint=?", (fp,))
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE jobs SET last_seen=?, sightings=sightings+1, score=?, remote=?, senior=?, salary_range=? WHERE fingerprint=?",
            (now, score, remote, senior, salary, fp),
        )
    else:
        conn.execute(
            """INSERT INTO jobs (fingerprint, source, company_slug, company_name, external_id,
               title, location, url, posted_at, description, first_seen, last_seen,
               sightings, remote, senior, score, salary_range)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?)""",
            (fp, job["source"], job["company_slug"], job["company_name"], job["external_id"],
             job["title"], job["location"], job["url"], job["posted_at"], job["description"],
             now, now, remote, senior, score, salary),
        )


# --- Main pipeline -------------------------------------------------------

def run():
    with open(COMPANIES_PATH) as f:
        companies = json.load(f)

    conn = get_conn()
    totals = {"greenhouse": 0, "lever": 0, "ashby": 0}
    failures = []

    totals["workday"] = 0
    for source, fetcher in SOURCES.items():
        entries = companies.get(source, [])
        print(f"\n[{source}] {len(entries)} companies")
        for i, entry in enumerate(entries, 1):
            label = entry.get("name", entry.get("tenant", "?")) if isinstance(entry, dict) else entry
            try:
                jobs = fetcher(entry)
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

    generate_dashboard(conn)
    conn.close()


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


def generate_dashboard(conn):
    rows = conn.execute("""
        SELECT fingerprint, company_name, title, location, url, posted_at, first_seen, last_seen,
               sightings, remote, senior, score, description, salary_range
        FROM jobs
        WHERE last_seen >= datetime('now', '-30 days')
        ORDER BY score DESC, last_seen DESC
        LIMIT 2000
    """).fetchall()
    # Hide jobs that aren't a fit for Geetanjali's product/IT profile
    rows = [r for r in rows if not _is_irrelevant_title(r[2])]
    rows = rows[:1000]

    # Stats
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    senior_remote = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE senior=1 AND remote=1 AND last_seen >= datetime('now','-7 days')"
    ).fetchone()[0]
    ghost = conn.execute(
        f"SELECT COUNT(*) FROM jobs WHERE julianday(last_seen) - julianday(first_seen) > {GHOST_DAYS}"
    ).fetchone()[0]

    cards = []
    for r in rows:
        (fp, company, title, loc, url, posted_at, first_seen, last_seen,
         sightings, remote, senior, score, desc, salary) = r
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
        if listed_days == 0: badges.append('<span class="b fresh">New today</span>')
        elif listed_days is not None and listed_days <= 7: badges.append('<span class="b week">This week</span>')
        if ghost_flag: badges.append(f'<span class="b ghost">Ghost? {listed_days}d</span>')
        if sightings > 3: badges.append(f'<span class="b repost">Seen {sightings}×</span>')
        badge_html = " ".join(badges)
        salary_html = f'<div class="salary-row"><span class="salary">{_esc(salary)}</span></div>' if salary else ''

        cards.append(f"""
        <div class="card" data-fp="{fp}" data-score="{score}" data-senior="{senior}" data-remote="{remote}" data-listed-days="{listed_days if listed_days is not None else 9999}" data-salary-max="{salary_max}" data-last-seen="{last_seen or ''}" data-first-seen="{first_seen or ''}">
          <div class="row1">
            <div class="title"><a href="{url}" target="_blank">{_esc(title)}</a></div>
            <div class="score">{score}</div>
          </div>
          <div class="row2">
            <span class="company">{_esc(company)}</span> ·
            <span class="loc">{_esc(loc or 'Location N/A')}</span> ·
            <span class="age">{listed_days}d old</span>
          </div>
          {salary_html}
          <div class="badges" data-badges>{badge_html}</div>
          <div class="desc">{_esc(desc[:300])}…</div>
          <div class="actions">
            <button class="btn primary" onclick="prepApplication('{fp}', this)">Prep Application</button>
            <button class="btn track" onclick="cycleStatus('{fp}', this)" data-status-for="{fp}">Mark Applied</button>
            <a class="btn ghost-btn" href="{url}" target="_blank">Open Listing →</a>
          </div>
        </div>""")

    html = HTML_TEMPLATE.format(
        total=total,
        senior_remote=senior_remote,
        ghost=ghost,
        generated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        shown=len(rows),
        cards="\n".join(cards) or "<p>No jobs yet — run the fetcher.</p>",
    )
    with open(DASHBOARD_PATH, "w") as f:
        f.write(html)
    print(f"\nDashboard written: {DASHBOARD_PATH}")


def _days_old(iso):
    if not iso: return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return None


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>HealthTech Jobs — Geetanjali</title>
<style>
  body {{ font: 14px -apple-system, system-ui, sans-serif; margin: 0; background: #f7f7f8; color: #222; }}
  header {{ background: #1f3a5f; color: white; padding: 18px 28px; position: relative; }}
  header h1 {{ margin: 0; font-size: 20px; }}
  header .sub {{ opacity: .85; font-size: 13px; margin-top: 4px; }}
  .header-actions {{ position: absolute; right: 28px; top: 50%; transform: translateY(-50%); display: flex; gap: 8px; }}
  .header-btn {{ background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }}
  .header-btn:hover {{ background: rgba(255,255,255,0.25); }}
  .header-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
  .stats {{ display: flex; gap: 24px; padding: 14px 28px; background: white; border-bottom: 1px solid #e5e5ea; }}
  .stat {{ font-size: 13px; }}
  .stat b {{ font-size: 22px; display: block; color: #1f3a5f; }}
  .filters {{ padding: 12px 28px; background: white; border-bottom: 1px solid #e5e5ea; display: flex; gap: 12px; }}
  .filters input, .filters select {{ padding: 6px 10px; font-size: 13px; border: 1px solid #ddd; border-radius: 6px; }}
  .grid {{ padding: 18px 28px; display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 14px; }}
  .card {{ background: white; border-radius: 10px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .row1 {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }}
  .title a {{ color: #1f3a5f; text-decoration: none; font-weight: 600; font-size: 15px; }}
  .title a:hover {{ text-decoration: underline; }}
  .score {{ background: #1f3a5f; color: white; border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 600; }}
  .row2 {{ font-size: 12px; color: #666; margin-top: 4px; }}
  .badges {{ margin: 8px 0; display: flex; flex-wrap: wrap; gap: 6px; }}
  .b {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; }}
  .b.senior {{ background: #e6f0ff; color: #1f3a5f; }}
  .b.remote {{ background: #e6fff0; color: #0a6b3a; }}
  .b.ghost {{ background: #fff1e6; color: #a85c00; }}
  .b.repost {{ background: #ffe6e6; color: #a80000; }}
  .b.fresh {{ background: #fffbe6; color: #8a6d00; font-weight: 600; }}
  .b.week {{ background: #f0e6ff; color: #4b2e9c; }}
  .pill {{ font-size: 12px; padding: 5px 12px; border-radius: 999px; border: 1px solid #ddd; background: white; cursor: pointer; }}
  .pill.active {{ background: #1f3a5f; color: white; border-color: #1f3a5f; }}
  .actions {{ margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }}
  .btn {{ font-size: 12px; padding: 6px 10px; border-radius: 6px; border: 1px solid #ddd; background: white; cursor: pointer; color: #333; text-decoration: none; display: inline-block; }}
  .btn:hover {{ background: #f0f0f0; }}
  .btn.primary {{ background: #1f3a5f; color: white; border-color: #1f3a5f; }}
  .btn.primary:hover {{ background: #2d4f7a; }}
  .btn.track.applied {{ background: #0a6b3a; color: white; border-color: #0a6b3a; }}
  .btn.track.phonescreen {{ background: #c97a00; color: white; border-color: #c97a00; }}
  .btn.track.onsite {{ background: #7a009c; color: white; border-color: #7a009c; }}
  .btn.track.offer {{ background: #ff7700; color: white; border-color: #ff7700; }}
  .btn.track.rejected {{ background: #888; color: white; border-color: #888; }}
  .b.applied {{ background: #d6f5e3; color: #0a6b3a; }}
  .b.phonescreen {{ background: #fce5b8; color: #6b4500; }}
  .b.onsite {{ background: #ead4ff; color: #4b2e9c; }}
  .b.offer {{ background: #ffd9b3; color: #a04500; }}
  .b.rejected {{ background: #e8e8e8; color: #666; }}
  .app-tracker {{ padding: 14px 28px; background: white; border-bottom: 1px solid #e5e5ea; }}
  .view-toggle {{ display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }}
  .view-toggle .pill {{ font-size: 13px; padding: 6px 14px; }}
  .view-label {{ font-size: 12px; color: #666; margin-right: 4px; font-weight: 600; }}
  .app-stats {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .app-stat {{ font-size: 12px; padding: 8px 14px; border-radius: 8px; min-width: 80px; }}
  .app-stat b {{ font-size: 20px; display: block; font-weight: 700; line-height: 1.15; }}
  .app-stat.applied {{ background: #d6f5e3; color: #0a6b3a; }}
  .app-stat.phonescreen {{ background: #fce5b8; color: #6b4500; }}
  .app-stat.onsite {{ background: #ead4ff; color: #4b2e9c; }}
  .app-stat.offer {{ background: #ffd9b3; color: #a04500; }}
  .app-stat.rejected {{ background: #e8e8e8; color: #666; }}
  .app-stat.response {{ background: #1f3a5f; color: white; }}
  body.apps-mode .card[data-status="offer"] {{ order: 1; }}
  body.apps-mode .card[data-status="onsite"] {{ order: 2; }}
  body.apps-mode .card[data-status="phonescreen"] {{ order: 3; }}
  body.apps-mode .card[data-status="applied"] {{ order: 4; }}
  body.apps-mode .card[data-status="rejected"] {{ order: 5; }}
  .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 100; align-items: center; justify-content: center; padding: 20px; }}
  .modal-overlay.show {{ display: flex; }}
  .modal {{ background: white; border-radius: 12px; padding: 24px; max-width: 600px; width: 100%; max-height: 80vh; overflow-y: auto; }}
  .modal h3 {{ margin: 0 0 12px 0; color: #1f3a5f; }}
  .modal pre {{ background: #f5f5f5; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; }}
  .modal .copy-btn {{ margin-top: 10px; }}
  .modal-close {{ float: right; cursor: pointer; font-size: 22px; line-height: 1; color: #999; }}
  .prep-result-modal {{ max-width: 760px; }}
  .prep-status {{ font-size: 13px; color: #555; padding: 14px 0; }}
  .prep-status.error {{ color: #a80000; }}
  .prep-section {{ margin: 18px 0; padding-bottom: 18px; border-bottom: 1px solid #eee; }}
  .prep-section:last-child {{ border-bottom: none; }}
  .prep-label {{ font-size: 12px; font-weight: 700; color: #1f3a5f; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
  .prep-text {{ background: #f7f7f8; padding: 12px; border-radius: 6px; font-size: 13px; white-space: pre-wrap; word-wrap: break-word; line-height: 1.5; font-family: inherit; max-height: 260px; overflow-y: auto; margin: 0 0 8px 0; }}
  .desc {{ font-size: 12.5px; color: #444; margin-top: 6px; line-height: 1.4; }}
  .salary-row {{ margin: 6px 0 2px 0; }}
  .salary {{ display: inline-block; background: #e6fff0; color: #0a6b3a; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }}
  .tabs {{ display: flex; gap: 4px; border-bottom: 1px solid #e0e0e0; margin: 10px 0 16px 0; }}
  .tab-btn {{ background: none; border: none; padding: 8px 14px; cursor: pointer; font-size: 13px; color: #666; border-bottom: 2px solid transparent; font-weight: 500; }}
  .tab-btn.active {{ color: #1f3a5f; border-bottom-color: #1f3a5f; font-weight: 700; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .dropzone {{ border: 2px dashed #c0c8d4; border-radius: 8px; padding: 28px 16px; text-align: center; background: #fafbfc; transition: all 0.15s; cursor: pointer; }}
  .dropzone:hover, .dropzone.drag {{ background: #eef3fa; border-color: #1f3a5f; }}
  .dropzone strong {{ display: block; font-size: 14px; color: #1f3a5f; margin-bottom: 4px; }}
  .dropzone span {{ font-size: 12px; color: #666; }}
  .version-row {{ display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid #e6e8eb; border-radius: 6px; margin-bottom: 6px; background: #fff; }}
  .version-row.active {{ border-color: #1f3a5f; background: #f3f7fc; }}
  .version-main {{ flex: 1; min-width: 0; }}
  .version-label {{ font-weight: 600; font-size: 13px; color: #1f3a5f; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .version-meta {{ font-size: 11px; color: #777; margin-top: 2px; }}
  .version-badge {{ background: #1f3a5f; color: white; font-size: 10px; padding: 2px 7px; border-radius: 10px; font-weight: 700; letter-spacing: 0.3px; }}
  .version-actions {{ display: flex; gap: 4px; }}
  .v-btn {{ background: #f3f4f6; border: 1px solid #ddd; color: #333; padding: 5px 10px; border-radius: 4px; font-size: 11px; cursor: pointer; font-weight: 500; }}
  .v-btn:hover {{ background: #e6e8eb; }}
  .v-btn.danger {{ color: #b00; }}
  .v-btn.primary {{ background: #1f3a5f; color: white; border-color: #1f3a5f; }}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js"></script>
</head><body>
<header>
  <h1>HealthTech Jobs for Geetanjali</h1>
  <div class="sub">Senior leadership · Healthcare IT · Remote · Generated {generated}</div>
  <div class="header-actions">
    <button id="resume-btn" class="header-btn" onclick="openResumeModal()">Resume</button>
    <button id="refresh-btn" class="header-btn" onclick="refreshData()">Refresh data</button>
  </div>
</header>
<div class="stats">
  <div class="stat"><b>{total}</b>Total jobs tracked</div>
  <div class="stat"><b>{senior_remote}</b>Senior + Remote (last 7d)</div>
  <div class="stat"><b>{ghost}</b>Possible ghost jobs (60d+)</div>
  <div class="stat"><b id="shown-counter">{shown}</b>Showing</div>
</div>
<div class="app-tracker">
  <div class="view-toggle">
    <span class="view-label">View:</span>
    <button class="pill active" id="view-all" onclick="setView('all')">All Jobs</button>
    <button class="pill" id="view-apps" onclick="setView('apps')">My Applications</button>
  </div>
  <div class="app-stats">
    <div class="app-stat applied"><b id="cnt-applied">0</b>Applied</div>
    <div class="app-stat phonescreen"><b id="cnt-phonescreen">0</b>Phone Screens</div>
    <div class="app-stat onsite"><b id="cnt-onsite">0</b>Onsites</div>
    <div class="app-stat offer"><b id="cnt-offer">0</b>Offers</div>
    <div class="app-stat rejected"><b id="cnt-rejected">0</b>Rejected</div>
    <div class="app-stat response"><b id="cnt-response">--</b>Response rate</div>
  </div>
</div>
<div class="filters">
  <input type="text" id="q" placeholder="Search title or company…" oninput="filter()">
  <select id="srOnly" onchange="filter()">
    <option value="">All jobs</option>
    <option value="srOnly">Senior + Remote only</option>
    <option value="sOnly">Senior only</option>
    <option value="rOnly">Remote only</option>
  </select>
  <select id="trackedFilter" onchange="filter()">
    <option value="">Tracker: all</option>
    <option value="untouched">Not yet applied</option>
    <option value="applied">Applied</option>
    <option value="phonescreen">Phone screen</option>
    <option value="onsite">Onsite</option>
    <option value="offer">Offer</option>
    <option value="rejected">Rejected</option>
  </select>
  <select id="salaryFilter" onchange="filter()">
    <option value="">Salary: any</option>
    <option value="listed">With salary listed</option>
    <option value="100000">$100k+</option>
    <option value="150000">$150k+</option>
    <option value="200000">$200k+</option>
    <option value="250000">$250k+</option>
  </select>
  <select id="sortBy" onchange="sortCards()">
    <option value="score">Sort: Best match</option>
    <option value="salary">Sort: Salary (high to low)</option>
    <option value="recent">Sort: Most recent</option>
    <option value="ghost">Sort: Newest postings first</option>
  </select>
  <span style="display:flex; gap:6px; align-items:center;">
    <button class="pill active" data-window="all" onclick="setWindow(this,'all')">All</button>
    <button class="pill" data-window="0" onclick="setWindow(this,0)">Today</button>
    <button class="pill" data-window="7" onclick="setWindow(this,7)">Last 7 days</button>
    <button class="pill" data-window="30" onclick="setWindow(this,30)">Last 30 days</button>
  </span>
</div>
<div class="grid" id="grid">
{cards}
</div>

<div class="modal-overlay" id="resume-modal" onclick="if(event.target===this)closeResumeModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeResumeModal()">&times;</span>
    <h3>Geetanjali's Resume</h3>
    <p class="prep-status" id="resume-status">Loading…</p>
    <div id="resume-editor" style="display:none;">
      <div class="tabs">
        <button class="tab-btn active" data-tab="upload" onclick="setResumeTab('upload')">Upload File</button>
        <button class="tab-btn" data-tab="versions" onclick="setResumeTab('versions')">Versions</button>
        <button class="tab-btn" data-tab="json" onclick="setResumeTab('json')">Edit JSON</button>
      </div>

      <div class="tab-panel active" id="tab-upload">
        <p style="font-size:13px;color:#555;margin-bottom:10px;">Upload Geetanjali's resume as PDF or Word. The AI converts it to structured form and saves a new version.</p>
        <label for="resume-file-input" class="dropzone" id="resume-dropzone">
          <strong id="dropzone-label">Click to choose a file</strong>
          <span>or drop a .pdf / .docx here</span>
        </label>
        <input type="file" id="resume-file-input" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" style="display:none;">
        <div style="margin-top: 12px; display: flex; gap: 8px; align-items: center;">
          <button class="btn primary" id="parse-resume-btn" onclick="parseUploadedResume(this)" disabled>Parse &amp; Save</button>
          <span id="upload-status" style="font-size: 12px; color: #555;"></span>
        </div>
        <details style="margin-top:14px;font-size:12px;color:#666;">
          <summary style="cursor:pointer;">What happens?</summary>
          <ol style="margin:6px 0 0 18px;padding:0;line-height:1.6;">
            <li>Your browser reads the file locally (it never leaves your computer raw).</li>
            <li>The extracted text is sent to the Cloudflare Worker.</li>
            <li>Claude converts it to structured JSON, saved as a new version.</li>
            <li>The new version becomes active immediately.</li>
          </ol>
        </details>
      </div>

      <div class="tab-panel" id="tab-versions">
        <p style="font-size:13px;color:#555;margin-bottom:10px;">Older versions remain saved. Click <em>Activate</em> to switch which one the AI uses.</p>
        <div id="versions-list"><p style="font-size:12px;color:#888;">Loading versions…</p></div>
      </div>

      <div class="tab-panel" id="tab-json">
        <p style="font-size:13px;color:#555;margin-bottom:8px;">Advanced: paste structured JSON directly. Saving creates a new version.</p>
        <textarea id="resume-text" spellcheck="false" style="width:100%; height:300px; font-family: ui-monospace, Menlo, monospace; font-size: 12px; padding: 10px; border: 1px solid #ddd; border-radius: 6px; resize: vertical;"></textarea>
        <div style="margin-top: 12px; display: flex; gap: 8px; align-items: center;">
          <button class="btn primary" onclick="saveResume(this)">Save resume</button>
          <span id="resume-save-status" style="font-size: 12px; color: #555;"></span>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="modal-overlay" id="prep-modal" onclick="if(event.target===this)closeModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeModal()">&times;</span>
    <h3 id="prep-modal-title">Prep this application</h3>
    <p id="prep-status" class="prep-status">Generating tailored materials with Claude…</p>
    <div id="prep-output" style="display:none;">
      <div class="prep-section">
        <div class="prep-label">Resume Summary</div>
        <pre id="prep-summary" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-summary', this)">Copy summary</button>
      </div>
      <div class="prep-section">
        <div class="prep-label">Cover Letter</div>
        <pre id="prep-cover" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-cover', this)">Copy cover letter</button>
      </div>
      <div class="prep-section">
        <div class="prep-label">LinkedIn Intro</div>
        <pre id="prep-linkedin" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-linkedin', this)">Copy LinkedIn intro</button>
      </div>
    </div>
  </div>
</div>

<script>
let activeWindow = 'all';

// --- Tracker state (localStorage) -----------------------------------------
const STATUS_CYCLE = ['', 'applied', 'phonescreen', 'onsite', 'offer', 'rejected'];
const STATUS_LABEL = {{
  '': 'Mark Applied',
  'applied': 'Applied ✓',
  'phonescreen': 'Phone Screen',
  'onsite': 'Onsite',
  'offer': 'Offer',
  'rejected': 'Rejected'
}};

function getTracker() {{
  try {{ return JSON.parse(localStorage.getItem('htj_tracker') || '{{}}'); }}
  catch(e) {{ return {{}}; }}
}}
function saveTracker(t) {{ localStorage.setItem('htj_tracker', JSON.stringify(t)); }}

function getStatus(fp) {{ return getTracker()[fp]?.status || ''; }}

function cycleStatus(fp, btn) {{
  const t = getTracker();
  const cur = t[fp]?.status || '';
  const next = STATUS_CYCLE[(STATUS_CYCLE.indexOf(cur) + 1) % STATUS_CYCLE.length];
  if (next === '') {{
    delete t[fp];
  }} else {{
    t[fp] = {{ status: next, updated: new Date().toISOString() }};
  }}
  saveTracker(t);
  refreshTrackerUI();
  filter();
}}

function refreshTrackerUI() {{
  const tracker = getTracker();
  document.querySelectorAll('.card').forEach(card => {{
    const fp = card.dataset.fp;
    const st = tracker[fp]?.status || '';
    card.dataset.status = st;
    const btn = card.querySelector('.btn.track');
    if (btn) {{
      btn.className = 'btn track ' + st;
      btn.textContent = STATUS_LABEL[st];
    }}
    // Update badges to include tracker status
    const badges = card.querySelector('[data-badges]');
    if (badges) {{
      // Remove old tracker badges
      badges.querySelectorAll('.b.tracker').forEach(b => b.remove());
      if (st) {{
        const span = document.createElement('span');
        span.className = 'b tracker ' + st;
        span.textContent = STATUS_LABEL[st];
        badges.appendChild(document.createTextNode(' '));
        badges.appendChild(span);
      }}
    }}
  }});
  updateTrackerStats();
}}

function updateTrackerStats() {{
  const t = getTracker();
  const counts = {{ applied: 0, phonescreen: 0, onsite: 0, offer: 0, rejected: 0 }};
  Object.values(t).forEach(v => {{ if (counts[v.status] !== undefined) counts[v.status]++; }});
  // Update each per-status counter
  for (const k of Object.keys(counts)) {{
    const el = document.getElementById('cnt-' + k);
    if (el) el.textContent = counts[k];
  }}
  // Response rate: any status past 'applied' counts as a response (incl. rejection)
  const totalApplied = counts.applied + counts.phonescreen + counts.onsite + counts.offer + counts.rejected;
  const responses = counts.phonescreen + counts.onsite + counts.offer + counts.rejected;
  const respEl = document.getElementById('cnt-response');
  if (respEl) {{
    respEl.textContent = totalApplied === 0 ? '--' : Math.round(100 * responses / totalApplied) + '%';
  }}
  // Legacy counter (unused but kept in case anything references it)
  const legacy = document.getElementById('apps-counter');
  if (legacy) legacy.textContent = counts.applied + counts.phonescreen + counts.onsite + counts.offer;
}}

// --- View mode toggle ---------------------------------------------------
let viewMode = localStorage.getItem('htj_view') || 'all';

function setView(mode) {{
  viewMode = mode;
  localStorage.setItem('htj_view', mode);
  document.body.classList.toggle('apps-mode', mode === 'apps');
  const allBtn = document.getElementById('view-all');
  const appsBtn = document.getElementById('view-apps');
  if (allBtn) allBtn.classList.toggle('active', mode === 'all');
  if (appsBtn) appsBtn.classList.toggle('active', mode === 'apps');
  filter();
}}

// --- Sorting ------------------------------------------------------------
function sortCards() {{
  const sel = document.getElementById('sortBy');
  if (!sel) return;
  const by = sel.value || 'score';
  const grid = document.getElementById('grid');
  const cards = Array.from(grid.querySelectorAll('.card'));
  cards.sort((a, b) => {{
    if (by === 'salary') {{
      return (parseInt(b.dataset.salaryMax || '0', 10)) - (parseInt(a.dataset.salaryMax || '0', 10));
    }}
    if (by === 'recent') {{
      return (b.dataset.lastSeen || '').localeCompare(a.dataset.lastSeen || '');
    }}
    if (by === 'ghost') {{
      // First-seen most recent first (i.e., newest job listings)
      return (b.dataset.firstSeen || '').localeCompare(a.dataset.firstSeen || '');
    }}
    // score (default)
    return (parseInt(b.dataset.score || '0', 10)) - (parseInt(a.dataset.score || '0', 10));
  }});
  cards.forEach(c => grid.appendChild(c));
}}

// --- Filtering ----------------------------------------------------------
function setWindow(btn, w) {{
  activeWindow = w;
  document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  filter();
}}
function filter() {{
  const q = document.getElementById('q').value.toLowerCase();
  const flt = document.getElementById('srOnly').value;
  const trk = document.getElementById('trackedFilter').value;
  const sal = document.getElementById('salaryFilter')?.value || '';
  const tracker = getTracker();
  const cards = Array.from(document.querySelectorAll('.card'));
  let shown = 0;
  cards.forEach(c => {{
    const text = c.innerText.toLowerCase();
    const senior = c.dataset.senior === '1';
    const remote = c.dataset.remote === '1';
    const days = parseInt(c.dataset.listedDays || '9999', 10);
    const salaryMax = parseInt(c.dataset.salaryMax || '0', 10);
    const st = tracker[c.dataset.fp]?.status || '';
    let show = text.includes(q);
    if (viewMode === 'apps' && !st) show = false;
    if (flt === 'srOnly' && !(senior && remote)) show = false;
    if (flt === 'sOnly' && !senior) show = false;
    if (flt === 'rOnly' && !remote) show = false;
    if (activeWindow !== 'all') {{
      const maxDays = parseInt(activeWindow, 10);
      if (days > maxDays) show = false;
    }}
    if (trk === 'untouched' && st) show = false;
    else if (trk && trk !== 'untouched' && st !== trk) show = false;
    if (sal === 'listed' && salaryMax === 0) show = false;
    else if (sal && sal !== 'listed' && salaryMax < parseInt(sal, 10)) show = false;
    c.style.display = show ? '' : 'none';
    if (show) shown++;
  }});
  const counter = document.getElementById('shown-counter');
  if (counter) counter.textContent = shown;
}}

// --- Resume editor (Cloudflare Worker + KV) -----------------------------
const WORKER_BASE = 'https://cool-darkness-dce5.tr6jz6v7wg.workers.dev';
const RESUME_WORKER_URL = WORKER_BASE + '/resume';
const VERSIONS_WORKER_URL = WORKER_BASE + '/resume-versions';
const PARSE_RESUME_WORKER_URL = WORKER_BASE + '/parse-resume';

// pdf.js worker path (must be set once before parsing PDFs)
if (window.pdfjsLib) {{
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}}

let _pendingUploadFile = null;

function getEditKey(promptMsg) {{
  let editKey = localStorage.getItem('htj_resume_key');
  if (!editKey) {{
    editKey = prompt(promptMsg || 'Enter the resume edit key (set as RESUME_EDIT_KEY secret in the Cloudflare Worker):');
    if (!editKey) return null;
    localStorage.setItem('htj_resume_key', editKey);
  }}
  return editKey;
}}

function setResumeTab(name) {{
  document.querySelectorAll('#resume-editor .tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('#resume-editor .tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + name));
  if (name === 'versions') loadVersions();
}}

async function openResumeModal() {{
  const modal = document.getElementById('resume-modal');
  const statusEl = document.getElementById('resume-status');
  const editor = document.getElementById('resume-editor');
  const textarea = document.getElementById('resume-text');
  document.getElementById('resume-save-status').textContent = '';
  document.getElementById('upload-status').textContent = '';
  document.getElementById('dropzone-label').textContent = 'Click to choose a file';
  document.getElementById('parse-resume-btn').disabled = true;
  _pendingUploadFile = null;
  statusEl.className = 'prep-status';
  statusEl.textContent = 'Loading…';
  statusEl.style.display = 'block';
  editor.style.display = 'none';
  modal.classList.add('show');
  try {{
    const r = await fetch(RESUME_WORKER_URL);
    const data = await r.json();
    if (data.error) {{
      statusEl.className = 'prep-status error';
      statusEl.textContent = 'Error loading resume: ' + data.error;
      return;
    }}
    textarea.value = data.resume || '';
    statusEl.style.display = 'none';
    editor.style.display = 'block';
    setResumeTab('upload');
    if (!data.resume) {{
      document.getElementById('upload-status').textContent = 'No resume saved yet — upload one to begin.';
    }}
  }} catch (e) {{
    statusEl.className = 'prep-status error';
    statusEl.textContent = 'Error loading resume: ' + (e.message || e);
  }}
}}

function closeResumeModal() {{
  document.getElementById('resume-modal').classList.remove('show');
}}

// --- File upload + browser-side text extraction -----------------------
function _wireResumeDropzone() {{
  const dz = document.getElementById('resume-dropzone');
  const input = document.getElementById('resume-file-input');
  if (!dz || !input || dz._wired) return;
  dz._wired = true;
  input.addEventListener('change', (e) => {{
    if (e.target.files && e.target.files[0]) _handleFileChosen(e.target.files[0]);
  }});
  ['dragover','dragenter'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.add('drag'); }}));
  ['dragleave','drop'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.remove('drag'); }}));
  dz.addEventListener('drop', (e) => {{
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) _handleFileChosen(e.dataTransfer.files[0]);
  }});
}}

function _handleFileChosen(file) {{
  const name = (file.name || '').toLowerCase();
  if (!name.endsWith('.pdf') && !name.endsWith('.docx')) {{
    document.getElementById('upload-status').textContent = 'Unsupported file. Use .pdf or .docx.';
    return;
  }}
  _pendingUploadFile = file;
  document.getElementById('dropzone-label').textContent = file.name;
  document.getElementById('parse-resume-btn').disabled = false;
  document.getElementById('upload-status').textContent = 'Ready. Click Parse & Save.';
}}

async function _extractText(file) {{
  const name = (file.name || '').toLowerCase();
  if (name.endsWith('.docx')) {{
    const buf = await file.arrayBuffer();
    const res = await window.mammoth.extractRawText({{ arrayBuffer: buf }});
    return (res && res.value || '').trim();
  }}
  if (name.endsWith('.pdf')) {{
    if (!window.pdfjsLib) throw new Error('PDF parser failed to load.');
    const buf = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({{ data: buf }}).promise;
    let out = '';
    for (let i = 1; i <= pdf.numPages; i++) {{
      const page = await pdf.getPage(i);
      const tc = await page.getTextContent();
      out += tc.items.map(it => it.str).join(' ') + '\\n\\n';
    }}
    return out.trim();
  }}
  throw new Error('Unsupported file type.');
}}

async function parseUploadedResume(btn) {{
  if (!_pendingUploadFile) return;
  const statusEl = document.getElementById('upload-status');
  const editKey = getEditKey();
  if (!editKey) return;
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Reading file…';
  statusEl.textContent = '';
  try {{
    const text = await _extractText(_pendingUploadFile);
    if (!text || text.length < 80) {{
      statusEl.textContent = 'Could not extract text from this file. Try saving as .docx, or use Edit JSON tab.';
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    btn.textContent = 'Parsing with Claude…';
    const r = await fetch(PARSE_RESUME_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify({{ text, filename: _pendingUploadFile.name }}),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) localStorage.removeItem('htj_resume_key');
      statusEl.textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    statusEl.textContent = 'Saved as new version (' + (data.version && data.version.label || 'new') + ') and activated.';
    if (data.parsed) {{
      const ta = document.getElementById('resume-text');
      if (ta) ta.value = JSON.stringify(data.parsed, null, 2);
    }}
    btn.textContent = orig;
    btn.disabled = false;
    _pendingUploadFile = null;
    document.getElementById('resume-file-input').value = '';
    document.getElementById('dropzone-label').textContent = 'Upload another to replace';
  }} catch (e) {{
    statusEl.textContent = 'Failed: ' + (e.message || e);
    btn.textContent = orig;
    btn.disabled = false;
  }}
}}

// --- Versions list ------------------------------------------------------
async function loadVersions() {{
  const list = document.getElementById('versions-list');
  list.innerHTML = '<p style="font-size:12px;color:#888;">Loading versions…</p>';
  try {{
    const r = await fetch(VERSIONS_WORKER_URL);
    const data = await r.json();
    if (data.error) {{
      list.innerHTML = '<p style="font-size:12px;color:#b00;">Error: ' + data.error + '</p>';
      return;
    }}
    const versions = data.versions || [];
    const activeId = data.activeId;
    if (!versions.length) {{
      list.innerHTML = '<p style="font-size:12px;color:#888;">No versions yet. Upload a file or paste JSON to create one.</p>';
      return;
    }}
    list.innerHTML = versions.map(v => {{
      const isActive = v.id === activeId;
      const dt = new Date(v.savedAt);
      const when = isNaN(dt) ? v.savedAt : dt.toLocaleString();
      const src = v.sourceType === 'upload' ? 'uploaded' : 'JSON paste';
      return '<div class="version-row' + (isActive ? ' active' : '') + '">' +
             '<div class="version-main">' +
             '<div class="version-label">' + _esc(v.label) + (isActive ? ' <span class="version-badge">Active</span>' : '') + '</div>' +
             '<div class="version-meta">' + src + ' · ' + when + '</div>' +
             '</div>' +
             '<div class="version-actions">' +
             (isActive ? '' : '<button class="v-btn primary" onclick="activateVersion(\\''+ v.id +'\\')">Activate</button>') +
             '<button class="v-btn" onclick="previewVersion(\\''+ v.id +'\\')">Preview</button>' +
             '<button class="v-btn" onclick="renameVersion(\\''+ v.id +'\\', \\''+ _esc(v.label).replace(/'/g,"\\\\'") +'\\')">Rename</button>' +
             (isActive ? '' : '<button class="v-btn danger" onclick="deleteVersion(\\''+ v.id +'\\')">Delete</button>') +
             '</div></div>';
    }}).join('');
  }} catch (e) {{
    list.innerHTML = '<p style="font-size:12px;color:#b00;">Error: ' + (e.message || e) + '</p>';
  }}
}}

function _esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}

async function _versionAction(action, body) {{
  const editKey = getEditKey();
  if (!editKey) return null;
  const r = await fetch(VERSIONS_WORKER_URL, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    body: JSON.stringify(body),
  }});
  const data = await r.json().catch(() => ({{}}));
  if (!r.ok || data.error) {{
    if (r.status === 401) localStorage.removeItem('htj_resume_key');
    alert('Failed: ' + (data.error || ('HTTP ' + r.status)));
    return null;
  }}
  return data;
}}

async function activateVersion(id) {{
  const data = await _versionAction('activate', {{ action: 'activate', id }});
  if (data) loadVersions();
}}

async function deleteVersion(id) {{
  if (!confirm('Delete this version? This cannot be undone.')) return;
  const data = await _versionAction('delete', {{ action: 'delete', id }});
  if (data) loadVersions();
}}

async function previewVersion(id) {{
  const editKey = getEditKey();
  if (!editKey) return;
  const r = await fetch(VERSIONS_WORKER_URL, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    body: JSON.stringify({{ action: 'get', id }}),
  }});
  const data = await r.json().catch(() => ({{}}));
  if (!r.ok || data.error) {{ alert('Failed: ' + (data.error || ('HTTP ' + r.status))); return; }}
  setResumeTab('json');
  const ta = document.getElementById('resume-text');
  if (ta) ta.value = data.resume || '';
  document.getElementById('resume-save-status').textContent = 'Previewing version. Save to create a new version from this content.';
}}

async function renameVersion(id, currentLabel) {{
  const label = prompt('New label for this version:', currentLabel || '');
  if (label == null) return;
  const data = await _versionAction('rename', {{ action: 'rename', id, label }});
  if (data) loadVersions();
}}

async function saveResume(btn) {{
  const textarea = document.getElementById('resume-text');
  const statusEl = document.getElementById('resume-save-status');
  const value = textarea.value.trim();
  if (!value) {{
    statusEl.textContent = 'Resume is empty — paste content first.';
    return;
  }}
  // Light validation: should be JSON with a personal section
  try {{
    const parsed = JSON.parse(value);
    if (!parsed.personal) throw new Error('Resume JSON should include a "personal" key.');
  }} catch (e) {{
    if (!confirm('This does not look like valid resume JSON (' + e.message + '). Save anyway?')) return;
  }}
  const editKey = getEditKey();
  if (!editKey) return;
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = 'Saving…';
  statusEl.textContent = '';
  try {{
    const label = prompt('Label this version (e.g. "Hand-edited – Apr 14"):', '') || 'JSON edit';
    const r = await fetch(RESUME_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify({{ resume: value, label, sourceType: 'json-paste' }}),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) localStorage.removeItem('htj_resume_key');
      statusEl.textContent = 'Save failed: ' + (data.error || ('HTTP ' + r.status));
      btn.disabled = false;
      btn.textContent = orig;
      return;
    }}
    statusEl.textContent = 'Saved as new version.';
    btn.textContent = orig;
    btn.disabled = false;
  }} catch (e) {{
    statusEl.textContent = 'Save failed: ' + (e.message || e);
    btn.disabled = false;
    btn.textContent = orig;
  }}
}}

// Wire dropzone after DOM is ready
if (document.readyState !== 'loading') _wireResumeDropzone();
else document.addEventListener('DOMContentLoaded', _wireResumeDropzone);

// --- Refresh data (triggers GitHub Action via Cloudflare Worker) --------
const REFRESH_WORKER_URL = 'https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/refresh';

async function refreshData() {{
  const btn = document.getElementById('refresh-btn');
  if (!btn) return;
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Triggering refresh…';
  try {{
    const r = await fetch(REFRESH_WORKER_URL, {{ method: 'POST' }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      btn.textContent = 'Refresh failed';
      alert('Refresh failed: ' + (data.error || ('HTTP ' + r.status)) + (data.details ? '\\n' + data.details : ''));
      setTimeout(() => {{ btn.textContent = original; btn.disabled = false; }}, 3000);
      return;
    }}
  }} catch (e) {{
    btn.textContent = 'Refresh failed';
    alert('Refresh failed: ' + (e.message || e));
    setTimeout(() => {{ btn.textContent = original; btn.disabled = false; }}, 3000);
    return;
  }}
  // Countdown then reload
  let secs = 150;
  const tick = () => {{
    btn.textContent = `Fetching jobs… ${{secs}}s, page will reload`;
    secs--;
    if (secs <= 0) {{
      window.location.reload();
    }} else {{
      setTimeout(tick, 1000);
    }}
  }};
  tick();
}}

// --- Prep modal (calls Cloudflare Worker for AI generation) -------------
const PREP_WORKER_URL = 'https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/prep';

async function prepApplication(fp, btn) {{
  const card = btn.closest('.card');
  const titleEl = card.querySelector('.title a');
  const jobTitle = (titleEl?.textContent || '').trim();
  const company = (card.querySelector('.company')?.textContent || '').trim();
  const jobUrl = titleEl?.href || '';
  const jobDescription = (card.querySelector('.desc')?.textContent || '').trim();

  const modal = document.getElementById('prep-modal');
  const statusEl = document.getElementById('prep-status');
  const outputEl = document.getElementById('prep-output');
  const titleH = document.getElementById('prep-modal-title');

  titleH.textContent = `Materials for ${{jobTitle}} @ ${{company}}`;
  statusEl.className = 'prep-status';
  statusEl.textContent = 'Generating with Claude… this takes 10–30 seconds.';
  statusEl.style.display = 'block';
  outputEl.style.display = 'none';
  modal.classList.add('show');

  try {{
    const r = await fetch(PREP_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ jobTitle, company, jobDescription, jobUrl }}),
    }});
    const data = await r.json();
    if (!r.ok || data.error) {{
      statusEl.className = 'prep-status error';
      statusEl.textContent = `Error: ${{data.error || ('HTTP ' + r.status)}}${{data.details ? ' — ' + data.details : ''}}`;
      return;
    }}
    document.getElementById('prep-summary').textContent = data.summary || '(no summary returned)';
    document.getElementById('prep-cover').textContent = data.coverLetter || '(no cover letter returned)';
    document.getElementById('prep-linkedin').textContent = data.linkedin || '(no LinkedIn intro returned)';
    statusEl.style.display = 'none';
    outputEl.style.display = 'block';
  }} catch (e) {{
    statusEl.className = 'prep-status error';
    statusEl.textContent = `Error: ${{e.message || e}}`;
  }}
}}
function closeModal() {{ document.getElementById('prep-modal').classList.remove('show'); }}
function copyPrepField(id, btn) {{
  const txt = document.getElementById(id).textContent;
  navigator.clipboard.writeText(txt).then(() => {{
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }});
}}

// init
refreshTrackerUI();
setView(viewMode);
</script>
</body></html>"""


if __name__ == "__main__":
    run()
