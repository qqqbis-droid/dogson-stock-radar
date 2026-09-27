(()=>{
  if(window.__DOGSON_MARKET_HOME_V1750__) return;
  window.__DOGSON_MARKET_HOME_V1750__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pick=(o,keys)=>{for(const k of keys){const v=num(o?.[k]);if(v!==null)return v}return null};
  const signed=(v,d=2,suffix='')=>{const n=num(v);return n===null?'—':`${n>0?'+':''}${n.toFixed(d)}${suffix}`};
  const fmtIndex=v=>{const n=num(v);return n===null?'—':n.toLocaleString('zh-TW',{minimumFractionDigits:2,maximumFractionDigits:2})};
  const tone=v=>{const n=num(v);return n===null?'flat':n>0?'up':n<0?'down':'flat'};
  const tradeDay=v=>{const m=String(v||'').match(/20\d{2}-(\d{2})-(\d{2})/);return m?`${Number(m[1])}/${Number(m[2])}`:''};
  const staleIntraday=()=>window.DOGSON_INTRADAY_STALE===true;
  const liveIntraday=()=>window.DOGSON_INTRADAY_LIVE_READY===true&&!staleIntraday();
  const dayActionable=()=>window.DOGSON_DAYTRADE_ACTIONABLE===true&&liveIntraday();

  function currentMode(){try{return typeof mode!=='undefined'&&mode?mode:'intraday'}catch{return'intraday'}}
  function portfolioView(){try{return typeof portfolioOnly!=='undefined'&&!!portfolioOnly}catch{return false}}
  function currentView(){
    if(portfolioView())return'portfolio';
    const m=currentMode();
    return m==='close'?'close':m==='daytrade'?'daytrade':'intraday';
  }
  function getCloseMarket(){try{return typeof closeMarket!=='undefined'&&closeMarket?closeMarket:{}}catch{return{}}}
  function getMarket(){try{return typeof market!=='undefined'&&market?market:{}}catch{return{}}}
  function getMarketLive(){try{return typeof marketLive!=='undefined'&&marketLive?marketLive:{}}catch{return{}}}
  function rotation(){try{return typeof sectorRotation!=='undefined'&&Array.isArray(sectorRotation)?sectorRotation:[]}catch{return[]}}
  function funds(){try{return typeof sectorFunds!=='undefined'&&Array.isArray(sectorFunds)?sectorFunds:[]}catch{return[]}}
  function rowsFor(name){
    try{
      if(name==='close')return typeof closeRows!=='undefined'&&Array.isArray(closeRows)?closeRows:[];
      if(name==='daytrade')return typeof daytradeRows!=='undefined'&&Array.isArray(daytradeRows)?daytradeRows:[];
      return typeof intraRows!=='undefined'&&Array.isArray(intraRows)?intraRows:[];
    }catch{return[]}
  }

  function ensureLayout(){
    const ctl=$('.controls');
    if(!ctl)return false;
    let stock=$('#dogsonStockLayerV1685');
    if(!stock){
      const old=[...ctl.childNodes];
      const marketEl=document.createElement('section');
      marketEl.id='dogsonMarketHomeV1685';
      marketEl.className='dogson-market-home-v1685';
      const flow=document.createElement('section');
      flow.id='dogsonFlowHomeV1685';
      flow.className='dogson-flow-home-v1685';
      stock=document.createElement('section');
      stock.id='dogsonStockLayerV1685';
      stock.className='dogson-stock-layer-v1685';
      stock.innerHTML='<div class="dogson-layer-head-v1685"><div><div class="dogson-layer-kicker-v1685">個股雷達</div><div class="dogson-layer-sub-v1685">搜尋後先顯示全部，再依需要縮小範圍。</div></div></div><div class="dogson-stock-controls-body-v1685"></div>';
      const body=$('.dogson-stock-controls-body-v1685',stock);
      old.forEach(n=>body.appendChild(n));
      ctl.append(marketEl,flow,stock);
      document.documentElement.classList.add('dogson-market-home-ready-v1685');
    }
    const body=$('.dogson-stock-controls-body-v1685',stock);
    [...ctl.childNodes].forEach(n=>{
      if(n.nodeType===1&&['dogsonMarketHomeV1685','dogsonFlowHomeV1685','dogsonStockLayerV1685'].includes(n.id))return;
      if(n!==stock&&body)body.appendChild(n);
    });
    return true;
  }

  function installStyle(){
    if($('#dogson-market-style-v1750'))return;
    const s=document.createElement('style');
    s.id='dogson-market-style-v1750';
    s.textContent=`
      #dogsonFlowHomeV1685{display:block!important}
      #dogsonFlowHomeV1685 .dogson-flow-row-v1750{background:#f8faf8;border:1px solid #e5eae7;border-radius:11px;padding:9px 10px;margin:6px 0;min-width:0}
      #dogsonFlowHomeV1685 .dogson-flow-main-v1750{display:flex;align-items:center;justify-content:space-between;gap:10px}
      #dogsonFlowHomeV1685 .dogson-flow-sector-v1750{min-width:0;font-size:11px;font-weight:900;color:#2b3731;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      #dogsonFlowHomeV1685 .dogson-flow-value-v1750{flex:0 0 auto;font-size:10px;font-weight:900;white-space:nowrap;font-variant-numeric:tabular-nums}
      #dogsonFlowHomeV1685 .dogson-flow-value-v1750.up{color:#c84c4c}
      #dogsonFlowHomeV1685 .dogson-flow-value-v1750.down{color:#2d8a63}
      #dogsonFlowHomeV1685 .dogson-sector-members-v1750{margin-top:7px!important;padding-top:0!important;border-top:0!important}
      #dogsonFlowHomeV1685 .dogson-sector-members-v1750>summary{display:inline-flex;align-items:center;gap:4px;list-style:none;cursor:pointer;font-size:9.5px;font-weight:850;color:#55756b;background:transparent;border:0;padding:2px 0}
      #dogsonFlowHomeV1685 .dogson-sector-members-v1750>summary::-webkit-details-marker{display:none}
      #dogsonFlowHomeV1685 .dogson-sector-members-v1750>summary::after{content:'▾';font-size:9px;transition:transform .16s ease}
      #dogsonFlowHomeV1685 .dogson-sector-members-v1750[open]>summary::after{transform:rotate(180deg)}
      #dogsonFlowHomeV1685 .dogson-sector-member-grid-v1750{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:7px}
      #dogsonFlowHomeV1685 .dogson-flow-stock-v1750{appearance:none;-webkit-appearance:none;width:100%;min-width:0;padding:7px 8px;border:1px solid #dce5df;border-radius:10px;background:#fff;color:#315f52;text-align:left;cursor:pointer;touch-action:manipulation}
      #dogsonFlowHomeV1685 .dogson-flow-stock-v1750:active{transform:scale(.985);background:#f1f6f3}
      #dogsonFlowHomeV1685 .dogson-flow-stock-v1750 b{display:block;font-size:10px;line-height:1.25;color:#315f52;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      #dogsonFlowHomeV1685 .dogson-flow-stock-v1750 small{display:block;margin-top:2px;font-size:8.5px;line-height:1.25;color:#7b8781;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      #dogsonFlowHomeV1685 .dogson-flow-note-v1750{margin-top:8px;padding:8px 10px;border:1px dashed #d8dfdb;border-radius:10px;background:#f7f9f7;color:#67736d;font-size:9.5px;line-height:1.55}
      #dogsonFlowHomeV1685 .dogson-flow-preview-v1685{margin-top:8px}
      #dogsonFlowHomeV1685 .dogson-flow-summary-v1685{margin-top:8px;padding:8px 10px;font-size:11px}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-row-v1750{background:#252b27;border-color:#343b37}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-sector-v1750{color:#eef2ef}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-stock-v1750{background:#252b27;border-color:#3a433e;color:#dce8e1}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-stock-v1750 b{color:#dce8e1}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-stock-v1750 small{color:#9da8a2}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-note-v1750{background:#252b27;border-color:#3a433e;color:#b8c2bc}
      @media(max-width:520px){#dogsonFlowHomeV1685 .dogson-sector-member-grid-v1750{grid-template-columns:1fr}}
    `;
    document.head.appendChild(s);
  }

  function currentMarket(){
    if(currentMode()!=='close'&&!liveIntraday())return getCloseMarket();
    return getMarket();
  }
  function liveMarket(){return liveIntraday()?getMarketLive():{}}
  function indexSnap(symbol,component){
    const live=liveMarket()?.[symbol]||{};
    const current=pick(live,['price','last','close','value','index','last_price','lastPrice'])??pick(component,['price','last','close','value','index']);
    const pct=pick(live,['change_pct','changePct','pct','change_percent'])??pick(component,['change_pct','changePct','pct']);
    let pts=pick(live,['change','change_point','change_points','change_value','diff','delta'])??pick(component,['change','change_point','change_points','change_value','diff','delta']);
    if(pts===null&&current!==null&&pct!==null&&pct!==-100){
      const prev=current/(1+pct/100);
      if(Number.isFinite(prev))pts=current-prev;
    }
    return{current,pct,pts};
  }
  function marketData(){
    const m=currentMarket();
    const intraday=currentMode()!=='close'&&!!m.intraday_only&&liveIntraday();
    const ta=intraday?(m.components?.taiex||{}):(m.taiex||{});
    const ot=intraday?(m.components?.otc||{}):(m.otc||{});
    return{m,tw:indexSnap('^TWII',ta),two:indexSnap('^TWOII',ot)};
  }
  function marketSentence(m,tw,two){
    const state=String(m?.market_mode||'中性');
    const a=num(tw?.pct),b=num(two?.pct);
    if(a!==null&&b!==null&&a*b<0)return`大型與中小型股分歧，先看相對強勢族群；市場目前${state}。`;
    if(state.includes('防守'))return'市場偏防守，新倉先縮小部位並避免追價。';
    if(state.includes('偏多'))return a!==null&&b!==null&&a>0&&b>0?'加權與櫃買同步偏強，可優先找強勢族群。':'市場偏多但仍有分歧，優先看相對強勢族群。';
    return'市場中性，先看資金集中在哪些族群，再挑個股。';
  }
  function originalMarketDetails(){
    const grid=$('.marketgrid',$('#marketbox'));
    return grid?`<div class="dogson-market-detail-copy-v1685">${grid.outerHTML}</div>`:'<div class="dogson-empty-v1685">市場細節更新中…</div>';
  }
  function renderMarket(){
    const host=$('#dogsonMarketHomeV1685');if(!host)return;
    const {m,tw,two}=marketData();
    const score=num(m?.market_score),scoreText=score===null?'—':`${score.toFixed(1)}/15`;
    const state=String(m?.market_mode||'資料更新中');
    const stateClass=state.includes('防守')?'defense':state.includes('偏多')?'bull':'neutral';
    const updated=$('#updated')?.textContent?.trim()||'更新中';
    const date=tradeDay(m?.trade_date||m?.taiex?.date||m?.otc?.date||window.DOGSON_EFFECTIVE_MARKET_DATE);
    const html=`
      <div class="dogson-layer-head-v1685">
        <div><div class="dogson-layer-kicker-v1685">市場環境</div><div class="dogson-market-state-v1685 ${stateClass}">📊 ${esc(state)}</div></div>
        <div class="dogson-market-score-v1685"><b>${esc(scoreText)}</b><span>市場分數</span></div>
      </div>
      <div class="dogson-index-grid-v1685">
        <div class="dogson-index-card-v1685"><div class="dogson-index-name-v1685">加權指數</div><div class="dogson-index-main-v1685">${fmtIndex(tw.current)}</div><div class="dogson-index-change-v1685 ${tone(tw.pct)}"><span>${signed(tw.pts,2)}</span><span>${signed(tw.pct,2,'%')}</span></div></div>
        <div class="dogson-index-card-v1685"><div class="dogson-index-name-v1685">櫃買指數</div><div class="dogson-index-main-v1685">${fmtIndex(two.current)}</div><div class="dogson-index-change-v1685 ${tone(two.pct)}"><span>${signed(two.pts,2)}</span><span>${signed(two.pct,2,'%')}</span></div></div>
      </div>
      <div class="dogson-market-callout-v1685">${esc(marketSentence(m,tw,two))}</div>
      <div class="dogson-market-updated-v1685">交易日 ${esc(date||'—')}｜更新 ${esc(updated)}｜紅漲綠跌</div>
      <details class="dogson-inline-details-v1685"><summary>查看市場細節</summary><div class="dogson-inline-details-body-v1685">${originalMarketDetails()}</div></details>`;
    if(host.dataset.h1750!==html){host.innerHTML=html;host.dataset.h1750=html}
  }

  function intradayFlow(){
    const arr=rotation().filter(x=>num(x?.heat)!==null);
    return{
      hot:[...arr].filter(x=>num(x.heat)>0).sort((a,b)=>num(b.heat)-num(a.heat)),
      cold:[...arr].filter(x=>num(x.heat)<0).sort((a,b)=>num(a.heat)-num(b.heat))
    };
  }
  function closeFlow(){
    const arr=funds().filter(x=>num(x?.today_amount_100m)!==null);
    return{
      hot:[...arr].filter(x=>num(x.today_amount_100m)>0).sort((a,b)=>num(b.today_amount_100m)-num(a.today_amount_100m)),
      cold:[...arr].filter(x=>num(x.today_amount_100m)<0).sort((a,b)=>num(a.today_amount_100m)-num(b.today_amount_100m))
    };
  }
  function flowSpec(){
    const view=currentView();
    if(view==='close')return{view,memberView:'close',closeMode:true,subtitle:'盤後法人族群資金',note:'',...closeFlow()};
    if(view==='portfolio'){
      if(liveIntraday()&&rotation().length)return{view,memberView:'intraday',closeMode:false,subtitle:'庫存｜盤中族群資金背景',note:'',...intradayFlow()};
      return{view,memberView:'close',closeMode:true,subtitle:'庫存｜最近完整盤後法人資金背景',note:'非即時盤中資料，這裡顯示最近完整盤後資金背景。',...closeFlow()};
    }
    if(view==='daytrade'){
      if(dayActionable()&&rotation().length)return{view,memberView:'daytrade',closeMode:false,subtitle:'當沖｜盤中族群資金動能',note:'',...intradayFlow()};
      return{view,memberView:'close',closeMode:true,subtitle:'當沖｜最近完整盤後法人資金背景',note:'目前不是可驗證的即時盤中狀態；以下只作市場背景參考，不作當沖進場訊號。',...closeFlow()};
    }
    if(liveIntraday()&&rotation().length)return{view,memberView:'intraday',closeMode:false,subtitle:'盤中族群資金動能／熱度',note:'',...intradayFlow()};
    return{view,memberView:'close',closeMode:true,subtitle:'盤中｜最近完整盤後法人資金背景',note:'目前沒有合格即時盤中資金資料，改顯示最近完整盤後資金背景。',...closeFlow()};
  }
  function flowValue(x,closeMode){return closeMode?signed(x?.today_amount_100m,1,'億'):`熱度 ${signed(x?.heat,1)}`}
  function sectorKey(r){return String(r?.sector_group||r?.sector||'').trim()}
  function memberScore(r,view){
    if(view==='daytrade')return num(r?.daytrade_score)??num(r?.intraday_score)??num(r?.score);
    return num(r?.intraday_score)??num(r?.swing_quality_score)??num(r?.score);
  }
  function stageLabel(r,view){
    if(view==='daytrade'&&r?.daytrade_state)return String(r.daytrade_state);
    try{if(typeof stageKey==='function')return stageKey(r?.category)||String(r?.category||'觀察')}catch{}
    return String(r?.category||'觀察');
  }
  function membersForSector(sector,view,closeMode){
    const key=String(sector||'').trim();
    if(closeMode){
      try{
        if(typeof closeSectorMembers==='function'){
          const a=closeSectorMembers(key);
          if(Array.isArray(a)&&a.length)return a;
        }
      }catch{}
    }
    const source=rowsFor(closeMode?'close':view==='daytrade'?'daytrade':'intraday');
    return source.filter(r=>sectorKey(r)===key).sort((a,b)=>(memberScore(b,view)??-999)-(memberScore(a,view)??-999)||(num(b?.day_change)??-999)-(num(a?.day_change)??-999));
  }
  function memberButton(r,view){
    const score=memberScore(r,view);
    const scoreText=score===null?'':`${Math.round(score)}分`;
    const stage=stageLabel(r,view);
    return `<button type="button" class="dogson-flow-stock-v1750 peerlink" data-code="${esc(r?.code||'')}"><b>${esc(r?.code||'')} ${esc(r?.name||'')}</b><small>${esc([scoreText,stage].filter(Boolean).join(' · '))}</small></button>`;
  }
  function membersHTML(x,spec){
    const members=membersForSector(x?.sector,spec.memberView,spec.closeMode).slice(0,30);
    const key=`sector:${String(x?.sector||'')}`;
    if(!members.length)return`<details class="dogson-sector-members-v1750" data-flow-key="${esc(key)}"><summary>查看族群個股</summary><div class="dogson-empty-v1685" style="margin-top:7px">目前沒有可用個股資料</div></details>`;
    return `<details class="dogson-sector-members-v1750" data-flow-key="${esc(key)}"><summary>查看族群個股 ${members.length} 檔</summary><div class="dogson-sector-member-grid-v1750">${members.map(r=>memberButton(r,spec.memberView)).join('')}</div></details>`;
  }
  function flowRows(arr,kind,spec,limit){
    if(!arr.length)return`<div class="dogson-empty-v1685">目前沒有明顯${kind==='in'?'流入／吸金':'流出／降溫'}族群</div>`;
    return arr.slice(0,limit).map(x=>`<div class="dogson-flow-row-v1750"><div class="dogson-flow-main-v1750"><div class="dogson-flow-sector-v1750">${esc(x?.sector||'未分類')}</div><div class="dogson-flow-value-v1750 ${kind==='in'?'up':'down'}">${esc(flowValue(x,spec.closeMode))}</div></div>${membersHTML(x,spec)}</div>`).join('');
  }
  function openKeys(host){return new Set($$('details[open][data-flow-key]',host).map(x=>x.dataset.flowKey).filter(Boolean))}
  function restoreKeys(host,keys){$$('details[data-flow-key]',host).forEach(x=>{if(keys.has(x.dataset.flowKey))x.open=true})}
  function renderFlow(){
    const host=$('#dogsonFlowHomeV1685');if(!host)return;
    const spec=flowSpec();
    const opened=openKeys(host);
    const lead=spec.hot.slice(0,3).map(x=>x?.sector).filter(Boolean);
    const sentence=lead.length?`目前資金較集中：${lead.join('、')}。`:'目前沒有明顯集中族群。';
    const note=spec.note?`<div class="dogson-flow-note-v1750">${esc(spec.note)}</div>`:'';
    const html=`
      <div class="dogson-layer-head-v1685"><div><div class="dogson-layer-kicker-v1685">資金流向</div><div class="dogson-layer-sub-v1685">${esc(spec.subtitle)}</div></div></div>
      <div class="dogson-flow-summary-v1685">${esc(sentence)}</div>${note}
      <div class="dogson-flow-preview-v1685">
        <div><div class="dogson-flow-colhead-v1685">${spec.closeMode?'🔴 流入 TOP 3':'🔥 吸金 TOP 3'}</div>${flowRows(spec.hot,'in',spec,3)}</div>
        <div><div class="dogson-flow-colhead-v1685">${spec.closeMode?'🟢 流出 TOP 3':'🧊 降溫 TOP 3'}</div>${flowRows(spec.cold,'out',spec,3)}</div>
      </div>
      <details class="dogson-inline-details-v1685" data-flow-key="all"><summary>查看完整資金流向</summary><div class="dogson-inline-details-body-v1685"><div class="dogson-flow-detail-grid-v1685"><div><div class="dogson-flow-colhead-v1685">主要流入／吸金</div>${flowRows(spec.hot,'in',spec,8)}</div><div><div class="dogson-flow-colhead-v1685">主要流出／降溫</div>${flowRows(spec.cold,'out',spec,8)}</div></div></div></details>`;
    if(host.dataset.h1750!==html){host.innerHTML=html;host.dataset.h1750=html;restoreKeys(host,opened)}
  }
  function render(){if(!ensureLayout())return;installStyle();renderMarket();renderFlow()}
  function watchSource(el){
    if(!el||el.__dogsonMarketWatch1750)return;
    el.__dogsonMarketWatch1750=true;
    let t;
    new MutationObserver(()=>{clearTimeout(t);t=setTimeout(render,80)}).observe(el,{subtree:true,childList:true,characterData:true});
  }
  function boot(){
    render();
    watchSource($('#marketbox'));watchSource($('#rotationbox'));watchSource($('#updated'));
    document.addEventListener('click',e=>{if(e.target?.closest?.('.tab,#dogsonViewNav,#portfolioOnly'))setTimeout(render,100)});
    ['dogson:freshness','dogson:data-truth','dogson:actionability'].forEach(n=>window.addEventListener(n,()=>setTimeout(render,0)));
    setTimeout(render,300);setTimeout(render,1000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
