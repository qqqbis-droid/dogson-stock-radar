#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.23 — Step 4：盤中進場雷達／三燈。

新增：
- 🟢 可試單（波段）／🟡 等確認／🔴 先不進
- 三燈只做決策層，不建立新分數、不改盤中100分
- 大盤環境維持15分獨立，只做進場門檻提示，不併入個股分
- 20T/60T、Stage Engine、籌碼、5分鐘變化雷達全部保留原架構
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def must(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f"v1.5.23 missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    s = must(
        s,
        "Free Edition v1.5.22｜5分鐘變化雷達＋庫存模式",
        "Free Edition v1.5.23｜庫存模式＋盤中進場三燈",
        "version header",
    )

    css = r'''
/* v1.5.23 intraday entry radar */
.entrysummary{background:linear-gradient(180deg,#171d27,#10161e);border:1px solid #344156;border-radius:16px;padding:11px 12px;margin:10px 0}.entrysummarytop{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}.entrysummarytitle{font-size:16px;font-weight:900}.entrysummarysub{font-size:10px;color:var(--muted);margin-top:3px;line-height:1.5}.entrycounts{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:9px}.entrycount{background:#0e131a;border:1px solid #293442;border-radius:10px;padding:8px;text-align:center}.entrycountv{font-size:18px;font-weight:900}.entrycountl{font-size:9px;color:var(--muted);margin-top:2px}
.entrybox{margin-top:10px;border:1px solid #334052;background:linear-gradient(180deg,#111821,#0d131b);border-radius:13px;padding:10px}.entrytop{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.entrytitle{font-size:11px;color:#9ba5b6;font-weight:850}.entrylight{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:6px 9px;font-size:12px;font-weight:900;white-space:nowrap}.entrylight.green{background:#153323;border:1px solid #2b6041;color:#a6efbf}.entrylight.yellow{background:#3a2e12;border:1px solid #69551e;color:#ffd77b}.entrylight.red{background:#3d171d;border:1px solid #6b2b36;color:#ffacb8}.entryheadline{font-size:13px;font-weight:900;margin-top:7px}.entrymeta{display:flex;gap:7px;flex-wrap:wrap;margin-top:7px}.entrymeta span{font-size:9px;color:#aeb8c8;background:#151d28;border:1px solid #293442;border-radius:999px;padding:4px 7px}.entrywhy{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}.entrywhy span{font-size:10px;line-height:1.35;padding:5px 7px;border-radius:8px;background:#17231d;border:1px solid #274532;color:#a9e8bf}.entrywhy span.wait{background:#2a2415;border-color:#51431e;color:#ffd477}.entrywhy span.block{background:#28191c;border-color:#4f2931;color:#ffb2be}.entrynote{font-size:9px;color:var(--muted);line-height:1.5;margin-top:8px}
@media(max-width:520px){.entrycounts{grid-template-columns:repeat(3,minmax(0,1fr))}.entrycountv{font-size:16px}}
'''
    if ".entrysummary{" not in s:
        s = must(s, "</style>", css + "\n</style>", "entry radar css")

    old = '    <div class="guide-title">⑮ 第一次使用，照這個順序最快</div>'
    new = '''    <div class="guide-title">⑮ 🚦 盤中進場三燈：回答「現在要不要動手」</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">🟢 可試單（波段）</span>：個股盤中動能、5分K結構、量價、相對強弱、族群與追價風險同時通過，且沒有過熱／結構失效；大盤若進入防守，綠燈會降為黃燈。</div>
      <div class="guide-line"><span class="guide-key">🟡 等確認／等回踩</span>：方向沒有壞，但仍缺一到數個條件，例如尚未站穩 VWAP、量價不足、相對強弱不足、位置太靠近當日高檔，或大盤環境偏防守。</div>
      <div class="guide-line"><span class="guide-key">🔴 先不進</span>：結構失效、過熱不追，或出現明顯追價風險。紅燈不是看空，而是「這個位置先不要追」。</div>
      <div class="guide-tip">三燈不是另一套分數：盤中100分原公式完全不變；大盤15分保持獨立；籌碼仍只當背景。🟢 也不是自動買進訊號，只代表目前條件允許小量試單。</div>
    </div>
+
+    <div class="guide-title">⑯ 第一次使用，照這個順序最快</div>'''.replace("\n+", "\n")
    s = must(s, old, new, "entry radar help")

    s = must(
        s,
        '<div id="changebox"></div>\n<div id="liveStatus"',
        '<div id="changebox"></div>\n<div id="entrySummary"></div>\n<div id="liveStatus"',
        "entry summary container",
    )

    functions = r'''
function entryDecision(r,mkt=market){
 const c=r?.intraday_components||{};
 const stage=stageKey(r?.category);
 const score=+(r?.intraday_score??r?.score??0);
 const ps=+(c.price_structure??0),flow=+(c.flow_volume??0),rel=+(c.relative_strength??0),sec=+(c.sector??0),liq=+(c.liquidity_risk??0);
 const vwap=+(r?.vwap_dist??0),day=+(r?.day_change??0),pos=+(r?.range_position_pct??50),pace=+(r?.pace??0);
 const marketMode=String(mkt?.market_mode||"—"),marketScore=+(mkt?.market_score??0);
 const good=[],wait=[],block=[];

 // Hard gates：沿用既有過熱/失效概念，不重算100分。
 if(stage==="結構失效")block.push("生命週期：結構失效");
 if(stage==="過熱不追")block.push("生命週期：過熱不追");
 if(day>=8.5)block.push(`當日已漲 ${num(day,1)}%，追價風險高`);
 if(vwap>4.5)block.push(`距 VWAP +${num(vwap,1)}%，延伸過遠`);
 if(score<42)block.push(`盤中動能僅 ${num(score,0)}/100`);
 if(ps<7&&score<55)block.push(`5分K價格結構僅 ${num(ps,0)}/30`);

 if(block.length){
  return {key:"red",icon:"🔴",label:"先不進",headline:"先避開追價／弱結構",good,wait,block,marketMode,marketScore,score};
 }

 // Green checklist：不是加權，只檢查既有構成是否同步到位。
 if(score>=70)good.push(`盤中動能 ${num(score,0)}/100`);else wait.push(`動能 ${num(score,0)}/100，等 ≥70`);
 if(ps>=20)good.push(`5分K結構 ${num(ps,0)}/30`);else wait.push(`價格結構 ${num(ps,0)}/30，等更完整`);
 if(flow>=14)good.push(`量價/動能 ${num(flow,0)}/25`);else wait.push(`量價 ${num(flow,0)}/25，尚未共振`);
 if(rel>=8)good.push(`相對強弱 ${num(rel,0)}/15`);else wait.push(`相對強弱 ${num(rel,0)}/15，仍偏普通`);
 if(sec>=8)good.push(`族群 ${num(sec,0)}/20`);else wait.push(`族群 ${num(sec,0)}/20，缺共振`);
 if(liq>=6)good.push(`流動性/風險 ${num(liq,0)}/10`);else wait.push(`流動性/追價風險 ${num(liq,0)}/10`);
 if(vwap>=-.5&&vwap<=2.5)good.push(`距 VWAP ${signed(vwap,1)} 合理`);else if(vwap<-.5)wait.push(`仍在 VWAP 下 ${signed(vwap,1)}`);else wait.push(`距 VWAP ${signed(vwap,1)}，等回踩`);
 if(pos>=45&&pos<=90)good.push(`區間位置 ${num(pos,0)}%`);else if(pos<45)wait.push(`區間位置 ${num(pos,0)}%，等轉強`);else wait.push(`區間位置 ${num(pos,0)}%，靠近高檔`);
 if(pace>5)wait.push(`量速 ${num(pace,1)}x，先防爆量追價`);
 if(stage==="轉弱警戒")wait.push("Stage 仍在轉弱警戒，需等5分K重新轉強");

 const marketWeak=marketMode==="防守"||(Number.isFinite(marketScore)&&marketScore>0&&marketScore<6);
 const coreGreen=score>=70&&ps>=20&&flow>=14&&rel>=8&&sec>=8&&liq>=6&&vwap>=-.5&&vwap<=2.5&&pos>=45&&pos<=90&&stage!=="轉弱警戒";
 if(coreGreen&&!marketWeak){
  return {key:"green",icon:"🟢",label:"可試單（波段）",headline:"條件同步，可用小部位試單",good,wait:wait.slice(0,2),block,marketMode,marketScore,score};
 }
 if(marketWeak)wait.unshift(`大盤 ${marketMode}${marketScore?` ${num(marketScore,1)}/15`:""}，環境門檻偏保守`);
 return {key:"yellow",icon:"🟡",label:"等確認",headline:"方向未壞，等缺口補齊或回踩",good,wait:block.length?block:wait,block,marketMode,marketScore,score};
}
function entryDecisionHTML(r){
 if(mode!=="intraday")return "";
 const d=entryDecision(r,market);
 const positives=(d.good||[]).slice(0,4).map(x=>`<span>${x}</span>`).join("");
 const waits=(d.wait||[]).slice(0,4).map(x=>`<span class="wait">${x}</span>`).join("");
 const blocks=(d.block||[]).slice(0,4).map(x=>`<span class="block">${x}</span>`).join("");
 return `<div class="entrybox"><div class="entrytop"><div><div class="entrytitle">🚦 Step 4｜盤中進場雷達</div><div class="entryheadline">${d.headline}</div></div><span class="entrylight ${d.key}">${d.icon} ${d.label}</span></div><div class="entrymeta"><span>個股動能 ${num(d.score,0)}/100</span><span>大盤 ${d.marketMode}${d.marketScore?` ${num(d.marketScore,1)}/15`:""} · 獨立</span><span>20T/60T 不另加權</span></div><div class="entrywhy">${positives}${waits}${blocks}</div><div class="entrynote">三燈只做進場時機判斷，不改原本100分；🟢 代表可小量試單，不等於自動買進。</div></div>`;
}
function entrySummaryHTML(){
 if(mode!=="intraday")return "";
 let green=0,yellow=0,red=0;
 (intraRows||[]).forEach(r=>{const k=entryDecision(r,intraMarket).key;if(k==="green")green++;else if(k==="red")red++;else yellow++});
 return `<div class="entrysummary"><div class="entrysummarytop"><div><div class="entrysummarytitle">🚦 盤中進場三燈</div><div class="entrysummarysub">Step 4｜波段優先。三燈是既有訊號的決策層，不增加新分數；大盤15分獨立。</div></div></div><div class="entrycounts"><div class="entrycount"><div class="entrycountv">🟢 ${green}</div><div class="entrycountl">可試單</div></div><div class="entrycount"><div class="entrycountv">🟡 ${yellow}</div><div class="entrycountl">等確認</div></div><div class="entrycount"><div class="entrycountv">🔴 ${red}</div><div class="entrycountl">先不進</div></div></div></div>`;
}

'''
    if "function entryDecision(r,mkt=market)" not in s:
        s = must(s, "function srHTML(r){", functions + "function srHTML(r){", "entry radar functions")

    s = must(
        s,
        '$("portfolioSummary").innerHTML=portfolioSummaryHTML();',
        '$("portfolioSummary").innerHTML=portfolioSummaryHTML();\n $("entrySummary").innerHTML=entrySummaryHTML();',
        "entry summary render",
    )

    s = must(
        s,
        '  ${stageExplainHTML(r)}\n  ${portfolioHTML(r)}',
        '  ${stageExplainHTML(r)}\n  ${entryDecisionHTML(r)}\n  ${portfolioHTML(r)}',
        "entry box in cards",
    )

    s = s.replace('./sw.js?v=1522', './sw.js?v=1523')
    s = s.replace('dogsonSwReloaded1522', 'dogsonSwReloaded1523')

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    if "dogson-free-v1523" not in s:
        s = must(s, "dogson-free-v1522", "dogson-free-v1523", "service worker cache")
    write(p, s)


def patch_status():
    p = "docs/data/status.json"
    d = json.loads(read(p))
    d["version"] = "1.5.23-free"
    d["entry_radar_version"] = "1.0"
    write(p, json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    patch_index()
    patch_sw()
    patch_status()
    print("v1.5.23 intraday entry radar patch applied")
