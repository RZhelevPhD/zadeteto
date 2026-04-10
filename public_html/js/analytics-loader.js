/* === ZaDeteto Analytics Loader ===
 *
 * Single point of integration for all third-party analytics + session-replay
 * tools. Loads each tool ONLY after the visitor has explicitly opted in via
 * the cookie banner.
 *
 * Currently wired:
 *   - Contentsquare (UXA) — session replay + heatmaps + funnel analytics
 *     Gated on:  ZdConsent.has('analytics')
 *     Privacy:   form fields auto-masked at the source via data-cs-mask
 *
 * Easy to extend later:
 *   - Umami / Plausible / Cloudflare Web Analytics — add in same pattern
 *     by wiring _loadIfConsented() to fire their respective script tags
 *
 * Architecture:
 *   1. On page load, check current consent via ZdConsent.has('analytics')
 *   2. If true → inject the third-party script tag asynchronously
 *   3. If false → do nothing, sit and wait
 *   4. Listen for the 'zd-consent-change' event from cookie-banner.js so
 *      the moment a user clicks "Accept" the script loads without a reload
 *   5. Idempotent — once a script is loaded, never load it twice
 *
 * Why a separate file (not inline in each page):
 *   - Single source of truth for analytics integrations
 *   - Adding/removing a tool is a 1-line edit, not a 12-page sweep
 *   - Easier to audit for GDPR compliance reviews
 */
(function () {
  var _loaded = {}; // map of tool names → boolean

  function _injectScript(src, attrs) {
    var s = document.createElement('script');
    s.src = src;
    s.async = true;
    if (attrs) {
      Object.keys(attrs).forEach(function (k) { s.setAttribute(k, attrs[k]); });
    }
    document.head.appendChild(s);
    return s;
  }

  /* ─────────────── Contentsquare (session replay + heatmaps) ─────────────── */
  function _loadContentsquare() {
    if (_loaded.contentsquare) return;
    _loaded.contentsquare = true;
    _injectScript('https://t.contentsquare.net/uxa/6dc8ffe946b20.js');
    console.info('[analytics] Contentsquare loaded (consent: analytics=true)');
  }

  /* ─────────────── Master loader — runs for every tool ─────────────── */
  function _loadIfConsented() {
    var consent = window.ZdConsent && window.ZdConsent.get();
    if (!consent) return;  // banner not yet shown / no choice made → load nothing

    if (consent.analytics) {
      _loadContentsquare();
      // Future tools (Umami, Plausible, etc.) go here, gated on the same flag
    } else if (_loaded.contentsquare) {
      // Contentsquare was previously loaded but consent has been revoked —
      // send runtime opt-out so it stops collecting data this session.
      window._uxa = window._uxa || [];
      window._uxa.push(['optout']);
      console.info('[analytics] Contentsquare opt-out sent (consent revoked)');
    }
  }

  /* ─────────────── Init ─────────────── */
  // 1. Try immediately (in case ZdConsent is already available)
  if (window.ZdConsent) {
    _loadIfConsented();
  } else {
    // ZdConsent isn't ready yet (cookie-banner.js hasn't run). Wait briefly.
    document.addEventListener('DOMContentLoaded', _loadIfConsented);
  }

  // 2. React to consent changes from the banner UI
  window.addEventListener('zd-consent-change', function (e) {
    _loadIfConsented();
  });
})();
