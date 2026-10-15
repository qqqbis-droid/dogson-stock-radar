#!/usr/bin/env python3
"""Regression: genuinely same-day 5m candles must survive a zero-MIS-tail build."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import unittest

import pandas as pd

import bridge_intraday as deep

TW = ZoneInfo("Asia/Taipei")


class TestFreshFiveMinuteHistory(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, 10, 38, tzinfo=TW)
        self.idx = pd.date_range("2026-10-15 09:00", periods=20, freq="5min")
        self.bars = pd.DataFrame({
            "Open": [25.0] * 20,
            "High": [25.3] * 20,
            "Low": [24.9] * 20,
            "Close": [25.1] * 20,
            "Volume": [10000] * 20,
        }, index=self.idx)

    def test_no_tail_still_accepts_current_real_yahoo_candles(self):
        result = deep._fresh_yahoo_5m(self.bars, "2026-10-15", self.now)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 20)

    def test_previous_session_never_promoted(self):
        old = self.bars.copy()
        old.index = old.index - pd.Timedelta(days=1)
        self.assertIsNone(deep._fresh_yahoo_5m(old, "2026-10-15", self.now))

    def test_old_candles_not_live(self):
        old = self.bars.iloc[:10]
        self.assertIsNone(deep._fresh_yahoo_5m(old, "2026-10-15", self.now))

    def test_future_candles_not_live(self):
        future = self.bars.copy()
        future.index = future.index + pd.Timedelta(minutes=60)
        self.assertIsNone(deep._fresh_yahoo_5m(future, "2026-10-15", self.now))

    def test_insufficient_bars_not_live(self):
        self.assertIsNone(deep._fresh_yahoo_5m(self.bars.iloc[:3], "2026-10-15", self.now))


if __name__ == "__main__":
    unittest.main()
