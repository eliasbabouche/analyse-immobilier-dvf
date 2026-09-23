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

from pathlib import Path

import pandas as pd
import requests

from src import config

# Certains serveurs publics refusent les requetes qui ne s'identifient pas.
ENTETES = {"User-Agent": "analyse-immobilier-dvf (projet open data)"}
DELAI_MAX = 60  # secondes, pour ne jamais rester bloque sur un serveur muet


# --- Referentiel des metropoles -------------------------------------------------------


def _appeler_api_geo(chemin: str, champs: str) -> dict | list:
    reponse = requests.get(
        f"{config.URL_API_GEO}{chemin}",
        params={"fields": champs},
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
