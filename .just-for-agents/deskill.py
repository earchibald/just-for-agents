#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUSTFILE = ROOT / "Justfile"

target = sys.argv[1]
lines = JUSTFILE.read_text().splitlines(keepends=True)

new_lines = []
skip = False
for i, line in enumerate(lines):
    if "[doc(" in line and i + 1 < len(lines) and re.match(rf"^{target}(\s|:)", lines[i + 1].strip()):
        skip = True
        continue
    if skip:
        if re.match(rf"^{target}(\s|:)", line.strip()):
            continue
        if line.startswith("    "):
            continue
        skip = False
    new_lines.append(line)

JUSTFILE.write_text("".join(new_lines))
