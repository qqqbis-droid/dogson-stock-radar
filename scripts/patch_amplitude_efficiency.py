#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Add intraday amplitude efficiency without changing the 100-point weight model.
# Keeps intraday weights: 30 + 25 + 15 + 20 + 10 = 100.

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_data.py"
HTML = ROOT / "docs" / "index.html"
SW = ROOT / "docs" / "sw.js"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"patch marker not found: {label}")
    return text.replace(old, new, 1)


def patch_build():
    s = BUILD.read_text(encoding="utf-8")

    old = '''    day_change = (cur / prev_close - 1) * 100 if prev_close else 0
    ret15 = (c.iloc[-1] / c.iloc[-4] - 1) * 100 if len(c) >= 4 else 0
    vwap_dist = (cur / vwap - 1) * 100 if vwap else 0

    # 資金輪動用：目前累積成交金額，以及最近一段 vs 前一段成交金額。
'''
    new = '''    day_change = (cur / prev_close - 1) * 100 if prev_close else 0
    ret15 = (c.iloc[-1] / c.iloc[-4] - 1) * 100 if len(c) >= 4 else 0
    vwap_dist = (cur / vwap - 1) * 100 if vwap else 0

    # 振幅效率：不新增分數權重，只用來升級原本的量價品質與追價風險。
    # 分母用「前收至今日高低的有效波動區間」，避免跳空股把效率算到 >100%。
    day_high = float(today["High"].max())
    day_low = float(today["Low"].min())
    day_range = max(0.0, day_high - day_low)
    day_amplitude_pct = (day_range / prev_close * 100) if prev_close else 0.0

    true_high = max(day_high, prev_close)
    true_low = min(day_low, prev_close)
    true_range = max(0.0, true_high - true_low)
    true_amplitude_pct = (true_range / prev_close * 100) if prev_close else 0.0
    advance = max(0.0, cur - prev_close)
    amplitude_efficiency = (
        max(0.0, min(100.0, advance / true_range * 100))
        if true_range > 1e-9 else 0.0
    )
    range_position_pct = (
        max(0.0, min(100.0, (cur - day_low) / day_range * 100))
        if day_range > 1e-9 else 50.0
    )

    def _efficiency_until(z):
        if z is None or z.empty:
            return None
        zz_cur = float(z["Close"].iloc[-1])
        zz_high = max(float(z["High"].max()), prev_close)
        zz_low = min(float(z["Low"].min()), prev_close)
        zz_range = max(0.0, zz_high - zz_low)
        if zz_range <= 1e-9:
            return 0.0
        zz_advance = max(0.0, zz_cur - prev_close)
        return max(0.0, min(100.0, zz_advance / zz_range * 100))

    efficiency_15m_ago = _efficiency_until(today.iloc[:-3]) if len(today) >= 6 else None
    efficiency_change_15m = (
        amplitude_efficiency - efficiency_15m_ago
        if efficiency_15m_ago is not None else None
    )

    if day_change <= 0:
        amplitude_state = "未形成上攻"
    elif amplitude_efficiency >= 70 and range_position_pct >= 75 and cur >= vwap:
        amplitude_state = "高效推進"
    elif amplitude_efficiency >= 50 and range_position_pct >= 60:
        amplitude_state = "有效推進"
    elif (
        efficiency_change_15m is not None
        and efficiency_change_15m <= -25
        and range_position_pct < 70
    ):
        amplitude_state = "效率惡化"
    elif true_amplitude_pct >= 2.5 and amplitude_efficiency < 35:
        amplitude_state = "低效震盪"
    else:
        amplitude_state = "一般"

    # 資金輪動用：目前累積成交金額，以及最近一段 vs 前一段成交金額。
'''
    s = replace_once(s, old, new, "intraday amplitude metrics")

    old = '''    if pace > 5:
        score -= 5; over.append("量速極端")
    if ret15 > 4:
        score -= 5; over.append("15分鐘急拉")

    sr = intraday_sr(x, vwap)
'''
    new = '''    if pace > 5:
        score -= 5; over.append("量速極端")
    if ret15 > 4:
        score -= 5; over.append("15分鐘急拉")

    chase_risk = []
    if day_change > 0 and true_amplitude_pct >= 2.5 and amplitude_efficiency < 35:
        chase_risk.append("振幅大但推進效率低")
    if (
        efficiency_change_15m is not None
        and efficiency_change_15m <= -25
        and range_position_pct < 70
    ):
        chase_risk.append("振幅效率15分鐘明顯惡化")
    if day_change > 0 and day_high > prev_close and range_position_pct < 45:
        chase_risk.append("沖高後落到當日區間中低檔")
    if day_change > 0 and cur < vwap and amplitude_efficiency < 40:
        chase_risk.append("上攻效率低且跌回VWAP")

    if amplitude_state == "高效推進":
        reasons.append(f"振幅效率{amplitude_efficiency:.0f}%・高效推進")
    elif amplitude_state == "有效推進":
        reasons.append(f"振幅效率{amplitude_efficiency:.0f}%・有效推進")

    sr = intraday_sr(x, vwap)
'''
    s = replace_once(s, old, new, "intraday chase-risk reasons")

    old = '''        "vwap_dist": round(vwap_dist, 2), "day_change": round(day_change, 2),
        "ret15": round(ret15, 2),
        "break3": b3, "break12": b12, "trend5": trend,
'''
    new = '''        "vwap_dist": round(vwap_dist, 2), "day_change": round(day_change, 2),
        "ret15": round(ret15, 2),
        "day_high": round(day_high, 2), "day_low": round(day_low, 2),
        "day_amplitude_pct": round(day_amplitude_pct, 2),
        "true_amplitude_pct": round(true_amplitude_pct, 2),
        "amplitude_efficiency": round(amplitude_efficiency, 1),
        "range_position_pct": round(range_position_pct, 1),
        "amplitude_efficiency_15m_ago": round(efficiency_15m_ago, 1) if efficiency_15m_ago is not None else None,
        "amplitude_efficiency_change_15m": round(efficiency_change_15m, 1) if efficiency_change_15m is not None else None,
        "amplitude_state": amplitude_state,
        "chase_risk_reasons": chase_risk,
        "break3": b3, "break12": b12, "trend5": trend,
'''
    s = replace_once(s, old, new, "intraday return fields")

    old = '''    day = float(r.get("day_change") or 0)
    ret15 = float(r.get("ret15") or 0)

    price = 0.0
'''
    new = '''    day = float(r.get("day_change") or 0)
    ret15 = float(r.get("ret15") or 0)
    amplitude_efficiency = float(r.get("amplitude_efficiency") or 0)
    range_position_pct = float(r.get("range_position_pct") or 0)
    true_amplitude_pct = float(r.get("true_amplitude_pct") or 0)
    try:
        efficiency_change_15m = (
            float(r.get("amplitude_efficiency_change_15m"))
            if r.get("amplitude_efficiency_change_15m") is not None else None
        )
    except Exception:
        efficiency_change_15m = None

    price = 0.0
'''
    s = replace_once(s, old, new, "score reads amplitude fields")

    old = '''    if 0.5 <= day <= 6.5:
        flow += 4
    elif 0 < day < 0.5:
        flow += 2
    flow = min(25.0, flow)

    comps = (market or {}).get("components") or {}
'''
    new = '''    if 0.5 <= day <= 6.5:
        flow += 4
    elif 0 < day < 0.5:
        flow += 2

    # 振幅效率只調整原本的「量價/動能25分」，不新增第六個分項。
    flow_efficiency_adjustment = 0.0
    if day > 0:
        if (
            amplitude_efficiency >= 70
            and range_position_pct >= 75
            and close >= vwap
            and pace >= 1.2
        ):
            flow_efficiency_adjustment += 3.0
        elif amplitude_efficiency >= 50 and range_position_pct >= 60 and close >= vwap:
            flow_efficiency_adjustment += 1.0

        if true_amplitude_pct >= 2.5 and amplitude_efficiency < 35:
            flow_efficiency_adjustment -= 5.0
        if efficiency_change_15m is not None and efficiency_change_15m <= -25:
            flow_efficiency_adjustment -= 3.0

    flow = max(0.0, min(25.0, flow + flow_efficiency_adjustment))

    comps = (market or {}).get("components") or {}
'''
    s = replace_once(s, old, new, "flow amplitude adjustment")

    old = '''    hot_n = len(r.get("overheat_reasons") or [])
    risk = 5.0 if hot_n == 0 else 2.0 if hot_n == 1 else 0.0
    if float(r.get("vwap_dist") or 0) < -2.0:
        risk = max(0.0, risk - 2.0)
    liquidity_risk = min(10.0, liquidity + risk)

    total = max(0.0, min(100.0, price + flow + relative + sector + liquidity_risk))
'''
    new = '''    hot_n = len(r.get("overheat_reasons") or [])
    risk = 5.0 if hot_n == 0 else 2.0 if hot_n == 1 else 0.0
    if float(r.get("vwap_dist") or 0) < -2.0:
        risk = max(0.0, risk - 2.0)

    # 振幅效率同樣只升級原本的「追價風險5分」，不另開新權重。
    chase_n = len(r.get("chase_risk_reasons") or [])
    risk_efficiency_adjustment = -3.0 if chase_n >= 2 else -1.5 if chase_n == 1 else 0.0
    risk = max(0.0, min(5.0, risk + risk_efficiency_adjustment))
    liquidity_risk = min(10.0, liquidity + risk)

    total = max(0.0, min(100.0, price + flow + relative + sector + liquidity_risk))
'''
    s = replace_once(s, old, new, "risk amplitude adjustment")

    old = '''        "sector": round(sector, 1),
        "liquidity_risk": round(liquidity_risk, 1),
    }
'''
    new = '''        "sector": round(sector, 1),
        "liquidity_risk": round(liquidity_risk, 1),
        "amplitude_efficiency": round(amplitude_efficiency, 1),
        "range_position_pct": round(range_position_pct, 1),
        "amplitude_state": r.get("amplitude_state") or "—",
        "flow_efficiency_adjustment": round(flow_efficiency_adjustment, 1),
        "risk_efficiency_adjustment": round(risk_efficiency_adjustment, 1),
    }
'''
    s = replace_once(s, old, new, "component diagnostics")

    BUILD.write_text(s, encoding="utf-8")


def patch_html():
    s = HTML.read_text(encoding="utf-8")

    s = s.replace(
        "Free Edition v1.5.2｜盤中動能100＋盤後波段100＋60K全股票資訊",
        "Free Edition v1.5.2｜盤中振幅效率＋盤後波段100＋60K全股票資訊",
        1,
    )

    old = '''    <b>盤中動能 100：</b>價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10。籌碼只顯示為「偏多/中性/偏空背景」，不灌入盤中分數。<br>
'''
    new = '''    <b>盤中動能 100：</b>價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10。籌碼只顯示為「偏多/中性/偏空背景」，不灌入盤中分數。<br>
    <b>振幅效率：</b>不是新增分數，而是升級原本的量價25與追價風險10。效率越高，代表今天走過的有效波動大多有保留成上漲；振幅很大但效率低、區間位置掉到中低檔，會被視為低效震盪或沖高回落。<br>
'''
    s = replace_once(s, old, new, "help amplitude text")

    old_footer = '盤中動能100＝價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10｜籌碼只作背景｜大盤15分獨立'
    new_footer = '盤中動能100＝價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10｜振幅效率內嵌量價/追價、不另加權｜大盤15分獨立'
    s = s.replace(old_footer, new_footer)

    old = ''' if(mode==="intraday")return [["現價",num(r.close,2)],["行情時間",r.quote_time||r.time||"—"],["5分K結構",r.structure_time||r.time||"—"],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["當日",signed(r.day_change,1)],["VWAP",num(r.vwap,2)],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["族群共振",(r.sector_score_label?(num(r.sector_score,1)+"/10 · "+r.sector_score_label+(r.sector_score_source==="官方產業代理"?"（產業代理）":"")):"待分類")]];
'''
    new = ''' if(mode==="intraday")return [["現價",num(r.close,2)],["行情時間",r.quote_time||r.time||"—"],["5分K結構",r.structure_time||r.time||"—"],["同時間量速",num(r.pace,1)+"x"],["振幅效率",(r.amplitude_efficiency===null||r.amplitude_efficiency===undefined?"—":num(r.amplitude_efficiency,0)+"%")],["區間位置",(r.range_position_pct===null||r.range_position_pct===undefined?"—":num(r.range_position_pct,0)+"%")],["振幅判讀",r.amplitude_state||"—"],["當日振幅",(r.day_amplitude_pct===null||r.day_amplitude_pct===undefined?"—":num(r.day_amplitude_pct,1)+"%")],["距VWAP",signed(r.vwap_dist,1)],["當日",signed(r.day_change,1)],["VWAP",num(r.vwap,2)],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["族群共振",(r.sector_score_label?(num(r.sector_score,1)+"/10 · "+r.sector_score_label+(r.sector_score_source==="官方產業代理"?"（產業代理）":"")):"待分類")]];
'''
    s = replace_once(s, old, new, "intraday metrics UI")

    old = '''  ["現價",num(r.close,2)],["盤中動能",num(r.intraday_score??r.score,0)+"/100"],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["族群共振",num(r.sector_score,1)+"/10"],["籌碼背景",r.chip_background||"資料不足"]
'''
    new = '''  ["現價",num(r.close,2)],["盤中動能",num(r.intraday_score??r.score,0)+"/100"],["同時間量速",num(r.pace,1)+"x"],["振幅效率",(r.amplitude_efficiency===null||r.amplitude_efficiency===undefined?"—":num(r.amplitude_efficiency,0)+"% · "+(r.amplitude_state||""))],["距VWAP",signed(r.vwap_dist,1)],["族群共振",num(r.sector_score,1)+"/10"],["籌碼背景",r.chip_background||"資料不足"]
'''
    s = replace_once(s, old, new, "peer peek amplitude")

    old = '''${(r.overheat_reasons||[]).map(x=>`<span class="reason warn">⚠ ${x}</span>`).join("")}</div>
'''
    new = '''${(r.overheat_reasons||[]).map(x=>`<span class="reason warn">⚠ ${x}</span>`).join("")}${(r.chase_risk_reasons||[]).map(x=>`<span class="reason warn">⚠ 追價：${x}</span>`).join("")}</div>
'''
    s = replace_once(s, old, new, "render chase-risk warnings")

    HTML.write_text(s, encoding="utf-8")


def patch_sw():
    s = SW.read_text(encoding="utf-8")
    if "dogson-free-v152-ae" not in s:
        s = s.replace("const CACHE='dogson-free-v152';", "const CACHE='dogson-free-v152-ae';", 1)
    SW.write_text(s, encoding="utf-8")


def main():
    patch_build()
    patch_html()
    patch_sw()
    print("amplitude-efficiency patch applied")


if __name__ == "__main__":
    main()
