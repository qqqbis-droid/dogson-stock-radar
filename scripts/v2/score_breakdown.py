from __future__ import annotations


def _num(value):
    try:
        x = float(value)
        return x if x == x else None
    except Exception:
        return None


def _component(key, label, raw, max_score, contribution=None):
    value = _num(raw)
    if value is None:
        return None
    contrib = _num(contribution)
    if contrib is None:
        contrib = value
    return {
        "key": key,
        "label": label,
        "score": round(value, 2),
        "max_score": float(max_score),
        "contribution": round(contrib, 2),
    }


def _model(model, total, basis, specs, weight_source=None):
    total_value = _num(total)
    components = []
    for key, label, max_score, raw, contribution in specs:
        item = _component(key, label, raw, max_score, contribution)
        if item is not None:
            components.append(item)
    if total_value is None and not components:
        return None
    return {
        "model": model,
        "total": round(total_value, 2) if total_value is not None else None,
        "basis": basis,
        "weight_source": weight_source,
        "components": components,
    }


def build_score_breakdown(row):
    """Map already-computed v1.x components into the v2 canonical explanation contract.

    This function never re-scores a stock. It only carries forward values already
    computed by the source engine so the UI can explain the same decision without
    creating a second scoring model.
    """
    swing_raw = row.get("swing_components") or {}
    swing_weighted = row.get("swing_weighted_components") or {}
    swing_total = _num(row.get("swing_quality_score"))
    if swing_total is None and str(row.get("score_type") or "") not in {"intraday_execution", "daytrade_execution"}:
        swing_total = _num(row.get("score"))
    swing = _model(
        "SWING",
        swing_total,
        "LEGACY_V1_CALCULATED" if swing_raw else "TOTAL_ONLY",
        [
            ("technical", "技術", 50, swing_raw.get("technical"), swing_weighted.get("technical")),
            ("chip", "籌碼", 25, swing_raw.get("chip"), swing_weighted.get("chip")),
            ("sector", "族群", 15, swing_raw.get("sector"), swing_weighted.get("sector")),
            ("liquidity", "流動性", 10, swing_raw.get("liquidity"), swing_weighted.get("liquidity")),
        ],
        row.get("swing_weight_source"),
    )

    intraday_raw = row.get("intraday_components") or {}
    intraday = _model(
        "INTRADAY",
        row.get("intraday_score", row.get("intraday_momentum_score")),
        "LEGACY_V1_CALCULATED" if intraday_raw else "TOTAL_ONLY",
        [
            ("price_structure", "價格結構", 30, intraday_raw.get("price_structure"), None),
            ("flow_volume", "量價動能", 25, intraday_raw.get("flow_volume"), None),
            ("relative_strength", "相對強弱", 15, intraday_raw.get("relative_strength"), None),
            ("sector", "族群", 20, intraday_raw.get("sector"), None),
            ("liquidity_risk", "流動性／追價風險", 10, intraday_raw.get("liquidity_risk"), None),
        ],
        "baseline",
    )

    daytrade_raw = row.get("daytrade_components") or {}
    daytrade = _model(
        "DAYTRADE",
        row.get("daytrade_score"),
        "LEGACY_V1_CALCULATED" if daytrade_raw else "TOTAL_ONLY",
        [
            ("execution_structure", "執行結構", 30, daytrade_raw.get("execution_structure"), None),
            ("flow_volume", "量價推進", 25, daytrade_raw.get("flow_volume"), None),
            ("relative_sector", "相對強弱／族群", 20, daytrade_raw.get("relative_sector"), None),
            ("timing_volatility", "時機／波動效率", 15, daytrade_raw.get("timing_volatility"), None),
            ("liquidity_risk", "流動性／追價風險", 10, daytrade_raw.get("liquidity_risk"), None),
        ],
        "baseline",
    )

    return {"swing": swing, "intraday": intraday, "daytrade": daytrade}
