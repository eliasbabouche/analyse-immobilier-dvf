"""Tests du nettoyage, sur de petites ventes fabriquees a la main.

Chaque vente de test illustre un cas precis : on sait d'avance si elle doit etre
gardee ou ecartee, et pourquoi.
"""

import pandas as pd

from src import nettoyage as n

NANTES, REZE, HORS_METROPOLE = "44109", "44143", "44184"


def ligne(id_mutation, type_local, surface, prix=200_000, nature="Vente", commune=NANTES):
    return {
        "id_mutation": id_mutation,
        "date_mutation": "2024-06-01",
        "nature_mutation": nature,
        "valeur_fonciere": prix,
        "code_commune": commune,
        "type_local": type_local,
        "surface_reelle_bati": surface,
        "nombre_pieces_principales": 2,
    }


REFERENTIEL = pd.DataFrame(
    {
        "code_commune": [NANTES, REZE],
        "nom_commune": ["Nantes", "Rezé"],
        "ville": ["Nantes", "Nantes"],
        "est_centre": [True, False],
    }
)


def test_arrondissements_ramenes_a_leur_commune():
    codes = pd.Series(["75108", "75120", "69383", "13205", "44109", "13001"])
    attendu = ["75056", "75056", "69123", "13055", "44109", "13001"]
    assert n.ramener_arrondissements(codes).tolist() == attendu


def test_vente_multi_lots_prix_compte_une_seule_fois():
    # Un appartement vendu avec sa cave : deux lignes, le prix repete sur chacune.
    df = pd.DataFrame([ligne("A", "Appartement", 50), ligne("A", "Dépendance", None)])
    resultat = n.garder_ventes_un_logement(df)
    assert len(resultat) == 1
    assert resultat["valeur_fonciere"].sum() == 200_000  # et non 400 000


def test_vente_de_deux_logements_ecartee():
    # Prix global de deux appartements : impossible a repartir entre eux.
    df = pd.DataFrame([ligne("B", "Appartement", 50), ligne("B", "Appartement", 60)])
    assert n.garder_ventes_un_logement(df).empty


def test_piege_ordre_surface_nulle_ne_fait_pas_passer_la_vente():
    # Deux appartements, dont un sans surface. Si l'on filtrait les surfaces d'abord,
    # il ne resterait qu'un appartement visible, garde a tort avec le prix des deux.
    df = pd.DataFrame([ligne("C", "Appartement", 50), ligne("C", "Appartement", 0)])
    resultat = n.ecarter_aberrations(n.garder_ventes_un_logement(df))
    assert resultat.empty


def test_seules_les_ventes_classiques_sont_gardees():
    df = pd.DataFrame(
        [
            ligne("D", "Maison", 100, nature="Vente"),
            ligne("E", "Maison", 100, nature="Echange"),
            ligne("F", "Appartement", 50, nature="Vente en l'état futur d'achèvement"),
        ]
    )
    assert n.garder_ventes(df)["id_mutation"].tolist() == ["D"]


def test_bornes_des_aberrations():
    df = pd.DataFrame(
        [
            ligne("ok", "Appartement", 50, prix=200_000),  # 4 000 EUR/m2
            ligne("petit", "Appartement", 8, prix=40_000),  # surface < 9 m2
            ligne("donation", "Maison", 100, prix=1),  # 0,01 EUR/m2
            ligne("luxe", "Maison", 100, prix=3_100_000),  # 31 000 EUR/m2
            ligne("borne_basse", "Maison", 100, prix=50_000),  # 500 EUR/m2 : inclus
            ligne("borne_haute", "Maison", 100, prix=3_000_000),  # 30 000 EUR/m2 : inclus
        ]
    )
    resultat = n.ecarter_aberrations(df)
    assert sorted(resultat["id_mutation"]) == ["borne_basse", "borne_haute", "ok"]
    assert (resultat.loc[resultat["id_mutation"] == "ok", "prix_m2"] == 4_000).all()


def test_vente_a_cheval_sur_la_limite_de_la_metropole_reste_entiere():
    # Deux appartements, l'un dans la metropole, l'autre dehors : la vente entiere doit
    # etre conservee a ce stade pour que le comptage des logements la voie comme double.
    df = pd.DataFrame(
        [
            ligne("G", "Appartement", 50, commune=NANTES),
            ligne("G", "Appartement", 50, commune=HORS_METROPOLE),
            ligne("H", "Maison", 100, commune=HORS_METROPOLE),
        ]
    )
    gardees = n.garder_mutations_metropoles(df, set(REFERENTIEL["code_commune"]))
    assert gardees["id_mutation"].tolist() == ["G", "G"]
    assert n.garder_ventes_un_logement(gardees).empty


def test_rattachement_centre_et_peripherie():
    df = pd.DataFrame([ligne("I", "Maison", 100, commune=NANTES),
                       ligne("J", "Maison", 100, commune=REZE)])
    resultat = n.rattacher_metropole(df, REFERENTIEL).set_index("id_mutation")
    assert resultat.loc["I", "est_centre"]
    assert not resultat.loc["J", "est_centre"]
    assert resultat.loc["J", "ville"] == "Nantes"


def test_chaine_complete_sur_un_fichier(tmp_path):
    df = pd.DataFrame(
        [
            ligne("A", "Appartement", 50),
            ligne("A", "Dépendance", None),  # multi-lots : garde, une seule fois
            ligne("B", "Appartement", 50),
            ligne("B", "Appartement", 60),  # deux logements : ecarte
            ligne("C", "Appartement", 50),
            ligne("C", "Appartement", 0),  # piege d'ordre : doit etre ecarte
            ligne("E", "Maison", 100, nature="Echange"),  # echange : ecarte
            ligne("K", "Maison", 100, commune="75108"),  # hors metropole de Nantes
            ligne("P", "Dépendance", None),  # parking seul : aucun logement
        ]
    )
    fichier = tmp_path / "dvf_2024_44.csv.gz"
    df.to_csv(fichier, index=False)

    table, entonnoir = n.nettoyer_fichier(fichier, REFERENTIEL)

    assert table["id_mutation"].tolist() == ["A"]
    assert table["prix_m2"].iloc[0] == 4_000
    # metropole (A B C E P), Vente (A B C P), avec logement (A B C), un seul (A), ...
    assert list(entonnoir.values()) == [5, 4, 3, 1, 1, 1]
