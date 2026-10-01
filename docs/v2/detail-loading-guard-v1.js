(()=>{
  'use strict';

  const nativeFetch=window.fetch.bind(window);
  const shardCache=new Map();
  let active={code:'',view:'',until:0};

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
    if(input instanceof URL)return input.href;
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

  function shardUrl(build,view,code){
    return new URL(`./data/builds/${encodeURIComponent(build)}/stock-shards/${encodeURIComponent(view)}/${encodeURIComponent(code)}.json`,document.baseURI).href;
  }

  async function loadShard(build,view,code){
    const key=`${build}:${view}:${code}`;
    if(shardCache.has(key))return shardCache.get(key);
    const promise=(async()=>{
      const r=await nativeFetch(shardUrl(build,view,code),{cache:'no-store',credentials:'same-origin'});
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
    if(!active.code||Date.now()>active.until||hit.view!==active.view)return nativeFetch(input,init);

    try{
      const shard=await loadShard(hit.build,hit.view,active.code);
      return new Response(JSON.stringify(synthetic(hit.kind,shard)),{
        status:200,
        headers:{'Content-Type':'application/json; charset=utf-8','X-Inuko-Stock-Shard':'1'}
      });
    }catch(err){
      console.error('stock shard adapter',err);
      // Fail closed. Never fall back to the multi-megabyte whole-market file on
      // mobile/detail open; the stock renderer will show its normal error state.
      return new Response(JSON.stringify({error:'single-stock shard unavailable'}),{
        status:503,
        headers:{'Content-Type':'application/json; charset=utf-8','X-Inuko-Stock-Shard':'error'}
      });
    }
  };

  document.addEventListener('radar:open-stock',e=>{
    const code=String(e.detail?.code||'').trim();
    const view=String(e.detail?.view||document.querySelector('.tab.active')?.dataset.view||'intraday');
    if(!code||view==='portfolio')return;
    active={code,view,until:Date.now()+20000};
  },true);

  document.addEventListener('radar:detail-rendered',()=>{
    // Keep the context alive briefly for any synchronous follow-up read, then
    // drop it so unrelated background fetches can never receive a stock shard.
    active.until=Math.min(active.until,Date.now()+1500);
  },true);

  document.addEventListener('radar:data-reloaded',()=>{
    shardCache.clear();
    active={code:'',view:'',until:0};
  });

  document.addEventListener('close',e=>{
    if(e.target?.id==='detailDialog')active={code:'',view:'',until:0};
  },true);
})();
