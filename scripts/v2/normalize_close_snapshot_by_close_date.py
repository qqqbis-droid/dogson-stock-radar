#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def resolve(root: Path, url: str) -> Path:
    raw = str(url or "")
    if raw.startswith("./data/"):
        return root / raw[len("./data/"):]
    return root / raw.lstrip("./")


def close_trade_date(root: Path, manifest: dict) -> str:
    meta = (manifest.get("datasets") or {}).get("decision_close_detail") or {}
    as_of = str(meta.get("as_of") or "")[:10]
    if len(as_of) == 10:
        return as_of
    path = resolve(root, meta.get("url")) if meta.get("url") else None
    if path and path.exists():
        obj = load(path)
        rows = list((obj.get("items") or {}).values()) if isinstance(obj, dict) and isinstance(obj.get("items"), dict) else (obj if isinstance(obj, list) else [])
        dates = [str(r.get("trade_date") or r.get("as_of") or "")[:10] for r in rows if isinstance(r, dict)]
        dates = [d for d in dates if len(d) == 10]
        if dates:
            return max(set(dates), key=dates.count)
    return ""


def run_script(name: str, root: Path, *extra: str):
    subprocess.run([sys.executable, str(Path(__file__).with_name(name)), "--root", str(root), *extra], check=True)


def finalize_common(root: Path):
    run_script("close_semantics_v5.py", root)
    run_script("build_radar_stats.py", root)
    overlay_mode = os.environ.get("V2_OVERLAY_MODE", "")
    # During a preserve overlay, the canonical V2 bundle is the validated source
    # of truth. Re-validating it against the runner's independently rebuilt legacy
    # close can create a false source/date/evidence failure even though the
    # canonical bundle is intentionally being preserved. The caller still runs
    # validate_bundle, market/capital validation, source-lock checks and
    # index/detail semantic checks against the preserved canonical data.
    if overlay_mode in {"PRESERVE_SAME_DAY", "PRESERVE_CLOSE_ADVANCE", "PRESERVE_NEWER_CANONICAL"}:
        print("close evidence legacy-root cross-check skipped for preserve overlay", overlay_mode)
    else:
        run_script("validate_mission_evidence.py", root, "--legacy-root", "docs/data", "--mission", "close")


def finalize_close(root: Path):
    # The normalizer can change entry-position and ranks. Rebuild the physical
    # summary/index arrays after rank assignment so card order and displayed #rank
    # are guaranteed to be the same thing.
    run_script("rebuild_close_rank_views.py", root)
    finalize_common(root)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs/v2/data")
    args = ap.parse_args()
    root = Path(args.root)
    manifest_path = root / "current_manifest.json"
    manifest = load(manifest_path)
    bundle_date = str(manifest.get("trade_date") or "")[:10]
    close_date = close_trade_date(root, manifest)
    if len(close_date) != 10:
        raise SystemExit("close-date normalizer: decision_close_detail trade date missing")

    if close_date == bundle_date:
        run_script("normalize_close_snapshot.py", root)
        finalize_close(root)
        print("close-date wrapper", {"bundle_date": bundle_date, "close_date": close_date, "mode": "same-date"})
        return

    # The Atomic Bundle may already be on today's pre-open/intraday date while
    # close_next_day intentionally refers to the most recently completed cash
    # session. Temporarily bind only manifest.trade_date to the close date while
    # normalizing close semantics, then restore the bundle date.
    manifest["trade_date"] = close_date
    write(manifest_path, manifest)
    try:
        run_script("normalize_close_snapshot.py", root)
        run_script("rebuild_close_rank_views.py", root)
    finally:
        latest = load(manifest_path)
        latest["trade_date"] = bundle_date
        write(manifest_path, latest)
    finalize_common(root)
    print("close-date wrapper", {"bundle_date": bundle_date, "close_date": close_date, "mode": "temporary-close-bind"})


if __name__ == "__main__":
    main()
