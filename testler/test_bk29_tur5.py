"""BK-29 tur 5 (pano 216) · 13 Kasım 2026 canlı denetimi tur 3 (v2026.11.13d), gözlem 1.

Onay bekleyen planda "iptal" ilk yazışta iptal sayılmıyordu: LLM "red" niyeti veriyor, kural onu "Anladım. Neyi değiştirelim?" sorusuna
çeviriyordu (revizyon formu); talep ikinci "iptal"le kapanıyordu. Bayinin açık iptal sözü (K18) talebi ilk yazışta kapatır.
"beğenmedim", "olmadı", "hayır" ve olumsuz biçim ("iptal etmeyin") bugünkü gibi revizyon sorusu alır.
Pano 202 (D-85): prefabrik plan metni kodun metni ("PA-06 seçildi. Ön onay planınız hazır; …").
Tur 4 canlı denetimi (v2026.11.13e, 14 Kasım 00:02–00:16): "hiçbiri" ilk planda (r01) yeni revizyon üretiyordu. Yerelde üretildi: LLM revizyon
mesajında evin kodunu bağlamdan yineliyor ("PA-06"), seçilmiş çatı (PA-06-K) sessizce evin kendi çatısına dönüyordu; "pencere" sözü olmayan
serbest istek kopyası ("Mutfak camı 120x120") da planı "değişti" saydırıyordu. P6001 ve ölçü cevabından sonraki metin D-85 metniyle.
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
from test_celik_revizyon_karar import Sohbet  # noqa: E402
from test_bk29_revizyon_reddi import KABUL  # noqa: E402
from test_bk29_pencere_sorulari import _plan  # noqa: E402

KAPANDI = "Talep kapatıldı. Yeni bir plan istediğinizde yazmanız yeterli."


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path, kabul=KABUL)


@pytest.mark.parametrize("soz", ["iptal", "İptal", "iptal edin", "Talebi iptal edin lütfen", "iptal ediyoruz", "vazgeçtik"])
def test_onay_bekleyen_planda_iptal_ilk_yazista_kapatir(s, soz):
    _plan(s, "PA04")
    k = s.yaz(soz, niyet="red", ozet="Bayi talebi iptal etmek istiyor.")
    assert (k.eylem, k.gerekce, k.mesaj) == ("cevapla", "iptal", KAPANDI)
    assert not s.k.d.get("taslak") and not s.k.d.get("son_is_emri")


def test_iptalden_sonra_yalniz_kod_yeni_plan(s):
    """Denetim A7: "iptal" → "Talep kapatıldı." → "PA-04" → PA-04 planı r01 (tur 3'te iki "iptal" gerekiyordu)."""
    _plan(s, "PA04")
    assert s.yaz("iptal", niyet="red").mesaj == KAPANDI
    k = s.yaz("PA-04", niyet="diger", ozet='"PA-04" yazdınız, ne istediğinizi anlayamadık.')
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 1, k.mesaj
    assert k.mesaj.startswith("PA-04 seçildi. ")


@pytest.mark.parametrize("soz", ["beğenmedim", "olmadı", "hayır", "iptal etmeyin", "iptal mi?"])
def test_ret_sozu_revizyon_sorusu_alir(s, soz):
    """Açık iptal sözü olmayan ret bugünkü gibi: plan açık kalır, "Neyi değiştirelim?" sorulur."""
    _plan(s, "PA04")
    k = s.yaz(soz, niyet="red")
    assert (k.eylem, k.soru_alani) == ("sor", "revizyon_ne"), k.mesaj
    assert k.mesaj.startswith("Anladım. Neyi değiştirelim?")
    assert s.plan["revizyon"] == 1


def test_revizyon_sorusundan_sonra_iptal_bugunku_gibi(s):
    """"Neyi değiştirelim?" açıkken "iptal" talebi kapatır (tur 3'teki ikinci "iptal"; değişmedi)."""
    _plan(s, "PA04")
    s.yaz("beğenmedim", niyet="red")
    assert s.yaz("iptal", niyet="red").mesaj == KAPANDI


@pytest.mark.parametrize("soz,beklenen", [
    ("iptal", True), ("iptal et", True), ("iptal edelim", True), ("iptal olsun", True), ("iptal edilsin", True),
    ("bu talebi iptal ediyorum", True), ("vazgeçtim", True), ("iptal lütfen", True),
    ("iptal etmeyin", False), ("iptal etme", False), ("iptal edilmesin", False), ("vazgeçmedim", False), ("iptal etmedik", False),
    ("iptal mi", False), ("pencereyi iptal et", False), ("beğenmedim", False), ("hayır", False), ("", False),
])
def test_iptal_sozu(soz, beklenen):
    assert K._iptal_sozu(soz) is beklenen


# ── D-85: plan metni kodun metni (pano 202; Lokman 13 Kasım 19:15:09 kartı "Yeni metin olsun") ────────────────────────────────

HAZIR = "Ön onay planınız hazır; plan görseli ve PDF ektedir."


def test_dis_olcuden_plan_metni(tmp_path):
    """Dış ölçüden kurulan plan (GRID şablonu): baş yok, "Dış ölçü … pano)." ön bilgisi yeter; revizyonda "Plan r02"."""
    from test_celik_revizyon_karar import pen
    s = Sohbet(tmp_path)
    k = s.yaz("7,73 x 10,14 m 2+1 tek kat prefabrik", dis_olcu={"en_m": 7.73, "boy_m": 10.14}, oda_programi="2+1",
              yapi_turu="prefabrik", kat_sayisi=1, ozet="7,73 x 10,14 metre 2+1 prefabrik ev istiyorsunuz.")
    assert k.eylem == "is_emri" and k.gerekce == "şablon GRID-6x8", k.mesaj
    assert k.mesaj == f"Dış ölçü 7,73 m x 10,14 m (6x8 pano). {HAZIR}"
    assert k.is_emri["talep"]["metin"] == "Dış ölçü 7,73 m x 10,14 m (6x8 pano)"
    k = s.yaz("salonun sol penceresi 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="sol")])
    assert k.mesaj == f"Dış ölçü 7,73 m x 10,14 m (6x8 pano). Plan r02. Değişiklik: SALON 120x120 sol penceresi 120x180. {HAZIR}"
    assert k.is_emri["talep"]["metin"] == "Plan r02 · Değişiklik: SALON 120x120 sol penceresi 120x180"


@pytest.mark.parametrize("kaynak,rev,ozet,beklenen", [
    ("PA06K", 1, "", "PA-06-K seçildi"), ("PA04", 3, "", "PA-04 r03"), ("P6001", 1, "LLM özeti", "P6001 seçildi"),
    ("cizim-okuma", 1, "Çiziminizdeki plan (7,73 × 8,88 m, 2+1).", "Çiziminizdeki plan (7,73 × 8,88 m, 2+1)"),
    ("cizim-okuma", 2, "Mutfak penceresi değişsin.", "Çiziminizdeki plan r02"), ("GRID-6x8", 1, "x", ""), ("GRID-6x8", 2, "x", "Plan r02"),
])
def test_plan_basi(kaynak, rev, ozet, beklenen):
    from beyin.katalog import Katalog
    assert K._plan_basi(Katalog(kabul_edilmis=KABUL), kaynak, rev, ozet) == beklenen


# ── Tur 4 canlı denetimi (v2026.11.13e): "hiçbiri" ilk planda, yinelenen kod, P6001 ve ölçü cevabının metni ─────────────────────────

def _cati_setinden_r01(tmp_path):
    from test_bk29_tur4 import CanliSohbet
    s = CanliSohbet(tmp_path, kabul=KABUL)
    s.yaz("PA-06", niyet="diger")
    k = s.yaz("2", niyet="diger")
    assert k.revizyon == 1 and s.plan["talep"]["kaynak"] == "PA06K"
    return s


@pytest.mark.parametrize("ek", [{"katalog_kodu": "PA-06"}, {"ozel_istekler": ["Mutfak camı 120x120 olsun"]},
                                {"bina_ozellikleri": {"Mutfak": "120x120"}}, {"katalog_kodu": "PA06", "ozel_istekler": ["Mutfak 120x120"]}])
def test_hicbiri_ilk_planda_yeni_revizyon_uretmez(tmp_path, ek):
    """Canlı A18 (…3784 r02, …4243 r02): r01'de "hiçbiri" → "Tamam, o pencereyi değiştirmedim. Ön onay planını hazırlıyorum" + yeni revizyon.
    LLM'in yinelediği kod ya da "pencere" sözü olmayan kopya planı "değişti" saydırıyordu. Plan aynı numarayla kalır."""
    from test_celik_revizyon_karar import pen
    s = _cati_setinden_r01(tmp_path)
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")], ozet="Mutfak penceresinin 120x120 olmasını istiyorsunuz.", **ek)
    assert k.soru_alani == "pencere_secim"
    k = s.yaz("hiçbiri", niyet="red", ozet="Pencere seçimi için sunulan seçeneklerin hiçbirini istemiyorsunuz.", **ek)
    no = s.plan["is_emri_no"]
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_DEGISMEDI) and s.plan["revizyon"] == 1, k.mesaj
    assert k.mesaj.startswith(f"Tamam, o pencereyi değiştirmedim. Planınız ({no} r01) değişmedi.")


def test_yinelenen_kod_secilen_catiyi_degistirmez(tmp_path):
    """LLM revizyonda "PA-06" yazınca r02 PA-06'nın kendi çatısıyla çiziliyordu (bayinin seçtiği PA-06-K sessizce düşüyordu)."""
    from test_celik_revizyon_karar import pen
    s = _cati_setinden_r01(tmp_path)
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")], katalog_kodu="PA-06")
    k = s.dugme("q:pencere_secim:1")
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["talep"]["kaynak"] == "PA06K", k.mesaj
    assert k.mesaj.startswith("PA-06-K r02. Değişiklik: MUTFAK 120x100 sol penceresi 120x120.")


def test_yazilan_kod_bugunku_gibi(tmp_path):
    """Bayi kodu kendisi yazarsa ("PA-06 olsun") LLM'in kodu geçerli: kod yazılı seçimdir (K18)."""
    s = _cati_setinden_r01(tmp_path)
    k = s.yaz("PA-06 olsun", niyet="revizyon", katalog_kodu="PA-06")
    assert k.eylem == "is_emri" and s.plan["talep"]["kaynak"] == "PA06", k.mesaj


def test_hicbiri_baska_degisiklik_sessizce_dusmez(tmp_path):
    """Aynı mesajdaki pencereyle ilgisiz serbest istek "hiçbiri"de kalır: plan o istekle r02 olur (değişiklik isteği sessizce düşmez)."""
    from test_celik_revizyon_karar import pen
    s = _cati_setinden_r01(tmp_path)
    s.yaz("mutfak penceresi 120x120 olsun, iç duvarlar beyaz olsun", pencereler=[pen("mutfak", "120x120")],
          ozel_istekler=["Mutfak penceresi 120x120 olsun", "İç duvarlar beyaz olsun"])
    k = s.yaz("hiçbiri", niyet="red")
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    assert k.mesaj.startswith("Tamam, o pencereyi değiştirmedim. PA-06-K r02.")
    assert k.is_emri["ozel_istekler"] == ["İç duvarlar beyaz olsun"]


def test_p6001_metni_koddan(s):
    """Canlı A8 (…4618 r01): LLM kodu verince metin ve PDF başlığı modelin sorusuydu ("P6001 modeliyle ilgili talebinizi aldık; …
    belirtir misiniz?"). D-85 metni: "P6001 seçildi. Ön onay planınız hazır; …"."""
    k = s.yaz("P6001", katalog_kodu="P6001", ozet="P6001 modeliyle ilgili talebinizi aldık; bu modelle ne yapmak istediğinizi belirtir misiniz?")
    assert k.eylem == "is_emri" and k.mesaj == f"P6001 seçildi. {HAZIR}", k.mesaj
    assert k.is_emri["talep"]["metin"] == "P6001 seçildi" and k.is_emri["talep"]["metin_koddan"] is True


def test_olcu_cevabindan_sonra_metin_koddan(s):
    """Canlı A15 (…3459 r03): ölçü sorusunun cevabından sonra plan metni önceki mesajın özetini taşıyordu ("… yeni pencere ölçüsünü
    belirtir misiniz? (YATAK ODASI 1 penceresi 120x150) Ön onay planını hazırlıyorum …")."""
    from test_celik_revizyon_karar import pen
    _plan(s, "PA04")
    s.yaz("Yatak odası 1 penceresini değiştirelim", pencereler=[pen("yatak odası 1", None)],
          ozet="Yatak odası 1 penceresini değiştirmek istiyorsunuz; yeni pencere ölçüsünü belirtir misiniz?")
    k = s.yaz("120x150", niyet="diger", pencereler=[pen(None, None)])
    assert k.eylem == "is_emri" and k.mesaj == f"PA-04 r02. Değişiklik: YATAK ODASI 1 penceresi 120x150. {HAZIR}", k.mesaj
    assert k.is_emri["talep"]["metin"] == "PA-04 r02 · Değişiklik: YATAK ODASI 1 penceresi 120x150"


# ── D-86 (Lokman, 13 Kasım 21:36 UTC kartı "Değişmedi desin"): aynı değişiklik yeniden istenince yeni revizyon gitmez ──────────────

def test_ayni_degisiklik_yeniden_istenince_plan_degismedi(s):
    """Tur 4 canlı gözlem 3 (…4303 r03 → …4342 r04): aynı cümle ikinci kez yazılınca aynı plan yeni numarayla gidiyordu."""
    from test_celik_revizyon_karar import pen
    _plan(s, "PA04")
    k = s.yaz("Yatak odası 1 penceresi 100x140 olsun", pencereler=[pen("yatak odası 1", None)])
    assert k.eylem == "is_emri" and k.revizyon == 2, k.mesaj
    no = s.plan["is_emri_no"]
    k = s.yaz("Yatak odası 1 penceresi 100x140 olsun", pencereler=[pen("yatak odası 1", None)])
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_DEGISMEDI) and s.plan["revizyon"] == 2 and s.k.d["revizyon"] == 1
    assert k.mesaj == (f"Planınız ({no} r02) değişmedi; YATAK ODASI 1 penceresi zaten 100x140. "
                       "Onaylayabilir ya da başka bir değişiklik yazabilirsiniz.")
    assert [b["baslik"] for b in k.butonlar] == ["Onayla", "Revize et"] and s.k.d["asama"] == "onay_bekliyor"
    k = s.yaz("Yatak odası 1 penceresi 120x150 olsun", pencereler=[pen("yatak odası 1", None)])
    assert k.eylem == "is_emri" and k.revizyon == 3, k.mesaj                       # gerçek değişiklik: sayaç kaldığı yerden


def test_ilk_plandaki_olcu_istenince_plan_degismedi(s):
    """Planda zaten olan ölçü istenince (altın set D03) plan yeniden çizilmez."""
    from test_celik_revizyon_karar import pen
    s.yaz("P6001", katalog_kodu="P6001")
    k = s.yaz("yatak odası 1 penceresi 120x120 olsun", pencereler=[pen("yatak odası 1", "120x120")])
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_DEGISMEDI) and s.plan["revizyon"] == 1
    assert "değişmedi; YATAK ODASI 1 penceresi zaten 120x120." in k.mesaj


def test_secilmis_pencerede_ayni_olcu(s):
    """Seçilmiş pencere (birden çok pencereli oda): notta önceki ölçü yazılmaz ("MUTFAK sol penceresi zaten 120x120")."""
    from test_celik_revizyon_karar import pen
    _plan(s, "PA06")
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert s.dugme("q:pencere_secim:1").revizyon == 2
    s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    k = s.dugme("q:pencere_secim:1")
    assert (k.eylem, k.gerekce) == ("cevapla", K.PLAN_DEGISMEDI) and s.plan["revizyon"] == 2, k.mesaj
    assert "değişmedi; MUTFAK sol penceresi zaten 120x120." in k.mesaj


def test_degismedi_notu_yalniz_bu_mesajin_odasi(s):
    """Önceki revizyonun değişikliği nota karışmaz: yalnız bu mesajda istenen oda yazılır."""
    from test_celik_revizyon_karar import pen
    _plan(s, "PA04")
    s.yaz("Yatak odası 1 penceresi 100x140 olsun", pencereler=[pen("yatak odası 1", None)])
    banyo = next(a["olcu"] for a in s.plan["acikliklar"] if a["tur"] == "pencere" and a.get("mahal") == "BANYO")
    k = s.yaz(f"banyo penceresi {banyo} olsun", pencereler=[pen("banyo", banyo)])
    assert k.gerekce == K.PLAN_DEGISMEDI and f"değişmedi; BANYO penceresi zaten {banyo}." in k.mesaj, k.mesaj


def test_musteri_adi_degisirse_yeni_revizyon(s):
    """Pencere aynı, antet bilgisi değişti: plan değişmiş sayılır (D-86 kapsam dışı)."""
    from test_celik_revizyon_karar import pen
    _plan(s, "PA04")
    s.yaz("Yatak odası 1 penceresi 100x140 olsun", pencereler=[pen("yatak odası 1", None)])
    k = s.yaz("Yatak odası 1 penceresi 100x140 olsun, müşteri Ali Veli", pencereler=[pen("yatak odası 1", None)], musteri={"ad": "Ali Veli"})
    assert k.eylem == "is_emri" and k.revizyon == 3, k.mesaj


@pytest.mark.parametrize("notlar,beklenen", [
    (["YATAK ODASI 1 penceresi 100x140"], "YATAK ODASI 1 penceresi zaten 100x140"),
    (["MUTFAK 120x120 sol penceresi 120x120"], "MUTFAK sol penceresi zaten 120x120"),
    (["ODA 1 penceresi 120x120", "BANYO penceresi 60x60"], "ODA 1 penceresi zaten 120x120, BANYO penceresi zaten 60x60"),
    (["sol-sağ aynalandı"], "istediğiniz değişiklik planda zaten var"), ([], ""),
])
def test_zaten_notu(notlar, beklenen):
    assert K._zaten_notu(notlar) == beklenen

