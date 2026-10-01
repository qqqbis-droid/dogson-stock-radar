#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "docs" / "v2" / "index.html"

REQUIRED = {
    "data-source.js",
    "universe-search.js",
    "theme-toggle.js",
    "portfolio-store.js",
    "app.js",
    "market-capital-renderer.js",
    "sector-ranking-panel.js",
    "stock-detail-renderer.js",
    "portfolio-renderer.js",
    "portfolio-ledger-ui.js",
    "portfolio-quick-add.js",
    "radar-transparency-v7.js",
}

FORBIDDEN_ACTIVE = {
    "market-capital-ui.js",
    "pagination-bridge.js",
    "components-ui.js",
    "tradeplan-ui.js",
    "case-ui.js",
    "ux-detail.js",
    "stock-detail-bridge.js",
    "detail-context-v2.js",
    "detail-context-v3.js",
    "score-explain-v4.js",
    "card-display-v3.js",
    "ui-coherence-v5.js",
    "copy-polish-v6.js",
    "card-open-bridge.js",
    "stock-detail-prime.js",
    "live-ui-20261001.js",
    "live-pulse-points.js",
    "live-index-source-guard.js",
    "sector-member-alias-guard.js",
    "sector-summary-layout-v2.js",
    "price-map-theme.js",
    "brand-inuko-lab.js",
    "portfolio-average-cost-label.js",
    "runtime-observability.js",
}

SINGLE_WRITER_FILES = {
    "app.js",
    "market-capital-renderer.js",
    "sector-ranking-panel.js",
    "stock-detail-renderer.js",
    "portfolio-renderer.js",
}

PORTFOLIO_FIELDS = {
    "code", "name", "shares", "avg_cost", "entry_date", "reason_status",
    "entry_reason", "hold_reason", "validation_condition", "failure_condition",
    "strategy", "note",
}


def main():
    html = INDEX.read_text(encoding="utf-8")
    scripts = set(re.findall(r'<script[^>]+src=["\']\.\/([^"\'?]+)', html))
    errors: list[str] = []

    missing = sorted(REQUIRED - scripts)
    forbidden = sorted(FORBIDDEN_ACTIVE & scripts)
    if missing:
        errors.append(f"required production renderers missing: {missing}")
    if forbidden:
        errors.append(f"retired/competing overlay scripts are active: {forbidden}")

    node = shutil.which("node")
    if not node:
        errors.append("node executable unavailable; cannot syntax-check active UI")
    else:
        for name in sorted(REQUIRED):
            path = ROOT / "docs" / "v2" / name
            if not path.is_file():
                errors.append(f"active file missing: {name}")
                continue
            proc = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, cwd=ROOT)
            if proc.returncode != 0:
                msg = (proc.stderr or proc.stdout or "syntax error").strip().splitlines()[-1]
                errors.append(f"active UI syntax failed {name}: {msg}")

    for name in SINGLE_WRITER_FILES:
        path = ROOT / "docs" / "v2" / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "MutationObserver" in text:
            errors.append(f"single-writer renderer must not use MutationObserver: {name}")

    app = (ROOT / "docs" / "v2" / "app.js").read_text(encoding="utf-8")
    detail = (ROOT / "docs" / "v2" / "stock-detail-renderer.js").read_text(encoding="utf-8")
    market = (ROOT / "docs" / "v2" / "market-capital-renderer.js").read_text(encoding="utf-8")

    for token in ('#cards .card[data-code]', 'radar:open-stock', 'NEXT_DAY_ELITE', 'qualityMin:75', 'positionMin:65', 'confidenceMin:80'):
        if token not in app:
            errors.append(f"canonical app interaction missing {token}")
    for capped in ('limit:8', 'NEXT_DAY_ELITE.limit', 'slice(0,NEXT_DAY_ELITE.limit)'):
        if capped in app:
            errors.append(f"tomorrow candidate policy must be uncapped: found {capped}")
    if 'showAllNextDay' not in app:
        errors.append("tomorrow candidate quick filter must render all qualified rows")
    if "await dataset(cfg.detail)" in app.split("async function ensureIndex()", 1)[-1].split("async function ensureDetail()", 1)[0]:
        errors.append("ensureIndex must not fetch multi-megabyte detail data")

    start = detail.find("async function openStock")
    open_fn = detail[start:] if start >= 0 else ""
    if "loadingShell(code)" not in open_fn or "await smanifest()" not in open_fn:
        errors.append("detail open flow missing loading shell or manifest")
    elif open_fn.find("loadingShell(code)") > open_fn.find("await smanifest()"):
        errors.append("detail dialog must open before network awaits")
    for token in ("safeOpen", "radar:detail-core-rendered", "radar:detail-rendered", "支撐區", "壓力區", "評分依據", "資料品質"):
        if token not in detail:
            errors.append(f"canonical detail renderer missing {token}")

    if "../data/market.json" in market or "../data/intraday.json" in market:
        errors.append("canonical market renderer must not read legacy root market/intraday files")

    mounts = {
        "marketSummary": "market-capital-renderer.js",
        "sectorList": "market-capital-renderer.js",
        "sectorRankExplain": "sector-ranking-panel.js",
        "detailBody": "stock-detail-renderer.js",
        "cards": "app.js",
        "portfolioPanel": "portfolio-renderer.js",
        "portfolioCards": "portfolio-renderer.js",
        "portfolioEditDialog": "portfolio-renderer.js",
        "portfolioDetailDialog": "portfolio-renderer.js",
    }
    for mount, owner in mounts.items():
        if html.count(f'id="{mount}"') != 1:
            errors.append(f"{mount} must have exactly one DOM owner mount ({owner})")

    form_fields = set(re.findall(r'<(?:input|select|textarea)[^>]+name=["\']([^"\']+)', html))
    missing_fields = sorted(PORTFOLIO_FIELDS - form_fields)
    if missing_fields:
        errors.append(f"portfolio form missing required fields: {missing_fields}")
    if 'min="1"' not in html or 'name="shares"' not in html:
        errors.append("portfolio must accept actual holdings from 1 share")
    if "localStorage" not in html or "不會寫入公開 GitHub" not in html:
        errors.append("portfolio privacy disclosure missing")
    if "Portfolio Ledger 2.0" not in html or "portfolio-ledger-ui.js" not in html:
        errors.append("portfolio transaction-ledger surface missing")

    store_path = ROOT / "docs" / "v2" / "portfolio-store.js"
    if store_path.is_file():
        store = store_path.read_text(encoding="utf-8")
        if "localStorage" not in store:
            errors.append("portfolio store is not browser-local")
        for forbidden_api in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket("):
            if forbidden_api in store:
                errors.append(f"portfolio store may not transmit holdings: found {forbidden_api}")
        for token in ("transactions", "addTransaction", "deleteTransaction", "history", "realized_pl", "LEGACY_POSITION_MIGRATION", "2.0.0"):
            if token not in store:
                errors.append(f"portfolio ledger 2.0 store missing {token}")

    ledger_path = ROOT / "docs" / "v2" / "portfolio-ledger-ui.js"
    if ledger_path.is_file() and "MutationObserver" in ledger_path.read_text(encoding="utf-8"):
        errors.append("portfolio ledger UI must not DOM-watch/rewrite with MutationObserver")

    quick_path = ROOT / "docs" / "v2" / "portfolio-quick-add.js"
    if quick_path.is_file():
        quick = quick_path.read_text(encoding="utf-8")
        if "RadarPortfolioStore.addTransaction" not in quick:
            errors.append("portfolio quick-add must append through canonical transaction ledger")
        if "MutationObserver" in quick:
            errors.append("portfolio quick-add must not watch/rewrite stock detail DOM")

    if node:
        ledger_test = ROOT / "scripts" / "v2" / "test_portfolio_ledger.js"
        proc = subprocess.run([node, str(ledger_test)], capture_output=True, text=True, cwd=ROOT)
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "ledger arithmetic test failed").strip().splitlines()[-1]
            errors.append(f"portfolio ledger arithmetic failed: {msg}")

    if errors:
        raise SystemExit("single-writer UI gate failed: " + " | ".join(errors))

    smoke = ROOT / "scripts" / "v2" / "validate_product_surface.py"
    subprocess.run([sys.executable, str(smoke)], cwd=ROOT, check=True)

    print({
        "status": "PASS",
        "active_scripts": sorted(scripts),
        "card_owner": "app.js",
        "market_owner": "market-capital-renderer.js",
        "sector_rank_owner": "sector-ranking-panel.js",
        "detail_owner": "stock-detail-renderer.js",
        "detail_loading": "progressive",
        "legacy_index_writer_active": False,
        "mutation_observers_in_single_writers": False,
        "next_day_elite_limit": "unlimited",
        "portfolio_ledger": "2.0.0",
        "portfolio_storage": "browser-local-only",
        "product_smoke": "PASS",
    })


if __name__ == "__main__":
    main()
