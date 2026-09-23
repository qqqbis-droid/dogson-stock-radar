#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.6: make intraday sector capital-rotation rows drill into member stocks.

Scope intentionally limited to user request #1:
- Click a sector in intraday capital rotation to expand its member stocks.
- Click a member stock to reuse the existing peer mini-card.
- No score/formula/backend changes.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "index.html"
SW = ROOT / "docs" / "sw.js"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"marker not found: {label}")
    return text.replace(old, new, 1)


s = HTML.read_text(encoding="utf-8")

s = replace_once(
    s,
    'Free Edition v1.5.5｜盤中振幅效率＋盤中動能100＋盤後波段100',
    'Free Edition v1.5.6｜盤中族群資金可展開＋振幅效率＋動能100',
    'version header',
)

old_css = '.rotationbox{background:linear-gradient(180deg,#151c27,#111720);border:1px solid var(--line);border-radius:18px;padding:13px;margin:12px 0}.rotationtop{display:flex;justify-content:space-between;align-items:flex-start}.rotationtitle{font-size:18px;font-weight:900}.rotationcols{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.rotationhead{font-size:13px;font-weight:900;margin-bottom:6px}.rotationrow{display:flex;justify-content:space-between;gap:8px;background:#0e131a;border:1px solid #252d39;border-radius:11px;padding:9px;margin:6px 0;font-size:11px}.rotationleaders{color:var(--muted);margin-top:4px}.rotationnums{text-align:right;color:#cbd3df;line-height:1.45;min-width:138px}@media(max-width:620px){.rotationcols{grid-template-columns:1fr}.rotationrow{font-size:10px}}'
new_css = '.rotationbox{background:linear-gradient(180deg,#151c27,#111720);border:1px solid var(--line);border-radius:18px;padding:13px;margin:12px 0}.rotationtop{display:flex;justify-content:space-between;align-items:flex-start}.rotationtitle{font-size:18px;font-weight:900}.rotationcols{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.rotationhead{font-size:13px;font-weight:900;margin-bottom:6px}.rotationgroup{margin:6px 0;padding:0;border:0}.rotationgroup>summary{list-style:none}.rotationgroup>summary::-webkit-details-marker{display:none}.rotationrow{display:flex;justify-content:space-between;gap:8px;background:#0e131a;border:1px solid #252d39;border-radius:11px;padding:9px;margin:0;font-size:11px;cursor:pointer}.rotationrow:hover{border-color:#38506d}.rotationleaders{color:var(--muted);margin-top:4px}.rotationnums{text-align:right;color:#cbd3df;line-height:1.45;min-width:138px}.rotationopen{display:inline-block;margin-top:5px;color:#9cc9ff;font-weight:850}.rotationmembers{display:grid;gap:6px;padding:7px 3px 2px}.rotationmember{width:100%;border:1px solid #29313e;background:#111823;color:#edf2fa;border-radius:9px;padding:8px 9px;display:flex;justify-content:space-between;align-items:center;text-align:left;cursor:pointer;font-size:11px}.rotationmember small{color:var(--muted);margin-left:5px}.rotationmember .rmscore{color:#9cc9ff;font-weight:850;white-space:nowrap}.rotationmember:active{transform:scale(.995)}@media(max-width:620px){.rotationcols{grid-template-columns:1fr}.rotationrow{font-size:10px}}'
s = replace_once(s, old_css, new_css, 'rotation css')

old_one = ' const one=x=>`<div class="rotationrow"><div><b>${x.state}｜${x.sector}</b><div class="rotationleaders">${(x.leaders||[]).map(s=>`${s.name} ${signed(s.change_pct,1)}`).join(" · ")}</div></div><div class="rotationnums">熱度 ${signed(x.heat,1,"")}<br>族群 ${signed(x.change_pct,1)}｜資金占比 ${num(x.turnover_share_pct,1)}%<br>${x.share_change_pp===null||x.share_change_pp===undefined?"占比變化待累積":`近${x.window_min||30}分占比 ${signed(x.share_change_pp,2,"pp")}`}｜VWAP上 ${num(x.above_vwap_pct,0)}%</div></div>`;'
new_one = ''' const one=x=>{\n  const members=intraRows\n   .filter(r=>(r.sector_group||"").trim()===(x.sector||"").trim())\n   .sort((a,b)=>(+(b.intraday_score??b.score)||0)- (+(a.intraday_score??a.score)||0) || (+(b.day_change)||0)- (+(a.day_change)||0));\n  const memberHTML=members.length?members.slice(0,30).map(r=>`<button class="rotationmember peerlink" data-code="${r.code}"><span><b>${r.code} ${r.name}</b><small>${signed(r.day_change,1)} · ${r.category||"觀察"}</small></span><span class="rmscore">${num(r.intraday_score??r.score,0)}/100</span></button>`).join(""):`<div class="sub">目前沒有可展開的盤中個股資料</div>`;\n  return `<details class="rotationgroup"><summary class="rotationrow"><div><b>${x.state}｜${x.sector}</b><div class="rotationleaders">${(x.leaders||[]).map(s=>`${s.name} ${signed(s.change_pct,1)}`).join(" · ")}</div><span class="rotationopen">查看族群 ${members.length} 檔 ▾</span></div><div class="rotationnums">熱度 ${signed(x.heat,1,"")}<br>族群 ${signed(x.change_pct,1)}｜資金占比 ${num(x.turnover_share_pct,1)}%<br>${x.share_change_pp===null||x.share_change_pp===undefined?"占比變化待累積":`近${x.window_min||30}分占比 ${signed(x.share_change_pp,2,"pp")}`}｜VWAP上 ${num(x.above_vwap_pct,0)}%</div></summary><div class="rotationmembers">${memberHTML}</div></details>`;\n };'''
s = replace_once(s, old_one, new_one, 'rotation member drilldown')

old_help = '<b>資金輪動：</b>看族群成交金額占比的近30分鐘變化，再合併漲跌、站VWAP比例、上漲家數與量速；這是吸金熱度，不是法人淨流入。'
new_help = '<b>資金輪動：</b>看族群成交金額占比的近30分鐘變化，再合併漲跌、站VWAP比例、上漲家數與量速；這是吸金熱度，不是法人淨流入。盤中可直接點族群展開目前掃描到的同族群股票，再點股票查看小卡。'
s = replace_once(s, old_help, new_help, 'rotation help')

HTML.write_text(s, encoding="utf-8")

sw = SW.read_text(encoding="utf-8")
if "dogson-free-v155" in sw:
    sw = sw.replace("dogson-free-v155", "dogson-free-v156", 1)
elif "dogson-free-v156" not in sw:
    raise SystemExit("service worker cache marker not found")
SW.write_text(sw, encoding="utf-8")

print("v1.5.6 intraday sector rotation drilldown patched")
