#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.29 — Step 8：獨立當沖模式 UI / persistence / version wiring。"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def read(p): return (ROOT / p).read_text(encoding="utf-8")
def write(p, s): (ROOT / p).write_text(s, encoding="utf-8")
def must(s, old, new, label, count=1):
    if old not in s:
        raise SystemExit("v1.5.29 missing marker: " + label)
    return s.replace(old, new, count)


def patch_versions():
    p = "scripts/build_data.py"
    s = read(p)
    s = s.replace("犬子老師飆股雷達 Free Edition v1.5.28", "犬子老師飆股雷達 Free Edition v1.5.29", 1)
    s = s.replace('"version": "1.5.28-free"', '"version": "1.5.29-free"')
    write(p, s)

    p = "scripts/bridge_intraday.py"
    s = read(p).replace('"version": "1.5.27-free"', '"version": "1.5.29-free"')
    write(p, s)


def patch_sync():
    p = "scripts/sync_live_data.py"
    s = read(p)
    s = s.replace("以及 v1.4.2 的 TWSE MIS 盤中快照橋接歷史、Step 7 驗證歷史。", "以及 v1.4.2 的 TWSE MIS 盤中快照橋接歷史、Step 7 驗證歷史、Step 8 當沖衍生資料。")
    s = must(
        s,
        '    "validation_history.json", "validation.json",\n',
        '    "validation_history.json", "validation.json", "daytrade.json",\n',
        "sync daytrade",
    )
    write(p, s)


def patch_ui():
    p = "docs/index.html"
    s = read(p)
    s = s.replace("Free Edition v1.5.28｜Step 7 歷史驗證校準", "Free Edition v1.5.29｜Step 8 獨立當沖模式", 1)
    s = s.replace(".tabs{display:grid;grid-template-columns:1fr 1fr;", ".tabs{display:grid;grid-template-columns:repeat(3,1fr);", 1)

    css = r'''
/* v1.5.29 Step 8 independent daytrade */
.daytradebox{margin-top:10px;border:1px solid #46516b;background:linear-gradient(180deg,#151a27,#0e141d);border-radius:13px;padding:10px}.daytradetop{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}.daytradetitle{font-size:11px;color:#aeb9ca;font-weight:850}.daytradestate{border-radius:999px;padding:6px 9px;font-size:11px;font-weight:900;white-space:nowrap}.daytradestate.go{background:#153323;color:#a6efbf}.daytradestate.wait{background:#3a2e12;color:#ffd77b}.daytradestate.watch{background:#17304a;color:#b9ddff}.daytradestate.hot{background:#3c1d3f;color:#eab4ff}.daytradestate.fail{background:#3d171d;color:#ffacb8}.daytradeheadline{font-size:12px;font-weight:900;margin-top:6px}.daytradesource{font-size:9px;color:var(--muted);margin-top:7px;line-height:1.45}.daytrade-only{display:none}
@media(max-width:620px){.tabs{grid-template-columns:1fr}.tab{padding:9px;font-size:13px}}
'''
    if ".daytradebox{" not in s:
        s = must(s, "</style>", css + "\n</style>", "daytrade css")

    s = must(
        s,
        '<div class="tabs"><button class="tab active" data-mode="intraday">⚡ 盤中雷達</button><button class="tab" data-mode="close">🌙 盤後雷達</button></div>',
        '<div class="tabs"><button class="tab active" data-mode="intraday">⚡ 盤中波段</button><button class="tab" data-mode="daytrade">🎯 當沖模式</button><button class="tab" data-mode="close">🌙 盤後波段</button></div>',
        "three tabs",
    )

    filter_old = '<button class="filter" data-f="過熱不追">🚫 過熱不追</button><button class="filter" id="watchOnly">⭐ 我的關注</button>'
    filter_new = '<button class="filter" data-f="過熱不追">🚫 過熱不追</button><button class="filter daytrade-only" data-daytrade-only="1" data-f="可執行">🟢 可執行</button><button class="filter daytrade-only" data-daytrade-only="1" data-f="等回踩">🟡 等回踩</button><button class="filter daytrade-only" data-daytrade-only="1" data-f="失效">🔴 失效</button><button class="filter" id="watchOnly">⭐ 我的關注</button>'
    s = must(s, filter_old, filter_new, "daytrade filters")

    s = must(
        s,
        '<div class="guide-line"><span class="guide-key">🌙 盤後雷達</span>：看「收盤後，這檔股票適不適合繼續追蹤成波段」。會加入日K、籌碼、法人與進場位置。</div>\n      <div class="guide-tip">同一檔股票盤中分數高、盤後分數普通，不代表資料打架；兩套雷達看的時間尺度不同。</div>',
        '<div class="guide-line"><span class="guide-key">🎯 當沖模式</span>：只看當天 5 分K 執行條件，使用獨立的當沖100分與「可執行／等回踩／觀察／過熱不追／失效」狀態；不覆蓋盤中波段 Stage。</div>\n      <div class="guide-line"><span class="guide-key">🌙 盤後雷達</span>：看「收盤後，這檔股票適不適合繼續追蹤成波段」。會加入日K、籌碼、法人與進場位置。</div>\n      <div class="guide-tip">同一檔股票在三個頁籤分數不同是正常的：盤中波段、當沖、盤後波段本來就是三套不同時間尺度。</div>',
        "guide three modes",
    )

    guide_marker = '<div class="guide-title">⑱ 第一次使用，照這個順序最快</div>'
    guide_insert = '''<div class="guide-title">⑱ Step 8｜獨立當沖模式：只回答今天這一筆好不好做</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">獨立當沖 100 分</span>：執行價格結構 30＋量價推進 25＋相對強弱/族群 20＋進場時機/波動效率 15＋流動性/風險 10。</div>
      <div class="guide-line"><span class="guide-key">🟢 可執行</span>：VWAP、5分短均、量價、相對強弱、族群與位置同步，而且大盤不是防守模式。</div>
      <div class="guide-line"><span class="guide-key">🟡 等回踩</span>：股票夠強，但位置偏高、15分鐘推進偏快或突破後風險報酬不漂亮，先等回到合理執行區。</div>
      <div class="guide-line"><span class="guide-key">🔵 觀察</span>：尚未形成足夠同步，沒有必要因為一根紅K就追。</div>
      <div class="guide-line"><span class="guide-key">🚫 過熱不追</span>：超過 Step 6 的個股化漲幅／VWAP／15分／量速門檻，或振幅屬高震盪／沖高回落。</div>
      <div class="guide-line"><span class="guide-key">🔴 失效</span>：跌回 VWAP 下且短均、15分鐘動能等同步轉弱，當沖執行結構不成立。</div>
      <div class="guide-tip">隔離規則：當沖模式只讀 intraday.json，另寫 daytrade.json；不改 Stage 2.0、不改盤中波段100分、不改盤後波段100分。原盤中 Stage 會以「來源 Stage」保留給你對照。</div>
    </div>

    <div class="guide-title">⑲ 第一次使用，照這個順序最快</div>'''
    s = must(s, guide_marker, guide_insert, "Step8 guide")
    s = s.replace(
        '<div class="guide-line"><b>盤後：</b>① 看大盤環境 → ② 看法人族群資金流 → ③ 看個股波段延續 → ④ 再看進場位置 → ⑤ 用籌碼、支撐壓力確認隔日計畫。</div>',
        '<div class="guide-line"><b>當沖：</b>① 先看大盤是否防守 → ② 找當沖「可執行／等回踩」→ ③ 看 VWAP、5分短均、量速與15分鐘推進 → ④ 檢查個股化過熱門檻 → ⑤ 不符合就放掉，不硬追。</div>\n      <div class="guide-line"><b>盤後：</b>① 看大盤環境 → ② 看法人族群資金流 → ③ 看個股波段延續 → ④ 再看進場位置 → ⑤ 用籌碼、支撐壓力確認隔日計畫。</div>',
        1,
    )

    s = must(
        s,
        'let mode="intraday",filter="all",watchOnly=false,portfolioOnly=false,portfolioData={},universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[],changeRadar={},validationReport={};',
        'let mode="intraday",filter="all",watchOnly=false,portfolioOnly=false,portfolioData={},universe=[],closeRows=[],intraRows=[],daytradeRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},daytradeMarket={},sectorRotation=[],sectorFunds=[],changeRadar={},validationReport={},daytradeReport={};',
        "daytrade variables",
    )

    old = '''function currentHoldingRow(code){
 code=String(code);
 const primary=mode==="intraday"?intraRows:closeRows;
 const secondary=mode==="intraday"?closeRows:intraRows;'''
    new = '''function currentHoldingRow(code){
 code=String(code);
 const primary=mode==="daytrade"?daytradeRows:(mode==="intraday"?intraRows:closeRows);
 const secondary=mode==="daytrade"?intraRows:(mode==="intraday"?closeRows:intraRows);'''
    s = must(s, old, new, "holding row mode")
    s = s.replace('mode==="intraday"?"盤中行情暫缺，使用最近盤後資料":"盤後資料暫缺，使用最近盤中資料"', 'mode==="close"?"盤後資料暫缺，使用最近盤中資料":(mode==="daytrade"?"當沖衍生資料暫缺，使用原盤中資料":"盤中行情暫缺，使用最近盤後資料")', 1)

    old = '''function portfolioHTML(r){
 const h=holding(r.code);if(!h)return "";
 const sh=+(h.shares||0),co=h.cost===null||h.cost===undefined?null:+h.cost,px=+(r.close||0),p=portfolioPnL(h,px);
 const pc=p.pnl>0?"pnl up":p.pnl<0?"pnl down":"pnl";
 const st=stageKey(r.category),sys=st==="結構失效"?`<span class="portfolio-system bad">系統目前：❌ 結構失效，請對照你的失效條件</span>`:st==="轉弱警戒"?`<span class="portfolio-system warn">系統目前：⚠️ 轉弱警戒，請檢查持有理由</span>`:`<span class="portfolio-system">系統目前：${st||"觀察"}</span>`;'''
    new = '''function portfolioHTML(r){
 const h=holding(r.code);if(!h)return "";
 const pr=mode==="daytrade"?(intraRows.find(x=>String(x.code)===String(r.code))||r):r;
 const sh=+(h.shares||0),co=h.cost===null||h.cost===undefined?null:+h.cost,px=+(r.close||0),p=portfolioPnL(h,px);
 const pc=p.pnl>0?"pnl up":p.pnl<0?"pnl down":"pnl";
 const st=stageKey(pr.category),sys=st==="結構失效"?`<span class="portfolio-system bad">系統目前：❌ 結構失效，請對照你的失效條件</span>`:st==="轉弱警戒"?`<span class="portfolio-system warn">系統目前：⚠️ 轉弱警戒，請檢查持有理由</span>`:`<span class="portfolio-system">系統目前：${st||"觀察"}</span>`;'''
    s = must(s, old, new, "portfolio source isolation")
    s = s.replace('${dynamicThresholdHTML(r)}${portfolioDecisionHTML(r,h)}', '${dynamicThresholdHTML(pr)}${portfolioDecisionHTML(pr,h)}', 1)

    old_cls = 'function cls(c){return c==="蓄勢待發"?"setup":c==="剛啟動"?"start":c==="回踩承接"?"pull":c==="趨勢持有"?"trendhold":c==="轉弱警戒"?"weak":c==="結構失效"?"invalid":c==="過熱不追"?"hot":"watch"}'
    new_cls = 'function cls(c){return c==="可執行"?"start":c==="等回踩"?"pull":c==="失效"?"invalid":c==="蓄勢待發"?"setup":c==="剛啟動"?"start":c==="回踩承接"?"pull":c==="趨勢持有"?"trendhold":c==="轉弱警戒"?"weak":c==="結構失效"?"invalid":c==="過熱不追"?"hot":"watch"}'
    s = must(s, old_cls, new_cls, "daytrade cls")
    s = s.replace('function qualityCls(q){return (q==="高共振"||q==="高延續"||q==="強動能")?"high":(q==="強"||q==="轉強")?"strong":""}', 'function qualityCls(q){return (q==="高共振"||q==="高延續"||q==="強動能"||q==="強勢")?"high":(q==="強"||q==="轉強"||q==="良好")?"strong":""}', 1)

    old_footer = '''function updateFooter(){
 const el=$("footerText");if(!el)return;
 el.textContent=mode==="intraday"
  ?"盤中動能100＝價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10｜籌碼只作背景｜大盤15分獨立"
  :"波段延續100＝日K技術50＋籌碼25＋族群15＋流動性10｜直接加總不換算｜進場位置100獨立｜大盤15分獨立";
}'''
    new_footer = '''function updateFooter(){
 const el=$("footerText");if(!el)return;
 el.textContent=mode==="daytrade"
  ?"獨立當沖100＝執行結構30＋量價推進25＋相對/族群20＋時機/波動15＋流動性/風險10｜只讀原盤中資料，不覆蓋Stage或波段分"
  :mode==="intraday"
  ?"盤中動能100＝價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10｜籌碼只作背景｜大盤15分獨立"
  :"波段延續100＝日K技術50＋籌碼25＋族群15＋流動性10｜直接加總不換算｜進場位置100獨立｜大盤15分獨立";
}'''
    s = must(s, old_footer, new_footer, "daytrade footer")

    s = s.replace('if(mode==="intraday"&&m.intraday_only){', 'if((mode==="intraday"||mode==="daytrade")&&m.intraday_only){', 1)
    s = s.replace('const members=intraRows\n   .filter', 'const members=(mode==="daytrade"?daytradeRows:intraRows)\n   .filter', 1)

    old_entry_summary = '''function entrySummaryHTML(){
 if(mode!=="intraday")return "";
 let green=0,yellow=0,red=0;'''
    new_entry_summary = '''function entrySummaryHTML(){
 if(mode==="daytrade"){
  const counts={"可執行":0,"等回踩":0,"觀察":0,"過熱不追":0,"失效":0};
  (daytradeRows||[]).forEach(r=>{const k=r.daytrade_state||r.category||"觀察";counts[k]=(counts[k]||0)+1});
  return `<div class="entrysummary"><div class="entrysummarytop"><div><div class="entrysummarytitle">🎯 Step 8｜獨立當沖雷達</div><div class="entrysummarysub">只回答今天的執行品質；不改盤中波段 Stage 2.0，也不改波段分數。</div></div></div><div class="entrycounts"><div class="entrycount"><div class="entrycountv">🟢 ${counts["可執行"]||0}</div><div class="entrycountl">可執行</div></div><div class="entrycount"><div class="entrycountv">🟡 ${counts["等回踩"]||0}</div><div class="entrycountl">等回踩</div></div><div class="entrycount"><div class="entrycountv">🚫 ${(counts["過熱不追"]||0)+(counts["失效"]||0)}</div><div class="entrycountl">過熱／失效</div></div></div></div>`;
 }
 if(mode!=="intraday")return "";
 let green=0,yellow=0,red=0;'''
    s = must(s, old_entry_summary, new_entry_summary, "daytrade summary")

    s = s.replace('function metrics(r){\n if(mode==="intraday")return', 'function metrics(r){\n if(mode!=="close")return', 1)

    old_stage = '''function stageExplainHTML(r,compact=false){
 const category=r.category||"觀察";
 const reason=(r.stage_reason||"目前沒有足夠資料形成明確生命週期判讀").trim();'''
    new_stage = '''function stageExplainHTML(r,compact=false){
 const category=(mode==="daytrade"?(r.daytrade_state||r.category):r.category)||"觀察";
 const reason=(r.stage_reason||(mode==="daytrade"?"目前沒有足夠資料形成明確當沖判讀":"目前沒有足夠資料形成明確生命週期判讀")).trim();'''
    s = must(s, old_stage, new_stage, "daytrade stage header")
    old_return = 'return `<div class="stagebox"><div class="stagetop"><span class="stagetitle">${compact?"生命週期":"🧭 生命週期判讀"}</span><span class="cat ${cls(category)}">${category}</span></div><div class="stagereason">${reason}</div>${evidence}</div>`;'
    new_return = 'return `<div class="stagebox"><div class="stagetop"><span class="stagetitle">${mode==="daytrade"?(compact?"當沖判讀":"🎯 當沖獨立判讀"):(compact?"生命週期":"🧭 生命週期判讀")}</span><span class="cat ${cls(category)}">${category}</span></div><div class="stagereason">${reason}</div>${evidence}${mode==="daytrade"?`<div class="stagehint">來源盤中 Stage 2.0：${escHTML(r.source_category||"—")}｜來源盤中動能 ${num(r.source_intraday_score,0)}/100｜兩套分數互不覆蓋</div>`:""}</div>`;'
    s = must(s, old_return, new_return, "daytrade stage return")

    old_peer = ''' const intr=mode==="intraday";
 const items=intr?[
  ["現價",num(r.close,2)],["盤中動能",num(r.intraday_score??r.score,0)+"/100"],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["族群共振",num(r.sector_score,1)+"/10"],["籌碼背景",r.chip_background||"資料不足"]
 ]:[
'''
    new_peer = ''' const dt=mode==="daytrade",intr=mode==="intraday";
 const items=dt?[
  ["現價",num(r.close,2)],["當沖分",num(r.daytrade_score??r.score,0)+"/100"],["當沖狀態",r.daytrade_state||"觀察"],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["來源Stage",r.source_category||"—"]
 ]:intr?[
  ["現價",num(r.close,2)],["盤中動能",num(r.intraday_score??r.score,0)+"/100"],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["族群共振",num(r.sector_score,1)+"/10"],["籌碼背景",r.chip_background||"資料不足"]
 ]:[
'''
    s = must(s, old_peer, new_peer, "daytrade peer")

    s = must(
        s,
        ' if(x.includes("蓄勢"))return "蓄勢待發";',
        ' if(raw==="可執行"||raw==="等回踩"||raw==="失效")return raw;\n if(x.includes("蓄勢"))return "蓄勢待發";',
        "daytrade stage key",
    )

    old_parts = '''function partsHTML(r){
 if(mode==="intraday"){'''
    new_parts = '''function partsHTML(r){
 if(mode==="daytrade"){
  const c=r.daytrade_components||{};
  return `<div class="parts intradayparts">
   <div class="part"><div class="partv">${num(c.execution_structure,0)}/30</div><div class="partl">執行價格結構</div></div>
   <div class="part"><div class="partv">${num(c.flow_volume,0)}/25</div><div class="partl">量價／即時推進</div></div>
   <div class="part"><div class="partv">${num(c.relative_sector,0)}/20</div><div class="partl">相對強弱＋族群</div></div>
   <div class="part"><div class="partv">${num(c.timing_volatility,0)}/15</div><div class="partl">時機／波動效率</div></div>
   <div class="part"><div class="partv">${num(c.liquidity_risk,0)}/10</div><div class="partl">流動性／追價風險</div></div>
   <div class="part"><div class="partv">${num(r.source_intraday_score,0)}/100</div><div class="partl">來源盤中分 · 不覆蓋</div></div>
  </div>`;
 }
 if(mode==="intraday"){'''
    s = must(s, old_parts, new_parts, "daytrade parts")

    old_render = ' rows=mode==="intraday"?intraRows:closeRows;'
    s = must(s, old_render, ' rows=mode==="daytrade"?daytradeRows:(mode==="intraday"?intraRows:closeRows);', "render daytrade rows")
    s = s.replace('${mode==="intraday"?(r.time||""):(r.date||"")}', '${mode==="close"?(r.date||""):(r.quote_time||r.time||"")}', 1)
    s = s.replace('${mode==="intraday"?"動能":"波段"}：${r.quality_label||"一般"}', '${mode==="daytrade"?"當沖":(mode==="intraday"?"動能":"波段")}：${r.quality_label||"一般"}', 1)
    s = s.replace('${mode==="intraday"?num(r.intraday_score??r.score,0):(r.score_reliable===false?"—":num(r.swing_quality_score??r.score,0))}', '${mode==="daytrade"?num(r.daytrade_score??r.score,0):(mode==="intraday"?num(r.intraday_score??r.score,0):(r.score_reliable===false?"—":num(r.swing_quality_score??r.score,0)))}', 1)
    s = s.replace('${mode==="intraday"?"盤中動能 /100":(r.score_reliable===false?"籌碼覆蓋不足":"波段延續 /100")}', '${mode==="daytrade"?"獨立當沖 /100":(mode==="intraday"?"盤中動能 /100":(r.score_reliable===false?"籌碼覆蓋不足":"波段延續 /100"))}', 1)

    old_load = '''  const [u,c,i,s,m,v]=await Promise.all([
   fetch("./data/universe.json?"+bust),fetch("./data/close.json?"+bust),
   fetch("./data/intraday.json?"+bust),fetch("./data/status.json?"+bust),
   fetch("./data/market.json?"+bust),fetch("./data/validation.json?"+bust)
  ]);
  universe=await u.json();let cj=await c.json(),ij=await i.json(),sj=await s.json();validationReport=await v.json();
  closeMarket=await m.json();intraMarket=ij.market||closeMarket;marketLive=ij.market_intraday||{};sectorRotation=ij.sector_rotation||[];changeRadar=ij.change_radar||{};market=intraMarket;
  closeRows=cj.rows||[];sectorFunds=cj.sector_funds||[];intraRows=ij.rows||[];'''
    new_load = '''  const [u,c,i,s,m,v,d]=await Promise.all([
   fetch("./data/universe.json?"+bust),fetch("./data/close.json?"+bust),
   fetch("./data/intraday.json?"+bust),fetch("./data/status.json?"+bust),
   fetch("./data/market.json?"+bust),fetch("./data/validation.json?"+bust),fetch("./data/daytrade.json?"+bust)
  ]);
  universe=await u.json();let cj=await c.json(),ij=await i.json(),sj=await s.json();validationReport=await v.json();daytradeReport=await d.json();
  closeMarket=await m.json();intraMarket=ij.market||closeMarket;daytradeMarket=daytradeReport.market||intraMarket;marketLive=ij.market_intraday||{};sectorRotation=ij.sector_rotation||[];changeRadar=ij.change_radar||{};market=intraMarket;
  closeRows=cj.rows||[];sectorFunds=cj.sector_funds||[];intraRows=ij.rows||[];daytradeRows=daytradeReport.rows||[];'''
    s = must(s, old_load, new_load, "load daytrade")

    filter_fn = r'''
const DAYTRADE_FILTERS=new Set(["all","可執行","等回踩","觀察","過熱不追","失效"]);
function syncModeFilters(){
 document.querySelectorAll(".filter[data-f]").forEach(b=>{
  const extra=b.dataset.daytradeOnly==="1",f=b.dataset.f||"all";
  b.style.display=mode==="daytrade"?(DAYTRADE_FILTERS.has(f)?"":"none"):(extra?"none":"");
 });
}
'''
    tab_marker = 'document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{'
    if "function syncModeFilters()" not in s:
        s = must(s, tab_marker, filter_fn + "\n" + tab_marker, "filter mode function")

    old_tab = 'document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");mode=b.dataset.mode;market=mode==="intraday"?intraMarket:closeMarket;$("modeText").textContent=mode==="intraday"?"盤中：執行雷達 / 動能 / 當沖與庫存進出 / 族群輪動":"盤後：波段雷達 / 延續性 / 進場位置 / 60分K";$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();$("changebox").innerHTML=changeRadarHTML();updateFooter();render()});'
    new_tab = 'document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");mode=b.dataset.mode;filter="all";document.querySelectorAll(".filter[data-f]").forEach(x=>x.classList.toggle("on",x.dataset.f==="all"));market=mode==="daytrade"?daytradeMarket:(mode==="intraday"?intraMarket:closeMarket);$("modeText").textContent=mode==="daytrade"?"當沖：獨立100分 / VWAP / 5分執行 / 個股化追價門檻":(mode==="intraday"?"盤中波段：動能 / 三燈 / Stage / 族群輪動":"盤後波段：延續性 / 進場位置 / 60分K");syncModeFilters();$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();$("changebox").innerHTML=changeRadarHTML();updateFooter();render()});'
    s = must(s, old_tab, new_tab, "daytrade tab handler")

    # Initial UI state and service-worker cache.
    s = s.replace('$("status").textContent="已更新";$("marketbox")', '$("status").textContent="已更新";syncModeFilters();$("marketbox")', 1)
    s = s.replace('./sw.js?v=1528', './sw.js?v=1529').replace('dogsonSwReloaded1528', 'dogsonSwReloaded1529').replace('./hourly.js?v=1528', './hourly.js?v=1529')
    write(p, s)


def patch_sw_status():
    p = "docs/sw.js"
    s = read(p).replace("dogson-free-v1528", "dogson-free-v1529").replace("./hourly.js?v=1528", "./hourly.js?v=1529")
    write(p, s)

    p = "docs/data/status.json"
    d = json.loads(read(p))
    d["version"] = "1.5.29-free"
    d["daytrade_version"] = "1.0"
    write(p, json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n")

    dp = ROOT / "docs/data/daytrade.json"
    if not dp.exists():
        write("docs/data/daytrade.json", json.dumps({
            "version": "1.0", "updated_at": None, "source": "intraday.json read-only derivative",
            "market": {}, "market_intraday": {}, "sector_rotation": [],
            "weights": {"execution_structure":30,"flow_volume":25,"relative_sector":20,"timing_volatility":15,"liquidity_risk":10},
            "state_counts": {},
            "isolation": {"writes_intraday":False,"changes_stage2":False,"changes_swing_score":False,"changes_intraday_score":False},
            "rows": [], "note": "Step 8 已啟用，等待當沖資料建置。"
        }, ensure_ascii=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    patch_versions()
    patch_sync()
    patch_ui()
    patch_sw_status()
    print("v1.5.29 Step 8 independent daytrade UI applied")
