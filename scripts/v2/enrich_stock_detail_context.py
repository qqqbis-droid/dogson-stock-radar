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
    # Source dates are evidence, not build metadata.  Keep them beside the chip
    # metrics so the UI can truthfully disclose whether EOD capital data is from
    # the current trading day or a prior completed session.
    "chip_date", "foreign_date", "trust_date", "dealer_date", "sbl_date", "margin_date",
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


def compact(row, context):
    keys = list(COMMON)
    if context == "close":
        keys += list(CLOSE)
    elif context == "intraday":
        keys += list(INTRADAY)
    else:
        keys += list(INTRADAY) + list(DAYTRADE)
    return {key: row.get(key) for key in keys if key in row}


def enrich(*, legacy_root: Path, root: Path):
    manifest_path = root / "current_manifest.json"
    manifest = load(manifest_path)
    build_id = manifest["active_build_id"]
    build_dir = root / "builds" / build_id
    counts = {}

    for context, source_name, decision_key in (
        ("close", "close.json", "decision_close_detail"),
        ("intraday", "intraday.json", "decision_intraday_detail"),
        ("daytrade", "daytrade.json", "decision_daytrade_detail"),
    ):
        payload = load(legacy_root / source_name)
        rows = rows_of(payload)
        items = {str(row.get("code")): compact(row, context) for row in rows if isinstance(row, dict) and row.get("code")}
        trade_date = trade_date_of(payload, rows)
        decision_meta = (manifest.get("datasets") or {}).get(decision_key) or {}
        obj = {
            "schema_version": "1.0.0",
            "build_id": build_id,
            "context": context.upper(),
            "trade_date": trade_date,
            "as_of": decision_meta.get("as_of"),
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
    write(manifest_path, manifest)
    print("stock detail evidence OK", counts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-root", default=str(ROOT / "docs" / "data"))
    ap.add_argument("--root", default=str(ROOT / "docs" / "v2" / "data"))
    args = ap.parse_args()
    enrich(legacy_root=Path(args.legacy_root), root=Path(args.root))


if __name__ == "__main__":
    main()
