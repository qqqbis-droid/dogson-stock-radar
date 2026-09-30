#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the close radar from the latest *completed* Taiwan cash session.

The close mission is intentionally different from intraday/daytrade: while the
cash market is still open, Yahoo daily bars may already expose today's partial
bar.  A close build must never treat that partial bar as a completed session.

This wrapper therefore enforces the same completed-session cutoff on both MIS
and every Yahoo daily frame before ``build_data.build_close()`` sees them.  MIS
is still preferred when it is current; stale MIS may be ignored, but the daily
fallback is capped to the latest completed session as well.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

import build_data as bd


_ORIGINAL_MIS = bd.official_mis_snapshot
_ORIGINAL_DOWNLOAD_DAILY = bd.download_daily


def _frame_latest_date(frame) -> date | None:
    if frame is None or len(frame) == 0:
        return None
    try:
        idx = pd.to_datetime(frame.index, errors="coerce")
        idx = idx[~pd.isna(idx)]
        if len(idx) == 0:
            return None
        return max(x.date() for x in idx)
    except Exception:
        return None


def completed_daily(syms, period="6mo"):
    """Return Yahoo daily data with any not-yet-completed session removed."""
    data = _ORIGINAL_DOWNLOAD_DAILY(syms, period)
    cutoff = bd._latest_completed_cutoff()
    out = {}
    for sym, frame in (data or {}).items():
        try:
            if frame is None or frame.empty:
                continue
            idx = pd.to_datetime(frame.index, errors="coerce")
            keep = [not pd.isna(ts) and ts.date() <= cutoff for ts in idx]
            trimmed = frame.loc[keep].copy()
            if not trimmed.empty:
                out[sym] = trimmed
        except Exception as exc:
            print("completed daily filter", sym, exc)
    return out


def _latest_reference_date() -> date | None:
    dates: list[date] = []
    cutoff = bd._latest_completed_cutoff()

    # TPEx history already applies the completed-session cutoff internally.
    try:
        d = _frame_latest_date(bd.tpex_index_history())
        if d and d <= cutoff:
            dates.append(d)
    except Exception as exc:
        print("freshness reference TPEx failed:", exc)

    # Independent listed-market cross-check. completed_daily removes today's
    # partial bar while the cash session is still open.
    try:
        twii = bd.download_daily(["^TWII"], "1mo").get("^TWII")
        d = _frame_latest_date(twii)
        if d and d <= cutoff:
            dates.append(d)
    except Exception as exc:
        print("freshness reference TWII failed:", exc)

    return max(dates) if dates else None


def guarded_mis_snapshot(uni):
    snap = _ORIGINAL_MIS(uni)
    if not snap:
        return snap

    cutoff = bd._latest_completed_cutoff()
    snap = {k: v for k, v in snap.items() if v.get("date") and v.get("date") <= cutoff}
    if not snap:
        return {}

    mis_dates = [v.get("date") for v in snap.values() if v.get("date")]
    mis_latest = max(mis_dates) if mis_dates else None
    reference_latest = _latest_reference_date()

    print("freshness guard: cutoff", cutoff, "MIS", mis_latest, "reference", reference_latest)
    if mis_latest and reference_latest and reference_latest > mis_latest:
        print(
            "freshness guard: ignoring stale MIS overlay so close build can use",
            reference_latest,
        )
        return {}
    return snap


def main():
    # Patch the daily source first so every downstream fallback, including
    # index_state and the all-stock close build, is bound to completed sessions.
    bd.download_daily = completed_daily
    bd.official_mis_snapshot = guarded_mis_snapshot
    bd.build_close()


if __name__ == "__main__":
    main()

# refresh-marker: 2026-09-30-completed-session-only
