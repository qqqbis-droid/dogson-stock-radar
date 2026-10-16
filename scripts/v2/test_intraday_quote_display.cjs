#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs');
const code=fs.readFileSync('docs/v2/app.js','utf8');
const a=code.indexOf('function validSessionQuote(');
const b=code.indexOf('\nfunction quoteHtml(',a);
assert(a>=0&&b>a,'The single-card same-session quote fallback must be present.');
const body=code.slice(a,b);
const helpers=new Function('num',body+'\nreturn {validSessionQuote,displayEvidenceRow}')(
 v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v));
const {displayEvidenceRow,validSessionQuote}=helpers;
const day='2026-10-13',build='test-20261013';
const row=(code,quote,confidence=undefined)=>({
 code,as_of:'2026-10-13T11:46:00+08:00',data_confidence:confidence,quote,
 opportunity_rank:1,action_state:'WAIT_TRIGGER',scores:{intraday_momentum_score:68}
});
const summary=new Map([
 ['2855',{...row('2855',{price:58.7,day_change_pct:-1.34,quote_time:'2026-10-13T11:00:00+08:00'},60),build_id:build}],
 ['3008',{...row('3008',{price:7400,day_change_pct:1.02,quote_time:'2026-10-13T11:08:45+08:00'},60),build_id:build}]
]);
for(const code of ['2855','3008']){
 const original=row(code,{price:null,day_change_pct:null});
 const fixed=displayEvidenceRow(original,summary,day,build);
 assert(fixed.quote?.price>0,code+' quote missing');
 assert.equal(fixed.data_confidence,60,code+' confidence missing');
 assert.equal(fixed.opportunity_rank,1,'Ranking must remain untouched');
 assert.equal(fixed.action_state,'WAIT_TRIGGER','No buy/sell verdict change');
 assert.equal(fixed.scores.intraday_momentum_score,68,'Scores must remain the original Engine scores');
 assert.equal(original.quote.price,null,'Fallback may not mutate the model row');
}
const stale=new Map([['2855',{...summary.get('2855'),quote:{price:100,quote_time:'2026-10-12T13:30:00+08:00'}}]]);
assert(!validSessionQuote(stale.get('2855'),day));
assert.equal(displayEvidenceRow(row('2855',{price:null}),stale,day,build).quote.price,null,
 'Previous day prices may not enter today quote cards');
assert.equal(displayEvidenceRow(row('2855',{price:null}),summary,day,'another-build').quote.price,null,
 'Cross-build quote leaks are forbidden');
const old=row('2855',{price:58.1,quote_time:'2026-10-13T10:30:00+08:00'},50);
const fixed=displayEvidenceRow(old,summary,day,build);
assert.equal(fixed.quote.price,58.7,'Choose later same-session trade instead of older one');
assert.equal(fixed.data_confidence,50,'Do not overwrite an existing Engine confidence score');
const quoteHtml=code.slice(code.indexOf('function quoteHtml(d){'),code.indexOf('\nfunction rankText(',code.indexOf('function quoteHtml(d){')));
assert(quoteHtml.includes('成交時間')&&quoteHtml.includes('非逐筆即時'),'Display actual quote clock and its latency nature');
assert(quoteHtml.includes('showPrice?priceFmt(p):"—"'),'Only validated same-day quote is displayed');
const html=fs.readFileSync('docs/v2/index.html','utf8');
assert(html.includes('app.js?v=20261016ignitionrestore1'));
assert(html.includes('quote.css?v=20261013clock1'));
console.log('PASS intraday quote: summary repairs missing index price and confidence, respects Atomic Build/date and Engine scoring, timestamps trade.');
