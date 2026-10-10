(()=>{
  'use strict';

  const nativeFetch=window.fetch.bind(window);
  const cache=new Map();
  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const shortDate=v=>{
    const s=String(v||'').slice(0,10);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(s))return '—';
    const [,m,d]=s.split('-');
    return `${Number(m)}/${Number(d)}`;
  };
  const checkedStamp=v=>{
    if(!v)return '—';
    const d=new Date(v);
    if(Number.isNaN(d.getTime()))return String(v);
    return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  };
  const isoDate=v=>String(v||'').slice(0,10);
  const sourceDates=e=>[
    ['外資',e?.foreign_date],
    ['投信',e?.trust_date],
    ['借券',e?.sbl_date],
    ['融資',e?.margin_date],
  ];

  async function getShard(build,view,code){
    const key=`${build}:${view}:${code}`;
    if(cache.has(key))return cache.get(key);
    const url=`./data/builds/${encodeURIComponent(build)}/stock-shards/${encodeURIComponent(view)}/${encodeURIComponent(code)}.json?t=${Date.now()}`;
    const r=await nativeFetch(url,{cache:'no-store',credentials:'same-origin'});
    if(!r.ok)throw new Error(`HTTP ${r.status}`);
    const obj=await r.json();
    cache.set(key,obj);
    return obj;
  }

  function sourceSummary(e){
    return sourceDates(e).map(([k,v])=>`${k} ${v?shortDate(v):'—'}`).join(' · ');
  }

  function aggregateDateLabel(e){
    const dates=[...new Set(sourceDates(e).map(([,v])=>isoDate(v)).filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x)))].sort();
    if(!dates.length){
      const fallback=e?.chip_date;
      return {label:shortDate(fallback),mixed:false,latest:isoDate(fallback),complete:false};
    }
    if(dates.length===1)return {label:shortDate(dates[0]),mixed:false,latest:dates[0],complete:sourceDates(e).every(([,v])=>!!v)};
    return {label:`${shortDate(dates[0])}–${shortDate(dates[dates.length-1])}`,mixed:true,latest:dates[dates.length-1],complete:false};
  }

  function stateFor(e,baseDate){
    const checked=e?.chip_checked_at||null;
    const health=String(e?.chip_check_health||'').toUpperCase();
    const sources=sourceDates(e);
    const known=sources.filter(([,v])=>!!v).map(([,v])=>isoDate(v));
    const current=known.filter(x=>x===baseDate).length;
    const allFourKnown=known.length===sources.length;

    if(!checked)return ['⚠️ 尚未重新檢查','warn'];
    if(health==='ERROR')return ['❌ 籌碼更新失敗','error'];
    if(allFourKnown&&current===sources.length&&health!=='PARTIAL')return ['✅ 當日籌碼已更新','ok'];
    if(current>0)return ['🟡 當日籌碼部分更新','warn'];
    if(health==='PARTIAL')return ['⚠️ 已檢查，部分來源異常','warn'];
    if(isoDate(checked)&&baseDate&&isoDate(checked)>=baseDate)return ['⏳ 已檢查，當日籌碼尚未發布','wait'];
    return ['⚠️ 尚未重新檢查','warn'];
  }

  function enhance(shard){
    const e=shard?.evidence||{};
    const strip=document.querySelector('#detailBody .isd-fresh-strip');
    if(!strip)return;
    strip.querySelector('.isd-chip-provenance')?.remove();

    const agg=aggregateDateLabel(e);
    const baseDate=isoDate(shard?.as_of)||isoDate(e?.quote_date)||isoDate(shard?.decision?.as_of);
    const sourceStale=!!(agg.latest&&baseDate&&agg.latest!==baseDate);
    const warn=sourceStale||agg.mixed||!agg.complete;
    const firstLine=strip.querySelector('.isd-fresh-line');
    if(firstLine){
      const spans=firstLine.querySelectorAll('span');
      if(spans.length>=3){
        spans[2].classList.toggle('stale',warn);
        spans[2].innerHTML=`籌碼資料日 <b>${esc(agg.label)}</b>${warn?' ⚠️':''}`;
      }
    }

    const [label,tone]=stateFor(e,baseDate);
    const sourceText=sourceSummary(e);
    const box=document.createElement('div');
    box.className='isd-chip-provenance';
    box.style.cssText='margin-top:7px;padding-top:7px;border-top:1px dashed var(--line);font-size:.68rem;line-height:1.55;color:var(--muted)';
    const toneStyle=tone==='error'?'color:var(--red);font-weight:800':tone==='ok'?'color:var(--green);font-weight:800':'font-weight:800';
    box.innerHTML=`<div><span>最後檢查 <b style="color:var(--text)">${esc(checkedStamp(e.chip_checked_at))}</b></span> · <span style="${toneStyle}">${esc(label)}</span></div><div>${esc(sourceText)}</div><div style="margin-top:3px">「資料日」＝來源資料本身的交易日；「最後檢查」＝系統實際去查來源的時間，兩者不互相代替。若各來源日期不同，資料日會顯示日期範圍。</div>`;
    strip.appendChild(box);
  }

  document.addEventListener('radar:detail-rendered',async ev=>{
    try{
      const code=String(ev.detail?.code||'');
      const view=String(ev.detail?.view||'');
      const build=String(ev.detail?.build||'');
      if(!code||!view||!build)return;
      const shard=await getShard(build,view,code);
      const dialog=document.getElementById('detailDialog');
      if(!dialog?.open)return;
      enhance(shard);
    }catch(err){
      console.warn('chip-freshness-provenance',err);
    }
  });

  document.addEventListener('radar:data-reloaded',()=>cache.clear());
})();

(()=>{
  'use strict';
  if(window.__INUKO_STRICT_CLOSE_DATE_GUARD_V1__)return;
  window.__INUKO_STRICT_CLOSE_DATE_GUARD_V1__=true;

  const CLOSED_2026=new Set([
    '2026-01-01','2026-02-12','2026-02-13','2026-02-16','2026-02-17','2026-02-18','2026-02-19','2026-02-20',
    '2026-02-27','2026-04-03','2026-04-06','2026-05-01','2026-06-19','2026-09-25','2026-09-28','2026-10-09','2026-10-26','2026-12-25'
  ]);
  let state={checked:false,stale:false,actual:'',expected:''};
  let timer=null,checking=false;
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const ymd=v=>String(v||'').match(/20\d{2}-\d{2}-\d{2}/)?.[0]||'';
  const activeView=()=>$('.tab.active')?.dataset?.view||'intraday';
  const setText=(el,text)=>{if(el&&el.textContent!==text)el.textContent=text};
  const setHTML=(el,html)=>{if(el&&el.innerHTML!==html)el.innerHTML=html};

  function clock(){
    const p={};
    try{new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).forEach(x=>{if(x.type!=='literal')p[x.type]=x.value})}catch{}
    return{today:p.year?`${p.year}-${p.month}-${p.day}`:'',minute:Number(p.hour||0)*60+Number(p.minute||0)};
  }
  function utcDate(s){const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})$/);return m?new Date(Date.UTC(+m[1],+m[2]-1,+m[3])):null}
  function fmtDate(d){return d?`${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`:''}
  function addDays(s,n){const d=utcDate(s);if(!d)return'';d.setUTCDate(d.getUTCDate()+n);return fmtDate(d)}
  function isTradingDay(s){const d=utcDate(s);if(!d)return false;const w=d.getUTCDay();if(w===0||w===6)return false;return !CLOSED_2026.has(s)}
  function previousTradingDay(s){let x=addDays(s,-1);for(let i=0;i<20&&x;i++,x=addDays(x,-1)){if(isTradingDay(x))return x}return''}
  function expectedCloseDate(){const c=clock();if(!c.today)return'';if(isTradingDay(c.today)&&c.minute>=14*60)return c.today;return previousTradingDay(c.today)}
  function actualCloseDate(m){return ymd(m?.datasets?.decision_close_summary?.as_of)||ymd(m?.datasets?.market_close_context?.as_of)||ymd(m?.trade_date)}

  function installStyle(){
    if($('#inukoStrictCloseStyle'))return;
    const s=document.createElement('style');s.id='inukoStrictCloseStyle';s.textContent=`
      .inuko-strict-close-warning{margin:8px 0;padding:9px 10px;border:1px solid color-mix(in srgb,var(--red) 45%,var(--line));border-radius:10px;background:color-mix(in srgb,var(--red) 9%,var(--soft));color:var(--red);font-size:.72rem;line-height:1.5;font-weight:800}
      html[data-inuko-close-stale="1"] #marketSummary .market-grid{opacity:.62}
      html[data-inuko-close-stale="1"] #radarSummary{opacity:.65}
      html[data-inuko-close-stale="1"] #cards .card>.action-line{opacity:.55}
    `;document.head.appendChild(s);
  }

  function publish(){
    const previous=window.DOGSON_CLOSE_DATA_STATUS||{};
    // Strict calendar checks must never re-enable trading while the Atomic
    // context validator still reports errors, or vice versa.
    const mergedAllowed=!state.stale&&!(Array.isArray(previous.reasons)&&previous.reasons.length);
    window.DOGSON_CLOSE_DECISION_ALLOWED=mergedAllowed;
    window.DOGSON_CLOSE_DATA_STATUS={...previous,allowed:mergedAllowed,strictExpectedDate:state.expected,strictActualDate:state.actual,strictStale:state.stale};
    document.documentElement.dataset.inukoCloseStale=state.stale?'1':'0';
  }

  function warningHost(){
    const host=$('#unifiedFreshness');if(!host)return;
    let w=$('[data-inuko-strict-close-warning]',host);
    if(!state.stale){w?.remove();return}
    if(!w){w=document.createElement('div');w.dataset.inukoStrictCloseWarning='1';w.className='uf-warning hard inuko-strict-close-warning';const head=$('.uf-head',host);head?.insertAdjacentElement('afterend',w)}
    setText(w,`⛔ 盤後不可執行：目前盤後資料 ${state.actual||'無日期'}，最新應完成交易日為 ${state.expected||'待確認'}。禁止據此下單；市場分數、明日策略、個股結論與關鍵價只供歷史參考。`);
    $$('.uf-card',host).forEach(card=>{
      if(card.querySelector('span')?.textContent?.trim()!=='盤後')return;
      const em=card.querySelector('em');if(em){em.className='stale';setText(em,`資料過期｜應為 ${state.expected.slice(5).replace('-','/')}`)}
    });
  }

  function statusBox(){
    if(!state.stale||activeView()!=='close')return;
    const box=$('#statusBox');if(!box)return;
    const html=`<b>${state.actual||'—'}</b><br><span>盤後</span><br><small style="color:var(--red);font-weight:800">⛔ 資料過期</small>`;
    setHTML(box,html);
  }

  function marketSummary(){
    if(!state.stale||activeView()!=='close')return;
    const box=$('#marketSummary');if(box){
      $$('.metric',box).forEach(cell=>{
        const label=cell.querySelector('span')?.textContent?.trim(),b=cell.querySelector('b');if(!b)return;
        if(label==='市場環境')setText(b,'歷史參考');
        if(label==='市場分')setHTML(b,'—<small>/15</small>');
        if(label==='資料信心')setHTML(b,'—<small>%</small>');
      });
      const fresh=$('.data-line .fresh',box);if(fresh){fresh.className='fresh stale';setText(fresh,`過期｜${state.actual}`)}
    }
    const pulse=$('#marketPulse');if(pulse){
      $$(':scope>div',pulse).forEach(cell=>{
        const label=cell.querySelector('span')?.textContent?.trim(),b=cell.querySelector('b');
        if(label==='市場'&&b)setText(b,'歷史資料');
        if(label==='環境分'&&b)setText(b,'—/15');
      });
      const t=$('.pulse-time span',pulse);if(t)setText(t,`⛔ 盤後 ${state.actual}｜應為 ${state.expected}`);
    }
  }

  function strategy(){
    if(!state.stale||activeView()!=='close')return;
    const box=$('#afterhoursDecision');if(!box)return;
    box.classList.remove('go','wait','caution','risk');box.classList.add('blocked');
    const head=$('.ahd-head',box);if(head){setText(head.querySelector('b'),'歷史參考');setText(head.querySelector('em'),'⛔ 僅供歷史參考')}
    const main=$$('.ahd-main>div',box);if(main[0])setText(main[0].querySelector('strong'),'—');if(main[1])setText(main[1].querySelector('strong'),'—');if(main[2])setText(main[2].querySelector('strong'),'—');
    setText($('.ahd-summary',box),`盤後資料仍停在 ${state.actual}，但最新應完成交易日是 ${state.expected}；本區只保留歷史脈絡，不提供明日持股水位或進場建議。`);
    $$('.ahd-rule',box).forEach(row=>{const k=row.querySelector('b')?.textContent?.trim(),v=row.querySelector('span');if(k==='新倉')setText(v,'禁止依這份舊資料開新倉');if(k==='追價')setText(v,'禁止把舊快照當成追價依據')});
    const iff=$('.ahd-if',box);if(iff)setHTML(iff,`<div><b>恢復條件 →</b>資料更新至 ${state.expected}，且同一 Atomic Build／同交易日／驗證通過後，自動恢復操作建議。</div>`);
  }

  function cards(){
    if(!state.stale||activeView()!=='close')return;
    $$('[data-ahd-strip]').forEach(strip=>{
      strip.classList.remove('go','wait','risk');strip.classList.add('stale');
      setText($('.ahd-card-title b',strip),'僅供歷史參考');setText($('.ahd-card-title em',strip),'資料失效');
      setText($('.ahd-card-action span',strip),`資料未更新至 ${state.expected}，不依這份 ${state.actual} 快照開新倉、加碼或減碼。`);
      setText($('.ahd-card-fail span',strip),'資料恢復最新且通過驗證前，不設定新的操作失效價；S1／R1 僅供歷史位置參考。');
    });
    const title=$('#rankingTitle');if(title)setText(title,'盤後歷史名單｜禁止據此下單');
  }

  function apply(){
    installStyle();publish();
    if(!state.stale||activeView()!=='close')return;
    warningHost();statusBox();marketSummary();strategy();cards();
  }
  function schedule(ms=40){clearTimeout(timer);timer=setTimeout(apply,ms)}
  async function check(){
    if(checking)return;checking=true;
    try{
      const r=await fetch(`./data/current_manifest.json?strictClose=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(`HTTP ${r.status}`);
      const m=await r.json(),expected=expectedCloseDate(),actual=actualCloseDate(m);
      state={checked:true,actual,expected,stale:!!(expected&&(!actual||actual!==expected))};publish();schedule(0);
    }catch(err){console.warn('INUKO strict close-date guard',err);state={...state,checked:true,stale:true};publish();schedule(0)}finally{checking=false}
  }

  function boot(){
    installStyle();check();
    document.addEventListener('radar:data-reloaded',()=>check());
    document.addEventListener('radar:view-rendered',()=>schedule(20));
    document.addEventListener('radar:afterhours-refresh',()=>check());
    document.getElementById('tabs')?.addEventListener('click',()=>setTimeout(()=>{schedule(0);if(activeView()==='close')check()},60));
    const roots=['unifiedFreshness','marketSummary','afterhoursDecision','cards','marketPulse'].map(id=>document.getElementById(id)).filter(Boolean);
    const obs=new MutationObserver(()=>schedule(25));roots.forEach(x=>obs.observe(x,{childList:true,subtree:true}));
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)check()});
    setInterval(()=>{if(!document.hidden)check()},120000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
