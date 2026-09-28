from __future__ import annotations

LIFECYCLE = {
    "觀察": "OBSERVE",
    "蓄勢待發": "SETUP",
    "剛啟動": "LAUNCH",
    "趨勢持有": "TREND",
    "回踩觀察": "PULLBACK_TEST",
    "回踩承接": "PULLBACK_CONFIRMED",
    "轉弱警戒": "WEAKENING",
    "結構失效": "FAILED",
}

def canonical_stage(legacy_category, previous_stage=None):
    raw = str(legacy_category or "").strip()
    if raw == "過熱不追":
        return previous_stage if previous_stage in set(LIFECYCLE.values()) else "OBSERVE"
    return LIFECYCLE.get(raw, "OBSERVE")

def risk_overlays(row, freshness="FRESH"):
    out = []
    if row.get("overheat_reasons"):
        out.append("OVERHEAT")
    if row.get("trading_restriction"):
        out.append("TRADING_RESTRICTION")
    if row.get("liquidity_gate") is False:
        out.append("LIQUIDITY_RISK")
    if freshness in {"STALE", "UNKNOWN"}:
        out.append("DATA_QUALITY_RISK")
    return out

def synthesize_action(stage, overlays, freshness, entry_score=None, has_position=False):
    if freshness in {"STALE", "UNKNOWN"}:
        return "DATA_STALE", False
    if stage == "FAILED":
        return ("EXIT_PRIORITY", False) if has_position else ("WATCH", False)
    if stage == "WEAKENING":
        return ("REDUCE_WATCH", False) if has_position else ("WATCH", False)
    if "TRADING_RESTRICTION" in overlays or "LIQUIDITY_RISK" in overlays:
        return ("HOLD", False) if has_position else ("WATCH", False)
    if "OVERHEAT" in overlays:
        return ("HOLD", False) if has_position else ("DO_NOT_CHASE", False)
    if has_position and stage == "TREND":
        return "HOLD", False
    if stage == "PULLBACK_CONFIRMED" and (entry_score is None or entry_score >= 60):
        return ("ADD_ON_CONFIRM", True) if has_position else ("SMALL_TEST", True)
    if stage == "LAUNCH" and (entry_score is None or entry_score >= 60):
        return "SMALL_TEST", True
    if stage in {"SETUP", "PULLBACK_TEST"}:
        return "WAIT_TRIGGER", False
    if stage == "TREND":
        return "WAIT_PULLBACK", False
    return "WATCH", False

def bucket_for(mission, stage, action, freshness, actionable, has_position=False):
    if mission == "portfolio_risk":
        if action in {"EXIT_PRIORITY","REDUCE_WATCH","HOLD","ADD_ON_CONFIRM"}:
            return action
        return "REVIEW_TODAY"
    if mission == "daytrade_execution":
        if freshness not in {"LIVE", "FRESH"}:
            return "STALE"
        if actionable:
            return "ACTIONABLE_NOW"
        if action == "WAIT_TRIGGER":
            return "WAIT_TRIGGER"
        return "NO_TRADE"
    if mission == "intraday_swing":
        if stage in {"FAILED","WEAKENING"}:
            return "RISK"
        if freshness in {"STALE","UNKNOWN"}:
            return "RESEARCH_ONLY"
        if actionable and stage in {"LAUNCH","PULLBACK_CONFIRMED"}:
            return "TRIGGER_READY"
        if stage in {"SETUP","PULLBACK_TEST"}:
            return "WAIT_TRIGGER"
        if stage == "TREND" and action != "DO_NOT_CHASE":
            return "TREND_MONITOR"
        if action in {"WAIT_PULLBACK","DO_NOT_CHASE"}:
            return "WAIT_PULLBACK"
        return "RESEARCH_ONLY"
    if stage in {"FAILED","WEAKENING"}:
        return "RISK"
    if freshness in {"STALE","UNKNOWN"}:
        return "RESEARCH"
    if actionable and stage in {"LAUNCH","PULLBACK_CONFIRMED"}:
        return "NEXT_DAY_READY"
    if stage == "SETUP":
        return "BREAKOUT_WATCH"
    if action in {"WAIT_PULLBACK","DO_NOT_CHASE"} or stage == "PULLBACK_TEST":
        return "PULLBACK_WATCH"
    if stage == "TREND":
        return "TREND_QUALITY"
    return "RESEARCH"
