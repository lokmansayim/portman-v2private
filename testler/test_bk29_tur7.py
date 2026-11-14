"""BK-29 tur 7 · canlı bulgu (14–15 Kasım 2026): İş Emri'nin `talep.musteri_adi` alanı bazen bayinin adıyla doluyordu.

LLM bağlamında "bayinin adı/hitabı" yazar (D-06, `worker.bayi_tanimi`). LLM bunu bazı çıkarımlarda `musteri.ad`'a yazdı; bayinin adı
PDF başlığına (prefabrik) ve antetin proje adına (çelik) çıktı. Müşteri adı bayinin kendi mesajından okunur (K18): LLM'in verdiği ad
bayinin kartındaki adın ya da hitabın sözcüklerinden oluşuyorsa ve bu mesajda yazmıyorsa alınmaz. Müşteri adı görünür kalır (D-33).
LLM yok, Postgres yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür; bayi adları uydurmadır.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import karar as K  # noqa: E402
from beyin.katalog import Katalog  # noqa: E402
from beyin.konusma import Konusma  # noqa: E402
from beyin.sema import Talep  # noqa: E402
from test_celik_revizyon_karar import pen  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402

BAYI = {"kod": "B07", "ad": "Deniz Örnek", "hitap": "Deniz Bey", "rol": "bayi", "numara": "900000000107"}


class Sohbet:
    def __init__(self, kok: Path, bayi=BAYI):
        self.k = Konusma(bayi["numara"], kok=kok)
        self.kat = Katalog(kabul_edilmis=KABUL)
        self.bayi = bayi

    def yaz(self, metin: str, **alan):
        alan.setdefault("niyet", "revizyon" if self.k.d.get("son_is_emri") else "yeni_talep")
        t = Talep(guven="yuksek", ozet=alan.pop("ozet", metin[:80]), **alan)
        return K.karar_ver(t, self.k, self.bayi, self.kat, metin)


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path)


def _ad(k) -> str:
    assert k.eylem == "is_emri", k.mesaj
    return k.is_emri["talep"]["musteri_adi"]


# ── prefabrik: ilk plan ve revizyon ─────────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("llm_adi", ["Deniz", "Deniz Örnek", "Deniz Bey", "deniz örnek", "Sayın Deniz Örnek"])
def test_baglamdan_gelen_bayi_adi_musteri_adi_olmaz(s, llm_adi):
    k = s.yaz("PA-04", katalog_kodu="PA04", musteri={"ad": llm_adi})
    assert _ad(k) == ""
    assert "musteri" not in s.k.d["taslak"] or not (s.k.d["taslak"]["musteri"] or {}).get("ad")


def test_revizyonda_da_bayi_adi_yazilmaz(s):
    """Canlı: PA-04 r01'de alan boştu, r02'de bayinin adıyla doldu."""
    assert _ad(s.yaz("PA-04", katalog_kodu="PA04")) == ""
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("YATAK ODASI 1", "120x180")], musteri={"ad": "Deniz"})
    assert k.is_emri["revizyon"] == 2 and _ad(k) == ""


def test_sevk_adresi_kalir_ad_duser(s):
    k = s.yaz("PA-04, sevk Çatalca", katalog_kodu="PA04", musteri={"ad": "Deniz", "sevk_adresi": "Çatalca"})
    assert _ad(k) == "" and k.is_emri["kunye"]["sevk_adresi"] == "Çatalca"


# ── müşteri adı görünür kalır (D-33) ────────────────────────────────────────────────────────────────────────────────────────

def test_mesajda_yazan_musteri_adi_kalir(s):
    k = s.yaz("PA-04, müşteri Ayşe Kaya", katalog_kodu="PA04", musteri={"ad": "Ayşe Kaya"})
    assert _ad(k) == "Ayşe Kaya"


@pytest.mark.parametrize("metin", ["PA-04, müşteri Deniz Örnek", "PA-04 Deniz'in evi", "PA-04 deniz bey için"])
def test_bayi_kendi_adini_yazdiysa_kalir(s, metin):
    """Bayi kendi evi için istiyor olabilir: adı bu mesajda yazıyorsa müşteri adıdır."""
    k = s.yaz(metin, katalog_kodu="PA04", musteri={"ad": "Deniz"})
    assert _ad(k) == "Deniz"


def test_onceki_mesajdaki_musteri_adi_ezilmez(s):
    assert _ad(s.yaz("PA-04, müşteri Ayşe Kaya", katalog_kodu="PA04", musteri={"ad": "Ayşe Kaya"})) == "Ayşe Kaya"
    k = s.yaz("yatak odası 1 penceresi 120x180 olsun", pencereler=[pen("YATAK ODASI 1", "120x180")], musteri={"ad": "Deniz Bey"})
    assert _ad(k) == "Ayşe Kaya"


def test_bayi_adinin_bir_sozcugunu_tasiyan_baska_ad_kalir(s):
    """"Deniz Kaya" bayinin adı değildir (Kaya kartta yok): kural yalnız bütün sözcükleri karttan gelen adı düşürür."""
    k = s.yaz("PA-04", katalog_kodu="PA04", musteri={"ad": "Deniz Kaya"})
    assert _ad(k) == "Deniz Kaya"


# ── çelik: antetin proje adı ────────────────────────────────────────────────────────────────────────────────────────────────

def test_celik_antetine_bayi_adi_cikmaz(s):
    k = s.yaz("Ç8801K", katalog_kodu="Ç8801K", yapi_turu="celik", musteri={"ad": "Deniz"})
    assert _ad(k) == "" and k.is_emri["bilgi"]["musteri_adi"] == ""
    assert k.is_emri["talep"]["bayi"]["ad"] == "Deniz Örnek"             # bayinin adı kendi alanında aynen


def test_celik_mesajda_yazan_musteri_adi_antette(s):
    k = s.yaz("Ç8801K, müşteri Ayşe Kaya", katalog_kodu="Ç8801K", yapi_turu="celik", musteri={"ad": "Ayşe Kaya"})
    assert _ad(k) == "Ayşe Kaya" and k.is_emri["bilgi"]["musteri_adi"] == "Ayşe Kaya"


# ── kuralın kenarları ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_kart_ya_da_ham_mesaj_yoksa_dokunulmaz(tmp_path):
    t = Talep(niyet="yeni_talep", guven="yuksek", ozet="x", musteri={"ad": "Deniz"})
    k = Konusma("900000000107", kok=tmp_path)
    assert K._bayi_adi_musteri_degil(k, t, None, "PA-04") is t
    assert K._bayi_adi_musteri_degil(k, t, BAYI, None) is t
    assert K._bayi_adi_musteri_degil(k, t, {"kod": "B08", "ad": "", "hitap": ""}, "PA-04") is t


def test_yalniz_unvan_ad_degildir():
    assert K._ad_sozcukleri("Deniz Bey") == ["deniz"] and K._ad_sozcukleri("Sayın ÖRNEK, Deniz") == ["ornek", "deniz"]
    assert K._ad_sozcukleri(None) == [] and K._ad_sozcukleri("Bey") == []
