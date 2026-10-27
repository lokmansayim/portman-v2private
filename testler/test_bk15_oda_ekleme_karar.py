"""BK-15 · çelik katalog modelinde oda ekleme isteğinin gerekçesi (O4). LLM oda varyantı işaretlemese de "Bir yatak odası daha ekleyelim"
bayiye "Pencere ekleme …" diye yönlenmez; oda eklemeyi söyler. Pencere eklemesinin mesajı aynı kalır. LLM yok, Postgres yok, çizim yok
(`test_celik_revizyon_karar.py`'nin sohbet düzeni)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from beyin import karar as K  # noqa: E402
from testler.test_celik_revizyon_karar import Sohbet, r01_k  # noqa: E402

PENCERE_MESAJI = "Pencere ekleme ya da kaldırma çelik modelde otomatik yapılamıyor; mevcut pencerenin ölçüsünü değiştirebilirim. " + K.YONLENDIRME


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path)


@pytest.mark.parametrize("metin", ["Bir yatak odası daha ekleyelim", "Mutfağın yanına bir oda daha ekleyelim", "Ebeveyn banyosu ekleyelim",
                                   "Yatak odasını kaldıralım"])
def test_oda_ekleme_dogru_gerekceyle_yonlenir(s, metin):
    r01_k(s)
    k = s.yaz(metin)
    assert k.eylem == "yonlendir"
    assert k.mesaj == "Oda ekleme ya da kaldırma çelik modelde otomatik yapılamıyor. " + K.YONLENDIRME
    assert k.gerekce == "çelik katalog modelinde oda ekleme/kaldırma otomatik yapılamıyor"
    assert metin not in k.gerekce and "Pencere" not in k.mesaj


@pytest.mark.parametrize("metin", ["Mutfağa bir pencere daha ekleyelim", "Salondaki pencereyi kaldıralım"])
def test_pencere_eklemesinin_mesaji_ayni(s, metin):
    r01_k(s)
    k = s.yaz(metin)
    assert k.eylem == "yonlendir" and k.mesaj == PENCERE_MESAJI
    assert k.gerekce == "çelikte pencere ekleme/kaldırma otomatik yapılamıyor (8a: yalnız ölçü)"


def test_oda_ve_pencere_birlikte(s):
    r01_k(s)
    k = s.yaz("Bir yatak odası daha ekleyelim. Salona bir pencere daha ekleyelim.")
    assert k.eylem == "yonlendir"
    assert k.mesaj == "Oda ekleme ya da kaldırma ve pencere ekleme ya da kaldırma çelik modelde otomatik yapılamıyor. " + K.YONLENDIRME
    assert k.gerekce == "çelik katalog modelinde oda ekleme/kaldırma otomatik yapılamıyor (pencere ekleme/kaldırma da: 8a yalnız ölçü)"
