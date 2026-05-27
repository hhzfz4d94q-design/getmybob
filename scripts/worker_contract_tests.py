"""Worker endpoint contract tests. Hits each known Worker endpoint with
sample inputs, asserts response shape + status. Catches Worker regressions
before they break the client.

Env: WORKER_URL (defaults to cool-darkness-dce5.tr6jz6v7wg.workers.dev)
     ADMIN_KEY (required for endpoints that need it)
Exit 0 = all green, 1 = any failure.
"""
import os
import sys
import json
import urllib.request
import urllib.error

WORKER = os.environ.get(
    "WORKER_URL", "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev"
).rstrip("/")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
TEST_SLUG = os.environ.get("TEST_SLUG", "amit-arora")


def req(path, method="GET", headers=None, body=None, timeout=30):
    url = WORKER + path
    headers = dict(headers or {})
    headers.setdefault("User-Agent", "getmemyjob-contract-test/1.0")
    if body is not None:
        headers.setdefault("Content-Type", "application/json")
        body = json.dumps(body).encode("utf-8")
    r = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def expect(name, ok, detail=""):
    print(f"  {'✓' if ok else '✗'} {name}{(' — ' + detail) if detail and not ok else ''}")
    return ok


def main():
    print(f"Worker contract tests against {WORKER}")
    all_ok = True

    # GET /
    s, t = req("/")
    all_ok &= expect("GET /", s == 200, f"status {s}")

    # GET /skills-profile
    s, t = req(f"/skills-profile?user={TEST_SLUG}")
    try:
        data = json.loads(t)
        has_profile_field = "profile" in data
        all_ok &= expect("GET /skills-profile shape", has_profile_field, "missing 'profile' field")
        if has_profile_field and data["profile"]:
            p = data["profile"]
            all_ok &= expect("  profile.targetTitles is array", isinstance(p.get("targetTitles"), list))
            all_ok &= expect("  profile.industries is array", isinstance(p.get("industries"), list))
    except Exception as e:
        all_ok &= expect("/skills-profile parses as JSON", False, str(e))

    # GET /admin/users (admin-only)
    if ADMIN_KEY:
        s, t = req("/admin/users", headers={"X-Admin-Key": ADMIN_KEY})
        all_ok &= expect("GET /admin/users (admin auth)", s == 200, f"status {s}")
        try:
            d = json.loads(t)
            all_ok &= expect("  users array exists", isinstance(d.get("users"), list))
        except Exception as e:
            all_ok &= expect("/admin/users parses", False, str(e))

    # POST /rerank-titles (no body — should error gracefully)
    s, t = req(f"/rerank-titles?user={TEST_SLUG}", method="POST", body={"items": []})
    all_ok &= expect("POST /rerank-titles empty body", s == 200, f"status {s}")

    # POST /regenerate-companies with dry_run (read-only)
    if ADMIN_KEY:
        # First need user's edit-key — fetch via admin/users
        ek = None
        s, t = req("/admin/users", headers={"X-Admin-Key": ADMIN_KEY})
        if s == 200:
            try:
                for u in json.loads(t).get("users", []):
                    if u.get("slug") == TEST_SLUG:
                        ek = u.get("editKey")
                        break
            except Exception:
                pass
        if ek:
            s, t = req(
                f"/regenerate-companies?user={TEST_SLUG}",
                method="POST",
                headers={"X-Edit-Key": ek},
                body={"dry_run": True},
                timeout=60,
            )
            all_ok &= expect("POST /regenerate-companies dry_run", s == 200, f"status {s}")
            try:
                d = json.loads(t)
                all_ok &= expect("  has 'proposed' array", isinstance(d.get("proposed"), list))
                all_ok &= expect("  has 'diff' object", isinstance(d.get("diff"), dict))
            except Exception as e:
                all_ok &= expect("/regenerate-companies parses", False, str(e))

    print(f"\n{'✓ ALL PASS' if all_ok else '✗ FAILURES'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
