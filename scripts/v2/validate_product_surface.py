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
    sector_layout = text("sector-summary-layout-v2.js")
    detail = text("stock-detail-renderer.js")
    price_map = text("price-map-theme.js")
    card_bridge = text("card-open-bridge.js")
    portfolio = text("portfolio-renderer.js")
    store = text("portfolio-store.js")
    ledger = text("portfolio-ledger-ui.js")
    quick = text("portfolio-quick-add.js")
    universe = text("universe-search.js")
    transparency = text("radar-transparency-v7.js")
    theme = text("theme-toggle.js")
    runtime = text("runtime-observability.js")

    errors: list[str] = []

    for mount in (
        "marketPulse", "mission", "marketSummary", "marketDetail",
        "capitalTitle", "sectorList", "sectorRankExplain", "rankingTitle", "countText",
        "radarSummary", "searchInput", "stageFilter", "actionFilter",
        "positionFilter", "sectorFilter", "cards", "loadMore",
        "detailDialog", "detailTitle", "detailBody",
        "portfolioPanel", "portfolioSummary", "portfolioCards",
    ):
        require_once(html, f'id="{mount}"', "index mount", errors)

    for view, label in (("intraday", "盤中"), ("close", "盤後"), ("portfolio", "庫存"), ("daytrade", "當沖")):
        require(html, f'data-view="{view}"', f"tab {label}", errors)

    require(html, "分數表示條件同步程度，不代表上漲機率", "footer semantics", errors)
    require(html, "排名是注意力順序", "footer ranking semantics", errors)
    require(transparency, "名次只代表今天的注意力順序", "ranking transparency", errors)
    require(transparency, "Shadow", "shadow validation state", errors)
    require(transparency, "官方股票清單", "universe vs pool disclosure", errors)

    for needle in ("市場分", "資料信心", "報價快照", "最後成交", "VWAP／量速／族群結構"):
        require(market, needle, "market environment", errors)
    require(market, "點一下看細節", "capital drill-down affordance", errors)
    require(market, "radar:open-stock", "sector-to-stock bridge", errors)

    # Sector summary V2: upper cards explain the sector; the lower panel owns the
    # stock list. Ranking must reuse the page's official opportunity order and
    # existing mission score instead of inventing a separate sector-member score.
    require(html, "sector-summary-layout-v2.js", "sector summary layout script", errors)
    require(sector_layout, "查看族群明細", "sector summary drill-down", errors)
    require(sector_layout, "同族群股票 ↓", "sector member handoff", errors)
    for needle in (".member-list", ".capital-section-label", ".live-sector-preview", ".live-sector-members"):
        require(sector_layout, needle, "sector upper-member dedupe", errors)
    require(sector_layout, "display:none!important", "sector upper-member hide rule", errors)

    require(sector_rank, "同族群股票", "sector member ranking panel", errors)
    require(sector_rank, "opportunity_rank", "sector official ranking reuse", errors)
    require(sector_rank, "intraday_momentum_score", "intraday sector ranking semantics", errors)
    require(sector_rank, "swing_quality_score", "close sector ranking semantics", errors)
    require(sector_rank, "daytrade_score", "daytrade sector ranking semantics", errors)
    require(sector_rank, "系統不會用假分數補滿", "sector ranking no-fake-score rule", errors)
    require(sector_rank, "radar:open-stock", "sector ranked stock bridge", errors)

    for needle in ("radarSummary", "positionFilter", "sectorFilter", "RadarUniverseSearch"):
        require(app, needle, "radar interaction", errors)
    require(universe, "_outsidePool", "full-market outside-pool state", errors)
    require(universe, "系統不會用假分數補滿", "outside-pool honesty", errors)

    require(html, "card-open-bridge.js", "stock card click bridge script", errors)
    require(card_bridge, "#cards .card[data-code]", "ranked card tap target", errors)
    require(card_bridge, "radar:open-stock", "ranked card open event", errors)
    require(card_bridge, "CustomEvent", "ranked card event dispatch", errors)
    if ".innerHTML" in card_bridge or "showModal" in card_bridge:
        errors.append("stock card bridge must not become a second detail renderer")

    for needle in ("支撐區", "壓力區", "評分依據", "資料品質"):
        require(detail, needle, "stock detail", errors)
    require(detail, "radar:open-stock", "stock detail open event", errors)
    require(html, "price-map-theme.js", "price-map theme script", errors)
    for needle in ("關鍵價位地圖", "第一防守帶", "深層防守帶", "第一突破帶", "延伸突破帶", "DOGSON PRICE MAP"):
        require(price_map, needle, "Dogson price map", errors)
    require(price_map, "沒有可信結構就留白", "price-map no-guess rule", errors)
    require(price_map, "第二層不額外灌分", "price-map no-score-inflation rule", errors)

    for needle in ("entry_reason", "hold_reason", "validation_condition", "failure_condition", "strategy"):
        require(store, needle, "portfolio store schema", errors)
        require(portfolio, needle, "portfolio renderer", errors)
    require(html, 'name="shares"', "portfolio shares field", errors)
    require(html, 'min="1"', "portfolio one-share rule", errors)
    require(html, "不會寫入公開 GitHub", "portfolio privacy disclosure", errors)
    require(html, "Portfolio Ledger 2.0", "portfolio ledger disclosure", errors)
    require(html, "portfolio-ledger-ui.js", "portfolio ledger script", errors)
    for needle in ("transactions", "addTransaction", "history", "realized_pl", "cycle_count"):
        require(store, needle, "portfolio ledger store", errors)
    for needle in ("新增成交", "交易流水", "已實現", "addTransaction"):
        require(ledger, needle, "portfolio ledger interaction", errors)
    require(quick, "RadarPortfolioStore.addTransaction", "detail-to-portfolio ledger append", errors)
    if "RadarPortfolioStore.upsert" in quick:
        errors.append("detail quick-add must not overwrite aggregate holdings in ledger 2.0")

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
        "sector_summary_deduped": True,
        "sector_member_table": True,
        "stock_card_click_bridge": True,
        "stock_detail": True,
        "dogson_price_map": True,
        "score_explanation": True,
        "portfolio_private": True,
        "portfolio_one_share": True,
        "portfolio_ledger": "2.0.0",
        "portfolio_transaction_history": True,
        "dark_mode": True,
        "runtime_observability": True,
        "shadow_disclosure": True,
    })


if __name__ == "__main__":
    main()
