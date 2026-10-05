const CACHE='dogson-free-v1760';
const UI_VERSION='1760';
const MARKET_UI_REV='1760close1';
const SW_REV='1760close1';

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
html.dogson-booting body::after{content:'正在載入介面與資料…';position:fixed;z-index:99999;left:0;right:0;top:calc(42% + 42px);text-align:center;color:#718078;font:700 13px/1.4 -apple-system,BlinkMacSystemFont,'PingFang TC',sans-serif}
</style>
<script id="inuko-supabase-sdk" src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.2" defer></script>
<script id="inuko-cloud-sync" src="./supabase-cloud-v1.js?v=1" defer></script>
<script id="dogson-decision-filters" src="./ui-filters.js?v=${MARKET_UI_REV}" defer></script>
<script id="dogson-close-health-v1760" src="./ui-close-health-v1760.js?v=${UI_VERSION}" defer></script>`;

function transformHtml(html){
  if(!html.includes('dogson-boot-v1688')){
    html=html.replace('<html lang="zh-Hant">','<html lang="zh-Hant" class="dogson-booting">');
    html=html.replace('</head>',`${UI_HEAD}\n</head>`);
  }
  return html
    .replace('<meta name="theme-color" content="#0b0d12">','<meta name="theme-color" content="#f5f6f3">')
    .replaceAll('./sw.js?v=1530',`./sw.js?v=${SW_REV}`)
    .replaceAll('./realtime-config.js?v=151','./realtime-config.js?v=1751stable4')
    .replaceAll('./realtime.js?v=151',`./realtime.js?v=${UI_VERSION}`)
    .replaceAll('dogsonSwReloaded1530',`dogsonSwReloaded${SW_REV}`)
    .replaceAll('location.reload();','void 0;');
}

function htmlResponse(html,res){const headers=new Headers(res.headers);headers.delete('content-length');headers.delete('content-encoding');headers.set('cache-control','no-store, max-age=0');return new Response(html,{status:res.status,statusText:res.statusText,headers});}
async function transformResponse(res){const type=res.headers.get('content-type')||'';if(!res.ok||!type.includes('text/html'))return res;const html=transformHtml(await res.text());return htmlResponse(html,res);}

const STATIC_ASSETS=[
  './manifest.webmanifest','./hourly.js?v=1530','./realtime-config.js?v=1751stable4','./realtime.js?v=1760','./supabase-cloud-v1.js?v=1','./ui-copy-clean-v1.js?v=2',`./ui-filters.js?v=${MARKET_UI_REV}`,'./ui-close-health-v1760.js?v=1760',
  './redesign-v160.css?v=1760','./redesign-v160-dark.css?v=1760','./contrast-v160.css?v=1760','./redesign-v162.css?v=1760','./redesign-v162-fix.css?v=1760','./redesign-v163.css?v=1760','./redesign-v164.css?v=1760','./redesign-v165.css?v=1760','./redesign-v166.css?v=1760','./redesign-v1679.css?v=1760','./redesign-v1685.css?v=1760','./redesign-v1686.css?v=1760','./redesign-v1690.css?v=1760',
  './ui-data-bootstrap-v1751.js?v=1751data3','./redesign-v160.js?v=1760','./ui-polish-v160.js?v=1760','./ui-layout-v162.js?v=1760','./ui-card-v164.js?v=1760','./ui-card-v166.js?v=1760','./ui-interactions-v163.js?v=1760','./ui-fold-v167.js?v=1760','./ui-entry-v1679.js?v=1760','./ui-freshness-v1688.js?v=1760','./ui-system-status-v1700.js?v=1751light1','./ui-dual-decision-v1690.js?v=1760','./ui-load-more-v1681.js?v=1760','./ui-market-v1685.js?v=1750peer1','./ui-market-ticker-v1686.js?v=1760','./ui-page-architecture-v1701.js?v=1750','./ui-accuracy-guard-v1702.js?v=1750peer2','./ui-runtime-safety-v1720.js?v=1760','./ui-filter-v1730.js?v=1760','./ui-candidate-v1752.js?v=1752candidate2','./ui-shell-v1751.js?v=1751shell2','./ui-card-open-v1752.js?v=1752card2'
];

async function warmStatic(cache,url){
  try{
    const req=new Request(url,{cache:'no-store'});
    const res=await fetch(req);
    if(res.ok)await cache.put(url,res.clone());
    return res.ok;
  }catch{return false}
}

self.addEventListener('install',event=>{
  self.skipWaiting();
  event.waitUntil((async()=>{
    const cache=await caches.open(CACHE);
    await Promise.allSettled(STATIC_ASSETS.map(url=>warmStatic(cache,url)));
    try{const res=await fetch('./index.html',{cache:'no-store'});const out=await transformResponse(res);if(out.ok)await cache.put('./index.html',out.clone())}catch{}
  })());
});

// Do not claim already-open pages. A new worker will control the next navigation,
// avoiding controllerchange -> reload in the middle of app/data initialization.
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))))});

async function freshDocument(req){const res=await fetch(req,{cache:'no-store'});const out=await transformResponse(res);if(out.ok){const cache=await caches.open(CACHE);await cache.put('./index.html',out.clone())}return out;}

function dataCacheKey(url){return new Request(`${url.origin}${url.pathname}`)}
function emptyJson(){return new Response('{}',{status:200,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}})}
const dataInflight=new Map();
async function fetchData(req,url){
  const name=url.pathname.split('/').pop()||'';
  const diagnostic=url.searchParams.has('truth')||url.searchParams.has('shell');
  const heavy=new Set(['close.json','intraday.json','daytrade.json','hourly.json','chip_history.json']);
  if(diagnostic&&heavy.has(name))return emptyJson();

  const key=url.pathname,cache=await caches.open(CACHE),stableKey=dataCacheKey(url);
  if(dataInflight.has(key))return(await dataInflight.get(key)).clone();
  const task=(async()=>{
    try{
      const res=await fetch(req,{cache:'no-store'});
      if(res.ok){await cache.put(stableKey,res.clone());return res}
      const old=await cache.match(stableKey);return old||res;
    }catch{return await cache.match(stableKey)||Response.error()}
  })();
  dataInflight.set(key,task);
  try{return(await task).clone()}finally{dataInflight.delete(key)}
}

async function staticAsset(req){
  const cache=await caches.open(CACHE),hit=await cache.match(req);if(hit)return hit;
  try{const res=await fetch(req,{cache:'no-store'});if(res.ok)await cache.put(req,res.clone());return res}catch{return Response.error()}
}

self.addEventListener('fetch',event=>{
  const req=event.request;if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.pathname.includes('/v2/'))return;
  if(url.pathname.includes('/data/')){event.respondWith(fetchData(req,url));return}
  if(req.mode==='navigate'||req.destination==='document'){event.respondWith(freshDocument(req).catch(async()=>await caches.match('./index.html')||Response.error()));return}
  if(req.destination==='script'||req.destination==='style'||req.destination==='manifest'||/\.(?:js|css|webmanifest)$/.test(url.pathname)){event.respondWith(staticAsset(req));return}
  event.respondWith(fetch(req,{cache:'no-store'}).catch(()=>caches.match(req)));
});
