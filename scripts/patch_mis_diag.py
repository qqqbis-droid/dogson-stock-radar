#!/usr/bin/env python3
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts'/'build_data.py'
s=p.read_text(encoding='utf-8')
a=s.index('def intraday_stock_snapshot(')
b=s.index('def _weighted_pct(',a)
block=s[a:b]
if 'MIS_DIAG' in block:
    print('diagnostics already present'); raise SystemExit(0)
block=block.replace('    out = {}\n    # MIS becomes unreliable', '''    out = {}\n    MIS_DIAG = {"requests":0,"msg_entries":0,"wanted_entries":0,"today_entries":0,"valid_z":0,"missing_z":0,"wrong_date":0}\n    MIS_SAMPLES = []\n    # MIS becomes unreliable''')
block=block.replace('        try:\n            rr = requests.get(', '        try:\n            MIS_DIAG["requests"] += 1\n            rr = requests.get(')
block=block.replace('            rr.raise_for_status()\n            for x in rr.json().get("msgArray") or []:', '''            rr.raise_for_status()\n            arr = rr.json().get("msgArray") or []\n            MIS_DIAG["msg_entries"] += len(arr)\n            for x in arr:''')
block=block.replace('                if not code or td != today:\n                    continue\n                last = fnum(x.get("z"))', '''                if not code:\n                    continue\n                MIS_DIAG["wanted_entries"] += 1\n                if td != today:\n                    MIS_DIAG["wrong_date"] += 1\n                    if len(MIS_SAMPLES) < 8:\n                        MIS_SAMPLES.append({"code":code,"why":"date","d":x.get("d"),"t":x.get("t"),"z":x.get("z"),"ex":x.get("ex")})\n                    continue\n                MIS_DIAG["today_entries"] += 1\n                last = fnum(x.get("z"))''')
block=block.replace('                if last is None or last <= 0:\n                    continue\n                tm = str(x.get("t") or "").strip()', '''                if last is None or last <= 0:\n                    MIS_DIAG["missing_z"] += 1\n                    if code in {"3189","4707"} or len(MIS_SAMPLES) < 16:\n                        MIS_SAMPLES.append({"code":code,"why":"z","d":x.get("d"),"t":x.get("t"),"z":x.get("z"),"tv":x.get("tv"),"y":x.get("y"),"o":x.get("o"),"h":x.get("h"),"l":x.get("l"),"v":x.get("v"),"b":x.get("b"),"a":x.get("a"),"ex":x.get("ex")})\n                    continue\n                MIS_DIAG["valid_z"] += 1\n                tm = str(x.get("t") or "").strip()''')
block=block.replace('    print("MIS intraday stock quotes", len(out), "/", len(recs))', '    print("MIS intraday stock quotes", len(out), "/", len(recs)); print("MIS_DIAG", json.dumps(MIS_DIAG,ensure_ascii=False), "samples", json.dumps(MIS_SAMPLES,ensure_ascii=False))')
s=s[:a]+block+s[b:]
p.write_text(s,encoding='utf-8')
print('MIS diagnostics patched')
