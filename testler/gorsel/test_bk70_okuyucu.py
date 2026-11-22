"""BK-70 · çizim okuyucudaki üç hata (pano 83, 22 Kasım 2026 denemesi): gömme veranda, ölçüsü yazmayan oda sınırı, aynı duvarda iki
pencere; Motor'un kuramadığı şablon bayiye soru olur. LLM yok: girdi sunucunun 22 Kasım Opus 5.5 okumalarıdır (`veri/BK70_*`, bayi
çizimleri depoya girmez). Beklenen değerler Lokman'ın onayladığı planlardan: TK-06 r02, TK-08 r05 (proje dosyaları Teklif_Calisma),
TK-01 r08 (`testler/motor/veri/TK01_r08.json`).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import gorsel_okuma as GO  # noqa: E402
from motor import geometry as G  # noqa: E402

VERI = Path(__file__).resolve().parent / "veri"


def okuma(ad: str, sorusuz: bool = True) -> dict:
    o = json.loads((VERI / f"BK70_{ad}_okuma.json").read_text(encoding="utf-8"))
    return {**o, "emin_olunamayanlar": []} if sorusuz else o      # bayi okuyucunun kendi sorularına "doğru" der


def mahaller(ie: dict) -> dict[str, tuple[str, list]]:
    return {m["ad"]: (m["tur"], [[round(v, 2) for v in q] for q in m["konum_cm"]]) for m in ie["mahaller"]}


# ───────────── 1. gömme veranda ─────────────
# TK-06 r02 (onaylı): gövde 800 × 1088, veranda gövdenin sol ön köşesinde açık mahal, giriş kapısı veranda ile hol arasında
TK06_R02 = {"YATAK ODASI 1": ("yatak_odasi", [[10, 5, 323.75, 444.25]]), "YATAK ODASI 2": ("yatak_odasi", [[323.75, 5, 790, 318.75]]),
            "BANYO": ("banyo", [[449.25, 318.75, 790, 507]]), "HOL": ("antre_hol", [[323.75, 318.75, 449.25, 758]]),
            "MUTFAK": ("mutfak", [[10, 444.25, 323.75, 758]]), "SALON": ("salon", [[449.25, 507, 790, 1083]]),
            "VERANDA": ("veranda", [[10, 758, 449.25, 1083]])}


def test_gomme_veranda_govdenin_icinde_tk06():
    den = GO.denetle(okuma("TK06"))
    assert not den["sorular"] and not den["cizilemez"], den["sorular"]
    ie = den["cevrim"]["is_emri"]
    assert ie["yapi"]["dis_olcu_cm"] == {"x": 800, "y": 1088}
    assert mahaller(ie) == TK06_R02
    assert "verandalar" not in ie                                   # taşan veranda yok
    kapi = next(a for a in ie["acikliklar"] if a["tur"] == "dis_kapi")
    assert kapi["arasi"] == ["VERANDA", "HOL"] and kapi["duvar"] == "on"
    pen = {(a["mahal"], a["duvar"], a["olcu"]) for a in ie["acikliklar"] if a["tur"] == "pencere"}
    assert ("MUTFAK", "on", "160x180") in pen and ("SALON", "on", "120x160") in pen      # verandaya bakan pencereler (onaylıda da)
    assert any("gövdenin içinde" in n for n in den["notlar"])
    G.kur(copy.deepcopy(ie))


def test_gomme_veranda_tk09_bos_alan_sorusu_kalkti():
    """45 m²: okumada boş alan sorusu yok; kalan tek soru dış ölçünün ızgaraya oturmaması (onaylı plan 647,5)."""
    den = GO.denetle(okuma("TK09"))
    assert not any("hiçbir odaya ait" in s for s in den["sorular"])
    assert any(x["islev"] == "veranda" for x in den["kanonik"]["odalar"]) and not den["kanonik"]["verandalar"]
    assert den["sorular"] == ["Gövdenin yan cephesi 6,50 m; pano ızgarasında sonda 2,5 cm'lik pano kalıyor, bu ölçü prefabrikte olmuyor. "
                              "En yakın ölçüler 6,47 m ve 7,10 m; hangisiyle çizeyim?"]


def test_gomme_veranda_l_biciminde_govde_buyur_tk08():
    """76 m²: cephe boyunca veranda + gövdedeki girinti = L veranda; gövde veranda kadar büyür (onaylı r05: 800 × 951,25)."""
    for ad in ("TK08", "TK08_fable"):                              # Fable L verandayı iki parça okudu (0–264 derinlik 325,51)
        kan = GO.kanonik(okuma(ad))
        assert abs(kan["H"] - 950.06) < 0.01 and not kan["verandalar"], ad
        ver = next(x for x in kan["odalar"] if x["islev"] == "veranda")
        assert sorted(ver["rects"]) == [[0.0, 624.55, 264.0, 750.05], [0.0, 750.05, 800.05, 950.06]], ad
    den = GO.denetle(okuma("TK08"))
    assert not any("hiçbir odaya ait" in s for s in den["sorular"])
    k = next(k for k in den["kanonik"]["kapilar"] if k["dis"])
    assert k["arasinda"] == ["VERANDA", "SALON+MUTFAK"] and k["cephe"] == "sol"


def test_gomme_veranda_bos_alan_verandaya_uymazsa_sorulur():
    """Boş bölüm verandanın yansımasına uymuyor ve veranda cephenin tamamı değil: okuma aynen, boş alan sorulur (K21)."""
    o = okuma("TK06")
    o["verandalar"][0]["derinlik_cm"] = 150.0
    o["verandalar"][0]["bit_cm"] = 300.0
    den = GO.denetle(o)
    assert any("hiçbir odaya ait" in s for s in den["sorular"])
    assert den["kanonik"]["verandalar"] and not any(x["islev"] == "veranda" for x in den["kanonik"]["odalar"])


# ───────────── 2. ölçüsü yazmayan sınır ─────────────
def test_olcusuz_sinir_en_yakin_aksa_tk01():
    """80 m²: banyoların derinliği çizimde yazmıyor, LLM 245 aldı; en yakın aks 256 (onaylı r08). Soru değil, bayiye not."""
    den = GO.denetle(okuma("TK01"))
    assert not den["sorular"], den["sorular"]
    ie = den["cevrim"]["is_emri"]
    r08 = json.loads((KOK / "testler/motor/veri/TK01_r08.json").read_text(encoding="utf-8"))
    beklenen = {m["ad"]: m["konum_cm"] for m in r08["mahaller"]}
    okunan = {m["ad"]: m["konum_cm"] for m in ie["mahaller"]}
    assert okunan["BANYO 2"] == beklenen["BANYO"] and okunan["BANYO 1"] == beklenen["E. BANYO"]
    assert any("ölçüsü çizimde yazmayan" in n and "245 → 256" in n for n in den["notlar"])
    p0, p1 = G.kur(copy.deepcopy(r08)), G.kur(copy.deepcopy(ie))
    assert len(p1.panolar) == len(p0.panolar) == 60


def test_olculu_sinir_yine_sorulur():
    """Aynı 245 çizimde yazılı bir ölçüyse (zincirde) bugünkü gibi sorulur: bayinin yazdığı ölçü sessizce kaymaz."""
    o = okuma("TK01")
    o["zincirler"].append({"kenar": "sol", "olculer_cm": [245.0, 643.0], "toplam_cm": 888.0, "kapsam": "govde"})
    den = GO.denetle(o)
    assert any("245 cm) pano ızgarasına oturmuyor" in s for s in den["sorular"])


def test_olcusuz_sinir_iki_aksa_esit_uzaksa_sorulur():
    o = okuma("TK01")
    for x in o["odalar"]:                       # 224,6: 193,25 ile 256 akslarının tam ortası
        x["dikdortgenler"] = [[224.6 if v == 245.0 else v for v in r] for r in x["dikdortgenler"]]
        x["alan_m2"] = None                     # yazılı m² denetimi bu testin konusu değil
    den = GO.denetle(o)
    assert any("ölçüsü çizimde yazmıyor" in s and " mi olsun?" in s for s in den["sorular"]), den["sorular"]


# ───────────── 3. aynı duvarda iki pencere; Motor hatası soru olur ─────────────
def test_ayni_duvarda_iki_pencere_tk07():
    """61 m² tek oda: uzun duvarlarda ikişer pencere. Motor hepsini odanın ortasına alıp "Aynı panoya iki açıklık" veriyordu."""
    den = GO.denetle(okuma("TK07"))
    assert not den["sorular"] and den["cevrim"], den["sorular"]
    p = G.kur(copy.deepcopy(den["cevrim"]["is_emri"]))
    pen = [q for q in p.panolar if q.acilim and q.acilim.tur == "pencere"]
    assert len(pen) == 5 and len({q.rect() for q in pen}) == 5


def test_motor_iki_pencereyi_esit_boler():
    """Motor: oda ortası dizilimde aynı odanın aynı duvarındaki n pencere odanın net duvarının n + 1 eşit bölme noktasına yakın panoda."""
    ie = json.loads(json.dumps(GO.denetle(okuma("TK07"))["cevrim"]["is_emri"]))
    p = G.kur(copy.deepcopy(ie))
    sag = sorted((q.rect() for q in p.panolar if q.acilim and q.acilim.tur == "pencere" and q.rect()[0] > 600), key=lambda r: r[1])
    merkez = [(r[1] + r[3]) / 2 for r in sag]
    hedef = [10 + 930 / 3, 10 + 2 * 930 / 3]
    assert all(abs(m - h) <= 125.5 / 2 for m, h in zip(merkez, hedef)), merkez


def test_motor_iki_mahal_arasi_kapida_duvar():
    """Motor: iki mahal arasındaki kapıda `duvar` (BK-70) adayları o doğrultudaki duvara indirir; bilinmeyen değer hata (K21)."""
    ie = json.loads(json.dumps(GO.denetle(okuma("TK06"))["cevrim"]["is_emri"]))
    kapi = next(a for a in ie["acikliklar"] if a["tur"] == "dis_kapi")
    p = G.kur(copy.deepcopy(ie))
    q = next(q for q in p.panolar if q.acilim and q.acilim.tur == "dis_kapi")
    x0, y0, x1, y1 = q.rect()
    assert x1 - x0 > y1 - y0                                         # on: x boyunca uzanan duvar
    kapi["duvar"] = "yukari"
    try:
        G.kur(copy.deepcopy(ie))
        raise AssertionError("bilinmeyen duvar değeri hata vermeliydi")
    except G.IsEmriHatasi as e:
        assert "Kapıda duvar yalnız" in str(e)


def test_motor_kuramazsa_bayiye_soru():
    """Şablon Motor'da kurulamıyorsa (76 m²: salonun öndeki duvarında 180'lik pencereye yanında tam pano kalmıyor) cevrim yok, soru var."""
    den = GO.denetle(okuma("TK08"))
    assert den["cevrim"] is None
    assert den["sorular"] == ["Planı panolara yerleştirirken Salon+mutfak öndeki duvarında pencere ve kapıları sığdıramadım. Bu duvardaki "
                              "pencerelerin ve kapının yerini (köşeden cm) yazar mısınız?"]
