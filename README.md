# Analyse computationnelle du lexique et de la diversité lexicale : Alexandre Dumas père et Victor Hugo

## Présentation

Ce projet d'humanités numériques étudie les propriétés lexicales d'un corpus de textes de fiction en prose d'**Alexandre Dumas père** et de **Victor Hugo**, à l'aide de Python et de méthodes de traitement automatique du langage naturel (TALN).

Le pipeline couvre la constitution et l'audit du corpus, le nettoyage des textes, le regroupement des volumes, la lemmatisation, l'analyse lexicale et la production de visualisations.

**État du projet :** les analyses lexicales, la comparaison MATTR, les tests de robustesse et les visualisations ont été produits sur le corpus de travail. Il s'agit d'une étude exploratoire sur un corpus déterminé, et non d'une caractérisation définitive du style des deux auteurs.

## Corpus

Le corpus de travail comprend **54 volumes regroupés en 31 unités d'analyse** :

- **Alexandre Dumas père** : 24 unités d'analyse ;
- **Victor Hugo** : 7 unités d'analyse.

Les textes proviennent du catalogue de [Project Gutenberg](https://www.gutenberg.org/). Les volumes appartenant à une même œuvre sont regroupés selon les décisions consignées dans les manifestes du projet.

Les principaux fichiers de documentation du corpus sont :

- `corpus_manifest_reviewed_v2.csv` — sélection et décisions concernant les textes sources ;
- `corpus_manifest_v1_locked.csv` — métadonnées des unités d'analyse retenues ;
- `corpus_source_volume_map_v1.csv` — correspondance entre volumes sources et unités d'analyse ;
- `CORPUS_FREEZE_v1.md` — documentation du périmètre du corpus.

Les textes complets, les fichiers intermédiaires et les fichiers de lemmes peuvent occuper un volume important. Leur présence dans une copie locale dépend de la configuration du dépôt ; les manifestes et les rapports documentent le corpus et les traitements réalisés.

## Méthodologie

### 1. Constitution et audit du corpus

Les scripts de téléchargement s'appuient sur les métadonnées et les décisions consignées dans le manifeste. Les scripts d'audit vérifient la présence des fichiers attendus et certains marqueurs structurels. Ces contrôles facilitent la traçabilité, sans remplacer une vérification éditoriale exhaustive de chaque texte.

### 2. Nettoyage et regroupement

Le traitement comprend plusieurs étapes :

1. Téléchargement des textes approuvés.
2. Audit des fichiers sources.
3. Suppression de l'encadrement standard de Project Gutenberg.
4. Retrait ciblé de paratexte et d'artefacts éditoriaux à l'aide de règles spécifiques aux volumes.
5. Regroupement des volumes d'une même œuvre dans l'ordre prévu par le manifeste.

Les rapports de nettoyage, de retrait du paratexte, de construction et de validation permettent de consulter les opérations effectuées.

### 3. Lemmatisation et filtrage lexical

Les textes regroupés sont traités avec **spaCy** et un modèle de français. Les sorties de lemmatisation servent d'entrée aux analyses lexicales. Selon la variante d'analyse, les mesures peuvent porter sur les tokens alphabétiques, sur les lemmes de contenu après filtrage des mots-outils, ou sur un ensemble excluant les entités reconnues comme noms de personnes.

Ces variantes ne sont pas interchangeables : les résultats doivent être interprétés en fonction de la définition exacte de chaque ensemble lexical.

### 4. Analyses lexicales

Les scripts produisent notamment :

- des statistiques descriptives par œuvre ;
- les fréquences des lemmes par œuvre et par auteur ;
- des comparaisons de fréquences lexicales ;
- des représentations TF-IDF ;
- des mesures de diversité lexicale, dont la **Moving-Average Type–Token Ratio (MATTR)** ;
- des visualisations comparatives ;
- une analyse de robustesse de la comparaison MATTR, notamment par exclusion des œuvres les plus longues et par analyses *leave-one-work-out*.

Le TTR brut est sensible à la longueur des textes. MATTR utilise des fenêtres de taille fixe et permet une comparaison plus adaptée, sans éliminer pour autant toutes les différences liées au corpus.

## Résultat illustratif : diversité lexicale

Pour la variante **MATTR-500 sur les lemmes de contenu**, les moyennes descriptives observées dans le corpus sont approximativement :

| Auteur | Nombre d'unités | MATTR-500 moyen |
|---|---:|---:|
| Alexandre Dumas père | 24 | 0,634 |
| Victor Hugo | 7 | 0,703 |

Dans ce corpus, les œuvres de Hugo présentent une MATTR-500 moyenne plus élevée que celles de Dumas. La différence reste visible dans les analyses de robustesse effectuées.

Ce résultat est **descriptif et limité au corpus analysé**. Il ne permet pas, à lui seul, d'affirmer que Hugo possède en général une diversité lexicale supérieure à celle de Dumas. Le nombre inégal d'œuvres, la sélection des textes, les différences de genre, de période, d'édition et de forme narrative peuvent influencer les comparaisons. Les mesures dépendent également des règles de nettoyage, de lemmatisation et de filtrage.

Les tableaux CSV et les figures du dossier `reports/` permettent d'examiner les résultats œuvre par œuvre, sans réduire l'interprétation à une seule moyenne par auteur.

## Structure du dépôt

La structure exacte peut varier selon les fichiers de données conservés localement. Les principaux éléments sont :

```text
Dumas-Hugo-comparaison/
├── README.md
├── CORPUS_FREEZE_v1.md
├── LEMMATIZATION.md
├── corpus_manifest_reviewed_v2.csv
├── corpus_manifest_v1_locked.csv
├── corpus_source_volume_map_v1.csv
├── download_approved_texts.py
├── audit_raw_corpus.py
├── clean_corpus.py
├── strip_paratext.py
├── join_volumes.py
├── lemmatize_corpus.py
├── analyze_corpus.py
├── compare_mattr_authors.py
├── mattr_robustness.py
├── visualize_corpus.py
├── data/
│   ├── raw/
│   ├── cleaned/
│   ├── works/
│   └── lemmas/
└── reports/
    └── figures/
```

Les scripts de traitement sont à la racine du dépôt. `data/` contient les données de travail et les sorties intermédiaires selon la configuration locale ; `reports/` contient les tableaux et les visualisations produits par les analyses.

## Reproductibilité

### Prérequis

- Python 3.10 ou une version ultérieure ;
- les bibliothèques Python utilisées par les scripts, notamment spaCy, pandas, scikit-learn et matplotlib ;
- le modèle linguistique français de spaCy utilisé lors de la lemmatisation ;
- une connexion Internet pour télécharger à nouveau les textes depuis Project Gutenberg.

Les versions exactes des dépendances et du modèle doivent correspondre à l'environnement utilisé pour produire les résultats. Elles ne sont pas fixées dans ce README.

### Installation du dépôt

```bash
git clone https://github.com/buka-buka-glasnost/Dumas-Hugo-comparaison.git
cd Dumas-Hugo-comparaison
```

Installez les dépendances et le modèle spaCy requis pour les scripts que vous souhaitez exécuter. Les commandes exactes peuvent varier selon l'environnement Python utilisé.

### Ordre général du pipeline

À partir du répertoire racine du projet, les principales étapes sont :

```bash
python download_approved_texts.py
python audit_raw_corpus.py
python clean_corpus.py
python strip_paratext.py
python join_volumes.py
python lemmatize_corpus.py
python analyze_corpus.py
python compare_mattr_authors.py
python mattr_robustness.py
python visualize_corpus.py
```

Les scripts ne sont pas tous nécessaires si l'on souhaite seulement consulter les résultats déjà produits. Pour reproduire l'ensemble de la chaîne, vérifiez les manifestes, les rapports et les fichiers attendus par chaque script avant l'exécution. Les scripts de préparation dépendent des données locales présentes dans `data/`.

## Limites

- **Corpus déséquilibré :** 24 unités d'analyse de Dumas contre 7 de Hugo.
- **Sélection des œuvres :** les résultats reflètent le corpus retenu, et non l'intégralité de la production des deux auteurs.
- **Hétérogénéité littéraire et éditoriale :** période, genre, structure narrative, édition et longueur peuvent influer sur les mesures.
- **Nettoyage :** les règles ciblées réduisent le paratexte, mais ne garantissent pas l'absence de tout artefact résiduel.
- **Lemmatisation et reconnaissance d'entités :** les erreurs du modèle et les variations de filtrage peuvent modifier les comptages.
- **Interprétation statistique :** les fréquences agrégées sont descriptives ; les œuvres ne constituent pas un échantillon aléatoire de toute la production des auteurs.
- **Reproductibilité logicielle :** les résultats peuvent varier si les versions des bibliothèques, du modèle linguistique ou les fichiers d'entrée diffèrent.

Les analyses de robustesse renforcent la confiance dans la stabilité du contraste observé au sein du corpus retenu, mais elles ne résolvent pas les limites de sélection et de représentativité.

## Sources et droits

Les textes sont issus du catalogue de [Project Gutenberg](https://www.gutenberg.org/). Les identifiants et les décisions de sélection sont documentés dans les manifestes.

Le statut juridique des œuvres et des éditions numériques doit être évalué selon la juridiction applicable et les conditions de distribution de chaque fichier. La disponibilité d'un texte sur Project Gutenberg ne signifie pas automatiquement que sa redistribution est autorisée dans tous les pays.

Le code et les données textuelles peuvent relever de conditions de licence différentes. Aucune licence de redistribution des textes n'est revendiquée par ce README.

---

*Projet de science des données et d'humanités numériques consacré à l'analyse computationnelle du lexique dans la littérature française.*
