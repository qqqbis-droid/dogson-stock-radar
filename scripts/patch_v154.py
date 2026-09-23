#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install Dogson Radar v1.5.4.

v1.5.4 focuses on the swing-entry layer:
- MA20 / MA60 fresh golden cross + continuing golden-cross trend
- entry-light labels that reuse the existing stage classification
- explicit stock-quality vs market-environment fields
- market environment remains a gate/label and never enters the stock 100 score
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
        raise SystemExit(f"v1.5.4 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)

    s = s.replace("犬子老師飆股雷達 Free Edition v1.5.3", "犬子老師飆股雷達 Free Edition v1.5.4", 1)
    s = s.replace("犬子老師飆股雷達 Free Edition v1.5.1", "犬子老師飆股雷達 Free Edition v1.5.4", 1)

    # Daily swing radar now needs a valid 60MA.
    if "ma20_60_state" not in s:
        s = must_replace(
            s,
            '''def close_technical(x):\n    """技術分 0~50。"""\n    if len(x) < 35:\n        return None\n    c, h, v = x["Close"], x["High"], x["Volume"]\n    ma5, ma10, ma20 = c.rolling(5).mean(), c.rolling(10).mean(), c.rolling(20).mean()\n''',
            '''def close_technical(x):\n    """技術分 0~50；v1.5.4 納入 20MA/60MA 黃金交叉與多頭續航。"""\n    if len(x) < 65:\n        return None\n    c, h, v = x["Close"], x["High"], x["Volume"]\n    ma5, ma10, ma20, ma60 = c.rolling(5).mean(), c.rolling(10).mean(), c.rolling(20).mean(), c.rolling(60).mean()\n''',
            "close technical 60MA base",
        )

        s = must_replace(
            s,
            '''    p3 = h.shift(1).rolling(3).max()\n    p20 = h.shift(1).rolling(20).max()\n\n    row = {\n''',
            '''    p3 = h.shift(1).rolling(3).max()\n    p20 = h.shift(1).rolling(20).max()\n\n    ma20_now, ma60_now = float(ma20.iloc[-1]), float(ma60.iloc[-1])\n    ma20_prev, ma60_prev = float(ma20.iloc[-2]), float(ma60.iloc[-2])\n    ma20_5ago, ma60_5ago = float(ma20.iloc[-5]), float(ma60.iloc[-5])\n    ma20_slope_5d = (ma20_now / ma20_5ago - 1) * 100 if ma20_5ago else 0.0\n    ma60_slope_5d = (ma60_now / ma60_5ago - 1) * 100 if ma60_5ago else 0.0\n    ma20_60_fresh = bool(ma20_prev <= ma60_prev and ma20_now > ma60_now)\n    ma20_60_continuing = bool(\n        ma20_now > ma60_now\n        and ma20_slope_5d > 0\n        and ma60_slope_5d >= -0.10\n    )\n    if ma20_60_fresh:\n        ma20_60_state = "剛黃金交叉"\n    elif ma20_60_continuing:\n        ma20_60_state = "多頭續航"\n    elif ma20_now > ma60_now:\n        ma20_60_state = "黃金交叉但斜率轉弱"\n    else:\n        ma20_60_state = "未黃金交叉"\n    ma20_60_spread_pct = (ma20_now / ma60_now - 1) * 100 if ma60_now else 0.0\n\n    row = {\n''',
            "20/60 state calculation",
        )

        s = must_replace(
            s,
            '''        "ma5": float(ma5.iloc[-1]),\n        "ma10": float(ma10.iloc[-1]),\n        "ma20": float(ma20.iloc[-1]),\n''',
            '''        "ma5": float(ma5.iloc[-1]),\n        "ma10": float(ma10.iloc[-1]),\n        "ma20": ma20_now,\n        "ma60": ma60_now,\n        "ma20_60_state": ma20_60_state,\n        "ma20_60_fresh": ma20_60_fresh,\n        "ma20_60_continuing": ma20_60_continuing,\n        "ma20_slope_5d": round(ma20_slope_5d, 3),\n        "ma60_slope_5d": round(ma60_slope_5d, 3),\n        "ma20_60_spread_pct": round(ma20_60_spread_pct, 3),\n''',
            "20/60 row fields",
        )

        s = must_replace(
            s,
            '''    if row["trend"]:\n        score += 8; reasons.append("均線多頭")\n    if row["break3"]:\n''',
            '''    if row["trend"]:\n        score += 8; reasons.append("均線多頭")\n    if row["ma20_60_state"] == "剛黃金交叉":\n        score += 6; reasons.append("20/60黃金交叉剛形成")\n    elif row["ma20_60_state"] == "多頭續航":\n        score += 5; reasons.append("20/60黃金交叉續航")\n    elif row["ma20_60_state"] == "黃金交叉但斜率轉弱":\n        score += 1; reasons.append("20/60仍多頭但斜率轉弱")\n    if row["break3"]:\n''',
            "20/60 technical score",
        )

    # Entry-position score rewards both a new cross and an established rising cross.
    if "20/60 趨勢只加進場分" not in s:
        marker = '''    score = 40.0\n    if r.get("trend"):\n        score += 10\n'''
        repl = '''    score = 40.0\n    if r.get("trend"):\n        score += 10\n\n    # v1.5.4: 20/60 趨勢只加進場分與階段判讀；大盤仍不進個股分。\n    state2060 = str(r.get("ma20_60_state") or "")\n    if state2060 == "剛黃金交叉":\n        score += 8\n    elif state2060 == "多頭續航":\n        score += 5\n    elif state2060 == "黃金交叉但斜率轉弱":\n        score += 1\n'''
        s = must_replace(s, marker, repl, "entry score 20/60")

    # Explicitly expose market as environment/gate, never part of stock quality.
    if 'r["market_gate"]' not in s:
        marker = '''        r["market_score"] = market_score\n        r["market_mode"] = market.get("market_mode", "中性")\n        r["market_data_complete"] = bool(market.get("data_complete", True))\n'''
        repl = '''        r["market_score"] = market_score\n        r["market_env_score"] = market_score\n        r["market_mode"] = market.get("market_mode", "中性")\n        _mm = str(r["market_mode"])\n        r["market_gate"] = "順風" if _mm == "偏多" else "中性" if _mm == "中性" else "逆風" if _mm == "防守" else "資料待補"\n        r["market_data_complete"] = bool(market.get("data_complete", True))\n'''
        s = must_replace(s, marker, repl, "market gate fields")

    if 'r["quality_score"] = swing' not in s:
        marker = '''            r["score"] = swing\n            r["swing_quality_score"] = swing\n'''
        repl = '''            r["score"] = swing\n            r["quality_score"] = swing\n            r["swing_quality_score"] = swing\n'''
        s = must_replace(s, marker, repl, "quality score alias")

    # The stage light now recognises a new 20/60 cross as launch, and an established
    # rising cross as a valid trend that can remain on the pullback watch list.
    old = '''        else:\n            launch_structure = bool(\n                r.get("break20")\n                or (r.get("break3") and r.get("trend"))\n            )\n            launch = bool(\n                launch_structure\n                and r.get("vol_x", 0) >= 1.2\n                and r.get("dist20", 999) <= 12\n                and r.get("ret5", 999) <= 18\n            )\n            pullback = bool(\n                (r.get("trend") or r.get("break3") or r.get("technical_score", 0) >= 28)\n                and r.get("dist20", 999) <= 15\n                and r.get("ret5", 999) <= 22\n            )\n\n            if launch:\n                r["category"] = "剛啟動"\n                r["stage_reason"] = "20日突破" if r.get("break20") else "3日平台突破＋均線多頭"\n            elif pullback:\n                r["category"] = "等回踩"\n                r["stage_reason"] = "趨勢仍強，但較適合等支撐/均線承接"\n            else:\n                r["category"] = "觀察"\n                r["stage_reason"] = "條件尚未集中到啟動階段"\n\n    order = {"剛啟動": 0, "等回踩": 1, "觀察": 2, "過熱不追": 3}\n'''
    new = '''        else:\n            state2060 = str(r.get("ma20_60_state") or "")\n            fresh2060 = state2060 == "剛黃金交叉"\n            trend2060 = state2060 in {"剛黃金交叉", "多頭續航"}\n            launch_structure = bool(\n                r.get("break20")\n                or (r.get("break3") and r.get("trend"))\n                or fresh2060\n            )\n            launch = bool(\n                launch_structure\n                and r.get("vol_x", 0) >= (0.9 if fresh2060 else 1.2)\n                and r.get("dist20", 999) <= 12\n                and r.get("ret5", 999) <= 18\n            )\n            pullback = bool(\n                (r.get("trend") or r.get("break3") or trend2060 or r.get("technical_score", 0) >= 28)\n                and r.get("dist20", 999) <= 15\n                and r.get("ret5", 999) <= 22\n            )\n\n            if launch:\n                r["category"] = "剛啟動"\n                if fresh2060:\n                    r["stage_reason"] = "20/60黃金交叉剛形成，位階尚未過熱"\n                else:\n                    r["stage_reason"] = "20日突破" if r.get("break20") else "3日平台突破＋均線多頭"\n            elif pullback:\n                r["category"] = "等回踩"\n                if state2060 == "多頭續航":\n                    r["stage_reason"] = "20/60黃金交叉續航，等待20MA/支撐承接"\n                else:\n                    r["stage_reason"] = "趨勢仍強，但較適合等支撐/均線承接"\n            else:\n                r["category"] = "觀察"\n                r["stage_reason"] = "條件尚未集中到啟動階段"\n\n        r["entry_light"] = {\n            "剛啟動": "🟢 剛啟動",\n            "等回踩": "🟡 等回踩",\n            "過熱不追": "🔴 過熱不追",\n            "觀察": "⚪ 觀察",\n        }.get(r.get("category"), "⚪ 觀察")\n        r["entry_light_reason"] = r.get("stage_reason")\n\n    order = {"剛啟動": 0, "等回踩": 1, "觀察": 2, "過熱不追": 3}\n'''
    if 'r["entry_light"]' not in s:
        s = must_replace(s, old, new, "close entry lights")

    # Make formula/status self-describing.
    s = s.replace('"market_separate": 15}', '"market_separate": 15, "ma20_60": "technical+entry_stage"}', 1)
    s = s.replace('"version": "1.5.1-free"', '"version": "1.5.4-free"', 1)
    s = s.replace('"version": "1.5.3-free"', '"version": "1.5.4-free"', 1)

    write(p, s)


def patch_index():
    p = "docs/index.html"
    s = read(p)
    s = s.replace("Free Edition v1.5.3｜族群資金可展開＋盤後法人流向＋60K全股票資訊",
                  "Free Edition v1.5.4｜20/60續航＋進場燈號＋族群法人資金流", 1)
    s = s.replace("Free Edition v1.5.2｜盤中動能100＋盤後波段100＋60K全股票資訊",
                  "Free Edition v1.5.4｜20/60續航＋進場燈號＋族群法人資金流", 1)

    if "20/60 黃金交叉" not in s:
        help_marker = '<b>盤後波段 100：</b>波段延續＝日K技術50＋籌碼25＋族群15＋流動性10，直接加總100，不再用85分換算；另外獨立計算「進場位置100」，避免好股票在過熱位置仍被誤認為好買點。<br>'
        help_repl = help_marker + '<b>20/60 黃金交叉：</b>除了「剛黃金交叉」會加分，已經黃金交叉一段時間、20MA仍向上且60MA沒有明顯轉弱，也會標為「多頭續航」；不要求兩條均線斜率平行。這個條件會進日K技術與進場階段，但不會把大盤分數灌進個股分。<br>'
        s = must_replace(s, help_marker, help_repl, "20/60 help")

    if "大盤環境 · 不計入個股分" not in s:
        marker = '''  <div class="part"><div class="partv">${num(r.entry_position_score,0)}/100</div><div class="partl">進場位置 · 獨立</div></div>\n </div>`;'''
        repl = '''  <div class="part"><div class="partv">${num(r.entry_position_score,0)}/100</div><div class="partl">進場位置 · 獨立</div></div>\n  <div class="part"><div class="partv">${r.market_gate||"—"} · ${num(r.market_env_score??r.market_score,1)}/15</div><div class="partl">大盤環境 · 不計入個股分</div></div>\n </div>`;'''
        s = must_replace(s, marker, repl, "market gate UI")

    if '"20/60狀態"' not in s:
        old = 'return [["收盤",num(r.close,2)],["日量比",num(r.vol_x,1)+"x"],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["距20MA",signed(r.dist20,1)],["5日漲幅",signed(r.ret5,1)],["20日漲幅",signed(r.ret20,1)],["RSI",num(r.rsi,0)],["5MA",num(r.ma5,2)],["10MA",num(r.ma10,2)],["20MA",num(r.ma20,2)],["20日突破",r.break20?"是":"否"],["均線多頭",r.trend?"是":"否"],["族群共振",(r.sector_score_label?((r.sector_hot_count||0)+"檔 · "+r.sector_score_label+(r.sector_score_source==="官方產業代理"?"（產業代理）":"")):"待分類")]];'
        new = 'return [["收盤",num(r.close,2)],["日量比",num(r.vol_x,1)+"x"],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["距20MA",signed(r.dist20,1)],["5日漲幅",signed(r.ret5,1)],["20日漲幅",signed(r.ret20,1)],["RSI",num(r.rsi,0)],["5MA",num(r.ma5,2)],["10MA",num(r.ma10,2)],["20MA",num(r.ma20,2)],["60MA",num(r.ma60,2)],["20/60狀態",r.ma20_60_state||"—"],["20MA 5日斜率",signed(r.ma20_slope_5d,2)],["60MA 5日斜率",signed(r.ma60_slope_5d,2)],["20日突破",r.break20?"是":"否"],["均線多頭",r.trend?"是":"否"],["族群共振",(r.sector_score_label?((r.sector_hot_count||0)+"檔 · "+r.sector_score_label+(r.sector_score_source==="官方產業代理"?"（產業代理）":"")):"待分類")]];'
        s = must_replace(s, old, new, "close 20/60 metrics")

    # Bump cache-busting ids if v1.5.3 already touched them.
    s = s.replace('realtime-config.js?v=153', 'realtime-config.js?v=154')
    s = s.replace('realtime.js?v=153', 'realtime.js?v=154')
    s = s.replace('realtime-config.js?v=151', 'realtime-config.js?v=154')
    s = s.replace('realtime.js?v=151', 'realtime.js?v=154')
    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = s.replace("dogson-free-v153", "dogson-free-v154")
    s = s.replace("dogson-free-v151", "dogson-free-v154")
    s = s.replace("realtime-config.js?v=153", "realtime-config.js?v=154")
    s = s.replace("realtime.js?v=153", "realtime.js?v=154")
    s = s.replace("realtime-config.js?v=151", "realtime-config.js?v=154")
    s = s.replace("realtime.js?v=151", "realtime.js?v=154")
    write(p, s)


if __name__ == "__main__":
    patch_build_data()
    patch_index()
    patch_sw()
    print("v1.5.4 patch applied")
