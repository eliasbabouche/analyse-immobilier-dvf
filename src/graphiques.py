"""Graphiques du dashboard : chaque fonction recoit un tableau agrege et renvoie une figure.

Aucune mise en page Streamlit ici (voir app.py) : ces fonctions restent testables sans
lancer l'application.

Regles de lisibilite suivies partout :
- une couleur a toujours le meme sens : bleu = centre, orange = peripherie ;
- jamais dix couleurs a la fois : la ville choisie en couleur, les autres en gris ;
- jamais deux axes verticaux sur un meme graphique.
"""

import math

import pandas as pd
import plotly.graph_objects as go

BLEU = "#2a78d6"  # centre, ou baisse / resserrement
ORANGE = "#eb6834"  # peripherie
ROUGE = "#e34948"  # hausse / ecart qui se creuse
GRIS_NEUTRE = "#f0efec"  # milieu de l'echelle divergente
GRIS_CONTEXTE = "#c3c2b7"  # villes non selectionnees
GRIS_ABSENT = "#e4e3df"  # communes sans donnees suffisantes
TEXTE_SECONDAIRE = "#52514e"
BLEUS = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

COULEUR_ZONE = {"centre": BLEU, "peripherie": ORANGE}
NOM_ZONE = {"centre": "Ville-centre", "peripherie": "Périphérie"}


def variation_lisible(valeur: float) -> str:
    """Variation signee a deux decimales, virgule francaise : +0,01 / -0,17 / 0,00.

    Sans le cas particulier, -0,003 s'afficherait "-0,00".
    """
    texte = f"{valeur:+.2f}"
    if float(texte) == 0:
        texte = "0.00"
    return texte.replace(".", ",")


def _mise_en_forme(fig: go.Figure, titre: str, hauteur: int = 380) -> go.Figure:
    fig.update_layout(
        title={"text": titre, "font": {"size": 16}},
        height=hauteur,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        separators=", ",  # notation francaise : virgule decimale, espace des milliers
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"bgcolor": "white"},
        legend={"orientation": "h", "y": -0.15},
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)")
    return fig


# --- Donnees preparees pour l'affichage ---------------------------------------------------


def resume_reponse(evolution: pd.DataFrame, type_local: str) -> dict:
    """Les chiffres de la reponse : combien de villes voient l'ecart se resserrer."""
    lignes = evolution[evolution["type_local"] == type_local].dropna(subset=["variation_ecart"])
    plus_fort = lignes.loc[lignes["variation_ecart"].idxmin()]
    return {
        "nb_villes": len(lignes),
        "nb_resserrement": int((lignes["variation_ecart"] < 0).sum()),
        "ville_plus_fort_resserrement": plus_fort["ville"],
        "variation_plus_forte": plus_fort["variation_ecart"],
    }


def evolution_communes(
    prix_communes: pd.DataFrame, ville: str, type_local: str, debut: int, fin: int
) -> pd.DataFrame:
    """Une ligne par commune de la metropole : prix de debut et de fin, evolution en %.

    Une mediane masquee (moins de 30 ventes) a l'une des deux dates donne une evolution
    vide : la commune reste listee, marquee comme sans donnees suffisantes.
    """
    lignes = prix_communes[
        (prix_communes["ville"] == ville) & (prix_communes["type_local"] == type_local)
    ]
    # pivot (et non pivot_table) : simple reorganisation, une valeur par commune et par
    # annee, sans agregation qui ecarterait les medianes masquees.
    table = lignes.pivot(
        index=["code_commune", "nom_commune", "zone"],
        columns="annee",
        values=["prix_m2_median", "nb_ventes"],
    )
    resultat = pd.DataFrame(
        {
            "prix_debut": table[("prix_m2_median", debut)],
            "prix_fin": table[("prix_m2_median", fin)],
            "nb_ventes_fin": table[("nb_ventes", fin)],
        }
    ).reset_index()
    resultat["evolution_pct"] = (
        (resultat["prix_fin"] / resultat["prix_debut"] - 1) * 100
    ).round(1)
    return resultat.sort_values("prix_fin", ascending=False, ignore_index=True)


# --- Figures --------------------------------------------------------------------------------


def barres_variation_ecart(evolution: pd.DataFrame, type_local: str) -> go.Figure:
    """Une barre par ville : l'ecart centre / peripherie s'est-il creuse ou resserre ?"""
    lignes = evolution[evolution["type_local"] == type_local].sort_values("variation_ecart")
    couleurs = [ROUGE if v > 0 else BLEU for v in lignes["variation_ecart"]]
    fig = go.Figure(
        go.Bar(
            x=lignes["variation_ecart"],
            y=lignes["ville"],
            orientation="h",
            marker={"color": couleurs, "cornerradius": 4},
            text=[variation_lisible(v) for v in lignes["variation_ecart"]],
            textposition="outside",
            customdata=lignes[["ratio_debut", "ratio_fin"]],
            hovertemplate=(
                "<b>%{y}</b><br>Ratio centre / périphérie : %{customdata[0]:.2f} → "
                "%{customdata[1]:.2f}<extra></extra>"
            ),
        )
    )
    fig.add_vline(x=0, line_width=1, line_color=TEXTE_SECONDAIRE)
    fig.update_xaxes(title="Variation de l'écart (en points de ratio)", zeroline=False)
    fig.update_yaxes(showgrid=False)
    fig.update_layout(bargap=0.35)
    return _mise_en_forme(
        fig, "L'écart centre / périphérie entre 2021 et 2025", hauteur=420
    )


def courbes_prix_zones(prix_zones: pd.DataFrame, ville: str, type_local: str) -> go.Figure:
    """Prix median au m2 du centre et de la peripherie, annee par annee."""
    fig = go.Figure()
    lignes = prix_zones[(prix_zones["ville"] == ville) & (prix_zones["type_local"] == type_local)]
    for zone, groupe in lignes.groupby("zone"):
        groupe = groupe.sort_values("annee")
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["prix_m2_median"],
                name=NOM_ZONE[zone],
                mode="lines+markers",
                line={"color": COULEUR_ZONE[zone], "width": 2},
                marker={"size": 8},
                customdata=groupe["nb_ventes"],
                hovertemplate=(
                    f"<b>{NOM_ZONE[zone]}</b> %{{x}}<br>%{{y:,.0f}} €/m²"
                    "<br>%{customdata:,} ventes<extra></extra>"
                ),
            )
        )
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title="Prix médian (€/m²)", rangemode="tozero")
    return _mise_en_forme(fig, f"{ville} : prix médian au m²")


def courbes_ratio(ecart: pd.DataFrame, ville: str, type_local: str) -> go.Figure:
    """Ratio centre / peripherie de la ville choisie, les autres villes en gris."""
    fig = go.Figure()
    lignes = ecart[ecart["type_local"] == type_local]
    # Les autres villes d'abord, pour que la ville choisie soit dessinee par-dessus.
    for nom, groupe in sorted(lignes.groupby("ville"), key=lambda paire: paire[0] == ville):
        choisie = nom == ville
        groupe = groupe.sort_values("annee")
        fig.add_trace(
            go.Scatter(
                x=groupe["annee"],
                y=groupe["ratio"],
                name=nom,
                mode="lines+markers" if choisie else "lines",
                line={"color": BLEU if choisie else GRIS_CONTEXTE, "width": 3 if choisie else 1},
                marker={"size": 8},
                showlegend=False,
                hovertemplate=f"<b>{nom}</b> %{{x}}<br>ratio %{{y:.2f}}<extra></extra>",
            )
        )
    derniere = lignes[(lignes["ville"] == ville)].sort_values("annee").iloc[-1]
    fig.add_annotation(
        x=derniere["annee"], y=derniere["ratio"], text=f"<b>{ville}</b>",
        xanchor="left", xshift=8, showarrow=False, font={"color": BLEU},
    )
    fig.add_hline(
        y=1, line_dash="dot", line_color=TEXTE_SECONDAIRE,
        annotation_text="centre = périphérie", annotation_position="bottom right",
    )
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title="Prix centre / prix périphérie")
    return _mise_en_forme(fig, "Ratio centre / périphérie, face aux 9 autres villes")


def _cadrage(contours: dict) -> tuple[dict, float]:
    """Centre et niveau de zoom qui englobent toutes les communes affichees."""
    lons, lats = [], []

    def parcourir(coordonnees):
        if isinstance(coordonnees[0], (int, float)):
            lons.append(coordonnees[0])
            lats.append(coordonnees[1])
        else:
            for element in coordonnees:
                parcourir(element)

    for commune in contours["features"]:
        parcourir(commune["geometry"]["coordinates"])
    centre = {"lon": (min(lons) + max(lons)) / 2, "lat": (min(lats) + max(lats)) / 2}
    # Au zoom z, le monde entier (360 degres) mesure 512 x 2^z pixels. On cherche le zoom
    # qui fait tenir la metropole dans un cadre d'environ 900 x 480 pixels. En latitude,
    # la projection etire les distances d'un facteur 1 / cos(latitude).
    etirement = 1 / math.cos(math.radians(centre["lat"]))
    zoom_largeur = math.log2(900 * 360 / (512 * (max(lons) - min(lons))))
    zoom_hauteur = math.log2(480 * 360 / (512 * (max(lats) - min(lats)) * etirement))
    return centre, min(zoom_largeur, zoom_hauteur) - 0.2


def carte_communes(communes: pd.DataFrame, contours: dict, indicateur: str) -> go.Figure:
    """Carte des communes d'une metropole.

    indicateur = "evolution" : evolution du prix 2021 -> 2025, echelle divergente centree
    sur 0 (bleu = baisse, rouge = hausse).
    indicateur = "prix" : prix au m2 de la derniere annee, echelle d'une seule teinte.
    Les communes sans donnees suffisantes restent dessinees en gris.
    """
    codes = set(communes["code_commune"])
    contours = {
        "type": "FeatureCollection",
        "features": [c for c in contours["features"] if c["properties"]["code"] in codes],
    }
    colonne = "evolution_pct" if indicateur == "evolution" else "prix_fin"
    avec_valeur = communes.dropna(subset=[colonne])
    sans_valeur = communes[communes[colonne].isna()]

    if indicateur == "evolution":
        borne = max(avec_valeur[colonne].abs().max(), 1)
        echelle = {
            "colorscale": [[0, BLEU], [0.5, GRIS_NEUTRE], [1, ROUGE]],
            "zmin": -borne, "zmax": borne,
            "colorbar": {"title": "Évolution", "ticksuffix": " %"},
        }
        survol = "%{customdata[0]}<br><b>%{z:+.1f} %</b><extra></extra>"
    else:
        echelle = {
            "colorscale": [[i / (len(BLEUS) - 1), c] for i, c in enumerate(BLEUS)],
            "colorbar": {"title": "€/m²"},
        }
        survol = "%{customdata[0]}<br><b>%{z:,.0f} €/m²</b><extra></extra>"

    fig = go.Figure()
    fig.add_trace(
        go.Choroplethmap(
            geojson=contours, featureidkey="properties.code",
            locations=sans_valeur["code_commune"], z=[0] * len(sans_valeur),
            colorscale=[[0, GRIS_ABSENT], [1, GRIS_ABSENT]], showscale=False,
            customdata=sans_valeur[["nom_commune"]],
            hovertemplate="%{customdata[0]}<br>données insuffisantes<extra></extra>",
            marker={"line": {"width": 0.5, "color": "white"}},
        )
    )
    fig.add_trace(
        go.Choroplethmap(
            geojson=contours, featureidkey="properties.code",
            locations=avec_valeur["code_commune"], z=avec_valeur[colonne],
            customdata=avec_valeur[["nom_commune"]], hovertemplate=survol,
            marker={"line": {"width": 0.5, "color": "white"}, "opacity": 0.85},
            **echelle,
        )
    )
    centre, zoom = _cadrage(contours)
    fig.update_layout(map={"style": "carto-positron", "center": centre, "zoom": zoom})
    return _mise_en_forme(fig, "", hauteur=520)
