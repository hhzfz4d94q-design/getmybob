// Service worker — minimal for MV3. Listens for content-script messages
// asking for the cached profile.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "GET_PROFILE") {
    chrome.storage.local.get(["gmj_profile", "gmj_slug", "gmj_key"]).then((o) => {
      sendResponse(o);
    });
    return true; // async response
  }
  if (msg && msg.type === "DRAFT_ANSWER") {
    // Proxy to Worker /prep for a custom-question free-text answer
    chrome.storage.local.get(["gmj_slug", "gmj_key"]).then(async (auth) => {
      if (!auth.gmj_slug || !auth.gmj_key) {
        sendResponse({ ok: false, error: "Not signed in" });
        return;
      }
      try {
        const r = await fetch("https://cool-darkness-dce5.tr6jz6v7wg.workers.dev/prep?user=" + encodeURIComponent(auth.gmj_slug), {
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
      } catch (e) {
        sendResponse({ ok: false, error: e.message || String(e) });
      }
    });
    return true;
  }
});
