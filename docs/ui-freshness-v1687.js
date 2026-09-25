(()=>{
  if(window.__DOGSON_FRESHNESS_V1687__) return;
  window.__DOGSON_FRESHNESS_V1687__=true;

  const ymd=v=>{
    const s=String(v||'').trim();
    const m=s.match(/(20\d{2})-(\d{2})-(\d{2})/);
    return m?`${m[1]}-${m[2]}-${m[3]}`:'';
  };
  const marketDate=m=>ymd(m?.trade_date)||ymd(m?.taiex?.date)||ymd(m?.otc?.date)||ymd(m?.updated_at);

  function readSources(){
    try{
      if(typeof closeMarket==='undefined'||typeof intraMarket==='undefined') return null;
      return {close:closeMarket||{},intra:intraMarket||{}};
    }catch(_){return null;}
  }

  function modeNow(){try{return mode||'intraday'}catch{return'intraday'}}

  function refreshLegacyBoxes(){
    try{
      if(modeNow()==='intraday'&&window.DOGSON_INTRADAY_STALE&&typeof market!=='undefined') market=closeMarket||{};
      if(typeof marketHTML==='function'){
        const el=document.getElementById('marketbox');
        if(el) el.innerHTML=marketHTML();
      }
    }catch(_){ }
  }

  function apply(){
    const src=readSources();
    if(!src) return false;
    const closeDate=marketDate(src.close);
    const intraDate=marketDate(src.intra);
    if(!closeDate&&!intraDate) return false;

    const stale=!!(closeDate&&(!intraDate||intraDate<closeDate));
    const prev=window.DOGSON_INTRADAY_STALE;
    window.DOGSON_INTRADAY_STALE=stale;
    window.DOGSON_CLOSE_TRADE_DATE=closeDate;
    window.DOGSON_INTRADAY_TRADE_DATE=intraDate;
    window.DOGSON_EFFECTIVE_MARKET_DATE=stale?closeDate:(intraDate||closeDate);

    if(stale&&modeNow()==='intraday'){
      try{market=src.close||{};}catch(_){ }
    }
    refreshLegacyBoxes();

    if(prev!==stale||!window.__DOGSON_FRESHNESS_EMITTED_V1687__){
      window.__DOGSON_FRESHNESS_EMITTED_V1687__=true;
      try{window.dispatchEvent(new CustomEvent('dogson:freshness',{detail:{stale,closeDate,intraDate,effectiveDate:window.DOGSON_EFFECTIVE_MARKET_DATE}}));}catch(_){ }
    }
    return true;
  }

  let tries=0;
  const timer=setInterval(()=>{
    tries+=1;
    if(apply()||tries>=120) clearInterval(timer);
  },50);
  apply();

  document.addEventListener('click',e=>{
    if(e.target?.closest?.('.tab,#dogsonViewNav')) setTimeout(apply,0);
  });
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(apply,0)});
})();
