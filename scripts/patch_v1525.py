#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.25 — Step 5B：多時間框架相對強弱 + 60K死亡交叉語意。

- 15m / 60m：相對同市場股票中位數（免費版穩定 proxy）
- 當日：優先相對官方 TWSE MIS 加權／櫃買即時漲跌
- 5日：優先相對官方指數日K 5日報酬，缺資料才用同市場中位數
- 全部只進決策層，不改既有盤中100分權重
"""
from pathlib import Path
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]


def read(rel): return (ROOT / rel).read_text(encoding="utf-8")
def write(rel, text): (ROOT / rel).write_text(text, encoding="utf-8")
def must(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f"v1.5.25 missing marker: {label}")
    return text.replace(old, new, count)


REL_HELPER = r'''
def _attach_relative_multitimeframe(rows, close_map, close_market, market_live=None):
    """Add 15m/60m/day/5d relative strength as decision context, never as a new score bucket.

    15m/60m use the median return of the same TWSE/TPEx stock pool as a robust free-data proxy.
    Day uses the official live index change when available. 5d uses completed index history when
    available, otherwise falls back to the same-market median 5d stock return.
    """
    if not rows:
        return rows
    market_live = market_live or {}
    close_market = close_market or {}

    def val(x):
        try:
            if x is None: return None
            z = float(x)
            return z if np.isfinite(z) else None
        except Exception:
            return None

    def median_for(market_name, key, source_rows):
        xs=[]
        for x in source_rows:
            if str(x.get("market") or "") != market_name: continue
            z=val(x.get(key))
            if z is not None: xs.append(z)
        return float(np.median(xs)) if xs else None

    # Previous completed daily rows are used only for the 5d fallback.
    close_rows_for_proxy=[]
    for code,d in (close_map or {}).items():
        if not isinstance(d,dict): continue
        close_rows_for_proxy.append({"code":code,"market":d.get("market"),"ret5":d.get("ret5")})

    baselines={}
    for market_name, side, sym in (("上市","taiex","^TWII"),("上櫃","otc","^TWOII")):
        live = market_live.get(sym) or {}
        day_bench = val(live.get("change_pct"))
        day_source = "官方即時指數"
        if day_bench is None:
            day_bench = val((close_market.get(side) or {}).get("change_pct"))
            day_source = "最近完成交易日指數"
        if day_bench is None:
            day_bench = median_for(market_name,"day_change",rows)
            day_source = "同市場中位數 proxy"

        ret5_bench = val((close_market.get(side) or {}).get("ret5"))
        ret5_source = "官方指數5日"
        if ret5_bench is None:
            vals=[]
            for code,d in (close_map or {}).items():
                if not isinstance(d,dict) or str(d.get("market") or "") != market_name: continue
                z=val(d.get("ret5"))
                if z is not None: vals.append(z)
            ret5_bench=float(np.median(vals)) if vals else None
            ret5_source="同市場5日中位數 proxy"

        baselines[market_name]={
            "ret15":median_for(market_name,"ret15",rows),
            "ret60":median_for(market_name,"ret60",rows),
            "day":day_bench,
            "ret5":ret5_bench,
            "sources":{"15m":"同市場15分報酬中位數 proxy","60m":"同市場60分報酬中位數 proxy","day":day_source,"5d":ret5_source},
        }

    for r in rows:
        market_name=str(r.get("market") or "")
        b=baselines.get(market_name) or {}
        d=(close_map or {}).get(str(r.get("code") or "")) or {}
        raw={"15m":val(r.get("ret15")),"60m":val(r.get("ret60")),"day":val(r.get("day_change")),"5d":val(d.get("ret5"))}
        bench={"15m":val(b.get("ret15")),"60m":val(b.get("ret60")),"day":val(b.get("day")),"5d":val(b.get("ret5"))}
        rel={k:(raw[k]-bench[k] if raw[k] is not None and bench[k] is not None else None) for k in raw}
        available=[v for v in rel.values() if v is not None]
        pos=sum(1 for v in available if v>0)
        neg=sum(1 for v in available if v<0)
        day_rel=rel.get("day")
        r15,r60=rel.get("15m"),rel.get("60m")
        if len(available)>=3 and pos>=3 and (day_rel is None or day_rel>=0):
            status="LEADING"; label="多時框領先市場"
        elif r15 is not None and r60 is not None and r15>r60 and r15>0 and (day_rel is None or day_rel>=0):
            status="IMPROVING"; label="短線相對強弱改善"
        elif len(available)>=3 and neg>=3 and (day_rel is None or day_rel<=0):
            status="LAGGING"; label="多時框落後市場"
        else:
            status="MIXED"; label="相對強弱分歧"
        r["relative_multiframe"]={
            "version":"1.0","status":status,"label":label,"available_count":len(available),
            "relative_pct":{k:(round(v,2) if v is not None else None) for k,v in rel.items()},
            "stock_return_pct":{k:(round(v,2) if v is not None else None) for k,v in raw.items()},
            "benchmark_return_pct":{k:(round(v,2) if v is not None else None) for k,v in bench.items()},
            "sources":b.get("sources") or {},"score_weight":0,
            "note":"多時間框架相對強弱只作波段決策確認；不改既有相對強弱15分公式",
        }
    return rows

'''


def patch_build_data():
    p="scripts/build_data.py"; s=read(p)
    s=s.replace("犬子老師飆股雷達 Free Edition v1.5.24","犬子老師飆股雷達 Free Edition v1.5.25",1)

    s=must(s,
        '''    day_change = (cur / prev_close - 1) * 100 if prev_close else 0\n    ret15 = (c.iloc[-1] / c.iloc[-4] - 1) * 100 if len(c) >= 4 else 0\n    vwap_dist =''',
        '''    day_change = (cur / prev_close - 1) * 100 if prev_close else 0\n    ret15 = (c.iloc[-1] / c.iloc[-4] - 1) * 100 if len(c) >= 4 else 0\n    ret60 = (c.iloc[-1] / c.iloc[-13] - 1) * 100 if len(c) >= 13 else None\n    vwap_dist =''',"ret60 calculation")
    s=must(s,
        '''        "ret15": round(ret15, 2),\n        "amplitude_pct":''',
        '''        "ret15": round(ret15, 2),\n        "ret60": round(ret60, 2) if ret60 is not None else None,\n        "amplitude_pct":''',"ret60 output")

    s=must(s,
        '''        if snap and snap.get("date") == str(c.index[-1].date()) and snap.get("change_pct") is not None:\n            change = float(snap["change_pct"])\n        else:\n            change = float((c.iloc[-1]/c.iloc[-2]-1)*100)\n        return {''',
        '''        if snap and snap.get("date") == str(c.index[-1].date()) and snap.get("change_pct") is not None:\n            change = float(snap["change_pct"])\n        else:\n            change = float((c.iloc[-1]/c.iloc[-2]-1)*100)\n        ret5 = float((c.iloc[-1]/c.iloc[-6]-1)*100) if len(c) >= 6 else None\n        return {''',"index ret5 calc")
    s=must(s,
        '''            "change_pct": round(change, 2),\n            "ma5":''',
        '''            "change_pct": round(change, 2), "ret5": round(ret5, 2) if ret5 is not None else None,\n            "ma5":''',"index ret5 output")

    if "def _attach_relative_multitimeframe(" not in s:
        s=must(s,"def _attach_multitimeframe_context(rows, close_map, hourly_obj):",REL_HELPER+"def _attach_multitimeframe_context(rows, close_map, hourly_obj):","relative helper")

    # 60K death-cross semantics: gap below zero plus 20T down is enough to call it a bearish structural conflict.
    s=must(s,
        '''        if not h_available:\n            h_state = "UNAVAILABLE"\n        elif hcat in {"PRE_CROSS", "EARLY", "STABLE_CONT", "ACCEL_CONT"}:''',
        '''        gap20_60 = fv(h, "gap20_60_pct", 999)\n        if not h_available:\n            h_state = "UNAVAILABLE"\n        elif gap20_60 < 0 and dir20 == "DOWN":\n            h_state = "DEATH_CROSS"\n        elif hcat in {"PRE_CROSS", "EARLY", "STABLE_CONT", "ACCEL_CONT"}:''',"death cross state")
    s=must(s,
        '''        h_bearish = h_state == "BEARISH"''',
        '''        h_bearish = h_state in {"BEARISH", "DEATH_CROSS"}''',"death cross bearish")
    s=must(s,
        '''            "BEARISH": "20T/60T偏弱",\n            "NEUTRAL":''',
        '''            "BEARISH": "20T/60T偏弱",\n            "DEATH_CROSS": "20T跌破60T／死亡交叉風險",\n            "NEUTRAL":''',"death cross label")

    # Stage reads multi-timeframe relative strength as evidence/gate, not as score.
    s=must(s,
        '''        mtf_daily_weak = str(mtfd.get("state") or "") == "WEAK"\n        mtf_daily_supportive = str(mtfd.get("state") or "") == "BULLISH"\n\n        invalid_flags = [''',
        '''        mtf_daily_weak = str(mtfd.get("state") or "") == "WEAK"\n        mtf_daily_supportive = str(mtfd.get("state") or "") == "BULLISH"\n        rel_mtf = r.get("relative_multiframe") or {}\n        rel_mtf_status = str(rel_mtf.get("status") or "")\n        rel_mtf_lagging = rel_mtf_status == "LAGGING"\n        rel_mtf_supportive = rel_mtf_status in {"LEADING", "IMPROVING"}\n\n        invalid_flags = [''',"Stage reads relative MTF")
    s=must(s,
        '''            and (trend5 or break12 or tech >= 22)\n            and not (mtf_60_available and mtf_60_bearish)\n        )''',
        '''            and (trend5 or break12 or tech >= 22)\n            and not (mtf_60_available and mtf_60_bearish)\n            and not rel_mtf_lagging\n        )''',"launch relative gate")
    s=must(s,
        '''            if mtf_daily_supportive:\n                launch_signals.append("日K背景偏多")\n            r["stage_signals"] = launch_signals[:5]''',
        '''            if mtf_daily_supportive:\n                launch_signals.append("日K背景偏多")\n            if rel_mtf_supportive:\n                launch_signals.append(rel_mtf.get("label") or "多時框相對強弱改善")\n            r["stage_signals"] = launch_signals[:5]''',"launch relative evidence")
    s=must(s,
        '''            and (trend5 or break12)\n            and not (mtf_60_available and mtf_60_bearish)\n        )''',
        '''            and (trend5 or break12)\n            and not (mtf_60_available and mtf_60_bearish)\n            and not rel_mtf_lagging\n        )''',"trend relative gate")
    s=must(s,
        '''            (mtf_daily_supportive, "日K背景仍支持"),\n        ]''',
        '''            (mtf_daily_supportive, "日K背景仍支持"),\n            (rel_mtf_supportive, rel_mtf.get("label") or "多時框相對強弱改善"),\n        ]''',"setup relative evidence")
    s=must(s,
        '''            (mtf_daily_weak, "日K背景偏弱"),\n        ]''',
        '''            (mtf_daily_weak, "日K背景偏弱"),\n            (rel_mtf_lagging, "15分／60分／當日／5日相對強弱多數落後"),\n        ]''',"weak relative evidence")

    s=must(s,
        '''    hourly_obj = load_json("hourly.json", {})\n    rows = _attach_multitimeframe_context(rows, close_map, hourly_obj)\n\n    market_live = intraday_index_snapshot()\n    sector_rotation =''',
        '''    hourly_obj = load_json("hourly.json", {})\n    rows = _attach_multitimeframe_context(rows, close_map, hourly_obj)\n\n    market_live = intraday_index_snapshot()\n    rows = _attach_relative_multitimeframe(rows, close_map, market, market_live)\n    sector_rotation =''',"attach relative before scoring")

    s=s.replace('"multi_timeframe_version": "1.0"','"multi_timeframe_version": "1.1"')
    s=must(s,
        '''        "score_formula": {"mode": "intraday_execution", "price_structure": 30, "flow_volume": 25, "relative_strength": 15, "sector": 20, "liquidity_risk": 10, "amplitude_efficiency": "inside_flow_and_liquidity_risk_no_new_weight", "multi_timeframe": "decision_context_no_new_weight", "chip": "background_only", "market_separate": 15},''',
        '''        "relative_multiframe_version": "1.0",\n        "score_formula": {"mode": "intraday_execution", "price_structure": 30, "flow_volume": 25, "relative_strength": 15, "sector": 20, "liquidity_risk": 10, "amplitude_efficiency": "inside_flow_and_liquidity_risk_no_new_weight", "multi_timeframe": "decision_context_no_new_weight", "relative_multiframe": "decision_context_no_new_weight", "chip": "background_only", "market_separate": 15},''',"relative root marker")
    s=s.replace('"version": "1.5.24-free"','"version": "1.5.25-free"')
    s=must(s,
        '''        "multi_timeframe_version": "1.1",\n    })''',
        '''        "multi_timeframe_version": "1.1",\n        "relative_multiframe_version": "1.0",\n    })''',"relative status")
    write(p,s)


def patch_bridge():
    p="scripts/bridge_intraday.py"; s=read(p)
    s=must(s,
        '''    out_rows = list(by_code.values())\n    out_rows = bd._attach_multitimeframe_context(out_rows, close_map, bd.load_json("hourly.json", {}))\n    market_live = bd.intraday_index_snapshot()\n    rotation =''',
        '''    out_rows = list(by_code.values())\n    out_rows = bd._attach_multitimeframe_context(out_rows, close_map, bd.load_json("hourly.json", {}))\n    market_live = bd.intraday_index_snapshot()\n    out_rows = bd._attach_relative_multitimeframe(out_rows, close_map, close_market, market_live)\n    rotation =''',"bridge relative refresh")
    s=s.replace('"multi_timeframe_version": "1.0"','"multi_timeframe_version": "1.1"')
    s=must(s,
        '''        "change_radar": change_radar,\n        "multi_timeframe_version": "1.1",\n        "rows": out_rows,''',
        '''        "change_radar": change_radar,\n        "multi_timeframe_version": "1.1",\n        "relative_multiframe_version": "1.0",\n        "rows": out_rows,''',"bridge root relative marker")
    s=s.replace('"version": "1.5.24-free"','"version": "1.5.25-free"')
    s=must(s,
        '''        "multi_timeframe_version": "1.1",\n        "version": "1.5.25-free",''',
        '''        "multi_timeframe_version": "1.1",\n        "relative_multiframe_version": "1.0",\n        "version": "1.5.25-free",''',"bridge status relative")
    write(p,s)


def patch_index():
    p="docs/index.html"; s=read(p)
    s=must(s,"Free Edition v1.5.24｜Step 5 多時間框架","Free Edition v1.5.25｜Step 5 多時間框架完整化","header")
    s=s.replace('.mtfgrid{display:grid;grid-template-columns:repeat(3,1fr);', '.mtfgrid{display:grid;grid-template-columns:repeat(4,1fr);',1)

    # Clarify the help section: structural frames + multi-frame relative strength.
    s=must(s,
        '''      <div class="guide-line"><span class="guide-key">三框共振</span>：5分觸發＋60K結構支持＋日K沒有轉弱，才是最完整的波段進場背景。</div>\n      <div class="guide-tip">60K 20T／60T不新增總分權重，而是正式接進 Stage 與盤中三燈。''',
        '''      <div class="guide-line"><span class="guide-key">三框共振</span>：5分觸發＋60K結構支持＋日K沒有轉弱，才是最完整的波段進場背景。</div>\n      <div class="guide-line"><span class="guide-key">相對強弱 15分／60分／當日／5日</span>：短週期看相對同市場中位數，當日優先對官方加權／櫃買，5日優先對官方指數日K；用來找「大盤回檔它撐住、大盤止跌它先走」的股票。</div>\n      <div class="guide-tip">60K 20T／60T與多時框相對強弱都不新增總分權重，而是正式接進 Stage 與盤中三燈。''',"help relative")

    s=must(s,
        ''' const mtf=r?.multi_timeframe||{},mtfState=String(mtf.state||""),mtf60=mtf["60m"]||{};\n const good=[],wait=[],block=[];''',
        ''' const mtf=r?.multi_timeframe||{},mtfState=String(mtf.state||""),mtf60=mtf["60m"]||{};\n const rsm=r?.relative_multiframe||{},rsStatus=String(rsm.status||"");\n const good=[],wait=[],block=[];''',"entry reads relative")
    s=must(s,
        ''' else wait.push("60K資料待補，不因缺資料自動判空");\n\n const mtfGreenOk=''',
        ''' else wait.push("60K資料待補，不因缺資料自動判空");\n if(rsStatus==="LEADING"||rsStatus==="IMPROVING")good.push(rsm.label||"多時框相對強弱改善");\n else if(rsStatus==="LAGGING")wait.unshift("15分／60分／當日／5日相對強弱多數落後");\n else if(rsStatus==="MIXED")wait.push("多時框相對強弱仍分歧");\n\n const rsGreenOk=rsStatus!=="LAGGING";\n const mtfGreenOk=''',"entry relative checklist")
    s=must(s,
        '''&&stage!=="轉弱警戒"&&mtfGreenOk;''',
        '''&&stage!=="轉弱警戒"&&mtfGreenOk&&rsGreenOk;''',"entry green relative gate")
    s=must(s,
        '''<span>60K ${r?.multi_timeframe?.["60m"]?.label||"待補"}</span><span>20T/60T 權重＝0</span>''',
        '''<span>60K ${r?.multi_timeframe?.["60m"]?.label||"待補"}</span><span>相對強弱 ${r?.relative_multiframe?.label||"待補"}</span><span>MTF權重＝0</span>''',"entry relative display")

    s=must(s,
        ''' const f=m["5m"]||{},h=m["60m"]||{},d=m.daily||{};''',
        ''' const f=m["5m"]||{},h=m["60m"]||{},d=m.daily||{},rs=r?.relative_multiframe||{},rp=rs.relative_pct||{};''',"mtf relative var")
    s=must(s,
        ''' const dailyMA=(d.ma20!==null&&d.ma20!==undefined)?`20MA ${num(d.ma20,2)}｜距20MA ${signed(d.dist20,1)}`:"日K資料待補";\n return `<div class="mtfbox">''',
        ''' const dailyMA=(d.ma20!==null&&d.ma20!==undefined)?`20MA ${num(d.ma20,2)}｜距20MA ${signed(d.dist20,1)}`:"日K資料待補";\n const rsline=`15分 ${rp["15m"]===null||rp["15m"]===undefined?"—":signed(rp["15m"],2)}｜60分 ${rp["60m"]===null||rp["60m"]===undefined?"—":signed(rp["60m"],2)}<br>當日 ${rp.day===null||rp.day===undefined?"—":signed(rp.day,2)}｜5日 ${rp["5d"]===null||rp["5d"]===undefined?"—":signed(rp["5d"],2)}`;\n return `<div class="mtfbox">''',"mtf relative line")
    s=must(s,
        '''<div class="mtfcell"><div class="mtfcellv">${d.label||"日K中性"}</div><div class="mtfcelll">${dailyMA}<br>${d.stage?`前收生命週期：${d.stage}`:"以前一完成交易日日K為背景"}</div></div></div><div class="mtfnote">''',
        '''<div class="mtfcell"><div class="mtfcellv">${d.label||"日K中性"}</div><div class="mtfcelll">${dailyMA}<br>${d.stage?`前收生命週期：${d.stage}`:"以前一完成交易日日K為背景"}</div></div><div class="mtfcell"><div class="mtfcellv">${rs.label||"相對強弱待補"}</div><div class="mtfcelll">${rsline}</div></div></div><div class="mtfnote">''',"mtf 4th cell")

    s=s.replace('./hourly.js?v=1524','./hourly.js?v=1525')
    s=s.replace('./sw.js?v=1524','./sw.js?v=1525')
    s=s.replace('dogsonSwReloaded1524','dogsonSwReloaded1525')
    write(p,s)


def patch_sw():
    p="docs/sw.js"; s=read(p)
    s=must(s,"dogson-free-v1524","dogson-free-v1525","sw cache")
    s=s.replace('./hourly.js?v=1524','./hourly.js?v=1525')
    write(p,s)


def attach_static_relative(rows, close_rows, market_obj):
    cmap={str(x.get("code")):x for x in close_rows if isinstance(x,dict) and x.get("code")}
    def v(x):
        try:return float(x) if x is not None else None
        except:return None
    bases={}
    for mn,side in (("上市","taiex"),("上櫃","otc")):
        same=[r for r in rows if str(r.get("market") or "")==mn]
        def med(key, arr):
            xs=[v(x.get(key)) for x in arr];xs=[x for x in xs if x is not None];return statistics.median(xs) if xs else None
        cd=[d for d in close_rows if str(d.get("market") or "")==mn]
        day=v((market_obj.get(side) or {}).get("change_pct")); day_src="最近完成交易日指數"
        if day is None: day=med("day_change",same);day_src="同市場中位數 proxy"
        r5=v((market_obj.get(side) or {}).get("ret5")); r5src="官方指數5日"
        if r5 is None:r5=med("ret5",cd);r5src="同市場5日中位數 proxy"
        bases[mn]={"15m":med("ret15",same),"60m":med("ret60",same),"day":day,"5d":r5,"sources":{"15m":"同市場15分報酬中位數 proxy","60m":"同市場60分報酬中位數 proxy","day":day_src,"5d":r5src}}
    for r in rows:
        b=bases.get(str(r.get("market") or ""),{});d=cmap.get(str(r.get("code") or ""),{})
        raw={"15m":v(r.get("ret15")),"60m":v(r.get("ret60")),"day":v(r.get("day_change")),"5d":v(d.get("ret5"))}
        rel={k:(raw[k]-b.get(k) if raw[k] is not None and b.get(k) is not None else None) for k in raw}
        av=[x for x in rel.values() if x is not None];pos=sum(x>0 for x in av);neg=sum(x<0 for x in av);day=rel.get("day");r15=rel.get("15m");r60=rel.get("60m")
        if len(av)>=3 and pos>=3 and (day is None or day>=0):st,lab="LEADING","多時框領先市場"
        elif r15 is not None and r60 is not None and r15>r60 and r15>0 and (day is None or day>=0):st,lab="IMPROVING","短線相對強弱改善"
        elif len(av)>=3 and neg>=3 and (day is None or day<=0):st,lab="LAGGING","多時框落後市場"
        else:st,lab="MIXED","相對強弱分歧"
        r["relative_multiframe"]={"version":"1.0","status":st,"label":lab,"available_count":len(av),"relative_pct":{k:(round(x,2) if x is not None else None) for k,x in rel.items()},"stock_return_pct":raw,"benchmark_return_pct":{k:b.get(k) for k in raw},"sources":b.get("sources",{}),"score_weight":0,"note":"多時間框架相對強弱只作波段決策確認；不改既有相對強弱15分公式"}


def patch_current_data():
    ip=ROOT/'docs/data/intraday.json';cp=ROOT/'docs/data/close.json';mp=ROOT/'docs/data/market.json';sp=ROOT/'docs/data/status.json'
    if ip.exists() and cp.exists():
        o=json.loads(ip.read_text(encoding='utf-8'));c=json.loads(cp.read_text(encoding='utf-8'));m=json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else (c.get('market') or {})
        attach_static_relative(o.get('rows') or [],c.get('rows') or [],m)
        o['multi_timeframe_version']='1.1';o['relative_multiframe_version']='1.0';o.setdefault('score_formula',{})['relative_multiframe']='decision_context_no_new_weight'
        ip.write_text(json.dumps(o,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    if sp.exists():
        s=json.loads(sp.read_text(encoding='utf-8'));s['version']='1.5.25-free';s['multi_timeframe_version']='1.1';s['relative_multiframe_version']='1.0';sp.write_text(json.dumps(s,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')


if __name__=='__main__':
    patch_build_data();patch_bridge();patch_index();patch_sw();patch_current_data();print('v1.5.25 Step 5B applied')
