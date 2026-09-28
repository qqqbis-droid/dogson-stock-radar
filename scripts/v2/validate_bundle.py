#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib
from jsonschema import Draft202012Validator, FormatChecker

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "contracts" / "schemas"


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def validate(schema_file, obj):
    schema = load(SCHEMA_ROOT / schema_file)
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(obj))
    if errors:
        for error in errors[:30]:
            print(f"ERROR {schema_file} {list(error.path)}: {error.message}")
        return False
    return True


def resolve(root, url):
    raw = str(url)
    if raw.startswith("./data/"):
        return root / raw[len("./data/"):]
    return root / raw.lstrip("./")


def plan_zone_refs(plan):
    refs = []
    for key in ("entry_zone", "invalidation", "no_chase_zone"):
        obj = plan.get(key)
        if isinstance(obj, dict) and obj.get("zone_id"):
            refs.append(str(obj["zone_id"]))
    for target in plan.get("targets") or []:
        if isinstance(target, dict) and target.get("zone_id"):
            refs.append(str(target["zone_id"]))
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT / "docs" / "v2" / "data"))
    args = ap.parse_args()
    root = pathlib.Path(args.root)
    manifest = load(root / "current_manifest.json")
    ok = validate("bundle-manifest.schema.json", manifest)
    active = manifest["active_build_id"]
    if any(dataset.get("build_id") != active for dataset in manifest["datasets"].values()):
        print("ERROR mixed build_id in manifest")
        ok = False

    zone_ids = set()
    plan_ids = set()
    case_ids = set()
    delta_ids = set()
    decision_ids = set()
    for key, meta in manifest["datasets"].items():
        path = resolve(root, meta["url"])
        if not path.exists():
            continue
        obj = load(path)
        if key.startswith("zone_") and isinstance(obj, list):
            zone_ids.update(str(row.get("zone_id")) for row in obj if isinstance(row, dict) and row.get("zone_id"))
        if key.startswith("tradeplan_") and isinstance(obj, list):
            plan_ids.update(str(row.get("plan_id")) for row in obj if isinstance(row, dict) and row.get("plan_id"))
        if key.startswith("tradecase_") and isinstance(obj, list):
            case_ids.update(str(row.get("case_id")) for row in obj if isinstance(row, dict) and row.get("case_id"))
        if key.startswith("delta_") and isinstance(obj, list):
            delta_ids.update(str(row.get("delta_id")) for row in obj if isinstance(row, dict) and row.get("delta_id"))
        if key.startswith("decision_") and key.endswith("_detail") and isinstance(obj, dict):
            for row in (obj.get("items") or {}).values():
                if isinstance(row, dict) and row.get("decision_context_id"):
                    decision_ids.add(str(row["decision_context_id"]))

    for key, meta in manifest["datasets"].items():
        path = resolve(root, meta["url"])
        if not path.exists():
            print("ERROR missing dataset", key, path)
            ok = False
            continue
        obj = load(path)
        if key == "market_summary":
            ok = validate("market-state.schema.json", obj) and ok
        elif key.startswith("sector_"):
            for row in obj:
                ok = validate("sector-state.schema.json", row) and ok
        elif key.startswith("zone_"):
            for row in obj:
                ok = validate("structural-zone.schema.json", row) and ok
                if row.get("build_id") != active:
                    print("ERROR zone build_id mismatch", row.get("zone_id"))
                    ok = False
        elif key.startswith("tradeplan_"):
            for row in obj:
                ok = validate("trade-plan.schema.json", row) and ok
                if row.get("build_id") != active:
                    print("ERROR tradeplan build_id mismatch", row.get("plan_id"))
                    ok = False
                missing = [ref for ref in plan_zone_refs(row) if ref not in zone_ids]
                if missing:
                    print("ERROR unresolved tradeplan zone refs", row.get("plan_id"), missing)
                    ok = False
        elif key.startswith("tradecase_"):
            for row in obj:
                ok = validate("trade-case.schema.json", row) and ok
                if row.get("build_id") != active:
                    print("ERROR tradecase build_id mismatch", row.get("case_id"))
                    ok = False
                missing_events = [ref for ref in row.get("timeline_event_ids") or [] if ref not in delta_ids]
                if missing_events:
                    print("ERROR unresolved tradecase timeline refs", row.get("case_id"), missing_events)
                    ok = False
                missing_decisions = [ref for ref in row.get("source_decision_ids") or [] if ref not in decision_ids]
                if missing_decisions:
                    print("ERROR unresolved tradecase decision refs", row.get("case_id"), missing_decisions)
                    ok = False
        elif key.startswith("delta_"):
            for row in obj:
                ok = validate("decision-delta.schema.json", row) and ok
                if row.get("build_id") != active:
                    print("ERROR delta build_id mismatch", row.get("delta_id"))
                    ok = False
                case_id = row.get("case_id")
                if case_id and case_id not in case_ids:
                    print("ERROR unresolved delta case ref", row.get("delta_id"), case_id)
                    ok = False
                for ref_key in ("from_context_id", "to_context_id"):
                    ref = row.get(ref_key)
                    if ref and ref not in decision_ids:
                        print("ERROR unresolved delta decision ref", row.get("delta_id"), ref_key, ref)
                        ok = False
        elif key.startswith("decision_") and key.endswith("_summary"):
            for row in obj:
                ok = validate("stock-decision.schema.json", row) and ok
                case_id = row.get("case_id")
                if case_id and case_id not in case_ids:
                    print("ERROR unresolved summary case ref", row.get("code"), case_id)
                    ok = False
        elif key.startswith("decision_") and key.endswith("_detail"):
            values = list((obj.get("items") or {}).values()) if isinstance(obj, dict) else []
            for row in values:
                if isinstance(row, dict) and row.get("dataset") == "decision":
                    ok = validate("stock-decision.schema.json", row) and ok
                    if row.get("build_id") != active:
                        print("ERROR detail build_id mismatch", row.get("code"))
                        ok = False
                    refs = list(row.get("support_zone_ids") or []) + list(row.get("resistance_zone_ids") or [])
                    missing = [ref for ref in refs if ref not in zone_ids]
                    if missing:
                        print("ERROR unresolved zone refs", row.get("code"), missing)
                        ok = False
                    plan_id = row.get("trade_plan_id")
                    if plan_id and plan_id not in plan_ids:
                        print("ERROR unresolved tradeplan ref", row.get("code"), plan_id)
                        ok = False
                    case_id = row.get("case_id")
                    if case_id and case_id not in case_ids:
                        print("ERROR unresolved tradecase ref", row.get("code"), case_id)
                        ok = False
    if not ok:
        raise SystemExit(1)
    print(
        "bundle validation OK",
        active,
        "zones", len(zone_ids),
        "tradeplans", len(plan_ids),
        "tradecases", len(case_ids),
        "deltas", len(delta_ids),
    )


if __name__ == "__main__":
    main()
