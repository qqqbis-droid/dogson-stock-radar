#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.30 — 原始「波段決策雷達」構想補完版。

補齊：
1) 籌碼力度：外資3日淨買超 / 個股20日平均成交股數。
2) 舒服買點型態：量縮回踩 / 回踩承接 / 量增上攻。
3) 今日累積變化：不是只看上一個5分鐘快照。
4) 庫存「可考慮加碼」＋持有狀態方向。
5) Step 6 前端三燈正式改讀個股動態門檻。
6) 歷史突破量自身基準：最近最多20次20日突破事件。
7) Step 7 保存上述特徵並新增組合研究欄位。

不新增總分桶，不改盤中30/25/15/20/10，也不改盤後基準50/25/15/10。
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
        raise SystemExit(f"v1.5.30 missing marker: {label}")
    return text.replace(old, new, count)


COMPLETION_HELPERS = r'''
def _chip_intensity_fields(r):
    """跨股票可比的法人力度；不新增chip score權重。"""
    avg_vol = _finite(r.get("avg_volume20_shares"))
    f3 = _finite(r.get("foreign_3d_net"))
    trust = _finite(r.get("trust_net_latest"))
    fint = (f3 / avg_vol * 100.0) if avg_vol and avg_vol > 0 and f3 is not None else None
    tint = (trust / avg_vol * 100.0) if avg_vol and avg_vol > 0 and trust is not None else None
    if fint is None:
        label = "資料待補"
    elif fint >= 20:
        label = "強力累積"
    elif fint >= 8:
        label = "明顯累積"
    elif fint >= 2:
        label = "溫和累積"
    elif fint <= -20:
        label = "強力調節"
    elif fint <= -8:
        label = "明顯調節"
    elif fint <= -2:
        label = "溫和調節"
    else:
        label = "中性"
    return {
        "chip_intensity_version": "1.0",
        "foreign_3d_intensity_pct": round(fint, 2) if fint is not None else None,
        "trust_latest_intensity_pct": round(tint, 2) if tint is not None else None,
        "chip_intensity_label": label,
        "chip_intensity_basis": "外資3日淨買超股數 ÷ 20日平均成交股數",
    }


def _execution_pattern_fields(r):
    """辨識舒服進場型態；是決策層，不形成新的100分桶。"""
    close = _finite(r.get("close")) or 0.0
    vwap = _finite(r.get("vwap")) or 0.0
    vwap_dist = _finite(r.get("vwap_dist")) or 0.0
    ret15 = _finite(r.get("ret15")) or 0.0
    recent = _finite(r.get("recent_turnover"))
    previous = _finite(r.get("previous_turnover"))
    pace = _finite(r.get("pace")) or 0.0
    trend = bool(r.get("trend5"))
    break3 = bool(r.get("break3"))
    ratio = (recent / previous) if recent is not None and previous and previous > 0 else None
    above = bool(vwap > 0 and close >= vwap)
    near = bool(vwap > 0 and -0.8 <= vwap_dist <= 1.5)

    attack = bool(
        above and (break3 or trend) and ret15 >= 0.15
        and ((ratio is not None and ratio >= 1.12) or pace >= 1.35)
    )
    shrink_pullback = bool(
        near and -1.0 <= ret15 <= 0.45 and (trend or above)
        and ratio is not None and ratio <= 0.88
    )
    support_hold = bool(
        near and above and -0.35 <= ret15 <= 0.8 and trend
        and not attack and not shrink_pullback
    )

    if attack:
        pattern, strength = "量增上攻", 85
        reasons = ["價格在VWAP上", "5分結構向上", "近段成交金額放大"]
    elif shrink_pullback:
        pattern, strength = "量縮回踩", 82
        reasons = ["價格回到VWAP附近", "拉回幅度受控", "回踩成交金額收縮"]
    elif support_hold:
        pattern, strength = "回踩承接", 72
        reasons = ["VWAP附近守住", "5分短均未破", "15分鐘沒有明顯轉弱"]
    else:
        pattern, strength = "中性"
        strength = 40 if above else 25
        reasons = []
    return {
        "execution_pattern_version": "1.0",
        "execution_pattern": pattern,
        "execution_pattern_strength": strength,
        "turnover_acceleration": round(ratio, 3) if ratio is not None else None,
        "execution_pattern_reasons": reasons,
    }


def _attach_completion_context(rows, close_map=None):
    close_map = close_map or {}
    for r in rows or []:
        d = close_map.get(str(r.get("code") or "")) or {}
        for key in ("avg_volume20_shares", "foreign_3d_intensity_pct", "trust_latest_intensity_pct",
                    "chip_intensity_label", "chip_intensity_basis", "breakout_volume_profile"):
            if r.get(key) is None and d.get(key) is not None:
                r[key] = d.get(key)
        # If this is a close row, calculate intensity from itself; intraday normally inherits it.
        if r.get("avg_volume20_shares") is not None and r.get("foreign_3d_net") is not None:
            r.update(_chip_intensity_fields(r))
        if r.get("vwap") is not None:
            r.update(_execution_pattern_fields(r))
    return rows


def _build_today_cumulative_change(rows, history_obj=None):
    """開盤至目前的累積方向；validation_history只含已發生的舊快照。"""
    history_obj = history_obj if isinstance(history_obj, dict) else load_json("validation_history.json", {})
    scans = history_obj.get("intraday") or []
    dates = [str(r.get("quote_date") or r.get("date") or "")[:10] for r in rows or []]
    dates = [d for d in dates if len(d) == 10]
    trade_date = max(dates) if dates else None
    today = [s for s in scans if str(s.get("date") or "") == str(trade_date)]
    today.sort(key=lambda x: str(x.get("key") or x.get("time") or ""))
    counts = {"new_setup":0, "new_start":0, "turn_strong":0, "turn_weak":0, "to_overheat":0}
    out = {"version":"1.0", "ready":False, "trade_date":trade_date, "scan_count":len(today)+1,
           "counts":counts, "events":[], "reason":"等待今日第二個歷史快照"}
    for r in rows or []:
        r["today_score_delta"] = None
        r["today_pace_delta"] = None
        r["today_stage_start"] = None
        r["today_direction"] = "待累積"
    if not today:
        return out

    first = today[0]
    first_map = {str(x.get("code")): x for x in (first.get("rows") or []) if x.get("code")}
    strong = {"蓄勢待發", "剛啟動", "回踩承接", "趨勢持有"}
    weak = {"轉弱警戒", "結構失效"}
    events = []
    for r in rows or []:
        code = str(r.get("code") or "")
        p = first_map.get(code)
        if not p:
            continue
        cs = _finite(r.get("intraday_score", r.get("score"))) or 0.0
        ps = _finite(p.get("score")) or 0.0
        cp = _finite(r.get("pace")) or 0.0
        pp = _finite(p.get("pace")) or 0.0
        delta = cs - ps
        pdelta = cp - pp
        cur_stage = str(r.get("category") or "觀察")
        old_stage = str(p.get("category") or "觀察")
        r["today_score_delta"] = round(delta, 1)
        r["today_pace_delta"] = round(pdelta, 2)
        r["today_stage_start"] = old_stage
        if (cur_stage in weak and old_stage not in weak) or delta <= -10:
            direction = "惡化"
        elif (cur_stage in strong and old_stage not in strong) or delta >= 10:
            direction = "改善"
        elif delta >= 4:
            direction = "小幅改善"
        elif delta <= -4:
            direction = "小幅降溫"
        else:
            direction = "持平"
        r["today_direction"] = direction

        labels = []
        if cur_stage == "蓄勢待發" and old_stage != "蓄勢待發":
            counts["new_setup"] += 1; labels.append("🌱 新進蓄勢")
        if cur_stage == "剛啟動" and old_stage != "剛啟動":
            counts["new_start"] += 1; labels.append("🔥 新進剛啟動")
        if cur_stage in strong and old_stage not in strong:
            counts["turn_strong"] += 1
        if cur_stage in weak and old_stage not in weak:
            counts["turn_weak"] += 1; labels.append("⚠️ 今日轉弱")
        if cur_stage == "過熱不追" and old_stage != "過熱不追":
            counts["to_overheat"] += 1; labels.append("🚫 今日轉過熱")
        if labels or abs(delta) >= 8:
            events.append({"code":code, "name":r.get("name"), "label":"／".join(labels) if labels else ("⬆️ 今日改善" if delta>0 else "⬇️ 今日降溫"),
                           "score_delta":round(delta,1), "pace_delta":round(pdelta,2),
                           "stage_start":old_stage, "stage":cur_stage, "direction":direction})
    events.sort(key=lambda e: (abs(float(e.get("score_delta") or 0)), abs(float(e.get("pace_delta") or 0))), reverse=True)
    out.update({"ready":True, "reason":"從今日最早保存快照比較到目前", "events":events[:40]})
    return out

'''


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)
    s = s.replace("犬子老師飆股雷達 Free Edition v1.5.29", "犬子老師飆股雷達 Free Edition v1.5.30", 1)

    # Daily self-baselines: 20d average shares + up to 20 historical breakout events.
    s = must(s,
        '        "avg_turnover20": float((c*v).rolling(20).mean().iloc[-1]),\n        "date": str(x.index[-1].date()),',
        '        "avg_turnover20": float((c*v).rolling(20).mean().iloc[-1]),\n        "avg_volume20_shares": float(v.rolling(20).mean().iloc[-1]),\n        "date": str(x.index[-1].date()),',
        "avg volume shares")

    old = '''    hist_ret = ret1.tail(60).dropna().abs()\n    hist_vx = vx.tail(60).dropna()\n    row["dynamic_profile"] = {'''
    new = '''    hist_ret = ret1.tail(60).dropna().abs()\n    hist_vx = vx.tail(60).dropna()\n    # 最近最多20次「20日突破」事件，建立這檔股票自己的突破量基準。\n    breakout_mask = (c > p20) & p20.notna()\n    breakout_event_volumes = v[breakout_mask].iloc[:-1].tail(20).dropna()\n    breakout_event_vx = vx[breakout_mask].iloc[:-1].tail(20).dropna()\n    breakout_avg_volume = float(breakout_event_volumes.mean()) if len(breakout_event_volumes) >= 3 else None\n    breakout_vx_median = float(breakout_event_vx.median()) if len(breakout_event_vx) >= 3 else None\n    breakout_vx_p75 = float(breakout_event_vx.quantile(.75)) if len(breakout_event_vx) >= 3 else None\n    current_vs_breakout_avg = (float(v.iloc[-1]) / breakout_avg_volume) if breakout_avg_volume and breakout_avg_volume > 0 else None\n    row["breakout_volume_profile"] = {\n        "version":"1.0", "ready":bool(len(breakout_event_volumes) >= 3),\n        "sample_events":int(len(breakout_event_volumes)),\n        "event_avg_volume_shares":round(breakout_avg_volume, 0) if breakout_avg_volume is not None else None,\n        "event_vol_x_median":round(breakout_vx_median, 3) if breakout_vx_median is not None else None,\n        "event_vol_x_p75":round(breakout_vx_p75, 3) if breakout_vx_p75 is not None else None,\n        "current_volume_vs_event_avg":round(current_vs_breakout_avg, 3) if current_vs_breakout_avg is not None else None,\n        "current_is_breakout":bool(row["break20"]),\n    }\n    row["dynamic_profile"] = {'''
    s = must(s, old, new, "breakout event baseline")
    s = must(s,
        '        "vol_x_p90": round(float(hist_vx.quantile(.90)), 3) if len(hist_vx) >= 10 else None,\n    }',
        '        "vol_x_p90": round(float(hist_vx.quantile(.90)), 3) if len(hist_vx) >= 10 else None,\n        "breakout_event_count": int(len(breakout_event_volumes)),\n        "breakout_vol_x_median": round(breakout_vx_median, 3) if breakout_vx_median is not None else None,\n    }',
        "dynamic breakout fields")

    # Intraday execution pattern uses recent-vs-previous turnover windows.
    old = '''    else:\n        recent_turnover = None\n        previous_turnover = None\n        rotation_window_min = None\n\n    score = 0'''
    new = '''    else:\n        recent_turnover = None\n        previous_turnover = None\n        rotation_window_min = None\n\n    _pattern_seed = {\n        "close":cur, "vwap":vwap, "vwap_dist":vwap_dist, "ret15":ret15, "pace":pace,\n        "recent_turnover":recent_turnover, "previous_turnover":previous_turnover,\n        "trend5":trend, "break3":b3,\n    }\n    _pattern = _execution_pattern_fields(_pattern_seed)\n\n    score = 0'''
    s = must(s, old, new, "execution pattern seed")
    s = must(s,
        '        "rotation_window_min": rotation_window_min,\n        "technical_score": max(0, min(50, round(score, 1))),',
        '        "rotation_window_min": rotation_window_min,\n        **_pattern,\n        "technical_score": max(0, min(50, round(score, 1))),',
        "execution pattern return")

    # Insert shared completion helpers before Step 6 helper functions.
    if "def _chip_intensity_fields(r):" not in s:
        s = must(s, "def _finite(v):", COMPLETION_HELPERS + "def _finite(v):", "completion helpers")

    # Stage evidence understands the new execution pattern, without adding score.
    s = must(s,
        '        rel_mtf_supportive = rel_mtf_status in {"LEADING", "IMPROVING"}\n\n        invalid_flags = [',
        '        rel_mtf_supportive = rel_mtf_status in {"LEADING", "IMPROVING"}\n        execution_pattern = str(r.get("execution_pattern") or "中性")\n\n        invalid_flags = [',
        "stage reads execution pattern")
    s = must(s,
        '            if rel_mtf_supportive:\n                launch_signals.append(rel_mtf.get("label") or "多時框相對強弱改善")\n            r["stage_signals"] = launch_signals[:5]',
        '            if rel_mtf_supportive:\n                launch_signals.append(rel_mtf.get("label") or "多時框相對強弱改善")\n            if execution_pattern == "量增上攻":\n                launch_signals.append("量增上攻型態")\n            r["stage_signals"] = launch_signals[:5]',
        "launch pattern evidence")
    s = must(s,
        '            r["stage_signals"] = ["靠近VWAP", "短線結構未破", "相對市場未明顯轉弱"]\n            return',
        '            pull_signals = ["靠近VWAP", "短線結構未破", "相對市場未明顯轉弱"]\n            if execution_pattern in {"量縮回踩", "回踩承接"}:\n                pull_signals.insert(0, execution_pattern)\n            r["stage_signals"] = pull_signals[:4]\n            return',
        "pullback pattern evidence")
    s = must(s,
        '            (rel_mtf_supportive, rel_mtf.get("label") or "多時框相對強弱改善"),\n        ]',
        '            (rel_mtf_supportive, rel_mtf.get("label") or "多時框相對強弱改善"),\n            (execution_pattern in {"量縮回踩", "回踩承接", "量增上攻"}, f"{execution_pattern}型態已形成"),\n        ]',
        "setup pattern evidence")

    # Daily stage also surfaces chip intensity and breakout-event volume evidence.
    s = must(s,
        '    break20 = bool(r.get("break20"))\n\n    below20 =',
        '    break20 = bool(r.get("break20"))\n    chip_intensity = _finite(r.get("foreign_3d_intensity_pct"))\n    breakout_profile = r.get("breakout_volume_profile") or {}\n\n    below20 =',
        "close stage reads intensity")
    s = must(s,
        '        r["stage_signals"] = ["20日突破" if break20 else "3日平台突破", f"量比{vol:.1f}x", f"距20MA {dist20:+.1f}%"]\n        return',
        '        launch_signals = ["20日突破" if break20 else "3日平台突破", f"量比{vol:.1f}x", f"距20MA {dist20:+.1f}%"]\n        if chip_intensity is not None and chip_intensity >= 5:\n            launch_signals.append(f"外資3日力度 {chip_intensity:+.1f}%")\n        if breakout_profile.get("ready") and breakout_profile.get("current_volume_vs_event_avg") is not None:\n            launch_signals.append(f"突破量/歷史突破量 {float(breakout_profile.get('current_volume_vs_event_avg')):.2f}x")\n        r["stage_signals"] = launch_signals[:5]\n        return',
        "close launch intensity")
    s = must(s,
        '    add_setup(sec >= 5.0, 5, "族群已有共振")\n',
        '    add_setup(sec >= 5.0, 5, "族群已有共振")\n    add_setup(chip_intensity is not None and chip_intensity >= 2, 5, f"外資3日力度 {chip_intensity:+.1f}%" if chip_intensity is not None else "外資力度")\n',
        "setup chip intensity")

    # Attach chip intensity after chips are merged into close rows.
    s = must(s,
        '        r.update(chip)\n        r["chip_score"] = cs\n        r["chip_coverage_pct"] = coverage\n\n    rows = add_component_scores',
        '        r.update(chip)\n        r["chip_score"] = cs\n        r["chip_coverage_pct"] = coverage\n        r.update(_chip_intensity_fields(r))\n\n    rows = add_component_scores',
        "attach close intensity")

    # Intraday inherits daily intensity / breakout profile from the last completed close.
    s = must(s,
        '                    "foreign_3d_net": prev.get("foreign_3d_net"),\n                    "sbl_3down": prev.get("sbl_3down"),',
        '                    "foreign_3d_net": prev.get("foreign_3d_net"),\n                    "foreign_3d_intensity_pct": prev.get("foreign_3d_intensity_pct"),\n                    "trust_latest_intensity_pct": prev.get("trust_latest_intensity_pct"),\n                    "chip_intensity_label": prev.get("chip_intensity_label"),\n                    "chip_intensity_basis": prev.get("chip_intensity_basis"),\n                    "avg_volume20_shares": prev.get("avg_volume20_shares"),\n                    "breakout_volume_profile": prev.get("breakout_volume_profile"),\n                    "sbl_3down": prev.get("sbl_3down"),',
        "inherit completion fields")

    # Refresh completion context after MIS overlay and before scoring/stage.
    s = must(s,
        '    rows = _attach_relative_multitimeframe(rows, close_map, market, market_live)\n    rows = _refresh_dynamic_thresholds(rows, close_map)\n    sector_rotation = build_sector_rotation(rows)',
        '    rows = _attach_relative_multitimeframe(rows, close_map, market, market_live)\n    rows = _refresh_dynamic_thresholds(rows, close_map)\n    rows = _attach_completion_context(rows, close_map)\n    sector_rotation = build_sector_rotation(rows)',
        "refresh completion context")

    # Cumulative today summary is separate from 5-minute delta radar.
    s = must(s,
        '    change_radar = build_change_radar(rows, sector_rotation, previous_intraday)\n\n    dump("intraday.json", {',
        '    change_radar = build_change_radar(rows, sector_rotation, previous_intraday)\n    change_radar["today_summary"] = _build_today_cumulative_change(rows)\n\n    dump("intraday.json", {',
        "today cumulative change")

    # Version/status markers. Also fixes old close status that still said v1.5.17.
    s = s.replace('"version": "1.5.29-free"', '"version": "1.5.30-free"')
    s = s.replace('"version": "1.5.17-free"', '"version": "1.5.30-free"')
    s = must(s,
        '        "dynamic_threshold_version": "1.0",\n        "score_formula":',
        '        "dynamic_threshold_version": "1.1",\n        "vision_completion_version": "1.0",\n        "score_formula":',
        "intraday version markers")
    s = s.replace('"dynamic_threshold_version": "1.0",\n        "version": "1.5.30-free",', '"dynamic_threshold_version": "1.1",\n        "vision_completion_version": "1.0",\n        "version": "1.5.30-free",')
    write(p, s)


def patch_bridge():
    p = "scripts/bridge_intraday.py"
    s = read(p)
    # Bridge can change current quote fields; refresh completion patterns afterwards.
    old = '    out_rows = bd._attach_relative_multitimeframe(out_rows, close_map, close_market, market_live)\n    rotation = bd.build_sector_rotation(out_rows)'
    new = '    out_rows = bd._attach_relative_multitimeframe(out_rows, close_map, close_market, market_live)\n    out_rows = bd._refresh_dynamic_thresholds(out_rows, close_map)\n    out_rows = bd._attach_completion_context(out_rows, close_map)\n    rotation = bd.build_sector_rotation(out_rows)'
    if old in s:
        s = s.replace(old, new, 1)
    # Existing bridge may already refresh dynamic thresholds; insert only completion if needed.
    if 'bd._attach_completion_context(out_rows, close_map)' not in s:
        marker = '    out_rows = bd._refresh_dynamic_thresholds(out_rows, close_map)\n'
        s = must(s, marker, marker + '    out_rows = bd._attach_completion_context(out_rows, close_map)\n', "bridge completion")
    # Today cumulative summary must be regenerated after official MIS bridge.
    if 'today_summary' not in s:
        marker = '    change_radar = bd.build_change_radar(out_rows, rotation, previous_obj)\n'
        s = must(s, marker, marker + '    change_radar["today_summary"] = bd._build_today_cumulative_change(out_rows)\n', "bridge today summary")
    s = s.replace('"version": "1.5.29-free"', '"version": "1.5.30-free"')
    write(p, s)


def patch_validation():
    p = "scripts/build_validation.py"
    s = read(p)
    s = must(s,
        '        "weights": r.get("swing_weights") or BASE_WEIGHTS,\n    }',
        '        "weights": r.get("swing_weights") or BASE_WEIGHTS,\n        "foreign_3d_intensity_pct": f(r.get("foreign_3d_intensity_pct")),\n        "chip_intensity_label": r.get("chip_intensity_label"),\n        "breakout_volume_profile": r.get("breakout_volume_profile") or {},\n    }',
        "validation close completion fields")
    s = must(s,
        '        "dynamic_thresholds": r.get("dynamic_thresholds") or {},\n    }',
        '        "dynamic_thresholds": r.get("dynamic_thresholds") or {},\n        "foreign_3d_intensity_pct": f(r.get("foreign_3d_intensity_pct")),\n        "chip_intensity_label": r.get("chip_intensity_label"),\n        "execution_pattern": r.get("execution_pattern"),\n        "execution_pattern_strength": f(r.get("execution_pattern_strength")),\n        "turnover_acceleration": f(r.get("turnover_acceleration")),\n        "today_direction": r.get("today_direction"),\n        "today_score_delta": f(r.get("today_score_delta")),\n        "relative_strength_pct": f((r.get("intraday_components") or {}).get("relative_strength_pct")),\n    }',
        "validation intraday completion fields")
    s = must(s,
        '                "components": r.get("components") or {}, "returns": {},\n            }',
        '                "components": r.get("components") or {}, "returns": {},\n                "foreign_3d_intensity_pct": r.get("foreign_3d_intensity_pct"),\n                "chip_intensity_label": r.get("chip_intensity_label"),\n                "breakout_volume_profile": r.get("breakout_volume_profile") or {},\n            }',
        "outcome completion fields")

    # Research layer: which stage + chip intensity + breakout-volume combinations work after 5d.
    marker = '    high_quality = stats([r for r in matured5 if f(r.get("score"), 0) >= 70])\n'
    combo = '''    high_quality = stats([r for r in matured5 if f(r.get("score"), 0) >= 70])\n\n    combo_groups = {}\n    for r in matured5:\n        bp = r.get("breakout_volume_profile") or {}\n        bvr = f(bp.get("current_volume_vs_event_avg"))\n        btier = "突破量偏強" if bvr is not None and bvr >= 1.2 else "突破量正常" if bvr is not None and bvr >= 0.8 else "突破量偏弱" if bvr is not None else "突破量待補"\n        key = "｜".join([str(r.get("category") or "觀察"), str(r.get("chip_intensity_label") or "力度待補"), btier])\n        combo_groups.setdefault(key, []).append(r)\n    combination_5d = []\n    for key, items in combo_groups.items():\n        z = stats(items)\n        if z["n"] >= 5:\n            combination_5d.append({"combination":key, **z})\n    combination_5d.sort(key=lambda x: (x.get("n",0), x.get("median_return") or -999), reverse=True)\n'''
    s = must(s, marker, combo, "combination research")
    s = must(s,
        '        "stage_5d": stage,\n        "calibration": calibration,',
        '        "stage_5d": stage,\n        "combination_5d": combination_5d[:30],\n        "calibration": calibration,',
        "combination report")
    write(p, s)


def patch_daytrade():
    p = "scripts/build_daytrade.py"
    s = read(p)
    # Daytrade remains isolated, but can read the new execution pattern as explanation/context.
    s = s.replace('"daytrade_version": "1.0",', '"daytrade_version": "1.1",', 1)
    s = must(s,
        '        "daytrade_dynamic_mode": dyn["mode"],\n',
        '        "daytrade_dynamic_mode": dyn["mode"],\n        "source_execution_pattern": source.get("execution_pattern"),\n        "source_turnover_acceleration": source.get("turnover_acceleration"),\n',
        "daytrade source pattern")
    s = s.replace('"version": "1.5.29-free"', '"version": "1.5.30-free"')
    write(p, s)


def patch_ui():
    p = "docs/index.html"
    s = read(p)
    s = s.replace("Free Edition v1.5.29｜Step 8 獨立當沖模式", "Free Edition v1.5.30｜原始構想補完版", 1)

    css = r'''
/* v1.5.30 original vision completion */
.completionbox{margin-top:10px;border:1px solid #33465d;background:#0e151f;border-radius:12px;padding:9px}.completiontop{display:flex;justify-content:space-between;gap:8px;align-items:center}.completiontitle{font-size:10px;color:#9ba5b6;font-weight:850}.completionvalue{font-size:12px;font-weight:900}.completiongrid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:7px}.completioncell{background:#101923;border:1px solid #28384b;border-radius:9px;padding:7px}.completionv{font-size:11px;font-weight:900}.completionl{font-size:9px;color:var(--muted);margin-top:3px}.todaygrid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:9px}.todayitem{background:#0e141c;border:1px solid #293442;border-radius:10px;padding:8px}.todayv{font-size:13px;font-weight:900}.todayl{font-size:9px;color:var(--muted);margin-top:3px}.portfolio-decision-badge.add{background:#173527;color:#a5efbf}@media(max-width:520px){.todaygrid{grid-template-columns:1fr 1fr}.completiongrid{grid-template-columns:1fr}}
'''
    if ".completionbox{" not in s:
        s = must(s, "</style>", css + "\n</style>", "completion css")

    # Dynamic threshold display includes historical breakout-event volume baseline.
    old = ' return `<div class="mtf-note"><b>🎚️ 動態門檻 ${mode}</b>　漲幅 ${num(d.day_hot_pct,1)}%｜VWAP ${num(d.vwap_hot_pct,1)}%｜15分 ${num(d.ret15_hot_pct,1)}%｜量速 ${num(d.pace_hot_x,1)}x<br><span class="muted">依據：${escHTML(ev)}；ATR14 ${d.atr14_pct==null?"—":num(d.atr14_pct,1)+"%"}，同時段樣本 ${d.sample_days??0} 日。只改門檻，不改 30/25/15/20/10 權重。</span></div>`;'
    new = ' const bp=r?.breakout_volume_profile||{};const bpt=bp.ready?`｜歷史突破 ${bp.sample_events} 次，今日量/突破均量 ${bp.current_volume_vs_event_avg==null?"—":num(bp.current_volume_vs_event_avg,2)+"x"}`:"｜突破事件基準暖機中";\n return `<div class="mtf-note"><b>🎚️ 動態門檻 ${mode}</b>　漲幅 ${num(d.day_hot_pct,1)}%｜VWAP ${num(d.vwap_hot_pct,1)}%｜15分 ${num(d.ret15_hot_pct,1)}%｜量速 ${num(d.pace_hot_x,1)}x<br><span class="muted">依據：${escHTML(ev)}；ATR14 ${d.atr14_pct==null?"—":num(d.atr14_pct,1)+"%"}，同時段樣本 ${d.sample_days??0} 日${bpt}。只改門檻，不改原權重。</span></div>`;'
    s = must(s, old, new, "dynamic UI breakout baseline")

    # New card context block for chip intensity + execution pattern + today direction.
    marker = 'function portfolioDecision(r,h){'
    fn = r'''function completionContextHTML(r){
 if(mode==="daytrade")return "";
 const pattern=r?.execution_pattern||"中性",acc=r?.turnover_acceleration;
 const intensity=r?.foreign_3d_intensity_pct,label=r?.chip_intensity_label||"資料待補";
 const dir=r?.today_direction||"待累積",sd=r?.today_score_delta,pd=r?.today_pace_delta;
 const bp=r?.breakout_volume_profile||{};
 return `<div class="completionbox"><div class="completiontop"><div class="completiontitle">🧩 原始構想補完層</div><div class="completionvalue">${escHTML(pattern)}</div></div><div class="completiongrid"><div class="completioncell"><div class="completionv">外資3日力度 ${intensity==null?"—":signed(intensity,1)}</div><div class="completionl">${escHTML(label)}｜相對個股20日平均成交量</div></div><div class="completioncell"><div class="completionv">近段量能 ${acc==null?"—":num(acc,2)+"x"}</div><div class="completionl">${pattern==="量縮回踩"?"回踩量縮":pattern==="量增上攻"?"上攻放量":pattern==="回踩承接"?"支撐承接":"尚無明確執行型態"}</div></div><div class="completioncell"><div class="completionv">今日方向 ${escHTML(dir)}</div><div class="completionl">動能 ${sd==null?"—":signed(sd,0,"")}｜量速變化 ${pd==null?"—":signed(pd,2,"x")}</div></div><div class="completioncell"><div class="completionv">突破量基準 ${bp.ready?num(bp.sample_events,0)+"次":"暖機"}</div><div class="completionl">${bp.current_volume_vs_event_avg==null?"等待突破事件樣本":`今日量 / 歷史突破均量 ${num(bp.current_volume_vs_event_avg,2)}x`}</div></div></div></div>`;
}
'''
    if "function completionContextHTML" not in s:
        s = must(s, marker, fn + marker, "completion UI function")

    # Portfolio can now answer 留/加/減/出 and includes direction, not only current state.
    s = must(s,
        ' const manual=String(h?.reason_status||"valid");\n const reasons=[];',
        ' const manual=String(h?.reason_status||"valid");\n const pattern=String(r?.execution_pattern||"中性"),todayDir=String(r?.today_direction||"待累積");\n const todayDelta=+(r?.today_score_delta??r?.change_score_delta??0);\n const reasons=[];',
        "portfolio direction vars")
    s = must(s,
        ' const cooling=st==="回踩承接"||amp==="健康整理"||(mode==="intraday"&&score>0&&score<68&&h60.supportive===true&&String(daily.state||"")!=="WEAK");',
        ' const entry=mode==="intraday"?entryDecision(r,market):null;\n const addable=manual==="valid"&&h60.supportive===true&&String(daily.state||"")!=="WEAK"&&!relWeak&&!multiWeak&&(entry?.key==="green"||((st==="回踩承接"||st==="趨勢持有")&&["量縮回踩","回踩承接","量增上攻"].includes(pattern)))&&todayDir!=="惡化"&&todayDelta>=-3;\n if(addable){\n  reasons.push(h60.label||"60K波段結構仍支持");\n  reasons.push(pattern==="中性"?"盤中進場三燈重新轉綠":`${pattern}型態成立`);\n  if(todayDir!=="待累積")reasons.push(`今日方向：${todayDir}`);\n  if(rsState==="LEADING"||rsState==="IMPROVING")reasons.push(rs.label||"相對強弱支持");\n  return {key:"add",label:"🟢 可考慮加碼",head:"原持有理由仍在，而且重新出現較舒服的風險報酬位置",reasons:reasons.slice(0,4)};\n }\n const cooling=st==="回踩承接"||amp==="健康整理"||(mode==="intraday"&&score>0&&score<68&&h60.supportive===true&&String(daily.state||"")!=="WEAK");',
        "portfolio add decision")
    s = must(s,
        ' return `<div class="portfolio-decision"><div class="portfolio-decision-top"><div class="portfolio-decision-title">🧭 系統持有判讀</div><span class="portfolio-decision-badge ${d.key}">${d.label}</span></div><div class="portfolio-decision-head">${d.head}</div>',
        ' const direction=r?.today_direction&&r.today_direction!=="待累積"?`<div class="portfolio-decision-note">今日變化方向：<b>${escHTML(r.today_direction)}</b>${r.today_score_delta==null?"":`｜盤中動能較今日早段 ${signed(r.today_score_delta,0,"")}`}</div>`:"";\n return `<div class="portfolio-decision"><div class="portfolio-decision-top"><div class="portfolio-decision-title">🧭 系統持有判讀</div><span class="portfolio-decision-badge ${d.key}">${d.label}</span></div><div class="portfolio-decision-head">${d.head}</div>${direction}',
        "portfolio direction UI")

    # Portfolio summary shows actual decision distribution: 留 / 加 / 減 / 出.
    s = must(s,
        ' const pnl=coveredCost>0?coveredValue-coveredCost:null,pct=coveredCost>0?pnl/coveredCost*100:null;\n const pc=pnl>0?"pnl up":pnl<0?"pnl down":"pnl";',
        ' const pnl=coveredCost>0?coveredValue-coveredCost:null,pct=coveredCost>0?pnl/coveredCost*100:null;\n const pc=pnl>0?"pnl up":pnl<0?"pnl down":"pnl";\n const actions={add:0,hold:0,cool:0,pause:0,reduce:0,exit:0};\n entries.forEach(([code,h])=>{const r=currentHoldingRow(code);if(r){const d=portfolioDecision(r,h);actions[d.key]=(actions[d.key]||0)+1}});',
        "portfolio action summary")
    s = must(s,
        '<div class="portfolio-summary-sub">本機資料，不上傳 GitHub｜目前可取得行情 ${quoted}/${entries.length} 檔</div><div class="portfolio-summary-grid">',
        '<div class="portfolio-summary-sub">本機資料，不上傳 GitHub｜目前可取得行情 ${quoted}/${entries.length} 檔｜🟢可加 ${actions.add||0}｜✅續抱 ${(actions.hold||0)+(actions.cool||0)}｜🟠減碼 ${actions.reduce||0}｜❌退出 ${actions.exit||0}</div><div class="portfolio-summary-grid">',
        "portfolio summary decisions")

    # Entry radar finally uses Step 6 per-stock thresholds and explicit comfortable-entry pattern.
    s = must(s,
        ' const rsm=r?.relative_multiframe||{},rsStatus=String(rsm.status||"");\n const good=[],wait=[],block=[];',
        ' const rsm=r?.relative_multiframe||{},rsStatus=String(rsm.status||"");\n const dyn=r?.dynamic_thresholds||{},dayHot=+(dyn.day_hot_pct??8.5),vwapHot=+(dyn.vwap_hot_pct??4.5),paceHot=+(dyn.pace_hot_x??5),ret15Hot=+(dyn.ret15_hot_pct??4);\n const pattern=String(r?.execution_pattern||"中性"),patternGood=["量增上攻","量縮回踩","回踩承接"].includes(pattern);\n const good=[],wait=[],block=[];',
        "entry dynamic vars")
    s = s.replace('if(day>=8.5)block.push(`當日已漲 ${num(day,1)}%，追價風險高`);', 'if(day>=dayHot)block.push(`當日已漲 ${num(day,1)}%，超過個股門檻 ${num(dayHot,1)}%`);', 1)
    s = s.replace('if(vwap>4.5)block.push(`距 VWAP +${num(vwap,1)}%，延伸過遠`);', 'if(vwap>vwapHot)block.push(`距 VWAP +${num(vwap,1)}%，超過個股門檻 ${num(vwapHot,1)}%`);', 1)
    # Add pattern confirmation into green checklist, but it stays a gate not a score.
    s = must(s,
        ' if(stage==="轉弱警戒")wait.push("Stage 仍在轉弱警戒，需等5分K重新轉強");',
        ' if(patternGood)good.push(`舒服買點型態：${pattern}`);else wait.push("尚未形成量縮回踩／回踩承接／量增上攻型態");\n if(pace>paceHot)wait.unshift(`量速 ${num(pace,1)}x 超過個股門檻 ${num(paceHot,1)}x，先等降溫`);\n if(+(r?.ret15??0)>ret15Hot)wait.unshift(`15分鐘推進過快，超過個股門檻 ${num(ret15Hot,1)}%`);\n if(stage==="轉弱警戒")wait.push("Stage 仍在轉弱警戒，需等5分K重新轉強");',
        "entry pattern checklist")
    s = must(s,
        '&&stage!=="轉弱警戒"&&mtfGreenOk&&rsGreenOk;',
        '&&stage!=="轉弱警戒"&&mtfGreenOk&&rsGreenOk&&patternGood&&pace<=paceHot&&+(r?.ret15??0)<=ret15Hot;',
        "green comfortable pattern gate")

    # Today worth-noticing homepage: cumulative day + last 5m change + local portfolio weakness.
    old = ' const x=changeRadar||{},c=x.counts||{};\n const head=`<div class="changetop"><div><div class="changetitle">🚨 5分鐘變化雷達</div>'
    new = ' const x=changeRadar||{},c=x.counts||{},t=x.today_summary||{},tc=t.counts||{};\n const heldWeak=intraRows.filter(r=>held(r.code)&&["轉弱警戒","結構失效"].includes(stageKey(r.category))).length;\n const head=`<div class="changetop"><div><div class="changetitle">🚨 今天值得注意</div>'
    s = must(s, old, new, "today worth noticing header")
    s = must(s,
        ' if(!x.ready)return `<div class="changebox">${head}<div class="changesub" style="margin-top:8px">第一輪只建立基準，不會把隔夜差異誤判成盤中訊號。</div></div>`;',
        ' const today=`<div class="todaygrid"><div class="todayitem"><div class="todayv">🌱 ${tc.new_setup||0}</div><div class="todayl">今日新進蓄勢</div></div><div class="todayitem"><div class="todayv">🔥 ${tc.new_start||0}</div><div class="todayl">今日新進剛啟動</div></div><div class="todayitem"><div class="todayv">⚠️ ${heldWeak}</div><div class="todayl">我的庫存目前轉弱/失效</div></div><div class="todayitem"><div class="todayv">⬆️ ${tc.turn_strong||0}</div><div class="todayl">今日累積轉強</div></div><div class="todayitem"><div class="todayv">⬇️ ${tc.turn_weak||0}</div><div class="todayl">今日累積轉弱</div></div><div class="todayitem"><div class="todayv">🚫 ${tc.to_overheat||0}</div><div class="todayl">今日轉為過熱</div></div></div>`;\n if(!x.ready)return `<div class="changebox">${head}${today}<div class="changesub" style="margin-top:8px">5分鐘比較基準尚未建立；上方今日累積會隨 Step 7 歷史快照逐輪完整。</div></div>`;',
        "today summary grid")
    s = must(s,
        ' return `<div class="changebox">${head}${counts}${items}${sectors}</div>`;',
        ' const tev=(t.events||[]).slice(0,5);const todayEvents=tev.length?`<div class="sectorchange"><b>今日累積：</b><br>${tev.map(e=>`${e.label} ${e.name||""} ${e.code||""}｜動能 ${e.score_delta==null?"—":signed(e.score_delta,0,"")}｜量速 ${e.pace_delta==null?"—":signed(e.pace_delta,2,"x")}`).join("<br>")}</div>`:"";\n return `<div class="changebox">${head}${today}${counts}${items}${sectors}${todayEvents}</div>`;',
        "today cumulative events")

    # Render the completion block between lifecycle and entry radar.
    s = must(s,
        '  ${stageExplainHTML(r)}\n  ${mtfHTML(r)}',
        '  ${stageExplainHTML(r)}\n  ${completionContextHTML(r)}\n  ${mtfHTML(r)}',
        "render completion context")

    # Guide section documents the completed original vision.
    guide = '''    <div class="guide-title">⑲ 原始構想補完｜波段決策流程真正閉環</div>\n    <div class="guide-card">\n      <div class="guide-line"><span class="guide-key">籌碼力度</span>：外資3日淨買超 ÷ 個股20日平均成交股數，跨股票比較不再只看絕對張數。</div>\n      <div class="guide-line"><span class="guide-key">舒服進場型態</span>：正式辨識量縮回踩、回踩承接、量增上攻；盤中綠燈除了分數與多時間框架，也要有型態確認。</div>\n      <div class="guide-line"><span class="guide-key">今日累積變化</span>：首頁同時看今日新進蓄勢、新進剛啟動、累積轉強／轉弱、過熱與本機庫存警報，不只比較上一個5分鐘。</div>\n      <div class="guide-line"><span class="guide-key">庫存留／加／減／出</span>：持有管理新增「🟢可考慮加碼」，並把今日改善／降溫方向納入判讀。</div>\n      <div class="guide-line"><span class="guide-key">突破事件自身基準</span>：保存最近最多20次20日突破事件的成交量，顯示本次突破量相對自己歷史突破均量。</div>\n      <div class="guide-line"><span class="guide-key">歷史組合驗證</span>：Step 7 同步保存上述特徵，後續可比較「Stage＋籌碼力度＋突破量」5日結果。</div>\n      <div class="guide-tip">這些都是決策層或基準層；原本盤中30/25/15/20/10與盤後基準50/25/15/10沒有被另加一桶分數。</div>\n    </div>\n\n'''
    marker = '    <div class="guide-title">⑲ 第一次使用，照這個順序最快</div>'
    if marker in s:
        s = s.replace(marker, guide + '    <div class="guide-title">⑳ 第一次使用，照這個順序最快</div>', 1)

    s = s.replace('./hourly.js?v=1529', './hourly.js?v=1530').replace('./sw.js?v=1529', './sw.js?v=1530').replace('dogsonSwReloaded1529', 'dogsonSwReloaded1530')
    write(p, s)


def patch_sw_and_status():
    p = "docs/sw.js"
    s = read(p).replace("dogson-free-v1529", "dogson-free-v1530").replace('./hourly.js?v=1529', './hourly.js?v=1530')
    write(p, s)
    p = "docs/data/status.json"
    d = json.loads(read(p))
    d["version"] = "1.5.30-free"
    d["vision_completion_version"] = "1.0"
    d["dynamic_threshold_version"] = "1.1"
    d["portfolio_mode_version"] = "1.2"
    d["change_radar_version"] = "1.1"
    write(p, json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n")


def patch_current_data():
    cp = ROOT / "docs/data/close.json"
    ip = ROOT / "docs/data/intraday.json"
    if cp.exists():
        c = json.loads(cp.read_text(encoding="utf-8"))
        cmap = {}
        for r in c.get("rows") or []:
            try:
                if r.get("avg_volume20_shares") is None and float(r.get("close") or 0) > 0:
                    r["avg_volume20_shares"] = round(float(r.get("avg_turnover20") or 0) / float(r.get("close")), 0)
            except Exception:
                pass
            avg = r.get("avg_volume20_shares")
            f3 = r.get("foreign_3d_net")
            try:
                fint = float(f3) / float(avg) * 100 if f3 is not None and avg and float(avg) > 0 else None
            except Exception:
                fint = None
            r["foreign_3d_intensity_pct"] = round(fint, 2) if fint is not None else None
            if fint is None: lab="資料待補"
            elif fint>=20: lab="強力累積"
            elif fint>=8: lab="明顯累積"
            elif fint>=2: lab="溫和累積"
            elif fint<=-20: lab="強力調節"
            elif fint<=-8: lab="明顯調節"
            elif fint<=-2: lab="溫和調節"
            else: lab="中性"
            r["chip_intensity_label"] = lab
            r["chip_intensity_basis"] = "外資3日淨買超股數 ÷ 20日平均成交股數"
            r.setdefault("breakout_volume_profile", {"version":"1.0","ready":False,"sample_events":0,"current_volume_vs_event_avg":None})
            cmap[str(r.get("code"))] = r
        c["vision_completion_version"] = "1.0"
        cp.write_text(json.dumps(c,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    else:
        cmap = {}
    if ip.exists():
        o = json.loads(ip.read_text(encoding="utf-8"))
        for r in o.get("rows") or []:
            d = cmap.get(str(r.get("code"))) or {}
            for k in ("avg_volume20_shares","foreign_3d_intensity_pct","chip_intensity_label","chip_intensity_basis","breakout_volume_profile"):
                if d.get(k) is not None: r[k]=d.get(k)
            recent=r.get("recent_turnover");prev=r.get("previous_turnover")
            try: ratio=float(recent)/float(prev) if recent is not None and prev and float(prev)>0 else None
            except Exception: ratio=None
            ret=float(r.get("ret15") or 0); vd=float(r.get("vwap_dist") or 0); pace=float(r.get("pace") or 0)
            above=vd>=0;trend=bool(r.get("trend5"));br=bool(r.get("break3"));near=-0.8<=vd<=1.5
            if above and (br or trend) and ret>=.15 and ((ratio is not None and ratio>=1.12) or pace>=1.35): pat="量增上攻";strength=85
            elif near and -1<=ret<=.45 and (trend or above) and ratio is not None and ratio<=.88: pat="量縮回踩";strength=82
            elif near and above and -.35<=ret<=.8 and trend: pat="回踩承接";strength=72
            else: pat="中性";strength=40 if above else 25
            r["execution_pattern_version"]="1.0";r["execution_pattern"]=pat;r["execution_pattern_strength"]=strength;r["turnover_acceleration"]=round(ratio,3) if ratio is not None else None
            r.setdefault("today_direction","待累積");r.setdefault("today_score_delta",None);r.setdefault("today_pace_delta",None)
        o["vision_completion_version"]="1.0"
        o.setdefault("change_radar",{}).setdefault("today_summary",{"version":"1.0","ready":False,"counts":{"new_setup":0,"new_start":0,"turn_strong":0,"turn_weak":0,"to_overheat":0},"events":[],"reason":"等待下一輪盤中歷史快照"})
        ip.write_text(json.dumps(o,ensure_ascii=False,separators=(",",":")),encoding="utf-8")


if __name__ == "__main__":
    patch_build_data()
    patch_bridge()
    patch_validation()
    patch_daytrade()
    patch_ui()
    patch_sw_and_status()
    patch_current_data()
    print("v1.5.30 original vision completion patch applied")
