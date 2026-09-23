#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def write(rel, text):
    (ROOT / rel).write_text(text, encoding='utf-8')


def must_replace(text, old, new, label):
    if old not in text:
        raise SystemExit(f'v1.5 patch missing marker: {label}')
    return text.replace(old, new, 1)


def patch_build_data():
    p = 'scripts/build_data.py'
    s = read(p)
    s = s.replace('犬子老師飆股雷達 Free Edition v1.4.0', '犬子老師飆股雷達 Free Edition v1.5.0', 1)
    s = s.replace('個股品質 = 技術50 + 籌碼25 + 族群10（85分換算100）；大盤15分獨立',
                  '盤中＝執行雷達（即時動能100，籌碼只作背景）；盤後＝波段雷達（延續品質＋進場位置）；大盤15分獨立', 1)

    old = '"vwap_dist": round(vwap_dist, 2), "day_change": round(day_change, 2),\n        "break3": b3, "break12": b12, "trend5": trend,'
    new = '"vwap_dist": round(vwap_dist, 2), "day_change": round(day_change, 2),\n        "ret15": round(ret15, 2),\n        "break3": b3, "break12": b12, "trend5": trend,'
    s = must_replace(s, old, new, 'intraday ret15 field')

    helper = r'''

def _chip_background_label(score, coverage):
    try:
        sc = float(score)
        cov = float(coverage or 0)
    except Exception:
        return "資料不足"
    if cov < 40:
        return "資料不足"
    if sc >= 18:
        return "偏多"
    if sc <= 9:
        return "偏空"
    return "中性"


def _intraday_score_parts(r, market, sector_score_10):
    """盤中執行分 0~100；籌碼不計分，只作背景。

    30 價格結構 + 25 量價/動能 + 15 相對強弱 + 20 族群 + 10 流動性/追價風險。
    """
    close = float(r.get("close") or 0)
    vwap = float(r.get("vwap") or 0)
    pace = float(r.get("pace") or 0)
    day = float(r.get("day_change") or 0)
    ret15 = float(r.get("ret15") or 0)

    price = 0.0
    if vwap > 0 and close > vwap:
        price += 10
    if r.get("break3"):
        price += 8
    if r.get("break12"):
        price += 6
    if r.get("trend5"):
        price += 6
    price = min(30.0, price)

    flow = 0.0
    if 1.5 <= pace < 3.5:
        flow += 15
    elif 1.2 <= pace < 1.5:
        flow += 10
    elif 3.5 <= pace <= 5:
        flow += 10
    elif pace >= 1.0:
        flow += 5
    if 0.2 <= ret15 <= 2.5:
        flow += 6
    elif ret15 > 0:
        flow += 3
    if 0.5 <= day <= 6.5:
        flow += 4
    elif 0 < day < 0.5:
        flow += 2
    flow = min(25.0, flow)

    comps = (market or {}).get("components") or {}
    side = "otc" if str(r.get("market")) == "上櫃" else "taiex"
    bench = ((comps.get(side) or {}).get("change_pct"))
    try:
        bench = float(bench) if bench is not None else 0.0
    except Exception:
        bench = 0.0
    rel_pct = day - bench
    if rel_pct >= 2.0:
        relative = 10.0
    elif rel_pct >= 1.0:
        relative = 8.0
    elif rel_pct >= 0.3:
        relative = 6.0
    elif rel_pct >= 0:
        relative = 4.0
    elif rel_pct > -1.0:
        relative = 2.0
    else:
        relative = 0.0
    if close > 0 and vwap > 0 and close >= vwap and ret15 > 0:
        relative += 5.0
    relative = min(15.0, relative)

    sector = max(0.0, min(20.0, float(sector_score_10 or 0) * 2.0))

    level = str(r.get("liquidity_level") or "未知")
    liquidity = 5.0 if level == "活躍" else 4.0 if level == "正常" else 2.0 if level == "偏低" else 3.0
    hot_n = len(r.get("overheat_reasons") or [])
    risk = 5.0 if hot_n == 0 else 2.0 if hot_n == 1 else 0.0
    if float(r.get("vwap_dist") or 0) < -2.0:
        risk = max(0.0, risk - 2.0)
    liquidity_risk = min(10.0, liquidity + risk)

    total = max(0.0, min(100.0, price + flow + relative + sector + liquidity_risk))
    return round(total, 1), {
        "price_structure": round(price, 1),
        "flow_volume": round(flow, 1),
        "relative_strength": round(relative, 1),
        "relative_strength_pct": round(rel_pct, 2),
        "sector": round(sector, 1),
        "liquidity_risk": round(liquidity_risk, 1),
    }


def _close_entry_position_score(r):
    """波段進場位置 0~100；和『這家公司/趨勢好不好』分開。"""
    score = 40.0
    if r.get("trend"):
        score += 10
    if r.get("break20"):
        score += 5
    elif r.get("break3"):
        score += 3

    try:
        dist = float(r.get("dist20"))
    except Exception:
        dist = 999.0
    if 0 <= dist <= 3:
        score += 20
    elif dist <= 7:
        score += 15
    elif dist <= 10:
        score += 8
    elif dist <= 15:
        score += 2
    elif dist < 0:
        score -= 10
    else:
        score -= 10

    try:
        vx = float(r.get("vol_x"))
    except Exception:
        vx = 0.0
    if 1.2 <= vx <= 2.5:
        score += 10
    elif 0.8 <= vx < 1.2:
        score += 5
    elif vx > 4:
        score -= 5

    try:
        ret5 = float(r.get("ret5"))
    except Exception:
        ret5 = 999.0
    if 0 <= ret5 <= 8:
        score += 10
    elif ret5 <= 15:
        score += 5
    elif ret5 > 20:
        score -= 10

    sup = r.get("support") or {}
    try:
        upper = float(sup.get("high"))
        close = float(r.get("close"))
        if upper > 0 and close >= upper and (close / upper - 1) <= 0.03:
            score += 5
    except Exception:
        pass

    score -= min(25.0, 10.0 * len(r.get("overheat_reasons") or []))
    return round(max(0.0, min(100.0, score)), 1)
'''
    marker = '\ndef add_component_scores(rows, market, preliminary_intraday=False):'
    if '_intraday_score_parts' not in s:
        if marker not in s:
            raise SystemExit('v1.5 patch missing add_component_scores marker')
        s = s.replace(marker, helper + marker, 1)

    pat = re.compile(r'''        cs = float\(r\.get\("chip_score", 12\.5\)\)\n        liq_adjust = float\(r\.get\("liquidity_adjust", 0\)\)\n        # v1\.4: market is an independent operation-environment gauge\.  It must not\n        # make every stock's quality rise/fall by the same amount\.\n        stock_raw = float\(r\.get\("technical_score", 0\)\) \+ cs \+ sec \+ liq_adjust\n        stock_raw = max\(0\.0, min\(85\.0, stock_raw\)\)\n        r\["stock_raw_score"\] = round\(stock_raw, 1\)\n        r\["score"\] = round\(stock_raw / 85\.0 \* 100\.0, 1\)\n        r\["market_in_quality_score"\] = False\n\n        chip_cov = float\(r\.get\("chip_coverage_pct"\) or 0\)\n        r\["score_reliable"\] = bool\(chip_cov >= 60\)\n        if not r\["score_reliable"\]:\n            r\["quality_label"\] = "資料待補"\n        elif r\["score"\] >= 80:\n            r\["quality_label"\] = "高共振"\n        elif r\["score"\] >= 70:\n            r\["quality_label"\] = "強"\n        else:\n            r\["quality_label"\] = "一般"\n        r\["quality_reference"\] = quality_reference\n        r\["quality_pass_market"\] = bool\(r\["score_reliable"\] and r\["score"\] >= quality_reference\)\n''')
    repl = '''        cs = float(r.get("chip_score", 12.5))\n        chip_cov = float(r.get("chip_coverage_pct") or 0)\n        liq_adjust = float(r.get("liquidity_adjust", 0))\n        r["market_in_quality_score"] = False\n        r["chip_background"] = _chip_background_label(cs, chip_cov)\n        r["chip_background_score"] = round(cs, 1)\n\n        if preliminary_intraday:\n            # v1.5：盤中是執行雷達。籌碼僅作昨日/最近盤後背景，不灌入即時動能分。\n            intraday_score, intraday_parts = _intraday_score_parts(r, market, sec)\n            r["intraday_score"] = intraday_score\n            r["intraday_components"] = intraday_parts\n            r["stock_raw_score"] = intraday_score\n            r["score"] = intraday_score\n            r["score_type"] = "intraday_execution"\n            r["score_reliable"] = True\n            if intraday_score >= 82:\n                r["quality_label"] = "強動能"\n            elif intraday_score >= 70:\n                r["quality_label"] = "轉強"\n            elif intraday_score >= 55:\n                r["quality_label"] = "中性"\n            else:\n                r["quality_label"] = "轉弱"\n            r["quality_reference"] = 70\n            r["quality_pass_market"] = bool(intraday_score >= 70)\n        else:\n            # v1.5：盤後是波段雷達。延續品質與進場位置分開，避免『好股票＝現在可追』。\n            stock_raw = float(r.get("technical_score", 0)) + cs + sec + liq_adjust\n            stock_raw = max(0.0, min(85.0, stock_raw))\n            swing = round(stock_raw / 85.0 * 100.0, 1)\n            r["stock_raw_score"] = round(stock_raw, 1)\n            r["score"] = swing\n            r["swing_quality_score"] = swing\n            r["swing_continuation_score"] = swing\n            r["entry_position_score"] = _close_entry_position_score(r)\n            r["score_type"] = "swing_continuation"\n            r["score_reliable"] = bool(chip_cov >= 60)\n            if not r["score_reliable"]:\n                r["quality_label"] = "資料待補"\n            elif swing >= 80:\n                r["quality_label"] = "高延續"\n            elif swing >= 70:\n                r["quality_label"] = "強"\n            else:\n                r["quality_label"] = "一般"\n            r["quality_reference"] = quality_reference\n            r["quality_pass_market"] = bool(r["score_reliable"] and swing >= quality_reference)\n'''
    s, n = pat.subn(repl, s, count=1)
    if n != 1:
        raise SystemExit(f'v1.5 score block replacement count={n}')

    s = s.replace('quality_order = {"高共振": 0, "強": 1, "一般": 2}',
                  'quality_order = {"強動能": 0, "高延續": 0, "轉強": 1, "強": 1, "中性": 2, "一般": 2, "轉弱": 3, "資料待補": 4}', 1)

    s = s.replace('"score_formula": {"technical": 50, "chip": 25, "sector": 10, "stock_raw_max": 85, "normalized_to": 100, "market_separate": 15},',
                  '"score_formula": {"mode": "swing", "technical": 50, "chip": 25, "sector": 10, "stock_raw_max": 85, "normalized_to": 100, "entry_position": 100, "market_separate": 15},', 1)
    # second occurrence is intraday
    s = s.replace('"score_formula": {"technical": 50, "chip": 25, "sector": 10, "stock_raw_max": 85, "normalized_to": 100, "market_separate": 15},',
                  '"score_formula": {"mode": "intraday_execution", "price_structure": 30, "flow_volume": 25, "relative_strength": 15, "sector": 20, "liquidity_risk": 10, "chip": "background_only", "market_separate": 15},', 1)
    s = s.replace('"version": "1.4.0-free"', '"version": "1.5.0-free"')
    write(p, s)


def patch_index():
    p = 'docs/index.html'
    s = read(p)
    s = s.replace('Free Edition v1.4.0｜官方即時價＋獨立大盤＋多因子族群',
                  'Free Edition v1.5.0｜盤中執行雷達＋盤後波段雷達＋可展開族群', 1)

    extra_css = '''\n.parts.intradayparts,.parts.closeparts{grid-template-columns:repeat(2,1fr)}\n.peerpeekback{position:fixed;inset:0;background:rgba(0,0,0,.58);z-index:40;display:flex;align-items:flex-end;justify-content:center;padding:14px}.peerpeek{width:min(720px,100%);background:#161c26;border:1px solid #344052;border-radius:18px;padding:14px;box-shadow:0 18px 50px rgba(0,0,0,.45)}.peerpeektop{display:flex;justify-content:space-between;gap:10px}.peerpeekname{font-size:19px;font-weight:900}.peerpeekgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin-top:10px}.peerpeekitem{background:#0e131a;border:1px solid #29313e;border-radius:10px;padding:9px}.peerpeekv{font-weight:900}.peerpeekl{font-size:10px;color:var(--muted);margin-top:3px}.peerpeekactions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.peerpeekbtn{border:1px solid #36506f;background:#17304a;color:#cde6ff;border-radius:11px;padding:10px;font-weight:850}.peerpeekbtn.secondary{background:#242b38;border-color:#343d4d;color:#d4dae4}\n'''
    if '.peerpeekback{' not in s:
        s = s.replace('</style>', extra_css + '</style>', 1)

    s = s.replace('<b>技術 50：</b>突破、均線、量能、RSI、MACD、VWAP 等。<br>\n    <b>籌碼 25：</b>外資連3買、借券賣出連3減、投信、融資。覆蓋率低於60%時品質總分會標示「資料待補」，不再用假精準分數誤導。盤後會在14:25、20:30、23:40及次日08:15自動重抓，補齊較晚公布的融資與借券資料。<br>',
'''<b>盤中動能 100：</b>價格結構30＋量價/動能25＋相對強弱15＋族群20＋流動性/追價風險10。籌碼只顯示為「偏多/中性/偏空背景」，不灌入盤中分數。<br>\n    <b>盤後波段：</b>波段延續＝技術50＋籌碼25＋族群10換算100；另外獨立計算「進場位置100」，避免好股票在過熱位置仍被誤認為好買點。<br>\n    <b>籌碼：</b>外資連3買、借券賣出連3減、投信、融資。盤中只作背景；盤後才正式進入波段延續評分。盤後會在14:25、20:30、23:40及次日08:15補抓。<br>''', 1)
    s = s.replace('<b>個股品質：</b>技術50＋籌碼25＋族群10＝85分，再換算為100分；大盤不再灌進每一檔個股分數。<br>',
'''<b>兩套個股分數：</b>盤中看「盤中動能」，用來做當沖/庫存進出/族群輪動；盤後看「波段延續＋進場位置」，用來規劃隔日與波段。大盤15分始終獨立，不灌入個股。<br>''', 1)
    s = s.replace('<b>品質標籤：</b>80分以上＝高共振、70～79＝強、70以下＝一般。先看「階段」，再看「品質」。',
                  '<b>分數標籤：</b>盤中＝強動能/轉強/中性/轉弱；盤後＝高延續/強/一般。先看用途，再看階段與分數。', 1)

    parts_pat = re.compile(r'function partsHTML\(r\)\{\n.*?\n\}', re.S)
    parts_new = '''function partsHTML(r){\n if(mode==="intraday"){\n  const c=r.intraday_components||{};\n  return `<div class="parts intradayparts">\n   <div class="part"><div class="partv">${num(c.price_structure,0)}/30</div><div class="partl">價格結構</div></div>\n   <div class="part"><div class="partv">${num(c.flow_volume,0)}/25</div><div class="partl">量價/動能</div></div>\n   <div class="part"><div class="partv">${num(c.relative_strength,0)}/15</div><div class="partl">相對強弱 ${signed(c.relative_strength_pct,1)}</div></div>\n   <div class="part"><div class="partv">${num(c.sector,0)}/20</div><div class="partl">族群共振</div></div>\n   <div class="part"><div class="partv">${num(c.liquidity_risk,0)}/10</div><div class="partl">流動性/追價風險</div></div>\n   <div class="part"><div class="partv">${r.chip_background||"資料不足"}</div><div class="partl">籌碼背景 · 不計分</div></div>\n  </div>`;\n }\n return `<div class="parts closeparts">\n  <div class="part"><div class="partv">${num(r.technical_score,0)}/50</div><div class="partl">日K技術</div></div>\n  <div class="part"><div class="partv">${(+r.chip_coverage_pct||0)<60?"待補":num(r.chip_score,0)+"/25"}</div><div class="partl">籌碼${(+r.chip_coverage_pct||0)<60?" · 資料不足":""}</div></div>\n  <div class="part"><div class="partv">${num(r.sector_score,1)}/10</div><div class="partl">族群延續</div></div>\n  <div class="part"><div class="partv">${num(r.entry_position_score,0)}/100</div><div class="partl">進場位置</div></div>\n </div>`;\n}'''
    s, n = parts_pat.subn(parts_new, s, count=1)
    if n != 1:
        raise SystemExit(f'v1.5 index partsHTML replacement count={n}')

    old_top = '''<div class="top"><div class="stockleft"><button class="star ${watched(r.code)?"on":""}" onclick="toggleWatch('${r.code}')">${watched(r.code)?"★":"☆"}</button><div><div class="name">${r.name}<span class="code">${r.code}</span></div><div class="sub">${r.industry_name||r.industry||"未分類"}${r.sector_group?" · "+r.sector_group:""} · ${mode==="intraday"?(r.time||""):(r.date||"")}</div><span class="cat ${cls(r.category)}">${r.category}</span><span class="quality ${qualityCls(r.quality_label)}">品質：${r.quality_label||"一般"}</span></div></div><div><div class="score">${r.score_reliable===false?"—":num(r.score,0)}</div><div class="label">${r.score_reliable===false?"籌碼覆蓋不足":"品質總分 /100"}</div></div></div>'''
    new_top = '''<div class="top"><div class="stockleft"><button class="star ${watched(r.code)?"on":""}" onclick="toggleWatch('${r.code}')">${watched(r.code)?"★":"☆"}</button><div><div class="name">${r.name}<span class="code">${r.code}</span></div><div class="sub">${r.industry_name||r.industry||"未分類"}${r.sector_group?" · "+r.sector_group:""} · ${mode==="intraday"?(r.time||""):(r.date||"")}</div><span class="cat ${cls(r.category)}">${r.category}</span><span class="quality ${qualityCls(r.quality_label)}">${mode==="intraday"?"動能":"波段"}：${r.quality_label||"一般"}</span></div></div><div><div class="score">${mode==="intraday"?num(r.intraday_score??r.score,0):(r.score_reliable===false?"—":num(r.swing_quality_score??r.score,0))}</div><div class="label">${mode==="intraday"?"盤中動能 /100":(r.score_reliable===false?"籌碼覆蓋不足":"波段延續 /100")}</div></div></div>'''
    s = must_replace(s, old_top, new_top, 'card score header')

    peek = '''\nfunction showPeerPeek(code){\n const r=rows.find(x=>String(x.code)===String(code));if(!r)return;\n document.getElementById("peerPeekBack")?.remove();\n const back=document.createElement("div");back.id="peerPeekBack";back.className="peerpeekback";\n const intr=mode==="intraday";\n const items=intr?[\n  ["現價",num(r.close,2)],["盤中動能",num(r.intraday_score??r.score,0)+"/100"],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["族群共振",num(r.sector_score,1)+"/10"],["籌碼背景",r.chip_background||"資料不足"]\n ]:[\n  ["收盤",num(r.close,2)],["波段延續",(r.score_reliable===false?"待補":num(r.swing_quality_score??r.score,0)+"/100")],["進場位置",num(r.entry_position_score,0)+"/100"],["籌碼",(+r.chip_coverage_pct||0)<60?"待補":num(r.chip_score,0)+"/25"],["族群共振",num(r.sector_score,1)+"/10"],["階段",r.category||"觀察"]\n ];\n back.innerHTML=`<div class="peerpeek"><div class="peerpeektop"><div><div class="peerpeekname">${r.name} <span class="code">${r.code}</span></div><div class="sub">${r.sector_group||r.industry_name||r.industry||"未分類"}｜${signed(r.day_change,1)}</div></div><span class="cat ${cls(r.category)}">${r.category||"觀察"}</span></div><div class="peerpeekgrid">${items.map(x=>`<div class="peerpeekitem"><div class="peerpeekv">${x[1]}</div><div class="peerpeekl">${x[0]}</div></div>`).join("")}</div><div class="peerpeekactions"><button class="peerpeekbtn" data-peer-open="${r.code}">查看完整個股</button><button class="peerpeekbtn secondary" data-peer-close="1">關閉</button></div></div>`;\n document.body.appendChild(back);\n}\nfunction focusPeer(code){\n $("q").value=code;filter="all";watchOnly=false;\n document.querySelectorAll(".filter").forEach(x=>x.classList.toggle("on",x.dataset.f==="all"));\n document.getElementById("peerPeekBack")?.remove();render();\n setTimeout(()=>document.querySelector(".card")?.scrollIntoView({behavior:"smooth",block:"start"}),30);\n}\n'''
    if 'function showPeerPeek(code)' not in s:
        s = s.replace('\nfunction render(){', peek + '\nfunction render(){', 1)

    old_click = '''$("cards").addEventListener("click",e=>{\n const b=e.target.closest(".peerlink");if(!b)return;\n const code=b.dataset.code;if(!code)return;\n $("q").value=code;filter="all";watchOnly=false;\n document.querySelectorAll(".filter").forEach(x=>x.classList.toggle("on",x.dataset.f==="all"));\n render();\n setTimeout(()=>document.querySelector(".card")?.scrollIntoView({behavior:"smooth",block:"start"}),30);\n});'''
    new_click = '''document.addEventListener("click",e=>{\n const peer=e.target.closest(".peerlink");\n if(peer){const code=peer.dataset.code;if(code)showPeerPeek(code);return}\n const open=e.target.closest("[data-peer-open]");if(open){focusPeer(open.dataset.peerOpen);return}\n if(e.target.closest("[data-peer-close]")||e.target.id==="peerPeekBack")document.getElementById("peerPeekBack")?.remove();\n});'''
    s = must_replace(s, old_click, new_click, 'peer click mini card')

    s = s.replace('mode==="intraday"?"盤中：純即時大盤 / 5分K / 資金輪動":"盤後：正式收盤日K / 籌碼 / 同交易日大盤 / 支撐壓力"',
                  'mode==="intraday"?"盤中：執行雷達 / 動能 / 當沖與庫存進出 / 族群輪動":"盤後：波段雷達 / 延續性 / 進場位置 / 60分K"', 1)
    s = s.replace('./realtime-config.js?v=140', './realtime-config.js?v=150')
    s = s.replace('./realtime.js?v=140', './realtime.js?v=150')
    write(p, s)


def patch_hourly():
    p = 'docs/hourly.js'
    s = read(p)
    if "let hourlyExpanded=false;" not in s:
        s = must_replace(s, "  let selected='ALL';", "  let selected='ALL';\n  let hourlyExpanded=false;", 'hourly expanded state')
    if '.hourlytoggle{' not in s:
        s = s.replace('      .hourlyfilters{', '      .hourlytoggle{border:1px solid #36506f;background:#17304a;color:#cde6ff;border-radius:10px;padding:7px 10px;font-size:11px;font-weight:850;white-space:nowrap}.hourlysummary{font-size:11px;color:#9ba5b6;margin-top:7px}\n      .hourlyfilters{', 1)

    pat = re.compile(r'  function renderPanel\(\)\{\n.*?\n  \}\n\n  function rowHTML', re.S)
    new = '''  function renderPanel(){\n    const box=ensureBox();if(!box)return;\n    const isClose=(typeof mode!=='undefined'&&mode==='close');\n    box.style.display=isClose?'block':'none';\n    if(!isClose)return;\n    const rows=filteredRows();\n    const counts=data.entry_light_counts||{};\n    const updated=data.updated_at?new Date(data.updated_at).toLocaleString('zh-TW',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}):'—';\n    const body=hourlyExpanded?`\n      <div class="hourlyfilters">\n        ${buttonHTML('ALL','全部60K')}${buttonHTML('PRE_CROSS','🟡 金叉前夕')}${buttonHTML('EARLY','🟢 初升')}${buttonHTML('STABLE_CONT','🔵 穩定續航')}${buttonHTML('ACCEL_CONT','🚀 加速續航')}${buttonHTML('GREEN',`🟢 位置舒服 ${counts.GREEN??''}`)}\n      </div>\n      <div class="hourlylist">${rows.length?rows.slice(0,18).map(rowHTML).join(''):'<div class="hourlyempty">目前沒有符合這個60K條件的股票。</div>'}</div>\n      <div class="hourlymore">目前共 ${data.rows?.length||0} 檔符合60K生命週期條件；🟢 ${counts.GREEN||0}｜🟡 ${counts.YELLOW||0}｜🟠 ${counts.ORANGE||0}｜🔴 ${counts.RED||0}。點股票會帶到下方完整卡片。</div>`:\n      `<div class="hourlysummary">符合 ${data.rows?.length||0} 檔｜🟢位置舒服 ${counts.GREEN||0}｜收合時不占版面，點「展開」再挑60K股票。</div>`;\n    box.innerHTML=`\n      <div class="hourlytop"><div><div class="hourlytitle">⏱️ 60分K 趨勢雷達</div><div class="hourlysub">四種生命週期＋進場燈號；預設收合，避免手機版被名單擋住。</div></div><div style="display:flex;gap:8px;align-items:flex-start"><div class="hourlystamp">${data.trade_date||''}<br>${updated}</div><button id="hourlyToggle" class="hourlytoggle">${hourlyExpanded?'收合 ▲':'展開 ▼'}</button></div></div>\n      ${body}`;\n    box.querySelector('#hourlyToggle')?.addEventListener('click',()=>{hourlyExpanded=!hourlyExpanded;renderPanel()});\n    box.querySelectorAll('[data-h60]').forEach(b=>b.onclick=()=>{selected=b.dataset.h60;renderPanel()});\n    box.querySelectorAll('[data-hourly-code]').forEach(b=>b.onclick=()=>focusStock(b.dataset.hourlyCode));\n  }\n\n  function rowHTML'''
    s, n = pat.subn(new, s, count=1)
    if n != 1:
        raise SystemExit(f'v1.5 hourly render replacement count={n}')
    write(p, s)


def patch_sw():
    p='docs/sw.js'
    s=read(p)
    s=s.replace("const CACHE='dogson-free-v140';", "const CACHE='dogson-free-v150';", 1)
    s=s.replace("realtime-config.js?v=140", "realtime-config.js?v=150")
    s=s.replace("realtime.js?v=140", "realtime.js?v=150")
    write(p,s)


if __name__ == '__main__':
    patch_build_data()
    patch_index()
    patch_hourly()
    patch_sw()
    print('v1.5 patch applied')
