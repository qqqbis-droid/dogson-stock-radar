#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.14 — 盤後今日法人金額排名 + 盤中成交資金輪動命名透明化。

只調整排序語意與前端文字：
- 盤後流入/流出 TOP 3 與完整清單，以「今日估算法人淨額」排序。
- 5日/20日保留作趨勢觀察，不再干擾「今日 TOP」名次。
- 盤中明確標示為「成交資金輪動／吸金熱度」，避免誤認為法人淨流入。
不改任何個股100分、大盤15分、盤中 Heat 計算或法人估算公式。
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
        raise SystemExit(f"v1.5.14 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)
    s = re.sub(
        r"Free Edition v1\.5\.\d+｜[^<]*",
        "Free Edition v1.5.14｜盤後今日法人金額排名＋盤中成交資金輪動透明化",
        s,
        count=1,
    )

    old = ''' const strength=x=>x.net5_amount_100m??x.today_amount_100m??0;\n const allBuys=arr.filter(x=>(x.today_amount_100m??0)>0).sort((a,b)=>strength(b)-strength(a));\n const allSells=arr.filter(x=>(x.today_amount_100m??0)<0).sort((a,b)=>strength(a)-strength(b));'''
    new = ''' const todayStrength=x=>x.today_amount_100m??0;\n // v1.5.14：既然畫面寫「今日 TOP」，名次就只看今日估算法人淨額。\n // 5日/20日留在卡片裡看趨勢，不再干擾今日排名。\n const allBuys=arr.filter(x=>(x.today_amount_100m??0)>0).sort((a,b)=>todayStrength(b)-todayStrength(a));\n const allSells=arr.filter(x=>(x.today_amount_100m??0)<0).sort((a,b)=>todayStrength(a)-todayStrength(b));'''
    s = must_replace(s, old, new, "today amount ranking")

    s = must_replace(s, '🔴 流入前 3', '🔴 今日估算流入 TOP 3', "buy preview title")
    s = must_replace(s, '🟢 流出前 3', '🟢 今日估算流出 TOP 3', "sell preview title")
    s = must_replace(
        s,
        '依估算金額力度排序｜今日流入 ${allBuys.length} 個族群｜流出 ${allSells.length} 個族群',
        '依今日估算法人淨額排序｜今日流入 ${allBuys.length} 個族群｜流出 ${allSells.length} 個族群',
        "preview ranking note",
    )

    # Two visible intraday panel titles (empty state + normal state).
    s = s.replace('💰 族群資金輪動', '💰 盤中族群成交資金輪動')
    s = must_replace(
        s,
        '成交金額占比變化＋價格＋VWAP＋廣度；不是法人淨流入',
        '吸金熱度＝成交金額占比變化＋價格＋VWAP＋廣度＋量速；反映市場成交資金輪動，不是法人淨流入',
        "intraday rotation explanation",
    )

    write(p, s)


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)
    old = '''    out.sort(\n        key=lambda x: (\n            abs(float(x.get("net5_amount_100m") or x.get("today_amount_100m") or 0)),\n            abs(float(x.get("net5_lots") or x.get("today_lots") or 0)),\n        ),\n        reverse=True,\n    )'''
    new = '''    # v1.5.14：資料層也統一以「今日估算法人淨額」力度排序。\n    # 5日/20日只作趨勢欄位，不影響今日榜名次。\n    out.sort(\n        key=lambda x: (\n            abs(float(x.get("today_amount_100m") or 0)),\n            abs(float(x.get("today_lots") or 0)),\n        ),\n        reverse=True,\n    )'''
    s = must_replace(s, old, new, "backend today amount order")
    s = s.replace('"version": "1.5.12-free"', '"version": "1.5.14-free"')
    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v1514", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_index()
    patch_build_data()
    patch_sw()
    print("v1.5.14 today-money ranking + intraday rotation naming patch applied")
