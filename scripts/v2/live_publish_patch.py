#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

TW = timezone(timedelta(hours=8))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    return {
        "hash": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "bytes": len(text.encode("utf-8")),
    }


def file_meta(path: Path):
    raw = path.read_bytes()
    return {"hash": "sha256:" + hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def rows_of(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "items", "data", "stocks", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def trade_date_of(payload):
    rows = rows_of(payload)
    candidates = []
    if isinstance(payload, dict):
        for key in ("trade_date", "date"):
            value = payload.get(key)
            if isinstance(value, str) and len(value) >= 10:
                candidates.append(value[:10])
    for row in rows:
        if not isinstance(row, dict):
            continue
        value = row.get("quote_date") or row.get("market_trade_date") or row.get("date")
        if isinstance(value, str) and len(value) >= 10:
            candidates.append(value[:10])
    return max(candidates) if candidates else None


def parse_dt(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(TW)
    except Exception:
        return None


def parse_clock(trade_date, value):
    if not trade_date or not isinstance(value, str) or not value:
        return None
    if "T" in value:
        return parse_dt(value)
    try:
        clock = value.strip()[:8]
        if len(clock) == 5:
            clock += ":00"
        return datetime.fromisoformat(f"{trade_date}T{clock}+08:00").astimezone(TW)
    except Exception:
        return None


def source_as_of(payload, trade_date):
    """Bind V2 decisions to the source market clock, not file-write time.

    ``normalize_intraday_clock.py`` writes the canonical official MIS snapshot
    timestamp to ``as_of``.  ``updated_at`` may be a few seconds later because
    subsequent enrichment writes the file again.  Using that write time would
    make V2 appear newer than its source and fail the exact source lock.
    """
    if not isinstance(payload, dict) or not trade_date:
        return None
    now = datetime.now(TW)

    explicit = parse_dt(payload.get("as_of"))
    if explicit and explicit.date().isoformat() == trade_date and explicit <= now + timedelta(minutes=5):
        return explicit.isoformat(timespec="seconds")

    candidates = []
    for key in ("source_updated_at", "updated_at", "generated_at"):
        dt = parse_dt(payload.get(key))
        if dt and dt.date().isoformat() == trade_date and dt <= now + timedelta(minutes=5):
            candidates.append(dt)
    if candidates:
        return max(candidates).isoformat(timespec="seconds")
    return None


def fresh_structure_codes(payload, trade_date, now, max_age_minutes=20):
    fresh = set()
    for row in rows_of(payload):
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        qd = str(row.get("quote_date") or row.get("date") or "")[:10]
        if not code or qd != trade_date:
            continue
        structure_date = str(row.get("structure_date") or row.get("date") or "")[:10]
        if structure_date and structure_date != trade_date:
            continue
        if row.get("quote_price_validated") is False:
            continue
        st = parse_clock(trade_date, row.get("structure_time"))
        if not st:
            continue
        age = (now - st).total_seconds() / 60.0
        if -5 <= age <= max_age_minutes:
            fresh.add(code)
    return fresh


def resolve(root: Path, url: str):
    raw = str(url)
    if raw.startswith("./data/"):
        return root / raw[len("./data/"):]
    return root / raw.lstrip("./")


def iter_records(obj):
    if isinstance(obj, list):
        yield from (row for row in obj if isinstance(row, dict))
    elif isinstance(obj, dict) and isinstance(obj.get("items"), dict):
        yield from (row for row in obj["items"].values() if isinstance(row, dict))


def clamp_live_file(path: Path, trade_date: str, as_of: str, *, sector=False):
    obj = load(path)
    changed = False
    limit = parse_dt(as_of)
    for row in iter_records(obj):
        row_trade_date = str(row.get("trade_date") or "")[:10]
        if row_trade_date and row_trade_date != trade_date:
            continue
        if row.get("session_phase") not in (None, "LIVE") and not sector:
            continue
        if sector:
            if row.get("session_phase") != "LIVE":
                row["session_phase"] = "LIVE"
                changed = True
            if row.get("freshness") != "LIVE":
                row["freshness"] = "LIVE"
                changed = True
            if row.get("as_of") != as_of:
                row["as_of"] = as_of
                changed = True
            if row.get("known_at") != as_of:
                row["known_at"] = as_of
                changed = True
        elif "as_of" in row:
            current = parse_dt(row.get("as_of"))
            if current is None or (limit is not None and current > limit):
                row["as_of"] = as_of
                changed = True
    return write(path, obj) if changed else file_meta(path)


def gate_structure_file(path: Path, fresh_codes: set[str], *, mission: str):
    obj = load(path)
    changed = False
    blocker = "5分結構尚未更新到目前時段；保留即時報價，但不可視為可執行訊號"
    for row in iter_records(obj):
        code = str(row.get("code") or "").strip()
        if not code or code in fresh_codes:
            continue
        if row.get("actionable") is not False:
            row["actionable"] = False
            changed = True
        desired_action = "WATCH"
        if row.get("action_state") != desired_action:
            row["action_state"] = desired_action
            changed = True
        desired_bucket = "STALE" if mission == "daytrade" else "RESEARCH_ONLY"
        if row.get("opportunity_bucket") != desired_bucket:
            row["opportunity_bucket"] = desired_bucket
            changed = True
        blockers = list(row.get("blockers") or [])
        if blocker not in blockers:
            row["blockers"] = ([blocker] + blockers)[:3]
            changed = True
        overlays = list(row.get("risk_overlays") or [])
        if "DATA_QUALITY_RISK" not in overlays:
            row["risk_overlays"] = overlays + ["DATA_QUALITY_RISK"]
            changed = True
        missing = list(row.get("missing_fields") or [])
        if "fresh_5m_structure" not in missing:
            row["missing_fields"] = missing + ["fresh_5m_structure"]
            changed = True
    return write(path, obj) if changed else file_meta(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-root", default="docs/data")
    ap.add_argument("--root", default="docs/v2/data")
    args = ap.parse_args()

    legacy_root = Path(args.legacy_root)
    root = Path(args.root)
    manifest_path = root / "current_manifest.json"
    manifest = load(manifest_path)
    intraday = load(legacy_root / "intraday.json")
    daytrade = load(legacy_root / "daytrade.json")

    now = datetime.now(TW)
    today = now.date().isoformat()
    intraday_date = trade_date_of(intraday)
    daytrade_date = trade_date_of(daytrade)
    intraday_as_of = source_as_of(intraday, intraday_date)
    daytrade_as_of = source_as_of(daytrade, daytrade_date)
    live_window = time(9, 0) <= now.time() <= time(13, 40)
    is_live = bool(live_window and intraday_date == today and intraday_as_of)

    if not is_live:
        print("V2 live patch skipped:", {"now": now.isoformat(timespec="seconds"), "intraday_date": intraday_date, "intraday_as_of": intraday_as_of})
        return

    active = manifest["active_build_id"]
    structure_codes = fresh_structure_codes(intraday, intraday_date, now, 20)
    intraday_keys = (
        "sector_intraday",
        "decision_intraday_summary",
        "decision_intraday_index",
        "decision_intraday_detail",
    )
    daytrade_keys = (
        "decision_daytrade_summary",
        "decision_daytrade_index",
        "decision_daytrade_detail",
    )

    for key in intraday_keys:
        meta = (manifest.get("datasets") or {}).get(key)
        if not meta:
            continue
        path = resolve(root, meta["url"])
        result = clamp_live_file(path, intraday_date, intraday_as_of, sector=(key == "sector_intraday"))
        if key.startswith("decision_intraday"):
            result = gate_structure_file(path, structure_codes, mission="intraday")
        meta.update(result)
        meta["as_of"] = intraday_as_of
        meta["complete"] = True
        meta["build_id"] = active

    if daytrade_date == today and daytrade_as_of:
        for key in daytrade_keys:
            meta = (manifest.get("datasets") or {}).get(key)
            if not meta:
                continue
            path = resolve(root, meta["url"])
            clamp_live_file(path, daytrade_date, daytrade_as_of)
            result = gate_structure_file(path, structure_codes, mission="daytrade")
            meta.update(result)
            meta["as_of"] = daytrade_as_of
            meta["complete"] = True
            meta["build_id"] = active

    manifest["trade_date"] = today
    manifest["session_phase"] = "LIVE"
    warnings = list((manifest.get("health") or {}).get("warnings") or [])
    live_warning = "LIVE Preview：盤中資料由既有 TWSE MIS 5 分鐘管線橋接至 V2 Canonical Bundle；仍屬 Shadow 驗證。"
    coverage_warning = f"LIVE 結構 Gate：{len(structure_codes)}/{len(rows_of(intraday))} 檔具 20 分鐘內新鮮 5 分結構；其餘只顯示即時報價/觀察，不提供可執行狀態。"
    for msg in (live_warning, coverage_warning):
        if msg not in warnings:
            warnings.append(msg)
    manifest.setdefault("health", {})["warnings"] = warnings
    write(manifest_path, manifest)
    print("V2 LIVE patched", active, "intraday", intraday_as_of, "daytrade", daytrade_as_of, "fresh_structure", len(structure_codes), "/", len(rows_of(intraday)))


if __name__ == "__main__":
    main()
