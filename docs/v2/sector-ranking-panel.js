const SRP={build:null,cache:new Map(),activeGroup:'',activeView:'',activeHost:null};
const SRP_CFG={
  intraday:{index:'decision_intraday_index',sector:'sector_intraday',score:'intraday_momentum_score',label:'盤中動能'},
  close:{index:'decision_close_index',sector:'sector_close',score:'swing_quality_score',label:'波段品質'},
  portfolio:{index:'decision_close_index',sector:'sector_close',score:'swing_quality_score',label:'波段品質'},
  daytrade:{index:'decision_daytrade_index',sector:'sector_intraday',score:'daytrade_score',label:'當沖分'}
};
const SRP_ALIAS={'ASIC／IC設計服務':'ASIC／IC設計服務／IP','伺服器電源':'電源／UPS','記憶體／儲存IC':'記憶體IC'};
const SRP_BUCKET={TRIGGER_READY:'觸發就緒',WAIT_TRIGGER:'等待觸發',TREND_MONITOR:'趨勢追蹤',WAIT_PULLBACK:'等待回踩',RESEARCH_ONLY:'研究觀察',NEXT_DAY_READY:'明日候選',BREAKOUT_WATCH:'突破觀察',PULLBACK_WATCH:'回踩觀察',TREND_QUALITY:'趨勢品質',RESEARCH:'研究觀察',RISK:'風險優先',ACTIONABLE_NOW:'可執行',NO_TRADE:'不交易',STALE:'資料失效'};
const srpEsc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const srpNum=v=>v==null||v===''||!Number.isFinite(Number(v))?null:Number(v);
const srpFmt=(v,d=0)=>srpNum(v)==null?'—':Number(v).toLocaleString('zh-TW',{maximumFractionDigits:d});
const srpPct=v=>srpNum(v)==null?'—':`${Number(v)>0?'+':''}${srpFmt(v,2)}%`;
const srpView=()=>document.querySelector('.tab.active')?.dataset.view||'intraday';
const srpNormGroup=v=>String(v??'').trim().replace(/\s*[／/]\s*/g,'／').replace(/\s+/g,'');
async function srpJson(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error(`${url} HTTP ${r.status}`);return r.json()}
async function srpManifest(){const m=await srpJson(`./data/current_manifest.json?sectorRank=${Date.now()}`);if(SRP.build!==m.active_build_id){SRP.build=m.active_build_id;SRP.cache.clear()}return m}
async function srpDataset(m,key){const meta=m.datasets?.[key];if(!meta)return null;const ck=`${m.active_build_id}:${key}`;if(SRP.cache.has(ck))return SRP.cache.get(ck);const x=await srpJson(meta.url);SRP.cache.set(ck,x);return x}
// Legacy fallback only. Current V2 must use the same Atomic Build sector dataset first.
async function srpMembers(){const ck=`${SRP.build}:sector-members`;if(SRP.cache.has(ck))return SRP.cache.get(ck);try{const x=await srpJson(`./data/sector-members.json?t=${Date.now()}`);if(x?.build_id&&SRP.build&&x.build_id!==SRP.build)return null;SRP.cache.set(ck,x);return x}catch{return null}}
function style(){if(document.getElementById('sectorRankingPanelStyle'))return;const s=document.createElement('style');s.id='sectorRankingPanelStyle';s.textContent=`
#sectorRankExplain{display:none!important}.sector-rank-inline{grid-column:1/-1;margin-top:7px;padding-top:8px;border-top:1px dashed var(--line);min-width:0}.sector-rank-inline .sector-rank-panel{padding:9px;border-radius:12px;background:color-mix(in srgb,var(--soft) 78%,transparent);border:1px solid var(--line)}.sector-rank-inline .sector-rank-head{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:4px}.sector-rank-inline .sector-rank-head b{font-size:.74rem}.sector-rank-inline .sector-rank-head span{font-size:.61rem;color:var(--muted)}.sector-rank-inline .sector-rank-note{font-size:.61rem;color:var(--muted);line-height:1.4;margin-bottom:7px}.sector-rank-inline .sector-rank-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.sector-rank-inline .sector-rank-row{display:grid;grid-template-columns:20px minmax(0,1fr);gap:4px 6px;align-items:start;border:1px solid var(--line);background:var(--card);border-radius:10px;padding:8px 7px;cursor:pointer;text-align:left;color:var(--ink);min-width:0}.sector-rank-inline .sector-rank-no{grid-row:1/3;font-weight:850;color:var(--green);font-size:.72rem;text-align:center}.sector-rank-inline .sector-rank-id{min-width:0}.sector-rank-inline .sector-rank-id b{display:block;font-size:.68rem;line-height:1.25;overflow-wrap:anywhere}.sector-rank-inline .sector-rank-id small{display:block;color:var(--muted);font-size:.56rem;margin-top:2px;line-height:1.32}.sector-rank-inline .sector-rank-score{grid-column:2;display:flex;gap:4px;align-items:baseline;color:var(--muted);font-size:.54rem}.sector-rank-inline .sector-rank-score b{font-size:.68rem;color:var(--ink)}.sector-rank-inline .sector-rank-empty{font-size:.65rem;color:var(--muted);padding:5px 0}@media(max-width:380px){.sector-rank-inline .sector-rank-list{grid-template-columns:1fr}}
`;document.head.appendChild(s)}
function groupFromChip(chip){const t=chip?.querySelector(':scope > b')?.textContent?.trim()||'';return t.replace(/^[^\p{L}\p{N}]+/u,'').trim()}
function groupCandidates(group){const out=[group,SRP_ALIAS[group]];for(const [k,v] of Object.entries(SRP_ALIAS)){if(srpNormGroup(v)===srpNormGroup(group))out.push(k)}return [...new Set(out.filter(Boolean).map(srpNormGroup))]}
function sectorCandidateSet(sectors,group){
  const wanted=new Set(groupCandidates(group)),list=Array.isArray(sectors)?sectors:[];
  const row=list.find(x=>wanted.has(srpNormGroup(x?.primary_group)));
  if(!row)return {allowed:new Set(),memberCount:null,leaderCount:0,source:'none'};
  const raw=Array.isArray(row.leaders)?row.leaders:[];
  const codes=raw.map(x=>String(typeof x==='object'?(x?.code??''):x??'')).filter(Boolean);
  const unique=[...new Set(codes)];
  return {allowed:new Set(unique),memberCount:srpNum(row.member_count),leaderCount:unique.length,source:'sector-engine'};
}
function legacyMemberSet(members,view,group){const key=view==='intraday'||view==='daytrade'?'intraday':'close',names=groupCandidates(group);for(const target of names){const groups=members?.[key]?.groups||{};const hit=Object.keys(groups).find(k=>srpNormGroup(k)===target);if(hit){const rows=groups[hit]||[];return new Set(rows.map(x=>String(x.code)).filter(Boolean))}}return new Set()}
function sortRows(rows){return [...rows].sort((a,b)=>{const ar=srpNum(a.opportunity_rank),br=srpNum(b.opportunity_rank);if(ar!=null||br!=null)return (ar??1e9)-(br??1e9);return String(a.code).localeCompare(String(b.code))})}
function clearInline(except=null){document.querySelectorAll('.sector-rank-inline').forEach(x=>{if(x!==except)x.remove()})}
function hostBox(host){let box=host?.querySelector(':scope > .sector-rank-inline');if(!box&&host){box=document.createElement('div');box.className='sector-rank-inline';host.appendChild(box)}return box}
async function render(group,view=srpView(),host=SRP.activeHost){
  style();if(!host||!host.isConnected)return;const box=hostBox(host);if(!box)return;clearInline(box);SRP.activeGroup=group;SRP.activeView=view;SRP.activeHost=host;if(!group){box.remove();return}
  box.innerHTML='<div class="sector-rank-panel"><div class="sector-rank-empty">讀取同族群股票…</div></div>';
  try{
    const cfg=SRP_CFG[view]||SRP_CFG.intraday,m=await srpManifest(),[idx,sectors,members]=await Promise.all([srpDataset(m,cfg.index),srpDataset(m,cfg.sector),srpMembers()]);
    if(SRP.activeGroup!==group||SRP.activeView!==view||SRP.activeHost!==host||!host.isConnected)return;
    const sectorPick=sectorCandidateSet(sectors,group);
    let allowed=sectorPick.allowed,source=sectorPick.source;
    if(!allowed.size){allowed=legacyMemberSet(members,view,group);if(allowed.size)source='legacy-member-map'}
    const all=Array.isArray(idx)?idx:[],rows=sortRows(all.filter(x=>allowed.has(String(x.code))));
    const scoredRows=rows.filter(x=>srpNum(x.scores?.[cfg.score])!=null);
    const ranked=scoredRows.slice(0,5);
    const unrankedCount=Math.max(0,allowed.size-scoredRows.length);
    const total=sectorPick.memberCount;
    const sourceNote=source==='sector-engine'
      ?(total!=null&&total>allowed.size?`族群共 ${srpFmt(total)} 檔，本區採 Engine 優先股 ${allowed.size} 檔再依${cfg.label}排序。`:`族群共 ${total!=null?srpFmt(total):allowed.size} 檔，本區依${cfg.label}排序。`)
      :'使用相容成分股清單排序。';
    const body=ranked.length?ranked.map((x,i)=>{const s=x.scores||{},q=x.quote||{},score=s[cfg.score],price=q.price??x.price??x.close,change=q.day_change_pct??q.change_pct??x.day_change_pct??x.change_pct,bucket=SRP_BUCKET[x.opportunity_bucket]||x.opportunity_bucket||'觀察';return `<button type="button" class="sector-rank-row" data-stock-code="${srpEsc(x.code)}"><span class="sector-rank-no">${i+1}</span><span class="sector-rank-id"><b>${srpEsc(x.code)} ${srpEsc(x.name||'')}</b><small>${srpFmt(price,2)} · ${srpPct(change)} · ${srpEsc(bucket)}</small></span><span class="sector-rank-score"><span>${srpEsc(cfg.label)}</span><b>${srpFmt(score,1)}</b></span></button>`}).join(''):`<div class="sector-rank-empty">${allowed.size?`${srpEsc(group)} 的 Engine 優先股目前缺完整 ${srpEsc(cfg.label)}；系統不會用假分數補滿。`:`${srpEsc(group)} 目前找不到同一批次的族群個股資料。`}</div>`;
    box.innerHTML=`<div class="sector-rank-panel"><div class="sector-rank-head"><b>同族群優先股</b><span>前 ${ranked.length}/${allowed.size} 檔</span></div><div class="sector-rank-note">直接接在 ${srpEsc(group)} 下方；點股票可看完整個股。${srpEsc(sourceNote)}${unrankedCount?` 另有 ${unrankedCount} 檔缺完整執行分。`:''}</div><div class="sector-rank-list">${body}</div></div>`;
  }catch(err){console.warn('sector-ranking-panel',err);box.innerHTML='<div class="sector-rank-panel"><div class="sector-rank-empty">同族群股票目前無法載入；不影響族群資金資料。</div></div>'}
}
function boot(){
  style();
  document.addEventListener('click',e=>{
    const chip=e.target.closest?.('[data-capital-expand]');
    if(!chip||e.target.closest?.('[data-stock-code]'))return;
    const group=groupFromChip(chip);
    setTimeout(()=>{
      if(chip.getAttribute('aria-expanded')!=='true'){
        chip.querySelector(':scope > .sector-rank-inline')?.remove();
        if(SRP.activeHost===chip){SRP.activeHost=null;SRP.activeGroup=''}
        return;
      }
      render(group,srpView(),chip);
    },0);
  });
  document.addEventListener('radar:view-rendered',()=>{clearInline();SRP.activeGroup='';SRP.activeView=srpView();SRP.activeHost=null});
  document.addEventListener('radar:data-reloaded',()=>{SRP.build=null;SRP.cache.clear();if(SRP.activeGroup&&SRP.activeHost?.isConnected)render(SRP.activeGroup,srpView(),SRP.activeHost)});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();