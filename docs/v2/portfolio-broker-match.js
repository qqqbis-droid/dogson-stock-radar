(()=>{
'use strict';
if(window.__INUKO_BROKER_MATCH_V1__)return;
window.__INUKO_BROKER_MATCH_V1__=true;

const $=s=>document.querySelector(s);
const money=v=>`$${Math.round(Number(v)||0).toLocaleString('zh-TW')}`;
const signedMoney=v=>`${Number(v)>0?'+':''}${money(v)}`;
const signedPct=v=>`${Number(v)>0?'+':''}${Number(v||0).toLocaleString('zh-TW',{minimumFractionDigits:2,maximumFractionDigits:2})}%`;
const numText=s=>Number(String(s||'').replace(/[$,+%\s]/g,'').replace(/,/g,''));
const floorCharge=v=>Math.max(0,Math.floor((Number(v)||0)+1e-9));
let patched=false;
let observer=null;
let timer=null;

function feeProfile(){
  return window.RadarPortfolioStore?.feeProfile?.()||window.InukoFeeEngine?.profile?.()||{commission_rate:.001425,minimum_commission_twd:20,odd_lot_minimum_commission_twd:1,sell_tax_rate:.003,daytrade_sell_tax_rate:.0015};
}
function isDaytradeTx(t){return /DAYTRADE/i.test(String(t?.source||''))}
function commissionFor(gross,shares,p=feeProfile()){
  if(!(gross>0)||!(Number(p.commission_rate)>0))return 0;
  const minFee=Number(shares)<1000?Number(p.odd_lot_minimum_commission_twd||0):Number(p.minimum_commission_twd||0);
  return Math.max(floorCharge(gross*Number(p.commission_rate||0)),floorCharge(minFee));
}
function estimateTx(t,p=feeProfile()){
  const shares=Number(t?.shares)||0,price=Number(t?.price)||0,gross=shares*price,side=String(t?.side||'').toUpperCase();
  const commission=commissionFor(gross,shares,p);
  const taxRate=side==='SELL'?(isDaytradeTx(t)?Number(p.daytrade_sell_tax_rate||0):Number(p.sell_tax_rate||0)):0;
  const tax=side==='SELL'?floorCharge(gross*taxRate):0;
  const net=side==='BUY'?gross+commission:gross-commission-tax;
  return{gross,commission,tax,net,daytrade:isDaytradeTx(t)};
}
function aggregate(data,code){
  const c=String(code||'').toUpperCase();
  const txs=(data?.transactions||[]).filter(t=>String(t.code||'').toUpperCase()===c).slice().sort((a,b)=>String(a.trade_date||'').localeCompare(String(b.trade_date||''))||String(a.created_at||'').localeCompare(String(b.created_at||''))||String(a.id||'').localeCompare(String(b.id||'')));
  let shares=0,avg=0,realized=0,buyValue=0,sellValue=0,buyFees=0,sellFees=0,sellTax=0,cycle=0,lastBuy=null,lastSell=null;
  for(const t of txs){
    const q=Number(t.shares)||0,fees=estimateTx(t);
    if(String(t.side||'').toUpperCase()==='BUY'){
      if(shares===0)cycle+=1;
      const previousCost=avg*shares;
      avg=(previousCost+fees.net)/(shares+q);
      shares+=q;buyValue+=fees.gross;buyFees+=fees.commission;lastBuy={...t,...fees};
    }else{
      if(q>shares)throw new Error(`${c} 在 ${t.trade_date||'未填日期'} 的減碼超過當時持股`);
      realized+=fees.net-(avg*q);shares-=q;sellValue+=fees.gross;sellFees+=fees.commission;sellTax+=fees.tax;lastSell={...t,...fees};if(shares===0)avg=0;
    }
  }
  const m=data?.meta?.[c]||{},firstBuy=txs.find(t=>String(t.side||'').toUpperCase()==='BUY');
  return{code:c,name:m.name||lastBuy?.name||firstBuy?.name||'',shares,avg_cost:shares>0?avg:0,entry_date:firstBuy?.trade_date||'',entry_reason:firstBuy?.reason||'',hold_reason:m.hold_reason||'',reason_status:m.reason_status||'VALID',validation_condition:m.validation_condition||'',failure_condition:m.failure_condition||'',strategy:m.strategy||'',note:m.note||'',realized_pl:realized,buy_value:buyValue,sell_value:sellValue,buy_fees:buyFees,sell_fees:sellFees,sell_tax:sellTax,total_fees:buyFees+sellFees+sellTax,transaction_count:txs.length,cycle_count:cycle,last_buy:lastBuy,last_sell:lastSell,closed:shares===0&&txs.length>0,created_at:firstBuy?.created_at||'',updated_at:m.updated_at||data?.updated_at||new Date().toISOString()};
}
function estimatePosition(p,price){
  const px=Number(price),shares=Number(p?.shares)||0,cost=Number(p?.avg_cost||0)*shares;
  if(!Number.isFinite(px)||px<=0||shares<=0)return{price:px,cost,gross:null,net:null,commission:null,tax:null,pl:null,pct:null};
  const exit=estimateTx({side:'SELL',shares,price:px,source:'ESTIMATED_EXIT'});
  const pl=exit.net-cost,pct=cost>0?pl/cost*100:null;
  return{price:px,cost,gross:exit.gross,net:exit.net,commission:exit.commission,tax:exit.tax,pl,pct};
}
function patchStore(){
  const s=window.RadarPortfolioStore;if(!s||patched)return false;
  const raw=()=>s.exportData?.()||{transactions:[],meta:{}};
  const codes=data=>[...new Set((data?.transactions||[]).map(t=>String(t.code||'').toUpperCase()).filter(Boolean))];
  s.get=code=>{const p=aggregate(raw(),code);return p.transaction_count?p:null};
  s.listAll=()=>codes(raw()).map(c=>aggregate(raw(),c)).filter(p=>p.transaction_count).sort((a,b)=>a.code.localeCompare(b.code));
  s.list=()=>s.listAll().filter(p=>p.shares>0);
  s.history=code=>(raw().transactions||[]).filter(t=>String(t.code||'').toUpperCase()===String(code||'').toUpperCase()).map(t=>({...t,...estimateTx(t)}));
  s.estimateFees=t=>estimateTx(t);
  patched=true;
  if(window.InukoFeeEngine)window.InukoFeeEngine.estimate=estimateTx;
  document.dispatchEvent(new CustomEvent('radar:portfolio-changed',{detail:{brokerMatch:true,count:s.list().length}}));
  return true;
}
function findSummary(label){return [...document.querySelectorAll('#portfolioSummary>div')].find(x=>(x.querySelector('span')?.textContent||'').trim()===label)}
function patchSummary(){
  const s=window.RadarPortfolioStore;if(!s)return;
  const cards=[...document.querySelectorAll('.portfolio-card[data-portfolio-code]')];if(!cards.length)return;
  let totalCost=0,totalNet=0,known=0;
  for(const card of cards){
    const code=card.dataset.portfolioCode,p=s.get?.(code),scores=card.querySelectorAll('.score-row .score');if(!p||!scores.length)continue;
    const px=numText(scores[0]?.querySelector('b')?.textContent);if(!(px>0))continue;
    const est=estimatePosition(p,px);totalCost+=est.cost||0;totalNet+=est.net||0;known++;
    const pnl=scores[1]?.querySelector('b');if(pnl&&est.pct!=null&&pnl.textContent!==signedPct(est.pct))pnl.textContent=signedPct(est.pct);
  }
  if(!known)return;
  const cost=findSummary('成本合計')?.querySelector('b'),pl=findSummary('估計損益')?.querySelector('b');
  if(cost&&cost.textContent!==money(totalCost))cost.textContent=money(totalCost);
  const netPl=totalNet-totalCost;if(pl&&pl.textContent!==signedMoney(netPl))pl.textContent=signedMoney(netPl);
  const sum=$('#portfolioSummary');if(sum&&!$('#inukoEstimatedExitNote')){
    const note=document.createElement('div');note.id='inukoEstimatedExitNote';note.style.cssText='grid-column:1/-1;background:transparent;padding:2px 4px 0;text-align:left;font-size:.66rem;color:#74817b';note.textContent='估計損益已預扣若現在賣出的手續費與交易稅；月退回饋不先計入。';sum.appendChild(note);
  }
}
function patchDetail(){
  const dialog=$('#portfolioDetailDialog');if(!dialog?.open)return;
  const title=$('#portfolioDetailTitle')?.textContent||'',code=(title.match(/\b\d{4}\b/)||[])[0],p=window.RadarPortfolioStore?.get?.(code);if(!p)return;
  const cells=[...dialog.querySelectorAll('.portfolio-detail-grid>div')],priceCell=cells.find(x=>(x.querySelector('span')?.textContent||'').trim()==='現價'),plCell=cells.find(x=>(x.querySelector('span')?.textContent||'').trim()==='估計損益');
  const px=numText(priceCell?.querySelector('b')?.textContent);if(!(px>0)||!plCell)return;
  const est=estimatePosition(p,px),b=plCell.querySelector('b'),text=`${signedMoney(est.pl)} · ${signedPct(est.pct)}`;if(b&&b.textContent!==text)b.textContent=text;
}
function schedule(){if(timer)clearTimeout(timer);timer=setTimeout(()=>{patchSummary();patchDetail()},30)}
function boot(){
  let tries=0;const start=()=>{if(patchStore()){schedule();return}if(++tries<30)setTimeout(start,100)};start();
  document.addEventListener('radar:portfolio-changed',schedule);document.addEventListener('radar:view-rendered',schedule);document.addEventListener('click',()=>setTimeout(schedule,80),true);
  observer=new MutationObserver(schedule);const root=$('#portfolioPanel');if(root)observer.observe(root,{childList:true,subtree:true,characterData:true});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
window.InukoBrokerFeeEngine={estimate:estimateTx,estimatePosition,aggregate};
})();