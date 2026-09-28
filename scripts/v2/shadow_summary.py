#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
MISSIONS = ("intraday", "close", "daytrade")
VIEWS = ("intraday", "close", "portfolio", "daytrade")


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: pathlib.Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def report_files(reports_root: pathlib.Path):
    return sorted(p for p in reports_root.glob("*.json") if p.is_file())


def choose_distinct_trading_days(reports):
    """Keep the newest captured report for each trade date.

    Phase 5 promotion counts distinct trading days, not repeated builds/runs from
    the same date. Reports without a trade_date are deliberately ignored.
    """
    chosen = {}
    for report in reports:
        trade_date = report.get("trade_date")
        if not trade_date:
            continue
        current = chosen.get(trade_date)
        if current is None or str(report.get("captured_at") or "") >= str(current.get("captured_at") or ""):
            chosen[trade_date] = report
    return [chosen[d] for d in sorted(chosen)]


def _min_coverage(reports):
    out = {}
    for mission in MISSIONS:
        values = []
        for report in reports:
            value = (report.get("coverage_ratio") or {}).get(mission)
            if isinstance(value, (int, float)):
                values.append(float(value))
        out[mission] = round(min(values), 4) if values else None
    return out


def _payload_summary(reports):
    latest = reports[-1] if reports else None
    latest_views = ((latest or {}).get("payload_profile") or {}).get("views") or {}
    max_initial = {view: None for view in VIEWS}
    for view in VIEWS:
        values = []
        for report in reports:
            item = (((report.get("payload_profile") or {}).get("views") or {}).get(view) or {})
            value = item.get("initial_bytes")
            if isinstance(value, int):
                values.append(value)
        max_initial[view] = max(values) if values else None
    return {
        "latest_initial_bytes": {
            view: (latest_views.get(view) or {}).get("initial_bytes") for view in VIEWS
        },
        "max_initial_bytes": max_initial,
        "note": "Static transfer-size observability only; browser interaction SLO remains a separate measured gate.",
    }


def build_summary(reports):
    distinct = choose_distinct_trading_days(reports)
    status_counts = Counter(str(r.get("status") or "UNKNOWN") for r in distinct)
    safety_count = sum(len(r.get("safety_violations") or []) for r in distinct)
    days = len(distinct)
    blockers = []
    if days < 20:
        blockers.append(f"Need {20 - days} more distinct trading-day Shadow samples to reach the minimum review window.")
    if status_counts.get("FAIL", 0):
        blockers.append(f"{status_counts['FAIL']} distinct trading-day report(s) are FAIL.")
    if safety_count:
        blockers.append(f"{safety_count} unresolved fail-closed safety violation(s) are present in selected daily reports.")
    blockers.append("Predictive threshold validation evidence and rollback verification remain separate Phase 5/6 gates.")

    latest = distinct[-1] if distinct else None
    ready_for_review = days >= 20 and status_counts.get("FAIL", 0) == 0 and safety_count == 0
    return {
        "shadow_summary_schema_version": "1.0.0",
        "generated_at": (latest or {}).get("captured_at"),
        "total_report_files": len(reports),
        "distinct_trading_days": days,
        "first_trade_date": distinct[0].get("trade_date") if distinct else None,
        "latest_trade_date": (latest or {}).get("trade_date"),
        "latest_build_id": (latest or {}).get("build_id"),
        "latest_status": (latest or {}).get("status"),
        "daily_status_counts": dict(sorted(status_counts.items())),
        "unresolved_safety_violations": safety_count,
        "minimum_coverage_ratio": _min_coverage(distinct),
        "payload": _payload_summary(distinct),
        "promotion": {
            "minimum_review_days": 20,
            "target_window_days": 40,
            "ready_for_review": ready_for_review,
            "eligible_for_cutover": False,
            "blockers": blockers,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", default=str(ROOT / "shadow" / "reports"))
    ap.add_argument("--output", default=str(ROOT / "shadow" / "summary.json"))
    args = ap.parse_args()

    reports_root = pathlib.Path(args.reports)
    reports = []
    for path in report_files(reports_root):
        try:
            reports.append(load(path))
        except (json.JSONDecodeError, OSError) as exc:
            raise SystemExit(f"Invalid Shadow report {path}: {exc}") from exc

    summary = build_summary(reports)
    write(pathlib.Path(args.output), summary)
    print(
        "Shadow summary",
        summary["distinct_trading_days"],
        "distinct trading day(s); ready_for_review=",
        summary["promotion"]["ready_for_review"],
    )


if __name__ == "__main__":
    main()
