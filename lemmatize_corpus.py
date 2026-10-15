
from pathlib import Path
import csv
import gzip
import hashlib
import re

import spacy


# --------------------------------------------------
# Configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "data" / "works"
OUTPUT_DIR = ROOT / "data" / "lemmas"
REPORT_PATH = OUTPUT_DIR / "lemmatization_report.csv"

MODEL_NAME = "fr_core_news_lg"
BATCH_SIZE = 16

SCRIPT_VERSION = "1.1.0"

# Allow long paragraphs in historical novels.
MAX_LENGTH = 5_000_000

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not INPUT_DIR.exists():
    raise FileNotFoundError(
        f"Input directory not found: {INPUT_DIR}"
    )

input_files = sorted(INPUT_DIR.glob("*.txt"))

if not input_files:
    raise FileNotFoundError(
        f"No .txt files found in {INPUT_DIR}"
    )


# --------------------------------------------------
# Load spaCy model
# --------------------------------------------------

# Keep all pipeline components, including parser and NER.
nlp = spacy.load(MODEL_NAME)
nlp.max_length = MAX_LENGTH


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024), b""
        ):
            digest.update(block)

    return digest.hexdigest()


def read_paragraphs(path: Path):
    """Yield non-empty paragraphs in source order."""
    with path.open(
        "r", encoding="utf-8-sig"
    ) as file:
        text = file.read()

    for paragraph in re.split(r"\n\s*\n", text):
        if paragraph.strip():
            yield paragraph


# --------------------------------------------------
# Output schema
# --------------------------------------------------

fieldnames = [
    "paragraph_index",
    "token_index",
    "token",
    "lemma",
    "lemma_lower",
    "pos",
    "tag",
    "morph",
    "is_alpha",
    "is_stop",
    "is_punct",
    "is_digit",
    "sentence_index",
    "sentence_start",
    "dependency",
    "head",
    "head_token_index",
    "entity_text",
    "entity_type",
    "entity_iob",
]


# --------------------------------------------------
# Process corpus
# --------------------------------------------------

report_rows = []

print(f"Model: {MODEL_NAME}")
print(f"spaCy version: {spacy.__version__}")
print(f"Model version: {nlp.meta.get('version', 'unknown')}")
print(f"Pipeline: {nlp.pipe_names}")
print(f"Input files: {len(input_files)}")
print()

for file_number, input_path in enumerate(
    input_files, start=1
):
    output_path = (
        OUTPUT_DIR / f"{input_path.stem}.tokens.tsv.gz"
    )

    paragraph_count = 0
    token_count = 0
    alpha_count = 0
    stop_count = 0
    punct_count = 0
    digit_count = 0
    sentence_count = 0
    entity_token_count = 0
    entity_mentions = 0
    person_entity_mentions = 0

    unique_entity_surface_forms = set()
    unique_person_surface_forms = set()

    print(
        f"[{file_number}/{len(input_files)}] "
        f"{input_path.name}"
    )

    with gzip.open(
        output_path,
        "wt",
        encoding="utf-8",
        newline="",
        compresslevel=6,
    ) as output_file:

        writer = csv.DictWriter(
            output_file,
            fieldnames=fieldnames,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()

        paragraphs = read_paragraphs(input_path)

        for paragraph_index, doc in enumerate(
            nlp.pipe(
                paragraphs,
                batch_size=BATCH_SIZE,
            ),
            start=1,
        ):
            paragraph_count += 1

            # Map each token to its sentence index.
            # Sentence indices are local to each paragraph.
            sentence_by_token = {}
            sentence_start_by_token = {}

            for local_sentence_index, sent in enumerate(
                doc.sents, start=1
            ):
                sentence_count += 1

                for token in sent:
                    sentence_by_token[token.i] = (
                        local_sentence_index
                    )
                    sentence_start_by_token[token.i] = (
                        token.i == sent.start
                    )

            # Map tokens to their complete detected entity.
            entity_by_token = {}

            for entity in doc.ents:
                entity_mentions += 1

                normalized_text = " ".join(
                    entity.text.casefold().split()
                )

                unique_entity_surface_forms.add(normalized_text)

                if entity.label_ in {"PER", "PERSON"}:
                    person_entity_mentions += 1
                    unique_person_surface_forms.add(normalized_text)

                for token in entity:
                    entity_by_token[token.i] = {
                        "text": entity.text,
                        "label": entity.label_,
                    }

            for token in doc:
                lemma = token.lemma_

                entity = entity_by_token.get(token.i)

                # Token indices are 1-based within a paragraph.
                # The head index is also paragraph-local.
                writer.writerow({
                    "paragraph_index": paragraph_index,
                    "token_index": token.i + 1,
                    "token": token.text,
                    "lemma": lemma,
                    "lemma_lower": lemma.lower(),
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "morph": str(token.morph),
                    "is_alpha": token.is_alpha,
                    "is_stop": token.is_stop,
                    "is_punct": token.is_punct,
                    "is_digit": token.is_digit,
                    "sentence_index": sentence_by_token.get(
                        token.i
                    ),
                    "sentence_start": sentence_start_by_token.get(
                        token.i, False
                    ),
                    "dependency": token.dep_,
                    "head": token.head.text,
                    "head_token_index": token.head.i + 1,
                    "entity_text": (
                        entity["text"] if entity else ""
                    ),
                    "entity_type": (
                        entity["label"] if entity else ""
                    ),
                    "entity_iob": token.ent_iob_,
                })

                token_count += 1
                alpha_count += token.is_alpha
                stop_count += token.is_stop
                punct_count += token.is_punct
                digit_count += token.is_digit
                entity_token_count += token.ent_iob_ != "O"

    report_rows.append({
        "source_file": input_path.name,
        "output_file": output_path.name,
        "source_sha256": sha256_file(input_path),
        "output_sha256": sha256_file(output_path),
        "source_bytes": input_path.stat().st_size,
        "paragraphs_processed": paragraph_count,
        "sentences_detected": sentence_count,
        "tokens": token_count,
        "alphabetic_tokens": alpha_count,
        "stop_tokens": stop_count,
        "punctuation_tokens": punct_count,
        "numeric_tokens": digit_count,
        "entity_tokens": entity_token_count,
        "model": MODEL_NAME,
        "spacy_version": spacy.__version__,
        "model_version": nlp.meta.get("version", "unknown"),
        "entity_mentions": entity_mentions,
        "person_entity_mentions": person_entity_mentions,
        "unique_entity_surface_forms": len(
            unique_entity_surface_forms
        ),
        "unique_person_surface_forms": len(
            unique_person_surface_forms
        ),
        "script_version": SCRIPT_VERSION,
        "batch_size": BATCH_SIZE,
        "max_length": MAX_LENGTH,
        "pipeline_components": "|".join(nlp.pipe_names),
    })

    print(f"  Paragraphs: {paragraph_count:,}")
    print(f"  Sentences: {sentence_count:,}")
    print(f"  Tokens: {token_count:,}")
    print(f"  Entity tokens: {entity_token_count:,}")
    print(f"  Output: {output_path.name}")


# --------------------------------------------------
# Write report
# --------------------------------------------------

with REPORT_PATH.open(
    "w",
    encoding="utf-8",
    newline="",
) as report_file:
    writer = csv.DictWriter(
        report_file,
        fieldnames=report_rows[0].keys(),
    )
    writer.writeheader()
    writer.writerows(report_rows)


print()
print("Lemmatization and annotation completed.")
print(f"Processed files: {len(report_rows)}")
print(f"Report: {REPORT_PATH}")
print(f"Output directory: {OUTPUT_DIR}")
