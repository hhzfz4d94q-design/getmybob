// Runs on getmemyjob.officebeatllc.com and the per-user .html pages on Cloudflare Pages.
// Sets data attributes the wizard checks to confirm the extension is installed,
// and dispatches a custom event for async listeners.
//
// Belt-and-suspenders: attribute on <html> AND <body>, event on document AND window,
// plus a postMessage so page-context code that can't access content-script context
// can still hear the signal.
(function () {
  function _mark() {
    try {
      document.documentElement.setAttribute("data-gmj-installed", "1");
      document.documentElement.setAttribute("data-gmj-version", "0.1.2");
      if (document.body) {
        document.body.setAttribute("data-gmj-installed", "1");
      }
    } catch (e) {}
    try {
      var detail = { version: "0.1.2", at: Date.now() };
      document.dispatchEvent(new CustomEvent("gmj-extension-ready", { detail: detail }));
      window.dispatchEvent(new CustomEvent("gmj-extension-ready", { detail: detail }));
      // postMessage so isolated page-context can pick this up too
      window.postMessage({ type: "GMJ_EXTENSION_READY", version: "0.1.2" }, "*");
    } catch (e) {}
  }
  _mark();
  // Re-emit once body exists (document_start may fire before body is created)
  if (!document.body) {
    document.addEventListener("DOMContentLoaded", _mark, { once: true });
  }
  // And once more after the page is fully loaded, in case anything listens late.
  window.addEventListener("load", function () { setTimeout(_mark, 50); }, { once: true });
})();
