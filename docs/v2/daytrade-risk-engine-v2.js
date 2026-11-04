/* 犬子選骨室｜當沖風控 SOP 2.0 (independent manual simulator).
   Deliberately does not modify ranking, stock score, orders or holdings.
   Quotes and fills are user-entered, never labelled as real-time broker data. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.InukoDaytradeRiskV2=api;
})(typeof window!=='undefined'?window:null,function(){
'use strict';
const DEFAULTS=Object.freeze({commission_rate:0.001425,minimum_commission_twd:20,daytrade_sell_tax_rate:0.0015});
const number=v=>(v==null||String(v).trim()===''?NaN:Number(v));
const money=n=>Math.round(n);
function tick(price){
  const p=number(price);
  if(!Number.isFinite(p)||p<=0)return NaN;
  if(p<10)return 0.01;
  if(p<50)return 0.05;
  if(p<100)return 0.1;
  if(p<500)return 0.5;
  if(p<1000)return 1;
  return 5;
}
function floorTick(price){
  if(!Number.isFinite(number(price))||number(price)<=0)return NaN;
  const t=tick(price);return Math.round(Math.floor((price+1e-8)/t)*t*100)/100;
}
function ceilTick(price){
  if(!Number.isFinite(number(price))||number(price)<=0)return NaN;
  let p=number(price),t=tick(p);let v=Math.round(Math.ceil((p-1e-8)/t)*t*100)/100;
  if(v<p-1e-8){p+=t;v=Math.round(Math.ceil((p-1e-8)/tick(p))*tick(p)*100)/100;}
  return v;
}
function validTick(price){
  const p=number(price), t=tick(p);
  return Number.isFinite(t)&&Math.abs(p/t-Math.round(p/t))<1e-6;
}
function profile(input){
  const p=input||{};
  const pick=(key,def)=>Number.isFinite(number(p[key]))?number(p[key]):def;
  const out={
    commission_rate:pick('commission_rate',DEFAULTS.commission_rate),
    minimum_commission_twd:pick('minimum_commission_twd',DEFAULTS.minimum_commission_twd),
    daytrade_sell_tax_rate:pick('daytrade_sell_tax_rate',DEFAULTS.daytrade_sell_tax_rate)
  };
  if(out.commission_rate<0||out.commission_rate>.05||out.minimum_commission_twd<0||out.daytrade_sell_tax_rate<0||out.daytrade_sell_tax_rate>.05)throw Error('費率設定不合理');
  return out;
}
function commission(gross,p){return Math.max(money(gross*p.commission_rate),money(p.minimum_commission_twd));}
function netPnl(entry,sell,shares,feeProfile){
  const e=number(entry),s=number(sell),q=number(shares),p=profile(feeProfile);
  if(!(e>0&&s>0&&q>0))return NaN;
  const buyFee=commission(e*q,p),sellFee=commission(s*q,p),tax=money(s*q*p.daytrade_sell_tax_rate);
  return money((s-e)*q-buyFee-sellFee-tax);
}
function breakEven(entry,shares,feeProfile,slippageTicks=1){
  const e=number(entry),q=number(shares);
  if(!(e>0&&q>0))return NaN;
  let candidate=ceilTick(e);
  for(let n=0;n<1000;n++){
    const buffer=tick(candidate)*Math.max(0,number(slippageTicks)||0)*q;
    if(netPnl(e,candidate,q,feeProfile)>=buffer)return candidate;
    candidate=ceilTick(candidate+tick(candidate)+1e-7);
  }
  return NaN;
}
function assess(input){
  const a=input||{},entry=number(a.entry),stop=number(a.stop),shares=number(a.shares);
  const budget=number(a.budget),capitalLimit=number(a.capitalLimit),slippageTicks=number(a.slippageTicks==null?1:a.slippageTicks);
  const p=profile(a.fees);
  const errors=[];
  if(!(entry>0&&stop>0&&stop<entry))errors.push('停損必須低於買進價，且兩者都要有效');
  if(!Number.isInteger(shares)||shares<1000||shares%1000!==0)errors.push('現股當沖以整張 1,000 股為單位；零股不可當沖');
  if(!(budget>0))errors.push('請輸入有效單筆風險預算');
  if(!(capitalLimit>0))errors.push('請輸入有效買進資金上限');
  if(!Number.isInteger(slippageTicks)||slippageTicks<0||slippageTicks>20)errors.push('滑價預留請設定 0～20 檔');
  if(entry>0&&!validTick(entry))errors.push('買進價不符合一般台股跳動單位');
  if(stop>0&&!validTick(stop))errors.push('停損價不符合一般台股跳動單位');
  if(errors.length)return{ok:false,errors,capital:null,risk:null,netProfit:null,breakEven:null};
  const buyFee=commission(entry*shares,p),sellFee=commission(stop*shares,p),tax=money(stop*shares*p.daytrade_sell_tax_rate);
  const priceRisk=money((entry-stop)*shares);
  const feeTax=buyFee+sellFee+tax;
  const slip=money((tick(entry)+tick(stop))*slippageTicks*shares);
  const risk=priceRisk+feeTax+slip;
  const capital=money(entry*shares+buyFee);
  if(risk>budget)errors.push('含費稅與預留滑價風險超過單筆預算：禁止新開倉');
  if(capital>capitalLimit)errors.push('預估買進金額超過單筆資金上限：禁止新開倉');
  const be=breakEven(entry,shares,p,slippageTicks);
  return{ok:!errors.length,errors,entry,stop,shares,budget,capitalLimit,slippageTicks,
    capital,risk,priceRisk,feeTax,slippageReserve:slip,breakEven:be,
    riskRewardBasis:'estimated net downside incl. fees/tax/two-side slippage reserve'};
}
function protection(input,peak,last,heldStop){
  const a=assess(input);
  if(a.risk==null)return{stage:'INVALID',suggested:null,peakR:null,currentR:null,warning:'輸入不完整'};
  const p=profile(input.fees),peakPrice=number(peak),lastPrice=number(last),floor=number(heldStop);
  if(!(peakPrice>=a.entry&&lastPrice>0))return{stage:'UNKNOWN',suggested:null,peakR:null,currentR:null,warning:'未輸入有效人工價格'};
  const peakNet=netPnl(a.entry,peakPrice,a.shares,p),currentNet=netPnl(a.entry,lastPrice,a.shares,p);
  const peakR=peakNet/a.risk,currentR=currentNet/a.risk;
  let suggested=null,stage='HOLD_INITIAL';
  if(peakR>=1){suggested=a.breakEven;stage='CHECK_BREAKEVEN';}
  if(peakR>=2){
    const halfGross=a.entry+(peakPrice-a.entry)/2;
    suggested=Math.max(a.breakEven,floorTick(halfGross));
    stage='PROTECT_HALF_PEAK';
  }
  // Suggestion is informational. The user's saved hard stop never auto-moves.
  const warning=(Number.isFinite(floor)&&lastPrice<=floor)?'價格已到達或跌破手動防守價，請立即依券商實際成交與原計畫處理'
    :(suggested!=null&&lastPrice<suggested)?'已跌破獲利保護參考價；不能保證以參考價成交':'';
  return{stage,suggested,peakR,currentR,peakNet,currentNet,warning};
}
return{DEFAULTS,tick,floorTick,ceilTick,validTick,profile,commission,netPnl,breakEven,assess,protection};
});