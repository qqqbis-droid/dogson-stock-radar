#!/usr/bin/env python3
from pathlib import Path
p=Path('scripts/bridge_intraday.py')
s=p.read_text(encoding='utf-8')
old='''        row["quote_date"] = q.get("date")
        row["quote_time"] = q.get("time")
        row["quote_source"] = q.get("source")
        row["quote_close"] = q.get("close")
'''
new='''        row["quote_date"] = q.get("date")
        row["quote_time"] = q.get("time")
        row["quote_snapshot_time"] = q.get("snapshot_time")
        row["quote_source"] = q.get("source")
        row["quote_carried"] = bool(q.get("quote_carried"))
        row["quote_close"] = q.get("close")
'''
if old not in s: raise SystemExit('first quote block not found')
s=s.replace(old,new,1)
if old in s:
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('patched bridge quote metadata')
