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
    return list(dict.fromkeys(items))[:6]


def make_zone(value, side, decision):
    low, high, center = zone_numbers(value)
    if low is None or high is None or center is None:
        return None
    low, high = sorted((low, high))
    zone_id = f"{decision['decision_context_id']}:{side}"
    strength = None
    if isinstance(value, dict):
        strength = num(value.get("strength"))
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
        "low": round(low, 4),
        "high": round(high, 4),
        "center": round(center, 4),
        "strength": strength,
        "confidence": None,
        "evidence": evidence_of(value),
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
        support = first_present(row, ("support", "support_zone", "entry_support", "near_support"))
        resistance = first_present(row, ("resistance", "resistance_zone", "near_resistance"))
        support_zone = make_zone(support, "SUPPORT", decision) if support is not None else None
        resistance_zone = make_zone(resistance, "RESISTANCE", decision) if resistance is not None else None
        decision["support_zone_ids"] = [support_zone["zone_id"]] if support_zone else []
        decision["resistance_zone_ids"] = [resistance_zone["zone_id"]] if resistance_zone else []
        for zone in (support_zone, resistance_zone):
            if zone and zone["zone_id"] not in zone_by_id:
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
    note = "Phase 4：支撐／壓力區間由 v1.x 已計算結構遷移為 StructuralZone；Zone 本身不是買進訊號。"
    if note not in warnings:
        warnings.append(note)
    write_json(manifest_path, manifest)
    print("zone enrichment OK", counts)


if __name__ == "__main__":
    main()
