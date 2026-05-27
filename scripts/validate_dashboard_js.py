"""Validates that every <script> block in the generated dashboard HTML parses
as syntactically-correct JavaScript. Catches escape-hell bugs (literal newlines
in JS strings, bare apostrophes, etc.) BEFORE they reach the live dashboard.

Usage: python3 scripts/validate_dashboard_js.py
Exit: 0 if all scripts parse, 1 if any fail (with details printed).

Used by .github/workflows/js-syntax-gate.yml on every PR/push touching
fetch_jobs.py, and locally before pushing changes.
"""
import sys
import os
import re
import subprocess
import tempfile
import importlib.util


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fj_path = os.path.join(root, "fetch_jobs.py")
    if not os.path.exists(fj_path):
        print(f"FATAL: {fj_path} not found", file=sys.stderr)
        return 2

    # Import fetch_jobs.py without executing its main() — just load HTML_TEMPLATE
    spec = importlib.util.spec_from_file_location("fj", fj_path)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except Exception as e:
        print(f"FATAL: fetch_jobs.py module-load failed: {e}", file=sys.stderr)
        return 2

    if not hasattr(m, "HTML_TEMPLATE"):
        print("FATAL: HTML_TEMPLATE not found in fetch_jobs.py", file=sys.stderr)
        return 2

    # Render with dummy kwargs (exhaustive — every placeholder)
    try:
        rendered = m.HTML_TEMPLATE.format(
            total=0, senior_remote=0, ghost=0, generated="x", shown=0,
            cards="", user_slug="x", user_name="x", subtitle="x",
            has_profile_js="true", hidden_jobs_json="[]", low_match_warning="",
        )
    except KeyError as e:
        print(f"FATAL: HTML_TEMPLATE.format() missing kwarg {e}", file=sys.stderr)
        return 2

    # Extract every <script> block
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", rendered, re.DOTALL)
    print(f"Found {len(scripts)} <script> blocks in rendered HTML_TEMPLATE")

    # Also check WIZARD_V3_BLOCK (appended separately)
    if hasattr(m, "WIZARD_V3_BLOCK"):
        wiz_scripts = re.findall(
            r"<script[^>]*>(.*?)</script>", m.WIZARD_V3_BLOCK, re.DOTALL
        )
        scripts.extend(wiz_scripts)
        print(f"+ {len(wiz_scripts)} <script> blocks in WIZARD_V3_BLOCK")

    failures = []
    for i, js in enumerate(scripts):
        if not js.strip():
            continue
        # Write to temp file (surrogatepass to handle any emoji surrogate pairs)
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".js", delete=False
        ) as f:
            f.write(js.encode("utf-8", errors="surrogatepass"))
            path = f.name
        r = subprocess.run(
            ["node", "-c", path], capture_output=True, text=True
        )
        if r.returncode == 0:
            print(f"  ✓ script #{i+1} ({len(js):>7} chars)")
        else:
            print(f"  ✗ script #{i+1} ({len(js):>7} chars) FAIL:")
            # Show first 5 lines of error
            for line in (r.stderr or r.stdout or "").splitlines()[:6]:
                print(f"      {line}")
            failures.append((i + 1, r.stderr or r.stdout))
        os.unlink(path)

    if failures:
        print(f"\nFAILURE: {len(failures)} script(s) failed JS syntax check")
        return 1

    print("\n✓ All scripts parse cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
