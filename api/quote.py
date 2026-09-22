import json
import os
import urllib.error
import urllib.parse
import urllib.request

API_ROOT = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/"
MAX_CODES = 5


def _headers(origin="*"):
    return {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Content-Type": "application/json; charset=utf-8",
        "Vary": "Origin",
    }


def _json(handler, status, obj, origin="*"):
    handler.send_response(status)
    for k, v in _headers(origin).items():
        handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def _fetch_one(code, api_key):
    req = urllib.request.Request(
        API_ROOT + urllib.parse.quote(code),
        headers={
            "X-API-KEY": api_key,
            "Accept": "application/json",
            "User-Agent": "DogsonStockRadar/1.3",
        },
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))

    price = data.get("closePrice")
    prev = data.get("previousClose") or data.get("referencePrice")
    change = None
    if price not in (None, 0) and prev not in (None, 0):
        change = (float(price) / float(prev) - 1) * 100

    return {
        "code": str(data.get("symbol") or code),
        "name": data.get("name"),
        "market": data.get("market"),
        "price": price,
        "previousClose": prev,
        "changePct": round(change, 4) if change is not None else None,
        "open": data.get("openPrice"),
        "high": data.get("highPrice"),
        "low": data.get("lowPrice"),
        "avgPrice": data.get("avgPrice"),
        "volume": data.get("total", {}).get("tradeVolume") if isinstance(data.get("total"), dict) else None,
        "time": data.get("closeTime"),
        "source": "Fugle MarketData",
    }


class handler:
    def __init__(self, request, response):
        self.request = request
        self.response = response

    def __call__(self):
        origin = self.request.headers.get("origin", "*")
        if self.request.method == "OPTIONS":
            self.response.status_code = 204
            for k, v in _headers(origin).items():
                self.response.headers[k] = v
            return ""

        api_key = os.environ.get("FUGLE_API_KEY", "").strip()
        if not api_key:
            self.response.status_code = 503
            for k, v in _headers(origin).items():
                self.response.headers[k] = v
            return {"ok": False, "error": "FUGLE_API_KEY is not configured"}

        raw = (self.request.args.get("codes") or "").strip()
        codes = []
        for x in raw.split(","):
            x = x.strip()
            if len(x) == 4 and x.isdigit() and x not in codes:
                codes.append(x)
        codes = codes[:MAX_CODES]
        if not codes:
            self.response.status_code = 400
            for k, v in _headers(origin).items():
                self.response.headers[k] = v
            return {"ok": False, "error": "codes is required"}

        quotes, errors = [], []
        for code in codes:
            try:
                quotes.append(_fetch_one(code, api_key))
            except urllib.error.HTTPError as e:
                errors.append({"code": code, "error": f"HTTP {e.code}"})
            except Exception as e:
                errors.append({"code": code, "error": type(e).__name__})

        self.response.status_code = 200 if quotes else 502
        for k, v in _headers(origin).items():
            self.response.headers[k] = v
        return {"ok": bool(quotes), "quotes": quotes, "errors": errors, "maxCodes": MAX_CODES}
