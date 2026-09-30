import copy
import json
import pathlib
import unittest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "fixtures"
REGISTRIES = ROOT / "registries"

VERSION_FIELDS = (
    "app_contract_version",
    "schema_version",
    "engine_version",
    "enum_registry_version",
    "threshold_registry_version",
    "taxonomy_version",
)


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate(schema_name, data):
    schema = load(SCHEMAS / schema_name)
    v = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(v.iter_errors(data), key=lambda e: list(e.path))


def active_version_set():
    reg = load(REGISTRIES / "version_registry.json")
    active_id = reg["active_version_set_id"]
    return reg, active_id, reg["version_sets"][active_id]


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

    def test_version_registry_schema_and_single_active_set(self):
        reg, active_id, active = active_version_set()
        self.assertEqual(validate("version-registry.schema.json", reg), [])
        self.assertIn(active_id, reg["version_sets"])
        self.assertEqual(active["status"], "active")
        self.assertEqual(
            sum(1 for item in reg["version_sets"].values() if item["status"] == "active"),
            1,
        )

    def test_active_version_set_matches_canonical_registries(self):
        _, _, active = active_version_set()
        self.assertEqual(active["enum_registry_version"], load(REGISTRIES / "enum_registry.json")["registry_version"])
        self.assertEqual(active["threshold_registry_version"], load(REGISTRIES / "threshold_registry.json")["registry_version"])
        self.assertEqual(active["taxonomy_version"], load(REGISTRIES / "taxonomy_registry.json")["taxonomy_version"])

    def test_valid_stock_decision(self):
        data = load(FIXTURES / "valid" / "stock-decision.json")
        self.assertEqual(validate("stock-decision.schema.json", data), [])

    def test_valid_manifest(self):
        data = load(FIXTURES / "valid" / "bundle-manifest.json")
        self.assertEqual(validate("bundle-manifest.schema.json", data), [])
        active = data["active_build_id"]
        self.assertTrue(all(d["build_id"] == active for d in data["datasets"].values()))

    def test_manifest_version_binding_matches_active_set(self):
        reg, active_id, active = active_version_set()
        data = load(FIXTURES / "valid" / "bundle-manifest.json")
        self.assertEqual(data["version_registry_version"], reg["registry_version"])
        self.assertEqual(data["version_set_id"], active_id)
        for field in VERSION_FIELDS:
            self.assertEqual(data[field], active[field], field)
        self.assertEqual(
            set(reg["manifest_binding"]["fields"]),
            {"version_registry_version", "version_set_id", *VERSION_FIELDS},
        )

    def test_manifest_version_drift_fails_closed(self):
        data = copy.deepcopy(load(FIXTURES / "valid" / "bundle-manifest.json"))
        data["threshold_registry_version"] = "2.0.1"
        self.assertTrue(validate("bundle-manifest.schema.json", data))

    def test_manifest_accepts_declared_build_identity(self):
        data = copy.deepcopy(load(FIXTURES / "valid" / "bundle-manifest.json"))
        data["health"]["build_identity"] = {
            "source_fingerprint": "0123456789",
            "implementation_fingerprint": "abcdef0123",
            "identity_rule": "source-content + production-v2-implementation-contract",
        }
        self.assertEqual(validate("bundle-manifest.schema.json", data), [])

    def test_manifest_rejects_malformed_build_identity(self):
        data = copy.deepcopy(load(FIXTURES / "valid" / "bundle-manifest.json"))
        data["health"]["build_identity"] = {
            "source_fingerprint": "too-short",
            "implementation_fingerprint": "abcdef0123",
            "identity_rule": "source-content + production-v2-implementation-contract",
        }
        self.assertTrue(validate("bundle-manifest.schema.json", data))

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
