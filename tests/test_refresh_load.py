"""Load projection for refresh-jobs — when do we hit the GitHub Actions timeout?

Not a CI test (would burn minutes). Run manually to project scrape duration
as catalog grows. Catches "catalog hit 1000 entries and now refresh times
out at 6h" before it becomes a midnight incident.

Usage:
  python3 tests/test_refresh_load.py            # uses observed timing
  python3 tests/test_refresh_load.py --catalog 1500  # project at 1500
"""
import argparse
import sys

# Observed: 2026-05-28 22:24 refresh ran 1310s scraping 432 catalog entries
# (270 HT + 108 WD ≈ 378 ATS-bound + workday-bound; plus 50-ish from VC).
OBSERVED_ENTRIES = 432
OBSERVED_SECONDS = 1310
GH_ACTIONS_TIMEOUT_SECONDS = 6 * 3600  # 6h hard limit


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", type=int, default=OBSERVED_ENTRIES,
                   help="Projected catalog size (entries)")
    args = p.parse_args()

    per_entry = OBSERVED_SECONDS / OBSERVED_ENTRIES
    projected = args.catalog * per_entry
    pct_of_limit = projected / GH_ACTIONS_TIMEOUT_SECONDS * 100

    print(f"=== refresh-jobs load projection ===\n")
    print(f"  Observed baseline: {OBSERVED_ENTRIES} entries in {OBSERVED_SECONDS}s")
    print(f"  Per-entry cost:    {per_entry:.2f}s")
    print(f"\n  Projection for {args.catalog} entries:")
    print(f"    Projected time:  {projected:.0f}s ({projected/60:.1f}min)")
    print(f"    % of 6h limit:   {pct_of_limit:.1f}%")

    # Project some milestones
    print(f"\n  Catalog milestones:")
    for n in [500, 800, 1200, 2000, 3000, 5000]:
        t = n * per_entry
        pct = t / GH_ACTIONS_TIMEOUT_SECONDS * 100
        print(f"    {n:5} entries → {t/60:5.1f}min ({pct:5.1f}% of limit)")

    # Soft alert at 50%
    if pct_of_limit > 80:
        print(f"\n  ⚠ ALERT: projected {pct_of_limit:.0f}% of 6h timeout. "
              f"Time to shard the scrape into parallel jobs.")
        return 1
    elif pct_of_limit > 50:
        print(f"\n  ⚠ WARN: projected {pct_of_limit:.0f}% of 6h timeout. "
              f"Monitor; plan sharding when this hits 80%.")
    else:
        print(f"\n  ✓ OK — well within timeout. Re-run this when catalog "
              f"doubles to stay ahead of trouble.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
