#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.21 — 5分鐘變化雷達。

新增一個獨立於100分與Stage Engine之外的「狀態變化層」：
- ⬆️ 剛轉強
- ⬇️ 剛轉弱
- 🚀 剛突破
- ♻️ 剛站回VWAP
- 🔥 族群加速

比較來源：上一輪已部署的 intraday.json vs 本輪完成MIS快照橋接後的資料。
不改任何既有評分權重、Stage門檻或盤後邏輯。
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def must(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f"v1.5.21 missing marker: {label}")
    return text.replace(old, new, count)


def patch_build():
    p = "scripts/build_data.py"
    s = read(p)

    helper = r'''

def build_change_radar(rows, rotation, previous_obj):
    """Compare this intraday snapshot with the prior deployed snapshot.

    This is an event/change layer only. It never changes the 100-point score or
    Stage Engine result.  A comparison is accepted only for the same trade date
    and a reasonably recent prior run, so overnight/stale gaps are not mislabeled
    as "just turned" events.
    """
    def num(v, default=0.0):
        try:
            return float(v) if v is not None else float(default)
        except Exception:
            return float(default)

    def trade_date_of(rs):
        vals = []
        for z in rs or []:
            d = str(z.get("quote_date") or z.get("date") or "")[:10]
            if len(d) == 10:
                vals.append(d)
        return max(vals) if vals else None

    now = now_tw()
    previous_obj = previous_obj if isinstance(previous_obj, dict) else {}
    prev_rows = previous_obj.get("rows") or []
    prev_time_raw = previous_obj.get("updated_at")
    comparison_min = None
    try:
        pt = datetime.fromisoformat(str(prev_time_raw))
        if pt.tzinfo is None:
            pt = pt.replace(tzinfo=TW)
        comparison_min = (now - pt.astimezone(TW)).total_seconds() / 60.0
    except Exception:
        comparison_min = None

    cur_date = trade_date_of(rows)
    prev_date = trade_date_of(prev_rows)
    same_day = bool(cur_date and prev_date and cur_date == prev_date)
    fresh_gap = bool(comparison_min is not None and 0.5 <= comparison_min <= 16.0)

    for r in rows:
        r["change_events"] = []
        r["change_score_delta"] = None
        r["previous_intraday_score"] = None
        r["previous_stage"] = None

    base = {
        "version": "1.0",
        "ready": False,
        "trade_date": cur_date,
        "previous_trade_date": prev_date,
        "previous_updated_at": prev_time_raw,
        "comparison_minutes": round(comparison_min, 1) if comparison_min is not None else None,
        "events": [],
        "sector_events": [],
        "counts": {"turn_strong": 0, "turn_weak": 0, "breakout": 0, "vwap_reclaim": 0, "sector_accel": 0},
    }
    if not prev_rows:
        base["reason"] = "等待下一個5分鐘快照建立比較基準"
        return base
    if not same_day:
        base["reason"] = "新交易日第一輪，先建立今日比較基準"
        return base
    if not fresh_gap:
        base["reason"] = "上一輪間隔過久，為避免誤判『剛發生』事件，本輪只建立新基準"
        return base

    prev_map = {str(x.get("code")): x for x in prev_rows if x.get("code")}
    strong_stages = {"蓄勢待發", "剛啟動", "回踩承接", "趨勢持有"}
    weak_stages = {"轉弱警戒", "結構失效"}
    events = []

    def add_event(r, typ, label, reason, priority):
        e = {
            "type": typ, "label": label, "reason": reason,
            "priority": int(priority), "code": str(r.get("code") or ""),
            "name": str(r.get("name") or ""),
            "score": round(num(r.get("intraday_score", r.get("score"))), 1),
            "score_delta": r.get("change_score_delta"),
            "stage": str(r.get("category") or "觀察"),
            "previous_stage": r.get("previous_stage"),
        }
        r.setdefault("change_events", []).append(e)
        events.append(e)
        base["counts"][typ] += 1

    for r in rows:
        code = str(r.get("code") or "")
        p = prev_map.get(code)
        if not p:
            continue
        cur_score = num(r.get("intraday_score", r.get("score")))
        prev_score = num(p.get("intraday_score", p.get("score")))
        delta = cur_score - prev_score
        cur_stage = str(r.get("category") or "觀察")
        prev_stage = str(p.get("category") or "觀察")
        r["change_score_delta"] = round(delta, 1)
        r["previous_intraday_score"] = round(prev_score, 1)
        r["previous_stage"] = prev_stage

        cur_close, cur_vwap = num(r.get("close")), num(r.get("vwap"))
        prev_close, prev_vwap = num(p.get("close")), num(p.get("vwap"))
        cur_above = bool(cur_vwap > 0 and cur_close >= cur_vwap)
        prev_above = bool(prev_vwap > 0 and prev_close >= prev_vwap)
        cur_rel = num((r.get("intraday_components") or {}).get("relative_strength_pct"))
        prev_rel = num((p.get("intraday_components") or {}).get("relative_strength_pct"))
        rel_delta = cur_rel - prev_rel
        cur_break3, prev_break3 = bool(r.get("break3")), bool(p.get("break3"))
        cur_break12, prev_break12 = bool(r.get("break12")), bool(p.get("break12"))

        # 新突破：必須是本輪才由 false -> true，且站在VWAP上方、動能至少60。
        if ((cur_break3 and not prev_break3) or (cur_break12 and not prev_break12)) and cur_above and cur_score >= 60:
            which = "3K突破" if cur_break3 and not prev_break3 else "60分區間突破"
            add_event(r, "breakout", "🚀 剛突破", f"{which}剛成立｜動能 {prev_score:.0f}→{cur_score:.0f}", 100)

        # 站回VWAP：要求上一輪在下方、本輪站回，且15分動能不為負，降低來回穿越雜訊。
        if prev_vwap > 0 and cur_vwap > 0 and (not prev_above) and cur_above and num(r.get("ret15")) >= 0:
            add_event(r, "vwap_reclaim", "♻️ 剛站回VWAP", f"由VWAP下方重新站回｜距VWAP {num(r.get('vwap_dist')):+.1f}%", 88)

        stage_turn_strong = prev_stage in ({"觀察", "轉弱警戒"} | weak_stages) and cur_stage in strong_stages
        score_turn_strong = delta >= 8 and cur_score >= 60 and ((not prev_above and cur_above) or rel_delta >= 0.5 or (cur_break3 and not prev_break3))
        if stage_turn_strong or score_turn_strong:
            bits = [f"動能 {prev_score:.0f}→{cur_score:.0f}"]
            if prev_stage != cur_stage:
                bits.append(f"{prev_stage}→{cur_stage}")
            if rel_delta >= 0.5:
                bits.append(f"相對市場改善 {rel_delta:+.1f}pp")
            add_event(r, "turn_strong", "⬆️ 剛轉強", "｜".join(bits), 92)

        stage_turn_weak = prev_stage not in weak_stages and cur_stage in weak_stages
        score_turn_weak = delta <= -8 and cur_score <= 60 and ((prev_above and not cur_above) or rel_delta <= -0.5)
        if stage_turn_weak or score_turn_weak:
            bits = [f"動能 {prev_score:.0f}→{cur_score:.0f}"]
            if prev_stage != cur_stage:
                bits.append(f"{prev_stage}→{cur_stage}")
            if rel_delta <= -0.5:
                bits.append(f"相對市場惡化 {rel_delta:+.1f}pp")
            add_event(r, "turn_weak", "⬇️ 剛轉弱", "｜".join(bits), 95)

    # 族群加速：熱度跨過+2.5，或已在正熱區且單輪再增加至少1.5。
    prev_rot = {str(x.get("sector") or ""): x for x in (previous_obj.get("sector_rotation") or [])}
    sector_events = []
    for x in rotation or []:
        sector = str(x.get("sector") or "")
        p = prev_rot.get(sector)
        if not sector or not p:
            continue
        h = num(x.get("heat")); ph = num(p.get("heat")); dh = h - ph
        crossed = ph < 2.5 <= h
        accelerated = h >= 2.5 and dh >= 1.5
        if crossed or accelerated:
            sector_events.append({
                "type": "sector_accel", "label": "🔥 族群加速", "sector": sector,
                "heat": round(h, 1), "heat_delta": round(dh, 1),
                "reason": f"熱度 {ph:+.1f}→{h:+.1f}（{dh:+.1f}）",
                "priority": 85,
            })
    sector_events.sort(key=lambda z: (z.get("heat_delta", 0), z.get("heat", 0)), reverse=True)
    base["counts"]["sector_accel"] = len(sector_events)

    events.sort(key=lambda z: (z.get("priority", 0), abs(z.get("score_delta") or 0)), reverse=True)
    base.update({
        "ready": True,
        "reason": "只顯示相較上一輪新發生的變化",
        "events": events[:80],
        "sector_events": sector_events[:20],
    })
    return base
'''

    marker = "def build_intraday():\n"
    if "def build_change_radar(" not in s:
        s = must(s, marker, helper + "\n" + marker, "insert change radar helper")

    old = '''def build_intraday():\n    close_obj = load_json("close.json", {"rows": []})'''
    new = '''def build_intraday():\n    # v1.5.21：sync_live_data 已先抓回上一輪正式 intraday.json。\n    # 先留一份到 .cache，讓 build_data 與後續 MIS bridge 都能和同一個基準比較。\n    previous_intraday = load_json("intraday.json", {})\n    try:\n        (CACHE / "intraday_previous.json").write_text(\n            json.dumps(previous_intraday, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"\n        )\n    except Exception:\n        pass\n    close_obj = load_json("close.json", {"rows": []})'''
    s = must(s, old, new, "cache prior intraday snapshot")

    old = '''    rows = add_component_scores(rows, intraday_market, preliminary_intraday=True)\n\n    dump("intraday.json", {\n        "updated_at": now_tw().isoformat(timespec="seconds"),'''
    new = '''    rows = add_component_scores(rows, intraday_market, preliminary_intraday=True)\n    change_radar = build_change_radar(rows, sector_rotation, previous_intraday)\n\n    dump("intraday.json", {\n        "updated_at": now_tw().isoformat(timespec="seconds"),\n        "change_radar": change_radar,'''
    s = must(s, old, new, "write base change radar")
    write(p, s)


def patch_bridge():
    p = "scripts/bridge_intraday.py"
    s = read(p)
    old = '''    out_rows = bd.add_component_scores(out_rows, intraday_market, preliminary_intraday=True)\n\n    quote_times = [str(q.get("time") or "")[:5] for q in quotes.values() if q.get("time")]'''
    new = '''    out_rows = bd.add_component_scores(out_rows, intraday_market, preliminary_intraday=True)\n\n    # v1.5.21：最後以「完成MIS橋接後」的最新狀態和上一輪正式頁面比較。\n    previous_obj = {}\n    try:\n        prev_path = bd.CACHE / "intraday_previous.json"\n        if prev_path.exists():\n            previous_obj = json.loads(prev_path.read_text(encoding="utf-8"))\n    except Exception:\n        previous_obj = {}\n    change_radar = bd.build_change_radar(out_rows, rotation, previous_obj)\n\n    quote_times = [str(q.get("time") or "")[:5] for q in quotes.values() if q.get("time")]'''
    s = must(s, old, new, "bridge computes final change radar")
    old = '''        "sector_rotation": rotation,\n        "rows": out_rows,'''
    new = '''        "sector_rotation": rotation,\n        "change_radar": change_radar,\n        "rows": out_rows,'''
    s = must(s, old, new, "bridge writes change radar")
    write(p, s)


def patch_index():
    p = "docs/index.html"
    s = read(p)
    s = must(s, "Free Edition v1.5.20", "Free Edition v1.5.21", "version header")
    s = s.replace("./sw.js?v=1520", "./sw.js?v=1521")
    s = s.replace("dogsonSwReloaded1520", "dogsonSwReloaded1521")

    css_marker = '.empty{text-align:center;color:var(--muted);padding:35px 10px}.note{font-size:11px;color:var(--muted);line-height:1.5;margin:12px 2px}\n'
    css_add = css_marker + '''.changebox{background:linear-gradient(180deg,#171d27,#111720);border:1px solid #314056;border-radius:16px;padding:12px;margin:12px 0}.changetop{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.changetitle{font-size:16px;font-weight:900}.changesub{font-size:10px;color:var(--muted);margin-top:3px}.changecounts{display:flex;gap:6px;overflow:auto;margin-top:9px;padding-bottom:2px}.changecount{white-space:nowrap;background:#0e141c;border:1px solid #293442;border-radius:999px;padding:6px 8px;font-size:10px}.changeevents{display:grid;gap:6px;margin-top:9px}.changeevent{width:100%;border:1px solid #293442;background:#0e141c;color:#eef3fb;border-radius:10px;padding:8px 9px;display:flex;justify-content:space-between;gap:8px;text-align:left;cursor:pointer}.changeeventmain{min-width:0}.changeeventname{font-size:11px;font-weight:900}.changeeventreason{font-size:9px;color:var(--muted);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.changedelta{font-size:11px;font-weight:900;white-space:nowrap}.changebadges{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}.changebadge{font-size:10px;padding:5px 7px;border-radius:8px;background:#152235;border:1px solid #294463;color:#b9ddff}.changebadge.down{background:#281a1d;border-color:#543038;color:#ffb1bd}.changebadge.up{background:#14271d;border-color:#28503a;color:#a7edbd}.sectorchange{margin-top:9px;padding-top:8px;border-top:1px solid #293442;font-size:10px;color:#ffd477;line-height:1.6}\n'''
    s = must(s, css_marker, css_add, "change radar css")

    marker = '<div id="liveStatus" class="live-status warn">🟡 近即時報價準備中｜技術結構仍採5分K</div>'
    s = must(s, marker, '<div id="changebox"></div>\n' + marker, "change radar container")

    old = 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[];'
    new = 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[],changeRadar={};'
    s = must(s, old, new, "change radar state")

    func_marker = 'function srHTML(r){\n'
    funcs = r'''function changeBadgeHTML(r){
 if(mode!=="intraday"||!(r.change_events||[]).length)return "";
 return `<div class="changebadges">${r.change_events.slice(0,4).map(e=>`<span class="changebadge ${e.type==="turn_weak"?"down":"up"}">${e.label} · ${e.reason}</span>`).join("")}</div>`;
}
function changeRadarHTML(){
 if(mode!=="intraday")return "";
 const x=changeRadar||{},c=x.counts||{};
 const head=`<div class="changetop"><div><div class="changetitle">🚨 5分鐘變化雷達</div><div class="changesub">${x.ready?`比較上一輪${x.comparison_minutes?`（約 ${num(x.comparison_minutes,0)} 分鐘）`:""}｜只顯示新發生的變化`:x.reason||"等待下一輪建立比較基準"}</div></div></div>`;
 if(!x.ready)return `<div class="changebox">${head}<div class="changesub" style="margin-top:8px">第一輪只建立基準，不會把隔夜差異誤判成盤中訊號。</div></div>`;
 const counts=`<div class="changecounts"><span class="changecount">⬆️轉強 ${c.turn_strong||0}</span><span class="changecount">⬇️轉弱 ${c.turn_weak||0}</span><span class="changecount">🚀突破 ${c.breakout||0}</span><span class="changecount">♻️站回VWAP ${c.vwap_reclaim||0}</span><span class="changecount">🔥族群加速 ${c.sector_accel||0}</span></div>`;
 const ev=(x.events||[]).slice(0,8);
 const items=ev.length?`<div class="changeevents">${ev.map(e=>`<button class="changeevent peerlink" data-code="${e.code}"><span class="changeeventmain"><span class="changeeventname">${e.label}｜${e.name} ${e.code}</span><div class="changeeventreason">${e.reason}</div></span><span class="changedelta">${e.score_delta===null||e.score_delta===undefined?"":signed(e.score_delta,0,"")}</span></button>`).join("")}</div>`:`<div class="changesub" style="margin-top:9px">這一輪沒有新的個股轉折訊號。</div>`;
 const se=(x.sector_events||[]).slice(0,5);
 const sectors=se.length?`<div class="sectorchange">${se.map(e=>`${e.label} ${e.sector}｜${e.reason}`).join("<br>")}</div>`:"";
 return `<div class="changebox">${head}${counts}${items}${sectors}</div>`;
}

'''
    if "function changeRadarHTML()" not in s:
        s = must(s, func_marker, funcs + func_marker, "change radar frontend functions")

    old = '  ${stageExplainHTML(r)}\n  ${partsHTML(r)}'
    new = '  ${stageExplainHTML(r)}\n  ${changeBadgeHTML(r)}\n  ${partsHTML(r)}'
    s = must(s, old, new, "stock card change badges")

    old = 'closeMarket=await m.json();intraMarket=ij.market||closeMarket;marketLive=ij.market_intraday||{};sectorRotation=ij.sector_rotation||[];market=intraMarket;'
    new = 'closeMarket=await m.json();intraMarket=ij.market||closeMarket;marketLive=ij.market_intraday||{};sectorRotation=ij.sector_rotation||[];changeRadar=ij.change_radar||{};market=intraMarket;'
    s = must(s, old, new, "load change radar data")

    old = '$("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();render();'
    new = '$("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();$("changebox").innerHTML=changeRadarHTML();render();'
    s = must(s, old, new, "render change radar on load")

    old = '$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();updateFooter();render()});'
    new = '$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();$("changebox").innerHTML=changeRadarHTML();updateFooter();render()});'
    s = must(s, old, new, "render change radar on tab switch")

    # Add a concise beginner-guide explanation before the final workflow section.
    guide_marker = '    <div class="guide-title">⑬ 第一次使用，照這個順序最快</div>'
    guide = '''    <div class="guide-title">⑬ 5分鐘變化雷達：看「剛剛發生什麼」</div>\n    <div class="guide-card">\n      <div class="guide-line"><span class="guide-key">⬆️ 剛轉強</span>：分數／生命週期／VWAP／相對強弱出現明顯改善，不是小幅跳動就算。</div>\n      <div class="guide-line"><span class="guide-key">⬇️ 剛轉弱</span>：動能明顯下降，且價格或相對市場同步轉差；用來提醒庫存要多看一眼，不等於立刻賣出。</div>\n      <div class="guide-line"><span class="guide-key">🚀 剛突破</span>：本輪才新出現3K或60分區間突破，且站上VWAP、動能至少60。</div>\n      <div class="guide-line"><span class="guide-key">♻️ 剛站回VWAP</span>：上一輪在VWAP下方，本輪重新站回，且15分鐘動能沒有繼續轉弱。</div>\n      <div class="guide-line"><span class="guide-key">🔥 族群加速</span>：族群熱度跨進正向區，或原本已熱又明顯加速。</div>\n      <div class="guide-tip">這一區回答的是「剛剛變了什麼」，不是另一套分數，也不會改動原本100分。</div>\n    </div>\n\n    <div class="guide-title">⑭ 第一次使用，照這個順序最快</div>'''
    s = must(s, guide_marker, guide, "change radar help")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v1521", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_build()
    patch_bridge()
    patch_index()
    patch_sw()
    print("v1.5.21 five-minute change radar patch applied")
