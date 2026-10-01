#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast intraday quote lane for GitHub Pages.

Publish the official TWSE MIS snapshot layer every five minutes without
pretending every symbol must emit a new trade in that exact request.

TWSE MIS ``z`` is event-like: many perfectly valid snapshot rows have current
order-book / cumulative-volume metadata but ``z == '-'`` because no new trade
was emitted at the sampled instant.  Therefore publication quality is judged by
OFFICIAL SNAPSHOT coverage, while last-trade coverage is reported separately.

Truthfulness rules:
- bid/ask is never substituted for a last-trade price;
- only a newly observed real MIS trade or a same-day previously observed real
  trade may populate ``quote_close``;
- rows with a current MIS snapshot but no observed trade remain publishable as
  orderbook-only, preserving the slower verified structure price separately;
- ``quote_snapshot_time`` is the time the official snapshot was sampled, while
  ``quote_time`` is the time of the last real trade we actually observed.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

import build_data as bd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data"
SNAP_FILE = OUT / "mis_snapshots.json"


def _num(v):
    try:
        if v in (None, "", "-", "--"):
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
    s = str(v or "").strip().replace("/", "").replace("-", "")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return str(v or "")[:10]


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


def _fetch_batch(part, stamp, salt):
    ex_ch = "|".join(f"{'otc' if x['market'] == '上櫃' else 'tse'}_{x['code']}.tw" for x in part)
    rr = requests.get(
        "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
        params={"ex_ch": ex_ch, "json": "1", "delay": "0", "_": int(stamp.timestamp() * 1000) + salt},
        headers={
            "User-Agent": "Mozilla/5.0 DogsonRadar/1.6-fast",
            "Referer": "https://mis.twse.com.tw/stock/index.jsp",
            "Accept": "application/json,text/plain,*/*",
        },
        timeout=15,
    )
    rr.raise_for_status()
    return rr.json().get("msgArray") or []


def _latest_snapshot_trade(store, code, today):
    arr = ((store or {}).get("stocks") or {}).get(str(code)) or []
    usable = [x for x in arr if str(x.get("date") or "")[:10] == today and _num(x.get("price"))]
    if not usable:
        return None
    usable.sort(key=lambda x: str(x.get("time") or ""))
    x = usable[-1]
    return {"close": _num(x.get("price")), "time": str(x.get("time") or "").strip()}


def _fast_quotes(universe, rows):
    now = bd.now_tw()
    today = now.strftime("%Y-%m-%d")
    by_code = {str(r.get("code")): r for r in rows if r.get("code")}
    recs = []
    for x in universe:
        code = str(x.get("code") or "").strip()
        if code in by_code:
            recs.append({"code": code, "market": str(x.get("market") or "")})

    # Keep the lane fast but sample three short rounds.  This increases the
    # chance of observing a real ``z`` without turning event-like trade coverage
    # into the publication gate.
    batch_size = 80
    batches = [recs[i:i + batch_size] for i in range(0, len(recs), batch_size)]
    latest_meta = {}
    fresh_trade = {}
    errors = []
    rounds = 3
    for rnd in range(rounds):
        stamp = bd.now_tw()
        with ThreadPoolExecutor(max_workers=min(6, max(1, len(batches)))) as pool:
            futs = [pool.submit(_fetch_batch, b, stamp, rnd * 1000 + i) for i, b in enumerate(batches)]
            for fut in as_completed(futs):
                try:
                    arr = fut.result()
                except Exception as exc:
                    errors.append(str(exc))
                    continue
                for m in arr:
                    code = str(m.get("c") or "").strip()
                    qd = _date(m.get("d"))
                    if not code or qd != today:
                        continue
                    latest_meta[code] = m
                    last = _num(m.get("z"))
                    tm = str(m.get("t") or "").strip()
                    if last is not None and last > 0 and tm:
                        fresh_trade[code] = {"close": last, "time": tm}
        if rnd < rounds - 1:
            time.sleep(0.9)

    snapshot_store = _load(SNAP_FILE, {"date": None, "stocks": {}})
    quotes = {}
    fresh = carried = orderbook_only = 0
    sampled_at = bd.now_tw().strftime("%H:%M:%S")

    for rec in recs:
        code = rec["code"]
        old = by_code.get(code) or {}
        m = latest_meta.get(code)
        if not isinstance(m, dict):
            continue
        qd = _date(m.get("d")) or today
        if qd != today:
            continue

        trade = fresh_trade.get(code)
        is_fresh = trade is not None
        is_carried = False
        if trade is None:
            old_date = str(old.get("quote_date") or "")[:10]
            old_px = _num(old.get("quote_close"))
            old_tm = str(old.get("quote_time") or "").strip()
            if old_date == today and old_px is not None and old_px > 0 and old_tm:
                trade = {"close": old_px, "time": old_tm}
                is_carried = True
            else:
                cached = _latest_snapshot_trade(snapshot_store, code, today)
                if cached:
                    trade = cached
                    is_carried = True

        last = _num(trade.get("close")) if trade else None
        tm = str(trade.get("time") or "").strip() if trade else ""
        prev = _num(m.get("y"))
        vol_lots = _num(m.get("v"))
        if is_fresh:
            fresh += 1
        elif is_carried:
            carried += 1
        else:
            orderbook_only += 1

        quotes[code] = {
            "date": today,
            "time": tm or None,
            "snapshot_time": sampled_at,
            "exchange_time": str(m.get("t") or "").strip() or None,
            "close": last,
            "prev_close": prev if prev is not None else _num(old.get("prev_close")),
            "change_pct": ((last / prev - 1) * 100) if last is not None and prev not in (None, 0) else None,
            "volume_lots": vol_lots if vol_lots is not None else _num(old.get("quote_volume_lots")),
            "bid1": _first_book(m.get("b")),
            "ask1": _first_book(m.get("a")),
            "open": _num(m.get("o")),
            "high": _num(m.get("h")),
            "low": _num(m.get("l")),
            "source": "TWSE MIS official snapshot",
            "quote_carried": bool(is_carried),
            "quote_has_trade": bool(last is not None),
            "quote_trade_fresh": bool(is_fresh),
            "quote_snapshot_present": True,
        }

    snapshot_rows = len(quotes)
    min_snapshot = max(300, int(len(recs) * 0.70))
    print("FAST_MIS", json.dumps({
        "requested": len(recs),
        "snapshot_rows": snapshot_rows,
        "fresh_trade_rows": fresh,
        "carried_trade_rows": carried,
        "orderbook_only_rows": orderbook_only,
        "batches": len(batches),
        "rounds": rounds,
        "errors": errors[:3],
        "snapshot_time": sampled_at,
    }, ensure_ascii=False))
    if snapshot_rows < min_snapshot:
        raise SystemExit(f"fast MIS official snapshot coverage too low: {snapshot_rows}/{len(recs)}")
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
        raise SystemExit("fast MIS returned no dated official snapshot")
    trade_date = max(trade_dates)

    store = _load(SNAP_FILE, {"date": None, "stocks": {}})
    if store.get("date") != trade_date:
        store = {"date": trade_date, "stocks": {}}

    by_code = {str(r.get("code")): r for r in rows if r.get("code")}
    fresh_trade_rows = carried_trade_rows = orderbook_only_rows = 0
    for code, q in quotes.items():
        row = by_code.get(code)
        if not row:
            continue
        if q.get("quote_trade_fresh"):
            fresh_trade_rows += 1
        elif q.get("quote_carried"):
            carried_trade_rows += 1
        else:
            orderbook_only_rows += 1
        for key, value in (
            ("quote_date", q.get("date")), ("quote_time", q.get("time")),
            ("quote_snapshot_time", q.get("snapshot_time")), ("quote_exchange_time", q.get("exchange_time")),
            ("quote_source", q.get("source")), ("quote_carried", bool(q.get("quote_carried"))),
            ("quote_has_trade", bool(q.get("quote_has_trade"))), ("quote_trade_fresh", bool(q.get("quote_trade_fresh"))),
            ("quote_snapshot_present", True), ("quote_bid1", q.get("bid1")), ("quote_ask1", q.get("ask1")),
            ("quote_volume_lots", q.get("volume_lots")), ("quote_close", q.get("close")),
        ):
            row[key] = value
        # Only overwrite the decision price with a real observed last trade.
        # Orderbook-only rows keep their verified slower structure price.
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

    store["date"] = trade_date
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
    quoted_rows = len(quotes)

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
            "version": "1.6-fast",
            "source": "TWSE MIS official snapshot lane; deep structure preserved from latest verified build",
            "trade_date": trade_date,
            "latest_quote_time": latest_snapshot,
            "latest_trade_time": latest_trade,
            "quoted_rows": quoted_rows,
            "official_snapshot_rows": quoted_rows,
            "fresh_trade_rows": fresh_trade_rows,
            "carried_trade_rows": carried_trade_rows,
            "orderbook_only_rows": orderbook_only_rows,
            "fast_lane": True,
        },
        "quote_layer": {
            **(obj.get("quote_layer") or {}),
            "source": "TWSE MIS",
            "trade_date": trade_date,
            "latest_time": latest_snapshot,
            "latest_trade_time": latest_trade,
            "quoted_rows": quoted_rows,
            "official_snapshot_rows": quoted_rows,
            "fresh_trade_rows": fresh_trade_rows,
            "carried_trade_rows": carried_trade_rows,
            "orderbook_only_rows": orderbook_only_rows,
            "total_rows": len(out_rows),
            "fast_lane": True,
            "price_truth_rule": "real_or_same_day_carried_trade_only; bid_ask_never_substituted",
        },
    })
    bd.save_json("intraday.json", obj)
    print("FAST_INTRADAY_DONE", json.dumps({
        "trade_date": trade_date,
        "snapshot": latest_snapshot,
        "latest_trade": latest_trade,
        "official_snapshots": quoted_rows,
        "fresh_trades": fresh_trade_rows,
        "carried_trades": carried_trade_rows,
        "orderbook_only": orderbook_only_rows,
        "rows": len(out_rows),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
