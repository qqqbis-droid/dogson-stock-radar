const CACHE='dogson-free-v1671';

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll([
      './manifest.webmanifest',
      './hourly.js?v=1530',
      './realtime-config.js?v=1671',
      './realtime.js?v=1671',
      './ui-filters.js?v=1671',
      './redesign-v160.css?v=1671',
      './redesign-v160-dark.css?v=1671',
      './contrast-v160.css?v=1671',
      './redesign-v162.css?v=1671',
      './redesign-v162-fix.css?v=1671',
      './redesign-v163.css?v=1671',
      './redesign-v164.css?v=1671',
      './redesign-v165.css?v=1671',
      './redesign-v166.css?v=1671',
      './redesign-v160.js?v=1671',
      './ui-polish-v160.js?v=1671',
      './ui-layout-v162.js?v=1671',
      './ui-card-v164.js?v=1671',
      './ui-card-v166.js?v=1671',
      './ui-fold-v167.js?v=1671'
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

  if (url.pathname.includes('/data/')) {
    event.respondWith(fetch(req, { cache: 'no-store' }));
    return;
  }

  if (req.mode === 'navigate' || req.destination === 'document') {
    event.respondWith(
      fetch(req, { cache: 'no-store' }).catch(() => caches.match('./index.html'))
    );
    return;
  }

  event.respondWith(
    fetch(req, { cache: 'no-store' }).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(cache => cache.put(req, copy));
      return res;
    }).catch(() => caches.match(req))
  );
});
