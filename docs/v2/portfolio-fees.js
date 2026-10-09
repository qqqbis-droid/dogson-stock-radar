(()=>{
'use strict';
if(window.__INUKO_PORTFOLIO_FEES_V1__)return;
window.__INUKO_PORTFOLIO_FEES_V1__=true;

const BASE_COMMISSION_RATE=0.001425;
const DEFAULT_PROFILE={commission_rate:BASE_COMMISSION_RATE,minimum_commission_twd:20,odd_lot_minimum_commission_twd:1,sell_tax_rate:0.003,daytrade_sell_tax_rate:0.0015};
const ACCOUNT_KEY='inuko.portfolio.cloud.account';
const LOCAL_PREFIX='inuko.fee.profile.v1:';
const CONFIG=()=>window.INUKO_CLOUD_CONFIG||{};
let profile={...DEFAULT_PROFILE};
let profileAccount='device';
let lastRemoteAccount='';
let wrapped=false;
let observer=null;

const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const clamp=(v,min,max)=>Math.min(max,Math.max(min,v));
const money=v=>`$${Math.round(Number(v)||0).toLocaleString('zh-TW')}`;
const pct=v=>`${(Number(v||0)*100).toLocaleString('zh-TW',{maximumFractionDigits:4})}%`;
const currentAccount=()=>localStorage.getItem(ACCOUNT_KEY)||'device';
const localKey=id=>LOCAL_PREFIX+(id||'device');

function normalizeProfile(x={}){
  const pick=(k,d,min=0,max=1)=>{const v=n(x[k]);return v==null?d:clamp(v,min,max)};
  return{
    commission_rate:pick('commission_rate',DEFAULT_PROFILE.commission_rate,0,0.05),
    minimum_commission_twd:pick('minimum_commission_twd',DEFAULT_PROFILE.minimum_commission_twd,0,10000),
    odd_lot_minimum_commission_twd:pick('odd_lot_minimum_commission_twd',DEFAULT_PROFILE.odd_lot_minimum_commission_twd,0,10000),
    sell_tax_rate:pick('sell_tax_rate',DEFAULT_PROFILE.sell_tax_rate,0,0.05),
    daytrade_sell_tax_rate:pick('daytrade_sell_tax_rate',DEFAULT_PROFILE.daytrade_sell_tax_rate,0,0.05)
  };
}
function readLocal(id=currentAccount()){
  try{const raw=localStorage.getItem(localKey(id));return raw?normalizeProfile(JSON.parse(raw)):null}catch{return null}
}
function writeLocal(id,p){try{localStorage.setItem(localKey(id),JSON.stringify(normalizeProfile(p)))}catch{}}
function discountFold(p=profile){return BASE_COMMISSION_RATE>0?p.commission_rate/BASE_COMMISSION_RATE*10:10}
function roundCharge(v){return Math.max(0,Math.round((Number(v)||0)+Number.EPSILON))}
function commissionFor(gross,shares,p=profile){
  if(!(gross>0)||!(p.commission_rate>0))return 0;
  const minFee=Number(shares)<1000?p.odd_lot_minimum_commission_twd:p.minimum_commission_twd;
  return Math.max(roundCharge(gross*p.commission_rate),roundCharge(minFee));
}
function isDaytradeTx(t){return /DAYTRADE/i.test(String(t?.source||''))}
function taxFor(gross,t,p=profile){
  if(String(t?.side||'').toUpperCase()!=='SELL')return 0;
  const rate=isDaytradeTx(t)?p.daytrade_sell_tax_rate:p.sell_tax_rate;
  return roundCharge(gross*rate);
}
function estimateTx(t,p=profile){
  const shares=Number(t?.shares)||0,price=Number(t?.price)||0,gross=shares*price,commission=commissionFor(gross,shares,p),tax=taxFor(gross,t,p),side=String(t?.side||'').toUpperCase();
  const net=side==='BUY'?gross+commission:gross-commission-tax;
  return{gross,commission,tax,net,daytrade:isDaytradeTx(t)};
}
function feeAggregate(data,code){
  const c=String(code||'').toUpperCase(),txs=(data?.transactions||[]).filter(t=>t.code===c).slice().sort((a,b)=>String(a.trade_date||'').localeCompare(String(b.trade_date||''))||String(a.created_at||'').localeCompare(String(b.created_at||''))||String(a.id||'').localeCompare(String(b.id||'')));
  let shares=0,avg=0,swingRealized=0,daytradeRealized=0,buyValue=0,sellValue=0,buyFees=0,sellFees=0,sellTax=0,cycle=0,lastBuy=null,lastSell=null,daytradeCount=0;
  const pairs=new Map();
  for(const t of txs)if(t.daytrade_pair_id){const id=t.daytrade_pair_id;if(!pairs.has(id))pairs.set(id,{});pairs.get(id)[t.side]=t}
  for(const [id,pair] of pairs){
    const b=pair.BUY,s=pair.SELL;
    if(!b||!s||b.shares!==s.shares||b.trade_date!==s.trade_date)throw new Error('當沖買賣資料不完整：'+id);
    const bf=estimateTx(b),sf=estimateTx(s);
    daytradeRealized+=sf.net-bf.net;daytradeCount++;
    buyValue+=bf.gross;sellValue+=sf.gross;buyFees+=bf.commission;sellFees+=sf.commission;sellTax+=sf.tax;
  }
  for(const t of txs){
    if(t.daytrade_pair_id)continue;
    const q=Number(t.shares),fees=estimateTx(t);
    if(t.side==='BUY'){
      if(shares===0)cycle++;
      avg=(avg*shares+fees.net)/(shares+q);
      shares+=q;buyValue+=fees.gross;buyFees+=fees.commission;lastBuy={...t,...fees};
    }else{
      if(q>shares)throw new Error(`${c} 在 ${t.trade_date||'未填日期'} 的減碼超過當時波段持股`);
      swingRealized+=fees.net-(avg*q);shares-=q;sellValue+=fees.gross;sellFees+=fees.commission;sellTax+=fees.tax;lastSell={...t,...fees};if(shares===0)avg=0;
    }
  }
  const m=data?.meta?.[c]||{},firstBuy=txs.find(t=>t.side==='BUY'&&!t.daytrade_pair_id),entryReason=firstBuy?.reason||'';
  const status=m.reason_status==='VALID'&&!String(entryReason||m.hold_reason||m.validation_condition||'').trim()?'UNVERIFIED':(m.reason_status||'UNVERIFIED');
  return{code:c,name:m.name||lastBuy?.name||firstBuy?.name||txs[0]?.name||'',shares,avg_cost:shares>0?avg:0,entry_date:firstBuy?.trade_date||'',entry_reason:entryReason,hold_reason:m.hold_reason||'',reason_status:status,validation_condition:m.validation_condition||'',failure_condition:m.failure_condition||'',strategy:m.strategy||'',note:m.note||'',realized_pl:swingRealized+daytradeRealized,swing_realized_pl:swingRealized,daytrade_realized_pl:daytradeRealized,daytrade_count:daytradeCount,buy_value:buyValue,sell_value:sellValue,buy_fees:buyFees,sell_fees:sellFees,sell_tax:sellTax,total_fees:buyFees+sellFees+sellTax,transaction_count:txs.length,cycle_count:cycle,last_buy:lastBuy,last_sell:lastSell,closed:shares===0&&txs.length>0,created_at:firstBuy?.created_at||'',updated_at:m.updated_at||data?.updated_at||new Date().toISOString()};
}

function enrichHistory(rows=[]){return rows.map(t=>({...t,...estimateTx(t)}))}
// Daytrade is declared by an explicit completed BUY/SELL pair or an explicit
// imported legacy transaction flag, never inferred from a checkbox in a sell form.
function wrapStore(){
  const s=window.RadarPortfolioStore;if(!s||wrapped)return false;wrapped=true;
  const original={addTransaction:s.addTransaction,exportData:s.exportData,history:s.history};
  const allCodes=data=>[...new Set((data?.transactions||[]).map(t=>t.code).filter(Boolean))];
  s.get=code=>{const p=feeAggregate(original.exportData(),code);return p.transaction_count?p:null};
  s.listAll=()=>allCodes(original.exportData()).map(c=>feeAggregate(original.exportData(),c)).filter(p=>p.transaction_count).sort((a,b)=>a.code.localeCompare(b.code));
  s.list=()=>s.listAll().filter(p=>p.shares>0);
  s.history=code=>enrichHistory(original.history(code));
  s.addTransaction=input=>{
    const x={...(input||{})};
    if(String(x.side||'').toUpperCase()==='SELL'&&x.daytrade===true){
      const base=String(x.source||'MANUAL_FILL').replace(/:DAYTRADE/ig,'');x.source=(base+':DAYTRADE').slice(0,60);
    }
    return original.addTransaction(x);
  };
  s.feeProfile=()=>({...profile});
  s.estimateFees=t=>estimateTx(t);
  return true;
}

function authSession(){
  try{
    const url=String(CONFIG().supabaseUrl||''),m=url.match(/^https:\/\/([^.]+)\.supabase\.co/i),keys=[];
    if(m)keys.push(`sb-${m[1]}-auth-token`);
    for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k?.startsWith('sb-')&&k.endsWith('-auth-token')&&!keys.includes(k))keys.push(k)}
    for(const k of keys){const raw=localStorage.getItem(k);if(!raw)continue;const x=JSON.parse(raw);if(x?.access_token)return x;if(x?.currentSession?.access_token)return x.currentSession}
  }catch{}
  return null;
}
function jwtSub(token){try{let s=token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');while(s.length%4)s+='=';return JSON.parse(atob(s)).sub||''}catch{return''}}
async function rest(path,{method='GET',body=null,prefer=''}={}){
  const cfg=CONFIG(),sess=authSession();if(!cfg.supabaseUrl||!cfg.supabaseAnonKey||!sess?.access_token)throw new Error('尚未登入雲端');
  const headers={apikey:cfg.supabaseAnonKey,Authorization:`Bearer ${sess.access_token}`,'Content-Type':'application/json'};if(prefer)headers.Prefer=prefer;
  const r=await fetch(String(cfg.supabaseUrl).replace(/\/$/,'')+'/rest/v1/'+path,{method,headers,body:body==null?undefined:JSON.stringify(body)});
  const text=await r.text();let data=null;try{data=text?JSON.parse(text):null}catch{data=text}
  if(!r.ok)throw new Error(data?.message||data?.hint||`雲端費率讀取失敗 (${r.status})`);return data;
}
async function fetchRemote(accountId){
  const rows=await rest(`inuko_fee_profiles?account_id=eq.${encodeURIComponent(accountId)}&select=account_id,commission_rate,minimum_commission_twd,odd_lot_minimum_commission_twd,sell_tax_rate,daytrade_sell_tax_rate`);
  return Array.isArray(rows)&&rows[0]?rows[0]:null;
}
async function saveRemote(accountId,p){
  const body={commission_rate:p.commission_rate,minimum_commission_twd:p.minimum_commission_twd,odd_lot_minimum_commission_twd:p.odd_lot_minimum_commission_twd,sell_tax_rate:p.sell_tax_rate,daytrade_sell_tax_rate:p.daytrade_sell_tax_rate,updated_at:new Date().toISOString()};
  let rows=await rest(`inuko_fee_profiles?account_id=eq.${encodeURIComponent(accountId)}`,{method:'PATCH',body,prefer:'return=representation'});
  if(Array.isArray(rows)&&rows.length)return rows[0];
  const sess=authSession(),userId=jwtSub(sess?.access_token||'');if(!userId)throw new Error('找不到登入帳號');
  rows=await rest('inuko_fee_profiles',{method:'POST',body:{account_id:accountId,user_id:userId,...body},prefer:'return=representation'});return Array.isArray(rows)?rows[0]:rows;
}
function applyProfile(p,{account=currentAccount(),silent=false}={}){
  profile=normalizeProfile(p);profileAccount=account||'device';writeLocal(profileAccount,profile);renderPanel();patchDaytradeControls();patchLedgerRows();
  if(!silent){document.dispatchEvent(new CustomEvent('inuko:fee-profile-changed',{detail:{accountId:profileAccount,profile:{...profile}}}));const s=window.RadarPortfolioStore;document.dispatchEvent(new CustomEvent('radar:portfolio-changed',{detail:{count:s?.list?.().length||0,fees:true}}))}
}
async function loadProfile(){
  wrapStore();const account=currentAccount();profileAccount=account;const cached=readLocal(account);if(cached)profile=normalizeProfile(cached);else profile={...DEFAULT_PROFILE};renderPanel();patchDaytradeControls();
  if(account==='device'||!authSession())return applyProfile(profile,{account,silent:false});
  try{const remote=await fetchRemote(account);lastRemoteAccount=account;applyProfile(remote?normalizeProfile(remote):profile,{account,silent:false})}catch(err){console.warn('fee profile cloud load failed',err);applyProfile(profile,{account,silent:false})}
}

function injectStyle(){if($('#inukoFeeStyle'))return;const s=document.createElement('style');s.id='inukoFeeStyle';s.textContent=`
.inuko-fees{margin:10px 0 14px;border:1px solid var(--line);border-radius:14px;background:var(--card);overflow:hidden}.inuko-fees summary{list-style:none;cursor:pointer;padding:11px 12px;font-weight:800;display:flex;align-items:center;justify-content:space-between;gap:8px}.inuko-fees summary::-webkit-details-marker{display:none}.inuko-fees-summary{font-size:.68rem;color:var(--muted);font-weight:600;text-align:right}.inuko-fees-body{padding:0 12px 12px}.inuko-fees-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.inuko-fees label{display:grid;gap:4px;font-size:.72rem;color:var(--muted)}.inuko-fees input{width:100%;box-sizing:border-box;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:9px;padding:9px}.inuko-fees-note{font-size:.68rem;color:var(--muted);line-height:1.5;margin:8px 0}.inuko-fees-actions{display:flex;align-items:center;justify-content:space-between;gap:8px}.inuko-fees-status{font-size:.68rem;color:var(--muted)}.fee-tx-detail{margin-top:4px;font-size:.67rem;color:var(--muted);font-weight:500}@media(max-width:560px){.inuko-fees-grid{grid-template-columns:1fr}}
`;document.head.appendChild(s)}
function panelHost(){return $('#inukoCloudPanel')||document.querySelector('#portfolioPanel .portfolio-privacy')}
function ensurePanel(){injectStyle();let d=$('#inukoFeePanel');if(d)return d;const host=panelHost();if(!host)return null;d=document.createElement('details');d.id='inukoFeePanel';d.className='inuko-fees';host.insertAdjacentElement('afterend',d);d.addEventListener('submit',saveForm);return d}
function renderPanel(status=''){
  const d=ensurePanel();if(!d)return;const fold=discountFold(),summary=`手續費 ${fold.toLocaleString('zh-TW',{maximumFractionDigits:2})} 折 · 賣出稅 ${(profile.sell_tax_rate*100).toFixed(2)}%`;
  d.innerHTML=`<summary><span>⚙️ 交易費率設定</span><span class="inuko-fees-summary">${esc(summary)}</span></summary><div class="inuko-fees-body"><form id="inukoFeeForm"><div class="inuko-fees-note">股票手續費標準費率 0.1425%。填你的券商折扣與最低手續費，庫存成本和已實現損益會一起重算。</div><div class="inuko-fees-grid"><label>券商手續費折扣（折）<input name="discount" type="number" min="0" max="20" step="0.1" inputmode="decimal" value="${fold.toFixed(2)}"></label><label>整股最低手續費（元）<input name="minimum" type="number" min="0" step="1" inputmode="numeric" value="${profile.minimum_commission_twd}"></label><label>零股最低手續費（元）<input name="odd_minimum" type="number" min="0" step="1" inputmode="numeric" value="${profile.odd_lot_minimum_commission_twd}"></label><label>一般賣出交易稅（%）<input name="sell_tax" type="number" min="0" max="5" step="0.01" inputmode="decimal" value="${(profile.sell_tax_rate*100).toFixed(2)}"></label><label>當沖賣出交易稅（%）<input name="daytrade_tax" type="number" min="0" max="5" step="0.01" inputmode="decimal" value="${(profile.daytrade_sell_tax_rate*100).toFixed(2)}"></label><label>目前實際手續費率<input value="${pct(profile.commission_rate)}" readonly aria-readonly="true"></label></div><div class="inuko-fees-note">買進：成交金額＋手續費。賣出：成交金額－手續費－交易稅。零股以單筆股數少於 1,000 股判斷；實際扣款仍以券商對帳單為準。</div><div class="inuko-fees-actions"><span class="inuko-fees-status" id="inukoFeeStatus">${esc(status||(profileAccount==='device'?'儲存在這台裝置':'依目前證券帳戶保存'))}</span><button class="refresh-btn" type="submit">儲存費率</button></div></form></div>`;
}
async function saveForm(e){
  if(e.target.id!=='inukoFeeForm')return;e.preventDefault();const f=e.target,fd=new FormData(f),discount=clamp(Number(fd.get('discount')||0),0,20),p=normalizeProfile({commission_rate:BASE_COMMISSION_RATE*(discount/10),minimum_commission_twd:Number(fd.get('minimum')),odd_lot_minimum_commission_twd:Number(fd.get('odd_minimum')),sell_tax_rate:Number(fd.get('sell_tax'))/100,daytrade_sell_tax_rate:Number(fd.get('daytrade_tax'))/100});
  const account=currentAccount();applyProfile(p,{account,silent:false});renderPanel('正在儲存…');
  try{if(account!=='device'&&authSession()){await saveRemote(account,p);lastRemoteAccount=account;renderPanel('已儲存到雲端');}else renderPanel('已儲存在這台裝置');}catch(err){console.error(err);renderPanel(`雲端儲存失敗：${err.message||'請稍後再試'}；本機設定已保留`)}
}
// Remove stale checkbox injected by older cached fee scripts, while preserving
// the separate completed same-day round-trip entry mode and its tax treatment.
function patchDaytradeControls(){
  document.querySelectorAll('#ledgerForm .fee-daytrade-row,#pqaForm .fee-daytrade-row').forEach(el=>el.remove());
}
function patchLedgerRows(){
  for(const row of document.querySelectorAll('.ledger-row')){const btn=row.querySelector('[data-ledger-delete]'),id=btn?.dataset?.ledgerDelete;if(!id)continue;const raw=window.RadarPortfolioStore?.exportData?.()?.transactions?.find(x=>x.id===id);if(!raw)continue;const fee=estimateTx(raw);if(fee.daytrade&&!row.querySelector('.fee-daytrade-badge')){const tag=row.querySelector('.ledger-row-top>div');tag?.insertAdjacentHTML('beforeend',' <span class="tag fee-daytrade-badge">當沖</span>')}
    const main=row.querySelector('.ledger-row-main');if(main){let detail=row.querySelector('.fee-tx-detail');if(!detail){detail=document.createElement('div');detail.className='fee-tx-detail';main.insertAdjacentElement('afterend',detail)}const text=raw.side==='BUY'?`手續費 ${money(fee.commission)} · 含費用成本 ${money(fee.net)}`:`手續費 ${money(fee.commission)} · 交易稅 ${money(fee.tax)} · 賣出實收 ${money(fee.net)}`;if(detail.textContent!==text)detail.textContent=text}
  }
}
function boot(){
  injectStyle();wrapStore();ensurePanel();patchDaytradeControls();loadProfile();
  document.addEventListener('inuko:auth-changed',()=>setTimeout(loadProfile,80));
  document.addEventListener('inuko:portfolio-account-changed',()=>setTimeout(loadProfile,80));
  document.addEventListener('radar:portfolio-changed',()=>setTimeout(()=>{ensurePanel();patchDaytradeControls();patchLedgerRows()},60));
  document.addEventListener('click',()=>setTimeout(()=>{patchDaytradeControls();patchLedgerRows()},80),true);
  observer=new MutationObserver(()=>{ensurePanel();patchDaytradeControls();patchLedgerRows()});observer.observe(document.body,{childList:true,subtree:true});
  setTimeout(()=>{if(currentAccount()!==lastRemoteAccount&&authSession())loadProfile()},1200);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
window.InukoFeeEngine={defaults:{...DEFAULT_PROFILE},profile:()=>({...profile}),estimate:estimateTx,reload:loadProfile};
})();
