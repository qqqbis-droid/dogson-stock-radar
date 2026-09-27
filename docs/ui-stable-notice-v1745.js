(()=>{
  if(window.__DOGSON_HEADER_ONLY_STATUS_V1748__) return;
  window.__DOGSON_HEADER_ONLY_STATUS_V1748__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const shortDate=v=>{
    const m=String(v||'').match(/20\d{2}-(\d{2})-(\d{2})/);
    return m?`${Number(m[1])}/${Number(m[2])}`:'';
  };
  const modeNow=()=>{try{return mode||'intraday'}catch{return document.documentElement.dataset.dogsonPage||'intraday'}};
  let systemCache=null;
  let rendering=false;

  function taipeiClock(){
    try{
      const p={};
      new Intl.DateTimeFormat('en-CA',{
        timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'
      }).formatToParts(new Date()).forEach(x=>{if(x.type!=='literal')p[x.type]=x.value});
      const minute=Number(p.hour)*60+Number(p.minute);
      const weekday=['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday);
      return {today:`${p.year}-${p.month}-${p.day}`,session:weekday&&minute>=535&&minute<=815};
    }catch{return {today:'',session:false}}
  }

  async function loadSystemStatus(){
    try{
      const r=await fetch(`./data/system_status.json?header=${Date.now()}`,{cache:'no-store'});
      if(!r.ok) return;
      systemCache=await r.json();
      sync();
    }catch(_){ }
  }

  function installStyle(){
    if($('#dogson-header-only-status-style-v1748')) return;
    $('#dogson-header-only-status-style-v1746')?.remove();
    $('#dogson-header-only-status-style-v1747')?.remove();
    const s=document.createElement('style');
    s.id='dogson-header-only-status-style-v1748';
    s.textContent=`
      #dogsonAccuracyGuardV1702,
      #dogsonStableNoticeV1745{display:none!important;visibility:hidden!important;height:0!important;min-height:0!important;max-height:0!important;margin:0!important;padding:0!important;border:0!important;overflow:hidden!important;}

      .wrap>header #status.dogson-status-owner-v1748{
        display:flex!important;
        flex-direction:column!important;
        justify-content:center!important;
        gap:2px!important;
      }
      .wrap>header #status.dogson-status-owner-v1748 .dogson-status-line{
        display:block!important;
        width:100%!important;
        white-space:nowrap!important;
        overflow:hidden!important;
        text-overflow:clip!important;
      }
      .wrap>header #status.dogson-status-owner-v1748.dogson-status-live-v1748{
        align-items:flex-start!important;
        text-align:left!important;
      }
      .wrap>header #status.dogson-status-owner-v1748.dogson-status-close-v1748{
        align-items:center!important;
        text-align:center!important;
      }
      .wrap>header #status.dogson-status-alert-v1748{
        background:#fff8e8!important;
        border-color:#ead9a9!important;
        color:#6f5718!important;
      }
      html[data-dogson-theme="dark"] .wrap>header #status.dogson-status-alert-v1748{
        background:#332c1b!important;
        border-color:#5a4b25!important;
        color:#f0d98e!important;
      }
    `;
    document.head.appendChild(s);
  }

  function hideLegacyNotice(){
    const guard=$('#dogsonAccuracyGuardV1702');
    if(guard){
      guard.style.setProperty('display','none','important');
      guard.style.setProperty('visibility','hidden','important');
      guard.style.setProperty('height','0','important');
      guard.style.setProperty('min-height','0','important');
      guard.style.setProperty('max-height','0','important');
      guard.style.setProperty('margin','0','important');
      guard.style.setProperty('padding','0','important');
      guard.setAttribute('aria-hidden','true');
    }
    const stable=$('#dogsonStableNoticeV1745');
    if(stable){
      stable.style.setProperty('display','none','important');
      stable.setAttribute('aria-hidden','true');
    }
  }

  function datePool(){
    const snap=window.DOGSON_DATA_TRUTH_V1700||{};
    const sd=systemCache?.dates||{};
    const d=snap.dates||{};
    return {
      latest:snap.latest||systemCache?.latest_completed_trade_date||'',
      market:d.market||sd.market||'',
      close:d.close||sd.close||'',
      intraday:d.intraday||sd.intraday||window.DOGSON_INTRADAY_TRADE_DATE||'',
      daytrade:d.daytrade||sd.daytrade||window.DOGSON_DAYTRADE_TRADE_DATE||''
    };
  }

  function quality(){
    const snap=window.DOGSON_DATA_TRUTH_V1700||{};
    return snap.operational?.quality||systemCache?.operational?.intraday_quality||{};
  }

  function spec(){
    const m=modeNow();
    const dates=datePool();
    const q=quality();
    const clock=taipeiClock();
    const live=window.DOGSON_INTRADAY_LIVE_READY===true;
    const dayActionable=window.DOGSON_DAYTRADE_ACTIONABLE===true;
    const quote=q.latest_quote_time||'';
    const structure=q.structure_latest_time||'';

    if(m==='close'){
      const d=shortDate(dates.close||dates.market||dates.latest);
      return {kind:'close',abnormal:false,lines:[`${d||'—'} 盤後`,'完整資料']};
    }

    if(m==='daytrade'){
      if(dayActionable){
        const d=shortDate(dates.daytrade||dates.intraday||dates.latest||clock.today);
        return {kind:'live',abnormal:false,lines:[`${d||'—'} MIS${quote?` ${quote}`:''}`,`5分K${structure?` ${structure}`:''}`]};
      }
      const d=shortDate(dates.daytrade||dates.intraday||dates.close||dates.latest);
      return {kind:'close',abnormal:clock.session,lines:[`${d||'—'} 歷史`,'當沖停用']};
    }

    if(live){
      const d=shortDate(dates.intraday||dates.latest||clock.today);
      return {kind:'live',abnormal:false,lines:[`${d||'—'} MIS${quote?` ${quote}`:''}`,`5分K${structure?` ${structure}`:''}`]};
    }

    const d=shortDate(dates.close||dates.market||dates.latest);
    return {kind:'close',abnormal:clock.session,lines:[`${d||'—'} 盤後`,'完整資料']};
  }

  function renderStatus(){
    const status=$('#status');
    if(!status||rendering) return;
    rendering=true;
    try{
      const x=spec();
      const raw=x.lines.join('｜');

      status.classList.remove('dogson-status-owner-v1747','dogson-status-live-v1747','dogson-status-close-v1747','dogson-status-alert-v1747','dogson-status-alert-v1746');
      status.classList.add('dogson-status-owner-v1748');
      status.classList.toggle('dogson-status-live-v1748',x.kind==='live');
      status.classList.toggle('dogson-status-close-v1748',x.kind!=='live');
      status.classList.toggle('dogson-status-alert-v1748',!!x.abnormal);

      // Keep the legacy formatter's raw cache dated as well. If another old
      // module changes #status, the observer below restores this authoritative value.
      status.dataset.dogsonStatusRaw=raw;
      status.dataset.dogsonStatusDisplay=raw;
      status.dataset.dogsonHeaderOwner='1748';

      const current=[...status.querySelectorAll(':scope > .dogson-status-line')].map(n=>n.textContent||'');
      if(current.length!==2||current[0]!==x.lines[0]||current[1]!==x.lines[1]){
        status.innerHTML='';
        x.lines.forEach(line=>{
          const span=document.createElement('span');
          span.className='dogson-status-line dogson-clean-status-line';
          span.textContent=line;
          status.appendChild(span);
        });
      }
    }finally{
      rendering=false;
    }
  }

  function sync(){
    installStyle();
    hideLegacyNotice();
    renderStatus();
  }

  function boot(){
    sync();
    loadSystemStatus();

    // Legacy safety/status modules may redraw after navigation or data refresh.
    // Observe those changes and immediately restore the single authoritative UI.
    const root=document.querySelector('.wrap')||document.body;
    if(root){
      new MutationObserver(()=>{
        if(rendering) return;
        hideLegacyNotice();
        renderStatus();
      }).observe(root,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['class','style']});
    }

    window.addEventListener('dogson:data-truth',()=>setTimeout(sync,0));
    window.addEventListener('dogson:actionability',()=>setTimeout(sync,0));
    window.addEventListener('dogson:freshness',()=>setTimeout(sync,0));
    document.addEventListener('click',e=>{
      if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly')){
        setTimeout(sync,0);
        setTimeout(sync,45);
        setTimeout(sync,120);
      }
    },true);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden){setTimeout(sync,0);loadSystemStatus()}});
    setTimeout(sync,250);
    setTimeout(sync,800);
    setInterval(()=>{if(!document.hidden)sync()},15000);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();
