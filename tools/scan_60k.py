#!/usr/bin/env python3
import csv
import json
import math
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

TWSE_URL = 'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'
TPEX_URL = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes'
YAHOO_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=60m&includePrePost=false&events=div%2Csplits'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36'
TZ = timezone(timedelta(hours=8))


def get_json(url, timeout=20, retries=4):
    last = None
    for i in range(retries):
        try:
            req = Request(url, headers={'User-Agent': UA, 'Accept': 'application/json,text/plain,*/*'})
            with urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8'))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep((0.8 * (2 ** i)) + random.random() * 0.8)
    raise last


def num(s):
    if s is None:
        return None
    try:
        return float(str(s).replace(',', '').strip())
    except Exception:
        return None


def load_universe(min_shares=300_000):
    rows = []
    twse = get_json(TWSE_URL)
    for x in twse:
        code = str(x.get('Code', '')).strip()
        if not (len(code) == 4 and code.isdigit() and int(code) >= 1000):
            continue
        vol = num(x.get('TradeVolume')) or 0
        close = num(x.get('ClosingPrice'))
        if close is None or vol < min_shares:
            continue
        rows.append({'code': code, 'name': str(x.get('Name','')).strip(), 'market':'TWSE', 'suffix':'.TW', 'day_volume': int(vol), 'day_close': close})

    tpex = get_json(TPEX_URL)
    for x in tpex:
        code = str(x.get('SecuritiesCompanyCode', x.get('Code',''))).strip()
        if not (len(code) == 4 and code.isdigit() and int(code) >= 1000):
            continue
        vol = num(x.get('TradingShares', x.get('TradeVolume')) ) or 0
        close = num(x.get('Close', x.get('ClosingPrice')))
        if close is None or vol < min_shares:
            continue
        name = str(x.get('CompanyName', x.get('SecuritiesCompanyName', x.get('Name','')))).strip()
        rows.append({'code': code, 'name': name, 'market':'TPEx', 'suffix':'.TWO', 'day_volume': int(vol), 'day_close': close})

    # dedupe by code (should not overlap, but be safe)
    out = {}
    for r in rows:
        out[r['code']] = r
    return list(out.values())


def sma(vals, n):
    if len(vals) < n:
        return None
    return sum(vals[-n:]) / n


def scan_one(item):
    symbol = item['code'] + item['suffix']
    try:
        data = get_json(YAHOO_URL.format(symbol=symbol), timeout=18, retries=3)
        result = data.get('chart', {}).get('result') or []
        if not result:
            return None, 'no-result'
        r = result[0]
        ts = r.get('timestamp') or []
        quote = ((r.get('indicators') or {}).get('quote') or [{}])[0]
        closes = quote.get('close') or []
        volumes = quote.get('volume') or []
        bars = []
        for t, c, v in zip(ts, closes, volumes):
            if c is None:
                continue
            dt = datetime.fromtimestamp(t, TZ)
            # keep Taiwan regular session only, Mon-Fri. Yahoo can sometimes include odd stamps.
            if dt.weekday() >= 5:
                continue
            if not (8 <= dt.hour <= 14):
                continue
            bars.append((dt, float(c), float(v or 0)))
        if len(bars) < 61:
            return None, 'too-few-bars'
        vals = [b[1] for b in bars]
        ma20 = sum(vals[-20:]) / 20
        ma60 = sum(vals[-60:]) / 60
        prev20 = sum(vals[-21:-1]) / 20
        prev60 = sum(vals[-61:-1]) / 60
        dist_pct = (ma20 / ma60 - 1) * 100 if ma60 else None
        cross_now = prev20 <= prev60 and ma20 > ma60

        # how many bars ago did the most recent cross occur (0=current, 1=previous completed 60m bar ...)
        cross_age = None
        max_back = min(10, len(vals)-61)
        for age in range(0, max_back + 1):
            end = len(vals) - age
            cur20 = sum(vals[end-20:end]) / 20
            cur60 = sum(vals[end-60:end]) / 60
            p20 = sum(vals[end-21:end-1]) / 20
            p60 = sum(vals[end-61:end-1]) / 60
            if p20 <= p60 and cur20 > cur60:
                cross_age = age
                break

        last_dt, last_close, last_vol = bars[-1]
        ret = dict(item)
        ret.update({
            'symbol': symbol,
            'last_bar': last_dt.isoformat(),
            'last_close_60m': round(last_close, 4),
            'ma20_60m': round(ma20, 4),
            'ma60_60m': round(ma60, 4),
            'ma_gap_pct': round(dist_pct, 4),
            'cross_now': cross_now,
            'cross_age_bars': cross_age,
            'bars': len(bars),
        })
        return ret, None
    except Exception as e:
        return None, type(e).__name__


def main():
    min_shares = int(sys.argv[1]) if len(sys.argv) > 1 else 300_000
    universe = load_universe(min_shares=min_shares)
    print(f'UNIVERSE {len(universe)} stocks, min daily shares={min_shares}', flush=True)

    results, errors = [], {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(scan_one, x): x for x in universe}
        done = 0
        for fut in as_completed(futs):
            r, err = fut.result()
            done += 1
            if r:
                results.append(r)
            else:
                errors[err] = errors.get(err, 0) + 1
            if done % 100 == 0:
                print(f'PROGRESS {done}/{len(universe)}', flush=True)

    exact = [r for r in results if r['cross_now']]
    recent3 = [r for r in results if r['cross_age_bars'] is not None and r['cross_age_bars'] <= 3]
    exact.sort(key=lambda r: (-r['day_volume'], abs(r['ma_gap_pct'])))
    recent3.sort(key=lambda r: (r['cross_age_bars'], -r['day_volume']))

    with open('scan_60k_results.json','w',encoding='utf-8') as f:
        json.dump({'generated_at': datetime.now(TZ).isoformat(), 'min_shares': min_shares, 'universe': len(universe), 'scanned': len(results), 'errors': errors, 'exact': exact, 'recent3': recent3}, f, ensure_ascii=False, indent=2)
    with open('scan_60k_exact.csv','w',encoding='utf-8-sig',newline='') as f:
        w = csv.DictWriter(f, fieldnames=['code','name','market','day_close','day_volume','last_bar','last_close_60m','ma20_60m','ma60_60m','ma_gap_pct','cross_age_bars'])
        w.writeheader()
        for r in exact:
            w.writerow({k:r.get(k) for k in w.fieldnames})

    print('=== SCAN_SUMMARY ===')
    print(json.dumps({'universe':len(universe),'scanned':len(results),'errors':errors,'exact_count':len(exact),'recent3_count':len(recent3)}, ensure_ascii=False))
    print('=== EXACT_CROSS_NOW ===')
    for r in exact:
        print(f"{r['code']}\t{r['name']}\t{r['market']}\tclose={r['last_close_60m']}\tMA20={r['ma20_60m']}\tMA60={r['ma60_60m']}\tgap={r['ma_gap_pct']}%\tdayVol={r['day_volume']}\tbar={r['last_bar']}")
    print('=== RECENT_CROSS_WITHIN_3_BARS ===')
    for r in recent3:
        print(f"age={r['cross_age_bars']}\t{r['code']}\t{r['name']}\t{r['market']}\tclose={r['last_close_60m']}\tMA20={r['ma20_60m']}\tMA60={r['ma60_60m']}\tgap={r['ma_gap_pct']}%\tdayVol={r['day_volume']}")


if __name__ == '__main__':
    main()
