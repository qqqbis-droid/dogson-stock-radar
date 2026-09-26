(()=>{
  if(window.__DOGSON_PAGE_ARCH_V1730__) return;
  window.__DOGSON_PAGE_ARCH_V1730__=true;
  const $=(s,r=document)=>r.querySelector(s);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clean=s=>String(s??'').replace(/\s+/g,' ').trim();

  function state(){let m='intraday',p=false;try{m=mode||m;p=!!portfolioOnly}catch{}return{m,p}}
  const liveIntra=()=>window.DOGSON_INTRADAY_LIVE_READY===true;
  const dayActionable=()=>window.DOGSON_DAYTRADE_ACTIONABLE===true;
  function sourceRows(m){
    try{
      if(m==='daytrade')return dayActionable()?(Array.isArray(daytradeRows)?daytradeRows:[]):[];
      if(m==='close')return Array.isArray(closeRows)?closeRows:[];
      return liveIntra()?(Array.isArray(intraRows)?intraRows:[]):(Array.isArray(closeRows)?closeRows:[]);
    }catch{return[]}
  }
  function stage(r){try{return clean(stageKey(r?.category))}catch{return clean(r?.category||'觀察')}}
  function heldCodes(){try{return new Set(Object.keys(portfolioData||{}).map(String))}catch{return new Set()}}
  function countLike(rows,rx){return rows.filter(r=>rx.test(stage(r))).length}

  function swingSummary(rows,m,title){
    const setup=countLike(rows,/蓄勢/),launch=countLike(rows,/剛啟動/),pull=countLike(rows,/回踩/),trend=countLike(rows,/趨勢|持有/),hot=countLike(rows,/過熱/),weak=countLike(rows,/轉弱|失效/);const fallback=m==='intraday'&&!liveIntra();
    return{title:fallback?'最近完整波段候選':title,sub:fallback?'目前不是通過即時品質門檻的盤中狀態，改用最近完整盤後波段資料；5分鐘與盤中資金訊號暫停。':m==='close'?'收盤後用完整日K、60分K、籌碼與位置整理明日觀察名單。':'盤中用市場、族群、波段結構與目前位置找值得追蹤的機會。',items:[['🌱',setup,'蓄勢'],['🔥',launch,'剛啟動'],['🟡',pull,'回踩'],['🚂',trend,'趨勢中'],['🚫',hot,'過熱'],['⚠️',weak,'轉弱/失效']]};
  }
  function daytradeSummary(rows){
    const active=dayActionable();const c=s=>rows.filter(r=>clean(r?.daytrade_state)===s).length;const high=rows.filter(r=>Number(r?.daytrade_score)>=75).length;
    return{title:active?'今日當沖候選':'當沖資料暫停',sub:active?'只統計獨立 daytrade 即時資料；波段 Stage 與昨日法人不混入當沖分。':'目前不是可驗證的台股現貨盤中即時狀態，因此不顯示任何「現在可執行」的當沖清單。',items:[['🟢',c('可執行'),active?'可執行':'暫停'],['🟡',c('等回踩'),active?'等回踩':'暫停'],['🔵',c('觀察'),active?'觀察':'暫停'],['🚫',c('過熱不追'),'過熱不追'],['🔴',c('失效'),'失效'],['⚡',high,active?'75分以上':'即時未開']]};
  }
  function portfolioSummary(){
    const codes=heldCodes(),rows=sourceRows('intraday').filter(r=>codes.has(String(r?.code)));let invalid=0,weak=0,healthy=0,hot=0;rows.forEach(r=>{const s=stage(r);if(/失效/.test(s))invalid++;else if(/轉弱/.test(s))weak++;else if(/過熱/.test(s))hot++;else healthy++});const missing=Math.max(0,codes.size-rows.length);
    return{title:'庫存優先處理',sub:liveIntra()?'目前為合格盤中即時狀態，庫存可同時參考盤中轉折。':'目前使用最近完整盤後結構判讀庫存，不把非即時盤中轉折當成現在訊號。',items:[['💼',codes.size,'持有檔數'],['❌',invalid,'結構失效'],['⚠️',weak,'轉弱警戒'],['✅',healthy,'結構正常'],['🚫',hot,'短線過熱'],['…',missing,'行情待補']]};
  }
  function summarySpec(){const s=state();if(s.p)return portfolioSummary();const rows=sourceRows(s.m);if(s.m==='daytrade')return daytradeSummary(rows);return swingSummary(rows,s.m,s.m==='close'?'明日波段候選':'今日波段機會')}

  function renderOverview(){const o=$('#dogsonOverviewV160');if(!o)return;const x=summarySpec();const items=x.items.map(([i,n,l])=>`<div class="dogson-mode-stat-v1701"><b>${esc(i)} ${Number(n)||0}</b><span>${esc(l)}</span></div>`).join('');const html=`<div class="dogson-section-title">${esc(x.title)}</div><div class="dogson-section-sub">${esc(x.sub)}</div><div class="dogson-mode-grid-v1701">${items}</div>`;if(o.dataset.v1730!==html){o.innerHTML=html;o.dataset.v1730=html;o.classList.add('dogson-overview-v1701')}}
  function applyVisibility(){const s=state(),page=s.p?'portfolio':s.m;document.documentElement.dataset.dogsonPage=page;const quick=$('#dogsonQuickFilters');if(quick)quick.hidden=(s.p||s.m==='daytrade');const changes=$('#changebox');if(changes)changes.hidden=(s.p||s.m!=='intraday'||!liveIntra());const ps=$('#portfolioSummary');if(ps)ps.hidden=!s.p;const more=$('#dogsonMoreMarket');if(more){const sm=$(':scope>summary',more);if(sm)sm.textContent=s.p?'市場與驗證背景':s.m==='daytrade'?'更多當沖背景資料':s.m==='close'?'更多盤後市場資訊':'更多市場資訊'}}
  function prioritizePortfolio(){const s=state(),ps=$('#portfolioSummary'),truth=$('#dogsonDataTruthV1700');if(!s.p||!ps||!truth)return;if(truth.nextElementSibling!==ps)truth.after(ps)}
  function installStyle(){if($('#dogsonPageArchStyle1701'))return;const el=document.createElement('style');el.id='dogsonPageArchStyle1701';el.textContent=`.dogson-mode-grid-v1701{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px;margin-top:10px}.dogson-mode-stat-v1701{min-width:0;padding:9px 5px;border:1px solid #e5eae6;background:#f8faf8;border-radius:12px;text-align:center}.dogson-mode-stat-v1701 b{display:block;font-size:15px;color:#27312d}.dogson-mode-stat-v1701 span{display:block;font-size:9px;color:#7c8882;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}html[data-dogson-page="portfolio"] #dogsonFlowHomeV1685{display:none!important}html[data-dogson-page="daytrade"] #dogsonQuickFilters{display:none!important}html[data-dogson-page="close"] #changebox,html[data-dogson-page="daytrade"] #changebox,html[data-dogson-page="portfolio"] #changebox{display:none!important}html[data-dogson-theme="dark"] .dogson-mode-stat-v1701{background:#252b27;border-color:#343b37}html[data-dogson-theme="dark"] .dogson-mode-stat-v1701 b{color:#eef2ef}@media(max-width:720px){.dogson-mode-grid-v1701{grid-template-columns:repeat(3,minmax(0,1fr))}.dogson-mode-stat-v1701 b{font-size:14px}}`;document.head.appendChild(el)}
  let busy=false,timer=null;function apply(){if(busy)return;busy=true;try{installStyle();applyVisibility();renderOverview();prioritizePortfolio()}finally{busy=false}}function schedule(){clearTimeout(timer);timer=setTimeout(apply,60)}
  function boot(){apply();document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav,#portfolioOnly'))setTimeout(apply,90)});window.addEventListener('dogson:freshness',schedule);window.addEventListener('dogson:data-truth',schedule);window.addEventListener('dogson:actionability',schedule);const root=$('.wrap')||document.body;new MutationObserver(schedule).observe(root,{subtree:true,childList:true,characterData:false});setTimeout(apply,300);setTimeout(apply,1000)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
