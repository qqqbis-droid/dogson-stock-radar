#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the close radar without letting a stale MIS snapshot pin the whole build.

TWSE MIS occasionally keeps an older session around on a holiday/night refresh even
though the official index histories (and daily bars) already contain a newer completed
trading day.  build_data.build_close() intentionally locks every row to one date, so a
stale-but-nonempty MIS snapshot can otherwise force the whole radar back one session.

This wrapper keeps MIS as the preferred overlay when it is current.  When MIS is older
than the newest completed date visible from the official TPEx index history or Yahoo's
TWII daily history, it suppresses that stale overlay for this build.  build_close() then
selects the newest date present in the daily stock bars and its normal one-date lock,
market validation and completeness checks remain in force.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

import build_data as bd


_ORIGINAL_MIS = bd.official_mis_snapshot


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


def _latest_reference_date() -> date | None:
    dates: list[date] = []

    # TPEx history is an official post-close source and is especially useful on
    # holidays when MIS may keep the previous-previous session in memory.
    try:
        d = _frame_latest_date(bd.tpex_index_history())
        if d:
            dates.append(d)
    except Exception as exc:
        print("freshness reference TPEx failed:", exc)

    # Independent cross-check for the listed market.  Failure is non-fatal.
    try:
        twii = bd.download_daily(["^TWII"], "1mo").get("^TWII")
        d = _frame_latest_date(twii)
        if d:
            dates.append(d)
    except Exception as exc:
        print("freshness reference TWII failed:", exc)

    return max(dates) if dates else None


def guarded_mis_snapshot(uni):
    snap = _ORIGINAL_MIS(uni)
    if not snap:
        return snap

    mis_dates = [v.get("date") for v in snap.values() if v.get("date")]
    mis_latest = max(mis_dates) if mis_dates else None
    reference_latest = _latest_reference_date()

    print("freshness guard: MIS", mis_latest, "reference", reference_latest)
    if mis_latest and reference_latest and reference_latest > mis_latest:
        print(
            "freshness guard: ignoring stale MIS overlay so close build can use",
            reference_latest,
        )
        return {}
    return snap


def main():
    bd.official_mis_snapshot = guarded_mis_snapshot
    bd.build_close()


if __name__ == "__main__":
    main()
