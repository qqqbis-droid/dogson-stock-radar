const CACHE='dogson-free-v1681';
const UI_VERSION='1681';

self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll([
      './manifest.webmanifest',
      './hourly.js?v=1530',
      './realtime-config.js?v=1681',
      './realtime.js?v=1681',
      './ui-filters.js?v=1681',
      './redesign-v160.css?v=1681',
      './redesign-v160-dark.css?v=1681',
      './contrast-v160.css?v=1681',
      './redesign-v162.css?v=1681',
      './redesign-v162-fix.css?v=1681',
      './redesign-v163.css?v=1681',
      './redesign-v164.css?v=1681',
      './redesign-v165.css?v=1681',
      './redesign-v166.css?v=1681',
      './redesign-v1679.css?v=1681',
      './redesign-v160.js?v=1681',
      './ui-polish-v160.js?v=1681',
      './ui-layout-v162.js?v=1681',
      './ui-card-v164.js?v=1681',
      './ui-card-v166.js?v=1681',
      './ui-fold-v167.js?v=1681',
      './ui-entry-v1679.js?v=1681',
      './ui-load-more-v1681.js?v=1681'
    ]))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil((async()=>{
    await caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))));
    await self.clients.claim();
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
