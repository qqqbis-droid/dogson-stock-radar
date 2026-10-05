(()=>{
  if(window.__DOGSON_CLOSE_HEALTH_V1760__) return;
  window.__DOGSON_CLOSE_HEALTH_V1760__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const ymd=v=>{const m=String(v||'').match(/(20\d{2})-(\d{2})-(\d{2})/);return m?`${m[1]}-${m[2]}-${m[3]}`:''};
  const CLOSED_2026=new Set([
    '2026-01-01','2026-02-12','2026-02-13','2026-02-16','2026-02-17','2026-02-18','2026-02-19','2026-02-20',
    '2026-02-27','2026-04-03','2026-04-06','2026-05-01','2026-06-19','2026-09-25','2026-09-28','2026-10-09','2026-10-26','2026-12-25'
  ]);

  function modeNow(){try{return mode||'intraday'}catch{return'intraday'}}
  function portfolioView(){try{return!!portfolioOnly}catch{return false}}
  function taipeiClock(){
    const p={};
    try{new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).forEach(x=>{if(x.type!=='literal')p[x.type]=x.value})}catch{}
    return{today:p.year?`${p.year}-${p.month}-${p.day}`:'',weekday:p.weekday||'',minute:Number(p.hour||0)*60+Number(p.minute||0)};
  }
  function utcDate(s){const m=String(s||'').match(/^(\d{4})-(\d{2})-(\d{2})$/);return m?new Date(Date.UTC(+m[1],+m[2]-1,+m[3])):null}
  function fmtDate(d){return d?`${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`:''}
  function isTradingDay(s){const d=utcDate(s);if(!d)return false;const wd=d.getUTCDay();if(wd===0||wd===6)return false;if(s.startsWith('2026-')&&CLOSED_2026.has(s))return false;return true}
  function addDays(s,delta){const d=utcDate(s);if(!d)return'';d.setUTCDate(d.getUTCDate()+delta);return fmtDate(d)}
  function previousTradingDay(s,includeSelf=false){let x=includeSelf?s:addDays(s,-1);for(let i=0;i<15&&x;i++,x=addDays(x,-1)){if(isTradingDay(x))return x}return''}
  function expectedCompletedCloseDate(){
    const c=taipeiClock();if(!c.today)return'';
    if(isTradingDay(c.today)&&c.minute>=14*60)return c.today;
    return previousTradingDay(c.today,false);
  }
  function firstRowDate(){
    try{for(const r of (Array.isArray(closeRows)?closeRows.slice(0,80):[])){const d=ymd(r?.date)||ymd(r?.trade_date)||ymd(r?.quote_date)||ymd(r?.chip_date);if(d)return d}}catch{}
    return'';
  }
  function actualCloseDate(){
    const truth=ymd(window.DOGSON_DATA_TRUTH_V1700?.dates?.close);
    if(truth)return truth;
    try{return ymd(closeMarket?.trade_date)||ymd(closeMarket?.taiex?.date)||ymd(closeMarket?.updated_at)||firstRowDate()}catch{return firstRowDate()}
  }
  function strictState(){
    const expected=expectedCompletedCloseDate(),actual=actualCloseDate();
    let incomplete=false;try{incomplete=closeMarket?.data_complete===false}catch{}
    const future=!!(expected&&actual&&actual>expected);
    const stale=!actual||incomplete||future||!!(expected&&actual<expected);
    return{expected,actual,stale,missing:!actual,incomplete,future};
  }
  function publish(st){
    window.DOGSON_CLOSE_EXPECTED_DATE=st.expected;
    window.DOGSON_CLOSE_ACTUAL_DATE=st.actual;
    window.DOGSON_CLOSE_STRICT_STALE=st.stale;
    document.documentElement.dataset.dogsonCloseStale=st.stale?'1':'0';
  }

  function installStyle(){
    if($('#dogsonCloseHealthStyleV1760'))return;
    const s=document.createElement('style');s.id='dogsonCloseHealthStyleV1760';s.textContent=`
      .dogson-close-health-v1760{margin:9px 0 10px;padding:11px 12px;border-radius:14px;border:1px solid #dce4df;background:#fff;box-shadow:0 3px 14px rgba(34,51,43,.04)}
      .dogson-close-health-v1760.ok{border-color:#cfe1d7;background:#f3f8f5}.dogson-close-health-v1760.bad{border-color:#efc8cd;background:#fff2f3}
      .dogson-close-health-title-v1760{font-size:13px;font-weight:950;color:#28352f}.dogson-close-health-v1760.bad .dogson-close-health-title-v1760{color:#a93d49}
      .dogson-close-health-sub-v1760{margin-top:4px;font-size:10px;line-height:1.55;color:#728078}.dogson-close-health-v1760.bad .dogson-close-health-sub-v1760{color:#8f5960}
      .dogson-market-directive-v1760{margin-top:9px;padding:10px;border:1px solid #dbe4df;border-radius:12px;background:#f8faf8}
      .dogson-market-directive-v1760.blocked{border-color:#efc8cd;background:#fff3f4}.dogson-market-directive-head-v1760{font-size:10px;font-weight:900;color:#56645d}
      .dogson-market-directive-grid-v1760{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:7px}.dogson-market-directive-cell-v1760{padding:7px 8px;border-radius:10px;background:#fff;border:1px solid #e4e9e6;min-width:0}
      .dogson-market-directive-cell-v1760 span{display:block;font-size:8.5px;color:#829089}.dogson-market-directive-cell-v1760 b{display:block;margin-top:2px;font-size:10.5px;line-height:1.35;color:#2c3933}
      .dogson-market-directive-foot-v1760{margin-top:7px;font-size:9px;line-height:1.5;color:#728078}.dogson-market-directive-v1760.blocked .dogson-market-directive-foot-v1760{color:#a84a54;font-weight:850}
      .dogson-close-decision-v1760{margin:8px 0 10px;padding:10px;border:1px solid #d9e2dd;border-radius:13px;background:#fbfcfb}.dogson-close-decision-v1760.stale{border-color:#efc8cd;background:#fff4f5}
      .dogson-close-decision-top-v1760{display:flex;align-items:center;justify-content:space-between;gap:8px}.dogson-close-decision-kicker-v1760{font-size:9px;font-weight:900;color:#77847e}.dogson-close-decision-badge-v1760{font-size:11px;font-weight:950;color:#2a3832}.dogson-close-decision-v1760.stale .dogson-close-decision-badge-v1760{color:#b13f4a}
      .dogson-close-decision-grid-v1760{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin-top:8px}.dogson-close-decision-cell-v1760{padding:8px;border:1px solid #e4e9e6;border-radius:10px;background:#fff;min-width:0}
      .dogson-close-decision-label-v1760{font-size:8.5px;color:#87928d}.dogson-close-decision-value-v1760{margin-top:3px;font-size:10.5px;line-height:1.45;font-weight:900;color:#2c3933;word-break:break-word}
      .dogson-close-decision-note-v1760{margin-top:7px;font-size:8.8px;line-height:1.5;color:#7c8882}.dogson-close-decision-v1760.stale .dogson-close-decision-note-v1760{color:#a3535c;font-weight:800}
      html[data-dogson-theme="dark"] .dogson-close-health-v1760,html[data-dogson-theme="dark"] .dogson-market-directive-v1760,html[data-dogson-theme="dark"] .dogson-close-decision-v1760{background:#202622;border-color:#39433d;color:#eef2ef}
      html[data-dogson-theme="dark"] .dogson-close-health-v1760.bad,html[data-dogson-theme="dark"] .dogson-market-directive-v1760.blocked,html[data-dogson-theme="dark"] .dogson-close-decision-v1760.stale{background:#322326;border-color:#654149}
      html[data-dogson-theme="dark"] .dogson-market-directive-cell-v1760,html[data-dogson-theme="dark"] .dogson-close-decision-cell-v1760{background:#252c27;border-color:#3b453f}
      html[data-dogson-theme="dark"] .dogson-market-directive-cell-v1760 b,html[data-dogson-theme="dark"] .dogson-close-decision-value-v1760,html[data-dogson-theme="dark"] .dogson-close-health-title-v1760,html[data-dogson-theme="dark"] .dogson-close-decision-badge-v1760{color:#edf2ef}
      @media(max-width:430px){.dogson-market-directive-grid-v1760,.dogson-close-decision-grid-v1760{grid-template-columns:1fr 1fr}}
    `;document.head.appendChild(s);
  }

  function renderHealth(st){
    const shouldShow=modeNow()==='close'||portfolioView();
    let box=$('#dogsonCloseHealthV1760');
    const anchor=$('#dogsonDataTruthV1700')||$('#dogsonMissionV1700')||$('#dogsonViewNav')||$('.controls');
    if(!anchor)return;
    if(!box){box=document.createElement('section');box.id='dogsonCloseHealthV1760';anchor.after(box)}
    box.style.display=shouldShow?'block':'none';if(!shouldShow)return;
    box.className=`dogson-close-health-v1760 ${st.stale?'bad':'ok'}`;
    const title=st.stale?'⛔ 盤後資料過期｜禁止據此下單':'✅ 盤後資料日期正常';
    const sub=st.stale
      ?`目前盤後資料：${st.actual||'無日期'}｜依台北時間與 TWSE 2026 開休市日曆，應有：${st.expected||'待確認'}。市場分數、個股結論與關鍵價全部降級為歷史參考，資料追上後自動解除。`
      :`目前盤後資料：${st.actual||'—'}｜應有最新完成交易日：${st.expected||'—'}。可進入下一層市場與個股決策。`;
    const html=`<div class="dogson-close-health-title-v1760">${esc(title)}</div><div class="dogson-close-health-sub-v1760">${esc(sub)}</div>`;
    if(box.dataset.h!==html){box.innerHTML=html;box.dataset.h=html}
  }

  function closeMarketData(){try{return closeMarket||{}}catch{return{}}}
  function marketPlan(st){
    const m=closeMarketData(),score=num(m.market_score),state=String(m.market_mode||'中性');
    const ta=num(m?.taiex?.change_pct),ot=num(m?.otc?.change_pct);
    const otcWeak=ta!==null&&ot!==null&&ot<=ta-.4;
    const otcStrong=ta!==null&&ot!==null&&ot>=ta+.4;
    if(st.stale)return{blocked:true,regime:'歷史資料',holding:'禁止依此調整持股',entry:'禁止開新倉',chase:'禁止追價',relative:'等待最新完成交易日資料'};
    let holding='50–65%',entry='新倉只做回踩／突破後回測',chase='突破需量價確認';
    if(state.includes('防守')||(score!==null&&score<6)){holding='30–45%';entry='原則上暫停新倉；只做最強回踩';chase='禁止追突破'}
    else if(score!==null&&score<8){holding='40–55%';entry='只做支撐回踩、小量試單';chase='不追突破'}
    else if(score!==null&&score>=10.5){holding='60–75%';entry='可開新倉，但分批且優先強族群';chase='不追離支撐過遠'}
    if(otcWeak){const map={'60–75%':'55–70%','50–65%':'45–60%','40–55%':'35–50%'};holding=map[holding]||holding;chase='禁止追突破'}
    const relative=otcWeak?'櫃買弱於加權｜中小型股門檻提高':otcStrong?'櫃買強於加權｜中小型股相對有利':'加權／櫃買未明顯背離';
    return{blocked:false,regime:state+(score!==null?`｜${score.toFixed(1)}/15`:''),holding,entry,chase,relative};
  }
  function renderMarketDirective(st){
    const host=$('#dogsonMarketHomeV1685');if(!host)return;
    let box=$('#dogsonMarketDirectiveV1760',host);
    if(!box){box=document.createElement('section');box.id='dogsonMarketDirectiveV1760';const anchor=$('.dogson-market-callout-v1685',host)||$('.dogson-layer-head-v1685',host);anchor?.after(box)}
    if(!box)return;
    const p=marketPlan(st);box.className=`dogson-market-directive-v1760 ${p.blocked?'blocked':''}`;
    const html=`<div class="dogson-market-directive-head-v1760">🧭 犬子明日操作指令</div><div class="dogson-market-directive-grid-v1760"><div class="dogson-market-directive-cell-v1760"><span>市場</span><b>${esc(p.regime)}</b></div><div class="dogson-market-directive-cell-v1760"><span>建議持股</span><b>${esc(p.holding)}</b></div><div class="dogson-market-directive-cell-v1760"><span>新倉</span><b>${esc(p.entry)}</b></div><div class="dogson-market-directive-cell-v1760"><span>追價</span><b>${esc(p.chase)}</b></div></div><div class="dogson-market-directive-foot-v1760">${esc(p.relative)}${p.blocked?'｜本區只保留歷史脈絡，不提供交易指令。':''}</div>`;
    if(box.dataset.h!==html){box.innerHTML=html;box.dataset.h=html}
    if(st.stale&&modeNow()==='close'){
      const score=$('.dogson-market-score-v1685',host);if(score){const b=$('b',score),span=$('span',score);if(b&&b.textContent!=='歷史')b.textContent='歷史';if(span&&span.textContent!=='市場分數已停用')span.textContent='市場分數已停用'}
      const state=$('.dogson-market-state-v1685',host);if(state&&state.textContent!=='⛔ 歷史市場環境')state.textContent='⛔ 歷史市場環境';
    }
  }

  function codeOf(card){return String(card?.dataset?.code||$('.code',card)?.textContent||'').match(/\d{4}/)?.[0]||''}
  function closeRow(code){try{return(Array.isArray(closeRows)?closeRows:[]).find(r=>String(r?.code)===String(code))||null}catch{return null}}
  function heldNow(code){try{return typeof held==='function'&&held(code)}catch{return false}}
  function stageOf(r){
    try{if(typeof stageKey==='function')return String(stageKey(r?.category)||r?.category||'觀察')}catch{}
    return String(r?.category||'觀察');
  }
  function px(v){const n=num(v);if(n===null)return'—';return n>=1000?n.toFixed(0):n>=100?n.toFixed(1):n.toFixed(2)}
  function zone(x){
    if(!x)return'';const lo=num(x.low??x.min??x.price),hi=num(x.high??x.max??x.price);
    if(lo===null&&hi===null)return'';if(lo!==null&&hi!==null&&Math.abs(lo-hi)>1e-9)return`${px(Math.min(lo,hi))}～${px(Math.max(lo,hi))}`;return px(lo??hi)
  }
  function cardDecision(r,st,heldFlag){
    const stage=stageOf(r),score=num(r?.swing_quality_score??r?.score),entry=num(r?.entry_position_score);
    const support=zone(r?.support),resistance=zone(r?.resistance),supportLow=num(r?.support?.low??r?.support?.min??r?.support?.price),ma20=num(r?.ma20);
    const key=[support?`支撐 ${support}`:'',resistance?`壓力 ${resistance}`:''].filter(Boolean).join('｜')||`20MA ${px(ma20)}`;
    const invalid=supportLow!==null?`有效跌破 ${px(supportLow)}＋回抽不過 → 失效`:ma20!==null?`有效跌破 20MA ${px(ma20)}＋回抽不過 → 失效`:'收盤／連續K確認轉弱後才退出';
    if(st.stale)return{badge:'⛔ 歷史資料｜禁下單',action:`等待資料更新到 ${st.expected||'最新交易日'}`,key:key||'歷史支撐壓力',invalid:'僅供歷史參考，不作停損／加碼依據'};
    let badge='觀察｜等待條件',action='先觀察，不主動出手';
    if(/結構失效|失效/.test(stage)){badge=heldFlag?'❌ 結構失效｜準備退出':'❌ 結構失效｜不接';action=heldFlag?'依有效跌破確認執行減碼／退出':'不開新倉'}
    else if(/轉弱/.test(stage)){badge=heldFlag?'⚠️ 減碼警戒':'⚠️ 先不進';action=heldFlag?'停止加碼；守關鍵支撐':'等重新站回關鍵結構'}
    else if(/過熱/.test(stage)){badge=heldFlag?'✅ 續抱觀察｜不加碼':'🚫 趨勢強｜不追';action='等回踩支撐／均線後再評估'}
    else if(/回踩/.test(stage)){badge=heldFlag?'✅ 續抱看支撐':'🟡 回踩承接｜可等確認';action='支撐區守住且量價轉強，可小量試'}
    else if(/趨勢|持有/.test(stage)){badge=heldFlag?'✅ 續抱':'🚂 強勢但新倉不追';action=heldFlag?'主要支撐上方不動':'等回踩或突破後回測'}
    else if(/剛啟動|啟動/.test(stage)){badge=heldFlag?'🔥 續抱看發動':'🔥 剛啟動｜等確認';action='回踩不破可試；突破壓力需量能確認'}
    else if(/蓄勢/.test(stage)){badge='🌱 可蹲｜等突破';action='支撐上方蹲守；突破壓力再加分'}
    else if(score!==null&&score>=75&&entry!==null&&entry>=65){badge='🟢 優先觀察';action='只在合理位置分批，不追離支撐過遠'}
    return{badge,action,key:key||'支撐／壓力待補',invalid};
  }
  function renderCards(st){
    if(modeNow()!=='close'){$$('.dogson-close-decision-v1760').forEach(x=>x.remove());return}
    $$('.card').forEach(card=>{
      const code=codeOf(card),r=closeRow(code);if(!code||!r)return;
      const d=cardDecision(r,st,heldNow(code));let box=$('.dogson-close-decision-v1760',card);
      if(!box){box=document.createElement('section');box.className='dogson-close-decision-v1760';const anchor=$('.dogson-card-brief',card)||$('.dogson-dual-decision',card)||$('.top',card);anchor?.after(box)}
      if(!box)return;box.className=`dogson-close-decision-v1760 ${st.stale?'stale':''}`;
      const html=`<div class="dogson-close-decision-top-v1760"><div class="dogson-close-decision-kicker-v1760">犬子結論 → 明日動作 → 關鍵價 → 失效條件</div><div class="dogson-close-decision-badge-v1760">${esc(d.badge)}</div></div><div class="dogson-close-decision-grid-v1760"><div class="dogson-close-decision-cell-v1760"><div class="dogson-close-decision-label-v1760">明日動作</div><div class="dogson-close-decision-value-v1760">${esc(d.action)}</div></div><div class="dogson-close-decision-cell-v1760"><div class="dogson-close-decision-label-v1760">關鍵價</div><div class="dogson-close-decision-value-v1760">${esc(d.key)}</div></div><div class="dogson-close-decision-cell-v1760"><div class="dogson-close-decision-label-v1760">失效條件</div><div class="dogson-close-decision-value-v1760">${esc(d.invalid)}</div></div><div class="dogson-close-decision-cell-v1760"><div class="dogson-close-decision-label-v1760">資料層級</div><div class="dogson-close-decision-value-v1760">${st.stale?`歷史參考｜${st.actual||'無日期'}`:`正式盤後｜${st.actual||'—'}`}</div></div></div><div class="dogson-close-decision-note-v1760">停損採「有效跌破」：收盤或連續K確認、回抽不過，再配合量價與大盤，不因單根急殺直接砍。</div>`;
      if(box.dataset.h!==html){box.innerHTML=html;box.dataset.h=html}
    })
  }

  let pending=false;
  function apply(){
    if(pending)return;pending=true;
    requestAnimationFrame(()=>{pending=false;installStyle();const st=strictState();publish(st);renderHealth(st);renderMarketDirective(st);renderCards(st);try{window.dispatchEvent(new CustomEvent('dogson:close-health',{detail:st}))}catch{}})
  }
  function start(){
    installStyle();apply();
    const obs=new MutationObserver(()=>apply());obs.observe(document.body,{childList:true,subtree:true});
    window.addEventListener('dogson:data-ready',apply);window.addEventListener('dogson:data-truth',apply);window.addEventListener('dogson:freshness',apply);window.addEventListener('dogson:ui-ready',apply);
    document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav,#portfolioOnly'))setTimeout(apply,50)});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)apply()});
    setInterval(()=>{if(!document.hidden)apply()},60000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
