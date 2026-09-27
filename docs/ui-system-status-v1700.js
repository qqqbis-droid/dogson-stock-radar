(()=>{
  if(window.__DOGSON_SYSTEM_STATUS_V1720__) return;
  window.__DOGSON_SYSTEM_STATUS_V1720__=true;
  window.DOGSON_APP_VERSION='1.7.2';

  const $=(s,r=document)=>r.querySelector(s);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const ymd=v=>{const m=String(v||'').match(/(20\d{2})-(\d{2})-(\d{2})/);return m?`${m[1]}-${m[2]}-${m[3]}`:''};
  const firstDate=(o,keys)=>{for(const k of keys){const d=ymd(o?.[k]);if(d)return d}return''};
  const firstRowDate=rows=>{for(const r of (Array.isArray(rows)?rows.slice(0,40):[])){const d=ymd(r?.quote_date)||ymd(r?.trade_date)||ymd(r?.date)||ymd(r?.chip_date);if(d)return d}return''};

  async function json(name){
    try{const r=await fetch(`./data/${name}.json?truth=1751&t=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(String(r.status));return await r.json()}
    catch(e){return{_error:e?.message||'讀取失敗'}}
  }

  function taipeiClock(){
    try{
      const p={};new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).forEach(x=>{if(x.type!=='literal')p[x.type]=x.value});
      const minute=Number(p.hour)*60+Number(p.minute);
      return{today:`${p.year}-${p.month}-${p.day}`,minute,second:Number(p.second||0),session:['Mon','Tue','Wed','Thu','Fri'].includes(p.weekday)&&minute>=535&&minute<=815};
    }catch{return{today:'',minute:0,second:0,session:false}}
  }

  function currentMode(){try{return mode||'intraday'}catch{return'intraday'}}
  function portfolioView(){try{return!!portfolioOnly}catch{return false}}
  function globals(){
    let cm={},im={},dm={},cr=[],ir=[],dr=[];
    try{cm=closeMarket||{};im=intraMarket||{};dm=daytradeMarket||{};cr=closeRows||[];ir=intraRows||[];dr=daytradeRows||[]}catch{}
    return{cm,im,dm,cr,ir,dr};
  }

  function fallbackDates(){
    const g=globals();
    return{
      market:firstDate(g.cm,['trade_date','date','updated_at']),
      close:firstDate(g.cm,['trade_date','date'])||firstRowDate(g.cr),
      intraday:firstDate(g.im,['trade_date','date'])||firstRowDate(g.ir),
      hourly:ymd(window.DOGSON_HOURLY_TRADE_DATE),
      daytrade:firstDate(g.dm,['trade_date','date'])||firstRowDate(g.dr),
      chips:ymd(window.DOGSON_CHIP_TRADE_DATE)
    };
  }

  function mission(m,p){
    if(p)return{icon:'💼',title:'我的庫存',text:'先看哪些持股需要處理，再看市場背景；不是拿來找今天最強的新股票。'};
    if(m==='close')return{icon:'🌙',title:'盤後作戰',text:'收盤後找值得明天繼續蹲的波段候選，再確認進場位置與風險。'};
    if(m==='daytrade')return{icon:'🎯',title:'當沖執行',text:'只有合格盤中即時狀態才顯示可執行候選；其他時間不把歷史訊號冒充現在機會。'};
    return{icon:'🔎',title:'找波段',text:'盤中即時層通過品質門檻才用5分鐘雷達；其他時間自動使用最近完整盤後資料。'};
  }

  function installStyle(){
    if($('#dogsonSystemStatusStyle'))return;
    const s=document.createElement('style');s.id='dogsonSystemStatusStyle';s.textContent=`
      .dogson-mission-v1700{margin:9px 0 10px;padding:11px 12px;border:1px solid #dfe5e1;border-radius:14px;background:#fff;box-shadow:0 3px 14px rgba(34,51,43,.04)}
      .dogson-mission-title-v1700{font-size:14px;font-weight:950;color:#25312c}.dogson-mission-text-v1700{font-size:10.5px;line-height:1.55;color:#75817b;margin-top:3px}
      .dogson-truth-v1700{margin:8px 0 10px;border:1px solid #dfe5e1;border-radius:14px;background:#fff;overflow:hidden}.dogson-truth-v1700>summary{list-style:none;padding:10px 12px;display:flex;gap:8px;align-items:center;justify-content:space-between;cursor:pointer}.dogson-truth-v1700>summary::-webkit-details-marker{display:none}
      .dogson-truth-title-v1700{font-size:11px;font-weight:900;color:#304038}.dogson-truth-sub-v1700{font-size:9.5px;color:#7e8984;margin-top:2px}.dogson-truth-badge-v1700{font-size:9px;font-weight:900;padding:5px 7px;border-radius:999px;white-space:nowrap}.dogson-truth-badge-v1700.ok{background:#edf6f0;color:#337256}.dogson-truth-badge-v1700.warn{background:#faf3df;color:#8b681b}.dogson-truth-badge-v1700.bad{background:#faecee;color:#b9444e}.dogson-truth-body-v1700{padding:0 10px 10px}.dogson-truth-grid-v1700{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.dogson-truth-item-v1700{padding:8px;border-radius:10px;background:#f7f9f7;border:1px solid #e8ece9}.dogson-truth-k-v1700{font-size:9px;color:#7d8983}.dogson-truth-v-v1700{font-size:11px;font-weight:900;color:#2b3731;margin-top:2px}.dogson-truth-note-v1700{font-size:9px;line-height:1.5;color:#7c8882;margin-top:8px}
      @media(max-width:560px){.dogson-truth-grid-v1700{grid-template-columns:repeat(2,minmax(0,1fr))}}
    `;document.head.appendChild(s);
  }

  function setVersion(){const sub=$('header .sub');if(sub)sub.textContent='犬子老師・決策雷達 v1.7.2';document.documentElement.dataset.dogsonAppVersion='1.7.2'}
  function renderMission(){
    const nav=$('#dogsonViewNav');if(!nav)return;let box=$('#dogsonMissionV1700');
    if(!box){box=document.createElement('section');box.id='dogsonMissionV1700';box.className='dogson-mission-v1700';nav.after(box)}
    const x=mission(currentMode(),portfolioView()),html=`<div class="dogson-mission-title-v1700">${x.icon} ${esc(x.title)}</div><div class="dogson-mission-text-v1700">${esc(x.text)}</div>`;
    if(box.dataset.h!==html){box.innerHTML=html;box.dataset.h=html}
  }

  let snapshot=null;
  function makeSnapshot(system={},status={},market={}){
    const fb=fallbackDates(),sd=system?.dates||{};
    const dates={
      market:ymd(sd.market)||fb.market,
      intraday:ymd(sd.intraday)||fb.intraday,
      close:ymd(sd.close)||fb.close,
      hourly:ymd(sd.hourly)||fb.hourly,
      daytrade:ymd(sd.daytrade)||fb.daytrade,
      chips:ymd(sd.chips)||fb.chips
    };
    const valid=Object.values(dates).filter(Boolean).sort();
    const latest=ymd(system?.latest_completed_trade_date)||[dates.market,dates.close].filter(Boolean).sort().at(-1)||valid.at(-1)||'';
    const intradayStale=system?.freshness?.intraday_stale===true||!!(latest&&dates.intraday&&dates.intraday<latest);
    const daytradeStale=system?.freshness?.daytrade_stale===true||!!(latest&&dates.daytrade&&dates.daytrade<latest);
    const q={...(system?.operational?.intraday_quality||{})};
    const c=taipeiClock();
    const liveReady=!!(c.session&&dates.intraday===c.today&&!intradayStale&&Number(q.quote_coverage_pct||0)>=Number(q.coverage_min_pct||80)&&q.latest_quote_time);
    const dayActionable=!!(liveReady&&dates.daytrade===c.today&&!daytradeStale);
    const errors=[system,status,market].filter(x=>x?._error).length;
    return{dates,latest,errors,status,market,system,freshness:{intradayStale,daytradeStale},operational:{clock:c,quality:q,liveReady,dayActionable}};
  }

  function publish(){
    if(!snapshot)return;
    const {dates,freshness,operational}=snapshot;
    window.DOGSON_DATA_TRUTH_V1700=snapshot;
    window.DOGSON_INTRADAY_STALE=freshness.intradayStale;
    window.DOGSON_DAYTRADE_STALE=freshness.daytradeStale;
    window.DOGSON_INTRADAY_LIVE_READY=operational.liveReady;
    window.DOGSON_DAYTRADE_ACTIONABLE=operational.dayActionable;
    window.DOGSON_CLOSE_TRADE_DATE=dates.close||dates.market||'';
    window.DOGSON_INTRADAY_TRADE_DATE=dates.intraday||'';
    window.DOGSON_DAYTRADE_TRADE_DATE=dates.daytrade||'';
    renderTruth();
    try{window.dispatchEvent(new CustomEvent('dogson:data-truth',{detail:snapshot}))}catch{}
  }

  async function loadTruth(){
    const [system,status,market]=await Promise.all([json('system_status'),json('status'),json('market')]);
    snapshot=makeSnapshot(system,status,market);publish();
  }

  function refreshFromGlobals(){
    snapshot=makeSnapshot(snapshot?.system||window.DOGSON_BOOT_SYSTEM_STATUS||{},snapshot?.status||{},snapshot?.market||{});publish();
  }

  function renderTruth(){
    const anchor=$('#dogsonMissionV1700')||$('#dogsonViewNav');if(!anchor||!snapshot)return;let d=$('#dogsonDataTruthV1700');
    if(!d){d=document.createElement('details');d.id='dogsonDataTruthV1700';d.className='dogson-truth-v1700';anchor.after(d)}
    const {dates,latest,errors,freshness,operational}=snapshot;let tone='ok',badge='資料日期一致';
    if(errors){tone='bad';badge='狀態資料讀取失敗'}else if(freshness.intradayStale||freshness.daytradeStale){tone='warn';badge='舊即時訊號已停用'}else if(!operational.liveReady){tone='warn';badge=operational.clock.session?'即時品質未達門檻':'非盤中・使用完整盤後'}
    const items=[['市場',dates.market],['盤中結構',dates.intraday],['盤後波段',dates.close],['60分K',dates.hourly],['當沖行情',dates.daytrade],['籌碼',dates.chips]];
    const grid=items.map(([k,v])=>`<div class="dogson-truth-item-v1700"><div class="dogson-truth-k-v1700">${esc(k)}</div><div class="dogson-truth-v-v1700">${esc(v||'—')}</div></div>`).join('');
    const q=operational.quality||{},sub=latest?`最近完整交易日 ${latest}｜MIS覆蓋 ${Number(q.quote_coverage_pct||0).toFixed(1)}%｜${operational.liveReady?'即時可用':'即時未啟用'}`:'正在核對資料…';
    const html=`<summary><div><div class="dogson-truth-title-v1700">資料狀態・v1.7.2</div><div class="dogson-truth-sub-v1700">${esc(sub)}</div></div><span class="dogson-truth-badge-v1700 ${tone}">${esc(badge)}</span></summary><div class="dogson-truth-body-v1700"><div class="dogson-truth-grid-v1700">${grid}</div><div class="dogson-truth-note-v1700">狀態層只讀小型 canonical metadata；大型 close / intraday / daytrade 不會在這裡重複下載。</div></div>`;
    if(d.dataset.h!==html){d.innerHTML=html;d.dataset.h=html}
  }

  function boot(){
    installStyle();setVersion();renderMission();loadTruth();
    document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav,#portfolioOnly'))setTimeout(()=>{renderMission();refreshFromGlobals()},80)});
    window.addEventListener('dogson:data-ready',()=>setTimeout(refreshFromGlobals,20));
    window.addEventListener('dogson:freshness',()=>setTimeout(refreshFromGlobals,20));
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)setTimeout(loadTruth,50)});
    setInterval(()=>{if(!document.hidden)loadTruth()},120000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();