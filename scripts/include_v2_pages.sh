#!/usr/bin/env bash
set -euo pipefail

# Every GitHub Pages publisher replaces the whole site artifact. Always overlay the
# validated Clean Build 2.0 tree so a legacy/root deployment cannot erase /v2/.
git fetch origin clean-build-v2 --depth=1
rm -rf docs/v2
git archive FETCH_HEAD docs/v2 | tar -xf -

test -f docs/v2/index.html
test -f docs/v2/data/current_manifest.json

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
echo "Included Clean Build 2.0 in Pages artifact: $(python -c 'import json; print(json.load(open("docs/v2/data/current_manifest.json")).get("active_build_id", "unknown"))')"
