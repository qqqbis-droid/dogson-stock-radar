(()=>{
  'use strict';

  const MISSION={
    intraday:{label:'盤中',core:'decision_intraday_summary',prefixes:['decision_intraday_','zone_intraday','stock_detail_intraday','sector_intraday','market_intraday_context','capital_intraday_context']},
    close:{label:'盤後',core:'decision_close_summary',prefixes:['decision_close_','zone_close','stock_detail_close','sector_close','market_close_context','capital_close_context']},
    daytrade:{label:'當沖',core:'decision_daytrade_summary',prefixes:['decision_daytrade_','zone_daytrade','stock_detail_daytrade']}
  };
  let manifest=null;

  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const pad=n=>String(n).padStart(2,'0');
  function parse(v){const d=v?new Date(v):null;return d&&!Number.isNaN(d.getTime())?d:null}
  function short(v,withDate=true){
    const d=parse(v);if(!d)return '時間未知';
    const md=`${d.getMonth()+1}/${d.getDate()}`;
    const hm=`${pad(d.getHours())}:${pad(d.getMinutes())}`;
    return withDate?`${md} ${hm}`:hm;
  }
  function dateKey(v){const d=parse(v);return d?`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`:''}
  function missionMeta(key){
    const cfg=MISSION[key],ds=manifest?.datasets||{},core=ds[cfg.core]||null;
    return {cfg,core,asOf:core?.as_of||null,date:dateKey(core?.as_of)};
  }
  function badge(meta){
    if(!meta.asOf)return {cls:'unknown',text:'時間未知'};
    const base=manifest?.trade_date||dateKey(manifest?.generated_at);
    if(meta.date&&base&&meta.date<base)return {cls:'stale',text:'舊資料／凍結'};
    if(meta.date===base)return {cls:'same',text:'本交易日快照'};
    return {cls:'unknown',text:'日期待核對'};
  }
  function datasetRows(key){
    const cfg=MISSION[key],ds=manifest?.datasets||{};
    return Object.entries(ds)
      .filter(([name])=>cfg.prefixes.some(p=>name===p||name.startsWith(p)))
      .sort((a,b)=>a[0].localeCompare(b[0]))
      .map(([name,m])=>{
        const d=dateKey(m?.as_of),st=!m?.as_of?'時間未知':(d&&manifest?.trade_date&&d<manifest.trade_date?'舊／凍結':'本交易日');
        return `<div class="uf-ds"><code>${esc(name)}</code><span>${esc(short(m?.as_of))}</span><b class="${st==='舊／凍結'?'stale':''}">${esc(st)}</b></div>`;
      }).join('');
  }
  function mixedWarning(){
    const metas=Object.fromEntries(Object.keys(MISSION).map(k=>[k,missionMeta(k)]));
    const dates=[...new Set(Object.values(metas).map(x=>x.date).filter(Boolean))];
    if(dates.length<=1)return '';
    return `<div class="uf-warning">⚠ 混合資料日：${Object.entries(metas).map(([k,m])=>`${m.cfg.label} ${m.date?short(m.asOf,false)+'（'+(m.date.slice(5).replace('-','/'))+'）':'未知'}`).join('；')}。不同任務不可互相視為同一時間的新資料。</div>`;
  }
  function activeView(){return document.querySelector('.tab.active')?.dataset.view||'intraday'}
  function render(){
    if(!manifest)return;
    const host=document.getElementById('unifiedFreshness');if(!host)return;
    const view=activeView();
    if(view==='portfolio'){host.hidden=true;return}host.hidden=false;
    const cards=Object.entries(MISSION).map(([k])=>{
      const m=missionMeta(k),b=badge(m);
      return `<button type="button" class="uf-card ${k===view?'active':''}" data-uf-view="${k}"><span>${m.cfg.label}</span><strong>${esc(short(m.asOf))}</strong><em class="${b.cls}">${esc(b.text)}</em></button>`;
    }).join('');
    const current=MISSION[view]||MISSION.intraday;
    host.innerHTML=`<div class="uf-head"><div><b>資料新鮮度</b><small>每個任務看自己的 as_of，不用總包裝時間猜。</small></div><button type="button" class="uf-refresh">重查時間</button></div>${mixedWarning()}<div class="uf-cards">${cards}</div><details class="uf-detail"><summary>${current.label}｜逐資料集時間</summary><div class="uf-datasets">${datasetRows(view)}</div></details><div class="uf-bundle">資料包產生：${esc(short(manifest.generated_at))}。這只代表重新打包時間，<b>不代表包內每一個數據都在這個時間更新。</b></div>${view==='close'?'<div class="uf-schedule">盤後固定批次（台北時間）：<b>14:25 初版 → 20:30 籌碼補件 → 23:40 再補件 → 次交易日 08:15 最終補件／確認</b>。來源公布與 Actions / Pages 部署完成後，畫面才會實際更新，因此可能比排程時間晚幾分鐘。</div>':''}`;
    host.querySelectorAll('[data-uf-view]').forEach(btn=>btn.addEventListener('click',()=>{
      const tab=document.querySelector(`.tab[data-view="${btn.dataset.ufView}"]`);if(tab)tab.click();
    }));
    host.querySelector('.uf-refresh')?.addEventListener('click',load);
  }
  async function load(){
    try{
      const r=await fetch(`./data/current_manifest.json?freshness=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error(`HTTP ${r.status}`);
      manifest=await r.json();render();
    }catch(err){
      const host=document.getElementById('unifiedFreshness');
      if(host)host.innerHTML=`<div class="uf-warning">⚠ 無法讀取資料時間：${esc(err.message||err)}</div>`;
    }
  }
  function ensurePanel(){
    if(document.getElementById('unifiedFreshness'))return;
    const mission=document.getElementById('mission');if(!mission)return;
    const el=document.createElement('section');el.id='unifiedFreshness';el.className='panel uf-panel';
    mission.insertAdjacentElement('afterend',el);
  }
  function normalizeScoreExplain(){
    const body=document.getElementById('detailBody');if(!body)return;
    const box=body.querySelector('.sdr-explain');if(!box)return;
    const summary=box.querySelector('summary'),inner=box.querySelector('.sdr-explain-body');if(!summary||!inner)return;
    const view=activeView();
    if(!['close','intraday','daytrade'].includes(view))return;
    summary.textContent='評分依據｜為什麼是這個分數';
    if(view==='intraday'){
      if(!inner.querySelector('[data-uf-reminder]'))inner.insertAdjacentHTML('beforeend','<div class="sdr-note" data-uf-reminder>分數代表條件同步程度，不代表上漲機率；盤中分數必須搭配同一時間的價格、量能與支撐壓力判讀。</div>');
      return;
    }
    if(view==='daytrade'){
      if(!inner.querySelector('[data-uf-formula]')){
        const parts=[...inner.querySelectorAll('.sdr-exp-card .sdr-exp-head')].map(h=>{
          const name=h.querySelector('b')?.textContent?.trim()||'分項';
          const text=h.querySelector('strong')?.textContent||'';
          const max=(text.match(/\/\s*([\d.]+)/)||[])[1];
          return max?`${name}${max}`:name;
        });
        inner.insertAdjacentHTML('afterbegin',`<div class="sdr-note" data-uf-formula>當沖總分＝${esc(parts.length?parts.join('＋'):'Engine 分項加總')}。以下沿用 Engine 原始分項，不在前端重新配分。</div>`);
      }
      inner.querySelectorAll('.sdr-exp-card').forEach(card=>{
        if(card.querySelector('.sdr-exp-item,[data-uf-evidence]'))return;
        card.insertAdjacentHTML('beforeend','<div class="sdr-exp-detail" data-uf-evidence>此資料包目前只提供這個分項的得分／滿分；若 Engine 沒有輸出可拆解證據，畫面不補猜、不用舊證據冒充最新依據。</div>');
      });
      if(!inner.querySelector('[data-uf-reminder]'))inner.insertAdjacentHTML('beforeend','<div class="sdr-note" data-uf-reminder>分數代表條件同步程度，不代表獲利機率；當沖只在同交易日、同快照資料有效時才可執行。</div>');
    }
  }
  function style(){
    if(document.getElementById('unifiedFreshnessStyle'))return;
    const s=document.createElement('style');s.id='unifiedFreshnessStyle';s.textContent=`
      .uf-panel{margin-top:10px}.uf-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.uf-head b{display:block;font-size:.9rem}.uf-head small{display:block;margin-top:3px;color:var(--muted);font-size:.69rem}.uf-refresh{border:0;background:transparent;color:var(--muted);font-size:.7rem;padding:4px;cursor:pointer}.uf-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:9px}.uf-card{border:1px solid var(--line);border-radius:11px;background:var(--soft);padding:8px;text-align:left;color:inherit}.uf-card.active{outline:2px solid color-mix(in srgb,var(--green) 48%,transparent)}.uf-card span,.uf-card strong,.uf-card em{display:block}.uf-card span{font-size:.68rem;color:var(--muted)}.uf-card strong{font-size:.82rem;margin:2px 0}.uf-card em{font-style:normal;font-size:.64rem}.uf-card em.same{color:var(--green)}.uf-card em.stale,.uf-ds b.stale{color:var(--red)}.uf-card em.unknown{color:var(--muted)}.uf-warning{margin-top:8px;padding:8px 9px;border-radius:9px;background:color-mix(in srgb,var(--red) 8%,var(--soft));font-size:.72rem;line-height:1.45}.uf-detail{margin-top:8px;border-top:1px dashed var(--line);padding-top:7px}.uf-detail summary{cursor:pointer;font-size:.72rem;font-weight:750}.uf-datasets{margin-top:6px}.uf-ds{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:7px;align-items:center;padding:4px 0;border-top:1px dashed var(--line);font-size:.64rem}.uf-ds:first-child{border-top:0}.uf-ds code{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted)}.uf-ds b{font-size:.62rem}.uf-bundle,.uf-schedule{margin-top:7px;color:var(--muted);font-size:.68rem;line-height:1.45}.uf-bundle b,.uf-schedule b{color:inherit}.sdr-exp-card>.sdr-exp-detail[data-uf-evidence]{margin-top:6px;padding-top:5px;border-top:1px dashed var(--line)}
      @media(max-width:520px){.uf-card{padding:7px 6px}.uf-card strong{font-size:.75rem}.uf-ds{grid-template-columns:minmax(0,1fr) auto}.uf-ds b{grid-column:2}}
    `;document.head.appendChild(s);
  }
  function boot(){
    style();ensurePanel();load();
    document.getElementById('tabs')?.addEventListener('click',()=>setTimeout(()=>{render();normalizeScoreExplain()},0));
    document.getElementById('detailBody')&&new MutationObserver(normalizeScoreExplain).observe(document.getElementById('detailBody'),{childList:true,subtree:true});
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
