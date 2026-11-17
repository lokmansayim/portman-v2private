"""D-121 (BK-52, PC-46): makas aksı kaymaz, makasa dik duvarda pencere tam ortada.

Lokman, 16 Kasım 2026 20:56:44: "makas yönündeki akslar çok önemli makasları o akslara oturtuyoruz ama makas yönüne dik olan akslar
kayabilir ama yine kurallı kaysın". Kartlar 21:14:20 "Okuma 1: aks kaymaz, yarım pano olur", 21:15:33 "Her zaman tam ortada",
21:36:53 "B) 125,5 pencere yanında, kalan uçta", 21:38:12 "Yalnız yeni çizilen evlere". Hedef örnek 60 m² (P6001 r03, Lokman'ın onayı
20:57): `testler/motor/veri/D121_beklenen.json`.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from motor import geometry as G

KOK = Path(__file__).resolve().parents[2]
VERI = KOK / "testler" / "motor" / "veri"


def _oku(yol: str) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _anahtarli(ie: dict) -> dict:
    ie = copy.deepcopy(ie)
    ie["yapi"].setdefault("dizilim", {})["dik_duvar_pencere"] = "tam_orta"
    return ie


def _dizilim(plan) -> dict:
    return {f"{d.tur} {d.yon} {d.c:g}": [[round(q.a0, 3), round(q.boy, 3), q.acilim.tur if q.acilim else ""] for q in d.panolar]
            for d in plan.duvarlar}


def test_hedef_ornek_60m2():
    """Kuralla kurulan 60 m², Lokman'ın onayladığı r03 dizilimiyle pano pano aynı (A′ ek aksı ve dayanağı olmadan)."""
    hedef = json.loads((VERI / "D121_beklenen.json").read_text(encoding="utf-8"))
    plan = G.kur(_oku("testler/motor/veri/D121_60m2_is_emri.json"))
    assert _dizilim(plan) == {d["duvar"]: d["panolar"] for d in hedef["duvarlar"]}
    assert plan.dik_duvar_pencere == [{"duvar": "dis x 5", "once": [125.5, 125.5, 62.75], "sonra": [94.125, 125.5, 94.125]}]
    assert G.makas_aksi_denetimi(plan, "x") == []


def test_anahtarsiz_eski_yol():
    ie = _oku("testler/motor/veri/D121_60m2_is_emri.json")
    del ie["yapi"]["dizilim"]["dik_duvar_pencere"]
    plan = G.kur(ie)
    assert plan.dik_duvar_pencere == []
    d = next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "x" and abs(d.c - 5) < 1e-6)
    assert [round(q.boy, 3) for q in d.panolar] == [125.5, 125.5, 62.75]


def test_uzun_yan_125_pencere_yaninda_kalan_ucta():
    """Kart 21:36:53 "B": 87 m²'nin yatak odası 2 arka duvarı (466,25): 44,875 + 125,5 + pencere + 125,5 + 44,875."""
    plan = G.kur(_anahtarli(_oku("is_emri/adaylar/PA06.json")))
    assert {"duvar": "dis x 1083", "once": [125.5, 125.5, 125.5, 89.75], "sonra": [44.875, 125.5, 125.5, 125.5, 44.875]} \
        in plan.dik_duvar_pencere
    d = next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "x" and abs(d.c - 1083) < 1e-6)
    p = next(q for q in d.panolar if abs(q.a0 - 494.125) < 1e-6)
    assert p.acilim is not None and p.acilim.tur == "pencere" and abs(p.boy - 125.5) < 1e-9


def _kuru_oda(ie: dict, mahal: str, olcu: str = "120x120") -> dict:
    """D-124'ten sonra ıslak hacim ve vasistas penceresi kurala girmez. Kuralın kısa yan ve ortadaki T yolları bugün depoda yalnız ıslak
    hacimde vardı; o yollar odayı kuru oda, pencereyi 120'lik yaparak sınanır (uydurma girdi, hedef örnek değil)."""
    ie = copy.deepcopy(ie)
    for m in ie["mahaller"]:
        if m["ad"] == mahal:
            m["tur"] = "yatak_odasi"
    for a in ie["acikliklar"]:
        if a["tur"] == "pencere" and a.get("mahal") == mahal:
            a["olcu"] = olcu
    return ie


def test_kisa_yan_her_zaman_ortada():
    """Kart 21:15:33 "Her zaman tam ortada": 188,25'lik oda parçasında 31,375 + pencere + 31,375. 90 m²'nin bu parçası banyodur; banyonun
    vasistası D-124'ten beri yerinde kalır (`test_islak_hacim_ve_vasistas_yerinde`). Kural kuru odada sınanır."""
    plan = G.kur(_anahtarli(_kuru_oda(_oku("testler/motor/veri/TK01_r08.json"), "BANYO")))
    assert {"duvar": "dis x 883.5", "once": [125.5, 62.75], "sonra": [31.375, 125.5, 31.375]} in plan.dik_duvar_pencere


def test_islak_hacim_ve_vasistas_yerinde():
    """D-124 (Lokman, 17 Kasım 2026 08:35:02): "banyo ebeveyn banyo wc tuvalet yani vasistas pencresi ne varsa onlar kendi konumlarında
    kalacak ortalamıyacaksın". 90 m²'nin banyo vasistası yerinde; ıslak hacmin 120'liği de, kuru odanın 60×40'ı da yerinde (iki okuma birlikte)."""
    def banyo_duvari(ie):                                     # banyo penceresinin duvarındaki panolar (yer, boy)
        plan = G.kur(ie)
        d = next(d for d in plan.duvarlar if any(q.acilim and q.acilim.mahal == "BANYO" for q in d.panolar))
        return [(round(q.a0, 3), round(q.boy, 3)) for q in d.panolar], plan

    ie = _oku("testler/motor/veri/TK01_r08.json")
    once, _ = banyo_duvari(copy.deepcopy(ie))
    sonra, plan = banyo_duvari(_anahtarli(ie))
    assert sonra == once and [c for c in plan.dik_duvar_pencere if c["duvar"] == "dis x 883.5"] == []
    islak_120 = copy.deepcopy(ie)                             # ıslak hacim, 120'lik pencere: yerinde
    for a in islak_120["acikliklar"]:
        if a.get("mahal") == "BANYO":
            a["olcu"] = "120x120"
    assert banyo_duvari(_anahtarli(islak_120))[0] == banyo_duvari(copy.deepcopy(islak_120))[0]
    kuru_vasistas = _kuru_oda(ie, "BANYO", "60x40")           # kuru oda, vasistas: yerinde
    assert banyo_duvari(_anahtarli(kuru_vasistas))[0] == banyo_duvari(copy.deepcopy(kuru_vasistas))[0]
    kuru_120 = _kuru_oda(ie, "BANYO")                         # kuru oda, 120'lik: ortalanır
    assert banyo_duvari(_anahtarli(kuru_120))[0] != banyo_duvari(copy.deepcopy(kuru_120))[0]


@pytest.mark.parametrize("yol", ["is_emri/adaylar/PA06.json", "testler/motor/veri/TK01_r08.json", "is_emri/adaylar/PA39.json",
                                 "testler/motor/veri/D121_60m2_is_emri.json", "is_emri/YAN_VERANDALI_2plus1_6x8p5.json"])
def test_sacak_duvari_ve_ic_duvar_degismez(yol):
    """Kart 21:14:20 (Okuma 1): makasın oturduğu saçak duvarı ve iç duvarlar kuraldan etkilenmez; yalnız makasa dik dış duvar değişir."""
    ie = _oku(yol)
    (ie["yapi"].get("dizilim") or {}).pop("dik_duvar_pencere", None)
    me = (ie.get("cati") or {}).get("makas_ekseni", "x")
    once, sonra = _dizilim(G.kur(copy.deepcopy(ie))), _dizilim(G.kur(_anahtarli(ie)))
    for k in once:
        tur, yon, _ = k.split(" ")
        if tur != "dis" or yon != me:
            assert once[k] == sonra[k], k


def test_pencere_dis_olcu_ve_pano_sayisi():
    """Pencere odanın duvar parçasının tam ortasında; dış ölçü değişmez; açıklıksız pano 125,5'i aşmaz (D-69 denetimi geçer)."""
    for yol in ("is_emri/adaylar/PA06.json", "testler/motor/veri/TK01_r08.json", "testler/motor/veri/D121_60m2_is_emri.json"):
        ie = _oku(yol)
        p0, p1 = G.kur(copy.deepcopy(ie)), G.kur(_anahtarli(ie))
        assert (p0.W, p0.H) == (p1.W, p1.H)
        for c in p1.dik_duvar_pencere:
            s = c["sonra"]
            assert abs(sum(s) - sum(c["once"])) < 1e-6
            i = s.index(125.5) if len(s) == 3 else len(s) // 2
            assert abs(sum(s[:i]) - sum(s[i + 1:])) < 1e-6, c   # iki yan eşit


def test_bilinmeyen_deger_hata():
    ie = _anahtarli(_oku("testler/motor/veri/D121_60m2_is_emri.json"))
    ie["yapi"]["dizilim"]["dik_duvar_pencere"] = "oda_ortasi"
    with pytest.raises(G.IsEmriHatasi, match="dik_duvar_pencere bilinmiyor"):
        G.kur(ie)


def test_anahtarla_havuzun_her_evi_kurulur():
    """Yeni çizilen ev havuz evleri gibi olacak: havuzdaki her prefabrik İş Emri anahtarla da kurulur, D-69 denetimi geçer."""
    for f in sorted((KOK / "is_emri" / "adaylar").glob("*.json")):
        ie = json.loads(f.read_text(encoding="utf-8"))
        if not (isinstance(ie.get("yapi"), dict) and "grid" in ie["yapi"] and "mahaller" in ie):
            continue
        G.kur(_anahtarli(ie))


def test_makas_aksi_denetimi():
    """Hakem (kart 21:14:20): saçak duvarında ek tam ya da yarım aksta. 90 m² (yarım panolu) temiz; 37 m² paftasında 94,12'lik iki ek
    ızgara dışında (asıl proje havuzda aynen, D-103; hakem bulguyu söyler)."""
    assert G.makas_aksi_denetimi(G.kur(_oku("testler/motor/veri/TK01_r08.json")), "x") == []
    b = G.makas_aksi_denetimi(G.kur(_oku("is_emri/adaylar/PA39.json")), "y")
    assert len(b) == 2 and all("makas aksı kaymaz" in x for x in b)


def _t_ve_pencereler(plan) -> dict:
    """Her dış duvarda pano ekindeki T'ler ve pencerenin üstüne düşen T'ler (eksen, cm)."""
    cik = {}
    for d in plan.duvarlar:
        if d.tur != "dis":
            continue
        ts = G._t_noktalari(plan, d)
        ekler = [q.a1 for q in d.panolar[:-1]]
        pencereler = [(q.a0, q.a1) for q in d.panolar if q.acilim is not None and q.acilim.tur == "pencere"]
        cik[f"{d.yon} {d.c:g}"] = ([t for t in ts if any(abs(t - e) < 0.6 for e in ekler)],
                                   sorted(t for t in ts for a, b in pencereler if a + 0.6 < t < b - 0.6))
    return cik


def test_pencere_odasinda_kalir_t_ekleri_degismez():
    """Geometri hakemi (BK-52, 1. tur): oda duvarı panonun ortasındaki T'de (çektirme U) biter; pencere komşu odaya ya da iç duvarın
    üstüne geçmez, T ekleri yerinde kalır. Havuzdaki her prefabrik İş Emri anahtarla."""
    for f in sorted((KOK / "is_emri" / "adaylar").glob("*.json")):
        ie = json.loads(f.read_text(encoding="utf-8"))
        if not (isinstance(ie.get("yapi"), dict) and "grid" in ie["yapi"] and "mahaller" in ie):
            continue
        once, sonra = _t_ve_pencereler(G.kur(copy.deepcopy(ie))), _t_ve_pencereler(G.kur(_anahtarli(ie)))
        for k in once:
            assert sonra[k][0] == once[k][0], (f.name, k, "T eki değişti")
            assert sonra[k][1] == once[k][1], (f.name, k, "pencere T'nin üstüne geçti")


def test_ortadaki_t_odayi_keser_pa21_banyo():
    """PA-21: banyonun penceresi (386,5–512) yerinde; oda duvarı 323,75'teki T'de biter, pencere yatak odasına geçmez; uyarı yazılır.
    D-124'ten beri banyonun vasistası kurala hiç girmez; V6 yolu banyo kuru oda ve pencere 120'lik yapılarak sınanır."""
    ie = _kuru_oda(_oku("is_emri/adaylar/PA21.json"), "BANYO 1")
    once, sonra = G.kur(copy.deepcopy(ie)), G.kur(_anahtarli(ie))
    d0 = next(d for d in once.duvarlar if d.tur == "dis" and d.yon == "x" and abs(d.c - 1024) < 1e-6)
    d1 = next(d for d in sonra.duvarlar if d.tur == "dis" and d.yon == "x" and abs(d.c - 1024) < 1e-6)
    assert [(q.a0, q.boy) for q in d1.panolar] == [(q.a0, q.boy) for q in d0.panolar]
    assert any("panonun ortasındaki T" in u for u in sonra.uyarilar)


def test_kirma_catida_uygulanmaz():
    """Kırma çatıda makasa dik duvar da makas taşır (BK-46): kural uygulanmaz, plan anahtarsızla aynı, uyarı yazılır (VARSAYIM V7)."""
    for kod in ("PA08", "PA33"):
        ie = _oku(f"is_emri/adaylar/{kod}.json")
        assert ie["cati"]["tip"] == "kirma"
        sonra = G.kur(_anahtarli(ie))
        assert _dizilim(sonra) == _dizilim(G.kur(copy.deepcopy(ie)))
        assert sonra.dik_duvar_pencere == []
        assert any("kırma çatıda" in u for u in sonra.uyarilar)


def test_makas_aksi_denetimi_kirma_iki_yon():
    """Kırma çatıda hakem makasa dik duvarın eklerini de kendi ızgarasında denetler: 77 m² paftasında (PA-24) bir ek dışarıda."""
    ie = _oku("is_emri/adaylar/PA24.json")
    plan = G.kur(ie)
    assert G.makas_aksi_denetimi(plan, ie["cati"].get("makas_ekseni", "x")) == []
    b = G.makas_aksi_denetimi(plan, ie["cati"].get("makas_ekseni", "x"), "kirma")
    assert len(b) == 1 and b[0].startswith("Kırma çatının makasa dik duvarında")
