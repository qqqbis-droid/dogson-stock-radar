#!/usr/bin/env python3
"""Separate full-market closing-quote coverage for *owned* stocks.

The swing scanner can filter low-turnover symbols; portfolio quote coverage may
not. Fetch public TWSE / TPEx official latest-session snapshots without using
their data to invent technical/sector scores or support/resistance.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

TPE = timezone(timedelta(hours=8))
SOURCES = (
    ("TWSE", "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"),
    ("TPEX", "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"),
)


def n(value):
    try:
        v = float(str(value).strip().replace(",", ""))
        return v if v > 0 and v < 10000000 else None
    except (ValueError, TypeError):
        return None


def session(value):
    s = re.sub(r"[^0-9]", "", str(value or ""))
    if len(s) == 7 and s[:3].isdigit():
        year = int(s[:3]) + 1911
        s = f"{year:04d}{s[3:]}"
    if len(s) != 8:
        return None
    try:
        return datetime.strptime(s, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def field(row, *names):
    for key in names:
        if row.get(key) not in (None, ""):
            return row[key]
    return None


def extract(market, rows):
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(field(row, "Code", "SecuritiesCompanyCode", "SecuritiesCode", "代號") or "").strip()
        if not re.fullmatch(r"[0-9A-Z]{4,6}", code):
            continue
        price = n(field(row, "ClosingPrice", "Close", "Closing", "收盤"))
        date = session(field(row, "Date", "日期"))
        if price is None or not date:
            continue
        raw_vol = n(field(row, "TradeVolume", "TradingShares", "TradeVolumeShares", "成交股數"))
        out[code] = {
            "code": code,
            "name": str(field(row, "Name", "CompanyName", "SecuritiesCompanyName", "SecuritiesCompany", "股票名稱") or "").strip(),
            "close": price,
            "trade_date": date,
            "market": market,
            "volume_shares": int(raw_vol) if raw_vol is not None else None,
            "source": "TWSE STOCK_DAY_ALL" if market == "TWSE" else "TPEx daily_close_quotes",
        }
    return out


def collect():
    quotes = {}
    status = {}
    for market, url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "INUKO-LAB/2.0 (portfolio coverage)", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=24) as resp:
                raw = json.loads(resp.read().decode("utf-8-sig"))
            if not isinstance(raw, list):
                raise ValueError("official response is not a list")
            entries = extract(market, raw)
            if not entries:
                raise ValueError("no valid dated closing quotes")
            quotes.update(entries)
            status[market] = {"ok": True, "count": len(entries), "trade_dates": sorted({x["trade_date"] for x in entries.values()})[-3:]}
        except Exception as exc:
            status[market] = {"ok": False, "error": str(exc)[:180]}
    return {
        "schema_version": "1.0.0",
        "purpose": "all-market portfolio fallback; not swing ranking",
        "generated_at": datetime.now(TPE).isoformat(timespec="seconds"),
        "source_status": status,
        "quotes": quotes,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    path = Path(args.out)
    result = collect()
    # Never replace a previously good public snapshot with two failed requests.
    if not result["quotes"] and path.exists():
        print("portfolio quote fetch unavailable; preserving existing snapshot", result["source_status"])
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("portfolio market quotes", len(result["quotes"]), result["source_status"])


if __name__ == "__main__":
    main()
