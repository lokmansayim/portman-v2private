"""İE-12 · Prefabrik bayi paftası (`motor/sunum.py`) ve pano ekleri (H profili; Lokman 13.10.2026 09:39).

- Pano ekleri: PK-01 montaj paftasının H planıyla (sayfa 3, vektörden: `pafta_montaj.json`) sayıca ve yerce.
- Plan çizimi Motor'un geometrisinden: ölçü zincirleri, kapı kanadının menteşe ucu (DXF'teki `mentese_ucu` sözleşmesiyle aynı; hakem Ö4).
- Sayfa: 1 sayfa, beklenen yazılar, perspektif yoksa uyarı, doğrulama geçmezse yalnız `.HATALI.pdf` (K23), çağıranın matplotlib ayarı değişmez.
- Anahtarsız İş Emri'nin IFC'sine pano eki girmez (eski IFC'ler değişmez).
Perspektifler (VTK) burada koşulmaz; elle: `python -m motor.sunum <is_emri> <klasör>` (İE-12 › Kanıt).
"""
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import geometry as G  # noqa: E402
from motor import sunum  # noqa: E402

PK01 = KOK / "testler" / "motor" / "veri" / "PK01.json"
PAFTA = KOK / "testler" / "motor" / "veri" / "PK01_pafta_montaj.json"   # dalda deneme/2026-10-13_pk_01/; BK-12 PR-1 ile taşındı
P6001 = KOK / "is_emri" / "P6001_2plus1_6x6.json"
P6001_AYNA_Y = KOK / "is_emri" / "P6001_ayna_y.json"


def _oku(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pk01():
    return _oku(PK01)


@pytest.fixture(scope="module")
def pk01_dogrulama(pk01):
    return sunum.motor_dogrulamasi(pk01)


def test_pano_ekleri_pafta_h_plani(pk01):
    """Her iki panonun arasında H: PK-01'de 19 dış + 10 iç pano eki, 5 dış + 4 iç üçlü (paftanın H planı). Her pafta işareti bir eke düşer."""
    plan = G.kur(pk01)
    ek = G.pano_ekleri(plan)
    pafta = _oku(PAFTA)["h_plani_s3"]
    assert Counter((k["duvar"], k["cins"]) for k in ek) == Counter((h["duvar"], h["cins"]) for h in pafta)
    for h in pafta:
        x, y = h["xy"]
        en_yakin = min(ek, key=lambda k: (k["x"] - x) ** 2 + (k["y"] - y) ** 2)
        assert (en_yakin["x"] - x) ** 2 + (en_yakin["y"] - y) ** 2 <= 10.0 ** 2, (h, en_yakin)
        assert en_yakin["cins"] == h["cins"] and en_yakin["duvar"] == h["duvar"], (h, en_yakin)


def test_ifc_pano_ekleri_yalniz_yeni_anahtarla(pk01):
    """Anahtarsız İş Emri'nin IFC girdisinde pano eki yok (eski IFC'ler değişmez); PK-01'de 38 şerit, 5 cm, eke ortalı."""
    from motor import ifc_uret
    assert "pano_ekleri" not in ifc_uret.hazirla(_oku(P6001))
    g = ifc_uret.hazirla(pk01)
    assert len(g["pano_ekleri"]) == 38
    assert Counter(b["cins"] for b in g["pano_ekleri"]) == Counter({"pano_eki": 29, "uclu": 9})
    for b in g["pano_ekleri"]:
        x0, y0, x1, y1 = b["rect"]
        assert min(x1 - x0, y1 - y0) == pytest.approx(G.H_PROFIL_GORUNEN_CM)


def test_olcu_zincirleri_pk01(pk01):
    """Dış yüzden zincirler; iç duvarda aks, çevrede olmayan dış duvarda açık alana bakan yüz. Paftanın sunum planıyla aynı uçlar
    (pafta iç duvarı yüzünden ölçüyor: 201,25 ↔ aks 198,25; o fark kuraldır, uyum değil)."""
    z = sunum.zincirler(G.kur(pk01))
    assert z["alt"] == [0.0, 266.0, 386.5, 600.0]
    assert z["ust"] == [0.0, 198.25, 386.5, 600.0]
    assert z["sol"] == [0.0, 618.5, 1000.0]
    assert z["sag"] == [0.0, 200.0, 618.5, 1000.0]


def test_ozellikler_ve_sayimlar(pk01):
    say = sunum.sayimlar(G.kur(pk01))
    assert (say["pano_dis"], say["pano_ic"], say["h_pano_eki"], say["h_uclu"], say["kose"], say["dikme"]) == (30, 20, 29, 9, 7, 1)
    assert say["oturum_m2"] == pytest.approx(60.0) and say["oda_programi"] == "2+1"
    oz, diger = sunum.ozellikler(pk01, say)
    assert oz["Bina Yüksekliği"] == "2500 mm" and oz["Dış Duvarlar"] == "100 mm Pres Panel" and oz["İç Duvarlar"] == "60 mm Pres Panel"
    assert oz["Pencereler"] == "5 adet (3 × 120/120, 2 × 120/180)" and oz["Vasistaslar"] == "1 adet (1 × 60/40)"
    assert oz["İç Kapılar"] == "5 adet (Standart Amerikan)" and oz["Dış Kapı"] == "Alıcıya ait" and oz["Çatı Eğimi"] == "%33"
    assert oz["Köşe ve Söveler"] == "..."                                          # bilinmeyen uydurulmaz (K21)
    assert "Pencere Rengi: Alıcıya ait" in diger


class _KayitEkseni:
    """Matplotlib ekseni yerine: çizgileri ve yamaları kaydeder (kapı kanadının yeri ve yönü için)."""
    def __init__(self):
        self.cizgiler, self.yamalar = [], []

    def plot(self, xs, ys, **kw):
        self.cizgiler.append((tuple(xs), tuple(ys)))

    def add_patch(self, p):
        self.yamalar.append(p)


def test_kapi_kanadi_mentese_ucunda(pk01):
    """Kanat menteşe ucundan (`mentese_ucu`, DXF ile aynı sözleşme) `icine_normal` yönünde, boy = boşluk eni. Bölmeye yaslı iki oda kapısının
    kanatları birbirine doğru (D-15): HOL'ün iki yanındaki çiftler bölmeye (y = 618,5) yakın uçta."""
    assert pk01["yapi"]["dizilim"]["kapi"] == "mantik"
    plan = G.kur(pk01)
    kanatlar = {}
    for d in plan.duvarlar:
        for p in d.panolar:
            a = p.acilim
            if a is None or a.tur not in ("ic_kapi", "dis_kapi"):
                continue
            ax = _KayitEkseni()
            g = p.gap()
            sunum._kapi_ciz(ax, d, g, a, kapi_mantik=True)
            (x0, x1), (y0, y1) = ax.cizgiler[0]
            a0, a1 = (g[0], g[2]) if d.yon == "x" else (g[1], g[3])
            beklenen = a0 if G.mentese_ucu(a) == 0 else a1
            assert (x0 if d.yon == "x" else y0) == pytest.approx(beklenen)
            s = 1 if a.icine_normal[0] == "+" else -1
            boy = (y1 - y0) if d.yon == "x" else (x1 - x0)
            assert boy == pytest.approx(s * (a1 - a0))
            kanatlar[a.arasi] = (y0 if d.yon == "y" else None)
    for oda in ("MUTFAK", "YATAK ODASI 1", "SALON", "YATAK ODASI 2"):
        assert abs(kanatlar[("HOL", oda)] - 618.5) < 15, (oda, kanatlar[("HOL", oda)])


def test_giris_kapisi_bayi_gorseliyle_ayni(pk01):
    """BK-12 geometri hakemi 3. tur: bayi paftası (`plan_ciz`) giriş kapısının menteşesini bayi görseliyle aynı kuraldan alır
    (`bayi_gorseli._mentese_a0_ucunda`): anahtarsız İş Emri'nde "sol" = a0, çünkü DXF sembolü aynalanmaz; `dizilim.kapi: mantik`'te
    `mentese_ucu` (DXF `dis_ayna`). Eskiden dış kapıda da `mentese_ucu` vardı, P6001 ayna y'de giriş kapısı DXF'e göre tersti.
    Ayırt edici: aynı kapı anahtarsız a0'da, `mantik`'li kopyada a1'de."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Arc
    from motor import bayi_gorseli as BG
    ayna_mantik = _oku(P6001_AYNA_Y)
    ayna_mantik["yapi"].setdefault("dizilim", {})["kapi"] = "mantik"
    a0_ucunda = {}
    for ad, ie in (("ayna_y", _oku(P6001_AYNA_Y)), ("ayna_y_mantik", ayna_mantik), ("PK01", pk01)):
        mantik = ((ie.get("yapi") or {}).get("dizilim") or {}).get("kapi") == "mantik"
        plan = G.kur(ie)
        fig, ax = plt.subplots()
        try:
            sunum.plan_ciz(ax, plan)
            merkezler = [tuple(p.center) for p in ax.patches if isinstance(p, Arc)]
        finally:
            plt.close(fig)
        for d in plan.duvarlar:
            for p in d.panolar:
                a = p.acilim
                if a is None or a.tur != "dis_kapi":
                    continue
                g = p.gap()
                a0, a1 = (g[0], g[2]) if d.yon == "x" else (g[1], g[3])
                dik = d.c + (1 if a.icine_normal[0] == "+" else -1) * d.h
                hm = a0 if BG._mentese_a0_ucunda(a, mantik) else a1
                beklenen = (hm, dik) if d.yon == "x" else (dik, hm)
                assert any(m == pytest.approx(beklenen) for m in merkezler), (ad, a.arasi, beklenen)
                a0_ucunda[ad] = hm == a0
    assert a0_ucunda == {"ayna_y": True, "ayna_y_mantik": False, "PK01": True}


def test_bayi_paftasi_perspektifsiz(pk01, pk01_dogrulama, tmp_path):
    import matplotlib
    import pymupdf
    rc = lambda: {k: v for k, v in matplotlib.rcParams.items() if k != "backend"}    # arka uç rc_context'in dışında (matplotlib; yalnız ad: agg/Agg)
    once = rc()
    o = sunum.bayi_paftasi(pk01, tmp_path, perspektif=False, bilgi={"tarih": "13.10.2026"}, dogrulama=pk01_dogrulama)
    assert rc() == once                                                            # rc_context: çağıranın yazı tipi ve çizim ayarları değişmedi
    assert o["teslim"] is True and o["dosyalar"] == ["PK01_bayi.pdf", "PK01_plan_bayi.png"]
    with pymupdf.open(tmp_path / "PK01_bayi.pdf") as d:
        assert len(d) == 1
        assert (round(d[0].rect.width), round(d[0].rect.height)) == (842, 595)
        metin = " ".join(w[4] for w in d[0].get_text("words"))
    for s in ("TASLAK", "BİNA ÖZELLİKLERİ", "ÖZEL İSTEKLER;", "ARKA", "SOL", "SAĞ", "ÖN (GİRİŞ)", "ÇATI PLANI", "ÖN-SAĞ PERSPEKTİF",
              "ARKA-SAĞ PERSPEKTİF", "perspektif çizilemedi", "PM-PK01-60M2 r01", "PK-01 · 60 M² · 2+1 PREFABRİK KONUT", "MUTFAK",
              "15,0 m²", "198,25", "618,5", "1000", "120/180", "mahya 1060", "29 pano eki + 9 üçlü"):
        assert s in metin, s
    png = tmp_path / "PK01_plan_bayi.png"
    assert png.is_file() and png.stat().st_size <= sunum.PNG_SINIRI
    oz = _oku(tmp_path / "PK01_bayi_ozet.json")
    assert oz["perspektif"]["durum"] == "ÇİZİLMEDİ" and oz["dis_olcu_cm"] == [600.0, 1000.0]


def test_dogrulama_gecmezse_teslim_pdfi_yok(pk01, tmp_path):
    """K23: Motor doğrulaması geçmezse yalnız tanı için `.HATALI.pdf`; teslim adıyla PDF yok."""
    o = sunum.bayi_paftasi(pk01, tmp_path, perspektif=False, dogrulama={"passed": False, "errors": ["deneme"]})
    assert o["teslim"] is False
    assert (tmp_path / "PK01_bayi.HATALI.pdf").is_file() and not (tmp_path / "PK01_bayi.pdf").exists()


def test_motor_dogrulamasi_pk01(pk01_dogrulama):
    assert pk01_dogrulama["passed"] is True, pk01_dogrulama
