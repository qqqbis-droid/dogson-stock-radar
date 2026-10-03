#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persist completed daily OHLCV frames for lightweight browser-side holdings analysis.

The close builder already downloads six months of daily bars for the whole market.
This helper reuses those already-fetched frames and writes compact per-code files,
so the portfolio page can load only the holdings the user actually owns.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data" / "history"
TW = timezone(timedelta(hours=8))
SYMBOL_RE = re.compile(r"^(?P<code>\d{4})\.(?P<market>TW|TWO)$")
MAX_BARS = 160


def _num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _round_price(v):
    x = _num(v)
    return None if x is None else round(x, 4)


def _volume(v):
    x = _num(v)
    return None if x is None else int(round(x))


def capture_frames(frames: dict, max_bars: int = MAX_BARS) -> int:
    """Write one compact history file per Taiwan stock symbol.

    Input frames are expected to have already been filtered to completed sessions
    by build_close_fresh.completed_daily().
    """
    if not isinstance(frames, dict) or not frames:
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    written = 0

    for symbol, frame in frames.items():
        m = SYMBOL_RE.fullmatch(str(symbol))
        if not m or frame is None or getattr(frame, "empty", True):
            continue

        code = m.group("code")
        market = "上市" if m.group("market") == "TW" else "上櫃"

        try:
            x = frame.tail(max_bars).copy()
            bars = []
            for idx, row in x.iterrows():
                ts = pd.to_datetime(idx, errors="coerce")
                if pd.isna(ts):
                    continue
                close = _round_price(row.get("Close"))
                if close is None or close <= 0:
                    continue
                open_ = _round_price(row.get("Open"))
                high = _round_price(row.get("High"))
                low = _round_price(row.get("Low"))
                vol = _volume(row.get("Volume"))
                bars.append([
                    ts.date().isoformat(),
                    open_ if open_ is not None else close,
                    high if high is not None else close,
                    low if low is not None else close,
                    close,
                    vol,
                ])

            if len(bars) < 20:
                continue

            payload = {
                "schema_version": "1.0.0",
                "code": code,
                "symbol": str(symbol),
                "market": market,
                "trade_date": bars[-1][0],
                "generated_at": datetime.now(TW).isoformat(),
                "source": "Yahoo Finance daily OHLCV; completed-session filtered by close builder",
                "field_order": ["date", "open", "high", "low", "close", "volume"],
                "bar_count": len(bars),
                "bars": bars,
            }
            (OUT / f"{code}.json").write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            written += 1
        except Exception as exc:
            print("daily history capture", symbol, exc)

    if written:
        print("daily history captured:", written)
    return written
