"""İE-27 PR-2 · Pencere veri tabanı, kısaltma yok (Lokman, 3 Kasım 2026 09:52, madde 11: "pencere modellerini sana vermiştim yani
pencereler konusunda da bir veri tabanın olmalı hangisi geldiyse onu uygula yani kısaltma"; D-45).

- `kurallar/pencere/pencereler.json`: Motor'un tek pencere kuralı (`kural`; `geometry.pencere_kurali` okur) ve bildiğimiz pencerelerin kaydı
  (`modeller`, kaynağıyla). Depodaki her İş Emri'nin pencere ölçüsü kayıtta; kayıtta olmayan ölçü yine kurulur, plan uyarısı yazılır.
- Kısaltma yok: boyu 200'ü geçen pencere döşemeden (eşik 0, üst kotu boyu kadar); en 247'yi geçen pencere üç (ve daha çok) panoluk.
  Kör ölçümün sürgülüleri paftadaki ölçüsüyle: AP-11 ve AP-14 180/200, AP-26 280/210 ve 200/210 (önce 180x180, 240x180, 200x180).
- Görünüş, IFC ve paftanın kot yazısı döşemeden pencereyi gerçek kotlarıyla verir; TK-01 ve TK-02'nin çizimi değişmez (hedef örnek
  `test_bk18_ic_100.py`, mühür M-02).
"""
from __future__ import annotations
import json
import re
import sys
import tempfile
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

VT = json.loads((KOK / "kurallar" / "pencere" / "pencereler.json").read_text(encoding="utf-8"))
KOR = KOK / "testler" / "kor" / "projeler"
ALTIN = KOK / "is_emri" / "ALTIN_2plus1_6x8.json"


def _ie(kod: str) -> dict:
    return json.loads((KOR / kod / "is_emri.json").read_text(encoding="utf-8"))


def _pencere(plan, olcu: str):
    """Pencerenin panosu ve kendisi; karkaslı kaplama panosunda (D-46) açıklık panonun açıklıklarından biri."""
    ps = [(p, a) for p in plan.panolar for a in p.aciklar if a.tur == "pencere" and a.olcu == olcu]
    assert len(ps) == 1, (olcu, len(ps))
    return ps[0][0]


def _acik(p, olcu: str):
    return next(a for a in p.aciklar if a.tur == "pencere" and a.olcu == olcu)


# --------------------------------------------------------------------------- veri tabanı

def test_veritabani_bicimi():
    assert VT["sema"] == "portman.pencere_veritabani/1" and "kısaltma" in VT["aciklama"]
    assert all({"deger", "kaynak"} <= set(v) for v in VT["kural"].values())
    k = {a: v["deger"] for a, v in VT["kural"].items()}
    assert (k["ust_kot_cm"], k["pano_payi_cm"], k["dosemeden"]) == (200, 4, True)
    assert (G.PENCERE_UST_KOTU_CM, G.PENCERE_PANO_PAYI_CM, G.PENCERE_EN_SINIRI, G.PENCERE_BOY_SINIRI) == (200.0, 4.0, (30, 999), (20, 240))
    olculer = [m["olcu"] for m in VT["modeller"]]
    assert len(olculer) == len(set(olculer))
    for m in VT["modeller"]:
        pk = G.pencere_kurali(m["olcu"])                          # her model kuralla kurulabilir
        assert m["tur"] in ("pencere", "vasistas") and m["kaynak"], m
        assert (m["tur"] == "vasistas") == (pk.boy <= 60), m        # vasistas: boy ≤ 60 (paftanın ve BOM'un ayrımı, `sunum.VASISTAS_ESIGI_CM`)
        assert m.get("acilis") in (None, "surgulu"), m
    assert {"120x120", "120x180", "60x40"} <= set(olculer)        # Motor'un ilk üçü


def _depodaki_pencereler():
    for f in sorted(KOK.glob("**/*.json")):
        r = f.relative_to(KOK).as_posix()
        if r.startswith(("deneme/", ".git/")) or "/node_modules/" in r:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(d, dict) and isinstance(d.get("acikliklar"), list):
            for a in d["acikliklar"]:
                if isinstance(a, dict) and a.get("tur") == "pencere" and a.get("olcu"):
                    yield r, a["olcu"]


def test_depodaki_her_pencere_kayitta():
    """Depodaki İş Emri'lerinin (referans, kör ölçüm, adaylar, harness) pencereleri kayıtta: gelen model kayda girer."""
    disi = sorted({(o, r) for r, o in _depodaki_pencereler() if o not in G.PENCERE_MODELLERI})
    assert not disi, disi


def test_kayitta_olmayan_pencere_kurulur_ve_uyarir():
    ie = json.loads(ALTIN.read_text(encoding="utf-8"))
    ie["acikliklar"][0]["olcu"] = "110x130"
    assert "110x130" not in G.PENCERE_MODELLERI
    plan = G.kur(ie)
    p = _pencere(plan, "110x130")
    assert (p.acilim.genislik, p.acilim.yukseklik) == (110.0, 130.0)
    assert any("110x130" in u and "pencere veri tabanında yok" in u for u in plan.uyarilar)
    assert not any("veri tabanında yok" in u for u in G.kur(json.loads(ALTIN.read_text(encoding="utf-8"))).uyarilar)


# --------------------------------------------------------------------------- kural: kısaltma yok

@pytest.mark.parametrize("olcu, esik, ust, pano", [
    ("120x180", 20.0, 200.0, 1), ("120x200", 0.0, 200.0, 1), ("180x200", 0.0, 200.0, 2), ("200x210", 0.0, 210.0, 2),
    ("280x210", 0.0, 210.0, 3), ("247x120", 80.0, 200.0, 2), ("248x120", 80.0, 200.0, 3), ("200x240", 0.0, 240.0, 2)])
def test_kural_kisaltmaz(olcu, esik, ust, pano):
    k = G.pencere_kurali(olcu)
    en, boy = map(int, olcu.split("x"))
    assert (k.en, k.boy, k.esik, k.ust, k.pano) == (en, boy, esik, ust, pano)


# --------------------------------------------------------------------------- Motor: kör ölçümün sürgülüleri

# D-46 (İE-28; Lokman, 4 Kasım 2026 04:35, "Paftadan, ev ev"): AP-14'ün 180/200'ü ve AP-26'nın iki sürgülüsü paftadaki karkaslı kaplama duvar
# panosunda (242,75; kapıyla birlikte 428,58; 491,33); AP-11'in 251'i odanın ortasında karkaslı pano. Pencerenin eni yine kısaltılmadan
@pytest.mark.parametrize("kod, olcu, pano_boy", [("AP11", "180x200", 2 * G.MOD), ("AP14", "180x200", 242.75),
                                                  ("AP26", "200x210", 428.58), ("AP26", "280x210", 491.33)])
def test_kor_surguluyu_paftadaki_olcusuyle(kod, olcu, pano_boy):
    ie = _ie(kod)
    a = [x for x in ie["acikliklar"] if x.get("olcu") == olcu]
    assert len(a) == 1 and a[0]["acilis"] == "surgulu"
    assert not [x for x in ie["acikliklar"] if x.get("olcu") in ("180x180", "240x180", "200x180") and x.get("acilis") == "surgulu"]
    plan = G.kur(ie)
    p = _pencere(plan, olcu)
    assert p.boy == pytest.approx(pano_boy, abs=1e-6) and p.karkasli
    k = G.pencere_kurali(olcu)
    g = p.bosluk_dortgeni(_acik(p, olcu))
    assert abs((g[2] - g[0] if p.duvar.yon == "x" else g[3] - g[1]) - k.en) < 1e-6
    assert not any("veri tabanında yok" in u for u in plan.uyarilar)


def _tek_oda(*ekler):
    """ALTIN'de ODA 1 ve ODA 2 tek oda: arka duvarında altı tam pano (10–763), açıklıksız."""
    ie = json.loads(ALTIN.read_text(encoding="utf-8"))
    ie["mahaller"] = [m for m in ie["mahaller"] if m["ad"] != "ODA 2"]
    for m in ie["mahaller"]:
        if m["ad"] == "ODA 1":
            m["konum_pano"] = [[0, 5, 6, 8]]
    ie["acikliklar"] = [a for a in ie["acikliklar"] if a.get("mahal") != "ODA 2" and "ODA 2" not in a.get("arasi", [])] + list(ekler)
    return ie


@pytest.mark.parametrize("pano, beklenen", [(0, (10.0, 386.5)), (2, (261.0, 637.5)), (3, (386.5, 763.0)),
                                            (4, (386.5, 763.0)), (5, (386.5, 763.0))])
def test_uc_panoluk_birlesme_sirasi(pano, beklenen):
    """n panoluk pencere: önce kendi panosu ve sonraki n − 1; sığmazsa birer geri kayarak (iki panoda bugünkü sıra: sonraki, önceki).
    Altı tam panolu duvarda 280'lik pencere: 0–3. panoda kendisi ve sonraki iki; 4'te bir, 5'te iki geri."""
    pen = {"tur": "pencere", "olcu": "280x120", "mahal": "ODA 1", "duvar": "arka", "pano": pano}
    p = _pencere(G.kur(_tek_oda(pen)), "280x120")
    assert (p.a0, p.a1) == beklenen


def test_uc_panoluk_dolu_panoyu_atlar():
    """Sonraki panolardan biri açıklıklı (vasistas) olunca pencere bir geri kayar: 2. pano + 3, 4 değil, 1 + 2 + 3."""
    pen = {"tur": "pencere", "olcu": "280x120", "mahal": "ODA 1", "duvar": "arka", "pano": 2}
    vas = {"tur": "pencere", "olcu": "60x40", "mahal": "ODA 1", "duvar": "arka", "pano": 4}
    plan = G.kur(_tek_oda(pen, vas))
    p = _pencere(plan, "280x120")
    assert (p.a0, p.a1) == (135.5, 512.0)
    assert [(q.a0, q.a1) for q in p.duvar.panolar if q.acilim and q.acilim.olcu == "60x40"] == [(512.0, 637.5)]


@pytest.mark.parametrize("olcu, ust_mm, alt_mm", [("120x180", 500, 200), ("120x200", 500, None), ("120x220", 300, None)])
def test_liste_pencere_panelleri_kuraldan(olcu, ust_mm, alt_mm):
    """Yükleme listesi 120'lik pencerenin üst ve alt panelini Motor'un pencere kuralından yazar (D-28 madde 1; geometri hakemi, İE-27
    PR-2): döşemeden pencerede alt panel yok, üst panel duvar yüksekliği − boy."""
    from motor import prefabrik_liste as PL
    ie = json.loads(ALTIN.read_text(encoding="utf-8"))
    ie["acikliklar"][3]["olcu"] = olcu                              # SALON ön 120x180
    L = PL.liste(PL.model_motor(ie), PL.kurallari_oku(), None)
    en, boy = olcu.split("x")
    altlar = [s for s in L["satirlar"] if s["kalem"].startswith(f"Pencere alt panel ({en}/{boy})")]
    ustler = {s["olcu"]: s["adet"] for s in L["satirlar"] if s["kalem"].startswith("Pencere üst panel")}
    assert ustler.get(f"100 × 1250 × {ust_mm}", 0) >= 1, ustler
    if alt_mm is None:
        assert not altlar, altlar
    else:
        assert [s["olcu"] for s in altlar] == [f"100 × 1250 × {alt_mm}"]
    assert not any(" × 0" == s["olcu"][-4:] or " × -" in s["olcu"] for s in L["satirlar"] if s["kalem"].startswith("Pencere"))


def test_uc_panoluga_yer_yoksa_hata():
    ie = json.loads(ALTIN.read_text(encoding="utf-8"))
    ie["acikliklar"][0]["olcu"] = "600x120"                      # beş panoluk: odanın duvarına sığmaz
    with pytest.raises(G.IsEmriHatasi, match="yanında tam pano yok"):
        G.kur(ie)


# --------------------------------------------------------------------------- görünüş, IFC, pafta

def test_gorunus_ve_ifc_dosemeden():
    from motor import cephe_gorunus as CG, ifc_uret as I
    ie = _ie("AP26")
    plan = G.kur(ie)
    gor = {a["olcu"]: a for t in CG.TARAFLAR for a in CG.cephe(plan, t)["acikliklar"] if a["tur"] == "pencere"}
    assert (gor["280x210"]["z0"], gor["280x210"]["z1"]) == (0.0, 210.0)
    assert (gor["200x210"]["z0"], gor["200x210"]["z1"]) == (0.0, 210.0)
    assert (gor["120x120"]["z0"], gor["120x120"]["z1"]) == (80.0, 200.0)
    ifc = {a["olcu"]: a for a in I.hazirla(json.loads(json.dumps(ie)))["acikliklar"] if a["tur"] == "pencere"}
    assert (ifc["280x210"]["z0"], ifc["280x210"]["z1"]) == (0.0, 210.0)       # önce IFC 200'de kesiyordu (KAPI_UST)
    assert (ifc["120x120"]["z0"], ifc["120x120"]["z1"]) == (80.0, 200.0)


def test_pafta_kot_yazisi_dosemeden_pencereyi_soyler():
    import ezdxf
    from motor import dxf_out
    for kod, beklenen in (("AP26", "döşemeden pencere 200/210, 280/210"), ("AP09", None)):
        with tempfile.TemporaryDirectory() as t:
            dxf_out.uret(_ie(kod), Path(t), pdf_hatada=False)
            doc = ezdxf.readfile(next(Path(t).glob("*.dxf")))
            yazi = [e.dxf.text for e in doc.modelspace().query("TEXT MTEXT") if "Pencere üst kotu" in e.dxf.text or "lento" in e.dxf.text]
        assert yazi, kod
        if beklenen:
            assert all(beklenen in s for s in yazi), yazi
        else:
            assert not any("döşemeden" in s for s in yazi), yazi
            assert any(re.search(r"Pencere üst kotu 200 cm \| Lento 50 cm", s) for s in yazi), yazi
