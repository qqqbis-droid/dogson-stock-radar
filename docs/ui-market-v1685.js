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
  const tradeDay=v=>{const m=String(v||'').match(/20\d{2}-(\d{2})-(\d{2})/);return m?`${Number(m[1])}/${Number(m[2])}`:''};

  function currentMode(){try{return mode||'intraday'}catch{return'intraday'}}
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

  function leaderText(x){
    const arr=Array.isArray(x?.leaders)?x.leaders:[];
    return arr.slice(0,2).map(v=>v?.name||v?.code).filter(Boolean).join('、');
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
  function flowValue(x,closeMode){
    if(closeMode)return`${signed(x.today_amount_100m,1,'億')}`;
    return`熱度 ${signed(x.heat,1)}`;
  }
  function flowMeta(x,closeMode){
    if(closeMode)return x.flow_text||x.action||'法人資金方向';
    const parts=[];
    if(num(x.change_pct)!==null)parts.push(`族群 ${signed(x.change_pct,1,'%')}`);
    if(num(x.turnover_share_pct)!==null)parts.push(`成交占比 ${num(x.turnover_share_pct).toFixed(1)}%`);
    const l=leaderText(x);if(l)parts.push(l);
    return parts.join('｜')||'族群輪動資料';
  }
  function flowRows(arr,kind,closeMode,limit=3){
    if(!arr.length)return`<div class="dogson-empty-v1685">目前沒有明顯${kind==='in'?'流入／吸金':'流出／降溫'}族群</div>`;
    return arr.slice(0,limit).map(x=>`<div class="dogson-flow-row-v1685"><div><b>${esc(x.sector||'未分類')}</b><span>${esc(flowMeta(x,closeMode))}</span></div><strong class="${kind==='in'?'up':'down'}">${esc(flowValue(x,closeMode))}</strong></div>`).join('');
  }
  function renderFlow(){
    const host=$('#dogsonFlowHomeV1685');if(!host)return;
    const fallback=staleIntraday()&&currentMode()!=='close';
    const closeMode=currentMode()==='close'||fallback;
    const {hot,cold}=closeMode?closeFlow():intradayFlow();
    const lead=hot.slice(0,3).map(x=>x.sector).filter(Boolean);
    const sentence=lead.length?`資金目前較集中在：${lead.join('、')}。`:'目前沒有明顯集中族群，先以個股相對強弱為主。';
    const subtitle=fallback?'最新有效交易日法人族群資金':(closeMode?'盤後法人族群資金':'盤中成交資金輪動');
    const html=`
      <div class="dogson-layer-head-v1685"><div><div class="dogson-layer-kicker-v1685">資金流向</div><div class="dogson-layer-sub-v1685">${esc(subtitle)}｜先看錢往哪裡走，再挑個股。</div></div></div>
      <div class="dogson-flow-summary-v1685">${esc(sentence)}</div>
      <div class="dogson-flow-preview-v1685">
        <div><div class="dogson-flow-colhead-v1685">${closeMode?'🔴 流入 TOP 3':'🔥 吸金 TOP 3'}</div>${flowRows(hot,'in',closeMode,3)}</div>
        <div><div class="dogson-flow-colhead-v1685">${closeMode?'🟢 流出 TOP 3':'🧊 降溫 TOP 3'}</div>${flowRows(cold,'out',closeMode,3)}</div>
      </div>
      <details class="dogson-inline-details-v1685"><summary>查看完整資金流向</summary><div class="dogson-inline-details-body-v1685"><div class="dogson-flow-detail-grid-v1685"><div><div class="dogson-flow-colhead-v1685">${closeMode?'主要流入':'主要吸金'}</div>${flowRows(hot,'in',closeMode,5)}</div><div><div class="dogson-flow-colhead-v1685">${closeMode?'主要流出':'主要降溫'}</div>${flowRows(cold,'out',closeMode,5)}</div></div></div></details>`;
    if(host.dataset.h!==html){host.innerHTML=html;host.dataset.h=html}
  }

  function render(){
    if(!ensureLayout())return;
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
    setTimeout(render,250);setTimeout(render,900);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
