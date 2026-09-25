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
    lagging = [k for k, d in dates.items() if d and newest and d < newest]

    out = {
        "app_version": APP_VERSION,
        "data_engine_version": status.get("version"),
        "generated_at": datetime.now(TW).isoformat(timespec="seconds"),
        "newest_trade_date": newest,
        "dates": dates,
        "lagging_sources": lagging,
        "rules": {
            "intraday": "近即時5分雷達；最新成交價可由TWSE MIS補充",
            "close": "最近完成交易日盤後波段資料",
            "hourly": "60分K波段骨架",
            "daytrade": "獨立當沖資料，不改盤中波段分數",
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
