#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "docs" / "v2"


def text(name: str) -> str:
    p = V2 / name
    if not p.is_file():
        raise SystemExit(f"product smoke: missing file {name}")
    return p.read_text(encoding="utf-8")


def require(haystack: str, needle: str, label: str, errors: list[str]):
    if needle not in haystack:
        errors.append(f"{label}: missing {needle}")


def require_once(haystack: str, needle: str, label: str, errors: list[str]):
    count = haystack.count(needle)
    if count != 1:
        errors.append(f"{label}: expected exactly one {needle}, got {count}")


def main():
    html = text("index.html")
    app = text("app.js")
    market = text("market-capital-renderer.js")
    sector_rank = text("sector-ranking-panel.js")
    detail = text("stock-detail-renderer.js")
    portfolio = text("portfolio-renderer.js")
    store = text("portfolio-store.js")
    quick = text("portfolio-quick-add.js")
    universe = text("universe-search.js")
    transparency = text("radar-transparency-v7.js")
    theme = text("theme-toggle.js")
    runtime = text("runtime-observability.js")

    errors: list[str] = []

    # Core mobile decision flow mounts.
    for mount in (
        "marketPulse", "mission", "marketSummary", "marketDetail",
        "capitalTitle", "sectorList", "sectorRankExplain", "rankingTitle", "countText",
        "radarSummary", "searchInput", "stageFilter", "actionFilter",
        "positionFilter", "sectorFilter", "cards", "loadMore",
        "detailDialog", "detailTitle", "detailBody",
        "portfolioPanel", "portfolioSummary", "portfolioCards",
    ):
        require_once(html, f'id="{mount}"', "index mount", errors)

    # Four missions must remain distinct in the navigation.
    for view, label in (("intraday", "盤中"), ("close", "盤後"), ("portfolio", "庫存"), ("daytrade", "當沖")):
        require(html, f'data-view="{view}"', f"tab {label}", errors)

    # Product semantics: no score/probability confusion.
    require(html, "分數表示條件同步程度，不代表上漲機率", "footer semantics", errors)
    require(html, "排名是注意力順序", "footer ranking semantics", errors)
    require(transparency, "名次只代表今天的注意力順序", "ranking transparency", errors)
    require(transparency, "Shadow", "shadow validation state", errors)
    require(transparency, "官方股票清單", "universe vs pool disclosure", errors)

    # Market environment must expose score reasons and independent clocks.
    for needle in ("市場分", "資料信心", "報價快照", "最後成交", "VWAP／量速／族群結構"):
        require(market, needle, "market environment", errors)
    require(market, "點一下看細節", "capital drill-down affordance", errors)
    require(market, "radar:open-stock", "sector-to-stock bridge", errors)

    # Sector drill-down must explain attention order without inventing a second score.
    require(sector_rank, "族群內先看", "sector watch-priority panel", errors)
    require(sector_rank, "沿用盤後正式排序", "close sector ranking semantics", errors)
    require(sector_rank, "沿用盤中正式排序", "intraday sector ranking semantics", errors)
    require(sector_rank, "不另外發明一套族群內分數", "sector ranking no-fake-score rule", errors)
    require(sector_rank, "radar:open-stock", "sector ranked stock bridge", errors)

    # Radar summary, filters and full-universe search.
    for needle in ("radarSummary", "positionFilter", "sectorFilter", "RadarUniverseSearch"):
        require(app, needle, "radar interaction", errors)
    require(universe, "_outsidePool", "full-market outside-pool state", errors)
    require(universe, "系統不會用假分數補滿", "outside-pool honesty", errors)

    # Stock detail must prioritize action/structure and retain score explanation.
    for needle in ("支撐區", "壓力區", "評分依據", "資料品質"):
        require(detail, needle, "stock detail", errors)
    require(detail, "radar:open-stock", "stock detail open event", errors)

    # Private portfolio contract and one-share rule.
    for needle in ("entry_reason", "hold_reason", "validation_condition", "failure_condition", "strategy"):
        require(store, needle, "portfolio store schema", errors)
        require(portfolio, needle, "portfolio renderer", errors)
    require(html, 'name="shares"', "portfolio shares field", errors)
    require(html, 'min="1"', "portfolio one-share rule", errors)
    require(html, "不會寫入公開 GitHub", "portfolio privacy disclosure", errors)
    require(quick, "RadarPortfolioStore.upsert", "detail-to-portfolio canonical write", errors)

    # Theme and runtime observability are independent controllers, not decision writers.
    require(theme, "data-theme", "dark mode controller", errors)
    require(theme, "dogson.theme.v1", "theme persistence", errors)
    require(runtime, "sessionStorage", "runtime metrics local storage", errors)
    require(runtime, "更多市場資訊・驗證背景", "validation background panel", errors)
    require(runtime, "不會上傳你的操作紀錄", "runtime privacy disclosure", errors)

    if errors:
        raise SystemExit("product surface smoke failed: " + " | ".join(errors))

    print({
        "status": "PASS",
        "product_goal": "10s market/attention; 30s why/trigger/invalidation",
        "market_pulse": True,
        "market_dual_clock": True,
        "radar_summary": True,
        "filters": ["stage", "action", "position", "sector"],
        "full_market_search": True,
        "sector_drilldown": True,
        "sector_attention_reason": True,
        "stock_detail": True,
        "score_explanation": True,
        "portfolio_private": True,
        "portfolio_one_share": True,
        "dark_mode": True,
        "runtime_observability": True,
        "shadow_disclosure": True,
    })


if __name__ == "__main__":
    main()
