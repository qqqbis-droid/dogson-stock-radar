#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply Dogson Radar v1.4.0 upgrade.

Goals:
1) MIS official quote overlay for intraday rows; Yahoo 5m remains structure source.
2) Stock quality score excludes market score; market 15 is an independent operation gauge.
3) Sector resonance becomes breadth + strength + volume + leaders + continuity.
4) Sector peers become clickable in the UI.
5) UI shows quote time and 5m structure time separately.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")
    print("patched", rel)


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"missing patch target: {label}")
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# build_data.py
# ---------------------------------------------------------------------------
p = "scripts/build_data.py"
s = read(p)
s = s.replace("犬子老師飆股雷達 Free Edition v1.3.7", "犬子老師飆股雷達 Free Edition v1.4.0", 1)
s = s.replace("總分 = 技術 50 + 籌碼 25 + 族群 10 + 大盤 15", "個股品質 = 技術50 + 籌碼25 + 族群10（85分換算100）；大盤15分獨立", 1)

# Insert official MIS stock quote layer after intraday_index_snapshot.
marker = "\ndef _weighted_pct(rows, predicate, weight_key=\"current_turnover\"):\n"
if "def intraday_stock_snapshot(" not in s:
    if marker not in s:
        raise RuntimeError("missing intraday quote insertion marker")
    func = r'''

def intraday_stock_snapshot(universe_df, codes=None):
    """Official TWSE MIS near-real-time quotes for listed + OTC stocks.

    This is intentionally a quote layer, not a replacement for the 5-minute
    structure engine.  MIS supplies last price / previous close / official time;
    Yahoo 5m continues to supply VWAP, breakout, pace and support/resistance.
    """
    if universe_df is None or universe_df.empty:
        return {}
    wanted = set(str(c) for c in (codes or []))
    cols = ["code", "market"]
    recs = universe_df[cols].astype(str).to_dict("records")
    if wanted:
        recs = [r for r in recs if r["code"] in wanted]
    now = now_tw()
    today = now.date()
    out = {}

    def fnum(v):
        try:
            z = str(v or "").replace(",", "").strip()
            return float(z) if z not in {"", "-", "--"} else None
        except Exception:
            return None

    for i in range(0, len(recs), 80):
        part = recs[i:i+80]
        ex_ch = "|".join(
            f"{'otc' if r['market'] == '上櫃' else 'tse'}_{r['code']}.tw"
            for r in part
        )
        try:
            rr = requests.get(
                "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
                params={"ex_ch": ex_ch, "json": "1", "delay": "0", "_": int(now.timestamp()*1000)},
                headers={
                    "User-Agent": "Mozilla/5.0 DogsonRadar/1.4.0",
                    "Referer": "https://mis.twse.com.tw/stock/index.jsp",
                    "Accept": "application/json,text/plain,*/*",
                },
                timeout=20,
            )
            rr.raise_for_status()
            for x in rr.json().get("msgArray") or []:
                code = str(x.get("c") or "").strip()
                td = _parse_mis_trade_date(x.get("d"))
                if not code or td != today:
                    continue
                last = fnum(x.get("z"))
                prev = fnum(x.get("y"))
                if last is None or last <= 0:
                    continue
                tm = str(x.get("t") or "").strip()
                # Some MIS responses include HH:MM:SS, some HH:MM.
                if len(tm) >= 5:
                    tm = tm[:8]
                out[code] = {
                    "date": td.isoformat(),
                    "time": tm,
                    "close": last,
                    "prev_close": prev,
                    "change_pct": ((last / prev - 1) * 100) if prev and prev > 0 else None,
                    "volume_lots": fnum(x.get("v")),
                    "source": "TWSE MIS",
                }
        except Exception as e:
            print("MIS intraday stock batch", i, e)
    print("MIS intraday stock quotes", len(out), "/", len(recs))
    return out
'''
    s = s.replace(marker, func + marker, 1)

# Add multi-factor sector resonance helper inside add_component_scores.
needle = '''    quality_reference = market.get("radar_threshold", 76)\n    market_score = float(market.get("market_score", 7.5))\n'''
if "def _resonance_stats(group_rows):" not in s:
    helper = '''    def _resonance_stats(group_rows):\n        total = len(group_rows)\n        if not total:\n            return {"score": 0.0, "count": 0, "strong_count": 0}\n        strong = [x for x in group_rows if float(x.get("technical_score") or 0) >= 30 and not x.get("overheat_reasons")]\n        up_pct = sum(1 for x in group_rows if float(x.get("day_change") or 0) > 0) / total * 100\n        strong_pct = len(strong) / total * 100\n        avg_tech = sum(float(x.get("technical_score") or 0) for x in group_rows) / total\n        acts = []\n        for x in group_rows:\n            v = x.get("pace") if x.get("pace") is not None else x.get("vol_x")\n            if v is not None:\n                try: acts.append(float(v))\n                except Exception: pass\n        avg_activity = sum(acts) / len(acts) if acts else 1.0\n        leaders = [x for x in group_rows if float(x.get("technical_score") or 0) >= 35 and float(x.get("day_change") or 0) >= 1]\n        trend_hits = sum(1 for x in group_rows if x.get("trend5") or x.get("trend") or x.get("break12") or x.get("break20"))\n        continuity_pct = trend_hits / total * 100\n\n        # Strong-stock turnover share is especially useful intraday: two large leaders\n        # matter more than many tiny red/green prints.\n        total_turn = sum(float(x.get("current_turnover") or 0) for x in group_rows)\n        strong_turn = sum(float(x.get("current_turnover") or 0) for x in strong)\n        strong_turn_pct = (strong_turn / total_turn * 100) if total_turn > 0 else strong_pct\n\n        breadth_score = 3.0 if up_pct >= 70 else 2.5 if up_pct >= 60 else 1.5 if up_pct >= 50 else 0.5 if up_pct >= 40 else 0.0\n        strength_basis = max(strong_pct, strong_turn_pct)\n        strength_score = 2.0 if strength_basis >= 60 else 1.5 if strength_basis >= 45 else 1.0 if strength_basis >= 30 else 0.5 if avg_tech >= 25 else 0.0\n        volume_score = 2.0 if avg_activity >= 2.0 else 1.5 if avg_activity >= 1.5 else 1.0 if avg_activity >= 1.2 else 0.5 if avg_activity >= 1.0 else 0.0\n        leader_score = 2.0 if len(leaders) >= 2 else 1.2 if len(leaders) == 1 else 0.0\n        continuity_score = 1.0 if continuity_pct >= 60 else 0.5 if continuity_pct >= 40 else 0.0\n        score = round(min(10.0, breadth_score + strength_score + volume_score + leader_score + continuity_score), 1)\n        return {\n            "score": score, "count": total, "strong_count": len(strong),\n            "up_pct": round(up_pct, 1), "strong_pct": round(strong_pct, 1),\n            "strong_turnover_pct": round(strong_turn_pct, 1),\n            "avg_technical": round(avg_tech, 1), "activity": round(avg_activity, 2),\n            "leader_count": len(leaders), "continuity_pct": round(continuity_pct, 1),\n            "components": {\n                "breadth": breadth_score, "strength": strength_score,\n                "volume": volume_score, "leaders": leader_score,\n                "continuity": continuity_score,\n            },\n        }\n\n    quality_reference = 76\n    market_score = float(market.get("market_score", 7.5))\n'''
    if needle not in s:
        raise RuntimeError("missing add_component_scores helper marker")
    s = s.replace(needle, helper, 1)

old = '''        if key:\n            n = int(hot.get(key, 0))\n            sec = sector_score(n)\n            source = "次產業"\n            label = key\n            ratio = None\n        else:\n            n = int(industry_hot.get(industry, 0)) if industry and industry != "未分類" else 0\n            total_n = int(industry_total.get(industry, 0)) if industry and industry != "未分類" else 0\n            ratio = (n / total_n) if total_n else 0\n            sec = sector_score(n, ratio, True)\n            source = "官方產業代理" if total_n else "待分類"\n            label = industry if total_n else "待分類"\n'''
new = '''        stat = None\n        group_rows = []\n        if key:\n            group_rows = [x for x in rows if str(x.get("sector_group") or "").strip() == key]\n            stat = _resonance_stats(group_rows)\n            n = int(stat.get("strong_count") or 0)\n            sec = float(stat.get("score") or 0)\n            source = "次產業多因子"\n            label = key\n            ratio = (n / len(group_rows)) if group_rows else None\n        else:\n            n = int(industry_hot.get(industry, 0)) if industry and industry != "未分類" else 0\n            total_n = int(industry_total.get(industry, 0)) if industry and industry != "未分類" else 0\n            ratio = (n / total_n) if total_n else 0\n            sec = sector_score(n, ratio, True)\n            source = "官方產業代理" if total_n else "待分類"\n            label = industry if total_n else "待分類"\n'''
s = replace_once(s, old, new, "sector scoring block")

needle = '''        r["sector_hot_ratio"] = round(ratio * 100, 1) if ratio is not None else None\n        r["market_score"] = market_score\n'''
new = '''        r["sector_hot_ratio"] = round(ratio * 100, 1) if ratio is not None else None\n        r["sector_detail"] = stat\n        if group_rows:\n            peers = sorted(group_rows, key=lambda x: (float(x.get("technical_score") or 0), float(x.get("day_change") or 0), float(x.get("current_turnover") or 0)), reverse=True)[:10]\n            r["sector_peers"] = [{\n                "code": x.get("code"), "name": x.get("name"),\n                "technical_score": x.get("technical_score"),\n                "score": x.get("score"), "day_change": x.get("day_change"),\n                "category": x.get("category"),\n            } for x in peers]\n        else:\n            r["sector_peers"] = []\n        r["market_score"] = market_score\n'''
s = replace_once(s, needle, new, "sector detail fields")

old = '''        cs = float(r.get("chip_score", 12.5))\n        liq_adjust = float(r.get("liquidity_adjust", 0))\n        total = float(r.get("technical_score", 0)) + cs + sec + market_score + liq_adjust\n        r["score"] = round(max(0, min(100, total)), 1)\n\n        chip_cov = float(r.get("chip_coverage_pct") or 0)\n        same_day = (not r.get("market_trade_date")) or str(r.get("date")) == str(r.get("market_trade_date"))\n        r["score_reliable"] = bool(chip_cov >= 60 and r.get("market_data_complete", True) and same_day)\n'''
new = '''        cs = float(r.get("chip_score", 12.5))\n        liq_adjust = float(r.get("liquidity_adjust", 0))\n        # v1.4: market is an independent operation-environment gauge.  It must not\n        # make every stock's quality rise/fall by the same amount.\n        stock_raw = float(r.get("technical_score", 0)) + cs + sec + liq_adjust\n        stock_raw = max(0.0, min(85.0, stock_raw))\n        r["stock_raw_score"] = round(stock_raw, 1)\n        r["score"] = round(stock_raw / 85.0 * 100.0, 1)\n        r["market_in_quality_score"] = False\n\n        chip_cov = float(r.get("chip_coverage_pct") or 0)\n        r["score_reliable"] = bool(chip_cov >= 60)\n'''
s = replace_once(s, old, new, "independent stock score")

# Overlay MIS quote layer before market/rotation calculation.
needle = '''    market_live = intraday_index_snapshot()\n    sector_rotation = build_sector_rotation(rows)\n'''
new = '''    # Official quote overlay: all rows get the freshest MIS last price available.\n    # Structure fields (technical_score/breakouts/VWAP/support) still come from the\n    # 5-minute engine; quote time is stored separately so freshness is transparent.\n    quote_map = intraday_stock_snapshot(u, [r.get("code") for r in rows])\n    structure_times = [str(r.get("time") or "")[:5] for r in rows if r.get("time")]\n    for r in rows:\n        r["structure_time"] = r.get("time")\n        r["structure_close"] = r.get("close")\n        q = quote_map.get(str(r.get("code")))\n        if not q:\n            continue\n        r["quote_date"] = q.get("date")\n        r["quote_time"] = q.get("time")\n        r["quote_source"] = q.get("source")\n        r["quote_close"] = q.get("close")\n        r["close"] = q.get("close")\n        if q.get("change_pct") is not None:\n            r["day_change"] = round(float(q.get("change_pct")), 2)\n        if r.get("vwap"):\n            try: r["vwap_dist"] = round((float(r["close"]) / float(r["vwap"]) - 1) * 100, 2)\n            except Exception: pass\n\n    quote_times = [str(q.get("time") or "")[:5] for q in quote_map.values() if q.get("time")]\n    quote_latest = max(quote_times) if quote_times else None\n    structure_latest = max(structure_times) if structure_times else None\n\n    market_live = intraday_index_snapshot()\n    sector_rotation = build_sector_rotation(rows)\n'''
s = replace_once(s, needle, new, "MIS row overlay")

s = s.replace('"score_formula": {"technical": 50, "chip": 25, "sector": 10, "market": 15},', '"score_formula": {"technical": 50, "chip": 25, "sector": 10, "stock_raw_max": 85, "normalized_to": 100, "market_separate": 15},')

needle = '''        "sector_rotation": sector_rotation,\n        "score_formula": {"technical": 50, "chip": 25, "sector": 10, "stock_raw_max": 85, "normalized_to": 100, "market_separate": 15},\n        "rows": rows,\n'''
new = '''        "sector_rotation": sector_rotation,\n        "quote_layer": {\n            "source": "TWSE MIS", "coverage": len(quote_map), "row_count": len(rows),\n            "latest_time": quote_latest, "structure_latest_time": structure_latest,\n            "note": "現價/當日漲跌採官方MIS；VWAP/突破/量速/支撐壓力仍採5分K結構",\n        },\n        "score_formula": {"technical": 50, "chip": 25, "sector": 10, "stock_raw_max": 85, "normalized_to": 100, "market_separate": 15},\n        "rows": rows,\n'''
if needle in s:
    s = s.replace(needle, new, 1)
else:
    raise RuntimeError("missing quote_layer dump marker")

s = s.replace('"version": "1.3.6-free"', '"version": "1.4.0-free"')
write(p, s)


# ---------------------------------------------------------------------------
# sector_groups.py - narrower and broader coverage for common Taiwan themes
# ---------------------------------------------------------------------------
sector = '''# -*- coding: utf-8 -*-\n"""犬子老師雷達：官方大產業 + 實戰較窄次產業/題材群組。\n\nv1.4：優先使用較窄群組，讓族群共振不再被「整個電子零組件/半導體」稀釋。\n同一股票若跨題材，仍以第一個、最主要的映射為主，避免同一筆資料重複灌分。\n"""\n\nINDUSTRY_NAMES = {\n    "01": "水泥工業", "02": "食品工業", "03": "塑膠工業", "04": "紡織纖維",\n    "05": "電機機械", "06": "電器電纜", "08": "玻璃陶瓷", "09": "造紙工業",\n    "10": "鋼鐵工業", "11": "橡膠工業", "12": "汽車工業", "14": "建材營造",\n    "15": "航運業", "16": "觀光餐旅", "17": "金融保險", "18": "貿易百貨",\n    "19": "綜合", "20": "其他", "21": "化學工業", "22": "生技醫療",\n    "23": "油電燃氣", "24": "半導體業", "25": "電腦及週邊設備業", "26": "光電業",\n    "27": "通信網路業", "28": "電子零組件業", "29": "電子通路業", "30": "資訊服務業",\n    "31": "其他電子業", "32": "文化創意", "33": "農業科技", "34": "電子商務",\n    "35": "綠能環保", "36": "數位雲端", "37": "運動休閒", "38": "居家生活",\n}\n\nGROUPS = {\n    # PCB 先細分，避免全部塞進電子零組件。\n    "PCB／多層板": {"3044", "2313", "2368", "6191", "5469", "2355", "4927", "8155", "3715"},\n    "CCL／銅箔": {"2383", "6274", "6213", "8358"},\n    "ABF載板": {"3037", "8046", "3189"},\n    "PCB設備／耗材": {"8021", "6664", "1595"},\n\n    # AI server / high speed / thermal.\n    "AI伺服器ODM": {"6669", "2382", "3231", "2317"},\n    "伺服器電源": {"2308", "6412", "6282", "6409"},\n    "BBU／電池備援": {"6781", "6121", "3323"},\n    "散熱": {"3017", "3324", "8996", "3653"},\n    "高速連接／線材": {"6197", "3665", "3533", "3023"},\n    "CPO／光通訊": {"6442", "3363", "3081", "4979", "3163", "4908"},\n\n    # Semiconductor.\n    "晶圓代工": {"2330", "2303", "5347", "6770"},\n    "IC封裝測試": {"3711", "2441", "6239", "6147", "8150", "6257", "8131", "3372"},\n    "ASIC／IC設計服務": {"3035", "3443", "3661"},\n    "IC設計": {"2454", "2379", "3034", "8016", "4966", "3227", "6415"},\n    "網通IC": {"8040", "2379"},\n    "記憶體／儲存IC": {"2408", "2344", "2337", "3006", "5351", "8299"},\n    "功率半導體": {"3707", "3105", "8086", "3016"},\n    "矽晶圓": {"5483", "6182", "6488", "3532"},\n    "半導體測試介面": {"6223", "6510", "6683", "6515"},\n    "半導體設備": {"3131", "3583", "2467", "6532", "6187", "6640", "5443"},\n}\n\nCODE_TO_GROUP = {}\nfor group, codes in GROUPS.items():\n    for code in codes:\n        CODE_TO_GROUP.setdefault(code, group)\n\ndef industry_name_for(industry):\n    key = str(industry or "").strip()\n    return INDUSTRY_NAMES.get(key, key if key and key != "nan" else "未分類")\n\ndef sector_group_for(code, name=None, industry=None):\n    return CODE_TO_GROUP.get(str(code or "").strip())\n'''
write("scripts/sector_groups.py", sector)


# ---------------------------------------------------------------------------
# index.html
# ---------------------------------------------------------------------------
p = "docs/index.html"
s = read(p)
s = s.replace("Free Edition v1.3.7｜交易日一致性＋櫃買官方指數", "Free Edition v1.4.0｜官方即時價＋獨立大盤＋多因子族群", 1)
s = s.replace(".parts{display:grid;grid-template-columns:repeat(4,1fr);", ".parts{display:grid;grid-template-columns:repeat(3,1fr);", 1)
s = s.replace(".g{display:flex;justify-content:space-between;background:#10151d;padding:8px;border-radius:9px;font-size:12px}", ".g{display:flex;justify-content:space-between;background:#10151d;padding:8px;border-radius:9px;font-size:12px}.peerlink{width:100%;border:0;color:inherit;text-align:left;cursor:pointer}.peerlink:active{transform:scale(.995)}", 1)

old = '''function groupHTML(r){\n const key=(r.sector_group||\"\").trim();\n if(!key)return \"\";\n let same=rows.filter(x=>x.sector_group===key&&x.technical_score>=30&&!(x.overheat_reasons||[]).length).slice(0,8);\n if(same.length<2)return \"\";\n return `<details><summary>👥 ${key} 共振 ${r.sector_hot_count||same.length} 檔｜點我展開</summary><div class=\"group\">${same.map(x=>`<div class=\"g\"><span>${x.code} ${x.name}</span><span>${x.score_reliable===false?\"—\":num(x.score,0)}｜${x.category}</span></div>`).join(\"\")}</div></details>`;\n}\n'''
new = '''function groupHTML(r){\n const key=(r.sector_group||\"\").trim();\n if(!key)return \"\";\n const d=r.sector_detail||{};\n const peers=(r.sector_peers&&r.sector_peers.length?r.sector_peers:rows.filter(x=>x.sector_group===key).slice(0,10));\n const comp=d.components||{};\n const detail=`廣度 ${num(comp.breadth,1)}/3 · 強度 ${num(comp.strength,1)}/2 · 量能 ${num(comp.volume,1)}/2 · 領頭 ${num(comp.leaders,1)}/2 · 延續 ${num(comp.continuity,1)}/1`;\n return `<details><summary>👥 ${key} 共振 ${num(r.sector_score,1)}/10｜${d.strong_count||0}/${d.count||peers.length} 檔轉強｜點我展開</summary><div class=\"helptext\" style=\"margin:7px 2px\">${detail}</div><div class=\"group\">${peers.map(x=>`<button class=\"g peerlink\" data-code=\"${x.code}\"><span>${x.code} ${x.name}<small> ${signed(x.day_change,1)}</small></span><span>${x.score===null||x.score===undefined?\"—\":num(x.score,0)}｜${x.category||\"觀察\"}</span></button>`).join(\"\")}</div></details>`;\n}\n'''
s = replace_once(s, old, new, "groupHTML")

old = '''function partsHTML(r){\n return `<div class=\"parts\">\n <div class=\"part\"><div class=\"partv\">${num(r.technical_score,0)}/50</div><div class=\"partl\">技術</div></div>\n <div class=\"part\"><div class=\"partv\">${(+r.chip_coverage_pct||0)<60?\"待補\":num(r.chip_score,0)+\"/25\"}</div><div class=\"partl\">籌碼${(+r.chip_coverage_pct||0)<60?\" · 資料不足\":\"\"}</div></div>\n <div class=\"part\"><div class=\"partv\">${num(r.sector_score,0)}/10</div><div class=\"partl\">族群</div></div>\n <div class=\"part\"><div class=\"partv\">${r.market_data_complete===false?\"待補\":num(r.market_score,0)+\"/15\"}</div><div class=\"partl\">大盤${r.market_data_complete===false?\" · 日期未齊\":\"\"}</div></div>\n </div>`;\n}\n'''
new = '''function partsHTML(r){\n return `<div class=\"parts\">\n <div class=\"part\"><div class=\"partv\">${num(r.technical_score,0)}/50</div><div class=\"partl\">技術</div></div>\n <div class=\"part\"><div class=\"partv\">${(+r.chip_coverage_pct||0)<60?\"待補\":num(r.chip_score,0)+\"/25\"}</div><div class=\"partl\">籌碼${(+r.chip_coverage_pct||0)<60?\" · 資料不足\":\"\"}</div></div>\n <div class=\"part\"><div class=\"partv\">${num(r.sector_score,1)}/10</div><div class=\"partl\">族群</div></div>\n </div>`;\n}\n'''
s = replace_once(s, old, new, "partsHTML")

# Show quote vs structure time directly in intraday metrics.
old = 'if(mode==="intraday")return [["現價",num(r.close,2)],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["當日",signed(r.day_change,1)],["VWAP",num(r.vwap,2)],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["族群共振",(r.sector_score_label?((r.sector_hot_count||0)+"檔 · "+r.sector_score_label+(r.sector_score_source==="官方產業代理"?"（產業代理）":"")):"待分類")]];'
new = 'if(mode==="intraday")return [["現價",num(r.close,2)],["行情時間",r.quote_time||r.time||"—"],["5分K結構",r.structure_time||r.time||"—"],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["當日",signed(r.day_change,1)],["VWAP",num(r.vwap,2)],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["族群共振",(r.sector_score_label?(num(r.sector_score,1)+"/10 · "+r.sector_score_label+(r.sector_score_source==="官方產業代理"?"（產業代理）":"")):"待分類")]];'
s = replace_once(s, old, new, "intraday metrics")

# Card data-code lets realtime overlay update the visible price cell reliably.
s = s.replace('rr.slice(0,70).map(r=>`<div class="card">', 'rr.slice(0,70).map(r=>`<div class="card" data-code="${r.code}">', 1)

# Help copy + footer.
s = s.replace('<b>族群 10：</b>優先看較窄的次產業/題材共振：4檔以上=10、3檔=8、2檔=5、1檔=2。沒有窄群組時改用官方產業廣度作代理，最高6分，並明確標示「產業代理」，不再因為資料尚未分類就直接判0分。', '<b>族群 10：</b>改用多因子共振：廣度3＋強度2＋量能2＋領頭股2＋延續性1。強勢股成交金額占比也納入強度，避免冷門小股一起紅就拿高分；點開族群即可點選共振個股。', 1)
s = s.replace('<b>大盤 15：</b>盤中＝', '<b>個股品質：</b>技術50＋籌碼25＋族群10＝85分，再換算為100分；大盤不再灌進每一檔個股分數。<br><b>大盤 15（獨立）：</b>只判斷今天的操作環境。盤中＝', 1)
s = s.replace('階段看價格行為｜品質分 = 技術50 + 籌碼25 + 族群10 + 大盤15 ± 流動性修正', '階段看價格行為｜個股品質 = 技術50＋籌碼25＋族群10（85換算100）｜大盤15分獨立判斷操作環境', 1)

# Click a resonance peer -> show that stock immediately.
insert = '''\n$("cards").addEventListener("click",e=>{\n const b=e.target.closest(".peerlink");if(!b)return;\n const code=b.dataset.code;if(!code)return;\n $("q").value=code;filter="all";watchOnly=false;\n document.querySelectorAll(".filter").forEach(x=>x.classList.toggle("on",x.dataset.f==="all"));\n render();\n setTimeout(()=>document.querySelector(".card")?.scrollIntoView({behavior:"smooth",block:"start"}),30);\n});\n'''
load_marker = 'if("serviceWorker" in navigator)navigator.serviceWorker.register("./sw.js").catch(()=>{});\nload();'
if insert.strip() not in s:
    s = replace_once(s, load_marker, insert + load_marker, "peer click handler")
write(p, s)


# ---------------------------------------------------------------------------
# realtime.js: 10-second official-quote overlay, batched 5 codes, up to 15.
# ---------------------------------------------------------------------------
realtime = r'''(()=>{
  const REFRESH_MS = 10000;
  const MAX_CODES = 15;
  const BATCH_SIZE = 5;
  const FRESHNESS_MS = 30000;
  const quotes = new Map();
  let lastSuccessAt = 0;
  let latestQuoteLabel = '';
  let busy = false;

  function apiUrl(){
    const configured=String(window.DOGSON_REALTIME_API||'').trim();
    if(configured) return configured.replace(/\/$/,'') + '/api/quote';
    return 'https://dogson-stock-radar-live.vercel.app/api/quote';
  }
  function codeFromCard(card){
    const dc=String(card?.dataset?.code||'');if(/^\d{4}$/.test(dc))return dc;
    const t=card?.querySelector('.code')?.textContent||'';const m=t.match(/\b\d{4}\b/);return m?m[0]:null;
  }
  function selectedCodes(){
    const out=[];const add=c=>{c=String(c||'').trim();if(/^\d{4}$/.test(c)&&!out.includes(c)&&out.length<MAX_CODES)out.push(c)};
    const q=document.getElementById('q')?.value.trim()||'';
    if(/^\d{4}$/.test(q))add(q);
    try{if(q&&!/^\d{4}$/.test(q)){const hit=(typeof universe!=='undefined'?universe:[]).find(x=>String(x.name)===q);if(hit)add(hit.code)}}catch{}
    try{(typeof watchlist==='function'?watchlist():[]).forEach(add)}catch{}
    document.querySelectorAll('.card').forEach(card=>add(codeFromCard(card)));
    return out;
  }
  function n(v){const x=Number(v);return Number.isFinite(x)?x:null}
  function fmtPrice(v){if(v==null)return'—';return v>=1000?v.toFixed(0):v>=100?v.toFixed(1):v.toFixed(2)}
  function fmtPct(v){if(v==null)return'—';return `${v>=0?'+':''}${v.toFixed(2)}%`}
  function toDate(v){const x=n(v);if(!x)return null;let ms=x;if(ms>1e14)ms/=1000;else if(ms<1e12)ms*=1000;const d=new Date(ms);return Number.isNaN(d.getTime())?null:d}
  function fmtTime(v){const d=toDate(v);return d?d.toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}):'—'}
  function status(text,cls=''){const el=document.getElementById('liveStatus');if(!el)return;el.className=`live-status ${cls}`;el.textContent=text}
  function setRadarPill(text,level='ok'){
    const el=document.getElementById('status');if(!el)return;el.textContent=text;
    if(level==='bad'){el.style.background='#2c141a';el.style.borderColor='#61303a';el.style.color='#ff9cac'}
    else if(level==='warn'){el.style.background='#2a230f';el.style.borderColor='#66521f';el.style.color='#ffd477'}
    else{el.style.background='#16263a';el.style.borderColor='#24496e';el.style.color='#9fd0ff'}
  }
  function taipeiClock(){
    const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date());
    const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));return {year:+p.year,month:+p.month,day:+p.day,hour:+p.hour,minute:+p.minute};
  }
  function structureLatest(){
    const rs=typeof intraRows!=='undefined'&&Array.isArray(intraRows)?intraRows:[];let latest='';
    for(const r of rs){const t=String(r.structure_time||r.time||'').slice(0,5);if(/^\d{2}:\d{2}$/.test(t)&&t>latest)latest=t}return latest;
  }
  function checkRadarFreshness(){
    try{
      if(typeof mode!=='undefined'&&mode==='close'){setRadarPill('盤後資料','ok');return}
      const st=structureLatest();
      if(lastSuccessAt&&Date.now()-lastSuccessAt<45000){
        setRadarPill(`即時價 ${latestQuoteLabel||'已連線'}｜5分K結構 ${st||'—'}`,'ok');return;
      }
      const now=taipeiClock();const nowMin=now.hour*60+now.minute;
      let latest=-1;for(const r of (typeof intraRows!=='undefined'?intraRows:[])){const m=String(r.structure_time||r.time||'').match(/^(\d{1,2}):(\d{2})/);if(m)latest=Math.max(latest,(+m[1])*60+(+m[2]))}
      if(latest<0){setRadarPill('行情連線中','warn');return}
      const age=nowMin-latest;const label=`${String(Math.floor(latest/60)).padStart(2,'0')}:${String(latest%60).padStart(2,'0')}`;
      if(age>30)setRadarPill(`⚠️ 即時價未連線｜5分K結構 ${label}`,'bad');else setRadarPill(`5分K結構 ${label}｜即時價連線中`,'warn');
    }catch{}
  }
  function ensureStyles(){
    if(document.getElementById('liveQuoteStyles'))return;const s=document.createElement('style');s.id='liveQuoteStyles';s.textContent=`
    .live-status{margin:8px 2px 2px;padding:9px 11px;border:1px solid #285b48;border-radius:12px;background:#10241d;color:#8cf0bd;font-size:12px;font-weight:800}
    .live-status.warn{border-color:#66521f;background:#2a230f;color:#ffd477}.live-status.bad{border-color:#61303a;background:#2c141a;color:#ff9cac}
    .livequote{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:10px}.livecell{background:#0c1612;border:1px solid #244936;border-radius:11px;padding:9px}
    .liveval{font-size:15px;font-weight:900;color:#8cf0bd}.livelab{font-size:9px;color:#9ba5b6;margin-top:3px}`;document.head.appendChild(s);
  }
  function updateMainMetrics(card,q){
    card.querySelectorAll('.metric').forEach(cell=>{const lab=cell.querySelector('.mlab')?.textContent?.trim();const val=cell.querySelector('.mval');if(!val)return;
      if(lab==='現價')val.textContent=fmtPrice(q.price);else if(lab==='當日'&&q.change!=null)val.textContent=fmtPct(q.change);else if(lab==='行情時間')val.textContent=fmtTime(q.time).slice(0,5);
    });
  }
  function applyQuotes(){
    ensureStyles();const liveEl=document.getElementById('liveStatus');
    if(typeof mode!=='undefined'&&mode!=='intraday'){if(liveEl)liveEl.style.display='none';document.querySelectorAll('.livequote').forEach(x=>x.remove());return}
    if(liveEl)liveEl.style.display='block';
    document.querySelectorAll('.card').forEach(card=>{const code=codeFromCard(card);if(!code)return;const q=quotes.get(code);let box=card.querySelector('.livequote');
      if(!box){box=document.createElement('div');box.className='livequote';const top=card.querySelector('.top');if(top)top.insertAdjacentElement('afterend',box);else card.prepend(box)}
      if(!q){box.innerHTML='<div class="livecell"><div class="liveval">—</div><div class="livelab">官方即時價</div></div><div class="livecell"><div class="liveval">—</div><div class="livelab">即時漲跌</div></div><div class="livecell"><div class="liveval">5分K</div><div class="livelab">等待進入即時池</div></div>';return}
      box.innerHTML=`<div class="livecell"><div class="liveval">${fmtPrice(q.price)}</div><div class="livelab">官方即時價</div></div><div class="livecell"><div class="liveval">${fmtPct(q.change)}</div><div class="livelab">即時漲跌</div></div><div class="livecell"><div class="liveval">${fmtTime(q.time)}</div><div class="livelab">TWSE MIS｜結構仍採5分K</div></div>`;
      updateMainMetrics(card,q);
    });
  }
  async function fetchBatch(endpoint,codes){
    const url=`${endpoint}?codes=${encodeURIComponent(codes.join(','))}&_=${Date.now()}`;const r=await fetch(url,{cache:'no-store',credentials:'omit'});const j=await r.json();if(!r.ok||!j?.ok)throw new Error(j?.error||`HTTP ${r.status}`);return j.quotes||[];
  }
  async function refresh(){
    if(busy||document.hidden)return;if(typeof mode!=='undefined'&&mode!=='intraday'){applyQuotes();return}
    const codes=selectedCodes();if(!codes.length){status('🟡 尚無即時追蹤標的｜搜尋或加入關注後會優先追蹤','warn');return}
    busy=true;try{
      const endpoint=apiUrl(),batches=[];for(let i=0;i<codes.length;i+=BATCH_SIZE)batches.push(codes.slice(i,i+BATCH_SIZE));
      const results=await Promise.allSettled(batches.map(b=>fetchBatch(endpoint,b)));let count=0,newest=null;
      for(const rr of results){if(rr.status!=='fulfilled')continue;for(const x of rr.value){const code=String(x.code||''),price=n(x.price);if(!/^\d{4}$/.test(code)||price==null)continue;quotes.set(code,{price,change:n(x.changePct),time:x.time,receivedAt:Date.now()});count++;const d=toDate(x.time);if(d&&(!newest||d>newest))newest=d}}
      if(!count)throw new Error('no quotes');lastSuccessAt=Date.now();latestQuoteLabel=(newest||new Date()).toLocaleTimeString('zh-TW',{hour:'2-digit',minute:'2-digit',hour12:false});
      status(`🟢 官方近即時 ${latestQuoteLabel}｜更新 ${count}/${codes.length} 檔｜每10秒｜5分K結構分開顯示`);applyQuotes();checkRadarFreshness();
    }catch(e){const age=lastSuccessAt?Math.round((Date.now()-lastSuccessAt)/1000):null;status(age!=null?`⚠️ 官方即時行情暫斷｜上次成功 ${age} 秒前｜5分K雷達仍可用`:'⚠️ 官方即時行情連線中｜5分K雷達仍可用','bad');applyQuotes();checkRadarFreshness()}finally{busy=false}
  }
  function boot(){ensureStyles();applyQuotes();refresh();setTimeout(checkRadarFreshness,1000);setInterval(refresh,REFRESH_MS);setInterval(checkRadarFreshness,FRESHNESS_MS);
    const cards=document.getElementById('cards');if(cards){let t;new MutationObserver(()=>{clearTimeout(t);t=setTimeout(()=>{applyQuotes();refresh()},250)}).observe(cards,{childList:true,subtree:true})}
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});document.getElementById('q')?.addEventListener('change',refresh);document.getElementById('scan')?.addEventListener('click',()=>setTimeout(refresh,150));document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>setTimeout(()=>{applyQuotes();refresh();checkRadarFreshness()},50)));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
'''
write("docs/realtime.js", realtime)

# Service worker gets a new cache namespace. Static files remain network-first.
sw = read("docs/sw.js")
sw = sw.replace("dogson-free-v136", "dogson-free-v140")
sw = sw.replace("realtime-config.js?v=136", "realtime-config.js?v=140")
sw = sw.replace("realtime.js?v=136", "realtime.js?v=140")
write("docs/sw.js", sw)

# The HTML still uses network-first SW, but bump its explicit asset query too.
idx = read("docs/index.html")
idx = idx.replace('realtime-config.js?v=136', 'realtime-config.js?v=140')
idx = idx.replace('realtime.js?v=136', 'realtime.js?v=140')
write("docs/index.html", idx)

print("v1.4.0 patch complete")
