/* === ZaDeteto Analytics Loader ===
 *
 * Single point of integration for all third-party analytics + session-replay
 * + advertising pixel tools. Loads each tool ONLY after the visitor has
 * explicitly opted in via the cookie banner.
 *
 * Currently wired:
 *   - Contentsquare (UXA) — session replay + heatmaps + funnel analytics
 *     Gated on:  ZdConsent.has('analytics')
 *     Privacy:   form fields auto-masked at the source via data-cs-mask
 *
 *   - Meta Pixel (Facebook + Instagram remarketing)
 *     Gated on:  ZdConsent.has('marketing')
 *     On revoke: fires fbq('consent','revoke') so Meta stops collection mid-session
 *     Cookies:   _fbp (and _fbc when CAPI is later wired) — already in
 *                cookie-banner.js COOKIE_MAP under 'marketing'
 *
 * Pending (waiting on IDs from user):
 *   - Google Tag (GA4 -> analytics, Google Ads -> marketing)
 *   - TikTok Pixel (-> marketing)
 *
 * ─── ID config (public, not secrets) ─────────────────────────────────────
 * These IDs are intentionally embedded in client-side JS. Browsers expose
 * them in network requests by design. NOT for .env. See memory file
 * project_zadeteto_pixel_ids.md for context.
 */
(function () {
  /* ─── IDs ─── */
  var META_PIXEL_ID    = '1291940649013805';
  var GA4_ID           = null;  // pending: 'G-XXXXXXX'
  var GOOGLE_ADS_ID    = null;  // pending: 'AW-XXXXXXX'
  var TIKTOK_PIXEL_ID  = null;  // pending: 'CXXXXXXXX...'

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

  /* ─────────────── Meta Pixel (Facebook + Instagram) ─────────────── */
  function _loadMetaPixel() {
    if (_loaded.metaPixel) return;
    if (!META_PIXEL_ID) return;
    _loaded.metaPixel = true;

    // Inline Meta bootstrap (per official Meta Pixel snippet, minus the auto
    // PageView call so we control event firing order).
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return;
      n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n;
      n.push = n;
      n.loaded = !0;
      n.version = '2.0';
      n.queue = [];
      t = b.createElement(e);
      t.async = !0;
      t.src = v;
      s = b.getElementsByTagName(e)[0];
      s.parentNode.insertBefore(t, s);
    }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');

    window.fbq('init', META_PIXEL_ID);
    // Explicit Meta Consent Mode signal so server-side knows this load is opted-in.
    window.fbq('consent', 'grant');
    window.fbq('track', 'PageView');
    _revoked = false;
    console.info('[analytics] Meta Pixel loaded (consent: marketing=true)');
  }

  var _revoked = false;
  function _revokeMetaPixel() {
    if (!_loaded.metaPixel || _revoked) return;
    if (typeof window.fbq !== 'function') return;
    window.fbq('consent', 'revoke');
    _revoked = true;
    console.info('[analytics] Meta Pixel consent revoked');
  }

  /* ─────────────── Master loader — runs for every tool ─────────────── */
  function _loadIfConsented() {
    var consent = window.ZdConsent && window.ZdConsent.get();
    if (!consent) return;  // banner not yet shown / no choice made → load nothing

    /* analytics-tier tools */
    if (consent.analytics) {
      _loadContentsquare();
    } else if (_loaded.contentsquare) {
      // Contentsquare runtime opt-out (consent revoked mid-session)
      window._uxa = window._uxa || [];
      window._uxa.push(['optout']);
      console.info('[analytics] Contentsquare opt-out sent (consent revoked)');
    }

    /* marketing-tier tools (advertising pixels) */
    if (consent.marketing) {
      _loadMetaPixel();
    } else {
      _revokeMetaPixel();
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
