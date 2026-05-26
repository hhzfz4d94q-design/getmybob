// Ashby auto-fill. Ashby fields are dynamically rendered. We match by label text
// since field names are randomized.

(function () {
  const GMJ = window.__gmj;
  if (!GMJ) return;
  GMJ.log("ashby loaded on", location.href);

  const LABEL_MAP = [
    [["first name"], "firstName"],
    [["last name"], "lastName"],
    [["full name", "name"], "fullName"],
    [["email"], "email"],
    [["phone"], "phone"],
    [["location"], "location"],
    [["current company", "company"], "currentCompany"],
    [["linkedin"], "linkedinUrl"],
    [["github"], "githubUrl"],
    [["website", "portfolio", "personal site"], "websiteUrl"],
  ];

  function fill(profile) {
    let filled = 0;
    for (const [labels, key] of LABEL_MAP) {
      for (const lab of labels) {
        const el = GMJ.findByLabel(lab);
        if (el && profile[key] && GMJ.setValue(el, profile[key])) {
          filled++;
          break;
        }
      }
    }
    // Find textareas (custom questions) and attach AI-draft buttons
    const customAreas = document.querySelectorAll("textarea");
    const company = document.title.split(" at ").slice(-1)[0] || "";
    const jobTitle = document.querySelector("h1,h2")?.innerText || document.title;
    const jobDesc = (document.body.innerText || "").slice(0, 3000);
    customAreas.forEach((t) => {
      GMJ.attachDraftButton(t, { jobTitle, jobCompany: company, jobDescription: jobDesc, question: t.getAttribute("aria-label") || t.placeholder || "Tell us about yourself" });
    });
    return filled;
  }

  function tryFill() {
    const form = document.querySelector("form");
    if (!form || form._gmjDone) return false;
    form._gmjDone = true;
    GMJ.runFill(fill);
    return true;
  }

  if (!tryFill()) {
    const obs = new MutationObserver(() => { if (tryFill()) obs.disconnect(); });
    obs.observe(document.body, { childList: true, subtree: true });
  }
})();
