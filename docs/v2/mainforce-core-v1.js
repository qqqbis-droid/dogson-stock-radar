/* 犬子選骨室：外部主力集中度資料核心 v1.0
   Manual broker-branch concentration is NOT official institutional flow.
   Never infer 5d/20d concentration from price or from foreign net. */
(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root)root.InukoMainforceCore=api;
})(typeof window!=="undefined"?window:null,function(){
"use strict";
const MAX_ROWS=12000, MAX_BYTES=1800000;
const fields={
 code:["股票代號","證券代號","代號","code","stock_code","stockcode","ticker"],
 name:["股票名稱","證券名稱","名稱","name","stock_name"],
 date:["日期","交易日期","資料日期","date","trade_date","tradedate"],
 net:["主力買賣超(張)","主力買賣超","主力買賣超張數","買賣超(張)","買賣超","net_lots","mainforce_net","net"],
 houses:["買賣家數差(家)","買賣家數差","家數差(家)","家數差","houses_diff","brokers_diff"],
 c5:["5日集中(%)","5日集中度","5日集中","5日主力集中度","五日集中度","concentration_5d","concentration5"],
 c20:["20日集中(%)","20日集中度","20日集中","20日主力集中度","二十日集中度","concentration_20d","concentration20"],
 source:["資料來源","來源","source"]
};
const norm=x=>String(x||"").replace(/^\uFEFF/,"").toLowerCase().replace(/[\s_\-()（）%％/＋+]/g,"");
function parseCsv(text){
 const raw=String(text||"").replace(/^\uFEFF/,"");
 if(!raw.trim())throw Error("檔案沒有內容");
 if(new TextEncoder().encode(raw).length>MAX_BYTES)throw Error("CSV 超過 1.8 MB，請分批匯入");
 let first=raw.split(/\r?\n/).find(x=>x.trim())||"";
 const delim=first.split("\t").length>first.split(",").length?"\t":",";
 let result=[],line=[],cell="",quoted=false;
 for(let i=0;i<raw.length;i++){
   const c=raw[i],next=raw[i+1];
   if(quoted){
     if(c==='"'&&next==='"'){cell+='"';i++}
     else if(c==='"')quoted=false;
     else cell+=c;
   }else if(c==='"'){quoted=true}
   else if(c===delim){line.push(cell);cell=""}
   else if(c==="\n"||c==="\r"){
     if(c==="\r"&&next==="\n")i++;
     line.push(cell);cell="";
     if(line.some(v=>v.trim()))result.push(line);
     line=[];
   }else cell+=c;
 }
 if(quoted)throw Error("CSV 欄位引號沒有正確結束");
 line.push(cell);if(line.some(v=>v.trim()))result.push(line);
 if(result.length>MAX_ROWS+1)throw Error("超過 12,000 列，請分批匯入");
 return result;
}
function mapHeaders(row){
 const map={};
 for(const [key,aliases] of Object.entries(fields)){
   const idx=row.findIndex(v=>aliases.some(a=>norm(a)===norm(v)));
   if(idx>=0)map[key]=idx;
 }
 if(map.date==null||map.code==null)throw Error("必須包含日期和股票代號兩欄");
 if(["net","houses","c5","c20"].every(k=>map[k]==null))throw Error("沒有可辨識的主力資料欄位");
 return map;
}
function numeric(raw,percent=false){
 let s=String(raw??"").trim().replace(/,/g,"").replace(/[％%]/g,"").replace(/−/g,"-");
 if(!s||["—","-","--","NA","N/A","null","無"].includes(s))return null;
 if(!/^[+-]?\d+(\.\d+)?$/.test(s))throw Error("數值格式不正確："+String(raw).slice(0,30));
 const n=Number(s);
 if(!Number.isFinite(n)||Math.abs(n)>1e9)throw Error("超出可接受數值範圍");
 if(percent&&(n < -100||n>100))throw Error("集中度必須介於 -100% 至 +100%");
 return n;
}
function normalizeDate(raw){
 const s=String(raw||"").trim();
 const m=/^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$/.exec(s);
 if(!m)throw Error("日期請填完整西元年，例如 2026/11/05");
 const y=Number(m[1]),mo=Number(m[2]),d=Number(m[3]);
 const date=new Date(Date.UTC(y,mo-1,d));
 if(date.getUTCFullYear()!==y||date.getUTCMonth()+1!==mo||date.getUTCDate()!==d||y<2000||y>2100)throw Error("日期無效");
 return [String(y),String(mo).padStart(2,"0"),String(d).padStart(2,"0")].join("-");
}
function safeCode(x){
 const s=String(x||"").trim().toUpperCase().replace(/\.TW$|\.TWO$/i,"");
 if(!/^[0-9A-Z-]{4,12}$/.test(s))throw Error("股票代號格式不正確");
 return s;
}
function record(obj){
 const o=obj||{},date=normalizeDate(o.date),code=safeCode(o.code);
 const net=numeric(o.net),houses=numeric(o.houses),c5=numeric(o.c5,true),c20=numeric(o.c20,true);
 if([net,houses,c5,c20].every(v=>v===null))throw Error("至少需要一項真正主力資料");
 if(net!=null&&!Number.isInteger(net))throw Error("主力買賣超張數須為整數");
 if(houses!=null&&!Number.isInteger(houses))throw Error("家數差須為整數");
 return{code,date,name:String(o.name||"").trim().slice(0,40),
   net,houses,c5,c20,source:String(o.source||"使用者手動提供").trim().slice(0,60)};
}
function importCsv(raw,nowDate){
 const table=parseCsv(raw),header=mapHeaders(table[0]),out=[],errors=[];
 for(let i=1;i<table.length;i++){
   const cols=table[i],get=k=>header[k]==null?"":(cols[header[k]]||"");
   try{
     const r=record({code:get("code"),date:get("date"),name:get("name"),
       net:get("net"),houses:get("houses"),c5:get("c5"),c20:get("c20"),source:get("source")});
     if(nowDate&&r.date>nowDate)throw Error("不接受未來的來源日期");
     out.push(r);
   }catch(e){
     errors.push("第 "+(i+1)+" 列："+e.message);
   }
 }
 if(errors.length)throw Error(errors.slice(0,5).join("；")+(errors.length>5?"（另有 "+(errors.length-5)+" 列錯誤）":""));
 if(!out.length)throw Error("沒有有效交易日資料");
 return out;
}
function merge(existing,incoming){
 const m=new Map();
 for(const r of [...(existing||[]),...(incoming||[])]){
  let o=record(r),key=o.code+"|"+o.date,prev=m.get(key);
  if(prev){
   for(const k of ["name","source","net","houses","c5","c20"])
     if(o[k]!==null && o[k]!=="")prev[k]=o[k];
  }else m.set(key,o);
 }
 return [...m.values()].sort((a,b)=>b.date.localeCompare(a.date)||a.code.localeCompare(b.code)).slice(0,MAX_ROWS);
}
function twDate(d=new Date()){return new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Taipei",year:"numeric",month:"2-digit",day:"2-digit"}).format(d).replace(/\//g,"-")}
function summarize(rows,closeDate){
 const sorted=(rows||[]).slice().sort((a,b)=>b.date.localeCompare(a.date));
 if(!sorted.length)return null;
 const current=sorted[0],prior=sorted.find(r=>r.date<current.date)||null;
 const diff=k=>prior&&Number.isFinite(current[k])&&Number.isFinite(prior[k])?+(current[k]-prior[k]).toFixed(3):null;
 const d5=diff("c5"),d20=diff("c20");
 let status="PARTIAL",label="資料不足，無法確認主力方向",reason="需要更多實際主力集中度資料";
 if(current.c5!=null&&current.c20!=null){
   if(current.c5>0&&current.c20>0){
     status="CONCENTRATING";label="短中期籌碼偏集中";reason="5 日與 20 日集中度均為正，但仍需量價及交易限制交叉驗證";
   }else if(current.c5>0&&current.c20<=0){
     status="RECOVERY_WATCH";label="短線轉正，中期仍偏空";reason="5 日已轉正、20 日仍非正值：僅列觀察";
   }else if(current.c5<=0&&current.c20<0){
     if(current.net!=null&&current.net>0&&d5!=null&&d5>0){
       status="REBOUND_WATCH";label="回補觀察，中期仍偏空";reason="當日主力買超且 5 日集中度改善；20 日仍負值";
     }else if(d5!=null&&d5>0){
       status="SELL_EASING";label="短線賣壓趨緩，中期仍偏空";reason="5 日集中度改善，但 20 日仍負值；不等於翻多";
     }else{
       status="DISTRIBUTING";label="主力籌碼偏分散";reason="5 日與 20 日集中度均非正值；單一供應商指標不能證明持有人身分";
     }
   }else{
     status="MIXED";label="短中期方向分歧";reason="5 日與 20 日集中度方向不一致";
   }
 }
 const freshness=closeDate?(current.date===closeDate?"SAME_DAY":current.date<closeDate?"STALE":"AHEAD"):"UNVERIFIED";
 return{...current,prev:prior,d5,d20,status,label,reason,freshness,history:sorted.slice(0,30)};
}
function allSummaries(rows,closeDate){
 const groups=new Map();
 for(const r of rows||[]){if(!groups.has(r.code))groups.set(r.code,[]);groups.get(r.code).push(r)}
 return [...groups.values()].map(v=>summarize(v,closeDate)).filter(Boolean);
}
const csvTemplate="\uFEFF日期,股票代號,股票名稱,主力買賣超(張),買賣家數差(家),5日集中(%),20日集中(%),資料來源\r\n";
return{MAX_ROWS,parseCsv,mapHeaders,record,importCsv,merge,twDate,summarize,allSummaries,csvTemplate};
});