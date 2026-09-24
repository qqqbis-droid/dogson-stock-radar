#!/usr/bin/env python3
from pathlib import Path

p=Path('scripts/build_data.py')
s=p.read_text(encoding='utf-8')

old_meta='''                    meta = {
                        "date": today_s,
                        "snapshot_time": tm,
                        "prev_close": prev,
                        "volume_lots": fnum(x.get("v")),
                        "market": x.get("ex"),
                    }
'''
new_meta='''                    meta = {
                        "date": today_s,
                        "snapshot_time": tm,
                        "prev_close": prev,
                        "volume_lots": fnum(x.get("v")),
                        "bid1": fnum(str(x.get("b") or "").split("_")[0]),
                        "ask1": fnum(str(x.get("a") or "").split("_")[0]),
                        "open": fnum(x.get("o")),
                        "high": fnum(x.get("h")),
                        "low": fnum(x.get("l")),
                        "market": x.get("ex"),
                    }
'''
if old_meta not in s:
    raise SystemExit('MIS meta marker not found')
s=s.replace(old_meta,new_meta,1)

old_missing='''        if tr is None:
            diag["missing"] += 1
            continue
        last = float(tr["close"])
        prev = meta.get("prev_close")
        out[code] = {
            "date": today_s,
            "time": tr.get("time"),              # last REAL trade we observed
            "snapshot_time": meta.get("snapshot_time"),
            "close": last,
            "prev_close": prev,
            "change_pct": ((last / prev - 1) * 100) if prev and prev > 0 else None,
            "volume_lots": meta.get("volume_lots"),
            "source": "TWSE MIS last-trade cache" if carried else "TWSE MIS live trade",
            "quote_carried": bool(carried),
        }
'''
new_missing='''        prev = meta.get("prev_close")
        if tr is None:
            # No trade happened exactly during our sampling window.  Still keep
            # the official order-book snapshot so the UI can prove the market
            # data is fresh without inventing a transaction price.
            diag["missing"] += 1
            out[code] = {
                "date": today_s,
                "time": None,
                "snapshot_time": meta.get("snapshot_time"),
                "close": None,
                "prev_close": prev,
                "change_pct": None,
                "volume_lots": meta.get("volume_lots"),
                "bid1": meta.get("bid1"),
                "ask1": meta.get("ask1"),
                "open": meta.get("open"),
                "high": meta.get("high"),
                "low": meta.get("low"),
                "source": "TWSE MIS orderbook snapshot",
                "quote_carried": False,
                "quote_has_trade": False,
            }
            continue
        last = float(tr["close"])
        out[code] = {
            "date": today_s,
            "time": tr.get("time"),              # last REAL trade we observed
            "snapshot_time": meta.get("snapshot_time"),
            "close": last,
            "prev_close": prev,
            "change_pct": ((last / prev - 1) * 100) if prev and prev > 0 else None,
            "volume_lots": meta.get("volume_lots"),
            "bid1": meta.get("bid1"),
            "ask1": meta.get("ask1"),
            "open": meta.get("open"),
            "high": meta.get("high"),
            "low": meta.get("low"),
            "source": "TWSE MIS last-trade cache" if carried else "TWSE MIS live trade",
            "quote_carried": bool(carried),
            "quote_has_trade": True,
        }
'''
if old_missing not in s:
    raise SystemExit('MIS out marker not found')
s=s.replace(old_missing,new_missing,1)

p.write_text(s,encoding='utf-8')
print('patched build_data: all MIS snapshots visible without fake trade price')

p=Path('scripts/bridge_intraday.py')
s=p.read_text(encoding='utf-8')
old='''        row["quote_source"] = q.get("source")
        row["quote_carried"] = bool(q.get("quote_carried"))
        row["quote_close"] = q.get("close")
'''
new='''        row["quote_source"] = q.get("source")
        row["quote_carried"] = bool(q.get("quote_carried"))
        row["quote_has_trade"] = bool(q.get("quote_has_trade", q.get("close") is not None))
        row["quote_bid1"] = q.get("bid1")
        row["quote_ask1"] = q.get("ask1")
        row["quote_volume_lots"] = q.get("volume_lots")
        row["quote_close"] = q.get("close")
'''
count=s.count(old)
if count < 1:
    raise SystemExit('bridge quote marker not found')
s=s.replace(old,new)
# In the structural-refresh block, never replace technical close with None.
old_uncond='''            row["quote_close"] = q.get("close")
            row["close"] = q.get("close")
            if q.get("change_pct") is not None:
'''
new_uncond='''            row["quote_close"] = q.get("close")
            if q.get("close") is not None:
                row["close"] = q.get("close")
            if q.get("change_pct") is not None:
'''
if old_uncond in s:
    s=s.replace(old_uncond,new_uncond,1)
p.write_text(s,encoding='utf-8')
print('patched bridge: snapshot/orderbook metadata attached to every MIS row')
