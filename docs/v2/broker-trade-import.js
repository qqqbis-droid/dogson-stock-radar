/* INUKO LAB - client-only brokerage CSV/TSV trade import.
   Never upload files; read locally, preview, deduplicate, then commit atomically.
   Deliberately does not guess unmarked daytrades or merge multiple brokerage accounts. */
(function(){
'use strict';
if(window.__INUKO_BROKER_CSV_V1__)return;
window.__INUKO_BROKER_CSV_V1__=true;

var PREVIEW=null, DIALOG=null;
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function field(s){return String(s||'').replace(/^\uFEFF/,'').replace(/[\s\u3000_（）()【】「」\-\/]/g,'').toLowerCase()}
function detectDelimiter(first){var t=(first.match(/\t/g)||[]).length,c=(first.match(/,/g)||[]).length;return t>c?'\t':','}
function csvRecords(input){
  var text=String(input||'').replace(/^\uFEFF/,'');
  var delimiter=detectDelimiter(text.split(/\r?\n/).slice(0,15).find(function(x){return /\t|,/.test(x)})||'');
  var result=[], row=[], cell='', quoted=false;
  for(var i=0;i<text.length;i++){
    var ch=text[i];
    if(ch==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++}else quoted=!quoted}
    else if(ch===delimiter&&!quoted){row.push(cell);cell=''}
    else if((ch==='\n'||ch==='\r')&&!quoted){
      row.push(cell);cell='';
      if(row.some(function(x){return String(x).trim()}))result.push(row);
      row=[];if(ch==='\r'&&text[i+1]==='\n')i++;
    }else cell+=ch;
  }
  if(quoted)throw new Error('CSV 引號沒有結束，請重新從券商匯出 CSV');
  row.push(cell);if(row.some(function(x){return String(x).trim()}))result.push(row);
  if(result.length<2)throw new Error('找不到有效成交明細，至少需要欄名與一筆成交');
  if(result.length>20001)throw new Error('一次最多匯入 20,000 筆，請分批處理');
  return result;
}
var aliases={
 date:['成交日期','交易日期','成交日','交易日','日期','tradedate','date'],
 code:['股票代號','證券代號','證券代碼','股票代碼','股號','代號','symbol','stockcode','code'],
 name:['股票名稱','證券名稱','名稱','stockname','name'],
 side:['買賣別','買賣方向','買賣','交易別','交易方向','成交別','買賣區分','side','buyorsell'],
 shares:['成交股數','成交數量','成交股數股','股數','股數股','成交量','交易股數','數量','shares','quantity','qty'],
 lots:['成交張數','張數','數量張','交易張數','lots'],
 price:['成交均價','成交單價','成交價格','成交價','成交平均價','成交價位','成交價格元','成交單價元','成交價元','價格','price','avgprice'],
 time:['成交時間','成交時刻','時間','tradetime','time'],
 daytrade:['當沖','當沖別','當沖註記','現股當沖','交易型態','交易類別','daytrade'],
 account:['證券帳號','交易帳號','分戶帳號','帳戶號碼','子帳號','account'],
 order:['成交序號','成交編號','成交單號','交易序號','成交識別碼','tradeno','tradeid','fillid']
};
function columns(head){
  var out={};head.forEach(function(x,i){var h=field(x);for(var k in aliases){if(out[k]==null&&aliases[k].some(function(a){return h===field(a)}))out[k]=i}});
  return out;
}
function cell(row,col){return col==null?'':String(row[col]||'').trim()}
function dateOf(s){
  var x=String(s||'').trim().replace(/[年月]/g,'/').replace(/日/g,'').replace(/[.\-]/g,'/');
  if(/^\d{7,8}$/.test(x)){if(x.length===7)x=x.slice(0,3)+'/'+x.slice(3,5)+'/'+x.slice(5);else x=x.slice(0,4)+'/'+x.slice(4,6)+'/'+x.slice(6)}
  var m=x.match(/^(\d{3,4})\/(\d{1,2})\/(\d{1,2})$/);
  if(!m)return null;var year=Number(m[1]);if(m[1].length===3)year+=1911;
  if(year<2000||year>2100)return null;
  var d=year+'-'+String(Number(m[2])).padStart(2,'0')+'-'+String(Number(m[3])).padStart(2,'0');
  var when=new Date(d+'T00:00:00Z');return Number.isFinite(when.getTime())&&when.toISOString().slice(0,10)===d?d:null;
}
function amount(x){var t=String(x||'').trim().replace(/[,$，\sNT＄$元]/g,'');if(!t)return NaN;return Number(t)}
function sharesOf(value,asLots){
  var s=String(value||'').trim();
  if(/^\d+(?:\.\d+)?張(?:\d+股)?$/.test(s)){
    var m=s.match(/^(\d+(?:\.\d+)?)張(?:(\d+)股)?$/);
    return Number(m[1])*1000+Number(m[2]||0);
  }
  var q=amount(s);return asLots?q*1000:q;
}
function sideOf(s){
  var x=String(s||'').trim().toUpperCase().replace(/\s/g,'');
  if(/融資|融券|借券|權證|期貨|選擇權|申購|配股|股利/.test(x))return null;
  if(x==='B'||x==='BUY'||x.includes('買進')||x==='買'||x==='現買')return 'BUY';
  if(x==='S'||x==='SELL'||x.includes('賣出')||x==='賣'||x==='現賣')return 'SELL';
  return null;
}
function daytradeOf(s){var x=String(s||'').trim().toUpperCase();return x==='1'||x==='Y'||x==='YES'||x==='TRUE'||/當沖|現沖|沖銷/.test(x)}
function timeOf(s){
  var t=String(s||'').trim();if(!t)return '';
  var a=t.match(/^(\d{1,2}):?(\d{2})(?::?(\d{2}))?$/);
  if(!a)return '';var h=+a[1],m=+a[2],sec=+(a[3]||0);
  if(h>23||m>59||sec>59)return '';
  return String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':'+String(sec).padStart(2,'0');
}
function fingerprint(t){return [t.trade_date,t.code,t.side,t.shares,Number(t.price).toFixed(4),t.daytrade_pair_id?'DAYTRADE':'STANDARD'].join('|')}
function hash(x){var h=2166136261;for(var i=0;i<x.length;i++){h^=x.charCodeAt(i);h=Math.imul(h,16777619)}return(h>>>0).toString(36)}
function prepare(text){
  var all=csvRecords(text),headAt=all.findIndex(function(row){var x=columns(row);return x.date!=null&&x.code!=null&&x.side!=null&&x.price!=null&&(x.shares!=null||x.lots!=null)});if(headAt<0)headAt=0;var data=all.slice(headAt),col=columns(data[0]),required=['date','code','side','price'];
  var missing=required.filter(function(k){return col[k]==null});
  if(col.shares==null&&col.lots==null)missing.push('shares');
  if(missing.length)throw new Error('券商檔案欄位無法辨識：'+missing.join('、')+'。可先匯出具有「成交日期／股票代號／買賣別／成交股數／成交價」欄名的 CSV');
  var accounts=new Set(),valid=[],rejected=[];
  var store=window.RadarPortfolioStore;
  data.slice(1).forEach(function(row,index){
    var line=index+2,acc=cell(row,col.account);if(acc)accounts.add(acc);
    var day=dateOf(cell(row,col.date)),code=cell(row,col.code).toUpperCase().replace(/\s/g,''),side=sideOf(cell(row,col.side));
    var q=sharesOf(cell(row,col.shares!=null?col.shares:col.lots),col.shares==null),price=amount(cell(row,col.price));
    var mark=col.daytrade!=null&&daytradeOf(cell(row,col.daytrade));
    var reason='';
    if(!day)reason='日期無法辨識';
    else if(!store?.isTradingDay?.(day)||day>new Date(Date.now()+8*3600000).toISOString().slice(0,10))reason='非可確認的已成交交易日';
    else if(!/^[0-9A-Z-]{3,12}$/.test(code))reason='股票代號無效';
    else if(!side)reason='買賣別不支援（融資、融券等不能直接混入現股帳本）';
    else if(!Number.isInteger(q)||q<=0)reason='股數無效';
    else if(!Number.isFinite(price)||price<=0)reason='成交價無效';
    if(reason){rejected.push({line:line,reason:reason});return}
    valid.push({line:line,code:code,name:cell(row,col.name),side:side,shares:q,price:price,trade_date:day,time:timeOf(cell(row,col.time)),daytrade:mark,order:cell(row,col.order)});
  });
  if(accounts.size>1)throw new Error('檔案包含多個證券帳號，為避免混帳，請先按券商帳號分開匯出後再匯入');
  if(!valid.length)throw new Error('沒有可匯入的成交紀錄：'+(rejected[0]?.reason||'欄位資料無效'));
  var byPair=new Map();
  valid.filter(function(x){return x.daytrade}).forEach(function(x){var key=x.trade_date+'|'+x.code;if(!byPair.has(key))byPair.set(key,[]);byPair.get(key).push(x)});
  for(var pair of byPair.values()){
    var buys=pair.filter(function(x){return x.side==='BUY'}),sells=pair.filter(function(x){return x.side==='SELL'});
    if(pair.length===2&&buys.length===1&&sells.length===1&&buys[0].shares===sells[0].shares){
      var pairid='broker_pair_'+hash(pair[0].trade_date+'|'+pair[0].code+'|'+pair[0].shares+'|'+buys[0].price+'|'+sells[0].price);
      pair.forEach(function(x){x.pair_id=pairid});
    }else{
      pair.forEach(function(x){x.rejected='當沖買賣筆數或股數無法一對一配對，需先確認券商資料'});
    }
  }
  valid=valid.filter(function(x){if(!x.rejected)return true;rejected.push({line:x.line,reason:x.rejected});return false});
  var existing=store?.exportData?.()?.transactions||[];
  var used=new Map();existing.forEach(function(t){var key=fingerprint(t);used.set(key,(used.get(key)||0)+1)});
  valid.sort(function(a,b){return a.trade_date.localeCompare(b.trade_date)||a.time.localeCompare(b.time)||((a.side==='BUY'?0:1)-(b.side==='BUY'?0:1))||a.line-b.line});
  var ordinal=new Map(),newOnes=[],duplicates=[];
  valid.forEach(function(t){
    var key=fingerprint({trade_date:t.trade_date,code:t.code,side:t.side,shares:t.shares,price:t.price,daytrade_pair_id:t.pair_id||''});
    var n=(ordinal.get(key)||0)+1;ordinal.set(key,n);
    if(n<=(used.get(key)||0)){duplicates.push(t);return}
    var born=t.trade_date+'T'+(t.time||'12:00:00')+'+08:00';
    var id='broker_'+hash(key+'|'+(t.order||'')+'|'+n);
    newOnes.push({id:id,code:t.code,name:t.name,side:t.side,shares:t.shares,price:t.price,trade_date:t.trade_date,created_at:born,action:t.side==='BUY'?'ENTRY':'REDUCE',source:t.pair_id?'BROKER_CSV:DAYTRADE':'BROKER_CSV',daytrade_pair_id:t.pair_id||'',reason:'',discipline:'UNREVIEWED'});
  });
  return {rows:newOnes,duplicates:duplicates.length,rejected:rejected,fileRows:data.length-1,accounts:accounts.size,valid:valid.length,ledgerRevision:JSON.stringify((store?.exportData?.()?.transactions||[]).map(function(t){return [t.id,fingerprint(t)]}))};
}
function merge(prepared){
  var store=window.RadarPortfolioStore;if(!store?.importData||!store?.exportData)throw new Error('私人交易帳本尚未載入');
  // Recompute duplicates against the latest ledger: avoid double taps and any
  // manual additions between preview and confirmation.
  var current=store.exportData(),toAdd=[];var revision=JSON.stringify((current.transactions||[]).map(function(t){return [t.id,fingerprint(t)]}));if(revision!==prepared.ledgerRevision)throw new Error('預覽後交易帳本已有變更，請重新選檔預覽，避免重複匯入');
  prepared.rows.forEach(function(t){if(!current.transactions.some(function(x){return x.id===t.id}))toAdd.push(t)});
  if(!toAdd.length)return 0;
  var snapshot={transactions:current.transactions.concat(toAdd),meta:{...current.meta}};
  toAdd.forEach(function(t){if(!snapshot.meta[t.code]&&t.name)snapshot.meta[t.code]={name:t.name}});
  store.importData(snapshot); // validates full historical balance in memory, then one write.
  return toAdd.length;
}
function style(){
  if(document.getElementById('brokerTradeImportStyle'))return;
  var s=document.createElement('style');s.id='brokerTradeImportStyle';
  s.textContent='#brokerTradeImportDialog{width:min(94vw,650px);max-height:88dvh;border:1px solid var(--line);border-radius:16px;background:var(--card);color:var(--ink);padding:0}#brokerTradeImportDialog::backdrop{background:#0008}#brokerTradeImportDialog .broker-body{padding:13px;overflow-y:auto;max-height:69dvh;font-size:.78rem}#brokerTradeImportDialog .broker-note{font-size:.73rem;line-height:1.65;padding:10px;background:var(--soft);border-radius:9px;margin:9px 0}#brokerTradeImportDialog .broker-preview{overflow-x:auto;max-height:230px;overflow-y:auto;border:1px solid var(--line);border-radius:8px}#brokerTradeImportDialog table{border-collapse:collapse;width:100%;font-size:.69rem;white-space:nowrap}#brokerTradeImportDialog td,#brokerTradeImportDialog th{padding:7px;border-bottom:1px solid var(--line);text-align:left}#brokerTradeImportDialog .broker-error{color:#b54137;font-size:.75rem;line-height:1.5}#brokerTradeImportDialog .broker-actions{display:flex;gap:8px;justify-content:flex-end;padding:12px;border-top:1px solid var(--line)}#brokerTradeImportDialog button{min-height:36px}#portfolioBrokerImportBtn{white-space:nowrap}';
  document.head.appendChild(s);
}
function ensure(){
  style();var panel=document.querySelector('#portfolioPanel .portfolio-tools');
  if(panel&&!document.getElementById('portfolioBrokerImportBtn')){
    var button=document.createElement('button');button.id='portfolioBrokerImportBtn';button.className='text-btn';button.type='button';button.textContent='📥 匯入券商成交';
    var near=document.getElementById('portfolioImportBtn');panel.insertBefore(button,near||null);
  }
  if(!DIALOG){
    DIALOG=document.createElement('dialog');DIALOG.id='brokerTradeImportDialog';
    DIALOG.innerHTML='<div class="dialog-head"><strong>匯入券商成交｜CSV／TSV</strong><button type="button" class="icon-btn" id="brokerImportClose" aria-label="關閉">×</button></div>'+
      '<div class="broker-body"><div class="broker-note">① 從券商匯出「已成交明細」（非委託紀錄），在 iPhone「檔案」選取 CSV／TSV。<br>② 核對下方預覽後才會一次寫入私人帳本。<br>🔒 本機解析、不上傳券商檔案；不會清空舊交易紀錄。現階段帳本不分證券帳號，請勿混入不同帳戶。</div>'+
      '<input id="brokerCsvFile" type="file" accept=".csv,.tsv,text/csv,text/tab-separated-values,text/plain" style="max-width:100%;width:100%"><div id="brokerImportStatus" aria-live="polite" class="broker-note">尚未選擇檔案。Excel 可先另存成 CSV；圖片、PDF、XLSX 尚未支援。</div><div id="brokerImportPreview"></div></div>'+
      '<div class="broker-actions"><button type="button" class="text-btn" id="brokerImportCancel">取消</button><button type="button" class="refresh-btn" id="brokerImportConfirm" disabled>確認匯入 0 筆</button></div>';
    document.body.appendChild(DIALOG);
    DIALOG.querySelector('#brokerImportClose').addEventListener('click',function(){DIALOG.close()});
    DIALOG.querySelector('#brokerImportCancel').addEventListener('click',function(){DIALOG.close()});
    DIALOG.querySelector('#brokerCsvFile').addEventListener('change',onFile);
    DIALOG.querySelector('#brokerImportConfirm').addEventListener('click',commit);
  }
}
function show(){ensure();PREVIEW=null;DIALOG.querySelector('#brokerCsvFile').value='';DIALOG.querySelector('#brokerImportStatus').textContent='尚未選擇檔案。';DIALOG.querySelector('#brokerImportPreview').innerHTML='';DIALOG.querySelector('#brokerImportConfirm').disabled=true;DIALOG.showModal()}
async function onFile(event){
  PREVIEW=null;var status=DIALOG.querySelector('#brokerImportStatus'),box=DIALOG.querySelector('#brokerImportPreview'),confirm=DIALOG.querySelector('#brokerImportConfirm');
  confirm.disabled=true;box.innerHTML='';
  var f=event.target.files?.[0];if(!f)return;
  if(f.size>4000000){status.textContent='檔案超過 4MB，請先分批匯出';return}
  try{
    var buf=await f.arrayBuffer(),decoded;
    try{decoded=new TextDecoder('utf-8',{fatal:true}).decode(buf)}
    catch{decoded=new TextDecoder('big5').decode(buf)}
    PREVIEW=prepare(decoded);
    status.textContent='檔案 '+f.name+'｜可新增 '+PREVIEW.rows.length+' 筆｜與現有紀錄相同 '+PREVIEW.duplicates+' 筆｜無法辨識 '+PREVIEW.rejected.length+' 筆';
    var html='<div class="broker-preview"><table><thead><tr><th>日期</th><th>代號</th><th>買賣</th><th>股數</th><th>成交價</th></tr></thead><tbody>';
    PREVIEW.rows.slice(0,25).forEach(function(x){html+='<tr><td>'+esc(x.trade_date)+'</td><td>'+esc(x.code)+'</td><td>'+esc(x.side==='BUY'?'買':'賣')+'</td><td>'+x.shares+'</td><td>'+esc(x.price)+'</td></tr>'});
    html+='</tbody></table></div>';
    if(PREVIEW.rows.length>25)html+='<div class="broker-note">僅預覽前 25 筆；確認後會一次匯入全部 '+PREVIEW.rows.length+' 筆。</div>';
    if(PREVIEW.rejected.length)html+='<p class="broker-error">⚠️ 有 '+PREVIEW.rejected.length+' 筆無法辨識，將不匯入：'+PREVIEW.rejected.slice(0,5).map(function(x){return '第'+x.line+'列 '+esc(x.reason)}).join('；')+'。請確認不是融資融券或未配對當沖。</p>';
    html+='<p class="broker-note">本帳本不分帳戶；若既有庫存是其他證券帳號，請不要按確認。手續費與證交稅仍按網站的費率設定估算，未讀取券商實收費稅。</p>';
    box.innerHTML=html;confirm.disabled=!PREVIEW.rows.length;confirm.textContent='確認匯入 '+PREVIEW.rows.length+' 筆';
  }catch(err){status.textContent='無法讀取：'+(err?.message||'不支援的檔案格式')}
}
function commit(){
  if(!PREVIEW||!PREVIEW.rows.length)return;
  try{
    var count=merge(PREVIEW);
    DIALOG.querySelector('#brokerImportStatus').textContent='✅ 已匯入 '+count+' 筆；原有紀錄保留，重複項目不重複加入。';
    DIALOG.querySelector('#brokerImportConfirm').disabled=true;
    DIALOG.querySelector('#brokerImportPreview').innerHTML='<div class="broker-note">匯入完成，請到「全部交易紀錄」確認持股與已實現損益。</div>';
    PREVIEW=null;
  }catch(err){DIALOG.querySelector('#brokerImportStatus').textContent='未匯入任何一筆：'+(err?.message||'歷史持股無法核對')+'。請先確認是否包含完整買進歷史或期初庫存。'}
}
function boot(){
  ensure();document.addEventListener('radar:view-rendered',ensure);
  document.addEventListener('click',function(e){if(e.target.closest?.('#portfolioBrokerImportBtn')){e.preventDefault();show()}},true);
}
window.InukoBrokerTradeImport={parse:prepare,records:csvRecords};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
