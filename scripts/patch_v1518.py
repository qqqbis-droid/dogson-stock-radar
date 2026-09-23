#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.18 — Explainable Stage Engine UI.

只改前端呈現，不改 Stage Engine 2.0 判斷與任何 100 分公式：
- 個股卡片直接顯示「生命週期 + 白話原因 + 支持證據 / 風險證據」。
- 族群成分股 mini-card 也顯示簡化版生命週期原因。
- stage_signals / stage_risks 既有資料直接使用，不新增評分權重。
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
        raise SystemExit(f"v1.5.18 missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    # Version headline.
    s, n = re.subn(
        r"Free Edition v1\.5\.17｜[^<]*",
        "Free Edition v1.5.18｜生命週期可解釋化＋Stage Engine 2.0",
        s,
        count=1,
    )
    if n != 1:
        raise SystemExit("v1.5.18 could not update version headline")

    # Stage explanation visual block.
    css_old = '.reasons{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}.reason{background:#202734;border-radius:8px;padding:5px 7px;font-size:11px;color:#d7deea}.warn{color:#ff9baa}'
    css_new = css_old + '.stagebox{margin-top:10px;background:#0e141c;border:1px solid #2b3544;border-radius:13px;padding:10px 11px}.stagetop{display:flex;align-items:center;justify-content:space-between;gap:8px}.stagetitle{font-size:11px;color:#9ba5b6;font-weight:850}.stagereason{font-size:12px;line-height:1.55;color:#edf2fa;margin-top:7px}.stagechips{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}.stagechip{font-size:10px;line-height:1.35;padding:5px 7px;border-radius:8px;background:#17231d;border:1px solid #274532;color:#a9e8bf}.stagechip.risk{background:#25191c;border-color:#4a2930;color:#ffb2be}.stagehint{font-size:10px;color:#7f8b9d;margin-top:7px}.peerpeek .stagebox{margin-top:10px}.peerpeek .stagereason{font-size:11px}.peerpeek .stagechip{font-size:9px;padding:4px 6px}'
    s = must_replace(s, css_old, css_new, "stage explain css")

    # Reusable stage explanation renderer before peer mini-card.
    marker = 'function showPeerPeek(code){'
    helper = '''function stageExplainHTML(r,compact=false){
 const category=r.category||"觀察";
 const reason=(r.stage_reason||"目前沒有足夠資料形成明確生命週期判讀").trim();
 const signals=[...(r.stage_signals||[])].filter(Boolean).slice(0,5);
 const risks=[...(r.stage_risks||[])].filter(Boolean).slice(0,5);
 const signalHTML=signals.map(x=>`<span class="stagechip">✓ ${x}</span>`).join("");
 const riskHTML=risks.map(x=>`<span class="stagechip risk">⚠ ${x}</span>`).join("");
 const evidence=(signalHTML||riskHTML)?`<div class="stagechips">${signalHTML}${riskHTML}</div>`:`<div class="stagehint">目前沒有額外的關鍵證據需要提示。</div>`;
 return `<div class="stagebox"><div class="stagetop"><span class="stagetitle">${compact?"生命週期":"🧭 生命週期判讀"}</span><span class="cat ${cls(category)}">${category}</span></div><div class="stagereason">${reason}</div>${evidence}</div>`;
}

'''
    if marker not in s:
        raise SystemExit("v1.5.18 cannot find showPeerPeek")
    s = s.replace(marker, helper + marker, 1)

    # Mini-card: add explainable lifecycle block below metrics.
    old_peer = 'back.innerHTML=`<div class="peerpeek"><div class="peerpeektop"><div><div class="peerpeekname">${r.name} <span class="code">${r.code}</span></div><div class="sub">${r.sector_group||r.industry_name||r.industry||"未分類"}｜${signed(r.day_change,1)}</div></div><span class="cat ${cls(r.category)}">${r.category||"觀察"}</span></div><div class="peerpeekgrid">${items.map(x=>`<div class="peerpeekitem"><div class="peerpeekv">${x[1]}</div><div class="peerpeekl">${x[0]}</div></div>`).join("")}</div><div class="peerpeekactions"><button class="peerpeekbtn" data-peer-open="${r.code}">查看完整個股</button><button class="peerpeekbtn secondary" data-peer-close="1">關閉</button></div></div>`;'
    new_peer = 'back.innerHTML=`<div class="peerpeek"><div class="peerpeektop"><div><div class="peerpeekname">${r.name} <span class="code">${r.code}</span></div><div class="sub">${r.sector_group||r.industry_name||r.industry||"未分類"}｜${signed(r.day_change,1)}</div></div><span class="cat ${cls(r.category)}">${r.category||"觀察"}</span></div><div class="peerpeekgrid">${items.map(x=>`<div class="peerpeekitem"><div class="peerpeekv">${x[1]}</div><div class="peerpeekl">${x[0]}</div></div>`).join("")}</div>${stageExplainHTML(r,true)}<div class="peerpeekactions"><button class="peerpeekbtn" data-peer-open="${r.code}">查看完整個股</button><button class="peerpeekbtn secondary" data-peer-close="1">關閉</button></div></div>`;'
    s = must_replace(s, old_peer, new_peer, "peer stage explanation")

    # Full stock card: place stage explanation immediately under the header.
    old_parts = '''  ${partsHTML(r)}
  <div class="metrics">'''
    new_parts = '''  ${stageExplainHTML(r)}
  ${partsHTML(r)}
  <div class="metrics">'''
    s = must_replace(s, old_parts, new_parts, "full card stage explanation")

    # Remove the old one-line stage reason pill to avoid duplicate explanation.
    old_reasons = '${r.stage_reason?`<span class="reason">階段：${r.stage_reason}</span>`:""}${(r.reasons||[]).map(x=>`<span class="reason">${x}</span>`).join("")}${(r.overheat_reasons||[]).map(x=>`<span class="reason warn">⚠ ${x}</span>`).join("")}'
    new_reasons = '${(r.reasons||[]).map(x=>`<span class="reason">${x}</span>`).join("")}${(r.overheat_reasons||[]).filter(x=>!(r.stage_risks||[]).includes(x)).map(x=>`<span class="reason warn">⚠ ${x}</span>`).join("")}'
    s = must_replace(s, old_reasons, new_reasons, "dedupe old stage reason")

    # Update service worker registration so Safari gets the UI immediately.
    s = must_replace(s, './sw.js?v=1517b', './sw.js?v=1518', "sw registration")
    s = must_replace(s, 'dogsonSwReloaded1517b', 'dogsonSwReloaded1518', "sw reload key")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s, n = re.subn(r"dogson-free-v1517b", "dogson-free-v1518", s, count=1)
    if n != 1:
        raise SystemExit("v1.5.18 could not bump service worker cache")
    write(p, s)


if __name__ == "__main__":
    patch_index()
    patch_sw()
    print("v1.5.18 explainable lifecycle UI applied")
