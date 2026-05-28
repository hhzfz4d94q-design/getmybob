// Phase 6 — multi-user Worker with admin UI support
// KV layout:
//   users:list                      -> JSON array of {slug, name, email, createdAt}
//   user:{slug}:edit_key            -> per-user upload password
//   user:{slug}:name                -> display name (also in users:list)
//   user:{slug}:resume:active       -> id of currently active version
//   user:{slug}:resume:list         -> JSON array of version metadata
//   user:{slug}:resume:{id}         -> stringified resume JSON
//   user:{slug}:skills_profile      -> AI-generated profile JSON
// Migration: legacy keys move to user:geetu:* on first read; users:list is
// bootstrapped by scanning existing user:*:edit_key keys.

const GH_OWNER = 'hhzfz4d94q-design';
const GH_REPO = 'getmybob';
const GH_WORKFLOW = 'refresh-jobs.yml';

const DEFAULT_USER = 'geetu';

// Legacy keys (pre-multi-user) — auto-migrated on first read
const LEGACY_ACTIVE = 'resume:active';
const LEGACY_LIST = 'resume:list';
const LEGACY_PROFILE = 'skills_profile';
const LEGACY_LEGACY_RESUME = 'default'; // pre-versioning single-resume key

function uk(slug, suffix) { return `user:${slug}:${suffix}`; }

export default {
  // G2: Cloudflare scheduled (cron) handler — runs daily at 7am ET (configured
  // via wrangler.toml or dashboard cron triggers). Emails each user a digest
  // of their top-5 picks. Set CF cron to "0 11 * * *" (11am UTC = 7am ET).
  // Cron handler — runs every hour (cron "0 * * * *"). Each call passes
  // event.scheduledTime; sendDailyMixedToAll uses it to decide which users
  // (if any) get an email this hour based on their nudge / recap time prefs.
  async scheduled(event, env, ctx) {
    try {
      await sendDailyMixedToAll(env, event);
    } catch (e) {
      console.error("[scheduled] failed:", e && e.message ? e.message : e);
    }
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-Edit-Key, X-Admin-Key, Authorization',
    };
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Key, X-Edit-Key, Authorization', 'Access-Control-Max-Age': '86400' } });

    // Admin endpoints (provision / list / delete users)
    if (url.pathname === '/admin/users') return handleAdminUsers(request, env, cors);
    if (url.pathname === '/admin/enrich-companies') return handleEnrichCompanies(request, env, cors);
    if (url.pathname === '/admin/discover-vc-portfolio') return handleDiscoverVcPortfolio(request, env, cors);
    if (url.pathname === '/company-stage') return handleCompanyStage(request, env, cors);
    if (url.pathname === '/admin/pending-users') return handleAdminPendingUsers(request, env, cors);
    if (url.pathname === '/admin/approve-user') return handleAdminApproveUser(request, env, cors);
    if (url.pathname === '/admin/reject-user') return handleAdminRejectUser(request, env, cors);
    // Public read-only user list (used by fetch_jobs.py to generate dashboards)
    if (url.pathname === '/users') return handlePublicUsers(request, env, cors);

    if (url.pathname === '/refresh') return handleRefresh(request, env, cors);

    // --- Auth endpoints (Slice A) — no slug required ---
    if (url.pathname === '/api/auth/signup') return handleSignup(request, env, cors);
    if (url.pathname === '/api/auth/login') return handleLogin(request, env, cors);
    if (url.pathname === '/api/auth/logout') return handleLogout(request, env, cors);
    if (url.pathname === '/api/auth/me') return handleMe(request, env, cors);
    if (url.pathname === '/api/auth/change-password') return handleChangePassword(request, env, cors);
    if (url.pathname === '/api/auth/admin-reset-password') return handleAdminResetPassword(request, env, cors);
    if (url.pathname === '/api/auth/capacity') return handleCapacity(request, env, cors);
    if (url.pathname === '/api/auth/admin-login') return handleAdminLogin(request, env, cors);
    if (url.pathname === '/api/auth/admin-change-password') return handleAdminChangePassword(request, env, cors);

    // Determine which user this request operates on.
    // Priority: ?user=slug in URL → "user" field in JSON body → DEFAULT_USER
    const slug = await resolveSlug(request, url);

    if (url.pathname === '/resume') return handleResume(request, env, cors, slug);
    if (url.pathname === '/resume-versions') return handleVersions(request, env, cors, slug);
    if (url.pathname === '/parse-resume') return handleParseResume(request, env, cors, slug);
    if (url.pathname === '/resume-health') return handleResumeHealth(request, env, cors, slug);
    if (url.pathname === '/resume-health-suggest') return handleResumeHealthSuggest(request, env, cors, slug);
    if (url.pathname === '/api/tuning/save')    return handleTuningSave(request, env, cors, slug);
    if (url.pathname === '/api/tuning/outcome') return handleTuningOutcome(request, env, cors, slug);
    if (url.pathname === '/api/tuning/list')    return handleTuningList(request, env, cors, slug);
    if (url.pathname === '/api/dismiss')         return handleDismiss(request, env, cors, slug);
    if (url.pathname === '/api/rerank')          return handleRerank(request, env, cors, slug);
    if (url.pathname === '/skills-profile') return handleSkillsProfile(request, env, cors, slug);
    if (url.pathname === '/regenerate-profile') return handleRegenerateProfile(request, env, cors, slug);
    if (url.pathname === '/regenerate-companies') return handleRegenerateCompanies(request, env, cors, slug);
    if (url.pathname === '/draft-warm-intro') return handleDraftWarmIntro(request, env, cors, slug);
    if (url.pathname === '/suggest-refinements') return handleSuggestRefinements(request, env, cors, slug);
    if (url.pathname === '/rerank-titles') return handleRerankTitles(request, env, cors, slug);
    if (url.pathname === '/prep') return handlePrep(request, env, cors, slug);
    if (url.pathname === '/tracker') return handleTracker(request, env, cors, slug);
    if (url.pathname === '/draft-followup') return handleDraftFollowup(request, env, cors, slug);
    if (url.pathname === '/interview-prep') return handleInterviewPrep(request, env, cors, slug);
    if (url.pathname === '/generate-digest') return handleGenerateDigest(request, env, cors, slug);
    if (url.pathname === '/admin/digest-trigger') return handleDigestTrigger(request, env, cors);
    if (url.pathname === '/notes') return handleNotes(request, env, cors, slug);
    if (url.pathname === '/contacts') return handleContacts(request, env, cors, slug);
    if (url.pathname === '/admin/contacts') return handleAdminContacts(request, env, cors);
    if (url.pathname === '/api/sprint/start') return handleSprintStart(request, env, cors, slug);
    if (url.pathname === '/api/sprint/complete') return handleSprintComplete(request, env, cors, slug);
    if (url.pathname === '/api/sprint/snooze-today') return handleSprintSnoozeToday(request, env, cors, slug);
    if (url.pathname === '/api/sprint/reset') return handleSprintReset(request, env, cors, slug);
    if (url.pathname === '/api/picks') return handlePicks(request, env, cors, slug);
    if (url.pathname === '/admin/clear-all-picks') return handleAdminClearAllPicks(request, env, cors);
    return new Response(
      'Endpoints: /api/auth/{signup,login,logout,me,change-password}, /prep, /resume, /resume-versions, /parse-resume, /skills-profile, /regenerate-profile, /regenerate-companies, /draft-warm-intro, /suggest-refinements, /rerank-titles, /tracker, /draft-followup, /interview-prep, /generate-digest, /refresh, /admin/users, /notes.',
      { status: 404, headers: cors }
    );
  },
};

async function resolveSlug(request, url) {
  const q = url.searchParams.get('user');
  if (q && /^[a-z0-9_-]{1,32}$/.test(q)) return q;
  // For POST requests we ALSO accept "user" in the JSON body — but reading body
  // here would consume it. So we only honour the query string for user routing.
  return DEFAULT_USER;
}

// --- Migration ---------------------------------------------------------
async function migrateLegacyIfNeeded(env) {
  // If user:geetu:resume:list already exists, nothing to do.
  if (await env.RESUMES.get(uk(DEFAULT_USER, 'resume:list'))) return;

  // Migrate version-list (Phase 2/3 era)
  const legacyList = await env.RESUMES.get(LEGACY_LIST);
  if (legacyList) {
    await env.RESUMES.put(uk(DEFAULT_USER, 'resume:list'), legacyList);
    const legacyActive = await env.RESUMES.get(LEGACY_ACTIVE);
    if (legacyActive) {
      await env.RESUMES.put(uk(DEFAULT_USER, 'resume:active'), legacyActive);
      const content = await env.RESUMES.get('resume:' + legacyActive);
      if (content) await env.RESUMES.put(uk(DEFAULT_USER, 'resume:' + legacyActive), content);
      // Copy every version listed
      try {
        const arr = JSON.parse(legacyList);
        for (const meta of arr) {
          const c = await env.RESUMES.get('resume:' + meta.id);
          if (c) await env.RESUMES.put(uk(DEFAULT_USER, 'resume:' + meta.id), c);
        }
      } catch (e) { /* ignore */ }
    }
    const legacyProfile = await env.RESUMES.get(LEGACY_PROFILE);
    if (legacyProfile) await env.RESUMES.put(uk(DEFAULT_USER, 'skills_profile'), legacyProfile);
    return;
  }

  // Phase 1 era — only single "default" resume, no list
  const legacy = await env.RESUMES.get(LEGACY_LEGACY_RESUME);
  if (legacy) {
    const id = 'v' + Date.now();
    const meta = { id, label: 'Original (migrated)', savedAt: new Date().toISOString(), sourceType: 'json-paste' };
    await env.RESUMES.put(uk(DEFAULT_USER, 'resume:' + id), legacy);
    await env.RESUMES.put(uk(DEFAULT_USER, 'resume:active'), id);
    await env.RESUMES.put(uk(DEFAULT_USER, 'resume:list'), JSON.stringify([meta]));
  }
}

// --- Version helpers ---------------------------------------------------
async function getVersionList(env, slug) {
  const raw = await env.RESUMES.get(uk(slug, 'resume:list'));
  if (!raw) return [];
  try { return JSON.parse(raw); } catch (e) { return []; }
}

async function saveVersionList(env, slug, list) {
  await env.RESUMES.put(uk(slug, 'resume:list'), JSON.stringify(list));
}

async function getActiveResume(env, slug) {
  if (slug === DEFAULT_USER) await migrateLegacyIfNeeded(env);
  const activeId = await env.RESUMES.get(uk(slug, 'resume:active'));
  if (!activeId) return null;
  return await env.RESUMES.get(uk(slug, 'resume:' + activeId));
}

async function saveNewVersion(env, slug, content, label, sourceType) {
  if (slug === DEFAULT_USER) await migrateLegacyIfNeeded(env);
  const list = await getVersionList(env, slug);
  const id = 'v' + Date.now();
  const meta = {
    id,
    label: label || ('Version ' + (list.length + 1)),
    savedAt: new Date().toISOString(),
    sourceType: sourceType || 'json-paste',
  };
  await env.RESUMES.put(uk(slug, 'resume:' + id), content);
  await env.RESUMES.put(uk(slug, 'resume:active'), id);
  list.unshift(meta);
  if (list.length > 20) {
    for (const old of list.slice(20)) await env.RESUMES.delete(uk(slug, 'resume:' + old.id)).catch(() => {});
    list.length = 20;
  }
  await saveVersionList(env, slug, list);
  return meta;
}

async function checkEditKey(request, env, slug) {
  // Per-user edit key stored in KV. If unset for the user, fall back to env.RESUME_EDIT_KEY
  // for backward compatibility (the original single-user shared key).
  const provided = request.headers.get('X-Edit-Key');
  if (!provided) return false;
  const stored = await env.RESUMES.get(uk(slug, 'edit_key'));
  const expected = stored || env.RESUME_EDIT_KEY;
  if (!expected) return true; // no key configured anywhere — allow (only happens during initial setup)
  return provided === expected;
}

// --- /resume -----------------------------------------------------------
async function handleResume(request, env, cors, slug) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });

  if (request.method === 'GET') {
    const stored = await getActiveResume(env, slug);
    return Response.json({ resume: stored, user: slug }, { headers: cors });
  }
  if (request.method === 'POST') {
    if (!(await checkEditKey(request, env, slug))) return Response.json({ error: 'Invalid X-Edit-Key' }, { status: 401, headers: cors });
    const body = await request.json().catch(() => null);
    if (!body || typeof body.resume !== 'string' || !body.resume.trim()) {
      return Response.json({ error: 'Body must be { resume: "..." }' }, { status: 400, headers: cors });
    }
    const meta = await saveNewVersion(env, slug, body.resume, body.label || null, body.sourceType || 'json-paste');
    try { await regenerateSkillsProfile(env, slug); } catch (e) { /* best-effort */ }
    return Response.json({ status: 'saved', version: meta, user: slug }, { headers: cors });
  }
  return new Response('Use GET or POST', { status: 405, headers: cors });
}

// --- /resume-versions --------------------------------------------------
async function handleVersions(request, env, cors, slug) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });

  if (request.method === 'GET') {
    if (slug === DEFAULT_USER) await migrateLegacyIfNeeded(env);
    const list = await getVersionList(env, slug);
    const activeId = await env.RESUMES.get(uk(slug, 'resume:active'));
    return Response.json({ versions: list, activeId, user: slug }, { headers: cors });
  }
  if (request.method === 'POST') {
    if (!(await checkEditKey(request, env, slug))) return Response.json({ error: 'Invalid X-Edit-Key' }, { status: 401, headers: cors });
    const body = await request.json().catch(() => null);
    if (!body || !body.action) return Response.json({ error: 'Body must include action' }, { status: 400, headers: cors });
    const list = await getVersionList(env, slug);

    if (body.action === 'activate') {
      if (!body.id) return Response.json({ error: 'Missing id' }, { status: 400, headers: cors });
      if (!list.find(v => v.id === body.id)) return Response.json({ error: 'Unknown version id' }, { status: 404, headers: cors });
      await env.RESUMES.put(uk(slug, 'resume:active'), body.id);
      try { await regenerateSkillsProfile(env, slug); } catch (e) { /* best-effort */ }
      return Response.json({ status: 'activated', activeId: body.id }, { headers: cors });
    }
    if (body.action === 'delete') {
      if (!body.id) return Response.json({ error: 'Missing id' }, { status: 400, headers: cors });
      const activeId = await env.RESUMES.get(uk(slug, 'resume:active'));
      if (body.id === activeId) return Response.json({ error: 'Cannot delete the active version. Activate another version first.' }, { status: 400, headers: cors });
      await env.RESUMES.delete(uk(slug, 'resume:' + body.id));
      await saveVersionList(env, slug, list.filter(v => v.id !== body.id));
      return Response.json({ status: 'deleted' }, { headers: cors });
    }
    if (body.action === 'get') {
      if (!body.id) return Response.json({ error: 'Missing id' }, { status: 400, headers: cors });
      const content = await env.RESUMES.get(uk(slug, 'resume:' + body.id));
      if (!content) return Response.json({ error: 'Version not found' }, { status: 404, headers: cors });
      return Response.json({ resume: content }, { headers: cors });
    }
    if (body.action === 'rename') {
      if (!body.id || typeof body.label !== 'string') return Response.json({ error: 'Missing id or label' }, { status: 400, headers: cors });
      const idx = list.findIndex(v => v.id === body.id);
      if (idx < 0) return Response.json({ error: 'Unknown version id' }, { status: 404, headers: cors });
      list[idx].label = body.label.slice(0, 80);
      await saveVersionList(env, slug, list);
      return Response.json({ status: 'renamed' }, { headers: cors });
    }
    return Response.json({ error: 'Unknown action' }, { status: 400, headers: cors });
  }
  return new Response('Use GET or POST', { status: 405, headers: cors });
}

// Deterministic augmentation: add domain-standard frameworks/regulations
// based on signals in the parsed profile. Belt-and-suspenders to the AI prompt:
// even if the AI is sparse, a banking-GRC profile is guaranteed to include
// NIST CSF, COSO, FFIEC, etc.
function augmentProfileWithStandards(profile) {
  const haystack = [
    ...(profile.industries || []),
    ...(profile.specialties || []),
    ...(profile.keywords || []),
    profile.primaryRole || '',
    profile.summary || '',
  ].join(' ').toLowerCase();

  const adds = { frameworks: [], regulations: [] };

  if (/\b(grc|governance|risk management|compliance|audit|internal controls)\b/.test(haystack)) {
    adds.frameworks.push('nist csf', 'nist 800-53', 'iso 27001', 'iso 27002', 'soc 2', 'cobit', 'coso', 'coso erm', 'sox itgc');
    adds.regulations.push('sox');
  }
  if (/\b(bank|financial services|capital markets|wealth|asset|lending|credit risk|treasury)\b/.test(haystack)) {
    adds.frameworks.push('ffiec', 'occ heightened standards', 'basel iii', 'pci dss');
    adds.regulations.push('sox', 'glba', 'bsa', 'aml', 'kyc', 'dodd-frank');
  }
  if (/\b(healthcare|health it|clinical|pharma|biotech|life sciences|medical)\b/.test(haystack)) {
    adds.frameworks.push('hipaa security rule', 'hipaa privacy rule', 'hitrust', 'fda qsr', '21 cfr part 11');
    adds.regulations.push('hipaa', 'hitech');
  }
  if (/\b(cloud|saas|enterprise tech|infrastructure|platform engineering)\b/.test(haystack)) {
    adds.frameworks.push('soc 2', 'iso 27001', 'csa ccm');
  }
  if (/\b(cyber|cybersecurity|security|infosec|threat|vulnerability|identity)\b/.test(haystack)) {
    adds.frameworks.push('nist csf', 'nist 800-53', 'iso 27001', 'mitre att&ck', 'owasp', 'cis controls', 'zero trust');
    adds.regulations.push('nydfs part 500', 'sec cyber disclosure rule');
  }
  if (/\b(trading|capital markets|asset management|hedge fund|fx)\b/.test(haystack)) {
    adds.frameworks.push('frtb');
    adds.regulations.push('mifid ii', 'sec cyber disclosure rule');
  }
  if (/\b(privacy|data protection|gdpr|personal data)\b/.test(haystack)) {
    adds.regulations.push('gdpr', 'ccpa', 'cpra');
  }
  if (/\b(program management|portfolio|pmo)\b/.test(haystack)) {
    adds.frameworks.push('pmi pmbok', 'prince2', 'agile', 'scrum', 'safe', 'lean', 'six sigma');
  }
  if (/\b(federal|government|fedramp|public sector|dod|defense)\b/.test(haystack)) {
    adds.frameworks.push('fedramp', 'nist 800-171', 'cmmc', 'fisma');
  }

  for (const [field, items] of Object.entries(adds)) {
    const existing = new Set((profile[field] || []).map(s => String(s).toLowerCase()));
    profile[field] = profile[field] || [];
    for (const item of items) {
      if (!existing.has(item)) {
        profile[field].push(item);
        existing.add(item);
      }
    }
  }
  return profile;
}

// --- /skills-profile ---------------------------------------------------
async function regenerateSkillsProfile(env, slug) {
  if (!env.ANTHROPIC_API_KEY) return null;
  const resumeJson = await getActiveResume(env, slug);
  if (!resumeJson) return null;
  const activeId = await env.RESUMES.get(uk(slug, 'resume:active'));

  // Read the user's existing size preferences so the AI can bias
  // targetCompanies toward sizes the user actually wants. New format
  // is companySizeMix (object with %s); fall back to companySizePreferences
  // (older array format) for backward compat.
  let sizeMix = null;
  let preservedMix = null;
  let preservedPrefs = null;
  try {
    const existingRaw = await env.RESUMES.get(uk(slug, 'skills_profile'));
    if (existingRaw) {
      const existing = JSON.parse(existingRaw);
      if (existing && typeof existing.companySizeMix === 'object' && existing.companySizeMix) {
        sizeMix = existing.companySizeMix;
        preservedMix = existing.companySizeMix;
      }
      if (Array.isArray(existing.companySizePreferences) && existing.companySizePreferences.length) {
        preservedPrefs = existing.companySizePreferences;
        if (!sizeMix) {
          // Synthesize equal-weight mix from picked prefs
          const share = Math.floor(100 / existing.companySizePreferences.length);
          sizeMix = {};
          existing.companySizePreferences.forEach((k, i, arr) => {
            sizeMix[k] = (i === arr.length - 1) ? 100 - share * (arr.length - 1) : share;
          });
        }
      }
    }
  } catch (e) { /* fall through with defaults */ }
  if (!sizeMix) sizeMix = { startup: 33, midsize: 33, large: 34 };
  const _norm = (v) => Math.max(0, Math.min(100, Number(v) || 0));
  sizeMix = {
    startup: _norm(sizeMix.startup),
    midsize: _norm(sizeMix.midsize),
    large: _norm(sizeMix.large),
  };
  const sizeInstruction = (() => {
    const total = sizeMix.startup + sizeMix.midsize + sizeMix.large || 1;
    const pct = {
      startup: Math.round(sizeMix.startup * 100 / total),
      midsize: Math.round(sizeMix.midsize * 100 / total),
      large: Math.round(sizeMix.large * 100 / total),
    };
    const excluded = ['startup','midsize','large'].filter(k => pct[k] === 0);
    const excludeLine = excluded.length
      ? `Do NOT suggest any ${excluded.join(' or ')} employers — the user has explicitly excluded them. `
      : '';
    return `IMPORTANT: the user wants their target-company list to mirror this size mix (sums to ~100%): startups ${pct.startup}% / mid-size ${pct.midsize}% / large ${pct.large}%. ${excludeLine}Across the 15-25 targetCompanies you suggest, the proportion of each size category must roughly match those percentages. Size definitions: startup = under 500 employees / typically Series A-C; midsize = 500-10k employees / established but not Fortune 500; large = 10k+ employees / Fortune 500 / public. For startup suggestions prefer "greenhouse"/"lever"/"ashby" atsHint; for large prefer "workday".`;
  })();

  const prompt = `Analyze this resume and produce a structured skills profile that gives the candidate a manageable, signal-dense starting list.

CRITICAL: Be precise, not exhaustive. The user will trim to a tight bullseye (5 titles / 5 industries / 25 skills) via a wizard, so your job is to surface the BEST few per field — not every possible variant. Exact caps below — respect them strictly. Quality over coverage. Better to give the user 10 strong, distinct options than 30 with overlap. If you find yourself listing minor variants of the same thing, consolidate.

INFERENCE RULES — also INCLUDE industry-standard items even when not literally typed in the resume:

  - If the resume describes "GRC", "governance risk and compliance", "third-party risk", or audit/risk work at US financial institutions → INCLUDE the standard frameworks for that lane: nist csf, nist 800-53, iso 27001, iso 27002, soc 2, coso, cobit, ffiec, occ heightened standards, sox itgc, pci dss. INCLUDE the standard regulations: sox, glba, bsa, aml, kyc, dodd-frank, ny dfs part 500, sec cyber disclosure rule.

  - If the resume mentions banking, payments, or cards → also include relevant ones: pci dss, swift csp, bsa, aml.

  - If the resume mentions healthcare or health systems → also include: hipaa security rule, hipaa privacy rule, hitech, hitrust, fda qsr, 21 cfr part 11 (if devices/clinical).

  - If the resume mentions cloud, SaaS, or enterprise tech → also include: soc 2, iso 27001, csa ccm, fedramp (if government-adjacent), nist 800-53.

  - If the resume mentions trading, capital markets, or asset management → also include: mifid ii, frtb, sec cyber disclosure rule.

  - If the resume mentions program management / PMO → include: pmi pmbok, prince2 (if european), agile, scrum, safe.

  These are inferences based on what a senior practitioner in that domain would universally know and have touched. Be reasonable — do not include irrelevant ones. If a resume is purely healthcare, do not add banking-specific items.

CRITICAL: The user's profession determines what frameworks/regulations they'd know. A senior GRC leader at a US bank would unquestionably know NIST CSF, COSO, SOX ITGC, FFIEC even if they don't list them by name on their resume — include the 3-5 most central ones, not every adjacent standard.

SENIORITY CALIBRATION — BE CONSERVATIVE:

- seniorityLevel should match the candidate's MOST RECENT title, not their aspirational ceiling. A "Principal, X" or "Senior Director, X" maps to seniorityLevel="vp" at most. Do NOT default to "c-suite" unless their most recent title literally contains Chief/CEO/CTO/CIO/COO/CFO/President.
- careerStage: a candidate with VP/SVP/EVP/Chief/President in recent titles → "executive". Otherwise prefer "senior" over "executive" when on the boundary. The user can edit upward; they cannot edit a too-aggressive default downward without noticing.
- targetTitles must stay within current level + 1 rung. NEVER include CXO titles unless the candidate's current title is already C-suite.

Return ONLY a JSON object with this exact shape (no prose, no code fences):

{
  "primaryRole": "one-line description of the role this person targets",
  "summary": "2-3 sentence summary of their professional background and what they bring",
  "seniorityLevel": "one of: junior | mid | senior | principal | director | vp | c-suite",
  "careerStage": "one of: internship | new-grad | early-career | mid-career | senior | executive",
  "seniorityTitles": ["..."],
  "targetTitles": ["..."],
  "titlesPool": ["..."],
  "industries": ["..."],
  "industriesPool": ["..."],
  "specialties": ["..."],
  "keywords": ["..."],
  "technologies": ["..."],
  "frameworks": ["..."],
  "skillsPool": ["..."],
  "regulations": ["..."],
  "certifications": ["..."],
  "negativeKeywords": ["..."],
  "remotePreferred": true,
  "salaryFloor": 200000,
  "targetCompanies": [{"name":"Moody's","atsHint":"workday","atsUrl":"https://moodys.wd5.myworkdayjobs.com/Careers","why":"top global credit rating agency, frequently hires senior analysts and managing directors in structured credit"}],
  "preferredLocations": ["New York City", "Remote (US)"],
  "remotePreference": "hybrid"
}

Field guidance (ALL fields lowercase strings):

- seniorityTitles (5-10): title words at THIS person's level. e.g. ["vp", "director", "head of", "principal", "senior director", "executive director", "chief"].

- careerStage: classify the candidate's CURRENT stage based on years of experience, most-recent titles, and whether they are still in school:
  - "internship": still in school (undergrad/grad), looking for summer/fall/winter internship
  - "new-grad": graduated within the last 12 months, 0-1 yrs full-time work
  - "early-career": 1-5 yrs full-time, IC roles (analyst, associate, junior engineer)
  - "mid-career": 5-12 yrs, senior IC or first-line manager
  - "senior": 12-20 yrs, director/sr director/principal/staff
  - "executive": 18+ yrs, VP+/C-suite. Use this for anyone whose recent titles include VP, SVP, EVP, Chief, President, Head-of (org-wide).
  This field drives which jobs and companies we surface — be precise.

POOL FIELDS — RANKED SWAP-IN SUGGESTIONS:

In addition to the primary selection fields (targetTitles, industries, keywords/technologies/frameworks), emit three "pool" fields with WIDER ranked candidate lists the user can swap into the primary set via the wizard UI:

  - titlesPool (up to 15): the same shape and rules as targetTitles, but a wider ranked list. The first 5 entries MUST be identical to targetTitles in the same order. Entries 6-15 are your next-best title alternatives (still respecting the seniority-rung rule). The user picks one to swap when they remove a top-5 chip.

  - industriesPool (up to 15): same shape as industries. First 5 entries identical to industries; entries 6-15 are next-best industry candidates the user can promote.

  - skillsPool (up to 45): a SINGLE merged, deduped, ranked list of distinct skill terms drawn from keywords + technologies + frameworks. The first 15 entries are the ones you'd put in front of the user as their default "skills" set (most signal-dense, most distinctive). Entries 16-45 are next-best alternatives. Skip generic words; favor distinctive terms a recruiter would scan for. The wizard merges keywords/technologies/frameworks into a single bullseye, so skillsPool is what powers that picker — make the first 15 the BEST 15.

  Pools must be in strict descending order of usefulness — the user assumes earlier = more important. Lowercase strings, no duplicates.

- targetTitles (up to 5): SPECIFIC titles matching the candidate's ACTUAL current level and at most ONE rung above. Do NOT jump 2-3 rungs (e.g. a Sr Director should NOT see Chief titles — only Director, Sr Director, VP, Head of). Concrete and varied within the band. e.g. for a Sr Director banking-tech leader targeting director/vp roles: ["head of digital transformation", "vp banking technology", "vp grc", "director of enterprise architecture", "senior director, technology", "head of it strategy", "vp third-party risk management", "director of digital banking"]. Each title must be tokenizable into 2+ meaningful words.

- industries (up to 5): broad sectors where the candidate has DIRECT hands-on experience (not just employer-adjacent). Each industry will be a heavy match signal, so be selective — only the sectors they'd actually target. e.g. ["banking", "commercial banking", "fintech", "consulting", "regtech"]. AVOID umbrella terms like "saas" or "enterprise software" unless the candidate specifically targets B2B software.

- specialties (10-20): granular sub-domains and functional areas with HANDS-ON depth (not just touched on a project). These are surfaced to the AI re-ranker as context, so be specific. e.g. ["credit risk modeling", "regulatory reporting", "digital transformation", "vendor management", "m&a integration"]. Pull from the actual bullets — if the resume doesn't directly evidence a specialty, don't list it.

- keywords (up to 15): high-signal terms from THIS resume that should BOOST a job's score when present in its title or description. Mix of: domain words, methodologies (agile, scrum, lean), outcome areas (cost reduction, revenue growth), and concepts (digital strategy, automation). NO generic words like "team" or "leadership" alone. Note: total skills budget across keywords + technologies + frameworks should sum to ~15-20, because the user trims to 15 in the wizard.

- technologies (up to 10 if present in resume): the most SIGNATURE tools/platforms/vendors mentioned — not every tool ever touched. Pick the ones a recruiter would scan for. If resume doesn't mention specific tools, return empty array.

- frameworks (up to 5, the most CENTRAL ones — be EXHAUSTIVE in scanning but cap at 5): standards, control frameworks, methodologies, and best-practice frameworks. Be selective — pick the ones the candidate would actually reference in their own self-description, not every adjacent standard. Common buckets to draw from:

  Cybersecurity & risk: nist csf, nist 800-53, nist 800-171, nist 800-37, nist 800-30, nist 800-66, nist rmf, iso 27001, iso 27002, iso 27017, iso 27018, iso 31000, iso 22301, soc 2, soc 1, ssae 18, mitre att&ck, owasp, owasp top 10, cis controls, cis benchmarks, fair, octave, cobit, togaf, sabsa, zero trust, devsecops, cmmc, disa stig, csa ccm, csa star, swift csp, isa 62443, nerc cip, iso 13485, iec 62304

  Privacy & compliance: hipaa security rule, hipaa privacy rule, hitech, hitrust, ferpa, glba safeguards, ccpa/cpra controls, pci dss, pci pin, c5, irap, fedramp moderate, fedramp high, statefedramp, fisma

  Governance/audit/IT: itil v3, itil 4, coso erm, coso icfr, sox itgc, ffiec it handbook, ffiec cat, occ heightened standards, cobit 2019, val it, risk it

  Healthcare/life-sciences: 21 cfr part 11, gxp, gcp (ich gcp), gmp, gdp, gvp, fda qsr, iso 14971, iec 82304

  Financial frameworks (non-regulation): basel iii capital, cecl, ifrs 9 ecl, solvency ii, frtb, ifrs 17

  Methodology / delivery: pmi pmbok, prince2, lean, six sigma, agile, scrum, safe, less, kanban, waterfall, dama dmbok, togaf adm, archimate

  If a framework appears once anywhere in the resume — even in passing — include it. The point of this field is high recall.

- regulations (any present, also be EXHAUSTIVE): specific regulatory regimes / laws / acts the person has worked with. Be liberal here too — include both US and international. Examples (include any present):

  Banking/finance: dodd-frank, basel iii, basel iv, sox, mifid ii, ccar, dfast, fcra, glba, bsa, aml, kyc, fatca, crs, emir, dora

  Privacy/data: gdpr, ccpa, cpra, lgpd, pipeda, hipaa (privacy/security rules can also live here)

  Healthcare/pharma: hipaa, hitech, 21 cfr part 11, fda 510k, ich gcp, gdpr (in eu trials)

  Cyber/critical infrastructure: nist (when used as a regulatory baseline), fisma, dfars, cmmc, ny shield act, nydfs part 500, sec cyber disclosure rule

  Accounting: gaap, ifrs, ifrs 9, ifrs 16, asc 842, asc 606

  If a regulation appears anywhere in the resume — include it. Do not over-categorize: if uncertain whether something is a framework vs regulation, put it in both fields.

- certifications (any present): CFA, FRM, PMP, CISSP, CISM, MBA, CPA, six sigma, scrum master, etc.

- negativeKeywords (up to 5, ONLY universally-junior signals): things to NEVER show. Stick to terms that are ALWAYS junior regardless of role family: ["intern", "entry level", "new grad", "graduate program"]. DO NOT include "assistant" (EU/UK firms title Director-level roles "Assistant Vice President"), "associate" (Associate Director / Associate Partner are senior), "staff" (Chief of Staff is senior), "analyst" (Senior Analyst / Investment Analyst can be appropriate), "coordinator" (Program Coordinator can be a real career role). The scorer applies these as token-blocks with a senior-context guard, so over-listing here causes silent kills.

- remotePreferred: true if resume signals remote/hybrid preference or recent remote experience.

- salaryFloor: reasonable minimum US base salary given seniority. For c-suite ~350k, vp ~250k, director ~180k, senior 130k.
- targetCompanies: array of 15-25 specific companies this person would realistically target next. ${sizeInstruction} Each entry: {name: string, atsHint: one of "greenhouse"|"lever"|"ashby"|"workday"|"unknown", why: one-sentence reason this company fits}.\n\n  **OUR PRODUCT EDGE: surface MID-MARKET / hidden-gem employers, not the Fortune 100 giants every aggregator already covers.** For senior/exec candidates, STRONGLY PREFER mid-market firms (500-15,000 employees, sub-S&P-400) in the candidate's niche over the obvious giants. Use the giants only when the candidate's industries genuinely demand them.\n\n  CONCRETE GUIDANCE PER CAREER STAGE (set careerStage first, then choose companies that fit):\n  - executive / senior-exec: mid-market PE-backed firms, specialty firms, super-regional banks, mid-tier consultancies (Crowe/BDO/Grant Thornton/RSM/Baker Tilly/FTI/AlixPartners/Riveron/Capco/West Monroe/Slalom — NOT Big 4). For banking → super-regionals (First Citizens, Comerica, Zions, M&T, Webster, Synovus, Western Alliance, Texas Capital, Cullen/Frost, Fifth Third, KeyBank, Huntington, BOK, Cadence, Atlantic Union). For GRC/cyber → Vanta/Drata/OneTrust/AuditBoard/LogicGate/MetricStream/Diligent/Resolver/ProcessUnity/Aravo. For credit/risk → Moody's Analytics/S&P/Fitch/KBRA/Morningstar DBRS rather than the rating-agency giants alone; also Ares/Owl Rock/Antares/Golub/Crescent/Trinity Capital.\n  - senior (director/principal): same mid-market bias, slightly fewer C-suite-only firms.\n  - mid-career: balanced — include both mid-market and 1-2 well-known reach firms in the niche.\n  - early-career (3-7 yrs): a mix of named structured programs at large firms AND specialist mid-market firms where they can grow fast.\n  - new-grad (0-2 yrs): MUST be companies with named entry-level / analyst / new-grad programs (Goldman Analyst, McKinsey BA, Capital One Analyst, JPM Analyst, Big 4 Audit Associate, Google STEP, FAANG new-grad SWE, etc.). Mix Fortune 500 structured programs with mid-market firms that have published new-grad tracks.\n  - internship: companies with **published, current** internship programs only.\n\n  Include a mix of large, mid-market, AND mid-stage startup employers across the candidate's niche — DO NOT exclude well-known firms; the user needs maximum coverage to get hired. The mid-market and mid-stage emphasis is for VARIETY, not exclusion.\n\n  **MID-STAGE STARTUPS ($10-99M ARR / Series B-D / 50-500 employees) are PRIME territory.** They hire fast, post on Greenhouse/Lever/Ashby (not Workday), need senior leaders as they scale, and are dramatically under-aggregated. EVERY senior/exec profile should include 4-8 mid-stage startups in the candidate's niche. Examples by domain:\n  - Risk / GRC / RegTech: AuditBoard, LogicGate, MetricStream, Diligent, Resolver, ProcessUnity, Aravo, Riskonnect, Coalition, At-Bay, Resilience, Cowbell Cyber, Corvus Insurance, Sardine, Persona, Socure, Alloy, Middesk\n  - Fintech / Banking-adjacent: Pipe, Column, Treasury Prime, Unit, Mercury, Ramp, Brex, Lithic, Modern Treasury, Increase, Fragment, Stitch, Mainstreet, Pilot, Finch\n  - Healthtech: Headway, Cohere Health, Spring Health, Octave, Thirty Madison, Transcarent, Forge Health, Modern Health, Nuna, Aledade, Formation Bio, Spark Advisors, Truepill, Ro, Maven, Hims, Sword Health, Lyra, Wellth\n  - Climate / energy: Watershed, Persefoni, Sweep, Patch, Crusoe, Form Energy, Sila Nanotechnologies, Tessera Therapeutics\n  - Developer tools / infra: Linear, Vercel, PlanetScale, Supabase, Railway, Replicate, Pinecone, Modal, Anthropic, Hugging Face\n\n  When the candidate is in a niche, include 4-8 startups from that niche specifically. Use atsHint='greenhouse' for most (Greenhouse is the dominant ATS in this segment). The atsUrl is OPTIONAL for non-workday entries.\n\n  For "workday" entries you MUST include atsUrl: full public Workday careers URL. Only set atsHint="workday" if you actually know the URL — otherwise use "unknown". For other atsHint values atsUrl is optional. Examples of verified URL patterns: https://moodys.wd5.myworkdayjobs.com/Careers, https://wf.wd1.myworkdayjobs.com/WellsFargoJobs, https://citi.wd5.myworkdayjobs.com/2, https://capitalone.wd12.myworkdayjobs.com/Capital_One. When in doubt about a Workday URL, use atsHint="unknown" — guessing breaks the scrape.
- preferredLocations: array of locations (cities, regions, or "Remote") the person prefers. Extract from resume signals like current location, past locations, and any stated preferences. Examples: ["New York City", "San Francisco", "Remote (US)"]. If unsure include both their current city and "Remote (US)" as fallbacks.
- remotePreference: one of "remote-only" | "hybrid" | "onsite" | "any". Default to "any" if no signal. Use "remote-only" if resume shows recent fully-remote roles or explicit remote preference. Use "hybrid" if mixed signals or current employer is hybrid. Use "onsite" only if all recent roles are onsite and no remote signal.

RESUME (JSON):
${resumeJson}`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 5000, messages: [{ role: 'user', content: prompt }] }),
    });
    if (!r.ok) return null;
    const data = await r.json();
    const text = data.content?.[0]?.text || '';
    const cleaned = text.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/\s*```$/, '').trim();
    let parsed;
    try { parsed = JSON.parse(cleaned); } catch (e) { return null; }
    // Normalize: ensure all array fields exist and are lowercase strings
    for (const k of ['seniorityTitles','targetTitles','titlesPool','industries','industriesPool','specialties','keywords','technologies','frameworks','skillsPool','regulations','certifications','negativeKeywords']) {
      if (!Array.isArray(parsed[k])) parsed[k] = [];
      else parsed[k] = parsed[k].filter(x => typeof x === 'string').map(x => x.toLowerCase().trim()).filter(Boolean);
    }
    // Deterministic augmentation: add standard frameworks/regulations based on profile signals.
    // This ensures a banking-GRC profile always gets NIST CSF, COSO, FFIEC etc. even if the AI omits them.
    augmentProfileWithStandards(parsed);
    // Pool fallback: if AI omitted a pool, derive it from the primary field.
    // The wizard UI assumes pool[:N] == primary[:N], so backfilling keeps the
    // suggestion-row UX functional even for older prompts or partial responses.
    if (!parsed.titlesPool || !parsed.titlesPool.length) parsed.titlesPool = (parsed.targetTitles || []).slice(0, 15);
    if (!parsed.industriesPool || !parsed.industriesPool.length) parsed.industriesPool = (parsed.industries || []).slice(0, 15);
    if (!parsed.skillsPool || !parsed.skillsPool.length) {
      const merged = [].concat(parsed.keywords || [], parsed.technologies || [], parsed.frameworks || []);
      const seen = new Set();
      parsed.skillsPool = merged.filter(s => {
        if (!s || seen.has(s)) return false;
        seen.add(s); return true;
      }).slice(0, 45);
    }
    // Pool invariant: first N of pool must equal the primary selection.
    // If the AI accidentally re-ordered things, prepend missing primaries.
    function _alignPool(primary, pool, takeN) {
      const out = [];
      const seen = new Set();
      for (const p of (primary || []).slice(0, takeN)) {
        if (!seen.has(p)) { out.push(p); seen.add(p); }
      }
      for (const p of (pool || [])) {
        if (!seen.has(p)) { out.push(p); seen.add(p); }
      }
      return out;
    }
    parsed.titlesPool = _alignPool(parsed.targetTitles, parsed.titlesPool, 5).slice(0, 15);
    parsed.industriesPool = _alignPool(parsed.industries, parsed.industriesPool, 5).slice(0, 15);
    // skillsPool: align against the merged keywords+technologies+frameworks (top 15)
    const mergedTop15 = [].concat(parsed.keywords || [], parsed.technologies || [], parsed.frameworks || []).slice(0, 15);
    parsed.skillsPool = _alignPool(mergedTop15, parsed.skillsPool, 15).slice(0, 45);
    // Extract structured contact + biographical fields from the raw resume JSON
    // (already produced by /parse-resume in shape {personal: {name,phone,email,location,linkedin}, education, experience}).
    // These power the auto-fill extension and the wizard's "Application profile" step.
    let _personal = {}, _exp0 = {}, _edu0 = {};
    try {
      const _rj = JSON.parse(resumeJson);
      _personal = _rj.personal || {};
      _exp0 = (Array.isArray(_rj.experience) && _rj.experience[0]) || {};
      _edu0 = (Array.isArray(_rj.education) && _rj.education[0]) || {};
    } catch (e) { /* resumeJson might not be JSON */ }
    const _extracted = {
      // Direct contact fields used by Greenhouse/Lever/Ashby/Workday autofill
      phone: _personal.phone || _personal.phoneNumber || '',
      email: _personal.email || '',
      location: _personal.location || _personal.address || '',
      linkedinUrl: _personal.linkedin || _personal.linkedinUrl || '',
      githubUrl: _personal.github || _personal.githubUrl || '',
      websiteUrl: _personal.website || _personal.portfolio || '',
      // Current role context — defaults from first experience entry
      currentCompany: _exp0.company || '',
      currentTitle: _exp0.title || _exp0.role || '',
      // Education for "where did you study?" fields
      school: _edu0.school || _edu0.institution || '',
      degree: _edu0.degree || '',
      graduationYear: _edu0.year || _edu0.graduationYear || _edu0.endYear || '',
      // Inferred from resume (defaults reasonable for US-based candidates)
      workAuthorization: _personal.workAuthorization || 'US Citizen',
      requiresSponsorship: _personal.requiresSponsorship || 'No',
      // Full-name fields broken out (some apps want them separately)
      firstName: (_personal.name || '').split(/\s+/)[0] || '',
      lastName: (_personal.name || '').split(/\s+/).slice(1).join(' ') || '',
    };
    const profile = Object.assign({}, parsed, _extracted, { resumeId: activeId, generatedAt: new Date().toISOString(), user: slug });
    // Preserve the user's wizard-set size preferences across regen
    if (preservedMix) profile.companySizeMix = preservedMix;
    // Preserve wizard-set match weights across regen
    try {
      const existRaw = await env.RESUMES.get(uk(slug, 'skills_profile'));
      if (existRaw) {
        const exist = JSON.parse(existRaw);
        if (exist && exist.matchWeights && typeof exist.matchWeights === 'object') {
          profile.matchWeights = exist.matchWeights;
        }
      }
    } catch (e) { /* ignore */ }
    if (preservedPrefs) profile.companySizePreferences = preservedPrefs;
    await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(profile));
    return profile;
  } catch (e) { return null; }
}

async function handleSkillsProfile(request, env, cors, slug) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  if (request.method === 'GET') {
    if (slug === DEFAULT_USER) await migrateLegacyIfNeeded(env);
    const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
    if (!raw) return Response.json({ profile: null, user: slug }, { headers: cors });
    try { return Response.json({ profile: JSON.parse(raw), user: slug }, { headers: cors }); }
    catch (e) { return Response.json({ profile: null }, { headers: cors }); }
  }
  if (request.method === 'POST') {
    // Accept either X-Edit-Key / X-Admin-Key (legacy) OR a session Bearer
    // token for this slug (the new auth surface so logged-in users can
    // edit their own profile from /account.html without copying keys).
    let authed = await checkEditKey(request, env, slug);
    if (!authed) {
      try {
        const sess = await sessionFromRequest(request, env);
        if (sess && sess.slug === slug) authed = true;
      } catch (e) {}
    }
    if (!authed) return Response.json({ error: 'Invalid X-Edit-Key (or sign in)' }, { status: 401, headers: cors });
    const body = await request.json().catch(() => ({}));
    // Patch mode: merge user-supplied additions into the existing profile (manual edits)
    if (body && body.patchFields && typeof body.patchFields === 'object') {
      const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
      const existing = raw ? JSON.parse(raw) : {};
      const updated = Object.assign({}, existing);
      const SCALAR_FIELDS = new Set(['salaryFloor', 'remotePreferred', 'seniorityLevel', 'careerStage', 'primaryRole', 'summary', 'companySizeMix', 'companySizePreferences', 'dailyTarget', 'recencyWindow', 'defaultSort', 'hideNoSalary', 'negativeTitles', 'matchWeights', 'signalStability', 'phone', 'email', 'location', 'linkedinUrl', 'githubUrl', 'websiteUrl', 'workAuthorization', 'requiresSponsorship', 'currentCompany', 'currentTitle', 'school', 'degree', 'graduationYear', 'firstName', 'lastName', 'excludeCompanies', 'sprintStart', 'sprintDays', 'sprintDailyQuota', 'sprintDaysOfWeek', 'sprintNudgeTime', 'sprintRecapTime', 'sprintTimezone', 'sprintSnoozedDays', 'networkCompanies', 'resumeHealth', 'resumeHealthHistory', 'lastMonthlyReportAt', 'dismissalPatterns']);
      for (const [field, items] of Object.entries(body.patchFields)) {
        if (SCALAR_FIELDS.has(field)) {
          updated[field] = items;
          continue;
        }
        if (!Array.isArray(items)) continue;
        const normalized = items.filter(x => typeof x === 'string').map(x => x.toLowerCase().trim()).filter(Boolean);
        // Replace mode: client sends complete final array (allows removal too)
        // Deduplicate
        const seen = new Set();
        const deduped = [];
        for (const item of normalized) {
          if (!seen.has(item)) { seen.add(item); deduped.push(item); }
        }
        updated[field] = deduped;
      }
      updated.user = slug;
      updated.editedAt = new Date().toISOString();
      await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(updated));
      return Response.json({ profile: updated, status: 'patched' }, { headers: cors });
    }
    // Default: regenerate from active resume via AI
    const profile = await regenerateSkillsProfile(env, slug);
    if (!profile) return Response.json({ error: 'Could not generate profile. Make sure an active resume is saved.' }, { status: 500, headers: cors });
    return Response.json({ profile }, { headers: cors });
  }
  return new Response('Use GET or POST', { status: 405, headers: cors });
}

// --- /parse-resume -----------------------------------------------------
async function handleParseResume(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY secret' }, { status: 500, headers: cors });
  if (!(await checkEditKey(request, env, slug))) return Response.json({ error: 'Invalid X-Edit-Key' }, { status: 401, headers: cors });

  let body;
  try { body = await request.json(); } catch (e) { return Response.json({ error: 'Body must be valid JSON' }, { status: 400, headers: cors }); }
  const rawText = (body.text || '').trim();
  const filename = body.filename || 'resume';
  if (!rawText) return Response.json({ error: 'Missing text' }, { status: 400, headers: cors });
  if (rawText.length > 60000) return Response.json({ error: 'Resume text is too long (>60k chars).' }, { status: 400, headers: cors });

  const prompt = `You are converting a raw resume into structured JSON for a job-application tool.

Return ONLY a JSON object with EXACTLY this shape:

{
  "personal": { "name": "...", "location": "...", "phone": "...", "email": "...", "linkedin": "..." },
  "summary": "...",
  "skills": ["..."],
  "experience": [{ "company": "...", "location": "...", "title": "...", "start": "...", "end": "...", "bullets": ["..."] }],
  "education": [{ "school": "...", "degree": "...", "field": "...", "year": "..." }],
  "certifications": ["..."]
}

Rules: missing fields use empty string/array. Keep bullets atomic. Preserve numbers and product names exactly. Do not invent. Do not wrap in markdown.

RAW RESUME TEXT (from ${filename}):
${rawText}`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 4096, messages: [{ role: 'user', content: prompt }] }),
    });
    if (!r.ok) { const err = await r.text(); return Response.json({ error: 'Anthropic API error', details: err }, { status: 502, headers: cors }); }
    const data = await r.json();
    const text = data.content?.[0]?.text || '';
    const cleaned = text.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/\s*```$/, '').trim();
    let parsed;
    try { parsed = JSON.parse(cleaned); }
    catch (e) { return Response.json({ error: 'AI did not return valid JSON', raw: text.slice(0, 2000) }, { status: 502, headers: cors }); }
    if (!parsed.personal || !parsed.personal.name) {
      return Response.json({ error: 'Parsed JSON missing personal.name', parsed }, { status: 502, headers: cors });
    }
    const meta = await saveNewVersion(env, slug, JSON.stringify(parsed, null, 2), filename, 'upload');
    try { await regenerateSkillsProfile(env, slug); } catch (e) { /* best-effort */ }
    return Response.json({ status: 'saved', version: meta, parsed }, { headers: cors });
  } catch (e) { return Response.json({ error: 'Worker error', message: String(e) }, { status: 500, headers: cors }); }
}

// --- /refresh — trigger GitHub Action ----------------------------------
async function triggerRefreshWorkflow(env) {
  if (!env.GH_REPO_TOKEN) return { ok: false, error: 'GH_REPO_TOKEN missing' };
  const r = await fetch(`https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/actions/workflows/${GH_WORKFLOW}/dispatches`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.GH_REPO_TOKEN}`,
      'Accept': 'application/vnd.github+json',
      'User-Agent': 'cool-darkness-dce5-worker',
    },
    body: JSON.stringify({ ref: 'main' }),
  });
  if (r.status === 204) return { ok: true };
  const errText = await r.text().catch(() => '');
  return { ok: false, status: r.status, details: errText };
}
async function handleRefresh(request, env, cors) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  const res = await triggerRefreshWorkflow(env);
  if (res.ok) return Response.json({ status: 'triggered' }, { headers: cors });
  if (res.error === 'GH_REPO_TOKEN missing') return Response.json({ error: 'Worker missing GH_REPO_TOKEN secret' }, { status: 500, headers: cors });
  return Response.json({ error: 'GitHub API error', status: res.status, details: res.details }, { status: 502, headers: cors });
}

// --- /prep -------------------------------------------------------------
async function handlePrep(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only.', { status: 405, headers: cors });
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY secret' }, { status: 500, headers: cors });
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  const resumeJson = await getActiveResume(env, slug);
  if (!resumeJson) return Response.json({ error: 'No resume saved yet for user ' + slug + '. Open the dashboard, click Resume, upload, Save.' }, { status: 500, headers: cors });

  let body;
  try { body = await request.json(); } catch (e) { return Response.json({ error: 'Body must be valid JSON' }, { status: 400, headers: cors }); }
  const { jobTitle, company, jobDescription = '', jobUrl = '' } = body;
  if (!jobTitle || !company) return Response.json({ error: 'Missing jobTitle or company' }, { status: 400, headers: cors });

  // Extract candidate's name for personalization
  let candidateName = '';
  try { const r = JSON.parse(resumeJson); candidateName = r?.personal?.name || ''; } catch (e) { /* ignore */ }

  const prompt = `You are helping ${candidateName || 'a candidate'} apply for a job. Based on the resume below, produce SEVEN outputs:

1. A tailored 3-sentence resume summary highlighting why they're a strong fit.
2. A 250-word cover letter, professional but warm.
3. A 100-word LinkedIn intro message to a recruiter or hiring manager at this company.
4. A FULL TAILORED RESUME for this specific job — structured JSON. Re-order skills and re-emphasize/re-word existing bullets to lead with what's most relevant for THIS role. Do NOT invent claims.
5. A KEYWORD DIFF — the recruiter-Boolean-search check. Extract the hard-skill / proper-noun / framework / regulation keywords a recruiter would Boolean-search for from this job description. For each, decide whether the candidate's resume already contains it as an EXACT phrase (matched) or only via a paraphrase / not at all (missing). For each missing keyword, suggest the closest paraphrase the candidate already uses (so they can swap or augment) plus a one-line replacement hint.
6. A SIX-SECOND SCAN — the human-reviewer-skimming-200-resumes check. A recruiter or HM spends literally six seconds on the first pass; their eye goes to the title line under the candidate's name and the first 3 bullets of their most recent role. Report:
   - titleObserved: the title currently on line 1 (or top of resume)
   - titleAlignment: 'aligned' | 'one level off' | 'two+ levels off' vs. the job title
   - titleSuggestion: a one-line subtitle the candidate could add ('Targeting: <job title here>') — leave empty string if titleAlignment is 'aligned'
   - topBulletsCritique: 1-2 sentences on whether the first 3 bullets of the most recent role hit this job's themes or read as generic
   - rewrites: array of {original, suggested, why} — propose rewrites for up to 3 weak/generic top bullets. 'original' must be the EXACT text from the resume. 'suggested' must use only true facts from the resume but emphasize JD-relevant verbs/numbers. 'why' is one sentence.
7. A COVER PARAGRAPH — a 3-4 sentence editorial paragraph the candidate could paste at the very top of their resume for THIS application only. Lead with years + domain. Cite one or two specific accomplishments (verbatim from the resume). End with a single sentence naming the company + role and what specifically they want to bring. NO marketing fluff.

Return your response as a JSON object with EXACTLY these keys and nothing else:
- "summary" (string)
- "coverLetter" (string)
- "linkedin" (string)
- "tailoredResume" (object with keys: personal, summary, skills, experience, education, certifications — same shape as the input resume)
- "keywordDiff" (object with keys: matched, missing — diff between ORIGINAL resume and the JD)
- "keywordCoverageAfterTailor" (object with keys: matched, missing, closedByTailoring — diff between the TAILORED resume above and the JD, plus the count of missing-keywords the tailoring closed)
- "sixSecondScan" (object with keys: titleObserved, titleAlignment, titleSuggestion, topBulletsCritique, rewrites)
- "coverParagraph" (string)

For keywordCoverageAfterTailor:
{
  "matched": [ { "term": "Vendor Risk Management", "occurrences": 3 } ],  // now present in the tailored resume
  "missing": [ { "required": "FFIEC IT Examination", "reason": "no credible basis in candidate's experience" } ],  // still gone after tailoring (with reason)
  "closedByTailoring": 4   // how many of keywordDiff.missing the tailored resume now hits
}

For tailoredResume:
- personal: copy from input as-is
- summary: rewrite for THIS job, 3-4 sentences. MUST naturally include 2-4 of the keywordDiff.missing terms IF the candidate's actual background credibly supports them.
- skills: re-order so most relevant 8-12 come first; drop the least relevant. ADD any missing JD keywords from keywordDiff.missing that the candidate has credible exposure to (e.g. if missing.required is "Vendor Risk Management" and the candidate's bullets describe vendor onboarding/oversight, add VRM to skills using that exact phrase).
- experience: keep same companies/titles/dates; re-order/rewrite bullets to emphasize relevance. 3-5 strongest bullets per role for THIS job.
  CRITICAL: rewrite bullets to surface the JD's exact phrasing where the underlying work matches. If the JD says "Vendor Risk Management" and a bullet says "managed third-party reviews", change it to "managed vendor risk reviews" — same fact, JD-matching phrasing. If the candidate has NO credible basis for a missing keyword, leave it out. NEVER fabricate.
- education / certifications: copy as-is

The point: a recruiter Boolean-searching for the JD's exact terms should now hit the tailored resume. The keywordDiff (computed against the ORIGINAL resume) tells you which gaps exist; close the credible ones in tailoredResume.

After producing tailoredResume, COMPUTE keywordCoverageAfterTailor by re-checking the tailored resume's text against the same JD keywords. Report how many you closed.

For keywordDiff:
{
  "matched": [
    { "term": "COSO", "occurrences": 3 },
    { "term": "NIST 800-53", "occurrences": 1 }
  ],
  "missing": [
    {
      "required": "Vendor Risk Management",
      "alternative": "Third-Party Risk",
      "alternativeOccurrences": 2,
      "fix": "Swap 2 mentions of 'Third-Party Risk' for 'Vendor Risk Management', or add VRM to your Skills block."
    },
    {
      "required": "FFIEC IT Examination",
      "alternative": null,
      "alternativeOccurrences": 0,
      "fix": "Add 'FFIEC IT Examination' to your Frameworks/Skills block if you have any FFIEC exposure; otherwise leave out."
    }
  ]
}

Pull 5-12 keywords (mix of must-have skills, frameworks, regulations, methodologies, named tools). Skip generic terms ('leadership', 'team player'). If a keyword has a clear synonym in the resume, surface it in 'alternative' so the user knows there's already a paraphrase they can swap. If the candidate genuinely doesn't have that keyword anywhere, set alternative=null.

Only re-emphasize what's already in the resume. Never fabricate. The keywordDiff is a TRUE diff against the actual resume text — don't list a keyword as matched if it isn't literally present.

JOB:
Title: ${jobTitle}
Company: ${company}
${jobUrl ? `URL: ${jobUrl}\n` : ''}${jobDescription ? `Description: ${jobDescription.slice(0, 3000)}\n` : ''}
RESUME (JSON):
${resumeJson}`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 9500, messages: [{ role: 'user', content: prompt }] }),
    });
    if (!r.ok) { const err = await r.text(); return Response.json({ error: 'Anthropic API error', details: err }, { status: 502, headers: cors }); }
    const data = await r.json();
    const text = data.content?.[0]?.text || '';
    const cleaned = text.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/\s*```$/, '').trim();
    let parsed;
    try { parsed = JSON.parse(cleaned); }
    catch (e) { return Response.json({ summary: text, coverLetter: '', linkedin: '', tailoredResume: null, keywordDiff: null, keywordCoverageAfterTailor: null, sixSecondScan: null, coverParagraph: '', warning: 'AI did not return valid JSON' }, { headers: cors }); }
    return Response.json(parsed, { headers: cors });
  } catch (e) { return Response.json({ error: 'Worker error', message: String(e) }, { status: 500, headers: cors }); }
}


// --- /resume-health (Week 3) ------------------------------------------
// Deterministic resume health checks (no LLM). Returns a score 0-100 plus
// a breakdown across parseability, keyword density vs. user's targets,
// quantified-bullet ratio, title alignment, recency clarity. Persists
// to skills_profile.resumeHealth so the dashboard can render history.
async function handleResumeHealth(request, env, cors, slug) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  const resumeJson = await getActiveResume(env, slug);
  if (!resumeJson) return Response.json({ error: 'No active resume saved.' }, { status: 404, headers: cors });
  let resume;
  try { resume = JSON.parse(resumeJson); }
  catch (e) { return Response.json({ error: 'Resume not valid JSON' }, { status: 400, headers: cors }); }

  const profRaw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  const profile = profRaw ? JSON.parse(profRaw) : {};

  // ---- helpers ----
  function _flattenResumeText(r) {
    const parts = [];
    if (r.summary) parts.push(String(r.summary));
    if (Array.isArray(r.skills)) parts.push(r.skills.join(' '));
    if (Array.isArray(r.experience)) {
      r.experience.forEach(e => {
        if (e.title) parts.push(String(e.title));
        if (e.company) parts.push(String(e.company));
        if (Array.isArray(e.bullets)) parts.push(e.bullets.join(' '));
        if (Array.isArray(e.achievements)) parts.push(e.achievements.join(' '));
      });
    }
    if (Array.isArray(r.education)) r.education.forEach(e => { if (e.school) parts.push(String(e.school)); if (e.degree) parts.push(String(e.degree)); });
    if (Array.isArray(r.certifications)) parts.push(r.certifications.join(' '));
    return parts.join(' ').toLowerCase();
  }
  function _allBullets(r) {
    const out = [];
    if (Array.isArray(r.experience)) {
      r.experience.forEach(e => {
        if (Array.isArray(e.bullets)) e.bullets.forEach(b => out.push(String(b)));
        if (Array.isArray(e.achievements)) e.achievements.forEach(b => out.push(String(b)));
      });
    }
    return out;
  }

  const flat = _flattenResumeText(resume);
  const allBullets = _allBullets(resume);

  // ---- 1. Parseability — JSON resume is already clean text, so default 95.
  // We can't inspect PDF/DOCX from here (the JSON has been parsed already).
  // Surface that limitation in the breakdown instead of pretending.
  const parseability = {
    score: 95,
    issues: [],
    notes: 'Resume is stored as structured JSON, so ATS extraction is reliable. To check the original PDF\'s parseability, re-upload it as PDF rather than pasting.'
  };

  // ---- 2. Keyword density vs. user's targetTitles + industries + keywords
  const targetTerms = [].concat(profile.targetTitles || [], profile.industries || [], profile.keywords || [])
    .map(t => String(t || '').toLowerCase().trim()).filter(Boolean);
  const uniqTerms = Array.from(new Set(targetTerms));
  const hit = uniqTerms.filter(t => flat.includes(t));
  const missing = uniqTerms.filter(t => !flat.includes(t));
  const keywordScore = uniqTerms.length === 0 ? 0 : Math.round(100 * hit.length / uniqTerms.length);
  const keyword = { score: keywordScore, hit, missing, targetTermCount: uniqTerms.length };

  // ---- 3. Quantified-bullet ratio — bullets with a number
  const numberRx = /\b\$?[0-9][0-9,.]*[kKmMbB%]?\b/;
  const quantified = allBullets.filter(b => numberRx.test(b));
  const ratio = allBullets.length === 0 ? 0 : quantified.length / allBullets.length;
  const quantScore = Math.round(100 * Math.min(1, ratio / 0.6)); // 60% = full score
  const weakBullets = allBullets
    .filter(b => !numberRx.test(b))
    .filter(b => b.length > 20)
    .slice(0, 5);
  const quantBreakdown = { score: quantScore, total: allBullets.length, quantified: quantified.length, ratio: Math.round(ratio * 100) / 100, weakBullets };

  // ---- 4. Title alignment — top experience entry's title vs. user's targetTitles
  let titleObserved = '';
  if (Array.isArray(resume.experience) && resume.experience.length) {
    titleObserved = (resume.experience[0].title || '').trim();
  }
  const targetTitles = (profile.targetTitles || []).map(t => String(t || '').toLowerCase());
  const obsLow = titleObserved.toLowerCase();
  let titleScore = 50;
  let titleStatus = 'unknown';
  if (titleObserved && targetTitles.length) {
    const exact = targetTitles.some(t => obsLow === t);
    const contains = targetTitles.some(t => obsLow.includes(t.split(/\s+/).pop() || ''));
    if (exact) { titleScore = 100; titleStatus = 'aligned'; }
    else if (contains) { titleScore = 70; titleStatus = 'level-adjacent'; }
    else { titleScore = 40; titleStatus = 'misaligned'; }
  }
  const titleAlignment = { score: titleScore, observed: titleObserved, targeted: profile.targetTitles || [], status: titleStatus };

  // ---- 5. Recency + clarity — most-recent role present, dates clear
  let recencyScore = 100;
  const recencyIssues = [];
  if (!Array.isArray(resume.experience) || resume.experience.length === 0) {
    recencyScore = 0; recencyIssues.push('No experience entries found.');
  } else {
    const first = resume.experience[0];
    if (!first.endDate && !first.end && !first.current) recencyIssues.push('Most recent role has no end date or "Present" marker.');
    resume.experience.slice(0, 3).forEach((e, i) => {
      const start = e.startDate || e.start || '';
      const end = e.endDate || e.end || (e.current ? 'Present' : '');
      if (!start) { recencyScore -= 15; recencyIssues.push('Role #' + (i+1) + ' has no start date.'); }
      if (!end)   { recencyScore -= 10; recencyIssues.push('Role #' + (i+1) + ' has no end date.'); }
    });
    recencyScore = Math.max(0, recencyScore);
  }
  const recency = { score: recencyScore, issues: recencyIssues };

  // ---- Aggregate (weighted average) ----
  // Weights: keywords 30, quantified 25, title 20, recency 15, parseability 10
  const weights = { keyword: 0.30, quantified: 0.25, titleAlignment: 0.20, recency: 0.15, parseability: 0.10 };
  const total =
    keyword.score        * weights.keyword +
    quantBreakdown.score * weights.quantified +
    titleAlignment.score * weights.titleAlignment +
    recency.score        * weights.recency +
    parseability.score   * weights.parseability;
  const score = Math.round(total);

  // Active resume id (so we can detect "stale health for this version")
  const resumeId = await env.RESUMES.get(uk(slug, 'resume:active')) || null;

  const health = {
    computedAt: new Date().toISOString(),
    resumeId,
    score,
    weights,
    breakdown: {
      parseability,
      keyword,
      quantified: quantBreakdown,
      titleAlignment,
      recency
    }
  };

  // Persist on profile (best-effort — auth-gated separately via patch path,
  // but reads are public anyway so we don't require auth to compute).
  try {
    profile.resumeHealth = health;
    profile.user = slug;
    if (!Array.isArray(profile.resumeHealthHistory)) profile.resumeHealthHistory = [];
    profile.resumeHealthHistory.push({ at: health.computedAt, score, resumeId });
    if (profile.resumeHealthHistory.length > 12) profile.resumeHealthHistory = profile.resumeHealthHistory.slice(-12);
    await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(profile));
  } catch (e) { /* tolerate */ }

  return Response.json(health, { headers: cors });
}

// --- /resume-health-suggest (Week 4 — LLM rewrites) -------------------
// Takes the active resume + user profile + (optionally) a precomputed
// health breakdown, and asks Claude to produce concrete fix actions:
//   - bullet rewrites (BEFORE/AFTER/why) for the weakest bullets
//   - a one-line subtitle suggestion when title is misaligned
//   - keyword-injection suggestions: where in the resume to add
//     missing target terms
async function handleResumeHealthSuggest(request, env, cors, slug) {
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY secret' }, { status: 500, headers: cors });
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  const resumeJson = await getActiveResume(env, slug);
  if (!resumeJson) return Response.json({ error: 'No active resume saved.' }, { status: 404, headers: cors });
  const profRaw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  const profile = profRaw ? JSON.parse(profRaw) : {};
  const health = profile.resumeHealth || null;

  const prompt = `You are a resume coach. Based on the resume + the user's profile + the precomputed health breakdown, produce concrete, copy-paste fix actions. Stay within the bounds of what the resume already says — emphasize, reword, add subtitles. NEVER fabricate.

Return ONLY a JSON object with this shape:

{
  "bulletRewrites": [
    { "original": "<exact text from resume>", "suggested": "<rewrite that emphasizes JD-relevant verbs + adds a credible quantification when one is implied by the original>", "why": "<one sentence>" }
  ],
  "titleSubtitle": "<one-line subtitle the user could add directly under their name to signal targeting, or empty string if the title is already aligned>",
  "keywordInjections": [
    { "term": "<missing target term>", "wherePlace": "Skills | Summary | Experience > <company>", "verbatim": "<short phrase to drop in>" }
  ]
}

Constraints:
- bulletRewrites: 3-5 items. 'original' MUST match a bullet from the resume's experience entries EXACTLY (no paraphrasing). Pick the bullets that are most generic OR longest without a number.
- titleSubtitle: only if profile.targetTitles[0] differs meaningfully from the top resume title. Use the user's actual targetTitles. Empty string is valid.
- keywordInjections: only for terms in profile.targetTitles/industries/keywords that don't appear anywhere in the resume body. Suggest the most credible placement; verbatim should be 3-8 words.

PROFILE:
${JSON.stringify({ targetTitles: profile.targetTitles, industries: profile.industries, keywords: profile.keywords }).slice(0, 2000)}

HEALTH BREAKDOWN:
${JSON.stringify(health).slice(0, 4000)}

RESUME (JSON):
${resumeJson.slice(0, 12000)}`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 3500, messages: [{ role: 'user', content: prompt }] }),
    });
    if (!r.ok) { const err = await r.text(); return Response.json({ error: 'Anthropic API error', details: err }, { status: 502, headers: cors }); }
    const data = await r.json();
    const text = data.content?.[0]?.text || '';
    const cleaned = text.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/\s*```$/, '').trim();
    let parsed;
    try { parsed = JSON.parse(cleaned); }
    catch (e) { return Response.json({ error: 'AI did not return valid JSON', raw: text }, { status: 502, headers: cors }); }
    return Response.json(parsed, { headers: cors });
  } catch (e) { return Response.json({ error: 'Worker error', message: String(e) }, { status: 500, headers: cors }); }
}

// --- /api/tuning (Week 5 — store + score per-job customizations) ------
// save:    POST { fp, jobMeta:{title,company}, keywordDiff, sixSecondScan, coverParagraph }
// outcome: POST { fp, status:'applied'|'phonescreen'|'rejected'|'onsite'|'offer' }
// list:    GET  → { tunings: [...] }
async function _readTunings(env, slug) {
  try {
    const raw = await env.RESUMES.get(uk(slug, 'tunings'));
    return raw ? JSON.parse(raw) : [];
  } catch (e) { return []; }
}
async function _writeTunings(env, slug, arr) {
  await env.RESUMES.put(uk(slug, 'tunings'), JSON.stringify(arr.slice(-50)));
}
async function _tuningAuth(request, env, slug) {
  if (await checkEditKey(request, env, slug)) return true;
  try { const s = await sessionFromRequest(request, env); if (s && s.slug === slug) return true; } catch(e) {}
  const ak = request.headers.get('X-Admin-Key');
  if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) return true;
  return false;
}
async function handleTuningSave(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!await _tuningAuth(request, env, slug)) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
  const body = await request.json().catch(() => ({}));
  if (!body.fp || typeof body.fp !== 'string') return Response.json({ error: 'Missing fp' }, { status: 400, headers: cors });
  const list = await _readTunings(env, slug);
  // Dedupe — replace any prior tuning for the same fp
  const filtered = list.filter(t => t.fp !== body.fp);
  filtered.push({
    fp: body.fp,
    jobMeta: body.jobMeta || {},
    createdAt: new Date().toISOString(),
    keywordChanges: ((body.keywordDiff || {}).missing || []).map(m => ({ required: m.required, alternative: m.alternative || null })),
    titleSuggested: (body.sixSecondScan || {}).titleSuggestion || '',
    bulletRewriteCount: Array.isArray((body.sixSecondScan || {}).rewrites) ? body.sixSecondScan.rewrites.length : 0,
    coverParagraphUsed: !!(body.coverParagraph && body.coverParagraph.trim()),
    outcome: null,
    outcomeAt: null
  });
  await _writeTunings(env, slug, filtered);
  return Response.json({ status: 'saved', count: filtered.length }, { headers: cors });
}
async function handleTuningOutcome(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!await _tuningAuth(request, env, slug)) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
  const body = await request.json().catch(() => ({}));
  if (!body.fp || !body.status) return Response.json({ error: 'Missing fp or status' }, { status: 400, headers: cors });
  const list = await _readTunings(env, slug);
  const t = list.find(x => x.fp === body.fp);
  if (!t) return Response.json({ status: 'no-tuning-for-fp' }, { headers: cors });
  t.outcome = String(body.status).toLowerCase();
  t.outcomeAt = new Date().toISOString();
  await _writeTunings(env, slug, list);
  return Response.json({ status: 'updated', outcome: t.outcome }, { headers: cors });
}
async function handleTuningList(request, env, cors, slug) {
  if (request.method !== 'GET') return new Response('GET only', { status: 405, headers: cors });
  const list = await _readTunings(env, slug);
  // Lightweight win-rate rollup
  const summary = { total: list.length, applied: 0, advanced: 0, rejected: 0 };
  list.forEach(t => {
    const o = (t.outcome || '').toLowerCase();
    if (['applied','phonescreen','onsite','offer','rejected'].includes(o)) summary.applied++;
    if (['phonescreen','onsite','offer'].includes(o)) summary.advanced++;
    if (o === 'rejected') summary.rejected++;
  });
  return Response.json({ tunings: list, summary }, { headers: cors });
}

// --- /api/dismiss (Week 2 — structured per-reason dismissal) ----------
// POST { fp, company, title, reason } where reason in:
//   'too-junior' | 'wrong-industry' | 'bad-company' | 'wrong-location' | 'other'
// Appends to profile.dismissalPatterns (capped 100). Also flips the
// tracker entry to 'dismissed' so the regular tracker pipeline still
// filters this job out of future picks.
async function handleDismiss(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  let authed = await checkEditKey(request, env, slug);
  if (!authed) {
    const sess = await sessionFromRequest(request, env);
    if (sess && sess.slug === slug) authed = true;
  }
  if (!authed) {
    const ak = request.headers.get('X-Admin-Key');
    if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) authed = true;
  }
  if (!authed) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
  const body = await request.json().catch(() => ({}));
  if (!body.fp) return Response.json({ error: 'Missing fp' }, { status: 400, headers: cors });
  const allowedReasons = ['too-junior','wrong-industry','bad-company','wrong-location','other'];
  const reason = allowedReasons.includes(body.reason) ? body.reason : 'other';

  const profRaw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  const profile = profRaw ? JSON.parse(profRaw) : {};
  if (!Array.isArray(profile.dismissalPatterns)) profile.dismissalPatterns = [];
  profile.dismissalPatterns.push({
    fp: body.fp,
    company: (body.company || '').slice(0, 80),
    title: (body.title || '').slice(0, 120),
    reason,
    note: (body.note || '').slice(0, 300),
    ts: new Date().toISOString()
  });
  if (profile.dismissalPatterns.length > 100) profile.dismissalPatterns = profile.dismissalPatterns.slice(-100);
  profile.editedAt = new Date().toISOString();
  await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(profile));

  // Also mark in tracker so the focus panel filters this fp on next render
  try {
    const trackerRaw = await env.RESUMES.get(uk(slug, 'tracker'));
    const tracker = trackerRaw ? JSON.parse(trackerRaw) : {};
    tracker[body.fp] = Object.assign(tracker[body.fp] || {}, {
      status: 'dismissed',
      statusChangedAt: new Date().toISOString(),
      jobMeta: { title: body.title || '', company: body.company || '' },
      dismissReason: reason
    });
    await env.RESUMES.put(uk(slug, 'tracker'), JSON.stringify(tracker));
  } catch (e) { /* tolerate */ }

  return Response.json({ status: 'recorded', reason, totalDismissals: profile.dismissalPatterns.length }, { headers: cors });
}

// --- /api/rerank (Week 3 — LLM re-rank against JD body) ---------------
// Two methods:
//   GET  → returns today's stamped re-rank (or {} if none)
//   POST { jobs: [{fp,title,company,description}] } → re-runs Claude
//        against the top-15 candidates the client provides + the user's
//        profile + last 14 days of dismissalPatterns. Stamps result.
//   DELETE → clears today's stamp (used by user-triggered refresh)
async function handleRerank(request, env, cors, slug) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  const today = new Date().toISOString().slice(0, 10);
  const key = uk(slug, 'rerank:today');

  if (request.method === 'GET') {
    const raw = await env.RESUMES.get(key);
    if (!raw) return Response.json({}, { headers: cors });
    let p; try { p = JSON.parse(raw); } catch (e) { return Response.json({}, { headers: cors }); }
    if (!p || p.date !== today) return Response.json({}, { headers: cors });
    return Response.json(p, { headers: cors });
  }
  if (request.method === 'DELETE') {
    await env.RESUMES.delete(key);
    return Response.json({ status: 'cleared' }, { headers: cors });
  }
  if (request.method !== 'POST') return new Response('GET / POST / DELETE only', { status: 405, headers: cors });

  // Auth — re-rank costs Claude tokens, gate by edit key or session.
  let authed = await checkEditKey(request, env, slug);
  if (!authed) {
    const sess = await sessionFromRequest(request, env);
    if (sess && sess.slug === slug) authed = true;
  }
  if (!authed) {
    const ak = request.headers.get('X-Admin-Key');
    if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) authed = true;
  }
  if (!authed) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY' }, { status: 500, headers: cors });

  const body = await request.json().catch(() => ({}));
  const jobs = Array.isArray(body.jobs) ? body.jobs.slice(0, 15) : [];
  if (jobs.length === 0) return Response.json({ error: 'No jobs to rerank' }, { status: 400, headers: cors });

  const profRaw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  const profile = profRaw ? JSON.parse(profRaw) : {};
  const profSlim = {
    targetTitles: profile.targetTitles || [],
    industries:   profile.industries   || [],
    keywords:     profile.keywords     || [],
    careerStage:  profile.careerStage  || '',
    primaryRole:  profile.primaryRole  || '',
    remotePreference: profile.remotePreference || 'any',
    salaryFloor:  profile.salaryFloor  || null
  };

  // Week 4: dismissal patterns become a strong signal. Pre-roll up by
  // reason + company so Claude doesn't have to re-derive the pattern
  // from raw rows. Cap at last 20 raw + the full rollup.
  const dismissalsRaw = (Array.isArray(profile.dismissalPatterns) ? profile.dismissalPatterns : [])
    .filter(d => {
      const ts = Date.parse(d.ts || '');
      return Number.isFinite(ts) && (Date.now() - ts) < 14 * 86400000;
    });
  const dismissals = dismissalsRaw.slice(-20);
  // Rollup: count dismissals by reason, by company, and by (reason+company)
  const byReason = {};
  const byCompany = {};
  const byReasonCompany = {};
  dismissalsRaw.forEach(d => {
    const r = d.reason || 'other';
    const c = (d.company || '').toLowerCase();
    byReason[r] = (byReason[r] || 0) + 1;
    if (c) byCompany[c] = (byCompany[c] || 0) + 1;
    if (c) {
      const k = r + '::' + c;
      byReasonCompany[k] = (byReasonCompany[k] || 0) + 1;
    }
  });
  // Identify "strong patterns" — same reason for 3+ jobs from same company
  // OR same reason for 5+ jobs anywhere.
  const strongPatterns = [];
  Object.entries(byReasonCompany).forEach(([k, n]) => {
    if (n >= 3) {
      const [reason, company] = k.split('::');
      strongPatterns.push({ pattern: reason + ' at ' + company, count: n });
    }
  });
  Object.entries(byReason).forEach(([reason, n]) => {
    if (n >= 5) strongPatterns.push({ pattern: 'broad ' + reason + ' (any company)', count: n });
  });

  const jobsForPrompt = jobs.map(j => ({
    fp: j.fp,
    title: (j.title || '').slice(0, 120),
    company: (j.company || '').slice(0, 80),
    description: (j.description || '').slice(0, 1200)  // bound per-job to keep prompt small
  }));

  const prompt = `You are re-ranking job candidates for a specific user. You will receive: (1) a slim user profile, (2) a list of up to 15 candidate jobs already pre-filtered by per-dimension gates, (3) a short history of the user's recent dismissals + their stated reasons.

Your job: for EACH candidate, output a confidence score 0-100 (how likely the user should apply), a one-sentence primary reason, and an explicit deal-breaker (string) if the job has any single fatal issue — null otherwise.

Confidence guide:
  90-100 — strong fit on title + industry + level; user has direct experience for the JD's must-haves
  70-89  — solid fit with 1 minor mismatch
  50-69  — partial fit, JD has some real misalignment
  <50    — should not be shown to user; explain why in dealBreaker

DISMISSAL PATTERNS — use these as A STRONG VETO SIGNAL, not advisory:
- Any job matching a 'strong pattern' below should get confidence <= 40 with a clear dealBreaker that names the pattern. Example: if 'too-junior at capco' appears in strongPatterns and a Capco Director role shows up in candidates, set dealBreaker = "matches your repeated 'too-junior at Capco' dismissal pattern".
- Treat lighter dismissals (1-2 occurrences) as soft downweight — drop confidence by ~10-15 if the candidate triggers the same reason.
- If a strong-pattern says 'wrong-industry at <company>', do NOT just suppress that company — also downweight other companies in the same sector.

Return ONLY a JSON object with this exact shape:

{
  "ranked": [
    { "fp": "...", "confidence": 92, "primaryReason": "VP banking tech with GRC + Basel III exposure — direct match to the JD's must-haves and your last role at Mercury", "dealBreaker": null }
  ]
}

PROFILE:
${JSON.stringify(profSlim).slice(0, 1500)}

RECENT DISMISSALS (last 14d, oldest first):
${JSON.stringify(dismissals).slice(0, 2500)}

STRONG PATTERNS (computed from raw dismissals — VETO signal):
${JSON.stringify(strongPatterns).slice(0, 1000)}

DISMISSAL COUNTS BY REASON (last 14d):
${JSON.stringify(byReason).slice(0, 500)}

DISMISSAL COUNTS BY COMPANY (last 14d):
${JSON.stringify(byCompany).slice(0, 800)}

CANDIDATES (${jobsForPrompt.length}):
${JSON.stringify(jobsForPrompt).slice(0, 14000)}`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 3500, messages: [{ role: 'user', content: prompt }] }),
    });
    if (!r.ok) { const err = await r.text(); return Response.json({ error: 'Anthropic API error', details: err.slice(0, 500) }, { status: 502, headers: cors }); }
    const data = await r.json();
    const text = data.content?.[0]?.text || '';
    const cleaned = text.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/\s*```$/, '').trim();
    let parsed;
    try { parsed = JSON.parse(cleaned); }
    catch (e) { return Response.json({ error: 'AI did not return valid JSON', raw: text.slice(0, 500) }, { status: 502, headers: cors }); }
    const record = {
      date: today,
      stampedAt: new Date().toISOString(),
      jobCount: jobs.length,
      dismissalCount: dismissalsRaw.length,
      strongPatternCount: strongPatterns.length,
      ranked: Array.isArray(parsed.ranked) ? parsed.ranked.slice(0, 15) : []
    };
    await env.RESUMES.put(key, JSON.stringify(record));
    return Response.json(record, { headers: cors });
  } catch (e) { return Response.json({ error: 'Worker error', message: String(e) }, { status: 500, headers: cors }); }
}

// --- /regenerate-profile -----------------------------------------------
// Re-run regenerateSkillsProfile for an existing user without needing them
// to re-upload their resume. Accepts POST (with X-Edit-Key for self-service)
// or POST (with X-Admin-Key for cross-user regen by the platform admin).
async function handleRegenerateProfile(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY secret' }, { status: 500, headers: cors });
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  // Admin override OR per-user edit key
  const adminKey = request.headers.get('X-Admin-Key') || '';
  const isAdmin = env.ADMIN_KEY && adminKey === env.ADMIN_KEY;
  if (!isAdmin && !(await checkEditKey(request, env, slug))) {
    return Response.json({ error: 'Invalid X-Edit-Key (or use X-Admin-Key)' }, { status: 401, headers: cors });
  }
  const resumeJson = await getActiveResume(env, slug);
  if (!resumeJson) return Response.json({ error: 'No resume stored for ' + slug + ' — nothing to re-parse' }, { status: 404, headers: cors });
  const profile = await regenerateSkillsProfile(env, slug);
  if (!profile) return Response.json({ error: 'Regeneration failed (Anthropic API error or JSON parse failure)' }, { status: 502, headers: cors });
  return Response.json({ status: 'regenerated', profile }, { headers: cors });
}

// --- /regenerate-companies ---------------------------------------------
// Decoupled from the resume — uses ONLY the user's bullseye (5 titles /
// 5 industries / 25 skills / sizeMix) to suggest 20 companies. Pure
// instruction-based prompt, no hardcoded company lists.
//
// Modes:
//   POST  body {dry_run: true}  → returns {proposed, diff} but does NOT save
//   POST  body {dry_run: false} → saves to profile.targetCompanies and returns it
// Auth: admin key OR per-user edit key (same as /regenerate-profile).
async function handleRegenerateCompanies(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY secret' }, { status: 500, headers: cors });
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  const adminKey = request.headers.get('X-Admin-Key') || '';
  const isAdmin = env.ADMIN_KEY && adminKey === env.ADMIN_KEY;
  if (!isAdmin && !(await checkEditKey(request, env, slug))) {
    return Response.json({ error: 'Invalid X-Edit-Key (or use X-Admin-Key)' }, { status: 401, headers: cors });
  }

  let body = {};
  try { body = await request.json(); } catch (e) { body = {}; }
  const dryRun = body.dry_run !== false;  // default: dry-run

  const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  if (!raw) return Response.json({ error: 'No profile stored for ' + slug }, { status: 404, headers: cors });
  let profile;
  try { profile = JSON.parse(raw); } catch (e) { return Response.json({ error: 'Profile JSON invalid' }, { status: 500, headers: cors }); }

  const titles = profile.targetTitles || [];
  const industries = profile.industries || [];
  const keywords = profile.keywords || [];
  if (titles.length === 0 || industries.length === 0) {
    return Response.json({ error: 'Bullseye incomplete — need targetTitles and industries set first (run the wizard)' }, { status: 400, headers: cors });
  }

  const seniority = profile.seniorityLevel || 'senior';
  const careerStage = profile.careerStage || 'senior';
  const sizeMix = profile.companySizeMix || { startup: 33, midsize: 33, large: 34 };
  const negKw = profile.negativeKeywords || [];
  const summary = (profile.summary || '').slice(0, 400);

  const prompt = `You are recommending real, currently-hiring companies for a job-seeker. Use ONLY their bullseye below — do not draw on any other source. Return a JSON array of 20 companies.

CANDIDATE BULLSEYE:
- Target titles (max 5): ${JSON.stringify(titles)}
- Target industries (max 5): ${JSON.stringify(industries)}
- Skills/keywords: ${JSON.stringify(keywords.slice(0, 25))}
- Seniority level: ${seniority}
- Career stage: ${careerStage}
- Size mix preference: startup ${sizeMix.startup}% / midsize ${sizeMix.midsize}% / large ${sizeMix.large}%
- Negative keywords (avoid roles containing these as standalone words): ${JSON.stringify(negKw)}
- Background summary: ${summary}

SELECTION RULES:
1. Each company must currently hire for at least one of the candidate's target titles at the right seniority. If unsure, skip — quality over quantity.
2. Each company must be in or directly adjacent to one of the 5 industries.
3. Respect the size mix: across the 20 suggestions, roughly that proportion of startups (under 500 employees / Series A-D), midsize (500-10k employees / Series E+ or PE-backed), and large (10k+ employees / Fortune 500). If any size is 0%, exclude that bucket entirely.
4. Prefer companies known to use scrape-able ATSes: Greenhouse, Lever, Ashby, or Workday. Set atsHint accordingly.
5. For workday entries, include atsUrl as the full public Workday careers URL if you know it (e.g. https://moodys.wd5.myworkdayjobs.com/Careers). If unsure of the exact URL, set atsHint="unknown".
6. Mix it up: don't list 20 of the same archetype. For a banking-tech candidate, include super-regional banks AND fintech infrastructure AND GRC SaaS AND consulting firms — not 20 banks. For a healthtech candidate, include EHR vendors AND payer tech AND DTC health AND clinical platforms.
7. AVOID giant Fortune 100 firms for senior+ candidates unless their niche genuinely demands them. Prefer mid-market and scale-up firms where the candidate would have outsized impact.
8. AVOID companies that have been acquired into bigger entities, are in known hiring freezes, or have well-publicized layoff cycles in the last 12 months.
9. Each suggestion must be a real, current company name (not a generic "any consulting firm" placeholder).

Return shape (no prose, no markdown, just the JSON array):
[{"name":"string","atsHint":"greenhouse|lever|ashby|workday|unknown","atsUrl":"optional full url","why":"one-sentence reason this fits the bullseye"}, ...]`;

  let claudeResp;
  try {
    claudeResp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({
        model: 'claude-sonnet-4-5-20250929',
        max_tokens: 4096,
        messages: [{ role: 'user', content: prompt }]
      })
    });
  } catch (e) {
    return Response.json({ error: 'Anthropic call failed: ' + String(e) }, { status: 502, headers: cors });
  }
  if (!claudeResp.ok) {
    const errText = await claudeResp.text().catch(()=> '');
    return Response.json({ error: 'Anthropic returned ' + claudeResp.status, detail: errText.slice(0, 300) }, { status: 502, headers: cors });
  }
  const claudeData = await claudeResp.json();
  const text = ((claudeData.content && claudeData.content[0] && claudeData.content[0].text) || '').trim();
  let proposed;
  try {
    proposed = JSON.parse(text);
  } catch (e) {
    const m = text.match(/\[[\s\S]*\]/);
    if (m) { try { proposed = JSON.parse(m[0]); } catch (ee) { proposed = null; } }
  }
  if (!Array.isArray(proposed)) {
    return Response.json({ error: 'Claude returned non-array', raw: text.slice(0, 400) }, { status: 502, headers: cors });
  }
  // Normalize each entry
  proposed = proposed.filter(x => x && x.name).map(x => ({
    name: String(x.name).trim(),
    atsHint: (String(x.atsHint || 'unknown').toLowerCase()),
    atsUrl: x.atsUrl ? String(x.atsUrl) : undefined,
    why: x.why ? String(x.why) : '',
  }));

  // Build diff vs existing
  const existing = Array.isArray(profile.targetCompanies) ? profile.targetCompanies : [];
  const existingNames = new Set(existing.map(c => (c && c.name ? c.name : String(c)).toLowerCase().trim()));
  const proposedNames = new Set(proposed.map(c => c.name.toLowerCase().trim()));
  const removing = existing.filter(c => !proposedNames.has((c && c.name ? c.name : String(c)).toLowerCase().trim()));
  const adding = proposed.filter(c => !existingNames.has(c.name.toLowerCase().trim()));
  const keeping = proposed.filter(c => existingNames.has(c.name.toLowerCase().trim()));

  if (dryRun) {
    return Response.json({
      status: 'preview',
      dry_run: true,
      proposed,
      diff: { removing, adding, keeping, summary: `Will remove ${removing.length}, add ${adding.length}, keep ${keeping.length}` }
    }, { headers: cors });
  }

  // Commit: replace targetCompanies
  profile.targetCompanies = proposed;
  profile.editedAt = new Date().toISOString();
  await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(profile));
  return Response.json({
    status: 'saved',
    dry_run: false,
    profile,
    diff: { removing, adding, keeping, summary: `Removed ${removing.length}, added ${adding.length}, kept ${keeping.length}` }
  }, { headers: cors });
}

// --- /draft-warm-intro -------------------------------------------------
// Drafts a personalized LinkedIn DM + email asking a connection for a
// warm intro to a specific job. Body shape:
//   { fp, job: {title, company, url, desc}, connection: {first, last, position, company, url} }
async function handleDraftWarmIntro(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY' }, { status: 500, headers: cors });

  let body;
  try { body = await request.json(); } catch (e) { return Response.json({ error: 'Bad JSON' }, { status: 400, headers: cors }); }
  const job = body.job || {};
  const conn = body.connection || {};
  if (!job.title || !job.company || !conn.first) {
    return Response.json({ error: 'Body must include job{title,company} and connection{first}' }, { status: 400, headers: cors });
  }

  // Load user profile for personalization
  const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  const profile = raw ? (JSON.parse(raw) || {}) : {};
  const userFirstName = profile.firstName || (slug.split('-')[0] || 'me');
  const userName = (profile.firstName && profile.lastName) ? `${profile.firstName} ${profile.lastName}` : userFirstName;
  const userRole = profile.primaryRole || profile.currentTitle || 'a job seeker';
  const userSummary = (profile.summary || '').slice(0, 400);
  const userIndustries = (profile.industries || []).slice(0, 3).join(', ');

  const connName = `${conn.first} ${conn.last || ''}`.trim();
  const connPos = conn.position || '';
  const connCompany = conn.company || '';
  const jobDesc = (job.desc || '').slice(0, 600);

  const prompt = `You're drafting a warm-intro request on behalf of ${userName}. They want to apply for "${job.title}" at ${job.company} and have a LinkedIn connection at the company. Generate TWO short, professional messages: a LinkedIn DM (max 300 characters) and an email (subject + 4-6 sentence body).

USER (sender):
- Name: ${userName}
- Role: ${userRole}
- Industries: ${userIndustries}
- Background: ${userSummary}

CONNECTION (recipient):
- Name: ${connName}
- Position when last connected: ${connPos}${connCompany ? ' @ ' + connCompany : ''}

JOB:
- Title: ${job.title}
- Company: ${job.company}
- URL: ${job.url || '(not provided)'}
- JD snippet: ${jobDesc}

RULES:
- Be warm but not gushing. Acknowledge it's been a while (assume they may not remember).
- Be specific about the job and why it fits the sender.
- Ask explicitly if they'd be open to a brief intro/referral. Don't demand.
- LinkedIn DM: max 300 chars, conversational. Start "Hi ${conn.first},".
- Email subject: under 60 chars, action-oriented (e.g., "Quick referral ask: ${job.title} at ${job.company}").
- Email body: 4-6 sentences. Same warm tone. Mention the job by name + paste the URL near the end.
- Don't sign with full address blocks. Just first name.

Return ONLY a JSON object, no prose, no markdown:
{"linkedin_dm": "...", "email_subject": "...", "email_body": "..."}`;

  let resp;
  try {
    resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-haiku-4-5-20251001', max_tokens: 1024, messages: [{ role: 'user', content: prompt }] })
    });
  } catch (e) {
    return Response.json({ error: 'Anthropic call failed: ' + String(e) }, { status: 502, headers: cors });
  }
  if (!resp.ok) {
    return Response.json({ error: 'Anthropic ' + resp.status }, { status: 502, headers: cors });
  }
  const data = await resp.json();
  const text = ((data.content && data.content[0] && data.content[0].text) || '').trim();
  let parsed;
  try { parsed = JSON.parse(text); }
  catch (e) {
    const m = text.match(/\{[\s\S]*\}/);
    if (m) { try { parsed = JSON.parse(m[0]); } catch (ee) {} }
  }
  if (!parsed || !parsed.linkedin_dm) {
    return Response.json({ error: 'AI returned malformed', raw: text.slice(0, 300) }, { status: 502, headers: cors });
  }
  return Response.json({
    linkedin_dm: parsed.linkedin_dm,
    email_subject: parsed.email_subject || ('Referral request: ' + job.title + ' at ' + job.company),
    email_body: parsed.email_body || ''
  }, { headers: cors });
}

// --- /suggest-refinements ---------------------------------------------
// Engagement-driven intelligence: reads the user's tracker (apply/save/
// dismiss patterns) and asks Claude for 1-3 specific bullseye refinements.
// e.g. "12 of your 15 applies have 'GRC' in the title — add it to keywords?"
// Returns structured suggestions the client can 1-click apply.
async function handleSuggestRefinements(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY' }, { status: 500, headers: cors });
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });

  // Load profile + tracker
  const rawP = await env.RESUMES.get(uk(slug, 'skills_profile'));
  if (!rawP) return Response.json({ error: 'No profile' }, { status: 404, headers: cors });
  const profile = JSON.parse(rawP);
  const tracker = await getTracker(env, slug);

  // Filter to engaged jobs: applied / phonescreen / onsite / offer
  const ENGAGED = new Set(['applied', 'phonescreen', 'onsite', 'offer', 'saved-today']);
  const engaged = Object.values(tracker || {}).filter(t => t && ENGAGED.has(t.status));
  const dismissed = Object.values(tracker || {}).filter(t => t && t.status === 'dismissed');

  if (engaged.length < 5) {
    return Response.json({
      status: 'insufficient_data',
      suggestions: [],
      meta: { engaged_count: engaged.length, threshold: 5, message: 'Need at least 5 engaged jobs (applied/phonescreen/onsite/offer) to suggest refinements.' }
    }, { headers: cors });
  }

  const engagedSummary = engaged.slice(0, 40).map(t => `${t.title || ''} @ ${t.company || ''}`).join('\n');
  const dismissedSummary = dismissed.slice(0, 20).map(t => `${t.title || ''} @ ${t.company || ''}`).join('\n');

  const prompt = `You're refining a job-seeker's matching configuration based on their actual engagement patterns. Compare what they're ENGAGING WITH vs. what their bullseye says, then suggest 1-3 specific refinements.

CURRENT BULLSEYE:
- targetTitles: ${JSON.stringify(profile.targetTitles || [])}
- industries: ${JSON.stringify(profile.industries || [])}
- keywords: ${JSON.stringify(profile.keywords || [])}
- negativeKeywords: ${JSON.stringify(profile.negativeKeywords || [])}
- seniorityLevel: ${profile.seniorityLevel || 'unknown'}

JOBS THEY ENGAGED WITH (applied / interviewing / accepted): ${engaged.length} total. Sample:
${engagedSummary}

JOBS THEY DISMISSED: ${dismissed.length} total. Sample:
${dismissedSummary}

ANALYSIS RULES:
1. Look for patterns in engaged jobs that AREN'T reflected in the bullseye. e.g. if 12 of 15 applied jobs have "GRC" in title but "grc" isn't in their keywords, suggest adding it.
2. Look for bullseye entries that are NOT matching engaged jobs. e.g. if "fintech" is in industries but 0 engaged jobs are at fintech firms, suggest removing it.
3. Look for negativeKeywords blocking jobs the user is actually applying to. e.g. if they applied to a "Senior Analyst" role but "analyst" is in their negativeKeywords, flag it.
4. Be conservative: only suggest changes backed by ≥3 examples. Cite evidence specifically.
5. Each suggestion's confidence: "high" (≥70% pattern), "medium" (40-70%), "low" (<40% but interesting).

Return ONLY a JSON array (no prose, no markdown) of 1-3 suggestions in this shape:
[
  {
    "type": "add_keyword" | "remove_keyword" | "add_industry" | "remove_industry" | "add_title" | "remove_title" | "remove_negative_keyword" | "add_negative_keyword",
    "field": "keywords" | "industries" | "targetTitles" | "negativeKeywords",
    "value": "string",
    "evidence": "human-readable evidence (e.g. '12 of 15 applied jobs have GRC in title')",
    "confidence": "high" | "medium" | "low"
  }
]

If there are no clear patterns, return an empty array [].`;

  let resp;
  try {
    resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({
        model: 'claude-sonnet-4-5-20250929',
        max_tokens: 1500,
        messages: [{ role: 'user', content: prompt }]
      })
    });
  } catch (e) {
    return Response.json({ error: 'Anthropic call failed: ' + String(e) }, { status: 502, headers: cors });
  }
  if (!resp.ok) return Response.json({ error: 'Anthropic ' + resp.status }, { status: 502, headers: cors });
  const data = await resp.json();
  const text = ((data.content && data.content[0] && data.content[0].text) || '').trim();
  let parsed;
  try { parsed = JSON.parse(text); }
  catch (e) {
    const m = text.match(/\[[\s\S]*\]/);
    if (m) { try { parsed = JSON.parse(m[0]); } catch (ee) {} }
  }
  if (!Array.isArray(parsed)) parsed = [];

  return Response.json({
    status: parsed.length > 0 ? 'ok' : 'no_suggestions',
    suggestions: parsed,
    meta: { engaged_count: engaged.length, dismissed_count: dismissed.length }
  }, { headers: cors });
}

// --- users:list helpers -------------------------------------------------
async function readUsersList(env) {
  const raw = await env.RESUMES.get('users:list');
  if (!raw) return [];
  try { return JSON.parse(raw); } catch (e) { return []; }
}

async function writeUsersList(env, users) {
  await env.RESUMES.put('users:list', JSON.stringify(users));
}

async function bootstrapUsersListIfEmpty(env) {
  const existing = await readUsersList(env);
  if (existing.length > 0) return existing;
  // Scan KV for existing user:*:edit_key keys and build the registry
  const scan = await env.RESUMES.list({ prefix: 'user:' });
  const slugs = new Set();
  for (const k of scan.keys) {
    const m = k.name.match(/^user:([^:]+):edit_key$/);
    if (m) slugs.add(m[1]);
  }
  // Also include the default user if they have any data
  if (await env.RESUMES.get(uk(DEFAULT_USER, 'resume:active'))) slugs.add(DEFAULT_USER);
  if (await env.RESUMES.get(uk(DEFAULT_USER, 'resume:list'))) slugs.add(DEFAULT_USER);
  const users = [];
  for (const slug of slugs) {
    const name = (await env.RESUMES.get(uk(slug, 'name'))) || (slug === DEFAULT_USER ? 'Geetanjali Arora' : slug);
    users.push({ slug, name, email: '', createdAt: new Date().toISOString() });
  }
  await writeUsersList(env, users);
  return users;
}

async function migrateUserStatusIfNeeded(env) {
  // One-shot migration: any pre-2026-05-26 user without an explicit
  // status:'pending'|'approved'|'rejected' KV value is backfilled to
  // 'approved' (they were created before the approval gate existed).
  if (!env.RESUMES) return;
  const flag = await env.RESUMES.get('migration:user_status:v1');
  if (flag) return;
  const users = await readUsersList(env);
  for (const u of users) {
    if (!u || !u.slug) continue;
    const cur = await env.RESUMES.get(uk(u.slug, 'status'));
    if (!cur) {
      await env.RESUMES.put(uk(u.slug, 'status'), 'approved');
    }
  }
  await env.RESUMES.put('migration:user_status:v1', '1');
}

function generateSlug(name, existing) {
  const base = (name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 20);
  let slug = base || ('user' + Date.now().toString().slice(-6));
  const taken = new Set(existing.map(u => u.slug));
  if (!taken.has(slug)) return slug;
  // Append number to disambiguate
  for (let i = 2; i < 100; i++) {
    const candidate = slug + '-' + i;
    if (!taken.has(candidate)) return candidate;
  }
  return slug + '-' + Date.now().toString().slice(-4);
}

function generatePassword(len) {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789';
  let out = '';
  const arr = new Uint8Array(len || 16);
  crypto.getRandomValues(arr);
  for (let i = 0; i < (len || 16); i++) out += chars[arr[i] % chars.length];
  return out;
}

// --- /users (public, minimal read) --------------------------------------
async function handlePublicUsers(request, env, cors) {
  if (request.method !== 'GET') return new Response('GET only', { status: 405, headers: cors });
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  await migrateLegacyIfNeeded(env);
  const users = await bootstrapUsersListIfEmpty(env);
  // Strip emails — public endpoint
  return Response.json({ users: users.map(u => ({ slug: u.slug, name: u.name })) }, { headers: cors });
}

// --- /company-stage (public read) + /admin/enrich-companies (admin write) ---
// Cache shape: KV key 'company:stage:{name_lower}' -> JSON {
//   stage: 'seed' | 'series-a' | ... | 'public' | 'bootstrapped' | 'unknown',
//   lastFundedApproxYear: 2024,
//   isRecentlyFunded: boolean,   // last 12 months from analysis date
//   analyzedAt: ISO,
// }
// TTL: 90 days (re-classify periodically as funding rounds close).
async function handleCompanyStage(request, env, cors) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  const url = new URL(request.url);
  const company = String(url.searchParams.get('company') || '').trim().toLowerCase();
  if (!company) return Response.json({ error: 'Missing ?company=' }, { status: 400, headers: cors });
  const raw = await env.RESUMES.get('company:stage:' + company);
  if (!raw) return Response.json({ company, cached: false, stage: null }, { headers: cors });
  try { return Response.json({ company, cached: true, ...JSON.parse(raw) }, { headers: cors }); }
  catch (e) { return Response.json({ company, cached: false, stage: null }, { headers: cors }); }
}

async function handleDiscoverVcPortfolio(request, env, cors) {
  // POST { vcFirms?: [str], industries?: [str], targetTitles?: [str], excludeCompanies?: [str] }
  // → Asks Claude to enumerate startups/scaleups (Seed–Series C) funded by
  // those VCs in those industries that hire those titles. Cached 30 days
  // per (vc, industry) tuple. Returns a flat list of company names + atsHint.
  if (request.method !== 'POST') return Response.json({ error: 'POST only' }, { status: 405, headers: cors });
  if (!env.ADMIN_KEY) return Response.json({ error: 'Worker missing ADMIN_KEY secret' }, { status: 500, headers: cors });
  if (request.headers.get('X-Admin-Key') !== env.ADMIN_KEY) {
    return Response.json({ error: 'Invalid X-Admin-Key' }, { status: 401, headers: cors });
  }
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY' }, { status: 500, headers: cors });
  let body;
  try { body = await request.json(); } catch (e) { return Response.json({ error: 'Bad JSON' }, { status: 400, headers: cors }); }
  const vcFirms = Array.isArray(body.vcFirms) && body.vcFirms.length
    ? body.vcFirms.slice(0, 30)
    : ['Andreessen Horowitz (a16z)', 'Sequoia Capital', 'Founders Fund', 'Bessemer Venture Partners',
       'Lightspeed Venture Partners', 'Greylock Partners', 'Index Ventures', 'Union Square Ventures',
       'Accel', 'Kleiner Perkins', 'GV (Google Ventures)', 'General Catalyst'];
  const industries = Array.isArray(body.industries) ? body.industries.slice(0, 10) : ['fintech', 'banking', 'healthcare IT'];
  const titles = Array.isArray(body.targetTitles) ? body.targetTitles.slice(0, 10) : ['VP', 'Director', 'Head of'];
  const excludeNames = new Set((Array.isArray(body.excludeCompanies) ? body.excludeCompanies : []).map(x => String(x).toLowerCase()));
  const force = !!body.force;

  const cacheKey = 'vc:portfolio:' + (industries.join('|') + '|' + vcFirms.join('|')).slice(0, 250).toLowerCase().replace(/[^a-z0-9|]/g, '_');
  if (!force) {
    const cached = await env.RESUMES.get(cacheKey);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (parsed.companies && (Date.now() - (parsed.cachedAt || 0)) < 30 * 24 * 3600 * 1000) {
          return Response.json({ ...parsed, fromCache: true }, { headers: cors });
        }
      } catch (e) {}
    }
  }

  const prompt = `You are sourcing companies for a job-search product. Return a JSON array of currently-operating private companies (Seed through Series C, plus selected Series D startups) that meet ALL of these criteria:

1. Funded by one of these VCs: ${vcFirms.join(', ')}
2. Operate primarily in one of these industries: ${industries.join(', ')}
3. Plausibly hire roles like: ${titles.join(' / ')}
4. US-headquartered (preferred) or have major US presence
5. Currently active (not acquired/shut down per your knowledge)

For each, output: {"name": exact legal/common name, "industry": one from list above, "fundingStage": one of "seed"/"series-a"/"series-b"/"series-c"/"series-d", "atsHint": one of "greenhouse"/"lever"/"ashby"/"workday"/"workable"/"unknown" — pick the ATS slug they MOST LIKELY use based on company size and stage}

Aim for 30-60 companies, biased toward Series A-C (where senior hiring is most active). Do NOT include: ${[...excludeNames].slice(0, 20).join(', ') || '(none)'}.

Output ONLY a JSON object: {"companies": [...]}. No prose, no markdown.`;

  try {
    const aiResp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 6000, messages: [{ role: 'user', content: prompt }] }),
    });
    const aiJson = await aiResp.json();
    const text = ((aiJson.content || [])[0] || {}).text || '';
    const cleanText = text.replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/i, '').trim();
    let parsed;
    try { parsed = JSON.parse(cleanText); }
    catch (e) {
      return Response.json({ error: 'AI returned non-JSON', preview: cleanText.slice(0, 200) }, { status: 502, headers: cors });
    }
    const companies = Array.isArray(parsed.companies) ? parsed.companies : [];
    const record = {
      companies,
      vcFirms,
      industries,
      titles,
      cachedAt: Date.now(),
      analyzedAt: new Date().toISOString(),
    };
    await env.RESUMES.put(cacheKey, JSON.stringify(record), { expirationTtl: 30 * 24 * 3600 });
    return Response.json({ ...record, fromCache: false, count: companies.length }, { headers: cors });
  } catch (e) {
    return Response.json({ error: 'Discovery failed: ' + (e && e.message || String(e)) }, { status: 502, headers: cors });
  }
}


async function handleEnrichCompanies(request, env, cors) {
  if (request.method !== 'POST') return Response.json({ error: 'POST only' }, { status: 405, headers: cors });
  if (!env.ADMIN_KEY) return Response.json({ error: 'Worker missing ADMIN_KEY secret' }, { status: 500, headers: cors });
  if (request.headers.get('X-Admin-Key') !== env.ADMIN_KEY) {
    return Response.json({ error: 'Invalid X-Admin-Key' }, { status: 401, headers: cors });
  }
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY' }, { status: 500, headers: cors });
  let body;
  try { body = await request.json(); } catch (e) { return Response.json({ error: 'Bad JSON' }, { status: 400, headers: cors }); }
  const companies = Array.isArray(body.companies) ? body.companies.slice(0, 50) : [];
  const force = !!body.force;
  if (!companies.length) return Response.json({ error: 'Body must include {companies:[name,...]}' }, { status: 400, headers: cors });

  // Filter to ones not already cached (unless force=true)
  const toClassify = [];
  const fromCache = {};
  for (const raw of companies) {
    const name = String(raw || '').trim();
    if (!name) continue;
    const key = 'company:stage:' + name.toLowerCase();
    if (!force) {
      const exist = await env.RESUMES.get(key);
      if (exist) {
        try { fromCache[name] = JSON.parse(exist); continue; } catch (e) {}
      }
    }
    toClassify.push(name);
  }

  let newlyClassified = {};
  if (toClassify.length) {
    const prompt = `You are classifying companies by funding stage for a job-search product. Output ONLY valid JSON (no prose, no markdown).

For each company below, return:
{
  "stage": one of: "bootstrapped", "seed", "series-a", "series-b", "series-c", "series-d", "series-e-plus", "late-stage-private", "public", "acquired", "unknown",
  "lastFundedApproxYear": integer year of most recent funding round per your training data (or null if unknown / not applicable),
  "notes": one short string (under 100 chars) — e.g. "Stripe last raised \$6.5B Series I in 2023"
}

Companies to classify:
${toClassify.map((c, i) => `${i + 1}. ${c}`).join('\n')}

Return as: {"results": {"CompanyName": {...}, ...}}`;

    try {
      const aiResp = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
        body: JSON.stringify({ model: 'claude-haiku-4-5-20251001', max_tokens: 4000, messages: [{ role: 'user', content: prompt }] }),
      });
      const aiJson = await aiResp.json();
      const text = ((aiJson.content || [])[0] || {}).text || '';
      const cleanText = text.replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/i, '').trim();
      const parsed = JSON.parse(cleanText);
      const results = parsed.results || {};
      const nowIso = new Date().toISOString();
      const currentYear = new Date().getUTCFullYear();
      for (const [name, info] of Object.entries(results)) {
        const stage = String(info.stage || 'unknown').toLowerCase();
        const yr = (typeof info.lastFundedApproxYear === 'number') ? info.lastFundedApproxYear : null;
        const isRecentlyFunded = (yr !== null) && (currentYear - yr <= 1);
        const record = {
          stage,
          lastFundedApproxYear: yr,
          isRecentlyFunded,
          notes: String(info.notes || '').slice(0, 200),
          analyzedAt: nowIso,
        };
        await env.RESUMES.put('company:stage:' + name.toLowerCase(), JSON.stringify(record), { expirationTtl: 90 * 24 * 3600 });
        newlyClassified[name] = record;
      }
    } catch (e) {
      return Response.json({
        error: 'AI classification failed: ' + (e && e.message || String(e)),
        fromCache,
        toClassify,
      }, { status: 502, headers: cors });
    }
  }

  return Response.json({
    fromCache,
    newlyClassified,
    cachedCount: Object.keys(fromCache).length,
    newCount: Object.keys(newlyClassified).length,
  }, { headers: cors });
}


// --- /admin/users — full CRUD ------------------------------------------

// --- /contacts (per-user LinkedIn connections) -------------------------
async function handleContacts(request, env, cors, slug) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  if (request.method === 'GET') {
    // Auth: edit key, own session, or admin
    let authed = await checkEditKey(request, env, slug);
    if (!authed) {
      const sess = await sessionFromRequest(request, env);
      if (sess && sess.slug === slug) authed = true;
    }
    if (!authed) {
      const ak = request.headers.get('X-Admin-Key');
      if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) authed = true;
    }
    if (!authed) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
    const raw = await env.RESUMES.get(uk(slug, 'contacts'));
    const metaRaw = await env.RESUMES.get(uk(slug, 'contacts:meta'));
    return Response.json({
      contacts: raw ? JSON.parse(raw) : [],
      meta: metaRaw ? JSON.parse(metaRaw) : null,
    }, { headers: cors });
  }
  if (request.method === 'POST') {
    let authed = await checkEditKey(request, env, slug);
    if (!authed) {
      const sess = await sessionFromRequest(request, env);
      if (sess && sess.slug === slug) authed = true;
    }
    if (!authed) {
      const ak = request.headers.get('X-Admin-Key');
      if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) authed = true;
    }
    if (!authed) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
    const body = await request.json().catch(() => ({}));
    const contacts = Array.isArray(body && body.contacts) ? body.contacts : null;
    if (!contacts) return Response.json({ error: 'Body must be { contacts: [...] }' }, { status: 400, headers: cors });
    const meta = {
      count: contacts.length,
      uploadedAt: new Date().toISOString(),
      filename: (body.filename || 'Connections.csv'),
      source: (body.source || 'manual'),
    };
    await env.RESUMES.put(uk(slug, 'contacts'), JSON.stringify(contacts));
    await env.RESUMES.put(uk(slug, 'contacts:meta'), JSON.stringify(meta));
    return Response.json({ status: 'saved', meta }, { headers: cors });
  }
  return new Response('Use GET or POST', { status: 405, headers: cors });
}

// --- /admin/contacts (admin push for any user) -------------------------
async function handleAdminContacts(request, env, cors) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  const adminKey = request.headers.get('X-Admin-Key');
  if (!adminKey || adminKey !== env.ADMIN_KEY) return Response.json({ error: 'Invalid X-Admin-Key' }, { status: 401, headers: cors });
  const body = await request.json().catch(() => ({}));
  const slug = (body && body.slug || '').trim().toLowerCase();
  const contacts = Array.isArray(body && body.contacts) ? body.contacts : null;
  if (!slug || !contacts) return Response.json({ error: 'Body must be { slug, contacts: [...] }' }, { status: 400, headers: cors });
  const meta = {
    count: contacts.length,
    uploadedAt: new Date().toISOString(),
    filename: (body.filename || 'Connections.csv'),
    source: (body.source || 'admin'),
  };
  await env.RESUMES.put(uk(slug, 'contacts'), JSON.stringify(contacts));
  await env.RESUMES.put(uk(slug, 'contacts:meta'), JSON.stringify(meta));
  return Response.json({ status: 'saved', slug, meta }, { headers: cors });
}

// --- /api/sprint/start (user-controlled sprint start) ------------------
async function handleSprintStart(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  let authed = await checkEditKey(request, env, slug);
  if (!authed) {
    const sess = await sessionFromRequest(request, env);
    if (sess && sess.slug === slug) authed = true;
  }
  if (!authed) {
    const ak = request.headers.get('X-Admin-Key');
    if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) authed = true;
  }
  if (!authed) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
  const body = await request.json().catch(() => ({}));
  const sprintDays = Math.max(1, Math.min(30, parseInt(body.sprintDays || 10, 10)));
  const sprintDailyQuota = Math.max(1, Math.min(20, parseInt(body.sprintDailyQuota || 3, 10)));

  // Days-of-week: array of integers 0-6 (0=Sun, 1=Mon, ..., 6=Sat).
  // Default Mon-Fri ([1,2,3,4,5]) if missing or invalid.
  let sprintDaysOfWeek = [1,2,3,4,5];
  if (Array.isArray(body.sprintDaysOfWeek)) {
    const filtered = body.sprintDaysOfWeek
      .map(d => parseInt(d, 10))
      .filter(d => Number.isInteger(d) && d >= 0 && d <= 6);
    if (filtered.length > 0) {
      // Dedupe + sort for stable storage
      sprintDaysOfWeek = Array.from(new Set(filtered)).sort((a, b) => a - b);
    }
  }

  // Nudge time: HH:MM string (24h). Default 07:00. Validated by regex.
  function _validHhmm(v, def) {
    if (typeof v !== 'string') return def;
    if (!/^([01]?\d|2[0-3]):[0-5]\d$/.test(v)) return def;
    const [h, m] = v.split(':');
    return String(h).padStart(2, '0') + ':' + m;
  }
  const sprintNudgeTime = _validHhmm(body.sprintNudgeTime, '07:00');
  const sprintRecapTime = _validHhmm(body.sprintRecapTime, '19:00');

  // sprintTimezone: IANA tz name. Default America/New_York. Validate by
  // attempting an Intl.DateTimeFormat construction — invalid tz throws.
  let sprintTimezone = 'America/New_York';
  if (typeof body.sprintTimezone === 'string' && body.sprintTimezone) {
    try { new Intl.DateTimeFormat('en-US', { timeZone: body.sprintTimezone }); sprintTimezone = body.sprintTimezone; }
    catch (e) { /* keep default */ }
  }

  const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  const profile = raw ? JSON.parse(raw) : {};
  profile.sprintStart = new Date().toISOString();
  profile.sprintDays = sprintDays;
  profile.sprintDailyQuota = sprintDailyQuota;
  profile.sprintDaysOfWeek = sprintDaysOfWeek;
  profile.sprintNudgeTime = sprintNudgeTime;
  profile.sprintRecapTime = sprintRecapTime;
  profile.sprintTimezone = sprintTimezone;
  profile.sprintSnoozedDays = []; // fresh sprint, fresh snooze list
  profile.user = slug;
  profile.editedAt = new Date().toISOString();
  await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(profile));
  return Response.json({
    status: 'started',
    sprintStart: profile.sprintStart,
    sprintDays,
    sprintDailyQuota,
    sprintDaysOfWeek,
    sprintNudgeTime,
    sprintRecapTime,
    sprintTimezone
  }, { headers: cors });
}

async function handleSprintReset(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  let authed = await checkEditKey(request, env, slug);
  if (!authed) {
    const sess = await sessionFromRequest(request, env);
    if (sess && sess.slug === slug) authed = true;
  }
  if (!authed) {
    const ak = request.headers.get('X-Admin-Key');
    if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) authed = true;
  }
  if (!authed) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
  const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  const profile = raw ? JSON.parse(raw) : {};
  profile.sprintStart = '';
  profile.editedAt = new Date().toISOString();
  await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(profile));
  return Response.json({ status: 'reset' }, { headers: cors });
}

// --- /api/sprint/snooze-today (2026-05-28) -----------------------------
// Adds today's ET date to profile.sprintSnoozedDays so the cron skips
// sending emails on this date. Idempotent — POSTing twice on the same
// day is a no-op (date is already in the list).
async function handleSprintSnoozeToday(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  let authed = await checkEditKey(request, env, slug);
  if (!authed) {
    const sess = await sessionFromRequest(request, env);
    if (sess && sess.slug === slug) authed = true;
  }
  if (!authed) {
    const ak = request.headers.get('X-Admin-Key');
    if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) authed = true;
  }
  if (!authed) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
  const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  const profile = raw ? JSON.parse(raw) : {};
  if (!profile.sprintStart) return Response.json({ error: 'No active sprint' }, { status: 400, headers: cors });
  if (!Array.isArray(profile.sprintSnoozedDays)) profile.sprintSnoozedDays = [];
  const etDate = _etDateStr(new Date());
  if (!profile.sprintSnoozedDays.includes(etDate)) {
    profile.sprintSnoozedDays.push(etDate);
    // Keep list small — only last 30 entries needed
    if (profile.sprintSnoozedDays.length > 30) profile.sprintSnoozedDays = profile.sprintSnoozedDays.slice(-30);
  }
  profile.editedAt = new Date().toISOString();
  await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(profile));
  return Response.json({ status: 'snoozed', date: etDate, snoozedDays: profile.sprintSnoozedDays }, { headers: cors });
}

// --- /api/sprint/complete (2026-05-28) --------------------------------
// End-of-sprint review: records this sprint's outcome to sprintHistory[],
// clears sprintStart so the dashboard stops showing the sprint strip, and
// preserves the chosen daysOfWeek/nudgeTime as defaults for the next sprint.
// Body: { appliedCount, advancedCount, rejectedCount, feedback?: {...} }
async function handleSprintComplete(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  let authed = await checkEditKey(request, env, slug);
  if (!authed) {
    const sess = await sessionFromRequest(request, env);
    if (sess && sess.slug === slug) authed = true;
  }
  if (!authed) {
    const ak = request.headers.get('X-Admin-Key');
    if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) authed = true;
  }
  if (!authed) return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });

  const body = await request.json().catch(() => ({}));
  const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  const profile = raw ? JSON.parse(raw) : {};
  if (!profile.sprintStart) {
    return Response.json({ error: 'No active sprint to complete' }, { status: 400, headers: cors });
  }

  const _safeInt = (v, def) => {
    const n = parseInt(v, 10);
    return Number.isFinite(n) && n >= 0 ? n : def;
  };
  const _safeStrArr = (a) => Array.isArray(a)
    ? a.filter(s => typeof s === 'string').slice(0, 10).map(s => s.slice(0, 80))
    : [];

  const fb = (body && body.feedback && typeof body.feedback === 'object') ? body.feedback : {};
  const feedback = {
    worked: _safeStrArr(fb.worked),
    didnt:  _safeStrArr(fb.didnt),
    note:   (typeof fb.note === 'string' ? fb.note.slice(0, 1000) : '')
  };

  // Compute activeDays — days the user was actually eligible to apply
  // during this sprint (not snoozed, day-of-week allowed, within window).
  // Falls back gracefully if any input is malformed.
  function _computeActiveDays(prof) {
    try {
      const start = new Date(prof.sprintStart);
      const end = new Date();
      if (isNaN(start.getTime())) return _safeInt(prof.sprintDays, 10);
      const tz = (typeof prof.sprintTimezone === 'string' && prof.sprintTimezone) || 'America/New_York';
      const allowedDays = (Array.isArray(prof.sprintDaysOfWeek) && prof.sprintDaysOfWeek.length)
        ? prof.sprintDaysOfWeek.map(Number)
        : [1, 2, 3, 4, 5];
      const snoozed = new Set(Array.isArray(prof.sprintSnoozedDays) ? prof.sprintSnoozedDays : []);
      const plannedDays = _safeInt(prof.sprintDays, 10);
      // Cap iteration at min(elapsed-days+1, plannedDays) so an early
      // end before sprint window is over doesn't count future days.
      const elapsedDays = Math.max(1, Math.floor((end - start) / 86400000) + 1);
      const cap = Math.min(elapsedDays, plannedDays);
      let active = 0;
      for (let i = 0; i < cap; i++) {
        const d = new Date(start.getTime() + i * 86400000);
        const dow = _localDowNow(d, tz);
        const date = _localDateStr(d, tz);
        if (!allowedDays.includes(dow)) continue;
        if (snoozed.has(date)) continue;
        active++;
      }
      return active;
    } catch (e) { return _safeInt(prof.sprintDays, 10); }
  }
  const activeDays = _computeActiveDays(profile);

  const record = {
    startedAt:      profile.sprintStart,
    endedAt:        new Date().toISOString(),
    daysPlanned:    _safeInt(profile.sprintDays, 10),
    activeDays:     activeDays,
    dailyQuota:     _safeInt(profile.sprintDailyQuota, 3),
    daysOfWeek:     Array.isArray(profile.sprintDaysOfWeek) ? profile.sprintDaysOfWeek : [1,2,3,4,5],
    nudgeTime:      (typeof profile.sprintNudgeTime === 'string' && profile.sprintNudgeTime) ? profile.sprintNudgeTime : '07:00',
    recapTime:      (typeof profile.sprintRecapTime === 'string' && profile.sprintRecapTime) ? profile.sprintRecapTime : '19:00',
    timezone:       (typeof profile.sprintTimezone === 'string' && profile.sprintTimezone) ? profile.sprintTimezone : 'America/New_York',
    appliedCount:   _safeInt(body.appliedCount, 0),
    advancedCount:  _safeInt(body.advancedCount, 0),
    rejectedCount:  _safeInt(body.rejectedCount, 0),
    feedback
  };

  if (!Array.isArray(profile.sprintHistory)) profile.sprintHistory = [];
  profile.sprintHistory.push(record);
  // Cap history to last 12 sprints so KV value stays small
  if (profile.sprintHistory.length > 12) {
    profile.sprintHistory = profile.sprintHistory.slice(-12);
  }
  profile.sprintStart = '';
  // sprintDays / sprintDailyQuota / sprintDaysOfWeek / sprintNudgeTime stay
  // on the profile as the *defaults* for the next sprint config modal open.
  profile.editedAt = new Date().toISOString();
  await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(profile));
  return Response.json({ status: 'completed', historyLength: profile.sprintHistory.length, record }, { headers: cors });
}


// --- /api/picks (per-day pick stability) -------------------------------
// GET  → returns { date, fingerprints[] } for today, or {} if not stamped.
// POST { fingerprints: [...] } → stamps today's picks. Idempotent: re-stamping
//   the same day overwrites.
// DELETE → clears today's stamp so dashboard recomputes on next load.
// Stored at uk(slug, 'picks:today') = { date: 'YYYY-MM-DD', fingerprints: [...], stampedAt }
async function handlePicks(request, env, cors, slug) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });

  // 3-tier auth: edit key OR own session OR admin key
  async function authorize() {
    if (await checkEditKey(request, env, slug)) return true;
    const sess = await sessionFromRequest(request, env);
    if (sess && sess.slug === slug) return true;
    const ak = request.headers.get('X-Admin-Key');
    if (ak && env.ADMIN_KEY && ak === env.ADMIN_KEY) return true;
    return false;
  }
  if (!(await authorize())) {
    return Response.json({ error: 'Auth required' }, { status: 401, headers: cors });
  }

  const today = new Date().toISOString().slice(0, 10);
  const key = uk(slug, 'picks:today');

  if (request.method === 'GET') {
    const raw = await env.RESUMES.get(key);
    if (!raw) return Response.json({}, { headers: cors });
    let parsed;
    try { parsed = JSON.parse(raw); } catch (e) { return Response.json({}, { headers: cors }); }
    // Auto-expire stale stamps — return empty if not from today
    if (!parsed || parsed.date !== today) return Response.json({}, { headers: cors });
    return Response.json(parsed, { headers: cors });
  }

  if (request.method === 'POST') {
    const body = await request.json().catch(() => ({}));
    const fps = Array.isArray(body && body.fingerprints) ? body.fingerprints : null;
    if (!fps) return Response.json({ error: 'Body must be { fingerprints: [...] }' }, { status: 400, headers: cors });
    // Cap at 10 to prevent abuse
    const fpsLimited = fps.filter(f => typeof f === 'string').slice(0, 10);
    const record = { date: today, fingerprints: fpsLimited, stampedAt: new Date().toISOString() };
    await env.RESUMES.put(key, JSON.stringify(record));
    return Response.json(record, { headers: cors });
  }

  if (request.method === 'DELETE') {
    await env.RESUMES.delete(key);
    return Response.json({ status: 'cleared' }, { headers: cors });
  }

  return new Response('Use GET / POST / DELETE', { status: 405, headers: cors });
}

// --- /admin/clear-all-picks --------------------------------------------
// One-shot admin endpoint: wipes today's stamped picks for every known user.
// Pairs with the self-healing in refreshFocusPanel; this is the belt-and-
// suspenders for any user the self-heal missed (stale device, offline, etc).
// Returns { cleared: N, users: [slug, ...] }.
async function handleAdminClearAllPicks(request, env, cors) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  if (!env.ADMIN_KEY) return Response.json({ error: 'Worker missing ADMIN_KEY secret' }, { status: 500, headers: cors });
  if (request.headers.get('X-Admin-Key') !== env.ADMIN_KEY) {
    return Response.json({ error: 'Invalid X-Admin-Key' }, { status: 401, headers: cors });
  }
  if (request.method !== 'POST' && request.method !== 'DELETE') {
    return new Response('Use POST or DELETE', { status: 405, headers: cors });
  }
  await migrateLegacyIfNeeded(env);
  const users = await bootstrapUsersListIfEmpty(env);
  const cleared = [];
  for (const u of users) {
    try {
      await env.RESUMES.delete(uk(u.slug, 'picks:today'));
      cleared.push(u.slug);
    } catch (e) {}
  }
  return Response.json({ cleared: cleared.length, users: cleared }, { headers: cors });
}

async function handleAdminUsers(request, env, cors) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  if (!env.ADMIN_KEY) return Response.json({ error: 'Worker missing ADMIN_KEY secret' }, { status: 500, headers: cors });
  if (request.headers.get('X-Admin-Key') !== env.ADMIN_KEY) {
    return Response.json({ error: 'Invalid X-Admin-Key' }, { status: 401, headers: cors });
  }

  await migrateLegacyIfNeeded(env);
  let users = await bootstrapUsersListIfEmpty(env);

  // GET — rich list with email + status
  if (request.method === 'GET') {
    const enriched = [];
    for (const u of users) {
      const activeId = await env.RESUMES.get(uk(u.slug, 'resume:active'));
      const profile = await env.RESUMES.get(uk(u.slug, 'skills_profile'));
      const editKey = await env.RESUMES.get(uk(u.slug, 'edit_key'));
      // Engagement rollup from tracker — validates auto-learn threshold
      let trackerSummary = null;
      try {
        const trackerRaw = await env.RESUMES.get(uk(u.slug, 'tracker'));
        if (trackerRaw) {
          const tracker = JSON.parse(trackerRaw) || {};
          const all = Object.values(tracker);
          const cutoff30 = Date.now() - 30 * 24 * 3600 * 1000;
          const dismissedByCompany = {};
          let counts = { applied: 0, dismissed: 0, phonescreen: 0, onsite: 0, offer: 0, rejected: 0, saved: 0 };
          let dismissedPast30 = 0;
          for (const t of all) {
            if (!t) continue;
            const st = String(t.status || '').toLowerCase();
            if (st in counts) counts[st] += 1;
            if (st === 'dismissed') {
              const ts = Date.parse(t.lastUpdated || '');
              if (!isNaN(ts) && ts >= cutoff30) dismissedPast30 += 1;
              const co = String(t.company || '').trim();
              if (co) dismissedByCompany[co] = (dismissedByCompany[co] || 0) + 1;
            }
          }
          const topDismissed = Object.entries(dismissedByCompany)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([company, count]) => ({ company, count }));
          trackerSummary = {
            total: all.length,
            ...counts,
            dismissedPast30Days: dismissedPast30,
            topDismissedCompanies: topDismissed,
          };
        }
      } catch (e) { /* tracker may be missing or malformed */ }
      // excludeCompanies for context on what's already auto-learned
      let excludeCompanies = [];
      let lastAutoLearn = null;
      try {
        if (profile) {
          const p = JSON.parse(profile);
          excludeCompanies = Array.isArray(p.excludeCompanies) ? p.excludeCompanies : [];
          lastAutoLearn = p.lastAutoLearn || null;
        }
      } catch (e) {}
      enriched.push({
        ...u,
        hasResume: !!activeId,
        hasProfile: !!profile,
        editKey: editKey || '',
        tracker: trackerSummary,
        excludeCompanies,
        lastAutoLearn,
      });
    }
    return Response.json({ users: enriched }, { headers: cors });
  }

  // POST — create new user OR update existing, return invite details
  if (request.method === 'POST') {
    const body = await request.json().catch(() => null);
    if (!body || !body.name) return Response.json({ error: 'Body must include {name, email?, slug?, editKey?, resetKey?}' }, { status: 400, headers: cors });

    const slug = body.slug || generateSlug(body.name, users);
    if (!/^[a-z0-9_-]{1,32}$/.test(slug)) {
      return Response.json({ error: 'slug must be lowercase alphanumeric / dash / underscore, up to 32 chars' }, { status: 400, headers: cors });
    }
    const idx = users.findIndex(u => u.slug === slug);
    const isUpdate = idx >= 0;

    // EditKey logic: explicit > resetKey forces new > existing on update > new on create
    let editKey;
    if (body.editKey) {
      editKey = body.editKey;
    } else if (body.resetKey === true) {
      editKey = generatePassword(16);
    } else if (isUpdate) {
      editKey = (await env.RESUMES.get(uk(slug, 'edit_key'))) || generatePassword(16);
    } else {
      editKey = generatePassword(16);
    }

    const email = (body.email || '').trim();
    const name = body.name.trim();

    await env.RESUMES.put(uk(slug, 'edit_key'), editKey);
    await env.RESUMES.put(uk(slug, 'name'), name);

    const userEntry = {
      slug,
      name,
      email,
      createdAt: isUpdate ? users[idx].createdAt : new Date().toISOString(),
    };
    if (isUpdate) users[idx] = userEntry;
    else users.push(userEntry);
    await writeUsersList(env, users);

    return Response.json({ status: 'ok', user: userEntry, editKey, isUpdate }, { headers: cors });
  }

  // DELETE — remove user and all their data
  if (request.method === 'DELETE') {
    const body = await request.json().catch(() => null);
    if (!body || !body.slug) return Response.json({ error: 'Body must include {slug}' }, { status: 400, headers: cors });
    if (body.slug === DEFAULT_USER) {
      return Response.json({ error: 'Refusing to delete the default user (geetu). Edit user:geetu:* keys manually if needed.' }, { status: 400, headers: cors });
    }
    // Delete all user:{slug}:* keys
    const scan = await env.RESUMES.list({ prefix: uk(body.slug, '') });
    for (const k of scan.keys) await env.RESUMES.delete(k.name);
    // Remove from users:list
    users = users.filter(u => u.slug !== body.slug);
    await writeUsersList(env, users);
    return Response.json({ status: 'deleted', slug: body.slug, removed: scan.keys.length }, { headers: cors });
  }

  return new Response('Use GET, POST, or DELETE', { status: 405, headers: cors });
}

// =====================================================================
// Application tracker (server-side replacement for localStorage tracker)
// =====================================================================
// KV: user:{slug}:tracker -> JSON map { [fp]: trackerRecord }
//
// trackerRecord:
//   { fp, title, company, url,
//     status, statusHistory: [{status, at}],
//     appliedAt, lastUpdated,
//     notes, recruiter,
//     prepKit, interviewPrep, salary }

async function getTracker(env, slug) {
  const raw = await env.RESUMES.get(uk(slug, 'tracker'));
  if (!raw) return {};
  try { return JSON.parse(raw); } catch (e) { return {}; }
}

async function saveTracker(env, slug, tracker) {
  await env.RESUMES.put(uk(slug, 'tracker'), JSON.stringify(tracker));
}

async function handleTracker(request, env, cors, slug) {
  if (!env.RESUMES) return Response.json({ error: 'RESUMES KV binding missing' }, { status: 500, headers: cors });
  if (request.method === 'GET') {
    return Response.json({ tracker: await getTracker(env, slug) }, { headers: cors });
  }
  if (request.method !== 'POST') return new Response('GET or POST', { status: 405, headers: cors });
  if (!(await checkEditKey(request, env, slug))) return Response.json({ error: 'Invalid X-Edit-Key' }, { status: 401, headers: cors });

  const body = await request.json().catch(() => null);
  if (!body || !body.action) return Response.json({ error: 'Missing action' }, { status: 400, headers: cors });

  const tracker = await getTracker(env, slug);
  const now = new Date().toISOString();
  const fp = body.fp;

  function record() {
    if (!tracker[fp]) {
      tracker[fp] = {
        fp,
        title: (body.jobMeta || {}).title || '',
        company: (body.jobMeta || {}).company || '',
        url: (body.jobMeta || {}).url || '',
        statusHistory: [],
        appliedAt: null,
        lastUpdated: now,
      };
    } else if (body.jobMeta) {
      // Refresh job meta on subsequent calls (in case title/url updated)
      const r = tracker[fp];
      if (body.jobMeta.title) r.title = body.jobMeta.title;
      if (body.jobMeta.company) r.company = body.jobMeta.company;
      if (body.jobMeta.url) r.url = body.jobMeta.url;
    }
    return tracker[fp];
  }

  switch (body.action) {
    case 'setStatus': {
      if (!fp || !body.status) return Response.json({ error: 'fp and status required' }, { status: 400, headers: cors });
      const r = record();
      r.status = body.status;
      r.statusHistory = r.statusHistory || [];
      r.statusHistory.push({ status: body.status, at: now });
      if (body.status === 'applied' && !r.appliedAt) r.appliedAt = now;
      r.lastUpdated = now;
      // ENGAGEMENT LEARNING (2026-05-27): if this is a dismissal AND the user
      // has already dismissed 3+ jobs at the same company in the last 30 days,
      // auto-add the company to their excludeCompanies. Saves the user from
      // having to repeatedly hit X on the same employer.
      if (body.status === 'dismissed' && r.company) {
        try {
          const company = String(r.company).trim().toLowerCase();
          if (company) {
            const cutoff = Date.now() - 30 * 24 * 3600 * 1000;
            let dismissCount = 0;
            for (const t of Object.values(tracker)) {
              if (!t || t.status !== 'dismissed') continue;
              if (String(t.company || '').trim().toLowerCase() !== company) continue;
              const ts = Date.parse(t.lastUpdated || t.appliedAt || '');
              if (!isNaN(ts) && ts >= cutoff) dismissCount += 1;
            }
            // Include THIS dismissal (just set)
            if (dismissCount >= 3) {
              const profRaw = await env.RESUMES.get(uk(slug, 'skills_profile'));
              if (profRaw) {
                const profile = JSON.parse(profRaw);
                const excl = Array.isArray(profile.excludeCompanies) ? profile.excludeCompanies : [];
                const exclLower = new Set(excl.map(x => String(x).toLowerCase()));
                if (!exclLower.has(company)) {
                  profile.excludeCompanies = [...excl, r.company.trim()];
                  profile.lastAutoLearn = { kind: 'excludeCompany', value: r.company, dismissCount, at: now };
                  await env.RESUMES.put(uk(slug, 'skills_profile'), JSON.stringify(profile));
                }
              }
            }
          }
        } catch (e) { /* learning is best-effort */ }
      }
      break;
    }
    case 'clearStatus': {
      if (!fp) return Response.json({ error: 'fp required' }, { status: 400, headers: cors });
      delete tracker[fp];
      break;
    }
    case 'setNotes': {
      if (!fp) return Response.json({ error: 'fp required' }, { status: 400, headers: cors });
      const r = record();
      r.notes = String(body.notes || '').slice(0, 8000);
      r.lastUpdated = now;
      break;
    }
    case 'setRecruiter': {
      if (!fp) return Response.json({ error: 'fp required' }, { status: 400, headers: cors });
      const r = record();
      r.recruiter = String(body.recruiter || '').slice(0, 500);
      r.lastUpdated = now;
      break;
    }
    case 'savePrepKit': {
      if (!fp) return Response.json({ error: 'fp required' }, { status: 400, headers: cors });
      const r = record();
      r.prepKit = body.prepKit || null;
      r.lastUpdated = now;
      break;
    }
    case 'saveInterviewPrep': {
      if (!fp) return Response.json({ error: 'fp required' }, { status: 400, headers: cors });
      const r = record();
      r.interviewPrep = body.interviewPrep || null;
      r.lastUpdated = now;
      break;
    }
    case 'saveSalary': {
      if (!fp) return Response.json({ error: 'fp required' }, { status: 400, headers: cors });
      const r = record();
      r.salary = body.salary || null;
      r.lastUpdated = now;
      break;
    }
    default:
      return Response.json({ error: 'Unknown action: ' + body.action }, { status: 400, headers: cors });
  }

  await saveTracker(env, slug, tracker);
  return Response.json({ status: 'ok', record: tracker[fp] || null }, { headers: cors });
}

// =====================================================================
// /draft-followup — AI-drafted polite check-in email
// =====================================================================
async function handleDraftFollowup(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY' }, { status: 500, headers: cors });
  const body = await request.json().catch(() => null);
  if (!body || !body.fp) return Response.json({ error: 'fp required' }, { status: 400, headers: cors });

  const tracker = await getTracker(env, slug);
  const rec = tracker[body.fp];
  if (!rec) return Response.json({ error: 'Not in tracker' }, { status: 404, headers: cors });

  const resumeJson = await getActiveResume(env, slug);
  let candidateName = '';
  try { const r = JSON.parse(resumeJson || '{}'); candidateName = r?.personal?.name || ''; } catch (e) {}
  const daysSince = rec.lastUpdated ? Math.floor((Date.now() - new Date(rec.lastUpdated).getTime()) / 86400000) : 0;

  const prompt = `Write a brief, polite follow-up email from ${candidateName || 'a senior candidate'} to a hiring manager / recruiter at ${rec.company} about the ${rec.title} role.

Context:
- Current status: ${rec.status || 'applied'}
- Days since last update: ${daysSince}
- Recruiter/contact: ${rec.recruiter || '(not specified)'}
- Notes the candidate has: ${rec.notes || '(none)'}

Tone: warm, confident, not pushy. 4-6 short sentences. No fluff. Include a soft call-to-action (e.g., "happy to share availability for next steps" or "would value a quick update when you have a moment").

Return JSON with exactly:
{
  "subject": "...",
  "body": "..."
}`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 800, messages: [{ role: 'user', content: prompt }] }),
    });
    if (!r.ok) return Response.json({ error: 'Anthropic error' }, { status: 502, headers: cors });
    const data = await r.json();
    const text = data.content?.[0]?.text || '';
    const cleaned = text.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/\s*```$/, '').trim();
    let parsed;
    try { parsed = JSON.parse(cleaned); } catch (e) { parsed = { subject: 'Following up on the ' + rec.title + ' role', body: text }; }
    return Response.json(parsed, { headers: cors });
  } catch (e) { return Response.json({ error: String(e) }, { status: 500, headers: cors }); }
}

// =====================================================================
// /interview-prep — AI generates likely interview questions + model answers
// =====================================================================
async function handleInterviewPrep(request, env, cors, slug) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!env.ANTHROPIC_API_KEY) return Response.json({ error: 'Missing ANTHROPIC_API_KEY' }, { status: 500, headers: cors });
  const body = await request.json().catch(() => null);
  if (!body || !body.jobTitle || !body.company) return Response.json({ error: 'jobTitle + company required' }, { status: 400, headers: cors });

  const resumeJson = await getActiveResume(env, slug);
  if (!resumeJson) return Response.json({ error: 'No resume saved' }, { status: 400, headers: cors });

  const prompt = `Generate 12 likely interview questions for a candidate applying to "${body.jobTitle}" at "${body.company}". For each, write a model answer grounded in the candidate's actual resume below — use specific accomplishments, companies, and numbers from the resume. Mix question types: behavioural (4-5), domain-technical (4-5), leadership/strategy (2-3).

Return JSON with exactly this shape (no prose, no fences):
{ "questions": [ { "q": "...", "a": "...", "type": "behavioural|technical|leadership" } ] }

Each answer 4-6 sentences. Use STAR-style structure for behavioural. Cite specific resume bullets where possible. Do not invent.

JOB:
Title: ${body.jobTitle}
Company: ${body.company}
${body.jobDescription ? 'Description: ' + body.jobDescription.slice(0, 2000) : ''}

CANDIDATE RESUME (JSON):
${resumeJson}`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 6000, messages: [{ role: 'user', content: prompt }] }),
    });
    if (!r.ok) return Response.json({ error: 'Anthropic error' }, { status: 502, headers: cors });
    const data = await r.json();
    const text = data.content?.[0]?.text || '';
    const cleaned = text.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/\s*```$/, '').trim();
    let parsed;
    try { parsed = JSON.parse(cleaned); } catch (e) { return Response.json({ error: 'AI did not return valid JSON' }, { status: 502, headers: cors }); }
    return Response.json(parsed, { headers: cors });
  } catch (e) { return Response.json({ error: String(e) }, { status: 500, headers: cors }); }
}

// =====================================================================
// /generate-digest — returns digest payload for daily email
// =====================================================================
async function handleGenerateDigest(request, env, cors, slug) {
  if (request.method !== 'GET') return new Response('GET only', { status: 405, headers: cors });
  // Public read — returns user's stale apps + their job-search status summary
  const tracker = await getTracker(env, slug);
  const profileRaw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  let primaryRole = '';
  try { primaryRole = (JSON.parse(profileRaw || '{}').primaryRole) || ''; } catch (e) {}
  const userName = (await env.RESUMES.get(uk(slug, 'name'))) || slug;

  const now = Date.now();
  const stale = [];
  let counts = { applied: 0, phonescreen: 0, onsite: 0, offer: 0, rejected: 0 };
  for (const rec of Object.values(tracker)) {
    if (rec.status && counts[rec.status] !== undefined) counts[rec.status]++;
    const last = rec.lastUpdated ? new Date(rec.lastUpdated).getTime() : 0;
    const daysSince = Math.floor((now - last) / 86400000);
    if (rec.status === 'applied' && daysSince >= 7) {
      stale.push({ fp: rec.fp, title: rec.title, company: rec.company, daysSince });
    }
  }
  return Response.json({ slug, userName, primaryRole, counts, staleApplications: stale.slice(0, 10) }, { headers: cors });
}

// =================================================================
// /rerank-titles  --  AI fit score (0..100) for a batch of job titles
// using the user's skills_profile. Used by the dashboard to re-rank
// the keyword-filtered results. Public (no edit key required) so
// anonymous browser sessions on the dashboard can call it.
// =================================================================
async function handleRerankTitles(request, env, cors, slug) {
  if (request.method !== 'POST') {
    return new Response('POST only', { status: 405, headers: cors });
  }
  if (!env.ANTHROPIC_API_KEY) {
    return Response.json({ error: 'No ANTHROPIC_API_KEY' }, { status: 500, headers: cors });
  }
  let body;
  try { body = await request.json(); } catch (e) { body = {}; }
  const items = Array.isArray(body.items) ? body.items.slice(0, 60) : [];
  if (!items.length) return Response.json({ scores: {} }, { headers: cors });

  const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
  if (!raw) return Response.json({ scores: {} }, { headers: cors });
  let profile;
  try { profile = JSON.parse(raw); } catch (e) { return Response.json({ scores: {} }, { headers: cors }); }

  const primary = profile.primaryRole || '';
  const seniority = profile.seniorityLevel || '';
  const targets = (profile.targetTitles || []).slice(0, 12).join(', ');
  const industries = (profile.industries || []).slice(0, 8).join(', ');
  const specialties = (profile.specialties || []).slice(0, 8).join(', ');
  const summary = (profile.summary || '').slice(0, 800);

  const titleList = items.map((it, i) => `${i + 1}. [${it.fp}] ${it.title}`).join('\n');

  const prompt = `You are scoring how well each job title matches the candidate's actual target. Return ONLY a JSON object mapping each job's fingerprint id to an integer 0..100. No prose, no markdown.

CANDIDATE PROFILE
- Primary role: ${primary}
- Seniority: ${seniority}
- Their explicit target titles: ${targets}
- Industries: ${industries}
- Specialties: ${specialties}
- Summary: ${summary}

SCORING GUIDANCE
- 90-100: exact target-title match at their seniority in their industry
- 70-89:  same function family at their level, possibly different industry
- 50-69:  related function or one level off
- 30-49:  loose adjacency
- 0-29:   wrong role family or wrong seniority

JOB TITLES TO SCORE (fingerprints in brackets)
${titleList}

Return JSON shape: {"<fp>": <int>, "<fp>": <int>, ...}`;

  try {
    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 2048,
        messages: [{ role: 'user', content: prompt }]
      })
    });
    if (!resp.ok) {
      return Response.json({ scores: {}, error: 'AI call failed' }, { status: 500, headers: cors });
    }
    const aiData = await resp.json();
    const text = (aiData.content && aiData.content[0] && aiData.content[0].text) || '';
    // Strip code fences if any
    const cleaned = text.replace(/^```(?:json)?\s*/, '').replace(/\s*```$/, '').trim();
    let scores;
    try { scores = JSON.parse(cleaned); } catch (e) {
      // Try to find the first {...} block
      const m = text.match(/\{[\s\S]*\}/);
      if (m) { try { scores = JSON.parse(m[0]); } catch (ee) { scores = {}; } }
      else scores = {};
    }
    // Normalize. Accept either int (legacy) or {score, hardBlocker} (new).
    const out = {};
    for (const [k, v] of Object.entries(scores || {})) {
      if (!k) continue;
      if (typeof v === 'object' && v) {
        const n = Math.max(0, Math.min(100, parseInt(v.score, 10) || 0));
        const hb = !!v.hardBlocker;
        out[k] = { score: hb ? 0 : n, hardBlocker: hb };
      } else {
        const n = Math.max(0, Math.min(100, parseInt(v, 10) || 0));
        out[k] = { score: n, hardBlocker: false };
      }
    }
    return Response.json({ scores: out }, { headers: cors });
  } catch (e) {
    return Response.json({ scores: {}, error: String(e) }, { status: 500, headers: cors });
  }
}


// ============================================================
// Slice A — Auth (signup / login / logout / session / password)
// KV layout:
//   auth:email:{email}              -> slug                 (lookup)
//   user:{slug}:auth                -> { email, name, hash, salt, createdAt }
//   session:{token}                 -> { slug, expiresAt }  (TTL'd)
// Tokens are returned in JSON body; clients send them via
// `Authorization: Bearer <token>` header (cross-origin-friendly).
// ============================================================

const SESSION_TTL_SECONDS = 60 * 60 * 24 * 30; // 30 days
const PBKDF2_ITERATIONS = 100000;

function _b64(bytes) {
  let s = '';
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

function _b64url(bytes) {
  return _b64(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function _randomBytes(n) {
  const a = new Uint8Array(n);
  crypto.getRandomValues(a);
  return a;
}

async function hashPasswordPbkdf2(password, saltB64) {
  const enc = new TextEncoder();
  const saltBytes = Uint8Array.from(atob(saltB64), c => c.charCodeAt(0));
  const keyMaterial = await crypto.subtle.importKey(
    'raw', enc.encode(password), { name: 'PBKDF2' }, false, ['deriveBits']
  );
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt: saltBytes, iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
    keyMaterial,
    256
  );
  return _b64(new Uint8Array(bits));
}

async function createSession(env, slug) {
  const token = _b64url(_randomBytes(32));
  const expiresAt = Date.now() + SESSION_TTL_SECONDS * 1000;
  await env.RESUMES.put(
    `session:${token}`,
    JSON.stringify({ slug, expiresAt }),
    { expirationTtl: SESSION_TTL_SECONDS }
  );
  return { token, expiresAt };
}

async function sessionFromRequest(request, env) {
  const authHeader = request.headers.get('Authorization') || '';
  const m = authHeader.match(/^Bearer\s+(.+)$/i);
  if (!m) return null;
  const token = m[1].trim();
  const raw = await env.RESUMES.get(`session:${token}`);
  if (!raw) return null;
  try {
    const sess = JSON.parse(raw);
    if (sess.expiresAt && sess.expiresAt < Date.now()) {
      await env.RESUMES.delete(`session:${token}`);
      return null;
    }
    return { token, slug: sess.slug };
  } catch (e) { return null; }
}

function _json(body, status, cors, extraHeaders) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...cors, ...(extraHeaders || {}) }
  });
}

function _normEmail(s) { return String(s || '').trim().toLowerCase(); }
function _isValidEmail(e) { return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e); }

// POST /api/auth/signup  { email, password, name }
async function handleSignup(request, env, cors) {
  if (request.method !== 'POST') return _json({ error: 'POST only' }, 405, cors);
  if (!env.RESUMES) return _json({ error: 'RESUMES KV binding missing' }, 500, cors);
  let body;
  try { body = await request.json(); } catch (e) { return _json({ error: 'Bad JSON' }, 400, cors); }
  const email = _normEmail(body.email);
  const password = String(body.password || '');
  const name = String(body.name || '').trim();
  if (!_isValidEmail(email)) return _json({ error: 'Valid email required' }, 400, cors);
  if (password.length < 8) return _json({ error: 'Password must be at least 8 characters' }, 400, cors);
  if (!name) return _json({ error: 'Name required' }, 400, cors);

  const existing = await env.RESUMES.get(`auth:email:${email}`);
  if (existing) return _json({ error: 'An account with that email already exists. Try logging in.' }, 409, cors);

  await migrateLegacyIfNeeded(env);
  await migrateUserStatusIfNeeded(env);
  const users = await bootstrapUsersListIfEmpty(env);

  // Alpha cap: 25 self-serve signups. Admin can still add more via /admin/users.
  const ALPHA_CAP = parseInt(env.ALPHA_CAP || '25', 10);
  if (users.length >= ALPHA_CAP) {
    return _json({ error: `Alpha is full (${ALPHA_CAP}/${ALPHA_CAP} spots taken). Email us at hello@officebeatllc.com to join the waitlist.` }, 403, cors);
  }

  const slug = generateSlug(name, users);

  const salt = _b64(_randomBytes(16));
  const hash = await hashPasswordPbkdf2(password, salt);
  const createdAt = new Date().toISOString();

  await env.RESUMES.put(uk(slug, 'auth'), JSON.stringify({ email, name, hash, salt, createdAt }));
  await env.RESUMES.put(`auth:email:${email}`, slug);
  await env.RESUMES.put(uk(slug, 'name'), name);
  // Slice D: also provision an edit_key so this user can do writes on their dashboard
  // (the per-user HTML dashboards still use X-Edit-Key for write auth).
  if (!(await env.RESUMES.get(uk(slug, 'edit_key')))) {
    await env.RESUMES.put(uk(slug, 'edit_key'), generatePassword(20));
  }

  // APPROVAL GATE (2026-05-26): new signups go to status=pending. Admin
  // approves via /admin/approve-user before the user can log in or build a
  // dashboard. Existing users (backfilled) are status=approved.
  await env.RESUMES.put(uk(slug, 'status'), 'pending');
  await env.RESUMES.put(uk(slug, 'createdAt'), createdAt);

  // Add to users:list so existing admin / refresh flows can see them
  users.push({ slug, name, email, createdAt, status: 'pending' });
  await writeUsersList(env, users);

  // Notify admin via Resend so they can approve quickly.
  // Best-effort — failure here doesn't block signup.
  try {
    if (env.RESEND_API_KEY && env.DIGEST_FROM) {
      const adminEmail = env.ADMIN_NOTIFY_TO || 'team@officebeatllc.com';
      await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + env.RESEND_API_KEY, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from: env.DIGEST_FROM,
          to: [adminEmail],
          subject: `New getmemyjob signup: ${name} (${email})`,
          html: `<p><strong>${name}</strong> &lt;${email}&gt; signed up just now.</p>` +
                `<p>Slug: <code>${slug}</code> · Status: pending</p>` +
                `<p><a href="https://getmemyjob.officebeatllc.com/admin.html" style="background:#5C5CD6;color:white;text-decoration:none;padding:8px 14px;border-radius:6px;font-weight:600;">Review &amp; approve</a></p>`,
        }),
      }).catch(() => {});
    }
  } catch (e) { /* swallow */ }

  // We still issue a session token so the user can land on a "pending" page,
  // but the existing dashboard router (/api/auth/me) will tell them their
  // status. We do NOT trigger refresh-jobs until approved.
  const { token, expiresAt } = await createSession(env, slug);
  return _json({
    ok: true, token, expiresAt, slug, name, email,
    editKey: (await env.RESUMES.get(uk(slug, 'edit_key'))) || null,
    status: 'pending',
    pending: true,
    message: 'Your account is pending approval. We\'ll email you when it\'s ready.'
  }, 200, cors);
}

// POST /api/auth/login  { email, password }
async function handleLogin(request, env, cors) {
  if (request.method !== 'POST') return _json({ error: 'POST only' }, 405, cors);
  if (!env.RESUMES) return _json({ error: 'RESUMES KV binding missing' }, 500, cors);
  let body;
  try { body = await request.json(); } catch (e) { return _json({ error: 'Bad JSON' }, 400, cors); }
  const email = _normEmail(body.email);
  const password = String(body.password || '');
  if (!email || !password) return _json({ error: 'Email and password required' }, 400, cors);

  const slug = await env.RESUMES.get(`auth:email:${email}`);
  if (!slug) return _json({ error: 'Invalid email or password' }, 401, cors);
  const authRaw = await env.RESUMES.get(uk(slug, 'auth'));
  if (!authRaw) return _json({ error: 'Invalid email or password' }, 401, cors);
  let auth;
  try { auth = JSON.parse(authRaw); } catch (e) { return _json({ error: 'Account corrupted; contact admin' }, 500, cors); }
  const hash = await hashPasswordPbkdf2(password, auth.salt);
  if (hash !== auth.hash) return _json({ error: 'Invalid email or password' }, 401, cors);

  // APPROVAL GATE: reject login if not yet approved by admin
  const status = await env.RESUMES.get(uk(slug, 'status'));
  if (status === 'pending') {
    return _json({
      error: 'Your account is pending approval. We\'ll email you when it\'s ready.',
      status: 'pending',
      pending: true,
    }, 403, cors);
  }
  if (status === 'rejected') {
    return _json({
      error: 'Your account application was not approved. Contact hello@officebeatllc.com if you think this is a mistake.',
      status: 'rejected',
    }, 403, cors);
  }

  const { token, expiresAt } = await createSession(env, slug);
  const editKey = await env.RESUMES.get(uk(slug, 'edit_key'));
  return _json({ ok: true, token, expiresAt, slug, name: auth.name, email: auth.email, editKey: editKey || null }, 200, cors);
}

// POST /api/auth/logout    (Authorization: Bearer <token>)
async function handleLogout(request, env, cors) {
  const sess = await sessionFromRequest(request, env);
  if (sess) await env.RESUMES.delete(`session:${sess.token}`);
  return _json({ ok: true }, 200, cors);
}

// GET /api/auth/me         (Authorization: Bearer <token>)
async function handleMe(request, env, cors) {
  const sess = await sessionFromRequest(request, env);
  if (!sess) return _json({ authenticated: false }, 200, cors);
  const authRaw = await env.RESUMES.get(uk(sess.slug, 'auth'));
  if (!authRaw) return _json({ authenticated: false }, 200, cors);
  let auth;
  try { auth = JSON.parse(authRaw); } catch (e) { return _json({ authenticated: false }, 200, cors); }
  // Include the user's per-dashboard edit_key so the frontend can store it
  // and use the existing X-Edit-Key write protocol on the per-user HTML dashboards.
  const editKey = await env.RESUMES.get(uk(sess.slug, 'edit_key'));
  // Approval gate status — undefined means pre-approval-era user; treat as approved.
  const status = (await env.RESUMES.get(uk(sess.slug, 'status'))) || 'approved';
  return _json({
    authenticated: true,
    slug: sess.slug,
    name: auth.name,
    email: auth.email,
    createdAt: auth.createdAt || null,
    editKey: editKey || null,
    status: status,
  }, 200, cors);
}

// POST /api/auth/admin-reset-password  { email, newPassword }
// Admin-only path: lets the platform admin reset ANY user's password
// (including their own) without knowing the current one. This is the
// 'forgot password' recovery path until proper email-based recovery exists.
// Requires X-Admin-Key.
async function handleAdminResetPassword(request, env, cors) {
  if (request.method !== 'POST') return _json({ error: 'POST only' }, 405, cors);
  if (!env.ADMIN_KEY) return _json({ error: 'Worker missing ADMIN_KEY secret' }, 500, cors);
  if (request.headers.get('X-Admin-Key') !== env.ADMIN_KEY) {
    return _json({ error: 'Invalid X-Admin-Key' }, 401, cors);
  }
  let body;
  try { body = await request.json(); } catch (e) { return _json({ error: 'Bad JSON' }, 400, cors); }
  const email = String(body.email || '').trim().toLowerCase();
  let slug = String(body.slug || '').trim().toLowerCase();
  const newPassword = String(body.newPassword || '');
  if (!email && !slug) return _json({ error: 'Body must include {email or slug, newPassword}' }, 400, cors);
  if (newPassword.length < 8) return _json({ error: 'New password must be at least 8 characters' }, 400, cors);

  // 1. Primary lookup: email index
  if (!slug && email) {
    slug = (await env.RESUMES.get(`auth:email:${email}`)) || '';
  }
  // 2. Fallback: scan /users list for matching email (handles legacy accounts
  //    where the email index wasn't populated at signup time)
  if (!slug && email) {
    const usersRaw = await env.RESUMES.get('users:list');
    if (usersRaw) {
      try {
        const users = JSON.parse(usersRaw);
        const match = users.find(u => String(u.email || '').toLowerCase() === email);
        if (match && match.slug) slug = match.slug;
      } catch (e) {}
    }
  }
  if (!slug) return _json({ error: `No account found for ${email || '(no email/slug)'}` }, 404, cors);

  // Load existing auth record OR create a fresh one (for legacy users
  // who exist in users:list but never set a password)
  const authRaw = await env.RESUMES.get(uk(slug, 'auth'));
  const newSalt = _b64(_randomBytes(16));
  const newHash = await hashPasswordPbkdf2(newPassword, newSalt);
  const nowIso = new Date().toISOString();
  let auth;
  let created = false;
  if (authRaw) {
    auth = JSON.parse(authRaw);
    auth.salt = newSalt;
    auth.hash = newHash;
    auth.passwordUpdatedAt = nowIso;
    auth.lastResetBy = 'admin';
  } else {
    // Fresh auth record. Pull email + name from users:list if we can.
    let userMeta = {};
    try {
      const usersRaw = await env.RESUMES.get('users:list');
      if (usersRaw) {
        const users = JSON.parse(usersRaw);
        userMeta = users.find(u => u.slug === slug) || {};
      }
    } catch (e) {}
    auth = {
      slug,
      email: email || userMeta.email || '',
      name: userMeta.name || '',
      salt: newSalt,
      hash: newHash,
      createdAt: nowIso,
      passwordUpdatedAt: nowIso,
      createdBy: 'admin-reset',
      lastResetBy: 'admin',
    };
    created = true;
  }
  await env.RESUMES.put(uk(slug, 'auth'), JSON.stringify(auth));

  // 3. Heal the email index so future logins/resets work via email
  const effEmail = email || (auth.email || '').toLowerCase();
  if (effEmail) {
    try { await env.RESUMES.put(`auth:email:${effEmail}`, slug); } catch (e) {}
  }
  return _json({ ok: true, slug, email: effEmail, resetAt: auth.passwordUpdatedAt, healedEmailIndex: !!effEmail, created }, 200, cors);
}


// POST /api/auth/change-password  { currentPassword, newPassword }
async function handleChangePassword(request, env, cors) {
  if (request.method !== 'POST') return _json({ error: 'POST only' }, 405, cors);
  const sess = await sessionFromRequest(request, env);
  if (!sess) return _json({ error: 'Not authenticated' }, 401, cors);
  let body;
  try { body = await request.json(); } catch (e) { return _json({ error: 'Bad JSON' }, 400, cors); }
  const current = String(body.currentPassword || '');
  const next = String(body.newPassword || '');
  if (next.length < 8) return _json({ error: 'New password must be at least 8 characters' }, 400, cors);
  const authRaw = await env.RESUMES.get(uk(sess.slug, 'auth'));
  if (!authRaw) return _json({ error: 'Account not found' }, 404, cors);
  const auth = JSON.parse(authRaw);
  const curHash = await hashPasswordPbkdf2(current, auth.salt);
  if (curHash !== auth.hash) return _json({ error: 'Current password incorrect' }, 401, cors);
  const newSalt = _b64(_randomBytes(16));
  const newHash = await hashPasswordPbkdf2(next, newSalt);
  auth.salt = newSalt; auth.hash = newHash; auth.passwordUpdatedAt = new Date().toISOString();
  await env.RESUMES.put(uk(sess.slug, 'auth'), JSON.stringify(auth));
  return _json({ ok: true }, 200, cors);
}


// ============================================================
// Slice C — Notes + reminders
// KV: user:{slug}:notes -> { [jobFp]: { text, reminderDate, jobTitle, company, jobUrl, updatedAt } }
// GET is public per-slug (so the dashboard can display them);
// POST/DELETE require X-Edit-Key (legacy) OR a Bearer session matching the slug.
// ============================================================
async function handleNotes(request, env, cors, slug) {
  if (!env.RESUMES) return _json({ error: 'RESUMES KV missing' }, 500, cors);
  const key = uk(slug, 'notes');

  if (request.method === 'GET') {
    const raw = await env.RESUMES.get(key);
    return _json({ notes: raw ? JSON.parse(raw) : {} }, 200, cors);
  }

  // Auth for writes: admin key (any user), or per-user X-Edit-Key, or a Bearer session whose slug matches
  let authed = false;
  if (env.ADMIN_KEY) {
    const adminKey = request.headers.get('X-Admin-Key');
    if (adminKey && adminKey === env.ADMIN_KEY) authed = true;
  }
  if (!authed) authed = await checkEditKey(request, env, slug);
  if (!authed) {
    const sess = await sessionFromRequest(request, env);
    if (sess && sess.slug === slug) authed = true;
  }
  if (!authed) return _json({ error: 'Unauthorized — need X-Admin-Key, X-Edit-Key for this user, or matching Bearer session' }, 401, cors);

  const raw = await env.RESUMES.get(key);
  const notes = raw ? JSON.parse(raw) : {};

  if (request.method === 'POST') {
    let body;
    try { body = await request.json(); } catch (e) { return _json({ error: 'Bad JSON' }, 400, cors); }
    const fp = String(body.fp || '').trim();
    if (!fp) return _json({ error: 'fp (job fingerprint) required' }, 400, cors);
    const text = String(body.text || '').trim();
    const reminderDate = body.reminderDate ? String(body.reminderDate).trim() : null;
    const existing = notes[fp] || {};
    const jobTitle = body.jobTitle != null ? String(body.jobTitle) : (existing.jobTitle || '');
    const company = body.company != null ? String(body.company) : (existing.company || '');
    const jobUrl = body.jobUrl != null ? String(body.jobUrl) : (existing.jobUrl || '');
    if (!text && !reminderDate) {
      delete notes[fp];
    } else {
      notes[fp] = { text, reminderDate, jobTitle, company, jobUrl, updatedAt: new Date().toISOString() };
    }
    await env.RESUMES.put(key, JSON.stringify(notes));
    return _json({ ok: true, notes }, 200, cors);
  }

  if (request.method === 'DELETE') {
    const url = new URL(request.url);
    const fp = url.searchParams.get('fp');
    if (!fp) return _json({ error: 'fp query param required' }, 400, cors);
    delete notes[fp];
    await env.RESUMES.put(key, JSON.stringify(notes));
    return _json({ ok: true, notes }, 200, cors);
  }

  return _json({ error: 'GET/POST/DELETE only' }, 405, cors);
}


// GET /api/auth/capacity — public; returns { taken, cap, available }
async function handleCapacity(request, env, cors) {
  await migrateLegacyIfNeeded(env);
  const users = await bootstrapUsersListIfEmpty(env);
  const cap = parseInt(env.ALPHA_CAP || '25', 10);
  return _json({ taken: users.length, cap, available: Math.max(0, cap - users.length) }, 200, cors);
}

// =====================================================================
// =====================================================================
// Loads admin auth from KV (if user rotated password) or falls back to env.
async function _loadAdminAuth(env) {
  if (env.RESUMES) {
    const raw = await env.RESUMES.get('admin:auth');
    if (raw) {
      try {
        const a = JSON.parse(raw);
        if (a && a.salt && a.hash) {
          return { email: _normEmail(a.email || env.ADMIN_EMAIL || 'team@officebeatllc.com'), salt: a.salt, hash: a.hash };
        }
      } catch (e) {}
    }
  }
  if (env.ADMIN_PASSWORD_HASH && env.ADMIN_PASSWORD_SALT) {
    return {
      email: _normEmail(env.ADMIN_EMAIL || 'team@officebeatllc.com'),
      salt: env.ADMIN_PASSWORD_SALT,
      hash: env.ADMIN_PASSWORD_HASH,
    };
  }
  return null;
}

// POST /api/auth/admin-login  { email, password }
// Returns ADMIN_KEY on success so admin.html can use it as X-Admin-Key.
async function handleAdminLogin(request, env, cors) {
  if (request.method !== 'POST') return _json({ error: 'POST only' }, 405, cors);
  if (!env.ADMIN_KEY) return _json({ error: 'ADMIN_KEY missing' }, 500, cors);
  const stored = await _loadAdminAuth(env);
  if (!stored) return _json({ error: 'Admin login not configured. Set ADMIN_PASSWORD_HASH + ADMIN_PASSWORD_SALT or POST /api/auth/admin-change-password with X-Admin-Key.' }, 503, cors);

  let body;
  try { body = await request.json(); } catch (e) { return _json({ error: 'Bad JSON' }, 400, cors); }
  const email = _normEmail(body.email);
  const password = String(body.password || '');
  if (!email || !password) return _json({ error: 'Email and password required' }, 400, cors);
  if (email !== stored.email) return _json({ error: 'Invalid email or password' }, 401, cors);

  const hash = await hashPasswordPbkdf2(password, stored.salt);
  if (hash !== stored.hash) {
    return _json({ error: 'Invalid email or password' }, 401, cors);
  }

  return _json({ ok: true, adminKey: env.ADMIN_KEY, email: stored.email }, 200, cors);
}

// POST /api/auth/admin-change-password
//   { newPassword, newEmail? }  +  either X-Admin-Key header OR  currentPassword in body
// Writes new salt+hash to KV admin:auth (overrides env going forward).
async function handleAdminChangePassword(request, env, cors) {
  if (request.method !== 'POST') return _json({ error: 'POST only' }, 405, cors);
  if (!env.ADMIN_KEY) return _json({ error: 'ADMIN_KEY missing' }, 500, cors);
  if (!env.RESUMES) return _json({ error: 'RESUMES KV missing' }, 500, cors);

  let body;
  try { body = await request.json(); } catch (e) { return _json({ error: 'Bad JSON' }, 400, cors); }
  const newPassword = String(body.newPassword || '');
  const newEmail = body.newEmail ? _normEmail(body.newEmail) : null;
  if (newPassword.length < 10) return _json({ error: 'Password must be at least 10 characters' }, 400, cors);
  if (newEmail && !_isValidEmail(newEmail)) return _json({ error: 'Invalid newEmail' }, 400, cors);

  const hasKey = request.headers.get('X-Admin-Key') === env.ADMIN_KEY;
  if (!hasKey) {
    const stored = await _loadAdminAuth(env);
    if (!stored) return _json({ error: 'Not authenticated' }, 401, cors);
    const curHash = await hashPasswordPbkdf2(String(body.currentPassword || ''), stored.salt);
    if (curHash !== stored.hash) return _json({ error: 'Current password incorrect' }, 401, cors);
  }

  const prev = await _loadAdminAuth(env);
  const salt = _b64(_randomBytes(16));
  const hash = await hashPasswordPbkdf2(newPassword, salt);
  const finalEmail = newEmail || (prev ? prev.email : _normEmail(env.ADMIN_EMAIL || 'team@officebeatllc.com'));
  await env.RESUMES.put('admin:auth', JSON.stringify({
    email: finalEmail, salt, hash,
    updatedAt: new Date().toISOString(),
  }));
  return _json({ ok: true, email: finalEmail }, 200, cors);
}

// =====================================================================
// Admin approval workflow (2026-05-26)
// =====================================================================
async function handleAdminPendingUsers(request, env, cors) {
  if (request.method !== 'GET') return _json({ error: 'GET only' }, 405, cors);
  if (!env.ADMIN_KEY) return _json({ error: 'ADMIN_KEY missing' }, 500, cors);
  if (request.headers.get('X-Admin-Key') !== env.ADMIN_KEY) {
    return _json({ error: 'Invalid X-Admin-Key' }, 401, cors);
  }
  await migrateUserStatusIfNeeded(env);
  const users = await readUsersList(env);
  const enriched = [];
  for (const u of users) {
    if (!u || !u.slug) continue;
    const status = await env.RESUMES.get(uk(u.slug, 'status'));
    if (status === 'pending') {
      const resumeActive = await env.RESUMES.get(uk(u.slug, 'resume:active'));
      const profileRaw = await env.RESUMES.get(uk(u.slug, 'skills_profile'));
      let primaryRole = '';
      try { primaryRole = (JSON.parse(profileRaw || '{}').primaryRole) || ''; } catch (e) {}
      enriched.push({
        slug: u.slug,
        name: u.name,
        email: u.email,
        createdAt: u.createdAt,
        primaryRole,
        hasResume: !!resumeActive,
        status: 'pending',
      });
    }
  }
  return _json({ pendingUsers: enriched, count: enriched.length }, 200, cors);
}

async function handleAdminApproveUser(request, env, cors) {
  if (request.method !== 'POST') return _json({ error: 'POST only' }, 405, cors);
  if (!env.ADMIN_KEY) return _json({ error: 'ADMIN_KEY missing' }, 500, cors);
  if (request.headers.get('X-Admin-Key') !== env.ADMIN_KEY) {
    return _json({ error: 'Invalid X-Admin-Key' }, 401, cors);
  }
  const url = new URL(request.url);
  const slug = url.searchParams.get('user');
  if (!slug) return _json({ error: 'Missing user= param' }, 400, cors);
  const current = await env.RESUMES.get(uk(slug, 'status'));
  if (!current) return _json({ error: 'User not found' }, 404, cors);

  await env.RESUMES.put(uk(slug, 'status'), 'approved');
  await env.RESUMES.put(uk(slug, 'approvedAt'), new Date().toISOString());

  // Update status in users:list
  const users = await readUsersList(env);
  for (const u of users) {
    if (u.slug === slug) { u.status = 'approved'; break; }
  }
  await writeUsersList(env, users);

  // Trigger refresh-jobs so this user's dashboard gets built now
  try { if (typeof triggerRefreshWorkflow === 'function') triggerRefreshWorkflow(env).catch(() => {}); } catch (e) {}

  // Email the user that their account is approved
  try {
    const authRaw = await env.RESUMES.get(uk(slug, 'auth'));
    const auth = authRaw ? JSON.parse(authRaw) : null;
    const userEmail = auth?.email;
    if (userEmail && env.RESEND_API_KEY && env.DIGEST_FROM) {
      const dashUrl = `https://getmemyjob.officebeatllc.com/${slug}.html`;
      await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + env.RESEND_API_KEY, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from: env.DIGEST_FROM,
          to: [userEmail],
          subject: 'Your getmemyjob account is approved 🎯',
          html: `<p>Hi ${auth?.name || ''},</p>` +
                `<p>You're in. Your personal job-search dashboard is being built and will be ready in ~3 minutes at ` +
                `<a href="${dashUrl}">${dashUrl}</a>.</p>` +
                `<p>Sign in at <a href="https://getmemyjob.officebeatllc.com/login.html">getmemyjob.officebeatllc.com</a>.</p>` +
                `<p>— Amit</p>`,
        }),
      }).catch(() => {});
    }
  } catch (e) { /* swallow */ }

  return _json({ ok: true, slug, status: 'approved' }, 200, cors);
}

async function handleAdminRejectUser(request, env, cors) {
  if (request.method !== 'POST') return _json({ error: 'POST only' }, 405, cors);
  if (!env.ADMIN_KEY) return _json({ error: 'ADMIN_KEY missing' }, 500, cors);
  if (request.headers.get('X-Admin-Key') !== env.ADMIN_KEY) {
    return _json({ error: 'Invalid X-Admin-Key' }, 401, cors);
  }
  const url = new URL(request.url);
  const slug = url.searchParams.get('user');
  if (!slug) return _json({ error: 'Missing user= param' }, 400, cors);
  const current = await env.RESUMES.get(uk(slug, 'status'));
  if (!current) return _json({ error: 'User not found' }, 404, cors);

  await env.RESUMES.put(uk(slug, 'status'), 'rejected');
  await env.RESUMES.put(uk(slug, 'rejectedAt'), new Date().toISOString());

  // Update status in users:list
  const users = await readUsersList(env);
  for (const u of users) {
    if (u.slug === slug) { u.status = 'rejected'; break; }
  }
  await writeUsersList(env, users);

  return _json({ ok: true, slug, status: 'rejected' }, 200, cors);
}


// G2: Daily digest email functions
// =====================================================================

// --- Sprint reminder (overrides digest during active sprint) -----------
// Compute the current hour in the given IANA timezone (handles DST via Intl).
// Returns an integer 0..23. Falls back to UTC hour if Intl is unavailable
// OR if the supplied tz is invalid (caught + retried with America/New_York).
function _localHourNow(now, tz) {
  const try1 = _tryHour(now, tz || 'America/New_York');
  if (try1 != null) return try1;
  // Bad tz string — retry with fallback
  const try2 = _tryHour(now, 'America/New_York');
  if (try2 != null) return try2;
  return now.getUTCHours();
}
function _tryHour(now, tz) {
  try {
    const fmt = new Intl.DateTimeFormat('en-US', { timeZone: tz, hour: 'numeric', hour12: false });
    const v = parseInt(fmt.format(now), 10);
    return Number.isFinite(v) ? v : null;
  } catch (e) { return null; }
}
// Same but for any HH:MM string — returns just the hour as an int.
function _hhmmHour(s) {
  if (typeof s !== 'string') return null;
  const m = /^([01]?\d|2[0-3]):[0-5]\d$/.exec(s);
  return m ? parseInt(m[1], 10) : null;
}
// Day-of-week in the given timezone. 0=Sun..6=Sat.
function _localDowNow(now, tz) {
  const dayMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  function _try(zone) {
    try {
      const fmt = new Intl.DateTimeFormat('en-US', { timeZone: zone, weekday: 'short' });
      const v = dayMap[fmt.format(now)];
      return Number.isFinite(v) ? v : null;
    } catch (e) { return null; }
  }
  return _try(tz || 'America/New_York') ?? _try('America/New_York') ?? now.getUTCDay();
}
function _localDateStr(now, tz) {
  function _try(zone) {
    try {
      const parts = new Intl.DateTimeFormat('en-CA', {
        timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit'
      }).formatToParts(now);
      const y = parts.find(p => p.type === 'year').value;
      const m = parts.find(p => p.type === 'month').value;
      const d = parts.find(p => p.type === 'day').value;
      return y + '-' + m + '-' + d;
    } catch (e) { return null; }
  }
  return _try(tz || 'America/New_York') || _try('America/New_York') || now.toISOString().slice(0, 10);
}
// Back-compat aliases (in case anything still calls the old names)
const _etHourNow = (now) => _localHourNow(now, 'America/New_York');
const _etDowNow  = (now) => _localDowNow(now,  'America/New_York');
const _etDateStr = (now) => _localDateStr(now, 'America/New_York');

// 2026-05-28 — cron now fires every hour. This function decides which
// users get an email THIS hour based on their personal nudge / recap
// time preferences. Sprint users also get a daily progress recap email
// in addition to the morning nudge.
async function sendDailyMixedToAll(env, event) {
  if (!env.RESEND_API_KEY || !env.DIGEST_FROM) {
    console.log("[scheduled] RESEND_API_KEY or DIGEST_FROM missing — skipping");
    return { sent: 0, skipped: "missing-secrets" };
  }
  const now = (event && event.scheduledTime) ? new Date(event.scheduledTime) : new Date();
  const users = await readUsersList(env);
  let nudgeSent = 0, recapSent = 0, digestSent = 0, skipped = 0;
  for (const u of users) {
    if (!u || !u.slug || !u.email) continue;
    try {
      const profRaw = await env.RESUMES.get(uk(u.slug, 'skills_profile'));
      const prof = profRaw ? JSON.parse(profRaw) : {};
      // Per-user timezone (IANA). Default ET if missing/invalid. The
      // helpers below all gracefully fall back to ET on a bad tz string.
      const tz = (typeof prof.sprintTimezone === 'string' && prof.sprintTimezone) || 'America/New_York';
      const localHour = _localHourNow(now, tz);
      const localDow  = _localDowNow(now,  tz);
      const localDate = _localDateStr(now, tz);
      const sp = prof.sprintStart;
      let inSprint = false;
      if (sp) {
        const start = new Date(sp);
        const days = parseInt(prof.sprintDays || 10, 10);
        const dayN = Math.floor((now - start) / 86400000) + 1;
        if (dayN >= 1 && dayN <= days) inSprint = true;
      }
      if (inSprint) {
        // Days-of-week gate (user's local zone)
        const allowedDays = (Array.isArray(prof.sprintDaysOfWeek) && prof.sprintDaysOfWeek.length)
          ? prof.sprintDaysOfWeek.map(Number)
          : [1, 2, 3, 4, 5];
        if (!allowedDays.includes(localDow)) { skipped++; continue; }
        const snoozed = Array.isArray(prof.sprintSnoozedDays) ? prof.sprintSnoozedDays : [];
        if (snoozed.includes(localDate)) {
          console.log('[scheduled]', u.slug, 'snoozed for', localDate);
          skipped++; continue;
        }
        const nudgeHr = _hhmmHour(prof.sprintNudgeTime || '07:00');
        const recapHr = _hhmmHour(prof.sprintRecapTime || '19:00');
        if (localHour === nudgeHr) {
          const r = await sendSprintReminderForUser(env, u, prof);
          if (r && r.ok) nudgeSent++;
        } else if (localHour === recapHr) {
          const r = await sendSprintRecapForUser(env, u, prof);
          if (r && r.ok) recapSent++;
        } else {
          skipped++;
        }
      } else {
        // Non-sprint users get the daily digest in THEIR local 7am slot.
        if (localHour === 7) {
          const r = await sendDigestForUser(env, u);
          if (r && r.ok) digestSent++;
        }
      }
      // Week 5: monthly resume-health report (separate from sprint nudges)
      // Fires once per month at the user's local 9am on the 1st.
      try {
        const localDay = parseInt(localDate.slice(8, 10), 10);
        if (localDay === 1 && localHour === 9) {
          const lastSent = prof.lastMonthlyReportAt || '';
          if (lastSent.slice(0, 7) !== localDate.slice(0, 7)) {
            const r = await sendMonthlyHealthReport(env, u, prof);
            if (r && r.ok) {
              prof.lastMonthlyReportAt = new Date().toISOString();
              await env.RESUMES.put(uk(u.slug, 'skills_profile'), JSON.stringify(prof));
            }
          }
        }
      } catch (e) { console.error('[monthly-report]', u.slug, e && e.message); }
    } catch (e) {
      console.error("[scheduled]", u.slug, "failed:", e && e.message);
    }
  }
  console.log(`[scheduled] nudge=${nudgeSent} recap=${recapSent} digest=${digestSent} skipped=${skipped} of ${users.length}`);
  return { nudgeSent, recapSent, digestSent, skipped, total: users.length };
}

// PURE function — testable without env / fetch / KV. Takes already-fetched
// data, returns { subject, bodyHtml, ccList, meta }. Refactored 2026-05-28.
function buildSprintReminder({ slug, userName, profile, tracker, contacts, cards, now, ccEmail }) {
  // Defensive: cron should not call us without sprintStart, but a single bad
  // profile shouldn't crash the whole loop. Return a null-shaped result the
  // caller can detect.
  if (!profile || !profile.sprintStart) {
    return { subject: null, bodyHtml: null, ccList: [], meta: { skipped: 'no-sprint-start' } };
  }
  const start = new Date(profile.sprintStart);
  if (isNaN(start.getTime())) {
    return { subject: null, bodyHtml: null, ccList: [], meta: { skipped: 'invalid-sprint-start' } };
  }
  now = now || new Date();
  const sprintDays = parseInt(profile.sprintDays || 10, 10);
  const dailyQuota = parseInt(profile.sprintDailyQuota || 3, 10);
  const dayN = Math.floor((now - start) / 86400000) + 1;
  const quotaTotal = sprintDays * dailyQuota;

  // Tracker rollup over the sprint window
  let applied = 0, todayApplied = 0, yesterdayApplied = 0;
  const todayStr = now.toISOString().slice(0, 10);
  const yesterdayStr = new Date(now.getTime() - 86400000).toISOString().slice(0, 10);
  Object.values(tracker || {}).forEach(e => {
    if (!e || typeof e !== 'object') return;
    const st = (e.status || '').toLowerCase();
    if (!['applied','phone','onsite','offer','rejected'].includes(st)) return;
    const ts = e.appliedAt || e.updatedAt || '';
    if (!ts) return;
    const dt = new Date(ts);
    if (isNaN(dt.getTime()) || dt < start) return;
    applied++;
    const ds = dt.toISOString().slice(0, 10);
    if (ds === todayStr) todayApplied++;
    if (ds === yesterdayStr) yesterdayApplied++;
  });

  // Build contacts-by-company map (lowercased company name → count)
  const contactsByCo = {};
  (contacts || []).forEach(c => {
    const k = ((c && c.company) || '').toLowerCase().trim();
    if (!k) return;
    contactsByCo[k] = (contactsByCo[k] || 0) + 1;
  });

  // Filter + rank cards: warm-intro first, then score
  const picks = [];
  (cards || []).forEach(card => {
    const rec = tracker && tracker[card.fp];
    if (rec && rec.status && ['applied','phone','onsite','offer'].includes(rec.status)) return;
    const warmCount = contactsByCo[(card.company || '').toLowerCase()] || 0;
    picks.push({ ...card, warmCount });
  });
  picks.sort((a, b) => {
    const wa = a.warmCount > 0 ? 1 : 0;
    const wb = b.warmCount > 0 ? 1 : 0;
    if (wa !== wb) return wb - wa;
    return (b.score || 0) - (a.score || 0);
  });
  const top = picks.slice(0, dailyQuota);

  // Day-3-miss cc escalation
  const ccList = [];
  if (dayN >= 4 && yesterdayApplied === 0 && ccEmail) ccList.push(ccEmail);

  const pct = quotaTotal > 0 ? Math.min(100, Math.round((applied / quotaTotal) * 100)) : 0;
  const subject = `Day ${dayN} of ${sprintDays} · ${todayApplied}/${dailyQuota} today · ${applied}/${quotaTotal} total`;

  let listHtml = '';
  top.forEach(p => {
    const badge = p.warmCount > 0
      ? `<span style="background:#fbbf24;color:#78350f;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;margin-right:6px;">🤝 ${p.warmCount} contact${p.warmCount===1?'':'s'}</span>`
      : '';
    listHtml += `<li style="margin:10px 0;line-height:1.4;">${badge}<a href="${p.applyUrl}" style="color:#1817B5;font-weight:600;text-decoration:none;">${p.title}</a> · ${p.company} <span style="color:#666;">(${p.score})</span></li>`;
  });
  const firstName = (userName || slug).split(' ')[0];
  const endStr = new Date(start.getTime() + sprintDays*86400000).toISOString().slice(0,10);
  const bodyHtml = `<!doctype html><html><body style="font-family:Inter,system-ui,sans-serif;color:#222;max-width:600px;margin:0 auto;padding:24px;">
    <div style="background:linear-gradient(135deg,#0B0828,#1817B5);color:#fff;padding:20px;border-radius:12px;margin-bottom:20px;">
      <div style="font-size:18px;font-weight:700;letter-spacing:0.3px;">🎯 Sprint Day ${dayN} of ${sprintDays}</div>
      <div style="font-size:14px;margin-top:6px;opacity:0.92;">${applied} of ${quotaTotal} applications · ${pct}% to goal</div>
      <div style="margin-top:12px;height:6px;background:rgba(255,255,255,0.18);border-radius:4px;overflow:hidden;">
        <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,#7C7CF0,#A4A4FF);"></div>
      </div>
    </div>
    <p style="font-size:15px;">Hi ${firstName}, here are <b>${top.length} jobs</b> to apply to today. Warm-intro picks (where you have LinkedIn contacts) come first — those callbacks beat cold applies 5×.</p>
    <ol style="padding-left:18px;">${listHtml}</ol>
    <p style="font-size:13px;color:#666;margin-top:24px;">Mark them applied on your dashboard so tomorrow's email knows. <a href="https://getmemyjob.officebeatllc.com/${slug}.html" style="color:#1817B5;">Open dashboard →</a></p>
    <p style="font-size:11px;color:#888;margin-top:18px;">This is a sprint reminder, not a regular digest. Sprint ends ${endStr}.</p>
  </body></html>`;

  return { subject, bodyHtml, ccList, meta: { dayN, applied, todayApplied, yesterdayApplied, quotaTotal, pct, topCount: top.length } };
}

// Outer: fetches everything, calls pure builder, sends via Resend.
async function sendSprintReminderForUser(env, user, profile) {
  const slug = user.slug;
  const trackerRaw = await env.RESUMES.get(uk(slug, 'tracker'));
  const tracker = trackerRaw ? JSON.parse(trackerRaw) : {};
  const contactsRaw = await env.RESUMES.get(uk(slug, 'contacts'));
  const contacts = contactsRaw ? JSON.parse(contactsRaw) : [];
  let html = '';
  try {
    const r = await fetch(`https://getmemyjob.officebeatllc.com/${slug}.html`, { headers: { 'Accept':'text/html' } });
    if (r.ok) html = await r.text();
  } catch (e) {}
  // Parse cards out of the dashboard HTML
  const cardRx = /<div class="card"[^>]*data-fp="([^"]+)"[^>]*data-score="(\d+)"[^>]*>[\s\S]*?<div class="title"><a href="([^"]+)"[^>]*>([^<]+)<\/a>[\s\S]*?<span class="company">([^<]+)<\/span>/g;
  const cards = [];
  let m;
  while ((m = cardRx.exec(html)) !== null) {
    cards.push({ fp: m[1], score: parseInt(m[2], 10), applyUrl: m[3], title: (m[4]||'').trim(), company: (m[5]||'').trim() });
  }
  const { subject, bodyHtml, ccList, meta } = buildSprintReminder({
    slug, userName: user.name || slug, profile, tracker, contacts, cards,
    now: new Date(), ccEmail: env.SPRINT_CC_EMAIL || '',
  });
  if (!subject || !bodyHtml) {
    console.log(`[sprint-reminder] ${slug} skipped: ${meta && meta.skipped}`);
    return { ok: false, reason: meta && meta.skipped };
  }
  return await sendEmailViaResend(env, user.email, subject, bodyHtml, ccList);
}

// 2026-05-28 — end-of-day sprint recap email. Lighter than the morning
// reminder: just today's progress numbers and a link back to the dashboard.
async function sendSprintRecapForUser(env, user, profile) {
  const slug = user.slug;
  const trackerRaw = await env.RESUMES.get(uk(slug, 'tracker'));
  const tracker = trackerRaw ? JSON.parse(trackerRaw) : {};
  const now = new Date();
  const tz = (typeof profile.sprintTimezone === 'string' && profile.sprintTimezone) || 'America/New_York';
  const localDate = _localDateStr(now, tz);
  const dailyQuota = parseInt(profile.sprintDailyQuota || 3, 10);
  const sprintDays = parseInt(profile.sprintDays || 10, 10);
  const start = new Date(profile.sprintStart);
  const dayN = Math.floor((now - start) / 86400000) + 1;
  let appliedToday = 0, appliedTotal = 0, advancedTotal = 0;
  Object.values(tracker || {}).forEach(e => {
    if (!e) return;
    const st = String(e.status || '').toLowerCase();
    if (!['applied','phone','onsite','offer','rejected'].includes(st)) return;
    appliedTotal += 1;
    if (['phone','onsite','offer'].includes(st)) advancedTotal += 1;
    const when = (e.statusChangedAt || e.appliedAt || e.updatedAt || '');
    try {
      const d = new Date(when);
      const dStr = _localDateStr(d, tz);
      if (dStr === localDate) appliedToday += 1;
    } catch (_) {}
  });
  const quotaTotal = sprintDays * dailyQuota;
  const pct = quotaTotal ? Math.round(100 * appliedTotal / quotaTotal) : 0;
  const hitToday = appliedToday >= dailyQuota;
  const userName = (user.name || slug).split(/\s+/)[0];
  const subject = hitToday
    ? `🎯 Day ${dayN}/${sprintDays} done — ${appliedToday} apps today`
    : `Day ${dayN}/${sprintDays} — ${appliedToday}/${dailyQuota} applied today`;
  const dashUrl = `https://getmemyjob.officebeatllc.com/${slug}.html`;
  const bodyHtml = `<!doctype html><html><body style="font-family:Inter,system-ui,sans-serif;color:#1a1a2e;line-height:1.55;max-width:560px;margin:0 auto;padding:24px;">
    <h2 style="margin:0 0 4px;font-size:18px;">Hey ${escHtmlSafe(userName)},</h2>
    <p style="margin:0 0 18px;color:#555;font-size:14px;">Your sprint progress at end-of-day.</p>
    <table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:separate;border-spacing:8px 0;">
      <tr>
        ${_recapTile('Today', appliedToday + ' / ' + dailyQuota, hitToday ? '#0a6b3a' : '#5C5CD6')}
        ${_recapTile('Sprint total', appliedTotal + ' / ' + quotaTotal, '#5C5CD6')}
        ${_recapTile('Advanced', String(advancedTotal), '#0a6b3a')}
        ${_recapTile('% to goal', pct + '%', '#5C5CD6')}
      </tr>
    </table>
    <p style="margin:22px 0 6px;font-size:14px;">${
      hitToday
        ? `You hit today's quota of ${dailyQuota}. ${sprintDays - dayN > 0 ? `${sprintDays - dayN} day(s) left.` : 'Last day of sprint!'}`
        : `${dailyQuota - appliedToday} more to hit today's quota. You can still log late — open the dashboard before tomorrow's nudge.`
    }</p>
    <p style="margin:14px 0;font-size:13px;">
      <a href="${dashUrl}" style="background:#1817B5;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">Open dashboard</a>
    </p>
    <p style="margin:24px 0 0;font-size:11px;color:#888;">You're getting this because you started a 10-day sprint on getmemyjob. Change the recap time or end the sprint anytime from the dashboard.</p>
  </body></html>`;
  return await sendEmailViaResend(env, user.email, subject, bodyHtml, []);
}

// === Week 5: monthly resume-health report ============================
async function sendMonthlyHealthReport(env, user, profile) {
  const slug = user.slug;
  const tuningsRaw = await env.RESUMES.get(uk(slug, 'tunings'));
  const tunings = tuningsRaw ? JSON.parse(tuningsRaw) : [];
  const lastMonthCutoff = Date.now() - 30 * 86400000;
  const recent = tunings.filter(t => new Date(t.createdAt).getTime() >= lastMonthCutoff);
  const advanced = recent.filter(t => ['phonescreen','onsite','offer'].includes(String(t.outcome || '').toLowerCase()));
  const applied = recent.filter(t => t.outcome).length;
  const winRate = applied > 0 ? Math.round(100 * advanced.length / applied) : 0;
  const health = profile.resumeHealth || {};
  const hist = Array.isArray(profile.resumeHealthHistory) ? profile.resumeHealthHistory.slice(-2) : [];
  let delta = 0;
  if (hist.length === 2) delta = (hist[1].score || 0) - (hist[0].score || 0);
  const userName = (user.name || slug).split(/\s+/)[0];
  const arrow = delta > 0 ? '↑' : (delta < 0 ? '↓' : '→');
  const dColor = delta > 0 ? '#0a6b3a' : (delta < 0 ? '#B91C1C' : '#666');
  const dashUrl = `https://getmemyjob.officebeatllc.com/${slug}.html`;
  const subject = `Your resume + applications — monthly check-in (score ${health.score || '—'})`;
  const bodyHtml = `<!doctype html><html><body style="font-family:Inter,system-ui,sans-serif;color:#1a1a2e;line-height:1.55;max-width:600px;margin:0 auto;padding:24px;">
    <h2 style="margin:0 0 4px;font-size:18px;">Hi ${escHtmlSafe(userName)} —</h2>
    <p style="margin:0 0 18px;color:#555;font-size:14px;">Your monthly resume + applications snapshot.</p>
    <table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:separate;border-spacing:8px 0;margin-bottom:18px;">
      <tr>
        ${_recapTile('Resume score', String(health.score || '—'), '#5C5CD6')}
        ${_recapTile('Δ vs prior', arrow + ' ' + (delta >= 0 ? '+' : '') + delta, dColor)}
        ${_recapTile('Tuned apps (30d)', String(recent.length), '#5C5CD6')}
        ${_recapTile('Advanced', String(advanced.length) + ' (' + winRate + '%)', '#0a6b3a')}
      </tr>
    </table>
    <p style="margin:0 0 6px;font-size:14px;">${
      recent.length === 0
        ? 'No tuned applications in the last 30 days. The Prep Application kit can boost recruiter-keyword match — give it a try next time.'
        : (winRate >= 30
            ? 'Solid hit-rate. Keep using the keyword check + cover paragraph; they\'re carrying their weight.'
            : 'Your tuned applications converted at ' + winRate + '%. Open the dashboard\'s resume modal — \"Show me what to fix\" surfaces concrete bullet rewrites.')
    }</p>
    <p style="margin:14px 0;">
      <a href="${dashUrl}" style="background:#1817B5;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:600;display:inline-block;">Open dashboard</a>
    </p>
    <p style="margin:24px 0 0;font-size:11px;color:#888;">Monthly check-in from getmemyjob. Adjust nudge times in /account.html.</p>
  </body></html>`;
  return await sendEmailViaResend(env, user.email, subject, bodyHtml, []);
}

function _recapTile(label, val, color) {
  return `<td style="background:#f4f4ff;border:1px solid #e0e2ed;border-radius:8px;padding:12px;text-align:center;width:25%;">
    <div style="font-size:22px;font-weight:700;color:${color};">${val}</div>
    <div style="font-size:11px;color:#444;text-transform:uppercase;letter-spacing:0.04em;margin-top:3px;">${label}</div>
  </td>`;
}
function escHtmlSafe(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}


async function sendDailyDigestToAll(env) {
  if (!env.RESEND_API_KEY || !env.DIGEST_FROM) {
    console.log("[digest] RESEND_API_KEY or DIGEST_FROM missing — skipping");
    return { sent: 0, skipped: "missing-secrets" };
  }
  const users = await readUsersList(env);
  let sent = 0;
  for (const u of users) {
    if (!u || !u.slug || !u.email) continue;
    try {
      const result = await sendDigestForUser(env, u);
      if (result.ok) sent++;
    } catch (e) {
      console.error("[digest]", u.slug, "failed:", e && e.message);
    }
  }
  console.log(`[digest] sent ${sent} of ${users.length}`);
  return { sent, total: users.length };
}

async function sendDigestForUser(env, user) {
  // Pull skills_profile (for primaryRole), tracker (for status counts), and
  // the per-user HTML to extract top-5 unapplied picks.
  const slug = user.slug;
  const profileRaw = await env.RESUMES.get(uk(slug, "skills_profile"));
  const profile = profileRaw ? JSON.parse(profileRaw) : {};
  const trackerRaw = await env.RESUMES.get(uk(slug, "tracker"));
  const tracker = trackerRaw ? JSON.parse(trackerRaw) : {};
  const userName = user.name || slug;
  const dailyTarget = Math.max(1, Math.min(50, parseInt(profile.dailyTarget || "5", 10)));

  // Fetch the per-user HTML from getmemyjob.officebeatllc.com to extract top picks
  const url = `https://getmemyjob.officebeatllc.com/${slug}.html`;
  let html = "";
  try {
    const r = await fetch(url, { headers: { 'Accept': 'text/html' } });
    if (r.ok) html = await r.text();
  } catch (e) { /* swallow */ }
  if (!html) {
    console.log(`[digest] ${slug} — could not fetch dashboard`);
    return { ok: false, reason: "no-html" };
  }

  // Extract first N cards by score, skipping any whose fp is in tracker as applied/saved-today
  const today = new Date().toISOString().slice(0, 10);
  const cardRx = /<div class="card"[^>]*data-fp="([^"]+)"[^>]*data-score="(\d+)"[^>]*data-listed-days="(\d+)"[^>]*>[\s\S]*?<div class="title"><a href="([^"]+)"[^>]*>([^<]+)<\/a>[\s\S]*?<span class="company">([^<]+)<\/span>/g;
  const picks = [];
  let m;
  while ((m = cardRx.exec(html)) !== null) {
    const [, fp, score, days, applyUrl, title, company] = m;
    const rec = tracker[fp];
    if (rec && rec.status && rec.statusChangedAt) {
      const day = (rec.statusChangedAt || "").slice(0, 10);
      if (day === today || rec.status === "applied" || rec.status === "phonescreen" || rec.status === "onsite" || rec.status === "offer") continue;
    }
    picks.push({ fp, score: parseInt(score, 10), days: parseInt(days, 10), applyUrl, title: title.trim(), company: company.trim() });
    if (picks.length >= dailyTarget) break;
  }
  picks.sort((a, b) => b.score - a.score);

  if (!picks.length) {
    console.log(`[digest] ${slug} — no picks to send`);
    return { ok: false, reason: "no-picks" };
  }

  const subject = `🎯 ${dailyTarget} job picks for you today, ${userName.split(" ")[0]}`;
  const cards = picks.map((p, i) => `
    <tr>
      <td style="padding:10px 12px;border-bottom:1px solid #e5e5ea;vertical-align:top;">
        <div style="display:flex;align-items:start;gap:8px;">
          <span style="display:inline-block;min-width:24px;text-align:center;background:#5C5CD6;color:#fff;border-radius:4px;font-weight:700;font-size:11px;padding:2px 4px;line-height:1.6;">${i+1}</span>
          <div style="flex:1;">
            <a href="${p.applyUrl}" style="color:#22223b;text-decoration:none;font-weight:600;font-size:14.5px;">${esc(p.title)}</a>
            <div style="font-size:12.5px;color:#666;margin-top:2px;">${esc(p.company)} · ${p.days}d listed · score ${p.score}</div>
          </div>
          <a href="${p.applyUrl}" style="background:#5C5CD6;color:white;text-decoration:none;padding:6px 10px;border-radius:5px;font-size:12px;font-weight:600;white-space:nowrap;">Apply →</a>
        </div>
      </td>
    </tr>
  `).join("");

  const dashUrl = `https://getmemyjob.officebeatllc.com/${slug}.html`;
  const body = `<!doctype html><html><body style="font-family:-apple-system,sans-serif;background:#f4f5f8;padding:0;margin:0;">
    <div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;margin-top:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
      <div style="padding:20px 20px 12px;background:linear-gradient(135deg,#eef0ff 0%,#fef8e8 100%);">
        <div style="font-size:22px;font-weight:700;color:#22223b;">🎯 Your ${dailyTarget} picks for today</div>
        <div style="font-size:13px;color:#555;margin-top:4px;">Hand-picked from your getmemyjob feed — score-sorted, freshest first. Apply to all ${dailyTarget} = day's goal hit.</div>
      </div>
      <table style="width:100%;border-collapse:collapse;">${cards}</table>
      <div style="padding:14px 20px;background:#fafbfc;border-top:1px solid #e5e5ea;font-size:12.5px;color:#666;">
        <a href="${dashUrl}" style="color:#5C5CD6;font-weight:600;">Open full dashboard →</a> ·
        <span style="color:#999;">If a job won't open, browse the company's careers page from your dashboard for a working link.</span>
      </div>
    </div>
  </body></html>`;

  return await sendEmailViaResend(env, user.email, subject, body);

  function esc(s) {
    return String(s || "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  }
}

async function sendEmailViaResend(env, toEmail, subject, htmlBody, ccList) {
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: env.DIGEST_FROM,
      to: [toEmail],
      subject,
      html: htmlBody,
      cc: (Array.isArray(ccList) && ccList.length ? ccList : undefined),
    }),
  });
  if (!r.ok) {
    const err = await r.text().catch(() => "");
    return { ok: false, status: r.status, error: err.slice(0, 200) };
  }
  return { ok: true };
}

async function handleDigestTrigger(request, env, cors) {
  const url = new URL(request.url);
  const adminKey = request.headers.get("X-Admin-Key") || "";
  if (!env.ADMIN_KEY || adminKey !== env.ADMIN_KEY) {
    return Response.json({ error: "Unauthorized" }, { status: 401, headers: cors });
  }
  const slug = url.searchParams.get("user");
  if (slug && slug !== "all") {
    const users = await readUsersList(env);
    const user = users.find(u => u.slug === slug);
    if (!user) return Response.json({ error: "User not found" }, { status: 404, headers: cors });
    if (!user.email) return Response.json({ error: "User has no email" }, { status: 400, headers: cors });
    const result = await sendDigestForUser(env, user);
    return Response.json(result, { headers: cors });
  }
  const result = await sendDailyDigestToAll(env);
  return Response.json(result, { headers: cors });
}

// Named export for unit testing — Cloudflare ignores non-default exports at runtime.
export { buildSprintReminder };
