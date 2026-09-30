#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    raw = text.encode("utf-8")
    return {"hash": "sha256:" + hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def resolve(root: Path, url: str) -> Path:
    raw = str(url or "")
    if raw.startswith("./data/"):
        return root / raw[len("./data/"):]
    return root / raw.lstrip("./")


def rows(obj):
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict) and isinstance(obj.get("items"), dict):
        return [x for x in obj["items"].values() if isinstance(x, dict)]
    return []


def count_field(xs, key):
    return dict(Counter(str(x.get(key) or "UNKNOWN") for x in xs))


def mission_stats(root, manifest, key):
    meta = (manifest.get("datasets") or {}).get(key)
    if not meta:
        return {"total": 0, "buckets": {}, "stages": {}, "actions": {}, "freshness": {}, "as_of": None}
    xs = rows(load(resolve(root, meta.get("url"))))
    return {
        "total": len(xs),
        "buckets": count_field(xs, "opportunity_bucket"),
        "stages": count_field(xs, "lifecycle_stage"),
        "actions": count_field(xs, "action_state"),
        "freshness": count_field(xs, "freshness"),
        "as_of": meta.get("as_of"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs/v2/data")
    args = ap.parse_args()
    root = Path(args.root)
    mp = root / "current_manifest.json"
    m = load(mp)
    active = str(m.get("active_build_id") or "")
    if not active:
        raise SystemExit("radar stats: active_build_id missing")
    build = root / "builds" / active
    build.mkdir(parents=True, exist_ok=True)

    obj = {
        "schema_version": "1.0.0",
        "build_id": active,
        "generated_at": m.get("generated_at"),
        "missions": {
            "close": mission_stats(root, m, "decision_close_index"),
            "intraday": mission_stats(root, m, "decision_intraday_index"),
            "daytrade": mission_stats(root, m, "decision_daytrade_index"),
        },
    }
    path = build / "radar-stats.json"
    meta = write(path, obj)
    m.setdefault("datasets", {})["radar_stats"] = {
        "url": f"./data/builds/{active}/radar-stats.json",
        "hash": meta["hash"],
        "bytes": meta["bytes"],
        "complete": True,
        "as_of": m.get("generated_at"),
        "known_at": m.get("generated_at"),
        "build_id": active,
    }
    write(mp, m)
    print(json.dumps({"build": active, "missions": obj["missions"], "bytes": meta["bytes"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
