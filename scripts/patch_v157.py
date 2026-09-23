#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.7 — 盤後族群法人資金流。

只處理使用者第 2 點：盤後雷達加入類似截圖的族群法人流向卡。
不改盤中/盤後 100 分權重、不加入收合按鈕、不改相對強弱與族群共振展開。
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def must_replace(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f"v1.5.7 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_chip_data():
    p = "scripts/chip_data.py"
    s = read(p)

    if "def backfill_institution_history(" not in s:
        marker = "\ndef _save_status(out: Dict[str, dict]):\n"
        helper = r'''
def backfill_institution_history(codes: set, market_map: dict, target_days: int = 20, calendar_days: int = 45):
    """只回補外資＋投信歷史，供盤後族群 1/5/20 日法人流向使用。

    不重抓歷史融資/借券，避免盤後流程過慢。資料仍寫回既有
    chip_history.json，之後每日只需補最新交易日。
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

    listed = {c for c in codes if str(market_map.get(c) or "") == "上市"}
    otc = set(codes) - listed

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
    new = '''    history = {}\n    for c in codes:\n        history[c] = _merge_history(persisted.get(c, []), fetched.get(c, []))\n    _save_history(history)\n\n    # v1.5.7: 盤後族群資金流需要 5/20 日官方法人歷史。\n    history = backfill_institution_history(codes, market_map, target_days=20, calendar_days=45)\n\n    out = {}\n'''
    if "v1.5.7: 盤後族群資金流需要" not in s:
        s = must_replace(s, old, new, "call institution backfill")

    if '"institution_history_days"' not in s:
        s = must_replace(
            s,
            '            "chip_history_days": min(len(hs), 4),',
            '            "chip_history_days": min(len(hs), 40),\n            "institution_history_days": len({x.get("date") for x in hs if x.get("date") and (x.get("foreign_net") is not None or x.get("trust_net") is not None)}),',
            "institution history count",
        )

    write(p, s)


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)
    s = re.sub(r"犬子老師飆股雷達 Free Edition v1\.5\.\d+", "犬子老師飆股雷達 Free Edition v1.5.7", s, count=1)

    if "def build_sector_institution_flow(rows):" not in s:
        marker = "\ndef build_intraday():\n"
        helper = r'''
def build_sector_institution_flow(rows):
    """盤後族群法人資金流：外資＋投信官方逐股淨買賣股數彙總。

    單位使用「張」，而不是用現在股價回推歷史億元，避免把估算金額
    誤當成官方歷史資金流。族群優先採自訂 sector_group，未分類者退回
    官方 industry_name。此資料只做盤後觀察，不額外灌入個股 100 分。
    """
    history = load_json("chip_history.json", {})
    if not isinstance(history, dict) or not rows:
        return []

    groups = {}
    for r in rows:
        sector = str(r.get("sector_group") or "").strip()
        industry = str(r.get("industry_name") or "").strip()
        key = sector if sector else (industry if industry and industry != "未分類" else "")
        if key:
            groups.setdefault(key, []).append(r)

    out = []
    for key, members in groups.items():
        daily = {}
        for r in members:
            code = str(r.get("code") or "")
            for h in history.get(code) or []:
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

        ordered = sorted(daily.items(), key=lambda x: x[0], reverse=True)
        vals = [v / 1000.0 for _, v in ordered]  # 股 -> 張
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

        accelerating = bool(
            latest is not None and prev is not None and latest * prev > 0
            and abs(latest) >= abs(prev) * 1.15
        )
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

        weighted = [
            (float(r.get("ret5") or 0), max(float(r.get("avg_turnover20") or 0), 1.0))
            for r in members
        ]
        sw = sum(w for _, w in weighted)
        ret5 = sum(v * w for v, w in weighted) / sw if sw else None

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
        })

    out.sort(
        key=lambda x: (
            abs(float(x.get("net5_lots") or x.get("today_lots") or 0)),
            abs(float(x.get("today_lots") or 0)),
        ),
        reverse=True,
    )
    return out

'''
        s = must_replace(s, marker, "\n" + helper + "def build_intraday():\n", "sector institution helper")

    old_close = '''    rows = add_component_scores(rows, market, preliminary_intraday=False)\n\n    dump("close.json", {\n'''
    new_close = '''    rows = add_component_scores(rows, market, preliminary_intraday=False)\n    sector_funds = build_sector_institution_flow(rows)\n\n    dump("close.json", {\n'''
    if "sector_funds = build_sector_institution_flow(rows)" not in s:
        s = must_replace(s, old_close, new_close, "build close sector funds")

    old_market = '        "market": market,\n        "score_formula": {"mode": "swing_direct_100"'
    new_market = '        "market": market,\n        "sector_funds": sector_funds,\n        "sector_funds_note": "外資＋投信官方淨買賣股數彙總，單位張；未含自營商；不額外計入個股100分",\n        "score_formula": {"mode": "swing_direct_100"'
    if '"sector_funds": sector_funds' not in s:
        s = must_replace(s, old_market, new_market, "close payload sector funds")

    s = re.sub(r'"version": "1\.5\.\d+-free"', '"version": "1.5.7-free"', s, count=1)
    write(p, s)


def patch_index():
    p = "docs/index.html"
    s = read(p)

    s = re.sub(
        r"Free Edition v1\.5\.\d+｜[^<]*",
        "Free Edition v1.5.7｜盤中族群可展開＋盤後法人族群流向＋振幅效率",
        s,
        count=1,
    )

    old_vars = 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[];'
    new_vars = 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[],sectorFunds=[];'
    if "sectorFunds=[]" not in s:
        s = must_replace(s, old_vars, new_vars, "sector funds state")

    css_marker = '.rotationmember:active{transform:scale(.995)}@media(max-width:620px)'
    css_new = '.rotationmember:active{transform:scale(.995)}.closeflowcard{background:#0e131a;border:1px solid #252d39;border-radius:11px;padding:10px;margin:6px 0}.closeflowname{font-size:14px;font-weight:900}.closeflowgrid{display:grid;grid-template-columns:1fr 1fr;gap:5px 10px;margin-top:8px}.closeflowitem{font-size:11px;color:#cbd3df;display:flex;justify-content:space-between;gap:8px}.closeflowitem span:first-child{color:var(--muted)}.flowtext{font-size:11px;font-weight:850;margin-top:8px;line-height:1.45}.flowtag{display:inline-block;margin-top:7px;padding:4px 8px;border-radius:999px;font-size:10px;font-weight:900}.flowtag.buy{color:#ff9cac;border:1px solid #5b2d35;background:#2a171c}.flowtag.sell{color:#75e9a8;border:1px solid #244936;background:#10251b}.flowtag.flat{color:#ffd477;border:1px solid #5a4820;background:#2c2513}@media(max-width:620px)'
    if ".closeflowcard{" not in s:
        s = must_replace(s, css_marker, css_new, "close flow styles")

    old_start = '''function rotationHTML(){\n if(mode!=="intraday")return "";\n const arr=sectorRotation||[];\n'''
    new_start = r'''function closeSectorFundsHTML(){
 const arr=sectorFunds||[];
 const title="🏦 盤後族群法人資金流";
 const sub="外資＋投信官方淨買賣股數彙總（張），未含自營商；這是盤後觀察欄位，不額外增加個股100分";
 if(!arr.length)return `<div class="rotationbox"><div class="rotationtitle">${title}</div><div class="sub">${sub}</div><div class="rotationleaders">目前法人歷史資料不足，完成盤後籌碼更新後會顯示。</div></div>`;
 const buys=arr.filter(x=>(x.today_lots||0)>0).sort((a,b)=>(b.net5_lots??b.today_lots??0)-(a.net5_lots??a.today_lots??0)).slice(0,8);
 const sells=arr.filter(x=>(x.today_lots||0)<0).sort((a,b)=>(a.net5_lots??a.today_lots??0)-(b.net5_lots??b.today_lots??0)).slice(0,8);
 const period=(v,need,n)=>v===null||v===undefined?`累積中 ${Math.min(n||0,need)}/${need}日`:signed(v,0,"張");
 const one=x=>{const buy=(x.today_lots||0)>0,sell=(x.today_lots||0)<0;const tag=buy?"buy":sell?"sell":"flat";return `<div class="closeflowcard"><div class="closeflowname">${x.sector}</div><div class="closeflowgrid"><div class="closeflowitem"><span>當日法人淨買超</span><b>${signed(x.today_lots,0,"張")}</b></div><div class="closeflowitem"><span>近 5 日法人淨買超</span><b>${period(x.net5_lots,5,x.history_days)}</b></div><div class="closeflowitem"><span>近 20 日法人淨買超</span><b>${period(x.net20_lots,20,x.history_days)}</b></div><div class="closeflowitem"><span>近 5 日漲跌</span><b>${signed(x.ret5_pct,2)}</b></div></div><div class="flowtext">資金流向｜${x.flow_text||"—"}</div><span class="flowtag ${tag}">${x.action||"觀察"}</span></div>`};
 return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div></div><div class="rotationcols"><div><div class="rotationhead">🔴 法人流入／加碼</div>${buys.length?buys.map(one).join(""):`<div class="sub">目前沒有明顯法人流入族群</div>`}</div><div><div class="rotationhead">🟢 法人流出／減碼</div>${sells.length?sells.map(one).join(""):`<div class="sub">目前沒有明顯法人流出族群</div>`}</div></div></div>`;
}

function rotationHTML(){
 if(mode==="close")return closeSectorFundsHTML();
 const arr=sectorRotation||[];
'''
    if "function closeSectorFundsHTML()" not in s:
        s = must_replace(s, old_start, new_start, "close rotation renderer")

    old_load = '  closeRows=cj.rows||[];intraRows=ij.rows||[];'
    new_load = '  closeRows=cj.rows||[];sectorFunds=cj.sector_funds||[];intraRows=ij.rows||[];'
    if "sectorFunds=cj.sector_funds||[]" not in s:
        s = must_replace(s, old_load, new_load, "load sector funds")

    help_marker = '<b>盤後波段 100：</b>波段延續＝日K技術50＋籌碼25＋族群15＋流動性10，直接加總100，不再用85分換算；另外獨立計算「進場位置100」，避免好股票在過熱位置仍被誤認為好買點。<br>'
    help_new = help_marker + '<b>盤後族群法人資金流：</b>把同族群成分股的外資＋投信官方淨買賣股數加總，顯示當日、近5日、近20日、連續流入/流出與是否加速，再搭配族群近5日漲跌。單位用張，不用目前股價回推歷史億元；此欄不新增個股分數。<br>'
    if "盤後族群法人資金流：</b>" not in s:
        s = must_replace(s, help_marker, help_new, "close flow help")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v157", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_chip_data()
    patch_build_data()
    patch_index()
    patch_sw()
    print("v1.5.7 close sector institutional flow patch applied")
