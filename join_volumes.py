#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Combine cleaned Gutenberg volumes into one file per analytical work.

Run from the project root:
    python join_volumes.py

Inputs:
    corpus_manifest_reviewed_v2.csv (project root, or data/)
    data/cleaned/*.txt (or cleaned/*.txt)

Outputs:
    data/works/<analysis_work_id_v2>.txt
    data/work_build_report.csv
    data/work_volume_map.csv

Only manifest rows with download_v2=YES are used. Source volume files remain
unchanged. Volumes are joined in volume_order_v2 order; single-volume works
are copied as the same plain-text analytical unit. No metadata is inserted
into the text, to avoid contaminating NLP features.
"""
from __future__ import annotations
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST_CANDIDATES = [ROOT / "corpus_manifest_reviewed_v2.csv", ROOT / "data" / "corpus_manifest_reviewed_v2.csv"]
CLEANED_CANDIDATES = [ROOT / "data" / "cleaned", ROOT / "cleaned"]
OUTPUT_DIR = ROOT / "data" / "works"
REPORT_PATH = ROOT / "data" / "work_build_report.csv"
MAP_PATH = ROOT / "data" / "work_volume_map.csv"


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def normalized_id(value: str) -> str:
    return str(value or "").strip()


def find_text_file(cleaned_dir: Path, ebook_id: str) -> Path | None:
    # IDs are the stable key; titles can contain accents and punctuation.
    matches = sorted(p for p in cleaned_dir.rglob("*.txt") if p.is_file() and re.match(rf"^{re.escape(ebook_id)}_", p.name))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(f"Multiple cleaned files match ebook_id={ebook_id}: {matches}")
    return None


def main() -> int:
    manifest_path = next((p for p in MANIFEST_CANDIDATES if p.is_file()), None)
    cleaned_dir = next((p for p in CLEANED_CANDIDATES if p.is_dir()), None)
    if manifest_path is None:
        print("ERROR: Could not find corpus_manifest_reviewed_v2.csv in project root or data/.", file=sys.stderr)
        return 1
    if cleaned_dir is None:
        print("ERROR: Could not find data/cleaned/ or cleaned/.", file=sys.stderr)
        return 1

    approved = [r for r in read_csv(manifest_path) if normalized_id(r.get("download_v2")).upper() == "YES"]
    groups = defaultdict(list)
    report = []
    volume_map = []

    for row in approved:
        ebook_id = normalized_id(row.get("ebook_id"))
        work_id = normalized_id(row.get("analysis_work_id_v2"))
        author = normalized_id(row.get("author"))
        title = normalized_id(row.get("title"))
        if not ebook_id or not work_id:
            report.append({"analysis_work_id": work_id, "author": author, "status": "ERROR_MISSING_ID", "volume_count_expected": "", "volume_count_found": 0, "output_file": "", "notes": f"Missing ebook_id or analysis_work_id for title={title}"})
            continue
        try:
            path = find_text_file(cleaned_dir, ebook_id)
        except RuntimeError as exc:
            report.append({"analysis_work_id": work_id, "author": author, "status": "ERROR_DUPLICATE_FILE", "volume_count_expected": "", "volume_count_found": 0, "output_file": "", "notes": str(exc)})
            continue
        if path is None:
            report.append({"analysis_work_id": work_id, "author": author, "status": "ERROR_MISSING_VOLUME", "volume_count_expected": "", "volume_count_found": 0, "output_file": "", "notes": f"No cleaned file found for ebook_id={ebook_id}, title={title}"})
            continue
        try:
            order_raw = normalized_id(row.get("volume_order_v2"))
            order = float(order_raw) if order_raw else None
        except ValueError:
            order = None
        try:
            text = path.read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeError) as exc:
            report.append({"analysis_work_id": work_id, "author": author, "status": "ERROR_READ", "volume_count_expected": "", "volume_count_found": 0, "output_file": "", "notes": f"{path.name}: {exc}"})
            continue
        if not text:
            report.append({"analysis_work_id": work_id, "author": author, "status": "ERROR_EMPTY_VOLUME", "volume_count_expected": "", "volume_count_found": 0, "output_file": "", "notes": f"Empty cleaned file: {path.name}"})
            continue
        groups[work_id].append({"ebook_id": ebook_id, "author": author, "title": title, "order": order, "path": path, "text": text})

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Expected group membership comes from the approved manifest. A work is
    # only written if every approved volume for it was found and read.
    expected_by_work = defaultdict(list)
    for row in approved:
        wid = normalized_id(row.get("analysis_work_id_v2"))
        if wid:
            expected_by_work[wid].append(row)

    error_work_ids = {r["analysis_work_id"] for r in report if r.get("analysis_work_id")}
    for work_id, rows in sorted(groups.items()):
        expected_rows = expected_by_work[work_id]
        if work_id in error_work_ids or len(rows) != len(expected_rows):
            report.append({"analysis_work_id": work_id, "author": rows[0]["author"], "status": "ERROR_INCOMPLETE_WORK", "volume_count_expected": len(expected_rows), "volume_count_found": len(rows), "output_file": "", "notes": "At least one approved volume is missing or unreadable; no combined file written."})
            continue
        # If all volumes have explicit order, sort numerically; otherwise stable ebook ID order.
        if all(r["order"] is not None for r in rows):
            rows.sort(key=lambda r: (r["order"], int(r["ebook_id"])))
        else:
            rows.sort(key=lambda r: int(r["ebook_id"]))
        orders = [r["order"] for r in rows if r["order"] is not None]
        if len(orders) != len(set(orders)):
            report.append({"analysis_work_id": work_id, "author": rows[0]["author"], "status": "ERROR_DUPLICATE_VOLUME_ORDER", "volume_count_expected": len(expected_rows), "volume_count_found": len(rows), "output_file": "", "notes": f"Duplicate volume order values: {orders}; no combined file written."})
            continue
        combined = "\n\n".join(r["text"] for r in rows).strip() + "\n"
        destination = OUTPUT_DIR / f"{work_id}.txt"
        destination.write_text(combined, encoding="utf-8", newline="\n")
        report.append({"analysis_work_id": work_id, "author": rows[0]["author"], "status": "BUILT", "volume_count_expected": len(expected_rows), "volume_count_found": len(rows), "output_file": str(destination.relative_to(ROOT)), "notes": ""})
        for sequence, row in enumerate(rows, start=1):
            volume_map.append({"analysis_work_id": work_id, "author": row["author"], "combined_sequence": sequence, "ebook_id": row["ebook_id"], "manifest_volume_order": "" if row["order"] is None else row["order"], "source_title": row["title"], "source_file": str(row["path"].relative_to(ROOT)), "output_file": str(destination.relative_to(ROOT))})

    fields = ["analysis_work_id", "author", "status", "volume_count_expected", "volume_count_found", "output_file", "notes"]
    with REPORT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(report)
    map_fields = ["analysis_work_id", "author", "combined_sequence", "ebook_id", "manifest_volume_order", "source_title", "source_file", "output_file"]
    with MAP_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=map_fields); writer.writeheader(); writer.writerows(volume_map)

    built = sum(r.get("status") == "BUILT" for r in report)
    errors = [r for r in report if str(r.get("status", "")).startswith("ERROR")]
    print("Work-building summary")
    print(f"Approved volume records: {len(approved)}")
    print(f"Analytical works built: {built}")
    print(f"Errors requiring review: {len(errors)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Build report: {REPORT_PATH}")
    print(f"Volume map: {MAP_PATH}")
    if errors:
        print("Review ERROR rows in work_build_report.csv before proceeding.")
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
