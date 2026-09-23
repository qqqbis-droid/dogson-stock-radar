#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Install Dogson Radar v1.5.5 intraday amplitude-efficiency upgrade.

Design constraint:
- Do NOT add a new score bucket or increase the 100-point total.
- Keep intraday weights at 30 + 25 + 15 + 20 + 10.
- Use amplitude efficiency only to improve the existing 25-point flow/volume
  judgement and the existing 10-point liquidity/chase-risk judgement.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"v1.5.5 patch missing marker: {label}")
    return text.replace(old, new, 1)


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)

    for oldv in ["v1.5.1", "v1.5.2", "v1.5.3", "v1.5.4"]:
        if f"犬子老師飆股雷達 Free Edition {oldv}" in s:
            s = s.replace(f"犬子老師飆股雷達 Free Edition {oldv}",
                          "犬子老師飆股雷達 Free Edition v1.5.5", 1)
            break

    if '"amplitude_efficiency"' not in s:
        old = '''    day_change = (cur / prev_close - 1) * 100 if prev_close else 0\n    ret15 = (c.iloc[-1] / c.iloc[-4] - 1) * 100 if len(c) >= 4 else 0\n    vwap_dist = (cur / vwap - 1) * 100 if vwap else 0\n\n    # 資金輪動用：目前累積成交金額，以及最近一段 vs 前一段成交金額。\n'''
        new = '''    day_change = (cur / prev_close - 1) * 100 if prev_close else 0\n    ret15 = (c.iloc[-1] / c.iloc[-4] - 1) * 100 if len(c) >= 4 else 0\n    vwap_dist = (cur / vwap - 1) * 100 if vwap else 0\n\n    # v1.5.5 振幅效率：只升級既有量價/追價風險，不新增總分權重。\n    day_high = float(today["High"].max())\n    day_low = float(today["Low"].min())\n    day_range = max(0.0, day_high - day_low)\n    amplitude_pct = (day_range / prev_close * 100) if prev_close else 0.0\n    range_position_pct = ((cur - day_low) / day_range * 100) if day_range > 0 else 50.0\n    range_position_pct = max(0.0, min(100.0, range_position_pct))\n    amplitude_efficiency = (day_change / amplitude_pct) if amplitude_pct > 1e-9 else 0.0\n\n    # 同時段振幅基準：欄位支援最多20個歷史交易日；現行5日5分K來源\n    # 會先用可取得的歷史樣本暖機。只有樣本>=3才讓倍數參與評分。\n    all_dates = sorted(set(x.index.date))\n    cutoff_time = today.index[-1].time()\n    amp_samples = []\n    for d0 in [d for d in all_dates if d < latest][-20:]:\n        hist = x[x.index.date == d0]\n        hist = hist[[ts.time() <= cutoff_time for ts in hist.index]]\n        if hist.empty:\n            continue\n        earlier = [d for d in all_dates if d < d0]\n        if not earlier:\n            continue\n        pd0 = earlier[-1]\n        pday = x[x.index.date == pd0]\n        if pday.empty:\n            continue\n        hist_prev_close = float(pday["Close"].iloc[-1])\n        if hist_prev_close <= 0:\n            continue\n        hist_range = float(hist["High"].max() - hist["Low"].min())\n        hist_amp = hist_range / hist_prev_close * 100\n        if np.isfinite(hist_amp) and hist_amp >= 0:\n            amp_samples.append(float(hist_amp))\n\n    amp_sample_days = len(amp_samples)\n    same_time_amp_avg_pct = float(np.mean(amp_samples)) if amp_samples else None\n    amplitude_multiple = (amplitude_pct / same_time_amp_avg_pct) if same_time_amp_avg_pct and same_time_amp_avg_pct > 1e-9 else None\n    amp_baseline_ready = bool(amp_sample_days >= 3 and amplitude_multiple is not None)\n\n    # 狀態只用來修正既有量價25與追價風險10，不形成新的分數桶。\n    expanded = bool((amp_baseline_ready and amplitude_multiple >= 1.25) or (not amp_baseline_ready and amplitude_pct >= 4.5))\n    compressed = bool(amp_baseline_ready and amplitude_multiple <= 0.90)\n    if expanded and range_position_pct >= 80 and amplitude_efficiency >= 0.55 and cur >= vwap:\n        amplitude_regime = "有效擴張"\n    elif expanded and range_position_pct <= 40 and cur < vwap and amplitude_efficiency <= 0.25:\n        amplitude_regime = "沖高回落"\n    elif expanded and abs(amplitude_efficiency) < 0.30:\n        amplitude_regime = "高震盪"\n    elif compressed and cur >= vwap and 45 <= range_position_pct <= 85 and amplitude_efficiency >= 0:\n        amplitude_regime = "健康整理"\n    else:\n        amplitude_regime = "中性"\n\n    # 資金輪動用：目前累積成交金額，以及最近一段 vs 前一段成交金額。\n'''
        s = replace_once(s, old, new, "intraday amplitude calculations")

        old = '''        "ret15": round(ret15, 2),\n        "break3": b3, "break12": b12, "trend5": trend,\n'''
        new = '''        "ret15": round(ret15, 2),\n        "amplitude_pct": round(amplitude_pct, 2),\n        "range_position_pct": round(range_position_pct, 1),\n        "amplitude_efficiency": round(amplitude_efficiency, 3),\n        "same_time_amp_avg_pct": round(same_time_amp_avg_pct, 2) if same_time_amp_avg_pct is not None else None,\n        "amplitude_multiple": round(amplitude_multiple, 3) if amplitude_multiple is not None else None,\n        "amp_sample_days": amp_sample_days,\n        "amp_baseline_ready": amp_baseline_ready,\n        "amplitude_regime": amplitude_regime,\n        "break3": b3, "break12": b12, "trend5": trend,\n'''
        s = replace_once(s, old, new, "intraday amplitude output fields")

        old = '''    if ret15 > 4:\n        score -= 5; over.append("15分鐘急拉")\n\n    sr = intraday_sr(x, vwap)\n'''
        new = '''    if ret15 > 4:\n        score -= 5; over.append("15分鐘急拉")\n    if amplitude_regime == "高震盪":\n        over.append("高振幅低效率")\n    elif amplitude_regime == "沖高回落":\n        over.append("振幅擴大後沖高回落")\n\n    sr = intraday_sr(x, vwap)\n'''
        s = replace_once(s, old, new, "amplitude overheat reasons")

    if 'amp_regime = str(r.get("amplitude_regime")' not in s:
        old = '''    pace = float(r.get("pace") or 0)\n    day = float(r.get("day_change") or 0)\n    ret15 = float(r.get("ret15") or 0)\n\n    price = 0.0\n'''
        new = '''    pace = float(r.get("pace") or 0)\n    day = float(r.get("day_change") or 0)\n    ret15 = float(r.get("ret15") or 0)\n    amp_regime = str(r.get("amplitude_regime") or "中性")\n    amp_multiple = r.get("amplitude_multiple")\n    amp_ready = bool(r.get("amp_baseline_ready"))\n    range_pos = float(r.get("range_position_pct") or 50)\n\n    price = 0.0\n'''
        s = replace_once(s, old, new, "score amplitude inputs")

        old = '''    flow = 0.0\n    if 1.5 <= pace < 3.5:\n        flow += 15\n    elif 1.2 <= pace < 1.5:\n        flow += 10\n    elif 3.5 <= pace <= 5:\n        flow += 10\n    elif pace >= 1.0:\n        flow += 5\n    if 0.2 <= ret15 <= 2.5:\n'''
        new = '''    flow = 0.0\n    # 原本的量速權重仍在量價/動能25分內；振幅效率只修正量速品質。\n    if 1.5 <= pace < 3.5:\n        pace_points = 15.0\n    elif 1.2 <= pace < 1.5:\n        pace_points = 10.0\n    elif 3.5 <= pace <= 5:\n        pace_points = 10.0\n    elif pace >= 1.0:\n        pace_points = 5.0\n    else:\n        pace_points = 0.0\n\n    if amp_regime == "有效擴張":\n        pace_points = min(15.0, pace_points + 2.0)\n    elif amp_regime == "高震盪":\n        pace_points = max(0.0, pace_points - 4.0)\n    elif amp_regime == "沖高回落":\n        pace_points = max(0.0, pace_points - 6.0)\n    flow += pace_points\n\n    if 0.2 <= ret15 <= 2.5:\n'''
        s = replace_once(s, old, new, "flow volume amplitude quality")

        old = '''    hot_n = len(r.get("overheat_reasons") or [])\n    risk = 5.0 if hot_n == 0 else 2.0 if hot_n == 1 else 0.0\n    if float(r.get("vwap_dist") or 0) < -2.0:\n        risk = max(0.0, risk - 2.0)\n    liquidity_risk = min(10.0, liquidity + risk)\n'''
        new = '''    hot_n = len(r.get("overheat_reasons") or [])\n    risk = 5.0 if hot_n == 0 else 2.0 if hot_n == 1 else 0.0\n    if float(r.get("vwap_dist") or 0) < -2.0:\n        risk = max(0.0, risk - 2.0)\n    # 振幅效率只調整原本的「追價風險」5分，不增加10分上限。\n    if amp_regime == "高震盪":\n        risk = max(0.0, risk - 2.0)\n    elif amp_regime == "沖高回落":\n        risk = max(0.0, risk - 3.0)\n    elif amp_regime == "有效擴張" and amp_ready and amp_multiple is not None and float(amp_multiple) >= 1.6 and range_pos >= 95:\n        # 強勢是真的，但若已貼近極端高檔且振幅明顯擴張，仍降低追價安全度。\n        risk = max(0.0, risk - 1.0)\n    liquidity_risk = min(10.0, liquidity + risk)\n'''
        s = replace_once(s, old, new, "chase risk amplitude quality")

    # Keep the score weights visibly unchanged and describe amplitude as an in-bucket modifier.
    old_formula = '"score_formula": {"mode": "intraday_execution", "price_structure": 30, "flow_volume": 25, "relative_strength": 15, "sector": 20, "liquidity_risk": 10, "chip": "background_only", "market_separate": 15},'
    if old_formula in s:
        new_formula = '"score_formula": {"mode": "intraday_execution", "price_structure": 30, "flow_volume": 25, "relative_strength": 15, "sector": 20, "liquidity_risk": 10, "amplitude_efficiency": "inside_flow_and_liquidity_risk_no_new_weight", "chip": "background_only", "market_separate": 15},'
        s = s.replace(old_formula, new_formula, 1)

    write(p, s)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    for old in [
        "Free Edition v1.5.2｜盤中動能100＋盤後波段100＋60K全股票資訊",
        "Free Edition v1.5.3｜族群資金可展開＋盤後法人流向＋60K全股票資訊",
        "Free Edition v1.5.4｜20/60續航＋進場燈號＋族群法人資金流",
    ]:
        if old in s:
            s = s.replace(old, "Free Edition v1.5.5｜盤中振幅效率＋盤中動能100＋盤後波段100", 1)
            break

    help_old = '<b>同時間量速 2.4x：</b>今天此刻的累積量約為過去同時間的 2.4 倍。1.5～3 倍通常最舒服，>5 倍要防過熱。<br>'
    if "振幅效率：</b>" not in s:
        help_new = help_old + '<b>振幅效率：</b>今日振幅＝(今日高−今日低)÷昨收；區間位置＝(現價−今日低)÷(今日高−今日低)；振幅效率＝當日漲幅÷今日振幅。「有效擴張」代表振幅放大且價格仍靠近高點；「高震盪／沖高回落」會降低原本量價品質與追價安全度。這不是新增分數，盤中仍維持30＋25＋15＋20＋10＝100。<br><b>同時段振幅倍數：</b>今日此刻振幅 ÷ 歷史同時間平均振幅。程式欄位支援最多20個交易日；現行5日5分K來源先以可取得樣本暖機，畫面會顯示樣本數，至少3日才讓倍數參與評分。<br>'
        s = replace_once(s, help_old, help_new, "amplitude help")

    old_metrics = 'if(mode==="intraday")return [["現價",num(r.close,2)],["行情時間",r.quote_time||r.time||"—"],["5分K結構",r.structure_time||r.time||"—"],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["當日",signed(r.day_change,1)],["VWAP",num(r.vwap,2)],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["族群共振",(r.sector_score_label?(num(r.sector_score,1)+"/10 · "+r.sector_score_label+(r.sector_score_source==="官方產業代理"?"（產業代理）":"")):"待分類")]];'
    if "振幅狀態" not in s:
        new_metrics = 'if(mode==="intraday")return [["現價",num(r.close,2)],["行情時間",r.quote_time||r.time||"—"],["5分K結構",r.structure_time||r.time||"—"],["同時間量速",num(r.pace,1)+"x"],["今日振幅",num(r.amplitude_pct,2)+"%"],["區間位置",num(r.range_position_pct,0)+"%"],["同時段振幅倍數",r.amp_baseline_ready?(num(r.amplitude_multiple,2)+"x"):((r.amp_sample_days||0)+"日樣本")],["振幅效率",num(r.amplitude_efficiency,2)],["振幅狀態",r.amplitude_regime||"中性"],["距VWAP",signed(r.vwap_dist,1)],["當日",signed(r.day_change,1)],["VWAP",num(r.vwap,2)],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["族群共振",(r.sector_score_label?(num(r.sector_score,1)+"/10 · "+r.sector_score_label+(r.sector_score_source==="官方產業代理"?"（產業代理）":"")):"待分類")]];'
        s = replace_once(s, old_metrics, new_metrics, "intraday amplitude metrics")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    for old in ["dogson-free-v152", "dogson-free-v153", "dogson-free-v154"]:
        if old in s:
            s = s.replace(old, "dogson-free-v155", 1)
            break
    write(p, s)


if __name__ == "__main__":
    patch_build_data()
    patch_index()
    patch_sw()
    print("v1.5.5 amplitude-efficiency patch applied")
