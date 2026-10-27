"""BK-15 · yeni planın revizyonunda oda ekleme (`plan_islem` `oda_ekle`): yalnız ebeveyn banyosu, yatak odasının köşesinden; sığmazsa oda
bir kenarından büyütülür (ev en az büyüyen yönde). Öteki oda istekleri gerekçesiyle "uygulanamadı". LLM çağrısı yok: `manuel` arka uç
kayıtlı işlem listesini oynatır.

Örnekler (`testler/plan/ornekler/`): `rehber_3arti1_90` bayi rehberindeki konuşmanın ilk planı ("Tek kat çelik, 3+1, 90 m² civarı", kırma;
`plan_uretici.uret`'in birinci adayı, 27.10.2026); `buyume_2arti1_70` banyonun odaya sığmadığı plan (70 m² 2+1 beşik, birinci aday);
`veranda_on_3arti1` ön şeridi veranda olan, elle kurulmuş 3+1 (geometri hakemi, ikinci tur).

Yatak odasının gövdesi (`govde_gercek`) kodun tahmininden değil, motorun net bölgesinden ölçülür (denetçinin kullandığı yapı).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from shapely.geometry import LineString

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from beyin import plan_islem as PI  # noqa: E402
from beyin.plan_denetim import denetle  # noqa: E402

ORNEK = KOK / "testler" / "plan" / "ornekler"
P3 = {"oda_programi": "3+1"}


def ornek(ad):
    return json.loads((ORNEK / f"{ad}.json").read_text(encoding="utf-8"))


def ekle(**k) -> dict:
    return {"islemler": [{"op": "oda_ekle", "alinti": k.pop("alinti", "Ebeveyn banyosu ekleyelim"), **k}], "uygulanamayan": []}


def mahal(p, ad):
    return next((m for m in p["mahaller"] if m["ad"] == ad), None)


def govde_gercek(p, ad) -> float:
    """Mahalin gövdesi motorun net bölgesinden: net çokgenin içine sığan eksene paralel dikdörtgenlerden kısa kenarı en büyük olanın kısa
    kenarı (köşeler çokgenin köşe çizgilerinde). Plan denetçiden geçmeli (yapı onun tanımından kurulur)."""
    from itertools import combinations
    from shapely.geometry import box
    from beyin.varyant import _kur
    d = denetle(p)
    assert d["gecerli"], d["ihlaller"]
    net = _kur(d["tanim"])["bolgeler"][ad]["net"].buffer(0)
    koseler = [c for g in getattr(net, "geoms", [net]) for c in g.exterior.coords]
    xs, ys = sorted({round(c[0], 3) for c in koseler}), sorted({round(c[1], 3) for c in koseler})
    return max((min(x1 - x0, y1 - y0) for x0, x1 in combinations(xs, 2) for y0, y1 in combinations(ys, 2)
                if net.buffer(0.01).contains(box(x0, y0, x1, y1))), default=0.0)


def test_hedef_ornek_rehberdeki_konusma():
    """Rehber Bölüm 3: "Ebeveyn banyosu ekleyelim" → R2. Yatak Odası 3 (345 × 495) köşesine banyo kesilince odanın gövdesi 3 m'nin altına
    iner; oda ön (giriş) cephesinden 100 cm büyütülür (salon-mutfak da öne uzar) (ev en az büyüyen yönde, O2 (a)) ve banyo var olan banyonun yanına (ıslak hacimler yan yana)
    kesilir; vasistası yan cephede (giriş cephesinde değil), kapısı odadan; odanın penceresi yerinde. Ev büyüdüğü açıkça yazılır (CIO 27.10)."""
    p = ornek("rehber_3arti1_90")
    assert PI._banyo_kes(p, "Yatak Odası 3", "Ebeveyn Banyo") is None             # odaya sığmıyor (gövde kuralı)
    s = PI.duzenle(p, "Ebeveyn banyosu ekleyelim", P3, hazir=ekle(islev="ebeveyn_banyosu"))
    assert s["durum"] == "gecerli" and s["cagri"] == 0 and not s["uygulanamayan"]
    assert s["fark"] == ["dış ölçü 800×1125 → 800×1225 cm", "ebeveyn banyosu için ev 100 cm büyüdü (boy 1125 → 1225 cm)",
                         "Salon - Mutfak 28,2 → 32,7 m²", "Yatak Odası 3 17,1 → 16,1 m²", "Ebeveyn Banyo eklendi (4,4 m²)",
                         "pencere eklendi: Ebeveyn Banyo sağ 60/40", "kapı eklendi: Ebeveyn Banyo – Yatak Odası 3"]
    q = s["plan"]
    assert mahal(q, "Ebeveyn Banyo") == {"ad": "Ebeveyn Banyo", "islev": "banyo", "dikdortgenler": [[585, 390, 800, 595]]}
    assert mahal(q, "Yatak Odası 3")["dikdortgenler"] == [[455, 0, 800, 390], [455, 390, 585, 595]]
    assert mahal(q, "Banyo")["dikdortgenler"] == [[585, 595, 800, 805]]                  # yeni banyo y = 595'te var olan banyoya bitişik
    assert govde_gercek(q, "Yatak Odası 3") >= 300
    assert {"arasinda": ["Yatak Odası 3", "Ebeveyn Banyo"]} in q["kapilar"]
    assert {"mahal": "Ebeveyn Banyo", "cephe": "D", "olcu": "60x40", "adet": 1} in q["pencereler"]
    # var olan kapılar ve pencereler aynen; öteki yatak odaları yalnız kayar (ölçüleri aynı)
    assert all(k in q["kapilar"] for k in p["kapilar"]) and all(x in q["pencereler"] for x in p["pencereler"])
    for ad in ("Yatak Odası 1", "Yatak Odası 2", "Banyo", "Hol"):
        assert [(r[2] - r[0], r[3] - r[1]) for r in mahal(q, ad)["dikdortgenler"]] == \
            [(r[2] - r[0], r[3] - r[1]) for r in mahal(p, ad)["dikdortgenler"]], ad
    # denetçi: oda en küçükleri (net), program, erişim; ebeveyn banyosu yatak odasından (ikinci banyo; ortak banyo holden kalıyor)
    d = denetle(q, P3)
    assert d["gecerli"] and d["ozet"]["banyo"] == 2 and d["ozet"]["yatak"] == 3
    assert d["ozet"]["odalar_m2"]["Yatak Odası 3"] >= 10.5 and d["ozet"]["odalar_m2"]["Ebeveyn Banyo"] >= 3.8
    assert s["tanim"] is not None and PI._ortak_banyo(q)


def test_bayinin_soyledigi_yatak_odasi():
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=ekle(islev="banyo", mahal="Yatak Odası 1"))
    assert s["durum"] == "gecerli"
    assert s["fark"] == ["dış ölçü 800×1125 → 800×1225 cm", "ebeveyn banyosu için ev 100 cm büyüdü (boy 1125 → 1225 cm)",
                         "Yatak Odası 1 16,8 → 16,4 m²", "Yatak Odası 2 16,8 → 20,8 m²", "Ebeveyn Banyo eklendi (4,4 m²)",
                         "pencere eklendi: Ebeveyn Banyo sol 60/40", "kapı eklendi: Ebeveyn Banyo – Yatak Odası 1"]
    assert mahal(s["plan"], "Yatak Odası 3") == mahal(ornek("rehber_3arti1_90"), "Yatak Odası 3")
    assert govde_gercek(s["plan"], "Yatak Odası 1") >= 300


def test_ikinci_ebeveyn_banyosu_ayri_adla():
    h = {"islemler": [{"op": "oda_ekle", "islev": "ebeveyn_banyosu", "alinti": "Ebeveyn banyosu ekleyelim"},
                      {"op": "oda_ekle", "islev": "banyo", "mahal": "Yatak Odası 1", "alinti": "1. yatak odasına da banyo"}], "uygulanamayan": []}
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=h)
    assert s["durum"] == "gecerli"
    assert mahal(s["plan"], "Ebeveyn Banyo 2") and {"arasinda": ["Yatak Odası 1", "Ebeveyn Banyo 2"]} in s["plan"]["kapilar"]
    assert s["fark"][:3] == ["dış ölçü 800×1125 → 800×1325 cm", "ebeveyn banyosu için ev 100 cm büyüdü (boy 1125 → 1225 cm)",
                             "ebeveyn banyosu için ev 100 cm büyüdü (boy 1225 → 1325 cm)"]


def test_sigmayan_odada_ev_en_az_buyuyen_yonde_buyur():
    """O2 (a), CIO onayı 27.10: oda köşesine banyo sığmıyor (oda 10,5 m²'nin altına ya da gövdesi 3 m'nin altına düşer) → oda bir
    kenarından büyütülür; yeni dış ölçü ve büyümenin nedeni bayiye yazılır."""
    p = ornek("buyume_2arti1_70")
    assert PI._banyo_kes(p, "Yatak Odası 1", "Ebeveyn Banyo") is None
    s = PI.duzenle(p, "x", {"oda_programi": "2+1"}, hazir=ekle(islev="ebeveyn_banyosu"))
    assert s["durum"] == "gecerli"
    assert s["fark"] == ["dış ölçü 700×1000 → 700×1200 cm", "ebeveyn banyosu için ev 200 cm büyüdü (boy 1000 → 1200 cm)",
                         "Yatak Odası 1 11,9 → 14,5 m²", "Yatak Odası 2 11,9 → 18,9 m²", "Ebeveyn Banyo eklendi (4,4 m²)",
                         "pencere eklendi: Ebeveyn Banyo sol 60/40", "kapı eklendi: Ebeveyn Banyo – Yatak Odası 1"]
    assert denetle(s["plan"], {"oda_programi": "2+1"})["gecerli"] and govde_gercek(s["plan"], "Yatak Odası 1") >= 300
    # en az büyüme: daha küçük bir büyümeyle (her yön, 100–250 cm) denetçiden geçen yerleşim yok
    brut = lambda x: x["dis_olcu"]["en"] * x["dis_olcu"]["boy"]       # noqa: E731
    secilen = brut(s["plan"]) - brut(p)
    for yon, cm in PI.BUYUME:
        g, _ = PI._oda_kenari(p, "Yatak Odası 1", yon, cm)
        if g is not None and brut(g) - brut(p) < secilen:
            assert PI._banyo_kes(g, "Yatak Odası 1", "Ebeveyn Banyo") is None, (yon, cm)


def test_l_odanin_govdesi_dar_kenar_kuralina_uyar():
    """Geometri hakemi 27.10, bulgu 1: denetçi dar kenarı sınır kutusundan ölçer; kesme sonrası L odanın gövdesi (en büyük iç dikdörtgeni)
    3 m'nin altına inen aday alınmaz. Rehber planında Yatak Odası 1'e (400 × 420) köşeden banyo: gövde 400 × 200 kalırdı."""
    p = ornek("rehber_3arti1_90")
    assert PI._banyo_kes(p, "Yatak Odası 1", "Ebeveyn Banyo") is None
    for ad in ("Yatak Odası 1", "Yatak Odası 3"):
        g, _ = PI._oda_kenari(p, ad, "G" if ad == "Yatak Odası 3" else "K", 100)
        q = PI._banyo_kes(g, ad, "Ebeveyn Banyo")
        assert q is not None and govde_gercek(q, ad) >= 300, ad


def test_ortak_banyo_korunur():
    """Geometri hakemi 27.10, bulgu 2: denetçi "banyo yatak odasından geçmez" kuralını yalnız tek banyoda arar. Ebeveyn banyosuyla iki
    banyo olunca ortak banyonun holden kapısı kaldırılıp yatak odasına alınırsa banyolara yalnız yatak odasından ulaşılırdı: o işlem
    gerekçesiyle düşer, öteki işlemler uygulanır."""
    h = {"islemler": [{"op": "oda_ekle", "islev": "ebeveyn_banyosu", "alinti": "ebeveyn banyosu"},
                      {"op": "kapi_kaldir", "mahal": "Hol", "mahal_b": "Banyo", "alinti": "banyo kapısını kaldır"},
                      {"op": "kapi_ekle", "mahal": "Banyo", "mahal_b": "Yatak Odası 2", "alinti": "banyoya yatak odasından gir"}],
         "uygulanamayan": []}
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=h)
    assert s["durum"] == "gecerli" and PI._ortak_banyo(s["plan"])
    assert s["uygulanamayan"] == ["banyo kapısını kaldır: ortak banyo kalmıyor: banyolardan birine yatak odasından…"]
    assert {"arasinda": ["Hol", "Banyo"]} in s["plan"]["kapilar"] and mahal(s["plan"], "Ebeveyn Banyo")
    # ortak banyosu olmayan plan (yalnız yatak odasından açılan banyo) bu ölçütle reddedilmez: kural yalnız revizyonda kaybı önler
    p = ornek("rehber_3arti1_90")
    p["kapilar"] = [k for k in p["kapilar"] if k["arasinda"] != ["Hol", "Banyo"]] + [{"arasinda": ["Yatak Odası 2", "Banyo"]}]
    assert not PI._ortak_banyo(p)
    assert PI._denetle(p, P3, "YENI", p)["ihlaller"] != [PI.ORTAK_BANYO]


def test_duzenlenen_oda_farkta_yazilir():
    """Geometri hakemi 27.10, bulgu 3: büyütmede duvarı kayıp L olan oda alanı 0,25 m²'den az değişse de bayiye yazılır; yalnız kayan oda
    (ölçüleri aynı) yazılmaz."""
    eski = {"dis_olcu": {"en": 800, "boy": 600}, "mahaller": [
        {"ad": "Salon", "islev": "salon", "dikdortgenler": [[0, 0, 455, 600]]},
        {"ad": "Yatak Odası 1", "islev": "yatak_odasi", "dikdortgenler": [[455, 0, 800, 420]]},
        {"ad": "Hol", "islev": "hol", "dikdortgenler": [[455, 420, 800, 600]]}]}
    yeni = {"dis_olcu": {"en": 800, "boy": 700}, "mahaller": [
        {"ad": "Salon", "islev": "salon", "dikdortgenler": [[0, 0, 455, 700]]},
        {"ad": "Yatak Odası 1", "islev": "yatak_odasi", "dikdortgenler": [[455, 0, 800, 300], [455, 300, 595, 520]]},
        {"ad": "Hol", "islev": "hol", "dikdortgenler": [[455, 520, 800, 700]]},
        {"ad": "Ebeveyn Banyo", "islev": "banyo", "dikdortgenler": [[595, 300, 800, 520]]}]}
    fark = ["dış ölçü 800×600 → 800×700 cm", "Salon 27,3 → 31,9 m²", "Ebeveyn Banyo eklendi (4,5 m²)", "kapı eklendi: Ebeveyn Banyo – Yatak Odası 1"]
    assert PI._duzenlenen_odalar(eski, yeni, fark, [("boy", 600, 700)]) == [
        "dış ölçü 800×600 → 800×700 cm", "ebeveyn banyosu için ev 100 cm büyüdü (boy 600 → 700 cm)", "Salon 27,3 → 31,9 m²",
        "Ebeveyn Banyo eklendi (4,5 m²)", "Yatak Odası 1 yeniden düzenlendi (13,4 m²)", "kapı eklendi: Ebeveyn Banyo – Yatak Odası 1"]


def test_belirlenimci():
    a = PI.duzenle(ornek("buyume_2arti1_70"), "x", {"oda_programi": "2+1"}, hazir=ekle(islev="ebeveyn_banyosu"))
    b = PI.duzenle(ornek("buyume_2arti1_70"), "x", {"oda_programi": "2+1"}, hazir=ekle(islev="ebeveyn_banyosu"))
    assert json.dumps(a["plan"], sort_keys=True) == json.dumps(b["plan"], sort_keys=True) and a["fark"] == b["fark"]


@pytest.mark.parametrize("islem, gerekce", [
    ({"islev": "yatak_odasi", "alinti": "Bir yatak odası daha ekleyelim"},
     "Bir yatak odası daha ekleyelim: yatak odası ekleme otomatik yapılamıyor (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"),
    ({"islev": "mutfak", "alinti": "ayrı mutfak olsun"},
     "ayrı mutfak olsun: mutfak ekleme otomatik yapılamıyor (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"),
    ({"islev": "depo", "alinti": "kiler ekleyelim"},
     "kiler ekleyelim: depo ekleme otomatik yapılamıyor (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"),
    ({"islev": "banyo", "mahal": "Hol", "alinti": "holden ikinci banyo"},
     "holden ikinci banyo: banyo yalnız bir yatak odasının içinden eklenebiliyor (Hol yatak odası değil)"),
    ({"islev": "banyo", "mahal": "Çocuk Odası", "alinti": "çocuk odasına banyo"}, "çocuk odasına banyo: 'Çocuk Odası' adlı mahal yok"),
    ({"alinti": "bir oda daha"}, "bir oda daha: yeni oda ekleme otomatik yapılamıyor (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"),
])
def test_baska_oda_uygulanamaz_plan_aynen(islem, gerekce):
    """O3: yatak odası, mutfak, kiler, ortak banyo eklenmez; istek bayinin sözü ve gerekçesiyle, plan aynen geçerli."""
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=ekle(**islem))
    assert s["durum"] == "uygulanamadi" and s["plan"] is None and s["uygulanamayan"] == [gerekce]


def test_oda_ekleme_oteki_islemlerle_birlikte():
    h = {"islemler": [{"op": "oda_ekle", "islev": "ebeveyn_banyosu", "alinti": "Ebeveyn banyosu ekleyelim"},
                      {"op": "pencere_ekle", "mahal": "Yatak Odası 1", "cephe": "K", "olcu": "120x120", "alinti": "b"},
                      {"op": "oda_ekle", "islev": "yatak_odasi", "alinti": "bir yatak odası daha"}], "uygulanamayan": []}
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=h)
    assert s["durum"] == "gecerli" and "Ebeveyn Banyo eklendi (4,4 m²)" in s["fark"] and "pencere eklendi: Yatak Odası 1 arka 120/120" in s["fark"]
    assert len(s["uygulanamayan"]) == 1 and s["uygulanamayan"][0].startswith("bir yatak odası daha: yatak odası ekleme")


def test_yatak_odasi_yoksa_gerekceli():
    p = ornek("rehber_3arti1_90")
    for m in p["mahaller"]:
        if m["islev"] == "yatak_odasi":
            m["islev"] = "depo"
    q, olmayan = PI.uygula(p, ekle(islev="ebeveyn_banyosu")["islemler"])
    assert q == p and olmayan == ["Ebeveyn banyosu ekleyelim: planda yatak odası yok"]


def test_islem_semasi_ve_istem():
    """LLM'e giden araç şeması `oda_ekle`'yi ve işlevleri tanır; istem yalnız ebeveyn banyosunun uygulandığını söyler, koordinat istemez."""
    sema = PI.IslemListesi.model_json_schema()
    islem = sema["$defs"]["Islem"]["properties"]
    assert "oda_ekle" in islem["op"]["enum"]
    assert all(i in json.dumps(islem["islev"]) for i in ("ebeveyn_banyosu", "banyo", "yatak_odasi"))
    assert "oda_ekle (islev, mahal)" in PI.PROMPT and "ebeveyn banyosu (yatak odasının içinden açılan banyo) için islev ebeveyn_banyosu" in PI.PROMPT
    assert "yeri söylenmemiş ikinci banyo için\n  islev banyo" in PI.PROMPT
    assert PI.Islem.model_validate({"op": "oda_ekle", "islev": "ebeveyn_banyosu"}).islev == "ebeveyn_banyosu"


def test_once_sonra_gorselinde_mahal_yazisi_odaya_sigar(tmp_path, monkeypatch):
    """Bayiye giden önce–sonra görselinde (r02 başlığı) her mahalin adı ve m² yazısı mahalin içinde kalır: 2 m'lik ebeveyn banyosunda
    "EBEVEYN BANYO" bayi plan görselindeki gibi küçülür (`bayi_gorseli.dar_mahal_yazisi`; önceden önce–sonra panelinde duvarı aşıyordu)."""
    import matplotlib.figure as MF
    from motor.genel import okuma_gorseli as OG
    once = denetle(ornek("rehber_3arti1_90"), P3)
    s = PI.duzenle(ornek("rehber_3arti1_90"), "Ebeveyn banyosu ekleyelim", P3, hazir=ekle(islev="ebeveyn_banyosu"))
    _, y1 = OG._kur(s["tanim"], None, None)
    tasan, eski = [], MF.Figure.savefig

    def yakala(self, *a, **k):
        if Path(str(a[0])).name.endswith("_once_sonra_ust.png"):
            self.canvas.draw(); r = self.canvas.get_renderer(); ax = self.axes[1]; inv = ax.transData.inverted()
            for b in y1["bolgeler"].values():
                if b["sinif"] == "dis":
                    continue
                for t in (t for t in ax.texts if t.get_gid() == f"mahal:{b['ad']}"):
                    bb = t.get_window_extent(r)
                    (x0, _), (x1, _) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
                    _, py = t.get_position()
                    if not b["net"].buffer(0.5).contains(LineString([(x0, py), (x1, py)])):
                        tasan.append((b["ad"], t.get_text(), round(x0), round(x1)))
        return eski(self, *a, **k)
    monkeypatch.setattr(MF.Figure, "savefig", yakala)
    OG.once_sonra(once["tanim"], s["tanim"], tmp_path, "YENI", [], 1, 2, perspektif=False, baslik="r02")
    assert tasan == []
    assert any(b["ad"] == "Ebeveyn Banyo" for b in y1["bolgeler"].values())


def test_sonraki_islem_l_odanin_govdesini_daraltamaz():
    """Geometri hakemi ikinci tur, B1: banyo kesildikten sonra gelen işlem (ön şeridi kısaltan `oda_kucult`) L odanın gövdesini 300'ün
    altına indiremez; denetçi sınır kutusundan ölçtüğü için görmüyordu. İşlem gerekçesiyle düşer, banyo kalır; sonraki revizyonda da aynı."""
    kucult = lambda ad: {"op": "oda_kucult", "mahal": ad, "yon": "G", "cm": 100, "alinti": f"{ad} önden 1 m kısalsın"}     # noqa: E731
    for ad in ("Yatak Odası 3", "Salon - Mutfak"):
        s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir={"islemler": [ekle(islev="ebeveyn_banyosu")["islemler"][0], kucult(ad)], "uygulanamayan": []})
        assert s["durum"] == "gecerli" and mahal(s["plan"], "Ebeveyn Banyo") and s["plan"]["dis_olcu"] == {"en": 800, "boy": 1225}
        [u] = s["uygulanamayan"]
        assert u == f"{ad} önden 1 m kısalsın: Yatak Odası 3 gövdesi 274 cm, en az 300 cm", u
        assert govde_gercek(s["plan"], "Yatak Odası 3") >= 300
    r2 = s["plan"]
    s = PI.duzenle(r2, "x", P3, hazir={"islemler": [kucult("Yatak Odası 3")], "uygulanamayan": []})
    assert s["durum"] == "uygulanamadi" and s["plan"] is None and s["uygulanamayan"] == ["Yatak Odası 3 önden 1 m kısalsın: Yatak Odası 3 gövdesi 274 cm, en az 300 cm"]
    assert PI._dar_govdeler(r2, r2) == [] and PI._govde(r2, "Yatak Odası 3") == govde_gercek(r2, "Yatak Odası 3")


@pytest.mark.parametrize("karkas", [80, 140])
def test_verandaya_bakan_yuz_dis_duvar(karkas):
    """Geometri hakemi ikinci tur, B2: verandaya bakan yüz dış duvardır (net payı 80'likte 10,5, 140'lıkta 16,5 cm); iç sayılınca gövde
    5–11 cm fazla çıkıyor, net 293–299 cm'lik L oda geçiyordu. Kodun gövde ölçüsü motorun net bölgesiyle aynı."""
    p = ornek("veranda_on_3arti1")
    if karkas == 140:
        p["dis_karkas"] = 140
    s = PI.duzenle(p, "x", P3, hazir=ekle(islev="banyo", mahal="Yatak Odası 1"))
    assert s["durum"] == "gecerli" and mahal(s["plan"], "Ebeveyn Banyo")
    g = govde_gercek(s["plan"], "Yatak Odası 1")
    assert g >= 300 and PI._govde(s["plan"], "Yatak Odası 1") == pytest.approx(g)
    assert mahal(s["plan"], "Veranda") == mahal(p, "Veranda")


def test_buyume_satiri_son_plana_gore():
    """Geometri hakemi ikinci tur, B3: "ev büyüdü" satırı son plandaki dış ölçüye göre yazılır. Sonraki işlem büyümeyi geri alırsa (arka
    odalar 1 m kısalır, ev yine 800 × 1125) bayiye "ev büyüdü" gitmez."""
    h = {"islemler": [ekle(islev="ebeveyn_banyosu")["islemler"][0],
                      {"op": "oda_kucult", "mahal": "Yatak Odası 1", "yon": "K", "cm": 100, "alinti": "arka odalar 1 m kısalsın"}], "uygulanamayan": []}
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=h)
    assert s["durum"] == "gecerli" and s["plan"]["dis_olcu"] == {"en": 800, "boy": 1125} and mahal(s["plan"], "Ebeveyn Banyo")
    assert not any(f.startswith("dış ölçü") or "büyüdü" in f for f in s["fark"])
    assert "Ebeveyn Banyo eklendi (4,4 m²)" in s["fark"] and "Yatak Odası 1 16,8 → 12,8 m²" in s["fark"]
    e, y = {"dis_olcu": {"en": 800, "boy": 1125}, "mahaller": []}, {"dis_olcu": {"en": 800, "boy": 1175}, "mahaller": []}
    assert PI._duzenlenen_odalar(e, y, [], [("boy", 1125, 1225)]) == []                       # 100 büyüdü, 50 geri alındı: satır yok
    assert PI._duzenlenen_odalar(e, y, [], [("boy", 1125, 1175)]) == ["ebeveyn banyosu için ev 50 cm büyüdü (boy 1125 → 1175 cm)"]


@pytest.mark.parametrize("alinti", ["Bir banyo daha ekleyelim", "İkinci banyo olsun, oda sayısı aynı kalsın", ""])
def test_yeri_soylenmemis_banyo_ebeveyn_sanilmaz(alinti):
    """Geometri hakemi ikinci ve üçüncü tur: yeri söylenmemiş ikinci banyo (islev `banyo`, mahal yok) ortak banyo olabilir; kod ebeveyn
    banyosu eklemez, gerekçesiyle "uygulanamadı" (plan aynen geçerli). Ayrımı LLM'in işlevi yapar; kod bayinin sözünü taramaz."""
    s = PI.duzenle(ornek("rehber_3arti1_90"), "x", P3, hazir=ekle(islev="banyo", alinti=alinti))
    assert s["durum"] == "uygulanamadi" and s["plan"] is None
    assert s["uygulanamayan"] == [f"{alinti or 'oda ekleme'}: banyonun hangi odadan açılacağı belli değil (yalnız yatak odasının içinden ebeveyn banyosu eklenebiliyor)"]


@pytest.mark.parametrize("islem", [{"islev": "ebeveyn_banyosu", "alinti": ""}, {"islev": "ebeveyn_banyosu", "alinti": "ebeveyin banyosu"},
                                   {"islev": "banyo", "mahal": "Yatak Odası 1", "alinti": "yatak odasına banyo"}])
def test_ebeveyn_banyosu_isleviyle_ya_da_yatak_odasiyla(islem):
    """Ebeveyn banyosu işlevi bayinin sözünden bağımsız uygulanır (boş alıntı, yazım hatası); `banyo` da mahal bir yatak odasıysa."""
    s = PI.duzenle(ornek("veranda_on_3arti1"), "x", P3, hazir=ekle(**islem))
    assert s["durum"] == "gecerli" and {"arasinda": ["Yatak Odası 1", "Ebeveyn Banyo"]} in s["plan"]["kapilar"]


def test_kurallara_uymayan_ara_planda_arama_yapilmaz(monkeypatch):
    """Başlangıç planı kurallara uymuyorsa (aynı mesajdaki önceki işlemin ara hâli) hiçbir aday uymaz: arama yapılmaz, tek denetimle
    gerekçeli döner (geometri hakemi ikinci tur: 140'lık duvarla kuralı bozulmuş planda arama bir dakikayı buluyordu)."""
    p = ornek("rehber_3arti1_90")
    p["pencereler"] = [x for x in p["pencereler"] if x["mahal"] != "Banyo"]          # banyonun zorunlu penceresi yok
    sayac = []
    gercek = PI.denetle
    monkeypatch.setattr(PI, "denetle", lambda *a, **k: sayac.append(1) or gercek(*a, **k))
    q, olmayan = PI.uygula(p, ekle(islev="ebeveyn_banyosu")["islemler"])
    assert q == p and olmayan == ["Ebeveyn banyosu ekleyelim: planın bu hâli kurallara uymadığı için banyo eklenemedi"] and len(sayac) == 1
