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
console.log('Broker CSV/TSV import regression PASS: ROC/ISO, multiline header, daytrade, accounts, dedup, preview-only');
