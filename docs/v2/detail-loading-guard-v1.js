(()=>{
  'use strict';

  let token=0;
  let current={code:'',view:''};
  let manifestCache=null;
  const summaryCache=new Map();
  const timers=new Set();
  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[m]));
  const num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
  const fmt=(v,d=1)=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
  const stage={OBSERVE:'觀察',SETUP:'蓄勢待發',LAUNCH:'剛啟動',TREND:'趨勢持有',PULLBACK_TEST:'回踩觀察',PULLBACK_CONFIRMED:'回踩承接',WEAKENING:'轉弱警戒',FAILED:'結構失效'};
  const action={WATCH:'觀察',WAIT_TRIGGER:'等觸發',SMALL_TEST:'小量試單候選',WAIT_PULLBACK:'等回踩',HOLD:'續抱',ADD_ON_CONFIRM:'確認後加碼候選',DO_NOT_CHASE:'過熱不追',REDUCE_WATCH:'減碼觀察',EXIT_PRIORITY:'優先出場',DATA_STALE:'資料失效'};
  const summaryKey={intraday:'decision_intraday_summary',close:'decision_close_summary',daytrade:'decision_daytrade_summary'};

  function clearTimers(){for(const id of timers)clearTimeout(id);timers.clear()}
  function later(fn,ms){const id=setTimeout(()=>{timers.delete(id);fn()},ms);timers.add(id);return id}
  function body(){return document.getElementById('detailBody')}
  function dialog(){return document.getElementById('detailDialog')}
  function title(){return document.getElementById('detailTitle')}
  function cardFor(code){
    return [...document.querySelectorAll('#cards .card[data-code]')].find(x=>String(x.dataset.code||'').trim()===String(code||'').trim())||null;
  }
  function active(mine){return mine===token&&dialog()?.open}
  async function getJson(url,timeoutMs=4500){
    const ctl=new AbortController();
    const id=setTimeout(()=>ctl.abort(),timeoutMs);
    try{
      const r=await fetch(url,{cache:'no-store',signal:ctl.signal});
      if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);
      return await r.json();
    }finally{clearTimeout(id)}
  }
  async function manifest(){
    if(manifestCache)return manifestCache;
    manifestCache=await getJson(`./data/current_manifest.json?t=${Date.now()}`,3500);
    return manifestCache;
  }
  async function summary(view){
    const m=await manifest();
    const key=summaryKey[view]||summaryKey.intraday;
    const ck=`${m.active_build_id}:${key}`;
    if(summaryCache.has(ck))return {m,rows:summaryCache.get(ck)};
    const meta=m.datasets?.[key];
    if(!meta?.url)throw new Error(`missing ${key}`);
    const rows=await getJson(meta.url,5000);
    if(!Array.isArray(rows))throw new Error(`${key} is not array`);
    summaryCache.set(ck,rows);
    return {m,rows};
  }
  function initialHtml(code,view){
    const label=view==='close'?'盤後':view==='daytrade'?'當沖':'盤中';
    return `<div class="dlg-fast-core" data-detail-fast-core="1">
      <div class="dlg-fast-note"><b>${esc(code)} 核心詳情</b><span>先顯示目前卡片；正在讀取輕量核心資料。</span><small>${esc(label)}資料只採同一 Atomic Build，不跨日補猜。</small></div>
      <div class="dlg-fast-card-host"></div>
    </div>`;
  }
  function showImmediate(code,view){
    const b=body(),d=dialog();
    if(!b||!d?.open||!b.querySelector('.detail-loading'))return;
    b.innerHTML=initialHtml(code,view);
    const host=b.querySelector('.dlg-fast-card-host');
    const src=cardFor(code);
    if(host&&src){
      const clone=src.cloneNode(true);
      clone.removeAttribute('role');clone.removeAttribute('tabindex');clone.removeAttribute('aria-label');clone.removeAttribute('data-code');
      clone.classList.add('dlg-fast-card');clone.style.pointerEvents='none';host.appendChild(clone);
    }else if(host){
      host.innerHTML='<div class="detail-note">正在讀取這檔股票的核心資料…</div>';
    }
  }
  function listBlock(label,items,empty='目前沒有額外資料。'){
    const xs=[...new Set((items||[]).filter(Boolean).map(String))];
    return `<div class="detail-block"><h3>${esc(label)}</h3><div class="detail-list">${xs.length?xs.map(x=>`<span>${esc(x)}</span>`).join(''):`<span class="muted">${esc(empty)}</span>`}</div></div>`;
  }
  function scoreValue(row,view){
    const s=row?.scores||{};
    if(view==='close')return ['波段品質',s.swing_quality_score];
    if(view==='daytrade')return ['當沖分',s.daytrade_score];
    return ['盤中動能',s.intraday_momentum_score];
  }
  function tone(row){
    if(['EXIT_PRIORITY','REDUCE_WATCH'].includes(row?.action_state)||['FAILED','WEAKENING'].includes(row?.lifecycle_stage))return ['risk','風險優先'];
    if(row?.actionable)return ['go','可執行'];
    return ['wait','先等待'];
  }
  function summaryHtml(row,view,m){
    const [scoreLabel,score]=scoreValue(row,view),[heroTone,heroLabel]=tone(row),s=row.scores||{};
    const why=row.why_now||[],block=row.blockers||[],up=row.upgrade_conditions||[],risks=row.risk_overlays||[];
    return `<div class="dlg-fast-core" data-detail-fast-core="1" data-build="${esc(m.active_build_id||'')}">
      <div class="sdr-context">${view==='close'?'盤後波段':view==='daytrade'?'當沖':'盤中波段'}核心詳情 · ${esc(row.opportunity_bucket||'—')} · 排名 #${esc(row.opportunity_rank??'—')}</div>
      <div class="detail-hero"><div><span class="badge stage">${esc(stage[row.lifecycle_stage]||row.lifecycle_stage||'—')}</span><h2>${esc(action[row.action_state]||row.action_state||'—')}</h2><p>核心資料已載入；支撐壓力與技術／籌碼證據正在背景補齊。</p></div><div class="detail-light ${heroTone}">${esc(heroLabel)}</div></div>
      <div class="sdr-quick"><div><span>${esc(scoreLabel)}</span><b>${fmt(score)}</b></div><div><span>進場位置</span><b>${fmt(s.entry_position_score)}</b></div><div><span>資料信心</span><b>${fmt(row.data_confidence,0)}%</b></div></div>
      ${listBlock('為什麼現在看它',why,'目前沒有新增理由。')}
      ${listBlock('現在卡在哪裡',block,'目前沒有額外卡點。')}
      ${up.length?listBlock(view==='close'?'明日升級條件':'升級條件',up):''}
      ${risks.length?listBlock('風險旗標',risks):''}
      <div class="dlg-fast-note compact"><b>完整詳情背景載入中</b><span>核心畫面不再等待大型全市場 JSON；完整層完成後會自動替換。</span></div>
    </div>`;
  }
  async function loadFastCore(code,view,mine){
    try{
      const {m,rows}=await summary(view);
      if(!active(mine))return;
      const row=rows.find(x=>String(x?.code||'').trim()===code);
      if(!row)return;
      if(row.build_id&&row.build_id!==m.active_build_id)return;
      const b=body();
      if(!b)return;
      if(!b.querySelector('.detail-loading')&&!b.querySelector('[data-detail-fast-core]'))return;
      const t=title();if(t)t.textContent=`${row.code} ${row.name||''}`.trim();
      b.innerHTML=summaryHtml(row,view,m);
    }catch(err){
      console.warn('detail fast core',err);
      if(!active(mine))return;
      const note=body()?.querySelector('.dlg-fast-note');
      if(note){note.classList.add('late');const span=note.querySelector('span');if(span)span.textContent='輕量核心資料讀取較慢；保留目前卡片，不會讓視窗卡在空白 Loading。'}
    }
  }
  function markLate(mine){
    if(!active(mine))return;
    const wrap=body()?.querySelector('[data-detail-fast-core]');
    if(!wrap)return;
    let note=wrap.querySelector('[data-detail-late-note]');
    if(!note){
      note=document.createElement('div');note.className='dlg-fast-note late compact';note.dataset.detailLateNote='1';
      note.innerHTML='<b>完整支撐／籌碼層仍在載入</b><span>核心資料已可使用；大型資料層不再阻塞個股視窗。</span><button type="button" class="dlg-fast-retry" data-detail-retry="1">重試完整詳情</button>';
      wrap.appendChild(note);
    }
  }
  function start(e){
    const code=String(e.detail?.code||'').trim();
    const view=String(e.detail?.view||document.querySelector('.tab.active')?.dataset.view||'intraday');
    if(!code)return;
    token+=1;const mine=token;current={code,view};clearTimers();
    queueMicrotask(()=>{if(active(mine))showImmediate(code,view)});
    loadFastCore(code,view,mine);
    later(()=>markLate(mine),9000);
  }
  function resolved(){
    const b=body();
    if(!b)return;
    if(!b.querySelector('.detail-loading')&&!b.querySelector('[data-detail-fast-core]'))clearTimers();
  }
  function retry(){
    if(!current.code)return;
    document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code:current.code,view:current.view}}));
  }
  function style(){
    if(document.getElementById('detailLoadingGuardStyle'))return;
    const s=document.createElement('style');s.id='detailLoadingGuardStyle';s.textContent=`
      .dlg-fast-core{padding:2px 0 12px}.dlg-fast-note{padding:10px 11px;border-radius:11px;background:var(--soft);border:1px solid var(--line);margin-bottom:10px}.dlg-fast-note.compact{margin-top:10px;margin-bottom:0}.dlg-fast-note.late{border-color:color-mix(in srgb,var(--red) 35%,var(--line));background:color-mix(in srgb,var(--red) 6%,var(--soft))}.dlg-fast-note b,.dlg-fast-note span,.dlg-fast-note small{display:block}.dlg-fast-note b{font-size:.86rem}.dlg-fast-note span{margin-top:4px;font-size:.75rem;line-height:1.45}.dlg-fast-note small{margin-top:5px;color:var(--muted);font-size:.67rem;line-height:1.4}.dlg-fast-card-host>.card{margin:0;box-shadow:none}.dlg-fast-retry{display:block;width:100%;margin-top:9px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:inherit;font-weight:750}
    `;document.head.appendChild(s);
  }
  function boot(){
    style();
    document.addEventListener('radar:open-stock',start);
    document.addEventListener('radar:detail-core-rendered',resolved);
    document.addEventListener('radar:detail-rendered',resolved);
    document.addEventListener('radar:data-reloaded',()=>{manifestCache=null;summaryCache.clear()});
    document.addEventListener('click',e=>{if(e.target.closest?.('[data-detail-retry]'))retry()});
    document.addEventListener('close',e=>{if(e.target?.id==='detailDialog'){token+=1;clearTimers()}},true);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();