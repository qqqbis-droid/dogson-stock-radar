(()=>{
  const REFRESH_MS = 10000;
  const MAX_CODES = 24;
  const BATCH_SIZE = 5;
  const FRESHNESS_MS = 30000;
  const quotes = new Map();
  const snapshots = new Map();
  const STORE_KEY = 'dogson-last-real-trades-v1';
  const STORE_MAX_AGE = 8*60*60*1000;
  let lastSuccessAt = 0;
  let latestQuoteLabel = '';
  let busy = false;

  function apiUrl(){
    const configured=String(window.DOGSON_REALTIME_API||'').trim();
    if(configured) return configured.replace(/\/$/,'') + '/api/quote';
    return 'https://dogson-stock-radar-live.vercel.app/api/quote';
  }
  function codeFromCard(card){
    const dc=String(card?.dataset?.code||'');if(/^\d{4}$/.test(dc))return dc;
    const t=card?.querySelector('.code')?.textContent||'';const m=t.match(/\b\d{4}\b/);return m?m[0]:null;
  }
  function selectedCodes(){
    const out=[];const add=c=>{c=String(c||'').trim();if(/^\d{4}$/.test(c)&&!out.includes(c)&&out.length<MAX_CODES)out.push(c)};
    const q=document.getElementById('q')?.value.trim()||'';
    if(/^\d{4}$/.test(q))add(q);
    try{if(q&&!/^\d{4}$/.test(q)){const hit=(typeof universe!=='undefined'?universe:[]).find(x=>String(x.name)===q);if(hit)add(hit.code)}}catch{}
    // What the user is looking at wins over cards that happen to be earlier in DOM order.
    const cards=[...document.querySelectorAll('.card')];
    cards.filter(card=>{const r=card.getBoundingClientRect();return r.bottom>=-240&&r.top<=window.innerHeight+240}).forEach(card=>add(codeFromCard(card)));
    // Then keep portfolio/watchlist names warm in the remaining slots.
    try{(typeof watchlist==='function'?watchlist():[]).forEach(add)}catch{}
    cards.forEach(card=>add(codeFromCard(card)));
    return out;
  }
  function n(v){const x=Number(v);return Number.isFinite(x)?x:null}
  function quoteEpoch(v){const d=toDate(v);return d?d.getTime():0}
  function setQuote(code,q){
    const old=quotes.get(code);const nt=quoteEpoch(q?.time),ot=quoteEpoch(old?.time);
    if(!old||!ot||!nt||nt>=ot)quotes.set(code,q);
  }
  function saveStored(){
    try{const o={};for(const [c,q] of quotes)o[c]=q;localStorage.setItem(STORE_KEY,JSON.stringify({savedAt:Date.now(),quotes:o}))}catch{}
  }
  function loadStored(){
    try{const o=JSON.parse(localStorage.getItem(STORE_KEY)||'{}');if(!o?.savedAt||Date.now()-o.savedAt>STORE_MAX_AGE)return;
      for(const [c,q] of Object.entries(o.quotes||{})){if(/^\d{4}$/.test(c)&&n(q?.price)!=null)setQuote(c,q)}
    }catch{}
  }
  function seedFromRows(){
    try{for(const r of (typeof intraRows!=='undefined'&&Array.isArray(intraRows)?intraRows:[])){
      const c=String(r.code||'');if(!/^\d{4}$/.test(c))continue;
      const st=String(r.quote_snapshot_time||'').trim();
      if(st)snapshots.set(c,{bid1:n(r.quote_bid1),ask1:n(r.quote_ask1),time:st,receivedAt:Date.now(),source:'TWSE MIS snapshot'});
      const px=n(r.quote_close),qd=String(r.quote_date||''),qt=String(r.quote_time||'');if(px==null||!qd||!qt)continue;
      const ms=Date.parse(`${qd}T${qt.length===5?qt+':00':qt}+08:00`);if(!Number.isFinite(ms)||Date.now()-ms>STORE_MAX_AGE)continue;
      setQuote(c,{price:px,change:n(r.day_change),time:ms,receivedAt:Date.now(),source:r.quote_source||'TWSE MIS last trade'});
    }}catch{}
  }
  function fmtPrice(v){if(v==null)return'—';return v>=1000?v.toFixed(0):v>=100?v.toFixed(1):v.toFixed(2)}
  function fmtPct(v){if(v==null)return'—';return `${v>=0?'+':''}${v.toFixed(2)}%`}
  function toDate(v){const x=n(v);if(!x)return null;let ms=x;if(ms>1e14)ms/=1000;else if(ms<1e12)ms*=1000;const d=new Date(ms);return Number.isNaN(d.getTime())?null:d}
  function fmtTime(v){const d=toDate(v);return d?d.toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}):'—'}
  function status(text,cls=''){const el=document.getElementById('liveStatus');if(!el)return;el.className=`live-status ${cls}`;el.textContent=text}
  function setRadarPill(text,level='ok'){
    const el=document.getElementById('status');if(!el)return;el.textContent=text;
    if(level==='bad'){el.style.background='#2c141a';el.style.borderColor='#61303a';el.style.color='#ff9cac'}
    else if(level==='warn'){el.style.background='#2a230f';el.style.borderColor='#66521f';el.style.color='#ffd477'}
    else{el.style.background='#16263a';el.style.borderColor='#24496e';el.style.color='#9fd0ff'}
  }
  function taipeiClock(){
    const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date());
    const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));return {year:+p.year,month:+p.month,day:+p.day,hour:+p.hour,minute:+p.minute};
  }
  function structureLatest(){
    const rs=typeof intraRows!=='undefined'&&Array.isArray(intraRows)?intraRows:[];let latest='';
    for(const r of rs){const t=String(r.structure_time||r.time||'').slice(0,5);if(/^\d{2}:\d{2}$/.test(t)&&t>latest)latest=t}return latest;
  }
  function checkRadarFreshness(){
    try{
      if(typeof mode!=='undefined'&&mode==='close'){setRadarPill('盤後資料','ok');return}
      const st=structureLatest();
      if(lastSuccessAt&&Date.now()-lastSuccessAt<45000){
        setRadarPill(`即時價 ${latestQuoteLabel||'已連線'}｜5分K結構 ${st||'—'}`,'ok');return;
      }
      const now=taipeiClock();const nowMin=now.hour*60+now.minute;
      let latest=-1;for(const r of (typeof intraRows!=='undefined'?intraRows:[])){const m=String(r.structure_time||r.time||'').match(/^(\d{1,2}):(\d{2})/);if(m)latest=Math.max(latest,(+m[1])*60+(+m[2]))}
      if(latest<0){setRadarPill('行情連線中','warn');return}
      const age=nowMin-latest;const label=`${String(Math.floor(latest/60)).padStart(2,'0')}:${String(latest%60).padStart(2,'0')}`;
      if(age>30)setRadarPill(`⚠️ 即時價未連線｜5分K結構 ${label}`,'bad');else setRadarPill(`5分K結構 ${label}｜即時價連線中`,'warn');
    }catch{}
  }
  function ensureStyles(){
    if(document.getElementById('liveQuoteStyles'))return;const s=document.createElement('style');s.id='liveQuoteStyles';s.textContent=`
    .live-status{margin:8px 2px 2px;padding:9px 11px;border:1px solid #285b48;border-radius:12px;background:#10241d;color:#8cf0bd;font-size:12px;font-weight:800}
    .live-status.warn{border-color:#66521f;background:#2a230f;color:#ffd477}.live-status.bad{border-color:#61303a;background:#2c141a;color:#ff9cac}
    .livequote{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:10px}.livecell{background:#0c1612;border:1px solid #244936;border-radius:11px;padding:9px}
    .liveval{font-size:15px;font-weight:900;color:#8cf0bd}.livelab{font-size:9px;color:#9ba5b6;margin-top:3px}`;document.head.appendChild(s);
  }
  function updateMainMetrics(card,q){
    card.querySelectorAll('.metric').forEach(cell=>{const lab=cell.querySelector('.mlab')?.textContent?.trim();const val=cell.querySelector('.mval');if(!val)return;
      if(lab==='現價')val.textContent=fmtPrice(q.price);else if(lab==='當日'&&q.change!=null)val.textContent=fmtPct(q.change);else if(lab==='行情時間')val.textContent=fmtTime(q.time).slice(0,5);
    });
  }
  function applyQuotes(){
    ensureStyles();const liveEl=document.getElementById('liveStatus');
    if(typeof mode!=='undefined'&&mode!=='intraday'){if(liveEl)liveEl.style.display='none';document.querySelectorAll('.livequote').forEach(x=>x.remove());return}
    if(liveEl)liveEl.style.display='block';
    document.querySelectorAll('.card').forEach(card=>{const code=codeFromCard(card);if(!code)return;const q=quotes.get(code);let box=card.querySelector('.livequote');
      if(!box){box=document.createElement('div');box.className='livequote';const top=card.querySelector('.top');if(top)top.insertAdjacentElement('afterend',box);else card.prepend(box)}
      const snap=snapshots.get(code);
      const snapTime=snap?(typeof snap.time==='number'?fmtTime(snap.time):String(snap.time||'—')):'—';
      if(!q){const r=card.getBoundingClientRect(),onscreen=r.bottom>=-240&&r.top<=window.innerHeight+240;
        if(snap){box.innerHTML=`<div class="livecell"><div class="liveval">買 ${fmtPrice(snap.bid1)}</div><div class="livelab">MIS 買一｜非成交價</div></div><div class="livecell"><div class="liveval">賣 ${fmtPrice(snap.ask1)}</div><div class="livelab">MIS 賣一｜非成交價</div></div><div class="livecell"><div class="liveval">${snapTime}</div><div class="livelab">官方快照｜等下一筆成交</div></div>`;return}
        box.innerHTML=`<div class="livecell"><div class="liveval">—</div><div class="livelab">最後真實成交</div></div><div class="livecell"><div class="liveval">—</div><div class="livelab">MIS 買賣盤</div></div><div class="livecell"><div class="liveval">5分K</div><div class="livelab">${onscreen?'官方行情重試中':'滑到此卡即優先追蹤'}</div></div>`;return}
      box.innerHTML=`<div class="livecell"><div class="liveval">${fmtPrice(q.price)}</div><div class="livelab">最後真實成交</div></div><div class="livecell"><div class="liveval">${fmtPct(q.change)}</div><div class="livelab">依最後成交計算</div></div><div class="livecell"><div class="liveval">${fmtTime(q.time)}</div><div class="livelab">成交時間｜MIS快照 ${snapTime}</div></div>`;
      updateMainMetrics(card,q);
    });
  }
  async function fetchBatch(endpoint,codes){
    const url=`${endpoint}?codes=${encodeURIComponent(codes.join(','))}&_=${Date.now()}`;const r=await fetch(url,{cache:'no-store',credentials:'omit'});const j=await r.json();if(!r.ok||!j?.ok)throw new Error(j?.error||`HTTP ${r.status}`);return j.quotes||[];
  }
  async function refresh(){
    if(busy||document.hidden)return;if(typeof mode!=='undefined'&&mode!=='intraday'){applyQuotes();return}
    const codes=selectedCodes();if(!codes.length){status('🟡 尚無即時追蹤標的｜搜尋或加入關注後會優先追蹤','warn');return}
    busy=true;try{
      const endpoint=apiUrl(),batches=[];for(let i=0;i<codes.length;i+=BATCH_SIZE)batches.push(codes.slice(i,i+BATCH_SIZE));
      const results=await Promise.allSettled(batches.map(b=>fetchBatch(endpoint,b)));let count=0,snapshotCount=0,newest=null;
      for(const rr of results){if(rr.status!=='fulfilled')continue;for(const x of rr.value){const code=String(x.code||'');if(!/^\d{4}$/.test(code))continue;
        snapshots.set(code,{bid1:n(x.bid1),ask1:n(x.ask1),time:x.time,receivedAt:Date.now(),source:x.source||'TWSE MIS snapshot'});snapshotCount++;const d=toDate(x.time);if(d&&(!newest||d>newest))newest=d;
        const price=n(x.price);if(price==null)continue;setQuote(code,{price,change:n(x.changePct),time:x.time,receivedAt:Date.now(),source:'TWSE MIS live trade'});count++;}}
      if(!snapshotCount)throw new Error('no MIS snapshots');lastSuccessAt=Date.now();latestQuoteLabel=(newest||new Date()).toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',hour12:false});
      saveStored();status(`🟢 MIS快照 ${latestQuoteLabel}｜覆蓋 ${snapshotCount}/${codes.length}｜本輪新成交 ${count}｜無成交顯示買一/賣一`);applyQuotes();checkRadarFreshness();
    }catch(e){const age=lastSuccessAt?Math.round((Date.now()-lastSuccessAt)/1000):null;status(age!=null?`⚠️ 官方即時行情暫斷｜上次成功 ${age} 秒前｜5分K雷達仍可用`:'⚠️ 官方即時行情連線中｜5分K雷達仍可用','bad');applyQuotes();checkRadarFreshness()}finally{busy=false}
  }
  function boot(){ensureStyles();loadStored();seedFromRows();applyQuotes();refresh();setTimeout(checkRadarFreshness,1000);setInterval(refresh,REFRESH_MS);setInterval(checkRadarFreshness,FRESHNESS_MS);
    const cards=document.getElementById('cards');if(cards){let t;new MutationObserver(()=>{clearTimeout(t);t=setTimeout(()=>{applyQuotes();refresh()},250)}).observe(cards,{childList:true,subtree:true})}
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});let scrollTimer;addEventListener('scroll',()=>{clearTimeout(scrollTimer);scrollTimer=setTimeout(refresh,180)},{passive:true});document.getElementById('q')?.addEventListener('change',refresh);document.getElementById('scan')?.addEventListener('click',()=>setTimeout(refresh,150));document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>setTimeout(()=>{applyQuotes();refresh();checkRadarFreshness()},50)));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
