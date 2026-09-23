#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.8 — 盤後族群法人資金流展開／收合。

只處理使用者第 3 點：
- 盤後族群法人資金流預設收合，保留精簡摘要。
- 按鈕可展開／收合完整明細，狀態寫入 localStorage。
- 不改任何盤中／盤後分數、籌碼公式或法人資料計算。
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
        raise SystemExit(f"v1.5.8 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    s = re.sub(
        r"Free Edition v1\.5\.\d+｜[^<]*",
        "Free Edition v1.5.8｜盤中族群可展開＋盤後法人族群流向可收合＋振幅效率",
        s,
        count=1,
    )

    # Add compact preview + toggle styles once.
    if ".rotationtoggle{" not in s:
        css_marker = ".flowtag.flat{color:#ffd477;border:1px solid #5a4820;background:#2c2513}"
        css_add = css_marker + ".rotationtoggle{border:1px solid #36506f;background:#17304a;color:#cde6ff;border-radius:10px;padding:7px 10px;font-size:11px;font-weight:900;cursor:pointer;white-space:nowrap}.rotationtoggle:active{transform:scale(.98)}.closeflowpreview{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.closeflowpreviewcol{background:#0e131a;border:1px solid #252d39;border-radius:11px;padding:8px}.closeflowpreviewhead{font-size:11px;font-weight:900;margin-bottom:5px}.closeflowpreviewitem{display:flex;justify-content:space-between;gap:8px;font-size:10px;padding:3px 0;color:#cbd3df}.closeflowpreviewitem span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.closeflowsummary{font-size:10px;color:var(--muted);margin-top:7px}@media(max-width:620px){.closeflowpreview{grid-template-columns:1fr}}"
        s = must_replace(s, css_marker, css_add, "close flow collapse styles")

    # Add UI state. Default collapsed; remember user's last choice.
    state_marker = 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[];'
    if "dogsonSectorFundsOpen" not in s:
        state_new = state_marker + '\nlet sectorFundsOpen=localStorage.getItem("dogsonSectorFundsOpen")==="1";'
        s = must_replace(s, state_marker, state_new, "collapse state")

    # Replace only the v1.5.7 close-sector renderer. Leave intraday rotation untouched.
    start = s.find("function closeSectorFundsHTML(){")
    end = s.find("\n\nfunction rotationHTML(){", start)
    if start < 0 or end < 0:
        raise SystemExit("v1.5.8 patch missing marker: close sector renderer")

    renderer = r'''function toggleCloseSectorFunds(){
 sectorFundsOpen=!sectorFundsOpen;
 localStorage.setItem("dogsonSectorFundsOpen",sectorFundsOpen?"1":"0");
 const box=document.getElementById("rotationbox");
 if(box)box.innerHTML=rotationHTML();
}

function closeSectorFundsHTML(){
 const arr=sectorFunds||[];
 const title="🏦 盤後族群法人資金流";
 const sub="外資＋投信官方淨買賣股數彙總（張），未含自營商；這是盤後觀察欄位，不額外增加個股100分";
 if(!arr.length)return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div></div><div class="rotationleaders">目前法人歷史資料不足，完成盤後籌碼更新後會顯示。</div></div>`;

 const allBuys=arr.filter(x=>(x.today_lots||0)>0).sort((a,b)=>(b.net5_lots??b.today_lots??0)-(a.net5_lots??a.today_lots??0));
 const allSells=arr.filter(x=>(x.today_lots||0)<0).sort((a,b)=>(a.net5_lots??a.today_lots??0)-(b.net5_lots??b.today_lots??0));
 const buys=allBuys.slice(0,8),sells=allSells.slice(0,8);
 const period=(v,need,n)=>v===null||v===undefined?`累積中 ${Math.min(n||0,need)}/${need}日`:signed(v,0,"張");
 const mini=x=>`<div class="closeflowpreviewitem"><span>${x.sector}</span><b>${signed(x.today_lots,0,"張")}</b></div>`;
 const one=x=>{const buy=(x.today_lots||0)>0,sell=(x.today_lots||0)<0;const tag=buy?"buy":sell?"sell":"flat";return `<div class="closeflowcard"><div class="closeflowname">${x.sector}</div><div class="closeflowgrid"><div class="closeflowitem"><span>當日法人淨買超</span><b>${signed(x.today_lots,0,"張")}</b></div><div class="closeflowitem"><span>近 5 日法人淨買超</span><b>${period(x.net5_lots,5,x.history_days)}</b></div><div class="closeflowitem"><span>近 20 日法人淨買超</span><b>${period(x.net20_lots,20,x.history_days)}</b></div><div class="closeflowitem"><span>近 5 日漲跌</span><b>${signed(x.ret5_pct,2)}</b></div></div><div class="flowtext">資金流向｜${x.flow_text||"—"}</div><span class="flowtag ${tag}">${x.action||"觀察"}</span></div>`};

 const preview=`<div class="closeflowpreview"><div class="closeflowpreviewcol"><div class="closeflowpreviewhead">🔴 流入前 3</div>${allBuys.length?allBuys.slice(0,3).map(mini).join(""):`<div class="sub">目前無明顯流入</div>`}</div><div class="closeflowpreviewcol"><div class="closeflowpreviewhead">🟢 流出前 3</div>${allSells.length?allSells.slice(0,3).map(mini).join(""):`<div class="sub">目前無明顯流出</div>`}</div></div><div class="closeflowsummary">今日流入 ${allBuys.length} 個族群｜流出 ${allSells.length} 個族群｜完整明細各顯示前 8 名</div>`;
 const detail=sectorFundsOpen?`<div class="rotationcols"><div><div class="rotationhead">🔴 法人流入／加碼</div>${buys.length?buys.map(one).join(""):`<div class="sub">目前沒有明顯法人流入族群</div>`}</div><div><div class="rotationhead">🟢 法人流出／減碼</div>${sells.length?sells.map(one).join(""):`<div class="sub">目前沒有明顯法人流出族群</div>`}</div></div>`:"";
 const label=sectorFundsOpen?"收合族群明細":"展開完整族群";
 const arrow=sectorFundsOpen?"▲":"▼";
 return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div><button class="rotationtoggle" type="button" aria-expanded="${sectorFundsOpen}" onclick="toggleCloseSectorFunds()">${arrow} ${label}</button></div>${preview}${detail}</div>`;
}'''
    s = s[:start] + renderer + s[end:]

    # Explain the new interaction without altering scoring documentation.
    old_help = "單位用張，不用目前股價回推歷史億元；此欄不新增個股分數。<br>"
    new_help = "單位用張，不用目前股價回推歷史億元；此欄不新增個股分數。預設先收合成流入／流出前三名摘要，按「展開完整族群」才顯示完整明細，收合狀態會記住。<br>"
    if "預設先收合成流入／流出前三名摘要" not in s:
        s = must_replace(s, old_help, new_help, "collapse help")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v158", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_index()
    patch_sw()
    print("v1.5.8 close sector flow collapse patch applied")
