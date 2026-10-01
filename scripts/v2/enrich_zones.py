#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from copy import deepcopy

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


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
        for key in ("rows", "items", "data", "stocks", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def num(value):
    try:
        value = float(value)
        return value if value == value else None
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
    return list(dict.fromkeys(items))[:8]


def levels_for(row, side):
    """Return ordered S1/S2 or R1/R2 source levels, with legacy fallback."""
    array_key = "support_levels" if side == "SUPPORT" else "resistance_levels"
    raw = row.get(array_key)
    if isinstance(raw, list):
        values = [x for x in raw if isinstance(x, dict)]
        if values:
            return values[:2]
    legacy_keys = (
        ("support", "support_zone", "entry_support", "near_support")
        if side == "SUPPORT"
        else ("resistance", "resistance_zone", "near_resistance")
    )
    value = first_present(row, legacy_keys)
    return [value] if value is not None else []


def make_zone(value, side, decision, ordinal):
    low, high, center = zone_numbers(value)
    if low is None or high is None or center is None:
        return None
    low, high = sorted((low, high))
    prefix = "S" if side == "SUPPORT" else "R"
    default_rank = f"{prefix}{ordinal}"
    rank = str(value.get("rank") or default_rank) if isinstance(value, dict) else default_rank
    if rank not in {"S1", "S2", "R1", "R2"}:
        rank = default_rank
    zone_id = f"{decision['decision_context_id']}:{side}:{rank}"
    strength = num(value.get("strength")) if isinstance(value, dict) else None
    confidence = num(value.get("confidence")) if isinstance(value, dict) else None
    distance_pct = num(value.get("distance_pct")) if isinstance(value, dict) else None
    evidence_count = None
    label = None
    structure_state = None
    validation_condition = None
    invalidation_condition = None
    if isinstance(value, dict):
        evidence_count = value.get("evidence_count")
        label = value.get("label")
        structure_state = value.get("structure_state")
        validation_condition = value.get("validation_condition")
        invalidation_condition = value.get("invalidation_condition")
    return {
        "schema_version": "2.0.0",
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
        "zone_id": zone_id,
        "side": side,
        "rank": rank,
        "label": str(label or ("近端支撐" if rank == "S1" else "第二支撐" if rank == "S2" else "第一壓力" if rank == "R1" else "第二壓力")),
        "low": round(low, 4),
        "high": round(high, 4),
        "center": round(center, 4),
        "distance_pct": round(distance_pct, 4) if distance_pct is not None else None,
        "strength": strength,
        "confidence": confidence,
        "evidence": evidence_of(value),
        "evidence_count": int(evidence_count) if evidence_count is not None else len(evidence_of(value)),
        "structure_state": str(structure_state or "ACTIVE"),
        "validation_condition": str(validation_condition) if validation_condition else None,
        "invalidation_condition": str(invalidation_condition) if invalidation_condition else None,
        "created_at": decision.get("generated_at"),
        "last_tested_at": None,
        "role_state": "ORIGINAL",
    }


def source_map(payload):
    return {str(r.get("code")): r for r in rows_of(payload) if isinstance(r, dict) and r.get("code")}


def enrich_context(*, legacy_root, output_root, manifest, context, source_file):
    build_id = manifest["active_build_id"]
    build_dir = output_root / "builds" / build_id
    detail_key = f"decision_{context}_detail"
    summary_key = f"decision_{context}_summary"
    if detail_key not in manifest["datasets"]:
        return []

    detail_path = build_dir / pathlib.Path(manifest["datasets"][detail_key]["url"]).name
    summary_path = build_dir / pathlib.Path(manifest["datasets"][summary_key]["url"]).name
    detail = load_json(detail_path)
    summary = load_json(summary_path)
    raw = source_map(load_json(legacy_root / source_file))

    zones = []
    zone_by_id = {}
    for code, decision in (detail.get("items") or {}).items():
        row = raw.get(str(code), {})
        support_zones = [
            make_zone(value, "SUPPORT", decision, i)
            for i, value in enumerate(levels_for(row, "SUPPORT"), start=1)
        ]
        resistance_zones = [
            make_zone(value, "RESISTANCE", decision, i)
            for i, value in enumerate(levels_for(row, "RESISTANCE"), start=1)
        ]
        support_zones = [z for z in support_zones if z]
        resistance_zones = [z for z in resistance_zones if z]
        decision["support_zone_ids"] = [z["zone_id"] for z in support_zones]
        decision["resistance_zone_ids"] = [z["zone_id"] for z in resistance_zones]
        for zone in [*support_zones, *resistance_zones]:
            if zone["zone_id"] not in zone_by_id:
                zone_by_id[zone["zone_id"]] = zone
                zones.append(zone)

    summary_by_code = {str(x.get("code")): x for x in summary if isinstance(x, dict)}
    for code, full in (detail.get("items") or {}).items():
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
    manifest = load_json(manifest_path)

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
        )
        counts[context] = len(zones)

    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    note = "支撐／壓力結構 2.0：每檔最多保留 S1/S2/R1/R2；Zone 只描述結構，不等於買進訊號。"
    if note not in warnings:
        warnings.append(note)
    write_json(manifest_path, manifest)
    print("zone enrichment 2.0 OK", counts)


if __name__ == "__main__":
    main()
