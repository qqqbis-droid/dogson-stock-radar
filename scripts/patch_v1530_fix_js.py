#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repair the literal newline escape accidentally emitted by the v1.5.30 final UI patch."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "docs" / "index.html"

s = P.read_text(encoding="utf-8")
bad = r"\nfunction chipHTML"
good = "\nfunction chipHTML"

if bad in s:
    s = s.replace(bad, good)
P.write_text(s, encoding="utf-8")
print("v1.5.30 inline JS newline repaired")
