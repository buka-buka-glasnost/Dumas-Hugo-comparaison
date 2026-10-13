# Gel du corpus — Dumas-Hugo (v1.0)

**Date de gel : 14 octobre 2026**  
**Statut : périmètre des unités d'analyse verrouillé ; contrôle textuel structurel effectué ; validation exhaustive du paratexte encore incomplète.**

## Périmètre verrouillé

Le corpus v1.0 contient 31 unités d'analyse construites à partir de 54 volumes de Project Gutenberg :
- Alexandre Dumas père : 24 unités d'analyse ;
- Victor Hugo : 7 unités d'analyse.

Le corpus inclut la fiction en prose française : romans et récits courts. Les recueils de récits restent admissibles comme unités d'analyse ; ils ne sont pas exclus uniquement parce qu'ils regroupent plusieurs récits. La poésie, le théâtre, les textes non fictionnels, les traductions et les œuvres d'autres auteurs restent hors périmètre selon les critères du projet.

Les œuvres publiées en plusieurs volumes sont regroupées en une unité d'analyse. Les identifiants et l'ordre des volumes sont consignés dans `corpus_source_volume_map_v1.csv`.

## Fichiers de référence

- `corpus_manifest_v1_locked.csv` : manifeste au niveau des 31 œuvres, avec tailles, IDs sources et empreintes SHA-256.
- `corpus_source_volume_map_v1.csv` : correspondance des 54 volumes sources avec les unités d'analyse.
- `SHA256SUMS_works_v1.txt` : empreintes des fichiers de textes de la version auditée.

## Résultat du contrôle structurel

L'archive examinée contient 31 fichiers texte, environ 5,91 millions de mots selon un comptage approximatif, et aucune occurrence détectée des marqueurs de début ou de fin Project Gutenberg recherchés.

**Ce résultat n'est pas une preuve que tout le paratexte a été retiré.** Les préfaces, tables des matières, notes éditoriales et autres éléments de l'édition peuvent encore subsister. Le statut de validation de chaque œuvre est donc volontairement indiqué comme `STRUCTURAL_CHECK_PASSED; PARATEXT_REVIEW_NOT_EXHAUSTIVE`.

## Règles de versionnement

- Ne pas modifier les textes v1.0 silencieusement.
- Toute modification des fichiers, de la sélection ou du regroupement produit une nouvelle version (`v1.1`, `v1.2`, etc.) et de nouvelles empreintes SHA-256.
- Garder les fichiers sources et les sorties générées séparés.
- Documenter les exclusions, scissions et corrections dans un journal de changements.

## Limites

Les catégories de genre doivent encore être vérifiées bibliographiquement œuvre par œuvre. Le manifeste distingue donc les unités d'analyse sans prétendre que chaque sous-type est déjà confirmé. Les tailles de texte sont calculées automatiquement et sont approximatives.

Les textes complets ne sont pas inclus dans ce paquet de métadonnées. Vérifier les droits applicables avant toute redistribution des fichiers textuels.
