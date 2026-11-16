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


def onayla(s: Sohbet):
    return s.dugme(f"o:{s.plan['is_emri_no']}:{s.plan['revizyon']}")


def cati_seti(s: Sohbet):
    """İE-42 (D-94): "Ç8801" r01'i katalog çatısıyla çizer; "Onayla" çatı setini getirir (önce set plan seçilince, çizimden önce geliyordu)."""
    k = s.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik")
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 1 and s.plan["yapi"]["kod"] == "Ç8801", k.mesaj
    k = onayla(s)
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "cati_varyanti" and s.k.d["asama"] == "onay_bekliyor", k.mesaj
    return k


KARARSIZ = ", çatı K mı L mi bilemedim"            # İE-42: set plandan önce yalnız kararsız çatı sözüyle (İE-25 yolu)


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


def test_set_sunulurken_istek_saklanir_secimde_uygulanir(s, tmp_path):
    """CR1b: "Ç8801, <kararsız çatı>, mutfak penceresi 120x120" → çatı seti (istek saklanır, mesajda söylenir) → K düğmesi → r01 K + mutfak
    120/120. Önce düğmeden sonra LLM ipucuyla bütün pencereler soruluyordu ("Yaşam Alanı penceresini hangi ölçüye"). İE-42: çatı sözü
    yoksa set gelmez; r01 katalog çatısı ve pencereyle, onaydan sonra K seçilince pencere r02'de kalır."""
    k = s.yaz("Ç8801" + KARARSIZ + ", mutfak penceresi 120x120 olsun", katalog_kodu="Ç8801", yapi_turu="celik",
              pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "secenek" and K.CELIK_ISTEK_NOTU in k.mesaj
    k = s.dugme("s:{set}:Ç8801K")
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801K" and s.degisiklikler(k) == ["pencere_olcu:P5"]
    t = Sohbet(tmp_path / "ikinci")
    k = t.yaz("Ç8801, mutfak penceresi 120x120 olsun", katalog_kodu="Ç8801", yapi_turu="celik", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and t.plan["yapi"]["kod"] == "Ç8801" and t.degisiklikler(k) == ["pencere_olcu:P5"], k.mesaj
    assert onayla(t).eylem == "secenek"
    k = t.dugme("s:{set}:Ç8801K")
    assert k.eylem == "is_emri" and k.revizyon == 2 and t.degisiklikler(k) == ["pencere_olcu:P5", "cati_varyanti:Ç8801K"], k.mesaj


@pytest.mark.parametrize("cevap, alan, beklenen", [
    ("L olsun", {"niyet": "yeni_talep"}, "Ç8801L"),
    ("çatı K olsun", {"niyet": "yeni_talep", "katalog_kodu": "Ç8801"}, "Ç8801K"),      # LLM bağlamdan taban kodu yinelese de
    ("3", {"niyet": "diger"}, "Ç8801L"),
])
def test_cati_seti_yazili_cevap(s, cevap, alan, beklenen):
    """Çatı seti açıkken yazılı cevap: setin kendi örneği ("çatı K olsun"), harf ve numara. Önce taslakta kalan "Ç8801" katalog çatısını
    seçiyor, "3" "Anlayamadım" diyordu (PR-2a'dan kalma; kapanış incelemesinde bulundu). İE-42: set onaydan sonra; seçim r02."""
    cati_seti(s)
    k = s.yaz(cevap, **alan)
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == beklenen and k.revizyon == 2


def test_set_acikken_secim_olmayan_istek_set_yeniden_sunulur(s, tmp_path):
    """Plandan önceki sette (kararsız çatı sözüyle) seçim olmayan istek set yeniden sunulur, istek saklanır. Onaydan sonraki sette (İE-42)
    istek planın değişikliğidir: set kapanır, r02 katalog çatısı ve pencereyle, r01'in onayı düşer; r02'nin onayı çatıyı yeniden sorar."""
    s.yaz("Ç8801" + KARARSIZ, katalog_kodu="Ç8801", yapi_turu="celik")
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "secenek" and "Önce listeden seçin" in k.mesaj and K.CELIK_ISTEK_NOTU in k.mesaj
    k = s.yaz("2", niyet="diger")
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801K" and s.degisiklikler(k) == ["pencere_olcu:P5"]
    t = Sohbet(tmp_path / "ikinci")
    cati_seti(t)
    k = t.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and k.revizyon == 2 and t.plan["yapi"]["kod"] == "Ç8801" and t.degisiklikler(k) == ["pencere_olcu:P5"]
    assert k.mesaj.endswith("Bu değişiklik r01 onayınızı geçersiz kıldı. r02 için yeniden onay gerekir."), k.mesaj
    assert onayla(t).mesaj.startswith("Planınız onaylandı (r02). Şimdi çatıyı seçin.")


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
    cati_seti(s)
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
    """"çatı nasıl olacak?" değişiklik isteği değildir: set mesajında "isteğinizi işleyeceğim" notu yok, seçim r01 verir. İE-42 (hakem tur
    1, bulgu 4): seçimsiz çatı sözü planla gelince set plandan önce gelir (D-94: "ad ya da kararsız söz planla gelirse eski gibi set önce")."""
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
    """Set açıkken "Ç8801K'dan Ç8801L'ye geçmeyelim" L'yi seçmez: plandan önceki set yeniden sunulur; onaydan sonraki sette (İE-42)
    "Hangi çatı olsun?", plan r01 onay bekler."""
    assert s.yaz("Ç8801" + KARARSIZ, katalog_kodu="Ç8801", yapi_turu="celik").eylem == "secenek"
    k = s.yaz("Ç8801K'dan Ç8801L'ye geçmeyelim", katalog_kodu="Ç8801L")
    assert k.eylem == "secenek" and not s.plan
    t = Sohbet(s.k.path.parent / "ikinci")
    cati_seti(t)
    k = t.yaz("Ç8801K'dan Ç8801L'ye geçmeyelim", katalog_kodu="Ç8801L")
    assert k.eylem == "sor" and "Hangi çatı olsun?" in k.mesaj and t.plan["revizyon"] == 1 and t.k.d["asama"] == "onay_bekliyor"


def test_besinci_tur_dis140_oda_cumlesiyle_dusmez(s):
    """Beşinci tur: "dışlar 140'lık olsun ve oda kapıları beyaz olsun" birleşip dış 140 ilk planda sessizce düşüyordu; set yolunda da."""
    k = s.yaz("Ç8801K olsun, dışlar 140'lık olsun ve oda kapıları beyaz olsun", katalog_kodu="Ç8801K", yapi_turu="celik")
    assert k.eylem == "is_emri" and s.degisiklikler(k) == ["dis_karkas_140:"]
    t = Sohbet(s.k.path.parent / "ikinci")
    k = t.yaz("Ç8801 çelik, dışlar 140'lık olsun ve çalışma odası geniş olsun", katalog_kodu="Ç8801", yapi_turu="celik")
    assert k.eylem == "is_emri" and t.degisiklikler(k) == ["dis_karkas_140:"]           # İE-42: r01 katalog çatısıyla
    onayla(t)
    k = t.yaz("2", niyet="diger")
    assert k.eylem == "is_emri" and t.plan["yapi"]["kod"] == "Ç8801K" and t.degisiklikler(k) == ["dis_karkas_140:", "cati_varyanti:Ç8801K"]


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


@pytest.mark.parametrize("metin, alan, eylem", [
    ("Ç8801L'ye gerek yok", {"katalog_kodu": "Ç8801L"}, "secenek"),                     # altıncı tur: olumsuz biçimler (ters çatı çiziliyordu)
    ("Ç8801 çelik ev, Ç8801L hariç", {"katalog_kodu": "Ç8801"}, "secenek"),
    ("Ç8801L yok", {"katalog_kodu": "Ç8801L"}, "secenek"),
    ("Ç8801 olsun ama L çatıyı beğenmedik", {"katalog_kodu": "Ç8801L"}, "secenek"),
    ("Ç8801K olsun, salonun sol duvarı ve arka duvarındaki pencereler 120x120 olsun", {"katalog_kodu": "Ç8801K"}, "sor"),   # yanlış oda değil
    ("Ç8801K olsun, mutfak penceresinin eni 120 ve boyu 180 olsun", {"katalog_kodu": "Ç8801K"}, "sor"),
    ("Ç8801K olsun, mutfakta pencereyi 120x120 yapalım", {"katalog_kodu": "Ç8801K"}, "is_emri"),       # bulunma eki ekleme değil
])
def test_altinci_tur_ilk_plan(s, metin, alan, eylem):
    k = s.yaz(metin, yapi_turu="celik", **alan)
    assert k.eylem == eylem, (k.eylem, k.mesaj)
    if eylem == "is_emri":
        assert s.degisiklikler(k) == ["pencere_olcu:P5"]


@pytest.mark.parametrize("metin, alan, eylem, degisiklik", [
    ("L çatıyı beğenmiyoruz", {}, "sor", None),                                           # r2 L çiziliyordu
    ("katalog çatısını beğenmedik", {}, "sor", None),
    ("çatı rengi kırmızı ve şekli kırma olsun", {"bina_ozellikleri": {"Çatı Kaplama Rengi": "kırmızı", "Çatı Şekli": "kırma"}}, "yonlendir", None),
    ("çatı gri olsun, eğimi dik olsun", {"bina_ozellikleri": {"Çatı Kaplama Rengi": "gri", "Çatı Eğimi": "dik"}}, "yonlendir", None),
    ("mutfakta pencereyi 120x120 yapalım", {"pencereler": [pen("mutfak", "120x120")]}, "is_emri", ["pencere_olcu:P5"]),
    ("salon aynı kalsın ve mutfak penceresi 120x120 olsun", {"pencereler": [pen("mutfak", "120x120")]}, "is_emri", ["pencere_olcu:P5"]),
    ("çatı tek renk olsun", {"bina_ozellikleri": {"Çatı Kaplama Rengi": "tek renk"}}, "is_emri", []),
])
def test_altinci_tur_revizyon(s, metin, alan, eylem, degisiklik):
    """Altıncı tur: olumsuz biçimlerde çatı seçilmez; çatı şekli/eğimi ayrı cümlede de bilgi değil; "mutfakta pencereyi …" ölçü değişikliği;
    "salon aynı kalsın" ayrı cümle; "tek renk" şekil değil."""
    r01_k(s)
    k = s.yaz(metin, **alan)
    assert k.eylem == eylem, (k.eylem, k.mesaj)
    if degisiklik is not None:
        assert s.plan["revizyon"] == 2 and s.plan["yapi"]["kod"] == "Ç8801K" and s.degisiklikler(k) == degisiklik
    else:
        assert s.plan["revizyon"] == 1


def test_altinci_tur_hesaplanan_satir_ezilmez(s):
    """Çizimden hesaplanan tablo satırı (çatı eğimi, kapı sayısı) bayinin değeriyle ezilmez, özel isteğe yazılır; renk satırı yazılır."""
    k = s.yaz("Ç8801K olsun, çatı eğimi dik olsun, dış boya krem", katalog_kodu="Ç8801K", yapi_turu="celik",
              bina_ozellikleri={"Çatı Eğimi": "dik", "Dış Boya Rengi": "krem"})
    assert k.eylem == "is_emri"
    b = s.plan["bilgi"]
    assert "Çatı Eğimi" not in b["ozellikler"] and b["ozellikler"]["Dış Boya Rengi"] == "krem" and "Çatı Eğimi: dik" in b["ozel_istekler"]


def test_altinci_tur_cati_secenegi_olmayan_model(s):
    """Ç8201'in çatı varyantı yok: ilk planda "çatı L" isteği söylenir (sessizce düşüyordu), revizyonda yönlendirilir."""
    k = s.yaz("Ç8201 olsun, çatı L", katalog_kodu="Ç8201", yapi_turu="celik")
    assert k.eylem == "is_emri" and k.mesaj.startswith("Ç8201 modelinin çatı seçeneği yok") and s.plan["yapi"]["kod"] == "Ç8201"
    k = s.yaz("çatı L olsun")
    assert k.eylem == "yonlendir" and "çatı seçeneği yok" in k.mesaj and s.plan["revizyon"] == 1


def test_altinci_tur_set_acikken_olumsuz_bicim(s):
    assert s.yaz("Ç8801" + KARARSIZ, katalog_kodu="Ç8801", yapi_turu="celik").eylem == "secenek"
    k = s.yaz("L çatıyı beğenmedik", katalog_kodu="Ç8801L")
    assert k.eylem == "secenek" and not s.plan
    t = Sohbet(s.k.path.parent / "ikinci")                   # İE-42: onaydan sonraki sette soru, çatı seçilmez
    cati_seti(t)
    k = t.yaz("L çatıyı beğenmedik", katalog_kodu="Ç8801L")
    assert k.eylem == "sor" and "Hangi çatı olsun?" in k.mesaj and t.plan["revizyon"] == 1


@pytest.mark.parametrize("metin, alan, eylem", [
    ("odalar geniş ve mutfak penceresi 120x120 olsun", {"pencereler": [pen("mutfak", "120x120")]}, "yonlendir"),   # yedinci tur: düşüyordu
    ("banyo daha büyük ve mutfak penceresi 120x120 olsun", {"pencereler": [pen("mutfak", "120x120")]}, "yonlendir"),
    ("mutfak penceresi 120x120 olsun, dış cephe su geçirmez olsun", {"pencereler": [pen("mutfak", "120x120")]}, "yonlendir"),
    ("tuvalete 80x50 pencere yapalım", {"pencereler": [pen("banyo", islem="ekle")]}, "yonlendir"),  # vasistas değişiyordu
    ("salona pencereler yapalım", {}, "yonlendir"),
    ("salon aynı kalacak ve mutfak penceresi 120x120 olsun", {"pencereler": [pen("mutfak", "120x120")]}, "is_emri"),
])
def test_yedinci_tur_revizyon(s, metin, alan, eylem):
    r01_k(s)
    k = s.yaz(metin, **alan)
    assert k.eylem == eylem, (k.eylem, k.mesaj)
    if eylem == "is_emri":
        assert s.degisiklikler(k) == ["pencere_olcu:P5"]
    else:
        assert s.plan["revizyon"] == 1


@pytest.mark.parametrize("metin, alan, eylem, degisiklik, not_var", [
    ("Ç8801K olsun, odalar geniş ve dışlar 140'lık olsun", {"katalog_kodu": "Ç8801K"}, "is_emri", ["dis_karkas_140:"], True),   # oda isteği söylenir
    ("Ç8801K olsun, dış duvarlar kalın olsun ve mutfak penceresi 120x120 olsun", {"katalog_kodu": "Ç8801K"}, "sor", None, False),
    ("Ç8801K olsun, dışlar 140'lık sandviç panel olsun", {"katalog_kodu": "Ç8801K"}, "is_emri", [], True),        # güvenlik ağı: söylenir
    ("Ç8801K olsun, dışlar 140'lık olsun ve yüksekliği 300 olsun", {"katalog_kodu": "Ç8801K"}, "is_emri", [], True),
    ("Ç8801L olsun başka bir şeye gerek yok", {"katalog_kodu": "Ç8801L"}, "is_emri", [], False),               # set açılmıyor
    ("Ç8801K olsun harici tuvalet olsun", {"katalog_kodu": "Ç8801K"}, "is_emri", [], False),
    ("Ç8801K olsun, pencereler PVC olsun", {"katalog_kodu": "Ç8801K"}, "is_emri", [], True),                    # pencere isteği: söylenir
    ("Ç8801K olsun, pencereler PVC mi alüminyum mu?", {"katalog_kodu": "Ç8801K"}, "is_emri", [], False),       # soru: not yok
    ("Ç8801K olsun, odalar geniş olsun", {"katalog_kodu": "Ç8801K"}, "is_emri", [], True),                      # oda isteği: söylenir
    ("Ç8801K olsun, çatı şekli kırma olsun", {"katalog_kodu": "Ç8801K"}, "is_emri", [], True),                  # çatı şekli: söylenir
    ("Ç8801 çelik ev, dış cephe gri olsun", {"katalog_kodu": "Ç8801K", "bina_ozellikleri": {"Dış Cephe Rengi": "gri"}}, "is_emri", [], False),
    ("Ç8801K olsun, mutfak penceresi 120x120 ve oda sayısı aynı kalsın", {"katalog_kodu": "Ç8801K"}, "is_emri", ["pencere_olcu:P5"], False),
])
def test_yedinci_tur_ilk_plan(s, metin, alan, eylem, degisiklik, not_var):
    """Yedinci tur ve Lokman'ın kuralı (13.10): ilk planda değişiklik isteği taşıyan okunamayan cümle (pencere, dış 140, ekleme, çatı şekli,
    oda isteği) bayiye söylenir ("… isteğini otomatik uygulayamadım"); bilgi (renk) ve soru söylenmez; eksiltili oda isteği dış 140'ı
    düşürmez; "gerek yok" ve "harici" çatı seti açtırmaz."""
    k = s.yaz(metin, yapi_turu="celik", **alan)
    assert k.eylem == eylem, (k.eylem, k.mesaj)
    if degisiklik is not None:
        assert s.degisiklikler(k) == degisiklik
    assert ("otomatik uygulayamadım" in k.mesaj) is not_var, k.mesaj


def test_dorduncu_tur_set_acikken_kaynak_ve_kararsizlik(s):
    """Set açıkken iki kod seçim değildir (set yeniden sunulur; önce ilk kod seçiliyordu); "Ç8801K yerine Ç8801L" L'yi seçer. İE-42:
    onaydan sonraki sette de aynı okuma ("Hangi çatı olsun?", sonra r02 L)."""
    assert s.yaz("Ç8801" + KARARSIZ, katalog_kodu="Ç8801", yapi_turu="celik").eylem == "secenek"
    k = s.yaz("Ç8801K mi Ç8801L mi olsun?", katalog_kodu="Ç8801K")
    assert k.eylem == "secenek" and "Önce listeden seçin" in k.mesaj and not s.plan
    k = s.yaz("Ç8801K yerine Ç8801L olsun", katalog_kodu="Ç8801K")
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801L"
    t = Sohbet(s.k.path.parent / "ikinci")
    cati_seti(t)
    k = t.yaz("Ç8801K mi Ç8801L mi olsun?", katalog_kodu="Ç8801K")
    assert k.eylem == "sor" and "Hangi çatı olsun?" in k.mesaj and t.plan["revizyon"] == 1
    k = t.yaz("Ç8801K yerine Ç8801L olsun", katalog_kodu="Ç8801K")
    assert k.eylem == "is_emri" and t.plan["yapi"]["kod"] == "Ç8801L" and k.revizyon == 2


def test_celik_plan_mesaji_ekleri_soyler(s):
    """BK-08 madde 4 (13.10 canlı denemesi): çelik r01/r02'de görsel ve PDF metinle birlikte gider; mesaj "birkaç dakika içinde
    göndereceğim" diye söz vermez. Prefabrik metni ayrı yolda, değişmedi."""
    k = r01_k(s)
    assert "plan görseli ve PDF ektedir" in k.mesaj and "göndereceğim" not in k.mesaj and "Görselde" not in k.mesaj
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and k.revizyon == 2
    assert "plan görseli ve PDF ektedir" in k.mesaj and "göndereceğim" not in k.mesaj


# ── İE-42 · geometri hakemi tur 1 (14 Kasım 2026 gece): onaydan sonraki çatı seti ve plandan önceki set ─────────────────────────
@pytest.mark.parametrize("metin, alan", [
    ("Ç8801 olsun, kırma çatı olsun", {"varyantlar": [var("cati_degistir", "kırma çatı olsun")]}),
    ("Ç8801 olsun, kırma çatı olsun", {}),
    ("Ç8801 olsun, çatısı farklı olsun", {"varyantlar": [var("cati_degistir", "çatısı farklı olsun")]}),
    ("Ç8801 olsun, çatı seçeneklerini görelim", {}),
])
def test_hakem1_secimsiz_cati_sozu_set_once(s, metin, alan):
    """Bulgu 4: plan seçilirken seçimsiz çatı sözü (çatının adı, "farklı", "seçenekleri görelim") set getirir (D-94: ad ya da kararsız söz
    planla gelirse set önce); plan katalog çatısıyla çizilip istek düşmez."""
    k = s.yaz(metin, katalog_kodu="Ç8801", yapi_turu="celik", **alan)
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "cati_varyanti" and not s.plan, k.mesaj
    k = s.yaz("2", niyet="diger")
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801K" and k.revizyon == 1
    assert onayla(s).gerekce == K.PLAN_ONAYI                                  # çatı seçildi: onayda yeniden sorulmaz


def test_hakem1_alan_setinde_saklanan_cati_sozu_set_getirir(s):
    """Bulgu 4: "88 m² 2+1 tek kat çelik, kırma çatı olsun" → alan seti (istek saklanır) → Ç8801 düğmesi → çatı seti (r01 çizilmez)."""
    k = s.yaz("88 m² 2+1 tek kat çelik, kırma çatı olsun", alan_m2=88, oda_programi="2+1", yapi_turu="celik", kat_sayisi=1,
              varyantlar=[var("cati_degistir", "kırma çatı olsun")])
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "alan", k.mesaj
    k = s.dugme("s:{set}:Ç8801")
    assert k.eylem == "secenek" and s.k.d["secenek_seti"]["tur"] == "cati_varyanti" and not s.plan, k.mesaj


def test_hakem1_cati_rengi_bilgi_set_getirmez(s):
    """Renk ve malzeme sözü çatı seçimi istemez (bilgi): r01 katalog çatısıyla, set onaydan sonra."""
    k = s.yaz("Ç8801 olsun, çatı rengi antrasit olsun", katalog_kodu="Ç8801", yapi_turu="celik")
    assert k.eylem == "is_emri" and s.plan["yapi"]["kod"] == "Ç8801", k.mesaj
    assert onayla(s).eylem == "secenek"


@pytest.mark.parametrize("metin, alan", [
    ("tamam", {"niyet": "yeni_talep"}),
    ("bakalım", {"niyet": "yeni_talep", "katalog_kodu": "Ç8801", "yapi_turu": "celik"}),
])
def test_hakem1_celik_iceriksiz_mesaj_cati_sorar(s, metin, alan):
    """Bulgu 5: onaydan sonraki sette içeriksiz "yeni talep" okuması konuşmayı sıfırlamaz: "Hangi çatı olsun?"."""
    cati_seti(s)
    k = s.yaz(metin, **alan)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?") and s.k.d.get("cati_adimi") and s.plan["revizyon"] == 1, k.mesaj


def test_hakem1_celik_katalog_catisi_ve_bilgi(s):
    """Bulgu 2: katalog çatısı + sevk adresi: onay o an kaydedilmez; plan antet bilgisiyle r02, çatı seçilmiş."""
    cati_seti(s)
    k = s.yaz("Ç8801 olsun, sevk adresi Deneme İlçesi olsun", katalog_kodu="Ç8801", musteri={"sevk_adresi": "Deneme İlçesi"})
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801" and K.PLAN_ONAYI not in k.gerekce, k.mesaj
    assert (s.plan.get("bilgi") or {}).get("sevk_adresi") == "Deneme İlçesi" and k.mesaj.startswith("Çatı: Beşik + cumba (Ç8801).")
    assert onayla(s).gerekce == K.PLAN_ONAYI


def test_hakem1_celik_yalniz_musteri_bilgisi(s):
    """Bulgu 3: set açıkken yalnız müşteri adı: soru değil, plan bilgiyle r02."""
    cati_seti(s)
    k = s.yaz("müşteri Ayşe Deneme", musteri={"ad": "Ayşe Deneme"})
    assert k.eylem == "is_emri" and k.revizyon == 2 and not k.mesaj.startswith("Hangi çatı"), k.mesaj


def test_hakem1_celik_onay_sozunde_cati(s):
    """Bulgu 8: "çatı K olsun, onaylıyorum" (LLM "onay") çatıyı seçer: r02 K."""
    cati_seti(s)
    k = s.yaz("çatı K olsun, onaylıyorum", niyet="onay")
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


def test_hakem1_celik_yalniz_cati_degisince_onay_dusme_notu_yok(s):
    """Bulgu 7: K + antet bilgisi (plan geometrisi yalnız çatıda değişir): "Plan aynı", "onayınızı geçersiz kıldı" yazılmaz; bilgi r02'de."""
    cati_seti(s)
    k = s.yaz("çatı K olsun, sevk adresi Deneme İlçesi", musteri={"sevk_adresi": "Deneme İlçesi"})
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj
    assert "Plan aynı" in k.mesaj and "geçersiz kıldı" not in k.mesaj and (s.plan.get("bilgi") or {}).get("sevk_adresi") == "Deneme İlçesi"


def test_hakem1_celik_cati_ve_okunamayan_istek_secimi_dusurmez(s):
    """Bulgu 6: K + okunamayan istek ("dışlar 140 olmasın": olumsuz, soru): çatı "seçildi" sayılıp düşmez; plan değişmez, set açık kalır,
    bayiye çatı seçiminin kaydedilmediği yazılır; sonraki "Onayla" çatıyı yine sorar."""
    cati_seti(s)
    st = s.k.d["secenek_seti"]
    k = s.yaz("çatı K olsun, dışlar 140 olmasın")
    assert k.eylem == "cevapla" and k.mesaj.endswith("Çatı seçiminizi (Ç8801-K) kaydetmedim; çatıyı yeniden seçin."), k.mesaj
    assert s.k.d.get("cati_adimi") and not s.k.d.get("cati_secilen") and s.k.d["secenek_seti"]["durum"] == "acik"
    assert [b["id"] for b in k.butonlar] == [f"s:{st['id']}:{c}" for c in ("Ç8801", "Ç8801K", "Ç8801L")] and s.plan["revizyon"] == 1
    k = s.dugme("s:{set}:Ç8801K")
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


# ── İE-42 · geometri hakemi tur 2 (14 Kasım 2026 gece) ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["Ç8801K'nın fiyatı ne kadar?", "K çatı daha mı pahalı?"])
def test_hakem2_celik_soru_cumlesindeki_kod_secim_degil(s, metin):
    """O2: soru cümlesindeki kod ya da etiket çatı seçimi değildir: plan çizilmez, set açık kalır."""
    cati_seti(s)
    k = s.yaz(metin, niyet="soru")
    assert k.eylem != "is_emri" and s.plan["revizyon"] == 1 and not s.k.d.get("cati_secilen") and s.k.d.get("cati_adimi"), k.mesaj


def test_hakem2_celik_eskiyen_cati_secimi_onayda_sorulur(s):
    """O3: çatı seçimi okuma sorusuyla bekledi, bayi soruyu cevaplamadan başka istek yazdı (r02 katalog çatısıyla): r02'nin onayında
    çatı seti yeniden gelir (eskiyen seçim çatı adımını atlatmaz)."""
    cati_seti(s)
    k = s.yaz("çatı L olsun, salondaki pencere 120x120 olsun", pencereler=[pen("salon", "120x120")])
    assert k.eylem == "sor", k.mesaj
    k = s.yaz("mutfak penceresi 120x120 olsun", pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801", k.mesaj
    k = onayla(s)
    assert k.eylem == "secenek" and k.gerekce.startswith("plan onayından sonra çatı seti") and s.k.d.get("cati_adimi"), k.mesaj


@pytest.mark.parametrize("metin, alan", [("100 m2 olsun", {"alan_m2": 100}), ("3+1 olsun", {"oda_programi": "3+1"})])
def test_hakem2_celik_talep_degisince_yapi_turu_kalir(tmp_path, metin, alan):
    """O6: yalnız kodla seçilen çelik evde (taslakta yapı türü yok) talep değişikliği yeni talepte çelik kalır (prefabrik öneri gelmez)."""
    s = Sohbet(tmp_path)
    k = s.yaz("Ç8801", katalog_kodu="Ç8801")
    assert k.eylem == "is_emri", k.mesaj
    assert onayla(s).eylem == "secenek"
    k = s.yaz(metin, niyet="revizyon", **alan)
    assert s.k.d["taslak"].get("yapi_turu") == "celik" and "prefabrik" not in k.mesaj, k.mesaj
    assert not s.k.d.get("cati_adimi") and K.PLAN_ONAYI not in k.gerekce


@pytest.mark.parametrize("metin, kod", [("2 olsun, mutfak penceresi 120x120 olsun", "Ç8801K"),
                                        ("ikinci çatı olsun, mutfak penceresi 120x120 olsun", "Ç8801K")])
def test_hakem2_celik_numara_baska_cumleyle(s, metin, kod):
    """O7: çelikte numara ya da sıra sözü başka cümleyle birlikte de setin numarasıdır: r02 o çatıyla ve pencereyle."""
    cati_seti(s)
    k = s.yaz(metin, pencereler=[pen("mutfak", "120x120")])
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == kod, k.mesaj
    assert k.mesaj.startswith("Çatı: Beşik + cumba, doğu ucu kırma (Ç8801-K).") and "120/120" in k.mesaj, k.mesaj


def test_hakem2_celik_numara_ve_okunamayan_istek(s):
    """O7 + Y1: "1 olsun, dış kapı çelik olsun": çatı seçimi okunur, istek otomatik yapılamaz; plan değişmez, set açık kalır ve bayiye
    çatı seçiminin kaydedilmediği yazılır (onay kaydedilmez)."""
    cati_seti(s)
    k = s.yaz("1 olsun, dış kapı çelik olsun", dis_kapi="çelik", varyantlar=[var("kapi_degistir", "dış kapı çelik olsun")])
    assert K.PLAN_ONAYI not in k.gerekce and k.mesaj.endswith("Çatı seçiminizi (Ç8801) kaydetmedim; çatıyı yeniden seçin."), k.mesaj
    assert s.k.d.get("cati_adimi") and s.k.d["secenek_seti"]["durum"] == "acik" and s.plan["revizyon"] == 1


@pytest.mark.parametrize("metin", ["L olsun onaylıyorum", "üçüncü çatı olsun, onaylıyorum"])
def test_hakem2_celik_virgulsuz_onay_ve_sira_sozu(s, metin):
    """D4: onay sözü virgülsüz ("L olsun onaylıyorum") ya da sıra sözüyle gelince de seçim okunur: r02 L."""
    cati_seti(s)
    k = s.yaz(metin, niyet="onay")
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801L", k.mesaj


# ── İE-42 · geometri hakemi üçüncü tur (14 Kasım 2026 gecesi): istek bayinin sözünden, LLM'in alanından değil (K18) ─────────────────────
@pytest.mark.parametrize("metin", ["1 olsun, kapılar ahşap olsun", "1 olsun, banyoya küvet koyalım", "1 olsun, mutfak duvarını kaldırın",
                                   "1 olsun, yükseklik 300 olsun", "Ç8801 olsun, iç kapılar ahşap olsun"])
def test_hakem3_celik_evin_catisi_ve_sozdeki_istek(s, metin):
    """Y1 (genel): katalog çatısıyla aynı mesajdaki istek LLM'in okuduğu bir alan taşımasa da istektir. Onay kaydedilmez (mühendis
    kontrolüne gitmez), set açık kalır, bayiye isteğin durumu ve çatı seçiminin kaydedilmediği yazılır."""
    cati_seti(s)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan") and s.plan["revizyon"] == 1, k.mesaj
    assert k.mesaj.endswith("Çatı seçiminizi (Ç8801) kaydetmedim; çatıyı yeniden seçin."), k.mesaj
    assert s.k.d.get("cati_adimi") and s.k.d["secenek_seti"]["durum"] == "acik"


@pytest.mark.parametrize("metin, alan", [("1 olsun, salon 30 m2 olsun", {"ozel_istekler": ["salon 30 m2"], "alan_m2": 30}),
                                         ("tamam", {"niyet": "yeni_talep", "katalog_kodu": "Ç8801", "alan_m2": 88, "yukseklik_cm": 280})])
def test_hakem3_celik_oda_m2_si_ve_yanki_talep_degil(s, metin, alan):
    """Bulgu 1, 10: oda m²'si ve LLM'in yinelediği değerler talebi değiştirmez (konuşma sıfırlanmaz, plan düşmez)."""
    cati_seti(s)
    k = s.yaz(metin, **alan)
    assert "Talebiniz değişti" not in k.mesaj and s.plan["revizyon"] == 1 and s.k.d.get("cati_adimi"), k.mesaj


# ── İE-42 · geometri hakemi dördüncü tur (15 Kasım 2026 gecesi) ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["1 olsun, prefabrik olsun", "1 olsun, ev 2 katlı olsun"])
def test_hakem4_celik_yapi_ve_kat_sozu_talep_degisikligi(s, metin):
    """B2: çelik evde "prefabrik olsun" ve "2 katlı olsun" talebi değiştirir (LLM alanı boşken de): onay kaydedilmez, mühendise gitmez."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.mesaj.startswith("Talebiniz değişti; bu değişiklik r01 onayınızı geçersiz kıldı."), k.mesaj
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan")


@pytest.mark.parametrize("metin", ["1 olsun, onay veriyoruz", "1 olsun abi", "kendi çatısı olsun", "aynı kalsın", "1 olsun, müşteri beğendi",
                                   "1 olsun, çelik olsun"])
def test_hakem4_celik_onay_ve_nezaket_sozu_secimdir(s, metin):
    """O-B, D-D: çelikte onay ve nezaket sözü, evin kendi çatısı ve evin kendi yapı sözü seçimdir: r01 onaylanır (mühendis kontrolü)."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and s.k.d.get("onaylanan"), k.mesaj


# ── İE-42 · geometri hakemi tur 5 (15 Kasım 2026 gecesi) ──────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["mevcut çatıdan farklı olsun", "1 olsun, mevcut çatıdan farklı olsun", "1 olsun, kırmayı alın",
                                   "1 olsun, kırmada kalalım", "1 olsun, teklifte K de olsun", "1 olsun, kırma gelsin", "1 olsun, L gelsin",
                                   "1 olsun, K de gelsin", "1 olsun, cumba sağ olsun", "1 olsun, kalkan sağ olsun", "1 olsun, L tipi olsun",
                                   "1 olsun, başka çatıya da bakalım"])
def test_hakem5_celik_cati_sozu_secimle_celisir(s, metin):
    """Y1–Y3: çelikte "farklı çatı", seçimle çelişen çatı adı ya da etiketi, "sağ olsun" yön sözü onay kaydettirmez, mühendise gitmez."""
    cati_seti(s)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and not s.k.d.get("onaylanan") and s.plan["revizyon"] == 1, k.mesaj


@pytest.mark.parametrize("metin", ["1 olsun, çelik olmasın prefabrik olsun", "çelik istemiyoruz prefabrik olsun"])
def test_hakem5_celik_yapi_olumsuzu(s, metin):
    """O1: "çelik olmasın prefabrik olsun" prefabriğe geçiştir: talep değişti."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.mesaj.startswith("Talebiniz değişti; bu değişiklik r01 onayınızı geçersiz kıldı."), k.mesaj
    assert s.k.d["taslak"]["yapi_turu"] == "prefabrik"


@pytest.mark.parametrize("metin, kod", [("K ile devam edelim", "Ç8801K"), ("K'yı alın", "Ç8801K"), ("2 yi alın", "Ç8801K"),
                                        ("L olsun teşekkürler", "Ç8801L"), ("kendi çatısıyla devam edelim", "Ç8801"),
                                        ("1 olsun, başka değişiklik yok", "Ç8801"), ("1 olsun, son halini onaylıyoruz", "Ç8801")])
def test_hakem5_celik_devam_sozu_secimdir(s, metin, kod):
    """D1, O2: devam ve alma sözlü etiket, numara ve "kendi çatısı" seçimdir; "başka değişiklik yok" istek değildir."""
    cati_seti(s)
    k = s.yaz(metin)
    if kod == "Ç8801":
        assert k.gerekce == K.PLAN_ONAYI and s.k.d.get("onaylanan"), k.mesaj
    else:
        assert k.eylem == "is_emri" and s.plan["revizyon"] == 2 and s.plan["yapi"]["kod"] == kod, k.mesaj


# ── İE-42 · geometri hakemi altıncı tur (15 Kasım 2026 gece) ──────────────────────────────────────────────────────────────────────────

_MUTFAK = dict(pencereler=[pen("mutfak", "120x120")])


@pytest.mark.parametrize("metin", ["K olsun mutfak penceresi 120x120", "2 olsun mutfak penceresi 120x120 olsun",
                                   "K olsun ama mutfak penceresi 120x120 olsun"])
def test_hakem6_celik_virgulsuz_secim_ve_istek(s, metin):
    """Y1 çelikte; D2: çatıyla gelen istekte de PDF başlığı model adı ve m²'yle başlar (İE-20 PR-10, C5)."""
    cati_seti(s)
    k = s.yaz(metin, **_MUTFAK)
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj
    assert [d["op"] for d in s.plan["yapi"]["degisiklikler"]] == ["pencere_olcu", "cati_varyanti"], s.plan["yapi"]["degisiklikler"]
    assert s.plan["talep"]["metin"] == ("Ç8801-K (Beşik + cumba, doğu ucu kırma) · 88 m², 2+1. "
                                        "Uygulanan: Mutfak penceresi 120/180 (arka cephe) → 120/120."), s.plan["talep"]["metin"]


def test_hakem6_celik_istek_cumlesinde_cati_numarasi_sorulur(s):
    """Y1 çelikte: "çatı 3 mutfak penceresi 120x120" çatı ve istek; seçim okunmadı: sorulur, öteki isteğin uygulanmadığı yazılır."""
    cati_seti(s)
    k = s.yaz("çatı 3 mutfak penceresi 120x120", **_MUTFAK)
    assert k.mesaj.startswith("Hangi çatı olsun?") and "öteki isteği uygulamadım" in k.mesaj, k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik"


def test_hakem6_celik_oda_sira_sayisi_cati_degil(s):
    """Y2 çelikte: "2. yatak odası penceresi …" çatı seçimi değildir. Tur 7 (Y1, Y2): "N." numaralı listenin maddesi de olabilir; tek
    başına "N." ve ardından istek: çatı sorulur (set açık, seçim kaydedilmez), öteki isteğin uygulanmadığı yazılır."""
    cati_seti(s)
    k = s.yaz("2. yatak odası penceresi 120x120 olsun", pencereler=[pen("yatak odası 2", "120x120")])
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?") and "öteki isteği uygulamadım" in k.mesaj, k.mesaj
    assert not s.k.d.get("cati_secilen") and s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik", k.mesaj


@pytest.mark.parametrize("metin", ["2 olsun eline sağlık", "2 olsn"])
def test_hakem6_celik_whatsapp_yazimi_secimdir(s, metin):
    """O2 çelikte: "2 olsun eline sağlık" Lokman'a yönlendirilmez; çatı K seçilir (r02)."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


def test_hakem6_celik_cati_basliginda_olcu_farki(s):
    """D1: ölçü değişen plandan sonra çatı seçilince PDF başlığında ölçü farkı ve taslak notu kalır."""
    k = s.yaz("Ç8801", katalog_kodu="Ç8801", yapi_turu="celik")
    s.k.llm_degisiklik = {"durum": "tamam", "germe": True, "islemler": [
        {"tur": "oda_buyut", "aciklik": None, "adaylar": [], "en": None, "yuk": None, "cati_kodu": None,
         "alinti": "banyoyu arkaya 30 cm büyütelim", "mahal": "Banyo", "yon": "K", "cm": 30}]}
    k = s.yaz("banyoyu arkaya 30 cm büyütelim")
    s.k.llm_degisiklik = None
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2, k.mesaj
    assert onayla(s).eylem == "secenek"
    k = s.yaz("K olsun")
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 3 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj
    m = s.plan["talep"]["metin"]
    assert m.startswith("Ç8801-K (Beşik + cumba, doğu ucu kırma) · 88 m², 2+1. Uygulanan: Banyo arkaya 30 cm büyütüldü.") and m.endswith(
        "Ölçüler değiştiği için plan taslaktır; mühendis kontrolünde kesinleşir."), m


# ── İE-42 · geometri hakemi yedinci tur (15 Kasım 2026 gece) ──────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("metin", ["K olsun eline sağlık mutfak penceresi 120x120 olsun", "K olsun, eline sağlık mutfak penceresi 120x120 olsun",
                                   "mutfak penceresi 120x120 olsun 2 olsun", "mutfak penceresi 120x120 olsun çatı da 2 olsun",
                                   "mutfak penceresi 120x120 olsun ikinci çatı olsun"])
def test_hakem7_celik_secim_ve_istek(s, metin):
    """D3: teşekkürle başlayan istek Lokman'a yönlendirilmez; Y4: istekten sonra virgülsüz gelen seçim okunur. Çatı K, pencere aynı r02'de."""
    cati_seti(s)
    k = s.yaz(metin, **_MUTFAK)
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj
    assert [d["op"] for d in s.plan["yapi"]["degisiklikler"]] == ["pencere_olcu", "cati_varyanti"], s.plan["yapi"]["degisiklikler"]


@pytest.mark.parametrize("metin", ["1. yatak odası 1 penceresi 120x120 olsun\n2. mutfak penceresi 120x120 olsun",
                                   "2. Yatak odası 1 penceresi 120x120 olsun", "2 olsun banyo", "3 olsun yatak odası",
                                   "1 olsun, daha ucuz olsun", "1 olsun, ikisi de olsun", "Plan aynı kalsın"])
def test_hakem7_celik_kararsiz_soz_sorulur(s, metin):
    """Y1, Y2 (numaralı liste), Y3 (devrik sayı), O1 (ucuz, ikisi), O2 (plan aynı kalsın) çelikte: "Hangi çatı olsun?", onay ve seçim
    kaydedilmez. Önce bayiye "Çatı seçiminizi (Ç8801-K) kaydetmedim" gidiyordu ya da r01 onaylanıyordu."""
    cati_seti(s)
    k = s.yaz(metin, **_MUTFAK)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj
    assert "Ç8801-K" not in k.mesaj.split("\n\n")[-1], k.mesaj


def test_hakem7_celik_sira_sozu_secimdir(s):
    """D1 çelikte: "2. sıradaki olsun" seçimdir."""
    cati_seti(s)
    k = s.yaz("2. sıradaki olsun")
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


# ── İE-42 · geometri hakemi sekizinci tur (15 Kasım 2026 gece) ────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["Son olarak, mutfak penceresi 120x120 olsun", "İlk olarak, mutfak penceresi 120x120 olsun"])
def test_hakem8_celik_son_olarak_cati_secmez(s, metin):
    """Y2 çelikte: "Son olarak, …" isteği çatı seçmez (tur 7'de Ç8801-L çiziliyordu); pencere evin çatısıyla r02'de, çatı r02'nin onayında
    yeniden sorulur."""
    cati_seti(s)
    k = s.yaz(metin, **_MUTFAK)
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2 and s.plan["yapi"]["kod"] == "Ç8801", k.mesaj
    assert s.k.d["secenek_seti"]["durum"] == "eskidi" and not s.k.d.get("cati_secilen") and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["mutfak penceresi 120x120 olsun 2 de", "mutfak penceresi 120x120 olsun ikinciye de"])
def test_hakem8_celik_eksiltili_devam_cati_secmez(s, metin):
    """Y1 çelikte: eksiltili devam çatı seçmez; okunamayan istek bayiye sorulur, çatı ve onay kaydedilmez."""
    cati_seti(s)
    k = s.yaz(metin, **_MUTFAK)
    assert s.plan["yapi"]["kod"] == "Ç8801" and not s.k.d.get("cati_secilen") and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin, al", [("1 olsun, hangisi ucuzsa", {}), ("1 olsun, haber vereceğiz", {}), ("2 olsun, ikisinden biri", {}),
                                       ("Son haliyle onaylıyoruz", dict(niyet="onay")), ("Son haliyle kalsın", {}),
                                       ("Müşteri karar verince haber vereceğiz", {})])
def test_hakem8_celik_kararsiz_soz_sorulur(s, metin, al):
    """O3, O4, Y3 çelikte: erteleme, seçimi bize bırakan söz ve "son haliyle" sorulur; onay ve seçim kaydedilmez."""
    cati_seti(s)
    k = s.yaz(metin, **al)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["Plan aynı kalsın çatı K olsun", "K'da kalalım"])
def test_hakem8_celik_secim_okunur(s, metin):
    """D1 çelikte: plan sözü seçim cümlesine virgülsüz bağlansa da çatı seçilir; "K'da" eki eksiltili "da" değildir."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


# ── İE-42 · geometri hakemi dokuzuncu tur (15 Kasım 2026 sabaha karşı) ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin, al", [("mutfak penceresi 120x120 olsun, çatı 2 de olsun", _MUTFAK),
                                       ("mutfak penceresi 120x120 olsun, K de olsun", _MUTFAK),
                                       ("mutfak penceresi 120x120 olsun, çatı L de olsun", _MUTFAK),
                                       ("Peki 2 olsun banyo 2 tane", {}), ("1 olsun, müşteri onaylarsa", {}), ("1 olsun, uygunsa", {}),
                                       ("2 olsun, montaj tarihi ve çatıyı haber veririz", {}), ("Biz de 2 diyoruz", {})])
def test_hakem9_celik_kararsiz_soz_sorulur(s, metin, al):
    """Y-1, O-2, Y-2, Y-3, Y-4 çelikte: eksiltili çatı sözü, önekli devrik sayı, koşullu söz ve çatıyı da anan haber sorulur; onay ve
    seçim kaydedilmez."""
    cati_seti(s)
    k = s.yaz(metin, **al)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


# ── İE-42 · geometri hakemi onuncu tur (15 Kasım 2026 sabaha karşı) ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["2 olsun, müşteri onaylayınca", "1 olsun, müşteri onaylayacak", "1 olsun, müşteri onayından sonra",
                                   "Evin kendi çatısı olsun, müşteri onayından sonra", "2'yi seçtik banyo 2 tane", "Çatıyı siz bildirin"])
def test_hakem10_celik_ertelenen_onay_ve_secim_sozu_sorulur(s, metin):
    """Y-1, Y-2, O-4 çelikte: ertelenen onay sözü, ekli sayıyla seçim ve çatıyı bize bırakan söz sorulur; onay ve seçim kaydedilmez."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


# ── İE-42 · geometri hakemi on birinci tur (15 Kasım 2026 sabaha karşı) ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["2 olsun, müşteri kabul edince", "L olsun, kredi çıkınca", "2 olsun, stok varsa", "2 olsun, fiyat makulse",
                                   "K mı olsun, müşteri Ayşe Kaya"])
def test_hakem11_celik_kosullu_zamanli_ve_soru_bicimli_secim_sorulur(s, metin):
    """Y-1, Y-2, Y-3 çelikte: zamana ya da koşula bağlı seçim ve soru biçimli seçim sorulur; çatı ve onay kaydedilmez."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin, kod", [("Çatıya gelince L olsun", "Ç8801L"), ("Çatıya gelince, K olsun", "Ç8801K")])
def test_hakem11_celik_catiya_gelince_secimdir(s, metin, kod):
    """D-1 çelikte: "Çatıya gelince" söylem sözüdür; tur 10 kodunda istek diye Lokman'a iletiliyordu, çatı kaydedilmiyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == kod, k.mesaj


@pytest.mark.parametrize("metin", ["1 olsun, teklifi bekliyoruz", "1 olsun, onayımızdır"])
def test_hakem11_celik_acik_onay_soruya_donmez(s, metin):
    """O-1, O-2 çelikte: açık onay ve "teklifi bekliyoruz" onaydır."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


# ── İE-42 × BK-29 tur 9 (main c0a31afb, 15 Kasım 2026): kod ve müşteri adı çatı setinde ───────────────────────────────────────────────
@pytest.mark.parametrize("metin, kod", [("Ç8801 olsun, müşteri Ayşe Kaya", "Ç8801"), ("Ç8801K olsun, müşteri Ayşe Kaya", "Ç8801K")])
def test_bk29_tur9_celik_kod_ve_musteri_adi_cati_setinde(s, metin, kod):
    """Çelikte de: kod + "müşteri <ad>" çatıyı seçer, ad plana girer, plan r02; onay sessizce kaydedilmez, r02'nin Onayla'sı onaylar."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == kod, k.mesaj
    assert not s.k.d.get("onaylanan") and (s.k.d["taslak"].get("musteri") or {}).get("ad") == "Ayşe Kaya"
    k = onayla(s)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 2, k.mesaj


# ── İE-42 · geometri hakemi on ikinci tur (15 Kasım 2026 sabaha karşı) ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["1 olsun, onaylayamadık", "Evin kendi çatısı olsun, onaylatmadık", "1 olsun, onaylamak yok",
                                   "1 olsun, onaylamak istemiyoruz", "1 olsun, onay yok", "1 olsun, müşteri onay vermedi",
                                   "1 olsun, netleşince gönderin", "K olsun, kapora yatınca gönderin", "2 olsun, kredi çıkınca gönderin",
                                   "K olsun, stok varsa gönderin"])
def test_hakem12_celik_olumsuz_onay_ve_bagli_secim_sorulur(s, metin):
    """Y-1, Y-2, Y-3, O-4, O-5 çelikte: olumsuz onay, emirle biten "netleşince", müşterinin ya da paranın zamanı ve "stok varsa" + emir
    sorulur; tur 11 kodunda onay kaydediliyor (plan teknik kontrole gidiyordu) ya da istek Lokman'a iletiliyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin, kod", [("Ç8801-K olsun, müşteri Nursen Kaya", "Ç8801K"), ("K olsun, K'nın fiyatı ne olacak?", "Ç8801K"),
                                        ("L olsun, L'nin fiyatı ne olacak?", "Ç8801L")])
def test_hakem12_celik_acik_secim_soruya_donmez(s, metin, kod):
    """O-1, O-2 çelikte: "-rsen" adlı müşteri ve seçilen çatının fiyat sorusu açık seçimi soruya çevirmez."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == kod, k.mesaj


# ── İE-42 · geometri hakemi on üçüncü tur (15 Kasım 2026 sabah) ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["1 olsun, onaylamaktan vazgeçtik", "Evin kendi çatısı olsun, onaylamaktan vazgeçtik",
                                   "Ç8801 olsun, onaylamaktan vazgeçtik", "K olsun, onaylamaktan vazgeçtik", "1 olsun, K'nın çatısı mı olsa?",
                                   "1 olsun, Ç8801-K'nın çatısı mı olsa?", "Evin kendi çatısı olsun, L'nin çatısı mı olsa?",
                                   "Ç8801 olsun, Ç8801-L'nin çatısı mı olsa?", "K'nın çatısı mı olsun, müşteri Ayşe Kaya", "K olsun, Fiyat Uygunsa",
                                   "K olsun, ödeme bitince gönderin"])
def test_hakem13_celik_ilgi_ekli_secim_sorusu_ve_cekince_sorulur(s, metin):
    """Yüksek-1, Yüksek-2, Orta-2, Orta-4 çelikte: on ikinci tur kodunda "onaylamaktan vazgeçtik" ve ilgi ekli seçim sorusu onay
    kaydediyordu (plan teknik kontrole gidiyordu) ya da sorulan çatı çiziliyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["Ç8801 olsun, onaylıyoruz başka değişiklik istemiyoruz", "1 olsun, onaylıyoruz başka değişiklik istemiyoruz"])
def test_hakem13_celik_olumlu_onay_soruya_donmez(s, metin):
    """Orta-1 çelikte: "başka değişiklik istemiyoruz" onayı olumsuzlamaz."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


# ── İE-42 · geometri hakemi on dördüncü tur (15 Kasım 2026 sabah) ────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["1 olsun, bilemedik", "1 olsun, karar veremedik", "Ç8801 olsun, karar veremedik", "1 olsun, emin değiliz",
                                   "1 olsun. Emin değiliz.", "Ç8801 olsun, emin değiliz", "1 olsun, onay için emin değiliz",
                                   "Evin kendi çatısı olsun, emin değilim", "Evin kendi çatısı olsun, onaydan emin değiliz",
                                   "1 olsun, bilmiyoruz", "K olsun, emin değiliz", "K olsun, bilemedik", "K olsun, karar veremedik",
                                   "K olsun, onay için emin değiliz", "K olsun, çatıda değişiklik istemiyoruz", "Çatıda değişiklik istemiyoruz",
                                   "1 olsun, onaylamaya hazır değiliz", "1 olsun, onay isteğimize cevap vermediler",
                                   "K olsun, onay sorunu çözülmedi"])
def test_hakem14_celik_kararsizlik_ve_olumsuz_onay_sorulur(s, metin):
    """Yüksek-1, Orta-4, Düşük çelikte: on üçüncü tur kodunda "1 olsun, bilemedik", "emin değiliz", "karar veremedik" onay kaydediyordu
    (plan teknik kontrole gidiyordu); "K olsun, emin değiliz" ve "K olsun, çatıda değişiklik istemiyoruz" r02 K çiziyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin, kod", [("K olsun, K'nın eğimi kaç olacak?", "Ç8801K"), ("L olsun, L'nin rengi ne olacak?", "Ç8801L")])
def test_hakem14_celik_acik_secim_soruya_donmez(s, metin, kod):
    """Orta-3 çelikte: seçilen çatının özelliğini soran ilgi eki açık seçimi soruya çevirmez."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == kod, k.mesaj


# ── İE-42 · geometri hakemi on beşinci tur (15 Kasım 2026 sabah) ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["1 olsun. K mı daha iyi?", "1 olsun. K'nın şekli mi daha iyi?", "Ç8801 olsun. L mi daha iyi?"])
def test_hakem15_celik_karsilastirma_sorusu_sorulur(s, metin):
    """Y-1 çelikte: on dördüncü tur kodunda çatıları kıyaslayan soru onay kaydediyordu (plan teknik kontrole gidiyordu)."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["Ç8801 olsun, onaylıyoruz başka söyleyeceğimiz yok", "1 olsun, onaylıyoruz başka diyeceğimiz yok"])
def test_hakem15_celik_olumlu_onay_soruya_donmez(s, metin):
    """O-4 çelikte: araya söz giren "başka söyleyeceğimiz yok" onayı olumsuzlamaz."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


# ── İE-42 · geometri hakemi on altıncı tur (15 Kasım 2026 sabah) ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["1 olsun, hangisi daha iyi?", "1 olsun, ikincisi daha mı iyi?", "1 olsun, karar yok",
                                   "1 olsun, son karar müşterinin"])
def test_hakem16_celik_kiyas_ve_karar_sahibi_sorulur(s, metin):
    """Y-A, Y-B çelikte: onay kaydediliyor, plan teknik kontrole gidiyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


def test_hakem16_celik_birimli_sayi_secimi_bozmaz(s):
    """O-A çelikte: "teslim 3 hafta mı?" setin 3. çatısı değildir."""
    cati_seti(s)
    k = s.yaz("Ç8801 olsun, 3 haftada mı teslim?")
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


# ── İE-42 · geometri hakemi on yedinci tur (15 Kasım 2026 sabah) ───────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["K olsun, en iyisi hangisi?", "K olsun, hangisi iyi?", "K olsun, diğer çatı daha mı iyi?",
                                   "1 olsun, hangisi olsun?", "K olsun, kararı müşteri verecek"])
def test_hakem17_celik_tavsiye_ve_karar_birakma_sorulur(s, metin):
    """Y-A', Y-B' çelikte: setten çatı kaydediliyor ya da onay mühendis kontrolüne gidiyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["1 olsun, teslim 2-3 hafta mı?", "Ç8801 olsun, teslim 2,5 ay mı?"])
def test_hakem17_celik_sayi_araligi_onayi_bozmaz(s, metin):
    """O-A kalanı çelikte: "2-3 hafta", "2,5 ay" setin numarası değildir; evin çatısı r01'i onaylar."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


# ── İE-42 · geometri hakemi on sekizinci tur (15 Kasım 2026 sabah) ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["K olsun, birinci daha mı iyi?", "Ç8801 olsun, ikinci daha mı iyi?",
                                   "Ç8801 olsun, gönderdiklerinizden hangisi daha iyi?", "Ç8801 olsun, karar müşteride tabii",
                                   "K olsun, ötekini önerir misiniz?", "Ç8801 olsun, son karar yarın verilecek",
                                   "Ç8801 olsun, eğime göre sonra bakarız", "Ç8801 olsun, karar müşterinin eşinde",
                                   "Ç8801 olsun, zemine göre değişebilir", "Ç8801 olsun, tavsiyenize göre değiştiririz"])
def test_hakem18_celik_sira_sahip_ve_erteleme_sorulur(s, metin):
    """Tur 18 çelikte: sıra sözü, setten seçen ayrılma, dolgulu ya da tamlamalı sahip, karardan sonra zaman ve "göre" ertelemesi onayı
    mühendis kontrolüne gönderiyor ya da setten çatı kaydediyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["K olsun, kararımızı veriyoruz", "K olsun, kararımızı verebildik"])
def test_hakem18_celik_olumlu_karar_secimi_bozmaz(s, metin):
    """Tur 18 (Orta 3) çelikte: olumlu karar sözü K'yı seçer: r02."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and s.plan["revizyon"] == 2 and s.k.d.get("cati_secilen") == "Ç8801K", k.mesaj


# ── İE-42 · geometri hakemi on dokuzuncu tur (15 Kasım 2026 sabah) ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["Ç8801 olsun, fiyat olarak hangisi daha uygun?", "Ç8801 olsun, modellerden hangisi daha iyi?",
                                   "K olsun, montaj için hangisi daha kolay?", "Ç8801 olsun bir bakalım", "Ç8801 olsun sonra bir bakalım",
                                   "Ç8801 olsun, bir düşünelim mi?", "K olsun bir bakalım"])
def test_hakem19_celik_olcutlu_kiyas_ve_erteleme_sorulur(s, metin):
    """Tur 19 (Y1, Y3) çelikte: ölçütle kıyas ve seçimle aynı cümlede ya da soru biçiminde erteleme onayı mühendis kontrolüne
    gönderiyor ya da setten çatı kaydediyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


# ── İE-42 · geometri hakemi yirminci tur (15 Kasım 2026 sabah) ─────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["Ç8801 olsun, ikinci olabilir mi?", "Ç8801 olsun, üçüncü olabilir mi?",
                                   "Ç8801 olsun, ikinci olursa nasıl olur?", "Ç8801 olsun, fiyat için hangi çatı daha iyi?",
                                   "Ç8801 olsun, hangi modeli seçelim?", "K olsun, üçüncü olabilir mi?", "K olsun, hangi modeli önerirsiniz?"])
def test_hakem20_celik_sira_ve_olcut_sorulur(s, metin):
    """Tur 20 (Y1, Y2) çelikte: eksiz sıra sözü ve "hangi çatı/modeli" onayı mühendis kontrolüne gönderiyor ya da setten çatı
    kaydediyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


# ── İE-42 · geometri hakemi yirmi birinci tur (15 Kasım 2026 öğle) ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["Ç8801 olsun ama, şimdilik", "Ç8801 olsun şimdilik", "K olsun ama, sonra değişebilir",
                                   "K olsun, hangisi daha dayanıklı, karda mı rüzgarda mı?"])
def test_hakem21_celik_simdilik_ve_baglac_sorulur(s, metin):
    """Tur 21 (Y1, Y2, O1, O3) çelikte: "şimdilik" onayı mühendis kontrolüne gönderiyordu; bağlaçtan sonraki çekince ve koşul sözlü
    ayrık soru onaylanabilir r02 çiziyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj



# ── İE-42 · geometri hakemi yirmi ikinci tur (15 Kasım 2026 öğle) ──────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["Ç8801 olsun ama, çatı ne olacak bilmiyoruz", "Ç8801 olsun, başka nasıl bir çatı olabilir?",
                                   "Ç8801 olsun, ikinci seçilen bir çatı olur mu?", "Ç8801 olsun, şimdilik iyi",
                                   "K olsun ama, çatı kalsın mı bilmiyoruz", "K olsun, müşteri ne der bilmiyoruz",
                                   "K olsun, kapora yatırırsak çatıyı değiştirebilir miyiz?",
                                   "K olsun, fiyat açısından başka seçenek var mı?"])
def test_hakem22_celik_cekince_ve_soru_sorulur(s, metin):
    """Tur 22 (Y1–Y4, O2, O3) çelikte: onayı mühendis kontrolüne gönderiyor ya da onaylanabilir r02 çiziyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["Ç8801 olsun, şimdilik değişiklik istemiyoruz", "1 olsun, şimdilik sağ olun"])
def test_hakem22_celik_kapanis_onayi_bozmaz(s, metin):
    """Tur 22 (O5) çelikte: kapanıştaki "şimdilik" onayı bozmaz."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


# ── İE-42 · geometri hakemi yirmi üçüncü tur (15 Kasım 2026 öğleden sonra) ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", ["Ç8801 olsun, müşteri şimdilik razı", "Ç8801 olsun, müşteri onaylasın",
                                   "Ç8801 olsun, çatıyı müşteri seçecek", "Ç8801 olsun ama, çatı müşteriye kalsın",
                                   "Ç8801 olsun, karar için müşterinin onayı lazım", "K olsun, çatıyı müşteri seçecek",
                                   "Ç8801 olsun, böyle kalsın mı?", "K olsun, karar verildi ama değişebilir"])
def test_hakem23_celik_musteri_ve_secim_sorusu_sorulur(s, metin):
    """Tur 23 (Y1–Y3, O9) çelikte: onayı mühendis kontrolüne gönderiyor ya da onaylanabilir r02 çiziyordu."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", ["K olsun, teslim ne zaman olur bilmiyoruz", "K olsun, karar sonrası teslim ne kadar sürer?",
                                   "K olsun, kapora yatırırsak çatı malzemesi ne zaman gelir?"])
def test_hakem23_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 23 (O1, O3) çelikte: konusu belli bilgi ve süreç sorusu açık seçimi soruya çevirmez: r02 K."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


# ── İE-42 · geometri hakemi yirmi dördüncü tur (15 Kasım 2026 öğleden sonra) ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, karar veremedik fiyat ne kadar?", "Ç8801 olsun, emin değiliz teslim ne zaman?",
    "Ç8801 olsun, ustam karar veremedik ne yapalım?", "K olsun, emin değiliz teslim ne zaman?",
    "K olsun, fiyatı görünce karar veririz ne zaman gelir?", "Ç8801 olsun, tamam mı?", "K olsun, olur mu?",
    "K olsun, kapora yatırırsak montaja kadar değiştirebilir miyiz?", "Ç8801 olsun, müşteri dün aradı yarın bakacak",
    "K olsun, müşteri dün aradı yarın bakacak", "K olsun ama, odalar sonra netleşsin"])
def test_hakem24_celik_kararsizlik_ve_secim_sorusu_sorulur(s, metin):
    """Tur 24 (Y1, Y2, O6, O7, O8) çelikte: onayı mühendis kontrolüne gönderiyor, onaylanabilir r02 çiziyor ya da kayıtsız
    yönlendiriyordu: seçim sorulur."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", [
    "K olsun, fatura şirkete mi olsun?", "K olsun, müşteri beğendi ne zaman başlıyoruz?"])
def test_hakem24_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 24 (O1) çelikte: çatı dışı süreç sorusu açık seçimi soruya çevirmez: r02 K."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


@pytest.mark.parametrize("metin", ["Ç8801 olsun, olur mu abi?", "K olsun, tamam mı hocam?", "Ç8801 olsun, sorun olur mu?",
                                   "K olsun, makul mü?"])
def test_hakem24_celik_hitapli_secim_sorusu_sorulur(s, metin):
    """Tur 24 sonrası çelikte: hitaplı seçim sorusu onayı mühendis kontrolüne gönderiyor ya da r02 çiziyordu: seçim sorulur."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


# ── İE-42 · geometri hakemi yirmi beşinci tur (15 Kasım 2026 öğleden sonra) ─────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, ne yapalım bilemedik teslim ne zaman?", "K olsun, ne yapalım bilemedik fiyat ne kadar?",
    "Ç8801 olsun, olur mu usta?", "Ç8801 olsun, en iyisi bu mu?", "Ç8801 olsun, yeter mi?", "K olsun, olur mu usta?",
    "K olsun, müşteri ne der?", "K olsun, müşterim beğenir mi?", "K olsun, doğru tercih mi?", "K olsun, sıkıntı olur mu?",
    "Ç8801 olsun, müşteri ne der?", "Ç8801 olsun, ama aklımız değişebilir", "Ç8801 olsun, müşterinin onayı gerekecek",
    "Ç8801 olsun geçici bir süre böyle kalsın", "Geçici bir süre Ç8801 olsun", "Ç8801 olsun, doğru tercih mi?"])
def test_hakem25_celik_kararsizlik_ve_secim_sorusu_sorulur(s, metin):
    """Tur 25 (Y1, Y2, O1–O5) çelikte: onayı mühendis kontrolüne gönderiyor, onaylanabilir r02 çiziyor ya da kayıtsız
    yönlendiriyordu: seçim sorulur."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", [
    "K olsun, kapora yatırırsak ödeme tarihini sonra değiştirebilir miyiz?"])
def test_hakem25_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 25 (O6) çelikte: zaman sözü konudan sonra gelen süreç sorusu açık seçimi soruya çevirmez: r02 K."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


# ── İE-42 · geometri hakemi yirmi altıncı tur (15 Kasım 2026 akşam) ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, seçimi müşteriye bıraktık", "Ç8801 olsun, müşteriye bıraktık", "Ç8801 olsun, tercihi müşteriye bıraktık",
    "Ç8801 olsun, müşterinin tercihine bıraktık", "K olsun, seçimi müşteriye bıraktık", "K olsun, müşteriye bıraktık",
    "Ç8801 olsun, abi müşteriye kalsın", "Ç8801 olsun, hocam müşteriye kalsın", "Ç8801 olsun, en iyisi müşteriye kalsın",
    "K olsun, abi müşteriye kalsın", "Ç8801 olsun, okey mi?", "Ç8801 olsun, diyelim mi?", "Ç8801 olsun, haliyle mi kalsın?",
    "K olsun, diyelim mi?", "K olsun, olur mu kral?", "Ç8801 olsun tamammı", "K olsun tamammı"])
def test_hakem26_celik_birakilan_karar_ve_secim_sorusu_sorulur(s, metin):
    """Tur 26 (Y1–Y4) çelikte: "müşteriye bıraktık", "abi müşteriye kalsın", "okey mi?", "diyelim mi?", "tamammı" onayı mühendis
    kontrolüne gönderiyor ya da onaylanabilir r02 çiziyordu: seçim sorulur."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", [
    "K olsun, değiştirip gönderebilir misiniz?", "K olsun, değiştirip atabilir misiniz?", "K olsun, değişikliği gönderebilir misiniz?",
    "K olsun, değişiklik yapabilir misiniz?", "K olsun, iki usta yeter mi?", "K olsun, montajda usta olur mu?",
    "K olsun, montaj için usta yeterli mi?", "K olsun, nasıl yapalım?"])
def test_hakem26_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 26 (O1, O2) çelikte: değişikliği isteyen rica ve çatı dışı soru açık seçimi soruya çevirmez: r02 K."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


@pytest.mark.parametrize("metin", ["Geçici bir süre K olsun", "K olsun, rüzgar için sağlam mı?"])
def test_hakem26_celik_kendi_yoklamamiz_sorulur(s, metin):
    """Tur 26 sonrası çelikte: etiketli "geçici bir süre" ve dayanıklılık sorusu: seçim sorulur."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


# ── İE-42 · geometri hakemi yirmi yedinci tur (15 Kasım 2026 gece) ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", [
    "K olsun, sizce abi olur mu?", "K olsun, müşterinin onayı gerekiyor alınmadı daha", "K olsun, değiştirmek gerekebilir",
    "Ç8801 olsun, usta müşteriye kalsın", "Ç8801 olsun, usta seçim müşteriye kalsın", "K olsun, usta müşteriye kalsın",
    "Ç8801 olsun, müşteriye bıraktık. Onaylamış olabilir", "Ç8801 olsun, müşteriye bıraktık seçtiği olsun"])
def test_hakem27_celik_kararsizlik_ve_erteleme_sorulur(s, metin):
    """Tur 27 (Y1, Y2, O3, O6, O7) çelikte: "usta müşteriye kalsın", seçimi bildirmeyen "bıraktık", hitaplı seçim sorusu, alınmamış onay
    ve olasılık sözlü değişiklik: seçim sorulur."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", [
    "K olsun, montaj için ne düşünüyorsunuz?", "K olsun, kapı için ne düşünüyorsun?"])
def test_hakem27_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 27 (O4) çelikte: konulu ölçüt sorusu açık seçimi soruya çevirmez: r02 K."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, ne zaman?", "Ç8801 olsun, teklifi gönderir misiniz?", "Ç8801 olsun, kaç günde olur?",
    "1 olsun, pdf gönderir misiniz?", "Ç8801 olsun, teklifi ne zaman gönderirsiniz?", "Ç8801 olsun, pdf gönderir misiniz?",
    "Merhaba, iyi misiniz? Ç8801 olsun"])
def test_hakem27_celik_acik_onay_soruya_donmez(s, metin):
    """Tur 27 (O1) çelikte: süreç sorusu ve selam evin çatısının onayını bozmaz."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj


# ── İE-42 · geometri hakemi yirmi sekizinci tur (çelik) ────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, hemen onaylayalım mı?", "Ç8801 olsun, şimdi onaylayalım mı?", "Ç8801 olsun, hemen tamam mı?",
    "Ç8801 olsun, 2 gün düşünelim mi?", "Ç8801 olsun, ne yapalım?", "Hocam iyi misiniz bu çatı olur mu, Ç8801 olsun",
    "Ç8801 olsun, bu mu kalsın iyi misiniz?", "Ç8801 olsun, nakliye için daha mı uygun?", "K olsun, montaj için ikisi de olur mu?",
    "K olsun, 2 gün düşünelim mi?", "Ç8801 olsun, müşteriye bıraktık, razı değil", "K olsun müşteri bakcak"])
def test_hakem28_celik_karar_sorusu_ve_kararsizlik_sorulur(s, metin):
    """Tur 28 (Y1, Y2, Y3, O2, Y5) çelikte: onayın ve ertelemenin sorusu, selamlı seçim sorusu, konulu kıyas, "razı değil", konuşma
    dili ("K olsun müşteri bakcak"): seçim sorulur."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "sor" and k.mesaj.startswith("Hangi çatı olsun?"), k.mesaj
    assert s.plan["revizyon"] == 1 and s.k.d["secenek_seti"]["durum"] == "acik" and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", [
    "K olsun, yatak odası 2 penceresini değiştirebilir misiniz?", "K olsun, son olarak salon kapısını değiştirebilir misiniz?",
    "K olsun, ödemeyi 3 taksit olarak yapabilir miyiz?", "K olsun, usta ücreti müşteriye kalsın",
    "K olsun, değişiklik ücreti olabilir mi?", "Merhaba hocam K olsun teklifi gönderir misiniz", "K olsun teklifi gönderin"])
def test_hakem28_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 28 (O1, O5, O6 ve virgülsüz yazım) çelikte: açık seçim soruya dönmez: r02 K."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


@pytest.mark.parametrize("metin", [
    "Ç8801 olsun teklifi gönderin", "Merhaba hocam Ç8801 olsun", "Ç8801 olsun müşteri onayladı"])
def test_hakem28_celik_virgulsuz_onay_soruya_donmez(s, metin):
    """Tur 28 çelikte: virgülsüz seçim ve selam evin çatısının onayını bozmaz."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj



@pytest.mark.parametrize("metin", [
    "Ç8801 olsun ama sonra", "Ç8801 olsun ama bekliyoruz", "Ç8801 olsun sonra", "Ç8801 olsun bekliyoruz",
    "Ç8801 olsun teklif gelsin bakalım", "Ç8801 olsun teklifi görelim", "Ç8801 olsun, ama şimdi değil", "Ç8801 olsun ama şimdi değil",
    "Ç8801 olsun şimdi değil", "Ç8801 olsun, teklifi atın bakalım", "K olsun ama şimdi değil", "K olsun teklif gelsin bakalım",
    "K olsun ama sonra", "K olsun ama bekliyoruz", "Ç8801 olsun, usta bunu müşteri seçecek", "K olsun, usta bunu müşteri seçecek"])
def test_hakem29_celik_erteleme_kaydedilmez(s, metin):
    """Tur 29 (Y1, Y5, Y4, Y2) çelikte: virgülsüz ve virgüllü erteleme ("Ç8801 olsun ama sonra", "şimdi değil", "teklif gelsin bakalım",
    "bekliyoruz") ve "usta bunu müşteri seçecek" kayıt almaz: plan r01, onay yok, r02 yok."""
    cati_seti(s)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and k.eylem != "is_emri" and s.plan["revizyon"] == 1 and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", [
    "K olsun, kapı rengini sonra mı seçelim?", "K olsun, renk seçimini ne zaman yapalım?", "K olsun, montaj tarihini ne zaman seçelim?",
    "Günaydın hocam K olsun", "Merhaba hocam iyi misiniz K olsun", "K olsun inşallah"])
def test_hakem29_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 29 (O3 ve selamlı yazım) çelikte: başka konunun karar sorusu ve selamlı seçim r02 K'yı çizer."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj


@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, bunu ne zaman gönderirsiniz?"])
def test_hakem29_celik_surec_sorusu_onay(s, metin):
    """Tur 29 (O4) çelikte: gösterme sözlü süreç sorusu evin çatısının onayını soruya çevirmez."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj



@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, fark etmez ya", "Ç8801 olsun, bence fark etmez", "Ç8801 olsun, müşteri için fark etmez", "K olsun, fark etmez ya",
    "K olsun, bence fark etmez", "Ç8801 olsun, ödemeden sonra mı onaylayalım?", "K olsun, ödemeden sonra mı onaylayalım?",
    "K olsun, montajdan sonra mı karar verelim?", "K olsun, teslim tarihine göre mi karar verelim?", "K olsun, modeli sonra mı seçelim?",
    "Ç8801 olsun son karar müşteriye", "Ç8801 olsun, müşteri razı olur", "Ç8801 olsun gibi", "Ç8801 olsun gibi düşünüyoruz",
    "K olsun, müşteri razı olur", "K olsun gibi", "Merhaba hocam Ç8801 olsun ama sonra", "K olsun, son karar müşteriye"])
def test_hakem30_celik_kararsiz_soz_kaydedilmez(s, metin):
    """Tur 30 (Y1–Y5, O4) çelikte: "fark etmez ya", "bence fark etmez", "ödemeden sonra mı onaylayalım?", "son karar müşteriye", "müşteri
    razı olur", "Ç8801 olsun gibi" ve selamlı erteleme kayıt almaz: plan r01, onay yok, r02 yok."""
    cati_seti(s)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and k.eylem != "is_emri" and s.plan["revizyon"] == 1 and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", [
    "K olsun allah razı olsun", "K olsun planı atın", "K olsun hemen çizin", "K olsun değişiklik yok", "K olsun montaj ne zaman",
    "K olsun tamamdır", "K olsun değişiklik yok teklif gönderin", "Hocam merhaba K olsun"])
def test_hakem30_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 30 (O1) çelikte: virgülsüz olumlu söz ("K olsun Allah razı olsun", "planı atın", "değişiklik yok", "montaj ne zaman") r02 K'yı
    çizer."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj



@pytest.mark.parametrize("metin", [
    "K olsun fark etmez ya", "Ç8801 olsun, ödemeyi yapınca onaylarız", "K olsun mu dersiniz", "Ç8801 olsun, hemen olmasın",
    "Ç8801 olsun, çatı modeli fark etmez", "Ç8801 olsun, bakalım fiyat ne kadar olacak?", "Ç8801 olsun, görelim fiyat ne olacak?",
    "Ç8801 olsun, model fark etmez", "Ç8801 olsun, modeli size bırakıyorum", "Ç8801 olsun, kaç olursa fark etmez",
    "Ç8801 olsun, hemen değil", "Ç8801 olsun, hemen değil sonra", "Evin kendi çatısı olsun, hemen değil", "Ç8801 olsun onu da çizin",
    "Ç8801 olsun plan sonra", "Ç8801 olsun, müşteri razı gibi", "Ç8801 olsun, bu da olur", "K olsun, o da olur",
    "Ç8801 olsun, son karar müşteriye", "Ç8801 olsun, onay müşteriden", "Ç8801 olsun, montajdan sonra mı onaylayalım?",
    "Ç8801 olsun, ödemeyle birlikte mi onaylayalım?", "K olsun, müşteri beğendi, bakalım ne olacak", "K olsun, bakalım ne olacak?",
    "Ç8801 olsun, faturayı görünce mi onaylayalım?", "Ç8801 olsun, karar eşine", "K olsun, hemen değil",
    "K olsun, bakalım fiyat ne kadar olacak?"])
def test_hakem31_celik_kararsiz_soz_kaydedilmez(s, metin):
    """Tur 31 (Y1–Y4) çelikte: "bakalım fiyat ne kadar olacak?", "model fark etmez", "hemen değil", "onu da çizin" kayıt almaz: plan r01,
    onay yok, r02 yok."""
    cati_seti(s)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and k.eylem != "is_emri" and s.plan["revizyon"] == 1 and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", [
    "K olsun, klozet modelini sonra mı seçelim?", "K olsun, müşteri onayı", "K olsun, müşteri tercihi",
    "K olsun, müşteri onayladı bence süper", "K olsun, kapıları montajdan sonra mı onaylayalım?",
    "K olsun, rengi ödemeden sonra mı onaylayalım?", "K olsun, rengine montajdan sonra mı karar verelim?",
    "K olsun, korkuluk modelini sonra mı seçelim?", "K olsun, kombi modelini sonra mı seçelim?", "K olsun tamamdır teklifi atın",
    "Selamünaleyküm K olsun", "K olsun iki usta yeter mi"])
def test_hakem31_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 31 (O1–O5) çelikte: konusu belli devir, bildirilmiş karar, görüş sözü, başka konunun zamanı ve modeli r02 K'yı çizer."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj



@pytest.mark.parametrize("metin", [
    "Ç8801 olsun değişiklik yok", "Ç8801 olsun tamamdır teklifi atın"])
def test_hakem31_celik_olumlu_soz_onay(s, metin):
    """Tur 31 çelikte: konusu belli devir ve bildirilmiş karar evin çatısının onayıdır."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj



@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, çatı tipi fark etmez", "Ç8801 olsun, bence müşteri de onayladı", "Ç8801 olsun, bakalım teklif uygun mu?",
    "Ç8801 olsun, çatı şekli fark etmez", "Ç8801 olsun, tip fark etmez", "Ç8801 olsun, çatı seçimini size bırakıyorum",
    "Ç8801 olsun, neyse fark etmez", "Ç8801 olsun, uygun olanı size bırakıyorum", "Ç8801 olsun, birincisi ya da ikincisi fark etmez",
    "Ç8801 olsun, müşteri bence bunu seçti", "K olsun, çatı tipi fark etmez", "K olsun, çatı seçimini size bırakıyorum",
    "K olsun, ödemeyi yaptıktan sonra mı onaylayalım?", "K olsun, montajı bitirdikten sonra mı onaylayalım?", "Ç8801 olsun, acil değil",
    "Ç8801 olsun, hemen gerek yok", "Ç8801 olsun, teklif sonra", "Ç8801 olsun, karar müşteri ile", "K olsun, acil değil",
    "Ç8801 olsun, siz seçin", "Ç8801 olsun, bakalım maliyet ne olur?"])
def test_hakem32_celik_kararsiz_soz_kaydedilmez(s, metin):
    """Tur 32 çelikte: "çatı tipi fark etmez", "çatı seçimini size bırakıyorum", "bence müşteri de onayladı", "bakalım teklif uygun mu?"
    kayıt almaz: plan r01, onay yok, r02 yok."""
    cati_seti(s)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and k.eylem != "is_emri" and s.plan["revizyon"] == 1 and not s.k.d.get("onaylanan"), k.mesaj


@pytest.mark.parametrize("metin", [
    "K olsun, bakalım vinç fiyatı ne kadar?", "K olsun, bakalım kurulum fiyatı ne kadar?", "K olsun, mail ya da whatsapp fark etmez",
    "K olsun, müşteri onayladı bence de güzel"])
def test_hakem32_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 32 çelikte: işin devri, başka işin fiyatı ("bakalım vinç fiyatı ne kadar?") r02 K'yı çizer."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj



@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, gerisini sonra konuşuruz", "Ç8801 olsun, mail ya da whatsapp fark etmez"])
def test_hakem32_celik_olumlu_soz_onay(s, metin):
    """Tur 32 çelikte: öteki konuyu sonraya bırakma ve işin devri evin çatısının onayıdır."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.gerekce == K.PLAN_ONAYI and k.revizyon == 1, k.mesaj



@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, bakalım bu modelin fiyatı ne kadar?", "Ç8801 olsun, siz seçin dedim", "Ç8801 olsun, bakalım en iyi fiyat ne olur?",
    "Ç8801 olsun, bakalım müşteriye fiyat ne olur?", "K olsun, bakalım bu modelin fiyatı ne kadar?",
    "Ç8801 olsun, tercihini size bırakıyorum", "Ç8801 olsun, müşteri ile karar", "Ç8801 olsun, uygun olanı siz seçin",
    "Ç8801 olsun, ödemeyi yaptıktan sonra mı onaylayalım?", "K olsun, ustayla birlikte mi karar verelim?",
    "Ç8801 olsun, gerisini sonra konuşuruz çatı dahil", "Ç8801 olsun, bakalım bu modelin maliyeti ne olur?"])
def test_hakem33_celik_kararsiz_soz_kaydedilmez(s, metin):
    """Tur 33 çelikte: "bakalım bu modelin fiyatı ne kadar?", "siz seçin dedim" kayıt almaz: plan r01, onay yok, r02 yok."""
    cati_seti(s)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and k.eylem != "is_emri" and s.plan["revizyon"] == 1 and not s.k.d.get("onaylanan"), k.mesaj



@pytest.mark.parametrize("metin", [
    "K olsun, bakalım toplam kaç gün?", "K olsun, bakalım alan ne kadar?", "K olsun, müşteri seçti bence de en iyisi",
    "K olsun, rengi ustayla birlikte mi seçelim?"])
def test_hakem33_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 33 çelikte: işi anan bakış sözü, iş kaleminin seçimi ve ölçü sorusu r02 K'yı çizer."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj



@pytest.mark.parametrize("metin", [
    "K olsun, müşteri istedi tamam mı?", "K olsun, bakalım bu ay ne kadar olur?", "K olsun, yarın kesinleşir",
    "Ç8801 olsun, bakalım bu ay ne kadar olur?", "Ç8801 olsun, bakalım kaç gün ne kadar olur?",
    "Ç8801 olsun, müşteri beğendi bence olur bakalım", "Ç8801 olsun, müşteri onayladı bence de olur bakalım",
    "Ç8801 olsun, müşteri kabul etmez bence de olur", "K olsun, bakalım kaç gün ne kadar olur?",
    "K olsun, müşteri beğendi bence olur bakalım", "K olsun, müşteri onayladı bence de olur bakalım",
    "K olsun, müşteri istedi bence de olur mu acaba", "K olsun, müşteri istedi bence tamam mı?", "K olsun, bakalım metrekaresi ne kadar?",
    "Ç8801 olsun, siz seçin dedimya", "Ç8801 olsun, siz seçin diyorum", "Ç8801 olsun, ne gönderirseniz fark etmez",
    "K olsun, kırma ya da beşik hangisi uygunsa fark etmez", "Ç8801 olsun, bence müşteri doğru karar verecek",
    "Ç8801 olsun, bakalım metrekaresi ne kadar tutar?", "Ç8801 olsun, bakalım kaç gün ne kadar tutar?", "Ç8801 olsun, siz seçin dedim ya",
    "Ç8801 olsun, bakalım nakliye dahil fiyat ne kadar?", "Ç8801 olsun, bakalım kaç gün, ne kadar?",
    "K olsun, bakalım nakliye dahil fiyat ne kadar?"])
def test_hakem34_celik_kararsiz_soz_kaydedilmez(s, metin):
    """Tur 34 çelikte: "bakalım bu ay ne kadar olur?", "müşteri beğendi bence olur bakalım", "müşteri istedi tamam mı?", "yarın
    kesinleşir" kayıt almaz: plan r01, onay yok, r02 yok."""
    cati_seti(s)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and k.eylem != "is_emri" and s.plan["revizyon"] == 1 and not s.k.d.get("onaylanan"), k.mesaj



@pytest.mark.parametrize("metin", [
    "K olsun, hangi gün gelmeniz fark etmez", "K olsun, ne zaman gelmeniz fark etmez"])
def test_hakem34_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 34 çelikte: fiilimsiyle işin devri ("hangi gün gelmeniz fark etmez") r02 K'yı çizer."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj



@pytest.mark.parametrize("metin", [
    "Ç8801 olsun, bakalım nakliyesiyle ne kadar?", "K olsun, bakalım nakliyesiyle ne kadar?", "K olsun, bakalım kurulumla ne kadar olur?",
    "K olsun, bakalım vinçle birlikte ne kadar?", "K olsun, pazartesi kesinleşir", "K olsun, bakalım ne zaman teslim, ne kadar?",
    "K olsun, bakalım montaj ne zaman, fiyat ne kadar?"])
def test_hakem35_celik_kararsiz_soz_kaydedilmez(s, metin):
    """Tur 35 çelikte: "bakalım nakliyesiyle ne kadar?", "kurulumla ne kadar olur?", "pazartesi kesinleşir", "bakalım ne zaman teslim,
    ne kadar?" kayıt almaz: plan r01, onay yok, r02 yok."""
    cati_seti(s)
    k = s.yaz(metin)
    assert K.PLAN_ONAYI not in k.gerekce and k.eylem != "is_emri" and s.plan["revizyon"] == 1 and not s.k.d.get("onaylanan"), k.mesaj



@pytest.mark.parametrize("metin", [
    "K olsun, diğer konuları sonra konuşuruz, fiyat ne kadar olur?", "K olsun, kabul ederiz"])
def test_hakem35_celik_acik_secim_soruya_donmez(s, metin):
    """Tur 35 çelikte: başka işin ertelemesi ("diğer konuları sonra konuşuruz") ve "kabul ederiz" r02 K'yı çizer."""
    cati_seti(s)
    k = s.yaz(metin)
    assert k.eylem == "is_emri" and k.revizyon == 2 and s.plan["yapi"]["kod"] == "Ç8801K", k.mesaj
