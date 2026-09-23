#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-time source patch for Radar v1.4.1.

Goal: stop presenting a 30~40 minute delayed Yahoo 5m timestamp as the current
intraday structure.  MIS does not expose usable per-stock minute history on the
endpoints we tested, so v1.4.1 persists official MIS quote snapshots and merges
sampled 5-minute bars on top of Yahoo's delayed history.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")
    print("patched", path)


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"missing patch anchor: {label}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# build_data.py
# ---------------------------------------------------------------------------
p = "scripts/build_data.py"
s = read(p)
s = s.replace("犬子老師飆股雷達 Free Edition v1.4.0", "犬子老師飆股雷達 Free Edition v1.4.1")
s = s.replace('"version": "1.4.0-free"', '"version": "1.4.1-free"')

helper_anchor = "\ndef _weighted_pct(rows, predicate, weight_key=\"current_turnover\"):\n"
helpers = r'''

def _parse_intraday_quote_dt(q):
    """Convert an MIS quote's trading date/time to a naive Taipei datetime."""
    if not q:
        return None
    ds = str(q.get("date") or "").strip()
    ts = str(q.get("time") or "").strip()
    if not ds or len(ts) < 5:
        return None
    try:
        return datetime.strptime(f"{ds} {ts[:8]}", "%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            return datetime.strptime(f"{ds} {ts[:5]}", "%Y-%m-%d %H:%M")
        except Exception:
            return None


def update_mis_tick_history(quote_map):
    """Persist official MIS snapshots across stateless GitHub Actions runs.

    The file is deployed with Pages and pulled back by sync_live_data.py on the
    next run.  Duplicate non-trades are not appended, so illiquid stocks do not
    get a fake fresh timestamp.
    """
    today = now_tw().date().isoformat()
    obj = load_json("live_ticks.json", {})
    if str(obj.get("trade_date") or "") != today:
        obj = {"trade_date": today, "stocks": {}}
    stocks = obj.setdefault("stocks", {})
    appended = 0
    for code, q in (quote_map or {}).items():
        dt = _parse_intraday_quote_dt(q)
        if dt is None or dt.date().isoformat() != today:
            continue
        try:
            price = float(q.get("close"))
        except Exception:
            continue
        if not np.isfinite(price) or price <= 0:
            continue
        lots = q.get("volume_lots")
        try:
            cum_shares = max(0.0, float(lots) * 1000.0) if lots is not None else None
        except Exception:
            cum_shares = None
        item = {
            "ts": dt.isoformat(timespec="seconds"),
            "time": dt.strftime("%H:%M:%S"),
            "price": price,
            "cum_volume": cum_shares,
        }
        arr = stocks.setdefault(str(code), [])
        sig = (item["ts"], item["price"], item["cum_volume"])
        last_sig = None
        if arr:
            z = arr[-1]
            last_sig = (z.get("ts"), z.get("price"), z.get("cum_volume"))
        if sig != last_sig:
            arr.append(item)
            appended += 1
        # More than enough for one Taiwan cash session, while keeping JSON small.
        stocks[str(code)] = arr[-120:]
    obj["updated_at"] = now_tw().isoformat(timespec="seconds")
    obj["sample_count"] = sum(len(v) for v in stocks.values())
    dump("live_ticks.json", obj)
    print("MIS persisted snapshots", appended, "stocks", len(stocks))
    return obj


def _taipei_naive_intraday(x):
    if x is None or x.empty:
        return x
    y = x.copy()
    idx = pd.DatetimeIndex(pd.to_datetime(y.index))
    if idx.tz is not None:
        idx = idx.tz_convert(TW).tz_localize(None)
    y.index = idx
    return y.sort_index()


def merge_mis_snapshot_structure(x, code, history, quote=None):
    """Bridge delayed Yahoo history with persisted official MIS snapshots.

    These bars are *sampled* 5-minute bars, not exchange-complete tick OHLC.
    On the first observation after a Yahoo gap, the missing cumulative volume is
    attached to a bridge bar so today's VWAP/turnover are not left 30~40 minutes
    behind.  The row is explicitly labelled MIS快照橋接 until enough sampled bars
    exist to treat the recent structure as a normal sampled 5m sequence.
    """
    y = _taipei_naive_intraday(x)
    if y is None or y.empty:
        return x, {"source": "Yahoo 5分K備援", "time": None, "live_bar_count": 0, "approx": False}

    today = now_tw().date()
    arr = (((history or {}).get("stocks") or {}).get(str(code)) or [])
    ticks = []
    for z in arr:
        try:
            dt = datetime.fromisoformat(str(z.get("ts")))
            if dt.date() != today:
                continue
            px = float(z.get("price"))
            cv = z.get("cum_volume")
            cv = float(cv) if cv is not None else None
            if px > 0:
                ticks.append((dt.replace(tzinfo=None), px, cv))
        except Exception:
            continue

    # Ensure the current quote is represented even when the persisted file was empty.
    qdt = _parse_intraday_quote_dt(quote)
    if qdt is not None and qdt.date() == today:
        try:
            qpx = float(quote.get("close"))
            qcv = float(quote.get("volume_lots")) * 1000.0 if quote.get("volume_lots") is not None else None
            if qpx > 0 and not any(t[0] == qdt and t[1] == qpx and t[2] == qcv for t in ticks):
                ticks.append((qdt, qpx, qcv))
        except Exception:
            pass
    ticks.sort(key=lambda z: z[0])
    if not ticks:
        t = y.index[-1].strftime("%H:%M") if len(y) else None
        return y, {"source": "Yahoo 5分K備援", "time": t, "live_bar_count": 0, "approx": False}

    today_mask = np.array([pd.Timestamp(i).date() == today for i in y.index])
    y_today = y.loc[today_mask]
    if y_today.empty:
        last_yahoo = None
        yahoo_cum = 0.0
    else:
        last_yahoo = pd.Timestamp(y_today.index[-1]).to_pydatetime().replace(tzinfo=None)
        yahoo_cum = float(pd.to_numeric(y_today["Volume"], errors="coerce").fillna(0).sum())

    # Collapse multiple official snapshots inside the same 5-minute bucket.
    buckets = {}
    for dt, px, cv in ticks:
        bucket = pd.Timestamp(dt).floor("5min").to_pydatetime()
        rec = buckets.setdefault(bucket, {"prices": [], "cum": None, "last_dt": dt})
        rec["prices"].append(px)
        if cv is not None:
            rec["cum"] = cv
        if dt >= rec["last_dt"]:
            rec["last_dt"] = dt

    candidates = [(b, buckets[b]) for b in sorted(buckets) if last_yahoo is None or b > last_yahoo]
    if not candidates:
        t = y.index[-1].strftime("%H:%M") if len(y) else None
        return y, {"source": "Yahoo 5分K備援", "time": t, "live_bar_count": 0, "approx": False}

    prev_cum = yahoo_cum if last_yahoo is not None else None
    rows = []
    for bucket, rec in candidates:
        prices = rec["prices"]
        cv = rec.get("cum")
        if cv is not None and prev_cum is not None:
            vol = max(0.0, cv - prev_cum)
        else:
            vol = 0.0
        if cv is not None:
            prev_cum = cv
        rows.append((pd.Timestamp(bucket), {
            "Open": float(prices[0]), "High": float(max(prices)),
            "Low": float(min(prices)), "Close": float(prices[-1]),
            "Volume": float(vol),
        }))

    live = pd.DataFrame([r for _, r in rows], index=[i for i, _ in rows])
    y = pd.concat([y, live]).sort_index()
    y = y[~y.index.duplicated(keep="last")]
    live_count = len(live)
    first_live = live.index[0].to_pydatetime()
    gap_min = ((first_live - last_yahoo).total_seconds() / 60.0) if last_yahoo is not None else None
    # If the first official sample jumped over more than one expected 5m bucket,
    # be explicit that it is a bridge. After 4 recent samples, the last 15m logic
    # is based on the official sample sequence rather than the delayed gap.
    approx = bool((gap_min is not None and gap_min > 10) and live_count < 4)
    source = "MIS快照橋接" if approx else "MIS快照5分K"
    return y, {
        "source": source,
        "time": rows[-1][0].strftime("%H:%M"),
        "live_bar_count": live_count,
        "gap_min": round(gap_min, 1) if gap_min is not None else None,
        "approx": approx,
    }

'''
if "def update_mis_tick_history(" not in s:
    s = replace_once(s, helper_anchor, helpers + helper_anchor, "live structure helpers")

old_intra_start = s.index("def intraday_technical(x):")
old_intra_end = s.index("\ndef add_component_scores", old_intra_start)
new_intra = r'''def intraday_technical(x, official_cum_volume=None, official_time=None):
    # 開盤早段也要能掃描；累積至少 4 根 5 分K 即可開始判斷。
    if len(x) < 4:
        return None
    x = _taipei_naive_intraday(x)
    latest = x.index[-1].date()
    today = x[x.index.date == latest]
    prev = x[x.index.date < latest]
    if len(today) < 3:
        return None

    c, h, v = today["Close"], today["High"], today["Volume"]
    cur = float(c.iloc[-1])
    typical = (today["High"] + today["Low"] + today["Close"]) / 3
    turnover_s = typical * v
    vwap_s = turnover_s.cumsum() / v.cumsum().replace(0, np.nan)
    vwap = float(vwap_s.iloc[-1]) if pd.notna(vwap_s.iloc[-1]) else cur

    p3 = h.shift(1).rolling(3).max()
    p12 = h.shift(1).rolling(12).max()
    b3 = bool(cur > p3.iloc[-1]) if pd.notna(p3.iloc[-1]) else False
    b12 = bool(cur > p12.iloc[-1]) if pd.notna(p12.iloc[-1]) else False
    ma5, ma10 = c.rolling(5).mean(), c.rolling(10).mean()
    if pd.notna(ma10.iloc[-1]):
        trend = bool(cur > ma5.iloc[-1] > ma10.iloc[-1])
    elif pd.notna(ma5.iloc[-1]):
        trend = bool(cur > ma5.iloc[-1])
    else:
        trend = bool(cur >= float(c.iloc[0]))

    # Volume pace: when MIS cumulative volume/time are available, compare against
    # the same elapsed clock time on previous days instead of the delayed Yahoo
    # bar count. This avoids a 10:45 structure being compared as if it were 11:25.
    target_n = len(today)
    if official_time and len(str(official_time)) >= 5:
        try:
            hh, mm = map(int, str(official_time)[:5].split(":"))
            elapsed = max(0, hh * 60 + mm - 9 * 60)
            target_n = max(1, min(55, elapsed // 5 + 1))
        except Exception:
            target_n = len(today)
    vals = []
    for d in sorted(set(prev.index.date))[-4:]:
        z = prev[prev.index.date == d]
        if len(z) >= target_n:
            vals.append(float(z["Volume"].iloc[:target_n].sum()))
    if official_cum_volume is not None and vals and np.median(vals) > 0:
        pace = float(official_cum_volume / np.median(vals))
    else:
        n = len(today)
        vals2 = []
        for d in sorted(set(prev.index.date))[-4:]:
            z = prev[prev.index.date == d]
            if len(z) >= n:
                vals2.append(float(z["Volume"].iloc[:n].sum()))
        pace = float(v.sum() / np.median(vals2)) if vals2 and np.median(vals2) > 0 else 1.0

    if not prev.empty:
        d = sorted(set(prev.index.date))[-1]
        prev_close = float(prev[prev.index.date == d]["Close"].iloc[-1])
    else:
        prev_close = float(c.iloc[0])
    day_change = (cur / prev_close - 1) * 100 if prev_close else 0

    # Only call it a 15-minute move when the four observations really span about
    # 15 minutes. A Yahoo->MIS bridge can otherwise span 30~40 minutes.
    ret15 = 0.0
    if len(c) >= 4:
        span_min = (today.index[-1] - today.index[-4]).total_seconds() / 60.0
        if span_min <= 20:
            ret15 = (c.iloc[-1] / c.iloc[-4] - 1) * 100
    vwap_dist = (cur / vwap - 1) * 100 if vwap else 0

    current_turnover = float(turnover_s.sum())
    pair_n = min(6, len(today) // 2)
    regular_recent = False
    if pair_n >= 3 and len(today) >= pair_n * 2:
        dts = today.index[-pair_n * 2:]
        gaps = [(dts[i] - dts[i-1]).total_seconds() / 60 for i in range(1, len(dts))]
        regular_recent = bool(gaps and max(gaps) <= 10)
    if pair_n >= 3 and regular_recent:
        recent_turnover = float(turnover_s.iloc[-pair_n:].sum())
        previous_turnover = float(turnover_s.iloc[-2 * pair_n:-pair_n].sum())
        rotation_window_min = int(pair_n * 5)
    else:
        recent_turnover = None
        previous_turnover = None
        rotation_window_min = None

    score = 0
    reasons = []
    if cur > vwap:
        score += 8; reasons.append("站上VWAP")
    if b3:
        score += 8; reasons.append("3K突破")
    if b12:
        score += 6; reasons.append("60分突破")
    if trend:
        score += 7; reasons.append("5分K短均多頭")
    if 1.5 <= pace < 3.5:
        score += 10; reasons.append(f"量速{pace:.1f}x")
    elif 1.2 <= pace < 1.5:
        score += 5; reasons.append(f"量速{pace:.1f}x")
    elif 3.5 <= pace <= 5:
        score += 6; reasons.append(f"大量速{pace:.1f}x")
    if 1 <= day_change <= 6.5:
        score += 5
    if .2 <= ret15 <= 2.5:
        score += 6; reasons.append("短線動能")

    over = []
    if day_change >= 8.5:
        score -= 10; over.append("接近漲停/漲幅過熱")
    if vwap_dist > 4.5:
        score -= 6; over.append("離VWAP過遠")
    if pace > 5:
        score -= 5; over.append("量速極端")
    if ret15 > 4:
        score -= 5; over.append("15分鐘急拉")

    sr = intraday_sr(x, vwap)
    return {
        "date": str(latest), "time": x.index[-1].strftime("%H:%M"),
        "close": cur, "pace": round(pace, 2), "vwap": round(vwap, 2),
        "vwap_dist": round(vwap_dist, 2), "day_change": round(day_change, 2),
        "break3": b3, "break12": b12, "trend5": trend,
        "current_turnover": round(current_turnover, 0),
        "recent_turnover": round(recent_turnover, 0) if recent_turnover is not None else None,
        "previous_turnover": round(previous_turnover, 0) if previous_turnover is not None else None,
        "rotation_window_min": rotation_window_min,
        "technical_score": max(0, min(50, round(score, 1))),
        "reasons": reasons, "overheat_reasons": over, **sr,
    }
'''
s = s[:old_intra_start] + new_intra + s[old_intra_end:]

build_start = s.index("def build_intraday():")
build_end = s.index("\ndef main():", build_start)
new_build = r'''def build_intraday():
    close_obj = load_json("close.json", {"rows": []})
    close_rows = close_obj.get("rows", [])
    market = load_json("market.json", close_obj.get("market", {}))
    universe_list = load_json("universe.json", [])

    if not universe_list:
        uni = get_universe()
        universe_list = uni[["code", "name", "industry", "market"]].astype(str).to_dict("records")
        dump("universe.json", universe_list)

    u = pd.DataFrame(universe_list)
    if u.empty:
        raise RuntimeError("沒有股票清單")
    u["symbol"] = u["code"].astype(str) + np.where(u["market"].eq("上櫃"), ".TWO", ".TW")
    code_to_sym = dict(zip(u["code"].astype(str), u["symbol"]))
    meta = u.set_index("symbol").to_dict("index")

    watch = (ROOT / "config" / "watchlist.txt").read_text(encoding="utf-8").splitlines()
    watch = [x.strip() for x in watch if x.strip() and not x.strip().startswith("#")]
    pool = [code_to_sym[c] for c in watch if c in code_to_sym]
    pool += [code_to_sym[r["code"]] for r in close_rows if r.get("code") in code_to_sym]
    pool = list(dict.fromkeys(pool))

    # Fetch official MIS first, persist it, then use the fresh snapshots to bridge
    # the delayed Yahoo 5m history in this same build.
    pool_codes = [str(meta.get(sym, {}).get("code", sym.split(".")[0])) for sym in pool]
    quote_map = intraday_stock_snapshot(u, pool_codes)
    live_history = update_mis_tick_history(quote_map)

    close_map = {str(r["code"]): r for r in close_rows}
    rows = []

    for i in range(0, len(pool), 60):
        part = pool[i:i+60]
        try:
            data = download_intraday(part)
        except Exception as e:
            print("intra batch", i, e)
            continue

        for sym, x in data.items():
            try:
                m = meta.get(sym, {})
                code = str(m.get("code", sym.split(".")[0]))
                q = quote_map.get(code)
                merged, smeta = merge_mis_snapshot_structure(x, code, live_history, q)
                cum_shares = None
                if q and q.get("volume_lots") is not None:
                    try: cum_shares = float(q.get("volume_lots")) * 1000.0
                    except Exception: cum_shares = None
                t = intraday_technical(
                    merged,
                    official_cum_volume=cum_shares,
                    official_time=(q or {}).get("time"),
                )
                if not t:
                    continue
                t["structure_time"] = smeta.get("time") or t.get("time")
                t["structure_source"] = smeta.get("source")
                t["structure_live_bars"] = smeta.get("live_bar_count", 0)
                t["structure_gap_min"] = smeta.get("gap_min")
                t["structure_approx"] = bool(smeta.get("approx"))
                prev = close_map.get(code, {})
                rows.append({
                    "symbol": sym,
                    "code": code,
                    "name": str(m.get("name", sym)),
                    "industry": str(m.get("industry", "未分類")),
                    "industry_name": str(m.get("industry_name", industry_name_for(m.get("industry")))),
                    "sector_group": str(m.get("sector_group") or sector_group_for(code, m.get("name"), m.get("industry")) or ""),
                    "market": str(m.get("market", "")),
                    **t,
                    "chip_date": prev.get("chip_date"),
                    "foreign_3buy": prev.get("foreign_3buy"),
                    "foreign_net_latest": prev.get("foreign_net_latest"),
                    "foreign_3d_net": prev.get("foreign_3d_net"),
                    "sbl_3down": prev.get("sbl_3down"),
                    "sbl_3change_pct": prev.get("sbl_3change_pct"),
                    "trust_net_latest": prev.get("trust_net_latest"),
                    "margin_3d_pct": prev.get("margin_3d_pct"),
                    "margin_status": prev.get("margin_status"),
                    "chip_combo": prev.get("chip_combo"),
                    "chip_score": prev.get("chip_score", 12.5),
                    "chip_coverage_pct": prev.get("chip_coverage_pct", 0),
                    "avg_turnover20": prev.get("avg_turnover20"),
                    "avg_turnover20_mn": prev.get("avg_turnover20_mn"),
                    "liquidity_level": prev.get("liquidity_level", "未知"),
                    "liquidity_adjust": prev.get("liquidity_adjust", 0),
                })
            except Exception as e:
                print("intra stock", sym, e)

    if not rows:
        previous = load_json("intraday.json", {})
        if previous.get("rows"):
            previous["stale"] = True
            previous["attempted_at"] = now_tw().isoformat(timespec="seconds")
            previous["note"] = "本輪資料源暫時沒有有效盤中結構，已保留上一輪資料。"
            dump("intraday.json", previous)
            status = load_json("status.json", {})
            status.update({
                "updated_at": now_tw().isoformat(timespec="seconds"),
                "intraday_attempted_at": now_tw().isoformat(timespec="seconds"),
                "intraday_count": len(previous.get("rows", [])),
                "version": "1.4.1-free",
            })
            dump("status.json", status)
            print("intraday source empty; kept previous", len(previous.get("rows", [])))
            return

    # Last-price overlay remains official MIS. Structure freshness/source is kept
    # separate and is never silently labelled as a true exchange 5m bar.
    row_codes = {str(r.get("code")) for r in rows}
    relevant_quotes = {c: q for c, q in quote_map.items() if c in row_codes}
    structure_times = []
    mis_structure_count = 0
    bridge_count = 0
    for r in rows:
        r["structure_close"] = r.get("close")
        if r.get("structure_time"):
            structure_times.append(str(r.get("structure_time"))[:5])
        if str(r.get("structure_source") or "").startswith("MIS"):
            mis_structure_count += 1
        if r.get("structure_approx"):
            bridge_count += 1
        q = relevant_quotes.get(str(r.get("code")))
        if not q:
            continue
        r["quote_date"] = q.get("date")
        r["quote_time"] = q.get("time")
        r["quote_source"] = q.get("source")
        r["quote_close"] = q.get("close")
        r["close"] = q.get("close")
        if q.get("change_pct") is not None:
            r["day_change"] = round(float(q.get("change_pct")), 2)
        if r.get("vwap"):
            try: r["vwap_dist"] = round((float(r["close"]) / float(r["vwap"]) - 1) * 100, 2)
            except Exception: pass

    quote_times = [str(q.get("time") or "")[:5] for q in relevant_quotes.values() if q.get("time")]
    quote_latest = max(quote_times) if quote_times else None
    structure_latest = max(structure_times) if structure_times else None

    market_live = intraday_index_snapshot()
    sector_rotation = build_sector_rotation(rows)
    intraday_market = build_intraday_market(rows, market_live, sector_rotation, market)
    rows = add_component_scores(rows, intraday_market, preliminary_intraday=True)

    dump("intraday.json", {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "market": intraday_market,
        "market_intraday": market_live,
        "sector_rotation": sector_rotation,
        "quote_layer": {
            "source": "TWSE MIS", "coverage": len(relevant_quotes), "row_count": len(rows),
            "latest_time": quote_latest, "structure_latest_time": structure_latest,
            "mis_structure_count": mis_structure_count, "bridge_count": bridge_count,
            "structure_source": "MIS快照5分K＋Yahoo歷史備援",
            "note": "即時價採官方MIS；技術結構以持續累積的MIS快照補上Yahoo延遲區段。橋接初期為取樣近似，不冒充逐筆完整5分K。",
        },
        "score_formula": {"technical": 50, "chip": 25, "sector": 10, "stock_raw_max": 85, "normalized_to": 100, "market_separate": 15},
        "rows": rows,
    })

    status = load_json("status.json", {})
    status.update({
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "intraday_updated_at": now_tw().isoformat(timespec="seconds"),
        "intraday_count": len(rows),
        "version": "1.4.1-free",
    })
    dump("status.json", status)
    print("intraday done", len(rows), "MIS structure", mis_structure_count, "bridges", bridge_count)
'''
s = s[:build_start] + new_build + s[build_end:]
write(p, s)


# ---------------------------------------------------------------------------
# sync_live_data.py: persist MIS samples between Actions runs.
# ---------------------------------------------------------------------------
p = "scripts/sync_live_data.py"
s = read(p)
if '"live_ticks.json"' not in s:
    s = s.replace('"chip_history.json", "chip_status.json",', '"chip_history.json", "chip_status.json", "live_ticks.json",')
write(p, s)


# ---------------------------------------------------------------------------
# index.html: distinguish official quote time from sampled technical structure.
# ---------------------------------------------------------------------------
p = "docs/index.html"
s = read(p)
s = s.replace("Free Edition v1.4.0｜官方即時價＋獨立大盤＋多因子族群", "Free Edition v1.4.1｜官方即時價＋MIS快照技術＋獨立大盤")
s = s.replace("Free Edition v1.4.0", "Free Edition v1.4.1")
s = s.replace("5分K結構", "技術結構")
s = s.replace("VWAP、量速、突破、支撐壓力與階段仍以5分K計算，避免逐筆雜訊讓訊號一直跳。", "VWAP、量速、突破與支撐壓力以Yahoo歷史5分K為底，再用每輪官方MIS快照補上最新區段；剛開始累積時會標示MIS快照橋接，不把取樣近似冒充逐筆完整K線。")
old_metric = 'if(mode==="intraday")return [["現價",num(r.close,2)],["行情時間",r.quote_time||r.time||"—"],["技術結構",r.structure_time||r.time||"—"],["同時間量速",num(r.pace,1)+"x"]'
new_metric = 'if(mode==="intraday")return [["現價",num(r.close,2)],["行情時間",r.quote_time||r.time||"—"],[(r.structure_source||"").includes("橋接")?"MIS快照橋接":((r.structure_source||"").startsWith("MIS")?"MIS快照結構":"技術結構"),r.structure_time||r.time||"—"],["同時間量速",num(r.pace,1)+"x"]'
if old_metric in s:
    s = s.replace(old_metric, new_metric, 1)
write(p, s)


# ---------------------------------------------------------------------------
# realtime.js labels: price is 10s near-real-time; structure comes from v1.4.1.
# ---------------------------------------------------------------------------
p = "docs/realtime.js"
s = read(p)
s = s.replace("5分K結構", "技術結構")
s = s.replace("TWSE MIS｜結構仍採5分K", "TWSE MIS｜技術結構另計")
s = s.replace("每10秒｜5分K結構分開顯示", "每10秒｜技術結構分開顯示")
s = s.replace("5分K雷達仍可用", "技術雷達仍可用")
write(p, s)


# ---------------------------------------------------------------------------
# PWA cache bump.
# ---------------------------------------------------------------------------
p = "docs/sw.js"
s = read(p)
s = s.replace("dogson-free-v140", "dogson-free-v141")
s = s.replace("realtime-config.js?v=140", "realtime-config.js?v=141")
s = s.replace("realtime.js?v=140", "realtime.js?v=141")
write(p, s)

print("v1.4.1 patch complete")
