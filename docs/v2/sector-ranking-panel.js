const SRP={build:null,cache:new Map(),activeGroup:'',activeView:''};
const SRP_CFG={
  intraday:{index:'decision_intraday_index',score:'intraday_momentum_score',label:'盤中動能'},
  close:{index:'decision_close_index',score:'swing_quality_score',label:'波段品質'},
  portfolio:{index:'decision_close_index',score:'swing_quality_score',label:'波段品質'},
  daytrade:{index:'decision_daytrade_index',score:'daytrade_score',label:'當沖分'}
};
const SRP_BUCKET={TRIGGER_READY:'觸發就緒',WAIT_TRIGGER:'等待觸發',TREND_MONITOR:'趨勢追蹤',WAIT_PULLBACK:'等待回踩',RESEARCH_ONLY:'研究觀察',NEXT_DAY_READY:'明日候選',BREAKOUT_WATCH:'突破觀察',PULLBACK_WATCH:'回踩觀察',TREND_QUALITY:'趨勢品質',RESEARCH:'研究觀察',RISK:'風險優先',ACTIONABLE_NOW:'可執行',NO_TRADE:'不交易',STALE:'資料失效'};
const srpEsc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const srpNum=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const srpFmt=(v,d=0)=>srpNum(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const srpView=()=>document.querySelector('.tab.active')?.dataset.view||'intraday';
async function srpJson(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
async function srpManifest(){const m=await srpJson(`./data/current_manifest.json?sectorRank=${Date.now()}`);if(SRP.build!==m.active_build_id){SRP.build=m.active_build_id;SRP.cache.clear()}return m}
async function srpDataset(m,key){const meta=m.datasets?.[key];if(!meta)return null;const ck=`${m.active_build_id}:${key}`;if(SRP.cache.has(ck))return SRP.cache.get(ck);const x=await srpJson(meta.url);SRP.cache.set(ck,x);return x}
async function srpMembers(){const ck=`${SRP.build}:sector-members`;if(SRP.cache.has(ck))return SRP.cache.get(ck);try{const x=await srpJson(`./data/sector-members.json?t=${Date.now()}`);if(x?.build_id&&SRP.build&&x.build_id!==SRP.build)return null;SRP.cache.set(ck,x);return x}catch{return null}}
function style(){if(document.getElementById('sectorRankingPanelStyle'))return;const s=document.createElement('style');s.id='sectorRankingPanelStyle';s.textContent=`
#sectorRankExplain[hidden]{display:none}.sector-rank-panel{margin-top:9px;padding:9px 10px;border-radius:10px;background:var(--soft);border:1px solid var(--line)}.sector-rank-head{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:6px}.sector-rank-head b{font-size:.82rem}.sector-rank-head span{font-size:.68rem;color:var(--muted)}.sector-rank-note{font-size:.7rem;color:var(--muted);line-height:1.45;margin-bottom:6px}.sector-rank-list{display:grid;gap:5px}.sector-rank-row{display:grid;grid-template-columns:auto 1fr auto;gap:7px;align-items:center;border:1px solid var(--line);background:var(--card);border-radius:9px;padding:7px 8px;cursor:pointer;text-align:left;color:var(--ink)}.sector-rank-no{font-weight:800;color:var(--green);min-width:22px}.sector-rank-id b{font-size:.76rem}.sector-rank-id small{display:block;color:var(--muted);font-size:.65rem;margin-top:2px}.sector-rank-score{text-align:right;font-size:.72rem}.sector-rank-score b{display:block;font-size:.82rem}.sector-rank-empty{font-size:.72rem;color:var(--muted);padding:7px 0}
`;document.head.appendChild(s)}
function groupFromChip(chip){const t=chip?.querySelector('b')?.textContent?.trim()||'';return t.replace(/^[^\p{L}\p{N}]+/u,'').trim()}
function memberSet(members,view,group){const key=view==='intraday'||view==='daytrade'?'intraday':'close';const rows=members?.[key]?.groups?.[group]||[];return new Set(rows.map(x=>String(x.code)))}
function sortRows(rows){return [...rows].sort((a,b)=>{const ar=srpNum(a.opportunity_rank),br=srpNum(b.opportunity_rank);if(ar!=null||br!=null)return (ar??1e9)-(br??1e9);return String(a.code).localeCompare(String(b.code))})}
async function render(group,view=srpView()){
  style();const box=document.getElementById('sectorRankExplain');if(!box)return;SRP.activeGroup=group;SRP.activeView=view;if(!group){box.hidden=true;box.innerHTML='';return}
  box.hidden=false;box.innerHTML='<div class="sector-rank-panel"><div class="sector-rank-empty">讀取族群內排序…</div></div>';
  try{
    const cfg=SRP_CFG[view]||SRP_CFG.intraday,m=await srpManifest(),[idx,members]=await Promise.all([srpDataset(m,cfg.index),srpMembers()]);
    if(SRP.activeGroup!==group||SRP.activeView!==view)return;
    const allowed=memberSet(members,view,group),all=Array.isArray(idx)?idx:[],rows=sortRows(all.filter(x=>allowed.has(String(x.code))));
    const ranked=rows.filter(x=>srpNum(x.scores?.[cfg.score])!=null).slice(0,5);
    const unrankedCount=Math.max(0,allowed.size-rows.filter(x=>srpNum(x.scores?.[cfg.score])!=null).length);
    const rule=view==='close'||view==='portfolio'?'沿用盤後正式排序：候選層級 → 波段品質 → 進場位置 → 資料信心。':view==='intraday'?'沿用盤中正式排序：決策狀態 → 盤中動能 → 資料信心。':'沿用當沖正式排序：可執行狀態 → 當沖分 → 資料信心。';
    const body=ranked.length?ranked.map((x,i)=>{const s=x.scores||{},score=s[cfg.score],entry=s.entry_position_score,bucket=SRP_BUCKET[x.opportunity_bucket]||x.opportunity_bucket||'觀察';return `<button type="button" class="sector-rank-row" data-sector-rank-code="${srpEsc(x.code)}"><span class="sector-rank-no">${i+1}</span><span class="sector-rank-id"><b>${srpEsc(x.code)} ${srpEsc(x.name||'')}</b><small>${srpEsc(bucket)} · 全雷達 #${srpEsc(x.opportunity_rank??'—')}</small></span><span class="sector-rank-score"><b>${srpEsc(cfg.label)} ${srpFmt(score)}</b><span>位置 ${srpFmt(entry)} · 信心 ${srpFmt(x.data_confidence)}%</span></span></button>`}).join(''):`<div class="sector-rank-empty">${srpEsc(group)} 目前沒有具完整 ${srpEsc(cfg.label)} 的排名股；系統不會用假分數補滿。</div>`;
    box.innerHTML=`<div class="sector-rank-panel"><div class="sector-rank-head"><b>${srpEsc(group)}｜族群內先看</b><span>${ranked.length}/${allowed.size} 檔列前排</span></div><div class="sector-rank-note">${srpEsc(rule)} 這裡只從該族群成分股中取正式排名最前面的 5 檔，不另外發明一套族群內分數。${unrankedCount?` 另有 ${unrankedCount} 檔缺完整執行分，不硬排名。`:''}</div><div class="sector-rank-list">${body}</div></div>`;
  }catch(err){console.warn('sector-ranking-panel',err);box.innerHTML='<div class="sector-rank-panel"><div class="sector-rank-empty">族群內排序目前無法載入；不影響原本族群資金資料。</div></div>'}
}
function boot(){style();document.addEventListener('click',e=>{const row=e.target.closest?.('[data-sector-rank-code]');if(row){document.dispatchEvent(new CustomEvent('radar:open-stock',{detail:{code:row.dataset.sectorRankCode}}));return}const chip=e.target.closest?.('[data-capital-expand]');if(chip){const group=groupFromChip(chip);setTimeout(()=>render(group,srpView()),0)}});document.addEventListener('radar:view-rendered',()=>{const box=document.getElementById('sectorRankExplain');if(box){box.hidden=true;box.innerHTML=''};SRP.activeGroup='';SRP.activeView=srpView()});document.addEventListener('radar:data-reloaded',()=>{SRP.build=null;SRP.cache.clear();if(SRP.activeGroup)render(SRP.activeGroup,srpView())})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
