/* Contract tests: isolated SOP2 engine, zero changes to existing scores. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const E=require('../../docs/v2/daytrade-risk-engine-v2.js');
const base={entry:53,stop:52.5,shares:1000,budget:1000,capitalLimit:60000,slippageTicks:1};
function test(name,fn){try{fn();console.log('PASS',name)}catch(e){console.error('FAIL',name);throw e}}
test('stock tick ladder 9/10/50/100/500/1000',()=>{
  assert.deepEqual([9,10,49,50,99,100,499,500,999,1000].map(E.tick),[.01,.05,.05,.1,.1,.5,.5,1,1,5]);
});
test('risk includes fee tax and both-side slippage',()=>{
  const r=E.assess(base);assert.equal(r.ok,true);
  assert.equal(r.priceRisk,500);assert.ok(r.feeTax>0);assert.ok(r.slippageReserve>0);
  assert.equal(r.risk,500+r.feeTax+r.slippageReserve);
  assert.ok(r.capital>53000);
});
test('reject risk budget, capital limit, untradeable odd lots',()=>{
  assert.equal(E.assess({...base,budget:500}).ok,false);
  assert.equal(E.assess({...base,capitalLimit:50000}).ok,false);
  assert.equal(E.assess({...base,shares:100}).ok,false);
});
test('stop must be below entry and prices must use valid exchange ticks',()=>{
  assert.equal(E.assess({...base,stop:53}).ok,false);
  assert.equal(E.assess({...base,stop:53.02}).ok,false);
  assert.equal(E.assess({...base,entry:53.03}).ok,false);
});
test('bad prices, blank inputs and slippage are rejected',()=>{
  assert.equal(E.assess({...base,entry:''}).ok,false);
  assert.equal(E.assess({...base,slippageTicks:-1}).ok,false);
  assert.equal(E.assess({...base,shares:0}).ok,false);
});
test('break-even covers fees and conservative exit slippage',()=>{
  const be=E.breakEven(535,1000,null,1);
  assert.ok(be>537);
  assert.ok(E.netPnl(535,be,1000)>=E.tick(be)*1000);
});
test('one R and two R change protection suggestions but not saved stop',()=>{
  const p1=E.protection(base,54.5,54.5,52.5);
  assert.ok(['CHECK_BREAKEVEN','PROTECT_HALF_PEAK'].includes(p1.stage));
  const p2=E.protection(base,57,57,52.5);
  assert.equal(p2.stage,'PROTECT_HALF_PEAK');
  assert.ok(p2.suggested>=p1.suggested);
  assert.ok(p2.suggested>52.5);
});
test('price at existing stop emits an alert, never an order',()=>{
  const p=E.protection(base,54,52.5,52.5);
  assert.match(p.warning,/防守價/);
  assert.ok(!Object.hasOwn(p,'order'));
});
test('UI has manual price, raise-only stop, local CSV and no broker API',()=>{
  const ui=fs.readFileSync(path.join(__dirname,'../../docs/v2/daytrade-risk-ui-v2.js'),'utf8');
  for(const k of ['MANUAL_PRICE','STOP_RAISED','MANUAL_EXIT','localStorage','slippageTicks','匯出風控紀錄 CSV','next>p.defense','confirm(']){
    assert.ok(ui.includes(k),'missing UI feature: '+k);
  }
  assert.ok(!ui.includes('fetch(')&&!ui.includes('XMLHttpRequest'));
});
test('only daytrade tab shows SOP; no risk evaluator modifies score',()=>{
  const ui=fs.readFileSync(path.join(__dirname,'../../docs/v2/daytrade-risk-ui-v2.js'),'utf8');
  assert.ok(ui.includes('.tab.active[data-view="daytrade"]'));
  assert.ok(!ui.includes('RadarPortfolioStore.importData'));
  const index=fs.readFileSync(path.join(__dirname,'../../docs/v2/index.html'),'utf8');
  assert.ok(index.includes('./daytrade-risk-engine-v2.js?v=20261104sop2'));
  assert.ok(index.includes('./daytrade-risk-ui-v2.js?v=20261104sop2'));
});
console.log('Daytrade SOP 2.0 tests complete');
