(()=>{
  if(window.__DOGSON_MARKET_TICKER_V1686__) return;
  window.__DOGSON_MARKET_TICKER_V1686__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
  const pick=(o,keys)=>{for(const k of keys){const v=num(o?.[k]);if(v!==null)return v}return null};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function currentMode(){try{return mode||'intraday'}catch{return'intraday'}}
  function currentMarket(){try{return market||{}}catch{return{}}}
  function liveMarket(){try{return marketLive||{}}catch{return{}}}

  function snap(symbol,component){
    const live=liveMarket()?.[symbol]||{};
    const current=pick(live,['price','last','close','value','index','last_price','lastPrice'])??pick(component,['price','last','close','value','index']);
    const pct=pick(live,['change_pct','changePct','pct','change_percent'])??pick(component,['change_pct','changePct','pct']);
    let pts=pick(live,['change','change_point','change_points','change_value','diff','delta'])??pick(component,['change','change_point','change_points','change_value','diff','delta']);
    if(pts===null&&current!==null&&pct!==null&&pct!==-100){
      const prev=current/(1+pct/100);
      if(Number.isFinite(prev))pts=current-prev;
    }
    return{pts};
  }

  function marketData(){
    const m=currentMarket(),intraday=(currentMode()!=='close')&&!!m.intraday_only;
    const ta=intraday?(m.components?.taiex||{}):(m.taiex||{});
    const ot=intraday?(m.components?.otc||{}):(m.otc||{});
    return{m,tw:snap('^TWII',ta),two:snap('^TWOII',ot)};
  }

  function pointText(v,decimals){
    const n=num(v);
    if(n===null)return'—';
    const d=Math.abs(n)>=100?0:decimals;
    const body=Math.abs(n).toLocaleString('zh-TW',{minimumFractionDigits:d,maximumFractionDigits:d});
    return`${n>0?'▲+':n<0?'▼-':''}${body}`;
  }

  function tone(v){const n=num(v);return n===null||n===0?'flat':n>0?'up':'down'}
  function stateInfo(state){
    const s=String(state||'中性');
    if(/系統|極端|風險/.test(s))return{icon:'🔴',cls:'risk'};
    if(s.includes('偏多'))return{icon:'🟢',cls:'bull'};
    if(s.includes('防守'))return{icon:'🟠',cls:'defense'};
    return{icon:'🟡',cls:'neutral'};
  }
  function updateTime(){
    const raw=$('#updated')?.textContent?.trim()||'';
    const m=raw.match(/(?:^|\s)([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?/);
    return m?`${String(m[1]).padStart(2,'0')}:${m[2]}`:'更新中';
  }

  function ensure(){
    let bar=$('#dogsonMarketTickerV1686');
    if(bar)return bar;
    bar=document.createElement('div');
    bar.id='dogsonMarketTickerV1686';
    bar.className='dogson-market-ticker-v1686';
    bar.innerHTML='<button type="button" class="dogson-market-ticker-inner-v1686" aria-label="查看市場環境"></button>';
    document.body.prepend(bar);
    bar.addEventListener('click',()=>{
      const target=$('#dogsonMarketHomeV1685');
      if(target)target.scrollIntoView({behavior:'smooth',block:'start'});
    });
    document.documentElement.classList.add('dogson-market-ticker-ready-v1686');
    return bar;
  }

  function render(){
    const bar=ensure();
    const btn=$('.dogson-market-ticker-inner-v1686',bar);if(!btn)return;
    const {m,tw,two}=marketData();
    const score=num(m?.market_score);
    const scoreText=score===null?'—/15':`${score.toFixed(score%1===0?0:1)}/15`;
    const state=String(m?.market_mode||'中性');
    const si=stateInfo(state);
    const html=`<span class="dogson-ticker-state-v1686 ${si.cls}">${si.icon} ${esc(state)} ${esc(scoreText)}</span><span class="dogson-ticker-sep-v1686">｜</span><span>加權 <b class="${tone(tw.pts)}">${esc(pointText(tw.pts,2))}</b></span><span class="dogson-ticker-sep-v1686">｜</span><span>櫃買 <b class="${tone(two.pts)}">${esc(pointText(two.pts,2))}</b></span><span class="dogson-ticker-sep-v1686">｜</span><span class="dogson-ticker-time-v1686">${esc(updateTime())}</span>`;
    if(btn.dataset.h!==html){btn.innerHTML=html;btn.dataset.h=html}
  }

  function watch(el){
    if(!el||el.__dogsonTickerWatch1686)return;
    el.__dogsonTickerWatch1686=true;
    let t;
    new MutationObserver(()=>{clearTimeout(t);t=setTimeout(render,30)}).observe(el,{subtree:true,childList:true,characterData:true});
  }

  function boot(){
    render();
    watch($('#marketbox'));watch($('#updated'));
    document.addEventListener('click',e=>{
      if(e.target?.closest?.('.tab,#dogsonViewNav'))setTimeout(render,80);
    });
    setInterval(render,3000);
    setTimeout(render,250);setTimeout(render,900);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
