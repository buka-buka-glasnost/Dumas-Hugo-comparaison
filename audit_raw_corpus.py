#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit downloaded Project Gutenberg text files against the reviewed manifest.

Run from the project root:
    python audit_raw_corpus.py

Looks for data/raw/ first, then raw/. It does not modify or delete source files.
Creates data/raw_audit_report.csv and prints a concise summary.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST_CANDIDATES = [
    ROOT / "corpus_manifest_reviewed_v2.csv",
    ROOT / "data" / "corpus_manifest_reviewed_v2.csv",
    ROOT / "data" / "corpus_manifest.csv",
]
RAW_CANDIDATES = [ROOT / "data" / "raw", ROOT / "raw"]
REPORT_PATH = ROOT / "data" / "raw_audit_report.csv"

START_RE = re.compile(rb"\*\*\*\s*START OF (?:THE )?PROJECT GUTENBERG", re.IGNORECASE)
END_RE = re.compile(rb"\*\*\*\s*END OF (?:THE )?PROJECT GUTENBERG", re.IGNORECASE)


def first_existing(paths):
    return next((p for p in paths if p.exists()), None)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    manifest_path = first_existing(MANIFEST_CANDIDATES)
    raw_dir = first_existing(RAW_CANDIDATES)

    if manifest_path is None:
        print("ERROR: Could not find corpus manifest.")
        print("Place corpus_manifest_reviewed_v2.csv beside this script or in data/.")
        return 1
    if raw_dir is None:
        print("ERROR: Could not find data/raw/ or raw/.")
        print("Set RAW_CANDIDATES in this script if your raw folder is elsewhere.")
        return 1

    with manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
        manifest_rows = list(csv.DictReader(f))

    expected = {}
    for row in manifest_rows:
        if (row.get("download_v2") or "").strip().upper() != "YES":
            continue
        ebook_id = (row.get("ebook_id") or "").strip()
        if ebook_id.isdigit():
            expected[ebook_id] = row

    files = sorted(p for p in raw_dir.rglob("*.txt") if p.is_file())
    files_by_id = defaultdict(list)
    for path in files:
        match = re.match(r"^(\d+)_", path.name)
        if match:
            files_by_id[match.group(1)].append(path)

    rows = []
    duplicate_hashes = defaultdict(list)
    seen_ids = set()

    for ebook_id, record in expected.items():
        matches = files_by_id.get(ebook_id, [])
        if not matches:
            rows.append({
                "ebook_id": ebook_id,
                "title": record.get("title", ""),
                "filename": "",
                "status": "MISSING",
                "bytes": "",
                "utf8_ok": "",
                "gutenberg_start_marker": "",
                "gutenberg_end_marker": "",
                "sha256": "",
                "notes": "No .txt file with this ebook ID prefix was found."
            })
            continue

        for path in matches:
            seen_ids.add(ebook_id)
            size = path.stat().st_size
            notes = []
            utf8_ok = True
            start_found = False
            end_found = False
            sha = ""

            if size == 0:
                notes.append("Empty file")
            try:
                data = path.read_bytes()
                data.decode("utf-8-sig")
            except UnicodeDecodeError:
                utf8_ok = False
                notes.append("Not valid UTF-8; inspect encoding")
                data = b""
            except OSError as exc:
                utf8_ok = False
                notes.append(f"Read error: {exc}")
                data = b""

            if data:
                start_found = bool(START_RE.search(data[: min(len(data), 200_000)]))
                end_found = bool(END_RE.search(data[max(0, len(data) - 200_000):]))
                if not start_found:
                    notes.append("Gutenberg START marker not found near beginning")
                if not end_found:
                    notes.append("Gutenberg END marker not found near end")
                sha = sha256_file(path)
                duplicate_hashes[sha].append(path.name)

            status = "OK" if size > 0 and utf8_ok and start_found and end_found else "CHECK"
            rows.append({
                "ebook_id": ebook_id,
                "title": record.get("title", ""),
                "filename": str(path.relative_to(ROOT)),
                "status": status,
                "bytes": size,
                "utf8_ok": utf8_ok,
                "gutenberg_start_marker": start_found,
                "gutenberg_end_marker": end_found,
                "sha256": sha,
                "notes": "; ".join(notes)
            })

        if len(matches) > 1:
            for row in rows:
                if row["ebook_id"] == ebook_id:
                    row["status"] = "CHECK"
                    extra = f"Multiple files share ebook ID prefix ({len(matches)} files)"
                    row["notes"] = (row["notes"] + "; " + extra).strip("; ")

    extra_ids = sorted(set(files_by_id) - set(expected))
    for ebook_id in extra_ids:
        for path in files_by_id[ebook_id]:
            rows.append({
                "ebook_id": ebook_id,
                "title": "",
                "filename": str(path.relative_to(ROOT)),
                "status": "EXTRA",
                "bytes": path.stat().st_size,
                "utf8_ok": "",
                "gutenberg_start_marker": "",
                "gutenberg_end_marker": "",
                "sha256": "",
                "notes": "File ID is not marked download_v2=YES in the current manifest."
            })

    duplicate_groups = [names for names in duplicate_hashes.values() if len(names) > 1]
    if duplicate_groups:
        print("WARNING: byte-identical duplicate files detected:")
        for names in duplicate_groups:
            print("  " + " | ".join(names))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "ebook_id", "title", "filename", "status", "bytes", "utf8_ok",
        "gutenberg_start_marker", "gutenberg_end_marker", "sha256", "notes"
    ]
    with REPORT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    counts = defaultdict(int)
    for row in rows:
        counts[row["status"]] += 1

    print(f"Manifest: {manifest_path}")
    print(f"Raw directory: {raw_dir}")
    print(f"Expected approved records: {len(expected)}")
    print(f"Text files found: {len(files)}")
    print("Audit results:")
    for status in ("OK", "CHECK", "MISSING", "EXTRA"):
        print(f"  {status}: {counts[status]}")
    print(f"Report written to: {REPORT_PATH}")
    print("\nThis is a structural audit only; OK does not prove that the edition is complete or bibliographically correct.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
