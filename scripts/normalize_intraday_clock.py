#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize intraday/daytrade mission date and source clock from quote metadata."""
import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    ip = Path("docs/data/intraday.json")
    obj = load(ip)
    rows = [r for r in (obj.get("rows") or []) if isinstance(r, dict)]
    bridge = obj.get("bridge") or {}
    qlayer = obj.get("quote_layer") or {}
    dates = []
    for v in (bridge.get("trade_date"), obj.get("trade_date"), qlayer.get("trade_date")):
        s = str(v or "")[:10]
        if len(s) == 10:
            dates.append(s)
    for r in rows:
        s = str(r.get("quote_date") or r.get("market_trade_date") or r.get("date") or "")[:10]
        if len(s) == 10:
            dates.append(s)
    if not dates:
        raise SystemExit("intraday effective trade date missing")
    effective = max(dates)
    clocks = []
    for v in (bridge.get("latest_quote_time"), qlayer.get("latest_time"), bridge.get("latest_trade_time"), qlayer.get("latest_trade_time")):
        s = str(v or "").strip()
        if ":" in s:
            clocks.append(s[:8] if len(s) >= 8 else s[:5] + ":00")
    for r in rows:
        if str(r.get("quote_date") or "")[:10] != effective:
            continue
        for k in ("quote_snapshot_time", "quote_time", "structure_time"):
            s = str(r.get(k) or "").strip()
            if ":" in s:
                clocks.append(s[:8] if len(s) >= 8 else s[:5] + ":00")
    latest = max(clocks) if clocks else "13:30:00"
    as_of = f"{effective}T{latest}+08:00"
    obj["trade_date"] = effective
    obj["source_trade_date"] = effective
    obj["as_of"] = as_of
    obj["source_updated_at"] = as_of
    ip.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    dp = Path("docs/data/daytrade.json")
    if dp.exists():
        day = load(dp)
        day["trade_date"] = effective
        day["source_trade_date"] = effective
        day["as_of"] = as_of
        day["source_updated_at"] = as_of
        dp.write_text(json.dumps(day, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    now = datetime.now(ZoneInfo("Asia/Taipei"))
    source_dt = datetime.fromisoformat(as_of)
    age = (now - source_dt).total_seconds()
    print("intraday normalized:", effective, as_of, "rows=", len(rows), "source_age_sec=", round(age, 1))

    # During the cash session, never publish a page labelled current if the
    # official quote snapshot is materially behind. Outside live hours the
    # final 13:30 snapshot is allowed to remain frozen.
    if now.weekday() < 5 and time(9, 5) <= now.time() <= time(13, 31):
        if age > 7 * 60:
            raise SystemExit(f"live intraday source is too old: {age:.0f}s behind")
        if source_dt.date() != now.date():
            raise SystemExit(f"live intraday source date mismatch: {source_dt.date()} != {now.date()}")


if __name__ == "__main__":
    main()
