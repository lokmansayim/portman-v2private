"""İE-16 PR-3b · motor/genel/makas.py ve karkas.bacalar: çatı karkas kuralı.

Kuraldaki modelden gelen değerler KT-01'in (= ÇP-13) karkas modelinden yeniden hesaplanır: makasın panel boyu (16 makas, en küçük
kareler ve bir tür dışarıda bırakılınca hata), baca ve çatı panelinin profil boyu. Makasın üyeleri elle hesaplanmış küçük örnekle.
Dizilim açık beş projenin tanımında: türlerin sayısı kuralın bugünkü sonucudur (paftayla kıyası İE-16 › PR-3b'de; burada gerileme),
kuralın kaynak metnindeki ana çatı sayıları paftanınkiyle aynı. Karkas istemeyen tanımda kural hiç çağrılmaz (bugünkü çıktı bayt bayt
aynı: altın testler ve `dogrula.py`).
PR-3c (Lokman, 27 Ekim 2026): çatı panelinde ve çatı üstü panelinde çapraz yok, çatı üstü paneli 180 cm × beş makas aralığı, adedi
tanımda yazmayan çatı paneli 180 cm'lik, tavan paneli en çok 13,60 m, tek açıklığı 8 m'yi aşan makas 1,2 mm. PR-3b'nin davranışı eski
kural kopyasıyla (`ESKI`) aynen sınanır.
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
ESKI_YOL = KOK / "testler" / "celik" / "projeler" / "setler" / "7940e1d20cc18652.json"   # PR-3b'nin kural kopyası
ESKI = karkas.oku(ESKI_YOL)
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
    Çatı paneli: müştemilatın tek paneli (MPNL1 68,889 m, 546 × 337); PR-3b'nin kuralıyla (çaprazlı) 70,79 (+%2,8), et ek yapıda 0,8.
    PR-3c'de çatı panelinde çapraz yok (A3): 55,54 m (−%19,4; modeldeki panelde çapraz payı kadar profil var, İE-16 › PR-3c)."""
    t, c, y = _yukle(KT01)
    b = karkas.bacalar(y, t, KURAL)
    assert len(b) == 1 and [p["profil_boyu_m"] for p in b[0]["paneller"]] == [10.536, 10.536, 9.736, 9.736]
    pb = json.loads(PROFIL_BOYLARI.read_text(encoding="utf-8"))
    assert (pb["BACA1"]["boy_m"], pb["BACA2"]["boy_m"]) == (10.487, 9.687)
    for k, capraz, boy, fark in ((ESKI, True, 70.79, 2.8), (KURAL, False, 55.54, -19.4)):
        cp = makas.cati_panelleri(c, y, k)
        assert len(cp) == 1 and cp[0]["olcu_cm"] == [546.0, 337.04] and cp[0]["profil"] == "80x45x0,8" and cp[0]["ortu"] == "ek yapı"
        assert ("capraz" in cp[0]["uyeler_m"]) == capraz
        assert round((cp[0]["profil_boyu_m"] / pb["MPNL1"]["boy_m"] - 1) * 100, 1) == fark and round(cp[0]["profil_boyu_m"], 2) == boy


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
    """Kuralın yedeğe düştüğü ya da bir şey koymadığı yer sessiz geçmez. Açık beşte (listelerin yöntemiyle): ÇP-03'te altı uyarı (uzanım
    ucunda iki ailede 15,2 cm'lik çizgi, makas yok; iki ailenin arasındaki iki kırma çizgisinde çapraz yok, biri 487,2 cm; 11 tavan paneli
    başka makasların alt başlığını kesiyor; salonda kısa kenarı 15,5 cm tavan paneli), ÇP-07'de iki (kanat birleşiminde 35,4 ve 127,4 cm'lik
    kırma çizgisi, çapraz yok); öteki üçünde uyarı yok (kod incelemesi: iki aile arasındaki kırma ve makası kesen tavan paneli sessizdi).
    Mahyaya varmayan beşik makas kısa."""
    for kod in TANIMLAR:
        t, c, y = _yukle(PROJELER / TANIMLAR[kod])
        u = makas.kur(t, y, KURAL, "panel" if kod == "CP03" else None)["uyarilar"]
        capraz_yok = [x.split(" kırma çizgisi (")[1].split(" cm)")[0] for x in u if "iki ailenin arasında: çapraz yok" in x]
        if kod == "CP07":
            assert len(u) == 2 and capraz_yok == ["35.4", "127.4"], u
        elif kod != "CP03":
            assert u == [], (kod, u)
        else:
            assert len(u) == 6 and sum("15.2 cm (en kısa 40): makas yok" in x for x in u) == 2 and capraz_yok == ["56.4", "487.2"], u
            assert "kısa kenarı 15.5 cm" in u[4] and "tavan paneli: 11 panel başka makasların alt başlığını kesiyor (toplam 40 kesişme)" in u[5], u
    t, c, y = _yukle(PROJELER / TANIMLAR["CP03"])
    m = makas.makaslar(t, c, y, KURAL)
    besik = {f["aile"] for f in m["aileler"] if f["tur"] == "besik"}
    assert sum(1 for x in m["makaslar"] if x["tur"] == "kisa" and x["aile"] in besik) == 4


def test_yedek_ve_dusme_uyarilari(monkeypatch):
    """Açık beşte çalışmayan uyarı yolları gerçek geometriyle (geometri hakemi 2. tur): ucunda duvar bulunamayan aile (ÇP-06'nın kuzey
    duvarı yok), saçağı bulunamayan kırma yüzü ve tek parça kesilmeyen kırma şeridi (ÇP-03'ün ön yüzü), aileye bağlanmayan kırma yüzü."""
    from shapely.affinity import translate
    t, c, y = _yukle(PROJELER / TANIMLAR["CP06"])
    assert makas.makaslar(t, c, y, KURAL)["uyarilar"] == []
    y2 = dict(y, duvarlar=[w for w in y["duvarlar"] if w["ad"] != "W03"])
    assert makas.makaslar(t, c, y2, KURAL)["uyarilar"] == ["makas: batı/doğu ailesinin alın ucunda duvar bulunamadı; uç 1027.0 (mahyanın ucu)"]
    t, c, y = _yukle(PROJELER / TANIMLAR["CP03"])
    c2 = dict(c, kenarlar=[e for e in c["kenarlar"] if not (e["tur"] == "sacak" and e["duzlemler"] == ["ön"])])
    assert "makas: ön sol/sağ ailesinin ön kırma yüzünde saçak bulunamadı; uç mahyanın ucundan 10 × saçak" in makas.makaslar(t, c2, y, KURAL)["uyarilar"]
    c3 = dict(c, duzlemler=[dict(d, cokgen=translate(d["cokgen"], 0, 1e5)) if d["ad"] == "ön" else d for d in c["duzlemler"]])
    assert any(u.startswith("makas: ön sol/sağ ailesinin ön kırma yüzünde uç duvar çizgisi yüzü tek parça kesmiyor (boş)")
               for u in makas.makaslar(t, c3, y, KURAL)["uyarilar"])
    gercek = makas.aileler
    monkeypatch.setattr(makas, "aileler", lambda c_: (*gercek(c_)[:3], ["ön"]))
    assert makas.makaslar(t, c, y, KURAL)["uyarilar"][0] == "makas: ön kırma yüzü hiçbir aileye bağlanmadı; o yüzde kısa makas ve çapraz yok"


@pytest.mark.parametrize("kod, beklenen", [
    ("CP06", []),
    ("CP07", ["Salon 376.8–481.9", "Yatak Odası 702.1–809.8"]),
    ("CP13", ["Banyo 575.0–683.0"]),
    ("CP14", ["Banyo 601.7–719.2"]),
])
def test_tavan_paneli_makastan_dar_serit_ve_parca(kod, beklenen):
    """Yöntem A öteki dört açık projede (bilgi; listeleri B): makas kalınlığından dar şerit (ÇP-06 235–243, ÇP-13 243–251: iki makas sırt
    sırta) panel olmaz ve uyarı yazmaz; kısa kenarı makas kalınlığından dar parça panel olmaz, uyarı yazar (geometri hakemi 2. tur)."""
    t, c, y = _yukle(PROJELER / TANIMLAR[kod])
    a = makas.kur(t, y, KURAL, "panel")
    kal = makas._d(KURAL, "makas")["kalinlik_cm"]
    sinirlar = sorted({v for f in a["aileler"] if f["ana"] and f["tur"] == "besik" for v in f["konumlar"]})
    dar = [(p, q) for p, q in zip(sinirlar, sinirlar[1:]) if q - p <= kal + makas.EPS]
    assert bool(dar) == (kod in ("CP06", "CP13"))
    assert all(p["serit"][1] - p["serit"][0] > kal + makas.EPS and min(p["olcu_cm"]) > kal + makas.EPS for p in a["tavan_panelleri"])
    kesen = [p for p in a["tavan_panelleri"] if p["kesilen_makas"]]
    assert bool(kesen) and f"tavan paneli: {len(kesen)} panel başka makasların" in "".join(a["uyarilar"])
    yok = [u for u in a["uyarilar"] if u.endswith("panel yok")]
    assert [u.split(" mahalinde ")[0][len("tavan paneli: "):] + " " + u.split(" mahalinde ")[1].split(" ")[0] for u in yok] == beklenen


def test_kucuk_ve_bozuk_catilar_cokmez():
    """Kod incelemesi: bütün düzlemleri çatı paneli olan çatı, iki ucu kırma ve 125 cm'den kısa aile, saçağı olmayan tek eğimli düzlem
    çökmez; kural makas koymaz ve uyarı yazar."""
    t, c, y = _yukle(PROJELER / TANIMLAR["CP13"])
    t1 = copy.deepcopy(t)
    for d in t1["cati"]["duzlemler"]:
        d["ust_yapi"] = "cati_paneli"
    ck = makas.kur(t1, yapi.kur(t1), KURAL)
    assert ck["makaslar"] == [] and ck["uyarilar"] == ["makas: çatıda makas ailesi bulunamadı; makas yok"]
    dz = lambda ad, plan, yuk, sac: {"ad": ad, "plan": plan, "yukari": yuk, "egim": 0.3, "sacak_kotu": 280.0, "sacak": sac}
    cati = {"tip": "kirma", "sacak": 30, "duvar_ustu": 270, "duzlemler": [      # 170 × 180 kırma çatı, mahya 10 cm, duvarsız
        dz("batı", [[-30, -30], [55, 55], [55, 65], [-30, 150]], [1, 0], {"x": -30}),
        dz("doğu", [[140, -30], [140, 150], [55, 65], [55, 55]], [-1, 0], {"x": 140}),
        dz("güney", [[-30, -30], [140, -30], [55, 55]], [0, 1], {"y": -30}),
        dz("kuzey", [[-30, 150], [55, 65], [140, 150]], [0, -1], {"y": 150})]}
    m = makas.makaslar({"cati": cati}, cati_genel.cati_kur(cati), {"duvarlar": []}, KURAL)
    assert Counter(x["tur"] for x in m["makaslar"]) == {"capraz": 4}
    assert m["uyarilar"][-1] == "makas: batı/doğu ailesinde iki uç arası 120.0 cm (iki ucu da düşen konum, aralık en çok 125): tam makas yok"
    t, c, y = _yukle(PROJELER / TANIMLAR["CP06"])
    c2 = dict(c, kenarlar=[e for e in c["kenarlar"] if not (e["tur"] == "sacak" and e["duzlemler"] == ["veranda"])])
    m = makas.makaslar(t, c2, y, KURAL)
    assert m["uyarilar"] == ["makas: veranda ailesinin (tek eğimli) saçağı yok: makas yok"] and all(x["aile"] != "veranda" for x in m["makaslar"])


def test_tavan_paneli_kurulamazsa_uyari_ve_oran(monkeypatch):
    """Kural tavan panelini kuramazsa (ana beşik aile yok) uyarı yazılır; yükleme girdisinde satır kitabın oranına sessizce dönmez."""
    t, c, y = _yukle(PROJELER / TANIMLAR["CP03"])
    mk = makas.makaslar(t, c, y, KURAL)
    u: list[str] = []
    assert makas.tavan_panelleri(c, y, KURAL, dict(mk, aileler=[dict(f, ana=False) for f in mk["aileler"]]), u) == []
    assert u == ["tavan paneli: ana beşik aile yok; tavan paneli kurulmadı"]
    monkeypatch.setattr(makas, "tavan_panelleri", lambda *a: [])
    g = _girdi(PROJELER / TANIMLAR["CP03"])
    assert set(g["celik"]["a_panelleri"]) == {"ust_paneli"}
    assert "karkas kuralı: tavan paneli kurulmadı; satır kitabın oranıyla (100 m² için kg, oturum alanına)" in g["uyarilar"]


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


def test_uret_eski_kural_kopyasinda_makas_paftasi_cizilmez(tmp_path):
    """`uret` eski kural kopyasıyla (çatı kuralı yok) makas paftasını çizmeye kalkmaz, üretim geçer (PR-3a'nın listeleri o kopyayla
    `liste_yap`'tan yeniden üretilir; geometri hakemi 2. tur: koruma testsizdi). Bugünkü kuralla pafta manifest'te."""
    from motor.genel import uret
    eski = uret.uret(PROJELER / TANIMLAR["CP13"], tmp_path / "eski", perspektif=False, bayi=False,
                     karkas_yolu=PROJELER / "setler" / "a3683af36f42b92d.json")
    assert eski["passed"] and "makaslar" not in eski and "duvar_panelleri" in eski
    yeni = uret.uret(PROJELER / TANIMLAR["CP13"], tmp_path / "yeni", perspektif=False, bayi=False)
    assert yeni["passed"] and yeni["makaslar"]["makas"] == {"makas": 14, "kisa": 1, "capraz": 1}


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
    """Çatı üstü ve tavan paneli yalnız yöntem A'da kurulur; tavan panelinde çapraz yok (`tavan_paneli.capraz`). PR-3b'nin kopyasında çatı
    üstü paneli saçak boyunca 366'lık şeritler, çaprazlı (ÇP-03 14); PR-3c'de eğim boyunca 180 cm, saçak boyunca beş makas aralığı (625),
    çaprazsız (B7, B9; ÇP-03 25, paftada 20)."""
    t, c, y = _yukle(PROJELER / TANIMLAR["CP03"])
    for k, n_ust, capraz in ((ESKI, 14, True), (KURAL, 25, False)):
        a = makas.kur(t, y, k, "panel")
        b = makas.kur(t, y, k, "omega_asik")
        assert (len(a["ust_panelleri"]), len(a["tavan_panelleri"])) == (n_ust, 12)
        assert "ust_panelleri" not in b and "tavan_panelleri" not in b and a["makaslar"] == b["makaslar"]
        assert all("capraz" not in p["uyeler_m"] for p in a["tavan_panelleri"])
        assert all(("capraz" in p["uyeler_m"]) == capraz for p in a["ust_panelleri"])
    up = karkas.d(KURAL, "ust_paneli")
    boy = up["boy_makas_araligi"] * makas._d(KURAL, "makas")["aralik_cm"]
    assert (up["en_cm"], boy) == (180, 625)
    assert all(p["olcu_cm"][0] <= boy + 0.01 and p["olcu_cm"][1] <= up["en_cm"] + 0.01 for p in a["ust_panelleri"])


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
    assert (g["makas"]["adet"], g["ust_paneli"]["adet"], g["tavan_paneli"]["adet"]) == (24, 25, 12)
    t = json.loads((PROJELER / TANIMLAR["CP13"]).read_text(encoding="utf-8"))
    y = yapi.kur(t)
    g = karkas.gruplar(karkas.kur(y, t, KURAL), y, t, KURAL, kur["celik"]["profil_kg_m"]["deger"])
    assert (g["makas"]["adet"], g["baca"]["adet"], g["cati_paneli"]["adet"]) == (16, 4, 1) and g["cati_paneli"]["profil"] == "80x45x0,8"
    t = json.loads((PROJELER / TANIMLAR["CP06"]).read_text(encoding="utf-8"))
    assert sum(v["adet"] for v in t["cati"]["makaslar"].values()) == 13
    ce = _girdi(PROJELER / TANIMLAR["CP06"])["celik"]
    assert ce["cati"]["panel_adedi"] == 15 and ce["cati"]["not"] == "makas kuralından: 13 tam, 1 kısa, 1 kırma çaprazı"
    ce = _girdi(PROJELER / TANIMLAR["CP03"])["celik"]
    assert {k: v["adet"] for k, v in ce["a_panelleri"].items()} == {"ust_paneli": 25, "tavan_paneli": 12}


def test_karkas_istemeyen_tanimda_cati_kurali_yok(tmp_path):
    """Karkas kuralı istemeyen tanımın yükleme girdisinde makas adedi tanımdan (`cati.makaslar`), kuralın kayıtları yok; makas paftası
    çizilmez."""
    t = json.loads((PROJELER / "CP06" / "CP06.json").read_text(encoding="utf-8"))
    assert t.get("karkas") != "kural"
    ce = _girdi(PROJELER / "CP06" / "CP06.json")["celik"]
    assert ce["cati"]["panel_adedi"] == 13 and "a_panelleri" not in ce and "karkas" not in ce
    with pytest.raises(SystemExit):
        makas_pafta.ciz(t, tmp_path, "CP06")


def test_makas_paftasi_uyarilari_basar(tmp_path, monkeypatch):
    """Makas paftası kuralın uyarılarını tablonun altında basar (ÇP-03, yöntem A: altı)."""
    yazilan = []
    gercek = makas_pafta.tablo
    monkeypatch.setattr(makas_pafta, "tablo", lambda ax, *a: (gercek(ax, *a), yazilan.append(ax.texts[-1].get_text())))
    t = json.loads((PROJELER / TANIMLAR["CP03"]).read_text(encoding="utf-8"))
    r = makas_pafta.ciz(t, tmp_path, "CP03", yontem="panel")
    assert r["uyari"] == 6 and "Uyarılar (6):" in yazilan[0] and yazilan[0].count("• ") == 6 and "panel kuruldu" in yazilan[0]


def test_makas_paftasi(tmp_path):
    """Pafta kuralın kaydını çizer: sayılar `karkas.kur`'unkiyle aynı, PNG ve PDF yazılır."""
    t = json.loads((PROJELER / TANIMLAR["CP07"]).read_text(encoding="utf-8"))
    r = makas_pafta.ciz(t, tmp_path, "CP07")
    assert r["makas"] == {"makas": 11, "kisa": 11, "capraz": 6} and (r["cati_paneli"], r["baca"]) == (4, 2)
    assert (tmp_path / r["png"]).stat().st_size > 0 and (tmp_path / r["pdf"]).stat().st_size > 0 and r["uyari"] == 2


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


@pytest.mark.parametrize("kod, en_uzun", [("CP06", 548.0), ("CP03", 645.0), ("CP07", 540.4), ("CP13", 518.0), ("CP14", 534.0)])
def test_makasin_tek_acikligi_ve_eti(kod, en_uzun):
    """PR-3c (B5): makasın altında desteksiz en uzun aralık (dış, iç, ek duvar, kolon ve makasa dik kiriş destektir); 8 m'yi aşarsa 1,2 mm.
    Açık beşte ana makaslar 9,55 m'ye varsa da desteksiz aralık en çok 6,45 m: hepsi 0,8. Eski kopyada et yazılmaz."""
    t, c, y = _yukle(PROJELER / TANIMLAR[kod])
    m = makas.kur(t, y, KURAL, "panel" if kod == "CP03" else None)["makaslar"]
    ta = [x["tek_aciklik_cm"] for x in m if x["tek_aciklik_cm"] is not None]
    assert max(ta) == en_uzun and all(x["et"] == "0,8" for x in m)
    assert all(x["tek_aciklik_cm"] is None or x["tek_aciklik_cm"] <= x["acik_cm"] + 0.1 for x in m)
    assert not any("et" in x or "tek_aciklik_cm" in x for x in makas.kur(t, y, ESKI)["makaslar"])


def test_kalin_makas_ayri_satir(tmp_path, monkeypatch):
    """Tek açıklığı sınırı aşan makas kuralın kalın etiyle ayrı grup (`makas_kalin`) ve listede ayrı satır ('Çatı makas panelleri (1,2 mm)');
    hepsi kalınsa makas satırının kendisi kalın. Sınır 5 m'ye indirilmiş kopyayla ÇP-06: 548 ve 518 cm'lik açıklıklar kalın."""
    from testler.celik.projeler import liste_yap
    d = json.loads(karkas.KURAL.read_text(encoding="utf-8"))
    d["makas_eti"]["deger"]["tek_aciklik_en_cok_cm"] = 500
    yol = tmp_path / "kural.json"
    yol.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    k = karkas.oku(yol)
    t, c, y = _yukle(PROJELER / TANIMLAR["CP06"])
    kk = karkas.kur(y, t, k)
    kalin = [x for x in kk["cati"]["makaslar"] if x["et"] == "1,2"]
    assert kalin and all(x["tek_aciklik_cm"] > 500 for x in kalin)
    g = karkas.gruplar(kk, y, t, k, kurallar_oku.oku()["celik"]["profil_kg_m"]["deger"])
    assert g["makas_kalin"]["adet"] == len(kalin) and g["makas_kalin"]["profil"] == "80x45x1,2"
    assert g["makas"]["adet"] + g["makas_kalin"]["adet"] == len(kk["cati"]["makaslar"])
    monkeypatch.setenv("PORTMAN_KARKAS", str(yol))
    es = [x for x in _girdi(PROJELER / TANIMLAR["CP06"])["celik"]["ek_satirlar"] if x["ad"].startswith("Çatı makas panelleri")]
    assert [(x["ad"], x["panel_adedi"], x["profil"]) for x in es] == [("Çatı makas panelleri (1,2 mm)", len(kalin), "80x45x1,2")]
    assert liste_yap.celik_turu("Çatı makas panelleri (1,2 mm)") == liste_yap.celik_turu("Çatı makas panelleri") == "makas"
    hepsi = {**kk, "cati": {**kk["cati"], "makaslar": [{**x, "et": "1,2"} for x in kk["cati"]["makaslar"]]}}
    g = karkas.gruplar(hepsi, y, t, k, {})
    assert "makas_kalin" not in g and g["makas"]["profil"] == "80x45x1,2"


def test_cati_paneli_adedi_tanimda_yoksa_kuraldan():
    """PR-3c (B9): adedi tanımda yazmayan açık alan çatı paneli (kör proje) saçak boyunca 180 cm'lik; açık paftalarla: ÇP-14 verandası 5
    (paftada 5), ÇP-07 verandası 3 (3) ve sundurması 1 (1). Ek yapının çatı paneli tek panel (ÇP-13 = KT-01 müştemilatı; tanımda adet
    yazmıyor). Liste ve makas paftası aynı adedi okur. Eski kopyada düzlem başına 1."""
    for kod in ("CP07", "CP14"):
        t = json.loads((PROJELER / TANIMLAR[kod]).read_text(encoding="utf-8"))
        yazili = [dz.pop("cati_paneli_adedi") for dz in t["cati"]["duzlemler"] if "cati_paneli_adedi" in dz]
        c, y = cati_genel.cati_kur(t["cati"]), yapi.kur(t)
        assert len(makas.cati_panelleri(c, y, KURAL)) == len(makas_pafta.cati_paneli_planlari(c, KURAL, y)) == sum(yazili)
        assert len(makas.cati_panelleri(c, y, ESKI)) == len(makas_pafta.cati_paneli_planlari(c)) == len(yazili)
    t, c, y = _yukle(PROJELER / TANIMLAR["CP07"])
    assert len(makas.cati_panelleri(c, y, KURAL)) == len(makas_pafta.cati_paneli_planlari(c, KURAL, y)) == 4    # yazılı adet (3 + 1) geçer
    t, c, y = _yukle(PROJELER / TANIMLAR["CP13"])
    dz = next(dz for dz in c["duzlemler"] if dz.get("ust_yapi") == "cati_paneli")
    assert "cati_paneli_adedi" not in dz and makas.ek_yapi_mi(dz, y) and makas.cati_paneli_adedi(dz, KURAL, y) == 1


def test_tavan_paneli_en_uzun_13_60():
    """PR-3c (B6): uzun kenarı tırın 13,60 m'sini aşan tavan paneli o kenar boyunca eşit bölünür; sınır yoksa (eski kopya) bölünmez."""
    from shapely.geometry import box
    assert karkas.d(KURAL, "tavan_paneli")["en_uzun_cm"] == 1360 and "en_uzun_cm" not in karkas.d(ESKI, "tavan_paneli")
    p = makas._uzunu_bol(box(0, 0, 3000, 110), 1360)
    assert len(p) == 3 and all(abs(g.bounds[2] - g.bounds[0] - 1000) < 0.01 for g in p)
    assert len(makas._uzunu_bol(box(0, 0, 110, 1360), 1360)) == 1 and len(makas._uzunu_bol(box(0, 0, 3000, 110), None)) == 1
