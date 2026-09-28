#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from copy import deepcopy

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def write_json(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    return {
        "hash": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "bytes": len(text.encode("utf-8")),
    }


def latest_text(*values):
    values = [str(v) for v in values if v]
    return max(values) if values else None


def worse_freshness(*values):
    order = {"LIVE": 0, "FRESH": 1, "FROZEN": 2, "STALE": 3, "UNKNOWN": 4}
    cleaned = [v for v in values if v in order]
    return max(cleaned, key=lambda v: order[v]) if cleaned else "UNKNOWN"


def merged_source_status(*decisions):
    sources = []
    fallback = False
    fallback_source = None
    fallback_build_id = None
    fallback_reason = None
    last_success_at = None
    for decision in decisions:
        if not decision:
            continue
        status = decision.get("source_status") or {}
        for source in status.get("sources") or []:
            if source not in sources:
                sources.append(source)
        fallback = fallback or bool(status.get("fallback"))
        fallback_source = fallback_source or status.get("fallback_source")
        fallback_build_id = fallback_build_id or status.get("fallback_build_id")
        fallback_reason = fallback_reason or status.get("fallback_reason")
        last_success_at = latest_text(last_success_at, status.get("last_success_at"))
    if "shadow-tradecase-builder" not in sources:
        sources.append("shadow-tradecase-builder")
    return {
        "sources": sources,
        "fallback": fallback,
        "fallback_source": fallback_source,
        "fallback_build_id": fallback_build_id,
        "fallback_reason": fallback_reason,
        "last_success_at": last_success_at,
    }


def case_id(trade_date, mission, code):
    date_key = str(trade_date or "UNKNOWN").replace("-", "")
    return f"TC:{date_key}:{mission}:{code}"


def stage_event(view, decision):
    if not decision:
        return None
    return {
        "view": view,
        "decision_context_id": decision.get("decision_context_id"),
        "lifecycle_stage": decision.get("lifecycle_stage"),
        "as_of": decision.get("as_of"),
    }


def priority_event(view, decision):
    if not decision:
        return None
    return {
        "view": view,
        "action_state": decision.get("action_state"),
        "opportunity_bucket": decision.get("opportunity_bucket"),
        "opportunity_rank": decision.get("opportunity_rank"),
        "actionable": bool(decision.get("actionable")),
        "as_of": decision.get("as_of"),
    }


def sector_event(view, decision):
    if not decision:
        return None
    return {
        "view": view,
        "primary_group": decision.get("primary_group"),
        "as_of": decision.get("as_of"),
    }


def get_nested(obj, path):
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def build_delta(before, after, cid):
    if not before or not after:
        return None
    fields = [
        "lifecycle_stage",
        "action_state",
        "actionable",
        "no_chase",
        "risk_overlays",
        "scores.entry_position_score",
        "primary_group",
        "blockers",
        "upgrade_conditions",
    ]
    changes = []
    reasons = []
    for field in fields:
        old = get_nested(before, field)
        new = get_nested(after, field)
        if old == new:
            continue
        changes.append({"field": field, "from": old, "to": new})
        if field == "lifecycle_stage":
            reasons.append(f"生命週期：{old} → {new}")
        elif field == "action_state":
            reasons.append(f"行動狀態：{old} → {new}")
        elif field == "actionable":
            reasons.append(f"可執行 Gate：{old} → {new}")
        elif field == "no_chase":
            reasons.append(f"不追價標記：{old} → {new}")
        elif field == "risk_overlays":
            reasons.append("風險 Overlay 有變化")
        elif field == "scores.entry_position_score":
            reasons.append(f"進場位置分：{old} → {new}")
        elif field == "primary_group":
            reasons.append(f"主要族群：{old or '—'} → {new or '—'}")
        elif field == "blockers":
            reasons.append("阻擋條件有變化")
        elif field == "upgrade_conditions":
            reasons.append("升級條件有變化")
    if not changes:
        return None
    return {
        "schema_version": "2.0.0",
        "build_id": after["build_id"],
        "dataset": "delta",
        "trade_date": after.get("trade_date"),
        "session_phase": "POST_CLOSE",
        "as_of": after.get("as_of"),
        "known_at": latest_text(before.get("known_at"), after.get("known_at")),
        "generated_at": after.get("generated_at"),
        "freshness": worse_freshness(before.get("freshness"), after.get("freshness")),
        "complete": True,
        "source_status": merged_source_status(before, after),
        "delta_id": f"{cid}:INTRADAY_TO_CLOSE",
        "case_id": cid,
        "code": str(after.get("code") or before.get("code") or ""),
        "from_context_id": before.get("decision_context_id"),
        "to_context_id": after.get("decision_context_id"),
        "changed_fields": [x["field"] for x in changes],
        "changes": changes,
        "reason": reasons,
    }


def case_status(decision, plan):
    if not decision:
        return "SHADOW_REVIEW"
    if decision.get("lifecycle_stage") == "FAILED" or (plan and plan.get("plan_state") == "INVALIDATED"):
        return "INVALIDATED"
    if decision.get("freshness") in {"STALE", "UNKNOWN"}:
        return "SHADOW_REVIEW"
    if decision.get("actionable"):
        return "ARMED"
    return "TRACKING"


def build_case(*, mission, origin_view, decisions, latest, plan, delta=None):
    cid = case_id(latest.get("trade_date"), mission, latest["code"])
    core = [str(x) for x in (latest.get("why_now") or []) if str(x).strip()]
    stage_history = [event for event in (stage_event(view, decision) for view, decision in decisions) if event]
    priority_history = [event for event in (priority_event(view, decision) for view, decision in decisions) if event]
    sector_history = [event for event in (sector_event(view, decision) for view, decision in decisions) if event]
    delta_ids = [delta["delta_id"]] if delta else []
    invalidated = latest.get("lifecycle_stage") == "FAILED" or (plan and plan.get("plan_state") == "INVALIDATED")
    return {
        "schema_version": "2.0.0",
        "build_id": latest["build_id"],
        "dataset": "tradecase",
        "trade_date": latest.get("trade_date"),
        "session_phase": "POST_CLOSE",
        "as_of": latest.get("as_of"),
        "known_at": latest_text(*(d.get("known_at") for _, d in decisions if d)),
        "generated_at": latest.get("generated_at"),
        "freshness": worse_freshness(*(d.get("freshness") for _, d in decisions if d)),
        "complete": bool(core or plan),
        "source_status": merged_source_status(*(d for _, d in decisions if d)),
        "case_id": cid,
        "thesis_id": f"{cid}:THESIS-1",
        "code": str(latest["code"]),
        "origin_trade_date": latest.get("trade_date"),
        "origin_view": origin_view,
        "origin_build_id": latest["build_id"],
        "core_thesis": core,
        "bonus_conditions": [],
        "trigger": {"conditions": deepcopy(plan.get("trigger_conditions") or []), "source_plan_id": plan.get("plan_id")} if plan else None,
        "entry_zone": deepcopy(plan.get("entry_zone")) if plan else None,
        "no_chase": deepcopy(plan.get("no_chase_zone")) if plan else None,
        "invalidation": deepcopy(plan.get("invalidation")) if plan else None,
        "stage_history": stage_history,
        "priority_history": priority_history,
        "sector_history": sector_history,
        "confirmation_history": [{"phase": "POST_CLOSE", "status": "PENDING", "reason": "Shadow：正式收盤確認模型尚未升格為 Active。"}],
        "timeline_event_ids": delta_ids,
        "source_decision_ids": [d.get("decision_context_id") for _, d in decisions if d and d.get("decision_context_id")],
        "actual_executions": [],
        "case_status": case_status(latest, plan),
        "close_confirmation": "PENDING",
        "carry_state": "ARCHIVE" if invalidated else "REVIEW",
        "close_reason": "Shadow：目前只建立同日生命線；跨交易日 Carry 必須等待下一交易日資料驗證，不從單日快照推測。",
        "archived_at": latest.get("as_of") if invalidated else None,
    }


def update_decision_case_id(collection, case_by_code):
    if isinstance(collection, list):
        rows = collection
    elif isinstance(collection, dict):
        rows = list((collection.get("items") or {}).values())
    else:
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cid = case_by_code.get(str(row.get("code") or ""))
        if cid:
            row["case_id"] = cid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT / "docs" / "v2" / "data"))
    args = ap.parse_args()
    output_root = pathlib.Path(args.output)
    manifest_path = output_root / "current_manifest.json"
    manifest = load_json(manifest_path)
    build_id = manifest["active_build_id"]
    build_dir = output_root / "builds" / build_id

    def path_for(key):
        return build_dir / pathlib.Path(manifest["datasets"][key]["url"]).name

    details = {}
    summaries = {}
    indexes = {}
    plans = {}
    for context in ("intraday", "close", "daytrade"):
        dkey = f"decision_{context}_detail"
        skey = f"decision_{context}_summary"
        ikey = f"decision_{context}_index"
        pkey = f"tradeplan_{context}"
        details[context] = load_json(path_for(dkey))
        summaries[context] = load_json(path_for(skey))
        indexes[context] = load_json(path_for(ikey))
        plans[context] = {p["source_decision_id"]: p for p in load_json(path_for(pkey))}

    intraday_by_code = details["intraday"].get("items") or {}
    close_by_code = details["close"].get("items") or {}
    daytrade_by_code = details["daytrade"].get("items") or {}

    swing_cases = []
    swing_case_by_code = {}
    deltas = []
    for code in sorted(set(intraday_by_code) | set(close_by_code)):
        intraday = intraday_by_code.get(code)
        close = close_by_code.get(code)
        latest = close or intraday
        if not latest:
            continue
        cid = case_id(latest.get("trade_date"), "SWING", code)
        delta = build_delta(intraday, close, cid) if intraday and close else None
        if delta:
            deltas.append(delta)
        plan = plans["close"].get(close.get("decision_context_id")) if close else None
        if not plan and intraday:
            plan = plans["intraday"].get(intraday.get("decision_context_id"))
        case = build_case(
            mission="SWING",
            origin_view="intraday" if intraday else "close",
            decisions=[("intraday", intraday), ("close", close)],
            latest=latest,
            plan=plan,
            delta=delta,
        )
        swing_cases.append(case)
        swing_case_by_code[str(code)] = case["case_id"]

    daytrade_cases = []
    daytrade_case_by_code = {}
    for code, decision in sorted(daytrade_by_code.items()):
        plan = plans["daytrade"].get(decision.get("decision_context_id"))
        case = build_case(
            mission="DAYTRADE",
            origin_view="daytrade",
            decisions=[("daytrade", decision)],
            latest=decision,
            plan=plan,
            delta=None,
        )
        daytrade_cases.append(case)
        daytrade_case_by_code[str(code)] = case["case_id"]

    for context in ("intraday", "close"):
        for obj in (details[context], summaries[context], indexes[context]):
            update_decision_case_id(obj, swing_case_by_code)
    for obj in (details["daytrade"], summaries["daytrade"], indexes["daytrade"]):
        update_decision_case_id(obj, daytrade_case_by_code)

    for context in ("intraday", "close", "daytrade"):
        for prefix, obj in (("detail", details[context]), ("summary", summaries[context]), ("index", indexes[context])):
            key = f"decision_{context}_{prefix}"
            meta = write_json(path_for(key), obj)
            manifest["datasets"][key].update(meta)

    source_meta = manifest["datasets"]["decision_close_detail"]
    outputs = {
        "tradecase_swing": ("tradecase-swing.json", swing_cases),
        "tradecase_daytrade": ("tradecase-daytrade.json", daytrade_cases),
        "delta_intraday_close": ("delta-intraday-close.json", deltas),
    }
    for key, (filename, rows) in outputs.items():
        meta = write_json(build_dir / filename, rows)
        manifest["datasets"][key] = {
            "url": f"./data/builds/{build_id}/{filename}",
            "hash": meta["hash"],
            "bytes": meta["bytes"],
            "complete": True,
            "as_of": source_meta.get("as_of"),
            "known_at": source_meta.get("known_at"),
            "build_id": build_id,
        }

    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    note = "Phase 4/5 Shadow：TradeCase 已建立同日盤中→盤後生命線；跨日 Carry 僅在下一交易日資料實際存在後才驗證，不由單日快照推測。"
    if note not in warnings:
        warnings.append(note)
    write_json(manifest_path, manifest)
    print("tradecase enrichment OK", {"swing": len(swing_cases), "daytrade": len(daytrade_cases), "deltas": len(deltas)})


if __name__ == "__main__":
    main()
