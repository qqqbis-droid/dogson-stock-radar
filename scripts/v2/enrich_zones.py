#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, math, pathlib
from copy import deepcopy

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def write_json(path, obj):
    path = pathlib.Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    return {"hash":"sha256:"+hashlib.sha256(text.encode()).hexdigest(),"bytes":len(text.encode())}


def rows_of(payload):
    if isinstance(payload, list): return payload
    if isinstance(payload, dict):
        for key in ("all_rows","rows","items","data","stocks","results"):
            value=payload.get(key)
            if isinstance(value,list): return value
    return []


def source_map(payload):
    return {str(r.get("code")):r for r in rows_of(payload) if isinstance(r,dict) and r.get("code")}


def num(value):
    try:
        v=float(value); return v if math.isfinite(v) else None
    except Exception: return None


def first_present(row, keys):
    for key in keys:
        value=row.get(key)
        if value not in (None,"",[]): return value
    return None


def zone_numbers(value):
    if isinstance(value,dict):
        lo=num(first_present(value,("low","zone_low","min","lower")))
        hi=num(first_present(value,("high","zone_high","max","upper")))
        mid=num(first_present(value,("center","price","level","mid")))
        if mid is None and lo is not None and hi is not None: mid=(lo+hi)/2
        if lo is None and mid is not None: lo=mid
        if hi is None and mid is not None: hi=mid
        return lo,hi,mid
    mid=num(value); return (mid,mid,mid) if mid is not None else (None,None,None)


def evidence_of(value):
    if not isinstance(value,dict): return []
    out=[]
    raw=value.get("evidence") or value.get("labels")
    if isinstance(raw,list): out += [str(x).strip() for x in raw if str(x).strip()]
    basis=value.get("basis") or value.get("reason")
    if isinstance(basis,str): out += [x.strip() for x in basis.replace("+","＋").split("＋") if x.strip()]
    return list(dict.fromkeys(out))[:10]


def current_price(row):
    return num(first_present(row,("quote_close","close","price","last","last_price")))


def raw_anchors(row,side):
    array_key="support_levels" if side=="SUPPORT" else "resistance_levels"
    values=row.get(array_key); out=[x for x in values if isinstance(x,dict)] if isinstance(values,list) else []
    keys=("support","support_zone","entry_support","near_support") if side=="SUPPORT" else ("resistance","resistance_zone","near_resistance")
    legacy=first_present(row,keys)
    if legacy is not None: out.append(legacy)
    return out


def atr_pct(row):
    p=row.get("dynamic_profile") if isinstance(row.get("dynamic_profile"),dict) else {}
    return num(p.get("atr14_pct")) or 0.0


def candidate(value,label,weight,anchor=False):
    lo,hi,mid=zone_numbers(value)
    if lo is None or hi is None or mid is None or mid<=0: return None
    lo,hi=sorted((lo,hi)); ev=evidence_of(value) or [label]
    strength=num(value.get("strength")) if isinstance(value,dict) else None
    return {"low":lo,"high":hi,"center":mid,"evidence":ev,"weight":max(.2,float(weight))+.18*(strength or 0),"anchor":bool(anchor)}


def add(out,value,label,weight,anchor=False):
    c=candidate(value,label,weight,anchor)
    if c: out.append(c)


def fused_levels(row,side,hourly=None):
    """Return up to two credible multi-timeframe price bands for one side."""
    cur=current_price(row)
    if cur is None or cur<=0: return raw_anchors(row,side)[:2]
    items=[]
    for value in raw_anchors(row,side): add(items,value,"日K多證據結構",3.1,True)
    for key,label,weight in (("ma5","5MA",1.05),("ma10","10MA",1.35),("ma20","20MA",2.05),("ma60","60MA",2.2),("ma120","120MA",2.0)):
        v=num(row.get(key))
        if v is not None: add(items,{"center":v,"basis":label},label,weight)
    weak_key,weak_label=("low","今日低") if side=="SUPPORT" else ("high","今日高")
    v=num(row.get(weak_key))
    if v is not None: add(items,{"center":v,"basis":weak_label},weak_label,.85)
    for key,label,weight in (("ma20_60","60分20T",1.75),("ma60_60","60分60T",2.05),("ma240_60","60分240T",2.25)):
        v=num((hourly or {}).get(key))
        if v is not None: add(items,{"center":v,"basis":label},label,weight)

    valid=[]
    for c in items:
        p=c["center"]
        if side=="SUPPORT" and p<=cur*1.003: valid.append(c)
        if side=="RESISTANCE" and p>=cur*.997: valid.append(c)
    if not valid: return []
    ap=atr_pct(row)
    cluster_pct=max(.0065,min(.018,(ap/100)*.32 if ap else .0105))
    near=[c for c in valid if abs(c["center"]/cur-1)<=.18]
    if near: valid=near

    clusters=[]
    for seed in valid:
        members=[c for c in valid if abs(c["center"]/seed["center"]-1)<=cluster_pct]
        sw=sum(c["weight"] for c in members)
        center=sum(c["center"]*c["weight"] for c in members)/max(sw,1e-9)
        distance=(center/cur-1)*100
        ev=[]
        for c in sorted(members,key=lambda x:x["weight"],reverse=True):
            for e in c["evidence"]:
                if e not in ev: ev.append(e)
        anchors=sum(1 for c in members if c["anchor"])
        if not (anchors or len(ev)>=2 or sw>=2.0): continue
        quality=sw+.45*len(ev)+.8*anchors-abs(distance/100)*8
        spread=max(c["high"] for c in members)-min(c["low"] for c in members)
        anchor_half=max(((c["high"]-c["low"])/2 for c in members if c["anchor"]),default=0.0)
        adaptive=cur*max(.0035,min(.012,(ap/100)*.16 if ap else .0045))
        half=max(cur*.0035,adaptive,spread*.55,anchor_half)
        confidence=min(100.0,30+sw*7+len(ev)*4.5+anchors*8)
        strength=5 if confidence>=82 else 4 if confidence>=68 else 3 if confidence>=54 else 2 if confidence>=42 else 1
        clusters.append({"center":center,"low":max(0,center-half),"high":center+half,"distance_pct":distance,"basis":"＋".join(ev[:6]),"evidence":ev[:8],"evidence_count":len(ev),"strength":strength,"confidence":round(confidence,1),"quality":quality})

    unique=[]
    for c in sorted(clusters,key=lambda x:(-x["quality"],abs(x["distance_pct"]))):
        if not any(abs(c["center"]/x["center"]-1)<=cluster_pct*.55 for x in unique): unique.append(c)
    chosen=[]
    for c in sorted(unique,key=lambda x:(abs(x["distance_pct"]),-x["quality"])):
        if any(abs(c["center"]/x["center"]-1)<=max(.008,cluster_pct*.75) for x in chosen): continue
        chosen.append(c)
        if len(chosen)==2: break

    out=[]; prefix="S" if side=="SUPPORT" else "R"
    for i,c in enumerate(chosen,1):
        rank=f"{prefix}{i}"
        if side=="SUPPORT":
            label="第一防守帶" if i==1 else "深層防守帶"
            validation="回測價格帶守住並重新站回上緣；量縮回測優先。"
            invalidation="連續兩根對應週期K收在支撐帶下緣下方，或跌破後反抽站不回且量價轉弱，才視為結構失效。"
        else:
            label="第一突破帶" if i==1 else "延伸突破帶"
            validation="有效收上壓力帶上緣且量能不萎縮；突破後回測不破才算確認。"
            invalidation="突破後快速跌回壓力帶下方且無法站回，視為假突破並恢復壓力角色。"
        out.append({"rank":rank,"label":label,"low":round(c["low"],2),"high":round(c["high"],2),"center":round(c["center"],2),"distance_pct":round(c["distance_pct"],2),"basis":c["basis"],"evidence":c["evidence"],"evidence_count":c["evidence_count"],"strength":c["strength"],"confidence":c["confidence"],"structure_state":"ACTIVE","validation_condition":validation,"invalidation_condition":invalidation})
    return out


def make_zone(value,side,decision,ordinal):
    lo,hi,mid=zone_numbers(value)
    if lo is None or hi is None or mid is None: return None
    lo,hi=sorted((lo,hi)); prefix="S" if side=="SUPPORT" else "R"; default=f"{prefix}{ordinal}"
    rank=str(value.get("rank") or default) if isinstance(value,dict) else default
    if rank not in {"S1","S2","R1","R2"}: rank=default
    context_id=str(decision.get("decision_context_id") or decision.get("context_id") or "")
    ev=evidence_of(value); strength=num(value.get("strength")) if isinstance(value,dict) else None; confidence=num(value.get("confidence")) if isinstance(value,dict) else None
    distance=num(value.get("distance_pct")) if isinstance(value,dict) else None; ec=value.get("evidence_count") if isinstance(value,dict) else None
    label=value.get("label") if isinstance(value,dict) else None; state=value.get("structure_state") if isinstance(value,dict) else None
    validation=value.get("validation_condition") if isinstance(value,dict) else None; invalidation=value.get("invalidation_condition") if isinstance(value,dict) else None
    return {
        "schema_version":"2.0.0","build_id":decision["build_id"],"dataset":"zone","trade_date":decision.get("trade_date"),"session_phase":decision.get("session_phase"),"as_of":decision.get("as_of"),"known_at":decision.get("known_at"),"generated_at":decision.get("generated_at"),"freshness":decision.get("freshness"),"complete":True,"source_status":deepcopy(decision.get("source_status") or {"sources":[],"fallback":False}),
        "zone_id":f"{context_id}:{side}:{rank}","side":side,"rank":rank,"label":str(label or ("第一防守帶" if rank=="S1" else "深層防守帶" if rank=="S2" else "第一突破帶" if rank=="R1" else "延伸突破帶")),"low":round(lo,4),"high":round(hi,4),"center":round(mid,4),"distance_pct":round(distance,4) if distance is not None else None,"strength":strength,"confidence":confidence,"evidence":ev,"evidence_count":int(ec) if ec is not None else len(ev),"structure_state":str(state or "ACTIVE"),"validation_condition":str(validation) if validation else None,"invalidation_condition":str(invalidation) if invalidation else None,"created_at":decision.get("generated_at"),"last_tested_at":None,"role_state":"ORIGINAL"
    }


def reference_only_marker(decision):
    return {"schema_version":"2.0.0","build_id":decision["build_id"],"dataset":"zone","trade_date":decision.get("trade_date"),"session_phase":decision.get("session_phase"),"as_of":decision.get("as_of"),"known_at":decision.get("known_at"),"generated_at":decision.get("generated_at"),"freshness":decision.get("freshness"),"complete":True,"source_status":deepcopy(decision.get("source_status") or {"sources":[],"fallback":False}),"zone_id":f"{decision['build_id']}:DAYTRADE:REFERENCE_ONLY","side":"SUPPORT","rank":"S1","label":"市場已收盤・當沖結構停用","low":0.0,"high":0.0,"center":0.0,"distance_pct":None,"strength":0.0,"confidence":0.0,"evidence":["REFERENCE_ONLY","DATA_STALE","NON_EXECUTABLE"],"evidence_count":3,"structure_state":"BROKEN","validation_condition":None,"invalidation_condition":"市場非 LIVE；此記錄只是停用標記，不是可執行支撐／壓力","created_at":decision.get("generated_at"),"last_tested_at":None,"role_state":"EXPIRED"}


def enrich_context(*,legacy_root,output_root,manifest,context,source_file,hourly_by_code):
    build_id=manifest["active_build_id"]; build_dir=output_root/"builds"/build_id
    detail_key=f"decision_{context}_detail"; summary_key=f"decision_{context}_summary"
    if detail_key not in manifest.get("datasets",{}): return []
    detail_path=build_dir/pathlib.Path(manifest["datasets"][detail_key]["url"]).name
    summary_path=build_dir/pathlib.Path(manifest["datasets"][summary_key]["url"]).name
    detail=load_json(detail_path,{}); summary=load_json(summary_path,[]); raw=source_map(load_json(legacy_root/source_file,{}))
    zones=[]; zone_by_id={}; decisions=detail.get("items") or {}
    for code,decision in decisions.items():
        row=raw.get(str(code),{})
        stale=context in {"intraday","daytrade"} and (decision.get("action_state")=="DATA_STALE" or "DATA_QUALITY_RISK" in (decision.get("risk_overlays") or []))
        if stale:
            decision["support_zone_ids"]=[]; decision["resistance_zone_ids"]=[]; continue
        hourly=hourly_by_code.get(str(code),{}) if context=="close" else {}
        ss=[make_zone(v,"SUPPORT",decision,i) for i,v in enumerate(fused_levels(row,"SUPPORT",hourly),1)]
        rr=[make_zone(v,"RESISTANCE",decision,i) for i,v in enumerate(fused_levels(row,"RESISTANCE",hourly),1)]
        ss=[z for z in ss if z]; rr=[z for z in rr if z]
        decision["support_zone_ids"]=[z["zone_id"] for z in ss]; decision["resistance_zone_ids"]=[z["zone_id"] for z in rr]
        for z in [*ss,*rr]:
            if z["zone_id"] not in zone_by_id: zone_by_id[z["zone_id"]]=z; zones.append(z)
    if context=="daytrade" and not zones and decisions:
        vals=[x for x in decisions.values() if isinstance(x,dict)]
        if vals and all(str(x.get("action_state") or "")=="DATA_STALE" for x in vals): zones.append(reference_only_marker(vals[0]))
    summary_by_code={str(x.get("code")):x for x in summary if isinstance(x,dict)}
    for code,full in decisions.items():
        short=summary_by_code.get(str(code))
        if short is not None:
            short["support_zone_ids"]=list(full.get("support_zone_ids") or []); short["resistance_zone_ids"]=list(full.get("resistance_zone_ids") or [])
    dm=write_json(detail_path,detail); sm=write_json(summary_path,summary); manifest["datasets"][detail_key].update(dm); manifest["datasets"][summary_key].update(sm)
    zone_key=f"zone_{context}"; fn=f"zone-{context}.json"; zm=write_json(build_dir/fn,zones); source=manifest["datasets"][detail_key]
    manifest["datasets"][zone_key]={"url":f"./data/builds/{build_id}/{fn}","hash":zm["hash"],"bytes":zm["bytes"],"complete":True,"as_of":source.get("as_of"),"known_at":source.get("known_at"),"build_id":build_id}
    return zones


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--legacy-root",default=str(ROOT/"docs"/"data")); ap.add_argument("--output",default=str(ROOT/"docs"/"v2"/"data")); args=ap.parse_args()
    legacy_root=pathlib.Path(args.legacy_root); output_root=pathlib.Path(args.output); manifest_path=output_root/"current_manifest.json"; manifest=load_json(manifest_path,{})
    if not manifest.get("active_build_id"): raise SystemExit("active_build_id missing")
    hourly=source_map(load_json(legacy_root/"hourly.json",{})); counts={}
    for context,source in (("close","close.json"),("intraday","intraday.json"),("daytrade","daytrade.json")):
        counts[context]=len(enrich_context(legacy_root=legacy_root,output_root=output_root,manifest=manifest,context=context,source_file=source,hourly_by_code=hourly))
    warnings=manifest.setdefault("health",{}).setdefault("warnings",[]); note="支撐／壓力結構 3.0：日K多證據結構＋日均線＋60分K 20T/60T/240T 共振；以價格帶呈現 S1/S2/R1/R2，不把單點價位當成假精準值。"
    if note not in warnings: warnings.append(note)
    write_json(manifest_path,manifest); print("zone enrichment 3.0 OK",counts)


if __name__=="__main__": main()
