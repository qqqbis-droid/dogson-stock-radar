#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT / "docs" / "v2" / "data"))
    args = parser.parse_args()
    stamp(pathlib.Path(args.root))


if __name__ == "__main__":
    main()
