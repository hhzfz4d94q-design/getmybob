"""Ask Claude for mid-stage healthcare leadership employers, merge into catalog.

Env: ANTHROPIC_API_KEY (required), COUNT (default 200), FOCUS (default mid-stage).
Outputs commit-ready changes to healthtech_companies.json + companies.json.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error


def main():
    count = max(50, min(300, int(os.environ.get("COUNT", "200"))))
    focus = os.environ.get("FOCUS", "mid-stage")

    focus_clause = {
        "mid-stage": (
            "200-2000 employees, Series B-D or post-IPO mid-cap. These are the "
            "companies actively scaling and hiring senior leaders publicly."
        ),
        "enterprise": "5000+ employees, established Fortune-500-adjacent. Often on Workday.",
        "mixed": (
            "a mix across stages — 30% startup (Series A-B), 50% mid-stage "
            "(200-2000), 20% enterprise."
        ),
    }[focus]

    prompt = f"""You're populating a US healthcare/healthtech employer catalog for a senior digital-transformation product leader.

Target band: {focus_clause}

Return exactly {count} distinct US-based healthcare-domain companies that hire senior product / transformation / GRC / IT leaders. Include verticals:
- Mid-stage healthtech SaaS (telehealth, payer-tech, EHR-adjacent, clinical-AI)
- Value-based care / risk-bearing care delivery
- Real-world data / life-sciences analytics
- Medical devices + diagnostics (mid-cap)
- Pharma + biotech (mid-cap)
- Health insurers + payers (regional + national)
- Major US health systems (Workday-hosted)
- Health-IT compliance / interoperability vendors

For each company, output a JSON object with these fields:
  name (string), vertical (string), atsHint (one of greenhouse|lever|ashby|workday|icims|smartrecruiters|other), slug (lowercased ATS slug — omit for workday), workday (object with tenant, subdomain like wd1/wd3/wd5/wd12, and site — only for workday entries you have HIGH confidence about).

Output ONLY a JSON array of these objects. No prose, no markdown fences, just the array. {count} objects.
Skip companies with fewer than 50 employees. Skip pure consultancies. Skip recruiters.
Prefer companies you have HIGH confidence about. Don't invent slugs or workday URLs you're not sure of. For workday entries you're uncertain about, OMIT the workday object — we'll fall back to catalog-only."""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("FATAL: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1
    print(f"API key present (len={len(api_key)}, prefix={api_key[:8]}…)", flush=True)

    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")
    print(f"Using model: {model}, asking for {count} companies, focus={focus}", flush=True)

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        data=json.dumps(
            {
                "model": model,
                "max_tokens": 16000,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode(),
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            status = r.status
            body = r.read().decode()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"FATAL: Anthropic API HTTPError {e.code}: {err_body[:1500]}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"FATAL: Anthropic request failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(f"API HTTP {status}, body length={len(body)}", flush=True)
    try:
        resp = json.loads(body)
    except Exception as e:
        print(f"FATAL: API body not JSON: {e}\nHead: {body[:500]}", file=sys.stderr)
        return 1
    text = resp.get("content", [{}])[0].get("text", "")
    print(f"Claude text length={len(text)}, head={text[:200]!r}", flush=True)
    cleaned = re.sub(r"^```json\s*|```$", "", text.strip(), flags=re.MULTILINE)
    try:
        companies = json.loads(cleaned)
    except Exception as e:
        print(
            f"FATAL: Claude didn't return valid JSON: {e}\n"
            f"Head: {cleaned[:500]}\nTail: {cleaned[-500:]}",
            file=sys.stderr,
        )
        return 1
    print(f"Discovered {len(companies)} companies from Claude", flush=True)

    with open("healthtech_companies.json") as f:
        ht = json.load(f)
    ht_slugs = {c.get("slug", "").lower() for c in ht["companies"]}

    added_ht = 0
    for c in companies:
        hint = (c.get("atsHint") or "").lower()
        slug = (c.get("slug") or "").lower()
        if (
            hint in {"greenhouse", "lever", "ashby", "workable"}
            and slug
            and slug not in ht_slugs
        ):
            ht["companies"].append(
                {
                    "name": c.get("name", ""),
                    "category": c.get("vertical", "healthcare"),
                    "atsHint": hint,
                    "slug": slug,
                }
            )
            ht_slugs.add(slug)
            added_ht += 1
    ht["version"] = (ht.get("version", "") + "+discovered").strip("+")
    with open("healthtech_companies.json", "w") as f:
        json.dump(ht, f, indent=2)
    print(f"Added {added_ht} healthtech entries")

    with open("companies.json") as f:
        co = json.load(f)
    wd_keys = {(w.get("tenant", ""), w.get("site", "")) for w in co.get("workday", [])}
    added_wd = 0
    for c in companies:
        if (c.get("atsHint") or "").lower() != "workday":
            continue
        wd = c.get("workday") or {}
        if not wd.get("tenant") or not wd.get("site"):
            continue
        key = (wd["tenant"], wd["site"])
        if key in wd_keys:
            continue
        co["workday"].append(
            {
                "name": c.get("name", ""),
                "tenant": wd["tenant"],
                "subdomain": wd.get("subdomain", "wd1"),
                "site": wd["site"],
                "industries": ["healthcare", "health-saas"],
            }
        )
        wd_keys.add(key)
        added_wd += 1
    with open("companies.json", "w") as f:
        json.dump(co, f, indent=2)
    print(f"Added {added_wd} workday tenants")
    print(f"DONE — total new: {added_ht + added_wd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
