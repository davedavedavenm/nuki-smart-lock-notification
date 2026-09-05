/* Nuki Console service worker.
 *
 * Deliberately minimal:
 *  - never caches HTML or API responses (lock state must always be live)
 *  - cache-first only for hashed/static assets under /static/
 *  - network-first navigations with a cached login page as the offline
 *    fallback so the installed app opens instead of a browser error
 */
const CACHE = 'nuki-shell-v1';
const OFFLINE_URLS = ['/login', '/static/icons/icon-192.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(OFFLINE_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // Pages: live or bust, with a last-resort offline fallback
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).catch(() => caches.match('/login'))
    );
    return;
  }

  // Static assets: cache-first with background refresh
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.open(CACHE).then(async (c) => {
        const hit = await c.match(req);
        const refresh = fetch(req)
          .then((resp) => {
            if (resp && resp.ok) c.put(req, resp.clone());
            return resp;
          })
          .catch(() => hit);
        return hit || refresh;
      })
    );
  }
});
