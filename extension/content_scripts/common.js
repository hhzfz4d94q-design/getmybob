// Shared utilities used by all per-ATS content scripts.
// Exposes window.__gmj global with helpers.

(function () {
  if (window.__gmj) return; // already loaded
  const GMJ = {};

  GMJ.log = (...args) => console.log("%c[gmj-helper]", "color:#5C5CD6;font-weight:bold;", ...args);
  GMJ.warn = (...args) => console.warn("[gmj-helper]", ...args);

  GMJ.getProfile = () =>
    new Promise((resolve) =>
      chrome.runtime.sendMessage({ type: "GET_PROFILE" }, (resp) => resolve(resp || {}))
    );

  GMJ.draftAnswer = ({ jobTitle, jobCompany, jobDescription, question }) =>
    new Promise((resolve) =>
      chrome.runtime.sendMessage(
        { type: "DRAFT_ANSWER", jobTitle, jobCompany, jobDescription, question },
        (resp) => resolve(resp || {})
      )
    );

  // Set the value on an input and dispatch the events frameworks listen to.
  GMJ.setValue = (el, value) => {
    if (!el || value == null || value === "") return false;
    const tag = (el.tagName || "").toLowerCase();
    const proto = (tag === "textarea") ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, String(value));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  };

  GMJ.selectByText = (selectEl, text) => {
    if (!selectEl || !text) return false;
    const t = String(text).toLowerCase().trim();
    for (const opt of selectEl.options) {
      if ((opt.text || "").toLowerCase().trim() === t || (opt.value || "").toLowerCase() === t) {
        selectEl.value = opt.value;
        selectEl.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      }
    }
    // Loose match — first option that contains the text
    for (const opt of selectEl.options) {
      if ((opt.text || "").toLowerCase().includes(t)) {
        selectEl.value = opt.value;
        selectEl.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      }
    }
    return false;
  };

  GMJ.findByLabel = (labelText) => {
    // Find an input/textarea/select whose label text matches.
    const t = labelText.toLowerCase();
    const labels = document.querySelectorAll("label");
    for (const lab of labels) {
      const lt = (lab.textContent || "").toLowerCase().trim();
      if (lt === t || lt.startsWith(t + " ") || lt.startsWith(t + "*") || lt.startsWith(t + ":") || lt.includes(t)) {
        const forId = lab.getAttribute("for");
        if (forId) {
          const el = document.getElementById(forId);
          if (el) return el;
        }
        // Sometimes the input is inside the label
        const inner = lab.querySelector("input,textarea,select");
        if (inner) return inner;
      }
    }
    return null;
  };

  GMJ.notify = (msg, ok = true) => {
    // Toast at the top right
    let host = document.getElementById("__gmj_toast");
    if (!host) {
      host = document.createElement("div");
      host.id = "__gmj_toast";
      host.style.cssText = "position:fixed;top:18px;right:18px;z-index:2147483647;display:flex;flex-direction:column;gap:8px;";
      document.body.appendChild(host);
    }
    const t = document.createElement("div");
    t.style.cssText =
      "background:" + (ok ? "#0a6b3a" : "#b00") +
      ";color:#fff;padding:8px 12px;border-radius:6px;font-family:-apple-system,sans-serif;font-size:13px;font-weight:600;box-shadow:0 4px 14px rgba(0,0,0,0.18);";
    t.textContent = msg;
    host.appendChild(t);
    setTimeout(() => t.remove(), 5000);
  };

  // Add a small floating "✨ Draft with AI" button next to a textarea/contenteditable.
  GMJ.attachDraftButton = (el, opts) => {
    if (!el || el._gmjBtn) return;
    el._gmjBtn = true;
    const wrapper = document.createElement("div");
    wrapper.style.cssText = "display:inline-block;margin:4px 0;";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "✨ Draft with AI from your resume";
    btn.style.cssText =
      "background:#5C5CD6;color:#fff;border:0;border-radius:6px;padding:4px 10px;font-size:11.5px;font-weight:600;cursor:pointer;";
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      btn.disabled = true;
      btn.textContent = "Drafting…";
      const resp = await GMJ.draftAnswer({
        jobTitle: opts.jobTitle || document.title,
        jobCompany: opts.jobCompany || "",
        jobDescription: opts.jobDescription || "",
        question: opts.question || (el.placeholder || el.getAttribute("aria-label") || "Tell us about yourself"),
      });
      btn.disabled = false;
      btn.textContent = "✨ Re-draft";
      const text = (resp && resp.data && (resp.data.coverLetter || resp.data.summary || resp.data.answer)) || "";
      if (text) {
        GMJ.setValue(el, text);
        GMJ.notify("Drafted ✓", true);
      } else {
        GMJ.notify("Couldn't draft — sign in via the extension popup", false);
      }
    });
    wrapper.appendChild(btn);
    el.insertAdjacentElement("afterend", wrapper);
  };

  // Run a fill function and report results.
  GMJ.runFill = async (fillFn) => {
    const { gmj_profile } = await GMJ.getProfile();
    if (!gmj_profile) {
      GMJ.notify("Sign in via the extension popup first", false);
      return;
    }
    let filled = 0;
    try {
      filled = await fillFn(gmj_profile);
    } catch (e) {
      GMJ.warn("fill failed", e);
    }
    GMJ.notify("Filled " + filled + " field" + (filled === 1 ? "" : "s") + " ✓", true);
  };

  window.__gmj = GMJ;
})();
