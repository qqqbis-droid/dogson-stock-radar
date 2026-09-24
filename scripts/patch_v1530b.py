#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Robust backend patch for v1.5.30.

Keeps Stage/score core intact and attaches the original-vision completion layer
before/after existing scoring, reducing fragile edits inside stable Stage code.
"""
from patch_v1530 import COMPLETION_HELPERS, read, write, must


def patch_build_data():
    p="scripts/build_data.py"
    s=read(p)
    s=s.replace("犬子老師飆股雷達 Free Edition v1.5.29","犬子老師飆股雷達 Free Edition v1.5.30",1)

    # 1. Daily 20d average shares.
    if '"avg_volume20_shares"' not in s:
        s=must(s,
          '        "avg_turnover20": float((c*v).rolling(20).mean().iloc[-1]),\n        "date": str(x.index[-1].date()),',
          '        "avg_turnover20": float((c*v).rolling(20).mean().iloc[-1]),\n        "avg_volume20_shares": float(v.rolling(20).mean().iloc[-1]),\n        "date": str(x.index[-1].date()),',
          'avg volume shares')

    # 2. Historical breakout-event volume baseline.
    if 'row["breakout_volume_profile"]' not in s:
        anchor='''    hist_ret = ret1.tail(60).dropna().abs()\n    hist_vx = vx.tail(60).dropna()\n    row["dynamic_profile"] = {'''
        replacement='''    hist_ret = ret1.tail(60).dropna().abs()\n    hist_vx = vx.tail(60).dropna()\n    # v1.5.30：最近最多20次20日突破事件，建立個股自己的突破量基準。\n    breakout_mask = (c > p20) & p20.notna()\n    breakout_event_volumes = v[breakout_mask].iloc[:-1].tail(20).dropna()\n    breakout_event_vx = vx[breakout_mask].iloc[:-1].tail(20).dropna()\n    breakout_avg_volume = float(breakout_event_volumes.mean()) if len(breakout_event_volumes) >= 3 else None\n    breakout_vx_median = float(breakout_event_vx.median()) if len(breakout_event_vx) >= 3 else None\n    breakout_vx_p75 = float(breakout_event_vx.quantile(.75)) if len(breakout_event_vx) >= 3 else None\n    current_vs_breakout_avg = (float(v.iloc[-1]) / breakout_avg_volume) if breakout_avg_volume and breakout_avg_volume > 0 else None\n    row["breakout_volume_profile"] = {\n        "version":"1.0", "ready":bool(len(breakout_event_volumes) >= 3),\n        "sample_events":int(len(breakout_event_volumes)),\n        "event_avg_volume_shares":round(breakout_avg_volume,0) if breakout_avg_volume is not None else None,\n        "event_vol_x_median":round(breakout_vx_median,3) if breakout_vx_median is not None else None,\n        "event_vol_x_p75":round(breakout_vx_p75,3) if breakout_vx_p75 is not None else None,\n        "current_volume_vs_event_avg":round(current_vs_breakout_avg,3) if current_vs_breakout_avg is not None else None,\n        "current_is_breakout":bool(row["break20"]),\n    }\n    row["dynamic_profile"] = {'''
        s=must(s,anchor,replacement,'breakout event baseline')
        s=must(s,
          '        "vol_x_p90": round(float(hist_vx.quantile(.90)), 3) if len(hist_vx) >= 10 else None,\n    }',
          '        "vol_x_p90": round(float(hist_vx.quantile(.90)), 3) if len(hist_vx) >= 10 else None,\n        "breakout_event_count": int(len(breakout_event_volumes)),\n        "breakout_vol_x_median": round(breakout_vx_median,3) if breakout_vx_median is not None else None,\n    }',
          'dynamic breakout fields')

    # 3. Completion helpers: chip intensity, comfortable-entry pattern, cumulative day direction.
    if 'def _chip_intensity_fields(r):' not in s:
        s=must(s,'def _finite(v):',COMPLETION_HELPERS+'def _finite(v):','completion helpers')

    # 4. Attach cross-stock chip intensity to every completed close row before Stage/score.
    close_anchor='''    rows = add_component_scores(rows, market, preliminary_intraday=False)\n    sector_funds = build_sector_institution_flow(rows, price_history)'''
    if '_attach_completion_context(rows, {})' not in s:
        s=must(s,close_anchor,
          '''    rows = _attach_completion_context(rows, {})\n    rows = add_component_scores(rows, market, preliminary_intraday=False)\n    rows = _enrich_completion_stage_signals(rows)\n    sector_funds = build_sector_institution_flow(rows, price_history)''',
          'close completion attach')

    # 5. Intraday reads close background + computes execution pattern before Stage.
    intra_anchor='''    rows = _attach_relative_multitimeframe(rows, close_map, market, market_live)\n    rows = _refresh_dynamic_thresholds(rows, close_map)\n    sector_rotation = build_sector_rotation(rows)'''
    if '_attach_completion_context(rows, close_map)' not in s:
        s=must(s,intra_anchor,
          '''    rows = _attach_relative_multitimeframe(rows, close_map, market, market_live)\n    rows = _refresh_dynamic_thresholds(rows, close_map)\n    rows = _attach_completion_context(rows, close_map)\n    sector_rotation = build_sector_rotation(rows)''',
          'intraday completion attach')

    # 6. Enrich Stage evidence after Stage itself has finished. No score/category rewrite.
    if 'def _enrich_completion_stage_signals' not in s:
        helper=r'''
def _enrich_completion_stage_signals(rows):
    for r in rows or []:
        sig=list(r.get("stage_signals") or [])
        risks=list(r.get("stage_risks") or [])
        cat=str(r.get("category") or "")
        pattern=str(r.get("execution_pattern") or "")
        intensity=_finite(r.get("foreign_3d_intensity_pct"))
        bp=r.get("breakout_volume_profile") or {}
        extras=[]
        if cat=="剛啟動" and pattern=="量增上攻": extras.append("量增上攻型態")
        if cat=="回踩承接" and pattern in {"量縮回踩","回踩承接"}: extras.append(pattern)
        if intensity is not None and intensity>=5: extras.append(f"外資3日力度 {intensity:+.1f}%")
        if bp.get("ready") and bp.get("current_volume_vs_event_avg") is not None and cat in {"剛啟動","蓄勢待發"}:
            extras.append(f"突破量/歷史突破量 {float(bp.get('current_volume_vs_event_avg')):.2f}x")
        for x in extras:
            if x not in sig: sig.append(x)
        r["stage_signals"]=sig[:6]
        r["stage_risks"]=risks[:6]
    return rows

'''
        # Insert immediately before add_component_scores, which calls Stage logic.
        s=must(s,'def add_component_scores(rows, market, preliminary_intraday=False):',helper+'def add_component_scores(rows, market, preliminary_intraday=False):','stage enrichment helper')

    # Intraday post-Stage enrichment and cumulative today summary.
    if 'rows = _enrich_completion_stage_signals(rows)\n    change_radar = build_change_radar' not in s:
        s=must(s,
          '''    rows = add_component_scores(rows, intraday_market, preliminary_intraday=True)\n    change_radar = build_change_radar(rows, sector_rotation, previous_intraday)''',
          '''    rows = add_component_scores(rows, intraday_market, preliminary_intraday=True)\n    rows = _enrich_completion_stage_signals(rows)\n    change_radar = build_change_radar(rows, sector_rotation, previous_intraday)\n    change_radar["today_summary"] = _build_today_cumulative_change(rows)''',
          'intraday post stage completion')

    # 7. Version markers; do not change score weights.
    s=s.replace('"version": "1.5.29-free"','"version": "1.5.30-free"')
    s=s.replace('"version": "1.5.17-free"','"version": "1.5.30-free"')
    if '"vision_completion_version": "1.0"' not in s:
        s=must(s,
          '        "dynamic_threshold_version": "1.0",\n        "score_formula":',
          '        "dynamic_threshold_version": "1.1",\n        "vision_completion_version": "1.0",\n        "score_formula":',
          'intraday completion version')
    # Normalize status dynamic version and add completion marker near status update.
    s=s.replace('"dynamic_threshold_version": "1.0",\n        "version": "1.5.30-free",', '"dynamic_threshold_version": "1.1",\n        "vision_completion_version": "1.0",\n        "version": "1.5.30-free",')
    write(p,s)
