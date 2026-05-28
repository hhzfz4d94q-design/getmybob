"""Wizard v3 HTML+CSS+JS block.

Extracted from fetch_jobs.py 2026-05-28 (Phase 3). Appended to per-user
dashboards by generate_dashboard. Pure constant — no imports needed.
"""

WIZARD_V3_BLOCK = r"""
<!-- ====================== Wizard v3 ====================== -->
<style>
  #wiz3-overlay { position:fixed; inset:0; background:rgba(20,22,40,0.55); z-index:2147483600; display:none; align-items:center; justify-content:center; padding:24px; font-family:'Inter',-apple-system,system-ui,sans-serif; }
  #wiz3-overlay.show { display:flex; }
  #wiz3-card { width:min(960px,100%); max-height:92vh; background:#fff; border-radius:14px; box-shadow:0 24px 60px rgba(20,22,40,0.4); display:flex; flex-direction:row; overflow:hidden; }
  @media (max-width:680px) {
    #wiz3-overlay { padding:0; }
    #wiz3-card { flex-direction:column; max-height:100vh; max-width:100vw; border-radius:0; }
    #wiz3-rail { display:none; }
    #wiz3-foot { padding:10px 14px; }
    #wiz3-head { padding:14px 18px; }
    /* Let the whole main section scroll on mobile so footer (Continue) is reachable */
    #wiz3-main { overflow-y:auto; -webkit-overflow-scrolling:touch; }
    #wiz3-body { overflow:visible; flex:0 0 auto; }
  }
  @media (max-width:1024px) {
    body { overflow-x:hidden; }  /* dashboard isn't fully responsive yet; stop awkward sideways scroll */
  }
  #wiz3-rail { flex:0 0 240px; background:#F7F7FB; border-right:1px solid #E5E7EE; padding:24px 18px; overflow-y:auto; }
  #wiz3-rail .wiz3-brand { font-size:13px; font-weight:700; color:#5C5CD6; letter-spacing:.02em; text-transform:uppercase; margin-bottom:18px; }
  #wiz3-rail ol { list-style:none; padding:0; margin:0; }
  #wiz3-rail li { display:flex; align-items:flex-start; gap:10px; padding:8px 6px; border-radius:8px; cursor:pointer; transition:background 0.15s; font-size:13px; color:#444; }
  #wiz3-rail li:hover { background:#EEEEF8; }
  #wiz3-rail li.is-current { background:#EEEEF8; color:#5C5CD6; font-weight:600; }
  #wiz3-rail li.is-done   { color:#0A6B3A; }
  #wiz3-rail li.is-skipped{ color:#9a9aac; }
  #wiz3-rail li[aria-disabled="true"] { cursor:not-allowed; opacity:0.55; }
  #wiz3-rail .wiz3-dot { flex:0 0 18px; width:18px; height:18px; border-radius:50%; border:1.5px solid #C0C4CC; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; color:#888; background:#fff; margin-top:1px; }
  #wiz3-rail li.is-current .wiz3-dot { border-color:#5C5CD6; color:#5C5CD6; background:#fff; }
  #wiz3-rail li.is-done    .wiz3-dot { border-color:#0A6B3A; background:#0A6B3A; color:#fff; }
  #wiz3-rail li.is-skipped .wiz3-dot { border-color:#C0C4CC; background:#fff; color:#aaa; }
  #wiz3-main { flex:1 1 0; display:flex; flex-direction:column; min-height:0; min-width:0; position:relative; overflow:hidden; }
  #wiz3-head { padding:22px 60px 16px 28px; border-bottom:1px solid #F0F0F5; flex:0 0 auto; background:linear-gradient(135deg,#5C5CD6,#7878E0); color:#fff; }
  #wiz3-head .wiz3-step-no { font-size:12px; color:rgba(255,255,255,0.85); letter-spacing:.04em; font-weight:600; text-transform:uppercase; }
  #wiz3-head h2 { margin:6px 0 2px; font-size:21px; font-weight:700; color:#fff; letter-spacing:-0.01em; }
  #wiz3-head .wiz3-sub { font-size:13.5px; color:rgba(255,255,255,0.85); margin:0; }
  #wiz3-body { flex:1 1 auto; padding:18px 28px 18px; overflow-y:auto; min-height:200px; }
  #wiz3-body p { font-size:14px; color:#444; line-height:1.55; }
  #wiz3-body label { display:block; font-size:12px; font-weight:600; color:#444; text-transform:uppercase; letter-spacing:.04em; margin:14px 0 6px; }
  #wiz3-body input[type=text], #wiz3-body input[type=email], #wiz3-body input[type=tel], #wiz3-body input[type=url], #wiz3-body input[type=number], #wiz3-body select { width:100%; padding:9px 11px; font-size:14px; font-family:inherit; border:1px solid #D8DBE3; border-radius:6px; box-sizing:border-box; background:#fff; }
  #wiz3-body input:focus, #wiz3-body select:focus { outline:none; border-color:#5C5CD6; box-shadow:0 0 0 3px rgba(92,92,214,0.12); }
  #wiz3-body .hint { font-size:12px; color:#888; margin-top:-2px; }
  #wiz3-body .radio-list label { display:flex; gap:10px; align-items:flex-start; padding:10px 12px; border:1px solid #D8DBE3; border-radius:8px; margin-bottom:8px; font-size:13.5px; font-weight:500; color:#1A1A2E; text-transform:none; letter-spacing:0; cursor:pointer; }
  #wiz3-body .radio-list label:hover { border-color:#5C5CD6; background:#FAFAFE; }
  #wiz3-body .radio-list input { margin-top:2px; }
  #wiz3-foot { border-top:1px solid #F0F0F5; padding:14px 28px; display:flex; justify-content:space-between; align-items:center; gap:10px; flex:0 0 auto; background:#FAFAFC; }
  #wiz3-foot .wiz3-left, #wiz3-foot .wiz3-right { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  .wiz3-btn { font-family:inherit; font-size:13.5px; font-weight:600; padding:9px 16px; border-radius:6px; cursor:pointer; border:1px solid transparent; transition:background 0.15s, border 0.15s; }
  .wiz3-btn-primary { background:#5C5CD6; color:#fff; border-color:#5C5CD6; }
  .wiz3-btn-primary:hover { background:#4B4BBE; }
  .wiz3-btn-primary[disabled] { opacity:0.55; cursor:not-allowed; }
  .wiz3-btn-ghost { background:transparent; color:#5C5CD6; border-color:#C7C7E8; }
  .wiz3-btn-ghost:hover { background:#EEEEF8; }
  .wiz3-btn-quiet { background:transparent; color:#888; border-color:transparent; }
  .wiz3-btn-quiet:hover { color:#5C5CD6; }
  .wiz3-msg { font-size:12.5px; padding:8px 12px; border-radius:6px; margin-top:12px; display:none; }
  .wiz3-msg.show { display:block; }
  .wiz3-msg.ok  { background:#ECFDF5; color:#0A6B3A; }
  .wiz3-msg.err { background:#FEF2F2; color:#B91C1C; }
  .wiz3-msg.info{ background:#EEEEF8; color:#4B4BBE; }
  #wiz3-close { position:absolute; top:8px; right:10px; background:rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.3); border-radius:10px; width:44px; height:44px; font-size:24px; line-height:1; color:#fff; cursor:pointer; z-index:10; display:flex; align-items:center; justify-content:center; }
  #wiz3-close:hover { background:rgba(255,255,255,0.32); border-color:rgba(255,255,255,0.5); }
  .wiz3-chip-row { display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 10px; }
  .wiz3-chip { background:#EEEEF8; color:#4B4BBE; font-size:12px; padding:4px 9px; border-radius:12px; }
  /* Hide old wizard markup so nothing leaks through */
  #gmj-wizard.wiz-overlay { display:none !important; }
</style>

<div id="wiz3-overlay" role="dialog" aria-modal="true" aria-labelledby="wiz3-h2">
  <div id="wiz3-card">
    <aside id="wiz3-rail">
      <div class="wiz3-brand">getmemyjob setup</div>
      <ol id="wiz3-rail-list"></ol>
    </aside>
    <section id="wiz3-main" style="position:relative;">
      <button id="wiz3-close" type="button" aria-label="Close wizard">&times;</button>
      <header id="wiz3-head">
        <div class="wiz3-step-no" id="wiz3-step-no">Step 1 of 9</div>
        <h2 id="wiz3-h2">Welcome</h2>
        <p class="wiz3-sub" id="wiz3-sub"></p>
      </header>
      <div id="wiz3-body"></div>
      <footer id="wiz3-foot">
        <div class="wiz3-left">
          <button class="wiz3-btn wiz3-btn-quiet" id="wiz3-back" type="button">&larr; Back</button>
        </div>
        <div class="wiz3-right">
          <button class="wiz3-btn wiz3-btn-quiet" id="wiz3-skip" type="button">Skip</button>
          <button class="wiz3-btn wiz3-btn-primary" id="wiz3-continue" type="button">Continue &rarr;</button>
        </div>
      </footer>
    </section>
  </div>
</div>

<script>
(function () {
  if (window.WizV3) return; // idempotent
  const STATE_KEY = "gmj_wizard_state_v3";
  const WORKER = "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev";
  const SLUG = (typeof USER_SLUG === "string" && USER_SLUG) ? USER_SLUG : (window.USER_SLUG || "");

  // ---- State persistence ----
  function loadState() {
    try {
      const raw = localStorage.getItem(STATE_KEY);
      if (raw) {
        const s = JSON.parse(raw);
        if (s && typeof s === "object") return s;
      }
    } catch (e) {}
    return { currentStep: "welcome", completed: [], skipped: [], data: {}, finished: false };
  }
  function saveState(s) {
    try { localStorage.setItem(STATE_KEY, JSON.stringify(s)); } catch (e) {}
  }
  let state = loadState();
  // Migrate v2 → v3: if user already finished v2, mark v3 finished too so we don't bug them again.
  try {
    const seenV2 = localStorage.getItem("gmj_wizard_seen_v2");
    if (seenV2 && !state.finished && !state.completed.length) {
      state.finished = true;
      saveState(state);
    }
  } catch (e) {}

  // ---- Helpers ----
  function getEditKey() {
    try {
      return localStorage.getItem("htj_resume_key_" + SLUG) || localStorage.getItem("htj_resume_key") || "";
    } catch (e) { return ""; }
  }
  async function getProfile() {
    try {
      const r = await fetch(WORKER + "/skills-profile?user=" + encodeURIComponent(SLUG), { cache: "no-store" });
      const j = await r.json();
      return (j && j.profile) || {};
    } catch (e) { return {}; }
  }
  async function patchProfile(patchFields) {
    const ek = getEditKey();
    const adminKey = (function(){ try { return localStorage.getItem("htj_admin_key") || ""; } catch(e){ return ""; } })();
    if (!ek && !adminKey) throw new Error("Not signed in to this browser");
    const headers = { "Content-Type": "application/json" };
    if (ek) headers["X-Edit-Key"] = ek; else headers["X-Admin-Key"] = adminKey;
    const r = await fetch(WORKER + "/skills-profile?user=" + encodeURIComponent(SLUG), {
      method: "POST",
      headers: headers,
      body: JSON.stringify({ patchFields }),
    });
    if (!r.ok) {
      // If edit key was sent and rejected, retry with admin key (if we have one)
      if (r.status === 401 && ek && adminKey) {
        const r2 = await fetch(WORKER + "/skills-profile?user=" + encodeURIComponent(SLUG), {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Admin-Key": adminKey },
          body: JSON.stringify({ patchFields }),
        });
        if (r2.ok) return r2.json();
        throw new Error(r2.status === 401 ? "Session expired — please re-authenticate at /account.html" : "HTTP " + r2.status);
      }
      throw new Error(r.status === 401 ? "Session expired — please re-authenticate at /account.html" : "HTTP " + r.status);
    }
    return r.json();
  }
  function escHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
  }
  function setMsg(host, type, text) {
    let el = host.querySelector(".wiz3-msg");
    if (!el) {
      el = document.createElement("div");
      el.className = "wiz3-msg";
      host.appendChild(el);
    }
    el.className = "wiz3-msg show " + type;
    el.textContent = text;
  }

  // ---- Bullseye picker (used by pick-titles / pick-industries / pick-skills) ----
  // Renders a chip-based picker with a cap. Each chip is removable.
  // Input/Add button are disabled when at cap. Counter goes red over cap.
  // Exposes body.__bullseyeValues() returning the current array.
  function renderBullseye(body, opts) {
    const max = opts.max;
    let items = (opts.current || []).map(x => String(x).toLowerCase().trim()).filter(Boolean);
    // Dedupe preserving order
    const seen = new Set(); items = items.filter(x => { if (seen.has(x)) return false; seen.add(x); return true; });

    body.innerHTML = ''
      + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
      +   '<div style="font-size:13px;color:#555;">Pick <b>up to ' + max + '</b></div>'
      +   '<div class="bullseye-count" style="font-size:13px;font-weight:600;">0 / ' + max + '</div>'
      + '</div>'
      + '<div class="bullseye-chips" style="display:flex;flex-wrap:wrap;gap:6px;min-height:36px;padding:10px;border:1px solid #e0e2ed;border-radius:8px;background:#fafbff;"></div>'
      + '<div style="display:flex;gap:6px;margin-top:10px;">'
      +   '<input type="text" class="bullseye-input" placeholder="' + (opts.placeholder || 'Add an item…') + '" style="flex:1;padding:8px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:13px;">'
      +   '<button type="button" class="bullseye-add wiz3-btn wiz3-btn-ghost" style="padding:6px 14px;">+ Add</button>'
      + '</div>'
      + (opts.hint ? '<div style="font-size:12px;color:#888;margin-top:8px;">' + opts.hint + '</div>' : '');

    const chipsEl   = body.querySelector('.bullseye-chips');
    const inputEl   = body.querySelector('.bullseye-input');
    const addBtn    = body.querySelector('.bullseye-add');
    const counterEl = body.querySelector('.bullseye-count');

    function refresh() {
      chipsEl.innerHTML = '';
      if (!items.length) {
        const empty = document.createElement('div');
        empty.style.cssText = 'color:#999;font-size:12.5px;font-style:italic;padding:2px;';
        empty.textContent = '(no picks yet — add some below)';
        chipsEl.appendChild(empty);
      }
      items.forEach((item, idx) => {
        const chip = document.createElement('span');
        chip.style.cssText = 'display:inline-flex;align-items:center;gap:5px;padding:5px 10px;background:#EEEEF8;color:#4B4BBE;border:1px solid #c8cde6;border-radius:14px;font-size:12.5px;';
        const txt = document.createElement('span');
        txt.textContent = item;
        chip.appendChild(txt);
        const x = document.createElement('button');
        x.type = 'button';
        x.textContent = '×';
        x.setAttribute('aria-label', 'Remove');
        x.style.cssText = 'background:none;border:none;cursor:pointer;color:#7c7cd1;font-size:16px;line-height:1;padding:0;margin-left:2px;';
        x.addEventListener('click', () => { items.splice(idx, 1); refresh(); });
        chip.appendChild(x);
        chipsEl.appendChild(chip);
      });
      counterEl.textContent = items.length + ' / ' + max;
      counterEl.style.color = items.length > max ? '#B91C1C' : (items.length === max ? '#666' : '#5C5CD6');
      const atCap = items.length >= max;
      inputEl.disabled = atCap;
      addBtn.disabled = atCap;
      inputEl.style.opacity = atCap ? '0.5' : '1';
    }
    function tryAdd() {
      const v = (inputEl.value || '').trim().toLowerCase();
      if (!v || items.length >= max || items.includes(v)) { inputEl.value = ''; return; }
      items.push(v); inputEl.value = ''; refresh();
    }
    addBtn.addEventListener('click', tryAdd);
    inputEl.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); tryAdd(); } });
    refresh();
    body.__bullseyeValues = () => items.slice();
    body.__bullseyeMax = max;
  }

  // ---- Step definitions ----
  // Contract: { key, title, subtitle, optional, render(body, state, ctx),
  //             validate(state) -> "" or err, save(state) -> Promise, isComplete(state) }
  const STEPS = [
    {
      key: "welcome",
      title: "Welcome to getmemyjob",
      subtitle: "We'll have your tailored dashboard ready in about 5 minutes.",
      optional: true,
      render(body, st) {
        body.innerHTML =
          '<p>Quick setup so we can match you to jobs that actually fit. You can stop any time — we\'ll remember exactly where you left off.</p>' +
          '<p><strong>What\'s next:</strong></p>' +
          '<ul style="font-size:14px;color:#444;line-height:1.7;padding-left:18px;">' +
            '<li>Upload your resume so the AI can read your background</li>' +
            '<li>Confirm your target titles, industries, locations, and remote preference</li>' +
            '<li>Install the Helper extension so we can auto-fill 18 of 25 fields on apply forms</li>' +
            '<li>Tell us your daily application target so we can show you a focus list</li>' +
          '</ul>';
      },
      save() { return Promise.resolve(); },
    },
    {
      key: "upload-resume",
      title: "Upload your resume",
      subtitle: "We'll extract your skills, titles, industries, and contact fields.",
      optional: true,
      render(body) {
        body.innerHTML =
          '<p>Click below to open the Resume panel. Upload a PDF or DOCX — the AI parses it in ~10 seconds.</p>' +
          '<button type="button" class="wiz3-btn wiz3-btn-ghost" id="wiz3-open-resume">Open Resume panel</button>' +
          '<p style="font-size:12px;color:#888;margin-top:12px;">When you close the panel, we\'ll move you to the next step automatically.</p>';
        const btn = body.querySelector("#wiz3-open-resume");
        if (btn) btn.addEventListener("click", () => {
          try {
            // Hide the wizard overlay so the resume modal isn't visually blocked
            const wiz = document.getElementById("wiz3-overlay");
            if (wiz) wiz.classList.remove("show");
            if (typeof openResumeModal === "function") openResumeModal();
            // When the resume modal closes, re-open the wizard. The modal's close
            // calls closeResumeModal — observe its display change.
            const rm = document.getElementById("resume-modal");
            if (rm) {
              const obs = new MutationObserver(() => {
                if (rm.style.display === "none" || !rm.classList.contains("show")) {
                  obs.disconnect();
                  if (wiz) wiz.classList.add("show");
                }
              });
              obs.observe(rm, { attributes: true, attributeFilter: ["style", "class"] });
            }
          } catch (e) { console.warn("open resume from wizard:", e); }
        });
      },
      async save() {
        // Try to verify a resume was actually uploaded
        try {
          const p = await getProfile();
          if (p && (p.primaryRole || p.targetTitles || p.industries)) return;
        } catch (e) {}
      },
    },
    {
      key: "your-bullseye",
      title: "Your bullseye — what you want the matcher to look for",
      subtitle: "5 titles / 5 industries / 15 skills / 15 companies. Trim aggressively — sharp picks beat vague ones.",
      async render(body, st) {
        body.innerHTML =
          '<div id="bs-section-titles" style="margin-bottom:24px;padding-bottom:18px;border-bottom:1px solid #eee;"><h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">1. Target job titles (max 5)</h3><p style="margin:0 0 10px;font-size:12px;color:#666;">The matcher looks for these as a fallback signal. Lowercase, multi-word.</p><div id="bs-titles-host"></div></div>' +
          '<div id="bs-section-industries" style="margin-bottom:24px;padding-bottom:18px;border-bottom:1px solid #eee;"><h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">2. Industries (max 5)</h3><p style="margin:0 0 10px;font-size:12px;color:#666;">Industries you want your NEXT job in — not every industry you have ever touched. DOMINANT match signal.</p><div id="bs-industries-host"></div></div>' +
          '<div id="bs-section-skills" style="margin-bottom:24px;padding-bottom:18px;border-bottom:1px solid #eee;"><h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">3. Skills (max 15)</h3><p style="margin:0 0 10px;font-size:12px;color:#666;">Distinct, signal-dense terms. Skip generic words. DOMINANT match signal alongside industry.</p><div id="bs-skills-host"></div></div>' +
          '<div id="bs-section-companies"><h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">4. Target companies (optional refresh)</h3><p style="margin:0 0 10px;font-size:12px;color:#666;">AI will re-derive 20 companies from your bullseye above. Click below to see the diff.</p><div id="bs-companies-host"></div></div>';

        const p = await getProfile();
        // 1. Titles
        renderBullseye(body.querySelector("#bs-titles-host"), {
          max: 5, current: p.targetTitles || [],
          placeholder: "e.g. vp of product management",
          hint: "Lowercase, multi-word titles match best."
        });
        // 2. Industries
        renderBullseye(body.querySelector("#bs-industries-host"), {
          max: 5, current: p.industries || [],
          placeholder: "e.g. healthcare technology",
          hint: "Tight industry choice = less noise."
        });
        // 3. Skills (merge keywords + technologies + frameworks)
        const merged = [].concat(p.keywords || [], p.technologies || [], p.frameworks || []);
        renderBullseye(body.querySelector("#bs-skills-host"), {
          max: 15, current: merged,
          placeholder: "e.g. digital transformation",
          hint: "These boost a job\'s score when found in title or description."
        });
        // 4. Companies — same inline UI as original pick-companies step
        const cHost = body.querySelector("#bs-companies-host");
        cHost.innerHTML =
          '<button type="button" id="bs-co-ask" class="wiz3-btn wiz3-btn-ghost">Show me what AI would suggest</button>' +
          '<div id="bs-co-result" style="margin-top:14px;"></div>' +
          '<p style="font-size:11px;color:#888;margin-top:10px;">Skipping this section keeps your current target companies.</p>';
        const askBtn = cHost.querySelector("#bs-co-ask");
        const out = cHost.querySelector("#bs-co-result");
        askBtn.addEventListener("click", async () => {
          askBtn.disabled = true; askBtn.textContent = "Asking AI...";
          const ek = getEditKey();
          const adminKey = (function(){ try { return localStorage.getItem("htj_admin_key") || ""; } catch(e){ return ""; } })();
          if (!ek && !adminKey) {
            out.innerHTML = '<div style="padding:10px 12px;background:#fef3c7;border:1px solid #fcd34d;border-radius:6px;font-size:12.5px;color:#78350f;">⚠ You\'re not signed in to this browser. Open <a href="/account.html" style="color:#5C5CD6;font-weight:600;">your account page</a> to paste your invite key, then come back. Skipping this step keeps your current 20 target companies.</div>';
            askBtn.disabled = false; askBtn.textContent = "Show me what AI would suggest"; return;
          }
          const authHdr = ek ? { "X-Edit-Key": ek } : { "X-Admin-Key": adminKey };
          try {
            let r = await fetch(WORKER_BASE + "/regenerate-companies" + USER_QS, {
              method: "POST",
              headers: Object.assign({ "Content-Type": "application/json" }, authHdr),
              body: JSON.stringify({ dry_run: true })
            });
            // 401 with edit key? retry with admin key if available
            if (r.status === 401 && ek && adminKey) {
              r = await fetch(WORKER_BASE + "/regenerate-companies" + USER_QS, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-Admin-Key": adminKey },
                body: JSON.stringify({ dry_run: true })
              });
            }
            const data = await r.json();
            if (!r.ok) {
              if (r.status === 401) {
                out.innerHTML = '<div style="padding:10px 12px;background:#fef3c7;border:1px solid #fcd34d;border-radius:6px;font-size:12.5px;color:#78350f;">⚠ Your session expired. Open <a href="/account.html" style="color:#5C5CD6;font-weight:600;">your account page</a> to re-enter your invite key, then come back. <strong>You can skip this section</strong> and your current target companies will be kept.</div>';
              } else {
                out.innerHTML = '<em style="color:#B91C1C;">Failed: ' + (data.error || r.status) + '</em>';
              }
              askBtn.disabled = false; askBtn.textContent = "Try again";
              return;
            }
            const removing = (data.diff && data.diff.removing) || [];
            const adding = (data.diff && data.diff.adding) || [];
            const keeping = (data.diff && data.diff.keeping) || [];
            const chip = (label, color, bg, border) => '<span style="display:inline-block;padding:3px 9px;background:' + bg + ';color:' + color + ';border:1px solid ' + border + ';border-radius:12px;font-size:12px;margin:2px;">' + label + '</span>';
            const remHtml = removing.map(c => chip((c && c.name ? c.name : c) + " x", "#B91C1C", "#FEF2F2", "#fecaca")).join('') || '<em style="font-size:12px;color:#888;">(none)</em>';
            const addHtml = adding.map(c => chip(c.name + " +", "#0a6b3a", "#ECFDF5", "#a7f3d0")).join('') || '<em style="font-size:12px;color:#888;">(none)</em>';
            const keepHtml = keeping.map(c => chip(c.name, "#3F3F46", "#F4F4F5", "#e4e4e7")).join('') || '<em style="font-size:12px;color:#888;">(no overlap)</em>';
            out.innerHTML =
              '<div style="font-size:13px;color:#555;margin-bottom:10px;"><strong>' + data.diff.summary + '</strong></div>' +
              '<div style="margin-bottom:10px;"><div style="font-size:12px;font-weight:600;color:#B91C1C;margin-bottom:4px;">Removing (' + removing.length + ')</div><div style="line-height:1.7;">' + remHtml + '</div></div>' +
              '<div style="margin-bottom:10px;"><div style="font-size:12px;font-weight:600;color:#0a6b3a;margin-bottom:4px;">Adding (' + adding.length + ')</div><div style="line-height:1.7;">' + addHtml + '</div></div>' +
              '<div style="margin-bottom:14px;"><div style="font-size:12px;font-weight:600;color:#3F3F46;margin-bottom:4px;">Keeping (' + keeping.length + ')</div><div style="line-height:1.7;">' + keepHtml + '</div></div>' +
              '<button type="button" id="bs-co-confirm" class="wiz3-btn wiz3-btn-primary" style="background:#5C5CD6;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">Save these ' + ((data.proposed || []).length) + ' companies</button>';
            askBtn.textContent = "Re-ask AI";
            askBtn.disabled = false;
            const confirmBtn = out.querySelector("#bs-co-confirm");
            confirmBtn.addEventListener("click", async () => {
              confirmBtn.disabled = true; confirmBtn.textContent = "Saving...";
              try {
                let r2 = await fetch(WORKER_BASE + "/regenerate-companies" + USER_QS, {
                  method: "POST",
                  headers: Object.assign({ "Content-Type": "application/json" }, authHdr),
                  body: JSON.stringify({ dry_run: false })
                });
                if (r2.status === 401 && ek && adminKey) {
                  r2 = await fetch(WORKER_BASE + "/regenerate-companies" + USER_QS, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", "X-Admin-Key": adminKey },
                    body: JSON.stringify({ dry_run: false })
                  });
                }
                const d2 = await r2.json();
                if (!r2.ok) {
                  confirmBtn.textContent = r2.status === 401 ? "Session expired — see /account.html" : ("Failed: " + (d2.error || r2.status));
                  confirmBtn.disabled = false; return;
                }
                confirmBtn.textContent = "✓ Saved " + ((d2.profile && d2.profile.targetCompanies || []).length) + " companies";
                st.data.companies_saved = true;
              } catch (e) { confirmBtn.textContent = "Network error"; }
            });
          } catch (e) { out.innerHTML = '<em style="color:#B91C1C;">' + (e.message || e) + '</em>'; askBtn.disabled = false; askBtn.textContent = "Try again"; }
        });
      },
      async save(st, ctx) {
        // Collect from all 3 picker sections (companies is async via button — not blocking save)
        let tItems = ((ctx.body.querySelector("#bs-titles-host") || {}).__bullseyeValues || (() => []))();
        let iItems = ((ctx.body.querySelector("#bs-industries-host") || {}).__bullseyeValues || (() => []))();
        let sItems = ((ctx.body.querySelector("#bs-skills-host") || {}).__bullseyeValues || (() => []))();
        // Minimum gates — these we still enforce (a profile with 0 titles or 0
        // industries gives the matcher nothing to work with).
        if (tItems.length === 0) { setMsg(ctx.body, "err", "Pick at least 1 title."); throw new Error("empty titles"); }
        if (iItems.length === 0) { setMsg(ctx.body, "err", "Pick at least 1 industry."); throw new Error("empty industries"); }
        // Over-cap is no longer a hard block — auto-trim to the first N and
        // tell the user. Previously this threw, which locked over-cap users
        // out of the wizard forever (bug 2026-05-28).
        const trimNotes = [];
        if (tItems.length > 5)  { trimNotes.push("titles: " + tItems.length + " → 5"); tItems = tItems.slice(0, 5); }
        if (iItems.length > 5)  { trimNotes.push("industries: " + iItems.length + " → 5"); iItems = iItems.slice(0, 5); }
        if (sItems.length > 15) { trimNotes.push("skills: " + sItems.length + " → 15"); sItems = sItems.slice(0, 15); }
        if (trimNotes.length) {
          setMsg(ctx.body, "warn", "Auto-trimmed to caps (" + trimNotes.join("; ") + "). You can adjust later from /account.html.");
        }
        // Patch all bullseye fields in one go
        await patchProfile({
          targetTitles: tItems,
          industries: iItems,
          keywords: sItems,
          technologies: [],
          frameworks: []
        });
        st.data.targetTitles = tItems;
        st.data.industries = iItems;
        st.data.skills = sItems;
      },
    },
    {
      key: "where-you-work",
      title: "Where you want to work",
      subtitle: "Locations + remote preference + company sizes.",
      optional: true,
      async render(body, st) {
        body.innerHTML =
          '<div style="margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid #eee;">' +
            '<h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">1. Locations + remote</h3>' +
            '<label for="wiz3-locs">Preferred locations (comma-separated)</label>' +
            '<input type="text" id="wiz3-locs" placeholder="e.g. New York City, Remote (US)">' +
            '<div class="hint">Cities, states, or country regions.</div>' +
            '<label for="wiz3-remote" style="margin-top:10px;display:block;">Remote preference</label>' +
            '<select id="wiz3-remote">' +
              '<option value="any">Any — onsite, hybrid, or remote</option>' +
              '<option value="hybrid">Hybrid — prefer some in-office days</option>' +
              '<option value="onsite">Onsite — in-office is fine</option>' +
              '<option value="remote-only">Remote only — must be fully remote</option>' +
            '</select>' +
          '</div>' +
          '<div>' +
            '<h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">2. Company size mix (must add to 100)</h3>' +
            ['startup','midsize','large','consulting'].map(k => {
              const labels = {
                startup:    'Startups (under 500)',
                midsize:    'Mid-size (500-10k)',
                large:      'Large (10k+ / F500)',
                consulting: 'Consulting firms (Accenture, Capco, Deloitte, etc.)'
              };
              const defaults = {startup:33, midsize:33, large:34, consulting:0};
              return '<label>' + labels[k] + ' <span style="float:right;font-weight:500;color:#5C5CD6;" id="wiz-mix-' + k + '-val">' + defaults[k] + '%</span></label>' +
                     '<input type="range" id="wiz-mix-' + k + '" min="0" max="100" step="5" value="' + defaults[k] + '" oninput="wizMixOnSlide(\'' + k + '\')" style="width:100%;">';
            }).join('') +
            '<div style="font-size:11px;color:#888;margin-top:4px;">Consulting at 0% blocks consulting firms entirely. Above 0%, they appear softer down-ranked. Set to ~30% if you actively want consulting roles (they hire faster).</div>' +
            '<div id="wiz-mix-total" style="margin-top:8px;font-size:13px;font-weight:600;text-align:right;">Total: 100%</div>' +
          '</div>';
        const p = await getProfile();
        // Locations
        const locsEl = body.querySelector("#wiz3-locs");
        const remoteEl = body.querySelector("#wiz3-remote");
        if (locsEl && Array.isArray(p.preferredLocations)) locsEl.value = p.preferredLocations.join(", ");
        if (st.data.preferredLocations) locsEl.value = st.data.preferredLocations;
        if (remoteEl) {
          let rp = p.remotePreference || (p.remotePreferred ? "remote-only" : "any");
          if (st.data.remotePreference) rp = st.data.remotePreference;
          remoteEl.value = rp;
        }
        // Size mix (now 4-way including consulting)
        const mix = (st.data.companySizeMix) || p.companySizeMix || { startup:33, midsize:33, large:34, consulting:0 };
        // Heal legacy 3-way mix: if consulting is missing, default to 0 (preserves user's existing intent)
        if (mix.consulting == null) mix.consulting = 0;
        ['startup','midsize','large','consulting'].forEach(k => {
          const el = body.querySelector('#wiz-mix-' + k);
          if (el) { el.value = mix[k] || 0; body.querySelector('#wiz-mix-' + k + '-val').textContent = (mix[k] || 0) + '%'; }
        });
        _wizMixRebalance('startup');
      },
      async save(st, ctx) {
        // Locations
        const locs = (ctx.body.querySelector("#wiz3-locs") || {}).value || "";
        const remote = (ctx.body.querySelector("#wiz3-remote") || {}).value || "any";
        const preferredLocations = locs.split(",").map(s => s.trim()).filter(Boolean);
        // Sizes (4-way: startup / midsize / large / consulting)
        const mix = {};
        ['startup','midsize','large','consulting'].forEach(k => { mix[k] = parseInt((ctx.body.querySelector('#wiz-mix-' + k) || {}).value || 0, 10); });
        await patchProfile({
          preferredLocations: preferredLocations,
          remotePreference: remote,
          companySizeMix: mix
        });
        st.data.preferredLocations = locs;
        st.data.remotePreference = remote;
        st.data.companySizeMix = mix;
      },
    },
    {
      key: "scoring-tune",
      title: "How we score job matches",
      subtitle: "Two layers: PRIORITY (how much you care about each signal, must sum to 100) and RELIABILITY (how much to trust each signal — title-wording varies between companies so it\'s less reliable than industry+skills).",
      optional: true,
      async render(body, st) {
        body.innerHTML =
          '<div style="margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid #eee;">' +
            '<h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">1. Priority weights (sum to 100)</h3>' +
            ['titles','industry','skills'].map(k => {
              const labels = {titles:"Title fit", industry:"Industry fit", skills:"Skills fit"};
              const defaults = {titles:50, industry:25, skills:25};
              return '<label>' + labels[k] + ' <span style="float:right;font-weight:500;color:#5C5CD6;" id="wiz3-w-' + k + '-val">' + defaults[k] + '%</span></label>' +
                     '<input type="range" id="wiz3-w-' + k + '" min="0" max="100" step="5" value="' + defaults[k] + '" style="width:100%;">';
            }).join('') +
            '<div id="wiz3-w-total" style="margin-top:8px;font-size:13px;font-weight:600;text-align:right;">Total: 100%</div>' +
          '</div>' +
          '<div>' +
            '<h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">2. Signal reliability (independent)</h3>' +
            ['title','industry','skills'].map(k => {
              const labels = {title:'Title-wording reliability', industry:'Industry reliability', skills:'Skills reliability'};
              const hints  = {title: 'Low = ignore wording (default 40%)', industry: 'High = require industry overlap', skills: 'High = require skill keywords in JD'};
              const defaults = {title:40, industry:100, skills:100};
              return '<div style="margin-bottom:14px;">' +
                     '<label style="display:flex;justify-content:space-between;align-items:baseline;">' +
                       '<span>' + labels[k] + '</span>' +
                       '<span style="font-weight:600;color:#5C5CD6;" id="wiz3-stab-' + k + '-val">' + defaults[k] + '%</span>' +
                     '</label>' +
                     '<input type="range" id="wiz3-stab-' + k + '" min="0" max="100" step="5" value="' + defaults[k] + '" style="width:100%;">' +
                     '<div class="hint" style="font-size:11.5px;color:#888;">' + hints[k] + '</div>' +
                     '</div>';
            }).join('') +
          '</div>';
        const p = await getProfile();
        // Match weights
        const w = (st.data.matchWeights) || p.matchWeights || { titles:50, industry:25, skills:25 };
        ['titles','industry','skills'].forEach(k => {
          const el = body.querySelector('#wiz3-w-' + k);
          if (el) { el.value = w[k] || 0; body.querySelector('#wiz3-w-' + k + '-val').textContent = (w[k] || 0) + '%'; }
        });
        const recomputeTotal = () => {
          let t = 0;
          ['titles','industry','skills'].forEach(k => { t += parseInt((body.querySelector('#wiz3-w-' + k) || {}).value || 0, 10); });
          const totalEl = body.querySelector('#wiz3-w-total');
          if (totalEl) { totalEl.textContent = 'Total: ' + t + '%'; totalEl.style.color = (t === 100) ? '#0A6B3A' : '#B91C1C'; }
        };
        ['titles','industry','skills'].forEach(k => {
          const el = body.querySelector('#wiz3-w-' + k);
          if (el) el.addEventListener('input', () => { body.querySelector('#wiz3-w-' + k + '-val').textContent = el.value + '%'; recomputeTotal(); });
        });
        recomputeTotal();
        // Stability
        const s = (st.data.signalStability) || p.signalStability || { title: 40, industry: 100, skills: 100 };
        ['title','industry','skills'].forEach(k => {
          const el = body.querySelector('#wiz3-stab-' + k);
          const v = (s[k] != null) ? s[k] : ({title:40,industry:100,skills:100}[k]);
          if (el) { el.value = v; body.querySelector('#wiz3-stab-' + k + '-val').textContent = v + '%'; }
        });
        ['title','industry','skills'].forEach(k => {
          const el = body.querySelector('#wiz3-stab-' + k);
          if (el) el.addEventListener('input', () => { body.querySelector('#wiz3-stab-' + k + '-val').textContent = el.value + '%'; });
        });
      },
      validate(st, ctx) {
        const w = {};
        ['titles','industry','skills'].forEach(k => { w[k] = parseInt((ctx.body.querySelector('#wiz3-w-' + k) || {}).value || 0, 10); });
        const t = w.titles + w.industry + w.skills;
        if (t !== 100) return "Priority weights must add to 100. Currently: " + t + ".";
        return "";
      },
      async save(st, ctx) {
        const w = {}; ['titles','industry','skills'].forEach(k => { w[k] = parseInt((ctx.body.querySelector('#wiz3-w-' + k) || {}).value || 0, 10); });
        const s = {}; ['title','industry','skills'].forEach(k => { s[k] = parseInt((ctx.body.querySelector('#wiz3-stab-' + k) || {}).value || 0, 10); });
        await patchProfile({ matchWeights: w, signalStability: s });
        st.data.matchWeights = w; st.data.signalStability = s;
      },
    },
    {
      key: "daily-workflow",
      title: "Daily workflow",
      subtitle: "How many to apply to each day + how fresh jobs need to be.",
      optional: true,
      render(body, st) {
        body.innerHTML =
          '<div style="margin-bottom:18px;padding-bottom:18px;border-bottom:1px solid #eee;">' +
            '<label for="wiz3-target"><strong>Applications per day</strong></label>' +
            '<input type="number" id="wiz3-target" min="1" max="50" value="5" style="max-width:140px;">' +
            '<div class="hint">5 per day is a healthy default.</div>' +
          '</div>' +
          '<div>' +
            '<label for="wiz3-recency"><strong>Recency window</strong></label>' +
            '<select id="wiz3-recency">' +
              '<option value="3">Last 3 days</option>' +
              '<option value="7" selected>Last 7 days</option>' +
              '<option value="14">Last 14 days</option>' +
              '<option value="30">Last 30 days</option>' +
            '</select>' +
            '<div class="hint">Older jobs are usually filled or stale.</div>' +
          '</div>';
        let cur = 5;
        try { cur = parseInt(localStorage.getItem("gmj_daily_target_" + SLUG) || "5", 10); } catch (e) {}
        if (st.data.dailyTarget) cur = st.data.dailyTarget;
        body.querySelector("#wiz3-target").value = cur;
        let rec = "7"; try { rec = localStorage.getItem("gmj_recency_window_" + SLUG) || "7"; } catch(e) {}
        if (st.data.recencyWindow) rec = st.data.recencyWindow;
        body.querySelector("#wiz3-recency").value = rec;
      },
      async save(st, ctx) {
        const target = parseInt((ctx.body.querySelector("#wiz3-target") || {}).value || 5, 10);
        const recency = (ctx.body.querySelector("#wiz3-recency") || {}).value || "7";
        st.data.dailyTarget = target;
        st.data.recencyWindow = recency;
        try { localStorage.setItem("gmj_daily_target_" + SLUG, String(target)); } catch (e) {}
        try { localStorage.setItem("gmj_recency_window_" + SLUG, recency); } catch (e) {}
        await patchProfile({ dailyTarget: target, recencyWindow: recency });
      },
    },
    {
      key: "addons",
      title: "Optional add-ons",
      subtitle: "Each is optional. Set up later from the More menu if you skip now.",
      optional: true,
      render(body, st) {
        body.innerHTML =
          '<div style="margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid #eee;">' +
            '<h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">1. Browser extension (Chrome/Firefox)</h3>' +
            '<p style="font-size:12px;color:#666;margin:0 0 10px;">Marks jobs across LinkedIn / Indeed / company sites so you do not double-apply.</p>' +
            '<a href="extension.zip" class="wiz3-btn wiz3-btn-ghost" download>Download Chrome extension</a> ' +
            '<a href="extension-firefox.zip" class="wiz3-btn wiz3-btn-ghost" download>Download Firefox extension</a>' +
          '</div>' +
          '<div style="margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid #eee;">' +
            '<h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">2. Contact / application profile</h3>' +
            '<p style="font-size:12px;color:#666;margin:0 0 10px;">Used to pre-fill application materials. Edit later from the Account page.</p>' +
            '<button type="button" class="wiz3-btn wiz3-btn-ghost" id="wiz3-open-app-profile">Open profile editor</button>' +
          '</div>' +
          '<div>' +
            '<h3 style="margin:0 0 6px;font-size:14px;color:#1a1a2e;">3. LinkedIn Connections (CSV)</h3>' +
            '<p style="font-size:12px;color:#666;margin:0 0 10px;">Upload your Connections.csv from LinkedIn to surface warm-intro paths for jobs at companies where you know people.</p>' +
            '<button type="button" class="wiz3-btn wiz3-btn-ghost" id="wiz3-open-contacts">Open LinkedIn Contacts panel</button>' +
          '</div>';
        const apBtn = body.querySelector("#wiz3-open-app-profile");
        if (apBtn) apBtn.addEventListener("click", () => { try { if (typeof window.openAccountModal === "function") window.openAccountModal(); else window.open("/account.html", "_blank"); } catch (e) {} });
        const lkBtn = body.querySelector("#wiz3-open-contacts");
        if (lkBtn) lkBtn.addEventListener("click", () => { try { if (typeof openContactsModal === "function") openContactsModal(); } catch (e) {} });
      },
      save() { return Promise.resolve(); },
    },
    {
      key: "pick-blocks",
      title: "Things to never show me (optional)",
      subtitle: "Words that, if found in a job title, will block that job — UNLESS the title also contains a seniority signal (VP/Director/Head/etc.). Edit only if the AI added something too aggressive.",
      optional: true,
      async render(body) {
        const p = await getProfile();
        renderBullseye(body, {
          max: 20,  // soft cap; mostly to keep the list manageable
          current: p.negativeKeywords || [],
          placeholder: "e.g. intern",
          hint: "Default keepers: intern, entry level, new grad. AVOID: 'assistant' (kills Assistant VP), 'associate' (kills Associate Director), 'staff' (kills Chief of Staff), 'analyst' (kills Senior Analyst). The scorer skips blocks if the title has any senior signal, so 'Associate Director' won't get killed by 'associate' even if you keep it — but cleaner to remove ambiguous terms.",
        });
      },
      async save(st, ctx) {
        const items = (ctx.body.__bullseyeValues || (() => []))();
        // Normalize: lowercase, trim, dedupe (renderBullseye already does this; defensive copy)
        const normalized = Array.from(new Set(items.map(s => (s || "").toLowerCase().trim()).filter(Boolean)));
        await patchProfile({ negativeKeywords: normalized });
        st.data.negativeKeywords = normalized;
      },
    },
    {
      key: "done",
      title: "All set",
      subtitle: "We'll build your tailored dashboard now.",
      optional: false,
      render(body) {
        body.innerHTML =
          '<p>Your settings are saved. The next job-refresh run will rebuild your dashboard with everything tuned to your profile.</p>' +
          '<p style="font-size:13.5px;color:#444;">Quick reminders:</p>' +
          '<ul style="font-size:13.5px;color:#444;line-height:1.7;padding-left:18px;">' +
            '<li><strong>Prep Application</strong> on any job → tailored cover letter + resume summary</li>' +
            '<li><strong>Refresh data</strong> in the header → trigger a fresh pull anytime</li>' +
            '<li><strong>?</strong> in the header → replay this setup</li>' +
          '</ul>';
      },
      async save(st) {
        st.finished = true;
        // Best-effort: trigger a refresh so the new dashboard regenerates
        try {
          const ek = getEditKey();
          await fetch(WORKER + "/refresh?user=" + encodeURIComponent(SLUG), {
            method: "POST",
            headers: ek ? { "X-Edit-Key": ek } : {},
          });
        } catch (e) {}
      },
    },
  ];

  // ---- Controller ----
  function stepIndex(key) { for (let i = 0; i < STEPS.length; i++) if (STEPS[i].key === key) return i; return 0; }
  function currentStep() { return STEPS[stepIndex(state.currentStep)]; }

  function renderRail() {
    const list = document.getElementById("wiz3-rail-list");
    if (!list) return;
    list.innerHTML = STEPS.map((s, i) => {
      const isCurrent = s.key === state.currentStep;
      const isDone = state.completed.includes(s.key);
      const isSkipped = state.skipped.includes(s.key);
      let cls = "";
      if (isCurrent) cls = "is-current";
      else if (isDone) cls = "is-done";
      else if (isSkipped) cls = "is-skipped";
      const allowJump = isCurrent || isDone || isSkipped || (i <= Math.max(0, stepIndex(state.currentStep)));
      return '<li class="' + cls + '"' + (allowJump ? '' : ' aria-disabled="true"') + ' data-key="' + s.key + '">' +
        '<span class="wiz3-dot">' + (isDone ? "✓" : (isSkipped ? "–" : String(i+1))) + '</span>' +
        '<span>' + escHtml(s.title) + '</span>' +
      '</li>';
    }).join('');
    list.querySelectorAll("li[data-key]").forEach(li => {
      if (li.getAttribute("aria-disabled") === "true") return;
      li.addEventListener("click", () => goto(li.getAttribute("data-key")));
    });
  }

  function renderHead(s, idx) {
    document.getElementById("wiz3-step-no").textContent = "Step " + (idx + 1) + " of " + STEPS.length;
    document.getElementById("wiz3-h2").textContent = s.title;
    document.getElementById("wiz3-sub").textContent = s.subtitle || "";
  }
  function renderFoot(s, idx) {
    const skip = document.getElementById("wiz3-skip");
    const cont = document.getElementById("wiz3-continue");
    const back = document.getElementById("wiz3-back");
    back.disabled = (idx === 0);
    back.style.visibility = (idx === 0) ? "hidden" : "visible";
    skip.style.display = (s.optional && s.key !== "done") ? "" : "none";
    cont.textContent = (s.key === "done") ? "Finish" : "Continue →";
  }
  async function render() {
    saveState(state);
    const s = currentStep(); const idx = stepIndex(state.currentStep);
    renderRail();
    renderHead(s, idx);
    renderFoot(s, idx);
    const body = document.getElementById("wiz3-body");
    body.innerHTML = "";
    try {
      const r = s.render(body, state, { body });
      if (r && typeof r.then === "function") await r;
    } catch (e) { console.warn("wiz3 render", e); }
  }
  function goto(key) {
    if (!STEPS.find(s => s.key === key)) return;
    state.currentStep = key;
    saveState(state);
    render();
  }
  async function doContinue() {
    const s = currentStep();
    const body = document.getElementById("wiz3-body");
    if (typeof s.validate === "function") {
      const err = s.validate(state, { body });
      if (err) { setMsg(body, "err", err); return; }
    }
    const cont = document.getElementById("wiz3-continue");
    cont.disabled = true; cont.textContent = "Saving…";
    let _migrationDone = false;
    try {
      await s.save(state, { body });
      if (!state.completed.includes(s.key)) state.completed.push(s.key);
      state.skipped = state.skipped.filter(k => k !== s.key);
    } catch (e) {
      const msg = e && e.message ? e.message : String(e);
      try { console.warn("[wiz3] save threw:", msg, e); } catch(_) {}
      // FIX 1 hook: bullseye save throws "__migration_complete" after auto-finishing.
      if (msg === "__migration_complete") {
        _migrationDone = true;
      } else if (/session expired|HTTP 401|Not signed in/i.test(msg)) {
        setMsg(body, "err", "Session expired. Open your account page to re-enter your invite key. Your picks are kept here until you do.");
        try {
          let el = body.querySelector(".wiz3-msg");
          if (el) {
            el.innerHTML = 'Session expired. <a href="/account.html" target="_blank" style="color:#5C5CD6;font-weight:600;">Open account page</a> to re-enter your invite key. Your picks stay until you do.';
          }
        } catch(_) {}
        cont.disabled = false; cont.textContent = "Continue →";
        return;
      } else {
        setMsg(body, "err", "Couldn't save: " + msg);
        cont.disabled = false; cont.textContent = "Continue →";
        return;
      }
    } finally {
      // FIX 3: Continue button must never stick in "Saving…" state.
      try { cont.disabled = false; if (cont.textContent === "Saving…") cont.textContent = "Continue →"; } catch(_) {}
    }
    if (_migrationDone) return; // already closed by bullseye save()
    const idx = stepIndex(state.currentStep);
    if (idx + 1 >= STEPS.length) { finish(); return; }
    state.currentStep = STEPS[idx + 1].key;
    saveState(state);
    render();
  }
  function doSkip() {
    const s = currentStep();
    if (!s.optional) return;
    if (!state.skipped.includes(s.key)) state.skipped.push(s.key);
    state.completed = state.completed.filter(k => k !== s.key);
    const idx = stepIndex(state.currentStep);
    if (idx + 1 >= STEPS.length) { finish(); return; }
    state.currentStep = STEPS[idx + 1].key;
    saveState(state);
    render();
  }
  function doBack() {
    const idx = stepIndex(state.currentStep);
    if (idx === 0) return;
    state.currentStep = STEPS[idx - 1].key;
    saveState(state);
    render();
  }
  async function finish() {
    state.finished = true;
    saveState(state);
    document.getElementById("wiz3-overlay").classList.remove("show");
    // Failsafe: if the user reached the end without explicitly saving companies
    // in pick-companies step (it's optional), auto-regen once so their target
    // list aligns to the bullseye they just committed to. Silent on failure.
    if (!state.data.companies_saved && !state.data.companies_autoregen) {
      try {
        const ek = (typeof getEditKey === "function") ? getEditKey() : null;
        if (ek) {
          state.data.companies_autoregen = true;
          saveState(state);
          fetch(WORKER_BASE + "/regenerate-companies" + USER_QS, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Edit-Key": ek },
            body: JSON.stringify({ dry_run: false })
          }).catch(() => {});
        }
      } catch (e) { /* silent */ }
    }
  }
  function open() {
    // If user did the reload-to-detect dance on the install-extension step, resume there.
    try {
      const pending = localStorage.getItem("gmj_wizard_state_v3_pendingStep");
      if (pending) {
        state.currentStep = pending;
        localStorage.removeItem("gmj_wizard_state_v3_pendingStep");
      }
    } catch (e) {}
    if (!state.currentStep || !STEPS.find(s => s.key === state.currentStep)) state.currentStep = "welcome";
    document.getElementById("wiz3-overlay").classList.add("show");
    render();
  }
  function close() { document.getElementById("wiz3-overlay").classList.remove("show"); saveState(state); }
  function reset() {
    state = { currentStep: "welcome", completed: [], skipped: [], data: {}, finished: false };
    saveState(state);
    open();
  }

  // Wire footer + close
  document.getElementById("wiz3-back").addEventListener("click", doBack);
  document.getElementById("wiz3-skip").addEventListener("click", doSkip);
  document.getElementById("wiz3-continue").addEventListener("click", doContinue);
  document.getElementById("wiz3-close").addEventListener("click", close);
  // Backdrop click closes (but only outside the card)
  document.getElementById("wiz3-overlay").addEventListener("click", (e) => {
    if (e.target && e.target.id === "wiz3-overlay") close();
  });

  // Listen for postMessage from extension's marker (page-context can't see content-script JS directly)
  window.addEventListener("message", (ev) => {
    if (ev && ev.data && ev.data.type === "GMJ_EXTENSION_READY") window.__gmj_extension_ready = true;
  });

  // Public API
  window.WizV3 = { open, close, reset, goto, state: () => state };

  // Replace the old replayTour function so the ? button + Preferences link both
  // open the new wizard.
  window.replayTour = function () { state.finished = false; saveState(state); open(); };

  // Disable the old auto-launch: we'll trigger v3 here instead.
  async function autoLaunch() {
    // If old v2 auto-launch already ran and opened a modal, hide it.
    const oldModal = document.getElementById("gmj-wizard");
    if (oldModal) oldModal.classList.remove("show");
    // Decide whether to open: not finished, OR pending step from reload.
    let pending = "";
    try { pending = localStorage.getItem("gmj_wizard_state_v3_pendingStep") || ""; } catch (e) {}

    // MIGRATION (2026-05-27): existing users whose AI-extracted profile
    // exceeds the bullseye caps get force-routed to the new picker steps.
    // Caps mirror what pick-titles / pick-industries / pick-skills enforce.
    // Skipped if user just opened wizard (pending set) or hasn't finished yet.
    // MIGRATION (refined 2026-05-27): only trigger when the user's profile
    // exceeds the caps that 'your-bullseye' ACTUALLY enforces:
    //   targetTitles ≤ 5, industries ≤ 5, keywords ≤ 15
    // (technologies + frameworks are NOT capped — they hold the legacy long-
    // tail and we keep them as-is). Routes to 'your-bullseye' not the dead
    // 'pick-titles' step. Also stamps a one-time 'migrated' flag so we don't
    // re-trigger every reload after the user just walked through it.
    let needsMigration = false;
    if (state.finished && !pending) {
      try {
        const p = await getProfile();
        const titles  = ((p && p.targetTitles) || []).length;
        const inds    = ((p && p.industries)   || []).length;
        const kwOnly  = ((p && p.keywords)     || []).length;
        const alreadyMigrated = !!(state.data && state.data.bullseyeMigratedAt);
        if (!alreadyMigrated && (titles > 5 || inds > 5 || kwOnly > 15)) {
          needsMigration = true;
          // NOTE: do NOT reset state.finished here. Doing so caused an infinite
          // re-open loop for users whose AI-extracted profile was over-cap and
          // who couldn't (or didn't) trim in one sitting. The bullseyeMigratedAt
          // stamp alone is enough to ensure this only nags once per browser;
          // state.finished is the LIFETIME completion flag and should stay sticky.
          state.currentStep = "your-bullseye";
          state.completed = state.completed.filter(k => k !== "your-bullseye");
          state.data = state.data || {};
          state.data.bullseyeMigratedAt = new Date().toISOString();
          saveState(state);
          try { console.log("[wizard migration] over-cap profile detected — opening your-bullseye"); } catch(e) {}
        }
      } catch (e) { /* network blip — skip migration this load */ }
    }

    if (pending || !state.finished || needsMigration) {
      setTimeout(open, 500);
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoLaunch);
  } else {
    autoLaunch();
  }
})();
</script>
<!-- ====================== /Wizard v3 ====================== -->
"""
