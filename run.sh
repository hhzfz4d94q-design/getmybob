#!/bin/bash
# HealthTech Jobs — one-command runner for Mac
# Fetches latest jobs and opens the dashboard in your browser.

cd "$(dirname "$0")"

# Use system python3 (built into macOS)
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required. Install from python.org or run: brew install python"
    exit 1
fi

echo "Fetching jobs from healthcare/health-tech companies…"
python3 fetch_jobs.py

if [ -f index.html ]; then
    echo ""
    echo "Opening dashboard…"
    open index.html
else
    echo "Something went wrong — no dashboard generated."
    exit 1
fi
