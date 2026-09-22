#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the close-time 60-minute lifecycle radar.

This module is intentionally separate from the existing 100-point stock radar:
- lifecycle = filter/classification
- score60 = 60K structure quality
- combined_score = review ordering only (60K/daily/chips/sector)
- entry light = position/extension warning, not a buy/sell signal

Output: docs/data/hourly.json
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data"
OUT.mkdir(parents=True, exist_ok=True)
TW = timezone(timedelta(hours=8))


def now_tw():
    return datetime.now(TW)


def load(name, default):
    p = OUT / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def dump(obj):
    (OUT / "hourly.json").write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def frame(raw, sym, batch):
    if raw is None or raw.empty:
        return None
    try:
        if isinstance(raw.columns, pd.MultiIndex):
            l0 = set(map(str, raw.columns.get_level_values(0)))
            l1 = set(map(str, raw.columns.get_level_values(1)))
            if sym in l0:
                d = raw[sym].copy()
            elif sym in l1:
                d = raw.xs(sym, axis=1, level=1).copy()
            else:
                return None
        elif len(batch) == 1:
            d = raw.copy()
        else:
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = [str(c[0]) for c in d.columns]
        if "Close" not in d.columns or "Volume" not in d.columns:
            return None
        d = d[["Close", "Volume"]].copy()
        d["Close"] = pd.to_numeric(d["Close"], errors="coerce")
        d["Volume"] = pd.to_numeric(d["Volume"], errors="coerce").fillna(0)
        d = d.dropna(subset=["Close"])
        d = d[d["Close"] > 0]
        # Need 240T plus five completed bars for direction checks.
        return d if len(d) >= 246 else None
    except Exception:
        return None


def direction(s):
    one = (s.iloc[-1] / s.iloc[-2] - 1) * 100
    three = (s.iloc[-1] / s.iloc[-3] - 1) * 100
    five = (s.iloc[-1] / s.iloc[-6] - 1) * 100
    # Latest direction matters; five-bar slope is kept separately for speed comparison.
    if one > 0 and three > 0.03:
        label = "UP"
    elif one >= -0.02 and three >= -0.05:
        label = "FLAT"
    else:
        label = "DOWN"
    return label, float(one), float(three), float(five)


def daily_position_score(r):
    """20 points: daily MA20 position, RSI, 5d extension and momentum context."""
    dist = float(r.get("dist20") or 0)
    rr = float(r.get("rsi") or 50)
    ret5 = float(r.get("ret5") or 0)
    s = 0
    if 0 <= dist <= 8:
        s += 8
    elif -5 <= dist < 0:
        s += 6
    elif 8 < dist <= 12:
        s += 5
    elif -8 <= dist < -5:
        s += 4
    else:
        s += 1
    if 50 <= rr <= 68:
        s += 5
    elif 45 <= rr < 50 or 68 < rr <= 72:
        s += 4
    elif 40 <= rr < 45 or 72 < rr <= 78:
        s += 2
    else:
        s += 1
    if -3 <= ret5 <= 10:
        s += 4
    elif 10 < ret5 <= 15 or -6 <= ret5 < -3:
        s += 2
    momentum = bool(r.get("trend")) or bool(r.get("break3")) or (
        (r.get("macd_h") or 0) > 0 and (r.get("macd_acc") or 0) > 0
    )
    s += 3 if momentum else 1
    return min(20, int(s))


def entry_light(p20, daily_dist20, daily_rsi, daily_ret5, above240, overhead240):
    """Independent entry-position/extension light.

    The light never changes lifecycle classification. It only communicates how far
    price has stretched away from the 60K 20T and whether daily-K is overheated.
    """
    if p20 > 8 or p20 < -3:
        level = 3
    elif p20 > 5:
        level = 2
    elif p20 > 2 or p20 < -1.5:
        level = 1
    else:
        level = 0

    warnings = []
    if p20 > 8:
        warnings.append("距60K20T>8%")
    elif p20 > 5:
        warnings.append("距60K20T 5~8%")
    elif p20 > 2:
        warnings.append("距60K20T 2~5%")
    elif p20 < -3:
        warnings.append("跌破60K20T超過3%")
    elif p20 < -1.5:
        warnings.append("60K20T下方1.5~3%")
    else:
        warnings.append("貼近60K20T")

    if daily_dist20 > 12 or daily_ret5 > 15 or daily_rsi > 78:
        level = max(level, 3)
        warnings.append("日K明顯過熱")
    elif daily_dist20 > 8 or daily_ret5 > 10 or daily_rsi > 72:
        level = max(level, 2)
        warnings.append("日K偏延伸")

    if (not above240) and overhead240 <= 5:
        level = max(level, 2)
        warnings.append("240T上方近壓")

    labels = [
        ("GREEN", "🟢", "位置舒服"),
        ("YELLOW", "🟡", "等回踩/確認"),
        ("ORANGE", "🟠", "偏延伸不追"),
        ("RED", "🔴", "過熱或結構風險"),
    ]
    key, emoji, text = labels[level]
    return key, emoji, text, "；".join(warnings)


def build():
    close_obj = load("close.json", {})
    universe = load("universe.json", [])
    close_rows = {
        str(r.get("code")): r
        for r in close_obj.get("rows", [])
        if isinstance(r, dict) and r.get("code")
    }
    if not close_rows or not universe:
        print("hourly skipped: close/universe data missing")
        return

    meta = {}
    for x in universe:
        code = str(x.get("code", "")).strip()
        market = str(x.get("market") or "").strip()
        if not (code.isdigit() and len(code) == 4) or code not in close_rows:
            continue
        sym = code + (".TWO" if market == "上櫃" else ".TW")
        meta[sym] = {
            "code": code,
            "name": str(x.get("name") or code),
            "market": market,
            "industry_name": str(x.get("industry_name") or close_rows[code].get("industry_name") or ""),
            "sector_group": str(x.get("sector_group") or close_rows[code].get("sector_group") or ""),
        }

    syms = list(meta)
    rows = []
    failed = []
    batch_size = 50

    for st in range(0, len(syms), batch_size):
        batch = syms[st:st + batch_size]
        try:
            raw = yf.download(
                batch, period="3mo", interval="60m", group_by="ticker",
                auto_adjust=False, threads=True, progress=False, prepost=False,
            )
        except Exception as e:
            print("60m batch failed", st, e)
            failed += batch
            continue

        for sym in batch:
            d = frame(raw, sym, batch)
            if d is None:
                failed.append(sym)
                continue
            c = d["Close"]
            v = d["Volume"]
            ma20 = c.rolling(20).mean()
            ma60 = c.rolling(60).mean()
            ma240 = c.rolling(240).mean()
            if any(pd.isna(s.iloc[-6]) or pd.isna(s.iloc[-1]) for s in (ma20, ma60, ma240)):
                continue

            d20, _, _, s20 = direction(ma20)
            d60, _, _, s60 = direction(ma60)
            d240, _, _, s240 = direction(ma240)
            price = float(c.iloc[-1])
            m20 = float(ma20.iloc[-1])
            m60 = float(ma60.iloc[-1])
            m240 = float(ma240.iloc[-1])
            gap = (m20 / m60 - 1) * 100
            p20 = (price / m20 - 1) * 100
            above240 = price >= m240
            overhead = ((m240 / price) - 1) * 100 if not above240 else 0.0
            orderly = price > m20 > m60 > m240
            slope_diff = abs(s20 - s60)

            idx = pd.to_datetime(d.index)
            dates = pd.Series([z.date() for z in idx], index=d.index)
            day_vol = v.groupby(dates).sum()
            day_turn = (c * v).groupby(dates).sum()
            avg_vol_lots = float(day_vol.tail(10).mean()) / 1000 if len(day_vol) else 0
            avg_turn_mn = float(day_turn.tail(10).mean()) / 1e6 if len(day_turn) else 0
            if not (avg_turn_mn >= 50 and avg_vol_lots >= 300):
                continue
            lastv = float(day_vol.iloc[-1]) if len(day_vol) else 0
            prev9 = float(day_vol.iloc[-10:-1].mean()) if len(day_vol) >= 10 else 0
            volratio = lastv / prev9 if prev9 > 0 else None

            cross_age = None
            for age in range(0, min(120, len(d) - 60)):
                i = len(d) - 1 - age
                if i <= 0:
                    break
                if ma20.iloc[i - 1] <= ma60.iloc[i - 1] and ma20.iloc[i] > ma60.iloc[i]:
                    cross_age = age
                    break

            # Nearby falling 240T overhead is a hard structural warning.
            if (not above240) and overhead <= 3 and d240 != "UP":
                continue

            category = None
            if m20 <= m60 and -0.8 <= gap <= 0 and d20 == "UP" and d60 in ("UP", "FLAT"):
                category = "PRE_CROSS"
            elif m20 > m60 and cross_age is not None and cross_age <= 3 and d20 == "UP" and d60 in ("UP", "FLAT"):
                category = "EARLY"
            elif m20 > m60 and d20 == "UP" and d60 == "UP":
                category = "ACCEL_CONT" if (s20 >= s60 and slope_diff > 0.60) else "STABLE_CONT"
            else:
                continue

            score = 0
            score += 12 if d20 == "UP" else 0
            score += 10 if d60 == "UP" else (5 if d60 == "FLAT" else 0)
            score += 3 if m20 > m60 else 1
            score += 8 if category == "PRE_CROSS" else (12 if category == "EARLY" else 15)
            score += 10 if above240 else (4 if overhead > 5 else 2)
            score += 8 if d240 == "UP" else (5 if d240 == "FLAT" else 2)
            score += 2 if orderly else 0
            score += 10 if slope_diff <= 0.30 else (8 if slope_diff <= 0.60 else (6 if slope_diff <= 1.20 else (3 if slope_diff <= 2 else 1)))
            ap = abs(p20)
            score += 15 if ap <= 3 else (12 if ap <= 5 else (7 if ap <= 8 else (3 if ap <= 12 else 1)))
            if category == "PRE_CROSS":
                ag = abs(gap)
                score += 10 if ag <= 0.30 else (8 if ag <= 0.80 else 3)
            else:
                score += 10 if 0 <= gap <= 3 else (6 if 3 < gap <= 6 else 2)
            score += 2 if volratio is None else (5 if 0.8 <= volratio <= 2.5 else (3 if 0.5 <= volratio < 0.8 or 2.5 < volratio <= 4 else 1))
            score = min(100, int(score))

            m = meta[sym]
            cr = close_rows[m["code"]]
            daily_dist = float(cr.get("dist20") or 0)
            daily_rsi = float(cr.get("rsi") or 0)
            daily_ret5 = float(cr.get("ret5") or 0)
            light_key, light_emoji, light_label, light_reason = entry_light(
                p20, daily_dist, daily_rsi, daily_ret5, above240, overhead
            )
            dpos = daily_position_score(cr)
            chip = float(cr.get("chip_score") or 0)
            sector = float(cr.get("sector_score") or 0)
            combined = round(score * 0.50 + dpos + chip * 0.80 + sector, 1)

            rows.append({
                **m,
                "category60": category,
                "score60": score,
                "combined_score": combined,
                "entry_light": light_key,
                "entry_light_emoji": light_emoji,
                "entry_light_label": light_label,
                "entry_light_reason": light_reason,
                "price": round(price, 2),
                "ma20_60": round(m20, 3),
                "ma60_60": round(m60, 3),
                "ma240_60": round(m240, 3),
                "dir20": d20,
                "dir60": d60,
                "dir240": d240,
                "s20_5": round(s20, 3),
                "s60_5": round(s60, 3),
                "s240_5": round(s240, 3),
                "slope_diff": round(slope_diff, 3),
                "gap20_60_pct": round(gap, 3),
                "cross_age": cross_age,
                "price_vs20_60_pct": round(p20, 2),
                "above240": above240,
                "overhead240_pct": round(overhead, 2),
                "orderly": orderly,
                "vol_ratio60day": None if volratio is None else round(volratio, 2),
                "daily_position_score": dpos,
                "daily_dist20": round(daily_dist, 2),
                "daily_rsi": round(daily_rsi, 1),
                "daily_ret5": round(daily_ret5, 2),
                "daily_ret20": round(float(cr.get("ret20") or 0), 2),
                "chip_score": cr.get("chip_score"),
                "chip_coverage_pct": cr.get("chip_coverage_pct"),
                "chip_date": cr.get("chip_date"),
                "foreign_3buy": cr.get("foreign_3buy"),
                "sbl_3down": cr.get("sbl_3down"),
                "margin_status": cr.get("margin_status"),
                "sector_score": cr.get("sector_score"),
                "industry_hot_count": cr.get("industry_hot_count"),
                "existing_radar_score": cr.get("score"),
            })
        time.sleep(0.25)

    light_order = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
    lifecycle_order = {"PRE_CROSS": 0, "EARLY": 1, "STABLE_CONT": 2, "ACCEL_CONT": 3}
    rows.sort(key=lambda x: (
        light_order.get(x.get("entry_light"), 9),
        -float(x.get("combined_score") or 0),
        lifecycle_order.get(x.get("category60"), 9),
    ))

    counts = {k: sum(1 for r in rows if r["category60"] == k) for k in lifecycle_order}
    lights = {k: sum(1 for r in rows if r["entry_light"] == k) for k in light_order}
    trade_dates = [str(r.get("date")) for r in close_rows.values() if r.get("date")]

    result = {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "source_close_updated_at": close_obj.get("updated_at"),
        "trade_date": max(trade_dates) if trade_dates else None,
        "method": "60K lifecycle + independent entry-position light; review score = 60K 50% + daily position 20% + chips 20% + sector 10%",
        "entry_light_rule": "GREEN -1.5%~+2% vs 60K20T; YELLOW +2~5% or -1.5~-3%; ORANGE +5~8%; RED >8% or <-3%; daily overextension can downgrade",
        "counts": counts,
        "entry_light_counts": lights,
        "failed_60m": len(set(failed)),
        "rows": rows,
    }
    dump(result)
    print("hourly done", len(rows), counts, lights, "failed", len(set(failed)))


if __name__ == "__main__":
    build()
