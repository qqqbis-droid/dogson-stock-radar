#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""從目前 GitHub Pages 把上一版 data JSON 拉回 Actions 工作目錄。
讓盤中 workflow 不必每 5 分鐘重跑全市場日K/籌碼，並保留逐日籌碼歷史、60K盤後快照，
以及 v1.4.2 的 TWSE MIS 盤中快照橋接歷史、Step 7 驗證歷史、Step 8 當沖衍生資料。
"""
from pathlib import Path
import os
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data"
OUT.mkdir(parents=True, exist_ok=True)

repo_full = os.environ.get("GITHUB_REPOSITORY", "")
if "/" not in repo_full:
    raise SystemExit(0)

owner, repo = repo_full.split("/", 1)
base = f"https://{owner}.github.io/{repo}/data/"
files = [
    "universe.json", "close.json", "market.json", "intraday.json", "hourly.json", "status.json", "system_status.json",
    "chip_history.json", "chip_status.json", "mis_snapshots.json",
    "validation_history.json", "validation.json", "daytrade.json", "decision_history.json",
]

# Pages sits behind a CDN.  Cache-Control alone is not a strong enough guarantee
# for a scheduled producer that immediately consumes the previous deployment.
# Give every workflow invocation its own cache-busting token while retaining the
# canonical output filenames on disk.
stamp = time.time_ns()

for name in files:
    try:
        r = requests.get(
            base + name,
            params={"ts": f"{stamp}-{name}"},
            timeout=12,
            headers={"Cache-Control": "no-cache, no-store", "Pragma": "no-cache"},
        )
        if r.ok and r.text.strip():
            (OUT / name).write_bytes(r.content)
            print("synced", name)
    except Exception as e:
        print("skip", name, e)
