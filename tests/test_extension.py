"""Validate the Chrome extension — manifest correctness + JS syntax.

Run via:  python3 tests/test_extension.py
"""
import os, sys, json, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT  = os.path.join(ROOT, "extension")

PASS = 0
FAIL = 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✓ {label}")
    else:    FAIL += 1; print(f"  ✗ {label}  {detail}")

# --- manifest.json ---
print("manifest.json:")
mpath = os.path.join(EXT, "manifest.json")
check("manifest.json exists", os.path.isfile(mpath))
manifest = json.load(open(mpath))
check("manifest_version is 3", manifest.get("manifest_version") == 3)
check("name set", "getmemyjob" in manifest.get("name", "").lower())
check("version set", bool(manifest.get("version")))
check("has background.service_worker", "service_worker" in (manifest.get("background") or {}))
check("declares Greenhouse host_permission",
      any("greenhouse" in p for p in manifest.get("host_permissions", [])))
check("declares Lever host_permission",
      any("lever" in p for p in manifest.get("host_permissions", [])))
check("declares Ashby host_permission",
      any("ashby" in p for p in manifest.get("host_permissions", [])))
check("declares Workday host_permission",
      any("myworkdayjobs" in p for p in manifest.get("host_permissions", [])))
check("declares getmemyjob host_permission",
      any("getmemyjob" in p for p in manifest.get("host_permissions", [])))

# Content scripts cover all 4 ATSes + our marker
cs = manifest.get("content_scripts", [])
patterns = " ".join(",".join(c.get("matches", [])) for c in cs)
check("content_scripts cover Greenhouse", "greenhouse" in patterns)
check("content_scripts cover Lever",      "lever" in patterns)
check("content_scripts cover Ashby",      "ashby" in patterns)
check("content_scripts cover Workday",    "myworkdayjobs" in patterns)
check("content_scripts cover getmemyjob marker", "getmemyjob" in patterns)

# --- icons exist ---
print("\nicons/:")
for s in (16, 48, 128):
    p = os.path.join(EXT, "icons", f"icon{s}.png")
    check(f"icons/icon{s}.png exists", os.path.isfile(p))

# --- JS syntax check on every .js file ---
print("\nJS syntax:")
for root, _, files in os.walk(EXT):
    for fn in files:
        if not fn.endswith(".js"): continue
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, EXT)
        out = subprocess.run(
            ["node", "-e", f"new Function(require('fs').readFileSync('{full}','utf-8'))"],
            capture_output=True, text=True, timeout=20,
        )
        check(f"{rel} parses", out.returncode == 0,
              out.stderr.strip().split('\n')[-1][:200] if out.returncode else "")

# --- popup.html sanity ---
print("\npopup.html:")
ppath = os.path.join(EXT, "popup.html")
check("popup.html exists", os.path.isfile(ppath))
ph = open(ppath).read()
check("popup loads popup.js", '<script src="popup.js"' in ph)
check("popup has slug+key inputs", 'id="slug"' in ph and 'id="key"' in ph)

# --- README present ---
print("\nREADME.md:")
rpath = os.path.join(EXT, "README.md")
check("README exists", os.path.isfile(rpath))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
