#!/usr/bin/env python3
"""Pin a verified completed-close mission across the next intraday sessions.

A new intraday bundle may carry a newer *live* trade_date while CLOSE must
retain the last validated completed-session scores, quote, zones and verdict.
This never borrows scores from another trading day and never marks an
incomplete input as complete. Refresh the pin only after a newer complete close
has been independently validated.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

CLOSE_KEYS = (
    "market_summary", "sector_close", "decision_close_summary",
    "decision_close_index", "decision_close_detail", "zone_close",
    "stock_detail_close", "market_close_context", "capital_close_context",
)

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return {"hash": "sha256:" + hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

def resolve(root, metadata):
    url = str(metadata.get("url") or "")
    if url.startswith("./data/"):
        url = url[len("./data/"):]
    else:
        url = url.lstrip("./")
    if not url:
        raise ValueError("missing dataset location")
    return Path(root)/url

def date(x):
    return str(x or "")[:10]

def retag(obj, before, after):
    if isinstance(obj, str):
        return obj.replace(before, after)
    if isinstance(obj, list):
        return [retag(x, before, after) for x in obj]
    if isinstance(obj, dict):
        return {k: retag(v, before, after) for k,v in obj.items()}
    return obj

def verify(source, day, source_build):
    required = ("market_close_context", "capital_close_context", "decision_close_summary", "decision_close_detail")
    for key in required:
        node = source[key]
        if key == "decision_close_summary":
            if not isinstance(node, list) or len(node) < 10:
                raise RuntimeError("frozen close summary missing or too small")
            if any(date(row.get("trade_date") or row.get("as_of")) != day for row in node):
                raise RuntimeError("frozen close summary spans multiple sessions")
            if any(row.get("action_state") == "DATA_STALE" or row.get("freshness") not in ("FRESH","FROZEN") for row in node):
                raise RuntimeError("cannot pin stale close conclusions")
        elif key == "decision_close_detail":
            if not isinstance(node.get("items"), dict) or not node["items"]:
                raise RuntimeError("frozen close detail missing")
        elif node.get("complete") is not True or date(node.get("trade_date")) != day:
            raise RuntimeError(f"frozen {key} not a complete {day} close")
        if isinstance(node, dict) and node.get("build_id") != source_build:
            raise RuntimeError(f"frozen {key} build mismatch")
    if any(not isinstance(source.get(k), (list, dict)) for k in CLOSE_KEYS):
        raise RuntimeError("frozen snapshot lacks a required close dataset")

def frozen_snapshot(folder):
    manifest_path = Path(folder)/"manifest.json"
    if not manifest_path.is_file():
        return None
    fm = load(manifest_path)
    day = date(fm.get("trade_date"))
    build = str(fm.get("source_build_id") or "")
    if not day or not build:
        raise RuntimeError("invalid frozen close manifest")
    source = {}
    for key in CLOSE_KEYS:
        path = Path(folder)/(key+".json")
        if not path.is_file():
            raise RuntimeError(f"missing pinned {key}")
        raw = path.read_bytes()
        recorded = str((fm.get("source_hashes") or {}).get(key) or "")
        if recorded and "sha256:"+hashlib.sha256(raw).hexdigest() != recorded:
            raise RuntimeError(f"immutable frozen hash mismatch: {key}")
        source[key] = json.loads(raw)
    verify(source,day,build)
    return fm,source

def hydrate(root, folder):
    root=Path(root)
    mp=root/"current_manifest.json"
    manifest=load(mp)
    ds=manifest.get("datasets") or {}
    current_day=date((ds.get("decision_close_summary") or {}).get("as_of"))
    active=str(manifest.get("active_build_id") or "")
    saved=frozen_snapshot(folder)
    if not saved:
        return {"action":"skip","reason":"no frozen snapshot"}
    fm, source=saved
    pinned_day=date(fm["trade_date"])
    source_build=str(fm["source_build_id"])
    if not current_day or not active:
        raise RuntimeError("no current close mission date/build")
    if current_day > pinned_day:
        return {"action":"new_completed_close","current":current_day,"pinned":pinned_day}
    if current_day < pinned_day:
        raise RuntimeError(f"refusing to regress close from pinned {pinned_day} to {current_day}")
    for key in CLOSE_KEYS:
        meta=ds.get(key)
        if not isinstance(meta,dict):
            raise RuntimeError("missing frozen target: "+key)
        value=retag(source[key],source_build,active)
        # Price/score/decision and evidence numbers are copied unchanged;
        # only the Atomic container's reference identifier is rebound.
        stamp=write(resolve(root,meta),value)
        old_meta=(fm.get("datasets") or {}).get(key) or {}
        meta.update(stamp)
        for k in ("as_of","known_at","complete"):
            if k in old_meta: meta[k]=old_meta[k]
        meta["build_id"]=active
    manifest["close_frozen_trade_date"]=pinned_day
    manifest["close_frozen_source_build_id"]=source_build
    manifest["close_frozen_reason"]="Prior verified completed-close session; unaffected by intraday refresh"
    warnings=manifest.setdefault("health",{}).setdefault("warnings",[])
    note=f"Frozen CLOSE {pinned_day} from independently verified {source_build}; same close prices, ranking and verdicts, not a new model run."
    if note not in warnings: warnings.append(note)
    write(mp,manifest)
    return {"action":"restored","date":pinned_day,"build":active,"from":source_build,"datasets":len(CLOSE_KEYS)}

def capture(root, folder):
    root=Path(root)
    m=load(root/"current_manifest.json")
    ds=m.get("datasets") or {}
    latest=date((ds.get("decision_close_summary") or {}).get("as_of"))
    if not latest:
        raise RuntimeError("cannot capture close without trading date")
    saved=frozen_snapshot(folder) if (Path(folder)/"manifest.json").is_file() else None
    if saved and latest<=date(saved[0]["trade_date"]):
        return {"action":"unchanged","latest":latest}
    active=str(m.get("active_build_id") or "")
    source={key:load(resolve(root,ds[key])) for key in CLOSE_KEYS}
    verify(source,latest,active)
    folder=Path(folder)
    hashes={key:write(folder/(key+".json"),source[key])["hash"] for key in CLOSE_KEYS}
    sm={"trade_date":latest,"source_build_id":active,
        "source_hashes":hashes,
        "datasets":{key:{k:v for k,v in ds[key].items() if k in ("as_of","known_at","complete","build_id")}
                    for key in CLOSE_KEYS}}
    write(folder/"manifest.json",sm)
    return {"action":"captured","trade_date":latest,"source":active,"datasets":len(hashes)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default="docs/v2/data")
    parser.add_argument("--frozen-root",default="docs/v2/frozen-close/latest")
    parser.add_argument("--capture-newer",action="store_true")
    args=parser.parse_args()
    result=capture(args.root,args.frozen_root) if args.capture_newer else hydrate(args.root,args.frozen_root)
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":
    main()
