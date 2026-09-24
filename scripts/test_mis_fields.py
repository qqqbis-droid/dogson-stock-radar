#!/usr/bin/env python3
import json,time,requests
CODES=['3189','4707','2308','2330','3044','6274']
S=requests.Session();S.headers.update({'User-Agent':'Mozilla/5.0','Referer':'https://mis.twse.com.tw/stock/index.jsp'})
URL='https://mis.twse.com.tw/stock/api/getStockInfo.jsp'

def probe(channels,label):
    r=S.get(URL,params={'ex_ch':'|'.join(channels),'json':'1','delay':'0','_':str(int(time.time()*1000))},timeout=15)
    r.raise_for_status();arr=r.json().get('msgArray') or []
    print('\n',label,'count',len(arr))
    for x in arr:
        print(json.dumps({k:x.get(k) for k in ['c','n','ex','d','t','z','pz','tv','v','y','o','h','l','b','a','bp','ap','s','ts','tlong']},ensure_ascii=False))

for code in CODES:
    probe([f'tse_{code}.tw',f'otc_{code}.tw'],f'single {code}')
    time.sleep(.25)
probe([f'{m}_{c}.tw' for c in CODES for m in ('tse','otc')],'multi both markets')
