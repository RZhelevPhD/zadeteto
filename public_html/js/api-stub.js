/* === ZaDeteto Form Submission API ===
 *
 * Single entry point for ALL form submissions site-wide.
 *   ZdApi.submitForm(endpoint, payload, options) -> Promise
 *
 * Behaviour (offline-first):
 *   1. If ZdSupabase is loaded → POST via supabase-js insert.
 *      On success, resolve with the inserted row's id.
 *      On failure (network/RLS/etc), persist to localStorage AND
 *      still resolve successfully so the user sees the success state.
 *   2. If ZdSupabase is NOT loaded (CDN failed, offline mode) →
 *      persist to localStorage and resolve as if it succeeded.
 *
 * Endpoints map directly to Supabase tables:
 *   - "partner_applications"  (partners.html)
 *   - "contact_messages"      (contacts.html)
 *   - "reports"               (report.html)
 *   - "feedback_log"          (search.html dismiss feedback wizard)
 *   - "reviews"               (search.html mobile review sheet)
 *
 * Pending recovery: open DevTools console on any page →
 *   ZdApi.getPending()    // see queued localStorage submissions
 *   ZdApi.clearPending()  // wipe after manual import
 */
(function () {
  var STORAGE_KEY = 'zd_pending_submissions';
  var STUB_DELAY_MS = 350;  // small UX delay so loading states render even when network is fast

  // Some forms send camelCase keys but the Supabase columns are snake_case.
  // Map per-endpoint here so the form code stays untouched.
  var KEY_ALIASES = {
    feedback_log: { otherText: 'other_text', timestamp: null },  // null = strip
    reviews:      { timestamp: null }                             // strip; created_at auto-set
  };

  function _normalizePayload(endpoint, payload) {
    var aliases = KEY_ALIASES[endpoint];
    if (!aliases) return payload;
    var out = {};
    Object.keys(payload).forEach(function (k) {
      if (aliases[k] === null) return;            // drop
      var newKey = aliases[k] || k;
      out[newKey] = payload[k];
    });
    return out;
  }

  function _persistLocally(endpoint, payload) {
    try {
      var log = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      log.push({
        endpoint: endpoint,
        payload: payload,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: location.href
      });
      // Cap at 200 entries so localStorage doesn't bloat
      if (log.length > 200) log = log.slice(-200);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(log));
      return true;
    } catch (e) {
      console.warn('[ZdApi] Could not persist submission to localStorage:', e);
      return false;
    }
  }

  // ─────────── REAL SUBMISSION (Supabase + offline fallback) ───────────
  function _doSubmit(endpoint, payload) {
    var normalized = _normalizePayload(endpoint, payload);

    // No Supabase client → offline-only mode (CDN failed, init not loaded)
    if (typeof window.ZdSupabase === 'undefined') {
      _persistLocally(endpoint, payload);
      console.warn('[ZdApi] ZdSupabase not loaded, saved to localStorage:', endpoint);
      return new Promise(function (resolve) {
        setTimeout(function () {
          resolve({ ok: true, id: 'offline-' + Date.now(), offline: true });
        }, STUB_DELAY_MS);
      });
    }

    // IMPORTANT: do NOT chain `.select()` after `.insert()` here.
    //
    // For form tables like contact_messages / reports / partner_applications /
    // feedback_log / reviews, the SELECT policy is admin-only by design (we
    // don't want the public to read back submitted forms). If we ask
    // PostgREST to return the inserted row via `.select()`, the implicit
    // RETURNING clause runs through the SELECT policy and fails — even
    // though the INSERT itself succeeds. PostgREST then rolls back the
    // whole transaction and returns the misleading error
    //   "new row violates row-level security policy for table X".
    //
    // Solution: do a bare insert (sends `Prefer: return=minimal`), and
    // synthesize an id locally for the response. The form code only uses
    // the returned id for optional sessionStorage tracking, never as a
    // foreign key, so a synthetic id is fine.
    return window.ZdSupabase
      .from(endpoint)
      .insert(normalized)
      .then(function (res) {
        if (res.error) throw res.error;
        return { ok: true, id: 'inserted-' + Date.now() };
      })
      .catch(function (err) {
        // Network failure / RLS rejection / schema mismatch — persist locally
        // so the submission isn't lost, and still resolve successfully so the
        // user sees the success state. The pending log can be reconciled later.
        _persistLocally(endpoint, payload);
        console.error('[ZdApi] Supabase insert failed, saved locally:', endpoint, err);
        return { ok: true, id: 'queued-' + Date.now(), queued: true, error: err.message };
      });
  }
  // ─────────────────────────────────────────────────────────────────────

  /**
   * submitForm(endpoint, payload, options)
   *
   * @param {string} endpoint  e.g. "contact_messages"
   * @param {Object} payload   plain JS object — will be JSON-stringified
   * @param {Object} [options] reserved for future use
   * @returns {Promise<{ok: boolean, id: string}>}
   */
  function submitForm(endpoint, payload, options) {
    if (!endpoint || typeof endpoint !== 'string') {
      return Promise.reject(new Error('submitForm: endpoint required'));
    }
    if (!payload || typeof payload !== 'object') {
      return Promise.reject(new Error('submitForm: payload object required'));
    }
    return _doSubmit(endpoint, payload);
  }

  /**
   * Returns all locally-queued submissions, useful during the stub period
   * for manually inspecting what users have sent. Open DevTools console:
   *   ZdApi.getPending()      // see all
   *   ZdApi.clearPending()    // wipe after manual import
   */
  function getPending() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
    catch (e) { return []; }
  }
  function clearPending() {
    try { localStorage.removeItem(STORAGE_KEY); return true; }
    catch (e) { return false; }
  }

  // Expose to window
  window.ZdApi = {
    submitForm: submitForm,
    getPending: getPending,
    clearPending: clearPending
  };
})();
