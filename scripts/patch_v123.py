from pathlib import Path

p = Path('scripts/build_data.py')
s = p.read_text(encoding='utf-8')

new_universe = '''def get_universe():
    """取得上市 + 上櫃股票清單；TPEx OpenAPI 失敗時改用官方 MOPS CSV。"""
    import io

    frames = []
    old = load_json("universe.json", [])
    old_df = pd.DataFrame(old) if old else pd.DataFrame()

    def normalize_company_df(df, suffix, market):
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
        return o

    configs = [
        {
            "market": "上市",
            "suffix": ".TW",
            "json": TWSE_COMPANY_URL,
            "csv": "https://mopsfin.twse.com.tw/opendata/t187ap03_L.csv",
        },
        {
            "market": "上櫃",
            "suffix": ".TWO",
            "json": TPEX_COMPANY_URL,
            "csv": "https://mopsfin.twse.com.tw/opendata/t187ap03_O.csv",
        },
    ]

    for cfg in configs:
        market = cfg["market"]
        suffix = cfg["suffix"]
        loaded = False

        # 1) 先嘗試官方 OpenAPI JSON
        try:
            r = requests.get(cfg["json"], timeout=30, headers={
                "User-Agent": "Mozilla/5.0 DogsonRadar/1.2.3",
                "Accept": "application/json,text/plain,*/*",
            })
            r.raise_for_status()
            df = pd.DataFrame(r.json())
            o = normalize_company_df(df, suffix, market)
            frames.append(o)
            loaded = True
            print("universe", market, "json", len(o))
        except Exception as e:
            print("universe", market, "json failed", e)

        # 2) JSON 失敗時，用政府公開資料官方 CSV 備援
        if not loaded:
            try:
                r = requests.get(cfg["csv"], timeout=45, headers={
                    "User-Agent": "Mozilla/5.0 DogsonRadar/1.2.3",
                    "Accept": "text/csv,text/plain,*/*",
                })
                r.raise_for_status()
                raw = r.content
                last_err = None
                df = None
                for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
                    try:
                        text = raw.decode(enc)
                        df = pd.read_csv(io.StringIO(text), dtype=str)
                        break
                    except Exception as ex:
                        last_err = ex
                        df = None
                if df is None:
                    raise last_err or ValueError("CSV decode failed")
                o = normalize_company_df(df, suffix, market)
                frames.append(o)
                loaded = True
                print("universe", market, "csv", len(o))
            except Exception as e:
                print("universe", market, "csv failed", e)

        # 3) 兩個官方來源都暫時失效，才保留上次成功清單
        if not loaded and not old_df.empty and "market" in old_df.columns:
            fb = old_df[old_df["market"].astype(str).eq(market)].copy()
            if not fb.empty:
                fb["code"] = fb["code"].astype(str)
                fb["name"] = fb["name"].astype(str)
                if "industry" not in fb.columns:
                    fb["industry"] = "未分類"
                fb["industry"] = fb["industry"].astype(str)
                fb["symbol"] = fb["code"] + suffix
                frames.append(fb[["code", "name", "industry", "market", "symbol"]])
                print("universe", market, "cached", len(fb))

    if not frames:
        raise RuntimeError("無法取得上市上櫃公司清單")
    return pd.concat(frames, ignore_index=True).drop_duplicates("code")
'''

a = s.index('def get_universe():')
b = s.index('\ndef normalize(df):', a)
s = s[:a] + new_universe + s[b:]
s = s.replace('Free Edition v1.2.2', 'Free Edition v1.2.3', 1)
s = s.replace('"version": "1.2.2-free"', '"version": "1.2.3-free"')
p.write_text(s, encoding='utf-8')

ip = Path('docs/index.html')
h = ip.read_text(encoding='utf-8')
h = h.replace('Free Edition v1.2.2｜上櫃＋流動性修正版', 'Free Edition v1.2.3｜上櫃CSV備援＋流動性修正版')
ip.write_text(h, encoding='utf-8')

print('v1.2.3 patch applied')
