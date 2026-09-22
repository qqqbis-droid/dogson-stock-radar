#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_data.py"
HTML = ROOT / "docs" / "index.html"


def replace_once(text, old, new, label):
    if old not in text:
        if new in text:
            print(label, "already applied")
            return text
        raise SystemExit(f"patch marker missing: {label}")
    return text.replace(old, new, 1)


b = BUILD.read_text(encoding="utf-8")
b = b.replace("犬子老師飆股雷達 Free Edition v1.3\n", "犬子老師飆股雷達 Free Edition v1.3.1\n", 1)
b = replace_once(
    b,
    "from chip_data import build_chip_signals\n",
    "from chip_data import build_chip_signals\nfrom sector_groups import industry_name_for, sector_group_for\n",
    "sector imports",
)

mis_code = r'''

def official_mis_snapshot(uni):
    """盤後用 TWSE MIS 覆核今日最終 OHLCV，避免 Yahoo 日K仍停在盤中快照。"""
    now = now_tw()
    if (now.hour, now.minute) < (13, 30):
        return {}
    out = {}
    recs = uni[["code", "market"]].astype(str).to_dict("records")
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
                headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.1", "Referer": "https://mis.twse.com.tw/stock/index.jsp"},
                timeout=20,
            )
            rr.raise_for_status()
            arr = rr.json().get("msgArray") or []
            for x in arr:
                code = str(x.get("c") or "").strip()
                d = str(x.get("d") or "").strip()
                if not code or (d and d != now.strftime("%Y%m%d")):
                    continue
                def f(k):
                    try:
                        v = str(x.get(k) or "").replace(",", "").strip()
                        return float(v) if v not in {"", "-", "--"} else None
                    except Exception:
                        return None
                z, o, h, l, v = f("z"), f("o"), f("h"), f("l"), f("v")
                if z is None or z <= 0:
                    continue
                out[code] = {
                    "date": now.date(), "Close": z,
                    "Open": o if o and o > 0 else z,
                    "High": h if h and h > 0 else z,
                    "Low": l if l and l > 0 else z,
                    # MIS v 為張數；Yahoo 日K Volume 為股數。
                    "Volume": (v * 1000.0) if v is not None else None,
                }
        except Exception as e:
            print("MIS close batch", i, e)
    print("official MIS close snapshot", len(out))
    return out


def overlay_official_today_bar(x, snap):
    if x is None or x.empty or not snap:
        return x
    y = x.copy()
    target = snap["date"]
    idx_dates = [pd.Timestamp(v).date() for v in y.index]
    vals = {k: snap.get(k) for k in ["Open", "High", "Low", "Close", "Volume"]}
    if target in idx_dates:
        pos = max(i for i, d in enumerate(idx_dates) if d == target)
        idx = y.index[pos]
        for k, v in vals.items():
            if v is not None:
                y.loc[idx, k] = v
    else:
        row = {k: (v if v is not None else np.nan) for k, v in vals.items()}
        y.loc[pd.Timestamp(target)] = row
        y = y.sort_index()
    return y

'''
if "def official_mis_snapshot(" not in b:
    b = b.replace("\ndef rsi(s, n=14):\n", mis_code + "\ndef rsi(s, n=14):\n", 1)

b = replace_once(
    b,
    'def build_close():\n    uni = get_universe()\n    universe_public = uni[["code", "name", "industry", "market"]].astype(str).to_dict("records")\n    dump("universe.json", universe_public)\n    meta = uni.set_index("symbol").to_dict("index")\n',
    'def build_close():\n    uni = get_universe()\n    uni["industry_name"] = uni["industry"].map(industry_name_for)\n    uni["sector_group"] = [sector_group_for(c, n, i) or "" for c, n, i in zip(uni["code"], uni["name"], uni["industry"])]\n    universe_public = uni[["code", "name", "industry", "industry_name", "sector_group", "market"]].astype(str).to_dict("records")\n    dump("universe.json", universe_public)\n    meta = uni.set_index("symbol").to_dict("index")\n    official_today = official_mis_snapshot(uni)\n',
    "enrich universe + MIS snapshot",
)

b = replace_once(
    b,
    '        for sym, x in data.items():\n            try:\n                t = close_technical(x)\n                if not t:\n                    continue\n',
    '        for sym, x in data.items():\n            try:\n                m = meta.get(sym, {})\n                code = str(m.get("code", sym.split(".")[0]))\n                x = overlay_official_today_bar(x, official_today.get(code))\n                t = close_technical(x)\n                if not t:\n                    continue\n',
    "overlay official daily bar",
)

b = replace_once(
    b,
    '                m = meta.get(sym, {})\n                rows.append({\n                    "symbol": sym,\n                    "code": str(m.get("code", sym.split(".")[0])),\n                    "name": str(m.get("name", sym)),\n                    "industry": str(m.get("industry", "未分類")),\n                    "market": str(m.get("market", "")),\n',
    '                rows.append({\n                    "symbol": sym,\n                    "code": code,\n                    "name": str(m.get("name", sym)),\n                    "industry": str(m.get("industry", "未分類")),\n                    "industry_name": str(m.get("industry_name", industry_name_for(m.get("industry")))),\n                    "sector_group": str(m.get("sector_group") or ""),\n                    "market": str(m.get("market", "")),\n',
    "close row sector fields",
)

old_hot = '''    hot = {}\n    for r in rows:\n        if r.get("technical_score", 0) >= 30 and not r.get("overheat_reasons"):\n            hot[r["industry"]] = hot.get(r["industry"], 0) + 1\n'''
new_hot = '''    # 族群共振改用嚴格次產業/題材群組，不再拿整個「半導體業」當同族群。\n    hot = {}\n    for r in rows:\n        key = str(r.get("sector_group") or "").strip()\n        if key and r.get("technical_score", 0) >= 30 and not r.get("overheat_reasons"):\n            hot[key] = hot.get(key, 0) + 1\n'''
b = replace_once(b, old_hot, new_hot, "strict sector hot count")

old_n = '''    for r in rows:\n        n = int(hot.get(r["industry"], 0))\n        sec = sector_score(n)\n        r["industry_hot_count"] = n\n        r["sector_score"] = sec\n'''
new_n = '''    for r in rows:\n        key = str(r.get("sector_group") or "").strip()\n        n = int(hot.get(key, 0)) if key else 0\n        sec = sector_score(n)\n        r["industry_hot_count"] = n\n        r["sector_hot_count"] = n\n        r["sector_score"] = sec\n'''
b = replace_once(b, old_n, new_n, "strict sector scoring")

old_quality = '''        if r["score"] >= 80:\n            r["quality_label"] = "高共振"\n        elif r["score"] >= 70:\n            r["quality_label"] = "強"\n        else:\n            r["quality_label"] = "一般"\n        r["quality_reference"] = quality_reference\n        r["quality_pass_market"] = bool(r["score"] >= quality_reference)\n'''
new_quality = '''        chip_cov = float(r.get("chip_coverage_pct") or 0)\n        r["score_reliable"] = bool(chip_cov >= 60)\n        if not r["score_reliable"]:\n            r["quality_label"] = "資料待補"\n        elif r["score"] >= 80:\n            r["quality_label"] = "高共振"\n        elif r["score"] >= 70:\n            r["quality_label"] = "強"\n        else:\n            r["quality_label"] = "一般"\n        r["quality_reference"] = quality_reference\n        r["quality_pass_market"] = bool(r["score_reliable"] and r["score"] >= quality_reference)\n'''
b = replace_once(b, old_quality, new_quality, "quality reliability")

old_intraday_fields = '''                    "name": str(m.get("name", sym)),\n                    "industry": str(m.get("industry", "未分類")),\n                    "market": str(m.get("market", "")),\n'''
new_intraday_fields = '''                    "name": str(m.get("name", sym)),\n                    "industry": str(m.get("industry", "未分類")),\n                    "industry_name": str(m.get("industry_name", industry_name_for(m.get("industry")))),\n                    "sector_group": str(m.get("sector_group") or sector_group_for(code, m.get("name"), m.get("industry")) or ""),\n                    "market": str(m.get("market", "")),\n'''
# Only the remaining occurrence belongs to intraday after close occurrence was patched.
b = replace_once(b, old_intraday_fields, new_intraday_fields, "intraday row sector fields")

b = b.replace('"version": "1.3-free"', '"version": "1.3.1-free"')
BUILD.write_text(b, encoding="utf-8")

h = HTML.read_text(encoding="utf-8")
h = h.replace("Free Edition v1.3｜近即時報價＋5分K結構", "Free Edition v1.3.1｜收盤覆核＋嚴格族群修正版", 1)

h = replace_once(
    h,
    '''function groupHTML(r){\n let same=rows.filter(x=>x.industry===r.industry).slice(0,8);\n if(same.length<2)return "";\n return `<details><summary>👥 族群共振 ${r.industry_hot_count||same.length} 檔｜點我展開</summary><div class="group">${same.map(x=>`<div class="g"><span>${x.code} ${x.name}</span><span>${num(x.score,0)}｜${x.category}</span></div>`).join("")}</div></details>`;\n}\n''',
    '''function groupHTML(r){\n const key=(r.sector_group||"").trim();\n if(!key)return "";\n let same=rows.filter(x=>x.sector_group===key&&x.technical_score>=30&&!(x.overheat_reasons||[]).length).slice(0,8);\n if(same.length<2)return "";\n return `<details><summary>👥 ${key} 共振 ${r.sector_hot_count||same.length} 檔｜點我展開</summary><div class="group">${same.map(x=>`<div class="g"><span>${x.code} ${x.name}</span><span>${x.score_reliable===false?"—":num(x.score,0)}｜${x.category}</span></div>`).join("")}</div></details>`;\n}\n''',
    "UI strict sector group",
)

h = replace_once(
    h,
    ''' <div class="part"><div class="partv">${num(r.chip_score,0)}/25</div><div class="partl">籌碼</div></div>''',
    ''' <div class="part"><div class="partv">${(+r.chip_coverage_pct||0)<60?"待補":num(r.chip_score,1)+"/25"}</div><div class="partl">籌碼${(+r.chip_coverage_pct||0)<60?" · 資料不足":""}</div></div>''',
    "UI chip coverage",
)

h = h.replace('["族群共振",(r.industry_hot_count||0)+"檔"]', '["族群共振",r.sector_group?((r.sector_hot_count||0)+"檔 · "+r.sector_group):"未分類"]')
h = h.replace('${r.industry||"未分類"} · ${mode==="intraday"?(r.time||""):(r.date||"")}', '${r.industry_name||r.industry||"未分類"}${r.sector_group?" · "+r.sector_group:""} · ${mode==="intraday"?(r.time||""):(r.date||"")}')
h = h.replace('<div class="score">${num(r.score,0)}</div><div class="label">品質總分 /100</div>', '<div class="score">${r.score_reliable===false?"—":num(r.score,0)}</div><div class="label">${r.score_reliable===false?"籌碼覆蓋不足":"品質總分 /100"}</div>')
h = h.replace('${x.name}<small>${x.code} · ${x.industry}</small>', '${x.name}<small>${x.code} · ${x.industry_name||x.industry}</small>')
h = h.replace('<b>族群 10：</b>同產業至少 2～4 檔一起轉強才加分。', '<b>族群 10：</b>改用較窄的次產業/題材群組；沒有明確分類就不給族群分，避免把整個半導體業混成同一群。')
h = h.replace('<b>籌碼 25：</b>外資連3買、借券賣出連3減、投信、融資。資料缺漏時用中性分，不會亂扣分。', '<b>籌碼 25：</b>外資連3買、借券賣出連3減、投信、融資。覆蓋率低於60%時品質總分會標示「資料待補」，不再用假精準分數誤導。')
HTML.write_text(h, encoding="utf-8")

print("v1.3.1 accuracy patch applied")
