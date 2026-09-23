#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""犬子老師飆股雷達 Step 7 — 歷史驗證／結果校準引擎。

設計原則
1. 只用當時已存在的訊號做快照，不用未來資料重算舊訊號。
2. 等未來交易日真的發生後，才回填 1/3/5/10 日報酬與 MFE/MAE。
3. 波段權重校準只使用盤後快照；盤中快照只留作未來驗證，不污染波段權重。
4. 樣本不足時只輸出建議，正式權重維持 50/25/15/10。
5. 校準達最低樣本後，下一輪 build_data 才會讀取已完成的 calibration；因此不會用當日結果回頭改當日分數。
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
DATA.mkdir(parents=True, exist_ok=True)
TW = timezone(timedelta(hours=8))
HISTORY_PATH = DATA / "validation_history.json"
REPORT_PATH = DATA / "validation.json"

BASE_WEIGHTS = {"technical": 50.0, "chip": 25.0, "sector": 15.0, "liquidity": 10.0}
HORIZONS = (1, 3, 5, 10)


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


def f(v, default=None):
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def compact_close_row(r):
    comps = r.get("swing_components") or {}
    return {
        "code": str(r.get("code") or ""),
        "name": r.get("name"),
        "close": f(r.get("close")),
        "high": f(r.get("high"), f(r.get("close"))),
        "low": f(r.get("low"), f(r.get("close"))),
        "score": f(r.get("swing_quality_score"), f(r.get("score"), 0.0)),
        "entry": f(r.get("entry_position_score")),
        "category": r.get("category"),
        "quality": r.get("quality_label"),
        "sector_group": r.get("sector_group") or r.get("industry_name"),
        "market": r.get("market"),
        "market_mode": r.get("market_mode"),
        "technical_score": f(r.get("technical_score"), 0.0),
        "chip_score": f(r.get("chip_score"), 0.0),
        "chip_coverage_pct": f(r.get("chip_coverage_pct"), 0.0),
        "sector_score": f(r.get("sector_score"), 0.0),
        "liquidity_level": r.get("liquidity_level"),
        "components": {
            "technical": f(comps.get("technical"), 0.0),
            "chip": f(comps.get("chip"), 0.0),
            "sector": f(comps.get("sector"), 0.0),
            "liquidity": f(comps.get("liquidity"), 0.0),
        },
        "weight_source": r.get("swing_weight_source") or "baseline",
        "weights": r.get("swing_weights") or BASE_WEIGHTS,
    }


def compact_intraday_row(r):
    return {
        "code": str(r.get("code") or ""),
        "name": r.get("name"),
        "close": f(r.get("close")),
        "score": f(r.get("intraday_score"), f(r.get("score"), 0.0)),
        "category": r.get("category"),
        "sector_group": r.get("sector_group") or r.get("industry_name"),
        "market": r.get("market"),
        "market_mode": r.get("market_mode"),
        "pace": f(r.get("pace")),
        "vwap_dist": f(r.get("vwap_dist")),
        "ret15": f(r.get("ret15")),
        "amplitude_regime": r.get("amplitude_regime"),
        "chip_background": r.get("chip_background"),
        "chip_score": f(r.get("chip_score")),
        "dynamic_thresholds": r.get("dynamic_thresholds") or {},
    }


def trade_date_from(rows):
    ds = [str(r.get("date") or r.get("quote_date") or "")[:10] for r in rows or []]
    ds = [x for x in ds if len(x) == 10]
    return max(ds) if ds else None


def capture_close(history):
    obj = load(DATA / "close.json", {})
    rows = obj.get("rows") or []
    date = trade_date_from(rows)
    if not rows or not date:
        return history, False
    snap = {
        "date": date,
        "captured_at": now_tw().isoformat(timespec="seconds"),
        "market": obj.get("market") or load(DATA / "market.json", {}),
        "rows": [compact_close_row(r) for r in rows if r.get("code") and f(r.get("close"), 0) > 0],
    }
    arr = history.setdefault("close", [])
    arr[:] = [x for x in arr if x.get("date") != date]
    arr.append(snap)
    arr.sort(key=lambda x: x.get("date") or "")
    # 60 個交易日足以覆蓋 10 日 outcome、Stage/權重穩定性，又不讓免費 Pages 檔案無限膨脹。
    history["close"] = arr[-60:]
    return history, True


def capture_intraday(history):
    obj = load(DATA / "intraday.json", {})
    rows = obj.get("rows") or []
    date = trade_date_from(rows)
    if not rows or not date:
        return history, False
    time_vals = [str(r.get("quote_time") or r.get("structure_time") or r.get("time") or "")[:5] for r in rows]
    time_vals = [x for x in time_vals if len(x) >= 4]
    tm = max(time_vals) if time_vals else now_tw().strftime("%H:%M")
    # 每次掃描都留痕，但只保存最有判讀價值的候選，控制免費版歷史檔大小。
    stages = {"剛啟動", "蓄勢待發", "回踩承接", "趨勢持有", "轉弱警戒", "過熱不追"}
    candidates = [r for r in rows if f(r.get("intraday_score"), f(r.get("score"), 0)) >= 55 or str(r.get("category")) in stages]
    candidates.sort(key=lambda r: f(r.get("intraday_score"), f(r.get("score"), 0)), reverse=True)
    candidates = candidates[:40]
    snap = {
        "key": f"{date}T{tm}", "date": date, "time": tm,
        "captured_at": now_tw().isoformat(timespec="seconds"),
        "market": obj.get("market") or {},
        "rows": [compact_intraday_row(r) for r in candidates],
    }
    arr = history.setdefault("intraday", [])
    arr[:] = [x for x in arr if x.get("key") != snap["key"]]
    arr.append(snap)
    arr.sort(key=lambda x: x.get("key") or "")
    # 約 15 個交易日 × 每日最多 65 次五分掃描。
    if len(arr) > 975:
        arr = arr[-975:]
    history["intraday"] = arr
    return history, True


def row_maps(snaps):
    return [{str(r.get("code")): r for r in (s.get("rows") or [])} for s in snaps]


def outcome_records(snaps):
    """由真實後續快照形成 outcome；任何 horizon 不存在時就保持未成熟。"""
    maps = row_maps(snaps)
    records = []
    for i, snap in enumerate(snaps):
        base_map = maps[i]
        # 同一 signal date 的 5 日市場中位數，用來做選股相對績效校準。
        med5_pool = []
        if i + 5 < len(snaps):
            fm = maps[i + 5]
            for code, r in base_map.items():
                b = f(r.get("close")); z = f((fm.get(code) or {}).get("close"))
                if b and b > 0 and z and z > 0:
                    med5_pool.append((z / b - 1) * 100)
        med5 = statistics.median(med5_pool) if med5_pool else None

        for code, r in base_map.items():
            entry = f(r.get("close"))
            if not entry or entry <= 0:
                continue
            rec = {
                "signal_date": snap.get("date"), "code": code, "name": r.get("name"),
                "entry_close": round(entry, 4), "score": r.get("score"), "entry": r.get("entry"),
                "category": r.get("category"), "quality": r.get("quality"),
                "sector_group": r.get("sector_group"), "market_mode": r.get("market_mode"),
                "components": r.get("components") or {}, "returns": {},
            }
            for h in HORIZONS:
                if i + h < len(snaps):
                    fr = maps[i + h].get(code)
                    px = f((fr or {}).get("close"))
                    if px and px > 0:
                        rec["returns"][str(h)] = round((px / entry - 1) * 100, 3)
            # 真 MFE/MAE 使用未來每日 high/low；舊快照若尚未含 high/low，才退回 close。
            end = min(len(snaps) - 1, i + 10)
            highs, lows = [], []
            for j in range(i + 1, end + 1):
                z = maps[j].get(code) or {}
                hi = f(z.get("high"), f(z.get("close")))
                lo = f(z.get("low"), f(z.get("close")))
                if hi and hi > 0: highs.append(hi)
                if lo and lo > 0: lows.append(lo)
            rec["mfe10"] = round((max(highs) / entry - 1) * 100, 3) if highs else None
            rec["mae10"] = round((min(lows) / entry - 1) * 100, 3) if lows else None
            r5 = rec["returns"].get("5")
            rec["excess5"] = round(r5 - med5, 3) if r5 is not None and med5 is not None else None
            records.append(rec)
    return records


def pearson(xs, ys):
    pairs = [(float(x), float(y)) for x, y in zip(xs, ys) if x is not None and y is not None and math.isfinite(float(x)) and math.isfinite(float(y))]
    if len(pairs) < 3:
        return None
    ax = sum(x for x, _ in pairs) / len(pairs); ay = sum(y for _, y in pairs) / len(pairs)
    num = sum((x - ax) * (y - ay) for x, y in pairs)
    dx = math.sqrt(sum((x - ax) ** 2 for x, _ in pairs)); dy = math.sqrt(sum((y - ay) ** 2 for _, y in pairs))
    if dx <= 1e-12 or dy <= 1e-12:
        return 0.0
    return num / (dx * dy)


def calibrated_weights(records):
    matured = [r for r in records if r.get("excess5") is not None and (r.get("components") or {})]
    dates = sorted({r.get("signal_date") for r in matured if r.get("signal_date")})
    corr = {}
    caps = {"technical": 50.0, "chip": 25.0, "sector": 15.0, "liquidity": 10.0}
    for k in BASE_WEIGHTS:
        xs, ys = [], []
        for r in matured:
            v = f((r.get("components") or {}).get(k))
            y = f(r.get("excess5"))
            if v is None or y is None:
                continue
            xs.append(v / caps[k]); ys.append(max(-20.0, min(20.0, y)))
        c = pearson(xs, ys)
        corr[k] = None if c is None else round(c, 4)

    raw = {}
    for k, base in BASE_WEIGHTS.items():
        c = corr.get(k)
        # 單次最多讓一個 component 相對基準調整 ±15%，避免追逐近期雜訊。
        adj = max(-0.15, min(0.15, (c or 0.0) * 1.5))
        raw[k] = base * (1 + adj)
    total = sum(raw.values()) or 100.0
    suggested = {k: round(v / total * 100, 1) for k, v in raw.items()}
    # 修正四捨五入後總和，固定落在技術項目，不改相對排序。
    suggested["technical"] = round(suggested["technical"] + (100.0 - sum(suggested.values())), 1)

    # 要有足夠跨日期樣本才讓正式波段分採用；未達門檻只顯示研究結果。
    active = len(matured) >= 3000 and len(dates) >= 15
    return {
        "version": "1.0",
        "method": "5日相對報酬 × component正規化 Pearson；單項相對基準最大±15%，下一輪才生效",
        "active": bool(active),
        "status": "active" if active else "warming",
        "sample_rows": len(matured),
        "sample_dates": len(dates),
        "minimum_rows": 3000,
        "minimum_dates": 15,
        "baseline_weights": BASE_WEIGHTS,
        "suggested_weights": suggested,
        "active_weights": suggested if active else BASE_WEIGHTS,
        "correlations": corr,
        "as_of": dates[-1] if dates else None,
        "guardrail": "樣本不足不改正式分；盤中資料不參與波段權重校準；校準只使用已成熟5日結果。",
    }


def summarize(records, calibration, history):
    matured5 = [r for r in records if (r.get("returns") or {}).get("5") is not None]
    def stats(items, horizon="5"):
        vals = [f((r.get("returns") or {}).get(horizon)) for r in items]
        vals = [x for x in vals if x is not None]
        if not vals:
            return {"n": 0, "win_rate": None, "median_return": None, "avg_return": None}
        return {
            "n": len(vals),
            "win_rate": round(sum(x > 0 for x in vals) / len(vals) * 100, 1),
            "median_return": round(statistics.median(vals), 3),
            "avg_return": round(sum(vals) / len(vals), 3),
        }

    stage = {}
    for name in ["剛啟動", "蓄勢待發", "回踩承接", "趨勢持有", "觀察", "轉弱警戒", "結構失效", "過熱不追"]:
        s = stats([r for r in matured5 if r.get("category") == name])
        if s["n"]:
            stage[name] = s

    high_quality = stats([r for r in matured5 if f(r.get("score"), 0) >= 70])
    recent = []
    for r in reversed(matured5):
        if f(r.get("score"), 0) < 70 and r.get("category") not in {"剛啟動", "蓄勢待發", "回踩承接"}:
            continue
        recent.append({
            "signal_date": r.get("signal_date"), "code": r.get("code"), "name": r.get("name"),
            "category": r.get("category"), "score": r.get("score"),
            "r1": (r.get("returns") or {}).get("1"), "r3": (r.get("returns") or {}).get("3"),
            "r5": (r.get("returns") or {}).get("5"), "r10": (r.get("returns") or {}).get("10"),
            "mfe10": r.get("mfe10"), "mae10": r.get("mae10"),
        })
        if len(recent) >= 25:
            break

    return {
        "version": "1.0",
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "close_snapshot_days": len(history.get("close") or []),
        "intraday_scan_snapshots": len(history.get("intraday") or []),
        "outcome_rows": len(records),
        "matured_5d_rows": len(matured5),
        "high_quality_5d": high_quality,
        "stage_5d": stage,
        "calibration": calibration,
        "recent_matured_signals": recent,
        "horizons": [1, 3, 5, 10],
        "mfe_mae_window": 10,
        "note": "只顯示已發生的真實後續結果；尚未走滿 horizon 的訊號不會被當成0報酬。",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["close", "intraday", "all"], default="all")
    args = ap.parse_args()
    history = load(HISTORY_PATH, {"version": "1.0", "close": [], "intraday": []})
    history.setdefault("version", "1.0")
    changed = False
    if args.mode in {"close", "all"}:
        history, ok = capture_close(history); changed = changed or ok
    if args.mode in {"intraday", "all"}:
        history, ok = capture_intraday(history); changed = changed or ok
    history["updated_at"] = now_tw().isoformat(timespec="seconds")
    dump(HISTORY_PATH, history)

    records = outcome_records(history.get("close") or [])
    calibration = calibrated_weights(records)
    report = summarize(records, calibration, history)
    dump(REPORT_PATH, report)
    status_path = DATA / "status.json"
    status = load(status_path, {})
    status["validation_version"] = "1.0"
    status["validation_updated_at"] = report.get("updated_at")
    status["validation_close_days"] = report.get("close_snapshot_days")
    status["validation_matured_5d_rows"] = report.get("matured_5d_rows")
    status["calibration_active"] = bool(calibration.get("active"))
    # 不在這裡覆蓋 app version；由正式 build_data 版本負責。
    dump(status_path, status)
    print("validation", args.mode, "close_days", report["close_snapshot_days"], "intraday_scans", report["intraday_scan_snapshots"], "matured5", report["matured_5d_rows"], "calibration", calibration["status"], "changed", changed)


if __name__ == "__main__":
    main()
