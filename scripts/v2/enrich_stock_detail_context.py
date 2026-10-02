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


COMMON = (
    "code", "name", "market", "industry_name", "sector_group", "close", "high", "low", "day_change",
    "volume", "avg_volume20", "avg_turnover20", "avg_turnover20_mn", "vol_x", "vwap", "vwap_dist", "pace", "ret15", "ret60",
    "current_turnover", "recent_turnover", "previous_turnover", "quote_bid1", "quote_ask1", "quote_volume_lots",
    "quote_date", "quote_time", "quote_snapshot_time", "quote_source", "quote_carried", "quote_has_trade",
    "amplitude_pct", "range_position_pct", "amplitude_regime", "stage_reason", "structure_confidence", "structure_time",
    # Source dates are evidence, not build metadata. Keep them beside the chip
    # metrics so the UI can truthfully disclose whether EOD capital data is from
    # the current trading day or a prior completed session. chip_checked_at is
    # a separate provenance clock: it tells when our system last queried sources.
    "chip_date", "foreign_date", "trust_date", "dealer_date", "sbl_date", "margin_date",
    "chip_checked_at", "chip_check_health", "chip_check_latest_attempt_date",
    "chip_background", "chip_score", "chip_coverage_pct", "sector_score", "sector_score_source", "sector_score_label",
    "sector_hot_count", "industry_hot_count", "sector_hot_ratio", "liquidity_level",
    "support", "resistance", "reasons", "overheat_reasons", "stage_signals", "stage_risks",
)
CLOSE = (
    "ma5", "ma10", "ma20", "dist20", "ret5", "ret20", "rsi", "macd_h", "macd_acc", "break3", "break20", "trend",
    "foreign_3buy", "foreign_net_latest", "foreign_3d_net", "sbl_3down", "sbl_3change_pct", "trust_net_latest",
    "margin_3d_pct", "margin_status", "swing_components", "sector_detail",
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


def compact(row, context, h60=None, hmeta=None):
    keys = list(COMMON)
    if context == "close":
        keys += list(CLOSE)
    elif context == "intraday":
        keys += list(INTRADAY)
    else:
        keys += list(INTRADAY) + list(DAYTRADE)
    out = {key: row.get(key) for key in keys if key in row}
    out["hourly60"] = compact_hourly(h60, hmeta or {}) if h60 else None
    return out


def enrich(*, legacy_root: Path, root: Path):
    manifest_path = root / "current_manifest.json"
    manifest = load(manifest_path)
    build_id = manifest["active_build_id"]
    build_dir = root / "builds" / build_id
    counts = {}
    hmap, hmeta = hourly_map(legacy_root)

    for context, source_name, decision_key in (
        ("close", "close.json", "decision_close_detail"),
        ("intraday", "intraday.json", "decision_intraday_detail"),
        ("daytrade", "daytrade.json", "decision_daytrade_detail"),
    ):
        payload = load(legacy_root / source_name)
        rows = rows_of(payload)
        items = {
            str(row.get("code")): compact(row, context, hmap.get(str(row.get("code"))), hmeta)
            for row in rows if isinstance(row, dict) and row.get("code")
        }
        trade_date = trade_date_of(payload, rows)
        decision_meta = (manifest.get("datasets") or {}).get(decision_key) or {}
        obj = {
            "schema_version": "1.1.0",
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
        counts[context] = len(items)

    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    note = "個股詳情已分任務補入同 Atomic Build 的盤中／盤後／當沖證據快照；評分解釋只呈現 Engine 已算出的分項，不由前端重算。"
    if note not in warnings:
        warnings.append(note)
    hnote = "60分K生命週期與進場位置燈號已從既有 hourly Engine 帶回 V2 個股證據；只顯示 Engine 結果，不由前端重新判定。"
    if hnote not in warnings:
        warnings.append(hnote)
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
