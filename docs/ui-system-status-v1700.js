(()=>{
  if(window.__DOGSON_SYSTEM_STATUS_V1700__) return;
  window.__DOGSON_SYSTEM_STATUS_V1700__=true;
  window.DOGSON_APP_VERSION='1.7.0';
  const $=(s,r=document)=>r.querySelector(s);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const ymd=v=>{const m=String(v||'').match(/(20\d{2})-(\d{2})-(\d{2})/);return m?`${m[1]}-${m[2]}-${m[3]}`:''};
  const nowTs=()=>Date.now();
  const json=async name=>{
    try{
      const r=await fetch(`./data/${name}.json?truth=${nowTs()}`,{cache:'no-store'});
      if(!r.ok) throw new Error(String(r.status));
      return await r.json();
    }catch(e){return {_error:e?.message||'讀取失敗'}}
  };
  const dateFrom=(o,keys=[])=>{
    for(const k of keys){const d=ymd(o?.[k]);if(d)return d}
    const d=ymd(o?.trade_date)||ymd(o?.date)||ymd(o?.updated_at)||ymd(o?.close_updated_at)||ymd(o?.intraday_updated_at);
    if(d)return d;
    const rows=Array.isArray(o?.rows)?o.rows:[];
    for(const r of rows.slice(0,30)){
      const x=ymd(r?.trade_date)||ymd(r?.date)||ymd(r?.chip_date)||ymd(r?.updated_at);
      if(x)return x;
    }
    return '';
  };
  const chipDate=o=>{
    const rows=Array.isArray(o?.rows)?o.rows:[];
    const ds=rows.map(r=>ymd(r?.chip_date)||ymd(r?.foreign_date)||ymd(r?.date)).filter(Boolean).sort();
    return ds.at(-1)||dateFrom(o);
  };
  function currentMode(){try{return mode||'intraday'}catch{return'intraday'}}
  function mission(m,portfolio){
    if(portfolio)return{icon:'💼',title:'我的庫存',text:'先看哪些持股需要處理，再看市場背景；不是拿來找今天最強的新股票。'};
    if(m==='close')return{icon:'🌙',title:'盤後作戰',text:'收盤後找值得明天繼續蹲的波段候選，再確認進場位置與風險。'};
    if(m==='daytrade')return{icon:'🎯',title:'當沖執行',text:'只回答今天這一筆能不能做；5分K、VWAP、量速與位置優先。'};
    return{icon:'🔎',title:'找波段',text:'盤中先看市場與族群，再找趨勢成立而且位置合理的波段機會。'};
  }
  function portfolioView(){try{return !!portfolioOnly}catch{return document.documentElement.classList.contains('dogson-portfolio-view')}}
  function installStyle(){
    if($('#dogsonSystemStatusStyle'))return;
    const s=document.createElement('style');s.id='dogsonSystemStatusStyle';s.textContent=`
      .dogson-mission-v1700{margin:9px 0 10px;padding:11px 12px;border:1px solid #dfe5e1;border-radius:14px;background:#fff;box-shadow:0 3px 14px rgba(34,51,43,.04)}
      .dogson-mission-title-v1700{font-size:14px;font-weight:950;color:#25312c}.dogson-mission-text-v1700{font-size:10.5px;line-height:1.55;color:#75817b;margin-top:3px}
      .dogson-truth-v1700{margin:8px 0 10px;border:1px solid #dfe5e1;border-radius:14px;background:#fff;overflow:hidden}.dogson-truth-v1700>summary{list-style:none;padding:10px 12px;display:flex;gap:8px;align-items:center;justify-content:space-between;cursor:pointer}.dogson-truth-v1700>summary::-webkit-details-marker{display:none}
      .dogson-truth-head-v1700{min-width:0}.dogson-truth-title-v1700{font-size:11px;font-weight:900;color:#304038}.dogson-truth-sub-v1700{font-size:9.5px;color:#7e8984;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.dogson-truth-badge-v1700{font-size:9px;font-weight:900;padding:5px 7px;border-radius:999px;white-space:nowrap}.dogson-truth-badge-v1700.ok{background:#edf6f0;color:#337256}.dogson-truth-badge-v1700.warn{background:#faf3df;color:#8b681b}.dogson-truth-badge-v1700.bad{background:#faecee;color:#b9444e}
      .dogson-truth-body-v1700{padding:0 10px 10px}.dogson-truth-grid-v1700{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.dogson-truth-item-v1700{padding:8px;border-radius:10px;background:#f7f9f7;border:1px solid #e8ece9}.dogson-truth-k-v1700{font-size:9px;color:#7d8983}.dogson-truth-v-v1700{font-size:11px;font-weight:900;color:#2b3731;margin-top:2px}.dogson-truth-note-v1700{font-size:9px;line-height:1.5;color:#7c8882;margin-top:8px}.dogson-truth-source-v1700{margin-top:8px;padding-top:8px;border-top:1px dashed #e0e6e2;font-size:9px;line-height:1.5;color:#7d8983}
      html[data-dogson-theme="dark"] .dogson-mission-v1700,html[data-dogson-theme="dark"] .dogson-truth-v1700{background:#202522;border-color:#343b37}html[data-dogson-theme="dark"] .dogson-mission-title-v1700,html[data-dogson-theme="dark"] .dogson-truth-title-v1700,html[data-dogson-theme="dark"] .dogson-truth-v-v1700{color:#eef2ef}html[data-dogson-theme="dark"] .dogson-truth-item-v1700{background:#252b27;border-color:#343b37}
      @media(max-width:560px){.dogson-truth-grid-v1700{grid-template-columns:repeat(2,minmax(0,1fr))}}
    `;document.head.appendChild(s);
  }
  function setVersion(){
    const sub=$('header .sub');
    if(sub)sub.textContent='犬子老師・決策雷達 v1.7.0';
    document.documentElement.dataset.dogsonAppVersion='1.7.0';
  }
  function renderMission(){
    const nav=$('#dogsonViewNav');if(!nav)return;
    let box=$('#dogsonMissionV1700');if(!box){box=document.createElement('section');box.id='dogsonMissionV1700';box.className='dogson-mission-v1700';nav.after(box)}
    const x=mission(currentMode(),portfolioView());
    const html=`<div class="dogson-mission-title-v1700">${x.icon} ${esc(x.title)}</div><div class="dogson-mission-text-v1700">${esc(x.text)}</div>`;
    if(box.dataset.h!==html){box.innerHTML=html;box.dataset.h=html}
  }
  let snapshot=null;
  async function loadTruth(){
    const [market,intra,close,hourly,daytrade,chips,status,system]=await Promise.all(['market','intraday','close','hourly','daytrade','chip_history','status','system_status'].map(json));
    const dates=system?.dates&&typeof system.dates==='object'?{
      market:ymd(system.dates.market),intraday:ymd(system.dates.intraday),close:ymd(system.dates.close),hourly:ymd(system.dates.hourly),daytrade:ymd(system.dates.daytrade),chips:ymd(system.dates.chips)
    }:{
      market:dateFrom(market,['trade_date']),intraday:dateFrom(intra,['trade_date']),close:dateFrom(close,['trade_date']),hourly:dateFrom(hourly,['trade_date','updated_at']),daytrade:dateFrom(daytrade,['trade_date','updated_at']),chips:chipDate(chips)
    };
    const valid=Object.values(dates).filter(Boolean).sort();
    const latest=ymd(system?.latest_completed_trade_date)||valid.at(-1)||'';
    const errors=[market,intra,close,hourly,daytrade,chips,status,system].filter(x=>x?._error).length;
    snapshot={dates,latest,errors,status,market,system};
    window.DOGSON_DATA_TRUTH_V1700=snapshot;
    renderTruth();
  }
  function sourceLabel(){
    const m=currentMode(),stale=window.DOGSON_INTRADAY_STALE===true;
    if(m==='close')return'盤後頁使用 close + market + hourly + 已完成交易日籌碼';
    if(m==='daytrade')return stale?'當沖來源落後，舊訊號已停用；等待下一個實際交易時段重新建立':'當沖頁使用 daytrade / intraday；波段與昨日法人只作背景';
    if(stale)return'找波段的舊 intraday 已隔離；個股卡片改用較新的 close，盤中5分鐘訊號暫停';
    return'找波段頁使用 intraday；即時報價另由 TWSE MIS 補充';
  }
  function renderTruth(){
    const anchor=$('#dogsonMissionV1700')||$('#dogsonViewNav');if(!anchor||!snapshot)return;
    let d=$('#dogsonDataTruthV1700');if(!d){d=document.createElement('details');d.id='dogsonDataTruthV1700';d.className='dogson-truth-v1700';anchor.after(d)}
    const {dates,latest,errors,system}=snapshot;
    const current=ymd(system?.latest_completed_trade_date)||[dates.market,dates.close].filter(Boolean).sort().at(-1)||latest;
    const staleIntra=system?.freshness?.intraday_stale===true||!!(dates.intraday&&current&&dates.intraday<current);
    const staleDay=system?.freshness?.daytrade_stale===true||!!(dates.daytrade&&current&&dates.daytrade<current);
    const lag=Object.entries(dates).filter(([,v])=>v&&current&&v<current).map(([k])=>k);
    const guarded=staleIntra||staleDay;
    const tone=errors?'bad':guarded?'warn':lag.length?'warn':'ok';
    const badge=errors?'部分資料讀取失敗':guarded?'舊盤中已隔離':lag.length?'公布時差，已標示':'日期一致';
    const items=[['市場',dates.market],['盤中波段',dates.intraday],['盤後波段',dates.close],['60分K',dates.hourly],['當沖',dates.daytrade],['籌碼',dates.chips]];
    const grid=items.map(([k,v])=>`<div class="dogson-truth-item-v1700"><div class="dogson-truth-k-v1700">${esc(k)}</div><div class="dogson-truth-v-v1700">${esc(v||'讀取中／無日期')}</div></div>`).join('');
    const sub=current?`最近完整交易日 ${current}｜點開核對各資料日期`:'正在核對資料日期…';
    const guardNote=guarded?' 系統已自動隔離落後的盤中／當沖來源，不會把它們冒充成最新訊號。':'';
    const html=`<summary><div class="dogson-truth-head-v1700"><div class="dogson-truth-title-v1700">資料狀態・v1.7.0</div><div class="dogson-truth-sub-v1700">${esc(sub)}</div></div><span class="dogson-truth-badge-v1700 ${tone}">${esc(badge)}</span></summary><div class="dogson-truth-body-v1700"><div class="dogson-truth-grid-v1700">${grid}</div><div class="dogson-truth-note-v1700">日期不同不一定代表錯誤：60分K、法人籌碼公布時間本來不同。${esc(guardNote)}</div><div class="dogson-truth-source-v1700"><b>目前頁面資料規則：</b>${esc(sourceLabel())}<br><b>報價：</b>TWSE MIS｜<b>市場／法人：</b>TWSE、TPEx 官方資料與雷達產出檔。</div></div>`;
    if(d.dataset.h!==html){d.innerHTML=html;d.dataset.h=html}
  }
  let timer;
  function refreshUI(){clearTimeout(timer);timer=setTimeout(()=>{setVersion();renderMission();renderTruth()},40)}
  function boot(){
    installStyle();setVersion();renderMission();loadTruth();
    document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav'))setTimeout(refreshUI,60)});
    window.addEventListener('dogson:freshness',()=>{refreshUI();setTimeout(loadTruth,60)});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(loadTruth,50)});
    setTimeout(refreshUI,300);setTimeout(refreshUI,1000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
