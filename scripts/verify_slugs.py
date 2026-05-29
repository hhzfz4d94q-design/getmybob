"""Verify catalog slugs by hitting greenhouse/lever/ashby/workable APIs.
For each 404, ask Claude for the correct slug. Merge.

Run via .github/workflows/verify-slugs.yml — needs ANTHROPIC_API_KEY.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request


UA = "getmemyjob-verify/1.0 (+github.com/hhzfz4d94q-design/getmybob)"
ATS_URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever":      "https://api.lever.co/v0/postings/{slug}",
    "ashby":      "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "workable":   "https://apply.workable.com/api/v1/widget/accounts/{slug}",
}


def head_or_get(url, timeout=10):
    """Return (status, body_size). 404 if not found, 200 if valid."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception:
        return 0, 0


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("FATAL: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    with open("healthtech_companies.json") as f:
        ht = json.load(f)

    dead = []
    valid = 0
    skipped = 0
    print(f"Probing {len(ht['companies'])} healthtech entries against ATS APIs...", flush=True)
    for i, c in enumerate(ht["companies"]):
        hint = (c.get("atsHint") or "").lower()
        slug = (c.get("slug") or "").strip()
        name = c.get("name","")
        if hint not in ATS_URLS or not slug:
            skipped += 1
            continue
        url = ATS_URLS[hint].format(slug=slug)
        status, _ = head_or_get(url, timeout=8)
        if status == 200:
            valid += 1
        elif status == 404:
            dead.append({"name": name, "atsHint": hint, "old_slug": slug, "idx": i})
            print(f"  ✗ DEAD [{hint:10}] {slug:25} ← {name}", flush=True)
        else:
            # 5xx / network — don't conclude dead
            skipped += 1
        if (i+1) % 50 == 0:
            print(f"  ...progress: {i+1}/{len(ht['companies'])} valid={valid} dead={len(dead)} skipped={skipped}", flush=True)
        # Light politeness — avoid hammering one host
        time.sleep(0.05)

    print(f"\nProbe done — valid:{valid} dead:{len(dead)} skipped:{skipped}", flush=True)
    if not dead:
        print("No dead slugs found — nothing to fix")
        return 0

    print(f"\nAsking Claude for correct slugs for {len(dead)} dead entries...", flush=True)
    prompt = (
        "For each US-based company below, identify the CORRECT current ATS slug. "
        "We currently have the wrong slug in our catalog — the API returned 404. "
        "Return a JSON array, one object per company:\n"
        "  - name (string, exactly as provided)\n"
        "  - atsHint (lowercased: greenhouse|lever|ashby|workable|workday|other)\n"
        "  - slug (lowercased correct slug — REQUIRED for greenhouse/lever/ashby/workable)\n"
        "  - workday (only if the company moved off the original ATS to Workday; {tenant, subdomain, site})\n\n"
        "Be conservative: if you don't know the current slug for sure, use atsHint='unknown' and omit slug. "
        "Don't invent slugs.\n\nCompanies (with old/wrong slug shown for context):\n" +
        "\n".join(f"- {d['name']} (old slug was {d['atsHint']}/{d['old_slug']})" for d in dead) +
        "\n\nReturn ONLY the JSON array, no prose."
    )
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        data=json.dumps({
            "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5"),
            "max_tokens": 8000,
            "messages": [{"role": "user", "content": prompt}],
        }).encode(),
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"FATAL: API HTTP {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
        return 1
    text = resp.get("content", [{}])[0].get("text", "")
    cleaned = re.sub(r"^```json\s*|```$", "", text.strip(), flags=re.MULTILINE)
    fixes = json.loads(cleaned)
    print(f"Claude returned {len(fixes)} fix entries", flush=True)

    by_name = {f.get("name","").lower(): f for f in fixes}
    fixed = 0; removed = 0; skipped_no_fix = 0
    for d in dead:
        f = by_name.get(d["name"].lower())
        if not f:
            continue
        new_hint = (f.get("atsHint") or "").lower()
        new_slug = (f.get("slug") or "").strip().lower()
        if new_hint == "unknown" or not new_slug:
            # Claude doesn't know — leave entry but mark as suspect
            ht["companies"][d["idx"]]["suspectSlug"] = True
            skipped_no_fix += 1
            continue
        if new_hint != d["atsHint"] or new_slug != d["old_slug"]:
            ht["companies"][d["idx"]]["atsHint"] = new_hint
            ht["companies"][d["idx"]]["slug"] = new_slug
            ht["companies"][d["idx"]].pop("suspectSlug", None)
            fixed += 1
            print(f"  ↻ {d['name']}: {d['atsHint']}/{d['old_slug']} → {new_hint}/{new_slug}", flush=True)

    ht["version"] = ht.get("version","").rstrip("+") + "+verified"
    with open("healthtech_companies.json","w") as f:
        json.dump(ht, f, indent=2)
    print(f"\nDONE — fixed {fixed} slugs, {skipped_no_fix} marked suspectSlug (Claude unsure)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
