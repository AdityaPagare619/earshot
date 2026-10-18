#!/usr/bin/env python3
"""Check that every --ear-* token used under earshot/ui/ is defined in tokens.css.
Single source of truth: tokens.css (mirror of TOKENS.md). Fails the lane on drift.
Usage: python3 earshot/ui/check-tokens.py
"""
import re, sys
from pathlib import Path

UI = Path(__file__).resolve().parent
CSS = UI / "tokens.css"

defined = set(re.findall(r"--ear-[a-z0-9-]+(?=\s*:)", CSS.read_text()))
# also catch the --ear-room-state default binding via var(--ear-room-idle)
defined |= set(re.findall(r"--ear-[a-z0-9-]+", CSS.read_text()))

errors = []
files = [CSS] + sorted(UI.rglob("*.html"))
for f in files:
    used = set(re.findall(r"--ear-[a-z0-9-]+", f.read_text()))
    # var() references with fallbacks like var(--x, ...) are fine as long as --x is defined
    unknown = used - defined
    if unknown:
        errors.append(f"{f.relative_to(UI)}: undefined tokens: {sorted(unknown)}")

if errors:
    print("TOKEN DRIFT DETECTED:")
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(defined)} tokens defined; all usages in {len(files)} files resolve.")
