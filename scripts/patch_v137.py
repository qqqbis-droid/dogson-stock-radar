#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-time v1.3.7 patch: use official TPEx OpenAPI history for the OTC index."""
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
    """Parse TPEx OpenAPI Date defensively (Gregorian or ROC formats)."""
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


def tpex_index_history():
    """Official TPEx OpenAPI history for the OTC index.

    Yahoo's ^TWOII feed is intermittent.  The official TPEx endpoint exposes
    Date/Open/High/Low/Close and is therefore the canonical daily history used
    for the market-environment score.
    """
    try:
        rr = requests.get(
            "https://www.tpex.org.tw/openapi/v1/tpex_index",
            headers={
                "User-Agent": "Mozilla/5.0 DogsonRadar/1.3.7",
                "Accept": "application/json,text/plain,*/*",
                "Referer": "https://www.tpex.org.tw/",
            },
            timeout=30,
        )
        rr.raise_for_status()
        rows = rr.json()
        if not isinstance(rows, list) or not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        required = ["Date", "Open", "High", "Low", "Close"]
        if any(c not in df.columns for c in required):
            print("TPEx index schema mismatch", list(df.columns))
            return pd.DataFrame()

        parsed = df["Date"].map(_parse_tpex_index_date)
        out = pd.DataFrame(index=pd.to_datetime(parsed))
        for c in ["Open", "High", "Low", "Close"]:
            out[c] = pd.to_numeric(
                df[c].astype(str).str.replace(",", "", regex=False), errors="coerce"
            ).to_numpy()
        # Volume is not required for index scoring; keep the normalized shape.
        out["Volume"] = 0.0
        out = out[~out.index.isna()].dropna(subset=["Close"])
        out = out[~out.index.duplicated(keep="last")].sort_index()
        cutoff = _latest_completed_cutoff()
        out = out[[pd.Timestamp(i).date() <= cutoff for i in out.index]]
        return out
    except Exception as e:
        print("TPEx official index history", e)
        return pd.DataFrame()


def index_state(symbol, label, snap=None):
    try:
        # OTC index uses the official TPEx history first because Yahoo ^TWOII is
        # frequently missing/stale.  TWSE keeps Yahoo history with official MIS
        # close overlay for now.
        if symbol == "^TWOII":
            d = tpex_index_history()
            source = "TPEx OpenAPI"
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
            source = ("TPEx OpenAPI + MIS overlay" if symbol == "^TWOII" else "TWSE MIS overlay")
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
