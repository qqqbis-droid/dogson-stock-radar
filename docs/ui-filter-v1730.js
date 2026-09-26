(()=>{
  if(window.__DOGSON_FILTER_V1730__) return;
  window.__DOGSON_FILTER_V1730__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const clean=s=>String(s??'').replace(/\s+/g,' ').trim();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};

  const state={stage:null,decision:null};
  const stageDefs={
    setup:{label:'🌱 蓄勢',legacy:'蓄勢待發',rx:/蓄勢/},
    launch:{label:'🔥 剛啟動',legacy:'剛啟動',rx:/剛啟動/},
    pull:{label:'🟡 回踩',legacy:'回踩承接',rx:/回踩/},
    trend:{label:'🚂 趨勢',legacy:'趨勢持有',rx:/趨勢|持有/},
    weak:{label:'⚠️ 轉弱／失效',legacy:'轉弱警戒',rx:/轉弱|失效/},
    hot:{label:'🚫 過熱',legacy:'過熱不追',rx:/過熱/}
  };
  const decisionDefs={
    green:{label:'🟢 位置可觀察'},
    yellow:{label:'🟡 位置待確認'},
    focus:{label:'✨ 精選機會'}
  };

  let innerRender=null;
  let wrapping=false;
  let syncTimer=null;
  let lastCount=0;
  let lastView='';

  function modeNow(){try{return mode||'intraday'}catch{return'intraday'}}
  function portfolioNow(){try{return !!portfolioOnly}catch{return false}}
  function watchNow(){try{return !!watchOnly}catch{return false}}
  function liveReady(){return window.DOGSON_INTRADAY_LIVE_READY===true}
  function viewKey(){return `${modeNow()}|${portfolioNow()?'portfolio':'scan'}`}

  function stageOf(r){
    try{return clean(stageKey(r?.category))}catch{return clean(r?.category||r?.stage||'觀察')}
  }
  function stageMatch(r,key){
    if(!key)return true;
    const d=stageDefs[key];
    return d?d.rx.test(stageOf(r)):true;
  }
  function canonicalRows(m=modeNow()){
    try{
      if(m==='close')return Array.isArray(closeRows)?closeRows:[];
      if(m==='intraday')return liveReady()?(Array.isArray(intraRows)?intraRows:[]):(Array.isArray(closeRows)?closeRows:[]);
      if(m==='daytrade')return Array.isArray(daytradeRows)?daytradeRows:[];
    }catch{}
    return [];
  }
  function marketFor(m){
    try{
      if(m==='close'||(m==='intraday'&&!liveReady()))return typeof closeMarket!=='undefined'?closeMarket:undefined;
      return typeof intraMarket!=='undefined'?intraMarket:undefined;
    }catch{return undefined}
  }
  function decisionKey(r,m){
    if(m==='close'||(m==='intraday'&&!liveReady())){
      const st=stageOf(r),p=num(r?.entry_position_score);
      if(/轉弱|失效|過熱/.test(st))return'red';
      if(p===null)return'yellow';
      if(p>=70)return'green';
      if(p>=50)return'yellow';
      return'red';
    }
    try{
      const d=entryDecision(r,marketFor(m));
      if(['green','yellow','red'].includes(d?.key))return d.key;
    }catch{}
    const s=num(r?.intraday_score??r?.score)??0;
    return s>=75?'green':s>=58?'yellow':'red';
  }
  function focusMatch(r,m){
    const st=stageOf(r);
    if(/轉弱|失效|過熱/.test(st))return false;
    if(m==='close'||(m==='intraday'&&!liveReady())){
      const q=num(r?.swing_quality_score??r?.score??r?.close_score)??0;
      const p=num(r?.entry_position_score)??0;
      return q>=72&&p>=60;
    }
    const d=decisionKey(r,m);
    if(d==='green')return true;
    if(d!=='yellow')return false;
    const c=r?.intraday_components||{};
    const score=num(r?.intraday_score??r?.score)??0;
    return score>=65&&(num(c?.price_structure)??0)>=15&&(num(c?.flow_volume)??0)>=10&&(num(c?.relative_strength)??0)>=6&&(num(c?.sector)??0)>=6;
  }
  function decisionMatch(r,m,key){
    if(!key)return true;
    if(key==='focus')return focusMatch(r,m);
    return decisionKey(r,m)===key;
  }
  function filteredRows(m=modeNow()){
    return canonicalRows(m).filter(r=>stageMatch(r,state.stage)&&decisionMatch(r,m,state.decision));
  }
  function visibleCount(arr){
    let out=Array.isArray(arr)?arr.slice():[];
    try{if(watchOnly&&typeof watched==='function')out=out.filter(r=>watched(r.code))}catch{}
    const q=clean($('#q')?.value).toLowerCase();
    if(q)out=out.filter(r=>String(r?.code||'').toLowerCase()===q||String(r?.name||'').toLowerCase().includes(q));
    return out.length;
  }

  function forceLegacyNeutral(){
    try{filter='all'}catch{}
    $$('.filter[data-f]').forEach(b=>b.classList.toggle('on',b.dataset.f==='all'));
  }

  function installRender(){
    if(typeof render!=='function')return false;
    if(render.__dogsonFilterV1730)return true;
    innerRender=render;
    const wrapped=function(...args){
      if(wrapping)return innerRender.apply(this,args);
      const m=modeNow();
      if(!['intraday','close'].includes(m)||portfolioNow()){
        const out=innerRender.apply(this,args);scheduleSync();return out;
      }
      wrapping=true;
      const active=!!(state.stage||state.decision);
      const filtered=active?filteredRows(m):canonicalRows(m).slice();
      lastCount=visibleCount(filtered);
      let oldIntra,oldClose,oldRows,oldFilter;
      try{oldIntra=intraRows}catch{}
      try{oldClose=closeRows}catch{}
      try{oldRows=rows}catch{}
      try{oldFilter=filter}catch{}
      try{
        forceLegacyNeutral();
        if(active){
          if(m==='close')closeRows=filtered;
          else if(liveReady())intraRows=filtered;
          else{closeRows=filtered;intraRows=filtered;}
          try{rows=filtered}catch{}
        }
        return innerRender.apply(this,args);
      }finally{
        try{intraRows=oldIntra}catch{}
        try{closeRows=oldClose}catch{}
        try{rows=oldRows}catch{}
        try{filter=oldFilter??'all'}catch{}
        wrapping=false;
        scheduleSync();
      }
    };
    // Keep safety-wrapper markers on the outer function. Without this,
    // an already-installed accuracy wrapper may think it disappeared and
    // wrap render again, creating a recursive wrapper chain.
    Object.keys(innerRender).forEach(k=>{try{wrapped[k]=innerRender[k]}catch{}});
    wrapped.__dogsonFilterV1730=true;
    wrapped.__dogsonFilterInner=innerRender;
    render=wrapped;
    return true;
  }

  function labels(){
    const a=[];
    if(state.stage&&stageDefs[state.stage])a.push(stageDefs[state.stage].label);
    if(state.decision&&decisionDefs[state.decision])a.push(decisionDefs[state.decision].label);
    if(watchNow())a.push('⭐ 關注');
    return a;
  }
  function clearAll(doRender=true){
    state.stage=null;state.decision=null;
    try{watchOnly=false}catch{}
    forceLegacyNeutral();
    if(doRender)try{render()}catch{}
    scheduleSync();
  }
  function toggleStage(key){
    state.stage=state.stage===key?null:key;
    try{render()}catch{}
    scrollToResults();
  }
  function toggleDecision(key){
    state.decision=state.decision===key?null:key;
    try{render()}catch{}
    scrollToResults();
  }
  function toggleWatch(){
    try{watchOnly=!watchOnly}catch{}
    try{render()}catch{}
    scrollToResults();
  }

  function quickHTML(){
    const b=(key,label)=>`<button type="button" data-dogson-decision="${key}" class="${state.decision===key?'active':''}" aria-pressed="${state.decision===key?'true':'false'}">${state.decision===key?'✓ ':''}${label}</button>`;
    const labs=labels();
    return `<div class="dogson-filter-title-v1730">再篩選（可選）</div>
      <div class="dogson-filter-help-v1730">先在「今日雷達」選階段；這裡可再加 1 個位置條件縮小名單。選中的條件會顯示 ✓。</div>
      <div class="dogson-filter-row-v1730">${b('green','🟢 位置可觀察')}${b('yellow','🟡 位置待確認')}${b('focus','✨ 精選機會')}<button type="button" data-dogson-watch="1" class="${watchNow()?'active':''}" aria-pressed="${watchNow()?'true':'false'}">${watchNow()?'✓ ':''}⭐ 關注</button></div>
      <div class="dogson-filter-summary-v1730"><span>目前查看：</span><b>${labs.length?labs.map(esc).join(' × '):'全部股票'}</b><span>符合 ${lastCount} 檔</span>${labs.length?'<button type="button" data-dogson-clear="1">清除</button>':''}</div>`;
  }
  function syncQuick(){
    const q=$('#dogsonQuickFilters');if(!q)return;
    q.innerHTML=quickHTML();
    q.onclick=e=>{
      const b=e.target.closest('button');if(!b)return;
      if(b.dataset.dogsonDecision){toggleDecision(b.dataset.dogsonDecision);return}
      if(b.hasAttribute('data-dogson-watch')){toggleWatch();return}
      if(b.hasAttribute('data-dogson-clear')){clearAll();return}
    };
  }

  function overviewAction(label){
    if(label==='蓄勢')return'setup';
    if(label==='剛啟動')return'launch';
    if(label==='回踩')return'pull';
    if(label==='趨勢中')return'trend';
    if(label==='過熱')return'hot';
    if(/轉弱/.test(label))return'weak';
    return null;
  }
  function syncOverview(){
    const o=$('#dogsonOverviewV160');
    if(!o||portfolioNow()||!['intraday','close'].includes(modeNow()))return;
    let hint=$('.dogson-overview-click-hint-v1730',o);
    if(!hint){hint=document.createElement('div');hint.className='dogson-overview-click-hint-v1730';hint.textContent='點一個階段直接查看股票；再用下方「再篩選」縮小名單。';$('.dogson-section-sub',o)?.after(hint)}
    $$('.dogson-mode-stat-v1701',o).forEach(tile=>{
      const label=clean($('span',tile)?.textContent);
      const key=overviewAction(label);
      if(!key){tile.classList.remove('dogson-filterable-v1730','active');tile.onclick=null;tile.onkeydown=null;tile.removeAttribute('role');tile.removeAttribute('tabindex');return}
      const on=state.stage===key;
      tile.classList.add('dogson-filterable-v1730');tile.classList.toggle('active',on);
      tile.setAttribute('role','button');tile.setAttribute('tabindex','0');tile.setAttribute('aria-pressed',on?'true':'false');
      const n=$('b',tile);if(n){const raw=n.textContent.replace(/^✓\s*/,'');n.textContent=(on?'✓ ':'')+raw}
      tile.onclick=()=>toggleStage(key);
      tile.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tile.click()}};
    });
  }
  function scrollToResults(){setTimeout(()=>($('#cards')||$('.meta'))?.scrollIntoView({behavior:'smooth',block:'start'}),80)}

  function removeLegacyUi(){
    $('#dogsonActiveFilterBar')?.remove();
    $$('.decision-filterbar,.yellow-reasons').forEach(x=>x.remove());
  }
  function installStyle(){
    if($('#dogsonFilterStyle1730'))return;
    const s=document.createElement('style');s.id='dogsonFilterStyle1730';s.textContent=`
      .controls .filters{display:none!important}
      #dogsonQuickFilters{margin-top:8px}
      .dogson-filter-title-v1730{font-size:14px;font-weight:950;color:#30443b;margin:2px 2px 4px}
      .dogson-filter-help-v1730{font-size:10px;line-height:1.55;color:#74817b;margin:0 2px 7px}
      .dogson-filter-row-v1730{display:flex;gap:7px;overflow-x:auto;padding:1px 1px 7px;scrollbar-width:none}.dogson-filter-row-v1730::-webkit-scrollbar{display:none}
      .dogson-filter-row-v1730 button{flex:0 0 auto;white-space:nowrap;border:1px solid #d7e1db;background:#fff;color:#43564d;border-radius:999px;padding:8px 11px;font-size:11px;font-weight:850}
      .dogson-filter-row-v1730 button.active{background:#315f52;color:#fff;border-color:#315f52;box-shadow:0 2px 8px rgba(49,95,82,.16)}
      .dogson-filter-summary-v1730{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:3px 2px 0;color:#74817b;font-size:10px}.dogson-filter-summary-v1730 b{color:#31443b}.dogson-filter-summary-v1730 button{border:0;background:#eef5f1;color:#315f52;border-radius:999px;padding:5px 8px;font-weight:850}
      .dogson-overview-click-hint-v1730{font-size:9.5px;color:#6f7e77;margin-top:5px;font-weight:750}
      .dogson-filterable-v1730{cursor:pointer;transition:.15s}.dogson-filterable-v1730:active{transform:scale(.98)}.dogson-filterable-v1730.active{background:#e8f1ec!important;border-color:#9fc0af!important;box-shadow:inset 0 0 0 1px #b4cebf}.dogson-filterable-v1730.active b{color:#315f52!important}
      html[data-dogson-theme="dark"] .dogson-filter-title-v1730{color:#edf2ef}html[data-dogson-theme="dark"] .dogson-filter-row-v1730 button{background:#252f2a;border-color:#3b4b43;color:#dce9e2}html[data-dogson-theme="dark"] .dogson-filter-row-v1730 button.active{background:#315f52;border-color:#5f8f7e;color:#fff}html[data-dogson-theme="dark"] .dogson-filter-summary-v1730 b{color:#e6eee9}
    `;document.head.appendChild(s);
  }

  function sync(){
    const key=viewKey();
    if(lastView&&key!==lastView){
      state.stage=null;state.decision=null;
      try{watchOnly=false}catch{}
      forceLegacyNeutral();
      const m=modeNow();
      lastCount=visibleCount(canonicalRows(m));
    }
    lastView=key;
    installStyle();removeLegacyUi();
    if(['intraday','close'].includes(modeNow())&&!portfolioNow()){
      if(!(state.stage||state.decision))lastCount=visibleCount(canonicalRows(modeNow()));
      syncQuick();syncOverview();
    }
  }
  function scheduleSync(){clearTimeout(syncTimer);syncTimer=setTimeout(sync,45)}

  function boot(){
    forceLegacyNeutral();
    lastView=viewKey();
    lastCount=visibleCount(canonicalRows(modeNow()));
    installStyle();removeLegacyUi();
    let tries=0;const t=setInterval(()=>{tries++;if(installRender()||tries>100){clearInterval(t);try{render()}catch{}scheduleSync()}},40);
    const root=$('.wrap')||document.body;
    new MutationObserver(scheduleSync).observe(root,{subtree:true,childList:true,characterData:false});
    document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav,#portfolioOnly'))setTimeout(()=>{scheduleSync();try{render()}catch{}},100)},true);
    window.addEventListener('dogson:actionability',()=>setTimeout(()=>{try{render()}catch{}},30));
    window.addEventListener('dogson:data-truth',()=>setTimeout(()=>{try{render()}catch{}},30));
    setTimeout(sync,160);setTimeout(sync,700);
  }

  window.DOGSON_FILTER_UX={
    getState:()=>({stage:state.stage,decision:state.decision,watch:watchNow(),count:lastCount}),
    clear:()=>clearAll(),toggleStage,toggleDecision,
    rows:()=>filteredRows(modeNow())
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
