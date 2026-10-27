"""İE-16 PR-3a · motor/genel/karkas.py: çelik karkas kuralı.

Kuraldaki modelden gelen katsayılar (çapraz payı, kolon, kiriş) KT-01'in karkas modelinden yeniden hesaplanır; türetilmiş 140'lık birim
ağırlığı kitabın yöntemiyle yeniden türetilir. Bölme ve üyeler elle hesaplanmış küçük örneklerle; koşu, tanımın panelli ya da bölmesiz
yazılmasından bağımsızdır. Karkas istemeyen tanımda kural hiç çağrılmaz (bugünkü çıktı bayt bayt aynı: altın testler ve `dogrula.py`).
PR-3c (Lokman, 27 Ekim 2026): panel oda bölmesinde biter (`bolme.oda_bolmesi`), 140'lık motorun ortalamasıyla (`profil_kg_m_ek` boş).
PR-3a/3b'nin davranışı (366 cm hedefi, türetilmiş 2,225 kg/m) eski kural kopyasıyla (`ESKI`) aynen sınanır.
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
ESKI_YOL = KOK / "testler" / "celik" / "projeler" / "setler" / "7940e1d20cc18652.json"   # PR-3b'nin kural kopyası (366 cm, 2,225 kg/m)
ESKI = karkas.oku(ESKI_YOL)
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
    """PR-3a'nın türetilmiş değeri (eski kopyada durur) ve PR-3c'nin kuralı: 140'lığın birim ağırlığı yok, motorun ortalaması (A4)."""
    kitap = kurallar_oku.oku()["celik"]["profil_kg_m"]["deger"]["80x45x1,2"]
    acilim_mm = kitap / (1.2 * 7.85) * 1000                 # 80 × 45 × 1,2'nin açılımı
    assert round(acilim_mm, 1) == 176.2
    assert round((acilim_mm + 140 - 80) * 1.2 * 7.85 / 1000, 3) == karkas.d(ESKI, "profil_kg_m_ek")["140x45x1,2"]
    assert karkas.d(KURAL, "profil_kg_m_ek") == {} and KURAL["profil_kg_m_ek"]["durum"] == "lokman"


@pytest.mark.parametrize("boy,adet", [(100, 1), (366, 1), (366.5, 2), (732, 2), (733, 3), (1098, 3)])
def test_aciksiz_kosu_hedef_366_esit_panel(boy, adet):
    """Eski kopya (PR-3a/3b): koşu ceil(boy ÷ 366) eşit panel."""
    assert karkas.d(ESKI, "bolme") == {"hedef_cm": 366}
    p = karkas.bol({"bas": 50.0, "son": 50.0 + boy}, [], ESKI)
    assert len(p) == adet and p[0][0] == 50.0 and p[-1][1] == 50.0 + boy
    assert max(b - a for a, b in p) - min(b - a for a, b in p) < 0.2 and all(b - a <= 366 for a, b in p)


@pytest.mark.parametrize("boy,adet", [(100, 1), (516, 1), (516.5, 2), (1032, 2), (1033, 3)])
def test_bolmesiz_kosu_en_uzun_516_esit_panel(boy, adet):
    """PR-3c (A1, A5): oda bölmesi olmayan koşu 516'yı aşarsa eşit bölünür; 5 m'lik salon cephesi tek panel."""
    assert karkas.d(KURAL, "bolme") == {"oda_bolmesi": True, "en_uzun_cm": 516}
    p = karkas.bol({"bas": 50.0, "son": 50.0 + boy}, [], KURAL)
    assert len(p) == adet and p[0][0] == 50.0 and p[-1][1] == 50.0 + boy
    assert max(b - a for a, b in p) - min(b - a for a, b in p) < 0.2 and all(b - a <= 516 for a, b in p)


def test_panel_oda_bolmesinde_biter():
    """PR-3c (A1): koşu ona dik bağlanan her duvarın ekseninde bölünür; her bölme kendi içinde 516'ya göre. Açıklığa düşen ek yeri yakın
    kenara kayar. Eski kopyada bağlantı noktası sayılmaz (366'ya göre eşit)."""
    ks = {"bas": 0.0, "son": 1200.0}
    assert karkas.bol(ks, [], KURAL, [300.0]) == [(0.0, 300.0), (300.0, 750.0), (750.0, 1200.0)]
    assert karkas.bol(ks, [], KURAL, [300.0, 800.0]) == [(0.0, 300.0), (300.0, 800.0), (800.0, 1200.0)]
    assert karkas.bol(ks, [{"a0": 260.0, "a1": 320.0}], KURAL, [300.0]) == [(0.0, 320.0), (320.0, 760.0), (760.0, 1200.0)]
    assert karkas.bol(ks, [], ESKI, [300.0]) == karkas.bol(ks, [], ESKI) == [(0.0, 300.0), (300.0, 600.0), (600.0, 900.0), (900.0, 1200.0)]


def test_eklemler_koseyi_saymaz():
    """Bağlantı noktası: koşuya dik dış, iç ya da ek duvarın ekseni; koşunun ucuna dik duvarın kendi kalınlığından yakın olan (köşe) sayılmaz."""
    t = json.loads((CP06 / "CP06_kural.json").read_text(encoding="utf-8"))
    y = yapi.kur(t)
    for ks in karkas.kosular(y, t):
        for j in karkas.eklemler(y, ks):
            assert ks["bas"] < j < ks["son"]
    assert sum(len(karkas.eklemler(y, ks)) for ks in karkas.kosular(y, t)) > 0


def test_cok_yakin_iki_oda_bolmesi_uyari(monkeypatch):
    """İki ucu oda bölmesi olan kısa panel paftada da var (ÇP-14'ün 50–51 cm'lik sekizi; uyarı yok), ama iki profil derinliğinden kısası
    (karşılıklı iki duvarın ekseni birbirine çok yakın) sessiz kalmaz: kayıtta uyarı."""
    t = json.loads((CP06 / "CP06_kural.json").read_text(encoding="utf-8"))
    y = yapi.kur(t)
    assert karkas.kur(y, t, KURAL)["uyarilar"] == []
    gercek = karkas.eklemler
    monkeypatch.setattr(karkas, "eklemler", lambda y_, ks: sorted(e + [e[0] + 8.0]) if (e := gercek(y_, ks)) else e)
    kk = karkas.kur(y, t, KURAL)
    kisa = [p for p in kk["paneller"] if p["boy_cm"] == 8.0]
    assert kisa and len([u for u in kk["uyarilar"] if "iki profil derinliğinden" in u and "panel 8.0 cm" in u]) == len(kisa)


def test_ek_yeri_acikligin_yakin_kenarina_kayar():
    # eski kopya (366): 600'lük koşu iki panel: ek yeri 300; 280–380 arası açıklık → yakın kenar 280
    assert karkas.bol({"bas": 0.0, "son": 600.0}, [{"a0": 280.0, "a1": 380.0}], ESKI) == [(0.0, 280.0), (280.0, 600.0)]
    assert karkas.bol({"bas": 0.0, "son": 600.0}, [{"a0": 220.0, "a1": 310.0}], ESKI) == [(0.0, 310.0), (310.0, 600.0)]
    # 720'lik koşu: ek yeri 360, 300–370 kapısı → yakın kenar 370; ilk panel 370 (hedefi aşar, `kur` uyarı yazar)
    assert karkas.bol({"bas": 0.0, "son": 720.0}, [{"a0": 300.0, "a1": 370.0}], ESKI) == [(0.0, 370.0), (370.0, 720.0)]
    # PR-3c: 1100'lük bölmesiz koşu üç panel (ek yerleri 366,7 ve 733,3); 330–400 kapısı → yakın kenar 400 (en uzunu aşmaz)
    assert karkas.bol({"bas": 0.0, "son": 1100.0}, [{"a0": 330.0, "a1": 400.0}], KURAL)[0] == (0.0, 400.0)


def test_hedefi_asan_panel_uyari_olarak_yazilir(monkeypatch):
    """Ek yeri kapının kenarına kayınca panel 366'yı aşar (eski kopya; ÇP-14'te hol–veranda duvarı, 411,4 cm): sessiz kalmaz, kayıtta ve
    girdide uyarı."""
    monkeypatch.setenv("PORTMAN_KARKAS", str(ESKI_YOL))
    t = json.loads((KOK / "testler" / "celik" / "projeler" / "CP14" / "CP14.json").read_text(encoding="utf-8"))
    kk = karkas.kur(yapi.kur(t), t, ESKI)
    asan = [p for p in kk["paneller"] if p["boy_cm"] > 366 + karkas.TOL]
    assert asan and len(kk["uyarilar"]) == len(asan)
    assert all(p["ad"] in u and str(p["boy_cm"]) in u for p, u in zip(asan, kk["uyarilar"]))
    kur = kurallar_oku.oku()
    y = yapi.kur(t)
    c = cati_genel.cati_kur(t["cati"], kur)
    m = girdi_genel.metraj(y, c, kur)
    g = girdi_genel.girdi(y, c, m, kur, "test")
    assert [u for u in g["uyarilar"] if u.startswith("karkas kuralı: ")] == ["karkas kuralı: " + u for u in kk["uyarilar"]]
    assert g["celik"]["karkas"]["uyarilar"] == kk["uyarilar"]


def test_en_uzunu_asan_panel_uyari_bugunku_kuralla(tmp_path):
    """Bugünkü kuralla (oda bölmesi): bölme sınırı düşürülmüş kopyada (400) ÇP-14'ün hol–veranda duvarının ek yeri kapının kenarına kayar,
    panel 411,4 cm: uyarı yazar (sayı ve ad)."""
    d = json.loads(karkas.KURAL.read_text(encoding="utf-8"))
    d["bolme"]["deger"]["en_uzun_cm"] = 400
    yol = tmp_path / "kural.json"
    yol.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    t = json.loads((KOK / "testler" / "celik" / "projeler" / "CP14" / "CP14.json").read_text(encoding="utf-8"))
    kk = karkas.kur(yapi.kur(t), t, karkas.oku(yol))
    asan = [p for p in kk["paneller"] if p["boy_cm"] > 400 + karkas.TOL]
    uy = [u for u in kk["uyarilar"] if "bölmenin en uzunu 400 cm" in u]
    assert [p["boy_cm"] for p in asan] == [411.4] and len(uy) == 1 and asan[0]["ad"] in uy[0]


def test_kisa_kalan_panel_uyari_olarak_yazilir(monkeypatch):
    """Ek yeri açıklığın kenarına kayınca koşunun ucunda bir dikme aralığından kısa panel kalabilir (700'lük koşu, 20–690 açıklık: ek
    yeri 350'den 20'ye): sessiz kalmaz. Koşunun kendisi kısaysa (ÇP-14'ün 50 cm'lik cumba yanları) uyarı yok."""
    assert karkas.bol({"bas": 0.0, "son": 700.0}, [{"a0": 20.0, "a1": 690.0}], KURAL) == [(0.0, 20.0), (20.0, 700.0)]
    t = json.loads((KOK / "testler" / "celik" / "projeler" / "CP14" / "CP14.json").read_text(encoding="utf-8"))
    for k in (ESKI, KURAL):
        kk = karkas.kur(yapi.kur(t), t, k)
        assert any(p["boy_cm"] < 61 for p in kk["paneller"]) and not any("kısa" in u for u in kk["uyarilar"])
        assert all("_kosunun_parcasi" not in p for p in kk["paneller"])
    bol = karkas.bol
    monkeypatch.setattr(karkas, "bol", lambda ks, acik, k, eklem=(): [(ks["bas"], ks["bas"] + 20.0), (ks["bas"] + 20.0, ks["son"])]
                        if ks["son"] - ks["bas"] > 300 else bol(ks, acik, k, eklem))
    kk = karkas.kur(yapi.kur(t), t, ESKI)
    kisa = [p for p in kk["paneller"] if p["boy_cm"] == 20.0]
    assert kisa and len([u for u in kk["uyarilar"] if "bir dikme aralığından (61 cm) kısa" in u]) == len(kisa)


def test_gruplar_karisik_profili_ve_ezilen_grubu_durdurur():
    """Listede sınıf ve grup başına tek satır var: karışık profil sessizce tek profille tartılmaz, ikinci korkuluk profili birinciyi ezmez."""
    pan = lambda sinif, profil, kosu: {"sinif": sinif, "profil": profil, "kosu": [kosu], "profil_boyu_m": 1.0}
    bos = {"kolonlar": [], "kirisler": []}
    t = {"duvar_siniflari": {"korkuluk": {"profil": "80x45x0,8"}}}
    with pytest.raises(SystemExit, match="birden çok profil"):
        karkas.gruplar({"paneller": [pan("dis", "80x45x1,2", "W1"), pan("dis", "140x45x1,2", "W2")], **bos}, {"duvarlar": []}, t, KURAL, {})
    y = {"duvarlar": [{"ad": "R1", "sinif": "korkuluk", "profil": "80x45x0,8", "yukseklik": 90},
                      {"ad": "R2", "sinif": "korkuluk", "profil": "80x45x1,2", "yukseklik": 100}]}
    with pytest.raises(SystemExit, match="aynı gruba"):
        karkas.gruplar({"paneller": [pan("korkuluk", "80x45x0,8", "R1"), pan("korkuluk", "80x45x1,2", "R2")], **bos}, y, t, KURAL, {})


def test_kural_modunda_satirlar_kaynagi_dogru_yazar(monkeypatch):
    """Kural modunda kolon ve kirişin adedi tanımdan, profil boyu kuraldan (model yok). 140'lık dış duvar: eski kopyada formül türetilmiş
    birim ağırlığı kg'ı veren haneyle yazar; PR-3c'de (A4) kitabın hükmü, motorun ortalaması (duvar boyu × kg/m)."""
    from motor.genel import yukleme
    t = json.loads((KOK / "testler" / "celik" / "projeler" / "CP03" / "CP03.json").read_text(encoding="utf-8"))
    kur = kurallar_oku.oku()

    def satirlar():
        y = yapi.kur(t)
        c = cati_genel.cati_kur(t["cati"], kur)
        g = girdi_genel.girdi(y, c, girdi_genel.metraj(y, c, kur), kur, "test")
        return {s["kalem"]: s for s in yukleme.hesapla(g, kur)["satirlar"] if s.get("grup") == "Çelik panel"}

    satir = satirlar()
    assert "modelden" not in satir["Veranda dikmeleri (kolon paneli)"]["not"] and "tanımdan" in satir["Veranda dikmeleri (kolon paneli)"]["not"]
    assert "modelden" not in satir["Kirişler (kiriş paneli)"]["not"] + satir["Kirişler (kiriş paneli)"]["formul"]
    dis = satir["Dış cephe duvar panelleri"]
    assert dis["durum"] == "motor" and "motorun proje ortalaması" in dis["formul"] and "2,225" not in dis["formul"]
    assert "birim ağırlığı kuralda yok: motorun ortalaması kullanıldı" in dis["not"]
    monkeypatch.setenv("PORTMAN_KARKAS", str(ESKI_YOL))
    dis = satirlar()["Dış cephe duvar panelleri"]
    assert "× 2,225 kg/m" in dis["formul"]
    boy = float(dis["formul"].split("profil boyu ")[1].split(" m")[0].replace(",", "."))
    assert round(boy * 2.225, 2) == pytest.approx(dis["kg"], abs=0.01)


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


def test_acikligin_kenarindaki_dikme_tam_boydur():
    """150 × 270, panel pencerenin kenarında bitiyor (100–150, alt 70, üst 200; ek yeri açıklığın kenarına kayınca olur): 150'deki uç
    dikme kenar dikmesidir, tam boy, bir kez; kırpık yalnız 122'de; 100'e yarım aralık içinde tam dikme yok, bir kenar dikmesi."""
    u = karkas.uyeler(150.0, 270.0, [(100.0, 150.0, 70.0, 200.0)], KURAL)
    assert u["dikme"] == pytest.approx(3 * 2.70)                    # 0, 61, 150
    assert u["kirpik"] == pytest.approx(0.70 + 0.70)                # 122
    assert u["kenar_dikmesi"] == pytest.approx(2.70)                # 100


def test_kosu_tanimin_yazimindan_bagimsiz():
    """ÇP-06 panel panel (PR-2) ya da bölmesiz (W01…) yazılmış olsun: koşular ve kuralın panelleri aynı."""
    panelli = json.loads((CP06 / "CP06.json").read_text(encoding="utf-8"))
    bolmesiz = json.loads((CP06 / "CP06_kural.json").read_text(encoding="utf-8"))

    def ozet(t, k):
        kk = karkas.kur(yapi.kur(t), t, k)
        return [{a: p[a] for a in ("ad", "sinif", "profil", "bas", "son", "kutu", "yukseklik_cm", "uyeler_m", "profil_boyu_m")} for p in kk["paneller"]]

    kp, kb = karkas.kosular(yapi.kur(panelli), panelli), karkas.kosular(yapi.kur(bolmesiz), bolmesiz)
    assert [(k["sinif"], k["yon"], k["hat"], k["bas"], k["son"]) for k in kp] == [(k["sinif"], k["yon"], k["hat"], k["bas"], k["son"]) for k in kb]
    # ev duvarı paneli: eski kopya (366) 22, PR-3c (oda bölmesi) 20; paftada 26 (İE-16 › PR-3c)
    for k, n in ((ESKI, 22), (KURAL, 20)):
        assert ozet(panelli, k) == ozet(bolmesiz, k)
        assert sum(1 for p in ozet(bolmesiz, k) if p["sinif"] in ("dis", "ic")) == n


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
    assert r["duvar_paneli"]["dis"] == 10 and r["kolon_kiris"] == 10 and r["kural"]["sha256"] == KURAL["_sha256"]
    for ad in (r["png"], r["pdf"]):
        assert (tmp_path / "a" / ad).read_bytes() == (tmp_path / "b" / ad).read_bytes(), ad
    panelli = json.loads((CP06 / "CP06.json").read_text(encoding="utf-8"))
    with pytest.raises(SystemExit, match="yalnız karkas"):
        karkas_pafta.ciz(panelli, tmp_path, "CP06")


def test_uret_paftayi_yalniz_kuralda_yazar(tmp_path):
    from motor.genel import uret
    m = uret.uret(CP06 / "CP06_kural.json", tmp_path / "kural", perspektif=False, bayi=False)
    assert m["passed"] and m["duvar_panelleri"]["duvar_paneli"] == {"dis": 11, "ic": 9, "ek": 0, "korkuluk": 0}
    assert (tmp_path / "kural" / "CP06_duvar_panelleri.png").is_file() and (tmp_path / "kural" / "CP06_duvar_panelleri.pdf").is_file()
    m = uret.uret(CP06 / "CP06.json", tmp_path / "panelli", perspektif=False, bayi=False)
    assert m["passed"] and "duvar_panelleri" not in m and not list((tmp_path / "panelli").glob("*duvar_panelleri*"))
