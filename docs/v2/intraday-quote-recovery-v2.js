/* V2 intraday quote rescue: one build, one stock, read-only data repair.
 * Fills only genuinely missing quote/confidence cells; never changes ranking,
 * entry scores, executable signals or the user-owned ledger.
 */
(()=>{
 'use strict';
 const cache=new Map();
 let serial=0;
 const $=s=>document.querySelector(s);
 const asDate=v=>String(v||'').slice(0,10);
 const finite=v=>v!=null&&v!==''&&Number.isFinite(Number(v))?Number(v):null;
 const fmt=(v,n=2)=>Number(v).toLocaleString('zh-TW',{maximumFractionDigits:n});
 const pulse=()=>Date.now();
 async function read(url,ms=6500){
   const c=new AbortController(),t=setTimeout(()=>c.abort(),ms);
   try{
     const r=await fetch(url,{cache:'no-store',signal:c.signal});
     if(!r.ok)throw new Error('HTTP '+r.status);
     return await r.json();
   }finally{clearTimeout(t)}
 }
 const mission=()=>$('.tab.active')?.dataset.view||'';
 function quoteFromShard(shard,expected){
   if(!shard||shard.build_id!==expected.build||shard.view!==expected.view
      ||asDate(shard.as_of)!==expected.date||String(shard.code)!==expected.code)return null;
   const d=shard.decision||{},q=d.quote||{},e=shard.evidence||{};
   const quoteDay=asDate(q.quote_time||e.quote_date);
   // Do not silently re-label a previous day's last-trade price as LIVE.
   const sameQuote=quoteDay===expected.date;
   let px=sameQuote?finite(q.price):null;
   if(px==null&&sameQuote&&e.quote_price_validated===true)px=finite(e.close);
   const confidence=finite(d.data_confidence);
   return {
     price:px!=null&&px>0?px:null,
     change:sameQuote?finite(q.day_change_pct??e.day_change):null,
     volume:sameQuote?finite(e.quote_volume_lots):null,
     confidence,
     time:String(q.quote_time||e.quote_time||'').slice(11,16),
     checked:asDate(e.quote_date)===expected.date,
     source:sameQuote?String(e.quote_source||'盤中逐檔快照'):'資料日期待核對'
   };
 }
 function fill(card,result){
   if(!card?.isConnected||!result)return;
   const strip=card.querySelector('.quote-strip'),price=strip?.querySelector('.quote-price');
   const wasMissing=price&&price.textContent.trim().replace(/[\s—–\-]/g,'')==='';
   if(wasMissing&&result.price!=null){
     price.textContent=fmt(result.price);
     const change=strip.querySelector('.quote-change');
     if(change&&result.change!=null){
       change.textContent=(result.change>0?'+':'')+fmt(result.change)+'%';
       change.classList.remove('rise','fall','flat');
       change.classList.add(result.change>0?'rise':result.change<0?'fall':'flat');
     }
     const vol=strip.querySelector('.quote-volume');
     if(vol&&result.volume!=null&&/待補|^—/.test(vol.textContent.trim()))
       vol.textContent='累計量 '+fmt(result.volume,1)+' 張';
     card.dataset.quoteRecovered='1';
     // Evidence time, not page-load or Atomic Build time, is the source clock.
     const note=document.createElement('div');
     note.className='quote-rescue-provenance';
     note.textContent='逐檔行情核對'+(result.time?' · 成交 '+result.time:'')+' · 非逐筆即時';
     strip.insertAdjacentElement('afterend',note);
   }
   const confidence=card.querySelector('.score-row .score:nth-child(3) b');
   if(confidence&&result.confidence!=null&&confidence.textContent.trim().replace(/[%\s—–\-]/g,'')===''){
     confidence.textContent=fmt(result.confidence,0)+'%';
   }
 }
 async function hydrate(){
   const view=mission();
   if(view!=='intraday'&&view!=='daytrade')return;
   const cards=[...document.querySelectorAll('#cards .card[data-code]')].filter(c=>{
     const price=c.querySelector('.quote-strip .quote-price');
     const conf=c.querySelector('.score-row .score:nth-child(3) b');
     return price&&price.textContent.trim().replace(/[\s—–\-]/g,'')===''||
       conf&&conf.textContent.trim().replace(/[%\s—–\-]/g,'')==='';
   });
   if(!cards.length)return;
   const ticket=++serial;
   let m;
   try{m=await read('./data/current_manifest.json?t='+pulse(),6500)}
   catch(e){console.warn('intraday quote rescue manifest unavailable',e);return}
   if(ticket!==serial||mission()!==view||!m?.health?.validation_passed)return;
   const meta=m.datasets?.[view==='intraday'?'decision_intraday_summary':'decision_daytrade_summary'];
   const date=asDate(meta?.as_of),build=String(m.active_build_id||'');
   if(!date||!build)return;
   for(let start=0;start<cards.length;start+=4){
     const batch=cards.slice(start,start+4);
     await Promise.allSettled(batch.map(async card=>{
       const code=String(card.dataset.code||'');
       if(!/^[0-9A-Z]{4,6}$/.test(code))return;
       const expected={view,code,date,build};
       const key=[build,view,code].join(':');
       let item=cache.get(key);
       if(!item){
         try{
           const shard=await read('./data/builds/'+encodeURIComponent(build)+'/stock-shards/'+view+'/'+code+'.json',7000);
           item=quoteFromShard(shard,expected);
           if(item)cache.set(key,item);
         }catch(err){console.warn('intraday quote rescue shard',code,err)}
       }
       if(ticket!==serial||mission()!==view||!item)return;
       const fresh=document.querySelector('#cards .card[data-code="'+code+'"]');
       if(fresh===card)fill(card,item);
     }));
     if(ticket!==serial||mission()!==view)return;
   }
 }
 function schedule(){
   // Never rebuild the ranked card tree, so typing/favorites/search keep focus.
   void hydrate();
 }
 document.addEventListener('radar:cards-rendered',schedule);
 document.addEventListener('radar:data-reloaded',()=>{serial++;cache.clear();});
 window.RadarIntradayQuoteRecovery={quoteFromShard,fill};
})();
