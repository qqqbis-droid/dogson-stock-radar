#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, time, timezone, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v2.engine import bucket_for
from scripts.v2.legacy_adapter import adapt_legacy_stock

TW = timezone(timedelta(hours=8))


def now_tw():
    return datetime.now(TW)


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def rows_of(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "items", "data", "stocks", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise ValueError("unsupported legacy payload shape")


def trade_date_of(payload, rows):
    if isinstance(payload, dict):
        for key in ("trade_date", "date"):
            value = payload.get(key)
            if isinstance(value, str) and len(value) >= 10:
                return value[:10]
    dates = [str(r.get("date") or r.get("quote_date") or r.get("market_trade_date") or "")[:10] for r in rows if isinstance(r, dict)]
    dates = [d for d in dates if len(d) == 10]
    if not dates:
        raise ValueError("legacy dataset has no trustworthy trade_date")
    return Counter(dates).most_common(1)[0][0]


def source_updated_at(payload, trade_date, default_clock="13:30"):
    if isinstance(payload, dict):
        for key in ("updated_at", "source_updated_at", "generated_at"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
    return f"{trade_date}T{default_clock}:00+08:00"


def source_as_of(row, trade_date, fallback_clock="13:30"):
    if isinstance(row, dict):
        value = row.get("quote_time") or row.get("time") or row.get("structure_time")
        if isinstance(value, str) and value:
            if "T" in value:
                return value
            if ":" in value:
                return f"{trade_date}T{value[:5]}:00+08:00"
    return f"{trade_date}T{fallback_clock}:00+08:00"


def is_same_calendar_date(trade_date):
    return trade_date == now_tw().date().isoformat()


def phase_for_intraday(trade_date):
    now = now_tw()
    if trade_date == now.date().isoformat() and time(9, 0) <= now.time() <= time(13, 35):
        return "LIVE", "LIVE"
    return "CLOSE_FREEZE", "FROZEN"


def freshness_close(trade_date):
    return "FRESH" if is_same_calendar_date(trade_date) else "STALE"


def map_market_regime(mode):
    text = str(mode or "").strip()
    if text in {"多方", "偏多", "多頭", "積極"}:
        return "SELECTIVE_RISK_ON"
    if text in {"防守", "偏空", "保守"}:
        return "DEFENSIVE"
    if text in {"空方", "風險關閉", "Risk Off", "RISK_OFF"}:
        return "RISK_OFF"
    return "NEUTRAL"


def num(v, default=None):
    try:
        x = float(v)
        return x if x == x else default
    except Exception:
        return default


def common_source(source_name, updated_at):
    return {
        "sources": [source_name, "legacy-v1-migration-adapter"],
        "fallback": False,
        "fallback_source": None,
        "fallback_build_id": None,
        "fallback_reason": None,
        "last_success_at": updated_at,
    }


def canonical_market(payload, build_id, trade_date, generated_at):
    updated = source_updated_at(payload, trade_date, "15:30")
    fresh = freshness_close(trade_date)
    complete = bool(payload.get("data_complete"))
    score = num(payload.get("market_score"))
    confidence = 90 if complete and score is not None else 55
    flags = []
    if not complete:
        flags.append("舊版市場資料未標記 complete")
    if fresh == "STALE":
        flags.append("歷史市場快照：不可作即時執行")
    return {
        "schema_version": "2.0.0",
        "build_id": build_id,
        "dataset": "market",
        "trade_date": trade_date,
        "session_phase": "POST_CLOSE",
        "as_of": f"{trade_date}T13:30:00+08:00",
        "known_at": updated,
        "generated_at": generated_at,
        "freshness": fresh,
        "complete": complete,
        "source_status": common_source("docs/data/market.json", updated),
        "market_regime": map_market_regime(payload.get("market_mode")),
        "market_score": score,
        "market_confidence": confidence,
        "risk_flags": flags,
    }


def patch_context(decision, *, row, payload, freshness, phase, known_at, generated_at, mission):
    decision["freshness"] = freshness
    decision["session_phase"] = phase
    decision["as_of"] = source_as_of(row, decision["trade_date"])
    decision["known_at"] = known_at
    decision["generated_at"] = generated_at
    decision["source_status"] = common_source(f"docs/data/{payload}", known_at)
    if freshness in {"STALE", "UNKNOWN"}:
        decision["action_state"] = "DATA_STALE"
        decision["actionable"] = False
        decision["risk_overlays"] = list(dict.fromkeys(decision.get("risk_overlays", []) + ["DATA_QUALITY_RISK"]))
        decision["blockers"] = list(dict.fromkeys(decision.get("blockers", []) + ["資料不是目前可執行快照"]))[:3]
    if phase == "CLOSE_FREEZE":
        decision["actionable"] = False
    decision["opportunity_bucket"] = bucket_for(
        mission,
        decision["lifecycle_stage"],
        decision["action_state"],
        freshness,
        decision["actionable"],
        False,
    )
    return decision


def adapt_close_rows(payload, build_id, market_score, generated_at):
    rows = rows_of(payload)
    trade_date = trade_date_of(payload, rows)
    known_at = source_updated_at(payload, trade_date, "15:30")
    freshness = freshness_close(trade_date)
    out = []
    for row in rows:
        if not row.get("code"):
            continue
        d = adapt_legacy_stock(row, build_id=build_id, trade_date=trade_date, session_phase="POST_CLOSE", mission="close_next_day", market_score=market_score)
        out.append(patch_context(d, row=row, payload="close.json", freshness=freshness, phase="POST_CLOSE", known_at=known_at, generated_at=generated_at, mission="close_next_day"))
    return out, trade_date



def intraday_truth_reason(row, trade_date):
    """Return a blocker when the live price/structure chain is not trustworthy."""
    if row.get("quote_price_validated") is False:
        return str(row.get("live_truth_blocker") or "即時價格與5分結構尚未同時驗證")
    structure_date = str(row.get("structure_date") or row.get("date") or "")[:10]
    if structure_date and structure_date != trade_date:
        return f"5分結構日期 {structure_date} ≠ 報價日 {trade_date}"
    px = num(row.get("close"))
    bid = num(row.get("quote_bid1"))
    ask = num(row.get("quote_ask1"))
    book = (bid + ask) / 2.0 if bid is not None and ask is not None else (bid if bid is not None else ask)
    has_trade = bool(row.get("quote_has_trade")) and num(row.get("quote_close")) is not None
    if not has_trade and px is not None and book not in (None, 0):
        gap = abs(px / book - 1.0) * 100.0
        if gap > 2.0:
            return f"結構價與即時五檔差距 {gap:.1f}%；本輪未驗證到真實成交價"
    return None


def apply_intraday_truth_gate(decision, row, *, mission):
    reason = intraday_truth_reason(row, decision["trade_date"])
    if not reason:
        return decision
    decision["lifecycle_stage"] = "OBSERVE"
    decision["action_state"] = "DATA_STALE"
    decision["actionable"] = False
    decision["opportunity_bucket"] = "STALE" if mission == "daytrade_execution" else "RESEARCH_ONLY"
    decision["risk_overlays"] = list(dict.fromkeys(list(decision.get("risk_overlays") or []) + ["DATA_QUALITY_RISK"]))
    decision["blockers"] = list(dict.fromkeys([reason, "盤中分數與支撐壓力暫停，等同交易日價格／結構重新驗證"] + list(decision.get("blockers") or [])))[:3]
    decision["why_now"] = ["即時五檔已更新，但成交價／5分結構尚未同時驗證"]
    scores = decision.setdefault("scores", {})
    scores["intraday_momentum_score"] = None
    if mission == "daytrade_execution":
        scores["daytrade_score"] = None
    components = decision.setdefault("components", {})
    components["intraday"] = None
    if mission == "daytrade_execution":
        components["daytrade"] = None
    quote = decision.setdefault("quote", {})
    verified_trade = num(row.get("quote_close")) if bool(row.get("quote_has_trade")) else None
    quote["price"] = verified_trade
    decision["data_confidence"] = min(num(decision.get("data_confidence"), 0) or 0, 40)
    decision["component_coverage"] = min(num(decision.get("component_coverage"), 0) or 0, 40)
    decision["complete"] = False
    missing = list(decision.get("missing_fields") or [])
    for field in ("verified_live_price", "fresh_5m_structure"):
        if field not in missing:
            missing.append(field)
    decision["missing_fields"] = missing
    return decision

def adapt_intraday_rows(payload, build_id, market_score, generated_at):
    rows = rows_of(payload)
    trade_date = trade_date_of(payload, rows)
    phase, freshness = phase_for_intraday(trade_date)
    known_at = source_updated_at(payload, trade_date)
    out = []
    for row in rows:
        if not row.get("code"):
            continue
        d = adapt_legacy_stock(row, build_id=build_id, trade_date=trade_date, session_phase=phase, mission="intraday_swing", market_score=market_score)
        d = patch_context(d, row=row, payload="intraday.json", freshness=freshness, phase=phase, known_at=known_at, generated_at=generated_at, mission="intraday_swing")
        d = apply_intraday_truth_gate(d, row, mission="intraday_swing")
        out.append(d)
    return out, trade_date


def adapt_daytrade_rows(payload, build_id, market_score, generated_at):
    rows = rows_of(payload)
    trade_date = trade_date_of(payload, rows)
    phase, freshness = phase_for_intraday(trade_date)
    known_at = source_updated_at(payload, trade_date)
    out = []
    for row in rows:
        if not row.get("code"):
            continue
        base = dict(row)
        base["category"] = row.get("source_category") or "觀察"
        d = adapt_legacy_stock(base, build_id=build_id, trade_date=trade_date, session_phase=phase, mission="daytrade_execution", market_score=market_score)
        d["scores"]["daytrade_score"] = num(row.get("daytrade_score"))
        state = str(row.get("daytrade_state") or "觀察")
        if freshness != "LIVE":
            action, actionable = "DATA_STALE", False
        elif state == "可執行":
            action, actionable = "SMALL_TEST", True
        elif state == "等回踩":
            action, actionable = "WAIT_TRIGGER", False
        elif state == "過熱不追":
            action, actionable = "DO_NOT_CHASE", False
            if "OVERHEAT" not in d["risk_overlays"]:
                d["risk_overlays"].append("OVERHEAT")
        else:
            action, actionable = "WATCH", False
        d["action_state"] = action
        d["actionable"] = actionable
        d["why_now"] = list(row.get("daytrade_reasons") or row.get("stage_signals") or [])[:3]
        d["risk_flags"] = list(row.get("daytrade_risks") or [])[:5]
        d["blockers"] = [] if actionable else [str(row.get("daytrade_headline") or "尚未形成可執行條件")]
        d = patch_context(d, row=row, payload="daytrade.json", freshness=freshness, phase=phase, known_at=known_at, generated_at=generated_at, mission="daytrade_execution")
        d["opportunity_bucket"] = "ACTIONABLE_NOW" if actionable else ("WAIT_TRIGGER" if action == "WAIT_TRIGGER" and freshness == "LIVE" else ("STALE" if freshness != "LIVE" else "NO_TRADE"))
        d = apply_intraday_truth_gate(d, row, mission="daytrade_execution")
        out.append(d)
    return out, trade_date


def group_name(row):
    return str(row.get("sector_group") or row.get("industry_name") or row.get("industry") or "未分類").strip() or "未分類"


def sector_states(rows, *, build_id, trade_date, phase, freshness, generated_at, source_name):
    groups = defaultdict(list)
    for row in rows:
        if isinstance(row, dict) and row.get("code"):
            groups[group_name(row)].append(row)
    output = []
    for idx, (name, members) in enumerate(groups.items(), 1):
        adv = sum(1 for r in members if (num(r.get("day_change"), 0) or 0) > 0)
        leaders = sorted(members, key=lambda r: num(r.get("score"), -1), reverse=True)[:5]
        close_vals = [num(r.get("sector_score")) for r in members]
        close_vals = [x for x in close_vals if x is not None]
        intra_vals = [num((r.get("intraday_components") or {}).get("sector")) for r in members]
        intra_vals = [x for x in intra_vals if x is not None]
        score_close = min(15, max(0, sum(close_vals) / len(close_vals))) if close_vals else None
        score_intra = min(20, max(0, sum(intra_vals) / len(intra_vals))) if intra_vals else None
        known_at = max([source_updated_at({"updated_at": r.get("updated_at")}, trade_date) for r in members] + [f"{trade_date}T13:30:00+08:00"])
        output.append({
            "schema_version": "2.0.0", "build_id": build_id, "dataset": "sector", "trade_date": trade_date,
            "session_phase": phase, "as_of": f"{trade_date}T13:30:00+08:00", "known_at": known_at,
            "generated_at": generated_at, "freshness": freshness, "complete": bool(members),
            "source_status": common_source(source_name, known_at), "sector_id": f"LEGACY_{idx:04d}", "primary_group": name,
            "industry_parent": None, "supply_chain_links": [], "classification_confidence": 60,
            "taxonomy_version": "legacy-adapter-1", "reviewed_at": None, "member_count": len(members), "advancers": adv,
            "strong_count": sum(1 for r in members if str(r.get("category") or "") in {"剛啟動", "趨勢持有", "回踩承接"}),
            "breadth_pct": round(adv / len(members) * 100, 1) if members else None, "turnover_share": None,
            "turnover_acceleration": None, "heat_score": score_intra, "heat_delta": None, "momentum_regime": None,
            "leaders": [str(r.get("code")) for r in leaders], "leader_count": len(leaders), "persistence": None,
            "continuation_ratio": None, "sector_score_close": round(score_close, 1) if score_close is not None else None,
            "sector_score_intraday": round(score_intra, 1) if score_intra is not None else None,
        })
    output.sort(key=lambda s: ((s["sector_score_intraday"] if phase != "POST_CLOSE" else s["sector_score_close"]) is not None, (s["sector_score_intraday"] if phase != "POST_CLOSE" else s["sector_score_close"]) or -1), reverse=True)
    return output


BUCKET_ORDER = {
    "close_next_day": {"NEXT_DAY_READY": 0, "BREAKOUT_WATCH": 1, "PULLBACK_WATCH": 2, "TREND_QUALITY": 3, "RESEARCH": 4, "RISK": 5},
    "intraday_swing": {"TRIGGER_READY": 0, "WAIT_TRIGGER": 1, "TREND_MONITOR": 2, "WAIT_PULLBACK": 3, "RESEARCH_ONLY": 4, "RISK": 5},
    "daytrade_execution": {"ACTIONABLE_NOW": 0, "WAIT_TRIGGER": 1, "NO_TRADE": 2, "STALE": 3},
}


def rank_rows(rows, mission):
    order = BUCKET_ORDER[mission]

    def score(d, key):
        value = (d.get("scores") or {}).get(key)
        return value if value is not None else -1

    def sort_key(d):
        bucket = order.get(d.get("opportunity_bucket"), 99)
        confidence = d.get("data_confidence") or 0
        if mission == "close_next_day":
            return (
                bucket,
                -score(d, "swing_quality_score"),
                -score(d, "entry_position_score"),
                -confidence,
                d["code"],
            )
        if mission == "intraday_swing":
            return (bucket, -score(d, "intraday_momentum_score"), -confidence, d["code"])
        return (bucket, -score(d, "daytrade_score"), -confidence, d["code"])

    rows.sort(key=sort_key)
    for i, d in enumerate(rows, 1):
        d["opportunity_rank"] = i
    return rows


def summary_rows(rows, limit=15):
    return rows[:limit]


def lightweight_index(rows):
    return [{
        "code": d["code"], "name": d["name"], "market": d["market"], "primary_group": d.get("primary_group"),
        "decision_context_id": d["decision_context_id"], "build_id": d["build_id"], "freshness": d["freshness"],
        "lifecycle_stage": d["lifecycle_stage"], "action_state": d["action_state"], "actionable": d["actionable"],
        "opportunity_bucket": d.get("opportunity_bucket"), "opportunity_rank": d.get("opportunity_rank"),
        "scores": d["scores"], "why_now": d.get("why_now", []), "blockers": d.get("blockers", []),
        "upgrade_conditions": d.get("upgrade_conditions", []), "risk_flags": d.get("risk_flags", []),
        "ignition_model_version": d.get("ignition_model_version"), "ignition_raw_score": d.get("ignition_raw_score"),
        "ignition_confidence": d.get("ignition_confidence"), "ignition_stage": d.get("ignition_stage"),
        "ignition_action": d.get("ignition_action"), "ignition_verdict": d.get("ignition_verdict"),
        "ignition_summary": d.get("ignition_summary"), "ignition_reasons": d.get("ignition_reasons", []),
        "ignition_gate_cap": d.get("ignition_gate_cap"), "ignition_gate_flags": d.get("ignition_gate_flags", []),
        "ignition_breakout_distance_pct": d.get("ignition_breakout_distance_pct"),
        "ignition_breakout_distance_atr": d.get("ignition_breakout_distance_atr"),
        "ignition_candidate": d.get("ignition_candidate"), "ignition_rank": d.get("ignition_rank"),
    } for d in rows]


def detail_map(rows):
    return {"schema_version": "2.0.0", "build_id": rows[0]["build_id"] if rows else "", "items": {d["code"]: d for d in rows}}


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    return {"hash": "sha256:" + hashlib.sha256(text.encode()).hexdigest(), "bytes": len(text.encode())}


def build(legacy_root, output_root):
    close_payload = load_json(legacy_root / "close.json")
    intraday_payload = load_json(legacy_root / "intraday.json")
    daytrade_payload = load_json(legacy_root / "daytrade.json")
    market_payload = load_json(legacy_root / "market.json")
    close_rows = rows_of(close_payload); intraday_rows = rows_of(intraday_payload); daytrade_rows = rows_of(daytrade_payload)
    close_date = trade_date_of(close_payload, close_rows)
    intraday_date = trade_date_of(intraday_payload, intraday_rows)
    daytrade_date = trade_date_of(daytrade_payload, daytrade_rows)
    source_dates = sorted({close_date, intraday_date, daytrade_date})
    canonical_date = max(source_dates)
    generated_at = now_tw().isoformat(timespec="seconds")
    fingerprint = hashlib.sha256((canonical_date + source_updated_at(close_payload, close_date) + source_updated_at(intraday_payload, intraday_date) + source_updated_at(daytrade_payload, daytrade_date)).encode()).hexdigest()[:10]
    build_id = f"cb2-legacy-{canonical_date.replace('-', '')}-{fingerprint}"
    market = canonical_market(market_payload, build_id, close_date, generated_at)
    close_decisions, _ = adapt_close_rows(close_payload, build_id, market.get("market_score"), generated_at)
    intraday_decisions, _ = adapt_intraday_rows(intraday_payload, build_id, market.get("market_score"), generated_at)
    daytrade_decisions, _ = adapt_daytrade_rows(daytrade_payload, build_id, market.get("market_score"), generated_at)
    rank_rows(close_decisions, "close_next_day"); rank_rows(intraday_decisions, "intraday_swing"); rank_rows(daytrade_decisions, "daytrade_execution")
    intraday_phase, intraday_fresh = phase_for_intraday(intraday_date)
    close_sectors = sector_states(close_rows, build_id=build_id, trade_date=close_date, phase="POST_CLOSE", freshness=freshness_close(close_date), generated_at=generated_at, source_name="docs/data/close.json")
    intraday_sectors = sector_states(intraday_rows, build_id=build_id, trade_date=intraday_date, phase=intraday_phase, freshness=intraday_fresh, generated_at=generated_at, source_name="docs/data/intraday.json")
    if output_root.exists():
        shutil.rmtree(output_root)
    build_dir = output_root / "builds" / build_id
    payloads = {
        "market_summary": ("market-summary.json", market),
        "sector_close": ("sector-close.json", close_sectors),
        "sector_intraday": ("sector-intraday.json", intraday_sectors),
        "decision_close_summary": ("decision-close-summary.json", summary_rows(close_decisions)),
        "decision_close_index": ("decision-close-index.json", lightweight_index(close_decisions)),
        "decision_close_detail": ("decision-close-detail.json", detail_map(close_decisions)),
        "decision_intraday_summary": ("decision-intraday-summary.json", summary_rows(intraday_decisions)),
        "decision_intraday_index": ("decision-intraday-index.json", lightweight_index(intraday_decisions)),
        "decision_intraday_detail": ("decision-intraday-detail.json", detail_map(intraday_decisions)),
        "decision_daytrade_summary": ("decision-daytrade-summary.json", summary_rows(daytrade_decisions)),
        "decision_daytrade_index": ("decision-daytrade-index.json", lightweight_index(daytrade_decisions)),
        "decision_daytrade_detail": ("decision-daytrade-detail.json", detail_map(daytrade_decisions)),
        "portfolio_summary": ("portfolio-summary.json", []),
    }
    warnings = ["Phase 4 Migration Adapter：沿用 v1.x 公開市場資料，未升級的預測門檻仍為 Shadow。", "公開 Preview 不包含私人庫存資料。"]
    if len(source_dates) > 1:
        warnings.append("來源交易日不完全一致；各物件保留自己的 trade_date，禁止跨日合成可執行訊號。")
    datasets = {}
    for key, (filename, obj) in payloads.items():
        meta = write_json(build_dir / filename, obj)
        if key.startswith("decision_close") or key == "sector_close" or key == "market_summary":
            td, phase, fresh = close_date, "POST_CLOSE", freshness_close(close_date)
        else:
            td, (phase, fresh) = intraday_date, phase_for_intraday(intraday_date)
        datasets[key] = {"url": f"./data/builds/{build_id}/{filename}", "hash": meta["hash"], "bytes": meta["bytes"], "complete": True, "as_of": f"{td}T13:30:00+08:00", "known_at": generated_at, "build_id": build_id}
    health_obj = {"build_id": build_id, "validation_passed": True, "warnings": warnings, "errors": [], "source_dates": source_dates, "counts": {"close": len(close_decisions), "intraday": len(intraday_decisions), "daytrade": len(daytrade_decisions)}}
    meta = write_json(build_dir / "health.json", health_obj)
    datasets["health"] = {"url": f"./data/builds/{build_id}/health.json", "hash": meta["hash"], "bytes": meta["bytes"], "complete": True, "as_of": generated_at, "known_at": generated_at, "build_id": build_id}
    manifest = {"schema_version": "2.0.0", "app_contract_version": "2.0.0", "active_build_id": build_id, "previous_good_build_id": None, "trade_date": canonical_date, "session_phase": "POST_CLOSE", "generated_at": generated_at, "datasets": datasets, "health": {"validation_passed": True, "warnings": warnings, "errors": [], "fallback_reason": None}}
    write_json(output_root / "current_manifest.json", manifest)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-root", default=str(ROOT / "docs" / "data"))
    ap.add_argument("--output", default=str(ROOT / "docs" / "v2" / "data"))
    args = ap.parse_args()
    manifest = build(pathlib.Path(args.legacy_root), pathlib.Path(args.output))
    print("built", manifest["active_build_id"], "from", manifest["trade_date"])


if __name__ == "__main__":
    main()
