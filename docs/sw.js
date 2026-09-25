const CACHE='dogson-free-v1675';
const UI_VERSION='1675';

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll([
      './manifest.webmanifest',
      './hourly.js?v=1530',
      './realtime-config.js?v=1675',
      './realtime.js?v=1675',
      './ui-filters.js?v=1675',
      './redesign-v160.css?v=1675',
      './redesign-v160-dark.css?v=1675',
      './contrast-v160.css?v=1675',
      './redesign-v162.css?v=1675',
      './redesign-v162-fix.css?v=1675',
      './redesign-v163.css?v=1675',
      './redesign-v164.css?v=1675',
      './redesign-v165.css?v=1675',
      './redesign-v166.css?v=1675',
      './redesign-v160.js?v=1675',
      './ui-polish-v160.js?v=1675',
      './ui-layout-v162.js?v=1675',
      './ui-card-v164.js?v=1675',
      './ui-card-v166.js?v=1675',
      './ui-fold-v167.js?v=1675'
    ]))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil((async()=>{
    await caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))));
    await self.clients.claim();
    // One activation-time navigation clears iOS/PWA pages that are still holding
    // the legacy v151/v1530 boot URLs. This runs only when this worker activates.
    const clients = await self.clients.matchAll({type:'window', includeUncontrolled:true});
    await Promise.all(clients.map(async client => {
      try { await client.navigate(client.url); } catch (_) {}
    }));
  })());
});

async function freshDocument(req){
  const res = await fetch(req, { cache: 'no-store' });
  const type = res.headers.get('content-type') || '';
  if (!res.ok || !type.includes('text/html')) return res;

  let html = await res.text();
  // The large legacy index still contains old static boot query strings.
  // Rewrite only those boot URLs at response time so the current UI loader wins,
  // without touching scoring/render logic in index.html.
  html = html
    .replaceAll('./sw.js?v=1530', `./sw.js?v=${UI_VERSION}`)
    .replaceAll('dogsonSwReloaded1530', `dogsonSwReloaded${UI_VERSION}`)
    .replaceAll('./realtime-config.js?v=151', `./realtime-config.js?v=${UI_VERSION}`)
    .replaceAll('./realtime.js?v=151', `./realtime.js?v=${UI_VERSION}`);

  const headers = new Headers(res.headers);
  headers.delete('content-length');
  headers.delete('content-encoding');
  headers.set('cache-control','no-store, max-age=0');
  return new Response(html, {status:res.status, statusText:res.statusText, headers});
}

self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);

  if (url.pathname.includes('/data/')) {
    event.respondWith(fetch(req, { cache: 'no-store' }));
    return;
  }

  if (req.mode === 'navigate' || req.destination === 'document') {
    event.respondWith(
      freshDocument(req).catch(() => caches.match('./index.html'))
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
