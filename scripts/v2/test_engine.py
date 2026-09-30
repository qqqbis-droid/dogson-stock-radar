import unittest
from scripts.v2.engine import canonical_stage, synthesize_action, bucket_for
from scripts.v2.legacy_adapter import canonical_datetime

class EngineTests(unittest.TestCase):
    def test_overheat_is_not_lifecycle(self):
        self.assertEqual(canonical_stage("過熱不追", "TREND"), "TREND")

    def test_stale_fails_closed(self):
        action, actionable = synthesize_action("LAUNCH", [], "STALE", 80, False)
        self.assertEqual(action, "DATA_STALE")
        self.assertFalse(actionable)

    def test_failed_never_new_entry(self):
        action, actionable = synthesize_action("FAILED", [], "FRESH", 90, False)
        self.assertFalse(actionable)

    def test_high_quality_does_not_override_position_action(self):
        action, actionable = synthesize_action("TREND", ["OVERHEAT"], "FRESH", 95, False)
        self.assertEqual(action, "DO_NOT_CHASE")
        self.assertFalse(actionable)

    def test_missing_entry_position_fails_closed(self):
        action, actionable = synthesize_action("LAUNCH", [], "LIVE", None, False)
        self.assertEqual(action, "WAIT_TRIGGER")
        self.assertFalse(actionable)

    def test_bucket_requires_mission(self):
        self.assertEqual(bucket_for("close_next_day", "SETUP", "WAIT_TRIGGER", "FRESH", False), "BREAKOUT_WATCH")
        self.assertEqual(bucket_for("intraday_swing", "SETUP", "WAIT_TRIGGER", "LIVE", False), "WAIT_TRIGGER")

    def test_legacy_time_only_with_seconds_is_canonical(self):
        self.assertEqual(
            canonical_datetime("13:30:00", "2026-09-23"),
            "2026-09-23T13:30:00+08:00",
        )

    def test_legacy_time_only_without_seconds_is_canonical(self):
        self.assertEqual(
            canonical_datetime("09:05", "2026-09-23"),
            "2026-09-23T09:05:00+08:00",
        )

    def test_legacy_full_naive_datetime_gets_taiwan_offset(self):
        self.assertEqual(
            canonical_datetime("2026-09-23 13:30:00", "2026-09-23"),
            "2026-09-23T13:30:00+08:00",
        )

    def test_legacy_invalid_time_does_not_invent_timestamp(self):
        self.assertIsNone(canonical_datetime("not-a-time", "2026-09-23"))

if __name__ == "__main__":
    unittest.main()
