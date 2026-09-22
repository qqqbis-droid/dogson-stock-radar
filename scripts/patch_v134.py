#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply v1.3.4: pure intraday market score + sector capital-rotation radar."""

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


NEW_INTRADAY_TECH = r'''def intraday_technical(x):
    # 開盤早段也要能掃描；累積至少 4 根 5 分K 即可開始判斷。
    if len(x) < 4:
        return None
    x = x.copy()
    x.index = pd.to_datetime(x.index)
    latest = x.index[-1].date()
    today = x[x.index.date == latest]
    prev = x[x.index.date < latest]
    if len(today) < 3:
        return None

    c, h, v = today["Close"], today["High"], today["Volume"]
    cur = float(c.iloc[-1])
    typical = (today["High"] + today["Low"] + today["Close"]) / 3
    turnover_s = typical * v
    vwap_s = turnover_s.cumsum() / v.cumsum().replace(0, np.nan)
    vwap = float(vwap_s.iloc[-1])

    p3 = h.shift(1).rolling(3).max()
    p12 = h.shift(1).rolling(12).max()
    b3 = bool(cur > p3.iloc[-1]) if pd.notna(p3.iloc[-1]) else False
    b12 = bool(cur > p12.iloc[-1]) if pd.notna(p12.iloc[-1]) else False
    ma5, ma10 = c.rolling(5).mean(), c.rolling(10).mean()
    if pd.notna(ma10.iloc[-1]):
        trend = bool(cur > ma5.iloc[-1] > ma10.iloc[-1])
    elif pd.notna(ma5.iloc[-1]):
        trend = bool(cur > ma5.iloc[-1])
    else:
        trend = bool(cur >= float(c.iloc[0]))

    n = len(today)
    vals = []
    for d in sorted(set(prev.index.date))[-4:]:
        z = prev[prev.index.date == d]
        if len(z) >= n:
            vals.append(float(z["Volume"].iloc[:n].sum()))
    pace = float(v.sum() / np.median(vals)) if vals and np.median(vals) > 0 else 1.0

    if not prev.empty:
        d = sorted(set(prev.index.date))[-1]
        prev_close = float(prev[prev.index.date == d]["Close"].iloc[-1])
    else:
        prev_close = float(c.iloc[0])
    day_change = (cur / prev_close - 1) * 100 if prev_close else 0
    ret15 = (c.iloc[-1] / c.iloc[-4] - 1) * 100 if len(c) >= 4 else 0
    vwap_dist = (cur / vwap - 1) * 100 if vwap else 0

    # 資金輪動用：目前累積成交金額，以及最近一段 vs 前一段成交金額。
    current_turnover = float(turnover_s.sum())
    pair_n = min(6, len(today) // 2)  # 最多比較最近30分鐘 vs 前30分鐘
    if pair_n >= 3:
        recent_turnover = float(turnover_s.iloc[-pair_n:].sum())
        previous_turnover = float(turnover_s.iloc[-2 * pair_n:-pair_n].sum())
        rotation_window_min = int(pair_n * 5)
    else:
        recent_turnover = None
        previous_turnover = None
        rotation_window_min = None

    score = 0
    reasons = []
    if cur > vwap:
        score += 8; reasons.append("站上VWAP")
    if b3:
        score += 8; reasons.append("3K突破")
    if b12:
        score += 6; reasons.append("60分突破")
    if trend:
        score += 7; reasons.append("5分K短均多頭")
    if 1.5 <= pace < 3.5:
        score += 10; reasons.append(f"量速{pace:.1f}x")
    elif 1.2 <= pace < 1.5:
        score += 5; reasons.append(f"量速{pace:.1f}x")
    elif 3.5 <= pace <= 5:
        score += 6; reasons.append(f"大量速{pace:.1f}x")
    if 1 <= day_change <= 6.5:
        score += 5
    if .2 <= ret15 <= 2.5:
        score += 6; reasons.append("短線動能")

    over = []
    if day_change >= 8.5:
        score -= 10; over.append("接近漲停/漲幅過熱")
    if vwap_dist > 4.5:
        score -= 6; over.append("離VWAP過遠")
    if pace > 5:
        score -= 5; over.append("量速極端")
    if ret15 > 4:
        score -= 5; over.append("15分鐘急拉")

    sr = intraday_sr(x, vwap)
    return {
        "date": str(latest), "time": x.index[-1].strftime("%H:%M"),
        "close": cur, "pace": round(pace, 2), "vwap": round(vwap, 2),
        "vwap_dist": round(vwap_dist, 2), "day_change": round(day_change, 2),
        "break3": b3, "break12": b12, "trend5": trend,
        "current_turnover": round(current_turnover, 0),
        "recent_turnover": round(recent_turnover, 0) if recent_turnover is not None else None,
        "previous_turnover": round(previous_turnover, 0) if previous_turnover is not None else None,
        "rotation_window_min": rotation_window_min,
        "technical_score": max(0, min(50, round(score, 1))),
        "reasons": reasons, "overheat_reasons": over, **sr,
    }'''


NEW_INTRADAY_MARKET_CODE = r'''def intraday_index_snapshot():
    """盤中指數：優先 TWSE MIS，Yahoo 僅作備援。"""
    out = {}

    # 官方 MIS：tse_t00.tw = 加權；otc_o00.tw = 櫃買。
    try:
        rr = requests.get(
            "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
            params={"ex_ch": "tse_t00.tw|otc_o00.tw", "json": "1", "delay": "0", "_": int(now_tw().timestamp() * 1000)},
            headers={"User-Agent": "Mozilla/5.0 DogsonRadar/1.3.4", "Referer": "https://mis.twse.com.tw/stock/index.jsp"},
            timeout=15,
        )
        rr.raise_for_status()
        for x in rr.json().get("msgArray") or []:
            ch = str(x.get("ch") or x.get("ex") or "")
            name = str(x.get("n") or "")
            key = None
            label = None
            if "tse_t00" in ch or "發行量加權" in name:
                key, label = "^TWII", "加權"
            elif "otc_o00" in ch or "櫃買" in name:
                key, label = "^TWOII", "櫃買"
            if not key:
                continue
            try:
                cur = float(str(x.get("z") or "").replace(",", ""))
                prev = float(str(x.get("y") or "").replace(",", ""))
            except Exception:
                continue
            if cur <= 0:
                continue
            change = (cur / prev - 1) * 100 if prev > 0 else None
            out[key] = {
                "label": label, "close": round(cur, 2),
                "change_pct": round(change, 2) if change is not None else None,
                "time": str(x.get("t") or ""), "source": "TWSE MIS",
            }
    except Exception as e:
        print("MIS intraday index", e)

    # Yahoo 只補 MIS 沒抓到的指數。
    missing = [s for s in ["^TWII", "^TWOII"] if s not in out]
    if missing:
        try:
            data = download_intraday(missing)
            for sym, label in [("^TWII", "加權"), ("^TWOII", "櫃買")]:
                if sym not in missing:
                    continue
                x = data.get(sym)
                if x is None or x.empty:
                    continue
                latest = x.index[-1].date()
                today = x[x.index.date == latest]
                prev = x[x.index.date < latest]
                cur = float(today["Close"].iloc[-1])
                if not prev.empty:
                    d = sorted(set(prev.index.date))[-1]
                    pc = float(prev[prev.index.date == d]["Close"].iloc[-1])
                    chg = (cur / pc - 1) * 100 if pc else None
                else:
                    chg = None
                out[sym] = {
                    "label": label, "close": round(cur, 2),
                    "change_pct": round(chg, 2) if chg is not None else None,
                    "time": x.index[-1].strftime("%H:%M"), "source": "Yahoo fallback",
                }
        except Exception as e:
            print("intraday index fallback", e)
    return out


def _weighted_pct(rows, predicate, weight_key="current_turnover"):
    valid = [r for r in rows if (r.get(weight_key) or 0) > 0]
    total = sum(float(r.get(weight_key) or 0) for r in valid)
    if total <= 0:
        return None
    hit = sum(float(r.get(weight_key) or 0) for r in valid if predicate(r))
    return hit / total * 100


def _weighted_avg(rows, value_key, weight_key="current_turnover"):
    valid = [r for r in rows if r.get(value_key) is not None and (r.get(weight_key) or 0) > 0]
    total = sum(float(r.get(weight_key) or 0) for r in valid)
    if total <= 0:
        return None
    return sum(float(r[value_key]) * float(r.get(weight_key) or 0) for r in valid) / total


def build_sector_rotation(rows):
    """用成交金額占比變化 + 價格/VWAP/廣度判斷族群吸金熱度；不是法人淨流入。"""
    usable = [r for r in rows if str(r.get("sector_group") or "").strip()]
    if not usable:
        return []

    total_now = sum(float(r.get("current_turnover") or 0) for r in usable)
    total_recent = sum(float(r.get("recent_turnover") or 0) for r in usable)
    total_prev = sum(float(r.get("previous_turnover") or 0) for r in usable)
    groups = {}
    for r in usable:
        groups.setdefault(str(r.get("sector_group")).strip(), []).append(r)

    out = []
    for name, g in groups.items():
        if len(g) < 2:
            continue
        turnover = sum(float(r.get("current_turnover") or 0) for r in g)
        recent = sum(float(r.get("recent_turnover") or 0) for r in g)
        previous = sum(float(r.get("previous_turnover") or 0) for r in g)
        share = turnover / total_now * 100 if total_now > 0 else None
        recent_share = recent / total_recent * 100 if total_recent > 0 else None
        prev_share = previous / total_prev * 100 if total_prev > 0 else None
        share_change = (recent_share - prev_share) if recent_share is not None and prev_share is not None else None
        up_pct = sum(1 for r in g if float(r.get("day_change") or 0) > 0) / len(g) * 100
        above_vwap_pct = sum(1 for r in g if (r.get("close") or 0) >= (r.get("vwap") or 1e99)) / len(g) * 100
        avg_change = _weighted_avg(g, "day_change")
        avg_pace = _weighted_avg(g, "pace")

        # -10 ~ +10 熱度：占比正在增加、價格上漲、站VWAP、族群擴散、量速都會加分。
        heat = 0.0
        if share_change is not None:
            heat += max(-3.0, min(3.0, share_change * 2.5))
        if avg_change is not None:
            heat += max(-2.5, min(2.5, avg_change * 0.7))
        heat += max(-2.0, min(2.0, (above_vwap_pct - 50) / 20))
        heat += max(-1.5, min(1.5, (up_pct - 50) / 25))
        if avg_pace is not None:
            heat += max(-1.0, min(1.0, (avg_pace - 1.0) * 1.5))
        heat = round(max(-10, min(10, heat)), 1)

        if heat >= 5 and (share_change is None or share_change >= 0) and (avg_change or 0) > 0 and above_vwap_pct >= 60:
            state = "🔥 流入加速"
        elif heat >= 2.5 and (avg_change or 0) >= 0:
            state = "🟢 流入"
        elif heat <= -5 and (avg_change or 0) < 0 and above_vwap_pct <= 40:
            state = "🔻 資金流失"
        elif heat <= -2.5 or (share_change is not None and share_change <= -0.25):
            state = "🟠 降溫"
        else:
            state = "🟡 持平"

        leaders = sorted(
            g,
            key=lambda r: (float(r.get("day_change") or 0), float(r.get("current_turnover") or 0)),
            reverse=True,
        )[:3]
        out.append({
            "sector": name, "state": state, "heat": heat, "count": len(g),
            "change_pct": round(avg_change, 2) if avg_change is not None else None,
            "turnover_share_pct": round(share, 2) if share is not None else None,
            "recent_share_pct": round(recent_share, 2) if recent_share is not None else None,
            "previous_share_pct": round(prev_share, 2) if prev_share is not None else None,
            "share_change_pp": round(share_change, 2) if share_change is not None else None,
            "up_pct": round(up_pct, 1), "above_vwap_pct": round(above_vwap_pct, 1),
            "pace": round(avg_pace, 2) if avg_pace is not None else None,
            "window_min": next((r.get("rotation_window_min") for r in g if r.get("rotation_window_min")), None),
            "leaders": [{"code": r.get("code"), "name": r.get("name"), "change_pct": r.get("day_change")} for r in leaders],
        })

    out.sort(key=lambda x: (x.get("heat") or 0), reverse=True)
    return out


def _side_score(rows, live_info=None):
    """上市/上櫃即時結構，各 0~3 分。"""
    if not rows:
        return 1.5, {"change_pct": None, "above_vwap_pct": None, "breadth_pct": None}
    live_change = (live_info or {}).get("change_pct")
    weighted_change = _weighted_avg(rows, "day_change")
    ch = live_change if live_change is not None else weighted_change
    above = _weighted_pct(rows, lambda r: (r.get("close") or 0) >= (r.get("vwap") or 1e99))
    breadth = sum(1 for r in rows if float(r.get("day_change") or 0) > 0) / len(rows) * 100

    score = 0.0
    if ch is not None:
        score += 1.0 if ch > 0.25 else 0.7 if ch >= 0 else 0.3 if ch > -0.5 else 0
    else:
        score += 0.5
    if above is not None:
        score += 1.0 if above >= 60 else 0.7 if above >= 52 else 0.4 if above >= 45 else 0
    else:
        score += 0.5
    score += 1.0 if breadth >= 60 else 0.7 if breadth >= 52 else 0.4 if breadth >= 45 else 0
    return round(min(3, score), 1), {
        "change_pct": round(ch, 2) if ch is not None else None,
        "above_vwap_pct": round(above, 1) if above is not None else None,
        "breadth_pct": round(breadth, 1),
    }


def build_intraday_market(rows, market_live, rotation, close_market):
    """v1.3.4 盤中 15 分：只用今天即時資料，昨日外資僅背景、不計分。"""
    listed = [r for r in rows if r.get("market") == "上市"]
    otc_rows = [r for r in rows if r.get("market") == "上櫃"]
    taiex_score, taiex_meta = _side_score(listed, market_live.get("^TWII"))
    otc_score, otc_meta = _side_score(otc_rows, market_live.get("^TWOII"))

    breadth = sum(1 for r in rows if float(r.get("day_change") or 0) > 0) / len(rows) * 100 if rows else None
    if breadth is None:
        breadth_score = 1.5
    elif breadth >= 60:
        breadth_score = 3.0
    elif breadth >= 55:
        breadth_score = 2.5
    elif breadth >= 50:
        breadth_score = 1.8
    elif breadth >= 45:
        breadth_score = 0.8
    else:
        breadth_score = 0.0

    turnover_up = _weighted_pct(rows, lambda r: float(r.get("day_change") or 0) > 0)
    above_vwap_turnover = _weighted_pct(rows, lambda r: (r.get("close") or 0) >= (r.get("vwap") or 1e99))
    weighted_pace = _weighted_avg(rows, "pace")
    fund_score = 0.0
    if turnover_up is not None:
        fund_score += 2.0 if turnover_up >= 62 else 1.5 if turnover_up >= 55 else 1.0 if turnover_up >= 50 else 0.5 if turnover_up >= 45 else 0
    else:
        fund_score += 1.0
    if above_vwap_turnover is not None:
        fund_score += 1.0 if above_vwap_turnover >= 60 else 0.7 if above_vwap_turnover >= 52 else 0.3 if above_vwap_turnover >= 45 else 0
    else:
        fund_score += 0.5
    if weighted_pace is not None:
        if weighted_pace >= 1.25 and (turnover_up or 0) >= 55:
            fund_score += 1.0
        elif weighted_pace >= 1.0:
            fund_score += 0.5
    else:
        fund_score += 0.5
    fund_score = round(min(4, fund_score), 1)

    sector_valid = [x for x in rotation if (x.get("count") or 0) >= 2]
    positive = [x for x in sector_valid if (x.get("heat") or 0) >= 2.5]
    negative = [x for x in sector_valid if (x.get("heat") or 0) <= -2.5]
    if sector_valid:
        sector_positive_pct = len(positive) / len(sector_valid) * 100
        sector_score = 2.0 if sector_positive_pct >= 55 else 1.5 if sector_positive_pct >= 40 else 1.0 if sector_positive_pct >= 25 else 0.5 if sector_positive_pct >= 15 else 0.0
    else:
        sector_positive_pct = None
        sector_score = 1.0

    total = round(min(15, taiex_score + otc_score + breadth_score + fund_score + sector_score), 1)
    mode = "偏多" if total >= 11 else "中性" if total >= 7 else "防守"
    threshold = 70 if mode == "偏多" else 76 if mode == "中性" else 82

    return {
        "updated_at": now_tw().isoformat(timespec="seconds"),
        "market_score": total, "market_mode": mode, "radar_threshold": threshold,
        "breadth_up_pct": round(breadth, 1) if breadth is not None else None,
        "turnover_up_pct": round(turnover_up, 1) if turnover_up is not None else None,
        "above_vwap_turnover_pct": round(above_vwap_turnover, 1) if above_vwap_turnover is not None else None,
        "weighted_pace": round(weighted_pace, 2) if weighted_pace is not None else None,
        "sector_positive_pct": round(sector_positive_pct, 1) if sector_positive_pct is not None else None,
        "sector_positive_count": len(positive), "sector_negative_count": len(negative),
        "score_max": 15, "intraday_only": True,
        "foreign_used_in_score": False,
        "background_foreign_date": close_market.get("foreign_date"),
        "background_foreign_twse_billion": close_market.get("foreign_twse_billion"),
        "background_foreign_tpex_billion": close_market.get("foreign_tpex_billion"),
        "components": {
            "taiex": {"score": taiex_score, "max": 3, **taiex_meta},
            "otc": {"score": otc_score, "max": 3, **otc_meta},
            "breadth": {"score": round(breadth_score, 1), "max": 3},
            "funds": {"score": fund_score, "max": 4},
            "sector": {"score": round(sector_score, 1), "max": 2},
        },
        "explain": {
            "taiex": "加權即時結構3分：指數方向＋上市站VWAP成交金額比＋上市上漲家數",
            "otc": "櫃買即時結構3分：指數方向＋上櫃站VWAP成交金額比＋上櫃上漲家數",
            "breadth": "今日即時上漲家數3分",
            "funds": "盤中資金動能4分：上漲股成交金額占比＋站VWAP成交金額占比＋同時間量速",
            "sector": "族群擴散2分：吸金熱度為正的族群比例",
            "foreign": "昨日/最近盤後外資只顯示背景，不計入盤中15分",
        },
    }'''


NEW_MARKET_HTML = r'''function marketHTML(){
 const m=market||{},live=marketLive||{};
 const modeClass=m.market_mode==="偏多"?"yes":m.market_mode==="防守"?"bad":"";
 if(mode==="intraday"&&m.intraday_only){
  const c=m.components||{},ta=c.taiex||{},ot=c.otc||{},br=c.breadth||{},fu=c.funds||{},se=c.sector||{};
  const lt=live["^TWII"]||{},lo=live["^TWOII"]||{};
  const bg=m.background_foreign_date?`昨日/最近外資僅背景：${m.background_foreign_date} 上市 ${signed(m.background_foreign_twse_billion,1,"億")}｜上櫃 ${signed(m.background_foreign_tpex_billion,1,"億")}（不計分）`:`昨日外資僅背景，不計盤中分`;
  return `<div class="markettop"><div><div class="marketmode ${modeClass}">📊 盤中市場：${m.market_mode||"—"}</div><div class="sub">純即時評分｜不吃昨日外資</div></div><div><div class="marketscore">${num(m.market_score,1)}/15</div><div class="label">盤中大盤分</div></div></div>
  <div class="marketgrid">
   <div class="marketitem"><div class="marketv">加權 ${lt.change_pct!==undefined?signed(lt.change_pct):signed(ta.change_pct)}</div><div class="marketl">即時結構 ${num(ta.score,1)}/3｜站VWAP資金 ${num(ta.above_vwap_pct,0)}%</div></div>
   <div class="marketitem"><div class="marketv">櫃買 ${lo.change_pct!==undefined?signed(lo.change_pct):signed(ot.change_pct)}</div><div class="marketl">即時結構 ${num(ot.score,1)}/3｜站VWAP資金 ${num(ot.above_vwap_pct,0)}%</div></div>
   <div class="marketitem"><div class="marketv">上漲家數 ${m.breadth_up_pct===null||m.breadth_up_pct===undefined?"—":num(m.breadth_up_pct,0)+"%"}</div><div class="marketl">市場廣度 ${num(br.score,1)}/3</div></div>
   <div class="marketitem"><div class="marketv">💰 資金動能 ${num(fu.score,1)}/4</div><div class="marketl">上漲股成交額 ${num(m.turnover_up_pct,0)}%｜站VWAP成交額 ${num(m.above_vwap_turnover_pct,0)}%｜量速 ${num(m.weighted_pace,2)}x</div></div>
   <div class="marketitem"><div class="marketv">族群擴散 ${num(se.score,1)}/2</div><div class="marketl">轉強族群 ${m.sector_positive_count||0}｜轉弱 ${m.sector_negative_count||0}</div></div>
   <div class="marketitem"><div class="marketv">昨日外資：背景</div><div class="marketl">${bg}</div></div>
  </div>`;
 }
 const t=m.taiex||{},o=m.otc||{};
 const flowDate=m.foreign_date?`${m.foreign_date} 官方盤後`:`官方資料待補`;
 const flowDays=(+m.foreign_5d_count||0)>0?`近${m.foreign_5d_count}日 ${signed(m.foreign_5d_billion,1,"億")}`:`近5日 —`;
 return `<div class="markettop"><div><div class="marketmode ${modeClass}">📊 盤後市場：${m.market_mode||"—"}</div><div class="sub">品質參考線：${m.radar_threshold||"—"}分</div></div><div><div class="marketscore">${num(m.market_score,1)}/15</div><div class="label">盤後大盤分</div></div></div>
 <div class="marketgrid">
  <div class="marketitem"><div class="marketv">加權 ${signed(t.change_pct)}</div><div class="marketl">${t.trend?"多頭排列":"未完整多頭"} · ${t.close||"—"}</div></div>
  <div class="marketitem"><div class="marketv">櫃買 ${signed(o.change_pct)}</div><div class="marketl">${o.trend?"多頭排列":"未完整多頭"} · ${o.close||"—"}</div></div>
  <div class="marketitem"><div class="marketv">上漲家數 ${m.breadth_up_pct===null||m.breadth_up_pct===undefined?"—":num(m.breadth_up_pct,0)+"%"}</div><div class="marketl">完成交易日市場廣度</div></div>
  <div class="marketitem"><div class="marketv">外資上市 ${signed(m.foreign_twse_billion,1,"億")}</div><div class="marketl">${flowDate}<br>上櫃 ${signed(m.foreign_tpex_billion,1,"億")}｜合計 ${signed(m.foreign_net_billion,1,"億")}<br>${flowDays}｜外資分 ${num(m.foreign_score,1)}/3</div></div>
 </div>`;
}

function rotationHTML(){
 if(mode!=="intraday")return "";
 const arr=sectorRotation||[];
 if(!arr.length)return `<div class="rotationbox"><div class="rotationtitle">💰 族群資金輪動</div><div class="sub">目前資料不足，累積更多5分K後會開始顯示。</div></div>`;
 const hot=arr.filter(x=>(x.heat||0)>=2.5).slice(0,4);
 const cold=[...arr].sort((a,b)=>(a.heat||0)-(b.heat||0)).filter(x=>(x.heat||0)<=-2.5).slice(0,4);
 const one=x=>`<div class="rotationrow"><div><b>${x.state}｜${x.sector}</b><div class="rotationleaders">${(x.leaders||[]).map(s=>`${s.name} ${signed(s.change_pct,1)}`).join(" · ")}</div></div><div class="rotationnums">熱度 ${signed(x.heat,1,"")}<br>族群 ${signed(x.change_pct,1)}｜資金占比 ${num(x.turnover_share_pct,1)}%<br>${x.share_change_pp===null||x.share_change_pp===undefined?"占比變化待累積":`近${x.window_min||30}分占比 ${signed(x.share_change_pp,2,"pp")}`}｜VWAP上 ${num(x.above_vwap_pct,0)}%</div></div>`;
 return `<div class="rotationbox"><div class="rotationtop"><div><div class="rotationtitle">💰 族群資金輪動</div><div class="sub">成交金額占比變化＋價格＋VWAP＋廣度；不是法人淨流入</div></div></div><div class="rotationcols"><div><div class="rotationhead">🔥 吸金中</div>${hot.length?hot.map(one).join(""):`<div class="sub">暫無明顯流入族群</div>`}</div><div><div class="rotationhead">🧊 流失／降溫</div>${cold.length?cold.map(one).join(""):`<div class="sub">暫無明顯流失族群</div>`}</div></div></div>`;
}'''


# ---- patch Python ----
src = BUILD.read_text(encoding="utf-8")
src = src.replace("犬子老師飆股雷達 Free Edition v1.3.3", "犬子老師飆股雷達 Free Edition v1.3.4")
src = src.replace("    * 沿用最近完成交易日的大盤結構分數", "    * 盤中大盤15分只看今日即時結構，不使用昨日外資計分\n    * 族群成交金額占比輪動 / VWAP / 廣度")
src = replace_between(src, "def intraday_technical(", "def add_component_scores(", NEW_INTRADAY_TECH)
src = replace_between(src, "def intraday_index_snapshot(", "def build_intraday(", NEW_INTRADAY_MARKET_CODE)

old = "    rows = add_component_scores(rows, market, preliminary_intraday=True)\n\n    if not rows:"
if old not in src:
    raise RuntimeError("intraday pre-score anchor missing")
src = src.replace(old, "    if not rows:", 1)

old = "    market_live = intraday_index_snapshot()\n\n    dump(\"intraday.json\", {\n        \"updated_at\": now_tw().isoformat(timespec=\"seconds\"),\n        \"market\": market,\n        \"market_intraday\": market_live,\n        \"score_formula\": {\"technical\": 50, \"chip\": 25, \"sector\": 10, \"market\": 15},\n        \"rows\": rows,\n    })"
new = "    market_live = intraday_index_snapshot()\n    sector_rotation = build_sector_rotation(rows)\n    intraday_market = build_intraday_market(rows, market_live, sector_rotation, market)\n    rows = add_component_scores(rows, intraday_market, preliminary_intraday=True)\n\n    dump(\"intraday.json\", {\n        \"updated_at\": now_tw().isoformat(timespec=\"seconds\"),\n        \"market\": intraday_market,\n        \"market_intraday\": market_live,\n        \"sector_rotation\": sector_rotation,\n        \"score_formula\": {\"technical\": 50, \"chip\": 25, \"sector\": 10, \"market\": 15},\n        \"rows\": rows,\n    })"
if old not in src:
    raise RuntimeError("intraday dump anchor missing")
src = src.replace(old, new, 1)
src = src.replace('"version": "1.3.3-free"', '"version": "1.3.4-free"')
BUILD.write_text(src, encoding="utf-8")

# ---- patch UI ----
html = HTML.read_text(encoding="utf-8")
html = html.replace("Free Edition v1.3.3｜官方外資現貨＋5日資金流修正版", "Free Edition v1.3.4｜盤中純即時＋族群資金輪動")
html = html.replace(
    ".footer{position:fixed;",
    ".rotationbox{background:linear-gradient(180deg,#151c27,#111720);border:1px solid var(--line);border-radius:18px;padding:13px;margin:12px 0}.rotationtop{display:flex;justify-content:space-between;align-items:flex-start}.rotationtitle{font-size:18px;font-weight:900}.rotationcols{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.rotationhead{font-size:13px;font-weight:900;margin-bottom:6px}.rotationrow{display:flex;justify-content:space-between;gap:8px;background:#0e131a;border:1px solid #252d39;border-radius:11px;padding:9px;margin:6px 0;font-size:11px}.rotationleaders{color:var(--muted);margin-top:4px}.rotationnums{text-align:right;color:#cbd3df;line-height:1.45;min-width:138px}@media(max-width:620px){.rotationcols{grid-template-columns:1fr}.rotationrow{font-size:10px}}\n.footer{position:fixed;",
    1,
)
html = html.replace('<div id="marketbox" class="marketbox"><div class="empty" style="padding:8px">讀取大盤環境…</div></div>', '<div id="marketbox" class="marketbox"><div class="empty" style="padding:8px">讀取大盤環境…</div></div>\n<div id="rotationbox"></div>', 1)
html = html.replace('let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={};', 'let mode="intraday",filter="all",watchOnly=false,universe=[],closeRows=[],intraRows=[],rows=[],market={},marketLive={},closeMarket={},intraMarket={},sectorRotation=[];', 1)
html = replace_between(html, "function marketHTML(){", "function srHTML(", NEW_MARKET_HTML)
html = html.replace(
    '<b>大盤 15：</b>加權5＋櫃買4＋上漲家數3＋官方外資現貨3。外資改用 TWSE＋TPEx 當日官方買賣超金額，並加入近5日累計方向；盤中沿用最近已完整公布的盤後資料。大盤影響「品質分」與風險判讀，不會把真正剛突破的股票直接擋掉。',
    '<b>大盤 15：</b>盤中改成純即時：加權3＋櫃買3＋今日上漲家數3＋盤中資金動能4＋族群擴散2；昨日外資只顯示背景、不計盤中分。盤後仍用完成交易日的加權／櫃買／廣度／官方外資。<br><b>資金輪動：</b>看族群成交金額占比的近30分鐘變化，再合併漲跌、站VWAP比例、上漲家數與量速；這是吸金熱度，不是法人淨流入。',
    1,
)
html = html.replace('盤中分成兩層：卡片上方「近即時價／近即時漲跌」由瀏覽器約每10秒嘗試更新、最多追蹤5檔；VWAP、量速、突破、支撐壓力與階段判斷仍採5分K雷達。籌碼使用最近已完成交易日資料，不會把尚未公布的今日籌碼冒充成即時資料。', '盤中大盤分只使用今天即時量價、VWAP、市場廣度與族群資金輪動；昨日外資只保留背景提示，不計入盤中15分。個股籌碼仍使用最近已完成交易日資料。族群資金「流入／流失」代表成交資金集中度與價格結構的變化，不等於法人淨買賣。', 1)

old_load = '  market=await m.json();marketLive=ij.market_intraday||{};\n  closeRows=cj.rows||[];intraRows=ij.rows||[];\n  $("updated").textContent=sj.updated_at?new Date(sj.updated_at).toLocaleString("zh-TW",{month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"}):"—";\n  $("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();render();'
new_load = '  closeMarket=await m.json();intraMarket=ij.market||closeMarket;marketLive=ij.market_intraday||{};sectorRotation=ij.sector_rotation||[];market=intraMarket;\n  closeRows=cj.rows||[];intraRows=ij.rows||[];\n  $("updated").textContent=sj.updated_at?new Date(sj.updated_at).toLocaleString("zh-TW",{month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"}):"—";\n  $("status").textContent="已更新";$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();render();'
if old_load not in html:
    raise RuntimeError("HTML load anchor missing")
html = html.replace(old_load, new_load, 1)

old_tab = 'document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");mode=b.dataset.mode;$("modeText").textContent=mode==="intraday"?"盤中：5分K / VWAP / 同時間量速":"盤後：日K / 籌碼 / 大盤 / 支撐壓力";render()});'
new_tab = 'document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");mode=b.dataset.mode;market=mode==="intraday"?intraMarket:closeMarket;$("modeText").textContent=mode==="intraday"?"盤中：純即時大盤 / 5分K / 資金輪動":"盤後：日K / 籌碼 / 大盤 / 支撐壓力";$("marketbox").innerHTML=marketHTML();$("rotationbox").innerHTML=rotationHTML();render()});'
if old_tab not in html:
    raise RuntimeError("HTML tab anchor missing")
html = html.replace(old_tab, new_tab, 1)
HTML.write_text(html, encoding="utf-8")

print("v1.3.4 patch applied")
