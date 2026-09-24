#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""犬子老師飆股雷達 Step 8 — 獨立當沖模式。

重要隔離規則：
1. 只讀 docs/data/intraday.json，不寫回 intraday.json。
2. 只輸出 docs/data/daytrade.json。
3. 保留 source_intraday_score / source_category / source_* 作追溯，
   daytrade_score / daytrade_state / daytrade_components 為獨立系統。
4. 不改 Stage 2.0、不改盤中 30/25/15/20/10、不改波段 50/25/15/10。
"""
from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
INTRADAY = DATA / "intraday.json"
OUT = DATA / "daytrade.json"
STATUS = DATA / "status.json"
TW = timezone(timedelta(hours=8))

DAYTRADE_WEIGHTS = {
    "execution_structure": 30,
    "flow_volume": 25,
    "relative_sector": 20,
    "timing_volatility": 15,
    "liquidity_risk": 10,
}


def now_tw():
    return datetime.now(TW)


def load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def dump(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def f(v, default=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else float(default)
    except Exception:
        return float(default)


def clamp(v, lo, hi):
    return max(float(lo), min(float(hi), float(v)))


def _quality(score):
    if score >= 82:
        return "強勢"
    if score >= 72:
        return "良好"
    if score >= 60:
        return "一般"
    return "偏弱"


def _dynamic(r):
    d = r.get("dynamic_thresholds") or {}
    return {
        "day_hot": f(d.get("day_hot_pct"), 8.5),
        "vwap_hot": f(d.get("vwap_hot_pct"), 4.5),
        "ret15_hot": f(d.get("ret15_hot_pct"), 4.0),
        "pace_hot": f(d.get("pace_hot_x"), 5.0),
        "day_good": f(d.get("day_good_high_pct"), 6.5),
        "ret15_good": f(d.get("ret15_good_high_pct"), 2.5),
        "mode": d.get("mode") or "fallback",
    }


def score_daytrade_row(source):
    """Return a new daytrade row and never mutate *source*."""
    r = deepcopy(source)
    dyn = _dynamic(source)
    close = f(source.get("close"))
    vwap = f(source.get("vwap"))
    vwap_dist = f(source.get("vwap_dist"))
    pace = f(source.get("pace"), 1.0)
    ret15 = f(source.get("ret15"))
    day = f(source.get("day_change"))
    range_pos = f(source.get("range_position_pct"), 50.0)
    amp = str(source.get("amplitude_regime") or "中性")
    trend5 = bool(source.get("trend5"))
    break3 = bool(source.get("break3"))
    source_components = source.get("intraday_components") or {}
    source_stage = str(source.get("category") or "觀察")
    source_over = list(source.get("overheat_reasons") or [])
    market_mode = str(source.get("market_mode") or "")

    # A. 執行價格結構 30
    execution = 0.0
    exec_reasons = []
    if vwap > 0 and close >= vwap:
        execution += 10; exec_reasons.append("站上VWAP")
    if break3:
        execution += 7; exec_reasons.append("3K突破")
    if trend5:
        execution += 7; exec_reasons.append("5分短均向上")
    if 45 <= range_pos <= 88:
        execution += 6; exec_reasons.append("區間位置適中")
    elif 35 <= range_pos < 45 or 88 < range_pos <= 94:
        execution += 3
    execution = clamp(execution, 0, 30)

    # B. 量價／即時推進 25
    flow = 0.0
    flow_reasons = []
    if 1.2 <= pace < 3.5:
        flow += 12; flow_reasons.append(f"量速{pace:.1f}x")
    elif 0.9 <= pace < 1.2:
        flow += 6
    elif 3.5 <= pace <= dyn["pace_hot"]:
        flow += 8; flow_reasons.append("大量但未超個股門檻")
    elif pace > 0:
        flow += 2

    recent = f(source.get("recent_turnover"), -1)
    previous = f(source.get("previous_turnover"), -1)
    accel = (recent / previous) if recent >= 0 and previous > 0 else None
    if accel is not None:
        if accel >= 1.25:
            flow += 7; flow_reasons.append("近段成交金額加速")
        elif accel >= 1.05:
            flow += 5
        elif accel >= 0.90:
            flow += 2

    if 0.15 <= ret15 <= dyn["ret15_good"]:
        flow += 6; flow_reasons.append("15分鐘有效推進")
    elif 0 < ret15 < 0.15:
        flow += 3
    flow = clamp(flow, 0, 25)

    # C. 相對強弱＋族群確認 20（只讀來源 component，不改來源公式）
    src_rel = clamp(f(source_components.get("relative_strength")), 0, 15)
    src_sec = clamp(f(source_components.get("sector")), 0, 20)
    relative_sector = clamp((src_rel / 15.0) * 10.0 + (src_sec / 20.0) * 10.0, 0, 20)
    rs_reasons = []
    if src_rel >= 8:
        rs_reasons.append("相對市場有優勢")
    if src_sec >= 8:
        rs_reasons.append("族群有共振")

    # D. 進場時機／波動效率 15
    timing = 0.0
    timing_reasons = []
    if amp == "有效擴張":
        timing += 6; timing_reasons.append("振幅有效擴張")
    elif amp == "健康整理":
        timing += 5; timing_reasons.append("健康整理")
    elif amp == "中性":
        timing += 3

    vwap_soft = max(1.0, min(2.5, dyn["vwap_hot"] * 0.55))
    if -0.5 <= vwap_dist <= vwap_soft:
        timing += 5; timing_reasons.append("距VWAP適合執行")
    elif -1.0 <= vwap_dist < -0.5 or vwap_soft < vwap_dist <= dyn["vwap_hot"]:
        timing += 2

    if 0.3 <= day <= dyn["day_good"]:
        timing += 4; timing_reasons.append("當日漲幅未過度延伸")
    elif 0 < day < 0.3:
        timing += 2
    timing = clamp(timing, 0, 15)

    # E. 流動性／追價風險 10
    level = str(source.get("liquidity_level") or "未知")
    liquidity = 5.0 if level == "活躍" else 4.0 if level == "正常" else 2.0 if level == "偏低" else 0.0 if level == "不足" else 3.0
    hard_over = []
    if day >= dyn["day_hot"]:
        hard_over.append(f"當日漲幅≥個股門檻{dyn['day_hot']:.1f}%")
    if vwap_dist > dyn["vwap_hot"]:
        hard_over.append(f"距VWAP>{dyn['vwap_hot']:.1f}%")
    if pace > dyn["pace_hot"]:
        hard_over.append(f"量速>{dyn['pace_hot']:.1f}x")
    if ret15 > dyn["ret15_hot"]:
        hard_over.append(f"15分鐘>{dyn['ret15_hot']:.1f}%")
    if amp in {"高震盪", "沖高回落"}:
        hard_over.append(amp)
    risk_points = 5.0 if not hard_over and not source_over else 2.0 if len(hard_over) + len(source_over) == 1 else 0.0
    liquidity_risk = clamp(liquidity + risk_points, 0, 10)

    components = {
        "execution_structure": round(execution, 1),
        "flow_volume": round(flow, 1),
        "relative_sector": round(relative_sector, 1),
        "timing_volatility": round(timing, 1),
        "liquidity_risk": round(liquidity_risk, 1),
    }
    score = round(clamp(sum(components.values()), 0, 100), 1)

    # 獨立狀態機：只作用於 daytrade.json。
    below_vwap = bool(vwap > 0 and close < vwap)
    invalid = (
        source_stage == "結構失效"
        or (below_vwap and not trend5 and ret15 <= -0.5 and score < 48)
        or (vwap > 0 and close < vwap * 0.985 and ret15 < 0 and execution <= 7)
    )
    overheated = bool(hard_over) or source_stage == "過熱不追"
    market_defensive = market_mode == "防守"
    executable = bool(
        score >= 75 and execution >= 20 and flow >= 14 and relative_sector >= 10
        and liquidity_risk >= 6 and not below_vwap and trend5 and not market_defensive
    )
    wait_pullback = bool(
        not invalid and not overheated and score >= 62
        and (vwap_dist > vwap_soft or range_pos > 88 or ret15 > dyn["ret15_good"] * 0.8 or (break3 and not executable))
    )

    if invalid:
        state = "失效"
        headline = "短線執行結構已失守"
    elif overheated:
        state = "過熱不追"
        headline = "動能可能仍強，但當沖追價風險過高"
    elif executable:
        state = "可執行"
        headline = "5分結構、量價、相對強弱與位置同步"
    elif wait_pullback:
        state = "等回踩"
        headline = "條件偏強，但位置需要更好的風險報酬"
    else:
        state = "觀察"
        headline = "尚未形成足夠同步的當沖執行條件"

    # 當沖模式的 reasons / risks 只說明 daytrade score；來源 Stage 仍完整留存。
    reasons = (exec_reasons + flow_reasons + rs_reasons + timing_reasons)[:8]
    risks = list(dict.fromkeys(hard_over + source_over))[:6]
    if market_defensive and state not in {"失效", "過熱不追"}:
        risks.append("大盤防守模式：可執行條件提高")

    # UI 需要的行情欄位可以複製，但 source file 不會被改寫。
    r.update({
        "daytrade_version": "1.0",
        "source_intraday_score": f(source.get("intraday_score"), f(source.get("score"))),
        "source_category": source_stage,
        "source_stage_reason": source.get("stage_reason"),
        "source_intraday_components": source_components,
        "source_overheat_reasons": source_over,
        "daytrade_score": score,
        "daytrade_state": state,
        "daytrade_headline": headline,
        "daytrade_components": components,
        "daytrade_component_weights": DAYTRADE_WEIGHTS,
        "daytrade_reasons": reasons,
        "daytrade_risks": risks,
        "daytrade_turnover_acceleration": round(accel, 3) if accel is not None else None,
        "daytrade_dynamic_mode": dyn["mode"],
        # These aliases exist only in daytrade.json so current generic cards can render it.
        "score": score,
        "intraday_score": score,
        "category": state,
        "quality_label": _quality(score),
        "reasons": reasons,
        "overheat_reasons": risks,
        "stage_reason": headline,
        "stage_signals": reasons[:5],
        "stage_risks": risks[:5],
    })
    return r


def build_daytrade(intraday_obj):
    rows = [score_daytrade_row(r) for r in (intraday_obj.get("rows") or []) if r.get("code")]
    rows.sort(key=lambda r: (f(r.get("daytrade_score")), f(r.get("day_change"))), reverse=True)
    counts = {}
    for r in rows:
        st = str(r.get("daytrade_state") or "觀察")
        counts[st] = counts.get(st, 0) + 1
    return {
        "version": "1.0",
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "source": "intraday.json read-only derivative",
        "source_updated_at": intraday_obj.get("updated_at"),
        "market": intraday_obj.get("market") or {},
        "market_intraday": intraday_obj.get("market_intraday") or {},
        "sector_rotation": intraday_obj.get("sector_rotation") or [],
        "quote_layer": intraday_obj.get("quote_layer") or {},
        "weights": DAYTRADE_WEIGHTS,
        "state_counts": counts,
        "isolation": {
            "writes_intraday": False,
            "changes_stage2": False,
            "changes_swing_score": False,
            "changes_intraday_score": False,
        },
        "rows": rows,
        "note": "獨立當沖執行分；不覆蓋原盤中動能、Stage 2.0 或波段分數。",
    }


def main():
    obj = load(INTRADAY, {})
    if not obj.get("rows"):
        previous = load(OUT, {"version": "1.0", "rows": []})
        previous["attempted_at"] = now_tw().isoformat(timespec="seconds")
        previous["stale"] = True
        previous["note"] = "本輪 intraday.json 沒有資料，保留上一輪當沖雷達。"
        dump(OUT, previous)
        print("daytrade source empty; kept previous", len(previous.get("rows") or []))
        return

    out = build_daytrade(obj)
    dump(OUT, out)

    status = load(STATUS, {})
    status.update({
        "daytrade_version": "1.0",
        "daytrade_updated_at": out["updated_at"],
        "daytrade_count": len(out["rows"]),
        "version": "1.5.30-free",
    })
    dump(STATUS, status)
    print("daytrade done", len(out["rows"]), out["state_counts"])


if __name__ == "__main__":
    main()
