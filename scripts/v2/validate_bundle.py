#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib
from jsonschema import Draft202012Validator,FormatChecker
ROOT=pathlib.Path(__file__).resolve().parents[2]; SCHEMA_ROOT=ROOT/"contracts"/"schemas"
def load(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def validate(schema_file,obj):
    schema=load(SCHEMA_ROOT/schema_file); errors=list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(obj))
    if errors:
        for e in errors[:20]: print(f"ERROR {list(e.path)}: {e.message}")
        return False
    return True
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(ROOT/"docs"/"v2"/"data")); args=ap.parse_args(); root=pathlib.Path(args.root); manifest=load(root/"current_manifest.json"); ok=validate("bundle-manifest.schema.json",manifest); active=manifest["active_build_id"]
    if any(d.get("build_id")!=active for d in manifest["datasets"].values()): print("ERROR mixed build_id in manifest"); ok=False
    build=root/"builds"/active; ok=validate("market-state.schema.json",load(build/"market-summary.json")) and ok
    for row in load(build/"sector-summary.json"): ok=validate("sector-state.schema.json",row) and ok
    for row in load(build/"decision-summary.json"): ok=validate("stock-decision.schema.json",row) and ok
    if not ok: raise SystemExit(1)
    print("bundle validation OK",active)
if __name__=="__main__": main()
