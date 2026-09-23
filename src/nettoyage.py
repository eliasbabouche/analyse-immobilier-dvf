"""Nettoyage des fichiers DVF : des lignes brutes a une table propre, une ligne par vente.

Chaque regle est une petite fonction testee separement. L'ordre compte : voir
nettoyer_fichier, en particulier le comptage des logements AVANT le filtre des surfaces.

Usage, depuis la racine du projet (apres telecharger_donnees) :
    python -m src.nettoyage
"""

from pathlib import Path

import pandas as pd

from src import config

# Seules colonnes utiles : lire les 40 colonnes quadruplerait la memoire.
COLONNES = {
    "id_mutation": str,
    "date_mutation": str,
    "nature_mutation": str,
    "valeur_fonciere": float,
    "code_commune": str,  # texte : "06088" ne doit pas devenir 6088
    "type_local": str,
    "surface_reelle_bati": float,
    "nombre_pieces_principales": float,
}

# Paris, Lyon et Marseille sont codes par arrondissement dans le DVF.
ARRONDISSEMENTS = {
    r"^751\d\d$": "75056",  # Paris : 75101 a 75120
    r"^6938\d$": "69123",  # Lyon : 69381 a 69389
    r"^132\d\d$": "13055",  # Marseille : 13201 a 13216
}


def charger(fichier: Path) -> pd.DataFrame:
    df = pd.read_csv(fichier, usecols=list(COLONNES), dtype=COLONNES)
    df["date_mutation"] = pd.to_datetime(df["date_mutation"], format="%Y-%m-%d")
    return df


def ramener_arrondissements(codes: pd.Series) -> pd.Series:
    """Remplace chaque code d'arrondissement par le code de sa commune."""
    for motif, code_commune in ARRONDISSEMENTS.items():
        codes = codes.str.replace(motif, code_commune, regex=True)
    return codes


def garder_mutations_metropoles(df: pd.DataFrame, codes_metropoles: set[str]) -> pd.DataFrame:
    """Garde TOUTES les lignes des ventes dont au moins une ligne est dans une metropole.

    Filtrer ligne par ligne couperait certaines ventes en deux et fausserait le
    comptage des logements qui suit.
    """
    touchees = df.loc[df["code_commune"].isin(codes_metropoles), "id_mutation"]
    return df[df["id_mutation"].isin(touchees)]


def garder_ventes(df: pd.DataFrame) -> pd.DataFrame:
    """Ecarte echanges, adjudications, expropriations, VEFA et terrains a batir."""
    return df[df["nature_mutation"] == "Vente"]


def garder_ventes_avec_logement(df: pd.DataFrame) -> pd.DataFrame:
    """Ecarte les ventes sans aucun logement (parking seul, terrain, commerce).

    Etape distincte pour que l'entonnoir separe ces ventes hors sujet des ventes a
    plusieurs logements, seul vrai cout de la methode.
    """
    avec_logement = df.loc[df["type_local"].isin(config.LOGEMENTS), "id_mutation"]
    return df[df["id_mutation"].isin(avec_logement)]


def garder_ventes_un_logement(df: pd.DataFrame) -> pd.DataFrame:
    """Garde les ventes contenant exactement un logement, et seulement la ligne de celui-ci.

    C'est le traitement des ventes multi-lots : le prix total etant repete sur chaque
    ligne d'une vente, on ne conserve qu'une ligne par vente, et seulement quand le prix
    se rapporte sans ambiguite a un seul logement (dependances comprises dans le prix).
    """
    logements = df[df["type_local"].isin(config.LOGEMENTS)]
    nb_logements = logements.groupby("id_mutation")["id_mutation"].transform("size")
    return logements[nb_logements == 1]


def ecarter_aberrations(df: pd.DataFrame) -> pd.DataFrame:
    """Ecarte les surfaces trop petites et les prix au m2 hors bornes, puis calcule prix_m2."""
    df = df[df["surface_reelle_bati"] >= config.SURFACE_MIN].copy()
    # Surface >= 9 garantie ici : la division ne peut plus produire d'infini.
    df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]
    return df[df["prix_m2"].between(config.PRIX_M2_MIN, config.PRIX_M2_MAX)]


def rattacher_metropole(df: pd.DataFrame, referentiel: pd.DataFrame) -> pd.DataFrame:
    """Ajoute la ville de rattachement, le nom de la commune et le statut centre/peripherie."""
    colonnes = ["code_commune", "nom_commune", "ville", "est_centre"]
    return df.merge(referentiel[colonnes], on="code_commune", how="inner")


def nettoyer_fichier(
    fichier: Path, referentiel: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Applique toutes les regles a un fichier. Renvoie la table propre et l'entonnoir."""
    df = charger(fichier)
    df["code_commune"] = ramener_arrondissements(df["code_commune"])

    entonnoir = {}
    etapes = [
        ("ventes touchant une metropole",
         lambda d: garder_mutations_metropoles(d, set(referentiel["code_commune"]))),
        ("nature = Vente", garder_ventes),
        ("au moins un logement", garder_ventes_avec_logement),
        # Compter les logements AVANT de filtrer les surfaces : sinon une vente de deux
        # appartements dont l'un a une surface nulle passerait pour une vente d'un seul.
        ("exactement un logement", garder_ventes_un_logement),
        ("surface et prix au m2 plausibles", ecarter_aberrations),
        ("logement situe dans une metropole", lambda d: rattacher_metropole(d, referentiel)),
    ]
    for nom, etape in etapes:
        df = etape(df)
        entonnoir[nom] = df["id_mutation"].nunique()
    return df, entonnoir


def charger_referentiel() -> pd.DataFrame:
    return pd.read_csv(
        config.FICHIER_METROPOLES,
        sep=config.SEPARATEUR_EXPORT,
        encoding=config.ENCODAGE_EXPORT,
        dtype={"code_commune": str, "code_departement": str, "code_epci": str},
    )


def main() -> None:
    referentiel = charger_referentiel()
    fichiers = sorted(config.DONNEES_BRUT.glob("dvf_*.csv.gz"))
    if not fichiers:
        raise FileNotFoundError(
            "Aucun fichier DVF : lancer d'abord python -m src.telecharger_donnees"
        )

    tables, entonnoir_total = [], {}
    for fichier in fichiers:
        table, entonnoir = nettoyer_fichier(fichier, referentiel)
        tables.append(table)
        for etape, nombre in entonnoir.items():
            entonnoir_total[etape] = entonnoir_total.get(etape, 0) + nombre
        print(f"  {fichier.name:22} {len(table):>8,} ventes retenues")

    ventes = pd.concat(tables, ignore_index=True)
    ventes["annee"] = ventes["date_mutation"].dt.year
    ventes.to_parquet(config.FICHIER_VENTES, index=False)

    # Enregistre avec les tableaux agreges : le dashboard l'affiche dans sa section methode.
    config.DONNEES_AGREGE.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"etape": list(entonnoir_total), "nb_ventes": list(entonnoir_total.values())}
    ).to_csv(
        config.DONNEES_AGREGE / "entonnoir.csv",
        sep=config.SEPARATEUR_EXPORT,
        encoding=config.ENCODAGE_EXPORT,
        index=False,
    )

    print("\nEntonnoir (nombre de ventes apres chaque etape) :")
    depart = next(iter(entonnoir_total.values()))
    for etape, nombre in entonnoir_total.items():
        print(f"  {etape:35} {nombre:>10,}  ({nombre / depart:.0%})")
    print(f"\n{len(ventes):,} ventes -> {config.FICHIER_VENTES.name}")


if __name__ == "__main__":
    main()
