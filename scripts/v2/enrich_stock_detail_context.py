#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"hash": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(), "bytes": len(text.encode("utf-8"))}


def rows_of(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "items", "data", "stocks", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def trade_date_of(payload, rows):
    dates = []
    if isinstance(payload, dict):
        for key in ("trade_date", "source_trade_date", "date"):
            value = str(payload.get(key) or "")[:10]
            if len(value) == 10:
                dates.append(value)
    for row in rows:
        value = str(row.get("quote_date") or row.get("market_trade_date") or row.get("date") or "")[:10]
        if len(value) == 10:
            dates.append(value)
    return max(dates) if dates else None


def num(value):
    try:
        value = float(value)
        return value if value == value else None
    except (TypeError, ValueError):
        return None


def history_bars(payload):
    if isinstance(payload, dict):
        raw = payload.get("bars") or payload.get("items") or payload.get("history") or payload.get("data") or []
    elif isinstance(payload, list):
        raw = payload
    else:
        raw = []
    out = []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) >= 5:
            date = str(item[0] or "")[:10]
            o, h, l, c = (num(item[i]) for i in range(1, 5))
            v = num(item[5]) if len(item) > 5 else None
        elif isinstance(item, dict):
            date = str(item.get("trade_date") or item.get("date") or item.get("quote_date") or "")[:10]
            o = num(item.get("open"))
            h = num(item.get("high"))
            l = num(item.get("low"))
            c = num(item.get("close"))
            v = num(item.get("volume"))
        else:
            continue
        if len(date) == 10 and c is not None and h is not None and l is not None:
            out.append({"date": date, "open": o, "high": h, "low": l, "close": c, "volume": v})
    out.sort(key=lambda x: x["date"])
    return out


def avg(values):
    xs = [float(v) for v in values if num(v) is not None]
    return sum(xs) / len(xs) if xs else None


def atr14(bars):
    if len(bars) < 15:
        return None
    tr = []
    for i in range(1, len(bars)):
        b, prev = bars[i], bars[i - 1]
        tr.append(max(b["high"] - b["low"], abs(b["high"] - prev["close"]), abs(b["low"] - prev["close"])))
    return avg(tr[-14:])


def detect_launch_context(history_root: Path, code: str):
    path = history_root / f"{code}.json"
    if not path.exists():
        return None
    try:
        bars = history_bars(load(path))
    except Exception:
        return None
    if len(bars) < 35:
        return None

    current = bars[-1]["close"]
    atr = atr14(bars)
    start = max(20, len(bars) - 95)
    candidates = []
    for i in range(start, len(bars)):
        pre = bars[i - 20:i]
        b = bars[i]
        ph = max(x["high"] for x in pre)
        pl = min(x["low"] for x in pre)
        volumes = [x["volume"] for x in pre if x.get("volume") is not None and x["volume"] > 0]
        av = avg(volumes)
        vr = (b.get("volume") / av) if av and b.get("volume") else None
        width = ((ph - pl) / pl * 100) if pl > 0 else None
        break_pct = ((b["close"] - ph) / ph * 100) if ph > 0 else None
        closes_above = b["close"] > ph * 1.003
        volume_ok = vr is not None and vr >= 1.15
        tight = width is not None and width <= 25
        positive = b.get("open") is None or b["close"] >= b["open"]
        if not (closes_above and volume_ok and tight and positive):
            continue
        follow = bars[i + 1:]
        min_after = min((x["close"] for x in follow), default=b["close"])
        if current < ph * 0.96 or min_after < ph * 0.90:
            continue
        score = (2 if vr >= 1.5 else 1.2 if vr >= 1.25 else 0.6)
        score += (1.6 if width <= 15 else 1 if width <= 20 else 0.5)
        score += 1 if break_pct is not None and break_pct >= 2 else 0.5
        if i >= len(bars) - 25:
            score += 0.6
        candidates.append({
            "date": b["date"], "index": i, "price": ph, "break_close": b["close"],
            "volume_ratio": vr, "width_pct": width, "break_pct": break_pct,
            "score": score, "atr": atr,
        })

    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x["index"], -x["score"]))
    latest = candidates[0]
    cluster = [x for x in candidates if latest["index"] - x["index"] <= 18]
    origin = sorted(cluster, key=lambda x: (x["index"], -x["score"]))[0] if cluster else latest
    return {
        "price": origin["price"],
        "breakout": origin["break_close"],
        "date": origin["date"],
        "volume_ratio": origin["volume_ratio"],
        "width_pct": origin["width_pct"],
        "break_pct": origin["break_pct"],
        "atr": origin["atr"],
        "kind": "日K帶量突破基準",
        "source": "20日平台上緣＋帶量突破",
        "fallback": False,
    }


COMMON = (
    "code", "name", "market", "industry_name", "sector_group", "close", "high", "low", "day_change",
    "volume", "avg_volume20", "avg_turnover20", "avg_turnover20_mn", "vol_x", "vwap", "vwap_dist", "pace", "ret15", "ret60",
    "current_turnover", "recent_turnover", "previous_turnover", "quote_bid1", "quote_ask1", "quote_volume_lots",
    "quote_date", "quote_time", "quote_snapshot_time", "quote_source", "quote_carried", "quote_has_trade",
    "amplitude_pct", "range_position_pct", "amplitude_regime", "stage_reason", "structure_confidence", "structure_time",
    "chip_date", "foreign_date", "trust_date", "dealer_date", "sbl_date", "margin_date",
    "chip_checked_at", "chip_check_health", "chip_check_latest_attempt_date",
    "chip_background", "chip_score", "chip_coverage_pct", "sector_score", "sector_score_source", "sector_score_label",
    "sector_hot_count", "industry_hot_count", "sector_hot_ratio", "liquidity_level",
    "support", "resistance", "reasons", "overheat_reasons", "stage_signals", "stage_risks",
)
CLOSE = (
    "ma5", "ma10", "ma20", "ma60", "ma5_slope5_pct", "ma10_slope5_pct", "ma20_slope5_pct", "ma60_slope5_pct",
    "dist20", "ret3", "ret5", "ret10", "ret20", "rsi", "macd_h", "macd_acc", "kd_k", "kd_d", "kd_cross_up",
    "sar", "sar_state", "sar_flip_age", "break3", "break20", "trend", "trend60",
    "platform_high20", "platform_low20", "platform_width20_pct", "breakout_pct", "recent_breakout_age",
    "recent_breakout_volume_x", "recent_breakout_width_pct", "failed_breakout", "close_position_pct", "upper_wick_pct", "body_pct",
    "technical_model_version", "technical_score_legacy", "technical_score_v2", "technical_score_delta",
    "technical_confidence_v2", "technical_components_v2", "technical_lifecycle_v2",
    "technical_verdict_v2", "technical_summary_v2", "technical_relative_v2",
    "foreign_3buy", "foreign_net_latest", "foreign_3d_net", "foreign_5d_net", "foreign_20d_net",
    "foreign_buy_days_10", "foreign_streak", "foreign_3d_volume_pct",
    "trust_net_latest", "trust_3d_net", "trust_5d_net", "trust_buy_days_10", "trust_streak",
    "sbl_3down", "sbl_1d_pct", "sbl_3change_pct", "sbl_5d_pct",
    "margin_1d_pct", "margin_3d_pct", "margin_5d_pct", "margin_status",
    "chip_model_version", "chip_score_v2_raw", "chip_score_v2", "chip_score_legacy", "chip_score_delta",
    "chip_confidence_v2", "chip_verdict_v2", "chip_summary_v2", "chip_components_v2",
    "sector_model_version", "sector_score_v2", "sector_confidence_v2", "sector_verdict_v2",
    "sector_summary_v2", "sector_components_v2", "sector_member_count_v2",
    "liquidity_model_version", "liquidity_score_v2", "liquidity_confidence_v2", "liquidity_verdict_v2",
    "liquidity_summary_v2", "liquidity_components_v2", "liquidity_alerts_v2",
    "median_turnover20", "min_turnover20", "turnover_cv20", "turnover_days_ge30m20", "turnover_days_ge80m20",
    "turnover_today", "turnover_vs_median20", "price_impact_median20",
    "swing_components", "sector_detail",
)
INTRADAY = (
    "intraday_score", "intraday_components", "technical_score", "trend5", "break3", "break12",
    "multi_timeframe", "relative_multiframe", "structure_source", "structure_volume_verified", "dynamic_thresholds",
)
DAYTRADE = (
    "daytrade_score", "daytrade_state", "daytrade_headline", "daytrade_components", "daytrade_reasons",
    "daytrade_risks", "daytrade_turnover_acceleration", "daytrade_dynamic_mode", "source_intraday_score",
)
HOURLY60 = (
    "category60", "is_candidate", "data_status", "exclusion_reason", "score60", "combined_score",
    "entry_light", "entry_light_emoji", "entry_light_label", "entry_light_reason",
    "price", "ma20_60", "ma60_60", "ma240_60", "dir20", "dir60", "dir240",
    "s20_5", "s60_5", "s240_5", "slope_diff", "gap20_60_pct", "cross_age",
    "price_vs20_60_pct", "above240", "overhead240_pct", "orderly", "vol_ratio60day",
)


def hourly_map(legacy_root: Path):
    path = legacy_root / "hourly.json"
    if not path.exists():
        return {}, {"available": False, "trade_date": None, "updated_at": None}
    try:
        payload = load(path)
    except Exception:
        return {}, {"available": False, "trade_date": None, "updated_at": None}
    rows = payload.get("all_rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        rows = payload.get("rows") if isinstance(payload, dict) else []
    by_code = {
        str(row.get("code")): row
        for row in (rows or [])
        if isinstance(row, dict) and row.get("code")
    }
    meta = {
        "available": bool(by_code),
        "trade_date": payload.get("trade_date") if isinstance(payload, dict) else None,
        "updated_at": payload.get("updated_at") if isinstance(payload, dict) else None,
        "method": payload.get("method") if isinstance(payload, dict) else None,
        "entry_light_rule": payload.get("entry_light_rule") if isinstance(payload, dict) else None,
    }
    return by_code, meta


def compact_hourly(row, meta):
    if not isinstance(row, dict):
        return None
    out = {key: row.get(key) for key in HOURLY60 if key in row}
    out["trade_date"] = meta.get("trade_date")
    out["updated_at"] = meta.get("updated_at")
    out["engine"] = "legacy_hourly60_lifecycle"
    out["semantics"] = {
        "lifecycle": "60分K生命週期分類；不取代 V2 Stage",
        "entry_light": "位置／延伸風險；不代表買賣指令",
    }
    return out


def compact(row, context, h60=None, hmeta=None, launch=None):
    keys = list(COMMON)
    if context == "close":
        keys += list(CLOSE)
    elif context == "intraday":
        keys += list(INTRADAY)
    else:
        keys += list(INTRADAY) + list(DAYTRADE)
    out = {key: row.get(key) for key in keys if key in row}
    out["hourly60"] = compact_hourly(h60, hmeta or {}) if h60 else None
    if launch:
        out["launch_context"] = launch
    return out


def enrich(*, legacy_root: Path, root: Path):
    manifest_path = root / "current_manifest.json"
    manifest = load(manifest_path)
    build_id = manifest["active_build_id"]
    build_dir = root / "builds" / build_id
    counts = {}
    hmap, hmeta = hourly_map(legacy_root)
    history_root = legacy_root / "history"

    for context, source_name, decision_key in (
        ("close", "close.json", "decision_close_detail"),
        ("intraday", "intraday.json", "decision_intraday_detail"),
        ("daytrade", "daytrade.json", "decision_daytrade_detail"),
    ):
        payload = load(legacy_root / source_name)
        rows = rows_of(payload)
        items = {}
        launches = 0
        for row in rows:
            if not isinstance(row, dict) or not row.get("code"):
                continue
            code = str(row.get("code"))
            launch = detect_launch_context(history_root, code) if context == "close" and history_root.exists() else None
            if launch:
                launches += 1
            items[code] = compact(row, context, hmap.get(code), hmeta, launch)
        trade_date = trade_date_of(payload, rows)
        decision_meta = (manifest.get("datasets") or {}).get(decision_key) or {}
        obj = {
            "schema_version": "1.2.0",
            "build_id": build_id,
            "context": context.upper(),
            "trade_date": trade_date,
            "as_of": decision_meta.get("as_of"),
            "hourly60_trade_date": hmeta.get("trade_date"),
            "hourly60_updated_at": hmeta.get("updated_at"),
            "items": items,
        }
        filename = f"stock-detail-{context}.json"
        meta = write(build_dir / filename, obj)
        manifest.setdefault("datasets", {})[f"stock_detail_{context}"] = {
            "url": f"./data/builds/{build_id}/{filename}",
            "hash": meta["hash"],
            "bytes": meta["bytes"],
            "complete": True,
            "as_of": decision_meta.get("as_of"),
            "known_at": decision_meta.get("known_at"),
            "build_id": build_id,
        }
        counts[context] = {"items": len(items), "launch_context": launches}

    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    note = "個股詳情已分任務補入同 Atomic Build 的盤中／盤後／當沖證據快照；評分解釋只呈現 Engine 已算出的分項，不由前端重算。"
    if note not in warnings:
        warnings.append(note)
    hnote = "60分K生命週期與進場位置燈號已從既有 hourly Engine 帶回 V2 個股證據；只顯示 Engine 結果，不由前端重新判定。"
    if hnote not in warnings:
        warnings.append(hnote)
    lnote = "盤後個股詳情已預存最近有效日K平台帶量突破起漲基準；即使前端歷史K檔暫時不可用，也不直接退回20MA。"
    if lnote not in warnings:
        warnings.append(lnote)
    write(manifest_path, manifest)
    print("stock detail evidence OK", counts, "hourly60", len(hmap), hmeta.get("trade_date"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-root", default=str(ROOT / "docs" / "data"))
    ap.add_argument("--root", default=str(ROOT / "docs" / "v2" / "data"))
    args = ap.parse_args()
    enrich(legacy_root=Path(args.legacy_root), root=Path(args.root))


if __name__ == "__main__":
    main()
