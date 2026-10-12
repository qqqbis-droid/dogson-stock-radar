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

    newer={"quotes":{"1802":quote("1802","2026-10-13",64.5,"TWSE")}, "source_status":{}}
    now=mod.merge_same_session(newer,prior)
    assert set(now["quotes"])=={"1802"},"Older session never contaminates a newer close"
print("PASS: retain only same-session TWSE/TPEx prices, prefer current official data, reject stale quotes")
