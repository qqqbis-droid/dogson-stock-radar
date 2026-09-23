#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retry wrapper for v1.5.12.

The original v1.5.12 patch expected build_intraday() to begin immediately after
`return out`. Current build_data.py contains one blank line there, so loosen only
that boundary matcher and execute the otherwise unchanged patch.
"""
from pathlib import Path

src_path = Path(__file__).with_name("patch_v1512.py")
src = src_path.read_text(encoding="utf-8")
needle = r"return out\n(?=def build_intraday"
replacement = r"return out\n+(?=def build_intraday"
if needle not in src:
    raise SystemExit("v1.5.12 retry: expected boundary marker not found")
src = src.replace(needle, replacement, 1)
ns = {"__name__": "__main__", "__file__": str(src_path)}
exec(compile(src, str(src_path), "exec"), ns)
