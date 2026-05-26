"""Static checks on every per-user dashboard HTML:

  (1) Inline <script> blocks parse cleanly via `node --check`
      → Catches the class of bug we hit 2026-05-26 evening: a single
        unescaped apostrophe in 'Skip — I'll fill manually' caused JS
        parsing to abort, which broke EVERY button on the page silently.

  (2) Every onclick="funcName(...)" handler in the HTML refers to a
      function (or assignment to that name) that actually exists in the
      page's inline JS or in document.addEventListener/window.X glue.
      → Catches "click does nothing" failures from renamed/removed
        functions and typos.

Run via:  python3 tests/test_dashboard_js_syntax.py
Exits non-zero on any failure.

Requires `node` (already in test.yml's setup-node step).
"""
import os, re, sys, subprocess, tempfile, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# All per-user dashboard HTML files at repo root
CANDIDATES = sorted(glob.glob(os.path.join(ROOT, "*.html")))
# Filter to ones that have an inline <script> and look like a dashboard
# (skip simple pages like login.html, admin.html unless they're dashboards too)
DASHBOARDS = []
for p in CANDIDATES:
    with open(p, "r", errors="replace") as f:
        head = f.read(2048)
    # Heuristic: dashboard HTMLs declare "Jobs for ..." in <title> or <h1>
    if "Jobs for" in head or ("getmemyjob" in head and "data-fp=" in open(p, "r", errors="replace").read(50000)):
        DASHBOARDS.append(p)

if not DASHBOARDS:
    print("✗ No dashboard HTML files found at repo root — nothing to check")
    sys.exit(1)

PASS = 0
FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  ({detail})")


def extract_inline_js(html: str) -> str:
    """Concatenate all inline <script>...</script> bodies (no src=) into one string.

    Note: the dashboard sometimes contains literal '<script>' / '</script>'
    INSIDE a JS template literal (the wizard-v3 block renders an HTML chunk
    that contains a script tag). To handle that without writing a full HTML
    tokenizer, we take everything between the FIRST opening '<script>' tag
    on its own line and the LAST '</script>' tag, which is how every
    generated dashboard is structured.
    """
    lines = html.split("\n")
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("<script>") and "src=" not in stripped:
            start = i + 1
            break
    end = None
    for i in range(len(lines) - 1, -1, -1):
        if "</script>" in lines[i] and "<script>" not in lines[i] and "<script " not in lines[i]:
            end = i
            break
    if start is None or end is None or start >= end:
        return ""
    return "\n".join(lines[start:end])


def parse_js(js: str) -> tuple[bool, str]:
    """Run `node --check` on the given JS string. Returns (ok, error_excerpt)."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
        path = f.name
    r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
    os.unlink(path)
    if r.returncode == 0:
        return (True, "")
    # Pull a useful 4-line excerpt around the syntax error
    excerpt = "\n      ".join(r.stderr.strip().split("\n")[:6])
    return (False, excerpt)


# ----------------------------------------------------------------------
# (1) Inline JS parses cleanly
# ----------------------------------------------------------------------
print("(1) Inline JS syntax check (node --check on each dashboard):")
parsed_js_by_file = {}  # cache for the next test
for p in DASHBOARDS:
    fn = os.path.basename(p)
    with open(p, "r", errors="replace") as f:
        html = f.read()
    js = extract_inline_js(html)
    if not js:
        check(f"{fn}: inline JS extractable", False, "could not find <script>...</script> bounds")
        continue
    ok, err = parse_js(js)
    if ok:
        check(f"{fn}: parses cleanly ({len(js):,} bytes)", True)
        parsed_js_by_file[p] = js
    else:
        check(f"{fn}: parses cleanly", False, "see error below")
        print(f"      {err}")


# ----------------------------------------------------------------------
# (2) onclick handlers refer to functions that exist somewhere in the JS
# ----------------------------------------------------------------------
print("\n(2) onclick handlers reference functions that exist in inline JS:")

# Match: onclick="funcName(...)" — only verify the FIRST identifier
# (a chained expression like "obj.method(...)" would be flagged here too —
# so we restrict to simple top-level function names like prepApplication, refreshData)
ONCLICK_RE = re.compile(r'onclick="([A-Za-z_][A-Za-z0-9_]*)\s*\(', re.IGNORECASE)

# A function "exists" if any of these patterns is in the inline JS:
#   function NAME(
#   NAME = function
#   NAME = async function
#   NAME = (...) =>
#   window.NAME = ...
#   const NAME = ...   /  let NAME = ...   /  var NAME = ...
def function_exists(name: str, js: str) -> bool:
    patterns = [
        rf'\bfunction\s+{re.escape(name)}\s*\(',
        rf'\b{re.escape(name)}\s*=\s*function\b',
        rf'\b{re.escape(name)}\s*=\s*async\s+function\b',
        rf'\b{re.escape(name)}\s*=\s*\([^)]*\)\s*=>',
        rf'\bwindow\.{re.escape(name)}\s*=',
        rf'\b(?:const|let|var)\s+{re.escape(name)}\s*=',
    ]
    return any(re.search(p, js) for p in patterns)


# Skip names that aren't function calls — JS reserved words used in inline
# expressions like onclick="if(event.target===this)closeModal()"
JS_RESERVED = {
    "if", "for", "while", "do", "switch", "case", "return", "throw",
    "var", "let", "const", "new", "typeof", "instanceof", "delete",
    "void", "in", "of", "try", "catch", "finally", "function", "class",
    "this", "super", "yield", "async", "await",
}

# Browser globals that don't need a definition (built-in or document-level)
BUILTINS = {
    "event", "alert", "confirm", "prompt",
}

for p in DASHBOARDS:
    fn = os.path.basename(p)
    js = parsed_js_by_file.get(p)
    if js is None:
        continue  # skip files that failed parse (already reported)
    with open(p, "r", errors="replace") as f:
        html = f.read()
    handlers = set(ONCLICK_RE.findall(html))
    if not handlers:
        check(f"{fn}: has at least 1 onclick handler", False, "no onclick attributes found")
        continue
    missing = [h for h in handlers
               if h not in BUILTINS and h not in JS_RESERVED
               and not function_exists(h, js)]
    if not missing:
        check(f"{fn}: all {len(handlers)} onclick handlers resolve to defined functions", True)
    else:
        check(f"{fn}: all onclick handlers resolve", False,
              f"undefined: {sorted(missing)}")


# ----------------------------------------------------------------------
print(f"\n{'='*48}")
print(f"Result: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
