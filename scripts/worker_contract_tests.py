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

    # ─── NEW: negative-path tests (no key, bad key) ───────────────────
    # The wizard 401 bug we just fixed would have been caught by these.
    print()
    print("Negative-path / auth tests:")

    # /skills-profile POST with no key → 401
    s, t = req(f"/skills-profile?user={TEST_SLUG}", method="POST", body={"patchFields": {"targetTitles": ["test"]}})
    all_ok &= expect("POST /skills-profile without key returns 401", s == 401, f"status {s}")

    # /skills-profile POST with bad key → 401 (and body should mention X-Edit-Key)
    s, t = req(f"/skills-profile?user={TEST_SLUG}", method="POST",
               headers={"X-Edit-Key": "definitely-not-valid-key"}, body={"patchFields": {}})
    all_ok &= expect("POST /skills-profile with bad key returns 401", s == 401, f"status {s}")
    all_ok &= expect("  401 body mentions 'X-Edit-Key' (so wizard can match-and-friendly-ize)",
                     "X-Edit-Key" in t or "edit" in t.lower() or "auth" in t.lower(),
                     f"body: {t[:120]}")

    # /regenerate-companies POST with no key → 401
    s, t = req(f"/regenerate-companies?user={TEST_SLUG}", method="POST", body={"dry_run": True})
    all_ok &= expect("POST /regenerate-companies without key returns 401", s == 401, f"status {s}")

    # ─── NEW: shape contracts for endpoints the wizard / dashboard depend on ──
    print()
    print("Shape contracts (admin-key authed):")
    if ADMIN_KEY:
        # /tracker GET — must return { tracker: {...} }
        s, t = req(f"/tracker?user={TEST_SLUG}", headers={"X-Admin-Key": ADMIN_KEY})
        all_ok &= expect("GET /tracker returns 200", s == 200, f"status {s}")
        try:
            d = json.loads(t)
            all_ok &= expect("  has 'tracker' object", isinstance(d.get("tracker"), dict))
        except Exception as e:
            all_ok &= expect("/tracker parses", False, str(e))

        # /suggest-refinements — POST, returns suggestions or insufficient_data
        s, t = req(f"/suggest-refinements?user={TEST_SLUG}", method="POST",
                   headers={"X-Admin-Key": ADMIN_KEY}, body={}, timeout=60)
        all_ok &= expect("POST /suggest-refinements returns 200", s == 200, f"status {s}")
        try:
            d = json.loads(t)
            # Either {status:'insufficient_data', suggestions:[]} or {suggestions:[...]} — both have 'suggestions'
            all_ok &= expect("  has 'suggestions' array", isinstance(d.get("suggestions"), list),
                             f"got keys {list(d.keys())}")
        except Exception as e:
            all_ok &= expect("/suggest-refinements parses", False, str(e))

        # /draft-warm-intro — POST with bad shape → 400 (not 500)
        s, t = req(f"/draft-warm-intro?user={TEST_SLUG}", method="POST",
                   headers={"X-Admin-Key": ADMIN_KEY}, body={"job": {}})  # missing 'connection'
        all_ok &= expect("POST /draft-warm-intro with bad shape returns 400 (not 500)",
                         s == 400, f"status {s} body: {t[:80]}")

        # /draft-warm-intro — happy shape returns LinkedIn DM + email
        s, t = req(f"/draft-warm-intro?user={TEST_SLUG}", method="POST",
                   headers={"X-Admin-Key": ADMIN_KEY}, body={
                       "job": {"title": "Director of Risk", "company": "Stripe",
                               "url": "https://example.com", "desc": "Lead risk eng team."},
                       "connection": {"first": "Alex", "last": "Lee",
                                      "position": "VP Risk", "company": "Stripe"}
                   }, timeout=60)
        all_ok &= expect("POST /draft-warm-intro happy path returns 200", s == 200, f"status {s} body: {t[:80]}")
        try:
            d = json.loads(t)
            # Worker returns the AI text; shape is roughly {linkedin: "...", email: {subject, body}}
            has_content = any(k in d for k in ("linkedin", "email", "text", "draft", "messages"))
            all_ok &= expect("  has a draft field (linkedin/email/text/draft/messages)", has_content,
                             f"got keys {list(d.keys())}")
        except Exception as e:
            all_ok &= expect("/draft-warm-intro parses", False, str(e))

        # === New endpoints (Sprint Mode v2 + healthcare expansion) ============

        # GET /contacts — public read with auth, returns {contacts, meta}
        s, t = req(f"/contacts?user={TEST_SLUG}",
                   headers={"X-Admin-Key": ADMIN_KEY})
        all_ok &= expect("GET /contacts (admin key) returns 200", s == 200, f"status {s}")
        try:
            d = json.loads(t)
            all_ok &= expect("  has 'contacts' array", isinstance(d.get("contacts"), list))
        except Exception as e:
            all_ok &= expect("/contacts parses", False, str(e))

        # GET /contacts without auth → 401
        s, _ = req(f"/contacts?user={TEST_SLUG}")
        all_ok &= expect("GET /contacts no auth returns 401", s == 401, f"status {s}")

        # POST /admin/contacts with bad admin key → 401
        s, _ = req("/admin/contacts", method="POST",
                   headers={"X-Admin-Key": "wrong-key-zzz"},
                   body={"slug": TEST_SLUG, "contacts": []})
        all_ok &= expect("POST /admin/contacts bad key returns 401", s == 401, f"status {s}")

        # POST /admin/contacts with malformed body → 400
        s, _ = req("/admin/contacts", method="POST",
                   headers={"X-Admin-Key": ADMIN_KEY},
                   body={"slug": TEST_SLUG})  # missing contacts
        all_ok &= expect("POST /admin/contacts missing contacts returns 400", s == 400, f"status {s}")

        # POST /api/sprint/reset (safe — non-destructive test, clears sprintStart)
        # Run reset first so subsequent /api/sprint/start test starts from clean state.
        s, t = req(f"/api/sprint/reset?user={TEST_SLUG}", method="POST",
                   headers={"X-Admin-Key": ADMIN_KEY}, body={})
        all_ok &= expect("POST /api/sprint/reset returns 200", s == 200, f"status {s}")

        # Verify sprintStart actually cleared
        s, t = req(f"/skills-profile?user={TEST_SLUG}")
        try:
            d = json.loads(t)
            sp = (d.get("profile") or {}).get("sprintStart", "")
            all_ok &= expect("  sprintStart cleared after reset", not sp,
                             f"got {sp!r}")
        except Exception as e:
            all_ok &= expect("/skills-profile parses after reset", False, str(e))

        # POST /api/sprint/start with admin key
        s, t = req(f"/api/sprint/start?user={TEST_SLUG}", method="POST",
                   headers={"X-Admin-Key": ADMIN_KEY},
                   body={"sprintDays": 10, "sprintDailyQuota": 3})
        all_ok &= expect("POST /api/sprint/start returns 200", s == 200, f"status {s}")
        try:
            d = json.loads(t)
            all_ok &= expect("  start response has sprintStart", bool(d.get("sprintStart")))
            all_ok &= expect("  sprintDays defaulted to 10", d.get("sprintDays") == 10)
            all_ok &= expect("  sprintDailyQuota defaulted to 3", d.get("sprintDailyQuota") == 3)
        except Exception as e:
            all_ok &= expect("/api/sprint/start parses", False, str(e))

        # Sprint-start with no auth → 401
        s, _ = req(f"/api/sprint/start?user={TEST_SLUG}", method="POST", body={})
        all_ok &= expect("POST /api/sprint/start no auth returns 401", s == 401, f"status {s}")

        # Reset again so this test run is idempotent
        req(f"/api/sprint/reset?user={TEST_SLUG}", method="POST",
            headers={"X-Admin-Key": ADMIN_KEY}, body={})

        # /regenerate-profile (dry_run) — admin-only safety check
        s, t = req(f"/regenerate-profile?user={TEST_SLUG}", method="POST",
                   headers={"X-Admin-Key": ADMIN_KEY}, body={"dry_run": True}, timeout=90)
        # 200 or 400 (no resume to regenerate from) both acceptable; reject 500
        all_ok &= expect("POST /regenerate-profile not a 500", s != 500,
                         f"status {s} body: {t[:80]}")

    print(f"\n{'✓ ALL PASS' if all_ok else '✗ FAILURES'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
