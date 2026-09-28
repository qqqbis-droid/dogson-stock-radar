#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "data"
FILES = ["market.json", "close.json", "intraday.json", "daytrade.json"]

def first_rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "items", "data", "stocks", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        # Some legacy bundles are dicts keyed by stock code.
        vals = list(payload.values())
        if vals and all(isinstance(v, dict) for v in vals):
            return vals
    return []

def main():
    for name in FILES:
        path = DATA / name
        print(f"\n=== {name} ===")
        if not path.exists():
            print("MISSING")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        print("top_type:", type(payload).__name__)
        if isinstance(payload, dict):
            print("top_keys:", sorted(payload.keys())[:80])
            for key in ("updated_at", "trade_date", "date", "data_complete", "version"):
                if key in payload:
                    print(f"meta.{key}:", payload.get(key))
        rows = first_rows(payload)
        print("row_count:", len(rows))
        if rows:
            row = rows[0]
            print("row_type:", type(row).__name__)
            if isinstance(row, dict):
                print("row_keys:", sorted(row.keys())[:160])
                safe = {k: row.get(k) for k in ("code","name","date","trade_date","updated_at","time","score","swing_quality_score","intraday_score","daytrade_score","entry_position_score","category","stage","sector_group","industry_name") if k in row}
                print("row_safe_sample:", safe)

if __name__ == "__main__":
    main()
