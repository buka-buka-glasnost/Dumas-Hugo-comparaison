#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create visualizations and document-level TF-IDF from existing corpus reports.

Inputs expected in ./reports:
    work_statistics.csv
    lemma_frequencies_by_work.csv
    lemma_frequencies_by_author.csv   (optional)
    author_lemma_comparison.csv       (optional)

No corpus manifest is required. Existing reports are read-only; outputs are
written to ./reports/figures and ./reports/tfidf_by_work.csv.
"""

from pathlib import Path
import csv
import math
import sys

try:
    import pandas as pd
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise SystemExit(
        "Missing dependency. Install with: py -m pip install pandas matplotlib"
    ) from exc

ROOT = Path(__file__).resolve().parent
REPORT_DIR = ROOT / "reports"
FIGURE_DIR = REPORT_DIR / "figures"

STATS_FILE = REPORT_DIR / "work_statistics.csv"
WORK_FREQ_FILE = REPORT_DIR / "lemma_frequencies_by_work.csv"
AUTHOR_FREQ_FILE = REPORT_DIR / "lemma_frequencies_by_author.csv"
AUTHOR_COMPARISON_FILE = REPORT_DIR / "author_lemma_comparison.csv"

PREFERRED_SET = "content_no_person"
TFIDF_MIN_DOCUMENT_FREQUENCY = 2
TFIDF_TOP_N_PER_WORK = 30


def read_csv(path, required=True):
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required report not found: {path}")
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


def require_columns(df, columns, filename):
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f"{filename} is missing columns: {sorted(missing)}")


def save_figure(filename):
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / filename, dpi=180, bbox_inches="tight")
    plt.close()


def plot_work_length(stats):
    df = stats.sort_values("total_tokens", ascending=True).copy()
    labels = df["title_fr"].fillna(df["analysis_work_id"]).astype(str)
    authors = df["author"].fillna("Unknown").astype(str)
    author_names = list(authors.unique())
    # Matplotlib default color cycle; one series per author.
    fig, ax = plt.subplots(figsize=(12, max(7, len(df) * 0.28)))
    for author in author_names:
        mask = authors == author
        ax.barh(labels[mask], df.loc[mask, "total_tokens"], label=author)
    ax.set_title("Corpus work length")
    ax.set_xlabel("spaCy tokens")
    ax.set_ylabel("Work")
    ax.legend(title="Author")
    save_figure("01_work_length.png")


def plot_mattr(stats):
    metric = "mattr_content_500"
    if metric not in stats.columns:
        print(f"Skipping MATTR plot: column {metric!r} not found.")
        return
    df = stats.dropna(subset=[metric]).sort_values(metric)
    if df.empty:
        print("Skipping MATTR plot: no valid MATTR values.")
        return
    labels = df["title_fr"].fillna(df["analysis_work_id"]).astype(str)
    authors = df["author"].fillna("Unknown").astype(str)
    fig, ax = plt.subplots(figsize=(12, max(7, len(df) * 0.28)))
    for author in authors.unique():
        mask = authors == author
        ax.scatter(df.loc[mask, metric], labels[mask], label=author)
    ax.set_title("Moving-average type-token ratio (content words, window=500)")
    ax.set_xlabel("MATTR")
    ax.set_ylabel("Work")
    ax.legend(title="Author")
    save_figure("02_mattr_content_500.png")

    metric_1000 = "mattr_content_1000"
    if metric_1000 in stats.columns:
        df2 = stats.dropna(subset=[metric_1000]).sort_values(metric_1000)
        if not df2.empty:
            labels2 = df2["title_fr"].fillna(df2["analysis_work_id"]).astype(str)
            authors2 = df2["author"].fillna("Unknown").astype(str)
            fig, ax = plt.subplots(figsize=(12, max(7, len(df2) * 0.28)))
            for author in authors2.unique():
                mask = authors2 == author
                ax.scatter(df2.loc[mask, metric_1000], labels2[mask], label=author)
            ax.set_title("Moving-average type-token ratio (content words, window=1000)")
            ax.set_xlabel("MATTR")
            ax.set_ylabel("Work")
            ax.legend(title="Author")
            save_figure("03_mattr_content_1000.png")


def plot_author_lemma_differences(comparison):
    if comparison is None:
        print("Skipping author lemma comparison plot: optional report not found.")
        return
    required = {
        "analysis_set", "lemma", "difference_a_minus_b_per_10000",
        "author_a", "author_b", "combined_count"
    }
    require_columns(comparison, required, AUTHOR_COMPARISON_FILE.name)
    subset = comparison[comparison["analysis_set"] == PREFERRED_SET].copy()
    if subset.empty:
        print(f"Skipping lemma differences plot: no rows for {PREFERRED_SET}.")
        return
    subset["difference_a_minus_b_per_10000"] = pd.to_numeric(
        subset["difference_a_minus_b_per_10000"], errors="coerce"
    )
    subset = subset.dropna(subset=["difference_a_minus_b_per_10000"])
    subset = subset.reindex(
        subset["difference_a_minus_b_per_10000"].abs().sort_values(ascending=False).index
    ).head(30).sort_values("difference_a_minus_b_per_10000")
    if subset.empty:
        return

    author_a = str(subset["author_a"].iloc[0])
    author_b = str(subset["author_b"].iloc[0])
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.barh(subset["lemma"].astype(str), subset["difference_a_minus_b_per_10000"])
    ax.axvline(0, linewidth=0.8)
    ax.set_title(
        f"Largest relative-frequency differences: {PREFERRED_SET}\n"
        f"Positive = {author_a} more frequent; negative = {author_b} more frequent"
    )
    ax.set_xlabel("Difference in occurrences per 10,000 tokens")
    ax.set_ylabel("Lemma")
    save_figure("04_author_lemma_differences.png")


def build_tfidf(work_freq):
    required = {
        "analysis_work_id", "title_fr", "author", "analysis_set", "lemma", "count"
    }
    require_columns(work_freq, required, WORK_FREQ_FILE.name)
    df = work_freq[work_freq["analysis_set"] == PREFERRED_SET].copy()
    if df.empty:
        raise ValueError(
            f"No rows for analysis_set={PREFERRED_SET!r} in {WORK_FREQ_FILE.name}. "
            "Check the report's analysis_set values."
        )

    df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0)
    df = df[df["count"] > 0]
    # Aggregate duplicate work/lemma rows defensively.
    group_cols = ["analysis_work_id", "title_fr", "author", "lemma"]
    df = df.groupby(group_cols, dropna=False, as_index=False)["count"].sum()

    doc_ids = df["analysis_work_id"].astype(str).unique().tolist()
    n_docs = len(doc_ids)
    if n_docs == 0:
        raise ValueError("No documents available for TF-IDF.")

    document_frequency = df.groupby("lemma")["analysis_work_id"].nunique()
    df["df"] = df["lemma"].map(document_frequency)
    df = df[df["df"] >= TFIDF_MIN_DOCUMENT_FREQUENCY].copy()
    # Smoothed IDF; log base e. TF is within-document relative frequency.
    totals = df.groupby("analysis_work_id")["count"].transform("sum")
    df["tf"] = df["count"] / totals
    df["idf"] = (1 + n_docs) / (1 + df["df"])
    df["idf"] = df["idf"].map(math.log) + 1
    df["tfidf"] = df["tf"] * df["idf"]

    output_columns = [
        "analysis_work_id", "title_fr", "author", "lemma",
        "count", "df", "tf", "idf", "tfidf"
    ]
    result = df[output_columns].sort_values(
        ["analysis_work_id", "tfidf"], ascending=[True, False]
    )
    result.to_csv(REPORT_DIR / "tfidf_by_work.csv", index=False, encoding="utf-8-sig")

    top = result.groupby("analysis_work_id", sort=False).head(TFIDF_TOP_N_PER_WORK)
    top.to_csv(
        REPORT_DIR / "tfidf_top_lemmas_by_work.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Plot top TF-IDF terms across the corpus (mean score across documents).
    mean_scores = (
        result.groupby("lemma", as_index=False)["tfidf"]
        .mean()
        .sort_values("tfidf", ascending=False)
        .head(25)
        .sort_values("tfidf")
    )
    if not mean_scores.empty:
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.barh(mean_scores["lemma"].astype(str), mean_scores["tfidf"])
        ax.set_title(f"Highest mean TF-IDF lemmas across works ({PREFERRED_SET})")
        ax.set_xlabel("Mean TF-IDF")
        ax.set_ylabel("Lemma")
        save_figure("05_mean_tfidf_lemmas.png")

    print(f"TF-IDF documents: {n_docs}")
    print(f"TF-IDF vocabulary after min_df={TFIDF_MIN_DOCUMENT_FREQUENCY}: "
          f"{result['lemma'].nunique():,} lemmas")
    print("Wrote reports/tfidf_by_work.csv")
    print("Wrote reports/tfidf_top_lemmas_by_work.csv")


def main():
    if not REPORT_DIR.exists():
        raise FileNotFoundError(f"Reports directory not found: {REPORT_DIR}")
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    stats = read_csv(STATS_FILE)
    require_columns(
        stats,
        {"analysis_work_id", "title_fr", "author", "total_tokens"},
        STATS_FILE.name,
    )
    stats["total_tokens"] = pd.to_numeric(stats["total_tokens"], errors="coerce")
    plot_work_length(stats)
    plot_mattr(stats)

    comparison = read_csv(AUTHOR_COMPARISON_FILE, required=False)
    plot_author_lemma_differences(comparison)

    work_freq = read_csv(WORK_FREQ_FILE)
    build_tfidf(work_freq)

    print("\nVisualization completed.")
    print(f"Figures saved in: {FIGURE_DIR}")
    print("Existing reports were not modified.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
