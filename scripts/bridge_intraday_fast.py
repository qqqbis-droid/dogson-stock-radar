#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast intraday quote lane for GitHub Pages.

Purpose: publish current TWSE MIS quotes quickly without re-downloading the
entire Yahoo 5-minute history on every five-minute schedule tick.  Deep 5m/60m
structure is refreshed by the slower bridge/full audit; this lane updates the
quote layer, current market/sector context and decision inputs from official MIS.

Important truthfulness rule: when MIS has no fresh trade (`z == -`), only a
same-day previously observed real trade may be carried forward. Bid/ask is never
used as a fake last price. `quote_snapshot_time` records when MIS itself was
sampled, separately from the actual last-trade `quote_time`.
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

import build_data as bd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data"
SNAP_FILE = OUT / "mis_snapshots.json"


def _num(v):
    try:
        if v in (None, "", "-"):
            return None
        return float(str(v).replace(",", ""))
    except Exception:
        return None


def _first_book(v):
    s = str(v or "").strip()
    if not s or s == "-":
        return None
    for part in s.split("_"):
        n = _num(part)
        if n is not None and n > 0:
            return n
    return None


def _date(v):
    s = str(v or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s[:10] if len(s) >= 10 else ""


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_snapshots(store):
    SNAP_FILE.write_text(json.dumps(store, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _merge_snapshot(store, code, q):
    if q.get("quote_carried") or q.get("close") is None or not q.get("date") or not q.get("time"):
        return
    arr = store.setdefault("stocks", {}).setdefault(str(code), [])
    item = {
        "date": q["date"],
        "time": q["time"],
        "price": round(float(q["close"]), 4),
        "volume_lots": q.get("volume_lots"),
        "prev_close": q.get("prev_close"),
    }
    key = (item["date"], item["time"])
    arr = [x for x in arr if (str(x.get("date")), str(x.get("time"))) != key]
    arr.append(item)
    arr.sort(key=lambda x: (str(x.get("date")), str(x.get("time"))))
    store["stocks"][str(code)] = arr[-90:]


def _fetch_batch(part, stamp):
    ex_ch = "|".join(f"{'otc' if x['market'] == '上櫃' else 'tse'}_{x['code']}.tw" for x in part)
    rr = requests.get(
        "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
        params={"ex_ch": ex_ch, "json": "1", "delay": "0", "_": int(stamp.timestamp() * 1000)},
        headers={
            "User-Agent": "Mozilla/5.0 DogsonRadar/1.5-fast",
            "Referer": "https://mis.twse.com.tw/stock/index.jsp",
        },
        timeout=12,
    )
    rr.raise_for_status()
    data = rr.json()
    return data.get("msgArray") or []


def _fast_quotes(universe, rows):
    now = bd.now_tw()
    today = now.strftime("%Y-%m-%d")
    by_code = {str(r.get("code")): r for r in rows if r.get("code")}
    recs = []
    for x in universe:
        code = str(x.get("code") or "").strip()
        if code in by_code:
            recs.append({"code": code, "market": str(x.get("market") or "")})

    # One official snapshot is enough for the fast lane because the previous
    # published same-day real trade is explicitly allowed as continuity.
    # Seven-ish batches are fetched concurrently instead of 30 sequential MIS
    # requests (old path: 10 batches x 3 rounds).
    batch_size = 120
    batches = [recs[i:i + batch_size] for i in range(0, len(recs), batch_size)]
    messages = []
    errors = []
    with ThreadPoolExecutor(max_workers=min(5, max(1, len(batches)))) as pool:
        futs = [pool.submit(_fetch_batch, b, now) for b in batches]
        for fut in as_completed(futs):
            try:
                messages.extend(fut.result())
            except Exception as exc:
                errors.append(str(exc))

    meta = {}
    for m in messages:
        code = str(m.get("c") or "").strip()
        if not code:
            continue
        qd = _date(m.get("d"))
        meta[code] = (m, qd)

    quotes = {}
    fresh = carried = missing = 0
    snapshot_time = now.strftime("%H:%M:%S")
    for rec in recs:
        code = rec["code"]
        old = by_code.get(code) or {}
        m, qd = meta.get(code, ({}, ""))
        if not qd:
            qd = str(old.get("quote_date") or "")[:10]

        last = _num(m.get("z"))
        tm = str(m.get("t") or "").strip()
        is_fresh = bool(qd == today and last is not None and last > 0 and tm)
        is_carried = False
        if not is_fresh:
            old_date = str(old.get("quote_date") or "")[:10]
            old_px = _num(old.get("quote_close") if old.get("quote_close") is not None else old.get("close"))
            old_tm = str(old.get("quote_time") or "").strip()
            if old_date == today and old_px is not None and old_px > 0 and old_tm:
                qd, last, tm, is_carried = today, old_px, old_tm, True

        if last is None or not qd:
            missing += 1
            continue

        prev = _num(m.get("y"))
        vol_lots = _num(m.get("v"))
        if is_fresh:
            fresh += 1
        elif is_carried:
            carried += 1
        quotes[code] = {
            "date": qd,
            "time": tm or str(old.get("quote_time") or ""),
            "snapshot_time": snapshot_time if qd == today else str(old.get("quote_snapshot_time") or ""),
            "close": last,
            "prev_close": prev if prev is not None else _num(old.get("prev_close")),
            "change_pct": ((last / prev - 1) * 100) if prev not in (None, 0) else _num(old.get("day_change")),
            "volume_lots": vol_lots if vol_lots is not None else _num(old.get("quote_volume_lots")),
            "bid1": _first_book(m.get("b")),
            "ask1": _first_book(m.get("a")),
            "source": "TWSE MIS fast snapshot",
            "quote_carried": bool(is_carried),
            "quote_has_trade": bool(is_fresh),
        }

    print("FAST_MIS", json.dumps({
        "requested": len(recs), "messages": len(messages), "fresh": fresh,
        "carried": carried, "missing": missing, "batches": len(batches),
        "errors": errors[:3], "snapshot_time": snapshot_time,
    }, ensure_ascii=False))
    if len(quotes) < max(50, int(len(recs) * 0.70)):
        raise SystemExit(f"fast MIS coverage too low: {len(quotes)}/{len(recs)}")
    return quotes


def main():
    obj = bd.load_json("intraday.json", {})
    rows = obj.get("rows") or []
    universe = bd.load_json("universe.json", [])
    if not rows or not universe:
        raise SystemExit("missing intraday/universe data")

    quotes = _fast_quotes(universe, rows)
    trade_dates = [str(q.get("date") or "")[:10] for q in quotes.values() if q.get("date")]
    if not trade_dates:
        raise SystemExit("fast MIS returned no dated quote")
    trade_date = max(trade_dates)

    store = _load(SNAP_FILE, {"date": None, "stocks": {}})
    if store.get("date") != trade_date:
        store = {"date": trade_date, "stocks": {}}

    by_code = {str(r.get("code")): r for r in rows if r.get("code")}
    for code, q in quotes.items():
        row = by_code.get(code)
        if not row:
            continue
        for key, value in (
            ("quote_date", q.get("date")), ("quote_time", q.get("time")),
            ("quote_snapshot_time", q.get("snapshot_time")), ("quote_source", q.get("source")),
            ("quote_carried", bool(q.get("quote_carried"))), ("quote_has_trade", bool(q.get("quote_has_trade"))),
            ("quote_bid1", q.get("bid1")), ("quote_ask1", q.get("ask1")),
            ("quote_volume_lots", q.get("volume_lots")), ("quote_close", q.get("close")),
        ):
            row[key] = value
        if q.get("close") is not None:
            row["close"] = q["close"]
        if q.get("change_pct") is not None:
            row["day_change"] = round(float(q["change_pct"]), 2)
        if row.get("vwap") and row.get("close") is not None:
            try:
                row["vwap_dist"] = round((float(row["close"]) / float(row["vwap"]) - 1) * 100, 2)
            except Exception:
                pass
        _merge_snapshot(store, code, q)

    store["updated_at"] = bd.now_tw().isoformat(timespec="seconds")
    _save_snapshots(store)

    close_obj = bd.load_json("close.json", {"rows": []})
    close_map = {str(r.get("code")): r for r in (close_obj.get("rows") or []) if r.get("code")}
    close_market = bd.load_json("market.json", close_obj.get("market", {}))
    out_rows = list(by_code.values())
    market_live = bd.intraday_index_snapshot()
    try:
        out_rows = bd._attach_relative_multitimeframe(out_rows, close_map, close_market, market_live)
        out_rows = bd._refresh_dynamic_thresholds(out_rows, close_map)
    except Exception as exc:
        print("fast context refresh warning", exc)
    rotation = bd.build_sector_rotation(out_rows)
    intraday_market = bd.build_intraday_market(out_rows, market_live, rotation, close_market)
    out_rows = bd.add_component_scores(out_rows, intraday_market, preliminary_intraday=True)

    snapshot_times = [str(q.get("snapshot_time") or "") for q in quotes.values() if q.get("snapshot_time")]
    trade_times = [str(q.get("time") or "") for q in quotes.values() if q.get("time")]
    latest_snapshot = max(snapshot_times) if snapshot_times else None
    latest_trade = max(trade_times) if trade_times else None

    obj.update({
        "updated_at": bd.now_tw().isoformat(timespec="seconds"),
        "trade_date": trade_date,
        "source_trade_date": trade_date,
        "market": intraday_market,
        "market_intraday": market_live,
        "sector_rotation": rotation,
        "rows": out_rows,
        "bridge": {
            **(obj.get("bridge") or {}),
            "version": "1.5-fast",
            "source": "TWSE MIS fast quote lane; deep structure preserved from latest verified build",
            "trade_date": trade_date,
            "latest_quote_time": latest_snapshot,
            "latest_trade_time": latest_trade,
            "quoted_rows": len(quotes),
            "fast_lane": True,
        },
        "quote_layer": {
            **(obj.get("quote_layer") or {}),
            "source": "TWSE MIS",
            "trade_date": trade_date,
            "latest_time": latest_snapshot,
            "latest_trade_time": latest_trade,
            "quoted_rows": len(quotes),
            "total_rows": len(out_rows),
            "fast_lane": True,
        },
    })
    bd.save_json("intraday.json", obj)
    print("FAST_INTRADAY_DONE", trade_date, latest_snapshot, "quotes", len(quotes), "rows", len(out_rows))


if __name__ == "__main__":
    main()
