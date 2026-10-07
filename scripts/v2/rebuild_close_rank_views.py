#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
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


def num(v, default=-1.0):
    try:
        x = float(v)
        return x if x == x else default
    except Exception:
        return default


BUCKET_ORDER = {
    "NEXT_DAY_READY": 0,
    "BREAKOUT_WATCH": 1,
    "PULLBACK_WATCH": 2,
    "TREND_QUALITY": 3,
    "RESEARCH": 4,
    "RISK": 5,
}


def sort_key(d):
    scores = d.get("scores") or {}
    return (
        BUCKET_ORDER.get(d.get("opportunity_bucket"), 99),
        -num(scores.get("swing_quality_score")),
        -num(scores.get("entry_position_score")),
        -num(d.get("data_confidence"), 0),
        str(d.get("code") or ""),
    )


def lightweight(d):
    # Everything required to render/search a radar card without downloading the
    # multi-megabyte detail/evidence payload.
    keys = (
        "code", "name", "market", "primary_group", "decision_context_id", "build_id",
        "trade_date", "session_phase", "as_of", "freshness", "lifecycle_stage",
        "action_state", "actionable", "opportunity_bucket", "opportunity_rank",
        "scores", "why_now", "blockers", "upgrade_conditions", "risk_flags",
        "risk_overlays", "data_confidence", "component_coverage", "missing_fields", "quote",
        "ignition_model_version", "ignition_raw_score", "ignition_confidence", "ignition_stage",
        "ignition_signal_action", "ignition_action", "ignition_execution_state", "ignition_execution_ready",
        "ignition_execution_note", "ignition_verdict", "ignition_summary", "ignition_reasons",
        "ignition_gate_cap", "ignition_gate_flags", "ignition_breakout_distance_pct",
        "ignition_breakout_distance_atr", "ignition_candidate", "ignition_rank",
    )
    return {k: d.get(k) for k in keys if k in d}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs/v2/data")
    args = ap.parse_args()

    root = Path(args.root)
    manifest_path = root / "current_manifest.json"
    manifest = load(manifest_path)
    ds = manifest.get("datasets") or {}
    active = str(manifest.get("active_build_id") or "")
    for key in ("decision_close_detail", "decision_close_index", "decision_close_summary"):
        if key not in ds:
            raise SystemExit(f"close rank rebuild: manifest missing {key}")

    detail_path = resolve(root, ds["decision_close_detail"].get("url"))
    detail = load(detail_path)
    items = detail.get("items") if isinstance(detail, dict) else None
    if not isinstance(items, dict) or not items:
        raise SystemExit("close rank rebuild: decision_close_detail items missing")

    rows = [x for x in items.values() if isinstance(x, dict)]
    rows.sort(key=sort_key)
    for rank, row in enumerate(rows, 1):
        row["opportunity_rank"] = rank

    # Keep detail-map insertion order aligned too. It is not required for lookup,
    # but it makes audits deterministic and prevents future consumers from seeing
    # a different order than the explicit rank.
    detail["items"] = {str(row.get("code")): row for row in rows}
    dmeta = write(detail_path, detail)
    ds["decision_close_detail"].update(dmeta)

    index = [lightweight(row) for row in rows]
    index_path = resolve(root, ds["decision_close_index"].get("url"))
    imeta = write(index_path, index)
    ds["decision_close_index"].update(imeta)

    summary = rows[:15]
    summary_path = resolve(root, ds["decision_close_summary"].get("url"))
    smeta = write(summary_path, summary)
    ds["decision_close_summary"].update(smeta)

    # Hard assertions: the physical arrays must now match their displayed ranks.
    if [r.get("opportunity_rank") for r in index[:25]] != list(range(1, min(25, len(index)) + 1)):
        raise SystemExit("close rank rebuild: index physical order does not match opportunity_rank")
    if [r.get("code") for r in summary] != [r.get("code") for r in rows[:15]]:
        raise SystemExit("close rank rebuild: summary is not top-15 of full ranking")

    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    msg = "Close Ranking：候選層級 → 波段品質 → 進場位置 → 資料信心 → 代號；summary/index 實體順序與 opportunity_rank 強制一致。"
    if msg not in warnings:
        warnings.append(msg)
    write(manifest_path, manifest)
    print(json.dumps({
        "build": active,
        "rows": len(rows),
        "top15": [r.get("code") for r in rows[:15]],
        "ranking": "bucket>swing_quality>entry_position>confidence>code",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
