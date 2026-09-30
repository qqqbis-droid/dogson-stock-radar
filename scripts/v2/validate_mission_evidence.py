#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, time, timezone, timedelta
from pathlib import Path

TW = timezone(timedelta(hours=8))
LIVE_START = time(9, 5)
LIVE_END = time(13, 31)
MAX_QUOTE_AGE_SEC = 8 * 60
MAX_STRUCTURE_AGE_SEC = 18 * 60

MISSION = {
    "close": {
        "decision": "decision_close_detail",
        "stock": "stock_detail_close",
        "zone": "zone_close",
        "market": "market_close_context",
        "capital": "capital_close_context",
        "source": "close.json",
    },
    "intraday": {
        "decision": "decision_intraday_detail",
        "stock": "stock_detail_intraday",
        "zone": "zone_intraday",
        "market": "market_intraday_context",
        "capital": "capital_intraday_context",
        "source": "intraday.json",
    },
    "daytrade": {
        "decision": "decision_daytrade_detail",
        "stock": "stock_detail_daytrade",
        "zone": "zone_daytrade",
        "market": "market_intraday_context",
        "capital": "capital_intraday_context",
        "source": "daytrade.json",
    },
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(root: Path, url: str) -> Path:
    raw = str(url or "")
    if raw.startswith("./data/"):
        return root / raw[len("./data/"):]
    return root / raw.lstrip("./")


def items(obj):
    if isinstance(obj, dict) and isinstance(obj.get("items"), dict):
        return obj["items"]
    if isinstance(obj, list):
        return {str(x.get("code") or i): x for i, x in enumerate(obj) if isinstance(x, dict)}
    return {}


def parse_dt(value):
    s = str(value or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TW)
        return dt.astimezone(TW)
    except Exception:
        return None


def first_time(*values):
    for value in values:
        dt = parse_dt(value)
        if dt:
            return dt
    return None


def zone_ids(zones):
    out = set()
    if isinstance(zones, list):
        for z in zones:
            if not isinstance(z, dict):
                continue
            zid = z.get("zone_id") or z.get("id")
            if zid:
                out.add(str(zid))
    return out


def dataset(root, manifest, key, active):
    meta = (manifest.get("datasets") or {}).get(key)
    if not meta:
        raise SystemExit(f"mission evidence gate: manifest missing {key}")
    if meta.get("build_id") and meta.get("build_id") != active:
        raise SystemExit(f"mission evidence gate: {key} meta build mismatch")
    path = resolve(root, meta.get("url"))
    if not path.is_file() or path.stat().st_size <= 0:
        raise SystemExit(f"mission evidence gate: {key} file missing/empty: {path}")
    obj = load(path)
    if isinstance(obj, dict) and obj.get("build_id") and obj.get("build_id") != active:
        raise SystemExit(f"mission evidence gate: {key} payload build mismatch")
    return meta, obj


def source_date(payload):
    if not isinstance(payload, dict):
        return ""
    for key in ("trade_date", "source_trade_date", "date"):
        s = str(payload.get(key) or "")[:10]
        if len(s) == 10:
            return s
    bridge = payload.get("bridge") or {}
    s = str(bridge.get("trade_date") or "")[:10]
    return s if len(s) == 10 else ""


def source_asof(payload):
    if not isinstance(payload, dict):
        return None
    bridge = payload.get("bridge") or {}
    q = payload.get("quote_layer") or {}
    return first_time(
        payload.get("as_of"),
        bridge.get("quote_snapshot_time"),
        bridge.get("latest_quote_time"),
        q.get("quote_snapshot_time"),
    )


def structure_asof(payload, market_obj=None):
    bridge = payload.get("bridge") or {} if isinstance(payload, dict) else {}
    metrics = (market_obj or {}).get("metrics") or {}
    return first_time(
        bridge.get("latest_structure_time"),
        payload.get("structure_time") if isinstance(payload, dict) else None,
        metrics.get("structure_latest_time"),
    )


def check_safety(mission, decisions, now, errors):
    live_clock = now.weekday() < 5 and LIVE_START <= now.time() <= LIVE_END
    for code, row in decisions.items():
        if not isinstance(row, dict):
            continue
        fresh = str(row.get("freshness") or "")
        phase = str(row.get("session_phase") or "")
        actionable = bool(row.get("actionable"))
        action = str(row.get("action_state") or "")
        if mission in {"intraday", "daytrade"}:
            if fresh != "LIVE" or phase != "LIVE":
                if actionable:
                    errors.append(f"{mission}:{code} actionable while {fresh}/{phase}")
                if mission == "daytrade" and action in {"SMALL_TEST", "ADD_ON_CONFIRM", "HOLD"}:
                    errors.append(f"daytrade:{code} executable action while not LIVE: {action}")
            elif not live_clock:
                # LIVE payload outside the exchange live window is semantically unsafe.
                errors.append(f"{mission}:{code} marked LIVE outside live clock")
        else:
            if fresh in {"STALE", "UNKNOWN"} and actionable:
                errors.append(f"close:{code} actionable while freshness={fresh}")


def validate_one(root: Path, legacy_root: Path, manifest: dict, mission: str):
    cfg = MISSION[mission]
    active = str(manifest.get("active_build_id") or "")
    if not active:
        raise SystemExit("mission evidence gate: active_build_id missing")

    metas = {}
    payloads = {}
    for key in (cfg["decision"], cfg["stock"], cfg["zone"], cfg["market"], cfg["capital"]):
        metas[key], payloads[key] = dataset(root, manifest, key, active)

    decisions = items(payloads[cfg["decision"]])
    stock = items(payloads[cfg["stock"]])
    zones = payloads[cfg["zone"]]
    if not decisions:
        raise SystemExit(f"mission evidence gate: {mission} decision detail empty")
    if not stock:
        raise SystemExit(f"mission evidence gate: {mission} stock detail empty")
    if not isinstance(zones, list) or not zones:
        raise SystemExit(f"mission evidence gate: {mission} zones empty")

    errors = []
    missing_stock = sorted(set(decisions) - set(stock))
    if missing_stock:
        errors.append(f"missing stock detail {missing_stock[:20]}")

    known_zone_ids = zone_ids(zones)
    missing_zone_refs = []
    for code, row in decisions.items():
        if not isinstance(row, dict):
            continue
        for field in ("support_zone_ids", "resistance_zone_ids"):
            refs = row.get(field) or []
            for ref in refs:
                if str(ref) not in known_zone_ids:
                    missing_zone_refs.append(f"{code}:{field}:{ref}")
    if missing_zone_refs:
        errors.append(f"unknown zone refs {missing_zone_refs[:20]}")

    now = datetime.now(TW)
    check_safety(mission, decisions, now, errors)

    source_path = legacy_root / cfg["source"]
    source = load(source_path) if source_path.is_file() else {}
    sdate = source_date(source)
    ddate = str(metas[cfg["decision"]].get("as_of") or "")[:10]
    if sdate and ddate and sdate != ddate:
        errors.append(f"source/date mismatch source={sdate} decision={ddate}")

    quote_age = None
    structure_age = None
    if mission in {"intraday", "daytrade"}:
        # daytrade shares the same live quote/structure context as intraday.
        intraday_source_path = legacy_root / "intraday.json"
        intraday_source = load(intraday_source_path) if intraday_source_path.is_file() else source
        qdt = source_asof(intraday_source)
        sdt = structure_asof(intraday_source, payloads[cfg["market"]])
        live_clock = now.weekday() < 5 and LIVE_START <= now.time() <= LIVE_END
        if qdt:
            quote_age = (now - qdt).total_seconds()
        if sdt:
            structure_age = (now - sdt).total_seconds()
        if live_clock:
            today = now.date().isoformat()
            if source_date(intraday_source) != today:
                errors.append(f"live source is not today: {source_date(intraday_source)}")
            if qdt is None or quote_age is None or quote_age > MAX_QUOTE_AGE_SEC:
                errors.append(f"live quote too old/missing: {quote_age}s")
            if sdt is None or structure_age is None or structure_age > MAX_STRUCTURE_AGE_SEC:
                errors.append(f"live structure too old/missing: {structure_age}s")

    report = {
        "mission": mission,
        "build": active,
        "decision_rows": len(decisions),
        "stock_detail_rows": len(stock),
        "zones": len(zones),
        "source_date": sdate,
        "decision_date": ddate,
        "quote_age_sec": round(quote_age, 1) if quote_age is not None else None,
        "structure_age_sec": round(structure_age, 1) if structure_age is not None else None,
        "ok": not errors,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False))
    if errors:
        raise SystemExit(f"mission evidence gate failed [{mission}]: " + " | ".join(errors[:12]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs/v2/data")
    ap.add_argument("--legacy-root", default="docs/data")
    ap.add_argument("--mission", choices=("close", "intraday", "daytrade", "all"), default="all")
    args = ap.parse_args()

    root = Path(args.root)
    legacy_root = Path(args.legacy_root)
    manifest = load(root / "current_manifest.json")
    missions = MISSION.keys() if args.mission == "all" else (args.mission,)
    for mission in missions:
        validate_one(root, legacy_root, manifest, mission)


if __name__ == "__main__":
    main()
