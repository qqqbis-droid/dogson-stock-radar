(()=>{
  'use strict';

  if(window.__DOGSON_UNIFIED_FRESHNESS_V2__) return;
  window.__DOGSON_UNIFIED_FRESHNESS_V2__=true;

  const MISSION={
    intraday:{label:'盤中',core:'decision_intraday_summary',prefixes:['decision_intraday_','zone_intraday','stock_detail_intraday','sector_intraday','market_intraday_context','capital_intraday_context']},
    close:{label:'盤後',core:'decision_close_summary',prefixes:['decision_close_','zone_close','stock_detail_close','sector_close','market_close_context','capital_close_context']},
    daytrade:{label:'當沖',core:'decision_daytrade_summary',prefixes:['decision_daytrade_','zone_daytrade','stock_detail_daytrade']}
  };
  const CLOSE_REQUIRED=['decision_close_summary','market_close_context','capital_close_context','zone_close'];
  const STAGE={OBSERVE:'觀察',SETUP:'蓄勢待發',LAUNCH:'剛啟動',TREND:'趨勢持有',PULLBACK_TEST:'回踩觀察',PULLBACK_CONFIRMED:'回踩承接',WEAKENING:'轉弱警戒',FAILED:'結構失效'};
  const ACTION={WATCH:'觀察',WAIT_TRIGGER:'等觸發',SMALL_TEST:'小量試單候選',WAIT_PULLBACK:'等回踩',HOLD:'續抱',ADD_ON_CONFIRM:'確認後加碼候選',DO_NOT_CHASE:'過熱不追',REDUCE_WATCH:'減碼觀察',EXIT_PRIORITY:'優先出場',DATA_STALE:'資料失效'};

  let manifest=null;
  let closeContext=null;
  let closeRows=[];
  let closeIndex=null;
  let closeZones=null;
  let rowMap=new Map();
  let zoneMap=new Map();
  let renderSeq=0;
  let loadingIndex=false;
  let loadingZones=false;

  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
  const fmt=(v,d=1)=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
  const pad=n=>String(n).padStart(2,'0');
  const parse=v=>{const d=v?new Date(v):null;return d&&!Number.isNaN(d.getTime())?d:null};
  const dateKey=v=>{const d=parse(v);return d?`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`:''};
  const ymd=v=>String(v||'').match(/20\d{2}-\d{2}-\d{2}/)?.[0]||'';
  const activeView=()=>document.querySelector('.tab.active')?.dataset.view||'intraday';
  const shortTime=v=>{const d=parse(v);return d?`${d.getMonth()+1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`:'時間未知'};

  function taipeiToday(){
    try{
      const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
      const get=t=>parts.find(x=>x.type===t)?.value||'';
      return `${get('year')}-${get('month')}-${get('day')}`;
    }catch(_){return new Date().toISOString().slice(0,10)}
  }
  function daysBetween(a,b){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(a)||!/^\d{4}-\d{2}-\d{2}$/.test(b))return null;
    const x=Date.parse(`${a}T00:00:00Z`),y=Date.parse(`${b}T00:00:00Z`);
    return Number.isFinite(x)&&Number.isFinite(y)?Math.floor((y-x)/86400000):null;
  }
  async function getJson(url){
    const r=await fetch(url,{cache:'no-store'});
    if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);
    return r.json();
  }
  async function datasetFromManifest(key){
    const meta=manifest?.datasets?.[key];
    if(!meta)return null;
    return getJson(`${meta.url}${meta.url.includes('?')?'&':'?'}afterhours=${Date.now()}`);
  }

  function missionMeta(key){
    const cfg=MISSION[key],ds=manifest?.datasets||{},core=ds[cfg.core]||null;
    return {key,cfg,core,asOf:core?.as_of||null,date:ymd(core?.as_of)||dateKey(core?.as_of)};
  }
  function missionBadge(meta){
    if(!meta.asOf)return {cls:'unknown',text:'時間未知'};
    if(meta.key==='close')return {cls:'same',text:`盤後定格｜${meta.date||'—'}`};
    const base=manifest?.trade_date||ymd(manifest?.generated_at);
    if(meta.date&&base&&meta.date<base)return {cls:'stale',text:'舊資料／凍結'};
    if(meta.date===base)return {cls:'same',text:'本交易日快照'};
    return {cls:'unknown',text:'日期待核對'};
  }
  function datasetRows(key){
    const cfg=MISSION[key],ds=manifest?.datasets||{},missionDate=missionMeta(key).date,base=key==='close'?missionDate:(manifest?.trade_date||missionDate);
    return Object.entries(ds)
      .filter(([name])=>cfg.prefixes.some(p=>name===p||name.startsWith(p)))
      .sort((a,b)=>a[0].localeCompare(b[0]))
      .map(([name,m])=>{
        const d=ymd(m?.as_of)||dateKey(m?.as_of);
        let st='時間未知';
        if(m?.as_of){
          if(key==='close')st=d===base?'盤後定格':d&&base&&d<base?'更舊快照':'日期異常';
          else st=d&&base&&d<base?'舊／凍結':'本交易日';
        }
        const bad=['舊／凍結','更舊快照','日期異常'].includes(st);
        return `<div class="uf-ds"><code>${esc(name)}</code><span>${esc(shortTime(m?.as_of))}</span><b class="${bad?'stale':''}">${esc(st)}</b></div>`;
      }).join('');
  }
  function mixedWarning(){
    const metas=Object.fromEntries(Object.keys(MISSION).map(k=>[k,missionMeta(k)]));
    const dates=[...new Set(Object.values(metas).map(x=>x.date).filter(Boolean))];
    if(dates.length<=1)return '';
    const closeDate=metas.close?.date||'',liveDates=[metas.intraday?.date,metas.daytrade?.date].filter(Boolean),liveSame=liveDates.length&&liveDates.every(x=>x===liveDates[0]);
    if(closeDate&&liveSame&&liveDates[0]>closeDate){
      return `<div class="uf-schedule">雙時鐘正常：盤中／當沖已進入 ${esc(liveDates[0])}；盤後仍定格最後完成收盤 ${esc(closeDate)}，直到新收盤 Atomic Build 驗證完成才切換。</div>`;
    }
    return `<div class="uf-warning">⚠ 混合資料日：${Object.entries(metas).map(([k,m])=>`${m.cfg.label} ${m.date||'未知'}`).join('；')}。不同任務不可互相視為同一時間的新資料。</div>`;
  }

  function closeGuard(){
    const reasons=[];
    const warnings=[];
    const build=manifest?.active_build_id||'';
    // Close decisions are anchored to the latest completed close mission, not
    // the bundle's live trade_date. During the next session, manifest.trade_date
    // may already be today while close must remain yesterday until today's close
    // bundle is complete and validated.
    const tradeDate=missionMeta('close').date||manifest?.trade_date||'';
    if(!manifest||manifest.schema_version!=='2.0.0')reasons.push('V2 manifest 契約無效');
    if(!manifest?.health?.validation_passed)reasons.push('Atomic Build 尚未通過驗證');
    for(const key of CLOSE_REQUIRED){
      const m=manifest?.datasets?.[key];
      if(!m){reasons.push(`缺少 ${key}`);continue}
      if(m.complete===false)reasons.push(`${key} 尚未完整`);
      if(m.build_id&&build&&m.build_id!==build)reasons.push(`${key} build 不一致`);
      const d=ymd(m.as_of);
      if(d&&tradeDate&&d!==tradeDate)reasons.push(`${key} 日期 ${d} ≠ ${tradeDate}`);
    }
    const ctxDate=ymd(closeContext?.trade_date||closeContext?.as_of);
    if(closeContext){
      if(closeContext.complete===false)reasons.push('市場環境資料不完整');
      if(closeContext.build_id&&build&&closeContext.build_id!==build)reasons.push('市場環境 build 不一致');
      if(ctxDate&&tradeDate&&ctxDate!==tradeDate)reasons.push(`市場環境日期 ${ctxDate} ≠ ${tradeDate}`);
      if(['STALE','UNKNOWN'].includes(String(closeContext.freshness||'').toUpperCase()))reasons.push(`市場環境 freshness=${closeContext.freshness}`);
    }else reasons.push('市場環境尚未載入');

    const age=daysBetween(tradeDate,taipeiToday());
    if(age!=null&&age>=7)reasons.push(`資料距今天已 ${age} 天，超過安全上限`);
    else if(age!=null&&age>=5)warnings.push(`資料距今天 ${age} 天；可能遇連假，開盤前請再核對最新交易日`);

    const allowed=reasons.length===0;
    const caution=allowed&&warnings.length>0;
    window.DOGSON_CLOSE_DECISION_ALLOWED=allowed;
    window.DOGSON_CLOSE_DATA_STATUS={allowed,caution,reasons:[...reasons],warnings:[...warnings],tradeDate,ageDays:age,buildId:build};
    return window.DOGSON_CLOSE_DATA_STATUS;
  }

  function regimeLabel(x){
    const v=String(x||'').toUpperCase();
    if(v==='SELECTIVE_RISK_ON')return'偏多但選股';
    if(v==='RISK_ON')return'偏多';
    if(v==='RISK_OFF')return'防守';
    if(v==='SELECTIVE_RISK_OFF')return'偏空但選股';
    return x||'中性';
  }
  function marketPlan(){
    const g=closeGuard();
    const c=closeContext||{},score=num(c.market_score),comp=c.components||{},breadth=num(c.metrics?.breadth_up_pct??comp.breadth?.breadth_up_pct),foreign1=num(c.metrics?.foreign_net_billion),foreign5=num(c.metrics?.foreign_5d_billion),taStrong=comp.taiex?.trend===true&&comp.taiex?.above20!==false,otcStrong=comp.otc?.trend===true&&comp.otc?.above20!==false;
    if(!g.allowed){
      return {guard:g,tone:'blocked',regime:'歷史參考',score,exposure:'—',newPos:'暫停依這份資料開新倉',chase:'禁止把舊快照當成追價依據',summary:'盤後資料未通過可執行檢查；只保留歷史閱讀，不提供明日操作建議。',improve:'等最新 Atomic Build 通過驗證後再恢復建議。',worsen:g.reasons.join('；')};
    }
    let lo=40,hi=55;
    if(score!=null&&score>=13){lo=65;hi=80}
    else if(score!=null&&score>=11){lo=55;hi=70}
    else if(score!=null&&score>=8){lo=40;hi=60}
    else if(score!=null){lo=25;hi=45}
    if(!taStrong||!otcStrong){lo-=5;hi-=10}
    if(breadth!=null&&breadth<50){lo-=5;hi-=10}
    if(foreign5!=null&&foreign5<0){hi-=5}
    lo=Math.max(20,Math.min(80,lo));hi=Math.max(lo+5,Math.min(85,hi));
    const strong=score!=null&&score>=13&&taStrong&&otcStrong&&(breadth==null||breadth>=55);
    const weak=score!=null&&score<8;
    const newPos=strong?'可開新倉，但只做「回踩守住」或「突破後回測確認」；單筆先小量。':weak?'先不主動擴倉；把資金留給結構重新轉強後。':'新倉縮小，等支撐守住或突破確認，不先猜底。';
    const chase=(foreign5!=null&&foreign5<0)||!otcStrong?'不追開高急拉；站穩 R1 且量價延續，或回踩 S1 守住再做。':'仍不無條件追高；突破需站穩 R1、量價同步，回測不破才升級。';
    const summary=strong?'大盤結構偏多，但仍採選股模式；可以做強勢族群，部位不要一次打滿。':weak?'市場偏防守，先守現金與持股結構。':'市場可做但分歧仍在，重點放在相對強勢族群與低風險進場位置。';
    const improve=`若加權／櫃買續強、上漲家數維持 ${breadth!=null&&breadth>=60?'60%':'55%'} 以上，且外資近5日轉正，可把持股水位再提高一級。`;
    const worsen='若櫃買轉弱、上漲家數跌破 50%，或外資當日重新明顯轉賣，持股水位降一級，新倉改成只觀察不追。';
    return {guard:g,tone:g.caution?'caution':strong?'go':weak?'risk':'wait',regime:regimeLabel(c.market_regime),score,exposure:`${lo}–${hi}%`,newPos,chase,summary,improve,worsen,metrics:{breadth,foreign1,foreign5,taStrong,otcStrong}};
  }

  function ensureFreshnessPanel(){
    let el=document.getElementById('unifiedFreshness');
    if(el)return el;
    const mission=document.getElementById('mission');if(!mission)return null;
    el=document.createElement('section');el.id='unifiedFreshness';el.className='panel uf-panel';
    mission.insertAdjacentElement('afterend',el);return el;
  }
  function renderFreshness(){
    if(!manifest)return;
    const host=ensureFreshnessPanel();if(!host)return;
    const view=activeView();
    if(view==='portfolio'){host.hidden=true;return}host.hidden=false;
    const cards=Object.entries(MISSION).map(([k])=>{const m=missionMeta(k),b=missionBadge(m);return `<button type="button" class="uf-card ${k===view?'active':''}" data-uf-view="${k}"><span>${m.cfg.label}</span><strong>${esc(shortTime(m.asOf))}</strong><em class="${b.cls}">${esc(b.text)}</em></button>`}).join('');
    const current=MISSION[view]||MISSION.intraday;
    const g=view==='close'?closeGuard():null;
    const hard=g&&!g.allowed?`<div class="uf-warning hard">⛔ 盤後不可執行：${esc(g.reasons.join('；'))}</div>`:'';
    const caution=g?.caution?`<div class="uf-warning">⚠ ${esc(g.warnings.join('；'))}</div>`:'';
    host.innerHTML=`<div class="uf-head"><div><b>資料新鮮度</b><small>每個任務看自己的 as_of；盤後另外檢查整包日期、build 與可執行性。</small></div><button type="button" class="uf-refresh">重查時間</button></div>${mixedWarning()}${hard}${caution}<div class="uf-cards">${cards}</div><details class="uf-detail"><summary>${current.label}｜逐資料集時間</summary><div class="uf-datasets">${datasetRows(view)}</div></details><div class="uf-bundle">資料包產生：${esc(shortTime(manifest.generated_at))}。這只代表重新打包時間，<b>不代表包內每一個數據都在這個時間更新。</b></div>${view==='close'?'<div class="uf-schedule">盤後資料以最後完成收盤日為基準；市場、法人、決策與 Zone 必須同一 Close 日期且通過驗證。隔日收盤前維持前一完成交易日快照。</div>':''}`;
    host.querySelectorAll('[data-uf-view]').forEach(btn=>btn.addEventListener('click',()=>document.querySelector(`.tab[data-view="${btn.dataset.ufView}"]`)?.click()));
    host.querySelector('.uf-refresh')?.addEventListener('click',()=>load(true));
  }

  function ensureMarketDecision(){
    let box=document.getElementById('afterhoursDecision');
    if(box)return box;
    const summary=document.getElementById('marketSummary');
    if(!summary)return null;
    box=document.createElement('div');box.id='afterhoursDecision';box.className='ahd-market';
    summary.insertAdjacentElement('afterend',box);return box;
  }
  function renderMarketDecision(){
    const box=ensureMarketDecision();if(!box)return;
    if(activeView()!=='close'){box.hidden=true;return}box.hidden=false;
    const p=marketPlan(),g=p.guard,m=p.metrics||{};
    const dataBadge=!g.allowed?'⛔ 僅供歷史參考':g.caution?'⚠ 日期需再核對':`✓ 可用｜${g.tradeDate||'—'}`;
    box.className=`ahd-market ${p.tone}`;
    box.innerHTML=`<div class="ahd-head"><div><span>犬子明日總策略</span><b>${esc(p.regime)}</b></div><em>${esc(dataBadge)}</em></div><div class="ahd-main"><div><small>建議持股水位</small><strong>${esc(p.exposure)}</strong></div><div><small>市場分數</small><strong>${p.score==null?'—':`${fmt(p.score,1)}/15`}</strong></div><div><small>市場廣度</small><strong>${m.breadth==null?'—':`${fmt(m.breadth,1)}%`}</strong></div></div><p class="ahd-summary">${esc(p.summary)}</p><div class="ahd-rule"><b>新倉</b><span>${esc(p.newPos)}</span></div><div class="ahd-rule"><b>追價</b><span>${esc(p.chase)}</span></div><div class="ahd-if"><div><b>若改善 →</b>${esc(p.improve)}</div><div><b>若轉弱 →</b>${esc(p.worsen)}</div></div>${m.foreign1!=null||m.foreign5!=null?`<div class="ahd-foot">外資：今日 ${m.foreign1==null?'—':`${m.foreign1>0?'+':''}${fmt(m.foreign1,1)} 億`}｜近5日 ${m.foreign5==null?'—':`${m.foreign5>0?'+':''}${fmt(m.foreign5,1)} 億`}</div>`:''}<div class="ahd-foot">持股水位與明日動作屬犬子策略層；不改寫 Engine 分數，仍以同一 Atomic Build 的市場、決策與 Zone 資料為依據。</div>`;
  }

  function price(v){
    const n=num(v);if(n==null)return'—';
    const tick=n<10?.01:n<50?.05:n<100?.1:n<500?.5:n<1000?1:5;
    const d=tick<.1?2:tick<1?1:0;
    return n.toLocaleString('zh-TW',{maximumFractionDigits:d});
  }
  function zoneText(z){
    if(!z)return'—';
    const lo=num(z.low),hi=num(z.high),c=num(z.center);
    if(lo!=null&&hi!=null&&Math.abs(lo-hi)>1e-9)return `${price(lo)}–${price(hi)}`;
    return price(c??lo??hi);
  }
  function zoneFor(d,side){
    const ids=side==='SUPPORT'?(d?.support_zone_ids||[]):(d?.resistance_zone_ids||[]);
    for(const id of ids){const z=zoneMap.get(String(id));if(z)return z}
    return null;
  }
  function conclusion(d,allowed){
    if(!allowed||d?.action_state==='DATA_STALE')return {tone:'stale',label:'僅供歷史參考'};
    if(['EXIT_PRIORITY','REDUCE_WATCH'].includes(d?.action_state)||['FAILED','WEAKENING'].includes(d?.lifecycle_stage))return {tone:'risk',label:'風險優先'};
    if(d?.action_state==='DO_NOT_CHASE')return {tone:'wait',label:'過熱不追'};
    if(['SMALL_TEST','ADD_ON_CONFIRM'].includes(d?.action_state)||d?.opportunity_bucket==='NEXT_DAY_READY')return {tone:'go',label:'明日候選'};
    if(d?.action_state==='HOLD'||d?.lifecycle_stage==='TREND')return {tone:'go',label:'續抱觀察'};
    if(d?.action_state==='WAIT_PULLBACK'||['PULLBACK_TEST','PULLBACK_CONFIRMED'].includes(d?.lifecycle_stage))return {tone:'wait',label:'等回踩'};
    if(d?.action_state==='WAIT_TRIGGER')return {tone:'wait',label:'等觸發'};
    return {tone:'neutral',label:STAGE[d?.lifecycle_stage]||'觀察'};
  }
  function tomorrowAction(d,s,r,allowed){
    if(!allowed)return '資料未通過可執行檢查，不依這份快照開新倉。';
    const sv=zoneText(s),rv=zoneText(r),a=d?.action_state;
    if(a==='EXIT_PRIORITY')return s?`若仍無法站回 S1 ${sv}，優先處理風險。`:'結構已失效，明日優先處理風險。';
    if(a==='REDUCE_WATCH')return r?`反彈若過不了 R1 ${rv}，以分批降低部位為主。`:'反彈無法恢復結構時，以分批降低部位為主。';
    if(a==='ADD_ON_CONFIRM')return r?`站穩 R1 ${rv} 且量價延續，再考慮確認後加碼。`:'突破確認且量價延續後，再考慮加碼。';
    if(a==='SMALL_TEST')return s&&r?`回踩 S1 ${sv} 守住，或站穩 R1 ${rv} 後，再小量試單。`:s?`回踩 S1 ${sv} 守住再小量試單。`:r?`站穩 R1 ${rv} 後再小量試單。`:'只做確認後的小量試單，不追開高。';
    if(a==='WAIT_PULLBACK')return s?`等回踩 S1 ${sv} 守住、量價重新轉強再看。`:'等回踩止穩後再看，不先接刀。';
    if(a==='WAIT_TRIGGER')return r?`等站穩 R1 ${rv} 且回測不破再看。`:'等待觸發條件完成，不提前卡位。';
    if(a==='HOLD')return s?`S1 ${sv} 未有效跌破前以續抱觀察為主。`:'結構未破先續抱，不因單日震盪亂出。';
    if(a==='DO_NOT_CHASE')return s?`不追；等回到 S1 ${sv} 附近重新評估承接。`:'不追高，等回踩後再重新評估。';
    return (d?.blockers||[])[0]?`先處理卡點：${String(d.blockers[0])}`:'先觀察，等條件變得可量化再行動。';
  }
  function invalidation(d,s,allowed){
    if(!allowed)return '資料恢復最新且通過驗證前，不設定新的操作失效價。';
    if(s){
      const low=price(s.low??s.center);
      return `有效跌破 S1 ${low}：連續對應K收破，或跌破後反抽站不回且量價轉弱。`;
    }
    if(['FAILED','WEAKENING'].includes(d?.lifecycle_stage))return '結構已轉弱；反抽無法恢復原結構時，不把下跌當成加碼理由。';
    return '目前沒有可信 S1，不用固定百分比硬設假停損；等結構價建立後再判斷。';
  }
  function cardStrip(d){
    const g=closeGuard(),s=zoneFor(d,'SUPPORT'),r=zoneFor(d,'RESISTANCE'),c=conclusion(d,g.allowed),action=tomorrowAction(d,s,r,g.allowed),fail=invalidation(d,s,g.allowed);
    return `<div class="ahd-card-strip ${c.tone}" data-ahd-strip><div class="ahd-card-title"><span>犬子結論</span><b>${esc(c.label)}</b><em>${esc(ACTION[d?.action_state]||d?.action_state||'—')}</em></div><div class="ahd-card-action"><b>明日動作</b><span>${esc(action)}</span></div><div class="ahd-card-grid"><div><small>S1 支撐</small><strong>${esc(zoneText(s))}</strong></div><div><small>R1 壓力</small><strong>${esc(zoneText(r))}</strong></div></div><div class="ahd-card-fail"><b>失效條件</b><span>${esc(fail)}</span></div></div>`;
  }

  function mergeRows(rows){
    for(const d of Array.isArray(rows)?rows:[]){if(d?.code)rowMap.set(String(d.code),d)}
  }
  async function ensureIndexForMissing(){
    if(loadingIndex||closeIndex||!manifest)return;
    const cards=[...document.querySelectorAll('#cards .card[data-code]')];
    if(!cards.some(c=>!rowMap.has(String(c.dataset.code||''))))return;
    const meta=manifest.datasets?.decision_close_index;if(!meta)return;
    loadingIndex=true;
    try{closeIndex=await datasetFromManifest('decision_close_index');mergeRows(closeIndex);decorateCards()}
    catch(err){console.warn('afterhours decision index',err)}
    finally{loadingIndex=false}
  }
  async function ensureZones(){
    if(loadingZones||closeZones||!manifest)return;
    const meta=manifest.datasets?.zone_close;if(!meta)return;
    loadingZones=true;
    try{
      closeZones=await datasetFromManifest('zone_close');
      zoneMap=new Map((Array.isArray(closeZones)?closeZones:[]).filter(z=>z?.zone_id).map(z=>[String(z.zone_id),z]));
      decorateCards();
    }catch(err){console.warn('afterhours decision zones',err)}
    finally{loadingZones=false}
  }
  function decorateCards(){
    if(activeView()!=='close')return;
    const cards=[...document.querySelectorAll('#cards .card[data-code]')];
    for(const card of cards){
      card.querySelector('[data-ahd-strip]')?.remove();
      const d=rowMap.get(String(card.dataset.code||''));if(!d)continue;
      const holder=document.createElement('div');holder.innerHTML=cardStrip(d);const strip=holder.firstElementChild;
      const anchor=card.querySelector('.action-line')||card.querySelector('.quote-strip')||card.querySelector('.card-top');
      anchor?.insertAdjacentElement('afterend',strip);
    }
    ensureIndexForMissing();
    if(!closeZones){
      const idle=window.requestIdleCallback||((fn)=>setTimeout(fn,50));idle(()=>ensureZones());
    }
  }

  function normalizeScoreExplain(){
    const body=document.getElementById('detailBody');if(!body)return;
    const box=body.querySelector('.sdr-explain');if(!box)return;
    const summary=box.querySelector('summary'),inner=box.querySelector('.sdr-explain-body');if(!summary||!inner)return;
    const view=activeView();
    if(!['close','intraday','daytrade'].includes(view))return;
    summary.textContent='評分依據｜為什麼是這個分數';
    if(!inner.querySelector('[data-uf-reminder]')){
      const text=view==='close'?'分數代表條件同步程度，不代表上漲機率；明日動作仍以支撐／壓力、量價確認與資料新鮮度為準。':view==='daytrade'?'分數代表條件同步程度，不代表獲利機率；當沖只在同交易日、同快照資料有效時才可執行。':'分數代表條件同步程度，不代表上漲機率；盤中分數要搭配同一時間的價格、量能與支撐壓力判讀。';
      inner.insertAdjacentHTML('beforeend',`<div class="sdr-note" data-uf-reminder>${esc(text)}</div>`);
    }
  }

  function style(){
    if(document.getElementById('unifiedFreshnessStyleV2'))return;
    const s=document.createElement('style');s.id='unifiedFreshnessStyleV2';s.textContent=`
      .uf-panel{margin-top:10px}.uf-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.uf-head b{display:block;font-size:.9rem}.uf-head small{display:block;margin-top:3px;color:var(--muted);font-size:.69rem}.uf-refresh{border:0;background:transparent;color:var(--muted);font-size:.7rem;padding:4px;cursor:pointer}.uf-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:9px}.uf-card{border:1px solid var(--line);border-radius:11px;background:var(--soft);padding:8px;text-align:left;color:inherit}.uf-card.active{outline:2px solid color-mix(in srgb,var(--green) 48%,transparent)}.uf-card span,.uf-card strong,.uf-card em{display:block}.uf-card span{font-size:.68rem;color:var(--muted)}.uf-card strong{font-size:.82rem;margin:2px 0}.uf-card em{font-style:normal;font-size:.64rem}.uf-card em.same{color:var(--green)}.uf-card em.stale,.uf-ds b.stale{color:var(--red)}.uf-card em.unknown{color:var(--muted)}.uf-warning{margin-top:8px;padding:8px 9px;border-radius:9px;background:color-mix(in srgb,var(--red) 8%,var(--soft));font-size:.72rem;line-height:1.45}.uf-warning.hard{border:1px solid color-mix(in srgb,var(--red) 40%,var(--line));color:var(--red)}.uf-detail{margin-top:8px;border-top:1px dashed var(--line);padding-top:7px}.uf-detail summary{cursor:pointer;font-size:.72rem;font-weight:750}.uf-datasets{margin-top:6px}.uf-ds{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:7px;align-items:center;padding:4px 0;border-top:1px dashed var(--line);font-size:.64rem}.uf-ds:first-child{border-top:0}.uf-ds code{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted)}.uf-ds b{font-size:.62rem}.uf-bundle,.uf-schedule{margin-top:7px;color:var(--muted);font-size:.68rem;line-height:1.45}
      .ahd-market{margin:10px 0 3px;padding:12px;border:1px solid var(--line);border-radius:14px;background:var(--soft)}.ahd-market.go{border-left:4px solid var(--green)}.ahd-market.wait,.ahd-market.caution{border-left:4px solid #c7a44b}.ahd-market.risk,.ahd-market.blocked{border-left:4px solid var(--red)}.ahd-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.ahd-head span{display:block;font-size:.67rem;color:var(--muted)}.ahd-head b{display:block;margin-top:2px;font-size:1rem}.ahd-head em{font-style:normal;font-size:.66rem;padding:4px 7px;border-radius:999px;background:var(--card);white-space:nowrap}.ahd-main{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:10px}.ahd-main>div{padding:8px;border-radius:10px;background:var(--card)}.ahd-main small{display:block;color:var(--muted);font-size:.64rem}.ahd-main strong{display:block;margin-top:2px;font-size:.92rem}.ahd-summary{margin:10px 0 8px;font-size:.78rem;line-height:1.5}.ahd-rule{display:grid;grid-template-columns:42px 1fr;gap:7px;padding:7px 0;border-top:1px dashed var(--line);font-size:.72rem;line-height:1.45}.ahd-rule b{color:var(--muted)}.ahd-if{display:grid;gap:5px;margin-top:8px}.ahd-if>div{padding:7px 8px;border-radius:9px;background:var(--card);font-size:.68rem;line-height:1.45}.ahd-if b{margin-right:5px}.ahd-foot{margin-top:8px;color:var(--muted);font-size:.66rem}
      .ahd-card-strip{margin:9px 0;padding:10px;border:1px solid var(--line);border-radius:12px;background:color-mix(in srgb,var(--soft) 88%,transparent);text-align:left}.ahd-card-strip.go{border-left:4px solid var(--green)}.ahd-card-strip.wait{border-left:4px solid #c7a44b}.ahd-card-strip.risk,.ahd-card-strip.stale{border-left:4px solid var(--red)}.ahd-card-title{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.ahd-card-title span{font-size:.64rem;color:var(--muted)}.ahd-card-title b{font-size:.78rem}.ahd-card-title em{font-style:normal;font-size:.62rem;color:var(--muted);margin-left:auto}.ahd-card-action,.ahd-card-fail{display:grid;grid-template-columns:54px 1fr;gap:7px;margin-top:7px;font-size:.68rem;line-height:1.45}.ahd-card-action b,.ahd-card-fail b{color:var(--muted)}.ahd-card-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}.ahd-card-grid>div{padding:7px 8px;border-radius:9px;background:var(--card)}.ahd-card-grid small{display:block;font-size:.6rem;color:var(--muted)}.ahd-card-grid strong{display:block;margin-top:2px;font-size:.82rem}.ahd-card-fail{padding-top:7px;border-top:1px dashed var(--line)}
      @media(max-width:520px){.uf-card{padding:7px 6px}.uf-card strong{font-size:.75rem}.uf-ds{grid-template-columns:minmax(0,1fr) auto}.uf-ds b{grid-column:2}.ahd-main{grid-template-columns:1fr 1fr}.ahd-main>div:first-child{grid-column:1/-1}.ahd-card-title em{width:100%;margin-left:0}.ahd-card-action,.ahd-card-fail{grid-template-columns:48px 1fr}}
    `;document.head.appendChild(s);
  }

  function loadChipProvenance(){
    if(document.querySelector('script[data-chip-provenance]'))return;
    const s=document.createElement('script');s.src='./chip-freshness-provenance.js?v=20261002a';s.dataset.chipProvenance='1';document.head.appendChild(s);
  }

  async function load(force=false){
    const seq=++renderSeq;
    try{
      manifest=await getJson(`./data/current_manifest.json?uf=${Date.now()}`);
      if(seq!==renderSeq)return;
      closeContext=null;closeRows=[];closeIndex=null;closeZones=null;rowMap=new Map();zoneMap=new Map();
      const [ctx,rows]=await Promise.all([
        datasetFromManifest('market_close_context').catch(()=>null),
        datasetFromManifest('decision_close_summary').catch(()=>[])
      ]);
      if(seq!==renderSeq)return;
      closeContext=ctx;closeRows=Array.isArray(rows)?rows:[];mergeRows(closeRows);
      renderFreshness();renderMarketDecision();
      if(activeView()==='close')decorateCards();
      if(force)document.dispatchEvent(new CustomEvent('radar:afterhours-refresh',{detail:{build:manifest?.active_build_id}}));
    }catch(err){
      console.error('unified freshness v2',err);
      const host=ensureFreshnessPanel();if(host)host.innerHTML=`<div class="uf-warning hard">⛔ 無法驗證盤後資料：${esc(err.message||err)}。操作建議已停用。</div>`;
      window.DOGSON_CLOSE_DECISION_ALLOWED=false;
    }
  }
  function rerender(){
    renderFreshness();renderMarketDecision();normalizeScoreExplain();
    if(activeView()==='close')setTimeout(decorateCards,0);
  }
  function boot(){
    style();ensureFreshnessPanel();loadChipProvenance();load();
    document.getElementById('tabs')?.addEventListener('click',()=>setTimeout(rerender,0));
    document.addEventListener('radar:view-rendered',()=>setTimeout(rerender,0));
    document.addEventListener('radar:data-reloaded',()=>load(true));
    const cards=document.getElementById('cards');if(cards)new MutationObserver(()=>{if(activeView()==='close')setTimeout(decorateCards,0)}).observe(cards,{childList:true,subtree:false});
    const body=document.getElementById('detailBody');if(body)new MutationObserver(normalizeScoreExplain).observe(body,{childList:true,subtree:true});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
