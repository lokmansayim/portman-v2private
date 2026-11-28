"""63 m² tek evin (TK-11) montaj rehberinde oda sırası ve kubbe (BK-89, D-164; 28 Kasım 2026).

Lokman, 28 Kasım 2026 (UTC), 27 Kasım'da onayladığı rehber için:
- 05:16:18 "3. adımdaki salon diziliminde kubbe deki parçalar önce açılı pencere olan parça sonra karşıya gelen 133,78 lik parça sonra
  solundaki açılı parça sonra üstündeki 50 cm lik 251 duvar gelir ve bunların hepsi kaplı gelir yani çıplak çelik bırakılmaz bunlara
  karkaslı pano denir kubbenin yamuk olan panoları tek kanat penceredir"
- 05:16:56 "yani aynı duvarlar gibi gelir montaj paftasını aç kubbede duvar duvardır"
- 05:18:03 "ayrıca sıralama hatalı önce köşedeki küçük bir bölmeden başlarsın bu proje için önce yatak odası 1 koydun sonra banyo sonra
  yatak odası 2 sonra salon gelir"
- 05:18:47 "çelik karkasları aynı duvar mantığındaki gibi 8 mm iç dış fibercement ile kaplıyoruz"
- 05:45:38 "… sonra sırayla sağdaki kubbe panosunu karşıdaki panoyu soldaki panoyu en son üstteki 50 cm lik parça geliyor bu arada unutma
  yükleme listesindeki KUBBE ÜSTÜ H 100*100*500 2 / ÖZEL AÇILI KÖŞE DİREĞİ + KAPAMASI 100*100*2330 aynı H'lar gibi kullanılıyor"
- 05:48:38–05:53:37 saha kesimi: direkler ve kubbe panoları 203 cm, üstteki pano 50 cm; usta üstteki panonun köşelerini açılı keser, pano
  3 cm iner, toplam 250; açılı köşe direği ve açılı panolar kesilmez; alttan alçıpan
- 06:08:55 "burada saçak omegası var kubbe saçaklarını koymak için mecburen saçak omegasıda koyuyoruz gerisini doğru yapmışsın"
- 06:11:13 kart "Soru 21": "13 cm" (kubbe penceresinin alt kenarı üretim dosyasındaki gibi)
- 06:23:20 kart "Soru 22: r03 eskizi doğru mu? …": "Onaylıyorum" (yalnız eskiz; yeni rehber ayrıca onaya gider)

Girdi `araclar/paket/girdi/TK11_r02_rehber.json`: 27 Kasım'da onaylanan rehberin girdisi (`TK11_r02_cati.json`) ve `rehber` anahtarı.
Anahtarı yalnız montaj rehberi okur; Motor, yükleme listesi ve teklif okumaz. Eski girdi eski rehberi aynen verir: onun hedef örneği
(D-160, `rehber_tk11_63/iz.json`) `test_rehber_tk11_63.py`'de durur ve bu işte değişmedi. Yeni girdinin rehberi Lokman'ın onayından
sonra hedef örnek olur (D-28 madde 2; ayrı PR).
"""
from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz  # noqa: E402

IE = KOK / "araclar" / "paket" / "girdi" / "TK11_r02_rehber.json"          # evin rehber girdisi: onaylı girdi + `rehber` anahtarı
IE_ONCEKI = KOK / "araclar" / "paket" / "girdi" / "TK11_r02_cati.json"      # 27 Kasım'da onaylanan rehberin girdisi (D-160); değişmez
URETIM = KOK / "araclar" / "uretim" / "veri" / "kubbe.json"
ODA_SIRASI = ["YATAK ODASI 1", "BANYO", "YATAK ODASI 2", "YAŞAMA ALANI", "HOL"]
PANO = "Karkaslı özel pencere panosu"
UST, DIREK, H, OMEGA, ALCIPAN = ("Kubbe özel pano 100 × 2500 × 500 · karkaslı", "Özel açılı köşe direği + kapaması", "Kubbe üstü H 100 × 100 × 500",
                                 "Saçak omegası · kubbe", "Kubbe tavanı alçıpanı")
# salon diziliminde kubbe, art arda (Lokman 05:45:38; eskiz r03): dışarıdan bakışla sağdaki açılı pano, karşıdaki, soldaki, üstteki pano
KUBBE_DIZISI = [DIREK, f"{PANO} (59/170) · kubbe, sağdaki açılı", DIREK, f"{PANO} (105/170) · kubbe, karşıdaki", DIREK,
                f"{PANO} (59/170) · kubbe, soldaki açılı", DIREK, H, UST, H,
                "PVC pencere 59/170 (kubbe)", "PVC pencere 105/170 (kubbe)", "PVC pencere 59/170 (kubbe)"]


def _kur(ie, tmp):
    from motor import geometry as G
    from araclar.paket import uret
    from araclar.paket.rehber import veri
    L = uret.listeler(copy.deepcopy(ie), ["ters"])["ters"]
    uret.kart_modeli(copy.deepcopy(ie), tmp, "TK-11")
    try:
        return veri.kur(copy.deepcopy(ie), tmp / "kart", "TK-11", L["satirlar"], "TK-11")
    finally:
        G.lento_ayarla({})                               # lento modül durumudur (BK-23): öteki testlere sızmaz


@pytest.fixture(scope="module")
def d(tmp_path_factory):
    return _kur(json.loads(IE.read_text(encoding="utf-8")), tmp_path_factory.mktemp("tk11_kubbe"))


@pytest.fixture(scope="module")
def ek(d):
    return {ad: [e for e in d["ek"] if e["ad"] == ad or e["ad"].startswith(ad + " ")] for ad in (PANO, UST, DIREK, H, OMEGA, ALCIPAN, "PVC pencere")}


def _kutu(m):
    v = m["v"]
    return [min(v[0::3]), min(v[1::3]), min(v[2::3]), max(v[0::3]), max(v[1::3]), max(v[2::3])]


def test_girdi_onayli_girdi_ve_rehber_anahtari():
    """Yeni girdi, 27 Kasım'da onaylanan rehberin girdisi ve `rehber` anahtarıdır; başka fark yok. Anahtarı Motor ve liste okumaz:
    motorun planı ve yükleme listesi satır satır aynı (liste ve teklif mühürlü; dokunulmadı)."""
    from motor import geometry as G
    from motor import ifc_uret
    from araclar.paket import uret
    yeni, onceki = (json.loads(y.read_text(encoding="utf-8")) for y in (IE, IE_ONCEKI))
    assert yeni.pop("rehber") == {"oda_sirasi": ODA_SIRASI, "kubbe": "karkasli_pano"}
    assert yeni == onceki
    yeni = json.loads(IE.read_text(encoding="utf-8"))
    try:
        a, b = (ifc_uret.hazirla(copy.deepcopy(ie)) for ie in (yeni, onceki))
    finally:
        G.lento_ayarla({})
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
    ozet = lambda ie: [(r["grup"], r["kalem"], r["olcu"], r["adet"], r["birim"]) for r in uret.listeler(ie, ["ters"])["ters"]["satirlar"]]   # noqa: E731
    assert ozet(yeni) == ozet(onceki) and len(ozet(yeni)) == 136


def test_oda_sirasi_is_emrinden(d):
    """Oda adımları İş Emri'nin yazdığı sırada (Lokman 05:18:03): yatak odası 1, banyo, yatak odası 2, salon; hol en sonda (duvarları
    önceki odalarla kurulur). Kuralın kendi sırası (`oda_sirasi`: salon ikinci, banyo dördüncü) anahtarsız girdide kalır."""
    from motor import geometry as G
    from motor import ifc_uret
    from araclar.paket.rehber import veri
    assert [(r["ad"], r["step"]) for r in d["rooms"]] == [("Yatak odası 1", 2), ("Banyo", 3), ("Yatak odası 2", 4), ("Yaşama alanı", 5), ("Hol", 6)]
    assert [a.get("oda") for a in d["adimlar"][2:7]] == [r["id"] for r in d["rooms"]]
    assert d["rooms"][0]["metin"].startswith("Dizilim bu odanın arka sol köşesinden başlar.")
    assert d["rooms"][-1]["metin"].endswith("Dizilim bu odada kapanır.")
    try:
        odalar = [dict(o, acik=False) for o in ifc_uret.hazirla(json.loads(IE.read_text(encoding="utf-8")))["odalar"]]
    finally:
        G.lento_ayarla({})
    kural = veri.oda_sirasi(odalar, {"x": "min", "y": "max"})[0]
    assert kural == ["YATAK ODASI 1", "YAŞAMA ALANI", "YATAK ODASI 2", "BANYO", "HOL"] and sorted(kural) == sorted(ODA_SIRASI)


def test_kubbe_karkasli_pano(d, ek):
    """Kubbenin dört parçası karkaslı pano (Lokman 05:16:18, 05:18:47): üretim karkası (çubuk sayısı dosyadaki) ve iki yüzünde 8 mm
    fibercement. Açılı panolar tek kanat 59/170, karşıdaki 105/170. Aralarında listeden 4 özel açılı köşe direği ve 2 kubbe üstü H."""
    fr = {f["cerceve"]: f for f in json.loads(URETIM.read_text(encoding="utf-8"))}
    assert Counter(e["ad"] for e in ek[PANO]) == {f"{PANO} (59/170) · kubbe, soldaki açılı": 1, f"{PANO} (105/170) · kubbe, karşıdaki": 1,
                                                  f"{PANO} (59/170) · kubbe, sağdaki açılı": 1}
    assert [len(e["cubuk"]) for e in ek[PANO]] == [len(fr[a]["parcalar"]) for a in ("KUBBE-DUVAR1", "KUBBE-DUVAR2", "KUBBE-DUVAR3")]
    assert len(ek[UST]) == 1 and len(ek[UST][0]["cubuk"]) == len(fr["KUBBE-DUVAR4"]["parcalar"])
    for e in ek[PANO] + ek[UST]:
        s = dict(e["satir"])
        assert e["kap"]["f"] and s["Yapı"] == "çelik karkas, iki yüzünde 8 mm fibercement" and "listede satırı yok" not in s["Liste"]
    assert [dict(e["satir"])["Bu parça"] for e in ek[PANO] + ek[UST]] == [
        "karkaslı pano · KUBBE-DUVAR-1 · karkas 808 × 2030 mm", "karkaslı pano · KUBBE-DUVAR-2 · karkas 1270 × 2030 mm",
        "karkaslı pano · KUBBE-DUVAR-3 · karkas 808 × 2030 mm", "karkaslı pano · KUBBE-DUVAR-4 · karkas 2500 × 500 mm"]
    assert [dict(e["satir"])["Açıklık"] for e in ek[PANO]] == ["pencere 59/170 · tek kanat · alt kenar 13 cm", "pencere 105/170 · alt kenar 13 cm",
                                                              "pencere 59/170 · tek kanat · alt kenar 13 cm"]
    # kaplama pano gövdesinin boyunca (direkten direğe: karşıdaki pano 125,5 cm), 10 cm duvarın iki yüzünde 0,8 cm, 203 cm yüksek
    assert _kutu(ek[PANO][1]["kap"]) == [811.61, 135.36, 0, 821.61, 260.86, 203.0]
    assert sorted({round(v, 2) for v in ek[PANO][1]["kap"]["v"][0::3]}) == [811.61, 812.41, 820.81, 821.61]
    assert [_kutu(e["kap"])[:2] + _kutu(e["kap"])[3:5] for e in ek[PANO][::2]] == [[755.93, 72.61, 818.86, 135.54], [755.93, 260.68, 818.86, 323.61]]
    # köşe direği panoya değer: direğin kutusu panonun bittiği yerde başlar (kart modelinin çokgenleri motorun kubbesinden)
    assert sorted(_kutu(e["mesh"])[:2] + _kutu(e["mesh"])[3:5] for e in ek[DIREK]) == [[753.0, 72.61, 763.0, 79.68], [753.0, 316.54, 763.0, 323.61],
                                                                                    [811.61, 128.47, 821.61, 135.36], [811.61, 260.86, 821.61, 267.75]]
    assert len(ek[DIREK]) == 4 and all(e["mat"] == "post" and _kutu(e["mesh"])[2::3] == [0.0, 203.0] for e in ek[DIREK])
    assert [dict(e["satir"])["Liste"] for e in ek[DIREK]] == ["Özel açılı köşe direği + kapaması 100 × 100 × 2330 · 4 adet"] * 4
    assert len(ek[H]) == 2 and [dict(e["satir"])["Liste"] for e in ek[H]] == ["Kubbe üstü H 100 × 100 × 500 · 2 adet"] * 2
    assert [_kutu(e["mesh"]) for e in ek[H]] == [[752.8, 70.11, 200.0, 763.2, 75.11, 250.0], [752.8, 321.11, 200.0, 763.2, 326.11, 250.0]]
    # çıplak çelik kalmaz: eski adlarla (kaplamasız duvar ve bant) parça yok
    assert not [e for e in d["ek"] if e["ad"].startswith(("Kubbe duvarı", "Kubbe üst bandı"))]
    assert not [e for e in d["ek"] for k in ("kubbe_anahtar", "merkez", "kubbe_olcu", "order") if k in e]   # yardımcı anahtar veriye girmez
    assert sum(len(e["cubuk"]) for e in d["ek"] if e["ad"].startswith("Kubbe makası")) == sum(len(fr[a]["parcalar"]) for a in ("KMK14", "KMK15", "KMK16"))


def test_kubbe_salon_diziliminde_art_arda(d, ek):
    """Kubbenin parçaları salonun adımında, dizilimde art arda (Lokman 05:16:18, 05:45:38): 62,89'luk panodan sonra, dizilimin geldiği
    yandaki açılı panodan başlar; direk, pano, direk, karşıdaki pano, direk, öteki açılı pano, direk; kubbe üstü H, üstteki 50 cm'lik
    pano, öteki H; en son pencereler. Kubbeden sonra dizilim ön duvarla sürer."""
    salon = next(r for r in d["rooms"] if r["ad"] == "Yaşama alanı")
    kubbe = sorted((e for v in ek.values() for e in v if e["adim"] == salon["step"]), key=lambda e: e["sira"])
    assert [e["ad"] for e in kubbe] == KUBBE_DIZISI
    sira = [e["sira"] for e in kubbe]
    assert sira == list(range(sira[0], sira[0] + len(kubbe)))                  # arada başka parça yok
    oda = [p for p in d["panels"] + d["hs"] if p["step"] == salon["step"]]
    onceki = next(p for p in oda if p["order"] == sira[0] - 1)
    assert onceki["boy"] == 62.89 and not [p for p in oda if sira[0] <= p["order"] <= sira[-1]]
    assert len([p for p in oda if p["order"] > sira[-1]]) > 0 and max(p["order"] for p in oda) > sira[-1]
    # sağdaki açılı pano dizilimin geldiği yanda (veranda yanı, arka): planda y'si büyük olan
    ym = lambda e: sum(e["kap"]["v"][1::3]) / len(e["kap"]["v"][1::3])         # noqa: E731
    assert ym(kubbe[1]) > ym(kubbe[3]) > ym(kubbe[5])


def test_ustteki_pano_sahada_kesilir(d, ek):
    """Saha kesimi (Lokman 05:48:38, 05:49:31, 05:49:44, 05:53:37): kubbe panoları ve açılı köşe direkleri 203 cm, üstteki pano 50 cm.
    Usta yalnız üstteki panonun iki alt köşesini açılı keser; pano 3 cm iner (200–250), üstü duvar üstünde kalır. Kesim planda açılı
    panonun iç yüzü boyunca: iç yüzde 4,14 cm, dış yüzde 14,14 cm. Direk ve açılı pano kesilmez (203 cm tam). Uyarı adımın başında."""
    ust = ek[UST][0]
    v = ust["kap"]["v"]
    P = [(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)]
    assert _kutu(ust["kap"]) == [753.0, 72.61, 200.0, 763.0, 323.61, 250.0]
    alt = sorted({(x, y) for x, y, z in P if z == 200.0})                      # alt kenar (200 cm): uçlar kesik
    assert alt == [(753.0, 76.75), (753.0, 319.47), (753.8, 77.55), (753.8, 318.67), (762.2, 85.95), (762.2, 310.27), (763.0, 86.75), (763.0, 309.47)]
    assert {y for x, y, z in P if z == 250.0} == {72.61, 323.61}                # üst kenar tam boy
    assert {z for x, y, z in P} == {200.0, 203.0, 250.0}
    s = dict(ust["satir"])
    assert s["Yer"] == "düz duvarda kubbenin üstü; alt kenar 200 cm, üst kenar 250 cm"
    assert s["Saha kesimi"].startswith("iki alt köşe açılı kesilir: 3 cm yüksek") and s["Saha kesimi"].endswith("Açılı köşe direği ve açılı pano kesilmez")
    assert all(_kutu(e["kap"])[2::3] == [0.0, 203.0] for e in ek[PANO])
    assert all(dict(e["satir"])["Boy"] == "203 cm; sahada kesilmez" for e in ek[DIREK])
    m = next(r for r in d["rooms"] if r["ad"] == "Yaşama alanı")["metin"]
    assert m.startswith("DİKKAT: Kubbenin üstündeki 50 cm'lik panonun iki alt köşesini sahada açılı kesin. Pano 3 cm aşağı oturur; üstü 250 cm'de "
                        "kalır. Açılı köşe direklerini ve açılı panoları kesmeyin. Bu odayla ")
    assert m.endswith(" Kubbeyi bu odanın diziliminde, sırası gelince kurun. Kubbenin parçaları: 3 karkaslı pano, 4 özel açılı köşe direği, "
                      "üstteki 50 cm'lik pano ve 2 kubbe üstü H.")
    assert not [r for r in d["rooms"] if r["ad"] != "Yaşama alanı" and "DİKKAT" in r["metin"]]


def test_kubbe_sacak_omegasi_ve_tavan_alcipani(d, ek):
    """Kubbe panolarının üstünde saçak omegası (Lokman 06:08:55): 3 parça, saçak omegası adımında, kubbe duvarının üstünde (203 cm);
    kesit evin saçak omegasının ölçüleriyle (eskiz r03; dış dudak çizilmez). Kubbe tavanına alttan alçıpan (05:48:38), alçıpan adımında, üstteki panonun alt
    kenarında. İkisinin de listede satırı yok: parça kartı bunu yazar (liste mühürlü; dokunulmadı)."""
    S = d["S"]
    assert [(e["adim"], e["mat"]) for e in ek[OMEGA]] == [(S["omega"], "frame")] * 3
    assert [dict(e["satir"])["Bu parça"] for e in ek[OMEGA]] == [f"kubbede {y} panonun üstünde; kubbe saçağı buna oturur"
                                                                for y in ("soldaki açılı", "karşıdaki", "sağdaki açılı")]
    assert {dict(e["satir"])["Kesit"] for e in ek[OMEGA]} == {"üst 10 cm, iki yanda 3 cm kanat, içte 3 cm ayak; sac 1 mm"}
    for e in ek[OMEGA]:
        k = _kutu(e["mesh"])
        assert (k[2], k[5]) == (199.9, 203.1) and k[0] >= 763.0 - 0.1          # iç ayak 200'de, üst 203'te; düz duvarın dış yüzünde biter
        assert dict(e["satir"])["Liste"] == "listede satırı yok"
    assert max(_kutu(e["mesh"])[3] for e in ek[OMEGA]) == pytest.approx(821.71, abs=0.011)
    a = ek[ALCIPAN]
    assert len(a) == 1 and (a[0]["adim"], a[0]["mat"]) == (S["alcipan"], "alcipan")
    assert _kutu(a[0]["mesh"]) == [753.0, 76.75, 198.65, 811.61, 319.47, 199.9]
    assert dict(a[0]["satir"])["Liste"] == "listede satırı yok"
    om, al = (next(x for x in d["adimlar"] if x.get("ad") == ad) for ad in ("Saçak, duvar ve baş makas omegası", "Ters tavan alçıpanı"))
    assert om["p"].endswith(" Kubbenin panolarının üstüne de saçak omegası geçirin. Kubbe saçağı bu omegaya oturur.")
    assert [None, "Saçak omegası · kubbe", "3 parça", "model"] in om["rows"]
    assert al["p"].endswith(" Kubbenin tavanına alttan alçıpan takın. İçeriden bakınca çatı görünmez.")


def test_kubbe_penceresi_karkasin_boslugunda(ek):
    """Soru 21 (Lokman, 28 Kasım 2026 06:11:13 UTC, kart "13 cm"): kubbe penceresinin alt kenarı üretim dosyasındaki gibi 13 cm (kart
    modeli 30 cm çizer). Pencere karkasın boşluğunda: 13–183 cm; kaplamadaki boşluk aynı yerde."""
    from araclar.paket.rehber import ek as EKM
    fr = {f["cerceve"]: f for f in json.loads(URETIM.read_text(encoding="utf-8"))}
    bosluk = [EKM._pencere_boslugu(fr[a]) for a in ("KUBBE-DUVAR1", "KUBBE-DUVAR2", "KUBBE-DUVAR3")]
    assert bosluk == [pytest.approx(b, abs=0.001) for b in ((10.8, 70.0, 13.0, 183.0), (10.897, 116.097, 13.0, 183.0), (10.8, 70.0, 13.0, 183.0))]
    assert [round(b[1] - b[0], 1) for b in bosluk] == [59.2, 105.2, 59.2]      # 59/170 ve 105/170 pencerenin boşluğu
    dis = [EKM._cerceve_dis_olcusu(fr[a]) for a in ("KUBBE-DUVAR1", "KUBBE-DUVAR2", "KUBBE-DUVAR4")]   # karkasın gerçek dış ölçüsü
    assert dis == [pytest.approx(b, abs=0.001) for b in ((0.0, 80.8, 0.0, 203.0), (0.0, 126.993, 0.0, 203.0), (0.0, 250.0, 0.0, 50.0))]
    pen = ek["PVC pencere"]
    assert len(pen) == 3 and all(_kutu(e["mesh"])[2::3] == [13.0, 183.0] for e in pen)
    assert all(dict(e["satir"])["Bu parça"].endswith(" · alt kenar 13 cm") for e in pen)
    for e in ek[PANO]:                                                          # kaplamada boşluğun altı 13, üstü 183
        assert {13.0, 183.0} <= {round(z, 2) for z in e["kap"]["v"][2::3]}


def _hacim(m):
    """Üçgen ağın işaretli hacmi (cm³): yüzler dışa bakıyorsa artı."""
    v, f = m["v"], m["f"]
    P = [(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), 3)]
    t = 0.0
    for i in range(0, len(f), 3):
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = P[f[i]], P[f[i + 1]], P[f[i + 2]]
        t += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
    return t / 6


def test_yeni_parcalarin_yuzleri_disa_bakar(ek):
    """Sahne tek yüzlü malzeme kullanır; içe bakan yüz çizilmez. Kodun kurduğu her yeni ağın (kaplama, kubbe üstü H, saçak omegası,
    alçıpan) işaretli hacmi artıdır; kart modelinden gelen direklerinki gibi. Hacimler ölçüden: karşıdaki panonun kaplaması iki levha
    (125,5 × 203 cm − 105,2 × 170 cm boşluk) × 0,8 cm; H iki kanat levhası 5 × 0,2 × 50; alçıpan iç çokgenin alanı × 1,25 cm."""
    aglar = [e["kap"] for e in ek[PANO] + ek[UST]] + [e["mesh"] for e in ek[H] + ek[OMEGA] + ek[ALCIPAN] + ek[DIREK]]
    assert len(aglar) == 3 + 1 + 2 + 3 + 1 + 4 and all(_hacim(m) > 0 for m in aglar)
    assert _hacim(ek[PANO][1]["kap"]) == pytest.approx(2 * 0.8 * (125.5 * 203 - 105.2 * 170), rel=1e-3)
    assert [_hacim(e["mesh"]) for e in ek[H]] == [pytest.approx(2 * 5 * 0.2 * 50, rel=1e-6)] * 2
    ic_alan = (811.61 - 753.0) * ((319.47 - 76.75) + (260.86 - 135.36)) / 2    # iç çokgen yamuk: düz duvarda 242,72, karşıda 125,5, derinlik 58,61
    assert _hacim(ek[ALCIPAN][0]["mesh"]) == pytest.approx(ic_alan * 1.25, rel=1e-3)


def test_karkasli_kubbe_bilmedigi_evi_kurmaz():
    """Karkaslı kubbe yalnız sağ dış duvardaki kubbe için kurulur (63 m²): üstteki panonun kesimi ve omeganın uçları o duvara göre.
    Başka cephede, ya da İş Emri'ndeki kubbe penceresi üretim karkasının boşluğuna uymuyorsa rehber açık hatayla durur (K21)."""
    from motor import geometry as G
    from motor import ifc_uret
    from araclar.paket.rehber import ek as EKM
    try:
        HZ = ifc_uret.hazirla(json.loads(IE.read_text(encoding="utf-8")))
    finally:
        G.lento_ayarla({})
    FR = {f["cerceve"]: f for f in json.loads(URETIM.read_text(encoding="utf-8"))}
    kb = HZ["kubbeler"][0]
    ls = lambda ad: ad                                                          # noqa: E731
    assert len(EKM._kubbe_karkasli(HZ, copy.deepcopy(kb), FR, ls)[0]) == 3 + 1 + 2 + 3 + 1
    with pytest.raises(ValueError, match="yalnız sağ dış duvardaki kubbe için kurulur; bu evde kubbenin cephesi: sol"):
        EKM._kubbe_karkasli(HZ, dict(copy.deepcopy(kb), cephe="sol"), FR, ls)
    dar = copy.deepcopy(kb)
    dar["panolar"][0]["pencere"] = "40x120"
    with pytest.raises(ValueError, match=r"karkasın pencere boşluğu 592 × 1700 mm, İş Emri'ndeki kubbe penceresi 40x120 cm"):
        EKM._kubbe_karkasli(HZ, dar, FR, ls)


@pytest.mark.parametrize("rehber, hata", [
    ({}, "boş ya da sözlük değil"),
    ([], "boş ya da sözlük değil"),
    ({"oda_sira": ODA_SIRASI}, "bilinmeyen anahtar: oda_sira"),
    ({"oda_sirasi": ODA_SIRASI[:-1]}, "evin odalarını birer kez yazmalı"),
    ({"oda_sirasi": ODA_SIRASI + ["HOL"]}, "evin odalarını birer kez yazmalı"),
    ({"oda_sirasi": ODA_SIRASI[:-1] + ["MUTFAK"]}, "evin odalarını birer kez yazmalı"),
    ({"oda_sirasi": "HOL"}, "evin odalarını birer kez yazmalı"),
    ({"kubbe": "kapli"}, "`rehber.kubbe` 'kapli'; bilinen değer: karkasli_pano"),
])
def test_rehber_anahtari_denetlenir(rehber, hata):
    """Bilinmeyen anahtar ya da değer, eksik, fazla ya da yabancı oda rehberi kurdurmaz (K21): yanlış yazılan anahtar sessizce
    düşmez. Kubbesiz evde `kubbe` da öyle. Anahtarsız İş Emri'nde hiçbir seçim yok (eski yol)."""
    from araclar.paket.rehber import veri
    with pytest.raises(veri.Desteklenmiyor, match=hata):
        veri.rehber_anahtarlari({"rehber": rehber}, sorted(ODA_SIRASI), True)
    with pytest.raises(veri.Desteklenmiyor, match="evde kubbe yok"):
        veri.rehber_anahtarlari({"rehber": {"kubbe": "karkasli_pano"}}, ODA_SIRASI, False)
    assert veri.rehber_anahtarlari({}, ODA_SIRASI, True) == {}
    tam = {"oda_sirasi": ODA_SIRASI, "kubbe": "karkasli_pano"}
    assert veri.rehber_anahtarlari({"rehber": tam}, sorted(ODA_SIRASI), True) == tam


def test_kubbe_dizilimin_geldigi_yandan_baslar():
    """Lokman 05:45:38: "salonun duvar panolarını nereden dizmeye başlıyorsan o taraftan doğru dizmeye başlayacaksın". Kubbe, odanın
    başlangıç köşesine yakın açılı panodan başlar; köşe öteki yandaysa sıra tersine döner. Kubbe, ilk açılı panonun dizilimdeki
    yerine bütün olarak girer; eksik parça rehberi kurdurmaz."""
    from araclar.paket.rehber import veri
    KE = {k: [{"ad": k, "merkez": m}] for k, m in {"pano0": [30, 10], "pano1": [50, 50], "pano2": [30, 90], "direk1": [45, 25], "direk2": [45, 75],
                                                  "direk3": [5, 2], "direk4": [5, 98], "h0": [0, 0], "h2": [0, 100], "bant": [0, 50]}.items()}
    KE["pencere"] = [{"ad": "p0", "merkez": [30, 10]}, {"ad": "p2", "merkez": [30, 90]}, {"ad": "p1", "merkez": [50, 50]}]
    lst = [((0, y), 1, {"ad": f"duvar{y}"}) for y in (150, 120, 60, -20)]
    ad = lambda kose: [t[2]["ad"] for t in veri.kubbe_dizilimi(sorted(lst, key=lambda t: abs(t[0][1] - kose[1])), KE, kose)]   # noqa: E731
    assert ad((0, 150)) == ["duvar150", "duvar120", "direk4", "pano2", "direk2", "pano1", "direk1", "pano0", "direk3", "h2", "bant", "h0",
                            "p2", "p1", "p0", "duvar60", "duvar-20"]
    assert ad((0, -20)) == ["duvar-20", "direk3", "pano0", "direk1", "pano1", "direk2", "pano2", "direk4", "h0", "bant", "h2",
                            "p0", "p1", "p2", "duvar60", "duvar120", "duvar150"]
    with pytest.raises(veri.Desteklenmiyor, match="kubbenin parçası eksik: h2"):
        veri.kubbe_dizilimi(lst, {k: v for k, v in KE.items() if k != "h2"}, (0, 150))


@pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber denetimi: {iz.hazir()}")
def test_sahnede_kubbe(d, ek, tmp_path):
    """Sahnede (sayfanın izi): sayfa hatasız; 20 adım ve bitmiş bina, 439 parça (27 Kasım'daki 429 + 4 direk + 2 H + 3 saçak omegası +
    1 alçıpan). Karkaslı panoda kaplama çizilir (çubuklar ve kaplamanın üçgenleri). Salonun adımında kubbe art arda; adım yazısı
    uyarıyla başlar; saçak omegası adımının listesinde kubbe satırı."""
    from araclar.paket.rehber import sayfa
    z = iz.al(sayfa.yaz(d, tmp_path / "rehber.html"), tmp_path / "iz.json")
    assert z["hatalar"] == [] and (z["N"], z["parca"], len(z["adimlar"])) == (20, 439, 21)
    S = d["S"]
    salon = next(r for r in d["rooms"] if r["ad"] == "Yaşama alanı")["step"]
    ad = lambda p: p["ad"]                                                      # noqa: E731
    kubbe = sorted((p for p in z["parts"] if p["s"] == salon and (ad(p) in (UST, DIREK, H) or ad(p).startswith((PANO, "PVC pencere")))), key=lambda p: p["o"])
    assert [ad(p) for p in kubbe] == KUBBE_DIZISI
    for p, e in zip([p for p in kubbe if ad(p).startswith(PANO) or ad(p) == UST], sorted(ek[PANO] + ek[UST], key=lambda e: e["sira"])):
        assert p["ad"] == e["ad"] and p["n"] == len(e["kap"]["f"]) + 24 * len(e["cubuk"])
    assert Counter(ad(p) for p in z["parts"] if p["s"] == S["omega"])[OMEGA] == 3
    assert Counter(ad(p) for p in z["parts"] if p["s"] == S["alcipan"])[ALCIPAN] == 1
    assert z["adimlar"][salon]["p"].startswith("DİKKAT: Kubbenin üstündeki 50 cm'lik panonun iki alt köşesini sahada açılı kesin.")
    assert "Saçak omegası · kubbe" in z["adimlar"][S["omega"]]["satirlar"] and "3 parça" in z["adimlar"][S["omega"]]["satirlar"]
    assert "if (e.kap) g.add(ekMesh(e.kap, mat('pdis', e.adim)));" in (KOK / "araclar" / "paket" / "rehber" / "sahne.js").read_text(encoding="utf-8")
