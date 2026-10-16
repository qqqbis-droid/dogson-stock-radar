#!/usr/bin/env python3
"""Regression: missing ignition scores must be repaired only from same-session
and exact-price source records; no synthetic points or past-day roll-forward."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("ignition_recovery",Path(__file__).with_name("restore_ignition_from_previous.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DAY="2026-10-16"
BUILD="fresh-close"
OLD="prior-good"

def row(code,price,day=DAY,scored=False):
    out={"code":code,"trade_date":day,"quote":{"price":price},
         "scores":{"swing_quality_score":80,"entry_position_score":70,"ignition_score":None},
         "ignition_model_version":None,"ignition_rank":None,"ignition_confidence":None}
    if scored:
        out.update({"ignition_model_version":"inuko-ignition-v2.0","ignition_rank":5,
                    "ignition_confidence":82,"ignition_stage":"剛點火",
                    "ignition_action":"等確認","ignition_gate_cap":85,
                    "ignition_raw_score":83,"ignition_execution_ready":False,
                    "known_at":DAY+"T15:25:00+08:00"})
        out["scores"]["ignition_score"]=81
    return out

class RestoreTests(unittest.TestCase):
    def fixture(self,source_day=DAY,source_price=27.3,include_model=True):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root=Path(td.name)
        base=root/"builds"/BUILD
        oldroot=root/"builds"/OLD
        base.mkdir(parents=True)
        oldroot.mkdir(parents=True)
        current=row("1101",27.3)
        prior=row("1101",source_price,source_day,include_model)
        datasets={}
        for key,filename,obj in [
            ("decision_close_detail","decision-close-detail.json",{"items":{"1101":current}}),
            ("decision_close_index","decision-close-index.json",[dict(current)]),
            ("decision_close_summary","decision-close-summary.json",[dict(current)]),
            ("stock_detail_close","stock-detail-close.json",{"items":{"1101":{"trade_date":DAY,"close":27.3}}}),
        ]:
            path=base/filename
            path.write_text(json.dumps(obj),encoding="utf-8")
            datasets[key]={"url":f"./data/builds/{BUILD}/{filename}","build_id":BUILD}
        (oldroot/"decision-close-detail.json").write_text(json.dumps({"items":{"1101":prior}}),encoding="utf-8")
        (oldroot/"stock-detail-close.json").write_text(
            json.dumps({"items":{"1101":{"trade_date":source_day,"close":source_price,
               "ignition_components_v2":{"structure":{"score":20}},"ignition_score_v2":81}}}),encoding="utf-8")
        (root/"current_manifest.json").write_text(json.dumps({
            "active_build_id":BUILD,"previous_good_build_id":OLD,
            "trade_date":DAY,"datasets":datasets,"health":{"validation_passed":True}
        }),encoding="utf-8")
        return root

    def test_exact_session_and_price_restores_model_and_breakdown(self):
        root=self.fixture()
        r=mod.restore(root)
        self.assertEqual(r["restored"],1)
        self.assertEqual(r["breakdown_restored"],1)
        m=mod.load(root/"current_manifest.json")
        for key in ("decision_close_index","decision_close_summary"):
            a=mod.load(mod.filepath(root,m["datasets"][key]))[0]
            self.assertEqual(a["scores"]["ignition_score"],81)
            self.assertEqual(a["ignition_rank"],5)
            self.assertNotIn("ignition_recovered_from_build",a)
        evidence=mod.load(mod.filepath(root,m["datasets"]["stock_detail_close"]))["items"]["1101"]
        self.assertEqual(evidence["ignition_components_v2"]["structure"]["score"],20)
        self.assertEqual(mod.restore(root)["restored"],0)
    def test_previous_session_rejected(self):
        self.assertEqual(mod.restore(self.fixture(source_day="2026-10-15"))["restored"],0)
    def test_different_close_price_rejected(self):
        self.assertEqual(mod.restore(self.fixture(source_price=28))["restored"],0)
    def test_missing_actual_model_rejected(self):
        self.assertEqual(mod.restore(self.fixture(include_model=False))["restored"],0)
    def test_never_overwrite_existing_scored_row(self):
        root=self.fixture()
        path=root/"builds"/BUILD/"decision-close-detail.json"
        data=mod.load(path)
        data["items"]["1101"]=row("1101",27.3,scored=True)
        data["items"]["1101"]["scores"]["ignition_score"]=90
        path.write_text(json.dumps(data),encoding="utf-8")
        self.assertEqual(mod.restore(root)["restored"],0)
        self.assertEqual(mod.load(path)["items"]["1101"]["scores"]["ignition_score"],90)

if __name__=="__main__":unittest.main()
