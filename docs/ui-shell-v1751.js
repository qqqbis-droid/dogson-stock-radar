(()=>{
  if(window.__DOGSON_SHELL_V1751__) return;
  window.__DOGSON_SHELL_V1751__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const ymd=v=>{const m=String(v||'').match(/(20\d{2})-(\d{2})-(\d{2})/);return m?`${m[1]}-${m[2]}-${m[3]}`:''};
  const shortDate=v=>{const d=ymd(v);if(!d)return'';const [,m,day]=d.split('-');return `${Number(m)}/${Number(day)}`};
  const firstRowDate=rows=>{for(const r of (Array.isArray(rows)?rows.slice(0,30):[])){const d=ymd(r?.quote_date)||ymd(r?.trade_date)||ymd(r?.date);if(d)return d}return''};

  function installStyle(){
    if($('#dogson-shell-style-v1751')) return;
    const s=document.createElement('style');
    s.id='dogson-shell-style-v1751';
    s.textContent=`
      .wrap>header #status,#dogsonAccuracyGuardV1702,#dogsonStableNoticeV1745,#dogsonDataTruthV1700{display:none!important;visibility:hidden!important;height:0!important;min-height:0!important;max-height:0!important;margin:0!important;padding:0!important;border:0!important;overflow:hidden!important}
      .wrap>header{position:relative!important;display:block!important;min-height:58px!important;padding-right:132px!important;margin:4px 2px 10px!important}
      .wrap>header>div:first-child{min-width:0!important;display:flex!important;flex-direction:column!important;justify-content:center!important}
      .wrap>header h1{margin:0!important;white-space:nowrap!important;line-height:1.18!important}
      .wrap>header .sub{margin-top:4px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
      #dogsonHeaderStatusV1751{position:absolute!important;top:0!important;right:0!important;width:122px;height:58px;min-width:122px;box-sizing:border-box;margin:0!important;padding:8px 10px;border:1px solid #dfe6e1;border-radius:14px;background:#fff;color:#52665e;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:3px;font-size:10.5px;font-weight:850;line-height:1.25;overflow:hidden}
      #dogsonHeaderStatusV1751.alert{background:#fff8e8!important;border-color:#ead9a9!important;color:#6f5718!important}
      #dogsonHeaderStatusV1751 .line{display:block;width:100%;white-space:nowrap;overflow:hidden;text-overflow:clip}
      #dogsonViewNav{display:grid!important;grid-template-columns:minmax(0,1fr) 48px!important;gap:10px!important;align-items:center!important;padding:0!important;background:transparent!important;border:0!important;box-shadow:none!important;overflow:visible!important}
      #dogsonViewNav .dogson-view-main{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:4px!important;width:100%!important;padding:4px!important;margin:0!important;background:#eef2ef!important;border:1px solid #dfe6e1!important;border-radius:20px!important;overflow:hidden!important}
      #dogsonViewNav .dogson-view-main>button{appearance:none!important;-webkit-appearance:none!important;min-width:0!important;min-height:48px!important;margin:0!important;padding:0 6px!important;border:0!important;border-radius:16px!important;background:transparent!important;color:#56665f!important;box-shadow:none!important;font-size:14px!important;font-weight:800!important;line-height:1!important;white-space:nowrap!important}
      #dogsonViewNav .dogson-view-main>button.active{background:#2f7865!important;color:#fff!important;box-shadow:0 2px 8px rgba(34,86,71,.20)!important}
      #dogsonViewNav .dogson-theme-toggle{width:48px!important;height:56px!important;min-width:48px!important;margin:0!important;padding:0!important;display:grid!important;place-items:center!important;border:1px solid #dfe6e1!important;border-radius:18px!important;background:#fff!important;color:#52665e!important;font-size:20px!important}
      #dogsonMissionV1700{margin:14px 2px 8px!important;padding:0!important;border:0!important;border-radius:0!important;background:transparent!important;box-shadow:none!important}
      #dogsonMissionV1700 .dogson-mission-title-v1700{font-size:15px!important;font-weight:950!important;color:#25312c!important}
      #dogsonMissionV1700 .dogson-mission-text-v1700{margin-top:3px!important;font-size:10.5px!important;line-height:1.5!important;color:#7a8580!important}
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main{background:#252b28!important;border-color:#39423d!important}
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main>button{color:#aeb9b3!important}
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main>button.active{background:#3a806d!important;color:#fff!important}
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-theme-toggle{background:#252b28!important;border-color:#39423d!important;color:#e3ebe6!important}
      html[data-dogson-theme="dark"] #dogsonHeaderStatusV1751{background:#252b28;border-color:#39423d;color:#e3ebe6}
      html[data-dogson-theme="dark"] #dogsonHeaderStatusV1751.alert{background:#332c1b!important;border-color:#5a4b25!important;color:#f0d98e!important}
      html[data-dogson-theme="dark"] #dogsonMissionV1700 .dogson-mission-title-v1700{color:#eef2ef!important}
      html[data-dogson-theme="dark"] #dogsonMissionV1700 .dogson-mission-text-v1700{color:#9da8a2!important}
      @media(max-width:720px){.wrap>header{min-height:56px!important;padding-right:124px!important}#dogsonHeaderStatusV1751{width:116px;min-width:116px;height:56px;padding:7px 9px;font-size:10px}#dogsonViewNav{grid-template-columns:minmax(0,1fr) 46px!important;gap:8px!important}#dogsonViewNav .dogson-view-main>button{min-height:46px!important;padding:0 3px!important;font-size:13px!important}#dogsonViewNav .dogson-theme-toggle{width:46px!important;height:54px!important;min-width:46px!important;font-size:19px!important}}
      @media(max-width:360px){.wrap>header{padding-right:116px!important}#dogsonHeaderStatusV1751{width:110px;min-width:110px;padding-left:7px;padding-right:7px;font-size:9.5px}}
    `;
    document.head.appendChild(s);
  }

  function ensureStatusBox(){
    const header=$('.wrap>header');if(!header)return null;
    document.getElementById('dogsonHeaderStatusV1750')?.remove();
    let box=$('#dogsonHeaderStatusV1751');
    if(!box){box=document.createElement('div');box.id='dogsonHeaderStatusV1751';box.setAttribute('aria-label','資料狀態');header.appendChild(box)}
    return box;
  }

  function activeView(){
    const v=$('#dogsonViewNav .dogson-view-main > button.active[data-v]')?.dataset?.v||'';
    if(v==='close'||v==='portfolio'||v==='daytrade')return v;
    try{if(portfolioOnly)return'portfolio';if(mode==='close')return'close';if(mode==='daytrade')return'daytrade'}catch{}
    return'intraday';
  }

  function dates(){
    const snap=window.DOGSON_DATA_TRUTH_V1700||{};const d=snap.dates||{};
    let cm={},im={},dm={};try{cm=closeMarket||{};im=intraMarket||{};dm=daytradeMarket||{}}catch{}
    let cr=[],ir=[],dr=[];try{cr=closeRows||[];ir=intraRows||[];dr=daytradeRows||[]}catch{}
    const close=ymd(d.close)||ymd(window.DOGSON_CLOSE_TRADE_DATE)||ymd(cm.trade_date)||firstRowDate(cr);
    const market=ymd(d.market)||ymd(cm.trade_date)||close;
    const intraday=ymd(d.intraday)||ymd(window.DOGSON_INTRADAY_TRADE_DATE)||ymd(im.trade_date)||firstRowDate(ir);
    const daytrade=ymd(d.daytrade)||ymd(window.DOGSON_DAYTRADE_TRADE_DATE)||ymd(dm.trade_date)||firstRowDate(dr);
    const latest=ymd(snap.latest)||[market,close,intraday,daytrade].filter(Boolean).sort().at(-1)||'';
    return{close,market,intraday,daytrade,latest};
  }

  function quality(){return window.DOGSON_DATA_TRUTH_V1700?.operational?.quality||window.DOGSON_BOOT_SYSTEM_STATUS?.operational?.intraday_quality||{}}
  function taipeiSession(){try{const p={};new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).forEach(x=>{if(x.type!=='literal')p[x.type]=x.value});const m=Number(p.hour)*60+Number(p.minute);return['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday)&&m>=535&&m<=815}catch{return false}}

  function spec(){
    const view=activeView(),ds=dates(),q=quality();
    const live=window.DOGSON_INTRADAY_LIVE_READY===true,actionable=window.DOGSON_DAYTRADE_ACTIONABLE===true;
    const quote=q.latest_quote_time||'',structure=q.structure_latest_time||'';
    if(view==='close')return{alert:false,lines:[`${shortDate(ds.close||ds.market||ds.latest)||'—'} 盤後`,'完整資料']};
    if(view==='portfolio')return{alert:false,lines:[`${shortDate(ds.close||ds.market||ds.latest)||'—'} 庫存`,'盤後結構']};
    if(view==='daytrade'){
      if(actionable)return{alert:false,lines:[`${shortDate(ds.daytrade||ds.intraday||ds.latest)||'—'} 盤中即時`,`報價 ${quote||'—'}｜5K ${structure||'—'}`]};
      return{alert:taipeiSession(),lines:[`${shortDate(ds.daytrade||ds.intraday||ds.close||ds.latest)||'—'} 歷史`,'當沖停用']};
    }
    if(live)return{alert:false,lines:[`${shortDate(ds.intraday||ds.latest)||'—'} 盤中即時`,`報價 ${quote||'—'}｜5K ${structure||'—'}`]};
    return{alert:taipeiSession(),lines:[`${shortDate(ds.close||ds.market||ds.latest)||'—'} 盤後`,'完整資料']};
  }

  function renderStatus(){
    const box=ensureStatusBox();if(!box)return;const x=spec();box.classList.toggle('alert',!!x.alert);
    const fp=x.lines.join('|');if(box.dataset.fp===fp)return;box.innerHTML='';x.lines.forEach(v=>{const s=document.createElement('span');s.className='line';s.textContent=v;box.appendChild(s)});box.dataset.fp=fp;
  }

  function setupNav(){
    const nav=$('#dogsonViewNav'),main=nav?.querySelector('.dogson-view-main');if(!nav||!main)return;
    const defs=[['find','盤中','盤中波段'],['close','盤後','盤後波段'],['portfolio','庫存','我的庫存'],['daytrade','當沖','當沖模式']];
    const buttons=[];for(const [key,label,title] of defs){const b=main.querySelector(`[data-v="${key}"]`);if(!b)continue;b.textContent=label;b.title=title;b.setAttribute('role','tab');b.setAttribute('aria-selected',b.classList.contains('active')?'true':'false');buttons.push(b)}
    if(buttons.length===4)buttons.forEach(b=>main.appendChild(b));
  }

  function renderMission(){
    const box=$('#dogsonMissionV1700');if(!box)return;const title=$('.dogson-mission-title-v1700',box),text=$('.dogson-mission-text-v1700',box);if(!title||!text)return;
    const v=activeView();let t='🔎 找波段',x='盤中找正在轉強、適合波段觀察的股票。';
    if(v==='close'){t='🌙 盤後作戰';x='收盤後找值得明天繼續觀察的波段候選。'}else if(v==='portfolio'){t='💼 我的庫存';x='先看持股結構與風險，再決定續抱、減碼或加碼。'}else if(v==='daytrade'){t='🎯 當沖執行';x='只看通過即時品質門檻、盤中可執行的候選。'}
    title.textContent=t;text.textContent=x;
  }

  function render(){installStyle();setupNav();renderStatus();renderMission()}
  function boot(){
    render();[120,450,1000,2200].forEach(ms=>setTimeout(render,ms));
    ['dogson:data-truth','dogson:data-ready','dogson:actionability','dogson:freshness'].forEach(name=>window.addEventListener(name,()=>setTimeout(render,0)));
    document.addEventListener('click',e=>{if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly')){setTimeout(render,0);setTimeout(render,100)}},true);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)render()});
    setInterval(()=>{if(!document.hidden)render()},60000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();