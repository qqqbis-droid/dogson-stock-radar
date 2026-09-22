#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply v1.3.5: integer chip scores, fair sector fallback, stronger S/R zones."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_data.py"
HTML = ROOT / "docs" / "index.html"


def must_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"marker not found: {label}")
    return text.replace(old, new)


def regex_replace(text: str, pattern: str, replacement: str, label: str) -> str:
    new, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError(f"regex replace failed {label}: {n}")
    return new


NEW_ZONE_AND_DAILY = r'''def zone(current, candidates, atr, side, intraday=False):
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
    }'''


NEW_SECTOR_SCORE = r'''def sector_score(n, ratio=None, fallback=False):
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
    return 0'''


build = BUILD.read_text(encoding="utf-8")
build = build.replace("Free Edition v1.3.4", "Free Edition v1.3.5")

# Chip score becomes a true integer, not merely an integer-looking UI value.
old_chip_return = '    return round(min(25, score), 1), round(coverage/25*100, 0)'
new_chip_return = '    return int(math.floor(min(25, score) + 0.5)), round(coverage/25*100, 0)'
build = must_replace(build, old_chip_return, new_chip_return, "chip score integer")

build = regex_replace(
    build,
    r'def sector_score\(n\):.*?\n\ndef liquidity_profile',
    NEW_SECTOR_SCORE + '\n\ndef liquidity_profile',
    "sector score function",
)

old_hot = '''    # 族群共振改用嚴格次產業/題材群組，不再拿整個「半導體業」當同族群。
    hot = {}
    for r in rows:
        key = str(r.get("sector_group") or "").strip()
        if key and r.get("technical_score", 0) >= 30 and not r.get("overheat_reasons"):
            hot[key] = hot.get(key, 0) + 1
'''
new_hot = '''    # 次產業/題材優先；沒有窄群組時，用官方產業廣度作為「代理分」，且上限 6 分。
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
'''
build = must_replace(build, old_hot, new_hot, "sector hot maps")

old_apply = '''        key = str(r.get("sector_group") or "").strip()
        n = int(hot.get(key, 0)) if key else 0
        sec = sector_score(n)
        r["industry_hot_count"] = n
        r["sector_hot_count"] = n
        r["sector_score"] = sec
'''
new_apply = '''        key = str(r.get("sector_group") or "").strip()
        industry = str(r.get("industry_name") or "").strip()
        if key:
            n = int(hot.get(key, 0))
            sec = sector_score(n)
            source = "次產業"
            label = key
            ratio = None
        else:
            n = int(industry_hot.get(industry, 0)) if industry and industry != "未分類" else 0
            total_n = int(industry_total.get(industry, 0)) if industry and industry != "未分類" else 0
            ratio = (n / total_n) if total_n else 0
            sec = sector_score(n, ratio, True)
            source = "官方產業代理" if total_n else "待分類"
            label = industry if total_n else "待分類"
        r["industry_hot_count"] = int(industry_hot.get(industry, 0)) if industry else 0
        r["sector_hot_count"] = n
        r["sector_score"] = sec
        r["sector_score_source"] = source
        r["sector_score_label"] = label
        r["sector_hot_ratio"] = round(ratio * 100, 1) if ratio is not None else None
'''
build = must_replace(build, old_apply, new_apply, "sector apply")

build = regex_replace(
    build,
    r'def zone\(current, candidates, atr, side, intraday=False\):.*?\n\ndef close_technical',
    NEW_ZONE_AND_DAILY + '\n\ndef close_technical',
    "support resistance engine",
)

BUILD.write_text(build, encoding="utf-8")

html = HTML.read_text(encoding="utf-8")
html = html.replace("Free Edition v1.3.4", "Free Edition v1.3.5")
html = html.replace("盤中純即時＋族群資金輪動", "整數籌碼＋族群代理＋強化支撐壓力")
html = html.replace('num(r.chip_score,1)+"/25"', 'num(r.chip_score,0)+"/25"')

old_metric = 'r.sector_group?((r.sector_hot_count||0)+"檔 · "+r.sector_group):"未分類"'
new_metric = '(r.sector_score_label?((r.sector_hot_count||0)+"檔 · "+r.sector_score_label+(r.sector_score_source==="官方產業代理"?"（產業代理）":"")):"待分類")'
html = html.replace(old_metric, new_metric)

old_sr = '<div class="sr ${t}"><div class="srtitle">${t==="support"?"🟢 支撐區":"🔴 壓力區"} · ${signed(x.distance_pct,1)}</div><div class="srprice">${num(x.low,2)}～${num(x.high,2)}</div><div class="srbasis">${x.basis||""}</div></div>`;'
new_sr = '<div class="sr ${t}"><div class="srtitle">${t==="support"?"🟢 主要支撐區":"🔴 主要壓力區"} · ${signed(x.distance_pct,1)}</div><div class="srprice">${num(x.low,2)}～${num(x.high,2)}</div><div class="srbasis">強度 ${x.strength||1}/5｜${x.basis||""}</div></div>`;'
html = must_replace(html, old_sr, new_sr, "SR UI")

old_help_sector = '<b>族群 10：</b>改用較窄的次產業/題材群組；沒有明確分類就不給族群分，避免把整個半導體業混成同一群。<br>'
new_help_sector = '<b>族群 10：</b>優先看較窄的次產業/題材共振：4檔以上=10、3檔=8、2檔=5、1檔=2。沒有窄群組時改用官方產業廣度作代理，最高6分，並明確標示「產業代理」，不再因為資料尚未分類就直接判0分。<br>'
html = must_replace(html, old_help_sector, new_help_sector, "sector help")

old_help_market = '<b>大盤 15：</b>盤中改成純即時：加權3＋櫃買3＋今日上漲家數3＋盤中資金動能4＋族群擴散2；昨日外資只顯示背景、不計盤中分。盤後仍用完成交易日的加權／櫃買／廣度／官方外資。<br>'
new_help_market = '<b>大盤 15：</b>盤中＝加權3＋櫃買3＋今日上漲家數3＋盤中資金動能4＋族群擴散2，昨日外資只顯示背景、不計分。盤後＝加權5（多頭排列5／僅站20MA 2.5／跌破20MA 0）＋櫃買4（4／2／0）＋上漲家數3（≥60%=3、55%=2.5、50%=1.5、45%=0.5）＋官方外資3（當日方向最多2＋近5日方向最多1）。<br>'
html = must_replace(html, old_help_market, new_help_market, "market help")

old_help_sr = '<b>支撐／壓力：</b>是區間，不是保證反彈或突破的精準價。'
new_help_sr = '<b>支撐／壓力：</b>改用多證據加權：前波轉折、5/10/20/60/120MA、前日與20/60日高低、突破回測平台、60日成交密集區、大量成交成本、跳空缺口，再用ATR聚類成區間；同時顯示1～5級強度。仍是決策區，不是保證反彈或突破的單一精準價。'
html = must_replace(html, old_help_sr, new_help_sr, "SR help")

HTML.write_text(html, encoding="utf-8")
print("v1.3.5 patch applied")
