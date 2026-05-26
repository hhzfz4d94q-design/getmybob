const WORKER_URL = "https://cool-darkness-dce5.tr6jz6v7wg.workers.dev";

const $ = (id) => document.getElementById(id);

async function getStored() {
  const o = await chrome.storage.local.get(["gmj_slug", "gmj_key", "gmj_profile"]);
  return o;
}

async function refreshProfile() {
  const { gmj_slug, gmj_key } = await getStored();
  if (!gmj_slug || !gmj_key) return null;
  // Fetch skills_profile + resume (we use these to populate form fields)
  const profileResp = await fetch(`${WORKER_URL}/skills-profile?user=${encodeURIComponent(gmj_slug)}`);
  const profileData = await profileResp.json().catch(() => ({}));
  const profile = (profileData && profileData.profile) || {};

  const resumeResp = await fetch(`${WORKER_URL}/resume?user=${encodeURIComponent(gmj_slug)}`);
  const resumeData = await resumeResp.json().catch(() => ({}));
  const resume = resumeData && resumeData.resume ? safeParse(resumeData.resume) : {};

  const merged = mergeAppProfile(profile, resume, gmj_slug);
  await chrome.storage.local.set({ gmj_profile: merged, gmj_profile_at: Date.now() });
  return merged;
}

function safeParse(s) {
  if (typeof s === "object") return s || {};
  try { return JSON.parse(s); } catch (e) { return {}; }
}

function mergeAppProfile(profile, resume, slug) {
  // Build the structured application profile from what we have on hand.
  // The resume is the AI-parsed JSON shape (name, email, phone, work history, education).
  const personal = (resume && resume.personal) || resume || {};
  const fullName = personal.name || profile.primaryName || profile.user || slug;
  const [firstName, ...rest] = (fullName || "").split(/\s+/);
  const lastName = rest.join(" ") || "";
  const educ = Array.isArray(resume.education) ? resume.education[0] : null;
  const work0 = Array.isArray(resume.experience) ? resume.experience[0] : null;

  return {
    slug,
    fullName,
    firstName,
    lastName,
    email: personal.email || "",
    phone: personal.phone || personal.phoneNumber || "",
    location: personal.location || personal.address || "",
    linkedinUrl: personal.linkedin || personal.linkedinUrl || "",
    githubUrl: personal.github || personal.githubUrl || "",
    websiteUrl: personal.website || personal.portfolio || "",
    currentCompany: (work0 && work0.company) || "",
    currentTitle: (work0 && (work0.title || work0.role)) || profile.primaryRole || "",
    school: (educ && (educ.school || educ.institution)) || "",
    degree: (educ && educ.degree) || "",
    graduationYear: (educ && (educ.graduationYear || educ.endYear)) || "",
    workAuthorization: profile.workAuthorization || "US Citizen",
    requiresSponsorship: profile.requiresSponsorship === true ? "Yes" : "No",
    salaryExpectation: profile.salaryFloor ? String(profile.salaryFloor) : "",
    yearsExperience: profile.yearsExperience || "",
    summary: profile.summary || "",
    // Free-text answers — extension uses /prep to draft when missing
    whyThisCompanyTemplate: profile.whyThisCompanyTemplate || "",
    coverLetter: profile.coverLetter || "",
  };
}

async function render() {
  const { gmj_slug, gmj_key, gmj_profile } = await getStored();
  if (gmj_slug && gmj_key) {
    $("signed-in").style.display = "";
    $("signed-out").style.display = "none";
    $("user-name").textContent = gmj_profile?.fullName || gmj_slug;
    const summary = gmj_profile ? `
      • Email: ${gmj_profile.email || "—"}<br>
      • Phone: ${gmj_profile.phone || "—"}<br>
      • Current: ${gmj_profile.currentTitle || "—"}<br>
      • LinkedIn: ${gmj_profile.linkedinUrl ? "✓" : "—"}<br>
      • Work auth: ${gmj_profile.workAuthorization || "—"}
    ` : "(profile not loaded — click Refresh)";
    $("profile-summary").innerHTML = summary;
  } else {
    $("signed-in").style.display = "none";
    $("signed-out").style.display = "";
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await render();

  $("signin-btn").addEventListener("click", async () => {
    const slug = $("slug").value.trim();
    const key = $("key").value.trim();
    if (!slug || !key) {
      $("signin-status").style.display = "";
      $("signin-status").className = "status err";
      $("signin-status").textContent = "Please enter both your slug and edit key.";
      return;
    }
    $("signin-status").style.display = "";
    $("signin-status").className = "status";
    $("signin-status").textContent = "Verifying…";
    // Verify by hitting /skills-profile — just confirms the slug exists
    try {
      const r = await fetch(`${WORKER_URL}/skills-profile?user=${encodeURIComponent(slug)}`);
      if (!r.ok) {
        $("signin-status").className = "status err";
        $("signin-status").textContent = "User not found. Check the slug.";
        return;
      }
      await chrome.storage.local.set({ gmj_slug: slug, gmj_key: key });
      const profile = await refreshProfile();
      $("signin-status").className = "status ok";
      $("signin-status").textContent = "Signed in ✓ — visit any Greenhouse/Lever/Ashby/Workday apply page.";
      await render();
    } catch (e) {
      $("signin-status").className = "status err";
      $("signin-status").textContent = "Network error: " + (e.message || e);
    }
  });

  $("refresh-btn") && $("refresh-btn").addEventListener("click", async () => {
    await refreshProfile();
    await render();
  });

  $("signout-btn") && $("signout-btn").addEventListener("click", async () => {
    await chrome.storage.local.clear();
    await render();
  });
});
