#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"patch target not found: {label}")
    return text.replace(old, new, 1)


# ---------- build_data.py ----------
p = ROOT / "scripts" / "build_data.py"
s = p.read_text(encoding="utf-8")

s = replace_once(
    s,
    "from chip_data import build_chip_signals\n",
    "from chip_data import build_chip_signals\nfrom sector_groups import industry_name_for, sector_group_for\n",
    "sector import",
)

marker = '''def download_intraday(syms):
    raw = yf.download(
        syms, period="5d", interval="5m", group_by="ticker",
        auto_adjust=False, threads=True, progress=False, prepost=False
    )
    return split_bulk(raw, syms)
'''
insert = marker + r'''

MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"


def _mis_num(v):
    try:
        if v in (None, "", "-", "--"):
            return None
        return float(str(v).replace(",", ""))
    except Exception:
        return None


def official_close_snapshots(uni):
    """盤後用 TWSE MIS 最終快照校正 Yahoo 日K最後一根。

    Yahoo 免費日K在台股收盤後偶爾仍殘留盤中快照；MIS 的 z/o/h/l/v/d 可用來
    校正當日 OHLCV。只在台灣時間 13:35 後啟用，避免盤中把未完成日K當收盤。
    """
    now = now_tw()
    if now.weekday() >= 5 or (now.hour, now.minute) < (13, 35):
        return {}
    today = now.strftime("%Y%m%d")
    out = {}
    records = uni[["code", "market"]].astype(str).to_dict("records")
    for i in range(0, len(records), 60):
        part = records[i:i+60]
        ex_ch = "|".join(
            f"{'otc' if r['market'] == '上櫃' else 'tse'}_{r['code']}.tw"
            for r in part
        )
        try:
            resp = requests.get(
                MIS_URL,
                params={"ex_ch": ex_ch, "json": "1", "delay": "0", "_": int(now.timestamp()*1000)},
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.1", "Referer": "https://mis.twse.com.tw/stock/index.jsp"},
            )
            resp.raise_for_status()
            obj = resp.json()
            for x in obj.get("msgArray") or []:
                code = str(x.get("c") or "").strip()
                if not code or str(x.get("d") or "") != today:
                    continue
                close = _mis_num(x.get("z"))
                if close is None or close <= 0:
                    continue
                vol_lots = _mis_num(x.get("v"))
                out[code] = {
                    "date": today,
                    "close": close,
                    "open": _mis_num(x.get("o")),
                    "high": _mis_num(x.get("h")),
                    "low": _mis_num(x.get("l")),
                    # MIS v 為累積成交張數；yfinance Volume 為股數。
                    "volume": (vol_lots * 1000) if vol_lots is not None else None,
                    "time": str(x.get("t") or ""),
                    "source": "TWSE MIS",
                }
        except Exception as e:
            print("MIS close batch", i, e)
    print("official close snapshots", len(out))
    return out


def apply_official_close(x, snap):
    if x is None or x.empty or not snap:
        return x
    x = x.copy()
    d = now_tw().date()
    vals = {
        "Open": snap.get("open"), "High": snap.get("high"), "Low": snap.get("low"),
        "Close": snap.get("close"), "Volume": snap.get("volume"),
    }
    if x.index[-1].date() == d:
        idx = x.index[-1]
        for k, v in vals.items():
            if v is not None:
                x.loc[idx, k] = v
    elif x.index[-1].date() < d and vals.get("Close") is not None:
        # Yahoo 尚未建立今日 daily bar 時，直接補上官方盤後快照。
        prev = float(x["Close"].iloc[-1])
        row = {
            "Open": vals.get("Open") or vals["Close"],
            "High": vals.get("High") or vals["Close"],
            "Low": vals.get("Low") or vals["Close"],
            "Close": vals["Close"],
            "Volume": vals.get("Volume") or 0,
        }
        x.loc[pd.Timestamp(d)] = row
    return x.sort_index()
'''
s = replace_once(s, marker, insert, "MIS close helper")

s = replace_once(
    s,
    '    universe_public = uni[["code", "name", "industry", "market"]].astype(str).to_dict("records")\n    dump("universe.json", universe_public)\n',
    '''    universe_public = []
    for rec in uni[["code", "name", "industry", "market"]].astype(str).to_dict("records"):
        rec["industry_name"] = industry_name_for(rec.get("industry"))
        rec["sector_group"] = sector_group_for(rec.get("code"), rec.get("name"), rec.get("industry"))
        universe_public.append(rec)
    dump("universe.json", universe_public)
''',
    "enriched universe",
)

s = replace_once(
    s,
    '    syms = uni["symbol"].tolist()\n\n    for i in range(0, len(syms), 100):\n',
    '    syms = uni["symbol"].tolist()\n    official_close = official_close_snapshots(uni)\n\n    for i in range(0, len(syms), 100):\n',
    "official snapshot bootstrap",
)

s = replace_once(
    s,
    '''        for sym, x in data.items():
            try:
                t = close_technical(x)
''',
    '''        for sym, x in data.items():
            try:
                code0 = str(meta.get(sym, {}).get("code", sym.split(".")[0]))
                if code0 in official_close:
                    x = apply_official_close(x, official_close[code0])
                t = close_technical(x)
''',
    "apply official close",
)

s = replace_once(
    s,
    '''                m = meta.get(sym, {})
                rows.append({
                    "symbol": sym,
                    "code": str(m.get("code", sym.split(".")[0])),
                    "name": str(m.get("name", sym)),
                    "industry": str(m.get("industry", "未分類")),
                    "market": str(m.get("market", "")),
                    **t,
                })
''',
    '''                m = meta.get(sym, {})
                code = str(m.get("code", sym.split(".")[0]))
                name = str(m.get("name", sym))
                industry = str(m.get("industry", "未分類"))
                rows.append({
                    "symbol": sym,
                    "code": code,
                    "name": name,
                    "industry": industry,
                    "industry_name": industry_name_for(industry),
                    "sector_group": sector_group_for(code, name, industry),
                    "market": str(m.get("market", "")),
                    "close_source": "TWSE MIS" if code in official_close else "Yahoo daily",
                    **t,
                })
''',
    "close metadata",
)

s = replace_once(
    s,
    '''    hot = {}
    for r in rows:
        if r.get("technical_score", 0) >= 30 and not r.get("overheat_reasons"):
            hot[r["industry"]] = hot.get(r["industry"], 0) + 1
''',
    '''    hot = {}
    for r in rows:
        group = r.get("sector_group")
        if group and r.get("technical_score", 0) >= 30 and not r.get("overheat_reasons"):
            hot[group] = hot.get(group, 0) + 1
''',
    "strict hot groups",
)

s = replace_once(
    s,
    '''    for r in rows:
        n = int(hot.get(r["industry"], 0))
        sec = sector_score(n)
        r["industry_hot_count"] = n
        r["sector_score"] = sec
''',
    '''    for r in rows:
        group = r.get("sector_group")
        n = int(hot.get(group, 0)) if group else 0
        sec = sector_score(n) if group else 0
        r["industry_hot_count"] = n
        r["sector_score"] = sec
''',
    "strict sector score",
)

# 無籌碼資料不再虛構 12.5/25 中性證據；直接以 0 分且 coverage=0 呈現待補。
s = s.replace('''    else:
        score += 4

    # 借券賣出餘額 7''', '''    else:
        score += 0

    # 借券賣出餘額 7''', 1)
s = s.replace('''    else:
        score += 3.5

    # 投信 5''', '''    else:
        score += 0

    # 投信 5''', 1)
s = s.replace('''    else:
        score += 2.5

    # 融資 5''', '''    else:
        score += 0

    # 融資 5''', 1)
s = s.replace('''    else:
        score += 2.5

    return round(min(25, score), 1), round(coverage/25*100, 0)''', '''    else:
        score += 0

    return round(min(25, score), 1), round(coverage/25*100, 0)''', 1)

# intraday metadata: strict group + human-readable industry; remove duplicated liquidity keys.
s = replace_once(
    s,
    '''                rows.append({
                    "symbol": sym,
                    "code": code,
                    "name": str(m.get("name", sym)),
                    "industry": str(m.get("industry", "未分類")),
                    "market": str(m.get("market", "")),
                    **t,
''',
    '''                name = str(m.get("name", sym))
                industry = str(m.get("industry", "未分類"))
                rows.append({
                    "symbol": sym,
                    "code": code,
                    "name": name,
                    "industry": industry,
                    "industry_name": str(m.get("industry_name") or industry_name_for(industry)),
                    "sector_group": m.get("sector_group") or sector_group_for(code, name, industry),
                    "market": str(m.get("market", "")),
                    **t,
''',
    "intraday metadata",
)

dup = '''                    "avg_turnover20": prev.get("avg_turnover20"),
                    "avg_turnover20_mn": prev.get("avg_turnover20_mn"),
                    "liquidity_level": prev.get("liquidity_level", "未知"),
                    "liquidity_adjust": prev.get("liquidity_adjust", 0),
                    "avg_turnover20": prev.get("avg_turnover20"),
                    "avg_turnover20_mn": prev.get("avg_turnover20_mn"),
                    "liquidity_level": prev.get("liquidity_level", "未知"),
                    "liquidity_adjust": prev.get("liquidity_adjust", 0),
'''
one = '''                    "avg_turnover20": prev.get("avg_turnover20"),
                    "avg_turnover20_mn": prev.get("avg_turnover20_mn"),
                    "liquidity_level": prev.get("liquidity_level", "未知"),
                    "liquidity_adjust": prev.get("liquidity_adjust", 0),
'''
s = replace_once(s, dup, one, "duplicate liquidity keys")

# 修正盤中剛啟動理由：量速不是硬門檻，不再誤寫成必然量速放大。
s = s.replace('r["stage_reason"] = "3K突破＋站上VWAP＋量速放大"', 'r["stage_reason"] = "3K突破＋站上VWAP＋短線結構轉強"')

# bump backend version
s = s.replace('version": "1.3-free"', 'version": "1.3.1-free"')
p.write_text(s, encoding="utf-8")


# ---------- chip_data.py ----------
p = ROOT / "scripts" / "chip_data.py"
c = p.read_text(encoding="utf-8")
old = '''        obj = r.json()
        fields = obj.get("fields") or obj.get("field")
        data = obj.get("data")
        if fields and isinstance(data, list):
            return pd.DataFrame(data, columns=fields)
'''
new = '''        obj = r.json()
        candidates = []
        fields = obj.get("fields") or obj.get("field")
        data = obj.get("data")
        if fields and isinstance(data, list):
            candidates.append(pd.DataFrame(data, columns=fields))
        # MI_MARGN 等新版 TWSE 端點回傳 tables[]，不可只讀 root fields/data。
        for table in obj.get("tables") or []:
            if not isinstance(table, dict):
                continue
            f = table.get("fields") or table.get("field")
            d = table.get("data")
            if f and isinstance(d, list):
                try:
                    candidates.append(pd.DataFrame(d, columns=f))
                except Exception:
                    pass
        if candidates:
            def rank(df):
                cols = "|".join(map(str, df.columns))
                has_code = ("代號" in cols) or ("Code" in cols)
                return (1 if has_code else 0, len(df), len(df.columns))
            return max(candidates, key=rank)
'''
c = replace_once(c, old, new, "TWSE tables parser")
p.write_text(c, encoding="utf-8")


# ---------- docs/index.html ----------
p = ROOT / "docs" / "index.html"
h = p.read_text(encoding="utf-8")
h = h.replace('Free Edition v1.3｜近即時報價＋5分K結構', 'Free Edition v1.3.1｜收盤校正＋嚴格次產業共振')
h = h.replace('<b>族群 10：</b>同產業至少 2～4 檔一起轉強才加分。', '<b>族群 10：</b>改用較窄的次產業／題材群組，至少 2～4 檔一起轉強才加分；只同屬「半導體業」不再算共振。')
h = h.replace('<b>籌碼 25：</b>外資連3買、借券賣出連3減、投信、融資。資料缺漏時用中性分，不會亂扣分。', '<b>籌碼 25：</b>外資連3買、借券賣出連3減、投信、融資。資料缺漏時顯示待補，不再用中性分假裝有證據。')

old_group = '''function groupHTML(r){
 let same=rows.filter(x=>x.industry===r.industry).slice(0,8);
 if(same.length<2)return "";
 return `<details><summary>👥 族群共振 ${r.industry_hot_count||same.length} 檔｜點我展開</summary><div class="group">${same.map(x=>`<div class="g"><span>${x.code} ${x.name}</span><span>${num(x.score,0)}｜${x.category}</span></div>`).join("")}</div></details>`;
}
'''
new_group = '''function groupHTML(r){
 const group=r.sector_group;
 if(!group)return "";
 let same=rows.filter(x=>x.sector_group===group && (x.technical_score||0)>=30 && !(x.overheat_reasons||[]).length).slice(0,8);
 if(same.length<2)return "";
 return `<details><summary>👥 ${group} 共振 ${r.industry_hot_count||same.length} 檔｜點我展開</summary><div class="group">${same.map(x=>`<div class="g"><span>${x.code} ${x.name}</span><span>${num(x.score,0)}｜${x.category}</span></div>`).join("")}</div></details>`;
}
'''
h = replace_once(h, old_group, new_group, "UI strict group")

old_parts = '''function partsHTML(r){
 return `<div class="parts">
 <div class="part"><div class="partv">${num(r.technical_score,0)}/50</div><div class="partl">技術</div></div>
 <div class="part"><div class="partv">${num(r.chip_score,0)}/25</div><div class="partl">籌碼</div></div>
 <div class="part"><div class="partv">${num(r.sector_score,0)}/10</div><div class="partl">族群</div></div>
 <div class="part"><div class="partv">${num(r.market_score,0)}/15</div><div class="partl">大盤</div></div>
 </div>`;
}
'''
new_parts = '''function scorePart(v,maxv){
 if(v===null||v===undefined||Number.isNaN(+v))return `—/${maxv}`;
 const x=+v;return `${Number.isInteger(x)?x.toFixed(0):x.toFixed(1)}/${maxv}`;
}
function partsHTML(r){
 const chip=(+r.chip_coverage_pct||0)<=0?`—/25`:scorePart(r.chip_score,25);
 const sector=r.sector_group?scorePart(r.sector_score,10):`—/10`;
 return `<div class="parts">
 <div class="part"><div class="partv">${scorePart(r.technical_score,50)}</div><div class="partl">技術</div></div>
 <div class="part"><div class="partv">${chip}</div><div class="partl">籌碼</div></div>
 <div class="part"><div class="partv">${sector}</div><div class="partl">族群</div></div>
 <div class="part"><div class="partv">${scorePart(r.market_score,15)}</div><div class="partl">大盤</div></div>
 </div>`;
}
'''
h = replace_once(h, old_parts, new_parts, "score decimals and missing")

h = h.replace('${r.industry||"未分類"} · ${mode==="intraday"?(r.time||""):(r.date||"")}', '${r.sector_group||r.industry_name||r.industry||"未分類"} · ${mode==="intraday"?(r.time||""):(r.date||"")}')
h = h.replace('let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={};', 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeUpdatedAt=null,intraUpdatedAt=null;')

# Tab-specific timestamp rather than global status timestamp.
old_load = '''  closeRows=cj.rows||[];intraRows=ij.rows||[];
  $("updated").textContent=sj.updated_at?new Date(sj.updated_at).toLocaleString("zh-TW",{month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"}):"—";
  $("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();render();
'''
new_load = '''  closeRows=cj.rows||[];intraRows=ij.rows||[];
  closeUpdatedAt=cj.updated_at||sj.close_updated_at||null;intraUpdatedAt=ij.updated_at||sj.intraday_updated_at||null;
  updateDisplayedTime();
  $("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();render();
'''
h = replace_once(h, old_load, new_load, "tab-specific timestamp load")

old_tab = 'document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");mode=b.dataset.mode;$("modeText").textContent=mode==="intraday"?"盤中：5分K / VWAP / 同時間量速":"盤後：日K / 籌碼 / 大盤 / 支撐壓力";render()});'
new_tab = '''function updateDisplayedTime(){const t=mode==="intraday"?intraUpdatedAt:closeUpdatedAt;$("updated").textContent=t?new Date(t).toLocaleString("zh-TW",{month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"}):"—";}
document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");mode=b.dataset.mode;$("modeText").textContent=mode==="intraday"?"盤中：5分K / VWAP / 同時間量速":"盤後：日K / 籌碼 / 大盤 / 支撐壓力";updateDisplayedTime();render()});'''
h = replace_once(h, old_tab, new_tab, "tab-specific timestamp handler")

h = h.replace('realtime-config.js?v=130', 'realtime-config.js?v=131').replace('realtime.js?v=130', 'realtime.js?v=131')
p.write_text(h, encoding="utf-8")

# ---------- service worker ----------
p = ROOT / "docs" / "sw.js"
w = p.read_text(encoding="utf-8")
w = w.replace("dogson-free-v130", "dogson-free-v131").replace("?v=130", "?v=131")
p.write_text(w, encoding="utf-8")

print("v1.3.1 accuracy patch applied")
