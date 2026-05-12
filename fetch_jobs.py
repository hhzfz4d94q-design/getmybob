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
        })
    return out


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
        })
    return out


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


def fingerprint(job):
    """Stable hash so the same role across reposts/sources dedupes."""
    base = f"{job['company_slug']}|{re.sub(r'[^a-z0-9]+', '', (job['title'] or '').lower())}|{re.sub(r'[^a-z0-9]+', '', (job['location'] or '').lower())}"
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
    score INTEGER
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

    cur = conn.execute("SELECT fingerprint, sightings FROM jobs WHERE fingerprint=?", (fp,))
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE jobs SET last_seen=?, sightings=sightings+1, score=?, remote=?, senior=? WHERE fingerprint=?",
            (now, score, remote, senior, fp),
        )
    else:
        conn.execute(
            """INSERT INTO jobs (fingerprint, source, company_slug, company_name, external_id,
               title, location, url, posted_at, description, first_seen, last_seen,
               sightings, remote, senior, score)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?)""",
            (fp, job["source"], job["company_slug"], job["company_name"], job["external_id"],
             job["title"], job["location"], job["url"], job["posted_at"], job["description"],
             now, now, remote, senior, score),
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


def generate_dashboard(conn):
    rows = conn.execute("""
        SELECT fingerprint, company_name, title, location, url, posted_at, first_seen, last_seen,
               sightings, remote, senior, score, description
        FROM jobs
        WHERE last_seen >= datetime('now', '-30 days')
        ORDER BY score DESC, last_seen DESC
        LIMIT 1000
    """).fetchall()

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
         sightings, remote, senior, score, desc) = r
        # "Listed" age — prefer the source's posted_at, fall back to first_seen
        listed_days = _days_old(posted_at) if posted_at else None
        if listed_days is None:
            listed_days = _days_old(first_seen) or 0
        ghost_flag = listed_days is not None and listed_days > GHOST_DAYS
        badges = []
        if senior: badges.append('<span class="b senior">Senior</span>')
        if remote: badges.append('<span class="b remote">Remote</span>')
        if listed_days == 0: badges.append('<span class="b fresh">New today</span>')
        elif listed_days is not None and listed_days <= 7: badges.append('<span class="b week">This week</span>')
        if ghost_flag: badges.append(f'<span class="b ghost">Ghost? {listed_days}d</span>')
        if sightings > 3: badges.append(f'<span class="b repost">Seen {sightings}×</span>')
        badge_html = " ".join(badges)

        cards.append(f"""
        <div class="card" data-fp="{fp}" data-score="{score}" data-senior="{senior}" data-remote="{remote}" data-listed-days="{listed_days if listed_days is not None else 9999}">
          <div class="row1">
            <div class="title"><a href="{url}" target="_blank">{_esc(title)}</a></div>
            <div class="score">{score}</div>
          </div>
          <div class="row2">
            <span class="company">{_esc(company)}</span> ·
            <span class="loc">{_esc(loc or 'Location N/A')}</span> ·
            <span class="age">{listed_days}d old</span>
          </div>
          <div class="badges" data-badges>{badge_html}</div>
          <div class="desc">{_esc(desc[:300])}…</div>
          <div class="actions">
            <button class="btn primary" onclick="showPrepCmd('{fp}', this)">Prep Application</button>
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
  header {{ background: #1f3a5f; color: white; padding: 18px 28px; }}
  header h1 {{ margin: 0; font-size: 20px; }}
  header .sub {{ opacity: .85; font-size: 13px; margin-top: 4px; }}
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
  .desc {{ font-size: 12.5px; color: #444; margin-top: 6px; line-height: 1.4; }}
</style>
</head><body>
<header>
  <h1>HealthTech Jobs for Geetanjali</h1>
  <div class="sub">Senior leadership · Healthcare IT · Remote · Generated {generated}</div>
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

<div class="modal-overlay" id="prep-modal" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <span class="modal-close" onclick="closeModal()">&times;</span>
    <h3>Prep this application</h3>
    <p style="font-size:13px;color:#555;">Copy the command below, paste it into Terminal, and hit Enter. The AI will tailor Geetanjali's resume, draft a cover letter and LinkedIn intro, and open the apply page.</p>
    <pre id="prep-cmd"></pre>
    <button class="btn primary copy-btn" onclick="copyCmd()">Copy command</button>
    <p style="font-size:12px;color:#888;margin-top:14px;">First time? See <code>SETUP_AI_KEY.md</code> to add your Anthropic API key.</p>
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
  const tracker = getTracker();
  const cards = Array.from(document.querySelectorAll('.card'));
  let shown = 0;
  cards.forEach(c => {{
    const text = c.innerText.toLowerCase();
    const senior = c.dataset.senior === '1';
    const remote = c.dataset.remote === '1';
    const days = parseInt(c.dataset.listedDays || '9999', 10);
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
    c.style.display = show ? '' : 'none';
    if (show) shown++;
  }});
  const counter = document.getElementById('shown-counter');
  if (counter) counter.textContent = shown;
}}

// --- Prep modal ---------------------------------------------------------
function showPrepCmd(fp, btn) {{
  const cmd = `cd ~/Documents/Claude/Projects/"Ticky Sun"/healthtech-jobs && python3 prep_application.py --job ${{fp}}`;
  document.getElementById('prep-cmd').textContent = cmd;
  document.getElementById('prep-modal').classList.add('show');
}}
function closeModal() {{ document.getElementById('prep-modal').classList.remove('show'); }}
function copyCmd() {{
  const txt = document.getElementById('prep-cmd').textContent;
  navigator.clipboard.writeText(txt).then(() => {{
    const btn = document.querySelector('.modal .copy-btn');
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = orig, 1500);
  }});
}}

// init
refreshTrackerUI();
setView(viewMode);
</script>
</body></html>"""


if __name__ == "__main__":
    run()
