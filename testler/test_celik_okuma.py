"""İE-08 8a PR-2b (A4) · `beyin/celik_okuma`: bayinin kendi sözünden pencere/çatı/dış 140 okuması (K18, K21). Motor ve Postgres yok."""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from beyin import celik_okuma as CO  # noqa: E402

C8801 = json.loads((KOK / "modeller" / "C8801.json").read_text(encoding="utf-8"))
C8201 = json.loads((KOK / "modeller" / "C8201.json").read_text(encoding="utf-8"))
KATALOG = {"kod": "Ç8801", "varyantlar": ["Ç8801K", "Ç8801L"]}


def adlar(r):
    return [a["aciklik"] for a in (r["pencere"] or {}).get("adaylar", [])]


@pytest.mark.parametrize("metin, aciklik, olcu", [
    ("mutfak penceresi 120x120 olsun", ["P5"], (120, 120)),
    ("Mutfağın penceresini 120 x 180 yapalım", ["P5"], (120, 180)),
    ("banyo vasistası 60/60 olsun", ["P7"], (60, 60)),
    ("holdeki pencere 120x180", ["P2"], (120, 180)),
    ("yaşam alanı penceresi 160x120", ["P1", "P3", "P4"], (160, 120)),              # 3 aday → numaralı soru
    ("salondaki sol taraftaki pencere 120x180 olsun", ["P3", "P4"], (120, 180)),   # oda + cephe: 2 aday → görselli soru
    ("salon ön cephedeki pencere 160x180", ["P1"], (160, 180)),
    ("yatak odası 2 penceresi 120x180", ["P8", "P9"], (120, 180)),
    ("ikinci yatak odasının sağ cephedeki penceresi 120x180", ["P8"], (120, 180)),
    ("1. yatak odası penceresi 120x180", ["P6"], (120, 180)),
    ("yatak odası penceresi 120x180", ["P6", "P8", "P9"], (120, 180)),            # iki yatak odası: 3 aday
    ("salon 120x120 olan pencere 120x180 olsun", ["P3", "P4"], (120, 180)),       # eski ölçü süzgeci
    ("salonda 120x180 yerine 160x180", ["P1"], (160, 180)),
    ("arka cephedeki pencere 120x120 olsun", ["P5"], (120, 120)),
])
def test_pencere_okumasi(metin, aciklik, olcu):
    r = CO.oku(metin, C8801, KATALOG)
    assert r["istek"] and r["pencere"] and not r["pencere"]["olumsuz"], r
    assert adlar(r) == aciklik and r["pencere"]["olcu"] == olcu, (adlar(r), r["pencere"]["olcu"])
    assert r["cati"] is None and r["dis140"] is False


def test_pencere_olcu_yok_ve_oda_yok():
    r = CO.oku("mutfak penceresini büyütelim", C8801, KATALOG)
    assert r["pencere"]["olcu"] is None and adlar(r) == ["P5"]
    r = CO.oku("kiler penceresi 120x120", C8801, KATALOG)                   # odası yok: aday 0, süzgeç yok → bütün pencereler (soru)
    assert r["pencere"]["olcu"] == (120, 120) and r["pencere"]["mahaller"] == [] and len(adlar(r)) == 9
    r = CO.oku("mutfak 60x40 olsun", C8801, KATALOG)                           # "pencere" sözü yok ama ölçü ve oda var
    assert adlar(r) == ["P5"] and r["pencere"]["olcu"] == (60, 40)
    assert CO.oku("sevk adresi Deneme İlçesi olsun", C8801, KATALOG)["istek"] is False


def test_olumsuz_ve_soru_belirsiz():
    assert CO.oku("mutfak penceresi 120x120 olmasın", C8801, KATALOG)["pencere"]["olumsuz"] is True
    assert CO.oku("mutfak penceresi 120x120 olur mu?", C8801, KATALOG)["pencere"]["olumsuz"] is True
    assert CO.oku("mutfak penceresi 120x120 olsun", C8801, KATALOG)["pencere"]["olumsuz"] is False
    # Kapanış incelemesi (13.10, CR6): ölçü yazılmış olsa da ekleme sözü eklemedir — mevcut pencere değiştirilmez, kural katmanı yönlendirir.
    # (Önceki vaka "ölçü varken ekleme sözü kural katmanına kalır; tek pencere değişir" idi: açık ekleme isteği var olan pencereyi
    # küçültüyordu. Davranış inceleme bulgusuyla değişti, gevşetme değil; IE-08 › Kapanış incelemesi düzeltmeleri (PR-2b).)
    for s in ("mutfağa bir pencere daha ekleyin 120x120", "mutfağa bir pencere daha ekleyin", "mutfağa bir pencere daha 120x120 olsun",
              "salona yeni pencere 120x180", "banyodaki vasistası kaldırın"):
        r = CO.oku(s, C8801, KATALOG)
        assert r["ekle_kaldir"] and r["pencere"]["ekle_kaldir"] is True, s


def test_cati_ve_dis140():
    assert CO.oku("çatı L olsun", C8801, KATALOG)["cati"] == "Ç8801L"
    assert CO.oku("Ç8801K", C8801, KATALOG)["cati"] == "Ç8801K"
    assert CO.oku("katalog çatısı kalsın", C8801, KATALOG)["cati"] == "Ç8801"
    for s in ("dışlar 140'lık olsun", "dış duvarlar 140 olsun", "dış karkas 140'lık", "dışlar 14'lük olsun", "140'lık dış duvar istiyoruz"):
        assert CO.oku(s, C8801, KATALOG)["dis140"] is True, s
    assert CO.oku("dışlar 140 olmasın", C8801, KATALOG)["dis140"] is False
    assert CO.oku("iç duvarlar 140 olsun", C8801, KATALOG)["dis140"] is False
    r = CO.oku("çatı K olsun, dışlar 140'lık, mutfak penceresi 120x120", C8801, KATALOG)
    assert r["cati"] == "Ç8801K" and r["dis140"] and adlar(r) == ["P5"]


def test_cephe_yuzlerden_ve_c8201():
    from motor.genel import yapi
    y = yapi.kur(C8801)
    ad = {a["aciklik"]: a["cephe"] for a in CO.pencere_adaylari(C8801, y)}
    assert ad == {"P1": "on", "P2": "on", "P3": "sol", "P4": "sol", "P5": "arka", "P6": "sag", "P7": "sag", "P8": "sag", "P9": "on"}
    assert {a["aciklik"]: a["cephe"] for a in CO.pencere_adaylari(C8801)} == ad                    # ortaya göre tahmin aynı (motor yokken)
    r = CO.oku("yaşam alanının sağdaki penceresi 180x120", C8201, {"kod": "Ç8201", "varyantlar": []})
    assert adlar(r) == ["P6", "P7", "P8"]


# Cevap biçimi {"secimler": [...]} (kapanış incelemesi 13.10: "ikisi de", "1 ve 3" çoklu seçim; tek seçim tek elemanlı liste)
@pytest.mark.parametrize("metin, bekleyen, cevap", [
    ("1", {"tur": "secim", "adaylar": [1, 2]}, {"secimler": [0]}), ("2", {"tur": "secim", "adaylar": [1, 2]}, {"secimler": [1]}),
    ("ikinci", {"tur": "secim", "adaylar": [1, 2]}, {"secimler": [1]}), ("1 olsun", {"tur": "secim", "adaylar": [1, 2]}, {"secimler": [0]}),
    ("3", {"tur": "secim", "adaylar": [1, 2]}, None), ("hiçbiri", {"tur": "secim", "adaylar": [1, 2]}, {"hicbiri": True}),
    ("ikisi de değil", {"tur": "secim", "adaylar": [1, 2]}, {"hicbiri": True}), ("mutfak penceresi 120x120 olsun", {"tur": "secim", "adaylar": [1, 2]}, None),
    ("120x120", {"tur": "olcu", "adaylar": [1]}, {"olcu": (120, 120)}), ("vazgeçtim, yok", {"tur": "olcu", "adaylar": [1]}, {"hicbiri": True}),
    ("3. pencere", {"tur": "secim", "adaylar": [1, 2, 3]}, {"secimler": [2]}),
    # CR14: "ikisi de" ikisi; sayı "yok/hayır"dan önce okunur
    ("ikisi de olsun", {"tur": "secim", "adaylar": [1, 2]}, {"secimler": [0, 1]}), ("2 olsun sorun yok", {"tur": "secim", "adaylar": [1, 2]}, {"secimler": [1]}),
    ("hayır 2", {"tur": "secim", "adaylar": [1, 2]}, {"secimler": [1]}), ("1 ve 3", {"tur": "secim", "adaylar": [1, 2, 3]}, {"secimler": [0, 2]}),
    ("hepsi", {"tur": "secim", "adaylar": [1, 2, 3]}, {"secimler": [0, 1, 2]}), ("hepsi 120x180 olsun", {"tur": "secim", "adaylar": [1, 2, 3]}, None),
    ("ikisi de", {"tur": "secim", "adaylar": [1, 2, 3]}, None), ("hayır", {"tur": "secim", "adaylar": [1, 2]}, {"hicbiri": True}),
    # CR13: "120'ye 120"
    ("120'ye 120", {"tur": "olcu", "adaylar": [1]}, {"olcu": (120, 120)}),
])
def test_okuma_cevabi(metin, bekleyen, cevap):
    assert CO.okuma_cevabi(metin, bekleyen) == cevap


def test_vasistas_esigi_kuralla_ayni():
    from motor.genel.sablon_pafta import sablon_kurallari
    assert CO.VASISTAS_ESIK == ((sablon_kurallari().get("vasistas_en_cok_yukseklik_cm") or {}).get("deger") or 60)


def test_kapanis_incelemesi_cumle_cumle_okuma():
    """Kapanış incelemesi (13.10): mesaj cümle cümle okunur; tanınmayan sözcük taşıyan cümle hiçbir türe zorlanmaz (başka)."""
    r = CO.oku("mutfak penceresi 120x120, banyo vasistası 60x60 olsun", C8801, KATALOG)                  # CR4: iki pencere
    assert [(adlar({"pencere": p}), p["olcu"]) for p in r["pencereler"]] == [(["P5"], (120, 120)), (["P7"], (60, 60))]
    r = CO.oku("hol penceresi 120x120 olsun, banyoya havlupan koyalım", C8801, KATALOG)                  # CR4: hol, havlupan başka
    assert adlar(r) == ["P2"] and r["baska"] == ["banyoya havlupan koyalım"]
    r = CO.oku("mutfak ve salon pencereleri 120x120", C8801, KATALOG)                                    # CR4: iki oda tek cümlede
    assert sorted(adlar(r)) == ["P1", "P3", "P4", "P5"]
    for s in ("iç duvarlar 140, dış duvarlar 80 kalsın", "dış kapı 140 cm olsun", "dış ölçü 14 x 8 olsun", "dış cepheye 14 cm yalıtım"):   # CR5
        r = CO.oku(s, C8801, KATALOG)
        assert r["dis140"] is False and r["baska"], s
    for s in ("mutfak kapısı 90x200 olsun", "mutfak dolabı 60x90 olsun", "çift kanatlı pencere 120x120 olsun"):   # G3: kapı/dolap/tür değişikliği
        r = CO.oku(s, C8801, KATALOG)
        assert r["pencereler"] == [] and r["baska"], s
    r = CO.oku("veranda L olsun", C8801, KATALOG)                                                        # CR12: çatı değil
    assert r["cati"] is None and r["baska"] and CO.cati_okumasi("veranda L olsun", KATALOG) is None
    assert CO.cati_okumasi("L olsun", KATALOG) == "Ç8801L" and CO.cati_okumasi("çatı K olsun", KATALOG) == "Ç8801K"
    assert CO.cati_okumasi("Ç8801 L", KATALOG) == "Ç8801L" and CO.cati_okumasi("çatı L olmasın", KATALOG) is None
    assert CO.olculer("120'ye 120") == [(120, 120)] and CO.olculer("80'e 80") == [(80, 80)] and CO.olculer("60'a 40") == [(60, 40)]   # CR13
    for s in ("bir yatak odasının penceresi 120x180 olsun", "iki yatak odasının penceresi 120x180"):    # CR15: "bir"/"iki" numara değil
        assert adlar(CO.oku(s, C8801, KATALOG)) == ["P6", "P8", "P9"], s
    assert adlar(CO.oku("ikinci yatak odasının sağ cephedeki penceresi 120x180", C8801, KATALOG)) == ["P8"]
    r = CO.oku("Merhaba, mutfak penceresi 120x120 olsun lütfen. Teşekkürler", C8801, KATALOG)           # selam ve teşekkür boş cümle
    assert adlar(r) == ["P5"] and r["baska"] == [] and r["belirsiz"] == []
    assert CO.oku("mutfak büyük olsun", C8801, KATALOG)["baska"] and CO.oku("banyo kalsın", C8801, KATALOG)["istek"] is False
    assert CO.oku("dış duvarlar kalın olsun", C8801, KATALOG)["belirsiz"]                                # dış ama 140 yok: sorulur
    assert CO.hizli_istek("L olsun") and CO.hizli_istek("dışlar 140'lık olsun") and not CO.hizli_istek("veranda L olsun")
    assert not CO.hizli_istek("büyük olsun") and not CO.hizli_istek("teşekkürler")


def test_olcu_cevabi_baska_oda_yeni_istektir():
    """CR10: ölçü sorusu askıdayken başka odanın adı geçen mesaj cevap değildir (yeni istek); aynı oda ya da yalnız ölçü cevaptır."""
    from beyin import celik_okuma as C
    a = [p for p in C.pencere_adaylari(C8801) if p["aciklik"] == "P5"]
    ob = {"tur": "olcu", "adaylar": a, "mahaller_t": [{"ad": m["ad"], "islev": m.get("islev") or []} for m in C8801["mahaller"]]}
    assert C.okuma_cevabi("yok yok, banyo penceresi 120x50 olsun", ob) is None
    assert C.okuma_cevabi("mutfak penceresi 120x120 olsun", ob) == {"olcu": (120, 120)}
    assert C.okuma_cevabi("120x180 yerine 120x120", ob) == {"olcu": (120, 120)}
    assert C.okuma_cevabi("büyük olsun", ob) is None


def test_ve_ile_baglanan_istekler_ayrilir():
    """Geometri hakemi ikinci tur (13.10): "ve"/"ile" iki yanında da istek çapası varsa ayrı cümle; değilse tek cümle. Bölünemeyen iki
    istek ya da ölçü dışı sayı belirsizdir (sorulur), sessizce düşmez."""
    assert CO._parcalar("mutfak penceresi 120x120 ve dışlar 140'lık olsun") == ["mutfak penceresi 120x120", "dışlar 140'lık olsun"]
    assert CO._parcalar("dış duvarlar 140'lık olsun ve çatı L olsun") == ["dış duvarlar 140'lık olsun", "çatı L olsun"]
    assert CO._parcalar("mutfak ve salon pencereleri 120x120") == ["mutfak ve salon pencereleri 120x120"]
    assert CO._parcalar("mutfak penceresini 120x120 ile değiştirelim") == ["mutfak penceresini 120x120 ile değiştirelim"]
    assert CO._parcalar("salon ve mutfak pencereleri 120x120 ve dışlar 140") == ["salon ve mutfak pencereleri 120x120", "dışlar 140"]
    r = CO.oku("mutfak penceresi 120x120 ve dışlar 140'lık olsun", C8801, KATALOG)
    assert adlar(r) == ["P5"] and r["dis140"] is True
    r = CO.oku("dış duvarlar 140'lık olsun ve çatı L olsun", C8801, KATALOG)
    assert r["dis140"] is True and r["cati"] == "Ç8801L" and CO.cati_okumasi("dış duvarlar 140'lık olsun ve çatı L olsun", KATALOG) == "Ç8801L"
    for s in ("mutfak penceresi 120x120 dışlar 140", "yatak odası 1 ve 2 pencereleri 120x180", "2 tane pencere 120x120"):
        r = CO.oku(s, C8801, KATALOG)
        assert r["belirsiz"] and r["pencereler"] == [] and r["dis140"] is False, s


def test_ucuncu_tur_cati_kararsizligi_ve_bagimsiz_parca():
    """Geometri hakemi üçüncü tur (13.10): tek başına "K"/"L" çapa değil; çatı harfi taşıyan parça bağımsız değil; mesajda iki ayrı çatı
    geçiyorsa seçim yok. Tanınmayan içerik taşıyan "ve" parçası ("dış cephe gri olsun") kendi cümlesidir."""
    for s in ("çatı K ile L arasındaki fark nedir?", "çatı K ve L'yi görelim", "çatı K ile L arasında kaldım", "Ç8801K ve Ç8801L arasında kararsızım",
              "K ve L seçeneklerini gönderin", "çatı K mı olur L mi?"):
        assert CO.cati_okumasi(s, KATALOG) is None, s
        assert CO.oku(s, C8801, KATALOG)["cati"] is None, s
    assert CO._parcalar("çatı L ve dış cephe gri olsun") == ["çatı L", "dış cephe gri olsun"]
    assert CO._parcalar("çatı K ile L arasındaki fark nedir?") == ["çatı K ile L arasındaki fark nedir?"]
    assert CO.cati_okumasi("çatı L ve dış cephe gri olsun", KATALOG) == "Ç8801L"
    oda = [p for p in CO.oku("Salon, mutfak, banyo.", C8801, KATALOG)["parcalar"]]
    assert all(p["tur"] == "belirsiz" and p["neden"] == "oda" for p in oda)
    assert CO.degisiklik_var("mutfak penceresi 120x120") and not CO.degisiklik_var("çatı nasıl olacak?")


def test_dorduncu_tur_cati_secenekleri():
    """Geometri hakemi dördüncü tur (13.10): çatı seçenekleri cümle cümle; değişimin kaynağı seçenek değildir ("K'dan L'ye", "K yerine L",
    "Ç8801'den …"); katalog çatısı seçenektir; iki seçenekli çatı cümlesinin belirsizliği başka bir değişiklikle birlikte de kalır (önce
    okumanın sonunda siliniyordu: K-1); şekil sözlü tek harf ("L tipi mutfak") çatı değildir."""
    M = C8801["mahaller"]
    for s, kod in (("çatıyı K'dan L'ye çevirelim", "Ç8801L"), ("Ç8801K yerine Ç8801L olsun", "Ç8801L"), ("çatıyı K yerine L yapalım", "Ç8801L"),
                   ("L yerine K olsun", "Ç8801K"), ("Ç8801'den Ç8801K'ya geçelim", "Ç8801K"), ("çatıyı L yapalım", "Ç8801L"),
                   ("Ç8801 katalog çatısı", "Ç8801"), ("Ç8801 çelik ev, çatı L olsun", "Ç8801L")):
        assert CO.cati_okumasi(s, KATALOG, M) == kod, s
    assert CO.cati_kaynak_kodlari("Ç8801K yerine Ç8801L olsun") == {"c8801k"} and CO.cati_kaynak_kodlari("Ç8801'den Ç8801K'ya") == {"c8801"}
    for s in ("Ç8801K mi katalog çatısı mı olsun?", "Ç8801L mi Ç8801 mi olsun?", "Ç8801K olsun ama çatısı katalogdaki gibi olsun",
              "Ç8801K ile katalog çatısı arasında kaldım", "çatı K ya da L olsun"):
        assert len(CO.cati_secenekleri(s, M, "c8801")) == 2 and CO.cati_okumasi(s, KATALOG, M) is None, s
    assert CO.cati_secenekleri("Ç8801K olsun, L tipi mutfak olsun", M) == {"k"} and CO.cati_secenekleri("katalogdaki Ç8801K olsun") == {"k"}
    assert CO.cati_secenekleri("çatı L tipi olsun") == {"l"}                                          # çatı sözüyle şekil: çatı L
    r = CO.oku("çatıyı K'dan L'ye çevirelim, mutfak penceresi de 120x120 olsun", C8801, KATALOG)
    assert r["cati"] == "Ç8801L" and adlar(r) == ["P5"] and not r["cati_belirsiz"]
    for s in ("mutfak penceresi 120x120 olsun, çatı K ve L olsun", "çatı K ya da L olsun, dışlar 140'lık olsun", "K ve L"):
        r = CO.oku(s, C8801, KATALOG)
        assert r["cati"] is None and r["cati_belirsiz"] is True, s
    # harfsiz "çatı" sözü bilgi cümlesini engellemez (İ-1); tanınmayan oda adı ayrı cümle değildir (İ-3); duvar sorusunda 140 işareti (Ö-2)
    p = CO.parca_oku("çatı rengi kırmızı olsun", C8801, KATALOG)
    assert p["tur"] == "baska" and not any(p["isaret"].values())
    assert CO.parca_oku("çatı rengi L olsun", C8801, KATALOG)["isaret"]["cati"] is True
    assert CO._parcalar("çatı ve dış cephe gri olsun", M) == ["çatı ve dış cephe gri olsun"]
    assert CO._parcalar("çalışma odası ve mutfak pencereleri 120x120", M) == ["çalışma odası ve mutfak pencereleri 120x120"]
    assert CO._parcalar("mutfak penceresi 120x120 ve banyo fayansı beyaz olsun", M) == ["mutfak penceresi 120x120", "banyo fayansı beyaz olsun"]
    p = CO.parca_oku("duvarlar 140 olabilir mi?", C8801, KATALOG)
    assert (p["tur"], p["neden"], p["olumsuz"], p["d140"]) == ("belirsiz", "dis", True, True)
    p = CO.parca_oku("dış duvar kalınlığı ne kadar?", C8801, KATALOG)
    assert (p["tur"], p["neden"], p["d140"]) == ("belirsiz", "dis", False)


def test_besinci_tur_olumsuz_cati_bagimsiz_parca_cati_sekli():
    """Geometri hakemi beşinci tur (13.10): çatı seçeneği taşıyan olumsuz cümle kararsızlıktır ("yok"/"hayır" değil); kendi başına
    "başka" olan "ve" parçası (oda sözü taşısa da) ayrı cümledir, yalın oda adı değildir; çatı şekli/eğimi değişiklik işaretidir, renk ve
    malzeme değildir; odaya pencere yapmak eklemedir; oda dönüşümü başkadır."""
    M = C8801["mahaller"]
    for s in ("Ç8801L olmasın", "Ç8801K'dan Ç8801L'ye geçmeyelim", "Ç8801K'dan bir tane olsun, Ç8801L değil", "Ç8801 çelik, Ç8801L istemiyoruz",
              "çatı L olmasın", "K'ya çevirmeyin"):
        assert CO.cati_olumsuz(s, M) is True, s
    for s in ("Ç8801K olsun başka değişiklik yok", "Ç8801K olsun, dışlar 140 olmasın", "çatı L olsun", "mutfak penceresi 120x120 olmasın"):
        assert CO.cati_olumsuz(s, M) is False, s
    assert CO._parcalar("dışlar 140'lık olsun ve oda kapıları beyaz olsun", M) == ["dışlar 140'lık olsun", "oda kapıları beyaz olsun"]
    assert CO._parcalar("dışlar 140'lık olsun ve odalar geniş olsun", M) == ["dışlar 140'lık olsun", "odalar geniş olsun"]
    assert CO._parcalar("mutfak penceresi 120x120 ve misafir odası büyük olsun", M) == ["mutfak penceresi 120x120", "misafir odası büyük olsun"]
    assert CO._parcalar("çalışma odası ve mutfak pencereleri 120x120", M) == ["çalışma odası ve mutfak pencereleri 120x120"]   # dördüncü tur
    for s in ("büyük banyo ve mutfak pencereleri 120x120", "geniş salon ve mutfak pencereleri 120x120", "küçük hol ve banyo vasistası 60x60"):
        assert CO._parcalar(s, M) == [s], s                                  # yüklemsiz oda tarifi pencere cümlesine aittir
    assert CO._parcalar("mutfak penceresi 120x120 ve salonu büyütelim", M) == ["mutfak penceresi 120x120", "salonu büyütelim"]
    assert sorted(adlar(CO.oku("büyük banyo ve mutfak pencereleri 120x120", C8801, KATALOG))) == ["P5", "P7"]
    r = CO.oku("dışlar 140'lık olsun ve oda kapıları beyaz olsun", C8801, KATALOG)
    assert r["dis140"] is True and r["baska"] == ["oda kapıları beyaz olsun"]
    for s in ("çatı eğimi dik olsun", "çatı şekli kırma olsun", "çatıyı tek yöne eğimli yapalım", "çatı düz olsun"):
        p = CO.parca_oku(s, C8801, KATALOG)
        assert p["tur"] == "baska" and p["isaret"]["cati"] is True, s
    for s in ("çatı rengi kırmızı olsun", "çatı kaplaması shingle olsun"):
        assert CO.parca_oku(s, C8801, KATALOG)["isaret"]["cati"] is False, s
    for s in ("salona pencere yapabilir misiniz?", "mutfağa bir pencere yapalım", "yatak odasına pencere yapalım"):
        assert CO.parca_oku(s, C8801, KATALOG)["tur"] == "ekle_kaldir", s
    assert CO.parca_oku("salondaki pencereyi 120x120 yapalım", C8801, KATALOG)["tur"] == "pencere"
    for s in ("salonu yatak odasına dönüştürelim", "mutfağı kilere çevirelim"):
        assert CO.parca_oku(s, C8801, KATALOG)["tur"] == "baska", s
    assert CO.cati_okumasi("çatıyı K'dan L'ye çevirelim", KATALOG, M) == "Ç8801L"


def test_altinci_tur_olumsuz_bicimler_tarif_cumleleri_cati_sekli():
    """Geometri hakemi altıncı tur (13.10): listede olmayan olumsuz biçimler ("beğenmiyoruz", "beğenmedik", "gereksiz", "gerek yok",
    "hariç", "olmadı", "istemedik", "… yok") çatıyı olumsuz yapar; yüklemsiz tarif ("salonun sol duvarı", "salondaki büyük", "boyu 180")
    pencere cümlesinden bölünmez; "kalsın"lı cümle ayrıdır; bulunma eki ve "pencereyi" ekleme değildir; çatıya özgü şekil sözü ayrı
    cümlede de işarettir."""
    M = C8801["mahaller"]
    for s in ("L çatıyı beğenmiyoruz", "L çatıyı beğenmedim", "L çatı gereksiz", "katalog çatısını beğenmedik", "Ç8801L'ye gerek yok",
              "Ç8801 çelik ev, Ç8801L hariç", "Ç8801L olmadı", "Ç8801L yok", "Ç8801L'yi istemedik"):
        assert CO.cati_olumsuz(s, M) is True and CO.cati_okumasi(s, KATALOG, M) is None, s
    assert CO.cati_olumsuz("çatı L olsun, beğendik", M) is False and CO.cati_okumasi("çatı L olsun, beğendik", KATALOG, M) == "Ç8801L"
    for s in ("salonun sol duvarı ve arka duvarındaki pencereler 120x120 olsun", "salondaki büyük ve mutfaktaki küçük pencereler 120x120 olsun",
              "salonun ön duvarındaki ve mutfağın arka duvarındaki pencereler 120x120 olsun", "mutfak penceresinin eni 120 ve boyu 180 olsun",
              "küçük misafir yatak odası ve mutfak pencereleri 120x120 olsun", "mutfak penceresini 120x120 ile değiştirelim"):
        assert CO._parcalar(s, M) == [s], s
    assert CO._parcalar("salon aynı kalsın ve mutfak penceresi 120x120 olsun", M) == ["salon aynı kalsın", "mutfak penceresi 120x120 olsun"]
    assert CO._parcalar("mutfak penceresi 120x120 ve gerisi aynı kalsın", M) == ["mutfak penceresi 120x120", "gerisi aynı kalsın"]
    assert [p["tur"] for p in CO.oku("salon aynı kalsın ve mutfak penceresi 120x120 olsun", C8801, KATALOG)["parcalar"]] == ["bos", "pencere"]
    for s in ("mutfakta pencereyi 120x120 yapalım", "1. yatak odasında pencereyi 120x180 yapalım", "antre penceresini 120x180 yapalım"):
        assert CO.parca_oku(s, C8801, KATALOG)["tur"] == "pencere", s
    for s in ("şekli kırma olsun", "eğimi dik olsun", "mahya yüksek olsun", "çatı kiremit kaplı piramit olsun", "çatı kırmızı mansard olsun"):
        assert CO.parca_oku(s, C8801, KATALOG)["isaret"]["cati"] is True, s
    assert CO.parca_oku("çatı tek renk olsun", C8801, KATALOG)["isaret"]["cati"] is False
    from beyin import celik
    assert celik.ozellikleri_esle({"Çatı Eğimi": "dik", "Dış Kapı": "çelik", "Dış Boya Rengi": "krem", "Kapı Rengi": "beyaz"}) == \
        ({"Dış Boya Rengi": "krem"}, ["Çatı Eğimi: dik", "Dış Kapı: çelik", "Kapı Rengi: beyaz"])   # hesaplanan satır ezilmez


def test_yedinci_tur_eksiltili_istek_sifat_yonelme():
    """Geometri hakemi yedinci tur (13.10): oda sözünden sonra gelen sıfat eksiltili istektir ("odalar geniş ve mutfak penceresi 120x120
    olsun": ayrı cümle; önce pencere cümlesine katılıp düşüyordu), önce gelen sıfat ve "-daki" eki tariftir; ölçü devamı ("yüksekliği 300
    olsun") ayrı cümle değildir; "-maz/-mez" sıfatı ("su geçirmez") olumsuz değildir, yeterlik olumsuzu ("olamaz") olumsuzdur; sonu t/d
    ile biten odanın yönelme hâli ("tuvalete") ve çoğul "pencereler" eklemedir; "gerek yok" yalnız çatı sözüne bağlıysa çatıyı olumsuz yapar."""
    M = C8801["mahaller"]
    for s, n in (("odalar geniş ve mutfak penceresi 120x120 olsun", 2), ("mutfak büyük ve penceresi 120x120 olsun", 2),
                 ("banyo daha büyük ve mutfak penceresi 120x120 olsun", 2), ("dış duvarlar kalın olsun ve mutfak penceresi 120x120 olsun", 2),
                 ("salon aynı kalacak ve mutfak penceresi 120x120 olsun", 2), ("odalar geniş ve dışlar 140'lık olsun", 2),
                 ("salondaki büyük ve mutfaktaki küçük pencereler 120x120 olsun", 1), ("büyük banyo ve mutfak pencereleri 120x120", 1),
                 ("dışlar 140'lık olsun ve yüksekliği 300 olsun", 1)):
        assert len(CO._parcalar(s, M)) == n, s
    for w, sinif in (("gecirmez", "bilinmeyen"), ("paslanmaz", "bilinmeyen"), ("kirilmaz", "bilinmeyen"), ("olamaz", "olumsuz"),
                     ("yapilamaz", "olumsuz"), ("begenmez", "olumsuz")):
        assert CO._sinifla(w) == sinif, w
    assert CO.parca_oku("dış cephe su geçirmez olsun", C8801, KATALOG)["tur"] == "baska"
    for s in ("tuvalete 80x50 pencere yapalım", "müştemilata pencere yapalım", "salona pencereler yapalım", "WC'ye 80x50 pencere yapalım",
              "salona iki pencere daha yapalım"):
        assert CO.parca_oku(s, C8801, KATALOG)["tur"] == "ekle_kaldir", s
    assert CO.parca_oku("tuvalette pencereyi 60x60 yapalım", C8801, KATALOG)["tur"] == "pencere"
    for s, beklenen in (("Ç8801L olsun başka bir şeye gerek yok", False), ("Ç8801K olsun harici tuvalet olsun", False), ("L çatı olamaz", True)):
        assert CO.cati_olumsuz(s, M) is beklenen, s
