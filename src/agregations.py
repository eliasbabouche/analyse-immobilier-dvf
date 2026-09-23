"""Agregations : des ventes nettoyees aux tableaux qui repondent a la question du projet.

Deux principes :
- toujours comparer a type de bien egal : le centre vend surtout des appartements, la
  peripherie beaucoup de maisons (effet de composition) ;
- mesurer l'ecart centre / peripherie par un ratio, comparable d'une ville a l'autre
  quel que soit le niveau de prix.

Usage, depuis la racine du projet (apres nettoyage) :
    python -m src.agregations
"""

import pandas as pd

from src import config


def ajouter_zone(ventes: pd.DataFrame) -> pd.DataFrame:
    ventes = ventes.copy()
    ventes["zone"] = ventes["est_centre"].map({True: "centre", False: "peripherie"})
    return ventes


def medianes(
    ventes: pd.DataFrame, par: list[str], n_min: int = config.VENTES_MIN_MEDIANE
) -> pd.DataFrame:
    """Prix median au m2 et nombre de ventes par groupe.

    Les groupes de moins de n_min ventes gardent leur nombre de ventes, mais leur
    mediane est masquee (vide) : on signale le manque de donnees au lieu de le cacher.
    """
    table = (
        ventes.groupby(par)["prix_m2"]
        .agg(prix_m2_median="median", nb_ventes="size")
        .reset_index()
    )
    table.loc[table["nb_ventes"] < n_min, "prix_m2_median"] = None
    table["prix_m2_median"] = table["prix_m2_median"].round(0)
    return table


def ecart_centre_peripherie(prix_zones: pd.DataFrame) -> pd.DataFrame:
    """Ratio prix centre / prix peripherie par ville, annee et type de bien.

    Un ratio de 1,30 signifie que le m2 coute 30 % plus cher au centre ; sous 1, la
    peripherie est plus chere (cas de Marseille avec Aix-en-Provence ou Cassis).
    """
    table = prix_zones.pivot_table(
        index=["ville", "annee", "type_local"], columns="zone", values="prix_m2_median"
    ).reset_index()
    table.columns.name = None
    table = table.rename(columns={"centre": "prix_centre", "peripherie": "prix_peripherie"})
    table["ratio"] = (table["prix_centre"] / table["prix_peripherie"]).round(3)
    return table


def evolution_ecart(ecart: pd.DataFrame, debut: int, fin: int) -> pd.DataFrame:
    """Compare le ratio entre deux annees : l'ecart se creuse-t-il ou se resserre-t-il ?

    L'ecart est la distance du ratio a 1, pour traiter pareil un centre plus cher
    (ratio > 1) et une peripherie plus chere (ratio < 1). variation_ecart > 0 : l'ecart
    se creuse ; < 0 : il se resserre.
    """
    ratios = ecart.pivot_table(index=["ville", "type_local"], columns="annee", values="ratio")
    table = pd.DataFrame(
        {"ratio_debut": ratios[debut], "ratio_fin": ratios[fin]}
    ).reset_index()
    table["variation_ecart"] = (
        (table["ratio_fin"] - 1).abs() - (table["ratio_debut"] - 1).abs()
    ).round(3)
    return table.sort_values("variation_ecart", ascending=False, ignore_index=True)


def main() -> None:
    config.creer_dossiers()
    ventes = ajouter_zone(pd.read_parquet(config.FICHIER_VENTES))
    debut, fin = config.ANNEES[0], config.ANNEES[-1]

    prix_zones = medianes(ventes, ["ville", "annee", "type_local", "zone"])
    ecart = ecart_centre_peripherie(prix_zones)
    tableaux = {
        "prix_ville_zone.csv": prix_zones,
        "ecart_centre_peripherie.csv": ecart,
        "evolution_ecart.csv": evolution_ecart(ecart, debut, fin),
        "prix_communes.csv": medianes(
            ventes,
            ["ville", "code_commune", "nom_commune", "zone", "annee", "type_local"],
        ),
    }
    for nom, table in tableaux.items():
        table.to_csv(
            config.DONNEES_AGREGE / nom,
            sep=config.SEPARATEUR_EXPORT,
            encoding=config.ENCODAGE_EXPORT,
            index=False,
        )
        print(f"  {nom:30} {len(table):>6,} lignes")

    print(f"\nEcart centre / peripherie des appartements, {debut} -> {fin} :")
    resume = tableaux["evolution_ecart.csv"]
    print(resume[resume["type_local"] == "Appartement"].to_string(index=False))


if __name__ == "__main__":
    main()
