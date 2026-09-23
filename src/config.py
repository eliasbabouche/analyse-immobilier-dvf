"""Chemins et parametres du projet, centralises en un seul endroit.

Aucun chemin en dur ailleurs dans le code : quand la structure bouge, une seule
ligne change ici.
"""

from pathlib import Path

# Racine du projet, deduite de l'emplacement de ce fichier (jamais un chemin absolu
# machine : le code doit tourner chez quelqu'un d'autre et dans la CI).
RACINE = Path(__file__).resolve().parent.parent

DOSSIER_DONNEES = RACINE / "donnees"
DONNEES_BRUT = DOSSIER_DONNEES / "brut"
DONNEES_TRAITE = DOSSIER_DONNEES / "traite"
DONNEES_REFERENCE = DOSSIER_DONNEES / "reference"  # petits fichiers versionnes

# Liste des communes de chaque metropole, construite depuis l'API geo.
FICHIER_METROPOLES = DONNEES_REFERENCE / "communes_metropoles.csv"

# --- Perimetre de l'analyse ---
ANNEES = [2021, 2022, 2023, 2024, 2025]

# Les dix plus grandes villes presentes dans le DVF, avec le code INSEE de la ville-centre.
# Strasbourg est absente : l'Alsace-Moselle (livre foncier) n'est pas publiee dans le DVF.
VILLES = {
    "Paris": "75056",
    "Marseille": "13055",
    "Lyon": "69123",
    "Toulouse": "31555",
    "Nice": "06088",
    "Nantes": "44109",
    "Montpellier": "34172",
    "Bordeaux": "33063",
    "Lille": "59350",
    "Rennes": "35238",
}

# --- Sources ---
# Millesime fige plutot que "latest" : les resultats restent identiques d'une execution
# a l'autre, meme apres une nouvelle publication d'Etalab.
MILLESIME_DVF = "2025-12"
URL_DVF = (
    "https://files.data.gouv.fr/geo-dvf/{millesime}/csv/{annee}/departements/{departement}.csv.gz"
)
URL_API_GEO = "https://geo.api.gouv.fr"

# --- Format des exports ---
# Ces trois parametres sont la cause la plus frequente d'un import casse en aval.
# Les fixer explicitement, ne jamais se reposer sur les valeurs par defaut de pandas.
ENCODAGE_EXPORT = "utf-8-sig"  # utf-8-sig pour qu'Excel affiche correctement les accents
SEPARATEUR_EXPORT = ";"  # convention francaise
FORMAT_DATE = "%Y-%m-%d"


def creer_dossiers() -> None:
    """Cree l'arborescence de donnees si elle n'existe pas encore."""
    for dossier in (DONNEES_BRUT, DONNEES_TRAITE, DONNEES_REFERENCE):
        dossier.mkdir(parents=True, exist_ok=True)
