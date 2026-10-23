"""BK-13 · Pano Motor'unun pencere kataloğu (Lokman, kartlar 23 Ekim 06:23: "Uygula", "251'lik pano", "Üstü 200").

- Her ölçü tek kuraldan (`geometry.pencere_kurali`): "ENxBOY" tam cm, en 30–247, boy 20–180; eşik = 200 − boy; en 121,5'i geçerse pencere
  iki panoluk 251'lik pencereli panoda.
- Komşu kuralı (CIO notu 2): önce dizilim yönünde sonraki pano, olmazsa önceki; tam boy, açıklıksız, aynı odanın duvar aralığında. Yoksa hata.
- Bugünkü üç ölçü (120x120, 120x180, 60x40) eskisi gibi: eşik, yazı, kod ve blok adları aynı; yalnız bunları kullanan çizimde yeni kod
  tahsis edilmez (CIO notu 3). Çıktıların bayt bayt aynılığı referans gerilemesinde (`dogrula.py`, DXF/PDF içerik izleri).
- Deneme girdisi: ALTIN 6×8 İş Emri'nin pencereleri T76'nın dört ölçüsü (150x140, 60x60, 120x150, 180x150) ve PK-07'nin 100x120'si
  (CIO notu 5; PK-08'in ölçüleri test edilmez).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402

ALTIN = KOK / "is_emri" / "ALTIN_2plus1_6x8.json"
PK01 = KOK / "testler" / "motor" / "veri" / "PK01.json"
DENEME = {0: "150x140", 1: "120x150", 2: "180x150", 4: "100x120", 5: "60x60"}     # ALTIN açıklık sırası → yeni ölçü (3: SALON 120x180 kalır)
GENIS = {"150x140", "180x150"}


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _kopya(ie: dict) -> dict:
    return json.loads(json.dumps(ie))


def _deneme() -> dict:
    ie = _oku(ALTIN)
    ie.pop("altin_beklenti", None); ie["yapi"]["referans_model"] = "BK13-deneme"; ie["is_emri_no"] = "PM-BK13-DENEME"
    for i, olcu in DENEME.items():
        ie["acikliklar"][i]["olcu"] = olcu
    return ie


def _pencereler(plan) -> dict:
    return {p.acilim.olcu: p for p in plan.panolar if p.acilim and p.acilim.tur == "pencere"}


# --------------------------------------------------------------------------- kural

def test_bugunku_uc_olcu_eskisi_gibi():
    """Eşik BOM notlarındaki 80, 20, 160 (eski `ifc_uret.PENCERE_ESIK`); yazı eski `sunum.PENCERE_OLCU_YAZISI`; tek panoda."""
    eski_esik = {"120x120": 80.0, "120x180": 20.0, "60x40": 160.0}
    eski_yazi = {"120x120": "120/120", "120x180": "120/180", "60x40": "60/40"}
    for olcu, (en, boy) in G.PENCERE_OLCULERI.items():
        k = G.pencere_kurali(olcu)
        assert (k.en, k.boy, k.esik, k.pano) == (en, boy, eski_esik[olcu], 1)
        assert G.pencere_yazisi(olcu) == eski_yazi[olcu]


@pytest.mark.parametrize("olcu, en, boy, esik, pano", [
    ("150x140", 150, 140, 60.0, 2), ("60x60", 60, 60, 140.0, 1), ("120x150", 120, 150, 50.0, 1), ("180x150", 180, 150, 50.0, 2),
    ("100x120", 100, 120, 80.0, 1),
    ("30x20", 30, 20, 180.0, 1), ("247x180", 247, 180, 20.0, 2), ("121x120", 121, 120, 80.0, 1), ("122x120", 122, 120, 80.0, 2)])
def test_kural_esik_200_eksi_boy_ve_pano(olcu, en, boy, esik, pano):
    k = G.pencere_kurali(olcu)
    assert (k.en, k.boy, k.esik, k.pano) == (en, boy, esik, pano)
    assert k.esik + k.boy == G.PENCERE_UST_KOTU_CM == 200.0


@pytest.mark.parametrize("olcu", ["29x120", "248x120", "120x19", "120x181", "120X120", "120x120 ", "120*120", "060x040", "120x120x50",
                                  "", None, 120, "1200x1200"])
def test_sinir_disi_ya_da_yanlis_yazim_hata(olcu):
    with pytest.raises(G.IsEmriHatasi, match="Katalog dışı pencere ölçüsü"):
        G.pencere_kurali(olcu)


def test_sinir_disi_olcu_motorda_hata():
    ie = _oku(ALTIN); ie["acikliklar"][0]["olcu"] = "260x120"
    with pytest.raises(G.IsEmriHatasi, match="Katalog dışı pencere ölçüsü"):
        G.kur(ie)


# --------------------------------------------------------------------------- Motor

def test_t76_ve_pk07_olculeri_kuruluyor():
    plan = G.kur(_deneme())
    pen = _pencereler(plan)
    assert set(pen) == set(DENEME.values()) | {"120x180"}
    for olcu, p in pen.items():
        k = G.pencere_kurali(olcu)
        assert (p.acilim.genislik, p.acilim.yukseklik) == (float(k.en), float(k.boy))
        assert p.boy == (2 * G.MOD if olcu in GENIS else G.MOD), (olcu, p.boy)            # geniş pencere 251'lik panoda
        g = p.gap(); assert abs((g[2] - g[0] if p.duvar.yon == "x" else g[3] - g[1]) - k.en) < 1e-6
    assert plan.uyarilar == []


def test_komsu_sonraki_yoksa_onceki():
    """ODA 1 sol duvarı (aralık 632,5–1009) üç pano: 0 → sonraki (632,5–883,5); 1 → sonraki (758–1009); 2 duvarın son panosu → önceki."""
    beklenen = {0: (632.5, 883.5), 1: (758.0, 1009.0), 2: (758.0, 1009.0)}
    for idx, (a0, a1) in beklenen.items():
        ie = _oku(ALTIN); ie["acikliklar"][0].update(olcu="150x140", pano=idx)
        p = _pencereler(G.kur(ie))["150x140"]
        assert (p.a0, p.a1) == (a0, a1), idx
        d = p.duvar
        assert sum(1 for q in d.panolar if q.a0 < p.a1 - 1e-6 and q.a1 > p.a0 + 1e-6) == 1, "birleşen iki pano tek pano olmalı"


def test_komsu_yoksa_hata():
    """BANYO sağ duvarında iki pano: ilki açıklıklı, sonraki ODA 2'nin aralığında → "yanında tam pano yok"."""
    ie = _oku(ALTIN)
    ie["acikliklar"].insert(5, {"tur": "pencere", "olcu": "60x40", "mahal": "BANYO / WC", "duvar": "sag", "pano": 0})
    ie["acikliklar"][6]["olcu"] = "150x140"                                     # BANYO'nun asıl penceresi (pano 1)
    with pytest.raises(G.IsEmriHatasi, match="yanında tam pano yok"):
        G.kur(ie)
    ie["acikliklar"].pop(5)                                                   # önceki boşsa önceki alınır
    p = _pencereler(G.kur(ie))["150x140"]
    assert (p.a0, p.a1) == (381.5, 632.5)


def test_ayni_girdi_ayni_cikti():
    ozet = lambda pl: [(d.id, [(q.a0, q.a1, q.acilim.olcu if q.acilim else None) for q in d.panolar]) for d in pl.duvarlar]
    assert ozet(G.kur(_deneme())) == ozet(G.kur(_deneme()))


def test_oda_ortasi_genis_pencerede_yapilmaz():
    """PK-01 (`dizilim.pencere: oda_ortasi`, arka-sol): geniş pencere ızgara panosunda kalır, uyarı yazılır; öteki pencereler eskisi gibi."""
    eski = G.kur(_oku(PK01))
    ie = _oku(PK01)
    a = next(a for a in ie["acikliklar"] if a["tur"] == "pencere" and a["mahal"] == "YATAK ODASI 1")
    a["olcu"] = "150x140"
    plan = G.kur(ie)
    assert any("YATAK ODASI 1 150x140: panodan geniş pencere oda ortasına alınmadı" in u for u in plan.uyarilar)
    p = next(p for p in plan.panolar if p.acilim and p.acilim.olcu == "150x140")
    assert p.boy == 2 * G.MOD
    yer = lambda pl: sorted((p.acilim.mahal, p.acilim.olcu, p.a0, p.a1) for p in pl.panolar
                            if p.acilim and p.acilim.tur == "pencere" and p.acilim.mahal != "YATAK ODASI 1")
    assert yer(plan) == yer(eski)


# --------------------------------------------------------------------------- çıktılar

@pytest.fixture(scope="module")
def deneme_uret(tmp_path_factory):
    from motor import dxf_out
    d = tmp_path_factory.mktemp("bk13")
    m = dxf_out.uret(_deneme(), d, pdf_hatada=True)
    return d, m


def test_dxf_dogrulama_ve_semboller(deneme_uret):
    import ezdxf
    d, m = deneme_uret
    v = json.loads((d / "validation.json").read_text(encoding="utf-8"))
    assert m["validation_passed"] is True and m["pdf"] is not None, v["errors"]
    assert (v["windows"], v["doors"]) == (6, 4)
    doc = ezdxf.readfile(d / m["dxf"])
    for olcu in set(DENEME.values()):
        k = G.pencere_kurali(olcu)
        blk = doc.blocks.get(f"kaynak-pencere-{k.en}x{k.boy}")
        assert blk is not None, olcu
        assert [e.dxf.text for e in blk.query("TEXT")] == [f"{k.en}/{k.boy}"]           # ölçü yazısı kaynağın "120/120"si değil
        ys = [y for e in blk.query("LINE") for y in (e.dxf.start.y, e.dxf.end.y)]
        assert abs(max(ys) - min(ys) - k.en) < 1e-6, olcu                               # sembol duvar boyunca en kadar
    tablo = [e.dxf.text for e in doc.modelspace().query("TEXT") if e.dxf.text.startswith("PVC doğrama")]
    assert tablo == ["PVC doğrama; 60×60, 100×120, 120×150, 120×180, 150×140, 180×150"]


def test_kodlar_ve_etiketler(deneme_uret):
    d, m = deneme_uret
    bom = {r["malzeme"]: r for r in json.loads((d / "bom.json").read_text(encoding="utf-8"))["kalemler"]}
    for olcu in DENEME.values():
        k = G.pencere_kurali(olcu)
        ad = "Vasistas" if k.boy <= 60 else "Pencere"
        r = bom[f"{ad} {k.en}×{k.boy}"]
        assert r["kod"][0] == "P" and r["kod"] not in ("P01", "P02", "P03") and r["olcu_mm"][:2] == [k.en * 10, k.boy * 10]
        assert f"eşik {round(k.esik * 10)} mm" in r["not"] and "teyit edilmeli" in r["not"]
        pano = bom[f"{k.en}×{k.boy} " + ("vasistaslı pano" if k.boy <= 60 else "pencereli pano")]
        assert pano["kod"][0] == "D" and pano["olcu_mm"][0] == (2510.0 if olcu in GENIS else 1255.0)
    assert bom["120×180 pencereli pano"]["kod"] == "D03" and bom["Pencere 120×180"]["kod"] == "P02"


def test_ifc_esik_ve_ust_kot():
    from motor import ifc_uret
    hz = ifc_uret.hazirla(_deneme())
    pen = {a["olcu"]: a for a in hz["acikliklar"] if a["tur"] == "pencere"}
    assert set(pen) == set(DENEME.values()) | {"120x180"}
    for olcu, a in pen.items():
        k = G.pencere_kurali(olcu)
        assert (a["z0"], a["z1"]) == (k.esik, 200.0) and abs(a["a1"] - a["a0"] - k.en) < 0.01


def test_pafta_yazisi_ve_vasistas(tmp_path):
    from motor import sunum
    oz = sunum.bayi_paftasi(_deneme(), tmp_path, perspektif=False)
    assert oz["teslim"] is True
    assert sorted(oz["sayimlar"]["pencere"]) == ["100/120", "120/150", "120/180", "150/140", "180/150"]
    assert oz["sayimlar"]["vasistas"] == ["60/60"]


def test_liste_karkasli_ozel_pencere_panosu():
    from motor import prefabrik_liste as PL
    L = PL.liste(PL.model_motor(_deneme()))
    S = {(s["kalem"], s["olcu"]): s["adet"] for s in L["satirlar"]}
    for olcu in ("100/120", "150/140", "180/150"):
        assert any(k[0] == f"Karkaslı özel pencere panosu ({olcu})" and v == 1 for k, v in S.items()), olcu
    assert S[("PVC vasistas", "60/60")] == 1 and S[("PVC pencere", "150/140")] == 1


def test_bugunku_olculerde_yeni_kod_yok(tmp_path):
    """Yalnız üç ölçüyü kullanan İş Emri'nde pencere ve pencereli pano kodları kataloğun kodları; ölçekli kaynak blok açılmaz."""
    import ezdxf
    from motor import dxf_out
    m = dxf_out.uret(_oku(ALTIN), tmp_path, pdf_hatada=True)
    assert m["validation_passed"] is True
    kat = json.loads((tmp_path / "malzeme_katalogu.guncel.json").read_text(encoding="utf-8"))["malzemeler"]
    assert not [k for k in m["yeni_kodlar"] if k[0] == "P" or "pencereli" in kat[k]["label"] or "vasistaslı" in kat[k]["label"]]
    doc = ezdxf.readfile(tmp_path / m["dxf"])
    adlar = {b.name for b in doc.blocks}
    assert {"BOM_P01_PENCERE_1200x1200", "BOM_P02_PENCERE_1200x1800", "BOM_P03_PENCERE_600x400"} <= adlar
    assert not [a for a in adlar if a.startswith("kaynak-pencere-") and "x" in a]
    tablo = [e.dxf.text for e in doc.modelspace().query("TEXT") if e.dxf.text.startswith("PVC doğrama")]
    assert tablo == ["PVC doğrama; katalog 120×120 / 120×180 / 60×40"]
