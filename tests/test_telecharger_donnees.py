"""Tests du telechargement, sans aucun acces reseau.

requests.get est remplace par une fausse fonction (monkeypatch) : un test qui depend
d'Internet echoue au hasard dans la CI et ne teste pas notre code, mais le serveur.
"""

import pandas as pd
import pytest

from src import telecharger_donnees as td


class FausseReponse:
    """Imite une reponse de requests, avec un contenu choisi par le test."""

    def __init__(self, blocs):
        self.blocs = blocs

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        for bloc in self.blocs:
            if isinstance(bloc, Exception):
                raise bloc
            yield bloc

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_url_dvf_pointe_vers_le_millesime_fige():
    url = td.url_dvf(2023, "06")
    assert url.endswith("/geo-dvf/2025-12/csv/2023/departements/06.csv.gz")


def test_departements_deduits_du_referentiel_sans_doublon():
    referentiel = pd.DataFrame({"code_departement": ["75", "92", "75", "13", "84"]})
    assert td.departements_a_telecharger(referentiel) == ["13", "75", "84", "92"]


def test_telechargement_ecrit_le_fichier(tmp_path, monkeypatch):
    monkeypatch.setattr(td.requests, "get", lambda *a, **k: FausseReponse([b"abc", b"def"]))
    destination = tmp_path / "dvf.csv.gz"

    assert td.telecharger("http://exemple", destination) is True
    assert destination.read_bytes() == b"abcdef"


def test_fichier_deja_present_non_retelecharge(tmp_path, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("requests.get ne doit pas etre appele")

    monkeypatch.setattr(td.requests, "get", interdit)
    destination = tmp_path / "dvf.csv.gz"
    destination.write_bytes(b"deja la")

    assert td.telecharger("http://exemple", destination) is False


def test_coupure_reseau_ne_laisse_aucun_fichier(tmp_path, monkeypatch):
    coupure = ConnectionError("coupure au milieu du telechargement")
    monkeypatch.setattr(td.requests, "get", lambda *a, **k: FausseReponse([b"abc", coupure]))
    destination = tmp_path / "dvf.csv.gz"

    with pytest.raises(ConnectionError):
        td.telecharger("http://exemple", destination)

    # Ni le fichier final, ni le temporaire : le prochain lancement reprendra proprement.
    assert list(tmp_path.iterdir()) == []


def test_fichier_vide_refuse(tmp_path, monkeypatch):
    monkeypatch.setattr(td.requests, "get", lambda *a, **k: FausseReponse([]))
    destination = tmp_path / "dvf.csv.gz"

    with pytest.raises(ValueError):
        td.telecharger("http://exemple", destination)
    assert not destination.exists()
