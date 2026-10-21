#!/usr/bin/env python3
"""Guard original, production-tested Inuko wave score 2.0 after UI-only redesign.

This checks the original model SOURCE, rather than inventing score contributions
from interpreted labels or modifying historical fixed close snapshots.
"""
from pathlib import Path
import ast
import unittest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"scripts"/"build_data.py"

class ScoringSourceIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SOURCE.read_text(encoding="utf-8")
        cls.tree=ast.parse(cls.source)

    def test_all_four_original_20_engines_restored(self):
        names={n.name for n in self.tree.body if isinstance(n,ast.FunctionDef)}
        self.assertTrue({
          "_apply_technical_score_v2","_apply_chip_score_v2",
          "_apply_sector_score_v2","_apply_liquidity_score_v2"}.issubset(names))
        self.assertIn('r["technical_model_version"] = "inuko-tech-v2.0"',self.source)
        self.assertIn('r["chip_model_version"] = "inuko-chip-v2.0"',self.source)
        self.assertIn('r["sector_model_version"] = "inuko-sector-v2.0"',self.source)
        self.assertIn('r["liquidity_model_version"] = "inuko-liquidity-v2.0"',self.source)

    def test_real_model_invoked_in_actual_close_build(self):
        root=next(n for n in self.tree.body
                  if isinstance(n,ast.FunctionDef) and n.name=="add_component_scores")
        stmt=ast.get_source_segment(self.source,root)
        for name in ("_apply_technical_score_v2","_apply_chip_score_v2",
                     "_apply_sector_score_v2","_apply_liquidity_score_v2"):
            self.assertIn(name+"(r",stmt)
        self.assertIn("if not preliminary_intraday:",stmt)
        self.assertIn('r["swing_components"]',stmt)
        self.assertIn('r["entry_position_score"]',stmt)
        self.assertIn('r["market_in_quality_score"] = False',stmt)
        self.assertIn('"technical": 50.0, "chip": 25.0, "sector": 15.0, "liquidity": 10.0',stmt)

    def test_model_is_24_item_engine_not_legacy_explanation(self):
        src=self.source
        tech=next(n for n in self.tree.body
                  if isinstance(n,ast.FunctionDef) and n.name=="_apply_technical_score_v2")
        chip=next(n for n in self.tree.body
                  if isinstance(n,ast.FunctionDef) and n.name=="_apply_chip_score_v2")
        sector=next(n for n in self.tree.body
                    if isinstance(n,ast.FunctionDef) and n.name=="_apply_sector_score_v2")
        liquidity=next(n for n in self.tree.body
                       if isinstance(n,ast.FunctionDef) and n.name=="_apply_liquidity_score_v2")
        tech_body=ast.get_source_segment(src,tech)
        chip_body=ast.get_source_segment(src,chip)
        sector_body=ast.get_source_segment(src,sector)
        liquidity_body=ast.get_source_segment(src,liquidity)
        for key in ("trend","breakout","volume_price","momentum","relative","risk_quality"):
            self.assertIn('"'+key+'"',tech_body)
        for key in ("foreign","trust","sbl","margin","consensus","price_chip","sector_inst"):
            self.assertIn('"'+key+'"',chip_body)
        for key in ("breadth","leaders","persistence","capital_resonance","structure","taxonomy"):
            self.assertIn('"'+key+'"',sector_body)
        for key in ("avg_turnover","stability","price_impact","continuity","crowding"):
            self.assertIn('"'+key+'"',liquidity_body)
        for v in ("technical_components_v2","chip_components_v2","sector_components_v2","liquidity_components_v2"):
            self.assertIn(v,src)

if __name__=="__main__":
    unittest.main()
