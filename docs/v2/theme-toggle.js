const THEME_KEY='dogson.theme.v1';
const THEMES=new Set(['light','dark']);
function getTheme(){const saved=localStorage.getItem(THEME_KEY);return THEMES.has(saved)?saved:'light'}
function applyTheme(theme){
  const value=THEMES.has(theme)?theme:'light';
  document.documentElement.dataset.theme=value;
  localStorage.setItem(THEME_KEY,value);
  const meta=document.querySelector('meta[name="theme-color"]');
  if(meta)meta.content=value==='dark'?'#15201b':'#f5f3ec';
  const btn=document.getElementById('themeToggle');
  if(btn){btn.textContent=value==='dark'?'☀️':'🌙';btn.setAttribute('aria-label',value==='dark'?'切換淺色模式':'切換深色模式');btn.title=value==='dark'?'淺色模式':'深色模式'}
}
function ensureStyle(){
  if(document.getElementById('themeToggleStyle'))return;
  const st=document.createElement('style');st.id='themeToggleStyle';st.textContent=`
  .tabs{grid-template-columns:repeat(4,1fr) auto}.theme-toggle{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:10px;min-width:44px;min-height:44px;font-size:16px;padding:0 10px}
  html[data-theme="dark"]{--bg:#15201b;--card:#1d2a24;--ink:#edf4ef;--muted:#9eb0a6;--green:#78b99c;--line:#34463d;--red:#ff9b91;--up:#ff7b70;--down:#64c995;--amber:#e2b967;--soft:#24342c;--blue:#8ebbd0;color-scheme:dark}
  html[data-theme="dark"] body{background:var(--bg);color:var(--ink)}
  html[data-theme="dark"] .top,html[data-theme="dark"] .tabs{background:rgba(21,32,27,.96)}
  html[data-theme="dark"] .tab{background:#2a3931;color:var(--ink)}
  html[data-theme="dark"] .tab.active{background:#4f8e71;color:#fff}
  html[data-theme="dark"] .panel,html[data-theme="dark"] dialog,html[data-theme="dark"] .dialog-head,html[data-theme="dark"] .status{background:var(--card);color:var(--ink)}
  html[data-theme="dark"] .card,html[data-theme="dark"] .chip,html[data-theme="dark"] input,html[data-theme="dark"] select,html[data-theme="dark"] textarea,html[data-theme="dark"] .refresh-btn{background:#223129;color:var(--ink);border-color:var(--line)}
  html[data-theme="dark"] .metric,html[data-theme="dark"] .score,html[data-theme="dark"] .detail-grid>div,html[data-theme="dark"] .quality-grid>div,html[data-theme="dark"] .detail-score-grid>div,html[data-theme="dark"] .sdr-quick>div,html[data-theme="dark"] .sdr-evidence>div,html[data-theme="dark"] .portfolio-summary>div,html[data-theme="dark"] .portfolio-detail-grid>div{background:var(--soft)!important}
  html[data-theme="dark"] .action-line,html[data-theme="dark"] .portfolio-reason,html[data-theme="dark"] .empty-state,html[data-theme="dark"] .load-more{background:#223129;color:var(--ink)}
  html[data-theme="dark"] .action-line.go{background:#214032;color:#9bd1b7}html[data-theme="dark"] .action-line.wait{background:#473c22;color:#f0cc7a}html[data-theme="dark"] .action-line.risk{background:#482b29;color:#ffaca4}
  html[data-theme="dark"] .sdr-explain,html[data-theme="dark"] .sdr-exp-card{background:#1b2822;border-color:var(--line)}
  html[data-theme="dark"] .portfolio-privacy,html[data-theme="dark"] .portfolio-focus{background:#26352e;color:var(--ink)}
  html[data-theme="dark"] dialog::backdrop{background:rgba(0,0,0,.6)}
  @media(max-width:560px){.tabs{gap:5px;padding-left:8px;padding-right:8px}.theme-toggle{padding:0 8px;min-width:42px}}
  `;document.head.appendChild(st)
}
function boot(){
  ensureStyle();
  const nav=document.getElementById('tabs');
  if(nav&&!document.getElementById('themeToggle')){
    const btn=document.createElement('button');btn.id='themeToggle';btn.type='button';btn.className='theme-toggle';nav.appendChild(btn);
    btn.addEventListener('click',()=>applyTheme(getTheme()==='dark'?'light':'dark'));
  }
  applyTheme(getTheme());
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
