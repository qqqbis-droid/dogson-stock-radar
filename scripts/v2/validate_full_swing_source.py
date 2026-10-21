#!/usr/bin/env python3
"""Guard original 24-item Wave Scoring 2.0 at the legacy-to-atomic boundary.

Never publish a v2-scored close from an old source lacking original engine
component records. This does NOT reconstruct scores, change weights, or
re-evaluate a previously frozen completed-session snapshot.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

MODELS = {
    "technical": ("inuko-tech-v2.0", "technical_components_v2",
                  ("trend","breakout","volume_price","momentum","relative","risk_quality"),50),
    "chip": ("inuko-chip-v2.0", "chip_components_v2",
             ("foreign","trust","sbl","margin","consensus","price_chip","sector_inst"),25),
    "sector": ("inuko-sector-v2.0", "sector_components_v2",
               ("breadth","leaders","persistence","capital_resonance","structure","taxonomy"),15),
    "liquidity": ("inuko-liquidity-v2.0", "liquidity_components_v2",
                  ("avg_turnover","stability","price_impact","continuity","crowding"),10),
}

def num(x):
    try:
        if x is None or isinstance(x,bool):return None
        n=float(x)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError):return None

def validate(payload):
    day=str(payload.get("trade_date") or "")[:10]
    rows=payload.get("rows")
    if len(day)!=10 or not isinstance(rows,list) or not rows:
        raise ValueError("no completed-close date or stock rows")
    errors=[]
    observed=0
    for row in rows:
        code=str(row.get("code") or "?")
        valid=True
        for name,(version,field,keys,cap) in MODELS.items():
            if row.get(name+"_model_version")!=version:
                errors.append(code+": "+name+" version not original 2.0")
                valid=False
                continue
            components=row.get(field)
            if not isinstance(components,dict) or set(components)!=set(keys):
                errors.append(code+": "+name+" original component keys missing")
                valid=False
            sv=num(row.get(name+"_score_v2"))
            if sv is None or sv<0 or sv>cap+.01:
                errors.append(code+": "+name+" v2 score absent/outside cap")
                valid=False
        swing=row.get("swing_components")
        weights=row.get("swing_weights")
        weighted=row.get("swing_weighted_components")
        total=num(row.get("swing_quality_score"))
        entry=num(row.get("entry_position_score"))
        if not isinstance(swing,dict) or not isinstance(weights,dict) or not isinstance(weighted,dict):
            errors.append(code+": missing original swing component ledger")
            valid=False
        elif set(swing)!=set(MODELS) or set(weights)!=set(MODELS) or set(weighted)!=set(MODELS):
            errors.append(code+": incorrect swing component ledger keys")
            valid=False
        elif abs(sum(num(v) or 0 for v in weighted.values())-(total if total is not None else -999))>.35:
            errors.append(code+": weighted components cannot reconcile to final score")
            valid=False
        if total is None or not 0<=total<=100 or entry is None or not 0<=entry<=100:
            errors.append(code+": missing quality/entry score")
            valid=False
        if valid:observed+=1
    if errors:
        raise ValueError(f"original 2.0 scoring missing/inconsistent in {len(rows)-observed}/{len(rows)} close stocks on {day}: "+ "; ".join(errors[:12]))
    return {"trade_date":day,"stocks":len(rows),"original_model_count":observed,
            "items_per_stock":24,"model":"INUKO original source-backed Wave 2.0",
            "weights":{"technical":50,"chip":25,"sector":15,"liquidity":10},
            "entry_position_independent":True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True)
    args=ap.parse_args()
    payload=json.loads(Path(args.source).read_text(encoding="utf-8"))
    print(json.dumps(validate(payload),ensure_ascii=False))

if __name__=="__main__":
    main()
