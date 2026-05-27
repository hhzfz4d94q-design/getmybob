"""Apply one-off patches to skills_profile records.

The /skills-profile POST endpoint only accepts X-Edit-Key (per-user secret),
not X-Admin-Key. So we do a two-step:
  1. GET /admin/users with X-Admin-Key → returns each user's editKey
  2. POST /skills-profile?user=<slug> with X-Edit-Key: <that user's key>

Reads every JSON file under scripts/profile_patches/<slug>.json and POSTs
its patchFields object.

Env: WORKER_URL, ADMIN_KEY (both required).
Writes a markdown report to reports/patch_<timestamp>.md.
"""
import json
import os
import sys
import glob
import urllib.request
import urllib.error
from datetime import datetime, timezone

WORKER_URL = os.environ.get("WORKER_URL", "").rstrip("/")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
if not WORKER_URL or not ADMIN_KEY:
    print("ERROR: WORKER_URL and ADMIN_KEY required", file=sys.stderr)
    sys.exit(2)

PATCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile_patches")
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)


def http(url, method="GET", headers=None, body_bytes=None):
    headers = dict(headers or {})
    headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; getmemyjob-patch/1.1)")
    if body_bytes is not None:
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, method=method, headers=headers, data=body_bytes)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def fetch_edit_keys():
    """GET /admin/users → {slug: editKey} map."""
    status, text = http(f"{WORKER_URL}/admin/users", headers={"X-Admin-Key": ADMIN_KEY})
    if not (200 <= status < 300):
        print(f"FATAL: /admin/users returned HTTP {status}", file=sys.stderr)
        print(f"  body: {text[:300]}", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(text)
    except Exception as e:
        print(f"FATAL: /admin/users response not JSON: {e}", file=sys.stderr)
        sys.exit(2)
    users = data.get("users") or []
    out = {}
    for u in users:
        slug = u.get("slug")
        ek = u.get("editKey")
        if slug and ek:
            out[slug] = ek
    return out


def main():
    files = sorted(glob.glob(os.path.join(PATCH_DIR, "*.json")))
    if not files:
        print("No patch files found in", PATCH_DIR)
        return 1

    print(f"Loading edit keys via /admin/users …")
    edit_keys = fetch_edit_keys()
    print(f"  got edit keys for {len(edit_keys)} users: {sorted(edit_keys.keys())}")

    lines = [f"# Profile patch run {datetime.now(timezone.utc).isoformat()}", ""]
    overall_ok = True

    for path in files:
        slug = os.path.splitext(os.path.basename(path))[0]
        with open(path) as f:
            doc = json.load(f)
        patch = doc.get("patchFields")
        if not isinstance(patch, dict):
            print(f"[skip:{slug}] no patchFields in {path}")
            lines.append(f"- **{slug}** — skipped (no patchFields)")
            continue

        edit_key = edit_keys.get(slug)
        if not edit_key:
            print(f"[FAIL:{slug}] no edit_key in /admin/users response")
            lines.append(f"- **{slug}** — FAIL (no edit_key)")
            overall_ok = False
            continue

        body = json.dumps({"patchFields": patch}).encode("utf-8")
        url = f"{WORKER_URL}/skills-profile?user={slug}"
        status, text = http(url, method="POST",
                            headers={"X-Edit-Key": edit_key}, body_bytes=body)
        ok = 200 <= status < 300
        overall_ok &= ok
        summary = ""
        try:
            resp = json.loads(text)
            prof = resp.get("profile") or {}
            summary = (
                f"seniorityLevel={prof.get('seniorityLevel')!r} · "
                f"targetTitles={len(prof.get('targetTitles') or [])} · "
                f"industries={len(prof.get('industries') or [])} · "
                f"specialties={len(prof.get('specialties') or [])} · "
                f"keywords={len(prof.get('keywords') or [])}"
            )
        except Exception:
            summary = (text or "")[:200]
        marker = "OK" if ok else "FAIL"
        print(f"[{marker}:{slug}] HTTP {status} — {summary}")
        lines.append(f"- **{slug}** — HTTP {status} {marker}")
        lines.append(f"  - {summary}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = os.path.join(REPORT_DIR, f"patch_{stamp}.md")
    with open(report, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("Wrote", report)
    return 0 if overall_ok else 3


if __name__ == "__main__":
    sys.exit(main())
