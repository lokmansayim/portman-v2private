"""İE-16 PR-3b · motor/genel/makas.py ve karkas.bacalar: çatı karkas kuralı.

Kuraldaki modelden gelen değerler KT-01'in (= ÇP-13) karkas modelinden yeniden hesaplanır: makasın panel boyu (16 makas, en küçük
kareler ve bir tür dışarıda bırakılınca hata), baca ve çatı panelinin profil boyu. Makasın üyeleri elle hesaplanmış küçük örnekle.
Dizilim açık beş projenin tanımında: türlerin sayısı kuralın bugünkü sonucudur (paftayla kıyası İE-16 › PR-3b'de; burada gerileme),
kuralın kaynak metnindeki ana çatı sayıları paftanınkiyle aynı. Karkas istemeyen tanımda kural hiç çağrılmaz (bugünkü çıktı bayt bayt
aynı: altın testler ve `dogrula.py`).
"""
from __future__ import annotations
import copy
import json
import math
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.genel import cati_genel, girdi_genel, karkas, kural as kurallar_oku, makas, makas_pafta, yapi  # noqa: E402

KURAL = karkas.oku(karkas.KURAL)
KT01 = KOK / "modeller" / "KT01.json"
PROFIL_BOYLARI = KOK / "deneme" / "2026-10-06_kor_test" / "tanim" / "KT01_profil_boylari.json"
PROJELER = KOK / "testler" / "celik" / "projeler"
TANIMLAR = {"CP03": "CP03/CP03.json", "CP06": "CP06/CP06_kural.json", "CP07": "CP07/CP07.json", "CP13": "CP13/CP13.json", "CP14": "CP14/CP14.json"}
# KT-01'in karkas modelindeki makaslar türlerine göre (profil boyları dosyası): tam 7 (MKS2–6, truss5, truss7), cumba 3 (MKS8, MKS9,
# truss10), veranda 4 (MKS11–14), kırma çaprazı MKS15, kısa MKS16
KT01_MAKAS = {"tam": ("MKS2", "MKS3", "MKS4", "MKS5", "MKS6", "truss5", "truss7"), "cumba": ("MKS8", "MKS9", "truss10"),
              "veranda": ("MKS11", "MKS12", "MKS13", "MKS14"), "capraz": ("MKS15",), "kisa": ("MKS16",)}


def _yukle(yol: Path):
    t = json.loads(yol.read_text(encoding="utf-8"))
    return t, cati_genel.cati_kur(t["cati"]), yapi.kur(t)


def _tur(x: dict) -> str:
    if x["tur"] in ("kisa", "capraz"):
        return x["tur"]
    return "cumba" if "cumba" in x["aile"] else ("veranda" if x["aile"] == "veranda" else "tam")


def _kt01_makaslari(panel_cm: float) -> list[dict]:
    t, c, y = _yukle(KT01)
    k = copy.deepcopy(KURAL)
    k["makas_uyeleri"]["deger"]["panel_cm"] = panel_cm
    return makas.makaslar(t, c, y, k)["makaslar"]


def test_makasin_uyeleri_elle():
    """Tek eğimli 148 cm açıklık, 74 cm yükselen üst: iki panel (74), iç düğümde bir dikme (37), iki çapraz (ortalama 18,5 ve 55,5)."""
    u = makas.uyeler([0.0, 148.0], [270.0, 344.0], 270.0, 74.0)
    assert u["alt_baslik"] == pytest.approx(1.48)
    assert u["ust_baslik"] == pytest.approx(math.hypot(148, 74) / 100)
    assert u["dikme"] == pytest.approx(0.37)
    assert u["capraz"] == pytest.approx((math.hypot(74, 18.5) + math.hypot(74, 55.5)) / 100)


def test_panel_boyu_kt01_modelinden_yeniden_hesaplanir():
    """Kuraldaki panel_cm: KT-01'in 16 makasında (türüne göre modeldeki boy) en küçük kareler; 74–79 aynı, en küçüğü. Toplam +%1,0;
    bir tür dışarıda bırakılınca hata kuralın kaynağındaki gibi."""
    pb = json.loads(PROFIL_BOYLARI.read_text(encoding="utf-8"))
    model = {tur: pb[adlar[0]]["boy_m"] for tur, adlar in KT01_MAKAS.items()}
    assert all(pb[a]["boy_m"] == model[tur] for tur, adlar in KT01_MAKAS.items() for a in adlar)
    toplam_model = sum(pb[a]["boy_m"] for adlar in KT01_MAKAS.values() for a in adlar)
    assert round(toplam_model, 2) == 424.63
    adaylar = {p: _kt01_makaslari(p) for p in range(50, 101)}
    assert all(Counter(_tur(x) for x in m) == {t: len(a) for t, a in KT01_MAKAS.items()} for m in adaylar.values())

    def hata(m, haric=None):
        return sum((x["profil_boyu_m"] - model[_tur(x)]) ** 2 for x in m if _tur(x) != haric)
    en_iyi = min(hata(m) for m in adaylar.values())
    plato = [p for p, m in adaylar.items() if hata(m) == pytest.approx(en_iyi)]
    assert plato == list(range(74, 80)) and makas._d(KURAL, "makas_uyeleri")["panel_cm"] == plato[0]
    toplam = sum(x["profil_boyu_m"] for x in adaylar[74])
    assert round(toplam, 2) == 429.02 and round((toplam / toplam_model - 1) * 100, 1) == 1.0
    disarida = {}
    for tur in model:
        p = min(adaylar, key=lambda p_: (hata(adaylar[p_], tur), p_))
        xs = [x["profil_boyu_m"] for x in adaylar[p] if _tur(x) == tur]
        disarida[tur] = round((sum(xs) / len(xs) / model[tur] - 1) * 100, 1)
    assert disarida == {"tam": -6.7, "cumba": 7.5, "veranda": 0.3, "capraz": -7.7, "kisa": 39.5}


def test_baca_ve_cati_paneli_kt01_modeliyle():
    """Baca: dört panel, ikisi dış ölçüde (KT-01 BACA1 10,487 m), ikisi profil derinliği kadar dar (BACA2 9,687); kural 10,536 ve 9,736.
    Çatı paneli: müştemilatın tek paneli (MPNL1 68,889 m, 546 × 337); kural 70,79 (+%2,8), et ek yapıda 0,8."""
    t, c, y = _yukle(KT01)
    b = karkas.bacalar(y, t, KURAL)
    assert len(b) == 1 and [p["profil_boyu_m"] for p in b[0]["paneller"]] == [10.536, 10.536, 9.736, 9.736]
    pb = json.loads(PROFIL_BOYLARI.read_text(encoding="utf-8"))
    assert (pb["BACA1"]["boy_m"], pb["BACA2"]["boy_m"]) == (10.487, 9.687)
    cp = makas.cati_panelleri(c, y, KURAL)
    assert len(cp) == 1 and cp[0]["olcu_cm"] == [546.0, 337.04] and cp[0]["profil"] == "80x45x0,8" and cp[0]["ortu"] == "ek yapı"
    assert round((cp[0]["profil_boyu_m"] / pb["MPNL1"]["boy_m"] - 1) * 100, 1) == 2.8 and round(cp[0]["profil_boyu_m"], 2) == 70.79


@pytest.mark.parametrize("kod, beklenen", [
    ("CP13", {"makas": 14, "kisa": 1, "capraz": 1}),
    ("CP06", {"makas": 13, "kisa": 1, "capraz": 1}),
    ("CP14", {"makas": 24}),
    ("CP07", {"makas": 11, "kisa": 11, "capraz": 6}),
    ("CP03", {"makas": 8, "kisa": 12, "capraz": 4}),
])
def test_acik_projelerde_dizilim(kod, beklenen):
    """Türlerin sayısı kuralın bugünkü sonucu (gerileme). Paftayla kıyas İE-16 › PR-3b'de: ÇP-13 16/16, ÇP-06 15 (paftada 13 M + cumbada
    2 C), ÇP-14 24 (26), ÇP-07 28 (34), ÇP-03 24 (14 makas + 13 makas paneli; tasarım başka). ÇP-03'ün 12 kısasının 4'ü beşik ailede
    çizgisi mahyaya varmayan makas (geometri hakemi 1. tur)."""
    t, c, y = _yukle(PROJELER / TANIMLAR[kod])
    m = makas.makaslar(t, c, y, KURAL)["makaslar"]
    assert Counter(x["tur"] for x in m) == beklenen
    assert all(x["acik_cm"] >= makas._d(KURAL, "makas")["en_kisa_cm"] for x in m if x["tur"] != "capraz")


def test_uyarilar():
    """Kuralın yedeğe düştüğü ya da bir şey koymadığı yer sessiz geçmez: açık beşte yalnız ÇP-03'te üç uyarı (uzanım ucunda iki ailede
    15,2 cm'lik çizgi, makas yok; salonda kısa kenarı 15,5 cm tavan paneli); öteki dördünde uyarı yok. Mahyaya varmayan beşik makas kısa."""
    for kod in TANIMLAR:
        t, c, y = _yukle(PROJELER / TANIMLAR[kod])
        u = makas.kur(t, y, KURAL, "panel" if kod == "CP03" else None)["uyarilar"]
        if kod != "CP03":
            assert u == [], (kod, u)
            continue
        assert len(u) == 3 and sum("15.2 cm (en kısa 40): makas yok" in x for x in u) == 2 and "kısa kenarı 15.5 cm" in u[2], u
        m = makas.makaslar(t, c, y, KURAL)
        besik = {f["aile"] for f in m["aileler"] if f["tur"] == "besik"}
        assert sum(1 for x in m["makaslar"] if x["tur"] == "kisa" and x["aile"] in besik) == 4


def test_mahyadaki_fazla_kose_aileyi_ikilemez():
    """Mahyanın üstündeki fazladan köşe (aynı doğru üzerinde) mahyayı iki kenara böler; aile yine tek, makaslar aynı (geometri hakemi 1. tur)."""
    t, c, y = _yukle(PROJELER / TANIMLAR["CP06"])
    t2 = copy.deepcopy(t)
    d = {x["ad"]: x for x in t2["cati"]["duzlemler"]}
    d["batı"]["plan"].insert(3, [450.0, 600.0])
    d["doğu"]["plan"].append([450.0, 600.0])
    c2 = cati_genel.cati_kur(t2["cati"])
    assert sum(1 for e in c2["kenarlar"] if e["tur"] == "mahya") == sum(1 for e in c["kenarlar"] if e["tur"] == "mahya") + 1
    a, b = makas.makaslar(t, c, y, KURAL), makas.makaslar(t2, c2, yapi.kur(t2), KURAL)
    assert a["makaslar"] == b["makaslar"] and [f["aile"] for f in a["aileler"]] == [f["aile"] for f in b["aileler"]]


def test_ailesiz_catida_makas_yok_ve_tanima_donulmez(monkeypatch):
    """Kural makas kuramazsa (aile yok) uyarı yazılır; yükleme girdisinde makas adedi yok ve tanımdaki `cati.makaslar`'a dönülmez,
    çatı çeliği motorun ortalamasıyla ve uyarıyla."""
    gercek = makas.aileler
    monkeypatch.setattr(makas, "aileler", lambda c: (*gercek(c)[:2], [], []))
    g = _girdi(PROJELER / TANIMLAR["CP06"])
    assert "panel_adedi" not in g["celik"]["cati"]
    assert "karkas kuralı: makas: çatıda makas ailesi bulunamadı; makas yok" in g["uyarilar"]
    assert any(u.startswith("karkas kuralı: makas kurulmadı;") for u in g["uyarilar"])


def test_eski_kural_kopyasinda_eski_davranis(monkeypatch):
    """PR-3b'nin anahtarları olmayan kural kopyası (PR-3a'nın `setler/a3683af36f42b92d.json`'u): baca ve çatı kuralı kurulmaz, makas adedi
    tanımdan (ÇP-06 13); liste o günkü kuralla yeniden üretilebilir."""
    eski = PROJELER / "setler" / "a3683af36f42b92d.json"
    k = karkas.oku(eski)
    assert "makas" not in k and "baca" not in k
    t, c, y = _yukle(PROJELER / TANIMLAR["CP13"])
    kk = karkas.kur(y, t, k)
    assert kk["bacalar"] == [] and kk["cati"] is None
    monkeypatch.setenv("PORTMAN_KARKAS", str(eski))
    ce = _girdi(PROJELER / TANIMLAR["CP06"])["celik"]
    assert ce["cati"]["panel_adedi"] == 13 and ce["cati"]["not"].endswith("adet modelden (13 makas)")


def test_ana_catinin_makas_sayisi_paftadaki_gibi():
    """Kuralın kaynağındaki sayılar (`makas`): tam makas sayısı ailelere göre paftadakiyle aynı (ÇP-06 ana 7; ÇP-13 7 + 3 + 4;
    ÇP-14 ana 14; ÇP-07 ana çatı 5 + 3)."""
    def aileler(kod):
        t, c, y = _yukle(PROJELER / TANIMLAR[kod])
        return Counter(x["aile"] for x in makas.makaslar(t, c, y, KURAL)["makaslar"] if x["tur"] == "makas")
    assert aileler("CP06")["batı/doğu"] == 7
    assert sorted(aileler("CP13").values()) == [3, 4, 7]
    assert aileler("CP14")["kuzey/güney"] == 14
    a = aileler("CP07")
    assert (a["kuzey/batı güney"], a["kuzey/doğu güney"]) == (5, 3)


def test_konumlar_esit_aralikli_en_cok_kural_araligi():
    """Ailenin konumları iki uç arasında eşit aralıklı, aralık en çok `aralik_cm`."""
    S = makas._d(KURAL, "makas")["aralik_cm"]
    for kod in TANIMLAR:
        t, c, y = _yukle(PROJELER / TANIMLAR[kod])
        for f in makas.makaslar(t, c, y, KURAL)["aileler"]:
            ks = f["konumlar"]
            if len(ks) < 2:
                continue
            araliklar = [b - a for a, b in zip(ks, ks[1:])]
            assert max(araliklar) <= S + 0.01 and max(araliklar) - min(araliklar) < 0.05, (kod, f["aile"], araliklar)


def test_yontem_a_panelleri_yalniz_panel_yontemiyle():
    """Çatı üstü ve tavan paneli yalnız yöntem A'da kurulur; tavan panelinde çapraz yok (`tavan_paneli.capraz`)."""
    t, c, y = _yukle(PROJELER / TANIMLAR["CP03"])
    a = makas.kur(t, y, KURAL, "panel")
    b = makas.kur(t, y, KURAL, "omega_asik")
    assert (len(a["ust_panelleri"]), len(a["tavan_panelleri"])) == (14, 12)
    assert "ust_panelleri" not in b and "tavan_panelleri" not in b and a["makaslar"] == b["makaslar"]
    assert all("capraz" not in p["uyeler_m"] for p in a["tavan_panelleri"]) and all("capraz" in p["uyeler_m"] for p in a["ust_panelleri"])


def _girdi(yol: Path) -> dict:
    """`girdi_genel.main`'in yaptığı: tanım → metraj → yükleme girdisi."""
    kur = kurallar_oku.oku()
    t = json.loads(yol.read_text(encoding="utf-8"))
    y = yapi.kur(t)
    c = cati_genel.cati_kur(t["cati"], kur)
    return girdi_genel.girdi(y, c, girdi_genel.metraj(y, c, kur), kur, "test")


def test_gruplar_ve_yukleme_girdisi():
    """`karkas.gruplar` makas, baca, çatı paneli ve (A) çatı üstü, tavan paneli gruplarını kurar. Yükleme girdisinde makas adedi kuraldan:
    ÇP-06'nın tanımındaki `cati.makaslar` (paftadan 13) karkas kuralında okunmaz, kuralın 15'i yazılır."""
    kur = kurallar_oku.oku()
    t = json.loads((PROJELER / TANIMLAR["CP03"]).read_text(encoding="utf-8"))
    y = yapi.kur(t)
    g = karkas.gruplar(karkas.kur(y, t, KURAL, "panel"), y, t, KURAL, kur["celik"]["profil_kg_m"]["deger"])
    assert (g["makas"]["adet"], g["ust_paneli"]["adet"], g["tavan_paneli"]["adet"]) == (24, 14, 12)
    t = json.loads((PROJELER / TANIMLAR["CP13"]).read_text(encoding="utf-8"))
    y = yapi.kur(t)
    g = karkas.gruplar(karkas.kur(y, t, KURAL), y, t, KURAL, kur["celik"]["profil_kg_m"]["deger"])
    assert (g["makas"]["adet"], g["baca"]["adet"], g["cati_paneli"]["adet"]) == (16, 4, 1) and g["cati_paneli"]["profil"] == "80x45x0,8"
    t = json.loads((PROJELER / TANIMLAR["CP06"]).read_text(encoding="utf-8"))
    assert sum(v["adet"] for v in t["cati"]["makaslar"].values()) == 13
    ce = _girdi(PROJELER / TANIMLAR["CP06"])["celik"]
    assert ce["cati"]["panel_adedi"] == 15 and ce["cati"]["not"] == "makas kuralından: 13 tam, 1 kısa, 1 kırma çaprazı"
    ce = _girdi(PROJELER / TANIMLAR["CP03"])["celik"]
    assert {k: v["adet"] for k, v in ce["a_panelleri"].items()} == {"ust_paneli": 14, "tavan_paneli": 12}


def test_karkas_istemeyen_tanimda_cati_kurali_yok():
    """Karkas kuralı istemeyen tanımın yükleme girdisinde makas adedi tanımdan (`cati.makaslar`), kuralın kayıtları yok; makas paftası
    çizilmez."""
    t = json.loads((PROJELER / "CP06" / "CP06.json").read_text(encoding="utf-8"))
    assert t.get("karkas") != "kural"
    ce = _girdi(PROJELER / "CP06" / "CP06.json")["celik"]
    assert ce["cati"]["panel_adedi"] == 13 and "a_panelleri" not in ce and "karkas" not in ce
    with pytest.raises(SystemExit):
        makas_pafta.ciz(t, KOK, "CP06")


def test_makas_paftasi(tmp_path):
    """Pafta kuralın kaydını çizer: sayılar `karkas.kur`'unkiyle aynı, PNG ve PDF yazılır."""
    t = json.loads((PROJELER / TANIMLAR["CP07"]).read_text(encoding="utf-8"))
    r = makas_pafta.ciz(t, tmp_path, "CP07")
    assert r["makas"] == {"makas": 11, "kisa": 11, "capraz": 6} and (r["cati_paneli"], r["baca"]) == (4, 2)
    assert (tmp_path / r["png"]).stat().st_size > 0 and (tmp_path / r["pdf"]).stat().st_size > 0 and r["uyari"] == 0


@pytest.mark.parametrize("kod", ["CP07", "CP13", "CP14"])
def test_cati_paneli_planda_acilimdaki_sirayla(kod):
    """Paftadaki çatı paneli şeritleri (Ç01…) tablodaki sırayla aynı: her şerit, açılımdaki aynı sıradaki panelin yerinde (açılımın saçak
    ekseni u = p · sag, `cati_genel`; plandaki u aralığı açılımdakiyle aynı) ve ölçüsünde (geometri hakemi 1. tur: sag eksi yöndeyken
    sıra tersti)."""
    t, c, y = _yukle(PROJELER / TANIMLAR[kod])
    adli = {d["ad"]: d for d in c["duzlemler"]}
    acilim = [(dz["ad"], g) for dz in c["duzlemler"] if dz.get("ust_yapi") == "cati_paneli"
              for g in makas._saciga_bol(makas._acilim(dz), int(dz.get("cati_paneli_adedi", 1)))]
    ters = 0
    for x, r, (ad, g) in zip(makas_pafta.cati_paneli_planlari(c), makas.cati_panelleri(c, y, KURAL), acilim, strict=True):
        dz = adli[x["duzlem"]]
        assert r["duzlem"] == x["duzlem"] == ad
        pts = list(x["cokgen"].exterior.coords)
        u = [p[0] * dz["sag"][0] + p[1] * dz["sag"][1] for p in pts]
        v = [p[0] * dz["yukari"][0] + p[1] * dz["yukari"][1] for p in pts]
        assert (min(u), max(u)) == (pytest.approx(g.bounds[0], abs=0.05), pytest.approx(g.bounds[2], abs=0.05))
        assert (max(u) - min(u), (max(v) - min(v)) * dz["kok"]) == (pytest.approx(r["olcu_cm"][0], abs=0.05), pytest.approx(r["olcu_cm"][1], abs=0.05))
        ters += dz["sag"][0] + dz["sag"][1] < 0
    assert (ters > 0) == (kod in ("CP07", "CP13"))     # sag eksi yönde: ÇP-07'nin verandası (dört panel; eski sıra burada tersti), ÇP-13 tek panel
