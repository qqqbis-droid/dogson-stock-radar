(()=>{
  if(window.__DOGSON_SHELL_V1750__) return;
  window.__DOGSON_SHELL_V1750__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const cache={system:null,close:null,intraday:null,daytrade:null};

  const ymd=v=>{const m=String(v||'').match(/(20\d{2})-(\d{2})-(\d{2})/);return m?`${m[1]}-${m[2]}-${m[3]}`:''};
  const shortDate=v=>{const d=ymd(v);if(!d)return'';const [,m,day]=d.split('-');return `${Number(m)}/${Number(day)}`};
  const firstDate=(o,keys)=>{for(const k of keys){const d=ymd(o?.[k]);if(d)return d}return''};
  const rowDate=o=>{for(const r of (Array.isArray(o?.rows)?o.rows:[])){const d=ymd(r?.quote_date)||ymd(r?.trade_date)||ymd(r?.date);if(d)return d}return''};

  async function json(name){
    try{
      const r=await fetch(`./data/${name}.json?shell=1750&t=${Date.now()}`,{cache:'no-store'});
      if(!r.ok) return null;
      return await r.json();
    }catch{return null}
  }

  function installStyle(){
    if($('#dogson-shell-style-v1750')) return;
    const s=document.createElement('style');
    s.id='dogson-shell-style-v1750';
    s.textContent=`
      /* Old status/reminder UIs stay available to their logic but are never visible. */
      .wrap>header #status,
      #dogsonAccuracyGuardV1702,
      #dogsonStableNoticeV1745,
      #dogsonDataTruthV1700{display:none!important;visibility:hidden!important;height:0!important;min-height:0!important;max-height:0!important;margin:0!important;padding:0!important;border:0!important;overflow:hidden!important;}

      .wrap>header{display:grid!important;grid-template-columns:minmax(0,1fr) 122px!important;column-gap:10px!important;align-items:stretch!important;margin:4px 2px 10px!important;}
      .wrap>header>div:first-child{min-width:0!important;display:flex!important;flex-direction:column!important;justify-content:center!important;}
      .wrap>header h1{margin:0!important;white-space:nowrap!important;line-height:1.18!important;}
      .wrap>header .sub{margin-top:4px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;}

      #dogsonHeaderStatusV1750{width:122px;height:58px;min-width:122px;box-sizing:border-box;margin:0;padding:8px 10px;border-radius:14px;display:flex;flex-direction:column;justify-content:center;gap:3px;font-size:10.5px;font-weight:850;line-height:1.25;overflow:hidden;}
      #dogsonHeaderStatusV1750.center{align-items:center;text-align:center;}
      #dogsonHeaderStatusV1750.left{align-items:flex-start;text-align:left;}
      #dogsonHeaderStatusV1750.alert{background:#fff8e8!important;border-color:#ead9a9!important;color:#6f5718!important;}
      #dogsonHeaderStatusV1750 .line{display:block;width:100%;white-space:nowrap;overflow:hidden;text-overflow:clip;}

      #dogsonViewNav.dogson-v1750-nav{display:grid!important;grid-template-columns:minmax(0,1fr) 48px!important;gap:10px!important;align-items:center!important;padding:0!important;background:transparent!important;border:0!important;box-shadow:none!important;overflow:visible!important;}
      #dogsonViewNav .dogson-view-main{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:4px!important;width:100%!important;padding:4px!important;margin:0!important;background:#eef2ef!important;border:1px solid #dfe6e1!important;border-radius:20px!important;overflow:hidden!important;}
      #dogsonViewNav .dogson-view-main>button{appearance:none!important;-webkit-appearance:none!important;min-width:0!important;min-height:48px!important;margin:0!important;padding:0 6px!important;border:0!important;border-radius:16px!important;background:transparent!important;color:#56665f!important;box-shadow:none!important;font-size:14px!important;font-weight:800!important;line-height:1!important;white-space:nowrap!important;}
      #dogsonViewNav .dogson-view-main>button.active{background:#2f7865!important;color:#fff!important;box-shadow:0 2px 8px rgba(34,86,71,.20)!important;}
      #dogsonViewNav .dogson-theme-toggle{width:48px!important;height:56px!important;min-width:48px!important;margin:0!important;padding:0!important;display:grid!important;place-items:center!important;border:1px solid #dfe6e1!important;border-radius:18px!important;background:#fff!important;color:#52665e!important;font-size:20px!important;}

      #dogsonMissionV1700{margin:14px 2px 8px!important;padding:0!important;border:0!important;border-radius:0!important;background:transparent!important;box-shadow:none!important;}
      #dogsonMissionV1700 .dogson-mission-title-v1700{font-size:15px!important;font-weight:950!important;color:#25312c!important;}
      #dogsonMissionV1700 .dogson-mission-text-v1700{margin-top:3px!important;font-size:10.5px!important;line-height:1.5!important;color:#7a8580!important;}

      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main{background:#252b28!important;border-color:#39423d!important;}
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main>button{color:#aeb9b3!important;}
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-view-main>button.active{background:#3a806d!important;color:#fff!important;}
      html[data-dogson-theme="dark"] #dogsonViewNav .dogson-theme-toggle{background:#252b28!important;border-color:#39423d!important;color:#e3ebe6!important;}
      html[data-dogson-theme="dark"] #dogsonHeaderStatusV1750.alert{background:#332c1b!important;border-color:#5a4b25!important;color:#f0d98e!important;}
      html[data-dogson-theme="dark"] #dogsonMissionV1700 .dogson-mission-title-v1700{color:#eef2ef!important;}
      html[data-dogson-theme="dark"] #dogsonMissionV1700 .dogson-mission-text-v1700{color:#9da8a2!important;}

      @media(max-width:720px){
        .wrap>header{grid-template-columns:minmax(0,1fr) 116px!important;column-gap:8px!important;}
        #dogsonHeaderStatusV1750{width:116px;min-width:116px;height:56px;padding:7px 9px;font-size:10px;}
        #dogsonViewNav.dogson-v1750-nav{grid-template-columns:minmax(0,1fr) 46px!important;gap:8px!important;}
        #dogsonViewNav .dogson-view-main>button{min-height:46px!important;padding:0 3px!important;font-size:13px!important;}
        #dogsonViewNav .dogson-theme-toggle{width:46px!important;height:54px!important;min-width:46px!important;font-size:19px!important;}
      }
      @media(max-width:360px){
        .wrap>header{grid-template-columns:minmax(0,1fr) 110px!important;column-gap:6px!important;}
        #dogsonHeaderStatusV1750{width:110px;min-width:110px;padding-left:7px;padding-right:7px;font-size:9.5px;}
      }
    `;
    document.head.appendChild(s);
  }

  function ensureStatusBox(){
    const header=$('.wrap>header');
    if(!header) return null;
    let box=$('#dogsonHeaderStatusV1750');
    if(!box){
      box=document.createElement('div');
      box.id='dogsonHeaderStatusV1750';
      box.className='pill center';
      box.setAttribute('aria-label','資料狀態');
      header.appendChild(box);
    }
    return box;
  }

  function activeView(){
    const v=$('#dogsonViewNav .dogson-view-main > button.active[data-v]')?.dataset?.v||'';
    if(v==='close') return 'close';
    if(v==='portfolio') return 'portfolio';
    if(v==='daytrade') return 'daytrade';
    try{if(portfolioOnly)return'portfolio'}catch{}
    try{if(mode==='close')return'close';if(mode==='daytrade')return'daytrade'}catch{}
    return 'intraday';
  }

  function dates(){
    const snap=window.DOGSON_DATA_TRUTH_V1700||{};
    const sd=cache.system?.dates||{};
    const d=snap.dates||{};
    const close=ymd(d.close)||ymd(sd.close)||firstDate(cache.close,['trade_date','date','quote_date'])||rowDate(cache.close)||ymd(window.DOGSON_CLOSE_TRADE_DATE);
    const market=ymd(d.market)||ymd(sd.market)||close;
    const intraday=ymd(d.intraday)||ymd(sd.intraday)||ymd(cache.intraday?.bridge?.trade_date)||firstDate(cache.intraday,['trade_date','date'])||rowDate(cache.intraday)||ymd(window.DOGSON_INTRADAY_TRADE_DATE);
    const daytrade=ymd(d.daytrade)||ymd(sd.daytrade)||firstDate(cache.daytrade,['source_trade_date','trade_date','date'])||rowDate(cache.daytrade)||ymd(window.DOGSON_DAYTRADE_TRADE_DATE);
    const latest=ymd(snap.latest)||ymd(cache.system?.latest_completed_trade_date)||[market,close,intraday,daytrade].filter(Boolean).sort().at(-1)||'';
    return {close,market,intraday,daytrade,latest};
  }

  function quality(){
    const snap=window.DOGSON_DATA_TRUTH_V1700||{};
    return snap.operational?.quality||cache.system?.operational?.intraday_quality||{};
  }

  function taipeiSession(){
    try{
      const p={};
      new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).forEach(x=>{if(x.type!=='literal')p[x.type]=x.value});
      const m=Number(p.hour)*60+Number(p.minute);
      return ['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday)&&m>=535&&m<=815;
    }catch{return false}
  }

  function spec(){
    const view=activeView();
    const ds=dates();
    const q=quality();
    const live=window.DOGSON_INTRADAY_LIVE_READY===true;
    const actionable=window.DOGSON_DAYTRADE_ACTIONABLE===true;
    const quote=q.latest_quote_time||cache.intraday?.quote_layer?.latest_time||'';
    const structure=q.structure_latest_time||'';

    if(view==='close'){
      const d=shortDate(ds.close||ds.market||ds.latest);
      return {align:'center',alert:false,lines:[`${d||'—'} 盤後`,'完整資料']};
    }
    if(view==='portfolio'){
      const d=shortDate(ds.close||ds.market||ds.latest);
      return {align:'center',alert:false,lines:[`${d||'—'} 庫存`,'盤後結構']};
    }
    if(view==='daytrade'){
      if(actionable){
        const d=shortDate(ds.daytrade||ds.intraday||ds.latest);
        return {align:'left',alert:false,lines:[`${d||'—'} MIS${quote?` ${quote}`:''}`,`5分K${structure?` ${structure}`:''}`]};
      }
      const d=shortDate(ds.daytrade||ds.intraday||ds.close||ds.latest);
      return {align:'center',alert:taipeiSession(),lines:[`${d||'—'} 歷史`,'當沖停用']};
    }
    if(live){
      const d=shortDate(ds.intraday||ds.latest);
      return {align:'left',alert:false,lines:[`${d||'—'} MIS${quote?` ${quote}`:''}`,`5分K${structure?` ${structure}`:''}`]};
    }
    const d=shortDate(ds.close||ds.market||ds.latest);
    return {align:'center',alert:taipeiSession(),lines:[`${d||'—'} 盤後`,'完整資料']};
  }

  function renderStatus(){
    const box=ensureStatusBox();
    if(!box) return;
    const x=spec();
    box.classList.toggle('left',x.align==='left');
    box.classList.toggle('center',x.align!=='left');
    box.classList.toggle('alert',!!x.alert);
    const fp=x.lines.join('|');
    if(box.dataset.fp!==fp){
      box.innerHTML='';
      x.lines.forEach(v=>{const line=document.createElement('span');line.className='line';line.textContent=v;box.appendChild(line)});
      box.dataset.fp=fp;
    }
  }

  function setupNav(){
    const nav=$('#dogsonViewNav');
    const main=nav?.querySelector('.dogson-view-main');
    if(!nav||!main) return;
    nav.classList.add('dogson-v1750-nav');
    const defs=[['find','盤中','盤中波段'],['close','盤後','盤後波段'],['portfolio','庫存','我的庫存'],['daytrade','當沖','當沖模式']];
    const buttons=[];
    for(const [key,label,title] of defs){
      const b=main.querySelector(`[data-v="${key}"]`);
      if(!b) continue;
      b.textContent=label;
      b.title=title;
      b.setAttribute('role','tab');
      b.setAttribute('aria-selected',b.classList.contains('active')?'true':'false');
      buttons.push(b);
    }
    if(buttons.length===4) buttons.forEach(b=>main.appendChild(b));
  }

  function renderMission(){
    const box=$('#dogsonMissionV1700');
    if(!box) return;
    const title=$('.dogson-mission-title-v1700',box);
    const text=$('.dogson-mission-text-v1700',box);
    if(!title||!text) return;
    const v=activeView();
    let t='🔎 找波段',x='盤中找正在轉強、適合波段觀察的股票。';
    if(v==='close'){t='🌙 盤後作戰';x='收盤後找值得明天繼續觀察的波段候選。'}
    else if(v==='portfolio'){t='💼 我的庫存';x='先看持股結構與風險，再決定續抱、減碼或加碼。'}
    else if(v==='daytrade'){t='🎯 當沖執行';x='只看通過即時品質門檻、盤中可執行的候選。'}
    title.textContent=t;text.textContent=x;
  }

  function render(){installStyle();setupNav();renderStatus();renderMission()}

  async function refreshData(){
    const [system,close,intraday,daytrade]=await Promise.all([json('system_status'),json('close'),json('intraday'),json('daytrade')]);
    if(system)cache.system=system;if(close)cache.close=close;if(intraday)cache.intraday=intraday;if(daytrade)cache.daytrade=daytrade;
    render();
  }

  function boot(){
    render();
    refreshData();
    [200,700,1500,3000].forEach(ms=>setTimeout(render,ms));
    window.addEventListener('dogson:data-truth',()=>setTimeout(render,0));
    window.addEventListener('dogson:actionability',()=>setTimeout(render,0));
    window.addEventListener('dogson:freshness',()=>setTimeout(render,0));
    document.addEventListener('click',e=>{if(e.target?.closest?.('#dogsonViewNav,.tab,#portfolioOnly')){setTimeout(render,0);setTimeout(render,80);setTimeout(render,220)}},true);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden){render();refreshData()}});
    setInterval(()=>{if(!document.hidden){render();refreshData()}},60000);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
