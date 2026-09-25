from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
TW = ZoneInfo("Asia/Taipei")
APP_VERSION = "1.7.2"
LIVE_COVERAGE_MIN_PCT = 80.0


def load(name):
    p = DATA / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def ymd(value):
    s = str(value or "")
    for i in range(max(0, len(s) - 9)):
        x = s[i : i + 10]
        if len(x) == 10 and x[4] == "-" and x[7] == "-" and x[:4].isdigit() and x[5:7].isdigit() and x[8:10].isdigit():
            return x
    return None


def explicit_date(obj, *keys):
    if not isinstance(obj, dict):
        return None
    for key in keys:
        d = ymd(obj.get(key))
        if d:
            return d
    return None


def dominant_row_date(obj):
    """Trading date represented by actual stock rows, never file generation time."""
    if not isinstance(obj, dict):
        return None
    ds = []
    rows = obj.get("rows") or []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            d = ymd(row.get("quote_date")) or ymd(row.get("date")) or ymd(row.get("trade_date"))
            if d:
                ds.append(d)
    return Counter(ds).most_common(1)[0][0] if ds else None


def intraday_date(obj):
    if not isinstance(obj, dict):
        return None
    bridge = obj.get("bridge") or {}
    return ymd(bridge.get("trade_date")) or dominant_row_date(obj) or explicit_date(obj, "trade_date")


def daytrade_date(obj):
    if not isinstance(obj, dict):
        return None
    # updated_at/source_updated_at are generation timestamps, not quote dates.
    return explicit_date(obj, "source_trade_date", "trade_date") or dominant_row_date(obj)


def latest_chip_date(obj):
    """Support both {rows:[...]} and chip_history's {code:[daily records]} shape."""
    ds = []
    if isinstance(obj, dict):
        rows = obj.get("rows")
        iterables = [rows] if isinstance(rows, list) else [v for v in obj.values() if isinstance(v, list)]
        for records in iterables:
            for row in records:
                if not isinstance(row, dict):
                    continue
                d = ymd(row.get("chip_date")) or ymd(row.get("foreign_date")) or ymd(row.get("date"))
                if d:
                    ds.append(d)
    return max(ds) if ds else explicit_date(obj, "trade_date", "date")


def intraday_quality(obj):
    if not isinstance(obj, dict):
        return {"quote_rows": 0, "row_count": 0, "quote_coverage_pct": 0.0, "latest_quote_time": None, "latest_trade_time": None, "structure_latest_time": None, "bridge_rows": 0, "source": None}
    rows = obj.get("rows") or []
    q = obj.get("quote_layer") or {}
    b = obj.get("bridge") or {}
    row_count = len(rows) if isinstance(rows, list) else 0
    quote_rows = int(q.get("coverage") or 0)
    coverage_pct = round(quote_rows / row_count * 100.0, 1) if row_count else 0.0
    return {
        "quote_rows": quote_rows,
        "row_count": row_count,
        "quote_coverage_pct": coverage_pct,
        "coverage_min_pct": LIVE_COVERAGE_MIN_PCT,
        "latest_quote_time": q.get("latest_time") or b.get("latest_quote_time"),
        "latest_trade_time": q.get("latest_trade_time") or b.get("latest_trade_time"),
        "structure_latest_time": q.get("structure_latest_time") or b.get("latest_structure_time"),
        "bridge_rows": int(b.get("bridged_rows") or 0),
        "source": q.get("source") or b.get("source"),
    }


def taipei_cash_session(now):
    minute = now.hour * 60 + now.minute
    return now.weekday() < 5 and 8 * 60 + 55 <= minute <= 13 * 60 + 35


def main():
    status = load("status.json")
    market = load("market.json")
    close = load("close.json")
    intra = load("intraday.json")
    hourly = load("hourly.json")
    daytrade = load("daytrade.json")
    chips = load("chip_history.json")

    dates = {
        "market": explicit_date(market, "trade_date"),
        "close": explicit_date(close, "trade_date"),
        "intraday": intraday_date(intra),
        "hourly": explicit_date(hourly, "trade_date"),
        "daytrade": daytrade_date(daytrade),
        "chips": latest_chip_date(chips),
    }
    valid = sorted(d for d in dates.values() if d)
    newest = valid[-1] if valid else None
    completed_candidates = [d for d in (dates.get("market"), dates.get("close")) if d]
    latest_completed = max(completed_candidates) if completed_candidates else newest
    lagging = [k for k, d in dates.items() if d and latest_completed and d < latest_completed]

    intraday_stale = bool(latest_completed and (not dates.get("intraday") or dates["intraday"] < latest_completed))
    daytrade_stale = bool(
        latest_completed
        and (
            not dates.get("daytrade")
            or dates["daytrade"] < latest_completed
            or (dates.get("intraday") and dates.get("daytrade") != dates.get("intraday"))
        )
    )

    now = datetime.now(TW)
    today = now.date().isoformat()
    session_open = taipei_cash_session(now)
    iq = intraday_quality(intra)
    live_quote_quality_ok = bool(
        iq["quote_coverage_pct"] >= LIVE_COVERAGE_MIN_PCT
        and iq.get("latest_quote_time")
    )
    intraday_live_ready = bool(
        session_open
        and dates.get("intraday") == today
        and not intraday_stale
        and live_quote_quality_ok
    )
    daytrade_actionable = bool(
        intraday_live_ready
        and dates.get("daytrade") == today
        and not daytrade_stale
    )

    if intraday_stale:
        intraday_state = "stale_fallback_close"
    elif intraday_live_ready:
        intraday_state = "live"
    elif session_open:
        intraday_state = "degraded_fallback_close"
    else:
        intraday_state = "last_session_reference"

    if daytrade_stale:
        daytrade_state = "disabled_stale"
    elif daytrade_actionable:
        daytrade_state = "live_actionable"
    elif session_open:
        daytrade_state = "disabled_not_live"
    else:
        daytrade_state = "reference_only_market_closed"

    out = {
        "app_version": APP_VERSION,
        "data_engine_version": status.get("version"),
        "generated_at": now.isoformat(timespec="seconds"),
        "newest_trade_date": newest,
        "latest_completed_trade_date": latest_completed,
        "dates": dates,
        "date_basis": {
            "market": "market.trade_date",
            "close": "close.trade_date",
            "intraday": "MIS bridge.trade_date, then dominant row quote_date/date",
            "hourly": "hourly.trade_date",
            "daytrade": "source/row quote date; never updated_at",
            "chips": "latest dated chip-history record across symbols",
        },
        "lagging_sources": lagging,
        "freshness": {
            "intraday_stale": intraday_stale,
            "daytrade_stale": daytrade_stale,
        },
        "operational": {
            "taipei_now": now.isoformat(timespec="seconds"),
            "taipei_today": today,
            "cash_session_open_at_build": session_open,
            "intraday_live_ready_at_build": intraday_live_ready,
            "daytrade_actionable_at_build": daytrade_actionable,
            "intraday_state": intraday_state,
            "daytrade_state": daytrade_state,
            "intraday_quality": iq,
        },
        "effective_sources": {
            "swing_cards": "intraday" if intraday_live_ready else "close",
            "daytrade": "daytrade" if daytrade_actionable else "disabled_not_actionable",
        },
        "usability": {
            "close": "ready" if dates.get("close") else "unavailable",
            "intraday": intraday_state,
            "daytrade": daytrade_state,
            "hourly": "ready" if dates.get("hourly") else "unavailable",
            "chips": "ready" if dates.get("chips") else "unavailable",
        },
        "rules": {
            "intraday": "只有台北現貨盤中、行情日期為今天且TWSE MIS個股覆蓋達門檻時才作為即時找波段來源；其他時間使用最近完整close",
            "close": "最近完成交易日盤後波段資料",
            "hourly": "60分K波段骨架",
            "daytrade": "只有台北現貨盤中且MIS即時層達標才可顯示可執行當沖；收盤後僅能視為歷史回顧，不作現在可執行訊號",
            "chips": "最近已公布完成交易日籌碼，不冒充即時資料",
        },
        "sources": {
            "quote": "TWSE MIS",
            "market_and_institutional": "TWSE / TPEx official data",
        },
    }
    (DATA / "system_status.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
