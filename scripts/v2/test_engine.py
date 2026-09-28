import unittest
from scripts.v2.engine import canonical_stage,synthesize_action,bucket_for
class EngineTests(unittest.TestCase):
    def test_overheat_is_not_lifecycle(self): self.assertEqual(canonical_stage("過熱不追","TREND"),"TREND")
    def test_stale_fails_closed(self):
        a,x=synthesize_action("LAUNCH",[],"STALE",80,False); self.assertEqual(a,"DATA_STALE"); self.assertFalse(x)
    def test_failed_never_new_entry(self):
        a,x=synthesize_action("FAILED",[],"FRESH",90,False); self.assertFalse(x)
    def test_high_quality_does_not_override_position_action(self):
        a,x=synthesize_action("TREND",["OVERHEAT"],"FRESH",95,False); self.assertEqual(a,"DO_NOT_CHASE"); self.assertFalse(x)
    def test_bucket_requires_mission(self):
        self.assertEqual(bucket_for("close_next_day","SETUP","WAIT_TRIGGER","FRESH",False),"BREAKOUT_WATCH"); self.assertEqual(bucket_for("intraday_swing","SETUP","WAIT_TRIGGER","LIVE",False),"WAIT_TRIGGER")
if __name__=="__main__": unittest.main()
