const US={rows:null,promise:null};
async function loadUniverse(){if(US.rows)return US.rows;if(US.promise)return US.promise;US.promise=fetch(`../data/universe.json?t=${Date.now()}`,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`universe ${r.status}`);return r.json()}).then(x=>{US.rows=Array.isArray(x)?x:(x.rows||[]);return US.rows}).finally(()=>{US.promise=null});return US.promise}
async function searchUniverse(query,rankedRows=[]){const q=String(query||'').trim().toLowerCase();if(q.length<2)return[];try{const all=await loadUniverse(),ranked=new Set((rankedRows||[]).map(x=>String(x.code||'')));return all.filter(x=>{const code=String(x.code||'').toLowerCase(),name=String(x.name||'').toLowerCase();return(code.includes(q)||name.includes(q))&&!ranked.has(String(x.code||''))}).slice(0,20).map(x=>({...x,_outsidePool:true,_outsideReason:'未進雷達排名池：目前無法產生完整執行分。常見原因是20日平均成交金額未達3,000萬元，或技術／資料完整度不足；系統不會用假分數補滿。'}))}catch(err){console.warn('universe search fallback',err);return[]}}
window.RadarUniverseSearch={search:searchUniverse,clear(){US.rows=null;US.promise=null}};

(()=>{
  'use strict';
  if(window.__INUKO_SEARCH_ZONE_HOTFIX_V1__)return;
  window.__INUKO_SEARCH_ZONE_HOTFIX_V1__=true;

  const missionIndex={intraday:'decision_intraday_index',close:'decision_close_index',daytrade:'decision_daytrade_index'};
  const state={manifest:null,index:new Map(),zones:new Map(),view:'',loadPromise:null,searchTimer:null,zoneTimer:null};
  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
  const fmtPrice=v=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:2});
  const zoneText=z=>{if(!z)return'—';const lo=num(z.low),hi=num(z.high),c=num(z.center);if(lo!=null&&hi!=null&&Math.abs(lo-hi)>1e-9)return`${fmtPrice(lo)}–${fmtPrice(hi)}`;return fmtPrice(c??lo??hi)};
  const activeView=()=>document.querySelector('.tab.active')?.dataset?.view||'intraday';
  const setText=(el,text)=>{if(el&&el.textContent!==text)el.textContent=text};

  async function json(url){const r=await fetch(`${url}${url.includes('?')?'&':'?'}hotfix=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(`${url} ${r.status}`);return r.json()}
  async function loadDecisionContext(force=false){
    const view=activeView();
    if(view==='portfolio')return;
    if(!force&&state.view===view&&state.index.size&&(view!=='close'||state.zones.size))return;
    if(state.loadPromise)return state.loadPromise;
    state.loadPromise=(async()=>{
      const manifest=await json('./data/current_manifest.json');
      const key=missionIndex[view],meta=manifest?.datasets?.[key];
      let rows=[];
      if(meta){const data=await json(meta.url);rows=Array.isArray(data)?data:(data?.items?Object.values(data.items):[])}
      state.manifest=manifest;state.view=view;state.index=new Map(rows.filter(x=>x?.code).map(x=>[String(x.code),x]));
      state.zones=new Map();
      if(view==='close'){
        const zm=manifest?.datasets?.zone_close;
        if(zm){const zs=await json(zm.url);state.zones=new Map((Array.isArray(zs)?zs:[]).filter(z=>z?.zone_id).map(z=>[String(z.zone_id),z]))}
      }
    })().catch(err=>console.warn('search/zone hotfix context',err)).finally(()=>{state.loadPromise=null});
    return state.loadPromise;
  }

  function matchingCard(q){
    if(!q)return null;
    return [...document.querySelectorAll('#cards .card[data-code]')].find(card=>{
      if(card.dataset.hotfixSearch==='1')return false;
      const text=String(card.querySelector('.code')?.textContent||`${card.dataset.code||''}`).toLowerCase();
      return text.includes(q);
    })||null;
  }
  function applyImmediateSearch(){
    const input=document.getElementById('searchInput'),host=document.getElementById('cards');if(!input||!host)return;
    const q=input.value.trim().toLowerCase();
    [...host.querySelectorAll('.card')].forEach(card=>{
      if(card.dataset.hotfixSearch==='1'){if(!q)card.remove();return}
      if(!q){card.style.removeProperty('display');return}
      const text=String(card.querySelector('.code')?.textContent||card.dataset.code||'').toLowerCase();
      card.style.display=text.includes(q)?'':'none';
    });
  }
  async function fallbackSearch(){
    const input=document.getElementById('searchInput'),host=document.getElementById('cards');if(!input||!host)return;
    const q=input.value.trim().toLowerCase();
    host.querySelectorAll('[data-hotfix-search="1"]').forEach(x=>x.remove());
    if(q.length<2||matchingCard(q))return;
    await loadDecisionContext();
    if(input.value.trim().toLowerCase()!==q||matchingCard(q))return;
    const ranked=[...state.index.values()].filter(x=>String(x.code||'').toLowerCase().includes(q)||String(x.name||'').toLowerCase().includes(q)).slice(0,20);
    let results=ranked.map(x=>({...x,_ranked:true}));
    if(!results.length){
      try{results=(await searchUniverse(q,[...state.index.values()])).slice(0,20)}catch(_){results=[]}
    }
    if(!results.length)return;
    const wrap=document.createElement('div');wrap.dataset.hotfixSearch='1';wrap.style.display='contents';
    wrap.innerHTML=results.map(x=>{
      const code=String(x.code||''),name=String(x.name||''),group=String(x.primary_group||x.sector_group||x.industry_name||x.industry||'分類待補');
      if(x._ranked)return `<article class="card neutral" data-hotfix-search="1" data-code="${esc(code)}" role="button" tabindex="0"><div class="card-top"><div class="identity"><span class="rank">搜尋結果</span><div><span class="code">${esc(code)} ${esc(name)}</span><div class="muted">${esc(group)}</div></div></div><span class="badge stage">點開詳情</span></div><div class="action-line neutral"><span>⌕</span><b>全市場排名池搜尋</b><small>${esc(activeView()==='close'?'盤後':'雷達')}</small></div></article>`;
      return `<article class="card neutral outside-pool" data-hotfix-search="1"><div class="card-top"><div class="identity"><span class="rank">全市場 · 未排名</span><div><span class="code">${esc(code)} ${esc(name)}</span><div class="muted">${esc(group)} · ${esc(x.market||'')}</div></div></div><span class="badge stage">未進排名池</span></div><div class="action-line neutral"><span>○</span><b>不產生執行分</b><small>全市場搜尋</small></div></article>`;
    }).join('');
    host.prepend(...wrap.children);
    applyImmediateSearch();
  }

  function zoneFor(row,side){
    const ids=side==='SUPPORT'?(row?.support_zone_ids||[]):(row?.resistance_zone_ids||[]);
    for(const id of ids){const z=state.zones.get(String(id));if(z)return z}
    return null;
  }
  function actionText(d,s,r){
    const sv=zoneText(s),rv=zoneText(r),a=d?.action_state;
    if(a==='EXIT_PRIORITY')return s?`若仍無法站回 S1 ${sv}，優先處理風險。`:'結構已失效，明日優先處理風險。';
    if(a==='REDUCE_WATCH')return r?`反彈若過不了 R1 ${rv}，以分批降低部位為主。`:'反彈無法恢復結構時，以分批降低部位為主。';
    if(a==='ADD_ON_CONFIRM')return r?`站穩 R1 ${rv} 且量價延續，再考慮確認後加碼。`:'突破確認且量價延續後，再考慮加碼。';
    if(a==='SMALL_TEST')return s&&r?`回踩 S1 ${sv} 守住，或站穩 R1 ${rv} 後，再小量試單。`:s?`回踩 S1 ${sv} 守住再小量試單。`:r?`站穩 R1 ${rv} 後再小量試單。`:'只做確認後的小量試單，不追開高。';
    if(a==='WAIT_PULLBACK')return s?`等回踩 S1 ${sv} 守住、量價重新轉強再看。`:'等回踩止穩後再看，不先接刀。';
    if(a==='WAIT_TRIGGER')return r?`等站穩 R1 ${rv} 且回測不破再看。`:'等待觸發條件完成，不提前卡位。';
    if(a==='HOLD')return s?`S1 ${sv} 未有效跌破前以續抱觀察為主。`:'結構未破先續抱，不因單日震盪亂出。';
    if(a==='DO_NOT_CHASE')return s?`不追；等回到 S1 ${sv} 附近重新評估承接。`:'不追高，等回踩後再重新評估。';
    return null;
  }
  function syncCardZones(){
    if(activeView()!=='close'||!state.zones.size)return;
    for(const card of document.querySelectorAll('#cards .card[data-code]')){
      const d=state.index.get(String(card.dataset.code||''));if(!d)continue;
      const strip=card.querySelector('[data-ahd-strip]');if(!strip)continue;
      const s=zoneFor(d,'SUPPORT'),r=zoneFor(d,'RESISTANCE');
      const cells=strip.querySelectorAll('.ahd-card-grid>div');
      if(cells[0])setText(cells[0].querySelector('strong'),zoneText(s));
      if(cells[1])setText(cells[1].querySelector('strong'),zoneText(r));
      const action=actionText(d,s,r);if(action)setText(strip.querySelector('.ahd-card-action span'),action);
      if(s){setText(strip.querySelector('.ahd-card-fail span'),`有效跌破 S1 ${fmtPrice(s.low??s.center)}：連續對應K收破，或跌破後反抽站不回且量價轉弱。`)}
    }
  }
  function scheduleZoneSync(){clearTimeout(state.zoneTimer);state.zoneTimer=setTimeout(async()=>{if(activeView()==='close'){await loadDecisionContext();syncCardZones()}},40)}

  function init(){
    const input=document.getElementById('searchInput'),host=document.getElementById('cards');if(!input||!host)return;
    input.addEventListener('input',()=>{
      applyImmediateSearch();
      clearTimeout(state.searchTimer);
      state.searchTimer=setTimeout(()=>fallbackSearch(),320);
    },{capture:true});
    const obs=new MutationObserver(()=>{applyImmediateSearch();scheduleZoneSync()});
    obs.observe(host,{childList:true,subtree:true});
    document.getElementById('tabs')?.addEventListener('click',()=>setTimeout(()=>{state.index.clear();state.zones.clear();state.view='';loadDecisionContext(true).then(()=>scheduleZoneSync())},80));
    document.addEventListener('radar:data-reloaded',()=>{state.manifest=null;state.index.clear();state.zones.clear();state.view='';loadDecisionContext(true).then(()=>scheduleZoneSync())});
    loadDecisionContext().then(()=>scheduleZoneSync());
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
