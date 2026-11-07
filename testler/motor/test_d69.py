"""D-69 (BK-26; Lokman, 7 Kasım 2026 14:33): 125,5 aks aralığını aşan pano ancak içinde pencere ya da kapı gibi bir boşlukla olur.

"bizde karkaslı bir pano yani örneğin 180/180 bir pencere 125.5 cm lik bir aks aralığına oturmayacağı için özel karkaslı pano yapıyoruz onuda
2 tam pano yapıyoruz ortasına pencereyi koyuyoruz 2 tam pano 251 ortasında lento 50 eni 180 boyu 180 bir boşluk bırakıyoruz yani teknik
olarak 155,75 ölçüsünü verdiğin pano olamaz bunu kesin bir kural olarak koy 125.5 aks aralığını aşma durumlarımız ortasında ya bir pencere
ya bir kapı gibi bir boşluk olması gerekiyor".

Motor planın son hâlinde bütün panoları denetler (`geometry.genis_pano_denetimi`, `_kur`'un son adımı): açıklıksız pano 125,5'i aşarsa
açık hata. Denetim yalnız denetler; depodaki prefabrik İş Emri'lerinin hepsi bugün kurala uyar, çizimleri ve listeleri değişmez.
"""
from __future__ import annotations

import copy
import glob
import json
from pathlib import Path

import pytest

from motor import geometry as G

KOK = Path(__file__).resolve().parents[2]

# Depodaki prefabrik İş Emri'leri: referans şablonları (P6001 dahil), adaylar, TK-01…TK-05, PK-01, kör AP projeleri ve model evler, paket
# girdileri, harness İş Emri'leri, teklif ve görsel testlerinin girdileri. `deneme/` tarihli denemedir, canlıda değil (tarama BK-26'da).
KALIPLAR = ["is_emri/*.json", "is_emri/adaylar/*.json", "testler/motor/veri/*.json", "testler/kor/projeler/*/is_emri.json",
            "testler/cizim/evler/*.json", "araclar/paket/girdi/*.json", "beyin/testler/is_emri_*.json", "testler/teklif/*.json",
            "testler/gorsel/veri/*.json"]


def _is_emirleri() -> list[tuple[str, dict]]:
    cik = []
    for k in KALIPLAR:
        for f in sorted(glob.glob(str(KOK / k))):
            o = json.loads(Path(f).read_text(encoding="utf-8"))
            if isinstance(o, dict) and isinstance(o.get("yapi"), dict) and "grid" in o["yapi"] and "mahaller" in o:
                cik.append((str(Path(f).relative_to(KOK)), o))
    return cik


def _altin() -> dict:
    return json.loads((KOK / "is_emri" / "ALTIN_2plus1_6x8.json").read_text(encoding="utf-8"))


def _iki_acikliksiz_komsu(plan):
    """Aynı duvarda yan yana iki açıklıksız tam pano (125,5 + 125,5); yoksa None."""
    for d in plan.duvarlar:
        for a, b in zip(d.panolar, d.panolar[1:]):
            if not a.aciklar and not b.aciklar and abs(a.boy - G.MOD) < 1e-6 and abs(b.boy - G.MOD) < 1e-6:
                return d, a, b
    return None


def _birlestir(plan, acilim=None):
    d, a, b = _iki_acikliksiz_komsu(plan)
    i = d.panolar.index(a)
    yeni = G.Pano(d, a.a0, b.a1, acilim)
    d.panolar[i:i + 2] = [yeni]
    return yeni


def test_acikliksiz_genis_pano_hata():
    """İki tam pano açıklıksız birleşirse (251) Motor açık hata verir; 155,75'lik açıklıksız pano da (Lokman'ın örneği) hata."""
    plan = G.kur(copy.deepcopy(_altin()))
    G.genis_pano_denetimi(plan)                                  # kurala uyan plan: hata yok
    yeni = _birlestir(plan)
    assert yeni.boy == 251.0
    with pytest.raises(G.IsEmriHatasi, match=r"125,5'i aşan açıklıksız pano \(1 adet: .*boy 251\b.*\(D-69\)"):
        G.genis_pano_denetimi(plan)
    plan = G.kur(copy.deepcopy(_altin()))
    d, a, b = _iki_acikliksiz_komsu(plan)
    i = d.panolar.index(a)
    d.panolar[i:i + 2] = [G.Pano(d, a.a0, a.a0 + 155.75), G.Pano(d, a.a0 + 155.75, b.a1)]
    with pytest.raises(G.IsEmriHatasi, match=r"boy 155\.75"):
        G.genis_pano_denetimi(plan)


def test_aciklikli_genis_pano_gecer():
    """İçinde pencere ya da kapı olan 251'lik pano kurala uyar (BK-13: 180/180 pencere iki tam panonun ortasında)."""
    plan = G.kur(copy.deepcopy(_altin()))
    _birlestir(plan, G.Acilim("pencere", "180x180", 180.0, 180.0))
    G.genis_pano_denetimi(plan)
    plan = G.kur(copy.deepcopy(_altin()))
    _birlestir(plan, G.Acilim("dis_kapi", "90", 90.0, None))
    G.genis_pano_denetimi(plan)


def test_kur_son_adimda_denetler(monkeypatch):
    """Denetim `kur`'un son adımıdır: dizilimin herhangi bir yolu (burada planın son adımına sokulan birleşme) açıklıksız geniş pano
    bırakırsa İş Emri çizilmez (K21; sessiz düzeltme yok)."""
    asil = G._kubbe_geometrisi

    def bozan(plan, kubbe_panolari):
        asil(plan, kubbe_panolari)
        _birlestir(plan)

    monkeypatch.setattr(G, "_kubbe_geometrisi", bozan)
    with pytest.raises(G.IsEmriHatasi, match=r"\(D-69\)"):
        G.kur(copy.deepcopy(_altin()))


def test_depodaki_is_emirleri_kurala_uyar():
    """BK-26 taraması: depodaki prefabrik İş Emri'lerinin hepsi kurulur; 125,5'i aşan her panoda açıklık var (251'lik pencereli pano,
    karkaslı kaplama panosu, kubbe tabanı). Bugünkü sayılar: 61 İş Emri, 125,5'i aşan 34 pano, hepsi açıklıklı."""
    ies = _is_emirleri()
    adlar = {a for a, _ in ies}
    for gerekli in ("is_emri/P6001_2plus1_6x6.json", "testler/motor/veri/TK01_r07.json", "testler/motor/veri/TK02.json",
                    "testler/motor/veri/TK03.json", "testler/motor/veri/TK04_r08.json", "testler/motor/veri/TK05_r06.json",
                    "testler/kor/projeler/AP26/is_emri.json", "testler/motor/veri/PK01.json"):
        assert gerekli in adlar, gerekli
    uzun = []
    for ad, ie in ies:
        plan = G.kur(copy.deepcopy(ie))                           # denetim kur'un içinde: aykırı pano burada hata verirdi
        for p in plan.panolar:
            assert p.boy <= G.MOD + 1e-6 or p.aciklar, (ad, p.duvar.id, p.a0, p.a1)
            if p.boy > G.MOD + 1e-6:
                uzun.append((ad, round(p.boy, 2)))
    assert len(ies) >= 61 and len(uzun) >= 34, (len(ies), len(uzun))


def _aynali_genis_veranda() -> dict:
    """`test_ie17_pr2._genis_veranda(True)`'nun girdisi (M-07'nin testi; burada kopyası): AP-03'ten, veranda 251 × 130,5 ve yanında ODA 3,
    ön ↔ arka aynalı. `tam_izgara` + `son_aks`, ızgara 6 × 6,5, dış ölçü tam ızgarada (son pano kesilmemiş)."""
    ie = json.loads((KOK / "testler" / "cizim" / "evler" / "AP03.json").read_text(encoding="utf-8"))
    for m in ie["mahaller"]:
        if m["ad"] == "VERANDA":
            m["konum_cm"] = [[507, 10, 758, 135.5]]
        if m["ad"] == "SALON+MUTFAK":
            m["konum_cm"] = [[5, 10, 507, 449.25]]
    ie["mahaller"].append({"ad": "ODA 3", "tur": "yatak_odasi", "konum_cm": [[507, 135.5, 758, 449.25]]})
    ie["acikliklar"] = [a for a in ie["acikliklar"] if a["tur"] == "dis_kapi"]
    H = 835.75
    for m in ie["mahaller"]:
        m["konum_cm"] = [[r[0], round(H - r[3], 4), r[2], round(H - r[1], 4)] for r in m["konum_cm"]]
    ie["dikmeler"] = [[d[0], round(H - 10 - d[1], 4)] for d in ie["dikmeler"]]
    for a in ie["acikliklar"]:
        if "duvar_ucu" in a:
            a["duvar_ucu"] = {"on": "arka", "arka": "on"}.get(a["duvar_ucu"], a["duvar_ucu"])
    for d in ie["yapi"]["dizilim"].get("dis_pano_dayanagi", []):
        if "y" in d:
            d["y"] = round(H - d["y"], 4)
            d["aralik_cm"] = sorted(round(H - v, 4) for v in d["aralik_cm"])
    return ie


def test_tam_izgara_son_aks_yarim_pano():
    """`tam_izgara` + `son_aks`'ta son pano kesilmemişse (yarım ızgarada tam 125,5) başı yine derzdir: sol duvarın önü 188,25'lik açıklıksız
    pano değil, 125,5 + 62,75 (İE-17: "kesilmiş son pano ızgaranın sondan bir önceki aksından başlar, gerekirse önünde yarım pano").
    Depodaki İş Emri'lerinin dizilimi aynı (BK-26 kıyası); değişen yalnız bu kurgu."""
    plan = G.kur(_aynali_genis_veranda())
    sol = next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == "y" and abs(d.c - 5.0) < 1e-6)
    assert [(p.a0, p.a1) for p in sol.panolar] == [(10.0, 135.5), (135.5, 198.25), (198.25, 323.75), (323.75, 449.25), (449.25, 574.75),
                                                   (574.75, 700.25), (700.25, 825.75)]
