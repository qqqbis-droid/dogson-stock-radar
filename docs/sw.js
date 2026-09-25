const CACHE='dogson-free-v1688';
const UI_VERSION='1688';

const UI_HEAD=`
<link id="dogson-dashboard-css" rel="stylesheet" href="./redesign-v160.css?v=${UI_VERSION}">
<link id="dogson-dashboard-dark-css" rel="stylesheet" href="./redesign-v160-dark.css?v=${UI_VERSION}">
<link id="dogson-dashboard-contrast-css" rel="stylesheet" href="./contrast-v160.css?v=${UI_VERSION}">
<link id="dogson-dashboard-v162-css" rel="stylesheet" href="./redesign-v162.css?v=${UI_VERSION}">
<link id="dogson-dashboard-v162-fix-css" rel="stylesheet" href="./redesign-v162-fix.css?v=${UI_VERSION}">
<link id="dogson-dashboard-v163-css" rel="stylesheet" href="./redesign-v163.css?v=${UI_VERSION}">
<link id="dogson-dashboard-v164-css" rel="stylesheet" href="./redesign-v164.css?v=${UI_VERSION}">
<link id="dogson-dashboard-v165-css" rel="stylesheet" href="./redesign-v165.css?v=${UI_VERSION}">
<link id="dogson-dashboard-v166-css" rel="stylesheet" href="./redesign-v166.css?v=${UI_VERSION}">
<link id="dogson-dashboard-v1679-css" rel="stylesheet" href="./redesign-v1679.css?v=${UI_VERSION}">
<link id="dogson-dashboard-v1685-css" rel="stylesheet" href="./redesign-v1685.css?v=${UI_VERSION}">
<link id="dogson-dashboard-v1686-css" rel="stylesheet" href="./redesign-v1686.css?v=${UI_VERSION}">
<style id="dogson-boot-v1688">
html.dogson-booting body{background:#f5f6f3!important;overflow:hidden!important}
html.dogson-booting .wrap,html.dogson-booting .footer{opacity:0!important;pointer-events:none!important}
html.dogson-booting body::before{content:'🐶 犬子老師・飆股雷達';position:fixed;z-index:99998;left:0;right:0;top:42%;transform:translateY(-50%);text-align:center;color:#234d40;font:900 20px/1.4 -apple-system,BlinkMacSystemFont,'PingFang TC',sans-serif;letter-spacing:.02em}
html.dogson-booting body::after{content:'正在載入最新介面…';position:fixed;z-index:99999;left:0;right:0;top:calc(42% + 42px);text-align:center;color:#718078;font:700 13px/1.4 -apple-system,BlinkMacSystemFont,'PingFang TC',sans-serif}
</style>
<script id="dogson-decision-filters" src="./ui-filters.js?v=${UI_VERSION}" defer></script>`;

function transformHtml(html){
  if(!html.includes('dogson-boot-v1688')){
    html=html.replace('<html lang="zh-Hant">','<html lang="zh-Hant" class="dogson-booting">');
    html=html.replace('</head>',`${UI_HEAD}\n</head>`);
  }
  return html
    .replace('<meta name="theme-color" content="#0b0d12">','<meta name="theme-color" content="#f5f6f3">')
    .replaceAll('./sw.js?v=1530',`./sw.js?v=${UI_VERSION}`)
    .replaceAll('./realtime-config.js?v=151',`./realtime-config.js?v=${UI_VERSION}`)
    .replaceAll('./realtime.js?v=151',`./realtime.js?v=${UI_VERSION}`)
    .replaceAll('location.reload();','void 0;');
}

function htmlResponse(html,res){
  const headers=new Headers(res.headers);
  headers.delete('content-length');
  headers.delete('content-encoding');
  headers.set('cache-control','no-store, max-age=0');
  return new Response(html,{status:res.status,statusText:res.statusText,headers});
}

async function transformResponse(res){
  const type=res.headers.get('content-type')||'';
  if(!res.ok||!type.includes('text/html')) return res;
  const html=transformHtml(await res.text());
  return htmlResponse(html,res);
}

self.addEventListener('install',event=>{
  self.skipWaiting();
  event.waitUntil((async()=>{
    const cache=await caches.open(CACHE);
    await cache.addAll([
      './manifest.webmanifest',
      './hourly.js?v=1530',
      './realtime-config.js?v=1688',
      './realtime.js?v=1688',
      './ui-filters.js?v=1688',
      './redesign-v160.css?v=1688',
      './redesign-v160-dark.css?v=1688',
      './contrast-v160.css?v=1688',
      './redesign-v162.css?v=1688',
      './redesign-v162-fix.css?v=1688',
      './redesign-v163.css?v=1688',
      './redesign-v164.css?v=1688',
      './redesign-v165.css?v=1688',
      './redesign-v166.css?v=1688',
      './redesign-v1679.css?v=1688',
      './redesign-v1685.css?v=1688',
      './redesign-v1686.css?v=1688',
      './redesign-v160.js?v=1688',
      './ui-polish-v160.js?v=1688',
      './ui-layout-v162.js?v=1688',
      './ui-card-v164.js?v=1688',
      './ui-card-v166.js?v=1688',
      './ui-fold-v167.js?v=1688',
      './ui-entry-v1679.js?v=1688',
      './ui-freshness-v1688.js?v=1688',
      './ui-load-more-v1681.js?v=1688',
      './ui-market-v1685.js?v=1688',
      './ui-market-ticker-v1686.js?v=1688'
    ]);
    try{
      const res=await fetch('./index.html',{cache:'no-store'});
      const out=await transformResponse(res);
      if(out.ok) await cache.put('./index.html',out.clone());
    }catch(_){ }
  })());
});

self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{
    await caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))));
    // Claim immediately, but do NOT navigate/reload open windows. The old
    // navigate + controllerchange reload combination caused blank launches.
    await self.clients.claim();
  })());
});

async function freshDocument(req){
  const res=await fetch(req,{cache:'no-store'});
  const out=await transformResponse(res);
  if(out.ok){
    const cache=await caches.open(CACHE);
    await cache.put('./index.html',out.clone());
  }
  return out;
}

self.addEventListener('fetch',event=>{
  const req=event.request;
  const url=new URL(req.url);

  if(url.pathname.includes('/data/')){
    event.respondWith(fetch(req,{cache:'no-store'}));
    return;
  }

  if(req.mode==='navigate'||req.destination==='document'){
    event.respondWith(
      freshDocument(req).catch(async()=>await caches.match('./index.html')||Response.error())
    );
    return;
  }

  event.respondWith(
    fetch(req,{cache:'no-store'}).then(res=>{
      const copy=res.clone();
      caches.open(CACHE).then(cache=>cache.put(req,copy));
      return res;
    }).catch(()=>caches.match(req))
  );
});
