#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply v1.3.3: use official TWSE + TPEx foreign cash-flow totals for market scoring."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_data.py"
HTML = ROOT / "docs" / "index.html"


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"start marker not found: {start_marker}")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"end marker not found: {end_marker}")
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


NEW_MARKET_CODE = r'''def _market_num(x):
    if x is None:
        return None
    s = str(x).replace(",", "").replace("+", "").replace("−", "-").strip()
    if s in {"", "-", "--", "nan", "None"}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _flatten_market_table(df):
    x = df.copy()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = ["|".join(str(v) for v in col if str(v) != "nan").strip("|") for col in x.columns]
    else:
        x.columns = [str(c) for c in x.columns]
    return x


def _twse_foreign_value(d):
    """TWSE BFI82U: foreign-investor net buy/sell amount in TWD for one trading day."""
    try:
        rr = requests.get(
            "https://www.twse.com.tw/rwd/zh/fund/BFI82U",
            params={"dayDate": d.strftime("%Y%m%d"), "response": "json", "type": "day"},
            headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.3", "Accept": "application/json,text/plain,*/*"},
            timeout=20,
        )
        rr.raise_for_status()
        obj = rr.json()
        obj_date = str(obj.get("date") or "").replace("/", "").replace("-", "")
        if obj_date and d.strftime("%Y%m%d") not in obj_date:
            return None
        fields = obj.get("fields") or obj.get("field")
        data = obj.get("data")
        if not fields or not isinstance(data, list):
            return None
        df = pd.DataFrame(data, columns=fields)
        name_col = pick_col(df, ["單位名稱", "名稱"])
        net_col = pick_col(df, ["買賣差額", "買賣超"])
        if name_col is None or net_col is None:
            return None
        names = df[name_col].astype(str)
        hit = df[names.str.contains("外資及陸資", na=False) & names.str.contains("不含", na=False)]
        if hit.empty:
            return None
        return _market_num(hit.iloc[0][net_col])
    except Exception as e:
        print("TWSE official foreign flow", d, e)
        return None


def _tpex_foreign_value(d):
    """TPEx 3-institution summary: foreign-investor net buy/sell amount in TWD."""
    import io

    roc = f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"
    try:
        rr = requests.get(
            "https://www.tpex.org.tw/web/stock/3insti/3insti_summary/3itrdsum_result.php",
            params={"d": roc, "l": "zh-tw", "o": "htm", "p": "1", "t": "D"},
            headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.3", "Accept-Language": "zh-TW,zh;q=0.9"},
            timeout=20,
        )
        rr.raise_for_status()
        text = rr.text
        date_markers = [
            roc,
            f"{d.year - 1911}年{d.month:02d}月{d.day:02d}日",
            f"{d.year - 1911}年{d.month}月{d.day}日",
        ]
        if not any(m in text for m in date_markers):
            return None
        tables = pd.read_html(io.StringIO(text))
        for raw in tables:
            if raw.empty or raw.shape[1] < 3:
                continue
            df = _flatten_market_table(raw)
            name_col = next((c for c in df.columns if "單位名稱" in str(c)), df.columns[0])
            net_col = next((c for c in df.columns if "買賣超" in str(c)), None)
            if net_col is None:
                continue
            names = df[name_col].astype(str).str.replace(" ", "", regex=False)
            hit = df[names.str.contains("外資及陸資", na=False) & names.str.contains("不含", na=False)]
            if hit.empty:
                hit = df[names.str.contains("外資及陸資合計", na=False)]
            if not hit.empty:
                return _market_num(hit.iloc[0][net_col])
        return None
    except Exception as e:
        print("TPEx official foreign flow", d, e)
        return None


def fetch_market_foreign_flow(need=5, lookback=18):
    """Return the latest complete TWSE+TPEx official foreign cash-flow record and recent trend."""
    records = []
    today = now_tw().date()
    for i in range(lookback):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        twse = _twse_foreign_value(d)
        tpex = _tpex_foreign_value(d)
        # Market-level score only accepts a complete listed + OTC pair.
        if twse is None or tpex is None:
            continue
        total = twse + tpex
        records.append({
            "date": d.isoformat(),
            "twse": twse,
            "tpex": tpex,
            "total": total,
        })
        if len(records) >= need:
            break

    if not records:
        return {
            "date": None, "twse_net": None, "tpex_net": None,
            "total_net": None, "five_day_net": None, "count": 0, "days": []
        }

    latest = records[0]
    return {
        "date": latest["date"],
        "twse_net": latest["twse"],
        "tpex_net": latest["tpex"],
        "total_net": latest["total"],
        "five_day_net": sum(x["total"] for x in records),
        "count": len(records),
        "days": records,
    }


def _foreign_market_score(flow):
    """Foreign component 0~3: latest direction 0.5~2 points + recent cumulative trend 0~1 point."""
    net = flow.get("total_net")
    trend = flow.get("five_day_net")
    count = int(flow.get("count") or 0)
    if net is None:
        return 1.5

    if net > 0:
        base = 2.0
    elif net < 0:
        base = 0.5
    else:
        base = 1.0

    if trend is None or count < 3:
        bonus = 0.5
    elif trend > 0:
        bonus = 1.0
    elif trend == 0:
        bonus = 0.5
    else:
        bonus = 0.0
    return round(min(3.0, max(0.0, base + bonus)), 1)


def build_market(breadth_pct, chips=None):
    taiex = index_state("^TWII", "加權")
    otc = index_state("^TWOII", "櫃買")

    # v1.3.3: market foreign score must use the official all-market cash-flow summary,
    # not a sum of 4-digit stock-pool share counts.
    foreign = fetch_market_foreign_flow()
    foreign_score = _foreign_market_score(foreign)

    score = 0.0
    if taiex:
        score += 5 if taiex["trend"] else 2.5 if taiex["above20"] else 0
    else:
        score += 2.5  # 缺資料中性
    if otc:
        score += 4 if otc["trend"] else 2 if otc["above20"] else 0
    else:
        score += 2
    if breadth_pct is not None:
        if breadth_pct >= 60: score += 3
        elif breadth_pct >= 55: score += 2.5
        elif breadth_pct >= 50: score += 1.5
        elif breadth_pct >= 45: score += 0.5
    else:
        score += 1.5
    score += foreign_score

    score = round(min(15, score), 1)
    mode = "偏多" if score >= 11 else "中性" if score >= 7 else "防守"
    threshold = 70 if mode == "偏多" else 76 if mode == "中性" else 82

    def billion(v):
        return round(v / 100_000_000, 1) if v is not None else None

    return {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "market_score": score,
        "market_mode": mode,
        "radar_threshold": threshold,
        "breadth_up_pct": round(breadth_pct, 1) if breadth_pct is not None else None,
        "foreign_date": foreign.get("date"),
        "foreign_net_billion": billion(foreign.get("total_net")),
        "foreign_twse_billion": billion(foreign.get("twse_net")),
        "foreign_tpex_billion": billion(foreign.get("tpex_net")),
        "foreign_5d_billion": billion(foreign.get("five_day_net")),
        "foreign_5d_count": int(foreign.get("count") or 0),
        "foreign_score": foreign_score,
        "foreign_source": "TWSE BFI82U + TPEx 三大法人買賣金額彙總表",
        "taiex": taiex,
        "otc": otc,
        "score_max": 15,
        "explain": {
            "taiex": "加權趨勢最多5分",
            "otc": "櫃買趨勢最多4分",
            "breadth": "上漲家數比最多3分",
            "foreign": "官方外資現貨：當日方向最多2分＋近5日累計最多1分",
        },
    }'''


NEW_MARKET_HTML = r'''function marketHTML(){
 const m=market||{},t=m.taiex||{},o=m.otc||{},live=marketLive||{};
 const lt=live["^TWII"]||{},lo=live["^TWOII"]||{};
 const modeClass=m.market_mode==="偏多"?"yes":m.market_mode==="防守"?"bad":"";
 const flowDate=m.foreign_date?`${m.foreign_date} 官方盤後`:`官方資料待補`;
 const flowDays=(+m.foreign_5d_count||0)>0?`近${m.foreign_5d_count}日 ${signed(m.foreign_5d_billion,1,"億")}`:`近5日 —`;
 return `<div class="markettop"><div><div class="marketmode ${modeClass}">📊 市場環境：${m.market_mode||"—"}</div><div class="sub">品質參考線：${m.radar_threshold||"—"}分</div></div><div><div class="marketscore">${num(m.market_score,1)}/15</div><div class="label">大盤分</div></div></div>
 <div class="marketgrid">
  <div class="marketitem"><div class="marketv">加權 ${lt.change_pct!==undefined?signed(lt.change_pct):signed(t.change_pct)}</div><div class="marketl">${t.trend?"多頭排列":"未完整多頭"} · ${lt.close||t.close||"—"}</div></div>
  <div class="marketitem"><div class="marketv">櫃買 ${lo.change_pct!==undefined?signed(lo.change_pct):signed(o.change_pct)}</div><div class="marketl">${o.trend?"多頭排列":"未完整多頭"} · ${lo.close||o.close||"—"}</div></div>
  <div class="marketitem"><div class="marketv">上漲家數 ${m.breadth_up_pct===null||m.breadth_up_pct===undefined?"—":num(m.breadth_up_pct,0)+"%"}</div><div class="marketl">最近完成交易日市場廣度</div></div>
  <div class="marketitem"><div class="marketv">外資現貨 ${signed(m.foreign_net_billion,1,"億")}</div><div class="marketl">${flowDate}<br>上市 ${signed(m.foreign_twse_billion,1,"億")}｜上櫃 ${signed(m.foreign_tpex_billion,1,"億")}<br>${flowDays}｜外資分 ${num(m.foreign_score,1)}/3</div></div>
 </div>`;
}'''


# Patch build_data.py
src = BUILD.read_text(encoding="utf-8")
src = src.replace("犬子老師飆股雷達 Free Edition v1.3.1", "犬子老師飆股雷達 Free Edition v1.3.3")
src = replace_between(src, "def build_market(", "def intraday_sr(", NEW_MARKET_CODE)
src = src.replace('"version": "1.3.1-free"', '"version": "1.3.3-free"')
BUILD.write_text(src, encoding="utf-8")

# Patch UI
html = HTML.read_text(encoding="utf-8")
html = html.replace(
    "Free Edition v1.3.2｜收盤覆核＋籌碼狀態修正版",
    "Free Edition v1.3.3｜官方外資現貨＋5日資金流修正版",
)
html = html.replace(
    '<b>大盤 15：</b>加權、櫃買、上漲家數比與全市場外資方向。大盤現在影響「品質分」與風險判讀，不會把真正剛突破的股票直接擋掉。',
    '<b>大盤 15：</b>加權5＋櫃買4＋上漲家數3＋官方外資現貨3。外資改用 TWSE＋TPEx 當日官方買賣超金額，並加入近5日累計方向；盤中沿用最近已完整公布的盤後資料。大盤影響「品質分」與風險判讀，不會把真正剛突破的股票直接擋掉。',
)
html = replace_between(html, "function marketHTML(){", "function srHTML(r){", NEW_MARKET_HTML)
HTML.write_text(html, encoding="utf-8")

print("v1.3.3 patch applied")
