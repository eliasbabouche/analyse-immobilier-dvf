"""Tests des graphiques et de l'application."""

import pandas as pd
from streamlit.testing.v1 import AppTest

from src import graphiques as g


def _evolution():
    return pd.DataFrame(
        {
            "ville": ["Nantes", "Lille", "Lyon"],
            "type_local": "Appartement",
            "ratio_debut": [1.30, 1.42, 1.46],
            "ratio_fin": [1.13, 1.43, 1.34],
            "variation_ecart": [-0.17, 0.01, -0.12],
        }
    )


def _prix_communes():
    lignes = []
    for annee, prix_centre, prix_reze, nb_reze in [(2021, 4000, 3000, 50), (2025, 3600, 3300, 10)]:
        lignes += [
            ("Nantes", "44109", "Nantes", "centre", annee, "Appartement", prix_centre, 900),
            ("Nantes", "44143", "Rezé", "peripherie", annee, "Appartement",
             prix_reze if nb_reze >= 30 else None, nb_reze),
        ]
    colonnes = ["ville", "code_commune", "nom_commune", "zone", "annee", "type_local",
                "prix_m2_median", "nb_ventes"]
    return pd.DataFrame(lignes, columns=colonnes)


def test_resume_compte_les_villes_ou_l_ecart_se_resserre():
    resume = g.resume_reponse(_evolution(), "Appartement")
    assert resume["nb_villes"] == 3
    assert resume["nb_resserrement"] == 2
    assert resume["ville_plus_fort_resserrement"] == "Nantes"


def test_evolution_des_communes_en_pourcentage():
    communes = g.evolution_communes(_prix_communes(), "Nantes", "Appartement", 2021, 2025)
    nantes = communes.set_index("nom_commune").loc["Nantes"]
    assert nantes["evolution_pct"] == -10.0


def test_commune_sans_donnees_suffisantes_reste_listee_sans_evolution():
    # Rezé : 10 ventes en 2025, mediane masquee -> evolution vide, mais commune presente.
    communes = g.evolution_communes(_prix_communes(), "Nantes", "Appartement", 2021, 2025)
    reze = communes.set_index("nom_commune").loc["Rezé"]
    assert pd.isna(reze["evolution_pct"])
    assert reze["nb_ventes_fin"] == 10


def test_barres_rouges_si_l_ecart_se_creuse_bleues_sinon():
    fig = g.barres_variation_ecart(_evolution(), "Appartement")
    barres = dict(zip(fig.data[0].y, fig.data[0].marker.color))
    assert barres["Lille"] == g.ROUGE
    assert barres["Nantes"] == g.BLEU


def test_ville_choisie_dessinee_en_dernier_et_en_couleur():
    ecart = pd.DataFrame(
        {
            "ville": ["Nantes", "Nantes", "Lyon", "Lyon"],
            "annee": [2021, 2025, 2021, 2025],
            "type_local": "Appartement",
            "ratio": [1.30, 1.13, 1.46, 1.34],
        }
    )
    fig = g.courbes_ratio(ecart, "Nantes", "Appartement")
    assert fig.data[-1].name == "Nantes"
    assert fig.data[-1].line.color == g.BLEU
    assert fig.data[0].line.color == g.GRIS_CONTEXTE


def test_l_application_s_affiche_sans_erreur():
    # Lance app.py pour de vrai, sur les tableaux agreges versionnes.
    app = AppTest.from_file("../app.py", default_timeout=60).run()
    assert not app.exception
    assert "resserré" in app.subheader[0].value


def test_variation_lisible_sans_moins_zero():
    assert g.variation_lisible(-0.003) == "0,00"
    assert g.variation_lisible(-0.165) == "-0,17"
    assert g.variation_lisible(0.012) == "+0,01"
