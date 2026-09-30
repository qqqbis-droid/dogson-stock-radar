#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: pathlib.Path, obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    return {
        "hash": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "bytes": len(text.encode("utf-8")),
    }


def fingerprint(paths: list[pathlib.Path], base: pathlib.Path) -> str:
    h = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p.relative_to(base) if p.is_relative_to(base) else p)):
        if not path.is_file():
            continue
        try:
            label = str(path.relative_to(base))
        except ValueError:
            label = str(path)
        h.update(label.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def replace_build_id(value, old_id: str, new_id: str):
    if isinstance(value, dict):
        return {k: replace_build_id(v, old_id, new_id) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_build_id(v, old_id, new_id) for v in value]
    if isinstance(value, str):
        return value.replace(old_id, new_id)
    return value


def implementation_paths(root: pathlib.Path) -> list[pathlib.Path]:
    paths = []
    # Atomic Build identity follows production transformation logic, including
    # this identity algorithm itself. Unit-test-only edits must not create a
    # new market-data snapshot identity.
    paths.extend(
        p for p in (root / "scripts" / "v2").glob("*.py")
        if not p.name.startswith("test_")
    )
    paths.extend((root / "contracts").rglob("*.json"))
    req = root / "requirements-contract.txt"
    if req.exists():
        paths.append(req)
    return [p for p in paths if p.is_file()]


def source_paths(legacy_root: pathlib.Path) -> list[pathlib.Path]:
    names = ("close.json", "intraday.json", "daytrade.json", "market.json")
    return [legacy_root / name for name in names if (legacy_root / name).is_file()]


def rekey(*, output_root: pathlib.Path, legacy_root: pathlib.Path, root: pathlib.Path = ROOT):
    manifest_path = output_root / "current_manifest.json"
    manifest = load_json(manifest_path)
    old_id = manifest["active_build_id"]
    trade_date = str(manifest.get("trade_date") or "unknown").replace("-", "")
    source_fp = fingerprint(source_paths(legacy_root), root)[:10]
    impl_fp = fingerprint(implementation_paths(root), root)[:10]
    new_id = f"cb2-real-{trade_date}-s{source_fp}-i{impl_fp}"

    old_dir = output_root / "builds" / old_id
    new_dir = output_root / "builds" / new_id
    if old_id != new_id:
        if new_dir.exists():
            shutil.rmtree(new_dir)
        for path in old_dir.rglob("*.json"):
            obj = replace_build_id(load_json(path), old_id, new_id)
            write_json(path, obj)
        old_dir.rename(new_dir)
        manifest = replace_build_id(manifest, old_id, new_id)

    manifest["active_build_id"] = new_id
    manifest.setdefault("health", {})["build_identity"] = {
        "source_fingerprint": source_fp,
        "implementation_fingerprint": impl_fp,
        "identity_rule": "source-content + production-v2-implementation-contract",
    }

    for key, meta in manifest.get("datasets", {}).items():
        url = str(meta.get("url") or "")
        filename = pathlib.Path(url).name
        path = new_dir / filename
        if not path.exists():
            continue
        raw = path.read_bytes()
        meta["build_id"] = new_id
        meta["hash"] = "sha256:" + hashlib.sha256(raw).hexdigest()
        meta["bytes"] = len(raw)

    write_json(manifest_path, manifest)
    return new_id, source_fp, impl_fp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT / "docs" / "v2" / "data"))
    ap.add_argument("--legacy-root", default=str(ROOT / "docs" / "data"))
    args = ap.parse_args()
    build_id, source_fp, impl_fp = rekey(
        output_root=pathlib.Path(args.output),
        legacy_root=pathlib.Path(args.legacy_root),
    )
    print("build identity OK", build_id, "source", source_fp, "impl", impl_fp)


if __name__ == "__main__":
    main()
