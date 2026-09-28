from __future__ import annotations

import unittest

from scripts.v2.enrich_tradecases import build_case, build_delta, case_id


def decision(**overrides):
    base = {
        "build_id": "b1",
        "trade_date": "2026-09-23",
        "session_phase": "LIVE",
        "as_of": "2026-09-23T12:00:00+08:00",
        "known_at": "2026-09-23T12:00:00+08:00",
        "generated_at": "2026-09-23T12:00:01+08:00",
        "freshness": "FRESH",
        "source_status": {"sources": ["test"], "fallback": False},
        "decision_context_id": "b1:intraday:2330",
        "code": "2330",
        "lifecycle_stage": "SETUP",
        "action_state": "WAIT_TRIGGER",
        "actionable": False,
        "no_chase": False,
        "risk_overlays": [],
        "scores": {"entry_position_score": 70},
        "primary_group": "AI",
        "blockers": [],
        "upgrade_conditions": ["等待突破"],
        "why_now": ["結構改善"],
    }
    base.update(overrides)
    return base


class TradeCaseTests(unittest.TestCase):
    def test_case_id_is_stable_for_same_origin(self):
        self.assertEqual(case_id("2026-09-23", "SWING", "2330"), "TC:20260923:SWING:2330")

    def test_delta_ignores_identical_snapshots(self):
        before = decision()
        after = decision(decision_context_id="b1:close:2330", session_phase="POST_CLOSE")
        self.assertIsNone(build_delta(before, after, case_id("2026-09-23", "SWING", "2330")))

    def test_delta_keeps_structured_from_to(self):
        before = decision()
        after = decision(
            decision_context_id="b1:close:2330",
            session_phase="POST_CLOSE",
            lifecycle_stage="LAUNCH",
            action_state="WAIT_PULLBACK",
            no_chase=True,
        )
        delta = build_delta(before, after, case_id("2026-09-23", "SWING", "2330"))
        self.assertIsNotNone(delta)
        self.assertIn("lifecycle_stage", delta["changed_fields"])
        self.assertTrue(any(c["field"] == "action_state" and c["from"] == "WAIT_TRIGGER" and c["to"] == "WAIT_PULLBACK" for c in delta["changes"]))

    def test_public_case_never_invents_execution(self):
        latest = decision(decision_context_id="b1:close:2330", session_phase="POST_CLOSE")
        case = build_case(
            mission="SWING",
            origin_view="intraday",
            decisions=[("intraday", decision()), ("close", latest)],
            latest=latest,
            plan=None,
            delta=None,
        )
        self.assertEqual(case["actual_executions"], [])
        self.assertEqual(case["close_confirmation"], "PENDING")
        self.assertEqual(case["carry_state"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
