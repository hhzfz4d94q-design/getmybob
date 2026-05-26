// Lever auto-fill. Lever uses fields like <input name="name">, <input name="email">,
// <input name="urls[LinkedIn]">.

(function () {
  const GMJ = window.__gmj;
  if (!GMJ) return;
  GMJ.log("lever loaded on", location.href);

  const FIELD_MAP = [
    ["name", "fullName"],
    ["email", "email"],
    ["phone", "phone"],
    ["org", "currentCompany"],
    ["location", "location"],
    ["urls[LinkedIn]", "linkedinUrl"],
    ["urls[GitHub]", "githubUrl"],
    ["urls[Portfolio]", "websiteUrl"],
    ["urls[Other]", "websiteUrl"],
  ];

  function fill(profile) {
    let filled = 0;
    for (const [name, key] of FIELD_MAP) {
      const el = document.querySelector(`[name="${name}"]`);
      if (el && profile[key] && GMJ.setValue(el, profile[key])) filled++;
    }
    const company = document.querySelector(".company-name, .posting-headline")?.innerText || "";
    const jobTitle = document.querySelector("h2, .posting-headline h2")?.innerText || document.title;
    const jobDesc = (document.querySelector(".content, .description")?.innerText || "").slice(0, 3000);
    const customAreas = document.querySelectorAll("textarea[name*='custom'], textarea[name*='additionalInfo']");
    customAreas.forEach((t) => {
      GMJ.attachDraftButton(t, { jobTitle, jobCompany: company, jobDescription: jobDesc, question: t.getAttribute("aria-label") || t.placeholder || "Tell us about yourself" });
    });
    return filled;
  }

  function tryFill() {
    const form = document.querySelector("form.application-form, form[action*='apply']");
    if (!form) return false;
    GMJ.runFill(fill);
    return true;
  }

  if (!tryFill()) {
    const obs = new MutationObserver(() => { if (tryFill()) obs.disconnect(); });
    obs.observe(document.body, { childList: true, subtree: true });
  }
})();
