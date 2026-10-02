#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Copy chip source dates/check provenance from the latest close rows to live missions.

The close build is the only workflow that actually queries EOD chip sources.
Intraday/daytrade may reuse that latest published chip background, but they must
not invent a newer check time.  This script copies only provenance/date fields,
not scores or trading signals.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"

FIELDS = (
    "chip_date",
    "foreign_date",
    "trust_date",
    "dealer_date",
    "sbl_date",
    "margin_date",
    "chip_checked_at",
    "chip_check_health",
    "chip_check_latest_attempt_date",
)


def load(name: str):
    p = DATA / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save(name: str, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    close = load("close.json") or {}
    close_rows = [r for r in (close.get("rows") or []) if isinstance(r, dict) and r.get("code")]
    by_code = {str(r.get("code")): r for r in close_rows}
    if not by_code:
        print("chip provenance sync skipped: close rows missing")
        return

    for name in ("intraday.json", "daytrade.json"):
        obj = load(name)
        if not isinstance(obj, dict):
            continue
        touched = 0
        for row in obj.get("rows") or []:
            if not isinstance(row, dict):
                continue
            src = by_code.get(str(row.get("code") or ""))
            if not src:
                continue
            changed = False
            for key in FIELDS:
                if key in src and src.get(key) is not None and row.get(key) != src.get(key):
                    row[key] = src.get(key)
                    changed = True
            touched += int(changed)
        obj["chip_provenance"] = close.get("chip_provenance") or obj.get("chip_provenance")
        save(name, obj)
        print("chip provenance sync", name, "rows=", touched)


if __name__ == "__main__":
    main()
