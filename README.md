# analyse-immobilier-dvf

> Comment les prix de l'immobilier ont-ils évolué dans les grandes villes françaises depuis
> cinq ans, et où l'écart entre le centre et la périphérie se creuse-t-il le plus ?

## Résultat

*En cours de construction : dashboard, capture et chiffres clés à venir.*

**Démo en ligne** : à venir (Streamlit Community Cloud)

**Notebook de restitution** : [`notebooks/01_restitution.ipynb`](notebooks/01_restitution.ipynb)
— lisible directement sur GitHub, graphiques compris.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eliasbabouche/analyse-immobilier-dvf/blob/main/notebooks/01_restitution.ipynb)

## Données

| | |
|---|---|
| Source | [Demandes de valeurs foncières géolocalisées](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/) (DGFiP, mise en forme Etalab) |
| Complément | Communes de chaque métropole (référentiel INSEE), via l'[API Découpage administratif](https://geo.api.gouv.fr/decoupage-administratif) |
| Volume | ~80 000 lignes pour un département comme la Loire-Atlantique, environ 3 millions par an pour la France |
| Période | 2021 à 2025 (millésime Etalab de décembre 2025, figé) |
| Licence | Licence Ouverte / Open Licence 2.0 |
| Mise à jour | semestrielle (avril et octobre) |

Chaque ligne décrit un bien ou une parcelle d'une vente (une *mutation*) : date, prix, adresse,
type de bien, surface bâtie, nombre de pièces, coordonnées GPS.

Les données brutes ne sont pas versionnées. Pour les récupérer :

```bash
python -m src.telecharger_donnees
```

## Méthode

**Périmètre.** Les dix plus grandes villes de France présentes dans le DVF : Paris, Marseille,
Lyon, Toulouse, Nice, Nantes, Montpellier, Bordeaux, Lille, Rennes. Pour chacune, on compare la
**ville-centre** aux **autres communes de sa métropole** (son EPCI, regroupement officiel de
communes défini par l'INSEE).

1. **Téléchargement** des fichiers départementaux utiles uniquement, année par année, pour ne
   jamais charger la France entière en mémoire.
2. **Nettoyage**, le cœur du projet :
   - ne garder que les ventes classiques (`nature_mutation = Vente`) : les échanges,
     adjudications, expropriations et ventes sur plan (VEFA) ne reflètent pas le prix de
     marché de l'ancien ;
   - **raisonner par vente et non par ligne** (voir ci-dessous) ;
   - ne garder que les ventes contenant **exactement un logement** (maison ou appartement),
     dépendances comprises ;
   - écarter les prix et surfaces nuls ou manquants, puis les prix au m² aberrants.
3. **Rattachement géographique** : les arrondissements de Paris, Lyon et Marseille sont
   ramenés à leur commune, puis chaque commune est rattachée à sa métropole.
4. **Agrégation** : prix médian au m² par commune, par année et par type de bien.
5. **Restitution** : dashboard Streamlit et notebook.

### Le piège des ventes multi-lots

Une vente qui comprend plusieurs biens (un appartement, une cave, un parking) apparaît sur
plusieurs lignes, et **le prix total de la vente est répété sur chacune d'elles**. Mesuré sur
la Loire-Atlantique en 2025 :

| Indicateur | Calcul naïf (par ligne) | Calcul correct (par vente) | Écart |
|---|---|---|---|
| Volume total des ventes | 30,0 Md€ | 7,4 Md€ | ×4,1 |
| Prix **moyen** au m², appartements à Nantes | 9 555 € | 3 668 € | +161 % |
| Prix **médian** au m², appartements à Nantes | 3 516 € | 3 385 € | +4 % |

Deux protections complémentaires en découlent : dédoublonner par vente, et travailler sur la
**médiane**, peu sensible aux valeurs extrêmes qui subsisteraient.

### Choix assumés et limites

- **Ventes à plusieurs logements écartées** (6 % des ventes contenant un logement dans les
  dix métropoles) : leur prix global ne peut pas être réparti entre les logements. Ce sont
  souvent des ventes en bloc à des investisseurs, dont l'exclusion peut légèrement biaiser les
  résultats.
- **Neuf exclu** : les ventes sur plan (VEFA) suivent un marché distinct. Les résultats portent
  sur l'ancien.
- **Strasbourg absente** : l'Alsace et la Moselle relèvent du livre foncier et ne sont pas
  publiées dans le DVF. Rennes la remplace dans le top 10.
- **La métropole comme périphérie** : un découpage administratif, simple et vérifiable, mais qui
  varie beaucoup en taille d'une ville à l'autre (la métropole d'Aix-Marseille compte près de
  cent communes, Rennes Métropole beaucoup moins).
- **Source retraitée** : la version géolocalisée d'Etalab est une mise en forme du fichier brut
  de la DGFiP, et non la publication officielle elle-même.

## Exécution

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run src/app.py
```

## Tests

```bash
pytest
```

## Structure

```
src/          code métier, une responsabilité par module
tests/        tests unitaires
notebooks/    restitution : importe depuis src/, ne contient pas de logique métier
donnees/      brut/ et traite/ (non versionnés), reference/ et agrege/ (petits, versionnés)
```

Les tableaux de `donnees/agrege/` sont versionnés pour que le dashboard en ligne n'ait pas à
retélécharger et nettoyer les données. Toute modification du nettoyage impose de les régénérer
(`python -m src.nettoyage` puis `python -m src.agregations`) et de les commiter.

Le code vit dans `src/` et reste testable ; le notebook importe depuis `src/` et raconte
l'histoire. Ses sorties sont volontairement conservées dans le fichier pour que les
graphiques s'affichent sur GitHub sans rien exécuter.

## Licence

MIT — voir [LICENSE](LICENSE).
