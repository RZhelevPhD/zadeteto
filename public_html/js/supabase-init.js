/* === ZaDeteto Supabase initializer ===
 *
 * Loads supabase-js v2 from CDN and exposes ZdSupabase as a global
 * synchronous handle for the rest of the app to use:
 *
 *     ZdSupabase.from('businesses').select('*').eq('published', true)
 *     ZdSupabase.auth.signInWithOtp({ email })
 *     ZdSupabase.auth.signOut()
 *
 * The publishable key embedded below is the **public** Supabase key
 * (sb_publishable_...). It is designed to be exposed in client-side code
 * and can ONLY do what Row Level Security policies allow.
 * NEVER paste the sb_secret_... key here — that one bypasses RLS.
 *
 * If you rotate the publishable key (Supabase Dashboard → Settings → API Keys),
 * update the SUPABASE_PUBLISHABLE_KEY constant below and redeploy.
 */
(function () {
  var SUPABASE_URL = 'https://erfndxmqitavqkfeohxh.supabase.co';
  var SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_S6OcoJLzI0tF-tP_1DseTw__B4Zaz4n';

  // Expose URL/key right away so consumers can read them even before the
  // SDK script finishes loading
  window.ZdSupabaseConfig = {
    url: SUPABASE_URL,
    publishableKey: SUPABASE_PUBLISHABLE_KEY,
    // Backwards-compat alias for any code still reading the old name
    anonKey: SUPABASE_PUBLISHABLE_KEY
  };

  // Inject the supabase-js UMD bundle from jsDelivr (browser-safe, no build step)
  // Using v2.45.x which is current stable as of 2026-04
  var sdkScript = document.createElement('script');
  sdkScript.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.49.4/dist/umd/supabase.js';
  sdkScript.integrity = 'sha384-rwykjmWNwVxboyFmvK9OXN0wj9hnMHA2aAHtits54DuACyCq0M2PrSNxhRb+hvXT';
  sdkScript.crossOrigin = 'anonymous';
  sdkScript.async = false;  // ensure load order is preserved
  sdkScript.onload = function () {
    if (window.supabase && window.supabase.createClient) {
      window.ZdSupabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true
        }
      });
      // Notify any code that was waiting for ZdSupabase to become available
      window.dispatchEvent(new CustomEvent('zd-supabase-ready'));
    } else {
      console.error('[supabase-init] supabase-js loaded but window.supabase.createClient is missing');
    }
  };
  sdkScript.onerror = function () {
    console.warn('[supabase-init] Failed to load supabase-js from CDN. App will run in offline-only mode.');
    // ZdSupabase stays undefined; api-stub.js falls back to localStorage-only behavior
  };
  document.head.appendChild(sdkScript);
})();
