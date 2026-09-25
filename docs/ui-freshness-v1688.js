(()=>{
  if(window.__DOGSON_FRESHNESS_V1688__) return;
  window.__DOGSON_FRESHNESS_V1688__=true;

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
      if(typeof marketHTML==='function'){
        const el=document.getElementById('marketbox');
        if(el) el.innerHTML=marketHTML();
      }
      if(typeof rotationHTML==='function'){
        const el=document.getElementById('rotationbox');
        if(el) el.innerHTML=rotationHTML();
      }
    }catch(_){ }
  }

  function applyEffectiveMarket(src,stale,closeDate,intraDate){
    const selectedMode=modeNow();

    // Mode is user navigation state. Never mutate it here.
    // When intraday data is older than the newest close, only replace the
    // market-environment source; the page remains in 找波段 / intraday mode.
    if(selectedMode==='intraday'){
      const effective=stale?(src.close||{}):(src.intra||{});
      try{market=effective;}catch(_){ }
      window.DOGSON_EFFECTIVE_MARKET=effective;
      window.DOGSON_EFFECTIVE_MARKET_SOURCE=stale?'close':'intraday';
      window.DOGSON_FRESHNESS_FORCED_CLOSE=false;

      if(stale){
        const text=document.getElementById('modeText');
        if(text) text.textContent=`找波段：市場環境引用 ${closeDate||'最近交易日'} 最新盤後資料｜頁面仍維持找波段`;
      }
      return;
    }

    if(selectedMode==='close'){
      try{market=src.close||{};}catch(_){ }
      window.DOGSON_EFFECTIVE_MARKET=src.close||{};
      window.DOGSON_EFFECTIVE_MARKET_SOURCE='close';
      return;
    }

    window.DOGSON_EFFECTIVE_MARKET_SOURCE=selectedMode;
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

    applyEffectiveMarket(src,stale,closeDate,intraDate);
    refreshLegacyBoxes();
    try{if(typeof render==='function') render();}catch(_){ }

    if(prev!==stale||!window.__DOGSON_FRESHNESS_EMITTED_V1688__){
      window.__DOGSON_FRESHNESS_EMITTED_V1688__=true;
      try{window.dispatchEvent(new CustomEvent('dogson:freshness',{detail:{stale,closeDate,intraDate,effectiveDate:window.DOGSON_EFFECTIVE_MARKET_DATE,marketSource:window.DOGSON_EFFECTIVE_MARKET_SOURCE,mode:modeNow()}}));}catch(_){ }
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
