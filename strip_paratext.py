#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Remove editorial paratext from the cleaned Gutenberg volumes.

Run from the project root, after clean_corpus.py and before join_volumes.py:
    python strip_paratext.py

clean_corpus.py removes only the Project Gutenberg START/END wrapper. The
files in data/cleaned/ still contain material that is not part of the novels:
title pages, publisher information, tables of contents, transcriber and
editor notes, prefaces, dedications, footnotes, illustration captions,
bibliographies and appended documents. This script removes that material.

How it works
------------
* A text is treated as a list of paragraphs separated by blank lines.
* RULES (below) describes each volume by its Gutenberg ID. Anchors are the
  texts of specific paragraphs, so the rules do not depend on line numbers:
    - "front": the opening segments to remove. Each item is
      (category, anchor). Paragraphs from the current position up to, but
      not including, the anchor get that category. The last anchor is the
      first paragraph of the literary text.
    - "back": (anchor, category) items. From the anchor (inclusive) to the
      next back anchor, or to the end of the file, gets that category.
    - "ranges": (from_anchor, to_anchor_inclusive, category) blocks in the
      middle of the text.
    - "inline": (regex, replacement, category) edits specific to one volume.
* GLOBAL rules apply to every volume: footnote markers and bodies,
  illustration captions, leftover Gutenberg lines, chapter/part numbering.
* An anchor that is missing or not where expected stops the script for that
  file; it never guesses.

Every removal has a category. To keep a category (for example author
prefaces), remove it from REMOVE below and rerun clean_corpus.py and this
script.

Re-running is safe. strip_paratext_hashes.json records, for each file, the
SHA-256 of the input these rules were written for and of the expected
output. A file whose hash equals the expected output is skipped as already
processed. A file that matches neither is processed anyway, with a warning:
check data/paratext_report.csv for that file.

Outputs
-------
    data/cleaned/*.txt             rewritten in place
    data/paratext_report.csv       what was removed, per file and category
    data/paratext_summary.csv      words before/after per file
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLEANED_DIR = ROOT / "data" / "cleaned"
REPORT_PATH = ROOT / "data" / "paratext_report.csv"
SUMMARY_PATH = ROOT / "data" / "paratext_summary.csv"
HASHES_PATH = ROOT / "strip_paratext_hashes.json"

# Categories that are removed. Delete a name from this set to keep it.
REMOVE = {
    "front_matter",       # title pages, publisher, edition and transcriber notes, TOC
    "back_matter",        # closing TOC, colophon, publisher lists, "FIN"
    "author_preface",     # prefaces/forewords written by Dumas or Hugo
    "author_afterword",   # afterwords written by the author outside the story
    "author_essay",       # non-fiction essay attached to a novel (L'Archipel de la Manche)
    "dedication",
    "editor_note",        # summaries, commentaries and notes by editors
    "notes",              # collected endnotes at the end of a volume
    "appendix",           # appended documents and letters by other people
    "bibliography",
    "footnote",           # footnote bodies and markers inside the text
    "illustration",       # [Illustration: ...] captions and lists of plates
    "structural_label",   # "CHAPITRE XII", "LIVRE PREMIER", "TOME II", "FIN"
    "boilerplate",        # leftover Project Gutenberg / producer lines
    "page_marker",        # page numbers, separators and similar typesetting residue
    "transcription_artifact",  # placeholders and flags left by the transcribers
}

# ----------------------------------------------------------------------
# Anchors
# ----------------------------------------------------------------------

class Anchor:
    """A paragraph identified by its text. n = which occurrence (1-based),
    counted from the search start."""

    def __init__(self, text: str, prefix: bool, n: int = 1):
        self.text = " ".join(text.split())
        self.prefix = prefix
        self.n = n

    def matches(self, paragraph: str) -> bool:
        if self.prefix:
            return paragraph.startswith(self.text)
        return paragraph == self.text

    def find(self, norm: list[str], start: int) -> int:
        seen = 0
        for i in range(start, len(norm)):
            if self.matches(norm[i]):
                seen += 1
                if seen == self.n:
                    return i
        raise LookupError(f"anchor not found: {self!r} (searching from paragraph {start})")

    def __repr__(self) -> str:
        kind = "P" if self.prefix else "E"
        nth = f", n={self.n}" if self.n != 1 else ""
        return f'{kind}("{self.text[:60]}"{nth})'


def E(text: str, n: int = 1) -> Anchor:
    """Exact paragraph text."""
    return Anchor(text, prefix=False, n=n)


def P(text: str, n: int = 1) -> Anchor:
    """Paragraph that starts with text."""
    return Anchor(text, prefix=True, n=n)


# ----------------------------------------------------------------------
# Per-volume rules, keyed by Project Gutenberg ebook ID
# ----------------------------------------------------------------------

# Chapter number followed directly by the title, without a separator.
MARGOT_HEADING = (r"^(?:[IVX]{1,6}|[IVXLC]{2,7})\s+(?=[A-ZÀ-ÖØ-Þ].{0,100}$)", "", "structural_label")

RULES: dict[str, dict] = {
    # --- Alexandre Dumas -------------------------------------------------
    "13819": {  # Les Compagnons de Jéhu
        "front": [("front_matter", E("PROLOGUE LA VILLE D'AVIGNON"))],
        # "Un mot au lecteur": Dumas's non-fiction account of his research.
        "back": [(E("UN MOT AU LECTEUR"), "author_afterword")],
    },
    "13856": {  # La Reine Margot I
        "front": [("front_matter", E("PREMIÈRE PARTIE"))],
        "inline": [MARGOT_HEADING],  # "I Le latin de M. de Guise"
        # After the last chapter: translations of the Latin dialogue (notes).
        "back": [(P("FIN DE LA PREMIÈRE PARTIE. -- Qui est à ma portière?"), "notes")],
    },
    "13857": {  # La Reine Margot II
        "front": [("front_matter", E("DEUXIÈME PARTIE"))],
        "inline": [MARGOT_HEADING],
        "back": [(E("FIN"), "back_matter"), (P("[1] Charles IX avait épousé"), "notes")],
    },
    "13947": {  # Le Vicomte de Bragelonne I
        "front": [("front_matter", E("Chapitre I — La lettre"))],
        "back": [(E("Fin du tome I"), "back_matter")],
    },
    "13948": {  # Le Vicomte de Bragelonne II
        "front": [("front_matter", E("Chapitre LXXII — La grandeur de l'évêque de Vannes"))],
        "back": [(E("Fin du tome II"), "back_matter")],
    },
    "13949": {  # Le Vicomte de Bragelonne III
        "front": [("front_matter", E("Chapitre CXXXII — Psychologie royale"))],
        "back": [(E("Fin du tome III"), "back_matter")],
    },
    "13950": {  # Le Vicomte de Bragelonne IV
        "front": [("front_matter", E("Chapitre CXCVII — Roi et noblesse"))],
        "back": [(E("FIN"), "back_matter")],
    },
    "13951": {  # Les Trois Mousquetaires
        "front": [
            ("front_matter", E("PRÉFACE")),
            ("author_preface", E("CHAPITRE PREMIER LES TROIS PRÉSENTS DE M. D'ARTAGNAN PÈRE")),
        ],
        "back": [(E("FIN"), "back_matter")],
    },
    "13952": {  # Vingt ans après
        "front": [("front_matter", E("I. Le fantôme de Richelieu"))],
        "back": [(E("FIN"), "back_matter")],
    },
    "15208": {  # Les Mille et Un Fantômes
        "front": [
            ("front_matter", E("A M. ***")),
            ("dedication", E("LA RUE DE DIANE A FONTENAY-AUX-ROSES")),
        ],
        "back": [(E("FIN."), "back_matter")],
    },
    "15574": {  # Le Capitaine Paul
        "front": [
            ("front_matter", P("Préface Habent sua fata libelli.")),
            ("author_preface", P("Chapitre I Vers la fin d'une belle soirée")),
        ],
    },
    "17693": {  # La San-Felice I
        "front": [
            ("front_matter", E("AVANT-PROPOS")),
            ("author_preface", E("LA SAN-FELICE")),
            ("front_matter", E("I")),
        ],
        "back": [(E("FIN DU TOME PREMIER"), "back_matter")],
    },
    "18401": {  # La San-Felice II
        "front": [("front_matter", E("XIX"))],
        "back": [(E("FIN DU TOME DEUXIÈME"), "back_matter")],
    },
    "18402": {  # La San-Felice III
        "front": [("front_matter", E("XXXVII"))],
        "back": [(E("FIN DU TOME TROISIÈME"), "back_matter")],
        "inline": [(r"\s*\[grec\]\s*", " ", "transcription_artifact")],  # omitted Greek text
    },
    "18586": {  # La San-Felice IV
        "front": [("front_matter", E("LVI"))],
        "back": [(E("FIN DU TOME QUATRIÈME."), "back_matter")],
    },
    "18773": {  # La San-Felice V
        "front": [("front_matter", E("LXXVI"))],
        "back": [(E("FIN DU TOME CINQUIÈME."), "back_matter")],
    },
    "18826": {  # La San-Felice VI
        "front": [("front_matter", E("C"))],
        "back": [(E("FIN DU TOME SIXIÈME"), "back_matter")],
    },
    "17989": {  # Le Comte de Monte-Cristo I
        "front": [("front_matter", E("I"))],
        "back": [(E("FIN DU TOME PREMIER"), "back_matter")],
    },
    "17990": {  # Le Comte de Monte-Cristo II
        "front": [("front_matter", E("XXXII"))],
        "back": [(E("FIN DU TOME DEUXIÈME."), "back_matter")],
    },
    "17991": {  # Le Comte de Monte-Cristo III
        "front": [("front_matter", E("LVI"))],
        "back": [(E("FIN DU TOME TROISIÈME."), "back_matter")],
        "inline": [(r"^\[Grec\]\s*", "", "transcription_artifact")],  # omitted Greek text
    },
    "17992": {  # Le Comte de Monte-Cristo IV
        "front": [("front_matter", E("LXXXV"))],
        "back": [
            (E("FIN"), "back_matter"),
            (P("Bibliographie--OEuvres complètes"), "bibliography"),
        ],
    },
    "18003": {  # La Femme au collier de velours
        "front": [("front_matter", E("CHAPITRE I."))],
    },
    "18006": {  # Le Chevalier de Maison-Rouge
        "front": [("front_matter", E("I"))],
        "back": [
            (E("FIN"), "back_matter"),
            (P("Bibliographie--OEuvres complètes"), "bibliography"),
        ],
    },
    "18028": {  # Le Chevalier d'Harmental
        "front": [("front_matter", E("Chapitre 1"))],
        "back": [(P("Bibliographie--OEuvres complètes"), "bibliography")],
    },
    "18199": {  # Le Collier de la Reine I
        "front": [
            ("front_matter", E("Avant-propos")),
            ("author_preface", E("Prologue--I")),
        ],
        "back": [(E("FIN DU TOME I."), "back_matter")],
    },
    "18200": {  # Le Collier de la Reine II
        "front": [("front_matter", E("Chapitre XLVIII"))],
        "back": [(E("FIN."), "back_matter")],
    },
    "18271": {  # Georges
        "front": [("front_matter", E("Chapitre I—L'île de France"))],
        "back": [(P("Bibliographie—Œuvres complètes"), "bibliography")],
    },
    "18321": {  # Acté
        "front": [
            ("front_matter", E("Préface")),
            ("editor_note", E("Chapitre I")),  # "Résumé" by the e-book editors
        ],
    },
    "18697": {  # Le Capitaine Pamphile
        "front": [
            ("front_matter", E("PRÉFACE")),
            ("editor_note", E("Chapitre I")),  # "Résumé" and "Commentaires" by the e-book editors
        ],
        # Reproduced constitution and a letter by Alphonse Karr.
        "back": [(E("Pièces justificatives"), "appendix")],
    },
    "26476": {  # Création et rédemption II: La Fille du marquis
        "front": [("front_matter", E("LES VOLONTAIRES DE 93"))],
        "ranges": [(E("FIN DU TOME PREMIER"), E("TOME II"), "structural_label")],
        "back": [(E("FIN"), "back_matter")],
    },
    "26504": {  # La Tulipe noire
        "front": [("front_matter", E("I"))],
    },
    "36812": {  # Création et rédemption I: Le Docteur mystérieux
        "front": [("front_matter", E("I"))],
        "back": [(P("LA SUITE DE CE RÉCIT S'INTITULE"), "back_matter")],
    },
    "37771": {  # Le Comte de Moret
        "front": [("front_matter", E("CHAPITRE Ier."))],
        "back": [(E("FIN."), "back_matter")],
        "inline": [(r"\s*\[\+\]\s*", " ", "transcription_artifact")],  # cross before Richelieu's signature
    },
    "46747": {  # Gabriel Lambert (with three shorter tales)
        "front": [("front_matter", E("GABRIEL LAMBERT", n=2))],
    },
    "5104": {  # Histoire d'un casse-noisette (with two shorter tales)
        "front": [
            ("front_matter", E("PRÉFACE")),
            ("author_preface", E("HISTOIRE D'UN CASSE-NOISETTE")),
        ],
        "back": [(E("FIN"), "back_matter")],
    },
    "71510": {  # Pauline; Murat; Pascal Bruno
        "front": [("front_matter", E("PAULINE."))],
        "back": [(E("FIN."), "back_matter")],
    },
    "7770": {  # Les Quarante-Cinq I
        "front": [("front_matter", E("I"))],
        "back": [(E("FIN DE LA PREMIÈRE PARTIE"), "back_matter")],
    },
    "7771": {  # Les Quarante-Cinq II
        "front": [("front_matter", E("XXXII"))],
        "back": [(E("FIN DE LA DEUXIÈME PARTIE"), "back_matter")],
    },
    "7772": {  # Les Quarante-Cinq III
        "front": [("front_matter", E("XLIV"))],
        "back": [(E("FIN DE LA TROISIÈME PARTIE"), "back_matter")],
    },
    "9637": {  # La Dame de Monsoreau I
        "front": [("front_matter", E("CHAPITRE PREMIER"))],
        "back": [(E("FIN DE LA PREMIÈRE PARTIE."), "back_matter")],
    },
    "9638": {  # La Dame de Monsoreau II
        "front": [("front_matter", E("CHAPITRE PREMIER"))],
        "back": [(E("FIN DE LA DEUXIÈME PARTIE."), "back_matter")],
    },
    "9639": {  # La Dame de Monsoreau III
        "front": [("front_matter", E("CHAPITRE PREMIER"))],
        "inline": [
            (r"\\PG\{\d+\}", "", "page_marker"),
            (r"\b(aise|faite)\*", r"\1", "transcription_artifact"),
            (r"\bmoi\*\*\*(?=\.)", "moi", "transcription_artifact"),
        ],
    },

    # --- Victor Hugo -----------------------------------------------------
    "17489": {  # Les Misérables I
        "front": [("front_matter", E("Livre premier--Un juste", n=2))],
    },
    "17493": {  # Les Misérables II
        "front": [("front_matter", E("Livre premier--Waterloo", n=2))],
    },
    "17494": {  # Les Misérables III
        "front": [("front_matter", E("Livre premier--Paris étudié dans son atome", n=2))],
    },
    "17518": {  # Les Misérables IV
        "front": [("front_matter", E("Livre premier--Quelques pages d'histoire", n=2))],
    },
    "17519": {  # Les Misérables V
        "front": [("front_matter", E("Livre premier--La guerre entre quatre murs", n=2))],
    },
    "19657": {  # Notre-Dame de Paris
        "front": [
            ("front_matter", E("PRÉFACE")),
            ("author_preface", E("LIVRE PREMIER")),  # 1831 preface and 1832 note
        ],
        "back": [(E("NOTES"), "notes")],
    },
    "5423": {  # L'Homme qui rit
        "front": [
            ("front_matter", P("De l'Angleterre tout est grand")),
            ("author_preface", E("PREMIÈRE PARTIE--LA MER ET LA NUIT")),
            ("front_matter", E("PREMIÈRE PARTIE")),
        ],
        "back": [(P("Au bas de la dernière page du manuscrit"), "editor_note")],
    },
    "6838": {  # Le Dernier Jour d'un condamné
        "front": [
            ("front_matter", E("Préface de 1832")),
            # Prefaces of 1832 and 1829, including "Une comédie à propos d'une tragédie".
            ("author_preface", E("LE DERNIER JOUR D'UN CONDAMNÉ")),
            ("front_matter", E("I")),
        ],
        "back": [(E("NOTES"), "notes")],
    },
    "6994": {  # Han d'Islande
        "front": [
            ("front_matter", P("Han d'Islande est un livre de jeune homme")),
            ("author_preface", E("Han D'Islande")),  # prefaces of 1833, 1823 and the 2nd edition
            ("front_matter", E("I")),
        ],
        "inline": [(r"\s*\[Nom de la morgue de Drontheim\]", "", "footnote")],
    },
    "79493": {  # Les Travailleurs de la mer I
        "front": [
            ("front_matter", P("Je dédie ce livre au rocher")),
            ("dedication", P("La religion, la société, la nature")),
            ("author_preface", E("L'ARCHIPEL DE LA MANCHE")),
            # Non-fiction essay on the Channel Islands, added before the novel.
            ("author_essay", E("PREMIÈRE PARTIE")),
        ],
        # Footnote 8: the Spanish original of the smugglers' dialogue.
        "ranges": [(P("[8]--Asi, entendido està?"), E("--Sois gentleman y soy caballero.]"), "footnote")],
        "back": [(E("TABLE DU PREMIER TOME"), "back_matter")],
    },
    "79659": {  # Les Travailleurs de la mer II
        "front": [("front_matter", E("DEUXIÈME PARTIE"))],
        "back": [(E("NOTES"), "notes")],
    },
    "9645": {  # Quatrevingt-Treize
        "front": [("front_matter", E("PREMIÈRE PARTIE"))],
    },
}


# ----------------------------------------------------------------------
# Global rules
# ----------------------------------------------------------------------

# Whole paragraphs. Each entry: (category, regex on the normalized paragraph).
GLOBAL_DROP = [
    ("boilerplate", re.compile(r"^End of (the )?Project Gutenberg", re.I)),
    ("boilerplate", re.compile(r"^(Produced by|This Etext was prepared|This file was produced)", re.I)),
    ("page_marker", re.compile(r"^[-—]\s*\d+\s*[-—]$")),
    ("page_marker", re.compile(r"^(\*\s*){3,}$")),                    # * * * * *
    ("footnote", re.compile(r"^Note de l'[ÉE]diteur\.$")),
    ("footnote", re.compile(r"^\* (?!\*)\S")),                          # "* Raconte." (Monte-Cristo)
]

# Paragraphs that open a bracket: dropped together with any following
# paragraphs needed to close it.
BRACKET_DROP = [
    ("illustration", re.compile(r"^\[Illustration\b")),
    ("footnote", re.compile(r"^\[(Note|note|Notes|Footnote)\b[^\]]*?:")),  # [Note 1: ...], [note *: ...]
    ("footnote", re.compile(r"^\[\d+(:|\]|\]:)")),                          # [12: ...], [3] ..., [2]: ...
    ("footnote", re.compile(r"^\[(\*|[A-Z])\]\s")),                         # [*] ..., [A] ...
]

# Inline edits. Each entry: (category, regex, replacement).
GLOBAL_INLINE = [
    ("footnote", re.compile(r"\s?\[(Notes?|note|Footnote)\s?:[^\]]*\]"), ""),  # [Note : Le bourreau.]
    ("footnote", re.compile(r"\[(\d{1,3}|[A-Z]|\*)\]"), ""),                   # markers [12], [B], [*]
]

# Structural labels: chapter, book, part and volume numbering.
ORD = (r"PREMIER|PREMIÈRE|DEUXIÈME|DEUXIEME|TROISIÈME|QUATRIÈME|CINQUIÈME|SIXIÈME|SIXIÈIME|"
       r"SEPTIÈME|SEPTIEME|HUITIÈME|HUITIEME|NEUVIÈME|NEUVIEME|DIXIÈME|ONZIÈME|DOUZIÈME|"
       r"TREIZIÈME|QUATORZIÈME|QUINZIÈME")
ROMAN = r"[IVXLC]+"
LABEL_DROP = re.compile(
    r"^(?:"
    rf"(?:CHAPITRE|Chapitre|CHAP\.|Chap\.)\s+(?:{ROMAN}|\d+|PREMIER|Premier|premier|Ier|1er|UNIQUE)\.?"
    rf"|{ROMAN}\.?"
    rf"|(?:LIVRE|Livre)\s+(?:{ORD}|premier|deuxième|troisième|quatrième|cinquième|sixième|septième|huitième|neuvième|dixième|onzième|douzième|treizième|quatorzième|quinzième|{ROMAN})\.?"
    rf"|(?:PREMIÈRE|DEUXIÈME|DEUXIEME|TROISIÈME|QUATRIÈME|CINQUIÈME|SIXIÈME)\s+PARTIE\.?"
    rf"|(?:PREMIER|DEUXIÈME|TROISIÈME|QUATRIÈME)\s+VOLUME\.?"
    rf"|(?:TOME|Tome)\s+(?:{ROMAN}|PREMIER)\.?"
    r"|FIN\.?|Fin\.?"
    r"|(?:FIN|Fin)\s+(?:DU|du)\s+(?:TOME|tome|PREMIER|DEUXIÈME|TROISIÈME|QUATRIÈME|PROLOGUE)\b.*"
    r"|FIN DE LA (?:PREMIÈRE|DEUXIÈME|TROISIÈME) PARTIE\.?"
    rf"|Prologue--{ROMAN}"
    r")$"
)

# Label + title (or label + merged first sentence) in one paragraph: strip the label.
SHORT = 120  # a paragraph this short is a heading, so a dash after the label is a separator
LABEL_PREFIX = [
    # "Chapitre I — La lettre", "CHAPITRE PREMIER LES TROIS PRÉSENTS", "Chapitre I Vers la fin..."
    re.compile(rf"^(?:CHAPITRE|Chapitre)\s+(?:{ROMAN}|\d+|PREMIER|Premier|premier|Ier|1er)\b\.?\s*"
               r"(?P<sep>(?:—|–|--|-|:)\s*)?(?=\S)"),
    # "Livre premier--Un juste", "LIVRE PREMIER--LA NUIT MOINS NOIRE QUE L'HOMME"
    re.compile(rf"^(?:LIVRE|Livre)\s+\S+\s*(?P<sep>(?:—|–|--)\s*)(?=\S)"),
    # "PREMIÈRE PARTIE--LA MER ET LA NUIT"
    re.compile(r"^(?:PREMIÈRE|DEUXIÈME|DEUXIEME|TROISIÈME)\s+PARTIE\s*(?P<sep>(?:—|–|--)\s*)(?=\S)"),
    # "I--URSUS", "I -- UNE TABLE D'HÔTE", "IV.  APRÈS CIMOURDAIN JUGE"
    re.compile(rf"^{ROMAN}\.?\s*(?P<sep>(?:—|–|--)\s*|\s{{2,}})(?=\S)"),
    # "I. Le fantôme de Richelieu" (not single L/C/D/M, which are usually initials)
    re.compile(r"^(?:[IVX]{1,6}|[IVXLC]{2,7})\.\s+(?=[A-ZÀ-ÖØ-Þ])"),
]


def strip_label_prefix(paragraph: str) -> str:
    """Remove a numbering label at the start of a paragraph, keep the rest."""
    chapter, *others = LABEL_PREFIX
    m = chapter.match(paragraph)
    if m:
        if len(paragraph) >= SHORT and m.group("sep") and m.group("sep").strip() in ("--", "-"):
            # Heading merged into a long paragraph ("Chapitre VIII -- Oui, dit
            # le vieillard..."): the dash opens the first line of dialogue.
            return paragraph[m.start("sep"):]
        return paragraph[m.end():]
    # Other labels only on heading-length paragraphs. Some chapter titles in
    # Vingt ans après are long sentences, hence the higher limit for the
    # roman-numeral patterns.
    for pattern, limit in zip(others, (SHORT, SHORT, 250, 250)):
        m = pattern.match(paragraph)
        if m and len(paragraph) < limit:
            return paragraph[m.end():]
    return paragraph


# ----------------------------------------------------------------------
# Processing
# ----------------------------------------------------------------------

def norm(paragraph: str) -> str:
    return " ".join(paragraph.split())


def words(paragraphs) -> int:
    return sum(len(p.split()) for p in paragraphs)


def tidy(text: str) -> str:
    """Clean spacing left behind by an inline removal."""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +([,.)])", r"\1", text)
    return text.strip()


def process(paragraphs: list[str], rule: dict, log) -> list[str]:
    n = [norm(p) for p in paragraphs]
    category = [None] * len(paragraphs)  # None = keep

    # Front segments.
    pos = 0
    for cat, anchor in rule.get("front", []):
        idx = anchor.find(n, pos)
        for i in range(pos, idx):
            category[i] = cat
        pos = idx
    text_start = pos

    # Middle ranges.
    for a, b, cat in rule.get("ranges", []):
        i = a.find(n, text_start)
        j = b.find(n, i)
        for k in range(i, j + 1):
            category[k] = cat

    # Back segments.
    back = rule.get("back", [])
    positions = []
    search = text_start
    for anchor, cat in back:
        idx = anchor.find(n, search)
        positions.append((idx, cat))
        search = idx + 1
    for (idx, cat), nxt in zip(positions, positions[1:] + [(len(n), None)]):
        for k in range(idx, nxt[0]):
            category[k] = cat

    # Global paragraph rules (only inside the kept text).
    open_bracket = None
    for i, p in enumerate(n):
        if category[i] is not None:
            continue
        if open_bracket:
            category[i] = open_bracket[0]
            open_bracket[1] += p.count("[") - p.count("]")
            if open_bracket[1] <= 0:
                open_bracket = None
            continue
        for cat, rx in BRACKET_DROP:
            if rx.match(p):
                category[i] = cat
                depth = p.count("[") - p.count("]")
                if depth > 0:
                    open_bracket = [cat, depth]
                break
        if category[i] is not None:
            continue
        for cat, rx in GLOBAL_DROP:
            if rx.match(p):
                category[i] = cat
                break
        if category[i] is None and LABEL_DROP.match(p):
            category[i] = "structural_label"

    # Keep categories that are not in REMOVE.
    kept, removed = [], defaultdict(list)
    for i, p in enumerate(paragraphs):
        cat = category[i]
        if cat is None or cat not in REMOVE:
            kept.append((i, p))
        else:
            removed[cat].append(i)

    for cat, idxs in removed.items():
        # Contiguous blocks make the report readable.
        blocks, start, prev = [], idxs[0], idxs[0]
        for k in idxs[1:]:
            if k != prev + 1:
                blocks.append((start, prev))
                start = k
            prev = k
        blocks.append((start, prev))
        for s, e in blocks:
            log(cat, "paragraphs", e - s + 1, words(n[s:e + 1]), n[s][:90], n[e][:90] if e != s else "")

    # Inline edits.
    inline = [(cat, rx, rep) for cat, rx, rep in GLOBAL_INLINE]
    inline += [(cat, re.compile(rx, re.M), rep) for rx, rep, cat in rule.get("inline", [])]
    out = []
    for i, p in kept:
        new = p
        for cat, rx, rep in inline:
            if cat not in REMOVE:
                continue
            found = rx.findall(new)
            if found:
                before = words([new])
                new = rx.sub(rep, new)
                log(cat, "inline", len(found), before - words([new]), norm(p)[:90], "")
        if "structural_label" in REMOVE:
            stripped = strip_label_prefix(new)
            if stripped != new:
                log("structural_label", "inline", 1, words([new]) - words([stripped]), norm(new)[:90], norm(stripped)[:60])
                new = stripped
        if new != p:
            new = tidy(new)
        if new.strip():
            out.append(new)
    return out


def split_paragraphs(text: str) -> list[str]:
    return [p.strip("\n") for p in re.split(r"\n\s*\n", text) if p.strip()]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if not CLEANED_DIR.is_dir():
        print(f"ERROR: {CLEANED_DIR} not found. Run clean_corpus.py first.", file=sys.stderr)
        return 1
    hashes = json.loads(HASHES_PATH.read_text(encoding="utf-8")) if HASHES_PATH.exists() else {}

    files = sorted(CLEANED_DIR.glob("*.txt"))
    report, summary, errors = [], [], []
    for path in files:
        ebook_id = path.name.split("_", 1)[0]
        rule = RULES.get(ebook_id)
        if rule is None:
            errors.append(f"{path.name}: no rule for ebook {ebook_id}")
            continue
        data = path.read_bytes()
        digest = sha256(data)
        expected = hashes.get(path.name, {})
        if digest == expected.get("output_sha256"):
            print(f"SKIP already processed: {path.name}")
            continue
        if expected and digest != expected.get("input_sha256"):
            print(f"WARNING input differs from the version the rules were written for: {path.name}")

        text = data.decode("utf-8-sig")
        paragraphs = split_paragraphs(text)

        def log(cat, kind, count, nwords, first, last, _name=path.name):
            report.append({"file": _name, "category": cat, "kind": kind, "count": count,
                           "words_removed": nwords, "first": first, "last": last})

        try:
            kept = process(paragraphs, rule, log)
        except LookupError as exc:
            errors.append(f"{path.name}: {exc}; file left unchanged")
            continue

        result = "\n\n".join(kept) + "\n"
        path.write_text(result, encoding="utf-8", newline="\n")
        before, after = words(paragraphs), words(kept)
        summary.append({"file": path.name, "paragraphs_before": len(paragraphs), "paragraphs_after": len(kept),
                        "words_before": before, "words_after": after,
                        "percent_removed": round(100 * (before - after) / before, 2) if before else 0,
                        "output_sha256": sha256(result.encode("utf-8"))})
        print(f"OK {path.name}: {before:,} -> {after:,} words")

    if report:
        with REPORT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(report[0]))
            w.writeheader()
            w.writerows(report)
    if summary:
        with SUMMARY_PATH.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(summary[0]))
            w.writeheader()
            w.writerows(summary)

    print(f"\nProcessed: {len(summary)}  Errors: {len(errors)}")
    for e in errors:
        print("ERROR", e)
    if report:
        print(f"Report: {REPORT_PATH}")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
