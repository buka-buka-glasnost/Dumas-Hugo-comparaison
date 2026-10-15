# Lemmatisation et annotation linguistique

## Objectif

Cette étape du projet applique le modèle français `fr_core_news_lg` de spaCy aux 31 unités d’analyse du corpus Dumas–Hugo. Elle produit des annotations token par token destinées aux analyses lexicales et, éventuellement, syntaxiques ultérieures.

Les textes complets et les fichiers de sortie volumineux sont conservés localement. Le dépôt public contient le code de traitement et le rapport synthétique, et non les corpus textuels dérivés.

## Environnement et modèle

- **Bibliothèque :** spaCy
- **Version de spaCy utilisée pour cette exécution :** 3.8.16
- **Modèle :** `fr_core_news_lg`
- **Version du modèle utilisée :** 3.8.0
- **Taille du lot (`BATCH_SIZE`) :** 16
- **Longueur maximale du document (`MAX_LENGTH`) :** 5 000 000 caractères

Le pipeline est chargé avec ses composants par défaut. Il comprend donc notamment l’analyse morphologique, la lemmatisation, l’analyse syntaxique et la reconnaissance d’entités nommées. La liste exacte des composants actifs est affichée par le script au démarrage.

## Entrées et sorties

Le script `lemmatize_corpus.py` lit les fichiers `.txt` du répertoire `data/works/` et écrit les résultats dans `data/lemmas/`.

Pour chaque texte, il produit un fichier compressé au format TSV (`.tokens.tsv.gz`). Chaque ligne représente un token. Le script génère également `lemmatization_report.csv`, qui résume le traitement par fichier.

## Champs du fichier token par token

| Champ | Description |
|---|---|
| `paragraph_index` | Numéro du paragraphe dans le texte source. |
| `token_index` | Position du token dans son paragraphe, à partir de 1. |
| `token` | Forme de surface du token. |
| `lemma` | Lemme attribué par spaCy. |
| `lemma_lower` | Lemme converti en minuscules. |
| `pos` | Catégorie grammaticale universelle attribuée par spaCy. |
| `tag` | Étiquette morphosyntaxique détaillée du modèle. |
| `morph` | Caractéristiques morphologiques prédites. |
| `is_alpha` | Indique si le token est alphabétique selon spaCy. |
| `is_stop` | Indique si spaCy considère le token comme un mot-outil. |
| `is_punct` | Indique si le token est considéré comme un signe de ponctuation. |
| `is_digit` | Indique si le token est numérique selon spaCy. |
| `sentence_index` | Numéro de la phrase dans le paragraphe ; la numérotation recommence à chaque paragraphe. |
| `sentence_start` | Indique si le token est le premier token de la phrase. |
| `dependency` | Relation de dépendance syntaxique prédite pour le token. |
| `head` | Forme du token tête dans la relation de dépendance. |
| `head_token_index` | Position, à partir de 1, du token tête dans le paragraphe. |
| `entity_text` | Texte complet de l’entité reconnue à laquelle appartient le token, le cas échéant. |
| `entity_type` | Type d’entité attribué par spaCy, le cas échéant. |
| `entity_iob` | Marqueur de position dans une entité (`B`, `I` ou `O`). |

Les indices des tokens et des têtes syntaxiques sont locaux au paragraphe. Les indices de phrase recommencent également à chaque paragraphe. Les relations syntaxiques doivent donc être interprétées à l’intérieur de ce cadre local.

## Rapport de traitement

Le fichier `lemmatization_report.csv` contient, pour chaque texte :

- le nom du fichier source et celui du fichier de sortie ;
- les sommes de contrôle SHA-256 du fichier source et du fichier de sortie ;
- la taille du fichier source en octets ;
- le nombre de paragraphes, de phrases détectées et de tokens ;
- les nombres de tokens alphabétiques, de mots-outils, de signes de ponctuation, de tokens numériques et de tokens associés à une entité ;
- les versions de spaCy et du modèle.

Le nombre de tokens associés à une entité n’est **pas** le nombre d’entités distinctes ni le nombre de noms de personnes. Il compte les tokens dont la marque `entity_iob` est différente de `O`.

## Limites et précautions méthodologiques

1. **Annotations automatiques.** Les lemmes, catégories grammaticales, dépendances syntaxiques, limites de phrases et entités sont des prédictions du modèle. Ils n’ont pas encore fait l’objet d’une validation manuelle exhaustive.
2. **Français littéraire du XIXe siècle.** Le modèle n’a pas été spécifiquement entraîné pour les œuvres de Dumas et de Hugo. L’orthographe historique, les formes archaïques, les noms propres et certaines constructions littéraires peuvent entraîner des erreurs.
3. **Reconnaissance d’entités nommées.** La reconnaissance automatique ne détecte pas tous les noms propres et peut classer incorrectement certains mots. Les entités doivent être évaluées sur un échantillon avant toute exclusion systématique.
4. **Conservation des données.** Les tokens originaux sont conservés. Aucune suppression automatique des noms propres ou des mots-outils n’est effectuée à cette étape. Les variantes filtrées doivent être produites séparément afin de préserver les données annotées d’origine.
5. **Granularité des phrases.** Les phrases sont numérotées à l’intérieur de chaque paragraphe. Cette convention simplifie le traitement de longs textes, mais doit être prise en compte lors de la construction de données au niveau de la phrase.
6. **Périmètre du corpus.** Le rapport décrit les fichiers effectivement traités ; il ne constitue pas, à lui seul, une preuve de validation exhaustive du contenu littéraire ou du paratexte de chaque œuvre.

## Reproductibilité

Depuis la racine du dépôt, après installation de spaCy et du modèle :

```bash
py -m pip install -U spacy
py -m spacy download fr_core_news_lg
py lemmatize_corpus.py
```

Les versions de spaCy et du modèle sont consignées dans le rapport de traitement. Pour une reproduction stricte à long terme, il est recommandé de conserver également les versions exactes des dépendances dans un fichier de verrouillage de l’environnement.

## Statut

Le pipeline de lemmatisation et d’annotation a été exécuté sur les 31 fichiers recensés dans le rapport de traitement. Les annotations doivent encore faire l’objet d’un contrôle qualitatif sur un échantillon avant d’être utilisées comme résultats linguistiques validés.
