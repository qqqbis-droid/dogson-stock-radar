#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=ROOT/'docs'/'index.html'
RT=ROOT/'docs'/'realtime.js'


def once(text, old, new, label):
    if new in text:
        print(label,'already applied'); return text
    if old not in text:
        raise SystemExit(f'marker missing: {label}')
    return text.replace(old,new,1)

h=HTML.read_text(encoding='utf-8')
h=h.replace('Free Edition v1.3.1｜收盤覆核＋嚴格族群修正版','Free Edition v1.3.2｜收盤覆核＋籌碼狀態修正版',1)
h=once(h,
'function lots(v){return v===null||v===undefined?"—":num((+v)/1000,0)+"張"}\n',
'function lots(v){return v===null||v===undefined?"—":num((+v)/1000,0)+"張"}\nfunction marketLots(v){if(v===null||v===undefined||Number.isNaN(+v))return "—";v=+v;return Math.abs(v)>=10000?signed(v/10000,1,"萬張"):signed(v,0,"張")}\n',
'market lots formatter')
h=once(h,
'${m.foreign_net_lots===null||m.foreign_net_lots===undefined?"—":signed(m.foreign_net_lots,0,"張")}',
'${marketLots(m.foreign_net_lots)}',
'market foreign display')
h=h.replace('<b>籌碼 25：</b>外資連3買、借券賣出連3減、投信、融資。覆蓋率低於60%時品質總分會標示「資料待補」，不再用假精準分數誤導。',
'<b>籌碼 25：</b>外資連3買、借券賣出連3減、投信、融資。覆蓋率低於60%時品質總分會標示「資料待補」，不再用假精準分數誤導。盤後會在14:25、20:30、23:40及次日08:15自動重抓，補齊較晚公布的融資與借券資料。')
HTML.write_text(h,encoding='utf-8')

r=RT.read_text(encoding='utf-8')
r=once(r,
'  function checkRadarFreshness(){\n    try{\n      const rs=',
'  function checkRadarFreshness(){\n    try{\n      // 盤後頁看的是完整日K/籌碼，不應拿盤中5分K最後時間當成錯誤警示。\n      if(typeof mode!==\'undefined\'&&mode===\'close\'){setRadarPill(\'盤後資料\',\'ok\');return;}\n      const rs=',
'mode aware freshness')
r=once(r,
"    document.getElementById('scan')?.addEventListener('click',()=>setTimeout(refresh,150));\n",
"    document.getElementById('scan')?.addEventListener('click',()=>setTimeout(refresh,150));\n    document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>setTimeout(checkRadarFreshness,30)));\n",
'tab freshness refresh')
RT.write_text(r,encoding='utf-8')
print('v1.3.2 patch applied')
