#!/usr/bin/env python3
from pathlib import Path

p=Path('scripts/build_data.py')
s=p.read_text(encoding='utf-8')
start=s.index('def intraday_stock_snapshot(universe_df, codes=None):')
end=s.index('def _weighted_pct(', start)
new=r'''def intraday_stock_snapshot(universe_df, codes=None):
    """Official TWSE MIS near-real-time quotes with last-trade persistence.

    MIS ``z`` is event-like: a snapshot may return ``-`` when no trade happened
    at that instant.  Never interpret that as "no market data".  We sample the
    market a few times, keep every real ``z`` we actually observe, and carry
    forward only a same-day previously observed trade price/time.  Bid/ask is
    never used as a fake last price.
    """
    if universe_df is None or universe_df.empty:
        return {}
    import time as _time

    wanted = set(str(c) for c in (codes or []))
    recs = universe_df[["code", "market"]].astype(str).to_dict("records")
    if wanted:
        recs = [r for r in recs if r["code"] in wanted]
    now = now_tw()
    today = now.date()
    today_s = today.isoformat()

    def fnum(v):
        try:
            z = str(v or "").replace(",", "").strip()
            return float(z) if z not in {"", "-", "--"} else None
        except Exception:
            return None

    # Seed with the last real trade that was already published on today's page.
    # sync_live_data.py downloads the previous live intraday.json before every run.
    cached = {}
    try:
        prev_obj = load_json("intraday.json", {})
        for r in (prev_obj.get("rows") or []):
            code = str(r.get("code") or "")
            qd = str(r.get("quote_date") or "")
            px = fnum(r.get("quote_close"))
            qt = str(r.get("quote_time") or "").strip()
            if code and qd == today_s and px is not None and px > 0 and qt:
                cached[code] = {"close": px, "time": qt}
    except Exception:
        cached = {}

    latest_meta = {}
    fresh = {}
    diag = {"requests":0,"msg_entries":0,"today_entries":0,"fresh_z":0,"cached_z":0,"missing":0}

    # Larger batches are fine: diagnostics proved MIS returns all requested rows.
    # The real issue is z being event-like, so take three snapshots ~1.2s apart.
    batch_size = 80
    rounds = 3
    for rnd in range(rounds):
        stamp = now_tw()
        for i in range(0, len(recs), batch_size):
            part = recs[i:i+batch_size]
            ex_ch = "|".join(
                f"{'otc' if r['market'] == '上櫃' else 'tse'}_{r['code']}.tw"
                for r in part
            )
            try:
                diag["requests"] += 1
                rr = requests.get(
                    "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
                    params={"ex_ch": ex_ch, "json": "1", "delay": "0", "_": int(stamp.timestamp()*1000)+rnd*1000+i},
                    headers={
                        "User-Agent": "Mozilla/5.0 DogsonRadar/1.4.1",
                        "Referer": "https://mis.twse.com.tw/stock/index.jsp",
                        "Accept": "application/json,text/plain,*/*",
                    },
                    timeout=20,
                )
                rr.raise_for_status()
                arr = rr.json().get("msgArray") or []
                diag["msg_entries"] += len(arr)
                for x in arr:
                    code = str(x.get("c") or "").strip()
                    td = _parse_mis_trade_date(x.get("d"))
                    if not code or td != today:
                        continue
                    diag["today_entries"] += 1
                    tm = str(x.get("t") or "").strip()
                    if len(tm) >= 5:
                        tm = tm[:8]
                    prev = fnum(x.get("y"))
                    meta = {
                        "date": today_s,
                        "snapshot_time": tm,
                        "prev_close": prev,
                        "volume_lots": fnum(x.get("v")),
                        "market": x.get("ex"),
                    }
                    latest_meta[code] = meta
                    last = fnum(x.get("z"))
                    if last is not None and last > 0:
                        fresh[code] = {"close": last, "time": tm}
            except Exception as e:
                print("MIS intraday stock batch", rnd, i, e)
        if rnd < rounds-1:
            _time.sleep(1.2)

    out = {}
    for r in recs:
        code = r["code"]
        meta = latest_meta.get(code)
        if not meta:
            diag["missing"] += 1
            continue
        tr = fresh.get(code)
        carried = False
        if tr is None:
            tr = cached.get(code)
            carried = tr is not None
        if tr is None:
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
        if carried:
            diag["cached_z"] += 1
        else:
            diag["fresh_z"] += 1

    print("MIS intraday stock quotes", len(out), "/", len(recs), "fresh", diag["fresh_z"], "cached", diag["cached_z"])
    print("MIS_LAST_TRADE_DIAG", json.dumps(diag, ensure_ascii=False))
    return out

'''
p.write_text(s[:start]+new+s[end:],encoding='utf-8')
print('patched build_data.py last-trade cache')
