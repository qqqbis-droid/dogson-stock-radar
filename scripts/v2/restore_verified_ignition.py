#!/usr/bin/env python3
"""Restore only genuine same-session Ignition 2.0 scores into the V2 bundle.

A UI deploy may preserve a same-day V2 market bundle assembled from an earlier
partial close, even though the authoritative root close has the complete six-
part ignition scores. Never infer these scores from swing quality or price.

No transaction, portfolio, quote, zone, or non-ignition field is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))
from scripts.v2.legacy_adapter import ignition_execution

PARTS = ("structure", "volume_acceleration", "sector_resonance",
         "relative_acceleration", "chip_acceleration", "tradability_risk")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload):
    raw = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return {"hash": "sha256:" + hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def resolve(root: Path, meta):
    path = str(meta.get("url") or "")
    return root / (path[len("./data/"):] if path.startswith("./data/") else path.lstrip("./"))


def number(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def valid_source(r, date):
    if str(r.get("date") or r.get("trade_date") or "")[:10] != date:
        return False
    if r.get("ignition_model_version") != "inuko-ignition-v2.0":
        return False
    total, raw, cap, confidence = (number(r.get(k)) for k in (
        "ignition_score_v2", "ignition_raw_score_v2",
        "ignition_gate_cap_v2", "ignition_confidence_v2"))
    if any(x is None for x in (total, raw, cap, confidence)):
        return False
    if not (0 <= total <= 100 and 0 <= raw <= 100 and 0 <= cap <= 100 and 0 <= confidence <= 100):
        return False
    comp = r.get("ignition_components_v2")
    if not isinstance(comp, dict) or any(not isinstance(comp.get(k), dict) for k in PARTS):
        return False
    values = [number(comp[k].get("score")) for k in PARTS]
    maxima = [number(comp[k].get("max")) for k in PARTS]
    if any(v is None for v in values + maxima):
        return False
    if abs(sum(values) - raw) > 0.31 or abs(sum(maxima) - 100) > 0.01:
        return False
    if total > raw + 0.11 or total > cap + 0.11:
        return False
    if not r.get("ignition_stage_v2"):
        return False
    return True


def patch_row(row, raw):
    # Do not touch any existing non-ignition score, position, quote or action.
    scores = row.setdefault("scores", {})
    scores["ignition_score"] = number(raw["ignition_score_v2"])
    fields = {
        "ignition_model_version": "ignition_model_version",
        "ignition_raw_score": "ignition_raw_score_v2",
        "ignition_confidence": "ignition_confidence_v2",
        "ignition_stage": "ignition_stage_v2",
        "ignition_verdict": "ignition_verdict_v2",
        "ignition_summary": "ignition_summary_v2",
        "ignition_reasons": "ignition_reasons_v2",
        "ignition_gate_cap": "ignition_gate_cap_v2",
        "ignition_gate_flags": "ignition_gate_flags_v2",
        "ignition_breakout_distance_pct": "ignition_breakout_distance_pct_v2",
        "ignition_breakout_distance_atr": "ignition_breakout_distance_atr_v2",
        "ignition_candidate": "ignition_candidate_v2",
    }
    for field, source in fields.items():
        value = raw.get(source)
        if isinstance(value, (list, dict)):
            value = json.loads(json.dumps(value))
        row[field] = value
    row["ignition_signal_action"] = raw.get("ignition_signal_action_v2") or raw.get("ignition_action_v2")
    ex = ignition_execution(
        row["ignition_stage"], row["ignition_signal_action"], scores["ignition_score"],
        scores.get("entry_position_score"), row["ignition_gate_cap"])
    row["ignition_action"] = ex["action"]
    row["ignition_execution_state"] = ex["state"]
    row["ignition_execution_ready"] = bool(ex["ready"])
    row["ignition_execution_note"] = ex["note"]


def run(root: Path, legacy: Path):
    manifest_path = root / "current_manifest.json"
    m = read(manifest_path)
    date = str(m.get("trade_date") or "")[:10]
    active = str(m.get("active_build_id") or "")
    source = read(legacy)
    rows = source.get("rows") or []
    source_dates = {str(r.get("date") or r.get("trade_date") or "")[:10] for r in rows}
    if not rows or not date or source_dates != {date}:
        raise SystemExit(f"Ignition restore: root close must be complete single session {date}, got {source_dates}")
    raw = {str(r["code"]): r for r in rows if valid_source(r, date) and r.get("code")}
    if len(raw) < max(10, int(len(rows) * 0.75)):
        raise SystemExit(f"Ignition source incomplete: validated {len(raw)}/{len(rows)} for {date}; refusing guessed scores")
    datasets = m["datasets"]
    detail_key = "decision_close_detail"
    detail_path = resolve(root, datasets[detail_key])
    detail = read(detail_path)
    items = detail.get("items") or {}
    if not isinstance(items, dict) or not items:
        raise SystemExit("Ignition restore: decision detail map missing")
    if detail.get("build_id") not in (None, active):
        raise SystemExit("Ignition restore: V2 detail build mismatch")
    updated = []
    for code, row in items.items():
        src = raw.get(str(code))
        # Ignore genuine out-of-universe stocks; do not show them as scored.
        if not src or str(row.get("trade_date") or "")[:10] != date:
            continue
        official = number(src.get("close") or src.get("current_price") or src.get("price"))
        canonical = number((row.get("quote") or {}).get("price"))
        if official is None or canonical is None or abs(official-canonical) > max(0.051, official*.001):
            continue
        patch_row(row, src)
        updated.append(str(code))
    if len(updated) < max(10, int(len(items)*0.60)):
        raise SystemExit(f"Ignition restore: only {len(updated)}/{len(items)} matching validated prices; refusing incomplete publish")

    scored = [r for r in items.values() if r.get("ignition_model_version")=="inuko-ignition-v2.0"
              and number((r.get("scores") or {}).get("ignition_score")) is not None
              and str(r.get("trade_date") or "")[:10]==date]
    scored.sort(key=lambda r: (-number(r["scores"]["ignition_score"]),
                               -(number(r.get("ignition_confidence")) or 0), str(r.get("code") or "")))
    for rank, row in enumerate(scored, 1):
        row["ignition_rank"] = rank
    for row in items.values():
        if row not in scored:
            row["ignition_rank"] = None
    # Keep the existing opportunity ranking and insertion order; ignition is a separate view.
    datasets[detail_key].update(write(detail_path, detail))
    for key in ("decision_close_index", "decision_close_summary"):
        target = resolve(root, datasets[key])
        data = read(target)
        if not isinstance(data, list):
            raise SystemExit(f"Ignition restore: {key} must be an array")
        for row in data:
            src = items.get(str(row.get("code") or ""))
            if not src:
                continue
            for field in ("scores", "ignition_model_version", "ignition_raw_score", "ignition_confidence",
                          "ignition_stage", "ignition_verdict", "ignition_summary", "ignition_reasons",
                          "ignition_gate_cap", "ignition_gate_flags", "ignition_breakout_distance_pct",
                          "ignition_breakout_distance_atr", "ignition_candidate", "ignition_signal_action",
                          "ignition_action", "ignition_execution_state", "ignition_execution_ready",
                          "ignition_execution_note", "ignition_rank"):
                if field=="scores":
                    row.setdefault("scores", {})["ignition_score"] = src["scores"].get("ignition_score")
                else:
                    row[field] = src.get(field)
        datasets[key].update(write(target, data))
    m.setdefault("health", {}).setdefault("warnings", []).append(
        f"Ignition 2.0: {len(updated)} current-session decisions restored from validated six-part root close")
    write(manifest_path, m)
    print(json.dumps({"status":"PASS","session":date,"build":active,"source_valid":len(raw),
                      "decisions_restored":len(updated),"ignition_ranked":len(scored)},
                     ensure_ascii=False))
    return len(updated)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="docs/v2/data")
    p.add_argument("--legacy-close", default="docs/data/close.json")
    a = p.parse_args()
    run(Path(a.root), Path(a.legacy_close))
