# Analyse computationnelle du lexique et du style : Alexandre Dumas père et Victor Hugo

## Présentation du projet

Ce projet explore les possibilités de l'analyse computationnelle pour étudier les caractéristiques lexicales et stylistiques des œuvres romanesques d'**Alexandre Dumas père** et de **Victor Hugo**.

À l'aide de Python et des méthodes du traitement automatique du langage naturel (TALN), le projet vise à constituer un corpus littéraire numérique reproductible, à analyser les propriétés linguistiques des textes et à examiner les différences et les ressemblances entre les deux auteurs.

Le projet s'inscrit à l'intersection de la **science des données, du traitement automatique des langues et des humanités numériques**.

**Statut :** en cours de développement — constitution et validation du corpus.

## Objectifs de recherche

Les principaux objectifs sont les suivants :

- Constituer un corpus numérique de textes littéraires en français attribués à Alexandre Dumas père et à Victor Hugo.
- Automatiser le téléchargement, le nettoyage et la préparation des textes.
- Étudier les fréquences lexicales et la distribution des lemmes.
- Mesurer la diversité lexicale et examiner les différences de vocabulaire entre les œuvres.
- Utiliser des méthodes statistiques et des techniques de représentation des textes pour comparer les deux auteurs.
- Évaluer dans quelle mesure les différences observées sont cohérentes d'une œuvre à l'autre, en tenant compte de la longueur des textes et, lorsque les données le permettent, du genre littéraire.

L'objectif n'est pas de présupposer l'existence de styles homogènes ou systématiquement opposés, mais de formuler et d'évaluer des hypothèses à partir des données.

## Corpus

Le corpus de travail comprend actuellement **54 volumes téléchargés, regroupés en 31 unités d'analyse**, selon les rapports de construction du corpus.

Les auteurs étudiés sont :

- **Alexandre Dumas père** (1802–1870)
- **Victor Hugo** (1802–1885)

Le corpus est constitué à partir de textes disponibles dans le catalogue de Project Gutenberg.

Les critères de sélection prévoient l'inclusion de romans et de textes de fiction courts. Les œuvres non fictionnelles, la poésie, le théâtre, les textes d'autres auteurs et les œuvres simplement traduites ou éditées par Dumas sont exclus du périmètre prévu.

Les œuvres publiées en plusieurs volumes sont regroupées en unités d'analyse uniques, tout en conservant les fichiers sources et l'ordre des volumes.

Le corpus reste provisoire : les choix bibliographiques, l'intégrité des textes et les éventuels éléments éditoriaux résiduels doivent encore faire l'objet d'une validation approfondie.

## Méthodologie

Le traitement des données est organisé en plusieurs étapes.

### 1. Identification des textes

Une première étape consiste à interroger le catalogue de Project Gutenberg et à identifier les textes français associés aux auteurs étudiés.

Un manifeste documente les textes retenus, les exclusions et les décisions de sélection.

### 2. Téléchargement

Les textes approuvés sont téléchargés automatiquement. Les fichiers originaux sont conservés séparément afin de permettre les contrôles et de reproduire les étapes suivantes.

### 3. Contrôle et nettoyage

Des scripts vérifient la présence des fichiers attendus et des marqueurs de début et de fin de Project Gutenberg.

Les éléments d'encadrement éditorial sont ensuite retirés pour produire des versions nettoyées des textes. Cette étape nécessite encore des vérifications qualitatives sur des extraits représentatifs.

### 4. Regroupement des volumes

Les volumes appartenant à une même œuvre sont concaténés dans l'ordre prévu par le manifeste. Les fichiers individuels sont conservés afin de préserver la traçabilité des opérations.

### 5. Prétraitement linguistique

L'étape suivante prévoit l'utilisation de modèles de TALN adaptés au français, notamment pour la tokenisation et la lemmatisation. Les listes de mots-outils et les règles de filtrage seront définies en fonction des analyses réalisées.

### 6. Analyse exploratoire et comparative

Les analyses envisagées comprennent :

- les fréquences des mots et des lemmes ;
- la fréquence relative des unités lexicales ;
- la diversité lexicale ;
- la pondération TF-IDF ;
- la comparaison des distributions lexicales entre les auteurs et les œuvres ;
- des visualisations et des analyses statistiques adaptées aux données.

Les comparaisons tiendront compte de la longueur des textes. Les résultats seront interprétés à l'échelle des œuvres, afin d'éviter de confondre les propriétés d'un texte particulier avec celles de l'ensemble de la production d'un auteur.

## Technologies envisagées

- **Python** — automatisation et analyse des données ;
- **spaCy** — traitement linguistique et lemmatisation ;
- **pandas** — gestion des métadonnées et des tableaux de résultats ;
- **scikit-learn** — vectorisation et analyses TF-IDF ;
- **Jupyter Notebook** — exploration, visualisation et documentation des analyses ;
- **Apache Spark** — traitement distribué lorsque cela est pertinent pour les objectifs du projet.

Les bibliothèques et versions effectivement utilisées seront documentées au fur et à mesure de la stabilisation du pipeline.

## Structure du projet

La structure cible du dépôt est la suivante :

```text
dumas-hugo-lexical-analysis/
├── README.md
├── .gitignore
├── requirements.txt
├── gutenberg_corpus.py
├── download_approved_texts.py
├── audit_raw_corpus.py
├── clean_corpus.py
├── join_volumes.py
├── corpus_manifest_reviewed_v2.csv
├── notebooks/
└── data/
    ├── raw/
    ├── cleaned/
    └── works/
```

Les répertoires `data/raw/`, `data/cleaned/` et `data/works/` sont destinés aux données générées localement et ne doivent pas être publiés par défaut dans le dépôt.

Cette structure est indicative : elle pourra évoluer au fur et à mesure du développement.

## Reproductibilité

Le pipeline est conçu pour séparer les textes sources, les données nettoyées et les œuvres regroupées.

Pour reproduire le traitement, il faut disposer de Python, des scripts du projet et du manifeste du corpus. Les dépendances exactes, les instructions d'installation et les commandes d'exécution seront précisées après stabilisation de l'environnement.

Les textes ne sont pas inclus dans le dépôt. Les utilisateurs doivent vérifier les conditions d'utilisation applicables et récupérer les sources à partir de leurs pages d'origine.

## Limites actuelles

Plusieurs précautions méthodologiques sont nécessaires :

- Le corpus n'a pas encore fait l'objet d'une validation bibliographique exhaustive.
- Les deux auteurs ne sont pas représentés de manière équilibrée en nombre d'œuvres.
- La longueur et le genre des textes peuvent influencer les résultats lexicaux.
- Le nettoyage automatique ne garantit pas l'élimination de tous les éléments éditoriaux.
- Les différences statistiques observées ne suffisent pas, à elles seules, à établir des différences stylistiques générales.

Ces limites seront prises en compte dans l'interprétation des résultats.

## Feuille de route

- [x] Identification initiale des textes dans le catalogue.
- [x] Constitution d'un manifeste de travail.
- [x] Téléchargement des 54 volumes sélectionnés.
- [x] Vérification structurelle des fichiers téléchargés.
- [x] Nettoyage automatique des 54 fichiers.
- [x] Regroupement en 31 unités d'analyse.
- [ ] Validation qualitative et bibliographique du corpus.
- [ ] Documentation de l'environnement Python et des dépendances.
- [ ] Prétraitement linguistique et lemmatisation.
- [ ] Analyse exploratoire et comparative.
- [ ] Visualisations et interprétation des résultats.
- [ ] Publication des résultats et documentation finale.

## Sources

Les textes sont identifiés à partir du catalogue de [Project Gutenberg](https://www.gutenberg.org/).

Les références bibliographiques et les identifiants des éditions retenues sont documentés dans le manifeste du corpus.

## Licence et droits d'auteur

Le code du projet pourra être distribué sous une licence libre définie séparément. Les droits applicables aux textes littéraires et aux éditions numériques doivent être examinés indépendamment, notamment en fonction de la juridiction concernée et des conditions de distribution des fichiers sources.

La présence d'un texte sur Project Gutenberg ne signifie pas nécessairement que toute redistribution de ce fichier est autorisée dans tous les pays.

---

*Projet de recherche en humanités numériques consacré à l'analyse computationnelle de la littérature française.*
