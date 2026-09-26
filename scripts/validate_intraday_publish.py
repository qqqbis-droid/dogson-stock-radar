#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail closed when intraday/daytrade data is stale, empty or date/time mismatched."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
TW = ZoneInfo("Asia/Taipei")
MIN_ROWS = 300
MIN_BRIDGED_ROWS = 200
MAX_QUOTE_AGE_MIN = 12
MAX_STRUCTURE_AGE_MIN = 20


def load(name: str) -> dict:
    p = DATA / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def ymd(v) -> str:
    s = str(v or "")
    for i in range(max(0, len(s) - 9)):
        x = s[i : i + 10]
        if len(x) == 10 and x[4] == "-" and x[7] == "-" and x[:4].isdigit() and x[5:7].isdigit() and x[8:10].isdigit():
            return x
    return ""


def dominant_row_date(obj: dict) -> str:
    ds = []
    for r in obj.get("rows") or []:
        if not isinstance(r, dict):
            continue
        d = ymd(r.get("quote_date")) or ymd(r.get("date")) or ymd(r.get("trade_date"))
        if d:
            ds.append(d)
    return Counter(ds).most_common(1)[0][0] if ds else ""


def intraday_date(obj: dict) -> str:
    bridge = obj.get("bridge") or {}
    return ymd(bridge.get("trade_date")) or dominant_row_date(obj) or ymd(obj.get("trade_date"))


def daytrade_date(obj: dict) -> str:
    # updated_at is deliberately excluded: rebuilding a derivative after midnight
    # does not make the underlying quotes a new trading session.
    return ymd(obj.get("source_trade_date")) or dominant_row_date(obj) or ymd(obj.get("trade_date"))


def completed_date(close: dict, market: dict) -> str:
    ds = [ymd(close.get("trade_date")), ymd(market.get("trade_date"))]
    return max((d for d in ds if d), default="")


def age_minutes(value, now: datetime):
    """Return age of an HH:MM[:SS] market clock on today's Taipei date."""
    m = re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?", str(value or ""))
    if not m:
        return None
    hh, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    stamp = now.replace(hour=hh, minute=mm, second=ss, microsecond=0)
    age = (now - stamp).total_seconds() / 60.0
    # Small clock skew is harmless; a large future timestamp is invalid.
    if age < -2:
        return None
    return max(0.0, age)


def main() -> None:
    intra = load("intraday.json")
    day = load("daytrade.json")
    close = load("close.json")
    market = load("market.json")
    irows = intra.get("rows") or []
    drows = day.get("rows") or []
    bridge = intra.get("bridge") or {}
    idate = intraday_date(intra)
    ddate = daytrade_date(day)
    cdate = completed_date(close, market)

    now = datetime.now(TW)
    # Scheduled builds may continue shortly after the close, but minute-level
    # actionability is only enforced while the cash market can still be traded.
    publish_session = now.weekday() < 5 and time(8, 55) <= now.time() <= time(14, 10)
    actionable_session = now.weekday() < 5 and time(9, 5) <= now.time() <= time(13, 35)
    today = now.date().isoformat()
    errors = []

    if len(irows) < MIN_ROWS:
        errors.append(f"intraday rows too small: {len(irows)} < {MIN_ROWS}")
    if len(drows) < MIN_ROWS:
        errors.append(f"daytrade rows too small: {len(drows)} < {MIN_ROWS}")
    if not idate:
        errors.append("intraday effective quote date missing")
    if not ddate:
        errors.append("daytrade effective quote date missing")
    if idate and ddate and idate != ddate:
        errors.append(f"daytrade source date {ddate} != intraday date {idate}")
    if cdate and idate and idate < cdate:
        errors.append(f"intraday date {idate} older than newest completed trade date {cdate}")

    bdate = ymd(bridge.get("trade_date"))
    bridged = int(bridge.get("bridged_rows") or 0)
    quote_time = bridge.get("latest_quote_time")
    structure_time = bridge.get("latest_structure_time")
    quote_age = age_minutes(quote_time, now)
    structure_age = age_minutes(structure_time, now)

    if bdate and idate and bdate != idate:
        errors.append(f"MIS bridge date {bdate} != intraday date {idate}")
    if publish_session:
        if idate != today:
            errors.append(f"active-session intraday date must be today {today}, got {idate or 'missing'}")
        if bdate != today:
            errors.append(f"active-session MIS bridge date must be today {today}, got {bdate or 'missing'}")
        if bridged < MIN_BRIDGED_ROWS:
            errors.append(f"MIS bridged rows too small: {bridged} < {MIN_BRIDGED_ROWS}")

    if actionable_session:
        if quote_age is None:
            errors.append("MIS latest quote clock missing or invalid")
        elif quote_age > MAX_QUOTE_AGE_MIN:
            errors.append(f"MIS quote too old: {quote_age:.1f}m > {MAX_QUOTE_AGE_MIN}m")
        if structure_age is None:
            errors.append("5-minute structure clock missing or invalid")
        elif structure_age > MAX_STRUCTURE_AGE_MIN:
            errors.append(f"5-minute structure too old: {structure_age:.1f}m > {MAX_STRUCTURE_AGE_MIN}m")

    report = {
        "checked_at": now.isoformat(timespec="seconds"),
        "publish_session_guard_active": publish_session,
        "actionability_time_guard_active": actionable_session,
        "today": today,
        "intraday_date": idate or None,
        "daytrade_date": ddate or None,
        "completed_trade_date": cdate or None,
        "intraday_rows": len(irows),
        "daytrade_rows": len(drows),
        "bridge_date": bdate or None,
        "bridged_rows": bridged,
        "latest_quote_time": quote_time,
        "latest_structure_time": structure_time,
        "quote_age_minutes": round(quote_age, 2) if quote_age is not None else None,
        "structure_age_minutes": round(structure_age, 2) if structure_age is not None else None,
        "max_quote_age_minutes": MAX_QUOTE_AGE_MIN,
        "max_structure_age_minutes": MAX_STRUCTURE_AGE_MIN,
        "publishable": not errors,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit("INTRADAY PUBLISH BLOCKED: " + " | ".join(errors))


if __name__ == "__main__":
    main()
