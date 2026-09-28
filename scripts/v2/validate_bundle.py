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
        elif key.startswith("decision_") and (key.endswith("_summary") or key.endswith("_detail")):
            rows = obj if isinstance(obj, list) else list((obj.get("items") or {}).values())
            for row in rows:
                ok = validate("stock-decision.schema.json", row) and ok
    if not ok:
        raise SystemExit(1)
    print("bundle validation OK", active)


if __name__ == "__main__":
    main()
