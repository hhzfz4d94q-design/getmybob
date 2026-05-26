// Runs on getmemyjob.officebeatllc.com and the per-user .html pages on Cloudflare Pages.
// Sets a data attribute the wizard checks to confirm the extension is installed.
(function () {
  try {
    document.documentElement.setAttribute("data-gmj-installed", "1");
    document.documentElement.setAttribute("data-gmj-version", "0.1.1");
    // Also dispatch a custom event so async listeners pick it up
    setTimeout(() => {
      try { document.dispatchEvent(new CustomEvent("gmj-extension-ready", { detail: { version: "0.1.1" } })); } catch (e) {}
    }, 50);
  } catch (e) {}
})();
