/* За Детето — Service Worker
 *
 * Phase 1 scaffold: app-shell precache, runtime cache for static assets,
 * navigation fallback to offline.html, versioned cache names, skipWaiting
 * on message so the page can prompt the user to refresh.
 *
 * Bump CACHE_VERSION on every release that changes precached files.
 * The active SW will then drop old caches in `activate`.
 */

const CACHE_VERSION = 'v1';
const PRECACHE = `zd-precache-${CACHE_VERSION}`;
const RUNTIME = `zd-runtime-${CACHE_VERSION}`;

// Keep this list small. Only the shell required to render offline.html
// and the landing page nav. Other pages get cached at runtime on first hit.
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.json',
  '/js/nav-inject.js',
  '/brand_assets/fonts/fonts.css',
  '/brand_assets/fonts/inter-cyrillic.woff2',
  '/brand_assets/fonts/inter-latin.woff2',
  '/brand_assets/fonts/ptserif-700-cyrillic.woff2',
  '/brand_assets/fonts/ptserif-700-latin.woff2',
  '/brand_assets/zadeteto-app-icon.svg',
  '/brand_assets/zadeteto-app-icon-maskable.svg',
  '/brand_assets/zadeteto-logo-horizontal.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(PRECACHE).then((cache) =>
      // addAll is atomic: if any URL fails, the SW install fails.
      // Use individual adds so a missing asset doesn't brick installation.
      Promise.all(
        PRECACHE_URLS.map((url) =>
          cache.add(new Request(url, { cache: 'reload' })).catch((err) => {
            console.warn('[sw] precache miss:', url, err);
          })
        )
      )
    )
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((k) => k !== PRECACHE && k !== RUNTIME)
          .map((k) => caches.delete(k))
      );
      await self.clients.claim();
    })()
  );
});

// Allow the page to tell the waiting SW to take over immediately.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

function isStaticAsset(url) {
  return /\.(?:css|js|woff2?|ttf|otf|eot|svg|png|jpe?g|gif|webp|ico)$/i.test(url.pathname);
}

function isCdnAsset(url) {
  // Tailwind CDN intentionally excluded: it's a JIT script that returns
  // different bytes per page (it scans the DOM), so cross-page caching
  // would serve a build missing classes used on later pages.
  return (
    url.hostname === 'cdnjs.cloudflare.com' ||
    url.hostname === 'fonts.googleapis.com' ||
    url.hostname === 'fonts.gstatic.com'
  );
}

function isSupabase(url) {
  return url.hostname.endsWith('.supabase.co');
}

function isCacheable(response) {
  // Skip opaque responses (cross-origin no-cors): they're 0-byte from the
  // SW's view and would poison the cache with empty matches.
  return response && response.ok && response.type !== 'opaque';
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (isCacheable(response)) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw err;
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const networkPromise = fetch(request)
    .then((response) => {
      if (isCacheable(response)) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);
  return cached || networkPromise || fetch(request);
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Never intercept Supabase — auth + dynamic data, handle in Phase 2.
  if (isSupabase(url)) return;

  // Navigation requests: network-first, fall back to cached page or offline.html.
  // Only cache navigations with no query string to avoid bloating runtime cache
  // with one entry per ?login=true / ?ref=... permutation.
  if (request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        try {
          const response = await fetch(request);
          if (isCacheable(response) && !url.search) {
            const cache = await caches.open(RUNTIME);
            cache.put(request, response.clone());
          }
          return response;
        } catch (err) {
          const cached = await caches.match(request);
          if (cached) return cached;
          const offline = await caches.match('/offline.html');
          return offline || new Response('Offline', { status: 503, statusText: 'Offline' });
        }
      })()
    );
    return;
  }

  // Same-origin static assets: stale-while-revalidate.
  if (url.origin === self.location.origin && isStaticAsset(url)) {
    event.respondWith(staleWhileRevalidate(request, RUNTIME));
    return;
  }

  // Trusted CDNs (GSAP, Tailwind, Google Fonts): SWR so offline pages still render.
  if (isCdnAsset(url)) {
    event.respondWith(staleWhileRevalidate(request, RUNTIME));
    return;
  }

  // Everything else: pass through.
});
