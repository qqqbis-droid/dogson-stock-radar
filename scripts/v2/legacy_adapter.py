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

def first_num(row, keys):
    for key in keys:
        value = num(row.get(key))
        if value is not None:
            return value
    return None

def canonical_datetime(value, trade_date):
    """Normalize legacy timestamps without changing their represented clock time.

    Accepted examples:
      13:30            -> YYYY-MM-DDT13:30:00+08:00
      13:30:00         -> YYYY-MM-DDT13:30:00+08:00
      YYYY-MM-DD HH:MM:SS -> YYYY-MM-DDTHH:MM:SS+08:00
      ISO-8601 with timezone -> preserved as an offset-aware ISO timestamp

    Unknown / malformed inputs return None rather than inventing a timestamp.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TW)
        return dt.isoformat(timespec="seconds")

    raw = str(value).strip()
    if not raw:
        return None

    # Time-only legacy values are common in intraday snapshots.
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(raw, fmt).time()
            dt = datetime.strptime(str(trade_date), "%Y-%m-%d").replace(
                hour=parsed.hour,
                minute=parsed.minute,
                second=parsed.second,
                microsecond=0,
                tzinfo=TW,
            )
            return dt.isoformat(timespec="seconds")
        except (TypeError, ValueError):
            pass

    # Accept common full datetime forms. Naive values are Taiwan-local source time.
    candidates = [raw]
    if raw.endswith("Z"):
        candidates.insert(0, raw[:-1] + "+00:00")
    if " " in raw and "T" not in raw:
        candidates.insert(0, raw.replace(" ", "T", 1))
    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TW)
            return dt.isoformat(timespec="seconds")
        except ValueError:
            pass
    return None

def infer_volume_unit(row):
    raw = str(row.get("volume_unit") or "").strip().upper()
    if raw in {"SHARE", "SHARES", "股"}:
        return "SHARES"
    if raw in {"LOT", "LOTS", "張"}:
        return "LOTS"
    return "UNKNOWN"

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
    code = str(row.get("code") or "").strip()
    now = datetime.now(TW).isoformat(timespec="seconds")
    raw_as_of = row.get("quote_time") or row.get("updated_at") or row.get("time")
    as_of = canonical_datetime(raw_as_of, trade_date)

    price = first_num(row, ("current_price", "price", "close", "last_price", "last"))
    day_change_pct = first_num(row, ("day_change", "day_change_pct", "change_pct", "pct_change"))
    volume = first_num(row, ("current_volume", "volume", "total_volume"))
    relative_volume = first_num(row, ("vol_x", "relative_volume", "volume_ratio"))
    turnover_value_twd = first_num(row, ("current_turnover", "turnover_value_twd"))
    quote = {
        "price": price,
        "day_change_pct": day_change_pct,
        "volume": volume,
        "volume_unit": infer_volume_unit(row),
        "relative_volume": relative_volume,
        "turnover_value_twd": turnover_value_twd,
        "quote_time": as_of,
    }

    missing=[]
    for name,value in [("swing_quality_score",score),("entry_position_score",entry),("quote.price",price)]:
        if value is None: missing.append(name)
    coverage=max(0,100-20*sum(1 for x in missing if x in {"swing_quality_score","entry_position_score"})-10*sum(1 for x in missing if x=="quote.price")); confidence=num(row.get("data_confidence"),coverage)
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
        "quote":quote,
        "scores":{"swing_quality_score":score,"intraday_momentum_score":intraday,"daytrade_score":daytrade,"entry_position_score":entry,"market_score":market_score},
        "lifecycle_stage":stage,"previous_stage":previous_stage,"stage_changed_at":None,"stage_age":None,"stage_confidence":None,"action_state":action,"actionable":bool(actionable),"no_chase":action=="DO_NOT_CHASE","risk_overlays":overlays,"opportunity_bucket":bucket,"opportunity_rank":None,
        "why_now":why[:3],"blockers":blockers[:3],"upgrade_conditions":["等待下一個合法 Trigger / 結構確認"] if not actionable else [],"risk_flags":list(row.get("stage_risks") or []),"data_confidence":confidence,"component_coverage":coverage,"missing_fields":missing,
        "trade_plan_id":None,"case_id":None,"support_zone_ids":[],"resistance_zone_ids":[],"evidence_ids":[]
    }
