#!/usr/bin/env python3
"""Compare per-work MATTR values between Alexandre Dumas and Victor Hugo.

Reads the existing reports/work_statistics.csv. Does not reprocess texts.
Writes reports/mattr_author_comparison.csv.

The permutation test evaluates the difference in group means. The bootstrap
interval is a percentile interval for the difference in group medians.
With unequal and small group sizes, interpret all inferential results cautiously.
"""
from pathlib import Path
import csv
import math
import random
import statistics

ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "reports" / "work_statistics.csv"
OUTPUT_PATH = ROOT / "reports" / "mattr_author_comparison.csv"

AUTHOR_A = "Alexandre Dumas"
AUTHOR_B = "Victor Hugo"
METRICS = (
    "mattr_content_500",
    "mattr_content_1000",
    "mattr_content_no_person_500",
    "mattr_content_no_person_1000",
)
N_PERMUTATIONS = 20_000
N_BOOTSTRAPS = 10_000
SEED = 20261016


def mean(values):
    return statistics.mean(values) if values else float("nan")


def median(values):
    return statistics.median(values) if values else float("nan")


def cliff_delta(a, b):
    """Cliff's delta: P(a > b) - P(a < b)."""
    greater = sum(x > y for x in a for y in b)
    less = sum(x < y for x in a for y in b)
    return (greater - less) / (len(a) * len(b))


def permutation_p_value_mean_difference(a, b, rng):
    """Two-sided Monte Carlo permutation test for difference in means."""
    observed = mean(a) - mean(b)
    pooled = list(a) + list(b)
    n_a = len(a)
    extreme = 0

    for _ in range(N_PERMUTATIONS):
        shuffled = pooled[:]
        rng.shuffle(shuffled)
        difference = mean(shuffled[:n_a]) - mean(shuffled[n_a:])
        if abs(difference) >= abs(observed):
            extreme += 1

    # Add-one correction prevents a reported p-value of exactly zero.
    return (extreme + 1) / (N_PERMUTATIONS + 1)


def bootstrap_median_difference_ci(a, b, rng):
    """Percentile 95% bootstrap CI for median(a) - median(b)."""
    differences = []
    for _ in range(N_BOOTSTRAPS):
        sample_a = [rng.choice(a) for _ in range(len(a))]
        sample_b = [rng.choice(b) for _ in range(len(b))]
        differences.append(median(sample_a) - median(sample_b))
    differences.sort()
    lower = differences[int(0.025 * len(differences))]
    upper = differences[min(int(0.975 * len(differences)), len(differences) - 1)]
    return lower, upper


def fmt(value):
    return "" if value is None or not math.isfinite(value) else f"{value:.6f}"


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find {INPUT_PATH}. Put this script in the project root "
            "and ensure reports/work_statistics.csv exists."
        )

    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    rng = random.Random(SEED)
    output = []

    for metric in METRICS:
        a, b = [], []
        for row in rows:
            author = (row.get("author") or "").strip()
            raw = (row.get(metric) or "").strip()
            if not raw:
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            if not math.isfinite(value):
                continue
            if author == AUTHOR_A:
                a.append(value)
            elif author == AUTHOR_B:
                b.append(value)

        if not a or not b:
            output.append({
                "metric": metric,
                "author_a": AUTHOR_A,
                "n_a": len(a),
                "mean_a": fmt(mean(a)),
                "median_a": fmt(median(a)),
                "author_b": AUTHOR_B,
                "n_b": len(b),
                "mean_b": fmt(mean(b)),
                "median_b": fmt(median(b)),
                "mean_difference_a_minus_b": "",
                "median_difference_a_minus_b": "",
                "median_difference_ci95_low": "",
                "median_difference_ci95_high": "",
                "cliffs_delta_a_vs_b": "",
                "permutation_p_two_sided_mean_difference": "",
            })
            continue

        ci_low, ci_high = bootstrap_median_difference_ci(a, b, rng)
        output.append({
            "metric": metric,
            "author_a": AUTHOR_A,
            "n_a": len(a),
            "mean_a": fmt(mean(a)),
            "median_a": fmt(median(a)),
            "author_b": AUTHOR_B,
            "n_b": len(b),
            "mean_b": fmt(mean(b)),
            "median_b": fmt(median(b)),
            "mean_difference_a_minus_b": fmt(mean(a) - mean(b)),
            "median_difference_a_minus_b": fmt(median(a) - median(b)),
            "median_difference_ci95_low": fmt(ci_low),
            "median_difference_ci95_high": fmt(ci_high),
            "cliffs_delta_a_vs_b": fmt(cliff_delta(a, b)),
            "permutation_p_two_sided_mean_difference": fmt(
                permutation_p_value_mean_difference(a, b, rng)
            ),
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fields = list(output[0].keys()) if output else []
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)

    print(f"Read {len(rows)} works from: {INPUT_PATH}")
    print(f"Wrote comparison results to: {OUTPUT_PATH}")
    print("Authors compared:", AUTHOR_A, "vs.", AUTHOR_B)
    print("Metrics:", ", ".join(METRICS))
    print(
        "Note: permutation p-values and bootstrap intervals are exploratory; "
        "works are not necessarily independent or representative samples."
    )


if __name__ == "__main__":
    main()
