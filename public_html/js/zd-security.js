/* ═══════════════════════════════════════════════════════════════
   zd-security.js  —  Shared escaping & URL sanitisation
   Load this BEFORE any inline <script> that renders DB content.
   ═══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var ESC_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

  /**
   * Escape a string for safe insertion into innerHTML / template literals.
   * Returns '' for non-string input.
   */
  function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/[&<>"']/g, function (c) { return ESC_MAP[c]; });
  }

  /**
   * Sanitise a URL for safe use in href attributes.
   * Allows http(s), tel, mailto only.  Returns '#' for anything else
   * (blocks javascript:, data:, vbscript:, etc.).
   */
  function sanitizeUrl(url) {
    if (typeof url !== 'string') return '#';
    var t = url.trim();
    if (t === '' || t === '#') return t;
    // Protocol-relative is OK (//example.com)
    if (t.indexOf('//') === 0) return url;
    var proto = t.toLowerCase().split(/[?#]/)[0];
    if (/^https?:\/\//i.test(proto) || /^tel:/i.test(proto) || /^mailto:/i.test(proto)) {
      return url;
    }
    return '#';
  }

  window.ZdSec = {
    escapeHtml: escapeHtml,
    sanitizeUrl: sanitizeUrl
  };
})();
