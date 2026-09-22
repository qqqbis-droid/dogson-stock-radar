import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

API_ROOT = "https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/"
MAX_CODES = 5


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


class handler(BaseHTTPRequestHandler):
    def _origin(self):
        return self.headers.get("Origin") or "*"

    def _send(self, status, obj=None):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", self._origin())
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Vary", "Origin")
        if obj is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        if obj is not None:
            self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        api_key = os.environ.get("FUGLE_API_KEY", "").strip()
        if not api_key:
            self._send(503, {"ok": False, "error": "FUGLE_API_KEY is not configured"})
            return

        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        raw = (qs.get("codes", [""])[0] or "").strip()
        codes = []
        for x in raw.split(","):
            x = x.strip()
            if len(x) == 4 and x.isdigit() and x not in codes:
                codes.append(x)
        codes = codes[:MAX_CODES]
        if not codes:
            self._send(400, {"ok": False, "error": "codes is required"})
            return

        quotes, errors = [], []
        for code in codes:
            try:
                quotes.append(_fetch_one(code, api_key))
            except urllib.error.HTTPError as e:
                errors.append({"code": code, "error": f"HTTP {e.code}"})
            except Exception as e:
                errors.append({"code": code, "error": type(e).__name__})

        self._send(200 if quotes else 502, {
            "ok": bool(quotes),
            "quotes": quotes,
            "errors": errors,
            "maxCodes": MAX_CODES,
        })
