#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.9 — 盤中相對強弱透明化。

只處理使用者第 4 點：不改 15 分公式，只把比較基準、相對強弱差值與
分段評分規則清楚顯示在 UI / 教學。
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
        raise SystemExit(f"v1.5.9 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    s = re.sub(
        r"Free Edition v1\.5\.\d+｜[^<]*",
        "Free Edition v1.5.9｜盤中相對強弱透明化＋盤後族群資金流可收合＋振幅效率",
        s,
        count=1,
    )

    old = '<div class="part"><div class="partv">${num(c.relative_strength,0)}/15</div><div class="partl">相對強弱 ${signed(c.relative_strength_pct,1)}</div></div>'
    new = '<div class="part"><div class="partv">${num(c.relative_strength,0)}/15</div><div class="partl">相對${String(r.market)==="上櫃"?"櫃買":"加權"} ${signed(c.relative_strength_pct,1)}</div></div>'
    if '相對${String(r.market)==="上櫃"?"櫃買":"加權"}' not in s:
        s = must_replace(s, old, new, "relative strength benchmark label")

    marker = '<b>盤中動能 100：</b>價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10。籌碼只顯示為「偏多/中性/偏空背景」，不灌入盤中分數。<br>'
    explain = marker + '<b>盤中相對強弱 15：</b>這不是 RSI。上市股拿個股當日漲跌去減「加權指數」當日漲跌；上櫃股則減「櫃買指數」當日漲跌。相對市場 ≥+2.0%＝10分、+1.0～&lt;+2.0%＝8分、+0.3～&lt;+1.0%＝6分、0～&lt;+0.3%＝4分、-1.0～&lt;0%＝2分、≤-1.0%＝0分；若同時現價≥VWAP 且近15分鐘漲幅&gt;0，再加5分，最高15分。也就是「比市場強」最多10分，「盤中仍站強勢結構」再加5分。<br>'
    if '<b>盤中相對強弱 15：</b>' not in s:
        s = must_replace(s, marker, explain, "relative strength help")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v159", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_index()
    patch_sw()
    print("v1.5.9 relative strength explanation patch applied")
