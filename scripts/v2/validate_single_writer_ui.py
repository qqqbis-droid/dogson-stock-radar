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
    "app.js",
    "market-capital-renderer.js",
    "sector-ranking-panel.js",
    "stock-detail-renderer.js",
    "price-map-theme.js",
    "live-pulse-points.js",
    "portfolio-store.js",
    "portfolio-renderer.js",
    "portfolio-quick-add.js",
    "radar-transparency-v7.js",
    "theme-toggle.js",
    "runtime-observability.js",
    "universe-search.js",
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

    missing = sorted(REQUIRED - scripts)
    forbidden = sorted(FORBIDDEN_ACTIVE & scripts)
    errors = []
    if missing:
        errors.append(f"required production renderers missing: {missing}")
    if forbidden:
        errors.append(f"deprecated overlay scripts are active again: {forbidden}")

    for name in SINGLE_WRITER_FILES:
        path = ROOT / "docs" / "v2" / name
        if not path.is_file():
            errors.append(f"renderer file missing: {name}")
            continue
        text = path.read_text(encoding="utf-8")
        if "MutationObserver" in text:
            errors.append(f"single-writer renderer must not use MutationObserver: {name}")

    # Production release gate: every required first-party JS module must parse.
    node = shutil.which("node")
    if not node:
        errors.append("node executable unavailable; cannot syntax-check active UI")
    else:
        for name in sorted(REQUIRED):
            path = ROOT / "docs" / "v2" / name
            if not path.is_file():
                continue
            proc = subprocess.run(
                [node, "--check", str(path)],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            if proc.returncode != 0:
                msg = (proc.stderr or proc.stdout or "syntax error").strip().splitlines()[-1]
                errors.append(f"active UI syntax failed {name}: {msg}")

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

    # Private portfolio contract: the public repo contains only UI/schema code.
    # User holdings must remain browser-local and all decision-reason fields are
    # mandatory UI capabilities even though their text values may be empty.
    form_fields = set(re.findall(r'<(?:input|select|textarea)[^>]+name=["\']([^"\']+)', html))
    missing_fields = sorted(PORTFOLIO_FIELDS - form_fields)
    if missing_fields:
        errors.append(f"portfolio form missing required fields: {missing_fields}")
    if 'min="1"' not in html or 'name="shares"' not in html:
        errors.append("portfolio must accept actual holdings from 1 share")
    if "localStorage" not in html or "不會寫入公開 GitHub" not in html:
        errors.append("portfolio privacy disclosure missing")

    store_path = ROOT / "docs" / "v2" / "portfolio-store.js"
    if store_path.is_file():
        store = store_path.read_text(encoding="utf-8")
        if "localStorage" not in store:
            errors.append("portfolio store is not browser-local")
        for forbidden_api in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket("):
            if forbidden_api in store:
                errors.append(f"portfolio store may not transmit holdings: found {forbidden_api}")
        for field in PORTFOLIO_FIELDS - {"note"}:
            if field not in store:
                errors.append(f"portfolio store schema missing {field}")

    quick_path = ROOT / "docs" / "v2" / "portfolio-quick-add.js"
    if quick_path.is_file():
        quick = quick_path.read_text(encoding="utf-8")
        if "RadarPortfolioStore.upsert" not in quick:
            errors.append("portfolio quick-add must write through the canonical browser-local store")
        if "MutationObserver" in quick:
            errors.append("portfolio quick-add must not watch/rewrite stock detail DOM")

    if errors:
        raise SystemExit("single-writer UI gate failed: " + " | ".join(errors))

    # Product smoke is intentionally a separate validator: this file protects
    # ownership/syntax/privacy; the smoke gate protects the end-user decision
    # journey. Bind them here so every publisher gets both automatically.
    smoke = ROOT / "scripts" / "v2" / "validate_product_surface.py"
    subprocess.run([sys.executable, str(smoke)], cwd=ROOT, check=True)

    print({
        "status": "PASS",
        "active_scripts": sorted(scripts),
        "card_owner": "app.js",
        "market_capital_owner": "market-capital-renderer.js",
        "sector_rank_owner": "sector-ranking-panel.js",
        "detail_owner": "stock-detail-renderer.js",
        "price_map_decorator": "price-map-theme.js",
        "pinned_index_point_change": "live-pulse-points.js",
        "portfolio_owner": "portfolio-renderer.js",
        "portfolio_quick_add_owner": "portfolio-quick-add.js",
        "theme_owner": "theme-toggle.js",
        "runtime_observability_owner": "runtime-observability.js",
        "portfolio_storage": "browser-local-only",
        "portfolio_fields": sorted(PORTFOLIO_FIELDS),
        "runtime_metrics_storage": "session-local-only",
        "syntax_checked": sorted(REQUIRED),
        "product_smoke": "PASS",
        "deprecated_overlays_active": [],
    })


if __name__ == "__main__":
    main()
