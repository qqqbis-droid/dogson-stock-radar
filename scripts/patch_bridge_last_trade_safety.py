#!/usr/bin/env python3
from pathlib import Path

p=Path('scripts/bridge_intraday.py')
s=p.read_text(encoding='utf-8')

old='''    for code, q in quotes.items():
        _merge_snapshot(store, code, q)
'''
new='''    # Only a newly observed REAL trade may enter the structural snapshot store.
    # Carried quotes are display continuity only; attaching current cumulative
    # volume to an older trade timestamp would fabricate a 5-minute volume bar.
    for code, q in quotes.items():
        if not bool(q.get("quote_carried")):
            _merge_snapshot(store, code, q)
'''
if old not in s:
    raise SystemExit('snapshot merge marker not found')
s=s.replace(old,new,1)

old2='''        if q:
            row["quote_date"] = q.get("date")
            row["quote_time"] = q.get("time")
            row["quote_source"] = q.get("source")
            row["quote_close"] = q.get("close")
            row["close"] = q.get("close")
'''
new2='''        if q:
            row["quote_date"] = q.get("date")
            row["quote_time"] = q.get("time")
            row["quote_snapshot_time"] = q.get("snapshot_time")
            row["quote_source"] = q.get("source")
            row["quote_carried"] = bool(q.get("quote_carried"))
            row["quote_close"] = q.get("close")
            row["close"] = q.get("close")
'''
if old2 not in s:
    raise SystemExit('second quote block not found')
s=s.replace(old2,new2,1)

old3='''    quote_times = [str(q.get("time") or "")[:5] for q in quotes.values() if q.get("time")]
    quote_latest = max(quote_times) if quote_times else None
    structure_latest = max(fresh_times) if fresh_times else obj.get("quote_layer", {}).get("structure_latest_time")
'''
new3='''    # Market-data freshness and last-trade freshness are different clocks.
    # snapshot_time proves the MIS response is current even when that stock has
    # not traded in the last few seconds; time is the timestamp of the real trade.
    snapshot_times = [str(q.get("snapshot_time") or q.get("time") or "")[:5] for q in quotes.values() if (q.get("snapshot_time") or q.get("time"))]
    trade_times = [str(q.get("time") or "")[:5] for q in quotes.values() if q.get("time")]
    quote_latest = max(snapshot_times) if snapshot_times else None
    trade_latest = max(trade_times) if trade_times else None
    structure_latest = max(fresh_times) if fresh_times else obj.get("quote_layer", {}).get("structure_latest_time")
'''
if old3 not in s:
    raise SystemExit('freshness block not found')
s=s.replace(old3,new3,1)

old4='''            "latest_quote_time": quote_latest,
            "latest_structure_time": structure_latest,
'''
new4='''            "latest_quote_time": quote_latest,
            "latest_trade_time": trade_latest,
            "latest_structure_time": structure_latest,
'''
if old4 not in s:
    raise SystemExit('bridge latest block not found')
s=s.replace(old4,new4,1)

old5='''            "latest_time": quote_latest,
            "structure_latest_time": structure_latest,
            "note": "現價/當日漲跌採官方MIS；技術尾端採持久化MIS快照橋接，Yahoo僅作較早5分K底座",
'''
new5='''            "latest_time": quote_latest,
            "latest_trade_time": trade_latest,
            "structure_latest_time": structure_latest,
            "note": "latest_time=官方MIS快照新鮮度；每檔quote_time=最後真實成交時間。現價只沿用同日曾實際觀測到的成交價，不用買賣盤推估成交價。",
'''
if old5 not in s:
    raise SystemExit('quote layer block not found')
s=s.replace(old5,new5,1)

p.write_text(s,encoding='utf-8')
print('patched bridge: carried quotes display-only; freshness clocks split')
