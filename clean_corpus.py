#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean Project Gutenberg wrappers from approved raw text files.

Run from the project root:
    python clean_corpus.py

Reads:
    data/raw/*.txt  (or raw/*.txt if data/raw/ does not exist)

Writes cleaned texts to:
    data/cleaned/

The original raw files are never modified. If START/END markers cannot be
reliably identified, the script skips that file rather than silently treating
the entire file as the literary text.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_CANDIDATES = [ROOT / "data" / "raw", ROOT / "raw"]
OUTPUT_DIR = ROOT / "data" / "cleaned"
REPORT_PATH = ROOT / "data" / "cleaning_report.csv"

START_RE = re.compile(
    r"^\s*\*{3}\s*START OF\b.*PROJECT GUTENBERG.*\*{3}\s*$",
    re.IGNORECASE,
)
END_RE = re.compile(
    r"^\s*\*{3}\s*END OF\b.*PROJECT GUTENBERG.*\*{3}\s*$",
    re.IGNORECASE,
)


def locate_boundaries(lines: list[str]) -> tuple[int | None, int | None]:
    """Return (first line after START, line index of END after START)."""
    start_after = None
    for i, line in enumerate(lines):
        if start_after is None:
            if START_RE.search(line):
                start_after = i + 1
        elif END_RE.search(line):
            return start_after, i
    return start_after, None


def main() -> int:
    raw_dir = next((p for p in RAW_CANDIDATES if p.is_dir()), None)
    if raw_dir is None:
        print("ERROR: Could not find data/raw/ or raw/.", file=sys.stderr)
        return 1

    files = sorted(p for p in raw_dir.rglob("*.txt") if p.is_file())
    if not files:
        print(f"ERROR: No .txt files found in {raw_dir}", file=sys.stderr)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_rows = []
    cleaned_count = 0
    skipped_count = 0

    for source in files:
        relative = source.relative_to(raw_dir)
        destination = OUTPUT_DIR / relative
        try:
            text = source.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            report_rows.append({
                "source_file": str(relative),
                "output_file": "",
                "status": "SKIPPED_READ_ERROR",
                "source_characters": "",
                "cleaned_characters": "",
                "start_marker_found": False,
                "end_marker_found": False,
                "notes": str(exc),
            })
            skipped_count += 1
            print(f"SKIP unreadable: {relative} ({exc})")
            continue

        lines = text.splitlines()
        start_after, end_at = locate_boundaries(lines)
        start_found = start_after is not None
        end_found = end_at is not None

        if not start_found or not end_found or start_after is None or end_at is None or end_at < start_after:
            report_rows.append({
                "source_file": str(relative),
                "output_file": "",
                "status": "SKIPPED_BOUNDARY_ERROR",
                "source_characters": len(text),
                "cleaned_characters": "",
                "start_marker_found": start_found,
                "end_marker_found": end_found,
                "notes": "Could not identify a valid START/END pair; raw file left unchanged.",
            })
            skipped_count += 1
            print(f"SKIP boundary issue: {relative}")
            continue

        cleaned = "\n".join(lines[start_after:end_at]).strip()
        if not cleaned:
            report_rows.append({
                "source_file": str(relative),
                "output_file": "",
                "status": "SKIPPED_EMPTY_RESULT",
                "source_characters": len(text),
                "cleaned_characters": 0,
                "start_marker_found": start_found,
                "end_marker_found": end_found,
                "notes": "Extracted text was empty; raw file left unchanged.",
            })
            skipped_count += 1
            print(f"SKIP empty extraction: {relative}")
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(cleaned + "\n", encoding="utf-8", newline="\n")
        report_rows.append({
            "source_file": str(relative),
            "output_file": str(destination.relative_to(ROOT)),
            "status": "CLEANED",
            "source_characters": len(text),
            "cleaned_characters": len(cleaned),
            "start_marker_found": start_found,
            "end_marker_found": end_found,
            "notes": "",
        })
        cleaned_count += 1
        print(f"OK {relative}: {len(text):,} -> {len(cleaned):,} characters")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_file", "output_file", "status", "source_characters",
        "cleaned_characters", "start_marker_found", "end_marker_found", "notes",
    ]
    with REPORT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report_rows)

    print("\nCleaning summary")
    print(f"Raw files: {len(files)}")
    print(f"Cleaned successfully: {cleaned_count}")
    print(f"Skipped for review: {skipped_count}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Report: {REPORT_PATH}")
    print("Review skipped files and sample cleaned texts before lemmatization.")
    return 0 if skipped_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
