#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
from copy import deepcopy

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def write_json(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    return {
        "hash": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "bytes": len(text.encode("utf-8")),
    }


def rows_of(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "all_rows", "items", "data", "stocks", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except Exception:
        return None


def first_present(row, keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, "", []):
            return value
    return None


def zone_numbers(value):
    if isinstance(value, dict):
        low = num(first_present(value, ("low", "zone_low", "min", "lower")))
        high = num(first_present(value, ("high", "zone_high", "max", "upper")))
        center = num(first_present(value, ("center", "price", "level", "mid")))
        if center is None and low is not None and high is not None:
            center = (low + high) / 2
        if low is None and center is not None:
            low = center
        if high is None and center is not None:
            high = center
        return low, high, center
    center = num(value)
    return (center, center, center) if center is not None else (None, None, None)


def evidence_of(value):
    if not isinstance(value, dict):
        return []
    items = []
    raw = value.get("evidence") or value.get("labels")
    if isinstance(raw, list):
        items.extend(str(x).strip() for x in raw if str(x).strip())
    basis = value.get("basis") or value.get("reason")
    if isinstance(basis, str) and basis.strip():
        items.extend(x.strip() for x in basis.replace("+", "＋").split("＋") if x.strip())
    return list(dict.fromkeys(items))[:10]


def current_price(row):
    return num(first_present(row, ("quote_close", "close", "price", "last", "last_price")))


def _candidate(value, label, weight, anchor=False):
    low, high, center = zone_numbers(value)
    if low is None or high is None or center is None or center <= 0:
        return None
    low, high = sorted((low, high))
    ev = evidence_of(value)
    if not ev:
        ev = [label]
    strength = num(value.get("strength")) if isinstance(value, dict) else None
    confidence = num(value.get("confidence")) if isinstance(value, dict) else None
    return {
        "low": low,
        "high": high,
        "center": center,
        "evidence": ev,
        "weight": max(0.2, float(weight)) + (0.18 * (strength or 0)),
        "anchor": bool(anchor),
        "source_strength": strength,
        "source_confidence": confidence,
    }


def _add_candidate(out, value, label, weight, anchor=False):
    c = _candidate(value, label, weight, anchor)
    if c:
        out.append(c)


def _raw_anchor_values(row, side):
    array_key = "support_levels" if side == "SUPPORT" else "resistance_levels"
    values = row.get(array_key)
    out = [x for x in values if isinstance(x, dict)] if isinstance(values, list) else []
    legacy_keys = (
        ("support", "support_zone", "entry_support", "near_support")
        if side == "SUPPORT"
        else ("resistance", "resistance_zone", "near_resistance")
    )
    legacy = first_present(row, legacy_keys)
    if legacy is not None:
        out.append(legacy)
    return out


def _atr_pct(row):
    profile = row.get("dynamic_profile") if isinstance(row.get("dynamic_profile"), dict) else {}
    return num(profile.get("atr14_pct")) or 0.0


def fused_levels(row, side, hourly=None):
    """Build up to S1/S2 or R1/R2 from independent technical evidence.

    The legacy daily zone is already a cluster of pivots / volume-by-price /
    gaps / moving averages.  We keep that as the strongest anchor, then add
    daily MAs and 60-minute 20T/60T/240T levels.  Nearby evidence is clustered
    into a price *band*, not presented as a falsely precise single price.
    """
    cur = current_price(row)
    if cur is None or cur <= 0:
        return _raw_anchor_values(row, side)[:2]

    candidates = []
    for value in _raw_anchor_values(row, side):
        _add_candidate(candidates, value, "日K多證據結構", 3.1, True)

    # Daily structure.  20/60MA carry more weight than very short 5/10MA.
    for key, label, weight in (
        ("ma5", "5MA", 1.05),
        ("ma10", "10MA", 1.35),
        ("ma20", "20MA", 2.05),
        ("ma60", "60MA", 2.20),
        ("ma120", "120MA", 2.00),
    ):
        v = num(row.get(key))
        if v is not None:
            _add_candidate(candidates, {"center": v, "basis": label}, label, weight)

    # Today's high/low are weak evidence only; they can reinforce a cluster but
    # cannot independently create a high-confidence zone.
    if side == "SUPPORT":
        v = num(row.get("low"))
        if v is not None:
            _add_candidate(candidates, {"center": v, "basis": "今日低"}, "今日低", 0.85)
    else:
        v = num(row.get("high"))
        if v is not None:
            _add_candidate(candidates, {"center": v, "basis": "今日高"}, "今日高", 0.85)

    # Cross-timeframe confirmation from the canonical 60K Engine.
    hourly = hourly or {}
    for key, label, weight in (
        ("ma20_60", "60分20T", 1.75),
        ("ma60_60", "60分60T", 2.05),
        ("ma240_60", "60分240T", 2.25),
    ):
        v = num(hourly.get(key))
        if v is not None:
            _add_candidate(candidates, {"center": v, "basis": label}, label, weight)

    side_candidates = []
    for c in candidates:
        p = c["center"]
        if side == "SUPPORT" and p <= cur * 1.003:
            side_candidates.append(c)
        elif side == "RESISTANCE" and p >= cur * 0.997:
            side_candidates.append(c)
    if not side_candidates:
        return []

    atr_pct = _atr_pct(row)
    cluster_pct = max(0.0065, min(0.018, (atr_pct / 100.0) * 0.32 if atr_pct else 0.0105))
    max_dist = 0.18
    near = [c for c in side_candidates if abs(c["center"] / cur - 1) <= max_dist]
    if near:
        side_candidates = near

    clusters = []
    for seed in side_candidates:
        members = [c for c in side_candidates if abs(c["center"] / seed["center"] - 1) <= cluster_pct]
        if not members:
            continue
        sw = sum(c["weight"] for c in members)
        center = sum(c["center"] * c["weight"] for c in members) / max(sw, 1e-9)
        distance = (center / cur - 1) * 100
        evidence = []
        for c in sorted(members, key=lambda x: x["weight"], reverse=True):
            for e in c["evidence"]:
                if e not in evidence:
                    evidence.append(e)
        anchor_count = sum(1 for c in members if c["anchor"])
        # One short MA alone is deliberately not enough.  A legacy multi-evidence
        # anchor, >=2 independent labels, or a structurally strong MA may qualify.
        credible = bool(anchor_count or len(evidence) >= 2 or sw >= 2.0)
        if not credible:
            continue
        quality = sw + 0.45 * len(evidence) + 0.8 * anchor_count - abs(distance / 100.0) * 8
        spread = max(c["high"] for c in members) - min(c["low"] for c in members)
        anchor_half = max(((c["high"] - c["low"]) / 2 for c in members if c["anchor"]), default=0.0)
        atr_half = cur * max(0.0035, min(0.012, (atr_pct / 100.0) * 0.16 if atr_pct else 0.0045))
        half = max(cur * 0.0035, atr_half, spread * 0.55, anchor_half)
        confidence = min(100.0, 30.0 + sw * 7.0 + len(evidence) * 4.5 + anchor_count * 8.0)
        strength = 5 if confidence >= 82 else 4 if confidence >= 68 else 3 if confidence >= 54 else 2 if confidence >= 42 else 1
        clusters.append({
            "center": center,
            "low": max(0.0, center - half),
            "high": center + half,
            "distance_pct": distance,
            "basis": "＋".join(evidence[:6]),
            "evidence": evidence[:8],
            "evidence_count": len(evidence),
            "strength": strength,
            "confidence": round(confidence, 1),
            "quality": quality,
        })

    # Deduplicate seed-generated copies of the same cluster.
    unique = []
    for c in sorted(clusters, key=lambda x: (-x["quality"], abs(x["distance_pct"]))):
        if any(abs(c["center"] / x["center"] - 1) <= cluster_pct * 0.55 for x in unique):
            continue
        unique.append(c)

    # S1/R1 = nearest credible band.  S2/R2 = next distinct structural band.
    chosen = []
    for c in sorted(unique, key=lambda x: (abs(x["distance_pct"]), -x["quality"])):
        if any(abs(c["center"] / x["center"] - 1) <= max(0.008, cluster_pct * 0.75) for x in chosen):
            continue
        chosen.append(c)
        if len(chosen) == 2:
            break

    out = []
    prefix = "S" if side == "SUPPORT" else "R"
    for i, c in enumerate(chosen, start=1):
        rank = f"{prefix}{i}"
        if side == "SUPPORT":
            validation = "回測價格帶守住並重新站回上緣；量縮回測優先。"
            invalidation = "連續兩根對應週期K收在支撐帶下緣下方，或跌破後反抽站不回且量價轉弱，才視為結構失效。"
            label = "第一防守帶" if i == 1 else "深層防守帶"
        else:
            validation = "有效收上壓力帶上緣且量能不萎縮；突破後回測不破才算確認。"
            invalidation = "突破後快速跌回壓力帶下方且無法站回，視為假突破並恢復壓力角色。"
            label = "第一突破帶" if i == 1 else "延伸突破帶"
        out.append({
            "rank": rank,
            "label": label,
            "low": round(c["low"], 2),
            "high": round(c["high"], 2),
            "center": round(c["center"], 2),
            "distance_pct": round(c["distance_pct"], 2),
            "basis": c["basis"],
            "evidence": c["evidence"],
            "evidence_count": c["evidence_count"],
            "strength": c["strength"],
            "confidence": c["confidence"],
            "structure_state": "ACTIVE",
            "validation_condition": validation,
            "invalidation_condition": invalidation,
        })
    return out


def make_zone(value, side, decision, ordinal, code):
    low, high, center = zone_numbers(value)
    if low is None or high is None or center is None:
        return None
    low, high = sorted((low, high))
    prefix = "S" if side == "SUPPORT" else "R"
    default_rank = f"{prefix}{ordinal}"
    rank = str(value.get("rank") or default_rank) if isinstance(value, dict) else default_rank
    if rank not in {"S1", "S2", "R1", "R2"}:
        rank = default_rank
    context_id = str(decision.get("decision_context_id") or decision.get("context_id") or "")
    zone_id = f"{context_id}:{side}:{rank}"
    strength = num(value.get("strength")) if isinstance(value, dict) else None
    confidence = num(value.get("confidence")) if isinstance(value, dict) else None
    distance_pct = num(value.get("distance_pct")) if isinstance(value, dict) else None
    evidence_count = value.get("evidence_count") if isinstance(value, dict) else None
    label = value.get("label") if isinstance(value, dict) else None
    structure_state = value.get("structure_state") if isinstance(value, dict) else None
    validation_condition = value.get("validation_condition") if isinstance(value, dict) else None
    invalidation_condition = value.get("invalidation_condition") if isinstance(value, dict) else None
    evidence = evidence_of(value)
    return {
        "schema_version": "3.0.0",
        "build_id": decision["build_id"],
        "dataset": "zone",
        "trade_date": decision.get("trade_date"),
        "session_phase": decision.get("session_phase"),
        "as_of": decision.get("as_of"),
        "known_at": decision.get("known_at"),
        "generated_at": decision.get("generated_at"),
        "freshness": decision.get("freshness"),
        "complete": True,
        "source_status": deepcopy(decision.get("source_status") or {"sources": [], "fallback": False}),
        "code": str(code),
        "decision_context_id": context_id,
        "zone_id": zone_id,
        "side": side,
        "rank": rank,
        "label": str(label or ("第一防守帶" if rank == "S1" else "深層防守帶" if rank == "S2" else "第一突破帶" if rank == "R1" else "延伸突破帶")),
        "low": round(low, 4),
        "high": round(high, 4),
        "center": round(center, 4),
        "distance_pct": round(distance_pct, 4) if distance_pct is not None else None,
        "strength": strength,
        "confidence": confidence,
        "evidence": evidence,
        "evidence_count": int(evidence_count) if evidence_count is not None else len(evidence),
        "structure_state": str(structure_state or "ACTIVE"),
        "validation_condition": str(validation_condition) if validation_condition else None,
        "invalidation_condition": str(invalidation_condition) if invalidation_condition else None,
        "created_at": decision.get("generated_at"),
        "last_tested_at": None,
        "role_state": "ORIGINAL",
    }


def reference_only_marker(decision):
    return {
        "schema_version": "3.0.0",
        "build_id": decision["build_id"],
        "dataset": "zone",
        "trade_date": decision.get("trade_date"),
        "session_phase": decision.get("session_phase"),
        "as_of": decision.get("as_of"),
        "known_at": decision.get("known_at"),
        "generated_at": decision.get("generated_at"),
        "freshness": decision.get("freshness"),
        "complete": True,
        "source_status": deepcopy(decision.get("source_status") or {"sources": [], "fallback": False}),
        "code": "",
        "decision_context_id": str(decision.get("decision_context_id") or ""),
        "zone_id": f"{decision['build_id']}:DAYTRADE:REFERENCE_ONLY",
        "side": "SUPPORT",
        "rank": "S1",
        "label": "市場已收盤・當沖結構停用",
        "low": 0.0,
        "high": 0.0,
        "center": 0.0,
        "distance_pct": None,
        "strength": 0.0,
        "confidence": 0.0,
        "evidence": ["REFERENCE_ONLY", "DATA_STALE", "NON_EXECUTABLE"],
        "evidence_count": 3,
        "structure_state": "BROKEN",
        "validation_condition": None,
        "invalidation_condition": "市場非 LIVE；此記錄只是停用標記，不是可執行支撐／壓力",
        "created_at": decision.get("generated_at"),
        "last_tested_at": None,
        "role_state": "EXPIRED",
    }


def source_map(payload):
    return {str(r.get("code")): r for r in rows_of(payload) if isinstance(r, dict) and r.get("code")}


def enrich_context(*, legacy_root, output_root, manifest, context, source_file, hourly_by_code):
    build_id = manifest["active_build_id"]
    build_dir = output_root / "builds" / build_id
    detail_key = f"decision_{context}_detail"
    summary_key = f"decision_{context}_summary"
    if detail_key not in manifest.get("datasets", {}):
        return []

    detail_path = build_dir / pathlib.Path(manifest["datasets"][detail_key]["url"]).name
    summary_path = build_dir / pathlib.Path(manifest["datasets"][summary_key]["url"]).name
    detail = load_json(detail_path, {})
    summary = load_json(summary_path, [])
    raw = source_map(load_json(legacy_root / source_file, {}))

    zones = []
    zone_by_id = {}
    decisions = detail.get("items") or {}
    for code, decision in decisions.items():
        row = raw.get(str(code), {})
        live_unverified = context in {"intraday", "daytrade"} and (
            decision.get("action_state") == "DATA_STALE"
            or "DATA_QUALITY_RISK" in (decision.get("risk_overlays") or [])
        )
        if live_unverified:
            decision["support_zone_ids"] = []
            decision["resistance_zone_ids"] = []
            continue

        hourly = hourly_by_code.get(str(code), {}) if context == "close" else {}
        support_values = fused_levels(row, "SUPPORT", hourly)
        resistance_values = fused_levels(row, "RESISTANCE", hourly)
        support_zones = [make_zone(v, "SUPPORT", decision, i, str(code)) for i, v in enumerate(support_values, 1)]
        resistance_zones = [make_zone(v, "RESISTANCE", decision, i, str(code)) for i, v in enumerate(resistance_values, 1)]
        support_zones = [z for z in support_zones if z]
        resistance_zones = [z for z in resistance_zones if z]
        decision["support_zone_ids"] = [z["zone_id"] for z in support_zones]
        decision["resistance_zone_ids"] = [z["zone_id"] for z in resistance_zones]
        for zone in [*support_zones, *resistance_zones]:
            if zone["zone_id"] not in zone_by_id:
                zone_by_id[zone["zone_id"]] = zone
                zones.append(zone)

    if context == "daytrade" and not zones and decisions:
        decision_values = [x for x in decisions.values() if isinstance(x, dict)]
        if decision_values and all(str(x.get("action_state") or "") == "DATA_STALE" for x in decision_values):
            zones.append(reference_only_marker(decision_values[0]))

    summary_by_code = {str(x.get("code")): x for x in summary if isinstance(x, dict)}
    for code, full in decisions.items():
        short = summary_by_code.get(str(code))
        if short is not None:
            short["support_zone_ids"] = list(full.get("support_zone_ids") or [])
            short["resistance_zone_ids"] = list(full.get("resistance_zone_ids") or [])

    detail_meta = write_json(detail_path, detail)
    summary_meta = write_json(summary_path, summary)
    manifest["datasets"][detail_key].update(detail_meta)
    manifest["datasets"][summary_key].update(summary_meta)

    zone_key = f"zone_{context}"
    zone_filename = f"zone-{context}.json"
    zone_meta = write_json(build_dir / zone_filename, zones)
    source_meta = manifest["datasets"][detail_key]
    manifest["datasets"][zone_key] = {
        "url": f"./data/builds/{build_id}/{zone_filename}",
        "hash": zone_meta["hash"],
        "bytes": zone_meta["bytes"],
        "complete": True,
        "as_of": source_meta.get("as_of"),
        "known_at": source_meta.get("known_at"),
        "build_id": build_id,
    }
    return zones


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-root", default=str(ROOT / "docs" / "data"))
    ap.add_argument("--output", default=str(ROOT / "docs" / "v2" / "data"))
    args = ap.parse_args()
    legacy_root = pathlib.Path(args.legacy_root)
    output_root = pathlib.Path(args.output)
    manifest_path = output_root / "current_manifest.json"
    manifest = load_json(manifest_path, {})
    if not manifest.get("active_build_id"):
        raise SystemExit("active_build_id missing")

    hourly_by_code = source_map(load_json(legacy_root / "hourly.json", {}))
    counts = {}
    for context, source_file in (
        ("close", "close.json"),
        ("intraday", "intraday.json"),
        ("daytrade", "daytrade.json"),
    ):
        zones = enrich_context(
            legacy_root=legacy_root,
            output_root=output_root,
            manifest=manifest,
            context=context,
            source_file=source_file,
            hourly_by_code=hourly_by_code,
        )
        counts[context] = len(zones)

    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    note = "支撐／壓力結構 3.0：日K多證據結構＋日均線＋60分K 20T/60T/240T 共振；以價格帶呈現 S1/S2/R1/R2，不把單點價位當成假精準值。"
    if note not in warnings:
        warnings.append(note)
    write_json(manifest_path, manifest)
    print("zone enrichment 3.0 OK", counts)


if __name__ == "__main__":
    main()
