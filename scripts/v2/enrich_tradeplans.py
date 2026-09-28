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


def zone_ref(zone, label):
    if not zone:
        return None
    return {
        "zone_id": zone["zone_id"],
        "label": label,
        "low": zone["low"],
        "high": zone["high"],
    }


def plan_state(decision):
    if decision.get("freshness") in {"STALE", "UNKNOWN"}:
        return "DRAFT"
    if decision.get("lifecycle_stage") == "FAILED" or decision.get("action_state") == "EXIT_PRIORITY":
        return "INVALIDATED"
    if decision.get("actionable") and decision.get("action_state") == "SMALL_TEST":
        return "TRIGGERED"
    if decision.get("actionable"):
        return "ARMED"
    if decision.get("upgrade_conditions") or decision.get("support_zone_ids"):
        return "WATCH"
    return "DRAFT"


def build_plan(decision, zone_by_id):
    support = next((zone_by_id.get(z) for z in decision.get("support_zone_ids") or [] if zone_by_id.get(z)), None)
    resistance = next((zone_by_id.get(z) for z in decision.get("resistance_zone_ids") or [] if zone_by_id.get(z)), None)
    triggers = [str(x) for x in (decision.get("upgrade_conditions") or []) if str(x).strip()]
    if decision.get("actionable") and not triggers:
        triggers = ["目前已通過 Engine 執行 Gate；實際成交仍由使用者決定"]

    invalidation = None
    if support:
        invalidation = {
            "type": "STRUCTURE_CONFIRMATION",
            "zone_id": support["zone_id"],
            "level": support["low"],
            "confirmation": "跌破結構區後，仍需配合均線／前低、量能與反抽失敗確認；瞬間刺穿不單獨視為失效。",
        }

    no_chase = None
    if resistance and (decision.get("no_chase") or decision.get("action_state") in {"DO_NOT_CHASE", "WAIT_PULLBACK"} or "OVERHEAT" in (decision.get("risk_overlays") or [])):
        no_chase = zone_ref(resistance, "壓力／不追價參考區")

    targets = []
    if resistance:
        target = zone_ref(resistance, "結構壓力參考")
        target["kind"] = "STRUCTURAL_RESISTANCE"
        targets.append(target)

    return {
        "schema_version": "2.0.0",
        "build_id": decision["build_id"],
        "dataset": "tradeplan",
        "trade_date": decision.get("trade_date"),
        "session_phase": decision.get("session_phase"),
        "as_of": decision.get("as_of"),
        "known_at": decision.get("known_at"),
        "generated_at": decision.get("generated_at"),
        "freshness": decision.get("freshness"),
        "complete": bool(support or resistance or triggers),
        "source_status": deepcopy(decision.get("source_status") or {"sources": [], "fallback": False}),
        "plan_id": f"{decision['decision_context_id']}:PLAN",
        "plan_version": "2.0-shadow-1",
        "plan_state": plan_state(decision),
        "entry_zone": zone_ref(support, "結構等待區") if support else None,
        "trigger_conditions": triggers,
        "invalidation": invalidation,
        "no_chase_zone": no_chase,
        "targets": targets,
        "reward_risk": None,
        "source_decision_id": decision["decision_context_id"],
    }


def enrich_context(output_root, manifest, context):
    build_id = manifest["active_build_id"]
    build_dir = output_root / "builds" / build_id
    detail_key = f"decision_{context}_detail"
    summary_key = f"decision_{context}_summary"
    index_key = f"decision_{context}_index"
    zone_key = f"zone_{context}"
    if detail_key not in manifest["datasets"] or zone_key not in manifest["datasets"]:
        return []

    def path_for(key):
        return build_dir / pathlib.Path(manifest["datasets"][key]["url"]).name

    detail = load_json(path_for(detail_key))
    summary = load_json(path_for(summary_key))
    index = load_json(path_for(index_key))
    zones = load_json(path_for(zone_key))
    zone_by_id = {z["zone_id"]: z for z in zones if isinstance(z, dict) and z.get("zone_id")}

    plans = []
    plan_by_code = {}
    for code, decision in (detail.get("items") or {}).items():
        plan = build_plan(decision, zone_by_id)
        decision["trade_plan_id"] = plan["plan_id"]
        plans.append(plan)
        plan_by_code[str(code)] = plan["plan_id"]

    for collection in (summary, index):
        for row in collection:
            code = str(row.get("code") or "")
            if code in plan_by_code:
                row["trade_plan_id"] = plan_by_code[code]

    for key, obj in ((detail_key, detail), (summary_key, summary), (index_key, index)):
        meta = write_json(path_for(key), obj)
        manifest["datasets"][key].update(meta)

    filename = f"tradeplan-{context}.json"
    meta = write_json(build_dir / filename, plans)
    source_meta = manifest["datasets"][detail_key]
    manifest["datasets"][f"tradeplan_{context}"] = {
        "url": f"./data/builds/{build_id}/{filename}",
        "hash": meta["hash"],
        "bytes": meta["bytes"],
        "complete": True,
        "as_of": source_meta.get("as_of"),
        "known_at": source_meta.get("known_at"),
        "build_id": build_id,
    }
    return plans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT / "docs" / "v2" / "data"))
    args = ap.parse_args()
    output_root = pathlib.Path(args.output)
    manifest_path = output_root / "current_manifest.json"
    manifest = load_json(manifest_path)
    counts = {}
    for context in ("close", "intraday", "daytrade"):
        counts[context] = len(enrich_context(output_root, manifest, context))
    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    note = "Phase 4：TradePlan 只引用已驗證結構區與 Engine 條件；reward/risk 未有可信來源時維持 null，不製造假精準。"
    if note not in warnings:
        warnings.append(note)
    write_json(manifest_path, manifest)
    print("tradeplan enrichment OK", counts)


if __name__ == "__main__":
    main()
