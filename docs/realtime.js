(()=>{
  const REFRESH_MS = 8000;
  const MAX_CODES = 24;
  const quotes = new Map();
  let lastSuccessAt = 0;
  let lastAttemptAt = 0;
  let busy = false;
  let lastSource = "";

  function codeFromCard(card){
    const t = card.querySelector('.code')?.textContent || '';
    const m = t.match(/\b\d{4}\b/);
    return m ? m[0] : null;
  }

  function marketOf(code){
    try{
      const x = (typeof universe !== 'undefined' ? universe : []).find(r=>String(r.code)===String(code));
      return x?.market === '上櫃' ? 'otc' : 'tse';
    }catch{return 'tse'}
  }

  function yahooSymbol(code){
    return `${code}.${marketOf(code)==='otc'?'TWO':'TW'}`;
  }

  function selectedCodes(){
    const out=[];
    const add=c=>{c=String(c||''); if(/^\d{4}$/.test(c)&&!out.includes(c)) out.push(c)};

    document.querySelectorAll('.card').forEach(card=>add(codeFromCard(card)));
    try{(typeof watchlist==='function'?watchlist():[]).forEach(add)}catch{}

    const q=document.getElementById('q')?.value.trim()||'';
    if(/^\d{4}$/.test(q)) add(q);
    try{
      if(q && !/^\d{4}$/.test(q)){
        const hit=(typeof universe!=='undefined'?universe:[]).find(x=>String(x.name)===q);
        if(hit) add(hit.code);
      }
    }catch{}
    return out.slice(0,MAX_CODES);
  }

  function n(v){
    const x=Number(v);
    return Number.isFinite(x)?x:null;
  }

  function fmtPrice(v){
    if(v==null) return '—';
    return v>=1000?v.toFixed(0):v>=100?v.toFixed(1):v.toFixed(2);
  }

  function fmtPct(v){
    if(v==null) return '—';
    return `${v>=0?'+':''}${v.toFixed(2)}%`;
  }

  function quoteAge(q){
    const t=q?.epoch?Number(q.epoch):0;
    if(!t) return null;
    return Math.max(0,Math.round((Date.now()-t)/1000));
  }

  function status(text, cls=''){
    const el=document.getElementById('liveStatus');
    if(!el) return;
    el.className=`live-status ${cls}`;
    el.textContent=text;
  }

  async function fetchMis(codes){
    const ex=codes.map(c=>`${marketOf(c)}_${c}.tw`).join('|');
    const url=`https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${encodeURIComponent(ex)}&json=1&delay=0&_=${Date.now()}`;
    const r=await fetch(url,{cache:'no-store',credentials:'omit',mode:'cors'});
    if(!r.ok) throw new Error(`MIS ${r.status}`);
    const j=await r.json();
    const arr=Array.isArray(j.msgArray)?j.msgArray:[];
    if(!arr.length) throw new Error('MIS empty');
    let count=0;
    for(const x of arr){
      const code=String(x.c||'');
      if(!/^\d{4}$/.test(code)) continue;
      const price=n(x.z);
      const prev=n(x.y);
      if(price==null || price<=0) continue;
      let epoch=n(x.tlong);
      if(epoch && epoch<1e12) epoch*=1000;
      const change=prev&&prev>0?(price/prev-1)*100:null;
      quotes.set(code,{price,prev,change,time:x.t||'',epoch:epoch||Date.now(),source:'TWSE MIS'});
      count++;
    }
    if(!count) throw new Error('MIS no valid price');
    return count;
  }

  async function fetchYahooOne(code){
    const symbol=yahooSymbol(code);
    const url=`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1m&range=1d&includePrePost=false&_=${Date.now()}`;
    const r=await fetch(url,{cache:'no-store',credentials:'omit',mode:'cors'});
    if(!r.ok) throw new Error(`Yahoo ${r.status}`);
    const j=await r.json();
    const x=j?.chart?.result?.[0];
    const meta=x?.meta||{};
    const price=n(meta.regularMarketPrice);
    const prev=n(meta.chartPreviousClose ?? meta.previousClose);
    if(price==null || price<=0) throw new Error('Yahoo no price');
    const epoch=(n(meta.regularMarketTime)||Math.floor(Date.now()/1000))*1000;
    const change=prev&&prev>0?(price/prev-1)*100:null;
    quotes.set(code,{price,prev,change,time:new Date(epoch).toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}),epoch,source:'Yahoo 1m'});
    return true;
  }

  async function fetchYahoo(codes){
    let ok=0;
    const queue=[...codes];
    const workers=Array.from({length:Math.min(6,queue.length)},async()=>{
      while(queue.length){
        const c=queue.shift();
        try{await fetchYahooOne(c);ok++}catch{}
      }
    });
    await Promise.all(workers);
    if(!ok) throw new Error('Yahoo unavailable');
    return ok;
  }

  function ensureStyles(){
    if(document.getElementById('liveQuoteStyles')) return;
    const s=document.createElement('style');
    s.id='liveQuoteStyles';
    s.textContent=`
      .live-status{margin:8px 2px 2px;padding:9px 11px;border:1px solid #285b48;border-radius:12px;background:#10241d;color:#8cf0bd;font-size:12px;font-weight:800}
      .live-status.warn{border-color:#66521f;background:#2a230f;color:#ffd477}
      .live-status.bad{border-color:#61303a;background:#2c141a;color:#ff9cac}
      .livequote{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:10px}
      .livecell{background:#0c1612;border:1px solid #244936;border-radius:11px;padding:9px}
      .liveval{font-size:15px;font-weight:900;color:#8cf0bd}.livelab{font-size:9px;color:#9ba5b6;margin-top:3px}
      .livequote.stale .livecell{border-color:#5f4d22;background:#211c0f}.livequote.stale .liveval{color:#ffd477}
    `;
    document.head.appendChild(s);
  }

  function applyQuotes(){
    ensureStyles();
    document.querySelectorAll('.card').forEach(card=>{
      const code=codeFromCard(card);
      if(!code) return;
      const q=quotes.get(code);
      let box=card.querySelector('.livequote');
      if(!box){
        box=document.createElement('div');
        box.className='livequote';
        const top=card.querySelector('.top');
        if(top) top.insertAdjacentElement('afterend',box); else card.prepend(box);
      }
      if(!q){
        box.innerHTML='<div class="livecell"><div class="liveval">—</div><div class="livelab">近即時價</div></div><div class="livecell"><div class="liveval">—</div><div class="livelab">近即時漲跌</div></div><div class="livecell"><div class="liveval">等待報價</div><div class="livelab">瀏覽器即時層</div></div>';
        box.classList.add('stale');
        return;
      }
      const age=quoteAge(q);
      const stale=age!=null && age>90;
      box.classList.toggle('stale',stale);
      const time=q.time||'—';
      const source=q.source||'近即時';
      box.innerHTML=`<div class="livecell"><div class="liveval">${fmtPrice(q.price)}</div><div class="livelab">近即時價</div></div><div class="livecell"><div class="liveval">${fmtPct(q.change)}</div><div class="livelab">近即時漲跌</div></div><div class="livecell"><div class="liveval">${time}</div><div class="livelab">${source}${stale?' · 可能延遲':''}</div></div>`;
    });
  }

  async function refresh(){
    if(busy || document.hidden) return;
    if(typeof mode!=='undefined' && mode!=='intraday') return;
    const codes=selectedCodes();
    if(!codes.length){status('🟡 尚無可更新的股票｜盤中結構仍為5分K','warn');return;}
    busy=true; lastAttemptAt=Date.now();
    try{
      let count=0;
      try{
        count=await fetchMis(codes);
        lastSource='TWSE MIS';
      }catch(misErr){
        count=await fetchYahoo(codes.slice(0,12));
        lastSource='Yahoo 1m fallback';
      }
      lastSuccessAt=Date.now();
      const now=new Date().toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
      status(`🟢 近即時報價 ${now}｜${lastSource}｜更新 ${count} 檔｜結構仍採5分K`);
      applyQuotes();
    }catch(e){
      const age=lastSuccessAt?Math.round((Date.now()-lastSuccessAt)/1000):null;
      status(age!=null?`⚠️ 近即時來源暫不可用｜上次成功 ${age} 秒前｜仍保留5分K雷達`:'⚠️ 近即時來源暫不可用｜目前使用5分K雷達','bad');
      applyQuotes();
    }finally{busy=false;}
  }

  function installObserver(){
    const cards=document.getElementById('cards');
    if(!cards) return;
    let t=null;
    new MutationObserver(()=>{
      clearTimeout(t);
      t=setTimeout(()=>{applyQuotes();refresh();},250);
    }).observe(cards,{childList:true,subtree:true});
  }

  function boot(){
    ensureStyles();
    applyQuotes();
    installObserver();
    refresh();
    setInterval(refresh,REFRESH_MS);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});
    document.getElementById('q')?.addEventListener('change',refresh);
    document.getElementById('scan')?.addEventListener('click',()=>setTimeout(refresh,150));
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else boot();
})();
