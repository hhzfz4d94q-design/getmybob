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
  async scheduled(event, env, ctx) {
    try {
      await sendDailyDigestToAll(env);
    } catch (e) {
      console.error("[digest] scheduled failed:", e && e.message ? e.message : e);
    }
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-Edit-Key, X-Admin-Key, Authorization',
    };
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Key, X-Edit-Key, Authorization', 'Access-Control-Max-Age': '86400' } });

    // Admin endpoints (provision / list / delete users)
    if (url.pathname === '/admin/users') return handleAdminUsers(request, env, cors);
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
    if (url.pathname === '/api/auth/capacity') return handleCapacity(request, env, cors);
    if (url.pathname === '/api/auth/admin-login') return handleAdminLogin(request, env, cors);
    if (url.pathname === '/api/auth/admin-change-password') return handleAdminChangePassword(request, env, cors);

    // Determine which user this request operates on.
    // Priority: ?user=slug in URL → "user" field in JSON body → DEFAULT_USER
    const slug = await resolveSlug(request, url);

    if (url.pathname === '/resume') return handleResume(request, env, cors, slug);
    if (url.pathname === '/resume-versions') return handleVersions(request, env, cors, slug);
    if (url.pathname === '/parse-resume') return handleParseResume(request, env, cors, slug);
    if (url.pathname === '/skills-profile') return handleSkillsProfile(request, env, cors, slug);
    if (url.pathname === '/regenerate-profile') return handleRegenerateProfile(request, env, cors, slug);
    if (url.pathname === '/rerank-titles') return handleRerankTitles(request, env, cors, slug);
    if (url.pathname === '/prep') return handlePrep(request, env, cors, slug);
    if (url.pathname === '/tracker') return handleTracker(request, env, cors, slug);
    if (url.pathname === '/draft-followup') return handleDraftFollowup(request, env, cors, slug);
    if (url.pathname === '/interview-prep') return handleInterviewPrep(request, env, cors, slug);
    if (url.pathname === '/generate-digest') return handleGenerateDigest(request, env, cors, slug);
    if (url.pathname === '/admin/digest-trigger') return handleDigestTrigger(request, env, cors);
    if (url.pathname === '/notes') return handleNotes(request, env, cors, slug);
    return new Response(
      'Endpoints: /api/auth/{signup,login,logout,me,change-password}, /prep, /resume, /resume-versions, /parse-resume, /skills-profile, /regenerate-profile, /rerank-titles, /tracker, /draft-followup, /interview-prep, /generate-digest, /refresh, /admin/users, /notes.',
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

  const prompt = `Analyze this resume EXHAUSTIVELY and produce a comprehensive structured skills profile.

CRITICAL: Be thorough, not sparse. Extract EVERY meaningful signal from the resume. If the resume mentions 20 technologies, include 20. If it spans 5 industries, include 5. Better to over-include than to miss things.

INFERENCE RULES — also INCLUDE industry-standard items even when not literally typed in the resume:

  - If the resume describes "GRC", "governance risk and compliance", "third-party risk", or audit/risk work at US financial institutions → INCLUDE the standard frameworks for that lane: nist csf, nist 800-53, iso 27001, iso 27002, soc 2, coso, cobit, ffiec, occ heightened standards, sox itgc, pci dss. INCLUDE the standard regulations: sox, glba, bsa, aml, kyc, dodd-frank, ny dfs part 500, sec cyber disclosure rule.

  - If the resume mentions banking, payments, or cards → also include relevant ones: pci dss, swift csp, bsa, aml.

  - If the resume mentions healthcare or health systems → also include: hipaa security rule, hipaa privacy rule, hitech, hitrust, fda qsr, 21 cfr part 11 (if devices/clinical).

  - If the resume mentions cloud, SaaS, or enterprise tech → also include: soc 2, iso 27001, csa ccm, fedramp (if government-adjacent), nist 800-53.

  - If the resume mentions trading, capital markets, or asset management → also include: mifid ii, frtb, sec cyber disclosure rule.

  - If the resume mentions program management / PMO → include: pmi pmbok, prince2 (if european), agile, scrum, safe.

  These are inferences based on what a senior practitioner in that domain would universally know and have touched. Be reasonable — do not include irrelevant ones. If a resume is purely healthcare, do not add banking-specific items.

CRITICAL: Be thorough but not sloppy. The user's profession determines what frameworks/regulations they'd know. A senior GRC leader at a US bank would unquestionably know NIST CSF, COSO, SOX ITGC, FFIEC even if they don't list them by name on their resume.

Return ONLY a JSON object with this exact shape (no prose, no code fences):

{
  "primaryRole": "one-line description of the role this person targets",
  "summary": "2-3 sentence summary of their professional background and what they bring",
  "seniorityLevel": "one of: junior | mid | senior | principal | director | vp | c-suite",
  "careerStage": "one of: internship | new-grad | early-career | mid-career | senior | executive",
  "seniorityTitles": ["..."],
  "targetTitles": ["..."],
  "industries": ["..."],
  "specialties": ["..."],
  "keywords": ["..."],
  "technologies": ["..."],
  "frameworks": ["..."],
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

- targetTitles (10-20): SPECIFIC titles this person could fill. Be concrete and varied. e.g. for a banking-tech leader: ["chief technology officer", "head of digital", "vp transformation", "director of risk", "head of grc", "vp engineering", "chief operating officer", "head of strategy"]. INCLUDE adjacent senior roles they could pivot into.

- industries (8-15): broad sectors where their resume directly applies. e.g. ["banking", "fintech", "capital markets", "wealth management", "credit risk", "cybersecurity", "insurance", "consulting", "saas"].

- specialties (10-25): granular sub-domains and functional areas they have hands-on depth in. e.g. ["investment banking", "anti-money-laundering", "credit risk modeling", "regulatory reporting", "digital transformation", "vendor management", "m&a integration", "operational risk", "treasury", "trade finance", "market risk"]. EXTRACT these from the actual bullets in the resume.

- keywords (25-40): high-signal terms from THIS resume that should BOOST a job's score when present in its title or description. Mix of: domain words, methodologies (agile, scrum, lean), outcome areas (cost reduction, revenue growth), and concepts (digital strategy, automation). NO generic words like "team" or "leadership" alone.

- technologies (10-25 if present in resume): specific tools, platforms, products, languages, vendors, or systems mentioned. e.g. ["salesforce", "aws", "azure", "oracle erp", "sap", "tableau", "snowflake", "moody's analytics", "calypso", "murex", "actimize", "fico", "sas", "servicenow", "splunk", "qualys", "okta"]. Include vendor names. If resume doesn't mention specific tools, return empty array.

- frameworks (any present, be EXHAUSTIVE — DO NOT miss these. SCAN THE ENTIRE RESUME including bullet points): standards, control frameworks, methodologies, and best-practice frameworks. Be liberal. Include cybersecurity, privacy, IT-governance, risk, audit, and delivery methodology frameworks. Look for these (include any you find):

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

- negativeKeywords (10-20): job types this person should NOT see — junior roles, adjacent-but-wrong roles, fields they've moved away from. e.g. ["junior", "intern", "associate", "entry level", "individual contributor", "field sales", "sdr"].

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
    for (const k of ['seniorityTitles','targetTitles','industries','specialties','keywords','technologies','frameworks','regulations','certifications','negativeKeywords']) {
      if (!Array.isArray(parsed[k])) parsed[k] = [];
      else parsed[k] = parsed[k].filter(x => typeof x === 'string').map(x => x.toLowerCase().trim()).filter(Boolean);
    }
    // Deterministic augmentation: add standard frameworks/regulations based on profile signals.
    // This ensures a banking-GRC profile always gets NIST CSF, COSO, FFIEC etc. even if the AI omits them.
    augmentProfileWithStandards(parsed);
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
    if (!(await checkEditKey(request, env, slug))) return Response.json({ error: 'Invalid X-Edit-Key' }, { status: 401, headers: cors });
    const body = await request.json().catch(() => ({}));
    // Patch mode: merge user-supplied additions into the existing profile (manual edits)
    if (body && body.patchFields && typeof body.patchFields === 'object') {
      const raw = await env.RESUMES.get(uk(slug, 'skills_profile'));
      const existing = raw ? JSON.parse(raw) : {};
      const updated = Object.assign({}, existing);
      const SCALAR_FIELDS = new Set(['salaryFloor', 'remotePreferred', 'seniorityLevel', 'careerStage', 'primaryRole', 'summary', 'companySizeMix', 'companySizePreferences', 'dailyTarget', 'recencyWindow', 'defaultSort', 'hideNoSalary', 'negativeTitles', 'matchWeights', 'phone', 'email', 'location', 'linkedinUrl', 'githubUrl', 'websiteUrl', 'workAuthorization', 'requiresSponsorship', 'currentCompany', 'currentTitle', 'school', 'degree', 'graduationYear', 'firstName', 'lastName']);
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

  const prompt = `You are helping ${candidateName || 'a candidate'} apply for a healthcare/tech job. Based on the resume below, produce four outputs:

1. A tailored 3-sentence resume summary highlighting why they're a strong fit.
2. A 250-word cover letter, professional but warm.
3. A 100-word LinkedIn intro message to a recruiter or hiring manager at this company.
4. A FULL TAILORED RESUME for this specific job — structured JSON. Re-order skills and re-emphasize/re-word existing bullets to lead with what's most relevant for THIS role. Do NOT invent claims.

Return your response as a JSON object with EXACTLY these keys and nothing else:
- "summary" (string)
- "coverLetter" (string)
- "linkedin" (string)
- "tailoredResume" (object with keys: personal, summary, skills, experience, education, certifications — same shape as the input resume)

For tailoredResume:
- personal: copy from input as-is
- summary: rewrite for THIS job, 3-4 sentences
- skills: re-order so most relevant 8-12 come first; drop the least relevant
- experience: keep same companies/titles/dates; re-order/rewrite bullets to emphasize relevance. 3-5 strongest bullets per role for THIS job.
- education / certifications: copy as-is

Only re-emphasize what's already in the resume. Never fabricate.

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
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 6000, messages: [{ role: 'user', content: prompt }] }),
    });
    if (!r.ok) { const err = await r.text(); return Response.json({ error: 'Anthropic API error', details: err }, { status: 502, headers: cors }); }
    const data = await r.json();
    const text = data.content?.[0]?.text || '';
    const cleaned = text.replace(/^```json\s*/i, '').replace(/^```\s*/, '').replace(/\s*```$/, '').trim();
    let parsed;
    try { parsed = JSON.parse(cleaned); }
    catch (e) { return Response.json({ summary: text, coverLetter: '', linkedin: '', tailoredResume: null, warning: 'AI did not return valid JSON' }, { headers: cors }); }
    return Response.json(parsed, { headers: cors });
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

// --- /admin/users — full CRUD ------------------------------------------
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
      enriched.push({
        ...u,
        hasResume: !!activeId,
        hasProfile: !!profile,
        editKey: editKey || '',
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
    // Coerce values to ints 0..100
    const out = {};
    for (const [k, v] of Object.entries(scores || {})) {
      const n = Math.max(0, Math.min(100, parseInt(v, 10) || 0));
      out[k] = n;
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

async function sendEmailViaResend(env, toEmail, subject, htmlBody) {
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

