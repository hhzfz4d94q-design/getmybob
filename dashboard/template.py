"""Per-user dashboard HTML template.

Extracted from fetch_jobs.py 2026-05-28 (Phase 3). Used via .format() with
the kwargs assembled by generate_dashboard. Pure constant.
"""

HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Jobs for {user_name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta name="theme-color" content="#5C5CD6">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
<link rel="icon" type="image/png" sizes="256x256" href="favicon.png">
<link rel="apple-touch-icon" href="favicon.png">
<meta name="description" content="A curated, AI-matched job feed for senior leadership roles — by OfficeBeat LLC.">
<meta property="og:type" content="website">
<meta property="og:title" content="getmemyjob — your tailored job feed">
<meta property="og:description" content="Real openings from real companies, AI-matched to your skills. By OfficeBeat LLC.">
<meta property="og:image" content="https://getmemyjob.officebeatllc.com/og-card.png">
<meta property="og:site_name" content="getmemyjob">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://getmemyjob.officebeatllc.com/og-card.png">
<style>
  body {{ font: 14px -apple-system, system-ui, sans-serif; margin: 0; background: #f7f7f8; color: #222; }}
  header {{ background: #5C5CD6; color: white; padding: 18px 28px; position: relative; }}
  header h1 {{ margin: 0; font-size: 20px; }}
  header .sub {{ opacity: .85; font-size: 13px; margin-top: 4px; max-width: calc(100% - 360px); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .header-actions {{ position: absolute; right: 28px; top: 50%; transform: translateY(-50%); display: flex; gap: 8px; }}
  .header-btn {{ background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: white; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; }}
  .header-btn:hover {{ background: rgba(255,255,255,0.25); }}
  .header-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
  /* "More" dropdown menu in header */
  .header-more-wrap {{ position: relative; display: inline-block; }}
  .header-more-menu {{
    display: none; position: absolute; right: 0; top: calc(100% + 8px);
    min-width: 260px; background: white; border: 1px solid #E5E5F0; border-radius: 12px;
    box-shadow: 0 16px 40px rgba(11,8,40,0.14), 0 4px 12px rgba(11,8,40,0.06);
    z-index: 1000; overflow: hidden; padding: 6px 0;
    animation: hmFade .14s ease-out;
  }}
  @keyframes hmFade {{ from {{ opacity:0; transform:translateY(-4px); }} to {{ opacity:1; transform:none; }} }}
  .header-more-wrap.open .header-more-menu {{ display: flex; flex-direction: column; }}
  .header-more-menu .hm-group {{
    padding: 8px 14px 4px; font-size: 10.5px; font-weight: 700; color: #8A86A6;
    text-transform: uppercase; letter-spacing: .08em;
  }}
  .header-more-menu .hm-group:not(:first-child) {{
    border-top: 1px solid #F0F0F7; margin-top: 4px; padding-top: 10px;
  }}
  .header-more-menu .hm-hint {{ color: #8A86A6; font-weight: 400; font-size: 11.5px; margin-left: 2px; }}
  .header-more-menu a, .header-more-menu button {{
    padding: 9px 14px; color: #0B0828 !important; background: transparent; border: none;
    text-align: left; font-size: 13.5px; font-weight: 500; cursor: pointer;
    text-decoration: none; font-family: inherit;
    width: 100%; display: block; transition: background .12s;
  }}
  .header-more-menu a:hover, .header-more-menu button:hover {{ background: #F6F6FB; }}
  .header-more-menu a:active, .header-more-menu button:active {{ background: #EEEEF8; }}
  .repost-badge {{ display: inline-block; padding: 1px 6px; background: #FEF3C7; color: #78350F; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .just-posted-badge {{ display: inline-block; padding: 1px 6px; background: #DCFCE7; color: #0A6B3A; border-radius: 4px; font-size: 11px; font-weight: 700; }}
  .stats {{ display: flex; gap: 24px; padding: 14px 28px; background: white; border-bottom: 1px solid #e5e5ea; }}
  .stat {{ font-size: 13px; }}
  .goal-stat {{ background: linear-gradient(135deg, #f8f4ff 0%, #eef0ff 100%) !important; }}
  .goal-stat b {{ color: #5C5CD6 !important; }}
  .stat b {{ font-size: 22px; display: block; color: #5C5CD6; }}
  /* Sprint config modal — prototype 2026-05-28 */
  .sc-section {{ margin-bottom: 16px; }}
  .sc-label {{ font-size: 12.5px; font-weight: 600; color: #1A1A2E; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.04em; }}
  .sc-pills {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .sc-pill {{ padding: 7px 14px; background: #fff; color: #5C5CD6; border: 1px solid #d0d4dc; border-radius: 16px; font-size: 13px; cursor: pointer; font-family: inherit; transition: all 0.1s; }}
  .sc-pill:hover {{ border-color: #5C5CD6; background: #fafbff; }}
  .sc-pill.active {{ background: #5C5CD6; color: #fff; border-color: #5C5CD6; font-weight: 600; }}
  .sc-pills.sc-days .sc-pill {{ padding: 6px 10px; min-width: 44px; text-align: center; font-size: 12px; }}
  .sc-hint {{ font-size: 11.5px; color: #888; margin-top: 6px; }}
  /* funnel-empty was referenced from JS but never had a CSS rule — repair */
  .funnel-empty {{ flex:1; background:#f7f8fb; border:1px dashed #d8dbe6; border-radius:8px; padding:10px 14px; color:#6b7280; font-size:13px; display:flex; align-items:center; justify-content:center; }}
  .filters {{ padding: 12px 28px; background: white; border-bottom: 1px solid #e5e5ea; display: flex; gap: 12px; }}
  .filters input, .filters select {{ padding: 6px 10px; font-size: 13px; border: 1px solid #ddd; border-radius: 6px; }}
  .grid {{ padding: 18px 28px; display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 14px; }}
  .card {{ background: white; border-radius: 10px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .row1 {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }}
  .title a {{ color: #5C5CD6; text-decoration: none; font-weight: 600; font-size: 15px; }}
  .title a:hover {{ text-decoration: underline; }}
  .score {{ background: #5C5CD6; color: white; border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 600; }}
  .row2 {{ font-size: 12px; color: #666; margin-top: 4px; }}
  .badges {{ margin: 8px 0; display: flex; flex-wrap: wrap; gap: 6px; }}
  .b {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; }}
  .b.senior {{ background: #e6f0ff; color: #5C5CD6; }}
  .b.remote {{ background: #e6fff0; color: #0a6b3a; }}
  .b.contract {{ background: #f3e6ff; color: #5a1f8a; }}
  .b.ghost {{ background: #fff1e6; color: #a85c00; }}
  .b.repost {{ background: #ffe6e6; color: #a80000; }}
  .b.fresh {{ background: #fffbe6; color: #8a6d00; font-weight: 600; }}
  .b.week {{ background: #f0e6ff; color: #4b2e9c; }}
  .pill {{ font-size: 12px; padding: 5px 12px; border-radius: 999px; border: 1px solid #ddd; background: white; cursor: pointer; }}
  .pill.active {{ background: #5C5CD6; color: white; border-color: #5C5CD6; }}
  .actions {{ margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }}
  .btn {{ font-size: 12px; padding: 6px 10px; border-radius: 6px; border: 1px solid #ddd; background: white; cursor: pointer; color: #333; text-decoration: none; display: inline-block; }}
  .btn:hover {{ background: #f0f0f0; }}
  .btn.primary {{ background: #5C5CD6; color: white; border-color: #5C5CD6; }}
  .btn.primary:hover {{ background: #4B4BBE; }}
  .btn.track.applied {{ background: #0a6b3a; color: white; border-color: #0a6b3a; }}
  .btn.track.phonescreen {{ background: #c97a00; color: white; border-color: #c97a00; }}
  .btn.track.onsite {{ background: #7a009c; color: white; border-color: #7a009c; }}
  .btn.track.offer {{ background: #ff7700; color: white; border-color: #ff7700; }}
  .btn.track.rejected {{ background: #888; color: white; border-color: #888; }}
  .b.applied {{ background: #d6f5e3; color: #0a6b3a; }}
  .b.phonescreen {{ background: #fce5b8; color: #6b4500; }}
  .b.onsite {{ background: #ead4ff; color: #4b2e9c; }}
  .b.offer {{ background: #ffd9b3; color: #a04500; }}
  .b.rejected {{ background: #e8e8e8; color: #666; }}
  .app-tracker {{ padding: 14px 28px; background: white; border-bottom: 1px solid #e5e5ea; }}
  .view-toggle {{ display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }}
  .view-toggle .pill {{ font-size: 13px; padding: 6px 14px; }}
  .view-label {{ font-size: 12px; color: #666; margin-right: 4px; font-weight: 600; }}
  .app-stats {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .app-stat {{ font-size: 12px; padding: 8px 14px; border-radius: 8px; min-width: 80px; }}
  .app-stat b {{ font-size: 20px; display: block; font-weight: 700; line-height: 1.15; }}
  .app-stat.applied {{ background: #d6f5e3; color: #0a6b3a; }}
  .app-stat.phonescreen {{ background: #fce5b8; color: #6b4500; }}
  .app-stat.onsite {{ background: #ead4ff; color: #4b2e9c; }}
  .app-stat.offer {{ background: #ffd9b3; color: #a04500; }}
  .app-stat.rejected {{ background: #e8e8e8; color: #666; }}
  .app-stat.response {{ background: #5C5CD6; color: white; }}
  body.apps-mode .card[data-status="offer"] {{ order: 1; }}
  body.apps-mode .card[data-status="onsite"] {{ order: 2; }}
  body.apps-mode .card[data-status="phonescreen"] {{ order: 3; }}
  body.apps-mode .card[data-status="applied"] {{ order: 4; }}
  body.apps-mode .card[data-status="rejected"] {{ order: 5; }}
  .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 2147483700; align-items: center; justify-content: center; padding: 20px; }}
  .modal-overlay.show {{ display: flex; }}
  .modal {{ background: white; border-radius: 12px; padding: 24px; max-width: 600px; width: 100%; max-height: 80vh; overflow-y: auto; }}
  .modal h3 {{ margin: 0 0 12px 0; color: #5C5CD6; }}
  .modal pre {{ background: #f5f5f5; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; }}
  .modal .copy-btn {{ margin-top: 10px; }}
  .modal-close {{ float: right; cursor: pointer; font-size: 22px; line-height: 1; color: #999; }}
  .prep-result-modal {{ max-width: 760px; }}
  .prep-status {{ font-size: 13px; color: #555; padding: 14px 0; }}
  .prep-status.error {{ color: #a80000; }}
  .prep-section {{ margin: 18px 0; padding-bottom: 18px; border-bottom: 1px solid #eee; }}
  .prep-section:last-child {{ border-bottom: none; }}
  .prep-label {{ font-size: 12px; font-weight: 700; color: #5C5CD6; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
  .prep-text {{ background: #f7f7f8; padding: 12px; border-radius: 6px; font-size: 13px; white-space: pre-wrap; word-wrap: break-word; line-height: 1.5; font-family: inherit; max-height: 260px; overflow-y: auto; margin: 0 0 8px 0; }}
  .desc {{ font-size: 12.5px; color: #444; margin-top: 6px; line-height: 1.4; }}
  .salary-row {{ margin: 6px 0 2px 0; }}
  .salary {{ display: inline-block; background: #e6fff0; color: #0a6b3a; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }}
  .tabs {{ display: flex; gap: 4px; border-bottom: 1px solid #e0e0e0; margin: 10px 0 16px 0; }}
  .tab-btn {{ background: none; border: none; padding: 8px 14px; cursor: pointer; font-size: 13px; color: #666; border-bottom: 2px solid transparent; font-weight: 500; }}
  .tab-btn.active {{ color: #5C5CD6; border-bottom-color: #5C5CD6; font-weight: 700; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .dropzone {{ display: block; box-sizing: border-box; width: 100%; border: 2px dashed #c0c8d4; border-radius: 8px; padding: 28px 16px; text-align: center; background: #fafbfc; transition: all 0.15s; cursor: pointer; }}
  .dropzone:hover, .dropzone.drag {{ background: #eef3fa; border-color: #5C5CD6; }}
  .dropzone strong {{ display: block; font-size: 14px; color: #5C5CD6; margin-bottom: 4px; }}
  .dropzone span {{ display: block; font-size: 12px; color: #666; }}
  .version-row {{ display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid #e6e8eb; border-radius: 6px; margin-bottom: 6px; background: #fff; }}
  .version-row.active {{ border-color: #5C5CD6; background: #f3f7fc; }}
  .version-main {{ flex: 1; min-width: 0; }}
  .version-label {{ font-weight: 600; font-size: 13px; color: #5C5CD6; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .version-meta {{ font-size: 11px; color: #777; margin-top: 2px; }}
  .version-badge {{ background: #5C5CD6; color: white; font-size: 10px; padding: 2px 7px; border-radius: 10px; font-weight: 700; letter-spacing: 0.3px; }}
  .version-actions {{ display: flex; gap: 4px; }}
  .v-btn {{ background: #f3f4f6; border: 1px solid #ddd; color: #333; padding: 5px 10px; border-radius: 4px; font-size: 11px; cursor: pointer; font-weight: 500; }}
  .v-btn:hover {{ background: #e6e8eb; }}
  .v-btn.danger {{ color: #b00; }}
  .v-btn.primary {{ background: #5C5CD6; color: white; border-color: #5C5CD6; }}
  /* LinkedIn contacts feature */
  .contact-badge {{ display: inline-flex; align-items: center; gap: 4px; background: #eaf2fb; color: #0a66c2; border: 1px solid #c9defb; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; cursor: pointer; margin-left: 8px; transition: all 0.12s; }}
  .contact-badge:hover {{ background: #d8e7f8; border-color: #0a66c2; }}
  .contact-badge.hiring {{ background: #fff3d6; color: #b85c00; border-color: #f0c47a; }}
  .contact-badge.hiring:hover {{ background: #ffe7a8; }}
  .btn.pending-confirm {{ background: #fff3d6 !important; color: #b85c00 !important; border-color: #f0c47a !important; }}
  .contact-badge .ic {{ font-size: 12px; line-height: 1; }}
  .contact-row {{ display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border: 1px solid #e6e8eb; border-radius: 8px; margin-bottom: 10px; background: #fff; }}
  .contact-row .name-line {{ display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }}
  .contact-row .cname {{ font-weight: 700; color: #5C5CD6; font-size: 14px; }}
  .contact-row .ctitle {{ font-size: 12px; color: #555; }}
  .contact-row .cmeta {{ font-size: 11px; color: #888; }}
  .contact-row .crow-actions {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }}
  .contact-row .msg-box {{ background: #f7f9fc; border: 1px solid #e2e7ef; border-radius: 6px; padding: 10px 12px; font-size: 12.5px; line-height: 1.55; color: #1f2a3a; white-space: pre-wrap; font-family: ui-sans-serif, system-ui, sans-serif; margin-top: 6px; }}
  .contact-empty {{ padding: 18px; text-align: center; color: #777; font-size: 13px; }}
  .contact-summary {{ background:#f3f7fc; border:1px solid #d6e1f1; border-radius:8px; padding:10px 14px; font-size:12px; color:#5C5CD6; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; }}
  .contact-summary .clear-btn {{ background: transparent; border: 1px solid #c9defb; color: #0a66c2; padding: 3px 10px; border-radius: 4px; font-size: 11px; cursor: pointer; }}
  .contact-summary .clear-btn:hover {{ background: #fff; }}
  /* ---- First-login wizard ---- */
  .wiz-overlay {{ position: fixed; inset: 0; background: rgba(15,23,60,0.92); z-index: 1000; display: none; align-items: center; justify-content: center; padding: 24px; }}
  .wiz-overlay.show {{ display: flex; }}
  .wiz-card {{ background: #fff; border-radius: 14px; max-width: 560px; width: 100%; max-height: 88vh; overflow-y: auto; box-shadow: 0 24px 64px rgba(0,0,0,0.35); padding: 30px 34px 26px; }}
  .wiz-step-count {{ font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #5C6BC0; margin-bottom: 10px; }}
  .wiz-progress {{ display: flex; gap: 6px; margin-bottom: 22px; }}
  .wiz-progress .dot {{ width: 28px; height: 4px; border-radius: 2px; background: #E2E2F2; }}
  .wiz-progress .dot.done {{ background: #5C6BC0; }}
  .wiz-progress .dot.active {{ background: #5C5CD6; }}
  .wiz-title {{ font-size: 24px; font-weight: 700; color: #5C5CD6; margin: 0 0 10px 0; line-height: 1.2; }}
  .wiz-body {{ font-size: 14.5px; color: #333; line-height: 1.55; margin: 0 0 22px 0; }}
  .wiz-body p {{ margin: 0 0 10px 0; }}
  .wiz-body ul {{ padding-left: 20px; margin: 8px 0; }}
  .wiz-body li {{ margin-bottom: 4px; }}
  .wiz-body strong {{ color: #5C5CD6; }}
  .wiz-actions {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
  .wiz-btn-primary {{ background: #5C5CD6; color: #fff; border: none; padding: 11px 22px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }}
  .wiz-btn-primary:hover {{ background: #4B4BBE; }}
  .wiz-btn-ghost {{ background: transparent; color: #666; border: none; padding: 11px 14px; font-size: 13.5px; cursor: pointer; }}
  .wiz-btn-ghost:hover {{ color: #5C5CD6; text-decoration: underline; }}
  .wiz-skip {{ margin-left: auto; }}
  .wiz-help-btn {{ background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: white; width: 32px; height: 32px; border-radius: 50%; font-size: 14px; font-weight: 700; cursor: pointer; padding: 0; display: inline-flex; align-items: center; justify-content: center; }}
  .wiz-help-btn:hover {{ background: rgba(255,255,255,0.28); }}
  .recovery-overlay {{ position: fixed; inset: 0; background: rgba(15,23,60,0.9); z-index: 1100; display: none; align-items: center; justify-content: center; padding: 24px; }}
  .recovery-overlay.show {{ display: flex; }}
  .recovery-card {{ background: #fff; border-radius: 14px; padding: 28px 32px; max-width: 520px; width: 100%; box-shadow: 0 24px 60px rgba(0,0,0,0.3); }}
  .recovery-card h3 {{ margin: 0 0 12px 0; color: #5C5CD6; font-size: 22px; }}
  .recovery-card p {{ margin: 0 0 14px 0; line-height: 1.5; font-size: 14px; color: #333; }}
  .recovery-row {{ margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap; }}
  .recovery-btn {{ background: #5C5CD6; color: white; border: 0; padding: 10px 18px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; }}
  .recovery-btn:hover {{ background: #4848bf; }}
  .recovery-btn.ghost {{ background: #fff; color: #5C5CD6; border: 1px solid #c0c8d4; }}
  .recovery-input {{ width: 100%; padding: 10px 12px; border: 1px solid #c0c8d4; border-radius: 8px; font-size: 13px; margin-top: 8px; box-sizing: border-box; font-family: monospace; }}
  .recovery-status {{ font-size: 12px; color: #777; margin-top: 10px; min-height: 16px; }}
  .recovery-status.ok {{ color: #0a6b3a; }}
  .recovery-status.err {{ color: #b00; }}
  .wiz-banner {{ position: fixed; top: 80px; left: 50%; transform: translateX(-50%); background: #5C5CD6; color: #fff; padding: 14px 22px; border-radius: 8px; box-shadow: 0 6px 20px rgba(0,0,0,0.25); z-index: 200; font-size: 14px; font-weight: 500; max-width: 90%; text-align: center; }}

  /* ---- Mobile responsive ---- */
  @media (max-width: 640px) {{
    header {{ padding: 14px 16px; }}
    header h1 {{ font-size: 18px; }}
    header .sub {{ font-size: 12px; max-width: none; white-space: normal; overflow: visible; }}
    .header-actions {{ position: static; transform: none; margin-top: 12px; flex-wrap: wrap; gap: 6px; }}
    .header-btn {{ padding: 8px 12px; font-size: 12.5px; flex: 0 0 auto; }}
    .wiz-help-btn {{ width: 30px; height: 30px; font-size: 13px; }}
    .stats {{ gap: 12px; padding: 12px 16px; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    .stat {{ flex: 0 0 auto; min-width: 84px; font-size: 11.5px; }}
    .stat b {{ font-size: 18px; }}
    .filters {{ padding: 10px 16px; gap: 8px; flex-wrap: wrap; }}
    .filters input, .filters select {{ font-size: 13px; padding: 8px 10px; flex: 1 1 140px; }}
    .grid {{ padding: 14px 16px; grid-template-columns: 1fr; gap: 10px; }}
    .card {{ padding: 12px; }}
    .title a {{ font-size: 14.5px; }}
    .app-tracker {{ padding: 12px 16px; }}
    .view-toggle {{ flex-wrap: wrap; }}
    .view-toggle .pill {{ font-size: 12px; padding: 7px 12px; }}
    .app-stats {{ gap: 8px; }}
    .app-stat {{ min-width: 68px; padding: 6px 10px; font-size: 11px; }}
    .app-stat b {{ font-size: 16px; }}
    .modal-overlay {{ padding: 0; }}
    .modal {{ max-width: 100%; max-height: 100vh; height: 100vh; border-radius: 0; padding: 18px 16px; }}
    .tabs {{ overflow-x: auto; -webkit-overflow-scrolling: touch; flex-wrap: nowrap; }}
    .tab-btn {{ padding: 10px 12px; font-size: 13px; flex: 0 0 auto; min-height: 44px; }}
    .btn {{ padding: 9px 12px; font-size: 13px; min-height: 38px; }}
    .pill {{ padding: 7px 14px; min-height: 38px; }}
    .wiz-card {{ padding: 22px 20px 18px; border-radius: 10px; max-height: 92vh; }}
    .wiz-title {{ font-size: 20px; }}
    .wiz-body {{ font-size: 14px; }}
    .wiz-btn-primary {{ padding: 12px 18px; width: 100%; }}
    .wiz-actions {{ flex-direction: column; align-items: stretch; gap: 6px; }}
    .wiz-skip {{ margin-left: 0; text-align: center; }}
    .wiz-banner {{ top: auto; bottom: 16px; left: 16px; right: 16px; transform: none; max-width: none; font-size: 13.5px; padding: 12px 16px; }}
    .contact-row {{ padding: 10px 12px; }}
    .contact-row .msg-box {{ font-size: 12px; padding: 8px 10px; }}
  }}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
</head><body>
<nav style="background:#fff;border-bottom:1px solid #E5E7EE;padding:14px 28px;margin:0;">
  <a href="/landing.html" style="display:inline-flex;align-items:center;text-decoration:none;">
    <img src="officebeat-logo.png" alt="OfficeBeat" style="height:38px;width:auto;display:block;">
  </a>
</nav>


<!-- Access-recovery modal: shown when an auth-required action returns 401 -->
<div class="recovery-overlay" id="recovery-modal" role="dialog" aria-modal="true" aria-labelledby="recovery-title">
  <div class="recovery-card">
    <h3 id="recovery-title">Your access key isn\'t valid anymore</h3>
    <p>This usually happens after clearing cookies or switching browsers. Two ways to get back in:</p>
    <p style="font-weight: 600; color: #5C5CD6;">Option A — paste a fresh invite URL</p>
    <p style="font-size: 13px; color: #555;">If you saved the original invite email or text message, paste the full URL below (it ends with <code>?key=&hellip;</code>):</p>
    <input id="recovery-paste-input" class="recovery-input" type="text" placeholder="https://getmemyjob.officebeatllc.com/{user_slug}.html?key=&hellip;">
    <div class="recovery-row">
      <button class="recovery-btn" onclick="recoveryApplyPaste()">Apply &amp; retry</button>
    </div>
    <div id="recovery-paste-status" class="recovery-status"></div>
    <p style="margin-top: 22px; font-weight: 600; color: #5C5CD6;">Option B — email Amit for a new link</p>
    <p style="font-size: 13px; color: #555;">If you don\'t have the original link, this opens your email app pre-filled. Amit will resend a fresh invite from the admin panel.</p>
    <div class="recovery-row">
      <a class="recovery-btn" id="recovery-mailto" href="#">Email Amit for a new invite</a>
      <button class="recovery-btn ghost" onclick="recoveryHide()">Close</button>
    </div>
  </div>
</div>

<!-- First-login wizard overlay -->
<div class="wiz-overlay" id="gmj-wizard" role="dialog" aria-modal="true" aria-labelledby="wiz-title">
  <div class="wiz-card">
    <div class="wiz-step-count" id="wiz-step-count">Step 1 of 5</div>
        <div style="text-align:center;margin-bottom:14px;"><img src="officebeat-logo.png" alt="OfficeBeat" style="height:28px;width:auto;"></div>
    <div class="wiz-progress" id="wiz-progress"></div>
    <h2 class="wiz-title" id="wiz-title">Welcome</h2>
    <div class="wiz-body" id="wiz-body"></div>
    <div class="wiz-actions" style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">
      <button class="wiz-btn-ghost" id="wiz-back" type="button">&larr; Back</button>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
        <button class="wiz-btn-ghost wiz-skip" id="wiz-skip" type="button">Skip for now</button>
        <button class="wiz-btn-ghost" id="wiz-save-exit" type="button" style="display:none">Save &amp; exit</button>
        <button class="wiz-btn-primary" id="wiz-cta" type="button">Let's go</button>
        <button class="wiz-btn-ghost" id="wiz-next" type="button" style="background:#EEEEF8;color:#5C5CD6;border:1px solid #C7C7E8;">Next &rarr;</button>
      </div>
    </div>
  </div>
</div>

<header>
  <h1>Jobs for {user_name}</h1>
  <div class="sub" title="{subtitle} · Generated {generated}">{subtitle} · Generated {generated}</div>
  <div class="header-actions" data-sprint-active="{sprint_active}">
    <button id="refresh-btn" class="header-btn" onclick="refreshData()" title="Pull fresh job listings from all sources. Takes 2-3 minutes.">⟳ Find new jobs</button>
    <button id="prefs-btn" class="header-btn" onclick="replayTour()" title="Re-open the setup wizard to update your bullseye, locations, scoring, etc.">⚙ Preferences</button>
    <div class="header-more-wrap">
      <button id="account-btn" class="header-btn" onclick="toggleHeaderMore(this)" aria-haspopup="true" aria-expanded="false">Account ⌄</button>
      <div class="header-more-menu" role="menu">
        <a href="/account.html">Application profile</a>
        <a href="/account.html#changePwForm">Change password</a>
        <button id="signout-btn" onclick="signOutDashboard(this)">Sign out</button>
      </div>
    </div>
    <div class="header-more-wrap">
      <button class="header-btn" onclick="toggleHeaderMore(this)" aria-haspopup="true" aria-expanded="false">More ⋯</button>
      <div class="header-more-menu" role="menu">
        <div class="hm-group">Matcher</div>
        <button id="regen-btn" onclick="regenerateFromHeader(this)" title="Re-run the AI matcher to refresh target companies + skills. Takes 30-60 seconds.">↻ Re-match my profile <span class="hm-hint">(slower)</span></button>
        <button id="regen-companies-btn" onclick="regenerateCompaniesFromHeader(this)" title="Ask AI to rebuild your 15 target companies based on your 5/5/15 bullseye. Shows a diff before saving.">⊕ Refresh target companies</button>
        <button id="why-hidden-btn" onclick="showWhyHiddenModal()" title="Search jobs that exist in our scrape but are hidden from your feed. See the exact filter that's killing each one.">⌕ Why isn&rsquo;t [X] in my feed?</button>
        <div class="hm-group">Personal</div>
        <button id="resume-btn" onclick="openResumeModal()">📄 Resume</button>
        <button id="contacts-btn" onclick="openContactsModal()">⚭ LinkedIn Contacts</button>
        <div class="hm-group">Help</div>
        <button id="show-tour-btn" onclick="if(window.gmjStartTour)gmjStartTour()">🎓 Show me around</button>
      </div>
    </div>
  </div>
</header>
{sprint_start_cta}
{sprint_strip}
{low_match_warning}
<div class="stats">
  <div class="stat personal"><b id="shown-counter">{shown}</b>Matches showing</div>
  <div class="stat personal goal-stat" id="goal-stat">
    <b><span id="goal-today-count">0</span>/<span id="goal-today-target">5</span></b>
    <span>Today\u2019s applications<br><span id="goal-progress-bar" style="display:inline-block;width:90%;height:5px;background:#e6e8eb;border-radius:3px;margin-top:4px;overflow:hidden;"><span id="goal-progress-fill" style="display:block;height:100%;width:0%;background:#5C5CD6;border-radius:3px;transition:width 0.3s;"></span></span> <span id="goal-streak" style="font-size:11px;color:#777;margin-left:4px;"></span></span>
  </div>
  <div class="stats-divider" aria-hidden="true"></div>
  <div class="stat global-stat" title="Total jobs in our entire scrape (not just yours)"><b>{total}</b>Jobs tracked (all users)</div>
  <div class="stat global-stat"><b>{senior_remote}</b>Senior + Remote (last 7d)</div>
  <div class="stat global-stat"><b>{ghost}</b>Likely ghost jobs (60d+)</div>
</div>
<div class="app-tracker">
  <div class="view-toggle">
    <span class="view-label">View:</span>
    <button class="pill active" id="view-all" onclick="setView('all')">All Jobs</button>
    <button class="pill" id="view-apps" onclick="setView('apps')">My Applications</button>
    <span class="view-label" style="margin-left:20px;">Type:</span>
    <button class="pill active" id="type-all" onclick="setEmploymentFilter('all')">All</button>
    <button class="pill" id="type-fulltime" onclick="setEmploymentFilter('full-time')">Full-time</button>
    <button class="pill" id="type-contract" onclick="setEmploymentFilter('contract')">Contract</button>
  </div>
  <div id="funnel-row" style="display:flex; gap:6px; align-items:stretch; margin-top:4px;"></div>
  <!-- Hidden per-status counters (used by JS) -->
  <div style="display:none;">
    <span id="cnt-applied">0</span><span id="cnt-phonescreen">0</span><span id="cnt-onsite">0</span>
    <span id="cnt-offer">0</span><span id="cnt-rejected">0</span><span id="cnt-response">--</span>
  </div>
</div>
<div class="filters">
  <input type="text" id="q" placeholder="Search title or company…" oninput="filter()">
  <select id="srOnly" onchange="filter()">
    <option value="">All jobs</option>
    <option value="srOnly">Senior + Remote only</option>
    <option value="sOnly">Senior only</option>
    <option value="rOnly">Remote only</option>
  </select>
  <select id="trackedFilter" onchange="filter()">
    <option value="">Tracker: all</option>
    <option value="untouched">Not yet applied</option>
    <option value="applied">Applied</option>
    <option value="phonescreen">Phone screen</option>
    <option value="onsite">Onsite</option>
    <option value="offer">Offer</option>
    <option value="rejected">Rejected</option>
  </select>
  <select id="salaryFilter" onchange="filter()">
    <option value="">Salary: any</option>
    <option value="listed">With salary listed</option>
    <option value="100000">$100k+</option>
    <option value="150000">$150k+</option>
    <option value="200000">$200k+</option>
    <option value="250000">$250k+</option>
  </select>
  <select id="recruiterFilter" onchange="filter()" title="Show or hide jobs posted by staffing/recruiting agencies">
    <option value="hide" selected>Recruiters: Hide</option>
    <option value="show">Recruiters: Show</option>
    <option value="only">Recruiters: Only</option>
  </select>
  <select id="maxPerCompanyFilter" onchange="changeMaxPerCompany()" title="How many roles per company can appear in today's picks. Default: 1 (max variety).">
    <option value="1">Max per company: 1</option>
    <option value="2">Max per company: 2</option>
    <option value="3">Max per company: 3</option>
    <option value="999">Max per company: ∞</option>
  </select>
  <select id="sortBy" onchange="sortCards()">
    <option value="sprint">Sort: Sprint priority</option>
    <option value="score">Sort: Best match</option>
    <option value="salary">Sort: Salary (high to low)</option>
    <option value="recent">Sort: Most recent</option>
    <option value="ghost">Sort: Newest postings first</option>
  </select>
  <span style="display:flex; gap:6px; align-items:center;">
    <button class="pill active" data-window="all" onclick="setWindow(this,'all')">All</button>
    <button class="pill" data-window="0" onclick="setWindow(this,0)">Today</button>
    <button class="pill" data-window="7" onclick="setWindow(this,7)">Last 7 days</button>
    <button class="pill" data-window="14" onclick="setWindow(this,14)">Last 14 days</button>
    <button class="pill" data-window="30" onclick="setWindow(this,30)">Last 30 days</button>
  </span>
</div>
<div id="contacts-priority-indicator" style="margin: 0 0 12px 0; min-height: 18px;"></div>

<!-- Daily focus panel (E6 / 2026-05-26): pin the top-N where N = dailyTarget -->
<div id="focus-panel" style="margin: 0 0 16px 0; padding:18px 22px; background:linear-gradient(135deg,#eef0ff 0%,#fef8e8 100%); border:1px solid #d0d4dc; border-radius:12px; display:none;">
  <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
    <div style="font-size:16px; font-weight:700; color:#1817B5;">
      🎯 Today’s picks: apply to <span id="focus-n">3</span>
      <button id="focus-refresh-btn" onclick="refreshPicks()" title="Recompute today’s picks from your latest feed" style="background:none;border:1px solid rgba(24,23,181,0.3);color:#1817B5;padding:2px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;margin-left:10px;vertical-align:middle;">↻ refresh</button>
    </div>
    <div style="font-size:13px; color:#444;">
      <strong id="focus-applied">0</strong> of <span id="focus-n-2">3</span> done today
      <span id="focus-progress-bar" style="display:inline-block;width:120px;height:6px;background:#dcdfe6;border-radius:3px;margin-left:8px;overflow:hidden;vertical-align:middle;">
        <span id="focus-progress-fill" style="display:block;height:100%;width:0%;background:#5C5CD6;border-radius:3px;transition:width 0.3s;"></span>
      </span>
    </div>
  </div>
  <div style="font-size:12.5px;color:#666; margin-top:6px;">
    Hand-picked from your feed: <strong>max 1 job per company</strong>, no jobs you’ve already applied to, and we suppress companies you’ve dismissed multiple times. Done one? Mark applied on the card.
  </div>
  <div id="focus-list" style="margin-top:14px; display:flex; flex-direction:column; gap:10px; font-size:13.5px;">
    <!-- populated by JS -->
  </div>
  <div id="focus-feed-toggle" style="margin-top:14px; text-align:center;">
    <button onclick="toggleFullFeed()" id="focus-feed-toggle-btn" style="background:rgba(24,23,181,0.08);border:1px solid rgba(24,23,181,0.2);color:#1817B5;padding:8px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;">
      View more matches ↓
    </button>
  </div>
</div>

<div class="grid" id="grid">
{cards}
</div>

<div class="modal-overlay" id="resume-modal" onclick="if(event.target===this)closeResumeModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeResumeModal()">&times;</span>
    <h3>{user_name}'s Resume</h3>
    <p class="prep-status" id="resume-status">Loading…</p>
    <div id="resume-editor" style="display:none;">
      <div class="tabs">
        <button class="tab-btn active" data-tab="upload" onclick="setResumeTab('upload')">Upload File</button>
        <button class="tab-btn" data-tab="profile" onclick="setResumeTab('profile')">My Profile</button>
        <button class="tab-btn" data-tab="versions" onclick="setResumeTab('versions')">Versions</button>
        <button class="tab-btn" data-tab="json" onclick="setResumeTab('json')">Edit JSON</button>
      </div>

      <div class="tab-panel active" id="tab-upload">
        <p style="font-size:13px;color:#555;margin-bottom:10px;">Upload your resume as PDF or Word. The AI converts it to structured form and saves a new version.</p>
        <label for="resume-file-input" class="dropzone" id="resume-dropzone">
          <strong id="dropzone-label">Click to choose a file</strong>
          <span>or drop a PDF or Word file (.docx — not legacy .doc) here</span>
        </label>
        <input type="file" id="resume-file-input" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" style="display:none;">
        <div style="margin-top: 12px; display: flex; gap: 8px; align-items: center;">
          <button class="btn primary" id="parse-resume-btn" onclick="parseUploadedResume(this)" disabled>Parse &amp; Save</button>
          <span id="upload-status" style="font-size: 12px; color: #555;"></span>
        </div>
        <details style="margin-top:14px;font-size:12px;color:#666;">
          <summary style="cursor:pointer;">What happens?</summary>
          <ol style="margin:6px 0 0 18px;padding:0;line-height:1.6;">
            <li>Your browser reads the file locally (it never leaves your computer raw).</li>
            <li>The extracted text is sent to the Cloudflare Worker.</li>
            <li>Claude converts it to structured JSON, saved as a new version.</li>
            <li>The new version becomes active immediately.</li>
          </ol>
        </details>
      </div>

      <div class="tab-panel" id="tab-profile">
        <p style="font-size:13px;color:#555;margin-bottom:10px;">This is what the AI extracted from your resume. We use it to match jobs. If something is missing, click <em>Edit</em> to add your own chips, or <em>Regenerate</em> to re-run extraction.</p>
        <div id="profile-display"><p style="font-size:12px;color:#888;">Loading profile…</p></div>
        <div id="profile-actions" style="margin-top:14px; display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn primary" id="edit-profile-btn" onclick="openEditProfileModal()">Edit profile</button>
          <button class="btn" id="regen-profile-btn" onclick="regenerateProfile(this)" style="background:#f3f4f6;color:#5C5CD6;border:1px solid #ccd0d6;">Regenerate from resume</button>
          <span id="regen-profile-status" style="font-size: 12px; color: #555;"></span>
        </div>
      </div>

      <!-- Edit profile modal -->
      <div id="edit-profile-overlay" style="display:none; position:fixed; inset:0; background:rgba(20,30,50,0.45); z-index:60; align-items:center; justify-content:center;" onclick="if(event.target===this)closeEditProfileModal()">
        <div style="background:#fff; padding:24px 28px; border-radius:10px; max-width:640px; width:100%; margin:12px; max-height:88vh; overflow-y:auto; box-shadow:0 24px 60px rgba(0,0,0,0.2);">
          <h3 style="margin:0 0 6px 0; color:#5C5CD6;">Edit your profile</h3>
          <p style="font-size:13px; color:#555; margin:0 0 16px 0;">Each field is a comma-separated list. Add things the AI missed (e.g. NIST CSF, HIPAA, ISO 27001). Remove anything inaccurate. Saving updates the profile used for job matching.</p>
          <div id="edit-profile-fields"></div>
          <div style="margin-top:18px; display:flex; gap:8px; flex-wrap:wrap;">
            <button class="btn primary" onclick="saveProfileEdits()">Save changes</button>
            <button class="btn" onclick="closeEditProfileModal()" style="background:#f3f4f6;color:#5C5CD6;border:1px solid #ccd0d6;">Cancel</button>
            <span id="edit-profile-status" style="font-size:12px;color:#555;align-self:center;"></span>
          </div>
        </div>
      </div>

      <div class="tab-panel" id="tab-versions">
        <p style="font-size:13px;color:#555;margin-bottom:10px;">Older versions remain saved. Click <em>Activate</em> to switch which one the AI uses.</p>
        <div id="versions-list"><p style="font-size:12px;color:#888;">Loading versions…</p></div>
      </div>

      <div class="tab-panel" id="tab-json">
        <p style="font-size:13px;color:#555;margin-bottom:8px;">Advanced: paste structured JSON directly. Saving creates a new version.</p>
        <textarea id="resume-text" spellcheck="false" style="width:100%; height:300px; font-family: ui-monospace, Menlo, monospace; font-size: 12px; padding: 10px; border: 1px solid #ddd; border-radius: 6px; resize: vertical;"></textarea>
        <div style="margin-top: 12px; display: flex; gap: 8px; align-items: center;">
          <button class="btn primary" onclick="saveResume(this)">Save resume</button>
          <span id="resume-save-status" style="font-size: 12px; color: #555;"></span>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- LinkedIn Contacts modal -->
<div class="modal-overlay" id="contacts-modal" onclick="if(event.target===this)closeContactsModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeContactsModal()">&times;</span>
    <h3>LinkedIn Contacts</h3>
    <p style="font-size:13px;color:#555;margin:0 0 14px 0;">
      Upload your LinkedIn connections (CSV) and we'll show you which of your contacts work at the companies you're applying to. Each match comes with a draft outreach message you can copy and a one-click link to their profile.
    </p>
    <div id="contacts-summary-wrap"></div>
    <div class="tabs" style="margin-bottom:10px;">
      <button class="tab-btn active" data-ctab="upload" onclick="setContactsTab('upload')">Upload CSV</button>
      <button class="tab-btn" data-ctab="list" onclick="setContactsTab('list')">My Contacts</button>
      <button class="tab-btn" data-ctab="how" onclick="setContactsTab('how')">How to export</button>
    </div>

    <div class="tab-panel active" id="ctab-upload">
      <label for="contacts-file-input" class="dropzone" id="contacts-dropzone">
        <strong id="contacts-dropzone-label">Click to choose your Connections.csv</strong>
        <span>or drop the file here. Only stays in your browser — never uploaded.</span>
      </label>
      <input type="file" id="contacts-file-input" accept=".csv,text/csv" style="display:none;">
      <div style="margin-top:12px; display:flex; gap:8px; align-items:center;">
        <button class="btn primary" id="parse-contacts-btn" onclick="parseUploadedContacts(this)" disabled>Save contacts</button>
        <span id="contacts-upload-status" style="font-size:12px; color:#555;"></span>
      </div>
    </div>

    <div class="tab-panel" id="ctab-list">
      <div id="contacts-list-wrap"><p class="contact-empty">No contacts saved yet. Upload your Connections.csv on the first tab.</p></div>
    </div>

    <div class="tab-panel" id="ctab-how">
      <ol style="font-size:13px; line-height:1.7; color:#333; padding-left:20px;">
        <li>Open LinkedIn → click your photo (top right) → <b>Settings &amp; Privacy</b>.</li>
        <li>Go to <b>Data Privacy</b> → <b>Get a copy of your data</b>.</li>
        <li>Choose <b>Want something in particular?</b> → check <b>Connections</b> only (faster than full archive).</li>
        <li>Click <b>Request archive</b>. LinkedIn emails you a download link, usually within 10 minutes.</li>
        <li>Open the email, download the ZIP, unzip it, and find <b>Connections.csv</b> inside.</li>
        <li>Come back here and upload that file on the <b>Upload CSV</b> tab.</li>
      </ol>
      <p style="font-size:12px; color:#777; margin-top:14px; line-height:1.6;">
        Re-upload anytime to refresh — newer uploads replace older ones. The file is parsed in your browser and stored only on this device.
      </p>
    </div>
  </div>
</div>

<div class="modal-overlay" id="company-contacts-modal" onclick="if(event.target===this)closeCompanyContactsModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeCompanyContactsModal()">&times;</span>
    <h3 id="company-contacts-title">Contacts at company</h3>
    <p style="font-size:13px;color:#555;margin:0 0 14px 0;" id="company-contacts-sub">Here are people you know who work there.</p>
    <div id="company-contacts-list"></div>
  </div>
</div>

<div class="modal-overlay" id="prep-modal" onclick="if(event.target===this)closeModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeModal()">&times;</span>
    <h3 id="prep-modal-title">Prep this application</h3>
    <p id="prep-status" class="prep-status">Generating tailored materials with Claude…</p>
    <div id="prep-output" style="display:none;">
      <!-- Week 1: keyword diff (recruiter Boolean search check) -->
      <div class="prep-section" id="prep-keyword-section" style="display:none;">
        <div class="prep-label" style="display:flex;align-items:center;gap:8px;">
          Recruiter keyword check
          <span id="prep-keyword-summary" style="font-size:11.5px;font-weight:500;color:#666;text-transform:none;letter-spacing:0;"></span>
        </div>
        <div id="prep-keyword-table" style="background:#fff;border:1px solid #e2e5ea;border-radius:8px;padding:10px 0;"></div>
        <button class="btn primary" onclick="copyKeywordFixList(this)" style="margin-top:10px;">Copy fix list</button>
      </div>

      <!-- Week 2: 6-second scan (what a human reviewer sees in 6s) -->
      <div class="prep-section" id="prep-scan-section" style="display:none;">
        <div class="prep-label">6-second scan (what a human reviewer sees)</div>
        <div id="prep-scan-body" style="background:#fff;border:1px solid #e2e5ea;border-radius:8px;padding:14px 16px;font-size:13px;line-height:1.55;"></div>
      </div>

      <!-- Week 2: editorial cover paragraph (paste at top of resume for this app) -->
      <div class="prep-section" id="prep-coverpara-section" style="display:none;">
        <div class="prep-label">Cover paragraph (paste at top of resume for this job)</div>
        <pre id="prep-coverpara" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-coverpara', this)">Copy cover paragraph</button>
      </div>

      <div class="prep-section">
        <div class="prep-label">Resume Summary</div>
        <pre id="prep-summary" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-summary', this)">Copy summary</button>
      </div>
      <div class="prep-section">
        <div class="prep-label">Cover Letter</div>
        <pre id="prep-cover" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-cover', this)">Copy cover letter</button>
      </div>
      <div class="prep-section">
        <div class="prep-label">LinkedIn Intro</div>
        <pre id="prep-linkedin" class="prep-text"></pre>
        <button class="btn primary" onclick="copyPrepField('prep-linkedin', this)">Copy LinkedIn intro</button>
      </div>
      <div class="prep-section" id="prep-resume-section" style="display:none;">
        <div class="prep-label">Tailored Resume</div>
        <div id="prep-resume-preview" style="background:#fff; border:1px solid #e2e5ea; padding:18px 22px; border-radius:6px; font-size:13px; line-height:1.5; max-height:420px; overflow-y:auto; margin:0 0 8px 0;"></div>
        <div style="display:flex; flex-wrap:wrap; gap:6px;">
          <button class="btn primary" onclick="copyTailoredResume(this)">Copy as text</button>
          <button class="btn primary" onclick="downloadTailoredResume('pdf', this)">Download PDF</button>
          <button class="btn primary" onclick="downloadTailoredResume('doc', this)">Download Word</button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Application detail side panel -->
<div class="modal-overlay" id="app-detail-modal" onclick="if(event.target===this)closeAppDetail()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeAppDetail()">&times;</span>
    <h3 id="app-detail-title">Application details</h3>
    <div id="app-detail-body"><p style="color:#666; font-size:13px;">Loading…</p></div>
  </div>
</div>

<!-- Follow-up draft modal -->
<div class="modal-overlay" id="followup-modal" onclick="if(event.target===this)closeFollowupModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeFollowupModal()">&times;</span>
    <h3 id="followup-title">Draft follow-up email</h3>
    <p class="prep-status" id="followup-status">Generating with Claude…</p>
    <div id="followup-output" style="display:none;">
      <div class="prep-section">
        <div class="prep-label">Subject</div>
        <pre id="followup-subject" class="prep-text"></pre>
      </div>
      <div class="prep-section">
        <div class="prep-label">Body</div>
        <pre id="followup-body" class="prep-text"></pre>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:8px;">
          <button class="btn primary" onclick="copyFollowupBody(this)">Copy</button>
          <button class="btn primary" onclick="openFollowupMailto()">Open in email client</button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Interview prep modal -->
<div class="modal-overlay" id="interview-modal" onclick="if(event.target===this)closeInterviewModal()">
  <div class="modal prep-result-modal">
    <span class="modal-close" onclick="closeInterviewModal()">&times;</span>
    <h3 id="interview-title">Interview prep</h3>
    <p class="prep-status" id="interview-status">Generating with Claude… this takes 20-30 seconds.</p>
    <div id="interview-output" style="display:none;"></div>
  </div>
</div>

<!-- Sprint config modal (prototype 2026-05-28) -->
<div class="modal-overlay" id="sprint-config-modal" onclick="if(event.target===this)closeSprintConfigModal()">
  <div class="modal sprint-config-modal" style="max-width:520px;">
    <span class="modal-close" onclick="closeSprintConfigModal()">&times;</span>
    <h3 style="margin:0 0 4px;display:flex;align-items:center;gap:8px;">🎯 Start your sprint</h3>
    <p style="margin:0 0 18px;color:#666;font-size:13.5px;">A short, focused push: a daily quota, a fixed end date, and a single email each morning with that day&rsquo;s picks. Tweak the defaults to match how aggressive you want to be.</p>
    <div class="sc-section">
      <div class="sc-label">How long?</div>
      <div class="sc-pills" data-group="duration">
        <button type="button" class="sc-pill" data-val="5">5 days</button>
        <button type="button" class="sc-pill" data-val="10">10 days</button>
        <button type="button" class="sc-pill" data-val="14">14 days</button>
        <button type="button" class="sc-pill" data-val="21">21 days</button>
      </div>
    </div>
    <div class="sc-section">
      <div class="sc-label">Apps per day</div>
      <div class="sc-pills" data-group="quota">
        <button type="button" class="sc-pill" data-val="2">2 / day</button>
        <button type="button" class="sc-pill" data-val="3">3 / day</button>
        <button type="button" class="sc-pill" data-val="5">5 / day</button>
      </div>
    </div>
    <div class="sc-section">
      <div class="sc-label">Days of the week</div>
      <div class="sc-pills sc-days" data-group="days">
        <button type="button" class="sc-pill" data-val="1">Mon</button>
        <button type="button" class="sc-pill" data-val="2">Tue</button>
        <button type="button" class="sc-pill" data-val="3">Wed</button>
        <button type="button" class="sc-pill" data-val="4">Thu</button>
        <button type="button" class="sc-pill" data-val="5">Fri</button>
        <button type="button" class="sc-pill" data-val="6">Sat</button>
        <button type="button" class="sc-pill" data-val="0">Sun</button>
      </div>
      <div class="sc-hint">Skip days won&rsquo;t count toward your streak or remaining-days count. (Saved locally for now &mdash; server enforcement is the next step.)</div>
    </div>
    <div class="sc-section">
      <div class="sc-label">Daily email nudge</div>
      <div style="display:flex;align-items:center;gap:10px;">
        <input type="time" id="sc-nudge-time" value="07:00" style="padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:13.5px;">
        <span style="font-size:12.5px;color:#666;">Eastern Time &middot; morning email with the top picks</span>
      </div>
    </div>
    <div class="sc-section">
      <div class="sc-label">End-of-day recap email</div>
      <div style="display:flex;align-items:center;gap:10px;">
        <input type="time" id="sc-recap-time" value="19:00" style="padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:13.5px;">
        <span style="font-size:12.5px;color:#666;">your local time &middot; evening email with today&rsquo;s progress</span>
      </div>
    </div>
    <div class="sc-section">
      <div class="sc-label">Your timezone</div>
      <select id="sc-timezone" style="padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:13.5px;min-width:260px;">
        <optgroup label="United States">
          <option value="America/New_York">Eastern (New York)</option>
          <option value="America/Chicago">Central (Chicago)</option>
          <option value="America/Denver">Mountain (Denver)</option>
          <option value="America/Phoenix">Mountain — no DST (Phoenix)</option>
          <option value="America/Los_Angeles">Pacific (Los Angeles)</option>
          <option value="America/Anchorage">Alaska</option>
          <option value="Pacific/Honolulu">Hawaii</option>
        </optgroup>
        <optgroup label="Americas">
          <option value="America/Toronto">Toronto</option>
          <option value="America/Vancouver">Vancouver</option>
          <option value="America/Mexico_City">Mexico City</option>
          <option value="America/Sao_Paulo">São Paulo</option>
        </optgroup>
        <optgroup label="Europe">
          <option value="Europe/London">London</option>
          <option value="Europe/Paris">Paris / Berlin / Madrid</option>
          <option value="Europe/Athens">Athens / Istanbul</option>
        </optgroup>
        <optgroup label="Asia / Pacific">
          <option value="Asia/Kolkata">Mumbai / Bengaluru / Delhi</option>
          <option value="Asia/Singapore">Singapore</option>
          <option value="Asia/Tokyo">Tokyo</option>
          <option value="Australia/Sydney">Sydney</option>
        </optgroup>
      </select>
      <div class="sc-hint">Nudge + recap emails fire at these times in your local zone.</div>
    </div>
    <div id="sc-preview" style="margin:16px 0 4px;padding:10px 12px;background:#f4f4ff;border:1px solid #d8dbe6;border-radius:8px;font-size:13px;color:#3a3a72;"></div>
    <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:14px;">
      <button type="button" class="btn ghost" onclick="closeSprintConfigModal()">Cancel</button>
      <button type="button" class="btn primary" id="sc-start-btn" onclick="startConfiguredSprint(this)">Start sprint &rarr;</button>
    </div>
  </div>
</div>

<!-- Sprint review modal (State C — prototype 2026-05-28) -->
<div class="modal-overlay" id="sprint-review-modal" onclick="if(event.target===this)closeSprintReviewModal()">
  <div class="modal sprint-review-modal" style="max-width:560px;">
    <span class="modal-close" onclick="closeSprintReviewModal()">&times;</span>
    <h3 style="margin:0 0 4px;display:flex;align-items:center;gap:8px;">🏁 Sprint complete</h3>
    <p style="margin:0 0 14px;color:#666;font-size:13.5px;" id="sr-subtitle">Nice work. Here&rsquo;s how it went &mdash; a quick recap so the next sprint can be sharper.</p>
    <div id="sr-stats" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:18px;"></div>
    <div class="sc-section">
      <div class="sc-label">What worked?</div>
      <div class="sc-pills" data-group="sr-worked">
        <button type="button" class="sc-pill" data-val="warm-intros">Warm intros</button>
        <button type="button" class="sc-pill" data-val="match-quality">Match quality</button>
        <button type="button" class="sc-pill" data-val="cadence">Cadence felt right</button>
        <button type="button" class="sc-pill" data-val="email-nudge">Daily email kept me honest</button>
      </div>
    </div>
    <div class="sc-section">
      <div class="sc-label">What didn&rsquo;t?</div>
      <div class="sc-pills" data-group="sr-didnt">
        <button type="button" class="sc-pill" data-val="too-many">Quota was too high</button>
        <button type="button" class="sc-pill" data-val="too-few">Quota was too low</button>
        <button type="button" class="sc-pill" data-val="bad-matches">Too many bad matches</button>
        <button type="button" class="sc-pill" data-val="too-short">Sprint was too short</button>
        <button type="button" class="sc-pill" data-val="too-long">Sprint was too long</button>
      </div>
    </div>
    <div class="sc-section">
      <div class="sc-label">Anything else? (optional)</div>
      <textarea id="sr-note" rows="2" placeholder="One sentence that future-you should read before starting the next sprint…" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:13px;font-family:inherit;resize:vertical;"></textarea>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:14px;flex-wrap:wrap;">
      <button type="button" class="btn ghost" onclick="finishSprintReview(this, false)">Save &amp; take a break</button>
      <button type="button" class="btn primary" onclick="finishSprintReview(this, true)">Save &amp; start another sprint &rarr;</button>
    </div>
  </div>
</div>

<script>
// === Identity + Worker base — MUST be first; everything below references USER_SLUG ===
const WORKER_BASE = 'https://cool-darkness-dce5.tr6jz6v7wg.workers.dev';
const USER_SLUG = '{user_slug}';
const USER_QS = '?user=' + encodeURIComponent(USER_SLUG);
// Hidden-jobs JSON: build-time-emitted list of jobs that didn't make Top-N,
// each tagged with a reason. Used by the "Why isn't [X] in my feed?" modal.
const _hiddenJobs = {hidden_jobs_json};
// Expose to window so page.evaluate() and external code can introspect
try {{ window._hiddenJobs = _hiddenJobs; }} catch(_) {{}}

// Remember this user as the most-recently-used dashboard so the root URL
// can auto-redirect them here next time.
try {{ localStorage.setItem('gmj_last_user', USER_SLUG); }} catch (e) {{}}

const RECENCY_WINDOW_KEY = 'htj_recency_window_' + USER_SLUG;
let activeWindow = (function() {{
  try {{ const v = localStorage.getItem(RECENCY_WINDOW_KEY); return v === null ? '7' : v; }} catch (e) {{ return '7'; }}
}})();

// --- Tracker state (localStorage) -----------------------------------------
const STATUS_CYCLE = ['', 'applied', 'phonescreen', 'onsite', 'offer', 'rejected'];
const STATUS_LABEL = {{
  '': 'Mark Applied',
  'applied': 'Applied ✓',
  'phonescreen': 'Phone Screen',
  'onsite': 'Onsite',
  'offer': 'Offer',
  'rejected': 'Rejected'
}};

// Tracker is server-side (Cloudflare KV). We cache it in memory for fast reads;
// every write goes to the Worker.
const TRACKER_WORKER_URL = WORKER_BASE + '/tracker' + USER_QS;
const FOLLOWUP_WORKER_URL = WORKER_BASE + '/draft-followup' + USER_QS;
const INTERVIEW_WORKER_URL = WORKER_BASE + '/interview-prep' + USER_QS;
let _trackerCache = null;

async function loadTracker(force) {{
  if (_trackerCache && !force) return _trackerCache;
  try {{
    const r = await fetch(TRACKER_WORKER_URL);
    const data = await r.json();
    _trackerCache = data.tracker || {{}};
  }} catch (e) {{
    // Fall back to localStorage if Worker unreachable
    try {{ _trackerCache = JSON.parse(localStorage.getItem('htj_tracker') || '{{}}'); }}
    catch (e2) {{ _trackerCache = {{}}; }}
  }}
  return _trackerCache;
}}

function getTracker() {{ return _trackerCache || {{}}; }}
function getStatus(fp) {{ return getTracker()[fp]?.status || ''; }}

async function _trackerAction(action, payload) {{
  const editKey = getEditKey();
  if (!editKey) return null;
  const body = Object.assign({{ action }}, payload || {{}});
  try {{
    const r = await fetch(TRACKER_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify(body),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      alert('Failed: ' + (data.error || ('HTTP ' + r.status)));
      return null;
    }}
    return data;
  }} catch (e) {{ alert('Network error: ' + (e.message || e)); return null; }}
}}

// One-click apply: open the job listing in a new tab and STASH it as a
// pending-confirm. We don't auto-mark Applied — that would inflate the
// counter for jobs the user just browses. Instead we ask them later
// (immediately if they tab back here, or on next dashboard load):
// "Did you complete your application to <Job> at <Company>?"
const PENDING_APPLY_KEY = "htj_pending_apply_" + USER_SLUG;

function _readPendingApplies() {{
  try {{ const r = localStorage.getItem(PENDING_APPLY_KEY); return r ? JSON.parse(r) : []; }} catch (e) {{ return []; }}
}}
function _writePendingApplies(arr) {{
  try {{ localStorage.setItem(PENDING_APPLY_KEY, JSON.stringify(arr.slice(0, 50))); }} catch (e) {{}}
}}

async function applyAndOpen(fp, btn, url) {{
  // Open immediately (before any await) so popup blockers don't kick in.
  try {{ window.open(url, "_blank", "noopener,noreferrer"); }} catch (e) {{}}
  // Stash a pending entry — we'll ask the user "did you finish?" shortly.
  const card = btn.closest(".card");
  const jobMeta = card ? {{
    fp: fp,
    title: (card.querySelector(".title a")?.textContent || "").trim(),
    company: (card.querySelector(".company")?.textContent || "").trim(),
    url: url,
    openedAt: new Date().toISOString(),
  }} : {{ fp: fp, title: "", company: "", url: url, openedAt: new Date().toISOString() }};
  const pending = _readPendingApplies().filter(p => p.fp !== fp);
  pending.push(jobMeta);
  _writePendingApplies(pending);
  // Visual cue on the button itself
  const orig = btn.textContent;
  btn.textContent = "Opened \u2192 confirm?";
  btn.disabled = false;
  btn.classList.add("pending-confirm");
  // Listen for tab refocus so we can prompt as soon as they come back
  setTimeout(function() {{ btn.textContent = orig; btn.classList.remove("pending-confirm"); }}, 8000);
  // Set up a one-shot prompt on next focus
  if (!window._pendingConfirmListenerAttached) {{
    window._pendingConfirmListenerAttached = true;
    window.addEventListener("focus", function() {{
      setTimeout(promptPendingApplies, 800);
    }});
  }}
  // Also schedule a prompt in 90s in case they don't come back to this tab
  setTimeout(promptPendingApplies, 90000);
}}

// Build a queue of unconfirmed apply-opens and prompt the user one at a time.
function promptPendingApplies() {{
  const pending = _readPendingApplies();
  if (!pending.length) return;
  // Already showing a prompt? Don't stack.
  if (document.getElementById("apply-confirm-modal")) return;
  const job = pending[0];
  const overlay = document.createElement("div");
  overlay.id = "apply-confirm-modal";
  overlay.className = "recovery-overlay show";
  overlay.style.zIndex = "1200";
  overlay.innerHTML =
    '<div class="recovery-card">' +
      '<h3 style="margin:0 0 6px 0;color:#5C5CD6;font-size:20px;">Did you finish applying?</h3>' +
      '<p style="margin:0 0 16px 0;color:#666;font-size:13px;">You opened <strong>' + (job.title || "this job") + '</strong>' + (job.company ? ' at <strong>' + job.company + '</strong>' : '') + '. Knowing whether you actually submitted lets us track your daily goal accurately.</p>' +
      '<div class="recovery-row">' +
        '<button class="recovery-btn" id="apply-confirm-yes">Yes \u2014 application submitted</button>' +
        '<button class="recovery-btn ghost" id="apply-confirm-no">No \u2014 skipped</button>' +
        '<button class="recovery-btn ghost" id="apply-confirm-later">Ask me later</button>' +
      '</div>' +
    '</div>';
  document.body.appendChild(overlay);

  function _finish(action) {{
    const arr = _readPendingApplies().filter(p => p.fp !== job.fp);
    _writePendingApplies(arr);
    overlay.remove();
    if (action === "applied") {{
      // Mark as applied via the tracker API
      _trackerAction("setStatus", {{ fp: job.fp, status: "applied", jobMeta: {{ title: job.title, company: job.company, url: job.url }} }})
        .then(function(r) {{
          if (r) _trackerCache[job.fp] = r.record;
          refreshTrackerUI();
          filter();
          if (typeof refreshDailyGoalWidget === "function") refreshDailyGoalWidget();
        }});
    }}
    // After a beat, prompt the next pending if any
    setTimeout(promptPendingApplies, 300);
  }}
  document.getElementById("apply-confirm-yes").onclick = function() {{ _finish("applied"); }};
  document.getElementById("apply-confirm-no").onclick = function() {{ _finish("skipped"); }};
  document.getElementById("apply-confirm-later").onclick = function() {{
    // Keep in pending. Move to back of queue so other pending get asked first.
    const arr = _readPendingApplies();
    const idx = arr.findIndex(p => p.fp === job.fp);
    if (idx >= 0) {{ const e = arr.splice(idx, 1)[0]; arr.push(e); _writePendingApplies(arr); }}
    overlay.remove();
  }};
}}

async function cycleStatus(fp, btn) {{
  const cur = getTracker()[fp]?.status || '';
  const next = STATUS_CYCLE[(STATUS_CYCLE.indexOf(cur) + 1) % STATUS_CYCLE.length];
  // Capture job meta from the card so the tracker knows what this job is
  const card = btn.closest('.card');
  const jobMeta = card ? {{
    title: (card.querySelector('.title a')?.textContent || '').trim(),
    company: (card.querySelector('.company')?.textContent || '').trim(),
    url: card.querySelector('.title a')?.href || '',
  }} : null;

  if (next === '') {{
    const r = await _trackerAction('clearStatus', {{ fp }});
    if (!r) return;
    delete _trackerCache[fp];
    try {{ document.dispatchEvent(new CustomEvent('tracker:updated', {{ detail: {{ fp, status: '' }} }})); }} catch(e) {{}}
  }} else {{
    const r = await _trackerAction('setStatus', {{ fp, status: next, jobMeta }});
    if (!r) return;
    _trackerCache[fp] = r.record;
    try {{ document.dispatchEvent(new CustomEvent('tracker:updated', {{ detail: {{ fp, status: next }} }})); }} catch(e) {{}}
  }}
  refreshTrackerUI();
  filter();
  if (typeof refreshDailyGoalWidget === "function") refreshDailyGoalWidget();
}}

function _daysSince(iso) {{
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86400000);
}}

function refreshTrackerUI() {{
  const tracker = getTracker();
  document.querySelectorAll('.card').forEach(card => {{
    const fp = card.dataset.fp;
    const rec = tracker[fp] || null;
    const st = rec?.status || '';
    card.dataset.status = st;
    const btn = card.querySelector('.btn.track');
    if (btn) {{
      btn.className = 'btn track ' + st;
      let label = STATUS_LABEL[st];
      if (rec && rec.lastUpdated && st) {{
        const d = _daysSince(rec.lastUpdated);
        if (d !== null) label += ' · ' + (d === 0 ? 'today' : d + 'd');
      }}
      btn.textContent = label;
    }}
    // Add/refresh Details button (only visible when tracked)
    let detailsBtn = card.querySelector('.btn.details-btn');
    if (st) {{
      if (!detailsBtn) {{
        detailsBtn = document.createElement('button');
        detailsBtn.className = 'btn details-btn';
        detailsBtn.textContent = 'Details';
        detailsBtn.style.cssText = 'background:#f3f4f6;color:#5C5CD6;border:1px solid #ccd0d6;';
        detailsBtn.onclick = (e) => {{ e.stopPropagation(); openAppDetail(fp); }};
        const actions = card.querySelector('.actions');
        if (actions) actions.insertBefore(detailsBtn, actions.querySelector('.ghost-btn'));
      }}
    }} else if (detailsBtn) {{
      detailsBtn.remove();
    }}
    // Update badges
    const badges = card.querySelector('[data-badges]');
    if (badges) {{
      badges.querySelectorAll('.b.tracker, .b.stale').forEach(b => b.remove());
      if (st) {{
        const span = document.createElement('span');
        span.className = 'b tracker ' + st;
        span.textContent = STATUS_LABEL[st];
        badges.appendChild(document.createTextNode(' '));
        badges.appendChild(span);
        // Stale alert if no movement in 7+ days while still in active stages
        const days = rec && rec.lastUpdated ? _daysSince(rec.lastUpdated) : null;
        if (days !== null && days >= 7 && ['applied','phonescreen','onsite'].includes(st)) {{
          const stale = document.createElement('span');
          stale.className = 'b stale';
          stale.style.cssText = 'background:#fff4cc; color:#7a5300; cursor:pointer;';
          stale.textContent = 'Follow up? ' + days + 'd';
          stale.onclick = (e) => {{ e.stopPropagation(); openFollowupDraft(fp); }};
          badges.appendChild(document.createTextNode(' '));
          badges.appendChild(stale);
        }}
      }}
    }}
  }});
  updateTrackerStats();
}}

function updateTrackerStats() {{
  const t = getTracker();
  const counts = {{ applied: 0, phonescreen: 0, onsite: 0, offer: 0, rejected: 0 }};
  Object.values(t).forEach(v => {{ if (counts[v.status] !== undefined) counts[v.status]++; }});
  for (const k of Object.keys(counts)) {{
    const el = document.getElementById('cnt-' + k);
    if (el) el.textContent = counts[k];
  }}
  const totalApplied = counts.applied + counts.phonescreen + counts.onsite + counts.offer + counts.rejected;
  const responses = counts.phonescreen + counts.onsite + counts.offer + counts.rejected;
  const respEl = document.getElementById('cnt-response');
  if (respEl) respEl.textContent = totalApplied === 0 ? '--' : Math.round(100 * responses / totalApplied) + '%';
  // Render funnel
  renderFunnel(counts);
}}

function renderFunnel(counts) {{
  const el = document.getElementById('funnel-row');
  if (!el) return;
  // The funnel respects status progression. "Total Applied" = anyone who ever applied
  // (includes those who progressed beyond), so we use cumulative counts.
  const c_applied = counts.applied + counts.phonescreen + counts.onsite + counts.offer + counts.rejected;
  // Empty-state: collapse the 5 empty stage cards into a thin hint row
  if (c_applied === 0) {{
    el.innerHTML = '<div class="funnel-empty">📋 Your application pipeline will appear here once you start applying. Mark jobs applied from the focus picks below.</div>';
    return;
  }}
  const c_phone = counts.phonescreen + counts.onsite + counts.offer; // people who reached at least phone screen
  const c_onsite = counts.onsite + counts.offer;
  const c_offer = counts.offer;
  function stage(label, count, prevCount, color) {{
    const pct = prevCount > 0 ? Math.round(100 * count / prevCount) + '%' : '';
    return '<div class="funnel-stage" style="flex:1; background:' + color + '; padding:10px 14px; border-radius:8px; color:#5C5CD6; min-width:0;">' +
      '<div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#666; font-weight:600;">' + label + '</div>' +
      '<div style="font-size:22px; font-weight:700; line-height:1.1; margin-top:2px;">' + count + '</div>' +
      (pct ? '<div style="font-size:11px; color:#666; margin-top:2px;">' + pct + ' from prev</div>' : '<div style="font-size:11px; color:#999; margin-top:2px;">&nbsp;</div>') +
    '</div>';
  }}
  el.innerHTML =
    stage('Applied', c_applied, 0, '#e9efff') +
    '<div style="display:flex; align-items:center; color:#bbb; font-size:18px; padding:0 4px;">▸</div>' +
    stage('Phone Screen', c_phone, c_applied, '#fff4e0') +
    '<div style="display:flex; align-items:center; color:#bbb; font-size:18px; padding:0 4px;">▸</div>' +
    stage('Onsite', c_onsite, c_phone, '#f0e6ff') +
    '<div style="display:flex; align-items:center; color:#bbb; font-size:18px; padding:0 4px;">▸</div>' +
    stage('Offer', c_offer, c_onsite, '#e6fff0') +
    '<div style="display:flex; align-items:center; color:#bbb; font-size:18px; padding:0 4px;">▸</div>' +
    stage('Rejected', counts.rejected, c_applied, '#ffe6e6');
}}

// ====================================================================
// Application detail side panel
// ====================================================================
let _currentDetailFp = null;

async function openAppDetail(fp) {{
  _currentDetailFp = fp;
  const rec = getTracker()[fp];
  if (!rec) {{ alert('Not in tracker'); return; }}
  document.getElementById('app-detail-title').textContent = (rec.title || 'Application') + ' @ ' + (rec.company || '');
  document.getElementById('app-detail-body').innerHTML = _renderAppDetail(rec);
  document.getElementById('app-detail-modal').classList.add('show');
}}

function closeAppDetail() {{
  document.getElementById('app-detail-modal').classList.remove('show');
  _currentDetailFp = null;
}}

function _renderAppDetail(rec) {{
  const days = _daysSince(rec.lastUpdated);
  const daysTxt = days === null ? '' : (days === 0 ? 'today' : days + ' days ago');
  let html = '';
  html += '<div style="background:#f8f9fb; border:1px solid #e6e8eb; border-radius:8px; padding:12px 14px; margin-bottom:14px;">';
  html += '<div style="font-size:13px;"><strong>Status:</strong> ' + (rec.status || 'untouched') + ' · last update ' + daysTxt + '</div>';
  // Status history
  if (rec.statusHistory && rec.statusHistory.length) {{
    html += '<div style="font-size:12px; color:#666; margin-top:6px;">Timeline: ';
    html += rec.statusHistory.map(h => h.status + ' (' + new Date(h.at).toLocaleDateString() + ')').join(' → ');
    html += '</div>';
  }}
  html += '</div>';
  // Recruiter
  html += '<div class="prep-section"><div class="prep-label">Recruiter / contact</div>';
  html += '<input type="text" id="detail-recruiter" value="' + _esc(rec.recruiter || '') + '" placeholder="name@example.com or LinkedIn URL" style="width:100%; box-sizing:border-box; padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px; font-size:13px;" />';
  html += '<button class="btn primary" style="margin-top:8px;" onclick="saveAppRecruiter()">Save</button>';
  html += '<span id="detail-recruiter-status" style="font-size:12px; color:#555; margin-left:10px;"></span></div>';
  // Notes
  html += '<div class="prep-section"><div class="prep-label">Notes</div>';
  html += '<textarea id="detail-notes" rows="6" placeholder="Hiring manager name, what they said, what to follow up on…" style="width:100%; box-sizing:border-box; padding:10px; font-size:13px; border:1px solid #ccd0d6; border-radius:6px; resize:vertical;">' + _esc(rec.notes || '') + '</textarea>';
  html += '<button class="btn primary" style="margin-top:8px;" onclick="saveAppNotes()">Save notes</button>';
  html += '<span id="detail-notes-status" style="font-size:12px; color:#555; margin-left:10px;"></span></div>';
  // Salary (if offer)
  if (rec.status === 'offer' || rec.salary) {{
    const s = rec.salary || {{}};
    html += '<div class="prep-section"><div class="prep-label">Offer details</div>';
    html += '<div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">';
    html += '<input id="sal-base" type="text" placeholder="Base salary" value="' + _esc(s.base || '') + '" style="padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px;" />';
    html += '<input id="sal-bonus" type="text" placeholder="Bonus %" value="' + _esc(s.bonus || '') + '" style="padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px;" />';
    html += '<input id="sal-equity" type="text" placeholder="Equity (vesting)" value="' + _esc(s.equity || '') + '" style="padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px;" />';
    html += '<input id="sal-signing" type="text" placeholder="Signing bonus" value="' + _esc(s.signing || '') + '" style="padding:8px 10px; border:1px solid #ccd0d6; border-radius:6px;" />';
    html += '</div>';
    html += '<button class="btn primary" style="margin-top:8px;" onclick="saveAppSalary()">Save compensation</button>';
    html += '<span id="detail-salary-status" style="font-size:12px; color:#555; margin-left:10px;"></span></div>';
  }}
  // Saved Prep kit
  if (rec.prepKit) {{
    html += '<div class="prep-section"><div class="prep-label">Saved Prep kit</div>';
    if (rec.prepKit.summary) html += '<div style="font-size:13px; padding:10px; background:#fafbfc; border-radius:6px; margin-bottom:8px; white-space:pre-wrap;">' + _esc(rec.prepKit.summary) + '</div>';
    html += '<button class="btn primary" onclick="reopenPrepFromTracker()">View full prep kit</button></div>';
  }}
  // Actions
  html += '<div class="prep-section">';
  html += '<button class="btn primary" onclick="openFollowupDraft(\\''+rec.fp+'\\')">Draft follow-up email</button> ';
  html += '<button class="btn primary" onclick="openInterviewPrep(\\''+rec.fp+'\\')">Generate interview prep</button> ';
  if (rec.interviewPrep && rec.interviewPrep.length) {{
    html += '<button class="btn primary" onclick="showSavedInterviewPrep()">View saved Q&amp;A (' + rec.interviewPrep.length + ')</button>';
  }}
  html += '</div>';
  return html;
}}

async function saveAppNotes() {{
  const notes = document.getElementById('detail-notes').value;
  const status = document.getElementById('detail-notes-status');
  status.textContent = 'Saving…';
  const r = await _trackerAction('setNotes', {{ fp: _currentDetailFp, notes }});
  if (r) {{
    _trackerCache[_currentDetailFp] = r.record;
    status.style.color = '#0a6b3a';
    status.textContent = 'Saved.';
  }}
}}

async function saveAppRecruiter() {{
  const recruiter = document.getElementById('detail-recruiter').value;
  const status = document.getElementById('detail-recruiter-status');
  status.textContent = 'Saving…';
  const r = await _trackerAction('setRecruiter', {{ fp: _currentDetailFp, recruiter }});
  if (r) {{
    _trackerCache[_currentDetailFp] = r.record;
    status.style.color = '#0a6b3a';
    status.textContent = 'Saved.';
  }}
}}

async function saveAppSalary() {{
  const salary = {{
    base: document.getElementById('sal-base').value,
    bonus: document.getElementById('sal-bonus').value,
    equity: document.getElementById('sal-equity').value,
    signing: document.getElementById('sal-signing').value,
  }};
  const status = document.getElementById('detail-salary-status');
  status.textContent = 'Saving…';
  const r = await _trackerAction('saveSalary', {{ fp: _currentDetailFp, salary }});
  if (r) {{
    _trackerCache[_currentDetailFp] = r.record;
    status.style.color = '#0a6b3a';
    status.textContent = 'Saved.';
  }}
}}

function reopenPrepFromTracker() {{
  const rec = getTracker()[_currentDetailFp];
  if (!rec || !rec.prepKit) return;
  closeAppDetail();
  document.getElementById('prep-modal-title').textContent = 'Materials for ' + rec.title + ' @ ' + rec.company;
  document.getElementById('prep-status').style.display = 'none';
  document.getElementById('prep-output').style.display = 'block';
  document.getElementById('prep-summary').textContent = rec.prepKit.summary || '(no summary)';
  document.getElementById('prep-cover').textContent = rec.prepKit.coverLetter || '(no cover letter)';
  document.getElementById('prep-linkedin').textContent = rec.prepKit.linkedin || '(no LinkedIn intro)';
  // Week 1: also restore keyword diff if cached
  _renderKeywordDiff(rec.prepKit.keywordDiff);
  // Week 2: restore scan + cover paragraph from cache
  _renderSixSecondScan(rec.prepKit.sixSecondScan);
  _renderCoverParagraph(rec.prepKit.coverParagraph);
  _tailoredResume = rec.prepKit.tailoredResume || null;
  _tailoredJobMeta = {{ jobTitle: rec.title, company: rec.company }};
  const sec = document.getElementById('prep-resume-section');
  if (_tailoredResume && _tailoredResume.personal) {{
    document.getElementById('prep-resume-preview').innerHTML = _renderResumeHTML(_tailoredResume);
    sec.style.display = 'block';
  }} else {{
    sec.style.display = 'none';
  }}
  document.getElementById('prep-modal').classList.add('show');
}}

// ====================================================================
// Follow-up email drafter
// ====================================================================
let _currentFollowup = null;
async function openFollowupDraft(fp) {{
  document.getElementById('followup-modal').classList.add('show');
  document.getElementById('followup-status').style.display = 'block';
  document.getElementById('followup-status').textContent = 'Generating with Claude…';
  document.getElementById('followup-output').style.display = 'none';
  const editKey = getEditKey(); // not actually needed; followup is public — but include for consistency
  try {{
    const r = await fetch(FOLLOWUP_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ fp }}),
    }});
    const data = await r.json();
    if (!r.ok || data.error) {{
      document.getElementById('followup-status').textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      return;
    }}
    _currentFollowup = data;
    const rec = getTracker()[fp];
    _currentFollowup.to = (rec && rec.recruiter) || '';
    document.getElementById('followup-subject').textContent = data.subject || '';
    document.getElementById('followup-body').textContent = data.body || '';
    document.getElementById('followup-status').style.display = 'none';
    document.getElementById('followup-output').style.display = 'block';
  }} catch (e) {{
    document.getElementById('followup-status').textContent = 'Failed: ' + (e.message || e);
  }}
}}
function closeFollowupModal() {{ document.getElementById('followup-modal').classList.remove('show'); }}
function copyFollowupBody(btn) {{
  if (!_currentFollowup) return;
  const txt = (_currentFollowup.subject || '') + '\\n\\n' + (_currentFollowup.body || '');
  navigator.clipboard.writeText(txt).then(() => {{ btn.textContent = 'Copied!'; setTimeout(() => btn.textContent = 'Copy', 1500); }});
}}
function openFollowupMailto() {{
  if (!_currentFollowup) return;
  const to = _currentFollowup.to || '';
  const m = 'mailto:' + encodeURIComponent(to) + '?subject=' + encodeURIComponent(_currentFollowup.subject || '') + '&body=' + encodeURIComponent(_currentFollowup.body || '');
  window.location.href = m;
}}

// ====================================================================
// Interview prep
// ====================================================================
async function openInterviewPrep(fp) {{
  const rec = getTracker()[fp];
  if (!rec) return;
  document.getElementById('interview-modal').classList.add('show');
  document.getElementById('interview-title').textContent = 'Interview prep — ' + rec.title + ' @ ' + rec.company;
  document.getElementById('interview-status').style.display = 'block';
  document.getElementById('interview-status').textContent = 'Generating with Claude… this takes 20-30 seconds.';
  document.getElementById('interview-output').style.display = 'none';
  try {{
    const r = await fetch(INTERVIEW_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ jobTitle: rec.title, company: rec.company }}),
    }});
    const data = await r.json();
    if (!r.ok || data.error) {{
      document.getElementById('interview-status').textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      return;
    }}
    document.getElementById('interview-status').style.display = 'none';
    document.getElementById('interview-output').style.display = 'block';
    document.getElementById('interview-output').innerHTML = _renderInterviewPrep(data.questions || []);
    // Save to tracker
    const ed = getEditKey();
    if (ed) {{
      await _trackerAction('saveInterviewPrep', {{ fp, interviewPrep: data.questions || [] }});
      const got = getTracker()[fp];
      if (got) got.interviewPrep = data.questions || [];
    }}
  }} catch (e) {{
    document.getElementById('interview-status').textContent = 'Failed: ' + (e.message || e);
  }}
}}
function closeInterviewModal() {{ document.getElementById('interview-modal').classList.remove('show'); }}
function _renderInterviewPrep(qs) {{
  if (!qs || !qs.length) return '<p>No questions generated.</p>';
  return qs.map((q, i) => {{
    const type = q.type || '';
    return '<div class="prep-section">' +
      '<div class="prep-label">' + (i+1) + '. ' + _esc(q.q || '') + (type ? ' <span style="background:#eef; color:#5C5CD6; padding:1px 7px; border-radius:10px; font-size:10px; margin-left:6px;">' + type + '</span>' : '') + '</div>' +
      '<pre class="prep-text">' + _esc(q.a || '') + '</pre>' +
      '</div>';
  }}).join('');
}}
function showSavedInterviewPrep() {{
  const rec = getTracker()[_currentDetailFp];
  if (!rec || !rec.interviewPrep) return;
  document.getElementById('interview-modal').classList.add('show');
  document.getElementById('interview-title').textContent = 'Interview prep — ' + rec.title + ' @ ' + rec.company;
  document.getElementById('interview-status').style.display = 'none';
  document.getElementById('interview-output').style.display = 'block';
  document.getElementById('interview-output').innerHTML = _renderInterviewPrep(rec.interviewPrep);
}}

// --- View mode toggle ---------------------------------------------------
let viewMode = localStorage.getItem('htj_view') || 'all';

function setView(mode) {{
  viewMode = mode;
  localStorage.setItem('htj_view', mode);
  document.body.classList.toggle('apps-mode', mode === 'apps');
  const allBtn = document.getElementById('view-all');
  const appsBtn = document.getElementById('view-apps');
  if (allBtn) allBtn.classList.toggle('active', mode === 'all');
  if (appsBtn) appsBtn.classList.toggle('active', mode === 'apps');
  filter();
}}

// --- Sorting ------------------------------------------------------------
function sortCards() {{
  const sel = document.getElementById('sortBy');
  if (!sel) return;
  const by = sel.value || 'score';
  const grid = document.getElementById('grid');
  const cards = Array.from(grid.querySelectorAll('.card'));
  function _secondary(a, b) {{
    if (by === 'sprint') return _sprintPriority(b) - _sprintPriority(a);
    if (by === 'salary') return (parseInt(b.dataset.salaryMax || '0', 10)) - (parseInt(a.dataset.salaryMax || '0', 10));
    if (by === 'recent') return (b.dataset.lastSeen || '').localeCompare(a.dataset.lastSeen || '');
    if (by === 'ghost') return (b.dataset.firstSeen || '').localeCompare(a.dataset.firstSeen || '');
    return (parseInt(b.dataset.score || '0', 10)) - (parseInt(a.dataset.score || '0', 10));
  }}
  function _sprintPriority(card) {{
    let p = 0;
    // Warm-intro wins big — connection at a hiring company = 5–10x callback rate vs cold
    const contactBadge = card.querySelector('.contact-badge');
    if (contactBadge) {{
      p += 200;
      // Hiring-role contacts (recruiter/HR) score even higher
      if (contactBadge.classList.contains('hiring')) p += 50;
    }}
    if (card.querySelector('.just-posted-badge')) p += 100;
    p += parseInt(card.dataset.score || '0', 10);
    const statusBtn = card.querySelector('[data-status-for]');
    if (statusBtn && /applied|phone|onsite|offer|rejected|dismissed/i.test(statusBtn.textContent || '')) p -= 20;
    return p;
  }}
  cards.sort((a, b) => {{
    // PRIMARY criterion: any LinkedIn connection at a company that's
    // hiring in the user's industry wins, regardless of whether the
    // contact is a recruiter or a peer. Industry match is already
    // enforced upstream (jobs without it never reach this list).
    const aHas = a.querySelector('.contact-badge') ? 1 : 0;
    const bHas = b.querySelector('.contact-badge') ? 1 : 0;
    if (aHas !== bHas) return bHas - aHas;
    return _secondary(a, b);
  }});
  cards.forEach(c => grid.appendChild(c));
  // Update the "X jobs with contacts" indicator if it exists
  const ind = document.getElementById('contacts-priority-indicator');
  if (ind) {{
    const withContacts = cards.filter(c => c.querySelector('.contact-badge') && c.style.display !== 'none').length;
    const withHiring = cards.filter(c => {{
      const b = c.querySelector('.contact-badge');
      return b && b.classList.contains('hiring') && c.style.display !== 'none';
    }}).length;
    if (withContacts > 0) {{
      ind.style.display = '';
      // Single tier — any connection at the hiring company. Recruiter count
      // is shown as supplementary info in the same line.
      const recruiterNote = withHiring > 0 ? ' <span style="color:#b85c00;">(' + withHiring + ' include a recruiter/HR contact \ud83c\udfaf)</span>' : '';
      ind.innerHTML = '<span style="font-size:11px;font-weight:600;color:#0a66c2;">\ud83e\udd1d ' + withContacts + ' job' + (withContacts === 1 ? '' : 's') + ' at companies where you have a LinkedIn connection \u2014 shown first' + recruiterNote + '</span>';
    }} else {{
      ind.style.display = 'none';
      ind.innerHTML = '';
    }}
  }}
}}

// --- Filtering ----------------------------------------------------------
function setWindow(btn, w) {{
  activeWindow = String(w);
  try {{ localStorage.setItem(RECENCY_WINDOW_KEY, String(w)); }} catch (e) {{}}
  try {{ pushPrefToProfile("recencyWindow", String(w)); }} catch (e) {{}}
  // Only toggle time-window pills (don't touch View / Type pills)
  document.querySelectorAll('[data-window]').forEach(p => p.classList.remove('active'));
  if (btn) btn.classList.add('active');
  filter();
}}
// On load, restore the saved recency window
function _restoreRecencyWindow() {{
  try {{
    const w = activeWindow;
    document.querySelectorAll('[data-window]').forEach(p => {{
      p.classList.toggle('active', p.getAttribute('data-window') === String(w));
    }});
    filter();
  }} catch (e) {{}}
}}

// --- Employment-type filter --------------------------------------------
let employmentFilter = localStorage.getItem('htj_employment') || 'all';

function setEmploymentFilter(mode) {{
  employmentFilter = mode;
  localStorage.setItem('htj_employment', mode);
  ['all','full-time','contract'].forEach(k => {{
    const el = document.getElementById('type-' + (k === 'full-time' ? 'fulltime' : k));
    if (el) el.classList.toggle('active', k === mode);
  }});
  filter();
}}
function filter() {{
  const q = document.getElementById('q').value.toLowerCase();
  const flt = document.getElementById('srOnly').value;
  const trk = document.getElementById('trackedFilter').value;
  const sal = document.getElementById('salaryFilter')?.value || '';
  const rec = document.getElementById('recruiterFilter')?.value || 'hide';
  const tracker = getTracker();
  const cards = Array.from(document.querySelectorAll('.card'));
  let shown = 0;
  cards.forEach(c => {{
    const text = c.innerText.toLowerCase();
    const senior = c.dataset.senior === '1';
    const remote = c.dataset.remote === '1';
    const days = parseInt(c.dataset.listedDays || '9999', 10);
    const salaryMax = parseInt(c.dataset.salaryMax || '0', 10);
    const st = tracker[c.dataset.fp]?.status || '';
    let show = text.includes(q);
    if (viewMode === 'apps' && !st) show = false;
    if (flt === 'srOnly' && !(senior && remote)) show = false;
    if (flt === 'sOnly' && !senior) show = false;
    if (flt === 'rOnly' && !remote) show = false;
    if (activeWindow !== 'all') {{
      const maxDays = parseInt(activeWindow, 10);
      if (days > maxDays) show = false;
    }}
    if (trk === 'untouched' && st) show = false;
    else if (trk && trk !== 'untouched' && st !== trk) show = false;
    if (sal === 'listed' && salaryMax === 0) show = false;
    else if (sal && sal !== 'listed' && salaryMax < parseInt(sal, 10)) show = false;
    // Employment-type filter — unknown counts as full-time
    const emp = c.dataset.employment || 'unknown';
    if (employmentFilter === 'contract' && emp !== 'contract') show = false;
    else if (employmentFilter === 'full-time' && emp === 'contract') show = false;
    const isRecr = c.dataset.recruiter === '1';
    if (rec === 'hide' && isRecr) show = false;
    else if (rec === 'only' && !isRecr) show = false;
    c.style.display = show ? '' : 'none';
    if (show) shown++;
  }});
  const counter = document.getElementById('shown-counter');
  if (counter) counter.textContent = shown;
}}

// --- Resume editor (Cloudflare Worker + KV) -----------------------------
// (WORKER_BASE, USER_SLUG, USER_QS now declared earlier near the tracker URLs)
const RESUME_WORKER_URL = WORKER_BASE + '/resume' + USER_QS;
const VERSIONS_WORKER_URL = WORKER_BASE + '/resume-versions' + USER_QS;
const PARSE_RESUME_WORKER_URL = WORKER_BASE + '/parse-resume' + USER_QS;

// pdf.js worker path (must be set once before parsing PDFs)
if (window.pdfjsLib) {{
  pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
}}

let _pendingUploadFile = null;

// --- Cross-device preference sync ---------------------------------------
// dailyTarget / recencyWindow / defaultSort live in localStorage for fast UI
// access, but we also mirror them to skills_profile via patchFields so the
// user's choices follow them between Chrome / Safari / mobile.
//
// On boot we GET /skills-profile and, if any of these fields are present on
// the server, copy them down into localStorage (server wins on tie). Then
// every time the user changes one, we POST patchFields to push it up.
async function hydratePrefsFromProfile() {{
  try {{
    const r = await fetch(WORKER_BASE + "/skills-profile" + USER_QS);
    if (!r.ok) return;
    const data = await r.json().catch(function() {{ return {{}}; }});
    const profile = (data && data.profile) || {{}};
    let touched = false;
    if (profile && profile.dailyTarget != null) {{
      const n = parseInt(profile.dailyTarget, 10);
      if (!isNaN(n) && n > 0 && n < 100) {{
        try {{ localStorage.setItem(DAILY_TARGET_KEY, String(n)); touched = true; }} catch (e) {{}}
      }}
    }}
    if (profile && typeof profile.recencyWindow === 'string' && profile.recencyWindow) {{
      try {{
        localStorage.setItem(RECENCY_WINDOW_KEY, profile.recencyWindow);
        activeWindow = String(profile.recencyWindow);
        touched = true;
      }} catch (e) {{}}
    }}
    if (touched) {{
      try {{ _restoreRecencyWindow(); }} catch (e) {{}}
      try {{ refreshDailyGoalWidget(); }} catch (e) {{}}
    }}
    // F4: apply salaryFloor / hideNoSalary from profile to the dropdown
    try {{ applySalaryPrefFromProfile(profile); }} catch (e) {{}}
  }} catch (e) {{ /* non-fatal: localStorage still works */ }}
}}

// Push a single scalar pref up to the user's skills_profile. Best-effort:
// silently swallow auth/network errors so the local UX is never blocked.
async function pushPrefToProfile(field, value) {{
  try {{
    const editKey = (typeof getEditKey === "function")
      ? localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key")
      : null;
    if (!editKey) return;  // not logged in yet; localStorage still works
    const patch = {{}}; patch[field] = value;
    await fetch(WORKER_BASE + "/skills-profile" + USER_QS, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json", "X-Edit-Key": editKey }},
      body: JSON.stringify({{ patchFields: patch }})
    }});
  }} catch (e) {{ /* non-fatal */ }}
}}

// ==============================================================
// F1: Not-for-me dismiss + pattern learning
// ==============================================================
const DISMISSED_KEY = 'htj_dismissed_' + USER_SLUG;
const DISMISSED_SIG_KEY = 'htj_dismissed_signals_' + USER_SLUG;

function _loadDismissedSet() {{
  try {{ return new Set(JSON.parse(localStorage.getItem(DISMISSED_KEY) || '[]')); }}
  catch (e) {{ return new Set(); }}
}}
function _saveDismissedSet(set) {{
  try {{ localStorage.setItem(DISMISSED_KEY, JSON.stringify(Array.from(set).slice(-500))); }} catch (e) {{}}
}}
function _loadDismissedSignals() {{
  try {{ return JSON.parse(localStorage.getItem(DISMISSED_SIG_KEY) || '[]'); }}
  catch (e) {{ return []; }}
}}
function _saveDismissedSignals(arr) {{
  try {{ localStorage.setItem(DISMISSED_SIG_KEY, JSON.stringify(arr.slice(-200))); }} catch (e) {{}}
}}

function dismissJob(fp, btn) {{
  const card = btn && btn.closest('.card');
  if (!card) return;
  const set = _loadDismissedSet();
  set.add(fp);
  _saveDismissedSet(set);
  const signals = _loadDismissedSignals();
  signals.push({{
    fp: fp,
    title: card.querySelector('.title') ? card.querySelector('.title').innerText.trim() : '',
    company: card.querySelector('.company') ? card.querySelector('.company').innerText.trim() : '',
    norm: card.getAttribute('data-title-norm') || '',
    ts: Date.now()
  }});
  _saveDismissedSignals(signals);
  card.style.transition = 'opacity 200ms';
  card.style.opacity = '0';
  setTimeout(function() {{ card.style.display = 'none'; }}, 220);
  // After every 5 dismissals, scan for patterns the user keeps rejecting.
  if (signals.length > 0 && signals.length % 5 === 0) {{
    setTimeout(_suggestBlocklistFromDismissals, 600);
  }}
}}

function _suggestBlocklistFromDismissals() {{
  const signals = _loadDismissedSignals();
  // Count first-2-word title prefix occurrences
  const counts = {{}};
  signals.forEach(function(s) {{
    const t = (s.title || '').toLowerCase().split(/[\s,\-]+/).filter(Boolean);
    if (t.length < 2) return;
    const key = t.slice(0, 2).join(' ');
    counts[key] = (counts[key] || 0) + 1;
  }});
  // Find prefix with >=3 hits that isn't already in negativeTitles
  const candidates = Object.entries(counts).filter(function(kv) {{ return kv[1] >= 3; }})
    .sort(function(a, b) {{ return b[1] - a[1]; }});
  if (!candidates.length) return;
  const [phrase, count] = candidates[0];
  if (sessionStorage.getItem('htj_dismissed_offer_' + phrase)) return;
  sessionStorage.setItem('htj_dismissed_offer_' + phrase, '1');
  // Build the banner via DOM API to avoid quote-escaping issues
  const banner = document.createElement('div');
  banner.style.cssText = 'position:fixed;bottom:18px;right:18px;background:#fffbe6;border:1px solid #f0c14b;border-radius:8px;padding:14px 16px;max-width:340px;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.18);font-size:13px;';
  const head = document.createElement('div');
  head.innerHTML = '<strong>Pattern detected</strong>';
  banner.appendChild(head);
  const txt = document.createElement('div');
  txt.style.margin = '6px 0 12px 0';
  txt.textContent = 'You have dismissed ' + count + ' jobs whose title starts with "' + phrase + '". Hide these permanently?';
  banner.appendChild(txt);
  const yes = document.createElement('button');
  yes.className = 'btn primary';
  yes.style.marginRight = '8px';
  yes.textContent = 'Yes, hide these';
  yes.addEventListener('click', function() {{ _acceptBlocklist(phrase, yes); }});
  banner.appendChild(yes);
  const no = document.createElement('button');
  no.className = 'btn ghost-btn';
  no.textContent = 'No thanks';
  no.addEventListener('click', function() {{ banner.remove(); }});
  banner.appendChild(no);
  document.body.appendChild(banner);
}}

async function _acceptBlocklist(phrase, btn) {{
  // Append to user profile.negativeTitles and push via patchFields
  try {{
    const r = await fetch(WORKER_BASE + '/skills-profile' + USER_QS);
    const data = await r.json().catch(function() {{ return {{}}; }});
    const cur = ((data && data.profile && data.profile.negativeTitles) || []).slice();
    if (!cur.includes(phrase)) cur.push(phrase);
    await pushPrefToProfile('negativeTitles', cur);
    if (btn && btn.parentElement) btn.parentElement.innerHTML = '<em style="color:#0a6b3a;">Saved. \"' + phrase + '\" will be hidden after the next refresh.</em>';
  }} catch (e) {{ alert('Could not save \u2014 try again.'); }}
}}

function _hideDismissedCards() {{
  const set = _loadDismissedSet();
  if (!set.size) return;
  document.querySelectorAll('.card[data-fp]').forEach(function(c) {{
    if (set.has(c.getAttribute('data-fp'))) c.style.display = 'none';
  }});
}}

// ==============================================================
// LinkedIn-connection boost: if user has uploaded their Connections.csv
// and a card's company matches a connection, give it a +15 score boost
// AND attach a "🤝 N connections here" badge that opens a warm-intro modal.
// ==============================================================
function _decorateContactBadges() {{
  if (typeof _findContactsForCompany !== 'function') return;
  const cards = document.querySelectorAll('.card[data-fp]');
  let boostedCount = 0;
  cards.forEach(function(card) {{
    if (card.getAttribute('data-contact-boost') === '1') return; // already done
    const coEl = card.querySelector('.company');
    if (!coEl) return;
    const co = coEl.textContent.trim();
    const matches = _findContactsForCompany(co);
    if (!matches.length) return;
    // Score boost: +15 to data-ai-score (capped at 100)
    const cur = parseInt(card.getAttribute('data-ai-score') || card.getAttribute('data-score') || '0', 10);
    const boosted = Math.min(100, cur + 15);
    card.setAttribute('data-ai-score', String(boosted));
    card.setAttribute('data-contact-boost', '1');
    // Update the visible score number too
    const scoreEl = card.querySelector('.score');
    if (scoreEl) {{ scoreEl.textContent = String(boosted); scoreEl.title = 'AI ' + boosted + '/100 (+15 connection boost)'; scoreEl.style.color = '#0a6b3a'; }}
    // Badge
    const actions = card.querySelector('.actions');
    if (actions && !actions.querySelector('.contact-badge')) {{
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn ghost-btn small contact-badge';
      btn.style.cssText = 'background:#ecfdf5;color:#0a6b3a;border-color:#a7f3d0;font-weight:600;';
      btn.textContent = '🤝 ' + matches.length + ' connection' + (matches.length === 1 ? '' : 's') + ' — Warm intro';
      btn.title = matches.map(function(c) {{ return c.first + ' ' + c.last + (c.position ? ' (' + c.position + ')' : ''); }}).join(' | ') + ' — Click to draft personalized intro';
      btn.addEventListener('click', function() {{ showWarmIntroModal(card.getAttribute('data-fp'), matches); }});
      const dismiss = actions.querySelector('.dismiss');
      if (dismiss) actions.insertBefore(btn, dismiss);
      else actions.appendChild(btn);
    }}
    boostedCount++;
  }});
  if (boostedCount > 0) {{
    try {{ _resortByAiScore(); }} catch (e) {{}}
    console.log('[contacts-boost] +15 applied to ' + boostedCount + ' cards');
  }}
}}

async function showWarmIntroModal(fp, connections) {{
  const card = document.querySelector('.card[data-fp="' + fp + '"]');
  if (!card) return;
  const title = ((card.querySelector('.title a') || {{}}).textContent || '').trim();
  const company = ((card.querySelector('.company') || {{}}).textContent || '').trim();
  const descEl = card.querySelector('.desc');
  const descSnippet = descEl ? descEl.innerText.trim().slice(0, 1200) : '';
  const jobUrl = (card.querySelector('.title a') || {{}}).href || '';

  // Build/replace modal
  let m = document.getElementById('warm-intro-modal');
  if (m) m.remove();
  m = document.createElement('div');
  m.id = 'warm-intro-modal';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(20,22,40,0.55);z-index:2147483600;display:flex;align-items:center;justify-content:center;padding:24px;font-family:Inter,system-ui,sans-serif;';
  const connList = connections.map(function(c) {{
    const name = (c.first + ' ' + c.last).trim();
    const pos = c.position ? c.position + (c.company ? ' @ ' + c.company : '') : (c.company || '');
    const li = c.url ? '<a href="' + c.url + '" target="_blank" rel="noopener" style="color:#5C5CD6;">' + escHtml(name) + '</a>' : escHtml(name);
    return '<div style="padding:6px 0;font-size:13px;color:#444;"><strong>' + li + '</strong> — <span style="color:#666;">' + escHtml(pos) + '</span></div>';
  }}).join('');

  m.innerHTML = ''
    + '<div style="background:white;border-radius:12px;max-width:700px;width:100%;max-height:88vh;display:flex;flex-direction:column;box-shadow:0 20px 50px rgba(0,0,0,0.3);">'
    + '  <div style="padding:18px 22px;border-bottom:1px solid #e6e8eb;display:flex;justify-content:space-between;align-items:center;">'
    + '    <h2 style="margin:0;font-size:18px;color:#1a1a2e;">🤝 Warm intro for ' + escHtml(title) + ' @ ' + escHtml(company) + '</h2>'
    + '    <button class="modal-close-btn" data-modal-id="warm-intro-modal" style="background:none;border:none;cursor:pointer;font-size:22px;color:#888;">×</button>'
    + '  </div>'
    + '  <div style="padding:14px 22px 6px;border-bottom:1px solid #f0f1f5;">'
    + '    <div style="font-size:12px;font-weight:600;color:#666;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.4px;">Your connections at this company</div>'
    + '    ' + connList
    + '  </div>'
    + '  <div id="warm-intro-content" style="padding:14px 22px 18px;overflow-y:auto;flex:1;">'
    + '    <div style="display:flex;align-items:center;gap:10px;color:#666;font-size:13px;"><div style="width:14px;height:14px;border:2px solid #5C5CD6;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite;"></div> Drafting personalized intro via AI…</div>'
    + '    <style>@keyframes spin {{ to {{ transform: rotate(360deg); }} }}</style>'
    + '  </div>'
    + '</div>';
  document.body.appendChild(m);
  m.addEventListener('click', function(e) {{ if (e.target === m) m.remove(); }});

  const content = document.getElementById('warm-intro-content');
  try {{
    const ek = (typeof getEditKey === 'function') ? getEditKey() : null;
    const headers = ek ? {{ 'X-Edit-Key': ek }} : {{}};
    headers['Content-Type'] = 'application/json';
    const r = await fetch(WORKER_BASE + '/draft-warm-intro' + USER_QS, {{
      method: 'POST',
      headers: headers,
      body: JSON.stringify({{
        fp: fp,
        job: {{ title: title, company: company, url: jobUrl, desc: descSnippet }},
        connection: connections[0]  // primary; we'll show one draft, user can adapt
      }})
    }});
    const data = await r.json();
    if (!r.ok) {{
      content.innerHTML = '<div style="color:#B91C1C;font-size:13px;">Failed: ' + (data.error || r.status) + '</div>';
      return;
    }}
    const dm = data.linkedin_dm || '';
    const subj = data.email_subject || '';
    const body = data.email_body || '';
    const dmEsc = escHtml(dm);
    const subjEsc = escHtml(subj);
    const bodyEsc = escHtml(body);
    const mailtoUrl = 'mailto:?subject=' + encodeURIComponent(subj) + '&body=' + encodeURIComponent(body);
    content.innerHTML = ''
      + '<div style="margin-bottom:18px;">'
      + '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
      + '    <div style="font-size:12px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.4px;">LinkedIn DM</div>'
      + '    <button class="copy-text-btn copy-btn-primary" data-copy-payload="' + escHtml(dm).replace(/"/g, '&quot;') + '" style="padding:4px 10px;font-size:11px;background:#5C5CD6;color:white;border:none;border-radius:4px;cursor:pointer;">Copy</button>'
      + '  </div>'
      + '  <div style="padding:10px 12px;background:#f8f9fb;border:1px solid #e6e8eb;border-radius:6px;font-size:13px;color:#1a1a2e;white-space:pre-wrap;line-height:1.5;">' + dmEsc + '</div>'
      + '</div>'
      + '<div>'
      + '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
      + '    <div style="font-size:12px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.4px;">Email</div>'
      + '    <div style="display:flex;gap:6px;">'
      + '      <button class="copy-text-btn" data-copy-payload="' + escHtml("Subject: " + subj + "\\n\\n" + body).replace(/"/g, '&quot;') + '" style="padding:4px 10px;font-size:11px;background:white;color:#5C5CD6;border:1px solid #5C5CD6;border-radius:4px;cursor:pointer;">Copy</button>'
      + '      <a href="' + mailtoUrl + '" style="padding:4px 10px;font-size:11px;background:#5C5CD6;color:white;border:none;border-radius:4px;cursor:pointer;text-decoration:none;">Open in mail app</a>'
      + '    </div>'
      + '  </div>'
      + '  <div style="padding:6px 12px;font-size:12px;color:#666;border-top:1px solid #f0f1f5;border-left:1px solid #e6e8eb;border-right:1px solid #e6e8eb;background:#fafbff;"><strong>Subject:</strong> ' + subjEsc + '</div>'
      + '  <div style="padding:10px 12px;background:#f8f9fb;border:1px solid #e6e8eb;border-top:none;border-radius:0 0 6px 6px;font-size:13px;color:#1a1a2e;white-space:pre-wrap;line-height:1.5;">' + bodyEsc + '</div>'
      + '</div>'
      + '<div style="font-size:11px;color:#888;margin-top:14px;font-style:italic;">AI-drafted from your profile + their LinkedIn position. Edit before sending.</div>';
  }} catch (e) {{
    content.innerHTML = '<div style="color:#B91C1C;font-size:13px;">Network error: ' + (e.message || e) + '</div>';
  }}
}}

// ==============================================================
// F5: Why-was-this-shown tooltip + cross-company cluster badge
// ==============================================================
function showWhyMatched(fp, btn) {{
  const card = btn && btn.closest('.card');
  if (!card) return;
  const why = card.getAttribute('data-why') || 'No explanation available.';
  // Toggle existing
  const existing = card.querySelector('.why-tooltip');
  if (existing) {{ existing.remove(); return; }}
  const tip = document.createElement('div');
  tip.className = 'why-tooltip';
  tip.style.cssText = 'margin-top:8px;padding:8px 10px;background:#f4f6fb;border-left:3px solid #5C5CD6;border-radius:4px;font-size:12px;color:#444;line-height:1.5;';
  tip.textContent = 'Matched because: ' + why;
  card.appendChild(tip);
}}

function _renderClusterBadges() {{
  document.querySelectorAll('.card[data-cluster-count]').forEach(function(c) {{
    const n = parseInt(c.getAttribute('data-cluster-count') || '0', 10);
    if (n < 1) return;
    const names = c.getAttribute('data-cluster-companies') || '';
    if (c.querySelector('.cluster-badge')) return;  // already rendered
    const badgesRow = c.querySelector('[data-badges]');
    if (!badgesRow) return;
    const b = document.createElement('span');
    b.className = 'b cluster-badge';
    b.style.cssText = 'background:#eef2ff;color:#3b3f8a;border:1px solid #c7d2fe;';
    b.title = 'Also hiring this role: ' + names;
    b.textContent = 'Also at ' + n + ' other employer' + (n === 1 ? '' : 's');
    badgesRow.appendChild(document.createTextNode(' '));
    badgesRow.appendChild(b);
  }});
}}

// ==============================================================
// F4: Apply salaryFloor / hideNoSalary from profile into the existing
// salary dropdown so jobs the user explicitly excluded are not shown.
// ==============================================================
function applySalaryPrefFromProfile(profile) {{
  // Intentionally a no-op now: auto-applying salaryFloor was hiding most jobs
  // (most ATS listings have no listed salary, so the gate filtered to 0).
  // Users opt in by selecting the salary dropdown themselves; their choice
  // still syncs to profile.salaryFloor via the change handler.
  return;
}}

// Save salary choice back to profile so it syncs across devices.
(function _hookSalarySync() {{
  function run() {{
    const sel = document.getElementById('salaryFilter');
    if (!sel) return;
    sel.addEventListener('change', function() {{
      const v = sel.value;
      if (v === 'listed') {{
        pushPrefToProfile('hideNoSalary', true);
        pushPrefToProfile('salaryFloor', 0);
      }} else if (v && /^\d+$/.test(v)) {{
        pushPrefToProfile('hideNoSalary', false);
        pushPrefToProfile('salaryFloor', parseInt(v, 10));
      }} else {{
        pushPrefToProfile('hideNoSalary', false);
        pushPrefToProfile('salaryFloor', 0);
      }}
    }});
  }}
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
}})();

// ==============================================================
// F2: AI re-rank the visible cards (Claude Haiku via Worker /rerank-titles)
// ==============================================================
const RERANK_CACHE_KEY = 'htj_ai_rerank_' + USER_SLUG;
const RERANK_TTL_MS = 24 * 60 * 60 * 1000;

function _loadRerankCache() {{
  try {{
    const raw = JSON.parse(localStorage.getItem(RERANK_CACHE_KEY) || '{{}}');
    const now = Date.now();
    const out = {{}};
    for (const [fp, v] of Object.entries(raw)) {{
      if (v && v.ts && (now - v.ts) < RERANK_TTL_MS) out[fp] = v;
    }}
    return out;
  }} catch (e) {{ return {{}}; }}
}}
function _saveRerankCache(cache) {{
  try {{ localStorage.setItem(RERANK_CACHE_KEY, JSON.stringify(cache)); }} catch (e) {{}}
}}

async function aiRerankCards() {{
  // Disabled if user explicitly turned it off
  if (localStorage.getItem('htj_ai_rerank_off_' + USER_SLUG) === '1') return;
  const cards = Array.from(document.querySelectorAll('.card[data-fp]'));
  if (!cards.length) return;
  const cache = _loadRerankCache();
  const need = [];
  cards.forEach(function(c) {{
    if (c.style.display === 'none') return;
    const fp = c.getAttribute('data-fp');
    if (!fp) return;
    if (cache[fp]) {{ _applyAiScore(c, cache[fp].score, cache[fp].hardBlocker); return; }}
    const titleEl = c.querySelector('.title a, .title');
    const title = titleEl ? titleEl.innerText.trim() : '';
    // Pull JD snippet from the card body — already in DOM, no extra fetch.
    const descEl = c.querySelector('.desc');
    const desc = descEl ? descEl.innerText.trim().slice(0, 1200) : '';
    if (title) need.push({{fp: fp, title: title, desc: desc}});
  }});
  if (cache && Object.keys(cache).length) {{ _resortByAiScore(); }}
  if (!need.length) return;
  // Batch in chunks of 40 to keep prompt size sane
  const batches = [];
  for (let i = 0; i < need.length; i += 40) batches.push(need.slice(i, i + 40));
  for (const batch of batches) {{
    try {{
      const r = await fetch(WORKER_BASE + '/rerank-titles' + USER_QS, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{items: batch}})
      }});
      if (!r.ok) continue;
      const data = await r.json().catch(function() {{ return {{}}; }});
      const scores = (data && data.scores) || {{}};
      for (const [fp, val] of Object.entries(scores)) {{
        // val may be a plain int (old API) or an object {{score, hardBlocker}} (new API)
        const score = (typeof val === 'object' && val) ? (val.score || 0) : val;
        const hardBlocker = (typeof val === 'object' && val) ? !!val.hardBlocker : false;
        cache[fp] = {{score: score, hardBlocker: hardBlocker, ts: Date.now()}};
        const c = document.querySelector('.card[data-fp="' + fp + '"]');
        if (c) _applyAiScore(c, score, hardBlocker);
      }}
      _saveRerankCache(cache);
      _resortByAiScore();
    }} catch (e) {{ /* network blip, skip batch */ }}
  }}
}}

function _applyAiScore(card, score, hardBlocker) {{
  const scoreEl = card.querySelector('.score');
  if (!scoreEl) return;
  if (hardBlocker) {{
    // Card flunked the JD-aware AI check (requires expertise the user doesn't have, wrong seniority, etc.)
    card.setAttribute('data-ai-score', '0');
    card.setAttribute('data-ai-blocked', '1');
    card.style.display = 'none';
    return;
  }}
  card.setAttribute('data-ai-score', String(score));
  scoreEl.textContent = String(score);
  scoreEl.title = 'AI fit score (' + score + '/100)';
}}

function _resortByAiScore() {{
  const grid = document.getElementById('grid');
  if (!grid) return;
  const cards = Array.from(grid.querySelectorAll('.card[data-fp]'));
  cards.sort(function(a, b) {{
    const sa = parseInt(a.getAttribute('data-ai-score') || a.getAttribute('data-score') || '0', 10);
    const sb = parseInt(b.getAttribute('data-ai-score') || b.getAttribute('data-score') || '0', 10);
    return sb - sa;
  }});
  cards.forEach(function(c) {{ grid.appendChild(c); }});
}}

// On first visit via invite link, the password is in the URL as ?key=XXX.
// Capture it, store to localStorage, then strip from URL so it isn't visible later.
(function bootstrapDailyWidget() {{
  function run() {{
    try {{ refreshDailyGoalWidget(); }} catch (e) {{}}
    try {{ promptPendingApplies(); }} catch (e) {{}}
    try {{ _restoreRecencyWindow(); }} catch (e) {{}}
    // Pull cross-device prefs from the server; happens async, will re-render
    // the widget + recency pills once it lands.
    try {{ hydratePrefsFromProfile(); }} catch (e) {{}}
    // F1: hide jobs the user has already dismissed in this browser.
    try {{ _hideDismissedCards(); }} catch (e) {{}}
    // LinkedIn-connection boost + warm-intro badges (no-op if no contacts uploaded yet)
    try {{ _decorateContactBadges(); }} catch (e) {{}}
    // F5: render cross-company "Also at" badges.
    try {{ _renderClusterBadges(); }} catch (e) {{}}
    // F2: AI re-rank the visible cards in the background.
    try {{ aiRerankCards(); }} catch (e) {{}}
    // Engagement-driven intelligence: check for bullseye refinement suggestions
    try {{ _checkRefinementSuggestions(); }} catch (e) {{}}
  }}
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();
}})();


// One-time global listener for modal close buttons (avoids inline-onclick
// nested-quote escape hell that broke the entire main script previously).
(function setupModalCloseDelegate() {{
  document.addEventListener('click', function(e) {{
    var btn = e.target;
    if (!btn || !btn.classList) return;
    // Modal close buttons
    if (btn.classList.contains('modal-close-btn')) {{
      var modalId = btn.getAttribute('data-modal-id');
      if (modalId) {{
        var modal = document.getElementById(modalId);
        if (modal) modal.remove();
      }}
      return;
    }}
    // Copy-to-clipboard buttons
    if (btn.classList.contains('copy-text-btn')) {{
      var raw = btn.getAttribute('data-copy-payload') || '';
      // The data-attr value was HTML-escaped; decode common entities
      var txt = raw.replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#39;/g, "'");
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(txt).then(function() {{
          var orig = btn.textContent;
          btn.textContent = 'Copied';
          setTimeout(function() {{ btn.textContent = orig || 'Copy'; }}, 1500);
        }});
      }}
      return;
    }}
  }}, false);
}})();

(function captureInviteKey() {{
  try {{
    const params = new URLSearchParams(window.location.search);
    const k = params.get('key');
    if (k) {{
      // Store per-user key so each dashboard remembers its own
      localStorage.setItem('htj_resume_key_' + USER_SLUG, k);
      params.delete('key');
      const q = params.toString();
      const newUrl = window.location.pathname + (q ? '?' + q : '') + window.location.hash;
      window.history.replaceState({{}}, '', newUrl);
    }}
  }} catch (e) {{ /* non-fatal */ }}
}})();

function getEditKey() {{
  // Silent lookup only — no native prompt. Callers handle null by either
  // falling back to admin-key auth or showing the inline Verify Session modal.
  return localStorage.getItem('htj_resume_key_' + USER_SLUG)
      || localStorage.getItem('htj_resume_key')
      || null;
}}

// Inline session-verify modal — replaces the old prompt('Enter the password')
// flow. Shows up when an action needs auth but no edit key is stored. The user
// clicks Confirm; if an admin key is stored we try that, otherwise we email
// for a fresh invite.
function showVerifyModal(onConfirm) {{
  // Admin-key fallback: silently confirm if it's stored
  const adminKey = localStorage.getItem('htj_admin_key');
  if (adminKey) {{ onConfirm && onConfirm(adminKey, 'admin'); return; }}
  // Build modal with DOM API (no innerHTML, no quote-escape risk)
  let m = document.getElementById('verify-modal');
  if (m) {{ m.style.display = 'flex'; return; }}
  m = document.createElement('div');
  m.id = 'verify-modal';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.45);display:flex;align-items:center;justify-content:center;z-index:99999;';
  const card = document.createElement('div');
  card.style.cssText = 'background:#fff;border-radius:12px;padding:24px;max-width:380px;width:90%;box-shadow:0 6px 24px rgba(0,0,0,0.2);font-family:Inter,sans-serif;';
  const title = document.createElement('div');
  title.style.cssText = 'font-size:16px;font-weight:700;margin-bottom:8px;';
  title.textContent = 'Confirm changes';
  card.appendChild(title);
  const desc = document.createElement('div');
  desc.style.cssText = 'font-size:13px;color:#555;margin-bottom:16px;line-height:1.5;';
  desc.textContent = 'Your save key is not stored in this browser. Click Confirm to try anyway, or email us for a fresh invite link.';
  card.appendChild(desc);
  const row = document.createElement('div');
  row.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;';
  const cancel = document.createElement('button');
  cancel.textContent = 'Cancel';
  cancel.style.cssText = 'padding:8px 14px;border:1px solid #d0d4dc;border-radius:6px;background:#fff;cursor:pointer;font-size:13px;';
  cancel.onclick = function() {{ m.style.display = 'none'; }};
  const emailLink = document.createElement('a');
  emailLink.textContent = 'Email for link';
  emailLink.href = 'mailto:info@officebeatllc.com?subject=Fresh%20invite%20link%20needed';
  emailLink.style.cssText = 'padding:8px 14px;border:1px solid #d0d4dc;border-radius:6px;background:#fff;text-decoration:none;color:#333;font-size:13px;display:inline-block;';
  const confirm = document.createElement('button');
  confirm.textContent = 'Confirm';
  confirm.style.cssText = 'padding:8px 14px;border:none;border-radius:6px;background:#5C5CD6;color:#fff;cursor:pointer;font-size:13px;font-weight:600;';
  confirm.onclick = function() {{ m.style.display = 'none'; onConfirm && onConfirm(null, 'none'); }};
  row.appendChild(cancel); row.appendChild(emailLink); row.appendChild(confirm);
  card.appendChild(row);
  m.appendChild(card);
  document.body.appendChild(m);
}}

// === Week 3: Resume Health renderer (deterministic) ==================
async function _renderResumeHealth() {{
  const widget = document.getElementById('resume-health-widget');
  if (!widget) return;
  widget.style.display = 'block';
  widget.innerHTML = '<div style="font-size:13px;color:#666;">Checking resume health…</div>';
  try {{
    const r = await fetch(WORKER_BASE + '/resume-health' + USER_QS, {{ cache: 'no-store' }});
    const h = await r.json();
    if (!r.ok || !h || typeof h.score !== 'number') {{
      widget.innerHTML = '<div style="font-size:13px;color:#a55;">Couldn\\'t compute health: ' + ((h && h.error) || ('HTTP ' + r.status)) + '</div>';
      return;
    }}
    function esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }}[c])); }}
    function bar(score) {{
      const color = score >= 80 ? '#0a6b3a' : (score >= 60 ? '#5C5CD6' : (score >= 40 ? '#a86b00' : '#B91C1C'));
      const pct = Math.max(0, Math.min(100, score));
      return '<div style="display:inline-block;vertical-align:middle;width:120px;height:6px;background:#eef0ff;border-radius:3px;overflow:hidden;margin:0 8px;">' +
             '<div style="width:' + pct + '%;height:100%;background:' + color + ';"></div></div>';
    }}
    function row(label, score, note) {{
      const color = score >= 80 ? '#0a6b3a' : (score >= 60 ? '#5C5CD6' : (score >= 40 ? '#a86b00' : '#B91C1C'));
      return '<div style="display:flex;justify-content:space-between;align-items:center;font-size:12.5px;padding:4px 0;border-bottom:1px solid #f4f5f7;">' +
        '<span>' + esc(label) + (note ? '  <span style="color:#888;font-weight:400;">' + esc(note) + '</span>' : '') + '</span>' +
        '<span>' + bar(score) + '<span style="color:' + color + ';font-weight:600;min-width:38px;display:inline-block;text-align:right;">' + score + '</span></span>' +
        '</div>';
    }}
    const b = h.breakdown || {{}};
    const headColor = h.score >= 80 ? '#0a6b3a' : (h.score >= 60 ? '#5C5CD6' : (h.score >= 40 ? '#a86b00' : '#B91C1C'));
    let html = '';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
    html += '<div style="font-size:13px;font-weight:600;color:#1A1A2E;">Resume health score</div>';
    html += '<div style="font-size:24px;font-weight:700;color:' + headColor + ';">' + h.score + ' / 100</div>';
    html += '</div>';
    html += '<div style="margin-bottom:6px;">';
    html += row('Keyword coverage',      (b.keyword || {{}}).score || 0,        (b.keyword || {{}}).hit ? ((b.keyword.hit.length) + ' of ' + ((b.keyword.hit.length||0) + (b.keyword.missing.length||0)) + ' target terms in resume') : '');
    html += row('Quantified bullets',    (b.quantified || {{}}).score || 0,     (b.quantified || {{}}).total ? ((b.quantified.quantified) + ' / ' + (b.quantified.total) + ' bullets have a number') : '');
    html += row('Title alignment',       (b.titleAlignment || {{}}).score || 0, ((b.titleAlignment || {{}}).status || ''));
    html += row('Recency + clarity',     (b.recency || {{}}).score || 0,        ((b.recency || {{}}).issues || []).length ? (b.recency.issues.length + ' issue(s)') : '');
    html += row('Parseability',          (b.parseability || {{}}).score || 0,   '');
    html += '</div>';
    // Quick actionable callouts (top 2 weakest)
    const sorted = [
      {{ label: 'keywords', score: (b.keyword || {{}}).score || 0, missing: (b.keyword || {{}}).missing || [] }},
      {{ label: 'quantified', score: (b.quantified || {{}}).score || 0, weak: (b.quantified || {{}}).weakBullets || [] }},
      {{ label: 'title', score: (b.titleAlignment || {{}}).score || 0, observed: (b.titleAlignment || {{}}).observed || '', targeted: (b.titleAlignment || {{}}).targeted || [] }},
      {{ label: 'recency', score: (b.recency || {{}}).score || 0, issues: (b.recency || {{}}).issues || [] }}
    ].sort((a, b2) => a.score - b2.score);
    const top2 = sorted.filter(s => s.score < 80).slice(0, 2);
    if (top2.length) {{
      html += '<div style="margin-top:10px;padding:8px 10px;background:#fff7e6;border:1px solid #fcd34d;border-radius:6px;font-size:12.5px;color:#78350f;">';
      html += '<strong>Quick wins:</strong><ul style="margin:6px 0 0;padding-left:20px;">';
      top2.forEach(t => {{
        if (t.label === 'keywords' && t.missing.length) {{
          html += '<li>Add these target terms to your resume body (currently missing): <em>' + esc(t.missing.slice(0,5).join(', ')) + '</em></li>';
        }} else if (t.label === 'quantified' && t.weak.length) {{
          html += '<li>Quantify these bullets (add a number or %): <em>' + esc(t.weak[0].slice(0, 100)) + (t.weak[0].length > 100 ? '…' : '') + '</em></li>';
        }} else if (t.label === 'title' && t.targeted.length) {{
          html += '<li>Your title line says <em>' + esc(t.observed || '(blank)') + '</em>; targets are <em>' + esc(t.targeted.slice(0,3).join(', ')) + '</em>. Consider adding a one-line subtitle.</li>';
        }} else if (t.label === 'recency' && t.issues.length) {{
          html += '<li>' + esc(t.issues[0]) + '</li>';
        }}
      }});
      html += '</ul></div>';
    }}
    html += '<div style="font-size:11px;color:#888;margin-top:8px;">Computed ' + new Date(h.computedAt).toLocaleString() + '. Re-uploading your resume re-runs this check.</div>';
    html += '<button class="btn primary" id="resume-health-fix-btn" style="margin-top:10px;" onclick="_loadResumeHealthFixes(this)">Show me what to fix</button>';
    html += '<div id="resume-health-fixes" style="display:none;margin-top:14px;"></div>';
    widget.innerHTML = html;
  }} catch (e) {{
    widget.innerHTML = '<div style="font-size:13px;color:#a55;">Couldn\\'t compute health (' + ((e && e.message) || e) + ')</div>';
  }}
}}

// === Week 4: LLM-powered "Show me what to fix" ========================
async function _loadResumeHealthFixes(btn) {{
  const out = document.getElementById('resume-health-fixes');
  if (!out) return;
  out.style.display = 'block';
  out.innerHTML = '<div style="font-size:13px;color:#666;">Asking Claude for concrete rewrites &middot; ~15s…</div>';
  if (btn) {{ btn.disabled = true; btn.textContent = 'Generating…'; }}
  try {{
    const r = await fetch(WORKER_BASE + '/resume-health-suggest' + USER_QS, {{ cache: 'no-store' }});
    const j = await r.json();
    if (!r.ok || j.error) {{
      out.innerHTML = '<div style="font-size:13px;color:#a55;">Couldn\\'t generate fixes: ' + ((j && j.error) || ('HTTP ' + r.status)) + '</div>';
      if (btn) {{ btn.disabled = false; btn.textContent = 'Try again'; }}
      return;
    }}
    function esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }}[c])); }}
    let html = '';
    if (j.titleSubtitle && j.titleSubtitle.trim()) {{
      html += '<div style="margin-bottom:14px;padding:10px 12px;background:#fff7e6;border:1px solid #fcd34d;border-radius:8px;">';
      html += '<div style="font-size:12px;font-weight:600;color:#78350f;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:4px;">Add this subtitle under your name</div>';
      html += '<code style="font-size:13px;background:#fff;padding:4px 8px;border-radius:4px;display:inline-block;">' + esc(j.titleSubtitle) + '</code>';
      html += '</div>';
    }}
    const rewrites = Array.isArray(j.bulletRewrites) ? j.bulletRewrites : [];
    if (rewrites.length) {{
      html += '<div style="font-size:12px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.04em;margin-bottom:8px;">Bullet rewrites</div>';
      rewrites.forEach((rw, i) => {{
        html += '<div style="margin-bottom:12px;padding:12px;background:#f7f8fb;border:1px solid #e2e5ea;border-radius:8px;">';
        html += '<div style="font-size:11.5px;color:#a55;margin-bottom:4px;">BEFORE</div>';
        html += '<div style="font-size:13px;color:#444;margin-bottom:8px;line-height:1.5;">' + esc(rw.original || '') + '</div>';
        html += '<div style="font-size:11.5px;color:#0a6b3a;margin-bottom:4px;">AFTER</div>';
        html += '<div style="font-size:13px;color:#1a1a2e;margin-bottom:6px;font-weight:500;line-height:1.5;">' + esc(rw.suggested || '') + '</div>';
        if (rw.why) html += '<div style="font-size:11.5px;color:#666;font-style:italic;margin-bottom:6px;">Why: ' + esc(rw.why) + '</div>';
        html += '<button class="btn ghost rh-copy-btn" data-rh-copy="' + esc(rw.suggested || '').replace(/&quot;/g, '&quot;') + '" style="font-size:11.5px;padding:4px 10px;">Copy AFTER</button>';
        html += '</div>';
      }});
    }}
    const injections = Array.isArray(j.keywordInjections) ? j.keywordInjections : [];
    if (injections.length) {{
      html += '<div style="font-size:12px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.04em;margin-top:14px;margin-bottom:8px;">Add these keywords</div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:12.5px;">';
      injections.forEach(inj => {{
        html += '<tr style="border-bottom:1px solid #f4f5f7;">';
        html += '<td style="padding:6px 10px;font-weight:600;">' + esc(inj.term) + '</td>';
        html += '<td style="padding:6px 10px;color:#666;">in <strong>' + esc(inj.wherePlace || '') + '</strong></td>';
        html += '<td style="padding:6px 10px;"><code style="background:#fff;border:1px solid #e0e2ed;padding:2px 6px;border-radius:4px;">' + esc(inj.verbatim || '') + '</code></td>';
        html += '</tr>';
      }});
      html += '</table>';
    }}
    if (!html) {{
      html = '<div style="font-size:13px;color:#666;">No fixes needed — your resume already covers what your profile targets.</div>';
    }}
    out.innerHTML = html;
    out.querySelectorAll('.rh-copy-btn').forEach(b => {{
      b.addEventListener('click', () => {{
        const txt = b.getAttribute('data-rh-copy') || '';
        // Decode the HTML entities we escaped during render
        const decoded = txt.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"');
        navigator.clipboard.writeText(decoded).then(() => {{
          const orig = b.textContent;
          b.textContent = 'Copied!';
          setTimeout(() => {{ b.textContent = orig; }}, 1200);
        }});
      }});
    }});
    if (btn) {{ btn.disabled = false; btn.textContent = 'Regenerate fixes'; }}
  }} catch (e) {{
    out.innerHTML = '<div style="font-size:13px;color:#a55;">Network error: ' + ((e && e.message) || e) + '</div>';
    if (btn) {{ btn.disabled = false; btn.textContent = 'Try again'; }}
  }}
}}

function setResumeTab(name) {{
  document.querySelectorAll('#resume-editor .tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('#resume-editor .tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + name));
  if (name === 'versions') loadVersions();
  if (name === 'profile') loadProfile();
}}

const PROFILE_WORKER_URL = WORKER_BASE + '/skills-profile' + USER_QS;

async function loadProfile() {{
  const el = document.getElementById('profile-display');
  const actions = document.getElementById('profile-actions');
  el.innerHTML = '<p style="font-size:12px;color:#888;">Loading profile…</p>';
  if (actions) actions.style.display = 'none';
  try {{
    const r = await fetch(PROFILE_WORKER_URL);
    const data = await r.json();
    const p = data.profile;
    if (!p) {{
      el.innerHTML =
        '<div style="background:#f3f7fc;border:1px solid #d6e1f1;border-radius:10px;padding:22px 24px;text-align:center;">' +
          '<div style="font-size:36px;line-height:1;margin-bottom:8px;">📄</div>' +
          '<div style="font-size:15px;font-weight:600;color:#5C5CD6;margin-bottom:6px;">No skills profile yet</div>' +
          '<div style="font-size:13px;color:#555;margin-bottom:16px;line-height:1.5;">Upload your resume (PDF or Word) and our AI will extract your target roles, industries, skills, technologies, and regulations — so the dashboard only shows jobs that actually match you.</div>' +
          '<button class="btn primary" onclick="setResumeTab(\\'upload\\')" style="padding:10px 22px;font-size:13.5px;">Upload your resume →</button>' +
        '</div>';
      // Hide Edit/Regenerate buttons — nothing to edit or regenerate yet.
      if (actions) actions.style.display = 'none';
      return;
    }}
    el.innerHTML = _renderProfileHTML(p);
    if (actions) actions.style.display = 'flex';
  }} catch (e) {{
    el.innerHTML = '<p style="font-size:13px;color:#b00;">Failed to load: ' + (e.message || e) + '</p>';
    if (actions) actions.style.display = 'none';
  }}
}}

function _renderProfileHTML(p) {{
  function section(title, items, color, fieldKey) {{
    items = items || [];
    const chips = items.map(s => {{
      const safe = _esc(s);
      const jsSafe = String(s).replace(/'/g, "\\\\'").replace(/"/g, '&quot;');
      return '<span style="display:inline-flex;align-items:center;background:' + color + ';color:#5C5CD6;padding:3px 4px 3px 9px;border-radius:12px;font-size:11.5px;margin:2px 4px 2px 0;font-weight:500;">' +
             safe +
             (fieldKey ? '<button onclick="removeChip(\\''+ fieldKey +'\\', \\''+ jsSafe +'\\')" style="background:none;border:0;color:#888;cursor:pointer;padding:0 0 0 6px;font-size:14px;line-height:1;font-weight:600;" title="Remove">&times;</button>' : '') +
             '</span>';
    }}).join('');
    const addBtn = fieldKey
      ? '<button onclick="addChip(\\''+ fieldKey +'\\')" style="display:inline-block;background:#fafbfc;border:1px dashed #c0c8d4;color:#5C5CD6;padding:3px 11px;border-radius:12px;font-size:11.5px;cursor:pointer;font-weight:500;margin:2px 4px 2px 0;">+ Add</button>'
      : '';
    const count = items.length > 0 ? (' <span style="color:#999;font-weight:500;">· ' + items.length + '</span>') : '';
    return '<div style="margin-bottom:12px;"><div style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">' + title + count + '</div><div>' + chips + addBtn + '</div></div>';
  }}
  let html = '';
  if (p.primaryRole) html += '<div style="font-size:14px;color:#5C5CD6;font-weight:600;margin-bottom:4px;">' + _esc(p.primaryRole) + '</div>';
  if (p.summary) html += '<div style="font-size:13px;color:#555;margin-bottom:14px;line-height:1.45;">' + _esc(p.summary) + '</div>';
  html += '<div style="background:#f8f9fb;padding:14px 16px;border-radius:8px;border:1px solid #e6e8eb;">';
  if (p.seniorityLevel) html += '<div style="font-size:12px;color:#777;margin-bottom:8px;">Seniority: <strong style="color:#333;">' + _esc(p.seniorityLevel) + '</strong>' + (p.salaryFloor ? ' · Salary floor ~$' + Number(p.salaryFloor).toLocaleString() : '') + (p.remotePreferred ? ' · Remote preferred' : '') + '</div>';
  html += section('Target titles', p.targetTitles, '#e6f0ff', 'targetTitles');
  html += section('Industries', p.industries, '#e6fff0', 'industries');
  html += section('Specialties', p.specialties, '#f3e6ff', 'specialties');
  html += section('Key skills', p.keywords, '#fff8e1', 'keywords');
  html += section('Technologies', p.technologies, '#e8f4ff', 'technologies');
  html += section('Frameworks', p.frameworks, '#fff3d6', 'frameworks');
  html += section('Regulations', p.regulations, '#fff0e6', 'regulations');
  html += section('Certifications', p.certifications, '#e6fff8', 'certifications');
  html += section('Preferred locations', p.preferredLocations, '#e6f0ff', 'preferredLocations');
  if (p.remotePreference) {{
    const remoteLabel = ({{'remote-only':'Remote only','hybrid':'Hybrid OK','onsite':'Onsite preferred','any':'Any'}})[p.remotePreference] || p.remotePreference;
    html += section('Remote preference', [remoteLabel], '#ffe6f0', 'remotePreference');
  }} else {{
    html += section('Remote preference', [], '#ffe6f0', 'remotePreference');
  }}
  html += section('Target companies (AI suggested)', (p.targetCompanies||[]).map(function(c){{ return typeof c==='string' ? c : (c.name + (c.atsHint && c.atsHint !== 'unknown' ? ' ('+c.atsHint+')' : '')); }}), '#fef3e8', 'targetCompanies');
  html += section('Filtered out', p.negativeKeywords, '#ffe6e6', 'negativeKeywords');
  html += '</div>';
  if (p.generatedAt) html += '<div style="font-size:11px;color:#999;margin-top:8px;">Generated ' + new Date(p.generatedAt).toLocaleString() + '</div>';
  return html;
}}

const EDITABLE_FIELDS = [
  ['industries', 'Industries'],
  ['specialties', 'Specialties'],
  ['keywords', 'Key skills'],
  ['technologies', 'Technologies'],
  ['frameworks', 'Frameworks'],
  ['regulations', 'Regulations'],
  ['certifications', 'Certifications'],
  ['targetTitles', 'Target titles'],
  ['preferredLocations', 'Preferred locations'],
  ['negativeKeywords', 'Filtered-out terms'],
];

let _currentProfile = null;

function openEditProfileModal() {{
  // Load current profile then render the editor
  fetch(PROFILE_WORKER_URL).then(r => r.json()).then(data => {{
    const p = data.profile || {{}};
    _currentProfile = p;
    const container = document.getElementById('edit-profile-fields');
    container.innerHTML = '';
    EDITABLE_FIELDS.forEach(([key, label]) => {{
      const wrap = document.createElement('div');
      wrap.style.cssText = 'margin-bottom:12px;';
      const labelEl = document.createElement('label');
      labelEl.style.cssText = 'display:block; font-size:12px; font-weight:600; color:#555; margin-bottom:4px;';
      labelEl.textContent = label;
      const input = document.createElement('textarea');
      input.id = 'edit-' + key;
      input.rows = key === 'keywords' || key === 'specialties' ? 3 : 2;
      input.style.cssText = 'width:100%; box-sizing:border-box; padding:7px 10px; font-size:12.5px; border:1px solid #ccd0d6; border-radius:6px; font-family:inherit; resize:vertical;';
      input.value = (Array.isArray(p[key]) ? p[key] : []).join(', ');
      input.placeholder = 'comma-separated, e.g. nist csf, hipaa, iso 27001';
      wrap.appendChild(labelEl);
      wrap.appendChild(input);
      container.appendChild(wrap);
    }});
    document.getElementById('edit-profile-status').textContent = '';
    document.getElementById('edit-profile-overlay').style.display = 'flex';
  }}).catch(e => {{
    alert('Could not load current profile: ' + (e.message || e));
  }});
}}

function closeEditProfileModal() {{
  document.getElementById('edit-profile-overlay').style.display = 'none';
}}

async function saveProfileEdits() {{
  const editKey = getEditKey();
  if (!editKey) return;
  const statusEl = document.getElementById('edit-profile-status');
  statusEl.style.color = '#555';
  statusEl.textContent = 'Saving…';
  const patchFields = {{}};
  EDITABLE_FIELDS.forEach(([key]) => {{
    const v = (document.getElementById('edit-' + key).value || '').trim();
    patchFields[key] = v ? v.split(/[,;\\n]/).map(s => s.trim()).filter(Boolean) : [];
  }});
  try {{
    const r = await fetch(PROFILE_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify({{ patchFields }}),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      statusEl.style.color = '#b00';
      statusEl.textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      return;
    }}
    statusEl.style.color = '#0a6b3a';
    statusEl.textContent = 'Saved. Refreshing dashboard…';
    loadProfile();
    // Trigger refresh so new chips affect filtering
    try {{ await fetch(WORKER_BASE + '/refresh', {{ method: 'POST' }}); }} catch (e) {{ /* ignore */ }}
    setTimeout(() => {{ closeEditProfileModal(); window.location.reload(); }}, 180000);
  }} catch (e) {{
    statusEl.style.color = '#b00';
    statusEl.textContent = 'Failed: ' + (e.message || e);
  }}
}}

async function _patchProfileField(fieldKey, newArray) {{
  const editKey = getEditKey();
  if (!editKey) return false;
  const r = await fetch(PROFILE_WORKER_URL, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    body: JSON.stringify({{ patchFields: {{ [fieldKey]: newArray }} }}),
  }});
  const data = await r.json().catch(() => ({{}}));
  if (!r.ok || data.error) {{
    if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
    alert('Failed: ' + (data.error || ('HTTP ' + r.status)));
    return false;
  }}
  return true;
}}

async function removeChip(fieldKey, value) {{
  if (!confirm('Remove "' + value + '" from your profile?')) return;
  // Read latest profile, drop the item, patch back
  const r = await fetch(PROFILE_WORKER_URL);
  const data = await r.json();
  const profile = data.profile || {{}};
  const existing = Array.isArray(profile[fieldKey]) ? profile[fieldKey] : [];
  const filtered = existing.filter(x => String(x).toLowerCase() !== String(value).toLowerCase());
  if (await _patchProfileField(fieldKey, filtered)) loadProfile();
}}

async function addChip(fieldKey) {{
  const input = prompt('Add to ' + fieldKey + ' (comma-separated for multiple):');
  if (!input) return;
  const additions = input.split(/[,;\\n]/).map(s => s.trim()).filter(Boolean);
  if (!additions.length) return;
  const r = await fetch(PROFILE_WORKER_URL);
  const data = await r.json();
  const profile = data.profile || {{}};
  const existing = Array.isArray(profile[fieldKey]) ? profile[fieldKey] : [];
  const merged = existing.slice();
  const seen = new Set(merged.map(x => String(x).toLowerCase()));
  for (const a of additions) {{
    const al = a.toLowerCase();
    if (!seen.has(al)) {{ merged.push(al); seen.add(al); }}
  }}
  if (await _patchProfileField(fieldKey, merged)) loadProfile();
}}

async function regenerateProfile(btn) {{
  const status = document.getElementById('regen-profile-status');
  const editKey = getEditKey();
  if (!editKey) return;
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = 'Regenerating…';
  status.textContent = '';
  status.style.color = '#555';
  try {{
    const r = await fetch(PROFILE_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      status.style.color = '#b00';
      status.textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    status.style.color = '#0a6b3a';
    status.textContent = 'Regenerated. Refreshing dashboard…';
    btn.textContent = orig;
    btn.disabled = false;
    loadProfile();
    // Trigger dashboard refresh so the richer profile starts filtering jobs
    try {{ await fetch(WORKER_BASE + '/refresh', {{ method: 'POST' }}); }} catch (e) {{ /* ignore */ }}
    setTimeout(() => window.location.reload(), 180000);
  }} catch (e) {{
    status.style.color = '#b00';
    status.textContent = 'Failed: ' + (e.message || e);
    btn.textContent = orig;
    btn.disabled = false;
  }}
}}

async function openResumeModal() {{
  const modal = document.getElementById('resume-modal');
  const statusEl = document.getElementById('resume-status');
  const editor = document.getElementById('resume-editor');
  const textarea = document.getElementById('resume-text');
  document.getElementById('resume-save-status').textContent = '';
  document.getElementById('upload-status').textContent = '';
  document.getElementById('dropzone-label').textContent = 'Click to choose a file';
  document.getElementById('parse-resume-btn').disabled = true;
  _pendingUploadFile = null;
  statusEl.className = 'prep-status';
  statusEl.textContent = 'Loading…';
  statusEl.style.display = 'block';
  editor.style.display = 'none';
  modal.classList.add('show');
  try {{
    const r = await fetch(RESUME_WORKER_URL);
    const data = await r.json();
    if (data.error) {{
      statusEl.className = 'prep-status error';
      statusEl.textContent = 'Error loading resume: ' + data.error;
      return;
    }}
    textarea.value = data.resume || '';
    statusEl.style.display = 'none';
    editor.style.display = 'block';
    setResumeTab('upload');
    if (!data.resume) {{
      document.getElementById('upload-status').textContent = 'No resume saved yet — upload one to begin.';
    }} else {{
      // Week 3: compute + render Resume Health Score (no LLM, fast)
      _renderResumeHealth();
    }}
  }} catch (e) {{
    statusEl.className = 'prep-status error';
    statusEl.textContent = 'Error loading resume: ' + (e.message || e);
  }}
}}

function closeResumeModal() {{
  document.getElementById('resume-modal').classList.remove('show');
}}

// --- File upload + browser-side text extraction -----------------------
function _wireResumeDropzone() {{
  const dz = document.getElementById('resume-dropzone');
  const input = document.getElementById('resume-file-input');
  if (!dz || !input || dz._wired) return;
  dz._wired = true;
  input.addEventListener('change', (e) => {{
    if (e.target.files && e.target.files[0]) _handleFileChosen(e.target.files[0]);
  }});
  ['dragover','dragenter'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.add('drag'); }}));
  ['dragleave','drop'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.remove('drag'); }}));
  dz.addEventListener('drop', (e) => {{
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) _handleFileChosen(e.dataTransfer.files[0]);
  }});
}}

function _handleFileChosen(file) {{
  const name = (file.name || '').toLowerCase();
  if (name.endsWith('.doc') && !name.endsWith('.docx')) {{
    document.getElementById('upload-status').textContent = 'Legacy .doc files are not supported. Open in Word → File → Save As → Word Document (.docx), then upload that.';
    return;
  }}
  if (!name.endsWith('.pdf') && !name.endsWith('.docx')) {{
    document.getElementById('upload-status').textContent = 'Unsupported file. Use PDF or Word (.docx).';
    return;
  }}
  _pendingUploadFile = file;
  document.getElementById('dropzone-label').textContent = file.name;
  document.getElementById('parse-resume-btn').disabled = false;
  document.getElementById('upload-status').textContent = 'Ready. Click Parse & Save.';
}}

async function _extractText(file) {{
  const name = (file.name || '').toLowerCase();
  if (name.endsWith('.docx')) {{
    const buf = await file.arrayBuffer();
    const res = await window.mammoth.extractRawText({{ arrayBuffer: buf }});
    return (res && res.value || '').trim();
  }}
  if (name.endsWith('.pdf')) {{
    if (!window.pdfjsLib) throw new Error('PDF parser failed to load.');
    const buf = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({{ data: buf }}).promise;
    let out = '';
    for (let i = 1; i <= pdf.numPages; i++) {{
      const page = await pdf.getPage(i);
      const tc = await page.getTextContent();
      out += tc.items.map(it => it.str).join(' ') + '\\n\\n';
    }}
    return out.trim();
  }}
  throw new Error('Unsupported file type.');
}}

async function parseUploadedResume(btn) {{
  if (!_pendingUploadFile) return;
  const statusEl = document.getElementById('upload-status');
  const editKey = getEditKey();
  if (!editKey) return;
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Reading file…';
  statusEl.textContent = '';
  try {{
    const text = await _extractText(_pendingUploadFile);
    if (!text || text.length < 80) {{
      statusEl.textContent = 'Could not extract text from this file. Try saving as .docx, or use Edit JSON tab.';
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    btn.textContent = 'Parsing with Claude…';
    const r = await fetch(PARSE_RESUME_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify({{ text, filename: _pendingUploadFile.name }}),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      statusEl.textContent = 'Failed: ' + (data.error || ('HTTP ' + r.status));
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    statusEl.textContent = 'Saved as new version (' + (data.version && data.version.label || 'new') + ') and activated.';
    if (data.parsed) {{
      const ta = document.getElementById('resume-text');
      if (ta) ta.value = JSON.stringify(data.parsed, null, 2);
    }}
    btn.textContent = orig;
    btn.disabled = false;
    _pendingUploadFile = null;
    document.getElementById('resume-file-input').value = '';
    document.getElementById('dropzone-label').textContent = 'Upload another to replace';
    // Slice D: after resume upload, auto-launch the wizard so the user captures
    // their preferences (titles/industries/skills weights, locations, sizes, etc.)
    try {{
      setTimeout(function() {{
        try {{ closeResumeModal(); }} catch(e) {{}}
        try {{ localStorage.removeItem('gmj_wizard_seen_v2'); }} catch(e) {{}}
        var startIdx = 0;
        try {{
          for (var i = 0; i < WIZ_STEPS.length; i++) {{
            var act = (WIZ_STEPS[i] && WIZ_STEPS[i].action) || '';
            if (act === 'open-resume-profile' || act === 'save-profile-chips' ||
                act === 'save-location-remote') {{ startIdx = i; break; }}
          }}
        }} catch(e) {{}}
        if (typeof wizCurrent !== 'undefined') wizCurrent = startIdx;
        if (typeof wizShow === 'function') wizShow();
        if (typeof wizRender === 'function') wizRender();
      }}, 800);
    }} catch(e) {{ /* if wizard absent, skip silently */ }}
  }} catch (e) {{
    statusEl.textContent = 'Failed: ' + (e.message || e);
    btn.textContent = orig;
    btn.disabled = false;
  }}
}}

// --- Versions list ------------------------------------------------------
async function loadVersions() {{
  const list = document.getElementById('versions-list');
  list.innerHTML = '<p style="font-size:12px;color:#888;">Loading versions…</p>';
  try {{
    const r = await fetch(VERSIONS_WORKER_URL);
    const data = await r.json();
    if (data.error) {{
      list.innerHTML = '<p style="font-size:12px;color:#b00;">Error: ' + data.error + '</p>';
      return;
    }}
    const versions = data.versions || [];
    const activeId = data.activeId;
    if (!versions.length) {{
      list.innerHTML = '<p style="font-size:12px;color:#888;">No versions yet. Upload a file or paste JSON to create one.</p>';
      return;
    }}
    list.innerHTML = versions.map(v => {{
      const isActive = v.id === activeId;
      const dt = new Date(v.savedAt);
      const when = isNaN(dt) ? v.savedAt : dt.toLocaleString();
      const src = v.sourceType === 'upload' ? 'uploaded' : 'JSON paste';
      return '<div class="version-row' + (isActive ? ' active' : '') + '">' +
             '<div class="version-main">' +
             '<div class="version-label">' + _esc(v.label) + (isActive ? ' <span class="version-badge">Active</span>' : '') + '</div>' +
             '<div class="version-meta">' + src + ' · ' + when + '</div>' +
             '</div>' +
             '<div class="version-actions">' +
             (isActive ? '' : '<button class="v-btn primary" onclick="activateVersion(\\''+ v.id +'\\')">Activate</button>') +
             '<button class="v-btn" onclick="previewVersion(\\''+ v.id +'\\')">Preview</button>' +
             '<button class="v-btn" onclick="renameVersion(\\''+ v.id +'\\', \\''+ _esc(v.label).replace(/'/g,"\\\\'") +'\\')">Rename</button>' +
             (isActive ? '' : '<button class="v-btn danger" onclick="deleteVersion(\\''+ v.id +'\\')">Delete</button>') +
             '</div></div>';
    }}).join('');
  }} catch (e) {{
    list.innerHTML = '<p style="font-size:12px;color:#b00;">Error: ' + (e.message || e) + '</p>';
  }}
}}

function _esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}

async function _versionAction(action, body) {{
  const editKey = getEditKey();
  if (!editKey) return null;
  const r = await fetch(VERSIONS_WORKER_URL, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    body: JSON.stringify(body),
  }});
  const data = await r.json().catch(() => ({{}}));
  if (!r.ok || data.error) {{
    if (r.status === 401) localStorage.removeItem('htj_resume_key');
    alert('Failed: ' + (data.error || ('HTTP ' + r.status)));
    return null;
  }}
  return data;
}}

async function activateVersion(id) {{
  const data = await _versionAction('activate', {{ action: 'activate', id }});
  if (!data) return;
  // Update UI immediately
  loadVersions();
  // Auto-trigger a dashboard refresh so the user actually sees the change.
  // Without this, Activate seems to "do nothing" since the visible dashboard
  // is a pre-generated static HTML file.
  const list = document.getElementById('versions-list');
  if (list) {{
    const banner = document.createElement('div');
    banner.style.cssText = 'background:#fff8e1;border:1px solid #f6c93b;border-radius:6px;padding:10px 12px;margin:8px 0 0 0;font-size:13px;color:#5a4400;';
    banner.innerHTML = 'Activated. Refreshing your dashboard — page will reload automatically in about 3 minutes.';
    list.appendChild(banner);
  }}
  try {{
    await fetch(WORKER_BASE + '/refresh', {{ method: 'POST' }});
  }} catch (e) {{ /* ignore — page reload below still helps */ }}
  // After flipping the active resume, auto-launch the wizard so the user can
  // re-confirm their preferences (the new resume may have different signals).
  try {{
    setTimeout(function() {{
      try {{ closeResumeModal(); }} catch(e) {{}}
      try {{ localStorage.removeItem('gmj_wizard_seen_v2'); }} catch(e) {{}}
      var startIdx = 0;
      try {{
        for (var i = 0; i < WIZ_STEPS.length; i++) {{
          var act = (WIZ_STEPS[i] && WIZ_STEPS[i].action) || '';
          if (act === 'open-resume-profile' || act === 'save-profile-chips' ||
              act === 'save-location-remote') {{ startIdx = i; break; }}
        }}
      }} catch(e) {{}}
      if (typeof wizCurrent !== 'undefined') wizCurrent = startIdx;
      if (typeof wizShow === 'function') wizShow();
      if (typeof wizRender === 'function') wizRender();
    }}, 800);
  }} catch(e) {{ /* if wizard absent, skip silently */ }}
  // Auto-reload after the GH Action should have finished (3 min is a safe estimate)
  setTimeout(() => window.location.reload(), 180000);
}}

async function deleteVersion(id) {{
  if (!confirm('Delete this version? This cannot be undone.')) return;
  const data = await _versionAction('delete', {{ action: 'delete', id }});
  if (data) loadVersions();
}}

async function previewVersion(id) {{
  const editKey = getEditKey();
  if (!editKey) return;
  const r = await fetch(VERSIONS_WORKER_URL, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
    body: JSON.stringify({{ action: 'get', id }}),
  }});
  const data = await r.json().catch(() => ({{}}));
  if (!r.ok || data.error) {{ alert('Failed: ' + (data.error || ('HTTP ' + r.status))); return; }}
  setResumeTab('json');
  const ta = document.getElementById('resume-text');
  if (ta) ta.value = data.resume || '';
  document.getElementById('resume-save-status').textContent = 'Previewing version. Save to create a new version from this content.';
}}

async function renameVersion(id, currentLabel) {{
  const label = prompt('New label for this version:', currentLabel || '');
  if (label == null) return;
  const data = await _versionAction('rename', {{ action: 'rename', id, label }});
  if (data) loadVersions();
}}

async function saveResume(btn) {{
  const textarea = document.getElementById('resume-text');
  const statusEl = document.getElementById('resume-save-status');
  const value = textarea.value.trim();
  if (!value) {{
    statusEl.textContent = 'Resume is empty — paste content first.';
    return;
  }}
  // Light validation: should be JSON with a personal section
  try {{
    const parsed = JSON.parse(value);
    if (!parsed.personal) throw new Error('Resume JSON should include a "personal" key.');
  }} catch (e) {{
    if (!confirm('This does not look like valid resume JSON (' + e.message + '). Save anyway?')) return;
  }}
  const editKey = getEditKey();
  if (!editKey) return;
  btn.disabled = true;
  const orig = btn.textContent;
  btn.textContent = 'Saving…';
  statusEl.textContent = '';
  try {{
    // Default label is timestamp so users don't accidentally save the example text
    const now = new Date();
    const defaultLabel = 'Manual edit — ' + now.toLocaleDateString();
    const label = prompt('Label for this version:', defaultLabel) || defaultLabel;
    const r = await fetch(RESUME_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': editKey }},
      body: JSON.stringify({{ resume: value, label, sourceType: 'json-paste' }}),
    }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      if (r.status === 401) {{ localStorage.removeItem('htj_resume_key'); localStorage.removeItem('htj_resume_key_' + USER_SLUG); }}
      statusEl.textContent = 'Save failed: ' + (data.error || ('HTTP ' + r.status));
      btn.disabled = false;
      btn.textContent = orig;
      return;
    }}
    statusEl.textContent = 'Saved as new version.';
    btn.textContent = orig;
    btn.disabled = false;
  }} catch (e) {{
    statusEl.textContent = 'Save failed: ' + (e.message || e);
    btn.disabled = false;
    btn.textContent = orig;
  }}
}}

// Wire dropzone after DOM is ready
if (document.readyState !== 'loading') _wireResumeDropzone();
else document.addEventListener('DOMContentLoaded', _wireResumeDropzone);

// --- Header "More" menu toggle (added 2026-05-26 with header redesign) ----
function toggleHeaderMore(btn) {{
  const wrap = btn.closest('.header-more-wrap');
  if (!wrap) return;
  const willOpen = !wrap.classList.contains('open');
  // Close any other open menus first
  document.querySelectorAll('.header-more-wrap.open').forEach(w => w.classList.remove('open'));
  if (willOpen) {{
    wrap.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
  }} else {{
    btn.setAttribute('aria-expanded', 'false');
  }}
}}
document.addEventListener('click', function(e) {{
  if (!e.target.closest('.header-more-wrap')) {{
    document.querySelectorAll('.header-more-wrap.open').forEach(function(w) {{
      w.classList.remove('open');
      const b = w.querySelector('button[aria-haspopup]');
      if (b) b.setAttribute('aria-expanded', 'false');
    }});
  }}
}});

// --- Sign out (added 2026-05-26 hotfix: signOutDashboard was referenced but never defined) ---
async function signOutDashboard(btn) {{
  if (btn) {{ btn.disabled = true; btn.textContent = 'Signing out…'; }}
  const TOKEN_KEY = 'gmj_session_token';
  try {{
    const tok = localStorage.getItem(TOKEN_KEY);
    if (tok) {{
      await fetch(WORKER_BASE + '/api/auth/logout', {{
        method: 'POST',
        headers: {{ 'Authorization': 'Bearer ' + tok }}
      }}).catch(function(){{}});
    }}
  }} catch (e) {{}}
  // Clear everything that might leak identity into the next session
  try {{
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem('htj_resume_key');
    localStorage.removeItem('htj_resume_key_' + USER_SLUG);
    localStorage.removeItem('htj_admin_key');
    localStorage.removeItem('gmj_last_user');
  }} catch (e) {{}}
  location.replace('/login.html');
}}

// --- Refresh data (triggers GitHub Action via Cloudflare Worker) --------
const REFRESH_WORKER_URL = WORKER_BASE + '/refresh';

async function refreshData() {{
  const btn = document.getElementById('refresh-btn');
  if (!btn) return;
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Triggering refresh…';
  try {{
    const r = await fetch(REFRESH_WORKER_URL, {{ method: 'POST' }});
    const data = await r.json().catch(() => ({{}}));
    if (!r.ok || data.error) {{
      btn.textContent = 'Refresh failed';
      alert('Refresh failed: ' + (data.error || ('HTTP ' + r.status)) + (data.details ? '\\n' + data.details : ''));
      setTimeout(() => {{ btn.textContent = original; btn.disabled = false; }}, 3000);
      return;
    }}
  }} catch (e) {{
    btn.textContent = 'Refresh failed';
    alert('Refresh failed: ' + (e.message || e));
    setTimeout(() => {{ btn.textContent = original; btn.disabled = false; }}, 3000);
    return;
  }}
  // Countdown then reload
  let secs = 150;
  const tick = () => {{
    btn.textContent = `Fetching jobs… ${{secs}}s, page will reload`;
    secs--;
    if (secs <= 0) {{
      window.location.reload();
    }} else {{
      setTimeout(tick, 1000);
    }}
  }};
  tick();
}}

// --- Prep modal (calls Cloudflare Worker for AI generation) -------------
const PREP_WORKER_URL = WORKER_BASE + '/prep' + USER_QS;

async function prepApplication(fp, btn) {{
  // === DIAGNOSTIC WRAPPER (2026-05-26): surfaces silent failures with visible error ===
  function _prepFail(msg) {{
    console.error('[prepApplication]', msg);
    const _s = document.getElementById('prep-status');
    const _m = document.getElementById('prep-modal');
    if (_s && _m) {{
      _s.className = 'prep-status error';
      _s.textContent = msg;
      _s.style.display = 'block';
      _m.classList.add('show');
    }} else {{
      alert('Prep materials failed: ' + msg);
    }}
  }}
  console.log('[prepApplication] click', {{ fp }});
  const card = btn && btn.closest && btn.closest('.card');
  if (!card) {{ _prepFail('clicked button is not inside a .card element'); return; }}

  const titleEl = card.querySelector('.title a');
  const jobTitle = (titleEl?.textContent || '').trim();
  const company = (card.querySelector('.company')?.textContent || '').trim();
  const jobUrl = titleEl?.href || '';
  const jobDescription = (card.querySelector('.desc')?.textContent || '').trim();

  const modal = document.getElementById('prep-modal');
  const statusEl = document.getElementById('prep-status');
  const outputEl = document.getElementById('prep-output');
  const titleH = document.getElementById('prep-modal-title');
  if (!modal || !statusEl || !outputEl || !titleH) {{
    _prepFail('modal elements missing: modal=' + !!modal + ' status=' + !!statusEl + ' output=' + !!outputEl + ' titleH=' + !!titleH);
    return;
  }}

  titleH.textContent = `Materials for ${{jobTitle}} @ ${{company}}`;
  statusEl.className = 'prep-status';
  statusEl.textContent = 'Generating with Claude… this takes 10–30 seconds.';
  statusEl.style.display = 'block';
  outputEl.style.display = 'none';
  modal.classList.add('show');

  try {{
    const r = await fetch(PREP_WORKER_URL, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ jobTitle, company, jobDescription, jobUrl }}),
    }});
    const data = await r.json();
    if (!r.ok || data.error) {{
      statusEl.className = 'prep-status error';
      statusEl.textContent = `Error: ${{data.error || ('HTTP ' + r.status)}}${{data.details ? ' — ' + data.details : ''}}`;
      return;
    }}
    document.getElementById('prep-summary').textContent = data.summary || '(no summary returned)';
    document.getElementById('prep-cover').textContent = data.coverLetter || '(no cover letter returned)';
    document.getElementById('prep-linkedin').textContent = data.linkedin || '(no LinkedIn intro returned)';
    // Week 1: render keyword diff section
    _renderKeywordDiff(data.keywordDiff);
    // Week 2: render six-second scan + cover paragraph
    _renderSixSecondScan(data.sixSecondScan);
    _renderCoverParagraph(data.coverParagraph);
    _tailoredResume = data.tailoredResume || null;
    _tailoredJobMeta = {{ jobTitle, company }};
    const tailoredSection = document.getElementById('prep-resume-section');
    if (_tailoredResume && _tailoredResume.personal) {{
      document.getElementById('prep-resume-preview').innerHTML = _renderResumeHTML(_tailoredResume);
      tailoredSection.style.display = 'block';
    }} else {{
      tailoredSection.style.display = 'none';
    }}
    statusEl.style.display = 'none';
    outputEl.style.display = 'block';
    // Auto-save the prep kit to the tracker so user can re-open without regenerating
    const kit = {{ summary: data.summary, coverLetter: data.coverLetter, linkedin: data.linkedin, tailoredResume: data.tailoredResume, keywordDiff: data.keywordDiff, sixSecondScan: data.sixSecondScan, coverParagraph: data.coverParagraph }};
    if (getEditKey()) {{
      _trackerAction('savePrepKit', {{ fp, jobMeta: {{ title: jobTitle, company, url: jobUrl }}, prepKit: kit }}).then(r => {{
        if (r && r.record) _trackerCache[fp] = r.record;
      }});
    }}
  }} catch (e) {{
    statusEl.className = 'prep-status error';
    statusEl.textContent = `Error: ${{e.message || e}}`;
  }}
}}
function closeModal() {{ document.getElementById('prep-modal').classList.remove('show'); }}
// === Week 1: Keyword diff renderer ====================================
let _lastKeywordDiff = null;
function _renderKeywordDiff(kd) {{
  _lastKeywordDiff = kd;
  const section = document.getElementById('prep-keyword-section');
  const table = document.getElementById('prep-keyword-table');
  const summary = document.getElementById('prep-keyword-summary');
  if (!section || !table) return;
  if (!kd || (!Array.isArray(kd.matched) && !Array.isArray(kd.missing))) {{
    section.style.display = 'none';
    return;
  }}
  const matched = Array.isArray(kd.matched) ? kd.matched : [];
  const missing = Array.isArray(kd.missing) ? kd.missing : [];
  const total = matched.length + missing.length;
  if (total === 0) {{ section.style.display = 'none'; return; }}
  summary.textContent = matched.length + ' of ' + total + ' recruiter-search keywords already in your resume';
  function esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }}[c])); }}
  let html = '';
  html += '<table style="width:100%;border-collapse:collapse;font-size:13px;">';
  html += '<thead><tr style="text-align:left;color:#666;font-size:11px;text-transform:uppercase;letter-spacing:0.04em;border-bottom:1px solid #e2e5ea;">' +
          '<th style="padding:8px 12px;">Required by JD</th>' +
          '<th style="padding:8px 12px;">In your resume</th>' +
          '<th style="padding:8px 12px;">Fix</th>' +
          '</tr></thead><tbody>';
  matched.forEach(m => {{
    const occ = m.occurrences ? '<span style="color:#666;font-size:11.5px;">(' + m.occurrences + '×)</span>' : '';
    html += '<tr style="border-bottom:1px solid #f4f5f7;">' +
      '<td style="padding:8px 12px;font-weight:600;">' + esc(m.term) + '</td>' +
      '<td style="padding:8px 12px;color:#0a6b3a;">✓ matched ' + occ + '</td>' +
      '<td style="padding:8px 12px;color:#aaa;">—</td>' +
      '</tr>';
  }});
  missing.forEach(m => {{
    const altLine = m.alternative
      ? '<span style="color:#a55;">paraphrase: <em>' + esc(m.alternative) + '</em>' + (m.alternativeOccurrences ? ' (' + m.alternativeOccurrences + '×)' : '') + '</span>'
      : '<span style="color:#999;">not present</span>';
    html += '<tr style="border-bottom:1px solid #f4f5f7;background:#fff7e6;">' +
      '<td style="padding:8px 12px;font-weight:600;">' + esc(m.required) + '</td>' +
      '<td style="padding:8px 12px;">' + altLine + '</td>' +
      '<td style="padding:8px 12px;color:#444;">' + esc(m.fix || '') + '</td>' +
      '</tr>';
  }});
  html += '</tbody></table>';
  table.innerHTML = html;
  section.style.display = 'block';
}}

// === Week 2: Six-second scan renderer ================================
function _renderSixSecondScan(scan) {{
  const section = document.getElementById('prep-scan-section');
  const body = document.getElementById('prep-scan-body');
  if (!section || !body) return;
  if (!scan || typeof scan !== 'object') {{ section.style.display = 'none'; return; }}
  function esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }}[c])); }}
  const alignmentColor = {{ 'aligned': '#0a6b3a', 'one level off': '#78350f', 'two+ levels off': '#B91C1C' }}[scan.titleAlignment] || '#444';
  let html = '';
  html += '<div style="margin-bottom:10px;">';
  html += '<strong>Title line:</strong> ' + esc(scan.titleObserved || '(not detected)');
  html += '  <span style="color:' + alignmentColor + ';font-weight:600;">[' + esc(scan.titleAlignment || 'unknown') + ']</span>';
  html += '</div>';
  if (scan.titleSuggestion) {{
    html += '<div style="margin-bottom:10px;padding:8px 10px;background:#fff7e6;border:1px solid #fcd34d;border-radius:6px;font-size:12.5px;">';
    html += '<strong>Suggested subtitle:</strong> <code style="background:#fff;padding:2px 6px;border-radius:4px;">' + esc(scan.titleSuggestion) + '</code>';
    html += '</div>';
  }}
  if (scan.topBulletsCritique) {{
    html += '<div style="margin-bottom:10px;color:#555;"><strong>Top-bullet read:</strong> ' + esc(scan.topBulletsCritique) + '</div>';
  }}
  const rewrites = Array.isArray(scan.rewrites) ? scan.rewrites : [];
  if (rewrites.length) {{
    html += '<div style="font-size:12px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.04em;margin-top:14px;margin-bottom:6px;">Suggested rewrites</div>';
    rewrites.forEach(rw => {{
      html += '<div style="margin-bottom:12px;padding:10px;background:#f7f8fb;border:1px solid #e2e5ea;border-radius:6px;">';
      html += '<div style="font-size:11.5px;color:#a55;margin-bottom:4px;">BEFORE</div>';
      html += '<div style="font-size:13px;color:#444;margin-bottom:8px;">' + esc(rw.original || '') + '</div>';
      html += '<div style="font-size:11.5px;color:#0a6b3a;margin-bottom:4px;">AFTER</div>';
      html += '<div style="font-size:13px;color:#1a1a2e;margin-bottom:6px;font-weight:500;">' + esc(rw.suggested || '') + '</div>';
      if (rw.why) html += '<div style="font-size:11.5px;color:#666;font-style:italic;">Why: ' + esc(rw.why) + '</div>';
      html += '</div>';
    }});
  }}
  body.innerHTML = html;
  section.style.display = 'block';
}}

// === Week 2: Cover paragraph renderer ================================
function _renderCoverParagraph(text) {{
  const section = document.getElementById('prep-coverpara-section');
  const pre = document.getElementById('prep-coverpara');
  if (!section || !pre) return;
  if (!text || typeof text !== 'string' || !text.trim()) {{ section.style.display = 'none'; return; }}
  pre.textContent = text;
  section.style.display = 'block';
}}

function copyKeywordFixList(btn) {{
  const kd = _lastKeywordDiff;
  if (!kd) return;
  const lines = [];
  if (Array.isArray(kd.missing) && kd.missing.length) {{
    lines.push('--- Add / swap to match this JD ---');
    kd.missing.forEach(m => {{
      lines.push(m.required + (m.alternative ? '  (you currently say: ' + m.alternative + ')' : '  (not in resume)'));
      if (m.fix) lines.push('  → ' + m.fix);
    }});
  }}
  if (Array.isArray(kd.matched) && kd.matched.length) {{
    lines.push('');
    lines.push('--- Already matched ---');
    kd.matched.forEach(m => lines.push('✓ ' + m.term + (m.occurrences ? ' (' + m.occurrences + '×)' : '')));
  }}
  navigator.clipboard.writeText(lines.join('\\n')).then(() => {{
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }});
}}

function copyPrepField(id, btn) {{
  const txt = document.getElementById(id).textContent;
  navigator.clipboard.writeText(txt).then(() => {{
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }});
}}

// --- Tailored resume rendering + downloads ----------------------------
let _tailoredResume = null;
let _tailoredJobMeta = {{ jobTitle: '', company: '' }};

function _escHtml(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}

function _renderResumeHTML(r) {{
  if (!r || !r.personal) return '';
  const p = r.personal || {{}};
  const contact = [p.location, p.phone, p.email, p.linkedin].filter(Boolean).map(x => _escHtml(x)).join(' &nbsp;·&nbsp; ');
  let html = '';
  html += '<div style="text-align:center; margin-bottom:14px;">';
  html += '<div style="font-size:20px; font-weight:700; color:#5C5CD6; letter-spacing:0.3px;">' + _escHtml(p.name || '') + '</div>';
  if (contact) html += '<div style="font-size:11.5px; color:#555; margin-top:4px;">' + contact + '</div>';
  html += '</div>';
  if (r.summary) {{
    html += '<div style="margin-bottom:12px;">' + _escHtml(r.summary) + '</div>';
  }}
  if (r.skills && r.skills.length) {{
    html += '<div style="margin-bottom:14px;"><div style="font-weight:700; color:#5C5CD6; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #d0d6e0; padding-bottom:3px; margin-bottom:6px;">Core Skills</div>';
    html += '<div style="font-size:12.5px;">' + r.skills.map(s => _escHtml(s)).join(' &nbsp;·&nbsp; ') + '</div></div>';
  }}
  if (r.experience && r.experience.length) {{
    html += '<div style="margin-bottom:14px;"><div style="font-weight:700; color:#5C5CD6; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #d0d6e0; padding-bottom:3px; margin-bottom:6px;">Experience</div>';
    r.experience.forEach(exp => {{
      html += '<div style="margin-bottom:10px;">';
      html += '<div style="display:flex; justify-content:space-between; gap:10px;"><div><strong>' + _escHtml(exp.title || '') + '</strong> — ' + _escHtml(exp.company || '') + (exp.location ? '<span style="color:#666;"> (' + _escHtml(exp.location) + ')</span>' : '') + '</div>';
      html += '<div style="color:#666; font-size:11.5px; white-space:nowrap;">' + _escHtml(exp.start || '') + ' – ' + _escHtml(exp.end || '') + '</div></div>';
      if (exp.bullets && exp.bullets.length) {{
        html += '<ul style="margin:4px 0 0 18px; padding:0;">';
        exp.bullets.forEach(b => {{ html += '<li style="margin-bottom:2px;">' + _escHtml(b) + '</li>'; }});
        html += '</ul>';
      }}
      html += '</div>';
    }});
    html += '</div>';
  }}
  if (r.education && r.education.length) {{
    html += '<div style="margin-bottom:12px;"><div style="font-weight:700; color:#5C5CD6; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #d0d6e0; padding-bottom:3px; margin-bottom:6px;">Education</div>';
    r.education.forEach(ed => {{
      const line = [ed.degree, ed.field].filter(Boolean).join(' in ');
      html += '<div style="margin-bottom:4px;">' + _escHtml(line) + (ed.school ? ' — ' + _escHtml(ed.school) : '') + (ed.year ? ' <span style="color:#666;">(' + _escHtml(ed.year) + ')</span>' : '') + '</div>';
    }});
    html += '</div>';
  }}
  if (r.certifications && r.certifications.length) {{
    html += '<div><div style="font-weight:700; color:#5C5CD6; font-size:12px; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #d0d6e0; padding-bottom:3px; margin-bottom:6px;">Certifications</div>';
    html += '<div>' + r.certifications.map(c => _escHtml(c)).join(' &nbsp;·&nbsp; ') + '</div></div>';
  }}
  return html;
}}

function _resumeToText(r) {{
  if (!r || !r.personal) return '';
  const p = r.personal || {{}};
  const lines = [];
  lines.push((p.name || '').toUpperCase());
  const contact = [p.location, p.phone, p.email, p.linkedin].filter(Boolean).join(' · ');
  if (contact) lines.push(contact);
  lines.push('');
  if (r.summary) {{ lines.push('SUMMARY'); lines.push(r.summary); lines.push(''); }}
  if (r.skills && r.skills.length) {{ lines.push('CORE SKILLS'); lines.push(r.skills.join(' · ')); lines.push(''); }}
  if (r.experience && r.experience.length) {{
    lines.push('EXPERIENCE');
    r.experience.forEach(exp => {{
      const dates = [exp.start, exp.end].filter(Boolean).join(' – ');
      lines.push((exp.title || '') + ' — ' + (exp.company || '') + (exp.location ? ' (' + exp.location + ')' : '') + (dates ? '  [' + dates + ']' : ''));
      (exp.bullets || []).forEach(b => lines.push('  • ' + b));
      lines.push('');
    }});
  }}
  if (r.education && r.education.length) {{
    lines.push('EDUCATION');
    r.education.forEach(ed => {{
      const line = [ed.degree, ed.field].filter(Boolean).join(' in ');
      lines.push(line + (ed.school ? ' — ' + ed.school : '') + (ed.year ? ' (' + ed.year + ')' : ''));
    }});
    lines.push('');
  }}
  if (r.certifications && r.certifications.length) {{
    lines.push('CERTIFICATIONS');
    lines.push(r.certifications.join(' · '));
  }}
  return lines.join('\\n');
}}

function _resumeFilename(ext) {{
  const company = (_tailoredJobMeta.company || 'company').replace(/[^a-z0-9]+/gi,'_').replace(/^_|_$/g,'').slice(0, 30);
  const name = (_tailoredResume && _tailoredResume.personal && _tailoredResume.personal.name) ? _tailoredResume.personal.name.replace(/[^a-z0-9]+/gi,'_').replace(/^_|_$/g,'') : 'Resume';
  return name + '_' + company + '.' + ext;
}}

function copyTailoredResume(btn) {{
  if (!_tailoredResume) return;
  const text = _resumeToText(_tailoredResume);
  navigator.clipboard.writeText(text).then(() => {{
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }});
}}

function _buildPrintableHTML(r) {{
  // Letter-paper friendly HTML. Word opens HTML-with-.doc-extension natively.
  return `<!doctype html><html><head><meta charset="utf-8"><title>${{_escHtml((r.personal && r.personal.name) || 'Resume')}}</title>` +
         `<style>body{{font-family:Calibri,Arial,sans-serif;color:#222;font-size:11pt;line-height:1.4;margin:32px 40px;}}` +
         `h1{{font-size:18pt;margin:0 0 4px 0;color:#5C5CD6;text-align:center;letter-spacing:.5px;}}` +
         `.contact{{text-align:center;font-size:10pt;color:#555;margin-bottom:14px;}}` +
         `h2{{font-size:11pt;color:#5C5CD6;text-transform:uppercase;letter-spacing:.6px;border-bottom:1px solid #c0c8d4;padding-bottom:2px;margin:14px 0 6px 0;}}` +
         `.role{{display:flex;justify-content:space-between;gap:10px;font-weight:bold;margin-top:8px;}}` +
         `.dates{{color:#666;font-weight:normal;font-size:10pt;}}` +
         `ul{{margin:4px 0 0 20px;padding:0;}}li{{margin-bottom:2px;}}p{{margin:0 0 6px 0;}}` +
         `</style></head><body>` +
         _renderResumeForPrint(r) +
         `</body></html>`;
}}

function _renderResumeForPrint(r) {{
  const p = r.personal || {{}};
  const contact = [p.location, p.phone, p.email, p.linkedin].filter(Boolean).map(x => _escHtml(x)).join(' &nbsp;·&nbsp; ');
  let html = '';
  html += '<h1>' + _escHtml(p.name || '') + '</h1>';
  if (contact) html += '<div class="contact">' + contact + '</div>';
  if (r.summary) {{ html += '<h2>Summary</h2><p>' + _escHtml(r.summary) + '</p>'; }}
  if (r.skills && r.skills.length) {{ html += '<h2>Core Skills</h2><p>' + r.skills.map(s => _escHtml(s)).join(' &nbsp;·&nbsp; ') + '</p>'; }}
  if (r.experience && r.experience.length) {{
    html += '<h2>Experience</h2>';
    r.experience.forEach(exp => {{
      const dates = [exp.start, exp.end].filter(Boolean).map(x => _escHtml(x)).join(' – ');
      html += '<div class="role"><div>' + _escHtml(exp.title || '') + ' — ' + _escHtml(exp.company || '');
      if (exp.location) html += ' <span style="color:#666;font-weight:normal;">(' + _escHtml(exp.location) + ')</span>';
      html += '</div><div class="dates">' + dates + '</div></div>';
      if (exp.bullets && exp.bullets.length) {{
        html += '<ul>';
        exp.bullets.forEach(b => {{ html += '<li>' + _escHtml(b) + '</li>'; }});
        html += '</ul>';
      }}
    }});
  }}
  if (r.education && r.education.length) {{
    html += '<h2>Education</h2>';
    r.education.forEach(ed => {{
      const line = [ed.degree, ed.field].filter(Boolean).map(x => _escHtml(x)).join(' in ');
      html += '<p>' + line + (ed.school ? ' — ' + _escHtml(ed.school) : '') + (ed.year ? ' <span style="color:#666;">(' + _escHtml(ed.year) + ')</span>' : '') + '</p>';
    }});
  }}
  if (r.certifications && r.certifications.length) {{
    html += '<h2>Certifications</h2><p>' + r.certifications.map(c => _escHtml(c)).join(' &nbsp;·&nbsp; ') + '</p>';
  }}
  return html;
}}

async function downloadTailoredResume(format, btn) {{
  if (!_tailoredResume) return;
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Building…';
  try {{
    if (format === 'pdf') {{
      const html = _buildPrintableHTML(_tailoredResume);
      const container = document.createElement('div');
      container.innerHTML = html;
      // html2pdf needs the actual content node, not the full <html>
      const node = container.querySelector('body') ? container : container;
      await html2pdf().set({{
        margin: [10, 10, 10, 10],
        filename: _resumeFilename('pdf'),
        image: {{ type: 'jpeg', quality: 0.98 }},
        html2canvas: {{ scale: 2, useCORS: true }},
        jsPDF: {{ unit: 'mm', format: 'letter', orientation: 'portrait' }},
        pagebreak: {{ mode: ['css', 'legacy'] }},
      }}).from(node).save();
    }} else if (format === 'doc') {{
      const html = _buildPrintableHTML(_tailoredResume);
      // Use MIME type Word recognises for HTML; saved as .doc opens directly in Word.
      const blob = new Blob(['\\ufeff' + html], {{ type: 'application/msword' }});
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = _resumeFilename('doc');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    }}
    btn.textContent = 'Downloaded!';
    setTimeout(() => {{ btn.textContent = orig; btn.disabled = false; }}, 1500);
  }} catch (e) {{
    alert('Download failed: ' + (e.message || e));
    btn.textContent = orig;
    btn.disabled = false;
  }}
}}

// --- LinkedIn Contacts feature ----------------------------------------
const LINKEDIN_CONTACTS_KEY = 'htj_linkedin_contacts_' + USER_SLUG;
const LINKEDIN_CONTACTS_META_KEY = 'htj_linkedin_contacts_meta_' + USER_SLUG;
let _pendingContactsFile = null;
let _contactsByCompany = null; // {{ normalizedCompany: [contact, ...] }}

function _normalizeCompany(name) {{
  if (!name) return '';
  let s = String(name).toLowerCase().trim();
  // strip leading "the "
  s = s.replace(/^the\s+/, '');
  // strip trailing punctuation
  s = s.replace(/[.,;:!?]+$/g, '');
  // strip common legal suffixes (with or without comma/period)
  s = s.replace(/[,]?\s*(inc|incorporated|llc|l\.l\.c\.|corp|corporation|co|company|ltd|limited|gmbh|plc|holdings|group|partners)\s*\.?$/g, '');
  // collapse whitespace
  s = s.replace(/\s+/g, ' ').trim();
  return s;
}}

function _companiesMatch(a, b) {{
  const na = _normalizeCompany(a);
  const nb = _normalizeCompany(b);
  if (!na || !nb) return false;
  if (na === nb) return true;
  // prefix/contains match — require shorter side >= 5 chars to avoid false positives
  const shorter = na.length <= nb.length ? na : nb;
  const longer = na.length <= nb.length ? nb : na;
  if (shorter.length < 5) return false;
  // word-boundary contains
  if (longer.startsWith(shorter + ' ') || longer.endsWith(' ' + shorter) || longer.includes(' ' + shorter + ' ')) return true;
  return false;
}}

// Parse a CSV line respecting quoted fields. Returns array of strings.
function _csvSplitLine(line) {{
  const out = [];
  let cur = '';
  let inQ = false;
  for (let i = 0; i < line.length; i++) {{
    const c = line[i];
    if (inQ) {{
      if (c === '"') {{
        if (line[i+1] === '"') {{ cur += '"'; i++; }}
        else inQ = false;
      }} else cur += c;
    }} else {{
      if (c === ',') {{ out.push(cur); cur = ''; }}
      else if (c === '"') inQ = true;
      else cur += c;
    }}
  }}
  out.push(cur);
  return out;
}}

// Parse a LinkedIn Connections.csv. Skips the "Notes:" preamble and any blank lines.
function _parseConnectionsCSV(text) {{
  if (!text) return [];
  // Normalize newlines
  const lines = text.replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').split('\\n');
  // Find header row — must contain "First Name" and "Last Name"
  let headerIdx = -1;
  for (let i = 0; i < lines.length; i++) {{
    const lower = lines[i].toLowerCase();
    if (lower.includes('first name') && lower.includes('last name')) {{
      headerIdx = i;
      break;
    }}
  }}
  if (headerIdx === -1) throw new Error('Could not find the connections header row. Make sure this is the Connections.csv from your LinkedIn export.');
  const header = _csvSplitLine(lines[headerIdx]).map(h => h.trim().toLowerCase());
  const idx = {{
    first: header.indexOf('first name'),
    last: header.indexOf('last name'),
    url: header.indexOf('url'),
    email: header.indexOf('email address'),
    company: header.indexOf('company'),
    position: header.indexOf('position'),
    connected: header.indexOf('connected on'),
  }};
  const out = [];
  for (let i = headerIdx + 1; i < lines.length; i++) {{
    const ln = lines[i];
    if (!ln || !ln.trim()) continue;
    const cols = _csvSplitLine(ln);
    const first = (idx.first >= 0 ? cols[idx.first] : '') || '';
    const last = (idx.last >= 0 ? cols[idx.last] : '') || '';
    const company = (idx.company >= 0 ? cols[idx.company] : '') || '';
    if (!first && !last) continue; // skip empty rows
    out.push({{
      first: first.trim(),
      last: last.trim(),
      url: (idx.url >= 0 ? (cols[idx.url] || '').trim() : ''),
      email: (idx.email >= 0 ? (cols[idx.email] || '').trim() : ''),
      company: company.trim(),
      position: (idx.position >= 0 ? (cols[idx.position] || '').trim() : ''),
      connected: (idx.connected >= 0 ? (cols[idx.connected] || '').trim() : ''),
    }});
  }}
  return out;
}}

function loadLinkedInContacts() {{
  try {{
    const raw = localStorage.getItem(LINKEDIN_CONTACTS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  }} catch (e) {{ return []; }}
}}

function loadLinkedInContactsMeta() {{
  try {{
    const raw = localStorage.getItem(LINKEDIN_CONTACTS_META_KEY);
    return raw ? JSON.parse(raw) : null;
  }} catch (e) {{ return null; }}
}}

function saveLinkedInContacts(contacts, filename) {{
  localStorage.setItem(LINKEDIN_CONTACTS_KEY, JSON.stringify(contacts));
  localStorage.setItem(LINKEDIN_CONTACTS_META_KEY, JSON.stringify({{
    count: contacts.length,
    uploadedAt: new Date().toISOString(),
    filename: filename || 'Connections.csv',
  }}));
  _contactsByCompany = null; // invalidate cache
}}

function clearLinkedInContacts() {{
  localStorage.removeItem(LINKEDIN_CONTACTS_KEY);
  localStorage.removeItem(LINKEDIN_CONTACTS_META_KEY);
  _contactsByCompany = null;
  injectContactBadgesOnCards(); // refresh badges
  renderContactsSummary();
  renderContactsList();
}}

function _buildContactsByCompany() {{
  if (_contactsByCompany) return _contactsByCompany;
  const contacts = loadLinkedInContacts();
  const map = {{}};
  contacts.forEach(c => {{
    const norm = _normalizeCompany(c.company);
    if (!norm) return;
    if (!map[norm]) map[norm] = [];
    map[norm].push(c);
  }});
  _contactsByCompany = map;
  return map;
}}

function _findContactsForCompany(displayCompany) {{
  const contacts = loadLinkedInContacts();
  if (!contacts.length) return [];
  const target = _normalizeCompany(displayCompany);
  if (!target) return [];
  const matched = [];
  const seen = new Set();
  for (const c of contacts) {{
    if (_companiesMatch(c.company, displayCompany)) {{
      const k = (c.first + '|' + c.last + '|' + c.url).toLowerCase();
      if (!seen.has(k)) {{ seen.add(k); matched.push(c); }}
    }}
  }}
  return matched;
}}

// --- Modal: upload / list ---------------------------------------------
function setContactsTab(tab) {{
  document.querySelectorAll('#contacts-modal .tab-btn').forEach(b => {{
    b.classList.toggle('active', b.dataset.ctab === tab);
  }});
  document.querySelectorAll('#contacts-modal .tab-panel').forEach(p => {{
    p.classList.toggle('active', p.id === 'ctab-' + tab);
  }});
  if (tab === 'list') renderContactsList();
}}

function openContactsModal() {{
  const modal = document.getElementById('contacts-modal');
  document.getElementById('contacts-upload-status').textContent = '';
  document.getElementById('contacts-dropzone-label').textContent = 'Click to choose your Connections.csv';
  document.getElementById('parse-contacts-btn').disabled = true;
  _pendingContactsFile = null;
  renderContactsSummary();
  setContactsTab('upload');
  modal.classList.add('show');
}}

function closeContactsModal() {{
  document.getElementById('contacts-modal').classList.remove('show');
}}

function renderContactsSummary() {{
  const wrap = document.getElementById('contacts-summary-wrap');
  if (!wrap) return;
  const meta = loadLinkedInContactsMeta();
  const contacts = loadLinkedInContacts();
  if (!contacts.length) {{
    wrap.innerHTML = '';
    return;
  }}
  const dt = meta && meta.uploadedAt ? new Date(meta.uploadedAt) : null;
  const dtStr = dt ? dt.toLocaleDateString(undefined, {{ year:'numeric', month:'short', day:'numeric' }}) : 'recently';
  wrap.innerHTML = '<div class="contact-summary"><span><b>' + contacts.length + '</b> contacts loaded · uploaded ' + dtStr + '</span><button class="clear-btn" onclick="if(confirm(\\'Clear all saved contacts?\\'))clearLinkedInContacts()">Clear</button></div>';
}}

function renderContactsList() {{
  const wrap = document.getElementById('contacts-list-wrap');
  if (!wrap) return;
  const contacts = loadLinkedInContacts();
  if (!contacts.length) {{
    wrap.innerHTML = '<p class="contact-empty">No contacts saved yet. Upload your Connections.csv on the first tab.</p>';
    return;
  }}
  // Group by company, sort by company then name
  const map = _buildContactsByCompany();
  const companies = Object.keys(map).sort();
  let html = '<p style="font-size:12px;color:#777;margin:0 0 10px 0;">Grouped by company. ' + companies.length + ' companies, ' + contacts.length + ' contacts.</p>';
  companies.forEach(normCo => {{
    const list = map[normCo].slice().sort((a,b) => (a.last||'').localeCompare(b.last||''));
    const display = list[0].company || normCo;
    html += '<div style="margin-bottom:14px;">';
    html += '<div style="font-weight:700;color:#5C5CD6;font-size:13px;margin-bottom:6px;">' + _escHtml(display) + ' <span style="color:#888;font-weight:normal;font-size:11px;">(' + list.length + ')</span></div>';
    list.forEach(c => {{
      const name = ((c.first || '') + ' ' + (c.last || '')).trim();
      html += '<div style="font-size:12.5px;color:#333;padding:4px 0 4px 10px;border-left:2px solid #eaf2fb;margin-bottom:3px;">';
      html += '<b>' + _escHtml(name) + '</b>';
      if (c.position) html += ' <span style="color:#666;">— ' + _escHtml(c.position) + '</span>';
      if (c.url) html += ' <a href="' + _escHtml(c.url) + '" target="_blank" style="color:#0a66c2;font-size:11px;margin-left:4px;">profile↗</a>';
      html += '</div>';
    }});
    html += '</div>';
  }});
  wrap.innerHTML = html;
}}

function _wireContactsDropzone() {{
  const dz = document.getElementById('contacts-dropzone');
  const input = document.getElementById('contacts-file-input');
  if (!dz || !input || dz._wired) return;
  dz._wired = true;
  input.addEventListener('change', (e) => {{
    if (e.target.files && e.target.files[0]) _handleContactsFileChosen(e.target.files[0]);
  }});
  ['dragover','dragenter'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.add('drag'); }}));
  ['dragleave','drop'].forEach(ev => dz.addEventListener(ev, (e) => {{ e.preventDefault(); dz.classList.remove('drag'); }}));
  dz.addEventListener('drop', (e) => {{
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) _handleContactsFileChosen(e.dataTransfer.files[0]);
  }});
}}

function _handleContactsFileChosen(file) {{
  const name = (file.name || '').toLowerCase();
  if (!name.endsWith('.csv')) {{
    document.getElementById('contacts-upload-status').textContent = 'Need a .csv file. Make sure you unzipped the LinkedIn archive and selected Connections.csv.';
    return;
  }}
  _pendingContactsFile = file;
  document.getElementById('contacts-dropzone-label').textContent = file.name;
  document.getElementById('parse-contacts-btn').disabled = false;
  document.getElementById('contacts-upload-status').textContent = 'Ready. Click Save contacts.';
}}

async function parseUploadedContacts(btn) {{
  if (!_pendingContactsFile) return;
  const statusEl = document.getElementById('contacts-upload-status');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Reading…';
  try {{
    const text = await _pendingContactsFile.text();
    const contacts = _parseConnectionsCSV(text);
    if (!contacts.length) {{
      statusEl.textContent = 'No contacts found in this file. Is this the right CSV?';
      btn.textContent = orig;
      btn.disabled = false;
      return;
    }}
    saveLinkedInContacts(contacts, _pendingContactsFile.name);
    // Decorate cards now that contacts are loaded
    try {{ _decorateContactBadges(); }} catch (e) {{}}
    statusEl.textContent = 'Saved ' + contacts.length + ' contacts. Badges will appear on matching jobs.';
    btn.textContent = orig;
    btn.disabled = false;
    _pendingContactsFile = null;
    document.getElementById('contacts-file-input').value = '';
    document.getElementById('contacts-dropzone-label').textContent = 'Upload another to replace';
    renderContactsSummary();
    renderContactsList();
    injectContactBadgesOnCards();
  }} catch (e) {{
    statusEl.textContent = 'Failed: ' + (e.message || e);
    btn.textContent = orig;
    btn.disabled = false;
  }}
}}

// --- Badge injection on job cards -------------------------------------
function injectContactBadgesOnCards() {{
  const cards = document.querySelectorAll('.card');
  if (!cards.length) return;
  const contacts = loadLinkedInContacts();
  cards.forEach(card => {{
    // Remove any existing badge first (so re-runs are clean)
    const existing = card.querySelector('.contact-badge');
    if (existing) existing.remove();
    if (!contacts.length) return;
    const companyEl = card.querySelector('.company');
    if (!companyEl) return;
    const company = (companyEl.textContent || '').trim();
    const matches = _findContactsForCompany(company);
    if (!matches.length) return;
    const badge = document.createElement('span');
    badge.className = 'contact-badge';
    const hiringCount = matches.filter(_isHiringRoleContact).length;
    if (hiringCount > 0) {{
      badge.classList.add('hiring');
      badge.title = hiringCount + ' recruiter/HR contact' + (hiringCount === 1 ? '' : 's') + ' + ' + (matches.length - hiringCount) + ' other at ' + company;
      badge.innerHTML = '<span class="ic">🎯</span> ' + hiringCount + ' recruiter' + (hiringCount === 1 ? '' : 's') + (matches.length > hiringCount ? ' (+ ' + (matches.length - hiringCount) + ')' : '');
    }} else {{
      badge.title = matches.length + ' of your LinkedIn contacts work at ' + company;
      badge.innerHTML = '<span class="ic">🤝</span> ' + matches.length + ' contact' + (matches.length === 1 ? '' : 's');
    }}
    badge.addEventListener('click', (e) => {{
      e.stopPropagation();
      const titleEl = card.querySelector('.title a');
      const jobTitle = titleEl ? (titleEl.textContent || '').trim() : '';
      const jobUrl = titleEl ? titleEl.getAttribute('href') : '';
      openCompanyContactsModal(company, jobTitle, jobUrl, matches);
    }});
    companyEl.parentNode.insertBefore(badge, companyEl.nextSibling);
  }});
  // Now that contact badges are in place, re-sort so contact-having
  // jobs bubble to the top.
  try {{ if (typeof sortCards === 'function') sortCards(); }} catch (e) {{}}
}}

// --- Per-company contacts modal ---------------------------------------
function _getSenderName() {{
  const h1 = document.querySelector('header h1');
  if (h1) {{
    const txt = h1.textContent || '';
    const m = txt.match(/^Jobs for\s+(.+)$/i);
    if (m) return m[1].trim();
  }}
  return USER_SLUG.charAt(0).toUpperCase() + USER_SLUG.slice(1);
}}

function _draftOutreachMessage(contact, company, jobTitle) {{
  const first = (contact.first || '').trim() || 'there';
  const sender = _getSenderName();
  const titlePart = jobTitle ? ('an opening for ' + jobTitle + ' at ' + company) : ('an opportunity at ' + company);
  return (
    'Hi ' + first + ',\\n\\n' +
    'Hope you\\'re doing well! I came across ' + titlePart + ' and noticed you\\'re on the team. ' +
    'Would you be open to a quick chat about your experience there? If it seems like a fit, I\\'d also really appreciate a referral or any thoughts on how to approach the application.\\n\\n' +
    'Happy to share my resume — thanks for considering!\\n\\n' +
    'Best,\\n' + sender
  );
}}

function openCompanyContactsModal(company, jobTitle, jobUrl, contacts) {{
  const modal = document.getElementById('company-contacts-modal');
  document.getElementById('company-contacts-title').textContent = contacts.length + ' contact' + (contacts.length === 1 ? '' : 's') + ' at ' + company;
  document.getElementById('company-contacts-sub').textContent = jobTitle ? ('For: ' + jobTitle) : 'People you know who work there.';
  const wrap = document.getElementById('company-contacts-list');
  let html = '';
  contacts.forEach((c, i) => {{
    const name = ((c.first || '') + ' ' + (c.last || '')).trim();
    const msg = _draftOutreachMessage(c, company, jobTitle);
    const msgId = 'msg-' + i;
    html += '<div class="contact-row">';
    html += '<div class="name-line"><span class="cname">' + _escHtml(name) + '</span>';
    if (c.position) html += '<span class="ctitle">' + _escHtml(c.position) + '</span>';
    html += '</div>';
    if (c.connected) html += '<div class="cmeta">Connected ' + _escHtml(c.connected) + '</div>';
    html += '<div class="msg-box" id="' + msgId + '">' + _escHtml(msg) + '</div>';
    html += '<div class="crow-actions">';
    html += '<button class="btn primary" onclick="copyContactMessage(\\'' + msgId + '\\', this)">Copy message</button>';
    if (c.url) {{
      html += '<a class="btn primary" href="' + _escHtml(c.url) + '" target="_blank" style="text-decoration:none;background:#0a66c2;border-color:#0a66c2;">Open profile on LinkedIn ↗</a>';
    }}
    if (c.email) {{
      const subj = encodeURIComponent('Quick question about ' + (jobTitle || company));
      const body = encodeURIComponent(msg);
      html += '<a class="btn" href="mailto:' + _escHtml(c.email) + '?subject=' + subj + '&body=' + body + '" style="text-decoration:none;background:#f3f4f6;color:#5C5CD6;border:1px solid #ccd0d6;">Email instead</a>';
    }}
    html += '</div>';
    html += '</div>';
  }});
  wrap.innerHTML = html;
  modal.classList.add('show');
}}

function closeCompanyContactsModal() {{
  document.getElementById('company-contacts-modal').classList.remove('show');
}}

function copyContactMessage(elId, btn) {{
  const el = document.getElementById(elId);
  if (!el) return;
  const text = el.textContent || '';
  navigator.clipboard.writeText(text).then(() => {{
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }}).catch(() => {{
    // Fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try {{ document.execCommand('copy'); }} catch (e) {{}}
    document.body.removeChild(ta);
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {{ btn.textContent = orig; }}, 1500);
  }});
}}

// Wire contacts on DOM ready, and inject badges
if (document.readyState !== 'loading') {{
  _wireContactsDropzone();
  injectContactBadgesOnCards();
}} else {{
  document.addEventListener('DOMContentLoaded', () => {{
    _wireContactsDropzone();
    injectContactBadgesOnCards();
  }});
}}

// init
loadTracker().then(() => {{
  refreshTrackerUI();
  setView(viewMode);
  setEmploymentFilter(employmentFilter);
}});

// ============================================================
// First-login wizard
// ============================================================
const HAS_PROFILE_AT_RENDER = {has_profile_js};
const WIZ_USER_NAME = "{user_name}";

const WIZ_STEPS = [
  {{
    title: "Welcome to getmemyjob, " + WIZ_USER_NAME + ".",
    body: "<p>We'll set you up in about <strong>2 minutes</strong>. After that you'll see roles tailored to your background — no clinical, no sales, no junk.</p><p>Here's what we'll do:</p><ul><li>Upload your resume (PDF or Word)</li><li>Review the skills we extract from it</li><li>Optionally add your LinkedIn network for warm intros</li></ul>",
    cta: "Let&rsquo;s go",
    action: "next",
    skipText: "Skip for now"
  }},
  {{
    title: "Upload your resume",
    body: "<p>Drop a <strong>PDF or Word</strong> resume — we'll read it and figure out which roles to surface for you.</p><p>It takes about 10 seconds.</p>",
    cta: "Open resume upload &rarr;",
    action: "open-resume",
    skipText: "Skip — I'll do this later"
  }},
  {{
    title: "Adjust your target titles, industries and skills",
    body:
      '<p style="margin-bottom:12px;font-size:14px;color:#444;">These are extracted from your resume. We use them to match you against jobs \u2014 add anything we missed, remove anything inaccurate. <strong>Sharper signals = fewer 0-match days.</strong></p>' +
      '<div id="wiz-chip-status" style="font-size:12px;color:#888;margin-bottom:8px;min-height:16px;">Loading your profile\u2026</div>' +
      '<div data-field="targetTitles" class="wiz-chip-section" style="margin-bottom:14px;">' +
        '<div class="wiz-chip-label" style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px;">Target titles <span style="font-weight:400;color:#888;">&mdash; the job titles you actually want (this drives matching the most)</span></div>' +
        '<div class="wiz-chip-list" id="wiz-chips-targetTitles" data-target="targetTitles" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px;min-height:28px;"></div>' +
        '<div style="display:flex;gap:6px;">' +
          '<input class="wiz-chip-input" data-target="targetTitles" type="text" placeholder="Add a target title\u2026 (Enter)" style="flex:1;padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:12.5px;">' +
        '</div>' +
      '</div>' +
      '<div data-field="industries" class="wiz-chip-section" style="margin-bottom:14px;">' +
        '<div class="wiz-chip-label" style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px;">Industries <span style="font-weight:400;color:#888;">\u2014 broad sectors (e.g. banking, fintech, healthcare-it)</span></div>' +
        '<div class="wiz-chip-list" id="wiz-chips-industries" style="min-height:30px;"></div>' +
        '<div style="display:flex;gap:6px;margin-top:6px;">' +
          '<input class="wiz-chip-input" data-target="industries" type="text" placeholder="Add an industry\u2026 (Enter)" style="flex:1;padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:12.5px;">' +
        '</div>' +
      '</div>' +
      '<div data-field="keywords" class="wiz-chip-section" style="margin-bottom:14px;">' +
        '<div class="wiz-chip-label" style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px;">Key skills &amp; keywords <span style="font-weight:400;color:#888;">\u2014 must-have terms in job title/desc</span></div>' +
        '<div class="wiz-chip-list" id="wiz-chips-keywords" style="min-height:30px;"></div>' +
        '<div style="display:flex;gap:6px;margin-top:6px;">' +
          '<input class="wiz-chip-input" data-target="keywords" type="text" placeholder="Add a keyword\u2026 (Enter)" style="flex:1;padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:12.5px;">' +
        '</div>' +
      '</div>' +
      '<div data-field="specialties" class="wiz-chip-section" style="margin-bottom:6px;">' +
        '<div class="wiz-chip-label" style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px;">Specialties <span style="font-weight:400;color:#888;">\u2014 granular sub-domains</span></div>' +
        '<div class="wiz-chip-list" id="wiz-chips-specialties" style="min-height:30px;"></div>' +
        '<div style="display:flex;gap:6px;margin-top:6px;">' +
          '<input class="wiz-chip-input" data-target="specialties" type="text" placeholder="Add a specialty\u2026 (Enter)" style="flex:1;padding:6px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:12.5px;">' +
        '</div>' +
      '</div>' +
      '<div id="wiz-chip-save-status" style="font-size:12px;color:#888;margin-top:10px;min-height:16px;"></div>',
    cta: "Save changes &rarr;",
    action: "save-profile-chips",
    skipText: "Skip \u2014 use AI defaults"
  }},
  {{
    title: "Confirm where you want to work",
    body: '<p style="margin-bottom:14px;">We extracted these from your resume. Tweak them so they reflect what you\u2019re actually open to \u2014 we use them to filter jobs.</p>' +
      '<label for="wiz-locs" style="display:block;font-size:12px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">Preferred locations</label>' +
      '<input id="wiz-locs" type="text" placeholder="e.g. New York City, Remote (US)" style="width:100%;padding:8px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:14px;margin-bottom:6px;">' +
      '<div style="font-size:12px;color:#888;margin-bottom:14px;">Comma-separated. Add &ldquo;Remote (US)&rdquo; if you\u2019re open to remote.</div>' +
      '<label for="wiz-remote" style="display:block;font-size:12px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">Remote preference</label>' +
      '<select id="wiz-remote" style="width:100%;padding:8px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:14px;background:white;">' +
      '<option value="any">Any &mdash; show me everything</option>' +
      '<option value="remote-only">Remote only</option>' +
      '<option value="hybrid">Hybrid (remote OK, but I\u2019ll travel to office sometimes)</option>' +
      '<option value="onsite">Onsite preferred</option>' +
      '</select>' +
      '<div id="wiz-locs-status" style="font-size:12px;color:#888;margin-top:10px;min-height:16px;"></div>',
    cta: "Save preferences &rarr;",
    action: "save-location-remote",
    skipText: "Skip \u2014 use AI defaults"
  }},
  {{
    title: "What's your ideal mix of company sizes?",
    body: '<p style="margin-bottom:14px;">We mix jobs across startups, mid-size, and large employers. Tell us your ideal balance \u2014 drag the sliders or type a number. Total has to add up to 100. Set any one to 0 to exclude that size entirely.</p>' +
      '<div style="display:flex;flex-direction:column;gap:14px;">' +
      '<div>' +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +'<span><strong>Startups</strong> <span style=\"color:#888;font-weight:normal;\">&mdash; under 500 employees, often early-stage</span></span>' +'<span style="display:flex;align-items:center;gap:4px;"><input id="wiz-mix-startup-num" type="number" min="0" max="100" value="33" oninput="wizMixOnNum(\\'startup\\')" style="width:54px;padding:4px 6px;border:1px solid #d0d4dc;border-radius:4px;text-align:right;font-size:13px;">%</span>' +'</div>' +'<input type="range" id="wiz-mix-startup" min="0" max="100" value="33" oninput="wizMixOnSlide(\\'startup\\')" style="width:100%;">' +'</div>' +
      '<div>' +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +'<span><strong>Mid-size</strong> <span style=\"color:#888;font-weight:normal;\">&mdash; 500\u201310k employees, established</span></span>' +'<span style="display:flex;align-items:center;gap:4px;"><input id="wiz-mix-midsize-num" type="number" min="0" max="100" value="33" oninput="wizMixOnNum(\\'midsize\\')" style="width:54px;padding:4px 6px;border:1px solid #d0d4dc;border-radius:4px;text-align:right;font-size:13px;">%</span>' +'</div>' +'<input type="range" id="wiz-mix-midsize" min="0" max="100" value="33" oninput="wizMixOnSlide(\\'midsize\\')" style="width:100%;">' +'</div>' +
      '<div>' +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +'<span><strong>Large</strong> <span style=\"color:#888;font-weight:normal;\">&mdash; 10k+ employees, Fortune 500 / public</span></span>' +'<span style="display:flex;align-items:center;gap:4px;"><input id="wiz-mix-large-num" type="number" min="0" max="100" value="33" oninput="wizMixOnNum(\\'large\\')" style="width:54px;padding:4px 6px;border:1px solid #d0d4dc;border-radius:4px;text-align:right;font-size:13px;">%</span>' +'</div>' +'<input type="range" id="wiz-mix-large" min="0" max="100" value="33" oninput="wizMixOnSlide(\\'large\\')" style="width:100%;">' +'</div>' +
      '</div>' +
      '<div id="wiz-mix-status" style="display:flex;justify-content:space-between;font-size:12px;color:#888;margin-top:10px;min-height:18px;">' +
      '<span>Total: <strong id="wiz-mix-sum-val">99</strong>%</span>' +
      '<span id="wiz-mix-msg"></span>' +
      '</div>',
    cta: "Save preferences &rarr;",
    action: "save-company-sizes",
    skipText: "Skip \u2014 use an even mix"
  }},
  {{
    title: "How should we weight your match score?",
    body: '<p style="margin-bottom:14px;">Tell us how much each signal should count when we score jobs. Drag a slider; the other two adjust so the total stays at 100. <strong>Default is title-heavy</strong> because exact title matches are the strongest predictor.</p>' +
      '<div style="display:flex;flex-direction:column;gap:14px;">' +
      '<div>' +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +'<span><strong>Job title</strong> <span style="color:#888;font-weight:normal;">&mdash; how closely the title matches your target titles</span></span>' +'<span style="display:flex;align-items:center;gap:4px;"><input id="wiz-wt-titles-num" type="number" min="0" max="100" value="50" oninput="wizWtOnNum(&apos;titles&apos;)" style="width:54px;padding:4px 6px;border:1px solid #d0d4dc;border-radius:4px;text-align:right;font-size:13px;">%</span>' +'</div>' +'<input type="range" id="wiz-wt-titles" min="0" max="100" value="50" oninput="wizWtOnSlide(&apos;titles&apos;)" style="width:100%;">' +'</div>' +
      '<div>' +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +'<span><strong>Industry</strong> <span style="color:#888;font-weight:normal;">&mdash; sector overlap (e.g. healthcare-it, banking, fintech)</span></span>' +'<span style="display:flex;align-items:center;gap:4px;"><input id="wiz-wt-industries-num" type="number" min="0" max="100" value="25" oninput="wizWtOnNum(&apos;industries&apos;)" style="width:54px;padding:4px 6px;border:1px solid #d0d4dc;border-radius:4px;text-align:right;font-size:13px;">%</span>' +'</div>' +'<input type="range" id="wiz-wt-industries" min="0" max="100" value="25" oninput="wizWtOnSlide(&apos;industries&apos;)" style="width:100%;">' +'</div>' +
      '<div>' +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +'<span><strong>Skills &amp; keywords</strong> <span style="color:#888;font-weight:normal;">&mdash; specific skills, tools, frameworks, regulations</span></span>' +'<span style="display:flex;align-items:center;gap:4px;"><input id="wiz-wt-skills-num" type="number" min="0" max="100" value="25" oninput="wizWtOnNum(&apos;skills&apos;)" style="width:54px;padding:4px 6px;border:1px solid #d0d4dc;border-radius:4px;text-align:right;font-size:13px;">%</span>' +'</div>' +'<input type="range" id="wiz-wt-skills" min="0" max="100" value="25" oninput="wizWtOnSlide(&apos;skills&apos;)" style="width:100%;">' +'</div>' +
      '</div>' +
      '<div style="display:flex;justify-content:space-between;font-size:12px;color:#888;margin-top:10px;min-height:18px;">' +
      '<span>Total: <strong id="wiz-wt-sum-val">100</strong>%</span>' +
      '<span id="wiz-wt-msg"></span>' +
      '</div>',
    cta: "Save weights &rarr;",
    action: "save-match-weights",
    skipText: "Skip — use defaults (50/25/25)"
  }},
  {{
    title: "How many jobs do you want to apply to per day?",
    body: '<p style="margin-bottom:14px;">A daily goal keeps the job search consistent. You can change this anytime in Preferences.</p>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px;">' +
      ['1','3','5','10','15','20'].map(function(n) {{
        return '<button type="button" class="wiz-quick-pick" data-n="' + n + '" onclick="wizPickDailyTarget(' + n + ')" style="padding:8px 14px;border:1px solid #d0d4dc;border-radius:8px;background:#fff;cursor:pointer;font-size:13px;font-weight:600;">' + n + '</button>';
      }}).join('') + '</div>' +
      '<label style="display:block;font-size:12px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;">Or set a custom number</label>' +
      '<input id="wiz-daily-target" type="number" min="1" max="50" value="5" style="width:100%;padding:8px 10px;border:1px solid #d0d4dc;border-radius:6px;font-size:14px;">' +
      '<div id="wiz-daily-status" style="font-size:12px;color:#888;margin-top:10px;min-height:16px;"></div>',
    cta: "Save target &rarr;",
    action: "save-daily-target",
    skipText: "Skip \u2014 default 5/day"
  }},
  {{
    title: "How recent should jobs be by default?",
    body: '<p style="margin-bottom:14px;">Older listings are often filled or ghost roles. We will default to this window when you load the dashboard \u2014 you can always change it with the pills above the job feed.</p>' +
      '<div style="display:flex;flex-direction:column;gap:8px;">' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="0" style="cursor:pointer;"> <span><strong>Last 24 hours</strong> &mdash; only show roles posted today</span></label>' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="7" checked style="cursor:pointer;"> <span><strong>Last 7 days</strong> &mdash; freshest listings, best signal of active hiring</span></label>' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="14" style="cursor:pointer;"> <span><strong>Last 2 weeks</strong> &mdash; balance freshness with broader pool</span></label>' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="30" style="cursor:pointer;"> <span><strong>Last 30 days</strong> &mdash; widest reasonable pool</span></label>' +
        '<label style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #d0d4dc;border-radius:8px;cursor:pointer;"><input type="radio" name="wiz-recency" value="all" style="cursor:pointer;"> <span><strong>All jobs</strong> &mdash; show everything, sort handles freshness</span></label>' +
      '</div>' +
      '<div id="wiz-recency-status" style="font-size:12px;color:#888;margin-top:10px;min-height:16px;"></div>',
    cta: "Save default &rarr;",
    action: "save-recency-window",
    skipText: "Skip \u2014 default Last 7 days"
  }},
  {{
    title: "Install the Helper Chrome extension (required)",
    body: '<p style="margin-bottom:10px;font-size:14px;color:#444;">Without this, you fill 20 fields by hand on every job application. With it, you click Apply → land on the company page → 18 of 25 fields auto-populate in 1 second from your resume. Total time per application: <strong>~60 seconds</strong> instead of ~10 minutes.</p>' +
      '<div style="background:#f4f5f8;border-radius:8px;padding:12px;margin-bottom:10px;font-size:13px;">' +
        '<div style="font-weight:700;margin-bottom:6px;">3-step install (one time only):</div>' +
        '<ol style="margin:0;padding-left:18px;">' +
          '<li><a href="/extension.zip" download style="color:#5C5CD6;font-weight:700;">⬇ Download getmemyjob-helper.zip</a> and unzip it somewhere you’ll keep (e.g. <code>~/Documents/getmemyjob-helper/</code>).</li>' +
          '<li>Open <a href="chrome://extensions" target="_blank" style="color:#5C5CD6;font-weight:700;">chrome://extensions</a> in Chrome, toggle <strong>Developer mode</strong> ON (top-right).</li>' +
          '<li>Click <strong>Load unpacked</strong> and select the unzipped folder.</li>' +
        '</ol>' +
      '</div>' +
      '<details style="margin-top:10px;font-size:12.5px;color:#444;">' +
        '<summary style="cursor:pointer;color:#5C5CD6;font-weight:600;">Using Firefox, Safari, or your phone instead?</summary>' +
        '<div style="margin-top:8px;padding:10px;background:#fff;border:1px solid #d0d4dc;border-radius:6px;">' +
          '<p style="margin:0 0 8px 0;"><strong>Firefox:</strong> <a href="/extension-firefox.zip" download style="color:#5C5CD6;font-weight:600;">⬇ Download Firefox build</a>, then in Firefox open <code>about:debugging</code> → This Firefox → Load Temporary Add-on, pick the manifest.json inside the unzipped folder.</p>' +
          '<p style="margin:0 0 8px 0;"><strong>Safari, iPhone/iPad, or any other browser:</strong> drag this link to your <strong>bookmarks bar</strong>:' +
            ' <a href="javascript:(function(){{var s=document.createElement(&apos;script&apos;);s.src=&apos;https://getmemyjob.officebeatllc.com/bookmarklet.js?t=&apos;+Date.now();document.body.appendChild(s);}})();" ' +
            'style="display:inline-block;margin-left:6px;padding:4px 10px;background:#5C5CD6;color:#fff;border-radius:4px;text-decoration:none;font-weight:700;">📌 getmemyjob Helper</a></p>' +
          '<p style="margin:0;font-size:11.5px;color:#777;">Bookmarklet works in any browser including iOS Safari — drag the purple button above into your bookmarks bar, then on any Greenhouse/Lever/Ashby/Workday apply page click it once to auto-fill.</p>' +
        '</div>' +
      '</details>' +
            '<div id="wiz-ext-status" style="font-size:13px;font-weight:600;color:#888;margin-top:10px;min-height:20px;display:flex;align-items:center;gap:8px;">Checking for the extension…</div>',
    cta: "I’ve installed it — check",
    action: "verify-extension",
    skipText: "Skip — I’ll fill applications manually"
  }},
  {{
    title: "Application profile (so we can auto-fill apply forms)",
    body: '<p style="margin-bottom:14px;font-size:14px;color:#444;">These fields appear on almost every job application. Save them here once and our Helper extension fills them automatically on Greenhouse / Lever / Ashby / Workday.</p>' +
      '<label style="display:block;font-size:11px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;margin-top:10px;">Phone</label>' +
      '<input id="wiz-app-phone" type="tel" placeholder="(555) 123-4567" style="width:100%;padding:7px 9px;border:1px solid #d0d4dc;border-radius:6px;font-size:13.5px;box-sizing:border-box;">' +
      '<label style="display:block;font-size:11px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;margin-top:10px;">City, State</label>' +
      '<input id="wiz-app-location" type="text" placeholder="e.g. Allendale, NJ" style="width:100%;padding:7px 9px;border:1px solid #d0d4dc;border-radius:6px;font-size:13.5px;box-sizing:border-box;">' +
      '<label style="display:block;font-size:11px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;margin-top:10px;">LinkedIn URL</label>' +
      '<input id="wiz-app-linkedin" type="url" placeholder="https://www.linkedin.com/in/your-name" style="width:100%;padding:7px 9px;border:1px solid #d0d4dc;border-radius:6px;font-size:13.5px;box-sizing:border-box;">' +
      '<label style="display:block;font-size:11px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;margin-top:10px;">Work authorization</label>' +
      '<select id="wiz-app-workauth" style="width:100%;padding:7px 9px;border:1px solid #d0d4dc;border-radius:6px;font-size:13.5px;background:white;">' +
        '<option value="US Citizen">US Citizen</option>' +
        '<option value="Green Card">Green Card / Permanent Resident</option>' +
        '<option value="H1B Visa">H1B Visa</option>' +
        '<option value="OPT">OPT / STEM OPT</option>' +
        '<option value="TN Visa">TN Visa</option>' +
        '<option value="Other">Other</option>' +
      '</select>' +
      '<label style="display:block;font-size:11px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px;margin-top:10px;">Will you need visa sponsorship now or in the future?</label>' +
      '<select id="wiz-app-sponsor" style="width:100%;padding:7px 9px;border:1px solid #d0d4dc;border-radius:6px;font-size:13.5px;background:white;">' +
        '<option value="No">No</option>' +
        '<option value="Yes">Yes</option>' +
      '</select>' +
      '<div id="wiz-app-status" style="font-size:12px;color:#888;margin-top:10px;min-height:16px;"></div>',
    cta: "Save profile &rarr;",
    action: "save-app-profile",
    skipText: "Skip — I’ll fill manually"
  }},
  {{
    title: "Add your LinkedIn network (optional)",
    body: "<p>Upload your LinkedIn connections (one CSV) and the job feed will show <strong>&#x1f91d; N contacts</strong> badges on companies where you have warm intros.</p><p>It's a 30-second optional step. You can also do this later.</p>",
    cta: "Add LinkedIn contacts &rarr;",
    action: "open-contacts",
    skipText: "Skip — I'll do this later"
  }},
  {{
    title: "You're all set.",
    body: "<p>We're matching jobs to your profile right now. Your tailored dashboard will appear after the next refresh (2–3 min).</p><p>Quick reminders:</p><ul><li><strong>Prep Application</strong> on any job &rarr; tailored cover letter + resume summary</li><li><strong>Refresh data</strong> in the header &rarr; trigger a fresh pull anytime</li><li><strong>?</strong> button in the header &rarr; replay this tour</li></ul>",
    cta: "Finish &amp; refresh my jobs",
    action: "finish",
    skipText: null
  }}
];

// Listen for the extension-ready postMessage (fires from content script when extension v0.1.2+ installs).
try {{
  window.addEventListener("message", function(ev) {{
    try {{
      if (ev && ev.data && ev.data.type === "GMJ_EXTENSION_READY") {{
        window.__gmj_extension_ready = true;
      }}
    }} catch(e) {{}}
  }});
}} catch(e) {{}}

let wizCurrent = 0;

function wizShow() {{
  const o = document.getElementById("gmj-wizard");
  if (!o) return;
  o.classList.add("show");
  wizRender();
}}
function wizHide() {{
  const o = document.getElementById("gmj-wizard");
  if (o) o.classList.remove("show");
}}
function wizRender() {{
  const s = WIZ_STEPS[wizCurrent];
  document.getElementById("wiz-step-count").textContent = "Step " + (wizCurrent + 1) + " of " + WIZ_STEPS.length;
  // Show "Save & exit" only on steps where the action actually saves something
  const _saveExit = document.getElementById("wiz-save-exit");
  if (_saveExit) {{
    const _s = WIZ_STEPS[wizCurrent];
    const _canSaveExit = _s && (_s.action === "save-location-remote" || _s.action === "save-company-sizes" || _s.action === "save-daily-target" || _s.action === "save-recency-window" || _s.action === "save-profile-chips");
    _saveExit.style.display = _canSaveExit ? "" : "none";
  }}
  document.getElementById("wiz-title").textContent = s.title;
  document.getElementById("wiz-body").innerHTML = s.body;
  document.getElementById("wiz-cta").innerHTML = s.cta;
  // Slice 2.5: prefill the location/remote form if this step is the inline form
  if (s.action === "save-location-remote") {{
    fetch(PROFILE_WORKER_URL).then(function(r){{ return r.json(); }}).then(function(d){{
      const p = (d && d.profile) || {{}};
      const locsEl = document.getElementById("wiz-locs");
      const remoteEl = document.getElementById("wiz-remote");
      if (locsEl && Array.isArray(p.preferredLocations)) locsEl.value = p.preferredLocations.join(", ");
      if (remoteEl) remoteEl.value = p.remotePreference || (p.remotePreferred ? "remote-only" : "any");
    }}).catch(function(){{}});
  }}
  if (s.action === "verify-extension") {{
    const statusEl = document.getElementById("wiz-ext-status");
    function _isInstalled() {{
      try {{
        if (document.documentElement.getAttribute("data-gmj-installed") === "1") return true;
        if (window.__gmj_extension_ready) return true;
      }} catch(e) {{}}
      return false;
    }}
    function _renderControls(failedRecently) {{
      // Always show: Reload + Skip buttons inline below the status so users can recover.
      var host = document.getElementById("wiz-ext-extra");
      if (!host) {{
        host = document.createElement("div");
        host.id = "wiz-ext-extra";
        host.style.cssText = "margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;";
        host.innerHTML =
          '<button type="button" id="wiz-ext-reload" style="padding:8px 14px;border:1px solid #5C5CD6;background:#5C5CD6;color:#fff;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">' +
            '↻ Reload page &amp; re-check' +
          '</button>' +
          '<button type="button" id="wiz-ext-skip-inline" style="padding:8px 14px;border:1px solid #c0c4cc;background:#fff;color:#444;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">' +
            'Skip — I\\'ll fill manually' +
          '</button>';
        var stat = document.getElementById("wiz-ext-status");
        if (stat && stat.parentNode) stat.parentNode.appendChild(host);
        var rb = document.getElementById("wiz-ext-reload");
        if (rb) rb.addEventListener("click", function(){{
          // Remember we're on this step so the wizard resumes here after reload.
          try {{ localStorage.setItem("gmj_wizard_resume_at", "verify-extension"); }} catch(e) {{}}
          location.reload();
        }});
        var sb = document.getElementById("wiz-ext-skip-inline");
        if (sb) sb.addEventListener("click", function(){{
          try {{ localStorage.removeItem("gmj_wizard_resume_at"); }} catch(e) {{}}
          if (typeof wizAdvance === "function") wizAdvance();
        }});
      }}
    }}
    function _check() {{
      const installed = _isInstalled();
      if (installed) {{
        if (statusEl) {{
          statusEl.style.color = "#0a6b3a";
          statusEl.innerHTML = '✅ Extension detected. You can move on.';
        }}
        const ctaBtn = document.getElementById("wiz-cta");
        if (ctaBtn) ctaBtn.textContent = "Next →";
        try {{ localStorage.removeItem("gmj_wizard_resume_at"); }} catch(e) {{}}
      }} else {{
        if (statusEl) {{
          statusEl.style.color = "#888";
          statusEl.innerHTML = '⌛ Not detected yet. Chrome only injects the helper into <strong>newly-loaded</strong> tabs — if you installed while this tab was already open, click <strong>Reload</strong> below.';
        }}
      }}
      _renderControls(!installed);
    }}
    _check();
    // Listen for the extension-ready event the content script dispatches.
    document.addEventListener("gmj-extension-ready", function(){{ window.__gmj_extension_ready = true; _check(); }}, {{ once: true }});
    // Re-check when the user tabs back from chrome://extensions
    window.addEventListener("focus", _check);
    // Poll every 1.5s. Don't time out — Geetu may take a minute.
    if (window._wizExtPoll) clearInterval(window._wizExtPoll);
    window._wizExtPoll = setInterval(_check, 1500);
  }}
  if (s.action === "save-app-profile") {{
    // Prefill from existing skills_profile + resume parsed JSON
    fetch(PROFILE_WORKER_URL).then(function(r){{return r.json();}}).then(function(d){{
      const p = (d && d.profile) || {{}};
      const ph = document.getElementById("wiz-app-phone");
      const loc = document.getElementById("wiz-app-location");
      const li = document.getElementById("wiz-app-linkedin");
      const wa = document.getElementById("wiz-app-workauth");
      const sp = document.getElementById("wiz-app-sponsor");
      if (ph) ph.value = p.phone || "";
      if (loc) loc.value = p.location || (Array.isArray(p.preferredLocations) ? p.preferredLocations[0] || "" : "");
      if (li) li.value = p.linkedinUrl || "";
      if (wa && p.workAuthorization) wa.value = p.workAuthorization;
      if (sp && p.requiresSponsorship) sp.value = p.requiresSponsorship === true || p.requiresSponsorship === "Yes" ? "Yes" : "No";
    }}).catch(function(){{}});
  }}
  let dots = "";
  for (let i = 0; i < WIZ_STEPS.length; i++) {{
    if (i < wizCurrent) dots += '<div class="dot done"></div>';
    else if (i === wizCurrent) dots += '<div class="dot active"></div>';
    else dots += '<div class="dot"></div>';
  }}
  document.getElementById("wiz-progress").innerHTML = dots;
  document.getElementById("wiz-back").style.display = wizCurrent > 0 ? "" : "none";
  const skip = document.getElementById("wiz-skip");
  if (s.skipText === null) {{ skip.style.display = "none"; }}
  else {{ skip.style.display = ""; skip.textContent = s.skipText || "Skip for now"; }}
  // Step-specific lazy loaders
  if (s.action === "save-profile-chips") {{
    setTimeout(wizLoadProfileChips, 50);
  }}
  if (s.action === "save-match-weights") {{
    setTimeout(wizWtPrefill, 50);
  }}
}}
function wizAdvance() {{
  wizCurrent++;
  if (wizCurrent >= WIZ_STEPS.length) {{ wizFinish(); return; }}
  wizRender();
}}
function wizBack() {{ if (wizCurrent > 0) {{ wizCurrent--; wizRender(); }} }}
async function wizFinish() {{
  try {{ localStorage.setItem("gmj_wizard_seen_v2", "true"); }} catch(e) {{}}

  // Lock the CTA, show progress in place, run the AI regen against the
  // user's just-saved companySizePreferences, then trigger a dashboard
  // refresh. Everything visible to the user — no console required.
  const ctaBtn = document.getElementById("wiz-cta");
  const titleEl = document.getElementById("wiz-title");
  const bodyEl = document.getElementById("wiz-body");
  const origCtaText = ctaBtn ? ctaBtn.textContent : "";
  if (ctaBtn) {{ ctaBtn.disabled = true; ctaBtn.textContent = "Personalizing\u2026"; }}
  if (titleEl) titleEl.textContent = "Personalizing your job feed\u2026";
  if (bodyEl) bodyEl.innerHTML = '<p style="margin-bottom:8px;">Re-running the AI matcher with your latest preferences. This takes about 30\u201360 seconds.</p><p style="font-size:13px;color:#666;" id="wiz-finish-status">Calling the AI\u2026</p>';

  const statusEl = document.getElementById("wiz-finish-status");
  const editKey = (typeof getEditKey === "function") ? getEditKey() : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));

  let regenOk = false;
  let regenTc = 0;
  if (editKey) {{
    try {{
      const r = await fetch(WORKER_BASE + "/regenerate-profile" + USER_QS, {{
        method: "POST",
        headers: {{ "X-Edit-Key": editKey }}
      }});
      const data = await r.json().catch(function(){{ return {{}}; }});
      if (r.ok && data && data.profile) {{
        regenOk = true;
        regenTc = (data.profile.targetCompanies || []).length;
        if (statusEl) statusEl.textContent = "Generated " + regenTc + " personalized target companies. Triggering job refresh\u2026";
      }} else if (statusEl) {{
        statusEl.textContent = "Couldn\u2019t regenerate (" + ((data && data.error) || ("HTTP " + r.status)) + ") \u2014 your existing AI matches still apply.";
      }}
    }} catch (e) {{
      if (statusEl) statusEl.textContent = "Network error during regen \u2014 your existing AI matches still apply.";
    }}
  }} else if (statusEl) {{
    statusEl.textContent = "No edit key in this browser \u2014 skipping regen. (Use the invite link with ?key=\u2026 once.)";
  }}

  // Kick the GitHub Action that rebuilds dashboards regardless of regen result
  try {{ fetch(WORKER_BASE + "/refresh", {{ method: "POST" }}).catch(function(){{}}); }} catch (e) {{}}

  // Final summary then close
  if (bodyEl) {{
    const summary = regenOk
      ? "Your job feed is rebuilding now (2\u20133 min). When it\u2019s done you\u2019ll see new role suggestions tuned to your sizes and locations."
      : "Your job feed is rebuilding now (2\u20133 min). Refresh this page in a few minutes to see updates.";
    bodyEl.innerHTML = '<p style="margin-bottom:8px;color:#0a6b3a;font-weight:600;">All set!</p><p>' + summary + '</p>';
  }}
  if (titleEl) titleEl.textContent = regenOk ? ("Personalized " + regenTc + " target companies") : "Your job feed is rebuilding";
  if (ctaBtn) {{ ctaBtn.disabled = false; ctaBtn.textContent = "Close"; ctaBtn.onclick = function(){{ wizHide(); }}; }}
}}
function wizSkipPermanent() {{
  try {{ localStorage.setItem("gmj_wizard_seen_v2", "true"); }} catch(e) {{}}
  wizHide();
}}
function wizBanner(msg) {{
  const b = document.createElement("div");
  b.className = "wiz-banner";
  b.textContent = msg;
  document.body.appendChild(b);
  setTimeout(function(){{ if (b.parentNode) b.parentNode.removeChild(b); }}, 8000);
}}
function replayTour() {{ wizCurrent = 0; wizShow(); }}

// --- Wizard inline chip editor (Industries / Keywords / Specialties) -----
const WIZ_CHIP_FIELDS = ["targetTitles", "industries", "keywords", "specialties"];
let _wizChipState = {{ industries: [], keywords: [], specialties: [] }};
let _wizChipLoaded = false;

function _renderWizChipsFor(field) {{
  const cont = document.getElementById("wiz-chips-" + field);
  if (!cont) return;
  const items = _wizChipState[field] || [];
  cont.innerHTML = items.map(function(s, i) {{
    const safe = (s || "").replace(/[&<>"]/g, c => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }}[c]));
    return '<span style="display:inline-flex;align-items:center;background:#eef0ff;color:#5C5CD6;padding:3px 4px 3px 9px;border-radius:12px;font-size:11.5px;margin:2px 4px 2px 0;font-weight:500;">' + safe + '<button type="button" data-idx="' + i + '" data-field="' + field + '" class="wiz-chip-remove" style="background:none;border:0;color:#888;cursor:pointer;padding:0 0 0 6px;font-size:14px;line-height:1;font-weight:600;" title="Remove">\u00d7</button></span>';
  }}).join("");
  // Wire up the remove buttons
  cont.querySelectorAll(".wiz-chip-remove").forEach(function(btn) {{
    btn.addEventListener("click", function() {{
      const f = btn.getAttribute("data-field");
      const i = parseInt(btn.getAttribute("data-idx"), 10);
      _wizChipState[f].splice(i, 1);
      _renderWizChipsFor(f);
    }});
  }});
}}

async function wizLoadProfileChips() {{
  const statusEl = document.getElementById("wiz-chip-status");
  try {{
    const r = await fetch(WORKER_BASE + "/skills-profile" + USER_QS);
    const data = await r.json().catch(function() {{ return {{}}; }});
    const profile = (data && data.profile) || {{}};
    WIZ_CHIP_FIELDS.forEach(function(f) {{
      _wizChipState[f] = (profile[f] || []).slice();
    }});
    _wizChipLoaded = true;
    WIZ_CHIP_FIELDS.forEach(_renderWizChipsFor);
    if (statusEl) statusEl.textContent = "";
    // Wire add-input listeners (Enter to add)
    document.querySelectorAll(".wiz-chip-input").forEach(function(inp) {{
      inp.addEventListener("keydown", function(e) {{
        if (e.key !== "Enter") return;
        e.preventDefault();
        const v = inp.value.trim().toLowerCase();
        if (!v) return;
        const f = inp.getAttribute("data-target");
        if (!_wizChipState[f].includes(v)) {{
          _wizChipState[f].push(v);
          _renderWizChipsFor(f);
        }}
        inp.value = "";
      }});
    }});
  }} catch (e) {{
    if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Couldn\'t load your profile \u2014 you can still skip this step."; }}
  }}
}}

// --- Daily apply target + progress widget -----------------------------
const DAILY_TARGET_KEY = "htj_daily_apply_target_" + USER_SLUG;
function _isoToday() {{ return new Date().toISOString().slice(0, 10); }}
function refreshDailyGoalWidget() {{
  try {{
    const target = loadDailyApplyTarget();
    const today = _isoToday();
    const tracker = (typeof getTracker === "function") ? getTracker() : {{}};
    // Count tracker entries that have status set to applied/phonescreen/onsite/offer
    // AND were set today
    let todayCount = 0;
    let appliedDates = [];
    Object.values(tracker || {{}}).forEach(function(r) {{
      const st = (r && r.status) || "";
      if (!st || st === "rejected") return;
      const when = (r.statusChangedAt || r.appliedAt || r.updatedAt || r.created_at || "");
      const day = (when || "").slice(0, 10);
      if (day) appliedDates.push(day);
      if (day === today) todayCount += 1;
    }});
    const countEl = document.getElementById("goal-today-count");
    const targEl = document.getElementById("goal-today-target");
    const fillEl = document.getElementById("goal-progress-fill");
    const streakEl = document.getElementById("goal-streak");
    if (countEl) countEl.textContent = todayCount;
    if (targEl) targEl.textContent = target;
    if (fillEl) fillEl.style.width = Math.min(100, Math.round(todayCount * 100 / Math.max(1, target))) + "%";
    if (streakEl) {{
      // Count days in a row (going backwards from today) that hit target
      const byDay = {{}};
      appliedDates.forEach(d => {{ byDay[d] = (byDay[d] || 0) + 1; }});
      let streak = 0;
      let cur = new Date();
      for (let i = 0; i < 30; i++) {{
        const d = cur.toISOString().slice(0, 10);
        if ((byDay[d] || 0) >= target) {{ streak += 1; cur.setDate(cur.getDate() - 1); }}
        else break;
      }}
      streakEl.textContent = streak > 0 ? "\ud83d\udd25 " + streak + "-day streak" : "";
    }}
  }} catch (e) {{ /* swallow */ }}
}}


// G3 (2026-05-26): Render-time check that shows the "Follow up" and "Interview Prep"
// buttons on a card based on its tracker status.
function updateActionButtonsFor(fp) {{
  try {{
    const tr = (typeof getTracker === "function" ? getTracker() : {{}})[fp] || {{}};
    const st = (tr.status || "").toLowerCase();
    const when = (tr.statusChangedAt || tr.appliedAt || tr.updatedAt || "");
    const days = when ? Math.floor((Date.now() - new Date(when).getTime()) / 86400000) : 0;
    const card = document.querySelector('.card[data-fp="' + fp + '"]');
    if (!card) return;
    const fbtn = card.querySelector('[data-fp-followup]');
    const ibtn = card.querySelector('[data-fp-interview]');
    if (fbtn) fbtn.style.display = (st === "applied" && days >= 7) ? "" : "none";
    if (ibtn) ibtn.style.display = (st === "phonescreen" || st === "onsite" || st === "interview") ? "" : "none";
  }} catch(e) {{}}
}}
function updateActionButtonsAll() {{
  document.querySelectorAll('.card[data-fp]').forEach(function(c) {{
    updateActionButtonsFor(c.getAttribute("data-fp"));
  }});
}}

// Hook into the existing tracker plumbing — patch cycleStatus and decorateAllCards
// so they refresh the buttons after any status change.
(function patchForActionButtons() {{
  if (typeof cycleStatus === "function" && !cycleStatus._patchedG3) {{
    const orig = cycleStatus;
    window.cycleStatus = async function(fp, btn) {{
      const r = await orig.apply(this, arguments);
      try {{ updateActionButtonsFor(fp); }} catch(e) {{}}
      return r;
    }};
    window.cycleStatus._patchedG3 = true;
  }}
  if (typeof decorateAllCards === "function" && !decorateAllCards._patchedG3) {{
    const orig = decorateAllCards;
    window.decorateAllCards = function() {{
      const r = orig.apply(this, arguments);
      try {{ updateActionButtonsAll(); }} catch(e) {{}}
      return r;
    }};
    window.decorateAllCards._patchedG3 = true;
  }}
}})();

// Run once at load (deferred so the tracker has hydrated)
document.addEventListener("DOMContentLoaded", function() {{
  setTimeout(updateActionButtonsAll, 800);
}});

// Card-level openers — route to the existing detail-panel + tracker entries
function openFollowupFromCard(fp) {{
  // Set the current detail context, then open the followup composer that already exists
  if (typeof _currentDetailFp !== "undefined") window._currentDetailFp = fp;
  if (typeof openAppDetail === "function") {{
    openAppDetail(fp).then(function() {{
      if (typeof openFollowupDraft === "function") openFollowupDraft();
    }});
  }}
}}
function openInterviewPrepFromCard(fp) {{
  if (typeof _currentDetailFp !== "undefined") window._currentDetailFp = fp;
  if (typeof openAppDetail === "function") {{
    openAppDetail(fp).then(function() {{
      if (typeof openInterviewPrep === "function") openInterviewPrep();
    }});
  }}
}}

// G4 (2026-05-26): When the Prep modal opens with a fresh cover-letter result,
// auto-copy it to the clipboard so user can paste into the Greenhouse textarea.
(function autoCopyCoverLetter() {{
  function tryCopy(text) {{
    if (!text || !navigator.clipboard) return;
    navigator.clipboard.writeText(text).then(function() {{
      const banner = document.createElement("div");
      banner.style.cssText = "position:fixed;top:18px;right:18px;z-index:2147483647;background:#0a6b3a;color:white;padding:8px 12px;border-radius:6px;font-weight:600;font-size:13px;box-shadow:0 4px 14px rgba(0,0,0,0.18);";
      banner.textContent = "📋 Cover letter copied to clipboard — paste it into the apply form";
      document.body.appendChild(banner);
      setTimeout(function() {{ banner.remove(); }}, 6000);
    }}).catch(function() {{}});
  }}
  // Patch prepApplication so after it loads results, we copy.
  if (typeof prepApplication === "function" && !prepApplication._patchedG4) {{
    const orig = prepApplication;
    window.prepApplication = async function() {{
      const r = await orig.apply(this, arguments);
      // The original sets document.getElementById('prep-cover').textContent — read from there
      setTimeout(function() {{
        const el = document.getElementById("prep-cover") || document.getElementById("prep-coverLetter");
        if (el && el.textContent) tryCopy(el.textContent);
      }}, 600);
      return r;
    }};
    window.prepApplication._patchedG4 = true;
  }}
}})();



// G1 (2026-05-26): Guarantee that the grid is rendered in score-DESC order at
// page load. This is a belt-and-suspenders measure — the Python side already
// sorts by score, but the freshness boost + tracker reorders + filter() can
// shuffle the DOM. This runs once on load and after every filter/sort cycle.
(function ensureScoreSort() {{
  function sortGrid() {{
    const grid = document.getElementById("grid");
    if (!grid) return;
    const cards = Array.from(grid.querySelectorAll(".card"));
    if (cards.length < 2) return;
    cards.sort(function(a, b) {{
      const sa = parseInt(a.getAttribute("data-score") || "0", 10);
      const sb = parseInt(b.getAttribute("data-score") || "0", 10);
      if (sb !== sa) return sb - sa;
      // Tiebreak: most recent last-seen wins
      const la = (a.getAttribute("data-last-seen") || "");
      const lb = (b.getAttribute("data-last-seen") || "");
      return lb.localeCompare(la);
    }});
    // Re-attach in sorted order (using DocumentFragment for perf)
    const frag = document.createDocumentFragment();
    cards.forEach(function(c) {{ frag.appendChild(c); }});
    grid.appendChild(frag);
  }}
  document.addEventListener("DOMContentLoaded", function() {{
    setTimeout(sortGrid, 200);
  }});
  // Patch sortCards (the existing UI sort handler) to re-sort the grid afterwards
  if (typeof sortCards === "function" && !sortCards._patchedG1) {{
    const orig = sortCards;
    window.sortCards = function() {{
      const r = orig.apply(this, arguments);
      // Only re-sort to score-desc if user didn't pick a different sort
      const sel = document.getElementById("sortBy");
      if (!sel || sel.value === "score") {{
        setTimeout(sortGrid, 50);
      }}
      return r;
    }};
    window.sortCards._patchedG1 = true;
  }}
}})();

// === Daily Focus Panel (E6 / 2026-05-26) =========================
// Shows top-N highest-scoring cards as the "apply today" picks. N = the user's
// dailyTarget. Updates as the user marks jobs applied via the existing tracker.
async function refreshFocusPanel() {{
  const panel = document.getElementById("focus-panel");
  if (!panel) return;
  let N = (typeof loadDailyApplyTarget === "function") ? loadDailyApplyTarget() : 3;
  N = Math.max(3, Math.min(5, parseInt(N, 10) || 3));

  const grid = document.getElementById("grid");
  if (!grid) return;
  const today = new Date().toISOString().slice(0,10);
  const tracker = (typeof getTracker === "function") ? getTracker() : {{}};

  // Build company → dismissed-count map (engagement-aware penalty)
  const dismissedByCompany = {{}};
  Object.values(tracker || {{}}).forEach(function(r) {{
    if (!r || (r.status !== "dismissed" && r.status !== "rejected")) return;
    const co = ((r.jobMeta && r.jobMeta.company) || "").trim().toLowerCase();
    if (!co) return;
    dismissedByCompany[co] = (dismissedByCompany[co] || 0) + 1;
  }});

  // STAGE 3: fetch today's stamped picks. If present, lock the picks to that
  // exact fingerprint set so they don't shift through the day.
  // SELF-HEALING (2026-05-28): if the stamp violates the current
  // maxPerCompany cap (e.g. legacy stamp written before dedup was wired up,
  // or stamp from before user lowered their cap), discard and recompute.
  let stampedFps = null;
  try {{
    const r = await fetch(WORKER_BASE + "/api/picks" + USER_QS);
    if (r.ok) {{
      const j = await r.json();
      if (j && Array.isArray(j.fingerprints) && j.fingerprints.length > 0 && j.date === today) {{
        const stampMax = (typeof loadMaxPerCompany === "function") ? loadMaxPerCompany() : 1;
        const stampCo = {{}};
        let violates = false;
        for (const fp of j.fingerprints) {{
          const c = grid.querySelector('.card[data-fp="' + fp + '"]');
          if (!c) continue;
          const ce = c.querySelector(".company");
          const co = ce ? ce.textContent.trim().toLowerCase() : "";
          if (!co) continue;
          stampCo[co] = (stampCo[co] || 0) + 1;
          if (stampCo[co] > stampMax) {{ violates = true; break; }}
        }}
        if (violates) {{
          // Stale/invalid stamp — clear it server-side so other devices also
          // get the fresh compute, then fall through to recompute.
          try {{
            const ek = (typeof getEditKey === 'function') ? getEditKey() : null;
            const ak = (typeof getAdminKey === 'function') ? getAdminKey() : null;
            const headers = {{}};
            if (ek) headers['X-Edit-Key'] = ek;
            else if (ak) headers['X-Admin-Key'] = ak;
            fetch(WORKER_BASE + "/api/picks" + USER_QS, {{
              method: 'DELETE', headers
            }}).catch(() => {{}});
          }} catch (e) {{}}
          // stampedFps stays null → fresh-compute branch runs below
        }} else {{
          stampedFps = j.fingerprints;
        }}
      }}
    }}
  }} catch (e) {{}}

  // Get all visible cards, exclude already-decided + heavy-dismissed-company jobs
  const allCards = Array.from(grid.querySelectorAll(".card"));
  const candidates = allCards.filter(function(c) {{
    const fp = c.getAttribute("data-fp");
    const rec = tracker[fp];
    if (rec) {{
      const st = (rec.status || "").toLowerCase();
      if (["applied","phone","onsite","offer","rejected","dismissed","skipped"].indexOf(st) !== -1) return false;
    }}
    const compEl = c.querySelector(".company");
    const co = compEl ? compEl.textContent.trim().toLowerCase() : "";
    if (dismissedByCompany[co] && dismissedByCompany[co] >= 5) return false;
    return true;
  }});

  let picks;
  if (stampedFps) {{
    // Use stamped picks IF they're still in the live feed AND haven't been
    // applied to since the stamp. Maintain stamped order, fall through to
    // unstamped overflow only if some stamped picks have been applied.
    const stampedSet = new Set(stampedFps);
    const candidateByFp = {{}};
    candidates.forEach(c => {{ candidateByFp[c.getAttribute("data-fp")] = c; }});
    picks = [];
    for (const fp of stampedFps) {{
      if (candidateByFp[fp]) picks.push(candidateByFp[fp]);
    }}
    // If user has applied to some stamped picks, top up from candidates
    if (picks.length < N) {{
      const used = new Set(picks.map(c => c.getAttribute("data-fp")));
      const MAX_CO_TOPUP = (typeof loadMaxPerCompany === "function") ? loadMaxPerCompany() : 1;
      const perCompanyCountTopup = {{}};
      picks.forEach(c => {{
        const ce = c.querySelector(".company");
        const co = ce ? ce.textContent.trim().toLowerCase() : "";
        if (co) perCompanyCountTopup[co] = (perCompanyCountTopup[co] || 0) + 1;
      }});
      candidates.sort(function(a, b) {{
        if (typeof _sprintPriority === "function") return _sprintPriority(b) - _sprintPriority(a);
        return (parseInt(b.dataset.score || "0", 10)) - (parseInt(a.dataset.score || "0", 10));
      }});
      for (const c of candidates) {{
        if (picks.length >= N) break;
        const fp = c.getAttribute("data-fp");
        if (used.has(fp)) continue;
        const ce = c.querySelector(".company");
        const co = ce ? ce.textContent.trim().toLowerCase() : "";
        if (!co) continue;
        const cnt = perCompanyCountTopup[co] || 0;
        if (cnt >= MAX_CO_TOPUP) continue;
        perCompanyCountTopup[co] = cnt + 1;
        picks.push(c);
      }}
    }}
  }} else {{
    // No stamp for today — compute fresh + stamp.
    candidates.sort(function(a, b) {{
      if (typeof _sprintPriority === "function") return _sprintPriority(b) - _sprintPriority(a);
      return (parseInt(b.dataset.score || "0", 10)) - (parseInt(a.dataset.score || "0", 10));
    }});
    picks = [];
    const MAX_CO = (typeof loadMaxPerCompany === "function") ? loadMaxPerCompany() : 1;
    const perCompanyCount = {{}};
    for (const c of candidates) {{
      const compEl = c.querySelector(".company");
      const co = compEl ? compEl.textContent.trim().toLowerCase() : "";
      if (!co) continue;
      const cnt = perCompanyCount[co] || 0;
      if (cnt >= MAX_CO) continue;
      perCompanyCount[co] = cnt + 1;
      picks.push(c);
      if (picks.length >= N) break;
    }}
    // Best-effort stamp — fire and forget
    if (picks.length > 0) {{
      const ek = (typeof getEditKey === 'function') ? getEditKey() : null;
      const ak = (typeof getAdminKey === 'function') ? getAdminKey() : null;
      const headers = {{ 'Content-Type': 'application/json' }};
      if (ek) headers['X-Edit-Key'] = ek;
      else if (ak) headers['X-Admin-Key'] = ak;
      fetch(WORKER_BASE + "/api/picks" + USER_QS, {{
        method: 'POST', headers,
        body: JSON.stringify({{ fingerprints: picks.map(c => c.getAttribute("data-fp")) }})
      }}).catch(() => {{}});
    }}
  }}

  // Update header counts
  const ne = document.getElementById("focus-n");
  const ne2 = document.getElementById("focus-n-2");
  if (ne) ne.textContent = N;
  if (ne2) ne2.textContent = N;

  // Applied-today counter
  let appliedToday = 0;
  Object.values(tracker || {{}}).forEach(function(r) {{
    if (!r) return;
    const st = r.status || "";
    if (!st || st === "rejected" || st === "skipped") return;
    const when = (r.statusChangedAt || r.appliedAt || r.updatedAt || r.created_at || "").slice(0,10);
    if (when === today) appliedToday += 1;
  }});
  const ae = document.getElementById("focus-applied");
  if (ae) ae.textContent = appliedToday;
  const fill = document.getElementById("focus-progress-fill");
  if (fill) fill.style.width = Math.min(100, Math.round(appliedToday * 100 / Math.max(1, N))) + "%";

  // Confidence band labels
  function fitLabel(score) {{
    const n = parseInt(score, 10) || 0;
    if (n >= 85) return {{ label: "Very high fit", color: "#0a6b3a", bg: "#d1fae5" }};
    if (n >= 70) return {{ label: "Good fit",      color: "#1817B5", bg: "#dbeafe" }};
    return                {{ label: "Possible fit",  color: "#78350f", bg: "#fef3c7" }};
  }}

  // Why-this-pick reason
  function whyPick(c) {{
    const parts = [];
    if (c.querySelector(".contact-badge")) {{
      const cb = c.querySelector(".contact-badge");
      const isHiring = cb.classList.contains("hiring");
      parts.push(isHiring ? "warm intro to a recruiter here" : "warm-intro (you have a LinkedIn contact here)");
    }}
    if (c.querySelector(".just-posted-badge")) parts.push("posted in last 3 days");
    const mr = c.querySelector(".match-reason, .why-match");
    if (mr) {{
      const txt = (mr.textContent || "").replace(/^→ Match:\s*/, "").trim();
      if (txt) {{
        let snippet = txt.length > 90 ? txt.slice(0, 90).replace(/\s+\S*$/, "") + "…" : txt;
        parts.push(snippet);
      }}
    }}
    return parts.length ? parts.join(" · ") : null;
  }}

  // Render
  const list = document.getElementById("focus-list");
  if (list) {{
    list.innerHTML = "";
    if (picks.length === 0) {{
      list.innerHTML = '<div style="padding:20px;text-align:center;color:#666;font-size:13.5px;">' +
        '✨ You’ve applied to everything in today’s picks. Check the feed below for more, or come back tomorrow for fresh jobs.' +
        '</div>';
    }}
    picks.forEach(function(c, idx) {{
      const titleA = c.querySelector(".title a");
      const compEl = c.querySelector(".company");
      const score = c.getAttribute("data-score");
      const fp = c.getAttribute("data-fp");
      const titleTxt = titleA ? titleA.textContent.trim() : "?";
      const compTxt = compEl ? compEl.textContent.trim() : "?";
      const fit = fitLabel(score);
      const why = whyPick(c);
      const cardLink = c.querySelector('.title a, a[href][target="_blank"]');
      const applyUrl = cardLink ? cardLink.href : "#";

      const row = document.createElement("div");
      row.style.cssText = "background:#fff;border:1px solid #d8dbe6;border-radius:10px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.04);display:flex;flex-direction:column;gap:8px;";
      let html = '';
      html += '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">';
      html += '<span style="display:inline-block;min-width:24px;height:24px;line-height:24px;text-align:center;background:#5C5CD6;color:#fff;border-radius:50%;font-weight:700;font-size:12px;">' + (idx+1) + '</span>';
      html += '<a href="' + applyUrl + '" target="_blank" rel="noopener" style="flex:1;color:#1817B5;text-decoration:none;font-weight:700;font-size:15px;line-height:1.3;">' + _esc(titleTxt) + '</a>';
      html += '<span style="background:' + fit.bg + ';color:' + fit.color + ';padding:3px 9px;border-radius:10px;font-size:11px;font-weight:700;white-space:nowrap;">' + fit.label + '</span>';
      html += '</div>';
      html += '<div style="color:#444;font-size:13px;font-weight:500;">' + _esc(compTxt) + '</div>';
      if (why) {{
        html += '<div style="color:#5C5CD6;font-size:12.5px;font-style:italic;line-height:1.4;">→ ' + _esc(why) + '</div>';
      }}
      html += '<div style="display:flex;gap:8px;align-items:center;margin-top:2px;">';
      html += '<a href="' + applyUrl + '" target="_blank" rel="noopener" style="background:linear-gradient(135deg,#1817B5,#7C7CF0);color:#fff;padding:7px 14px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;">Apply →</a>';
      html += '<button data-jump-fp="' + fp + '" style="background:none;border:1px solid #d0d4dc;color:#666;padding:6px 12px;border-radius:6px;font-size:12.5px;cursor:pointer;">View full card</button>';
      html += '<span style="margin-left:auto;color:#888;font-size:11px;">score ' + score + '</span>';
      html += '</div>';
      row.innerHTML = html;
      list.appendChild(row);
    }});
    list.querySelectorAll('[data-jump-fp]').forEach(function(b) {{
      b.addEventListener('click', function(e) {{
        e.preventDefault();
        const fp = b.getAttribute('data-jump-fp');
        if (typeof window._focusJumpTo === 'function') window._focusJumpTo(fp);
      }});
    }});
  }}
}}

// Stage 3: explicit "refresh today's picks" — clears the stamp + recomputes.
window.refreshPicks = async function() {{
  const btn = document.getElementById("focus-refresh-btn");
  if (btn) {{ btn.disabled = true; btn.textContent = "…"; }}
  try {{
    const ek = (typeof getEditKey === 'function') ? getEditKey() : null;
    const ak = (typeof getAdminKey === 'function') ? getAdminKey() : null;
    const headers = {{}};
    if (ek) headers['X-Edit-Key'] = ek;
    else if (ak) headers['X-Admin-Key'] = ak;
    await fetch(WORKER_BASE + "/api/picks" + USER_QS, {{
      method: 'DELETE', headers
    }}).catch(() => {{}});
    if (typeof refreshFocusPanel === 'function') await refreshFocusPanel();
  }} finally {{
    if (btn) {{ btn.disabled = false; btn.textContent = "↻ refresh"; }}
  }}
}};

// Helper used by the pick-card "View full card" button
window._focusJumpTo = function(fp) {{
  const card = document.querySelector('.card[data-fp="' + fp + '"]');
  if (card) {{
    card.scrollIntoView({{ behavior: "smooth", block: "center" }});
    card.style.boxShadow = "0 0 0 3px #5C5CD6";
    setTimeout(function() {{ card.style.boxShadow = ""; }}, 2400);
  }}
}};

// Stage 2: concierge mode — when sprint is active, collapse the full feed under
// the focus panel so the picks are the hero. Toggle re-expands it.
window.toggleFullFeed = function() {{
  const grid = document.getElementById("grid");
  const btn = document.getElementById("focus-feed-toggle-btn");
  if (!grid || !btn) return;
  const isCollapsed = grid.dataset.feedCollapsed === "true";
  if (isCollapsed) {{
    grid.style.display = "";
    grid.dataset.feedCollapsed = "false";
  }} else {{
    grid.style.display = "none";
    grid.dataset.feedCollapsed = "true";
  }}
  _syncFocusFeedToggle();
}};

// Auto-collapse the feed on first load when sprint is active.
(function autoCollapseFeedInSprintMode() {{
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", function() {{ setTimeout(autoCollapseFeedInSprintMode, 200); }});
    return;
  }}
  setTimeout(function() {{
    const ha = document.querySelector(".header-actions");
    if (!ha || ha.dataset.sprintActive !== "true") return;
    const grid = document.getElementById("grid");
    if (!grid) return;
    if (grid.dataset.feedCollapsed === "true") return;
    grid.style.display = "none";
    grid.dataset.feedCollapsed = "true";
    const btn = document.getElementById("focus-feed-toggle-btn");
    if (btn) {{
      const total = grid.querySelectorAll(".card").length;
      btn.innerHTML = "View " + Math.max(0, total - 3) + " more matches ↓";
    }}
  }}, 500);
}})();

// Keep the "View N more matches" toggle text in sync with grid visibility
// and current card count. Called by refreshFocusPanel and on DOMContentLoaded.
function _syncFocusFeedToggle() {{
  const grid = document.getElementById("grid");
  const btn = document.getElementById("focus-feed-toggle-btn");
  if (!grid || !btn) return;
  const total = grid.querySelectorAll(".card").length;
  const N = (typeof loadDailyApplyTarget === "function") ? loadDailyApplyTarget() : 3;
  const moreCount = Math.max(0, total - N);
  const isCollapsed = grid.dataset.feedCollapsed === "true";
  if (isCollapsed) {{
    btn.innerHTML = "Show all " + total + " matches ↓";
  }} else {{
    if (moreCount > 0) {{
      btn.innerHTML = "Hide the " + moreCount + " other matches ↑";
    }} else {{
      btn.innerHTML = "No other matches — these are the only ones today";
      btn.disabled = true;
      btn.style.opacity = "0.6";
      btn.style.cursor = "default";
    }}
  }}
}}

// Light helper for HTML-escaping used in the panel rows
function _esc(s) {{
  return (s || "").replace(/[&<>"]/g, function(c) {{
    return ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }}[c]);
  }});
}}

// Initial render + re-render after tracker updates
document.addEventListener("DOMContentLoaded", function() {{
  setTimeout(function() {{
    refreshFocusPanel();
    setTimeout(_syncFocusFeedToggle, 600);
  }}, 400);
}});

function wizPickDailyTarget(n) {{
  const input = document.getElementById("wiz-daily-target");
  if (input) input.value = n;
}}
function loadDailyApplyTarget() {{
  // Clamped to 3-5: focused picks, not a long list. (2026-05-28)
  try {{ const n = parseInt(localStorage.getItem(DAILY_TARGET_KEY) || "3", 10); return Math.max(3, Math.min(5, n)); }} catch (e) {{ return 3; }}
}}

// --- Max per company for today's picks (2026-05-28) -------------------
// Lets the user control how many roles from the same company can show up
// in the focus panel. Default 1 = maximum variety.
const MAX_PER_COMPANY_KEY = "htj_max_per_company_" + USER_SLUG;
function loadMaxPerCompany() {{
  try {{
    const v = parseInt(localStorage.getItem(MAX_PER_COMPANY_KEY) || "1", 10);
    return (v >= 1 && v <= 999) ? v : 1;
  }} catch (e) {{ return 1; }}
}}
function _restoreMaxPerCompanySelect() {{
  try {{
    const sel = document.getElementById("maxPerCompanyFilter");
    if (sel) sel.value = String(loadMaxPerCompany());
  }} catch (e) {{}}
}}
window.changeMaxPerCompany = async function() {{
  const sel = document.getElementById("maxPerCompanyFilter");
  if (!sel) return;
  try {{ localStorage.setItem(MAX_PER_COMPANY_KEY, sel.value); }} catch (e) {{}}
  // Clear today's stamp so picks recompute with the new cap
  try {{
    const ek = (typeof getEditKey === 'function') ? getEditKey() : null;
    const ak = (typeof getAdminKey === 'function') ? getAdminKey() : null;
    const headers = {{}};
    if (ek) headers['X-Edit-Key'] = ek;
    else if (ak) headers['X-Admin-Key'] = ak;
    await fetch(WORKER_BASE + "/api/picks" + USER_QS, {{
      method: 'DELETE', headers
    }}).catch(() => {{}});
  }} catch (e) {{}}
  if (typeof refreshFocusPanel === 'function') await refreshFocusPanel();
}};
document.addEventListener("DOMContentLoaded", function() {{
  setTimeout(_restoreMaxPerCompanySelect, 100);
}});
// --- Hiring-role detection in LinkedIn contacts -----------------------
// A contact whose Position contains words like "recruiter", "talent",
// "hiring", "people ops", "VP HR" is a higher-priority warm intro than
// a random colleague — that's literally their job.
const HIRING_ROLE_KEYWORDS = [
  "recruiter", "recruiting", "sourcer", "sourcing",
  "talent acquisition", "ta partner", "ta specialist", "ta lead",
  "hiring", "people partner", "people ops", "people operations",
  "hr business partner", "hrbp", "head of hr", "vp hr", "vp of hr",
  "vp people", "chief people", "chief talent", "chro",
  "head of people", "head of talent", "head of recruiting"
];
function _isHiringRoleContact(c) {{
  const pos = ((c && (c.position || c.title)) || "").toLowerCase();
  if (!pos) return false;
  return HIRING_ROLE_KEYWORDS.some(k => pos.indexOf(k) !== -1);
}}


// --- Auth recovery modal ----------------------------------------------
// Surfaced whenever an auth-required action returns 401. Lets the user
// (a) paste a fresh invite URL OR (b) email Amit to resend one.
const ADMIN_EMAIL = "amittarora@gmail.com";

function recoveryShow() {{
  const o = document.getElementById("recovery-modal");
  if (!o) return;
  // Build the mailto link with prefilled subject/body
  const subj = encodeURIComponent("Please resend my invite link to getmemyjob");
  const body = encodeURIComponent(
    "Hi Amit,\\n\\n" +
    "My access key to my getmemyjob dashboard isn\'t working anymore. " +
    "Could you please resend a fresh invite link?\\n\\n" +
    "User slug: " + USER_SLUG + "\\n" +
    "Dashboard: " + window.location.origin + "/" + USER_SLUG + ".html\\n\\n" +
    "Thanks!"
  );
  const a = document.getElementById("recovery-mailto");
  if (a) a.href = "mailto:" + ADMIN_EMAIL + "?subject=" + subj + "&body=" + body;
  const status = document.getElementById("recovery-paste-status");
  if (status) {{ status.textContent = ""; status.className = "recovery-status"; }}
  o.classList.add("show");
}}
function recoveryHide() {{
  const o = document.getElementById("recovery-modal");
  if (o) o.classList.remove("show");
}}
function recoveryApplyPaste() {{
  const input = document.getElementById("recovery-paste-input");
  const status = document.getElementById("recovery-paste-status");
  if (!input || !status) return;
  const raw = (input.value || "").trim();
  if (!raw) {{
    status.className = "recovery-status err";
    status.textContent = "Paste your full invite URL here first.";
    return;
  }}
  // Extract ?key=... from the URL
  let key = null;
  try {{
    const u = new URL(raw);
    key = u.searchParams.get("key");
    // If the URL is for a different user, warn (but still store the key)
    const path = u.pathname.replace(/^\/+/, "").replace(/\.html$/, "");
    if (path && path !== USER_SLUG) {{
      status.className = "recovery-status err";
      status.textContent = "That URL is for user '" + path + "', not '" + USER_SLUG + "'. Open the right dashboard URL first.";
      return;
    }}
  }} catch (e) {{
    // Maybe they just pasted the key itself
    if (/^[a-zA-Z0-9_-]{{6,}}$/.test(raw)) key = raw;
  }}
  if (!key) {{
    status.className = "recovery-status err";
    status.textContent = "Couldn\'t find a ?key=... in that URL. Try the full invite link.";
    return;
  }}
  // Stash both per-user and legacy keys
  try {{
    localStorage.setItem("htj_resume_key_" + USER_SLUG, key);
    localStorage.setItem("htj_resume_key", key);
  }} catch (e) {{}}
  status.className = "recovery-status ok";
  status.textContent = "Saved. Retrying\u2026";
  // Auto-close and trigger a regen retry
  setTimeout(function() {{
    recoveryHide();
    const btn = document.getElementById("regen-btn");
    if (btn && typeof regenerateFromHeader === "function") regenerateFromHeader(btn);
  }}, 700);
}}


// Header "Regenerate matches" button — fires /regenerate-profile with
// whichever auth header the browser has cached. Tries X-Edit-Key first
// (per-user, from invite link). Falls back to X-Admin-Key (from admin.html)
// if the edit key is missing or rejected as invalid.
async function regenerateFromHeader(btn) {{
  const orig = btn.textContent;
  const editKey = (typeof getEditKey === "function")
    ? getEditKey()
    : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));
  const adminKey = localStorage.getItem("htj_admin_key");
  // Build attempts in order of preference
  const attempts = [];
  if (editKey) attempts.push({{ header: "X-Edit-Key", value: editKey, label: "edit key" }});
  if (adminKey) attempts.push({{ header: "X-Admin-Key", value: adminKey, label: "admin key" }});
  if (attempts.length === 0) {{
    wizBanner("Can't regenerate \u2014 no auth in this browser. Either re-open your invite link with ?key=\u2026, or open admin.html and sign in once first.");
    return;
  }}
  btn.disabled = true;
  btn.textContent = "Regenerating\u2026";
  wizBanner("Re-running the AI matcher with your latest preferences. Takes about 30\u201360 seconds.");
  let lastErr = "";
  for (let i = 0; i < attempts.length; i++) {{
    const a = attempts[i];
    try {{
      const r = await fetch(WORKER_BASE + "/regenerate-profile" + USER_QS, {{
        method: "POST",
        headers: {{ [a.header]: a.value }}
      }});
      const data = await r.json().catch(function() {{ return {{}}; }});
      if (r.ok && !(data && data.error)) {{
        const tcCount = ((data.profile || {{}}).targetCompanies || []).length;
        wizBanner("Generated " + tcCount + " personalized target companies via " + a.label + ". Triggering job refresh\u2026");
        try {{ fetch(WORKER_BASE + "/refresh", {{ method: "POST" }}); }} catch (e) {{}}
        btn.textContent = "Refreshing\u2026 (reload in 2\u20133 min)";
        btn.disabled = false;
        setTimeout(function() {{ btn.textContent = orig; }}, 12000);
        return;
      }}
      lastErr = (data && data.error) || ("HTTP " + r.status);
      // 401 → try the next auth method; other codes → give up
      if (r.status !== 401) break;
    }} catch (e) {{
      lastErr = "network error: " + (e.message || e);
      break;
    }}
  }}
  // If the failure looked like an auth problem, pop the recovery modal
  // instead of just a banner. Otherwise show the banner as before.
  if (/Invalid X-Edit-Key|Invalid X-Admin-Key|HTTP 401/.test(lastErr)) {{
    btn.textContent = orig;
    btn.disabled = false;
    recoveryShow();
    return;
  }}
  wizBanner("Regen failed: " + lastErr);
  btn.textContent = orig;
  btn.disabled = false;
}}


// ==============================================================
// Header "Refresh target companies" — bullseye-driven regen with
// a diff preview modal. Calls /regenerate-companies (dry_run first),
// shows what'll change, user confirms, then commits + triggers refresh.
// ==============================================================
async function regenerateCompaniesFromHeader(btn) {{
  const orig = btn.textContent;
  const editKey = (typeof getEditKey === "function")
    ? getEditKey()
    : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));
  const adminKey = localStorage.getItem("htj_admin_key");
  if (!editKey && !adminKey) {{
    alert("Can't refresh — no auth in this browser.\\nOpen your invite link or admin login (or admin login) first, then try again.");
    return;
  }}
  const headers = editKey ? {{ "X-Edit-Key": editKey }} : {{ "X-Admin-Key": adminKey }};

  btn.disabled = true;
  btn.textContent = "Asking AI…";
  try {{
    const r = await fetch(WORKER_BASE + "/regenerate-companies" + USER_QS, {{
      method: "POST",
      headers: Object.assign({{ "Content-Type": "application/json" }}, headers),
      body: JSON.stringify({{ dry_run: true }})
    }});
    const data = await r.json();
    if (!r.ok) {{
      wizBanner("Regen failed: " + (data.error || ("HTTP " + r.status)));
      btn.textContent = orig; btn.disabled = false; return;
    }}
    _showCompaniesDiffModal(data.proposed, data.diff, headers, btn, orig);
  }} catch (e) {{
    wizBanner("Network error: " + (e.message || e));
    btn.textContent = orig; btn.disabled = false;
  }}
}}

function _showCompaniesDiffModal(proposed, diff, headers, btn, origText) {{
  // Build/replace modal
  let m = document.getElementById("companies-diff-modal");
  if (m) m.remove();
  m = document.createElement("div");
  m.id = "companies-diff-modal";
  m.style.cssText = "position:fixed;inset:0;background:rgba(20,22,40,0.55);z-index:2147483600;display:flex;align-items:center;justify-content:center;padding:24px;font-family:Inter,system-ui,sans-serif;";

  const chip = (label, color, bg, border) =>
    '<span style="display:inline-block;padding:3px 9px;background:' + bg + ';color:' + color + ';border:1px solid ' + border + ';border-radius:12px;font-size:12px;margin:2px;">' + label + '</span>';

  const removingHtml = (diff.removing || []).map(c => chip((c && c.name ? c.name : c) + " ✕", "#B91C1C", "#FEF2F2", "#fecaca")).join('') || '<em style="color:#888;font-size:12px;">(nothing being removed)</em>';
  const addingHtml = (diff.adding || []).map(c => chip(c.name + " +", "#0a6b3a", "#ECFDF5", "#a7f3d0")).join('') || '<em style="color:#888;font-size:12px;">(nothing new being added)</em>';
  const keepingHtml = (diff.keeping || []).map(c => chip(c.name, "#3F3F46", "#F4F4F5", "#e4e4e7")).join('') || '<em style="color:#888;font-size:12px;">(no overlap with existing)</em>';

  m.innerHTML = ''
    + '<div style="background:white;border-radius:12px;max-width:780px;width:100%;max-height:80vh;display:flex;flex-direction:column;box-shadow:0 20px 50px rgba(0,0,0,0.3);">'
    + '  <div style="padding:18px 22px;border-bottom:1px solid #e6e8eb;display:flex;justify-content:space-between;align-items:center;">'
    + '    <h2 style="margin:0;font-size:18px;color:#1a1a2e;">Bullseye-driven target companies</h2>'
    + '    <button class="modal-close-btn" data-modal-id="companies-diff-modal" style="background:none;border:none;cursor:pointer;font-size:22px;color:#888;">×</button>'
    + '  </div>'
    + '  <div style="padding:16px 22px;overflow-y:auto;flex:1;">'
    + '    <div style="font-size:13px;color:#555;margin-bottom:12px;">AI re-derived ' + proposed.length + ' companies using only your 5/5/25 bullseye — not your raw resume. <strong>' + diff.summary + '.</strong></div>'
    + '    <div style="margin-bottom:14px;"><div style="font-size:13px;font-weight:600;color:#B91C1C;margin-bottom:6px;">Removing (' + (diff.removing || []).length + ')</div><div style="line-height:1.8;">' + removingHtml + '</div></div>'
    + '    <div style="margin-bottom:14px;"><div style="font-size:13px;font-weight:600;color:#0a6b3a;margin-bottom:6px;">Adding (' + (diff.adding || []).length + ')</div><div style="line-height:1.8;">' + addingHtml + '</div></div>'
    + '    <div style="margin-bottom:14px;"><div style="font-size:13px;font-weight:600;color:#3F3F46;margin-bottom:6px;">Keeping (' + (diff.keeping || []).length + ')</div><div style="line-height:1.8;">' + keepingHtml + '</div></div>'
    + '  </div>'
    + '  <div style="padding:14px 22px;border-top:1px solid #e6e8eb;display:flex;justify-content:flex-end;gap:10px;">'
    + '    <button id="companies-diff-cancel" style="padding:8px 18px;background:white;border:1px solid #d0d4dc;border-radius:6px;cursor:pointer;font-size:13px;">Cancel</button>'
    + '    <button id="companies-diff-confirm" style="padding:8px 18px;background:#5C5CD6;color:white;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">Confirm — save and refresh</button>'
    + '  </div>'
    + '</div>';

  document.body.appendChild(m);
  document.getElementById("companies-diff-cancel").addEventListener("click", () => {{
    m.remove();
    btn.textContent = origText;
    btn.disabled = false;
  }});
  document.getElementById("companies-diff-confirm").addEventListener("click", async () => {{
    const confirmBtn = document.getElementById("companies-diff-confirm");
    confirmBtn.disabled = true; confirmBtn.textContent = "Saving…";
    try {{
      const r = await fetch(WORKER_BASE + "/regenerate-companies" + USER_QS, {{
        method: "POST",
        headers: Object.assign({{ "Content-Type": "application/json" }}, headers),
        body: JSON.stringify({{ dry_run: false }})
      }});
      const data = await r.json();
      if (!r.ok) {{
        confirmBtn.textContent = "Failed: " + (data.error || r.status);
        confirmBtn.disabled = false;
        return;
      }}
      // Trigger refresh-jobs via the Worker /refresh endpoint
      try {{ fetch(WORKER_BASE + "/refresh", {{ method: "POST" }}); }} catch (e) {{}}
      m.remove();
      wizBanner("Saved " + (data.profile.targetCompanies || []).length + " new target companies. Job feed will refresh in ~5 min.");
      btn.textContent = "Refreshing…";
      setTimeout(() => {{ btn.textContent = origText; btn.disabled = false; }}, 10000);
    }} catch (e) {{
      confirmBtn.textContent = "Network error";
    }}
  }});
  // Backdrop click closes
  m.addEventListener("click", e => {{ if (e.target === m) {{ m.remove(); btn.textContent = origText; btn.disabled = false; }} }});
}}


// ==============================================================
// "Why isn't [X] in my feed?" debug tool
// _hiddenJobs is a JSON blob emitted by fetch_jobs.py at build time:
// up to 2000 dropped rows, each tagged with reason+detail.
// ==============================================================
const _HIDDEN_REASON_LABELS = {{
  irrelevant_title: 'Title is in the global blocklist (junior / IC / sales-rep / etc.)',
  never_relevant: 'Universal hard-exclude (back-office, IC engineers, pre-sales)',
  role_family_mismatch: 'Role family doesn\\'t match your primary-role family',
  negative_keyword: 'Blocked by your "things to never show me" list (word: %d)',
  salary_floor: 'Salary missing or below your floor',
  company_size: 'Company size %d is excluded by your size-mix preference',
  industry_mismatch: 'Industry doesn\\'t overlap with your 5 picks, and company isn\\'t on your targetCompanies allowlist',
  location: 'Location/remote preference mismatch (your pref: %d)',
  ghost: 'Job is stale (listed for %d) — possible ghost listing',
  dedup_or_truncated: 'Survived filters but didn\\'t make the top-50 cut (broaden bullseye for more) or was deduped across locations',
}};

function _hiddenReasonText(r) {{
  let t = _HIDDEN_REASON_LABELS[r.reason] || ('Unknown: ' + r.reason);
  return t.replace('%d', r.detail || '');
}}

function _hiddenReasonColor(reason) {{
  return {{
    negative_keyword: '#B91C1C',
    salary_floor: '#9A3412',
    industry_mismatch: '#7C2D12',
    role_family_mismatch: '#7C2D12',
    location: '#6B21A8',
    company_size: '#6B21A8',
    irrelevant_title: '#374151',
    never_relevant: '#374151',
    ghost: '#888',
    dedup_or_truncated: '#0EA5E9',
  }}[reason] || '#666';
}}

function showWhyHiddenModal() {{
  // Always create + append modal first, so even if anything below throws, the element is in DOM
  let m = document.getElementById('why-hidden-modal');
  if (m) m.remove();
  m = document.createElement('div');
  m.id = 'why-hidden-modal';
  m.style.cssText = 'position:fixed;inset:0;background:rgba(20,22,40,0.55);z-index:2147483700;display:flex;align-items:center;justify-content:center;padding:24px;font-family:Inter,system-ui,sans-serif;';
  document.body.appendChild(m);  // appendChild FIRST so the element is in DOM no matter what
  // Defensive read of _hiddenJobs (may be script-scoped const not on window in some contexts)
  let hiddenCount = 0;
  try {{ hiddenCount = (typeof _hiddenJobs !== 'undefined' && _hiddenJobs && _hiddenJobs.length) || 0; }} catch(_) {{ hiddenCount = 0; }}
  m.innerHTML = ''
    + '<div style="background:white;border-radius:12px;max-width:820px;width:100%;max-height:84vh;display:flex;flex-direction:column;box-shadow:0 20px 50px rgba(0,0,0,0.3);">'
    + '  <div style="padding:18px 22px;border-bottom:1px solid #e6e8eb;display:flex;justify-content:space-between;align-items:center;">'
    + '    <h2 style="margin:0;font-size:18px;color:#1a1a2e;">Why isn\\'t [company or title] in my feed?</h2>'
    + '    <button class="modal-close-btn" data-modal-id="why-hidden-modal" style="background:none;border:none;cursor:pointer;font-size:22px;color:#888;">×</button>'
    + '  </div>'
    + '  <div style="padding:14px 22px;border-bottom:1px solid #f0f1f5;">'
    + '    <input type="text" id="why-hidden-input" placeholder="Type a company name or job title (e.g. AuditBoard, VP)" style="width:100%;padding:9px 12px;font-size:14px;border:1px solid #d0d4dc;border-radius:6px;">'
    + '    <div style="font-size:12px;color:#888;margin-top:6px;">' + hiddenCount + ' hidden jobs indexed (top 2000 by score). Searches name + title.</div>'
    + '  </div>'
    + '  <div id="why-hidden-results" style="padding:8px 22px 18px;overflow-y:auto;flex:1;">'
    + '    <div style="color:#888;font-size:13px;font-style:italic;padding:10px 0;">Type a company or title above to see what\\'s hidden and why.</div>'
    + '  </div>'
    + '</div>';
  const inp = document.getElementById('why-hidden-input');
  const out = document.getElementById('why-hidden-results');
  // Defensive snapshot — works whether _hiddenJobs is script-scoped const or window global
  let _hj = [];
  try {{ _hj = (typeof _hiddenJobs !== 'undefined' && Array.isArray(_hiddenJobs)) ? _hiddenJobs : []; }} catch(_) {{ _hj = []; }}
  const renderResults = (q) => {{
    const ql = (q || '').toLowerCase().trim();
    if (!ql) {{
      out.innerHTML = '<div style="color:#888;font-size:13px;font-style:italic;padding:10px 0;">Type a company or title above to see what\\'s hidden and why.</div>';
      return;
    }}
    if (!_hj || !_hj.length) {{
      out.innerHTML = '<div style="color:#B91C1C;font-size:13px;">No hidden-jobs data on this page (dashboard built before this feature shipped). Wait for next refresh-jobs run.</div>';
      return;
    }}
    const matches = _hj.filter(j => (j.company || '').toLowerCase().includes(ql) || (j.title || '').toLowerCase().includes(ql)).slice(0, 50);
    if (!matches.length) {{
      out.innerHTML = '<div style="color:#888;font-size:13px;padding:10px 0;">No hidden jobs match <strong>' + escHtml(q) + '</strong>. Either: (a) no such company in our scrape, (b) all their jobs are visible to you (check the grid).</div>';
      return;
    }}
    // Group by reason for summary at top
    const byReason = {{}};
    matches.forEach(j => {{ byReason[j.reason] = (byReason[j.reason] || 0) + 1; }});
    const summaryChips = Object.entries(byReason).sort((a,b)=>b[1]-a[1]).map(([reason, n]) => {{
      const color = _hiddenReasonColor(reason);
      return '<span style="display:inline-block;padding:2px 8px;background:' + color + '22;color:' + color + ';border:1px solid ' + color + '44;border-radius:10px;font-size:11px;margin:2px;">' + reason.replace(/_/g, ' ') + ': ' + n + '</span>';
    }}).join('');
    out.innerHTML = ''
      + '<div style="font-size:12.5px;color:#555;margin:6px 0 12px;"><strong>' + matches.length + '</strong> hidden job' + (matches.length === 1 ? '' : 's') + ' matching <strong>' + escHtml(q) + '</strong>. Breakdown: ' + summaryChips + '</div>'
      + '<div style="border-top:1px solid #f0f1f5;">' + matches.map(j => {{
        const c = _hiddenReasonColor(j.reason);
        return ''
          + '<div style="padding:9px 0;border-bottom:1px solid #f0f1f5;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">'
          + '  <div style="flex:1;min-width:0;">'
          + '    <div style="font-size:13px;font-weight:600;color:#1a1a2e;">' + escHtml(j.title) + '</div>'
          + '    <div style="font-size:12px;color:#666;margin-top:2px;">' + escHtml(j.company) + (j.location ? ' • ' + escHtml(j.location) : '') + ' • base score ' + j.score + '</div>'
          + '    <div style="font-size:12px;color:' + c + ';margin-top:4px;">→ ' + _hiddenReasonText(j) + '</div>'
          + '  </div>'
          + '</div>';
      }}).join('') + '</div>';
  }};
  inp.addEventListener('input', () => renderResults(inp.value));
  inp.focus();
  m.addEventListener('click', e => {{ if (e.target === m) m.remove(); }});
}}


// ==============================================================
// Engagement-driven refinement suggestions
// Pulls from /suggest-refinements (Claude reads tracker patterns +
// compares to bullseye). Shows a dismissable banner with 1-click apply.
// Throttled to once per 24h per dismissal.
// ==============================================================
const _REFINE_SUGG_CACHE_KEY = 'htj_refine_sugg_' + USER_SLUG;
const _REFINE_SUGG_DISMISS_KEY = 'htj_refine_sugg_dismissed_' + USER_SLUG;
const _REFINE_SUGG_TTL = 24 * 60 * 60 * 1000;

async function _checkRefinementSuggestions() {{
  // Don't bother more than once per 12h
  try {{
    const cached = JSON.parse(localStorage.getItem(_REFINE_SUGG_CACHE_KEY) || 'null');
    if (cached && cached.ts && (Date.now() - cached.ts) < 12 * 60 * 60 * 1000) {{
      _renderRefinementBanner(cached.suggestions || []);
      return;
    }}
  }} catch (e) {{}}

  const ek = (typeof getEditKey === 'function') ? getEditKey() : null;
  if (!ek) return; // anon user — skip

  try {{
    const r = await fetch(WORKER_BASE + '/suggest-refinements' + USER_QS, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': ek }}
    }});
    if (!r.ok) return;
    const data = await r.json();
    const suggs = data.suggestions || [];
    try {{ localStorage.setItem(_REFINE_SUGG_CACHE_KEY, JSON.stringify({{ ts: Date.now(), suggestions: suggs, meta: data.meta }})); }} catch (e) {{}}
    _renderRefinementBanner(suggs);
  }} catch (e) {{ /* silent */ }}
}}

function _isRefineSuggDismissed(sigKey) {{
  try {{
    const dis = JSON.parse(localStorage.getItem(_REFINE_SUGG_DISMISS_KEY) || '{{}}');
    return dis[sigKey] && (Date.now() - dis[sigKey]) < 7 * 24 * 60 * 60 * 1000;
  }} catch (e) {{ return false; }}
}}

function _markRefineSuggDismissed(sigKey) {{
  try {{
    const dis = JSON.parse(localStorage.getItem(_REFINE_SUGG_DISMISS_KEY) || '{{}}');
    dis[sigKey] = Date.now();
    localStorage.setItem(_REFINE_SUGG_DISMISS_KEY, JSON.stringify(dis));
  }} catch (e) {{}}
}}

function _renderRefinementBanner(suggestions) {{
  // Filter out dismissed
  const active = (suggestions || []).filter(s => {{
    const k = s.type + ':' + s.field + ':' + s.value;
    return !_isRefineSuggDismissed(k);
  }});
  if (!active.length) return;
  // Remove any existing banner
  const existing = document.getElementById('refine-sugg-banner');
  if (existing) existing.remove();

  const banner = document.createElement('div');
  banner.id = 'refine-sugg-banner';
  banner.style.cssText = 'background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:12px 16px;margin:0 auto 14px;max-width:1400px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-family:Inter,system-ui,sans-serif;';

  const lead = document.createElement('div');
  lead.style.cssText = 'font-size:13px;color:#78350f;flex:1;min-width:220px;';
  lead.innerHTML = '<strong style="font-size:14px;">💡 ' + active.length + ' suggestion' + (active.length === 1 ? '' : 's') + ' from your activity:</strong>';
  banner.appendChild(lead);

  const list = document.createElement('div');
  list.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px;flex:2;';

  active.slice(0, 3).forEach((s, idx) => {{
    const chip = document.createElement('div');
    chip.style.cssText = 'display:flex;align-items:center;gap:6px;padding:6px 12px;background:white;border:1px solid #fcd34d;border-radius:6px;font-size:12.5px;';
    const verb = s.type.startsWith('add_') ? 'Add' : 'Remove';
    const label = document.createElement('span');
    label.style.cssText = 'color:#444;';
    label.innerHTML = '<strong>' + verb + ' "' + escHtml(s.value) + '"</strong> to ' + escHtml(s.field) + '<br><span style="font-size:11px;color:#888;font-style:italic;">' + escHtml(s.evidence || '') + '</span>';
    chip.appendChild(label);
    const apply = document.createElement('button');
    apply.type = 'button';
    apply.textContent = '✓ Apply';
    apply.style.cssText = 'padding:4px 10px;font-size:11px;background:#16a34a;color:white;border:none;border-radius:4px;cursor:pointer;font-weight:600;';
    apply.addEventListener('click', () => _applyRefinement(s, chip));
    chip.appendChild(apply);
    const skip = document.createElement('button');
    skip.type = 'button';
    skip.textContent = '×';
    skip.title = 'Dismiss for 7 days';
    skip.style.cssText = 'padding:4px 8px;font-size:14px;background:none;color:#888;border:none;border-radius:4px;cursor:pointer;';
    skip.addEventListener('click', () => {{
      _markRefineSuggDismissed(s.type + ':' + s.field + ':' + s.value);
      chip.remove();
      // If all gone, kill the banner
      if (!list.children.length) banner.remove();
    }});
    chip.appendChild(skip);
    list.appendChild(chip);
  }});
  banner.appendChild(list);

  // Insert before the stats row
  const stats = document.querySelector('.stats');
  if (stats && stats.parentNode) {{
    stats.parentNode.insertBefore(banner, stats);
  }} else {{
    document.body.insertBefore(banner, document.body.firstChild);
  }}
}}

async function _applyRefinement(suggestion, chipEl) {{
  const ek = (typeof getEditKey === 'function') ? getEditKey() : null;
  if (!ek) {{ alert('No edit key — cannot save'); return; }}
  // Fetch current profile to compute the new array
  try {{
    const r = await fetch(WORKER_BASE + '/skills-profile' + USER_QS + '&_=' + Date.now(), {{ cache: 'no-store' }});
    const p = (await r.json()).profile || {{}};
    const field = suggestion.field;
    const cur = (p[field] || []).slice();
    const val = (suggestion.value || '').toLowerCase().trim();
    if (suggestion.type.startsWith('add_')) {{
      if (!cur.includes(val)) cur.push(val);
    }} else if (suggestion.type.startsWith('remove_')) {{
      const idx = cur.indexOf(val);
      if (idx >= 0) cur.splice(idx, 1);
    }}
    const r2 = await fetch(WORKER_BASE + '/skills-profile' + USER_QS, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json', 'X-Edit-Key': ek }},
      body: JSON.stringify({{ patchFields: {{ [field]: cur }} }})
    }});
    if (r2.ok) {{
      chipEl.style.background = '#ecfdf5';
      chipEl.innerHTML = '<span style="color:#0a6b3a;font-size:12.5px;font-weight:600;">✓ Applied — refresh in 5 min to see new ranking</span>';
      _markRefineSuggDismissed(suggestion.type + ':' + suggestion.field + ':' + suggestion.value);
    }} else {{
      chipEl.innerHTML = '<span style="color:#B91C1C;">Failed: HTTP ' + r2.status + '</span>';
    }}
  }} catch (e) {{
    chipEl.innerHTML = '<span style="color:#B91C1C;">Error: ' + (e.message || e) + '</span>';
  }}
}}


// --- Wizard step 5: company-size mix sliders ---------------------------
// Drag any slider; the other two auto-adjust proportionally so the
// total stays at 100. Same when a number input is typed.
function _wizMixRebalance(changedKey) {{
  // Rebalance N-way mix (currently 4-way: startup/midsize/large/consulting).
  // Scales the OTHER sliders proportionally so the total stays at 100.
  const KEYS = ["startup", "midsize", "large", "consulting"];
  // Only operate on keys present in the DOM (back-compat with legacy 3-way render)
  const keys = KEYS.filter(function(k) {{ return !!document.getElementById("wiz-mix-" + k); }});
  if (keys.length < 2) return;
  const vals = {{}};
  keys.forEach(function(k) {{
    const el = document.getElementById("wiz-mix-" + k);
    vals[k] = Math.max(0, Math.min(100, parseInt(el.value, 10) || 0));
  }});
  const others = keys.filter(function(k) {{ return k !== changedKey; }});
  const remaining = 100 - vals[changedKey];
  if (remaining <= 0) {{
    vals[changedKey] = 100;
    others.forEach(function(k) {{ vals[k] = 0; }});
  }} else {{
    const otherSum = others.reduce(function(a, k) {{ return a + vals[k]; }}, 0);
    if (otherSum === 0) {{
      // Distribute evenly when all others are at 0
      const base = Math.floor(remaining / others.length);
      const rem = remaining - base * others.length;
      others.forEach(function(k, i) {{ vals[k] = base + (i < rem ? 1 : 0); }});
    }} else {{
      // Proportional rebalance, then snap the LAST other so total is exact
      let allocated = 0;
      others.forEach(function(k, i) {{
        if (i === others.length - 1) {{
          vals[k] = remaining - allocated;
        }} else {{
          const share = Math.round(vals[k] / otherSum * remaining);
          vals[k] = share;
          allocated += share;
        }}
      }});
    }}
  }}
  keys.forEach(function(k) {{
    const slider = document.getElementById("wiz-mix-" + k);
    const num    = document.getElementById("wiz-mix-" + k + "-num");
    const valLbl = document.getElementById("wiz-mix-" + k + "-val");
    if (slider) slider.value = vals[k];
    if (num)    num.value    = vals[k];
    if (valLbl) valLbl.textContent = vals[k] + "%";
  }});
  const total = vals.startup + vals.midsize + vals.large;
  const sumEl   = document.getElementById("wiz-mix-sum-val");      // legacy id, may not exist
  const totalEl = document.getElementById("wiz-mix-total");        // current id used in primary UI
  if (sumEl)   sumEl.textContent   = total;
  if (totalEl) {{
    totalEl.textContent = "Total: " + total + "%";
    // Visual cue: red if !=100, normal otherwise
    totalEl.style.color = (total === 100) ? "" : "#B91C1C";
  }}
}}
function wizMixOnSlide(key) {{ _wizMixRebalance(key); }}
function wizMixOnNum(key) {{
  const num = document.getElementById("wiz-mix-" + key + "-num");
  const slider = document.getElementById("wiz-mix-" + key);
  if (num && slider) slider.value = num.value;
  _wizMixRebalance(key);
}}


// --- Wizard: title/industry/skills match-weight sliders -----------------
function _wizWtRebalance(changedKey) {{
  const keys = ["titles", "industries", "skills"];
  const vals = {{}};
  keys.forEach(function(k) {{
    const el = document.getElementById("wiz-wt-" + k);
    vals[k] = Math.max(0, Math.min(100, parseInt(el && el.value, 10) || 0));
  }});
  const others = keys.filter(function(k) {{ return k !== changedKey; }});
  const remaining = 100 - vals[changedKey];
  if (remaining <= 0) {{
    vals[changedKey] = 100;
    others.forEach(function(k) {{ vals[k] = 0; }});
  }} else {{
    const otherSum = vals[others[0]] + vals[others[1]];
    if (otherSum === 0) {{
      const half = Math.floor(remaining / 2);
      vals[others[0]] = half;
      vals[others[1]] = remaining - half;
    }} else {{
      vals[others[0]] = Math.round(vals[others[0]] / otherSum * remaining);
      vals[others[1]] = remaining - vals[others[0]];
    }}
  }}
  keys.forEach(function(k) {{
    const slider = document.getElementById("wiz-wt-" + k);
    const num = document.getElementById("wiz-wt-" + k + "-num");
    if (slider) slider.value = vals[k];
    if (num) num.value = vals[k];
  }});
  const sumEl = document.getElementById("wiz-wt-sum-val");
  if (sumEl) sumEl.textContent = vals.titles + vals.industries + vals.skills;
}}
function wizWtOnSlide(key) {{ _wizWtRebalance(key); }}
function wizWtOnNum(key) {{
  const num = document.getElementById("wiz-wt-" + key + "-num");
  const slider = document.getElementById("wiz-wt-" + key);
  if (num && slider) slider.value = num.value;
  _wizWtRebalance(key);
}}
function wizWtPrefill() {{
  fetch(WORKER_BASE + "/skills-profile" + USER_QS).then(function(r){{return r.json();}}).then(function(d){{
    const w = (d && d.profile && d.profile.matchWeights) || {{ titles: 50, industries: 25, skills: 25 }};
    ["titles","industries","skills"].forEach(function(k){{
      const s = document.getElementById("wiz-wt-" + k);
      const n = document.getElementById("wiz-wt-" + k + "-num");
      const v = Math.max(0, Math.min(100, parseInt(w[k], 10) || 0));
      if (s) s.value = v;
      if (n) n.value = v;
    }});
    const sum = (parseInt(w.titles,10)||0)+(parseInt(w.industries,10)||0)+(parseInt(w.skills,10)||0);
    const sumEl = document.getElementById("wiz-wt-sum-val");
    if (sumEl) sumEl.textContent = sum;
  }}).catch(function(){{}});
}}

(function wizardSetup() {{
  function setup() {{
    const cta = document.getElementById("wiz-cta");
    const back = document.getElementById("wiz-back");
    const skip = document.getElementById("wiz-skip");
    if (!cta || !back || !skip) return;

    cta.addEventListener("click", function() {{
      const s = WIZ_STEPS[wizCurrent];
      if (s.action === "next") {{ wizAdvance(); return; }}
      if (s.action === "open-resume") {{
        wizHide();
        try {{ openResumeModal(); }} catch(e) {{ console.error(e); }}
        window._wizExpect = "resume";
        return;
      }}
      if (s.action === "open-resume-profile") {{
        wizHide();
        try {{ openResumeModal(); }} catch(e) {{ console.error(e); }}
        setTimeout(function() {{
          const tabs = document.querySelectorAll(".tab-btn");
          for (let i = 0; i < tabs.length; i++) {{
            if (tabs[i].textContent.toLowerCase().indexOf("profile") !== -1) {{ tabs[i].click(); break; }}
          }}
        }}, 300);
        window._wizExpect = "profile";
        return;
      }}
      if (s.action === "open-contacts") {{
        wizHide();
        try {{ openContactsModal(); }} catch(e) {{ console.error(e); }}
        window._wizExpect = "contacts";
        return;
      }}
      if (s.action === "verify-extension") {{
        const installed = (document.documentElement.getAttribute("data-gmj-installed") === "1") || window.__gmj_extension_ready === true;
        const statusEl = document.getElementById("wiz-ext-status");
        if (installed) {{
          if (statusEl) {{ statusEl.style.color = "#0a6b3a"; statusEl.textContent = "✅ Extension installed. Continuing…"; }}
          if (window._wizExtPoll) {{ clearInterval(window._wizExtPoll); window._wizExtPoll = null; }}
          try {{ localStorage.removeItem("gmj_wizard_resume_at"); }} catch(e) {{}}
          setTimeout(wizAdvance, 600);
        }} else {{
          if (statusEl) {{
            statusEl.style.color = "#b00";
            statusEl.innerHTML = '❌ Not detected. If you just installed the extension, Chrome does not inject it into tabs that were already open — click <strong>Reload page &amp; re-check</strong> below.';
          }}
        }}
        return;
      }}
            if (s.action === "save-app-profile") {{
        const phone = (document.getElementById("wiz-app-phone")||{{}}).value || "";
        const location = (document.getElementById("wiz-app-location")||{{}}).value || "";
        const linkedin = (document.getElementById("wiz-app-linkedin")||{{}}).value || "";
        const wauth = (document.getElementById("wiz-app-workauth")||{{}}).value || "US Citizen";
        const sponsor = (document.getElementById("wiz-app-sponsor")||{{}}).value || "No";
        const statusEl = document.getElementById("wiz-app-status");
        const editKey = (typeof getEditKey === "function") ? getEditKey() : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));
        if (!editKey) {{ if (statusEl) statusEl.textContent = "No edit key — continuing without save."; setTimeout(wizAdvance, 800); return; }}
        if (statusEl) statusEl.textContent = "Saving…";
        const ctaBtn = document.getElementById("wiz-cta");
        if (ctaBtn) ctaBtn.disabled = true;
        fetch(PROFILE_WORKER_URL, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json", "X-Edit-Key": editKey }},
          body: JSON.stringify({{ patchFields: {{ phone: phone, location: location, linkedinUrl: linkedin, workAuthorization: wauth, requiresSponsorship: sponsor }} }})
        }})
          .then(function(r){{ return r.json(); }})
          .then(function(d){{
            if (ctaBtn) ctaBtn.disabled = false;
            if (statusEl) statusEl.textContent = "Saved ✓";
            setTimeout(wizAdvance, 400);
          }})
          .catch(function(){{
            if (ctaBtn) ctaBtn.disabled = false;
            if (statusEl) statusEl.textContent = "Network error — continuing.";
            setTimeout(wizAdvance, 800);
          }});
        return;
      }}
            if (s.action === "save-location-remote") {{
        const locsInput = document.getElementById("wiz-locs");
        const remoteSel = document.getElementById("wiz-remote");
        const statusEl = document.getElementById("wiz-locs-status");
        if (!locsInput || !remoteSel) {{ wizAdvance(); return; }}
        const locs = locsInput.value.split(",").map(function(x){{ return x.trim(); }}).filter(Boolean);
        const remotePref = remoteSel.value || "any";
        if (statusEl) statusEl.textContent = "Saving\u2026";
        const editKey = (typeof getEditKey === "function") ? getEditKey() : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));
        if (!editKey) {{
          if (statusEl) statusEl.textContent = "No edit key found \u2014 your changes can't be saved. Skipping.";
          setTimeout(wizAdvance, 1200);
          return;
        }}
        const ctaBtn = document.getElementById("wiz-cta");
        if (ctaBtn) ctaBtn.disabled = true;
        fetch(PROFILE_WORKER_URL, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json", "X-Edit-Key": editKey }},
          body: JSON.stringify({{ patchFields: {{ preferredLocations: locs, remotePreference: remotePref }} }})
        }})
          .then(function(r){{ return r.json().then(function(d){{ return {{ ok: r.ok, status: r.status, data: d }}; }}); }})
          .then(function(res){{
            if (!res.ok || (res.data && res.data.error)) {{
              if (statusEl) statusEl.textContent = "Save failed (" + (res.data.error || ("HTTP " + res.status)) + ") \u2014 continuing anyway.";
              setTimeout(wizAdvance, 1500);
            }} else {{
              if (statusEl) statusEl.textContent = "Saved.";
              setTimeout(function(){{
                if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
                else {{ wizAdvance(); }}
              }}, 400);
            }}
          }})
          .catch(function(e){{
            if (statusEl) statusEl.textContent = "Network error \u2014 continuing anyway.";
            setTimeout(function(){{
              if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
              else {{ wizAdvance(); }}
            }}, 1200);
          }})
          .finally(function(){{ if (ctaBtn) ctaBtn.disabled = false; }});
        return;
      }}
      if (s.action === "save-match-weights") {{
        const t = parseInt((document.getElementById("wiz-wt-titles")||{{}}).value,10) || 0;
        const i = parseInt((document.getElementById("wiz-wt-industries")||{{}}).value,10) || 0;
        const k = parseInt((document.getElementById("wiz-wt-skills")||{{}}).value,10) || 0;
        const total = t + i + k;
        if (Math.abs(total - 100) > 1) {{ alert("Weights must sum to 100. Currently " + total + "."); return; }}
        const msgEl = document.getElementById("wiz-wt-msg");
        const editKey = (typeof getEditKey === "function") ? getEditKey() : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));
        if (!editKey) {{
          if (msgEl) msgEl.textContent = "No edit key — skipping save.";
          setTimeout(wizAdvance, 800);
          return;
        }}
        if (msgEl) {{ msgEl.style.color="#666"; msgEl.textContent = "Saving…"; }}
        const ctaBtn = document.getElementById("wiz-cta");
        if (ctaBtn) ctaBtn.disabled = true;
        fetch(PROFILE_WORKER_URL, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json", "X-Edit-Key": editKey }},
          body: JSON.stringify({{ patchFields: {{ matchWeights: {{ titles: t, industries: i, skills: k }} }} }})
        }}).then(function(r){{return r.json();}}).then(function(d){{
          if (ctaBtn) ctaBtn.disabled = false;
          if (d && (d.ok || d.profile)) {{
            if (msgEl) {{ msgEl.style.color="#0a6b3a"; msgEl.textContent = "Saved."; }}
            setTimeout(wizAdvance, 400);
          }} else {{
            if (msgEl) {{ msgEl.style.color="#b00"; msgEl.textContent = (d && d.error) || "Save failed."; }}
          }}
        }}).catch(function(e){{
          if (ctaBtn) ctaBtn.disabled = false;
          if (msgEl) {{ msgEl.style.color="#b00"; msgEl.textContent = "Network error."; }}
        }});
        return;
      }}
      if (s.action === "save-company-sizes") {{
        const statusEl = document.getElementById("wiz-mix-msg");
        function _readVal(k) {{
          const el = document.getElementById("wiz-mix-" + k);
          return Math.max(0, Math.min(100, parseInt(el ? el.value : 0, 10) || 0));
        }}
        const mix = {{
          startup: _readVal("startup"),
          midsize: _readVal("midsize"),
          large: _readVal("large")
        }};
        const total = mix.startup + mix.midsize + mix.large;
        if (total !== 100) {{
          // Normalize so sum == 100 (rounding-safe)
          if (total === 0) {{ mix.startup = 33; mix.midsize = 33; mix.large = 34; }}
          else {{
            mix.startup = Math.round(mix.startup * 100 / total);
            mix.midsize = Math.round(mix.midsize * 100 / total);
            mix.large = 100 - mix.startup - mix.midsize;
          }}
        }}
        const derivedPrefs = ["startup","midsize","large"].filter(function(k){{ return mix[k] > 0; }});
        if (statusEl) {{ statusEl.style.color = "#888"; statusEl.textContent = "Saving\u2026"; }}
        const editKey = (typeof getEditKey === "function") ? getEditKey() : (localStorage.getItem("htj_resume_key_" + USER_SLUG) || localStorage.getItem("htj_resume_key"));
        if (!editKey) {{
          if (statusEl) statusEl.textContent = "No edit key in this browser \u2014 your choice can't be saved. Skipping.";
          setTimeout(wizAdvance, 1200);
          return;
        }}
        const ctaBtn = document.getElementById("wiz-cta");
        if (ctaBtn) ctaBtn.disabled = true;
        fetch(PROFILE_WORKER_URL, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json", "X-Edit-Key": editKey }},
          body: JSON.stringify({{ patchFields: {{ companySizeMix: mix, companySizePreferences: derivedPrefs }} }})
        }})
          .then(function(r){{ return r.json().then(function(d){{ return {{ ok: r.ok, status: r.status, data: d }}; }}); }})
          .then(function(res){{
            if (!res.ok || (res.data && res.data.error)) {{
              if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Save failed (" + (res.data.error || ("HTTP " + res.status)) + ") \u2014 continuing."; }}
              setTimeout(wizAdvance, 1500);
            }} else {{
              if (statusEl) {{ statusEl.style.color = "#0a6b3a"; statusEl.textContent = "Saved: " + mix.startup + "/" + mix.midsize + "/" + mix.large + " (startup/mid/large)."; }}
              setTimeout(function(){{
                if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
                else {{ wizAdvance(); }}
              }}, 600);
            }}
          }})
          .catch(function(e){{
            if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Network error \u2014 continuing."; }}
            setTimeout(function(){{
              if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
              else {{ wizAdvance(); }}
            }}, 1200);
          }})
          .finally(function(){{ if (ctaBtn) ctaBtn.disabled = false; }});
        return;
      }}
      if (s.action === "save-profile-chips") {{
        const statusEl = document.getElementById("wiz-chip-save-status");
        if (!_wizChipLoaded) {{ if (statusEl) statusEl.textContent = "Profile didn\'t load \u2014 skipping."; setTimeout(function() {{ if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }} else {{ wizAdvance(); }} }}, 800); return; }}
        let editKey = (typeof getEditKey === "function") ? getEditKey() : null;
        const adminKey = localStorage.getItem("htj_admin_key");
        const authHeader = editKey ? {{ "X-Edit-Key": editKey }} : (adminKey ? {{ "X-Admin-Key": adminKey }} : null);
        if (!authHeader) {{
          if (statusEl) statusEl.textContent = "Session expired \u2014 click Confirm to verify.";
          if (typeof showVerifyModal === "function") showVerifyModal(function() {{ wizAdvance(); }});
          return;
        }}
        if (statusEl) {{ statusEl.style.color = "#888"; statusEl.textContent = "Saving\u2026"; }}
        const ctaBtn = document.getElementById("wiz-cta");
        if (ctaBtn) ctaBtn.disabled = true;
        fetch(PROFILE_WORKER_URL, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json", "X-Edit-Key": editKey }},
          body: JSON.stringify({{ patchFields: {{
            targetTitles: _wizChipState.targetTitles,
            industries: _wizChipState.industries,
            keywords: _wizChipState.keywords,
            specialties: _wizChipState.specialties,
          }} }})
        }})
          .then(function(r) {{ return r.json().then(function(d) {{ return {{ ok: r.ok, status: r.status, data: d }}; }}); }})
          .then(function(res) {{
            if (!res.ok || (res.data && res.data.error)) {{
              if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Save failed (" + (res.data.error || ("HTTP " + res.status)) + ") \u2014 continuing."; }}
              setTimeout(function() {{ if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }} else {{ wizAdvance(); }} }}, 1500);
            }} else {{
              if (statusEl) {{ statusEl.style.color = "#0a6b3a"; statusEl.textContent = "Saved \u2014 " + (_wizChipState.industries.length + _wizChipState.keywords.length + _wizChipState.specialties.length) + " signals."; }}
              setTimeout(function() {{ if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }} else {{ wizAdvance(); }} }}, 600);
            }}
          }})
          .catch(function() {{
            if (statusEl) {{ statusEl.style.color = "#b00"; statusEl.textContent = "Network error \u2014 continuing."; }}
            setTimeout(function() {{ if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }} else {{ wizAdvance(); }} }}, 1200);
          }})
          .finally(function() {{ if (ctaBtn) ctaBtn.disabled = false; }});
        return;
      }}
      if (s.action === "save-recency-window") {{
        const picked = document.querySelector('input[name="wiz-recency"]:checked');
        const val = picked ? picked.value : "7";
        const statusEl = document.getElementById("wiz-recency-status");
        try {{ localStorage.setItem(RECENCY_WINDOW_KEY, val); }} catch (e) {{}}
        try {{ pushPrefToProfile("recencyWindow", String(val)); }} catch (e) {{}}
        // Also apply immediately if the user is viewing the dashboard
        try {{
          activeWindow = String(val);
          _restoreRecencyWindow();
        }} catch (e) {{}}
        if (statusEl) {{ statusEl.style.color = "#0a6b3a"; statusEl.textContent = "Saved: " + (val === "0" ? "Last 24 hours" : val === "all" ? "All jobs" : "Last " + val + " days"); }}
        setTimeout(function() {{
          if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
          else {{ wizAdvance(); }}
        }}, 500);
        return;
      }}
      if (s.action === "save-daily-target") {{
        const input = document.getElementById("wiz-daily-target");
        const statusEl = document.getElementById("wiz-daily-status");
        let n = parseInt(input ? input.value : "5", 10);
        if (isNaN(n) || n < 1) n = 5;
        if (n > 50) n = 50;
        try {{ localStorage.setItem(DAILY_TARGET_KEY, String(n)); }} catch (e) {{}}
        try {{ pushPrefToProfile("dailyTarget", n); }} catch (e) {{}}
        if (statusEl) {{ statusEl.style.color = "#0a6b3a"; statusEl.textContent = "Saved: " + n + "/day"; }}
        setTimeout(function() {{
          if (window._wizExitAfterSave) {{ window._wizExitAfterSave = false; wizFinish(); }}
          else {{ wizAdvance(); }}
        }}, 500);
        return;
      }}
      if (s.action === "finish") {{ wizFinish(); return; }}
    }});
    back.addEventListener("click", wizBack);
    skip.addEventListener("click", function() {{
      const s = WIZ_STEPS[wizCurrent];
      if (s.action && s.action !== "next" && s.action !== "finish") {{ wizAdvance(); return; }}
      wizSkipPermanent();
    }});
    const saveExitBtn = document.getElementById("wiz-save-exit");
    if (saveExitBtn) {{
      saveExitBtn.addEventListener("click", function() {{
        // Set a flag the save handlers honor: after a successful save, exit
        // the wizard (run regen + close) instead of advancing to the next step.
        window._wizExitAfterSave = true;
        cta.click();
      }});
    }}

    // Wrap existing close handlers so the wizard resumes after a modal closes
    if (typeof closeResumeModal === "function") {{
      const _origCloseResume = closeResumeModal;
      window.closeResumeModal = function() {{
        _origCloseResume.apply(this, arguments);
        if (window._wizExpect === "resume" || window._wizExpect === "profile") {{
          window._wizExpect = null;
          wizAdvance();
          setTimeout(wizShow, 180);
        }}
      }};
    }}
    if (typeof closeContactsModal === "function") {{
      const _origCloseContacts = closeContactsModal;
      window.closeContactsModal = function() {{
        _origCloseContacts.apply(this, arguments);
        if (window._wizExpect === "contacts") {{
          window._wizExpect = null;
          wizAdvance();
          setTimeout(wizShow, 180);
        }}
      }};
    }}

    // Auto-launch when this version of the wizard hasn't been seen yet.
    // Note: dropped the !HAS_PROFILE_AT_RENDER guard so existing users
    // also get prompted when we bump the wizard flag (e.g. to ask new
    // questions like company-size preference). Users can skip steps
    // that aren't relevant (resume upload, etc.).
    try {{
      // v3 wizard handles auto-launch + persistence now. If WizV3 is present,
      // skip v2 entirely to avoid two wizards racing.
      if (window.WizV3) {{ return; }}
      // If user clicked "Reload page & re-check" on the verify-extension step,
      // jump back to that step on reload so the freshly-injected content
      // script can be detected.
      const resumeAt = localStorage.getItem("gmj_wizard_resume_at");
      if (resumeAt) {{
        let resumeIdx = -1;
        for (let i = 0; i < WIZ_STEPS.length; i++) {{
          if ((WIZ_STEPS[i] && WIZ_STEPS[i].action) === resumeAt) {{ resumeIdx = i; break; }}
        }}
        if (resumeIdx >= 0) {{
          wizCurrent = resumeIdx;
          setTimeout(wizShow, 450);
          // Don't clear resume marker yet — verify-extension step itself
          // clears it once the extension is actually detected or user skips.
        }} else {{
          const seen = localStorage.getItem("gmj_wizard_seen_v2");
          if (!seen) {{ setTimeout(wizShow, 450); }}
        }}
      }} else {{
        const seen = localStorage.getItem("gmj_wizard_seen_v2");
        if (!seen) {{ setTimeout(wizShow, 450); }}
      }}
    }} catch(e) {{}}
  }}
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", setup);
  }} else {{
    setup();
  }}
}})();

// Slice B: explicit Next button — delegates to the step's CTA so user input
// is saved before advancing. (Earlier this just called wizAdvance, which meant
// Next silently dropped preferences on the save-* steps.)
(function setupWizNextBtn() {{
  function wire() {{
    const btn = document.getElementById("wiz-next");
    if (!btn || btn._wired) return;
    btn._wired = true;
    btn.addEventListener("click", function() {{
      try {{
        if (typeof wizCurrent !== "undefined" && typeof WIZ_STEPS !== "undefined" &&
            wizCurrent >= WIZ_STEPS.length - 1) {{
          // Last step — Next acts like Finish/Close
          if (typeof wizFinish === "function") {{ wizFinish(); }}
          else if (typeof wizHide === "function") {{ wizHide(); }}
          return;
        }}
        // Delegate to the CTA so the step's save handler runs first; on
        // open-resume / open-contacts / next-only steps the CTA already just
        // advances or opens a modal, so this is safe for every step.
        const cta = document.getElementById("wiz-cta");
        if (cta && !cta.disabled) {{ cta.click(); return; }}
        if (typeof wizAdvance === "function") {{ wizAdvance(); }}
      }} catch(e) {{ console.warn("wiz-next error", e); }}
    }});
  }}
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", wire);
  }} else {{ wire(); }}
}})();

// Slice B: enhance wizRender to manage the always-visible Back + Next buttons
(function enhanceWizRender() {{
  if (typeof wizRender !== "function") return;
  const _orig = wizRender;
  window.wizRender = function() {{
    _orig.apply(this, arguments);
    const back = document.getElementById("wiz-back");
    const next = document.getElementById("wiz-next");
    if (back) {{
      back.style.display = "";
      back.disabled = (typeof wizCurrent !== "undefined" && wizCurrent === 0);
      back.style.opacity = back.disabled ? "0.4" : "";
      back.style.cursor = back.disabled ? "not-allowed" : "pointer";
    }}
    if (next && typeof wizCurrent !== "undefined" && typeof WIZ_STEPS !== "undefined") {{
      // Hide Next on the very last step — the primary CTA there is "Finish".
      const isLast = wizCurrent >= WIZ_STEPS.length - 1;
      next.style.display = isLast ? "none" : "";
    }}
  }};
}})();

// ============================================================
// Slice C — Notes & follow-up reminders (injected client-side)
// Adds a "Notes" button to every job card + a Reminders panel at the top.
// Notes are persisted via /notes endpoint on the Worker (X-Edit-Key auth).
// ============================================================
(function notesAndReminders() {{
  if (window.__slice_c_loaded) return; window.__slice_c_loaded = true;
  const NOTES_URL = WORKER_BASE + "/notes" + USER_QS;
  let _notes = {{}};

  function _todayISO() {{ return new Date().toISOString().slice(0,10); }}
  function _esc(s) {{ return (s||"").replace(/[&<>"]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c])); }}

  function bucketReminder(dateStr) {{
    if (!dateStr) return null;
    const t = _todayISO();
    if (dateStr < t) return "overdue";
    if (dateStr === t) return "today";
    const d = new Date(dateStr); const tn = new Date(t);
    const days = Math.round((d - tn) / 86400000);
    if (days <= 7) return "upcoming";
    return "later";
  }}

  function loadNotes() {{
    return fetch(NOTES_URL).then(r => r.json()).then(d => {{
      _notes = (d && d.notes) || {{}};
      renderReminders();
      decorateAllCards();
    }}).catch(()=>{{}});
  }}

  function getEditKeyHere() {{
    try {{
      return localStorage.getItem("htj_resume_key_" + USER_SLUG) ||
             localStorage.getItem("htj_resume_key") || "";
    }} catch(e) {{ return ""; }}
  }}
  function getAdminKeyHere() {{
    try {{ return localStorage.getItem("htj_admin_key") || ""; }} catch(e) {{ return ""; }}
  }}
  function getSessionTokenHere() {{
    try {{ return localStorage.getItem("gmj_session_token") || ""; }} catch(e) {{ return ""; }}
  }}
  function notesAuthHeaders() {{
    const h = {{ 'Content-Type': 'application/json' }};
    const ek = getEditKeyHere();   if (ek) h['X-Edit-Key'] = ek;
    const ak = getAdminKeyHere();  if (ak) h['X-Admin-Key'] = ak;
    const st = getSessionTokenHere(); if (st) h['Authorization'] = 'Bearer ' + st;
    return h;
  }}

  function saveNote(fp, fields) {{
    const card = document.querySelector('.card[data-fp="'+fp+'"]');
    const body = Object.assign({{ fp: fp }}, fields);
    if (card) {{
      const titleA = card.querySelector('.title a');
      const compEl = card.querySelector('.company');
      if (titleA && !body.jobTitle) {{ body.jobTitle = titleA.textContent.trim(); body.jobUrl = titleA.href || ''; }}
      if (compEl && !body.company) body.company = compEl.textContent.trim();
    }}
    return fetch(NOTES_URL, {{
      method: 'POST',
      headers: notesAuthHeaders(),
      body: JSON.stringify(body)
    }}).then(r => r.json()).then(d => {{
      if (d && d.notes) _notes = d.notes;
      renderReminders(); decorateAllCards();
      return d;
    }});
  }}

  function deleteNote(fp) {{
    return fetch(NOTES_URL + "&fp=" + encodeURIComponent(fp), {{
      method: 'DELETE',
      headers: notesAuthHeaders()
    }}).then(r => r.json()).then(d => {{
      if (_notes[fp]) delete _notes[fp];
      renderReminders(); decorateAllCards();
      return d;
    }});
  }}

  function decorateAllCards() {{
    document.querySelectorAll('.card[data-fp]').forEach(decorateCard);
  }}

  function decorateCard(card) {{
    const fp = card.getAttribute('data-fp');
    const actions = card.querySelector('.actions');
    if (!actions) return;
    let btn = actions.querySelector('.btn-notes');
    const hasNote = !!_notes[fp];
    const note = _notes[fp] || {{}};
    const bucket = bucketReminder(note.reminderDate);
    const label = hasNote
      ? (bucket === 'overdue' ? '📌 Overdue note'
        : bucket === 'today'  ? '📌 Reminder today'
        : note.reminderDate    ? '📌 Note · ' + note.reminderDate
        : '📌 Note')
      : '📝 Notes';
    const color = bucket === 'overdue' ? '#b91c1c'
                : bucket === 'today'   ? '#b45309'
                : hasNote              ? '#5C5CD6'
                : '';
    if (!btn) {{
      btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn ghost-btn small btn-notes';
      btn.addEventListener('click', function() {{ toggleEditor(card, fp); }});
      // Insert before the dismiss × if present, otherwise append
      const dismiss = actions.querySelector('.dismiss');
      if (dismiss) actions.insertBefore(btn, dismiss);
      else actions.appendChild(btn);
    }}
    btn.textContent = label;
    btn.style.color = color || '';
    btn.style.borderColor = color || '';
    btn.style.fontWeight = hasNote ? '600' : '';
  }}

  function toggleEditor(card, fp) {{
    let panel = card.querySelector('.notes-panel');
    if (panel) {{ panel.remove(); return; }}
    const note = _notes[fp] || {{}};
    panel = document.createElement('div');
    panel.className = 'notes-panel';
    panel.style.cssText = 'margin-top:10px;padding:12px;background:#F8F8FC;border:1px solid #E5E7EE;border-radius:6px;';
    panel.innerHTML =
      '<div style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:6px;">Your notes</div>' +
      '<textarea class="np-text" rows="3" placeholder="Recruiter name, contact info, things to follow up on…" '+
        'style="width:100%;padding:8px 10px;font:13px/1.4 inherit;border:1px solid #d0d4dc;border-radius:6px;resize:vertical;">' + _esc(note.text || '') + '</textarea>' +
      '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:8px;">' +
        '<label style="font-size:12px;color:#555;">Remind me on: ' +
          '<input class="np-date" type="date" value="'+_esc(note.reminderDate||'')+'" style="margin-left:6px;padding:5px 8px;font:13px inherit;border:1px solid #d0d4dc;border-radius:6px;">' +
        '</label>' +
        '<button type="button" class="btn primary np-save" style="margin-left:auto;">Save</button>' +
        (note.text || note.reminderDate ? '<button type="button" class="btn ghost-btn np-del" style="color:#b91c1c;border-color:#fca5a5;">Delete</button>' : '') +
        '<button type="button" class="btn ghost-btn np-close">Close</button>' +
      '</div>' +
      '<div class="np-status" style="font-size:12px;color:#777;margin-top:6px;min-height:14px;"></div>';
    card.appendChild(panel);
    const statusEl = panel.querySelector('.np-status');
    panel.querySelector('.np-close').addEventListener('click', () => panel.remove());
    panel.querySelector('.np-save').addEventListener('click', () => {{
      statusEl.textContent = 'Saving…';
      const text = panel.querySelector('.np-text').value;
      const reminderDate = panel.querySelector('.np-date').value || null;
      saveNote(fp, {{ text: text, reminderDate: reminderDate }})
        .then(d => {{
          if (d && d.ok) {{ statusEl.style.color='#0a6b3a'; statusEl.textContent='Saved.'; setTimeout(()=>panel.remove(), 600); }}
          else {{ statusEl.style.color='#b91c1c'; statusEl.textContent = (d && d.error) || 'Save failed.'; }}
        }})
        .catch(e => {{ statusEl.style.color='#b91c1c'; statusEl.textContent = 'Network error.'; }});
    }});
    const delBtn = panel.querySelector('.np-del');
    if (delBtn) delBtn.addEventListener('click', () => {{
      if (!confirm('Delete this note?')) return;
      statusEl.textContent = 'Deleting…';
      deleteNote(fp).then(() => panel.remove());
    }});
    panel.querySelector('.np-text').focus();
  }}

  function renderReminders() {{
    let panel = document.getElementById('reminders-panel');
    if (!panel) {{
      panel = document.createElement('div');
      panel.id = 'reminders-panel';
      panel.style.cssText = 'background:#fff;border:1px solid #E5E7EE;border-radius:8px;padding:14px 18px;margin:14px 0;';
      const filters = document.querySelector('.filters');
      if (filters && filters.parentNode) filters.parentNode.insertBefore(panel, filters);
      else document.body.insertBefore(panel, document.body.firstChild);
    }}
    const all = Object.entries(_notes);
    const withDates = all.filter(([fp, n]) => !!n.reminderDate);
    const overdue = withDates.filter(([_, n]) => bucketReminder(n.reminderDate) === 'overdue');
    const today   = withDates.filter(([_, n]) => bucketReminder(n.reminderDate) === 'today');
    const upcoming= withDates.filter(([_, n]) => bucketReminder(n.reminderDate) === 'upcoming');
    if (withDates.length === 0 && all.length === 0) {{ panel.style.display = 'none'; return; }}
    panel.style.display = '';
    function pill(label, items, color) {{
      if (!items.length) return '';
      const list = items.slice(0, 5).map(([fp, n]) =>
        '<a href="#" data-jump="'+fp+'" style="color:'+color+';text-decoration:none;border-bottom:1px dotted '+color+';margin-right:10px;">' +
          _esc(n.jobTitle || n.company || fp.slice(0,8)) +
          (n.company ? ' <span style="color:#888;">@ '+_esc(n.company)+'</span>' : '') +
        '</a>'
      ).join('');
      return '<div style="margin-bottom:6px;"><strong style="color:'+color+';">'+label+' ('+items.length+'):</strong> ' + list + '</div>';
    }}
    panel.innerHTML =
      '<div style="font-size:11px;font-weight:700;color:#555;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:8px;">📌 Follow-ups</div>' +
      pill('Overdue',  overdue,  '#b91c1c') +
      pill('Today',    today,    '#b45309') +
      pill('This week',upcoming, '#5C5CD6') +
      (withDates.length === 0
        ? '<div style="color:#888;font-size:13px;">You have '+all.length+' note'+(all.length===1?'':'s')+' but no reminder dates set.</div>'
        : '');
    panel.querySelectorAll('a[data-jump]').forEach(a => {{
      a.addEventListener('click', function(e) {{
        e.preventDefault();
        const fp = a.getAttribute('data-jump');
        const card = document.querySelector('.card[data-fp="'+fp+'"]');
        if (card) {{
          card.scrollIntoView({{behavior:'smooth', block:'center'}});
          const orig = card.style.boxShadow;
          card.style.boxShadow = '0 0 0 3px #5C5CD6';
          setTimeout(() => {{ card.style.boxShadow = orig; }}, 1500);
        }}
      }});
    }});
  }}

  // Re-decorate when the job grid is re-filtered or re-rendered
  const _origFilter = window.filter;
  if (typeof _origFilter === 'function') {{
    window.filter = function() {{ const r = _origFilter.apply(this, arguments); setTimeout(decorateAllCards, 0); return r; }};
  }}

  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', loadNotes);
  }} else {{ loadNotes(); }}
}})();

// --- Sprint mode: auto-sort + hydrate counters -----------------------------
(function(){{
  function _initSprintSort(){{
    try {{
      const ha = document.querySelector('.header-actions');
      if (!ha || ha.dataset.sprintActive !== 'true') return;
      const sel = document.getElementById('sortBy');
      if (!sel) return;
      if (sel.dataset.sprintApplied === '1') return;
      sel.value = 'sprint';
      sel.dataset.sprintApplied = '1';
      if (typeof sortCards === 'function') sortCards();
    }} catch(e){{}}
  }}
  async function _hydrateSprint(){{
    try {{
      const strip = document.getElementById('sprint-strip');
      if (!strip) return;
      const start = strip.dataset.sprintStart;
      const days = parseInt(strip.dataset.sprintDays || '10', 10);
      const dailyQuota = parseInt(strip.dataset.sprintDailyQuota || '3', 10);
      const quotaTotal = parseInt(strip.dataset.sprintQuotaTotal || (days * dailyQuota), 10);
      if (!start) return;
      const startDt = new Date(start);
      const todayStr = new Date().toISOString().slice(0,10);
      // Use the in-page tracker cache if present, else fetch directly.
      let tracker = (typeof window._trackerCache === 'object' && window._trackerCache) || null;
      if (!tracker && typeof TRACKER_WORKER_URL !== 'undefined') {{
        try {{
          const r = await fetch(TRACKER_WORKER_URL);
          if (r.ok) tracker = await r.json();
        }} catch(e){{}}
      }}
      if (!tracker || typeof tracker !== 'object') return;
      let applied = 0, today = 0;
      const activeStatuses = {{applied:1, phone:1, onsite:1, offer:1, rejected:1}};
      Object.values(tracker).forEach(function(entry){{
        if (!entry || typeof entry !== 'object') return;
        const st = (entry.status || '').toLowerCase();
        if (!activeStatuses[st]) return;
        const ts = entry.appliedAt || entry.updatedAt || '';
        if (!ts) return;
        const td = new Date(ts);
        if (isNaN(td.getTime()) || td < startDt) return;
        applied += 1;
        if (td.toISOString().slice(0,10) === todayStr) today += 1;
      }});
      const pct = quotaTotal ? Math.min(100, Math.round((applied/quotaTotal)*100)) : 0;
      const elApplied = document.getElementById('sprint-applied-total');
      const elToday = document.getElementById('sprint-today-count');
      const elPct = document.getElementById('sprint-pct');
      const elFill = document.getElementById('sprint-progress-fill');
      if (elApplied) elApplied.textContent = String(applied);
      if (elToday) elToday.textContent = String(today);
      if (elPct) elPct.textContent = String(pct);
      if (elFill) elFill.style.width = pct + '%';
    }} catch(e){{}}
  }}
  function _runAll(){{ _initSprintSort(); _hydrateSprint(); }}
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', _runAll);
  }} else {{
    _runAll();
  }}
  // Re-hydrate after status changes (tracker mutates)
  document.addEventListener('tracker:updated', _hydrateSprint);
}})();

// === Sprint config modal (prototype 2026-05-28) =====================
// The dashboard banner's "Start my 10-day sprint →" used to POST blind
// defaults. Now it opens this modal first so the user can pick duration,
// quota, days-of-week, and nudge time before committing.
const SC_KEY = 'gmj_sprint_config_' + USER_SLUG;
// URL-aware error formatter — every sprint catch should use this so the
// failing endpoint is visible in console + the user-facing alert.
function _spErr(label, url, e) {{
  const msg = (e && e.message) ? e.message : String(e || 'unknown error');
  const short = (url || '').replace(/^https?:\/\/[^\/]+/, '');
  try {{ console.error('[' + label + ']', short, e); }} catch (_) {{}}
  return msg + '  (endpoint: ' + short + ')';
}}
function _scLoadConfig() {{
  try {{
    const raw = localStorage.getItem(SC_KEY);
    if (raw) {{
      const o = JSON.parse(raw);
      if (o && typeof o === 'object') return Object.assign({{ duration:10, quota:3, days:[1,2,3,4,5], nudgeTime:'07:00', recapTime:'19:00', timezone:'America/New_York' }}, o);
    }}
  }} catch (e) {{}}
  return {{ duration: 10, quota: 3, days: [1,2,3,4,5], nudgeTime: '07:00', recapTime: '19:00', timezone: 'America/New_York' }};
}}
function _scSaveConfig(o) {{
  try {{ localStorage.setItem(SC_KEY, JSON.stringify(o)); }} catch (e) {{}}
}}
function _scActivatePill(group, value) {{
  const wrap = document.querySelector('.sc-pills[data-group="' + group + '"]');
  if (!wrap) return;
  wrap.querySelectorAll('.sc-pill').forEach(p => {{
    p.classList.toggle('active', String(p.dataset.val) === String(value));
  }});
}}
function _scActivateDays(daysArr) {{
  const wrap = document.querySelector('.sc-pills[data-group="days"]');
  if (!wrap) return;
  const set = new Set((daysArr || []).map(String));
  wrap.querySelectorAll('.sc-pill').forEach(p => {{
    p.classList.toggle('active', set.has(String(p.dataset.val)));
  }});
}}
function _scReadConfig() {{
  const get = group => {{
    const el = document.querySelector('.sc-pills[data-group="' + group + '"] .sc-pill.active');
    return el ? parseInt(el.dataset.val, 10) : null;
  }};
  const days = Array.from(document.querySelectorAll('.sc-pills[data-group="days"] .sc-pill.active'))
    .map(p => parseInt(p.dataset.val, 10));
  const t = (document.getElementById('sc-nudge-time') || {{}}).value || '07:00';
  const rt = (document.getElementById('sc-recap-time') || {{}}).value || '19:00';
  const tz = (document.getElementById('sc-timezone') || {{}}).value || 'America/New_York';
  return {{
    duration: get('duration') || 10,
    quota: get('quota') || 3,
    days: days.length ? days : [1,2,3,4,5],
    nudgeTime: t,
    recapTime: rt,
    timezone: tz
  }};
}}
function _scUpdatePreview() {{
  const c = _scReadConfig();
  const el = document.getElementById('sc-preview');
  if (!el) return;
  const totalApps = c.duration * c.quota;
  const skipNote = c.days.length < 7 ? ' (only on selected days)' : '';
  const tzShort = (c.timezone || 'America/New_York').split('/').pop().replace(/_/g, ' ');
  el.innerHTML = '<strong>' + c.duration + ' days × ' + c.quota + ' apps/day = ' + totalApps + ' applications total</strong>' +
                 skipNote + ' &middot; morning nudge ' + c.nudgeTime + ' &middot; recap ' + c.recapTime + ' (' + tzShort + ').';
}}
function _scWirePills() {{
  document.querySelectorAll('.sc-pills .sc-pill').forEach(p => {{
    p.onclick = () => {{
      const wrap = p.closest('.sc-pills');
      const group = wrap.dataset.group;
      if (group === 'days') {{
        p.classList.toggle('active');
      }} else {{
        wrap.querySelectorAll('.sc-pill').forEach(x => x.classList.remove('active'));
        p.classList.add('active');
      }}
      _scUpdatePreview();
    }};
  }});
  const nt = document.getElementById('sc-nudge-time');
  if (nt) nt.oninput = _scUpdatePreview;
  const rt2 = document.getElementById('sc-recap-time');
  if (rt2) rt2.oninput = _scUpdatePreview;
  const tzSel = document.getElementById('sc-timezone');
  if (tzSel) tzSel.onchange = _scUpdatePreview;
}}
async function openSprintConfigModal() {{
  const modal = document.getElementById('sprint-config-modal');
  if (!modal) return;
  // Start with locally-stored prefs as the optimistic seed so the modal
  // opens instantly. Then quietly fetch /skills-profile and let server
  // values override if present (server is canonical once a sprint exists).
  let c = _scLoadConfig();
  // One-shot pickup of a "use N" suggestion accepted in the review modal
  try {{
    const sug = parseInt(localStorage.getItem('gmj_sprint_suggested_quota_' + USER_SLUG) || '', 10);
    if (Number.isFinite(sug) && sug >= 1 && sug <= 10) {{
      c.quota = sug;
      localStorage.removeItem('gmj_sprint_suggested_quota_' + USER_SLUG);
    }}
  }} catch(e) {{}}
  _scActivatePill('duration', c.duration);
  _scActivatePill('quota', c.quota);
  _scActivateDays(c.days);
  const nt = document.getElementById('sc-nudge-time');
  if (nt) nt.value = c.nudgeTime;
  const rt = document.getElementById('sc-recap-time');
  if (rt) rt.value = c.recapTime || '19:00';
  const tzEl = document.getElementById('sc-timezone');
  if (tzEl) {{
    // Auto-detect on first open if no stored value
    if (!c.timezone || c.timezone === 'America/New_York') {{
      try {{
        const detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (detected && Array.from(tzEl.options).some(o => o.value === detected)) c.timezone = detected;
      }} catch(e) {{}}
    }}
    tzEl.value = c.timezone || 'America/New_York';
  }}
  _scWirePills();
  _scUpdatePreview();
  modal.classList.add('show');
  try {{
    const r = await fetch(WORKER_BASE + '/skills-profile' + USER_QS, {{ cache: 'no-store' }});
    if (r.ok) {{
      const j = await r.json();
      const p = (j && j.profile) || {{}};
      // Prefer the last completed sprint's settings when the user is
      // between sprints (no active sprintStart) — makes "start another"
      // feel like a continuation. Active sprint? Use the live profile.
      const lastSprint = (Array.isArray(p.sprintHistory) && p.sprintHistory.length)
        ? p.sprintHistory[p.sprintHistory.length - 1] : null;
      const useHistory = !p.sprintStart && lastSprint;
      const merged = {{
        duration:  parseInt((useHistory ? lastSprint.daysPlanned   : p.sprintDays)         || c.duration, 10),
        quota:     parseInt((useHistory ? lastSprint.dailyQuota    : p.sprintDailyQuota)   || c.quota,    10),
        days:     (useHistory ? lastSprint.daysOfWeek : p.sprintDaysOfWeek) && (useHistory ? lastSprint.daysOfWeek : p.sprintDaysOfWeek).length
                   ? (useHistory ? lastSprint.daysOfWeek : p.sprintDaysOfWeek)
                   : c.days,
        nudgeTime: (typeof (useHistory ? lastSprint.nudgeTime : p.sprintNudgeTime) === 'string' && (useHistory ? lastSprint.nudgeTime : p.sprintNudgeTime))
                   ? (useHistory ? lastSprint.nudgeTime : p.sprintNudgeTime)
                   : c.nudgeTime,
        timezone:  (typeof (useHistory ? lastSprint.timezone : p.sprintTimezone) === 'string' && (useHistory ? lastSprint.timezone : p.sprintTimezone))
                   ? (useHistory ? lastSprint.timezone : p.sprintTimezone)
                   : c.timezone
      }};
      _scActivatePill('duration', merged.duration);
      _scActivatePill('quota', merged.quota);
      _scActivateDays(merged.days);
      if (nt) nt.value = merged.nudgeTime;
      const rt = document.getElementById('sc-recap-time');
      if (rt) rt.value = (useHistory ? lastSprint.recapTime : p.sprintRecapTime) || merged.recapTime || c.recapTime;
      const tzEl = document.getElementById('sc-timezone');
      if (tzEl) tzEl.value = merged.timezone || 'America/New_York';
      _scUpdatePreview();
    }}
  }} catch (e) {{}}
}}
function closeSprintConfigModal() {{
  const modal = document.getElementById('sprint-config-modal');
  if (modal) modal.classList.remove('show');
}}
// Banner CTA keeps onclick="startSprintNow(this)" — just route through
// the modal so we don't have to touch fetch_jobs.py.
function startSprintNow(btn) {{
  if (btn) {{ btn.disabled = true; btn.textContent = 'Opening…'; }}
  openSprintConfigModal();
  setTimeout(() => {{
    if (btn) {{ btn.disabled = false; btn.textContent = 'Start my 10-day sprint →'; }}
  }}, 400);
}}
// Actually start the sprint with the modal's chosen config.
async function startConfiguredSprint(btn) {{
  const c = _scReadConfig();
  _scSaveConfig(c);
  if (btn) {{ btn.disabled = true; btn.textContent = 'Starting…'; }}
  try {{
    const _ek = (typeof getEditKey === 'function') ? getEditKey() : null;
    const _ak = (typeof getAdminKey === 'function') ? getAdminKey() : null;
    const _headers = {{ 'Content-Type': 'application/json' }};
    if (_ek) _headers['X-Edit-Key'] = _ek;
    else if (_ak) _headers['X-Admin-Key'] = _ak;
    const r = await fetch(WORKER_BASE + '/api/sprint/start' + USER_QS, {{
      method: 'POST',
      headers: _headers,
      body: JSON.stringify({{
        sprintDays: c.duration,
        sprintDailyQuota: c.quota,
        sprintDaysOfWeek: c.days,
        sprintNudgeTime: c.nudgeTime,
        sprintRecapTime: c.recapTime,
        sprintTimezone: c.timezone
      }})
    }});
    if (r.ok) {{
      try {{
        const burst = document.createElement('div');
        burst.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:9999;background:radial-gradient(circle at 50% 50%,rgba(124,124,240,0.45),transparent 60%);opacity:0;transition:opacity .35s;';
        document.body.appendChild(burst);
        requestAnimationFrame(() => {{ burst.style.opacity='1'; }});
        setTimeout(() => {{ burst.style.opacity='0'; setTimeout(() => burst.remove(), 400); }}, 600);
      }} catch(e) {{}}
      closeSprintConfigModal();
      setTimeout(() => location.reload(), 700);
    }} else {{
      const j = await r.json().catch(()=>({{}}));
      alert('Could not start sprint: ' + (j.error || r.status));
      if (btn) {{ btn.disabled = false; btn.textContent = 'Start sprint →'; }}
    }}
  }} catch (e) {{
    alert(_spErr('startConfiguredSprint', WORKER_BASE + '/api/sprint/start' + USER_QS, e));
    if (btn) {{ btn.disabled = false; btn.textContent = 'Start sprint →'; }}
  }}
}}

// === Sprint review (State C — prototype 2026-05-28) ==================
// On dashboard load, if the user's sprint window has elapsed AND we
// haven't recorded the review yet (localStorage flag scoped to the
// sprintStart timestamp), surface a banner + open the review modal.
const SR_REVIEW_KEY = 'gmj_sprint_review_seen_' + USER_SLUG;
function _srTrackerSummary() {{
  // Mirror the stats we want to show. Uses getTracker() if available.
  const tracker = (typeof getTracker === 'function') ? getTracker() : {{}};
  let applied = 0, advanced = 0, rejected = 0;
  Object.values(tracker || {{}}).forEach(r => {{
    if (!r) return;
    const st = String(r.status || '').toLowerCase();
    if (['applied','phone','onsite','offer','rejected'].includes(st)) applied++;
    if (['phone','onsite','offer'].includes(st)) advanced++;
    if (st === 'rejected') rejected++;
  }});
  return {{ applied, advanced, rejected }};
}}
function _srRenderStats(applied, advanced, rejected, target) {{
  const stat = (label, val, sub) =>
    '<div style="background:#f4f4ff;border:1px solid #e0e2ed;border-radius:8px;padding:10px;text-align:center;">' +
    '<div style="font-size:22px;font-weight:700;color:#1817B5;">' + val + '</div>' +
    '<div style="font-size:11.5px;color:#444;text-transform:uppercase;letter-spacing:0.04em;margin-top:2px;">' + label + '</div>' +
    (sub ? '<div style="font-size:11px;color:#777;margin-top:2px;">' + sub + '</div>' : '') +
    '</div>';
  const pct = target > 0 ? Math.round(100 * applied / target) : 0;
  return [
    stat('Applied', applied, 'of ' + target),
    stat('Advanced', advanced, 'past applied'),
    stat('Rejected', rejected, ''),
    stat('Goal hit', pct + '%', '')
  ].join('');
}}
async function openSprintReviewModal() {{
  const modal = document.getElementById('sprint-review-modal');
  if (!modal) return;
  const strip = document.getElementById('sprint-strip');
  let days = 10, quota = 3;
  if (strip) {{
    days = parseInt(strip.getAttribute('data-sprint-days') || '10', 10);
    quota = parseInt(strip.getAttribute('data-sprint-daily-quota') || '3', 10);
  }}
  const {{ applied, advanced, rejected }} = _srTrackerSummary();
  const target = days * quota;
  document.getElementById('sr-stats').innerHTML = _srRenderStats(applied, advanced, rejected, target);
  // Wire the new pills (they live inside the modal — call after innerHTML render)
  document.querySelectorAll('#sprint-review-modal .sc-pills .sc-pill').forEach(p => {{
    p.onclick = () => p.classList.toggle('active');
  }});
  // Smart quota suggestion: pull sprintHistory and recommend a quota for
  // the next sprint when actual ≠ planned by ≥30% across recent sprints.
  await _srInjectQuotaSuggestion(quota);
  modal.classList.add('show');
}}

async function _srInjectQuotaSuggestion(currentQuota) {{
  // Idempotent: remove any prior banner so we don't stack
  const existing = document.getElementById('sr-quota-tip');
  if (existing) existing.remove();
  try {{
    const r = await fetch(WORKER_BASE + '/skills-profile' + USER_QS, {{ cache: 'no-store' }});
    if (!r.ok) return;
    const j = await r.json();
    const hist = ((j && j.profile && j.profile.sprintHistory) || []).slice(-3);
    if (hist.length < 2) return; // need ≥2 sprints to suggest anything
    let totalApplied = 0, totalActiveDays = 0;
    hist.forEach(h => {{
      // Prefer h.activeDays (computed at /complete time); fall back to
      // daysPlanned for older records that pre-date the field.
      const days = Math.max(1, (typeof h.activeDays === 'number' && h.activeDays > 0) ? h.activeDays : (h.daysPlanned || 0));
      totalApplied += (h.appliedCount || 0);
      totalActiveDays += days;
    }});
    const avgActualPerDay = totalActiveDays > 0 ? totalApplied / totalActiveDays : 0;
    if (!Number.isFinite(avgActualPerDay) || avgActualPerDay <= 0) return;
    const ratio = avgActualPerDay / (currentQuota || 1);
    // Round to int, clamp 1..10
    const suggested = Math.max(1, Math.min(10, Math.round(avgActualPerDay)));
    if (suggested === currentQuota) return; // nothing to suggest
    let direction = '';
    if (ratio < 0.7) direction = 'lower';
    else if (ratio > 1.3) direction = 'higher';
    else return; // within tolerance
    const tip = document.createElement('div');
    tip.id = 'sr-quota-tip';
    tip.style.cssText = 'margin:14px 0 0;padding:10px 14px;background:#fff7e6;border:1px solid #fcd34d;color:#78350f;border-radius:8px;font-size:13px;display:flex;justify-content:space-between;align-items:center;gap:10px;';
    const noun = hist.length === 2 ? 'sprints' : 'sprints';
    tip.innerHTML =
      '<span>📊 Across your last ' + hist.length + ' ' + noun + ' you averaged ' +
        '<strong>' + avgActualPerDay.toFixed(1) + ' / active day</strong> on a <strong>' + currentQuota + ' / day</strong> plan. ' +
        'Try ' + suggested + ' / day next sprint?</span>' +
      '<button type="button" id="sr-quota-apply" style="background:#1817B5;color:#fff;border:none;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">Use ' + suggested + ' / day</button>';
    // Insert above the CTAs (the action row)
    const ctas = document.querySelector('#sprint-review-modal .modal > div[style*="justify-content:flex-end"]');
    if (ctas) ctas.parentNode.insertBefore(tip, ctas);
    else document.querySelector('#sprint-review-modal .modal').appendChild(tip);
    document.getElementById('sr-quota-apply').onclick = () => {{
      // Stash the recommendation in localStorage; the config modal will
      // pick it up when "Save & start another" opens it next.
      try {{ localStorage.setItem('gmj_sprint_suggested_quota_' + USER_SLUG, String(suggested)); }} catch(e) {{}}
      tip.querySelector('button').textContent = '✓ Will use ' + suggested;
      tip.querySelector('button').disabled = true;
    }};
  }} catch (e) {{ /* silent */ }}
}}
function closeSprintReviewModal() {{
  const m = document.getElementById('sprint-review-modal');
  if (m) m.classList.remove('show');
}}
async function finishSprintReview(btn, startAnother) {{
  if (btn) {{ btn.disabled = true; btn.textContent = 'Saving…'; }}
  const worked = Array.from(document.querySelectorAll('.sc-pills[data-group="sr-worked"] .sc-pill.active')).map(p => p.dataset.val);
  const didnt  = Array.from(document.querySelectorAll('.sc-pills[data-group="sr-didnt"]  .sc-pill.active')).map(p => p.dataset.val);
  const note = (document.getElementById('sr-note') || {{}}).value || '';
  const {{ applied, advanced, rejected }} = _srTrackerSummary();
  try {{
    const _ek = (typeof getEditKey === 'function') ? getEditKey() : null;
    const _ak = (typeof getAdminKey === 'function') ? getAdminKey() : null;
    const _headers = {{ 'Content-Type': 'application/json' }};
    if (_ek) _headers['X-Edit-Key'] = _ek;
    else if (_ak) _headers['X-Admin-Key'] = _ak;
    const r = await fetch(WORKER_BASE + '/api/sprint/complete' + USER_QS, {{
      method: 'POST',
      headers: _headers,
      body: JSON.stringify({{
        appliedCount: applied,
        advancedCount: advanced,
        rejectedCount: rejected,
        feedback: {{ worked, didnt, note }}
      }})
    }});
    if (!r.ok) {{
      const j = await r.json().catch(() => ({{}}));
      alert('Could not save review: ' + (j.error || r.status));
      if (btn) {{ btn.disabled = false; btn.textContent = startAnother ? 'Save & start another sprint →' : 'Save & take a break'; }}
      return;
    }}
    try {{ localStorage.setItem(SR_REVIEW_KEY, new Date().toISOString()); }} catch(e) {{}}
    closeSprintReviewModal();
    if (startAnother) {{
      // Tiny delay so the modal close animation doesn't overlap; then open
      // the config modal which now hydrates from the just-saved profile.
      setTimeout(() => {{ openSprintConfigModal(); }}, 250);
    }} else {{
      setTimeout(() => location.reload(), 600);
    }}
  }} catch (e) {{
    alert(_spErr('finishSprintReview', WORKER_BASE + '/api/sprint/complete' + USER_QS, e));
    if (btn) {{ btn.disabled = false; btn.textContent = startAnother ? 'Save & start another sprint →' : 'Save & take a break'; }}
  }}
}}
// Detect "sprint ended" on dashboard load. The sprint strip has
// data-sprint-start + data-sprint-days set by the server-side renderer
// when a sprint is active. If it's active AND the end is in the past,
// we prompt the review unless we've already recorded one for this run.
(function _maybeOfferSprintReview() {{
  function check() {{
    try {{
      const strip = document.getElementById('sprint-strip');
      if (!strip) return; // no active sprint
      const startStr = strip.getAttribute('data-sprint-start');
      const days = parseInt(strip.getAttribute('data-sprint-days') || '10', 10);
      if (!startStr || !days) return;
      const start = new Date(startStr);
      const end = new Date(start.getTime() + days * 86400000);
      if (Date.now() < end.getTime()) return; // not over yet
      // Don't re-nag if already reviewed for this sprint
      const seen = localStorage.getItem(SR_REVIEW_KEY);
      if (seen && new Date(seen).getTime() > start.getTime()) return;
      // Render an "ended" banner overlay on top of the strip + auto-open modal.
      const banner = document.createElement('div');
      banner.style.cssText = 'background:#fff7e6;border:1px solid #fcd34d;color:#78350f;padding:10px 14px;border-radius:8px;margin:0 auto 10px;max-width:1400px;font-size:13.5px;display:flex;justify-content:space-between;align-items:center;gap:10px;';
      banner.innerHTML = '<span>🏁 Your sprint ended. Take 30 seconds to debrief.</span>' +
        '<button onclick="openSprintReviewModal()" style="background:#1817B5;color:#fff;border:none;padding:6px 14px;border-radius:6px;font-weight:600;cursor:pointer;font-size:13px;">Review &amp; pick next</button>';
      strip.parentNode.insertBefore(banner, strip);
      setTimeout(openSprintReviewModal, 800);
    }} catch (e) {{ /* silent */ }}
  }}
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => setTimeout(check, 600));
  }} else {{
    setTimeout(check, 600);
  }}
}})();

// === Mid-sprint controls + past-sprints history (State B, 2026-05-28) =
// Two pieces, both decoded from the sprint-strip's data-* attributes
// (server already renders those when sprintStart is set).

async function _spFetchProfile() {{
  try {{
    const r = await fetch(WORKER_BASE + '/skills-profile' + USER_QS, {{ cache: 'no-store' }});
    if (!r.ok) return {{}};
    const j = await r.json();
    return (j && j.profile) || {{}};
  }} catch (e) {{ return {{}}; }}
}}

function _spAuthHeaders() {{
  const _ek = (typeof getEditKey === 'function') ? getEditKey() : null;
  const _ak = (typeof getAdminKey === 'function') ? getAdminKey() : null;
  const h = {{ 'Content-Type': 'application/json' }};
  if (_ek) h['X-Edit-Key'] = _ek;
  else if (_ak) h['X-Admin-Key'] = _ak;
  return h;
}}

async function sprintSnoozeToday(btn) {{
  if (!confirm("Snooze today's nudge + recap emails? You'll still see the dashboard.")) return;
  if (btn) {{ btn.disabled = true; btn.textContent = 'Snoozing…'; }}
  try {{
    const r = await fetch(WORKER_BASE + '/api/sprint/snooze-today' + USER_QS, {{
      method: 'POST', headers: _spAuthHeaders(), body: '{{}}'
    }});
    if (!r.ok) {{
      const j = await r.json().catch(() => ({{}}));
      alert('Could not snooze: ' + (j.error || r.status));
      if (btn) {{ btn.disabled = false; btn.textContent = 'Snooze today'; }}
      return;
    }}
    if (btn) {{ btn.textContent = 'Snoozed ✓'; }}
  }} catch (e) {{
    alert(_spErr('sprintSnoozeToday', WORKER_BASE + '/api/sprint/snooze-today' + USER_QS, e));
    if (btn) {{ btn.disabled = false; btn.textContent = 'Snooze today'; }}
  }}
}}

async function sprintAdjustQuota() {{
  const cur = parseInt((document.getElementById('sprint-strip') || {{}}).getAttribute('data-sprint-daily-quota') || '3', 10);
  const v = prompt('New apps/day (1–10):', String(cur));
  if (!v) return;
  const next = parseInt(v, 10);
  if (!Number.isFinite(next) || next < 1 || next > 10) {{ alert('Pick a number 1–10.'); return; }}
  try {{
    const r = await fetch(WORKER_BASE + '/skills-profile' + USER_QS, {{
      method: 'POST', headers: _spAuthHeaders(),
      body: JSON.stringify({{ patchFields: {{ sprintDailyQuota: next }} }})
    }});
    if (!r.ok) {{
      const j = await r.json().catch(() => ({{}}));
      alert('Could not adjust: ' + (j.error || r.status));
      return;
    }}
    location.reload();
  }} catch (e) {{
    alert(_spErr('sprintAdjustQuota', WORKER_BASE + '/skills-profile' + USER_QS, e));
  }}
}}

async function sprintEndEarly() {{
  if (!confirm('End this sprint now? You can fill in the review next.')) return;
  // Just open the review modal — its "save" already calls /api/sprint/complete
  // which clears sprintStart. Effectively the same path as a natural end.
  if (typeof openSprintReviewModal === 'function') openSprintReviewModal();
}}

// Render mid-sprint controls into the strip header.
(function _addMidSprintControls() {{
  function run() {{
    try {{
      const strip = document.getElementById('sprint-strip');
      if (!strip) return;
      if (strip.querySelector('.sprint-controls')) return; // idempotent
      const bar = document.createElement('div');
      bar.className = 'sprint-controls';
      bar.style.cssText = 'display:flex;justify-content:flex-end;gap:8px;margin-top:8px;font-size:11.5px;';
      bar.innerHTML =
        '<button onclick="sprintSnoozeToday(this)" style="background:rgba(255,255,255,0.12);color:#fff;border:1px solid rgba(255,255,255,0.25);padding:4px 12px;border-radius:6px;font-size:11.5px;font-weight:600;cursor:pointer;">Snooze today</button>' +
        '<button onclick="sprintAdjustQuota()" style="background:rgba(255,255,255,0.12);color:#fff;border:1px solid rgba(255,255,255,0.25);padding:4px 12px;border-radius:6px;font-size:11.5px;font-weight:600;cursor:pointer;">Adjust quota</button>' +
        '<button onclick="sprintEndEarly()" style="background:rgba(255,255,255,0.12);color:#fff;border:1px solid rgba(255,255,255,0.25);padding:4px 12px;border-radius:6px;font-size:11.5px;font-weight:600;cursor:pointer;">End early</button>';
      strip.appendChild(bar);
    }} catch (e) {{ /* silent */ }}
  }}
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => setTimeout(run, 400));
  }} else {{
    setTimeout(run, 400);
  }}
}})();

// Render Past sprints expander right under sprint strip area (or top of grid if no strip).
(async function _renderPastSprints() {{
  function _esc(s) {{ return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({{ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }}[c])); }}
  function _fmtDate(iso) {{
    try {{ return new Date(iso).toLocaleDateString(undefined, {{ month: 'short', day: 'numeric' }}); }} catch(e) {{ return iso; }}
  }}
  function _rowHtml(h, idx) {{
    const target = (h.daysPlanned||0) * (h.dailyQuota||0);
    const pct = target > 0 ? Math.round(100 * (h.appliedCount||0) / target) : 0;
    const feedback = h.feedback || {{}};
    const tags = [].concat(feedback.worked || []).concat((feedback.didnt || []).map(s => '–' + s)).slice(0, 3);
    const tagHtml = tags.length
      ? '<div style="font-size:11.5px;color:#666;margin-top:2px;">' + tags.map(t => '<span style="background:#eef0ff;border:1px solid #d8dbe6;border-radius:10px;padding:1px 8px;margin-right:4px;">' + _esc(t) + '</span>').join('') + '</div>'
      : '';
    const note = feedback.note ? '<div style="font-size:11.5px;color:#777;margin-top:3px;font-style:italic;">&ldquo;' + _esc(feedback.note) + '&rdquo;</div>' : '';
    return '<div style="background:#fff;border:1px solid #e0e2ed;border-radius:8px;padding:10px 14px;margin-bottom:8px;">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;font-size:13px;">' +
        '<span><strong>Sprint #' + (idx+1) + '</strong> &middot; ' + _fmtDate(h.startedAt) + ' → ' + _fmtDate(h.endedAt) + '</span>' +
        '<span style="color:#5C5CD6;font-weight:600;">' + (h.appliedCount||0) + ' / ' + target + ' applied (' + pct + '%)</span>' +
      '</div>' +
      '<div style="font-size:12px;color:#666;margin-top:2px;">' +
        ((typeof h.activeDays === 'number') ? (h.activeDays + ' active / ' + (h.daysPlanned||0) + ' planned') : ((h.daysPlanned||0) + ' days')) + ' &middot; ' + (h.dailyQuota||0) + '/day &middot; advanced ' + (h.advancedCount||0) + ' &middot; rejected ' + (h.rejectedCount||0) +
      '</div>' +
      tagHtml + note +
      '</div>';
  }}
  try {{
    const p = await _spFetchProfile();
    const hist = Array.isArray(p.sprintHistory) ? p.sprintHistory : [];
    if (!hist.length) return;
    // Insertion target: directly after sprint-strip or sprint-start-cta;
    // else above #grid as a fallback.
    const anchor = document.getElementById('sprint-strip') || document.getElementById('sprint-start-cta') || document.getElementById('focus-panel') || document.getElementById('grid');
    if (!anchor) return;
    if (document.getElementById('past-sprints')) return; // idempotent
    const wrap = document.createElement('div');
    wrap.id = 'past-sprints';
    wrap.style.cssText = 'max-width:1400px;margin:0 auto 14px;font-family:Inter,system-ui,sans-serif;';
    const recent = hist.slice(-5).reverse();
    wrap.innerHTML =
      '<details style="background:#f7f8fb;border:1px solid #e0e2ed;border-radius:10px;padding:10px 14px;">' +
        '<summary style="cursor:pointer;font-size:13px;font-weight:600;color:#1A1A2E;">Past sprints (' + hist.length + ')</summary>' +
        '<div style="margin-top:10px;">' + recent.map(_rowHtml).join('') + '</div>' +
      '</details>';
    if (anchor.parentNode) anchor.parentNode.insertBefore(wrap, anchor.nextSibling);
  }} catch (e) {{ /* silent */ }}
}})();

// === #start-sprint deep-link handler (2026-05-28) =====================
// /account.html links here with #start-sprint when the user clicks
// "Start a sprint now" from the sprint preferences card. We auto-open
// the sprint config modal once, then strip the hash so refreshes don't
// re-trigger it.
(function _handleStartSprintHash() {{
  function run() {{
    try {{
      if (window.location.hash !== '#start-sprint') return;
      if (typeof openSprintConfigModal !== 'function') return;
      // Strip the hash so a reload doesn't re-open the modal
      history.replaceState(null, '', window.location.pathname + window.location.search);
      setTimeout(openSprintConfigModal, 300);
    }} catch (e) {{ /* silent */ }}
  }}
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => setTimeout(run, 200));
  }} else {{
    setTimeout(run, 200);
  }}
}})();

// --- Tier 2: p5.js-style particle burst on Mark Applied --------------
function _sprintParticleBurst(originEl) {{
  try {{
    const strip = document.getElementById('sprint-strip');
    if (!strip) return;
    const cvs = document.createElement('canvas');
    const rect = strip.getBoundingClientRect();
    cvs.width = Math.max(300, Math.round(rect.width));
    cvs.height = Math.round(rect.height);
    cvs.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none;z-index:5;';
    strip.style.position = 'relative';
    strip.appendChild(cvs);
    const ctx = cvs.getContext('2d');
    const fill = document.getElementById('sprint-progress-fill');
    const startX = fill ? (fill.getBoundingClientRect().right - rect.left) : (cvs.width * 0.55);
    const startY = fill ? (fill.getBoundingClientRect().top - rect.top + (fill.offsetHeight || 8) / 2) : (cvs.height * 0.55);
    const palette = ['#7C7CF0','#A4A4FF','#FFD580','#F0A0FF','#FFFFFF'];
    const N = 36;
    const parts = [];
    for (let i = 0; i < N; i++) {{
      const a = (Math.PI * 2 * i) / N + Math.random() * 0.3;
      const v = 2 + Math.random() * 4;
      parts.push({{
        x: startX, y: startY,
        vx: Math.cos(a) * v, vy: Math.sin(a) * v - 1,
        life: 0, maxLife: 38 + Math.random() * 22,
        size: 2 + Math.random() * 4,
        color: palette[(Math.random() * palette.length) | 0]
      }});
    }}
    let raf = 0;
    function step() {{
      ctx.clearRect(0, 0, cvs.width, cvs.height);
      let alive = 0;
      for (const p of parts) {{
        if (p.life >= p.maxLife) continue;
        alive++;
        p.x += p.vx; p.y += p.vy; p.vy += 0.08; p.life++;
        const alpha = 1 - (p.life / p.maxLife);
        ctx.globalAlpha = alpha;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (0.4 + alpha * 0.6), 0, Math.PI * 2);
        ctx.fill();
      }}
      ctx.globalAlpha = 1;
      if (alive > 0) {{ raf = requestAnimationFrame(step); }}
      else {{ cvs.remove(); }}
    }}
    raf = requestAnimationFrame(step);
  }} catch (e) {{}}
}}

// Hook tracker:updated → if status was applied, burst confetti and re-hydrate
document.addEventListener('tracker:updated', function(ev) {{
  try {{
    const detail = ev && ev.detail || {{}};
    if (!detail || !detail.status) return;
    if (/applied|phone|onsite|offer/i.test(detail.status)) {{
      _sprintParticleBurst();
    }}
  }} catch(e) {{}}
}});

// --- Contacts hydration from KV (server-side mirror) ----------------
(async function _hydrateContactsFromServer(){{
  try {{
    if (typeof LINKEDIN_CONTACTS_KEY === 'undefined') return;
    const existing = localStorage.getItem(LINKEDIN_CONTACTS_KEY);
    if (existing) {{
      try {{
        const arr = JSON.parse(existing);
        if (Array.isArray(arr) && arr.length > 0) return;
      }} catch(e) {{}}
    }}
    const _ek = (typeof getEditKey === 'function') ? getEditKey() : null;
    const _ak = (typeof getAdminKey === 'function') ? getAdminKey() : null;
    const _h = {{}};
    if (_ek) _h['X-Edit-Key'] = _ek;
    else if (_ak) _h['X-Admin-Key'] = _ak;
    const r = await fetch(WORKER_BASE + '/contacts' + USER_QS, {{
      headers: _h,
    }});
    if (!r.ok) return;
    const j = await r.json();
    if (!j || !Array.isArray(j.contacts) || !j.contacts.length) return;
    localStorage.setItem(LINKEDIN_CONTACTS_KEY, JSON.stringify(j.contacts));
    if (j.meta) localStorage.setItem(LINKEDIN_CONTACTS_META_KEY, JSON.stringify(j.meta));
    if (typeof _contactsByCompany !== 'undefined') _contactsByCompany = null;
    if (typeof injectContactBadgesOnCards === 'function') injectContactBadgesOnCards();
  }} catch (e) {{}}
}})();

</script>
</body></html>"""
