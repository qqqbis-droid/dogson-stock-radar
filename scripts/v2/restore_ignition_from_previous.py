#!/usr/bin/env python3
"""Restore same-session validated ignition model evidence after a UI data overwrite.

Recovery is allowed ONLY from manifest.previous_good_build_id and ONLY when
both source and destination rows belong to the exact same completed session
with identical verified closing prices. Never recompute from swing scores,
copy a previous trading day's model, or override newer valid ignition data.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

IGNITION_FIELDS = (
    "ignition_model_version", "ignition_raw_score", "ignition_confidence",
    "ignition_stage", "ignition_signal_action", "ignition_action",
    "ignition_execution_state", "ignition_execution_ready",
    "ignition_execution_note", "ignition_verdict", "ignition_summary",
    "ignition_reasons", "ignition_gate_cap", "ignition_gate_flags",
    "ignition_breakout_distance_pct", "ignition_breakout_distance_atr",
    "ignition_candidate", "ignition_rank",
)

def date(s):
    return str(s or "")[:10]

def number(v):
    try:
        if v is None or isinstance(v, bool): return None
        n=float(v)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None

def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def save(p: Path, obj):
    raw=(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n").encode("utf-8")
    p.write_bytes(raw)
    return {"hash":"sha256:"+hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}

def filepath(root,meta):
    u=str(meta.get("url") or "")
    return root/(u.removeprefix("./data/") if u.startswith("./data/") else u.lstrip("./"))

def current(row,day):
    s=(row.get("scores") or {}).get("ignition_score")
    return (date(row.get("trade_date") or row.get("as_of"))==day
            and row.get("ignition_model_version")=="inuko-ignition-v2.0"
            and number(s) is not None
            and number(row.get("ignition_rank")) is not None
            and number(row.get("ignition_confidence")) is not None)

def copyable(src,dest,day):
    if not isinstance(src,dict) or not isinstance(dest,dict): return False
    if not current(src,day): return False
    if date(dest.get("trade_date") or dest.get("as_of"))!=day:return False
    a=number((src.get("quote") or {}).get("price"))
    b=number((dest.get("quote") or {}).get("price"))
    return a is not None and a>0 and b is not None and a==b

def restore(root: Path):
    mp=root/"current_manifest.json"
    m=load(mp)
    build=str(m.get("active_build_id") or "")
    prior=str(m.get("previous_good_build_id") or "")
    day=date(m.get("trade_date"))
    if not build or not day or not prior or prior==build:
        return {"restored":0,"reason":"no previous distinct build"}
    ds=m.get("datasets") or {}
    keys=("decision_close_detail","decision_close_index","decision_close_summary")
    if any(k not in ds for k in keys):raise RuntimeError("Missing complete close datasets")
    path=filepath(root,ds["decision_close_detail"])
    target=load(path)
    current_rows=target.get("items")
    if not isinstance(current_rows,dict):raise RuntimeError("Canonical close details missing")
    previous=root/"builds"/prior/"decision-close-detail.json"
    if not previous.is_file():
        return {"restored":0,"reason":"no previous same-day close model"}
    old=load(previous).get("items") or {}
    if not isinstance(old,dict):raise RuntimeError("Previous model details invalid")
    restored={}
    for code,dest in current_rows.items():
        code=str(code)
        src=old.get(code)
        if current(dest,day):continue
        if not copyable(src,dest,day):continue
        nd=dict(dest)
        nd["scores"]=dict(dest.get("scores") or {})
        nd["scores"]["ignition_score"]=src["scores"]["ignition_score"]
        for field in IGNITION_FIELDS:
            if field in src:nd[field]=src[field]
        current_rows[code]=nd
        restored[code]=nd
    if not restored:
        return {"restored":0,"reason":"no valid same-session price-matched evidence"}
    target["items"]=current_rows
    ds["decision_close_detail"].update(save(path,target))
    for key in ("decision_close_index","decision_close_summary"):
        p=filepath(root,ds[key])
        rows=load(p)
        if not isinstance(rows,list):raise RuntimeError("Invalid "+key)
        rows=[{**r,**{k:v for k,v in restored[str(r["code"])].items() if k.startswith("ignition_") or k=="scores"}}
            if str(r.get("code") or "") in restored else r for r in rows]
        ds[key].update(save(p,rows))
    # Evidence and component breakdown must come from the same verified
    # earlier model build, not a synthetic frontend score.
    ek="stock_detail_close"
    ep=ds.get(ek)
    old_ev=root/"builds"/prior/"stock-detail-close.json"
    if ep and old_ev.is_file():
        epath=filepath(root,ep)
        current_evidence=load(epath)
        prev_evidence=load(old_ev)
        new_items=current_evidence.get("items") or {}
        prev_items=prev_evidence.get("items") or {}
        if isinstance(new_items,dict) and isinstance(prev_items,dict):
            count=0
            for code in restored:
                olde=prev_items.get(code)
                newer=new_items.get(code)
                if not isinstance(olde,dict) or not isinstance(newer,dict):continue
                if date(olde.get("trade_date") or olde.get("as_of") or day)!=day:continue
                pa=number(olde.get("close"));pb=number(newer.get("close"))
                if pa is None or pb is None or pa!=pb:continue
                newer=dict(newer)
                for k,v in olde.items():
                    if k.startswith("ignition_"):newer[k]=v
                new_items[code]=newer
                count+=1
            current_evidence["items"]=new_items
            ep.update(save(epath,current_evidence))
        else:count=0
    else:count=0
    # Never claim a new engine ran: provenance explicitly records recovery.
    msg=f"Ignition 2.0 restored for {len(restored)} matching {day} closes from prior verified build {prior}; not recomputed."
    warnings=m.setdefault("health",{}).setdefault("warnings",[])
    if msg not in warnings:warnings.append(msg)
    save(mp,m)
    return {"restored":len(restored),"breakdown_restored":count,"from":prior,"into":build,"trade_date":day}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="docs/v2/data")
    args=ap.parse_args()
    print(json.dumps(restore(Path(args.root)),ensure_ascii=False))

if __name__=="__main__":main()
