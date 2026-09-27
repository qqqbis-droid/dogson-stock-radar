(()=>{
  if(window.__DOGSON_STATUS_V1749__) return;
  window.__DOGSON_STATUS_V1749__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const shortDate=v=>{
    const m=String(v||'').match(/20\d{2}-(\d{2})-(\d{2})/);
    return m?`${Number(m[1])}/${Number(m[2])}`:'';
  };

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

  function activeView(){
    const v=$('#dogsonViewNav .dogson-view-main > button.active[data-v]')?.dataset?.v||'';
    if(v==='close') return 'close';
    if(v==='portfolio') return 'portfolio';
    if(v==='daytrade') return 'daytrade';
    return 'intraday';
  }

  function datePool(){
    const snap=window.DOGSON_DATA_TRUTH_V1700||{};
    const d=snap.dates||{};
    return {
      latest:snap.latest||'',
      market:d.market||'',
      close:d.close||window.DOGSON_CLOSE_TRADE_DATE||'',
      intraday:d.intraday||window.DOGSON_INTRADAY_TRADE_DATE||'',
      daytrade:d.daytrade||window.DOGSON_DAYTRADE_TRADE_DATE||''
    };
  }

  function quality(){
    const snap=window.DOGSON_DATA_TRUTH_V1700||{};
    return snap.operational?.quality||snap.system?.operational?.intraday_quality||{};
  }

  function statusSpec(){
    const view=activeView();
    const dates=datePool();
    const q=quality();
    const clock=taipeiClock();
    const live=window.DOGSON_INTRADAY_LIVE_READY===true;
    const dayActionable=window.DOGSON_DAYTRADE_ACTIONABLE===true;
    const quote=q.latest_quote_time||'';
    const structure=q.structure_latest_time||'';

    if(view==='close'){
      const d=shortDate(dates.close||dates.market||dates.latest);
      return {align:'center',alert:false,lines:[`${d||'—'} 盤後`,'完整資料']};
    }

    if(view==='portfolio'){
      const d=shortDate(dates.close||dates.market||dates.latest);
      return {align:'center',alert:false,lines:[`${d||'—'} 庫存`,'盤後結構']};
    }

    if(view==='daytrade'){
      if(dayActionable){
        const d=shortDate(dates.daytrade||dates.intraday||dates.latest||clock.today);
        return {align:'left',alert:false,lines:[`${d||'—'} MIS${quote?` ${quote}`:''}`,`5分K${structure?` ${structure}`:''}`]};
      }
      const d=shortDate(dates.daytrade||dates.intraday||dates.close||dates.latest);
      return {align:'center',alert:clock.session,lines:[`${d||'—'} 歷史`,'當沖停用']};
    }

    if(live){
      const d=shortDate(dates.intraday||dates.latest||clock.today);
      return {align:'left',alert:false,lines:[`${d||'—'} MIS${quote?` ${quote}`:''}`,`5分K${structure?` ${structure}`:''}`]};
    }

    const d=shortDate(dates.close||dates.market||dates.latest);
    return {align:'center',alert:clock.session,lines:[`${d||'—'} 盤後`,'完整資料']};
  }

  function installStyle(){
    if($('#dogson-status-style-v1749')) return;
    const s=document.createElement('style');
    s.id='dogson-status-style-v1749';
    s.textContent=`
      #dogsonAccuracyGuardV1702,
      #dogsonStableNoticeV1745,
      #dogsonDataTruthV1700{
        display:none!important;
        visibility:hidden!important;
        height:0!important;
        min-height:0!important;
        max-height:0!important;
        margin:0!important;
        padding:0!important;
        border:0!important;
        overflow:hidden!important;
      }

      .wrap>header #status.dogson-status-owner-v1749{
        height:58px!important;
        min-height:58px!important;
        max-height:58px!important;
        width:122px!important;
        min-width:122px!important;
        box-sizing:border-box!important;
        margin:0!important;
        padding:8px 10px!important;
        border-radius:14px!important;
        display:flex!important;
        flex-direction:column!important;
        justify-content:center!important;
        gap:3px!important;
        font-size:10.5px!important;
        font-weight:850!important;
        line-height:1.25!important;
        letter-spacing:0!important;
        overflow:hidden!important;
      }
      .wrap>header #status.dogson-status-owner-v1749 .dogson-status-line{
        display:block!important;
        width:100%!important;
        white-space:nowrap!important;
        overflow:hidden!important;
        text-overflow:clip!important;
      }
      .wrap>header #status.dogson-status-owner-v1749.dogson-status-left-v1749{
        align-items:flex-start!important;
        text-align:left!important;
      }
      .wrap>header #status.dogson-status-owner-v1749.dogson-status-center-v1749{
        align-items:center!important;
        text-align:center!important;
      }
      .wrap>header #status.dogson-status-alert-v1749{
        background:#fff8e8!important;
        border-color:#ead9a9!important;
        color:#6f5718!important;
      }

      #dogsonMissionV1700{
        margin:14px 2px 8px!important;
        padding:0!important;
        border:0!important;
        border-radius:0!important;
        background:transparent!important;
        box-shadow:none!important;
      }
      #dogsonMissionV1700 .dogson-mission-title-v1700{
        font-size:15px!important;
        font-weight:950!important;
        color:#25312c!important;
      }
      #dogsonMissionV1700 .dogson-mission-text-v1700{
        margin-top:3px!important;
        font-size:10.5px!important;
        line-height:1.5!important;
        color:#7a8580!important;
      }

      html[data-dogson-theme="dark"] .wrap>header #status.dogson-status-alert-v1749{
        background:#332c1b!important;
        border-color:#5a4b25!important;
        color:#f0d98e!important;
      }
      html[data-dogson-theme="dark"] #dogsonMissionV1700 .dogson-mission-title-v1700{color:#eef2ef!important}
      html[data-dogson-theme="dark"] #dogsonMissionV1700 .dogson-mission-text-v1700{color:#9da8a2!important}

      @media(max-width:720px){
        .wrap>header #status.dogson-status-owner-v1749{
          height:56px!important;
          min-height:56px!important;
          max-height:56px!important;
          width:116px!important;
          min-width:116px!important;
          padding:7px 9px!important;
          font-size:10px!important;
        }
      }
      @media(max-width:360px){
        .wrap>header #status.dogson-status-owner-v1749{
          width:110px!important;
          min-width:110px!important;
          padding-left:7px!important;
          padding-right:7px!important;
          font-size:9.5px!important;
        }
      }
    `;
    document.head.appendChild(s);
  }

  function hideLegacy(){
    const guard=$('#dogsonAccuracyGuardV1702');
    if(guard){
      guard.style.setProperty('display','none','important');
      guard.setAttribute('aria-hidden','true');
    }
    const stable=$('#dogsonStableNoticeV1745');
    if(stable){
      stable.style.setProperty('display','none','important');
      stable.setAttribute('aria-hidden','true');
    }
    const truth=$('#dogsonDataTruthV1700');
    if(truth) truth.setAttribute('aria-hidden','true');
  }

  function renderStatus(){
    const status=$('#status');
    if(!status) return;
    const x=statusSpec();
    const fingerprint=`${x.align}|${x.alert?'1':'0'}|${x.lines.join('|')}`;

    status.dataset.dogsonHeaderOwner='1749';
    status.dataset.dogsonStatusRaw=x.lines.join('｜');
    status.dataset.dogsonStatusDisplay=x.lines.join('｜');
    status.classList.add('dogson-status-owner-v1749');
    status.classList.toggle('dogson-status-left-v1749',x.align==='left');
    status.classList.toggle('dogson-status-center-v1749',x.align!=='left');
    status.classList.toggle('dogson-status-alert-v1749',!!x.alert);

    if(status.dataset.dogsonStatus1749!==fingerprint){
      status.innerHTML='';
      x.lines.forEach(line=>{
        const span=document.createElement('span');
        span.className='dogson-status-line';
        span.textContent=line;
        status.appendChild(span);
      });
      status.dataset.dogsonStatus1749=fingerprint;
    }
  }

  function renderMission(){
    const box=$('#dogsonMissionV1700');
    if(!box) return;
    const title=$('.dogson-mission-title-v1700',box);
    const text=$('.dogson-mission-text-v1700',box);
    if(!title||!text) return;

    const view=activeView();
    let t='🔎 找波段',x='盤中找正在轉強、適合波段觀察的股票。';
    if(view==='close'){
      t='🌙 盤後作戰';
      x='收盤後找值得明天繼續觀察的波段候選。';
    }else if(view==='portfolio'){
      t='💼 我的庫存';
      x='先看持股結構與風險，再決定續抱、減碼或加碼。';
    }else if(view==='daytrade'){
      t='🎯 當沖執行';
      x='只看通過即時品質門檻、盤中可執行的候選。';
    }
    if(title.textContent!==t) title.textContent=t;
    if(text.textContent!==x) text.textContent=x;
  }

  function apply(){
    installStyle();
    hideLegacy();
    renderStatus();
    renderMission();
  }

  function boot(){
    apply();
    window.addEventListener('dogson:data-truth',()=>setTimeout(apply,20));
    window.addEventListener('dogson:actionability',()=>setTimeout(apply,20));
    window.addEventListener('dogson:freshness',()=>setTimeout(apply,20));
    document.addEventListener('click',e=>{
      if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly')){
        setTimeout(apply,0);
        setTimeout(apply,60);
        setTimeout(apply,180);
      }
    },true);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(apply,30)});
    setTimeout(apply,250);
    setTimeout(apply,900);
    setInterval(()=>{if(!document.hidden)apply()},30000);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();
