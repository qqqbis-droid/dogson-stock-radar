#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

def load(p: Path): return json.loads(p.read_text(encoding='utf-8'))
def write(p: Path, obj):
    text=json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n'; p.write_text(text,encoding='utf-8'); raw=text.encode('utf-8'); return {'hash':'sha256:'+hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def resolve(root: Path,url: str):
    raw=str(url or ''); return root/raw[len('./data/'):] if raw.startswith('./data/') else root/raw.lstrip('./')
def lots_text(s: str):
    m=re.search(r'([+-]?[\d,]+(?:\.\d+)?)\s*股',str(s or ''))
    if not m:return s
    n=float(m.group(1).replace(',',''))/1000.0
    txt='0' if n == 0 else (f'{n:+,.0f}' if float(n).is_integer() else f'{n:+,.1f}')
    return str(s).replace(m.group(0),f'{txt} 張')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='docs/v2/data'); args=ap.parse_args(); root=Path(args.root)
    mp=root/'current_manifest.json'; m=load(mp); ds=m.get('datasets') or {}
    close_meta=ds.get('decision_close_detail') or ds.get('decision_close_summary') or {}
    close_date=str(close_meta.get('as_of') or '')[:10]
    if len(close_date)!=10: raise SystemExit('close semantics v5: close dataset date missing')
    dmeta=ds.get('decision_close_detail'); imeta=ds.get('decision_close_index'); zmeta=ds.get('zone_close')
    if not dmeta or not imeta: raise SystemExit('close semantics v5: decision close datasets missing')
    detail_path=resolve(root,dmeta.get('url')); index_path=resolve(root,imeta.get('url'))
    detail=load(detail_path); items=(detail.get('items') or {}) if isinstance(detail,dict) else {}
    index=load(index_path)
    rank_map={str(r.get('code')):r.get('opportunity_rank') for r in index if isinstance(r,dict) and r.get('code')} if isinstance(index,list) else {}
    detail_changed=False
    for row in items.values():
        if str(row.get('trade_date') or row.get('as_of') or '')[:10]!=close_date: continue
        code=str(row.get('code') or '')
        if rank_map.get(code) is not None and row.get('opportunity_rank')!=rank_map[code]:
            row['opportunity_rank']=rank_map[code]; detail_changed=True
        exp=row.get('score_explanations') or {}; chip=(exp.get('chip') or {}).get('items') or []
        for it in chip:
            if isinstance(it,dict) and re.search(r'外資|投信',str(it.get('label') or '')):
                old=str(it.get('detail') or ''); new=lots_text(old)
                if new!=old: it['detail']=new; detail_changed=True
    if detail_changed: dmeta.update(write(detail_path,detail))

    changed=0
    for row in index if isinstance(index,list) else []:
        src=items.get(str(row.get('code')))
        if not src or str(src.get('trade_date') or src.get('as_of') or '')[:10]!=close_date: continue
        for k in ('freshness','lifecycle_stage','action_state','actionable','opportunity_bucket','why_now','blockers','upgrade_conditions','risk_flags',
                  'ignition_model_version','ignition_raw_score','ignition_confidence','ignition_stage','ignition_signal_action','ignition_action',
                  'ignition_execution_state','ignition_execution_ready','ignition_execution_note',
                  'ignition_verdict','ignition_summary','ignition_reasons','ignition_gate_cap','ignition_gate_flags',
                  'ignition_breakout_distance_pct','ignition_breakout_distance_atr','ignition_candidate','ignition_rank'):
            if k in src and row.get(k)!=src.get(k): row[k]=src.get(k); changed+=1
        rs=row.setdefault('scores',{}); ss=src.get('scores') or {}
        for k in ('swing_quality_score','entry_position_score','ignition_score','market_score'):
            if k in ss and rs.get(k)!=ss.get(k): rs[k]=ss.get(k); changed+=1
    if changed: imeta.update(write(index_path,index))

    zone_changed=0
    if zmeta:
        zp=resolve(root,zmeta.get('url')); zones=load(zp)
        for z in zones if isinstance(zones,list) else []:
            if str(z.get('trade_date') or z.get('as_of') or '')[:10]!=close_date: continue
            if z.get('session_phase')!='POST_CLOSE': z['session_phase']='POST_CLOSE'; zone_changed+=1
            if z.get('freshness')!='FRESH': z['freshness']='FRESH'; zone_changed+=1
        if zone_changed: zmeta.update(write(zp,zones))

    warnings=m.setdefault('health',{}).setdefault('warnings',[])
    warning='Close UI Semantics V5：盤後 index 與 detail 以最近完成交易日同步，法人顯示單位改為張；結構價位由前端依台股 tick 對齊顯示。'
    if warning not in warnings: warnings.append(warning)
    write(mp,m)
    print('close semantics v5',{'close_date':close_date,'index_changes':changed,'detail_lot_unit':detail_changed,'zone_changes':zone_changed})
if __name__=='__main__': main()
