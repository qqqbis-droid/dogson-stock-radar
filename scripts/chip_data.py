# -*- coding: utf-8 -*-
"""盤後籌碼資料層（v0.4 / v1.3.5 repair）

資料來源：
- TWSE 三大法人 T86（可查歷史日）
- TWSE 融資融券 MI_MARGN（可查歷史日）
- TWSE 借券賣出餘額 TWT93U（可查歷史日）
- TPEx 新版 /www/zh-tw/insti/dailyTrade（三大法人，可查歷史日）
- TPEx OpenAPI：三大法人 / 融資融券 / 借券賣出（最新交易日）
- TPEx 舊版歷史頁面保留為融資與借券的備援

設計原則：
- 不把尚未公布或抓不到的資料當成 0。
- 每個來源分開抓；其中一個來源失效不拖累其他欄位。
- 將已成功取得的逐日籌碼保存到 docs/data/chip_history.json，跨工作流程累積。
- 將來源/覆蓋狀態寫到 docs/data/chip_status.json，避免再出現「全部 None 卻不知道哪裡壞」的情況。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import json
import re

import pandas as pd
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "application/json,text/html,text/plain,*/*",
}

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = DATA_DIR / "chip_history.json"
STATUS_FILE = DATA_DIR / "chip_status.json"

TWSE_T86 = "https://www.twse.com.tw/rwd/zh/fund/T86"
TWSE_MARGIN = "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
TWSE_SBL = "https://www.twse.com.tw/exchangeReport/TWT93U"

# TPEx 舊三大法人端點已失效，改用新版 JSON historical endpoint。
TPEX_INST_MODERN = "https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade"
TPEX_INST_OPENAPI = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading"
TPEX_MARGIN_OPENAPI = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_margin_balance"
TPEX_SBL_OPENAPI = "https://www.tpex.org.tw/openapi/v1/tpex_margin_sbl"

# 舊版融資/借券頁面仍留做歷史備援；若官方關閉，OpenAPI + 持久化歷史仍可繼續累積。
TPEX_MARGIN_LEGACY = "https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/margin_bal_result.php"
TPEX_SBL_LEGACY = "https://www.tpex.org.tw/web/stock/margin_trading/margin_sbl/margin_sbl_result.php"

DIAGNOSTICS: List[str] = []


def _diag(msg: str):
    msg = str(msg)
    print("[chips]", msg)
    if msg not in DIAGNOSTICS:
        DIAGNOSTICS.append(msg)
        if len(DIAGNOSTICS) > 120:
            del DIAGNOSTICS[:-120]


def _today_tw() -> date:
    return (datetime.now(timezone.utc) + timedelta(hours=8)).date()


def _num(x):
    if x is None:
        return None
    s = str(x).replace(",", "").replace("+", "").strip()
    s = s.replace("−", "-").replace("－", "-").replace("＋", "+")
    if s in {"", "-", "--", "nan", "None", "null", "<NA>"}:
        return None
    # 括號負數
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    s = re.sub(r"[^0-9.\-]", "", s)
    if not s or s in {"-", "."}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _roc(d: date) -> str:
    return f"{d.year - 1911:03d}/{d.month:02d}/{d.day:02d}"


def _roc_compact(d: date) -> str:
    return f"{d.year - 1911:03d}{d.month:02d}{d.day:02d}"


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _recent_calendar_days(n=18) -> List[date]:
    today = _today_tw()
    out = []
    for i in range(n):
        d = today - timedelta(days=i)
        if d.weekday() < 5:
            out.append(d)
    return out


def _json_table(url: str, params: Optional[dict] = None, label: str = "json") -> Optional[pd.DataFrame]:
    """同時支援 TWSE {fields,data} 與 TPEx OpenAPI list[dict]。"""
    try:
        r = requests.get(url, params=params or {}, headers=HEADERS, timeout=22)
        r.raise_for_status()
        obj = r.json()
        if isinstance(obj, list):
            df = pd.DataFrame(obj)
            _diag(f"{label}: {len(df)} rows")
            return df if not df.empty else None
        if isinstance(obj, dict):
            data = obj.get("data")
            if isinstance(data, list) and data and isinstance(data[0], dict):
                df = pd.DataFrame(data)
                _diag(f"{label}: {len(df)} rows")
                return df
            fields = obj.get("fields") or obj.get("field")
            if fields and isinstance(data, list):
                df = pd.DataFrame(data, columns=fields)
                _diag(f"{label}: {len(df)} rows")
                return df if not df.empty else None
            stat = obj.get("stat") or obj.get("message") or obj.get("msg")
            _diag(f"{label}: no table ({stat or 'empty response'})")
    except Exception as e:
        _diag(f"{label} failed: {type(e).__name__}: {e}")
    return None


def _date_cell_matches(v, d: date) -> bool:
    s = re.sub(r"[^0-9]", "", str(v or ""))
    if not s:
        return False
    return s in {_ymd(d), _roc_compact(d)}


def _openapi_latest(url: str, d: date, label: str) -> Optional[pd.DataFrame]:
    """TPEx OpenAPI 多為最新快照；有 Date 欄就嚴格核對，沒 Date 欄只准套在今天。"""
    df = _json_table(url, label=label)
    if df is None or df.empty:
        return None
    date_col = next((c for c in df.columns if str(c).strip().lower() in {"date", "tradedate", "data date"}), None)
    if date_col is not None:
        mask = df[date_col].map(lambda x: _date_cell_matches(x, d))
        z = df[mask].copy()
        if z.empty:
            return None
        return z
    if d != _today_tw():
        return None
    return df


def _html_table(url: str, params: dict, expected_roc: Optional[str] = None, label: str = "html") -> Optional[pd.DataFrame]:
    try:
        p = dict(params)
        p.setdefault("l", "zh-tw")
        p.setdefault("o", "htm")
        r = requests.get(url, params=p, headers=HEADERS, timeout=22)
        r.raise_for_status()
        text = r.text
        if expected_roc:
            y, m, d = expected_roc.split("/")
            found_dates = re.findall(r"(\d{3})[年/]\s*(\d{1,2})[月/]\s*(\d{1,2})日?", text)
            if found_dates:
                expected_tuple = (str(int(y)), str(int(m)), str(int(d)))
                normalized = {(str(int(a)), str(int(b)), str(int(c))) for a, b, c in found_dates}
                if expected_tuple not in normalized:
                    return None
        tables = pd.read_html(text)
        candidates = [t for t in tables if t.shape[0] >= 2 and t.shape[1] >= 4]
        if not candidates:
            return None
        df = max(candidates, key=lambda t: t.shape[0] * t.shape[1])
        _diag(f"{label}: {len(df)} rows")
        return df
    except Exception as e:
        _diag(f"{label} failed: {type(e).__name__}: {e}")
        return None


def _flatten_cols(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = ["|".join([str(y) for y in tup if str(y) != "nan"]).strip("|") for tup in x.columns]
    else:
        x.columns = [str(c) for c in x.columns]
    return x


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", str(s).lower())


def _find_col(df: pd.DataFrame, must_include: Iterable[str], any_include: Iterable[str] = (), exclude: Iterable[str] = ()):  # noqa
    must = [_norm(x) for x in must_include]
    anys = [_norm(x) for x in any_include]
    excludes = [_norm(x) for x in exclude]
    for c in df.columns:
        s = _norm(c)
        if all(k in s for k in must) and (not anys or any(k in s for k in anys)) and not any(k in s for k in excludes):
            return c
    return None


def _find_exactish(df: pd.DataFrame, names: Iterable[str]):
    wanted = {_norm(x) for x in names}
    for c in df.columns:
        if _norm(c) in wanted:
            return c
    return None


def _code_col(df):
    return (
        _find_exactish(df, ["證券代號", "股票代號", "代號", "SecuritiesCompanyCode", "SecurityCode", "StockCode", "Code"])
        or _find_col(df, ["代號"])
        or _find_col(df, ["securitiescompanycode"])
        or _find_col(df, ["securitycode"])
        or _find_col(df, ["code"])
    )


def _twse_institution(d: date) -> Optional[pd.DataFrame]:
    return _json_table(TWSE_T86, {"date": _ymd(d), "selectType": "ALLBUT0999", "response": "json"}, f"TWSE T86 {d}")


def _twse_margin(d: date) -> Optional[pd.DataFrame]:
    return _json_table(TWSE_MARGIN, {"date": _ymd(d), "selectType": "STOCK", "response": "json"}, f"TWSE margin {d}")


def _twse_sbl(d: date) -> Optional[pd.DataFrame]:
    return _json_table(TWSE_SBL, {"date": _ymd(d), "response": "json"}, f"TWSE TWT93U {d}")


def _tpex_inst_modern(d: date) -> Optional[pd.DataFrame]:
    """新版 TPEx 三大法人歷史 JSON。舊 3itrade_hedge_result.php 已失效。"""
    params = {"type": "Daily", "sect": "EW", "date": _roc(d), "id": "", "response": "json"}
    try:
        r = requests.get(TPEX_INST_MODERN, params=params, headers=HEADERS, timeout=22)
        r.raise_for_status()
        obj = r.json()
        tables = obj.get("tables") or [] if isinstance(obj, dict) else []
        if not tables:
            return None
        table = tables[0]
        resp_date = str(table.get("date") or obj.get("date") or "").strip()
        if resp_date and re.sub(r"[^0-9]", "", resp_date) != _roc_compact(d):
            _diag(f"TPEx inst {d}: wrong response date {resp_date}")
            return None
        rows = table.get("data") or []
        if not rows:
            return None
        # 官方表格欄位順序：0代號 1名稱；2~4 外資及陸資(不含外資自營商)；11~13 投信。
        recs = []
        for row in rows:
            if not row or len(row) < 14:
                continue
            recs.append({
                "證券代號": str(row[0]).strip().strip("=").strip('"'),
                "證券名稱": str(row[1]).strip(),
                "外陸資買賣超股數(不含外資自營商)": row[4],
                "投信買賣超股數": row[13],
            })
        df = pd.DataFrame(recs)
        if not df.empty:
            _diag(f"TPEx modern inst {d}: {len(df)} rows")
            return df
    except Exception as e:
        _diag(f"TPEx modern inst {d} failed: {type(e).__name__}: {e}")
    return None


def _tpex_institution(d: date) -> Optional[pd.DataFrame]:
    # 歷史日優先新版 dailyTrade；若暫時失敗，最新日再用 OpenAPI 備援。
    df = _tpex_inst_modern(d)
    if df is not None and not df.empty:
        return df
    return _openapi_latest(TPEX_INST_OPENAPI, d, f"TPEx inst OpenAPI {d}")


def _tpex_margin(d: date) -> Optional[pd.DataFrame]:
    # 最新日用官方 OpenAPI；歷史日嘗試舊頁面，並由 chip_history 跨日累積補強。
    df = _openapi_latest(TPEX_MARGIN_OPENAPI, d, f"TPEx margin OpenAPI {d}")
    if df is not None and not df.empty:
        return df
    roc = _roc(d)
    return _html_table(TPEX_MARGIN_LEGACY, {"d": roc}, expected_roc=roc, label=f"TPEx margin legacy {d}")


def _tpex_sbl(d: date) -> Optional[pd.DataFrame]:
    df = _openapi_latest(TPEX_SBL_OPENAPI, d, f"TPEx SBL OpenAPI {d}")
    if df is not None and not df.empty:
        return df
    roc = _roc(d)
    return _html_table(TPEX_SBL_LEGACY, {"d": roc}, expected_roc=roc, label=f"TPEx SBL legacy {d}")


def _extract_inst(df: pd.DataFrame, codes: set) -> Dict[str, dict]:
    if df is None or df.empty:
        return {}
    x = _flatten_cols(df)
    cc = _code_col(x)
    if cc is None:
        _diag(f"institution parser: code column missing; cols={list(x.columns)[:12]}")
        return {}

    foreign = (
        _find_exactish(x, [
            "外陸資買賣超股數(不含外資自營商)",
            "外資及陸資(不含外資自營商)買賣超股數",
            "Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Difference",
        ])
        or _find_col(x, ["外陸資", "買賣超"], ["不含外資自營商"])
        or _find_col(x, ["外資及陸資", "買賣超"], ["不含外資自營商"])
        or _find_col(x, ["foreigninvestorsincludemainlandareainvestors", "difference"], exclude=["dealersincluded"])
    )
    trust = (
        _find_exactish(x, ["投信買賣超股數", "SecuritiesInvestmentTrustCompanies-Difference"])
        or _find_col(x, ["投信", "買賣超"])
        or _find_col(x, ["securitiesinvestmenttrustcompanies", "difference"])
    )
    if foreign is None and trust is None:
        _diag(f"institution parser: foreign/trust columns missing; cols={list(x.columns)[:16]}")
        return {}

    out = {}
    for _, r in x.iterrows():
        code = str(r.get(cc, "")).strip().strip("=").strip('"')
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
        _diag(f"margin parser: code column missing; cols={list(x.columns)[:12]}")
        return {}

    bal = (
        _find_col(x, ["融資", "今日餘額"])
        or _find_col(x, ["融資", "當日餘額"])
        or _find_col(x, ["marginpurchase", "balanceoftheday"])
        or _find_col(x, ["marginpurchase", "balance"], exclude=["previous", "prev", "前日"])
        or _find_col(x, ["margin", "balance"], exclude=["short", "previous", "prev"])
        or _find_col(x, ["資餘額"], exclude=["前"])
    )
    prev = (
        _find_col(x, ["融資", "前日餘額"])
        or _find_col(x, ["marginpurchase", "balanceofpreviousday"])
        or _find_col(x, ["marginpurchase", "previous", "balance"])
        or _find_col(x, ["marginpurchase", "prev", "balance"])
        or _find_col(x, ["前資餘額"])
    )
    if bal is None:
        # OpenAPI 欄位偶爾改名；記錄實際欄位便於下一版立即修正。
        _diag(f"margin parser: balance column missing; cols={list(x.columns)[:20]}")
        return {}

    out = {}
    for _, r in x.iterrows():
        code = str(r.get(cc, "")).strip().strip("=").strip('"')
        if code not in codes:
            continue
        out[code] = {
            "margin_balance": _num(r.get(bal)),
            "margin_prev": _num(r.get(prev)) if prev else None,
        }
    return out


def _extract_sbl(df: pd.DataFrame, codes: set) -> Dict[str, dict]:
    if df is None or df.empty:
        return {}
    x = _flatten_cols(df)
    cc = _code_col(x)
    if cc is None:
        _diag(f"SBL parser: code column missing; cols={list(x.columns)[:12]}")
        return {}

    bal = (
        _find_col(x, ["借券賣出", "當日餘額"])
        or _find_col(x, ["借券賣出", "今日餘額"])
        or _find_col(x, ["借券賣出當日餘額"])
        or _find_col(x, ["sbl", "short", "balance"])
        or _find_col(x, ["securitieslending", "short", "balance"])
        or _find_col(x, ["borrow", "short", "balance"])
        or _find_col(x, ["shortsale", "balance"], exclude=["margin"])
    )
    if bal is None:
        _diag(f"SBL parser: balance column missing; cols={list(x.columns)[:20]}")
        return {}

    out = {}
    for _, r in x.iterrows():
        code = str(r.get(cc, "")).strip().strip("=").strip('"')
        if code not in codes:
            continue
        out[code] = {"sbl_short_balance": _num(r.get(bal))}
    return out


def _market_for(code: str, market_map: dict) -> str:
    return str(market_map.get(code, "上市"))


def _apply_source(merged: Dict[str, dict], codes: set, extractor, fetcher, d: date, label: str):
    try:
        df = fetcher(d)
        part = extractor(df, codes)
        populated = 0
        for c, vals in part.items():
            merged[c].update(vals)
            if any(v is not None for v in vals.values()):
                populated += 1
        _diag(f"{label} {d}: populated {populated}/{len(codes)}")
    except Exception as e:
        _diag(f"{label} {d} parser failed: {type(e).__name__}: {e}")


def _fetch_day(d: date, codes: set, market_map: dict) -> Dict[str, dict]:
    listed = {c for c in codes if _market_for(c, market_map) == "上市"}
    otc = codes - listed
    merged = {c: {} for c in codes}

    if listed:
        _apply_source(merged, listed, _extract_inst, _twse_institution, d, "TWSE inst")
        _apply_source(merged, listed, _extract_margin, _twse_margin, d, "TWSE margin")
        _apply_source(merged, listed, _extract_sbl, _twse_sbl, d, "TWSE SBL")

    if otc:
        _apply_source(merged, otc, _extract_inst, _tpex_institution, d, "TPEx inst")
        _apply_source(merged, otc, _extract_margin, _tpex_margin, d, "TPEx margin")
        _apply_source(merged, otc, _extract_sbl, _tpex_sbl, d, "TPEx SBL")

    return merged


def _load_persisted_history(codes: set) -> Dict[str, List[dict]]:
    out = {c: [] for c in codes}
    if not HISTORY_FILE.exists():
        return out
    try:
        obj = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            return out
        for c in codes:
            rows = obj.get(c) or []
            if isinstance(rows, list):
                out[c] = [r for r in rows if isinstance(r, dict) and r.get("date")]
    except Exception as e:
        _diag(f"load chip_history failed: {e}")
    return out


def _merge_history(existing: List[dict], new_rows: List[dict]) -> List[dict]:
    by_date: Dict[str, dict] = {}
    # 舊資料先放，新資料同日覆蓋非 None 欄位。
    for r in existing + new_rows:
        ds = str(r.get("date") or "")
        if not ds:
            continue
        base = by_date.setdefault(ds, {"date": ds})
        for k, v in r.items():
            if k == "date":
                continue
            if v is not None:
                base[k] = v
    rows = sorted(by_date.values(), key=lambda z: z["date"], reverse=True)
    return rows[:40]


def _save_history(history: Dict[str, List[dict]]):
    try:
        HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    except Exception as e:
        _diag(f"save chip_history failed: {e}")


def _save_status(out: Dict[str, dict]):
    try:
        vals = list(out.values())
        status = {
            "updated_at": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
            "codes": len(vals),
            "with_any_history": sum(bool(x.get("chip_history_days")) for x in vals),
            "foreign_latest": sum(x.get("foreign_net_latest") is not None for x in vals),
            "foreign_3d": sum(x.get("foreign_3buy") is not None for x in vals),
            "trust_latest": sum(x.get("trust_net_latest") is not None for x in vals),
            "sbl_latest": sum(x.get("sbl_balance_latest") is not None for x in vals),
            "sbl_3d": sum(x.get("sbl_3down") is not None for x in vals),
            "margin_3d": sum(x.get("margin_status") is not None for x in vals),
            "diagnostics": DIAGNOSTICS[-60:],
        }
        STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        _diag(f"coverage foreignLatest={status['foreign_latest']}/{status['codes']} trust={status['trust_latest']} sblLatest={status['sbl_latest']} foreign3d={status['foreign_3d']} margin3d={status['margin_3d']}")
    except Exception as e:
        _diag(f"save chip_status failed: {e}")


def build_chip_signals(codes: Iterable[str], market_map: dict, cache_dir: Path) -> Dict[str, dict]:
    """取得最近籌碼並計算外資連3買、借券連3減、投信與融資狀態。"""
    codes = {str(c) for c in codes}
    if not codes:
        return {}

    cache_dir.mkdir(exist_ok=True, parents=True)
    cache_file = cache_dir / f"chips_{_today_tw():%Y%m%d}.json"
    if cache_file.exists() and (datetime.now().timestamp() - cache_file.stat().st_mtime) < 1200:
        try:
            obj = json.loads(cache_file.read_text(encoding="utf-8"))
            if any((obj.get(c) or {}).get("chip_history_days") for c in codes):
                return {c: obj.get(c, {}) for c in codes}
        except Exception:
            pass

    persisted = _load_persisted_history(codes)
    fetched = {c: [] for c in codes}

    # 回看 18 個日曆日中的平日；TWSE 與 TPEx 三大法人可補歷史，
    # TPEx 融資/借券若歷史頁失效則用 OpenAPI 最新日 + 持久化歷史逐日累積。
    for d in _recent_calendar_days(18):
        day = _fetch_day(d, codes, market_map)
        for c, vals in day.items():
            if any(v is not None for v in vals.values()):
                fetched[c].append({"date": d.isoformat(), **vals})

        # 若每檔都已有至少 4 個「有資料日」，就不用再打官方站。
        enough = True
        for c in codes:
            merged_tmp = _merge_history(persisted.get(c, []), fetched.get(c, []))
            if len(merged_tmp) < 4:
                enough = False
                break
        if enough:
            break

    history = {}
    for c in codes:
        history[c] = _merge_history(persisted.get(c, []), fetched.get(c, []))
    _save_history(history)

    out = {}
    for c in codes:
        hs = history.get(c, [])
        foreign_rows = [x for x in hs if x.get("foreign_net") is not None]
        trust_rows = [x for x in hs if x.get("trust_net") is not None]
        sbl_rows = [x for x in hs if x.get("sbl_short_balance") is not None]
        margin_rows = [x for x in hs if x.get("margin_balance") is not None]

        foreign_vals = [x["foreign_net"] for x in foreign_rows]
        trust_vals = [x["trust_net"] for x in trust_rows]
        sbl_vals = [x["sbl_short_balance"] for x in sbl_rows]
        margin_vals = [x["margin_balance"] for x in margin_rows]

        foreign_3buy = len(foreign_vals) >= 3 and all(v > 0 for v in foreign_vals[:3])
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
            "foreign_date": foreign_rows[0]["date"] if foreign_rows else None,
            "sbl_date": sbl_rows[0]["date"] if sbl_rows else None,
            "margin_date": margin_rows[0]["date"] if margin_rows else None,
            "trust_date": trust_rows[0]["date"] if trust_rows else None,
            "foreign_3buy": foreign_3buy if len(foreign_vals) >= 3 else None,
            "foreign_net_latest": foreign_vals[0] if foreign_vals else None,
            "foreign_3d_net": sum(foreign_vals[:3]) if len(foreign_vals) >= 3 else None,
            "sbl_3down": sbl_3down if len(sbl_vals) >= 4 else None,
            "sbl_balance_latest": sbl_vals[0] if sbl_vals else None,
            "sbl_3change_pct": ((sbl_vals[0] / sbl_vals[3] - 1) * 100) if len(sbl_vals) >= 4 and sbl_vals[3] else None,
            "trust_net_latest": trust_vals[0] if trust_vals else None,
            "margin_balance_latest": margin_vals[0] if margin_vals else None,
            "margin_3d_pct": margin_3d_pct,
            "margin_status": margin_status,
            "chip_combo": (foreign_3buy and sbl_3down) if (len(foreign_vals) >= 3 and len(sbl_vals) >= 4) else None,
            "chip_history_days": min(len(hs), 4),
        }

    try:
        cache_file.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    _save_status(out)
    return out
