#!/usr/bin/env python3
from pathlib import Path


def patch_bundle():
    p=Path('scripts/v2/build_legacy_bundle.py')
    s=p.read_text(encoding='utf-8')
    if 'def intraday_truth_reason(row, trade_date):' not in s:
        anchor='\ndef adapt_intraday_rows(payload, build_id, market_score, generated_at):\n'
        helper=r'''

def intraday_truth_reason(row, trade_date):
    """Return a blocker when the live price/structure chain is not trustworthy."""
    if row.get("quote_price_validated") is False:
        return str(row.get("live_truth_blocker") or "即時價格與5分結構尚未同時驗證")
    structure_date = str(row.get("structure_date") or row.get("date") or "")[:10]
    if structure_date and structure_date != trade_date:
        return f"5分結構日期 {structure_date} ≠ 報價日 {trade_date}"
    px = num(row.get("close"))
    bid = num(row.get("quote_bid1"))
    ask = num(row.get("quote_ask1"))
    book = (bid + ask) / 2.0 if bid is not None and ask is not None else (bid if bid is not None else ask)
    has_trade = bool(row.get("quote_has_trade")) and num(row.get("quote_close")) is not None
    if not has_trade and px is not None and book not in (None, 0):
        gap = abs(px / book - 1.0) * 100.0
        if gap > 2.0:
            return f"結構價與即時五檔差距 {gap:.1f}%；本輪未驗證到真實成交價"
    return None


def apply_intraday_truth_gate(decision, row, *, mission):
    reason = intraday_truth_reason(row, decision["trade_date"])
    if not reason:
        return decision
    decision["lifecycle_stage"] = "OBSERVE"
    decision["action_state"] = "DATA_STALE"
    decision["actionable"] = False
    decision["opportunity_bucket"] = "STALE" if mission == "daytrade_execution" else "RESEARCH_ONLY"
    decision["risk_overlays"] = list(dict.fromkeys(list(decision.get("risk_overlays") or []) + ["DATA_QUALITY_RISK"]))
    decision["blockers"] = list(dict.fromkeys([reason, "盤中分數與支撐壓力暫停，等同交易日價格／結構重新驗證"] + list(decision.get("blockers") or [])))[:3]
    decision["why_now"] = ["即時五檔已更新，但成交價／5分結構尚未同時驗證"]
    scores = decision.setdefault("scores", {})
    scores["intraday_momentum_score"] = None
    if mission == "daytrade_execution":
        scores["daytrade_score"] = None
    components = decision.setdefault("components", {})
    components["intraday"] = None
    if mission == "daytrade_execution":
        components["daytrade"] = None
    quote = decision.setdefault("quote", {})
    verified_trade = num(row.get("quote_close")) if bool(row.get("quote_has_trade")) else None
    quote["price"] = verified_trade
    decision["data_confidence"] = min(num(decision.get("data_confidence"), 0) or 0, 40)
    decision["component_coverage"] = min(num(decision.get("component_coverage"), 0) or 0, 40)
    decision["complete"] = False
    missing = list(decision.get("missing_fields") or [])
    for field in ("verified_live_price", "fresh_5m_structure"):
        if field not in missing:
            missing.append(field)
    decision["missing_fields"] = missing
    return decision
'''
        if anchor not in s: raise SystemExit('bundle anchor missing')
        s=s.replace(anchor,helper+anchor,1)

    old='        out.append(patch_context(d, row=row, payload="intraday.json", freshness=freshness, phase=phase, known_at=known_at, generated_at=generated_at, mission="intraday_swing"))'
    new='        d = patch_context(d, row=row, payload="intraday.json", freshness=freshness, phase=phase, known_at=known_at, generated_at=generated_at, mission="intraday_swing")\n        d = apply_intraday_truth_gate(d, row, mission="intraday_swing")\n        out.append(d)'
    if old in s:
        s=s.replace(old,new,1)

    old2='        d["opportunity_bucket"] = "ACTIONABLE_NOW" if actionable else ("WAIT_TRIGGER" if action == "WAIT_TRIGGER" and freshness == "LIVE" else ("STALE" if freshness != "LIVE" else "NO_TRADE"))\n        out.append(d)'
    new2='        d["opportunity_bucket"] = "ACTIONABLE_NOW" if actionable else ("WAIT_TRIGGER" if action == "WAIT_TRIGGER" and freshness == "LIVE" else ("STALE" if freshness != "LIVE" else "NO_TRADE"))\n        d = apply_intraday_truth_gate(d, row, mission="daytrade_execution")\n        out.append(d)'
    if old2 in s:
        s=s.replace(old2,new2,1)
    p.write_text(s,encoding='utf-8')


def patch_zones():
    p=Path('scripts/v2/enrich_zones.py')
    s=p.read_text(encoding='utf-8')
    old='    for code, decision in (detail.get("items") or {}).items():\n        row = raw.get(str(code), {})\n        support_zones = ['
    new='    for code, decision in (detail.get("items") or {}).items():\n        row = raw.get(str(code), {})\n        live_unverified = context in {"intraday", "daytrade"} and (decision.get("action_state") == "DATA_STALE" or "DATA_QUALITY_RISK" in (decision.get("risk_overlays") or []))\n        if live_unverified:\n            decision["support_zone_ids"] = []\n            decision["resistance_zone_ids"] = []\n            continue\n        support_zones = ['
    if old in s and 'live_unverified = context in' not in s:
        s=s.replace(old,new,1)
    p.write_text(s,encoding='utf-8')


def patch_publish():
    p=Path('scripts/v2/live_publish_patch.py')
    s=p.read_text(encoding='utf-8')
    old='        if not code or qd != trade_date:\n            continue\n        st = parse_clock(trade_date, row.get("structure_time"))'
    new='        if not code or qd != trade_date:\n            continue\n        structure_date = str(row.get("structure_date") or row.get("date") or "")[:10]\n        if structure_date and structure_date != trade_date:\n            continue\n        if row.get("quote_price_validated") is False:\n            continue\n        st = parse_clock(trade_date, row.get("structure_time"))'
    if old in s and 'if row.get("quote_price_validated") is False:' not in s:
        s=s.replace(old,new,1)
    p.write_text(s,encoding='utf-8')


patch_bundle();patch_zones();patch_publish()
print('V2_INTRADAY_TRUTH_GATE_PATCHED')
