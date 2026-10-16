#!/usr/bin/env python3
"""Prove source-derived Ignition 2.0 restoration and fail-closed source gates."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.v2.restore_verified_ignition import run, valid_source

PARTS={"structure":25,"volume_acceleration":20,"sector_resonance":15,
       "relative_acceleration":15,"chip_acceleration":15,"tradability_risk":10}
DAY="2026-10-16"
BID="demo-build"

def row(code):
    return {
       "code":code,"date":DAY,"close":100.0,
       "ignition_model_version":"inuko-ignition-v2.0",
       "ignition_score_v2":80.0,"ignition_raw_score_v2":80.0,"ignition_gate_cap_v2":100,
       "ignition_confidence_v2":90,"ignition_stage_v2":"剛點火",
       "ignition_action_v2":"小量試單候選","ignition_reasons_v2":["量能加速"],
       "ignition_components_v2":{k:{"score":v*.8,"max":v} for k,v in PARTS.items()},
    }

class TestRepair(unittest.TestCase):
    def test_only_genuine_six_part_score_is_accepted(self):
        x=row("1101")
        self.assertTrue(valid_source(x,DAY))
        self.assertFalse(valid_source({**x,"date":"2026-10-15"},DAY))
        self.assertFalse(valid_source({**x,"ignition_components_v2":{}},DAY))
        self.assertFalse(valid_source({**x,"ignition_raw_score_v2":100},DAY))

    def test_detail_index_summary_reconciled_without_swing_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"data";b=root/"builds"/BID;b.mkdir(parents=True)
            raw=Path(td)/"close.json"
            raw.write_text(json.dumps({"rows":[{**row(str(1000+i)),"ignition_rank_v2":i+5} for i in range(16)]}))
            ds={}
            items={}
            for i in range(16):
                code=str(1000+i)
                items[code]={"code":code,"trade_date":DAY,"quote":{"price":100.0},
                     "scores":{"swing_quality_score":88,"entry_position_score":72,"ignition_score":None},
                     "ignition_rank":None}
            sources={"decision_close_detail":{"items":items,"build_id":BID},
                "decision_close_index":list(items.values()),
                "decision_close_summary":list(items.values())[:15]}
            for k,v in sources.items():
                path=b/(k+".json");path.write_text(json.dumps(v))
                ds[k]={"url":"./data/builds/"+BID+"/"+k+".json","build_id":BID}
            manifest={"active_build_id":BID,"trade_date":DAY,"datasets":ds}
            (root/"current_manifest.json").write_text(json.dumps(manifest))
            n=run(root,raw)
            self.assertEqual(n,16)
            output=json.loads((b/"decision_close_detail.json").read_text())
            self.assertEqual(len([r for r in output["items"].values() if r["ignition_rank"]]),16)
            self.assertEqual(output["items"]["1000"]["scores"]["ignition_score"],80)
            self.assertEqual(output["items"]["1000"]["scores"]["swing_quality_score"],88)
            self.assertEqual(output["items"]["1000"]["quote"]["price"],100.0)
            index=json.loads((b/"decision_close_index.json").read_text())
            self.assertEqual(index[0]["ignition_rank"],5)
            self.assertEqual(index[0]["ignition_execution_state"],"READY")
            m=json.loads((root/"current_manifest.json").read_text())
            self.assertEqual(m["datasets"]["decision_close_index"]["bytes"],(b/"decision_close_index.json").stat().st_size)
            # Cross-day source must be refused, NEVER reuse yesterday's model.
            old=json.loads(raw.read_text())
            for r in old["rows"]:r["date"]="2026-10-15"
            raw.write_text(json.dumps(old))
            with self.assertRaises(SystemExit):
                run(root,raw)

if __name__=="__main__":
    unittest.main()
