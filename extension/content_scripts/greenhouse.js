// Greenhouse auto-fill. Greenhouse forms use a consistent naming pattern:
// <input name="job_application[first_name]">, etc. Also exposed via Greenhouse's
// boards.greenhouse.io and the newer job-boards.greenhouse.io.

(function () {
  const GMJ = window.__gmj;
  if (!GMJ) return;
  GMJ.log("greenhouse loaded on", location.href);

  const FIELD_MAP = [
    ["job_application[first_name]", "firstName"],
    ["job_application[last_name]", "lastName"],
    ["job_application[email]", "email"],
    ["job_application[phone]", "phone"],
    ["job_application[location]", "location"],
    ["job_application[company]", "currentCompany"],
    ["job_application[urls][LinkedIn]", "linkedinUrl"],
    ["job_application[urls][LinkedIn Profile]", "linkedinUrl"],
    ["job_application[urls][GitHub]", "githubUrl"],
    ["job_application[urls][Website]", "websiteUrl"],
    ["job_application[urls][Portfolio]", "websiteUrl"],
  ];

  function fillByName(name, value) {
    const el = document.querySelector(`[name="${name}"]`);
    if (el) return GMJ.setValue(el, value);
    return false;
  }

  function fill(profile) {
    let filled = 0;
    for (const [name, key] of FIELD_MAP) {
      if (profile[key] && fillByName(name, profile[key])) filled++;
    }

    // Cover letter / "Why us?" text area — Greenhouse uses
    // <textarea name="job_application[answers_attributes][X][text_value]">.
    // We attach a "Draft with AI" button rather than auto-filling.
    const company = document.title.split(" - ").slice(-1)[0] || "";
    const jobTitle = document.title.split(" - ")[0] || "";
    const jobDesc = (document.querySelector(".content, .job-description, .body, #content")?.innerText || "").slice(0, 3000);
    const customAreas = document.querySelectorAll("textarea[name*='answers_attributes'], textarea[name*='cover_letter']");
    customAreas.forEach((t) => {
      GMJ.attachDraftButton(t, { jobTitle, jobCompany: company, jobDescription: jobDesc, question: t.getAttribute("aria-label") || t.placeholder || "Tell us why you're a fit" });
    });

    return filled;
  }

  // Wait for form to mount, then run.
  function tryFill() {
    const form = document.querySelector("form#new_job_application, form[action*='/applications']");
    if (!form) return false;
    GMJ.runFill(fill);
    return true;
  }

  if (!tryFill()) {
    const obs = new MutationObserver(() => {
      if (tryFill()) obs.disconnect();
    });
    obs.observe(document.body, { childList: true, subtree: true });
    // Also retry every 1.5s for 30s
    let n = 0;
    const iv = setInterval(() => {
      if (++n > 20 || tryFill()) clearInterval(iv);
    }, 1500);
  }
})();
