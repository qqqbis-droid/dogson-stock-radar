#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.4.3 MIS snapshot bridge.

GitHub Pages 是靜態站，免費版無法取得交易所逐筆歷史 K 線；Yahoo 5m 又常慢 20~40 分鐘。
這支程式在原本 Yahoo 5m 結構之後，持久化每輪 TWSE MIS 官方快照，將 Yahoo 最後一根之後
的官方成交價/累積量組成「快照橋接 5 分 K」，再重算 VWAP、量速、突破、技術分、族群與大盤。

注意：橋接 K 線不是逐筆 OHLC；High/Low 僅由每 5 分鐘快照與前一價格估計。
因此輸出會明確標示 structure_source / structure_confidence，不冒充完整逐筆 K 線。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import build_data as bd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data"
SNAP_FILE = OUT / "mis_snapshots.json"


def _load_snapshots():
    if not SNAP_FILE.exists():
        return {"date": None, "stocks": {}}
    try:
        obj = json.loads(SNAP_FILE.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {"date": None, "stocks": {}}
    except Exception:
        return {"date": None, "stocks": {}}


def _save_snapshots(obj):
    SNAP_FILE.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _naive_tw_index(x):
    y = x.copy()
    idx = pd.to_datetime(y.index)
    try:
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_convert("Asia/Taipei").tz_localize(None)
    except Exception:
        pass
    y.index = idx
    return y.sort_index()


def _snapshot_ts(s):
    try:
        tm = str(s.get("time") or "").strip()
        if len(tm) == 5:
            tm += ":00"
        return pd.Timestamp(f"{s['date']} {tm}")
    except Exception:
        return None


def _merge_snapshot(store, code, q):
    td = str(q.get("date") or "")
    tm = str(q.get("time") or "")
    px = q.get("close")
    if not td or not tm or px is None:
        return
    arr = store.setdefault("stocks", {}).setdefault(str(code), [])
    item = {
        "date": td,
        "time": tm,
        "price": round(float(px), 4),
        "volume_lots": q.get("volume_lots"),
        "prev_close": q.get("prev_close"),
    }
    # 同一秒/分鐘重跑時覆蓋，避免重複。
    key = (td, tm)
    arr = [x for x in arr if (str(x.get("date")), str(x.get("time"))) != key]
    arr.append(item)
    arr.sort(key=lambda x: (str(x.get("date")), str(x.get("time"))))
    store["stocks"][str(code)] = arr[-90:]  # 只需保留約一個交易日


def _snapshot_bars(x, snaps, trade_date):
    """Append 5m snapshot bars newer than Yahoo's last bar.

    Volume uses MIS cumulative lots when monotonic.  The first bridge bucket uses
    Yahoo today's accumulated volume as baseline.  If the cumulative field cannot
    be reconciled, price is still bridged but volume is set to zero so we do not
    fabricate activity.
    """
    if x is None or x.empty or not snaps:
        return x, 0, False
    x = _naive_tw_index(x)
    latest = x.index[-1]
    td = pd.Timestamp(trade_date).date()
    today_x = x[x.index.date == td]
    if today_x.empty:
        return x, 0, False

    usable = []
    for s in snaps:
        ts = _snapshot_ts(s)
        if ts is None or ts.date() != td or ts <= latest:
            continue
        try:
            px = float(s.get("price"))
        except Exception:
            continue
        if px <= 0:
            continue
        usable.append((ts, px, s.get("volume_lots")))
    if not usable:
        return x, 0, False

    # 5-minute buckets from official snapshots.
    buckets = {}
    for ts, px, lots in usable:
        b = ts.floor("5min")
        buckets.setdefault(b, []).append((ts, px, lots))

    base_volume = float(today_x["Volume"].fillna(0).sum())
    prev_cum = base_volume
    prev_px = float(today_x["Close"].iloc[-1])
    rows = []
    monotonic_volume = True

    for b in sorted(buckets):
        pts = sorted(buckets[b], key=lambda z: z[0])
        prices = [prev_px] + [p for _, p, _ in pts]
        close = float(pts[-1][1])
        cum = None
        try:
            lots = pts[-1][2]
            if lots is not None:
                cum = float(lots) * 1000.0
        except Exception:
            cum = None

        vol = 0.0
        if cum is not None and cum >= prev_cum * 0.98:
            # Small tolerance for source rounding; never allow negative bridge volume.
            vol = max(0.0, cum - prev_cum)
            prev_cum = max(prev_cum, cum)
        else:
            monotonic_volume = False

        rows.append({
            "Date": b,
            "Open": float(prev_px),
            "High": float(max(prices)),
            "Low": float(min(prices)),
            "Close": close,
            "Volume": vol,
        })
        prev_px = close

    if not rows:
        return x, 0, False
    bridge = pd.DataFrame(rows).set_index("Date")
    merged = pd.concat([x, bridge]).sort_index()
    merged = merged[~merged.index.duplicated(keep="last")]
    return merged, len(bridge), monotonic_volume


def main():
    obj = bd.load_json("intraday.json", {})
    rows = obj.get("rows") or []
    universe_list = bd.load_json("universe.json", [])
    close_obj = bd.load_json("close.json", {"rows": []})
    close_map = {str(r.get("code")): r for r in (close_obj.get("rows") or []) if r.get("code")}
    close_market = bd.load_json("market.json", close_obj.get("market", {}))
    if not rows or not universe_list:
        raise SystemExit("missing intraday/universe data")

    u = pd.DataFrame(universe_list)
    u["code"] = u["code"].astype(str)
    if "market" not in u.columns:
        raise SystemExit("universe missing market")
    u["symbol"] = u["code"] + np.where(u["market"].eq("上櫃"), ".TWO", ".TW")
    code_to_sym = dict(zip(u["code"], u["symbol"]))

    codes = [str(r.get("code")) for r in rows if r.get("code")]
    quotes = bd.intraday_stock_snapshot(u, codes)
    if not quotes:
        print("MIS bridge: no quotes; keep v1.4.1 output")
        return

    trade_date = max(str(q.get("date")) for q in quotes.values() if q.get("date"))
    store = _load_snapshots()
    if store.get("date") != trade_date:
        store = {"date": trade_date, "stocks": {}}
    for code, q in quotes.items():
        _merge_snapshot(store, code, q)
    store["updated_at"] = bd.now_tw().isoformat(timespec="seconds")
    _save_snapshots(store)

    # Re-download the same Yahoo 5m history only as a historical base, then bridge
    # the delayed tail with persisted official MIS snapshots.
    symbols = [code_to_sym[c] for c in codes if c in code_to_sym]
    raw = {}
    for i in range(0, len(symbols), 60):
        part = symbols[i:i+60]
        try:
            raw.update(bd.download_intraday(part))
        except Exception as e:
            print("MIS bridge yahoo base batch", i, e)

    by_code = {str(r.get("code")): r for r in rows}

    # Official quote and 5-minute structure are two independent layers.
    # A stock with a valid MIS quote must show the live price even when Yahoo
    # history or the snapshot-built 5m bar is temporarily unavailable.
    quoted_rows = 0
    for code, q in quotes.items():
        row = by_code.get(str(code))
        if not row:
            continue
        row["quote_date"] = q.get("date")
        row["quote_time"] = q.get("time")
        row["quote_snapshot_time"] = q.get("snapshot_time")
        row["quote_source"] = q.get("source")
        row["quote_carried"] = bool(q.get("quote_carried"))
        row["quote_close"] = q.get("close")
        if q.get("close") is not None:
            row["close"] = q.get("close")
        if q.get("change_pct") is not None:
            row["day_change"] = round(float(q.get("change_pct")), 2)
        if row.get("vwap") and row.get("close") is not None:
            try:
                row["vwap_dist"] = round((float(row["close"]) / float(row["vwap"]) - 1) * 100, 2)
            except Exception:
                pass
        quoted_rows += 1

    bridged = 0
    volume_ok = 0
    fresh_times = []
    for code, row in by_code.items():
        sym = code_to_sym.get(code)
        x = raw.get(sym)
        if x is None or x.empty:
            continue
        merged, nbar, vol_ok = _snapshot_bars(x, store.get("stocks", {}).get(code, []), trade_date)
        if nbar <= 0:
            continue
        try:
            t = bd.intraday_technical(merged)
        except Exception as e:
            print("MIS bridge technical", code, e)
            continue
        if not t:
            continue

        # Preserve identity/chip fields, replace only live technical structure.
        for k, v in t.items():
            row[k] = v
        q = quotes.get(code)
        if q:
            row["quote_date"] = q.get("date")
            row["quote_time"] = q.get("time")
            row["quote_source"] = q.get("source")
            row["quote_close"] = q.get("close")
            row["close"] = q.get("close")
            if q.get("change_pct") is not None:
                row["day_change"] = round(float(q.get("change_pct")), 2)
            if row.get("vwap"):
                try:
                    row["vwap_dist"] = round((float(row["close"]) / float(row["vwap"]) - 1) * 100, 2)
                except Exception:
                    pass
        row["structure_time"] = t.get("time")
        row["structure_close"] = t.get("close")
        row["structure_source"] = "Yahoo歷史5分K + TWSE MIS官方快照橋接"
        row["structure_bridge_bars"] = nbar
        row["structure_confidence"] = "高" if nbar >= 3 and vol_ok else "中" if nbar >= 1 else "低"
        row["structure_volume_verified"] = bool(vol_ok)
        bridged += 1
        volume_ok += int(bool(vol_ok))
        if t.get("time"):
            fresh_times.append(str(t.get("time"))[:5])

    out_rows = list(by_code.values())
    out_rows = bd._attach_multitimeframe_context(out_rows, close_map, bd.load_json("hourly.json", {}))
    market_live = bd.intraday_index_snapshot()
    out_rows = bd._attach_relative_multitimeframe(out_rows, close_map, close_market, market_live)
    out_rows = bd._refresh_dynamic_thresholds(out_rows, close_map)
    rotation = bd.build_sector_rotation(out_rows)
    intraday_market = bd.build_intraday_market(out_rows, market_live, rotation, close_market)
    out_rows = bd.add_component_scores(out_rows, intraday_market, preliminary_intraday=True)

    # v1.5.21：最後以「完成MIS橋接後」的最新狀態和上一輪正式頁面比較。
    previous_obj = {}
    try:
        prev_path = bd.CACHE / "intraday_previous.json"
        if prev_path.exists():
            previous_obj = json.loads(prev_path.read_text(encoding="utf-8"))
    except Exception:
        previous_obj = {}
    change_radar = bd.build_change_radar(out_rows, rotation, previous_obj)

    quote_times = [str(q.get("time") or "")[:5] for q in quotes.values() if q.get("time")]
    quote_latest = max(quote_times) if quote_times else None
    structure_latest = max(fresh_times) if fresh_times else obj.get("quote_layer", {}).get("structure_latest_time")

    obj.update({
        "updated_at": bd.now_tw().isoformat(timespec="seconds"),
        "market": intraday_market,
        "market_intraday": market_live,
        "sector_rotation": rotation,
        "change_radar": change_radar,
        "multi_timeframe_version": "1.1",
        "relative_multiframe_version": "1.0",
        "dynamic_threshold_version": "1.0",
        "rows": out_rows,
        "bridge": {
            "version": "1.4.3",
            "source": "TWSE MIS snapshot bridge",
            "trade_date": trade_date,
            "bridged_rows": bridged,
            "volume_verified_rows": volume_ok,
            "latest_quote_time": quote_latest,
            "latest_structure_time": structure_latest,
            "note": "Yahoo只作歷史底座；最後數根5分結構由每輪官方MIS快照橋接。橋接High/Low為快照估計，不冒充逐筆K線。",
        },
        "quote_layer": {
            "source": "TWSE MIS",
            "coverage": len(quotes),
            "row_count": len(out_rows),
            "latest_time": quote_latest,
            "structure_latest_time": structure_latest,
            "note": "現價/當日漲跌採官方MIS；技術尾端採持久化MIS快照橋接，Yahoo僅作較早5分K底座",
        },
    })
    bd.dump("intraday.json", obj)

    status = bd.load_json("status.json", {})
    status.update({
        "updated_at": bd.now_tw().isoformat(timespec="seconds"),
        "intraday_updated_at": bd.now_tw().isoformat(timespec="seconds"),
        "intraday_count": len(out_rows),
        "mis_bridge_count": bridged,
        "mis_bridge_structure_time": structure_latest,
        "change_radar_version": "1.0",
        "multi_timeframe_version": "1.1",
        "relative_multiframe_version": "1.0",
        "dynamic_threshold_version": "1.0",
        "version": "1.5.30-free",
    })
    bd.dump("status.json", status)
    print("MIS bridge done", "quotes", quoted_rows, "structure_rows", bridged, "volume_ok", volume_ok, "quote", quote_latest, "structure", structure_latest)


if __name__ == "__main__":
    main()
