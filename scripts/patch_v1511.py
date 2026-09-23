#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.11 — 盤中族群資金輪動整區可展開／收合。

只改 UI 互動，不改族群熱度、個股分數或任何後端公式。
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def must_replace(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f"v1.5.11 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    s = re.sub(
        r"Free Edition v1\.5\.\d+｜[^<]*",
        "Free Edition v1.5.11｜盤中族群輪動可收合＋族群共振全可展開＋盤後族群資金流",
        s,
        count=1,
    )

    old_state = 'let sectorFundsOpen=localStorage.getItem("dogsonSectorFundsOpen")==="1";'
    new_state = old_state + '\nlet sectorRotationOpen=localStorage.getItem("dogsonSectorRotationOpen")==="1";'
    if 'dogsonSectorRotationOpen' not in s:
        s = must_replace(s, old_state, new_state, "intraday rotation state")

    old_toggle = '''function toggleCloseSectorFunds(){\n sectorFundsOpen=!sectorFundsOpen;\n localStorage.setItem("dogsonSectorFundsOpen",sectorFundsOpen?"1":"0");\n const box=document.getElementById("rotationbox");\n if(box)box.innerHTML=rotationHTML();\n}\n'''
    new_toggle = old_toggle + '''\nfunction toggleIntradaySectorRotation(){\n sectorRotationOpen=!sectorRotationOpen;\n localStorage.setItem("dogsonSectorRotationOpen",sectorRotationOpen?"1":"0");\n const box=document.getElementById("rotationbox");\n if(box)box.innerHTML=rotationHTML();\n}\n'''
    if 'function toggleIntradaySectorRotation()' not in s:
        s = must_replace(s, old_toggle, new_toggle, "intraday rotation toggle")

    old_return = ''' return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">💰 族群資金輪動</div><div class="sub">成交金額占比變化＋價格＋VWAP＋廣度；不是法人淨流入</div></div></div><div class="rotationcols"><div><div class="rotationhead">🔥 吸金中</div>${hot.length?hot.map(one).join(""):`<div class="sub">暫無明顯流入族群</div>`}</div><div><div class="rotationhead">🧊 流失／降溫</div>${cold.length?cold.map(one).join(""):`<div class="sub">暫無明顯流失族群</div>`}</div></div></div>`;\n'''
    new_return = ''' const mini=x=>`<div class="closeflowpreviewitem"><span>${x.sector}</span><b>${signed(x.heat,1,"")}</b></div>`;\n const preview=`<div class="closeflowpreview"><div class="closeflowpreviewcol"><div class="closeflowpreviewhead">🔥 吸金前 3</div>${hot.length?hot.slice(0,3).map(mini).join(""):`<div class="sub">暫無明顯吸金族群</div>`}</div><div class="closeflowpreviewcol"><div class="closeflowpreviewhead">🧊 降溫前 3</div>${cold.length?cold.slice(0,3).map(mini).join(""):`<div class="sub">暫無明顯流失族群</div>`}</div></div>`;\n const detail=sectorRotationOpen?`<div class="rotationcols"><div><div class="rotationhead">🔥 吸金中</div>${hot.length?hot.map(one).join(""):`<div class="sub">暫無明顯流入族群</div>`}</div><div><div class="rotationhead">🧊 流失／降溫</div>${cold.length?cold.map(one).join(""):`<div class="sub">暫無明顯流失族群</div>`}</div></div>`:"";\n const label=sectorRotationOpen?"收合族群輪動":"展開完整輪動";\n const arrow=sectorRotationOpen?"▲":"▼";\n return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">💰 族群資金輪動</div><div class="sub">成交金額占比變化＋價格＋VWAP＋廣度；不是法人淨流入</div></div><button class="rotationtoggle" type="button" aria-expanded="${sectorRotationOpen}" onclick="toggleIntradaySectorRotation()">${arrow} ${label}</button></div>${preview}${detail}</div>`;\n'''
    if '展開完整輪動' not in s:
        s = must_replace(s, old_return, new_return, "intraday rotation render")

    help_old = '<b>資金輪動：</b>看族群成交金額占比的近30分鐘變化，再合併漲跌、站VWAP比例、上漲家數與量速；這是吸金熱度，不是法人淨流入。盤中可直接點族群展開目前掃描到的同族群股票，再點股票查看小卡。<br><br>'
    help_new = '<b>資金輪動：</b>看族群成交金額占比的近30分鐘變化，再合併漲跌、站VWAP比例、上漲家數與量速；這是吸金熱度，不是法人淨流入。整個盤中族群輪動區可展開／收合，狀態會記住；展開後仍可再點單一族群看同族群股票，再點股票查看小卡。<br><br>'
    if '整個盤中族群輪動區可展開／收合' not in s:
        s = must_replace(s, help_old, help_new, "rotation help")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v1511", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_index()
    patch_sw()
    print("v1.5.11 intraday sector rotation collapse patch applied")
