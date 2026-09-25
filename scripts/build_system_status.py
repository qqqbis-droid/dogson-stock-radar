from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
TW = ZoneInfo("Asia/Taipei")
APP_VERSION = "1.7.0"


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


def object_date(obj, keys=()):
    for key in keys:
        d = ymd(obj.get(key)) if isinstance(obj, dict) else None
        if d:
            return d
    if isinstance(obj, dict):
        for key in ("trade_date", "date", "updated_at", "close_updated_at", "intraday_updated_at"):
            d = ymd(obj.get(key))
            if d:
                return d
        rows = obj.get("rows") or []
        if isinstance(rows, list):
            for row in rows[:100]:
                if not isinstance(row, dict):
                    continue
                for key in ("trade_date", "quote_date", "date", "chip_date", "updated_at"):
                    d = ymd(row.get(key))
                    if d:
                        return d
    return None


def latest_chip_date(obj):
    ds = []
    rows = obj.get("rows") or [] if isinstance(obj, dict) else []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key in ("chip_date", "foreign_date", "date"):
                d = ymd(row.get(key))
                if d:
                    ds.append(d)
                    break
    return max(ds) if ds else object_date(obj)


def main():
    status = load("status.json")
    market = load("market.json")
    close = load("close.json")
    intra = load("intraday.json")
    hourly = load("hourly.json")
    daytrade = load("daytrade.json")
    chips = load("chip_history.json")

    dates = {
        "market": object_date(market, ("trade_date",)),
        "close": object_date(close, ("trade_date",)),
        "intraday": object_date(intra, ("trade_date",)),
        "hourly": object_date(hourly, ("trade_date", "updated_at")),
        "daytrade": object_date(daytrade, ("trade_date", "updated_at")),
        "chips": latest_chip_date(chips),
    }
    valid = sorted(d for d in dates.values() if d)
    newest = valid[-1] if valid else None
    completed_candidates = [d for d in (dates.get("market"), dates.get("close")) if d]
    latest_completed = max(completed_candidates) if completed_candidates else newest
    lagging = [k for k, d in dates.items() if d and newest and d < newest]

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
            "daytrade": "獨立當沖資料；若來源日期落後，停用舊當沖訊號，不改盤中波段分數",
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
