#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download the approved Project Gutenberg texts listed in corpus_manifest_reviewed_v2.csv.

Run from the folder containing this script and the manifest:
    python download_approved_texts.py

Only rows with download_v2 == YES are downloaded. Existing non-empty files are
skipped. Requests are spaced out, failures are logged, and the original
individual volumes are retained separately. This script does NOT concatenate
volumes; concatenation belongs in the preprocessing stage after each download
has been checked.
"""

from __future__ import annotations

import csv
import http.client
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "corpus_manifest_reviewed_v2.csv"
RAW_DIR = ROOT / "data" / "raw"
FAILURES_CSV = ROOT / "data" / "download_failures.csv"

# Replace this placeholder with a real project URL or contact address.
USER_AGENT = "DumasHugoCorpusResearch/0.1 (academic research; contact: bogdan.ristich@gmail.com)"
TIMEOUT_SECONDS = 60
PAUSE_SECONDS = 3.0
MAX_DOWNLOADS_PER_RUN = 20


def clean_filename(value: str, limit: int = 90) -> str:
    value = re.sub(r"[^A-Za-z0-9À-ž_-]+", "_", value or "").strip("_")
    return value[:limit] or "untitled"


def fetch(url: str, retries: int = 5) -> bytes:
    """
    Fetch a complete response, retrying transient connection failures.
    The caller only writes the returned bytes after this function succeeds,
    so an incomplete response is not saved as a completed raw text file.
    """
    last_error = None

    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/plain,*/*",
                "Connection": "close",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                chunks = []
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                data = b"".join(chunks)

                # If Content-Length is known, make sure the body is complete.
                expected = response.headers.get("Content-Length")
                if expected and len(data) != int(expected):
                    raise http.client.IncompleteRead(data, int(expected) - len(data))
                return data

        except (
            http.client.IncompleteRead,
            http.client.HTTPException,
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
            OSError,
        ) as exc:
            last_error = exc
            if attempt == retries:
                break
            wait = min(2 ** (attempt - 1), 30)
            print(
                f"  connection interrupted (attempt {attempt}/{retries}): {exc}; "
                f"retrying in {wait}s..."
            )
            time.sleep(wait)

    raise RuntimeError(f"Could not download a complete response after {retries} attempts: {last_error}")


def is_html(data: bytes) -> bool:
    head = data[:1000].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def main() -> int:
    if not MANIFEST.exists():
        print(f"ERROR: manifest not found: {MANIFEST}", file=sys.stderr)
        print("Place corpus_manifest_reviewed_v2.csv beside this script.", file=sys.stderr)
        return 1

    # Require an explicit contact string before making automated requests.
    if "replace-me" in USER_AGENT:
        print("ERROR: Edit USER_AGENT in this script and replace 'replace-me' with a project URL or contact.", file=sys.stderr)
        return 2

    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    approved = [r for r in rows if (r.get("download_v2") or "").strip().upper() == "YES"]
    if not approved:
        print("No rows with download_v2=YES found.")
        return 0

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    downloaded_now = 0
    skipped = 0
    success = 0

    print(f"Approved records: {len(approved)}")
    print(f"Output directory: {RAW_DIR}")
    print(f"Per-run limit: {MAX_DOWNLOADS_PER_RUN}")
    print("The script preserves each catalogue record as a separate raw text file.\n")

    for row in approved:
        if downloaded_now >= MAX_DOWNLOADS_PER_RUN:
            print(f"\nReached per-run limit ({MAX_DOWNLOADS_PER_RUN}). Run again to continue.")
            break

        ebook_id = (row.get("ebook_id") or "").strip()
        title = (row.get("title") or "").strip()
        author = (row.get("author") or "").strip()
        url = (row.get("text_url") or "").strip()
        work_id = (row.get("analysis_work_id_v2") or "").strip()

        if not ebook_id.isdigit():
            failures.append([ebook_id, title, url, "Invalid ebook_id"])
            continue
        if not url:
            url = f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt"

        filename = f"{ebook_id}_{clean_filename(author, 35)}_{clean_filename(title)}.txt"
        destination = RAW_DIR / filename

        if destination.exists() and destination.stat().st_size > 0:
            print(f"SKIP existing: {filename}")
            skipped += 1
            success += 1
            continue

        if downloaded_now > 0:
            time.sleep(PAUSE_SECONDS)

        print(f"GET {ebook_id} | {author} | {title}")
        try:
            data = fetch(url)
            if not data:
                raise ValueError("empty response")
            if is_html(data):
                raise ValueError("server returned HTML, not plain text")
            # Gutenberg texts should generally be UTF-8; reject obviously binary data.
            try:
                data.decode("utf-8-sig")
            except UnicodeDecodeError:
                data.decode("utf-8", errors="strict")
            destination.write_bytes(data)
            downloaded_now += 1
            success += 1
            print(f"  saved {destination.name} ({len(data):,} bytes)")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError, UnicodeError, RuntimeError, http.client.HTTPException) as exc:
            failures.append([ebook_id, title, url, str(exc)])
            print(f"  FAILED: {exc}")

    if failures:
        with FAILURES_CSV.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ebook_id", "title", "text_url", "error"])
            writer.writerows(failures)

    print("\nSummary")
    print(f"Successful or already present: {success}")
    print(f"New downloads this run: {downloaded_now}")
    print(f"Skipped existing: {skipped}")
    print(f"Failures: {len(failures)}")
    if failures:
        print(f"Failure log: {FAILURES_CSV}")
        print("Check the corresponding Gutenberg ebook page and update text_url in the manifest.")
    print("\nNext: verify text encoding and Gutenberg boundaries before cleaning or joining volumes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
