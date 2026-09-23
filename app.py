"""Dashboard Streamlit : le centre et la peripherie des grandes villes se rapprochent-ils ?

Ne lit que les petits tableaux de donnees/agrege/ et les contours de donnees/reference/,
tous versionnes : l'application deployee n'a rien a telecharger ni a recalculer.

Lancement, depuis la racine du projet :
    streamlit run app.py
"""

import json

import pandas as pd
import streamlit as st

from src import config
from src import graphiques as g

DEBUT, FIN = config.ANNEES[0], config.ANNEES[-1]
TYPES = {"Appartements": "Appartement", "Maisons": "Maison"}


@st.cache_data
def charger_tableaux() -> dict[str, pd.DataFrame]:
    """Lu une seule fois, puis garde en memoire entre deux clics (cache Streamlit)."""
    options = {
        "sep": config.SEPARATEUR_EXPORT,
        "encoding": config.ENCODAGE_EXPORT,
        "dtype": {"code_commune": str},
    }
    noms = ["prix_ville_zone", "ecart_centre_peripherie", "evolution_ecart",
            "prix_communes", "entonnoir"]
    return {nom: pd.read_csv(config.DONNEES_AGREGE / f"{nom}.csv", **options) for nom in noms}


@st.cache_data
def charger_contours() -> dict:
    with open(config.FICHIER_CONTOURS, encoding="utf-8") as fichier:
        return json.load(fichier)


st.set_page_config(page_title="Immobilier : centre et périphérie", page_icon="🏠", layout="wide")
tableaux = charger_tableaux()

st.title("Le centre et la périphérie des grandes villes se rapprochent-ils ?")
st.caption(
    f"Prix de l'immobilier ancien dans les 10 plus grandes villes présentes dans les données "
    f"DVF, {DEBUT}–{FIN}. Chaque ville-centre est comparée aux autres communes de sa métropole."
)
choix_type = st.radio("Type de bien", list(TYPES), horizontal=True)
type_local = TYPES[choix_type]

# --- 1. La reponse -------------------------------------------------------------------------
resume = g.resume_reponse(tableaux["evolution_ecart"], type_local)
variation = g.variation_lisible(resume["variation_plus_forte"])
st.subheader(
    f"L'écart s'est resserré dans {resume['nb_resserrement']} villes "
    f"sur {resume['nb_villes']}"
)
st.markdown(
    f"Plus fort resserrement : **{resume['ville_plus_fort_resserrement']}** "
    f"({variation} point de ratio). "
    "Le ratio compare le prix médian au m² du centre à celui de la périphérie : "
    "1,30 signifie un centre 30 % plus cher."
)
st.plotly_chart(g.barres_variation_ecart(tableaux["evolution_ecart"], type_local))

# --- 2. Zoom sur une ville -----------------------------------------------------------------
st.divider()
villes = list(config.VILLES)
ville = st.selectbox(
    "Zoom sur une ville", villes, index=villes.index(resume["ville_plus_fort_resserrement"])
)
gauche, droite = st.columns(2)
gauche.plotly_chart(g.courbes_prix_zones(tableaux["prix_ville_zone"], ville, type_local))
droite.plotly_chart(g.courbes_ratio(tableaux["ecart_centre_peripherie"], ville, type_local))

communes = g.evolution_communes(tableaux["prix_communes"], ville, type_local, DEBUT, FIN)
indicateur = st.radio(
    "Carte des communes",
    ["evolution", "prix"],
    format_func={"evolution": f"Évolution du prix {DEBUT} → {FIN}",
                 "prix": f"Prix au m² en {FIN}"}.get,
    horizontal=True,
)
st.plotly_chart(g.carte_communes(communes, charger_contours(), indicateur))
st.caption(
    f"En gris : moins de {config.VENTES_MIN_MEDIANE} ventes sur l'une des deux années, "
    "médiane trop instable pour être affichée."
)

# --- 3. Detail par commune -----------------------------------------------------------------
with st.expander(f"Détail des {len(communes)} communes de la métropole"):
    st.dataframe(
        communes.drop(columns="code_commune").replace({"zone": g.NOM_ZONE}),
        hide_index=True,
        column_config={
            "nom_commune": "Commune",
            "zone": "Zone",
            "prix_debut": st.column_config.NumberColumn(f"Prix {DEBUT} (€/m²)", format="%d"),
            "prix_fin": st.column_config.NumberColumn(f"Prix {FIN} (€/m²)", format="%d"),
            "nb_ventes_fin": st.column_config.NumberColumn(f"Ventes {FIN}", format="%d"),
            "evolution_pct": st.column_config.NumberColumn("Évolution (%)", format="%+.1f"),
        },
    )

# --- 4. Methode ----------------------------------------------------------------------------
with st.expander("Méthode et limites"):
    entonnoir = tableaux["entonnoir"]
    depart = entonnoir["nb_ventes"].iloc[0]
    entonnoir["part"] = (entonnoir["nb_ventes"] / depart * 100).round(0).astype(int)
    st.markdown(
        "**Du fichier brut à l'analyse**, nombre de ventes restantes après chaque étape "
        "(toutes années confondues) :"
    )
    st.dataframe(
        entonnoir,
        hide_index=True,
        column_config={
            "etape": "Étape",
            "nb_ventes": st.column_config.NumberColumn("Ventes", format="%d"),
            "part": st.column_config.NumberColumn("Part restante", format="%d %%"),
        },
    )
    st.markdown(
        "- **Ventes multi-lots** : une vente de plusieurs biens apparaît sur plusieurs lignes, "
        "avec le prix total répété. On ne garde que les ventes d'un seul logement.\n"
        "- **Médiane** plutôt que moyenne : insensible aux valeurs extrêmes.\n"
        "- **Appartements et maisons jamais mélangés** : le centre vend surtout des "
        "appartements, la périphérie beaucoup de maisons.\n"
        "- Sources : DVF géolocalisées (DGFiP, Etalab), référentiel des communes (INSEE, "
        "API geo.api.gouv.fr).\n\n"
        "Méthode complète et limites : "
        "[README du projet](https://github.com/eliasbabouche/analyse-immobilier-dvf)."
    )
