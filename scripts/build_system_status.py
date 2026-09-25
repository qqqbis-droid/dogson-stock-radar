from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
TW = ZoneInfo("Asia/Taipei")
APP_VERSION = "1.7.1"


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
    """Trading date represented by the actual stock rows, not file generated_at."""
    if not isinstance(obj, dict):
        return None
    ds = []
    rows = obj.get("rows") or []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            d = (
                ymd(row.get("quote_date"))
                or ymd(row.get("date"))
                or ymd(row.get("trade_date"))
            )
            if d:
                ds.append(d)
    return Counter(ds).most_common(1)[0][0] if ds else None


def intraday_date(obj):
    if not isinstance(obj, dict):
        return None
    bridge = obj.get("bridge") or {}
    return (
        ymd(bridge.get("trade_date"))
        or dominant_row_date(obj)
        or explicit_date(obj, "trade_date")
    )


def daytrade_date(obj):
    if not isinstance(obj, dict):
        return None
    # Important: updated_at/source_updated_at are generation timestamps, not
    # quote dates. A file rebuilt after midnight can still contain prior-session
    # prices, so only source/row trading dates are allowed here.
    return (
        explicit_date(obj, "source_trade_date", "trade_date")
        or dominant_row_date(obj)
    )


def latest_chip_date(obj):
    """Support both {rows:[...]} and chip_history's {code:[daily records]} shape."""
    ds = []
    if isinstance(obj, dict):
        rows = obj.get("rows")
        if isinstance(rows, list):
            iterables = [rows]
        else:
            iterables = [v for v in obj.values() if isinstance(v, list)]
        for records in iterables:
            for row in records:
                if not isinstance(row, dict):
                    continue
                d = ymd(row.get("chip_date")) or ymd(row.get("foreign_date")) or ymd(row.get("date"))
                if d:
                    ds.append(d)
    return max(ds) if ds else explicit_date(obj, "trade_date", "date")


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

    out = {
        "app_version": APP_VERSION,
        "data_engine_version": status.get("version"),
        "generated_at": datetime.now(TW).isoformat(timespec="seconds"),
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
        "effective_sources": {
            "swing_cards": "close" if intraday_stale else "intraday",
            "daytrade": "disabled_stale" if daytrade_stale else "daytrade",
        },
        "usability": {
            "close": "ready" if dates.get("close") else "unavailable",
            "intraday": "fallback_to_close" if intraday_stale else "ready",
            "daytrade": "disabled_stale" if daytrade_stale else "ready",
            "hourly": "ready" if dates.get("hourly") else "unavailable",
            "chips": "ready" if dates.get("chips") else "unavailable",
        },
        "rules": {
            "intraday": "近即時5分雷達；若日期落後最近完成交易日，個股卡片自動改用close，不把舊盤中訊號當最新",
            "close": "最近完成交易日盤後波段資料",
            "hourly": "60分K波段骨架",
            "daytrade": "獨立當沖資料；若來源行情日期落後，停用舊當沖訊號，不以檔案生成日冒充交易日",
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
