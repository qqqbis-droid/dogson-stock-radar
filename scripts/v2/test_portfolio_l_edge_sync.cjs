#!/usr/bin/env node
'use strict';
// Holding-risk L0..L4 owns each portfolio card's border, NOT the stock
// discovery/action state or P&L. Also check iPhone inline paint explicitly.
const fs=require('node:fs'),assert=require('node:assert/strict');
const read=p=>fs.readFileSync(p,'utf8');
const intel=read('docs/v2/inuko-portfolio-intel-v2.js');
const base=read('docs/v2/portfolio-renderer.js');
const html=read('docs/v2/index.html');
const start=intel.indexOf('const PORTFOLIO_LEVEL_EDGES=');
const stop=intel.indexOf('function levelZoneDistance(',start);
assert(start>=0&&stop>start,'Canonical portfolio edge helper missing');
const paint=new Function(intel.slice(start,stop)+'\nreturn paintPortfolioLevel;')();
const palette=['#1f5a46','#4b82ad','#d39a2c','#d97725','#b42318'];
function makeCard(){
  const values=new Set(['card','portfolio-card','risk']);
  const attrs={};const css={};
  const card={
    dataset:attrs,style:{setProperty:(k,v,priority)=>{css[k]=[v,priority]}},
    classList:{
      add:(...a)=>a.forEach(v=>values.add(v)),
      remove:(...a)=>a.forEach(v=>values.delete(v)),
      contains:k=>values.has(k)
    }
  };
  return{card,attrs,css,values};
}
for(let level=0;level<=4;level++){
 const {card,attrs,css,values}=makeCard();
 paint(card,level);
 assert.equal(attrs.portfolioLevel,'L'+level);
 assert(card.classList.contains('l'+level));
 assert(!values.has('risk')&&!values.has('wait')&&!values.has('go'),'Previous trading-color class must be gone');
 assert.deepEqual(css['border-left'],['6px solid '+palette[level],'important']);
 assert.deepEqual(css['border-inline-start'],['6px solid '+palette[level],'important']);
 assert(values.has('portfolio-card'),'Original holdings card retained');
}
{
 const x=makeCard();paint(x.card,2);paint(x.card,3);
 assert(!x.values.has('l2')&&x.values.has('l3'),'Changing L level must repaint the edge');
 assert.equal(x.attrs.portfolioLevel,'L3');
}
assert(intel.includes('const level=levelOf(x);paintPortfolioLevel(card,level)'), 'Border must derive from SAME levelOf used by holding review');
assert(intel.includes('const level=levelOf(x),meta=LEVEL_META[level]'),'Holding review badge must share the same canonical grading');
assert(base.includes("cardTone='neutral'"),'Initial stock-discovery trading risk must not color holdings card');
assert(base.includes('style="border-left:6px solid #8c9590"'),'Incomplete loading state must be explicitly neutral');
assert(!base.includes("cardTone=p.reason_status==='INVALID'||risk?"),'Portfolio card cannot use mixed signal colors');
assert(html.includes('inuko-portfolio-intel-v2.js?v=20261013l-edge1'),'iPhone must fetch the patched holding model');
assert(html.includes('portfolio-renderer.js?v=20261013l-edge1'),'iPhone must fetch neutral pending cards');
console.log('PASS: five L0-L4 holding border colors, shared grading, safe unknown, iOS inline painting, no trade-data writes');
