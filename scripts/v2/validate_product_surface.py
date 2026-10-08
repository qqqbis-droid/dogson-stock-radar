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
    app_css = text("app.css")
    quick_filter_css = text("quick-filter.css")
    market = text("market-capital-renderer.js")
    sector_rank = text("sector-ranking-panel.js")
    detail = text("stock-detail-renderer.js")
    portfolio = text("portfolio-renderer.js")
    store = text("portfolio-store.js")
    ledger = text("portfolio-ledger-ui.js")
    quick = text("portfolio-quick-add.js")
    universe = text("universe-search.js")
    transparency = text("radar-transparency-v7.js")
    freshness = text("unified-score-freshness-v1.js")
    theme = text("theme-toggle.js")

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
    require(market, "radar:open-stock", "sector-to-stock bridge", errors)
    require(market, "[data-stock-code]", "canonical sector stock click target", errors)
    if "../data/market.json" in market or "../data/intraday.json" in market:
        errors.append("market environment must not read stale legacy root index files")

    require(sector_rank, "同族群優先股", "inline sector member ranking", errors)
    require(sector_rank, "sector-rank-inline", "inline sector placement", errors)
    require(sector_rank, "data-stock-code", "sector ranked stock canonical bridge", errors)
    require(sector_rank, "opportunity_rank", "sector official ranking reuse", errors)
    require(sector_rank, "intraday_momentum_score", "intraday sector ranking semantics", errors)
    require(sector_rank, "swing_quality_score", "close sector ranking semantics", errors)
    require(sector_rank, "daytrade_score", "daytrade sector ranking semantics", errors)
    require(sector_rank, "系統不會用假分數補滿", "sector ranking no-fake-score rule", errors)

    for needle in ("radarSummary", "positionFilter", "sectorFilter", "RadarUniverseSearch"):
        require(app, needle, "radar interaction", errors)

    require(html, "quick-filter.css", "quick filter stylesheet", errors)
    for needle in ("盤中雷達快篩", "明日作戰快篩", "當沖執行快篩", "data-quick-filter", "quickFilterConfig"):
        require(app, needle, "radar quick filter", errors)
    require(app, 'values:["PULLBACK_TEST","PULLBACK_CONFIRMED"]', "close pullback quick-filter union", errors)
    require(app, "NEXT_DAY_ELITE", "next-day elite policy", errors)
    require(app, "qualityMin:75", "next-day quality gate", errors)
    require(app, "positionMin:65", "next-day position gate", errors)
    require(app, "confidenceMin:80", "next-day confidence gate", errors)
    require(app, "showAllNextDay", "uncapped next-day render path", errors)
    for needle in ("ignitionQuickFilter", "data-close-mode", "🔥 點火雷達", "ignitionCardHtml", "scores?.ignition_score", "ignition_stage",
                   "ignition_execution_ready", "ignition_execution_state", "ignition_execution_note"):
        require(app, needle, "close ignition radar", errors)
    for needle in ('closeMode:state.view==="close"?state.closeMode:null',):
        require(app, needle, "close detail source-mode bridge", errors)
    for needle in ("forcedCloseMode", "SDR.detailCloseMode", "盤後點火", "點火底層證據"):
        require(detail, needle, "ignition detail mode lock", errors)
    require(app_css, ".close-mode-switch", "close ignition mode switch style", errors)
    for needle in ("missionMeta('close').date", "盤後定格", "最後完成收盤"):
        require(freshness, needle, "completed-close freeze semantics", errors)
    for needle in ("ignitionExplain", "Gate 上限", "ignition_components_v2", "volume_acceleration", "relative_acceleration", "chip_acceleration", "tradability_risk",
                   "點火分數只回答", "進場位置"):
        require(detail, needle, "ignition score explanation", errors)
    for capped in ("limit:8", "NEXT_DAY_ELITE.limit", "slice(0,NEXT_DAY_ELITE.limit)"):
        if capped in app:
            errors.append(f"next-day candidate must be uncapped: found {capped}")
    require(app, "rows=applyQuickRows(rows)", "quick filter render pipeline", errors)
    require(app, "state.quickFilter=state.quickFilter===key", "quick filter toggle-off behavior", errors)
    require(app, "data-quick-filter-clear", "quick filter clear control", errors)
    for needle in (".quick-filter-grid", ".quick-filter-card.active", "grid-template-columns:repeat(2"):
        require(quick_filter_css, needle, "quick filter responsive UI", errors)

    require(universe, "_outsidePool", "full-market outside-pool state", errors)
    require(universe, "系統不會用假分數補滿", "outside-pool honesty", errors)

    require(app, '#cards .card[data-code]', "ranked card tap target", errors)
    require(app, "radar:open-stock", "ranked card open event", errors)
    require(app, 'role="button"', "ranked card keyboard target", errors)
    for retired in (
        "card-open-bridge.js", "stock-detail-prime.js", "live-ui-20261001.js",
        "live-pulse-points.js", "live-index-source-guard.js",
        "sector-member-alias-guard.js", "sector-summary-layout-v2.js",
        "price-map-theme.js", "brand-inuko-lab.js",
        "portfolio-average-cost-label.js", "runtime-observability.js",
    ):
        if retired in html:
            errors.append(f"retired overlay still active: {retired}")

    for needle in ("支撐區", "壓力區", "評分依據", "資料品質"):
        require(detail, needle, "stock detail", errors)
    require(detail, "safeOpen", "stock detail immediate dialog", errors)
    require(detail, "radar:detail-core-rendered", "progressive detail core", errors)
    require(detail, "radar:detail-rendered", "progressive detail completion", errors)
    require(detail, "intradayItems", "intraday score evidence", errors)
    require(detail, "前端不重新配分", "intraday no-rescore disclosure", errors)
    open_start = detail.find("async function openStock")
    open_fn = detail[open_start:] if open_start >= 0 else ""
    if "loadingShell(code)" not in open_fn or "await smanifest()" not in open_fn:
        errors.append("stock detail open flow incomplete")
    elif open_fn.find("loadingShell(code)") > open_fn.find("await smanifest()"):
        errors.append("stock detail must open before network fetch")

    ensure_start = app.find("async function ensureIndex")
    ensure_end = app.find("async function ensureDetail")
    ensure_body = app[ensure_start:ensure_end] if ensure_start >= 0 and ensure_end > ensure_start else ""
    if "await dataset(cfg.detail)" in ensure_body:
        errors.append("normal filtering must not download detail dataset")

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

    if errors:
        raise SystemExit("product surface smoke failed: " + " | ".join(errors))

    print({
        "status": "PASS",
        "product_goal": "10s market/attention; immediate detail shell; progressive evidence",
        "market_pulse": True,
        "radar_summary": True,
        "quick_filters": ["intraday", "close", "close_ignition", "daytrade"],
        "close_modes": ["swing", "ignition"],
        "next_day_elite": {"quality_min": 75, "position_min": 65, "confidence_min": 80, "limit": "unlimited"},
        "filters": ["quick", "stage", "action", "position", "sector"],
        "full_market_search": True,
        "sector_drilldown": "inline",
        "stock_card_owner": "app.js",
        "stock_detail_owner": "stock-detail-renderer.js",
        "progressive_stock_detail": True,
        "legacy_index_overlay": False,
        "portfolio_private": True,
        "portfolio_one_share": True,
        "portfolio_ledger": "2.0.0",
        "dark_mode": True,
        "shadow_disclosure": True,
    })

if __name__ == "__main__":
    main()
