"""SQLite storage layer + company industries.

Extracted from fetch_jobs.py 2026-05-28 (Phase 5).
"""
import json
import os
import re
import sqlite3
from hashlib import sha256
from datetime import datetime, timezone

from matcher.scoring import is_remote, is_senior, score_job

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "jobs.db")
COMPANIES_PATH = os.path.join(ROOT, "companies.json")

# Safe module-level defaults; _build_company_industries() reassigns these from companies.json.
COMPANY_INDUSTRIES = {}
DEFAULT_INDUSTRIES = ["healthcare", "digital-health"]

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
            # Migration: add employment_type column
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN employment_type TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass
            # Migration: add industries column (comma-separated)
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN industries TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass
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
    # Lazy import: detect_employment_type lives in fetch_jobs (needs its marker tables);
    # top-level import would be circular since fetch_jobs imports storage.db.
    from fetch_jobs import detect_employment_type
    fp = fingerprint(job)
    now = datetime.now(timezone.utc).isoformat()
    remote = 1 if is_remote(job) else 0
    senior = 1 if is_senior(job) else 0
    score = score_job(job)

    salary = job.get("salary_range") or ""
    employment_type = detect_employment_type(job)
    # Industries: looked up from COMPANY_INDUSTRIES based on company_slug (lowercased)
    industries = COMPANY_INDUSTRIES.get((job.get("company_slug") or "").lower(), DEFAULT_INDUSTRIES)
    industries_str = ",".join(industries) if industries else ""
    cur = conn.execute("SELECT fingerprint, sightings FROM jobs WHERE fingerprint=?", (fp,))
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE jobs SET last_seen=?, sightings=sightings+1, score=?, remote=?, senior=?, salary_range=?, employment_type=?, industries=? WHERE fingerprint=?",
            (now, score, remote, senior, salary, employment_type, industries_str, fp),
        )
    else:
        conn.execute(
            """INSERT INTO jobs (fingerprint, source, company_slug, company_name, external_id,
               title, location, url, posted_at, description, first_seen, last_seen,
               sightings, remote, senior, score, salary_range, employment_type, industries)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?)""",
            (fp, job["source"], job["company_slug"], job["company_name"], job["external_id"],
             job["title"], job["location"], job["url"], job["posted_at"], job["description"],
             now, now, remote, senior, score, salary, employment_type, industries_str),
        )


# Keep STOP_WORDS and _normalize_title byte-identical to fetch_jobs.py —
# fingerprints must stay stable or every existing job re-inserts as a duplicate.
# (Was missed in the 2026-05-28 Phase 5 extraction: fingerprint() referenced
# _normalize_title which stayed behind in fetch_jobs.py → NameError on every
# upsert → zero jobs ingested since 2026-05-28.)
STOP_WORDS = {"of", "the", "and", "for", "a", "an", "to", "with", "in", "on", "at", "by", "or"}


def _normalize_title(title):
    """Lowercase, strip stop words, then concatenate alphanumerics so minor wording
    differences ('Director of Product' vs 'Director, Product') collapse to the same hash."""
    words = re.split(r"[^a-z0-9]+", (title or "").lower())
    return "".join(w for w in words if w and w not in STOP_WORDS)


def fingerprint(job):
    """Stable hash so the same role across reposts/sources dedupes."""
    base = f"{job['company_slug']}|{_normalize_title(job['title'])}|{re.sub(r'[^a-z0-9]+', '', (job['location'] or '').lower())}"
    return sha256(base.encode()).hexdigest()[:16]


def _build_company_industries(companies):
    """Populate COMPANY_INDUSTRIES from companies.json.
    Each entry can be a slug string (uses _default_industries) or {slug, industries}."""
    global COMPANY_INDUSTRIES, DEFAULT_INDUSTRIES
    defaults = companies.get("_default_industries")
    if defaults:
        DEFAULT_INDUSTRIES = defaults
    mapping = {}
    for source in ("greenhouse", "lever", "ashby"):
        for entry in companies.get(source, []):
            if isinstance(entry, str):
                mapping[entry.lower()] = DEFAULT_INDUSTRIES
            elif isinstance(entry, dict) and entry.get("slug"):
                mapping[entry["slug"].lower()] = entry.get("industries", DEFAULT_INDUSTRIES)
    for entry in companies.get("workday", []):
        if isinstance(entry, dict):
            key = (entry.get("tenant") or entry.get("name", "")).lower()
            if key:
                mapping[key] = entry.get("industries", DEFAULT_INDUSTRIES)
    for entry in companies.get("wttj", []):
        if isinstance(entry, dict):
            key = (entry.get("slug") or entry.get("name", "")).lower()
            if key:
                mapping[key] = entry.get("industries", DEFAULT_INDUSTRIES)
    COMPANY_INDUSTRIES = mapping
    print(f"[industries] mapped {len(mapping)} companies; default={DEFAULT_INDUSTRIES}", flush=True)


def _slugify_company_name(name):
    """Lowercase, drop non-alphanumerics — best-effort guess at the ATS slug from a company name."""
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


