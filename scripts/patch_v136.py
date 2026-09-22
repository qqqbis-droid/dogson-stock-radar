#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply v1.3.6: completed-trading-day consistency and close-mode UI repair."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_data.py"
HTML = ROOT / "docs" / "index.html"
RT = ROOT / "docs" / "realtime.js"
SW = ROOT / "docs" / "sw.js"


def must_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"marker not found: {label}")
    return text.replace(old, new, 1)


def regex_replace(text: str, pattern: str, replacement: str, label: str) -> str:
    new, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError(f"regex replace failed {label}: {n}")
    return new


NEW_MIS = r'''def _latest_completed_cutoff():
    """Latest calendar date that may contain a fully completed Taiwan cash session."""
    now = now_tw()
    # Before 13:35, today's cash session is not considered completed.  This also
    # fixes the midnight/08:15 rebuild case: 9/23 should still accept 9/22 data.
    if (now.hour, now.minute) < (13, 35):
        return now.date() - timedelta(days=1)
    return now.date()


def _parse_mis_trade_date(raw):
    s = str(raw or "").strip().replace("-", "").replace("/", "")
    if len(s) != 8 or not s.isdigit():
        return None
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except Exception:
        return None


def official_mis_snapshot(uni):
    """Use TWSE MIS to overlay the latest *completed* official OHLCV session."""
    now = now_tw()
    cutoff = _latest_completed_cutoff()
    out = {}
    recs = uni[["code", "market"]].astype(str).to_dict("records")
    for i in range(0, len(recs), 80):
        part = recs[i:i+80]
        ex_ch = "|".join(
            f"{'otc' if r['market'] == '上櫃' else 'tse'}_{r['code']}.tw"
            for r in part
        )
        try:
            rr = requests.get(
                "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
                params={"ex_ch": ex_ch, "json": "1", "delay": "0", "_": int(now.timestamp()*1000)},
                headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.6", "Referer": "https://mis.twse.com.tw/stock/index.jsp"},
                timeout=20,
            )
            rr.raise_for_status()
            arr = rr.json().get("msgArray") or []
            for x in arr:
                code = str(x.get("c") or "").strip()
                trade_date = _parse_mis_trade_date(x.get("d"))
                if not code or trade_date is None or trade_date > cutoff:
                    continue
                # Ignore obviously stale snapshots; holidays/weekends are still safe.
                if (cutoff - trade_date).days > 10:
                    continue
                def f(k):
                    try:
                        v = str(x.get(k) or "").replace(",", "").strip()
                        return float(v) if v not in {"", "-", "--"} else None
                    except Exception:
                        return None
                z, o, h, l, v = f("z"), f("o"), f("h"), f("l"), f("v")
                if z is None or z <= 0:
                    continue
                out[code] = {
                    "date": trade_date, "Close": z,
                    "Open": o if o and o > 0 else z,
                    "High": h if h and h > 0 else z,
                    "Low": l if l and l > 0 else z,
                    # MIS v is lots; Yahoo daily Volume is shares.
                    "Volume": (v * 1000.0) if v is not None else None,
                }
        except Exception as e:
            print("MIS close batch", i, e)

    # One build must never mix trading dates. Keep only the newest completed date.
    if out:
        latest = max(v["date"] for v in out.values())
        out = {k: v for k, v in out.items() if v["date"] == latest}
        print("official MIS close snapshot", len(out), "trade_date", latest)
    else:
        print("official MIS close snapshot 0")
    return out


def official_index_snapshot():
    """Completed-session TWSE/TPEx index closes from TWSE MIS."""
    now = now_tw()
    cutoff = _latest_completed_cutoff()
    out = {}
    try:
        rr = requests.get(
            "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
            params={"ex_ch": "tse_t00.tw|otc_o00.tw", "json": "1", "delay": "0", "_": int(now.timestamp()*1000)},
            headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.6", "Referer": "https://mis.twse.com.tw/stock/index.jsp"},
            timeout=15,
        )
        rr.raise_for_status()
        for x in rr.json().get("msgArray") or []:
            ch = str(x.get("ch") or x.get("ex") or "")
            name = str(x.get("n") or "")
            key = None
            if "tse_t00" in ch or "發行量加權" in name:
                key = "^TWII"
            elif "otc_o00" in ch or "櫃買" in name:
                key = "^TWOII"
            if not key:
                continue
            trade_date = _parse_mis_trade_date(x.get("d"))
            if trade_date is None or trade_date > cutoff or (cutoff - trade_date).days > 10:
                continue
            try:
                cur = float(str(x.get("z") or "").replace(",", ""))
                prev = float(str(x.get("y") or "").replace(",", ""))
            except Exception:
                continue
            if cur <= 0:
                continue
            out[key] = {
                "date": trade_date.isoformat(),
                "close": cur,
                "prev_close": prev if prev > 0 else None,
                "change_pct": ((cur / prev - 1) * 100) if prev > 0 else None,
                "source": "TWSE MIS completed session",
            }
    except Exception as e:
        print("MIS completed index", e)
    return out'''


NEW_INDEX_STATE = r'''def index_state(symbol, label, snap=None):
    try:
        d = download_daily([symbol], "3mo").get(symbol)
        if d is None or len(d) < 24:
            return None
        c = d["Close"].copy().dropna()
        source = "Yahoo daily"
        if snap and snap.get("date") and snap.get("close"):
            td = datetime.strptime(str(snap["date"]), "%Y-%m-%d").date()
            hits = [idx for idx in c.index if pd.Timestamp(idx).date() == td]
            if hits:
                c.loc[hits[-1]] = float(snap["close"])
            else:
                c.loc[pd.Timestamp(td)] = float(snap["close"])
                c = c.sort_index()
            source = "TWSE MIS overlay"
        if len(c) < 25:
            return None
        ma5 = float(c.rolling(5).mean().iloc[-1])
        ma10 = float(c.rolling(10).mean().iloc[-1])
        ma20 = float(c.rolling(20).mean().iloc[-1])
        close = float(c.iloc[-1])
        if snap and snap.get("date") == str(c.index[-1].date()) and snap.get("change_pct") is not None:
            change = float(snap["change_pct"])
        else:
            change = float((c.iloc[-1]/c.iloc[-2]-1)*100)
        return {
            "label": label, "symbol": symbol, "close": round(close, 2),
            "change_pct": round(change, 2),
            "ma5": round(ma5, 2), "ma10": round(ma10, 2), "ma20": round(ma20, 2),
            "trend": bool(close > ma5 > ma10 > ma20),
            "above20": bool(close > ma20),
            "date": str(c.index[-1].date()), "source": source,
        }
    except Exception as e:
        print("index", symbol, e)
        return None'''


NEW_BUILD_MARKET = r'''def build_market(breadth_pct, chips=None, expected_trade_date=None):
    expected = expected_trade_date.isoformat() if hasattr(expected_trade_date, "isoformat") else (str(expected_trade_date) if expected_trade_date else None)
    idx = official_index_snapshot()
    taiex = index_state("^TWII", "加權", idx.get("^TWII"))
    otc = index_state("^TWOII", "櫃買", idx.get("^TWOII"))

    # Never combine index data from a different session into one market score.
    if expected and taiex and taiex.get("date") != expected:
        print("market date mismatch taiex", taiex.get("date"), expected)
        taiex = None
    if expected and otc and otc.get("date") != expected:
        print("market date mismatch otc", otc.get("date"), expected)
        otc = None

    foreign = fetch_market_foreign_flow()
    foreign_same_day = bool(expected and foreign.get("date") == expected)
    foreign_score = _foreign_market_score(foreign) if (foreign_same_day or not expected) else 1.5

    score = 0.0
    if taiex:
        score += 5 if taiex["trend"] else 2.5 if taiex["above20"] else 0
    else:
        score += 2.5
    if otc:
        score += 4 if otc["trend"] else 2 if otc["above20"] else 0
    else:
        score += 2
    if breadth_pct is not None:
        if breadth_pct >= 60: score += 3
        elif breadth_pct >= 55: score += 2.5
        elif breadth_pct >= 50: score += 1.5
        elif breadth_pct >= 45: score += 0.5
    else:
        score += 1.5
    score += foreign_score

    score = round(min(15, score), 1)
    complete = bool(expected and taiex and otc and breadth_pct is not None and foreign_same_day)
    mode = ("偏多" if score >= 11 else "中性" if score >= 7 else "防守") if complete else "資料待補"
    threshold = 70 if mode == "偏多" else 76 if mode == "中性" else 82

    def billion(v):
        return round(v / 100_000_000, 1) if v is not None else None

    return {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "trade_date": expected,
        "data_complete": complete,
        "market_score": score,
        "market_mode": mode,
        "radar_threshold": threshold,
        "breadth_up_pct": round(breadth_pct, 1) if breadth_pct is not None else None,
        "foreign_date": foreign.get("date"),
        "foreign_same_trade_date": foreign_same_day,
        "foreign_net_billion": billion(foreign.get("total_net")),
        "foreign_twse_billion": billion(foreign.get("twse_net")),
        "foreign_tpex_billion": billion(foreign.get("tpex_net")),
        "foreign_5d_billion": billion(foreign.get("five_day_net")),
        "foreign_5d_count": int(foreign.get("count") or 0),
        "foreign_score": foreign_score,
        "foreign_source": "TWSE BFI82U + TPEx 三大法人買賣金額彙總表",
        "taiex": taiex,
        "otc": otc,
        "score_max": 15,
        "explain": {
            "taiex": "加權趨勢最多5分",
            "otc": "櫃買趨勢最多4分",
            "breadth": "上漲家數比最多3分",
            "foreign": "官方外資現貨：同交易日當日方向最多2分＋近5日累計最多1分",
        },
    }'''


build = BUILD.read_text(encoding="utf-8")
build = build.replace("Free Edition v1.3.5", "Free Edition v1.3.6")

build = regex_replace(
    build,
    r'def official_mis_snapshot\(uni\):.*?\n\ndef overlay_official_today_bar',
    NEW_MIS + '\n\ndef overlay_official_today_bar',
    "completed MIS snapshot",
)

build = regex_replace(
    build,
    r'def index_state\(symbol, label\):.*?\n\ndef _market_num',
    NEW_INDEX_STATE + '\n\ndef _market_num',
    "index state overlay",
)

build = regex_replace(
    build,
    r'def build_market\(breadth_pct, chips=None\):.*?\n\ndef intraday_sr',
    NEW_BUILD_MARKET + '\n\ndef intraday_sr',
    "market date consistency",
)

build = must_replace(
    build,
    '    official_today = official_mis_snapshot(uni)\n\n    rows = []',
    '    official_today = official_mis_snapshot(uni)\n    official_trade_date = max((v.get("date") for v in official_today.values() if v.get("date")), default=None)\n\n    rows = []',
    "official trade date",
)

build = must_replace(
    build,
    '    market_map = dict(zip(uni["code"].astype(str), uni["market"].astype(str)))\n',
    '    # Lock the entire close radar to one completed trading date.  If MIS is temporarily\n    # unavailable, use the newest date present in downloaded daily data, then discard older rows.\n    trade_date = official_trade_date\n    if trade_date is None and rows:\n        try:\n            trade_date = max(datetime.strptime(str(r.get("date")), "%Y-%m-%d").date() for r in rows if r.get("date"))\n        except Exception:\n            trade_date = None\n    if trade_date is not None:\n        td = trade_date.isoformat()\n        before = len(rows)\n        rows = [r for r in rows if str(r.get("date")) == td]\n        print("close trade-date lock", td, "kept", len(rows), "of", before)\n\n    market_map = dict(zip(uni["code"].astype(str), uni["market"].astype(str)))\n',
    "close trade date lock",
)

build = must_replace(
    build,
    '    breadth_pct = None\n    if breadth_changes:\n        breadth_pct = sum(1 for x in breadth_changes if x > 0) / len(breadth_changes) * 100\n\n    market = build_market(breadth_pct, chips)\n',
    '    # Recompute breadth only from the rows that survived the same-date lock.\n    breadth_changes = [float(r.get("day_change", 0)) for r in rows]\n    breadth_pct = None\n    if breadth_changes:\n        breadth_pct = sum(1 for x in breadth_changes if x > 0) / len(breadth_changes) * 100\n\n    market = build_market(breadth_pct, chips, trade_date)\n',
    "same-date breadth market",
)

build = must_replace(
    build,
    '        r["market_score"] = market_score\n        r["market_mode"] = market.get("market_mode", "中性")\n',
    '        r["market_score"] = market_score\n        r["market_mode"] = market.get("market_mode", "中性")\n        r["market_data_complete"] = bool(market.get("data_complete", True))\n        r["market_trade_date"] = market.get("trade_date")\n',
    "row market reliability fields",
)

build = must_replace(
    build,
    '        r["score_reliable"] = bool(chip_cov >= 60)\n',
    '        same_day = (not r.get("market_trade_date")) or str(r.get("date")) == str(r.get("market_trade_date"))\n        r["score_reliable"] = bool(chip_cov >= 60 and r.get("market_data_complete", True) and same_day)\n',
    "score reliability includes market date",
)

build = must_replace(
    build,
    '        "updated_at": now_tw().isoformat(timespec="seconds"),\n        "market": market,\n',
    '        "updated_at": now_tw().isoformat(timespec="seconds"),\n        "trade_date": market.get("trade_date"),\n        "data_complete": bool(market.get("data_complete")),\n        "market": market,\n',
    "close payload trade date",
)

build = build.replace('"version": "1.3.4-free"', '"version": "1.3.6-free"')
BUILD.write_text(build, encoding="utf-8")

html = HTML.read_text(encoding="utf-8")
html = html.replace("Free Edition v1.3.5", "Free Edition v1.3.6")
html = html.replace("整數籌碼＋族群代理＋強化支撐壓力", "交易日一致性＋正式收盤覆核")
html = html.replace('src="./realtime-config.js?v=130"', 'src="./realtime-config.js?v=136"')
html = html.replace('src="./realtime.js?v=130"', 'src="./realtime.js?v=136"')
html = html.replace(
    '<div class="marketscore">${num(m.market_score,1)}/15</div><div class="label">盤後大盤分</div>',
    '<div class="marketscore">${m.data_complete===false?"待補":num(m.market_score,1)+"/15"}</div><div class="label">盤後大盤分</div>'
)
html = html.replace(
    '<div class="marketmode ${modeClass}">📊 盤後市場：${m.market_mode||"—"}</div><div class="sub">品質參考線：${m.radar_threshold||"—"}分</div>',
    '<div class="marketmode ${modeClass}">📊 盤後市場：${m.market_mode||"—"}</div><div class="sub">交易日 ${m.trade_date||"待確認"}｜${m.data_complete===false?"資料未齊，不採信總分":"同交易日資料已核對"}</div>'
)
html = html.replace(
    '<div class="part"><div class="partv">${num(r.market_score,0)}/15</div><div class="partl">大盤</div></div>',
    '<div class="part"><div class="partv">${r.market_data_complete===false?"待補":num(r.market_score,0)+"/15"}</div><div class="partl">大盤${r.market_data_complete===false?" · 日期未齊":""}</div></div>'
)
html = html.replace(
    '"盤後：日K / 籌碼 / 大盤 / 支撐壓力"',
    '"盤後：正式收盤日K / 籌碼 / 同交易日大盤 / 支撐壓力"'
)
HTML.write_text(html, encoding="utf-8")

rt = RT.read_text(encoding="utf-8")
rt = must_replace(
    rt,
    "  function applyQuotes(){\n    ensureStyles();\n    document.querySelectorAll('.card').forEach(card=>{",
    "  function applyQuotes(){\n    ensureStyles();\n    const liveEl=document.getElementById('liveStatus');\n    if(typeof mode!=='undefined'&&mode!=='intraday'){\n      if(liveEl)liveEl.style.display='none';\n      document.querySelectorAll('.livequote').forEach(x=>x.remove());\n      return;\n    }\n    if(liveEl)liveEl.style.display='block';\n    document.querySelectorAll('.card').forEach(card=>{",
    "hide live quotes on close tab",
)
rt = must_replace(
    rt,
    "    if(typeof mode!=='undefined'&&mode!=='intraday')return;",
    "    if(typeof mode!=='undefined'&&mode!=='intraday'){applyQuotes();return;}",
    "refresh close cleanup",
)
RT.write_text(rt, encoding="utf-8")

sw = SW.read_text(encoding="utf-8")
sw = re.sub(r"const CACHE='dogson-free-v\d+';", "const CACHE='dogson-free-v136';", sw, count=1)
sw = sw.replace("./realtime-config.js?v=130", "./realtime-config.js?v=136")
sw = sw.replace("./realtime.js?v=130", "./realtime.js?v=136")
SW.write_text(sw, encoding="utf-8")

print("v1.3.6 patch applied")
