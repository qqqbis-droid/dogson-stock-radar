#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility runner for the fast intraday bridge.

Legacy build_data exposes load_json but not save_json. Keep the fast bridge
focused on market logic and inject the canonical docs/data writer here.
"""
import json
from pathlib import Path

import build_data as bd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"


def _save_json(name, obj):
    p = DATA / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


bd.save_json = _save_json

import bridge_intraday_fast as fast  # noqa: E402
import recompute_live_engine as live_engine  # noqa: E402

fast.bd.save_json = _save_json

if __name__ == "__main__":
    fast.main()
    live_engine.main()
