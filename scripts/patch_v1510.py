#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.10 — 修正盤中族群共振有分數卻無法展開。

不改任何族群/個股評分公式：
- 有自訂窄族群：維持原本 sector_group 與 peers。
- 沒有窄族群但有官方產業代理分：補同官方產業 peers，讓 UI 可展開。
- 前端優先用窄族群；否則以官方產業代理作為可點群組。
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
        raise SystemExit(f"v1.5.10 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)

    # Source/version label only; scoring formula is intentionally untouched.
    s = re.sub(r"Free Edition v1\.5\.\d+", "Free Edition v1.5.10", s, count=1)
    s = s.replace('"version": "1.5.7-free"', '"version": "1.5.10-free"')

    old = '''        else:\n            n = int(industry_hot.get(industry, 0)) if industry and industry != "未分類" else 0\n            total_n = int(industry_total.get(industry, 0)) if industry and industry != "未分類" else 0\n            ratio = (n / total_n) if total_n else 0\n            sec = sector_score(n, ratio, True)\n            source = "官方產業代理" if total_n else "待分類"\n            label = industry if total_n else "待分類"\n'''
    new = '''        else:\n            n = int(industry_hot.get(industry, 0)) if industry and industry != "未分類" else 0\n            total_n = int(industry_total.get(industry, 0)) if industry and industry != "未分類" else 0\n            ratio = (n / total_n) if total_n else 0\n            sec = sector_score(n, ratio, True)\n            source = "官方產業代理" if total_n else "待分類"\n            label = industry if total_n else "待分類"\n            # v1.5.10：官方產業代理原本只有分數、沒有 peers，導致前端無法展開。\n            # 只補同產業成分股清單，不改 sec / ratio / 任何評分公式。\n            if total_n:\n                group_rows = [\n                    x for x in rows\n                    if str(x.get("industry_name") or "").strip() == industry\n                ]\n'''
    if "v1.5.10：官方產業代理原本只有分數" not in s:
        s = must_replace(s, old, new, "official-industry peers")

    s = s.replace(")[:10]\n            r[\"sector_peers\"]", ")[:15]\n            r[\"sector_peers\"]", 1)

    write(p, s)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    s = re.sub(
        r"Free Edition v1\.5\.\d+｜[^<]*",
        "Free Edition v1.5.10｜族群共振全可展開＋相對強弱透明化＋盤後族群資金流",
        s,
        count=1,
    )

    pattern = re.compile(r"function groupHTML\(r\)\{.*?\n\}\n\nfunction partsHTML", re.S)
    replacement = r'''function groupHTML(r){
 const narrow=(r.sector_group||"").trim();
 const source=(r.sector_score_source||"").trim();
 const label=(r.sector_score_label||"").trim();
 const key=narrow || (source==="官方產業代理"?label:"");
 if(!key||key==="待分類")return "";
 const d=r.sector_detail||{};
 const fallback=narrow
  ? rows.filter(x=>(x.sector_group||"").trim()===narrow).slice(0,15)
  : rows.filter(x=>(x.industry_name||"").trim()===key).slice(0,15);
 const peers=(r.sector_peers&&r.sector_peers.length?r.sector_peers:fallback);
 const hot=(r.sector_hot_count??d.strong_count??0);
 const count=(d.count||peers.length||0);
 const detail=source==="官方產業代理"
  ? `官方產業代理｜${hot}/${count} 檔轉強｜共振分沿用原本代理算法（未改評分）`
  : `廣度 ${num((d.components||{}).breadth,1)}/3 · 強度 ${num((d.components||{}).strength,1)}/2 · 量能 ${num((d.components||{}).volume,1)}/2 · 領頭 ${num((d.components||{}).leaders,1)}/2 · 延續 ${num((d.components||{}).continuity,1)}/1`;
 const sourceTag=source==="官方產業代理"?"官方產業":"次產業";
 return `<details><summary>👥 ${key} 共振 ${num(r.sector_score,1)}/10｜${hot}/${count} 檔轉強｜${sourceTag}｜點我展開</summary><div class="helptext" style="margin:7px 2px">${detail}</div><div class="group">${peers.map(x=>{const p=rows.find(y=>String(y.code)===String(x.code))||x;return `<button class="g peerlink" data-code="${p.code}"><span>${p.code} ${p.name}<small> ${signed(p.day_change,1)}</small></span><span>${p.score===null||p.score===undefined?"—":num(p.score,0)}｜${p.category||"觀察"}</span></button>`}).join("")}</div></details>`;
}

function partsHTML'''
    s2, n = pattern.subn(replacement, s, count=1)
    if n != 1:
        raise SystemExit("v1.5.10 patch could not replace groupHTML")
    s = s2

    old_help = '<b>族群共振原始10：</b>廣度3＋強度2＋量能2＋領頭股2＋延續性1；盤中換算為20分、盤後換算為15分。強勢股成交金額占比也納入強度；點開族群即可點選共振個股。<br>'
    new_help = '<b>族群共振原始10：</b>廣度3＋強度2＋量能2＋領頭股2＋延續性1；盤中換算為20分、盤後換算為15分。強勢股成交金額占比也納入強度；點開族群即可點選共振個股。若個股沒有自訂窄族群，會自動改用官方產業代理展開同產業股票；這只補成分股清單，不改原本代理分數。<br>'
    if "會自動改用官方產業代理展開同產業股票" not in s:
        s = must_replace(s, old_help, new_help, "sector help")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v1510", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_build_data()
    patch_index()
    patch_sw()
    print("v1.5.10 sector resonance drilldown patch applied")
