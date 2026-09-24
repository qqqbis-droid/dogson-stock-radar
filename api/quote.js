const MAX_CODES = 5;

function cors(req, res) {
  res.setHeader('Access-Control-Allow-Origin', req.headers.origin || '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
  res.setHeader('Vary', 'Origin');
}

function finite(v) {
  if (v == null || v === '' || v === '-' || v === '--') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function firstBook(v) {
  const x = String(v || '').split('_')[0];
  return finite(x);
}

function normalizeEpoch(v) {
  const n = finite(v);
  if (n == null) return Date.now();
  if (n > 1e14) return Math.round(n / 1000);
  if (n < 1e12) return n * 1000;
  return n;
}

function tradeEpoch(dateText, timeText, fallback = null) {
  const d = String(dateText || '').trim();
  const t = String(timeText || '').trim();
  if (!/^\d{8}$/.test(d) || !/^\d{1,2}:\d{2}:\d{2}$/.test(t)) return fallback;
  const iso = `${d.slice(0,4)}-${d.slice(4,6)}-${d.slice(6,8)}T${t.padStart(8,'0')}+08:00`;
  const ms = Date.parse(iso);
  return Number.isFinite(ms) ? ms : fallback;
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') return res.status(405).json({ ok: false, error: 'GET only' });

  const raw = Array.isArray(req.query.codes) ? req.query.codes[0] : (req.query.codes || '');
  const codes = [];
  for (const x of String(raw).split(',')) {
    const c = x.trim();
    if (/^\d{4}$/.test(c) && !codes.includes(c)) codes.push(c);
    if (codes.length >= MAX_CODES) break;
  }
  if (!codes.length) return res.status(400).json({ ok: false, error: 'codes is required' });

  const exCh = codes.flatMap(c => [`tse_${c}.tw`, `otc_${c}.tw`]).join('|');
  const url = `https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=${encodeURIComponent(exCh)}&json=1&delay=0&_=${Date.now()}`;

  try {
    const r = await fetch(url, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json,text/plain,*/*',
        'User-Agent': 'Mozilla/5.0 DogsonStockRadar/1.5',
        'Referer': 'https://mis.twse.com.tw/stock/index.jsp'
      }
    });
    if (!r.ok) throw new Error(`TWSE MIS HTTP ${r.status}`);
    const data = await r.json();
    const arr = Array.isArray(data.msgArray) ? data.msgArray : [];

    const byCode = new Map();
    for (const x of arr) {
      const code = String(x.c || '').trim();
      if (!/^\d{4}$/.test(code) || !codes.includes(code)) continue;
      const price = finite(x.z);
      const prev = finite(x.y);
      const hasTrade = price != null && price > 0;
      const snapshotTime = normalizeEpoch(x.tlong);
      const latestTradeTime = hasTrade ? tradeEpoch(x.d, x.t, snapshotTime) : null;
      const changePct = hasTrade && prev != null && prev > 0 ? (price / prev - 1) * 100 : null;
      const q = {
        code,
        name: x.n || null,
        market: x.ex === 'otc' ? '上櫃' : x.ex === 'tse' ? '上市' : (x.ex || null),
        price: hasTrade ? price : null,
        hasTrade,
        previousClose: prev,
        changePct: changePct == null ? null : Math.round(changePct * 10000) / 10000,
        bid1: firstBook(x.b),
        ask1: firstBook(x.a),
        open: finite(x.o),
        high: finite(x.h),
        low: finite(x.l),
        volume: finite(x.v),
        time: latestTradeTime,
        tradeTimeText: hasTrade ? (x.t || null) : null,
        tradeDate: hasTrade ? (x.d || null) : null,
        snapshotTime,
        source: hasTrade ? 'TWSE MIS latest matched trade' : 'TWSE MIS orderbook snapshot'
      };
      const old = byCode.get(code);
      if (!old || (x.ex === 'tse' && old.market !== '上市') || (hasTrade && !old.hasTrade)) byCode.set(code, q);
    }

    const quotes = codes.map(c => byCode.get(c)).filter(Boolean);
    const errors = codes.filter(c => !byCode.has(c)).map(code => ({ code, error: 'no MIS snapshot' }));
    return res.status(quotes.length ? 200 : 502).json({
      ok: quotes.length > 0,
      quotes,
      errors,
      maxCodes: MAX_CODES,
      fetchedAt: Date.now(),
      source: 'TWSE MIS'
    });
  } catch (e) {
    return res.status(502).json({ ok: false, error: e?.message || 'quote fetch failed' });
  }
}
