"""D-127 · BK-58 · PC-47 · Verandada tavan kirişi: makas yönünde 7 m'yi aşan veranda açıklığına açık kenardaki kolondan gövdeye kiriş.

Lokman, 19 Kasım 2026 19:05:44 UTC (76 m² teklif sohbeti): "verandanın tam ortasınada yani profil koyduğun yerede dikey bir kiriş gelecek
makası ortadan taşıması için aslında daha önce kural olarak girdik". D-107'nin (`motor/tavan_kirisi.py`) verandası: açıklık açık kenarların
kirişlerinin arası; kiriş kolonun yüzünden makasa dik gövdenin duvarına. Hedef örnek `veri/D127_veranda_kirisi_beklenen.json` (76 m² teklif
evi, İş Emri adsız kopya). D-107'nin evleri ve tarama testi (`test_d107_tavan_kirisi.py`) aynen.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, geometry as G, prefabrik_liste as PL, tavan_kirisi as TK  # noqa: E402
from motor.katalog import Katalog  # noqa: E402

BEKLENEN = json.loads((KOK / "testler" / "motor" / "veri" / "D127_veranda_kirisi_beklenen.json").read_text(encoding="utf-8"))
IE = json.loads((KOK / BEKLENEN["is_emri"]).read_text(encoding="utf-8"))
KALEM = "Kutu profil (kiriş) 100 × 100"


def _kolonsuz() -> dict:
    ie = copy.deepcopy(IE)
    ie["dikmeler"] = []
    return ie


def _bul(ie: dict) -> dict:
    with contextlib.redirect_stdout(io.StringIO()):
        plan = G.kur(copy.deepcopy(ie))
    return TK.bul(plan, ie)


def test_kural_degerleri():
    """Veranda anahtarı kural dosyasında, Lokman'ın sözüyle; kolona oturma kartın seçeneğiyle (19 Kasım 2026 19:33:12 "Eskizdeki gibi,
    L 1982,5")."""
    y = json.loads((KOK / "kurallar" / "yerlesim" / "prefabrik.json").read_text(encoding="utf-8"))["kurallar"]["tavan_kirisi"]["acik_mahal"]
    assert y["deger"] is True and y["durum"] == "lokman"
    assert "verandanın tam ortasınada yani profil koyduğun yerede dikey bir kiriş gelecek makası ortadan taşıması için" in y["not"]
    assert y["kolona_oturma_cm"]["durum"] == "lokman" and "Eskizdeki gibi, L 1982,5" in y["kolona_oturma_cm"]["not"]
    k = TK.kural()
    assert k["acik_mahal"] is True and k["kolona_oturma"] == y["kolona_oturma_cm"]["deger"] == 10


def test_76m2_veranda_kirisi():
    """Hedef örnek: verandanın kirişi ortadaki kolondan (391,5, paftadaki yer) salonun duvarına; açıklık 780 cm (yan kirişlerin arası).
    Salonun D-107 kirişi aynen; uyarı yok."""
    s = _bul(IE)
    assert s == {"kirisler": BEKLENEN["kirisler"], "disinda": [], "uyarilar": []}
    k = s["kirisler"][0]
    assert abs(k["eksen_cm"] - BEKLENEN["pafta_okumasi"]["kolon_eksen_cm"]) <= 0.5
    assert k["liste_boyu_cm"] == k["yuzden_yuze_cm"] + 20


def test_kolonsuz_veranda_sorulur():
    """K21: verandanın açık kenarında köşe kolonundan başka kolon yoksa kiriş konmaz; listede adetsiz "Kural yok" satırı sorar. Çizim
    verandanın kirişini çizmez (salonunki kalır)."""
    ie = _kolonsuz()
    s = _bul(ie)
    assert [k["oda"] for k in s["kirisler"]] == ["SALON+MUTFAK"]
    assert s["disinda"] == BEKLENEN["kolonsuz"]["disinda"]
    assert len(s["uyarilar"]) == 1 and "kolon bulunamadı" in s["uyarilar"][0]
    satir = [x for x in PL.is_emrinden(copy.deepcopy(ie))["satirlar"] if x["kalem"] == KALEM and x["dayanak"] == "Kural yok"]
    assert [(x["olcu"], x["adet"]) for x in satir] == [("L ?", None)]


def test_liste_satiri():
    """Listeye bir satır eklenir (1002, L 1982,5); öteki satırlar aynen (salonun kirişi dahil)."""
    L = PL.is_emrinden(copy.deepcopy(IE))
    N = PL.model_motor(copy.deepcopy(IE))
    assert N["tavan_kirisleri"] == BEKLENEN["kirisler"]
    N["tavan_kirisleri"] = [k for k in N["tavan_kirisleri"] if k.get("uc") != "kolon"]
    once = PL.liste(N, PL.kurallari_oku())
    yeni = [s for s in L["satirlar"] if s not in once["satirlar"]]
    alan = lambda s: {a: s[a] for a in ("grup", "kalem", "olcu", "adet")}   # noqa: E731
    assert [alan(s) for s in yeni] == [BEKLENEN["liste_satiri"]]
    assert "yüzden yüze 178,25 + 2 × 10" in yeni[0]["formul"] and "açık kenardaki kolonda" in yeni[0]["formul"] and "D-127" in yeni[0]["kaynak"]
    assert [s for s in L["satirlar"] if s is not yeni[0]] == once["satirlar"]


def test_saha_montaj_planinda_kiris():
    """Kiriş yalnız saha montaj planında (TAVAN_KIRISI); yazı kirişten uzun olduğundan kirişin boyuna sığar (salonunki 15 aynen)."""
    with contextlib.redirect_stdout(io.StringIO()):
        plan = G.kur(copy.deepcopy(IE))
    c = dxf_out.Cizici(plan, Katalog())
    py = c.paylar()
    gap = plan.W + 300.0 + py["sol"] + py["sag"]
    c.ciz_plan(0.0, 0.0, "ANA", "KAT PLANI — AKSLI", "")
    c.ciz_plan(gap, 0.0, "KOPYA", "KAT PLANI — NET ALANLAR", "")
    c.ciz_plan(2 * gap, 0.0, "MONTAJ", "SAHA MONTAJ PLANI", "")
    ox = 2 * gap
    tk = [e for e in c.msp if e.dxf.layer == "TAVAN_KIRISI"]
    cer = sorted(([round(min(p[0] for p in e.get_points("xy")) - ox, 2), round(max(p[0] for p in e.get_points("xy")) - ox, 2),
                   round(min(p[1] for p in e.get_points("xy")), 2), round(max(p[1] for p in e.get_points("xy")), 2)]
                  for e in tk if e.dxftype() == "LWPOLYLINE"))
    assert cer == sorted([[k["eksen_cm"] - 5, k["eksen_cm"] + 5, *k["uclar_cm"]] for k in BEKLENEN["kirisler"]])
    yazilar = {round(e.dxf.align_point[0] - ox, 1): e for e in tk if e.dxftype() == "TEXT"}
    assert len(yazilar) == 2
    for k in BEKLENEN["kirisler"]:
        y = min(yazilar.values(), key=lambda e: abs(e.dxf.align_point[0] - ox - k["eksen_cm"]))
        boy = dxf_out.Cizici.yazi_eni(y.dxf.text, y.dxf.height)
        assert boy <= k["yuzden_yuze_cm"] - 9.9
        # salonun kirişi (243) yazıdan uzun: 15 aynen; verandanınki (178,25): 15 × (178,25 − 10) / yazının 15'lik eni (211,93) ≈ 11,91
        bek = 15.0 if k["oda"] == "SALON+MUTFAK" else 15.0 * (k["yuzden_yuze_cm"] - 10.0) / dxf_out.Cizici.yazi_eni(y.dxf.text, 15.0)
        assert abs(y.dxf.height - bek) < 1e-6, (k["oda"], y.dxf.height)
        assert k["oda"] == "SALON+MUTFAK" or 11.9 < y.dxf.height < 11.92
        yk = c._yazi_kutusu(y.dxf.text, (y.dxf.align_point[0] - ox, y.dxf.align_point[1]), y.dxf.height, y.dxf.rotation)
        for t in c.msp:                                       # yazı plandaki öteki yazılara binmez (D-107 testi gibi)
            if t.dxftype() == "TEXT" and t.dxf.layer.startswith("MONTAJ") and t.get_placement()[0] == dxf_out.TextEntityAlignment.MIDDLE_CENTER:
                ap = t.dxf.align_point
                assert not c._kesisir(yk, c._yazi_kutusu(t.dxf.text, (ap[0] - ox, ap[1]), t.dxf.height, t.dxf.rotation)), t.dxf.text
    bolge = {h for hs in c.bolgeler.values() for h in hs}
    assert not bolge & {e.dxf.handle for e in tk}


def test_anahtar_kapaliyken_eski_yol(monkeypatch):
    """Kural dosyasında `acik_mahal` kapalıysa veranda eskisi gibi kapsam dışı (D-107'nin davranışı)."""
    asil = TK.kural
    monkeypatch.setattr(TK, "kural", lambda: {**asil(), "acik_mahal": False})
    s = _bul(IE)
    assert [k["oda"] for k in s["kirisler"]] == ["SALON+MUTFAK"] and s["disinda"] == [] and s["uyarilar"] == []


def test_kendi_catisi_olan_veranda():
    """Geometri hakemi (19 Kasım): verandanın kendi tek eğimli çatısı varsa (`cati.mahal_catilari`, AP-09 gibi) ana çatının makası
    verandaya gelmez; kiriş konmaz, uyarı yok. Kendi çatısı başka tipteyse (köşe kırması) kiriş konmaz, sorulur."""
    ie = copy.deepcopy(IE)
    ie["cati"]["mahal_catilari"] = [{"mahal": "VERANDA", "tip": "tek_yon", "egim_yuzde": 10, "yuksek_yan": "arka", "sacak_cm": 0}]
    s = _bul(ie)
    assert [k["oda"] for k in s["kirisler"]] == ["SALON+MUTFAK"] and s["uyarilar"] == []
    assert [(d["oda"], d["neden"]) for d in s["disinda"]] == [("VERANDA", "kendi tek eğimli çatısı var: makas gelmez")]
    ie["cati"]["mahal_catilari"][0]["tip"] = "kirma"
    s = _bul(ie)
    assert [k["oda"] for k in s["kirisler"]] == ["SALON+MUTFAK"]
    assert len(s["uyarilar"]) == 1 and "kendi çatısı (kirma) var" in s["uyarilar"][0]


def test_verandanin_icindeki_dikme_bandi_bolmez():
    """Geometri hakemi (19 Kasım): verandanın içindeki bir dikme açıklığı kesmez (bant bölünüp "makas gelmez" diye sessizce düşmez).
    Kolon açık kenarda değilse kiriş konmaz, sorulur."""
    ie = _kolonsuz()
    ie["dikmeler"] = [[386.5, 100.0]]
    s = _bul(ie)
    assert [k["oda"] for k in s["kirisler"]] == ["SALON+MUTFAK"]
    assert [(d["oda"], d["aciklik_cm"], d["neden"]) for d in s["disinda"]] == [
        ("VERANDA", 780.0, "açık kenarda kirişin oturacağı kolon bulunamadı")]
    assert len(s["uyarilar"]) == 1


def test_mahalsiz_parca_bant_acmaz():
    """Geometri hakemi (19 Kasım): hiçbir mahalden geçmeyen parça açık bant açmaz. Havuz evinin çatı seçeneğinde (PA42C) köşe kolonu planın
    2 cm dışında; kolonun çevresindeki mahalsiz şerit açıklık sayılmaz: kiriş, uyarı ve kapsam dışı satırı yok."""
    ie = json.loads((KOK / "is_emri" / "adaylar" / "PA42C.json").read_text(encoding="utf-8"))
    assert _bul(ie) == {"kirisler": [], "disinda": [], "uyarilar": []}
