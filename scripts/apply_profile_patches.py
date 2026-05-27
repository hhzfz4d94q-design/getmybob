"""Apply one-off patches to skills_profile records.

Reads every JSON file under scripts/profile_patches/<slug>.json and POSTs
the `patchFields` object to /skills-profile?user=<slug> with X-Admin-Key.

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

def post(url, headers, body_bytes):
    headers = dict(headers)
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; getmemyjob-patch/1.0)")
    req = urllib.request.Request(url, method="POST", headers=headers, data=body_bytes)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"

def main():
    files = sorted(glob.glob(os.path.join(PATCH_DIR, "*.json")))
    if not files:
        print("No patch files found in", PATCH_DIR)
        return 1
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
        body = json.dumps({"patchFields": patch}).encode("utf-8")
        url = f"{WORKER_URL}/skills-profile?user={slug}"
        status, text = post(url, {"X-Admin-Key": ADMIN_KEY}, body)
        ok = 200 <= status < 300
        overall_ok &= ok
        # Try to summarize new values
        summary = ""
        try:
            resp = json.loads(text)
            prof = resp.get("profile") or {}
            summary = (
                f"seniorityLevel={prof.get('seniorityLevel')!r} · "
                f"targetTitles={len(prof.get('targetTitles') or [])} · "
                f"industries={len(prof.get('industries') or [])} · "
                f"specialties={len(prof.get('specialties') or [])}"
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
