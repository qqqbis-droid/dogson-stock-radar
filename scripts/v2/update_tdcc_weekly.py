#!/usr/bin/env python3
"""Free TDCC weekly ownership concentration builder (no brokerage data).
Data.gov.tw dataset 11452, Government Open Data License v1.
The official CSV is the authority; optional archived original-week CSVs
are used ONLY to seed earlier weeks on first deployment. Fail closed.
"""
from __future__ import annotations
import argparse,csv,io,json,os,re,sys,time,urllib.request
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OFFICIAL_URLS=(
 "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5",
 "https://smart.tdcc.com.tw/opendata/getOD.ashx?id=1-5",
)
PUBLIC_ARCHIVE="https://api.github.com/repos/wirelessr/tdcc-opendata-archive/contents/snapshots/"
MAX_CONTENT=23_000_000
HEADERS=("資料日期","證券代號","持股分級","人數","股數","占集保庫存數比例%")
TZ=ZoneInfo("Asia/Taipei")

def fetch(url, timeout=28):
 req=urllib.request.Request(url,headers={
   "User-Agent":"Inuko-Lab-TDCC-OpenData/1.0 (noncommercial public open-data attribution)",
   "Accept":"text/csv,application/json,*/*","Cache-Control":"no-cache"
 })
 with urllib.request.urlopen(req,timeout=timeout) as resp:
  body=resp.read(MAX_CONTENT+1)
 if len(body)>MAX_CONTENT:raise ValueError("TDCC response too large")
 if len(body)<2000:raise ValueError("TDCC response too small")
 return body

def decoded(body):
 for enc in ("utf-8-sig","cp950","big5"):
  try:
   text=body.decode(enc)
   if "資料日期" in text[:500] and "證券代號" in text[:500]:return text
  except UnicodeError:pass
 raise ValueError("TDCC CSV missing official headers or encoding unsupported")

def date(raw):
 s=re.sub(r"\D","",str(raw))
 if len(s)!=8:raise ValueError("Unexpected TDCC date format")
 return datetime.strptime(s,"%Y%m%d").date().isoformat()

def numeric(raw,is_percent=False):
 s=str(raw or "").strip().replace(",","").replace("%","").replace("％","")
 if not s:return None
 n=float(s)
 if not (0<=n<=(100.01 if is_percent else 1e12)):
  raise ValueError("TDCC field outside expected range")
 return n

def parse_official_csv(body):
 text=decoded(body)
 rows=csv.DictReader(io.StringIO(text))
 fields={str(x).strip().replace("\ufeff",""):x for x in (rows.fieldnames or [])}
 if any(x not in fields for x in HEADERS):raise ValueError("TDCC CSV changed column schema")
 by_code=defaultdict(dict);week_dates=set();read=0
 for row in rows:
  if not row:continue
  try:
   source_date=date(row[fields["資料日期"]])
   code=str(row[fields["證券代號"]] or "").strip().upper()
   level=int(row[fields["持股分級"]])
   if not re.fullmatch(r"[A-Z0-9-]{4,10}",code) or level not in range(1,18):continue
   share=numeric(row[fields["占集保庫存數比例%"]],True)
   holders=numeric(row[fields["人數"]])
   if share is None:continue
   key=code+"|"+source_date
   if level in by_code[key]:raise ValueError("Duplicate TDCC stock/date/level")
   by_code[key][level]=(share,holders or 0)
   week_dates.add(source_date);read+=1
  except (KeyError,TypeError) as exc:raise ValueError("Malformed TDCC row") from exc
 if len(by_code)<800 or read<10000:raise ValueError("TDCC coverage unusually small; skip publication")
 if len(week_dates)>4:raise ValueError("Unexpected many TDCC dates in latest CSV")
 output={}
 for key,lv in by_code.items():
  if 15 not in lv or 17 not in lv:continue
  if not all(k in lv for k in range(12,16)):continue
  big400=round(sum(lv[k][0] for k in range(12,16)),4)
  big1000=round(lv[15][0],4)
  if big400>100.05 or big1000>100.05:continue
  code,d=key.split("|")
  output[key]={"code":code,"date":d,"big400":big400,"big1000":big1000,
               "total_holders":int(lv[17][1]),"large_holders":int(sum(lv[k][1] for k in range(12,16)))}
 if len({r["code"] for r in output.values()})<800:raise ValueError("Too few complete TDCC distributions")
 return output

def archive_backfill(official_date, max_weeks=7):
 """Optional original official CSV archive; cannot overwrite official latest."""
 year=official_date[:4];pairs={}
 try:
  req=urllib.request.Request(PUBLIC_ARCHIVE+year,headers={"User-Agent":"Inuko-Lab-OpenData/1.0","Accept":"application/vnd.github+json"})
  with urllib.request.urlopen(req,timeout=15) as r:entries=json.load(r)
  for item in entries:
   n=str(item.get("name") or "")
   if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.csv",n) and n[:-4]<official_date:
    pairs[n[:-4]]=item.get("download_url")
 except Exception as e:
  print("Archive listing unavailable; proceed using official current week:",str(e)[:160])
  return []
 gathered=[]
 for d,url in sorted(pairs.items(),reverse=True)[:max_weeks]:
  if not url:continue
  try:
   data=parse_official_csv(fetch(url,timeout=21))
   if d not in {r["date"] for r in data.values()}:raise ValueError("Archive filename date disagrees with TDCC source")
   gathered.append((d,data))
   print("Archive historical TDCC week",d,len(data))
  except Exception as exc:print("Historical TDCC week unavailable",d,str(exc)[:140])
 return gathered

def build(output, fetcher=fetch, backup=True):
 now=datetime.now(TZ)
 existing={}
 if output.exists():
  try:existing=json.loads(output.read_text(encoding="utf-8"))
  except Exception as exc:print("Previous weekly json invalid, will recreate",str(exc)[:100])
 prior=existing.get("stocks") or {}
 official_error=[]
 freshest=None
 for url in OFFICIAL_URLS:
  try:
   body=fetcher(url)
   records=parse_official_csv(body)
   current=max(r["date"] for r in records.values())
   if current>now.date().isoformat():raise ValueError("Future-dated TDCC source blocked")
   if current<(now.date()-timedelta(days=20)).isoformat():raise ValueError("TDCC official source older than 20 days")
   freshest=(current,records,url);break
  except Exception as exc:official_error.append(url+": "+str(exc)[:140])
 if not freshest:raise RuntimeError("No verified official TDCC current feed: "+" | ".join(official_error))
 d,rec,url=freshest
 stock_records=defaultdict(dict)
 for code,weeks in prior.items():
  for w in weeks:
   try:
    wdate=date(w["date"])
    if wdate<=d and wdate>=(now.date()-timedelta(days=125)).isoformat():
     stock_records[code][wdate]={"date":wdate,"big400":float(w["big400"]),"big1000":float(w["big1000"]),
                                  "total_holders":int(w.get("total_holders") or 0),
                                  "large_holders":int(w.get("large_holders") or 0)}
   except (ValueError,KeyError,TypeError):pass
 if backup and not prior:
  for _,historical in archive_backfill(d):
   for r in historical.values():
    stock_records[r["code"]][r["date"]]={k:r[k] for k in ("date","big400","big1000","total_holders","large_holders")}
 for r in rec.values():
  stock_records[r["code"]][r["date"]]={k:r[k] for k in ("date","big400","big1000","total_holders","large_holders")}
 stocks={code:sorted(w.values(),key=lambda x:x["date"],reverse=True)[:12]
         for code,w in stock_records.items() if w}
 if len(stocks)<800:raise ValueError("Insufficient TDCC coverage for publication")
 weeks=sorted({w["date"] for series in stocks.values() for w in series},reverse=True)
 result={"schema":"tdcc-weekly-ownership-v1","source":"臺灣集中保管結算所／政府資料開放平臺 11452",
         "license":"政府資料開放授權條款第1版",
         "source_url":url,"archive_attribution":"wirelessr/tdcc-opendata-archive (historical official CSV copies)" if backup else "",
         "latest_week":d,"weeks":weeks[:12],"stock_count":len(stocks),
         "coverage":"Official last-week distribution; not daily brokerage branch concentration",
         "stocks":stocks}
 output.parent.mkdir(parents=True,exist_ok=True)
 serialized=json.dumps(result,ensure_ascii=False,separators=(",",":"),sort_keys=True)+"\n"
 if output.exists() and output.read_text(encoding="utf-8")==serialized:
  print("No new TDCC week; unchanged",d);return False
 output.write_text(serialized,encoding="utf-8")
 print("TDCC verified weekly concentration",d,"stocks",len(stocks),"weeks",len(weeks))
 return True

if __name__=="__main__":
 a=argparse.ArgumentParser()
 a.add_argument("--out",default="docs/v2/data/tdcc_weekly_concentration.json")
 a.add_argument("--no-backfill",action="store_true")
 p=a.parse_args()
 try:build(Path(p.out),backup=not p.no_backfill)
 except Exception as exc:
  print("TDCC weekly auto update safely blocked:",exc,file=sys.stderr)
  sys.exit(1)
