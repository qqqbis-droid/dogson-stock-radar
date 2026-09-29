const CD3={manifest:null,build:null,data:new Map(),scheduled:false};
const C3_BUCKET={TRIGGER_READY:'觸發就緒',WAIT_TRIGGER:'等待觸發',TREND_MONITOR:'趨勢追蹤',WAIT_PULLBACK:'等待回踩',RESEARCH_ONLY:'研究觀察',NEXT_DAY_READY:'明日候選',BREAKOUT_WATCH:'突破觀察',PULLBACK_WATCH:'回踩觀察',TREND_QUALITY:'趨勢品質',RESEARCH:'研究觀察',RISK:'風險優先',ACTIONABLE_NOW:'可執行',NO_TRADE:'不交易',STALE:'資料失效'};
const C3_ACTION={WATCH:'觀察',WAIT_TRIGGER:'等觸發',SMALL_TEST:'小量試單候選',WAIT_PULLBACK:'等回踩',HOLD:'續抱',ADD_ON_CONFIRM:'確認後加碼候選',DO_NOT_CHASE:'過熱不追',REDUCE_WATCH:'減碼觀察',EXIT_PRIORITY:'優先出場',DATA_STALE:'資料失效'};
const C3_DATA={intraday:{index:'decision_intraday_index',evidence:'stock_detail_intraday'},close:{index:'decision_close_index',evidence:'stock_detail_close'},daytrade:{index:'decision_daytrade_index',evidence:'stock_detail_daytrade'}};
const c3view=()=>document.querySelector('.tab.active')?.dataset.view||'intraday';
const c3num=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const c3price=v=>c3num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:2});
const c3pct=v=>c3num(v)==null?'—':`${Number(v)>0?'+':''}${Number(v).toFixed(2)}%`;
const c3compact=v=>c3num(v)==null?'—':new Intl.NumberFormat('zh-TW',{notation:'compact',maximumFractionDigits:1}).format(Number(v));
async function c3json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
async function c3manifest(){const m=await c3json(`./data/current_manifest.json?t=${Date.now()}`);if(CD3.build!==m.active_build_id){CD3.data.clear();CD3.build=m.active_build_id}CD3.manifest=m;return m}
async function c3set(m,key){if(!key||!m.datasets?.[key])return null;const ck=`${m.active_build_id}:${key}`;if(CD3.data.has(ck))return CD3.data.get(ck);const x=await c3json(m.datasets[key].url);CD3.data.set(ck,x);return x}
function c3latestClose(m,d){if(!m||!d)return false;const date=String(d.as_of||d.quote?.quote_time||'').slice(0,10);return c3view()==='close'&&date===String(m.trade_date||'').slice(0,10)&&['POST_CLOSE','NEXT_DAY','CLOSE_FREEZE'].includes(m.session_phase)&&c3num(d.data_confidence)>=80&&c3num(d.component_coverage)>=80}
function c3quote(q){const p=c3num(q?.price),chg=c3num(q?.day_change_pct),cls=chg==null?'flat':chg>0?'rise':chg<0?'fall':'flat';let vol='量資料待補';if(c3num(q?.relative_volume)!=null)vol=`量比 ${Number(q.relative_volume).toFixed(1)}x`;else if(c3num(q?.volume)!=null){const unit=q.volume_unit==='SHARES'?'股':q.volume_unit==='LOTS'?'張':'';vol=`量 ${c3compact(q.volume)}${unit}`};const turnover=c3num(q?.turnover_value_twd)!=null?`<div class="quote-turnover">成交值 ${c3compact(q.turnover_value_twd)}元</div>`:'';return `<div class="quote-price">${c3price(p)}</div><div class="quote-change ${cls}">${c3pct(chg)}</div><div class="quote-volume">${vol}</div>${turnover}`}
function c3text(el,value){if(el&&el.textContent!==value)el.textContent=value}
async function c3normalize(){const view=c3view();if(view==='portfolio')return;const cfg=C3_DATA[view];if(!cfg)return;const m=await c3manifest(),[rows,ep]=await Promise.all([c3set(m,cfg.index),c3set(m,cfg.evidence).catch(()=>null)]),map=new Map((Array.isArray(rows)?rows:[]).map(x=>[String(x.code),x])),emap=ep?.items||{};for(const card of document.querySelectorAll('#cards .card[data-code]')){const d=map.get(String(card.dataset.code));if(!d)continue;const e=emap[String(d.code)]||null,latest=c3latestClose(m,d),group=d.primary_group||e?.sector_score_label||'族群待補',bucket=C3_BUCKET[d.opportunity_bucket]||d.opportunity_bucket||'—';c3text(card.querySelector('.identity .muted'),`${group} · ${bucket}`);
    let line=card.querySelector('.quote-strip');if(!line){line=document.createElement('div');line.className='quote-strip';const action=card.querySelector('.action-line');action?card.insertBefore(line,action):card.appendChild(line)}const qhtml=c3quote(d.quote||{});if(line.innerHTML!==qhtml)line.innerHTML=qhtml;
    if(latest&&d.action_state==='DATA_STALE'){card.classList.remove('stale');card.classList.add('wait');const action=card.querySelector('.action-line');if(action){action.classList.remove('stale');action.classList.add('wait');c3text(action.querySelector('b'),C3_ACTION.WATCH);c3text(action.querySelector('small'),'收盤定格')}const blocker=card.querySelector('.blocker');if(blocker&&/資料不是目前可執行快照|資料失效|過期/.test(blocker.textContent))c3text(blocker,'卡點：明日仍需重新確認即時 Trigger 與量價');}
  }}
function c3schedule(){if(CD3.scheduled)return;CD3.scheduled=true;setTimeout(()=>{CD3.scheduled=false;c3normalize().catch(err=>console.warn('card-display-v3',err))},0)}
const c3cards=document.querySelector('#cards');if(c3cards)new MutationObserver(c3schedule).observe(c3cards,{childList:true,subtree:true});
document.addEventListener('click',e=>{if(e.target.closest?.('.tab')||e.target.closest?.('#loadMore')||e.target.closest?.('#refreshBtn')){if(e.target.closest?.('#refreshBtn')){CD3.manifest=null;CD3.build=null;CD3.data.clear()}setTimeout(c3schedule,30)}},true);
document.querySelector('#searchInput')?.addEventListener('input',c3schedule);
document.querySelector('#stageFilter')?.addEventListener('change',c3schedule);
document.querySelector('#actionFilter')?.addEventListener('change',c3schedule);
c3schedule();
