(()=>{
  'use strict';

  const nativeFetch=window.fetch.bind(window);
  const shardCache=new Map();
  let active={code:'',view:'',until:0};
  let watchdog=0;

  const FILES={
    'decision-intraday-detail.json':{view:'intraday',kind:'detail'},
    'zone-intraday.json':{view:'intraday',kind:'zones'},
    'stock-detail-intraday.json':{view:'intraday',kind:'evidence'},
    'decision-close-detail.json':{view:'close',kind:'detail'},
    'zone-close.json':{view:'close',kind:'zones'},
    'stock-detail-close.json':{view:'close',kind:'evidence'},
    'decision-daytrade-detail.json':{view:'daytrade',kind:'detail'},
    'zone-daytrade.json':{view:'daytrade',kind:'zones'},
    'stock-detail-daytrade.json':{view:'daytrade',kind:'evidence'}
  };

  function inputUrl(input){
    if(typeof input==='string')return input;
    if(typeof URL!=='undefined'&&input instanceof URL)return input.href;
    if(input&&typeof input.url==='string')return input.url;
    return String(input||'');
  }

  function parseLargeDataset(raw){
    let u;
    try{u=new URL(raw,document.baseURI)}catch{return null}
    const name=u.pathname.split('/').pop()||'';
    const cfg=FILES[name];
    if(!cfg)return null;
    const parts=u.pathname.split('/').filter(Boolean);
    const i=parts.lastIndexOf('builds');
    if(i<0||!parts[i+1])return null;
    return {...cfg,build:decodeURIComponent(parts[i+1]),url:u};
  }

  function currentView(){
    return String(document.querySelector('.tab.active')?.dataset.view||'intraday');
  }

  function codeFromDialog(){
    const dialog=document.getElementById('detailDialog');
    if(!dialog||!dialog.open)return '';
    const text=String(document.getElementById('detailTitle')?.textContent||'').trim();
    return text.match(/^(\d{4,6})\b/)?.[1]||'';
  }

  function resolveContext(hit){
    const now=Date.now();
    if(active.code&&now<=active.until&&active.view===hit.view)return active;

    // Safari can start the module fetch before the CustomEvent listener state is
    // observable to the patched fetch. The dialog title is already written by
    // loadingShell(), so use it as a deterministic same-frame fallback.
    const code=codeFromDialog();
    const view=currentView();
    if(code&&view===hit.view){
      active={code,view,until:now+20000};
      return active;
    }
    return null;
  }

  function shardUrl(build,view,code){
    return new URL(`./data/builds/${encodeURIComponent(build)}/stock-shards/${encodeURIComponent(view)}/${encodeURIComponent(code)}.json`,document.baseURI).href;
  }

  async function fetchWithTimeout(url,ms=8000){
    const controller=typeof AbortController!=='undefined'?new AbortController():null;
    const timer=controller?setTimeout(()=>controller.abort(),ms):0;
    try{
      return await nativeFetch(url,{cache:'no-store',credentials:'same-origin',...(controller?{signal:controller.signal}:{})});
    }finally{
      if(timer)clearTimeout(timer);
    }
  }

  async function loadShard(build,view,code){
    const key=`${build}:${view}:${code}`;
    if(shardCache.has(key))return shardCache.get(key);
    const promise=(async()=>{
      const r=await fetchWithTimeout(shardUrl(build,view,code));
      if(!r.ok)throw new Error(`single-stock shard HTTP ${r.status}`);
      const x=await r.json();
      if(x?.build_id!==build)throw new Error('single-stock shard build mismatch');
      if(String(x?.code||'')!==String(code))throw new Error('single-stock shard code mismatch');
      if(String(x?.view||'')!==String(view))throw new Error('single-stock shard view mismatch');
      if(!x?.decision)throw new Error('single-stock shard decision missing');
      return x;
    })();
    shardCache.set(key,promise);
    try{return await promise}catch(err){shardCache.delete(key);throw err}
  }

  function synthetic(kind,shard){
    const code=String(shard.code);
    if(kind==='detail')return {build_id:shard.build_id,items:{[code]:shard.decision}};
    if(kind==='zones')return Array.isArray(shard.zones)?shard.zones:[];
    return {build_id:shard.build_id,items:{[code]:shard.evidence??null}};
  }

  window.fetch=async function(input,init){
    const hit=parseLargeDataset(inputUrl(input));
    if(!hit)return nativeFetch(input,init);

    const ctx=resolveContext(hit);
    if(!ctx)return nativeFetch(input,init);

    try{
      const shard=await loadShard(hit.build,hit.view,ctx.code);
      return new Response(JSON.stringify(synthetic(hit.kind,shard)),{
        status:200,
        headers:{
          'Content-Type':'application/json; charset=utf-8',
          'Cache-Control':'no-store',
          'X-Inuko-Stock-Shard':'1'
        }
      });
    }catch(err){
      console.error('stock shard adapter',err);
      // Fail closed: never fall back to a multi-megabyte whole-market detail file
      // while a stock detail dialog is open.
      return new Response(JSON.stringify({error:'single-stock shard unavailable'}),{
        status:503,
        headers:{'Content-Type':'application/json; charset=utf-8','X-Inuko-Stock-Shard':'error'}
      });
    }
  };

  function clearWatchdog(){
    if(watchdog){clearTimeout(watchdog);watchdog=0;}
  }

  function armWatchdog(code){
    clearWatchdog();
    watchdog=setTimeout(()=>{
      const dialog=document.getElementById('detailDialog');
      const body=document.getElementById('detailBody');
      const title=String(document.getElementById('detailTitle')?.textContent||'');
      if(!dialog?.open||!body||!title.startsWith(String(code)))return;
      if(!/讀取個股詳情/.test(body.textContent||''))return;
      body.innerHTML='<div class="detail-note warn"><b>個股詳情載入逾時。</b><br>單股資料沒有在 10 秒內完成，系統已停止等待，不會改抓全市場大型檔。請關閉後再點一次。</div>';
    },10000);
  }

  document.addEventListener('radar:open-stock',e=>{
    const code=String(e.detail?.code||'').trim();
    const view=String(e.detail?.view||currentView());
    if(!code||view==='portfolio')return;
    active={code,view,until:Date.now()+20000};
    armWatchdog(code);
  },true);

  document.addEventListener('radar:detail-rendered',()=>{
    clearWatchdog();
    active.until=Math.min(active.until,Date.now()+1500);
  },true);

  document.addEventListener('radar:data-reloaded',()=>{
    clearWatchdog();
    shardCache.clear();
    active={code:'',view:'',until:0};
  });

  document.addEventListener('close',e=>{
    if(e.target?.id==='detailDialog'){
      clearWatchdog();
      active={code:'',view:'',until:0};
    }
  },true);
})();