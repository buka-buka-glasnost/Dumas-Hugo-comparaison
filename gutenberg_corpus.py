#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a reviewable French-language Project Gutenberg corpus for Alexandre Dumas
and Victor Hugo.

Stage 1 (safe default): download the official machine-readable catalog and
create a candidate manifest. No book texts are downloaded in this stage.

Stage 2: after reviewing the manifest and setting include=1 for eligible works,
run:
    python gutenberg_corpus.py --download-approved

The script deliberately does not decide automatically whether a catalogue item
is a novel. Review titles, formats, multi-volume works, translations, duplicates,
and co-authored works before approving them.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional

CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CATALOG_PATH = DATA_DIR / "pg_catalog.csv"
CANDIDATES_PATH = DATA_DIR / "corpus_candidates.csv"
APPROVED_PATH = DATA_DIR / "corpus_manifest.csv"

# Identify catalogue records by author names, not by titles.
AUTHOR_PATTERNS = {
    "Alexandre Dumas": re.compile(r"\bDumas,\s*Alexandre\b", re.IGNORECASE),
    "Victor Hugo": re.compile(r"\bHugo,\s*Victor\b", re.IGNORECASE),
}

# Project Gutenberg's terms request a proper user-agent for automated tools.
# Replace the contact placeholder with a project page or contact address before
# running downloads.
USER_AGENT = "DumasHugoCorpusResearch/0.1 (academic research; contact: replace-me)"
REQUEST_TIMEOUT = 45
DOWNLOAD_PAUSE_SECONDS = 2.5
MAX_DOWNLOADS_PER_RUN = 80  # conservative limit; rerun later for more


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def get_field(row: Dict[str, str], *possible_names: str) -> str:
    """Read a field while tolerating small variations in catalogue headers."""
    normalized = {norm_key(k): (v or "").strip() for k, v in row.items() if k}
    for name in possible_names:
        value = normalized.get(norm_key(name))
        if value is not None:
            return value
    return ""


def fetch(url: str, *, user_agent: str = USER_AGENT) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/csv,text/plain,application/octet-stream,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def download_catalog(force: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CATALOG_PATH.exists() and not force:
        print(f"Using existing catalogue: {CATALOG_PATH}")
        return CATALOG_PATH

    print("Downloading the official Project Gutenberg CSV catalogue...")
    try:
        content = fetch(CATALOG_URL)
    except Exception as exc:
        raise RuntimeError(
            f"Could not download the catalogue from {CATALOG_URL}\n"
            "Download it manually from Project Gutenberg's Offline Catalogs page "
            "and save it as data/pg_catalog.csv."
        ) from exc

    CATALOG_PATH.write_bytes(content)
    print(f"Saved catalogue: {CATALOG_PATH} ({len(content):,} bytes)")
    return CATALOG_PATH


def read_catalog(path: Path) -> List[Dict[str, str]]:
    # utf-8-sig also handles a possible UTF-8 BOM.
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Catalogue CSV has no header row.")
        return [dict(row) for row in reader]


def author_for(authors: str) -> Optional[str]:
    for display_name, pattern in AUTHOR_PATTERNS.items():
        if pattern.search(authors or ""):
            return display_name
    return None


def make_candidate_rows(rows: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    candidates = []
    seen = set()

    for row in rows:
        ebook_id = get_field(row, "Text#", "Text", "EBook-No", "EBook No", "ID")
        title = get_field(row, "Title")
        language = get_field(row, "Language", "Languages")
        authors = get_field(row, "Authors", "Author")

        # Keep only exact French-language catalogue entries.
        languages = {x.strip().lower() for x in re.split(r"[,;| ]+", language) if x.strip()}
        if "fr" not in languages:
            continue

        author = author_for(authors)
        if not author:
            continue

        try:
            ebook_id_int = int(re.sub(r"\D", "", ebook_id))
        except ValueError:
            continue

        # Avoid duplicate rows for the same catalogue ID.
        if ebook_id_int in seen:
            continue
        seen.add(ebook_id_int)

        subjects = get_field(row, "Subjects", "Subject")
        bookshelves = get_field(row, "Bookshelves", "Bookshelf")
        issued = get_field(row, "Issued", "Release Date")
        candidates.append({
            "ebook_id": str(ebook_id_int),
            "author": author,
            "title": title,
            "language": "fr",
            "catalogue_authors": authors,
            "issued": issued,
            "subjects": subjects,
            "bookshelves": bookshelves,
            "catalogue_url": f"https://www.gutenberg.org/ebooks/{ebook_id_int}",
            "text_url": f"https://www.gutenberg.org/cache/epub/{ebook_id_int}/pg{ebook_id_int}.txt",
            "include": "0",
            "work_type": "",  # Fill after manual review: novel, short fiction, drama, other
            "notes": "",
            "download_status": "not_downloaded",
        })

    candidates.sort(key=lambda x: (x["author"], x["title"].casefold(), int(x["ebook_id"])))
    return candidates


def write_candidates(candidates: List[Dict[str, str]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "ebook_id", "author", "title", "language", "catalogue_authors", "issued",
        "subjects", "bookshelves", "catalogue_url", "text_url", "include",
        "work_type", "notes", "download_status",
    ]
    with CANDIDATES_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)
    print(f"Candidate manifest: {CANDIDATES_PATH}")
    print(f"French-language candidate records: {len(candidates)}")
    for author in AUTHOR_PATTERNS:
        count = sum(1 for item in candidates if item["author"] == author)
        print(f"  {author}: {count}")


def load_approved_manifest() -> List[Dict[str, str]]:
    if not APPROVED_PATH.exists():
        raise FileNotFoundError(
            f"Missing {APPROVED_PATH}. Review {CANDIDATES_PATH}, set include=1 "
            "for works you want, then save the reviewed file as corpus_manifest.csv."
        )
    with APPROVED_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader if (row.get("include") or "").strip() == "1"]


def safe_filename(ebook_id: str, title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_")[:90] or "ebook"
    return f"{ebook_id}_{slug}.txt"


def download_approved() -> None:
    approved = load_approved_manifest()
    if not approved:
        print("No approved rows found. Set include=1 in data/corpus_manifest.csv.")
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    downloaded_this_run = 0
    success = 0
    failures = []

    for item in approved:
        if downloaded_this_run >= MAX_DOWNLOADS_PER_RUN:
            print(f"Reached conservative run limit ({MAX_DOWNLOADS_PER_RUN} downloads).")
            print("Run again later for remaining approved titles.")
            break

        ebook_id = (item.get("ebook_id") or "").strip()
        title = (item.get("title") or "").strip()
        url = (item.get("text_url") or "").strip()
        if not ebook_id.isdigit():
            failures.append((ebook_id, title, "invalid ebook_id"))
            continue
        if not url:
            url = f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt"

        output_path = RAW_DIR / safe_filename(ebook_id, title)
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"SKIP (already exists): {output_path.name}")
            success += 1
            continue

        if downloaded_this_run:
            time.sleep(DOWNLOAD_PAUSE_SECONDS)

        print(f"Downloading {ebook_id}: {title}")
        try:
            content = fetch(url)
            # Avoid saving an HTML error page as a text file.
            sample = content[:500].lstrip().lower()
            if sample.startswith(b"<!doctype html") or sample.startswith(b"<html"):
                raise ValueError("server returned HTML rather than plain text")
            output_path.write_bytes(content)
            downloaded_this_run += 1
            success += 1
            print(f"  saved {output_path.name} ({len(content):,} bytes)")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            failures.append((ebook_id, title, str(exc)))
            print(f"  FAILED: {exc}")

    print(f"\nExisting/downloaded files: {success}")
    print(f"Failures: {len(failures)}")
    if failures:
        failure_path = DATA_DIR / "download_failures.csv"
        with failure_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["ebook_id", "title", "error"])
            writer.writerows(failures)
        print(f"Failure log: {failure_path}")
        print(
            "Some catalogue entries may use a different text-file path. "
            "Check the canonical catalogue page and update text_url in the manifest."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-catalog",
        action="store_true",
        help="Download a fresh copy of the official catalogue.",
    )
    parser.add_argument(
        "--download-approved",
        action="store_true",
        help="Download only rows with include=1 from data/corpus_manifest.csv.",
    )
    args = parser.parse_args()

    if args.download_approved:
        try:
            download_approved()
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        return 0

    try:
        catalog_path = download_catalog(force=args.refresh_catalog)
        rows = read_catalog(catalog_path)
        candidates = make_candidate_rows(rows)
        write_candidates(candidates)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("\nNext steps:")
    print("1. Open data/corpus_candidates.csv in Excel or LibreOffice.")
    print("2. Review every title; the script cannot determine whether it is a novel.")
    print("3. Set include=1 only for eligible works and fill work_type/notes.")
    print("4. Save the reviewed file as data/corpus_manifest.csv.")
    print("5. Replace the placeholder contact in USER_AGENT before automated downloads.")
    print("6. Run: python gutenberg_corpus.py --download-approved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
