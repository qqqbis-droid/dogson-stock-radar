import json
import pathlib
import unittest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "fixtures"
REGISTRIES = ROOT / "registries"

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate(schema_name, data):
    schema = load(SCHEMAS / schema_name)
    v = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(v.iter_errors(data), key=lambda e: list(e.path))

class ContractTests(unittest.TestCase):
    def test_registries_have_no_duplicate_enums(self):
        reg = load(REGISTRIES / "enum_registry.json")
        for key, values in reg.items():
            if isinstance(values, list):
                self.assertEqual(len(values), len(set(values)), key)

    def test_threshold_status_is_known(self):
        reg = load(REGISTRIES / "threshold_registry.json")
        allowed = {"active", "shadow", "candidate", "retired"}
        for key, entry in reg["entries"].items():
            self.assertIn(entry["status"], allowed, key)
            if entry["status"] == "shadow":
                self.assertIn("validation_report_id", entry, key)

    def test_valid_stock_decision(self):
        data = load(FIXTURES / "valid" / "stock-decision.json")
        self.assertEqual(validate("stock-decision.schema.json", data), [])

    def test_valid_manifest(self):
        data = load(FIXTURES / "valid" / "bundle-manifest.json")
        self.assertEqual(validate("bundle-manifest.schema.json", data), [])
        active = data["active_build_id"]
        self.assertTrue(all(d["build_id"] == active for d in data["datasets"].values()))

    def test_unknown_enum_fails_closed(self):
        data = load(FIXTURES / "invalid" / "stock-decision-unknown-enum.json")
        self.assertTrue(validate("stock-decision.schema.json", data))

    def test_stale_cannot_be_actionable(self):
        data = load(FIXTURES / "invalid" / "stock-decision-stale-actionable.json")
        self.assertTrue(validate("stock-decision.schema.json", data))

    def test_known_at_is_required(self):
        data = load(FIXTURES / "invalid" / "stock-decision-missing-known-at.json")
        self.assertTrue(validate("stock-decision.schema.json", data))

    def test_close_freeze_is_frozen_snapshot(self):
        data = load(FIXTURES / "edge-cases" / "close-freeze-stock-decision.json")
        self.assertEqual(validate("stock-decision.schema.json", data), [])
        self.assertEqual(data["session_phase"], "CLOSE_FREEZE")
        self.assertEqual(data["freshness"], "FROZEN")
        self.assertFalse(data["actionable"])

    def test_sector_registry_example(self):
        data = load(REGISTRIES / "sector_registry.example.json")
        self.assertEqual(validate("sector-registry.schema.json", data), [])

if __name__ == "__main__":
    unittest.main()
