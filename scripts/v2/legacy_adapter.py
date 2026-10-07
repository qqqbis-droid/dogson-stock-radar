from __future__ import annotations
from datetime import datetime, timezone, timedelta
from .engine import canonical_stage, risk_overlays, synthesize_action, bucket_for

try:
    from sector_groups import classification_for
except ImportError:  # package/import tests
    from scripts.sector_groups import classification_for

TW = timezone(timedelta(hours=8))

SWING_COMPONENTS = {
    "technical": ("技術", 50.0),
    "chip": ("籌碼", 25.0),
    "sector": ("族群", 15.0),
    "liquidity": ("流動性", 10.0),
}
INTRADAY_COMPONENTS = {
    "price_structure": ("價格結構", 30.0),
    "flow_volume": ("量價動能", 25.0),
    "relative_strength": ("相對強弱", 15.0),
    "sector": ("族群", 20.0),
    "liquidity_risk": ("流動性／追價風險", 10.0),
}
DAYTRADE_COMPONENTS = {
    "execution_structure": ("執行結構", 30.0),
    "flow_volume": ("量價推進", 25.0),
    "relative_sector": ("相對強弱／族群", 20.0),
    "timing_volatility": ("時機／波動效率", 15.0),
    "liquidity_risk": ("流動性／追價風險", 10.0),
}

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
    """Normalize legacy timestamps without changing their represented clock time."""
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
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(raw, fmt).time()
            dt = datetime.strptime(str(trade_date), "%Y-%m-%d").replace(
                hour=parsed.hour, minute=parsed.minute, second=parsed.second,
                microsecond=0, tzinfo=TW,
            )
            return dt.isoformat(timespec="seconds")
        except (TypeError, ValueError):
            pass
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
    if session_phase == "LIVE":
        return "LIVE"
    if session_phase == "CLOSE_FREEZE":
        return "FROZEN"
    return "FRESH"

def _component_model(*, model, source, total_score, raw, spec, contribution=None, contribution_max=None, note=None):
    raw = raw if isinstance(raw, dict) else {}
    contribution = contribution if isinstance(contribution, dict) else raw
    contribution_max = contribution_max if isinstance(contribution_max, dict) else {}
    items = []
    for key, (label, raw_max) in spec.items():
        raw_score = num(raw.get(key))
        actual = num(contribution.get(key))
        if raw_score is None and actual is None:
            continue
        if actual is None:
            actual = raw_score
        max_actual = num(contribution_max.get(key), raw_max)
        items.append({
            "key": key,
            "label": label,
            "raw_score": raw_score,
            "raw_max": raw_max,
            "contribution": actual,
            "contribution_max": max_actual,
        })
    if not items:
        return None
    return {
        "model": model,
        "model_status": "MIGRATED_SHADOW",
        "source": str(source or "legacy-v1"),
        "total_score": num(total_score),
        "items": items,
        "note": note,
    }

def build_component_models(row, swing_score, intraday_score, daytrade_score):
    swing = _component_model(
        model="swing_quality",
        source=row.get("swing_weight_source") or "baseline",
        total_score=swing_score,
        raw=row.get("swing_components"),
        spec=SWING_COMPONENTS,
        contribution=row.get("swing_weighted_components"),
        contribution_max=row.get("swing_weights"),
        note="原始 component 保留 50/25/15/10 尺度；若有歷史校準，實際貢獻顯示校準後權重。",
    )
    intraday = _component_model(
        model="intraday_momentum",
        source="intraday_execution_30_25_15_20_10",
        total_score=intraday_score,
        raw=row.get("intraday_components") or row.get("source_intraday_components"),
        spec=INTRADAY_COMPONENTS,
        note="盤中籌碼只作最近盤後背景，不灌入即時動能分。",
    )
    daytrade = _component_model(
        model="daytrade_execution",
        source="daytrade_30_25_20_15_10",
        total_score=daytrade_score,
        raw=row.get("daytrade_components"),
        spec=DAYTRADE_COMPONENTS,
        note="當沖分為獨立執行模型，不覆蓋波段分、盤中分或 Lifecycle。",
    )
    return {"swing": swing, "intraday": intraday, "daytrade": daytrade}

def ignition_execution(stage, signal_action, score, entry, gate_cap):
    """Keep ignition probability/acceleration separate from whether the current
    price is a good place to act. A strong ignition score never upgrades a poor
    entry location into a buy signal."""
    st = str(stage or "")
    act = str(signal_action or "觀察")
    s = num(score)
    pos = num(entry)
    cap = num(gate_cap, 100)

    if st == "末端過熱／不追":
        return {"state":"NO_CHASE","ready":False,"action":"不追","note":"點火訊號可能仍強，但末端／追價 Gate 已禁止追價。"}
    if st == "蓄勢":
        return {"state":"WAIT_BREAKOUT","ready":False,"action":"等突破","note":"尚未完成點火，等待正式突破與量價確認。"}
    if st == "已發動等回踩":
        return {"state":"WAIT_PULLBACK","ready":False,"action":"等回踩","note":"已發動但離起漲點偏遠，等回踩再評估。"}
    if st in {"剛點火","突破回踩"}:
        if pos is None:
            return {"state":"WAIT_POSITION","ready":False,"action":"位置待補","note":"點火條件成立，但進場位置資料不足，不直接給試單訊號。"}
        if pos < 55:
            return {"state":"WAIT_PULLBACK","ready":False,"action":"點火成立・位置差，等回踩","note":f"點火成立，但進場位置僅 {pos:.0f}/100，先等回踩，不把強勢當買點。"}
        if pos < 65:
            return {"state":"WAIT_CONFIRM","ready":False,"action":"點火成立・等確認","note":f"點火成立，進場位置 {pos:.0f}/100；等支撐／突破回測確認後再升級。"}
        if s is not None and s >= 75 and (cap is None or cap >= 75):
            if st == "突破回踩":
                return {"state":"RETEST_READY","ready":True,"action":"等承接／小量試單","note":f"突破回踩且進場位置 {pos:.0f}/100，可等承接確認後小量試單。"}
            return {"state":"READY","ready":True,"action":"小量試單候選","note":f"剛點火且進場位置 {pos:.0f}/100，具備小量試單資格；仍不可追高。"}
        return {"state":"WAIT_CONFIRM","ready":False,"action":"等確認","note":"點火尚未同時滿足分數／Gate／位置三項執行條件。"}
    return {"state":"WATCH","ready":False,"action":act if act else "觀察","note":"點火條件尚未集中，維持觀察。"}

def adapt_legacy_stock(row, *, build_id, trade_date, session_phase, mission, market_score=None, previous_stage=None, has_position=False):
    freshness = infer_freshness(row, session_phase)
    stage = canonical_stage(row.get("category"), previous_stage=previous_stage)
    overlays = risk_overlays(row, freshness=freshness)
    entry = num(row.get("entry_position_score", row.get("entry_score")))
    action, actionable = synthesize_action(stage, overlays, freshness, entry_score=entry, has_position=has_position)
    if session_phase == "CLOSE_FREEZE":
        actionable = False
    bucket = bucket_for(mission, stage, action, freshness, actionable, has_position=has_position)

    score = num(row.get("swing_quality_score"))
    if score is None and (mission == "close_next_day" or isinstance(row.get("swing_components"), dict)):
        score = num(row.get("score"))

    intraday = num(row.get("intraday_score", row.get("intraday_momentum_score")))
    daytrade = num(row.get("daytrade_score"))
    ignition = num(row.get("ignition_score_v2"))
    ignition_exec = ignition_execution(
        row.get("ignition_stage_v2"),
        row.get("ignition_signal_action_v2") or row.get("ignition_action_v2"),
        ignition,
        entry,
        row.get("ignition_gate_cap_v2"),
    )
    components = build_component_models(row, score, intraday, daytrade)
    code = str(row.get("code") or "").strip()
    name = str(row.get("name") or code)
    industry_raw = row.get("industry")
    taxonomy = classification_for(code, name=name, industry=industry_raw)
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

    missing = []
    for field, value in [
        ("swing_quality_score", score),
        ("entry_position_score", entry),
        ("quote.price", price),
    ]:
        if value is None:
            missing.append(field)
    coverage = max(
        0,
        100
        - 20 * sum(1 for x in missing if x in {"swing_quality_score", "entry_position_score"})
        - 10 * sum(1 for x in missing if x == "quote.price"),
    )
    confidence = num(row.get("data_confidence"), coverage)
    why = list(row.get("stage_signals") or row.get("reasons") or [])
    blockers = []
    if not actionable:
        if action == "WAIT_TRIGGER":
            blockers.append("等待正式觸發")
        if action in {"WAIT_PULLBACK", "DO_NOT_CHASE"}:
            blockers.append("位置不宜追價")
        if action == "DATA_STALE":
            blockers.append("資料新鮮度不足")

    primary_group = taxonomy.get("primary_group") if taxonomy.get("core_sector_score_eligible") else None
    secondary_groups = [x.get("group") for x in taxonomy.get("secondary_groups") or [] if x.get("group")]
    theme_tags = list(taxonomy.get("theme_tags") or [])
    taxonomy_meta = {
        "version": str(taxonomy.get("taxonomy_version") or "unknown"),
        "classification_status": str(taxonomy.get("classification_status") or "UNCLASSIFIED"),
        "evidence_status": str(taxonomy.get("evidence_status") or "NO_EXTERNAL_EVIDENCE"),
        "score_source": str(taxonomy.get("score_source") or "NONE"),
        "core_sector_score_eligible": bool(taxonomy.get("core_sector_score_eligible")),
        "peer_count": int(taxonomy.get("peer_count")) if taxonomy.get("peer_count") is not None else None,
        "primary_group_confidence": num(taxonomy.get("primary_group_confidence")),
        "evidence_quality": str(taxonomy.get("evidence_quality") or "UNSPECIFIED"),
        "evidence_urls_or_refs": [str(x) for x in taxonomy.get("evidence_urls_or_refs") or []],
        "last_reviewed_at": taxonomy.get("last_reviewed_at"),
        "review_due_at": taxonomy.get("review_due_at"),
        "classification_reason": taxonomy.get("classification_reason"),
    }

    return {
        "schema_version": "2.0.0",
        "build_id": build_id,
        "dataset": "decision",
        "trade_date": trade_date,
        "session_phase": session_phase,
        "as_of": as_of,
        "known_at": now,
        "generated_at": now,
        "freshness": freshness,
        "complete": len(missing) == 0,
        "confidence": confidence,
        "source_status": {
            "sources": ["legacy-v1-adapter", f"sector-taxonomy-{taxonomy.get('taxonomy_version') or 'unknown'}"],
            "fallback": False,
            "fallback_source": None,
            "fallback_build_id": None,
            "fallback_reason": None,
            "last_success_at": now,
        },
        "decision_context_id": f"{build_id}:{mission}:{code}",
        "code": code,
        "name": name,
        "market": str(row.get("market") or "UNKNOWN"),
        "industry": row.get("industry_name") or taxonomy.get("official_industry") or industry_raw,
        "primary_group": primary_group,
        "secondary_groups": secondary_groups,
        "theme_tags": theme_tags,
        "taxonomy": taxonomy_meta,
        "quote": quote,
        "scores": {
            "swing_quality_score": score,
            "intraday_momentum_score": intraday,
            "daytrade_score": daytrade,
            "entry_position_score": entry,
            "ignition_score": ignition,
            "market_score": market_score,
        },
        "components": components,
        "ignition_model_version": row.get("ignition_model_version"),
        "ignition_raw_score": num(row.get("ignition_raw_score_v2")),
        "ignition_confidence": num(row.get("ignition_confidence_v2")),
        "ignition_stage": row.get("ignition_stage_v2"),
        "ignition_signal_action": row.get("ignition_signal_action_v2") or row.get("ignition_action_v2"),
        "ignition_action": ignition_exec["action"],
        "ignition_execution_state": ignition_exec["state"],
        "ignition_execution_ready": bool(ignition_exec["ready"]),
        "ignition_execution_note": ignition_exec["note"],
        "ignition_verdict": row.get("ignition_verdict_v2"),
        "ignition_summary": row.get("ignition_summary_v2"),
        "ignition_reasons": list(row.get("ignition_reasons_v2") or []),
        "ignition_gate_cap": num(row.get("ignition_gate_cap_v2")),
        "ignition_gate_flags": list(row.get("ignition_gate_flags_v2") or []),
        "ignition_breakout_distance_pct": num(row.get("ignition_breakout_distance_pct_v2")),
        "ignition_breakout_distance_atr": num(row.get("ignition_breakout_distance_atr_v2")),
        "ignition_candidate": bool(row.get("ignition_candidate_v2")),
        "ignition_rank": row.get("ignition_rank_v2"),
        "lifecycle_stage": stage,
        "previous_stage": previous_stage,
        "stage_changed_at": None,
        "stage_age": None,
        "stage_confidence": None,
        "action_state": action,
        "actionable": bool(actionable),
        "no_chase": action == "DO_NOT_CHASE",
        "risk_overlays": overlays,
        "opportunity_bucket": bucket,
        "opportunity_rank": None,
        "why_now": why[:3],
        "blockers": blockers[:3],
        "upgrade_conditions": ["等待下一個合法 Trigger / 結構確認"] if not actionable else [],
        "risk_flags": list(row.get("stage_risks") or []),
        "data_confidence": confidence,
        "component_coverage": coverage,
        "missing_fields": missing,
        "trade_plan_id": None,
        "case_id": None,
        "support_zone_ids": [],
        "resistance_zone_ids": [],
        "evidence_ids": [],
    }
