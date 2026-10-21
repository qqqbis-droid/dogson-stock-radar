#!/usr/bin/env python3
"""Synthetic contract tests for reproducible stock/sector money-flow reconciliation."""
import json
import tempfile
from pathlib import Path
from build_capital_stock_breakdown import build

DATE = "2026-10-08"
ID = "test-close-stock-breakdown"
STOCKS = [
    ("2337", "旺宏", 116, -15690993, 17000),
    ("2344", "華邦電", 177, -14220689, -250134),
    ("2408", "南亞科", 532, 21773270, 192527),
    ("3006", "晶豪科", 267, -2411473, 1000),
    ("5351", "鈺創", 115, -1516753, 12000),
    ("6531", "愛普*", 980, -1245974, 41000),
]


def put(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / "data"
    bdir = root / "builds" / ID
    registry = Path(tmp) / "registry.json"
    put(registry, {"groups": [{"group": "記憶體IC", "members": [r[0] for r in STOCKS] + ["9999"]}], "stock_overrides": {"2344": {"primary_group":"OTHER_AUDIT"}}})
    put(bdir / "stock.json", {
        "build_id": ID, "items": {
            code: {"code": code, "name": name, "sector_group": "記憶體IC", "close": price,
                   "foreign_date": DATE, "trust_date": DATE,
                   "foreign_net_latest": foreign, "trust_net_latest": trust,
                   "volume": 120000000, "current_turnover": 120000000 * price}
            for code, name, price, foreign, trust in STOCKS
        },
    })
    source = {"build_id": ID, "trade_date": DATE, "rows": [
        {"primary_group": "記憶體IC", "latest_date": DATE, "today_amount_100m": 53.0877, "today_lots": -13299.2}
    ]}
    put(bdir / "capital.json", source)
    put(root / "current_manifest.json", {
        "schema_version": "2.0.0", "active_build_id": ID,
        "datasets": {
            "decision_close_summary": {"as_of": DATE + "T13:30:00+08:00"},
            "stock_detail_close": {"url": f"./data/builds/{ID}/stock.json", "as_of": DATE + "T13:30:00+08:00"},
            "capital_close_context": {"url": f"./data/builds/{ID}/capital.json",
                                      "as_of": DATE + "T13:30:00+08:00",
                                      "known_at": DATE + "T16:00:00+08:00"},
        },
    })
    build(root, registry)
    result = json.loads((bdir / "capital-close-members.json").read_text(encoding="utf-8"))
    memory = result["groups"]["記憶體IC"]
    assert memory["member_count"] == 6, "registry symbols outside Atomic universe must not inflate denominator"
    assert "2344" in [x["code"] for x in memory["stocks"]], "Audit registry override cannot move source stock to another flow group"
    assert memory["reconciled"], memory
    assert memory["rank_eligible"] and memory["rank_status"] == "RECONCILED"
    assert memory["rank_trade_date"] == DATE
    assert abs(memory["rank_amount_100m"] - 53.0877) < .012
    assert memory["sample_eligible"] and memory["sample_trade_date"] == DATE
    assert memory["sample_coverage_pct"] == 100
    assert abs(memory["sample_amount_100m"] - 53.0877) < .012
    assert (memory["buy_count"], memory["sell_count"], memory["verified_count"]) == (1, 5, 6)
    assert memory["amount_lots_diverge"] is True
    assert memory["verdict"] == "CONCENTRATED_INFLOW"
    assert memory["largest_positive_code"] == "2408"
    assert abs(memory["largest_positive_100m"] - 116.8580) < .01
    assert abs(memory["delta_amount_100m"]) < .001
    assert abs(memory["delta_lots"]) < .05
    # Malformed aggregate must never be called broad/verified.
    source["rows"][0]["today_amount_100m"] = 53.9
    put(bdir / "capital.json", source)
    build(root, registry)
    bad = json.loads((bdir / "capital-close-members.json").read_text(encoding="utf-8"))["groups"]["記憶體IC"]
    assert not bad["reconciled"] and bad["verdict"] == "UNVERIFIED"
    # Legacy same-day aggregate may be from a mismatched snapshot. The full
    # set of official same-day per-stock rows remains independently usable,
    # but never mark it as a reconciled aggregate.
    assert bad["verified_count"] == bad["member_count"] == 6
    assert bad["rank_eligible"] is True
    assert bad["rank_status"] == "RECALCULATED_SOURCE_DISAGREEMENT"
    assert bad["reconciled"] is False and bad["legacy_aggregate_differs"]
    assert bad["rank_evidence_source"] == "COMPLETE_SAME_DAY_STOCK_ROWS"
    assert abs(bad["rank_amount_100m"] - 53.0877) < .012
    assert abs(bad["delta_amount_100m"]) > .01
    assert bad["rank_amount_100m"] != source["rows"][0]["today_amount_100m"]
    source["rows"][0]["today_amount_100m"] = 53.0877
    put(bdir / "capital.json", source)
    stock = json.loads((bdir / "stock.json").read_text(encoding="utf-8"))
    stock["items"]["5351"]["foreign_date"] = "2026-10-07"
    put(bdir / "stock.json", stock)
    build(root, registry)
    stale = json.loads((bdir / "capital-close-members.json").read_text(encoding="utf-8"))["groups"]["記憶體IC"]
    assert not stale["reconciled"] and stale["verdict"] == "UNVERIFIED"
    assert stale["sample_eligible"], "Partial dated stock subset should remain useful"
    assert stale["sample_coverage_pct"] > 60 and stale["sample_trade_date"] == DATE
    assert stale["sample_amount_100m"] is not None
    assert stale["verified_count"] == 5
    assert stale["missing_count"] == 1 and stale["interval_available"] is True
    assert stale["interval_lower_100m"] is not None
    assert stale["interval_upper_100m"] is not None
    assert stale["interval_lower_100m"] < stale["sample_amount_100m"] < stale["interval_upper_100m"]
    assert stale["rank_eligible"] is False and stale["rank_status"] == "INCOMPLETE"
    assert stale["rank_amount_100m"] is None

    # Unknown/mismatched daily volume must suppress numeric intervals.
    stock["items"]["5351"]["volume"] = None
    put(bdir / "stock.json", stock)
    build(root, registry)
    unchecked = json.loads((bdir / "capital-close-members.json").read_text(encoding="utf-8"))["groups"]["記憶體IC"]
    assert unchecked["interval_available"] is False and unchecked["interval_lower_100m"] is None
    stock["items"]["5351"]["volume"] = 120000000

    # An older aggregate does not veto a complete SAME-DAY set of stock flows.
    stock["items"]["5351"]["foreign_date"] = DATE
    put(bdir / "stock.json", stock)
    source["rows"][0]["latest_date"] = "2026-10-07"
    source["rows"][0]["today_amount_100m"] = 999.0
    put(bdir / "capital.json", source)
    build(root, registry)
    rebuilt = json.loads((bdir / "capital-close-members.json").read_text(encoding="utf-8"))["groups"]["記憶體IC"]
    assert not rebuilt["reconciled"]
    assert rebuilt["rank_eligible"] and rebuilt["rank_status"] == "REBUILT_ALL_MEMBERS"
    assert rebuilt["rank_full_member_coverage"]
    assert abs(rebuilt["rank_amount_100m"] - 53.0877) < .012
    assert rebuilt["aggregate_source_date"] == "2026-10-07"
    # Old 999億 must never enter a new ranked result.
    assert rebuilt["rank_amount_100m"] != source["rows"][0]["today_amount_100m"]
print("PASS per-stock capital breadth, signed monetary weighting and fail-closed reconciliation")
