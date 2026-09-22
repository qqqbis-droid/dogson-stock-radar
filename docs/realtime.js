(()=>{
  const REFRESH_MS = 10000;
  const MAX_CODES = 5;
  const FRESHNESS_MS = 60000;
  const quotes = new Map();
  let lastSuccessAt = 0;
  let busy = false;

  function apiUrl(){
    const configured=String(window.DOGSON_REALTIME_API||'').trim();
    if(configured) return configured.replace(/\/$/,'') + '/api/quote';
    return 'https://dogson-stock-radar-live.vercel.app/api/quote';
  }

  function codeFromCard(card){
    const t=card.querySelector('.code')?.textContent||'';
    const m=t.match(/\b\d{4}\b/);
    return m?m[0]:null;
  }

  function selectedCodes(){
    const out=[];
    const add=c=>{c=String(c||'').trim();if(/^\d{4}$/.test(c)&&!out.includes(c)&&out.length<MAX_CODES)out.push(c)};
    const q=document.getElementById('q')?.value.trim()||'';
    if(/^\d{4}$/.test(q)) add(q);
    try{
      if(q&&!/^\d{4}$/.test(q)){
        const hit=(typeof universe!=='undefined'?universe:[]).find(x=>String(x.name)===q);
        if(hit)add(hit.code);
      }
    }catch{}
    try{(typeof watchlist==='function'?watchlist():[]).forEach(add)}catch{}
    document.querySelectorAll('.card').forEach(card=>add(codeFromCard(card)));
    return out;
  }

  function n(v){const x=Number(v);return Number.isFinite(x)?x:null}
  function fmtPrice(v){if(v==null)return'—';return v>=1000?v.toFixed(0):v>=100?v.toFixed(1):v.toFixed(2)}
  function fmtPct(v){if(v==null)return'—';return `${v>=0?'+':''}${v.toFixed(2)}%`}
  function fmtTime(v){
    const x=n(v);
    if(!x)return'—';
    let ms=x;
    if(ms>1e14)ms/=1000;
    else if(ms<1e12)ms*=1000;
    const d=new Date(ms);
    return Number.isNaN(d.getTime())?'—':d.toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
  }
  function status(text,cls=''){
    const el=document.getElementById('liveStatus');
    if(!el)return;
    el.className=`live-status ${cls}`;
    el.textContent=text;
  }

  function setRadarPill(text,level='ok'){
    const el=document.getElementById('status');
    if(!el)return;
    el.textContent=text;
    if(level==='bad'){
      el.style.background='#2c141a';el.style.borderColor='#61303a';el.style.color='#ff9cac';
    }else if(level==='warn'){
      el.style.background='#2a230f';el.style.borderColor='#66521f';el.style.color='#ffd477';
    }else{
      el.style.background='#16263a';el.style.borderColor='#24496e';el.style.color='#9fd0ff';
    }
  }

  function taipeiClock(){
    const parts=new Intl.DateTimeFormat('en-CA',{
      timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',
      hour:'2-digit',minute:'2-digit',hourCycle:'h23'
    }).formatToParts(new Date());
    const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));
    return {year:+p.year,month:+p.month,day:+p.day,hour:+p.hour,minute:+p.minute};
  }

  function checkRadarFreshness(){
    try{
      // 盤後頁看的是完整日K/籌碼，不應拿盤中5分K最後時間當成錯誤警示。
      if(typeof mode!=='undefined'&&mode==='close'){setRadarPill('盤後資料','ok');return;}
      const rs=typeof intraRows!=='undefined'&&Array.isArray(intraRows)?intraRows:[];
      if(!rs.length)return;
      const now=taipeiClock();
      const date=`${now.year}-${String(now.month).padStart(2,'0')}-${String(now.day).padStart(2,'0')}`;
      let latest=-1;
      for(const r of rs){
        if(String(r.date||'')!==date)continue;
        const m=String(r.time||'').match(/^(\d{1,2}):(\d{2})/);
        if(!m)continue;
        latest=Math.max(latest,(+m[1])*60+(+m[2]));
      }
      if(latest<0){setRadarPill('盤後資料','ok');return;}
      const nowMin=now.hour*60+now.minute;
      const dow=new Date(Date.UTC(now.year,now.month-1,now.day)).getUTCDay();
      const weekday=dow>=1&&dow<=5;
      const hh=String(Math.floor(latest/60)).padStart(2,'0');
      const mm=String(latest%60).padStart(2,'0');
      const label=`${hh}:${mm}`;
      if(weekday&&nowMin>=540&&nowMin<=825){
        const age=nowMin-latest;
        if(age>15)setRadarPill(`⚠️ 雷達延遲 ${age}分`,'bad');
        else setRadarPill(`雷達 ${label}`,'ok');
        return;
      }
      if(weekday&&nowMin>825){
        if(latest<800)setRadarPill(`⚠️ 雷達提早停在 ${label}`,'warn');
        else setRadarPill(`已收盤 · ${label}`,'ok');
        return;
      }
      setRadarPill(`盤後資料 · ${label}`,'ok');
    }catch{}
  }

  function ensureStyles(){
    if(document.getElementById('liveQuoteStyles'))return;
    const s=document.createElement('style');s.id='liveQuoteStyles';
    s.textContent=`
      .live-status{margin:8px 2px 2px;padding:9px 11px;border:1px solid #285b48;border-radius:12px;background:#10241d;color:#8cf0bd;font-size:12px;font-weight:800}
      .live-status.warn{border-color:#66521f;background:#2a230f;color:#ffd477}.live-status.bad{border-color:#61303a;background:#2c141a;color:#ff9cac}
      .livequote{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:10px}.livecell{background:#0c1612;border:1px solid #244936;border-radius:11px;padding:9px}
      .liveval{font-size:15px;font-weight:900;color:#8cf0bd}.livelab{font-size:9px;color:#9ba5b6;margin-top:3px}.livequote.stale .livecell{border-color:#5f4d22;background:#211c0f}.livequote.stale .liveval{color:#ffd477}`;
    document.head.appendChild(s);
  }

  function applyQuotes(){
    ensureStyles();
    document.querySelectorAll('.card').forEach(card=>{
      const code=codeFromCard(card);if(!code)return;
      const q=quotes.get(code);
      let box=card.querySelector('.livequote');
      if(!box){box=document.createElement('div');box.className='livequote';const top=card.querySelector('.top');if(top)top.insertAdjacentElement('afterend',box);else card.prepend(box)}
      if(!q){
        box.classList.add('stale');
        box.innerHTML='<div class="livecell"><div class="liveval">—</div><div class="livelab">近即時價</div></div><div class="livecell"><div class="liveval">—</div><div class="livelab">近即時漲跌</div></div><div class="livecell"><div class="liveval">5分K</div><div class="livelab">未列入5檔即時池</div></div>';
        return;
      }
      const stale=Date.now()-q.receivedAt>30000;box.classList.toggle('stale',stale);
      box.innerHTML=`<div class="livecell"><div class="liveval">${fmtPrice(q.price)}</div><div class="livelab">近即時價</div></div><div class="livecell"><div class="liveval">${fmtPct(q.change)}</div><div class="livelab">近即時漲跌</div></div><div class="livecell"><div class="liveval">${fmtTime(q.time)}</div><div class="livelab">TWSE MIS${stale?' · 可能延遲':''}</div></div>`;
    });
  }

  async function refresh(){
    if(busy||document.hidden)return;
    if(typeof mode!=='undefined'&&mode!=='intraday')return;
    const endpoint=apiUrl();
    const codes=selectedCodes();
    if(!codes.length){status('🟡 尚無即時追蹤標的｜搜尋或加入關注後會追蹤最多5檔','warn');return;}
    busy=true;
    try{
      const url=`${endpoint}?codes=${encodeURIComponent(codes.join(','))}&_=${Date.now()}`;
      const r=await fetch(url,{cache:'no-store',credentials:'omit'});
      const j=await r.json();
      if(!r.ok||!j?.ok)throw new Error(j?.error||`HTTP ${r.status}`);
      let count=0;
      for(const x of j.quotes||[]){
        const code=String(x.code||'');const price=n(x.price);if(!/^\d{4}$/.test(code)||price==null)continue;
        quotes.set(code,{price,change:n(x.changePct),time:x.time,receivedAt:Date.now()});count++;
      }
      lastSuccessAt=Date.now();
      const now=new Date().toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
      status(`🟢 近即時 ${now}｜更新 ${count}/${codes.length} 檔｜每10秒嘗試刷新｜結構仍採5分K`);
      applyQuotes();
    }catch(e){
      const age=lastSuccessAt?Math.round((Date.now()-lastSuccessAt)/1000):null;
      status(age!=null?`⚠️ 即時行情暫時中斷｜上次成功 ${age} 秒前｜5分K雷達仍正常`:'⚠️ 即時行情尚未連線｜5分K雷達仍正常','bad');applyQuotes();
    }finally{busy=false}
  }

  function boot(){
    ensureStyles();applyQuotes();refresh();
    setTimeout(checkRadarFreshness,1200);
    setInterval(refresh,REFRESH_MS);
    setInterval(checkRadarFreshness,FRESHNESS_MS);
    const cards=document.getElementById('cards');if(cards){let t;new MutationObserver(()=>{clearTimeout(t);t=setTimeout(()=>{applyQuotes();refresh();checkRadarFreshness()},250)}).observe(cards,{childList:true,subtree:true})}
    document.addEventListener('visibilitychange',()=>{if(!document.hidden){refresh();checkRadarFreshness()}});
    document.getElementById('q')?.addEventListener('change',refresh);
    document.getElementById('scan')?.addEventListener('click',()=>setTimeout(refresh,150));
    document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>setTimeout(checkRadarFreshness,30)));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
