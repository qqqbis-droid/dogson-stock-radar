(()=>{
  if(window.__DOGSON_MARKET_HOME_V1685__) return;
  window.__DOGSON_MARKET_HOME_V1685__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pick=(o,keys)=>{for(const k of keys){const v=num(o?.[k]);if(v!==null)return v}return null};
  const signed=(v,d=2,suffix='')=>{const n=num(v);return n===null?'—':`${n>0?'+':''}${n.toFixed(d)}${suffix}`};
  const fmtIndex=v=>{const n=num(v);return n===null?'—':n.toLocaleString('zh-TW',{minimumFractionDigits:2,maximumFractionDigits:2})};
  const tone=v=>{const n=num(v);return n===null?'flat':n>0?'up':n<0?'down':'flat'};
  const staleIntraday=()=>!!window.DOGSON_INTRADAY_STALE;
  const liveIntraday=()=>window.DOGSON_INTRADAY_LIVE_READY===true&&!staleIntraday();
  const dayActionable=()=>window.DOGSON_DAYTRADE_ACTIONABLE===true&&liveIntraday();
  const tradeDay=v=>{const m=String(v||'').match(/20\d{2}-(\d{2})-(\d{2})/);return m?`${Number(m[1])}/${Number(m[2])}`:''};

  function currentMode(){try{return mode||'intraday'}catch{return'intraday'}}
  function portfolioView(){try{return !!portfolioOnly}catch{return false}}
  function currentView(){
    if(portfolioView())return'portfolio';
    const m=currentMode();
    return m==='close'?'close':m==='daytrade'?'daytrade':'intraday';
  }
  function closeMarketData(){try{return closeMarket||{}}catch{return{}}}
  function currentMarket(){
    if(currentMode()!=='close'&&staleIntraday()) return closeMarketData();
    try{return market||{}}catch{return{}}
  }
  function liveMarket(){if(staleIntraday())return{};try{return marketLive||{}}catch{return{}}}
  function rotation(){try{return Array.isArray(sectorRotation)?sectorRotation:[]}catch{return[]}}
  function funds(){try{return Array.isArray(sectorFunds)?sectorFunds:[]}catch{return[]}}

  function ensureLayout(){
    const ctl=$('.controls');
    if(!ctl)return false;
    let stock=$('#dogsonStockLayerV1685');
    if(!stock){
      const old=[...ctl.childNodes];
      const market=document.createElement('section');
      market.id='dogsonMarketHomeV1685';
      market.className='dogson-market-home-v1685';
      const flow=document.createElement('section');
      flow.id='dogsonFlowHomeV1685';
      flow.className='dogson-flow-home-v1685';
      stock=document.createElement('section');
      stock.id='dogsonStockLayerV1685';
      stock.className='dogson-stock-layer-v1685';
      stock.innerHTML='<div class="dogson-layer-head-v1685"><div><div class="dogson-layer-kicker-v1685">個股雷達</div><div class="dogson-layer-sub-v1685">搜尋後先顯示全部，依分數由高到低；需要時再用篩選按鈕縮小範圍。</div></div></div><div class="dogson-stock-controls-body-v1685"></div>';
      const body=$('.dogson-stock-controls-body-v1685',stock);
      old.forEach(n=>body.appendChild(n));
      ctl.append(market,flow,stock);
      document.documentElement.classList.add('dogson-market-home-ready-v1685');
    }
    const body=$('.dogson-stock-controls-body-v1685',stock);
    [...ctl.childNodes].forEach(n=>{
      if(n.nodeType===1&&['dogsonMarketHomeV1685','dogsonFlowHomeV1685','dogsonStockLayerV1685'].includes(n.id))return;
      if(n!==stock&&body)body.appendChild(n);
    });
    return true;
  }

  function installFlowStyle(){
    if($('#dogson-flow-member-style-v1685'))return;
    const s=document.createElement('style');
    s.id='dogson-flow-member-style-v1685';
    s.textContent=`
      #dogsonFlowHomeV1685{display:block!important}
      #dogsonFlowHomeV1685 .dogson-flow-row-v1685{display:block!important}
      #dogsonFlowHomeV1685 .dogson-flow-row-top-v1685{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;list-style:none;cursor:pointer}
      #dogsonFlowHomeV1685 .dogson-flow-row-top-v1685::-webkit-details-marker{display:none}
      #dogsonFlowHomeV1685 .dogson-flow-row-side-v1685{display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex:0 0 auto}
      #dogsonFlowHomeV1685 .dogson-flow-row-side-v1685 small{font-size:8.5px;color:#7b8781;white-space:nowrap}
      #dogsonFlowHomeV1685 .dogson-flow-sector-v1685[open]>.dogson-flow-row-top-v1685{padding-bottom:7px}
      #dogsonFlowHomeV1685 .dogson-flow-sector-v1685[open] .dogson-flow-row-side-v1685 small{color:#315f52}
      #dogsonFlowHomeV1685 .dogson-flow-row-copy-v1685{min-width:0}
      #dogsonFlowHomeV1685 .dogson-flow-row-copy-v1685>b{display:block;font-size:11px;color:#2b3731;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
      #dogsonFlowHomeV1685 .dogson-flow-row-copy-v1685>span{display:block;font-size:9px;color:#7b8781;line-height:1.45;margin-top:3px;white-space:normal;overflow:visible}
      #dogsonFlowHomeV1685 .dogson-flow-row-top-v1685>strong{font-size:10px;white-space:nowrap;font-variant-numeric:tabular-nums}
      #dogsonFlowHomeV1685 .dogson-flow-stocks-v1685{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
      #dogsonFlowHomeV1685 .dogson-flow-stock-v1685{appearance:none;-webkit-appearance:none;display:flex;flex-direction:column;align-items:flex-start;gap:2px;max-width:100%;min-height:36px;padding:6px 8px;border:1px solid #dce5df;border-radius:10px;background:#fff;color:#315f52;text-align:left;cursor:pointer;touch-action:manipulation}
      #dogsonFlowHomeV1685 .dogson-flow-stock-v1685:active{transform:scale(.985);background:#f1f6f3}
      #dogsonFlowHomeV1685 .dogson-flow-stock-v1685>.dogson-flow-stock-name-v1685{display:block!important;font-size:10px!important;line-height:1.2!important;font-weight:900!important;color:#315f52!important;margin:0!important;white-space:nowrap!important}
      #dogsonFlowHomeV1685 .dogson-flow-stock-v1685>small{display:block;font-size:8.5px;color:#7b8781;line-height:1.2;white-space:nowrap}
      #dogsonFlowHomeV1685 .dogson-flow-members-v1685{margin-top:0!important;padding-top:7px!important;border-top:1px solid #edf1ee!important}
      #dogsonFlowHomeV1685 .dogson-flow-member-grid-v1685{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:7px}
      #dogsonFlowHomeV1685 .dogson-flow-disabled-v1685{margin-top:10px;padding:12px;border:1px dashed #d8dfdb;border-radius:12px;background:#f7f9f7;color:#67736d;font-size:11px;line-height:1.6}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-row-copy-v1685>b{color:#eef2ef}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-stock-v1685{background:#252b27;border-color:#3a433e;color:#dce8e1}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-stock-v1685>.dogson-flow-stock-name-v1685{color:#dce8e1!important}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-stock-v1685>small{color:#9da8a2}
      html[data-dogson-theme="dark"] #dogsonFlowHomeV1685 .dogson-flow-disabled-v1685{background:#252b27;border-color:#3a433e;color:#b8c2bc}
      @media(max-width:520px){
        #dogsonFlowHomeV1685 .dogson-flow-member-grid-v1685{grid-template-columns:1fr}
        #dogsonFlowHomeV1685 .dogson-flow-stock-v1685{min-width:0}
      }
    `;
    document.head.appendChild(s);
  }

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
    const m=currentMarket(),intraday=(currentMode()!=='close')&&!!m.intraday_only&&!staleIntraday();
    const ta=intraday?(m.components?.taiex||{}):(m.taiex||{});
    const ot=intraday?(m.components?.otc||{}):(m.otc||{});
    return{m,ta,ot,tw:indexSnap('^TWII',ta),two:indexSnap('^TWOII',ot)};
  }

  function marketSentence(m,tw,two){
    const state=String(m?.market_mode||'中性');
    const a=num(tw?.pct),b=num(two?.pct);
    if(a!==null&&b!==null&&a*b<0)return`大型與中小型股分歧，先看相對強勢族群；市場目前${state}。`;
    if(state.includes('防守'))return'市場偏防守，個股條件仍可看，但新倉以縮小部位、避免追價為主。';
    if(state.includes('偏多'))return a!==null&&b!==null&&a>0&&b>0?'加權與櫃買同步偏強，可優先找強勢族群中的個股。':'市場偏多但仍有分歧，優先選相對強勢、量價同步的族群。';
    if(a!==null&&b!==null&&a>0&&b>0)return'兩個市場同步上行，但整體環境仍以中性看待，先確認資金是否持續集中。';
    return'市場中性，先看資金集中在哪些族群，再挑個股。';
  }

  function originalMarketDetails(){
    const box=$('#marketbox');
    const grid=$('.marketgrid',box);
    if(!grid)return'<div class="dogson-empty-v1685">市場細節更新中…</div>';
    return`<div class="dogson-market-detail-copy-v1685">${grid.outerHTML}</div>`;
  }

  function renderMarket(){
    const host=$('#dogsonMarketHomeV1685');if(!host)return;
    const {m,tw,two}=marketData();
    const score=num(m.market_score),scoreText=score===null?'—':`${score.toFixed(1)}/15`;
    const state=String(m.market_mode||'資料更新中');
    const updated=$('#updated')?.textContent?.trim()||'更新中';
    const date=tradeDay(m?.trade_date||m?.taiex?.date||m?.otc?.date||window.DOGSON_EFFECTIVE_MARKET_DATE);
    const stateClass=state.includes('防守')?'defense':state.includes('偏多')?'bull':'neutral';
    const html=`
      <div class="dogson-layer-head-v1685">
        <div><div class="dogson-layer-kicker-v1685">市場環境</div><div class="dogson-market-state-v1685 ${stateClass}">📊 ${esc(state)}</div></div>
        <div class="dogson-market-score-v1685"><b>${esc(scoreText)}</b><span>市場分數</span></div>
      </div>
      <div class="dogson-index-grid-v1685">
        <div class="dogson-index-card-v1685">
          <div class="dogson-index-name-v1685">加權指數</div>
          <div class="dogson-index-main-v1685">${fmtIndex(tw.current)}</div>
          <div class="dogson-index-change-v1685 ${tone(tw.pct)}"><span>${signed(tw.pts,2)}</span><span>${signed(tw.pct,2,'%')}</span></div>
        </div>
        <div class="dogson-index-card-v1685">
          <div class="dogson-index-name-v1685">櫃買指數</div>
          <div class="dogson-index-main-v1685">${fmtIndex(two.current)}</div>
          <div class="dogson-index-change-v1685 ${tone(two.pct)}"><span>${signed(two.pts,2)}</span><span>${signed(two.pct,2,'%')}</span></div>
        </div>
      </div>
      <div class="dogson-market-callout-v1685">${esc(marketSentence(m,tw,two))}</div>
      <div class="dogson-market-updated-v1685">交易日 ${esc(date||'—')}｜更新 ${esc(updated)}｜紅漲綠跌</div>
      <details class="dogson-inline-details-v1685"><summary>查看市場細節</summary><div class="dogson-inline-details-body-v1685">${originalMarketDetails()}</div></details>`;
    if(host.dataset.h!==html){host.innerHTML=html;host.dataset.h=html}
  }

  function intradayFlow(){
    const arr=rotation().filter(x=>num(x?.heat)!==null);
    const hot=[...arr].filter(x=>num(x.heat)>0).sort((a,b)=>num(b.heat)-num(a.heat));
    const cold=[...arr].filter(x=>num(x.heat)<0).sort((a,b)=>num(a.heat)-num(b.heat));
    return{hot,cold};
  }
  function closeFlow(){
    const arr=funds().filter(x=>num(x?.today_amount_100m)!==null);
    const hot=[...arr].filter(x=>num(x.today_amount_100m)>0).sort((a,b)=>num(b.today_amount_100m)-num(a.today_amount_100m));
    const cold=[...arr].filter(x=>num(x.today_amount_100m)<0).sort((a,b)=>num(a.today_amount_100m)-num(b.today_amount_100m));
    return{hot,cold};
  }
  function momentumStamp(){
    let latest='';
    try{for(const r of (Array.isArray(intraRows)?intraRows:[])){const t=String(r?.structure_time||r?.time||'').match(/(?:^|\D)([01]?\d|2[0-3]):([0-5]\d)/);if(t){const x=`${String(t[1]).padStart(2,'0')}:${t[2]}`;if(x>latest)latest=x}}}catch{}
    const d=tradeDay(window.DOGSON_INTRADAY_TRADE_DATE||window.DOGSON_DATA_TRUTH_V1700?.dates?.intraday||'');
    return[d,latest].filter(Boolean).join(' ');
  }
  function flowValue(x,closeMode){
    if(closeMode)return`${signed(x.today_amount_100m,1,'億')}`;
    return`熱度 ${signed(x.heat,1)}`;
  }
  function flowMeta(x,closeMode){
    if(closeMode)return x.flow_text||x.action||'法人資金方向';
    const parts=[];
    if(num(x.change_pct)!==null)parts.push(`族群 ${signed(x.change_pct,1,'%')}`);
    if(num(x.turnover_share_pct)!==null)parts.push(`成交占比 ${num(x.turnover_share_pct).toFixed(1)}%`);
    return parts.join('｜')||'族群輪動資料';
  }
  function sourceRows(view,closeMode){
    try{
      if(closeMode)return Array.isArray(closeRows)?closeRows:[];
      if(view==='daytrade'){
        if(Array.isArray(daytradeRows)&&daytradeRows.length)return daytradeRows;
        return Array.isArray(intraRows)?intraRows:[];
      }
      return Array.isArray(intraRows)?intraRows:[];
    }catch{return[]}
  }
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
    const arr=sourceRows(view,closeMode).filter(r=>sectorKey(r)===key);
    return arr.sort((a,b)=>(memberScore(b,view)??-999)-(memberScore(a,view)??-999)||(num(b?.day_change)??-999)-(num(a?.day_change)??-999));
  }
  function memberButton(r,view){
    const score=memberScore(r,view);
    const scoreText=score===null?'—':`${Math.round(score)}分`;
    const stage=stageLabel(r,view);
    return `<button type="button" class="dogson-flow-stock-v1685 peerlink" data-code="${esc(r?.code||'')}"><span class="dogson-flow-stock-name-v1685">${esc(r?.code||'')} ${esc(r?.name||'')}</span><small>${esc(scoreText)} · ${esc(stage)}</small></button>`;
  }
  function membersHTML(x,view,closeMode){
    const members=membersForSector(x?.sector,view,closeMode);
    if(!members.length)return'<div class="dogson-flow-member-grid-v1685"><span class="dogson-empty-v1685">目前沒有可用個股</span></div>';
    return `<div class="dogson-flow-member-grid-v1685">${members.slice(0,30).map(r=>memberButton(r,view)).join('')}</div>`;
  }
  function flowRows(arr,kind,spec,limit=3){
    if(!arr.length)return`<div class="dogson-empty-v1685">目前沒有明顯${kind==='in'?'流入／吸金':'流出／降溫'}族群</div>`;
    return arr.slice(0,limit).map(x=>{
      const members=membersForSector(x?.sector,spec.memberView,spec.closeMode);
      const count=members.length;
      const key='sector:'+kind+':'+String(x?.sector||'');
      return `<details class="dogson-flow-row-v1685 dogson-flow-sector-v1685" data-flow-key="${esc(key)}"><summary class="dogson-flow-row-top-v1685"><div class="dogson-flow-row-copy-v1685"><b>${esc(x?.sector||'未分類')}</b><span>${esc(flowMeta(x,spec.closeMode))}</span></div><div class="dogson-flow-row-side-v1685"><strong class="${kind==='in'?'up':'down'}">${esc(flowValue(x,spec.closeMode))}</strong><small>${count?'查看 '+count+' 檔':'查看個股'} ▾</small></div></summary><div class="dogson-flow-members-v1685">${membersHTML(x,spec.memberView,spec.closeMode)}</div></details>`;
    }).join('');
  }
  function hasFlow(f){return !!(f&&(f.hot?.length||f.cold?.length))}
  function closeBackground(view,subtitle){
    const f=closeFlow();
    return{view,memberView:'close',closeMode:true,disabled:false,referenceOnly:view==='daytrade',subtitle,...f};
  }
  function momentumUnavailable(view,subtitle){return{view,memberView:view==='daytrade'?'daytrade':'intraday',closeMode:false,disabled:true,subtitle,message:'目前沒有可保留的盤中資金動能快照。',hot:[],cold:[]}}
  function flowSpec(){
    const view=currentView();
    if(view==='close')return closeBackground(view,'盤後法人族群資金');
    if(view==='portfolio'){
      if(liveIntraday()){
        const f=intradayFlow();
        if(hasFlow(f))return{view,memberView:'intraday',closeMode:false,disabled:false,subtitle:'庫存｜盤中族群資金背景',...f};
      }
      return closeBackground(view,'庫存｜最近完整盤後法人資金背景');
    }
    const f=intradayFlow();
    const stamp=momentumStamp();
    if(view==='daytrade'){
      if(hasFlow(f)){
        if(dayActionable())return{view,memberView:'daytrade',closeMode:false,disabled:false,frozen:false,subtitle:'當沖｜盤中即時資金動能',...f};
        return{view,memberView:'daytrade',closeMode:false,disabled:false,frozen:true,subtitle:`當沖｜${stamp?stamp+' ':''}收盤定格資金動能（不可執行）`,...f};
      }
      return momentumUnavailable(view,'當沖｜資金動能');
    }
    if(hasFlow(f)){
      if(liveIntraday())return{view,memberView:'intraday',closeMode:false,disabled:false,frozen:false,subtitle:'盤中｜即時資金動能',...f};
      return{view,memberView:'intraday',closeMode:false,disabled:false,frozen:true,subtitle:`盤中｜${stamp?stamp+' ':''}收盤定格資金動能`,...f};
    }
    return momentumUnavailable(view,'盤中｜資金動能');
  }
  function openFlowKeys(host){
    return new Set($$('details[open][data-flow-key]',host).map(x=>x.dataset.flowKey).filter(Boolean));
  }
  function restoreFlowKeys(host,keys){
    $$('details[data-flow-key]',host).forEach(x=>{if(keys.has(x.dataset.flowKey))x.open=true});
  }
  function renderFlow(){
    const host=$('#dogsonFlowHomeV1685');if(!host)return;
    installFlowStyle();
    const spec=flowSpec();
    const title=spec.closeMode?'資金流向':spec.view==='portfolio'?'資金背景':'資金動能';
    if(spec.disabled){
      const html=`<div class="dogson-layer-head-v1685"><div><div class="dogson-layer-kicker-v1685">${esc(title)}</div><div class="dogson-layer-sub-v1685">${esc(spec.subtitle)}</div></div></div><div class="dogson-flow-disabled-v1685">${esc(spec.message)}</div>`;
      if(host.dataset.h!==html){host.innerHTML=html;host.dataset.h=html}
      return;
    }
    const lead=spec.hot.slice(0,3).map(x=>x.sector).filter(Boolean);
    const sentence=lead.length?(spec.closeMode?`最近完整資金較集中在：${lead.join('、')}。`:spec.frozen?`收盤前最後動能較集中在：${lead.join('、')}。`:`盤中動能目前較集中在：${lead.join('、')}。`):'目前沒有明顯集中族群，先以個股相對強弱為主。';
    const openKeys=openFlowKeys(host);
    const fullLabel=spec.closeMode?'查看完整資金流向':spec.view==='portfolio'?'查看完整資金背景':'查看完整資金動能';
    const html=`
      <div class="dogson-layer-head-v1685"><div><div class="dogson-layer-kicker-v1685">${esc(title)}</div><div class="dogson-layer-sub-v1685">${esc(spec.subtitle)}｜先看族群，點開後再看個股。</div></div></div>
      <div class="dogson-flow-summary-v1685">${esc(sentence)}</div>
      <div class="dogson-flow-preview-v1685">
        <div><div class="dogson-flow-colhead-v1685">${spec.closeMode?'🔴 流入 TOP 3':'🔥 吸金 TOP 3'}</div>${flowRows(spec.hot,'in',spec,3)}</div>
        <div><div class="dogson-flow-colhead-v1685">${spec.closeMode?'🟢 流出 TOP 3':'🧊 降溫 TOP 3'}</div>${flowRows(spec.cold,'out',spec,3)}</div>
      </div>
      <details class="dogson-inline-details-v1685" data-flow-key="main"><summary>${esc(fullLabel)}</summary><div class="dogson-inline-details-body-v1685"><div class="dogson-flow-detail-grid-v1685"><div><div class="dogson-flow-colhead-v1685">${spec.closeMode?'主要流入':'主要吸金'}</div>${flowRows(spec.hot,'in',spec,5)}</div><div><div class="dogson-flow-colhead-v1685">${spec.closeMode?'主要流出':'主要降溫'}</div>${flowRows(spec.cold,'out',spec,5)}</div></div></div></details>`;
    if(host.dataset.h!==html){
      host.innerHTML=html;
      host.dataset.h=html;
      restoreFlowKeys(host,openKeys);
    }
  }

  function render(){
    if(!ensureLayout())return;
    installFlowStyle();
    renderMarket();renderFlow();
  }

  function watchSource(el){
    if(!el||el.__dogsonMarketWatch1685)return;
    el.__dogsonMarketWatch1685=true;
    let t;
    new MutationObserver(()=>{clearTimeout(t);t=setTimeout(render,40)}).observe(el,{subtree:true,childList:true,characterData:true});
  }
  function boot(){
    render();
    watchSource($('#marketbox'));watchSource($('#rotationbox'));watchSource($('#updated'));
    $$('.tab').forEach(b=>b.addEventListener('click',()=>setTimeout(render,80)));
    $('#dogsonViewNav')?.addEventListener('click',()=>setTimeout(render,100));
    window.addEventListener('dogson:freshness',()=>setTimeout(render,0));
    window.addEventListener('dogson:data-truth',()=>setTimeout(render,0));
    window.addEventListener('dogson:actionability',()=>setTimeout(render,0));
    setTimeout(render,250);setTimeout(render,900);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();