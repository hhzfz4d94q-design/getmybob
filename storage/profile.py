"""User profile + slug loading.

Extracted from fetch_jobs.py 2026-05-28 (Phase 5).
"""
import json
import os
import urllib.parse
import urllib.request
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_JSON_PATH = os.path.join(ROOT, "users.json")
WORKER_BASE_URL = "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev"


def load_skills_profile(slug="geetu"):
    """Fetch the AI-generated skills profile for a specific user from the Worker.
    Returns None on failure — scoring falls back to legacy hardcoded keywords."""
    try:
        url = WORKER_BASE_URL + "/skills-profile?user=" + slug
        req = Request(url, headers={"User-Agent": "fetch_jobs.py"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        profile = data.get("profile")
        if not profile or not isinstance(profile, dict):
            return None
        for k in ("keywords", "seniorityTitles", "industries", "negativeKeywords"):
            if isinstance(profile.get(k), list):
                profile[k] = [str(x).lower().strip() for x in profile[k] if x]
            else:
                profile[k] = []
        return profile
    except Exception as e:
        print(f"[skills-profile:{slug}] could not load: {e}", flush=True)
        return None


def load_users():
    """Fetch user list from Worker /users endpoint. Falls back to users.json on failure,
    then to a hardcoded default. The Worker is the canonical registry."""
    # Primary: Worker /users
    try:
        req = Request(WORKER_BASE_URL + "/users", headers={"User-Agent": "fetch_jobs.py"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        users = data.get("users", [])
        if isinstance(users, list) and users:
            print(f"[users] loaded {len(users)} from Worker", flush=True)
            return users
    except Exception as e:
        print(f"[users] Worker fetch failed ({e}), falling back to users.json", flush=True)

    # Fallback: users.json (legacy)
    try:
        with open(USERS_JSON_PATH) as f:
            users = json.load(f)
        if isinstance(users, list) and users:
            return users
    except Exception:
        pass

    # Last resort
    print("[users] using hardcoded default (geetu)", flush=True)
    return [{"slug": "geetu", "name": "Geetanjali Arora"}]


def _careers_root(url):
    """Derive the careers landing page for a job's ATS from its full URL.
    Returns a URL pointing to all jobs at that company on that ATS, or None.
    Used in the dashboard card as a fallback link in case the specific job
    listing has been removed."""
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        host = (p.netloc or "").lower()
        path = (p.path or "/")
        if "myworkdayjobs.com" in host:
            parts = [seg for seg in path.split("/") if seg]
            if parts:
                return f"https://{host}/{parts[0]}"
            return f"https://{host}/"
        if "boards.greenhouse.io" in host or "job-boards.greenhouse.io" in host:
            parts = [seg for seg in path.split("/") if seg]
            if parts:
                return f"https://{host}/{parts[0]}"
            return f"https://{host}/"
        if "jobs.lever.co" in host:
            parts = [seg for seg in path.split("/") if seg]
            if parts:
                return f"https://{host}/{parts[0]}"
            return f"https://{host}/"
        if "jobs.ashbyhq.com" in host:
            parts = [seg for seg in path.split("/") if seg]
            if parts:
                return f"https://{host}/{parts[0]}"
            return f"https://{host}/"
    except Exception:
        return None
    return None


