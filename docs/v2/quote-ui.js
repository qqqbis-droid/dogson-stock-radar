const viewDataset={intraday:"decision_intraday_index",close:"decision_close_index",daytrade:"decision_daytrade_index"};
let manifest=null;
const cache={};
let busy=false;
const fmtPrice=v=>v==null||Number.isNaN(Number(v))?"—":Number(v).toLocaleString("zh-TW",{maximumFractionDigits:2});
const fmtPct=v=>v==null||Number.isNaN(Number(v))?"—":`${Number(v)>0?"+":""}${Number(v).toFixed(2)}%`;
const compact=v=>v==null||Number.isNaN(Number(v))?"—":new Intl.NumberFormat("zh-TW",{notation:"compact",maximumFractionDigits:1}).format(Number(v));
function activeView(){return document.querySelector(".tab.active")?.dataset.view||"intraday"}
async function getManifest(force=false){if(manifest&&!force)return manifest;const r=await fetch(`./data/current_manifest.json${force?`?t=${Date.now()}`:""}`,{cache:"no-store"});if(!r.ok)throw new Error(`manifest HTTP ${r.status}`);manifest=await r.json();return manifest}
async function rowsFor(view){const m=await getManifest();const key=viewDataset[view];if(!key)return[];const meta=m.datasets?.[key];if(!meta)return[];const cacheKey=`${m.active_build_id}:${key}`;if(cache[cacheKey])return cache[cacheKey];const r=await fetch(meta.url,{cache:"no-store"});if(!r.ok)throw new Error(`${key} HTTP ${r.status}`);const rows=await r.json();for(const row of rows){if(row?.build_id&&row.build_id!==m.active_build_id)throw new Error(`${key} mixed build`)}cache[cacheKey]=rows;return rows}
function volumeText(q){if(q?.relative_volume!=null)return`量比 ${Number(q.relative_volume).toFixed(1)}x`;if(q?.volume==null)return"量 —";const unit=q.volume_unit==="SHARES"?"股":q.volume_unit==="LOTS"?"張":"";return`量 ${compact(q.volume)}${unit}`}
function turnoverText(q){if(q?.turnover_value_twd==null)return"";return`成交值 ${compact(q.turnover_value_twd)}元`}
function quoteHtml(q){const pct=Number(q?.day_change_pct);const cls=Number.isFinite(pct)?(pct>0?"rise":pct<0?"fall":"flat"):"flat";return `<div class="quote-price">${fmtPrice(q?.price)}</div><div class="quote-change ${cls}">${fmtPct(q?.day_change_pct)}</div><div class="quote-volume">${volumeText(q)}</div>${q?.turnover_value_twd!=null?`<div class="quote-turnover">${turnoverText(q)}</div>`:""}`}
async function enhanceCards(){if(busy)return;busy=true;try{const view=activeView();if(view==="portfolio")return;const m=await getManifest();const rows=await rowsFor(view);const map=new Map(rows.map(r=>[String(r.code),r]));for(const card of document.querySelectorAll("#cards .card[data-code]")){if(card.dataset.quoteBuild===m.active_build_id)continue;const row=map.get(String(card.dataset.code));if(!row)continue;let line=card.querySelector(".quote-strip");if(!line){line=document.createElement("div");line.className="quote-strip";const action=card.querySelector(".action-line");if(action)card.insertBefore(line,action);else card.appendChild(line)}line.innerHTML=quoteHtml(row.quote||{});card.dataset.quoteBuild=m.active_build_id}}catch(err){console.warn("quote-ui",err)}finally{busy=false}}
function schedule(){setTimeout(enhanceCards,0)}
const observer=new MutationObserver(schedule);
const cards=document.querySelector("#cards");if(cards)observer.observe(cards,{childList:true,subtree:true});
document.addEventListener("click",e=>{if(e.target.closest(".tab"))schedule();if(e.target.id==="loadMore")schedule();if(e.target.id==="refreshBtn"){manifest=null;for(const key of Object.keys(cache))delete cache[key];setTimeout(()=>getManifest(true).then(enhanceCards).catch(console.warn),700)}});
document.querySelector("#searchInput")?.addEventListener("input",schedule);
document.querySelector("#stageFilter")?.addEventListener("change",schedule);
document.querySelector("#actionFilter")?.addEventListener("change",schedule);
schedule();
