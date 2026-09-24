(()=>{
  if(window.__DOGSON_LAYOUT_V162__) return;
  window.__DOGSON_LAYOUT_V162__=1;
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  let busy=false,timer=null;
  const clean=s=>String(s||'').replace(/^✓\s*/,'').replace(/\s+/g,' ').trim();

  function isPortfolio(){
    try{return !!portfolioOnly}catch{return document.body.classList.contains('dogson-portfolio-view')}
  }

  function quoteTone(card){
    const vals=$$('.livequote .liveval',card);
    vals.forEach(v=>v.classList.remove('v162-up','v162-down'));
    if(vals[1]){
      const s=(vals[1].textContent||'').trim();
      if(/^\+/.test(s)&&!/^\+0(?:\.0+)?%?$/.test(s)) vals[1].classList.add('v162-up');
      if(/^−|^-/.test(s)) vals[1].classList.add('v162-down');
    }
  }

  function reasonTexts(card){
    const out=[];
    const add=t=>{t=clean(t);if(!t||t.length>26||out.includes(t))return;out.push(t)};
    $$('.entrywhy span:not(.block),.stagechip:not(.risk)',card).forEach(x=>add(x.textContent));
    if(out.length<2) $$('.entrymeta span',card).forEach(x=>{
      const t=clean(x.textContent);
      if(/VWAP|結構|相對強弱|量價|族群|60K|5分K|流動性/.test(t))add(t);
    });
    return out.slice(0,4);
  }

  function keyReasons(card,details){
    let box=$('.dogson-key-reasons',card);
    if(isPortfolio()||$('.portfolio-brief',card)){
      if(box)box.remove();
      return;
    }
    const rs=reasonTexts(card);
    if(!rs.length){if(box)box.remove();return}
    if(!box){
      box=document.createElement('div');box.className='dogson-key-reasons';
      details?.before(box);
    }
    const html=`<div class="dogson-key-title">關鍵理由</div><div class="dogson-key-list">${rs.map(x=>`<span>✓ ${x.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}</span>`).join('')}</div>`;
    if(box.dataset.h!==html){box.innerHTML=html;box.dataset.h=html}
  }

  function detailButton(details){
    const s=$(':scope>summary',details);if(!s)return;
    const set=()=>{s.textContent=details.open?'收合分析 ↑':'▥ 展開分析 ›'};
    set();
    if(!details.dataset.v162Toggle){details.dataset.v162Toggle='1';details.addEventListener('toggle',set)}
  }

  function card(card){
    card.classList.add('dogson-v162-card');
    const brief=$('.dogson-card-brief',card),live=$('.livequote',card),details=$('.dogson-card-details',card);
    if(brief&&live&&live.previousElementSibling!==brief) brief.after(live);
    if(details){detailButton(details);keyReasons(card,details)}
    quoteTone(card);
  }

  function polishTop(){
    const title=$('#dogsonOverviewV160 .dogson-section-title');
    if(title&&title.textContent!=='今日雷達')title.textContent='今日雷達';
    const nav=$('#dogsonViewNav');if(nav)nav.setAttribute('aria-label','雷達模式');
  }

  function run(){
    if(busy)return;busy=true;
    try{polishTop();$$('#cards .card').forEach(card)}finally{busy=false}
  }
  const schedule=()=>{if(busy)return;clearTimeout(timer);timer=setTimeout(run,70)};
  function start(){
    run();
    const obs=new MutationObserver(schedule);
    if(document.body)obs.observe(document.body,{subtree:true,childList:true,characterData:false});
    setTimeout(run,250);setTimeout(run,900);setInterval(run,5000);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
