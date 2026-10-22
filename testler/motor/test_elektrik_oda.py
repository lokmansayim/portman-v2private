"""BK-12 PR-2f · Elektrik oda kuralı (Lokman, 18 Ekim 19:52: "15 m² ye kadar her bir odaya 2 piriz 1 tane anahtar, 1 tane duy ve lamba
koyarsın, 15 m² ye kadar verandalara 2 glop 1 tane 2li anahtar koyarsın"; kartlar 19 Ekim 16:50 "Her 15 m2'ye bir takım" ve "Kitaptaki gibi";
22 Ekim 11:09–11:10 "Uygula", "Her eve 1", "Yukarı").

- Paftada elektrik sayımı yoksa noktalar odalardan: öteki her oda takım × (2 tekli priz, 1 tekli anahtar, 1 duy); açık mahal takım × (2 glop,
  1 çiftli anahtar); takım = alan ÷ 15, yukarı, en az 1. Banyo, WC, mutfak ve hol kitabın sayılarını alır (ıslak hacimler banyo, koridor hol
  gibi). Mutfağı ayrı mahal olmayan evde mutfağın kitap sayıları salona (açık mutfak). Uydu prizi her evde 1.
- Odalar adla birleşir (L biçimli oda tek oda; aynı ad farklı türde olamaz). Sayım varsa sayım geçer, kuralın sonucu aday sütununda. Zil her
  evde kitabın 1'i.
- `sigorta_en_uzak` pafta kipinde Motor kipindeki biçimde (`{m, nereden}`); biçimi yanlışsa liste üretilmez.
"""
from __future__ import annotations
import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
NOKTA = {"Tijli duy": "tavan_armaturu", "Yuvarlak glop": "glop", "Tekli anahtar (takım)": "anahtar_tekli", "Çiftli anahtar (takım)": "anahtar_cift",
         "Tekli priz (takım)": "priz_tekli", "Çiftli priz (takım)": "priz_cift", "Uydu prizi (takım)": "uydu_prizi"}


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kurallar():
    return PL.kurallari_oku()


@pytest.fixture(scope="module")
def N():
    return PL.model_motor(_oku(VERI / "PK01.json"))


def _satir(L: dict, kalem: str) -> dict:
    s = [x for x in L["satirlar"] if x["kalem"] == kalem]
    assert len(s) == 1, (kalem, len(s))
    return s[0]


def _adet(L: dict) -> dict:
    return {a: _satir(L, k)["adet"] for k, a in NOKTA.items()}


def _oda(ad: str, tur: str, alan: float) -> dict:
    return {"ad": ad, "tur": tur, "alan_m2": alan, "en_cm": 300.0, "derin_cm": 100 * alan / 3}


def _ev(kapali, acik=(), **d) -> dict:
    """Pafta kipinde 8 × 6 m beşik ev; açık mahal varsa dış duvar boyları okunmuş."""
    yp = {"H0": 250.0, "W": 800.0, "D": 600.0, "t_dis": 10.0, "panolar": [], "ekler": [], "koseler": {"dis": 4}, "dikmeler": 0,
          "veranda_kirisleri_cm": [], "kapali": list(kapali), "acik": list(acik), "ozellikler": {}, "alici_ait": {},
          "cati": [{"ad": "ana çatı", "tip": "besik", "aciklik_cm": 600.0, "boy_cm": 800.0, "egim_yuzde": 33.0, "sacak_cm": 30.0}]}
    if acik:
        yp.update(dis_cevre_m=28.0, ic_kalan_dis_duvar_m=0.0)
    yp.update(d)
    return PL.model_pafta(yp)


def _kural(N: dict, kurallar: dict) -> dict:
    R = kurallar["prefabrik"]["kurallar"]
    return PL.elektrik_oda(N, R["elektrik_oda"]["deger"], kurallar["ortak"]["elektrik_oda"]["deger"]["odalar"], R["elektrik_acik_mutfak"]["deger"])[0]


def test_pk01_elle_hesap(N, kurallar):
    """PK-01 (paftada elektrik sayımı yok): odaların hepsi 15 m²'nin altında. İki yatak odası ve salon oda takımı, banyo, mutfak ve hol kitaptan,
    veranda veranda takımı. Buat anahtar 7 + priz 15 + oda 6; NYM 8 × 8,58 + 16 × 2 → 101 ve 8 × 8,58 + 8 × 2 → 85."""
    L = PL.liste(copy.deepcopy(N), kurallar, _oku(VERI / "PK01_pafta_katmani.json"))
    assert _adet(L) == {"tavan_armaturu": 5, "glop": 3, "anahtar_tekli": 6, "anahtar_cift": 1, "priz_tekli": 13, "priz_cift": 1, "uydu_prizi": 1}
    assert [_satir(L, k)["adet"] for k in ("Ampul", "Zil", "Sigorta kutusu (12'li)", "Buat kasa", "NYM kablo 3 × 2,5", "NYM kablo 2 × 1,5", "Uydu kablo")] == \
        [8, 1, 1, 28, 101, 85, 25]
    s = _satir(L, "Tekli priz (takım)")
    assert s["dayanak"] == "Kural (Lokman 18.10, oda başına)" and s["aday"] is None
    assert s["formul"] == "YATAK ODASI 1: 2 + BANYO: 2 (kitap) + YATAK ODASI 2: 2 + MUTFAK: 5 (kitap) + SALON: 2"
    assert _satir(L, "Yuvarlak glop")["formul"] == "BANYO: 1 (kitap) + VERANDA: 2"
    assert _satir(L, "Uydu prizi (takım)")["formul"] == "her evde 1"
    assert "Elektrik grubu" not in {x["kalem"] for x in L["satirlar"]} and L["ozet"]["kural_yok"] == 0


@pytest.mark.parametrize("alan, takim", [(14.98, 1), (15.0, 1), (15.1, 2), (22.4, 2), (22.5, 2), (30.0, 2), (30.1, 3), (0.5, 1)])
def test_takim_yukari(kurallar, alan, takim):
    """Kart 22 Ekim 11:10 "Yukarı": 15 m²'yi geçen her oda 2 takım, 30'u geçen 3 takım; en az 1. Veranda da aynı (kart 19 Ekim 16:50)."""
    k = _kural(_ev([_oda("YATAK ODASI", "yatak_odasi", alan)], [_oda("VERANDA", "veranda", alan)]), kurallar)
    assert (k["priz_tekli"], k["anahtar_tekli"], k["tavan_armaturu"]) == (2 * takim, takim, takim)
    assert (k["glop"], k["anahtar_cift"]) == (2 * takim, takim)


def test_kartin_ornegi_26_m2_salon(kurallar):
    """Kart 19 Ekim 16:50: "26 m2'lik salon 2 takım alır: 4 priz, 2 anahtar, 2 duy". Formül takımı ve alanı yazar; mutfak kitaptan (5 tekli
    priz, 1 anahtar, 1 duy)."""
    L = PL.liste(_ev([_oda("SALON", "salon", 26.0), _oda("MUTFAK", "mutfak", 8.0)]), kurallar)
    assert (_satir(L, "Tekli priz (takım)")["adet"], _satir(L, "Tekli anahtar (takım)")["adet"], _satir(L, "Tijli duy")["adet"]) == (4 + 5, 2 + 1, 2 + 1)
    assert _satir(L, "Tekli priz (takım)")["formul"] == "SALON (26,0 m²): 2 takım × 2 + MUTFAK: 5 (kitap)"


@pytest.mark.parametrize("alan, yazi", [(15.04, "15,04 m²): 2 takım"), (30.04, "30,04 m²): 3 takım"), (15.0001, "15,0001 m²): 2 takım"),
                                        (26.0, "26,0 m²): 2 takım"), (18.18, "18,2 m²): 2 takım")])
def test_alan_yazisi_takimla_tutar(kurallar, alan, yazi):
    """Formüldeki alan takım sayısını elle sağlatır: tek basamak yetmezse basamak artar (15,04 m² "15,0" yazılsa 1 takım okunurdu; hakem, 22 Ekim)."""
    L = PL.liste(_ev([_oda("ODA", "yatak_odasi", alan)]), kurallar)
    assert yazi in _satir(L, "Tekli priz (takım)")["formul"]


def test_kitaptaki_gibi_ve_oteki_odalar(kurallar):
    """Kart 19 Ekim 16:50 "Kitaptaki gibi": banyo, mutfak ve hol (antre ve koridor da) kitabın sayılarını alır, WC ve öteki ıslak hacimler
    (ıslak, lavabo) banyo gibi; 15 m²'yi geçse de takım çarpanı yok. Çamaşır, depo, teknik, çalışma, giyinme, oturma ve "diğer" oda takımını alır
    (kart: "öteki odalar sizin kuralınızla"; kitabın depo satırı okunmaz, `kitapla_farkli`)."""
    kitap = kurallar["ortak"]["elektrik_oda"]["deger"]["odalar"]
    for tur, ko in (("banyo", "banyo"), ("wc", "banyo"), ("islak", "banyo"), ("lavabo", "banyo"), ("mutfak", "mutfak"), ("antre_hol", "hol"),
                    ("hol", "hol"), ("koridor", "hol")):
        k = _kural(_ev([_oda("ODA", tur, 20.0)]), kurallar)
        beklenen = {PL.ELEKTRIK_NOKTALARI[a]: n for a, n in kitap[ko].items()}
        assert {a: n for a, n in k.items() if n and a != "uydu_prizi"} == beklenen, tur
    for tur in ("camasir", "depo", "teknik", "calisma", "giyinme", "oturma", "diger", "yatak_odasi"):
        k = _kural(_ev([_oda("ODA", tur, 9.0)]), kurallar)
        assert {a: n for a, n in k.items() if n and a != "uydu_prizi"} == {"priz_tekli": 2, "anahtar_tekli": 1, "tavan_armaturu": 1}, tur


def test_islak_hacimler_banyo_gibi(kurallar):
    """Listenin ıslak hacim saydığı her tür (`islak_hacim`: tavan, duvar, sıhhi takım) elektrikte de banyo gibi sayılır; iki kural ayrışmaz."""
    R = kurallar["prefabrik"]["kurallar"]
    assert {t: R["elektrik_oda"]["deger"]["kitaptan"].get(t) for t in R["islak_hacim"]["deger"]} == dict.fromkeys(R["islak_hacim"]["deger"], "banyo")


def test_acik_mahaller_ve_uydu(kurallar):
    """Açık mahal (veranda, sundurma, teras, balkon) veranda takımını alır: 18 m² veranda 2 takım (kart 19 Ekim 16:50 veranda için de). Uydu
    prizi oda sayısından bağımsız her evde 1 (kart 22 Ekim 11:09); odasız evde de."""
    k = _kural(_ev([_oda("SALON", "salon", 12.0)], [_oda("VERANDA", "veranda", 18.0), _oda("SUNDURMA", "sundurma", 4.0)]), kurallar)
    assert (k["glop"], k["anahtar_cift"], k["uydu_prizi"]) == (6, 3, 1)
    assert _kural(_ev([]), kurallar) == dict.fromkeys(PL.ELEKTRIK_NOKTALARI.values(), 0) | {"uydu_prizi": 1}


def test_oda_adla_birlesir(kurallar):
    """L biçimli oda aynı adlı parçalarla gelir (PK-03'te salon 15,25 + 2,93): tek oda, alanları toplanır (18,18 m² → 2 takım). Ayrı adlı iki
    oda ayrı sayılır; buat kasadaki oda sayısı da adla."""
    L = PL.liste(_ev([_oda("SALON", "salon", 15.25), _oda("SALON", "salon", 2.93), _oda("YATAK ODASI 1", "yatak_odasi", 9.0),
                      _oda("YATAK ODASI 2", "yatak_odasi", 9.0), _oda("MUTFAK", "mutfak", 8.0)]), kurallar)
    assert _satir(L, "Tekli priz (takım)")["formul"] == "SALON (18,2 m²): 2 takım × 2 + YATAK ODASI 1: 2 + YATAK ODASI 2: 2 + MUTFAK: 5 (kitap)"
    assert _satir(L, "Tekli priz (takım)")["adet"] == 13
    assert "oda 4 " in _satir(L, "Buat kasa")["formul"]


def test_ayni_ad_farkli_tur(kurallar):
    """Aynı adlı parçalar tek oda sayılır; türleri farklıysa (salon ile mutfak aynı adla) mutfağın kitap sayıları sessizce düşmez, liste
    üretilmez (hakem, 22 Ekim)."""
    with pytest.raises(ValueError, match="farklı türde"):
        PL.liste(_ev([_oda("SALON", "salon", 10.0), _oda("SALON", "mutfak", 8.0)]), kurallar)


def test_acik_mutfak(kurallar):
    """Mutfak ayrı mahal değilse (açık mutfak, `elektrik_acik_mutfak`, varsayım, Lokman'ın kartı bekleniyor; planlayıcının varsayılanı, PK-08
    ve P6001 "yaşam alanı", TS-01 "salon & mutfak") mutfağın kitap sayıları salona eklenir, salonun oda takımına ek olarak (kitap birleşik mahale
    ikisinin kuralını uygular). Birden çok salon türlü odada ilkine. Mutfak ayrıysa salona eklenmez. Salon da yoksa mutfak noktası yazılmaz,
    satırın yazısı uyarıyla başlar (sessiz değil)."""
    kitap = kurallar["ortak"]["elektrik_oda"]["deger"]["odalar"]["mutfak"]
    L = PL.liste(_ev([_oda("SALON & MUTFAK", "salon", 20.0), _oda("OTURMA", "salon", 9.0), _oda("YATAK ODASI", "yatak_odasi", 9.0)]), kurallar)
    assert _adet(L) == {"tavan_armaturu": 2 + 1 + 1 + kitap["tijli_duy"], "glop": 0, "anahtar_tekli": 2 + 1 + 1 + kitap["tekli_anahtar"],
                        "anahtar_cift": 0, "priz_tekli": 4 + 2 + 2 + kitap["tekli_priz"], "priz_cift": kitap["cift_priz"], "uydu_prizi": 1}
    assert _satir(L, "Tekli priz (takım)")["formul"] == ("SALON & MUTFAK (20,0 m²): 2 takım × 2 + SALON & MUTFAK (açık mutfak): 5 (kitap) + "
                                                         "OTURMA: 2 + YATAK ODASI: 2")
    assert _satir(L, "Çiftli priz (takım)")["formul"] == "SALON & MUTFAK (açık mutfak): 1 (kitap)"
    ayri = _kural(_ev([_oda("SALON", "salon", 12.0), _oda("MUTFAK", "mutfak", 8.0)]), kurallar)
    assert (ayri["priz_tekli"], ayri["priz_cift"]) == (2 + kitap["tekli_priz"], kitap["cift_priz"])
    L = PL.liste(_ev([_oda("YATAK ODASI", "yatak_odasi", 9.0)]), kurallar)
    assert (_satir(L, "Tekli priz (takım)")["adet"], _satir(L, "Çiftli priz (takım)")["adet"]) == (2, 0)
    for kalem in ("Tijli duy", "Tekli anahtar (takım)", "Tekli priz (takım)", "Çiftli priz (takım)"):
        assert _satir(L, kalem)["formul"].startswith("UYARI: mutfak ayrı mahal değil, açık mutfağın odası da yok; mutfağın kitap noktaları yazılmadı.")
    assert _satir(L, "Yuvarlak glop")["formul"] == "oda kuralında yok"


def test_odasiz_girdi_uyarir(kurallar):
    """Girdide kapalı oda yoksa (odaları okunmamış pafta) oda noktalarının 0'ı kural sonucu gibi yazılmaz: uydu dışındaki nokta satırları uyarıyla
    başlar; açık mahalin takımı yine sayılır (hakem, 22 Ekim)."""
    L = PL.liste(_ev([], [_oda("VERANDA", "veranda", 10.0)]), kurallar)
    for kalem, a in NOKTA.items():
        assert _satir(L, kalem)["formul"].startswith("UYARI: girdide kapalı oda yok; oda noktaları sayılmadı.") == (a != "uydu_prizi"), kalem
    assert _satir(L, "Yuvarlak glop")["formul"] == "UYARI: girdide kapalı oda yok; oda noktaları sayılmadı. VERANDA: 2"
    assert (_adet(L)["glop"], _adet(L)["priz_tekli"]) == (2, 0)


def test_sayim_varsa_sayim_gecer(N, kurallar):
    """Paftada elektrik sayımı varsa satırlar sayımdan (kesin sayı); oda kuralının sonucu aday sütununda, dökümü aday notunda. Zil her evde
    kitabın 1'i: paftanın sayımı 0 olsa da (PK-07), sayım pafta sütununda. Sigorta kutusunda aday kitabın kat başına 1'i."""
    say = {"priz_tekli": 6, "priz_cift": 4, "anahtar_tekli": 5, "anahtar_cift": 2, "uydu_prizi": 0, "zil": 0, "tavan_armaturu": 7, "glop": 2,
           "sigorta_kutusu": 1}
    pf = dict(_oku(VERI / "PK01_pafta_katmani.json"), elektrik={a: {"adet": n} for a, n in say.items()})
    L = PL.liste(copy.deepcopy(N), kurallar, pf)
    assert _adet(L) == {a: say[a] for a in NOKTA.values()}
    assert {a: _satir(L, k)["aday"] for k, a in NOKTA.items()} == _kural(N, kurallar)
    s = _satir(L, "Tekli priz (takım)")
    assert (s["dayanak"], s["formul"]) == ("Sayım (pafta)", "elektrik planından")
    assert s["aday_notu"] == "oda kuralı: YATAK ODASI 1: 2 + BANYO: 2 (kitap) + YATAK ODASI 2: 2 + MUTFAK: 5 (kitap) + SALON: 2"
    z = _satir(L, "Zil")
    assert (z["adet"], z["pafta"], z["formul"]) == (1, 0, "her evde 1")
    sk = _satir(L, "Sigorta kutusu (12'li)")
    assert (sk["adet"], sk["aday"]) == (1, 1)
    assert (_satir(L, "Ampul")["adet"], _satir(L, "Ampul")["aday"]) == (9, 8)
    b = _satir(L, "Buat kasa")                                  # anahtar 7 + priz 10 + oda 6; aday 7.3: bütün noktalar, zil dahil
    assert (b["adet"], b["aday"]) == (23, 7 + 10 + 7 + 2 + 1)
    assert _satir(L, "Uydu kablo")["adet"] == 0 and _satir(L, "Uydu kablo")["formul"] == "uydu prizi 0 × 25 m"


def test_sigorta_en_uzak_bicimi(kurallar):
    """Pafta kipinde sigortadan en uzak mesafe Motor kipindeki biçimde: `{"m": metre, "nereden": yazı}`. Verilirse NYM onu kullanır; biçimi
    yanlışsa liste üretilmez (pafta okuyucusunun sözleşmesi). Verilmezse dış ölçünün köşegeni (8 × 6 m → 10,00)."""
    oda = [_oda("YATAK ODASI", "yatak_odasi", 12.0)]
    L = PL.liste(_ev(oda, sigorta_en_uzak={"m": 7.5, "nereden": "paftada sigorta kutusundan en uzak köşe"}), kurallar)
    assert _satir(L, "NYM kablo 2 × 1,5")["formul"].startswith("sigorta 8 × en uzak 7,50 m (paftada sigorta kutusundan en uzak köşe)")
    assert _satir(L, "NYM kablo 2 × 1,5")["adet"] == 8 * 7.5 + 1 * 2
    assert "en uzak 10,00 m (kapının yeri girdide yok: dış ölçünün köşegeni)" in _satir(PL.liste(_ev(oda), kurallar), "NYM kablo 2 × 1,5")["formul"]
    for yanlis in ({"m": 0, "nereden": "x"}, {"m": "7,5", "nereden": "x"}, {"m": True, "nereden": "x"}, {"m": 7.5}, {"m": 7.5, "nereden": " "},
                   {"m": 7.5, "nereden": "x", "fazla": 1}, 7.5):
        with pytest.raises(ValueError, match="sigorta_en_uzak"):
            _ev(oda, sigorta_en_uzak=yanlis)


def test_kitapta_olmayan_oda_ve_nokta(kurallar):
    """Kuraldaki kitap odası kitapta yoksa ya da takımda tanınmayan bir nokta varsa liste üretilmez (sessizce 0 sayılmaz)."""
    k = copy.deepcopy(kurallar)
    k["prefabrik"]["kurallar"]["elektrik_oda"]["deger"]["kitaptan"]["wc"] = "tuvalet"
    with pytest.raises(ValueError, match="tuvalet"):
        PL.liste(_ev([_oda("WC", "wc", 3.0)]), k)
    k = copy.deepcopy(kurallar)
    k["prefabrik"]["kurallar"]["elektrik_oda"]["deger"]["oda_takimi"]["aplik"] = 1
    with pytest.raises(ValueError, match="aplik"):
        PL.liste(_ev([_oda("SALON", "salon", 12.0)]), k)
