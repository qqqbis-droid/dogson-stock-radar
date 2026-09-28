#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import shutil
import tempfile
from datetime import datetime, timezone, timedelta

from scripts.v2.build_legacy_bundle import build as build_legacy_bundle

TW = timezone(timedelta(hours=8))
ROOT = pathlib.Path(__file__).resolve().parents[2]


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: pathlib.Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def legacy_count(path: pathlib.Path) -> int:
    payload = load(path)
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("rows", "items", "data", "stocks", "results"):
            if isinstance(payload.get(key), list):
                return len(payload[key])
    return 0


def dist(rows, key):
    return dict(sorted(collections.Counter(str(r.get(key) or "NULL") for r in rows).items()))


def safety_audit(datasets):
    violations = []
    for mission, rows in datasets.items():
        for row in rows:
            code = row.get("code")
            freshness = row.get("freshness")
            stage = row.get("lifecycle_stage")
            if freshness in {"FROZEN", "STALE", "UNKNOWN"} and row.get("actionable"):
                violations.append({"mission": mission, "code": code, "rule": "nonlive_actionable", "freshness": freshness})
            if stage == "FAILED" and row.get("actionable"):
                violations.append({"mission": mission, "code": code, "rule": "failed_actionable"})
            if row.get("action_state") == "DATA_STALE" and row.get("actionable"):
                violations.append({"mission": mission, "code": code, "rule": "data_stale_actionable"})
    return violations


def build_report(*, manifest, legacy_root, new_root, previous_build_id):
    active = manifest["active_build_id"]
    build_dir = new_root / "builds" / active
    close_rows = load(build_dir / "decision-close-index.json")
    intraday_rows = load(build_dir / "decision-intraday-index.json")
    daytrade_rows = load(build_dir / "decision-daytrade-index.json")
    datasets = {"close": close_rows, "intraday": intraday_rows, "daytrade": daytrade_rows}

    source_counts = {
        "close": legacy_count(legacy_root / "close.json"),
        "intraday": legacy_count(legacy_root / "intraday.json"),
        "daytrade": legacy_count(legacy_root / "daytrade.json"),
    }
    canonical_counts = {key: len(rows) for key, rows in datasets.items()}
    coverage = {
        key: round(canonical_counts[key] / source_counts[key], 4) if source_counts[key] else None
        for key in source_counts
    }
    violations = safety_audit(datasets)
    warnings = []
    for key, ratio in coverage.items():
        if ratio is not None and ratio < 0.98:
            warnings.append(f"{key} canonical coverage {ratio:.1%}")
    health = load(build_dir / "health.json")
    if len(health.get("source_dates") or []) > 1:
        warnings.append("source trade dates are not identical; contexts remain separated")

    status = "FAIL" if violations or any((ratio is not None and ratio < 0.90) for ratio in coverage.values()) else ("WARN" if warnings else "PASS")
    return {
        "shadow_schema_version": "1.0.0",
        "captured_at": datetime.now(TW).isoformat(timespec="seconds"),
        "trade_date": manifest.get("trade_date"),
        "build_id": active,
        "previous_build_id": previous_build_id,
        "status": status,
        "source_dates": health.get("source_dates") or [],
        "source_counts": source_counts,
        "canonical_counts": canonical_counts,
        "coverage_ratio": coverage,
        "safety_violations": violations,
        "warnings": warnings,
        "distributions": {
            key: {
                "lifecycle_stage": dist(rows, "lifecycle_stage"),
                "action_state": dist(rows, "action_state"),
                "opportunity_bucket": dist(rows, "opportunity_bucket"),
                "freshness": dist(rows, "freshness"),
            }
            for key, rows in datasets.items()
        },
        "promotion": {
            "eligible": False,
            "reason": "Phase 5 requires 20–40 distinct trading-day Shadow reports and no unresolved P0/P1 divergence."
        }
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy-root", default=str(ROOT / "docs" / "data"))
    ap.add_argument("--output", default=str(ROOT / "docs" / "v2" / "data"))
    ap.add_argument("--reports", default=str(ROOT / "shadow" / "reports"))
    args = ap.parse_args()

    legacy_root = pathlib.Path(args.legacy_root)
    output_root = pathlib.Path(args.output)
    reports_root = pathlib.Path(args.reports)
    previous_manifest_path = output_root / "current_manifest.json"
    previous_manifest = load(previous_manifest_path) if previous_manifest_path.exists() else None
    previous_build_id = previous_manifest.get("active_build_id") if previous_manifest else None

    with tempfile.TemporaryDirectory(prefix="dogson-v2-shadow-") as td:
        temp_root = pathlib.Path(td) / "data"
        manifest = build_legacy_bundle(legacy_root, temp_root)
        active = manifest["active_build_id"]
        report = build_report(
            manifest=manifest,
            legacy_root=legacy_root,
            new_root=temp_root,
            previous_build_id=previous_build_id,
        )
        if report["status"] == "FAIL":
            print(json.dumps(report, ensure_ascii=False, indent=2))
            raise SystemExit("Shadow safety gate failed; current_manifest was not changed")

        report_name = f"{manifest['trade_date']}-{active}.json"
        report_path = reports_root / report_name
        if active == previous_build_id and report_path.exists():
            print("No new source build; existing canonical bundle retained:", active)
            return

        output_root.mkdir(parents=True, exist_ok=True)
        target_build = output_root / "builds" / active
        if target_build.exists():
            shutil.rmtree(target_build)
        shutil.copytree(temp_root / "builds" / active, target_build)

        if previous_build_id and previous_build_id != active:
            manifest["previous_good_build_id"] = previous_build_id
        elif previous_manifest:
            manifest["previous_good_build_id"] = previous_manifest.get("previous_good_build_id")

        # current_manifest is written last. In Git/Vercel the whole commit/deployment is atomic;
        # keeping the previous build directory enables explicit last-known-good fallback.
        write(output_root / "current_manifest.json", manifest)
        write(report_path, report)
        write(reports_root.parent / "latest.json", report)

        # Keep active + previous good + one additional recent directory to bound repo growth.
        keep = {active, manifest.get("previous_good_build_id")}
        build_dirs = sorted((output_root / "builds").glob("cb2-*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in build_dirs[:3]:
            keep.add(p.name)
        for p in build_dirs:
            if p.name not in keep:
                shutil.rmtree(p)

        print("Shadow cycle", report["status"], manifest["trade_date"], active)


if __name__ == "__main__":
    main()
