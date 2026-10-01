#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast-lane publish gate.

The fast lane proves that the OFFICIAL MIS SNAPSHOT layer is current.  It does
not require every symbol to emit a new ``z`` trade in the same request because
TWSE MIS ``z`` is event-like.  Last-trade coverage is reported separately and
must never be fabricated from bid/ask.
"""
from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parents[1] / "docs" / "data"
TW = ZoneInfo("Asia/Taipei")
MIN_ROWS = 300
MIN_SNAPSHOT_ROWS = 300
MIN_SNAPSHOT_RATIO = 0.70
MAX_LIVE_QUOTE_AGE_SEC = 7 * 60


def load(name):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    intra = load("intraday.json")
    day = load("daytrade.json")
    rows = intra.get("rows") or []
    drows = day.get("rows") or []
    bridge = intra.get("bridge") or {}
    qlayer = intra.get("quote_layer") or {}
    td = str(intra.get("trade_date") or bridge.get("trade_date") or "")[:10]
    dd = str(day.get("source_trade_date") or day.get("trade_date") or "")[:10]
    as_of = str(intra.get("as_of") or "")
    snapshot_rows = int(
        bridge.get("official_snapshot_rows")
        or qlayer.get("official_snapshot_rows")
        or bridge.get("quoted_rows")
        or qlayer.get("quoted_rows")
        or 0
    )
    fresh_trade_rows = int(bridge.get("fresh_trade_rows") or qlayer.get("fresh_trade_rows") or 0)
    carried_trade_rows = int(bridge.get("carried_trade_rows") or qlayer.get("carried_trade_rows") or 0)
    orderbook_only_rows = int(bridge.get("orderbook_only_rows") or qlayer.get("orderbook_only_rows") or 0)
    now = datetime.now(TW)
    live = now.weekday() < 5 and time(9, 5) <= now.time() <= time(13, 31)
    errors = []
    age = None
    try:
        source_dt = datetime.fromisoformat(as_of)
        age = (now - source_dt).total_seconds()
    except Exception:
        errors.append("intraday as_of missing or invalid")

    if len(rows) < MIN_ROWS:
        errors.append(f"intraday rows too small: {len(rows)}")
    if len(drows) < MIN_ROWS:
        errors.append(f"daytrade rows too small: {len(drows)}")
    required_snapshots = max(MIN_SNAPSHOT_ROWS, int(len(rows) * MIN_SNAPSHOT_RATIO)) if rows else MIN_SNAPSHOT_ROWS
    if snapshot_rows < required_snapshots:
        errors.append(f"official MIS snapshot rows too small: {snapshot_rows}/{len(rows)} need>={required_snapshots}")
    if not td or td != dd:
        errors.append(f"intraday/daytrade date mismatch: {td}/{dd}")
    if live:
        if td != now.date().isoformat():
            errors.append(f"live quote date is not today: {td}")
        if age is None or age > MAX_LIVE_QUOTE_AGE_SEC:
            errors.append(f"live official snapshot too old: {age}s")

    report = {
        "checked_at": now.isoformat(timespec="seconds"),
        "mode": "FAST_QUOTE_LANE",
        "trade_date": td,
        "as_of": as_of,
        "quote_age_sec": round(age, 1) if age is not None else None,
        "official_snapshot_rows": snapshot_rows,
        "snapshot_ratio_pct": round(snapshot_rows / len(rows) * 100, 1) if rows else 0,
        "fresh_trade_rows": fresh_trade_rows,
        "carried_trade_rows": carried_trade_rows,
        "orderbook_only_rows": orderbook_only_rows,
        "intraday_rows": len(rows),
        "daytrade_rows": len(drows),
        "deep_structure_time": bridge.get("latest_structure_time"),
        "truth_rule": "publish gate uses official snapshot freshness; last trade must be real or same-day carried",
        "publishable": not errors,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("FAST INTRADAY PUBLISH BLOCKED: " + " | ".join(errors))


if __name__ == "__main__":
    main()
