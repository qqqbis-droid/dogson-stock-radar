#!/usr/bin/env python3
"""Protect real-time candidate ranking from cross-session 5m or unvalidated prices."""
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name("live_publish_patch.py")
spec = importlib.util.spec_from_file_location("live_publish_patch_under_test", MODULE)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)
TW = timezone(timedelta(hours=8))


class TruthGateTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, 10, 38, tzinfo=TW)
        self.basic = {"code": "1101", "quote_date": "2026-10-15",
                      "structure_date": "2026-10-15",
                      "structure_time": "10:30", "quote_price_validated": True}

    def selected(self, row):
        return patch.fresh_structure_codes({"rows": [row]}, "2026-10-15", self.now)

    def test_verified_same_day(self):
        self.assertEqual(self.selected(self.basic), {"1101"})

    def test_yesterday_cannot_be_ranked(self):
        self.assertEqual(self.selected({**self.basic, "structure_date": "2026-10-14"}), set())

    def test_missing_structure_date_not_proof(self):
        self.assertEqual(self.selected({**self.basic, "structure_date": None}), set())

    def test_missing_price_validation_not_proof(self):
        self.assertEqual(self.selected({**self.basic, "quote_price_validated": None}), set())

    def test_distant_structure_not_actionable(self):
        self.assertEqual(self.selected({**self.basic, "structure_time": "09:00"}), set())

    def test_missing_structure_becomes_stale_in_both_missions(self):
        for mission in ("intraday", "daytrade"):
            with self.subTest(mission=mission), tempfile.TemporaryDirectory() as td:
                path = Path(td) / "summary.json"
                path.write_text(json.dumps([{"code": "1101", "actionable": True,
                    "action_state": "SMALL_TEST", "opportunity_bucket": "ACTIONABLE_NOW",
                    "blockers": [], "risk_overlays": [], "missing_fields": []}]), encoding="utf-8")
                patch.gate_structure_file(path, set(), mission=mission)
                row = json.loads(path.read_text(encoding="utf-8"))[0]
                self.assertIs(row["actionable"], False)
                self.assertEqual(row["action_state"], "DATA_STALE")
                self.assertEqual(row["opportunity_bucket"], "STALE")


if __name__ == "__main__":
    unittest.main()
