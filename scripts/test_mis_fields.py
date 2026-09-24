#!/usr/bin/env python3
import json,time,requests
CODES=['3189','4707','2308','2330','3044','6274']
S=requests.Session();S.headers.update({'User-Agent':'Mozilla/5.0','Referer':'https://mis.twse.com.tw/stock/index.jsp'})
URL='https://mis.twse.com.tw/stock/api/getStockInfo.jsp'
channels=[f'{m}_{c}.tw' for c in CODES for m in ('tse','otc')]
seen={c:[] for c in CODES}
for i in range(12):
    r=S.get(URL,params={'ex_ch':'|'.join(channels),'json':'1','delay':'0','_':str(int(time.time()*1000))},timeout=15)
    r.raise_for_status();arr=r.json().get('msgArray') or []
    row={}
    for x in arr:
        c=str(x.get('c') or '').strip()
        if c in seen:
            row[c]={'t':x.get('t'),'z':x.get('z'),'tv':x.get('tv'),'v':x.get('v'),'b':x.get('b'),'a':x.get('a'),'ex':x.get('ex')}
            try:
                if float(x.get('z'))>0: seen[c].append((x.get('t'),float(x.get('z'))))
            except: pass
    print('sample',i+1,json.dumps(row,ensure_ascii=False))
    time.sleep(.8)
print('CAPTURE_SUMMARY',json.dumps({c:{'ticks':len(v),'last':v[-1] if v else None} for c,v in seen.items()},ensure_ascii=False))
