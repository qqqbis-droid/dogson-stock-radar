#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def must_replace(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f"v1.5.3 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_chip_data():
    p = "scripts/chip_data.py"
    s = read(p)
    if "def backfill_institution_history(" not in s:
        marker = "\ndef _save_status(out: Dict[str, dict]):\n"
        helper = r'''
def backfill_institution_history(codes: set, market_map: dict, target_days: int = 20, calendar_days: int = 40):
    """Backfill only foreign/trust history so sector flow can show 1/5/20-day trends.

    This avoids repeatedly fetching old margin/SBL tables. Once the persisted file
    contains target_days distinct institutional dates, future close runs return fast.
    """
    history = _load_persisted_history(codes)

    def inst_dates():
        return {
            str(r.get("date"))
            for rows in history.values()
            for r in rows
            if r.get("date") and (r.get("foreign_net") is not None or r.get("trust_net") is not None)
        }

    dates = inst_dates()
    if len(dates) >= target_days:
        return history

    listed = {c for c in codes if _market_for(c, market_map) == "上市"}
    otc = codes - listed
    for d in _recent_calendar_days(calendar_days):
        ds = d.isoformat()
        if ds in dates:
            continue
        merged = {c: {} for c in codes}
        if listed:
            try:
                part = _extract_inst(_twse_institution(d), listed)
                for c, vals in part.items():
                    merged[c].update(vals)
            except Exception as e:
                _diag(f"TWSE inst backfill {d} failed: {e}")
        if otc:
            try:
                part = _extract_inst(_tpex_institution(d), otc)
                for c, vals in part.items():
                    merged[c].update(vals)
            except Exception as e:
                _diag(f"TPEx inst backfill {d} failed: {e}")

        any_day = False
        for c, vals in merged.items():
            if vals and any(v is not None for v in vals.values()):
                history[c] = _merge_history(history.get(c, []), [{"date": ds, **vals}])
                any_day = True
        if any_day:
            dates.add(ds)
        if len(dates) >= target_days:
            break

    _save_history(history)
    _diag(f"institution history dates={len(dates)} target={target_days}")
    return history

'''
        s = must_replace(s, marker, "\n" + helper + "def _save_status(out: Dict[str, dict]):\n", "institution backfill helper")

    old = '''    history = {}\n    for c in codes:\n        history[c] = _merge_history(persisted.get(c, []), fetched.get(c, []))\n    _save_history(history)\n\n    out = {}\n'''
    new = '''    history = {}\n    for c in codes:\n        history[c] = _merge_history(persisted.get(c, []), fetched.get(c, []))\n    _save_history(history)\n\n    # v1.5.3: sector-level fund flow needs enough official institutional history\n    # for 5/20-day aggregation. Historical margin/SBL are not re-fetched here.\n    history = backfill_institution_history(codes, market_map, target_days=20, calendar_days=40)\n\n    out = {}\n'''
    if "sector-level fund flow needs enough official institutional history" not in s:
        s = must_replace(s, old, new, "call institution backfill")

    s = s.replace('            "chip_history_days": min(len(hs), 4),',
                  '            "chip_history_days": min(len(hs), 40),\n            "institution_history_days": len({x.get("date") for x in hs if x.get("date") and (x.get("foreign_net") is not None or x.get("trust_net") is not None)}),', 1)
    write(p, s)


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)
    s = s.replace("犬子老師飆股雷達 Free Edition v1.5.1", "犬子老師飆股雷達 Free Edition v1.5.3", 1)

    # Make relative-strength scoring transparent: 10-point market-relative base + 5-point trend confirmation.
    old_rel = '''    rel_pct = day - bench\n    if rel_pct >= 2.0:\n        relative = 10.0\n    elif rel_pct >= 1.0:\n        relative = 8.0\n    elif rel_pct >= 0.3:\n        relative = 6.0\n    elif rel_pct >= 0:\n        relative = 4.0\n    elif rel_pct > -1.0:\n        relative = 2.0\n    else:\n        relative = 0.0\n    if close > 0 and vwap > 0 and close >= vwap and ret15 > 0:\n        relative += 5.0\n'''
    new_rel = '''    rel_pct = day - bench\n    if rel_pct >= 2.0:\n        relative_base = 10.0\n    elif rel_pct >= 1.0:\n        relative_base = 8.0\n    elif rel_pct >= 0.3:\n        relative_base = 6.0\n    elif rel_pct >= 0:\n        relative_base = 4.0\n    elif rel_pct > -1.0:\n        relative_base = 2.0\n    else:\n        relative_base = 0.0\n    relative_confirm = 5.0 if (close > 0 and vwap > 0 and close >= vwap and ret15 > 0) else 0.0\n    relative = min(15.0, relative_base + relative_confirm)\n'''
    if "relative_base = 10.0" not in s:
        s = must_replace(s, old_rel, new_rel, "relative strength scoring")

    old_comp = '        "relative_strength_pct": round(rel_pct, 2),\n        "sector": round(sector, 1),'
    new_comp = '        "relative_strength_pct": round(rel_pct, 2),\n        "relative_base": round(relative_base, 1),\n        "relative_confirmation": round(relative_confirm, 1),\n        "relative_benchmark_pct": round(bench, 2),\n        "sector": round(sector, 1),'
    if '"relative_base": round(relative_base' not in s:
        s = must_replace(s, old_comp, new_comp, "relative component details")

    # If a stock has no curated sub-sector, use the official industry as a real peer group.
    old_ind = '''        else:\n            n = int(industry_hot.get(industry, 0)) if industry and industry != "未分類" else 0\n            total_n = int(industry_total.get(industry, 0)) if industry and industry != "未分類" else 0\n'''
    new_ind = '''        else:\n            group_rows = [x for x in rows if industry and industry != "未分類" and str(x.get("industry_name") or "").strip() == industry]\n            stat = _resonance_stats(group_rows) if group_rows else None\n            n = int(industry_hot.get(industry, 0)) if industry and industry != "未分類" else 0\n            total_n = int(industry_total.get(industry, 0)) if industry and industry != "未分類" else 0\n'''
    if "group_rows = [x for x in rows if industry and industry" not in s:
        s = must_replace(s, old_ind, new_ind, "industry peer fallback")

    # Every intraday sector-rotation item carries clickable members, not only three leaders.
    old_leaders = '            "leaders": [{"code": r.get("code"), "name": r.get("name"), "change_pct": r.get("day_change")} for r in leaders],\n'
    new_leaders = '''            "leaders": [{"code": r.get("code"), "name": r.get("name"), "change_pct": r.get("day_change")} for r in leaders],\n            "members": [{\n                "code": r.get("code"), "name": r.get("name"),\n                "change_pct": r.get("day_change"), "pace": r.get("pace"),\n                "vwap_dist": r.get("vwap_dist"), "category": r.get("category")\n            } for r in sorted(g, key=lambda z: float(z.get("current_turnover") or 0), reverse=True)[:12]],\n'''
    if '"members": [{' not in s:
        s = must_replace(s, old_leaders, new_leaders, "intraday sector members")

    if "def build_sector_institution_flow(rows):" not in s:
        marker = "\ndef build_intraday():\n"
        helper = r'''
def build_sector_institution_flow(rows):
    """Aggregate official foreign + investment-trust net shares by sector for close radar.

    Values are reported in lots (張), not monetary amount, because official history in
    chip_history is share quantity. This avoids pretending a current-price estimate is
    an exact historical cash-flow amount.
    """
    history = load_json("chip_history.json", {})
    if not isinstance(history, dict) or not rows:
        return []

    groups = {}
    for r in rows:
        sector = str(r.get("sector_group") or "").strip()
        industry = str(r.get("industry_name") or "").strip()
        key = sector if sector else (industry if industry and industry != "未分類" else "")
        if not key:
            continue
        groups.setdefault(key, []).append(r)

    out = []
    for key, members in groups.items():
        daily = {}
        member_latest = []
        for r in members:
            code = str(r.get("code") or "")
            hs = history.get(code) or []
            latest_inst = None
            for h in hs:
                ds = str(h.get("date") or "")
                if not ds:
                    continue
                fv = h.get("foreign_net")
                tv = h.get("trust_net")
                if fv is None and tv is None:
                    continue
                try:
                    net = float(fv or 0) + float(tv or 0)
                except Exception:
                    continue
                daily[ds] = daily.get(ds, 0.0) + net
                if latest_inst is None:
                    latest_inst = net / 1000.0
            member_latest.append({
                "code": code, "name": r.get("name"),
                "day_change": r.get("day_change"), "category": r.get("category"),
                "score": r.get("swing_quality_score", r.get("score")),
                "inst_lots": None if latest_inst is None else round(latest_inst, 1),
            })

        ordered = sorted(daily.items(), key=lambda x: x[0], reverse=True)
        vals = [v / 1000.0 for _, v in ordered]
        latest = vals[0] if vals else None
        prev = vals[1] if len(vals) >= 2 else None
        net5 = sum(vals[:5]) if len(vals) >= 5 else None
        net20 = sum(vals[:20]) if len(vals) >= 20 else None

        streak = 0
        streak_dir = None
        if vals and vals[0] != 0:
            streak_dir = 1 if vals[0] > 0 else -1
            for v in vals:
                if v == 0 or (1 if v > 0 else -1) != streak_dir:
                    break
                streak += 1
        accelerating = bool(latest is not None and prev is not None and latest * prev > 0 and abs(latest) >= abs(prev) * 1.15)
        if streak_dir == 1:
            flow_text = f"連續流入 {streak} 天" + (" ↑ 流入加速" if accelerating else "")
        elif streak_dir == -1:
            flow_text = f"連續流出 {streak} 天" + (" ↓ 流出加速" if accelerating else "")
        else:
            flow_text = "資金方向中性"

        if latest is None:
            action = "資料累積中"
        elif latest > 0 and (net5 is None or net5 > 0):
            action = "持續加碼"
        elif latest > 0:
            action = "轉為加碼"
        elif latest < 0 and (net5 is None or net5 < 0):
            action = "持續減碼"
        elif latest < 0:
            action = "轉為減碼"
        else:
            action = "中性"

        weighted = [(float(r.get("ret5") or 0), max(float(r.get("avg_turnover20") or 0), 1.0)) for r in members]
        sw = sum(w for _, w in weighted)
        ret5 = sum(v * w for v, w in weighted) / sw if sw else None
        peers = sorted(member_latest, key=lambda x: (abs(float(x.get("inst_lots") or 0)), float(x.get("day_change") or 0)), reverse=True)[:12]
        out.append({
            "sector": key,
            "today_lots": None if latest is None else round(latest, 1),
            "net5_lots": None if net5 is None else round(net5, 1),
            "net20_lots": None if net20 is None else round(net20, 1),
            "history_days": len(vals),
            "latest_date": ordered[0][0] if ordered else None,
            "flow_streak": streak,
            "flow_direction": "in" if streak_dir == 1 else "out" if streak_dir == -1 else "flat",
            "accelerating": accelerating,
            "flow_text": flow_text,
            "action": action,
            "ret5_pct": None if ret5 is None else round(ret5, 2),
            "member_count": len(members),
            "members": peers,
        })

    out.sort(key=lambda x: (abs(float(x.get("net5_lots") or x.get("today_lots") or 0)), abs(float(x.get("today_lots") or 0))), reverse=True)
    return out

'''
        s = must_replace(s, marker, "\n" + helper + "def build_intraday():\n", "sector institution helper")

    old_close = '''    rows = add_component_scores(rows, market, preliminary_intraday=False)\n\n    dump("close.json", {\n'''
    new_close = '''    rows = add_component_scores(rows, market, preliminary_intraday=False)\n    sector_funds = build_sector_institution_flow(rows)\n\n    dump("close.json", {\n'''
    if "sector_funds = build_sector_institution_flow(rows)" not in s:
        s = must_replace(s, old_close, new_close, "build close sector funds")

    old_market = '        "market": market,\n        "score_formula": {"mode": "swing_direct_100"'
    new_market = '        "market": market,\n        "sector_funds": sector_funds,\n        "sector_funds_note": "外資＋投信官方淨買賣股數彙總，單位張；未含自營商",\n        "score_formula": {"mode": "swing_direct_100"'
    if '"sector_funds": sector_funds' not in s:
        s = must_replace(s, old_market, new_market, "close payload sector funds")

    write(p, s)


def patch_index():
    p = "docs/index.html"
    s = read(p)
    s = s.replace("Free Edition v1.5.2｜盤中動能100＋盤後波段100＋60K全股票資訊",
                  "Free Edition v1.5.3｜族群資金可展開＋盤後法人流向＋60K全股票資訊", 1)

    # Styles for collapsible sector-flow cards.
    old_css = '.rotationnums{text-align:right;color:#cbd3df;line-height:1.45;min-width:138px}@media(max-width:620px){.rotationcols{grid-template-columns:1fr}.rotationrow{font-size:10px}}'
    new_css = '.rotationnums{text-align:right;color:#cbd3df;line-height:1.45;min-width:138px}.rotationtoggle{border:1px solid #36506f;background:#17304a;color:#cde6ff;border-radius:10px;padding:7px 10px;font-size:11px;font-weight:850}.rotationcard{background:#0e131a;border:1px solid #252d39;border-radius:12px;padding:9px;margin:6px 0}.rotationcard .rotationrow{border:0;padding:0;margin:0;background:transparent}.rotationdetail{margin-top:7px;padding-top:7px}.rotationdetail summary{color:#a9d5ff}.rotationhint{font-size:11px;color:#9ba5b6;margin-top:8px}.flowtag{display:inline-block;margin-top:5px;padding:4px 7px;border-radius:999px;background:#242b38;font-size:10px;font-weight:850}.flowtag.buy{color:#ff9cac;border:1px solid #5b2d35}.flowtag.sell{color:#75e9a8;border:1px solid #244936}@media(max-width:620px){.rotationcols{grid-template-columns:1fr}.rotationrow{font-size:10px}}'
    if ".rotationtoggle{" not in s:
        s = must_replace(s, old_css, new_css, "rotation styles")

    old_vars = 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[];'
    new_vars = 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[],rotationExpanded=false;'
    if "sectorFunds=[]" not in s:
        s = must_replace(s, old_vars, new_vars, "sector funds state")

    # Replace the rotation renderer with a shared intraday/close collapsible drill-down.
    pat = r'function rotationHTML\(\)\{.*?\n\}\n\nfunction srHTML\(r\)\{'
    repl = r'''function rotationMembers(x){
 const ms=(x.members||x.peers||x.leaders||[]).slice(0,12);
 if(!ms.length)return `<div class="rotationhint">這個族群目前沒有可展開的個股資料。</div>`;
 return `<details class="rotationdetail"><summary>展開族群股票 ${ms.length} 檔</summary><div class="group">${ms.map(m=>`<button class="g peerlink" data-rotation-code="${m.code}"><span>${m.code} ${m.name}<small> ${signed(m.change_pct??m.day_change,1)}</small></span><span>${m.inst_lots===null||m.inst_lots===undefined?"查看":signed(m.inst_lots,0,"張")}</span></button>`).join("")}</div></details>`;
}

function rotationHTML(){
 const intr=mode==="intraday";
 const arr=intr?(sectorRotation||[]):(sectorFunds||[]);
 const title=intr?"💰 盤中族群資金輪動":"🏦 盤後族群法人資金流";
 const sub=intr?"成交金額占比變化＋價格＋VWAP＋廣度；不是法人淨流入":"外資＋投信官方淨買賣股數彙總（張），未含自營商；5/20日不足時明確標示累積中";
 if(!arr.length)return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div></div><div class="rotationhint">目前資料不足。</div></div>`;
 if(!rotationExpanded){
   const pos=intr?arr.filter(x=>(x.heat||0)>=2.5).length:arr.filter(x=>(x.today_lots||0)>0).length;
   const neg=intr?arr.filter(x=>(x.heat||0)<=-2.5).length:arr.filter(x=>(x.today_lots||0)<0).length;
   return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div><button id="rotationToggle" class="rotationtoggle">展開 ▼</button></div><div class="rotationhint">${intr?`吸金 ${pos} 群｜降溫 ${neg} 群`:`今日淨買 ${pos} 群｜淨賣 ${neg} 群`}｜收合時不占版面</div></div>`;
 }
 if(intr){
   const hot=arr.filter(x=>(x.heat||0)>=2.0).slice(0,6);
   const cold=[...arr].sort((a,b)=>(a.heat||0)-(b.heat||0)).filter(x=>(x.heat||0)<=-2.0).slice(0,6);
   const one=x=>`<div class="rotationcard"><div class="rotationrow"><div><b>${x.state}｜${x.sector}</b><div class="rotationleaders">${(x.leaders||[]).map(s=>`${s.name} ${signed(s.change_pct,1)}`).join(" · ")}</div></div><div class="rotationnums">熱度 ${signed(x.heat,1,"")}<br>族群 ${signed(x.change_pct,1)}｜資金占比 ${num(x.turnover_share_pct,1)}%<br>${x.share_change_pp===null||x.share_change_pp===undefined?"占比變化待累積":`近${x.window_min||30}分占比 ${signed(x.share_change_pp,2,"pp")}`}｜VWAP上 ${num(x.above_vwap_pct,0)}%</div></div>${rotationMembers(x)}</div>`;
   return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div><button id="rotationToggle" class="rotationtoggle">收合 ▲</button></div><div class="rotationcols"><div><div class="rotationhead">🔥 吸金／轉強</div>${hot.length?hot.map(one).join(""):`<div class="sub">暫無明顯吸金族群</div>`}</div><div><div class="rotationhead">🧊 流失／降溫</div>${cold.length?cold.map(one).join(""):`<div class="sub">暫無明顯流失族群</div>`}</div></div></div>`;
 }
 const buys=arr.filter(x=>(x.today_lots||0)>0).sort((a,b)=>(b.net5_lots??b.today_lots??0)-(a.net5_lots??a.today_lots??0)).slice(0,8);
 const sells=arr.filter(x=>(x.today_lots||0)<0).sort((a,b)=>(a.net5_lots??a.today_lots??0)-(b.net5_lots??b.today_lots??0)).slice(0,8);
 const one=x=>{const buy=(x.today_lots||0)>=0;const d20=x.net20_lots===null||x.net20_lots===undefined?`累積中 ${x.history_days||0}/20日`:signed(x.net20_lots,0,"張");return `<div class="rotationcard"><div class="rotationrow"><div><b>${x.sector}</b><div class="rotationleaders">${x.flow_text||"—"}<br>族群近5日平均 ${signed(x.ret5_pct,2)}</div><span class="flowtag ${buy?'buy':'sell'}">${x.action||"觀察"}</span></div><div class="rotationnums">今日 ${signed(x.today_lots,0,"張")}<br>近5日 ${x.net5_lots===null||x.net5_lots===undefined?`累積中 ${x.history_days||0}/5日`:signed(x.net5_lots,0,"張")}<br>近20日 ${d20}</div></div>${rotationMembers(x)}</div>`};
 return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div><button id="rotationToggle" class="rotationtoggle">收合 ▲</button></div><div class="rotationcols"><div><div class="rotationhead">🔴 法人淨買／加碼</div>${buys.length?buys.map(one).join(""):`<div class="sub">目前沒有明顯淨買族群</div>`}</div><div><div class="rotationhead">🟢 法人淨賣／減碼</div>${sells.length?sells.map(one).join(""):`<div class="sub">目前沒有明顯淨賣族群</div>`}</div></div></div>`;
}

function wireRotation(){
 const t=$("rotationToggle");if(t)t.onclick=()=>{rotationExpanded=!rotationExpanded;$("rotationbox").innerHTML=rotationHTML();wireRotation()};
 document.querySelectorAll("[data-rotation-code]").forEach(b=>b.onclick=()=>showPeerPeek(b.dataset.rotationCode));
}

function srHTML(r){'''
    ns, n = re.subn(pat, repl, s, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("v1.5.3 patch missing marker: rotationHTML block")
    s = ns

    # Make group drill-down work for curated sector groups AND official industry fallback.
    pat2 = r'function groupHTML\(r\)\{.*?\n\}\n\nfunction partsHTML\(r\)\{'
    repl2 = r'''function groupHTML(r){
 const sector=(r.sector_group||"").trim(),industry=(r.industry_name||"").trim();
 const key=sector||(industry&&industry!=="未分類"?industry:"");
 if(!key)return `<details><summary>👥 族群共振｜尚無可用分類</summary><div class="helptext">目前沒有足夠的次產業或官方產業分類，因此無法安全地列出同族群股票。</div></details>`;
 const d=r.sector_detail||{},comp=d.components||{};
 let peers=(r.sector_peers&&r.sector_peers.length?r.sector_peers:rows.filter(x=>sector?String(x.sector_group||"").trim()===sector:String(x.industry_name||"").trim()===industry).slice(0,12));
 if(!peers.length)peers=[r];
 const detail=Object.keys(comp).length?`廣度 ${num(comp.breadth,1)}/3 · 強度 ${num(comp.strength,1)}/2 · 量能 ${num(comp.volume,1)}/2 · 領頭 ${num(comp.leaders,1)}/2 · 延續 ${num(comp.continuity,1)}/1`:`${sector?"次產業":"官方產業"}同類股 ${peers.length} 檔；目前共振分採${r.sector_score_source||"產業代理"}`;
 return `<details><summary>👥 ${key} 共振 ${num(r.sector_score,1)}/10｜${d.strong_count||r.sector_hot_count||0}/${d.count||peers.length} 檔轉強｜點我展開</summary><div class="helptext" style="margin:7px 2px">${detail}</div><div class="group">${peers.map(x=>`<button class="g peerlink" data-code="${x.code}"><span>${x.code} ${x.name}<small> ${signed(x.day_change,1)}</small></span><span>${x.score===null||x.score===undefined?"—":num(x.score,0)}｜${x.category||"觀察"}</span></button>`).join("")}</div></details>`;
}

function partsHTML(r){'''
    ns, n = re.subn(pat2, repl2, s, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("v1.5.3 patch missing marker: groupHTML block")
    s = ns

    old_part = '<div class="part"><div class="partv">${num(c.relative_strength,0)}/15</div><div class="partl">相對強弱 ${signed(c.relative_strength_pct,1)}</div></div>'
    new_part = '<div class="part"><div class="partv">${num(c.relative_strength,0)}/15</div><div class="partl">相對強弱 ${signed(c.relative_strength_pct,1,"pp")}｜基礎${num(c.relative_base,0)}＋確認${num(c.relative_confirmation,0)}</div></div>'
    if "基礎${num(c.relative_base" not in s:
        s = must_replace(s, old_part, new_part, "relative strength UI")

    old_help = '<b>盤中動能 100：</b>價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10。籌碼只顯示為「偏多/中性/偏空背景」，不灌入盤中分數。<br>'
    new_help = '<b>盤中動能 100：</b>價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10。籌碼只顯示為「偏多/中性/偏空背景」，不灌入盤中分數。<br><b>相對強弱 15：</b>先算「個股當日漲跌－所屬市場指數漲跌」：≥+2pp得10、+1~2得8、+0.3~1得6、0~+0.3得4、-1~0得2、≤-1得0；若同時站上VWAP且近15分鐘動能為正，再加5分，最高15。<br>'
    if "相對強弱 15：</b>" not in s:
        s = must_replace(s, old_help, new_help, "relative strength help")

    old_load = 'closeMarket=await m.json();intraMarket=ij.market||closeMarket;marketLive=ij.market_intraday||{};sectorRotation=ij.sector_rotation||[];market=intraMarket;'
    new_load = 'closeMarket=await m.json();intraMarket=ij.market||closeMarket;marketLive=ij.market_intraday||{};sectorRotation=ij.sector_rotation||[];sectorFunds=cj.sector_funds||[];market=intraMarket;'
    if "sectorFunds=cj.sector_funds" not in s:
        s = must_replace(s, old_load, new_load, "load close sector funds")

    s = s.replace('$("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();render();',
                  '$("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();wireRotation();render();', 1)
    s = s.replace('$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();updateFooter();render()});',
                  '$("marketbox").innerHTML=marketHTML();rotationExpanded=false;$("rotationbox").innerHTML=rotationHTML();wireRotation();updateFooter();render()});', 1)

    write(p, s)


def patch_close_workflow():
    p = ".github/workflows/close.yml"
    s = read(p)
    if '      - "scripts/build_data.py"' not in s:
        s = must_replace(s, '      - "scripts/chip_data.py"\n', '      - "scripts/chip_data.py"\n      - "scripts/build_data.py"\n', "close trigger build_data")
    if '      - "docs/index.html"' not in s:
        s = must_replace(s, '      - "docs/hourly.js"\n', '      - "docs/hourly.js"\n      - "docs/index.html"\n      - "docs/sw.js"\n', "close trigger UI")
    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = s.replace("dogson-free-v151", "dogson-free-v153")
    s = s.replace("realtime-config.js?v=151", "realtime-config.js?v=153")
    s = s.replace("realtime.js?v=151", "realtime.js?v=153")
    write(p, s)


if __name__ == "__main__":
    patch_chip_data()
    patch_build_data()
    patch_index()
    patch_close_workflow()
    patch_sw()
    print("v1.5.3 patch applied")
