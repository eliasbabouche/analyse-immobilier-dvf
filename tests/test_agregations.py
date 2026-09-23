"""Tests des agregations, sur des ventes fictives dont on connait les medianes."""

import pandas as pd
import pytest

from src import agregations as ag


def ventes(ville, annee, type_local, est_centre, prix_m2_liste):
    return pd.DataFrame(
        {
            "ville": ville,
            "annee": annee,
            "type_local": type_local,
            "est_centre": est_centre,
            "prix_m2": prix_m2_liste,
        }
    )


def test_mediane_resiste_a_une_valeur_extreme():
    df = ag.ajouter_zone(ventes("Nantes", 2025, "Appartement", True, [3000, 3100, 29000]))
    table = ag.medianes(df, ["ville", "zone"], n_min=1)
    assert table["prix_m2_median"].iloc[0] == 3100
    assert table["nb_ventes"].iloc[0] == 3


def test_mediane_masquee_sous_le_seuil_mais_effectif_conserve():
    df = ag.ajouter_zone(ventes("Nantes", 2025, "Maison", False, [2500, 2600]))
    table = ag.medianes(df, ["ville", "zone"], n_min=30)
    assert pd.isna(table["prix_m2_median"].iloc[0])
    assert table["nb_ventes"].iloc[0] == 2


def test_types_de_biens_jamais_melanges():
    # Effet de composition : les maisons du centre ne doivent pas tirer la mediane
    # des appartements.
    df = ag.ajouter_zone(
        pd.concat(
            [
                ventes("Nantes", 2025, "Appartement", True, [4000, 4000, 4000]),
                ventes("Nantes", 2025, "Maison", True, [6000]),
            ]
        )
    )
    table = ag.medianes(df, ["ville", "type_local"], n_min=1).set_index("type_local")
    assert table.loc["Appartement", "prix_m2_median"] == 4000


def _prix_zones(prix_centre, prix_peripherie, annee=2025, ville="Nantes"):
    return pd.DataFrame(
        {
            "ville": ville,
            "annee": annee,
            "type_local": "Appartement",
            "zone": ["centre", "peripherie"],
            "prix_m2_median": [prix_centre, prix_peripherie],
        }
    )


def test_ratio_centre_sur_peripherie():
    ecart = ag.ecart_centre_peripherie(_prix_zones(3900, 3000))
    assert ecart["ratio"].iloc[0] == pytest.approx(1.3)


def test_ecart_se_resserre_quand_le_ratio_se_rapproche_de_1():
    ecart = ag.ecart_centre_peripherie(
        pd.concat([_prix_zones(3900, 3000, 2021), _prix_zones(3300, 3000, 2025)])
    )
    evolution = ag.evolution_ecart(ecart, 2021, 2025)
    assert evolution["variation_ecart"].iloc[0] == pytest.approx(-0.2)


def test_peripherie_plus_chere_traitee_comme_un_ecart():
    # Marseille : ratio 0,83 -> 0,87. Le ratio monte, mais l'ecart se RESSERRE.
    ecart = ag.ecart_centre_peripherie(
        pd.concat([_prix_zones(830, 1000, 2021), _prix_zones(870, 1000, 2025)])
    )
    evolution = ag.evolution_ecart(ecart, 2021, 2025)
    assert evolution["variation_ecart"].iloc[0] == pytest.approx(-0.04)
