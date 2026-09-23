#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.28 — Step 7 歷史驗證／結果校準系統。"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def must(s,old,new,label,count=1):
    if old not in s: raise SystemExit('v1.5.28 missing marker: '+label)
    return s.replace(old,new,count)


def patch_build_data():
    p='scripts/build_data.py';s=read(p)
    s=s.replace('犬子老師飆股雷達 Free Edition v1.5.27','犬子老師飆股雷達 Free Edition v1.5.28',1)
    s=must(s,'c, h, v = x["Close"], x["High"], x["Volume"]','c, h, l, v = x["Close"], x["High"], x["Low"], x["Volume"]','daily low series')
    s=must(s,'        "close": float(c.iloc[-1]),\n        "ma5": float(ma5.iloc[-1]),','        "close": float(c.iloc[-1]),\n        "high": float(h.iloc[-1]),\n        "low": float(l.iloc[-1]),\n        "ma5": float(ma5.iloc[-1]),','daily high low')

    old='''    quality_reference = 76\n    market_score = float(market.get("market_score", 7.5))\n\n    for r in rows:\n'''
    new='''    quality_reference = 76\n    market_score = float(market.get("market_score", 7.5))\n\n    # Step 7：只讀「上一輪已完成」的歷史校準，確保今天的結果不會回頭改今天的分數。\n    _baseline_swing_weights = {"technical": 50.0, "chip": 25.0, "sector": 15.0, "liquidity": 10.0}\n    _validation = load_json("validation.json", {}) if not preliminary_intraday else {}\n    _calibration = (_validation.get("calibration") or {}) if isinstance(_validation, dict) else {}\n    _calibration_active = bool(_calibration.get("active"))\n    _candidate_weights = _calibration.get("active_weights") or {}\n    _swing_weights = {}\n    for _k, _base in _baseline_swing_weights.items():\n        try:\n            _swing_weights[_k] = float(_candidate_weights.get(_k, _base)) if _calibration_active else _base\n        except Exception:\n            _swing_weights[_k] = _base\n    _wsum = sum(_swing_weights.values()) or 100.0\n    _swing_weights = {k: v / _wsum * 100.0 for k, v in _swing_weights.items()}\n\n    for r in rows:\n'''
    s=must(s,old,new,'calibration load')

    old='''            liquidity_component = _swing_liquidity_score(r)\n            swing = round(min(100.0, tech_component + chip_component + sector_component + liquidity_component), 1)\n            r["swing_components"] = {\n                "technical": round(tech_component, 1),\n                "chip": round(chip_component, 1),\n                "sector": round(sector_component, 1),\n                "liquidity": round(liquidity_component, 1),\n            }\n            r["stock_raw_score"] = swing\n'''
    new='''            liquidity_component = _swing_liquidity_score(r)\n            # 原始 component 尺度仍是 50/25/15/10；校準只調整它們在100分內的相對權重。\n            _component_caps = {"technical": 50.0, "chip": 25.0, "sector": 15.0, "liquidity": 10.0}\n            _raw_components = {\n                "technical": tech_component, "chip": chip_component,\n                "sector": sector_component, "liquidity": liquidity_component,\n            }\n            _weighted_components = {\n                k: max(0.0, min(1.0, float(_raw_components[k]) / _component_caps[k])) * float(_swing_weights[k])\n                for k in _component_caps\n            }\n            swing = round(min(100.0, sum(_weighted_components.values())), 1)\n            r["swing_components"] = {\n                "technical": round(tech_component, 1),\n                "chip": round(chip_component, 1),\n                "sector": round(sector_component, 1),\n                "liquidity": round(liquidity_component, 1),\n            }\n            r["swing_weighted_components"] = {k: round(v, 1) for k, v in _weighted_components.items()}\n            r["swing_weights"] = {k: round(v, 1) for k, v in _swing_weights.items()}\n            r["swing_weight_source"] = "historical_calibration" if _calibration_active else "baseline"\n            r["calibration_sample_rows"] = int(_calibration.get("sample_rows") or 0)\n            r["calibration_sample_dates"] = int(_calibration.get("sample_dates") or 0)\n            r["stock_raw_score"] = swing\n'''
    s=must(s,old,new,'calibrated swing score')
    s=s.replace('"version": "1.5.27-free",','"version": "1.5.28-free",')
    write(p,s)


def patch_validation():
    p='scripts/build_validation.py';s=read(p)
    old='''    dump(REPORT_PATH, report)\n    print("validation", args.mode, "close_days", report["close_snapshot_days"], "intraday_scans", report["intraday_scan_snapshots"], "matured5", report["matured_5d_rows"], "calibration", calibration["status"], "changed", changed)\n'''
    new='''    dump(REPORT_PATH, report)\n    status_path = DATA / "status.json"\n    status = load(status_path, {})\n    status["validation_version"] = "1.0"\n    status["validation_updated_at"] = report.get("updated_at")\n    status["validation_close_days"] = report.get("close_snapshot_days")\n    status["validation_matured_5d_rows"] = report.get("matured_5d_rows")\n    status["calibration_active"] = bool(calibration.get("active"))\n    # 不在這裡覆蓋 app version；由正式 build_data 版本負責。\n    dump(status_path, status)\n    print("validation", args.mode, "close_days", report["close_snapshot_days"], "intraday_scans", report["intraday_scan_snapshots"], "matured5", report["matured_5d_rows"], "calibration", calibration["status"], "changed", changed)\n'''
    s=must(s,old,new,'validation status')
    write(p,s)


def patch_sync():
    p='scripts/sync_live_data.py';s=read(p)
    s=must(s,'    "chip_history.json", "chip_status.json", "mis_snapshots.json",\n','    "chip_history.json", "chip_status.json", "mis_snapshots.json",\n    "validation_history.json", "validation.json",\n','sync validation')
    s=s.replace('以及 v1.4.2 的 TWSE MIS 盤中快照橋接歷史。','以及 v1.4.2 的 TWSE MIS 盤中快照橋接歷史、Step 7 驗證歷史。')
    write(p,s)


def patch_workflows():
    p='.github/workflows/close.yml';s=read(p)
    s=must(s,'      - "scripts/sync_live_data.py"\n','      - "scripts/sync_live_data.py"\n      - "scripts/build_validation.py"\n','close trigger validation')
    s=must(s,'      - name: Build 60m lifecycle + entry-position lights\n        run: python scripts/build_hourly.py\n','      - name: Build 60m lifecycle + entry-position lights\n        run: python scripts/build_hourly.py\n      - name: Step 7 archive signals + resolve real outcomes\n        run: python scripts/build_validation.py --mode close\n','close validation run')
    write(p,s)

    p='.github/workflows/intraday.yml';s=read(p)
    s=must(s,'      - "scripts/sync_live_data.py"\n','      - "scripts/sync_live_data.py"\n      - "scripts/build_validation.py"\n','intraday trigger validation')
    s=must(s,'      - name: Bridge delayed 5-minute tail with TWSE MIS snapshots\n        run: python scripts/bridge_intraday.py\n','      - name: Bridge delayed 5-minute tail with TWSE MIS snapshots\n        run: python scripts/bridge_intraday.py\n      - name: Step 7 preserve this scan for future validation\n        run: python scripts/build_validation.py --mode intraday\n','intraday validation run')
    write(p,s)


def patch_ui():
    p='docs/index.html';s=read(p)
    s=s.replace('Free Edition v1.5.27｜Step 6 個股動態門檻','Free Edition v1.5.28｜Step 7 歷史驗證校準',1)
    css='''.validationbox{background:linear-gradient(180deg,#171d27,#111720);border:1px solid #314056;border-radius:16px;padding:12px;margin:12px 0}.validationtop{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.validationtitle{font-size:16px;font-weight:900}.validationbadge{font-size:10px;font-weight:900;padding:5px 8px;border-radius:999px;background:#40300f;color:#ffd477}.validationbadge.active{background:#173527;color:#a5efbf}.validationgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin-top:9px}.validationitem{background:#0e141c;border:1px solid #293442;border-radius:10px;padding:8px}.validationv{font-size:13px;font-weight:900}.validationl{font-size:9px;color:var(--muted);margin-top:3px}.validationnote{font-size:9px;color:var(--muted);line-height:1.5;margin-top:8px}.validationweights{font-size:10px;color:#cfe2f7;margin-top:8px;line-height:1.6}'''
    if '.validationbox{' not in s:s=must(s,'</style>',css+'\n</style>','validation css')
    s=must(s,'<div id="changebox"></div>','<div id="validationbox"></div>\n<div id="changebox"></div>','validation box')
    s=s.replace('let mode="intraday",filter="all",watchOnly=false,portfolioOnly=false,portfolioData={},universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[],changeRadar={};','let mode="intraday",filter="all",watchOnly=false,portfolioOnly=false,portfolioData={},universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[],changeRadar={},validationReport={};',1)
    marker='function updateFooter(){'
    fn=r'''function validationHTML(){
 const v=validationReport||{},c=v.calibration||{};
 if(!v.version)return `<div class="validationtop"><div><div class="validationtitle">🧪 Step 7 歷史驗證</div><div class="sub">歷史樣本開始累積</div></div><span class="validationbadge">暖機中</span></div>`;
 const active=!!c.active,w=c.active_weights||c.baseline_weights||{};
 const h=v.high_quality_5d||{};
 return `<div class="validationtop"><div><div class="validationtitle">🧪 Step 7｜真實結果校準</div><div class="sub">1／3／5／10日＋10日 MFE／MAE｜只用已發生結果</div></div><span class="validationbadge ${active?"active":""}">${active?"✅ 校準啟用":"🟡 暖機中"}</span></div><div class="validationgrid"><div class="validationitem"><div class="validationv">${v.close_snapshot_days??0} 日</div><div class="validationl">盤後快照</div></div><div class="validationitem"><div class="validationv">${c.sample_rows??0} / ${c.minimum_rows??3000}</div><div class="validationl">成熟校準樣本</div></div><div class="validationitem"><div class="validationv">${c.sample_dates??0} / ${c.minimum_dates??15}</div><div class="validationl">成熟交易日</div></div><div class="validationitem"><div class="validationv">${h.n?num(h.win_rate,1)+"%":"—"}</div><div class="validationl">70分↑訊號 5日正報酬率（${h.n||0}筆）</div></div></div><div class="validationweights">目前波段權重：技術 ${num(w.technical??50,1)}｜籌碼 ${num(w.chip??25,1)}｜族群 ${num(w.sector??15,1)}｜流動性 ${num(w.liquidity??10,1)}</div><div class="validationnote">${escHTML(c.guardrail||v.note||"樣本不足時正式權重維持50/25/15/10。")}</div>`;
}
'''
    if 'function validationHTML()' not in s:s=must(s,marker,fn+marker,'validation ui fn')

    # Guide: Step 7 section before the former final quick-start section.
    guide_old='<div class="guide-title">⑰ 第一次使用，照這個順序最快</div>'
    guide_new='''<div class="guide-title">⑰ Step 7｜歷史驗證：讓分數接受真實結果檢驗</div>\n    <div class="guide-card">\n      <div class="guide-line"><span class="guide-key">保存當時狀態</span>：每個盤後快照保存分數、Stage、族群、市場、籌碼與四大波段 component；盤中每次掃描保存高資訊候選。</div>\n      <div class="guide-line"><span class="guide-key">真實 Outcome</span>：等未來交易日實際發生後，才計算 1／3／5／10 日報酬與 10 日 MFE／MAE；未成熟的 horizon 不會當成 0。</div>\n      <div class="guide-line"><span class="guide-key">權重校準</span>：用 5 日相對報酬檢查技術／籌碼／族群／流動性 component 的有效性；至少 15 個成熟交易日、3000 筆成熟樣本後，下一輪才啟用受限幅校準。</div>\n      <div class="guide-tip">盤中歷史只保存與驗證，不參與波段權重校準；Step 8 的當沖模式也會另做，避免邏輯互相污染。</div>\n    </div>\n\n    <div class="guide-title">⑱ 第一次使用，照這個順序最快</div>'''
    if guide_old in s:s=s.replace(guide_old,guide_new,1)

    old='''  const [u,c,i,s,m]=await Promise.all([\n   fetch("./data/universe.json?"+bust),fetch("./data/close.json?"+bust),\n   fetch("./data/intraday.json?"+bust),fetch("./data/status.json?"+bust),\n   fetch("./data/market.json?"+bust)\n  ]);\n  universe=await u.json();let cj=await c.json(),ij=await i.json(),sj=await s.json();\n'''
    new='''  const [u,c,i,s,m,v]=await Promise.all([\n   fetch("./data/universe.json?"+bust),fetch("./data/close.json?"+bust),\n   fetch("./data/intraday.json?"+bust),fetch("./data/status.json?"+bust),\n   fetch("./data/market.json?"+bust),fetch("./data/validation.json?"+bust)\n  ]);\n  universe=await u.json();let cj=await c.json(),ij=await i.json(),sj=await s.json();validationReport=await v.json();\n'''
    s=must(s,old,new,'load validation')
    s=must(s,'$("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();$("changebox").innerHTML=changeRadarHTML();render();','$("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();$("validationbox").innerHTML=validationHTML();$("rotationbox").innerHTML=rotationHTML();$("changebox").innerHTML=changeRadarHTML();render();','render validation')
    s=s.replace('./hourly.js?v=1527','./hourly.js?v=1528').replace('./sw.js?v=1527','./sw.js?v=1528').replace('dogsonSwReloaded1527','dogsonSwReloaded1528')
    write(p,s)


def patch_sw_status_init():
    p='docs/sw.js';s=read(p).replace('dogson-free-v1527','dogson-free-v1528').replace('./hourly.js?v=1527','./hourly.js?v=1528');write(p,s)
    p='docs/data/status.json';d=json.loads(read(p));d['version']='1.5.28-free';d['validation_version']='1.0';write(p,json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
    vp=ROOT/'docs/data/validation.json'
    if not vp.exists():
        write('docs/data/validation.json',json.dumps({"version":"1.0","updated_at":None,"close_snapshot_days":0,"intraday_scan_snapshots":0,"outcome_rows":0,"matured_5d_rows":0,"high_quality_5d":{"n":0,"win_rate":None,"median_return":None,"avg_return":None},"stage_5d":{},"calibration":{"version":"1.0","active":False,"status":"warming","sample_rows":0,"sample_dates":0,"minimum_rows":3000,"minimum_dates":15,"baseline_weights":{"technical":50.0,"chip":25.0,"sector":15.0,"liquidity":10.0},"suggested_weights":{"technical":50.0,"chip":25.0,"sector":15.0,"liquidity":10.0},"active_weights":{"technical":50.0,"chip":25.0,"sector":15.0,"liquidity":10.0},"guardrail":"樣本不足不改正式分；盤中資料不參與波段權重校準。"},"recent_matured_signals":[],"horizons":[1,3,5,10],"mfe_mae_window":10,"note":"Step 7 已啟用，等待未來交易日累積真實 outcome。"},ensure_ascii=False,separators=(',',':'))+'\n')
    hp=ROOT/'docs/data/validation_history.json'
    if not hp.exists():write('docs/data/validation_history.json','{"version":"1.0","close":[],"intraday":[]}\n')

if __name__=='__main__':
    patch_build_data();patch_validation();patch_sync();patch_workflows();patch_ui();patch_sw_status_init();print('v1.5.28 Step 7 validation applied')
