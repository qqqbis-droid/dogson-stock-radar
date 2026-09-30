#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, time, timezone, timedelta
from pathlib import Path

TW = timezone(timedelta(hours=8))


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    return {"hash": "sha256:" + hashlib.sha256(text.encode()).hexdigest(), "bytes": len(text.encode())}


def num(v, default=None):
    try:
        x = float(v)
        return x if x == x else default
    except Exception:
        return default


def trade_date_of(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("trade_date", "source_trade_date", "date"):
        s = str(payload.get(key) or "")[:10]
        if len(s) == 10:
            return s
    market = payload.get("market") or {}
    for key in ("trade_date", "date"):
        s = str(market.get(key) or "")[:10]
        if len(s) == 10:
            return s
    dates = []
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        s = str(row.get("quote_date") or row.get("market_trade_date") or row.get("date") or "")[:10]
        if len(s) == 10:
            dates.append(s)
    return max(dates) if dates else None


def source_time(payload, trade_date, fallback="13:30:00"):
    if isinstance(payload, dict):
        for key in ("as_of", "source_updated_at", "updated_at", "generated_at"):
            v = payload.get(key)
            if isinstance(v, str) and v:
                return v if "T" in v else (f"{trade_date}T{v[:8]}+08:00" if trade_date and ":" in v else v)
    return f"{trade_date}T{fallback}+08:00" if trade_date else None


def regime(mode):
    text = str(mode or "").strip()
    if text in {"多方", "偏多", "多頭", "積極"}: return "SELECTIVE_RISK_ON"
    if text in {"防守", "偏空", "保守"}: return "DEFENSIVE"
    if text in {"空方", "風險關閉", "Risk Off", "RISK_OFF"}: return "RISK_OFF"
    return "NEUTRAL"


def intraday_phase(td):
    now = datetime.now(TW)
    if td == now.date().isoformat() and time(9, 0) <= now.time() <= time(13, 40):
        return "LIVE", "LIVE"
    return "CLOSE_FREEZE", "FROZEN" if td else "UNKNOWN"


def source_status(source, known_at):
    return {"sources":[source,"legacy-v1-migration-adapter"],"fallback":False,"fallback_source":None,"fallback_build_id":None,"fallback_reason":None,"last_success_at":known_at}


def close_components(m):
    t = m.get("taiex") if isinstance(m.get("taiex"), dict) else None
    o = m.get("otc") if isinstance(m.get("otc"), dict) else None
    breadth = num(m.get("breadth_up_pct"))
    ts = 2.5 if t is None else 5.0 if t.get("trend") else 2.5 if t.get("above20") else 0.0
    os = 2.0 if o is None else 4.0 if o.get("trend") else 2.0 if o.get("above20") else 0.0
    if breadth is None: bs = 1.5
    elif breadth >= 60: bs = 3.0
    elif breadth >= 55: bs = 2.5
    elif breadth >= 50: bs = 1.5
    elif breadth >= 45: bs = 0.5
    else: bs = 0.0
    fs = num(m.get("foreign_score"), 1.5)
    return {
        "taiex":{"score":ts,"max":5,"trend":bool(t.get("trend")) if t else None,"above20":bool(t.get("above20")) if t else None},
        "otc":{"score":os,"max":4,"trend":bool(o.get("trend")) if o else None,"above20":bool(o.get("above20")) if o else None},
        "breadth":{"score":bs,"max":3,"breadth_up_pct":breadth},
        "foreign":{"score":fs,"max":3,"foreign_net_billion":num(m.get("foreign_net_billion")),"foreign_5d_billion":num(m.get("foreign_5d_billion"))},
    }


def market_close(close, fallback, build_id, generated_at):
    m = (close.get("market") if isinstance(close, dict) else None) or fallback or {}
    td = trade_date_of(close) or str(m.get("trade_date") or "")[:10] or None
    known = source_time(close, td, "15:30:00")
    fresh = "FRESH" if td == datetime.now(TW).date().isoformat() else "STALE"
    return {
        "schema_version":"2.0.0","build_id":build_id,"dataset":"market_context","context":"CLOSE","trade_date":td,"session_phase":"POST_CLOSE",
        "as_of":f"{td}T13:30:00+08:00" if td else None,"known_at":known,"generated_at":generated_at,"freshness":fresh,
        "complete":bool(m.get("data_complete", close.get("data_complete", False) if isinstance(close, dict) else False)),"source_status":source_status("docs/data/close.json",known),
        "market_regime":regime(m.get("market_mode")),"market_score":num(m.get("market_score")),"market_confidence":90 if m.get("market_score") is not None else 55,
        "score_model":"close_5_4_3_3","components":close_components(m),
        "metrics":{"breadth_up_pct":num(m.get("breadth_up_pct")),"foreign_net_billion":num(m.get("foreign_net_billion")),"foreign_twse_billion":num(m.get("foreign_twse_billion")),"foreign_tpex_billion":num(m.get("foreign_tpex_billion")),"foreign_5d_billion":num(m.get("foreign_5d_billion"))},
        "notes":["盤後15分＝加權5＋櫃買4＋市場廣度3＋官方外資3。"]
    }


def market_intraday(intra, build_id, generated_at):
    m = (intra.get("market") if isinstance(intra, dict) else None) or {}
    td = trade_date_of(intra)
    phase, fresh = intraday_phase(td)
    as_of = source_time(intra, td)
    raw = m.get("components") if isinstance(m.get("components"), dict) else {}
    comps = {}
    for key, mx in (("taiex",3),("otc",3),("breadth",3),("funds",4),("sector",2)):
        r = raw.get(key) if isinstance(raw.get(key), dict) else {}
        comps[key] = {**r, "score":num(r.get("score")), "max":num(r.get("max"),mx)}
    q = intra.get("quote_layer") if isinstance(intra.get("quote_layer"), dict) else {}
    b = intra.get("bridge") if isinstance(intra.get("bridge"), dict) else {}
    quote_time = q.get("latest_time") or b.get("latest_quote_time")
    last_trade = q.get("latest_trade_time") or b.get("latest_trade_time")
    structure_time = q.get("structure_latest_time") or b.get("latest_structure_time")
    return {
        "schema_version":"2.0.0","build_id":build_id,"dataset":"market_context","context":"INTRADAY","trade_date":td,"session_phase":phase,
        "as_of":as_of,"known_at":as_of,"generated_at":generated_at,"freshness":fresh,"complete":bool(m.get("market_score") is not None and td),"source_status":source_status("docs/data/intraday.json",as_of),
        "market_regime":regime(m.get("market_mode")),"market_score":num(m.get("market_score")),"market_confidence":90 if m.get("market_score") is not None else 55,
        "score_model":"intraday_3_3_3_4_2","components":comps,
        "metrics":{"breadth_up_pct":num(m.get("breadth_up_pct")),"turnover_up_pct":num(m.get("turnover_up_pct")),"above_vwap_turnover_pct":num(m.get("above_vwap_turnover_pct")),"weighted_pace":num(m.get("weighted_pace")),"sector_positive_pct":num(m.get("sector_positive_pct")),"sector_positive_count":num(m.get("sector_positive_count")),"sector_negative_count":num(m.get("sector_negative_count")),"quote_snapshot_time":quote_time,"latest_trade_time":last_trade,"structure_latest_time":structure_time},
        "notes":["盤中15分＝加權3＋櫃買3＋市場廣度3＋資金動能4＋族群擴散2。","盤後外資只作背景，不計入盤中15分。","盤中資料採雙時鐘：官方MIS報價快線約5分鐘；VWAP、量速與族群結構約10分鐘更新。"]
    }


def capital_base(build_id, context, td, phase, fresh, as_of, generated_at, rows, source, method):
    return {"schema_version":"2.0.0","build_id":build_id,"dataset":"capital_context","context":context,"trade_date":td,"session_phase":phase,"as_of":as_of,"known_at":as_of,"generated_at":generated_at,"freshness":fresh,"complete":bool(rows),"source_status":source_status(source,as_of),"method":method,"rows":rows}


def capital_intraday(intra, build_id, generated_at):
    td = trade_date_of(intra); phase, fresh = intraday_phase(td); as_of = source_time(intra, td)
    rows=[]
    for r in (intra.get("sector_rotation") or []):
        if not isinstance(r,dict) or not str(r.get("sector") or "").strip(): continue
        rows.append({"primary_group":str(r.get("sector")).strip(),"member_count":int(r.get("count") or 0),"heat":num(r.get("heat")),"state":r.get("state"),"change_pct":num(r.get("change_pct")),"turnover_share_pct":num(r.get("turnover_share_pct")),"recent_share_pct":num(r.get("recent_share_pct")),"previous_share_pct":num(r.get("previous_share_pct")),"share_change_pp":num(r.get("share_change_pp")),"up_pct":num(r.get("up_pct")),"above_vwap_pct":num(r.get("above_vwap_pct")),"pace":num(r.get("pace")),"window_min":num(r.get("window_min")),"leaders":r.get("leaders") if isinstance(r.get("leaders"),list) else []})
    rows.sort(key=lambda x:(x.get("heat") is not None,x.get("heat") or -999),reverse=True)
    return capital_base(build_id,"INTRADAY",td,phase,fresh,as_of,generated_at,rows,"docs/data/intraday.json","成交金額占比變化＋價格/VWAP＋市場廣度＋量速；不是法人淨流入。")


def capital_close(close, build_id, generated_at):
    td=trade_date_of(close); as_of=source_time(close,td,"15:30:00"); fresh="FRESH" if td==datetime.now(TW).date().isoformat() else "STALE"
    rows=[]
    for r in (close.get("sector_funds") or []):
        if not isinstance(r,dict) or not str(r.get("sector") or "").strip(): continue
        rows.append({"primary_group":str(r.get("sector")).strip(),"today_amount_100m":num(r.get("today_amount_100m")),"net5_amount_100m":num(r.get("net5_amount_100m")),"net20_amount_100m":num(r.get("net20_amount_100m")),"amount_history_days":int(r.get("amount_history_days") or 0),"amount_coverage_pct":num(r.get("amount_coverage_pct")),"amount_method":r.get("amount_method"),"today_lots":num(r.get("today_lots")),"net5_lots":num(r.get("net5_lots")),"net20_lots":num(r.get("net20_lots")),"history_days":int(r.get("history_days") or 0),"latest_date":r.get("latest_date"),"flow_streak":int(r.get("flow_streak") or 0),"flow_direction":r.get("flow_direction"),"accelerating":bool(r.get("accelerating")),"flow_text":r.get("flow_text"),"action":r.get("action"),"ret5_pct":num(r.get("ret5_pct"))})
    rows.sort(key=lambda x:abs(x.get("today_amount_100m") or 0),reverse=True)
    return capital_base(build_id,"CLOSE",td,"POST_CLOSE",fresh,as_of,generated_at,rows,"docs/data/close.json","外資＋投信官方淨買賣股數 × 各交易日收盤價估算金額；金額看力度、張數看方向；未含自營商。")


def register(root, manifest, key, filename, obj):
    bid=manifest["active_build_id"]; meta=write(root/"builds"/bid/filename,obj)
    manifest.setdefault("datasets",{})[key]={"url":f"./data/builds/{bid}/{filename}","hash":meta["hash"],"bytes":meta["bytes"],"complete":bool(obj.get("complete")),"as_of":obj.get("as_of"),"known_at":obj.get("known_at"),"build_id":bid}


def patch_scores(root, manifest, close_score, intra_score):
    for prefix, score in (("decision_close_",close_score),("decision_intraday_",intra_score),("decision_daytrade_",intra_score)):
        if score is None: continue
        for key, meta in (manifest.get("datasets") or {}).items():
            if not key.startswith(prefix): continue
            raw=str(meta.get("url") or ""); path=root/(raw[len("./data/"):] if raw.startswith("./data/") else raw.lstrip("./")); obj=load(path)
            records=obj if isinstance(obj,list) else list((obj.get("items") or {}).values()) if isinstance(obj,dict) else []
            changed=False
            for rec in records:
                scores=rec.get("scores") if isinstance(rec,dict) else None
                if isinstance(scores,dict) and scores.get("market_score")!=score:
                    scores["market_score"]=score; changed=True
            if changed: meta.update(write(path,obj))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--legacy-root",default="docs/data"); ap.add_argument("--root",default="docs/v2/data"); args=ap.parse_args()
    legacy=Path(args.legacy_root); root=Path(args.root); manifest_path=root/"current_manifest.json"; manifest=load(manifest_path)
    if not isinstance(manifest,dict) or not manifest.get("active_build_id"): raise SystemExit("market/capital restore: manifest missing active_build_id")
    close=load(legacy/"close.json",{}) or {}; intra=load(legacy/"intraday.json",{}) or {}; fallback=load(legacy/"market.json",{}) or {}; generated=datetime.now(TW).isoformat(timespec="seconds"); bid=manifest["active_build_id"]
    mc=market_close(close,fallback,bid,generated); mi=market_intraday(intra,bid,generated); cc=capital_close(close,bid,generated); ci=capital_intraday(intra,bid,generated)
    register(root,manifest,"market_close_context","market-close-context.json",mc); register(root,manifest,"market_intraday_context","market-intraday-context.json",mi); register(root,manifest,"capital_close_context","capital-close-context.json",cc); register(root,manifest,"capital_intraday_context","capital-intraday-context.json",ci)
    patch_scores(root,manifest,mc.get("market_score"),mi.get("market_score"))
    warnings=manifest.setdefault("health",{}).setdefault("warnings",[])
    msg="Market/Capital Context 已分離：盤中/當沖使用即時15分與族群成交動能；盤後使用收盤15分與法人估算金額。"
    if msg not in warnings: warnings.append(msg)
    msg2="盤中市場環境使用雙時鐘：MIS報價快線約5分鐘；VWAP/量速/族群結構約10分鐘，UI須分別標示。"
    if msg2 not in warnings: warnings.append(msg2)
    write(manifest_path,manifest)
    print("restored market/capital contexts",{"build":bid,"intraday_score":mi.get("market_score"),"close_score":mc.get("market_score"),"intraday_sectors":len(ci["rows"]),"close_sectors":len(cc["rows"])})


if __name__ == "__main__":
    main()
