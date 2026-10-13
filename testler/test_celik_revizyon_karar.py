"""İE-08 8a PR-2b (A4) · kapanış incelemesi (13.10) bulgularının karar katmanında sınanması: çelik seçenek seti, okuma soruları ve
revizyon (bayinin sözünden, cümle cümle; K18, K21). LLM yok, Postgres yok, çizim yok: `karar_ver` elle kurulmuş `Talep`lerle sürülür,
düğmeler `kanal/etkilesim.coz` ile çözülür (worker'daki gibi). Katalog kabul kümesiz kurulur (harness gibi: yedi çelik aday görünür)."""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from beyin import celik_okuma as CO, karar as K  # noqa: E402
from beyin.katalog import Katalog  # noqa: E402
from beyin.konusma import Konusma  # noqa: E402
from beyin.sema import Talep  # noqa: E402
from kanal import etkilesim as ET  # noqa: E402

BAYI = {"kod": "B01", "ad": "Deneme Bayi A", "rol": "bayi", "numara": "900000000101"}


class Sohbet:
    def __init__(self, kok: Path, kabul=None):
        self.k = Konusma("900000000101", kok=kok)
        self.kat = Katalog(kabul_edilmis=kabul)

    def yaz(self, metin: str, **alan):
        alan.setdefault("niyet", "revizyon" if self.k.d.get("son_is_emri") else "yeni_talep")
        t = Talep(guven="yuksek", ozet=alan.pop("ozet", metin[:80]), **alan)
        return K.karar_ver(t, self.k, BAYI, self.kat, metin)

    def dugme(self, kimlik: str):
        if "{set}" in kimlik:
            kimlik = kimlik.replace("{set}", str((self.k.d.get("secenek_seti") or {}).get("id")))
        etk = ET.coz({"reply_id": kimlik, "type": "interactive"}, self.k.d)
        assert etk.get("gecerli"), etk
        return K.karar_ver(Talep.model_validate(etk["talep"]), self.k, BAYI, self.kat, etk["metin"])

    @property
    def plan(self) -> dict:
        return self.k.d.get("son_is_emri") or {}

    def degisiklikler(self, karar=None) -> list[str]:
        ie = (karar.is_emri if karar is not None else self.plan) or {}
        return [d.get("op") + ":" + str(d.get("aciklik") or d.get("kod") or "") for d in (ie.get("yapi") or {}).get("degisiklikler") or []]


def pen(mahal=None, olcu=None, islem="degistir", duvar=None) -> dict:
    p = {"mahal": mahal, "islem": islem}
    if olcu:
        p["olcu"] = olcu
    if duvar:
        p["duvar"] = duvar
    return p


def var(tur: str, aciklama: str) -> dict:
    return {"tur": tur, "aciklama": aciklama, "parametreler": {}}


@pytest.fixture
def s(tmp_path) -> Sohbet:
    return Sohbet(tmp_path)


def r01_k(s: Sohbet):
    k = s.yaz("Ç8801K", katalog_kodu="Ç8801K", yapi_turu="celik")
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 1
    return k


def test_ilk_planda_okuma_sorusu_cevaplanir(s):
    """CR1: soru r01 hazırlanırken de sorulur; cevap son plan olmadan işlenir (önce "Anlayamadım" dönüyordu)."""
    k = s.yaz("Ç8801K olsun, salondaki sol taraftaki pencere 120x180 olsun", katalog_kodu="Ç8801K", yapi_turu="celik",
              pencereler=[pen("salon", "120x180", duvar="sol")])
    assert k.eylem == "sor" and k.soru_alani == "okuma" and [b["id"] for b in k.butonlar] == ["q:okuma:1", "q:okuma:2", "q:okuma:0"]
    assert "Görselde" not in k.mesaj                                       # CR18: görsel cümlesini worker, görsel gidiyorsa ekler
    k = s.dugme("q:okuma:2")
    assert k.eylem == "is_emri" and k.revizyon == 1 and s.degisiklikler(k) == ["pencere_olcu:P4"]
    assert "kısa cevap" not in k.mesaj                                       # CR17: düğme özeti plan mesajına sızmaz


def test_set_sunulurken_istek_saklanir_secimde_uygulanir(s):
    """CR1b: "Ç8801, mutfak penceresi 120x120" → çatı seti (istek saklanır, mesajda söylenir) → K düğmesi → r01 K + mutfak 120/120.
    Önce düğmeden sonra LLM ipucuyla bütün pencereler soruluyordu ("Yaşam Alanı penceresini hangi ölçüye")."""
    k = s.yaz("Ç8801, mutfak penceresi 120x120 olsun", katalog_kodu="Ç8801", yapi_turu="celik", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "secenek" and K.CELIK_ISTEK_NOTU in k.mesaj
    k = s.dugme("s:{set}:Ç8801K")
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801K" and s.degisiklikler(k) == ["pencere_olcu:P5"]


@pytest.mark.parametrize("cevap, alan, beklenen", [
    ("L olsun", {"niyet": "yeni_talep"}, "Ç8801L"),
    ("çatı K olsun", {"niyet": "yeni_talep", "katalog_kodu": "Ç8801"}, "Ç8801K"),      # LLM bağlamdan taban kodu yinelese de
    ("3", {"niyet": "diger"}, "Ç8801L"),
])
def test_cati_seti_yazili_cevap(s, cevap, alan, beklenen):
    """Çatı seti açıkken yazılı cevap: setin kendi örneği ("çatı K olsun"), harf ve numara. Önce taslakta kalan "Ç8801" katalog çatısını
    seçiyor, "3" "Anlayamadım" diyordu (PR-2a'dan kalma; kapanış incelemesinde bulundu)."""
    assert s.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik").eylem == "secenek"
    k = s.yaz(cevap, **alan)
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == beklenen


def test_set_acikken_secim_olmayan_istek_set_yeniden_sunulur(s):
    s.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik")
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "secenek" and "Önce listeden seçin" in k.mesaj and K.CELIK_ISTEK_NOTU in k.mesaj
    k = s.yaz("2", niyet="diger")
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801K" and s.degisiklikler(k) == ["pencere_olcu:P5"]


def test_olcu_sorusu_ayni_turde_yinelenir(s):
    """CR2: ölçü sorusu yinelenince seçim sorusuna dönmez; ölçü gelince iki adayda seçim sorusu, sonra r02."""
    r01_k(s)
    k = s.yaz("yatak odası 2 penceresini değiştirelim", pencereler=[pen("yatak odası 2")])
    assert k.soru_alani == "okuma_olcu"
    k = s.yaz("büyük olsun", niyet="diger")
    assert k.soru_alani == "okuma_olcu" and k.mesaj.startswith("Anlayamadım.") and not k.butonlar
    k = s.yaz("120x180", niyet="diger")
    assert k.soru_alani == "okuma" and "120x180" in k.mesaj
    k = s.dugme("q:okuma:1")
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.degisiklikler(k) == ["pencere_olcu:P8"]


def test_eski_ipucu_sonraki_istegi_yonlendirmez(s):
    """CR3: "hiçbiri" denen pencere isteğinin LLM satırı taslakta kalsa da sonraki "dışlar 140" ve "çatı L" doğrudan uygulanır."""
    r01_k(s)
    assert s.yaz("salondaki sol taraftaki pencere 120x180", pencereler=[pen("salon", "120x180", duvar="sol")]).soru_alani == "okuma"
    assert s.dugme("q:okuma:0").soru_alani == "okuma_metin"
    k = s.yaz("dışlar 140'lık olsun", varyantlar=[var("diger", "dış duvarlar 140'lık")])
    assert k.eylem == "is_emri" and s.degisiklikler(k) == ["dis_karkas_140:"]
    k = s.yaz("çatı L olsun", varyantlar=[var("cati_degistir", "çatı L")])
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801L" and s.degisiklikler(k) == ["dis_karkas_140:", "cati_varyanti:Ç8801L"]


def test_iki_pencere_tek_mesajda(s):
    """CR4: "mutfak penceresi 120x120, banyo vasistası 60x60" — iki değişiklik (önce mutfak 60/60 oluyor, banyo düşüyordu)."""
    r01_k(s)
    k = s.yaz("mutfak penceresi 120x120, banyo vasistası 60x60 olsun", pencereler=[pen("mutfak", "120x120"), pen("banyo")])
    assert k.eylem == "is_emri" and s.degisiklikler(k) == ["pencere_olcu:P5", "pencere_olcu:P7"]
    yeni = {d["aciklik"]: (d["en"], d["yuk"]) for d in s.plan["yapi"]["degisiklikler"]}
    assert yeni == {"P5": (120, 120), "P7": (60, 60)}


@pytest.mark.parametrize("metin, alan", [
    ("dış kapı 140 cm olsun", {"varyantlar": [var("diger", "dış kapı 140 cm")]}),                      # CR5/CR9: dış 140 değil
    ("iç duvarlar 140, dış duvarlar 80 kalsın", {}),                                                    # CR5
    ("dış ölçü 14 x 8 olsun", {"dis_olcu": {"en_m": 8, "boy_m": 14}}),                                  # CR5
    ("dış cepheye 14 cm yalıtım", {"ozel_istekler": ["dış cepheye 14 cm yalıtım"]}),                    # CR5
    ("mutfak kapısı 90x200 olsun", {"varyantlar": [var("diger", "mutfak kapısı 90x200")]}),             # G3: pencereye yazılmaz
    ("mutfak dolabı 60x90 olsun", {}),                                                                 # G3
    ("veranda L olsun", {"varyantlar": [var("diger", "veranda L şeklinde")]}),                         # CR12: çatı L değil
    ("dışlar 140 olsun, mutfağa kapı ekleyin", {"varyantlar": [var("diger", "mutfağa kapı ekle")]}),   # CR9: kapı sessizce düşmez
    ("hol penceresi 120x120 olsun, banyoya havlupan koyalım", {"pencereler": [pen("hol", "120x120")]}),   # CR4: havlupan düşmez
    ("mutfağa bir pencere daha ekleyin 120x120", {"pencereler": [pen("mutfak", "120x120", islem="ekle")]}),   # CR6
])
def test_okunamayan_istek_yonlendirilir_plan_degismez(s, metin, alan):
    r01_k(s)
    no = s.plan["is_emri_no"]
    k = s.yaz(metin, **alan)
    assert k.eylem == "yonlendir" and k.is_emri is None, (k.eylem, k.mesaj)
    assert CO.norm(metin) not in CO.norm(k.gerekce)                         # gerekçe günlüğe gider: bayinin cümlesi orada yok (KVKK)
    assert s.plan["is_emri_no"] == no and s.plan["revizyon"] == 1 and s.degisiklikler() == []


def test_katalog_catisina_donus_sonra_pencere(s):
    """CR7: K seçilip katalog çatısına dönülünce sonraki revizyon kapanmış setin eski seçimine (K) geri dönmez."""
    s.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik")
    assert s.dugme("s:{set}:Ç8801K").eylem == "is_emri"
    k = s.yaz("katalog çatısı olsun", varyantlar=[var("cati_degistir", "katalog çatısı")])
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801"
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801" and s.degisiklikler(k) == ["pencere_olcu:P5"]


def test_soruyla_bekleyen_dis140_cevapta_uygulanir(s):
    """CR8: aynı mesajdaki "dışlar 140" pencere sorusuyla bekler (soruda söylenir), cevapta ikisi birlikte uygulanır."""
    r01_k(s)
    k = s.yaz("dışlar 140'lık olsun, salondaki sol taraftaki pencere 120x180 olsun", pencereler=[pen("salon", "120x180", duvar="sol")])
    assert k.soru_alani == "okuma" and k.mesaj.startswith("Not aldım: dış duvarlar 140'lık karkas")
    k = s.dugme("q:okuma:2")
    assert k.eylem == "is_emri" and s.degisiklikler(k) == ["dis_karkas_140:", "pencere_olcu:P4"]


def test_olcu_sorusunda_baska_oda_yeni_istektir(s):
    """CR10: mutfak için ölçü sorulmuşken "yok yok, banyo penceresi 120x50" mutfağa yazılmaz; soru düşer (söylenir), istek işlenir."""
    r01_k(s)
    assert s.yaz("mutfak penceresini değiştirelim", pencereler=[pen("mutfak")]).soru_alani == "okuma_olcu"
    k = s.yaz("yok yok, banyo penceresi 60x50 olsun", pencereler=[pen("banyo", None)])
    assert k.eylem == "is_emri" and "Önceki pencere sorumu cevaplamadığınız" in k.mesaj and s.degisiklikler(k) == ["pencere_olcu:P7"]


def test_gorunmeyen_cati_varyanti_soylenir(tmp_path):
    """CR11: kabul kaydı olmayan çatı istenince eski çatıyla aynı plan çizilmez; yönlendirilir."""
    s = Sohbet(tmp_path, kabul={"Ç8801", "Ç8801K"})
    r01_k(s)
    k = s.yaz("çatı L olsun", varyantlar=[var("cati_degistir", "çatı L")])
    assert k.eylem == "yonlendir" and "sunulamıyor" in k.mesaj and s.plan["revizyon"] == 1


def test_ikisi_de_iki_pencere(s):
    """CR14: "ikisi de olsun" hiçbiri değil, iki pencere."""
    r01_k(s)
    s.yaz("salondaki sol taraftaki pencere 120x180", pencereler=[pen("salon", "120x180", duvar="sol")])
    k = s.yaz("ikisi de olsun", niyet="diger")
    assert k.eylem == "is_emri" and s.degisiklikler(k) == ["pencere_olcu:P3", "pencere_olcu:P4"]


def test_degisiklik_yoksa_ayni_plan_cizilmez_bilgi_degisikligi_cizilir(s):
    """Revizyon niyetinde hiçbir şey okunmadıysa aynı plan yeniden çizilip hak harcanmaz (sorulur); bina özelliği (renk) revizyondur."""
    r01_k(s)
    k = s.yaz("tamam güzel olmuş", niyet="revizyon")
    assert k.eylem == "sor" and k.soru_alani == "okuma_metin" and s.plan["revizyon"] == 1
    k = s.yaz("dış boya rengi beyaz olsun", bina_ozellikleri={"Dış Boya Rengi": "beyaz"})
    assert k.eylem == "is_emri" and k.revizyon == 2 and k.is_emri["bilgi"]["ozellikler"].get("Dış Boya Rengi") == "beyaz"


def test_alan_seti_istegi_secilen_modele_islenir(s):
    """A2 alan seti: "88 m² 2+1 çelik, mutfak penceresi 120x120" — istek saklanır; KT-02 seçilince KT-02'nin mutfağına (açık mutfak:
    yaşama mekânı pencereleri) sorulur."""
    k = s.yaz("88 m2 2+1 çelik, mutfak penceresi 120x120", alan_m2=88, oda_programi="2+1", yapi_turu="celik", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "secenek" and K.CELIK_ISTEK_NOTU in k.mesaj
    k = s.yaz("KT-02 olsun", katalog_kodu="KT02")
    assert k.eylem == "sor" and k.soru_alani == "okuma" and "120x120" in k.mesaj


def test_ve_ile_iki_istek_ikisi_de_uygulanir(s):
    """Geometri hakemi ikinci tur: "ve" ile bağlanan ikinci istek düşmez (önce yalnız pencere uygulanıyor, dış 140 sessizce kalıyordu)."""
    r01_k(s)
    k = s.yaz("mutfak penceresi 120x120 ve dışlar 140'lık olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and s.degisiklikler(k) == ["dis_karkas_140:", "pencere_olcu:P5"]
    k = s.yaz("dış duvarlar 140'lık olsun ve çatı L olsun", varyantlar=[var("cati_degistir", "çatı L")])
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801L"
    assert s.degisiklikler(k) == ["dis_karkas_140:", "pencere_olcu:P5", "cati_varyanti:Ç8801L"]       # dış 140 zaten vardı: yinelenmedi


def test_ilk_planda_soru_bicimli_istek_sorulur(s):
    """Geometri hakemi ikinci tur: ilk planda "… olabilir mi?" sorulmadan değişikliksiz r01 çizilmez."""
    k = s.yaz("Ç8801K olsun, mutfak penceresi 120x120 olabilir mi?", katalog_kodu="Ç8801K", yapi_turu="celik", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "sor" and k.soru_alani == "okuma_metin" and not s.plan
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and k.revizyon == 1 and s.degisiklikler(k) == ["pencere_olcu:P5"]


def test_bilgi_cumlesi_tum_bilinmeyenleri_kapsamali(s):
    """Tek sözcüğü bilgi alanıyla örtüşen cümle bütünüyle bilgi sayılmaz: "salonu biraz büyütelim dış cephe gri olsun" yönlendirilir;
    yalnız renk söyleyen cümle bilgi revizyonudur (r02)."""
    r01_k(s)
    k = s.yaz("salonu biraz büyütelim dış cephe gri olsun", bina_ozellikleri={"Dış Cephe Rengi": "gri"})
    assert k.eylem == "yonlendir" and s.plan["revizyon"] == 1
    t = Sohbet(s.k.path.parent / "ikinci")
    r01_k(t)
    k = t.yaz("dış cephe rengi gri olsun", bina_ozellikleri={"Dış Cephe Rengi": "gri"})
    assert k.eylem == "is_emri" and k.revizyon == 2


@pytest.mark.parametrize("metin, alan, eylem", [
    ("Ç8801 çelik ev, çatı K ile L arasındaki fark nedir?", {"katalog_kodu": "Ç8801"}, "secenek"),      # kararsızlık: set (K seçilmez)
    ("Ç8801 çelik, çatı K ve L'yi görelim", {"katalog_kodu": "Ç8801"}, "secenek"),
    ("Ç8801K ve Ç8801L arasında kararsızım", {"katalog_kodu": "Ç8801K"}, "secenek"),
    ("Ç8801K olsun. Salon, mutfak, 2 yatak odası, banyo.", {"katalog_kodu": "Ç8801K"}, "is_emri"),     # oda listesi: talep bilgisi
    ("Ç8801K olur mu?", {"katalog_kodu": "Ç8801K"}, "is_emri"),
    ("Ç8801K olsun, dış duvar kalınlığı ne kadar?", {"katalog_kodu": "Ç8801K"}, "is_emri"),          # bilgi sorusu, değişiklik değil
    ("Ç8801K olsun, duvarlar 140 olsun", {"katalog_kodu": "Ç8801K"}, "sor"),                        # değişiklik ama "dış" yok: sorulur
])
def test_ilk_planda_soru_yalniz_gercek_degisiklikte(s, metin, alan, eylem):
    """Geometri hakemi üçüncü tur: ilk planda oda listesi, "… olur mu?" ve çatı kararsızlığı plan ya da set alır; yalnız gerçek değişiklik
    belirsizliği sorulur."""
    k = s.yaz(metin, yapi_turu="celik", **alan)
    assert k.eylem == eylem, (k.eylem, k.mesaj)


def test_cati_sorusunda_set_notu_yok_secimde_soru_yok(s):
    """"çatı nasıl olacak?" değişiklik isteği değildir: set mesajında "isteğinizi işleyeceğim" notu yok, seçim r01 verir."""
    k = s.yaz("Ç8801 çelik ev, çatı nasıl olacak?", katalog_kodu="Ç8801", yapi_turu="celik")
    assert k.eylem == "secenek" and K.CELIK_ISTEK_NOTU not in k.mesaj
    k = s.yaz("2", niyet="diger")
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801K"


def test_degisiklik_yok_yonlendirilmez(s):
    """"değişiklik yok" / "böyle kalsın" istek değildir: yönlendirilmez, aynı plan yeniden çizilmez (sorulur)."""
    r01_k(s)
    for metin in ("değişiklik yok", "böyle kalsın"):
        k = s.yaz(metin)
        assert k.eylem == "sor" and k.soru_alani == "okuma_metin" and s.plan["revizyon"] == 1, (metin, k.eylem)


@pytest.mark.parametrize("metin, alan, degisiklik", [
    ("çatıyı K'dan L'ye çevirelim, mutfak penceresi de 120x120 olsun", {"pencereler": [pen("mutfak", "120x120")]},
     ["pencere_olcu:P5", "cati_varyanti:Ç8801L"]),
    ("Ç8801K yerine Ç8801L olsun, mutfak penceresi 120x120", {"pencereler": [pen("mutfak", "120x120")]},
     ["pencere_olcu:P5", "cati_varyanti:Ç8801L"]),
    ("çatıyı K yerine L yapalım", {}, ["cati_varyanti:Ç8801L"]),
])
def test_dorduncu_tur_degisimin_kaynagi_secim_degil(s, metin, alan, degisiklik):
    """Geometri hakemi dördüncü tur (K-1): "K'dan L'ye", "K yerine L" çatıyı L yapar; değişimin kaynağı (K) seçenek sayılmaz. Önce iki
    harfli çatı cümlesinin belirsizliği okumanın sonunda siliniyor, çatı isteği pencereyle birlikte gelince sessizce düşüyordu (r02 K)."""
    r01_k(s)
    k = s.yaz(metin, **alan)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801L", (k.eylem, k.mesaj)
    assert s.degisiklikler(k) == degisiklik


@pytest.mark.parametrize("ilk, metin, alan", [
    ("Ç8801K", "mutfak penceresi 120x120 olsun, çatı K ve L olsun", {"pencereler": [pen("mutfak", "120x120")]}),
    ("Ç8801", "çatı K ya da L olsun, dışlar 140'lık olsun", {}),
])
def test_dorduncu_tur_iki_catili_cumle_baska_istekle_sorulur(s, ilk, metin, alan):
    """K-1: iki seçenekli çatı cümlesi başka bir değişiklikle birlikte gelse de sorulur (yalnız öteki değişiklik uygulanmaz)."""
    assert s.yaz(ilk + (" katalog çatısı" if ilk == "Ç8801" else ""), katalog_kodu=ilk, yapi_turu="celik").eylem == "is_emri"
    k = s.yaz(metin, **alan)
    assert k.eylem == "sor" and k.soru_alani == "okuma_metin" and s.plan["revizyon"] == 1, (k.eylem, k.mesaj)


@pytest.mark.parametrize("metin, alan, eylem, kod", [
    ("Ç8801K mi katalog çatısı mı olsun?", {"katalog_kodu": "Ç8801K"}, "secenek", None),          # Ö-1: katalog çatısı da seçenektir
    ("Ç8801 çelik ev, Ç8801K mi katalog çatısı mı olsun?", {"katalog_kodu": "Ç8801"}, "secenek", None),
    ("Ç8801L mi Ç8801 mi olsun?", {"katalog_kodu": "Ç8801L"}, "secenek", None),
    ("Ç8801K olsun ama çatısı katalogdaki gibi olsun", {"katalog_kodu": "Ç8801K"}, "secenek", None),
    ("Ç8801K ile katalog çatısı arasında kaldım", {"katalog_kodu": "Ç8801K"}, "secenek", None),
    ("Ç8801K olsun, duvarlar 140 olabilir mi?", {"katalog_kodu": "Ç8801K"}, "sor", None),            # Ö-2: 140 değerli soru değişikliktir
    ("Ç8801K olsun, duvarları 140'lık yapabilir miyiz?", {"katalog_kodu": "Ç8801K"}, "sor", None),
    ("Ç8801K olsun, L tipi mutfak olsun", {"katalog_kodu": "Ç8801K"}, "is_emri", "Ç8801K"),        # İ-2: şekil sözü çatı değil
    ("Ç8801 çelik ev, çatı L olsun", {"katalog_kodu": "Ç8801"}, "is_emri", "Ç8801L"),              # taban kod seçim sorusu dışında seçenek değil
    ("Ç8801 katalog çatısı", {"katalog_kodu": "Ç8801"}, "is_emri", "Ç8801"),
])
def test_dorduncu_tur_ilk_plan(s, metin, alan, eylem, kod):
    """Geometri hakemi dördüncü tur: ilk planda katalog çatısıyla kararsızlık set alır (mesajdaki kod seçilmez); "duvarlar 140 … mi?"
    sorulmadan çizilmez; çatı dışındaki tek harf ve taban kod kararsızlık sayılmaz."""
    k = s.yaz(metin, yapi_turu="celik", **alan)
    assert k.eylem == eylem, (k.eylem, k.mesaj)
    if kod:
        assert s.plan["yapi"]["kod"] == kod


def test_dorduncu_tur_taninmayan_oda_pencere_istegiyle_kalir(s):
    """İ-3: "çalışma odası ve mutfak pencereleri 120x120" — tanınmayan oda adı ayrı cümleye bölünüp düşmez; yalnız mutfak sessizce
    uygulanmaz, istek sorulur."""
    k = s.yaz("Ç8801K olsun, çalışma odası ve mutfak pencereleri 120x120", katalog_kodu="Ç8801K", yapi_turu="celik",
              pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "sor" and not s.plan, (k.eylem, k.mesaj)


@pytest.mark.parametrize("metin, ozellik", [
    ("çatı rengi kırmızı olsun", {"Çatı Kaplama Rengi": "kırmızı"}),
    ("çatı ve dış cephe gri olsun", {"Çatı Rengi": "gri", "Dış Cephe Rengi": "gri"}),
])
def test_dorduncu_tur_cati_rengi_bilgidir(s, metin, ozellik):
    """İ-1: harfsiz "çatı" sözü değişiklik işareti değildir: çatı rengi bilgi revizyonudur (r02, çatı aynı; önce yönlendiriliyor ya da
    "Anlayamadım" alıyordu)."""
    r01_k(s)
    k = s.yaz(metin, bina_ozellikleri=ozellik)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K" and s.degisiklikler(k) == [], (k.eylem, k.mesaj)


@pytest.mark.parametrize("metin, alan, eylem, kod", [
    ("Ç8801 çelik ev, Ç8801L olmasın", {"katalog_kodu": "Ç8801"}, "secenek", None),                  # olumsuz kod seçilmez (beşinci tur)
    ("Ç8801L olmasın", {"katalog_kodu": "Ç8801L"}, "secenek", None),
    ("Ç8801L istemiyoruz, Ç8801K olsun", {"katalog_kodu": "Ç8801K"}, "secenek", None),
    ("Ç8801K'dan bir tane olsun, Ç8801L değil", {"katalog_kodu": "Ç8801L"}, "secenek", None),
    ("Ç8801K'dan farklı bir çatı olsun", {"katalog_kodu": "Ç8801K"}, "secenek", None),               # LLM'in kodu değişimin kaynağı
    ("Ç8801K olsun başka değişiklik yok", {"katalog_kodu": "Ç8801K"}, "is_emri", "Ç8801K"),          # "yok" çatıyı olumsuz yapmaz
])
def test_besinci_tur_olumsuz_cati_secilmez(s, metin, alan, eylem, kod):
    """Geometri hakemi beşinci tur: çatı seçeneği taşıyan olumsuz cümlede kod seçilmez (ters çatı sorulmadan çiziliyordu); ilk planda
    çatı seti sunulur."""
    k = s.yaz(metin, yapi_turu="celik", **alan)
    assert k.eylem == eylem, (k.eylem, k.mesaj)
    if kod:
        assert s.plan["yapi"]["kod"] == kod


def test_besinci_tur_set_acikken_olumsuz_kod_secim_degil(s):
    """Set açıkken "Ç8801K'dan Ç8801L'ye geçmeyelim" L'yi seçmez, set yeniden sunulur."""
    assert s.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik").eylem == "secenek"
    k = s.yaz("Ç8801K'dan Ç8801L'ye geçmeyelim", katalog_kodu="Ç8801L")
    assert k.eylem == "secenek" and not s.plan


def test_besinci_tur_dis140_oda_cumlesiyle_dusmez(s):
    """Beşinci tur: "dışlar 140'lık olsun ve oda kapıları beyaz olsun" birleşip dış 140 ilk planda sessizce düşüyordu; set yolunda da."""
    k = s.yaz("Ç8801K olsun, dışlar 140'lık olsun ve oda kapıları beyaz olsun", katalog_kodu="Ç8801K", yapi_turu="celik")
    assert k.eylem == "is_emri" and s.degisiklikler(k) == ["dis_karkas_140:"]
    t = Sohbet(s.k.path.parent / "ikinci")
    assert t.yaz("Ç8801 çelik, dışlar 140'lık olsun ve çalışma odası geniş olsun", katalog_kodu="Ç8801", yapi_turu="celik").eylem == "secenek"
    k = t.yaz("2", niyet="diger")
    assert k.eylem == "is_emri" and t.plan["yapi"]["kod"] == "Ç8801K" and t.degisiklikler(k) == ["dis_karkas_140:"]


@pytest.mark.parametrize("metin, alan, cevap, degisiklik", [
    ("çatıyı K'dan L'ye çevirelim, salon penceresi 160x180", {"pencereler": [pen("salon", "160x180")]}, "1",
     ["pencere_olcu:P1", "cati_varyanti:Ç8801L"]),
    ("çatı L olsun, mutfak penceresini değiştirelim", {"pencereler": [pen("mutfak")]}, "120x120", ["pencere_olcu:P5", "cati_varyanti:Ç8801L"]),
    ("çatı L olsun, dışlar 140'lık olsun, salon penceresi 160x180", {"pencereler": [pen("salon", "160x180")]}, "1",
     ["dis_karkas_140:", "pencere_olcu:P1", "cati_varyanti:Ç8801L"]),
])
def test_besinci_tur_cati_soruyla_bekler(s, metin, alan, cevap, degisiklik):
    """Beşinci tur: revizyonda çatı, sorulan pencereyle birlikte bekler ("Not aldım: çatı Ç8801L") ve cevapta uygulanır (cevap turunda son
    planın çatısına dönülüp çatı isteği sessizce düşüyordu)."""
    r01_k(s)
    k = s.yaz(metin, **alan)
    assert k.eylem == "sor" and k.mesaj.startswith("Not aldım: çatı Ç8801L"), (k.eylem, k.mesaj)
    k = s.yaz(cevap, niyet="diger")
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801L" and s.degisiklikler(k) == degisiklik, (k.eylem, k.mesaj)


def test_besinci_tur_hicbiri_bekleyen_catiyi_soyler(s):
    """"Hiçbiri" denince soruyla bekleyen çatı da uygulanmadı diye söylenir."""
    r01_k(s)
    assert s.yaz("çatı L olsun, salondaki sol taraftaki pencere 120x180", pencereler=[pen("salon", "120x180", duvar="sol")]).soru_alani == "okuma"
    k = s.dugme("q:okuma:0")
    assert k.soru_alani == "okuma_metin" and "öteki değişiklikleri de uygulamadım" in k.mesaj and s.plan["revizyon"] == 1


@pytest.mark.parametrize("metin, alan", [
    ("çatı eğimi dik olsun", {"bina_ozellikleri": {"Çatı Eğimi": "dik"}}),                  # şekil/eğim bilgi değil (tablo çizimle çelişirdi)
    ("çatı şekli kırma olsun", {"bina_ozellikleri": {"Çatı Şekli": "kırma"}}),
    ("çatı eğimi dik olsun, mutfak penceresi 120x120", {"bina_ozellikleri": {"Çatı Eğimi": "dik"}, "pencereler": [pen("mutfak", "120x120")]}),
    ("salonu yatak odasına dönüştürelim", {}),                                               # oda dönüşümü: "Anlayamadım" değil, yönlendirme
    ("salona pencere yapabilir misiniz?", {"pencereler": [pen("salon", islem="ekle")]}),    # odaya pencere yapmak eklemedir
])
def test_besinci_tur_yonlendirilir(s, metin, alan):
    r01_k(s)
    k = s.yaz(metin, **alan)
    assert k.eylem == "yonlendir" and s.plan["revizyon"] == 1, (k.eylem, k.mesaj)


def test_dorduncu_tur_set_acikken_kaynak_ve_kararsizlik(s):
    """Set açıkken iki kod seçim değildir (set yeniden sunulur; önce ilk kod seçiliyordu); "Ç8801K yerine Ç8801L" L'yi seçer."""
    assert s.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik").eylem == "secenek"
    k = s.yaz("Ç8801K mi Ç8801L mi olsun?", katalog_kodu="Ç8801K")
    assert k.eylem == "secenek" and "Önce listeden seçin" in k.mesaj and not s.plan
    k = s.yaz("Ç8801K yerine Ç8801L olsun", katalog_kodu="Ç8801K")
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801L"
