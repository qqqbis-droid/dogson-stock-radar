'use strict';
/* Node regression tests: broker import must be private, preview-only, duplicate-safe. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path');
const script=fs.readFileSync(path.resolve(__dirname,'../../docs/v2/broker-trade-import.js'),'utf8');
let current={transactions:[],meta:{}},writes=0;
const store={
  isTradingDay(d){return /^\d{4}-\d{2}-\d{2}$/.test(d)},
  exportData(){return JSON.parse(JSON.stringify(current))},
  importData(data){
    if(!Array.isArray(data.transactions))throw Error('invalid ledger');
    const bal={};
    const sorted=data.transactions.slice().sort((a,b)=>String(a.trade_date).localeCompare(String(b.trade_date))||String(a.created_at||'').localeCompare(String(b.created_at||'')));
    for(const t of sorted){if(t.daytrade_pair_id)continue;
      bal[t.code]=(bal[t.code]||0)+(t.side==='BUY'?t.shares:-t.shares);
      if(bal[t.code]<0)throw Error('missing historical BUY');
    }
    writes++;current=JSON.parse(JSON.stringify(data));
  }
};
const window={RadarPortfolioStore:store};
const document={readyState:'loading',addEventListener(){}};
vm.runInNewContext(script,{window,document,console,Date,Number,String,Set,Map,Math,TextDecoder});
const parse=window.InukoBrokerTradeImport.parse;
const csv='交易日期,股票代號,股票名稱,買賣別,成交股數,成交價\n2026-11-02,2330,台積電,買進,"1,000",1000\n2026-11-02,2330,台積電,賣出,200,1010\n';
let v=parse(csv);
assert.equal(v.rows.length,2);
assert.equal(v.rejected.length,0);
assert.equal(v.rows[0].trade_date,'2026-11-02');
assert.equal(v.rows[0].shares,1000);
assert.equal(writes,0,'preview may not write');
assert.equal(store.exportData().transactions.length,0);
assert.equal(v.rows[1].side,'SELL');
const roc=parse('下載交易明細\n券商資料\n成交日期\t證券代號\t買賣別\t張數\t成交價\n115/11/02\t2451\t買\t1\t300\n');
assert.equal(roc.rows.length,1,'allow introductory rows / TSV');
assert.equal(roc.rows[0].trade_date,'2026-11-02');
assert.equal(roc.rows[0].shares,1000);
const onepair=parse('交易日期,股票代號,買賣別,成交股數,成交價,當沖\n2026/11/02,2451,買進,1000,300,當沖\n2026/11/02,2451,賣出,1000,305,當沖\n');
assert.equal(onepair.rows.length,2);
assert.ok(onepair.rows.every(x=>x.daytrade_pair_id));
assert.equal(new Set(onepair.rows.map(x=>x.daytrade_pair_id)).size,1);
const broken=parse('交易日期,股票代號,買賣別,成交股數,成交價,當沖\n2026/11/02,2451,買進,1000,300,當沖\n2026/11/02,2451,賣出,500,305,當沖\n');
assert.equal(broken.rows.length,0,'do not silently import unmatched daytrades');
assert.equal(broken.rejected.length,2);
assert.throws(()=>parse('成交日期,股票代號,買賣別,成交股數,成交價,證券帳號\n2026/11/02,2451,買,1000,300,aaa\n2026/11/02,2451,賣,1000,305,bbb\n'),/多個證券帳號/);
assert.equal(writes,0);
current={transactions:v.rows,meta:{}}; // exactly matching existing signatures
assert.equal(parse(csv).rows.length,0,'rerun must not duplicate identical fills');
const duplicated='交易日期,股票代號,買賣別,成交股數,成交價\n2026-11-02,2330,買進,100,1000\n2026-11-02,2330,買進,100,1000\n';
current={transactions:[],meta:{}};
assert.equal(parse(duplicated).rows.length,2,'two identical legitimate fills in one file are preserved');
// Unmarked same-day BUY/SELL MUST be classified explicitly before touching
// an existing swing position. Do not silently decide "daytrade" for the user.
current={transactions:[],meta:{}};writes=0;
const sameDay='成交日期,證券代號,買賣別,成交股數,成交價\n2026-11-02,1234,買進,1000,25\n2026-11-02,1234,賣出,1000,26\n';
let pending=parse(sameDay);
assert.equal(pending.possiblePairs.length,1,'one same-day candidate');
assert.equal(window.InukoBrokerTradeImport.assess(pending).safeRows.length,0,'unknown trade type blocked');
const pairKey=pending.possiblePairs[0].key;
const classified=parse(sameDay,{[pairKey]:'DAYTRADE'});
assert.equal(window.InukoBrokerTradeImport.assess(classified).safeRows.length,2);
assert.ok(classified.rows.every(t=>t.daytrade_pair_id));
assert.equal(window.InukoBrokerTradeImport.merge(classified),2);
assert.equal(writes,1);
assert.equal(store.exportData().transactions.length,2);
assert.equal(parse(sameDay,{[pairKey]:'DAYTRADE'}).rows.length,0,'daytrade dedup does not depend on chosen bucket');
const swing=parse(sameDay,{[pairKey]:'SWING'});
assert.equal(swing.rows.length,0,'cannot re-add existing daytrade as a new swing trade');
// Time-less regular fills must sort BUY before SELL, not by the hashed id.
current={transactions:[],meta:{}};writes=0;
let ordinary=parse(sameDay,{[pairKey]:'SWING'});
assert.equal(window.InukoBrokerTradeImport.assess(ordinary).safeRows.length,2);
assert.notEqual(ordinary.rows[0].created_at,ordinary.rows[1].created_at);
assert.equal(window.InukoBrokerTradeImport.merge(ordinary),2);
assert.equal(writes,1);
assert.equal(store.exportData().transactions.length,2);
// Partial history: isolate unsupported earlier sells, keep independent buys and
// never invent an opening transaction or discard valid independently funded rows.
current={transactions:[],meta:{}};writes=0;
const partial='成交日期,證券代號,買賣別,成交股數,成交價\n2026-10-20,9876,賣出,20,121\n2026-10-20,1234,買進,1000,25\n2026-10-20,1234,賣出,1000,26\n2026-11-02,1234,買進,10,30\n';
const all=parse(partial);
const key=all.possiblePairs[0].key;
const review=parse(partial,{[key]:'DAYTRADE'});
const assessed=window.InukoBrokerTradeImport.assess(review);
assert.equal(assessed.blocked.length,1,'unfunded prior sale should be flagged before confirmation');
assert.equal(assessed.blocked[0].code,'9876');
assert.equal(assessed.safeRows.length,3,'funded same-day pair plus separate lot');
assert.equal(window.InukoBrokerTradeImport.merge(review),3);
assert.equal(store.exportData().transactions.length,3);
assert.ok(store.exportData().transactions.every(t=>t.code!=='9876'));
assert.equal(window.InukoBrokerTradeImport.assess(parse(partial,{[key]:'DAYTRADE'})).safeRows.length,0,'safe subset is deduplicated');
// A 1,000 share daytrade must not pollute a later 30+15 swing lot.
current={transactions:[],meta:{}};writes=0;
const mixed='成交日期,證券代號,買賣別,成交股數,成交價\n2026-10-21,4567,買進,1000,94.6\n2026-10-21,4567,賣出,1000,96.5\n2026-10-21,4567,買進,30,98.1\n2026-10-22,4567,買進,15,106\n2026-10-29,4567,賣出,45,104.5\n';
const mixedKey=parse(mixed).possiblePairs[0].key;
const mixedReport=parse(mixed,{[mixedKey]:'DAYTRADE'});
assert.equal(window.InukoBrokerTradeImport.assess(mixedReport).safeRows.length,5);
assert.equal(window.InukoBrokerTradeImport.merge(mixedReport),5);
const ordinaryPositions=store.exportData().transactions.filter(t=>!t.daytrade_pair_id);
assert.equal(ordinaryPositions.filter(t=>t.side==='BUY').reduce((n,t)=>n+t.shares,0),45);
assert.equal(ordinaryPositions.filter(t=>t.side==='SELL').reduce((n,t)=>n+t.shares,0),45);
console.log('Broker CSV/TSV import regression PASS: ROC/ISO, daytrade explicit, chronological same-day fills, safe partial import, dedup, preview-only');
