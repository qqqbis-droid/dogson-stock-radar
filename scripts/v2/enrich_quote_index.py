#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def write_json(path, obj):
    path = pathlib.Path(path)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    raw = text.encode("utf-8")
    return {"hash": "sha256:" + hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def resolve(root, url):
    raw = str(url)
    if raw.startswith("./data/"):
        return root / raw[len("./data/"):]
    return root / raw.lstrip("./")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT / "docs" / "v2" / "data"))
    args = ap.parse_args()
    root = pathlib.Path(args.output)
    manifest_path = root / "current_manifest.json"
    manifest = load_json(manifest_path)
    build_id = manifest["active_build_id"]
    changed = {}

    for context in ("close", "intraday", "daytrade"):
        index_key = f"decision_{context}_index"
        detail_key = f"decision_{context}_detail"
        if index_key not in manifest.get("datasets", {}) or detail_key not in manifest.get("datasets", {}):
            continue
        index_path = resolve(root, manifest["datasets"][index_key]["url"])
        detail_path = resolve(root, manifest["datasets"][detail_key]["url"])
        index_rows = load_json(index_path)
        detail = load_json(detail_path)
        detail_items = detail.get("items") or {}
        count = 0
        for row in index_rows:
            full = detail_items.get(str(row.get("code")))
            if not isinstance(full, dict):
                continue
            row["quote"] = full.get("quote") or {
                "price": None,
                "day_change_pct": None,
                "volume": None,
                "volume_unit": "UNKNOWN",
                "relative_volume": None,
                "turnover_value_twd": None,
                "quote_time": full.get("as_of"),
            }
            count += 1
        meta = write_json(index_path, index_rows)
        manifest["datasets"][index_key].update(meta)
        changed[context] = count

    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    note = "Phase 4：行情快照已進入 StockDecision.quote；未知成交量單位保留 UNKNOWN，不自行換算。"
    if note not in warnings:
        warnings.append(note)
    write_json(manifest_path, manifest)
    print("quote index enrichment OK", build_id, changed)


if __name__ == "__main__":
    main()
