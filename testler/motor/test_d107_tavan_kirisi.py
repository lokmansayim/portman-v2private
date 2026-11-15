"""D-107 · BK-39 · PC-43 · Tavan kirişi: makas yönünde 7 m'yi aşan açıklığa köşeye bir kutu profil (`motor/tavan_kirisi.py`).

Lokman, 15 Kasım 2026 (UTC): 09:47:33 "eşik 7 metre olsun"; 10:20:13 "gerek yok çünkü buraya makas gelmiyor makaslar 125,5 cm arayla
koyuluyor"; 10:22:20 kirişlerin yerine "doğru bulmuşsun"; kart 10:22:40 "Evet, bu kuralla" (kiriş makasa dik, iki ucu duvarda, en kısa;
eşitse iki ucu köşede); kart 10:48:34 "Eskizdeki gibi" (listede 1 satır, yüzden yüze + 2 × 10, uçta kolon yok; kiriş yalnız saha montaj
planında, ön onay A4 sayfası aynen). Hedef örnek `veri/D107_tavan_kirisi_beklenen.json`: paftalardaki üç kiriş (70, 65, 81 m²).
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, geometry as G, prefabrik_liste as PL, tavan_kirisi as TK  # noqa: E402
from motor.katalog import Katalog  # noqa: E402

BEKLENEN = json.loads((KOK / "testler" / "motor" / "veri" / "D107_tavan_kirisi_beklenen.json").read_text(encoding="utf-8"))
KALEM = "Kutu profil (kiriş) 100 × 100"
# Tek kapalı oda, makas yönünde 753 cm, içinde duvar yok: kirişin oturacağı köşe yok (K21: kiriş konmaz, sorulur)
TEK_ODA = {"is_emri_no": "D107-SENTETIK", "revizyon": 1,
           "talep": {"bayi": {"kod": "TEST", "ad": "Test"}, "musteri_adi": "TEST", "metin": "tek oda"},
           "yapi": {"sistem": "prefabrik", "kat_sayisi": 1, "duvar_yuksekligi_cm": 250, "olcu_kaynagi": "serbest",
                    "grid": {"x_pano": 6, "y_pano": 7}, "kisa_kenar": "x", "giris_cephesi": "on"},
           "mahaller": [{"ad": "SALON", "tur": "salon", "konum_pano": [[0, 0, 6, 7]]}],
           "acikliklar": [{"tur": "pencere", "olcu": "120x120", "mahal": "SALON", "duvar": "on"}],
           "cati": {"tip": "besik", "egim_yuzde": 33, "sacak_cm": 30, "topuk_cm": 10}}


def _oku(yol: str | Path) -> dict:
    return json.loads((KOK / yol).read_text(encoding="utf-8"))


def _bul(ie: dict) -> dict:
    """Plan kurulur kurulmaz okunur (pano ve duvar uçları son kurulan ızgaradan)."""
    with contextlib.redirect_stdout(io.StringIO()):
        plan = G.kur(copy.deepcopy(ie))
    return TK.bul(plan, ie)


def _prefabrik_girdiler() -> list[Path]:
    yollar = sorted((KOK / "is_emri" / "adaylar").glob("PA*.json")) + sorted((KOK / "is_emri").glob("*.json"))
    yollar += sorted((KOK / "testler" / "motor" / "veri").glob("TK0*.json")) + [KOK / "testler" / "motor" / "veri" / "PK01.json"]
    out = []
    for y in yollar:
        ie = json.loads(y.read_text(encoding="utf-8"))
        if isinstance(ie, dict) and isinstance(ie.get("yapi"), dict) and ie["yapi"].get("sistem", "prefabrik") == "prefabrik" and "mahaller" in ie:
            out.append(y)
    return out


def test_kural_degerleri():
    """Eşik, oturma ve kesit kural dosyasında Lokman'ın değerleriyle; makas aralığı liste kuralından okunur (iki yerde yazılmaz)."""
    y = _oku("kurallar/yerlesim/prefabrik.json")["kurallar"]["tavan_kirisi"]
    k = TK.kural()
    assert (k["esik"], k["oturma"], k["kesit"], k["kalem"]) == (700.0, 10.0, 10.0, KALEM)
    assert k["makas"] == _oku("kurallar/liste/prefabrik.json")["kurallar"]["makas_aralik_cm"]["deger"] == 125.5
    assert y["durum"] == "lokman" and all(y[a]["durum"] == "lokman" and y[a]["not"] for a in ("esik_cm", "duvara_oturma_cm", "kesit_cm", "uc_kolonu"))
    assert y["uc_kolonu"]["deger"] is False
    for soz in ("eşik 7 metre olsun", "makaslar 125,5 cm arayla koyuluyor", "Evet, bu kuralla", "Eskizdeki gibi"):
        assert soz in y["kaynak"], soz


@pytest.mark.parametrize("kod", sorted(BEKLENEN["kirisli"]))
def test_paftadaki_kirisler(kod):
    """Hedef örnek: Motor'un kirişi paftadaki yerde (0,5 cm içinde) ve hedef örnekteki ölçülerle; tek kiriş, uyarı yok."""
    b = BEKLENEN["kirisli"][kod]
    s = _bul(_oku(b["is_emri"]))
    assert s["uyarilar"] == [] and s["disinda"] == []
    assert s["kirisler"] == [b["kiris"]]
    k, p = s["kirisler"][0], b["pafta_okumasi"]
    assert k["yon"] == p["yon"] and abs(k["eksen_cm"] - p["eksen_cm"]) <= 0.5
    assert all(abs(u - v) <= 0.5 for u, v in zip(k["uclar_cm"], p["uclar_cm"]))
    assert k["liste_boyu_cm"] == k["yuzden_yuze_cm"] + 20


def test_muhurlu_70m2_ayni_kiris():
    """M-07'nin 70 m²'si (AP-09; İş Emri mühürlü) PA-03 ile aynı ev: aynı kiriş. İş Emri, çizimin ön onay sayfası ve çatı değişmez."""
    assert _bul(_oku("testler/cizim/evler/AP09.json"))["kirisler"] == [BEKLENEN["kirisli"]["PA03"]["kiris"]]


@pytest.mark.parametrize("kod", sorted(BEKLENEN["kirissiz"]))
def test_kirissiz_evler(kod):
    """102 m²'nin antresi ve 6×8 referans evinin salonu: bant 117,5 < 125,5, makas gelmez (Lokman 10:20:13). 93 m²: çıkıntılı cumba
    kapsam dışı, ana çatıda açıklık 7 m'nin altında (Lokman 10:19:45, 10:22:20)."""
    b = BEKLENEN["kirissiz"][kod]
    s = _bul(_oku(b["is_emri"]))
    assert s["kirisler"] == [] and s["uyarilar"] == [] and s["disinda"] == b["disinda"]


def test_tarama_yalniz_uc_ev():
    """Havuzun bütün prefabrik evleri ve referans girdiler (6×8, Yan Verandalı, P6001, TK-01…TK-06, PK-01): kiriş yalnız hedef örnekteki
    üç evde, uyarı hiçbir evde yok."""
    kirisli, uyarili = set(), set()
    for y in _prefabrik_girdiler():
        s = _bul(json.loads(y.read_text(encoding="utf-8")))
        if s["kirisler"]:
            kirisli.add(y.stem)
        if s["uyarilar"]:
            uyarili.add(y.stem)
    assert kirisli == set(BEKLENEN["kirisli"]) and uyarili == set()


def test_liste_satiri():
    """70 m²: listeye yalnız bir satır eklenir (1002, Kutu profil (kiriş) 100 × 100, L 3257,5, 1 adet); öteki satırlar aynen."""
    ie = _oku(BEKLENEN["kirisli"]["PA03"]["is_emri"])
    L = PL.is_emrinden(ie)
    N = PL.model_motor(ie)
    assert N["tavan_kirisleri"] == [BEKLENEN["kirisli"]["PA03"]["kiris"]]
    N.pop("tavan_kirisleri")
    once = PL.liste(N, PL.kurallari_oku())
    yeni = [s for s in L["satirlar"] if s not in once["satirlar"]]
    alan = lambda s: {a: s[a] for a in ("grup", "kalem", "olcu", "adet")}   # noqa: E731
    assert [alan(s) for s in yeni] == [BEKLENEN["kirisli"]["PA03"]["liste_satiri"]]
    assert yeni[0]["dayanak"] == "Liste kuralı" and "yüzden yüze 305,75 + 2 × 10" in yeni[0]["formul"] and "D-107" in yeni[0]["kaynak"]
    assert [s for s in L["satirlar"] if s is not yeni[0]] == once["satirlar"]
    for kod, b in BEKLENEN["kirisli"].items():                   # 65 ve 81 m² aynı kuralla
        satir = [s for s in PL.is_emrinden(_oku(b["is_emri"]))["satirlar"] if s["formul"].startswith("tavan kirişi")]
        assert [alan(s) for s in satir] == [b["liste_satiri"]], kod


def test_kirissiz_evin_modeli_aynen():
    """Kirişsiz evin liste modelinde anahtar yok (liste bayt bayt eskisi)."""
    N = PL.model_motor(_oku("is_emri/ALTIN_2plus1_6x8.json"))
    assert "tavan_kirisleri" not in N and "tavan_kirisi_uyarilari" not in N


def test_kose_yoksa_sorulur():
    """K21: kirişin oturacağı köşe yoksa kiriş yazılmaz; listede adetsiz "Kural yok" satırı ve çizimde uyarı (yer Lokman'a sorulur)."""
    s = _bul(TEK_ODA)
    assert s["kirisler"] == [] and len(s["uyarilar"]) == 1 and "köşe bulunamadı" in s["uyarilar"][0]
    satir = [x for x in PL.is_emrinden(copy.deepcopy(TEK_ODA))["satirlar"] if x["kalem"] == KALEM]
    assert [(x["olcu"], x["adet"], x["dayanak"]) for x in satir] == [("L ?", None, "Kural yok")]
    assert satir[0]["formul"].startswith("UYARI: Tavan kirişi: SALON açıklığı 753 cm")


def _cizim(ie: dict):
    with contextlib.redirect_stdout(io.StringIO()):
        plan = G.kur(copy.deepcopy(ie))
    c = dxf_out.Cizici(plan, Katalog())
    py = c.paylar()
    gap = plan.W + 300.0 + py["sol"] + py["sag"]
    c.ciz_plan(0.0, 0.0, "ANA", "KAT PLANI — AKSLI", "")
    c.ciz_plan(gap, 0.0, "KOPYA", "KAT PLANI — NET ALANLAR", "")
    c.ciz_plan(2 * gap, 0.0, "MONTAJ", "SAHA MONTAJ PLANI", "")
    return plan, c, gap


def test_saha_montaj_planinda_kiris():
    """70 m²: kiriş yalnız saha montaj planında (taralı 10 cm dikdörtgen, çerçeve ve yazı; katman TAVAN_KIRISI); akslı plan, net alan
    planı ve A4 sayfasının bölgeleri kirişsiz. Yazı plandaki öteki yazılara ve özel pano ölçülerine binmez."""
    b = BEKLENEN["kirisli"]["PA03"]["kiris"]
    plan, c, gap = _cizim(_oku(BEKLENEN["kirisli"]["PA03"]["is_emri"]))
    ox = 2 * gap
    tk = [e for e in c.msp if e.dxf.layer == "TAVAN_KIRISI"]
    assert sorted(e.dxftype() for e in tk) == ["HATCH", "LWPOLYLINE", "TEXT"]
    cer = next(e for e in tk if e.dxftype() == "LWPOLYLINE")
    xs = [p[0] - ox for p in cer.get_points("xy")]; ys = [p[1] for p in cer.get_points("xy")]
    assert (round(min(xs), 2), round(max(xs), 2), round(min(ys), 2), round(max(ys), 2)) == (b["eksen_cm"] - 5, b["eksen_cm"] + 5, *b["uclar_cm"])
    yazi = next(e for e in tk if e.dxftype() == "TEXT")
    assert yazi.dxf.text == "TAVAN KİRİŞİ 10×10" and yazi.dxf.rotation == 90.0
    assert all(min(p[0] for p in e.get_points("xy")) >= ox - 1 for e in tk if e.dxftype() == "LWPOLYLINE")
    bolge = {h for hs in c.bolgeler.values() for h in hs}
    assert not bolge & {e.dxf.handle for e in tk}
    yk = c._yazi_kutusu(yazi.dxf.text, (yazi.dxf.align_point[0] - ox, yazi.dxf.align_point[1]), yazi.dxf.height, 90.0)
    for t in c.msp:
        if t.dxftype() == "TEXT" and t.dxf.layer.startswith("MONTAJ") and t.get_placement()[0] == dxf_out.TextEntityAlignment.MIDDLE_CENTER:
            ap = t.dxf.align_point
            assert not c._kesisir(yk, c._yazi_kutusu(t.dxf.text, (ap[0] - ox, ap[1]), t.dxf.height, t.dxf.rotation)), t.dxf.text


def test_81m2_yazisi_olcuye_binmez():
    """81 m²: kirişin solunda 59,75'lik özel pano ölçüsü var; yazı sağa geçer (eskizde sol ortası ölçüye biniyordu)."""
    b = BEKLENEN["kirisli"]["PA16"]["kiris"]
    plan, c, gap = _cizim(_oku(BEKLENEN["kirisli"]["PA16"]["is_emri"]))
    yazi = next(e for e in c.msp if e.dxf.layer == "TAVAN_KIRISI" and e.dxftype() == "TEXT")
    assert yazi.dxf.align_point[0] - 2 * gap > b["eksen_cm"]


def test_kirissiz_evde_katman_yok():
    """Kirişsiz evin DXF'inde TAVAN_KIRISI katmanı açılmaz (DXF ve referans çıktıları aynen)."""
    _plan, c, _gap = _cizim(_oku("is_emri/ALTIN_2plus1_6x8.json"))
    assert "TAVAN_KIRISI" not in c.doc.layers and not [e for e in c.msp if e.dxf.layer == "TAVAN_KIRISI"]


def test_kose_yoksa_cizimde_uyari():
    plan, c, _gap = _cizim(TEK_ODA)
    assert "TAVAN_KIRISI" not in c.doc.layers
    assert any(u.startswith("Tavan kirişi: SALON açıklığı 753 cm") for u in plan.uyarilar)
