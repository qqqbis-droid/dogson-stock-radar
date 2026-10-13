#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync('docs/v2/intraday-quote-recovery-v2.js','utf8');
const idx=fs.readFileSync('docs/v2/index.html','utf8');
const script={quoteFromShard:null,fill:null};
const ctx={
 document:{querySelector:()=>null,addEventListener:()=>{}},
 window:{},console,fetch:()=>Promise.reject(new Error('Do not fetch during unit test')),
 AbortController,setTimeout,clearTimeout,Date,Number,String,encodeURIComponent
};
vm.runInNewContext(src,ctx);
const api=ctx.window.RadarIntradayQuoteRecovery;
assert(api?.quoteFromShard&&api?.fill,'Quote recovery must expose tested helper');
const b='verified-build-1013',date='2026-10-13';
const expected={code:'2855',view:'intraday',build:b,date};
const good={code:'2855',view:'intraday',build_id:b,as_of:date+'T11:43:00+08:00',
 decision:{quote:{price:58.7,day_change_pct:-1.34,quote_time:date+'T11:00:00+08:00'},
 data_confidence:60},evidence:{quote_date:date,quote_volume_lots:2902,quote_source:'TWSE MIS official snapshot'}};
const yes=api.quoteFromShard(good,expected);
assert.equal(yes.price,58.7);assert.equal(yes.confidence,60);assert.equal(yes.change,-1.34);
assert.equal(api.quoteFromShard({...good,build_id:'old-build'},expected),null);
assert.equal(api.quoteFromShard({...good,as_of:'2026-10-12T13:30:00+08:00'},expected),null);
assert.equal(api.quoteFromShard({...good,view:'close'},expected),null);
const stale=api.quoteFromShard({...good,decision:{...good.decision,quote:{...good.decision.quote,quote_time:'2026-10-12T13:30:00+08:00'}}},expected);
assert.equal(stale.price,null,'Never relabel yesterday trade as today');
assert.equal(stale.change,null,'Never relabel yesterday change as today');
const blank=api.quoteFromShard({...good,decision:{...good.decision,quote:{price:null}},evidence:{quote_date:'2026-10-12',close:58.7}},expected);
assert.equal(blank.price,null);
const sameDayEvidence=api.quoteFromShard({...good,decision:{...good.decision,quote:{price:null}},evidence:{quote_date:date,quote_price_validated:true,close:58.5,day_change:-1.5}},expected);
assert.equal(sameDayEvidence.price,58.5);
assert(idx.includes('intraday-quote-recovery-v2.js?v=20261013recovery1'),'Asset version not in production index');
assert(!src.includes('renderCards(')&&!src.includes('innerHTML='),'Rescue may not replace ranked-card DOM during search');
console.log('PASS: Intraday quote recovery exact stock/build/day, old-source rejection, source confidence only and no card rerenders');
