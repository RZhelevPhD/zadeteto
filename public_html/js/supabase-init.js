/* === ZaDeteto Supabase initializer ===
 *
 * Loads supabase-js v2 from CDN and exposes ZdSupabase as a global
 * synchronous handle for the rest of the app to use:
 *
 *     ZdSupabase.from('businesses').select('*').eq('published', true)
 *     ZdSupabase.auth.signInWithOtp({ email })
 *     ZdSupabase.auth.signOut()
 *
 * The anon key embedded below is the **public** Supabase anon key.
 * It is designed to be exposed in client-side code. It can ONLY do what
 * Row Level Security policies allow. NEVER paste a service_role key here.
 *
 * If you regenerate the anon key (Supabase Dashboard → Settings → API),
 * update the SUPABASE_ANON_KEY constant below and redeploy.
 */
(function () {
  var SUPABASE_URL = 'https://erfndxmqitavqkfeohxh.supabase.co';
  var SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyZm5keG1xaXRhdnFrZmVvaHhoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUxNDc4OTcsImV4cCI6MjA5MDcyMzg5N30.q_1MyzvZFnFentGNYHHum1h54scHFQjdf_X3tZmdoR4';

  // Expose URL/key right away so consumers can read them even before the
  // SDK script finishes loading
  window.ZdSupabaseConfig = {
    url: SUPABASE_URL,
    anonKey: SUPABASE_ANON_KEY
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
      window.ZdSupabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
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
