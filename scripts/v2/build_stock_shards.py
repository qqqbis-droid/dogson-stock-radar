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
    """Audit evidence without relabeling an older value as today's signal.

    'observed' is reserved for same-session source values, NOT a buy signal.
    Earlier valid values stay 'pending' with reason PRIOR_SESSION and a dated
    historical summary. Missing data, incomplete checks and unchecked exchange
    notices each have their own reason. Scoring inputs are never changed.
    """
    e = evidence if isinstance(evidence, dict) else {}
    trade_date = str(decision.get("trade_date") or "")[:10]
    evidence_day = str(evidence_date or "")[:10]
    rows = []

    def add(key, label, status, description, source_date="", reason="CURRENT"):
        assert status in {"observed", "pending", "warning"}
        rows.append({"key": key, "label": label, "status": status,
                     "detail": str(description), "source_date": str(source_date or "")[:10],
                     "reason": reason})

    def source_day(field):
        raw = str(e.get(field) or "")[:10]
        return raw if len(raw) == 10 and raw[4] == "-" and raw[7] == "-" else ""

    def provenance(source_date, has_value):
        if source_date == trade_date and has_value:
            return "CURRENT"
        if source_date and trade_date and source_date < trade_date and has_value:
            return "PRIOR_SESSION"
        if source_date and trade_date and source_date > trade_date:
            return "DATE_MISMATCH"
        return "MISSING"

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
    dates = {k: source_day(k + "_date") for k in ("foreign", "trust", "sbl", "margin")}
    dates_aligned = all(v == trade_date for v in dates.values())
    # CHECKED is the exact success state emitted by build_close_fresh.py.
    if health in {"OK", "HEALTHY", "PASS", "COMPLETE", "CHECKED"} and dates_aligned:
        add("chip_sources", "籌碼來源查核", "observed",
            "四類來源日期一致，來源查詢已完成；不代表零風險", trade_date)
    else:
        dates_text = "／".join(f"{name} {dates.get(key) or '無日期'}" for key, name in
                              (("foreign", "外資"), ("trust", "投信"), ("sbl", "借券"), ("margin", "融資")))
        if health == "PARTIAL":
            reason, detail = "PARTIAL_CHECK", f"來源部分完成（PARTIAL）；{dates_text}。有日期不代表查核全通過"
        elif any(v and v < trade_date for v in dates.values()) and all(not v or v <= trade_date for v in dates.values()):
            reason, detail = "PRIOR_SESSION", f"當日四類籌碼尚未全部到齊；最近來源：{dates_text}。只能作歷史參考"
        else:
            reason, detail = "SOURCE_UNVERIFIED", f"來源未完成查核或日期異常；{dates_text}"
        add("chip_sources", "籌碼來源查核", "pending", detail, max((v for v in dates.values() if v), default=""), reason)

    for key, title, datekey, netkey in (
        ("foreign", "外資買賣方向", "foreign_date", "foreign_net_latest"),
        ("trust", "投信買賣方向", "trust_date", "trust_net_latest"),
    ):
        source_date = source_day(datekey)
        value = number(e.get(netkey))
        reason = provenance(source_date, value is not None)
        direction = "淨買" if value is not None and value > 0 else "淨賣" if value is not None and value < 0 else "持平"
        if reason == "CURRENT":
            add(key, title, "observed", direction + "（原始單位未經確認，不推定主力動向）", source_date)
        elif reason == "PRIOR_SESSION":
            add(key, title, "pending", f"{source_date} 歷史資料為{direction}；不是 {trade_date} 的法人訊號",
                source_date, reason)
        else:
            add(key, title, "pending",
                "同日淨買賣數值尚未取得" if reason == "MISSING" else "來源日期晚於評分日，須核對",
                source_date, reason)

    source_date = source_day("sbl_date")
    sbl = e.get("sbl_3down")
    change = number(e.get("sbl_3change_pct"))
    reason = provenance(source_date, isinstance(sbl, bool))
    label = "連三日減少" if sbl is True else "未符合連三日減少條件"
    suffix = f"；三日變動 {change:+.2f}%" if change is not None else ""
    if reason == "CURRENT":
        add("sbl", "借券趨勢", "observed", label + suffix + "（不代表風險已排除）", source_date)
    elif reason == "PRIOR_SESSION":
        add("sbl", "借券趨勢", "pending",
            f"{source_date} 歷史趨勢：{label}{suffix}；不可當作 {trade_date} 訊號", source_date, reason)
    else:
        add("sbl", "借券趨勢", "pending", "同日借券趨勢尚未取得或日期待核對",
            source_date, reason)

    source_date = source_day("margin_date")
    margin = str(e.get("margin_status") or "").strip()
    reason = provenance(source_date, bool(margin))
    if reason == "CURRENT":
        add("margin", "融資狀態", "observed", "來源標記：" + margin + "（不等同風險排除）", source_date)
    elif reason == "PRIOR_SESSION":
        add("margin", "融資狀態", "pending",
            f"{source_date} 歷史融資狀態：{margin}；不作為 {trade_date} 訊號", source_date, reason)
    else:
        add("margin", "融資狀態", "pending", "同日融資狀態尚未取得或日期待核對",
            source_date, reason)

    h60 = e.get("hourly60")
    h60 = h60 if isinstance(h60, dict) else {}
    hday = str(h60.get("trade_date") or "")[:10]
    hstatus = str(h60.get("data_status") or "").upper()
    ready = hstatus in {"OK", "READY", "VALID"}
    hreason = provenance(hday, ready)
    light = str(h60.get("entry_light_label") or h60.get("entry_light") or "結構可用")
    ma20 = number(h60.get("ma20_60"))
    ma60 = number(h60.get("ma60_60"))
    levels = f"；20T {ma20:.2f}、60T {ma60:.2f}" if ma20 is not None and ma60 is not None else ""
    if market_aligned and hreason == "CURRENT":
        add("hourly60", "60分K結構", "observed", "模組訊號：" + light + levels + "（不是交易許可）", hday)
    elif hreason == "PRIOR_SESSION":
        add("hourly60", "60分K結構", "pending",
            f"{hday} 歷史60分K：{light}{levels}；不可當作 {trade_date} 進場燈號", hday, hreason)
    else:
        add("hourly60", "60分K結構", "pending",
            "尚無當日可用的60分K；來源未回傳或日期未核對，不推定均線交叉",
            hday, "SOURCE_UNVERIFIED" if hreason == "CURRENT" else hreason)

    px = number(e.get("close"))
    ma20 = number(e.get("ma20"))
    rsi = number(e.get("rsi"))
    if market_aligned and px is not None and ma20 is not None and ma20 > 0 and rsi is not None:
        add("technical", "日K技術狀態", "observed",
            f"收盤 {px:g}，20MA {ma20:.2f}，RSI {rsi:.1f}；僅為量價事實", evidence_day)
    else:
        reason = "DATE_MISMATCH" if evidence_day and evidence_day != trade_date else "MISSING"
        add("technical", "日K技術狀態", "pending",
            "同日收盤價、20MA 或 RSI 未齊，暫不完整對照", evidence_day, reason)

    overlays = set(str(x) for x in (decision.get("risk_overlays") or []))
    if "TRADING_RESTRICTION" in overlays:
        add("restriction", "交易限制", "warning", "原模型標記交易限制，仍須核對交易所公告",
            trade_date, "RESTRICTION_FLAG")
    else:
        add("restriction", "交易限制", "pending",
            "交易所處置／注意股公告尚未獨立核對；不是『確認無限制』",
            "", "NOTICE_UNVERIFIED")

    pending_reasons = {}
    for row in rows:
        if row["status"] == "pending":
            pending_reasons[row["reason"]] = pending_reasons.get(row["reason"], 0) + 1

    return {
        "version": "research-audit-v2-provenance",
        "trade_date": trade_date,
        "evidence_date": evidence_day,
        "source_status": health,
        "checks": rows,
        "observed_count": sum(x["status"] == "observed" for x in rows),
        "pending_count": sum(x["status"] == "pending" for x in rows),
        "warning_count": sum(x["status"] == "warning" for x in rows),
        "historical_count": pending_reasons.get("PRIOR_SESSION", 0),
        "pending_reasons": pending_reasons,
        "semantics": "當日觀測不等於買進；歷史參考不等於同日通過；缺漏及來源未核對不可視為安全；不變更評分",
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
