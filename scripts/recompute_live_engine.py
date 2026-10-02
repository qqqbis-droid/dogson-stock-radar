#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recompute the live intraday engine from the official MIS quote layer.

The 5-minute structural build (Yahoo + MIS bridge) remains the slower structural
base. Every fast MIS refresh then updates the parts that can be refreshed
truthfully from the official snapshot layer:

- decision price: same-day real last trade only (never bid/ask as a fake trade)
- live VWAP: structure turnover + MIS cumulative-volume delta, using a clearly
  labelled trade/book proxy only for the *incremental turnover estimate*
- 15-minute momentum: same-day last-trade snapshot history sampled every fast run
- order-book microstructure: bid/ask midpoint and spread as validation/context
- intraday market/sector/100-point score: rebuilt after the live fields change

Support/resistance Structure 2.0 is rebuilt later in the workflow by
``enrich_sr_structure.py``; because this script updates ``close`` and ``vwap``
first, S1/S2/R1/R2 are re-ranked around the same live engine state.

No order-book value is ever written into ``close`` / ``quote_close``.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import build_data as bd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
SNAP_FILE = DATA / "mis_snapshots.json"
VERSION = "1.0"


def _num(v):
    try:
        if v in (None, "", "-", "--"):
            return None
        z = float(v)
        return z if math.isfinite(z) else None
    except Exception:
        return None


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(path: Path, obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _clock_minutes(v):
    s = str(v or "").strip()
    if not s:
        return None
    try:
        parts = s.split(":")
        hh = int(parts[0])
        mm = int(parts[1])
        ss = int(parts[2]) if len(parts) >= 3 else 0
        return hh * 60.0 + mm + ss / 60.0
    except Exception:
        return None


def _book(row):
    bid = _num(row.get("quote_bid1"))
    ask = _num(row.get("quote_ask1"))
    mid = None
    spread_pct = None
    if bid and ask and bid > 0 and ask > 0 and ask >= bid:
        mid = (bid + ask) / 2.0
        spread_pct = (ask / bid - 1.0) * 100.0
    elif bid and bid > 0:
        mid = bid
    elif ask and ask > 0:
        mid = ask
    return bid, ask, mid, spread_pct


def _trade_date(obj, rows):
    candidates = []
    for v in (
        ((obj.get("bridge") or {}).get("trade_date")),
        obj.get("source_trade_date"),
        obj.get("trade_date"),
    ):
        s = str(v or "")[:10]
        if len(s) == 10:
            candidates.append(s)
    for r in rows:
        s = str(r.get("quote_date") or r.get("structure_date") or r.get("date") or "")[:10]
        if len(s) == 10:
            candidates.append(s)
    return max(candidates) if candidates else None


def _append_engine_history(store, rows, trade_date):
    if store.get("date") != trade_date:
        store = {"date": trade_date, "stocks": {}}

    history = store.setdefault("engine_history", {})
    appended = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "")
        qd = str(row.get("quote_date") or "")[:10]
        snap = str(row.get("quote_snapshot_time") or row.get("quote_exchange_time") or row.get("quote_time") or "").strip()
        if not code or qd != trade_date or _clock_minutes(snap) is None:
            continue
        bid, ask, mid, spread = _book(row)
        trade = _num(row.get("quote_close")) if bool(row.get("quote_has_trade")) else None
        item = {
            "date": trade_date,
            "snapshot_time": snap,
            "trade_time": row.get("quote_time"),
            "last_trade": round(trade, 4) if trade is not None else None,
            "trade_fresh": bool(row.get("quote_trade_fresh")),
            "bid1": round(bid, 4) if bid is not None else None,
            "ask1": round(ask, 4) if ask is not None else None,
            "book_mid": round(mid, 4) if mid is not None else None,
            "spread_pct": round(spread, 4) if spread is not None else None,
            "volume_lots": _num(row.get("quote_volume_lots")),
        }
        arr = history.setdefault(code, [])
        arr = [
            x for x in arr
            if not (
                str(x.get("date") or "") == trade_date
                and str(x.get("snapshot_time") or "") == snap
            )
        ]
        arr.append(item)
        arr.sort(key=lambda x: (_clock_minutes(x.get("snapshot_time")) or -1))
        history[code] = arr[-120:]
        appended += 1
    store["engine_history"] = history
    store["engine_history_version"] = VERSION
    store["engine_updated_at"] = bd.now_tw().isoformat(timespec="seconds")
    return store, appended


def _refresh_ret15(row, history):
    cur = _num(row.get("quote_close")) if bool(row.get("quote_has_trade")) else None
    snap_now = _clock_minutes(
        row.get("quote_snapshot_time") or row.get("quote_exchange_time") or row.get("quote_time")
    )
    if cur is None or cur <= 0 or snap_now is None:
        row["ret15_live_source"] = "structure_fallback_no_same_day_trade"
        return False

    candidates = []
    for item in history or []:
        px = _num(item.get("last_trade"))
        tm = _clock_minutes(item.get("snapshot_time"))
        if px is None or px <= 0 or tm is None:
            continue
        age = snap_now - tm
        if 9.0 <= age <= 24.0:
            candidates.append((abs(age - 15.0), age, px, item))

    if not candidates:
        row["ret15_live_source"] = "structure_fallback_history_warming"
        return False

    _, age, past, item = min(candidates, key=lambda x: x[0])
    row["structure_ret15"] = row.get("structure_ret15", row.get("ret15"))
    row["ret15"] = round((cur / past - 1.0) * 100.0, 2)
    row["ret15_live_source"] = "MIS last-trade snapshot history"
    row["ret15_live_window_min"] = round(age, 1)
    row["ret15_reference_price"] = round(past, 4)
    row["ret15_reference_snapshot_time"] = item.get("snapshot_time")
    return True


def _capture_structure_basis(row):
    structure_time = str(row.get("structure_time") or row.get("time") or "")
    prior_basis_time = str(row.get("live_engine_basis_structure_time") or "")
    if (
        not prior_basis_time
        or prior_basis_time != structure_time
        or _num(row.get("structure_vwap")) is None
        or _num(row.get("structure_current_turnover")) is None
    ):
        vwap = _num(row.get("vwap"))
        turnover = _num(row.get("current_turnover"))
        if vwap is not None and vwap > 0:
            row["structure_vwap"] = vwap
        if turnover is not None and turnover > 0:
            row["structure_current_turnover"] = turnover
        row["structure_pace"] = row.get("pace")
        row["live_engine_basis_structure_time"] = structure_time or None


def _refresh_vwap(row):
    _capture_structure_basis(row)
    base_vwap = _num(row.get("structure_vwap"))
    base_turnover = _num(row.get("structure_current_turnover"))
    lots = _num(row.get("quote_volume_lots"))
    if base_vwap is None or base_vwap <= 0 or base_turnover is None or base_turnover <= 0 or lots is None or lots <= 0:
        row["vwap_live_source"] = "structure_fallback_missing_volume_basis"
        return False

    base_volume = base_turnover / base_vwap
    cum_volume = lots * 1000.0
    if base_volume <= 0:
        row["vwap_live_source"] = "structure_fallback_invalid_volume_basis"
        return False

    volume_ratio = cum_volume / base_volume
    # Yahoo and MIS can differ slightly (odd lots / source timing). Only bridge
    # when the two cumulative-volume bases are reconcilable.
    if volume_ratio < 0.88 or volume_ratio > 1.65:
        row["vwap_live_source"] = "structure_fallback_volume_basis_mismatch"
        row["vwap_volume_basis_ratio"] = round(volume_ratio, 3)
        return False

    delta_volume = max(0.0, cum_volume - base_volume)
    trade = _num(row.get("quote_close")) if bool(row.get("quote_has_trade")) else None
    bid, ask, mid, spread = _book(row)

    proxy = None
    method = None
    if bool(row.get("quote_trade_fresh")) and trade is not None and trade > 0:
        proxy = trade
        method = "fresh_trade"
    elif trade is not None and trade > 0 and mid is not None and mid > 0 and (spread is None or spread <= 1.5):
        proxy = (trade + mid) / 2.0
        method = "same_day_last_trade_plus_book_mid_proxy"
    elif trade is not None and trade > 0:
        proxy = trade
        method = "same_day_last_trade_proxy"
    elif mid is not None and mid > 0 and delta_volume > 0 and (spread is None or spread <= 1.0):
        # Used only for incremental-turnover estimation, never as last trade.
        proxy = mid
        method = "book_mid_incremental_turnover_proxy"

    if proxy is None:
        row["vwap_live_source"] = "structure_fallback_no_incremental_price_proxy"
        return False

    live_turnover = base_turnover + delta_volume * proxy
    live_vwap = live_turnover / cum_volume if cum_volume > 0 else base_vwap
    if not math.isfinite(live_vwap) or live_vwap <= 0:
        row["vwap_live_source"] = "structure_fallback_invalid_result"
        return False

    row["vwap"] = round(live_vwap, 4)
    row["current_turnover"] = round(live_turnover, 0)
    if _num(row.get("close")) is not None:
        row["vwap_dist"] = round((_num(row.get("close")) / live_vwap - 1.0) * 100.0, 2)
    row["vwap_live_source"] = f"structure turnover + MIS cumulative volume ({method})"
    row["vwap_volume_basis_ratio"] = round(volume_ratio, 3)
    row["vwap_incremental_volume_shares"] = round(delta_volume, 0)
    row["vwap_incremental_price_proxy"] = round(proxy, 4)
    row["vwap_is_estimate"] = bool(delta_volume > 0)
    return True


def _attach_book_context(row):
    bid, ask, mid, spread = _book(row)
    row["live_book"] = {
        "bid1": round(bid, 4) if bid is not None else None,
        "ask1": round(ask, 4) if ask is not None else None,
        "mid": round(mid, 4) if mid is not None else None,
        "spread_pct": round(spread, 4) if spread is not None else None,
        "used_as_last_trade": False,
        "role": "microstructure_validation_and_incremental_vwap_proxy_only",
    }
    trade = _num(row.get("quote_close"))
    if trade is not None and mid is not None and mid > 0:
        row["last_trade_vs_book_mid_pct"] = round((trade / mid - 1.0) * 100.0, 3)
    else:
        row["last_trade_vs_book_mid_pct"] = None


def main():
    obj = bd.load_json("intraday.json", {})
    rows = obj.get("rows") or []
    if not rows:
        raise SystemExit("live engine recompute: intraday rows missing")

    trade_date = _trade_date(obj, rows)
    if not trade_date:
        raise SystemExit("live engine recompute: trade date missing")

    store = _load(SNAP_FILE, {"date": trade_date, "stocks": {}})
    store, appended = _append_engine_history(store, rows, trade_date)
    history = store.get("engine_history") or {}

    vwap_updated = 0
    ret15_updated = 0
    book_rows = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        qd = str(row.get("quote_date") or "")[:10]
        if qd != trade_date:
            continue
        _attach_book_context(row)
        book_rows += int(bool((row.get("live_book") or {}).get("mid")))
        vwap_updated += int(_refresh_vwap(row))
        ret15_updated += int(_refresh_ret15(row, history.get(str(row.get("code") or ""), [])))
        row["live_engine_version"] = VERSION
        row["live_engine_trade_date"] = trade_date
        row["live_engine_snapshot_time"] = (
            row.get("quote_snapshot_time") or row.get("quote_exchange_time") or row.get("quote_time")
        )

    # Rebuild every downstream component that reads close/vwap/ret15/current_turnover.
    close_obj = bd.load_json("close.json", {"rows": []})
    close_map = {
        str(r.get("code")): r
        for r in (close_obj.get("rows") or [])
        if isinstance(r, dict) and r.get("code")
    }
    close_market = bd.load_json("market.json", close_obj.get("market", {}))
    hourly_obj = bd.load_json("hourly.json", {})

    rows = bd._attach_multitimeframe_context(rows, close_map, hourly_obj)
    market_live = bd.intraday_index_snapshot()
    rows = bd._attach_relative_multitimeframe(rows, close_map, close_market, market_live)
    rows = bd._refresh_dynamic_thresholds(rows, close_map)
    rotation = bd.build_sector_rotation(rows)
    intraday_market = bd.build_intraday_market(rows, market_live, rotation, close_market)
    rows = bd.add_component_scores(rows, intraday_market, preliminary_intraday=True)

    # Re-apply the existing fail-closed guard after the score is rebuilt.
    try:
        import bridge_intraday_fast as fast
        rows = fast._apply_live_truth_guard(rows, trade_date)
    except Exception as exc:
        print("live engine truth guard warning", exc)

    now = bd.now_tw().isoformat(timespec="seconds")
    obj["rows"] = rows
    obj["market"] = intraday_market
    obj["market_intraday"] = market_live
    obj["sector_rotation"] = rotation
    obj["updated_at"] = now
    obj["live_engine"] = {
        "version": VERSION,
        "trade_date": trade_date,
        "updated_at": now,
        "history_appended_rows": appended,
        "book_context_rows": book_rows,
        "vwap_recomputed_rows": vwap_updated,
        "ret15_recomputed_rows": ret15_updated,
        "score_recomputed": True,
        "support_resistance_next_step": "enrich_sr_structure.py consumes updated close/vwap and rebuilds S1/S2/R1/R2",
        "price_truth_rule": "last trade only; bid/ask never becomes close",
        "vwap_truth_rule": "estimate only when structure turnover and MIS cumulative volume reconcile",
    }
    ql = obj.setdefault("quote_layer", {})
    ql["engine_recomputed"] = True
    ql["engine_version"] = VERSION
    ql["engine_note"] = (
        "MIS latest trade feeds close/ret15; MIS cumulative volume + trade/book proxy refreshes live VWAP "
        "when reconcilable; bid/ask is microstructure context only; intraday score is rebuilt afterwards."
    )

    _save(SNAP_FILE, store)
    bd.dump("intraday.json", obj)
    print("LIVE_ENGINE_DONE", json.dumps({
        "trade_date": trade_date,
        "history": appended,
        "book_rows": book_rows,
        "vwap_rows": vwap_updated,
        "ret15_rows": ret15_updated,
        "rows": len(rows),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
