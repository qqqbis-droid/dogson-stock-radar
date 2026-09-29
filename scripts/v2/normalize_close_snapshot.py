#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v2.engine import bucket_for, synthesize_action


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    raw = text.encode("utf-8")
    return {
        "hash": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def resolve(root: Path, url: str) -> Path:
    raw = str(url or "")
    if raw.startswith("./data/"):
        return root / raw[len("./data/"):]
    return root / raw.lstrip("./")


def records(obj):
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict) and isinstance(obj.get("items"), dict):
        return [x for x in obj["items"].values() if isinstance(x, dict)]
    return [obj] if isinstance(obj, dict) else []


def same_trade_date(row: dict, canonical_date: str) -> bool:
    td = str(row.get("trade_date") or row.get("as_of") or "")[:10]
    return bool(canonical_date and td == canonical_date)


def normalize_decision(row: dict, canonical_date: str) -> bool:
    if not same_trade_date(row, canonical_date):
        return False
    changed = False
    if row.get("session_phase") != "POST_CLOSE":
        row["session_phase"] = "POST_CLOSE"
        changed = True
    if row.get("freshness") != "FRESH":
        row["freshness"] = "FRESH"
        changed = True

    overlays = [x for x in (row.get("risk_overlays") or []) if x != "DATA_QUALITY_RISK"]
    if overlays != list(row.get("risk_overlays") or []):
        row["risk_overlays"] = overlays
        changed = True

    blockers = [
        x for x in (row.get("blockers") or [])
        if str(x) not in {"資料不是目前可執行快照", "資料新鮮度不足"}
    ]
    if blockers != list(row.get("blockers") or []):
        row["blockers"] = blockers
        changed = True

    entry = (row.get("scores") or {}).get("entry_position_score")
    action, actionable = synthesize_action(
        row.get("lifecycle_stage"),
        overlays,
        "FRESH",
        entry_score=entry,
        has_position=False,
    )
    if row.get("action_state") != action:
        row["action_state"] = action
        changed = True
    if row.get("actionable") != bool(actionable):
        row["actionable"] = bool(actionable)
        changed = True
    no_chase = action == "DO_NOT_CHASE"
    if row.get("no_chase") != no_chase:
        row["no_chase"] = no_chase
        changed = True

    bucket = bucket_for(
        "close_next_day",
        row.get("lifecycle_stage"),
        action,
        "FRESH",
        bool(actionable),
        False,
    )
    if row.get("opportunity_bucket") != bucket:
        row["opportunity_bucket"] = bucket
        changed = True
    return changed


def normalize_generic_close(row: dict, canonical_date: str) -> bool:
    if not same_trade_date(row, canonical_date):
        return False
    changed = False
    if row.get("session_phase") != "POST_CLOSE":
        row["session_phase"] = "POST_CLOSE"
        changed = True
    if row.get("freshness") != "FRESH":
        row["freshness"] = "FRESH"
        changed = True
    flags = list(row.get("risk_flags") or [])
    cleaned = [x for x in flags if "歷史市場快照" not in str(x)]
    if cleaned != flags:
        row["risk_flags"] = cleaned
        changed = True
    return changed


def normalize_dataset(root: Path, manifest: dict, key: str, canonical_date: str, *, decision=False) -> int:
    meta = (manifest.get("datasets") or {}).get(key)
    if not meta:
        return 0
    path = resolve(root, meta.get("url"))
    if not path.exists():
        raise SystemExit(f"close snapshot normalizer: missing dataset {key}: {path}")
    obj = load(path)
    changed_count = 0
    for row in records(obj):
        changed = normalize_decision(row, canonical_date) if decision else normalize_generic_close(row, canonical_date)
        if changed:
            changed_count += 1
    if changed_count:
        meta.update(write(path, obj))
    return changed_count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs/v2/data")
    args = ap.parse_args()

    root = Path(args.root)
    manifest_path = root / "current_manifest.json"
    manifest = load(manifest_path)
    canonical_date = str(manifest.get("trade_date") or "")[:10]
    if len(canonical_date) != 10:
        raise SystemExit("close snapshot normalizer: manifest trade_date missing")

    counts = {}
    for key in ("decision_close_summary", "decision_close_index", "decision_close_detail"):
        counts[key] = normalize_dataset(root, manifest, key, canonical_date, decision=True)
    for key in ("sector_close", "market_summary", "market_close_context", "capital_close_context"):
        counts[key] = normalize_dataset(root, manifest, key, canonical_date, decision=False)

    warning = "Close Snapshot Policy：最近完成交易日跨午夜仍視為盤後可規劃快照，不因日曆換日自動標記 DATA_STALE。"
    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    if warning not in warnings:
        warnings.append(warning)
    write(manifest_path, manifest)

    changed = sum(counts.values())
    print("normalized latest completed close snapshot", {"trade_date": canonical_date, "changed": changed, "datasets": counts})


if __name__ == "__main__":
    main()
