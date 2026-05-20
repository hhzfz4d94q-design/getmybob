"""Scrape YC Work at a Startup using Playwright (the site is an SPA so
plain HTTP returns a shell with no jobs).

Flow:
  1. Launch headless Chromium
  2. Navigate to workatastartup.com/jobs (their search page)
  3. Let the SPA load — wait for any job-card-looking thing OR a known
     React-Query / Apollo / Next.js state blob in window.__INITIAL_*
  4. Extract: (a) __NEXT_DATA__ JSON if present, (b) failing that,
     parse the DOM for job cards via a generic anchor-href pattern
  5. Save to data/yc_jobs.json

Designed to fail gracefully — if YC ships a redesign and our selectors
break, we log clearly + leave the previous yc_jobs.json untouched."""
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone

from playwright.async_api import async_playwright

OUTPUT = os.environ.get("YC_OUTPUT", "data/yc_jobs.json")
DEBUG = os.path.join("reports", "yc_scrape_debug.log")


def log(msg):
    print(msg, flush=True)
    try:
        os.makedirs("reports", exist_ok=True)
        with open(DEBUG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")
    except Exception:
        pass


async def scrape():
    jobs_out = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = await ctx.new_page()
        try:
            log("navigating to workatastartup.com/jobs")
            await page.goto("https://www.workatastartup.com/jobs", wait_until="networkidle", timeout=45000)
        except Exception as e:
            log(f"navigation failed: {e}")
            await browser.close()
            return jobs_out

        # Give the SPA a moment to hydrate
        await page.wait_for_timeout(3000)

        # Try __NEXT_DATA__
        try:
            handle = await page.query_selector("script#__NEXT_DATA__")
            if handle:
                txt = await handle.inner_text()
                data = json.loads(txt)
                # Walk for arrays-of-job-looking dicts
                def looks_like_job(d):
                    return (isinstance(d, dict) and
                            any(k in d for k in ("title","name","role")) and
                            any(k in d for k in ("company","company_name","companyName","hiringOrganization","slug","show_url")))
                def find_jobs(node, depth=0):
                    if depth > 10: return None
                    if isinstance(node, list):
                        if node and looks_like_job(node[0]):
                            return node
                        for x in node:
                            r = find_jobs(x, depth+1)
                            if r: return r
                    elif isinstance(node, dict):
                        for v in node.values():
                            r = find_jobs(v, depth+1)
                            if r: return r
                    return None
                raw = find_jobs(data)
                if raw:
                    log(f"NEXT_DATA: found {len(raw)} job records")
                    for j in raw:
                        title = (j.get("title") or j.get("name") or j.get("role") or "").strip()
                        if not title: continue
                        comp = j.get("company") or j.get("company_name") or j.get("companyName")
                        if isinstance(comp, dict): comp = comp.get("name")
                        comp = (comp or "").strip() or "YC Startup"
                        url = j.get("show_url") or j.get("url") or "/jobs"
                        if isinstance(url, str) and url.startswith("/"):
                            url = "https://www.workatastartup.com" + url
                        loc = j.get("location") or j.get("locations") or ""
                        if isinstance(loc, list):
                            loc = ", ".join(l.get("name","") if isinstance(l,dict) else str(l) for l in loc if l)
                        elif isinstance(loc, dict):
                            loc = loc.get("name","")
                        jobs_out.append({
                            "id": str(j.get("id") or url),
                            "title": title,
                            "company": comp,
                            "url": url,
                            "location": (loc or "")[:200],
                            "posted_at": (j.get("posted_at") or j.get("created_at") or "")[:10],
                            "description": (j.get("description") or "")[:5000],
                        })
        except Exception as e:
            log(f"NEXT_DATA parse failed: {e}")

        # Fallback: scan the rendered DOM for job-card anchors
        if not jobs_out:
            log("falling back to DOM scrape")
            try:
                # Scroll a few times so virtualized lists load more
                for _ in range(5):
                    await page.evaluate("window.scrollBy(0, window.innerHeight * 0.9)")
                    await page.wait_for_timeout(1200)
                # Look for anchor tags pointing at job detail pages
                anchors = await page.query_selector_all("a[href*='/jobs/']")
                log(f"DOM scrape: found {len(anchors)} candidate anchors")
                seen = set()
                for a in anchors:
                    try:
                        href = await a.get_attribute("href")
                        text = (await a.inner_text()).strip()
                        if not href or not text or href in seen: continue
                        seen.add(href)
                        url = href if href.startswith("http") else "https://www.workatastartup.com" + href
                        # Title is usually the link text; company often in a sibling element
                        title = text.split("\n")[0].strip()[:140]
                        if len(title) < 4: continue
                        jobs_out.append({
                            "id": url,
                            "title": title,
                            "company": "YC Startup",  # we'll try to enrich from the URL
                            "url": url,
                            "location": "",
                            "posted_at": "",
                            "description": "",
                        })
                    except Exception:
                        continue
            except Exception as e:
                log(f"DOM scrape failed: {e}")

        await browser.close()
    log(f"scraped {len(jobs_out)} jobs total")
    return jobs_out


async def main():
    jobs = await scrape()
    if not jobs:
        log("ZERO jobs scraped — keeping previous yc_jobs.json untouched")
        sys.exit(0)
    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    out = {
        "_meta": {
            "scrapedAt": datetime.now(timezone.utc).isoformat(),
            "count": len(jobs),
            "source": "workatastartup.com via Playwright",
        },
        "jobs": jobs,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    log(f"wrote {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
