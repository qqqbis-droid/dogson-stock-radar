#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
犬子老師飆股雷達 Free Edition v1.5.29
=================================
盤中＝執行雷達（即時動能100，籌碼只作背景）；盤後＝波段雷達（延續品質直接100分＋進場位置）；大盤15分獨立

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
    * 固定關注池 + 所有通過流動性門檻的股票
    * 5 分 K / VWAP / 同時間量速
    * 沿用最近已公布的籌碼
    * 盤中大盤15分只看今日即時結構，不使用昨日外資計分
    * 族群成交金額占比輪動 / VWAP / 廣度
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
from sector_groups import industry_name_for, sector_group_for

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
    """取得上市 + 上櫃股票清單；TPEx OpenAPI 失敗時改用官方 MOPS CSV。"""
    import io

    frames = []
    old = load_json("universe.json", [])
    old_df = pd.DataFrame(old) if old else pd.DataFrame()

    def normalize_company_df(df, suffix, market):
        cc = pick_col(df, [
            "公司代號", "股票代號", "代號",
            "SecuritiesCompanyCode", "CompanyCode", "StockCode"
        ])
        nc = pick_col(df, [
            "公司簡稱", "公司名稱", "名稱",
            "CompanyAbbreviation", "SecuritiesCompanyName", "CompanyName"
        ])
        ic = pick_col(df, [
            "產業別", "產業",
            "SecuritiesIndustryCode", "IndustryCode", "Industry"
        ])
        if cc is None:
            raise ValueError(f"{market} 找不到股票代號欄位: {list(df.columns)}")
        o = pd.DataFrame()
        o["code"] = df[cc].astype(str).str.strip()
        o["name"] = df[nc].astype(str).str.strip() if nc else o["code"]
        o["industry"] = df[ic].astype(str).str.strip() if ic else "未分類"
        o["market"] = market
        o = o[o["code"].str.fullmatch(r"\d{4}", na=False)].copy()
        o["symbol"] = o["code"] + suffix
        if o.empty:
            raise ValueError(f"{market} 股票清單為空")
        return o

    configs = [
        {
            "market": "上市",
            "suffix": ".TW",
            "json": TWSE_COMPANY_URL,
            "csv": "https://mopsfin.twse.com.tw/opendata/t187ap03_L.csv",
        },
        {
            "market": "上櫃",
            "suffix": ".TWO",
            "json": TPEX_COMPANY_URL,
            "csv": "https://mopsfin.twse.com.tw/opendata/t187ap03_O.csv",
        },
    ]

    for cfg in configs:
        market = cfg["market"]
        suffix = cfg["suffix"]
        loaded = False

        # 1) 先嘗試官方 OpenAPI JSON
        try:
            r = requests.get(cfg["json"], timeout=30, headers={
                "User-Agent": "Mozilla/5.0 DogsonRadar/1.2.3",
                "Accept": "application/json,text/plain,*/*",
            })
            r.raise_for_status()
            df = pd.DataFrame(r.json())
            o = normalize_company_df(df, suffix, market)
            frames.append(o)
            loaded = True
            print("universe", market, "json", len(o))
        except Exception as e:
            print("universe", market, "json failed", e)

        # 2) JSON 失敗時，用政府公開資料官方 CSV 備援
        if not loaded:
            try:
                r = requests.get(cfg["csv"], timeout=45, headers={
                    "User-Agent": "Mozilla/5.0 DogsonRadar/1.2.3",
                    "Accept": "text/csv,text/plain,*/*",
                })
                r.raise_for_status()
                raw = r.content
                last_err = None
                df = None
                for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
                    try:
                        text = raw.decode(enc)
                        df = pd.read_csv(io.StringIO(text), dtype=str)
                        break
                    except Exception as ex:
                        last_err = ex
                        df = None
                if df is None:
                    raise last_err or ValueError("CSV decode failed")
                o = normalize_company_df(df, suffix, market)
                frames.append(o)
                loaded = True
                print("universe", market, "csv", len(o))
            except Exception as e:
                print("universe", market, "csv failed", e)

        # 3) 兩個官方來源都暫時失效，才保留上次成功清單
        if not loaded and not old_df.empty and "market" in old_df.columns:
            fb = old_df[old_df["market"].astype(str).eq(market)].copy()
            if not fb.empty:
                fb["code"] = fb["code"].astype(str)
                fb["name"] = fb["name"].astype(str)
                if "industry" not in fb.columns:
                    fb["industry"] = "未分類"
                fb["industry"] = fb["industry"].astype(str)
                fb["symbol"] = fb["code"] + suffix
                frames.append(fb[["code", "name", "industry", "market", "symbol"]])
                print("universe", market, "cached", len(fb))

    if not frames:
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



def _latest_completed_cutoff():
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
    return out

def overlay_official_today_bar(x, snap):
    if x is None or x.empty or not snap:
        return x
    y = x.copy()
    target = snap["date"]
    idx_dates = [pd.Timestamp(v).date() for v in y.index]
    vals = {k: snap.get(k) for k in ["Open", "High", "Low", "Close", "Volume"]}
    if target in idx_dates:
        pos = max(i for i, d in enumerate(idx_dates) if d == target)
        idx = y.index[pos]
        for k, v in vals.items():
            if v is not None:
                y.loc[idx, k] = v
    else:
        row = {k: (v if v is not None else np.nan) for k, v in vals.items()}
        y.loc[pd.Timestamp(target)] = row
        y = y.sort_index()
    return y


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
    """Weighted support/resistance clustering.

    Candidates may be (price, label) or (price, label, weight).  We no longer
    blindly pick the closest line: nearby evidence is clustered, weighted by
    structural importance, then penalised for distance from current price.
    """
    items = []
    for item in candidates:
        try:
            p = float(item[0])
            label = str(item[1])
            weight = float(item[2]) if len(item) >= 3 else 1.0
        except Exception:
            continue
        if not np.isfinite(p) or p <= 0:
            continue
        if side == "support" and p <= current * 1.002:
            items.append((p, label, max(.2, weight)))
        elif side == "resistance" and p >= current * .998:
            items.append((p, label, max(.2, weight)))
    if not items:
        return None

    # Keep meaningful nearby levels; if none fall inside the normal window,
    # retain the closest candidates rather than returning an arbitrary far line.
    max_dist = .055 if intraday else .16
    near = [x for x in items if abs(x[0] / current - 1) <= max_dist]
    if near:
        items = near
    items.sort(key=lambda x: abs(x[0] - current))
    items = items[:24]

    atr_pct = (atr / current) if atr and current else 0
    cluster_pct = max(.005 if intraday else .007,
                      min(.015 if intraday else .022, atr_pct * (.35 if intraday else .55)))

    best = None
    for seed, _, _ in items:
        cluster = [x for x in items if abs(x[0] / seed - 1) <= cluster_pct]
        if not cluster:
            continue
        sw = sum(x[2] for x in cluster)
        center = sum(x[0] * x[2] for x in cluster) / max(sw, 1e-9)
        dist = abs(center / current - 1)
        labels = []
        for _, label, _ in sorted(cluster, key=lambda x: x[2], reverse=True):
            if label not in labels:
                labels.append(label)
        # Evidence first, distance second.  This lets a strong breakout platform
        # beat a weak single MA a little closer to price.
        quality = sw + .35 * len(labels) - dist * (20 if intraday else 14)
        candidate = (quality, -dist, center, cluster, labels, sw)
        if best is None or candidate[:2] > best[:2]:
            best = candidate

    if best is None:
        return None
    quality, _, center, cluster, labels, sw = best
    spread = (max(x[0] for x in cluster) - min(x[0] for x in cluster)) if len(cluster) > 1 else 0
    half = max(
        current * (.0020 if intraday else .0028),
        (atr or 0) * (.14 if intraday else .18),
        spread * .55,
    )
    strength = 5 if sw >= 7 else 4 if sw >= 5 else 3 if sw >= 3.4 else 2 if sw >= 2 else 1
    return {
        "low": round(max(0, center - half), 2),
        "high": round(center + half, 2),
        "center": round(center, 2),
        "distance_pct": round((center / current - 1) * 100, 2),
        "basis": "＋".join(labels[:4]),
        "strength": strength,
        "evidence_count": len(labels),
    }


def daily_sr(x):
    """Multi-evidence daily support/resistance.

    Inputs include pivots, moving averages, prior highs/lows, breakout-retest
    levels, volume-by-price nodes, high-volume cost zones and recent gaps.
    """
    if len(x) < 25:
        return {"support": None, "resistance": None}
    cur = float(x["Close"].iloc[-1])
    atr = float(true_range(x).rolling(14).mean().iloc[-1])
    raw_sup, raw_res = pivots(x)
    sup = [(p, label, 1.5) for p, label in raw_sup]
    res = [(p, label, 1.5) for p, label in raw_res]

    def place(p, label, weight):
        try:
            p = float(p)
        except Exception:
            return
        if not np.isfinite(p) or p <= 0:
            return
        (sup if p <= cur else res).append((p, label, weight))

    c = x["Close"]
    for n, label, weight in [
        (5, "5MA", 1.1), (10, "10MA", 1.35), (20, "20MA", 1.8),
        (60, "60MA", 2.0), (120, "120MA", 1.8),
    ]:
        if len(c) >= n:
            v = c.rolling(n).mean().iloc[-1]
            if pd.notna(v):
                place(v, label, weight)

    hist = x.iloc[:-1]
    if len(hist):
        place(hist["Low"].iloc[-1], "前日低", 1.35)
        place(hist["High"].iloc[-1], "前日高", 1.35)

    if len(hist) >= 20:
        low20 = float(hist["Low"].tail(20).min())
        high20 = float(hist["High"].tail(20).max())
        place(low20, "20日低", 2.1)
        place(high20, "20日高", 2.3)
        if cur > high20 * 1.003:
            sup.append((high20, "突破平台", 3.2))
    if len(hist) >= 60:
        place(float(hist["Low"].tail(60).min()), "60日低", 2.0)
        place(float(hist["High"].tail(60).max()), "60日高", 2.0)

    # Volume-by-price: approximate recent cost concentration with 24 price bins.
    z = x.tail(60).copy()
    try:
        lo = float(z["Low"].min()); hi = float(z["High"].max())
        if hi > lo:
            edges = np.linspace(lo, hi, 25)
            tp = (z["High"] + z["Low"] + z["Close"]) / 3
            ids = np.clip(np.digitize(tp.to_numpy(), edges) - 1, 0, len(edges) - 2)
            vols = {}
            for idx, vol in zip(ids, z["Volume"].fillna(0).to_numpy()):
                vols[int(idx)] = vols.get(int(idx), 0.0) + float(vol)
            for idx, _ in sorted(vols.items(), key=lambda kv: kv[1], reverse=True)[:5]:
                center = (edges[idx] + edges[idx + 1]) / 2
                place(center, "成交密集區", 2.7)
    except Exception:
        pass

    # High-volume sessions are often meaningful cost zones.
    try:
        for idx in z.nlargest(min(5, len(z)), "Volume").index:
            row = z.loc[idx]
            p = (float(row["High"]) + float(row["Low"]) + float(row["Close"])) / 3
            place(p, "大量成交區", 2.0)
    except Exception:
        pass

    # Recent gaps: midpoint is a practical proxy for the unfilled gap zone.
    try:
        g = x.tail(45)
        for i in range(1, len(g)):
            ph = float(g["High"].iloc[i-1]); pl = float(g["Low"].iloc[i-1])
            ch = float(g["High"].iloc[i]); cl = float(g["Low"].iloc[i])
            if cl > ph * 1.005:
                place((cl + ph) / 2, "跳空缺口", 2.15)
            elif ch < pl * .995:
                place((ch + pl) / 2, "跳空缺口", 2.15)
    except Exception:
        pass

    return {
        "support": zone(cur, sup, atr, "support"),
        "resistance": zone(cur, res, atr, "resistance"),
    }

def close_technical(x):
    """技術分 0~50。"""
    if len(x) < 35:
        return None
    c, h, l, v = x["Close"], x["High"], x["Low"], x["Volume"]
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
    # v1.5.30: causal self baselines. Average volume excludes the current day;
    # breakout-event volume uses only prior completed 20-day breakout events.
    avgvol20 = v.shift(1).rolling(20).mean()
    breakout_mask = (c > p20) & p20.notna()
    hist_breakout_vol = v.iloc[:-1][breakout_mask.iloc[:-1]].dropna().tail(20)

    row = {
        "close": float(c.iloc[-1]),
        "high": float(h.iloc[-1]),
        "low": float(l.iloc[-1]),
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
        "volume": float(v.iloc[-1]),
        "avg_volume20": float(avgvol20.iloc[-1]) if pd.notna(avgvol20.iloc[-1]) else None,
        "breakout_event_count": int(len(hist_breakout_vol)),
        "breakout_volume_median20": float(hist_breakout_vol.median()) if len(hist_breakout_vol) >= 3 else None,
        "breakout_volume_avg20": float(hist_breakout_vol.mean()) if len(hist_breakout_vol) >= 3 else None,
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

    # Step 6：建立每檔自己的日波動基準，供盤中動態門檻使用。
    tr14 = true_range(x).rolling(14).mean()
    atr14 = float(tr14.iloc[-1]) if pd.notna(tr14.iloc[-1]) else None
    hist_ret = ret1.tail(60).dropna().abs()
    hist_vx = vx.tail(60).dropna()
    row["dynamic_profile"] = {
        "version": "1.0",
        "ready": bool(len(hist_ret) >= 35 and atr14 is not None and row["close"] > 0),
        "sample_days": int(len(hist_ret)),
        "atr14_pct": round(atr14 / row["close"] * 100, 3) if atr14 is not None and row["close"] > 0 else None,
        "abs_ret1_p90": round(float(hist_ret.quantile(.90)), 3) if len(hist_ret) >= 10 else None,
        "abs_ret1_median": round(float(hist_ret.median()), 3) if len(hist_ret) >= 10 else None,
        "vol_x_p90": round(float(hist_vx.quantile(.90)), 3) if len(hist_vx) >= 10 else None,
    }
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

    return int(math.floor(min(25, score) + 0.5)), round(coverage/25*100, 0)


def sector_score(n, ratio=None, fallback=False):
    """Sector score 0~10.

    Specific topic groups keep the original strict resonance logic.  Stocks not
    yet mapped to a narrow group use official-industry breadth as a capped proxy,
    so 'not mapped' is no longer automatically interpreted as 'sector weak'.
    """
    n = int(n or 0)
    if not fallback:
        if n >= 4:
            return 10
        if n == 3:
            return 8
        if n == 2:
            return 5
        if n == 1:
            return 2
        return 0

    r = float(ratio or 0)
    if n >= 4 and r >= .45:
        return 6
    if n >= 3 and r >= .30:
        return 5
    if n >= 2 and r >= .20:
        return 4
    if n >= 2 and r >= .12:
        return 2
    if n >= 1 and r >= .10:
        return 1
    return 0

def liquidity_profile(avg_turnover20):
    """20日平均成交金額流動性分級。"""
    try:
        x = float(avg_turnover20)
    except Exception:
        return "未知", 0
    if x < 30_000_000:
        return "不足", -999
    if x < 80_000_000:
        return "偏低", -5
    if x < 200_000_000:
        return "正常", 0
    return "活躍", 2


def _parse_tpex_index_date(value):
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
        ret5 = float((c.iloc[-1]/c.iloc[-6]-1)*100) if len(c) >= 6 else None
        return {
            "label": label, "symbol": symbol, "close": round(close, 2),
            "change_pct": round(change, 2), "ret5": round(ret5, 2) if ret5 is not None else None,
            "ma5": round(ma5, 2), "ma10": round(ma10, 2), "ma20": round(ma20, 2),
            "trend": bool(close > ma5 > ma10 > ma20),
            "above20": bool(close > ma20),
            "date": str(c.index[-1].date()), "source": source,
        }
    except Exception as e:
        print("index", symbol, e)
        return None

def _market_num(x):
    if x is None:
        return None
    s = str(x).replace(",", "").replace("+", "").replace("−", "-").strip()
    if s in {"", "-", "--", "nan", "None"}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _flatten_market_table(df):
    x = df.copy()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = ["|".join(str(v) for v in col if str(v) != "nan").strip("|") for col in x.columns]
    else:
        x.columns = [str(c) for c in x.columns]
    return x


def _twse_foreign_value(d):
    """TWSE BFI82U: foreign-investor net buy/sell amount in TWD for one trading day."""
    try:
        rr = requests.get(
            "https://www.twse.com.tw/rwd/zh/fund/BFI82U",
            params={"dayDate": d.strftime("%Y%m%d"), "response": "json", "type": "day"},
            headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.3", "Accept": "application/json,text/plain,*/*"},
            timeout=20,
        )
        rr.raise_for_status()
        obj = rr.json()
        obj_date = str(obj.get("date") or "").replace("/", "").replace("-", "")
        if obj_date and d.strftime("%Y%m%d") not in obj_date:
            return None
        fields = obj.get("fields") or obj.get("field")
        data = obj.get("data")
        if not fields or not isinstance(data, list):
            return None
        df = pd.DataFrame(data, columns=fields)
        name_col = pick_col(df, ["單位名稱", "名稱"])
        net_col = pick_col(df, ["買賣差額", "買賣超"])
        if name_col is None or net_col is None:
            return None
        names = df[name_col].astype(str)
        hit = df[names.str.contains("外資及陸資", na=False) & names.str.contains("不含", na=False)]
        if hit.empty:
            return None
        return _market_num(hit.iloc[0][net_col])
    except Exception as e:
        print("TWSE official foreign flow", d, e)
        return None


def _tpex_foreign_value(d):
    """TPEx 3-institution summary: foreign-investor net buy/sell amount in TWD."""
    import io

    roc = f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"
    try:
        rr = requests.get(
            "https://www.tpex.org.tw/web/stock/3insti/3insti_summary/3itrdsum_result.php",
            params={"d": roc, "l": "zh-tw", "o": "htm", "p": "1", "t": "D"},
            headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.3", "Accept-Language": "zh-TW,zh;q=0.9"},
            timeout=20,
        )
        rr.raise_for_status()
        text = rr.text
        date_markers = [
            roc,
            f"{d.year - 1911}年{d.month:02d}月{d.day:02d}日",
            f"{d.year - 1911}年{d.month}月{d.day}日",
        ]
        if not any(m in text for m in date_markers):
            return None
        tables = pd.read_html(io.StringIO(text))
        for raw in tables:
            if raw.empty or raw.shape[1] < 3:
                continue
            df = _flatten_market_table(raw)
            name_col = next((c for c in df.columns if "單位名稱" in str(c)), df.columns[0])
            net_col = next((c for c in df.columns if "買賣超" in str(c)), None)
            if net_col is None:
                continue
            names = df[name_col].astype(str).str.replace(" ", "", regex=False)
            hit = df[names.str.contains("外資及陸資", na=False) & names.str.contains("不含", na=False)]
            if hit.empty:
                hit = df[names.str.contains("外資及陸資合計", na=False)]
            if not hit.empty:
                return _market_num(hit.iloc[0][net_col])
        return None
    except Exception as e:
        print("TPEx official foreign flow", d, e)
        return None


def fetch_market_foreign_flow(need=5, lookback=18):
    """Return the latest complete TWSE+TPEx official foreign cash-flow record and recent trend."""
    records = []
    today = now_tw().date()
    for i in range(lookback):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        twse = _twse_foreign_value(d)
        tpex = _tpex_foreign_value(d)
        # Market-level score only accepts a complete listed + OTC pair.
        if twse is None or tpex is None:
            continue
        total = twse + tpex
        records.append({
            "date": d.isoformat(),
            "twse": twse,
            "tpex": tpex,
            "total": total,
        })
        if len(records) >= need:
            break

    if not records:
        return {
            "date": None, "twse_net": None, "tpex_net": None,
            "total_net": None, "five_day_net": None, "count": 0, "days": []
        }

    latest = records[0]
    return {
        "date": latest["date"],
        "twse_net": latest["twse"],
        "tpex_net": latest["tpex"],
        "total_net": latest["total"],
        "five_day_net": sum(x["total"] for x in records),
        "count": len(records),
        "days": records,
    }


def _foreign_market_score(flow):
    """Foreign component 0~3: latest direction 0.5~2 points + recent cumulative trend 0~1 point."""
    net = flow.get("total_net")
    trend = flow.get("five_day_net")
    count = int(flow.get("count") or 0)
    if net is None:
        return 1.5

    if net > 0:
        base = 2.0
    elif net < 0:
        base = 0.5
    else:
        base = 1.0

    if trend is None or count < 3:
        bonus = 0.5
    elif trend > 0:
        bonus = 1.0
    elif trend == 0:
        bonus = 0.5
    else:
        bonus = 0.0
    return round(min(3.0, max(0.0, base + bonus)), 1)


def build_market(breadth_pct, chips=None, expected_trade_date=None):
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
    # 開盤早段也要能掃描；累積至少 4 根 5 分K 即可開始判斷。
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
    typical = (today["High"] + today["Low"] + today["Close"]) / 3
    turnover_s = typical * v
    vwap_s = turnover_s.cumsum() / v.cumsum().replace(0, np.nan)
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
    pace = float(v.sum() / np.median(vals)) if vals and np.median(vals) > 0 else 1.0

    if not prev.empty:
        d = sorted(set(prev.index.date))[-1]
        prev_close = float(prev[prev.index.date == d]["Close"].iloc[-1])
    else:
        prev_close = float(c.iloc[0])
    day_change = (cur / prev_close - 1) * 100 if prev_close else 0
    ret15 = (c.iloc[-1] / c.iloc[-4] - 1) * 100 if len(c) >= 4 else 0
    ret60 = (c.iloc[-1] / c.iloc[-13] - 1) * 100 if len(c) >= 13 else None
    vwap_dist = (cur / vwap - 1) * 100 if vwap else 0

    # v1.5.5 振幅效率：只升級既有量價/追價風險，不新增總分權重。
    day_high = float(today["High"].max())
    day_low = float(today["Low"].min())
    day_range = max(0.0, day_high - day_low)
    amplitude_pct = (day_range / prev_close * 100) if prev_close else 0.0
    range_position_pct = ((cur - day_low) / day_range * 100) if day_range > 0 else 50.0
    range_position_pct = max(0.0, min(100.0, range_position_pct))
    amplitude_efficiency = (day_change / amplitude_pct) if amplitude_pct > 1e-9 else 0.0

    # 同時段振幅基準：欄位支援最多20個歷史交易日；現行5日5分K來源
    # 會先用可取得的歷史樣本暖機。只有樣本>=3才讓倍數參與評分。
    all_dates = sorted(set(x.index.date))
    cutoff_time = today.index[-1].time()
    amp_samples = []
    for d0 in [d for d in all_dates if d < latest][-20:]:
        hist = x[x.index.date == d0]
        hist = hist[[ts.time() <= cutoff_time for ts in hist.index]]
        if hist.empty:
            continue
        earlier = [d for d in all_dates if d < d0]
        if not earlier:
            continue
        pd0 = earlier[-1]
        pday = x[x.index.date == pd0]
        if pday.empty:
            continue
        hist_prev_close = float(pday["Close"].iloc[-1])
        if hist_prev_close <= 0:
            continue
        hist_range = float(hist["High"].max() - hist["Low"].min())
        hist_amp = hist_range / hist_prev_close * 100
        if np.isfinite(hist_amp) and hist_amp >= 0:
            amp_samples.append(float(hist_amp))

    amp_sample_days = len(amp_samples)
    same_time_amp_avg_pct = float(np.mean(amp_samples)) if amp_samples else None
    amplitude_multiple = (amplitude_pct / same_time_amp_avg_pct) if same_time_amp_avg_pct and same_time_amp_avg_pct > 1e-9 else None
    amp_baseline_ready = bool(amp_sample_days >= 3 and amplitude_multiple is not None)

    # Step 6：同一個股、同一時間點的歷史分布。
    day_abs_samples, vwap_abs_samples, ret15_abs_samples = [], [], []
    prior_dates = [d for d in all_dates if d < latest][-20:]
    for d0 in prior_dates:
        hist = x[x.index.date == d0]
        hist = hist[[ts.time() <= cutoff_time for ts in hist.index]]
        if hist.empty:
            continue
        earlier = [d for d in all_dates if d < d0]
        if not earlier:
            continue
        pday = x[x.index.date == earlier[-1]]
        if pday.empty:
            continue
        hpclose = float(pday["Close"].iloc[-1])
        if hpclose <= 0:
            continue
        hclose = float(hist["Close"].iloc[-1])
        htyp = (hist["High"] + hist["Low"] + hist["Close"]) / 3
        hvwap_s = (htyp * hist["Volume"]).cumsum() / hist["Volume"].cumsum().replace(0, np.nan)
        hvwap = _finite(hvwap_s.iloc[-1])
        day_abs_samples.append(abs((hclose / hpclose - 1) * 100))
        if hvwap and hvwap > 0:
            vwap_abs_samples.append(abs((hclose / hvwap - 1) * 100))
        if len(hist) >= 4:
            ret15_abs_samples.append(abs((hclose / float(hist["Close"].iloc[-4]) - 1) * 100))

    dynamic_sample_days = len(day_abs_samples)
    same_time_day_abs_p90 = float(np.quantile(day_abs_samples, .90)) if len(day_abs_samples) >= 3 else None
    same_time_vwap_abs_p90 = float(np.quantile(vwap_abs_samples, .90)) if len(vwap_abs_samples) >= 3 else None
    same_time_ret15_abs_p90 = float(np.quantile(ret15_abs_samples, .90)) if len(ret15_abs_samples) >= 3 else None

    # 狀態只用來修正既有量價25與追價風險10，不形成新的分數桶。
    expanded = bool((amp_baseline_ready and amplitude_multiple >= 1.25) or (not amp_baseline_ready and amplitude_pct >= 4.5))
    compressed = bool(amp_baseline_ready and amplitude_multiple <= 0.90)
    if expanded and range_position_pct >= 80 and amplitude_efficiency >= 0.55 and cur >= vwap:
        amplitude_regime = "有效擴張"
    elif expanded and range_position_pct <= 40 and cur < vwap and amplitude_efficiency <= 0.25:
        amplitude_regime = "沖高回落"
    elif expanded and abs(amplitude_efficiency) < 0.30:
        amplitude_regime = "高震盪"
    elif compressed and cur >= vwap and 45 <= range_position_pct <= 85 and amplitude_efficiency >= 0:
        amplitude_regime = "健康整理"
    else:
        amplitude_regime = "中性"

    # 資金輪動用：目前累積成交金額，以及最近一段 vs 前一段成交金額。
    current_turnover = float(turnover_s.sum())
    pair_n = min(6, len(today) // 2)  # 最多比較最近30分鐘 vs 前30分鐘
    if pair_n >= 3:
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
    if amplitude_regime == "高震盪":
        over.append("高振幅低效率")
    elif amplitude_regime == "沖高回落":
        over.append("振幅擴大後沖高回落")

    sr = intraday_sr(x, vwap)
    return {
        "date": str(latest), "time": x.index[-1].strftime("%H:%M"),
        "close": cur, "pace": round(pace, 2), "vwap": round(vwap, 2),
        "vwap_dist": round(vwap_dist, 2), "day_change": round(day_change, 2),
        "ret15": round(ret15, 2),
        "ret60": round(ret60, 2) if ret60 is not None else None,
        "amplitude_pct": round(amplitude_pct, 2),
        "range_position_pct": round(range_position_pct, 1),
        "amplitude_efficiency": round(amplitude_efficiency, 3),
        "same_time_amp_avg_pct": round(same_time_amp_avg_pct, 2) if same_time_amp_avg_pct is not None else None,
        "amplitude_multiple": round(amplitude_multiple, 3) if amplitude_multiple is not None else None,
        "amp_sample_days": amp_sample_days,
        "amp_baseline_ready": amp_baseline_ready,
        "dynamic_sample_days": dynamic_sample_days,
        "same_time_day_abs_p90": round(same_time_day_abs_p90, 3) if same_time_day_abs_p90 is not None else None,
        "same_time_vwap_abs_p90": round(same_time_vwap_abs_p90, 3) if same_time_vwap_abs_p90 is not None else None,
        "same_time_ret15_abs_p90": round(same_time_ret15_abs_p90, 3) if same_time_ret15_abs_p90 is not None else None,
        "amplitude_regime": amplitude_regime,
        "break3": b3, "break12": b12, "trend5": trend,
        "current_turnover": round(current_turnover, 0),
        "recent_turnover": round(recent_turnover, 0) if recent_turnover is not None else None,
        "previous_turnover": round(previous_turnover, 0) if previous_turnover is not None else None,
        "rotation_window_min": rotation_window_min,
        "technical_score": max(0, min(50, round(score, 1))),
        "reasons": reasons, "overheat_reasons": over, **sr,
    }



def _finite(v):
    try:
        z = float(v)
        return z if np.isfinite(z) else None
    except Exception:
        return None


def _clamp(v, lo, hi):
    return max(float(lo), min(float(hi), float(v)))


def _dynamic_threshold_values(r, daily_profile=None):
    """個股動態門檻；只替換門檻，不改任何分數桶權重。"""
    dp = daily_profile or r.get("dynamic_profile") or {}
    atr = _finite(dp.get("atr14_pct"))
    d1p90 = _finite(dp.get("abs_ret1_p90"))
    vxp90 = _finite(dp.get("vol_x_p90"))
    same_day = _finite(r.get("same_time_day_abs_p90"))
    same_vwap = _finite(r.get("same_time_vwap_abs_p90"))
    same_ret15 = _finite(r.get("same_time_ret15_abs_p90"))
    same_n = int(r.get("dynamic_sample_days") or r.get("amp_sample_days") or 0)
    daily_ready = bool(dp.get("ready"))

    evidence = []
    if atr is not None:
        evidence.append("ATR14")
    if daily_ready:
        evidence.append("近60日個股分布")
    if same_n >= 3:
        evidence.append("同時段歷史分布")
    ready = bool(daily_ready and atr is not None and same_n >= 3)

    if not evidence:
        return {
            "version": "1.0", "ready": False, "mode": "fallback",
            "day_hot_pct": 8.5, "vwap_hot_pct": 4.5,
            "ret15_hot_pct": 4.0, "pace_hot_x": 5.0,
            "day_good_high_pct": 6.5, "ret15_good_high_pct": 2.5,
            "atr14_pct": None, "sample_days": same_n,
            "evidence": [], "note": "歷史基準尚未建立，暫用舊版固定門檻",
        }

    day_candidates = [6.0]
    if atr is not None:
        day_candidates.append(atr * 2.0)
    if d1p90 is not None:
        day_candidates.append(d1p90 * 1.15)
    if same_day is not None:
        day_candidates.append(same_day * 1.25)
    day_hot = _clamp(max(day_candidates), 6.0, 9.5)

    vwap_candidates = [2.2]
    if atr is not None:
        vwap_candidates.append(atr * 0.90)
    if same_vwap is not None:
        vwap_candidates.append(same_vwap * 1.25)
    vwap_hot = _clamp(max(vwap_candidates), 2.2, 6.0)

    ret15_candidates = [2.0]
    if atr is not None:
        ret15_candidates.append(atr * 0.70)
    if same_ret15 is not None:
        ret15_candidates.append(same_ret15 * 1.30)
    ret15_hot = _clamp(max(ret15_candidates), 2.0, 5.0)

    pace_candidates = [3.5]
    if vxp90 is not None:
        pace_candidates.append(vxp90 * 1.10)
    pace_hot = _clamp(max(pace_candidates), 3.5, 6.5)

    return {
        "version": "1.0", "ready": ready,
        "mode": "personalized" if ready else "warming",
        "day_hot_pct": round(day_hot, 2),
        "vwap_hot_pct": round(vwap_hot, 2),
        "ret15_hot_pct": round(ret15_hot, 2),
        "pace_hot_x": round(pace_hot, 2),
        "day_good_high_pct": round(_clamp(day_hot * 0.72, 3.5, 7.0), 2),
        "ret15_good_high_pct": round(_clamp(ret15_hot * 0.62, 1.3, 3.0), 2),
        "atr14_pct": round(atr, 2) if atr is not None else None,
        "sample_days": same_n,
        "evidence": evidence,
        "note": "個股自己的ATR／歷史分布門檻" if ready else "部分個股化；樣本不足的部分仍採保守下限",
    }


def _apply_dynamic_thresholds(r, daily_profile=None):
    dyn = _dynamic_threshold_values(r, daily_profile)
    r["dynamic_thresholds"] = dyn
    day = _finite(r.get("day_change")) or 0.0
    vwap_dist = _finite(r.get("vwap_dist")) or 0.0
    pace = _finite(r.get("pace")) or 0.0
    ret15 = _finite(r.get("ret15")) or 0.0
    over = []
    if day >= float(dyn["day_hot_pct"]):
        over.append(f"漲幅超過個股門檻 {dyn['day_hot_pct']:.1f}%")
    if vwap_dist > float(dyn["vwap_hot_pct"]):
        over.append(f"距VWAP超過個股門檻 {dyn['vwap_hot_pct']:.1f}%")
    if pace > float(dyn["pace_hot_x"]):
        over.append(f"量速超過個股門檻 {dyn['pace_hot_x']:.1f}x")
    if ret15 > float(dyn["ret15_hot_pct"]):
        over.append(f"15分鐘漲幅超過個股門檻 {dyn['ret15_hot_pct']:.1f}%")
    amp = str(r.get("amplitude_regime") or "")
    if amp == "高震盪":
        over.append("高振幅低效率")
    elif amp == "沖高回落":
        over.append("振幅擴大後沖高回落")
    r["overheat_reasons"] = over
    return r


def _refresh_dynamic_thresholds(rows, close_map):
    for r in rows or []:
        _apply_dynamic_thresholds(r, (close_map or {}).get(str(r.get("code") or "")) or {})
    return rows


def _chip_background_label(score, coverage):
    try:
        sc = float(score)
        cov = float(coverage or 0)
    except Exception:
        return "資料不足"
    if cov < 40:
        return "資料不足"
    if sc >= 18:
        return "偏多"
    if sc <= 9:
        return "偏空"
    return "中性"


def _intraday_score_parts(r, market, sector_score_10):
    """盤中執行分 0~100；籌碼不計分，只作背景。

    30 價格結構 + 25 量價/動能 + 15 相對強弱 + 20 族群 + 10 流動性/追價風險。
    """
    close = float(r.get("close") or 0)
    vwap = float(r.get("vwap") or 0)
    pace = float(r.get("pace") or 0)
    day = float(r.get("day_change") or 0)
    ret15 = float(r.get("ret15") or 0)
    amp_regime = str(r.get("amplitude_regime") or "中性")
    amp_multiple = r.get("amplitude_multiple")
    amp_ready = bool(r.get("amp_baseline_ready"))
    range_pos = float(r.get("range_position_pct") or 50)
    dyn = r.get("dynamic_thresholds") or {}
    day_good_high = float(dyn.get("day_good_high_pct") or 6.5)
    ret15_good_high = float(dyn.get("ret15_good_high_pct") or 2.5)
    pace_hot = float(dyn.get("pace_hot_x") or 5.0)

    price = 0.0
    if vwap > 0 and close > vwap:
        price += 10
    if r.get("break3"):
        price += 8
    if r.get("break12"):
        price += 6
    if r.get("trend5"):
        price += 6
    price = min(30.0, price)

    flow = 0.0
    # 原本的量速權重仍在量價/動能25分內；振幅效率只修正量速品質。
    if 1.5 <= pace < 3.5:
        pace_points = 15.0
    elif 1.2 <= pace < 1.5:
        pace_points = 10.0
    elif 3.5 <= pace <= pace_hot:
        pace_points = 10.0
    elif pace >= 1.0:
        pace_points = 5.0
    else:
        pace_points = 0.0

    if amp_regime == "有效擴張":
        pace_points = min(15.0, pace_points + 2.0)
    elif amp_regime == "高震盪":
        pace_points = max(0.0, pace_points - 4.0)
    elif amp_regime == "沖高回落":
        pace_points = max(0.0, pace_points - 6.0)
    flow += pace_points

    if 0.2 <= ret15 <= ret15_good_high:
        flow += 6
    elif ret15 > 0:
        flow += 3
    if 0.5 <= day <= day_good_high:
        flow += 4
    elif 0 < day < 0.5:
        flow += 2
    flow = min(25.0, flow)

    comps = (market or {}).get("components") or {}
    side = "otc" if str(r.get("market")) == "上櫃" else "taiex"
    bench = ((comps.get(side) or {}).get("change_pct"))
    try:
        bench = float(bench) if bench is not None else 0.0
    except Exception:
        bench = 0.0
    rel_pct = day - bench
    if rel_pct >= 2.0:
        relative = 10.0
    elif rel_pct >= 1.0:
        relative = 8.0
    elif rel_pct >= 0.3:
        relative = 6.0
    elif rel_pct >= 0:
        relative = 4.0
    elif rel_pct > -1.0:
        relative = 2.0
    else:
        relative = 0.0
    if close > 0 and vwap > 0 and close >= vwap and ret15 > 0:
        relative += 5.0
    relative = min(15.0, relative)

    sector = max(0.0, min(20.0, float(sector_score_10 or 0) * 2.0))

    level = str(r.get("liquidity_level") or "未知")
    liquidity = 5.0 if level == "活躍" else 4.0 if level == "正常" else 2.0 if level == "偏低" else 3.0
    hot_n = len(r.get("overheat_reasons") or [])
    risk = 5.0 if hot_n == 0 else 2.0 if hot_n == 1 else 0.0
    if float(r.get("vwap_dist") or 0) < -2.0:
        risk = max(0.0, risk - 2.0)
    # 振幅效率只調整原本的「追價風險」5分，不增加10分上限。
    if amp_regime == "高震盪":
        risk = max(0.0, risk - 2.0)
    elif amp_regime == "沖高回落":
        risk = max(0.0, risk - 3.0)
    elif amp_regime == "有效擴張" and amp_ready and amp_multiple is not None and float(amp_multiple) >= 1.6 and range_pos >= 95:
        # 強勢是真的，但若已貼近極端高檔且振幅明顯擴張，仍降低追價安全度。
        risk = max(0.0, risk - 1.0)
    liquidity_risk = min(10.0, liquidity + risk)

    total = max(0.0, min(100.0, price + flow + relative + sector + liquidity_risk))
    return round(total, 1), {
        "price_structure": round(price, 1),
        "flow_volume": round(flow, 1),
        "relative_strength": round(relative, 1),
        "relative_strength_pct": round(rel_pct, 2),
        "sector": round(sector, 1),
        "liquidity_risk": round(liquidity_risk, 1),
    }



def _swing_liquidity_score(r):
    """盤後波段延續的流動性 0~10；不和進場位置混在一起。"""
    level = str(r.get("liquidity_level") or "未知")
    if level == "活躍":
        return 10.0
    if level == "正常":
        return 8.0
    if level == "偏低":
        return 5.0
    if level == "不足":
        return 0.0
    return 6.0

def _close_entry_position_score(r):
    """波段進場位置 0~100；和『這家公司/趨勢好不好』分開。"""
    score = 40.0
    if r.get("trend"):
        score += 10
    if r.get("break20"):
        score += 5
    elif r.get("break3"):
        score += 3

    try:
        dist = float(r.get("dist20"))
    except Exception:
        dist = 999.0
    if 0 <= dist <= 3:
        score += 20
    elif dist <= 7:
        score += 15
    elif dist <= 10:
        score += 8
    elif dist <= 15:
        score += 2
    elif dist < 0:
        score -= 10
    else:
        score -= 10

    try:
        vx = float(r.get("vol_x"))
    except Exception:
        vx = 0.0
    if 1.2 <= vx <= 2.5:
        score += 10
    elif 0.8 <= vx < 1.2:
        score += 5
    elif vx > 4:
        score -= 5

    try:
        ret5 = float(r.get("ret5"))
    except Exception:
        ret5 = 999.0
    if 0 <= ret5 <= 8:
        score += 10
    elif ret5 <= 15:
        score += 5
    elif ret5 > 20:
        score -= 10

    sup = r.get("support") or {}
    try:
        upper = float(sup.get("high"))
        close = float(r.get("close"))
        if upper > 0 and close >= upper and (close / upper - 1) <= 0.03:
            score += 5
    except Exception:
        pass

    score -= min(25.0, 10.0 * len(r.get("overheat_reasons") or []))
    return round(max(0.0, min(100.0, score)), 1)


def _assign_stage_v2(r, preliminary_intraday, sector_score_10):
    """Stage Engine 2.0：只判斷生命週期，不改任何100分權重。

    原則：
    1) 發動與蓄勢要有多項證據，不因單一指標亮燈。
    2) 轉弱與失效分開；失效採保守多證據確認，避免一根雜訊K誤殺。
    3) 盤中看 VWAP / 5分結構 / 相對市場 / 族群；盤後看均線 / MACD / 量價 / 籌碼 / 族群。
    """
    def f(key, default=0.0):
        try:
            v = r.get(key)
            return float(v) if v is not None else float(default)
        except Exception:
            return float(default)

    r["stage_version"] = "2.0"
    r["stage_signals"] = []
    r["stage_risks"] = []

    over = list(r.get("overheat_reasons") or [])
    if over:
        r["category"] = "過熱不追"
        r["stage_reason"] = "趨勢可能仍強，但短線延伸或波動已不適合追價"
        r["stage_risks"] = over[:4]
        return

    sec = float(sector_score_10 or 0)

    if preliminary_intraday:
        close = f("close")
        vwap = f("vwap")
        pace = f("pace")
        ret15 = f("ret15")
        tech = f("technical_score")
        score = f("intraday_score", f("score"))
        rel = float(((r.get("intraday_components") or {}).get("relative_strength_pct")) or 0)
        trend5 = bool(r.get("trend5"))
        break3 = bool(r.get("break3"))
        break12 = bool(r.get("break12"))
        above_vwap = bool(vwap > 0 and close >= vwap)
        near_vwap = bool(vwap > 0 and close >= vwap * 0.995 and close <= vwap * 1.02)
        mtf = r.get("multi_timeframe") or {}
        mtf60 = mtf.get("60m") or {}
        mtfd = mtf.get("daily") or {}
        mtf_60_available = bool(mtf60.get("available"))
        mtf_60_state = str(mtf60.get("state") or "")
        mtf_60_supportive = bool(mtf60.get("supportive"))
        mtf_60_bearish = bool(mtf60.get("bearish"))
        mtf_daily_weak = str(mtfd.get("state") or "") == "WEAK"
        mtf_daily_supportive = str(mtfd.get("state") or "") == "BULLISH"
        rel_mtf = r.get("relative_multiframe") or {}
        rel_mtf_status = str(rel_mtf.get("status") or "")
        rel_mtf_lagging = rel_mtf_status == "LAGGING"
        rel_mtf_supportive = rel_mtf_status in {"LEADING", "IMPROVING"}

        invalid_flags = [
            (vwap > 0 and close < vwap * 0.985, "明顯跌破VWAP"),
            (ret15 <= -1.0, "近15分鐘明顯走弱"),
            (not trend5, "5分短均未維持多頭"),
            (rel <= -1.0, "明顯弱於所屬市場"),
            (score < 50, "盤中動能低於50"),
        ]
        invalid_hits = [txt for ok, txt in invalid_flags if ok]
        if vwap > 0 and close < vwap * 0.975 and len(invalid_hits) >= 4 and score < 45 and rel <= -0.5:
            r["category"] = "結構失效"
            r["stage_reason"] = "價格明顯跌離VWAP，且短線動能、趨勢與相對強弱多項同步失守"
            r["stage_risks"] = invalid_hits[:4]
            return

        launch = bool(
            break3 and above_vwap and pace >= 1.1 and rel >= 0
            and (trend5 or break12 or tech >= 22)
            and not (mtf_60_available and mtf_60_bearish)
            and not rel_mtf_lagging
        )
        if launch:
            r["category"] = "剛啟動"
            r["stage_reason"] = "突破＋站上VWAP＋量速與相對強度同步轉強"
            launch_signals = ["3K突破", "站上VWAP", f"量速{pace:.1f}x", f"相對市場{rel:+.1f}%"]
            if mtf_60_supportive:
                launch_signals.append(f"60K {mtf60.get('label') or '20T/60T支持'}")
            if mtf_daily_supportive:
                launch_signals.append("日K背景偏多")
            if rel_mtf_supportive:
                launch_signals.append(rel_mtf.get("label") or "多時框相對強弱改善")
            r["stage_signals"] = launch_signals[:5]
            return

        pullback = bool(
            (break12 or score >= 70)
            and near_vwap
            and -1.0 <= ret15 <= 1.2
            and rel >= -0.3
            and (trend5 or tech >= 25)
        )
        if pullback:
            r["category"] = "回踩承接"
            r["stage_reason"] = "原結構仍強，價格回到VWAP附近測試承接"
            r["stage_signals"] = ["靠近VWAP", "短線結構未破", "相對市場未明顯轉弱"]
            return

        trend_hold = bool(
            score >= 70 and above_vwap and rel >= 0
            and (trend5 or break12)
            and not (mtf_60_available and mtf_60_bearish)
            and not rel_mtf_lagging
        )
        if trend_hold:
            r["category"] = "趨勢持有"
            r["stage_reason"] = "動能、VWAP與相對市場仍支持既有上升趨勢"
            r["stage_signals"] = ["站上VWAP", f"盤中動能{score:.0f}", f"相對市場{rel:+.1f}%"]
            return

        setup_flags = [
            (near_vwap, "價格貼近VWAP"),
            (0.8 <= pace <= 2.5, "量速溫和升溫"),
            (rel >= -0.2, "沒有明顯落後市場"),
            (sec >= 5.0, "族群有共振"),
            (trend5 or break12 or tech >= 20, "短線結構正在靠攏"),
            (-0.5 <= ret15 <= 1.5, "15分鐘未急拉急殺"),
            (mtf_60_supportive, f"60K {mtf60.get('label') or '20T/60T結構支持'}"),
            (mtf_daily_supportive, "日K背景仍支持"),
            (rel_mtf_supportive, rel_mtf.get("label") or "多時框相對強弱改善"),
        ]
        setup_hits = [txt for ok, txt in setup_flags if ok]
        mtf_setup_ok = (not mtf_60_available) or mtf_60_supportive or mtf_60_state == "PRE_CROSS"
        if not break3 and score >= 55 and len(setup_hits) >= 4 and mtf_setup_ok:
            r["category"] = "蓄勢待發"
            r["stage_reason"] = "尚未正式突破，但價格、量能、相對強弱與族群條件正在集中"
            r["stage_signals"] = setup_hits[:4]
            return

        weak_flags = [
            (vwap > 0 and close < vwap, "跌回VWAP下方"),
            (ret15 < -0.3, "近15分鐘轉弱"),
            (rel < -0.3, "開始落後所屬市場"),
            (pace < 0.8, "量能降溫"),
            (sec < 4.0, "族群共振偏弱"),
            (not trend5, "5分短均未維持多頭"),
            (mtf_60_available and mtf_60_bearish, "60K 20T/60T結構偏弱"),
            (mtf_daily_weak, "日K背景偏弱"),
            (rel_mtf_lagging, "15分／60分／當日／5日相對強弱多數落後"),
        ]
        weak_hits = [txt for ok, txt in weak_flags if ok]
        core_weak = bool(
            (vwap > 0 and close < vwap)
            or ret15 <= -0.8
            or rel <= -0.8
            or score < 50
        )
        if core_weak and len(weak_hits) >= 4:
            r["category"] = "轉弱警戒"
            r["stage_reason"] = "價格／相對強弱已有弱化，且量能、短線趨勢或族群等訊號同步轉差"
            r["stage_risks"] = weak_hits[:4]
            return

        r["category"] = "觀察"
        r["stage_reason"] = "目前沒有形成明確蓄勢、發動或轉弱共識"
        return

    # ---- 盤後波段 Stage 2.0 ----
    close = f("close")
    ma5 = f("ma5")
    ma10 = f("ma10")
    ma20 = f("ma20")
    dist20 = f("dist20", 999)
    ret5 = f("ret5", 999)
    day = f("day_change")
    vol = f("vol_x")
    rsi_v = f("rsi")
    macd_h = f("macd_h")
    macd_acc = f("macd_acc")
    tech = f("technical_score")
    swing = f("swing_quality_score", f("score"))
    chip = f("chip_score", 12.5)
    chip_cov = f("chip_coverage_pct")
    trend = bool(r.get("trend"))
    break3 = bool(r.get("break3"))
    break20 = bool(r.get("break20"))

    below20 = bool(ma20 > 0 and close < ma20)
    invalid_flags = [
        (ma20 > 0 and close < ma20 * 0.97, "收盤明顯跌破20MA"),
        (ma5 > 0 and ma10 > 0 and ma5 < ma10, "5MA跌破10MA"),
        (ma10 > 0 and ma20 > 0 and ma10 < ma20, "10MA跌破20MA"),
        (macd_h < 0, "MACD柱體在零軸下"),
        (ret5 <= -5, "近5日明顯回落"),
        (tech < 18, "日K技術分偏低"),
    ]
    invalid_hits = [txt for ok, txt in invalid_flags if ok]
    hard_break20 = bool(ma20 > 0 and close < ma20 * 0.96)
    midtrend_broken = bool(ma10 > 0 and ma20 > 0 and ma10 < ma20)
    deep_momentum_loss = bool(ret5 <= -8 or (macd_h < 0 and tech < 14))
    if hard_break20 and midtrend_broken and deep_momentum_loss and len(invalid_hits) >= 4:
        r["category"] = "結構失效"
        r["stage_reason"] = "明顯跌破20MA，且中期均線與動能同步失守；原波段結構需重新評估"
        r["stage_risks"] = invalid_hits[:4]
        return

    launch_structure = bool(break20 or (break3 and trend))
    launch = bool(
        launch_structure and vol >= 1.2 and dist20 <= 12 and ret5 <= 18
        and close >= ma20 and (tech >= 28 or swing >= 65)
    )
    if launch:
        r["category"] = "剛啟動"
        r["stage_reason"] = "突破結構成立，量能與波段品質同步支持發動"
        r["stage_signals"] = ["20日突破" if break20 else "3日平台突破", f"量比{vol:.1f}x", f"距20MA {dist20:+.1f}%"]
        return

    pullback = bool(
        close >= ma20 * 0.995
        and -0.5 <= dist20 <= 8
        and ret5 <= 12
        and day <= 1.5
        and vol <= 1.8
        and (trend or swing >= 72 or tech >= 30)
    )
    if pullback:
        r["category"] = "回踩承接"
        r["stage_reason"] = "既有趨勢尚未破壞，價格回到20MA／支撐附近等待承接"
        r["stage_signals"] = ["守在20MA附近", "短線未過度延伸", "量能未失控"]
        return

    trend_structure = bool(
        ma20 > 0 and close >= ma20
        and ma5 > 0 and ma10 > 0
        and ma5 >= ma10
        and ma10 >= ma20 * 0.995
    )
    trend_hold = bool(
        (trend or trend_structure)
        and (swing >= 60 or tech >= 30)
        and 1.5 <= dist20 <= 15
        and -2 <= ret5 <= 22
    )
    if trend_hold:
        r["category"] = "趨勢持有"
        r["stage_reason"] = "均線與波段延續分仍支持上升趨勢，重點是守住主要支撐"
        r["stage_signals"] = ["均線多頭", f"波段延續{swing:.0f}", f"距20MA {dist20:+.1f}%"]
        return

    # 蓄勢分不是新的交易總分，只用來確認「突破前條件集中度」。
    setup_points = 0
    setup_hits = []
    def add_setup(ok, pts, label):
        nonlocal setup_points
        if ok:
            setup_points += pts
            setup_hits.append(label)

    add_setup(ma20 > 0 and close >= ma20 * 0.99, 20, "守在20MA附近或上方")
    add_setup(ma5 > 0 and ma10 > 0 and ma5 >= ma10 * 0.995, 15, "5MA與10MA靠攏偏多")
    add_setup(macd_acc > 0 or macd_h > 0, 15, "MACD動能改善")
    add_setup(48 <= rsi_v <= 68, 10, "RSI位於健康蓄力區")
    add_setup(0.6 <= vol <= 1.8, 10, "量能沒有失控")
    add_setup(-1.5 <= dist20 <= 8, 10, "位置未過度延伸")
    add_setup(-3 <= ret5 <= 10, 10, "近5日仍在可蓄勢區")
    add_setup(chip_cov < 60 or chip >= 12.5, 5, "籌碼未明顯拖累")
    add_setup(sec >= 5.0, 5, "族群已有共振")

    if not trend and not break20 and setup_points >= 65 and tech >= 20:
        r["category"] = "蓄勢待發"
        r["stage_reason"] = "尚未完成正式突破，但均線、動能、位置、量能與籌碼／族群條件正在集中"
        r["stage_signals"] = setup_hits[:5]
        r["setup_evidence_score"] = setup_points
        return

    weak_flags = [
        (below20, "收盤跌到20MA下方"),
        (ma5 > 0 and ma10 > 0 and ma5 < ma10, "5MA低於10MA"),
        (macd_acc < 0, "MACD動能下降"),
        (ret5 < 0, "近5日報酬轉負"),
        (chip_cov >= 60 and chip < 10, "籌碼分偏弱"),
        (sec < 4.0, "族群共振偏弱"),
        (swing < 60, "波段延續分下降"),
    ]
    weak_hits = [txt for ok, txt in weak_flags if ok]
    # Final calibration：庫存管理的「轉弱警戒」必須比一般回檔更嚴格。
    # 核心價格/均線真的弱化 + 至少五項證據才亮警報，避免盤整股滿屏警告。
    ma_short_broken = bool(ma5 > 0 and ma10 > 0 and ma5 < ma10)
    core_weak = bool(
        (below20 and ma_short_broken)
        or swing < 48
        or (macd_h < 0 and macd_acc < 0 and ret5 <= -2)
    )
    if core_weak and len(weak_hits) >= 5:
        r["category"] = "轉弱警戒"
        r["stage_reason"] = "價格／短均已有明確弱化，且至少五項技術、動能、籌碼或族群訊號同步轉差；尚未確認結構失效"
        r["stage_risks"] = weak_hits[:5]
        return

    r["category"] = "觀察"
    r["stage_reason"] = "目前條件尚未集中成蓄勢／發動，也沒有足夠證據判定轉弱"


def add_component_scores(rows, market, preliminary_intraday=False):
    """加入族群分、總分、階段與品質。

    v1.2 起把「階段」和「品質」拆開：
    - 階段主要看價格行為、量能與位階。
    - 品質才用 100 分總分衡量。
    """
    if not rows:
        return rows

    # 次產業/題材優先；沒有窄群組時，用官方產業廣度作為「代理分」，且上限 6 分。
    hot = {}
    industry_hot = {}
    industry_total = {}
    for r in rows:
        key = str(r.get("sector_group") or "").strip()
        industry = str(r.get("industry_name") or "").strip()
        if industry and industry != "未分類":
            industry_total[industry] = industry_total.get(industry, 0) + 1
        is_hot = r.get("technical_score", 0) >= 30 and not r.get("overheat_reasons")
        if is_hot:
            if key:
                hot[key] = hot.get(key, 0) + 1
            if industry and industry != "未分類":
                industry_hot[industry] = industry_hot.get(industry, 0) + 1

    def _resonance_stats(group_rows):
        total = len(group_rows)
        if not total:
            return {"score": 0.0, "count": 0, "strong_count": 0}
        strong = [x for x in group_rows if float(x.get("technical_score") or 0) >= 30 and not x.get("overheat_reasons")]
        up_pct = sum(1 for x in group_rows if float(x.get("day_change") or 0) > 0) / total * 100
        strong_pct = len(strong) / total * 100
        avg_tech = sum(float(x.get("technical_score") or 0) for x in group_rows) / total
        acts = []
        for x in group_rows:
            v = x.get("pace") if x.get("pace") is not None else x.get("vol_x")
            if v is not None:
                try: acts.append(float(v))
                except Exception: pass
        avg_activity = sum(acts) / len(acts) if acts else 1.0
        leaders = [x for x in group_rows if float(x.get("technical_score") or 0) >= 35 and float(x.get("day_change") or 0) >= 1]
        trend_hits = sum(1 for x in group_rows if x.get("trend5") or x.get("trend") or x.get("break12") or x.get("break20"))
        continuity_pct = trend_hits / total * 100

        # Strong-stock turnover share is especially useful intraday: two large leaders
        # matter more than many tiny red/green prints.
        total_turn = sum(float(x.get("current_turnover") or 0) for x in group_rows)
        strong_turn = sum(float(x.get("current_turnover") or 0) for x in strong)
        strong_turn_pct = (strong_turn / total_turn * 100) if total_turn > 0 else strong_pct

        breadth_score = 3.0 if up_pct >= 70 else 2.5 if up_pct >= 60 else 1.5 if up_pct >= 50 else 0.5 if up_pct >= 40 else 0.0
        strength_basis = max(strong_pct, strong_turn_pct)
        strength_score = 2.0 if strength_basis >= 60 else 1.5 if strength_basis >= 45 else 1.0 if strength_basis >= 30 else 0.5 if avg_tech >= 25 else 0.0
        volume_score = 2.0 if avg_activity >= 2.0 else 1.5 if avg_activity >= 1.5 else 1.0 if avg_activity >= 1.2 else 0.5 if avg_activity >= 1.0 else 0.0
        leader_score = 2.0 if len(leaders) >= 2 else 1.2 if len(leaders) == 1 else 0.0
        continuity_score = 1.0 if continuity_pct >= 60 else 0.5 if continuity_pct >= 40 else 0.0
        score = round(min(10.0, breadth_score + strength_score + volume_score + leader_score + continuity_score), 1)
        return {
            "score": score, "count": total, "strong_count": len(strong),
            "up_pct": round(up_pct, 1), "strong_pct": round(strong_pct, 1),
            "strong_turnover_pct": round(strong_turn_pct, 1),
            "avg_technical": round(avg_tech, 1), "activity": round(avg_activity, 2),
            "leader_count": len(leaders), "continuity_pct": round(continuity_pct, 1),
            "components": {
                "breadth": breadth_score, "strength": strength_score,
                "volume": volume_score, "leaders": leader_score,
                "continuity": continuity_score,
            },
        }

    quality_reference = 76
    market_score = float(market.get("market_score", 7.5))

    # Step 7：只讀「上一輪已完成」的歷史校準，確保今天的結果不會回頭改今天的分數。
    _baseline_swing_weights = {"technical": 50.0, "chip": 25.0, "sector": 15.0, "liquidity": 10.0}
    _validation = load_json("validation.json", {}) if not preliminary_intraday else {}
    _calibration = (_validation.get("calibration") or {}) if isinstance(_validation, dict) else {}
    _calibration_active = bool(_calibration.get("active"))
    _candidate_weights = _calibration.get("active_weights") or {}
    _swing_weights = {}
    for _k, _base in _baseline_swing_weights.items():
        try:
            _swing_weights[_k] = float(_candidate_weights.get(_k, _base)) if _calibration_active else _base
        except Exception:
            _swing_weights[_k] = _base
    _wsum = sum(_swing_weights.values()) or 100.0
    _swing_weights = {k: v / _wsum * 100.0 for k, v in _swing_weights.items()}

    for r in rows:
        key = str(r.get("sector_group") or "").strip()
        industry = str(r.get("industry_name") or "").strip()
        stat = None
        group_rows = []
        if key:
            group_rows = [x for x in rows if str(x.get("sector_group") or "").strip() == key]
            stat = _resonance_stats(group_rows)
            n = int(stat.get("strong_count") or 0)
            sec = float(stat.get("score") or 0)
            source = "次產業多因子"
            label = key
            ratio = (n / len(group_rows)) if group_rows else None
        else:
            n = int(industry_hot.get(industry, 0)) if industry and industry != "未分類" else 0
            total_n = int(industry_total.get(industry, 0)) if industry and industry != "未分類" else 0
            ratio = (n / total_n) if total_n else 0
            sec = sector_score(n, ratio, True)
            source = "官方產業代理" if total_n else "待分類"
            label = industry if total_n else "待分類"
            # v1.5.10：官方產業代理原本只有分數、沒有 peers，導致前端無法展開。
            # 只補同產業成分股清單，不改 sec / ratio / 任何評分公式。
            if total_n:
                group_rows = [
                    x for x in rows
                    if str(x.get("industry_name") or "").strip() == industry
                ]
        r["industry_hot_count"] = int(industry_hot.get(industry, 0)) if industry else 0
        r["sector_hot_count"] = n
        r["sector_score"] = sec
        r["sector_score_source"] = source
        r["sector_score_label"] = label
        r["sector_hot_ratio"] = round(ratio * 100, 1) if ratio is not None else None
        r["sector_detail"] = stat
        if group_rows:
            peers = sorted(group_rows, key=lambda x: (float(x.get("technical_score") or 0), float(x.get("day_change") or 0), float(x.get("current_turnover") or 0)), reverse=True)[:15]
            r["sector_peers"] = [{
                "code": x.get("code"), "name": x.get("name"),
                "technical_score": x.get("technical_score"),
                "score": x.get("score"), "day_change": x.get("day_change"),
                "category": x.get("category"),
            } for x in peers]
        else:
            r["sector_peers"] = []
        r["market_score"] = market_score
        r["market_mode"] = market.get("market_mode", "中性")
        r["market_data_complete"] = bool(market.get("data_complete", True))
        r["market_trade_date"] = market.get("trade_date")

        cs = float(r.get("chip_score", 12.5))
        chip_cov = float(r.get("chip_coverage_pct") or 0)
        liq_adjust = float(r.get("liquidity_adjust", 0))
        r["market_in_quality_score"] = False
        r["chip_background"] = _chip_background_label(cs, chip_cov)
        r["chip_background_score"] = round(cs, 1)

        if preliminary_intraday:
            # v1.5：盤中是執行雷達。籌碼僅作昨日/最近盤後背景，不灌入即時動能分。
            intraday_score, intraday_parts = _intraday_score_parts(r, market, sec)
            r["intraday_score"] = intraday_score
            r["intraday_components"] = intraday_parts
            r["stock_raw_score"] = intraday_score
            r["score"] = intraday_score
            r["score_type"] = "intraday_execution"
            r["score_reliable"] = True
            if intraday_score >= 82:
                r["quality_label"] = "強動能"
            elif intraday_score >= 70:
                r["quality_label"] = "轉強"
            elif intraday_score >= 55:
                r["quality_label"] = "中性"
            else:
                r["quality_label"] = "轉弱"
            r["quality_reference"] = 70
            r["quality_pass_market"] = bool(intraday_score >= 70)
        else:
            # v1.5.1：盤後波段延續直接加總100分，不再先算85再換算。
            # 技術50＋籌碼25＋族群15＋流動性10＝100；進場位置另外獨立100。
            tech_component = max(0.0, min(50.0, float(r.get("technical_score") or 0)))
            chip_component = max(0.0, min(25.0, cs))
            sector_component = max(0.0, min(15.0, float(sec or 0) * 1.5))
            liquidity_component = _swing_liquidity_score(r)
            # 原始 component 尺度仍是 50/25/15/10；校準只調整它們在100分內的相對權重。
            _component_caps = {"technical": 50.0, "chip": 25.0, "sector": 15.0, "liquidity": 10.0}
            _raw_components = {
                "technical": tech_component, "chip": chip_component,
                "sector": sector_component, "liquidity": liquidity_component,
            }
            _weighted_components = {
                k: max(0.0, min(1.0, float(_raw_components[k]) / _component_caps[k])) * float(_swing_weights[k])
                for k in _component_caps
            }
            swing = round(min(100.0, sum(_weighted_components.values())), 1)
            r["swing_components"] = {
                "technical": round(tech_component, 1),
                "chip": round(chip_component, 1),
                "sector": round(sector_component, 1),
                "liquidity": round(liquidity_component, 1),
            }
            r["swing_weighted_components"] = {k: round(v, 1) for k, v in _weighted_components.items()}
            r["swing_weights"] = {k: round(v, 1) for k, v in _swing_weights.items()}
            r["swing_weight_source"] = "historical_calibration" if _calibration_active else "baseline"
            r["calibration_sample_rows"] = int(_calibration.get("sample_rows") or 0)
            r["calibration_sample_dates"] = int(_calibration.get("sample_dates") or 0)
            r["stock_raw_score"] = swing
            r["score"] = swing
            r["swing_quality_score"] = swing
            r["swing_continuation_score"] = swing
            r["entry_position_score"] = _close_entry_position_score(r)
            r["score_type"] = "swing_continuation_direct_100"
            r["score_reliable"] = bool(chip_cov >= 60)
            if not r["score_reliable"]:
                r["quality_label"] = "資料待補"
            elif swing >= 80:
                r["quality_label"] = "高延續"
            elif swing >= 70:
                r["quality_label"] = "強"
            else:
                r["quality_label"] = "一般"
            r["quality_reference"] = quality_reference
            r["quality_pass_market"] = bool(r["score_reliable"] and swing >= quality_reference)

        _assign_stage_v2(r, preliminary_intraday, sec)

    order = {
        "剛啟動": 0, "蓄勢待發": 1, "回踩承接": 2, "趨勢持有": 3,
        "觀察": 4, "轉弱警戒": 5, "結構失效": 6, "過熱不追": 7,
    }
    quality_order = {"強動能": 0, "高延續": 0, "轉強": 1, "強": 1, "中性": 2, "一般": 2, "轉弱": 3, "資料待補": 4}
    rows.sort(key=lambda r: (
        order.get(r["category"], 9),
        quality_order.get(r.get("quality_label"), 9),
        -r["score"]
    ))
    return rows


def build_close():
    uni = get_universe()
    uni["industry_name"] = uni["industry"].map(industry_name_for)
    uni["sector_group"] = [sector_group_for(c, n, i) or "" for c, n, i in zip(uni["code"], uni["name"], uni["industry"])]
    universe_public = uni[["code", "name", "industry", "industry_name", "sector_group", "market"]].astype(str).to_dict("records")
    dump("universe.json", universe_public)
    meta = uni.set_index("symbol").to_dict("index")
    official_today = official_mis_snapshot(uni)
    official_trade_date = max((v.get("date") for v in official_today.values() if v.get("date")), default=None)

    rows = []
    # v1.5.12：沿用這一輪本來就下載的6個月日K，保存各股近期每日收盤價，
    # 供法人「淨股數 × 當日收盤價」估算歷史金額；不額外再打一輪行情來源。
    price_history = {}
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
                m = meta.get(sym, {})
                code = str(m.get("code", sym.split(".")[0]))
                x = overlay_official_today_bar(x, official_today.get(code))
                try:
                    ph = {}
                    for idx, px in x["Close"].dropna().tail(45).items():
                        v = float(px)
                        if np.isfinite(v) and v > 0:
                            ph[str(pd.Timestamp(idx).date())] = v
                    price_history[code] = ph
                except Exception:
                    price_history[code] = {}
                t = close_technical(x)
                if not t:
                    continue
                breadth_changes.append(t["day_change"])
                liq_level, liq_adjust = liquidity_profile(t["avg_turnover20"])
                if liq_level == "不足":
                    continue
                t["liquidity_level"] = liq_level
                t["liquidity_adjust"] = liq_adjust
                t["avg_turnover20_mn"] = round(t["avg_turnover20"] / 1_000_000, 1)
                rows.append({
                    "symbol": sym,
                    "code": code,
                    "name": str(m.get("name", sym)),
                    "industry": str(m.get("industry", "未分類")),
                    "industry_name": str(m.get("industry_name", industry_name_for(m.get("industry")))),
                    "sector_group": str(m.get("sector_group") or ""),
                    "market": str(m.get("market", "")),
                    **t,
                })
            except Exception as e:
                print("daily stock", sym, e)

    # Lock the entire close radar to one completed trading date.  If MIS is temporarily
    # unavailable, use the newest date present in downloaded daily data, then discard older rows.
    trade_date = official_trade_date
    if trade_date is None and rows:
        try:
            trade_date = max(datetime.strptime(str(r.get("date")), "%Y-%m-%d").date() for r in rows if r.get("date"))
        except Exception:
            trade_date = None
    if trade_date is not None:
        td = trade_date.isoformat()
        before = len(rows)
        rows = [r for r in rows if str(r.get("date")) == td]
        print("close trade-date lock", td, "kept", len(rows), "of", before)

    market_map = dict(zip(uni["code"].astype(str), uni["market"].astype(str)))

    # All-market chip fetch is table-based, not 1000 individual HTTP calls.
    chips = build_chip_signals(
        uni["code"].astype(str).tolist(),
        market_map,
        CACHE / "chips"
    )

    # Recompute breadth only from the rows that survived the same-date lock.
    breadth_changes = [float(r.get("day_change", 0)) for r in rows]
    breadth_pct = None
    if breadth_changes:
        breadth_pct = sum(1 for x in breadth_changes if x > 0) / len(breadth_changes) * 100

    market = build_market(breadth_pct, chips, trade_date)

    for r in rows:
        chip = chips.get(r["code"], {})
        cs, coverage = chip_score(chip)
        r.update(chip)
        r["chip_score"] = cs
        r["chip_coverage_pct"] = coverage

    rows = add_component_scores(rows, market, preliminary_intraday=False)
    sector_funds = build_sector_institution_flow(rows, price_history)

    dump("close.json", {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "trade_date": market.get("trade_date"),
        "data_complete": bool(market.get("data_complete")),
        "market": market,
        "sector_funds": sector_funds,
        "sector_funds_note": "外資＋投信官方淨買賣股數 × 各交易日收盤價估算金額；張數保留；未含自營商；估算金額僅供力度比較，不額外計入個股100分",
        "score_formula": {"mode": "swing_direct_100", "technical": 50, "chip": 25, "sector": 15, "liquidity": 10, "total": 100, "normalized": False, "entry_position": 100, "market_separate": 15},
        "rows": rows,
    })
    dump("market.json", market)

    status = load_json("status.json", {})
    status.update({
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "close_updated_at": now_tw().isoformat(timespec="seconds"),
        "daily_count": len(rows),
        "version": "1.5.17-free",
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
    """盤中指數：優先 TWSE MIS，Yahoo 僅作備援。"""
    out = {}

    # 官方 MIS：tse_t00.tw = 加權；otc_o00.tw = 櫃買。
    try:
        rr = requests.get(
            "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
            params={"ex_ch": "tse_t00.tw|otc_o00.tw", "json": "1", "delay": "0", "_": int(now_tw().timestamp() * 1000)},
            headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.4", "Referer": "https://mis.twse.com.tw/stock/index.jsp"},
            timeout=15,
        )
        rr.raise_for_status()
        for x in rr.json().get("msgArray") or []:
            ch = str(x.get("ch") or x.get("ex") or "")
            name = str(x.get("n") or "")
            key = None
            label = None
            if "tse_t00" in ch or "發行量加權" in name:
                key, label = "^TWII", "加權"
            elif "otc_o00" in ch or "櫃買" in name:
                key, label = "^TWOII", "櫃買"
            if not key:
                continue
            try:
                cur = float(str(x.get("z") or "").replace(",", ""))
                prev = float(str(x.get("y") or "").replace(",", ""))
            except Exception:
                continue
            if cur <= 0:
                continue
            change = (cur / prev - 1) * 100 if prev > 0 else None
            out[key] = {
                "label": label, "close": round(cur, 2),
                "change_pct": round(change, 2) if change is not None else None,
                "time": str(x.get("t") or ""), "source": "TWSE MIS",
            }
    except Exception as e:
        print("MIS intraday index", e)

    # Yahoo 只補 MIS 沒抓到的指數。
    missing = [s for s in ["^TWII", "^TWOII"] if s not in out]
    if missing:
        try:
            data = download_intraday(missing)
            for sym, label in [("^TWII", "加權"), ("^TWOII", "櫃買")]:
                if sym not in missing:
                    continue
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
                    chg = (cur / pc - 1) * 100 if pc else None
                else:
                    chg = None
                out[sym] = {
                    "label": label, "close": round(cur, 2),
                    "change_pct": round(chg, 2) if chg is not None else None,
                    "time": x.index[-1].strftime("%H:%M"), "source": "Yahoo fallback",
                }
        except Exception as e:
            print("intraday index fallback", e)
    return out



def intraday_stock_snapshot(universe_df, codes=None):
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
                        "bid1": fnum(str(x.get("b") or "").split("_")[0]),
                        "ask1": fnum(str(x.get("a") or "").split("_")[0]),
                        "open": fnum(x.get("o")),
                        "high": fnum(x.get("h")),
                        "low": fnum(x.get("l")),
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
        prev = meta.get("prev_close")
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
        if carried:
            diag["cached_z"] += 1
        else:
            diag["fresh_z"] += 1

    print("MIS intraday stock quotes", len(out), "/", len(recs), "fresh", diag["fresh_z"], "cached", diag["cached_z"])
    print("MIS_LAST_TRADE_DIAG", json.dumps(diag, ensure_ascii=False))
    return out

def _weighted_pct(rows, predicate, weight_key="current_turnover"):
    valid = [r for r in rows if (r.get(weight_key) or 0) > 0]
    total = sum(float(r.get(weight_key) or 0) for r in valid)
    if total <= 0:
        return None
    hit = sum(float(r.get(weight_key) or 0) for r in valid if predicate(r))
    return hit / total * 100


def _weighted_avg(rows, value_key, weight_key="current_turnover"):
    valid = [r for r in rows if r.get(value_key) is not None and (r.get(weight_key) or 0) > 0]
    total = sum(float(r.get(weight_key) or 0) for r in valid)
    if total <= 0:
        return None
    return sum(float(r[value_key]) * float(r.get(weight_key) or 0) for r in valid) / total


def build_sector_rotation(rows):
    """用成交金額占比變化 + 價格/VWAP/廣度判斷族群吸金熱度；不是法人淨流入。"""
    usable = [r for r in rows if str(r.get("sector_group") or "").strip()]
    if not usable:
        return []

    total_now = sum(float(r.get("current_turnover") or 0) for r in usable)
    total_recent = sum(float(r.get("recent_turnover") or 0) for r in usable)
    total_prev = sum(float(r.get("previous_turnover") or 0) for r in usable)
    groups = {}
    for r in usable:
        groups.setdefault(str(r.get("sector_group")).strip(), []).append(r)

    out = []
    for name, g in groups.items():
        if len(g) < 2:
            continue
        turnover = sum(float(r.get("current_turnover") or 0) for r in g)
        recent = sum(float(r.get("recent_turnover") or 0) for r in g)
        previous = sum(float(r.get("previous_turnover") or 0) for r in g)
        share = turnover / total_now * 100 if total_now > 0 else None
        recent_share = recent / total_recent * 100 if total_recent > 0 else None
        prev_share = previous / total_prev * 100 if total_prev > 0 else None
        share_change = (recent_share - prev_share) if recent_share is not None and prev_share is not None else None
        up_pct = sum(1 for r in g if float(r.get("day_change") or 0) > 0) / len(g) * 100
        above_vwap_pct = sum(1 for r in g if (r.get("close") or 0) >= (r.get("vwap") or 1e99)) / len(g) * 100
        avg_change = _weighted_avg(g, "day_change")
        avg_pace = _weighted_avg(g, "pace")

        # -10 ~ +10 熱度：占比正在增加、價格上漲、站VWAP、族群擴散、量速都會加分。
        heat = 0.0
        if share_change is not None:
            heat += max(-3.0, min(3.0, share_change * 2.5))
        if avg_change is not None:
            heat += max(-2.5, min(2.5, avg_change * 0.7))
        heat += max(-2.0, min(2.0, (above_vwap_pct - 50) / 20))
        heat += max(-1.5, min(1.5, (up_pct - 50) / 25))
        if avg_pace is not None:
            heat += max(-1.0, min(1.0, (avg_pace - 1.0) * 1.5))
        heat = round(max(-10, min(10, heat)), 1)

        if heat >= 5 and (share_change is None or share_change >= 0) and (avg_change or 0) > 0 and above_vwap_pct >= 60:
            state = "🔥 流入加速"
        elif heat >= 2.5 and (avg_change or 0) >= 0:
            state = "🟢 流入"
        elif heat <= -5 and (avg_change or 0) < 0 and above_vwap_pct <= 40:
            state = "🔻 資金流失"
        elif heat <= -2.5 or (share_change is not None and share_change <= -0.25):
            state = "🟠 降溫"
        else:
            state = "🟡 持平"

        leaders = sorted(
            g,
            key=lambda r: (float(r.get("day_change") or 0), float(r.get("current_turnover") or 0)),
            reverse=True,
        )[:3]
        out.append({
            "sector": name, "state": state, "heat": heat, "count": len(g),
            "change_pct": round(avg_change, 2) if avg_change is not None else None,
            "turnover_share_pct": round(share, 2) if share is not None else None,
            "recent_share_pct": round(recent_share, 2) if recent_share is not None else None,
            "previous_share_pct": round(prev_share, 2) if prev_share is not None else None,
            "share_change_pp": round(share_change, 2) if share_change is not None else None,
            "up_pct": round(up_pct, 1), "above_vwap_pct": round(above_vwap_pct, 1),
            "pace": round(avg_pace, 2) if avg_pace is not None else None,
            "window_min": next((r.get("rotation_window_min") for r in g if r.get("rotation_window_min")), None),
            "leaders": [{"code": r.get("code"), "name": r.get("name"), "change_pct": r.get("day_change")} for r in leaders],
        })

    out.sort(key=lambda x: (x.get("heat") or 0), reverse=True)
    return out


def _side_score(rows, live_info=None):
    """上市/上櫃即時結構，各 0~3 分。"""
    if not rows:
        return 1.5, {"change_pct": None, "above_vwap_pct": None, "breadth_pct": None}
    live_change = (live_info or {}).get("change_pct")
    weighted_change = _weighted_avg(rows, "day_change")
    ch = live_change if live_change is not None else weighted_change
    above = _weighted_pct(rows, lambda r: (r.get("close") or 0) >= (r.get("vwap") or 1e99))
    breadth = sum(1 for r in rows if float(r.get("day_change") or 0) > 0) / len(rows) * 100

    score = 0.0
    if ch is not None:
        score += 1.0 if ch > 0.25 else 0.7 if ch >= 0 else 0.3 if ch > -0.5 else 0
    else:
        score += 0.5
    if above is not None:
        score += 1.0 if above >= 60 else 0.7 if above >= 52 else 0.4 if above >= 45 else 0
    else:
        score += 0.5
    score += 1.0 if breadth >= 60 else 0.7 if breadth >= 52 else 0.4 if breadth >= 45 else 0
    return round(min(3, score), 1), {
        "change_pct": round(ch, 2) if ch is not None else None,
        "above_vwap_pct": round(above, 1) if above is not None else None,
        "breadth_pct": round(breadth, 1),
    }


def build_intraday_market(rows, market_live, rotation, close_market):
    """v1.3.4 盤中 15 分：只用今天即時資料，昨日外資僅背景、不計分。"""
    listed = [r for r in rows if r.get("market") == "上市"]
    otc_rows = [r for r in rows if r.get("market") == "上櫃"]
    taiex_score, taiex_meta = _side_score(listed, market_live.get("^TWII"))
    otc_score, otc_meta = _side_score(otc_rows, market_live.get("^TWOII"))

    breadth = sum(1 for r in rows if float(r.get("day_change") or 0) > 0) / len(rows) * 100 if rows else None
    if breadth is None:
        breadth_score = 1.5
    elif breadth >= 60:
        breadth_score = 3.0
    elif breadth >= 55:
        breadth_score = 2.5
    elif breadth >= 50:
        breadth_score = 1.8
    elif breadth >= 45:
        breadth_score = 0.8
    else:
        breadth_score = 0.0

    turnover_up = _weighted_pct(rows, lambda r: float(r.get("day_change") or 0) > 0)
    above_vwap_turnover = _weighted_pct(rows, lambda r: (r.get("close") or 0) >= (r.get("vwap") or 1e99))
    weighted_pace = _weighted_avg(rows, "pace")
    fund_score = 0.0
    if turnover_up is not None:
        fund_score += 2.0 if turnover_up >= 62 else 1.5 if turnover_up >= 55 else 1.0 if turnover_up >= 50 else 0.5 if turnover_up >= 45 else 0
    else:
        fund_score += 1.0
    if above_vwap_turnover is not None:
        fund_score += 1.0 if above_vwap_turnover >= 60 else 0.7 if above_vwap_turnover >= 52 else 0.3 if above_vwap_turnover >= 45 else 0
    else:
        fund_score += 0.5
    if weighted_pace is not None:
        if weighted_pace >= 1.25 and (turnover_up or 0) >= 55:
            fund_score += 1.0
        elif weighted_pace >= 1.0:
            fund_score += 0.5
    else:
        fund_score += 0.5
    fund_score = round(min(4, fund_score), 1)

    sector_valid = [x for x in rotation if (x.get("count") or 0) >= 2]
    positive = [x for x in sector_valid if (x.get("heat") or 0) >= 2.5]
    negative = [x for x in sector_valid if (x.get("heat") or 0) <= -2.5]
    if sector_valid:
        sector_positive_pct = len(positive) / len(sector_valid) * 100
        sector_score = 2.0 if sector_positive_pct >= 55 else 1.5 if sector_positive_pct >= 40 else 1.0 if sector_positive_pct >= 25 else 0.5 if sector_positive_pct >= 15 else 0.0
    else:
        sector_positive_pct = None
        sector_score = 1.0

    total = round(min(15, taiex_score + otc_score + breadth_score + fund_score + sector_score), 1)
    mode = "偏多" if total >= 11 else "中性" if total >= 7 else "防守"
    threshold = 70 if mode == "偏多" else 76 if mode == "中性" else 82

    return {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "market_score": total, "market_mode": mode, "radar_threshold": threshold,
        "breadth_up_pct": round(breadth, 1) if breadth is not None else None,
        "turnover_up_pct": round(turnover_up, 1) if turnover_up is not None else None,
        "above_vwap_turnover_pct": round(above_vwap_turnover, 1) if above_vwap_turnover is not None else None,
        "weighted_pace": round(weighted_pace, 2) if weighted_pace is not None else None,
        "sector_positive_pct": round(sector_positive_pct, 1) if sector_positive_pct is not None else None,
        "sector_positive_count": len(positive), "sector_negative_count": len(negative),
        "score_max": 15, "intraday_only": True,
        "foreign_used_in_score": False,
        "background_foreign_date": close_market.get("foreign_date"),
        "background_foreign_twse_billion": close_market.get("foreign_twse_billion"),
        "background_foreign_tpex_billion": close_market.get("foreign_tpex_billion"),
        "components": {
            "taiex": {"score": taiex_score, "max": 3, **taiex_meta},
            "otc": {"score": otc_score, "max": 3, **otc_meta},
            "breadth": {"score": round(breadth_score, 1), "max": 3},
            "funds": {"score": fund_score, "max": 4},
            "sector": {"score": round(sector_score, 1), "max": 2},
        },
        "explain": {
            "taiex": "加權即時結構3分：指數方向＋上市站VWAP成交金額比＋上市上漲家數",
            "otc": "櫃買即時結構3分：指數方向＋上櫃站VWAP成交金額比＋上櫃上漲家數",
            "breadth": "今日即時上漲家數3分",
            "funds": "盤中資金動能4分：上漲股成交金額占比＋站VWAP成交金額占比＋同時間量速",
            "sector": "族群擴散2分：吸金熱度為正的族群比例",
            "foreign": "昨日/最近盤後外資只顯示背景，不計入盤中15分",
        },
    }


def build_sector_institution_flow(rows, price_history=None):
    """盤後族群法人資金流：官方淨買賣股數 + 同日收盤價估算金額。

    金額 = (外資淨買賣股數 + 投信淨買賣股數) × 該交易日收盤價。
    這是逐日、逐股估算後再彙總，不是官方逐股實際成交金額；張數仍保留。
    族群優先採自訂 sector_group，未分類者退回官方 industry_name。
    此資料只做盤後觀察，不額外灌入個股100分。
    """
    history = load_json("chip_history.json", {})
    price_history = price_history or {}
    if not isinstance(history, dict) or not rows:
        return []

    groups = {}
    for r in rows:
        sector = str(r.get("sector_group") or "").strip()
        industry = str(r.get("industry_name") or "").strip()
        key = sector if sector else (industry if industry and industry != "未分類" else "")
        if key:
            groups.setdefault(key, []).append(r)

    out = []
    for key, members in groups.items():
        daily = {}
        for r in members:
            code = str(r.get("code") or "")
            prices = price_history.get(code) or {}
            for h in history.get(code) or []:
                ds = str(h.get("date") or "")
                if not ds:
                    continue
                fv = h.get("foreign_net")
                tv = h.get("trust_net")
                if fv is None and tv is None:
                    continue
                try:
                    net = float(fv or 0) + float(tv or 0)
                except Exception:
                    continue
                z = daily.setdefault(ds, {"shares": 0.0, "amount": 0.0, "records": 0, "priced": 0})
                z["shares"] += net
                z["records"] += 1
                try:
                    px = float(prices.get(ds))
                except Exception:
                    px = None
                if px is not None and np.isfinite(px) and px > 0:
                    z["amount"] += net * px
                    z["priced"] += 1

        ordered = sorted(daily.items(), key=lambda x: x[0], reverse=True)
        vals = [z["shares"] / 1000.0 for _, z in ordered]  # 股 -> 張
        amount_vals = []
        for _, z in ordered:
            cov = (z["priced"] / z["records"]) if z["records"] else 0.0
            # 避免少數缺價個股讓族群金額看起來過度精確；單日覆蓋至少80%才採用。
            amount_vals.append((z["amount"] / 100_000_000.0) if cov >= 0.80 else None)

        latest = vals[0] if vals else None
        prev = vals[1] if len(vals) >= 2 else None
        net5 = sum(vals[:5]) if len(vals) >= 5 else None
        net20 = sum(vals[:20]) if len(vals) >= 20 else None

        latest_amount = amount_vals[0] if amount_vals else None
        prev_amount = amount_vals[1] if len(amount_vals) >= 2 else None
        net5_amount = sum(amount_vals[:5]) if len(amount_vals) >= 5 and all(v is not None for v in amount_vals[:5]) else None
        net20_amount = sum(amount_vals[:20]) if len(amount_vals) >= 20 and all(v is not None for v in amount_vals[:20]) else None

        recent_rows = [z for _, z in ordered[:20]]
        rec_n = sum(int(z.get("records") or 0) for z in recent_rows)
        priced_n = sum(int(z.get("priced") or 0) for z in recent_rows)
        amount_coverage = (priced_n / rec_n * 100.0) if rec_n else 0.0
        amount_days = sum(v is not None for v in amount_vals)

        # 金額資料完整時，用金額判定流入/流出與加速；否則退回原本張數方向。
        flow_vals = amount_vals if latest_amount is not None else vals
        flow_latest = flow_vals[0] if flow_vals else None
        flow_prev = flow_vals[1] if len(flow_vals) >= 2 else None
        streak = 0
        streak_dir = None
        if flow_latest is not None and flow_latest != 0:
            streak_dir = 1 if flow_latest > 0 else -1
            for v in flow_vals:
                if v is None or v == 0 or (1 if v > 0 else -1) != streak_dir:
                    break
                streak += 1

        accelerating = bool(
            flow_latest is not None and flow_prev is not None and flow_latest * flow_prev > 0
            and abs(flow_latest) >= abs(flow_prev) * 1.15
        )
        if streak_dir == 1:
            flow_text = f"連續流入 {streak} 天" + (" ↑ 流入加速" if accelerating else "")
        elif streak_dir == -1:
            flow_text = f"連續流出 {streak} 天" + (" ↓ 流出加速" if accelerating else "")
        else:
            flow_text = "資金方向中性"

        action_latest = latest_amount if latest_amount is not None else latest
        action_5 = net5_amount if net5_amount is not None else net5
        if action_latest is None:
            action = "資料累積中"
        elif action_latest > 0 and (action_5 is None or action_5 > 0):
            action = "持續加碼"
        elif action_latest > 0:
            action = "轉為加碼"
        elif action_latest < 0 and (action_5 is None or action_5 < 0):
            action = "持續減碼"
        elif action_latest < 0:
            action = "轉為減碼"
        else:
            action = "中性"

        weighted = [
            (float(r.get("ret5") or 0), max(float(r.get("avg_turnover20") or 0), 1.0))
            for r in members
        ]
        sw = sum(w for _, w in weighted)
        ret5 = sum(v * w for v, w in weighted) / sw if sw else None

        out.append({
            "sector": key,
            "today_amount_100m": None if latest_amount is None else round(latest_amount, 4),
            "net5_amount_100m": None if net5_amount is None else round(net5_amount, 4),
            "net20_amount_100m": None if net20_amount is None else round(net20_amount, 4),
            "amount_history_days": amount_days,
            "amount_coverage_pct": round(amount_coverage, 1),
            "amount_method": "外資＋投信淨買賣股數×各交易日收盤價（估算）",
            "today_lots": None if latest is None else round(latest, 1),
            "net5_lots": None if net5 is None else round(net5, 1),
            "net20_lots": None if net20 is None else round(net20, 1),
            "history_days": len(vals),
            "latest_date": ordered[0][0] if ordered else None,
            "flow_streak": streak,
            "flow_direction": "in" if streak_dir == 1 else "out" if streak_dir == -1 else "flat",
            "accelerating": accelerating,
            "flow_text": flow_text,
            "action": action,
            "ret5_pct": None if ret5 is None else round(ret5, 2),
            "member_count": len(members),
        })

    # v1.5.14：資料層也統一以「今日估算法人淨額」力度排序。
    # 5日/20日只作趨勢欄位，不影響今日榜名次。
    out.sort(
        key=lambda x: (
            abs(float(x.get("today_amount_100m") or 0)),
            abs(float(x.get("today_lots") or 0)),
        ),
        reverse=True,
    )
    return out


def build_change_radar(rows, rotation, previous_obj):
    """Compare this intraday snapshot with the prior deployed snapshot.

    This is an event/change layer only. It never changes the 100-point score or
    Stage Engine result.  A comparison is accepted only for the same trade date
    and a reasonably recent prior run, so overnight/stale gaps are not mislabeled
    as "just turned" events.
    """
    def num(v, default=0.0):
        try:
            return float(v) if v is not None else float(default)
        except Exception:
            return float(default)

    def trade_date_of(rs):
        vals = []
        for z in rs or []:
            d = str(z.get("quote_date") or z.get("date") or "")[:10]
            if len(d) == 10:
                vals.append(d)
        return max(vals) if vals else None

    now = now_tw()
    previous_obj = previous_obj if isinstance(previous_obj, dict) else {}
    prev_rows = previous_obj.get("rows") or []
    prev_time_raw = previous_obj.get("updated_at")
    comparison_min = None
    try:
        pt = datetime.fromisoformat(str(prev_time_raw))
        if pt.tzinfo is None:
            pt = pt.replace(tzinfo=TW)
        comparison_min = (now - pt.astimezone(TW)).total_seconds() / 60.0
    except Exception:
        comparison_min = None

    cur_date = trade_date_of(rows)
    prev_date = trade_date_of(prev_rows)
    same_day = bool(cur_date and prev_date and cur_date == prev_date)
    fresh_gap = bool(comparison_min is not None and 0.5 <= comparison_min <= 16.0)

    for r in rows:
        r["change_events"] = []
        r["change_score_delta"] = None
        r["previous_intraday_score"] = None
        r["previous_stage"] = None

    base = {
        "version": "1.0",
        "ready": False,
        "trade_date": cur_date,
        "previous_trade_date": prev_date,
        "previous_updated_at": prev_time_raw,
        "comparison_minutes": round(comparison_min, 1) if comparison_min is not None else None,
        "events": [],
        "sector_events": [],
        "counts": {"turn_strong": 0, "turn_weak": 0, "breakout": 0, "vwap_reclaim": 0, "sector_accel": 0},
    }
    if not prev_rows:
        base["reason"] = "等待下一個5分鐘快照建立比較基準"
        return base
    if not same_day:
        base["reason"] = "新交易日第一輪，先建立今日比較基準"
        return base
    if not fresh_gap:
        base["reason"] = "上一輪間隔過久，為避免誤判『剛發生』事件，本輪只建立新基準"
        return base

    prev_map = {str(x.get("code")): x for x in prev_rows if x.get("code")}
    strong_stages = {"蓄勢待發", "剛啟動", "回踩承接", "趨勢持有"}
    weak_stages = {"轉弱警戒", "結構失效"}
    events = []

    def add_event(r, typ, label, reason, priority):
        e = {
            "type": typ, "label": label, "reason": reason,
            "priority": int(priority), "code": str(r.get("code") or ""),
            "name": str(r.get("name") or ""),
            "score": round(num(r.get("intraday_score", r.get("score"))), 1),
            "score_delta": r.get("change_score_delta"),
            "stage": str(r.get("category") or "觀察"),
            "previous_stage": r.get("previous_stage"),
        }
        r.setdefault("change_events", []).append(e)
        events.append(e)
        base["counts"][typ] += 1

    for r in rows:
        code = str(r.get("code") or "")
        p = prev_map.get(code)
        if not p:
            continue
        cur_score = num(r.get("intraday_score", r.get("score")))
        prev_score = num(p.get("intraday_score", p.get("score")))
        delta = cur_score - prev_score
        cur_stage = str(r.get("category") or "觀察")
        prev_stage = str(p.get("category") or "觀察")
        r["change_score_delta"] = round(delta, 1)
        r["previous_intraday_score"] = round(prev_score, 1)
        r["previous_stage"] = prev_stage

        cur_close, cur_vwap = num(r.get("close")), num(r.get("vwap"))
        prev_close, prev_vwap = num(p.get("close")), num(p.get("vwap"))
        cur_above = bool(cur_vwap > 0 and cur_close >= cur_vwap)
        prev_above = bool(prev_vwap > 0 and prev_close >= prev_vwap)
        cur_rel = num((r.get("intraday_components") or {}).get("relative_strength_pct"))
        prev_rel = num((p.get("intraday_components") or {}).get("relative_strength_pct"))
        rel_delta = cur_rel - prev_rel
        cur_break3, prev_break3 = bool(r.get("break3")), bool(p.get("break3"))
        cur_break12, prev_break12 = bool(r.get("break12")), bool(p.get("break12"))

        # 新突破：必須是本輪才由 false -> true，且站在VWAP上方、動能至少60。
        if ((cur_break3 and not prev_break3) or (cur_break12 and not prev_break12)) and cur_above and cur_score >= 60:
            which = "3K突破" if cur_break3 and not prev_break3 else "60分區間突破"
            add_event(r, "breakout", "🚀 剛突破", f"{which}剛成立｜動能 {prev_score:.0f}→{cur_score:.0f}", 100)

        # 站回VWAP：要求上一輪在下方、本輪站回，且15分動能不為負，降低來回穿越雜訊。
        if prev_vwap > 0 and cur_vwap > 0 and (not prev_above) and cur_above and num(r.get("ret15")) >= 0:
            add_event(r, "vwap_reclaim", "♻️ 剛站回VWAP", f"由VWAP下方重新站回｜距VWAP {num(r.get('vwap_dist')):+.1f}%", 88)

        stage_turn_strong = prev_stage in ({"觀察", "轉弱警戒"} | weak_stages) and cur_stage in strong_stages
        score_turn_strong = delta >= 8 and cur_score >= 60 and ((not prev_above and cur_above) or rel_delta >= 0.5 or (cur_break3 and not prev_break3))
        if stage_turn_strong or score_turn_strong:
            bits = [f"動能 {prev_score:.0f}→{cur_score:.0f}"]
            if prev_stage != cur_stage:
                bits.append(f"{prev_stage}→{cur_stage}")
            if rel_delta >= 0.5:
                bits.append(f"相對市場改善 {rel_delta:+.1f}pp")
            add_event(r, "turn_strong", "⬆️ 剛轉強", "｜".join(bits), 92)

        stage_turn_weak = prev_stage not in weak_stages and cur_stage in weak_stages
        score_turn_weak = delta <= -8 and cur_score <= 60 and ((prev_above and not cur_above) or rel_delta <= -0.5)
        if stage_turn_weak or score_turn_weak:
            bits = [f"動能 {prev_score:.0f}→{cur_score:.0f}"]
            if prev_stage != cur_stage:
                bits.append(f"{prev_stage}→{cur_stage}")
            if rel_delta <= -0.5:
                bits.append(f"相對市場惡化 {rel_delta:+.1f}pp")
            add_event(r, "turn_weak", "⬇️ 剛轉弱", "｜".join(bits), 95)

    # 族群加速：熱度跨過+2.5，或已在正熱區且單輪再增加至少1.5。
    prev_rot = {str(x.get("sector") or ""): x for x in (previous_obj.get("sector_rotation") or [])}
    sector_events = []
    for x in rotation or []:
        sector = str(x.get("sector") or "")
        p = prev_rot.get(sector)
        if not sector or not p:
            continue
        h = num(x.get("heat")); ph = num(p.get("heat")); dh = h - ph
        crossed = ph < 2.5 <= h
        accelerated = h >= 2.5 and dh >= 1.5
        if crossed or accelerated:
            sector_events.append({
                "type": "sector_accel", "label": "🔥 族群加速", "sector": sector,
                "heat": round(h, 1), "heat_delta": round(dh, 1),
                "reason": f"熱度 {ph:+.1f}→{h:+.1f}（{dh:+.1f}）",
                "priority": 85,
            })
    sector_events.sort(key=lambda z: (z.get("heat_delta", 0), z.get("heat", 0)), reverse=True)
    base["counts"]["sector_accel"] = len(sector_events)

    events.sort(key=lambda z: (z.get("priority", 0), abs(z.get("score_delta") or 0)), reverse=True)
    base.update({
        "ready": True,
        "reason": "只顯示相較上一輪新發生的變化",
        "events": events[:80],
        "sector_events": sector_events[:20],
    })
    return base



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

def _attach_multitimeframe_context(rows, close_map, hourly_obj):
    """Attach 5m + prior completed 60m + daily context without changing any score weight."""
    if not rows:
        return rows
    hourly_rows = (hourly_obj or {}).get("all_rows") or (hourly_obj or {}).get("rows") or []
    hmap = {str(x.get("code")): x for x in hourly_rows if isinstance(x, dict) and x.get("code")}

    def fv(obj, key, default=0.0):
        try:
            v = obj.get(key)
            return float(v) if v is not None else float(default)
        except Exception:
            return float(default)

    for r in rows:
        code = str(r.get("code") or "")
        h = hmap.get(code) or {}
        d = (close_map or {}).get(code) or {}

        close = fv(r, "close")
        vwap = fv(r, "vwap")
        ret15 = fv(r, "ret15")
        five_bull = bool(vwap > 0 and close >= vwap and (r.get("trend5") or r.get("break3") or r.get("break12")))
        five_bear = bool(vwap > 0 and close < vwap and not r.get("trend5") and ret15 < 0)
        five_state = "BULLISH" if five_bull else "BEARISH" if five_bear else "NEUTRAL"

        h_available = bool(h and h.get("data_status") == "OK")
        hcat = str(h.get("category60") or "")
        dir20 = str(h.get("dir20") or "")
        dir60 = str(h.get("dir60") or "")
        h_ma20 = fv(h, "ma20_60")
        h_ma60 = fv(h, "ma60_60")
        h_price = fv(h, "price")
        gap20_60 = fv(h, "gap20_60_pct", 999)
        if not h_available:
            h_state = "UNAVAILABLE"
        elif gap20_60 < 0 and dir20 == "DOWN":
            h_state = "DEATH_CROSS"
        elif hcat in {"PRE_CROSS", "EARLY", "STABLE_CONT", "ACCEL_CONT"}:
            h_state = hcat
        elif dir20 == "DOWN" and dir60 == "DOWN" and (not h_ma20 or h_price < h_ma20):
            h_state = "BEARISH"
        elif dir20 == "UP" and dir60 == "UP" and h_ma20 > h_ma60:
            h_state = "BULLISH"
        elif dir20 == "UP" and dir60 in {"UP", "FLAT"}:
            h_state = "IMPROVING"
        else:
            h_state = "NEUTRAL"
        h_supportive = h_state in {"PRE_CROSS", "EARLY", "STABLE_CONT", "ACCEL_CONT", "BULLISH", "IMPROVING"}
        h_bearish = h_state in {"BEARISH", "DEATH_CROSS"}

        dclose = fv(d, "close")
        dma20 = fv(d, "ma20")
        dma5 = fv(d, "ma5")
        dma10 = fv(d, "ma10")
        dcat = str(d.get("category") or "")
        daily_weak = bool(
            dcat in {"轉弱警戒", "結構失效"}
            or (dma20 > 0 and dclose < dma20 and dma5 > 0 and dma10 > 0 and dma5 < dma10)
        )
        daily_bull = bool(
            not daily_weak and (
                d.get("trend") or d.get("break20")
                or (dma20 > 0 and dclose >= dma20 and dma5 > 0 and dma10 > 0 and dma5 >= dma10)
            )
        )
        daily_state = "WEAK" if daily_weak else "BULLISH" if daily_bull else "NEUTRAL"

        if five_bull and h_supportive and not daily_weak:
            state = "ALIGNED"
        elif h_state in {"PRE_CROSS", "IMPROVING"} and not daily_weak:
            state = "SETUP"
        elif five_bull and h_bearish:
            state = "CONFLICT"
        elif h_bearish and daily_weak:
            state = "WEAK"
        elif h_supportive and not daily_weak:
            state = "SUPPORTIVE"
        else:
            state = "MIXED"

        labels = {
            "ALIGNED": "三框共振",
            "SETUP": "60K蓄勢／等5分觸發",
            "SUPPORTIVE": "60K＋日K支持",
            "CONFLICT": "5分轉強但60K未跟上",
            "WEAK": "60K＋日K偏弱",
            "MIXED": "框架混合／等確認",
        }
        hlabels = {
            "PRE_CROSS": "20T/60T金叉前夕",
            "EARLY": "20T/60T初升金叉",
            "STABLE_CONT": "20T/60T穩定續航",
            "ACCEL_CONT": "20T/60T加速續航",
            "BULLISH": "20T/60T多頭",
            "IMPROVING": "20T轉上／60T改善",
            "BEARISH": "20T/60T偏弱",
            "DEATH_CROSS": "20T跌破60T／死亡交叉風險",
            "NEUTRAL": "20T/60T中性",
            "UNAVAILABLE": "60K資料待補",
        }
        dlabels = {"BULLISH": "日K偏多", "WEAK": "日K偏弱", "NEUTRAL": "日K中性"}
        flabels = {"BULLISH": "5分轉強", "BEARISH": "5分轉弱", "NEUTRAL": "5分等待"}

        r["multi_timeframe"] = {
            "version": "1.0",
            "state": state,
            "label": labels[state],
            "5m": {
                "state": five_state,
                "label": flabels[five_state],
                "above_vwap": bool(vwap > 0 and close >= vwap),
                "trend5": bool(r.get("trend5")),
                "break3": bool(r.get("break3")),
                "break12": bool(r.get("break12")),
            },
            "60m": {
                "available": h_available,
                "state": h_state,
                "label": hlabels[h_state],
                "category": hcat or None,
                "ma20": h.get("ma20_60"),
                "ma60": h.get("ma60_60"),
                "dir20": h.get("dir20"),
                "dir60": h.get("dir60"),
                "gap20_60_pct": h.get("gap20_60_pct"),
                "cross_age": h.get("cross_age"),
                "price_vs20_pct": h.get("price_vs20_60_pct"),
                "supportive": h_supportive,
                "bearish": h_bearish,
                "source_trade_date": (hourly_obj or {}).get("trade_date"),
            },
            "daily": {
                "state": daily_state,
                "label": dlabels[daily_state],
                "stage": dcat or None,
                "ma5": d.get("ma5"),
                "ma10": d.get("ma10"),
                "ma20": d.get("ma20"),
                "dist20": d.get("dist20"),
                "trend": bool(d.get("trend")),
                "break20": bool(d.get("break20")),
                "source_date": d.get("date"),
            },
            "score_weight": 0,
            "note": "多時間框架只作Stage/進場決策確認，不新增100分權重",
        }
    return rows

def build_intraday():
    # v1.5.21：sync_live_data 已先抓回上一輪正式 intraday.json。
    # 先留一份到 .cache，讓 build_data 與後續 MIS bridge 都能和同一個基準比較。
    previous_intraday = load_json("intraday.json", {})
    try:
        (CACHE / "intraday_previous.json").write_text(
            json.dumps(previous_intraday, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
    except Exception:
        pass
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
                    "industry_name": str(m.get("industry_name", industry_name_for(m.get("industry")))),
                    "sector_group": str(m.get("sector_group") or sector_group_for(code, m.get("name"), m.get("industry")) or ""),
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
                    "avg_turnover20": prev.get("avg_turnover20"),
                    "avg_turnover20_mn": prev.get("avg_turnover20_mn"),
                    "liquidity_level": prev.get("liquidity_level", "未知"),
                    "liquidity_adjust": prev.get("liquidity_adjust", 0),
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
            previous["note"] = "本輪免費盤中資料源暫時沒有有效5分K，已保留上一輪資料，不再顯示空白。"
            dump("intraday.json", previous)
            status = load_json("status.json", {})
            status.update({
                "updated_at": now_tw().isoformat(timespec="seconds"),
                "intraday_attempted_at": now_tw().isoformat(timespec="seconds"),
                "intraday_count": len(previous.get("rows", [])),
                "version": "1.5.29-free",
            })
            dump("status.json", status)
            print("intraday source empty; kept previous", len(previous.get("rows", [])))
            return

    # Official quote overlay: all rows get the freshest MIS last price available.
    # Structure fields (technical_score/breakouts/VWAP/support) still come from the
    # 5-minute engine; quote time is stored separately so freshness is transparent.
    quote_map = intraday_stock_snapshot(u, [r.get("code") for r in rows])
    structure_times = [str(r.get("time") or "")[:5] for r in rows if r.get("time")]
    for r in rows:
        r["structure_time"] = r.get("time")
        r["structure_close"] = r.get("close")
        q = quote_map.get(str(r.get("code")))
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

    quote_times = [str(q.get("time") or "")[:5] for q in quote_map.values() if q.get("time")]
    quote_latest = max(quote_times) if quote_times else None
    structure_latest = max(structure_times) if structure_times else None

    hourly_obj = load_json("hourly.json", {})
    rows = _attach_multitimeframe_context(rows, close_map, hourly_obj)

    market_live = intraday_index_snapshot()
    rows = _attach_relative_multitimeframe(rows, close_map, market, market_live)
    rows = _refresh_dynamic_thresholds(rows, close_map)
    sector_rotation = build_sector_rotation(rows)
    intraday_market = build_intraday_market(rows, market_live, sector_rotation, market)
    rows = add_component_scores(rows, intraday_market, preliminary_intraday=True)
    change_radar = build_change_radar(rows, sector_rotation, previous_intraday)

    dump("intraday.json", {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "change_radar": change_radar,
        "market": intraday_market,
        "market_intraday": market_live,
        "sector_rotation": sector_rotation,
        "quote_layer": {
            "source": "TWSE MIS", "coverage": len(quote_map), "row_count": len(rows),
            "latest_time": quote_latest, "structure_latest_time": structure_latest,
            "note": "現價/當日漲跌採官方MIS；VWAP/突破/量速/支撐壓力仍採5分K結構",
        },
        "multi_timeframe_version": "1.1",
        "relative_multiframe_version": "1.0",
        "dynamic_threshold_version": "1.0",
        "score_formula": {"mode": "intraday_execution", "price_structure": 30, "flow_volume": 25, "relative_strength": 15, "sector": 20, "liquidity_risk": 10, "amplitude_efficiency": "inside_flow_and_liquidity_risk_no_new_weight", "multi_timeframe": "decision_context_no_new_weight", "relative_multiframe": "decision_context_no_new_weight", "chip": "background_only", "market_separate": 15},
        "rows": rows,
    })

    status = load_json("status.json", {})
    status.update({
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "intraday_updated_at": now_tw().isoformat(timespec="seconds"),
        "intraday_count": len(rows),
        "version": "1.5.29-free",
        "multi_timeframe_version": "1.1",
        "relative_multiframe_version": "1.0",
        "dynamic_threshold_version": "1.0",
        "version": "1.5.29-free",
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
