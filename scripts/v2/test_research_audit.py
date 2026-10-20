#!/usr/bin/env python3
"""Research audit regression: do not infer safety or invent missing 60K."""
import unittest
from scripts.v2.build_stock_shards import research_checks

DATE="2026-10-20"

def base():
    return {"trade_date":DATE,"risk_overlays":[]}

def evidence():
    return {"chip_check_health":"PARTIAL",
        "foreign_date":DATE, "foreign_net_latest":10791777,
        "trust_date":DATE, "trust_net_latest":-922757,
        "sbl_date":DATE,"sbl_3down":True,"sbl_3change_pct":-2.04,
        "margin_date":DATE,"margin_status":"正常",
        "close":32.4,"ma20":31.66,"rsi":57.77,
        "hourly60":None}

class ResearchAuditTest(unittest.TestCase):
    def test_2353_partial(self):
        r=research_checks(base(),evidence(),DATE)
        by={x["key"]:x for x in r["checks"]}
        self.assertEqual(by["chip_sources"]["status"],"pending")
        self.assertEqual(by["hourly60"]["status"],"pending")
        self.assertEqual(by["restriction"]["status"],"pending")
        self.assertEqual(by["foreign"]["status"],"observed")
        self.assertIn("淨買",by["foreign"]["detail"])
        self.assertIn("淨賣",by["trust"]["detail"])
        self.assertEqual(by["sbl"]["status"],"observed")
        self.assertEqual(by["margin"]["status"],"observed")
        self.assertEqual(r["pending_count"],3)
        self.assertFalse(any("完全無風險" in x["detail"] for x in r["checks"]))

    def test_missing_data(self):
        r=research_checks(base(),None,None)
        self.assertEqual(r["observed_count"],0)
        self.assertEqual(r["pending_count"],len(r["checks"]))
        self.assertTrue(all(x["status"]=="pending" for x in r["checks"]))

    def test_stale_date_is_pending(self):
        e=evidence()
        e["foreign_date"]="2026-10-17"
        r=research_checks(base(),e,DATE)
        self.assertEqual(next(x for x in r["checks"] if x["key"]=="foreign")["status"],"pending")

    def test_confirmed_restriction_warning(self):
        d=base();d["risk_overlays"]=["TRADING_RESTRICTION"]
        r=research_checks(d,evidence(),DATE)
        self.assertEqual(next(x for x in r["checks"] if x["key"]=="restriction")["status"],"warning")

    def test_60k_only_if_same_day_and_valid(self):
        e=evidence()
        e["hourly60"]={"trade_date":DATE,"data_status":"OK","entry_light":"YELLOW"}
        r=research_checks(base(),e,DATE)
        self.assertEqual(next(x for x in r["checks"] if x["key"]=="hourly60")["status"],"observed")
        e["hourly60"]["trade_date"]="2026-10-17"
        r=research_checks(base(),e,DATE)
        self.assertEqual(next(x for x in r["checks"] if x["key"]=="hourly60")["status"],"pending")

if __name__=="__main__":
    unittest.main()
