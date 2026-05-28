"""Inline contextual help + scripted onboarding tour.

Stage 1: 12 '?' icons across the dashboard, each opens a small popover with
2-3 sentences of explanation. Pure HTML/CSS/JS injected via overlay so the
existing HTML_TEMPLATE doesn't need 12 surgical edits.

Stage 2: scripted onboarding tour for first-login users. Walks 7 hotspots
with a custom Shepherd.js-style overlay. Skippable + re-summonable from the
More menu. Stored in localStorage so it never re-fires after dismissal.

No LLM. No ongoing cost. Pure client-side.

Extracted from fetch_jobs.py 2026-05-28 (Phase 6, post-split).
"""

# Each entry: (selector or button-id, short title, body HTML).
# `selector` is the element the '?' icon attaches NEXT to (via JS).
# `body` can include inline <strong>, <em>, <a>, <br> — escaped by JS at render.
HELP_TOPICS = [
    {
        "id": "sprint-strip",
        "anchor": "#sprint-strip, #sprint-start-cta",
        "title": "What is sprint mode?",
        "body": "A 10-day focused push. Once started, your feed re-sorts by sprint priority (warm-intro picks first, then just-posted, then score). You get a daily 7am email with the 3 best matches for that day. Mark jobs applied so tomorrow's email knows.",
    },
    {
        "id": "top-picks",
        "anchor": "#focus-panel",
        "title": "How are today's targets chosen?",
        "body": "We pick the highest-fit unapplied jobs from your feed, capped at your daily target (default 5, configurable in Preferences). Marking one applied removes it; the next-best job slides in.",
    },
    {
        "id": "score-number",
        "anchor": ".card .ai-score, .card [data-score]",
        "title": "What does the score mean?",
        "body": "0-100 fit score. 50 = baseline. We add points for matching your industries (up to +25), title (up to +15), skills (up to +25), plus boosts for warm-intro company (+5), curated healthtech catalog (+3), recently-funded (+5), and just-posted (+10).",
    },
    {
        "id": "warm-intro",
        "anchor": ".contact-badge",
        "title": "What's a warm intro?",
        "body": "A LinkedIn connection at the hiring company. Warm intros get 5-10x the callback rate of cold applies. Click the badge to see who, then use the 'Warm intro' button on the card to draft an outreach message.",
    },
    {
        "id": "just-posted",
        "anchor": ".just-posted-badge",
        "title": "Why is this flagged just-posted?",
        "body": "Posted in the last 3 days. Fresh listings haven't been buried under 200 applicants yet — your callback odds are highest in the first week.",
    },
    {
        "id": "status-tracker",
        "anchor": ".btn.track",
        "title": "Application tracker status",
        "body": "Track each application's progress: Applied → Phone screen → Onsite → Offer. Click the button to cycle through. Status is saved to your account so it's the same across devices.",
    },
    {
        "id": "sort-by",
        "anchor": "#sortBy",
        "title": "Sort options",
        "body": "<strong>Sprint priority</strong> — warm-intro then just-posted then score (default in sprint mode).<br><strong>Best match</strong> — pure score.<br><strong>Most recent</strong> — newest first.<br><strong>Salary</strong> — high to low.",
    },
    {
        "id": "filters",
        "anchor": ".pill[data-window]",
        "title": "Time-window filters",
        "body": "Filter the feed by how recently jobs were posted. 'All' shows everything we have. 'Today' / 'Last 7 days' / 'Last 14 days' tightens to fresh listings — useful when you only want to apply to jobs unlikely to be ghost listings.",
    },
    {
        "id": "preferences",
        "anchor": "#preferences-btn, [onclick*='openPreferences']",
        "title": "Preferences",
        "body": "Tune the matcher: target industries, titles, keywords, salary floor, company size mix (startup/mid/large/consulting %), excluded companies, and signal-stability weights. Changes take effect on next refresh.",
    },
    {
        "id": "find-new",
        "anchor": "[onclick*='refreshDashboard']",
        "title": "Find new jobs",
        "body": "Triggers an out-of-band scrape across all 18 ATS sources (Greenhouse, Lever, Ashby, etc.). Takes 3-5 minutes. New listings appear on next page load.",
    },
    {
        "id": "resume",
        "anchor": "#resume-btn, [onclick*='openResumeModal']",
        "title": "Resume panel",
        "body": "Upload PDF or Word and the AI extracts your skills profile, target titles, and target companies. You can also edit the structured profile directly. Active resume is what the matcher uses.",
    },
    {
        "id": "contacts",
        "anchor": "#contacts-btn, [onclick*='openContactsModal']",
        "title": "LinkedIn Contacts",
        "body": "Upload your Connections.csv from LinkedIn's data export. Each connection becomes a warm-intro candidate — jobs at their companies get a contact badge AND a +5 score boost in sprint mode.",
    },
]


# Steps for the first-login tour. Each step anchors to a selector and points
# at it with a tooltip-style card.
TOUR_STEPS = [
    {
        "selector": "header",
        "title": "Welcome to getmemyjob",
        "body": "This is your tailored job feed — re-scored every 2 hours from 18 ATS sources. Quick tour: 6 steps, takes 30 seconds.",
        "position": "bottom",
    },
    {
        "selector": "#sprint-strip, #sprint-start-cta",
        "title": "Sprint mode",
        "body": "Click here to start a 10-day push. You'll get a daily 7am email with the 3 best jobs to apply to. Most users start their sprint once they're ready to focus.",
        "position": "bottom",
    },
    {
        "selector": "#focus-panel",
        "title": "Today's targets",
        "body": "Your highest-fit unapplied jobs, pinned at the top. Done one? Mark it applied — the next-best job slides in.",
        "position": "bottom",
    },
    {
        "selector": ".contact-badge, #grid",
        "title": "Warm-intro badges",
        "body": "Jobs at companies where you have a LinkedIn contact get this badge. These get 5-10x the callback rate. Always prioritize them.",
        "position": "right",
    },
    {
        "selector": "#sortBy",
        "title": "Sort + filter",
        "body": "Default sort puts warm-intro first. Change to 'Most recent' or 'Salary' anytime. Time filters cut out anything older than your chosen window.",
        "position": "bottom",
    },
    {
        "selector": "#preferences-btn, [onclick*='openPreferences']",
        "title": "Preferences",
        "body": "Anything not matching well? Tune target titles, industries, salary floor, and company size mix here. Changes take effect on next refresh (~5 min).",
        "position": "bottom",
    },
    {
        "selector": ".header-more-wrap, .header-more-menu",
        "title": "More menu",
        "body": "Find this tour, the resume editor, contacts upload, and 'Why isn't X in my feed?' debugger here. You're done — start applying!",
        "position": "left",
    },
]


def render_help_overlay():
    """Return the full <style> + <div> + <script> block to inject at end of dashboard HTML.

    Self-contained: pure HTML/CSS/JS, no external dependencies. Inserts the
    '?' icons next to anchored elements + wires the popover system + boots
    the first-login tour.
    """
    import json
    topics_json = json.dumps(HELP_TOPICS)
    tour_json = json.dumps(TOUR_STEPS)
    return r'''
<!-- ===================== HELP + ONBOARDING (Stage 1+2) ===================== -->
<style>
  .gmj-help-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 16px; height: 16px; border-radius: 50%;
    background: #eef0ff; color: #5C5CD6;
    font-size: 11px; font-weight: 700; cursor: pointer;
    margin-left: 6px; vertical-align: middle; flex-shrink: 0;
    border: 1px solid #c8cde6; line-height: 1;
    transition: background 0.15s, transform 0.15s;
    user-select: none;
  }
  .gmj-help-icon:hover { background: #5C5CD6; color: #fff; transform: scale(1.1); }
  .gmj-help-popover {
    position: absolute; z-index: 99998;
    max-width: 320px; padding: 14px 16px;
    background: #fff; color: #222;
    border: 1px solid #d0d4dc; border-radius: 10px;
    box-shadow: 0 6px 20px rgba(11, 8, 40, 0.18);
    font-family: Inter, system-ui, sans-serif; font-size: 13px;
    line-height: 1.5;
    opacity: 0; transform: translateY(-4px);
    pointer-events: none; transition: opacity 0.15s, transform 0.15s;
  }
  .gmj-help-popover.show { opacity: 1; transform: translateY(0); pointer-events: auto; }
  .gmj-help-popover .gmj-help-title { font-weight: 700; font-size: 13.5px; color: #1817B5; margin-bottom: 6px; }
  .gmj-help-popover .gmj-help-body { color: #444; }
  .gmj-help-popover .gmj-help-body strong { color: #1817B5; }
  .gmj-help-popover .gmj-help-close {
    position: absolute; top: 6px; right: 8px;
    background: none; border: none; cursor: pointer;
    font-size: 18px; line-height: 1; color: #999; padding: 2px 6px;
  }
  .gmj-help-popover .gmj-help-close:hover { color: #1817B5; }

  /* Tour overlay */
  .gmj-tour-backdrop {
    position: fixed; inset: 0; z-index: 99996;
    background: rgba(11, 8, 40, 0.55);
    opacity: 0; transition: opacity 0.3s;
  }
  .gmj-tour-backdrop.show { opacity: 1; }
  .gmj-tour-spot {
    position: absolute; z-index: 99997;
    border: 3px solid #FFD580; border-radius: 8px;
    box-shadow: 0 0 0 4px rgba(255, 213, 128, 0.35), 0 0 0 9999px rgba(11, 8, 40, 0.55);
    pointer-events: none;
    transition: top 0.35s, left 0.35s, width 0.35s, height 0.35s;
  }
  .gmj-tour-card {
    position: absolute; z-index: 99999;
    max-width: 360px; padding: 18px 20px;
    background: #fff; color: #222;
    border-radius: 14px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    font-family: Inter, system-ui, sans-serif;
    transition: top 0.35s, left 0.35s, opacity 0.2s;
  }
  .gmj-tour-card .gmj-tour-step { font-size: 11px; letter-spacing: 1px; text-transform: uppercase; color: #5C5CD6; font-weight: 700; margin-bottom: 6px; }
  .gmj-tour-card .gmj-tour-title { font-size: 17px; font-weight: 700; color: #1817B5; margin-bottom: 8px; }
  .gmj-tour-card .gmj-tour-body { font-size: 14px; line-height: 1.5; color: #333; margin-bottom: 14px; }
  .gmj-tour-card .gmj-tour-actions { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
  .gmj-tour-card .gmj-tour-back, .gmj-tour-card .gmj-tour-skip {
    background: none; border: none; color: #777; cursor: pointer;
    font-size: 13px; padding: 6px 10px;
  }
  .gmj-tour-card .gmj-tour-back:hover, .gmj-tour-card .gmj-tour-skip:hover { color: #1817B5; }
  .gmj-tour-card .gmj-tour-next {
    background: linear-gradient(135deg, #1817B5, #7C7CF0);
    color: #fff; border: none; padding: 9px 18px;
    border-radius: 8px; font-weight: 700; font-size: 13.5px;
    cursor: pointer; box-shadow: 0 3px 10px rgba(124, 124, 240, 0.4);
  }
  .gmj-tour-card .gmj-tour-next:hover { transform: translateY(-1px); }
</style>

<script>
(function() {
  var TOPICS = ''' + topics_json + r''';
  var TOUR = ''' + tour_json + r''';
  var TOUR_DONE_KEY = 'gmj_tour_completed_v1';

  // ---------- Stage 1: help icons + popover ----------
  function attachIcons() {
    TOPICS.forEach(function(t) {
      // Find first matching anchor for this topic
      var anchor = null;
      var sels = t.anchor.split(',').map(function(s){return s.trim();});
      for (var i = 0; i < sels.length; i++) {
        var el = document.querySelector(sels[i]);
        if (el) { anchor = el; break; }
      }
      if (!anchor) return;
      // Don't double-attach
      if (anchor.dataset.helpAttached === '1') return;
      anchor.dataset.helpAttached = '1';
      // Build icon
      var icon = document.createElement('span');
      icon.className = 'gmj-help-icon';
      icon.textContent = '?';
      icon.setAttribute('title', t.title);
      icon.setAttribute('data-help-id', t.id);
      icon.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        showPopover(t, icon);
      });
      // Insert next to anchor — prefer "after the heading text" if anchor is a header,
      // otherwise just append to parent
      if (anchor.tagName === 'H1' || anchor.tagName === 'H2' || anchor.tagName === 'H3' ||
          anchor.tagName === 'BUTTON' || anchor.tagName === 'SELECT') {
        anchor.parentNode.insertBefore(icon, anchor.nextSibling);
      } else {
        // For badges / structural elements, insert AFTER the first heading inside, else after element
        var hdr = anchor.querySelector('h1, h2, h3, h4, .label');
        if (hdr) { hdr.appendChild(icon); }
        else { anchor.parentNode.insertBefore(icon, anchor.nextSibling); }
      }
    });
  }

  var _activePop = null;
  function showPopover(topic, iconEl) {
    closePopover();
    var pop = document.createElement('div');
    pop.className = 'gmj-help-popover';
    pop.innerHTML =
      '<button class="gmj-help-close" aria-label="Close">&times;</button>' +
      '<div class="gmj-help-title">' + escapeHtml(topic.title) + '</div>' +
      '<div class="gmj-help-body">' + topic.body + '</div>';
    document.body.appendChild(pop);
    // Position to the right of the icon, or below if no space
    var rect = iconEl.getBoundingClientRect();
    var scrollY = window.scrollY || document.documentElement.scrollTop;
    var scrollX = window.scrollX || document.documentElement.scrollLeft;
    var popRect = pop.getBoundingClientRect();
    var top = rect.top + scrollY + 24;
    var left = rect.left + scrollX - 100;
    if (left + popRect.width > window.innerWidth - 10) {
      left = window.innerWidth - popRect.width - 10;
    }
    if (left < 10) left = 10;
    pop.style.top = top + 'px';
    pop.style.left = left + 'px';
    requestAnimationFrame(function() { pop.classList.add('show'); });
    pop.querySelector('.gmj-help-close').addEventListener('click', closePopover);
    _activePop = pop;
    setTimeout(function() {
      document.addEventListener('click', _outsideClick, { once: true });
    }, 50);
  }
  function _outsideClick(e) {
    if (_activePop && !_activePop.contains(e.target)) closePopover();
  }
  function closePopover() {
    if (_activePop) {
      _activePop.classList.remove('show');
      var p = _activePop;
      setTimeout(function() { if (p && p.parentNode) p.parentNode.removeChild(p); }, 200);
      _activePop = null;
    }
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function(c) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  }

  // ---------- Stage 2: scripted onboarding tour ----------
  var _tourState = { idx: 0, backdrop: null, spot: null, card: null };

  function startTour(forceStart) {
    if (!forceStart && localStorage.getItem(TOUR_DONE_KEY)) return;
    closePopover();
    _tourState.idx = 0;
    _tourState.backdrop = document.createElement('div');
    _tourState.backdrop.className = 'gmj-tour-backdrop';
    document.body.appendChild(_tourState.backdrop);
    requestAnimationFrame(function() { _tourState.backdrop.classList.add('show'); });
    showTourStep(0);
  }

  function showTourStep(idx) {
    if (idx < 0 || idx >= TOUR.length) { endTour(true); return; }
    _tourState.idx = idx;
    var step = TOUR[idx];
    // Find anchor
    var anchor = null;
    var sels = step.selector.split(',').map(function(s){return s.trim();});
    for (var i = 0; i < sels.length; i++) {
      var el = document.querySelector(sels[i]);
      if (el && el.offsetParent !== null) { anchor = el; break; }
    }
    if (!anchor) { showTourStep(idx + 1); return; } // skip missing anchors
    anchor.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(function() {
      var rect = anchor.getBoundingClientRect();
      var scrollY = window.scrollY || document.documentElement.scrollTop;
      var scrollX = window.scrollX || document.documentElement.scrollLeft;
      // Spotlight
      if (!_tourState.spot) {
        _tourState.spot = document.createElement('div');
        _tourState.spot.className = 'gmj-tour-spot';
        document.body.appendChild(_tourState.spot);
      }
      _tourState.spot.style.top = (rect.top + scrollY - 6) + 'px';
      _tourState.spot.style.left = (rect.left + scrollX - 6) + 'px';
      _tourState.spot.style.width = (rect.width + 12) + 'px';
      _tourState.spot.style.height = (rect.height + 12) + 'px';
      // Card
      if (!_tourState.card) {
        _tourState.card = document.createElement('div');
        _tourState.card.className = 'gmj-tour-card';
        document.body.appendChild(_tourState.card);
      }
      _tourState.card.innerHTML =
        '<div class="gmj-tour-step">Step ' + (idx + 1) + ' of ' + TOUR.length + '</div>' +
        '<div class="gmj-tour-title">' + escapeHtml(step.title) + '</div>' +
        '<div class="gmj-tour-body">' + step.body + '</div>' +
        '<div class="gmj-tour-actions">' +
          (idx > 0 ? '<button class="gmj-tour-back">&larr; Back</button>' : '<span></span>') +
          '<button class="gmj-tour-skip">Skip tour</button>' +
          '<button class="gmj-tour-next">' + (idx === TOUR.length - 1 ? 'Done' : 'Next →') + '</button>' +
        '</div>';
      // Position card — below the spotlight if there's room, else above
      var cardTop = rect.bottom + scrollY + 16;
      var cardLeft = Math.max(20, Math.min(rect.left + scrollX - 20, window.innerWidth - 380));
      if (cardTop + 200 > window.innerHeight + scrollY) {
        cardTop = Math.max(scrollY + 20, rect.top + scrollY - 220);
      }
      _tourState.card.style.top = cardTop + 'px';
      _tourState.card.style.left = cardLeft + 'px';
      // Wire actions
      var nextBtn = _tourState.card.querySelector('.gmj-tour-next');
      var backBtn = _tourState.card.querySelector('.gmj-tour-back');
      var skipBtn = _tourState.card.querySelector('.gmj-tour-skip');
      nextBtn.addEventListener('click', function() { showTourStep(idx + 1); });
      if (backBtn) backBtn.addEventListener('click', function() { showTourStep(idx - 1); });
      skipBtn.addEventListener('click', function() { endTour(false); });
    }, 300);
  }

  function endTour(completed) {
    if (completed) localStorage.setItem(TOUR_DONE_KEY, new Date().toISOString());
    if (_tourState.spot) { _tourState.spot.remove(); _tourState.spot = null; }
    if (_tourState.card) { _tourState.card.remove(); _tourState.card = null; }
    if (_tourState.backdrop) {
      _tourState.backdrop.classList.remove('show');
      var b = _tourState.backdrop;
      setTimeout(function() { if (b && b.parentNode) b.parentNode.removeChild(b); }, 300);
      _tourState.backdrop = null;
    }
  }

  // ---------- Public API ----------
  window.gmjStartTour = function() { startTour(true); };  // re-summonable from More menu

  // ---------- Boot ----------
  function boot() {
    attachIcons();
    // Re-attach when dynamic content (cards, modals) gets added
    if (window.MutationObserver) {
      var obs = new MutationObserver(function() {
        // Throttle — only re-run every 500ms max
        if (boot._t) return;
        boot._t = setTimeout(function() { boot._t = null; attachIcons(); }, 500);
      });
      obs.observe(document.body, { childList: true, subtree: true });
    }
    // Auto-start tour for first-login users (300ms after load so dashboard renders)
    setTimeout(function() { startTour(false); }, 1200);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
</script>
'''
