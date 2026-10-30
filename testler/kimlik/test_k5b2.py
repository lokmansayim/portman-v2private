"""İE-15 · K5b-2 · Tavan katmanı ve niş duvarının omegası (plan `Kimlik_Karti_Modeli/K5b2_tavan_plani.md`; CIO onayı 27 Ekim 23:11,
K5b satırı; OM-02 model atölyesinin K5b-1 notuyla).

- Niş duvarı omegası (OM-02; Lokman 21 Ekim, D-32): kapalı kısmın açık mahale (ana çatının altındaki veranda, giriş nişi) bakan dış duvarı
  100'lük duvar omegası alır. TK-01 r07'de ve PK-01'de kesim planının stoğu listenin "100'lük duvar omegası" adedi; boy listenin "çatı
  kenarına gelmeyen dış duvarlar" terimi, yalnız model duvarın ekseninde ölçer, liste dış çizgide (dış köşede yarım duvar, uç başına 5 cm).
  Parçalar `DIS_DUVAR_` önekli (montaj rehberi duvar omegalarını `OMEGA_` adıyla okur ve niş duvarını kendisi çizer) ve pafta anahtarı
  almaz (PK-01 paftasının 24 parçası iç duvarlarda; hakem saymaz, kart `pafta_disi`). TK-01'de niş yok: 0, liste 0. Tavanın türüne bakılmaz.
- Tavan H'ı ve gözler (H-11, AL-01, AL-02; kural `dizme_tavan`): asma dizme tavanda her odanın tavanı duvarlarla ve omegaların sırtıyla
  sütunlara bölünür; H'lar her sütunda koşunun büyük ucundan 62,5 aralıkla; göz iki H arası; ıslak hacimde yeşil. Gözler levhaya raflarla
  (`kesim.levha_karti`). Ters tavanda H ve göz yok.
- Çatı izolasyonu (IZ-01; kural `cati_izolasyonu`): makas aralığı başına bir şerit, dış duvarların iç yüzleri arasında; paket
  ⌈Σ alan ÷ 9,6⌉ (`kesim.paket_karti`). Beşik dışında "kural yok" (`test_k5.py`).
- Liste ile fark (bilgi; liste 6e'nin, değişmez): liste H'ı net alandan (÷ 1,255 × 0,625 + 5), alçıpanı alandan (× 1,05 + yedek, yeşilde
  veranda tavanı da), şilteyi brüt alandan sayar; model parçadan, yedeksiz. Sayılar burada yan yana kilitli.
"""
from __future__ import annotations

import copy
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element as ue
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import ifc_uret  # noqa: E402
from motor import kart_model as KM  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402
from motor import yerlesim as Y  # noqa: E402
from motor.yerlesim import kesim  # noqa: E402

MOTOR_VERI = KOK / "testler" / "motor" / "veri"
DUVAR100 = "100'lük duvar omegası"
EVLER = ("TK01_r07", "PK01")


def _oku(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _parcalar(say: dict, kart: str) -> list[dict]:
    return [p for p in say["yerlesim"]["parcalar"] if p.get("kart") == kart]


def _liste(ie: dict) -> dict[str, dict]:
    return {s["kalem"]: s for s in PL.is_emrinden(copy.deepcopy(ie))["satirlar"]}


def _satir(L: dict[str, dict], ad: str) -> dict:
    (s,) = [x for k, x in L.items() if k == ad or k.startswith((ad + " (", ad + " ·"))]
    return s


def _degerler() -> dict:
    return Y.degerler(_oku(KM.YERLESIM), _oku(KM.LISTE_KURALLARI))


@pytest.fixture(scope="module")
def evler(tmp_path_factory):
    out = {}
    for kod in EVLER:
        d = tmp_path_factory.mktemp(f"k5b2_{kod}")
        assert KM.main([str(MOTOR_VERI / f"{kod}.json"), str(d), "--kod", kod]) == 0           # kural yok yok: komut 0
        ie = _oku(MOTOR_VERI / f"{kod}.json")
        k = Y.katmanlar(ie, ifc_uret.hazirla(ie), KM.makaslar(ifcopenshell.open(str(d / f"{kod}.ifc")), KM._Kutular()), _oku(KM.YERLESIM),
                        _oku(KM.LISTE_KURALLARI))                                   # parçaların geometrisi (sayımda yazılmaz)
        out[kod] = {"ie": ie, "say": _oku(d / f"{kod}_kart_sayim.json"), "klasor": d, "liste": _liste(ie), "katman": k}
    return out


def _katmanlar(ie: dict, klasor: Path, ad: str) -> dict:
    bugunku = klasor / f"{ad}.ifc"
    assert ifc_uret.uret(ie, bugunku)["sema_hatasi"] == 0
    return Y.katmanlar(ie, ifc_uret.hazirla(ie), KM.makaslar(ifcopenshell.open(str(bugunku)), KM._Kutular()), _oku(KM.YERLESIM),
                       _oku(KM.LISTE_KURALLARI))


# ----------------------------------------------------------------------------- niş duvarının omegası (OM-02, D-32)
@pytest.mark.parametrize("kod, mahal, model_m, liste_m, adet", [("TK01_r07", "GİRİŞ", 3.665, 3.67, 2), ("PK01", "VERANDA", 5.24, 5.34, 3)])
def test_dis_duvar_omegasi_listeyle(evler, kod, mahal, model_m, liste_m, adet):
    say, L = evler[kod]["say"], evler[kod]["liste"]
    sirt = _degerler()["tavan_omegasi_yerlesimi"]["sirt_100"]
    dis = [p for p in _parcalar(say, "OM-02") if p["bilgi"].get("Duvar") == "dis"]
    assert dis and all(p["parca"].startswith(Y.DIS_DUVAR + "OMEGA_") and p["bilgi"]["Yer"] == "duvar_ekseni" and p["bilgi"]["Sirt_cm"] == sirt
                       and p["bilgi"]["Mahal"] == mahal and p["boy_cm"] <= 250 for p in dis)
    s = _satir(L, DUVAR100)
    terim = {a.strip(): float(m.replace(",", ".")) for a, m in re.findall(r"([^+÷]+?) ([\d,]+) m", s["formul"])}
    assert (round(sum(p["boy_cm"] for p in dis) / 100, 3), terim["çatı kenarına gelmeyen dış duvarlar"]) == (model_m, liste_m)
    assert say["kesim_plani"]["OM-02"]["stok"] == s["adet"] == adet


@pytest.mark.parametrize("kod", EVLER)
def test_dis_duvar_omegasi_pafta_disi(evler, kod):
    """Dış parçalar pafta anahtarı almaz; iç duvar omegalarının ve öteki parçaların anahtarları K5b-1'deki gibi (sayılar hakemin kapısında)."""
    say = evler[kod]["say"]
    kart = next(k for k in _oku(KM.KARTLAR)["kartlar"] if k["kod"] == "OM-02")
    assert kart["pafta_disi"]["bilgi"] == {"Duvar": "dis"} and kart["pafta_disi"]["neden"]
    f = ifcopenshell.open(str(evler[kod]["klasor"] / f"{kod}_model.ifc"))
    dis = [e for e in f.by_type("IfcElement") if (e.Name or "").startswith(Y.DIS_DUVAR)]
    assert len(dis) == len([p for p in _parcalar(say, "OM-02") if p["bilgi"].get("Duvar") == "dis"]) > 0
    for e in dis:
        p = ue.get_psets(e)[KM.PARCA_SETI]
        assert p["KartKodu"] == "OM-02" and p["PaftaAnahtari"] == "", e.Name


@pytest.mark.parametrize("kod, mahal", [("TK01_r07", "GİRİŞ"), ("PK01", "VERANDA")])
def test_acik_mahal_duvarinda_iki_omega(evler, kod, mahal):
    """Beyan (geometri hakemi, K5b-2; Bilinen sınırlama): açık mahale bakan ve omegalara paralel dış duvarda iki omega var. Açık mahalin
    ilk tavan omegası (OM-01) duvarın yüzünde (karar B; PK-01 paftasında "duvar yüzünde 1"), D-32'nin 100'lük duvar omegası (OM-02) duvarın
    ekseninde; sırtları üst üste biner. Hangisinin kalacağı mühendise soruldu; değişirse bu test bilerek değişir."""
    P = evler[kod]["katman"]["parcalar"]
    def hat(p):                                                       # omegalara paralel (y boyunca) parçanın ekseni, değilse None
        x0, y0, _, x1, y1, _ = p["geo"]["kutu"]
        return round((x0 + x1) / 2, 4) if x1 - x0 < y1 - y0 else None
    dis = {hat(p) for p in P if p["bilgi"].get("Duvar") == "dis"} - {None}
    yuz = {hat(p) for p in P if p["parca"] == "omega" and p["bilgi"].get("Yer") == "duvar_yuzu" and p["bilgi"].get("Mahal") == mahal}
    ust_uste = [(s, y) for s in dis for y in yuz if abs(abs(s - y) - 5) < 1e-6]          # duvar 10 cm: yüz eksenden 5 cm
    assert len(ust_uste) == len(yuz) == 1, (dis, yuz)


def test_nis_yoksa_dis_omega_yok(tmp_path):
    """TK-01'de giriş nişi yok, veranda taşan (BK-14; ona bakan duvar ana çatının kenarında): dış omega yok, liste de 0."""
    ie = _oku(MOTOR_VERI / "TK01.json")
    k = _katmanlar(ie, tmp_path, "TK01")
    assert not [p for p in k["parcalar"] if p["bilgi"].get("Duvar") == "dis"]
    assert _satir(_liste(ie), DUVAR100)["adet"] == 0


# ----------------------------------------------------------------------------- tavan H'ı ve gözler (H-11, AL-01, AL-02)
@pytest.mark.parametrize("kod", EVLER)
def test_tavan_h_ve_gozler(evler, kod):
    """H'lar her sütunda koşunun büyük ucundan aralıkla; göz aralıktan ve son gözün en kısasından uzun değil; ıslak hacimde yeşil; levha
    sayısı alandan az değil."""
    ie, say = evler[kod]["ie"], evler[kod]["say"]
    Z = _degerler()["dizme_tavan"]
    aralik = Z["aralik"] * 100
    tur = {m["ad"]: m.get("tur") for m in ie["mahaller"]}
    kosu = 1 if ifc_uret.hazirla(ie)["bina"]["cati"].get("makas_ekseni", "x") == "x" else 0     # H'ın koşudaki yeri kutunun merkezinden
    sutun = defaultdict(set)
    H = [p for p in evler[kod]["katman"]["parcalar"] if p["parca"] == "tavan_h"]
    assert len(H) == len(_parcalar(say, "H-11"))
    for p in H:
        k = p["geo"]["kutu"]
        sutun[(p["bilgi"]["Mahal"], p["bilgi"]["Sutun"])].add(round((k[kosu] + k[kosu + 3]) / 2, 4))
        assert p["boy_cm"] >= _degerler()["tavan_omegasi_yerlesimi"]["en_kisa_cm"]
    assert sutun and all(all(abs(a - b - aralik) < 1e-6 for a, b in zip(ts[::-1], ts[::-1][1:])) for ts in map(sorted, sutun.values()))
    gozler = _parcalar(say, "AL-01") + _parcalar(say, "AL-02")
    assert gozler and all(p["bilgi"]["Uzunluk_cm"] <= aralik + Z["son_en_kisa_cm"] + 1e-6 for p in gozler)
    assert all(p["alan_m2"] <= p["bilgi"]["En_cm"] * p["bilgi"]["Uzunluk_cm"] / 1e4 + 5e-5 for p in gozler)          # alan 4 haneye yuvarlı
    assert all((p["kart"] == "AL-02") == (tur.get(p["bilgi"]["Mahal"]) in Z["islak"]) for p in gozler)
    for kk in ("AL-01", "AL-02"):
        x = say["kesim_plani"][kk]
        assert x["levha_cm"] == Z["levha_cm"] and x["parca"] == len(_parcalar(say, kk))
        assert x["stok"] >= math.ceil(x["alan_m2"] / Z["levha_m2"] - 1e-9)


@pytest.mark.parametrize("kod, model, liste", [
    ("TK01_r07", {"H-11": 91, "AL-01": (96, 22), "AL-02": (16, 3), "IZ-01": (7, 8)}, {"H-11": 98, "AL-01": 24, "AL-02": 7, "IZ-01": 10}),
    ("PK01", {"H-11": 72, "AL-01": (76, 16), "AL-02": (8, 2), "IZ-01": (8, 6)}, {"H-11": 68, "AL-01": 17, "AL-02": 4, "IZ-01": 7}),
])
def test_liste_ile_yan_yana(evler, kod, model, liste):
    """Bilgi: liste alandan, model parçadan (bkz. modülün açıklaması); iki sayı da kilitli. Levha ve paket listeden az ya da eşit (liste yedek
    ve fire ekler, yeşilde veranda tavanını da sayar)."""
    say, L = evler[kod]["say"], evler[kod]["liste"]
    kartlar = {k["kod"]: k for k in _oku(KM.KARTLAR)["kartlar"]}
    adet = {k["kod"]: k["adet"] for k in say["kartlar"]}
    assert adet["H-11"] == model["H-11"]
    assert {k: (adet[k], say["kesim_plani"][k]["stok"]) for k in ("AL-01", "AL-02", "IZ-01")} == {k: model[k] for k in ("AL-01", "AL-02", "IZ-01")}
    assert {k: _satir(L, kartlar[k]["liste"]["satirlar"][0])["adet"] for k in liste} == liste
    assert all(model[k][1] <= liste[k] for k in ("AL-01", "AL-02", "IZ-01"))


def test_ters_tavanda_h_ve_goz_yok(tmp_path):
    """Ters tavanda H ve göz kurulmaz; niş duvarının omegası ve çatı izolasyonu tavanın türüne bakmaz."""
    ie = _oku(MOTOR_VERI / "TK01_r07.json")
    ie["ozellikler"]["Tavan"] = "Ters"
    k = _katmanlar(ie, tmp_path, "ters")
    assert k["girdi"]["tavan"] == "ters"
    parca = {p["parca"] for p in k["parcalar"]}
    assert not parca & {"tavan_h", "goz"}
    assert [p for p in k["parcalar"] if p["bilgi"].get("Duvar") == "dis"] and "serit" in parca


# ----------------------------------------------------------------------------- çatı izolasyonu (IZ-01)
@pytest.mark.parametrize("kod", EVLER)
def test_cati_izolasyonu_makas_araliginda(evler, kod):
    say, d = evler[kod]["say"], evler[kod]["klasor"]
    mk = sorted(m["konum"] for m in KM.makaslar(ifcopenshell.open(str(d / f"{kod}.ifc")), KM._Kutular()))
    plan = ifc_uret.hazirla(evler[kod]["ie"])
    W, H = max(p["rect"][2] for p in plan["panolar"]), max(p["rect"][3] for p in plan["panolar"])
    boy, derin = (W, H) if plan["bina"]["cati"].get("makas_ekseni", "x") == "x" else (H, W)
    serit = sorted(_parcalar(say, "IZ-01"), key=lambda p: p["bilgi"]["Aralik"])
    assert len(serit) == len(mk) - 1 and [p["bilgi"]["Aralik"] for p in serit] == list(range(1, len(mk)))
    assert {p["bilgi"]["Uzunluk_cm"] for p in serit} == {boy - 2 * 10}                  # dış duvarların iç yüzleri arası (dış pano 10 cm)
    assert sum(p["bilgi"]["En_cm"] for p in serit) == pytest.approx(min(mk[-1], derin - 10) - max(mk[0], 10))
    x = say["kesim_plani"]["IZ-01"]
    assert x["paket_m2"] == _degerler()["cati_izolasyonu"]["paket_m2"] == 9.6
    assert x["stok"] == math.ceil(sum(p["alan_m2"] for p in serit) / 9.6 - 1e-9) and x["parca"] == len(serit)


# ----------------------------------------------------------------------------- kesim birimleri
def test_levha_karti():
    k = kesim.levha_karti([(60, 100)] * 4, 120, 250)
    assert (k["raf"], k["stok"], k["dizilim"], "genis" in k) == (2, 1, [[100, 100]], False)
    k = kesim.levha_karti([(122.25, 62.5)], 120, 250)                  # dış duvar sütunu: levha + 2,25'lik şerit
    assert (k["raf"], k["stok"], k["genis"]) == (2, 1, {"goz": 1, "en_genis_cm": 122.25})
    k = kesim.levha_karti([(300, 50)], 120, 250)                       # levhanın iki katından geniş: iki levha eni + şerit
    assert (k["raf"], k["stok"], k["alan_m2"]) == (3, 1, 1.5)
    k = kesim.levha_karti([(60, 62.5)] * 17, 120, 250)                 # 2 göz bir rafta, 4 raf bir levhada: 9 raf → 3 levha
    assert (k["raf"], k["stok"]) == (9, 3)
    k = kesim.levha_karti([(62.5, 62.5)] * 17, 120, 250)               # 62,5'lik iki göz bir rafa sığmaz: 17 raf → 5 levha
    assert (k["raf"], k["stok"]) == (17, 5)
    with pytest.raises(ValueError):
        kesim.levha_karti([(60, 251)], 120, 250)


def test_paket_karti():
    assert kesim.paket_karti([4.8, 4.8], 9.6)["stok"] == 1
    assert kesim.paket_karti([4.8, 4.81], 9.6)["stok"] == 2
    assert kesim.paket_karti([], 9.6)["stok"] == 0


def test_kural_dosyasi():
    """Levhanın ölçüsü kitabın levha alanıyla aynı; değerlerin durumu yazılı."""
    yer = _oku(KM.YERLESIM)
    Z, I = yer["kurallar"]["dizme_tavan"], yer["kurallar"]["cati_izolasyonu"]
    D = _degerler()
    assert D["dizme_tavan"]["levha_cm"][0] * D["dizme_tavan"]["levha_cm"][1] / 1e4 == D["dizme_tavan"]["levha_m2"] == 3.0
    assert Z["durum"] == I["durum"] == "varsayim" and I["cati_tipleri"] == ["besik"]
    dis = yer["kurallar"]["tavan_omegasi_yerlesimi"]["dis_duvar"]
    assert dis["durum"] == "lokman" and dis["tarih"] == "2026-10-21"
    kartlar = {k["kod"]: k for k in _oku(KM.KARTLAR)["kartlar"]}
    assert [kartlar[k]["yerlesim"]["kural"] for k in ("H-11", "AL-01", "AL-02", "IZ-01")] == ["dizme_tavan"] * 3 + ["cati_izolasyonu"]
    assert (kartlar["AL-01"]["yerlesim"]["bilgi"], kartlar["AL-02"]["yerlesim"]["bilgi"]) == ({"Renk": "beyaz"}, {"Renk": "yesil"})


# ----------------------------------------------------------------------------- çizim ve katalog
def test_cizim_ve_katalog(evler):
    import openpyxl
    import pymupdf
    d = evler["TK01_r07"]["klasor"]
    metin = [" ".join(p.get_text().split()) for p in pymupdf.open(d / "TK01_r07_yerlesim_planlari.pdf")]
    assert len(metin) == 7 and not any("EKSİK" in s for s in metin)
    assert "OM-02 100'lük duvar omegası L 2500 3 parça, 3,67 m" in metin[0] and "açık mahale bakan dış duvarda: 3" in metin[0]
    assert ("H-11 Tavan H'ı L 1185: 91 parça (▬) AL-01 beyaz alçıpan: 96 göz → 22 levha AL-02 yeşil alçıpan: 16 göz → 3 levha "
            "(levha 120 × 250, raflarla; yedek yok) AL-01: 28 göz levhadan geniş (en 122,25 cm; levha + şerit)") in metin[0]
    assert "IZ-01 Çatı izolasyonu: 7 şerit (İ), 76,30 m² → 8 paket (9,6 m²)" in metin[1]
    ws = openpyxl.load_workbook(d / "TK01_r07_kart_katalogu.xlsx")["Kesim planı"]
    satir = {r[0]: r for r in ws.iter_rows(values_only=True)}
    assert satir["AL-01"][2] == "levha 120 × 250" and satir["AL-01"][5] == 22
    assert satir["IZ-01"][2] == "paket 9,6 m²" and satir["IZ-01"][5] == 8 and satir["IZ-01"][6] == "7 şerit"
