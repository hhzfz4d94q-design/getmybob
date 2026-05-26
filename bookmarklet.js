/*  getmemyjob universal bookmarklet
    Bookmark this once. When you're on a Greenhouse / Lever / Ashby / Workday
    apply page, click the bookmark — it auto-fills the standard fields from
    your getmemyjob profile. Works in Chrome, Firefox, Safari (desktop + iOS),
    Edge, mobile browsers — anywhere a bookmark can run JS.
*/
(function () {
  if (window.__gmj_bm_loaded) { __gmj_bm_run(); return; }
  window.__gmj_bm_loaded = true;
  const WORKER = "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev";
  const KEY_STORE = "gmj_bm_auth_v1";

  function toast(msg, ok) {
    let host = document.getElementById("__gmj_bm_toast");
    if (!host) {
      host = document.createElement("div");
      host.id = "__gmj_bm_toast";
      host.style.cssText = "position:fixed;top:18px;right:18px;z-index:2147483647;display:flex;flex-direction:column;gap:8px;font-family:-apple-system,sans-serif;";
      document.body.appendChild(host);
    }
    const t = document.createElement("div");
    t.style.cssText = "background:" + (ok ? "#0a6b3a" : "#b00") + ";color:#fff;padding:8px 12px;border-radius:6px;font-size:13px;font-weight:600;box-shadow:0 4px 14px rgba(0,0,0,0.18);";
    t.textContent = msg;
    host.appendChild(t);
    setTimeout(function () { t.remove(); }, 5000);
  }

  function setValue(el, value) {
    if (!el || value == null || value === "") return false;
    try {
      const tag = (el.tagName || "").toLowerCase();
      const proto = (tag === "textarea") ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
      setter.call(el, String(value));
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    } catch (e) { return false; }
  }

  function selectByText(el, text) {
    if (!el || !text) return false;
    const t = String(text).toLowerCase().trim();
    for (const opt of el.options) {
      if ((opt.text || "").toLowerCase().trim() === t || (opt.value || "").toLowerCase() === t) {
        el.value = opt.value; el.dispatchEvent(new Event("change", { bubbles: true })); return true;
      }
    }
    for (const opt of el.options) {
      if ((opt.text || "").toLowerCase().includes(t)) {
        el.value = opt.value; el.dispatchEvent(new Event("change", { bubbles: true })); return true;
      }
    }
    return false;
  }

  function findByLabel(labelText) {
    const t = labelText.toLowerCase();
    const labels = document.querySelectorAll("label");
    for (const lab of labels) {
      const lt = (lab.textContent || "").toLowerCase().trim();
      if (lt === t || lt.startsWith(t + " ") || lt.startsWith(t + "*") || lt.startsWith(t + ":") || lt.includes(t)) {
        const forId = lab.getAttribute("for");
        if (forId) { const el = document.getElementById(forId); if (el) return el; }
        const inner = lab.querySelector("input,textarea,select");
        if (inner) return inner;
      }
    }
    return null;
  }

  function detectAts() {
    const h = location.hostname;
    if (h.indexOf("greenhouse.io") >= 0) return "greenhouse";
    if (h === "jobs.lever.co" || h.endsWith(".jobs.lever.co")) return "lever";
    if (h === "jobs.ashbyhq.com" || h.endsWith(".jobs.ashbyhq.com")) return "ashby";
    if (h.indexOf("myworkdayjobs.com") >= 0) return "workday";
    return null;
  }

  function fillGreenhouse(p) {
    const map = [
      ["job_application[first_name]", p.firstName],
      ["job_application[last_name]",  p.lastName],
      ["job_application[email]",      p.email],
      ["job_application[phone]",      p.phone],
      ["job_application[location]",   p.location],
      ["job_application[company]",    p.currentCompany],
      ["job_application[urls][LinkedIn]",         p.linkedinUrl],
      ["job_application[urls][LinkedIn Profile]", p.linkedinUrl],
      ["job_application[urls][GitHub]",   p.githubUrl],
      ["job_application[urls][Website]",  p.websiteUrl],
      ["job_application[urls][Portfolio]", p.websiteUrl],
    ];
    let n = 0;
    for (const [name, value] of map) {
      const el = document.querySelector('[name="' + name + '"]');
      if (el && setValue(el, value)) n++;
    }
    return n;
  }

  function fillLever(p) {
    const map = [
      ["name",  p.fullName],
      ["email", p.email],
      ["phone", p.phone],
      ["org",   p.currentCompany],
      ["location", p.location],
      ["urls[LinkedIn]", p.linkedinUrl],
      ["urls[GitHub]",   p.githubUrl],
      ["urls[Portfolio]", p.websiteUrl],
      ["urls[Other]",     p.websiteUrl],
    ];
    let n = 0;
    for (const [name, value] of map) {
      const el = document.querySelector('[name="' + name + '"]');
      if (el && setValue(el, value)) n++;
    }
    return n;
  }

  function fillAshby(p) {
    const labelMap = [
      [["first name"], p.firstName],
      [["last name"], p.lastName],
      [["full name", "name"], p.fullName],
      [["email"], p.email],
      [["phone"], p.phone],
      [["location"], p.location],
      [["current company", "company"], p.currentCompany],
      [["linkedin"], p.linkedinUrl],
      [["github"], p.githubUrl],
      [["website", "portfolio", "personal site"], p.websiteUrl],
    ];
    let n = 0;
    for (const [labels, value] of labelMap) {
      for (const lab of labels) {
        const el = findByLabel(lab);
        if (el && setValue(el, value)) { n++; break; }
      }
    }
    return n;
  }

  function fillWorkday(p) {
    const labelMap = [
      [["first name", "legal first name"], p.firstName],
      [["last name", "legal last name", "family name"], p.lastName],
      [["full name", "legal full name"], p.fullName],
      [["email address", "email"], p.email],
      [["phone number", "mobile phone", "phone"], p.phone],
      [["address line 1", "street address"], p.location],
      [["linkedin"], p.linkedinUrl],
    ];
    let n = 0;
    for (const [labels, value] of labelMap) {
      for (const lab of labels) {
        const el = findByLabel(lab);
        if (!el) continue;
        const t = el.tagName.toLowerCase();
        if (t === "select") { if (selectByText(el, value)) { n++; break; } }
        else { if (setValue(el, value)) { n++; break; } }
      }
    }
    return n;
  }

  function mergeProfile(profile, resume, slug) {
    const personal = (resume && resume.personal) || {};
    const fullName = personal.name || profile.user || slug;
    const [firstName, ...rest] = (fullName || "").split(/\s+/);
    const lastName = rest.join(" ") || "";
    const exp0 = (resume && resume.experience && resume.experience[0]) || {};
    return {
      slug: slug, fullName: fullName, firstName: firstName, lastName: lastName,
      email: profile.email || personal.email || "",
      phone: profile.phone || personal.phone || "",
      location: profile.location || personal.location || "",
      linkedinUrl: profile.linkedinUrl || personal.linkedin || "",
      githubUrl: profile.githubUrl || personal.github || "",
      websiteUrl: profile.websiteUrl || personal.website || "",
      currentCompany: profile.currentCompany || exp0.company || "",
      currentTitle: profile.currentTitle || exp0.title || "",
      workAuthorization: profile.workAuthorization || "US Citizen",
      requiresSponsorship: profile.requiresSponsorship || "No",
    };
  }

  function getAuth() {
    try {
      const raw = localStorage.getItem(KEY_STORE);
      if (raw) return JSON.parse(raw);
    } catch (e) {}
    return null;
  }

  function setAuth(slug, key) {
    try { localStorage.setItem(KEY_STORE, JSON.stringify({ slug: slug, key: key, savedAt: Date.now() })); } catch (e) {}
  }

  function promptAuth() {
    const slug = window.prompt("Your getmemyjob slug (e.g. geetu)\n\nFrom your invite URL — the part right before .html");
    if (!slug) return null;
    const key = window.prompt("Your edit key\n\nFrom your invite URL — the value right after ?key=");
    if (!key) return null;
    setAuth(slug.trim(), key.trim());
    return { slug: slug.trim(), key: key.trim() };
  }

  async function fetchProfile(slug) {
    const p1 = await fetch(WORKER + "/skills-profile?user=" + encodeURIComponent(slug)).then(function (r) { return r.json(); }).catch(function () { return {}; });
    const p2 = await fetch(WORKER + "/resume?user=" + encodeURIComponent(slug)).then(function (r) { return r.json(); }).catch(function () { return {}; });
    const profile = (p1 && p1.profile) || {};
    let resume = {};
    if (p2 && p2.resume) {
      try { resume = typeof p2.resume === "string" ? JSON.parse(p2.resume) : p2.resume; } catch (e) {}
    }
    return mergeProfile(profile, resume, slug);
  }

  window.__gmj_bm_run = async function () {
    const ats = detectAts();
    if (!ats) {
      toast("Not an Apply page I recognize (need Greenhouse/Lever/Ashby/Workday)", false);
      return;
    }
    let auth = getAuth();
    if (!auth) { auth = promptAuth(); if (!auth) { toast("Cancelled", false); return; } }
    toast("Loading your getmemyjob profile…", true);
    let merged;
    try { merged = await fetchProfile(auth.slug); }
    catch (e) { toast("Couldn't fetch profile — check your slug.", false); return; }
    let n = 0;
    if (ats === "greenhouse") n = fillGreenhouse(merged);
    else if (ats === "lever") n = fillLever(merged);
    else if (ats === "ashby") n = fillAshby(merged);
    else if (ats === "workday") n = fillWorkday(merged);
    toast("Filled " + n + " field" + (n === 1 ? "" : "s") + " from your getmemyjob profile ✓", true);
  };

  __gmj_bm_run();
})();
