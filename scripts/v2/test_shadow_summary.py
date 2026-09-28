from __future__ import annotations

import unittest

from scripts.v2.shadow_summary import build_summary, choose_distinct_trading_days


class ShadowSummaryTests(unittest.TestCase):
    def test_duplicate_trade_date_counts_once_and_keeps_newest_capture(self):
        reports = [
            {
                "trade_date": "2026-09-23",
                "captured_at": "2026-09-23T16:45:00+08:00",
                "build_id": "old",
                "status": "WARN",
            },
            {
                "trade_date": "2026-09-23",
                "captured_at": "2026-09-23T17:00:00+08:00",
                "build_id": "new",
                "status": "PASS",
            },
            {
                "trade_date": "2026-09-24",
                "captured_at": "2026-09-24T16:45:00+08:00",
                "build_id": "next",
                "status": "PASS",
            },
        ]
        chosen = choose_distinct_trading_days(reports)
        self.assertEqual(2, len(chosen))
        self.assertEqual("new", chosen[0]["build_id"])
        self.assertEqual("next", chosen[1]["build_id"])

    def test_summary_tracks_coverage_safety_and_payload_without_claiming_cutover(self):
        reports = [
            {
                "trade_date": "2026-09-23",
                "captured_at": "2026-09-23T16:45:00+08:00",
                "build_id": "b1",
                "status": "PASS",
                "coverage_ratio": {"intraday": 1.0, "close": 0.99, "daytrade": 0.98},
                "safety_violations": [],
                "payload_profile": {
                    "views": {
                        "intraday": {"initial_bytes": 100000},
                        "close": {"initial_bytes": 95000},
                        "portfolio": {"initial_bytes": 65000},
                        "daytrade": {"initial_bytes": 110000},
                    }
                },
            },
            {
                "trade_date": "2026-09-24",
                "captured_at": "2026-09-24T16:45:00+08:00",
                "build_id": "b2",
                "status": "WARN",
                "coverage_ratio": {"intraday": 0.97, "close": 1.0, "daytrade": 0.99},
                "safety_violations": [],
                "payload_profile": {
                    "views": {
                        "intraday": {"initial_bytes": 101000},
                        "close": {"initial_bytes": 96000},
                        "portfolio": {"initial_bytes": 66000},
                        "daytrade": {"initial_bytes": 111000},
                    }
                },
            },
        ]
        summary = build_summary(reports)
        self.assertEqual(2, summary["distinct_trading_days"])
        self.assertEqual(0.97, summary["minimum_coverage_ratio"]["intraday"])
        self.assertEqual(101000, summary["payload"]["max_initial_bytes"]["intraday"])
        self.assertFalse(summary["promotion"]["ready_for_review"])
        self.assertFalse(summary["promotion"]["eligible_for_cutover"])
        self.assertTrue(any("18 more" in x for x in summary["promotion"]["blockers"]))


if __name__ == "__main__":
    unittest.main()
