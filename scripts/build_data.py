#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
犬子老師飆股雷達 Free Edition v1.2.1
=================================
總分 = 技術 50 + 籌碼 25 + 族群 10 + 大盤 15

--mode close
    每日盤後跑一次：
    * 全市場日 K
    * 外資 / 投信 / 融資 / 借券賣出
    * 加權 / 櫃買趨勢
    * 市場上漲家數比
    * 支撐壓力
    * 產生 close.json / market.json / universe.json

--mode intraday
    交易時段每 5 分鐘：
    * 固定關注池 + 前一盤後雷達前 150 名
    * 5 分 K / VWAP / 同時間量速
    * 沿用最近已公布的籌碼
    * 沿用最近完成交易日的大盤結構分數
    * 產生 intraday.json

免費版不把尚未公布的盤後籌碼冒充成即時資料。
"""

from __future__ import annotations
import argparse
import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from chip_data import build_chip_signals

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data"
CACHE = ROOT / ".cache"
OUT.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

TW = timezone(timedelta(hours=8))
TWSE_COMPANY_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_COMPANY_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"


def now_tw():
    return datetime.now(TW)


def dump(name, obj):
    (OUT / name).write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8"
    )


def load_json(name, default):
    p = OUT / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def pick_col(df, names):
    for n in names:
        if n in df.columns:
            return n
    for c in df.columns:
        for n in names:
            if n in str(c):
                return c
    return None


def get_universe():
    frames = []
    for url, suffix, market in [
        (TWSE_COMPANY_URL, ".TW", "上市"),
        (TPEX_COMPANY_URL, ".TWO", "上櫃"),
    ]:
        try:
            r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            df = pd.DataFrame(r.json())
            cc = pick_col(df, ["公司代號", "股票代號", "代號"])
            nc = pick_col(df, ["公司簡稱", "公司名稱", "名稱"])
            ic = pick_col(df, ["產業別", "產業"])
            if cc is None:
                continue
            o = pd.DataFrame()
            o["code"] = df[cc].astype(str).str.strip()
            o["name"] = df[nc].astype(str).str.strip() if nc else o["code"]
            o["industry"] = df[ic].astype(str).str.strip() if ic else "未分類"
            o["market"] = market
            o = o[o["code"].str.fullmatch(r"\d{4}", na=False)].copy()
            o["symbol"] = o["code"] + suffix
            frames.append(o)
        except Exception as e:
            print("universe", market, e)

    if not frames:
        # If the company endpoint is temporarily unavailable, preserve the last
        # deployed universe so the app does not go blank.
        old = load_json("universe.json", [])
        if old:
            o = pd.DataFrame(old)
            o["symbol"] = o["code"].astype(str) + np.where(o["market"].eq("上櫃"), ".TWO", ".TW")
            return o
        raise RuntimeError("無法取得上市上櫃公司清單")

    return pd.concat(frames, ignore_index=True).drop_duplicates("code")


def normalize(df):
    if df is None or df.empty:
        return pd.DataFrame()
    rename = {}
    for c in df.columns:
        s = str(c).lower()
        if s == "open": rename[c] = "Open"
        elif s == "high": rename[c] = "High"
        elif s == "low": rename[c] = "Low"
        elif s == "close": rename[c] = "Close"
        elif s == "volume": rename[c] = "Volume"
    df = df.rename(columns=rename)
    need = ["Open", "High", "Low", "Close", "Volume"]
    if any(c not in df.columns for c in need):
        return pd.DataFrame()
    x = df[need].copy()
    for c in need:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["Close", "Volume"])
    x.index = pd.to_datetime(x.index)
    return x


def split_bulk(raw, syms):
    out = {}
    if raw is None or raw.empty:
        return out
    if isinstance(raw.columns, pd.MultiIndex):
        l0 = set(map(str, raw.columns.get_level_values(0)))
        l1 = set(map(str, raw.columns.get_level_values(1)))
        for s in syms:
            try:
                if s in l0:
                    d = raw[s].copy()
                elif s in l1:
                    d = raw.xs(s, axis=1, level=1).copy()
                else:
                    continue
                d = normalize(d)
                if not d.empty:
                    out[s] = d
            except Exception:
                pass
    elif len(syms) == 1:
        d = normalize(raw)
        if not d.empty:
            out[syms[0]] = d
    return out


def download_daily(syms, period="6mo"):
    raw = yf.download(
        syms, period=period, interval="1d", group_by="ticker",
        auto_adjust=False, threads=True, progress=False
    )
    return split_bulk(raw, syms)


def download_intraday(syms):
    raw = yf.download(
        syms, period="5d", interval="5m", group_by="ticker",
        auto_adjust=False, threads=True, progress=False, prepost=False
    )
    return split_bulk(raw, syms)


def rsi(s, n=14):
    d = s.diff()
    u = d.clip(lower=0)
    dn = -d.clip(upper=0)
    au = u.ewm(alpha=1/n, adjust=False).mean()
    ad = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    return (100 - 100/(1+rs)).fillna(50)


def macd_hist(s):
    e12 = s.ewm(span=12, adjust=False).mean()
    e26 = s.ewm(span=26, adjust=False).mean()
    m = e12 - e26
    sig = m.ewm(span=9, adjust=False).mean()
    return m - sig


def true_range(df):
    pc = df["Close"].shift(1)
    return pd.concat([
        (df["High"] - df["Low"]).abs(),
        (df["High"] - pc).abs(),
        (df["Low"] - pc).abs(),
    ], axis=1).max(axis=1)


def pivots(df, lookback=70, order=2):
    z = df.tail(lookback)
    sup, res = [], []
    for i in range(order, max(order, len(z)-order)):
        lo = float(z["Low"].iloc[i])
        hi = float(z["High"].iloc[i])
        if lo <= float(z["Low"].iloc[i-order:i+order+1].min()):
            sup.append((lo, "前波低點"))
        if hi >= float(z["High"].iloc[i-order:i+order+1].max()):
            res.append((hi, "前波高點"))
    return sup, res


def zone(current, candidates, atr, side, intraday=False):
    c = []
    for p, label in candidates:
        try:
            p = float(p)
        except Exception:
            continue
        if not np.isfinite(p) or p <= 0:
            continue
        if side == "support" and p <= current * 1.002:
            c.append((p, label))
        elif side == "resistance" and p >= current * .998:
            c.append((p, label))
    if not c:
        return None
    c.sort(key=lambda x: abs(x[0] - current))
    seed = c[0][0]
    pct = .007 if intraday else .012
    cluster = [x for x in c if abs(x[0]/seed - 1) <= pct]
    center = float(np.median([x[0] for x in cluster]))
    half = max(
        current * (.0025 if intraday else .004),
        (atr or 0) * (.20 if intraday else .25)
    )
    labels = []
    for _, label in cluster:
        if label not in labels:
            labels.append(label)
    return {
        "low": round(max(0, center-half), 2),
        "high": round(center+half, 2),
        "center": round(center, 2),
        "distance_pct": round((center/current-1)*100, 2),
        "basis": "＋".join(labels[:3]),
    }


def daily_sr(x):
    if len(x) < 25:
        return {"support": None, "resistance": None}
    cur = float(x["Close"].iloc[-1])
    atr = float(true_range(x).rolling(14).mean().iloc[-1])
    sup, res = pivots(x)
    c = x["Close"]
    for n, label in [(5, "5MA"), (10, "10MA"), (20, "20MA")]:
        p = float(c.rolling(n).mean().iloc[-1])
        (sup if p <= cur else res).append((p, label))
    hist = x.iloc[:-1]
    if len(hist) >= 20:
        sup.append((float(hist["Low"].tail(20).min()), "20日低"))
        res.append((float(hist["High"].tail(20).max()), "20日高"))
    if len(hist):
        sup.append((float(hist["Low"].iloc[-1]), "前日低"))
        res.append((float(hist["High"].iloc[-1]), "前日高"))
    return {
        "support": zone(cur, sup, atr, "support"),
        "resistance": zone(cur, res, atr, "resistance"),
    }


def close_technical(x):
    """技術分 0~50。"""
    if len(x) < 35:
        return None
    c, h, v = x["Close"], x["High"], x["Volume"]
    ma5, ma10, ma20 = c.rolling(5).mean(), c.rolling(10).mean(), c.rolling(20).mean()
    vx = v / v.rolling(20).mean().shift(1).replace(0, np.nan)
    ret1 = (c/c.shift(1)-1)*100
    ret5 = (c/c.shift(5)-1)*100
    ret20 = (c/c.shift(20)-1)*100
    dist = (c/ma20-1)*100
    rr = rsi(c)
    mh = macd_hist(c)
    p3 = h.shift(1).rolling(3).max()
    p20 = h.shift(1).rolling(20).max()

    row = {
        "close": float(c.iloc[-1]),
        "ma5": float(ma5.iloc[-1]),
        "ma10": float(ma10.iloc[-1]),
        "ma20": float(ma20.iloc[-1]),
        "vol_x": float(vx.iloc[-1]) if pd.notna(vx.iloc[-1]) else 0,
        "day_change": float(ret1.iloc[-1]) if pd.notna(ret1.iloc[-1]) else 0,
        "ret5": float(ret5.iloc[-1]) if pd.notna(ret5.iloc[-1]) else 0,
        "ret20": float(ret20.iloc[-1]) if pd.notna(ret20.iloc[-1]) else 0,
        "dist20": float(dist.iloc[-1]) if pd.notna(dist.iloc[-1]) else 0,
        "rsi": float(rr.iloc[-1]),
        "macd_h": float(mh.iloc[-1]),
        "macd_acc": float(mh.iloc[-1]-mh.iloc[-2]),
        "break3": bool(c.iloc[-1] > p3.iloc[-1]) if pd.notna(p3.iloc[-1]) else False,
        "break20": bool(c.iloc[-1] > p20.iloc[-1]) if pd.notna(p20.iloc[-1]) else False,
        "trend": bool(c.iloc[-1] > ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1]),
        "avg_turnover20": float((c*v).rolling(20).mean().iloc[-1]),
        "date": str(x.index[-1].date()),
    }

    score = 0
    reasons = []
    if row["trend"]:
        score += 8; reasons.append("均線多頭")
    if row["break3"]:
        score += 5; reasons.append("3日突破")
    if row["break20"]:
        score += 8; reasons.append("20日突破")

    if 1.8 <= row["vol_x"] < 4:
        score += 8; reasons.append(f"量比{row['vol_x']:.1f}x")
    elif 1.3 <= row["vol_x"] < 1.8:
        score += 5; reasons.append(f"量比{row['vol_x']:.1f}x")
    elif 4 <= row["vol_x"] <= 6:
        score += 5; reasons.append(f"大量{row['vol_x']:.1f}x")

    if 55 <= row["rsi"] <= 72:
        score += 5; reasons.append("RSI強而未過熱")
    elif 50 <= row["rsi"] < 55:
        score += 2

    if row["macd_h"] > 0 and row["macd_acc"] > 0:
        score += 6; reasons.append("MACD動能增強")
    elif row["macd_h"] > 0:
        score += 3

    if 2 <= row["ret5"] <= 12:
        score += 5
    elif 0 < row["ret5"] < 2:
        score += 2

    if 5 <= row["ret20"] <= 30:
        score += 5
    elif 0 < row["ret20"] < 5:
        score += 2

    over = []
    if row["dist20"] > 15:
        score -= 8; over.append("距20MA過遠")
    if row["ret5"] > 25:
        score -= 7; over.append("5日漲幅過大")
    if row["vol_x"] > 6:
        score -= 5; over.append("爆量>6x")
    if row["rsi"] > 82:
        score -= 5; over.append("RSI過熱")

    row["technical_score"] = max(0, min(50, round(score, 1)))
    row["reasons"] = reasons
    row["overheat_reasons"] = over
    row.update(daily_sr(x))
    return row


def chip_score(chip):
    """籌碼分 0~25。缺資料以中性分處理，同時回傳 coverage。"""
    chip = chip or {}
    score = 0.0
    coverage = 0.0

    # 外資 8
    if chip.get("foreign_3buy") is not None:
        coverage += 8
        if chip.get("foreign_3buy"):
            score += 8
        elif (chip.get("foreign_net_latest") or 0) > 0:
            score += 5
        else:
            score += 1
    else:
        score += 4

    # 借券賣出餘額 7
    if chip.get("sbl_3down") is not None:
        coverage += 7
        if chip.get("sbl_3down"):
            score += 7
        elif (chip.get("sbl_3change_pct") is not None and chip.get("sbl_3change_pct") < 0):
            score += 4.5
        else:
            score += 1
    else:
        score += 3.5

    # 投信 5
    if chip.get("trust_net_latest") is not None:
        coverage += 5
        if chip.get("trust_net_latest") > 0:
            score += 5
        elif chip.get("trust_net_latest") == 0:
            score += 2.5
    else:
        score += 2.5

    # 融資 5
    if chip.get("margin_status") is not None:
        coverage += 5
        if chip.get("margin_status") == "正常":
            score += 5
        elif chip.get("margin_status") == "下降":
            score += 4
        elif chip.get("margin_status") == "偏熱":
            score += 0
        else:
            score += 2.5
    else:
        score += 2.5

    return round(min(25, score), 1), round(coverage/25*100, 0)


def sector_score(n):
    if n >= 4:
        return 10
    if n == 3:
        return 8
    if n == 2:
        return 5
    return 0


def index_state(symbol, label):
    try:
        d = download_daily([symbol], "3mo").get(symbol)
        if d is None or len(d) < 25:
            return None
        c = d["Close"]
        ma5 = float(c.rolling(5).mean().iloc[-1])
        ma10 = float(c.rolling(10).mean().iloc[-1])
        ma20 = float(c.rolling(20).mean().iloc[-1])
        close = float(c.iloc[-1])
        change = float((c.iloc[-1]/c.iloc[-2]-1)*100)
        return {
            "label": label, "symbol": symbol, "close": round(close, 2),
            "change_pct": round(change, 2),
            "ma5": round(ma5, 2), "ma10": round(ma10, 2), "ma20": round(ma20, 2),
            "trend": bool(close > ma5 > ma10 > ma20),
            "above20": bool(close > ma20),
            "date": str(d.index[-1].date()),
        }
    except Exception as e:
        print("index", symbol, e)
        return None


def build_market(breadth_pct, chips):
    taiex = index_state("^TWII", "加權")
    otc = index_state("^TWOII", "櫃買")

    # 全市場外資最近一日淨買超，TWSE/TPEx 原始值以股數為主，轉成張顯示。
    vals = [
        x.get("foreign_net_latest") for x in chips.values()
        if x.get("foreign_net_latest") is not None
    ]
    foreign_lots = (sum(vals)/1000) if vals else None

    score = 0.0
    if taiex:
        score += 5 if taiex["trend"] else 2.5 if taiex["above20"] else 0
    else:
        score += 2.5  # 缺資料中性
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
    if foreign_lots is None:
        score += 1.5
    elif foreign_lots > 0:
        score += 3

    score = round(min(15, score), 1)
    mode = "偏多" if score >= 11 else "中性" if score >= 7 else "防守"
    threshold = 70 if mode == "偏多" else 76 if mode == "中性" else 82

    return {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "market_score": score,
        "market_mode": mode,
        "radar_threshold": threshold,
        "breadth_up_pct": round(breadth_pct, 1) if breadth_pct is not None else None,
        "foreign_net_lots": round(foreign_lots, 0) if foreign_lots is not None else None,
        "taiex": taiex,
        "otc": otc,
        "score_max": 15,
        "explain": {
            "taiex": "加權趨勢最多5分",
            "otc": "櫃買趨勢最多4分",
            "breadth": "上漲家數比最多3分",
            "foreign": "全市場外資方向最多3分",
        },
    }


def intraday_sr(x, vwap):
    latest = x.index[-1].date()
    today = x[x.index.date == latest]
    prev = x[x.index.date < latest]
    cur = float(today["Close"].iloc[-1])
    atr = float(true_range(today).rolling(8).mean().iloc[-1]) if len(today) >= 8 else cur*.005
    sup, res = pivots(today, lookback=len(today), order=2)
    (sup if vwap <= cur else res).append((vwap, "VWAP"))
    sup.append((float(today["Low"].min()), "今日低"))
    res.append((float(today["High"].max()), "今日高"))
    if not prev.empty:
        d = sorted(set(prev.index.date))[-1]
        p = prev[prev.index.date == d]
        sup.append((float(p["Low"].min()), "前日低"))
        res.append((float(p["High"].max()), "前日高"))
    return {
        "support": zone(cur, sup, atr, "support", True),
        "resistance": zone(cur, res, atr, "resistance", True),
    }


def intraday_technical(x):
    # 開盤早段也要能掃描；只要累積至少 4 根 5 分K 就可開始判斷。
    if len(x) < 4:
        return None
    x = x.copy()
    x.index = pd.to_datetime(x.index)
    latest = x.index[-1].date()
    today = x[x.index.date == latest]
    prev = x[x.index.date < latest]
    if len(today) < 3:
        return None

    c, h, v = today["Close"], today["High"], today["Volume"]
    cur = float(c.iloc[-1])
    typical = (today["High"]+today["Low"]+today["Close"])/3
    vwap_s = (typical*v).cumsum()/v.cumsum().replace(0, np.nan)
    vwap = float(vwap_s.iloc[-1])

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

    n = len(today)
    vals = []
    for d in sorted(set(prev.index.date))[-4:]:
        z = prev[prev.index.date == d]
        if len(z) >= n:
            vals.append(float(z["Volume"].iloc[:n].sum()))
    pace = float(v.sum()/np.median(vals)) if vals and np.median(vals) > 0 else 1.0

    if not prev.empty:
        d = sorted(set(prev.index.date))[-1]
        prev_close = float(prev[prev.index.date == d]["Close"].iloc[-1])
    else:
        prev_close = float(c.iloc[0])
    day_change = (cur/prev_close-1)*100 if prev_close else 0
    ret15 = (c.iloc[-1]/c.iloc[-4]-1)*100 if len(c) >= 4 else 0
    vwap_dist = (cur/vwap-1)*100 if vwap else 0

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
        "technical_score": max(0, min(50, round(score, 1))),
        "reasons": reasons, "overheat_reasons": over, **sr,
    }


def add_component_scores(rows, market, preliminary_intraday=False):
    """加入族群分、總分、階段與品質。

    v1.2 起把「階段」和「品質」拆開：
    - 階段主要看價格行為、量能與位階。
    - 品質才用 100 分總分衡量。
    """
    if not rows:
        return rows

    hot = {}
    for r in rows:
        if r.get("technical_score", 0) >= 30 and not r.get("overheat_reasons"):
            hot[r["industry"]] = hot.get(r["industry"], 0) + 1

    quality_reference = market.get("radar_threshold", 76)
    market_score = float(market.get("market_score", 7.5))

    for r in rows:
        n = int(hot.get(r["industry"], 0))
        sec = sector_score(n)
        r["industry_hot_count"] = n
        r["sector_score"] = sec
        r["market_score"] = market_score
        r["market_mode"] = market.get("market_mode", "中性")

        cs = float(r.get("chip_score", 12.5))
        total = float(r.get("technical_score", 0)) + cs + sec + market_score
        r["score"] = round(max(0, min(100, total)), 1)

        if r["score"] >= 80:
            r["quality_label"] = "高共振"
        elif r["score"] >= 70:
            r["quality_label"] = "強"
        else:
            r["quality_label"] = "一般"
        r["quality_reference"] = quality_reference
        r["quality_pass_market"] = bool(r["score"] >= quality_reference)

        if r.get("overheat_reasons"):
            r["category"] = "過熱不追"
            r["stage_reason"] = "位階或動能已進入過熱區"

        elif preliminary_intraday:
            launch = bool(
                r.get("break3")
                and r.get("close", 0) > r.get("vwap", 1e99)
                and (r.get("trend5") or r.get("break12") or r.get("technical_score", 0) >= 22)
            )
            pullback = bool(
                (r.get("trend5") or r.get("technical_score", 0) >= 25)
                and r.get("close", 0) >= r.get("vwap", 0) * 0.995
            )

            if launch:
                r["category"] = "剛啟動"
                r["stage_reason"] = "3K突破＋站上VWAP＋量速放大"
            elif pullback:
                r["category"] = "等回踩"
                r["stage_reason"] = "短線結構仍強，等待VWAP/短均承接"
            else:
                r["category"] = "觀察"
                r["stage_reason"] = "已有部分條件，但尚未形成明確盤中啟動"

        else:
            launch_structure = bool(
                r.get("break20")
                or (r.get("break3") and r.get("trend"))
            )
            launch = bool(
                launch_structure
                and r.get("vol_x", 0) >= 1.2
                and r.get("dist20", 999) <= 12
                and r.get("ret5", 999) <= 18
            )
            pullback = bool(
                (r.get("trend") or r.get("break3") or r.get("technical_score", 0) >= 28)
                and r.get("dist20", 999) <= 15
                and r.get("ret5", 999) <= 22
            )

            if launch:
                r["category"] = "剛啟動"
                r["stage_reason"] = "20日突破" if r.get("break20") else "3日平台突破＋均線多頭"
            elif pullback:
                r["category"] = "等回踩"
                r["stage_reason"] = "趨勢仍強，但較適合等支撐/均線承接"
            else:
                r["category"] = "觀察"
                r["stage_reason"] = "條件尚未集中到啟動階段"

    order = {"剛啟動": 0, "等回踩": 1, "觀察": 2, "過熱不追": 3}
    quality_order = {"高共振": 0, "強": 1, "一般": 2}
    rows.sort(key=lambda r: (
        order.get(r["category"], 9),
        quality_order.get(r.get("quality_label"), 9),
        -r["score"]
    ))
    return rows


def build_close():
    uni = get_universe()
    universe_public = uni[["code", "name", "industry", "market"]].astype(str).to_dict("records")
    dump("universe.json", universe_public)
    meta = uni.set_index("symbol").to_dict("index")

    rows = []
    breadth_changes = []
    syms = uni["symbol"].tolist()

    for i in range(0, len(syms), 100):
        part = syms[i:i+100]
        try:
            data = download_daily(part, "6mo")
        except Exception as e:
            print("daily batch", i, e)
            continue

        for sym, x in data.items():
            try:
                t = close_technical(x)
                if not t:
                    continue
                breadth_changes.append(t["day_change"])
                if t["avg_turnover20"] < 30_000_000:
                    continue
                m = meta.get(sym, {})
                rows.append({
                    "symbol": sym,
                    "code": str(m.get("code", sym.split(".")[0])),
                    "name": str(m.get("name", sym)),
                    "industry": str(m.get("industry", "未分類")),
                    "market": str(m.get("market", "")),
                    **t,
                })
            except Exception as e:
                print("daily stock", sym, e)

    market_map = dict(zip(uni["code"].astype(str), uni["market"].astype(str)))

    # All-market chip fetch is table-based, not 1000 individual HTTP calls.
    chips = build_chip_signals(
        uni["code"].astype(str).tolist(),
        market_map,
        CACHE / "chips"
    )

    breadth_pct = None
    if breadth_changes:
        breadth_pct = sum(1 for x in breadth_changes if x > 0) / len(breadth_changes) * 100

    market = build_market(breadth_pct, chips)

    for r in rows:
        chip = chips.get(r["code"], {})
        cs, coverage = chip_score(chip)
        r.update(chip)
        r["chip_score"] = cs
        r["chip_coverage_pct"] = coverage

    rows = add_component_scores(rows, market, preliminary_intraday=False)

    dump("close.json", {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "market": market,
        "score_formula": {"technical": 50, "chip": 25, "sector": 10, "market": 15},
        "rows": rows,
    })
    dump("market.json", market)

    status = load_json("status.json", {})
    status.update({
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "close_updated_at": now_tw().isoformat(timespec="seconds"),
        "daily_count": len(rows),
        "version": "1.2.1-free",
    })
    dump("status.json", status)

    # On first deployment, make sure the file exists.
    if not (OUT / "intraday.json").exists():
        dump("intraday.json", {
            "updated_at": None, "market": market, "rows": [],
            "note": "等待交易時段第一次盤中更新"
        })

    print("close done", len(rows), market["market_mode"], market["market_score"])


def intraday_index_snapshot():
    out = {}
    try:
        data = download_intraday(["^TWII", "^TWOII"])
        for sym, label in [("^TWII", "加權"), ("^TWOII", "櫃買")]:
            x = data.get(sym)
            if x is None or x.empty:
                continue
            latest = x.index[-1].date()
            today = x[x.index.date == latest]
            prev = x[x.index.date < latest]
            cur = float(today["Close"].iloc[-1])
            if not prev.empty:
                d = sorted(set(prev.index.date))[-1]
                pc = float(prev[prev.index.date == d]["Close"].iloc[-1])
                ch = (cur/pc-1)*100 if pc else None
            else:
                ch = None
            out[sym] = {
                "label": label, "close": round(cur, 2),
                "change_pct": round(ch, 2) if ch is not None else None,
                "time": x.index[-1].strftime("%H:%M"),
            }
    except Exception as e:
        print("intraday index", e)
    return out


def build_intraday():
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
    pool += [
        code_to_sym[r["code"]] for r in close_rows
        if r.get("code") in code_to_sym
    ]
    pool = list(dict.fromkeys(pool))

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
                t = intraday_technical(x)
                if not t:
                    continue
                m = meta.get(sym, {})
                code = str(m.get("code", sym.split(".")[0]))
                prev = close_map.get(code, {})
                rows.append({
                    "symbol": sym,
                    "code": code,
                    "name": str(m.get("name", sym)),
                    "industry": str(m.get("industry", "未分類")),
                    "market": str(m.get("market", "")),
                    **t,
                    # 最近已公布的籌碼從盤後資料沿用
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
                })
            except Exception as e:
                print("intra stock", sym, e)

    rows = add_component_scores(rows, market, preliminary_intraday=True)

    if not rows:
        previous = load_json("intraday.json", {})
        if previous.get("rows"):
            previous["stale"] = True
            previous["attempted_at"] = now_tw().isoformat(timespec="seconds")
            previous["note"] = "本輪免費盤中資料源暫時沒有有效5分K，已保留上一輪資料，不再顯示空白。"
            dump("intraday.json", previous)
            status = load_json("status.json", {})
            status.update({
                "updated_at": now_tw().isoformat(timespec="seconds"),
                "intraday_attempted_at": now_tw().isoformat(timespec="seconds"),
                "intraday_count": len(previous.get("rows", [])),
                "version": "1.2.1-free",
            })
            dump("status.json", status)
            print("intraday source empty; kept previous", len(previous.get("rows", [])))
            return

    market_live = intraday_index_snapshot()

    dump("intraday.json", {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "market": market,
        "market_intraday": market_live,
        "score_formula": {"technical": 50, "chip": 25, "sector": 10, "market": 15},
        "rows": rows,
    })

    status = load_json("status.json", {})
    status.update({
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "intraday_updated_at": now_tw().isoformat(timespec="seconds"),
        "intraday_count": len(rows),
        "version": "1.2.1-free",
    })
    dump("status.json", status)
    print("intraday done", len(rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["close", "intraday", "all"], default="all")
    args = ap.parse_args()
    if args.mode in ("close", "all"):
        build_close()
    if args.mode in ("intraday", "all"):
        build_intraday()


if __name__ == "__main__":
    main()
