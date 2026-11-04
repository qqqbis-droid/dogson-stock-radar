/* INUKO LAB - manual Daytrade Risk SOP 2.0. No brokerage orders, no score changes. */
(function(){
'use strict';
if(window.__INUKO_DAYTRADE_SOP_V2__)return;
window.__INUKO_DAYTRADE_SOP_V2__=true;
var E=window.InukoDaytradeRiskV2,KEY='inuko.daytrade.sop.v2.manual',host=null;
if(!E){console.warn('SOP risk engine missing');return}
function load(){try{var x=JSON.parse(localStorage.getItem(KEY)||'{}');return{active:x.active||null,archive:Array.isArray(x.archive)?x.archive.slice(-100):[]}}catch(e){return{active:null,archive:[]}}}
var data=load();
function save(){try{localStorage.setItem(KEY,JSON.stringify(data))}catch(e){alert('本機儲存失敗；請匯出備份，不要依賴這份紀錄。')}}
function esc(x){return String(x==null?'':x).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function num(x){return x==null||String(x).trim()===''?NaN:Number(x)}
function fmt(x,d){return Number.isFinite(x)?Number(x).toLocaleString('zh-TW',{maximumFractionDigits:d==null?0:d,minimumFractionDigits:d==null?0:d}):'—'}
function signed(x){return Number.isFinite(x)?(x>=0?'+':'')+fmt(x)+' 元':'—'}
function fees(){try{return E.profile(window.InukoFeeEngine&&window.InukoFeeEngine.profile?window.InukoFeeEngine.profile():{})}catch(e){return E.profile({})}}
function setupData(){
  var f=host.querySelector('#sopSetupForm'),get=function(k){return f.elements.namedItem(k).value};
  return {code:String(get('code')||'').trim().toUpperCase(),entry:num(get('entry')),stop:num(get('stop')),
    shares:num(get('shares')),budget:num(get('budget')),capitalLimit:num(get('capitalLimit')),
    slippageTicks:num(get('slippageTicks')),fees:fees()};
}
function field(label,val,cls){return '<div class="sop-metric"><small>'+esc(label)+'</small><strong class="'+esc(cls||'')+'">'+esc(val)+'</strong></div>'}
function style(){
  if(document.getElementById('sopStyleV2'))return;
  var e=document.createElement('style');e.id='sopStyleV2';
  e.textContent='#daytradeSopV2{border:1px solid var(--line);background:var(--card);border-radius:16px;margin:12px 0;padding:13px;color:var(--ink)}'+
  '#daytradeSopV2[hidden]{display:none!important}#daytradeSopV2 summary{display:flex;cursor:pointer;justify-content:space-between;align-items:center;gap:8px;font-weight:800}'+
  '#daytradeSopV2 summary small{color:var(--muted);font-size:.69rem}#daytradeSopV2 .sop-note{color:var(--muted);font-size:.72rem;line-height:1.55;margin:9px 0}'+
  '#daytradeSopV2 .sop-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}'+
  '#daytradeSopV2 label{display:grid;gap:5px;color:var(--muted);font-size:.72rem}'+
  '#daytradeSopV2 input{min-width:0;width:100%;box-sizing:border-box;padding:10px 9px;font-size:16px;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:9px}'+
  '#daytradeSopV2 .sop-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:12px 0}'+
  '#daytradeSopV2 .sop-metric{border:1px solid var(--line);background:var(--soft);padding:10px;border-radius:10px;min-width:0}'+
  '#daytradeSopV2 .sop-metric small{display:block;font-size:.65rem;color:var(--muted);margin-bottom:4px}'+
  '#daytradeSopV2 .sop-metric strong{font-size:.98rem;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}'+
  '#daytradeSopV2 .sop-danger{color:#c64538}#daytradeSopV2 .sop-positive{color:#127c53}'+
  '#daytradeSopV2 .sop-status{padding:10px 11px;border:1px solid var(--line);border-radius:10px;font-size:.74rem;line-height:1.55;margin:9px 0}'+
  '#daytradeSopV2 .sop-status.warn{border-color:#df9d88;color:#b33a2d;background:rgba(216,79,49,.07)}'+
  '#daytradeSopV2 .sop-status.good{border-color:#91bca5;color:#1a7956;background:rgba(43,142,94,.07)}'+
  '#daytradeSopV2 .sop-actions{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}'+
  '#daytradeSopV2 button{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:9px 12px;border-radius:10px;cursor:pointer;font-size:.78rem;font-weight:750}'+
  '#daytradeSopV2 button.primary{background:#205c49;color:#fff;border-color:#205c49}'+
  '#daytradeSopV2 button.danger{color:#b33a2d;border-color:#d7a9a1}'+
  '#daytradeSopV2 button:disabled{opacity:.5;cursor:not-allowed}'+
  '#daytradeSopV2 h3{font-size:.91rem;margin:14px 0 6px}#daytradeSopV2 .sop-active{margin-top:11px;padding:12px;border:1px solid var(--line);border-radius:12px}'+
  '#daytradeSopV2 .sop-log{font-size:.68rem;line-height:1.5;color:var(--muted);padding-left:17px}'+
  '@media(min-width:800px){#daytradeSopV2 .sop-grid{grid-template-columns:repeat(3,minmax(0,1fr))}#daytradeSopV2 .sop-metrics{grid-template-columns:repeat(4,minmax(0,1fr))}}';
  document.head.appendChild(e);
}
function setup(){
  if(host||!document.getElementById('radarPanel'))return;
  style();host=document.createElement('section');host.id='daytradeSopV2';host.className='panel';host.hidden=true;
  host.innerHTML=[
    '<details id="sopDetails"><summary><span>🛡 當沖風控 SOP 2.0 <small>測試版・不更動評分</small></span><small>展開試算</small></summary>',
    '<p class="sop-note">手動輸入實際或預計成交價；不連券商、不下單、不會修改原本庫存與當沖分數。</p>',
    '<form id="sopSetupForm"><div class="sop-grid">',
    '<label>股票代號<input name="code" maxlength="12" placeholder="例如 1815" autocapitalize="characters" required></label>',
    '<label>買進成交／計畫價<input name="entry" type="number" min="0.01" step="any" inputmode="decimal" value="53" required></label>',
    '<label>結構停損價<input name="stop" type="number" min="0.01" step="any" inputmode="decimal" value="52.5" required></label>',
    '<label>股數（整張）<input name="shares" type="number" min="1000" step="1000" inputmode="numeric" value="1000" required></label>',
    '<label>單筆風險預算（元）<input name="budget" type="number" min="1" step="1" value="1000" inputmode="numeric" required></label>',
    '<label>買進資金上限（元）<input name="capitalLimit" type="number" min="1" step="1" value="60000" inputmode="numeric" required></label>',
    '<label>預留滑價（買賣各幾檔）<input name="slippageTicks" type="number" min="0" max="20" step="1" value="1" inputmode="numeric" required></label>',
    '</div><div id="sopPreview" aria-live="polite"></div>',
    '<div class="sop-actions"><button type="submit" id="sopStart" class="primary">通過風險檢查後建立手動計畫</button></div></form>',
    '<div id="sopActive"></div><div class="sop-actions"><button type="button" id="sopExport">匯出風控紀錄 CSV</button></div>',
    '<p class="sop-note">費率沿用「庫存 → 交易費率設定」。1R／2R 僅提供防守參考，絕不自動提高停損。MIT 觸價不保證成交，特殊股種的跳動價位與交易限制請另行核對。</p></details>'
  ].join('');
  document.getElementById('radarPanel').insertAdjacentElement('beforebegin',host);
  host.addEventListener('input',function(e){if(e.target.closest('#sopSetupForm'))preview()});
  host.addEventListener('submit',function(e){if(e.target.id==='sopSetupForm'){e.preventDefault();start()}});
  host.addEventListener('click',click);
  sync();
}
function sync(){if(!host)return;host.hidden=!document.querySelector('.tab.active[data-view="daytrade"]');if(!host.hidden){preview();renderActive()}}
function preview(){
  if(!host)return;
  var f=setupData(),a;try{a=E.assess(f)}catch(e){host.querySelector('#sopPreview').textContent='費率或資料錯誤：'+e.message;return}
  var errors=a.errors.slice();if(!/^[0-9A-Z-]{3,12}$/.test(f.code))errors.unshift('請填有效股票代號');
  var html='';
  if(a.risk!=null)html='<div class="sop-metrics">'+
    field('買進金額含手續費','NT$ '+fmt(a.capital))+
    field('總風險含費稅滑價','NT$ '+fmt(a.risk),'sop-danger')+
    field('其中價差風險','NT$ '+fmt(a.priceRisk))+
    field('費稅＋預留滑價','NT$ '+fmt(a.feeTax+a.slippageReserve))+
    field('含費稅滑價的保本參考','NT$ '+fmt(a.breakEven,2))+'</div>';
  html+='<div class="sop-status '+(errors.length?'warn':'good')+'">'+(errors.length?'⛔ '+errors.map(esc).join('；'):'✅ 通過單筆金額與風險 Gate；不代表當下適合進場')+'</div>';
  host.querySelector('#sopPreview').innerHTML=html;
  host.querySelector('#sopStart').disabled=errors.length>0||!!data.active;
}
function record(p,kind,more){p.events.push(Object.assign({at:new Date().toISOString(),kind:kind},more||{}));p.events=p.events.slice(-400)}
function start(){
  if(data.active){alert('已有一筆追蹤中的計畫；請先記錄平倉。');return}
  var f=setupData(),a;try{a=E.assess(f)}catch(e){alert(e.message);return}
  if(!a.ok||!/^[0-9A-Z-]{3,12}$/.test(f.code)){preview();return}
  var p={id:'sop_'+Date.now(),code:f.code,entry:a.entry,initialStop:a.stop,defense:a.stop,
    shares:a.shares,budget:a.budget,capitalLimit:a.capitalLimit,slippageTicks:a.slippageTicks,
    fees:f.fees,initialRisk:a.risk,breakEven:a.breakEven,last:a.entry,peak:a.entry,openedAt:new Date().toISOString(),events:[]};
  record(p,'PLAN_STARTED',{price:a.entry,defense:p.defense,risk:a.risk});
  data.active=p;save();renderActive();preview();
}
function renderActive(){
  var dst=host&&host.querySelector('#sopActive');if(!dst)return;
  var p=data.active;if(!p){var last=data.archive[data.archive.length-1];dst.innerHTML='<p class="sop-note">目前沒有手動追蹤中的計畫；此工具不會向券商送單。</p>'+(last?'<div class="sop-status">上一筆 '+esc(last.code)+'：實際出場 '+fmt(last.exit,2)+'｜估算淨損益 '+signed(last.netPnl)+'｜低於最後防守價的成交偏差 '+fmt(last.adverseStopGap||0)+' 元（僅當成交價低於防守價）</div>':'');return}
  var a=E.protection({entry:p.entry,stop:p.initialStop,shares:p.shares,budget:p.budget,capitalLimit:p.capitalLimit,slippageTicks:p.slippageTicks,fees:p.fees},p.peak,p.last,p.defense);
  var stage={HOLD_INITIAL:'未達 1R｜維持原始結構',CHECK_BREAKEVEN:'已達 1R｜檢查費稅保本',PROTECT_HALF_PEAK:'已達 2R｜檢查最高浮盈回撤一半'};
  var log=p.events.slice(-6).reverse().map(function(x){return '<li>'+esc(x.at.slice(0,19).replace('T',' '))+' '+esc(x.kind)+' '+esc(x.reason||'')+(x.price!=null?'｜'+fmt(x.price,2):'')+'</li>'}).join('');
  dst.innerHTML='<div class="sop-active"><h3>追蹤計畫｜'+esc(p.code)+'（人工價格）</h3>'+
    '<div class="sop-metrics">'+field('進場／原停損',fmt(p.entry,2)+' / '+fmt(p.initialStop,2))+
    field('目前人工價格',fmt(p.last,2))+field('已輸入最高價',fmt(p.peak,2))+
    field('現在手動防守價',fmt(p.defense,2))+
    field('估算浮動淨損益',signed(a.currentNet),a.currentNet>=0?'sop-positive':'sop-danger')+
    field('目前 R 倍數',fmt(a.currentR,2)+' R')+
    field('保護參考價（不自動採用）',a.suggested==null?'目前無':fmt(a.suggested,2))+
    field('初始總風險','NT$ '+fmt(p.initialRisk))+'</div>'+
    '<div class="sop-status">'+esc(stage[a.stage]||a.stage)+'｜費稅保本參考 '+fmt(p.breakEven,2)+'</div>'+
    (a.warning?'<div class="sop-status warn">'+esc(a.warning)+'</div>':'')+
    '<div class="sop-grid"><label>觀察／實際出場價<input id="sopLastPrice" type="number" min="0.01" step="any" inputmode="decimal" value="'+p.last+'"></label>'+
    '<label>擬調高防守價<input id="sopNewDefense" type="number" min="0.01" step="any" inputmode="decimal" value="'+p.defense+'"></label>'+
    '<label>調整或出場理由（必填）<input id="sopReason" maxlength="180" placeholder="例：支撐失守"></label></div>'+
    '<div class="sop-actions"><button type="button" id="sopPrice">記錄人工價格</button>'+
    '<button type="button" id="sopRaise">確認調高防守價</button>'+
    '<button type="button" id="sopClose" class="danger">記錄全數實際出場</button></div>'+
    '<p class="sop-note">防守價只可調高，不可向下放寬；觸及停損警告不代表已成交。出場請填寫券商實際成交價，不能用未成交掛單價格。</p>'+
    '<h3>最近紀錄</h3><ul class="sop-log">'+log+'</ul></div>';
}
function click(e){
  var id=e.target.id,p=data.active;
  if(id==='sopExport'){exportCsv();return}
  if(!p)return;
  var price=num(host.querySelector('#sopLastPrice').value),reason=host.querySelector('#sopReason').value.trim();
  if(id==='sopPrice'){
    if(!(price>0&&E.validTick(price))){alert('請輸入有效台股價格');return}
    p.last=price;p.peak=Math.max(p.peak,price);record(p,'MANUAL_PRICE',{price:price,defense:p.defense});save();renderActive();
  }else if(id==='sopRaise'){
    var next=num(host.querySelector('#sopNewDefense').value);
    if(!reason){alert('請填調整原因');return}
    if(!(next>p.defense&&next<p.last&&E.validTick(next))){alert('只能調高防守價，且必須低於目前手動價格；不得擴大原停損。');return}
    var prev=p.defense;p.defense=next;record(p,'STOP_RAISED',{from:prev,defense:next,price:p.last,reason:reason});save();renderActive();
  }else if(id==='sopClose'){
    if(!reason){alert('請填實際出場原因');return}
    if(!(price>0&&E.validTick(price))){alert('請填券商實際成交價；未成交不能結案。');return}
    if(!confirm('確定已實際全數成交於 '+price+' 元？這只會存入本機，不會向券商下單。'))return;
    var realized=E.netPnl(p.entry,price,p.shares,p.fees);
    var adverseGap=price<p.defense?Math.round((p.defense-price)*p.shares):0;
    record(p,'MANUAL_EXIT',{price:price,reason:reason,netPnl:realized,stopReference:p.defense,adverseStopGap:adverseGap});
    p.exit=price;p.netPnl=realized;p.adverseStopGap=adverseGap;p.closedAt=new Date().toISOString();data.archive.push(p);data.archive=data.archive.slice(-100);data.active=null;save();renderActive();preview();
  }
}
function exportCsv(){
  var rows=[['plan_id','code','entry','initial_stop','shares','initial_risk_including_fees_slippage','timestamp','event','price','defense','reason','estimated_net_pnl','stop_reference','adverse_stop_gap_twd','source']];
  data.archive.concat(data.active?[data.active]:[]).forEach(function(p){
    (p.events||[]).forEach(function(ev){rows.push([p.id,p.code,p.entry,p.initialStop,p.shares,p.initialRisk,ev.at,ev.kind,ev.price==null?'':ev.price,ev.defense==null?'':ev.defense,ev.reason||'',ev.netPnl==null?'':ev.netPnl,ev.stopReference==null?'':ev.stopReference,ev.adverseStopGap==null?'':ev.adverseStopGap,'MANUAL_ONLY_NOT_BROKER_VERIFIED'])});
  });
  function quote(x){return '"'+String(x==null?'':x).replace(/"/g,'""')+'"'}
  var csv='\uFEFF'+rows.map(function(r){return r.map(quote).join(',')}).join('\r\n')+'\r\n';
  var url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  var a=document.createElement('a');a.href=url;a.download='犬子選骨室_當沖SOP2_手動風控紀錄.csv';document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(url)},3000);
}
function boot(){
  setup();document.addEventListener('click',function(e){if(e.target.closest&&e.target.closest('#tabs .tab'))setTimeout(sync,0)});
  document.addEventListener('radar:view-rendered',sync);
  document.addEventListener('inuko:fee-profile-changed',preview);
  window.InukoDaytradeSop2={read:function(){return JSON.parse(JSON.stringify(data))},sync:sync};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
