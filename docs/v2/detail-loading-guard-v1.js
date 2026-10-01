(()=>{
  'use strict';

  let token=0;
  let manifestCache=null;
  const summaryCache=new Map();

  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
  const fmt=(v,d=1)=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
  const stage={OBSERVE:'觀察',SETUP:'蓄勢待發',LAUNCH:'剛啟動',TREND:'趨勢持有',PULLBACK_TEST:'回踩觀察',PULLBACK_CONFIRMED:'回踩承接',WEAKENING:'轉弱警戒',FAILED:'結構失效'};
  const action={WATCH:'觀察',WAIT_TRIGGER:'等觸發',SMALL_TEST:'小量試單候選',WAIT_PULLBACK:'等回踩',HOLD:'續抱',ADD_ON_CONFIRM:'確認後加碼候選',DO_NOT_CHASE:'過熱不追',REDUCE_WATCH:'減碼觀察',EXIT_PRIORITY:'優先出場',DATA_STALE:'資料失效'};
  const summaryKey={intraday:'decision_intraday_summary',close:'decision_close_summary',daytrade:'decision_daytrade_summary'};

  const body=()=>document.getElementById('detailBody');
  const dialog=()=>document.getElementById('detailDialog');
  const title=()=>document.getElementById('detailTitle');

  function safeOpen(d){
    if(!d||d.open)return;
    try{d.showModal()}catch(_){d.setAttribute('open','')}
  }

  function cardFor(code){
    return [...document.querySelectorAll('#cards .card[data-code]')].find(x=>String(x.dataset.code||'').trim()===String(code||'').trim())||null;
  }

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
    if(summaryCache.has(ck))return {m,meta:m.datasets?.[key],rows:summaryCache.get(ck)};
    const meta=m.datasets?.[key];
    if(!meta?.url)throw new Error(`missing ${key}`);
    const rows=await getJson(meta.url,5000);
    if(!Array.isArray(rows))throw new Error(`${key} is not array`);
    summaryCache.set(ck,rows);
    return {m,meta,rows};
  }

  function cloneCard(code){
    const src=cardFor(code);
    if(!src)return '<div class="detail-note">正在讀取這檔股票的核心資料…</div>';
    const holder=document.createElement('div');
    const clone=src.cloneNode(true);
    clone.removeAttribute('role');clone.removeAttribute('tabindex');clone.removeAttribute('aria-label');clone.removeAttribute('data-code');
    clone.style.pointerEvents='none';
    holder.appendChild(clone);
    return holder.innerHTML;
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

  function initialHtml(code,view){
    const label=view==='close'?'盤後':view==='daytrade'?'當沖':'盤中';
    return `<div class="dlg-fast-core"><div class="dlg-fast-note"><b>${esc(code)} 核心詳情</b><span>正在讀取輕量個股核心資料。</span><small>${esc(label)}只讀小型 summary；已停止自動下載大型全市場詳情檔，避免手機當機。</small></div><div class="dlg-fast-card-host">${cloneCard(code)}</div></div>`;
  }

  function summaryHtml(row,view,m,meta){
    const [scoreLabel,score]=scoreValue(row,view),[heroTone,heroLabel]=tone(row),s=row.scores||{};
    const asOf=meta?.as_of||row.as_of||'—';
    return `<div class="dlg-fast-core" data-build="${esc(m.active_build_id||'')}">
      <div class="sdr-context">${view==='close'?'盤後波段':view==='daytrade'?'當沖':'盤中波段'}核心詳情 · ${esc(row.opportunity_bucket||'—')} · 排名 #${esc(row.opportunity_rank??'—')}</div>
      <div class="detail-hero"><div><span class="badge stage">${esc(stage[row.lifecycle_stage]||row.lifecycle_stage||'—')}</span><h2>${esc(action[row.action_state]||row.action_state||'—')}</h2><p>核心資料已載入。為避免 iPhone/Safari 因解析全市場大型 JSON 當機，完整層暫不自動下載。</p></div><div class="detail-light ${heroTone}">${esc(heroLabel)}</div></div>
      <div class="sdr-quick"><div><span>${esc(scoreLabel)}</span><b>${fmt(score)}</b></div><div><span>進場位置</span><b>${fmt(s.entry_position_score)}</b></div><div><span>資料信心</span><b>${fmt(row.data_confidence,0)}%</b></div></div>
      ${listBlock('為什麼現在看它',row.why_now,'目前沒有新增理由。')}
      ${listBlock('現在卡在哪裡',row.blockers,'目前沒有額外卡點。')}
      ${(row.upgrade_conditions||[]).length?listBlock(view==='close'?'明日升級條件':'升級條件',row.upgrade_conditions):''}
      ${(row.risk_overlays||[]).length?listBlock('風險旗標',row.risk_overlays):''}
      <div class="dlg-fast-note compact safe"><b>手機安全模式已啟用</b><span>完整支撐／壓力、技術與籌碼會改成「單一股票小檔」後再接回；目前不會在背景偷偷抓 3–6MB 全市場 JSON。</span><small>資料時間：${esc(String(asOf).replace('T',' ').slice(0,16))}</small></div>
    </div>`;
  }

  async function start(e){
    const code=String(e.detail?.code||'').trim();
    const view=String(e.detail?.view||document.querySelector('.tab.active')?.dataset.view||'intraday');
    if(!code||view==='portfolio')return;

    // Critical: own this event and prevent stock-detail-renderer.js from starting
    // the old full-market detail/zone/evidence downloads on mobile.
    e.stopImmediatePropagation();

    const mine=++token;
    const d=dialog(),b=body(),t=title();
    if(!d||!b||!t)return;
    t.textContent=`${code} 個股詳情`;
    b.innerHTML=initialHtml(code,view);
    safeOpen(d);

    try{
      const {m,meta,rows}=await summary(view);
      if(mine!==token||!d.open)return;
      const row=rows.find(x=>String(x?.code||'').trim()===code);
      if(!row){b.innerHTML='<div class="detail-note warn">這檔股票目前不在輕量核心資料中。</div>';return}
      if(row.build_id&&row.build_id!==m.active_build_id){b.innerHTML='<div class="detail-note warn">資料版本不一致，已停止顯示避免混用。</div>';return}
      t.textContent=`${row.code} ${row.name||''}`.trim();
      b.innerHTML=summaryHtml(row,view,m,meta);
    }catch(err){
      console.error('safe stock detail',err);
      if(mine!==token||!d.open)return;
      b.innerHTML=`<div class="dlg-fast-note late"><b>核心詳情讀取失敗</b><span>已停止大型資料下載，因此頁面不會再因完整全市場 JSON 而卡死。請關閉後重試。</span></div>${cloneCard(code)}`;
    }
  }

  function style(){
    if(document.getElementById('detailLoadingGuardStyle'))return;
    const s=document.createElement('style');s.id='detailLoadingGuardStyle';s.textContent=`
      .dlg-fast-core{padding:2px 0 12px}.dlg-fast-note{padding:10px 11px;border-radius:11px;background:var(--soft);border:1px solid var(--line);margin-bottom:10px}.dlg-fast-note.compact{margin-top:10px;margin-bottom:0}.dlg-fast-note.safe{border-color:color-mix(in srgb,var(--green) 35%,var(--line))}.dlg-fast-note.late{border-color:color-mix(in srgb,var(--red) 35%,var(--line))}.dlg-fast-note b,.dlg-fast-note span,.dlg-fast-note small{display:block}.dlg-fast-note b{font-size:.86rem}.dlg-fast-note span{margin-top:4px;font-size:.75rem;line-height:1.45}.dlg-fast-note small{margin-top:5px;color:var(--muted);font-size:.67rem;line-height:1.4}.dlg-fast-card-host>.card{margin:0;box-shadow:none}
    `;document.head.appendChild(s);
  }

  function boot(){
    style();
    document.addEventListener('radar:open-stock',start,true);
    document.addEventListener('radar:data-reloaded',()=>{manifestCache=null;summaryCache.clear()});
    document.addEventListener('close',e=>{if(e.target?.id==='detailDialog')token+=1},true);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();