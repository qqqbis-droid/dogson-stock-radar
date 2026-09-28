from __future__ import annotations
from datetime import datetime, timezone, timedelta
from .engine import canonical_stage, risk_overlays, synthesize_action, bucket_for

TW = timezone(timedelta(hours=8))

def num(v, default=None):
    try:
        x = float(v)
        return x if x == x else default
    except Exception:
        return default

def infer_freshness(row, session_phase):
    if session_phase == "LIVE": return "LIVE"
    if session_phase == "CLOSE_FREEZE": return "FROZEN"
    return "FRESH"

def adapt_legacy_stock(row, *, build_id, trade_date, session_phase, mission, market_score=None, previous_stage=None, has_position=False):
    freshness = infer_freshness(row, session_phase)
    stage = canonical_stage(row.get("category"), previous_stage=previous_stage)
    overlays = risk_overlays(row, freshness=freshness)
    entry = num(row.get("entry_position_score", row.get("entry_score")))
    action, actionable = synthesize_action(stage, overlays, freshness, entry_score=entry, has_position=has_position)
    if session_phase == "CLOSE_FREEZE": actionable = False
    bucket = bucket_for(mission, stage, action, freshness, actionable, has_position=has_position)
    score = num(row.get("swing_quality_score", row.get("score")))
    intraday = num(row.get("intraday_score", row.get("intraday_momentum_score")))
    daytrade = num(row.get("daytrade_score"))
    missing=[]
    for name,value in [("swing_quality_score",score),("entry_position_score",entry)]:
        if value is None: missing.append(name)
    coverage=max(0,100-20*len(missing)); confidence=num(row.get("data_confidence"),coverage)
    code=str(row.get("code") or "").strip(); now=datetime.now(TW).isoformat(timespec="seconds")
    as_of=row.get("updated_at") or row.get("time") or now
    if isinstance(as_of,str) and "T" not in as_of:
        as_of=f"{trade_date}T{as_of}:00+08:00" if ":" in as_of else now
    why=list(row.get("stage_signals") or row.get("reasons") or [])
    blockers=[]
    if not actionable:
        if action=="WAIT_TRIGGER": blockers.append("等待正式觸發")
        if action in {"WAIT_PULLBACK","DO_NOT_CHASE"}: blockers.append("位置不宜追價")
        if action=="DATA_STALE": blockers.append("資料新鮮度不足")
    return {
        "schema_version":"2.0.0","build_id":build_id,"dataset":"decision","trade_date":trade_date,"session_phase":session_phase,"as_of":as_of,"known_at":now,"generated_at":now,"freshness":freshness,"complete":len(missing)==0,"confidence":confidence,
        "source_status":{"sources":["legacy-v1-adapter"],"fallback":False,"fallback_source":None,"fallback_build_id":None,"fallback_reason":None,"last_success_at":now},
        "decision_context_id":f"{build_id}:{mission}:{code}","code":code,"name":str(row.get("name") or code),"market":str(row.get("market") or "UNKNOWN"),"industry":row.get("industry_name") or row.get("industry"),"primary_group":row.get("sector_group"),"secondary_groups":[],"theme_tags":[],
        "scores":{"swing_quality_score":score,"intraday_momentum_score":intraday,"daytrade_score":daytrade,"entry_position_score":entry,"market_score":market_score},
        "lifecycle_stage":stage,"previous_stage":previous_stage,"stage_changed_at":None,"stage_age":None,"stage_confidence":None,"action_state":action,"actionable":bool(actionable),"no_chase":action=="DO_NOT_CHASE","risk_overlays":overlays,"opportunity_bucket":bucket,"opportunity_rank":None,
        "why_now":why[:3],"blockers":blockers[:3],"upgrade_conditions":["等待下一個合法 Trigger / 結構確認"] if not actionable else [],"risk_flags":list(row.get("stage_risks") or []),"data_confidence":confidence,"component_coverage":coverage,"missing_fields":missing,
        "trade_plan_id":None,"case_id":None,"support_zone_ids":[],"resistance_zone_ids":[],"evidence_ids":[]
    }
