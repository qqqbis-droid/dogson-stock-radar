#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const src=fs.readFileSync('docs/v2/portfolio-renderer.js','utf8');
function block(start,end){
 const a=src.indexOf(start),b=src.indexOf(end,a);
 assert(a>=0&&b>a,'Missing portfolio function: '+start);
 return src.slice(a,b);
}
const source=block('async function allMarketQuotes(m){','function ownedDecision(')
 +'\n'+block('async function data(positions=[]','function localFirst(');
assert(src.includes('new AbortController')||src.includes('new AbortController()'),'Network requests must be abortable');
assert(!source.includes('set(m,\'decision_close_detail\')'),'Should not wait for full close detail');
assert(!source.includes('set(m,\'stock_detail_close\')'),'Should not wait for full stock evidence');
assert(!source.includes('set(m,\'zone_close\')'),'Should not wait for every price zone');
let requested=[];
const manifest=async()=>({active_build_id:'test-build',trade_date:'2026-10-12',datasets:{decision_close_index:{as_of:'2026-10-12T13:30:00+08:00'}}});
async function j(url,ms){
 requested.push({url,ms});
 if(url.includes('portfolio_market_quotes.json'))return {quotes:{
   '1802':{close:63.5,trade_date:'2026-10-12',source:'TWSE'},
   '6271':{close:247.5,trade_date:'2026-10-12',source:'TWSE'},
   '9904':{close:30,trade_date:'2026-10-08',source:'outdated'}
 }};
 const code=url.split('/').pop().split('.')[0];
 if(code==='6271')throw new Error('simulate an unavailable stock shard');
 return{build_id:'test-build',view:'close',code,as_of:'2026-10-12T13:30:00+08:00',
  decision:{code,quote:{price:code==='1802'?63.5:18},scores:{swing_quality_score:70}},
  evidence:{chip_date:'2026-10-12'},zones:[]};
}
const funcs=new Function('manifest','j','pn','console',source+'\nreturn {data,allMarketQuotes};')(
 manifest,j,v=>v==null?null:Number(v),{warn(){}}
);
(async()=>{
 const progress=[],positions=[{code:'1802'},{code:'6271'},{code:'9904'}];
 const result=await funcs.data(positions,x=>progress.push({
  phase:x.phase,analyzed:x.loaded,quotes:Object.keys(x.quotes),details:Object.keys(x.detail),
  partial:x.partialSources
 }));
 assert(progress.length>=3,'There must be at least quote, shard and final paint stages');
 assert.equal(progress[0].analyzed,0,'Quotes must paint before any stock analysis');
 assert(progress[0].quotes.includes('1802'));
 assert(progress[0].quotes.includes('6271'));
 assert(!progress[0].quotes.includes('9904'),'Stale close price must never be treated as current');
 assert.equal(result.loaded,3);
 assert(result.detail['1802'],'One failed stock shard must not hide another stock');
 assert(!result.detail['6271'],'No fabricated stock analysis after a missing shard');
 assert(result.partialSources.some(x=>x.includes('6271')),'Report the failed stock source');
 assert(requested.every(x=>x.ms>=1000&&x.ms<=10000),'All fetches should have bounded timeouts');
 assert(requested.every(x=>x.url.includes('stock-shards/close/')||x.url.includes('portfolio_market_quotes.json')));
 console.log('PASS: progressive official quotes first, source dates validated, independent 3-stock details and deadline bounds');
})().catch(e=>{console.error(e);process.exitCode=1});
