#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Publish small non-canonical V2 companion files after an Atomic Build."""
import json
from collections import defaultdict
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rows_of(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for k in ("rows", "items", "data", "stocks", "results"):
            if isinstance(x.get(k), list):
                return x[k]
    return []


def date_of(x, rows):
    dates = []
    if isinstance(x, dict):
        for k in ("trade_date", "date"):
            v = x.get(k)
            if isinstance(v, str) and len(v) >= 10:
                dates.append(v[:10])
    for r in rows:
        v = str(r.get("quote_date") or r.get("market_trade_date") or r.get("date") or "")[:10]
        if len(v) == 10:
            dates.append(v)
    return max(dates) if dates else None


def group_of(r):
    return str(r.get("sector_group") or r.get("industry_name") or r.get("industry") or "未分類").strip() or "未分類"


def member_map(payload):
    rows = rows_of(payload)
    groups = defaultdict(list)
    seen = defaultdict(set)
    for r in rows:
        code = str(r.get("code") or "").strip()
        if not code:
            continue
        g = group_of(r)
        if code in seen[g]:
            continue
        seen[g].add(code)
        groups[g].append({"code": code, "name": str(r.get("name") or "").strip()})
    for g in groups:
        groups[g].sort(key=lambda x: x["code"])
    return {"trade_date": date_of(payload, rows), "groups": dict(groups)}


def main():
    root = Path("docs/v2/data")
    manifest = load(root / "current_manifest.json")
    market = load("docs/data/market.json")
    close = load("docs/data/close.json")
    intraday = load("docs/data/intraday.json")
    (root / "market-detail.json").write_text(
        json.dumps({
            "schema_version": "1.0.0",
            "build_id": manifest["active_build_id"],
            "trade_date": market.get("trade_date"),
            "payload": market,
        }, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    members = {
        "schema_version": "1.0.0",
        "build_id": manifest["active_build_id"],
        "close": member_map(close),
        "intraday": member_map(intraday),
    }
    (root / "sector-members.json").write_text(
        json.dumps(members, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print("V2 companions:", manifest["active_build_id"], manifest["trade_date"], manifest["session_phase"], members["intraday"]["trade_date"])


if __name__ == "__main__":
    main()
