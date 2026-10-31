"""BK-14 · Gövdeden taşan veranda (İş Emri `verandalar`).

Motor önceden yalnız pano ızgarasının içindeki verandayı çiziyordu; gövdenin dışına taşan veranda (TK-01: önde 386 × 181, arkada 261 × 130)
girdide yer bulamıyordu. Şimdi veranda gövdenin dış yüzüne dışarıdan eklenir: açık mahal, üç açık kenar (kiriş), iki dış köşede dikme ve
kendi çatısı. Plan, DXF ve doğrulama (dört görünüş dahil; D-31), bayi paftası (plan ve çatı planı), IFC ve yükleme listesi aynı
geometriden; bayiye canlıdaki gibi teknik pafta (`dxf_out`) ve plan görseli (`bayi_gorseli`) gider. Liste
TK-01'in geçici yolundaki listeyle (gövde Motor'dan, verandalar elle; `Teklif_Calisma/TK-01/gecici_r01`) bütün satırlarda aynı adeti verir;
burada o değerler sabit. `verandalar` yoksa hiçbiri devreye girmez (referans gerilemesi bayt bayt aynı). Bu bir Motor kilididir, paftaya
uygunluk kanıtı değildir. D-30 (Lokman, 29 Ekim 2026): TK-01'in gövdesi 898 × 888 → 898,5 × 888,5 (iki yönde son pano 125 ≥ 122, tam panoya);
arka verandanın kotları, gövde kutusu, oturum alanı, dış çevre ve brüt alan buna göre; verandaların kendi ölçüleri ve kenarları aynı.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import dxf_out, geometry as G, prefabrik_liste as PL, sunum, veranda as VR  # noqa: E402
from shapely.geometry import box  # noqa: E402

TK01 = KOK / "testler" / "motor" / "veri" / "TK01.json"
PK01 = KOK / "testler" / "motor" / "veri" / "PK01.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _ie(verandalar=None) -> dict:
    ie = _oku(TK01)
    if verandalar is not None:
        ie["verandalar"] = verandalar
    return ie


@pytest.fixture(scope="module")
def plan():
    return G.kur(_ie())


def test_veranda_geometrisi(plan):
    on, arka = plan.dis_verandalar
    assert (on["ad"], on["cephe"], on["rect"]) == ("ÖN VERANDA", "on", (256.0, -181.0, 642.0, 0.0))
    assert (arka["ad"], arka["cephe"], arka["rect"]) == ("ARKA VERANDA", "arka", (0.0, 888.5, 261.0, 1018.5))         # D-30
    assert plan.mahaller["ÖN VERANDA"].acik and plan.mahaller["ÖN VERANDA"].alan_m2 == pytest.approx(6.9866)
    assert plan.mahaller["ARKA VERANDA"].alan_m2 == pytest.approx(3.393)
    assert on["kolonlar"] == [(256.0, -181.0, 266.0, -171.0), (632.0, -181.0, 642.0, -171.0)]
    assert arka["kolonlar"] == [(0.0, 1008.5, 10.0, 1018.5), (251.0, 1008.5, 261.0, 1018.5)]
    assert len(plan.dikmeler) == 4 and all(k in plan.dikmeler for v in plan.dis_verandalar for k in v["kolonlar"])
    uz = lambda e: max(e[2] - e[0], e[3] - e[1])
    assert [uz(e) for v in plan.dis_verandalar for e in v["kenarlar"]] == [386.0, 181.0, 181.0, 261.0, 130.0, 130.0]
    assert all(e in plan.acik_kenarlar for v in plan.dis_verandalar for e in v["kenarlar"])
    assert G.govde_kutusu(plan) == (0.0, 0.0, 898.5, 888.5)              # ana çatı gövdeyi örter (D-30: tam pano)
    assert sunum.sinirlar(plan) == (0.0, -181.0, 898.5, 1018.5)
    assert sunum.oturum_m2(plan) == pytest.approx(90.21, abs=0.01)
    assert not [u for u in plan.uyarilar if u.startswith("Veranda")]     # iki çatı da İş Emri'nde, ikisi de ana çatının kalkan yüzünde


def test_veranda_catisi(plan):
    on, arka = (VR.cati(v, plan.is_emri) for v in plan.dis_verandalar)
    assert on["tip"] == "besik" and on["kutu"] == (226.0, -211.0, 672.0, 0.0)  # dış kenarda ve iki yanda 30 saçak, cephede yok
    assert on["sacak_kotu"] == 260.0 and on["mahya_kotu"] == pytest.approx(321.325)
    assert on["mahya"] == ((449.0, -211.0), (449.0, 0.0))                 # mahya cepheye dik
    assert arka["kutu"] == (-30.0, 888.5, 291.0, 1048.5) and arka["mahya_kotu"] == pytest.approx(304.1375)
    p = VR.gorunus_parcalari(plan, plan.is_emri, "on")
    say = {t: sum(x["tur"] == t for x in p) for t in ("kolon", "kiris", "alin", "cati")}
    assert say == {"kolon": 4, "kiris": 6, "alin": 0, "cati": 2}         # önden iki kalkan görünür; alın çerçevesi yok (D-31 madde 3)
    yan = VR.gorunus_parcalari(plan, plan.is_emri, "sag")
    assert not [x for x in yan if x["tur"] == "alin"] and sum(x["tur"] == "cati" for x in yan) == 2


def test_veranda_dogrulamadan_gecer(tmp_path):
    m = dxf_out.uret(_ie(), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True, m.get("errors")
    v = _oku(tmp_path / "validation.json")
    assert v["rooms_m2"]["ÖN VERANDA"] == pytest.approx(6.9866) and v["rooms_m2"]["ARKA VERANDA"] == pytest.approx(3.393)
    dxf = next(tmp_path.glob("*.dxf")).read_text(encoding="utf-8", errors="ignore")
    for blok in ("_VERANDA_ON_", "_VERANDA_YAN_"):
        assert blok in dxf, blok


def _nisli() -> dict:
    """TK-01 r06 (Patron 28 Ekim 08:01, "dış kapı 1 pano içeride"): ANTRE kapalı oda değil, önü açık giriş nişi; dış kapı niş ile hol arasında."""
    ie = _ie()
    for m in ie["mahaller"]:
        if m["ad"] == "ANTRE":
            m["ad"], m["tur"] = "GİRİŞ", "veranda"
    ie["acikliklar"] = [a for a in ie["acikliklar"] if a.get("arasi") != ["ANTRE", "HOL"]]
    for a in ie["acikliklar"]:
        if a["tur"] == "dis_kapi":
            a["arasi"] = ["GİRİŞ", "HOL"]
            del a["duvar"]
    return ie


def test_veranda_giris_nisinin_onunde(tmp_path):
    """Ön verandanın iç kenarı nişin ağzında gövdenin dış yüzüne değil nişe değer; nişin ağzı cephe sayılır. Nişin üç yanı dış duvar
    (10 cm), kapı bir pano içeride; ağızdaki kiriş listede ve teknik paftanın BOM'unda aynı (7 profil). Nişsiz hâli değişmez
    (test_veranda_geometrisi)."""
    p = G.kur(_nisli())
    assert p.dis_verandalar[0]["rect"] == (256.0, -181.0, 642.0, 0.0)
    assert p.mahaller["GİRİŞ"].acik and p.mahaller["GİRİŞ"].alan_m2 == pytest.approx(1.449525)     # D-30: niş derinliği 125 → 125,5
    kapi = [q for q in p.panolar if q.acilim and q.acilim.tur == "dis_kapi"]
    assert len(kapi) == 1 and kapi[0].acilim.arasi == ("GİRİŞ", "HOL") and kapi[0].gap() == (404.25, 125.5, 494.25, 135.5)  # bir pano içeride
    nis = [d for d in p.duvarlar if any(box(*q.rect()).intersects(box(391.5, 0.0, 507.0, 125.0).buffer(-0.5).buffer(6)) for q in d.panolar)]
    assert len(nis) == 3 and all(d.tur == "dis" and 2 * d.h == 10.0 for d in nis)                # iki yan ve kapının duvarı
    N = PL.model_motor(_nisli())
    assert N["veranda_kenarlari_cm"] == [386.0, 181.0, 181.0, 261.0, 130.0, 130.0] and N["nis_agizlari_cm"] == [125.5]   # ağız aks arası
    L = PL.liste(N)
    agiz = [s for s in L["satirlar"] if s["kalem"].startswith("Kutu profil (kiriş)") and s["olcu"] == "L 1255"]
    assert len(agiz) == 1 and agiz[0]["adet"] == 1
    m = dxf_out.uret(_nisli(), tmp_path, pdf_hatada=False)
    assert m["validation_passed"] is True, m.get("errors")
    assert _oku(tmp_path / "validation.json")["rooms_m2"]["GİRİŞ"] == pytest.approx(1.449525)
    bom = _oku(tmp_path / "bom.json")["kalemler"]
    assert sum(k["adet"] for k in bom if k["kod"].startswith("V")) == len(N["veranda_kenarlari_cm"]) + len(N["nis_agizlari_cm"])   # 7 profil


def test_nis_agzi_yalniz_tek_yuzu_acik_mahalde():
    """Listede niş, geometrinin tanımıyla: tek yüzü açık, dikmesiz açık mahal (geometri hakemi 2. tur, 28 Ekim). Katalogdaki köşe
    verandası (iki yüzü açık) taşan veranda eklenince de verandanın kuralıyla sayılır: köşesine Motor kolon koyar (D-36,
    `test_kose_kolonu`; D-35'te burada kolonsuz köşe kirişiydi); nişin ağız kirişi plandaki dikmelerden bağımsız."""
    ie = _oku(KOK / "is_emri" / "P6001_2plus1_6x6.json")
    ie["verandalar"] = [{"ad": "V", "cephe": "arka", "bas_cm": 0, "bit_cm": 300, "derinlik_cm": 150}]
    N = PL.model_motor(ie)
    assert "nis_agizlari_cm" not in N and N["veranda_kenarlari_cm"] == [439.25, 251.0, 300.0, 150.0, 150.0] and N["kose_kolonlari"] == 1
    nis = _nisli()
    del nis["verandalar"]
    N = PL.model_motor(nis)
    assert N["veranda_kenarlari_cm"] == [] and N["nis_agizlari_cm"] == [125.5]


def test_kose_kolonu(tmp_path):
    """D-36 (Lokman, 31 Ekim 15:08: "tam kirişlerin birleştiği yerde kolon gelir ... hiçbir zaman kirişler askıda kalmaz"): gövdenin içindeki
    açık mahalin iki açık kenarı köşede birleşiyorsa Motor o köşeye 10 × 10 dikme koyar, dış yüzleri mahalin dış ölçüsüyle aynı hizada (PK-01'in
    köşe dikmesi gibi). Kirişler kolonlu verandanın kuralıyla: açık kenar dış ölçüsü − 10 (P6001 L 4292,5 ve 2410; TK-03 balkonu L 3037,5 ve
    1832,5); listede kolon satırı. D-35'in kolonsuz köşe kirişi (dış ölçü) kalktı. İş Emri'nde köşesinde dikme olan veranda (PK-01, taşan
    verandalı TK-02) ve tek yüzü açık niş kolon almaz."""
    ie = _oku(KOK / "is_emri" / "P6001_2plus1_6x6.json")
    p = G.kur(ie)
    assert p.kose_kolonlari == [(0.0, 0.0, 10.0, 10.0)] and p.dikmeler == p.kose_kolonlari
    N = PL.model_motor(ie)
    assert N["veranda_kenarlari_cm"] == [439.25, 251.0] and N["dikmeler"] == N["kose_kolonlari"] == 1 and "nis_agizlari_cm" not in N
    L = PL.liste(N)["satirlar"]
    kiris = [s for s in L if s["kalem"].startswith("Kutu profil (kiriş)")]
    assert [(s["olcu"], s["adet"]) for s in kiris] == [("L 4292,5", 1), ("L 2410", 1)]
    kolon = [s for s in L if s["kalem"].startswith("Özel kutu profil (kolon)")]
    assert [(s["olcu"], s["adet"]) for s in kolon] == [("L 2500", 1)] and "D-36" in kolon[0]["kaynak"] and "köşede" in kolon[0]["formul"]
    dxf_out.uret(ie, tmp_path, pdf_hatada=False)
    bom = _oku(tmp_path / "bom.json")["kalemler"]
    assert [k["adet"] for k in bom if k["malzeme"] == "Veranda dikmesi"] == [1]                # teknik paftada da (PK-01 gibi)
    N3 = PL.model_motor(_oku(KOK / "testler" / "motor" / "veri" / "TK03.json"))
    assert N3["kose_kolonlari"] == 1 and N3["veranda_kenarlari_cm"] == [313.75, 193.25]
    assert G.kur(_oku(KOK / "testler" / "motor" / "veri" / "TK03.json")).kose_kolonlari == [(0.0, 863.3, 10.0, 873.3)]
    kiris3 = [s["olcu"] for s in PL.liste(N3)["satirlar"] if s["kalem"].startswith("Kutu profil (kiriş)") and "açık kenar" in s["formul"]]
    assert kiris3 == ["L 3037,5", "L 1832,5"]
    for dosya in ("PK01.json", "TK02.json"):
        assert G.kur(_oku(KOK / "testler" / "motor" / "veri" / dosya)).kose_kolonlari == []
    nis = _nisli()
    del nis["verandalar"]
    assert G.kur(nis).kose_kolonlari == []


@pytest.mark.parametrize("girdi, v", [
    ("nis", {"ad": "V", "cephe": "on", "bas_cm": 400, "bit_cm": 500, "derinlik_cm": 150}),   # iki iç köşesi nişin ağzında, havada
    ("nis", {"ad": "V", "cephe": "on", "bas_cm": 450, "bit_cm": 700, "derinlik_cm": 150}),   # bir iç köşesi nişin ağzında
    ("pk01", {"ad": "V", "cephe": "on", "bas_cm": 300, "bit_cm": 580, "derinlik_cm": 150}),  # köşedeki ızgara verandasının önünde
    ("pk01", {"ad": "V", "cephe": "sag", "bas_cm": 20, "bit_cm": 180, "derinlik_cm": 150}),  # ... ve yanında
    ("pk01", {"ad": "V", "cephe": "sag", "bas_cm": 50, "bit_cm": 400, "derinlik_cm": 150}),
])
def test_veranda_nis_disinda_oturmuyor(girdi, v):
    """Nişin ağzı yalnız verandanın iki iç köşesi duvardaysa ve nişin bütün açık kenarı verandanın iç kenarındaysa dış yüz sayılır
    (geometri hakemi, 28 Ekim); öteki boşluklar eskisi gibi hata."""
    ie = _nisli() if girdi == "nis" else _oku(PK01)
    ie["verandalar"] = [v]
    with pytest.raises(G.IsEmriHatasi, match="tam oturmuyor"):
        G.kur(ie)


def test_veranda_profili_kiris_yerinde(plan):
    """DXF'in veranda profili blokları (BOM ve IFC kirişleri bunlardan): her verandada üç, kutusu Plan'ın kirişiyle aynı; gövde duvarının
    içine profil düşmez, iki yanın iç çizgisi verandanın içinde (geometri hakemi, 27 Ekim: eski döngü gövde çizgisini de profil sayıyordu,
    aynı adlı iki yan bloğu bir yanın kaymasıyla çiziliyordu)."""
    from motor import ifc_uret
    g = ifc_uret.hazirla(_ie())
    profil = sorted(tuple(b["rect"]) for b in g["baglantilar"] if b["tur"] == "veranda_profil")
    kiris = sorted(tuple(round(t, 2) for t in k) for v in plan.dis_verandalar for k in v["kirisler"])
    assert profil == kiris and len(profil) == 6
    assert sum(b["tur"] == "dikme" for b in g["baglantilar"]) == 4
    assert g["veranda"] is None and [v["net_m2"] for v in g["dis_verandalar"]] == [pytest.approx(6.9866), pytest.approx(3.393)]


def test_veranda_listesi():
    """TK-01 listesi. Taşan verandanın dış kirişi kolonların dış yüzünden dış yüzüne, açık kenar boyunda (Lokman, kart 28 Ekim, "A: dış
    yüzden dış yüze": 3760 / 2510 → 3860 / 2610); iki yan kiriş açık kenar − 10 (1710, 1200), eskisi gibi. Satır sayısı D-29'la (Lokman 29 Ekim,
    pencerenin iki yanı 62,75'lik yarım pano) 131 → 128, ters tavanda 129 → 126: 100'lük dolu panonun dört boyu tek boya indi. D-30 (Lokman,
    29 Ekim 2026, son pano 122 ve üzeriyse tam pano): gövde 898,5 × 888,5, satır 128 → 124, ters tavanda 126 → 122 (kesik son panoların
    satırları tam boy satırına katıldı); veranda kirişleri ve yavru makaslar aynı. Taşan verandaya bakan gövde duvarı ana çatının
    kenarındadır, "çatı kenarına gelmeyen dış duvar"a girmez (D-32 madde 2, Lokman 29 Ekim 13:12: 6,47 → 0)."""
    N = PL.model_motor(_ie())
    assert (N["W"], N["D"], N["brut_m2"]) == (898.5, 1199.5, 90.211)       # brüt gövde + veranda; dış kutunun boş köşeleri sayılmaz
    assert N["dis_cevre_m"] == pytest.approx(35.74) and N["ic_kalan_dis_duvar_m"] == 0.0 and N["dikmeler"] == 4
    assert N["veranda_kenarlari_cm"] == [386.0, 181.0, 181.0, 261.0, 130.0, 130.0] and N["veranda_dis_kenar_sira"] == [0, 3]
    ana, on, arka = N["cati"]
    assert (ana["aciklik_cm"], ana["boy_cm"], ana["makas_kosu_cm"]) == (898.5, 888.5, 868.5)
    assert {k: on[k] for k in ("ad", "tip", "aciklik_cm", "boy_cm", "kalkan", "capraz", "acik", "mahya_boy_cm", "sacak_hatlari_m", "makas_kosu_cm")} == \
        {"ad": "ön veranda çatısı", "tip": "besik", "aciklik_cm": 386.0, "boy_cm": 181.0, "kalkan": 1, "capraz": False, "acik": True,
         "mahya_boy_cm": 211.0, "sacak_hatlari_m": [2.11, 2.11], "makas_kosu_cm": 161.0}
    assert (arka["aciklik_cm"], arka["boy_cm"], arka["mahya_boy_cm"]) == (261.0, 130.0, 160.0)
    N["ozellikler"] = {"Çatı Şekli": "Beşik", "Çatı Kaplaması": "Tek Kat Panel", "Çatı Kaplama Rengi": "Antrasit", "Tavan": "Asma"}
    L = PL.liste(N)
    sat = lambda kalem: [(s["olcu"], s["adet"]) for s in L["satirlar"] if s["kalem"] == kalem]
    assert sat("Özel kutu profil (kolon) 100 × 100") == [("L 2500", 4)]
    assert sat("Kutu profil (kiriş) 100 × 100") == [(f"L {x}", 1) for x in (3860, 1710, 1710, 2610, 1200, 1200)]
    formul = [s["formul"] for s in L["satirlar"] if s["kalem"] == "Kutu profil (kiriş) 100 × 100"]
    assert [f.startswith("taşan verandanın dış kenarı") for f in formul] == [True, False, False, True, False, False]
    assert sat("Yavru makas · ön veranda çatısı") == [("L 4460", 3)] and sat("Yavru makas · arka veranda çatısı") == [("L 3210", 2)]
    assert sat("Metal dere") == [("L 4000", 7)]
    assert L["ozet"]["satir"] == 124
    N["ozellikler"]["Tavan"] = "Ters"
    assert PL.liste(N)["ozet"]["satir"] == 122


def test_verandasiz_ayni():
    """`verandalar` yoksa yeni yol hiç çalışmaz: gövde kutusu dış ölçüyle aynı, listede tek çatı, brüt dış dikdörtgen."""
    ie = _oku(PK01)
    p = G.kur(json.loads(json.dumps(ie)))
    assert p.dis_verandalar == [] and G.govde_kutusu(p) == sunum.sinirlar(p)
    N = PL.model_motor(ie)
    assert len(N["cati"]) == 1 and N["brut_m2"] == round(N["W"] * N["D"] / 1e4, 3)
    assert "dis_verandalar" not in __import__("motor.ifc_uret", fromlist=["hazirla"]).hazirla(ie)


@pytest.mark.parametrize("v, hata", [
    ({"ad": "V", "cephe": "kuzey", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": 150}, "cephesi bilinmiyor"),
    ({"ad": "V", "cephe": "on", "bas_cm": 800, "bit_cm": 1000, "derinlik_cm": 150}, "tam oturmuyor"),
    ({"ad": "V", "cephe": "on", "bas_cm": 0, "bit_cm": 30, "derinlik_cm": 150}, "çok dar"),
    ({"ad": "V", "cephe": "on", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": "derin"}, "sayı olmalı"),
    ({"ad": "SALON", "cephe": "on", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": 150}, "aynı"),
    ({"ad": "V", "cephe": "on", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": 150, "tur": "salon"}, "açık mahal değil"),
    ({"ad": "V", "cephe": "on", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": 150, "cati": {"tip": "kirma"}}, "çatı tipi bilinmiyor"),
])
def test_veranda_hatali_girdi(v, hata):
    with pytest.raises(G.IsEmriHatasi, match=hata):
        G.kur(_ie([v]))


def test_veranda_ust_uste_hata():
    v = {"cephe": "on", "bas_cm": 0, "bit_cm": 300, "derinlik_cm": 150}
    with pytest.raises(G.IsEmriHatasi, match="çakışıyor"):
        G.kur(_ie([{"ad": "A", **v}, {"ad": "B", **v, "bas_cm": 200, "bit_cm": 500}]))


def test_veranda_saçak_yuzunde_uyarir_ve_capraz():
    """Ana çatının saçak yüzündeki veranda (sağ cephe; makaslar x'i geçer): çatısı yazılmamışsa beşik ve ana eğim, uyarı; mahyası saçağın
    üstünde kaldığı için dere çizilmez, uyarı; listede çapraz beşik (5.1 deresi), mahya ana çatının yüzüne kadar."""
    p = G.kur(_ie([{"ad": "SAĞ VERANDA", "cephe": "sag", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150}]))
    u = [x for x in p.uyarilar if x.startswith("Veranda")]
    assert len(u) == 2 and "%27,5" in u[0] and "dere" in u[1]
    N = PL.model_motor(_ie([{"ad": "SAĞ VERANDA", "cephe": "sag", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150}]))
    c = N["cati"][1]
    assert c["capraz"] is True and c["aciklik_cm"] == 300.0 and c["mahya_boy_cm"] == pytest.approx(150 + 180 * 0.275 / 0.275)
    assert N["veranda_kenarlari_cm"] == [300.0, 150.0, 150.0]
    tek = PL.model_motor(_ie([{"ad": "SAĞ VERANDA", "cephe": "sag", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150,
                                "cati": {"tip": "tek_yon", "egim_yuzde": 10}}]))["cati"][1]
    assert (tek["tip"], tek["aciklik_cm"], tek["boy_cm"], tek["kalkan"], tek["sacak_hatlari_m"]) == ("tek_yon", 150.0, 300.0, 0, [3.6])


def test_gorunuste_alin_yok_kalkan_cati_cizgisinde(plan):
    """D-31 madde 3 (Lokman, 29 Ekim 2026 11:07–11:09: "saçaklardan yukarı doğru çıkan çizgiler var olmamalı"): beşik verandanın kalkan
    dolgusu (alın) hiçbir görünüşte çizilmez; IFC'deki alın dolgusu aynen (`test_ifc_veranda_catisi`). Önceden bu test alının üst köşelerini
    denetliyordu; aynı nokta artık kalkanın çizgisinde: kolon yüzünde saçak kotu + saçak × eğim (268,25), tepede mahya (321,325)."""
    for taraf in ("on", "arka", "sol", "sag"):
        assert not [x for x in VR.gorunus_parcalari(plan, plan.is_emri, taraf) if x["tur"] == "alin"], taraf
    kal = [x["u"] for x in VR.gorunus_parcalari(plan, plan.is_emri, "on") if x.get("kalkan") and x["veranda"] == "ÖN VERANDA"][0]
    (u0, z0), (um, zm), (u1, z1) = kal
    z = lambda u: z0 + (zm - z0) * (u - u0) / (um - u0) if u <= um else zm + (z1 - zm) * (u - um) / (u1 - um)
    assert (z(256.0), zm, z(642.0)) == (pytest.approx(268.25), pytest.approx(321.325), pytest.approx(268.25))


def test_on_gorunuste_veranda_sacak_ve_topuk(plan, tmp_path):
    """Lokman, 29 Ekim 2026 (TK-02): "Ön Veranda makasındaki saçak çizgisi ile topuk çizgisi çıkmamış". Veranda çatısı görünüşte ana çatı
    gibi çizilir (BK-18 ek): duvar üstünde saçak ucundan saçak ucuna saçak altı çizgisi, iki uçta 10 cm topuk; kalkanın iki ucu topuğun
    üstünde. D-31: beşik de dört görünüşle; burada yalnız ön görünüşün (soldaki ilk görünüş, x ≤ ana saçak ucu) çizgileri; gövde
    898,5 (D-30), ana çatının sağ saçak ucu 928,5."""
    import ezdxf
    p = [x for x in VR.gorunus_parcalari(plan, plan.is_emri, "on") if x["veranda"] == "ÖN VERANDA"]
    assert [x["u"] for x in p if x["tur"] == "sacak"] == [[(226.0, 250.0), (672.0, 250.0)]]
    assert [x["u"] for x in p if x["tur"] == "topuk"] == [[(226.0, 250.0), (226.0, 260.0)], [(672.0, 250.0), (672.0, 260.0)]]
    kalkan = [x["u"] for x in p if x.get("kalkan")][0]
    assert (kalkan[0], kalkan[-1]) == ((226.0, 260.0), (672.0, 260.0))
    m = dxf_out.uret(_ie(), tmp_path, pdf_hatada=False)
    msp = ezdxf.readfile(tmp_path / m["dxf"]).modelspace()
    nokta = lambda e: [(round(q[0], 3), round(q[1], 3)) for q in (e.get_points("xy") if e.dxftype() == "LWPOLYLINE" else (e.dxf.start, e.dxf.end))]
    on = lambda c: all(q[0] <= 928.5 + 1e-6 for q in c)                                         # ön görünüş: ana çatının sağ saçak ucuna kadar
    topuk = sorted(c for e in msp if e.dxf.layer == "ON_TOPUK" for c in [nokta(e)] if on(c))
    assert len(topuk) == 4 and all(a[0] == b[0] and b[1] - a[1] == pytest.approx(10.0) for a, b in topuk)   # ana çatının ve ön verandanın iki ucu
    x0, alt, ust = topuk[0][0][0], topuk[0][0][1], topuk[0][1][1]
    assert [round(t[0][0] - x0, 3) for t in topuk] == [0.0, 256.0, 702.0, 958.5]               # saçak uçları: ana −30 / 928,5, veranda 226 / 672
    assert all(t[0][1] == alt and t[1][1] == ust for t in topuk)                                 # hepsi duvar üstünden saçak kotuna
    cati = [c for e in msp if e.dxf.layer == "ON_CATI" for c in [nokta(e)] if on(c)]
    assert [topuk[1][0], topuk[2][0]] in cati                                                    # verandanın saçak altı çizgisi, uçtan uca
    kal = [c for c in cati if len(c) == 3]
    assert len(kal) == 1 and (kal[0][0], kal[0][-1]) == (topuk[1][1], topuk[2][1])              # kalkan topuğun üstünde


def test_sol_veranda_profil_rolu_ve_aks_payi(tmp_path):
    """Sol verandada dış kenar düşeydir ama ön profildir (rol kenardan); aks tablosu olmayan planda (P6001) aks yazıları taşan verandanın
    dışında (kod incelemesi)."""
    import ezdxf
    ie = _ie([{"ad": "SOL VERANDA", "cephe": "sol", "bas_cm": 100, "bit_cm": 300, "derinlik_cm": 120}])
    m = dxf_out.uret(ie, tmp_path / "sol", pdf_hatada=False)
    assert m["validation_passed"] is True
    bloklar = {b.name for b in ezdxf.readfile(next((tmp_path / "sol").glob("*.dxf"))).blocks if "_VERANDA_" in b.name and "_SOL_" in b.name}
    assert {b.rsplit("_", 1)[1] for b in bloklar} == {"DIS", "YAN1", "YAN2"}
    assert [b for b in bloklar if b.endswith("_DIS")][0].split("_VERANDA_")[1].startswith("ON_2000p0_")
    assert all(b.split("_VERANDA_")[1].startswith("YAN_1200p0_") for b in bloklar if not b.endswith("_DIS"))
    p6001 = _oku(KOK / "is_emri" / "P6001_2plus1_6x6.json")
    p6001["verandalar"] = [{"ad": "ARKA V", "cephe": "arka", "bas_cm": 50, "bit_cm": 350, "derinlik_cm": 150}]
    m = dxf_out.uret(p6001, tmp_path / "p6001", pdf_hatada=False)
    assert m["validation_passed"] is True
    doc = ezdxf.readfile(next((tmp_path / "p6001").glob("*.dxf")))
    harf = [e for e in doc.modelspace().query("TEXT") if e.dxf.layer == "AKS_YAZI" and e.dxf.text == "A"]
    assert harf and all(e.dxf.insert.y >= 763 + 150 + 60 - 1e-6 for e in harf)     # H + veranda + 60; önceden H + 60 (verandanın içi)


def test_varsayilan_cati_uyarisi_adi_bozmaz():
    u = [x for x in G.kur(_ie([{"ad": "E. VERANDA", "cephe": "on", "bas_cm": 0, "bit_cm": 200, "derinlik_cm": 150}])).uyarilar if x.startswith("Veranda")]
    assert u[0].startswith("Veranda E. VERANDA: çatısı İş Emri'nde yok") and "%27,5" in u[0]


def test_kalkan_yaninda_cati_tasmasi_uyarir(plan):
    """Kalkan yanındaki veranda çatısı ana çatının saçağının üstüne çıkarsa uyarı (K16). TK-01'in kendi çatıları altında: ön 70 cm aşağıda,
    arkanın sol yüzü ana çatının sol yüzüyle aynı düzlemde (0)."""
    assert [round(VR.ana_catiya_tasma(plan, plan.is_emri, v), 1) for v in plan.dis_verandalar] == [-70.4, 0.0]
    for cati, cm in (({"tip": "tek_yon", "egim_yuzde": 27.5}, "44"), ({"tip": "besik", "egim_yuzde": 40}, "20")):
        ie = _ie(); ie["verandalar"][1]["cati"] = cati
        u = [x for x in G.kur(ie).uyarilar if x.startswith("Veranda")]
        assert len(u) == 1 and "ARKA VERANDA" in u[0] and f"yüzünü {cm} cm aşıyor" in u[0], u


def test_capraz_besik_farkli_sacak():
    """Saçak yüzündeki beşikte saçak hattı dış kenardan ana çatının saçak hattına, mahya ana çatının yüzüne: veranda saçağı 50, ana 30."""
    v = {"ad": "SAĞ VERANDA", "cephe": "sag", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150, "cati": {"tip": "besik", "egim_yuzde": 27.5, "sacak_cm": 50}}
    c = PL.model_motor(_ie([v]))["cati"][1]
    assert c["capraz"] is True and c["sacak_hatlari_m"] == [1.7, 1.7] and c["mahya_boy_cm"] == pytest.approx(150 + 20 + 200)


def test_ayna_verandayi_cevirir():
    """Varyant aynası (`beyin.varyant.ayna`, pano birimli İş Emri) verandayı da çevirir: cephe ve cephe boyunca konum. P6001 (773 × 763)."""
    from beyin import varyant
    p6001 = _oku(KOK / "is_emri" / "P6001_2plus1_6x6.json")
    for v, x, y in (({"ad": "ARKA V", "cephe": "arka", "bas_cm": 50, "bit_cm": 350, "derinlik_cm": 150},
                     (423.0, 763.0, 723.0, 913.0), (50.0, -150.0, 350.0, 0.0)),
                    ({"ad": "SOL V", "cephe": "sol", "bas_cm": 300, "bit_cm": 500, "derinlik_cm": 120},
                     (773.0, 300.0, 893.0, 500.0), (-120.0, 263.0, 0.0, 463.0))):
        ie = json.loads(json.dumps(p6001)); ie["verandalar"] = [v]
        assert G.kur(varyant.ayna(ie, "x")).dis_verandalar[0]["rect"] == x
        assert G.kur(varyant.ayna(ie, "y")).dis_verandalar[0]["rect"] == y
    # ayak izi simetrik değil (ızgara içi veranda sağ kenarı boydan boya kaplar): konum planın ölçüsüne göre, ayak izine göre değil (hakem 2. tur)
    yan = _oku(KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json")
    for m in yan["mahaller"]:
        m["konum_pano"] = {"VERANDA": [[5, 0, 6, 8.5]], "SALON": [[2.5, 4, 5, 8.5]]}.get(m["ad"], m["konum_pano"])
    yan["verandalar"] = [{"ad": "ARKA V", "cephe": "arka", "bas_cm": 100, "bit_cm": 400, "derinlik_cm": 150}]
    assert G.kur(varyant.ayna(yan, "x")).dis_verandalar[0]["rect"] == (373.0, 1076.75, 673.0, 1226.75)   # W 773: sağdan 100 içeride


def test_bayi_plan_gorseli_verandayi_kirpmaz(tmp_path):
    """Canlı yolun plan görseli (`bayi_gorseli.plan_gorseli`) çerçeveyi taşan verandayla genişletir (geometri hakemi: ön veranda
    kırpılıyordu); veranda yoksa çerçeve gövde ± 120, eskisi gibi."""
    from PIL import Image
    from motor import bayi_gorseli
    yol = bayi_gorseli.plan_gorseli(_ie(), tmp_path / "tk01.png")
    w, h = Image.open(yol).size
    assert w == 1400 and h == pytest.approx(1400 * (1199.5 + 2 * 120 + 90) / (898.5 + 2 * 120), abs=1)     # D-30: 898,5 × 1199,5


def test_bayi_paftasi_verandali(tmp_path):
    import pymupdf
    ie = _ie()
    o = sunum.bayi_paftasi(ie, tmp_path, perspektif=False, bilgi={"tarih": "27.10.2026"})
    assert o["teslim"] is True
    with pymupdf.open(tmp_path / "TK01_bayi.pdf") as d:
        metin = " ".join(w[4] for w in d[0].get_text("words"))
    for s in ("ÖN VERANDA", "ARKA VERANDA", "ÇATI PLANI", "386", "181", "130", "1199"):
        assert s in metin, s
    oz = _oku(tmp_path / "TK01_bayi_ozet.json")
    assert oz["sayimlar"]["dikme"] == 4 and oz["sayimlar"]["oturum_m2"] == pytest.approx(90.21)            # D-30


def test_ifc_veranda_catisi(tmp_path):
    from motor import ifc_uret
    g = ifc_uret.hazirla(_ie())
    assert [v["ad"] for v in g["dis_verandalar"]] == ["ÖN VERANDA", "ARKA VERANDA"]
    oz = ifc_uret.uret(_ie(), tmp_path / "tk01.ifc")
    assert oz["sema_hatasi"] == 0
    import ifcopenshell
    f = ifcopenshell.open(str(tmp_path / "tk01.ifc"))
    adlar = {e.Name for e in f.by_type("IfcRoof")} | {e.Name for e in f.by_type("IfcSlab")} | {e.Name for e in f.by_type("IfcPlate")}
    for ad in ("VERANDA_CATISI_1", "VERANDA_CATISI_2", "VERANDA_ZEMINI_1", "VERANDA_CATI_1_1", "VERANDA_CATI_1_2", "VERANDA_ALIN_1"):
        assert ad in adlar, ad
    mekan = {e.Name: e.LongName for e in f.by_type("IfcSpace")}
    assert mekan.get("M-VERANDA-1") == "ÖN VERANDA" and mekan.get("M-VERANDA-2") == "ARKA VERANDA" and "M-VERANDA" not in mekan
