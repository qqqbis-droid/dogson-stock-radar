#!/usr/bin/env python3
"""Regression: next-session live rebuild must keep last validated close unchanged."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from scripts.v2.preserve_frozen_close import CLOSE_KEYS, frozen_snapshot, hydrate, capture, load

PIN=Path(__file__).resolve().parents[2]/"docs/v2/frozen-close/latest"

class FrozenCloseTest(unittest.TestCase):
    def test_last_completed_session_immutable_across_live_rollover(self):
        fm, previous=frozen_snapshot(PIN)
        frozen_date=fm["trade_date"]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);active="new-intraday-build"; build=root/"builds"/active
            build.mkdir(parents=True)
            metas={}
            for key in CLOSE_KEYS:
                path=build/(key+".json")
                path.write_text("{}\n",encoding="utf-8")
                metas[key]={"url":f"./data/builds/{active}/{key}.json","as_of":frozen_date+"T13:30:00+08:00",
                            "complete":False,"build_id":active}
            mp=root/"current_manifest.json"
            mp.write_text(json.dumps({"trade_date":"2026-10-21","active_build_id":active,"datasets":metas}))
            result=hydrate(root,PIN)
            self.assertEqual(result["action"],"restored")
            updated=load(mp)
            self.assertEqual(updated["trade_date"],"2026-10-21")
            self.assertEqual(updated["close_frozen_trade_date"],frozen_date)
            for key in CLOSE_KEYS:
                new=load(build/(key+".json"))
                old=previous[key]
                self.assertEqual(json.loads(json.dumps(new).replace(active,fm["source_build_id"])),old,key)
            self.assertTrue(load(build/"market_close_context.json")["complete"])
            self.assertTrue(load(build/"capital_close_context.json")["complete"])
            summary=load(build/"decision_close_summary.json")
            if frozen_date=="2026-10-20":
                by={str(s.get("code")):s for s in summary}
                self.assertEqual(by["2002"]["scores"]["swing_quality_score"],82.9)
                self.assertEqual(by["5880"]["scores"]["swing_quality_score"],74.8)
                self.assertEqual(by["2002"]["quote"]["price"],19.6)
            self.assertTrue(all(s["freshness"] in ("FRESH","FROZEN") for s in summary))
            self.assertEqual(hydrate(root,PIN)["action"],"restored")

    def test_next_complete_close_is_not_rolled_back(self):
        fm,_=frozen_snapshot(PIN)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            root.mkdir(exist_ok=True)
            m={"active_build_id":"next-build","trade_date":"2026-10-22",
               "datasets":{"decision_close_summary":{"as_of":"2026-10-22T13:30:00+08:00"}}}
            (root/"current_manifest.json").write_text(json.dumps(m))
            self.assertEqual(hydrate(root,PIN)["action"],"new_completed_close")

if __name__=="__main__":
    unittest.main()
