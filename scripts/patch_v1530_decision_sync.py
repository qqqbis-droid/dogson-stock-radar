#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.30 completion 1.2: make final entry/portfolio decisions consume Step 6 dynamic gates.
Also allow the first intraday scan to detect a true same-day transition from the prior close stage,
and prevent Step 8 from downgrading the app version during intraday refreshes.
"""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]

def rd(p): return (ROOT/p).read_text(encoding='utf-8')
def wr(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def one(s,old,new,label):
    if old not in s: raise SystemExit('missing '+label)
    return s.replace(old,new,1)

def patch_ui():
    p='docs/index.html';s=rd(p)
    old=''' const vwap=+(r?.vwap_dist??0),day=+(r?.day_change??0),pos=+(r?.range_position_pct??50),pace=+(r?.pace??0);\n const marketMode=String(mkt?.market_mode||"—"),marketScore=+(mkt?.market_score??0);'''
    new=''' const vwap=+(r?.vwap_dist??0),day=+(r?.day_change??0),pos=+(r?.range_position_pct??50),pace=+(r?.pace??0),ret15=+(r?.ret15??0);\n const dyn=r?.dynamic_thresholds||{};\n const dayHot=+(dyn.day_hot_pct??8.5),vwapHot=+(dyn.vwap_hot_pct??4.5),paceHot=+(dyn.pace_hot_x??5),ret15Hot=+(dyn.ret15_hot_pct??4);\n const marketMode=String(mkt?.market_mode||"—"),marketScore=+(mkt?.market_score??0);'''
    s=one(s,old,new,'entry dynamic vars')
    s=one(s,' if(day>=8.5)block.push(`當日已漲 ${num(day,1)}%，追價風險高`);\n if(vwap>4.5)block.push(`距 VWAP +${num(vwap,1)}%，延伸過遠`);',''' if(day>=dayHot)block.push(`當日 ${num(day,1)}% ≥ 個股過熱門檻 ${num(dayHot,1)}%`);\n if(vwap>vwapHot)block.push(`距 VWAP +${num(vwap,1)}% > 個股門檻 ${num(vwapHot,1)}%`);\n if(pace>paceHot)block.push(`量速 ${num(pace,1)}x > 個股門檻 ${num(paceHot,1)}x`);\n if(ret15>ret15Hot)block.push(`15分鐘 ${num(ret15,1)}% > 個股門檻 ${num(ret15Hot,1)}%`);''','entry hard gates')
    s=s.replace(' if(pace>5)wait.push(`量速 ${num(pace,1)}x，先防爆量追價`);',' if(pace>Math.max(3.5,paceHot*.8))wait.push(`量速 ${num(pace,1)}x，接近個股過熱門檻 ${num(paceHot,1)}x`);',1)
    if '三燈 hard gate 也使用個股動態門檻' not in s:
        s=s.replace('只改門檻，不改 30/25/15/20/10 權重。','只改門檻，不改 30/25/15/20/10 權重；三燈 hard gate 也使用個股動態門檻。',1)
    wr(p,s)

def patch_completion():
    p='scripts/build_completion.py';s=rd(p)
    if 'prior_close_map=' not in s:
        s=one(s,'    hist.setdefault("transitions",[]); hist.setdefault("sector_accel",{})\n    for r in rows:','''    hist.setdefault("transitions",[]); hist.setdefault("sector_accel",{})\n    close_obj=load(DATA/"close.json",{}) if mode=="intraday" else {}\n    prior_close_map={str(x.get("code") or ""):x for x in (close_obj.get("rows") or [])}\n    for r in rows:''','prior close map')
        s=one(s,'            oldstage=(previous or {}).get("stage"); newstage=snap.get("stage")\n            flags={\n                "entered_setup": bool(previous and oldstage!="蓄勢待發" and newstage=="蓄勢待發"),\n                "entered_launch": bool(previous and oldstage!="剛啟動" and newstage=="剛啟動"),\n                "became_overheat": bool(previous and oldstage!="過熱不追" and newstage=="過熱不追"),\n                "became_weak": bool(previous and oldstage not in {"轉弱警戒","結構失效"} and newstage in {"轉弱警戒","結構失效"}),\n            }','''            prior_close=prior_close_map.get(code) or {}\n            oldstage=(previous or {}).get("stage") if previous else prior_close.get("category")\n            baseline_source="previous_scan" if previous else ("prior_close" if oldstage else "none")\n            newstage=snap.get("stage"); has_baseline=bool(oldstage)\n            flags={\n                "entered_setup": bool(has_baseline and oldstage!="蓄勢待發" and newstage=="蓄勢待發"),\n                "entered_launch": bool(has_baseline and oldstage!="剛啟動" and newstage=="剛啟動"),\n                "became_overheat": bool(has_baseline and oldstage!="過熱不追" and newstage=="過熱不追"),\n                "became_weak": bool(has_baseline and oldstage not in {"轉弱警戒","結構失效"} and newstage in {"轉弱警戒","結構失效"}),\n            }\n            r["today_transition_baseline"]=baseline_source''','prior close transition')
    s=s.replace('obj["completion_version"]="1.1"','obj["completion_version"]="1.2"').replace('"completion_version":"1.1"','"completion_version":"1.2"')
    wr(p,s)

def patch_daytrade_version():
    p='scripts/build_daytrade.py';s=rd(p)
    s=s.replace('"version": "1.5.29-free",','"version": "1.5.30-free",')
    wr(p,s)

def patch_status():
    p='docs/data/status.json';d=json.loads(rd(p));d['version']='1.5.30-free';d['completion_version']='1.2';wr(p,json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')

if __name__=='__main__':
    patch_ui();patch_completion();patch_daytrade_version();patch_status();print('v1.5.30 completion 1.2 decision sync applied')
