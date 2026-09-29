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


def source_as_of(payload, trade_date):
    if not isinstance(payload, dict) or not trade_date:
        return None
    now = datetime.now(TW)
    candidates = []
    for key in ("updated_at", "source_updated_at", "generated_at"):
        dt = parse_dt(payload.get(key))
        if dt and dt.date().isoformat() == trade_date and dt <= now + timedelta(minutes=5):
            candidates.append(dt)
    if candidates:
        return max(candidates).isoformat(timespec="seconds")
    return None


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
        if str(row.get("trade_date") or "")[:10] != trade_date:
            continue
        if row.get("session_phase") != "LIVE" and not sector:
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
            # Legacy sector adapter has no row-level quote timestamp and used a
            # close-time fallback. During LIVE, the source payload updated_at is
            # the earliest trustworthy timestamp for this aggregate.
            if row.get("known_at") != as_of:
                row["known_at"] = as_of
                changed = True
        else:
            current = parse_dt(row.get("as_of"))
            if current is None or (limit is not None and current > limit):
                row["as_of"] = as_of
                changed = True
    if changed:
        return write(path, obj)
    text = path.read_bytes()
    return {
        "hash": "sha256:" + hashlib.sha256(text).hexdigest(),
        "bytes": len(text),
    }


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
        file_meta = clamp_live_file(path, intraday_date, intraday_as_of, sector=(key == "sector_intraday"))
        meta.update(file_meta)
        meta["as_of"] = intraday_as_of
        meta["complete"] = True
        meta["build_id"] = active

    if daytrade_date == today and daytrade_as_of:
        for key in daytrade_keys:
            meta = (manifest.get("datasets") or {}).get(key)
            if not meta:
                continue
            path = resolve(root, meta["url"])
            file_meta = clamp_live_file(path, daytrade_date, daytrade_as_of)
            meta.update(file_meta)
            meta["as_of"] = daytrade_as_of
            meta["complete"] = True
            meta["build_id"] = active

    manifest["trade_date"] = today
    manifest["session_phase"] = "LIVE"
    warnings = list((manifest.get("health") or {}).get("warnings") or [])
    live_warning = "LIVE Preview：盤中資料由既有 TWSE MIS 5 分鐘管線橋接至 V2 Canonical Bundle；仍屬 Shadow 驗證。"
    if live_warning not in warnings:
        warnings.append(live_warning)
    manifest.setdefault("health", {})["warnings"] = warnings
    write(manifest_path, manifest)
    print("V2 LIVE patched", active, "intraday", intraday_as_of, "daytrade", daytrade_as_of)


if __name__ == "__main__":
    main()
