# -*- coding: utf-8 -*-
"""盤後籌碼資料層（v0.3）

資料優先來源：
- TWSE 三大法人 T86
- TWSE 融資融券 MI_MARGN
- TWSE 融券 / 借券賣出餘額 TWT93U
- TPEx 三大法人、融資融券、融券借券賣出餘額公開資料

設計原則：
- 盤中不假裝有「今天尚未公布」的外資 / 投信 / 融資 / 借券收盤資料。
- 盤中雷達使用最近一個已完成交易日的盤後籌碼快照。
- 某來源暫時取不到時，欄位回傳 None，不因缺資料硬扣分。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import json
import re

import pandas as pd
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

TWSE_T86 = "https://www.twse.com.tw/rwd/zh/fund/T86"
TWSE_MARGIN = "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
TWSE_SBL = "https://www.twse.com.tw/exchangeReport/TWT93U"

TPEX_INST = "https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php"
TPEX_MARGIN = "https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php"
TPEX_SBL = "https://www.tpex.org.tw/web/stock/margin_trading/margin_sbl/margin_sbl_result.php"


def _num(x):
    if x is None:
        return None
    s = str(x).replace(",", "").replace("+", "").strip()
    if s in {"", "-", "--", "nan", "None"}:
        return None
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s or s in {"-", "."}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _roc(d: date) -> str:
    return f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _recent_calendar_days(n=12) -> List[date]:
    today = datetime.now().date()
    out = []
    for i in range(n):
        d = today - timedelta(days=i)
        if d.weekday() < 5:
            out.append(d)
    return out


def _json_table(url: str, params: dict) -> Optional[pd.DataFrame]:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        obj = r.json()
        fields = obj.get("fields") or obj.get("field")
        data = obj.get("data")
        if fields and isinstance(data, list):
            return pd.DataFrame(data, columns=fields)
    except Exception:
        return None
    return None


def _html_table(url: str, params: dict, expected_roc: Optional[str] = None) -> Optional[pd.DataFrame]:
    """抓 TPEx HTML 表格。若頁面日期跟要求日期不符，視為後端忽略日期，避免假造歷史資料。"""
    try:
        p = dict(params)
        p.setdefault("l", "zh-tw")
        p.setdefault("o", "htm")
        r = requests.get(url, params=p, headers=HEADERS, timeout=15)
        r.raise_for_status()
        text = r.text
        if expected_roc:
            roc_compact = expected_roc.replace("/", "")
            # 常見標題：115年09月18日 / 115/09/18
            y, m, d = expected_roc.split("/")
            markers = [expected_roc, f"{y}年{m}月{d}日", roc_compact]
            # 若頁面明確顯示別的日期，且沒有要求日期，就拒絕。
            found_dates = re.findall(r"(\d{3})[年/]\s*(\d{1,2})[月/]\s*(\d{1,2})日?", text)
            if found_dates:
                expected_tuple = (str(int(y)), str(int(m)), str(int(d)))
                normalized = {(str(int(a)), str(int(b)), str(int(c))) for a,b,c in found_dates}
                if expected_tuple not in normalized:
                    return None
        tables = pd.read_html(text)
        candidates = [t for t in tables if t.shape[0] >= 2 and t.shape[1] >= 5]
        if not candidates:
            return None
        return max(candidates, key=lambda t: t.shape[0] * t.shape[1])
    except Exception:
        return None


def _flatten_cols(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = ["|".join([str(y) for y in tup if str(y) != "nan"]).strip("|") for tup in x.columns]
    else:
        x.columns = [str(c) for c in x.columns]
    return x


def _find_col(df: pd.DataFrame, must_include: Iterable[str], any_include: Iterable[str] = ()):  # noqa
    must = list(must_include)
    anys = list(any_include)
    for c in df.columns:
        s = str(c).replace("\n", "").replace(" ", "")
        if all(k in s for k in must) and (not anys or any(k in s for k in anys)):
            return c
    return None


def _code_col(df):
    return _find_col(df, ["代號"]) or _find_col(df, ["Code"]) or _find_col(df, ["SecurityCode"])


def _twse_institution(d: date) -> Optional[pd.DataFrame]:
    return _json_table(TWSE_T86, {"date": _ymd(d), "selectType": "ALLBUT0999", "response": "json"})


def _twse_margin(d: date) -> Optional[pd.DataFrame]:
    return _json_table(TWSE_MARGIN, {"date": _ymd(d), "selectType": "STOCK", "response": "json"})


def _twse_sbl(d: date) -> Optional[pd.DataFrame]:
    return _json_table(TWSE_SBL, {"date": _ymd(d), "response": "json"})


def _tpex_institution(d: date) -> Optional[pd.DataFrame]:
    roc = _roc(d)
    return _html_table(TPEX_INST, {"d": roc, "s": "0,asc"}, expected_roc=roc)


def _tpex_margin(d: date) -> Optional[pd.DataFrame]:
    roc = _roc(d)
    return _html_table(TPEX_MARGIN, {"d": roc}, expected_roc=roc)


def _tpex_sbl(d: date) -> Optional[pd.DataFrame]:
    roc = _roc(d)
    return _html_table(TPEX_SBL, {"d": roc}, expected_roc=roc)


def _extract_inst(df: pd.DataFrame, codes: set) -> Dict[str, dict]:
    if df is None or df.empty:
        return {}
    x = _flatten_cols(df)
    cc = _code_col(x)
    if cc is None:
        return {}

    foreign = (
        _find_col(x, ["外陸資", "買賣超"], ["不含外資自營商"])
        or _find_col(x, ["外資及陸資", "買賣超"], ["不含外資自營商"])
        or _find_col(x, ["外資及陸資(不含外資自營商)", "買賣超股數"])
    )
    trust = _find_col(x, ["投信", "買賣超"])

    out = {}
    for _, r in x.iterrows():
        code = str(r.get(cc, "")).strip()
        if code not in codes:
            continue
        out[code] = {
            "foreign_net": _num(r.get(foreign)) if foreign else None,
            "trust_net": _num(r.get(trust)) if trust else None,
        }
    return out


def _extract_margin(df: pd.DataFrame, codes: set) -> Dict[str, dict]:
    if df is None or df.empty:
        return {}
    x = _flatten_cols(df)
    cc = _code_col(x)
    if cc is None:
        return {}

    bal = (
        _find_col(x, ["融資", "今日餘額"])
        or _find_col(x, ["融資", "當日餘額"])
        or _find_col(x, ["MarginPurchase", "BalanceoftheDay"])
        or _find_col(x, ["資餘額"])
    )
    prev = (
        _find_col(x, ["融資", "前日餘額"])
        or _find_col(x, ["MarginPurchase", "BalanceofPreviousDay"])
        or _find_col(x, ["前資餘額"])
    )
    out = {}
    for _, r in x.iterrows():
        code = str(r.get(cc, "")).strip()
        if code not in codes:
            continue
        out[code] = {"margin_balance": _num(r.get(bal)) if bal else None,
                     "margin_prev": _num(r.get(prev)) if prev else None}
    return out


def _extract_sbl(df: pd.DataFrame, codes: set) -> Dict[str, dict]:
    if df is None or df.empty:
        return {}
    x = _flatten_cols(df)
    cc = _code_col(x)
    if cc is None:
        return {}
    bal = (
        _find_col(x, ["借券賣出", "當日餘額"])
        or _find_col(x, ["借券賣出", "今日餘額"])
        or _find_col(x, ["借券賣出當日餘額"])
    )
    out = {}
    for _, r in x.iterrows():
        code = str(r.get(cc, "")).strip()
        if code not in codes:
            continue
        out[code] = {"sbl_short_balance": _num(r.get(bal)) if bal else None}
    return out


def _market_for(code: str, market_map: dict) -> str:
    return str(market_map.get(code, "上市"))


def _fetch_day(d: date, codes: set, market_map: dict) -> Dict[str, dict]:
    listed = {c for c in codes if _market_for(c, market_map) == "上市"}
    otc = codes - listed
    merged = {c: {} for c in codes}

    if listed:
        for extractor, fetcher in [
            (_extract_inst, _twse_institution),
            (_extract_margin, _twse_margin),
            (_extract_sbl, _twse_sbl),
        ]:
            try:
                part = extractor(fetcher(d), listed)
                for c, vals in part.items(): merged[c].update(vals)
            except Exception:
                pass

    if otc:
        for extractor, fetcher in [
            (_extract_inst, _tpex_institution),
            (_extract_margin, _tpex_margin),
            (_extract_sbl, _tpex_sbl),
        ]:
            try:
                part = extractor(fetcher(d), otc)
                for c, vals in part.items(): merged[c].update(vals)
            except Exception:
                pass

    return merged


def build_chip_signals(codes: Iterable[str], market_map: dict, cache_dir: Path) -> Dict[str, dict]:
    """取得最近 4 個有效盤後快照，計算：外資連3買、借券賣出餘額連3減、投信、融資。

    外資連3買：最近 3 個有資料交易日 foreign_net > 0。
    借券連3減：最近 4 個餘額形成 3 次連續下降。
    """
    codes = {str(c) for c in codes}
    if not codes:
        return {}

    cache_dir.mkdir(exist_ok=True, parents=True)
    cache_file = cache_dir / f"chips_{datetime.now():%Y%m%d}.json"
    if cache_file.exists() and (datetime.now().timestamp() - cache_file.stat().st_mtime) < 1800:
        try:
            obj = json.loads(cache_file.read_text(encoding="utf-8"))
            return {c: obj.get(c, {}) for c in codes}
        except Exception:
            pass

    history = {c: [] for c in codes}
    # 抓到 4 個「至少有一項資料」的交易日為止；最多回看 12 個平日。
    for d in _recent_calendar_days(18):
        day = _fetch_day(d, codes, market_map)
        any_day = False
        for c, vals in day.items():
            if any(v is not None for v in vals.values()):
                any_day = True
                history[c].append({"date": d.isoformat(), **vals})
        if all(len(v) >= 4 for v in history.values() if v):
            break
        # 若這天所有來源都空，通常是假日 / 尚未公布
        if not any_day:
            continue

    out = {}
    for c in codes:
        hs = history.get(c, [])
        # 由新到舊
        foreign_vals = [x.get("foreign_net") for x in hs if x.get("foreign_net") is not None]
        trust_vals = [x.get("trust_net") for x in hs if x.get("trust_net") is not None]
        sbl_vals = [x.get("sbl_short_balance") for x in hs if x.get("sbl_short_balance") is not None]
        margin_vals = [x.get("margin_balance") for x in hs if x.get("margin_balance") is not None]

        foreign_3buy = len(foreign_vals) >= 3 and all(v > 0 for v in foreign_vals[:3])
        # hs 是新 -> 舊；三次連續下降 = 最新 < 前1 < 前2 < 前3
        sbl_3down = len(sbl_vals) >= 4 and (sbl_vals[0] < sbl_vals[1] < sbl_vals[2] < sbl_vals[3])

        margin_3d_pct = None
        if len(margin_vals) >= 4 and margin_vals[3] not in (None, 0):
            margin_3d_pct = (margin_vals[0] / margin_vals[3] - 1) * 100
        margin_status = None
        if margin_3d_pct is not None:
            if margin_3d_pct > 8:
                margin_status = "偏熱"
            elif margin_3d_pct < -5:
                margin_status = "下降"
            else:
                margin_status = "正常"

        latest_date = hs[0]["date"] if hs else None
        out[c] = {
            "chip_date": latest_date,
            "foreign_3buy": foreign_3buy if len(foreign_vals) >= 3 else None,
            "foreign_net_latest": foreign_vals[0] if foreign_vals else None,
            "foreign_3d_net": sum(foreign_vals[:3]) if len(foreign_vals) >= 3 else None,
            "sbl_3down": sbl_3down if len(sbl_vals) >= 4 else None,
            "sbl_balance_latest": sbl_vals[0] if sbl_vals else None,
            "sbl_3change_pct": ((sbl_vals[0]/sbl_vals[3]-1)*100) if len(sbl_vals) >= 4 and sbl_vals[3] else None,
            "trust_net_latest": trust_vals[0] if trust_vals else None,
            "margin_3d_pct": margin_3d_pct,
            "margin_status": margin_status,
            "chip_combo": (foreign_3buy and sbl_3down) if (len(foreign_vals) >= 3 and len(sbl_vals) >= 4) else None,
            "chip_history_days": min(len(hs), 4),
        }

    try:
        # 只把本次取得到的資料寫進快取；下次同日重用。
        cache_file.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return out
