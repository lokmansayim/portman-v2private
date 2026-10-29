"""D-29 · Lokman'ın TK-02 aday çizimine yorumları (29 Ekim 2026), Motor kuralı olarak.

1. Oda ortasındaki pencerenin iki yanı yarım pano (62,75): "63 değil 627,5 mm ... salonun ilk panosu doğal olarak 125'e düşmüş". Oda ortasına
   ¼ pano içindeki ekin iki yanında tam pano varsa pencereli pano o eke ortalanır; yoksa odanın ortası (D-15, PK-01 paftası aynen).
2. Giriş nişinin hol tarafında köşe direği yok: "giriş kapısındaki hole açılan taraftaki köşe direklerini kaldır". Nişin yan duvarı hol duvarı
   olarak sürer, kapı duvarı ona dik: T birleşimi, 3'lü H; kapı duvarı yan duvarların yüzleri arasında.
3. Dış duvar T'sindeki 3'lü H kutusu çizilmez: "yeşil yeşil kutular ... bizde öyle birşey yok". Parça sayımda ve listede kalır.
4. Plandaki pencere yazısı alttan ya da sağdan okunur: "önden bakınca arkadaki yatak odası 1'in 120/180 yazısı ters kalıyor".
5. Özel pano ölçü yazıları üst üste binmez (TK-02 aday planında yatak odası 3'te 62,75 ile 125 üst üsteydi).

Ön görünüşteki veranda saçak ve topuk çizgisi (aynı gün) `test_veranda.py::test_on_gorunuste_veranda_sacak_ve_topuk`'ta. 1–3 anahtarlı İş Emri'nde
çalışır (o durum yalnız orada var); 4 ve 5 P6001 dahil bütün planlarda (D-29 madde 6, Lokman 08:22: "takılıp kalma P6001'e").
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import ezdxf
import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, geometry as G, prefabrik_liste as PL  # noqa: E402

VERI = KOK / "testler" / "motor" / "veri"
TK01 = KOK / "araclar" / "paket" / "girdi" / "TK01_r06.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=["TK02", "TK01_r06"])
def ie(request):
    return _oku(VERI / "TK02.json") if request.param == "TK02" else _oku(TK01)


def _duvar(plan, yon, c):
    """`c` hattındaki pencereli dış duvar."""
    return next(d for d in plan.duvarlar if d.tur == "dis" and d.yon == yon and abs(d.c - c) < 1e-6
                and any(p.acilim and p.acilim.tur == "pencere" for p in d.panolar))


def _boylar(d):
    return [(round(p.boy, 3), "P" if p.acilim and p.acilim.tur == "pencere" else "") for p in d.panolar]


def test_pencere_iki_yani_yarim_pano(ie):
    plan = G.kur(ie)
    sol = _boylar(_duvar(plan, "y", 5.0))                                   # salonun sol duvarı (Lokman'ın örneği)
    assert sol[:5] == [(125.0, ""), (62.75, ""), (125.5, "P"), (62.75, ""), (125.5, "")], sol
    arka = _boylar(_duvar(plan, "x", 883.0))                                # yatak odası 1'in arka penceresi
    assert arka[:3] == [(62.75, ""), (125.5, "P"), (62.75, "")], arka


def test_uzak_ekte_oda_ortasi_kalir():
    """Oda ortası en yakın ekten 5 cm'den çok kaçıyorsa pencere odanın ortasında kalır: kör PK-02'nin gerçek listesinde bu duvarda
    42,25 / 83,25 var (mühendis 20,5 cm kaydırmamış; geometri hakemi). Kısa kaymada (TK-02: 0,25 ve 2,5 cm) yarım pano."""
    plan = G.kur(_oku(KOK / "testler" / "kor" / "projeler" / "PK02" / "is_emri.json"))
    b = _boylar(_duvar(plan, "y", 768.0))
    assert [b[i - 1:i + 2] for i, x in enumerate(b) if x[1] == "P"][1] == [(42.25, ""), (125.5, "P"), (83.25, "")], b


def test_pk01_paftasi_degismez():
    """İki yanı tam pano olmayan pencere odanın tam ortasında kalır (PK-01 paftası: 40,5 / 37,5 ve 60,25 / 60,25)."""
    plan = G.kur(_oku(VERI / "PK01.json"))
    assert _boylar(_duvar(plan, "x", 205.0)) == [(125.5, ""), (40.5, ""), (125.5, "P"), (37.5, "")]
    assert _boylar(_duvar(plan, "x", 5.0)) == [(60.25, ""), (125.5, "P"), (60.25, "")]
    assert _boylar(_duvar(plan, "x", 995.0)) == [(125.5, ""), (62.75, ""), (125.5, "P"), (62.75, ""), (125.5, ""), (78.0, "")]


def test_nis_kapisinda_kose_yok_3lu_h(ie):
    plan = G.kur(ie)
    kapi = next(p for p in plan.panolar if p.acilim and p.acilim.tur == "dis_kapi")
    d = kapi.duvar
    assert (d.p0, d.p1, kapi.boy) == (391.5, 507.0, 115.5)                    # yan duvarların yüzleri arası
    assert not [k for k in plan.koseler if k.rect[1] < d.c + d.h and k.rect[3] > d.c - d.h]   # kapı hattında köşe parçası yok
    assert len(plan.koseler) == 8                                            # nişin ağzındaki iki köşe kalır
    h = sorted((round(b.x, 3), round(b.y, 3), b.tur) for b in plan.h_baglantilar if abs(b.y - d.c) < 1e-6)
    assert h == [(386.5, 130.0, "dis"), (512.0, 130.0, "dis")]
    ek = G.uc_uca_ekler(plan)
    assert sorted((k["x"], k["y"], k["cins"]) for k in ek) == [(386.5, 130.0, "uclu"), (512.0, 130.0, "uclu")]
    for c in (386.5, 512.0):                                                 # yan duvar kapının ekseninde hol duvarına ek verir
        uc = sorted((w.tur, w.p0, w.p1) for w in plan.duvarlar if w.yon == "y" and abs(w.c - c) < 1e-6 and 130.0 in (w.p0, w.p1))
        assert [(t, a if t == "ic" else b) for t, a, b in uc] == [("dis", 130.0), ("ic", 130.0)] and uc[0][1] == 5.0, uc
    L = PL.is_emrinden(ie)
    adet = lambda bas: sum(r["adet"] for r in L["satirlar"] if r["kalem"].startswith(bas))
    assert adet("3'lü H 100 × 100") == sum(b.tur == "dis" for b in plan.h_baglantilar) == 8
    assert adet("10'luk köşe direği") + adet("6'lık köşe direği") == len(plan.koseler)


def test_nis_t_yalniz_ayni_eksende(ie, tmp_path):
    """Dış düşey duvar aks dışındaysa (varsayılan) nişin yan duvarı ile hol duvarı aynı eksende değil: niş T'si kurulmaz, köşe parçası kalır;
    doğrulama geçer, çizimdeki ve listedeki dış duvar T'si 3'lü H sayısı aynı (geometri hakemi, önemli 3)."""
    ie = json.loads(json.dumps(ie)); ie["yapi"].pop("dis_dusey_duvar")
    plan = G.kur(json.loads(json.dumps(ie)))
    assert G.uc_uca_ekler(plan) == []
    m = dxf_out.uret(json.loads(json.dumps(ie)), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True, m.get("warnings")
    L = PL.is_emrinden(json.loads(json.dumps(ie)))
    adet = sum(r["adet"] for r in L["satirlar"] if r["kalem"].startswith("3'lü H 100 × 100"))
    assert adet == sum(b.tur == "dis" for b in plan.h_baglantilar)


def test_dogrulamadan_gecer_dis_h_kutusu_cizilmez(ie, tmp_path):
    m = dxf_out.uret(ie, tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True, m.get("warnings")
    d = ezdxf.readfile(tmp_path / m["dxf"])
    assert d.layers.get("DIS_UCLU_H_GOVDE").is_off()
    blk = [b for b in d.blocks if b.name.startswith("BOM_") and "_UCLU_H_DIS_" in b.name]
    assert blk and all(e.dxf.layer == "DIS_UCLU_H_GOVDE" for b in blk for e in b)   # kutu kapalı katmanda; sayım INSERT'ten
    v = _oku(tmp_path / "validation.json")
    assert v["h_connectors_dis"] == sum(b.tur == "dis" for b in G.kur(ie).h_baglantilar)


@pytest.fixture(params=["TK02", "TK01_r06", "P6001"])
def ie_hepsi(request):
    """Pencere yazısı kuralı anahtarsız İş Emri'nde de çalışır (D-29 madde 6)."""
    yol = {"TK02": VERI / "TK02.json", "TK01_r06": TK01, "P6001": KOK / "is_emri" / "P6001_2plus1_6x6.json"}[request.param]
    return _oku(yol)


def test_pencere_yazisi_alttan_ya_da_sagdan_okunur(ie_hepsi, tmp_path):
    m = dxf_out.uret(ie_hepsi, tmp_path, pdf_hatada=False)
    msp = ezdxf.readfile(tmp_path / m["dxf"]).modelspace()

    def yazilar(e):
        for v in e.virtual_entities():
            if v.dxftype() == "INSERT":
                yield from yazilar(v)
            elif v.dxftype() == "TEXT":
                yield v
    acilar = [round(t.dxf.rotation % 360.0, 3) for e in msp.query("INSERT") if "_P0" in e.dxf.name for t in yazilar(e)]
    assert acilar and all(a <= 90.0 + 1e-6 or a > 270.0 for a in acilar), acilar
    assert any(e.dxf.name.endswith("_Y") for e in msp.query("INSERT"))      # arka ve sol duvarın pencereleri çevrilmiş blokla


@pytest.mark.parametrize("yol", [VERI / "TK02.json", TK01, VERI / "PK01.json", KOK / "is_emri" / "P6001_2plus1_6x6.json",
                                 KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json", KOK / "is_emri" / "ALTIN_2plus1_6x8.json"],
                         ids=lambda p: p.stem)
def test_ozel_pano_olcu_yazilari_ust_uste_binmez(yol, tmp_path):
    """Kat planı, net alan planı ve saha montaj planındaki özel pano ölçülerinin yazıları (gerçek yerleri, DIMENSION bloğundaki MTEXT)
    birbirine binmez (D-29 madde 7). Önceki kodda TK-02'de 8 + 4, PK-01'de 4 + 2, Yan Verandalı 6×8,5'te 4 + 2 çakışma vardı."""
    m = dxf_out.uret(_oku(yol), tmp_path, pdf_hatada=False)
    msp = ezdxf.readfile(tmp_path / m["dxf"]).modelspace()
    for kat in ("OZEL_PANEL_OLCU_CM", "MONTAJ_OZEL_OLCU"):
        kutular = []
        for e in msp.query(f"DIMENSION[layer=='{kat}']"):
            for t in e.get_geometry_block().query("MTEXT"):
                x, y = t.dxf.insert[0], t.dxf.insert[1]; w = dxf_out.Cizici.yazi_eni(t.text, t.dxf.char_height) / 2
                kutular.append((t.text, (x - w, y - 7, x + w, y + 7) if abs(t.dxf.get("rotation", 0.0)) < 1e-6 else (x - 7, y - w, x + 7, y + w)))
        assert kutular
        cakisan = [(a[0], b[0], [round(v) for v in a[1]]) for i, a in enumerate(kutular) for b in kutular[i + 1:]
                   if a[1][0] < b[1][2] and b[1][0] < a[1][2] and a[1][1] < b[1][3] and b[1][1] < a[1][3]]
        assert not cakisan, (kat, cakisan)
