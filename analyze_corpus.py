from collections import Counter, defaultdict
from pathlib import Path
import csv
import gzip

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "data" / "lemmas"
MANIFEST_PATH = ROOT / "corpus_manifest_v1_locked.csv"
REPORT_DIR = ROOT / "reports"

TOP_N = 30
MIN_COMBINED_LEMMA_COUNT = 10
PERSON_LABELS = {"PER", "PERSON"}
SETS = ("all_alpha", "content", "content_no_person")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def truth(value):
    return str(value).strip().casefold() == "true"


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_manifest():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")
    result = {}
    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"analysis_work_id", "title_fr", "author", "output_filename"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manifest missing columns: {sorted(missing)}")
        for row in reader:
            result[Path(row["output_filename"]).stem] = row
    return result


def analyze_file(path):
    counts = {name: Counter() for name in SETS}
    total_tokens = alpha_tokens = content_tokens = no_person_tokens = 0
    entity_tokens = person_tokens = 0

    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"lemma_lower", "is_alpha", "is_stop", "entity_type"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name} missing columns: {sorted(missing)}")

        for row in reader:
            total_tokens += 1
            lemma = (row.get("lemma_lower") or "").strip()
            entity_type = (row.get("entity_type") or "").strip().upper()

            if entity_type:
                entity_tokens += 1
            if entity_type in PERSON_LABELS:
                person_tokens += 1

            if not lemma or not truth(row.get("is_alpha", "")):
                continue

            alpha_tokens += 1
            counts["all_alpha"][lemma] += 1

            if not truth(row.get("is_stop", "")):
                content_tokens += 1
                counts["content"][lemma] += 1
                if entity_type not in PERSON_LABELS:
                    no_person_tokens += 1
                    counts["content_no_person"][lemma] += 1

    unique_alpha = len(counts["all_alpha"])
    unique_content = len(counts["content"])
    unique_no_person = len(counts["content_no_person"])
    stats = {
        "total_tokens": total_tokens,
        "alphabetic_tokens": alpha_tokens,
        "unique_alphabetic_lemmas": unique_alpha,
        "alphabetic_lemma_ttr": unique_alpha / alpha_tokens if alpha_tokens else 0,
        "content_tokens": content_tokens,
        "unique_content_lemmas": unique_content,
        "content_lemma_ttr": unique_content / content_tokens if content_tokens else 0,
        "content_tokens_excluding_person_entities": no_person_tokens,
        "unique_content_lemmas_excluding_person_entities": unique_no_person,
        "content_ttr_excluding_person_entities": (
            unique_no_person / no_person_tokens if no_person_tokens else 0
        ),
        "named_entity_tokens": entity_tokens,
        "person_entity_tokens": person_tokens,
    }
    return counts, stats


def main():
    manifest = load_manifest()
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Lemmatized directory not found: {INPUT_DIR}")
    files = sorted(INPUT_DIR.glob("*.tokens.tsv.gz"))
    if not files:
        raise FileNotFoundError(f"No *.tokens.tsv.gz files found in {INPUT_DIR}")

    author_counts = defaultdict(lambda: defaultdict(Counter))
    author_totals = defaultdict(lambda: defaultdict(int))
    work_stats = []

    stats_fields = [
        "analysis_work_id", "title_fr", "author", "lemmatized_file",
        "total_tokens", "alphabetic_tokens", "unique_alphabetic_lemmas",
        "alphabetic_lemma_ttr", "content_tokens", "unique_content_lemmas",
        "content_lemma_ttr", "content_tokens_excluding_person_entities",
        "unique_content_lemmas_excluding_person_entities",
        "content_ttr_excluding_person_entities", "named_entity_tokens",
        "person_entity_tokens",
    ]
    freq_fields = [
        "analysis_work_id", "title_fr", "author", "analysis_set", "lemma",
        "count", "selected_token_total", "relative_frequency_per_10000",
    ]
    work_freq_path = REPORT_DIR / "lemma_frequencies_by_work.csv"
    top_rows = []

    print(f"Found {len(files)} lemmatized files.")
    with work_freq_path.open("w", encoding="utf-8-sig", newline="") as freq_file:
        freq_writer = csv.DictWriter(freq_file, fieldnames=freq_fields)
        freq_writer.writeheader()

        for i, path in enumerate(files, start=1):
            stem = path.name.removesuffix(".tokens.tsv.gz")
            if stem not in manifest:
                raise ValueError(
                    f"{path.name} has no matching output_filename in the manifest. "
                    "Check that the corpus version matches."
                )

            meta = manifest[stem]
            author = meta["author"]
            work_id = meta["analysis_work_id"]
            title = meta["title_fr"]
            counts, stats = analyze_file(path)

            work_stats.append({
                "analysis_work_id": work_id,
                "title_fr": title,
                "author": author,
                "lemmatized_file": path.name,
                **stats,
            })

            for set_name in SETS:
                counter = counts[set_name]
                selected_total = sum(counter.values())
                author_counts[author][set_name].update(counter)
                author_totals[author][set_name] += selected_total

                for lemma, count in counter.items():
                    freq_writer.writerow({
                        "analysis_work_id": work_id,
                        "title_fr": title,
                        "author": author,
                        "analysis_set": set_name,
                        "lemma": lemma,
                        "count": count,
                        "selected_token_total": selected_total,
                        "relative_frequency_per_10000": (
                            count / selected_total * 10000 if selected_total else 0
                        ),
                    })

                for lemma, count in counter.most_common(TOP_N):
                    top_rows.append({
                        "analysis_work_id": work_id,
                        "title_fr": title,
                        "author": author,
                        "analysis_set": set_name,
                        "lemma": lemma,
                        "count": count,
                        "selected_token_total": selected_total,
                        "relative_frequency_per_10000": (
                            count / selected_total * 10000 if selected_total else 0
                        ),
                    })

            print(
                f"[{i}/{len(files)}] {title}: {stats['total_tokens']:,} tokens; "
                f"{stats['unique_content_lemmas']:,} content lemmas"
            )

    write_csv(REPORT_DIR / "work_statistics.csv", stats_fields, work_stats)
    write_csv(REPORT_DIR / "top_lemmas_by_work.csv", freq_fields, top_rows)

    author_freq = []
    author_fields = [
        "author", "analysis_set", "lemma", "count",
        "selected_token_total", "relative_frequency_per_10000",
    ]
    for author in sorted(author_counts):
        for set_name in SETS:
            counter = author_counts[author][set_name]
            total = author_totals[author][set_name]
            for lemma, count in counter.most_common():
                author_freq.append({
                    "author": author,
                    "analysis_set": set_name,
                    "lemma": lemma,
                    "count": count,
                    "selected_token_total": total,
                    "relative_frequency_per_10000": (
                        count / total * 10000 if total else 0
                    ),
                })
    write_csv(REPORT_DIR / "lemma_frequencies_by_author.csv", author_fields, author_freq)

    authors = sorted(author_counts)
    if len(authors) != 2:
        raise ValueError(f"Expected exactly two authors in manifest, found: {authors}")

    a, b = authors
    comparison = []
    for set_name in SETS:
        ca, cb = author_counts[a][set_name], author_counts[b][set_name]
        ta, tb = author_totals[a][set_name], author_totals[b][set_name]
        for lemma in set(ca) | set(cb):
            na, nb = ca.get(lemma, 0), cb.get(lemma, 0)
            if na + nb < MIN_COMBINED_LEMMA_COUNT:
                continue
            fa = na / ta * 10000 if ta else 0
            fb = nb / tb * 10000 if tb else 0
            comparison.append({
                "analysis_set": set_name,
                "lemma": lemma,
                "author_a": a,
                "count_author_a": na,
                "relative_frequency_author_a_per_10000": fa,
                "author_b": b,
                "count_author_b": nb,
                "relative_frequency_author_b_per_10000": fb,
                "difference_a_minus_b_per_10000": fa - fb,
                "combined_count": na + nb,
            })

    comparison.sort(
        key=lambda r: (r["analysis_set"], -abs(r["difference_a_minus_b_per_10000"]))
    )
    comparison_fields = [
        "analysis_set", "lemma", "author_a", "count_author_a",
        "relative_frequency_author_a_per_10000", "author_b", "count_author_b",
        "relative_frequency_author_b_per_10000",
        "difference_a_minus_b_per_10000", "combined_count",
    ]
    write_csv(REPORT_DIR / "author_lemma_comparison.csv", comparison_fields, comparison)

    print("\nAnalysis completed.")
    print(f"Works analyzed: {len(work_stats)}")
    print(f"Reports saved in: {REPORT_DIR}")
    print(" - work_statistics.csv")
    print(" - top_lemmas_by_work.csv")
    print(" - lemma_frequencies_by_work.csv")
    print(" - lemma_frequencies_by_author.csv")
    print(" - author_lemma_comparison.csv")
    print("TTR is sensitive to text length; pooled author frequencies are descriptive.")
    print("The no-person variant excludes only NER-recognized PER/PERSON tokens.")


if __name__ == "__main__":
    main()
