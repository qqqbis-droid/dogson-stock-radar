(()=>{
  if(window.__DOGSON_ACCURACY_GUARD_V1710__) return;
  window.__DOGSON_ACCURACY_GUARD_V1710__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const modeNow=()=>{try{return mode||'intraday'}catch{return'intraday'}};
  const portfolioView=()=>{try{return !!portfolioOnly}catch{return false}};
  const staleIntra=()=>window.DOGSON_INTRADAY_STALE===true;
  const staleDay=()=>window.DOGSON_DAYTRADE_STALE===true||staleIntra();

  let legacyRender=null;
  let wrapping=false;

  function dates(){return{close:window.DOGSON_CLOSE_TRADE_DATE||window.DOGSON_DATA_TRUTH_V1700?.dates?.close||'',intraday:window.DOGSON_INTRADAY_TRADE_DATE||window.DOGSON_DATA_TRUTH_V1700?.dates?.intraday||'',daytrade:window.DOGSON_DAYTRADE_TRADE_DATE||window.DOGSON_DATA_TRUTH_V1700?.dates?.daytrade||''}}

  function installStyle(){
    if($('#dogsonAccuracyGuardStyle1702'))return;
    const s=document.createElement('style');s.id='dogsonAccuracyGuardStyle1702';s.textContent=`
      .dogson-accuracy-v1702{margin:8px 0 10px;padding:11px 12px;border-radius:14px;border:1px solid #ead9a9;background:#fff8e8;color:#6f5718}.dogson-accuracy-v1702.bad{border-color:#efc5ca;background:#fff0f2;color:#8e303a}.dogson-accuracy-v1702.good{border-color:#cfe4d6;background:#f0f8f3;color:#2d6748}.dogson-accuracy-title-v1702{font-size:12px;font-weight:950}.dogson-accuracy-text-v1702{font-size:10px;line-height:1.6;margin-top:4px}.dogson-accuracy-date-v1702{font-weight:900}html[data-dogson-theme="dark"] .dogson-accuracy-v1702{background:#332c1b;border-color:#5a4b25;color:#f0d98e}html[data-dogson-theme="dark"] .dogson-accuracy-v1702.bad{background:#352126;border-color:#63343b;color:#ffb8c0}html[data-dogson-theme="dark"] .dogson-accuracy-v1702.good{background:#1c3025;border-color:#315640;color:#a7e1bd}
      html[data-dogson-stale-intraday="1"][data-dogson-page="intraday"] #changebox,html[data-dogson-stale-intraday="1"][data-dogson-page="intraday"] #dogsonFlowHomeV1685,html[data-dogson-stale-daytrade="1"][data-dogson-page="daytrade"] #changebox,html[data-dogson-stale-daytrade="1"][data-dogson-page="daytrade"] #dogsonFlowHomeV1685{display:none!important}
    `;document.head.appendChild(s);
  }

  function noticeSpec(){
    const m=modeNow(),d=dates();
    if(m==='daytrade'&&staleDay())return{tone:'bad',title:'🎯 當沖舊資料已停用',text:`當沖行情 ${d.daytrade||d.intraday||'—'} 舊於最近完整交易日 ${d.close||'—'}，或與盤中來源日期不一致。系統不顯示舊的「可執行」訊號，等下一個實際交易時段重新建立。`};
    if(m==='intraday'&&!portfolioView()&&staleIntra())return{tone:'',title:'🛡️ 找波段已啟用資料保護',text:`盤中資料 ${d.intraday||'—'} 舊於最近完整交易日 ${d.close||'—'}。個股卡片改用 ${d.close||'最近交易日'} 盤後波段資料；5分鐘變化、盤中資金輪動與即時進場判斷暫停，避免把舊盤中訊號當成最新。`};
    if(m==='intraday'&&portfolioView()&&staleIntra())return{tone:'',title:'🛡️ 庫存已改用最近完整資料',text:`盤中資料 ${d.intraday||'—'} 較舊，庫存判讀改用 ${d.close||'最近交易日'} 盤後結構；不使用舊盤中轉強／轉弱訊號。`};
    return null;
  }

  function renderNotice(){
    installStyle();
    document.documentElement.dataset.dogsonStaleIntraday=staleIntra()?'1':'0';
    document.documentElement.dataset.dogsonStaleDaytrade=staleDay()?'1':'0';
    const anchor=$('#dogsonDataTruthV1700')||$('#dogsonMissionV1700')||$('#dogsonViewNav');if(!anchor)return;
    let box=$('#dogsonAccuracyGuardV1702');const x=noticeSpec();if(!x){box?.remove();return}
    if(!box){box=document.createElement('section');box.id='dogsonAccuracyGuardV1702';anchor.after(box)}
    box.className=`dogson-accuracy-v1702 ${x.tone||''}`;box.innerHTML=`<div class="dogson-accuracy-title-v1702">${esc(x.title)}</div><div class="dogson-accuracy-text-v1702">${esc(x.text)}</div>`;
  }

  function withAccurateRows(fn){
    const m=modeNow();
    if(m==='intraday'&&staleIntra()){
      let savedRows,savedMarket,savedChange,savedRotation;
      try{savedRows=intraRows;savedMarket=intraMarket;savedChange=changeRadar;savedRotation=sectorRotation;intraRows=Array.isArray(closeRows)?closeRows:[];intraMarket=(typeof closeMarket!=='undefined'&&closeMarket)||savedMarket;changeRadar={ready:false,counts:{},today:{},events:[],_disabled_reason:'stale_intraday'};sectorRotation=[];window.DOGSON_EFFECTIVE_STOCK_SOURCE='close';return fn()}catch(e){return fn()}finally{try{intraRows=savedRows;intraMarket=savedMarket;changeRadar=savedChange;sectorRotation=savedRotation}catch(_){ }}
    }
    if(m==='daytrade'&&staleDay()){
      let savedRows,savedMarket;
      try{savedRows=daytradeRows;savedMarket=daytradeMarket;daytradeRows=[];daytradeMarket=(typeof closeMarket!=='undefined'&&closeMarket)||savedMarket;window.DOGSON_EFFECTIVE_STOCK_SOURCE='disabled_stale_daytrade';return fn()}catch(e){return fn()}finally{try{daytradeRows=savedRows;daytradeMarket=savedMarket}catch(_){ }}
    }
    return fn();
  }

  function wrapRender(){if(typeof render!=='function')return false;if(render.__dogsonAccuracyV1710)return true;legacyRender=render;const wrapped=function(...args){if(wrapping)return legacyRender.apply(this,args);wrapping=true;try{return withAccurateRows(()=>legacyRender.apply(this,args))}finally{wrapping=false;setTimeout(renderNotice,0)}};wrapped.__dogsonAccuracyV1710=true;render=wrapped;return true}
  function refresh(){renderNotice();if(wrapRender())try{render()}catch(_){ }}
  function boot(){installStyle();let n=0;const t=setInterval(()=>{n++;if(wrapRender()||n>100){clearInterval(t);refresh()}},40);window.addEventListener('dogson:freshness',()=>setTimeout(refresh,20));window.addEventListener('dogson:data-truth',()=>setTimeout(refresh,20));document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav,#portfolioOnly'))setTimeout(refresh,80)});document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(refresh,50)});setTimeout(refresh,400);setTimeout(refresh,1200)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
