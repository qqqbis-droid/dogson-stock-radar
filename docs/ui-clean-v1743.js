(()=>{
  if(window.__DOGSON_CLEAN_V1743__) return;
  window.__DOGSON_CLEAN_V1743__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const shortDate=v=>{
    const m=String(v||'').match(/20\d{2}-(\d{2})-(\d{2})/);
    return m?`${Number(m[1])}/${Number(m[2])}`:'';
  };
  const modeNow=()=>{try{return mode||'intraday'}catch{return document.documentElement.dataset.dogsonPage||'intraday'}};
  const portfolioView=()=>{try{return !!portfolioOnly}catch{return document.documentElement.dataset.dogsonPage==='portfolio'}};

  function installStyle(){
    if($('#dogson-clean-style-v1743')) return;
    const s=document.createElement('style');
    s.id='dogson-clean-style-v1743';
    s.textContent=`
      .wrap>header.dogson-clean-header-v1743{
        display:grid!important;
        grid-template-columns:minmax(0,1fr) 122px!important;
        column-gap:10px!important;
        align-items:stretch!important;
        margin:4px 2px 10px!important;
      }
      .wrap>header.dogson-clean-header-v1743>div:first-child{
        min-width:0!important;
        display:flex!important;
        flex-direction:column!important;
        justify-content:center!important;
      }
      .wrap>header.dogson-clean-header-v1743 h1{
        margin:0!important;
        white-space:nowrap!important;
        overflow:visible!important;
        text-overflow:clip!important;
        line-height:1.18!important;
      }
      .wrap>header.dogson-clean-header-v1743 .sub{
        margin-top:4px!important;
        white-space:nowrap!important;
        overflow:hidden!important;
        text-overflow:ellipsis!important;
      }
      .wrap>header.dogson-clean-header-v1743 #status.dogson-clean-status-v1743{
        width:122px!important;
        min-width:122px!important;
        min-height:58px!important;
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
        white-space:normal!important;
      }
      .wrap>header.dogson-clean-header-v1743 #status.dogson-clean-status-left{
        align-items:flex-start!important;
        text-align:left!important;
      }
      .wrap>header.dogson-clean-header-v1743 #status.dogson-clean-status-center{
        align-items:center!important;
        text-align:center!important;
      }
      .wrap>header.dogson-clean-header-v1743 #status .dogson-clean-status-line{
        display:block!important;
        width:100%!important;
        white-space:nowrap!important;
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
      #dogsonDataTruthV1700{display:none!important}

      #dogsonAccuracyGuardV1702.dogson-clean-notice-v1743{
        margin:4px 0 10px!important;
        padding:7px 10px!important;
        min-height:0!important;
        border-radius:10px!important;
        box-shadow:none!important;
        line-height:1.45!important;
      }
      #dogsonAccuracyGuardV1702.dogson-clean-notice-v1743 .dogson-accuracy-title-v1702{
        display:inline!important;
        font-size:10.5px!important;
        font-weight:950!important;
      }
      #dogsonAccuracyGuardV1702.dogson-clean-notice-v1743 .dogson-accuracy-text-v1702{
        display:inline!important;
        margin:0!important;
        font-size:10px!important;
        line-height:1.45!important;
      }
      html[data-dogson-theme="dark"] #dogsonMissionV1700 .dogson-mission-title-v1700{color:#eef2ef!important}
      html[data-dogson-theme="dark"] #dogsonMissionV1700 .dogson-mission-text-v1700{color:#9da8a2!important}

      @media(max-width:720px){
        .wrap>header.dogson-clean-header-v1743{
          grid-template-columns:minmax(0,1fr) 116px!important;
          column-gap:8px!important;
        }
        .wrap>header.dogson-clean-header-v1743 #status.dogson-clean-status-v1743{
          width:116px!important;
          min-width:116px!important;
          min-height:56px!important;
          padding:7px 9px!important;
          font-size:10px!important;
        }
      }
      @media(max-width:360px){
        .wrap>header.dogson-clean-header-v1743{
          grid-template-columns:minmax(0,1fr) 110px!important;
          column-gap:6px!important;
        }
        .wrap>header.dogson-clean-header-v1743 #status.dogson-clean-status-v1743{
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

  function dataSpec(){
    const snap=window.DOGSON_DATA_TRUTH_V1700;
    if(!snap) return null;
    const dates=snap.dates||{};
    const q=snap.operational?.quality||snap.system?.operational?.intraday_quality||{};
    const live=window.DOGSON_INTRADAY_LIVE_READY===true||snap.operational?.liveReady===true;
    const actionable=window.DOGSON_DAYTRADE_ACTIONABLE===true||snap.operational?.dayActionable===true;
    const m=modeNow();
    const p=portfolioView();
    const quote=q.latest_quote_time||'';
    const structure=q.structure_latest_time||'';

    if(m==='close'){
      const d=shortDate(dates.close||dates.market||snap.latest);
      return {align:'center',lines:[`${d||'—'} 盤後`,'完整資料']};
    }
    if(m==='daytrade'){
      if(actionable){
        const d=shortDate(dates.daytrade||dates.intraday||snap.latest);
        return {align:'left',lines:[`${d||'—'} MIS${quote?` ${quote}`:''}`,`5分K${structure?` ${structure}`:''}`]};
      }
      const d=shortDate(dates.daytrade||dates.intraday||dates.close||snap.latest);
      return {align:'center',lines:[`${d||'—'} 歷史`,'當沖停用']};
    }
    if(live){
      const d=shortDate(dates.intraday||snap.latest);
      return {align:'left',lines:[`${d||'—'} MIS${quote?` ${quote}`:''}`,`5分K${structure?` ${structure}`:''}`]};
    }
    const d=shortDate(dates.close||dates.market||snap.latest);
    return {align:'center',lines:[`${d||'—'} 盤後`,'完整資料']};
  }

  function cleanHeader(){
    const header=$('.wrap>header');
    const status=$('#status');
    if(!header||!status) return;
    header.classList.add('dogson-clean-header-v1743');
    status.classList.add('dogson-clean-status-v1743');
    const spec=dataSpec();
    if(!spec) return;
    const fingerprint=`${spec.align}|${spec.lines.join('|')}`;
    if(status.dataset.dogsonClean1743!==fingerprint){
      status.innerHTML='';
      spec.lines.forEach(line=>{
        const span=document.createElement('span');
        span.className='dogson-clean-status-line';
        span.textContent=line;
        status.appendChild(span);
      });
      status.dataset.dogsonClean1743=fingerprint;
    }
    status.classList.toggle('dogson-clean-status-left',spec.align==='left');
    status.classList.toggle('dogson-clean-status-center',spec.align!=='left');
  }

  function cleanMission(){
    const box=$('#dogsonMissionV1700');
    if(!box) return;
    const title=$('.dogson-mission-title-v1700',box);
    const text=$('.dogson-mission-text-v1700',box);
    const m=modeNow(),p=portfolioView();
    let t='🔎 找波段',x='盤中找正在轉強、適合波段觀察的股票。';
    if(p){t='💼 我的庫存';x='先看持股結構與風險，再決定續抱、減碼或加碼。'}
    else if(m==='close'){t='🌙 盤後作戰';x='收盤後找值得明天繼續觀察的波段候選。'}
    else if(m==='daytrade'){t='🎯 當沖執行';x='只看通過即時品質門檻、盤中可執行的候選。'}
    if(title&&title.textContent!==t) title.textContent=t;
    if(text&&text.textContent!==x) text.textContent=x;
  }

  function cleanTruth(){
    const truth=$('#dogsonDataTruthV1700');
    if(truth) truth.setAttribute('aria-hidden','true');
  }

  function cleanNotice(){
    const box=$('#dogsonAccuracyGuardV1702');
    if(!box) return;
    const title=$('.dogson-accuracy-title-v1702',box);
    const text=$('.dogson-accuracy-text-v1702',box);
    if(!title||!text) return;
    const snap=window.DOGSON_DATA_TRUTH_V1700;
    const dates=snap?.dates||{};
    const m=modeNow(),p=portfolioView();
    const live=window.DOGSON_INTRADAY_LIVE_READY===true||snap?.operational?.liveReady===true;
    const actionable=window.DOGSON_DAYTRADE_ACTIONABLE===true||snap?.operational?.dayActionable===true;
    let t=title.textContent||'',x=text.textContent||'';

    if(m==='intraday'&&!p&&!live){
      const d=shortDate(dates.close||dates.market||snap?.latest);
      t='🛡 非即時盤中';
      x=`｜候選股使用 ${d||'最近交易日'} 完整盤後資料`;
    }else if(m==='intraday'&&p&&!live){
      const d=shortDate(dates.close||dates.market||snap?.latest);
      t='🛡 非即時庫存';
      x=`｜使用 ${d||'最近交易日'} 完整盤後結構`;
    }else if(m==='daytrade'&&!actionable){
      t='🎯 當沖目前不可執行';
      x='｜即時條件未通過，歷史資料僅供回顧';
    }
    box.classList.add('dogson-clean-notice-v1743');
    if(title.textContent!==t) title.textContent=t;
    if(text.textContent!==x) text.textContent=x;
  }

  let timer=null;
  function apply(){
    installStyle();
    cleanHeader();
    cleanMission();
    cleanTruth();
    cleanNotice();
  }
  function schedule(){clearTimeout(timer);timer=setTimeout(apply,25)}

  function boot(){
    apply();
    const root=$('.wrap')||document.body;
    if(root)new MutationObserver(schedule).observe(root,{childList:true,subtree:true,characterData:true});
    window.addEventListener('dogson:data-truth',()=>setTimeout(apply,20));
    window.addEventListener('dogson:actionability',()=>setTimeout(apply,20));
    window.addEventListener('dogson:freshness',()=>setTimeout(apply,20));
    document.addEventListener('click',e=>{if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly'))setTimeout(apply,50)});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(apply,30)});
    setTimeout(apply,300);
    setTimeout(apply,1000);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
