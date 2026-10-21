const MCR={build:null,manifest:null,cache:new Map(),members:null,marketDetail:null,openMarket:false};
const MCFG={
  intraday:{market:'market_intraday_context',capital:'capital_intraday_context',capitalTitle:'即時族群動能',memberKey:'intraday'},
  daytrade:{market:'market_intraday_context',capital:'capital_intraday_context',capitalTitle:'即時族群動能',memberKey:'intraday'},
  close:{market:'market_close_context',capital:'capital_close_context',capitalTitle:'法人資金流向',memberKey:'close'},
  portfolio:{market:'market_close_context',capital:'capital_close_context',capitalTitle:'法人資金背景',memberKey:'close'}
};
const MREG={BROAD_RISK_ON:'全面偏多',SELECTIVE_RISK_ON:'選股偏多',NEUTRAL:'中性',DEFENSIVE:'防守',RISK_OFF:'風險關閉'};
const MFRESH={LIVE:'即時',FRESH:'盤後定格',FROZEN:'收盤定格',STALE:'過期',UNKNOWN:'未知'};
const MPHASE={PRE_OPEN:'盤前',LIVE:'盤中',CLOSE_FREEZE:'收盤定格',POST_CLOSE:'盤後',NEXT_DAY:'隔日準備'};
const mview=()=>document.querySelector('.tab.active')?.dataset.view||'intraday';
const mesc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const mn=v=>v==null||v===''||Number.isNaN(Number(v))?null:Number(v);
const mfmt=(v,d=1)=>mn(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const msigned=(v,d=1,s='')=>mn(v)==null?'—':`${Number(v)>0?'+':''}${mfmt(v,d)}${s}`;
const mmoney=v=>mn(v)==null?'—':`${Number(v)>0?'+':''}${mfmt(v,1)}億`;
const mlots=v=>mn(v)==null?'—':`${Number(v)>0?'+':''}${mfmt(v,1)}張`;
const mtime=v=>{const s=String(v||'');if(!s)return'—';return s.includes('T')?s.replace('T',' ').slice(0,16):s};
async function mjson(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
async function mmanifest(){const m=await mjson(`./data/current_manifest.json?t=${Date.now()}`);if(MCR.build!==m.active_build_id){MCR.build=m.active_build_id;MCR.cache.clear();MCR.members=null;MCR.marketDetail=null}MCR.manifest=m;return m}
async function mset(m,key){const meta=m.datasets?.[key];if(!meta)throw new Error(`manifest 缺少 ${key}`);const ck=`${m.active_build_id}:${key}`;if(MCR.cache.has(ck))return MCR.cache.get(ck);const obj=await mjson(meta.url);if(obj?.build_id&&obj.build_id!==m.active_build_id)throw new Error(`${key} build_id 不一致`);MCR.cache.set(ck,obj);return obj}
async function companion(name){try{const obj=await mjson(`./data/${name}?t=${Date.now()}`);if(obj?.build_id&&MCR.build&&obj.build_id!==MCR.build)return null;return obj}catch{return null}}
function style(){if(document.getElementById('marketCapitalRendererStyle'))return;const st=document.createElement('style');st.id='marketCapitalRendererStyle';st.textContent=`
.market-pulse{display:grid;grid-template-columns:1.2fr .7fr 1fr 1fr;gap:6px;padding:7px 10px;margin:0;background:#253c33;color:#fff;font-size:.72rem;align-items:center}.market-pulse b{font-size:.8rem}.market-pulse span{opacity:.82}.market-pulse .rise{color:#ffb5ad}.market-pulse .fall{color:#9fddbd}.mc-score-card{padding:8px 9px;border:1px solid #e2e7e3;border-radius:10px;background:#fff}.mc-score-card b{display:flex;justify-content:space-between;gap:8px;font-size:.84rem}.mc-score-card small{display:block;margin-top:4px;color:#718078;line-height:1.35;font-size:.75rem}.mc-clock{margin-top:7px;padding:7px 9px;background:#f5f7f4;border-radius:9px;font-size:.76rem;color:#65746d;line-height:1.45}.capital-chip{cursor:pointer}.capital-chip:focus{outline:2px solid #7aa996;outline-offset:2px}.capital-more{margin-top:7px;padding-top:7px;border-top:1px dashed #dfe5df;font-size:.78rem;line-height:1.5;color:#61716a}.capital-more[hidden]{display:none}.capital-more .mc-row{display:flex;justify-content:space-between;gap:10px}.capital-hint{font-size:.72rem;color:#809089;margin-top:4px}.member-list{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.member-btn{border:1px solid #d9e2dc;background:#fff;border-radius:999px;padding:6px 9px;font-size:.74rem;color:#355247}.member-btn:active{transform:scale(.98)}.capital-verification-note{grid-column:1/-1;padding:11px 12px;border-radius:11px;background:var(--soft);border:1px solid var(--line);font-size:.75rem;line-height:1.55}.capital-verification-note b{font-size:.85rem}.capital-estimates{grid-column:1/-1;min-width:0;border:1px solid var(--line);padding:10px;border-radius:12px}.capital-estimates>summary{font-size:.8rem;font-weight:850;cursor:pointer}.capital-estimate-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:10px}.capital-estimate-list .capital-chip{min-width:0}.capital-estimate-list .capital-chip>.capital-hint{overflow-wrap:anywhere}@media(max-width:390px){.capital-estimate-list{grid-template-columns:1fr}}.capital-section-label{flex-basis:100%;font-size:.72rem;color:#75837c;margin:2px 0 0}
@media(max-width:560px){.market-pulse{grid-template-columns:1fr 1fr 1fr;font-size:.68rem}.market-pulse .pulse-time{display:none}}
`;document.head.appendChild(st)}
function mcomponentName(k){return k==='taiex'?'加權':k==='otc'?'櫃買':k==='breadth'?'市場廣度':k==='funds'?'資金動能':k==='sector'?'族群擴散':'官方外資'}
function mwhy(intra,k,x,m){const q=m.metrics||{};if(intra){if(k==='taiex'||k==='otc'){return `${k==='taiex'?'加權':'櫃買'} ${msigned(x.change_pct,2,'%')}；站VWAP成交額 ${mfmt(x.above_vwap_pct)}%；上漲家數 ${mfmt(x.breadth_pct)}%。`}if(k==='breadth')return `雷達池上漲家數 ${mfmt(q.breadth_up_pct)}%；≥60%得3分、≥55%得2.5、≥50%得1.8、≥45%得0.8。`;if(k==='funds')return `上漲股成交額 ${mfmt(q.turnover_up_pct)}%；站VWAP成交額 ${mfmt(q.above_vwap_turnover_pct)}%；量速 ${mfmt(q.weighted_pace,2)}x。`;if(k==='sector')return `正向族群 ${mfmt(q.sector_positive_pct)}%；正向 ${mfmt(q.sector_positive_count,0)} 個、負向 ${mfmt(q.sector_negative_count,0)} 個。`}else{if(k==='taiex'||k==='otc')return `${x.trend?'趨勢多頭':x.above20?'仍在20日線上':'未符合趨勢條件'}；依趨勢與20日線位置給分。`;if(k==='breadth')return `上漲家數 ${mfmt(q.breadth_up_pct)}%；≥60%得3分、≥55%得2.5、≥50%得1.5、≥45%得0.5。`;if(k==='foreign')return `外資今日 ${mmoney(q.foreign_net_billion)}，5日 ${mmoney(q.foreign_5d_billion)}。`}return''}
function mcomponent(comps,k,max,intra,m){const x=comps?.[k]||{};return `<div class="mc-score-card"><b><span>${mesc(mcomponentName(k))}</span><span>${mfmt(x.score)}/${mfmt(x.max??max,0)}</span></b><small>${mesc(mwhy(intra,k,x,m))}</small></div>`}
function pulse(view,m,raw){const box=document.getElementById('marketPulse');if(!box)return;const ta=raw?.taiex||{},ot=raw?.otc||{},intra=m.context==='INTRADAY',tc=intra?(m.components?.taiex?.change_pct):ta.change_pct,oc=intra?(m.components?.otc?.change_pct):ot.change_pct,tone=v=>mn(v)==null?'':Number(v)>0?'rise':Number(v)<0?'fall':'';box.innerHTML=`<div><span>市場</span><br><b>${mesc(MREG[m.market_regime]||m.market_regime||'—')}</b></div><div><span>環境分</span><br><b>${mfmt(m.market_score)}/15</b></div><div><span>加權</span><br><b class="${tone(tc)}">${msigned(tc,2,'%')}</b></div><div><span>櫃買</span><br><b class="${tone(oc)}">${msigned(oc,2,'%')}</b></div><div class="pulse-time"><span>${mesc(MFRESH[m.freshness]||m.freshness||'—')} · ${mesc(mtime(m.as_of))}</span></div>`}
function renderMarket(view,m,raw){const box=document.getElementById('marketSummary'),detail=document.getElementById('marketDetail');if(!box||!detail)return;const intra=m.context==='INTRADAY',metrics=m.metrics||{},comps=m.components||{},model=intra?'盤中15分：加權3＋櫃買3＋廣度3＋資金動能4＋族群擴散2':'盤後15分：加權5＋櫃買4＋廣度3＋官方外資3';box.innerHTML=`<div class="market-grid"><div class="metric"><span>市場環境</span><b>${mesc(MREG[m.market_regime]||m.market_regime||'—')}</b></div><div class="metric"><span>市場分</span><b>${mfmt(m.market_score)}<small>/15</small></b></div><div class="metric"><span>資料信心</span><b>${mfmt(m.market_confidence,0)}<small>%</small></b></div></div><div class="data-line"><span class="fresh ${String(m.freshness||'').toLowerCase()}">${mesc(MFRESH[m.freshness]||m.freshness||'—')}</span><span>${mesc(model)}</span></div>${intra?'<div class="capital-hint">報價約5分鐘更新；VWAP／量速／族群結構約10分鐘更新，時間分開顯示。</div>':''}`;const cards=intra?[mcomponent(comps,'taiex',3,true,m),mcomponent(comps,'otc',3,true,m),mcomponent(comps,'breadth',3,true,m),mcomponent(comps,'funds',4,true,m),mcomponent(comps,'sector',2,true,m)]:[mcomponent(comps,'taiex',5,false,m),mcomponent(comps,'otc',4,false,m),mcomponent(comps,'breadth',3,false,m),mcomponent(comps,'foreign',3,false,m)];const metricText=intra?`上漲股成交額 ${mfmt(metrics.turnover_up_pct)}%｜站VWAP成交額 ${mfmt(metrics.above_vwap_turnover_pct)}%｜量速 ${mfmt(metrics.weighted_pace,2)}x`:`外資今日 ${mmoney(metrics.foreign_net_billion)}｜上市 ${mmoney(metrics.foreign_twse_billion)}｜上櫃 ${mmoney(metrics.foreign_tpex_billion)}｜5日 ${mmoney(metrics.foreign_5d_billion)}`;const clocks=intra?`<div class="mc-clock"><b>資料時鐘</b><br>報價快照：${mesc(mtime(metrics.quote_snapshot_time||m.as_of))}<br>最後成交：${mesc(mtime(metrics.latest_trade_time||'—'))}<br>VWAP／量速／族群：${mesc(mtime(metrics.structure_latest_time||'—'))}</div>`:`<div class="mc-clock"><b>盤後定格</b><br>交易日：${mesc(m.trade_date||String(m.as_of||'').slice(0,10)||'—')}<br>收盤資料：${mesc(mtime(m.as_of))}<br>最後補齊：${mesc(mtime(m.known_at||m.as_of))}</div>`;detail.innerHTML=`<div class="detail-grid">${cards.join('')}</div><div class="data-line"><span>${mesc(metricText)}</span></div>${clocks}`;detail.classList.toggle('open',MCR.openMarket);pulse(view,m,raw)}
function membersFor(view,group){const cfg=MCFG[view]||MCFG.intraday,groups=MCR.members?.[cfg.memberKey]?.groups||{};return Array.isArray(groups[group])?groups[group]:[]}
function memberButtons(view,group){const xs=membersFor(view,group),shown=xs.slice(0,24);if(!xs.length)return'<div class="capital-hint capital-member-fallback">成分股清單待載入；若已有逐檔法人明細，請直接查看下方列表。</div>';return `<div class="capital-section-label">查看族群個股（${xs.length}檔）</div><div class="member-list">${shown.map(x=>`<button class="member-btn" data-stock-code="${mesc(x.code)}" type="button">${mesc(x.code)} ${mesc(x.name)}</button>`).join('')}</div>${xs.length>shown.length?`<div class="capital-hint">先顯示前 ${shown.length} 檔；可用下方搜尋直接找其餘個股。</div>`:''}`}
// A recent BUILD date is NOT proof that the institutional flow amount is
// from that completed trading session, nor that the member books reconcile.
// Only one same-day, member-complete and explicitly reconciled group enters
// the verified institutional flow ranking.
function closeRankInfo(x,ledger,day){
 const sourceDay=String(x?.latest_date||'').slice(0,10);
 const row=ledger?.groups?.[String(x?.primary_group||'')];
 const ledgerDay=String(ledger?.trade_date||'').slice(0,10);
 const members=Number(row?.member_count)||0;
 const verified=Number(row?.verified_count)||0;
 const ratio=members>0?verified/members*100:null;
 const amount=mn(row?.rank_amount_100m),lots=mn(row?.rank_lots);
 const status=String(row?.rank_status||'INCOMPLETE');
 const confirmed=Boolean(day&&ledgerDay===day&&sourceDay===day
   &&row?.reconciled===true&&status==='RECONCILED'
   &&members>0&&verified===members&&amount!=null&&lots!=null);
 const rebuilt=Boolean(day&&ledgerDay===day&&sourceDay&&sourceDay<day
   &&row?.rank_full_member_coverage===true
   &&status==='REBUILT_ALL_MEMBERS'
   &&members>0&&verified===members&&amount!=null&&lots!=null);
 const rankEligible=Boolean(day&&row?.rank_eligible===true
   &&row?.rank_trade_date===day&&(confirmed||rebuilt));
 // 60%-covered individual-stock samples NEVER qualify for a sector rank.
 const sampleAmount=mn(row?.sample_amount_100m);
 const sampleReady=Boolean(!rankEligible&&ledgerDay===day&&row?.sample_trade_date===day
   &&row?.sample_scope==='SAME_DAY_MATCHED_STOCKS_ONLY'
   &&row?.sample_eligible===true&&members>=3&&verified>=3&&ratio>=60
   &&sampleAmount!=null&&mn(row?.sample_lots)!=null);
 return {confirmed,rebuilt,rankEligible,rankAmount:amount,rankLots:lots,
   rankStatus:status,sourceDay:sourceDay||'',members,verified,ratio,
   sampleReady,sampleAmount,sampleLots:mn(row?.sample_lots)};
}
function flowAuditText(x,info){
 const date=info.sourceDay||'無日期';
 const measured=info.ratio==null
   ?'逐檔有效數：'+info.verified+'/'+info.members+'（成分清單不足）'
   :'逐檔有效：'+info.verified+'/'+info.members+'（'+mfmt(info.ratio,0)+'%）';
 return '法人來源日 '+date+' · '+measured;
}
function closeMore(view,x){return `<div class="capital-more" hidden><div class="mc-row"><span>來源日 ${mesc(x.latest_date||'未確認')} 估算金額</span><b>${mmoney(x.today_amount_100m)}</b></div><div class="mc-row"><span>來源日估算張數</span><b>${mlots(x.today_lots)}</b></div><div class="mc-row"><span>5日累計</span><b>${mmoney(x.net5_amount_100m)}／${mlots(x.net5_lots)}</b></div><div class="mc-row"><span>20日累計</span><b>${mmoney(x.net20_amount_100m)}／${mlots(x.net20_lots)}</b></div><div class="mc-row"><span>連續方向</span><b>${mesc(x.flow_direction||'—')} ${x.flow_streak?`${Math.abs(x.flow_streak)}日`:''}</b></div><div class="mc-row"><span>加速</span><b>${x.accelerating?'是':'否'}</b></div><div class="mc-row"><span>5日股價</span><b>${msigned(x.ret5_pct,1,'%')}</b></div><div class="mc-row"><span>歷史估算涵蓋（非逐檔有效）</span><b>${mfmt(x.amount_coverage_pct,0)}%</b></div><div class="capital-hint">估算：${mesc(x.amount_method||'外資＋投信淨買賣張數 × 收盤價')}；未含自營商。</div>${memberButtons(view,x.primary_group)}</div>`}
function sampleMore(view,x,a){return `<div class="capital-more" hidden><div class="mc-row"><span>同日核對樣本（外資＋投信）</span><b>${mmoney(a.sampleAmount)}</b></div><div class="mc-row"><span>同日樣本淨張數</span><b>${mlots(a.sampleLots)}</b></div><div class="mc-row"><span>有效樣本數</span><b>${a.verified}/${a.members} 檔 · ${mfmt(a.ratio,0)}%</b></div><div class="mc-row"><span>原族群彙總來源日</span><b>${mesc(a.sourceDay||'待核對')}</b></div><div class="capital-hint">金額只加總同日有效股票，未納入缺漏成分股與自營商；不能推定整個族群資金流入或流出。</div>${memberButtons(view,x.primary_group)}</div>`}
function intraMore(view,x){return `<div class="capital-more" hidden><div class="mc-row"><span>目前成交占比</span><b>${mfmt(x.turnover_share_pct)}%</b></div><div class="mc-row"><span>前一視窗</span><b>${mfmt(x.previous_share_pct)}%</b></div><div class="mc-row"><span>最近視窗</span><b>${mfmt(x.recent_share_pct)}%</b></div><div class="mc-row"><span>上漲廣度</span><b>${mfmt(x.up_pct)}%</b></div><div class="mc-row"><span>站VWAP</span><b>${mfmt(x.above_vwap_pct)}%</b></div><div class="mc-row"><span>量速</span><b>${mfmt(x.pace,2)}x</b></div>${memberButtons(view,x.primary_group)}</div>`}
function renderCapital(view,c,context={}){const box=document.getElementById('sectorList'),title=document.getElementById('capitalTitle');if(!box)return;const cfg=MCFG[view]||MCFG.intraday;if(title)title.textContent=cfg.capitalTitle;const rows=Array.isArray(c.rows)?c.rows:[];if(c.context==='INTRADAY'){const ranked=[...rows].filter(x=>mn(x.heat)!=null).sort((a,b)=>(b.heat??-99)-(a.heat??-99)),hot=ranked.slice(0,3),cool=[...ranked].reverse().filter(x=>(x.heat??0)<0).slice(0,3),one=(x,label,i)=>`<div class="chip capital-chip" tabindex="0" role="button" aria-expanded="false" data-capital-expand="${label}-${i}"><b>${label==='hot'?'🔥':'❄️'} ${mesc(x.primary_group)}</b><strong>熱度 ${msigned(x.heat,1)}</strong><div>成交占比 ${mfmt(x.turnover_share_pct)}% · Δ ${msigned(x.share_change_pp,1,'pp')}</div><div>VWAP ${mfmt(x.above_vwap_pct)}% · 廣度 ${mfmt(x.up_pct)}% · 量速 ${mfmt(x.pace,2)}x</div><div class="capital-hint">點一下看細節與族群個股</div>${intraMore(view,x)}</div>`;box.innerHTML=[...hot.map((x,i)=>one(x,'hot',i)),...cool.map((x,i)=>one(x,'cool',i))].join('')||'<span class="muted">即時族群動能待補</span>'}else{
 const day=String(context?.tradeDate||c.trade_date||'').slice(0,10);
 const ledger=context?.closeLedger||null;
 const infos=rows.map(x=>({x,info:closeRankInfo(x,ledger,day)}));
 const verified=infos.filter(t=>t.info.confirmed);
 const samples=infos.filter(t=>t.info.sampleReady);
 const waiting=infos.filter(t=>!t.info.confirmed&&!t.info.sampleReady&&mn(t.x.today_amount_100m)!=null);
 const buys=verified.filter(t=>Number(t.x.today_amount_100m)>0).sort((a,b)=>b.x.today_amount_100m-a.x.today_amount_100m).slice(0,3);
 const sells=verified.filter(t=>Number(t.x.today_amount_100m)<0).sort((a,b)=>a.x.today_amount_100m-b.x.today_amount_100m).slice(0,3);
 const one=(t,dir,i)=>{const x=t.x,a=t.info;return `<div class="chip capital-chip" tabindex="0" role="button" aria-expanded="false" data-capital-expand="${dir}-${i}" data-capital-group="${mesc(x.primary_group)}"><b>${dir==='in'?'🔴':'🟢'} ${mesc(x.primary_group)}</b><strong>${mmoney(x.today_amount_100m)}</strong><div class="capital-hint">已核對 · ${mesc(flowAuditText(x,a))}</div><div>${mesc(x.flow_text||'族群法人淨額')} ${x.accelerating?'· 加速':''}</div><div class="capital-hint">歷史估算金額覆蓋 ${mfmt(x.amount_coverage_pct,0)}%（非逐檔覆蓋率）</div><div class="capital-hint">點一下看法人明細與族群個股</div>${closeMore(view,x)}</div>`};
 const pendingOne=(t,i)=>{const x=t.x,a=t.info;const previous=a.sourceDay&&a.sourceDay!==day;return `<div class="chip capital-chip" tabindex="0" role="button" aria-expanded="false" data-capital-expand="estimate-${i}" data-capital-group="${mesc(x.primary_group)}"><b>⚠ ${mesc(x.primary_group)}</b><strong>${mmoney(x.today_amount_100m)}</strong><div class="capital-hint">未完成逐檔對帳 · ${previous?'舊交易日資料，非'+mesc(day)+'今日':''} ${mesc(flowAuditText(x,a))}</div><div class="capital-hint">歷史估算資料涵蓋 ${mfmt(x.amount_coverage_pct,0)}% ≠ 法人逐檔驗證率</div>${closeMore(view,x)}</div>`};
 const sampleCard=(t,dir,i)=>{const x=t.x,a=t.info;return `<div class="chip capital-chip" tabindex="0" role="button" aria-expanded="false" data-capital-expand="sample-${dir}-${i}" data-capital-group="${mesc(x.primary_group)}"><b>${dir==='in'?'🔴':'🟢'} ${mesc(x.primary_group)}</b><strong>${mmoney(a.sampleAmount)}</strong><div class="capital-hint">當日有效個股樣本 ${a.verified}/${a.members} · ${mfmt(a.ratio,0)}%</div><div class="capital-hint">樣本淨金額估算，非全族群淨額；原彙總來源日 ${mesc(a.sourceDay||'未知')}</div><div class="capital-hint">點開查看樣本範圍及逐檔資料</div>${sampleMore(view,x,a)}</div>`};
 const sampleBuys=samples.filter(t=>t.info.sampleAmount>0).sort((a,b)=>b.info.sampleAmount-a.info.sampleAmount).slice(0,3);
 const sampleSells=samples.filter(t=>t.info.sampleAmount<0).sort((a,b)=>a.info.sampleAmount-b.info.sampleAmount).slice(0,3);
 const confirmedCards=[...buys.map((x,i)=>one(x,'in',i)),...sells.map((x,i)=>one(x,'out',i))];
 const sampleCards=[...sampleBuys.map((x,i)=>sampleCard(x,'in',i)),...sampleSells.map((x,i)=>sampleCard(x,'out',i))];
 const order=[...waiting].sort((a,b)=>Math.abs(Number(b.x.today_amount_100m))-Math.abs(Number(a.x.today_amount_100m)));
 const sample=order.slice(0,6);
 box.innerHTML=`<div class="capital-verification-note"><b>已確認當日法人流向｜${verified.length} 個族群</b><div>只計 ${mesc(day||'未知')} 當日來源、逐檔資料完整且金額／張數對帳成功的族群。</div>${verified.length?'':'<div>目前沒有通過完整對帳的族群，暫停已驗證流入／流出排行榜。</div>'}</div>`
 +confirmedCards.join('')
 +`<div class="capital-verification-note" data-same-day-sample><b>當日逐檔核對樣本｜${samples.length} 個族群</b><div>至少 3 檔、有效樣本涵蓋至少 60%；只加總核對過的同日個股外資＋投信淨額。這不是全族群淨額，也不冒充完整對帳。</div>${samples.length?'':'<div>尚無達最低覆蓋門檻的當日樣本；已保留下方待查來源。</div>'}</div>`
 +sampleCards.join('')
 +`<details class="capital-estimates"><summary>未對帳估算參考（非已驗證排行） · ${waiting.length} 個族群</summary><div class="capital-hint">保留估算供研究，不視為今日法人買賣排行；下列依估算絕對金額列出前 ${sample.length} 個供查核，每檔顯示實際來源日期。</div><div class="capital-estimate-list">${sample.map(pendingOne).join('')}</div>${waiting.length>sample.length?'<div class="capital-hint">其他未對帳族群暫不列入已驗證排行；等待來源補齊。</div>':''}</details>`;
 }
}
async function render(){try{style();const view=mview(),cfg=MCFG[view]||MCFG.intraday,m=await mmanifest();const [market,capital,members,raw,ledger]=await Promise.all([mset(m,cfg.market),mset(m,cfg.capital),MCR.members?Promise.resolve(MCR.members):companion('sector-members.json'),MCR.marketDetail?Promise.resolve(MCR.marketDetail):companion('market-detail.json'),(view==='close'||view==='portfolio')?mset(m,'capital_close_members').catch(()=>null):Promise.resolve(null)]);if(members)MCR.members=members;if(raw)MCR.marketDetail=raw;renderMarket(view,market,raw?.payload||null);renderCapital(view,capital,{closeLedger:ledger,tradeDate:String(m.datasets?.capital_close_context?.as_of||m.trade_date||'').slice(0,10)})}catch(err){console.error('market-capital-renderer',err);const b=document.getElementById('healthBanner');if(b){b.classList.remove('hidden');b.textContent='市場／資金資料載入失敗；個股資料仍可查看，但請先不要把市場區當成最新狀態。'}}}
function toggle(el){const more=el?.querySelector('.capital-more');if(!more)return;const open=more.hasAttribute('hidden');if(open)more.removeAttribute('hidden');else more.setAttribute('hidden','');el.setAttribute('aria-expanded',open?'true':'false')}
document.addEventListener('click',e=>{const member=e.target.closest?.('[data-stock-code]');if(member){e.stopPropagation();document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code:member.dataset.stockCode}}));return}const cap=e.target.closest?.('[data-capital-expand]');if(cap){toggle(cap);return}if(e.target.id==='marketToggle'){MCR.openMarket=!MCR.openMarket;document.getElementById('marketDetail')?.classList.toggle('open',MCR.openMarket);e.target.textContent=MCR.openMarket?'收合細節':'查看細節'}});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches?.('[data-capital-expand]')){e.preventDefault();toggle(e.target)}});
document.addEventListener('radar:view-rendered',render);
document.addEventListener('radar:data-reloaded',()=>{MCR.build=null;MCR.manifest=null;MCR.cache.clear();MCR.members=null;MCR.marketDetail=null;render()});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',render);else setTimeout(render,0);
