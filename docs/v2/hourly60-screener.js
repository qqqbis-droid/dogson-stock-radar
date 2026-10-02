(()=>{
  'use strict';
  const CAT={
    PRE_CROSS:{label:'金叉前夕',icon:'🟡',order:0},
    EARLY:{label:'剛啟動',icon:'🌱',order:1},
    STABLE_CONT:{label:'趨勢中',icon:'🔵',order:2},
    ACCEL_CONT:{label:'噴發／加速',icon:'🚀',order:3}
  };
  const POS={GREEN:'🟢 位置舒服',YELLOW:'🟡 等回踩／確認',ORANGE:'🟠 偏延伸不追',RED:'🔴 過熱／失效'};
  const DIR={UP:'↗',FLAT:'→',DOWN:'↘'};
  const storeKey='dogson-v2-close-mode';
  const state={mode:'v2',payload:null,category:'',preset:'',position:'',sector:'',search:'',sort:'combined'};
  let mounted=false,loading=false;

  const $=s=>document.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
  const fmt=(v,d=1)=>n(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
  const pct=(v,d=1)=>n(v)==null?'—':`${Number(v)>0?'+':''}${fmt(v,d)}%`;
  const activeView=()=>$('.tab.active')?.dataset?.view||'intraday';
  const rows=()=>{
    const p=state.payload||{};
    const source=Array.isArray(p.all_rows)?p.all_rows:Array.isArray(p.rows)?p.rows:[];
    return source.filter(r=>r&&CAT[r.category60]&&r.data_status!=='UNAVAILABLE');
  };

  // 犬子版「未過熱啟動」：只使用目前 Engine 已有且可驗證的欄位。
  // 不以缺失的 MFI / EMA9 假造結果；等正式資料源加入後再升級條件。
  function isUnheatedStart(r){
    const lifecycle=r.category60==='PRE_CROSS'||r.category60==='EARLY';
    const position=r.entry_light==='GREEN'||r.entry_light==='YELLOW';
    const dist=n(r.daily_dist20),rsi=n(r.daily_rsi),vol=n(r.vol_ratio60day),p20=n(r.price_vs20_60_pct);
    const dailyPosition=dist!=null&&dist>=0&&dist<=7;
    const neutralRsi=rsi!=null&&rsi>=40&&rsi<=65;
    const healthyVolume=vol!=null&&vol>=1.0&&vol<=1.8;
    const sixtyPosition=p20!=null&&p20>=-1.5&&p20<=5;
    const slope=r.dir20==='UP'&&(r.dir60==='UP'||r.dir60==='FLAT');
    return Boolean(r.is_candidate&&lifecycle&&position&&dailyPosition&&neutralRsi&&healthyVolume&&sixtyPosition&&slope);
  }

  function style(){
    if($('#hourly60ScreenerStyle'))return;
    const s=document.createElement('style');
    s.id='hourly60ScreenerStyle';
    s.textContent=`
      #h60ModeBar{display:none;margin:8px 0 12px;padding:4px;border:1px solid var(--line);border-radius:12px;background:var(--soft);gap:4px}
      #h60ModeBar button{flex:1;border:0;border-radius:9px;padding:9px 10px;background:transparent;color:var(--text);font-weight:800;font-size:.78rem}
      #h60ModeBar button.active{background:var(--card);box-shadow:0 1px 4px rgba(0,0,0,.08)}
      #h60Screener{display:none}
      #radarPanel.h60-screen-active #radarSummary,#radarPanel.h60-screen-active .toolbar,#radarPanel.h60-screen-active #cards,#radarPanel.h60-screen-active #loadMore{display:none!important}
      .h60-screen-head{margin-bottom:10px}.h60-screen-meta{font-size:.68rem;color:var(--muted);line-height:1.45;margin:5px 2px 10px}
      .h60-cat-row{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px;margin-bottom:8px}
      .h60-cat-row button{border:1px solid var(--line);border-radius:10px;background:var(--card);padding:8px 5px;color:var(--text);font-size:.68rem;font-weight:800;line-height:1.25}
      .h60-cat-row button.active{outline:2px solid rgba(47,104,82,.28);background:var(--soft)}
      .h60-cat-row button.unheated{background:color-mix(in srgb,#f4b942 12%,var(--card));border-color:color-mix(in srgb,#f4b942 38%,var(--line))}
      .h60-cat-row button.unheated.active{background:color-mix(in srgb,#f4b942 22%,var(--card));outline-color:rgba(190,128,28,.34)}
      .h60-cat-row strong{display:block;font-size:.84rem;margin-top:2px}
      .h60-tools{display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;gap:7px;margin-bottom:10px}
      .h60-tools input,.h60-tools select{min-width:0;width:100%;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--text);padding:9px;font-size:.72rem}
      #h60Cards{display:grid;gap:10px}
      .h60-screen-card{cursor:pointer;border:1px solid var(--line);border-radius:14px;background:var(--card);padding:12px;box-shadow:var(--shadow,0 1px 3px rgba(0,0,0,.04))}
      .h60-screen-card:active{transform:translateY(1px)}
      .h60-card-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
      .h60-card-code{font-size:.72rem;color:var(--muted);font-weight:800}.h60-card-name{font-size:1rem;font-weight:900;margin-top:2px}
      .h60-life{font-size:.72rem;font-weight:900;border:1px solid var(--line);border-radius:999px;padding:5px 8px;white-space:nowrap}
      .h60-card-price{display:flex;align-items:baseline;justify-content:space-between;margin-top:10px;padding-top:9px;border-top:1px solid var(--line)}
      .h60-card-price b{font-size:1.12rem}.h60-card-price span{font-size:.67rem;color:var(--muted)}
      .h60-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:9px}
      .h60-metrics div{background:var(--soft);border-radius:9px;padding:7px}.h60-metrics span{display:block;color:var(--muted);font-size:.61rem}.h60-metrics b{display:block;margin-top:2px;font-size:.76rem}
      .h60-unheated-evidence{margin-top:8px;padding:7px 8px;border-radius:9px;background:color-mix(in srgb,#f4b942 10%,var(--soft));font-size:.63rem;color:var(--muted);line-height:1.45}
      .h60-unheated-evidence b{color:var(--text)}
      .h60-card-foot{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-top:9px;font-size:.65rem;color:var(--muted)}
      .h60-empty{padding:26px 10px;text-align:center;color:var(--muted);font-size:.78rem}
      @media(max-width:620px){.h60-cat-row{grid-template-columns:repeat(2,minmax(0,1fr))}.h60-cat-row button:first-child{grid-column:span 2}.h60-tools{grid-template-columns:1fr 1fr}.h60-tools input{grid-column:span 2}.h60-metrics{grid-template-columns:1fr 1fr}}
    `;
    document.head.appendChild(s);
  }

  function mount(){
    if(mounted)return;
    const panel=$('#radarPanel'),head=panel?.querySelector('.section-head');
    if(!panel||!head)return;
    style();
    const bar=document.createElement('div');
    bar.id='h60ModeBar';
    bar.innerHTML='<button type="button" data-h60-mode="v2" class="active">V2 盤後</button><button type="button" data-h60-mode="hourly60">60分K</button>';
    head.insertAdjacentElement('afterend',bar);
    const sc=document.createElement('div');
    sc.id='h60Screener';
    sc.innerHTML=`<div class="h60-screen-head"><div class="h60-cat-row" id="h60Cats"></div><div class="h60-tools"><input id="h60Search" type="search" placeholder="搜尋代號／名稱"><select id="h60Position"><option value="">全部位置</option><option value="GREEN">🟢 位置舒服</option><option value="YELLOW">🟡 等回踩</option><option value="ORANGE">🟠 偏延伸</option><option value="RED">🔴 過熱／失效</option></select><select id="h60Sector"><option value="">全部族群／產業</option></select><select id="h60Sort"><option value="combined">綜合分優先</option><option value="score60">60K結構分</option><option value="newcross">新金叉優先</option><option value="near20">靠近20T優先</option></select></div><div class="h60-screen-meta" id="h60Meta">讀取60分K資料…</div></div><div id="h60Cards"></div>`;
    bar.insertAdjacentElement('afterend',sc);
    bar.addEventListener('click',e=>{const b=e.target.closest('[data-h60-mode]');if(b)setMode(b.dataset.h60Mode)});
    sc.addEventListener('click',e=>{
      const preset=e.target.closest('[data-h60-preset]');
      if(preset){state.preset=preset.dataset.h60Preset;state.category='';render();return}
      const cat=e.target.closest('[data-h60-cat]');
      if(cat){state.category=cat.dataset.h60Cat;state.preset='';render();return}
      const card=e.target.closest('.h60-screen-card[data-code]');
      if(card){document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code:card.dataset.code,source:'hourly60-screener'}}))}
    });
    sc.addEventListener('input',e=>{if(e.target.id==='h60Search'){state.search=e.target.value.trim().toLowerCase();renderCards()}});
    sc.addEventListener('change',e=>{
      if(e.target.id==='h60Position')state.position=e.target.value;
      if(e.target.id==='h60Sector')state.sector=e.target.value;
      if(e.target.id==='h60Sort')state.sort=e.target.value;
      renderCards();
    });
    mounted=true;
    try{state.mode=localStorage.getItem(storeKey)==='hourly60'?'hourly60':'v2'}catch(_){state.mode='v2'}
    syncView();
  }

  async function load(){
    if(state.payload||loading)return;
    loading=true;
    try{
      let r=await fetch(`../data/hourly.json?t=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error(`hourly ${r.status}`);
      state.payload=await r.json();
      hydrateControls();
    }catch(err){
      console.warn('60K screener load failed',err);
      const meta=$('#h60Meta');if(meta)meta.textContent='60分K資料讀取失敗，請按重新整理後再試。';
    }finally{loading=false}
  }

  function hydrateControls(){
    const sectors=[...new Set(rows().map(r=>String(r.sector_group||r.industry_name||'').trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'zh-Hant'));
    const sel=$('#h60Sector');
    if(sel){const current=state.sector;sel.innerHTML='<option value="">全部族群／產業</option>'+sectors.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');sel.value=current}
    render();
  }

  function filtered(){
    let out=rows().filter(r=>{
      if(state.preset==='unheated'&&!isUnheatedStart(r))return false;
      if(state.category&&r.category60!==state.category)return false;
      if(state.position&&r.entry_light!==state.position)return false;
      const sec=String(r.sector_group||r.industry_name||'').trim();
      if(state.sector&&sec!==state.sector)return false;
      if(state.search&&!`${r.code||''} ${r.name||''}`.toLowerCase().includes(state.search))return false;
      return true;
    });
    const sorters={
      combined:(a,b)=>(n(b.combined_score)??-999)-(n(a.combined_score)??-999)||(n(b.score60)??-999)-(n(a.score60)??-999),
      score60:(a,b)=>(n(b.score60)??-999)-(n(a.score60)??-999)||(n(b.combined_score)??-999)-(n(a.combined_score)??-999),
      newcross:(a,b)=>{const ca=CAT[a.category60]?.order??9,cb=CAT[b.category60]?.order??9;if(ca!==cb)return ca-cb;return (n(a.cross_age)??999)-(n(b.cross_age)??999)},
      near20:(a,b)=>Math.abs(n(a.price_vs20_60_pct)??999)-Math.abs(n(b.price_vs20_60_pct)??999)
    };
    return out.sort(sorters[state.sort]||sorters.combined);
  }

  function renderCats(){
    const all=rows(),counts={};all.forEach(r=>counts[r.category60]=(counts[r.category60]||0)+1);
    const unheated=all.filter(isUnheatedStart).length;
    const btns=[`<button type="button" data-h60-cat="" class="${state.category||state.preset?'':'active'}">全部60K<strong>${all.length}</strong></button>`,`<button type="button" data-h60-preset="unheated" class="unheated ${state.preset==='unheated'?'active':''}">✨ 未過熱啟動<strong>${unheated}</strong></button>`];
    for(const [key,v] of Object.entries(CAT))btns.push(`<button type="button" data-h60-cat="${key}" class="${state.category===key?'active':''}">${v.icon} ${v.label}<strong>${counts[key]||0}</strong></button>`);
    const host=$('#h60Cats');if(host)host.innerHTML=btns.join('');
  }

  function card(r){
    const life=CAT[r.category60]||{icon:'⚪',label:'60K觀察'};
    const sec=String(r.sector_group||r.industry_name||'分類待補');
    const dirs=`20T${DIR[r.dir20]||'—'} · 60T${DIR[r.dir60]||'—'} · 240T${DIR[r.dir240]||'—'}`;
    const cross=r.category60==='PRE_CROSS'?'20T 接近 60T':n(r.cross_age)==null?'金叉根數待補':`金叉 ${fmt(r.cross_age,0)} 根`;
    const launch=isUnheatedStart(r)?`<div class="h60-unheated-evidence"><b>✨ 未過熱啟動</b> · RSI ${fmt(r.daily_rsi,1)} · 量比 ${fmt(r.vol_ratio60day,2)}x · 日K距20MA ${pct(r.daily_dist20,1)}</div>`:'';
    return `<article class="h60-screen-card card" data-code="${esc(r.code)}" tabindex="0" role="button" aria-label="開啟 ${esc(r.code)} ${esc(r.name)} 詳情"><div class="h60-card-top"><div><div class="h60-card-code">${esc(r.code)} · ${esc(sec)}</div><div class="h60-card-name">${esc(r.name||'')}</div></div><div class="h60-life">${life.icon} ${life.label}</div></div><div class="h60-card-price"><b>${fmt(r.price,2)}</b><span>${esc(POS[r.entry_light]||r.entry_light_label||'位置待補')}</span></div><div class="h60-metrics"><div><span>60K結構分</span><b>${fmt(r.score60,0)}</b></div><div><span>綜合分</span><b>${fmt(r.combined_score,1)}</b></div><div><span>距20T</span><b>${pct(r.price_vs20_60_pct,2)}</b></div><div><span>金叉狀態</span><b>${esc(cross)}</b></div></div>${launch}<div class="h60-card-foot"><span>${esc(dirs)}</span><span>20/60差 ${pct(r.gap20_60_pct,2)}</span><span>籌碼 ${esc(String(r.chip_date||'—').slice(5).replace('-','/'))}</span></div></article>`;
  }

  function renderCards(){
    if(state.mode!=='hourly60')return;
    const list=filtered(),host=$('#h60Cards'),meta=$('#h60Meta');
    if(meta){
      const d=String(state.payload?.trade_date||'—'),u=String(state.payload?.updated_at||'');
      const presetText=state.preset==='unheated'?' · 未過熱啟動＝金叉前夕/剛啟動＋日K距20MA 0～7%＋RSI 40～65＋量比1.0～1.8＋位置不過熱。':'';
      meta.textContent=`60分K Engine 資料日 ${d}${u?` · 更新 ${u.replace('T',' ').slice(0,16)}`:''} · 目前 ${list.length} 檔。這是獨立60K技術篩選，不等同 V2 Stage。${presetText}`;
    }
    if($('#countText'))$('#countText').textContent=`60分K · ${list.length} 檔`;
    if(host)host.innerHTML=list.length?list.map(card).join(''):'<div class="h60-empty">目前沒有符合這組 60分K 條件的股票。</div>';
  }

  function render(){renderCats();renderCards()}

  async function setMode(mode){
    state.mode=mode==='hourly60'?'hourly60':'v2';
    try{localStorage.setItem(storeKey,state.mode)}catch(_){}
    syncView();
    if(state.mode==='hourly60'){await load();render()}
  }

  function syncView(){
    if(!mounted)return;
    const close=activeView()==='close',bar=$('#h60ModeBar'),sc=$('#h60Screener'),panel=$('#radarPanel');
    if(bar)bar.style.display=close?'flex':'none';
    if(!close){panel?.classList.remove('h60-screen-active');if(sc)sc.style.display='none';return}
    [...bar.querySelectorAll('[data-h60-mode]')].forEach(b=>b.classList.toggle('active',b.dataset.h60Mode===state.mode));
    const on=state.mode==='hourly60';
    panel?.classList.toggle('h60-screen-active',on);
    if(sc)sc.style.display=on?'block':'none';
    const title=$('#rankingTitle');if(title)title.textContent=on?'60分K篩選':'明日優先';
    if(on){load().then(render)}
  }

  function openFromKeyboard(e){
    if(e.key!=='Enter'&&e.key!==' ')return;
    const c=e.target.closest?.('.h60-screen-card[data-code]');if(!c)return;
    e.preventDefault();document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code:c.dataset.code,source:'hourly60-screener'}}));
  }

  function boot(){mount();document.addEventListener('keydown',openFromKeyboard);document.addEventListener('radar:view-rendered',()=>setTimeout(syncView,30));document.addEventListener('radar:data-reloaded',()=>{state.payload=null;if(activeView()==='close'&&state.mode==='hourly60')load()});document.addEventListener('click',e=>{if(e.target.closest?.('.tab'))setTimeout(syncView,80)});setInterval(syncView,1200)}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();