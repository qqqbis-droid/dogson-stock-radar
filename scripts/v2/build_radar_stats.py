#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


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
    xs = rows(load(resolve(root, meta.get("url")), []))
    return {
        "total": len(xs),
        "buckets": count_field(xs, "opportunity_bucket"),
        "stages": count_field(xs, "lifecycle_stage"),
        "actions": count_field(xs, "action_state"),
        "freshness": count_field(xs, "freshness"),
        "as_of": meta.get("as_of"),
    }


def shadow_progress(root: Path, manifest: dict):
    # The completed-session workflow keeps the canonical distinct-day summary at
    # shadow/summary.json. Fast intraday publishers also archive that file from
    # clean-build-v2 so every Atomic Build can expose the same validation status.
    candidates = [
        Path("shadow/summary.json"),
        root / "shadow-summary.json",  # compatibility fallback during migration
    ]
    summary = None
    for path in candidates:
        summary = load(path)
        if isinstance(summary, dict):
            break
    if not isinstance(summary, dict):
        # Preserve a previous embedded value if this publisher legitimately lacks
        # the Shadow tree. Never invent sample counts.
        old_meta = (manifest.get("datasets") or {}).get("radar_stats") or {}
        old_path = resolve(root, old_meta.get("url")) if old_meta.get("url") else None
        old = load(old_path) if old_path and old_path.exists() else None
        prior = old.get("shadow") if isinstance(old, dict) else None
        if isinstance(prior, dict):
            return prior
        return {
            "available": False,
            "distinct_trading_days": None,
            "minimum_review_days": 20,
            "target_window_days": 40,
            "remaining_to_review": None,
            "ready_for_review": False,
            "eligible_for_cutover": False,
            "unresolved_safety_violations": None,
            "latest_status": None,
            "latest_trade_date": None,
        }

    promo = summary.get("promotion") or {}
    days = int(summary.get("distinct_trading_days") or 0)
    minimum = int(promo.get("minimum_review_days") or 20)
    target = int(promo.get("target_window_days") or 40)
    return {
        "available": True,
        "distinct_trading_days": days,
        "minimum_review_days": minimum,
        "target_window_days": target,
        "remaining_to_review": max(0, minimum - days),
        "ready_for_review": bool(promo.get("ready_for_review")),
        "eligible_for_cutover": bool(promo.get("eligible_for_cutover")),
        "unresolved_safety_violations": int(summary.get("unresolved_safety_violations") or 0),
        "latest_status": summary.get("latest_status"),
        "latest_trade_date": summary.get("latest_trade_date"),
        "minimum_coverage_ratio": summary.get("minimum_coverage_ratio") or {},
        "blockers": promo.get("blockers") or [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs/v2/data")
    args = ap.parse_args()
    root = Path(args.root)
    mp = root / "current_manifest.json"
    m = load(mp)
    if not isinstance(m, dict):
        raise SystemExit("radar stats: manifest missing")
    active = str(m.get("active_build_id") or "")
    if not active:
        raise SystemExit("radar stats: active_build_id missing")
    build = root / "builds" / active
    build.mkdir(parents=True, exist_ok=True)

    obj = {
        "schema_version": "1.1.0",
        "build_id": active,
        "generated_at": m.get("generated_at"),
        "missions": {
            "close": mission_stats(root, m, "decision_close_index"),
            "intraday": mission_stats(root, m, "decision_intraday_index"),
            "daytrade": mission_stats(root, m, "decision_daytrade_index"),
        },
        "shadow": shadow_progress(root, m),
        "ranking_semantics": {
            "meaning": "attention_order",
            "not_probability": True,
            "close": "bucket>swing_quality>entry_position>confidence>code",
            "intraday": "bucket>intraday_momentum>confidence>code",
            "daytrade": "bucket>daytrade_score>confidence>code",
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
    print(json.dumps({"build": active, "missions": obj["missions"], "shadow": obj["shadow"], "bytes": meta["bytes"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
