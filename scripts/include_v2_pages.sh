#!/usr/bin/env bash
set -euo pipefail

# Every GitHub Pages publisher replaces the whole site artifact. Pull the V2
# runtime from clean-build-v2 first.  When all legacy sources are aligned we
# rebuild the Atomic Bundle from the exact root data that is about to ship.
# After-hours MIS can no longer reconstruct an already-finished intraday
# snapshot, however, so a verified same-trade-date canonical bundle is preserved
# instead of being overwritten by an older intraday/daytrade source.
git fetch origin clean-build-v2 --depth=1
rm -rf docs/v2 scripts/v2 contracts
git archive FETCH_HEAD docs/v2 scripts/v2 contracts requirements-contract.txt | tar -xf -

test -f docs/v2/index.html
test -f docs/v2/detail-context-v2.js
test -f docs/v2/detail-context-v3.js
test -f docs/v2/card-display-v3.js
test -f scripts/v2/shadow_cycle.py
test -f scripts/v2/live_publish_patch.py
test -f scripts/v2/enrich_zones.py
test -f scripts/v2/enrich_stock_detail_context.py
test -f scripts/v2/restore_market_capital_context.py
test -f scripts/v2/validate_market_capital_context.py
test -f scripts/v2/normalize_close_snapshot.py
test -f scripts/v2/stamp_version_contract.py
test -f requirements-contract.txt

python -m pip install --disable-pip-version-check -r requirements-contract.txt

mode="$(python - <<'PY'
import json
from pathlib import Path

def load(path):
    p=Path(path)
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return {}

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
canonical=str(m.get('trade_date') or '')[:10]
close=effective_date(load('docs/data/close.json'))
intra=effective_date(load('docs/data/intraday.json'))
day=effective_date(load('docs/data/daytrade.json'))
print(f'V2 overlay dates canonical={canonical} close={close} intraday={intra} daytrade={day}', file=__import__('sys').stderr)
if not canonical:
    print('REBUILD')
elif close and close > canonical:
    # A new completed session must never borrow an older canonical intraday set.
    if not intra or intra < close or not day or day < close:
        print('BLOCK_NEW_SESSION')
    else:
        print('REBUILD')
elif close == canonical and ((intra and intra < close) or (day and day < close) or not intra or not day):
    # Same completed session: after-hours quote APIs may no longer expose the
    # final snapshot.  Keep the already validated canonical session intact.
    print('PRESERVE_SAME_DAY')
elif close and canonical > close:
    # Root data is older than the canonical bundle.  Never regress V2.
    print('PRESERVE_NEWER_CANONICAL')
else:
    print('REBUILD')
PY
)"
export V2_OVERLAY_MODE="$mode"
echo "V2 overlay mode: $mode"

case "$mode" in
  BLOCK_NEW_SESSION)
    echo "A newer close session exists but intraday/daytrade are stale; refusing to fabricate or reuse another session." >&2
    exit 1
    ;;
  PRESERVE_SAME_DAY|PRESERVE_NEWER_CANONICAL)
    echo "Preserving verified canonical V2 data; deploying UI without rebuilding from stale after-hours MIS."
    # Crossing midnight does not make the latest completed close session stale.
    # Repair that semantic before validation while leaving intraday/daytrade frozen.
    python scripts/v2/normalize_close_snapshot.py --root docs/v2/data
    python scripts/v2/stamp_version_contract.py --root docs/v2/data
    python scripts/v2/validate_bundle.py --root docs/v2/data
    python scripts/v2/validate_market_capital_context.py --root docs/v2/data
    ;;
  REBUILD)
    rm -rf /tmp/dogson-pages-v2-shadow
    python -m scripts.v2.shadow_cycle \
      --legacy-root docs/data \
      --output docs/v2/data \
      --reports /tmp/dogson-pages-v2-shadow/reports
    python scripts/v2/live_publish_patch.py --legacy-root docs/data --root docs/v2/data
    # A fresh shadow_cycle rebuild replaces the active build directory. Re-run
    # all enrichers that create decision-linked datasets inside that build.
    python scripts/v2/enrich_zones.py --legacy-root docs/data --output docs/v2/data
    python scripts/v2/enrich_stock_detail_context.py --legacy-root docs/data --root docs/v2/data
    python scripts/v2/restore_market_capital_context.py --legacy-root docs/data --root docs/v2/data
    python scripts/v2/normalize_close_snapshot.py --root docs/v2/data
    python scripts/v2/stamp_version_contract.py --root docs/v2/data
    python scripts/v2/validate_bundle.py --root docs/v2/data
    python scripts/v2/validate_market_capital_context.py --root docs/v2/data
    ;;
  *)
    echo "Unknown V2 overlay mode: $mode" >&2
    exit 1
    ;;
esac

node --check docs/v2/stock-detail-bridge.js
node --check docs/v2/detail-context-v2.js
node --check docs/v2/detail-context-v3.js
node --check docs/v2/card-display-v3.js

test -f docs/v2/data/current_manifest.json

python - <<'PY'
import json, os
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

def resolve(root, url):
    raw=str(url or '')
    if raw.startswith('./data/'):
        return root / raw[len('./data/'):]
    return root / raw.lstrip('./')

mode=os.environ.get('V2_OVERLAY_MODE','')
root=Path('docs/v2/data')
m=load(root/'current_manifest.json')
intra=load('docs/data/intraday.json')
day=load('docs/data/daytrade.json')
close=load('docs/data/close.json')
ide=effective_date(intra); dde=effective_date(day); cde=effective_date(close)
vi=str((m.get('datasets',{}).get('decision_intraday_summary') or {}).get('as_of') or '')[:10]
vd=str((m.get('datasets',{}).get('decision_daytrade_summary') or {}).get('as_of') or '')[:10]
vc=str((m.get('datasets',{}).get('decision_close_summary') or {}).get('as_of') or '')[:10]

if mode == 'REBUILD':
    if ide and vi != ide:
        raise SystemExit(f'V2 intraday regression: source={ide} v2={vi}')
    if dde and vd != dde:
        raise SystemExit(f'V2 daytrade regression: source={dde} v2={vd}')
    if cde and vc != cde:
        raise SystemExit(f'V2 close regression: source={cde} v2={vc}')
else:
    # Preservation is allowed only when the canonical bundle represents at
    # least the latest completed close session and its three decision contexts
    # are internally same-session.  Older root intraday data is explicitly not
    # imported into the canonical build.
    if cde and vc < cde:
        raise SystemExit(f'preserved canonical close is older than root close: v2={vc} root={cde}')
    if not vc or vi != vc or vd != vc:
        raise SystemExit(f'preserved V2 decision contexts are not same-session: close={vc} intraday={vi} daytrade={vd}')

required_versions=('version_registry_version','version_set_id','schema_version','app_contract_version','engine_version','enum_registry_version','threshold_registry_version','taxonomy_version')
missing=[k for k in required_versions if not m.get(k)]
if missing:
    raise SystemExit(f'V2 version binding missing: {missing}')
required_contexts=('market_intraday_context','market_close_context','capital_intraday_context','capital_close_context')
required_details=('zone_intraday','zone_close','zone_daytrade','stock_detail_intraday','stock_detail_close','stock_detail_daytrade')
required=required_contexts+required_details
missing_ds=[k for k in required if k not in (m.get('datasets') or {})]
if missing_ds:
    raise SystemExit(f'V2 required datasets missing: {missing_ds}')
missing_files=[]
for key in required_details:
    meta=m['datasets'][key]
    p=resolve(root,meta.get('url'))
    if not p.is_file() or p.stat().st_size==0:
        missing_files.append(f'{key}:{p}')
if missing_files:
    raise SystemExit(f'V2 detail files missing from active build: {missing_files}')
zone_counts={}
for ctx in ('intraday','close','daytrade'):
    zp=resolve(root,m['datasets'][f'zone_{ctx}']['url'])
    zones=load(zp)
    zone_counts[ctx]=len(zones) if isinstance(zones,list) else 0
    if zone_counts[ctx] <= 0:
        raise SystemExit(f'V2 zone_{ctx} is empty after overlay')

# Close snapshot semantics: if close is the canonical latest completed session,
# it must remain planning-valid across midnight and must not be DATA_STALE.
close_summary=load(resolve(root,m['datasets']['decision_close_summary']['url']))
if vc == str(m.get('trade_date') or '')[:10]:
    bad=[r.get('code') for r in close_summary if r.get('freshness') in ('STALE','UNKNOWN') or r.get('action_state')=='DATA_STALE']
    if bad:
        raise SystemExit(f'latest close snapshot incorrectly stale: {bad[:10]}')

print('V2 source lock:', {'mode':mode,'build':m.get('active_build_id'),'close':vc,'intraday':vi,'daytrade':vd,'root_intraday':ide,'root_daytrade':dde,'version_set':m.get('version_set_id'),'market_capital':'split','zones':zone_counts,'stock_detail':'mission-split-v3','close_snapshot':'latest-completed-valid'})
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
echo "Included/preserved Clean Build 2.0 in Pages artifact: $(python -c 'import json; print(json.load(open("docs/v2/data/current_manifest.json")).get("active_build_id", "unknown"))')"
