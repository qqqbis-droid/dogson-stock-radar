#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.27 — Step 6：分數精準化／個股動態門檻。

固定過熱門檻逐步改為「ATR14 + 個股近60日分布 + 同時段歷史分布」。
不改盤中 30/25/15/20/10，不新增分數桶；樣本不足就回退舊門檻。
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def must(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f"v1.5.27 missing marker: {label}")
    return text.replace(old, new, count)


HELPERS = r'''
def _finite(v):
    try:
        z = float(v)
        return z if np.isfinite(z) else None
    except Exception:
        return None


def _clamp(v, lo, hi):
    return max(float(lo), min(float(hi), float(v)))


def _dynamic_threshold_values(r, daily_profile=None):
    """個股動態門檻；只替換門檻，不改任何分數桶權重。"""
    dp = daily_profile or r.get("dynamic_profile") or {}
    atr = _finite(dp.get("atr14_pct"))
    d1p90 = _finite(dp.get("abs_ret1_p90"))
    vxp90 = _finite(dp.get("vol_x_p90"))
    same_day = _finite(r.get("same_time_day_abs_p90"))
    same_vwap = _finite(r.get("same_time_vwap_abs_p90"))
    same_ret15 = _finite(r.get("same_time_ret15_abs_p90"))
    same_n = int(r.get("dynamic_sample_days") or r.get("amp_sample_days") or 0)
    daily_ready = bool(dp.get("ready"))

    evidence = []
    if atr is not None:
        evidence.append("ATR14")
    if daily_ready:
        evidence.append("近60日個股分布")
    if same_n >= 3:
        evidence.append("同時段歷史分布")
    ready = bool(daily_ready and atr is not None and same_n >= 3)

    if not evidence:
        return {
            "version": "1.0", "ready": False, "mode": "fallback",
            "day_hot_pct": 8.5, "vwap_hot_pct": 4.5,
            "ret15_hot_pct": 4.0, "pace_hot_x": 5.0,
            "day_good_high_pct": 6.5, "ret15_good_high_pct": 2.5,
            "atr14_pct": None, "sample_days": same_n,
            "evidence": [], "note": "歷史基準尚未建立，暫用舊版固定門檻",
        }

    day_candidates = [6.0]
    if atr is not None:
        day_candidates.append(atr * 2.0)
    if d1p90 is not None:
        day_candidates.append(d1p90 * 1.15)
    if same_day is not None:
        day_candidates.append(same_day * 1.25)
    day_hot = _clamp(max(day_candidates), 6.0, 9.5)

    vwap_candidates = [2.2]
    if atr is not None:
        vwap_candidates.append(atr * 0.90)
    if same_vwap is not None:
        vwap_candidates.append(same_vwap * 1.25)
    vwap_hot = _clamp(max(vwap_candidates), 2.2, 6.0)

    ret15_candidates = [2.0]
    if atr is not None:
        ret15_candidates.append(atr * 0.70)
    if same_ret15 is not None:
        ret15_candidates.append(same_ret15 * 1.30)
    ret15_hot = _clamp(max(ret15_candidates), 2.0, 5.0)

    pace_candidates = [3.5]
    if vxp90 is not None:
        pace_candidates.append(vxp90 * 1.10)
    pace_hot = _clamp(max(pace_candidates), 3.5, 6.5)

    return {
        "version": "1.0", "ready": ready,
        "mode": "personalized" if ready else "warming",
        "day_hot_pct": round(day_hot, 2),
        "vwap_hot_pct": round(vwap_hot, 2),
        "ret15_hot_pct": round(ret15_hot, 2),
        "pace_hot_x": round(pace_hot, 2),
        "day_good_high_pct": round(_clamp(day_hot * 0.72, 3.5, 7.0), 2),
        "ret15_good_high_pct": round(_clamp(ret15_hot * 0.62, 1.3, 3.0), 2),
        "atr14_pct": round(atr, 2) if atr is not None else None,
        "sample_days": same_n,
        "evidence": evidence,
        "note": "個股自己的ATR／歷史分布門檻" if ready else "部分個股化；樣本不足的部分仍採保守下限",
    }


def _apply_dynamic_thresholds(r, daily_profile=None):
    dyn = _dynamic_threshold_values(r, daily_profile)
    r["dynamic_thresholds"] = dyn
    day = _finite(r.get("day_change")) or 0.0
    vwap_dist = _finite(r.get("vwap_dist")) or 0.0
    pace = _finite(r.get("pace")) or 0.0
    ret15 = _finite(r.get("ret15")) or 0.0
    over = []
    if day >= float(dyn["day_hot_pct"]):
        over.append(f"漲幅超過個股門檻 {dyn['day_hot_pct']:.1f}%")
    if vwap_dist > float(dyn["vwap_hot_pct"]):
        over.append(f"距VWAP超過個股門檻 {dyn['vwap_hot_pct']:.1f}%")
    if pace > float(dyn["pace_hot_x"]):
        over.append(f"量速超過個股門檻 {dyn['pace_hot_x']:.1f}x")
    if ret15 > float(dyn["ret15_hot_pct"]):
        over.append(f"15分鐘漲幅超過個股門檻 {dyn['ret15_hot_pct']:.1f}%")
    amp = str(r.get("amplitude_regime") or "")
    if amp == "高震盪":
        over.append("高振幅低效率")
    elif amp == "沖高回落":
        over.append("振幅擴大後沖高回落")
    r["overheat_reasons"] = over
    return r


def _refresh_dynamic_thresholds(rows, close_map):
    for r in rows or []:
        _apply_dynamic_thresholds(r, (close_map or {}).get(str(r.get("code") or "")) or {})
    return rows

'''


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)
    s = s.replace("犬子老師飆股雷達 Free Edition v1.5.25", "犬子老師飆股雷達 Free Edition v1.5.27", 1)

    anchor = "def _chip_background_label(score, coverage):"
    if "def _dynamic_threshold_values" not in s:
        s = must(s, anchor, HELPERS + "\n" + anchor, "dynamic helpers")

    old = '''    row["technical_score"] = max(0, min(50, round(score, 1)))\n    row["reasons"] = reasons\n    row["overheat_reasons"] = over\n    row.update(daily_sr(x))\n    return row\n'''
    new = '''    # Step 6：建立每檔自己的日波動基準，供盤中動態門檻使用。\n    tr14 = true_range(x).rolling(14).mean()\n    atr14 = float(tr14.iloc[-1]) if pd.notna(tr14.iloc[-1]) else None\n    hist_ret = ret1.tail(60).dropna().abs()\n    hist_vx = vx.tail(60).dropna()\n    row["dynamic_profile"] = {\n        "version": "1.0",\n        "ready": bool(len(hist_ret) >= 35 and atr14 is not None and row["close"] > 0),\n        "sample_days": int(len(hist_ret)),\n        "atr14_pct": round(atr14 / row["close"] * 100, 3) if atr14 is not None and row["close"] > 0 else None,\n        "abs_ret1_p90": round(float(hist_ret.quantile(.90)), 3) if len(hist_ret) >= 10 else None,\n        "abs_ret1_median": round(float(hist_ret.median()), 3) if len(hist_ret) >= 10 else None,\n        "vol_x_p90": round(float(hist_vx.quantile(.90)), 3) if len(hist_vx) >= 10 else None,\n    }\n    row["technical_score"] = max(0, min(50, round(score, 1)))\n    row["reasons"] = reasons\n    row["overheat_reasons"] = over\n    row.update(daily_sr(x))\n    return row\n'''
    s = must(s, old, new, "daily dynamic profile")

    old = '''    amp_sample_days = len(amp_samples)\n    same_time_amp_avg_pct = float(np.mean(amp_samples)) if amp_samples else None\n    amplitude_multiple = (amplitude_pct / same_time_amp_avg_pct) if same_time_amp_avg_pct and same_time_amp_avg_pct > 1e-9 else None\n    amp_baseline_ready = bool(amp_sample_days >= 3 and amplitude_multiple is not None)\n'''
    new = '''    amp_sample_days = len(amp_samples)\n    same_time_amp_avg_pct = float(np.mean(amp_samples)) if amp_samples else None\n    amplitude_multiple = (amplitude_pct / same_time_amp_avg_pct) if same_time_amp_avg_pct and same_time_amp_avg_pct > 1e-9 else None\n    amp_baseline_ready = bool(amp_sample_days >= 3 and amplitude_multiple is not None)\n\n    # Step 6：同一個股、同一時間點的歷史分布。\n    day_abs_samples, vwap_abs_samples, ret15_abs_samples = [], [], []\n    prior_dates = [d for d in all_dates if d < latest][-20:]\n    for d0 in prior_dates:\n        hist = x[x.index.date == d0]\n        hist = hist[[ts.time() <= cutoff_time for ts in hist.index]]\n        if hist.empty:\n            continue\n        earlier = [d for d in all_dates if d < d0]\n        if not earlier:\n            continue\n        pday = x[x.index.date == earlier[-1]]\n        if pday.empty:\n            continue\n        hpclose = float(pday["Close"].iloc[-1])\n        if hpclose <= 0:\n            continue\n        hclose = float(hist["Close"].iloc[-1])\n        htyp = (hist["High"] + hist["Low"] + hist["Close"]) / 3\n        hvwap_s = (htyp * hist["Volume"]).cumsum() / hist["Volume"].cumsum().replace(0, np.nan)\n        hvwap = _finite(hvwap_s.iloc[-1])\n        day_abs_samples.append(abs((hclose / hpclose - 1) * 100))\n        if hvwap and hvwap > 0:\n            vwap_abs_samples.append(abs((hclose / hvwap - 1) * 100))\n        if len(hist) >= 4:\n            ret15_abs_samples.append(abs((hclose / float(hist["Close"].iloc[-4]) - 1) * 100))\n\n    dynamic_sample_days = len(day_abs_samples)\n    same_time_day_abs_p90 = float(np.quantile(day_abs_samples, .90)) if len(day_abs_samples) >= 3 else None\n    same_time_vwap_abs_p90 = float(np.quantile(vwap_abs_samples, .90)) if len(vwap_abs_samples) >= 3 else None\n    same_time_ret15_abs_p90 = float(np.quantile(ret15_abs_samples, .90)) if len(ret15_abs_samples) >= 3 else None\n'''
    s = must(s, old, new, "same time dynamic samples")

    old = '''        "amp_sample_days": amp_sample_days,\n        "amp_baseline_ready": amp_baseline_ready,\n        "amplitude_regime": amplitude_regime,\n'''
    new = '''        "amp_sample_days": amp_sample_days,\n        "amp_baseline_ready": amp_baseline_ready,\n        "dynamic_sample_days": dynamic_sample_days,\n        "same_time_day_abs_p90": round(same_time_day_abs_p90, 3) if same_time_day_abs_p90 is not None else None,\n        "same_time_vwap_abs_p90": round(same_time_vwap_abs_p90, 3) if same_time_vwap_abs_p90 is not None else None,\n        "same_time_ret15_abs_p90": round(same_time_ret15_abs_p90, 3) if same_time_ret15_abs_p90 is not None else None,\n        "amplitude_regime": amplitude_regime,\n'''
    s = must(s, old, new, "return same time stats")

    # Apply dynamic thresholds before the official score engine runs.
    old = '''    market_live = intraday_index_snapshot()\n    rows = _attach_relative_multitimeframe(rows, close_map, market, market_live)\n    sector_rotation = build_sector_rotation(rows)\n'''
    new = '''    market_live = intraday_index_snapshot()\n    rows = _attach_relative_multitimeframe(rows, close_map, market, market_live)\n    rows = _refresh_dynamic_thresholds(rows, close_map)\n    sector_rotation = build_sector_rotation(rows)\n'''
    s = must(s, old, new, "refresh dynamic main")

    # Flow score good-range thresholds use the same per-stock profile.
    old = '''    amp_regime = str(r.get("amplitude_regime") or "中性")\n    amp_multiple = r.get("amplitude_multiple")\n    amp_ready = bool(r.get("amp_baseline_ready"))\n    range_pos = float(r.get("range_position_pct") or 50)\n'''
    new = '''    amp_regime = str(r.get("amplitude_regime") or "中性")\n    amp_multiple = r.get("amplitude_multiple")\n    amp_ready = bool(r.get("amp_baseline_ready"))\n    range_pos = float(r.get("range_position_pct") or 50)\n    dyn = r.get("dynamic_thresholds") or {}\n    day_good_high = float(dyn.get("day_good_high_pct") or 6.5)\n    ret15_good_high = float(dyn.get("ret15_good_high_pct") or 2.5)\n    pace_hot = float(dyn.get("pace_hot_x") or 5.0)\n'''
    s = must(s, old, new, "score dynamic vars")
    s = s.replace('''    elif 3.5 <= pace <= 5:\n        pace_points = 10.0\n''', '''    elif 3.5 <= pace <= pace_hot:\n        pace_points = 10.0\n''', 1)
    s = s.replace('''    if 0.2 <= ret15 <= 2.5:\n        flow += 6\n''', '''    if 0.2 <= ret15 <= ret15_good_high:\n        flow += 6\n''', 1)
    s = s.replace('''    if 0.5 <= day <= 6.5:\n        flow += 4\n''', '''    if 0.5 <= day <= day_good_high:\n        flow += 4\n''', 1)

    s = s.replace('''        "relative_multiframe_version": "1.0",\n        "score_formula": {"mode": "intraday_execution"''', '''        "relative_multiframe_version": "1.0",\n        "dynamic_threshold_version": "1.0",\n        "score_formula": {"mode": "intraday_execution"''', 1)
    s = s.replace('''        "relative_multiframe_version": "1.0",\n    })\n    dump("status.json", status)\n    print("intraday done", len(rows))\n''', '''        "relative_multiframe_version": "1.0",\n        "dynamic_threshold_version": "1.0",\n        "version": "1.5.27-free",\n    })\n    dump("status.json", status)\n    print("intraday done", len(rows))\n''', 1)
    # Older intraday version assignments should not downgrade status.
    s = s.replace('"version": "1.5.25-free",', '"version": "1.5.27-free",')

    write(p, s)


def patch_bridge():
    p = "scripts/bridge_intraday.py"
    s = read(p)
    old = '''    out_rows = bd._attach_multitimeframe_context(out_rows, close_map, bd.load_json("hourly.json", {}))\n    market_live = bd.intraday_index_snapshot()\n    out_rows = bd._attach_relative_multitimeframe(out_rows, close_map, close_market, market_live)\n    rotation = bd.build_sector_rotation(out_rows)\n'''
    new = '''    out_rows = bd._attach_multitimeframe_context(out_rows, close_map, bd.load_json("hourly.json", {}))\n    market_live = bd.intraday_index_snapshot()\n    out_rows = bd._attach_relative_multitimeframe(out_rows, close_map, close_market, market_live)\n    out_rows = bd._refresh_dynamic_thresholds(out_rows, close_map)\n    rotation = bd.build_sector_rotation(out_rows)\n'''
    s = must(s, old, new, "bridge dynamic refresh")
    s = s.replace('''        "relative_multiframe_version": "1.0",\n        "rows": out_rows,\n''', '''        "relative_multiframe_version": "1.0",\n        "dynamic_threshold_version": "1.0",\n        "rows": out_rows,\n''', 1)
    s = s.replace('''        "relative_multiframe_version": "1.0",\n        "version": "1.5.25-free",\n''', '''        "relative_multiframe_version": "1.0",\n        "dynamic_threshold_version": "1.0",\n        "version": "1.5.27-free",\n''', 1)
    write(p, s)


def patch_ui():
    p = "docs/index.html"
    s = read(p)
    s = s.replace("Free Edition v1.5.26｜庫存決策層＋多時間框架", "Free Edition v1.5.27｜Step 6 個股動態門檻", 1)
    # Show the dynamic threshold source inside the existing amplitude/technical explanation.
    old = '''function portfolioDecision(r,h){'''
    fn = r'''function dynamicThresholdHTML(r){
 const d=r?.dynamic_thresholds||{}; if(!Object.keys(d).length)return "";
 const mode=d.mode==="personalized"?"✅ 個股化":d.mode==="warming"?"🟡 暖機中":"⚪ 固定門檻";
 const ev=(d.evidence||[]).join("＋")||"舊版固定值";
 return `<div class="mtf-note"><b>🎚️ 動態門檻 ${mode}</b>　漲幅 ${num(d.day_hot_pct,1)}%｜VWAP ${num(d.vwap_hot_pct,1)}%｜15分 ${num(d.ret15_hot_pct,1)}%｜量速 ${num(d.pace_hot_x,1)}x<br><span class="muted">依據：${escHTML(ev)}；ATR14 ${d.atr14_pct==null?"—":num(d.atr14_pct,1)+"%"}，同時段樣本 ${d.sample_days??0} 日。只改門檻，不改 30/25/15/20/10 權重。</span></div>`;
}
'''
    if "function dynamicThresholdHTML" not in s:
        s = must(s, old, fn + old, "dynamic UI function")

    # Existing card includes amplitudeHTML; append dynamic threshold block after it wherever rendered.
    if '${dynamicThresholdHTML(r)}' not in s:
        target = '${amplitudeHTML(r)}'
        if target in s:
            s = s.replace(target, target + '${dynamicThresholdHTML(r)}')
        else:
            # Fallback: portfolio card always renders and can surface threshold data there.
            s = s.replace('${portfolioDecisionHTML(r,h)}', '${dynamicThresholdHTML(r)}${portfolioDecisionHTML(r,h)}', 1)

    s = s.replace('./hourly.js?v=1526', './hourly.js?v=1527').replace('./sw.js?v=1526', './sw.js?v=1527').replace('dogsonSwReloaded1526', 'dogsonSwReloaded1527')
    write(p, s)


def patch_sw_status():
    p = "docs/sw.js"
    s = read(p).replace("dogson-free-v1526", "dogson-free-v1527").replace('./hourly.js?v=1526', './hourly.js?v=1527')
    write(p, s)
    p = "docs/data/status.json"
    d = json.loads(read(p))
    d["version"] = "1.5.27-free"
    d["dynamic_threshold_version"] = "1.0"
    write(p, json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    patch_build_data()
    patch_bridge()
    patch_ui()
    patch_sw_status()
    print("v1.5.27 Step 6 dynamic threshold applied")
