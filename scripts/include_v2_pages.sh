#!/usr/bin/env bash
set -euo pipefail

# Every GitHub Pages publisher replaces the whole site artifact. Pull the V2
# runtime from clean-build-v2, then rebuild its canonical bundle from the exact
# legacy/root data that this publisher is about to ship. This prevents a root
# deploy from restoring an older /v2/ manifest.
git fetch origin clean-build-v2 --depth=1
rm -rf docs/v2 scripts/v2 contracts
git archive FETCH_HEAD docs/v2 scripts/v2 contracts requirements-contract.txt | tar -xf -

test -f docs/v2/index.html
test -f scripts/v2/shadow_cycle.py
test -f scripts/v2/live_publish_patch.py

rm -rf /tmp/dogson-pages-v2-shadow
python -m scripts.v2.shadow_cycle \
  --legacy-root docs/data \
  --output docs/v2/data \
  --reports /tmp/dogson-pages-v2-shadow/reports
python scripts/v2/live_publish_patch.py --legacy-root docs/data --root docs/v2/data

test -f docs/v2/data/current_manifest.json

python - <<'PY'
import json
from pathlib import Path

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def effective_date(obj):
    dates=[]
    if isinstance(obj,dict):
        for k in ('trade_date','source_trade_date','date'):
            s=str(obj.get(k) or '')[:10]
            if len(s)==10: dates.append(s)
        b=obj.get('bridge') or {}
        s=str(b.get('trade_date') or '')[:10]
        if len(s)==10: dates.append(s)
        for r in obj.get('rows') or []:
            if not isinstance(r,dict): continue
            s=str(r.get('quote_date') or r.get('market_trade_date') or r.get('date') or '')[:10]
            if len(s)==10: dates.append(s)
    return max(dates) if dates else ''

m=load('docs/v2/data/current_manifest.json')
intra=load('docs/data/intraday.json')
day=load('docs/data/daytrade.json')
close=load('docs/data/close.json')
ide=effective_date(intra); dde=effective_date(day); cde=effective_date(close)
vi=str((m.get('datasets',{}).get('decision_intraday_summary') or {}).get('as_of') or '')[:10]
vd=str((m.get('datasets',{}).get('decision_daytrade_summary') or {}).get('as_of') or '')[:10]
vc=str((m.get('datasets',{}).get('decision_close_summary') or {}).get('as_of') or '')[:10]
if ide and vi != ide:
    raise SystemExit(f'V2 intraday regression: source={ide} v2={vi}')
if dde and vd != dde:
    raise SystemExit(f'V2 daytrade regression: source={dde} v2={vd}')
if cde and vc != cde:
    raise SystemExit(f'V2 close regression: source={cde} v2={vc}')
print('V2 source lock:', {'build':m.get('active_build_id'),'close':vc,'intraday':vi,'daytrade':vd})
PY

# The legacy service worker owns the repository root. Let /v2/ bypass it so iOS
# navigation is handled by the V2 app instead of the legacy SPA fallback/cache.
python - <<'PY'
from pathlib import Path
p = Path('docs/sw.js')
s = p.read_text(encoding='utf-8')
needle = "  const url=new URL(req.url);\n  if(url.pathname.includes('/data/'))"
guarded = "  const url=new URL(req.url);\n  if(url.pathname.includes('/v2/'))return;\n  if(url.pathname.includes('/data/'))"
if guarded not in s:
    if needle not in s:
        raise SystemExit('legacy sw fetch handler shape changed; refusing unsafe V2 overlay')
    s = s.replace(needle, guarded, 1)
    p.write_text(s, encoding='utf-8')
PY

grep -q "url.pathname.includes('/v2/')" docs/sw.js
echo "Included/rebuilt Clean Build 2.0 in Pages artifact: $(python -c 'import json; print(json.load(open("docs/v2/data/current_manifest.json")).get("active_build_id", "unknown"))')"
