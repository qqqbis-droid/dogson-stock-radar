from pathlib import Path
import re

p = Path('scripts/build_data.py')
s = p.read_text(encoding='utf-8')

new_universe = '''def get_universe():
    """取得上市 + 上櫃股票清單，支援 TWSE / TPEx 不同欄位名稱。"""
    frames = []
    old = load_json("universe.json", [])
    old_df = pd.DataFrame(old) if old else pd.DataFrame()

    for url, suffix, market in [
        (TWSE_COMPANY_URL, ".TW", "上市"),
        (TPEX_COMPANY_URL, ".TWO", "上櫃"),
    ]:
        try:
            r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            df = pd.DataFrame(r.json())
            cc = pick_col(df, [
                "公司代號", "股票代號", "代號",
                "SecuritiesCompanyCode", "CompanyCode", "StockCode"
            ])
            nc = pick_col(df, [
                "公司簡稱", "公司名稱", "名稱",
                "CompanyAbbreviation", "SecuritiesCompanyName", "CompanyName"
            ])
            ic = pick_col(df, [
                "產業別", "產業",
                "SecuritiesIndustryCode", "IndustryCode", "Industry"
            ])
            if cc is None:
                raise ValueError(f"{market} 找不到股票代號欄位: {list(df.columns)}")

            o = pd.DataFrame()
            o["code"] = df[cc].astype(str).str.strip()
            o["name"] = df[nc].astype(str).str.strip() if nc else o["code"]
            o["industry"] = df[ic].astype(str).str.strip() if ic else "未分類"
            o["market"] = market
            o = o[o["code"].str.fullmatch(r"\\d{4}", na=False)].copy()
            o["symbol"] = o["code"] + suffix
            if o.empty:
                raise ValueError(f"{market} 股票清單為空")
            frames.append(o)
            print("universe", market, len(o))
        except Exception as e:
            print("universe", market, "fallback", e)
            if not old_df.empty and "market" in old_df.columns:
                fb = old_df[old_df["market"].astype(str).eq(market)].copy()
                if not fb.empty:
                    fb["code"] = fb["code"].astype(str)
                    fb["name"] = fb["name"].astype(str)
                    if "industry" not in fb.columns:
                        fb["industry"] = "未分類"
                    fb["industry"] = fb["industry"].astype(str)
                    fb["symbol"] = fb["code"] + suffix
                    frames.append(fb[["code", "name", "industry", "market", "symbol"]])

    if not frames:
        raise RuntimeError("無法取得上市上櫃公司清單")
    return pd.concat(frames, ignore_index=True).drop_duplicates("code")
'''
a = s.index('def get_universe():')
b = s.index('\ndef normalize(df):', a)
s = s[:a] + new_universe + s[b:]

if 'def liquidity_profile(' not in s:
    anchor = '''def sector_score(n):\n    if n >= 4:\n        return 10\n    if n == 3:\n        return 8\n    if n == 2:\n        return 5\n    return 0\n'''
    liq = '''\n\ndef liquidity_profile(avg_turnover20):\n    """20日平均成交金額流動性分級。"""\n    try:\n        x = float(avg_turnover20)\n    except Exception:\n        return "未知", 0\n    if x < 30_000_000:\n        return "不足", -999\n    if x < 80_000_000:\n        return "偏低", -5\n    if x < 200_000_000:\n        return "正常", 0\n    return "活躍", 2\n'''
    if anchor not in s:
        raise RuntimeError('sector_score anchor not found')
    s = s.replace(anchor, anchor + liq, 1)

old = '''                breadth_changes.append(t["day_change"])\n                if t["avg_turnover20"] < 30_000_000:\n                    continue\n                m = meta.get(sym, {})'''
new = '''                breadth_changes.append(t["day_change"])\n                liq_level, liq_adjust = liquidity_profile(t["avg_turnover20"])\n                if liq_level == "不足":\n                    continue\n                t["liquidity_level"] = liq_level\n                t["liquidity_adjust"] = liq_adjust\n                t["avg_turnover20_mn"] = round(t["avg_turnover20"] / 1_000_000, 1)\n                m = meta.get(sym, {})'''
if old in s:
    s = s.replace(old, new, 1)
elif 't["liquidity_level"]' not in s:
    raise RuntimeError('close liquidity anchor not found')

old = '''        total = float(r.get("technical_score", 0)) + cs + sec + market_score\n        r["score"] = round(max(0, min(100, total)), 1)'''
new = '''        liq_adjust = float(r.get("liquidity_adjust", 0))\n        total = float(r.get("technical_score", 0)) + cs + sec + market_score + liq_adjust\n        r["score"] = round(max(0, min(100, total)), 1)'''
if old in s:
    s = s.replace(old, new, 1)
elif 'market_score + liq_adjust' not in s:
    raise RuntimeError('score anchor not found')

old = '''                    "chip_score": prev.get("chip_score", 12.5),\n                    "chip_coverage_pct": prev.get("chip_coverage_pct", 0),'''
new = '''                    "chip_score": prev.get("chip_score", 12.5),\n                    "chip_coverage_pct": prev.get("chip_coverage_pct", 0),\n                    "avg_turnover20": prev.get("avg_turnover20"),\n                    "avg_turnover20_mn": prev.get("avg_turnover20_mn"),\n                    "liquidity_level": prev.get("liquidity_level", "未知"),\n                    "liquidity_adjust": prev.get("liquidity_adjust", 0),'''
if old in s:
    s = s.replace(old, new, 1)
elif '"liquidity_level": prev.get' not in s:
    raise RuntimeError('intraday liquidity anchor not found')

s = s.replace('犬子老師飆股雷達 Free Edition v1.2.1', '犬子老師飆股雷達 Free Edition v1.2.2', 1)
s = s.replace('固定關注池 + 前一盤後雷達前 150 名', '固定關注池 + 所有通過流動性門檻的股票', 1)
s = s.replace('"version": "1.2.1-free"', '"version": "1.2.2-free"')
p.write_text(s, encoding='utf-8')

ip = Path('docs/index.html')
h = ip.read_text(encoding='utf-8')
h = h.replace('Free Edition v1.2.1｜盤中搜尋修正版', 'Free Edition v1.2.2｜上櫃＋流動性修正版')
h = h.replace(
    '<b>日量比：</b>今天完整成交量 ÷ 20日平均量。<br>',
    '<b>日量比：</b>今天完整成交量 ÷ 20日平均量。<br><b>流動性：</b>20日平均成交金額低於3,000萬直接排除；3,000萬～8,000萬標示偏低並降低品質分；8,000萬～2億正常；2億以上活躍。<br>'
)
helper = 'function signed(v,d=1,suffix="%"){if(v===null||v===undefined||Number.isNaN(+v))return "—";return ((+v)>=0?"+":"")+num(v,d)+suffix}\n'
if 'function moneyTw(' not in h and helper in h:
    h = h.replace(helper, helper + 'function moneyTw(v){if(v===null||v===undefined||Number.isNaN(+v))return "—";v=+v;if(v>=1e8)return num(v/1e8,1)+"億";if(v>=1e7)return num(v/1e7,1)+"千萬";return num(v/1e6,1)+"百萬"}\n', 1)

old = 'if(mode==="intraday")return [["現價",num(r.close,2)],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["當日",signed(r.day_change,1)],["VWAP",num(r.vwap,2)],["族群共振",(r.industry_hot_count||0)+"檔"]];'
new = 'if(mode==="intraday")return [["現價",num(r.close,2)],["同時間量速",num(r.pace,1)+"x"],["距VWAP",signed(r.vwap_dist,1)],["當日",signed(r.day_change,1)],["VWAP",num(r.vwap,2)],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["族群共振",(r.industry_hot_count||0)+"檔"]];'
if old in h:
    h = h.replace(old, new, 1)

old = 'return [["收盤",num(r.close,2)],["日量比",num(r.vol_x,1)+"x"],["距20MA",signed(r.dist20,1)],["5日漲幅",signed(r.ret5,1)],["20日漲幅",signed(r.ret20,1)],["RSI",num(r.rsi,0)],["5MA",num(r.ma5,2)],["10MA",num(r.ma10,2)],["20MA",num(r.ma20,2)],["20日突破",r.break20?"是":"否"],["均線多頭",r.trend?"是":"否"],["族群共振",(r.industry_hot_count||0)+"檔"]];'
new = 'return [["收盤",num(r.close,2)],["日量比",num(r.vol_x,1)+"x"],["流動性",(r.liquidity_level||"—")+" · "+moneyTw(r.avg_turnover20)],["距20MA",signed(r.dist20,1)],["5日漲幅",signed(r.ret5,1)],["20日漲幅",signed(r.ret20,1)],["RSI",num(r.rsi,0)],["5MA",num(r.ma5,2)],["10MA",num(r.ma10,2)],["20MA",num(r.ma20,2)],["20日突破",r.break20?"是":"否"],["均線多頭",r.trend?"是":"否"],["族群共振",(r.industry_hot_count||0)+"檔"]];'
if old in h:
    h = h.replace(old, new, 1)

h = h.replace(
    '階段看價格行為｜品質分 = 技術50 + 籌碼25 + 族群10 + 大盤15',
    '階段看價格行為｜品質分 = 技術50 + 籌碼25 + 族群10 + 大盤15 ± 流動性修正'
)
ip.write_text(h, encoding='utf-8')

sw = Path('docs/sw.js')
if sw.exists():
    x = sw.read_text(encoding='utf-8')
    x = re.sub(r'dogson-free-v\w+', 'dogson-free-v122', x)
    sw.write_text(x, encoding='utf-8')

print('v1.2.2 patch applied')
