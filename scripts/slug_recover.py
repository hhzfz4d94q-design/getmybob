"""Recover slugs for catalog entries that v1 verify-slugs couldn't fix.

Approach: for each still-dead entry, try MULTIPLE slug variants across
ALL major ATSes. The original verify probed only the stored ATS hint;
many of these companies moved to a different ATS (or got acquired and
went to Workday).

Probes the actual API endpoint for each ATS — slugs that return 200 are
verified. Updates the catalog with the working (ats, slug) combination.

Env: ANTHROPIC_API_KEY (optional, only used for final hand-pick fallback).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request


UA = "getmemyjob-slugrecover/1.0"


def http_status(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, len(r.read(2048))
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception:
        return 0, 0


def slug_variants(name, current_slug):
    """Generate plausible slug variants from a company name."""
    n = name.lower().strip()
    # Strip common suffixes for the variant generator
    n_base = re.sub(r"\s+(health|healthcare|labs|labs\.?|inc\.?|corp|llc|holdings?)\b", "", n)
    # Remove punctuation, normalize whitespace
    n_clean = re.sub(r"[^\w\s-]", "", n_base).strip()
    words = n_clean.split()

    variants = set()
    if current_slug: variants.add(current_slug)
    # Concatenated, no separator
    variants.add("".join(words))
    # First word only
    if words: variants.add(words[0])
    # Hyphen-joined
    variants.add("-".join(words))
    # Full name slug
    variants.add(re.sub(r"[^\w]+", "", n.replace(" ", "")))
    # With "health" suffix if not present
    cat = "".join(words)
    if "health" not in cat and len(words) > 0:
        variants.add(cat + "health")
        variants.add(words[0] + "health")
    # Some companies use "[name]-co" or "[name]inc"
    return [v for v in variants if v and len(v) >= 2]


def probe_company(name, current_ats, current_slug):
    """Try every (ats, slug) combination for this company. Return list of working ones."""
    working = []
    for slug in slug_variants(name, current_slug):
        # greenhouse
        s, _ = http_status(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        if s == 200: working.append(("greenhouse", slug)); break  # first hit wins
        time.sleep(0.05)
        # lever
        s, _ = http_status(f"https://api.lever.co/v0/postings/{slug}")
        if s == 200: working.append(("lever", slug)); break
        time.sleep(0.05)
        # ashby
        s, _ = http_status(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        if s == 200: working.append(("ashby", slug)); break
        time.sleep(0.05)
        # workable
        s, _ = http_status(f"https://apply.workable.com/api/v1/widget/accounts/{slug}")
        if s == 200: working.append(("workable", slug)); break
        time.sleep(0.05)
    return working


def main():
    with open("healthtech_companies.json") as f:
        ht = json.load(f)

    # Pick entries to revisit: marked suspectSlug OR known still-dead from list
    PRIORITY = {
        "hims & hers", "hims & hers health", "cityblock health", "flatiron health",
        "health catalyst", "color health", "hello heart", "headspace health",
        "capital rx", "included health", "prescryptive health", "tomorrow health",
        "devoted health", "oscar health", "k health", "spring health", "omada health",
        "clover health", "komodo health", "guardant health", "headway", "garner health",
        "pager health", "smarter dx", "alphasense", "celonis", "notion", "reddit",
        "dropbox", "anthropic", "instacart", "elastic", "lattice", "huge",
        "kaia health", "sword health", "calibrate", "transcarent", "modern health",
        "aledade", "agilon health", "iora health", "carbon health", "sondermind",
        "ginger", "nurx", "boulder care", "ophelia", "brightside",
    }
    todo = []
    seen = set()
    for c in ht["companies"]:
        nm = c.get("name","").lower().strip()
        if nm in PRIORITY and nm not in seen:
            seen.add(nm)
            todo.append(c)

    print(f"Probing {len(todo)} priority companies across all ATSes...\n", flush=True)
    fixed_count = 0
    no_fix = []
    for c in todo:
        name = c.get("name","")
        cur_ats = c.get("atsHint","")
        cur_slug = c.get("slug","")
        result = probe_company(name, cur_ats, cur_slug)
        if result:
            new_ats, new_slug = result[0]
            if new_ats != cur_ats or new_slug != cur_slug:
                c["atsHint"] = new_ats
                c["slug"] = new_slug
                c.pop("suspectSlug", None)
                print(f"  ✓ FIXED {name:30} {cur_ats}/{cur_slug!r} → {new_ats}/{new_slug!r}", flush=True)
                fixed_count += 1
            else:
                print(f"  = ALREADY OK {name:30} {cur_ats}/{cur_slug}", flush=True)
        else:
            no_fix.append(name)
            c["suspectSlug"] = True

    ht["version"] = ht.get("version","").rstrip("+") + "+slug-recover"
    open("healthtech_companies.json","w").write(json.dumps(ht, indent=2))
    print(f"\nDONE — fixed {fixed_count} slugs, {len(no_fix)} still no working slug:")
    for n in no_fix[:20]:
        print(f"  - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
