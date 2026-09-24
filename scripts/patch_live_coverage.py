#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

# 1) Backend MIS: small batches so the official endpoint does not silently truncate.
p=ROOT/'scripts'/'build_data.py'
s=p.read_text(encoding='utf-8')
a=s.index('def intraday_stock_snapshot(')
b=s.index('def _weighted_pct(',a)
block=s[a:b]
if 'batch_size = 10' not in block:
    block=block.replace('    out = {}\n\n    def fnum', '    out = {}\n    # MIS becomes unreliable when one ex_ch query carries too many symbols.\n    # Ten market-correct channels per request is intentionally conservative.\n    batch_size = 10\n\n    def fnum')
block=block.replace('for i in range(0, len(recs), 80):','for i in range(0, len(recs), batch_size):')
block=block.replace('part = recs[i:i+80]','part = recs[i:i+batch_size]')
s=s[:a]+block+s[b:]
p.write_text(s,encoding='utf-8')

# 2) Quote layer must not depend on successful 5m structural bridging.
p=ROOT/'scripts'/'bridge_intraday.py'
s=p.read_text(encoding='utf-8')
s=s.replace('v1.4.2 MIS snapshot bridge','v1.4.3 MIS snapshot bridge')
needle='    by_code = {str(r.get("code")): r for r in rows}\n    bridged = 0\n'
if 'quoted_rows = 0' not in s:
    repl='''    by_code = {str(r.get("code")): r for r in rows}\n\n    # Official quote and 5-minute structure are two independent layers.\n    # A stock with a valid MIS quote must show the live price even when Yahoo\n    # history or the snapshot-built 5m bar is temporarily unavailable.\n    quoted_rows = 0\n    for code, q in quotes.items():\n        row = by_code.get(str(code))\n        if not row:\n            continue\n        row["quote_date"] = q.get("date")\n        row["quote_time"] = q.get("time")\n        row["quote_source"] = q.get("source")\n        row["quote_close"] = q.get("close")\n        if q.get("close") is not None:\n            row["close"] = q.get("close")\n        if q.get("change_pct") is not None:\n            row["day_change"] = round(float(q.get("change_pct")), 2)\n        if row.get("vwap") and row.get("close") is not None:\n            try:\n                row["vwap_dist"] = round((float(row["close"]) / float(row["vwap"]) - 1) * 100, 2)\n            except Exception:\n                pass\n        quoted_rows += 1\n\n    bridged = 0\n'''
    if needle not in s:
        raise SystemExit('bridge insertion marker not found')
    s=s.replace(needle,repl,1)
s=s.replace('"version": "1.4.2"','"version": "1.4.3"')
s=s.replace('"version": "1.5.29-free"','"version": "1.5.30-free"')
s=s.replace('print("MIS bridge done", "rows", bridged, "volume_ok", volume_ok, "quote", quote_latest, "structure", structure_latest)', 'print("MIS bridge done", "quotes", quoted_rows, "structure_rows", bridged, "volume_ok", volume_ok, "quote", quote_latest, "structure", structure_latest)')
p.write_text(s,encoding='utf-8')

# 3) Mobile near-real-time: prioritize cards actually visible on screen.
p=ROOT/'docs'/'realtime.js'
s=p.read_text(encoding='utf-8')
s=s.replace('const MAX_CODES = 15;','const MAX_CODES = 24;')
a=s.index('  function selectedCodes(){')
b=s.index('  function n(v){',a)
new='''  function selectedCodes(){\n    const out=[];const add=c=>{c=String(c||'').trim();if(/^\\d{4}$/.test(c)&&!out.includes(c)&&out.length<MAX_CODES)out.push(c)};\n    const q=document.getElementById('q')?.value.trim()||'';\n    if(/^\\d{4}$/.test(q))add(q);\n    try{if(q&&!/^\\d{4}$/.test(q)){const hit=(typeof universe!=='undefined'?universe:[]).find(x=>String(x.name)===q);if(hit)add(hit.code)}}catch{}\n    // What the user is looking at wins over cards that happen to be earlier in DOM order.\n    const cards=[...document.querySelectorAll('.card')];\n    cards.filter(card=>{const r=card.getBoundingClientRect();return r.bottom>=-240&&r.top<=window.innerHeight+240}).forEach(card=>add(codeFromCard(card)));\n    // Then keep portfolio/watchlist names warm in the remaining slots.\n    try{(typeof watchlist==='function'?watchlist():[]).forEach(add)}catch{}\n    cards.forEach(card=>add(codeFromCard(card)));\n    return out;\n  }\n'''
s=s[:a]+new+s[b:]
old="if(!q){box.innerHTML='<div class=\"livecell\"><div class=\"liveval\">—</div><div class=\"livelab\">官方即時價</div></div><div class=\"livecell\"><div class=\"liveval\">—</div><div class=\"livelab\">即時漲跌</div></div><div class=\"livecell\"><div class=\"liveval\">5分K</div><div class=\"livelab\">等待進入即時池</div></div>';return}"
newmissing="if(!q){const r=card.getBoundingClientRect(),onscreen=r.bottom>=-240&&r.top<=window.innerHeight+240;box.innerHTML=`<div class=\"livecell\"><div class=\"liveval\">—</div><div class=\"livelab\">官方即時價</div></div><div class=\"livecell\"><div class=\"liveval\">—</div><div class=\"livelab\">即時漲跌</div></div><div class=\"livecell\"><div class=\"liveval\">5分K</div><div class=\"livelab\">${onscreen?'官方行情重試中':'滑到此卡即優先追蹤'}</div></div>`;return}"
if old in s:
    s=s.replace(old,newmissing)
if "addEventListener('scroll'" not in s:
    s=s.replace("document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});", "document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});let scrollTimer;addEventListener('scroll',()=>{clearTimeout(scrollTimer);scrollTimer=setTimeout(refresh,180)},{passive:true});")
p.write_text(s,encoding='utf-8')

print('live coverage patch applied')
