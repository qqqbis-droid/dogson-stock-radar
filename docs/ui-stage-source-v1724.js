(()=>{
  if(window.__DOGSON_STAGE_SOURCE_V1724__) return;
  window.__DOGSON_STAGE_SOURCE_V1724__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const clean=s=>String(s??'').replace(/\s+/g,' ').trim();
  const stageRules={
    setup:/蓄勢/,
    launch:/剛啟動/,
    pull:/回踩/,
    trend:/趨勢|持有/,
    weak:/轉弱|失效/,
    hot:/過熱/
  };
  const stageClasses=['setup','start','pull','trendhold','watch','weak','invalid','hot'];
  let busy=false,timer=null,lastTruth=null;

  function modeNow(){try{return mode||'intraday'}catch{return'intraday'}}
  function liveReady(){return window.DOGSON_INTRADAY_LIVE_READY===true}
  function portfolioNow(){try{return !!portfolioOnly}catch{return false}}
  function state(){try{return window.DOGSON_FILTER_UX?.getState?.()||{}}catch{return{}}}
  function codeOf(card){return String(card?.dataset?.code||$('.code',card)?.textContent||'').trim()}
  function stageOf(r){
    if(!r)return'';
    try{if(typeof stageKey==='function')return clean(stageKey(r.category))}catch{}
    return clean(r.category||r.stage||'');
  }
  function stageMatch(r,key){const rx=stageRules[key];return !rx||rx.test(stageOf(r))}

  // Single source of truth for stock rows:
  // intraday mode uses intraRows ONLY when live quality is explicitly true;
  // otherwise the whole stock-card layer uses the latest completed closeRows.
  function canonicalRows(m=modeNow()){
    try{
      if(m==='daytrade')return Array.isArray(daytradeRows)?daytradeRows:[];
      if(m==='close')return Array.isArray(closeRows)?closeRows:[];
      if(m==='intraday'){
        if(liveReady())return Array.isArray(intraRows)?intraRows:[];
        return Array.isArray(closeRows)?closeRows:[];
      }
    }catch{}
    return [];
  }

  function canonicalMap(){
    const map=new Map();
    canonicalRows().forEach(r=>{const c=String(r?.code||'');if(c)map.set(c,r)});
    return map;
  }

  function allowedCodes(map,st){
    const active=!!(st.stage||st.decision||st.watch);
    if(!active)return null;
    let rows=Array.isArray(window.DOGSON_FILTERED_ROWS)?window.DOGSON_FILTERED_ROWS:[];
    const codes=new Set();
    rows.forEach(r=>{
      const c=String(r?.code||'');
      const canonical=map.get(c);
      if(!c||!canonical)return;
      if(st.stage&&!stageMatch(canonical,st.stage))return;
      codes.add(c);
    });
    return codes;
  }

  function stageClass(r){
    try{if(typeof cls==='function')return String(cls(r?.category)||'').trim()}catch{}
    const s=stageOf(r);
    if(/蓄勢/.test(s))return'setup';
    if(/剛啟動/.test(s))return'start';
    if(/回踩/.test(s))return'pull';
    if(/趨勢|持有/.test(s))return'trendhold';
    if(/過熱/.test(s))return'hot';
    if(/失效/.test(s))return'invalid';
    if(/轉弱/.test(s))return'weak';
    return'watch';
  }

  function patchStageNode(node,label,row){
    if(!node)return;
    if(clean(node.textContent)!==label)node.textContent=label;
    if(node.dataset?.v164Full!==label)node.dataset.v164Full=label;
    if(node.dataset?.v166Full!==undefined&&node.dataset.v166Full!==label)node.dataset.v166Full=label;
    stageClasses.forEach(c=>node.classList.remove(c));
    const c=stageClass(row);if(c)node.classList.add(c);
    if(!node.classList.contains('cat'))node.classList.add('cat');
  }

  function syncCard(card,map,allowed,st){
    const code=codeOf(card);if(!code)return;
    if(allowed&&!allowed.has(code)){card.remove();return;}
    const row=map.get(code);if(!row){if(allowed)card.remove();return;}
    if(st.stage&&!stageMatch(row,st.stage)){card.remove();return;}
    const label=stageOf(row);if(!label)return;
    const nodes=new Set([
      ...$$('.cat',card),
      ...$$('[data-dogson-quick="stage"]',card),
      ...$$('.stagebox .cat',card)
    ]);
    nodes.forEach(n=>patchStageNode(n,label,row));
    card.dataset.dogsonCanonicalStage=label;
    card.dataset.dogsonStageSource=modeNow()==='intraday'?(liveReady()?'intraday':'close'):modeNow();
  }

  function sync(){
    if(busy||portfolioNow())return;
    const m=modeNow();if(!['intraday','close'].includes(m))return;
    busy=true;
    try{
      const st=state(),map=canonicalMap(),allowed=allowedCodes(map,st);
      window.DOGSON_CANONICAL_STAGE_SOURCE=m==='intraday'?(liveReady()?'intraday':'close'):m;
      window.DOGSON_CANONICAL_STAGE_ROWS=[...map.values()];
      window.DOGSON_CANONICAL_STAGE_BY_CODE=map;
      $$('#cards .card[data-code]').forEach(card=>syncCard(card,map,allowed,st));
    }finally{busy=false}
  }

  function schedule(delay=25){clearTimeout(timer);timer=setTimeout(sync,delay)}
  function rerenderForTruth(){
    const truth=liveReady()?'intraday':'close';
    if(lastTruth===truth){schedule();return;}
    lastTruth=truth;
    try{if(typeof render==='function')render()}catch{}
    schedule(35);
  }

  function boot(){
    lastTruth=liveReady()?'intraday':'close';
    sync();
    const root=$('#cards')||document.body;
    new MutationObserver(()=>schedule()).observe(root,{subtree:true,childList:true,characterData:true});
    window.addEventListener('dogson:data-truth',rerenderForTruth);
    window.addEventListener('dogson:freshness',()=>schedule(40));
    document.addEventListener('click',e=>{if(e.target?.closest?.('[data-ux-stage],[data-ux-decision],[data-ux-clear],.dogson-mode-stat-v1701,.tab,#dogsonViewNav'))schedule(35)},true);
    setTimeout(sync,120);setTimeout(sync,500);setInterval(sync,2500);
  }

  window.DOGSON_STAGE_SOURCE={
    rows:()=>canonicalRows(),
    row:code=>canonicalMap().get(String(code))||null,
    source:()=>modeNow()==='intraday'?(liveReady()?'intraday':'close'):modeNow()
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
