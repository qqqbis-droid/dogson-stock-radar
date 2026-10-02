#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRIES = ROOT / "contracts" / "registries"
VERSION_FIELDS = (
    "app_contract_version",
    "schema_version",
    "engine_version",
    "enum_registry_version",
    "threshold_registry_version",
    "taxonomy_version",
)


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stop(message: str):
    raise SystemExit(f"Version Registry contract failed: {message}")


def active_contract():
    registry = load(REGISTRIES / "version_registry.json")
    active_id = registry.get("active_version_set_id")
    version_sets = registry.get("version_sets") or {}
    if not active_id or active_id not in version_sets:
        stop("active_version_set_id is missing or unknown")
    active = version_sets[active_id]
    if active.get("status") != "active":
        stop(f"active version set {active_id} is not active")
    if sum(1 for item in version_sets.values() if item.get("status") == "active") != 1:
        stop("exactly one version set must be active")

    actual = {
        "enum_registry_version": load(REGISTRIES / "enum_registry.json").get("registry_version"),
        "threshold_registry_version": load(REGISTRIES / "threshold_registry.json").get("registry_version"),
        "taxonomy_version": load(REGISTRIES / "taxonomy_registry.json").get("taxonomy_version"),
    }
    for field, value in actual.items():
        if active.get(field) != value:
            stop(f"{field} drift: active={active.get(field)!r}, registry={value!r}")
    return registry, active_id, active


def resolve_dataset(root: pathlib.Path, meta: dict):
    raw = str((meta or {}).get("url") or "")
    if raw.startswith("./data/"):
        raw = raw[len("./data/") :]
    elif raw.startswith("data/"):
        raw = raw[len("data/") :]
    else:
        raw = raw.lstrip("./")
    return root / raw


def index_codes(obj):
    rows = obj.get("items", obj) if isinstance(obj, dict) else obj
    out = []
    if isinstance(rows, dict):
        for key, row in rows.items():
            if isinstance(row, dict):
                out.append(str(row.get("code") or row.get("stock_code") or key))
    elif isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            code = row.get("code") or row.get("stock_code") or row.get("symbol")
            if code is not None:
                out.append(str(code))
    return [x for x in out if x]


def ensure_stock_shards(root: pathlib.Path):
    manifest_path = root / "current_manifest.json"
    manifest = load(manifest_path)
    datasets = manifest.get("datasets") or {}
    required = (
        "decision_close_detail", "decision_close_index", "zone_close", "stock_detail_close",
        "decision_intraday_detail", "decision_intraday_index", "zone_intraday", "stock_detail_intraday",
    )
    missing = [key for key in required if key not in datasets]
    if missing:
        print("Stock shard build skipped; required datasets are not present:", missing)
        return

    builder = ROOT / "scripts" / "v2" / "build_stock_shards.py"
    if not builder.is_file():
        stop(f"stock shard builder missing: {builder}")
    subprocess.run(
        [sys.executable, str(builder), "--data-root", str(root)],
        check=True,
    )

    build_id = str(manifest.get("active_build_id") or "")
    if not build_id:
        stop("active_build_id missing while validating stock shards")
    shard_root = root / "builds" / build_id / "stock-shards"
    shard_index = shard_root / "index.json"
    if not shard_index.is_file() or shard_index.stat().st_size == 0:
        stop(f"stock shard index missing: {shard_index}")

    view_keys = {
        "close": "decision_close_index",
        "intraday": "decision_intraday_index",
        "daytrade": "decision_daytrade_index",
    }
    coverage = {}
    for view, key in view_keys.items():
        meta = datasets.get(key)
        if not isinstance(meta, dict):
            if view == "daytrade":
                continue
            stop(f"stock shard coverage source missing: {key}")
        src = resolve_dataset(root, meta)
        if not src.is_file():
            stop(f"stock shard coverage dataset missing: {key} -> {src}")
        codes = index_codes(load(src))
        missing_files = [code for code in codes if not (shard_root / view / f"{code}.json").is_file()]
        if missing_files:
            stop(f"stock shard coverage failed for {view}: {missing_files[:20]}")
        coverage[view] = len(codes)

    print("Stock shard coverage verified:", coverage)


def stamp(root: pathlib.Path):
    path = root / "current_manifest.json"
    if not path.exists():
        stop(f"manifest missing: {path}")
    manifest = load(path)
    registry, active_id, active = active_contract()
    expected = {
        "version_registry_version": registry["registry_version"],
        "version_set_id": active_id,
        **{field: active[field] for field in VERSION_FIELDS},
    }
    for field, value in expected.items():
        existing = manifest.get(field)
        if existing is not None and existing != value:
            stop(f"manifest {field} drift: manifest={existing!r}, active={value!r}")
        manifest[field] = value

    declared = set((registry.get("manifest_binding") or {}).get("fields") or [])
    if declared != set(expected):
        stop("manifest_binding.fields does not match the canonical version tuple")

    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(path)
    print("Version Registry bound:", active_id)
    ensure_stock_shards(root)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT / "docs" / "v2" / "data"))
    args = parser.parse_args()
    stamp(pathlib.Path(args.root))


if __name__ == "__main__":
    main()
