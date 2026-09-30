#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify that V2 intraday/daytrade contexts match the source just published."""
import json
import subprocess
import sys
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

    run_mission_gate("intraday")
    run_mission_gate("daytrade")
    run_py("scripts/v2/validate_single_writer_ui.py")
    print("V2 stock detail/evidence + single-writer UI verified")


if __name__ == "__main__":
    main()
