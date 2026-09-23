#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.5.15 — Safari/PWA 強制換版修復。

不改任何雷達分數、資金流公式或資料結構，只修前端更新機制：
- Service Worker 註冊 URL 版本化。
- updateViaCache='none'，主動 reg.update()。
- 新 worker 接管時只自動 reload 一次。
- 提供 refresh.html：一次性解除舊 SW、清除 Cache Storage，再回首頁。
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel, text):
    (ROOT / rel).write_text(text, encoding="utf-8")


def must_replace(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f"v1.5.15 patch missing marker: {label}")
    return text.replace(old, new, count)


def patch_index():
    p = "docs/index.html"
    s = read(p)
    s = re.sub(
        r"Free Edition v1\.5\.\d+｜[^<]*",
        "Free Edition v1.5.15｜Safari強制換版修復＋盤後今日法人金額排名＋盤中成交資金輪動透明化",
        s,
        count=1,
    )

    old = 'if("serviceWorker" in navigator)navigator.serviceWorker.register("./sw.js").catch(()=>{});'
    new = r'''if("serviceWorker" in navigator){
 window.addEventListener("load",async()=>{
  try{
   const reg=await navigator.serviceWorker.register("./sw.js?v=1515",{updateViaCache:"none"});
   await reg.update();
   let reloading=false;
   navigator.serviceWorker.addEventListener("controllerchange",()=>{
    if(reloading)return;
    if(sessionStorage.getItem("dogsonSwReloaded1515")==="1")return;
    reloading=true;
    sessionStorage.setItem("dogsonSwReloaded1515","1");
    location.reload();
   });
  }catch(e){}
 });
}'''
    s = must_replace(s, old, new, "service worker registration")
    write(p, s)


def patch_sw():
    p = "docs/sw.js"
    s = read(p)
    s = re.sub(r"dogson-free-v\d+[a-z]*", "dogson-free-v1515", s, count=1)
    write(p, s)


def write_refresh():
    p = "docs/refresh.html"
    html = r'''<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0b0d12">
<title>犬子老師・更新雷達</title>
<style>
body{margin:0;background:#0b0d12;color:#f4f6fb;font-family:-apple-system,BlinkMacSystemFont,"PingFang TC",sans-serif;display:grid;place-items:center;min-height:100vh}.box{max-width:520px;padding:28px;text-align:center}.title{font-size:24px;font-weight:900}.sub{margin-top:12px;color:#9ba5b6;line-height:1.65}.spin{font-size:38px;margin-bottom:14px}
</style>
</head>
<body>
<div class="box"><div class="spin">🔄</div><div class="title">正在切換到最新版…</div><div class="sub">會解除舊版 Service Worker、清除網站快取，完成後自動回到犬子老師飆股雷達。</div></div>
<script>
(async()=>{
 try{
  if("serviceWorker" in navigator){
   const regs=await navigator.serviceWorker.getRegistrations();
   await Promise.all(regs.map(r=>r.unregister()));
  }
  if("caches" in window){
   const keys=await caches.keys();
   await Promise.all(keys.map(k=>caches.delete(k)));
  }
 }catch(e){}
 const u=new URL("./",location.href);
 u.searchParams.set("force","1515");
 u.searchParams.set("t",Date.now().toString());
 location.replace(u.toString());
})();
</script>
</body>
</html>
'''
    write(p, html)


if __name__ == "__main__":
    patch_index()
    patch_sw()
    write_refresh()
    print("v1.5.15 Safari/PWA force-update repair applied")
