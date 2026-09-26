(()=>{
  if(window.__DOGSON_FILTER_INTEGRITY_V1723__) return;
  window.__DOGSON_FILTER_INTEGRITY_V1723__=true;

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

  function modeNow(){try{return mode||'intraday'}catch{return'intraday'}}
  function portfolioNow(){try{return !!portfolioOnly}catch{return false}}
  function liveReady(){return window.DOGSON_INTRADAY_LIVE_READY===true}
  function uxState(){try{return window.DOGSON_FILTER_UX?.getState?.()||{}}catch{return{}}}
  function stageOf(r){try{return clean(stageKey(r?.category))}catch{return clean(r?.category||'')}}
  function stageMatch(r,key){const rx=stageRules[key];return !rx||rx.test(stageOf(r))}
  function effectiveRows(m){
    try{
      if(m==='close') return Array.isArray(closeRows)?closeRows:[];
      if(m==='intraday'&&!liveReady()) return Array.isArray(closeRows)?closeRows:[];
      if(m==='intraday') return Array.isArray(intraRows)?intraRows:[];
    }catch{}
    return [];
  }

  function finalAllowed(stageRows){
    const uxRows=Array.isArray(window.DOGSON_FILTERED_ROWS)?window.DOGSON_FILTERED_ROWS:null;
    if(!uxRows) return stageRows;
    const stageCodes=new Set(stageRows.map(r=>String(r?.code||'')));
    return uxRows.filter(r=>stageCodes.has(String(r?.code||'')));
  }

  function enforceCards(allowedRows){
    const allowed=new Set((Array.isArray(allowedRows)?allowedRows:[]).map(r=>String(r?.code||'')));
    if(!allowed.size) return;
    $$('#cards .card[data-code]').forEach(card=>{
      const code=String(card.dataset.code||'');
      if(code&&!allowed.has(code)) card.remove();
    });
  }

  function install(){
    if(typeof render!=='function'||render.__dogsonFilterIntegrity1723) return false;
    const inner=render;
    const guarded=function(){
      const m=modeNow(),s=uxState();
      if(!['intraday','close'].includes(m)||portfolioNow()||!s.stage||!stageRules[s.stage]) return inner();

      const source=effectiveRows(m);
      const stageRows=source.filter(r=>stageMatch(r,s.stage));
      const fallback=m==='intraday'&&!liveReady();
      let oldIntra,oldClose;
      try{oldIntra=intraRows}catch{}
      try{oldClose=closeRows}catch{}

      let result;
      try{
        if(m==='close') closeRows=stageRows;
        else if(fallback){ closeRows=stageRows; intraRows=stageRows; }
        else intraRows=stageRows;
        result=inner();
        const allowed=finalAllowed(stageRows);
        window.DOGSON_FILTER_INTEGRITY_ROWS=allowed;
        enforceCards(allowed);
        setTimeout(()=>enforceCards(window.DOGSON_FILTER_INTEGRITY_ROWS||allowed),80);
        return result;
      }finally{
        try{intraRows=oldIntra}catch{}
        try{closeRows=oldClose}catch{}
      }
    };
    guarded.__dogsonFilterIntegrity1723=true;
    guarded.__dogsonInnerRender=inner;
    render=guarded;
    return true;
  }

  function boot(){
    if(install()) return;
    let tries=0;
    const t=setInterval(()=>{tries++;if(install()||tries>100)clearInterval(t)},50);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
