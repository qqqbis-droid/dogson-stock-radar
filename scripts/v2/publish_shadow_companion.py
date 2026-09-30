#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    src = Path("shadow/summary.json")
    root = Path("docs/v2/data")
    manifest_path = root / "current_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("shadow companion: current_manifest.json missing")
    manifest = load(manifest_path)
    active = str(manifest.get("active_build_id") or "")
    if not active:
        raise SystemExit("shadow companion: active_build_id missing")

    if not src.is_file():
        payload = {
            "schema_version": "1.0.0",
            "build_id": active,
            "available": False,
            "distinct_trading_days": 0,
            "minimum_review_days": 20,
            "target_window_days": 40,
            "ready_for_review": False,
            "eligible_for_cutover": False,
            "note": "Shadow summary 尚未產生；排序僅代表注意力順序。",
        }
    else:
        s = load(src)
        promo = s.get("promotion") or {}
        days = int(s.get("distinct_trading_days") or 0)
        minimum = int(promo.get("minimum_review_days") or 20)
        target = int(promo.get("target_window_days") or 40)
        payload = {
            "schema_version": "1.0.0",
            "build_id": active,
            "available": True,
            "generated_at": s.get("generated_at"),
            "latest_trade_date": s.get("latest_trade_date"),
            "latest_status": s.get("latest_status"),
            "distinct_trading_days": days,
            "minimum_review_days": minimum,
            "target_window_days": target,
            "remaining_to_review": max(0, minimum - days),
            "ready_for_review": bool(promo.get("ready_for_review")),
            "eligible_for_cutover": bool(promo.get("eligible_for_cutover")),
            "unresolved_safety_violations": int(s.get("unresolved_safety_violations") or 0),
            "minimum_coverage_ratio": s.get("minimum_coverage_ratio") or {},
            "blockers": promo.get("blockers") or [],
            "note": "Shadow 樣本用來驗證排名與門檻；未達最低樣本前不得把名次解讀成上漲機率。",
        }

    out = root / "shadow-summary.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
