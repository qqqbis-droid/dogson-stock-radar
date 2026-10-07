#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT=Path(__file__).resolve().parents[2]
SCHEMAS=ROOT/"contracts"/"schemas"


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))

def resolve(root,url):
    raw=str(url)
    return root/raw[len("./data/"):] if raw.startswith("./data/") else root/raw.lstrip("./")

def validate(schema_name,obj):
    schema=load(SCHEMAS/schema_name)
    errors=list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(obj))
    if errors:
        for e in errors[:20]: print("ERROR",schema_name,list(e.path),e.message)
        return False
    return True


def validate_release_surface():
    gate=ROOT/"scripts"/"v2"/"validate_single_writer_ui.py"
    if not gate.is_file():
        raise SystemExit(f"release surface gate missing: {gate}")
    subprocess.run([sys.executable,str(gate)],cwd=ROOT,check=True)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(ROOT/"docs"/"v2"/"data")); args=ap.parse_args(); root=Path(args.root)
    manifest=load(root/"current_manifest.json"); active=manifest.get("active_build_id"); ok=True
    required={
        "market_intraday_context":("market-context.schema.json","INTRADAY"),
        "market_close_context":("market-context.schema.json","CLOSE"),
        "capital_intraday_context":("capital-context.schema.json","INTRADAY"),
        "capital_close_context":("capital-context.schema.json","CLOSE"),
    }
    loaded={}
    for key,(schema,context) in required.items():
        meta=(manifest.get("datasets") or {}).get(key)
        if not meta:
            print("ERROR missing context dataset",key); ok=False; continue
        obj=load(resolve(root,meta["url"])); loaded[key]=obj
        ok=validate(schema,obj) and ok
        if obj.get("build_id")!=active or meta.get("build_id")!=active:
            print("ERROR context build mismatch",key); ok=False
        if obj.get("context")!=context:
            print("ERROR context type mismatch",key,obj.get("context"),context); ok=False
        if str(meta.get("as_of") or "")!=str(obj.get("as_of") or ""):
            print("ERROR context as_of mismatch",key); ok=False
    mi=loaded.get("market_intraday_context") or {}; mc=loaded.get("market_close_context") or {}
    if mi.get("score_model")!="intraday_3_3_3_4_2": print("ERROR intraday market model drift"); ok=False
    if mc.get("score_model")!="close_5_4_3_3": print("ERROR close market model drift"); ok=False
    expected_intra={"taiex":3,"otc":3,"breadth":3,"funds":4,"sector":2}
    expected_close={"taiex":5,"otc":4,"breadth":3,"foreign":3}
    for obj,expected,label in ((mi,expected_intra,"intraday"),(mc,expected_close,"close")):
        comps=obj.get("components") or {}
        for key,mx in expected.items():
            if float((comps.get(key) or {}).get("max") or -1)!=float(mx):
                print("ERROR",label,"component max",key,(comps.get(key) or {}).get("max"),"!=",mx); ok=False
    ci=loaded.get("capital_intraday_context") or {}; cc=loaded.get("capital_close_context") or {}
    if any("today_amount_100m" in r for r in ci.get("rows") or []): print("ERROR intraday capital contaminated by close money fields"); ok=False
    if cc.get("rows") and not any(r.get("today_amount_100m") is not None for r in cc.get("rows") or []): print("ERROR close capital has no amount rows"); ok=False

    # Close mission uses its own completed-session clock. It may legitimately be
    # one trading day behind the live manifest during the next session, but every
    # CLOSE context must agree with decision_close_summary and must never use a
    # next-calendar-day late-fill timestamp as its as_of date.
    close_meta=(manifest.get("datasets") or {}).get("decision_close_summary") or {}
    close_date=str(close_meta.get("as_of") or "")[:10]
    for key,obj in (("market_close_context",mc),("capital_close_context",cc)):
        obj_date=str(obj.get("trade_date") or "")[:10]
        asof_date=str(obj.get("as_of") or "")[:10]
        if close_date and obj_date!=close_date:
            print("ERROR close context trade_date mismatch",key,obj_date,"!=",close_date); ok=False
        if close_date and asof_date!=close_date:
            print("ERROR close context as_of date mismatch",key,asof_date,"!=",close_date); ok=False
        if str(obj.get("freshness") or "").upper() not in {"FROZEN","FRESH"}:
            print("ERROR close context must remain frozen/usable until next completed close",key,obj.get("freshness")); ok=False
    if not ok: raise SystemExit(1)
    # Shared production release gate: every publisher already calls this data
    # validator, so bind the UI single-writer/syntax checks here to prevent a
    # stale workflow check-list from reintroducing deprecated overlay renderers.
    validate_release_surface()
    print("market/capital context validation OK",active,"scores",mi.get("market_score"),mc.get("market_score"),"rows",len(ci.get("rows") or []),len(cc.get("rows") or []),"ui_gate","PASS")

if __name__=="__main__": main()
