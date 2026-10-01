#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Support / Resistance Structure 2.0 post-processor.

This enriches the already-built radar rows with ranked S1/S2/R1/R2 zones while
preserving the legacy `support` and `resistance` fields used by existing score
logic.  It therefore adds decision context without silently changing ranking
weights.

Inputs are only already-known structure values from the same radar build:
- legacy weighted support/resistance (which already includes pivots, volume by
  price, high-volume cost zones, gaps and longer moving averages),
- 5/10/20-day moving averages,
- VWAP / current range,
- completed 60m 20T/60T moving-average context when available.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

VERSION = "2.0"


def num(v):
    try:
        z = float(v)
        return z if math.isfinite(z) else None
    except Exception:
        return None


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write(path: Path, obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def rows_of(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("rows", "items", "data", "stocks", "results"):
            if isinstance(obj.get(key), list):
                return obj[key]
    return []


def evidence_of(zone):
    if not isinstance(zone, dict):
        return []
    out = []
    raw = zone.get("evidence") or zone.get("labels")
    if isinstance(raw, list):
        out.extend(str(x).strip() for x in raw if str(x).strip())
    basis = str(zone.get("basis") or zone.get("reason") or "").strip()
    if basis:
        out.extend(x.strip() for x in basis.replace("+", "＋").split("＋") if x.strip())
    return list(dict.fromkeys(out))


def point_candidate(price, label, weight):
    p = num(price)
    if p is None or p <= 0:
        return None
    return {"center": p, "low": p, "high": p, "label": label, "weight": float(weight)}


def zone_candidate(zone, default_label, base_weight=5.0):
    if not isinstance(zone, dict):
        return None
    center = num(zone.get("center"))
    low = num(zone.get("low"))
    high = num(zone.get("high"))
    if center is None and low is not None and high is not None:
        center = (low + high) / 2
    if center is None:
        return None
    low = center if low is None else low
    high = center if high is None else high
    low, high = sorted((low, high))
    strength = num(zone.get("strength")) or 0
    return {
        "center": center,
        "low": low,
        "high": high,
        "label": default_label,
        "weight": float(base_weight + min(5.0, strength) * 0.55),
        "evidence": evidence_of(zone),
    }


def add_candidate(pool, candidate):
    if not candidate:
        return
    if candidate.get("center") is None:
        return
    pool.append(candidate)


def cluster_levels(current, candidates, side, context):
    """Cluster known structural references and return nearest two meaningful levels."""
    if current is None or current <= 0:
        return []
    support = side == "SUPPORT"
    valid = []
    for c in candidates:
        p = num(c.get("center"))
        if p is None or p <= 0:
            continue
        if support and p > current * 1.006:
            continue
        if not support and p < current * 0.994:
            continue
        # The second level may be meaningfully farther away, but do not publish
        # remote historical levels as if they were actionable structure.
        max_dist = 0.26 if context == "close" else 0.14
        if abs(p / current - 1) > max_dist:
            continue
        valid.append(c)
    if not valid:
        return []

    valid.sort(key=lambda x: float(x["center"]))
    tolerance = 0.012 if context == "close" else 0.008
    clusters = []
    for c in valid:
        p = float(c["center"])
        best = None
        for cl in clusters:
            if abs(p / cl["center"] - 1) <= tolerance:
                best = cl
                break
        if best is None:
            best = {"items": [], "center": p}
            clusters.append(best)
        best["items"].append(c)
        sw = sum(max(0.2, float(x.get("weight") or 1)) for x in best["items"])
        best["center"] = sum(float(x["center"]) * max(0.2, float(x.get("weight") or 1)) for x in best["items"]) / sw

    cooked = []
    for cl in clusters:
        items = cl["items"]
        sw = sum(max(0.2, float(x.get("weight") or 1)) for x in items)
        center = sum(float(x["center"]) * max(0.2, float(x.get("weight") or 1)) for x in items) / sw
        lows = [num(x.get("low")) for x in items]
        highs = [num(x.get("high")) for x in items]
        lows = [x for x in lows if x is not None]
        highs = [x for x in highs if x is not None]
        raw_low = min(lows) if lows else center
        raw_high = max(highs) if highs else center
        min_half = current * (0.0028 if context == "close" else 0.0018)
        half = max(min_half, (raw_high - raw_low) * 0.55)
        low = max(0.0, min(raw_low, center - half))
        high = max(raw_high, center + half)

        evidence = []
        for x in sorted(items, key=lambda q: float(q.get("weight") or 1), reverse=True):
            for label in [*(x.get("evidence") or []), x.get("label")]:
                label = str(label or "").strip()
                if label and label not in evidence:
                    evidence.append(label)
        strength = 5 if sw >= 8 else 4 if sw >= 5.5 else 3 if sw >= 3.5 else 2 if sw >= 2 else 1
        confidence = min(95, int(round(52 + strength * 6 + min(len(evidence), 4) * 3)))
        distance = (center / current - 1) * 100
        if low <= current <= high:
            state = "TESTING"
        elif abs(distance) <= 1.8:
            state = "NEAR"
        else:
            state = "ACTIVE"
        cooked.append({
            "low": round(low, 4),
            "high": round(high, 4),
            "center": round(center, 4),
            "distance_pct": round(distance, 3),
            "basis": "＋".join(evidence[:4]),
            "evidence": evidence[:8],
            "evidence_count": len(evidence),
            "strength": strength,
            "confidence": confidence,
            "structure_state": state,
            "_weight": sw,
        })

    # S1 is the nearest support below price; R1 the nearest resistance above.
    cooked.sort(key=lambda z: float(z["center"]), reverse=support)
    selected = cooked[:2]
    for i, z in enumerate(selected, 1):
        rank = ("S" if support else "R") + str(i)
        z["rank"] = rank
        z["label"] = (
            "近端支撐" if rank == "S1" else
            "第二支撐" if rank == "S2" else
            "第一壓力" if rank == "R1" else
            "第二壓力"
        )
        if support:
            z["validation_condition"] = "回測價格帶守住並重新站回上緣；量縮回測、量價重新轉強優先。"
            z["invalidation_condition"] = "不因單一刺穿判定失守；連續兩根對應週期K收在下緣下方，或跌破後反抽站不回且量價轉弱，才視為結構失效。"
        else:
            z["validation_condition"] = "有效站上壓力上緣且量價同步，之後回測壓力帶不破才視為突破確認。"
            z["invalidation_condition"] = "突破後快速跌回壓力帶下方且反抽無法站回，視為假突破並恢復壓力角色。"
        z.pop("_weight", None)
    return selected


def hourly_map(root: Path):
    obj = load(root / "hourly.json", {})
    rows = (obj.get("all_rows") or obj.get("rows") or []) if isinstance(obj, dict) else []
    return {str(x.get("code")): x for x in rows if isinstance(x, dict) and x.get("code")}


def candidate_pools(row, *, context, close_row=None, hourly=None, intraday_row=None):
    support, resistance = [], []
    current = num(row.get("close") or row.get("price"))
    if current is None or current <= 0:
        return current, support, resistance

    add_candidate(support, zone_candidate(row.get("support"), "原始加權支撐"))
    add_candidate(resistance, zone_candidate(row.get("resistance"), "原始加權壓力"))

    refs = close_row or row
    for key, label, weight in (
        ("ma5", "5MA", 1.1), ("ma10", "10MA", 1.35), ("ma20", "20MA", 1.8),
    ):
        p = num(refs.get(key))
        if p is not None:
            add_candidate(support if p <= current else resistance, point_candidate(p, label, weight))

    for source, label, weight in ((row.get("low"), "今日低", 1.25), (row.get("high"), "今日高", 1.25)):
        p = num(source)
        if p is not None:
            add_candidate(support if p <= current else resistance, point_candidate(p, label, weight))

    if context != "close":
        p = num(row.get("vwap"))
        if p is not None:
            add_candidate(support if p <= current else resistance, point_candidate(p, "VWAP", 2.0))

    if close_row and close_row is not row:
        add_candidate(support, zone_candidate(close_row.get("support"), "日K支撐", 3.4))
        add_candidate(resistance, zone_candidate(close_row.get("resistance"), "日K壓力", 3.4))

    h = hourly or {}
    for key, label, weight in (("ma20_60", "60分K 20T", 2.15), ("ma60_60", "60分K 60T", 2.0)):
        p = num(h.get(key))
        if p is not None and p > 0:
            add_candidate(support if p <= current else resistance, point_candidate(p, label, weight))

    # Daytrade inherits the current intraday structure as a strong same-session
    # reference. It still gets its own distance/state recalculated at its price.
    if context == "daytrade" and intraday_row:
        for z in intraday_row.get("support_levels") or []:
            add_candidate(support, zone_candidate(z, f"盤中{z.get('rank') or '支撐'}", 4.0))
        for z in intraday_row.get("resistance_levels") or []:
            add_candidate(resistance, zone_candidate(z, f"盤中{z.get('rank') or '壓力'}", 4.0))

    return current, support, resistance


def enrich_payload(payload, *, context, close_by_code, hourly_by_code, intraday_by_code):
    rows = rows_of(payload)
    changed = 0
    four_level = 0
    for row in rows:
        if not isinstance(row, dict) or not row.get("code"):
            continue
        code = str(row.get("code"))
        current, sup, res = candidate_pools(
            row,
            context=context,
            close_row=close_by_code.get(code),
            hourly=hourly_by_code.get(code),
            intraday_row=intraday_by_code.get(code),
        )
        if current is None:
            continue
        slevels = cluster_levels(current, sup, "SUPPORT", context)
        rlevels = cluster_levels(current, res, "RESISTANCE", context)
        row["support_levels"] = slevels
        row["resistance_levels"] = rlevels
        row["sr_structure"] = {
            "version": VERSION,
            "scoring_impact": "NONE",
            "legacy_primary_preserved": True,
            "support_count": len(slevels),
            "resistance_count": len(rlevels),
            "note": "S2/R2 為結構規劃層；不改既有 support/resistance 與評分權重。",
        }
        changed += 1
        if len(slevels) >= 2 and len(rlevels) >= 2:
            four_level += 1
    return changed, four_level


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs/data")
    args = ap.parse_args()
    root = Path(args.root)

    paths = {name: root / f"{name}.json" for name in ("close", "intraday", "daytrade")}
    payloads = {name: load(path, {}) for name, path in paths.items()}
    hmap = hourly_map(root)

    close_rows = rows_of(payloads["close"])
    close_by_code = {str(r.get("code")): r for r in close_rows if isinstance(r, dict) and r.get("code")}
    counts = {}

    changed, four = enrich_payload(
        payloads["close"], context="close", close_by_code=close_by_code,
        hourly_by_code=hmap, intraday_by_code={},
    )
    counts["close"] = {"rows": changed, "full_S1S2R1R2": four}
    close_by_code = {str(r.get("code")): r for r in rows_of(payloads["close"]) if isinstance(r, dict) and r.get("code")}

    changed, four = enrich_payload(
        payloads["intraday"], context="intraday", close_by_code=close_by_code,
        hourly_by_code=hmap, intraday_by_code={},
    )
    counts["intraday"] = {"rows": changed, "full_S1S2R1R2": four}
    intraday_by_code = {str(r.get("code")): r for r in rows_of(payloads["intraday"]) if isinstance(r, dict) and r.get("code")}

    changed, four = enrich_payload(
        payloads["daytrade"], context="daytrade", close_by_code=close_by_code,
        hourly_by_code=hmap, intraday_by_code=intraday_by_code,
    )
    counts["daytrade"] = {"rows": changed, "full_S1S2R1R2": four}

    for name, path in paths.items():
        if path.exists() and rows_of(payloads[name]):
            write(path, payloads[name])

    print("SR_STRUCTURE_2_0", json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
