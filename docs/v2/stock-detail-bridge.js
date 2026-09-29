const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const num=v=>Number.isFinite(Number(v))?Number(v):null;
const fmt=(v,d=1)=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const price=v=>num(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:2});
const stage=v=>({OBSERVE:'觀察',SETUP:'蓄勢待發',LAUNCH:'剛啟動',TREND:'趨勢持有',PULLBACK_TEST:'回踩觀察',PULLBACK_CONFIRMED:'回踩承接',WEAKENING:'轉弱警戒',FAILED:'結構失效'}[v]||v||'—');
const action=v=>({WATCH:'觀察',WAIT_TRIGGER:'等觸發',SMALL_TEST:'小量試單候選',WAIT_PULLBACK:'等回踩',HOLD:'續抱',ADD_ON_CONFIRM:'確認後加碼候選',DO_NOT_CHASE:'過熱不追',REDUCE_WATCH:'減碼觀察',EXIT_PRIORITY:'優先出場',DATA_STALE:'資料失效'}[v]||v||'—');
const fresh=v=>({LIVE:'即時',FRESH:'新鮮',FROZEN:'收盤定格',STALE:'過期',UNKNOWN:'未知'}[v]||v||'—');
const cfg={
  intraday:{detail:'decision_intraday_detail',zone:'zone_intraday'},
  close:{detail:'decision_close_detail',zone:'zone_close'},
  daytrade:{detail:'decision_daytrade_detail',zone:'zone_daytrade'}
};
async function j(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
function resolveTone(d){if(d.action_state==='DATA_STALE')return'stale';if(['EXIT_PRIORITY','REDUCE_WATCH'].includes(d.action_state)||['FAILED','WEAKENING'].includes(d.lifecycle_stage))return'risk';if(d.actionable)return'go';return'wait'}
function list(title,items,empty='無'){return `<div class="detail-block"><h3>${esc(title)}</h3><div class="detail-list">${items?.length?items.map(x=>`<span>${esc(x)}</span>`).join(''):`<span class="muted">${esc(empty)}</span>`}</div></div>`}
function zoneCard(title,z,tone){if(!z)return `<div class="zone-card empty"><span>${esc(title)}</span><b>資料待補</b><small>沒有可信結構區間時不猜單一價位</small></div>`;const r=z.low===z.high?price(z.center):`${price(z.low)}–${price(z.high)}`;return `<div class="zone-card ${tone}"><span>${esc(title)}</span><b>${r}</b><small>${(z.evidence||[]).length?esc(z.evidence.join('＋')):'結構區間'}${z.strength!=null?` · 強度 ${fmt(z.strength)}`:''}</small></div>`}
async function openFull(code){
  const view=$('.tab.active')?.dataset.view||'intraday', c=cfg[view]||cfg.intraday;
  const m=await j(`./data/current_manifest.json?t=${Date.now()}`), dm=m?.datasets?.[c.detail];
  const title=$('#detailTitle'),body=$('#detailBody'),dialog=$('#detailDialog');
  if(!title||!body||!dialog)return;
  if(!dm){body.innerHTML='<div class="detail-note warn">目前這個頁面沒有完整個股資料集。</div>';return}
  body.innerHTML='<div class="muted">讀取完整個股資訊…</div>';
  const detail=await j(dm.url), d=detail?.items?.[String(code)];
  if(!d||d.build_id!==m.active_build_id){body.innerHTML='<div class="detail-note warn">找不到同一個 Atomic Build 的完整個股資料，已停止顯示避免混用。</div>';return}
  let zones=[];
  const zm=m.datasets?.[c.zone];
  if(zm){const z=await j(zm.url);if(Array.isArray(z))zones=z}
  const wanted=new Set([...(d.support_zone_ids||[]),...(d.resistance_zone_ids||[])]),mine=zones.filter(z=>wanted.has(z.zone_id)),support=mine.find(z=>z.side==='SUPPORT'),resistance=mine.find(z=>z.side==='RESISTANCE');
  const s=d.scores||{},tone=resolveTone(d),light=tone==='go'?'可執行':tone==='risk'?'風險優先':tone==='stale'?'資料失效':'先等待';
  title.textContent=`${d.code} ${d.name}`;
  body.innerHTML=`<div class="detail-hero"><div><span class="badge stage">${esc(stage(d.lifecycle_stage))}</span><h2>${esc(action(d.action_state))}</h2><p>${d.actionable?'目前通過執行 Gate':'目前僅觀察／等待，不視為可執行訊號'}</p></div><div class="detail-light ${tone}">${light}</div></div><div class="detail-score-grid"><div><span>波段品質</span><b>${fmt(s.swing_quality_score)}</b></div><div><span>盤中動能</span><b>${fmt(s.intraday_momentum_score)}</b></div><div><span>當沖分</span><b>${fmt(s.daytrade_score)}</b></div><div><span>進場位置</span><b>${fmt(s.entry_position_score)}</b></div></div><div class="detail-block"><h3>結構區間</h3><div class="zone-grid">${zoneCard('支撐區',support,'support')}${zoneCard('壓力區',resistance,'resistance')}</div><div class="zone-note">Zone 只描述結構，不等於買進指令；真正執行仍需 Trigger 與風險 Gate。</div></div>${list('為什麼現在看它',d.why_now,'目前無新增理由')}${list('現在卡在哪裡',d.blockers,'沒有額外卡點')}${list('升級條件',d.upgrade_conditions,'尚無')}${list('風險旗標',[...(d.risk_overlays||[]),...(d.risk_flags||[])],'目前無額外風險旗標')}<div class="detail-block"><h3>資料品質</h3><div class="quality-grid"><div><span>Freshness</span><b>${esc(fresh(d.freshness))}</b></div><div><span>資料信心</span><b>${fmt(d.data_confidence)}%</b></div><div><span>覆蓋率</span><b>${fmt(d.component_coverage)}%</b></div><div><span>排名</span><b>#${d.opportunity_rank??'—'}</b></div></div>${d.missing_fields?.length?`<div class="missing">缺少：${d.missing_fields.map(esc).join('、')}</div>`:''}</div><details class="engineering"><summary>資料時間與版本</summary><div>as_of：${esc(d.as_of||'—')}<br>known_at：${esc(d.known_at||'—')}<br>context：${esc(d.decision_context_id||'—')}<br>build：${esc(d.build_id||'—')}</div></details>`;
  if(!dialog.open)dialog.showModal();
}
function decorate(root=document){root.querySelectorAll?.('.sector-stock-mini').forEach(mini=>{if(mini.querySelector('.sector-stock-detail-btn'))return;const code=mini.dataset.miniCode;if(!code)return;mini.insertAdjacentHTML('beforeend',`<button type="button" class="sector-stock-detail-btn" data-full-stock="${esc(code)}">查看完整個股資訊 ›</button>`)})}
document.addEventListener('click',async e=>{const b=e.target.closest?.('.sector-stock-detail-btn');if(!b)return;e.preventDefault();e.stopPropagation();try{await openFull(b.dataset.fullStock)}catch(err){console.error(err);const body=$('#detailBody');if(body)body.innerHTML='<div class="detail-note warn">完整個股資訊載入失敗，請按更新雷達後再試。</div>'}});
const target=$('#detailBody');if(target)new MutationObserver(()=>decorate(target)).observe(target,{childList:true,subtree:true});decorate(document);
