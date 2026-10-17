#!/usr/bin/env python3
"""Sensitivity analysis for Dumas–Hugo MATTR comparisons.

Reads reports/work_statistics.csv and writes:
  reports/mattr_robustness_summary.csv
  reports/mattr_work_level.csv

No text processing or lemmatization is performed. This is an exploratory
sensitivity analysis; it does not make the works a random or independent sample.
"""
from pathlib import Path
import csv
import math
import statistics

ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "reports" / "work_statistics.csv"
SUMMARY_PATH = ROOT / "reports" / "mattr_robustness_summary.csv"
WORKS_PATH = ROOT / "reports" / "mattr_work_level.csv"
AUTHORS = ("Alexandre Dumas", "Victor Hugo")
METRICS = ("mattr_content_500", "mattr_content_1000", "mattr_content_no_person_500", "mattr_content_no_person_1000")
LENGTH_COLUMN = "total_tokens"


def num(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def med(values):
    return statistics.median(values) if values else None


def fmt(value):
    return "" if value is None else f"{value:.6f}"


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing {INPUT_PATH}. Put this script in the project root and ensure reports/work_statistics.csv exists.")
    with INPUT_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows found in {INPUT_PATH}")
    headers = set(rows[0])
    missing = [m for m in METRICS if m not in headers]
    if missing:
        raise ValueError("Missing MATTR columns: " + ", ".join(missing))
    if LENGTH_COLUMN not in headers:
        raise ValueError(f"Expected length column '{LENGTH_COLUMN}' is missing")

    works = []
    for row in rows:
        author = (row.get("author") or "").strip()
        if author not in AUTHORS:
            continue
        item = dict(row)
        item["_length"] = num(row.get(LENGTH_COLUMN))
        for metric in METRICS:
            item[metric] = num(row.get(metric))
        works.append(item)

    by_author = {a: sorted([r for r in works if r["author"] == a], key=lambda r: r["_length"] if r["_length"] is not None else -1, reverse=True) for a in AUTHORS}
    for author in AUTHORS:
        for rank, row in enumerate(by_author[author], start=1):
            row["length_rank_within_author"] = rank

    work_fields = ["analysis_work_id", "title_fr", "author", LENGTH_COLUMN, *METRICS, "length_rank_within_author"]
    with WORKS_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=work_fields, extrasaction="ignore")
        writer.writeheader()
        for row in works:
            out = dict(row)
            for m in METRICS:
                out[m] = fmt(row[m])
            writer.writerow(out)

    summary = []
    for metric in METRICS:
        a_rows = [r for r in by_author[AUTHORS[0]] if r[metric] is not None]
        b_rows = [r for r in by_author[AUTHORS[1]] if r[metric] is not None]
        av, bv = [r[metric] for r in a_rows], [r[metric] for r in b_rows]
        full = med(av) - med(bv) if av and bv else None
        longest_a = max(a_rows, key=lambda r: r["_length"] if r["_length"] is not None else -1) if a_rows else None
        longest_b = max(b_rows, key=lambda r: r["_length"] if r["_length"] is not None else -1) if b_rows else None

        def diff(remove_a=False, remove_b=False):
            xa = [r[metric] for r in a_rows if not (remove_a and r is longest_a)]
            xb = [r[metric] for r in b_rows if not (remove_b and r is longest_b)]
            return med(xa) - med(xb) if xa and xb else None

        loo = []
        for row in a_rows:
            xa = [r[metric] for r in a_rows if r is not row]
            if xa and bv:
                loo.append(med(xa) - med(bv))
        for row in b_rows:
            xb = [r[metric] for r in b_rows if r is not row]
            if av and xb:
                loo.append(med(av) - med(xb))
        both = diff(True, True)
        summary.append({
            "metric": metric, "n_dumas": len(av), "n_hugo": len(bv),
            "dumas_median_full": fmt(med(av)), "hugo_median_full": fmt(med(bv)),
            "median_difference_dumas_minus_hugo_full": fmt(full),
            "longest_dumas_work": longest_a.get("title_fr", "") if longest_a else "",
            "longest_hugo_work": longest_b.get("title_fr", "") if longest_b else "",
            "difference_without_longest_dumas": fmt(diff(remove_a=True)),
            "difference_without_longest_hugo": fmt(diff(remove_b=True)),
            "difference_without_both_longest": fmt(both),
            "leave_one_work_out_difference_min": fmt(min(loo) if loo else None),
            "leave_one_work_out_difference_max": fmt(max(loo) if loo else None),
            "direction_preserved_without_both_longest": "yes" if both is not None and both < 0 else "no",
            "direction_preserved_in_all_leave_one_out_checks": "yes" if loo and all(x < 0 for x in loo) else "no",
        })
    with SUMMARY_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)
    print(f"Read {len(rows)} rows from {INPUT_PATH}")
    print(f"Wrote {WORKS_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    print("Interpret as exploratory sensitivity checks, not proof of causality or generalizability.")

if __name__ == "__main__":
    main()
