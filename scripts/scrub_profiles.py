"""Universal profile scrubber.

Walks every user in /admin/users and applies generic "best practice" cleanup:
- Trims keywords[] to 15 (matches wizard cap)
- Removes overly-aggressive negativeKeywords that cause silent kills:
  "assistant", "associate", "staff engineer", "staff", "analyst", "coordinator"
- (Optional --regen-companies) Calls /regenerate-companies so each user's
  targetCompanies aligns to their current bullseye

Env: WORKER_URL, ADMIN_KEY (required)
Args: optional --regen-companies flag

Writes a markdown report to reports/scrub_<timestamp>.md
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
    print("ERROR: WORKER_URL and ADMIN_KEY required", file=sys.stderr)
    sys.exit(2)

REGEN_COMPANIES = "--regen-companies" in sys.argv

REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# negativeKeywords that cause silent kills — they have legitimate senior variants
SCRUB_NEG = {"assistant", "associate", "staff engineer", "staff", "analyst", "coordinator"}

KEYWORDS_CAP = 15


def http(url, method="GET", headers=None, body_bytes=None, timeout=120):
    headers = dict(headers or {})
    headers.setdefault("User-Agent", "Mozilla/5.0 (compatible; getmemyjob-scrub/1.0)")
    if body_bytes is not None:
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, method=method, headers=headers, data=body_bytes)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def fetch_users():
    status, text = http(f"{WORKER_URL}/admin/users", headers={"X-Admin-Key": ADMIN_KEY})
    if not (200 <= status < 300):
        print(f"FATAL: /admin/users HTTP {status}: {text[:300]}", file=sys.stderr)
        sys.exit(2)
    return json.loads(text).get("users") or []


def fetch_profile(slug):
    status, text = http(f"{WORKER_URL}/skills-profile?user={slug}&_=cb{datetime.now().timestamp()}")
    if not (200 <= status < 300):
        return None
    try:
        return json.loads(text).get("profile") or {}
    except Exception:
        return None


def patch_profile(slug, edit_key, patch_fields):
    body = json.dumps({"patchFields": patch_fields}).encode("utf-8")
    return http(f"{WORKER_URL}/skills-profile?user={slug}",
                method="POST", headers={"X-Edit-Key": edit_key}, body_bytes=body)


def regen_companies(slug, edit_key):
    body = json.dumps({"dry_run": False}).encode("utf-8")
    return http(f"{WORKER_URL}/regenerate-companies?user={slug}",
                method="POST", headers={"X-Edit-Key": edit_key}, body_bytes=body, timeout=180)


def main():
    print(f"Scrubbing profiles (regen_companies={REGEN_COMPANIES})…")
    users = fetch_users()
    print(f"Found {len(users)} users")

    lines = [f"# Profile scrub run {datetime.now(timezone.utc).isoformat()}", ""]
    lines.append(f"Regen companies: {REGEN_COMPANIES}")
    lines.append(f"Keywords cap: {KEYWORDS_CAP}")
    lines.append(f"Scrub negativeKeywords: {sorted(SCRUB_NEG)}")
    lines.append("")

    overall_ok = True

    for u in users:
        slug = u.get("slug")
        ek = u.get("editKey")
        if not slug or not ek:
            print(f"[skip:{slug}] no edit_key")
            lines.append(f"- **{slug}** — SKIPPED (no edit_key)")
            continue

        profile = fetch_profile(slug)
        if not profile:
            print(f"[skip:{slug}] no profile")
            lines.append(f"- **{slug}** — SKIPPED (no profile)")
            continue

        patches = {}

        # 1) Trim keywords
        kw = profile.get("keywords") or []
        if len(kw) > KEYWORDS_CAP:
            patches["keywords"] = kw[:KEYWORDS_CAP]

        # 2) Scrub negativeKeywords of overly-aggressive entries
        neg = profile.get("negativeKeywords") or []
        new_neg = [n for n in neg if (n or "").lower().strip() not in SCRUB_NEG]
        if len(new_neg) != len(neg):
            patches["negativeKeywords"] = new_neg

        if not patches:
            print(f"[clean:{slug}] nothing to scrub")
            lines.append(f"- **{slug}** — already clean")
        else:
            status, resp = patch_profile(slug, ek, patches)
            ok = 200 <= status < 300
            overall_ok &= ok
            removed_neg = sorted(set((n or "").lower().strip() for n in neg) - set((n or "").lower().strip() for n in new_neg))
            kept_kw = len(patches.get("keywords", kw))
            print(f"[{'OK' if ok else 'FAIL'}:{slug}] HTTP {status} kw={len(kw)}→{kept_kw}, removed_neg={removed_neg}")
            lines.append(f"- **{slug}** — HTTP {status} {'OK' if ok else 'FAIL'}")
            lines.append(f"  - keywords: {len(kw)} → {kept_kw}")
            lines.append(f"  - removed from negativeKeywords: {removed_neg}")

        # 3) Optionally regen companies via /regenerate-companies
        if REGEN_COMPANIES:
            tc_before = len(profile.get("targetCompanies") or [])
            status2, resp2 = regen_companies(slug, ek)
            if 200 <= status2 < 300:
                try:
                    d = json.loads(resp2)
                    tc_after = len((d.get("profile") or {}).get("targetCompanies") or [])
                    diff = (d.get("diff") or {}).get("summary", "")
                    print(f"  [regen-co:{slug}] {tc_before} → {tc_after} ({diff})")
                    lines.append(f"  - regen-companies: {tc_before} → {tc_after} ({diff})")
                except Exception as e:
                    lines.append(f"  - regen-companies: HTTP {status2} (parse error)")
            else:
                print(f"  [regen-co-FAIL:{slug}] HTTP {status2}")
                lines.append(f"  - regen-companies: HTTP {status2} FAIL")
                overall_ok = False

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = os.path.join(REPORT_DIR, f"scrub_{stamp}.md")
    with open(report, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {report}")
    return 0 if overall_ok else 3


if __name__ == "__main__":
    sys.exit(main())
