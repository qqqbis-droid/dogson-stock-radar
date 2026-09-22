const API_ROOT = 'https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/';
const MAX_CODES = 5;

function cors(req, res) {
  res.setHeader('Access-Control-Allow-Origin', req.headers.origin || '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
  res.setHeader('Vary', 'Origin');
}

async function fetchOne(code, apiKey) {
  const r = await fetch(API_ROOT + encodeURIComponent(code), {
    headers: {
      'X-API-KEY': apiKey,
      'Accept': 'application/json',
      'User-Agent': 'DogsonStockRadar/1.3'
    },
    cache: 'no-store'
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const data = await r.json();
  const price = Number(data.closePrice);
  const prev = Number(data.previousClose ?? data.referencePrice);
  const changePct = Number.isFinite(price) && Number.isFinite(prev) && prev !== 0
    ? (price / prev - 1) * 100
    : null;
  return {
    code: String(data.symbol || code),
    name: data.name ?? null,
    market: data.market ?? null,
    price: Number.isFinite(price) ? price : null,
    previousClose: Number.isFinite(prev) ? prev : null,
    changePct: changePct == null ? null : Math.round(changePct * 10000) / 10000,
    open: data.openPrice ?? null,
    high: data.highPrice ?? null,
    low: data.lowPrice ?? null,
    avgPrice: data.avgPrice ?? null,
    volume: data.total?.tradeVolume ?? null,
    time: data.closeTime ?? null,
    source: 'Fugle MarketData'
  };
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') return res.status(405).json({ ok: false, error: 'GET only' });

  const apiKey = String(process.env.FUGLE_API_KEY || '').trim();
  if (!apiKey) return res.status(503).json({ ok: false, error: 'FUGLE_API_KEY is not configured' });

  const raw = Array.isArray(req.query.codes) ? req.query.codes[0] : (req.query.codes || '');
  const codes = [];
  for (const x of String(raw).split(',')) {
    const c = x.trim();
    if (/^\d{4}$/.test(c) && !codes.includes(c)) codes.push(c);
    if (codes.length >= MAX_CODES) break;
  }
  if (!codes.length) return res.status(400).json({ ok: false, error: 'codes is required' });

  const settled = await Promise.allSettled(codes.map(c => fetchOne(c, apiKey)));
  const quotes = [];
  const errors = [];
  settled.forEach((x, i) => {
    if (x.status === 'fulfilled') quotes.push(x.value);
    else errors.push({ code: codes[i], error: x.reason?.message || 'fetch failed' });
  });
  return res.status(quotes.length ? 200 : 502).json({
    ok: quotes.length > 0,
    quotes,
    errors,
    maxCodes: MAX_CODES,
    fetchedAt: Date.now()
  });
}
