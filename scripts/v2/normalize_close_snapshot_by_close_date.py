#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
        subprocess.run([sys.executable, str(Path(__file__).with_name("normalize_close_snapshot.py")), "--root", str(root)], check=True)
        print("close-date wrapper", {"bundle_date": bundle_date, "close_date": close_date, "mode": "same-date"})
        return

    # The Atomic Bundle may already be on today's pre-open/intraday date while
    # close_next_day intentionally refers to the most recently completed cash
    # session.  The close normalizer keys its mutations by manifest.trade_date,
    # so temporarily bind that field to the close dataset's own date, run the
    # canonical normalizer, then restore only the bundle date.  Dataset hashes,
    # warnings and score explanations written by the normalizer are preserved.
    manifest["trade_date"] = close_date
    write(manifest_path, manifest)
    try:
        subprocess.run([sys.executable, str(Path(__file__).with_name("normalize_close_snapshot.py")), "--root", str(root)], check=True)
    finally:
        latest = load(manifest_path)
        latest["trade_date"] = bundle_date
        write(manifest_path, latest)
    print("close-date wrapper", {"bundle_date": bundle_date, "close_date": close_date, "mode": "temporary-close-bind"})


if __name__ == "__main__":
    main()
