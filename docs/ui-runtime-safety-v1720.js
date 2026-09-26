(()=>{
  if(window.__DOGSON_RUNTIME_SAFETY_V1720__) return;
  window.__DOGSON_RUNTIME_SAFETY_V1720__=true;

  const $=(s,r=document)=>r.querySelector(s);
  let repairing=false,timer=null;

  function modeNow(){try{return mode||'intraday'}catch{return'intraday'}}
  function structureLatest(){
    try{
      const rs=Array.isArray(intraRows)?intraRows:[];let latest='';
      for(const r of rs){
        const t=String(r?.structure_time||r?.time||'').slice(0,5);
        if(/^\d{2}:\d{2}$/.test(t)&&t>latest)latest=t;
      }
      return latest;
    }catch{return''}
  }
  function liveReady(){
    const ds=document.documentElement.dataset.dogsonLiveIntraday;
    if(ds==='1')return true;
    if(ds==='0')return false;
    return window.DOGSON_INTRADAY_LIVE_READY===true;
  }
  function truthReady(){return !!window.DOGSON_DATA_TRUTH_V1700}
  function sessionNow(){return window.DOGSON_DATA_TRUTH_V1700?.operational?.clock?.session===true}
  function staleNow(){return window.DOGSON_INTRADAY_STALE===true}

  function setStatus(text,level='warn'){
    const el=$('#status');if(!el||el.textContent===text)return;
    el.textContent=text;
    if(level==='bad'){
      el.style.background='#2c141a';el.style.borderColor='#61303a';el.style.color='#ff9cac';
    }else{
      el.style.background='#2a230f';el.style.borderColor='#66521f';el.style.color='#8b681b';
    }
  }

  function enforceRealtimeTruth(){
    if(repairing)return;repairing=true;
    try{
      if(modeNow()!=='intraday'||!truthReady()||liveReady())return;
      const st=structureLatest()||window.DOGSON_DATA_TRUTH_V1700?.operational?.quality?.structure_latest_time||'—';
      const label=st&&st!=='—'?String(st).slice(0,5):'—';
      if(staleNow())setStatus(`⚠️ 即時資料日期落後｜5分K結構 ${label}`,'bad');
      else if(sessionNow())setStatus(`⚠️ 即時層未通過｜5分K結構 ${label}`,'bad');
      else setStatus(`非盤中｜5分K結構 ${label}`,'warn');
      const live=$('#liveStatus');if(live)live.style.display='none';
      document.querySelectorAll('.livequote').forEach(x=>x.remove());
    }finally{repairing=false}
  }

  function schedule(ms=0){clearTimeout(timer);timer=setTimeout(enforceRealtimeTruth,ms)}
  function boot(){
    enforceRealtimeTruth();
    window.addEventListener('dogson:data-truth',()=>schedule(10));
    window.addEventListener('dogson:actionability',()=>schedule(10));
    window.addEventListener('dogson:freshness',()=>schedule(10));
    document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav'))schedule(120)});
    const status=$('#status');if(status)new MutationObserver(()=>schedule(0)).observe(status,{subtree:true,childList:true,characterData:true});
    setInterval(()=>{if(!document.hidden)enforceRealtimeTruth()},3000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();