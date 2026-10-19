#!/usr/bin/env python3
"""Regression: partial official responses cannot erase valid same-date holdings."""
from __future__ import annotations
import importlib.util
import json
import tempfile
from pathlib import Path

mod_path=Path("scripts/v2/portfolio_quote_fallback.py")
spec=importlib.util.spec_from_file_location("portfolio_quote_fallback",mod_path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def quote(code,day,price,market):
    return {"code":code,"name":code,"trade_date":day,"close":price,"market":market,
            "source":"TWSE STOCK_DAY_ALL" if market=="TWSE" else "TPEx daily_close_quotes"}

with tempfile.TemporaryDirectory() as root:
    prior=Path(root)/"published.json"
    prior.write_text(json.dumps({"source_status":{"TWSE":{"ok":True},"TPEX":{"ok":True}},
          "quotes":{"1802":quote("1802","2026-10-12",66.6,"TWSE"),
                    "6271":quote("6271","2026-10-12",247.5,"TPEX"),
                    "2344":quote("2344","2026-10-09",18.3,"TWSE")}}),encoding="utf-8")
    partial={"quotes":{"1802":quote("1802","2026-10-12",63.5,"TWSE")},
             "source_status":{"TWSE":{"ok":True},"TPEX":{"ok":False}}}
    merged=mod.merge_same_session(partial,prior)
    assert merged["quotes"]["1802"]["close"]==63.5,"Fresh official quote must win"
    assert merged["quotes"]["6271"]["close"]==247.5,"Same-session OTC must survive source outage"
    assert "2344" not in merged["quotes"],"Stale old-day price may not be carried forward"
    assert merged["preserved_same_session"]["from_published"]==1

    completed=Path(root)/"close.json"
    completed.write_text(json.dumps({"trade_date":"2026-10-12","rows":[
        {"code":"1802","name":"台玻","date":"2026-10-12","close":63.1,"market":"上市"},
        {"code":"6271","name":"同欣電","date":"2026-10-12","close":247.5,"market":"上市"},
        {"code":"9904","name":"寶成","date":"2026-10-09","close":30,"market":"上市"},
        {"code":"00685L","name":"群益臺灣加權正2","date":"2026-10-12","close":88.2,"market":"上市"}
    ]}),encoding="utf-8")
    actual=mod.merge_completed_close({"quotes":{"1802":quote("1802","2026-10-08",63,"TWSE")}},completed)
    assert actual["quotes"]["1802"]["close"]==63.1,"Newest completed-session daily K must replace old OpenAPI price"
    assert actual["quotes"]["1802"]["source"].endswith("(non-official)")
    assert actual["quotes"]["6271"]["trade_date"]=="2026-10-12"
    assert "9904" not in actual["quotes"],"Dated fallback must not mix sessions"
    assert actual["quotes"]["00685L"]["close"]==88.2,"Dated verified ETF daily bar must keep alphanumeric code"
    assert actual["quotes"]["00685L"]["source"].endswith("(non-official)"),"ETF daily-K fallback must not masquerade as official close"
    verified=mod.merge_same_session(actual,prior)
    assert verified["quotes"]["1802"]["source"]=="TWSE STOCK_DAY_ALL","Prior same-day official source beats fallback daily bar"

    newer={"quotes":{"1802":quote("1802","2026-10-13",64.5,"TWSE")}, "source_status":{}}
    now=mod.merge_same_session(newer,prior)
    assert set(now["quotes"])=={"1802"},"Older session never contaminates a newer close"
    dated=mod.attach_reference_quotes(
        {"quotes":{"2330":quote("2330","2026-10-15",100,"TWSE")}},
        {"5302":quote("5302","2026-10-14",9.67,"TPEX"),
         "2330":quote("2330","2026-10-14",98,"TWSE")}
    )
    assert dated["reference_quotes"]["5302"]["close"]==9.67,"Official prior day must be available as a dated reference"
    assert "5302" not in dated["quotes"],"Prior-day reference MUST NOT enter current valuation"
    assert "2330" not in dated["reference_quotes"],"Today-priced stocks need no stale fallback"

print("PASS: same-session portfolio quote valuation, separate date-stamped OTC references")
