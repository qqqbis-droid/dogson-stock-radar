#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify that V2 intraday/daytrade contexts match the source just published.

The production gate also proves Support/Resistance 2.0 is real data, not merely
UI capability: active zone datasets must contain genuine S2 and R2 records.
Reference-only daytrade decisions are intentionally allowed to publish without
zones, matching enrich_zones.py's DATA_STALE safety policy.
"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def resolve(root, url):
    raw = str(url or "")
    return root / (raw[len("./data/"):] if raw.startswith("./data/") else raw.lstrip("./"))


def run_py(path, *args):
    p = Path(path)
    if not p.is_file():
        raise SystemExit(f"required V2 validator missing after overlay: {p}")
    subprocess.run([sys.executable, str(p), *args], check=True)


def run_mission_gate(mission):
    run_py(
        "scripts/v2/validate_mission_evidence.py",
        "--root", "docs/v2/data",
        "--legacy-root", "docs/data",
        "--mission", mission,
    )


def verify_ranked_zones(root, manifest, key):
    p = resolve(root, manifest["datasets"][key]["url"])
    zones = load(p)
    if not isinstance(zones, list):
        raise SystemExit(f"{key} must be a list")
    ranks = Counter(str(z.get("rank") or "") for z in zones if isinstance(z, dict))
    print(key, "zone ranks", dict(ranks))
    # We deliberately do not require every stock to have S2/R2; a second level
    # is omitted when the engine cannot find an independent trustworthy cluster.
    # But an active production dataset with zero second levels means enrichment regressed.
    if ranks.get("S1", 0) == 0 or ranks.get("R1", 0) == 0:
        raise SystemExit(f"{key} missing primary S1/R1 zones: {dict(ranks)}")
    if ranks.get("S2", 0) < 10 or ranks.get("R2", 0) < 10:
        raise SystemExit(f"{key} S/R 2.0 regression; too few genuine S2/R2 zones: {dict(ranks)}")
    return ranks


def decision_rows(root, manifest, key):
    p = resolve(root, manifest["datasets"][key]["url"])
    payload = load(p)
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, dict):
            return [x for x in items.values() if isinstance(x, dict)]
        for name in ("rows", "data", "stocks", "results"):
            rows = payload.get(name)
            if isinstance(rows, list):
                return [x for x in rows if isinstance(x, dict)]
    return []


def main():
    src = load("docs/data/intraday.json")
    day = load("docs/data/daytrade.json")
    close = load("docs/data/close.json")
    root = Path("docs/v2/data")
    m = load(root / "current_manifest.json")
    src_date = str(src.get("trade_date") or "")[:10]
    day_date = str(day.get("trade_date") or day.get("source_trade_date") or "")[:10]
    close_date = str(close.get("trade_date") or "")[:10]
    intra = m["datasets"]["decision_intraday_summary"]
    daymeta = m["datasets"]["decision_daytrade_summary"]
    v2_i = str(intra.get("as_of") or "")[:10]
    v2_d = str(daymeta.get("as_of") or "")[:10]
    print("source intraday:", src_date, src.get("as_of"))
    print("source daytrade:", day_date, day.get("as_of"))
    print("source close:", close_date)
    print("V2 active:", m["active_build_id"])
    print("V2 phase/date:", m["session_phase"], m["trade_date"])
    print("V2 intraday as_of:", intra.get("as_of"))
    print("V2 daytrade as_of:", daymeta.get("as_of"))
    if not src_date or src_date != day_date:
        raise SystemExit("source intraday/daytrade dates disagree")
    if v2_i != src_date or v2_d != src_date:
        raise SystemExit(f"V2 source-date mismatch: source={src_date} intraday={v2_i} daytrade={v2_d}")
    if close_date and src_date < close_date:
        raise SystemExit(f"intraday {src_date} older than latest completed close {close_date}")
    required = (
        "market_intraday_context", "market_close_context", "capital_intraday_context", "capital_close_context",
        "zone_intraday", "zone_close", "zone_daytrade",
        "stock_detail_intraday", "stock_detail_close", "stock_detail_daytrade",
    )
    missing = [k for k in required if k not in m.get("datasets", {})]
    if missing:
        raise SystemExit(f"missing mission datasets: {missing}")
    for key in ("zone_intraday", "zone_close", "zone_daytrade", "stock_detail_intraday", "stock_detail_close", "stock_detail_daytrade"):
        p = resolve(root, m["datasets"][key]["url"])
        if not p.is_file() or p.stat().st_size == 0:
            raise SystemExit(f"{key} missing from active build: {p}")

    verify_ranked_zones(root, m, "zone_intraday")

    # enrich_zones.py intentionally strips zones from DATA_STALE daytrade rows so
    # post-close/reference-only data cannot look executable. Mirror that safety
    # contract here instead of demanding fabricated S/R zones after market close.
    day_decisions = decision_rows(root, m, "decision_daytrade_detail")
    day_reference_only = bool(day_decisions) and all(
        str(x.get("action_state") or "") == "DATA_STALE" for x in day_decisions
    )
    if day_reference_only:
        day_zones = load(resolve(root, m["datasets"]["zone_daytrade"]["url"]))
        if day_zones:
            raise SystemExit("reference-only daytrade must not publish executable zones")
        print("zone_daytrade skipped: all daytrade decisions are DATA_STALE/reference-only")
    else:
        verify_ranked_zones(root, m, "zone_daytrade")

    # Close is also checked here because the same deployment publishes the
    # cross-mission detail panel. It must not silently fall back to legacy-only.
    verify_ranked_zones(root, m, "zone_close")

    run_mission_gate("intraday")
    if day_reference_only:
        # validate_mission_evidence intentionally expects executable S/R evidence.
        # Running it against a reference-only daytrade mission would contradict
        # the DATA_STALE contract already proven above (all stale + zero zones).
        print("daytrade mission evidence gate skipped: reference-only DATA_STALE contract verified")
    else:
        run_mission_gate("daytrade")
    run_py("scripts/v2/validate_single_writer_ui.py")
    print("V2 stock detail/evidence + S1/S2/R1/R2 + single-writer UI verified")


if __name__ == "__main__":
    main()