(function inukoWeeklyReview(){
'use strict';
if(window.__INUKO_WEEKLY_REVIEW__)return;
window.__INUKO_WEEKLY_REVIEW__=true;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>Number(v||0).toLocaleString('zh-TW',{maximumFractionDigits:0,minimumFractionDigits:0});
const today=()=>new Date(Date.now()+8*3600000).toISOString().slice(0,10);
const dateShift=(day,offset)=>new Date(Date.parse(day+'T00:00:00Z')+offset*86400000).toISOString().slice(0,10);
let period='this',timer=null;
function dates(which=period){
  const d=today(),dow=new Date(d+'T00:00:00Z').getUTCDay(),monday=dateShift(d,-((dow+6)%7)+(which==='last'?-7:0));
  return{from:monday,to:dateShift(monday,6)};
}
function compute(transactions,from,to,estimate){
  const txs=(transactions||[]).slice().sort((a,b)=>String(a.trade_date||'').localeCompare(String(b.trade_date||''))||String(a.created_at||'').localeCompare(String(b.created_at||''))||String(a.id||'').localeCompare(String(b.id||'')));
  const pairs=new Map();
  for(const t of txs)if(t.daytrade_pair_id){const k=t.daytrade_pair_id;if(!pairs.has(k))pairs.set(k,{});pairs.get(k)[t.side]=t}
  const book=new Map(),rows=[];
  let net=0,daytradeNet=0,swingNet=0,exits=0,wins=0,followed=0,violated=0,unreviewed=0;
  const fee=t=>estimate?estimate(t):{net:t.side==='BUY'?t.shares*t.price:t.shares*t.price};
  function record(t,type,pnl,reason,entryReason){
    if(String(t.trade_date)<from||String(t.trade_date)>to)return;
    const state=t.discipline||'UNREVIEWED';
    rows.push({id:t.id,code:t.code,name:t.name||'',date:t.trade_date,side:type,shares:t.shares,price:t.price,pnl,reason:reason||'',entryReason:entryReason||'',note:t.note||'',state});
    if(state==='FOLLOWED')followed++;else if(state==='VIOLATED')violated++;else unreviewed++;
    if(pnl!=null){net+=pnl;exits++;if(pnl>0)wins++;if(type==='當沖')daytradeNet+=pnl;else swingNet+=pnl;}
  }
  for(const t of txs){
    const code=String(t.code||'');
    if(t.daytrade_pair_id){
      if(t.side==='BUY')continue;
      const b=pairs.get(t.daytrade_pair_id)?.BUY;
      if(!b)continue;
      record({...t,discipline:t.discipline==='UNREVIEWED'?b.discipline:t.discipline},'當沖',fee(t).net-fee(b).net,t.reason,b.reason);
      continue;
    }
    if(!book.has(code))book.set(code,{shares:0,avg:0,entry:''});
    const b=book.get(code),n=Number(t.shares),f=fee(t);
    if(t.side==='BUY'){
      if(b.shares===0)b.entry=t.reason||'';
      b.avg=(b.avg*b.shares+f.net)/(b.shares+n);
      b.shares+=n;
      record(t,'買進',null,t.reason,b.entry);
    }else{
      if(n>b.shares)continue;
      const pnl=f.net-b.avg*n;
      b.shares-=n;
      const reason=b.entry;
      if(b.shares===0){b.avg=0;b.entry=''}
      record(t,'賣出',pnl,t.reason,reason);
    }
  }
  rows.sort((a,b)=>b.date.localeCompare(a.date)||a.code.localeCompare(b.code));
  return{from,to,rows,net,daytradeNet,swingNet,exits,wins,followed,violated,unreviewed,entries:rows.filter(x=>x.side==='買進').length,feesIncluded:Boolean(estimate)};
}
function style(){
  if(document.getElementById('inukoWeeklyReviewStyle'))return;
  const s=document.createElement('style');s.id='inukoWeeklyReviewStyle';
  s.textContent='.inuko-weekly{border:1px solid var(--line);border-radius:14px;background:var(--card);margin:10px 0;overflow:hidden}.inuko-weekly>summary{cursor:pointer;display:flex;align-items:center;justify-content:space-between;padding:12px;font-weight:850;gap:8px}.inuko-weekly-body{padding:0 12px 12px}.inuko-weekly select{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:7px;border-radius:9px}.inuko-weekly-stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin:10px 0}.inuko-weekly-stats>div{border:1px solid var(--line);border-radius:10px;background:var(--soft);padding:8px}.inuko-weekly-stats span{display:block;font-size:.67rem;color:var(--muted)}.inuko-weekly-stats b{display:block;margin-top:3px;font-size:.88rem}.inuko-weekly-row{border-top:1px solid var(--line);padding:11px 2px;font-size:.72rem;line-height:1.6}.inuko-weekly-row strong{font-size:.78rem}.inuko-weekly-row .note{color:var(--muted)}.inuko-weekly-row label{display:flex;align-items:center;gap:8px;margin-top:4px;flex-wrap:wrap}.inuko-weekly-row select{font-size:.7rem}.inuko-weekly-foot{font-size:.68rem;color:var(--muted);line-height:1.5}';
  document.head.appendChild(s);
}
function render(){
  const panel=document.getElementById('portfolioPanel'),summary=document.getElementById('portfolioSummary'),store=window.RadarPortfolioStore;
  if(!panel||!summary||!store||panel.hidden)return;
  style();
  let root=document.getElementById('inukoWeeklyReview');
  if(!root){root=document.createElement('details');root.id='inukoWeeklyReview';root.className='inuko-weekly';root.innerHTML='<summary>📒 每週實際進出場復盤 <span style="font-size:.68rem;color:var(--muted)">展開查看</span></summary><div class="inuko-weekly-body" id="inukoWeeklyBody"></div>';summary.insertAdjacentElement('afterend',root);}
  const win=dates(),transactions=store.exportData?.()?.transactions||[],fee=window.InukoFeeEngine?.estimate||null;
  const result=compute(transactions,win.from,win.to,fee),body=document.getElementById('inukoWeeklyBody');
  if(!body)return;
  const statusOptions=[['UNREVIEWED','待復盤'],['FOLLOWED','✅ 有遵守'],['VIOLATED','⚠️ 未遵守']];
  const box=(title,value)=>`<div><span>${esc(title)}</span><b>${esc(value)}</b></div>`;
  body.innerHTML=`<label>區間 <select id="inukoReviewPeriod"><option value="this" ${period==='this'?'selected':''}>本週</option><option value="last" ${period==='last'?'selected':''}>上週</option></select></label><div class="inuko-weekly-foot">${esc(win.from)}～${esc(win.to)}（台灣時間）</div><div class="inuko-weekly-stats">${box('實際買進筆數',String(result.entries))}${box('已實現出場筆數',String(result.exits))}${box('波段已實現',`$${money(result.swingNet)}`)}${box('當沖已實現',`$${money(result.daytradeNet)}`)}${box('合計已實現',`$${money(result.net)}`)}${box('出場獲利筆數',result.exits?`${result.wins}/${result.exits}（${(result.wins/result.exits*100).toFixed(0)}%）`:'—')}${box('遵守計畫 / 未遵守',`${result.followed} / ${result.violated}`)}${box('待復盤筆數',String(result.unreviewed))}</div><div class="inuko-weekly-foot">僅統計實際成交；當沖已完成的一買一賣算一筆出場。${result.feesIncluded?'損益依目前費率試算，券商對帳單仍為準。':'費率尚未載入，暫為未扣費損益。'} 勝率以已實現賣出筆數為分母，不是全部持股勝率。</div>${result.rows.length?result.rows.map(t=>`<div class="inuko-weekly-row"><strong>${esc(t.date)} · ${esc(t.code)} ${esc(t.name)} · ${esc(t.side)}</strong>　${esc(t.shares)} 股 × ${esc(t.price)}${t.pnl!=null?` · 已實現 ${t.pnl>=0?'+':''}$${money(t.pnl)}`:''}<div><b>進場核心：</b>${esc(t.entryReason||'尚未記錄')}</div><div><b>本筆理由：</b>${esc(t.reason||'尚未記錄')}</div><div class="note"><b>當時技術／籌碼／市場：</b>${esc(t.note||'尚未記錄')}</div><label>交易紀律 <select data-inuko-discipline="${esc(t.id)}">${statusOptions.map(([value,label])=>`<option value="${value}" ${t.state===value?'selected':''}>${label}</option>`).join('')}</select></label></div>`).join(''):'<p class="inuko-weekly-foot">這個區間沒有實際成交記錄。</p>'}`;
}
function schedule(){clearTimeout(timer);timer=setTimeout(render,180)}
document.addEventListener('change',event=>{
  if(event.target?.id==='inukoReviewPeriod'){period=event.target.value==='last'?'last':'this';render();return}
  const id=event.target?.dataset?.inukoDiscipline;
  if(id)try{window.RadarPortfolioStore?.updateTransactionDiscipline?.(id,event.target.value);schedule()}catch(e){alert(e.message||'紀律更新失敗')}
});
document.addEventListener('radar:portfolio-cards-ready',()=>schedule(100));document.addEventListener('radar:portfolio-changed',schedule);
document.addEventListener('radar:view-rendered',schedule);
document.addEventListener('inuko:fee-profile-changed',schedule);
document.addEventListener('click',e=>{if(e.target?.closest?.('.tab[data-view="portfolio"]'))schedule()},true);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule,{once:true});else schedule();
window.InukoPortfolioReview={summarize:compute,range:dates};
})();
