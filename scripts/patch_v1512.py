#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.12 — 盤後族群法人流向改以估算金額為主、張數為輔。

金額不是官方逐股成交金額：用「外資＋投信官方淨買賣股數 × 該交易日收盤價」
逐日估算，再彙總到族群。5日/20日各自使用當日價格，不拿今天股價回推。
此版本只改盤後觀察資料與顯示，不改任何個股/大盤評分公式。
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
        raise SystemExit(f"v1.5.12 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_build_data():
    p = "scripts/build_data.py"
    s = read(p)
    s = re.sub(r"Free Edition v1\.5\.\d+", "Free Edition v1.5.12", s, count=1)
    s = s.replace('"version": "1.5.10-free"', '"version": "1.5.12-free"')

    old = '''    rows = []\n    breadth_changes = []\n'''
    new = '''    rows = []\n    # v1.5.12：沿用這一輪本來就下載的6個月日K，保存各股近期每日收盤價，\n    # 供法人「淨股數 × 當日收盤價」估算歷史金額；不額外再打一輪行情來源。\n    price_history = {}\n    breadth_changes = []\n'''
    if 'price_history = {}' not in s:
        s = must_replace(s, old, new, "price history container")

    old = '''                x = overlay_official_today_bar(x, official_today.get(code))\n                t = close_technical(x)\n'''
    new = '''                x = overlay_official_today_bar(x, official_today.get(code))\n                try:\n                    ph = {}\n                    for idx, px in x["Close"].dropna().tail(45).items():\n                        v = float(px)\n                        if np.isfinite(v) and v > 0:\n                            ph[str(pd.Timestamp(idx).date())] = v\n                    price_history[code] = ph\n                except Exception:\n                    price_history[code] = {}\n                t = close_technical(x)\n'''
    if 'ph[str(pd.Timestamp(idx).date())]' not in s:
        s = must_replace(s, old, new, "capture daily closes")

    s = must_replace(
        s,
        '    sector_funds = build_sector_institution_flow(rows)\n',
        '    sector_funds = build_sector_institution_flow(rows, price_history)\n',
        "pass price history",
    )

    s = must_replace(
        s,
        '        "sector_funds_note": "外資＋投信官方淨買賣股數彙總，單位張；未含自營商；不額外計入個股100分",\n',
        '        "sector_funds_note": "外資＋投信官方淨買賣股數 × 各交易日收盤價估算金額；張數保留；未含自營商；估算金額僅供力度比較，不額外計入個股100分",\n',
        "sector fund note",
    )

    pattern = re.compile(r'def build_sector_institution_flow\(rows\):.*?\n    return out\n(?=def build_intraday\(\):)', re.S)
    replacement = '''def build_sector_institution_flow(rows, price_history=None):\n    """盤後族群法人資金流：官方淨買賣股數 + 同日收盤價估算金額。\n\n    金額 = (外資淨買賣股數 + 投信淨買賣股數) × 該交易日收盤價。\n    這是逐日、逐股估算後再彙總，不是官方逐股實際成交金額；張數仍保留。\n    族群優先採自訂 sector_group，未分類者退回官方 industry_name。\n    此資料只做盤後觀察，不額外灌入個股100分。\n    """\n    history = load_json("chip_history.json", {})\n    price_history = price_history or {}\n    if not isinstance(history, dict) or not rows:\n        return []\n\n    groups = {}\n    for r in rows:\n        sector = str(r.get("sector_group") or "").strip()\n        industry = str(r.get("industry_name") or "").strip()\n        key = sector if sector else (industry if industry and industry != "未分類" else "")\n        if key:\n            groups.setdefault(key, []).append(r)\n\n    out = []\n    for key, members in groups.items():\n        daily = {}\n        for r in members:\n            code = str(r.get("code") or "")\n            prices = price_history.get(code) or {}\n            for h in history.get(code) or []:\n                ds = str(h.get("date") or "")\n                if not ds:\n                    continue\n                fv = h.get("foreign_net")\n                tv = h.get("trust_net")\n                if fv is None and tv is None:\n                    continue\n                try:\n                    net = float(fv or 0) + float(tv or 0)\n                except Exception:\n                    continue\n                z = daily.setdefault(ds, {"shares": 0.0, "amount": 0.0, "records": 0, "priced": 0})\n                z["shares"] += net\n                z["records"] += 1\n                try:\n                    px = float(prices.get(ds))\n                except Exception:\n                    px = None\n                if px is not None and np.isfinite(px) and px > 0:\n                    z["amount"] += net * px\n                    z["priced"] += 1\n\n        ordered = sorted(daily.items(), key=lambda x: x[0], reverse=True)\n        vals = [z["shares"] / 1000.0 for _, z in ordered]  # 股 -> 張\n        amount_vals = []\n        for _, z in ordered:\n            cov = (z["priced"] / z["records"]) if z["records"] else 0.0\n            # 避免少數缺價個股讓族群金額看起來過度精確；單日覆蓋至少80%才採用。\n            amount_vals.append((z["amount"] / 100_000_000.0) if cov >= 0.80 else None)\n\n        latest = vals[0] if vals else None\n        prev = vals[1] if len(vals) >= 2 else None\n        net5 = sum(vals[:5]) if len(vals) >= 5 else None\n        net20 = sum(vals[:20]) if len(vals) >= 20 else None\n\n        latest_amount = amount_vals[0] if amount_vals else None\n        prev_amount = amount_vals[1] if len(amount_vals) >= 2 else None\n        net5_amount = sum(amount_vals[:5]) if len(amount_vals) >= 5 and all(v is not None for v in amount_vals[:5]) else None\n        net20_amount = sum(amount_vals[:20]) if len(amount_vals) >= 20 and all(v is not None for v in amount_vals[:20]) else None\n\n        recent_rows = [z for _, z in ordered[:20]]\n        rec_n = sum(int(z.get("records") or 0) for z in recent_rows)\n        priced_n = sum(int(z.get("priced") or 0) for z in recent_rows)\n        amount_coverage = (priced_n / rec_n * 100.0) if rec_n else 0.0\n        amount_days = sum(v is not None for v in amount_vals)\n\n        # 金額資料完整時，用金額判定流入/流出與加速；否則退回原本張數方向。\n        flow_vals = amount_vals if latest_amount is not None else vals\n        flow_latest = flow_vals[0] if flow_vals else None\n        flow_prev = flow_vals[1] if len(flow_vals) >= 2 else None\n        streak = 0\n        streak_dir = None\n        if flow_latest is not None and flow_latest != 0:\n            streak_dir = 1 if flow_latest > 0 else -1\n            for v in flow_vals:\n                if v is None or v == 0 or (1 if v > 0 else -1) != streak_dir:\n                    break\n                streak += 1\n\n        accelerating = bool(\n            flow_latest is not None and flow_prev is not None and flow_latest * flow_prev > 0\n            and abs(flow_latest) >= abs(flow_prev) * 1.15\n        )\n        if streak_dir == 1:\n            flow_text = f"連續流入 {streak} 天" + (" ↑ 流入加速" if accelerating else "")\n        elif streak_dir == -1:\n            flow_text = f"連續流出 {streak} 天" + (" ↓ 流出加速" if accelerating else "")\n        else:\n            flow_text = "資金方向中性"\n\n        action_latest = latest_amount if latest_amount is not None else latest\n        action_5 = net5_amount if net5_amount is not None else net5\n        if action_latest is None:\n            action = "資料累積中"\n        elif action_latest > 0 and (action_5 is None or action_5 > 0):\n            action = "持續加碼"\n        elif action_latest > 0:\n            action = "轉為加碼"\n        elif action_latest < 0 and (action_5 is None or action_5 < 0):\n            action = "持續減碼"\n        elif action_latest < 0:\n            action = "轉為減碼"\n        else:\n            action = "中性"\n\n        weighted = [\n            (float(r.get("ret5") or 0), max(float(r.get("avg_turnover20") or 0), 1.0))\n            for r in members\n        ]\n        sw = sum(w for _, w in weighted)\n        ret5 = sum(v * w for v, w in weighted) / sw if sw else None\n\n        out.append({\n            "sector": key,\n            "today_amount_100m": None if latest_amount is None else round(latest_amount, 4),\n            "net5_amount_100m": None if net5_amount is None else round(net5_amount, 4),\n            "net20_amount_100m": None if net20_amount is None else round(net20_amount, 4),\n            "amount_history_days": amount_days,\n            "amount_coverage_pct": round(amount_coverage, 1),\n            "amount_method": "外資＋投信淨買賣股數×各交易日收盤價（估算）",\n            "today_lots": None if latest is None else round(latest, 1),\n            "net5_lots": None if net5 is None else round(net5, 1),\n            "net20_lots": None if net20 is None else round(net20, 1),\n            "history_days": len(vals),\n            "latest_date": ordered[0][0] if ordered else None,\n            "flow_streak": streak,\n            "flow_direction": "in" if streak_dir == 1 else "out" if streak_dir == -1 else "flat",\n            "accelerating": accelerating,\n            "flow_text": flow_text,\n            "action": action,\n            "ret5_pct": None if ret5 is None else round(ret5, 2),\n            "member_count": len(members),\n        })\n\n    out.sort(\n        key=lambda x: (\n            abs(float(x.get("net5_amount_100m") or x.get("today_amount_100m") or 0)),\n            abs(float(x.get("net5_lots") or x.get("today_lots") or 0)),\n        ),\n        reverse=True,\n    )\n    return out\n'''
    s2, n = pattern.subn(replacement, s, count=1)
    if n != 1:
        raise SystemExit("v1.5.12 could not replace build_sector_institution_flow")
    s = s2
    write(p, s)


def patch_index():
    p = "docs/index.html"
    s = read(p)
    s = re.sub(
        r"Free Edition v1\.5\.\d+｜[^<]*",
        "Free Edition v1.5.12｜盤後法人金額力度＋盤中族群輪動可收合＋族群共振全可展開",
        s,
        count=1,
    )

    marker = 'function moneyTw(v){if(v===null||v===undefined||Number.isNaN(+v))return "—";v=+v;if(v>=1e8)return num(v/1e8,1)+"億";if(v>=1e7)return num(v/1e7,1)+"千萬";return num(v/1e6,1)+"百萬"}'
    helper = marker + '\nfunction flowMoney(v){if(v===null||v===undefined||Number.isNaN(+v))return "—";v=+v;if(v===0)return "0";const a=Math.abs(v);if(a>=1)return signed(v,2,"億");if(a>=.1)return signed(v*10,1,"千萬");return signed(v*100,1,"百萬")}'
    if 'function flowMoney(v)' not in s:
        s = must_replace(s, marker, helper, "money formatter")

    pattern = re.compile(r'function closeSectorFundsHTML\(\)\{.*?\n\}\n\nfunction rotationHTML', re.S)
    replacement = r'''function closeSectorFundsHTML(){
 const arr=sectorFunds||[];
 const title="🏦 盤後族群法人資金流";
 const sub="外資＋投信官方淨買賣股數 × 各交易日收盤價估算；金額看力度、張數看方向，未含自營商；不額外增加個股100分";
 if(!arr.length)return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div></div><div class="rotationleaders">目前法人歷史資料不足，完成盤後籌碼更新後會顯示。</div></div>`;

 const strength=x=>x.net5_amount_100m??x.today_amount_100m??0;
 const allBuys=arr.filter(x=>(x.today_amount_100m??0)>0).sort((a,b)=>strength(b)-strength(a));
 const allSells=arr.filter(x=>(x.today_amount_100m??0)<0).sort((a,b)=>strength(a)-strength(b));
 const buys=allBuys.slice(0,8),sells=allSells.slice(0,8);
 const periodMoney=(v,need,n)=>v===null||v===undefined?`累積中 ${Math.min(n||0,need)}/${need}日`:flowMoney(v);
 const lotsSub=v=>v===null||v===undefined?"張數待補":signed(v,0,"張");
 const mini=x=>`<div class="closeflowpreviewitem"><span>${x.sector}</span><b>${flowMoney(x.today_amount_100m)}</b></div>`;
 const one=x=>{const buy=(x.today_amount_100m??x.today_lots??0)>0,sell=(x.today_amount_100m??x.today_lots??0)<0;const tag=buy?"buy":sell?"sell":"flat";return `<div class="closeflowcard"><div class="closeflowname">${x.sector}</div><div class="closeflowgrid"><div class="closeflowitem"><span>當日估算淨額</span><b>${flowMoney(x.today_amount_100m)} <small>｜${lotsSub(x.today_lots)}</small></b></div><div class="closeflowitem"><span>近 5 日估算淨額</span><b>${periodMoney(x.net5_amount_100m,5,x.amount_history_days)} <small>｜${x.net5_lots===null||x.net5_lots===undefined?"張數累積中":signed(x.net5_lots,0,"張")}</small></b></div><div class="closeflowitem"><span>近 20 日估算淨額</span><b>${periodMoney(x.net20_amount_100m,20,x.amount_history_days)} <small>｜${x.net20_lots===null||x.net20_lots===undefined?"張數累積中":signed(x.net20_lots,0,"張")}</small></b></div><div class="closeflowitem"><span>近 5 日漲跌</span><b>${signed(x.ret5_pct,2)}</b></div></div><div class="flowtext">資金流向｜${x.flow_text||"—"}</div><div class="closeflowsummary">估算金額覆蓋 ${num(x.amount_coverage_pct,0)}%｜${x.amount_method||"淨買賣股數×當日收盤價"}</div><span class="flowtag ${tag}">${x.action||"觀察"}</span></div>`};

 const preview=`<div class="closeflowpreview"><div class="closeflowpreviewcol"><div class="closeflowpreviewhead">🔴 流入前 3</div>${allBuys.length?allBuys.slice(0,3).map(mini).join(""):`<div class="sub">目前無明顯流入</div>`}</div><div class="closeflowpreviewcol"><div class="closeflowpreviewhead">🟢 流出前 3</div>${allSells.length?allSells.slice(0,3).map(mini).join(""):`<div class="sub">目前無明顯流出</div>`}</div></div><div class="closeflowsummary">依估算金額力度排序｜今日流入 ${allBuys.length} 個族群｜流出 ${allSells.length} 個族群｜完整明細各顯示前 8 名</div>`;
 const detail=sectorFundsOpen?`<div class="rotationcols"><div><div class="rotationhead">🔴 法人流入／加碼</div>${buys.length?buys.map(one).join(""):`<div class="sub">目前沒有明顯法人流入族群</div>`}</div><div><div class="rotationhead">🟢 法人流出／減碼</div>${sells.length?sells.map(one).join(""):`<div class="sub">目前沒有明顯法人流出族群</div>`}</div></div>`:"";
 const label=sectorFundsOpen?"收合族群明細":"展開完整族群";
 const arrow=sectorFundsOpen?"▲":"▼";
 return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">${title}</div><div class="sub">${sub}</div></div><button class="rotationtoggle" type="button" aria-expanded="${sectorFundsOpen}" onclick="toggleCloseSectorFunds()">${arrow} ${label}</button></div>${preview}${detail}</div>`;
}

function rotationHTML'''
    s2, n = pattern.subn(replacement, s, count=1)
    if n != 1:
        raise SystemExit("v1.5.12 could not replace closeSectorFundsHTML")
    s = s2

    old_help = '<b>盤後族群法人資金流：</b>把同族群成分股的外資＋投信官方淨買賣股數加總，顯示當日、近5日、近20日、連續流入/流出與是否加速，再搭配族群近5日漲跌。單位用張，不用目前股價回推歷史億元；此欄不新增個股分數。預設先收合成流入／流出前三名摘要，按「展開完整族群」才顯示完整明細，收合狀態會記住。<br>'
    new_help = '<b>盤後族群法人資金流：</b>外資＋投信官方逐股淨買賣股數，逐日乘上「該交易日收盤價」後加總成族群估算金額；5日／20日都使用各自當日價格，不拿今天股價回推。金額用來比較資金力度、張數仍保留看持股方向；這不是官方逐股實際成交金額，因此畫面明確標示「估算」。此欄不新增個股分數。<br>'
    if '金額用來比較資金力度' not in s:
        s = must_replace(s, old_help, new_help, "money flow help")

    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+", "dogson-free-v1512", s, count=1)
    write(p, s)


if __name__ == "__main__":
    patch_build_data()
    patch_index()
    patch_sw()
    print("v1.5.12 close sector estimated money flow patch applied")
