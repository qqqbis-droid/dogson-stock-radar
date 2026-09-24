#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.30 原始構想補完層：不改既有分數，只新增決策欄位與日內累積歷史。"""
from __future__ import annotations
import argparse,json,math
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"docs"/"data"; TW=timezone(timedelta(hours=8))
HIST=DATA/"decision_history.json"

def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return d
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
def f(x,d=0.0):
    try:
        v=float(x);return v if math.isfinite(v) else d
    except:return d
def enrich_chip(r):
    net_raw=r.get("foreign_3d_net")
    avgvol=f(r.get("avg_volume20"))
    strength=None
    if net_raw is not None and avgvol>0:
        # TWSE/TPEx institutional fields are 股數; Yahoo Volume is shares. Units match directly.
        strength=round(float(net_raw)/avgvol*100,2)
    r["foreign_3d_strength_pct"]=strength
    r["foreign_strength_unit"]="shares / prior20d_avg_shares"
    r["chip_force_label"]="資料不足" if strength is None else ("強力買超" if strength>=15 else "明顯買超" if strength>=5 else "小幅買超" if strength>0 else "偏賣超" if strength<0 else "中性")
def breakout_baseline(r):
    # Prefer a true event baseline when upstream has it; otherwise use the stock's own recent volume distribution proxy.
    cur=f(r.get("volume") or r.get("today_volume"))
    event=f(r.get("breakout_volume_median20") or r.get("breakout_volume_avg20"))
    avg=f(r.get("avg_volume20") or r.get("volume20_avg") or r.get("avg_vol20"))
    if event<=0: event=avg
    ratio=round(cur/event,2) if cur>0 and event>0 else None
    r["breakout_volume_baseline"]=event or None
    r["breakout_volume_ratio"]=ratio
    r["breakout_volume_baseline_mode"]="event20" if f(r.get("breakout_volume_median20") or r.get("breakout_volume_avg20"))>0 else ("self20_proxy" if event>0 else "insufficient")
def pattern(r):
    close=f(r.get("close")); vwap=f(r.get("vwap")); pace=f(r.get("pace"),1); ret15=f(r.get("ret15")); rp=f(r.get("range_position_pct"),50)
    trend=bool(r.get("trend5")); br=bool(r.get("break3")); ratio=r.get("breakout_volume_ratio")
    support=f(r.get("support") or r.get("support1") or r.get("sr_support"))
    near_support=support>0 and close>=support and close<=support*1.02
    if br and trend and close>=vwap>0 and pace>=1.2 and ret15>0:
        state="量增上攻"; detail="突破＋站上VWAP＋5分趨勢向上，量能同步推進"
    elif close>0 and (near_support or (-0.6<=f(r.get("vwap_dist"))<=0.8)) and pace<=1.15 and ret15>=-0.8 and rp>=30:
        state="量縮回踩"; detail="回到支撐/VWAP附近，量速收斂且短線未明顯失速"
    elif trend and ret15>=0 and 40<=rp<=85:
        state="承接整理"; detail="短線結構仍在，等待量能或突破確認"
    else:
        state="未形成"; detail="目前沒有形成量縮承接或量增上攻的完整組合"
    r["execution_pattern"]=state;r["execution_pattern_detail"]=detail
def main(mode):
    path=DATA/("intraday.json" if mode=="intraday" else "close.json")
    obj=load(path,{}); rows=obj.get("rows") or []
    hist=load(HIST,{"date":None,"codes":{},"transitions":[],"sector_accel":{}})
    today=datetime.now(TW).date().isoformat(); now=datetime.now(TW).isoformat(timespec="minutes")
    if hist.get("date")!=today: hist={"date":today,"codes":{},"transitions":[],"sector_accel":{}}
    hist.setdefault("transitions",[]); hist.setdefault("sector_accel",{})
    for r in rows:
        enrich_chip(r);breakout_baseline(r)
        if mode=="intraday":
            pattern(r); code=str(r.get("code") or ""); h=hist["codes"].setdefault(code,[])
            snap={"t":r.get("quote_time") or r.get("time") or now,"score":f(r.get("intraday_score") or r.get("score")),"stage":r.get("category"),"pace":f(r.get("pace"),1),"rs":f((r.get("intraday_components") or {}).get("relative_strength")),"sector":f((r.get("intraday_components") or {}).get("sector")),"vwap_dist":f(r.get("vwap_dist")),"pattern":r.get("execution_pattern")}
            previous=h[-1] if h else None
            if not h or h[-1].get("t")!=snap["t"]: h.append(snap)
            h[:]=h[-80:]
            first=h[0] if h else snap; prev=h[-2] if len(h)>1 else first
            oldstage=(previous or {}).get("stage"); newstage=snap.get("stage")
            flags={
                "entered_setup": bool(previous and oldstage!="蓄勢待發" and newstage=="蓄勢待發"),
                "entered_launch": bool(previous and oldstage!="剛啟動" and newstage=="剛啟動"),
                "became_overheat": bool(previous and oldstage!="過熱不追" and newstage=="過熱不追"),
                "became_weak": bool(previous and oldstage not in {"轉弱警戒","結構失效"} and newstage in {"轉弱警戒","結構失效"}),
            }
            r["today_transitions"]=flags
            for typ,hit in flags.items():
                if hit:
                    key=f"{code}:{typ}"
                    if not any(x.get("key")==key for x in hist["transitions"]): hist["transitions"].append({"key":key,"code":code,"name":r.get("name"),"type":typ,"time":snap["t"]})
            r["today_change_summary"]={"score_open_delta":round(snap["score"]-first["score"],1),"score_last_delta":round(snap["score"]-prev["score"],1),"pace_open":first["pace"],"pace_now":snap["pace"],"rs_open":first["rs"],"rs_now":snap["rs"],"stage_open":first["stage"],"stage_now":snap["stage"]}
            d=r["today_change_summary"]["score_open_delta"]
            r["today_direction"]="一路改善" if d>=10 and snap["score"]>=prev["score"] else "重新轉強" if snap["score"]-prev["score"]>=6 else "先強後弱" if d<=-8 else "持平整理"
    if mode=="intraday":
        for z in obj.get("sector_rotation") or []:
            name=str(z.get("sector") or '').strip(); heat=f(z.get("heat")); state=str(z.get("state") or '')
            if name and (heat>=5 or '流入加速' in state):
                old=hist["sector_accel"].get(name) or {"sector":name,"first_time":now}
                old.update({"latest_time":now,"heat":heat,"state":state}); hist["sector_accel"][name]=old
        trans=hist.get("transitions") or []
        dirs={}
        for r in rows: dirs[r.get("today_direction")]=(dirs.get(r.get("today_direction"),0)+1)
        today_radar={
            "new_setup":sum(x.get("type")=="entered_setup" for x in trans),
            "new_launch":sum(x.get("type")=="entered_launch" for x in trans),
            "became_overheat":sum(x.get("type")=="became_overheat" for x in trans),
            "became_weak":sum(x.get("type")=="became_weak" for x in trans),
            "improving":dirs.get("一路改善",0),"restrengthening":dirs.get("重新轉強",0),
            "sector_accel_count":len(hist["sector_accel"]),
            "sector_accel":sorted(hist["sector_accel"].values(),key=lambda x:f(x.get("heat")),reverse=True),
        }
        obj["today_change_radar"]=today_radar
        obj.setdefault("change_radar",{})["today"]=today_radar
        dump(HIST,hist)
    obj["completion_version"]="1.1";obj["completion_updated_at"]=datetime.now(TW).isoformat(timespec="seconds")
    dump(path,obj)
    st=load(DATA/"status.json",{});st.update({"version":"1.5.30-free","completion_version":"1.1"});dump(DATA/"status.json",st)
    print("completion",mode,len(rows))
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--mode",choices=["intraday","close"],required=True);main(ap.parse_args().mode)
