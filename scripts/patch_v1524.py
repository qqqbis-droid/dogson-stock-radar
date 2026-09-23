#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.24 — Step 5：多時間框架（5分＋60分＋日K）。

目標：
- 正式把既有 60K 20T／60T 結構接進盤中 Stage / Entry Decision。
- 60K 與日K只作決策上下文，不新增盤中100分或盤後100分權重。
- 保留「金叉前夕／初升／穩定續航／加速續航」，已金叉一段仍可辨識。
- 恢復首頁載入既有 hourly.js，讓60K資料不再成為孤島。
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
        raise SystemExit(f"v1.5.24 missing marker: {label}")
    return text.replace(old, new, count)


MTF_HELPERS = r'''
def _attach_multitimeframe_context(rows, close_map, hourly_obj):
    """Attach 5m + prior completed 60m + daily context without changing any score weight."""
    if not rows:
        return rows
    hourly_rows = (hourly_obj or {}).get("all_rows") or (hourly_obj or {}).get("rows") or []
    hmap = {str(x.get("code")): x for x in hourly_rows if isinstance(x, dict) and x.get("code")}

    def fv(obj, key, default=0.0):
        try:
            v = obj.get(key)
            return float(v) if v is not None else float(default)
        except Exception:
            return float(default)

    for r in rows:
        code = str(r.get("code") or "")
        h = hmap.get(code) or {}
        d = (close_map or {}).get(code) or {}

        close = fv(r, "close")
        vwap = fv(r, "vwap")
        ret15 = fv(r, "ret15")
        five_bull = bool(vwap > 0 and close >= vwap and (r.get("trend5") or r.get("break3") or r.get("break12")))
        five_bear = bool(vwap > 0 and close < vwap and not r.get("trend5") and ret15 < 0)
        five_state = "BULLISH" if five_bull else "BEARISH" if five_bear else "NEUTRAL"

        h_available = bool(h and h.get("data_status") == "OK")
        hcat = str(h.get("category60") or "")
        dir20 = str(h.get("dir20") or "")
        dir60 = str(h.get("dir60") or "")
        h_ma20 = fv(h, "ma20_60")
        h_ma60 = fv(h, "ma60_60")
        h_price = fv(h, "price")
        if not h_available:
            h_state = "UNAVAILABLE"
        elif hcat in {"PRE_CROSS", "EARLY", "STABLE_CONT", "ACCEL_CONT"}:
            h_state = hcat
        elif dir20 == "DOWN" and dir60 == "DOWN" and (not h_ma20 or h_price < h_ma20):
            h_state = "BEARISH"
        elif dir20 == "UP" and dir60 == "UP" and h_ma20 > h_ma60:
            h_state = "BULLISH"
        elif dir20 == "UP" and dir60 in {"UP", "FLAT"}:
            h_state = "IMPROVING"
        else:
            h_state = "NEUTRAL"
        h_supportive = h_state in {"PRE_CROSS", "EARLY", "STABLE_CONT", "ACCEL_CONT", "BULLISH", "IMPROVING"}
        h_bearish = h_state == "BEARISH"

        dclose = fv(d, "close")
        dma20 = fv(d, "ma20")
        dma5 = fv(d, "ma5")
        dma10 = fv(d, "ma10")
        dcat = str(d.get("category") or "")
        daily_weak = bool(
            dcat in {"轉弱警戒", "結構失效"}
            or (dma20 > 0 and dclose < dma20 and dma5 > 0 and dma10 > 0 and dma5 < dma10)
        )
        daily_bull = bool(
            not daily_weak and (
                d.get("trend") or d.get("break20")
                or (dma20 > 0 and dclose >= dma20 and dma5 > 0 and dma10 > 0 and dma5 >= dma10)
            )
        )
        daily_state = "WEAK" if daily_weak else "BULLISH" if daily_bull else "NEUTRAL"

        if five_bull and h_supportive and not daily_weak:
            state = "ALIGNED"
        elif h_state in {"PRE_CROSS", "IMPROVING"} and not daily_weak:
            state = "SETUP"
        elif five_bull and h_bearish:
            state = "CONFLICT"
        elif h_bearish and daily_weak:
            state = "WEAK"
        elif h_supportive and not daily_weak:
            state = "SUPPORTIVE"
        else:
            state = "MIXED"

        labels = {
            "ALIGNED": "三框共振",
            "SETUP": "60K蓄勢／等5分觸發",
            "SUPPORTIVE": "60K＋日K支持",
            "CONFLICT": "5分轉強但60K未跟上",
            "WEAK": "60K＋日K偏弱",
            "MIXED": "框架混合／等確認",
        }
        hlabels = {
            "PRE_CROSS": "20T/60T金叉前夕",
            "EARLY": "20T/60T初升金叉",
            "STABLE_CONT": "20T/60T穩定續航",
            "ACCEL_CONT": "20T/60T加速續航",
            "BULLISH": "20T/60T多頭",
            "IMPROVING": "20T轉上／60T改善",
            "BEARISH": "20T/60T偏弱",
            "NEUTRAL": "20T/60T中性",
            "UNAVAILABLE": "60K資料待補",
        }
        dlabels = {"BULLISH": "日K偏多", "WEAK": "日K偏弱", "NEUTRAL": "日K中性"}
        flabels = {"BULLISH": "5分轉強", "BEARISH": "5分轉弱", "NEUTRAL": "5分等待"}

        r["multi_timeframe"] = {
            "version": "1.0",
            "state": state,
            "label": labels[state],
            "5m": {
                "state": five_state,
                "label": flabels[five_state],
                "above_vwap": bool(vwap > 0 and close >= vwap),
                "trend5": bool(r.get("trend5")),
                "break3": bool(r.get("break3")),
                "break12": bool(r.get("break12")),
            },
            "60m": {
                "available": h_available,
                "state": h_state,
                "label": hlabels[h_state],
                "category": hcat or None,
                "ma20": h.get("ma20_60"),
                "ma60": h.get("ma60_60"),
                "dir20": h.get("dir20"),
                "dir60": h.get("dir60"),
                "gap20_60_pct": h.get("gap20_60_pct"),
                "cross_age": h.get("cross_age"),
                "price_vs20_pct": h.get("price_vs20_60_pct"),
                "supportive": h_supportive,
                "bearish": h_bearish,
                "source_trade_date": (hourly_obj or {}).get("trade_date"),
            },
            "daily": {
                "state": daily_state,
                "label": dlabels[daily_state],
                "stage": dcat or None,
                "ma5": d.get("ma5"),
                "ma10": d.get("ma10"),
                "ma20": d.get("ma20"),
                "dist20": d.get("dist20"),
                "trend": bool(d.get("trend")),
                "break20": bool(d.get("break20")),
                "source_date": d.get("date"),
            },
            "score_weight": 0,
            "note": "多時間框架只作Stage/進場決策確認，不新增100分權重",
        }
    return rows

'''


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)
    s = s.replace("犬子老師飆股雷達 Free Edition v1.5.17", "犬子老師飆股雷達 Free Edition v1.5.24", 1)

    if "def _attach_multitimeframe_context(rows, close_map, hourly_obj):" not in s:
        s = must(s, "def build_intraday():", MTF_HELPERS + "def build_intraday():", "MTF helper insertion")

    old = '''        near_vwap = bool(vwap > 0 and close >= vwap * 0.995 and close <= vwap * 1.02)\n\n        invalid_flags = ['''
    new = '''        near_vwap = bool(vwap > 0 and close >= vwap * 0.995 and close <= vwap * 1.02)\n        mtf = r.get("multi_timeframe") or {}\n        mtf60 = mtf.get("60m") or {}\n        mtfd = mtf.get("daily") or {}\n        mtf_60_available = bool(mtf60.get("available"))\n        mtf_60_state = str(mtf60.get("state") or "")\n        mtf_60_supportive = bool(mtf60.get("supportive"))\n        mtf_60_bearish = bool(mtf60.get("bearish"))\n        mtf_daily_weak = str(mtfd.get("state") or "") == "WEAK"\n        mtf_daily_supportive = str(mtfd.get("state") or "") == "BULLISH"\n\n        invalid_flags = ['''
    s = must(s, old, new, "Stage reads MTF")

    s = must(
        s,
        '''            and (trend5 or break12 or tech >= 22)\n        )''',
        '''            and (trend5 or break12 or tech >= 22)\n            and not (mtf_60_available and mtf_60_bearish)\n        )''',
        "launch 60K conflict gate",
    )
    s = must(
        s,
        '''            r["stage_signals"] = ["3K突破", "站上VWAP", f"量速{pace:.1f}x", f"相對市場{rel:+.1f}%"]''',
        '''            launch_signals = ["3K突破", "站上VWAP", f"量速{pace:.1f}x", f"相對市場{rel:+.1f}%"]\n            if mtf_60_supportive:\n                launch_signals.append(f"60K {mtf60.get('label') or '20T/60T支持'}")\n            if mtf_daily_supportive:\n                launch_signals.append("日K背景偏多")\n            r["stage_signals"] = launch_signals[:5]''',
        "launch MTF evidence",
    )
    s = must(
        s,
        '''            score >= 70 and above_vwap and rel >= 0\n            and (trend5 or break12)''',
        '''            score >= 70 and above_vwap and rel >= 0\n            and (trend5 or break12)\n            and not (mtf_60_available and mtf_60_bearish)''',
        "trend hold 60K gate",
    )
    s = must(
        s,
        '''            (-0.5 <= ret15 <= 1.5, "15分鐘未急拉急殺"),\n        ]\n        setup_hits = [txt for ok, txt in setup_flags if ok]\n        if not break3 and score >= 55 and len(setup_hits) >= 4:''',
        '''            (-0.5 <= ret15 <= 1.5, "15分鐘未急拉急殺"),\n            (mtf_60_supportive, f"60K {mtf60.get('label') or '20T/60T結構支持'}"),\n            (mtf_daily_supportive, "日K背景仍支持"),\n        ]\n        setup_hits = [txt for ok, txt in setup_flags if ok]\n        mtf_setup_ok = (not mtf_60_available) or mtf_60_supportive or mtf_60_state == "PRE_CROSS"\n        if not break3 and score >= 55 and len(setup_hits) >= 4 and mtf_setup_ok:''',
        "setup MTF evidence",
    )
    s = must(
        s,
        '''            (not trend5, "5分短均未維持多頭"),\n        ]''',
        '''            (not trend5, "5分短均未維持多頭"),\n            (mtf_60_available and mtf_60_bearish, "60K 20T/60T結構偏弱"),\n            (mtf_daily_weak, "日K背景偏弱"),\n        ]''',
        "weak MTF evidence",
    )

    s = must(
        s,
        '''    market_live = intraday_index_snapshot()\n    sector_rotation = build_sector_rotation(rows)''',
        '''    hourly_obj = load_json("hourly.json", {})\n    rows = _attach_multitimeframe_context(rows, close_map, hourly_obj)\n\n    market_live = intraday_index_snapshot()\n    sector_rotation = build_sector_rotation(rows)''',
        "attach MTF before scoring",
    )
    s = must(
        s,
        '''        "score_formula": {"mode": "intraday_execution", "price_structure": 30, "flow_volume": 25, "relative_strength": 15, "sector": 20, "liquidity_risk": 10, "amplitude_efficiency": "inside_flow_and_liquidity_risk_no_new_weight", "chip": "background_only", "market_separate": 15},\n        "rows": rows,''',
        '''        "multi_timeframe_version": "1.0",\n        "score_formula": {"mode": "intraday_execution", "price_structure": 30, "flow_volume": 25, "relative_strength": 15, "sector": 20, "liquidity_risk": 10, "amplitude_efficiency": "inside_flow_and_liquidity_risk_no_new_weight", "multi_timeframe": "decision_context_no_new_weight", "chip": "background_only", "market_separate": 15},\n        "rows": rows,''',
        "intraday root MTF marker",
    )
    s = s.replace('"version": "1.5.1-free"', '"version": "1.5.24-free"')
    s = must(
        s,
        '''        "intraday_count": len(rows),\n        "version": "1.5.24-free",''',
        '''        "intraday_count": len(rows),\n        "version": "1.5.24-free",\n        "multi_timeframe_version": "1.0",''',
        "status MTF version",
    )
    write(p, s)


def patch_bridge():
    p = "scripts/bridge_intraday.py"
    s = read(p)
    s = must(
        s,
        '''    close_obj = bd.load_json("close.json", {"rows": []})\n    close_market = bd.load_json("market.json", close_obj.get("market", {}))''',
        '''    close_obj = bd.load_json("close.json", {"rows": []})\n    close_map = {str(r.get("code")): r for r in (close_obj.get("rows") or []) if r.get("code")}\n    close_market = bd.load_json("market.json", close_obj.get("market", {}))''',
        "bridge close map",
    )
    s = must(
        s,
        '''    out_rows = list(by_code.values())\n    market_live = bd.intraday_index_snapshot()''',
        '''    out_rows = list(by_code.values())\n    out_rows = bd._attach_multitimeframe_context(out_rows, close_map, bd.load_json("hourly.json", {}))\n    market_live = bd.intraday_index_snapshot()''',
        "bridge refresh MTF",
    )
    s = must(
        s,
        '''        "change_radar": change_radar,\n        "rows": out_rows,''',
        '''        "change_radar": change_radar,\n        "multi_timeframe_version": "1.0",\n        "rows": out_rows,''',
        "bridge MTF root marker",
    )
    s = must(
        s,
        '''        "change_radar_version": "1.0",\n    })''',
        '''        "change_radar_version": "1.0",\n        "multi_timeframe_version": "1.0",\n        "version": "1.5.24-free",\n    })''',
        "bridge status MTF marker",
    )
    write(p, s)


def patch_index():
    p = "docs/index.html"
    s = read(p)
    s = must(
        s,
        "Free Edition v1.5.23｜庫存模式＋盤中進場三燈",
        "Free Edition v1.5.24｜Step 5 多時間框架",
        "version header",
    )

    css = r'''
/* v1.5.24 Step 5 multi-timeframe */
.mtfbox{margin-top:10px;border:1px solid #344760;background:linear-gradient(180deg,#111a26,#0e151f);border-radius:13px;padding:10px}.mtftop{display:flex;justify-content:space-between;gap:8px;align-items:center}.mtftitle{font-size:11px;color:#9ba5b6;font-weight:850}.mtflabel{font-size:12px;font-weight:900;color:#b9ddff}.mtfgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}.mtfcell{background:#0d141d;border:1px solid #29384b;border-radius:10px;padding:8px}.mtfcellv{font-size:11px;font-weight:900}.mtfcelll{font-size:9px;color:#9ba5b6;margin-top:3px;line-height:1.45}.mtfnote{font-size:9px;color:#7f8b9d;margin-top:7px;line-height:1.45}@media(max-width:520px){.mtfgrid{grid-template-columns:1fr}.mtfcell{padding:7px 8px}}
'''
    if ".mtfbox{" not in s:
        s = must(s, "</style>", css + "\n</style>", "MTF css")

    guide_old = '    <div class="guide-title">⑯ 第一次使用，照這個順序最快</div>'
    guide_new = '''    <div class="guide-title">⑯ Step 5｜多時間框架：5分＋60分＋日K要互相確認</div>
    <div class="guide-card">
      <div class="guide-line"><span class="guide-key">5分K</span>：負責「現在」的觸發，包含 VWAP、短均、突破與即時動能。</div>
      <div class="guide-line"><span class="guide-key">60分K 20T／60T</span>：負責波段骨架。正式辨識金叉前夕、初升金叉、已金叉穩定續航、加速續航，以及20T／60T轉弱。</div>
      <div class="guide-line"><span class="guide-key">日K</span>：負責大方向，確認均線與波段背景是否仍支持。</div>
      <div class="guide-line"><span class="guide-key">三框共振</span>：5分觸發＋60K結構支持＋日K沒有轉弱，才是最完整的波段進場背景。</div>
      <div class="guide-tip">60K 20T／60T不新增總分權重，而是正式接進 Stage 與盤中三燈。已黃金交叉一段、只要20T／60T斜率仍向上，也會保留為「穩定／加速續航」，不會因為不是剛金叉就被排除。</div>
    </div>

    <div class="guide-title">⑰ 第一次使用，照這個順序最快</div>'''
    s = must(s, guide_old, guide_new, "MTF help")

    mtf_js = r'''
function mtfArrow(v){return v==="UP"?"↗":v==="DOWN"?"↘":v==="FLAT"?"→":"—"}
function mtfHTML(r){
 if(mode!=="intraday")return "";
 const m=r?.multi_timeframe||{};
 if(!m.version)return `<div class="mtfbox"><div class="mtftop"><div class="mtftitle">🧭 Step 5｜多時間框架</div><div class="mtflabel">等待新一輪盤中資料</div></div><div class="mtfnote">5分＋60分＋日K連動會在盤中資料更新後顯示。</div></div>`;
 const f=m["5m"]||{},h=m["60m"]||{},d=m.daily||{};
 const hma=(h.available&&h.ma20!==null&&h.ma20!==undefined)?`20T ${num(h.ma20,2)} ${mtfArrow(h.dir20)}｜60T ${num(h.ma60,2)} ${mtfArrow(h.dir60)}`:"60K資料待補";
 const cross=h.available?(h.state==="PRE_CROSS"?"金叉前夕":Number.isFinite(+h.cross_age)?`金叉約 ${num(h.cross_age,0)} 根`:(h.supportive?"已金叉／結構向上":"尚未形成多頭")):"";
 const dailyMA=(d.ma20!==null&&d.ma20!==undefined)?`20MA ${num(d.ma20,2)}｜距20MA ${signed(d.dist20,1)}`:"日K資料待補";
 return `<div class="mtfbox"><div class="mtftop"><div class="mtftitle">🧭 Step 5｜5分＋60分＋日K</div><div class="mtflabel">${m.label||"框架確認"}</div></div><div class="mtfgrid"><div class="mtfcell"><div class="mtfcellv">${f.label||"5分等待"}</div><div class="mtfcelll">VWAP ${f.above_vwap?"上":"下"}｜3K ${f.break3?"突破":"未突破"}｜短均 ${f.trend5?"多頭":"未確認"}</div></div><div class="mtfcell"><div class="mtfcellv">${h.label||"60K待補"}</div><div class="mtfcelll">${hma}${cross?`<br>${cross}｜20/60差 ${h.gap20_60_pct===null||h.gap20_60_pct===undefined?"—":signed(h.gap20_60_pct,2)}`:""}</div></div><div class="mtfcell"><div class="mtfcellv">${d.label||"日K中性"}</div><div class="mtfcelll">${dailyMA}<br>${d.stage?`前收生命週期：${d.stage}`:"以前一完成交易日日K為背景"}</div></div></div><div class="mtfnote">多時間框架是決策確認層，權重＝0；不改盤中100分，也不改盤後波段100分。</div></div>`;
}

'''
    if "function mtfHTML(r)" not in s:
        s = must(s, "function srHTML(r){", mtf_js + "function srHTML(r){", "MTF frontend function")

    s = must(
        s,
        ''' const marketMode=String(mkt?.market_mode||"—"),marketScore=+(mkt?.market_score??0);\n const good=[],wait=[],block=[];''',
        ''' const marketMode=String(mkt?.market_mode||"—"),marketScore=+(mkt?.market_score??0);\n const mtf=r?.multi_timeframe||{},mtfState=String(mtf.state||""),mtf60=mtf["60m"]||{};\n const good=[],wait=[],block=[];''',
        "entry reads MTF",
    )
    s = must(
        s,
        ''' if(stage==="轉弱警戒")wait.push("Stage 仍在轉弱警戒，需等5分K重新轉強");\n\n const marketWeak=''',
        ''' if(stage==="轉弱警戒")wait.push("Stage 仍在轉弱警戒，需等5分K重新轉強");\n if(mtfState==="ALIGNED")good.push("5分＋60分＋日K三框共振");\n else if(mtfState==="SETUP")wait.unshift("60K 20T/60T蓄勢，等5分正式觸發");\n else if(mtfState==="CONFLICT")wait.unshift("5分已轉強，但60K 20T/60T尚未跟上");\n else if(mtfState==="WEAK")wait.unshift("60K＋日K偏弱，先不急進");\n else if(mtf60.available)wait.push("多時間框架尚未完全共振");\n else wait.push("60K資料待補，不因缺資料自動判空");\n\n const mtfGreenOk=!mtf60.available||mtfState==="ALIGNED"||(mtfState==="SETUP"&&(r.break3||stage==="剛啟動"));\n const marketWeak=''',
        "entry MTF checklist",
    )
    s = must(
        s,
        ''' const coreGreen=score>=70&&ps>=20&&flow>=14&&rel>=8&&sec>=8&&liq>=6&&vwap>=-.5&&vwap<=2.5&&pos>=45&&pos<=90&&stage!=="轉弱警戒";''',
        ''' const coreGreen=score>=70&&ps>=20&&flow>=14&&rel>=8&&sec>=8&&liq>=6&&vwap>=-.5&&vwap<=2.5&&pos>=45&&pos<=90&&stage!=="轉弱警戒"&&mtfGreenOk;''',
        "entry green MTF gate",
    )
    s = must(
        s,
        '''<span>20T/60T 不另加權</span></div><div class="entrywhy">''',
        '''<span>60K ${r?.multi_timeframe?.["60m"]?.label||"待補"}</span><span>20T/60T 權重＝0</span></div><div class="entrywhy">''',
        "entry MTF display",
    )
    s = must(
        s,
        '''  ${stageExplainHTML(r)}\n  ${entryDecisionHTML(r)}\n  ${portfolioHTML(r)}''',
        '''  ${stageExplainHTML(r)}\n  ${mtfHTML(r)}\n  ${entryDecisionHTML(r)}\n  ${portfolioHTML(r)}''',
        "MTF card placement",
    )

    if '<script src="./hourly.js?v=1524"></script>' not in s:
        s = must(
            s,
            '<script src="./realtime-config.js?v=151"></script>',
            '<script src="./hourly.js?v=1524"></script>\n<script src="./realtime-config.js?v=151"></script>',
            "load hourly UI",
        )
    s = s.replace('./sw.js?v=1523', './sw.js?v=1524')
    s = s.replace('dogsonSwReloaded1523', 'dogsonSwReloaded1524')
    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = must(s, "dogson-free-v1523", "dogson-free-v1524", "SW cache")
    if "./hourly.js?v=1524" not in s:
        s = must(
            s,
            "'./manifest.webmanifest','./realtime-config.js?v=151','./realtime.js?v=151'",
            "'./manifest.webmanifest','./hourly.js?v=1524','./realtime-config.js?v=151','./realtime.js?v=151'",
            "cache hourly asset",
        )
    write(p, s)


def decorate_static_row(r, close_map, hmap, hourly_trade_date):
    def fv(obj, key, default=0.0):
        try:
            v = obj.get(key)
            return float(v) if v is not None else float(default)
        except Exception:
            return float(default)
    code = str(r.get("code") or "")
    h = hmap.get(code) or {}
    d = close_map.get(code) or {}
    close, vwap, ret15 = fv(r,"close"), fv(r,"vwap"), fv(r,"ret15")
    five_bull = bool(vwap > 0 and close >= vwap and (r.get("trend5") or r.get("break3") or r.get("break12")))
    five_bear = bool(vwap > 0 and close < vwap and not r.get("trend5") and ret15 < 0)
    fs = "BULLISH" if five_bull else "BEARISH" if five_bear else "NEUTRAL"
    hav = bool(h and h.get("data_status") == "OK")
    hc = str(h.get("category60") or "")
    d20,d60=str(h.get("dir20") or ""),str(h.get("dir60") or "")
    if not hav: hs="UNAVAILABLE"
    elif hc in {"PRE_CROSS","EARLY","STABLE_CONT","ACCEL_CONT"}: hs=hc
    elif d20=="DOWN" and d60=="DOWN": hs="BEARISH"
    elif d20=="UP" and d60=="UP" and fv(h,"ma20_60")>fv(h,"ma60_60"): hs="BULLISH"
    elif d20=="UP" and d60 in {"UP","FLAT"}: hs="IMPROVING"
    else: hs="NEUTRAL"
    hsup=hs in {"PRE_CROSS","EARLY","STABLE_CONT","ACCEL_CONT","BULLISH","IMPROVING"}; hbear=hs=="BEARISH"
    dcat=str(d.get("category") or ""); dc=fv(d,"close"); dm20=fv(d,"ma20"); dm5=fv(d,"ma5"); dm10=fv(d,"ma10")
    dw=bool(dcat in {"轉弱警戒","結構失效"} or (dm20>0 and dc<dm20 and dm5>0 and dm10>0 and dm5<dm10))
    db=bool(not dw and (d.get("trend") or d.get("break20") or (dm20>0 and dc>=dm20 and dm5>0 and dm10>0 and dm5>=dm10)))
    ds="WEAK" if dw else "BULLISH" if db else "NEUTRAL"
    if five_bull and hsup and not dw: state="ALIGNED"
    elif hs in {"PRE_CROSS","IMPROVING"} and not dw: state="SETUP"
    elif five_bull and hbear: state="CONFLICT"
    elif hbear and dw: state="WEAK"
    elif hsup and not dw: state="SUPPORTIVE"
    else: state="MIXED"
    labels={"ALIGNED":"三框共振","SETUP":"60K蓄勢／等5分觸發","SUPPORTIVE":"60K＋日K支持","CONFLICT":"5分轉強但60K未跟上","WEAK":"60K＋日K偏弱","MIXED":"框架混合／等確認"}
    hl={"PRE_CROSS":"20T/60T金叉前夕","EARLY":"20T/60T初升金叉","STABLE_CONT":"20T/60T穩定續航","ACCEL_CONT":"20T/60T加速續航","BULLISH":"20T/60T多頭","IMPROVING":"20T轉上／60T改善","BEARISH":"20T/60T偏弱","NEUTRAL":"20T/60T中性","UNAVAILABLE":"60K資料待補"}
    fl={"BULLISH":"5分轉強","BEARISH":"5分轉弱","NEUTRAL":"5分等待"}; dl={"BULLISH":"日K偏多","WEAK":"日K偏弱","NEUTRAL":"日K中性"}
    r["multi_timeframe"]={"version":"1.0","state":state,"label":labels[state],"5m":{"state":fs,"label":fl[fs],"above_vwap":bool(vwap>0 and close>=vwap),"trend5":bool(r.get("trend5")),"break3":bool(r.get("break3")),"break12":bool(r.get("break12"))},"60m":{"available":hav,"state":hs,"label":hl[hs],"category":hc or None,"ma20":h.get("ma20_60"),"ma60":h.get("ma60_60"),"dir20":h.get("dir20"),"dir60":h.get("dir60"),"gap20_60_pct":h.get("gap20_60_pct"),"cross_age":h.get("cross_age"),"price_vs20_pct":h.get("price_vs20_60_pct"),"supportive":hsup,"bearish":hbear,"source_trade_date":hourly_trade_date},"daily":{"state":ds,"label":dl[ds],"stage":dcat or None,"ma5":d.get("ma5"),"ma10":d.get("ma10"),"ma20":d.get("ma20"),"dist20":d.get("dist20"),"trend":bool(d.get("trend")),"break20":bool(d.get("break20")),"source_date":d.get("date")},"score_weight":0,"note":"多時間框架只作Stage/進場決策確認，不新增100分權重"}


def patch_current_data():
    intra_p = ROOT / "docs/data/intraday.json"
    close_p = ROOT / "docs/data/close.json"
    hourly_p = ROOT / "docs/data/hourly.json"
    status_p = ROOT / "docs/data/status.json"
    if intra_p.exists() and close_p.exists() and hourly_p.exists():
        intra=json.loads(intra_p.read_text(encoding="utf-8")); close=json.loads(close_p.read_text(encoding="utf-8")); hourly=json.loads(hourly_p.read_text(encoding="utf-8"))
        cmap={str(x.get("code")):x for x in close.get("rows",[]) if isinstance(x,dict) and x.get("code")}
        hrows=hourly.get("all_rows") or hourly.get("rows") or []
        hmap={str(x.get("code")):x for x in hrows if isinstance(x,dict) and x.get("code")}
        for r in intra.get("rows",[]):
            if isinstance(r,dict): decorate_static_row(r,cmap,hmap,hourly.get("trade_date"))
        intra["multi_timeframe_version"]="1.0"
        sf=intra.setdefault("score_formula",{})
        sf["multi_timeframe"]="decision_context_no_new_weight"
        intra_p.write_text(json.dumps(intra,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    if status_p.exists():
        st=json.loads(status_p.read_text(encoding="utf-8"));st["version"]="1.5.24-free";st["multi_timeframe_version"]="1.0"
        status_p.write_text(json.dumps(st,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")


if __name__ == "__main__":
    patch_build_data()
    patch_bridge()
    patch_index()
    patch_sw()
    patch_current_data()
    print("v1.5.24 Step 5 multi-timeframe patch applied")
