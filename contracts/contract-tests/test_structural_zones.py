import copy
import json
import pathlib
import unittest

from jsonschema import Draft202012Validator, FormatChecker

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "structural-zone.schema.json").read_text(encoding="utf-8"))


def errors(data):
    validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
    return list(validator.iter_errors(data))


def sample():
    return {
        "schema_version": "2.0.0",
        "build_id": "cb2-zone-test",
        "dataset": "zone",
        "trade_date": "2026-09-30",
        "session_phase": "POST_CLOSE",
        "as_of": "2026-09-30T13:30:00+08:00",
        "known_at": "2026-09-30T13:35:00+08:00",
        "generated_at": "2026-09-30T13:36:00+08:00",
        "freshness": "FROZEN",
        "complete": True,
        "source_status": {"sources": ["close-structure"], "fallback": False},
        "zone_id": "2026-09-30:CLOSE:2330:SUPPORT:S1",
        "side": "SUPPORT",
        "rank": "S1",
        "label": "近端支撐",
        "low": 1380.0,
        "high": 1390.0,
        "center": 1385.0,
        "distance_pct": -1.8,
        "strength": 4,
        "confidence": 88,
        "evidence": ["20MA", "成交密集區", "前波低點"],
        "evidence_count": 3,
        "structure_state": "NEAR",
        "validation_condition": "回測價格帶守住並重新站回上緣。",
        "invalidation_condition": "連續兩根對應K收在下緣下方，或跌破後反抽站不回且量價轉弱。",
        "created_at": "2026-09-30T13:36:00+08:00",
        "last_tested_at": None,
        "role_state": "ORIGINAL"
    }


class StructuralZoneContractTests(unittest.TestCase):
    def test_ranked_zone_is_valid(self):
        self.assertEqual(errors(sample()), [])

    def test_all_four_ranks_are_supported(self):
        for rank, side in (("S1", "SUPPORT"), ("S2", "SUPPORT"), ("R1", "RESISTANCE"), ("R2", "RESISTANCE")):
            data = sample()
            data["rank"] = rank
            data["side"] = side
            self.assertEqual(errors(data), [], rank)

    def test_unknown_rank_fails_closed(self):
        data = sample()
        data["rank"] = "S3"
        self.assertTrue(errors(data))

    def test_unknown_structure_state_fails_closed(self):
        data = copy.deepcopy(sample())
        data["structure_state"] = "GUESSING"
        self.assertTrue(errors(data))


if __name__ == "__main__":
    unittest.main()
