#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
犬子老師飆股雷達 Free Edition
GitHub Actions 資料產生器。

設計：
- close.json：全市場日K雷達資料（盤後完整）
- intraday.json：活躍池（固定關注 + 日K前150名）的5分K資料
- universe.json：搜尋用股票清單
- status.json：最後更新時間

完全不需要常駐伺服器。
"""
from __future__ import annotations
import json, math, time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "data"
OUT.mkdir(parents=True, exist_ok=True)

TW = timezone(timedelta(hours=8))
TWSE_COMPANY_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_COMPANY_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"

def pick_col(df, names):
    for n in names:
        if n in df.columns:
            return n
    for c in df.columns:
        for n in names:
            if n in str(c):
                return c
    return None

def get_universe():
    frames=[]
    for url,suffix,market in [
        (TWSE_COMPANY_URL, ".TW", "上市"),
        (TPEX_COMPANY_URL, ".TWO", "上櫃")
    ]:
        try:
            r=requests.get(url,timeout=20,headers={"User-Agent":"Mozilla/5.0"})
            r.raise_for_status()
            df=pd.DataFrame(r.json())
            cc=pick_col(df,["公司代號","股票代號","代號"])
            nc=pick_col(df,["公司簡稱","公司名稱","名稱"])
            ic=pick_col(df,["產業別","產業"])
            if cc is None: continue
            o=pd.DataFrame()
            o["code"]=df[cc].astype(str).str.strip()
            o["name"]=df[nc].astype(str).str.strip() if nc else o["code"]
            o["industry"]=df[ic].astype(str).str.strip() if ic else "未分類"
            o["market"]=market
            o=o[o["code"].str.fullmatch(r"\d{4}",na=False)].copy()
            o["symbol"]=o["code"]+suffix
            frames.append(o)
        except Exception as e:
            print("universe",market,e)
    if not frames:
        raise RuntimeError("無法取得上市上櫃公司清單")
    return pd.concat(frames,ignore_index=True).drop_duplicates("code")

def normalize(df):
    if df is None or df.empty: return pd.DataFrame()
    rename={}
    for c in df.columns:
        s=str(c).lower()
        if s=="open":rename[c]="Open"
        elif s=="high":rename[c]="High"
        elif s=="low":rename[c]="Low"
        elif s=="close":rename[c]="Close"
        elif s=="volume":rename[c]="Volume"
    df=df.rename(columns=rename)
    need=["Open","High","Low","Close","Volume"]
    if any(c not in df.columns for c in need):return pd.DataFrame()
    x=df[need].copy()
    for c in need:x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna(subset=["Close","Volume"])
    x.index=pd.to_datetime(x.index)
    return x

def split_bulk(raw, syms):
    out={}
    if raw is None or raw.empty:return out
    if isinstance(raw.columns,pd.MultiIndex):
        l0=set(map(str,raw.columns.get_level_values(0)))
        l1=set(map(str,raw.columns.get_level_values(1)))
        for s in syms:
            try:
                d=raw[s].copy() if s in l0 else raw.xs(s,axis=1,level=1).copy() if s in l1 else None
                d=normalize(d)
                if not d.empty:out[s]=d
            except:pass
    elif len(syms)==1:
        d=normalize(raw)
        if not d.empty:out[syms[0]]=d
    return out

def download_daily(syms,period="6mo"):
    raw=yf.download(syms,period=period,interval="1d",group_by="ticker",auto_adjust=False,threads=True,progress=False)
    return split_bulk(raw,syms)

def download_intraday(syms):
    raw=yf.download(syms,period="5d",interval="5m",group_by="ticker",auto_adjust=False,threads=True,progress=False,prepost=False)
    return split_bulk(raw,syms)

def rsi(s,n=14):
    d=s.diff();u=d.clip(lower=0);dn=-d.clip(upper=0)
    au=u.ewm(alpha=1/n,adjust=False).mean();ad=dn.ewm(alpha=1/n,adjust=False).mean()
    rs=au/ad.replace(0,np.nan)
    return (100-100/(1+rs)).fillna(50)

def macd_hist(s):
    e12=s.ewm(span=12,adjust=False).mean();e26=s.ewm(span=26,adjust=False).mean()
    m=e12-e26;sig=m.ewm(span=9,adjust=False).mean()
    return m-sig

def tr(df):
    pc=df["Close"].shift(1)
    return pd.concat([(df["High"]-df["Low"]).abs(),(df["High"]-pc).abs(),(df["Low"]-pc).abs()],axis=1).max(axis=1)

def pivots(df,lookback=70,order=2):
    z=df.tail(lookback);sup=[];res=[]
    for i in range(order,max(order,len(z)-order)):
        lo=float(z["Low"].iloc[i]);hi=float(z["High"].iloc[i])
        if lo<=float(z["Low"].iloc[i-order:i+order+1].min()):sup.append((lo,"前波低點"))
        if hi>=float(z["High"].iloc[i-order:i+order+1].max()):res.append((hi,"前波高點"))
    return sup,res

def zone(current,candidates,atr,side,intraday=False):
    c=[]
    for p,l in candidates:
        try:p=float(p)
        except:continue
        if not np.isfinite(p) or p<=0:continue
        if side=="support" and p<=current*1.002:c.append((p,l))
        if side=="resistance" and p>=current*.998:c.append((p,l))
    if not c:return None
    c.sort(key=lambda x:abs(x[0]-current));seed=c[0][0]
    pct=.007 if intraday else .012
    cl=[x for x in c if abs(x[0]/seed-1)<=pct]
    center=float(np.median([x[0] for x in cl]))
    half=max(current*(.0025 if intraday else .004),(atr or 0)*(.20 if intraday else .25))
    labels=[]
    for _,l in cl:
        if l not in labels:labels.append(l)
    return {"low":round(max(0,center-half),2),"high":round(center+half,2),"center":round(center,2),
            "distance_pct":round((center/current-1)*100,2),"basis":"＋".join(labels[:3])}

def daily_sr(x):
    if len(x)<25:return {"support":None,"resistance":None}
    cur=float(x["Close"].iloc[-1]);atr=float(tr(x).rolling(14).mean().iloc[-1])
    sup,res=pivots(x)
    c=x["Close"]
    for n,label in [(5,"5MA"),(10,"10MA"),(20,"20MA")]:
        p=float(c.rolling(n).mean().iloc[-1]);(sup if p<=cur else res).append((p,label))
    hist=x.iloc[:-1]
    if len(hist)>=20:
        sup.append((float(hist["Low"].tail(20).min()),"20日低"))
        res.append((float(hist["High"].tail(20).max()),"20日高"))
    if len(hist):
        sup.append((float(hist["Low"].iloc[-1]),"前日低"))
        res.append((float(hist["High"].iloc[-1]),"前日高"))
    return {"support":zone(cur,sup,atr,"support"),"resistance":zone(cur,res,atr,"resistance")}

def daily_score(x):
    if len(x)<35:return None
    c=x["Close"];h=x["High"];v=x["Volume"]
    ma5=c.rolling(5).mean();ma10=c.rolling(10).mean();ma20=c.rolling(20).mean()
    vx=v/(v.rolling(20).mean().shift(1).replace(0,np.nan))
    ret5=(c/c.shift(5)-1)*100;ret20=(c/c.shift(20)-1)*100
    dist=(c/ma20-1)*100;rr=rsi(c);mh=macd_hist(c)
    p3=h.shift(1).rolling(3).max();p20=h.shift(1).rolling(20).max()
    row={
      "close":float(c.iloc[-1]),"ma5":float(ma5.iloc[-1]),"ma10":float(ma10.iloc[-1]),"ma20":float(ma20.iloc[-1]),
      "vol_x":float(vx.iloc[-1]) if pd.notna(vx.iloc[-1]) else 0,
      "ret5":float(ret5.iloc[-1]) if pd.notna(ret5.iloc[-1]) else 0,
      "ret20":float(ret20.iloc[-1]) if pd.notna(ret20.iloc[-1]) else 0,
      "dist20":float(dist.iloc[-1]) if pd.notna(dist.iloc[-1]) else 0,
      "rsi":float(rr.iloc[-1]),"macd_h":float(mh.iloc[-1]),"macd_acc":float(mh.iloc[-1]-mh.iloc[-2]),
      "break3":bool(c.iloc[-1]>p3.iloc[-1]) if pd.notna(p3.iloc[-1]) else False,
      "break20":bool(c.iloc[-1]>p20.iloc[-1]) if pd.notna(p20.iloc[-1]) else False,
      "trend":bool(c.iloc[-1]>ma5.iloc[-1]>ma10.iloc[-1]>ma20.iloc[-1]),
      "avg_turnover20":float((c*v).rolling(20).mean().iloc[-1]),
      "date":str(x.index[-1].date())
    }
    score=0
    if row["trend"]:score+=15
    if row["break3"]:score+=10
    if row["break20"]:score+=15
    if 1.8<=row["vol_x"]<4:score+=15
    elif 1.3<=row["vol_x"]<1.8:score+=7
    elif 4<=row["vol_x"]<=6:score+=10
    if 55<=row["rsi"]<=72:score+=10
    if row["macd_h"]>0 and row["macd_acc"]>0:score+=10
    if 2<=row["ret5"]<=12:score+=5
    if 5<=row["ret20"]<=30:score+=5
    over=[]
    if row["dist20"]>15:score-=18;over.append("距20MA過遠")
    if row["ret5"]>25:score-=12;over.append("5日漲幅過大")
    if row["vol_x"]>6:score-=10;over.append("爆量>6x")
    if row["rsi"]>82:score-=10;over.append("RSI過熱")
    row["score"]=max(0,min(100,score))
    row["overheat_reasons"]=over
    row["category"]="過熱不追" if over else "剛啟動" if row["break20"] and row["dist20"]<=8 and row["ret5"]<=12 else "等回踩" if row["score"]>=60 and row["dist20"]<=12 else "觀察"
    sr=daily_sr(x);row.update(sr)
    row["reasons"]=[t for t,ok in [("均線多頭",row["trend"]),("3日突破",row["break3"]),("20日突破",row["break20"]),(f"量比{row['vol_x']:.1f}x",row["vol_x"]>=1.3),("MACD轉強",row["macd_h"]>0 and row["macd_acc"]>0)] if ok]
    return row

def intraday_sr(x,vwap):
    latest=x.index[-1].date();today=x[x.index.date==latest];prev=x[x.index.date<latest]
    cur=float(today["Close"].iloc[-1]);atr=float(tr(today).rolling(8).mean().iloc[-1]) if len(today)>=8 else cur*.005
    sup,res=pivots(today,lookback=len(today),order=2)
    (sup if vwap<=cur else res).append((vwap,"VWAP"))
    sup.append((float(today["Low"].min()),"今日低"));res.append((float(today["High"].max()),"今日高"))
    if not prev.empty:
        pdte=sorted(set(prev.index.date))[-1];p=prev[prev.index.date==pdte]
        sup.append((float(p["Low"].min()),"前日低"));res.append((float(p["High"].max()),"前日高"))
    return {"support":zone(cur,sup,atr,"support",True),"resistance":zone(cur,res,atr,"resistance",True)}

def intraday_score(x):
    if len(x)<20:return None
    x=x.copy();x.index=pd.to_datetime(x.index)
    latest=x.index[-1].date();today=x[x.index.date==latest];prev=x[x.index.date<latest]
    if len(today)<3:return None
    c=today["Close"];h=today["High"];v=today["Volume"];cur=float(c.iloc[-1])
    typ=(today["High"]+today["Low"]+today["Close"])/3
    vwap=float(((typ*v).cumsum()/v.cumsum().replace(0,np.nan)).iloc[-1])
    p3=h.shift(1).rolling(3).max();p12=h.shift(1).rolling(12).max()
    b3=bool(cur>p3.iloc[-1]) if pd.notna(p3.iloc[-1]) else False
    b12=bool(cur>p12.iloc[-1]) if pd.notna(p12.iloc[-1]) else False
    ma5=c.rolling(5).mean();ma10=c.rolling(10).mean();trend=bool(cur>ma5.iloc[-1]>ma10.iloc[-1]) if pd.notna(ma10.iloc[-1]) else False
    n=len(today);vals=[]
    for d in sorted(set(prev.index.date))[-4:]:
        z=prev[prev.index.date==d]
        if len(z)>=n:vals.append(float(z["Volume"].iloc[:n].sum()))
    pace=float(v.sum()/np.median(vals)) if vals and np.median(vals)>0 else 1.0
    if not prev.empty:
        d=sorted(set(prev.index.date))[-1];pc=float(prev[prev.index.date==d]["Close"].iloc[-1])
    else:pc=float(c.iloc[0])
    ch=(cur/pc-1)*100 if pc else 0
    score=0;reasons=[];over=[]
    if cur>vwap:score+=15;reasons.append("站上VWAP")
    if b3:score+=15;reasons.append("3K突破")
    if b12:score+=12;reasons.append("60分突破")
    if trend:score+=12;reasons.append("5分K短均多頭")
    if 1.5<=pace<3.5:score+=20;reasons.append(f"量速{pace:.1f}x")
    elif 1.2<=pace<1.5:score+=10;reasons.append(f"量速{pace:.1f}x")
    if 1<=ch<=6.5:score+=10
    if ch>=8.5:score-=20;over.append("接近漲停/漲幅過熱")
    vd=(cur/vwap-1)*100 if vwap else 0
    if vd>4.5:score-=12;over.append("離VWAP過遠")
    if pace>5:score-=10;over.append("量速極端")
    score=max(0,min(100,score))
    cat="過熱不追" if over else "剛啟動" if score>=70 and b3 and cur>vwap else "等回踩" if score>=58 else "觀察"
    sr=intraday_sr(x,vwap)
    return {"date":str(latest),"time":x.index[-1].strftime("%H:%M"),"close":cur,"score":score,"category":cat,
            "pace":round(pace,2),"vwap":round(vwap,2),"vwap_dist":round(vd,2),"day_change":round(ch,2),
            "break3":b3,"break12":b12,"trend5":trend,"reasons":reasons,"overheat_reasons":over,**sr}

def add_group(rows):
    df=pd.DataFrame(rows)
    if df.empty:return rows
    hot=df[(df.score>=55)&(df.category!="過熱不追")]
    counts=hot.groupby("industry")["code"].count().to_dict()
    for r in rows:
        n=int(counts.get(r["industry"],0));r["industry_hot_count"]=n
        r["score"]=min(100,round(r["score"]+(10 if n>=3 else 6 if n==2 else 0),1))
    rows.sort(key=lambda r:({"剛啟動":0,"等回踩":1,"觀察":2,"過熱不追":3}.get(r["category"],9),-r["score"]))
    return rows

def dump(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":")),encoding="utf-8")

def main():
    uni=get_universe()
    dump("universe.json",uni[["code","name","industry","market"]].astype(str).to_dict("records"))
    meta=uni.set_index("symbol").to_dict("index")

    # 全市場日K
    all_rows=[];syms=uni["symbol"].tolist()
    for i in range(0,len(syms),100):
        part=syms[i:i+100]
        try:data=download_daily(part,"6mo")
        except Exception as e:print("daily batch",i,e);continue
        for s,x in data.items():
            try:
                d=daily_score(x)
                if not d or d["avg_turnover20"]<30_000_000:continue
                m=meta.get(s,{})
                all_rows.append({"symbol":s,"code":str(m.get("code",s.split(".")[0])),"name":str(m.get("name",s)),
                                 "industry":str(m.get("industry","未分類")),"market":str(m.get("market","")),**d})
            except Exception as e:print("daily stock",s,e)
    all_rows=add_group(all_rows)
    dump("close.json",{"updated_at":datetime.now(TW).isoformat(timespec="seconds"),"rows":all_rows})

    # 固定關注池 + 日K top150
    watch=(ROOT/"config"/"watchlist.txt").read_text(encoding="utf-8").splitlines()
    watch=[x.strip() for x in watch if x.strip() and not x.strip().startswith("#")]
    code_to_sym=dict(zip(uni["code"],uni["symbol"]))
    pool=[code_to_sym[c] for c in watch if c in code_to_sym]
    pool += [r["symbol"] for r in all_rows[:150]]
    pool=list(dict.fromkeys(pool))

    intra=[]
    for i in range(0,len(pool),60):
        part=pool[i:i+60]
        try:data=download_intraday(part)
        except Exception as e:print("intra batch",i,e);continue
        for s,x in data.items():
            try:
                d=intraday_score(x)
                if not d:continue
                m=meta.get(s,{})
                intra.append({"symbol":s,"code":str(m.get("code",s.split(".")[0])),"name":str(m.get("name",s)),
                              "industry":str(m.get("industry","未分類")),"market":str(m.get("market","")),**d})
            except Exception as e:print("intra stock",s,e)
    intra=add_group(intra)
    dump("intraday.json",{"updated_at":datetime.now(TW).isoformat(timespec="seconds"),"rows":intra})
    dump("status.json",{"updated_at":datetime.now(TW).isoformat(timespec="seconds"),"daily_count":len(all_rows),"intraday_count":len(intra),"version":"1.0-free"})
    print("done",len(all_rows),len(intra))

if __name__=="__main__":
    main()
