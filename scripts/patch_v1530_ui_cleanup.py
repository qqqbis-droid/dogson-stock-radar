#!/usr/bin/env python3
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'docs/index.html'
s=p.read_text(encoding='utf-8')
# Previous incremental patches left literal backslash-n tokens before JS function declarations.
# They are never valid separators in inline JavaScript, so normalize only this narrow pattern.
s=re.sub(r'\\n(?=function\s)', '\n', s)
p.write_text(s,encoding='utf-8')
print('v1.5.30 UI escape cleanup applied')
