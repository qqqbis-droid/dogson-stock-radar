(()=>{
  if(window.__DOGSON_DATA_BOOTSTRAP_V1751__) return;
  window.__DOGSON_DATA_BOOTSTRAP_V1751__=true;

  const REV='1751data1';
  const startedAt=Date.now();
  const loaded={close:false,intraday:false,daytrade:false,universe:false};
  const loading=new Map();

  const hasRows=v=>Array.isArray(v)&&v.length>0;
  const get=(name,fallback)=>{try{return globalThis[name]??fallback}catch{return fallback}};
  const set=(name,value)=>{try{globalThis[name]=value}catch{}};

  function taipeiSession(){
    try{
      const p={};
      new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'})
        .formatToParts(new Date()).forEach(x=>{if(x.type!=='literal')p[x.type]=x.value});
      const m=Number(p.hour)*60+Number(p.minute);
      return ['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday)&&m>=535&&m<=815;
    }catch{return false}
  }

  async function json(name,tag='boot'){
    const r=await fetch(`./data/${name}.json?${tag}=${REV}&t=${Date.now()}`,{cache:'no-store'});
    if(!r.ok) throw new Error(`${name} HTTP ${r.status}`);
    return await r.json();
  }

  function emit(source){
    window.DOGSON_DATA_BOOTSTRAP_STATE={source,at:Date.now(),close:hasRows(get('closeRows',[])),intraday:hasRows(get('intraRows',[])),daytrade:hasRows(get('daytradeRows',[]))};
    try{window.dispatchEvent(new CustomEvent('dogson:data-ready',{detail:window.DOGSON_DATA_BOOTSTRAP_STATE}))}catch{}
  }

  function paint(){
    try{if(typeof syncModeFilters==='function')syncModeFilters()}catch{}
    try{if(typeof marketHTML==='function'){const x=document.getElementById('marketbox');if(x)x.innerHTML=marketHTML()}}catch{}
    try{if(typeof validationHTML==='function'){const x=document.getElementById('validationbox');if(x)x.innerHTML=validationHTML()}}catch{}
    try{if(typeof rotationHTML==='function'){const x=document.getElementById('rotationbox');if(x)x.innerHTML=rotationHTML()}}catch{}
    try{if(typeof changeRadarHTML==='function'){const x=document.getElementById('changebox');if(x)x.innerHTML=changeRadarHTML()}}catch{}
    try{if(typeof render==='function')render()}catch{}
  }

  function applyMarket(m){
    if(!m||typeof m!=='object')return;
    set('closeMarket',m);
    const im=get('intraMarket',{});if(!im||!Object.keys(im).length)set('intraMarket',m);
    const dm=get('daytradeMarket',{});if(!dm||!Object.keys(dm).length)set('daytradeMarket',m);
    const mode=get('mode','intraday');
    if(mode==='close')set('market',m);
    else if(!get('market',null)||!Object.keys(get('market',{})).length)set('market',get('intraMarket',m)||m);
  }

  async function loadSmall(){
    const results=await Promise.allSettled([json('market','small'),json('status','small'),json('system_status','small')]);
    if(results[0].status==='fulfilled')applyMarket(results[0].value);
    if(results[1].status==='fulfilled'){
      const s=results[1].value;
      try{const el=document.getElementById('updated');if(el&&s?.updated_at)el.textContent=new Date(s.updated_at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})}catch{}
    }
    if(results[2].status==='fulfilled')window.DOGSON_BOOT_SYSTEM_STATUS=results[2].value;
    paint();emit('small');
  }

  async function loadUniverse(){
    if(loaded.universe||hasRows(get('universe',[])))return;
    try{const u=await json('universe','recover');if(Array.isArray(u)){set('universe',u);loaded.universe=true}}catch{}
  }

  async function loadSource(name){
    if(loading.has(name))return loading.get(name);
    if(name==='close'&&hasRows(get('closeRows',[])))return;
    if(name==='intraday'&&hasRows(get('intraRows',[])))return;
    if(name==='daytrade'&&hasRows(get('daytradeRows',[])))return;

    const p=(async()=>{
      try{
        const j=await json(name,'recover');
        if(name==='close'){
          set('closeRows',Array.isArray(j?.rows)?j.rows:[]);
          set('sectorFunds',Array.isArray(j?.sector_funds)?j.sector_funds:[]);
          loaded.close=hasRows(get('closeRows',[]));
          if(get('mode','intraday')==='close')set('market',get('closeMarket',{}));
        }else if(name==='intraday'){
          set('intraRows',Array.isArray(j?.rows)?j.rows:[]);
          set('intraMarket',j?.market||get('closeMarket',{}));
          set('marketLive',j?.market_intraday||{});
          set('sectorRotation',Array.isArray(j?.sector_rotation)?j.sector_rotation:[]);
          set('changeRadar',j?.change_radar||{});
          loaded.intraday=hasRows(get('intraRows',[]));
          if(get('mode','intraday')==='intraday')set('market',get('intraMarket',get('closeMarket',{})));
        }else if(name==='daytrade'){
          set('daytradeReport',j||{});
          set('daytradeRows',Array.isArray(j?.rows)?j.rows:[]);
          set('daytradeMarket',j?.market||get('intraMarket',get('closeMarket',{})));
          loaded.daytrade=hasRows(get('daytradeRows',[]));
          if(get('mode','intraday')==='daytrade')set('market',get('daytradeMarket',{}));
        }
        paint();emit(name);
        [350,1200,3000].forEach(ms=>setTimeout(paint,ms));
      }catch(e){
        window.DOGSON_DATA_BOOTSTRAP_ERROR=`${name}: ${e?.message||e}`;
      }finally{loading.delete(name)}
    })();
    loading.set(name,p);return p;
  }

  async function recover(){
    if(hasRows(get('closeRows',[]))||hasRows(get('intraRows',[]))){emit('legacy-ready');return}
    const first=taipeiSession()?'intraday':'close';
    const second=first==='intraday'?'close':'intraday';
    await loadSource(first);
    await loadUniverse();
    if(!hasRows(get(second==='close'?'closeRows':'intraRows',[])))await loadSource(second);
    try{const v=await json('validation','recover');set('validationReport',v||{});paint()}catch{}
  }

  function ensureForView(){
    const m=get('mode','intraday');
    if(m==='daytrade')loadSource('daytrade');
    else if(m==='close')loadSource('close');
    else if(!hasRows(get('intraRows',[]))&&!hasRows(get('closeRows',[])))recover();
  }

  function boot(){
    loadSmall();
    setTimeout(recover,8000);
    document.addEventListener('click',e=>{if(e.target?.closest?.('#dogsonViewNav,.tab'))setTimeout(ensureForView,80)},true);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-startedAt>3000)ensureForView()});
    let n=0;const heal=setInterval(()=>{n++;if(hasRows(get('closeRows',[]))||hasRows(get('intraRows',[])))paint();if(n>=30)clearInterval(heal)},1000);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();