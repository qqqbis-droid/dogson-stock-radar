#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "docs" / "v2" / "index.html"

REQUIRED = {
    "app.js",
    "market-capital-renderer.js",
    "stock-detail-renderer.js",
    "portfolio-store.js",
    "portfolio-renderer.js",
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
}

SINGLE_WRITER_FILES = {
    "app.js",
    "market-capital-renderer.js",
    "stock-detail-renderer.js",
    "portfolio-renderer.js",
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

    mounts = {
        "marketSummary": "market-capital-renderer.js",
        "sectorList": "market-capital-renderer.js",
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

    if errors:
        raise SystemExit("single-writer UI gate failed: " + " | ".join(errors))

    print({
        "status": "PASS",
        "active_scripts": sorted(scripts),
        "card_owner": "app.js",
        "market_capital_owner": "market-capital-renderer.js",
        "detail_owner": "stock-detail-renderer.js",
        "portfolio_owner": "portfolio-renderer.js",
        "portfolio_storage": "browser-local-only",
        "deprecated_overlays_active": [],
    })


if __name__ == "__main__":
    main()
