#!/usr/bin/env python3
"""Build compact, auditable per-stock TWSE/TPEx close capital breakdown.

This dataset is strictly derived from SAME close Atomic bundle's per-stock
foreign/trust net shares and official closing price. It never guesses missing
institutional flows, never changes existing sector ranking or engine scores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def number(x):
    try:
        if x is None or x == "":
            return None
        v = float(x)
        return v if abs(v) != float("inf") and v == v else None
    except (ValueError, TypeError, OverflowError):
        return None


def resolve(root, url):
    v = str(url or "")
    return root / (v[7:] if v.startswith("./data/") else v.lstrip("./"))


def registry_groups(path):
    data = load(path)
    out = {}
    for group in data.get("groups", []):
        name = str(group.get("group") or "").strip()
        for code in group.get("members") or []:
            code = str(code)
            if code in out and out[code] != name:
                raise SystemExit(f"duplicate primary sector {code}: {out[code]} vs {name}")
            out[code] = name
    for code, rec in (data.get("stock_overrides") or {}).items():
        group = str((rec or {}).get("primary_group") or "").strip()
        if group:
            out[str(code)] = group
    return out


def keyed(obj):
    if isinstance(obj, dict) and isinstance(obj.get("items"), dict):
        return obj["items"]
    if isinstance(obj, dict) and isinstance(obj.get("items"), list):
        return {str(v.get("code")): v for v in obj["items"] if isinstance(v, dict) and v.get("code")}
    raise SystemExit("stock_detail_close is not a keyed item collection")


def build(root, registry):
    mf = root / "current_manifest.json"
    m = load(mf)
    datasets = m.get("datasets") or {}
    build_id = str(m.get("active_build_id") or "")
    if not build_id or m.get("schema_version") != "2.0.0":
        raise SystemExit("invalid V2 Atomic manifest")
    required = ("capital_close_context", "stock_detail_close", "decision_close_summary")
    if any(k not in datasets for k in required):
        raise SystemExit("capital detail source dataset missing")
    close_date = str(datasets["decision_close_summary"].get("as_of") or "")[:10]
    context = load(resolve(root, datasets["capital_close_context"]["url"]))
    source = load(resolve(root, datasets["stock_detail_close"]["url"]))
    if not close_date or context.get("build_id") != build_id or source.get("build_id") != build_id:
        raise SystemExit("capital detail source build/date mismatch")
    if str(context.get("trade_date") or "")[:10] != close_date or str(datasets["stock_detail_close"].get("as_of") or "")[:10] != close_date:
        raise SystemExit("capital detail/stock close price dates inconsistent")
    members = registry_groups(registry)
    groups = {str(x["primary_group"]): x for x in context.get("rows") or [] if x.get("primary_group")}
    if not groups:
        raise SystemExit("capital_close_context has no groups")

    # Scope must be the SAME source universe as the close-sector aggregates.
    # A registry may contain many symbols outside the tracked Atomic bundle;
    # counting those as missing per-stock evidence makes every group fail forever.
    tracked = keyed(source)
    membership = {key: set() for key in groups}
    records = {}
    for code, e in tracked.items():
        if not isinstance(e, dict):
            continue
        code = str(code)
        # The upstream group aggregates were built from the SAME stock row's
        # sector_group (fallback to industry_name). Never override that with
        # a different taxonomy registry: that made two valid sums disagree.
        sector = str(e.get("sector_group") or "").strip()
        industry = str(e.get("industry_name") or "").strip()
        group = sector or (industry if industry and industry != "未分類" else "")
        if not group and members.get(code) in groups:
            group = members[code]
        if group not in groups:
            continue
        membership[group].add(code)
        date_foreign = str(e.get("foreign_date") or "")[:10]
        date_trust = str(e.get("trust_date") or "")[:10]
        f, t, close = number(e.get("foreign_net_latest")), number(e.get("trust_net_latest")), number(e.get("close"))
        valid = f is not None and t is not None and close is not None and close > 0 and date_foreign == close_date and date_trust == close_date
        lots = (f + t) / 1000 if valid else None
        amt = (f + t) * close / 1e8 if valid else None
        volume = number(e.get("volume"))
        turnover = number(e.get("current_turnover"))
        # volume is daily traded SHARES in the V1 market engine; validate its
        # magnitude against observed turnover before estimating missing impact.
        # This remains an approximation, NOT a guaranteed official bound.
        volume_usable = bool(volume is not None and volume > 0 and
            turnover is not None and turnover > 0 and close is not None and close > 0
            and 0.60 <= (turnover / (volume * close)) <= 1.70)
        records[code] = {
            "code": code,
            "name": str(e.get("name") or code),
            "foreign_lots": round(f / 1000, 3) if f is not None and date_foreign == close_date else None,
            "trust_lots": round(t / 1000, 3) if t is not None and date_trust == close_date else None,
            "net_lots": round(lots, 4) if lots is not None else None,
            "close_price": close,
            "estimated_amount_100m": round(amt, 8) if amt is not None else None,
            "foreign_date": date_foreign or None,
            "trust_date": date_trust or None,
            "valid": valid,
            "volume_shares": volume if volume_usable else None,
            "missing_flow_impact_100m": round(volume * close * 1.30 / 1e8, 8)
                if (not valid and volume_usable) else None,
            "volume_proxy_validated": volume_usable,
        }

    # Unlisted/untracked registry symbols are NOT included in the 756-stock
    # denominator; the UI explicitly discloses this tracking-universe scope.
    out = {}
    mismatch_count = 0
    valid_count = 0
    for group, x in groups.items():
        rows = [records[c] for c in sorted(membership[group]) if c in records]
        rows.sort(key=lambda a: (a["estimated_amount_100m"] is None, -abs(a["estimated_amount_100m"] or 0), a["code"]))
        good = [r for r in rows if r["valid"]]
        count, bought, sold = len(rows), sum(r["net_lots"] > 0 for r in good), sum(r["net_lots"] < 0 for r in good)
        neutral = len(good) - bought - sold
        missing = [r for r in rows if not r["valid"]]
        sum_amount = sum(r["estimated_amount_100m"] for r in good)
        sum_lots = sum(r["net_lots"] for r in good)
        # Same-day audited subset: never claim it is the full sector net.
        sample_ratio = len(good) / count * 100 if count else None
        sample_eligible = bool(len(good) >= 3 and sample_ratio is not None and sample_ratio >= 60)
        # A nonverified sector is never assigned a precise rank. When EVERY
        # missing stock has valid daily volume+turnover, expose a deliberately
        # wide +/-130% turnover-value impact interval, for direction analysis.
        # No volume or unit plausibility: no numeric interval, never fake 0.
        missing_bound_ok = bool(missing and all(
            r.get("missing_flow_impact_100m") is not None for r in missing))
        missing_impact = sum(r["missing_flow_impact_100m"] for r in missing) if missing_bound_ok else None
        lower = sum_amount - missing_impact if missing_impact is not None else None
        upper = sum_amount + missing_impact if missing_impact is not None else None
        interval_direction = ("POSITIVE" if lower is not None and lower > 0 else
                              "NEGATIVE" if upper is not None and upper < 0 else
                              "INDETERMINATE") if missing_bound_ok else "UNKNOWN"
        source_day = str(x.get("latest_date") or "")[:10]
        source_amount, source_lots = number(x.get("today_amount_100m")), number(x.get("today_lots"))
        # Existing cards round lots to tenths, monetary units to four decimals.
        delta_amount = sum_amount - source_amount if source_amount is not None else None
        delta_lots = sum_lots - source_lots if source_lots is not None else None
        # Source aggregate's "today" can actually be the previous trading day.
        # Never reconcile or rank it against a newer trade session.
        matched = (source_day == close_date and len(good) == count and count > 0 and
                   delta_amount is not None and abs(delta_amount) <= .012 and
                   delta_lots is not None and abs(delta_lots) <= .2)
        full_members = count > 0 and len(good) == count
        if matched:
            rank_status = "RECONCILED"
        elif full_members and source_day and source_day < close_date:
            # All registered constituents have today's official foreign/trust
            # shares and same-day closes. Rebuild today's total from all stocks;
            # the older group aggregate is not used or called reconciled.
            rank_status = "REBUILT_ALL_MEMBERS"
        elif full_members and source_day == close_date:
            # A same-day aggregate conflicting with fully dated members is a
            # real integrity failure: never silently choose a side.
            rank_status = "CONFLICT"
        else:
            rank_status = "INCOMPLETE"
        rank_eligible = rank_status in {"RECONCILED", "REBUILT_ALL_MEMBERS"}
        if not matched:
            mismatch_count += 1
        valid_count += len(good)
        positive = sorted((r for r in good if r["estimated_amount_100m"] > 0), key=lambda a: -a["estimated_amount_100m"])
        gross_buy = sum(r["estimated_amount_100m"] for r in positive)
        leader = positive[0] if positive else None
        concentration = (leader["estimated_amount_100m"] / gross_buy * 100) if leader and gross_buy > 0 else None
        opposed = source_amount is not None and source_lots is not None and source_amount * source_lots < 0
        # Separate "ranked by positive money" from "broad participation".
        dominant = len(good) >= 3 and source_amount is not None and source_amount > 0 and (
            bought <= 1 or (concentration is not None and concentration >= 60)
        )
        if not matched:
            verdict = "UNVERIFIED"
        elif len(good) < 3:
            verdict = "SMALL_SAMPLE"
        elif source_amount is not None and source_amount > 0 and bought / len(good) >= .6 and not dominant:
            verdict = "BROAD_INFLOW"
        elif dominant:
            verdict = "CONCENTRATED_INFLOW"
        elif source_amount is not None and source_amount > 0:
            verdict = "DIVERGENT_INFLOW"
        elif source_amount is not None and source_amount < 0 and sold / len(good) >= .6:
            verdict = "BROAD_OUTFLOW"
        else:
            verdict = "MIXED"
        out[group] = {
            "group": group, "trade_date": close_date, "member_count": count,
            "verified_count": len(good), "buy_count": bought,
            "sell_count": sold, "flat_count": neutral,
            "sample_trade_date": close_date if good else None,
            "sample_amount_100m": round(sum_amount, 8) if good else None,
            "sample_lots": round(sum_lots, 4) if good else None,
            "sample_coverage_pct": round(sample_ratio, 2) if sample_ratio is not None else None,
            "sample_eligible": sample_eligible,
            "sample_scope": "SAME_DAY_MATCHED_STOCKS_ONLY",
            "missing_count": len(missing),
            "interval_available": missing_bound_ok,
            "interval_lower_100m": round(lower, 6) if lower is not None else None,
            "interval_upper_100m": round(upper, 6) if upper is not None else None,
            "interval_impact_100m": round(missing_impact, 6) if missing_impact is not None else None,
            "interval_direction": interval_direction,
            "interval_method": "volume_shares * close * 1.30 impact per missing symbol; volume- and turnover-consistency-gated PROXY, not a guaranteed official bound",

            "buy_ratio_pct": round(bought / len(good) * 100, 2) if good else None,
            "largest_positive_code": leader["code"] if leader else None,
            "largest_positive_name": leader["name"] if leader else None,
            "largest_positive_100m": round(leader["estimated_amount_100m"], 4) if leader else None,
            "largest_positive_share_pct": round(concentration, 1) if concentration is not None else None,
            "amount_lots_diverge": opposed,
            "reconciled": matched,
            "rank_eligible": rank_eligible, "rank_status": rank_status,
            "rank_trade_date": close_date if rank_eligible else None,
            "rank_amount_100m": round(sum_amount, 8) if rank_eligible else None,
            "rank_lots": round(sum_lots, 4) if rank_eligible else None,
            "aggregate_source_date": source_day or None,
            "rank_full_member_coverage": full_members,
            "delta_amount_100m": round(delta_amount, 5) if delta_amount is not None else None,
            "delta_lots": round(delta_lots, 3) if delta_lots is not None else None,
            "verdict": verdict, "stocks": rows,
        }
    result = {
        "schema_version": "1.0.0", "dataset": "capital_close_members",
        "build_id": build_id, "trade_date": close_date,
        "as_of": datasets["capital_close_context"].get("as_of"),
        "method": "foreign/trust official net shares per stock multiplied by same-day closing price; amount is an estimate",
        "universe_scope": "ATOMIC_TRACKED_STOCKS_ONLY",
        "group_source": "stock_detail_close.sector_group_or_official_industry; registry must not override upstream group aggregates",
        "tracked_stock_count": len(tracked),
        "sample_rule": "at least 3 same-day stocks with at least 60% of tracked members; sample net is not full-sector net",
        "interval_rule": "missing impact = 130% of validated daily share volume * close; date-matched turnover sanity check; approximate range only, NOT an official upper/lower bound",
        "rank_rule": "ALL listed constituents require same-date foreign, trust and closing price. Full group aggregate must reconcile when its own source date matches; older aggregate is never used for today's rank.",
        "groups": out, "group_count": len(out), "verified_stock_count": valid_count,
        "unreconciled_group_count": mismatch_count,
    }
    data = json.dumps(result, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    dest = root / "builds" / build_id / "capital-close-members.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    datasets["capital_close_members"] = {
        "url": f"./data/builds/{build_id}/capital-close-members.json",
        "hash": "sha256:" + hashlib.sha256(data).hexdigest(),
        "bytes": len(data), "complete": mismatch_count == 0,
        "as_of": result["as_of"], "known_at": datasets["capital_close_context"].get("known_at"),
        "build_id": build_id,
    }
    mf.write_text(json.dumps(m, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print("capital close constituents", {"build": build_id, "date": close_date, "groups": len(out),
                                       "verified": valid_count, "unreconciled": mismatch_count,
                                       "rank_status": {kind: sum(g["rank_status"]==kind for g in out.values())
                                                       for kind in ("RECONCILED","REBUILT_ALL_MEMBERS","CONFLICT","INCOMPLETE")},
                                       "interval_available": sum(g["interval_available"] for g in out.values()),
                                       "memory": {field: out["記憶體IC"][field] for field in ["buy_count", "sell_count", "delta_amount_100m", "delta_lots", "verdict"]}
                                       if "記憶體IC" in out else None})
    # Do not abort deployment for missing/partial provenance in some groups.
    # UI will clearly label them unverified, never invent a strong sector signal.


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="docs/v2/data")
    ap.add_argument("--registry", default="contracts/registries/sector_registry.json")
    a = ap.parse_args()
    build(Path(a.root), Path(a.registry))
