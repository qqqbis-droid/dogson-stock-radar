(()=>{
'use strict';
// INUKO swing path: a PRESENTATION of same-build observed zones, not a
// price forecasting engine. NEVER fabricate R2 or mark price-only crossing
// as a verified breakout/entry.
const n=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const day=v=>String(v||'').slice(0,10);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const price=v=>n(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:Math.abs(Number(v))<10?2:Math.abs(Number(v))<100?2:Math.abs(Number(v))<1000?1:0});
const fmtRange=z=>!z?'待補（不推估）':n(z.low)===n(z.high)?price(z.low):price(z.low)+'～'+price(z.high);
const RISK=new Set(['EXIT_PRIORITY','REDUCE_WATCH','DO_NOT_CHASE','DATA_STALE']);
const STALE=new Set(['INVALID','STALE','SUPERSEDED']);
const FRESH=new Set(['FRESH','FROZEN']);
function sameZone(z,shard,tradeDate){
 return Boolean(z&&z.build_id===shard.build_id&&day(z.trade_date)===tradeDate
   &&FRESH.has(String(z.freshness||''))&&!STALE.has(String(z.structure_state||''))
   &&n(z.low)>0&&n(z.high)>=n(z.low)
   &&(z.side==='SUPPORT'||z.side==='RESISTANCE'));
}
function usable(shard,tradeDate,side,rank){
 return (Array.isArray(shard?.zones)?shard.zones:[])
  .filter(z=>sameZone(z,shard,tradeDate)&&z.side===side&&z.rank===rank)
  .sort((a,b)=>side==='SUPPORT'?b.high-a.high:a.low-b.low)[0]||null;
}
function zoneEvidence(z){
 if(!z)return {text:'無可核對價位',date:'',source:'無',status:'待補',validated:false};
 const evidence=(Array.isArray(z.evidence)?z.evidence:[]).filter(Boolean);
 const sources=(Array.isArray(z.source_status?.sources)?z.source_status.sources:[]).map(String);
 // A computed zone is not a verified historical high just because the
 // evidence list names one. Explicitly distinguish model-derived structure.
 return {
   text:evidence.length?evidence.join('＋'):'模型結構區（組成未列明）',
   date:day(z.trade_date),
   source:sources.includes('legacy-v1-migration-adapter')?'模型結構整理（含歷史來源）':'結構引擎',
   status:FRESH.has(z.freshness)?'同日來源已核對・尚待價格觸發':'資料待驗',
   validated:FRESH.has(z.freshness)
 };
}
function evaluate(shard,{expectedBuild='',expectedDate='',plan=null,view='close',allowed=true}={}){
 const d=shard?.decision||{},e=shard?.evidence||{};
 const date=day(shard?.as_of),build=String(shard?.build_id||'');
 const quote=n(d?.quote?.price),confidence=n(d?.data_confidence);
 const known=Boolean(allowed===true&&shard&&build&&(expectedBuild?build===expectedBuild:true)
   &&date&&(expectedDate?date===day(expectedDate):true)
   &&quote>0&&confidence!=null&&confidence>=80);
 const support=known?usable(shard,date,'SUPPORT','S1'):null;
 const resistance=known?usable(shard,date,'RESISTANCE','R1'):null;
 const proposedR2=known?usable(shard,date,'RESISTANCE','R2'):null;
 // A later barrier is meaningful only after a valid preceding R1. Suppress
 // duplicate/overlapping R2 and any orphaned remote price.
 const extension=resistance&&proposedR2&&n(proposedR2.low)>n(resistance.high)?proposedR2:null;
 const openSky=known&&plan?.openSky===true&&!resistance&&support&&n(plan?.breakoutLevel)>0;
 const H=e?.hourly60||{};
 const h60ok=day(H.trade_date)===date&&String(H.data_status||'')==='OK';
 const h60valid=h60ok&&n(H.ma20_60)!=null&&n(H.ma60_60)!=null;
 const chipDates=[day(e.foreign_date),day(e.trust_date)];
 const chipSame=chipDates.every(x=>x===date);
 const overheated=RISK.has(String(d.action_state||''))||['FAILED','WEAKENING'].includes(d.lifecycle_stage)
   ||H.entry_light==='RED'&&h60ok;
 let phase='條件待核對',kind='verify';
 let action='先補齊同一交易日證據，不建立新倉';
 if(known){
   const planType=String(plan?.type||'');
   if(openSky){
     phase=planType==='LAYOUT'?'前高突破・回測已確認':'前高突破・等待回測';
     kind=planType==='LAYOUT'?'pullback':'breakout';
     action=String(plan?.gate||'等待近20日平台與 S1 回測守住，不追價');
   }else if(planType==='NO_CHASE'||(!planType&&overheated)){
     // Risk must take priority over missing R1, or the compact path would
     // misleadingly say "data pending" on a verified no-chase stock.
     phase='風險優先／先不追價';kind='risk';
     action='暫停追價；等待風險改善後重新評估';
   }else if(['VERIFY','PARTIAL'].includes(planType)||!support||!resistance){
     phase='價位證據待補';kind='verify';
     action='S1／R1 尚未完整核對，暫不建立新倉';
   }else if(['PULLBACK_TEST','PULLBACK_CONFIRMED'].includes(d.lifecycle_stage)||['WAIT_PULLBACK'].includes(d.action_state)||planType==='LAYOUT'){
     phase='回測承接待確認';kind='pullback';
     action='等 S1 回測有效守住、量價與60分K同步，再評估進場';
   }else if(quote>=resistance.high){
     phase='突破後待回測';kind='breakout';
     action='價格已越過 R1，但仍須量價確認及回測不破，不能視為已完成突破';
   }else if(['TREND'].includes(d.lifecycle_stage)||['HOLD','ADD_ON_CONFIRM'].includes(d.action_state)){
     phase='波段延續觀察';kind='trend';
     action='先守住已確認支撐；接近 R1 不追價';
   }else{
     phase='等待突破';kind='wait';
     action='先驗證 R1 有效站上與量能，再觀察回測承接';
   }
 }
 if(plan?.gate&&known&&!['VERIFY','PARTIAL'].includes(String(plan.type||''))){
   // CloseOps verdict remains the owner of tomorrow's actionable plan.
   action=String(plan.gate);
 }
 const next=known&&resistance
   ?quote>=resistance.high?'R1 '+fmtRange(resistance)+'（回測待確認）':'R1 '+fmtRange(resistance)
   :openSky?'近20日突破平台 '+price(plan.breakoutLevel)+'（回測參考，非上方目標）'
   :known&&support?'R1 待補；先觀察 S1 '+fmtRange(support):'關鍵價位待核對';
 const invalidation=support
   ?'有效跌破 S1 下緣 '+price(support.low)+' 並回抽站不回，且量價轉弱時重評；非觸價即停損'
   :'S1 尚未核對，不設定猜測停損或買進價';
 // Explicit state-machine gates: every source must be both current and
 // independently supported. A price crossing alone never upgrades the stage.
 const volume=n(e.vol_x)??n(d.quote?.relative_volume);
 const volumePass=Boolean(known&&volume>=1&&
   (resistance&&quote>=resistance.high&&(e.break20===true||e.break3===true)
     ||openSky&&e.break20===true&&quote>n(plan.breakoutLevel)));
 const hourPass=Boolean(h60valid&&H.ma20_60>H.ma60_60&&H.entry_light!=='RED');
 const chipPass=Boolean(chipSame&&day(e.sbl_date)===date&&
   e.foreign_3buy===true&&e.sbl_3down===true);
 const relative=e?.relative_multiframe||{};
 const marketPass=Boolean(day(relative.trade_date)===date&&
   (relative.outperforming_market===true||relative.relative_strength_positive===true));
 const checks=[
   {name:'價格＋量能',passed:volumePass,desc:openSky?'20日平台突破、同日量能與回測證據':'R1 上緣、成交量與有效突破結構'},
   {name:'60分K結構',passed:hourPass,desc:'同日 20T／60T 多方排列且沒有紅燈'},
   {name:'法人與借券',passed:chipPass,desc:'同日外資連買與借券減少'},
   {name:'相對大盤',passed:marketPass,desc:'同交易日相對強弱需有獨立證據'}
 ];
 const promotionReady=Boolean(known&&support&&(resistance||openSky)&&checks.every(c=>c.passed)
   &&e.breakout_confirmed===true&&e.retest_confirmed===true
   &&!overheated&&!['VERIFY','PARTIAL','NO_CHASE'].includes(String(plan?.type||'')));
 if(promotionReady){phase='突破回測雙確認';kind='trend'}
 const sourceGood=Boolean(known&&support&&(resistance||openSky));
 const steps=[
  {name:'目前價格',value:known?price(quote):'待核對',state:known?'observed':'missing',hint:date?'資料日 '+date:'等待同日價格'},
  {name:openSky?'下一關｜前高回測':'下一關｜R1',value:openSky?price(plan.breakoutLevel):known?fmtRange(resistance):'待核對',state:resistance||openSky?'next':'missing',hint:openSky?'僅是已知20日平台基準，不代表已證實歷史新高':resistance?'有效站穩上緣、量價同步':'尚無同日有效 R1'},
  {name:'回測承接',value:openSky?'原平台／S1 待驗':resistance?'R1 角色轉換待確認':'不可推估',state:'future',hint:openSky?'回踩支撐、量價與大盤相對強弱確認後才能考慮布局':'突破後回測守住才可升級；未自動判定'},
  {name:openSky?'後續觀察｜上方':'後續觀察｜R2',value:openSky?'尚無有效歷史壓力':extension?fmtRange(extension):'待補，不預測',state:extension?'future':'missing',hint:openSky?'不得把缺少 R1 解讀成無上漲阻力或預設目標價':extension?'須重新驗證，不當目標價':'沒有同日 R2 證據'}
 ];
 return {date,build,quote,confidence,known,sourceGood,support,resistance,extension,h60ok,h60valid,chipSame,phase,kind,action,next,invalidation,steps,view,checks,promotionReady};
}
function compactHtml(p){
 if(!p)return '';
 return '<section class="swing-path-compact" data-swing-compact aria-label="明日波段路徑">'
   +'<div><span>目前階段</span><b>'+esc(p.phase)+'</b></div>'
   +'<div><span>下一關卡</span><b>'+esc(p.next)+'</b></div>'
   +'<div><span>明日動作</span><b>'+esc(p.action)+'</b></div>'
   +'<div class="swing-path-risk"><span>失效條件</span><b>'+esc(p.invalidation)+'</b></div>'
   +'<p>資料日 '+esc(p.date||'待核對')+' · 僅採有效 S1／R1 或經驗證前20日平台，不預測遠端價格</p>'
   +'</section>';
}
function sourceCard(z,rank){
 const source=zoneEvidence(z);
 return '<div class="swing-source-card">'
  +'<b>'+esc(rank)+'</b><strong>'+esc(fmtRange(z))+'</strong>'
  +'<span>'+esc(source.status)+'</span>'
  +'<small>來源：'+esc(source.source)+'｜資料日 '+esc(source.date||'待核對')+'</small>'
  +'<small>結構依據：'+esc(source.text)+'</small>'
  +'<small>觸發：'+esc(z?.validation_condition||'待量價／收盤確認')+'</small>'
  +'</div>';
}
function detailHtml(p){
 if(!p)return '';
 const steps=p.steps.map((s,i)=>'<div class="swing-path-step '+esc(s.state)+'"><span class="swing-path-count">'+(i+1)+'</span><span>'+esc(s.name)+'</span><b>'+esc(s.value)+'</b><small>'+esc(s.hint)+'</small></div>').join('');
 return '<section class="swing-path-detail isd-section" data-swing-path aria-label="犬子波段路徑">'
  +'<header><h3>犬子波段路徑</h3><span class="swing-path-stage '+esc(p.kind)+'">'+esc(p.phase)+'</span></header>'
  +'<p class="swing-path-note">現在的位置 → 首要關卡 → 回測驗證 → 後續觀察；關卡不是保證會到的目標。</p>'
  +'<div class="swing-path-steps">'+steps+'</div>'
  +'<div class="swing-path-action"><b>現在需要做什麼</b><span>'+esc(p.action)+'</span></div>'
  +'<div class="swing-path-checks"><b>關卡升級需四項同時核對</b><div>'
  +p.checks.map(c=>'<span class="'+(c.passed?'passed':'pending')+'">'+(c.passed?'✓ ':'○ ')+esc(c.name)+' · '+esc(c.desc)+'</span>').join('')
  +'</div><small>'+esc(p.promotionReady?'完整觸發與回測證據已核對，仍須自行確認盤面':'尚未取得完整突破＋回測雙確認，不能升級成已成立訊號')+'</small></div>'
  +'<div class="swing-path-action risk"><b>結構失效條件</b><span>'+esc(p.invalidation)+'</span></div>'
  +'<details class="swing-path-sources"><summary>關卡來源與驗證狀態</summary><div class="swing-path-sources-grid">'
  +sourceCard(p.support,'S1')+sourceCard(p.resistance,'R1')+sourceCard(p.extension,'R2')
  +'</div><p class="swing-path-note">60分K：'+esc(p.h60valid?'同交易日結構可核對，仍須確認收盤與交叉方向':'未取得同交易日完整20T／60T證據')
  +'；法人：'+esc(p.chipSame?'外資與投信日期一致，仍需檢查方向及借券':'法人日期不一致，禁止當日共振結論')
  +'。模型生成價區不是直接交易指令；缺失價區不補猜。</p></details>'
  +'</section>';
}
window.InukoSwingPath={version:'1.0',evaluate,compactHtml,detailHtml,zoneEvidence};
})();
