#!/usr/bin/env python3
from pathlib import Path
p=Path('docs/realtime.js')
s=p.read_text(encoding='utf-8')

s=s.replace("  const quotes = new Map();\n", "  const quotes = new Map();\n  const STORE_KEY = 'dogson-last-real-trades-v1';\n  const STORE_MAX_AGE = 8*60*60*1000;\n")

marker="  function n(v){const x=Number(v);return Number.isFinite(x)?x:null}\n"
insert=r'''  function n(v){const x=Number(v);return Number.isFinite(x)?x:null}
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
      const c=String(r.code||''),px=n(r.quote_close),qd=String(r.quote_date||''),qt=String(r.quote_time||'');if(!/^\d{4}$/.test(c)||px==null||!qd||!qt)continue;
      const ms=Date.parse(`${qd}T${qt.length===5?qt+':00':qt}+08:00`);if(!Number.isFinite(ms)||Date.now()-ms>STORE_MAX_AGE)continue;
      setQuote(c,{price:px,change:n(r.day_change),time:ms,receivedAt:Date.now(),source:r.quote_source||'TWSE MIS last trade'});
    }}catch{}
  }
'''
if marker not in s: raise SystemExit('marker n() not found')
s=s.replace(marker,insert,1)

old="quotes.set(code,{price,change:n(x.changePct),time:x.time,receivedAt:Date.now()});count++;"
new="setQuote(code,{price,change:n(x.changePct),time:x.time,receivedAt:Date.now(),source:'TWSE MIS live trade'});count++;"
if old not in s: raise SystemExit('quote set marker not found')
s=s.replace(old,new,1)

oldboot="  function boot(){ensureStyles();applyQuotes();refresh();setTimeout(checkRadarFreshness,1000);"
newboot="  function boot(){ensureStyles();loadStored();seedFromRows();applyQuotes();refresh();setTimeout(checkRadarFreshness,1000);"
if oldboot not in s: raise SystemExit('boot marker not found')
s=s.replace(oldboot,newboot,1)

# Persist successful true trades after every polling cycle.
s=s.replace("status(`🟢 官方近即時 ${latestQuoteLabel}｜更新 ${count}/${codes.length} 檔｜每10秒｜5分K結構分開顯示`);applyQuotes();checkRadarFreshness();",
            "saveStored();status(`🟢 官方近即時 ${latestQuoteLabel}｜新成交 ${count}/${codes.length} 檔｜其餘沿用最後真實成交｜每10秒`);applyQuotes();checkRadarFreshness();")

p.write_text(s,encoding='utf-8')
print('patched realtime.js persistent true-trade cache')
