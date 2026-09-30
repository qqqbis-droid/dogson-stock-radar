#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast-lane publish gate.

This gate proves the quote layer is current without pretending the slower 5m/60m
structure was rebuilt in the same run. The UI/decision bundle may keep the last
verified structure, but current price/date/market context must be fresh.
"""
from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parents[1] / "docs" / "data"
TW = ZoneInfo("Asia/Taipei")
MIN_ROWS = 300
MIN_QUOTED = 300
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
    quoted = int(bridge.get("quoted_rows") or qlayer.get("quoted_rows") or 0)
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
    if quoted < MIN_QUOTED:
        errors.append(f"fast MIS quoted rows too small: {quoted}")
    if not td or td != dd:
        errors.append(f"intraday/daytrade date mismatch: {td}/{dd}")
    if live:
        if td != now.date().isoformat():
            errors.append(f"live quote date is not today: {td}")
        if age is None or age > MAX_LIVE_QUOTE_AGE_SEC:
            errors.append(f"live quote source too old: {age}s")
    report = {
        "checked_at": now.isoformat(timespec="seconds"),
        "mode": "FAST_QUOTE_LANE",
        "trade_date": td,
        "as_of": as_of,
        "quote_age_sec": round(age, 1) if age is not None else None,
        "quoted_rows": quoted,
        "intraday_rows": len(rows),
        "daytrade_rows": len(drows),
        "deep_structure_time": bridge.get("latest_structure_time"),
        "publishable": not errors,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("FAST INTRADAY PUBLISH BLOCKED: " + " | ".join(errors))


if __name__ == "__main__":
    main()
