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
    for key, meta in manifest["datasets"].items():
        if not key.startswith("zone_"):
            continue
        path = resolve(root, meta["url"])
        if not path.exists():
            continue
        obj = load(path)
        if isinstance(obj, list):
            zone_ids.update(str(row.get("zone_id")) for row in obj if isinstance(row, dict) and row.get("zone_id"))

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
        elif key.startswith("decision_") and key.endswith("_summary"):
            for row in obj:
                ok = validate("stock-decision.schema.json", row) and ok
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
    if not ok:
        raise SystemExit(1)
    print("bundle validation OK", active, "zones", len(zone_ids))


if __name__ == "__main__":
    main()
