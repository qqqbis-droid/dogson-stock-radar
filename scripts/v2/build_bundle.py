#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, sys
from datetime import datetime, timezone, timedelta
ROOT=pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.v2.legacy_adapter import adapt_legacy_stock
TW=timezone(timedelta(hours=8)); OUT_ROOT=ROOT/"docs"/"v2"/"data"
def dumps(obj): return json.dumps(obj,ensure_ascii=False,indent=2)+"\n"
def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); text=dumps(obj); path.write_text(text,encoding="utf-8")
    return {"hash":"sha256:"+hashlib.sha256(text.encode()).hexdigest(),"bytes":len(text.encode())}
def demo_rows():
    return [
      {"code":"9001","name":"示例甲","market":"TWSE","industry_name":"電子","sector_group":"AI伺服器","score":86,"entry_position_score":76,"category":"剛啟動","stage_signals":["結構突破","量價同步","族群共振"]},
      {"code":"9002","name":"示例乙","market":"TWSE","industry_name":"電子","sector_group":"PCB","score":82,"entry_position_score":68,"category":"蓄勢待發","stage_signals":["均線靠攏","族群轉強"]},
      {"code":"9003","name":"示例丙","market":"TPEX","industry_name":"電子","sector_group":"散熱","score":91,"entry_position_score":42,"category":"趨勢持有","overheat_reasons":["距支撐過遠"],"stage_signals":["趨勢延續"]},
      {"code":"9004","name":"示例丁","market":"TPEX","industry_name":"半導體","sector_group":"ASIC","score":78,"entry_position_score":70,"category":"回踩承接","stage_signals":["回測支撐","量縮承接"]},
      {"code":"9005","name":"示例戊","market":"TWSE","industry_name":"電子","sector_group":"CPO","score":74,"entry_position_score":55,"category":"回踩觀察","stage_signals":["測試支撐"]},
      {"code":"9006","name":"示例己","market":"TWSE","industry_name":"電子","sector_group":"高速傳輸","score":64,"entry_position_score":44,"category":"轉弱警戒","stage_risks":["相對強弱轉差","跌回短均"]},
      {"code":"9007","name":"示例庚","market":"TPEX","industry_name":"電子","sector_group":"PCB","score":59,"entry_position_score":35,"category":"結構失效","stage_risks":["失效區跌破"]},
      {"code":"9008","name":"示例辛","market":"TWSE","industry_name":"電子","sector_group":"AI伺服器","score":69,"entry_position_score":61,"category":"觀察","stage_signals":["條件尚未集中"]}]
def make_market(build_id,trade_date,phase):
    now=datetime.now(TW).isoformat(timespec="seconds")
    return {"schema_version":"2.0.0","build_id":build_id,"dataset":"market","trade_date":trade_date,"session_phase":phase,"as_of":now,"known_at":now,"generated_at":now,"freshness":"FRESH","complete":True,"source_status":{"sources":["demo"],"fallback":False,"fallback_source":None,"fallback_build_id":None,"fallback_reason":None,"last_success_at":now},"market_regime":"SELECTIVE_RISK_ON","market_score":9.5,"market_confidence":86,"risk_flags":["示例資料：非真實行情"]}
def make_sector_rows(build_id,trade_date,phase):
    now=datetime.now(TW).isoformat(timespec="seconds"); groups=[("AI伺服器",72,14.2,16.5,["9001","9008"]),("PCB",66,12.8,14.8,["9002","9007"]),("散熱",63,11.5,13.2,["9003"]),("ASIC",58,10.8,12.6,["9004"]),("CPO",52,9.1,10.4,["9005"]),("高速傳輸",44,7.2,8.8,["9006"])]
    out=[]
    for i,(name,breadth,close_score,intra_score,leaders) in enumerate(groups,1):
        out.append({"schema_version":"2.0.0","build_id":build_id,"dataset":"sector","trade_date":trade_date,"session_phase":phase,"as_of":now,"known_at":now,"generated_at":now,"freshness":"FRESH","complete":True,"source_status":{"sources":["demo"],"fallback":False,"fallback_source":None,"fallback_build_id":None,"fallback_reason":None,"last_success_at":now},"sector_id":f"DEMO_{i}","primary_group":name,"industry_parent":"電子","supply_chain_links":[],"classification_confidence":90,"taxonomy_version":"2.0.0","reviewed_at":now,"member_count":max(3,len(leaders)),"advancers":2,"strong_count":len(leaders),"breadth_pct":breadth,"turnover_share":None,"turnover_acceleration":None,"heat_score":intra_score,"heat_delta":None,"momentum_regime":"WARM","leaders":leaders,"leader_count":len(leaders),"persistence":None,"continuation_ratio":None,"sector_score_close":close_score,"sector_score_intraday":intra_score})
    return out
def build_demo(output_root=OUT_ROOT):
    trade_date="2026-09-28"; phase="POST_CLOSE"; build_id="cb2-demo-20260928-postclose-v1"; build_dir=output_root/"builds"/build_id
    market=make_market(build_id,trade_date,phase); decisions=[adapt_legacy_stock(r,build_id=build_id,trade_date=trade_date,session_phase=phase,mission="close_next_day",market_score=market["market_score"]) for r in demo_rows()]
    order={"NEXT_DAY_READY":0,"BREAKOUT_WATCH":1,"PULLBACK_WATCH":2,"TREND_QUALITY":3,"RESEARCH":4,"RISK":5}; decisions.sort(key=lambda d:(order.get(d["opportunity_bucket"],99),-(d["scores"]["entry_position_score"] or -1),d["code"]))
    for i,d in enumerate(decisions,1): d["opportunity_rank"]=i
    sectors=make_sector_rows(build_id,trade_date,phase); detail={"schema_version":"2.0.0","build_id":build_id,"items":{}}
    for d in decisions: detail["items"][d["code"]]={"decision_context_id":d["decision_context_id"],"summary":{"why_now":d["why_now"],"blockers":d["blockers"],"upgrade_conditions":d["upgrade_conditions"]},"zones":[{"side":"SUPPORT","label":"示例支撐區","low":None,"high":None},{"side":"RESISTANCE","label":"示例壓力區","low":None,"high":None}],"evidence":[],"history":[]}
    portfolio=[]
    for code in ["9003","9004"]:
        d=next(x for x in decisions if x["code"]==code); portfolio.append({"code":code,"name":d["name"],"reason_status":"VALID","action":"HOLD","core_entry_reason":["示例：原始結構仍成立"],"quantity":1,"avg_cost":None,"market_value":None})
    health={"build_id":build_id,"validation_passed":True,"warnings":["DEMO DATA ONLY"],"errors":[]}; datasets={}; payloads={"market_summary":("market-summary.json",market),"sector_summary":("sector-summary.json",sectors),"decision_summary":("decision-summary.json",decisions),"decision_detail":("decision-detail.json",detail),"portfolio_summary":("portfolio-summary.json",portfolio),"health":("health.json",health)}; now=datetime.now(TW).isoformat(timespec="seconds")
    for key,(filename,obj) in payloads.items():
        meta=write_json(build_dir/filename,obj); datasets[key]={"url":f"./data/builds/{build_id}/{filename}","hash":meta["hash"],"bytes":meta["bytes"],"complete":True,"as_of":now,"known_at":now,"build_id":build_id}
    manifest={"schema_version":"2.0.0","app_contract_version":"2.0.0","active_build_id":build_id,"previous_good_build_id":None,"trade_date":trade_date,"session_phase":phase,"generated_at":now,"datasets":datasets,"health":{"validation_passed":True,"warnings":["DEMO DATA ONLY"],"errors":[],"fallback_reason":None}}; write_json(output_root/"current_manifest.json",manifest); return manifest
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--demo",action="store_true"); ap.add_argument("--output",default=str(OUT_ROOT)); args=ap.parse_args()
    if not args.demo: raise SystemExit("Phase 1 currently exposes demo build only. Legacy live adapter is wired in Phase 4 Integration.")
    print(build_demo(pathlib.Path(args.output))["active_build_id"])
if __name__=="__main__": main()
