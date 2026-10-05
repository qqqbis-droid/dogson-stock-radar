const US={rows:null,promise:null};
async function loadUniverse(){if(US.rows)return US.rows;if(US.promise)return US.promise;US.promise=fetch(`../data/universe.json?t=${Date.now()}`,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`universe ${r.status}`);return r.json()}).then(x=>{US.rows=Array.isArray(x)?x:(x.rows||[]);return US.rows}).finally(()=>{US.promise=null});return US.promise}
async function searchUniverse(query,rankedRows=[]){const q=String(query||'').trim().toLowerCase();if(q.length<2)return[];try{const all=await loadUniverse(),ranked=new Set((rankedRows||[]).map(x=>String(x.code||'')));return all.filter(x=>{const code=String(x.code||'').toLowerCase(),name=String(x.name||'').toLowerCase();return(code.includes(q)||name.includes(q))&&!ranked.has(String(x.code||''))}).slice(0,20).map(x=>({...x,_outsidePool:true,_outsideReason:'未進雷達排名池：目前無法產生完整執行分。常見原因是20日平均成交金額未達3,000萬元，或技術／資料完整度不足；系統不會用假分數補滿。'}))}catch(err){console.warn('universe search fallback',err);return[]}}
window.RadarUniverseSearch={search:searchUniverse,clear(){US.rows=null;US.promise=null}};

(()=>{
  'use strict';
  if(window.__INUKO_SEARCH_ZONE_HOTFIX_V2__)return;
  window.__INUKO_SEARCH_ZONE_HOTFIX_V2__=true;

  const missionIndex={intraday:'decision_intraday_index',close:'decision_close_index',daytrade:'decision_daytrade_index'};
  const ACTION={WATCH:'觀察',WAIT_TRIGGER:'等觸發',SMALL_TEST:'小量試單候選',WAIT_PULLBACK:'等回踩',HOLD:'續抱',ADD_ON_CONFIRM:'確認後加碼候選',DO_NOT_CHASE:'過熱不追',REDUCE_WATCH:'減碼觀察',EXIT_PRIORITY:'優先出場',DATA_STALE:'資料失效'};
  const state={manifest:null,manifestPromise:null,index:new Map(),indexView:'',indexPromise:null,searchTimer:null,hydrateTimer:null,shards:new Map(),shardPromises:new Map()};
  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
  const activeView=()=>document.querySelector('.tab.active')?.dataset?.view||'intraday';
  const rowsOf=x=>Array.isArray(x)?x:(x?.items&&typeof x.items==='object'?Object.values(x.items):[]);

  async function json(url){const r=await fetch(`${url}${url.includes('?')?'&':'?'}hotfix=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(`${url} ${r.status}`);return r.json()}
  async function ensureManifest(force=false){
    if(!force&&state.manifest)return state.manifest;
    if(state.manifestPromise)return state.manifestPromise;
    state.manifestPromise=json('./data/current_manifest.json').then(m=>{
      const old=state.manifest?.active_build_id||'';
      state.manifest=m;
      if(old&&old!==m?.active_build_id){state.index.clear();state.indexView='';state.shards.clear();state.shardPromises.clear()}
      return m;
    }).finally(()=>{state.manifestPromise=null});
    return state.manifestPromise;
  }
  async function ensureSearchIndex(force=false){
    const view=activeView();
    if(view==='portfolio')return;
    if(!force&&state.indexView===view&&state.index.size)return;
    if(state.indexPromise)return state.indexPromise;
    state.indexPromise=(async()=>{
      const m=await ensureManifest(force),key=missionIndex[view],meta=m?.datasets?.[key];
      let rows=[];if(meta)rows=rowsOf(await json(meta.url));
      state.indexView=view;state.index=new Map(rows.filter(x=>x?.code).map(x=>[String(x.code),x]));
    })().catch(err=>console.warn('search index hotfix',err)).finally(()=>{state.indexPromise=null});
    return state.indexPromise;
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
    await ensureSearchIndex();
    if(input.value.trim().toLowerCase()!==q||matchingCard(q))return;
    const ranked=[...state.index.values()].filter(x=>String(x.code||'').toLowerCase().includes(q)||String(x.name||'').toLowerCase().includes(q)).slice(0,20);
    let results=ranked.map(x=>({...x,_ranked:true}));
    if(!results.length){try{results=(await searchUniverse(q,[...state.index.values()])).slice(0,20)}catch(_){results=[]}}
    if(!results.length)return;
    const frag=document.createDocumentFragment();
    for(const x of results){
      const code=String(x.code||''),name=String(x.name||''),group=String(x.primary_group||x.sector_group||x.industry_name||x.industry||'分類待補');
      const box=document.createElement('div');
      if(x._ranked)box.innerHTML=`<article class="card neutral" data-hotfix-search="1" data-code="${esc(code)}" role="button" tabindex="0"><div class="card-top"><div class="identity"><span class="rank">搜尋結果</span><div><span class="code">${esc(code)} ${esc(name)}</span><div class="muted">${esc(group)}</div></div></div><span class="badge stage">點開詳情</span></div><div class="action-line neutral"><span>⌕</span><b>全市場排名池搜尋</b><small>${esc(activeView()==='close'?'盤後':'雷達')}</small></div></article>`;
      else box.innerHTML=`<article class="card neutral outside-pool" data-hotfix-search="1"><div class="card-top"><div class="identity"><span class="rank">全市場 · 未排名</span><div><span class="code">${esc(code)} ${esc(name)}</span><div class="muted">${esc(group)} · ${esc(x.market||'')}</div></div></div><span class="badge stage">未進排名池</span></div><div class="action-line neutral"><span>○</span><b>不產生執行分</b><small>全市場搜尋</small></div></article>`;
      if(box.firstElementChild)frag.appendChild(box.firstElementChild);
    }
    host.prepend(frag);applyImmediateSearch();scheduleHydration();
  }

  function stick(p){const x=Math.abs(Number(p));if(x<10)return .01;if(x<50)return .05;if(x<100)return .1;if(x<500)return .5;if(x<1000)return 1;return 5}
  function stickValue(v){const n=num(v);if(n==null)return null;const t=stick(n);return Math.round((n+Number.EPSILON)/t)*t}
  function price(v){const n=stickValue(v);if(n==null)return'—';const t=stick(n),d=t<.1?2:t<1?1:0;return Number(n).toLocaleString('zh-TW',{maximumFractionDigits:d})}
  function zoneText(z,side){if(!z)return side==='SUPPORT'?'無可信支撐':'無可信壓力';const lo=num(z.low),hi=num(z.high);return lo!=null&&hi!=null&&Math.abs(lo-hi)>1e-9?`${price(lo)}–${price(hi)}`:price(z.center??lo??hi)}
  function rankOrder(z){return({S1:1,S2:2,R1:1,R2:2})[z?.rank]||9}
  function firstZone(zones,side){return (Array.isArray(zones)?zones:[]).filter(z=>z?.side===side).sort((a,b)=>rankOrder(a)-rankOrder(b))[0]||null}
  function conclusion(d){
    if(d?.action_state==='DATA_STALE')return{tone:'stale',label:'僅供歷史參考'};
    if(['EXIT_PRIORITY','REDUCE_WATCH'].includes(d?.action_state)||['FAILED','WEAKENING'].includes(d?.lifecycle_stage))return{tone:'risk',label:'風險優先'};
    if(d?.action_state==='DO_NOT_CHASE')return{tone:'wait',label:'過熱不追'};
    if(['SMALL_TEST','ADD_ON_CONFIRM'].includes(d?.action_state)||d?.opportunity_bucket==='NEXT_DAY_READY')return{tone:'go',label:'明日候選'};
    if(d?.action_state==='HOLD'||d?.lifecycle_stage==='TREND')return{tone:'go',label:'續抱觀察'};
    if(d?.action_state==='WAIT_PULLBACK'||['PULLBACK_TEST','PULLBACK_CONFIRMED'].includes(d?.lifecycle_stage))return{tone:'wait',label:'等回踩'};
    if(d?.action_state==='WAIT_TRIGGER')return{tone:'wait',label:'等觸發'};
    return{tone:'neutral',label:'觀察'};
  }
  function actionText(d,s,r){
    const sv=zoneText(s,'SUPPORT'),rv=zoneText(r,'RESISTANCE'),a=d?.action_state;
    if(a==='EXIT_PRIORITY')return s?`若仍無法站回 S1 ${sv}，優先處理風險。`:'結構已失效，明日優先處理風險。';
    if(a==='REDUCE_WATCH')return r?`反彈若過不了 R1 ${rv}，以分批降低部位為主。`:'反彈無法恢復結構時，以分批降低部位為主。';
    if(a==='ADD_ON_CONFIRM')return r?`站穩 R1 ${rv} 且量價延續，再考慮確認後加碼。`:'突破確認且量價延續後，再考慮加碼。';
    if(a==='SMALL_TEST')return s&&r?`回踩 S1 ${sv} 守住，或站穩 R1 ${rv} 後，再小量試單。`:s?`回踩 S1 ${sv} 守住再小量試單。`:r?`站穩 R1 ${rv} 後再小量試單。`:'目前沒有可信結構價，只列候選，不追開高。';
    if(a==='WAIT_PULLBACK')return s?`等回踩 S1 ${sv} 守住、量價重新轉強再看。`:'等回踩止穩後再看，不先接刀。';
    if(a==='WAIT_TRIGGER')return r?`等站穩 R1 ${rv} 且回測不破再看。`:'等待觸發條件完成，不提前卡位。';
    if(a==='HOLD')return s?`S1 ${sv} 未有效跌破前以續抱觀察為主。`:'結構未破先續抱，不因單日震盪亂出。';
    if(a==='DO_NOT_CHASE')return s?`不追；等回到 S1 ${sv} 附近重新評估承接。`:'不追高，等回踩後再重新評估。';
    return(d?.blockers||[])[0]?`先處理卡點：${String(d.blockers[0])}`:'先觀察，等條件變得可量化再行動。';
  }
  function invalidText(d,s){
    if(s)return`有效跌破 S1 ${price(s.low??s.center)}：連續對應K收破，或跌破後反抽站不回且量價轉弱。`;
    if(['FAILED','WEAKENING'].includes(d?.lifecycle_stage))return'結構已轉弱；反抽無法恢復原結構時，不把下跌當成加碼理由。';
    return'目前沒有可信 S1；不硬設假停損，等結構價建立後再判斷。';
  }
  function stripHtml(d,zones){
    const s=firstZone(zones,'SUPPORT'),r=firstZone(zones,'RESISTANCE'),c=conclusion(d);
    return `<div class="ahd-card-strip ${c.tone}" data-ahd-strip data-shard-card="1"><div class="ahd-card-title"><span>犬子結論</span><b>${esc(c.label)}</b><em>${esc(ACTION[d?.action_state]||d?.action_state||'—')}</em></div><div class="ahd-card-action"><b>明日動作</b><span>${esc(actionText(d,s,r))}</span></div><div class="ahd-card-grid"><div><small>S1 支撐</small><strong>${esc(zoneText(s,'SUPPORT'))}</strong></div><div><small>R1 壓力</small><strong>${esc(zoneText(r,'RESISTANCE'))}</strong></div></div><div class="ahd-card-fail"><b>失效條件</b><span>${esc(invalidText(d,s))}</span></div></div>`;
  }
  async function loadShard(code){
    const m=await ensureManifest(),build=String(m?.active_build_id||'');if(!build)return null;
    const cached=state.shards.get(code);if(cached?.build_id===build)return cached;
    if(state.shardPromises.has(code))return state.shardPromises.get(code);
    const url=`./data/builds/${encodeURIComponent(build)}/stock-shards/close/${encodeURIComponent(code)}.json`;
    const p=json(url).then(x=>{
      if(x?.build_id!==build||String(x?.code||'')!==String(code)||x?.view!=='close')throw new Error(`shard mismatch ${code}`);
      state.shards.set(code,x);return x;
    }).catch(err=>{console.warn('card shard hydrate',code,err);return null}).finally(()=>state.shardPromises.delete(code));
    state.shardPromises.set(code,p);return p;
  }
  function needsHydration(card,build){
    if(!card?.dataset?.code||card.style.display==='none')return false;
    if(card.dataset.shardHydrated===build)return false;
    const strip=card.querySelector('[data-ahd-strip]');
    if(!strip)return true;
    return [...strip.querySelectorAll('.ahd-card-grid strong')].some(x=>String(x.textContent||'').trim()==='—');
  }
  function applyShard(card,payload){
    const d=payload?.decision;if(!d||!card?.isConnected)return;
    const holder=document.createElement('div');holder.innerHTML=stripHtml(d,payload.zones||[]);const fresh=holder.firstElementChild;if(!fresh)return;
    const old=card.querySelector('[data-ahd-strip]');
    if(old)old.replaceWith(fresh);else{const anchor=card.querySelector('.action-line')||card.querySelector('.quote-strip')||card.querySelector('.card-top');anchor?.insertAdjacentElement('afterend',fresh)}
    card.dataset.shardHydrated=String(payload.build_id||'');
  }
  async function hydrateVisibleCards(){
    if(activeView()!=='close')return;
    const m=await ensureManifest(),build=String(m?.active_build_id||'');if(!build)return;
    const cards=[...document.querySelectorAll('#cards .card[data-code]')].filter(c=>needsHydration(c,build));
    let cursor=0;
    async function worker(){while(cursor<cards.length){const card=cards[cursor++],code=String(card.dataset.code||'');const shard=await loadShard(code);if(shard&&activeView()==='close'&&card.isConnected)applyShard(card,shard)}}
    await Promise.all(Array.from({length:Math.min(4,cards.length)},()=>worker()));
  }
  function scheduleHydration(delay=90){clearTimeout(state.hydrateTimer);state.hydrateTimer=setTimeout(()=>hydrateVisibleCards(),delay)}

  function init(){
    const input=document.getElementById('searchInput'),host=document.getElementById('cards');if(!input||!host)return;
    input.addEventListener('input',()=>{applyImmediateSearch();clearTimeout(state.searchTimer);state.searchTimer=setTimeout(()=>fallbackSearch(),320);scheduleHydration(380)},{capture:true});
    new MutationObserver(()=>{applyImmediateSearch();scheduleHydration()}).observe(host,{childList:true,subtree:false});
    document.getElementById('tabs')?.addEventListener('click',()=>setTimeout(()=>{state.index.clear();state.indexView='';scheduleHydration()},100));
    document.addEventListener('radar:view-rendered',()=>scheduleHydration());
    document.addEventListener('radar:data-reloaded',()=>{state.manifest=null;state.index.clear();state.indexView='';state.shards.clear();state.shardPromises.clear();ensureManifest(true).then(()=>scheduleHydration())});
    ensureManifest().then(()=>scheduleHydration(140));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
