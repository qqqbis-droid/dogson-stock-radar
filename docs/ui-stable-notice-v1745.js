(()=>{
  if(window.__DOGSON_HEADER_ONLY_STATUS_V1747__) return;
  window.__DOGSON_HEADER_ONLY_STATUS_V1747__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const shortDate=v=>{
    const m=String(v||'').match(/20\d{2}-(\d{2})-(\d{2})/);
    return m?`${Number(m[1])}/${Number(m[2])}`:'';
  };
  const modeNow=()=>{try{return mode||'intraday'}catch{return document.documentElement.dataset.dogsonPage||'intraday'}};
  let systemCache=null;

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
    if($('#dogson-header-only-status-style-v1747')) return;
    $('#dogson-header-only-status-style-v1746')?.remove();
    const s=document.createElement('style');
    s.id='dogson-header-only-status-style-v1747';
    s.textContent=`
      #dogsonAccuracyGuardV1702,
      #dogsonStableNoticeV1745{display:none!important;}

      .wrap>header #status.dogson-status-owner-v1747{
        display:flex!important;
        flex-direction:column!important;
        justify-content:center!important;
        gap:2px!important;
      }
      .wrap>header #status.dogson-status-owner-v1747 .dogson-status-line{
        display:block!important;
        width:100%!important;
        white-space:nowrap!important;
        overflow:hidden!important;
        text-overflow:clip!important;
      }
      .wrap>header #status.dogson-status-owner-v1747.dogson-status-live-v1747{
        align-items:flex-start!important;
        text-align:left!important;
      }
      .wrap>header #status.dogson-status-owner-v1747.dogson-status-close-v1747{
        align-items:center!important;
        text-align:center!important;
      }
      .wrap>header #status.dogson-status-alert-v1747{
        background:#fff8e8!important;
        border-color:#ead9a9!important;
        color:#6f5718!important;
      }
      html[data-dogson-theme="dark"] .wrap>header #status.dogson-status-alert-v1747{
        background:#332c1b!important;
        border-color:#5a4b25!important;
        color:#f0d98e!important;
      }
    `;
    document.head.appendChild(s);
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
    if(!status) return;
    const x=spec();
    const raw=x.lines.join('｜');

    status.classList.add('dogson-status-owner-v1747');
    status.classList.toggle('dogson-status-live-v1747',x.kind==='live');
    status.classList.toggle('dogson-status-close-v1747',x.kind!=='live');
    status.classList.toggle('dogson-status-alert-v1747',!!x.abnormal);
    status.classList.remove('dogson-status-alert-v1746');

    // Feed the legacy formatter the SAME dated value so it cannot revert the
    // badge to the old undated MIS/5m text when its observer fires.
    status.dataset.dogsonStatusRaw=raw;
    status.dataset.dogsonStatusDisplay=raw;
    status.dataset.dogsonHeaderOwner='1747';

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
  }

  function sync(){
    installStyle();
    $('#dogsonStableNoticeV1745')?.remove();
    renderStatus();
  }

  function boot(){
    sync();
    loadSystemStatus();
    window.addEventListener('dogson:data-truth',()=>setTimeout(sync,30));
    window.addEventListener('dogson:actionability',()=>setTimeout(sync,30));
    window.addEventListener('dogson:freshness',()=>setTimeout(sync,30));
    document.addEventListener('click',e=>{if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly'))setTimeout(sync,70)});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden){setTimeout(sync,30);loadSystemStatus()}});
    setTimeout(sync,350);
    setTimeout(sync,1100);
    setInterval(()=>{if(!document.hidden)sync()},15000);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();
