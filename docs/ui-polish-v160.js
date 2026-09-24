(()=>{
if(window.__DOGSON_UI_POLISH_V160__)return;window.__DOGSON_UI_POLISH_V160__=1;
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
let timer=null,running=false;
function textReplace(root){
  if(!root)return;
  const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  const nodes=[];while(w.nextNode())nodes.push(w.currentNode);
  nodes.forEach(n=>{
    let s=n.nodeValue||'',v=s
      .replace(/Step\s*8\s*的當沖模式/gi,'獨立當沖模式')
      .replace(/Step\s*6\s*的個股化/gi,'個股化')
      .replace(/Stage\s*2\.0/gi,'波段生命週期')
      .replace(/來源\s*Stage/gi,'來源生命週期');
    if(v!==s)n.nodeValue=v;
  });
}
function clean(){
  if(running)return;running=true;
  try{
    $$('.entrytitle').forEach(x=>{if(/Step\s*4|盤中進場雷達/i.test(x.textContent||''))x.textContent='🚦 進場判讀'});
    $$('.mtftitle').forEach(x=>{let s=x.textContent||'';if(/Step\s*5|多時間框架|5分＋60分＋日K/i.test(s))x.textContent='🧭 多時間框架｜5分＋60分＋日K'});
    $$('.daytradetitle').forEach(x=>{if(/Step\s*8/i.test(x.textContent||''))x.textContent='🎯 當沖執行判讀'});
    $$('.entrysummarysub').forEach(x=>{
      let s=x.textContent||'';
      if(/Step\s*4/i.test(s))x.textContent='三燈整合個股條件與大盤環境；綠燈可觀察，黃燈等確認，紅燈先不進。';
    });
    $$('.entrymeta span').forEach(x=>{if(/MTF權重\s*[＝=]\s*0/i.test(x.textContent||''))x.textContent='多框架只確認'});
    $$('.mtfnote').forEach(x=>{let s=x.textContent||'';if(/權重\s*[＝=]\s*0/.test(s))x.textContent='多時間框架只用來確認進場，不另外加分；盤中與盤後原分數不變。'});
    $$('.entrynote').forEach(x=>{let s=x.textContent||'';if(/三燈只做進場時機判斷/.test(s))x.textContent='三燈只協助判斷進場時機；🟢 代表可小量試單，不等於自動買進。'});
    $$('.guide-title').forEach(x=>{
      let s=x.textContent||'',v=s
        .replace(/Step\s*5\s*｜?/gi,'')
        .replace(/Step\s*7\s*｜?/gi,'')
        .replace(/Step\s*8\s*｜?/gi,'');
      if(v!==s)x.textContent=v.replace(/\s*：/,'：').replace(/｜多時間框架/,'多時間框架');
    });
    $$('.guide-line,.guide-tip,.guide-mini').forEach(textReplace);
  }finally{running=false}
}
const obs=new MutationObserver(()=>{if(running)return;clearTimeout(timer);timer=setTimeout(clean,60)});
function start(){clean();if(document.body)obs.observe(document.body,{subtree:true,childList:true,characterData:true});setTimeout(clean,250);setTimeout(clean,900)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
