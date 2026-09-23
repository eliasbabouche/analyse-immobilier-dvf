"""Telechargement des donnees sources.

Deux etapes :
1. Referentiel : la liste des communes de chaque metropole, via l'API geo.api.gouv.fr
   (referentiel INSEE). Petit fichier, versionne dans donnees/reference/.
2. DVF : les fichiers departementaux de chaque annee, pour les seuls departements
   touches par une metropole. La liste est deduite du referentiel, jamais ecrite a la
   main : le Grand Paris deborde sur six departements, Aix-Marseille sur trois.

Usage, depuis la racine du projet :
    python -m src.telecharger_donnees
"""

import json
from pathlib import Path

import pandas as pd
import requests

from src import config

# Certains serveurs publics refusent les requetes qui ne s'identifient pas.
ENTETES = {"User-Agent": "analyse-immobilier-dvf (projet open data)"}
DELAI_MAX = 60  # secondes, pour ne jamais rester bloque sur un serveur muet


# --- Referentiel des metropoles -------------------------------------------------------


def _appeler_api_geo(chemin: str, champs: str, **autres_parametres) -> dict | list:
    reponse = requests.get(
        f"{config.URL_API_GEO}{chemin}",
        params={"fields": champs, **autres_parametres},
        headers=ENTETES,
        timeout=DELAI_MAX,
    )
    reponse.raise_for_status()
    return reponse.json()


def construire_referentiel(villes: dict[str, str]) -> pd.DataFrame:
    """Une ligne par commune de metropole, avec sa ville de rattachement."""
    lignes = []
    for ville, code_centre in villes.items():
        centre = _appeler_api_geo(f"/communes/{code_centre}", "codeEpci")
        code_epci = centre["codeEpci"]
        epci = _appeler_api_geo(f"/epcis/{code_epci}", "nom")
        membres = _appeler_api_geo(
            f"/epcis/{code_epci}/communes", "code,nom,codeDepartement,population"
        )
        for commune in membres:
            lignes.append(
                {
                    "ville": ville,
                    "code_epci": code_epci,
                    "nom_epci": epci["nom"],
                    "code_commune": commune["code"],
                    "nom_commune": commune["nom"],
                    "code_departement": commune["codeDepartement"],
                    "population": commune.get("population"),
                    "est_centre": commune["code"] == code_centre,
                }
            )
    return pd.DataFrame(lignes)


def arrondir_coordonnees(coordonnees, decimales: int):
    """Arrondit toutes les coordonnees d'une geometrie GeoJSON, quelle que soit sa forme.

    Un Polygon est une liste d'anneaux, un MultiPolygon une liste de Polygon : la
    fonction descend dans les listes jusqu'aux nombres.
    """
    if isinstance(coordonnees, (int, float)):
        return round(coordonnees, decimales)
    return [arrondir_coordonnees(element, decimales) for element in coordonnees]


def construire_contours(codes_epci: list[str]) -> dict:
    """Contours GeoJSON de toutes les communes des metropoles, coordonnees arrondies."""
    communes = []
    for code_epci in codes_epci:
        collection = _appeler_api_geo(
            f"/epcis/{code_epci}/communes", "code", format="geojson", geometry="contour"
        )
        for commune in collection["features"]:
            geometrie = commune["geometry"]
            geometrie["coordinates"] = arrondir_coordonnees(
                geometrie["coordinates"], config.DECIMALES_CONTOURS
            )
            communes.append(commune)
    return {"type": "FeatureCollection", "features": communes}


def departements_a_telecharger(referentiel: pd.DataFrame) -> list[str]:
    """Departements distincts touches par au moins une metropole, tries."""
    return sorted(referentiel["code_departement"].unique())


# --- Fichiers DVF ----------------------------------------------------------------------


def url_dvf(annee: int, departement: str) -> str:
    return config.URL_DVF.format(
        millesime=config.MILLESIME_DVF, annee=annee, departement=departement
    )


def chemin_dvf(annee: int, departement: str) -> Path:
    return config.DONNEES_BRUT / f"dvf_{annee}_{departement}.csv.gz"


def telecharger(url: str, destination: Path) -> bool:
    """Telecharge url vers destination. Renvoie False si le fichier etait deja present.

    Le fichier est d'abord ecrit sous un nom temporaire (.part), puis renomme une fois
    complet : une coupure reseau ne laisse jamais un fichier tronque qui passerait
    ensuite pour un fichier deja telecharge.
    """
    if destination.exists():
        return False

    temporaire = destination.with_name(destination.name + ".part")
    try:
        with requests.get(url, headers=ENTETES, timeout=DELAI_MAX, stream=True) as reponse:
            reponse.raise_for_status()
            with open(temporaire, "wb") as fichier:
                for bloc in reponse.iter_content(chunk_size=1024 * 1024):
                    fichier.write(bloc)
        if temporaire.stat().st_size == 0:
            raise ValueError(f"Fichier vide recu depuis {url}")
        temporaire.replace(destination)
    finally:
        temporaire.unlink(missing_ok=True)
    return True


# --- Point d'entree --------------------------------------------------------------------


def main() -> None:
    config.creer_dossiers()

    print("Referentiel des metropoles (API geo) ...")
    referentiel = construire_referentiel(config.VILLES)
    referentiel.to_csv(
        config.FICHIER_METROPOLES,
        sep=config.SEPARATEUR_EXPORT,
        encoding=config.ENCODAGE_EXPORT,
        index=False,
    )
    print(f"  {len(referentiel)} communes -> {config.FICHIER_METROPOLES.name}")

    print("Contours des communes (API geo) ...")
    contours = construire_contours(sorted(referentiel["code_epci"].unique()))
    with open(config.FICHIER_CONTOURS, "w", encoding="utf-8") as fichier:
        # separators sans espaces : quelques centaines de Ko en moins
        json.dump(contours, fichier, ensure_ascii=False, separators=(",", ":"))
    taille = config.FICHIER_CONTOURS.stat().st_size / 1e6
    print(f"  {len(contours['features'])} contours -> {config.FICHIER_CONTOURS.name} "
          f"({taille:.1f} Mo)")

    departements = departements_a_telecharger(referentiel)
    print(f"Fichiers DVF : {len(departements)} departements x {len(config.ANNEES)} annees")
    for annee in config.ANNEES:
        for departement in departements:
            destination = chemin_dvf(annee, departement)
            nouveau = telecharger(url_dvf(annee, departement), destination)
            etat = "telecharge" if nouveau else "deja present"
            print(f"  {destination.name:22} {etat}")


if __name__ == "__main__":
    main()
