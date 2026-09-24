const CACHE='dogson-free-v1600';

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll([
      './manifest.webmanifest',
      './hourly.js?v=1530',
      './realtime-config.js?v=1600',
      './realtime.js?v=1600',
      './ui-filters.js?v=1600',
      './redesign-v160.css?v=1600-1',
      './redesign-v160.js?v=1600-1'
    ]))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    Promise.all([
      caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))),
      self.clients.claim()
    ])
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);

  // Market JSON is always network-only; the page adds its own cache buster too.
  if (url.pathname.includes('/data/')) {
    event.respondWith(fetch(req, { cache: 'no-store' }));
    return;
  }

  // HTML/navigation is network-first so releases are visible immediately.
  if (req.mode === 'navigate' || req.destination === 'document') {
    event.respondWith(
      fetch(req, { cache: 'no-store' }).catch(() => caches.match('./index.html'))
    );
    return;
  }

  // Static assets are also network-first. Cache is only an offline fallback.
  event.respondWith(
    fetch(req, { cache: 'no-store' }).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(cache => cache.put(req, copy));
      return res;
    }).catch(() => caches.match(req))
  );
});
