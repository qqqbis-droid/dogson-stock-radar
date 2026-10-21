#!/usr/bin/env python3
"""Model 2.0 source gate: missing data must never downgrade silently."""
import unittest
from scripts.v2.validate_full_swing_source import validate, MODELS

def fixture():
    r={"code":"3231","swing_quality_score":76.8,"entry_position_score":60.0,
       "swing_components":{"technical":39.0,"chip":20.0,"sector":7.8,"liquidity":10.0},
       "swing_weights":{"technical":50.0,"chip":25.0,"sector":15.0,"liquidity":10.0},
       "swing_weighted_components":{"technical":39.0,"chip":20.0,"sector":7.8,"liquidity":10.0}}
    for kind,(version,field,keys,cap) in MODELS.items():
        r[kind+"_model_version"]=version
        r[field]={key:{} for key in keys}
        r[kind+"_score_v2"]=r["swing_components"][kind]
    return {"trade_date":"2026-10-21","rows":[r]}

class OriginalSourceGuard(unittest.TestCase):
    def test_complete(self):
        a=validate(fixture())
        self.assertEqual(a["items_per_stock"],24)
        self.assertEqual(a["original_model_count"],1)
    def test_each_model_missing_fails(self):
        for name in MODELS:
            with self.subTest(model=name):
                p=fixture()
                del p["rows"][0][name+"_model_version"]
                with self.assertRaisesRegex(ValueError,"version not original"):
                    validate(p)
    def test_component_missing_fails(self):
        p=fixture();del p["rows"][0]["chip_components_v2"]["margin"]
        with self.assertRaisesRegex(ValueError,"component keys missing"):
            validate(p)
    def test_synthetic_explanation_cannot_replace_orig_score(self):
        p=fixture()
        del p["rows"][0]["technical_components_v2"]
        p["rows"][0]["score_explanations"]={"technical":{"items":[{"points":39}]}}
        with self.assertRaisesRegex(ValueError,"component keys missing"):
            validate(p)
    def test_unbalanced_score_fails(self):
        p=fixture();p["rows"][0]["swing_quality_score"]=90
        with self.assertRaisesRegex(ValueError,"cannot reconcile"):
            validate(p)

if __name__=="__main__":unittest.main()
