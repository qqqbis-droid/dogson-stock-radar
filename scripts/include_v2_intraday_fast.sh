#!/usr/bin/env bash
set -euo pipefail

# Fast intraday publisher: rebuild the V2 mission bundle from the just-refreshed
# official MIS quote layer. Do not preserve an older same-day V2 bundle, because
# that would make the website look stale even though docs/data/intraday.json is
# current. Close/chip contexts still keep their own latest-completed-session date.
# The V2 live patch must bind exactly to the canonical MIS `as_of` market clock;
# file-write/update timestamps are not allowed to make the decision bundle newer.

git fetch origin clean-build-v2 --depth=1
rm -rf docs/v2 scripts/v2 contracts
mkdir -p docs/v2
git archive FETCH_HEAD docs/v2 scripts/v2 contracts requirements-contract.txt | tar -xf -

python -m pip install --disable-pip-version-check -r requirements-contract.txt

# Intraday/daytrade reuse the latest completed EOD chip background. Copy only
# provenance/source dates from close so the UI can distinguish source date from
# the last actual source check; never invent a newer chip clock.
python scripts/sync_chip_provenance.py

rm -rf /tmp/dogson-pages-v2-fast
python -m scripts.v2.shadow_cycle \
  --legacy-root docs/data \
  --output docs/v2/data \
  --reports /tmp/dogson-pages-v2-fast/reports
python scripts/v2/live_publish_patch.py --legacy-root docs/data --root docs/v2/data
python scripts/v2/enrich_zones.py --legacy-root docs/data --output docs/v2/data
python scripts/v2/enrich_stock_detail_context.py --legacy-root docs/data --root docs/v2/data
python scripts/v2/restore_market_capital_context.py --legacy-root docs/data --root docs/v2/data
python scripts/v2/normalize_close_snapshot_by_close_date.py --root docs/v2/data
python scripts/v2/stamp_version_contract.py --root docs/v2/data
python scripts/v2/validate_bundle.py --root docs/v2/data
python scripts/v2/validate_market_capital_context.py --root docs/v2/data

# Production UI is deliberately single-writer. Old overlay files may remain in
# git history, but they must not be loaded by index.html or use MutationObserver
# against production-owned DOM regions.
node --check docs/v2/app.js
node --check docs/v2/market-capital-renderer.js
node --check docs/v2/stock-detail-renderer.js
node --check docs/v2/radar-transparency-v7.js
node --check docs/v2/chip-freshness-provenance.js
python scripts/v2/validate_single_writer_ui.py
python -m py_compile scripts/v2/enrich_stock_detail_context.py
python -m py_compile scripts/v2/restore_market_capital_context.py
python -m py_compile scripts/v2/validate_mission_evidence.py
python -m py_compile scripts/v2/rebuild_close_rank_views.py

python - <<'PY'
import json
from pathlib import Path
root=Path('docs/v2/data')
m=json.loads((root/'current_manifest.json').read_text(encoding='utf-8'))
src=json.loads(Path('docs/data/intraday.json').read_text(encoding='utf-8'))
day=json.loads(Path('docs/data/daytrade.json').read_text(encoding='utf-8'))
source_asof=str(src.get('as_of') or '')
source_date=str(src.get('trade_date') or '')[:10]
day_date=str(day.get('trade_date') or day.get('source_trade_date') or '')[:10]
vi=m['datasets']['decision_intraday_summary']
vd=m['datasets']['decision_daytrade_summary']
vi_asof=str(vi.get('as_of') or '')
vd_asof=str(vd.get('as_of') or '')
print('FAST V2 source lock:', {'build':m.get('active_build_id'),'source':source_asof,'intraday':vi_asof,'daytrade':vd_asof,'phase':m.get('session_phase')})
if source_date != day_date:
    raise SystemExit(f'fast V2 source dates disagree: intraday={source_date} daytrade={day_date}')
if vi_asof != source_asof or vd_asof != source_asof:
    raise SystemExit(f'fast V2 did not bind current MIS clock: source={source_asof} intraday={vi_asof} daytrade={vd_asof}')
for key in ('decision_intraday_summary','decision_intraday_index','decision_intraday_detail','stock_detail_intraday','zone_intraday','market_intraday_context','capital_intraday_context'):
    if key not in m.get('datasets',{}):
        raise SystemExit(f'fast V2 missing dataset: {key}')
PY

# Keep V2 outside the legacy service worker cache path. This avoids an older
# static response masking a newly published Atomic Build on mobile.
python - <<'PY'
from pathlib import Path
p=Path('docs/sw.js')
s=p.read_text(encoding='utf-8')
needle="  const url=new URL(req.url);\n  if(url.pathname.includes('/data/'))"
guarded="  const url=new URL(req.url);\n  if(url.pathname.includes('/v2/'))return;\n  if(url.pathname.includes('/data/'))"
if guarded not in s:
    if needle not in s:
        raise SystemExit('legacy sw fetch handler shape changed')
    s=s.replace(needle,guarded,1)
    p.write_text(s,encoding='utf-8')
PY

echo "Fast V2 Atomic Build ready: $(python -c 'import json; print(json.load(open("docs/v2/data/current_manifest.json"))["active_build_id"])')"
