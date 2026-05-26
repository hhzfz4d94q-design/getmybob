// Workday auto-fill. Workday is per-tenant and uses data-automation-id attributes.
// We use those + label-text matching for common fields.

(function () {
  const GMJ = window.__gmj;
  if (!GMJ) return;
  GMJ.log("workday loaded on", location.href);

  const LABEL_MAP = [
    [["first name", "legal first name"], "firstName"],
    [["last name", "legal last name", "family name"], "lastName"],
    [["full name", "legal full name"], "fullName"],
    [["email address", "email"], "email"],
    [["phone number", "mobile phone", "phone"], "phone"],
    [["address line 1", "street address"], "location"],
    [["linkedin"], "linkedinUrl"],
    [["are you legally authorized"], "workAuthorization"],
    [["do you require sponsorship", "will you now or in the future require"], "requiresSponsorship"],
  ];

  function fill(profile) {
    let filled = 0;
    for (const [labels, key] of LABEL_MAP) {
      for (const lab of labels) {
        const el = GMJ.findByLabel(lab);
        if (!el) continue;
        const tag = el.tagName.toLowerCase();
        if (tag === "select") {
          if (GMJ.selectByText(el, profile[key])) { filled++; break; }
        } else {
          if (profile[key] && GMJ.setValue(el, profile[key])) { filled++; break; }
        }
      }
    }
    return filled;
  }

  function tryFill() {
    const ready = document.querySelector("[data-automation-id]");
    if (!ready) return false;
    GMJ.runFill(fill);
    return true;
  }

  // Workday is a SPA — try on every navigation
  let last = location.href;
  setInterval(() => {
    if (location.href !== last) {
      last = location.href;
      setTimeout(tryFill, 1500);
    }
  }, 1000);

  if (!tryFill()) {
    const obs = new MutationObserver(() => { if (tryFill()) obs.disconnect(); });
    obs.observe(document.body, { childList: true, subtree: true });
    let n = 0;
    const iv = setInterval(() => { if (++n > 30 || tryFill()) clearInterval(iv); }, 1500);
  }
})();
