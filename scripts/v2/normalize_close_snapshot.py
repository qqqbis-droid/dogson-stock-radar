#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v2.engine import bucket_for, synthesize_action


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")
    raw = text.encode("utf-8")
    return {"hash": "sha256:" + hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def resolve(root: Path, url: str) -> Path:
    raw = str(url or "")
    if raw.startswith("./data/"):
        return root / raw[len("./data/"):]
    return root / raw.lstrip("./")


def records(obj):
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict) and isinstance(obj.get("items"), dict):
        return [x for x in obj["items"].values() if isinstance(x, dict)]
    return [obj] if isinstance(obj, dict) else []


def rows_of(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "data", "stocks", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def num(v, default=None):
    try:
        x = float(v)
        return x if x == x else default
    except Exception:
        return default


def same_trade_date(row: dict, canonical_date: str) -> bool:
    td = str(row.get("trade_date") or row.get("as_of") or "")[:10]
    return bool(canonical_date and td == canonical_date)


def payload_trade_date(payload):
    if not isinstance(payload, dict):
        return ""
    for key in ("trade_date", "source_trade_date", "date"):
        value = str(payload.get(key) or "")[:10]
        if len(value) == 10:
            return value
    dates = [str(r.get("date") or r.get("quote_date") or "")[:10] for r in rows_of(payload) if isinstance(r, dict)]
    dates = [d for d in dates if len(d) == 10]
    return max(dates) if dates else ""


def source_map(payload):
    return {str(r.get("code")): r for r in rows_of(payload) if isinstance(r, dict) and r.get("code")}


def item(label, points, detail="", kind=None):
    p = round(float(points), 2)
    if kind is None:
        kind = "plus" if p > 0 else "minus" if p < 0 else "neutral"
    return {"label": label, "points": p, "detail": str(detail or ""), "kind": kind}


def component_score(decision, key, default=None):
    for x in (((decision.get("components") or {}).get("swing") or {}).get("items") or []):
        if x.get("key") == key:
            return num(x.get("contribution"), num(x.get("raw_score"), default))
    return default


def technical_explanation(src, actual):
    out = []
    trend = bool(src.get("trend")); b3 = bool(src.get("break3")); b20 = bool(src.get("break20"))
    vx = num(src.get("vol_x"), 0); rsi = num(src.get("rsi"), 0); mh = num(src.get("macd_h"), 0); ma = num(src.get("macd_acc"), 0)
    ret5 = num(src.get("ret5")); ret20 = num(src.get("ret20")); dist20 = num(src.get("dist20"), 0)
    if trend: out.append(item("均線多頭", 8, "收盤 > 5MA > 10MA > 20MA"))
    if b3: out.append(item("3日突破", 5, "收盤突破前3日高點"))
    if b20: out.append(item("20日突破", 8, "收盤突破前20日高點"))
    if 1.8 <= vx < 4: out.append(item("量比健康放大", 8, f"量比 {vx:.2f}x"))
    elif 1.3 <= vx < 1.8: out.append(item("量比放大", 5, f"量比 {vx:.2f}x"))
    elif 4 <= vx <= 6: out.append(item("大量但仍在可接受區", 5, f"量比 {vx:.2f}x"))
    if 55 <= rsi <= 72: out.append(item("RSI強而未過熱", 5, f"RSI {rsi:.1f}"))
    elif 50 <= rsi < 55: out.append(item("RSI偏強", 2, f"RSI {rsi:.1f}"))
    if mh > 0 and ma > 0: out.append(item("MACD動能增強", 6, f"柱體 {mh:+.3f}、增量 {ma:+.3f}"))
    elif mh > 0: out.append(item("MACD位於正值", 3, f"柱體 {mh:+.3f}"))
    if ret5 is not None:
        if 2 <= ret5 <= 12: out.append(item("近5日趨勢健康", 5, f"近5日 {ret5:+.1f}%"))
        elif 0 < ret5 < 2: out.append(item("近5日小幅走強", 2, f"近5日 {ret5:+.1f}%"))
    if ret20 is not None:
        if 5 <= ret20 <= 30: out.append(item("近20日趨勢健康", 5, f"近20日 {ret20:+.1f}%"))
        elif 0 < ret20 < 5: out.append(item("近20日小幅走強", 2, f"近20日 {ret20:+.1f}%"))
    if dist20 > 15: out.append(item("距20MA過遠", -8, f"距20MA {dist20:+.1f}%"))
    if ret5 is not None and ret5 > 25: out.append(item("5日漲幅過大", -7, f"近5日 {ret5:+.1f}%"))
    if vx > 6: out.append(item("爆量風險", -5, f"量比 {vx:.2f}x"))
    if rsi > 82: out.append(item("RSI過熱", -5, f"RSI {rsi:.1f}"))
    calc = max(0.0, min(50.0, sum(x["points"] for x in out)))
    if actual is not None and abs(calc - actual) >= 0.5:
        out.append(item("歷史計分／校準差額", actual - calc, f"Engine 最終技術分 {actual:g}/50", "neutral"))
    return out


def chip_explanation(src, actual):
    out = []
    f3 = src.get("foreign_3buy"); fl = num(src.get("foreign_net_latest"), 0)
    if f3 is not None:
        if f3: out.append(item("外資連3買", 8, f"今日 {fl:+,.0f} 股"))
        elif fl > 0: out.append(item("外資今日買超但未連3買", 5, f"今日 {fl:+,.0f} 股"))
        else: out.append(item("外資未連3買／今日偏賣", 1, f"今日 {fl:+,.0f} 股"))
    else: out.append(item("外資資料缺口中性處理", 4, "未把缺值當成0", "neutral"))
    sdown = src.get("sbl_3down"); schg = num(src.get("sbl_3change_pct"))
    if sdown is not None:
        if sdown: out.append(item("借券連3日下降", 7, f"3日變化 {schg:+.1f}%" if schg is not None else "連3日下降"))
        elif schg is not None and schg < 0: out.append(item("借券下降", 4.5, f"3日變化 {schg:+.1f}%"))
        else: out.append(item("借券未下降", 1, f"3日變化 {schg:+.1f}%" if schg is not None else ""))
    else: out.append(item("借券資料缺口中性處理", 3.5, "未把缺值當成0", "neutral"))
    trust = num(src.get("trust_net_latest"))
    if trust is not None:
        if trust > 0: out.append(item("投信買超", 5, f"今日 {trust:+,.0f} 股"))
        elif trust == 0: out.append(item("投信中性", 2.5, "今日 0 股", "neutral"))
        else: out.append(item("投信賣超", 0, f"今日 {trust:+,.0f} 股", "minus"))
    else: out.append(item("投信資料缺口中性處理", 2.5, "未把缺值當成0", "neutral"))
    ms = str(src.get("margin_status") or "")
    mp = num(src.get("margin_3d_pct"))
    if ms:
        if ms == "正常": out.append(item("融資正常", 5, f"3日 {mp:+.1f}%" if mp is not None else ""))
        elif ms == "下降": out.append(item("融資下降", 4, f"3日 {mp:+.1f}%" if mp is not None else ""))
        elif ms == "偏熱": out.append(item("融資偏熱", 0, f"3日 {mp:+.1f}%" if mp is not None else "", "minus"))
        else: out.append(item("融資中性", 2.5, ms, "neutral"))
    else: out.append(item("融資資料缺口中性處理", 2.5, "未把缺值當成0", "neutral"))
    calc = min(25.0, sum(x["points"] for x in out))
    if actual is not None and abs(round(calc) - actual) >= 0.5:
        out.append(item("歷史計分／四捨五入差額", actual - calc, f"Engine 最終籌碼分 {actual:g}/25", "neutral"))
    return out


def sector_explanation(src, actual):
    sec10 = num(src.get("sector_score"))
    ratio = num(src.get("sector_hot_ratio")); n = src.get("sector_hot_count"); label = src.get("sector_score_label") or src.get("industry_name") or "未分類"
    if sec10 is None and actual is not None:
        sec10 = actual / 1.5
    detail = f"{label}"
    if ratio is not None: detail += f"；強勢比 {ratio:.1f}%"
    if n is not None: detail += f"；強勢檔數 {n}"
    pts = actual if actual is not None else min(15.0, max(0.0, (sec10 or 0) * 1.5))
    return [item("族群共振", pts, f"基礎 {sec10:g}/10 × 1.5 → {pts:g}/15；{detail}" if sec10 is not None else detail)]


def liquidity_explanation(src, actual):
    level = str(src.get("liquidity_level") or "")
    amt = num(src.get("avg_turnover20_mn"))
    if not level and amt is not None:
        level = "不足" if amt < 30 else "偏低" if amt < 80 else "正常" if amt < 200 else "活躍"
    pts = actual if actual is not None else {"活躍":10,"正常":8,"偏低":5,"不足":0}.get(level, 6)
    detail = f"20日平均成交金額約 {amt:.1f} 百萬元；流動性＝{level or '未知'}" if amt is not None else f"流動性＝{level or '未知'}"
    return [item("流動性級距", pts, detail)]


def entry_explanation(src):
    out = [item("基本位置分", 40, "進場位置模型基礎分")]
    trend = bool(src.get("trend")); b20 = bool(src.get("break20")); b3 = bool(src.get("break3"))
    dist = num(src.get("dist20"), 999); vx = num(src.get("vol_x"), 0); ret5 = num(src.get("ret5"), 999); close = num(src.get("close"))
    if trend: out.append(item("均線多頭", 10, "趨勢結構完整"))
    if b20: out.append(item("20日突破", 5, "正式突破加分"))
    elif b3: out.append(item("3日突破", 3, "短平台突破加分"))
    if 0 <= dist <= 3: out.append(item("靠近20MA", 20, f"距20MA {dist:+.1f}%"))
    elif dist <= 7: out.append(item("距20MA尚合理", 15, f"距20MA {dist:+.1f}%"))
    elif dist <= 10: out.append(item("距20MA偏遠", 8, f"距20MA {dist:+.1f}%"))
    elif dist <= 15: out.append(item("距20MA較遠", 2, f"距20MA {dist:+.1f}%"))
    if 1.2 <= vx <= 2.5: out.append(item("量比健康", 10, f"量比 {vx:.2f}x"))
    elif 0.8 <= vx < 1.2: out.append(item("量能普通", 5, f"量比 {vx:.2f}x"))
    elif vx > 4: out.append(item("量能過熱", -5, f"量比 {vx:.2f}x"))
    if 0 <= ret5 <= 8: out.append(item("近5日未過度延伸", 10, f"近5日 {ret5:+.1f}%"))
    elif ret5 <= 15: out.append(item("近5日仍可接受", 5, f"近5日 {ret5:+.1f}%"))
    elif ret5 > 20: out.append(item("近5日漲幅過大", -10, f"近5日 {ret5:+.1f}%"))
    support = src.get("support") or {}
    sup_hi = num(support.get("high")) if isinstance(support, dict) else None
    if close is not None and sup_hi and close >= sup_hi and (close / sup_hi - 1) <= .03:
        out.append(item("仍靠近支撐上緣", 5, f"支撐上緣 {sup_hi:g}，現價 {close:g}"))
    over = list(src.get("overheat_reasons") or [])
    if over:
        out.append(item("過熱條件扣分", -min(25.0, 10.0 * len(over)), "、".join(map(str, over))))

    # V4：把壓力區直接納入進場位置，避免「已撞壓力卻仍100分」。
    resistance = src.get("resistance") or {}
    rlo = num(resistance.get("low")) if isinstance(resistance, dict) else None
    rhi = num(resistance.get("high")) if isinstance(resistance, dict) else None
    if close is not None and rlo is not None and rhi is not None:
        rlo, rhi = min(rlo, rhi), max(rlo, rhi)
        if rlo <= close <= rhi:
            out.append(item("身處壓力區", -20, f"現價 {close:g} 位於 {rlo:g}–{rhi:g}", "minus"))
        elif close < rlo:
            gap = (rlo / close - 1) * 100 if close > 0 else 999
            if gap <= 1: out.append(item("距壓力極近", -15, f"距壓力下緣僅 {gap:.1f}%", "minus"))
            elif gap <= 2.5: out.append(item("距壓力偏近", -10, f"距壓力下緣 {gap:.1f}%", "minus"))
            elif gap <= 5: out.append(item("上方壓力不遠", -5, f"距壓力下緣 {gap:.1f}%", "minus"))
        else:
            above = (close / rhi - 1) * 100 if rhi > 0 else 999
            if above <= 1.5:
                out.append(item("剛越過壓力待確認", -5, f"高於壓力上緣僅 {above:.1f}%；需隔日確認", "minus"))

    score = round(max(0.0, min(100.0, sum(x["points"] for x in out))), 1)
    return score, out


def build_explanations(decision, src, entry_score, entry_items):
    return {
        "version": "score-explain-v4-resistance-aware",
        "formula": "波段品質=技術50+籌碼25+族群15+流動性10；進場位置另計100並納入壓力區風險",
        "technical": {"score": component_score(decision, "technical", 0), "max": 50, "items": technical_explanation(src, component_score(decision, "technical", 0))},
        "chip": {"score": component_score(decision, "chip", 0), "max": 25, "items": chip_explanation(src, component_score(decision, "chip", 0))},
        "sector": {"score": component_score(decision, "sector", 0), "max": 15, "items": sector_explanation(src, component_score(decision, "sector", 0))},
        "liquidity": {"score": component_score(decision, "liquidity", 0), "max": 10, "items": liquidity_explanation(src, component_score(decision, "liquidity", 0))},
        "entry_position": {"score": entry_score, "max": 100, "items": entry_items, "model": "entry-position-v2-pressure-aware"},
    }


def normalize_decision(row: dict, canonical_date: str, src: dict | None = None, attach_explanations=False) -> bool:
    if not same_trade_date(row, canonical_date):
        return False
    changed = False
    if row.get("session_phase") != "POST_CLOSE": row["session_phase"] = "POST_CLOSE"; changed = True
    if row.get("freshness") != "FRESH": row["freshness"] = "FRESH"; changed = True
    overlays = [x for x in (row.get("risk_overlays") or []) if x != "DATA_QUALITY_RISK"]
    if overlays != list(row.get("risk_overlays") or []): row["risk_overlays"] = overlays; changed = True
    blockers = [x for x in (row.get("blockers") or []) if str(x) not in {"資料不是目前可執行快照", "資料新鮮度不足"}]
    if blockers != list(row.get("blockers") or []): row["blockers"] = blockers; changed = True

    scores = row.setdefault("scores", {})
    entry = scores.get("entry_position_score")
    entry_items = None
    if src:
        new_entry, entry_items = entry_explanation(src)
        if num(entry) != num(new_entry): scores["entry_position_score"] = new_entry; entry = new_entry; changed = True
    action, actionable = synthesize_action(row.get("lifecycle_stage"), overlays, "FRESH", entry_score=entry, has_position=False)
    if row.get("action_state") != action: row["action_state"] = action; changed = True
    if row.get("actionable") != bool(actionable): row["actionable"] = bool(actionable); changed = True
    no_chase = action == "DO_NOT_CHASE"
    if row.get("no_chase") != no_chase: row["no_chase"] = no_chase; changed = True
    bucket = bucket_for("close_next_day", row.get("lifecycle_stage"), action, "FRESH", bool(actionable), False)
    if row.get("opportunity_bucket") != bucket: row["opportunity_bucket"] = bucket; changed = True

    if attach_explanations and src and entry_items is not None:
        exp = build_explanations(row, src, entry, entry_items)
        if row.get("score_explanations") != exp:
            row["score_explanations"] = exp; changed = True
    return changed


def normalize_generic_close(row: dict, canonical_date: str) -> bool:
    if not same_trade_date(row, canonical_date): return False
    changed = False
    if row.get("session_phase") != "POST_CLOSE": row["session_phase"] = "POST_CLOSE"; changed = True
    if row.get("freshness") != "FRESH": row["freshness"] = "FRESH"; changed = True
    flags = list(row.get("risk_flags") or [])
    cleaned = [x for x in flags if "歷史市場快照" not in str(x)]
    if cleaned != flags: row["risk_flags"] = cleaned; changed = True
    return changed


def update_meta_file(root, manifest, key, obj):
    meta = (manifest.get("datasets") or {}).get(key)
    if not meta: return
    path = resolve(root, meta.get("url"))
    meta.update(write(path, obj))


def evidence_maps(root: Path, manifest: dict, canonical_date: str):
    evidence = {}
    meta = (manifest.get("datasets") or {}).get("stock_detail_close")
    if meta:
        p = resolve(root, meta.get("url"))
        if p.exists(): evidence = (load(p).get("items") or {})
    raw = {}
    close_path = ROOT / "docs" / "data" / "close.json"
    if close_path.exists():
        payload = load(close_path)
        if payload_trade_date(payload) == canonical_date: raw = source_map(payload)
    merged = {}
    for code in set(evidence) | set(raw):
        merged[str(code)] = {**(evidence.get(str(code)) or {}), **(raw.get(str(code)) or {})}
    return merged


def rerank(rows):
    order = {"NEXT_DAY_READY":0,"BREAKOUT_WATCH":1,"PULLBACK_WATCH":2,"TREND_QUALITY":3,"RESEARCH":4,"RISK":5}
    ranked = sorted(
        rows,
        key=lambda d: (
            order.get(d.get("opportunity_bucket"), 99),
            -(num((d.get("scores") or {}).get("swing_quality_score"), -1)),
            -(num((d.get("scores") or {}).get("entry_position_score"), -1)),
            -(num(d.get("data_confidence"), 0)),
            str(d.get("code") or ""),
        ),
    )
    return {str(d.get("code")): i for i,d in enumerate(ranked,1)}


def normalize_decision_dataset(root, manifest, key, canonical_date, sources, *, attach_explanations=False, rank_map=None):
    meta = (manifest.get("datasets") or {}).get(key)
    if not meta: return 0, None
    path = resolve(root, meta.get("url"))
    if not path.exists(): raise SystemExit(f"close snapshot normalizer: missing dataset {key}: {path}")
    obj = load(path); changed = 0
    for row in records(obj):
        src = sources.get(str(row.get("code"))) or {}
        if normalize_decision(row, canonical_date, src, attach_explanations=attach_explanations): changed += 1
        if rank_map and str(row.get("code")) in rank_map and row.get("opportunity_rank") != rank_map[str(row.get("code"))]:
            row["opportunity_rank"] = rank_map[str(row.get("code"))]; changed += 1
    if changed: meta.update(write(path, obj))
    return changed, obj


def normalize_generic_dataset(root, manifest, key, canonical_date):
    meta = (manifest.get("datasets") or {}).get(key)
    if not meta: return 0
    path = resolve(root, meta.get("url"))
    if not path.exists(): raise SystemExit(f"close snapshot normalizer: missing dataset {key}: {path}")
    obj = load(path); changed = 0
    for row in records(obj):
        if normalize_generic_close(row, canonical_date): changed += 1
    if changed: meta.update(write(path, obj))
    return changed


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default="docs/v2/data"); args = ap.parse_args()
    root = Path(args.root); manifest_path = root / "current_manifest.json"; manifest = load(manifest_path)
    canonical_date = str(manifest.get("trade_date") or "")[:10]
    if len(canonical_date) != 10: raise SystemExit("close snapshot normalizer: manifest trade_date missing")
    sources = evidence_maps(root, manifest, canonical_date)

    counts = {}
    counts["decision_close_detail"], detail_obj = normalize_decision_dataset(root, manifest, "decision_close_detail", canonical_date, sources, attach_explanations=True)
    rank_map = rerank(records(detail_obj)) if detail_obj is not None else {}
    for key in ("decision_close_summary", "decision_close_index"):
        counts[key], _ = normalize_decision_dataset(root, manifest, key, canonical_date, sources, rank_map=rank_map)
    for key in ("sector_close", "market_summary", "market_close_context", "capital_close_context"):
        counts[key] = normalize_generic_dataset(root, manifest, key, canonical_date)

    warnings = manifest.setdefault("health", {}).setdefault("warnings", [])
    for warning in (
        "Close Snapshot Policy：最近完成交易日跨午夜仍視為盤後可規劃快照，不因日曆換日自動標記 DATA_STALE。",
        "Entry Position V2：進場位置已納入壓力區距離／身處壓力區扣分；不再讓撞壓力股票維持假性100分。",
        "Score Explain V4：盤後技術／籌碼／族群／流動性／進場位置皆保存加分、扣分與實際依據，前端只負責呈現。",
    ):
        if warning not in warnings: warnings.append(warning)
    write(manifest_path, manifest)
    print("normalized latest completed close snapshot", {"trade_date":canonical_date,"changed":sum(counts.values()),"datasets":counts,"score_explain":"v4","entry_model":"pressure-aware"})


if __name__ == "__main__":
    main()
