(()=>{
  if(window.__DOGSON_FILTER_REFINE_V1722__) return;
  window.__DOGSON_FILTER_REFINE_V1722__=true;

  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  let busy=false,timer=null;

  function active(b){return b?.getAttribute('aria-pressed')==='true'||b?.classList.contains('active')}
  function setButtonLabel(b,label){
    if(!b)return;
    const text=(active(b)?'✓ ':'')+label;
    if(b.textContent!==text)b.textContent=text;
  }
  function replaceCopy(s){
    return String(s||'')
      .replaceAll('🟢 可觀察','🟢 位置可觀察')
      .replaceAll('🟡 等確認','🟡 位置待確認');
  }

  function refineQuick(){
    const q=$('#dogsonQuickFilters');if(!q)return;

    const stage=$('.dogson-quick-stage-row',q);
    if(stage&&!stage.hidden)stage.hidden=true;

    let title=$('.dogson-refine-title-v1722',q);
    const help=$('.dogson-filter-help',q);
    if(!title){
      title=document.createElement('div');
      title.className='dogson-refine-title-v1722';
      title.textContent='再篩選（可選）';
      (help||q.firstElementChild)?.before(title);
    }
    const helpText='先在「今日雷達」選想看的階段；這裡可再加 1 個條件縮小名單。選中會顯示 ✓，再點一次可取消。';
    if(help&&help.textContent!==helpText)help.textContent=helpText;

    setButtonLabel($('[data-ux-decision="green"]',q),'🟢 位置可觀察');
    setButtonLabel($('[data-ux-decision="yellow"]',q),'🟡 位置待確認');
    setButtonLabel($('[data-ux-decision="focus"]',q),'✨ 精選機會');
    setButtonLabel($('[data-ux-watch]',q),'⭐ 關注');

    const summary=$('.dogson-filter-summary-inline',q);
    if(summary){
      const first=$('span',summary);
      if(first&&first.textContent!=='目前查看：')first.textContent='目前查看：';
      const b=$('b',summary);
      if(b){const v=replaceCopy(b.textContent);if(v!==b.textContent)b.textContent=v}
    }
  }

  function refineOverview(){
    const o=$('#dogsonOverviewV160');if(!o)return;
    const hint=$('.dogson-overview-click-hint',o);
    const text='先點上方階段格直接看股票；需要更精準，再使用下方「再篩選」。';
    if(hint&&hint.textContent!==text)hint.textContent=text;
  }

  function refineActiveBar(){
    const bar=$('#dogsonActiveFilterBar');if(!bar)return;
    const label=$('.dogson-active-filter-label',bar);
    if(label&&label.textContent!=='目前查看')label.textContent='目前查看';
    $$('.dogson-active-filter-chips span',bar).forEach(x=>{const v=replaceCopy(x.textContent);if(v!==x.textContent)x.textContent=v});
  }

  function installStyle(){
    if($('#dogsonFilterRefineStyle1722'))return;
    const s=document.createElement('style');s.id='dogsonFilterRefineStyle1722';s.textContent=`
      #dogsonQuickFilters .dogson-quick-stage-row{display:none!important}
      .dogson-refine-title-v1722{margin:2px 2px 3px;font-size:13px;font-weight:900;color:#2f4038}
      #dogsonQuickFilters .dogson-filter-help{margin-bottom:7px}
      #dogsonQuickFilters .dogson-quick-decision-row{padding-top:1px}
      html[data-dogson-theme="dark"] .dogson-refine-title-v1722{color:#edf2ef}
    `;document.head.appendChild(s);
  }

  function apply(){
    if(busy)return;busy=true;
    try{installStyle();refineQuick();refineOverview();refineActiveBar()}finally{busy=false}
  }
  function schedule(){clearTimeout(timer);timer=setTimeout(apply,40)}
  function boot(){
    apply();
    const root=$('.wrap')||document.body;
    new MutationObserver(schedule).observe(root,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class','aria-pressed','hidden']});
    document.addEventListener('click',schedule,true);
    setTimeout(apply,250);setTimeout(apply,900);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
