"""One-shot: take a per-user dream list, ask Claude for ATS+slug per name,
fix broken slugs on existing entries, merge into catalog with dreamList tagging.

Env: ANTHROPIC_API_KEY (required), DREAM_USER (default 'geetu'), DREAM_FILE
(path to a one-name-per-line file, default scripts/dream_lists/{user}.txt).
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request


def main():
    user = os.environ.get("DREAM_USER", "geetu")
    dream_file = os.environ.get("DREAM_FILE", f"scripts/dream_lists/{user}.txt")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("FATAL: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1
    if not os.path.exists(dream_file):
        print(f"FATAL: {dream_file} not found", file=sys.stderr)
        return 1

    names = [
        l.strip() for l in open(dream_file).read().splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]
    # Dedupe preserving order
    seen = set(); names = [n for n in names if not (n.lower() in seen or seen.add(n.lower()))]
    print(f"Loaded {len(names)} unique dream companies for {user}", flush=True)

    prompt = (
        f"For each of these US-based companies, identify the primary ATS the careers page uses. "
        f"Output a JSON array, one object per company with these fields:\n"
        f"  - name (string, exactly as provided)\n"
        f"  - atsHint (one of: greenhouse | lever | ashby | workday | smartrecruiters | icims | workable | other)\n"
        f"  - slug (lowercased ATS slug — REQUIRED for greenhouse/lever/ashby/workable, omit for workday)\n"
        f"  - workday (object {{tenant, subdomain, site}} — REQUIRED for workday entries you have HIGH confidence about, otherwise omit)\n"
        f"  - vertical (one of: healthcare | tech | finance | consumer | media | other)\n\n"
        f"Be conservative: if you don't know the slug or workday URL, use atsHint='other' and omit slug/workday. "
        f"Don't invent slugs you're not 99% sure about.\n\n"
        f"Companies:\n" + "\n".join(f"- {n}" for n in names) +
        "\n\nReturn ONLY the JSON array, no prose, no markdown fences."
    )

    print(f"Asking Claude about {len(names)} companies...", flush=True)
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
    enriched = json.loads(cleaned)
    print(f"Claude returned {len(enriched)} entries", flush=True)

    with open("healthtech_companies.json") as f:
        ht = json.load(f)
    with open("companies.json") as f:
        co = json.load(f)

    # Build canonical-name → existing-entry index so we can fix slugs in place
    from matcher.canonical import canonical_company
    ht_by_canon = {canonical_company(c.get("name","")): c for c in ht["companies"]}
    wd_by_canon = {canonical_company(w.get("name","")): w for w in co.get("workday",[])}

    added_ht = 0; added_wd = 0; updated = 0
    for e in enriched:
        name = e.get("name","")
        if not name: continue
        canon = canonical_company(name)
        hint = (e.get("atsHint") or "").lower()
        slug = (e.get("slug") or "").lower()
        vertical = e.get("vertical","other")

        existing = ht_by_canon.get(canon) or wd_by_canon.get(canon)
        if existing:
            # Already in catalog — just tag dreamList, fix slug if Claude has a better one
            existing["dreamList"] = True
            existing["dreamListFor"] = user
            if slug and slug != (existing.get("slug","") or "").lower():
                old_slug = existing.get("slug","")
                existing["slug"] = slug
                print(f"  ↻ {name}: slug {old_slug!r} → {slug!r}")
                updated += 1
            continue

        # New entry
        if hint in {"greenhouse","lever","ashby","workable"} and slug:
            ht["companies"].append({
                "name": name,
                "category": f"dream-list-{user}",
                "atsHint": hint,
                "slug": slug,
                "vertical": vertical,
                "dreamList": True,
                "dreamListFor": user,
            })
            added_ht += 1
            print(f"  + HT [{hint:10}] {name:30} {slug}")
        elif hint == "workday":
            wd = e.get("workday") or {}
            if wd.get("tenant") and wd.get("site"):
                co["workday"].append({
                    "name": name,
                    "tenant": wd["tenant"],
                    "subdomain": wd.get("subdomain","wd1"),
                    "site": wd["site"],
                    "vertical": vertical,
                    "dreamList": True,
                    "dreamListFor": user,
                })
                added_wd += 1
                print(f"  + WD {name:30} {wd['tenant']}/{wd['site']}")
            else:
                print(f"  ? WD {name}: Claude flagged workday but no tenant/site — skipping")
        else:
            print(f"  ? {name}: atsHint={hint!r} slug={slug!r} — skipping (Claude wasn't confident)")

    ht["version"] = ht.get("version","").rstrip("+") + f"+dream-{user}"
    with open("healthtech_companies.json","w") as f: json.dump(ht, f, indent=2)
    with open("companies.json","w") as f: json.dump(co, f, indent=2)
    print(f"\nDONE — added {added_ht} HT + {added_wd} WD, fixed {updated} existing slugs, tagged dreamListFor={user}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
