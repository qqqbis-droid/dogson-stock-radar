#!/usr/bin/env python3
from pathlib import Path
p=Path('docs/realtime.js')
s=p.read_text(encoding='utf-8')

s=s.replace('''  const quotes = new Map();
  const STORE_KEY = 'dogson-last-real-trades-v1';
''','''  const quotes = new Map();
  const snapshots = new Map();
  const STORE_KEY = 'dogson-last-real-trades-v1';
''',1)

old_seed='''  function seedFromRows(){
    try{for(const r of (typeof intraRows!=='undefined'&&Array.isArray(intraRows)?intraRows:[])){
      const c=String(r.code||''),px=n(r.quote_close),qd=String(r.quote_date||''),qt=String(r.quote_time||'');if(!/^\\d{4}$/.test(c)||px==null||!qd||!qt)continue;
      const ms=Date.parse(`${qd}T${qt.length===5?qt+':00':qt}+08:00`);if(!Number.isFinite(ms)||Date.now()-ms>STORE_MAX_AGE)continue;
      setQuote(c,{price:px,change:n(r.day_change),time:ms,receivedAt:Date.now(),source:r.quote_source||'TWSE MIS last trade'});
    }}catch{}
  }
'''
new_seed='''  function seedFromRows(){
    try{for(const r of (typeof intraRows!=='undefined'&&Array.isArray(intraRows)?intraRows:[])){
      const c=String(r.code||'');if(!/^\\d{4}$/.test(c))continue;
      const st=String(r.quote_snapshot_time||'').trim();
      if(st)snapshots.set(c,{bid1:n(r.quote_bid1),ask1:n(r.quote_ask1),time:st,receivedAt:Date.now(),source:'TWSE MIS snapshot'});
      const px=n(r.quote_close),qd=String(r.quote_date||''),qt=String(r.quote_time||'');if(px==null||!qd||!qt)continue;
      const ms=Date.parse(`${qd}T${qt.length===5?qt+':00':qt}+08:00`);if(!Number.isFinite(ms)||Date.now()-ms>STORE_MAX_AGE)continue;
      setQuote(c,{price:px,change:n(r.day_change),time:ms,receivedAt:Date.now(),source:r.quote_source||'TWSE MIS last trade'});
    }}catch{}
  }
'''
if old_seed not in s: raise SystemExit('seedFromRows marker not found')
s=s.replace(old_seed,new_seed,1)

old_apply='''      if(!q){const r=card.getBoundingClientRect(),onscreen=r.bottom>=-240&&r.top<=window.innerHeight+240;box.innerHTML=`<div class="livecell"><div class="liveval">—</div><div class="livelab">官方即時價</div></div><div class="livecell"><div class="liveval">—</div><div class="livelab">即時漲跌</div></div><div class="livecell"><div class="liveval">5分K</div><div class="livelab">${onscreen?'官方行情重試中':'滑到此卡即優先追蹤'}</div></div>`;return}
      box.innerHTML=`<div class="livecell"><div class="liveval">${fmtPrice(q.price)}</div><div class="livelab">官方即時價</div></div><div class="livecell"><div class="liveval">${fmtPct(q.change)}</div><div class="livelab">即時漲跌</div></div><div class="livecell"><div class="liveval">${fmtTime(q.time)}</div><div class="livelab">TWSE MIS｜結構仍採5分K</div></div>`;
'''
new_apply='''      const snap=snapshots.get(code);
      const snapTime=snap?(typeof snap.time==='number'?fmtTime(snap.time):String(snap.time||'—')):'—';
      if(!q){const r=card.getBoundingClientRect(),onscreen=r.bottom>=-240&&r.top<=window.innerHeight+240;
        if(snap){box.innerHTML=`<div class="livecell"><div class="liveval">買 ${fmtPrice(snap.bid1)}</div><div class="livelab">MIS 買一｜非成交價</div></div><div class="livecell"><div class="liveval">賣 ${fmtPrice(snap.ask1)}</div><div class="livelab">MIS 賣一｜非成交價</div></div><div class="livecell"><div class="liveval">${snapTime}</div><div class="livelab">官方快照｜等下一筆成交</div></div>`;return}
        box.innerHTML=`<div class="livecell"><div class="liveval">—</div><div class="livelab">最後真實成交</div></div><div class="livecell"><div class="liveval">—</div><div class="livelab">MIS 買賣盤</div></div><div class="livecell"><div class="liveval">5分K</div><div class="livelab">${onscreen?'官方行情重試中':'滑到此卡即優先追蹤'}</div></div>`;return}
      box.innerHTML=`<div class="livecell"><div class="liveval">${fmtPrice(q.price)}</div><div class="livelab">最後真實成交</div></div><div class="livecell"><div class="liveval">${fmtPct(q.change)}</div><div class="livelab">依最後成交計算</div></div><div class="livecell"><div class="liveval">${fmtTime(q.time)}</div><div class="livelab">成交時間｜MIS快照 ${snapTime}</div></div>`;
'''
if old_apply not in s: raise SystemExit('applyQuotes marker not found')
s=s.replace(old_apply,new_apply,1)

old_refresh='''      const results=await Promise.allSettled(batches.map(b=>fetchBatch(endpoint,b)));let count=0,newest=null;
      for(const rr of results){if(rr.status!=='fulfilled')continue;for(const x of rr.value){const code=String(x.code||''),price=n(x.price);if(!/^\\d{4}$/.test(code)||price==null)continue;setQuote(code,{price,change:n(x.changePct),time:x.time,receivedAt:Date.now(),source:'TWSE MIS live trade'});count++;const d=toDate(x.time);if(d&&(!newest||d>newest))newest=d}}
      if(!count)throw new Error('no quotes');lastSuccessAt=Date.now();latestQuoteLabel=(newest||new Date()).toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',hour12:false});
      saveStored();status(`🟢 官方近即時 ${latestQuoteLabel}｜新成交 ${count}/${codes.length} 檔｜其餘沿用最後真實成交｜每10秒`);applyQuotes();checkRadarFreshness();
'''
new_refresh='''      const results=await Promise.allSettled(batches.map(b=>fetchBatch(endpoint,b)));let count=0,snapshotCount=0,newest=null;
      for(const rr of results){if(rr.status!=='fulfilled')continue;for(const x of rr.value){const code=String(x.code||'');if(!/^\\d{4}$/.test(code))continue;
        snapshots.set(code,{bid1:n(x.bid1),ask1:n(x.ask1),time:x.time,receivedAt:Date.now(),source:x.source||'TWSE MIS snapshot'});snapshotCount++;const d=toDate(x.time);if(d&&(!newest||d>newest))newest=d;
        const price=n(x.price);if(price==null)continue;setQuote(code,{price,change:n(x.changePct),time:x.time,receivedAt:Date.now(),source:'TWSE MIS live trade'});count++;}}
      if(!snapshotCount)throw new Error('no MIS snapshots');lastSuccessAt=Date.now();latestQuoteLabel=(newest||new Date()).toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',hour12:false});
      saveStored();status(`🟢 MIS快照 ${latestQuoteLabel}｜覆蓋 ${snapshotCount}/${codes.length}｜本輪新成交 ${count}｜無成交顯示買一/賣一`);applyQuotes();checkRadarFreshness();
'''
if old_refresh not in s: raise SystemExit('refresh marker not found')
s=s.replace(old_refresh,new_refresh,1)

p.write_text(s,encoding='utf-8')
print('patched realtime UI: live orderbook snapshot fallback')
