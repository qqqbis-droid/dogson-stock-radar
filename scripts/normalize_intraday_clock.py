#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize intraday/daytrade mission date and source clock from quote metadata.

Live session: `as_of` follows the official MIS snapshot clock so freshness can be
measured honestly. After the cash close: `as_of` follows the latest real trade
clock (normally 13:30), not the later time at which MIS happened to be queried.
"""
import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

TW = ZoneInfo("Asia/Taipei")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def norm_clock(v):
    s = str(v or "").strip()
    if ":" not in s:
        return ""
    return s[:8] if len(s) >= 8 else s[:5] + ":00"


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

    now = datetime.now(TW)
    live_session = now.weekday() < 5 and time(9, 0) <= now.time() <= time(13, 35)

    snapshot_clocks = []
    trade_clocks = []
    for v in (bridge.get("latest_quote_time"), qlayer.get("latest_time")):
        s = norm_clock(v)
        if s:
            snapshot_clocks.append(s)
    for v in (bridge.get("latest_trade_time"), qlayer.get("latest_trade_time")):
        s = norm_clock(v)
        if s:
            trade_clocks.append(s)
    for r in rows:
        if str(r.get("quote_date") or "")[:10] != effective:
            continue
        s = norm_clock(r.get("quote_snapshot_time"))
        if s:
            snapshot_clocks.append(s)
        for k in ("quote_time", "structure_time"):
            s = norm_clock(r.get(k))
            if s:
                trade_clocks.append(s)

    if live_session:
        latest = max(snapshot_clocks or trade_clocks or ["09:00:00"])
        clock_basis = "official_mis_snapshot"
    else:
        latest = max(trade_clocks or ["13:30:00"])
        # Never let a post-close structure/query timestamp drift past the cash close.
        if latest > "13:30:00":
            latest = "13:30:00"
        clock_basis = "latest_real_trade"

    as_of = f"{effective}T{latest}+08:00"
    obj["trade_date"] = effective
    obj["source_trade_date"] = effective
    obj["as_of"] = as_of
    obj["source_updated_at"] = as_of
    obj.setdefault("quote_layer", {})["clock_basis"] = clock_basis
    ip.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    dp = Path("docs/data/daytrade.json")
    if dp.exists():
        day = load(dp)
        day["trade_date"] = effective
        day["source_trade_date"] = effective
        day["as_of"] = as_of
        day["source_updated_at"] = as_of
        day["clock_basis"] = clock_basis
        dp.write_text(json.dumps(day, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    source_dt = datetime.fromisoformat(as_of)
    age = (now - source_dt).total_seconds()
    print("intraday normalized:", effective, as_of, "rows=", len(rows), "source_age_sec=", round(age, 1), "basis=", clock_basis)

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
