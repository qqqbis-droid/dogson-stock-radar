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


def merge_completed_close(result: dict, path: Path | None) -> dict:
    """Use today's already-validated close-build daily bars when OpenAPI lags.

    These are labelled as completed daily-K evidence, NOT official exchange
    close quotations, and never overwrite a same-session official quote.
    """
    if path is None or not path.is_file():
        return result
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
        day = session(source.get("trade_date"))
        rows = source.get("rows") or []
        if not day or not isinstance(rows, list):
            return result
        count = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = str(row.get("code") or "")
            if not re.fullmatch(r"[0-9]{4,6}", code):
                continue
            if session(row.get("date")) != day:
                continue
            px = n(row.get("close"))
            if px is None:
                continue
            old = result["quotes"].get(code)
            if old and str(old.get("trade_date") or "") >= day:
                continue
            market = str(row.get("market") or "")
            if market == "上市":
                market = "TWSE"
            elif market == "上櫃":
                market = "TPEX"
            result["quotes"][code] = {
                "code": code,
                "name": str(row.get("name") or ""),
                "close": px,
                "trade_date": day,
                "market": market,
                "source": "Radar completed-session daily K (non-official)"
            }
            count += 1
        result["completed_daily_fallback"] = {"trade_date": day, "covered": count}
        print("portfolio completed-session fallback", result["completed_daily_fallback"])
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print("portfolio completed close ignored:", str(exc)[:180])
    return result


def merge_same_session(result: dict, prior_path: Path | None) -> dict:
    """Preserve verified, same-session symbols missing from a partial fetch.

    Never copy an older trade date to today's holdings or prefer old quotes over
    new, successfully retrieved official records.
    """
    if prior_path is None or not prior_path.is_file():
        return result
    try:
        previous = json.loads(prior_path.read_text(encoding="utf-8"))
        old_quotes = previous.get("quotes") or {}
        old_ok = previous.get("source_status") or {}
        if not isinstance(old_quotes, dict):
            return result
        # Only reuse prior snapshots from this very same official builder.
        # Each quote must retain its market, date, and official provenance.
        accepted = {}
        for code, q in old_quotes.items():
            if not isinstance(q, dict):
                continue
            if not re.fullmatch(r"[0-9A-Z]{4,6}", str(code)):
                continue
            market = str(q.get("market") or "")
            provenance = str(q.get("source") or "")
            if market not in ("TWSE", "TPEX"):
                continue
            if provenance not in ("TWSE STOCK_DAY_ALL", "TPEx daily_close_quotes"):
                continue
            day = session(q.get("trade_date"))
            if day is None or n(q.get("close")) is None:
                continue
            if old_ok.get(market, {}).get("ok") is False:
                continue
            accepted[str(code)] = q

        current = result.get("quotes") or {}
        dates = [str(q.get("trade_date") or "") for q in current.values()]
        dates += [str(q.get("trade_date") or "") for q in accepted.values()]
        target = max(dates) if dates else ""
        if not target:
            return result
        merged = {code: q for code, q in accepted.items()
                  if str(q.get("trade_date") or "") == target}
        for code, q in current.items():
            if str(q.get("trade_date") or "") != target:
                continue
            # A previously verified same-day exchange close beats a newly
            # retrieved daily-bar fallback, but today's exchange close wins.
            if code in merged and q.get("source") == "Radar completed-session daily K (non-official)":
                continue
            merged[code] = q
        added = len(set(merged).difference(current))
        result["quotes"] = merged
        result["preserved_same_session"] = {
            "trade_date": target,
            "from_published": added,
            "newly_fetched": len(current),
            "final_count": len(merged),
        }
        if added:
            print("portfolio same-session preservation", result["preserved_same_session"])
    except (ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
        print("portfolio prior snapshot ignored:", str(exc)[:180])
    return result



def attach_reference_quotes(result: dict, dated_official: dict) -> dict:
    """Carry prior exchange closes for dated display only, never valuation."""
    accepted_days = sorted({str(q.get("trade_date") or "") for q in (result.get("quotes") or {}).values()})
    current_day = accepted_days[-1] if accepted_days else ""
    refs = {}
    for code, q in dated_official.items():
        day = str(q.get("trade_date") or "")
        if (code not in result.get("quotes", {}) and current_day and day < current_day
                and q.get("source") in ("TWSE STOCK_DAY_ALL", "TPEx daily_close_quotes")
                and n(q.get("close")) is not None):
            try:
                old_age = (datetime.fromisoformat(current_day) - datetime.fromisoformat(day)).days
            except ValueError:
                continue
            if 0 < old_age <= 10:
                refs[code] = {"code": code, "close": q["close"], "trade_date": day,
                              "source": q["source"], "market": q.get("market") or ""}
    result["reference_quotes"] = refs
    result["reference_note"] = "Dated previous-session prices only; never used in same-day holdings P/L"
    return result



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--prior", help="Previously published validated same-day quote snapshot")
    ap.add_argument("--close-json", help="Latest validated completed-session close.json")
    args = ap.parse_args()
    path = Path(args.out)
    collected = collect()
    # Keep older OFFICIAL prices in a separate reference-only namespace.
    # The regular quotes dictionary remains strictly same-session so that
    # no stale close can enter valuation or after-fee P/L.
    dated_official = dict(collected.get("quotes") or {})
    result = merge_same_session(merge_completed_close(collected, Path(args.close_json) if args.close_json else None), Path(args.prior) if args.prior else None)
    result = attach_reference_quotes(result, dated_official)
    # Never replace a previously good public snapshot with two failed requests.
    if not result["quotes"] and path.exists():
        print("portfolio quote fetch unavailable; preserving existing snapshot", result["source_status"])
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("portfolio market quotes", len(result["quotes"]), result["source_status"])


if __name__ == "__main__":
    main()
