# analyse-immobilier-dvf

> Evolution des prix de l'immobilier dans les grandes villes francaises (donnees DVF)

<!--
  Ordre imposé : le résultat AVANT la méthode. Un lecteur donne 20 secondes à ce fichier.
  Remplacer chaque section, puis supprimer ces commentaires.
-->

## Résultat

<!-- Capture d'écran, chiffre clé, ou lien vers la démo déployée. Mettre le visuel ICI. -->

![Aperçu](docs/apercu.png)

**Démo en ligne** : <lien Streamlit Cloud ou Hugging Face Spaces, ou « application locale »>

**Notebook de restitution** : [`notebooks/01_restitution.ipynb`](notebooks/01_restitution.ipynb)
— lisible directement sur GitHub, graphiques compris.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eliasbabouche/NOM-DU-DEPOT/blob/main/notebooks/01_restitution.ipynb)

## Données

| | |
|---|---|
| Source | <nom + lien> |
| Volume | <nombre de lignes / poids> |
| Période | <plage temporelle couverte> |
| Licence | <Licence Ouverte / CC-BY / …> |
| Mise à jour | <fréquence de publication de la source> |

Les données brutes ne sont pas versionnées. Pour les récupérer :

```bash
python src/telecharger_donnees.py
```

## Méthode

1. <étape>
2. <étape>
3. <étape>

**Choix assumés et limites** — la section que personne n'écrit, et qui fait la différence :

- <choix technique + pourquoi ce compromis>
- <limite connue du résultat : biais des données, période non couverte, hypothèse fragile>

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
donnees/      brut/ (non versionné) et traite/
```

Le code vit dans `src/` et reste testable ; le notebook importe depuis `src/` et raconte
l'histoire. Ses sorties sont volontairement conservées dans le fichier pour que les
graphiques s'affichent sur GitHub sans rien exécuter.

## Licence

MIT — voir [LICENSE](LICENSE).

