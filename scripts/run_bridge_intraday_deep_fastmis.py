#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the full Yahoo/MIS structural bridge with the concurrent MIS fetcher.

The deep bridge still rebuilds 5m/VWAP/pace/technical structure, but it no longer
spends ~90 seconds on the legacy sequential 3-round MIS sampler.
"""
import build_data as bd
import bridge_intraday_fast as fast


def fast_snapshot(_universe_df, _codes):
    universe = bd.load_json("universe.json", [])
    intraday = bd.load_json("intraday.json", {})
    rows = intraday.get("rows") or []
    return fast._fast_quotes(universe, rows)


bd.intraday_stock_snapshot = fast_snapshot

import bridge_intraday as deep  # noqa: E402

deep.bd.intraday_stock_snapshot = fast_snapshot

if __name__ == "__main__":
    deep.main()
