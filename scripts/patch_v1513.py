#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.13 — 盤後法人族群卡緊湊不換行 + 成分股可展開並點小卡。

前提：v1.5.12 已提供估算金額欄位。
只改前端呈現/互動，不改金額算法，也不改任何評分公式。
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
        raise SystemExit(f"v1.5.13 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)
    s = re.sub(
        r"Free Edition v1\.5\.\d+｜[^<]*",
        "Free Edition v1.5.13｜盤後法人金額力度＋族群成分股小卡＋盤中輪動可收合",
        s,
        count=1,
    )

    # Compact/no-wrap sector-flow presentation. Amount stays primary; lots are a separate compact row.
    css_marker = '.closeflowsummary{font-size:10px;color:var(--muted);margin-top:7px}'
    css_add = css_marker + '.closeflowcard{min-width:0}.closeflowname{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.closeflowgrid.compact{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.closeflowmetric{min-width:0;background:#111823;border:1px solid #29313e;border-radius:9px;padding:7px 8px}.closeflowmetric .cflabel{font-size:9px;color:var(--muted);white-space:nowrap}.closeflowmetric .cfvalue{font-size:12px;font-weight:900;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-variant-numeric:tabular-nums}.closeflowlots{display:flex;gap:8px;overflow-x:auto;white-space:nowrap;font-size:9px;color:var(--muted);padding:6px 1px 2px;scrollbar-width:none}.closeflowlots::-webkit-scrollbar{display:none}.closeflowmembers{margin-top:8px;padding-top:8px}.closeflowmembers>summary{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#b9ddff;font-weight:850}.closeflowmembergrid{display:grid;gap:6px;margin-top:7px}'
    if '.closeflowgrid.compact' not in s:
        s = must_replace(s, css_marker, css_add, "compact close flow css")

    # Keep mobile in two compact columns; deliberate rows inside each metric never wrap.
    mobile_old = '@media(max-width:620px){.closeflowpreview{grid-template-columns:1fr}}'
    mobile_new = '@media(max-width:620px){.closeflowpreview{grid-template-columns:1fr}.closeflowgrid.compact{grid-template-columns:repeat(2,minmax(0,1fr))}.closeflowmetric{padding:7px 6px}.closeflowmetric .cfvalue{font-size:11px}}'
    if '.closeflowmetric .cfvalue{font-size:11px}' not in s:
        s = must_replace(s, mobile_old, mobile_new, "mobile compact flow")

    pattern = re.compile(r'function closeSectorFundsHTML\(\)\{.*?\n\}\n\nfunction rotationHTML', re.S)
    replacement = r'''function closeSectorKey(r){
 const g=(r.sector_group||"").trim();
 const ind=(r.industry_name||"").trim();
 return g || (ind&&ind!=="未分類"?ind:"");
}
function closeSectorMembers(sector){
 return closeRows
  .filter(r=>closeSectorKey(r)===sector)
  .sort((a,b)=>(+(b.swing_quality_score??b.score)||0)- (+(a.swing_quality_score??a.score)||0) || (+(b.day_change)||0)- (+(a.day_change)||0))
  .slice(0,30);
}
function closeSectorFundsHTML(){
 const arr=sectorFunds||[];
 const title="🏦 盤後族群法人資金流";
 const sub="外資＋投信官方淨買賣股數 × 各交易日收盤價估算；金額看力度、張數看方向，未含自營商；不額外增加個股100分";
 if(!arr.length)return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div></div><div class="rotationleaders">目前法人歷史資料不足，完成盤後籌碼更新後會顯示。</div></div>`;

 const strength=x=>x.net5_amount_100m??x.today_amount_100m??0;
 const allBuys=arr.filter(x=>(x.today_amount_100m??0)>0).sort((a,b)=>strength(b)-strength(a));
 const allSells=arr.filter(x=>(x.today_amount_100m??0)<0).sort((a,b)=>strength(a)-strength(b));
 const buys=allBuys.slice(0,8),sells=allSells.slice(0,8);
 const periodMoney=(v,need,n)=>v===null||v===undefined?`累積 ${Math.min(n||0,need)}/${need}日`:flowMoney(v);
 const lotsText=(v,need,n)=>v===null||v===undefined?`累積${Math.min(n||0,need)}/${need}日`:signed(v,0,"張");
 const mini=x=>`<div class="closeflowpreviewitem"><span>${x.sector}</span><b>${flowMoney(x.today_amount_100m)}</b></div>`;
 const metric=(label,value)=>`<div class="closeflowmetric"><div class="cflabel">${label}</div><div class="cfvalue">${value}</div></div>`;
 const one=x=>{
   const buy=(x.today_amount_100m??x.today_lots??0)>0,sell=(x.today_amount_100m??x.today_lots??0)<0;
   const tag=buy?"buy":sell?"sell":"flat";
   const members=closeSectorMembers(x.sector);
   const memberHTML=members.length?members.map(p=>`<button class="rotationmember peerlink" data-code="${p.code}"><span>${p.code} ${p.name}<small> ${signed(p.day_change,1)}</small></span><span class="rmscore">${p.score_reliable===false?"待補":num(p.swing_quality_score??p.score,0)+"/100"} · ${p.category||"觀察"}</span></button>`).join(""):`<div class="sub">目前雷達沒有可用成分股</div>`;
   return `<div class="closeflowcard"><div class="closeflowname">${x.sector}</div><div class="closeflowgrid compact">${metric("當日估算",flowMoney(x.today_amount_100m))}${metric("5日估算",periodMoney(x.net5_amount_100m,5,x.amount_history_days))}${metric("20日估算",periodMoney(x.net20_amount_100m,20,x.amount_history_days))}${metric("5日漲跌",signed(x.ret5_pct,2))}</div><div class="closeflowlots"><span>張數｜今日 ${lotsText(x.today_lots,1,x.history_days)}</span><span>5日 ${lotsText(x.net5_lots,5,x.history_days)}</span><span>20日 ${lotsText(x.net20_lots,20,x.history_days)}</span></div><div class="flowtext">${x.flow_text||"資金方向中性"}</div><div class="closeflowsummary">金額覆蓋 ${num(x.amount_coverage_pct,0)}%｜估算值</div><span class="flowtag ${tag}">${x.action||"觀察"}</span><details class="closeflowmembers"><summary>👥 查看成分股 ${members.length} 檔</summary><div class="closeflowmembergrid">${memberHTML}</div></details></div>`;
 };

 const preview=`<div class="closeflowpreview"><div class="closeflowpreviewcol"><div class="closeflowpreviewhead">🔴 流入前 3</div>${allBuys.length?allBuys.slice(0,3).map(mini).join(""):`<div class="sub">目前無明顯流入</div>`}</div><div class="closeflowpreviewcol"><div class="closeflowpreviewhead">🟢 流出前 3</div>${allSells.length?allSells.slice(0,3).map(mini).join(""):`<div class="sub">目前無明顯流出</div>`}</div></div><div class="closeflowsummary">依估算金額力度排序｜今日流入 ${allBuys.length} 個族群｜流出 ${allSells.length} 個族群</div>`;
 const detail=sectorFundsOpen?`<div class="rotationcols"><div><div class="rotationhead">🔴 法人流入／加碼</div>${buys.length?buys.map(one).join(""):`<div class="sub">目前沒有明顯法人流入族群</div>`}</div><div><div class="rotationhead">🟢 法人流出／減碼</div>${sells.length?sells.map(one).join(""):`<div class="sub">目前沒有明顯法人流出族群</div>`}</div></div>`:"";
 const label=sectorFundsOpen?"收合族群明細":"展開完整族群";
 const arrow=sectorFundsOpen?"▲":"▼";
 return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div><button class="rotationtoggle" type="button" aria-expanded="${sectorFundsOpen}" onclick="toggleCloseSectorFunds()">${arrow} ${label}</button></div>${preview}${detail}</div>`;
}

function rotationHTML'''
    s2, n = pattern.subn(replacement, s, count=1)
    if n != 1:
        raise SystemExit("v1.5.13 could not replace closeSectorFundsHTML")
    s = s2

    help_old = '金額用來比較資金力度、張數仍保留看持股方向；這不是官方逐股實際成交金額，因此畫面明確標示「估算」。此欄不新增個股分數。<br>'
    help_new = '金額用來比較資金力度、張數仍保留看持股方向；這不是官方逐股實際成交金額，因此畫面明確標示「估算」。族群卡採固定單行數字避免換行，並可展開目前雷達中的同族群成分股，點個股直接開啟同一套小卡。此欄不新增個股分數。<br>'
    if '族群卡採固定單行數字避免換行' not in s:
        s = must_replace(s, help_old, help_new, "member drilldown help")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v1513", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_index()
    patch_sw()
    print("v1.5.13 compact close flow + sector member drilldown patch applied")
