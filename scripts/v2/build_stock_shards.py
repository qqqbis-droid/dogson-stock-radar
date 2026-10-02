#!/usr/bin/env python3
"""Build mobile-safe per-stock detail shards from the canonical V2 Atomic bundle.

This is a publish-time transform only: the canonical whole-market datasets remain
unchanged. Each shard contains exactly one stock's decision, referenced zones,
and evidence so mobile clients never need to parse multi-megabyte market JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VIEW_CONFIG = {
    "intraday": ("decision_intraday_detail", "zone_intraday", "stock_detail_intraday"),
    "close": ("decision_close_detail", "zone_close", "stock_detail_close"),
    "daytrade": ("decision_daytrade_detail", "zone_daytrade", "stock_detail_daytrade"),
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_path(data_root: Path, meta: dict[str, Any]) -> Path:
    raw = str(meta.get("url") or "")
    if raw.startswith("./data/"):
        rel = raw[len("./data/") :]
    elif raw.startswith("data/"):
        rel = raw[len("data/") :]
    else:
        rel = raw.lstrip("./")
    if not rel:
        raise ValueError("dataset url is empty")
    return data_root / rel


def keyed_items(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        items = obj.get("items", obj)
        if isinstance(items, dict):
            return {str(k): v for k, v in items.items()}
        if isinstance(items, list):
            out: dict[str, Any] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                code = item.get("code") or item.get("stock_code") or item.get("symbol")
                if code is not None:
                    out[str(code)] = item
            return out
    if isinstance(obj, list):
        out = {}
        for item in obj:
            if not isinstance(item, dict):
                continue
            code = item.get("code") or item.get("stock_code") or item.get("symbol")
            if code is not None:
                out[str(code)] = item
        return out
    return {}


def zone_items(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in ("items", "zones"):
            value = obj.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
            if isinstance(value, dict):
                return [x for x in value.values() if isinstance(x, dict)]
    return []


def code_of_zone(zone: dict[str, Any]) -> str:
    for key in ("code", "stock_code", "symbol", "ticker"):
        value = zone.get(key)
        if value is not None:
            return str(value)
    return ""


def context_of_zone(zone: dict[str, Any]) -> str:
    for key in ("decision_context_id", "context_id"):
        value = zone.get(key)
        if value:
            return str(value)
    zone_id = str(zone.get("zone_id") or "")
    if ":SUPPORT:" in zone_id:
        return zone_id.split(":SUPPORT:", 1)[0]
    if ":RESISTANCE:" in zone_id:
        return zone_id.split(":RESISTANCE:", 1)[0]
    return ""


def selected_zones(
    decision: dict[str, Any],
    code: str,
    zones: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    wanted: list[str] = []
    for key in ("support_zone_ids", "resistance_zone_ids"):
        values = decision.get(key) or []
        if isinstance(values, (list, tuple)):
            wanted.extend(str(x) for x in values if x is not None)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(zone: dict[str, Any], fallback: str = "") -> None:
        dedupe = str(zone.get("zone_id") or fallback or id(zone))
        if dedupe not in seen:
            seen.add(dedupe)
            out.append(zone)

    # Primary path: explicit decision -> zone ids.
    for zone_id in wanted:
        zone = by_id.get(zone_id)
        if zone is not None:
            add(zone, zone_id)

    # Defensive path 1: context id. Older/preserved Atomic bundles can retain the
    # zones while losing the copied support_zone_ids/resistance_zone_ids fields.
    context_ids = {
        str(x)
        for x in (decision.get("decision_context_id"), decision.get("context_id"))
        if x
    }
    if not out or len(out) < len(set(wanted)):
        for zone in zones:
            if context_ids and context_of_zone(zone) in context_ids:
                add(zone)

    # Defensive path 2: stock code. Zone 3.0 stores code explicitly so a
    # UI-only bundle-preservation step can never turn a valid price map blank.
    if not out or len(out) < len(set(wanted)):
        for zone in zones:
            if code_of_zone(zone) == code:
                add(zone)

    # Never mix another stock's zones into this shard.
    filtered = []
    for zone in out:
        zcode = code_of_zone(zone)
        if zcode and zcode != code:
            continue
        filtered.append(zone)
    return filtered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="docs/v2/data")
    parser.add_argument("--max-shard-bytes", type=int, default=512_000)
    args = parser.parse_args()

    data_root = Path(args.data_root)
    manifest_path = data_root / "current_manifest.json"
    manifest = read_json(manifest_path)
    build_id = str(manifest.get("active_build_id") or "")
    if not build_id:
        raise SystemExit("active_build_id missing")
    datasets = manifest.get("datasets") or {}
    build_dir = data_root / "builds" / build_id
    if not build_dir.is_dir():
        raise SystemExit(f"active build directory missing: {build_dir}")

    shard_root = build_dir / "stock-shards"
    if shard_root.exists():
        import shutil
        shutil.rmtree(shard_root)
    shard_root.mkdir(parents=True, exist_ok=True)

    stats: dict[str, Any] = {"build_id": build_id, "views": {}}
    total_files = 0
    total_bytes = 0

    for view, (detail_key, zone_key, evidence_key) in VIEW_CONFIG.items():
        metas = [datasets.get(detail_key), datasets.get(zone_key), datasets.get(evidence_key)]
        if any(not isinstance(meta, dict) for meta in metas):
            if view == "daytrade":
                stats["views"][view] = {"files": 0, "bytes": 0, "skipped": True}
                continue
            raise SystemExit(f"missing required shard source for {view}")

        detail_meta, zone_meta, evidence_meta = metas  # type: ignore[misc]
        detail_obj = read_json(dataset_path(data_root, detail_meta))
        zone_obj = read_json(dataset_path(data_root, zone_meta))
        evidence_obj = read_json(dataset_path(data_root, evidence_meta))

        if isinstance(detail_obj, dict) and detail_obj.get("build_id") not in (None, build_id):
            raise SystemExit(f"{detail_key} build mismatch")
        if isinstance(evidence_obj, dict) and evidence_obj.get("build_id") not in (None, build_id):
            raise SystemExit(f"{evidence_key} build mismatch")

        decisions = keyed_items(detail_obj)
        evidence = keyed_items(evidence_obj)
        zones = zone_items(zone_obj)
        by_id = {str(z.get("zone_id")): z for z in zones if z.get("zone_id") is not None}

        view_dir = shard_root / view
        view_dir.mkdir(parents=True, exist_ok=True)
        view_files = 0
        view_bytes = 0
        shards_with_zones = 0

        for code, decision in decisions.items():
            if not isinstance(decision, dict):
                continue
            if decision.get("build_id") not in (None, build_id):
                raise SystemExit(f"decision build mismatch: {view} {code}")
            picked = selected_zones(decision, code, zones, by_id)
            if picked:
                shards_with_zones += 1
            payload = {
                "schema_version": "1.1.0",
                "build_id": build_id,
                "view": view,
                "code": code,
                "as_of": decision.get("as_of") or detail_meta.get("as_of"),
                "known_at": decision.get("known_at") or detail_meta.get("known_at"),
                "decision": decision,
                "zones": picked,
                "evidence": evidence.get(code),
            }
            encoded = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            if len(encoded) > args.max_shard_bytes:
                raise SystemExit(f"shard too large: {view}/{code}.json {len(encoded)} bytes")
            path = view_dir / f"{code}.json"
            path.write_bytes(encoded)
            view_files += 1
            view_bytes += len(encoded)

        stats["views"][view] = {
            "files": view_files,
            "bytes": view_bytes,
            "skipped": False,
            "shards_with_zones": shards_with_zones,
        }
        if view == "close" and view_files and not shards_with_zones:
            raise SystemExit("close shards lost every support/resistance zone")
        total_files += view_files
        total_bytes += view_bytes

    stats["total_files"] = total_files
    stats["total_bytes"] = total_bytes
    (shard_root / "index.json").write_text(
        json.dumps(stats, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    if total_files == 0:
        raise SystemExit("no stock shards generated")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
