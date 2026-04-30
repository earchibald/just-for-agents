#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
root = ROOT / "docs" / "research"
root.mkdir(parents=True, exist_ok=True)
index = root / "index.md"
lines = ["# Research Index", ""]

for subject_dir in sorted(path for path in root.iterdir() if path.is_dir()):
    round_files = []
    for candidate in subject_dir.glob("round_*.md"):
        match = re.match(r"round_(\d+)\.md$", candidate.name)
        if match:
            round_files.append((int(match.group(1)), candidate))
    round_files.sort(key=lambda item: item[0])
    if not round_files:
        continue

    title = subject_dir.name.replace("-", " ")
    brief = subject_dir / "brief.md"
    if brief.exists():
        match = re.search(r"^# Research Brief: (.+)$", brief.read_text(), re.MULTILINE)
        if match:
            title = match.group(1).strip()

    lines.append(f"## {title} ({subject_dir.name})")
    for round_number, round_file in round_files:
        summary = "Research round complete."
        for line in round_file.read_text().splitlines():
            if line.startswith("SUMMARY:"):
                summary = line.split("SUMMARY:", 1)[1].strip() or summary
        lines.append(f"- [Round {round_number}]({round_file.as_posix()}): {summary}")
    lines.append("")

index.write_text("\n".join(lines).rstrip() + "\n")
