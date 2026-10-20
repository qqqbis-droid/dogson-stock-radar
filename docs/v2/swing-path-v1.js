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
function zoneDistance(z,quote){
 if(!z||!(quote>0))return null;
 return quote<z.low?(z.low-quote)/quote*100:quote>z.high?(z.high-quote)/quote*100:0;
}
function positionLens(quote,support,resistance){
 if(!(quote>0)||!support||!resistance||!(resistance.high>support.low))return null;
 const low=n(support.low),high=n(resistance.high);
 if(low==null||high==null||high<=low)return null;
 return {low,high,pct:Math.max(0,Math.min(100,(quote-low)/(high-low)*100)),
  rawPct:(quote-low)/(high-low)*100,
  position:quote>high?'區間上方':quote<low?'區間下方':(quote-low)/(high-low)>=.8?'靠近上緣':(quote-low)/(high-low)<=.2?'靠近下緣':'區間中段',
  nearSupport:zoneDistance(support,quote),nearResistance:zoneDistance(resistance,quote)};
}
function evidenceScore(z){
 if(!z)return null;
 const families=Array.isArray(z.evidence_families)?[...new Set(z.evidence_families.filter(Boolean))]:[];
 const confidence=n(z.confidence),strength=n(z.strength);
 return {families,independent:families.length,confidence,strength,
  labels:(Array.isArray(z.evidence)?z.evidence:[]).filter(Boolean).slice(0,8)};
}
function marketFacts(shard,known,date){
 const e=shard?.evidence||{},q=shard?.decision?.quote||{};
 if(!known)return [];
 const val=(x,d=2)=>Number(x).toLocaleString('zh-TW',{maximumFractionDigits:d});
 const facts=[];
 const volume=n(e.vol_x)??n(q.relative_volume);
 if(volume!=null)facts.push({name:'相對量',value:val(volume)+'×',meaning:volume>=1.5?'量能放大':volume<.8?'量能偏低':'量能一般'});
 const change=n(q.day_change_pct);
 if(change!=null)facts.push({name:'當日漲跌',value:(change>0?'+':'')+val(change)+'%',meaning:'當日價格變化，不代表原因'});
 const rsi=n(e.rsi14)??n(e.rsi_14);
 if(rsi!=null)facts.push({name:'RSI(14)',value:val(rsi,1),meaning:rsi>=70?'偏熱':rsi>=50?'相對偏強':'動能偏弱'});
 if(e.foreign_date&&day(e.foreign_date)===date&&n(e.foreign_net)!=null)
  facts.push({name:'外資',value:val(e.foreign_net,0),meaning:'同日淨買賣（單位依來源）'});
 return facts.slice(0,4);
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
 const lens=known?positionLens(quote,support,resistance):null;
 const zoneDiagnostics=[['S1',support],['R1',resistance],['R2',extension]].map(([rank,z])=>({rank,zone:z,metrics:evidenceScore(z),distance:known?zoneDistance(z,quote):null}));
 const facts=marketFacts(shard,known,date);
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
 return {date,build,quote,confidence,known,sourceGood,support,resistance,extension,lens,zoneDiagnostics,facts,h60ok,h60valid,chipSame,phase,kind,action,next,invalidation,steps,view,checks,promotionReady};
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
function sourceCard(z,rank,quote){
 const metric=evidenceScore(z),distance=zoneDistance(z,quote);
 const gap=distance==null?'':distance===0?'｜現價在區間內':'｜距離 '+(distance>0?'+':'')+distance.toFixed(1)+'%';
 const counts=metric?.independent?'｜獨立證據 '+metric.independent+' 類':'｜證據種類待補';
 const trust=metric?.confidence!=null?'｜結構信心 '+metric.confidence.toFixed(0)+'/100':'';

 const source=zoneEvidence(z);
 return '<div class="swing-source-card">'
  +'<b>'+esc(rank)+'</b><strong>'+esc(fmtRange(z))+'</strong>'
  +'<span>'+esc(source.status)+esc(gap)+'</span>'
  +'<small>來源：'+esc(source.source)+'｜資料日 '+esc(source.date||'待核對')+'</small>'
  +'<small>結構依據：'+esc(source.text)+esc(counts)+esc(trust)+'</small>'
  +'<small>觸發：'+esc(z?.validation_condition||'待量價／收盤確認')+'</small>'
  +'</div>';
}
function detailHtml(p){
 const lens=p.lens;
 const positionHtml=lens?'<div class="swing-location"><div class="swing-location-head"><b>價格結構位置</b><span>'+esc(price(lens.low))+'～'+esc(price(lens.high))+'</span></div><div class="swing-location-track" role="img" aria-label="在已驗證支撐與壓力區間中位於'+esc(lens.pct.toFixed(0))+'%"><i style="left:'+lens.pct.toFixed(1)+'%"></i></div><div class="swing-location-caption"><span>'+esc(lens.position)+' · '+lens.pct.toFixed(0)+'%</span><span>距 R1 '+(lens.nearResistance==null?'—':lens.nearResistance.toFixed(1)+'%')+'</span></div><small>僅反映同日有效 S1／R1 的位置，非超買判定或買賣建議。</small></div>'
  :'<div class="swing-location pending"><b>價格位置待核對</b><small>未具備同版本 S1 與 R1；不虛構區間比例，創高股改看回測路徑。</small></div>';
 const facts=p.facts?.length?'<div class="swing-facts"><b>今日發生什麼？（事實，非因果）</b><div>'+p.facts.map(f=>'<span><small>'+esc(f.name)+'</small><strong>'+esc(f.value)+'</strong><small>'+esc(f.meaning)+'</small></span>').join('')+'</div><small>只列資料日 '+esc(p.date)+' 有效來源；新聞與法人日期不符不推論原因。</small></div>':'';

 if(!p)return '';
 const steps=p.steps.map((s,i)=>'<div class="swing-path-step '+esc(s.state)+'"><span class="swing-path-count">'+(i+1)+'</span><span>'+esc(s.name)+'</span><b>'+esc(s.value)+'</b><small>'+esc(s.hint)+'</small></div>').join('');
 return '<section class="swing-path-detail isd-section" data-swing-path aria-label="犬子波段路徑">'
  +'<header><h3>犬子波段路徑</h3><span class="swing-path-stage '+esc(p.kind)+'">'+esc(p.phase)+'</span></header>'
  +'<p class="swing-path-note">現在的位置 → 首要關卡 → 回測驗證 → 後續觀察；關卡不是保證會到的目標。</p>'
  +positionHtml+facts+'<div class="swing-path-steps">'+steps+'</div>'
  +'<div class="swing-path-action"><b>現在需要做什麼</b><span>'+esc(p.action)+'</span></div>'
  +'<div class="swing-path-checks"><b>關卡升級需四項同時核對</b><div>'
  +p.checks.map(c=>'<span class="'+(c.passed?'passed':'pending')+'">'+(c.passed?'✓ ':'○ ')+esc(c.name)+' · '+esc(c.desc)+'</span>').join('')
  +'</div><small>'+esc(p.promotionReady?'完整觸發與回測證據已核對，仍須自行確認盤面':'尚未取得完整突破＋回測雙確認，不能升級成已成立訊號')+'</small></div>'
  +'<div class="swing-path-action risk"><b>結構失效條件</b><span>'+esc(p.invalidation)+'</span></div>'
  +'<details class="swing-path-sources"><summary>關卡來源與驗證狀態</summary><div class="swing-path-sources-grid">'
  +sourceCard(p.support,'S1',p.quote)+sourceCard(p.resistance,'R1',p.quote)+sourceCard(p.extension,'R2',p.quote)
  +'</div><p class="swing-path-note">60分K：'+esc(p.h60valid?'同交易日結構可核對，仍須確認收盤與交叉方向':'未取得同交易日完整20T／60T證據')
  +'；法人：'+esc(p.chipSame?'外資與投信日期一致，仍需檢查方向及借券':'法人日期不一致，禁止當日共振結論')
  +'。模型生成價區不是直接交易指令；缺失價區不補猜。</p></details>'
  +'</section>';
}
window.InukoSwingPath={version:'1.0',evaluate,compactHtml,detailHtml,zoneEvidence};
})();
