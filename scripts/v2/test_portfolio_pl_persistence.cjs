#!/usr/bin/env node
'use strict';
// Regression: 2026-10-15 iPhone card briefly showed money+percentage,
// then the delayed broker-match adapter overwrote the entire <b> with %.
const fs=require('node:fs'),assert=require('node:assert/strict');
const broker=fs.readFileSync('docs/v2/portfolio-broker-match.js','utf8');
const main=fs.readFileSync('docs/v2/portfolio-renderer.js','utf8');
const loader=fs.readFileSync('docs/v2/data-source.js','utf8');
const html=fs.readFileSync('docs/v2/index.html','utf8');
const start=broker.indexOf('function patchSummary(){'),end=broker.indexOf('function patchDetail(){',start);
assert(start>=0&&end>start,'Broker patchSummary source absent');
const fn=broker.slice(start,end);
assert(!/pnl\.textContent\s*=/.test(fn),'Never replace entire P/L node with percentage');
assert(main.includes('class="portfolio-pl-amount"')&&main.includes('class="portfolio-pl-pct"'),'Main renderer must provide independent money and percentage');
assert(main.includes('class="portfolio-pl-summary"'),'Total P/L must remain visible');
assert(loader.includes('portfolio-broker-match.js?v=20261015plpersist3'),'Late adapter must bypass stale iPhone cache');
assert(html.includes('data-source.js?v=20261015plpersist3'));
assert(html.includes('portfolio-renderer.js?v=20261015plpersist3'));

function harness(oldCard=false){
 const amount={textContent:'-$725'},pct={textContent:'-12.00%'};
 const pnl={
  classList:{contains:x=>x==='portfolio-pl-breakdown'},
  querySelector:x=>oldCard?null:x==='.portfolio-pl-amount'?amount:x==='.portfolio-pl-pct'?pct:null,
  replaceChildren:(a,b)=>{pnl.newChildren=[a,b]}
 };
 Object.defineProperty(pnl,'textContent',{set(){throw Error('Destructive percent-only overwrite')},get(){return amount.textContent+pct.textContent}});
 const scores=[{querySelector:()=>({textContent:'5,120'})},{querySelector:()=>pnl}];
 const card={dataset:{portfolioCode:'2383'},querySelectorAll:()=>scores};
 const doc={querySelectorAll:()=>[card],createElement:tag=>({tag,textContent:'',className:''})};
 const $=()=>null;
 const patch=new Function('document','window','numText','estimatePosition','signedMoney','signedPct','findSummary','$',
    fn+';return patchSummary;')(
   doc,{RadarPortfolioStore:{get:()=>({code:'2383',shares:2,avg_cost:5830})}},
   s=>Number(String(s).replace(/[$,+%\s]/g,'').replace(/,/g,'')),
   ()=>({cost:11660,net:10195,pl:-1465,pct:-12.56}),
   v=>(v<0?'-$':'$')+Math.abs(v).toLocaleString('en-US'),
   v=>v.toFixed(2)+'%',()=>null,$
 );
 patch();patch();
 if(oldCard){
  assert.equal(pnl.newChildren?.length,2);
  assert.equal(pnl.newChildren[0].className,'portfolio-pl-amount');
  assert.equal(pnl.newChildren[0].textContent,'-$1,465');
  assert.equal(pnl.newChildren[1].className,'portfolio-pl-pct');
  assert.equal(pnl.newChildren[1].textContent,'-12.56%');
 }else{
  assert.equal(amount.textContent,'-$1,465');
  assert.equal(pct.textContent,'-12.56%');
  assert(!pnl.newChildren,'Stable nodes should not be replaced');
 }
}
harness(false);
harness(true);
console.log('PASS: delayed broker match preserves money and percent over repeat paints, including cached old cards');
