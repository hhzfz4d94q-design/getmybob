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


def extract_inline_js_blocks(html: str) -> list[tuple[int, str]]:
    """Find each top-level inline <script>...</script> block — exactly the
    way the browser's HTML parser does it: from each opening <script> tag
    (without src=) to the NEXT </script>. This is critical because the
    browser parses each block as a SEPARATE JS context. Concatenating them
    (as an earlier version of this test did) can mask serious bugs like
    'Wizard v3 block injected into a JS template literal so the page sees
    </script> early and dies with Unexpected-end-of-input'.

    Returns list of (start_line_1indexed, code) tuples.
    """
    lines = html.split("\n")
    blocks: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        # Match either `<script>` alone OR `<script>` opening (no src attribute)
        is_open = stripped.startswith("<script>") and "src=" not in stripped and "</script>" not in stripped
        if not is_open:
            i += 1
            continue
        start = i + 1
        # Find next </script> alone on a line (matches browser's HTML parser)
        j = i + 1
        while j < len(lines) and lines[j].strip() != "</script>":
            j += 1
        if j >= len(lines):
            # Unterminated <script> — definitely a bug; record what we have
            blocks.append((start + 1, "\n".join(lines[start:])))
            break
        blocks.append((start + 1, "\n".join(lines[start:j])))
        i = j + 1
    return blocks


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
parsed_js_by_file = {}  # cache for the next test — concatenated for grep purposes
for p in DASHBOARDS:
    fn = os.path.basename(p)
    with open(p, "r", errors="replace") as f:
        html = f.read()
    blocks = extract_inline_js_blocks(html)
    if not blocks:
        check(f"{fn}: at least one inline <script> block found", False,
              "could not find any inline <script>...</script>")
        continue
    all_ok = True
    block_summary = []
    for idx, (start_line, code) in enumerate(blocks, 1):
        ok, err = parse_js(code)
        if ok:
            block_summary.append(f"block {idx}@L{start_line}={len(code):,}B ✓")
        else:
            all_ok = False
            # Translate node's local line to HTML line
            import re as _re
            m = _re.search(r":(\d+)", err)
            html_line = (start_line + int(m.group(1)) - 1) if m else None
            print(f"  ✗ {fn}: block {idx} (starts at HTML line {start_line}) FAILED parse"
                  + (f" — error near HTML line {html_line}" if html_line else ""))
            for ln in err.split("\n")[:5]:
                print(f"      {ln}")
    if all_ok:
        check(f"{fn}: {len(blocks)} script block(s) parse cleanly  [" + ", ".join(block_summary) + "]", True)
        # Concatenate ALL block code for the onclick-handler-resolution check below
        parsed_js_by_file[p] = "\n".join(c for _, c in blocks)
    else:
        check(f"{fn}: all {len(blocks)} script block(s) parse cleanly", False, "see error(s) above")


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
