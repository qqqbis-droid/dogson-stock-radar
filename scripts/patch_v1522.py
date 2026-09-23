#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.22 — 庫存模式（前端本機資料）。

新增：
- 💼 我的庫存篩選
- 股數、平均成本、進場理由、持有理由、理由狀態、結構失效條件
- 即時計算成本、市值、未實現損益、報酬率
- localStorage only：不把使用者庫存寫回公開 GitHub repo

不改盤中/盤後 100 分、Stage Engine、變化雷達或任何後端評分。
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
        raise SystemExit(f"v1.5.22 missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    s = must(
        s,
        "Free Edition v1.5.21｜生命週期可解釋化＋Stage Engine 2.0",
        "Free Edition v1.5.22｜5分鐘變化雷達＋庫存模式",
        "version header",
    )

    # CSS
    css = r'''
/* v1.5.22 portfolio mode */
.portfolio-mini{border:1px solid #334256;background:#192231;color:#b9c9dd;border-radius:999px;padding:5px 8px;font-size:10px;font-weight:850;margin:7px 0 0 5px;cursor:pointer}.portfolio-mini.held{background:#2b2011;border-color:#5a4320;color:#ffd477}
.portfolio-summary{background:linear-gradient(180deg,#1b202b,#121821);border:1px solid #394559;border-radius:16px;padding:12px;margin:10px 0}.portfolio-summary-title{font-size:16px;font-weight:900}.portfolio-summary-sub{font-size:10px;color:var(--muted);margin-top:3px;line-height:1.45}.portfolio-summary-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-top:10px}.portfolio-summary-item{background:#0e131a;border:1px solid #29313e;border-radius:10px;padding:8px;min-width:0}.portfolio-summary-v{font-size:13px;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.portfolio-summary-l{font-size:9px;color:var(--muted);margin-top:3px}
.portfoliobox{margin-top:10px;background:linear-gradient(180deg,#181d26,#10151c);border:1px solid #3b4658;border-radius:13px;padding:11px}.portfolio-top{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}.portfolio-title{font-size:12px;font-weight:900}.portfolio-editbtn{border:1px solid #40526a;background:#172538;color:#cde6ff;border-radius:9px;padding:6px 8px;font-size:10px;font-weight:850;cursor:pointer}.portfolio-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin-top:9px}.portfolio-metric{background:#0e131a;border:1px solid #29313e;border-radius:9px;padding:7px;min-width:0}.portfolio-metric-v{font-size:12px;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.portfolio-metric-l{font-size:9px;color:var(--muted);margin-top:3px}.pnl.up{color:var(--red)}.pnl.down{color:var(--green)}
.portfolio-statusline{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:9px}.portfolio-status{display:inline-flex;border-radius:999px;padding:5px 8px;font-size:10px;font-weight:900}.portfolio-status.valid{background:#173527;color:#9ef0bd}.portfolio-status.weak{background:#40300f;color:#ffd477}.portfolio-status.invalid{background:#471820;color:#ff9cac}.portfolio-system{font-size:10px;color:var(--muted)}.portfolio-system.warn{color:#ffd477}.portfolio-system.bad{color:#ff9cac}
.portfolio-reasons{display:grid;gap:6px;margin-top:9px}.portfolio-reason{background:#101722;border:1px solid #263140;border-radius:9px;padding:8px;font-size:11px;line-height:1.5}.portfolio-reason b{display:block;font-size:9px;color:#9ba5b6;margin-bottom:3px}.portfolio-fallback{font-size:10px;color:#ffd477;margin-top:8px}
.portfolio-back{position:fixed;inset:0;background:rgba(0,0,0,.64);z-index:55;display:flex;align-items:flex-end;justify-content:center;padding:14px}.portfolio-modal{width:min(720px,100%);max-height:88vh;overflow:auto;background:#161c26;border:1px solid #3a4659;border-radius:18px;padding:14px;box-shadow:0 18px 50px rgba(0,0,0,.5)}.portfolio-modal-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.portfolio-modal-title{font-size:19px;font-weight:900}.portfolio-close{border:0;background:#242b38;color:#d4dae4;border-radius:10px;padding:8px 10px;font-weight:900}.portfolio-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:12px}.portfolio-field{display:grid;gap:5px}.portfolio-field.full{grid-column:1/-1}.portfolio-field label{font-size:10px;color:#a8b2c1;font-weight:800}.portfolio-input,.portfolio-textarea,.portfolio-select{width:100%;background:#0e131a;color:#fff;border:1px solid #303b4a;border-radius:10px;padding:10px;font-size:13px}.portfolio-textarea{min-height:72px;resize:vertical;line-height:1.45}.portfolio-actions{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:12px}.portfolio-save,.portfolio-remove,.portfolio-cancel{border-radius:11px;padding:10px;font-weight:900}.portfolio-save{border:1px solid #2e6647;background:#173527;color:#9ef0bd}.portfolio-remove{border:1px solid #62303a;background:#30181e;color:#ffb3bf}.portfolio-cancel{border:1px solid #3a4352;background:#242b38;color:#d4dae4}.portfolio-privacy{font-size:10px;color:var(--muted);line-height:1.55;margin-top:10px}
@media(max-width:620px){.portfolio-summary-grid,.portfolio-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.portfolio-form-grid{grid-template-columns:1fr}.portfolio-field.full{grid-column:auto}.portfolio-actions{grid-template-columns:1fr 1fr}.portfolio-cancel{grid-column:1/-1}}
'''
    if ".portfolio-summary{" not in s:
        s = must(s, "</style>", css + "\n</style>", "portfolio css")

    # Filter button.
    old = '<button class="filter" id="watchOnly">⭐ 我的關注</button>'
    new = old + '<button class="filter" id="portfolioOnly">💼 我的庫存</button>'
    s = must(s, old, new, "portfolio filter button")

    # Help section.
    old = '    <div class="guide-title">⑭ 第一次使用，照這個順序最快</div>'
    new = '''    <div class="guide-title">⑭ 💼 庫存模式：把「為什麼買」一起保存</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">我的庫存</span>：只顯示你手動登記的實際持股，與「我的關注」分開。</div>
      <div class="guide-line"><span class="guide-key">股數／平均成本</span>：用來即時計算目前市值、未實現損益與報酬率；正報酬依台股習慣顯示紅色、負報酬顯示綠色。</div>
      <div class="guide-line"><span class="guide-key">進場理由</span>：記錄當初為什麼買；<span class="guide-key">持有理由</span>：記錄現在為什麼還留著。</div>
      <div class="guide-line"><span class="guide-key">理由狀態</span>：由你手動標記 ✅仍成立／⚠️轉弱／❌消失。系統生命週期只提供證據，不會自動把你的核心理由改掉。</div>
      <div class="guide-line"><span class="guide-key">結構失效條件</span>：先寫好什麼情況代表原本交易邏輯不成立，避免盤中被單根急殺或情緒帶走。</div>
      <div class="guide-tip">庫存資料只存在目前瀏覽器的 localStorage，不會寫進公開 GitHub；換裝置／清除網站資料後不會自動同步。</div>
    </div>

    <div class="guide-title">⑮ 第一次使用，照這個順序最快</div>'''
    s = must(s, old, new, "portfolio help guide")

    # Summary container.
    old = '<div class="meta"><span id="modeText">盤中：5分K / VWAP / 量速</span><span id="updated">—</span></div>\n<div id="cards">'
    new = '<div class="meta"><span id="modeText">盤中：5分K / VWAP / 量速</span><span id="updated">—</span></div>\n<div id="portfolioSummary"></div>\n<div id="cards">'
    s = must(s, old, new, "portfolio summary container")

    # State.
    old = 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[],changeRadar={};'
    new = 'let mode="intraday",filter="all",watchOnly=false,portfolioOnly=false,portfolioData={},universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[],changeRadar={};'
    s = must(s, old, new, "portfolio state")

    # Portfolio helpers after watchlist helper.
    old = 'function toggleWatch(c){let w=watchlist();c=String(c);w=w.includes(c)?w.filter(x=>x!==c):[...w,c];saveWatch(w);render()}\nfunction num(v,d=1)'
    helpers = r'''function toggleWatch(c){let w=watchlist();c=String(c);w=w.includes(c)?w.filter(x=>x!==c):[...w,c];saveWatch(w);render()}
const PORTFOLIO_KEY="dogson-portfolio-v1";
function loadPortfolio(){try{const x=JSON.parse(localStorage.getItem(PORTFOLIO_KEY)||"{}");return x&&typeof x==="object"&&!Array.isArray(x)?x:{}}catch{return {}}}
function savePortfolioData(){localStorage.setItem(PORTFOLIO_KEY,JSON.stringify(portfolioData))}
function holding(c){return portfolioData[String(c)]||null}
function held(c){return !!holding(c)}
function escHTML(v){return String(v??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]))}
function reasonStatusText(v){return v==="weak"?"⚠️ 轉弱":v==="invalid"?"❌ 消失":"✅ 仍成立"}
function reasonStatusClass(v){return v==="weak"?"weak":v==="invalid"?"invalid":"valid"}
function portfolioMoney(v){if(v===null||v===undefined||Number.isNaN(+v))return "—";const n=+v,a=Math.abs(n),sign=n>0?"+":n<0?"-":"";if(a>=1e8)return sign+"$"+num(a/1e8,2)+"億";if(a>=1e4)return sign+"$"+num(a/1e4,1)+"萬";return sign+"$"+num(a,0)}
function currentHoldingRow(code){
 code=String(code);
 const primary=mode==="intraday"?intraRows:closeRows;
 const secondary=mode==="intraday"?closeRows:intraRows;
 const a=primary.find(x=>String(x.code)===code);if(a)return a;
 const b=secondary.find(x=>String(x.code)===code);if(b)return {...b,_portfolio_fallback:mode==="intraday"?"盤中行情暫缺，使用最近盤後資料":"盤後資料暫缺，使用最近盤中資料"};
 const u=universe.find(x=>String(x.code)===code);
 return u?{...u,code,name:u.name||code,category:"觀察",score_reliable:false,reasons:[],_portfolio_fallback:"目前沒有可用行情，先保留庫存紀錄"}:null;
}
function portfolioPnL(h,px){
 const shares=+(h?.shares||0),cost=+(h?.cost||0),price=+px;
 if(!(shares>0)||!(cost>0)||!(price>0))return {costValue:null,marketValue:null,pnl:null,pct:null};
 const costValue=shares*cost,marketValue=shares*price,pnl=marketValue-costValue;
 return {costValue,marketValue,pnl,pct:costValue>0?pnl/costValue*100:null};
}
function portfolioSummaryHTML(){
 if(!portfolioOnly)return "";
 const entries=Object.entries(portfolioData);
 if(!entries.length)return `<div class="portfolio-summary"><div class="portfolio-summary-title">💼 我的庫存</div><div class="portfolio-summary-sub">目前還沒有庫存紀錄。從任一個股卡點「💼 加入庫存」即可建立。</div></div>`;
 let totalCost=0,coveredCost=0,coveredValue=0,quoted=0;
 entries.forEach(([code,h])=>{
  const sh=+(h.shares||0),co=+(h.cost||0);if(sh>0&&co>0)totalCost+=sh*co;
  const r=currentHoldingRow(code),px=+(r?.close||0);if(sh>0&&co>0&&px>0){coveredCost+=sh*co;coveredValue+=sh*px;quoted++}
 });
 const pnl=coveredCost>0?coveredValue-coveredCost:null,pct=coveredCost>0?pnl/coveredCost*100:null;
 const pc=pnl>0?"pnl up":pnl<0?"pnl down":"pnl";
 return `<div class="portfolio-summary"><div class="portfolio-summary-title">💼 我的庫存｜${entries.length} 檔</div><div class="portfolio-summary-sub">本機資料，不上傳 GitHub｜目前可取得行情 ${quoted}/${entries.length} 檔</div><div class="portfolio-summary-grid"><div class="portfolio-summary-item"><div class="portfolio-summary-v">${portfolioMoney(totalCost)}</div><div class="portfolio-summary-l">成本總額</div></div><div class="portfolio-summary-item"><div class="portfolio-summary-v">${portfolioMoney(coveredValue)}</div><div class="portfolio-summary-l">可計目前市值</div></div><div class="portfolio-summary-item"><div class="portfolio-summary-v ${pc}">${portfolioMoney(pnl)}</div><div class="portfolio-summary-l">可計未實現損益</div></div><div class="portfolio-summary-item"><div class="portfolio-summary-v ${pc}">${pct===null?"—":signed(pct,2)}</div><div class="portfolio-summary-l">可計報酬率</div></div></div></div>`;
}
function portfolioHTML(r){
 const h=holding(r.code);if(!h)return "";
 const sh=+(h.shares||0),co=h.cost===null||h.cost===undefined?null:+h.cost,px=+(r.close||0),p=portfolioPnL(h,px);
 const pc=p.pnl>0?"pnl up":p.pnl<0?"pnl down":"pnl";
 const st=stageKey(r.category),sys=st==="結構失效"?`<span class="portfolio-system bad">系統目前：❌ 結構失效，請對照你的失效條件</span>`:st==="轉弱警戒"?`<span class="portfolio-system warn">系統目前：⚠️ 轉弱警戒，請檢查持有理由</span>`:`<span class="portfolio-system">系統目前：${st||"觀察"}</span>`;
 const reason=x=>escHTML(x||"尚未填寫").replace(/\n/g,"<br>");
 return `<div class="portfoliobox"><div class="portfolio-top"><div><div class="portfolio-title">💼 我的庫存</div><div class="portfolio-statusline"><span class="portfolio-status ${reasonStatusClass(h.reason_status)}">${reasonStatusText(h.reason_status)}</span>${sys}</div></div><button class="portfolio-editbtn" type="button" data-portfolio-edit="${r.code}">編輯庫存</button></div><div class="portfolio-grid"><div class="portfolio-metric"><div class="portfolio-metric-v">${sh>0?num(sh,0)+"股":"—"}</div><div class="portfolio-metric-l">持有股數</div></div><div class="portfolio-metric"><div class="portfolio-metric-v">${co&&co>0?num(co,2):"—"}</div><div class="portfolio-metric-l">平均成本</div></div><div class="portfolio-metric"><div class="portfolio-metric-v ${pc}">${portfolioMoney(p.pnl)}</div><div class="portfolio-metric-l">未實現損益</div></div><div class="portfolio-metric"><div class="portfolio-metric-v ${pc}">${p.pct===null?"—":signed(p.pct,2)}</div><div class="portfolio-metric-l">報酬率</div></div></div><div class="portfolio-reasons"><div class="portfolio-reason"><b>🎯 進場理由</b>${reason(h.entry_reason)}</div><div class="portfolio-reason"><b>🧩 持有理由</b>${reason(h.hold_reason)}</div><div class="portfolio-reason"><b>🛑 結構失效條件</b>${reason(h.invalidation)}</div></div>${r._portfolio_fallback?`<div class="portfolio-fallback">⚠️ ${escHTML(r._portfolio_fallback)}</div>`:""}</div>`;
}
function showPortfolioEditor(code){
 code=String(code);const r=currentHoldingRow(code)||universe.find(x=>String(x.code)===code)||{code,name:code};const h=holding(code)||{};
 document.getElementById("portfolioEditBack")?.remove();
 const back=document.createElement("div");back.id="portfolioEditBack";back.className="portfolio-back";
 const status=h.reason_status||"valid";
 back.innerHTML=`<div class="portfolio-modal"><div class="portfolio-modal-top"><div><div class="portfolio-modal-title">💼 ${escHTML(r.name||code)} <span class="code">${escHTML(code)}</span></div><div class="sub">庫存資料只存在這個瀏覽器</div></div><button class="portfolio-close" type="button" data-portfolio-cancel="1">關閉</button></div><div class="portfolio-form-grid"><div class="portfolio-field"><label>持有股數</label><input id="pfShares" class="portfolio-input" type="number" min="0" step="1" inputmode="numeric" value="${escHTML(h.shares??"")}" placeholder="例如 40"></div><div class="portfolio-field"><label>平均成本</label><input id="pfCost" class="portfolio-input" type="number" min="0" step="0.01" inputmode="decimal" value="${escHTML(h.cost??"")}" placeholder="例如 139.5"></div><div class="portfolio-field full"><label>進場理由｜當初為什麼買？</label><textarea id="pfEntry" class="portfolio-textarea" placeholder="例如：外資連買、股價尚未發動，小量試單">${escHTML(h.entry_reason||"")}</textarea></div><div class="portfolio-field full"><label>持有理由｜現在為什麼繼續留？</label><textarea id="pfHold" class="portfolio-textarea" placeholder="例如：60分K仍向上、族群共振、支撐未失守">${escHTML(h.hold_reason||"")}</textarea></div><div class="portfolio-field"><label>理由狀態｜由你手動維護</label><select id="pfStatus" class="portfolio-select"><option value="valid" ${status==="valid"?"selected":""}>✅ 仍成立</option><option value="weak" ${status==="weak"?"selected":""}>⚠️ 轉弱</option><option value="invalid" ${status==="invalid"?"selected":""}>❌ 消失</option></select></div><div class="portfolio-field"><label>目前行情</label><div class="portfolio-input">${r.close?num(r.close,2):"—"}｜${stageKey(r.category)||"觀察"}</div></div><div class="portfolio-field full"><label>結構失效條件｜什麼情況代表交易邏輯不成立？</label><textarea id="pfInvalid" class="portfolio-textarea" placeholder="例如：跌破20MA＋前低且反抽站不回，並伴隨量增">${escHTML(h.invalidation||"")}</textarea></div></div><div class="portfolio-actions"><button class="portfolio-save" type="button" data-portfolio-save="${escHTML(code)}">儲存庫存</button><button class="portfolio-remove" type="button" data-portfolio-remove="${escHTML(code)}">移除庫存</button><button class="portfolio-cancel" type="button" data-portfolio-cancel="1">取消</button></div><div class="portfolio-privacy">🔒 這些資料只寫入目前裝置的 localStorage，不會送到公開 GitHub repository。清除網站資料、無痕模式或更換裝置時不會自動同步。</div></div>`;
 document.body.appendChild(back);
}
function savePortfolioEditor(code){
 code=String(code);const shares=Number(document.getElementById("pfShares")?.value||0),rawCost=(document.getElementById("pfCost")?.value||"").trim(),cost=rawCost===""?null:Number(rawCost);
 if(!(shares>0)){alert("請輸入大於 0 的持有股數");return}
 if(cost!==null&&(!(cost>0)||!Number.isFinite(cost))){alert("平均成本請輸入大於 0 的數字，或先留空");return}
 portfolioData[code]={shares,cost,entry_reason:document.getElementById("pfEntry")?.value.trim()||"",hold_reason:document.getElementById("pfHold")?.value.trim()||"",reason_status:document.getElementById("pfStatus")?.value||"valid",invalidation:document.getElementById("pfInvalid")?.value.trim()||"",updated_at:new Date().toISOString()};
 savePortfolioData();document.getElementById("portfolioEditBack")?.remove();render();
}
function removePortfolio(code){
 code=String(code);if(!holding(code)){document.getElementById("portfolioEditBack")?.remove();return}
 if(!confirm(`確定要把 ${code} 從「我的庫存」移除嗎？`))return;
 delete portfolioData[code];savePortfolioData();document.getElementById("portfolioEditBack")?.remove();render();
}
portfolioData=loadPortfolio();
function num(v,d=1)'''
    s = must(s, old, helpers, "portfolio JS helpers")

    # Peer peek: three actions, including inventory editor.
    s = s.replace(
        '.peerpeekactions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}',
        '.peerpeekactions{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}',
        1,
    )
    old = '<div class="peerpeekactions"><button class="peerpeekbtn" data-peer-open="${r.code}">查看完整個股</button><button class="peerpeekbtn secondary" data-peer-close="1">關閉</button></div>'
    new = '<div class="peerpeekactions"><button class="peerpeekbtn" data-peer-open="${r.code}">查看完整個股</button><button class="peerpeekbtn" data-portfolio-edit="${r.code}">💼 庫存</button><button class="peerpeekbtn secondary" data-peer-close="1">關閉</button></div>'
    s = must(s, old, new, "peer portfolio action")

    # Render: portfolio-only source, summary, card button + portfolio box.
    old = '''function render(){
 rows=mode==="intraday"?intraRows:closeRows;
 let rr=rows.filter(r=>(filter==="all"||stageKey(r.category)===stageKey(filter))&&(!watchOnly||watched(r.code)));
 const q=$("q").value.trim().toLowerCase();'''
    new = '''function render(){
 rows=mode==="intraday"?intraRows:closeRows;
 let source=rows;
 if(portfolioOnly)source=Object.keys(portfolioData).map(code=>currentHoldingRow(code)).filter(Boolean);
 let rr=source.filter(r=>(filter==="all"||stageKey(r.category)===stageKey(filter))&&(!watchOnly||watched(r.code)));
 $("portfolioSummary").innerHTML=portfolioSummaryHTML();
 const q=$("q").value.trim().toLowerCase();'''
    s = must(s, old, new, "portfolio render source")

    old = '<span class="quality ${qualityCls(r.quality_label)}">${mode==="intraday"?"動能":"波段"}：${r.quality_label||"一般"}</span></div></div><div><div class="score">'
    new = '<span class="quality ${qualityCls(r.quality_label)}">${mode==="intraday"?"動能":"波段"}：${r.quality_label||"一般"}</span><button class="portfolio-mini ${held(r.code)?"held":""}" type="button" data-portfolio-edit="${r.code}">${held(r.code)?"💼 已持有":"💼 加入庫存"}</button></div></div><div><div class="score">'
    s = must(s, old, new, "portfolio card button")

    old = '  ${stageExplainHTML(r)}\n  ${changeBadgeHTML(r)}'
    new = '  ${stageExplainHTML(r)}\n  ${portfolioHTML(r)}\n  ${changeBadgeHTML(r)}'
    s = must(s, old, new, "portfolio card detail")

    # Filter handler.
    old = '$("watchOnly").onclick=()=>{watchOnly=!watchOnly;$("watchOnly").classList.toggle("on",watchOnly);render()};\n$("scan").onclick=render;'
    new = '$("watchOnly").onclick=()=>{watchOnly=!watchOnly;$("watchOnly").classList.toggle("on",watchOnly);render()};\n$("portfolioOnly").onclick=()=>{portfolioOnly=!portfolioOnly;$("portfolioOnly").classList.toggle("on",portfolioOnly);render()};\n$("scan").onclick=render;'
    s = must(s, old, new, "portfolio filter handler")

    # Delegated modal actions.
    old = '''document.addEventListener("click",e=>{
 const peer=e.target.closest(".peerlink");'''
    new = '''document.addEventListener("click",e=>{
 const pe=e.target.closest("[data-portfolio-edit]");if(pe){showPortfolioEditor(pe.dataset.portfolioEdit);return}
 const ps=e.target.closest("[data-portfolio-save]");if(ps){savePortfolioEditor(ps.dataset.portfolioSave);return}
 const pr=e.target.closest("[data-portfolio-remove]");if(pr){removePortfolio(pr.dataset.portfolioRemove);return}
 if(e.target.closest("[data-portfolio-cancel]")||e.target.id==="portfolioEditBack"){document.getElementById("portfolioEditBack")?.remove();return}
 const peer=e.target.closest(".peerlink");'''
    s = must(s, old, new, "portfolio delegated actions")

    # Service worker version.
    s = s.replace('./sw.js?v=1521', './sw.js?v=1522')
    s = s.replace('dogsonSwReloaded1521', 'dogsonSwReloaded1522')

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = must(s, "dogson-free-v1521", "dogson-free-v1522", "service worker cache")
    write(p, s)


def patch_status():
    p = ROOT / "docs/data/status.json"
    obj = json.loads(p.read_text(encoding="utf-8"))
    obj["version"] = "1.5.22-free"
    obj["portfolio_mode_version"] = "1.0"
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    patch_index()
    patch_sw()
    patch_status()
    print("v1.5.22 portfolio mode patch applied")
