#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-time v1.3.7 patch: use official TPEx monthly history for the OTC index."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
build = ROOT / "scripts" / "build_data.py"
index = ROOT / "docs" / "index.html"

text = build.read_text(encoding="utf-8")

text = text.replace(
    "犬子老師飆股雷達 Free Edition v1.3.6",
    "犬子老師飆股雷達 Free Edition v1.3.7",
    1,
)

start = text.find("def index_state(symbol, label, snap=None):")
end = text.find("\ndef _market_num(x):", start)
if start < 0 or end < 0:
    raise SystemExit("index_state block not found")

new_block = r'''def _parse_tpex_index_date(value):
    """Parse TPEx index date defensively (Gregorian or ROC formats)."""
    s = str(value or "").strip()
    if not s:
        return None
    clean = s.replace("-", "/").replace(".", "/")
    parts = [p for p in clean.split("/") if p]
    try:
        if len(parts) == 3:
            y, m, d = map(int, parts)
            if y < 1911:
                y += 1911
            return datetime(y, m, d).date()
    except Exception:
        pass

    digits = "".join(ch for ch in s if ch.isdigit())
    try:
        if len(digits) == 8:
            y = int(digits[:4]); m = int(digits[4:6]); d = int(digits[6:8])
            return datetime(y, m, d).date()
        if len(digits) == 7:
            y = int(digits[:3]) + 1911; m = int(digits[3:5]); d = int(digits[5:7])
            return datetime(y, m, d).date()
    except Exception:
        return None
    return None


def _month_start(d, back=0):
    y = d.year
    m = d.month - int(back)
    while m <= 0:
        m += 12
        y -= 1
    return datetime(y, m, 1).date()


def tpex_index_history(months=4):
    """Official TPEx monthly history for the OTC index.

    The TPEx OpenAPI route can be blocked from GitHub-hosted runners.  The
    official historical endpoint /www/zh-tw/indexInfo/inx accepts a month and
    returns that month's daily OTC index OHLC values, so it is used as the
    primary source for MA5/10/20 and the market-environment score.
    """
    cutoff = _latest_completed_cutoff()
    frames = []
    url = "https://www.tpex.org.tw/www/zh-tw/indexInfo/inx"
    headers = {
        "User-Agent": "Mozilla/5.0 DogsonRadar/1.3.7",
        "Accept": "application/json,text/plain,*/*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://www.tpex.org.tw/zh-tw/index.html",
        "Origin": "https://www.tpex.org.tw",
    }

    for back in range(max(2, int(months))):
        first = _month_start(cutoff, back)
        try:
            rr = requests.post(
                url,
                data={"response": "json", "date": first.strftime("%Y/%m/%d")},
                headers=headers,
                timeout=25,
            )
            rr.raise_for_status()
            obj = rr.json()
            tables = obj.get("tables") or []
            if not tables:
                print("TPEx index no tables", first)
                continue
            table = tables[0] or {}
            fields = table.get("fields") or []
            data = table.get("data") or []
            if not fields or not data:
                print("TPEx index empty month", first)
                continue

            fmap = {str(v).strip(): i for i, v in enumerate(fields)}
            aliases = {
                "Date": ["日期", "Date"],
                "Open": ["開市", "開盤", "Open"],
                "High": ["最高", "High"],
                "Low": ["最低", "Low"],
                "Close": ["收市", "收盤", "Close"],
            }
            pos = {}
            for key, names in aliases.items():
                hit = next((fmap[n] for n in names if n in fmap), None)
                if hit is None:
                    raise ValueError(f"TPEx index missing {key}; fields={fields}")
                pos[key] = hit

            rows = []
            for row in data:
                if not isinstance(row, (list, tuple)):
                    continue
                try:
                    td = _parse_tpex_index_date(row[pos["Date"]])
                except Exception:
                    td = None
                if td is None or td > cutoff:
                    continue

                def num(key):
                    try:
                        s = str(row[pos[key]]).replace(",", "").replace("+", "").strip()
                        return float(s)
                    except Exception:
                        return None

                o, h, l, c = num("Open"), num("High"), num("Low"), num("Close")
                if c is None:
                    continue
                rows.append({
                    "Date": pd.Timestamp(td),
                    "Open": o if o is not None else c,
                    "High": h if h is not None else c,
                    "Low": l if l is not None else c,
                    "Close": c,
                    "Volume": 0.0,
                })
            if rows:
                f = pd.DataFrame(rows).set_index("Date")
                frames.append(f)
                print("TPEx official index month", first.strftime("%Y-%m"), len(f))
        except Exception as e:
            print("TPEx official index month failed", first, e)

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out


def index_state(symbol, label, snap=None):
    try:
        # OTC index uses official TPEx monthly history first because Yahoo ^TWOII
        # is intermittent. TWSE keeps Yahoo history with official MIS overlay.
        if symbol == "^TWOII":
            d = tpex_index_history()
            source = "TPEx official monthly history"
            if d is None or len(d) < 24:
                d = download_daily([symbol], "3mo").get(symbol)
                source = "Yahoo daily fallback"
        else:
            d = download_daily([symbol], "3mo").get(symbol)
            source = "Yahoo daily"

        if d is None or len(d) < 24:
            return None
        c = d["Close"].copy().dropna()
        if snap and snap.get("date") and snap.get("close"):
            td = datetime.strptime(str(snap["date"]), "%Y-%m-%d").date()
            hits = [idx for idx in c.index if pd.Timestamp(idx).date() == td]
            if hits:
                c.loc[hits[-1]] = float(snap["close"])
            else:
                c.loc[pd.Timestamp(td)] = float(snap["close"])
                c = c.sort_index()
            source = ("TPEx official history + MIS overlay" if symbol == "^TWOII" else "TWSE MIS overlay")
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
        return None
'''

text = text[:start] + new_block + text[end:]
build.write_text(text, encoding="utf-8")

html = index.read_text(encoding="utf-8")
html = html.replace(
    "Free Edition v1.3.6｜交易日一致性＋正式收盤覆核",
    "Free Edition v1.3.7｜交易日一致性＋櫃買官方指數",
    1,
)
index.write_text(html, encoding="utf-8")

print("v1.3.7 patch applied")
