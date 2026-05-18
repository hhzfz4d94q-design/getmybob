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
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-Edit-Key, X-Admin-Key',
    };
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Key, X-Edit-Key, Authorization', 'Access-Control-Max-Age': '86400' } });

    // Admin endpoints (provision / list / delete users)
    if (url.pathname === '/admin/users') return handleAdminUsers(request, env, cors);
    // Public read-only user list (used by fetch_jobs.py to generate dashboards)
    if (url.pathname === '/users') return handlePublicUsers(request, env, cors);

    if (url.pathname === '/refresh') return handleRefresh(request, env, cors);

    // Determine which user this request operates on.
    // Priority: ?user=slug in URL → "user" field in JSON body → DEFAULT_USER
    const slug = await resolveSlug(request, url);

    if (url.pathname === '/resume') return handleResume(request, env, cors, slug);
    if (url.pathname === '/resume-versions') return handleVersions(request, env, cors, slug);
    if (url.pathname === '/parse-resume') return handleParseResume(request, env, cors, slug);
    if (url.pathname === '/skills-profile') return handleSkillsProfile(request, env, cors, slug);
    if (url.pathname === '/regenerate-profile') return handleRegenerateProfile(request, env, cors, slug);
    if (url.pathname === '/prep') return handlePrep(request, env, cors, slug);
    if (url.pathname === '/tracker') return handleTracker(request, env, cors, slug);
    if (url.pathname === '/draft-followup') return handleDraftFollowup(request, env, cors, slug);
    if (url.pathname === '/interview-prep') return handleInterviewPrep(request, env, cors, slug);
    if (url.pathname === '/generate-digest') return handleGenerateDigest(request, env, cors, slug);
    return new Response(
      'Endpoints: /prep, /resume, /resume-versions, /parse-resume, /skills-profile, /regenerate-profile, /tracker, /draft-followup, /interview-prep, /generate-digest, /refresh, /admin/users.',
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

  // Read the user's existing size preference (set via the wizard) so the
  // AI can bias targetCompanies toward sizes the user actually wants.
  let sizePrefs = ["startup", "midsize", "large"];
  let preservedPrefs = null;
  try {
    const existingRaw = await env.RESUMES.get(uk(slug, 'skills_profile'));
    if (existingRaw) {
      const existing = JSON.parse(existingRaw);
      if (Array.isArray(existing.companySizePreferences) && existing.companySizePreferences.length) {
        sizePrefs = existing.companySizePreferences;
        preservedPrefs = existing.companySizePreferences;
      }
    }
  } catch (e) { /* fall through with defaults */ }
  const sizeInstruction = sizePrefs.length < 3
    ? `IMPORTANT: this user has explicitly told us they only want jobs at ${sizePrefs.join(' / ')} companies. ALL of your targetCompanies suggestions must be ${sizePrefs.join(' or ')} employers — do NOT suggest any companies outside those sizes. Size definitions: startup = under 500 employees / typically Series A-C; midsize = 500-10k employees / established but not Fortune 500; large = 10k+ employees / Fortune 500 / public.`
    : `This user is open to all company sizes. Provide a balanced mix in targetCompanies: roughly 30% startups (<500 emp), 40% mid-size (500-10k), 30% large (10k+). Avoid suggesting only Fortune 500 brand-name employers — sample across stages.`;

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
- targetCompanies: array of 15-25 specific companies this person would realistically target next. ${sizeInstruction} Match seniority + industries + niche specialization. Prefer specialist firms over generic ones. Each entry: {name: string, atsHint: one of "greenhouse"|"lever"|"ashby"|"workday"|"unknown" (best guess at which ATS hosts their careers page), why: one-sentence reason this company fits}. For "workday" entries you MUST also include atsUrl: the full URL to their public Workday careers page (e.g., https://moodys.wd5.myworkdayjobs.com/Careers, https://jpmc.wd1.myworkdayjobs.com/jpmc). For other atsHint values, atsUrl is optional. If you don't know the exact Workday URL, set atsHint to "unknown" instead of guessing. For a structured-credit director, prefer Moody's/S&P Global/Fitch/KBRA/Pimco/Apollo/Ares rather than generic fintech companies. For cybersecurity GRC executives, prefer Vanta/Drata/OneTrust/Wiz/Snyk rather than generic SaaS. Use "workday" for large enterprises (banks, big pharma), "greenhouse"/"lever"/"ashby" for startups under ~$5B, "unknown" if uncertain.
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
    const profile = Object.assign({}, parsed, { resumeId: activeId, generatedAt: new Date().toISOString(), user: slug });
    // Preserve the user's wizard-set companySizePreferences across regen
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
      const SCALAR_FIELDS = new Set(['salaryFloor', 'remotePreferred', 'seniorityLevel', 'primaryRole', 'summary']);
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
async function handleRefresh(request, env, cors) {
  if (request.method !== 'POST') return new Response('POST only', { status: 405, headers: cors });
  if (!env.GH_REPO_TOKEN) return Response.json({ error: 'Worker missing GH_REPO_TOKEN secret' }, { status: 500, headers: cors });
  const r = await fetch(`https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/actions/workflows/${GH_WORKFLOW}/dispatches`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${env.GH_REPO_TOKEN}`,
      'Accept': 'application/vnd.github+json',
      'User-Agent': 'cool-darkness-dce5-worker',
    },
    body: JSON.stringify({ ref: 'main' }),
  });
  if (r.status === 204) return Response.json({ status: 'triggered' }, { headers: cors });
  const errText = await r.text();
  return Response.json({ error: 'GitHub API error', status: r.status, details: errText }, { status: 502, headers: cors });
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