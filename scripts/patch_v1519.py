#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.19 — 生命週期篩選修正。

只修前端生命週期篩選與顯示名稱：
- 篩選列恢復完整 8 階段名稱，補回「觀察」。
- 用 stageKey() 標準化完整名／縮寫／emoji／舊格式，避免精確字串比對失效。
- 修正 v1.5.18 Service Worker sessionStorage 版本鍵不一致。
不改 Stage Engine 判斷、100 分架構、盤中 Heat 或任何資料計算。
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
        raise SystemExit(f"v1.5.19 missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    # Header/version text only; keep the existing product description after the separator.
    s = re.sub(r"Free Edition v1\.5\.18", "Free Edition v1.5.19", s, count=1)

    old_filters = '''  <button class="filter on" data-f="all">全部</button><button class="filter" data-f="蓄勢待發">🌱 蓄勢</button><button class="filter" data-f="剛啟動">🔥 剛啟動</button><button class="filter" data-f="回踩承接">🟡 回踩</button><button class="filter" data-f="趨勢持有">🚂 趨勢</button><button class="filter" data-f="轉弱警戒">⚠️ 轉弱</button><button class="filter" data-f="結構失效">❌ 失效</button><button class="filter" data-f="過熱不追">🚫 過熱</button><button class="filter" id="watchOnly">⭐ 我的關注</button>'''
    new_filters = '''  <button class="filter on" data-f="all">全部</button><button class="filter" data-f="蓄勢待發">🌱 蓄勢待發</button><button class="filter" data-f="剛啟動">🔥 剛啟動</button><button class="filter" data-f="回踩承接">🟡 回踩承接</button><button class="filter" data-f="趨勢持有">🚂 趨勢持有</button><button class="filter" data-f="觀察">🔵 觀察</button><button class="filter" data-f="轉弱警戒">⚠️ 轉弱警戒</button><button class="filter" data-f="結構失效">❌ 結構失效</button><button class="filter" data-f="過熱不追">🚫 過熱不追</button><button class="filter" id="watchOnly">⭐ 我的關注</button>'''
    s = must_replace(s, old_filters, new_filters, "lifecycle filter buttons")

    stage_fn = r'''function stageKey(v){
 const raw=String(v||"").trim();
 if(!raw)return "觀察";
 const x=raw.replace(/[🌱🔥🟡🚂🔵⚠️❌🚫]/gu,"").replace(/\s+/g,"");
 if(x.includes("蓄勢"))return "蓄勢待發";
 if(x.includes("剛啟動")||x.includes("啟動"))return "剛啟動";
 if(x.includes("回踩"))return "回踩承接";
 if(x.includes("趨勢"))return "趨勢持有";
 if(x.includes("轉弱"))return "轉弱警戒";
 if(x.includes("失效"))return "結構失效";
 if(x.includes("過熱"))return "過熱不追";
 if(x.includes("觀察"))return "觀察";
 return x;
}

'''
    marker = "function render(){\n"
    if "function stageKey(v){" not in s:
        s = must_replace(s, marker, stage_fn + marker, "render insertion point")

    old_filter_logic = 'let rr=rows.filter(r=>(filter==="all"||r.category===filter)&&(!watchOnly||watched(r.code)));'
    new_filter_logic = 'let rr=rows.filter(r=>(filter==="all"||stageKey(r.category)===stageKey(filter))&&(!watchOnly||watched(r.code)));'
    s = must_replace(s, old_filter_logic, new_filter_logic, "canonical stage filter")

    # Make displayed category canonical as well, without touching the underlying data.
    s = s.replace('${r.category||"觀察"}', '${stageKey(r.category)||"觀察"}')
    s = s.replace('${r.category}</span>', '${stageKey(r.category)}</span>')

    # Safari/PWA update key: v1.5.18 getter/setter accidentally used different versions.
    s = must_replace(s, './sw.js?v=1518', './sw.js?v=1519', "SW registration version")
    s = s.replace('dogsonSwReloaded1518', 'dogsonSwReloaded1519')
    s = s.replace('dogsonSwReloaded1517b', 'dogsonSwReloaded1519')

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+[a-z]?", "dogson-free-v1519", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_index()
    patch_sw()
    print("v1.5.19 lifecycle filter repair applied")
