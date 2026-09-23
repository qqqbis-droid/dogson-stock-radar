#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.20 — reclassify existing radar JSON with Stage Engine 2.0.

Purpose:
- Do NOT redownload market data.
- Reuse current close.json / intraday.json rows.
- Re-run the current _assign_stage_v2() logic from scripts/build_data.py.
- Canonicalize lifecycle categories so every filter has real backing data.
- Bump UI/SW version only; no score weights or Stage thresholds are changed.
"""
from __future__ import annotations

import ast
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
BUILD = ROOT / "scripts" / "build_data.py"
TW = timezone(timedelta(hours=8))

STAGES = [
    "蓄勢待發", "剛啟動", "回踩承接", "趨勢持有",
    "觀察", "轉弱警戒", "結構失效", "過熱不追",
]


def load_stage_fn():
    src = BUILD.read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_assign_stage_v2"),
        None,
    )
    if fn is None:
        raise SystemExit("_assign_stage_v2 not found in scripts/build_data.py")
    module = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(module)
    ns: dict[str, object] = {}
    exec(compile(module, str(BUILD), "exec"), ns, ns)
    return ns["_assign_stage_v2"]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj):
    path.write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def reclassify(path: Path, intraday: bool, assign_stage):
    obj = read_json(path)
    rows = obj.get("rows") or []
    before = Counter(str(r.get("category") or "觀察") for r in rows)
    for r in rows:
        sec = r.get("sector_score")
        try:
            sec = float(sec) if sec is not None else 0.0
        except Exception:
            sec = 0.0
        assign_stage(r, intraday, sec)
    after = Counter(str(r.get("category") or "觀察") for r in rows)
    obj["stage_version"] = "2.0"
    obj["stage_reclassified_at"] = datetime.now(TW).isoformat(timespec="seconds")
    write_json(path, obj)
    return len(rows), before, after


def patch_ui():
    index = ROOT / "docs" / "index.html"
    s = index.read_text(encoding="utf-8")
    if "Free Edition v1.5.19" not in s:
        raise SystemExit("v1.5.20 expected v1.5.19 index header")
    s = s.replace("Free Edition v1.5.19", "Free Edition v1.5.20", 1)
    s = s.replace("./sw.js?v=1519", "./sw.js?v=1520")
    s = s.replace("dogsonSwReloaded1519", "dogsonSwReloaded1520")
    index.write_text(s, encoding="utf-8")

    sw = ROOT / "docs" / "sw.js"
    w = sw.read_text(encoding="utf-8")
    if "dogson-free-v1519" not in w:
        raise SystemExit("v1.5.20 expected v1519 service worker cache")
    w = w.replace("dogson-free-v1519", "dogson-free-v1520", 1)
    sw.write_text(w, encoding="utf-8")


def update_status(close_count: int, intra_count: int, close_dist, intra_dist):
    path = DATA / "status.json"
    obj = read_json(path)
    obj["version"] = "1.5.20-free"
    obj["stage_version"] = "2.0"
    obj["stage_updated_at"] = datetime.now(TW).isoformat(timespec="seconds")
    obj["stage_close_count"] = close_count
    obj["stage_intraday_count"] = intra_count
    obj["stage_close_distribution"] = dict(close_dist)
    obj["stage_intraday_distribution"] = dict(intra_dist)
    write_json(path, obj)


def verify_close(dist: Counter, total: int):
    missing = [s for s in STAGES if dist.get(s, 0) <= 0]
    if missing:
        raise SystemExit(f"close lifecycle stages unexpectedly empty: {missing}; dist={dict(dist)}")
    if sum(dist.values()) != total:
        raise SystemExit("close lifecycle count mismatch")


def main():
    assign_stage = load_stage_fn()
    close_n, close_before, close_after = reclassify(DATA / "close.json", False, assign_stage)
    intra_n, intra_before, intra_after = reclassify(DATA / "intraday.json", True, assign_stage)

    verify_close(close_after, close_n)
    if sum(intra_after.values()) != intra_n:
        raise SystemExit("intraday lifecycle count mismatch")

    update_status(close_n, intra_n, close_after, intra_after)
    patch_ui()

    print("CLOSE BEFORE", dict(close_before))
    print("CLOSE AFTER ", dict(close_after))
    print("INTRA BEFORE", dict(intra_before))
    print("INTRA AFTER ", dict(intra_after))
    print("v1.5.20 lifecycle data reclassification OK")


if __name__ == "__main__":
    main()
