"""Bulk profile regeneration.

Usage: python3 scripts/regen_profiles.py <slug-or-all>

Reads ADMIN_KEY and WORKER_URL from env. Loops users via the Worker's
/users endpoint (or just the one slug given), POSTs /regenerate-profile
for each, writes a markdown report to reports/regen_<timestamp>.md.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

WORKER_URL = os.environ.get("WORKER_URL", "").rstrip("/")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")

if not WORKER_URL or not ADMIN_KEY:
    print("ERROR: WORKER_URL and ADMIN_KEY env vars required", file=sys.stderr)
    sys.exit(2)

slug_arg = (sys.argv[1] if len(sys.argv) > 1 else "all").strip()


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; getmemyjob-regen/1.0; +https://getmemyjob.officebeatllc.com)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def http_post_json(url, headers):
    headers = dict(headers or {})
    headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; getmemyjob-regen/1.0; +https://getmemyjob.officebeatllc.com)")
    headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, method="POST", headers=headers, data=b"")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  [debug] HTTP {e.code} body[:500]: {body[:500]!r}", flush=True)
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body[:300] or f"HTTP {e.code} (empty body)"}
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {"error": f"{type(e).__name__}: {e}"}


# Figure out the slug list
if slug_arg == "all":
    try:
        data = http_get_json(f"{WORKER_URL}/users")
    except Exception as e:
        print(f"ERROR fetching /users: {e}", file=sys.stderr)
        sys.exit(3)
    raw_users = data.get("users") if isinstance(data, dict) else data
    if not isinstance(raw_users, list):
        raw_users = []
    slugs = [u.get("slug") for u in raw_users if isinstance(u, dict) and u.get("slug")]
else:
    slugs = [slug_arg]
print(f"Regen targets: {slugs}")

os.makedirs("reports", exist_ok=True)
report_path = f"reports/regen_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%MZ')}.md"
lines = []
lines.append("# Profile regeneration report")
lines.append("")
lines.append(f"Triggered: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}")
lines.append("")
lines.append("| User | targetCompanies | size pref | role | Status |")
lines.append("|---|---:|---|---|---|")

for s in slugs:
    print(f"\n→ regenerating {s}…", flush=True)
    code, resp = http_post_json(
        f"{WORKER_URL}/regenerate-profile?user={s}",
        {"X-Admin-Key": ADMIN_KEY, "Accept": "application/json"},
    )
    if code != 200:
        err = (resp or {}).get("error", f"HTTP {code}")
        print(f"  ✗ {s}: {err}")
        lines.append(f"| `{s}` | — | — | — | ✗ {err} |")
        continue
    profile = (resp or {}).get("profile") or {}
    tc = profile.get("targetCompanies") or []
    mix = profile.get("companySizeMix")
    prefs = profile.get("companySizePreferences") or []
    if isinstance(mix, dict):
        sp = f"{mix.get('startup',0)}/{mix.get('midsize',0)}/{mix.get('large',0)}"
    elif prefs:
        sp = ", ".join(prefs)
    else:
        sp = "default (no wizard pick)"
    role = (profile.get("primaryRole") or "?")[:60]
    print(f"  ✓ {s}: {len(tc)} targetCompanies, size={sp}")
    lines.append(f"| `{s}` | {len(tc)} | {sp} | {role} | ✓ |")

lines.append("")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"\nReport written to {report_path}")
