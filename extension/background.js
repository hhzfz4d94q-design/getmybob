// Service worker — handles message passing between content scripts and our Worker.

const WORKER_URL = "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev";

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "GET_PROFILE") {
    chrome.storage.local.get(["gmj_profile", "gmj_slug", "gmj_key"]).then((o) => sendResponse(o));
    return true;
  }
  if (msg && msg.type === "DRAFT_ANSWER") {
    chrome.storage.local.get(["gmj_slug", "gmj_key"]).then(async (auth) => {
      if (!auth.gmj_slug || !auth.gmj_key) { sendResponse({ ok: false, error: "Not signed in" }); return; }
      try {
        const r = await fetch(`${WORKER_URL}/prep?user=${encodeURIComponent(auth.gmj_slug)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Edit-Key": auth.gmj_key },
          body: JSON.stringify({
            jobTitle: msg.jobTitle || "",
            jobCompany: msg.jobCompany || "",
            jobDescription: msg.jobDescription || "",
            question: msg.question || "",
          }),
        });
        const data = await r.json().catch(() => ({}));
        sendResponse({ ok: r.ok, data });
      } catch (e) { sendResponse({ ok: false, error: e.message || String(e) }); }
    });
    return true;
  }
  if (msg && msg.type === "MARK_APPLIED") {
    chrome.storage.local.get(["gmj_slug", "gmj_key"]).then(async (auth) => {
      if (!auth.gmj_slug || !auth.gmj_key) { sendResponse({ ok: false }); return; }
      try {
        // Stable fingerprint from the apply URL — matches how dashboard cards key off jobs
        // (we send the URL so the Worker can match by url-string if exact fp is unknown)
        const r = await fetch(`${WORKER_URL}/tracker?user=${encodeURIComponent(auth.gmj_slug)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Edit-Key": auth.gmj_key },
          body: JSON.stringify({
            action: "setStatus",
            fp: msg.jobUrl, // use URL as the fingerprint; dashboard matches by URL fallback
            status: "applied",
            jobMeta: { title: msg.jobTitle || "", company: msg.jobCompany || "", url: msg.jobUrl || "" },
          }),
        });
        sendResponse({ ok: r.ok });
      } catch (e) { sendResponse({ ok: false, error: e.message }); }
    });
    return true;
  }
});
