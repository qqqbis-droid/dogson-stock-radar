#!/usr/bin/env node
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const code=fs.readFileSync('docs/v2/portfolio-renderer.js','utf8');
const html=fs.readFileSync('docs/v2/index.html','utf8');
const start=code.indexOf('function positionCalc('),stop=code.indexOf('function sysRisk(',start);
assert(start>0&&stop>start,'Position P/L calculator unavailable');
const calc=new Function('pn','currentPrice','window',code.slice(start,stop)+'\nreturn positionCalc;')(
 v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v),
 (d,e)=>Number(d?.quote?.price||e?.close)||null,
 {InukoFeeEngine:{estimate:({shares,price})=>({net:shares*price-10,commission:5,tax:5})}}
);
let holding={code:'5302',shares:500,avg_cost:10.05};
const current=calc(holding,{quote:{price:9.5}},null);
assert.equal(current.cost,5025);
assert.equal(current.value,4750);
assert.equal(current.pl,-285);
assert(Math.abs(current.pct-(-285/5025*100))<1e-8);
const unknown=calc(holding,{quote:null,reference_quote:{trade_date:'2026-10-14',close:9.67}},null);
assert.equal(unknown.pl,null,'Old-day close must not be promoted into current P/L');
assert.equal(unknown.pct,null,'Old-day close cannot create current unrealized percent');
assert(code.includes('signedMoney(c.pl)')&&code.includes('signedPct(c.pct)'),'Each holding needs amount and %');
assert(code.includes("signedPct(totalPl/totalCost*100)"),'Portfolio totals need amount and %');
assert(code.includes('reference_quote?.close>0')&&code.includes('僅供參考，不計入損益'),'Prior price must be dated and non-valuation');
assert(code.includes('Object.entries(source?.reference_quotes||{})'),'Reference-only quotes must be processed');
assert(html.includes('portfolio-renderer.js?v=20261015plpersist3'),'iPhone should load fresh revision');
console.log('PASS: fee-adjusted individual and total unrealized amount + percent; prior OTC prices remain non-valuating');
