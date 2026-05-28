"""Pull every user's contacts via /admin/contacts GET, extract unique companies
not already in the catalog, ask Claude for ATS hint per company in one batch,
merge into healthtech_companies.json / companies.json.
"""
import json
import os
import re
import sys
import urllib.request

WORKER = "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev"


def fetch_json(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def main():
    admin_key = os.environ.get("ADMIN_KEY", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not admin_key:
        print("FATAL: ADMIN_KEY not set", file=sys.stderr)
        return 1
    if not api_key:
        print("FATAL: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    users = fetch_json(f"{WORKER}/users").get("users", [])
    print(f"Found {len(users)} users")

    all_companies = {}
    for u in users:
        slug = u.get("slug")
        if not slug:
            continue
        try:
            contacts = fetch_json(
                f"{WORKER}/admin/contacts?user={slug}", headers={"X-Admin-Key": admin_key}
            )
        except Exception as e:
            print(f"  [{slug}] no contacts ({e})")
            continue
        if not isinstance(contacts, list):
            print(f"  [{slug}] unexpected payload type — skipping")
            continue
        print(f"  [{slug}] {len(contacts)} contacts")
        for c in contacts:
            co = (c.get("company") or "").strip()
            if not co or len(co) < 2:
                continue
            key = co.lower()
            if key not in all_companies:
                all_companies[key] = {"name": co, "count": 0}
            all_companies[key]["count"] += 1

    ranked = sorted(all_companies.values(), key=lambda x: -x["count"])
    print(f"{len(ranked)} unique companies across all contacts")

    with open("healthtech_companies.json") as f:
        ht = json.load(f)
    with open("companies.json") as f:
        co = json.load(f)

    known = {c.get("name", "").lower() for c in ht["companies"]}
    known |= {w.get("name", "").lower() for w in co.get("workday", [])}
    for k in ("greenhouse", "lever", "ashby"):
        for s in co.get(k, []):
            name = s if isinstance(s, str) else s.get("slug", "")
            known.add(name.lower())

    new = [r for r in ranked if r["name"].lower() not in known][:80]
    if not new:
        print("No new companies to enrich — exiting.")
        return 0
    print(f"Asking Claude about {len(new)} new companies")

    prompt = (
        "For each of these US-based companies, identify the ATS "
        "(greenhouse/lever/ashby/workday/icims/other) and slug or workday URL if known.\n\n"
        "Companies:\n"
        + "\n".join(f"- {r['name']}" for r in new)
        + "\n\nOutput a JSON array. One object per company with fields: "
        "name, atsHint (lowercased), slug (for greenhouse/lever/ashby — leave blank otherwise), "
        "and a workday object with tenant/subdomain/site only when you have HIGH confidence. "
        "Be conservative — atsHint='other' if you don't know. Don't invent slugs."
    )

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
                "model": "claude-sonnet-4-6",
                "max_tokens": 16000,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode(),
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read().decode())
    text = resp.get("content", [{}])[0].get("text", "")
    cleaned = re.sub(r"^```json\s*|```$", "", text.strip(), flags=re.MULTILINE)
    enriched = json.loads(cleaned)
    print(f"Enriched {len(enriched)} companies")

    ht_slugs = {c.get("slug", "").lower() for c in ht["companies"]}
    wd_keys = {(w.get("tenant", ""), w.get("site", "")) for w in co.get("workday", [])}
    added_ht = 0
    added_wd = 0
    for e in enriched:
        hint = (e.get("atsHint") or "").lower()
        slug = (e.get("slug") or "").lower()
        if hint in {"greenhouse", "lever", "ashby", "workable"} and slug and slug not in ht_slugs:
            ht["companies"].append(
                {
                    "name": e.get("name", ""),
                    "category": "from-contacts",
                    "atsHint": hint,
                    "slug": slug,
                }
            )
            ht_slugs.add(slug)
            added_ht += 1
        elif hint == "workday":
            wd = e.get("workday") or {}
            if (
                wd.get("tenant")
                and wd.get("site")
                and (wd["tenant"], wd["site"]) not in wd_keys
            ):
                co["workday"].append(
                    {
                        "name": e.get("name", ""),
                        "tenant": wd["tenant"],
                        "subdomain": wd.get("subdomain", "wd1"),
                        "site": wd["site"],
                        "industries": ["from-contacts"],
                    }
                )
                wd_keys.add((wd["tenant"], wd["site"]))
                added_wd += 1

    ht["version"] = (ht.get("version", "") + "+from-contacts").strip("+")
    with open("healthtech_companies.json", "w") as f:
        json.dump(ht, f, indent=2)
    with open("companies.json", "w") as f:
        json.dump(co, f, indent=2)
    print(f"DONE — added {added_ht} healthtech + {added_wd} workday from contacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
