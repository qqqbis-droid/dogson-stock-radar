(()=>{
  if(window.__DOGSON_DATA_BOOTSTRAP_V1751__) return;
  window.__DOGSON_DATA_BOOTSTRAP_V1751__=true;

  const REV='1751data2';
  const startedAt=Date.now();
  const loading=new Map();
  const hasRows=v=>Array.isArray(v)&&v.length>0;

  const modeNow=()=>{try{return mode||'intraday'}catch{return'intraday'}};
  const closeList=()=>{try{return Array.isArray(closeRows)?closeRows:[]}catch{return[]}};
  const intraList=()=>{try{return Array.isArray(intraRows)?intraRows:[]}catch{return[]}};
  const dayList=()=>{try{return Array.isArray(daytradeRows)?daytradeRows:[]}catch{return[]}};
  const universeList=()=>{try{return Array.isArray(universe)?universe:[]}catch{return[]}};

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
    window.DOGSON_DATA_BOOTSTRAP_STATE={source,at:Date.now(),close:hasRows(closeList()),intraday:hasRows(intraList()),daytrade:hasRows(dayList())};
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
    try{
      closeMarket=m;
      if(!intraMarket||!Object.keys(intraMarket).length)intraMarket=m;
      if(!daytradeMarket||!Object.keys(daytradeMarket).length)daytradeMarket=m;
      if(modeNow()==='close')market=m;
      else if(!market||!Object.keys(market).length)market=intraMarket||m;
    }catch{}
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
    if(hasRows(universeList()))return;
    try{const u=await json('universe','recover');if(Array.isArray(u))universe=u}catch{}
  }

  async function loadSource(name){
    if(loading.has(name))return loading.get(name);
    if(name==='close'&&hasRows(closeList()))return;
    if(name==='intraday'&&hasRows(intraList()))return;
    if(name==='daytrade'&&hasRows(dayList()))return;

    const p=(async()=>{
      try{
        const j=await json(name,'recover');
        if(name==='close'){
          closeRows=Array.isArray(j?.rows)?j.rows:[];
          sectorFunds=Array.isArray(j?.sector_funds)?j.sector_funds:[];
          if(modeNow()==='close')market=closeMarket||{};
        }else if(name==='intraday'){
          intraRows=Array.isArray(j?.rows)?j.rows:[];
          intraMarket=j?.market||closeMarket||{};
          marketLive=j?.market_intraday||{};
          sectorRotation=Array.isArray(j?.sector_rotation)?j.sector_rotation:[];
          changeRadar=j?.change_radar||{};
          if(modeNow()==='intraday')market=intraMarket||closeMarket||{};
        }else if(name==='daytrade'){
          daytradeReport=j||{};
          daytradeRows=Array.isArray(j?.rows)?j.rows:[];
          daytradeMarket=j?.market||intraMarket||closeMarket||{};
          if(modeNow()==='daytrade')market=daytradeMarket||{};
        }
        paint();emit(name);
        [300,900,2200].forEach(ms=>setTimeout(paint,ms));
      }catch(e){
        window.DOGSON_DATA_BOOTSTRAP_ERROR=`${name}: ${e?.message||e}`;
      }finally{loading.delete(name)}
    })();
    loading.set(name,p);return p;
  }

  async function recover(){
    if(hasRows(closeList())||hasRows(intraList())){emit('legacy-ready');return}
    const first=taipeiSession()?'intraday':'close';
    const second=first==='intraday'?'close':'intraday';
    await loadSource(first);
    await loadUniverse();
    if(second==='close'&&!hasRows(closeList()))await loadSource('close');
    if(second==='intraday'&&!hasRows(intraList()))await loadSource('intraday');
    try{validationReport=await json('validation','recover');paint()}catch{}
  }

  function ensureForView(){
    const m=modeNow();
    if(m==='daytrade')loadSource('daytrade');
    else if(m==='close')loadSource('close');
    else if(!hasRows(intraList())&&!hasRows(closeList()))recover();
  }

  function boot(){
    loadSmall();
    // Give the legacy first request a short head start; recover independently if it stalls/fails.
    setTimeout(recover,4500);
    document.addEventListener('click',e=>{if(e.target?.closest?.('#dogsonViewNav,.tab'))setTimeout(ensureForView,80)},true);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-startedAt>2500)ensureForView()});
    let n=0;const heal=setInterval(()=>{n++;if(hasRows(closeList())||hasRows(intraList()))paint();if(n>=24)clearInterval(heal)},1000);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();