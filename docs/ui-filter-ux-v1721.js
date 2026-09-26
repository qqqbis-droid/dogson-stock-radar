(()=>{
  if(window.__DOGSON_FILTER_UX_V1721__) return;
  window.__DOGSON_FILTER_UX_V1721__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const clean=s=>String(s??'').replace(/\s+/g,' ').trim();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const ux={stage:null,decision:null};
  let baseRender=null,lastCount=0,syncTimer=null,busy=false;

  const stageDefs={
    setup:{label:'🌱 蓄勢',match:/蓄勢/},
    launch:{label:'🔥 剛啟動',match:/剛啟動/},
    pull:{label:'🟡 回踩',match:/回踩/},
    trend:{label:'🚂 趨勢',match:/趨勢|持有/},
    weak:{label:'⚠️ 轉弱／失效',match:/轉弱|失效/},
    hot:{label:'🚫 過熱',match:/過熱/}
  };
  const decisionDefs={
    green:{label:'🟢 可觀察'},
    yellow:{label:'🟡 等確認'},
    focus:{label:'✨ 精選機會'}
  };

  function currentMode(){try{return mode||'intraday'}catch{return'intraday'}}
  function inPortfolio(){try{return !!portfolioOnly}catch{return false}}
  function isWatch(){try{return !!watchOnly}catch{return false}}
  function stageOf(r){try{return clean(stageKey(r?.category))}catch{return clean(r?.category||'')}}
  function stageMatch(r,key){if(!key)return true;const d=stageDefs[key];return d?d.match.test(stageOf(r)):true}

  function marketFor(m){try{return m==='close'?closeMarket:intraMarket}catch{return undefined}}
  function intradayDecision(r,m){
    try{const d=entryDecision(r,marketFor(m));if(['green','yellow','red'].includes(d?.key))return d.key}catch{}
    const s=num(r?.intraday_score??r?.score)??0;
    return s>=75?'green':s>=58?'yellow':'red';
  }
  function closeDecision(r){
    const st=stageOf(r),p=num(r?.entry_position_score);
    if(/失效|轉弱/.test(st))return'red';
    if(/過熱/.test(st))return'red';
    if(p===null)return'yellow';
    if(p>=70)return'green';
    if(p>=50)return'yellow';
    return'red';
  }
  function decisionKey(r,m){return m==='close'?closeDecision(r):intradayDecision(r,m)}

  function focusMatch(r,m){
    const st=stageOf(r);if(/失效|轉弱|過熱/.test(st))return false;
    if(m==='close'){
      const q=num(r?.swing_quality_score??r?.score??r?.close_score)??0;
      const p=num(r?.entry_position_score)??0;
      return q>=72&&p>=60;
    }
    const d=decisionKey(r,m);if(d==='green')return true;if(d!=='yellow')return false;
    const c=r?.intraday_components||{};
    const score=num(r?.intraday_score??r?.score)??0;
    return score>=65&&(num(c?.price_structure)??0)>=15&&(num(c?.flow_volume)??0)>=10&&(num(c?.relative_strength)??0)>=6&&(num(c?.sector)??0)>=6;
  }

  function decisionMatch(r,m,key){
    if(!key)return true;
    if(key==='focus')return focusMatch(r,m);
    return decisionKey(r,m)===key;
  }
  function filterRows(arr,m){return (Array.isArray(arr)?arr:[]).filter(r=>stageMatch(r,ux.stage)&&decisionMatch(r,m,ux.decision))}

  function forceLegacyStageAll(){
    try{filter='all'}catch{}
    $$('.filter[data-f]').forEach(b=>b.classList.toggle('on',b.dataset.f==='all'));
  }
  function visibleCount(arr){
    let out=arr.slice();
    try{if(watchOnly&&typeof watched==='function')out=out.filter(r=>watched(r.code))}catch{}
    const q=clean($('#q')?.value).toLowerCase();
    if(q)out=out.filter(r=>String(r?.code||'').toLowerCase()===q||String(r?.name||'').toLowerCase().includes(q));
    return out.length;
  }

  function installRenderWrapper(){
    if(baseRender||typeof render!=='function')return false;
    baseRender=render;
    render=function(){
      const m=currentMode();
      if(!['intraday','close'].includes(m)||inPortfolio()){
        const out=baseRender();scheduleSync();return out;
      }
      forceLegacyStageAll();
      let full=[],previousRows;
      try{full=m==='close'?closeRows:intraRows}catch{}
      try{previousRows=rows}catch{}
      const filtered=filterRows(full,m);lastCount=visibleCount(filtered);
      try{
        if(m==='close')closeRows=filtered;else intraRows=filtered;
        try{rows=filtered}catch{}
        return baseRender();
      }finally{
        try{if(m==='close')closeRows=full;else intraRows=full}catch{}
        try{rows=previousRows??(m==='close'?closeRows:intraRows)}catch{}
        scheduleSync();
      }
    };
    return true;
  }

  function clearAll(){
    ux.stage=null;ux.decision=null;
    try{watchOnly=false}catch{}
    forceLegacyStageAll();
    render();
  }
  function toggleStage(key){ux.stage=ux.stage===key?null:key;render()}
  function toggleDecision(key){ux.decision=ux.decision===key?null:key;render()}
  function toggleWatch(){try{watchOnly=!watchOnly}catch{}render()}
  function activeLabels(){
    const a=[];
    if(ux.stage&&stageDefs[ux.stage])a.push(stageDefs[ux.stage].label);
    if(ux.decision&&decisionDefs[ux.decision])a.push(decisionDefs[ux.decision].label);
    if(isWatch())a.push('⭐ 關注');
    return a;
  }
  function isClear(){return !ux.stage&&!ux.decision&&!isWatch()}

  function quickHTML(){
    const active=(kind,key)=>kind==='stage'?ux.stage===key:ux.decision===key;
    const btn=(kind,key,label)=>{const on=active(kind,key);return `<button type="button" class="${on?'active':''}" data-ux-${kind}="${key}" aria-pressed="${on?'true':'false'}">${on?'✓ ':''}${label}</button>`};
    const allOn=isClear();
    const labels=activeLabels();
    return `<div class="dogson-filter-help">可同時選「1 個階段＋1 個條件」；兩個都有 ✓ 時，清單只顯示同時符合的股票。</div>
      <div class="dogson-quick-row dogson-quick-stage-row"><button type="button" class="${allOn?'active':''}" data-ux-clear="1" aria-pressed="${allOn?'true':'false'}">${allOn?'✓ ':''}全部</button>${btn('stage','setup','🌱 蓄勢')}${btn('stage','launch','🔥 剛啟動')}${btn('stage','pull','🟡 回踩')}${btn('stage','trend','🚂 趨勢')}${btn('stage','weak','⚠️ 轉弱／失效')}${btn('stage','hot','🚫 過熱')}</div>
      <div class="dogson-quick-row dogson-quick-decision-row">${btn('decision','green','🟢 可觀察')}${btn('decision','yellow','🟡 等確認')}${btn('decision','focus','✨ 精選機會')}<button type="button" class="${isWatch()?'active':''}" data-ux-watch="1" aria-pressed="${isWatch()?'true':'false'}">${isWatch()?'✓ ':''}⭐ 關注</button></div>
      <div class="dogson-filter-summary-inline"><span>目前篩選：</span><b>${labels.length?labels.map(esc).join(' × '):'全部股票'}</b><span class="dogson-filter-count">符合 ${lastCount} 檔</span>${labels.length?'<button type="button" data-ux-clear="1">清除</button>':''}</div>`;
  }

  function handleQuick(e){
    const b=e.target.closest('button');if(!b)return;
    if(b.hasAttribute('data-ux-clear')){clearAll();return}
    if(b.dataset.uxStage){toggleStage(b.dataset.uxStage);return}
    if(b.dataset.uxDecision){toggleDecision(b.dataset.uxDecision);return}
    if(b.hasAttribute('data-ux-watch')){toggleWatch();return}
  }
  function syncQuick(){
    const q=$('#dogsonQuickFilters');if(!q)return;
    q.onclick=handleQuick;
    const html=quickHTML();if(q.dataset.uxHtml!==html){q.innerHTML=html;q.dataset.uxHtml=html}
  }

  function listBarHTML(){
    const labels=activeLabels();if(!labels.length)return'';
    return `<span class="dogson-active-filter-label">目前篩選</span><div class="dogson-active-filter-chips">${labels.map(x=>`<span>${esc(x)}</span>`).join('')}</div><b>符合 ${lastCount} 檔</b><button type="button" data-ux-clear="1">清除</button>`;
  }
  function syncListBar(){
    let bar=$('#dogsonActiveFilterBar');
    if(!bar){bar=document.createElement('div');bar.id='dogsonActiveFilterBar';bar.className='dogson-active-filter-bar';const anchor=$('.meta')||$('#cards');anchor?.before(bar)}
    const html=listBarHTML();bar.hidden=!html;if(html&&bar.dataset.h!==html){bar.innerHTML=html;bar.dataset.h=html;bar.onclick=e=>{if(e.target.closest('[data-ux-clear]'))clearAll()}}
  }

  function overviewAction(label){
    if(label==='蓄勢')return['stage','setup'];
    if(label==='剛啟動')return['stage','launch'];
    if(label==='回踩')return['stage','pull'];
    if(label==='趨勢中')return['stage','trend'];
    if(label==='過熱')return['stage','hot'];
    if(/轉弱/.test(label))return['stage','weak'];
    if(label==='位置可觀察'||label==='可試單')return['decision','green'];
    return null;
  }
  function scrollToResults(){setTimeout(()=>($('#dogsonActiveFilterBar')||$('#cards'))?.scrollIntoView({behavior:'smooth',block:'start'}),90)}
  function syncOverview(){
    const m=currentMode(),o=$('#dogsonOverviewV160');if(!o||!['intraday','close'].includes(m)||inPortfolio())return;
    let hint=$('.dogson-overview-click-hint',o);if(!hint){hint=document.createElement('div');hint.className='dogson-overview-click-hint';hint.textContent='點任一格，就直接查看符合的股票。';$('.dogson-section-sub',o)?.after(hint)}
    $$('.dogson-mode-stat-v1701',o).forEach(tile=>{
      const label=clean($('span',tile)?.textContent);const action=overviewAction(label);
      if(!action){tile.classList.remove('dogson-overview-filterable','dogson-overview-filter-active');tile.removeAttribute('role');tile.removeAttribute('tabindex');tile.onclick=null;return}
      const [kind,key]=action;const on=kind==='stage'?ux.stage===key:ux.decision===key;
      tile.classList.add('dogson-overview-filterable');tile.classList.toggle('dogson-overview-filter-active',on);tile.setAttribute('role','button');tile.setAttribute('tabindex','0');tile.setAttribute('aria-pressed',on?'true':'false');
      const b=$('b',tile);if(b){const raw=b.textContent.replace(/^✓\s*/,'');b.textContent=(on?'✓ ':'')+raw}
      tile.onclick=()=>{kind==='stage'?toggleStage(key):toggleDecision(key);scrollToResults()};
      tile.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tile.click()}};
    });
  }

  function neutralizeLegacyFilters(){
    const q=$('[data-quality]');if(q&&/ON/.test(q.textContent||'')){try{q.click()}catch{}}
    $$('.decision-filterbar.event-quality').forEach(x=>x.remove());
    $$('#changebox .changecount').forEach(x=>{x.onclick=null;x.setAttribute('aria-disabled','true')});
  }

  function installStyle(){
    if($('#dogsonFilterUxStyle1721'))return;
    const s=document.createElement('style');s.id='dogsonFilterUxStyle1721';s.textContent=`
      .dogson-filter-help{font-size:10px;line-height:1.55;color:#728079;margin:0 2px 6px}
      #dogsonQuickFilters .dogson-quick-row{padding-bottom:6px}
      #dogsonQuickFilters button.active{background:#315f52!important;color:#fff!important;border-color:#315f52!important;box-shadow:0 2px 8px rgba(49,95,82,.16)}
      .dogson-filter-summary-inline{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:3px 2px 0;font-size:10px;color:#74807b}.dogson-filter-summary-inline b{color:#33443d}.dogson-filter-summary-inline button,.dogson-active-filter-bar button{border:0;background:transparent;color:#315f52;font-weight:850;padding:3px 5px}
      .dogson-filter-count{margin-left:auto}
      .dogson-active-filter-bar{scroll-margin-top:94px;display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin:8px 0 6px;padding:9px 10px;border:1px solid #cfded6;border-radius:12px;background:#f1f7f3;color:#52635b;font-size:10px}.dogson-active-filter-bar[hidden]{display:none!important}.dogson-active-filter-label{font-weight:850;color:#315f52}.dogson-active-filter-chips{display:flex;gap:5px;flex-wrap:wrap}.dogson-active-filter-chips span{padding:4px 7px;border-radius:999px;background:#fff;border:1px solid #d9e5de;color:#315f52;font-weight:800}.dogson-active-filter-bar>b{margin-left:auto;color:#34443d}
      .dogson-overview-click-hint{font-size:9.5px;color:#6f7e77;margin-top:5px;font-weight:750}.dogson-overview-filterable{cursor:pointer;transition:.15s}.dogson-overview-filterable:active{transform:scale(.98)}.dogson-overview-filter-active{background:#e8f1ec!important;border-color:#9fc0af!important;box-shadow:inset 0 0 0 1px #b4cebf}.dogson-overview-filter-active b{color:#315f52!important}
      .decision-filterbar.event-quality,#entrySummary .decision-filterbar,#entrySummary .yellow-reasons{display:none!important}#changebox .changecount{pointer-events:none!important}
      html[data-dogson-theme="dark"] #dogsonQuickFilters button.active{background:#315f52!important;color:#fff!important;border-color:#5f8f7e!important}html[data-dogson-theme="dark"] .dogson-active-filter-bar{background:#202b25;border-color:#3f5a4c;color:#b9c6bf}html[data-dogson-theme="dark"] .dogson-active-filter-chips span{background:#252f2a;border-color:#3b4b43;color:#dce9e2}html[data-dogson-theme="dark"] .dogson-filter-summary-inline b{color:#e6eee9}
      @media(max-width:560px){.dogson-filter-count{margin-left:0}.dogson-active-filter-bar>b{margin-left:0}}
    `;document.head.appendChild(s);
  }

  function scheduleSync(){clearTimeout(syncTimer);syncTimer=setTimeout(sync,45)}
  function sync(){
    if(busy)return;busy=true;
    try{installStyle();neutralizeLegacyFilters();syncQuick();syncOverview();syncListBar()}finally{busy=false}
  }
  function boot(){
    installStyle();
    if(!installRenderWrapper()){let tries=0;const t=setInterval(()=>{tries++;if(installRenderWrapper()||tries>80){clearInterval(t);if(baseRender)render()}},50)}else render();
    const root=$('.wrap')||document.body;new MutationObserver(scheduleSync).observe(root,{subtree:true,childList:true,characterData:false});
    document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav,#watchOnly,#portfolioOnly'))setTimeout(scheduleSync,80)});
    setTimeout(sync,150);setTimeout(sync,700);
  }

  window.DOGSON_FILTER_UX={getState:()=>({stage:ux.stage,decision:ux.decision,watch:isWatch(),count:lastCount}),clear:clearAll,toggleStage,toggleDecision};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();