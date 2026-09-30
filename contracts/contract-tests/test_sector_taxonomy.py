import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / "scripts" / "sector_groups.py"

spec = importlib.util.spec_from_file_location("sector_groups_contract", MODULE)
sg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sg)


class SectorTaxonomy21Tests(unittest.TestCase):
    def test_taxonomy_has_material_coverage(self):
        stats = sg.taxonomy_stats()
        self.assertEqual(stats["taxonomy_version"], "2.1.0")
        self.assertGreaterEqual(stats["registry_entries"], 220)
        self.assertGreaterEqual(stats["primary_groups"], 30)
        self.assertGreaterEqual(stats["eligible_primary_codes"], 220)
        self.assertFalse(stats["official_industry_can_grant_full_core_score"])

    def test_every_registry_scoring_group_has_minimum_peer_sample(self):
        for group, count in sg.taxonomy_stats()["group_sizes"].items():
            self.assertGreaterEqual(count, sg.PRIMARY_GROUP_MIN_PEERS, group)

    def test_primary_codes_are_unique(self):
        raw_count = sum(len(codes) for codes in sg.PRIMARY_GROUPS.values())
        self.assertEqual(raw_count, len(sg.CODE_TO_GROUP))

    def test_cross_exposure_does_not_double_count(self):
        r = sg.classification_for("2379", industry="24")
        self.assertEqual(r["primary_group"], "IC設計")
        self.assertEqual(sg.sector_group_for("2379", industry="24"), "IC設計")
        self.assertEqual(r["score_source"], "PRIMARY_GROUP")
        self.assertEqual(r["evidence_status"], "CURATED_ONLY")
        self.assertIn("網通IC", [x["group"] for x in r["secondary_groups"]])

    def test_diversified_company_falls_back_to_official_proxy(self):
        r = sg.classification_for("1303", industry="03")
        self.assertIsNone(r["primary_group"])
        self.assertFalse(r["core_sector_score_eligible"])
        self.assertEqual(r["score_source"], "OFFICIAL_PROXY")
        self.assertEqual(r["evidence_status"], "REVIEWED_MULTI_BUSINESS")
        self.assertEqual(sg.sector_group_for("1303", industry="03"), None)
        self.assertIn("CCL／電子材料", [x["group"] for x in r["secondary_groups"]])

    def test_even_narrow_official_industry_stays_capped_proxy(self):
        r = sg.classification_for("1101", industry="01")
        self.assertIsNone(r["primary_group"])
        self.assertFalse(r["core_sector_score_eligible"])
        self.assertEqual(r["score_source"], "OFFICIAL_PROXY")
        self.assertEqual(r["evidence_status"], "OFFICIAL_DIRECT")
        self.assertIsNone(sg.sector_group_for("1101", industry="01"))

    def test_broad_official_industry_stays_proxy(self):
        for code in ("24", "25", "26", "27", "28", "31"):
            r = sg.classification_for("9999", industry=code)
            self.assertEqual(r["classification_status"], "OFFICIAL_ONLY", code)
            self.assertEqual(r["score_source"], "OFFICIAL_PROXY", code)
            self.assertEqual(r["evidence_status"], "OFFICIAL_DIRECT", code)
            self.assertFalse(r["core_sector_score_eligible"], code)
            self.assertIsNone(sg.sector_group_for("9999", industry=code), code)

    def test_unknown_narrow_group_is_not_zeroed(self):
        r = sg.classification_for("9999", industry="24")
        self.assertEqual(r["classification_status"], "OFFICIAL_ONLY")
        self.assertEqual(r["official_industry"], "半導體業")
        self.assertEqual(r["score_source"], "OFFICIAL_PROXY")
        self.assertIsNone(sg.sector_group_for("9999", industry="24"))


if __name__ == "__main__":
    unittest.main()
