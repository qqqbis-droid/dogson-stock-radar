(()=>{
  if(window.__DOGSON_ACCURACY_GUARD_V1720__) return;
  window.__DOGSON_ACCURACY_GUARD_V1720__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));
  const modeNow=()=>{try{return mode||'intraday'}catch{return'intraday'}};
  const portfolioView=()=>{try{return !!portfolioOnly}catch{return false}};
  const staleIntra=()=>window.DOGSON_INTRADAY_STALE===true;
  const staleDay=()=>window.DOGSON_DAYTRADE_STALE===true||staleIntra();

  let legacyRender=null;
  let wrapping=false;

  function taipeiClock(){
    try{
      const p={};new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).forEach(x=>{if(x.type!=='literal')p[x.type]=x.value});
      const today=`${p.year}-${p.month}-${p.day}`;const minute=Number(p.hour)*60+Number(p.minute);const weekday=['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday);return{today,session:weekday&&minute>=535&&minute<=815};
    }catch{return{today:'',session:false}}
  }
  function dates(){return{close:window.DOGSON_CLOSE_TRADE_DATE||window.DOGSON_DATA_TRUTH_V1700?.dates?.close||'',intraday:window.DOGSON_INTRADAY_TRADE_DATE||window.DOGSON_DATA_TRUTH_V1700?.dates?.intraday||'',daytrade:window.DOGSON_DAYTRADE_TRADE_DATE||window.DOGSON_DATA_TRUTH_V1700?.dates?.daytrade||''}}
  function quality(){return window.DOGSON_DATA_TRUTH_V1700?.system?.operational?.intraday_quality||{}}
  function liveReady(){
    if(window.DOGSON_INTRADAY_LIVE_READY===true)return true;
    const c=taipeiClock(),d=dates(),q=quality();return !!(c.session&&d.intraday===c.today&&!staleIntra()&&Number(q.quote_coverage_pct||0)>=Number(q.coverage_min_pct||80)&&q.latest_quote_time);
  }
  function dayActionable(){
    if(window.DOGSON_DAYTRADE_ACTIONABLE===true)return true;
    const c=taipeiClock(),d=dates();return !!(liveReady()&&c.session&&d.daytrade===c.today&&!staleDay());
  }

  function installStyle(){
    if($('#dogsonAccuracyGuardStyle1702'))return;
    const s=document.createElement('style');s.id='dogsonAccuracyGuardStyle1702';s.textContent=`
      .dogson-accuracy-v1702{margin:8px 0 10px;padding:11px 12px;border-radius:14px;border:1px solid #ead9a9;background:#fff8e8;color:#6f5718}.dogson-accuracy-v1702.bad{border-color:#efc5ca;background:#fff0f2;color:#8e303a}.dogson-accuracy-v1702.good{border-color:#cfe4d6;background:#f0f8f3;color:#2d6748}.dogson-accuracy-title-v1702{font-size:12px;font-weight:950}.dogson-accuracy-text-v1702{font-size:10px;line-height:1.6;margin-top:4px}html[data-dogson-theme="dark"] .dogson-accuracy-v1702{background:#332c1b;border-color:#5a4b25;color:#f0d98e}html[data-dogson-theme="dark"] .dogson-accuracy-v1702.bad{background:#352126;border-color:#63343b;color:#ffb8c0}
      html[data-dogson-live-intraday="0"][data-dogson-page="intraday"] #changebox,html[data-dogson-live-intraday="0"][data-dogson-page="intraday"] #dogsonFlowHomeV1685,html[data-dogson-daytrade-actionable="0"][data-dogson-page="daytrade"] #changebox,html[data-dogson-daytrade-actionable="0"][data-dogson-page="daytrade"] #dogsonFlowHomeV1685{display:none!important}
    `;document.head.appendChild(s);
  }

  function reason(){const c=taipeiClock(),q=quality();if(staleIntra())return'盤中行情日期落後最近完整交易日';if(!c.session)return'目前不是台股現貨盤中時段';if(Number(q.quote_coverage_pct||0)<Number(q.coverage_min_pct||80))return`TWSE MIS 個股覆蓋 ${Number(q.quote_coverage_pct||0).toFixed(1)}%，未達 ${Number(q.coverage_min_pct||80).toFixed(0)}% 安全門檻`;if(!q.latest_quote_time)return'TWSE MIS 尚未提供可驗證的最新快照時間';return'盤中即時層尚未通過完整性檢查'}
  function noticeSpec(){
    const m=modeNow(),d=dates(),why=reason();
    if(m==='daytrade'&&!dayActionable())return{tone:staleDay()?'bad':'',title:staleDay()?'🎯 當沖舊資料已停用':'🎯 當沖目前不可執行',text:`${why}。系統不顯示「可執行／等回踩」清單；最近行情日 ${d.daytrade||d.intraday||'—'} 僅保留作歷史回顧，下一個合格盤中時段才重新啟用。`};
    if(m==='intraday'&&!portfolioView()&&!liveReady())return{tone:'',title:'🛡️ 找波段使用最近完整盤後資料',text:`${why}。個股卡片改用 ${d.close||'最近完整交易日'} 的盤後波段資料；5分鐘變化、盤中資金輪動與即時進場判斷暫停。`};
    if(m==='intraday'&&portfolioView()&&!liveReady())return{tone:'',title:'🛡️ 庫存使用最近完整資料',text:`${why}。庫存判讀改用 ${d.close||'最近完整交易日'} 盤後結構，不把非即時盤中轉折當成現在訊號。`};
    return null;
  }

  function renderNotice(){
    installStyle();const lr=liveReady(),da=dayActionable();window.DOGSON_INTRADAY_LIVE_READY=lr;window.DOGSON_DAYTRADE_ACTIONABLE=da;document.documentElement.dataset.dogsonLiveIntraday=lr?'1':'0';document.documentElement.dataset.dogsonDaytradeActionable=da?'1':'0';
    const anchor=$('#dogsonDataTruthV1700')||$('#dogsonMissionV1700')||$('#dogsonViewNav');if(!anchor)return;
    let box=$('#dogsonAccuracyGuardV1702');const x=noticeSpec();if(!x){box?.remove();return}if(!box){box=document.createElement('section');box.id='dogsonAccuracyGuardV1702';anchor.after(box)}box.className=`dogson-accuracy-v1702 ${x.tone||''}`;box.innerHTML=`<div class="dogson-accuracy-title-v1702">${esc(x.title)}</div><div class="dogson-accuracy-text-v1702">${esc(x.text)}</div>`;
    try{window.dispatchEvent(new CustomEvent('dogson:actionability',{detail:{intradayLiveReady:lr,daytradeActionable:da}}))}catch(_){ }
  }

  function withAccurateRows(fn){
    const m=modeNow();
    if(m==='intraday'&&!liveReady()){
      let savedRows,savedMarket,savedChange,savedRotation;try{savedRows=intraRows;savedMarket=intraMarket;savedChange=changeRadar;savedRotation=sectorRotation;intraRows=Array.isArray(closeRows)?closeRows:[];intraMarket=(typeof closeMarket!=='undefined'&&closeMarket)||savedMarket;changeRadar={ready:false,counts:{},today:{},events:[],_disabled_reason:'not_live'};sectorRotation=[];window.DOGSON_EFFECTIVE_STOCK_SOURCE='close';return fn()}catch(e){return fn()}finally{try{intraRows=savedRows;intraMarket=savedMarket;changeRadar=savedChange;sectorRotation=savedRotation}catch(_){ }}
    }
    if(m==='daytrade'&&!dayActionable()){
      let savedRows,savedMarket;try{savedRows=daytradeRows;savedMarket=daytradeMarket;daytradeRows=[];daytradeMarket=(typeof closeMarket!=='undefined'&&closeMarket)||savedMarket;window.DOGSON_EFFECTIVE_STOCK_SOURCE='disabled_not_actionable';return fn()}catch(e){return fn()}finally{try{daytradeRows=savedRows;daytradeMarket=savedMarket}catch(_){ }}
    }
    return fn();
  }

  function wrapRender(){if(typeof render!=='function')return false;if(render.__dogsonAccuracyV1720)return true;legacyRender=render;const wrapped=function(...args){if(wrapping)return legacyRender.apply(this,args);wrapping=true;try{return withAccurateRows(()=>legacyRender.apply(this,args))}finally{wrapping=false;setTimeout(renderNotice,0)}};wrapped.__dogsonAccuracyV1720=true;render=wrapped;return true}
  function refresh(){renderNotice();if(wrapRender())try{render()}catch(_){ }}
  function boot(){installStyle();let n=0;const t=setInterval(()=>{n++;if(wrapRender()||n>100){clearInterval(t);refresh()}},40);window.addEventListener('dogson:freshness',()=>setTimeout(refresh,20));window.addEventListener('dogson:data-truth',()=>setTimeout(refresh,20));document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav,#portfolioOnly'))setTimeout(refresh,80)});document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(refresh,50)});setInterval(()=>{if(!document.hidden)refresh()},60000);setTimeout(refresh,400);setTimeout(refresh,1200)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
