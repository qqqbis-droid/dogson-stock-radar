(()=>{
'use strict';
if(window.__DOGSON_COPY_CLEAN_V1__)return;
window.__DOGSON_COPY_CLEAN_V1__=true;

const SKIP=new Set(['SCRIPT','STYLE','NOSCRIPT','PRE','CODE','TEXTAREA']);
const ATTRS=['title','aria-label','placeholder'];
const LOGIN_COOLDOWN_KEY='inuko.cloud.login.cooldownUntil';
const LOGIN_COOLDOWN_MS=60_000;
let cooldownTimer=null;

function rewrite(input){
  let s=String(input??'');
  if(!s)return s;

  s=s
    .replace(/Portfolio Ledger 2\.0[\s\S]*?掛單與取消單不要加入。?/gi,'沒有登入時，資料只存在這台裝置。只記錄真的買到或賣掉的交易；沒成交或取消的委託不用記。')
    .replace(/INUKO Cloud 私人庫存/gi,'雲端庫存')
    .replace(/用 Email 驗證連結登入。庫存、成交流水與未來手續費設定會依帳號保存。?/gi,'輸入電子郵件後，我們會寄登入連結給你。登入後，庫存與交易紀錄會跟著帳號保存。')
    .replace(/雲端同步失敗：\s*email rate limit exceeded\s*。?\s*本機資料仍保留。?/gi,'登入信寄送太頻繁，請稍後再試。資料仍保留在這台裝置。')
    .replace(/email rate limit exceeded/gi,'登入信寄送太頻繁，請稍後再試')
    .replace(/For security purposes, you can only request this after[^。\n]*/gi,'登入信剛寄過，請稍後再試')
    .replace(/分數表示條件同步程度，不代表上漲機率；排名是注意力順序。資料過期或未通過[^。]*Gate[^。]*。?/gi,'分數代表條件符合程度，不代表上漲機率；排名只是查看順序。資料過期或不完整時，系統會暫停顯示可執行判斷。')
    .replace(/狀態列只讀\s*canonical metadata；盤中日期以超短操盤卡的\s*as_of\s*為準。?/gi,'這裡顯示各項資料的更新時間。')
    .replace(/等待獨立\s*daytrade\s*即時資料[^。]*。?/gi,'等今天的即時資料更新後再判斷。')
    .replace(/即時資料已達可驗證門檻/g,'今天的即時資料已完整')
    .replace(/盤中即時層通過品質門檻/g,'盤中資料已完整')
    .replace(/合格盤中即時狀態/g,'可用的盤中資料')
    .replace(/資料狀態\s*[・·]\s*v\d+(?:\.\d+)+/gi,'資料更新')
    .replace(/犬子老師\s*[・·]\s*決策雷達\s*v\d+(?:\.\d+)+/gi,'犬子老師・選股雷達')
    .replace(/Radar\s*v\d+(?:\.\d+)+\s*[・·]\s*/gi,'')
    .replace(/最近完整交易日([^｜\n]*)｜\s*MIS覆蓋/gi,'最近完整交易日$1｜盤中資料完整度');

  const replacements=[
    [/MIS覆蓋/gi,'盤中資料完整度'],
    [/\bMIS\b/gi,'盤中資料'],
    [/canonical metadata/gi,'資料資訊'],
    [/\bcanonical\b/gi,'主要資料'],
    [/\bmetadata\b/gi,'資料資訊'],
    [/\bas_of\b/gi,'資料時間'],
    [/波段\s*Stage/gi,'波段狀態'],
    [/\bStage\b/gi,'狀態'],
    [/\bdaytrade\b/gi,'當沖'],
    [/\bfreshness\b/gi,'更新狀態'],
    [/\bSupabase\b/gi,'雲端'],
    [/\blocalStorage\b/gi,'這台裝置'],
    [/publishable\s*key/gi,'登入設定'],
    [/service[-_ ]?role/gi,'管理權限'],
    [/\bRLS\b/g,'資料保護'],
    [/\bSDK\b/g,'登入功能'],
    [/\bschema\b/gi,'資料格式'],
    [/\bcontract\b/gi,'資料規則'],
    [/\brevision\b/gi,'同步狀態'],
    [/\bDATA_STALE\b/g,'資料待更新'],
    [/\bFRESH\b/g,'資料已更新'],
    [/\bUNKNOWN\b/g,'資料狀態不明'],
    [/Atomic\s*Bundle/gi,'資料'],
    [/Clean\s*Build\s*2\.0/gi,'新版'],
    [/\bmission\b/gi,'資料用途'],
    [/\bcontext\b/gi,'參考資料'],
    [/\bGate\b/g,'資料條件'],
    [/\bEmail\b/g,'電子郵件'],
    [/盤中結構/g,'盤中資料'],
    [/盤後波段/g,'盤後資料'],
    [/雙軸判讀|兩軸判讀/g,'綜合判斷'],
    [/雙軸/g,'綜合判斷'],
    [/可驗證門檻/g,'資料完整'],
    [/品質門檻/g,'完整度要求']
  ];
  for(const [pattern,to] of replacements)s=s.replace(pattern,to);

  s=s.replace(/\s*[·・]\s*r\d+\b/gi,'');
  s=s.replace(/(^|[（(｜|·・\s])v\d+(?:\.\d+)+(?!\d)/gi,(m,prefix)=>prefix);
  s=s.replace(/[ \t]{2,}/g,' ').replace(/\s+([，。；：！？｜])/g,'$1');
  return s;
}

function cleanText(node){
  if(!node||node.nodeType!==Node.TEXT_NODE)return;
  const parent=node.parentElement;if(!parent||SKIP.has(parent.tagName))return;
  const next=rewrite(node.nodeValue);if(next!==node.nodeValue)node.nodeValue=next;
}
function cleanElement(el){
  if(!el||el.nodeType!==Node.ELEMENT_NODE||SKIP.has(el.tagName))return;
  for(const attr of ATTRS){if(el.hasAttribute(attr)){const old=el.getAttribute(attr)||'';const next=rewrite(old);if(next!==old)el.setAttribute(attr,next)}}
  for(const child of el.childNodes){if(child.nodeType===Node.TEXT_NODE)cleanText(child)}
}
function cleanTree(root){
  if(!root)return;
  if(root.nodeType===Node.TEXT_NODE){cleanText(root);return}
  if(root.nodeType!==Node.ELEMENT_NODE&&root.nodeType!==Node.DOCUMENT_NODE)return;
  if(root.nodeType===Node.ELEMENT_NODE)cleanElement(root);
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT);
  let node;while((node=walker.nextNode())){if(node.nodeType===Node.TEXT_NODE)cleanText(node);else cleanElement(node)}
}

function cloudPanel(){return document.querySelector('#inukoCloudPanel')}
function showCloudMessage(text){
  const panel=cloudPanel();if(!panel)return;
  let msg=panel.querySelector('.inuko-cloud-user,.inuko-cloud-copy');
  if(!msg){msg=document.createElement('div');msg.className='inuko-cloud-user';panel.appendChild(msg)}
  msg.textContent=text;
}
function cooldownUntil(){return Number(localStorage.getItem(LOGIN_COOLDOWN_KEY)||0)}
function refreshLoginButton(){
  const btn=document.querySelector('[data-cloud-login] button[type="submit"]');if(!btn)return;
  const remain=Math.max(0,cooldownUntil()-Date.now());
  const disabled=remain>0;
  const label=disabled?`請稍候 ${Math.ceil(remain/1000)} 秒`:'寄登入連結';
  if(btn.disabled!==disabled)btn.disabled=disabled;
  if((btn.textContent||'').trim()!==label)btn.textContent=label;
  if(!disabled){localStorage.removeItem(LOGIN_COOLDOWN_KEY);if(cooldownTimer){clearInterval(cooldownTimer);cooldownTimer=null}}
}
function armCooldown(){
  localStorage.setItem(LOGIN_COOLDOWN_KEY,String(Date.now()+LOGIN_COOLDOWN_MS));
  refreshLoginButton();
  if(cooldownTimer)clearInterval(cooldownTimer);
  cooldownTimer=setInterval(refreshLoginButton,1000);
}
function installCloudLoginGuard(){
  document.addEventListener('submit',e=>{
    const form=e.target?.closest?.('[data-cloud-login]');if(!form)return;
    const remain=cooldownUntil()-Date.now();
    if(remain>0){e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();showCloudMessage(`登入信剛寄過，請 ${Math.ceil(remain/1000)} 秒後再試。`);refreshLoginButton();return}
    armCooldown();
  },true);
  refreshLoginButton();
}
function loadV2UserState(){
  if(!/\/v2(?:\/|$)/.test(location.pathname)||document.getElementById('inuko-v2-user-state'))return;
  const s=document.createElement('script');s.id='inuko-v2-user-state';s.src=new URL('../inuko-v2-user-state-v1.js?v=20261003a',location.href).href;s.defer=true;document.head.appendChild(s);
}
function loadPortfolioIntel(){
  if(!/\/v2(?:\/|$)/.test(location.pathname)||document.getElementById('inuko-portfolio-intel-script'))return;
  const s=document.createElement('script');s.id='inuko-portfolio-intel-script';s.src=new URL('../inuko-portfolio-intel-v1.js?v=20261004a',location.href).href;s.defer=true;document.head.appendChild(s);
}

function start(){
  loadV2UserState();
  loadPortfolioIntel();
  cleanTree(document.documentElement);
  installCloudLoginGuard();
  const observer=new MutationObserver(records=>{
    for(const record of records){
      if(record.type==='characterData')cleanText(record.target);
      else if(record.type==='attributes')cleanElement(record.target);
      else for(const node of record.addedNodes)cleanTree(node);
    }
    refreshLoginButton();
  });
  observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:ATTRS});
  window.addEventListener('dogson:ui-ready',()=>cleanTree(document.documentElement));
  window.addEventListener('dogson:data-ready',()=>cleanTree(document.documentElement));
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
