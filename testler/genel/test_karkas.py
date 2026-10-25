"""İE-16 PR-3a · motor/genel/karkas.py: çelik karkas kuralı.

Kuraldaki modelden gelen katsayılar (çapraz payı, kolon, kiriş) KT-01'in karkas modelinden yeniden hesaplanır; türetilmiş 140'lık birim
ağırlığı kitabın yöntemiyle yeniden türetilir. Bölme ve üyeler elle hesaplanmış küçük örneklerle; koşu, tanımın panelli ya da bölmesiz
yazılmasından bağımsızdır. Karkas istemeyen tanımda kural hiç çağrılmaz (bugünkü çıktı bayt bayt aynı: altın testler ve `dogrula.py`).
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import cati_genel, girdi_genel, karkas, kural as kurallar_oku, yapi  # noqa: E402

KURAL = karkas.oku(karkas.KURAL)
KT01 = KOK / "modeller" / "KT01.json"
PROFIL_BOYLARI = KOK / "deneme" / "2026-10-06_kor_test" / "tanim" / "KT01_profil_boylari.json"
CP06 = KOK / "testler" / "celik" / "projeler" / "CP06"


def _cozum(satirlar: list[tuple[float, float, float]]) -> tuple[float, float]:
    """En küçük kareler, iki bilinmeyen (r = a·u + b·v): normal denklemler."""
    suu = sum(u * u for u, v, r in satirlar); suv = sum(u * v for u, v, r in satirlar); svv = sum(v * v for u, v, r in satirlar)
    sur = sum(u * r for u, v, r in satirlar); svr = sum(v * r for u, v, r in satirlar)
    det = suu * svv - suv * suv
    return (sur * svv - svr * suv) / det, (svr * suu - sur * suv) / det


def _kt01_duvarlari():
    """KT-01'in 15 ev duvarı: (ad, boy, yükseklik, çaprazsız üyelerin boyu m, modeldeki boy m)."""
    sifir = {**KURAL, "capraz_payi": {"deger": {"a_m_m": 0.0, "b_m_m2": 0.0}}}
    t = json.loads(KT01.read_text(encoding="utf-8"))
    y = yapi.kur(t)
    pb = json.loads(PROFIL_BOYLARI.read_text(encoding="utf-8"))
    out = []
    for w in y["duvarlar"]:
        if w["sinif"] not in ("dis", "ic"):
            continue
        ap = [(a["a0"] - w["_bas"], a["a1"] - w["_bas"], a["z0"], a["z1"]) for a in y["acikliklar"] if a["duvar"] == w["ad"]]
        H = yapi._yukseklik(w)
        out.append((w["ad"], w["boy"], H, sum(karkas.uyeler(w["boy"], H, ap, sifir).values()), pb[w["ad"]]["boy_m"]))
    return t, pb, out


def test_capraz_payi_kt01_modelinden_yeniden_hesaplanir():
    """Kuraldaki çapraz payı (a, b): KT-01'in 15 ev duvarında modeldeki boy − öteki üyeler = H × (a + b × L), en küçük kareler."""
    _, _, duvarlar = _kt01_duvarlari()
    assert len(duvarlar) == 15 and sum(1 for d in duvarlar if d[0].startswith("D")) >= 9
    satirlar = [(H / 100, H / 100 * L / 100, g - s) for _, L, H, s, g in duvarlar]
    a, b = _cozum(satirlar)
    cp = karkas.d(KURAL, "capraz_payi")
    assert (round(a, 3), round(b, 3)) == (cp["a_m_m"], cp["b_m_m2"])
    # birini dışarıda bırakma hatası (kuralda %8,7)
    hatalar = []
    for i, (_, L, H, s, g) in enumerate(duvarlar):
        ai, bi = _cozum(satirlar[:i] + satirlar[i + 1:])
        hatalar.append((s + H / 100 * (ai + bi * L / 100) - g) / g)
    assert round(math.sqrt(sum(h * h for h in hatalar) / len(hatalar)) * 100, 1) == 8.7


def test_kolon_ve_kiris_katsayilari_kt01_modelinden():
    t, pb, _ = _kt01_duvarlari()
    assert round(pb["KLN1"]["boy_m"] / 2.4, 2) == karkas.d(KURAL, "kolon")["profil_m_m"]
    boy = sum(max(k["kutu"][2] - k["kutu"][0], k["kutu"][3] - k["kutu"][1]) for k in t["kirisler"]) / 100
    assert len(t["kirisler"]) == 3
    assert round(sum(pb[k["ad"]]["boy_m"] for k in t["kirisler"]) / boy, 3) == karkas.d(KURAL, "kiris")["profil_m_m"]


def test_140_birim_agirligi_kitabin_yontemiyle():
    kitap = kurallar_oku.oku()["celik"]["profil_kg_m"]["deger"]["80x45x1,2"]
    acilim_mm = kitap / (1.2 * 7.85) * 1000                 # 80 × 45 × 1,2'nin açılımı
    assert round(acilim_mm, 1) == 176.2
    assert round((acilim_mm + 140 - 80) * 1.2 * 7.85 / 1000, 3) == karkas.d(KURAL, "profil_kg_m_ek")["140x45x1,2"]


@pytest.mark.parametrize("boy,adet", [(100, 1), (366, 1), (366.5, 2), (732, 2), (733, 3), (1098, 3)])
def test_bolme_en_cok_366_esit_panel(boy, adet):
    p = karkas.bol({"bas": 50.0, "son": 50.0 + boy}, [], KURAL)
    assert len(p) == adet and p[0][0] == 50.0 and p[-1][1] == 50.0 + boy
    assert max(b - a for a, b in p) - min(b - a for a, b in p) < 0.2 and all(b - a <= 366 for a, b in p)


def test_ek_yeri_acikligin_yakin_kenarina_kayar():
    # 600'lük koşu iki panel: ek yeri 300; 280–380 arası açıklık → yakın kenar 280
    assert karkas.bol({"bas": 0.0, "son": 600.0}, [{"a0": 280.0, "a1": 380.0}], KURAL) == [(0.0, 280.0), (280.0, 600.0)]
    assert karkas.bol({"bas": 0.0, "son": 600.0}, [{"a0": 220.0, "a1": 310.0}], KURAL) == [(0.0, 310.0), (310.0, 600.0)]


def test_aciksiz_panelin_uyeleri():
    """366 × 270, açıklıksız: yedi dikme (0, 61, … 366), iki başlık, iki kuşak (122, 244), çapraz payı."""
    u = karkas.uyeler(366.0, 270.0, [], KURAL)
    cp = karkas.d(KURAL, "capraz_payi")
    assert u["dikme"] == pytest.approx(7 * 2.70) and u["baslik"] == pytest.approx(2 * 3.66) and u["kusak"] == pytest.approx(2 * 3.66)
    assert u["kirpik"] == u["kenar_dikmesi"] == u["lento_denizlik"] == 0
    assert u["capraz"] == pytest.approx(2.70 * (cp["a_m_m"] + cp["b_m_m2"] * 3.66))


def test_pencereli_panelin_uyeleri():
    """244 × 240, 100–200 arası pencere (alt 90, üst 210): 61'deki ve 244'teki dikme tam; 122 ve 183 kırpık; kenar dikmesi iki
    (100 ve 200'e en yakın tam dikme 61 ve 244, yarım aralıktan uzak); başlık ve denizlik levhası (100 + 10) iki kez; 244 kuşağı yok
    (240 − 5'ten yukarıda), 122 kuşağı pencerenin boyu kadar kısa."""
    u = karkas.uyeler(244.0, 240.0, [(100.0, 200.0, 90.0, 210.0)], KURAL)
    assert u["dikme"] == pytest.approx(3 * 2.40)                    # 0, 61, 244
    assert u["kirpik"] == pytest.approx(2 * (0.30 + 0.90))           # 122, 183
    assert u["kenar_dikmesi"] == pytest.approx(2 * 2.40)
    assert u["lento_denizlik"] == pytest.approx(2 * 1.10)
    assert u["kusak"] == pytest.approx(2.44 - 1.00)


def test_kosu_tanimin_yazimindan_bagimsiz():
    """ÇP-06 panel panel (PR-2) ya da bölmesiz (W01…) yazılmış olsun: koşular ve kuralın panelleri aynı."""
    panelli = json.loads((CP06 / "CP06.json").read_text(encoding="utf-8"))
    bolmesiz = json.loads((CP06 / "CP06_kural.json").read_text(encoding="utf-8"))

    def ozet(t):
        kk = karkas.kur(yapi.kur(t), t, KURAL)
        return [{k: p[k] for k in ("ad", "sinif", "profil", "bas", "son", "kutu", "yukseklik_cm", "uyeler_m", "profil_boyu_m")} for p in kk["paneller"]]

    kp, kb = karkas.kosular(yapi.kur(panelli), panelli), karkas.kosular(yapi.kur(bolmesiz), bolmesiz)
    assert [(k["sinif"], k["yon"], k["hat"], k["bas"], k["son"]) for k in kp] == [(k["sinif"], k["yon"], k["hat"], k["bas"], k["son"]) for k in kb]
    assert ozet(panelli) == ozet(bolmesiz)
    assert sum(1 for p in ozet(bolmesiz) if p["sinif"] in ("dis", "ic")) == 22


def test_karkas_istemeyen_tanimda_kural_cagrilmaz(monkeypatch):
    def yasak(*a, **k):
        raise AssertionError("karkas kuralı çağrıldı")

    for ad in ("oku", "kur", "gruplar", "kosular"):
        monkeypatch.setattr(karkas, ad, yasak)
    t = json.loads(KT01.read_text(encoding="utf-8"))
    assert "karkas" not in t
    kur = kurallar_oku.oku()
    y = yapi.kur(t)
    c = cati_genel.cati_kur(t["cati"], kur)
    m = girdi_genel.metraj(y, c, kur)
    g = girdi_genel.girdi(y, c, m, kur, "test")
    assert m["karkas"] is None and "celik" in g and "karkas" not in g["celik"]      # kural isteyen tanımda kayıt g["celik"]["karkas"]


def test_karkas_alani_yalniz_kural():
    t = json.loads((CP06 / "CP06_kural.json").read_text(encoding="utf-8"))
    kur = kurallar_oku.oku()
    for yanlis in ("model", True):
        t2 = {**t, "karkas": yanlis}
        y = yapi.kur(t2)
        with pytest.raises(SystemExit, match="yalnız"):
            girdi_genel.metraj(y, cati_genel.cati_kur(t2["cati"], kur), kur)


def test_duvar_panelleri_paftasi_belirlenimci(tmp_path):
    from motor.genel import karkas_pafta, uret
    uret.matplotlib_sabitle()
    t = json.loads((KOK / "testler" / "celik" / "projeler" / "CP03" / "CP03.json").read_text(encoding="utf-8"))
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    r = karkas_pafta.ciz(t, tmp_path / "a", "CP03", KURAL)
    karkas_pafta.ciz(t, tmp_path / "b", "CP03", KURAL)
    assert r["duvar_paneli"]["dis"] == 13 and r["kolon_kiris"] == 10 and r["kural"]["sha256"] == KURAL["_sha256"]
    for ad in (r["png"], r["pdf"]):
        assert (tmp_path / "a" / ad).read_bytes() == (tmp_path / "b" / ad).read_bytes(), ad
    panelli = json.loads((CP06 / "CP06.json").read_text(encoding="utf-8"))
    with pytest.raises(SystemExit, match="yalnız karkas"):
        karkas_pafta.ciz(panelli, tmp_path, "CP06")


def test_uret_paftayi_yalniz_kuralda_yazar(tmp_path):
    from motor.genel import uret
    m = uret.uret(CP06 / "CP06_kural.json", tmp_path / "kural", perspektif=False, bayi=False)
    assert m["passed"] and m["duvar_panelleri"]["duvar_paneli"] == {"dis": 14, "ic": 8, "ek": 0, "korkuluk": 0}
    assert (tmp_path / "kural" / "CP06_duvar_panelleri.png").is_file() and (tmp_path / "kural" / "CP06_duvar_panelleri.pdf").is_file()
    m = uret.uret(CP06 / "CP06.json", tmp_path / "panelli", perspektif=False, bayi=False)
    assert m["passed"] and "duvar_panelleri" not in m and not list((tmp_path / "panelli").glob("*duvar_panelleri*"))
