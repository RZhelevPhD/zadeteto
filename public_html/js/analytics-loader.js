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
 *   - Google Analytics 4 (GA4 — site analytics)
 *     Gated on:  ZdConsent.has('analytics')
 *     Consent:   uses Google Consent Mode v2 — defaults to 'denied' before
 *                opt-in, switches to 'granted' on accept, back to 'denied'
 *                on revoke (no full unload, but data collection stops)
 *     Cookies:   _ga, _ga_MT3ENS0YGX — in cookie-banner.js COOKIE_MAP under 'analytics'
 *
 * Pending (waiting on IDs from user):
 *   - Google Ads (-> marketing) — separate AW-XXX ID, will piggyback on gtag.js
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
  var GA4_ID           = 'G-MT3ENS0YGX';
  var GOOGLE_ADS_ID    = null;  // pending: 'AW-XXXXXXX'
  var TIKTOK_PIXEL_ID  = null;  // pending: 'CXXXXXXXX...'

  var _loaded = {};       // map of tool names → boolean
  var _revoked = false;   // Meta Pixel revoke flag
  var _ga4Revoked = false; // GA4 revoke flag

  /* ─── Google Consent Mode v2 default — MUST run before gtag.js loads,
   *     on every page load, regardless of prior consent state.
   *     Google requires denied "pings" to model conversions for users who
   *     never opt in. We flip these to 'granted' inside _loadGA4() once
   *     the visitor accepts analytics consent. */
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
  window.gtag('consent', 'default', {
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
    analytics_storage: 'denied',
    wait_for_update: 2000
  });

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

  function _revokeMetaPixel() {
    if (!_loaded.metaPixel || _revoked) return;
    if (typeof window.fbq !== 'function') return;
    window.fbq('consent', 'revoke');
    _revoked = true;
    console.info('[analytics] Meta Pixel consent revoked');
  }

  /* ─────────────── Google Analytics 4 (gtag.js) ─────────────── */
  function _loadGA4() {
    if (_loaded.ga4) return;
    if (!GA4_ID) return;
    _loaded.ga4 = true;

    // dataLayer + gtag shim + denied 'default' already initialised at IIFE top.
    // Flip analytics_storage to granted; ad_* stays denied until Google Ads wires in.
    window.gtag('consent', 'update', { analytics_storage: 'granted' });

    window.gtag('js', new Date());
    window.gtag('config', GA4_ID, { anonymize_ip: true });

    _injectScript('https://www.googletagmanager.com/gtag/js?id=' + GA4_ID);
    _ga4Revoked = false;
    console.info('[analytics] GA4 loaded (consent: analytics=true)');
  }

  function _revokeGA4() {
    if (!_loaded.ga4 || _ga4Revoked) return;
    if (typeof window.gtag !== 'function') return;
    window.gtag('consent', 'update', {
      analytics_storage: 'denied',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
    _ga4Revoked = true;
    console.info('[analytics] GA4 consent revoked');
  }

  /* ─────────────── Master loader — runs for every tool ─────────────── */
  function _loadIfConsented() {
    var consent = window.ZdConsent && window.ZdConsent.get();
    if (!consent) return;  // banner not yet shown / no choice made → load nothing

    /* analytics-tier tools */
    if (consent.analytics) {
      _loadContentsquare();
      _loadGA4();
    } else {
      if (_loaded.contentsquare) {
        // Contentsquare runtime opt-out (consent revoked mid-session)
        window._uxa = window._uxa || [];
        window._uxa.push(['optout']);
        console.info('[analytics] Contentsquare opt-out sent (consent revoked)');
      }
      _revokeGA4();
    }

    /* marketing-tier tools (advertising pixels) */
    if (consent.marketing) {
      _loadMetaPixel();
    } else {
      _revokeMetaPixel();
    }
  }

  /* Defer non-essential tracker loads off the critical path. The Consent
   * Mode v2 default at the top of this IIFE has already run synchronously,
   * so Google has its denied "ping" baseline before gtag.js arrives. The
   * heavy injects (Contentsquare, fbevents, gtag.js) and any chained loads
   * those scripts trigger (Meta Pixel pulls Google Maps JS for Advanced
   * Matching) are pushed onto requestIdleCallback so they don't compete
   * with the search page's first paint. Safari falls back to a 1.5s
   * timeout.
   *
   * Consent-change events (banner accept / revoke) fire the loader
   * immediately — those are user-driven and shouldn't feel delayed. */
  function _scheduleIdle(fn) {
    if (typeof window.requestIdleCallback === 'function') {
      window.requestIdleCallback(fn, { timeout: 4000 });
    } else {
      setTimeout(fn, 1500);
    }
  }

  /* For returning visitors who already accepted analytics, the stored
   * consent is known synchronously from localStorage via ZdConsent. Apply it
   * to the Consent Mode dataLayer immediately, BEFORE deferring gtag.js load.
   * Otherwise the 2000ms wait_for_update window (set in the synchronous
   * 'default' call above) can expire before the deferred gtag.js loads —
   * Google then sends the first pageview ping in 'denied' state and modelled
   * conversions never get the chance to apply the user's actual choice.
   * Marketing flag handled the same way for completeness. */
  function _applyStoredConsentToDataLayer() {
    var c = window.ZdConsent && window.ZdConsent.get && window.ZdConsent.get();
    if (!c) return;
    var update = {};
    if (c.analytics) update.analytics_storage = 'granted';
    if (c.marketing) {
      update.ad_storage = 'granted';
      update.ad_user_data = 'granted';
      update.ad_personalization = 'granted';
    }
    if (Object.keys(update).length) window.gtag('consent', 'update', update);
  }

  /* ─────────────── Init ─────────────── */
  // 1. Schedule the initial consented-tool load for browser idle. Heavy
  //    third-party JS waits until the page is interactive.
  if (window.ZdConsent) {
    _applyStoredConsentToDataLayer();
    _scheduleIdle(_loadIfConsented);
  } else {
    document.addEventListener('DOMContentLoaded', function () {
      _applyStoredConsentToDataLayer();
      _scheduleIdle(_loadIfConsented);
    });
  }

  // 2. React to consent changes from the banner UI — no defer; user just
  //    clicked Accept/Revoke and should see the effect immediately.
  window.addEventListener('zd-consent-change', function (e) {
    _loadIfConsented();
  });
})();
