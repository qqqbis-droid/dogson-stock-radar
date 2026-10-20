#!/usr/bin/env python3
"""Build mobile-safe per-stock detail shards from the canonical V2 Atomic bundle.

This is a publish-time transform only: the canonical whole-market datasets remain
unchanged. Each shard contains exactly one stock's decision, referenced zones,
and evidence so mobile clients never need to parse multi-megabyte market JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VIEW_CONFIG = {
    "intraday": ("decision_intraday_detail", "zone_intraday", "stock_detail_intraday"),
    "close": ("decision_close_detail", "zone_close", "stock_detail_close"),
    "daytrade": ("decision_daytrade_detail", "zone_daytrade", "stock_detail_daytrade"),
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_path(data_root: Path, meta: dict[str, Any]) -> Path:
    raw = str(meta.get("url") or "")
    if raw.startswith("./data/"):
        rel = raw[len("./data/") :]
    elif raw.startswith("data/"):
        rel = raw[len("data/") :]
    else:
        rel = raw.lstrip("./")
    if not rel:
        raise ValueError("dataset url is empty")
    return data_root / rel


def keyed_items(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        items = obj.get("items", obj)
        if isinstance(items, dict):
            return {str(k): v for k, v in items.items()}
        if isinstance(items, list):
            out: dict[str, Any] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                code = item.get("code") or item.get("stock_code") or item.get("symbol")
                if code is not None:
                    out[str(code)] = item
            return out
    if isinstance(obj, list):
        out = {}
        for item in obj:
            if not isinstance(item, dict):
                continue
            code = item.get("code") or item.get("stock_code") or item.get("symbol")
            if code is not None:
                out[str(code)] = item
        return out
    return {}


def zone_items(obj: Any) -> list[dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in ("items", "zones"):
            value = obj.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
            if isinstance(value, dict):
                return [x for x in value.values() if isinstance(x, dict)]
    return []


def code_of_zone(zone: dict[str, Any]) -> str:
    for key in ("code", "stock_code", "symbol", "ticker"):
        value = zone.get(key)
        if value is not None:
            return str(value)
    return ""


def context_of_zone(zone: dict[str, Any]) -> str:
    for key in ("decision_context_id", "context_id"):
        value = zone.get(key)
        if value:
            return str(value)
    zone_id = str(zone.get("zone_id") or "")
    if ":SUPPORT:" in zone_id:
        return zone_id.split(":SUPPORT:", 1)[0]
    if ":RESISTANCE:" in zone_id:
        return zone_id.split(":RESISTANCE:", 1)[0]
    return ""


def selected_zones(
    decision: dict[str, Any],
    code: str,
    zones: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    wanted: list[str] = []
    for key in ("support_zone_ids", "resistance_zone_ids"):
        values = decision.get(key) or []
        if isinstance(values, (list, tuple)):
            wanted.extend(str(x) for x in values if x is not None)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(zone: dict[str, Any], fallback: str = "") -> None:
        dedupe = str(zone.get("zone_id") or fallback or id(zone))
        if dedupe not in seen:
            seen.add(dedupe)
            out.append(zone)

    # Primary path: explicit decision -> zone ids.
    for zone_id in wanted:
        zone = by_id.get(zone_id)
        if zone is not None:
            add(zone, zone_id)

    # Defensive path 1: context id. Older/preserved Atomic bundles can retain the
    # zones while losing the copied support_zone_ids/resistance_zone_ids fields.
    context_ids = {
        str(x)
        for x in (decision.get("decision_context_id"), decision.get("context_id"))
        if x
    }
    if not out or len(out) < len(set(wanted)):
        for zone in zones:
            if context_ids and context_of_zone(zone) in context_ids:
                add(zone)

    # Defensive path 2: stock code. Zone 3.0 stores code explicitly so a
    # UI-only bundle-preservation step can never turn a valid price map blank.
    if not out or len(out) < len(set(wanted)):
        for zone in zones:
            if code_of_zone(zone) == code:
                add(zone)

    # Never mix another stock's zones into this shard.
    filtered = []
    for zone in out:
        zcode = code_of_zone(zone)
        if zcode and zcode != code:
            continue
        filtered.append(zone)
    return filtered



def research_checks(decision: dict[str, Any], evidence: Any, evidence_date: Any) -> dict[str, Any]:
    """Publish evidence-specific audit, not new trade verdicts or fake risk flags.

    Status observed means a data point was observed (possibly adverse), NOT a
    pass. Unknown/missing inputs are explicitly pending; no blank-list safety claims.
    """
    e = evidence if isinstance(evidence, dict) else {}
    trade_date = str(decision.get("trade_date") or "")[:10]
    evidence_day = str(evidence_date or "")[:10]
    rows = []

    def add(key, label, status, description, source_date=""):
        assert status in {"observed", "pending", "warning"}
        rows.append({"key": key, "label": label, "status": status,
                     "detail": str(description), "source_date": str(source_date or "")[:10]})

    def checked_date(field):
        value = str(e.get(field) or "")[:10]
        return bool(trade_date and value == trade_date), value

    def number(value):
        try:
            if isinstance(value, bool) or value is None or value == "":
                return None
            x = float(value)
            return x if x == x and abs(x) != float("inf") else None
        except (ValueError, TypeError):
            return None

    market_aligned = bool(trade_date and evidence_day == trade_date)
    health = str(e.get("chip_check_health") or "UNKNOWN").upper()
    dates_aligned = all(checked_date(k)[0] for k in
                        ("foreign_date", "trust_date", "sbl_date", "margin_date"))
    if health in {"OK", "HEALTHY", "PASS", "COMPLETE"} and dates_aligned:
        add("chip_sources", "籌碼來源查核", "observed", "資料日期一致，來源健康狀態通過", trade_date)
    elif health == "PARTIAL":
        add("chip_sources", "籌碼來源查核", "pending",
            "PARTIAL：資料日期可一致，但來源查核仍有未完成部分；須再核對原始來源", trade_date)
    else:
        add("chip_sources", "籌碼來源查核", "pending",
            "來源狀態未知、未完成或資料日期不一致；不可視為全面通過", trade_date)

    for key, title, datekey, netkey in (
        ("foreign", "外資買賣方向", "foreign_date", "foreign_net_latest"),
        ("trust", "投信買賣方向", "trust_date", "trust_net_latest"),
    ):
        good, source_date = checked_date(datekey)
        v = number(e.get(netkey))
        if good and v is not None:
            direction = "淨買" if v > 0 else "淨賣" if v < 0 else "持平"
            add(key, title, "observed", direction+"（未標示金額或張數單位；不推定主力動向）", source_date)
        else:
            add(key, title, "pending", "缺少同日有效法人淨買賣數據", source_date)

    good, source_date = checked_date("sbl_date")
    sbl = e.get("sbl_3down")
    sbl_change = number(e.get("sbl_3change_pct"))
    if good and isinstance(sbl, bool):
        direction = "連三日減少" if sbl else "未符合連三日減少條件"
        detail = direction + (f"；三日變動 {sbl_change:+.2f}%" if sbl_change is not None else "")
        add("sbl", "借券趨勢", "observed", detail, source_date)
    else:
        add("sbl", "借券趨勢", "pending", "借券三日趨勢或日期未提供", source_date)

    good, source_date = checked_date("margin_date")
    margin = str(e.get("margin_status") or "").strip()
    if good and margin:
        add("margin", "融資狀態", "observed", "來源標記："+margin+"（不等同風險排除）", source_date)
    else:
        add("margin", "融資狀態", "pending", "缺少同日融資狀態標記", source_date)

    h60 = e.get("hourly60")
    h60 = h60 if isinstance(h60, dict) else {}
    hday = str(h60.get("trade_date") or "")[:10]
    hstatus = str(h60.get("data_status") or "").upper()
    if market_aligned and hday == trade_date and hstatus in {"OK", "READY", "VALID"}:
        light = str(h60.get("entry_light_label") or h60.get("entry_light") or "資料可用")
        add("hourly60", "60分K結構", "observed",
            "模組訊號："+light+"（不能當作交易許可）", hday)
    else:
        add("hourly60", "60分K結構", "pending",
            "尚無同交易日可用的60分K輸出；不能推定均線交叉或進場燈號", hday)

    px = number(e.get("close"))
    ma20 = number(e.get("ma20"))
    rsi = number(e.get("rsi"))
    if market_aligned and px is not None and ma20 is not None and ma20 > 0 and rsi is not None:
        add("technical", "日K技術狀態", "observed",
            f"收盤 {px:g}，20MA {ma20:.2f}，RSI {rsi:.1f}；僅為量價事實",
            evidence_day)
    else:
        add("technical", "日K技術狀態", "pending",
            "缺少同日收盤價、20MA 或 RSI，無法完整對照", evidence_day)

    overlays = set(str(x) for x in (decision.get("risk_overlays") or []))
    if "TRADING_RESTRICTION" in overlays:
        add("restriction", "交易限制", "warning", "既有模型標記交易限制；需核對交易所公告", trade_date)
    else:
        add("restriction", "交易限制", "pending",
            "現有個股快照未包含可獨立核對的處置／注意股公告；不能判定沒有交易限制", trade_date)

    return {
        "version": "research-audit-v1",
        "trade_date": trade_date,
        "evidence_date": evidence_day,
        "source_status": health,
        "checks": rows,
        "observed_count": sum(x["status"] == "observed" for x in rows),
        "pending_count": sum(x["status"] == "pending" for x in rows),
        "warning_count": sum(x["status"] == "warning" for x in rows),
        "semantics": "觀測不等於通過；待補不等於安全；本清單不修改交易決策或分數",
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="docs/v2/data")
    parser.add_argument("--max-shard-bytes", type=int, default=512_000)
    args = parser.parse_args()

    data_root = Path(args.data_root)
    manifest_path = data_root / "current_manifest.json"
    manifest = read_json(manifest_path)
    build_id = str(manifest.get("active_build_id") or "")
    if not build_id:
        raise SystemExit("active_build_id missing")
    datasets = manifest.get("datasets") or {}
    build_dir = data_root / "builds" / build_id
    if not build_dir.is_dir():
        raise SystemExit(f"active build directory missing: {build_dir}")

    shard_root = build_dir / "stock-shards"
    if shard_root.exists():
        import shutil
        shutil.rmtree(shard_root)
    shard_root.mkdir(parents=True, exist_ok=True)

    stats: dict[str, Any] = {"build_id": build_id, "views": {}}
    total_files = 0
    total_bytes = 0

    for view, (detail_key, zone_key, evidence_key) in VIEW_CONFIG.items():
        metas = [datasets.get(detail_key), datasets.get(zone_key), datasets.get(evidence_key)]
        if any(not isinstance(meta, dict) for meta in metas):
            if view == "daytrade":
                stats["views"][view] = {"files": 0, "bytes": 0, "skipped": True}
                continue
            raise SystemExit(f"missing required shard source for {view}")

        detail_meta, zone_meta, evidence_meta = metas  # type: ignore[misc]
        detail_obj = read_json(dataset_path(data_root, detail_meta))
        zone_obj = read_json(dataset_path(data_root, zone_meta))
        evidence_obj = read_json(dataset_path(data_root, evidence_meta))

        if isinstance(detail_obj, dict) and detail_obj.get("build_id") not in (None, build_id):
            raise SystemExit(f"{detail_key} build mismatch")
        if isinstance(evidence_obj, dict) and evidence_obj.get("build_id") not in (None, build_id):
            raise SystemExit(f"{evidence_key} build mismatch")

        decisions = keyed_items(detail_obj)
        evidence = keyed_items(evidence_obj)
        zones = zone_items(zone_obj)
        by_id = {str(z.get("zone_id")): z for z in zones if z.get("zone_id") is not None}

        view_dir = shard_root / view
        view_dir.mkdir(parents=True, exist_ok=True)
        view_files = 0
        view_bytes = 0
        shards_with_zones = 0

        for code, decision in decisions.items():
            if not isinstance(decision, dict):
                continue
            if decision.get("build_id") not in (None, build_id):
                raise SystemExit(f"decision build mismatch: {view} {code}")
            picked = selected_zones(decision, code, zones, by_id)
            if picked:
                shards_with_zones += 1
            payload = {
                "schema_version": "1.1.0",
                "build_id": build_id,
                "view": view,
                "code": code,
                "as_of": decision.get("as_of") or detail_meta.get("as_of"),
                "known_at": decision.get("known_at") or detail_meta.get("known_at"),
                "decision": decision,
                "zones": picked,
                "evidence": evidence.get(code),
            }
            if view == "close":
                payload["research_checks"] = research_checks(decision, evidence.get(code), evidence_obj.get("trade_date"))
            encoded = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            if len(encoded) > args.max_shard_bytes:
                raise SystemExit(f"shard too large: {view}/{code}.json {len(encoded)} bytes")
            path = view_dir / f"{code}.json"
            path.write_bytes(encoded)
            view_files += 1
            view_bytes += len(encoded)

        stats["views"][view] = {
            "files": view_files,
            "bytes": view_bytes,
            "skipped": False,
            "shards_with_zones": shards_with_zones,
        }
        if view == "close" and view_files and not shards_with_zones:
            raise SystemExit("close shards lost every support/resistance zone")
        total_files += view_files
        total_bytes += view_bytes

    stats["total_files"] = total_files
    stats["total_bytes"] = total_bytes
    (shard_root / "index.json").write_text(
        json.dumps(stats, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    if total_files == 0:
        raise SystemExit("no stock shards generated")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
