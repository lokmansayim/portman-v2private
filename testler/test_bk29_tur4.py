"""BK-29 tur 4 (pano 201, 210) · 13 Kasım 2026 canlı denetimi (v2026.11.13c) bulguları.

B4: "Yatak odası 1 penceresi 120x150 olsun" ölçüyü yeniden sorduruyordu; "120x150" cevabı da alınmıyordu. LLM şeması pencere ölçüsünü listeden
seçer (`sema.Pencere.olcu`): listede olmayan ölçü null döner ya da listedeki bir ölçüye kayar. Kayıtta olmayan ölçü kurulur (İE-27 madde 11);
kod yeni ölçüyü bayinin sözünden okur (K18).
B5: LLM aynı isteği ("pencere 120x120 olsun") hem odasız pencere satırı hem varyant olarak yazıyordu: yazılı "Oda 1" cevabından sonra oda
ikinci kez soruluyor, listeden seçimden sonra değişiklik iki kez yazılıyordu ("ODA 1 penceresi 120x120, ODA 1 penceresi 120x120").
Gözlem 4: değişiklik notu pencereyi şablondaki ölçüyle anıyordu (r02'de 120x120 olan sol pencere r03'te "120x100 sol").
LLM yok, Postgres yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür (LLM'in canlıda verdiği biçimde).
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from beyin import karar as K  # noqa: E402
from test_celik_revizyon_karar import Sohbet, pen  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402
from test_bk29_pencere_sorulari import _plan, _pencereler, _pv  # noqa: E402


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


# ── B5: aynı istek hem satır hem varyant ──────────────────────────────────────────────────────────────────────────────────────

def _ikiz(s: Sohbet):
    _plan(s, "PA03")
    k = s.yaz("pencere 120x120 olsun", pencereler=[pen(None, "120x120")], varyantlar=[_pv("120x120", "pencere 120x120 olsun")])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_mahal")
    return k


def test_b5_yazili_oda_cevabi_ikizde_tek_soru(s):
    """Canlı: "Oda 1" yazınca "Hangi odanın penceresi?" yineleniyordu. Artık r02 gelir, not bir kez yazılır."""
    _ikiz(s)
    k = s.yaz("Oda 1", niyet="diger")
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert k.mesaj == "PA-03 r02. Değişiklik: ODA 1 penceresi 120x120. Ön onay planınız hazır; plan görseli ve PDF ektedir."   # tur 5 (pano 202): metin koddan
    assert _pencereler(k, "ODA 1") == [("120x120", "sol")]
    assert [p["mahal"] for p in s.k.d["taslak"]["pencereler"]] == ["ODA 1"]


def test_b5_listeden_oda_ikizde_not_bir_kez(s):
    """Canlı: listeden ODA 1 seçilince not iki kez yazılıyordu."""
    _ikiz(s)
    k = s.dugme("q:pencere_mahal:1")
    assert k.eylem == "is_emri" and k.revizyon == 2
    assert k.gerekce == "şablon PA03 (ODA 1 penceresi 120x120)"


def test_b5_yazili_oda_llm_icerikli_cevap(s):
    """LLM kısa cevaba içerik yazsa da ("Oda 1" → oda 1 penceresi) cevap odadır; plan bir kez değişir."""
    _ikiz(s)
    k = s.yaz("Oda 1", pencereler=[pen("oda 1", "120x120")])
    assert k.eylem == "is_emri" and k.revizyon == 2
    assert k.gerekce == "şablon PA03 (ODA 1 penceresi 120x120)"


def test_ikiz_ekleme_satiri_yutulmaz(s):
    """Odasız EKLEME satırı aynı ölçülü varyantla birleşmez: ekleme sessizce değişikliğe dönmez, bugünkü yönlendirme kalır (K21)."""
    _plan(s, "PA03")
    s.yaz("120x120 pencere ekleyin", pencereler=[pen(None, "120x120", islem="ekle")], varyantlar=[_pv("120x120", "120x120 pencere")])
    k = s.yaz("Oda 1", niyet="diger")
    assert k.eylem == "yonlendir" and "ekleme" in k.mesaj


# ── B4: listede olmayan ölçü ──────────────────────────────────────────────────────────────────────────────────────────────────

def test_b4_listede_olmayan_olcu_sozden_kurulur(s):
    """Canlı: "Pencereyi hangi ölçüye değiştirelim?" geliyordu. LLM ölçüyü null verir; ölçü bayinin sözünden okunur, r02 gelir."""
    _plan(s, "PA04")
    k = s.yaz("Yatak odası 1 penceresi 120x150 olsun", pencereler=[pen("yatak odası 1", None)])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert _pencereler(k, "YATAK ODASI 1") == [("120x150", "sol")]
    assert "Değişiklik: YATAK ODASI 1 penceresi 120x150." in k.mesaj


def test_b4_llm_listedeki_olcuye_kaysa_soz_gecerli(s):
    """LLM 120x150'yi listedeki 120x160'a kaydırırsa (sözde 120x160 yok) bayinin sözündeki 120x150 kurulur."""
    _plan(s, "PA04")
    k = s.yaz("Yatak odası 1 penceresi 120x150 olsun", pencereler=[pen("yatak odası 1", "120x160")])
    assert k.eylem == "is_emri" and _pencereler(k, "YATAK ODASI 1") == [("120x150", "sol")]


@pytest.mark.parametrize("cevap", ["120x150", "120x150 olsun", "120 x 150"])
def test_b4_olcu_sorusunun_cevabi(s, cevap):
    """Sözde ölçü yoksa bot sorar; "120x150" cevabı alınır (canlıda soru yineleniyordu). LLM cevaba boş satır yazar."""
    _plan(s, "PA04")
    k = s.yaz("Yatak odası 1 penceresini değiştirelim", pencereler=[pen("yatak odası 1", None)])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_olcu")
    k = s.yaz(cevap, niyet="diger", pencereler=[pen(None, None)])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert _pencereler(k, "YATAK ODASI 1") == [("120x150", "sol")]


def test_b4_varyant_yolunda_olcu_sorusunun_cevabi(s):
    """Ölçüsüz pencere varyantı ("yatak odası 1 penceresini büyütelim") sorulur; cevap varyanta yazılır."""
    _plan(s, "PA04")
    k = s.yaz("yatak odası 1 penceresini büyütelim",
              varyantlar=[{"tur": "pencere_degistir", "aciklama": "yatak odası 1 penceresini büyütelim", "parametreler": {"mahal": "yatak odası 1"}}])
    assert (k.eylem, k.soru_alani) == ("sor", "pencere_olcu")
    k = s.yaz("120x150", niyet="diger")
    assert k.eylem == "is_emri" and _pencereler(k, "YATAK ODASI 1") == [("120x150", "sol")]


def test_b4_iki_odali_sozde_her_oda_kendi_olcusu(s):
    """İki odayı anan sözde her oda kendi parçasından okunur (salonun ölçüsü yatak odasına geçmez)."""
    _plan(s, "PA04")
    k = s.yaz("Yatak odası 1 penceresi 120x150, salonun sol penceresi 160x120 olsun",
              pencereler=[pen("yatak odası 1", None), pen("salon", "160x120", duvar="sol")])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert _pencereler(k, "YATAK ODASI 1") == [("120x150", "sol")]
    assert _pencereler(k, "SALON") == [("160x120", "sol"), ("120x180", "on")]


def test_b4_olcu_sorusuna_olcusuz_cevap_bugunku_yol(s):
    """Ölçü sorusuna ölçüsüz cevap ölçü yazmaz, plan değişmez (bugünkü "Anlayamadım"); soru askıda kalır, sonraki ölçü cevabı alınır."""
    _plan(s, "PA04")
    s.yaz("Yatak odası 1 penceresini değiştirelim", pencereler=[pen("yatak odası 1", None)])
    k = s.yaz("bilmiyorum", niyet="diger")
    assert (k.eylem, k.gerekce) == ("cevapla", "anlaşılmadı") and s.plan["revizyon"] == 1
    assert not any(p.get("olcu") for p in s.k.d["taslak"].get("pencereler") or [])
    k = s.yaz("120x150", niyet="diger")
    assert k.eylem == "is_emri" and _pencereler(k, "YATAK ODASI 1") == [("120x150", "sol")]


def test_b4_olcu_sorusuna_baska_odanin_sozu_bekleyene_yazilmaz(s):
    """Ölçü sorusu askıdayken başka odayı anan söz ("Yatak odası 2 penceresi 120x150 olsun") cevap sayılmaz: 120x150 yatak odası 1'e
    yazılmaz (yalnız ölçüden oluşan cevap alınır)."""
    _plan(s, "PA04")
    s.yaz("Yatak odası 1 penceresini değiştirelim", pencereler=[pen("yatak odası 1", None)])
    s.yaz("Yatak odası 2 penceresi 120x150 olsun", pencereler=[pen("yatak odası 2", None)])
    yo1 = [p for p in s.k.d["taslak"]["pencereler"] if p["mahal"] == "yatak odası 1"]
    assert yo1 and yo1[0]["olcu"] is None and s.plan["revizyon"] == 1


@pytest.mark.parametrize("metin,beklenen", [
    ("120x150", "120x150"), ("120 x 150 olsun", "120x150"), ("120x150'lik yapın lütfen", "120x150"),
    ("mutfak penceresi 120x150 olsun", None), ("bilmiyorum", None), ("120x150 ve 120x180", None), ("7x4", None),
])
def test_yalniz_olcu_cevabi(metin, beklenen):
    assert K._yalniz_olcu(metin) == beklenen


@pytest.mark.parametrize("metin,beklenen", [
    ("Yatak odası 1 penceresi 120x150 olsun", "120x150"),
    ("120x100 yerine 120x150", "120x150"),
    ("Mutfağın sol duvarındaki 120x100 pencere 120x120 olsun", "120x120"),
    ("120x100 olan pencere 120x150 olsun", "120x150"),
    ("120 x 150'lik yapalım", "120x150"),
    ("120x150'ye çevirin", "120x150"),
    ("120x150", "120x150"),
    ("mutfaktaki 120x100 pencereyi değiştir", None),           # yalnız eski ölçü: yeni ölçü sorulur
    ("dış ölçü 700x400 olsun", None),                          # pencere aralığı dışında
    ("120x150 ve 120x180 olsun", None),                        # iki aday: okunmaz, sorulur (K21)
    ("pencereyi değiştirelim", None),
])
def test_sozdeki_yeni_olcu(metin, beklenen):
    assert K._sozdeki_yeni_olcu(metin) == beklenen


# ── Gözlem 4: değişiklik notu önceki planın ölçüsüyle ─────────────────────────────────────────────────────────────────────────

def test_not_onceki_planin_olcusuyle(s):
    """r02'de sol pencere 120x120 oldu; r03'te aynı pencere 120x180 olunca not "120x120 sol" der (şablonun "120x100 sol"u değil)."""
    _plan(s, "PA06")
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert s.dugme("q:pencere_secim:1").gerekce == "şablon PA06 (MUTFAK 120x100 sol penceresi 120x120)"
    k = s.yaz("mutfak penceresi 120x180 olsun", pencereler=[pen("mutfak", "120x180")])
    assert "1) 120x120, sol duvar" in k.mesaj and k.butonlar[0]["baslik"] == "120x120 sol"
    k = s.dugme("q:pencere_secim:1")
    assert k.revizyon == 3 and k.gerekce == "şablon PA06 (MUTFAK 120x120 sol penceresi 120x180)"


def test_not_suren_onceki_degisiklik_sablon_olcusuyle(s):
    """Önceki revizyonun değişikliği sürer: o pencere önceki planda zaten yeni ölçüde, notu şablonun ölçüsüyle kalır."""
    _plan(s, "PA06")
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    s.dugme("q:pencere_secim:1")
    k = s.yaz("mutfak ön penceresi 160x120 olsun", pencereler=[pen("mutfak", "160x120", duvar="on")])
    assert k.revizyon == 3 and k.gerekce == "şablon PA06 (MUTFAK 120x100 sol penceresi 120x120, MUTFAK 160x180 ön penceresi 160x120)"


# ── Tur 3 canlı gözlemleri (pano 216, 202) ───────────────────────────────────────────────────────────────────────────────────────

class CanliSohbet(Sohbet):
    """Konuşma her mesajda kayıttan okunur (canlı gibi)."""
    def __init__(self, kok, kabul=None):
        super().__init__(kok, kabul=kabul)
        self.kok = kok

    def yaz(self, metin, **alan):
        self.k = K.Konusma("900000000101", kok=self.kok)
        return super().yaz(metin, **alan)

    def dugme(self, kimlik):
        self.k = K.Konusma("900000000101", kok=self.kok)
        return super().dugme(kimlik)


@pytest.mark.parametrize("ek", [{"ozel_istekler": ["Mutfak penceresi 120x120 olsun"]}, {"bina_ozellikleri": {"Mutfak penceresi": "120x120"}}, {}])
def test_hicbiri_yeni_revizyon_uretmez(tmp_path, ek):
    """Tur 3 gözlem 2: LLM pencere isteğini serbest istek ya da pafta alanı olarak da yazınca "hiçbiri" aynı planı r02 olarak çiziyordu
    ("Tamam, o pencereyi değiştirmedim. … 120x120 olmasını istiyorsunuz. Ön onay planını hazırlıyorum"). Plan aynı numarayla kalır."""
    s = CanliSohbet(tmp_path, kabul=KABUL)
    s.yaz("PA-06", niyet="diger")
    assert s.yaz("2", niyet="diger").revizyon == 1
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")], ozet="Mutfak penceresinin 120x120 olmasını istiyorsunuz.", **ek)
    assert k.soru_alani == "pencere_secim"
    k = s.yaz("hiçbiri", niyet="revizyon", ozet="Pencere seçimi için sunulan seçeneklerin hiçbirini istemiyorsunuz.")
    no = s.plan["is_emri_no"]
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_DEGISMEDI) and s.plan["revizyon"] == 1
    assert k.mesaj == (f"Tamam, o pencereyi değiştirmedim. Planınız ({no} r01) değişmedi. "
                       "Onaylayabilir ya da başka bir değişiklik yazabilirsiniz.")


def test_yalniz_kod_ozeti_koddan(s):
    """Tur 3 gözlem 3 (pano 202): boş sohbette "PA-04" planı doğruydu, metin LLM'in özetiydi (""PA-04" yazdınız, ne istediğinizi
    anlayamadık …"). Metin ve PDF başlığı kodun (tur 5, pano 202: Lokman'ın onayladığı metin)."""
    k = s.yaz("PA-04", niyet="diger", ozet='"PA-04" yazdınız, ne istediğinizi anlayamadık. Bir katalog kodu mu? Açıklar mısınız?')
    assert k.eylem == "is_emri"
    assert k.mesaj == "PA-04 seçildi. Ön onay planınız hazır; plan görseli ve PDF ektedir."
    assert k.is_emri["talep"]["metin"] == "PA-04 seçildi" and k.is_emri["talep"]["metin_koddan"] is True


def test_cati_setine_yazili_numara_pdf_basligi_koddan(s):
    """Tur 3: çatı setine yazılı "2" doğru planı getiriyordu, PDF başlığı LLM'in "… "2" diye cevap verdiniz; teyit …" özetiydi."""
    s.yaz("PA-06", niyet="diger")
    k = s.yaz("2", niyet="diger", ozet='Önceki seçenek sorusuna "2" diye cevap verdiniz; hangi seçeneği kastettiğinizi teyit edebilir misiniz?')
    assert k.eylem == "is_emri" and k.mesaj == "PA-06-K seçildi. Ön onay planınız hazır; plan görseli ve PDF ektedir."
    assert k.is_emri["talep"]["metin"] == "PA-06-K seçildi" and k.is_emri["talep"]["metin_koddan"] is True


def test_dugmeyle_secimde_metin_ayni(s):
    """Tur 5 (pano 202): düğmeyle seçimde de metin ve PDF başlığı aynı kalıp; revizyonda değişiklik kodun notuyla."""
    k = _plan(s, "PA04")
    assert k.mesaj == "PA-04 seçildi. Ön onay planınız hazır; plan görseli ve PDF ektedir."
    assert s.plan["talep"]["metin"] == "PA-04 seçildi" and s.plan["talep"]["metin_koddan"] is True
    k = s.yaz("salonun sol penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="sol")])
    assert k.mesaj == "PA-04 r02. Değişiklik: SALON 120x120 sol penceresi 120x180. Ön onay planınız hazır; plan görseli ve PDF ektedir.", k.mesaj
    assert k.is_emri["talep"]["metin"] == "PA-04 r02 · Değişiklik: SALON 120x120 sol penceresi 120x180"
