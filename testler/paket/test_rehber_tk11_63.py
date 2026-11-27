"""63 m² tek evin (TK-11) montaj rehberi main'deki koddan çıkar (BK-77, BK-84; 24–27 Kasım 2026).

Lokman, 24 Kasım 2026 06:51:52 UTC "1-5 evet" (5: 63 m² montaj rehberi). 07:35:17 UTC: "Montaj Rehberlerinde bundan sonra orjinal
üretim çizimleri dursun": kubbenin çelik karkası üretim dosyasından (`araclar/uretim/veri/kubbe.json`, BK-76).

25 Kasım 2026 21:14:35 UTC: "… çizdiğin rehber çatı hiç olmamış". 26 Kasım 05:38:00 UTC: "bunu montaj rehberi çatısı içinde makasları
yeniden üret doğru yerleşimde gerçek üretilecek makaslar olacak". BK-84 (D-159): çatının 14 makası üretim dosyasından
(`araclar/uretim/veri/makas_63m2/`; Lokman 05:53:56 UTC kart "A: Evet, böyle üretilsin"), Motor'un yerinde (D-154, D-156); veranda
makasları son ana makasa üst başlığın ucuyla değer (Soru 14 "B: Son ana makasa, paftadaki gibi", Soru 16 "A: Üretim dosyası aynı
kalsın"), kalkan betopanı makasın geçtiği yerde kesilir; aşık sıraları mahyadan (D-158); verandanın köşe kırması şablonun yüzü.

Hedef örnek (D-28 madde 2): çatı `testler/paket/veri/TK11_rehber_cati_beklenen.json`; Lokman, 27 Kasım 2026 06:04:25 UTC, kart "Soru 6:
63 m2 evin montaj rehberinde çatı böyle olsun mu?": "A: Onaylıyorum".
Girdi `araclar/paket/girdi/TK11_r02_cati.json`: onaylı teklifin İş Emri (r02) ve iki çatı anahtarı; liste ve teklif aynı kalır.

Rehberin bütünü (BK-85, D-160): `testler/paket/rehber_tk11_63/iz.json`, onaylanan sayfanın izi. Lokman, 27 Kasım 2026 21:42:26 UTC, kart
"Soru 18: 63 m2 evin montaj rehberi bu çatıyla son hâli olsun mu?": "A: Onaylıyorum". `test_rehberin_butunu_onayli_ornek` komutun
çıkardığı sayfanın izini bu dosyayla kıyaslar.
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
from araclar.paket.rehber import iz  # noqa: E402

IE = KOK / "araclar" / "paket" / "girdi" / "TK11_r02_cati.json"             # evin İş Emri: r02 + kısa makas yerleri (D-156) + aşık (D-158)
IE_R02 = KOK / "testler" / "teklif_formu" / "TK11_r02" / "is_emri.json"      # onaylı teklifin girdisi: 14 makas (D-154); değişmez
HEDEF = json.loads((KOK / "testler" / "paket" / "veri" / "TK11_rehber_cati_beklenen.json").read_text(encoding="utf-8"))
REHBER_IZI = KOK / "testler" / "paket" / "rehber_tk11_63" / "iz.json"         # rehberin bütünü (D-160): onaylanan sayfanın izi
IE_R01 = KOK / "testler" / "teklif_formu" / "TK11" / "is_emri.json"         # mühürlü r01: 13 makas
URETIM = KOK / "araclar" / "uretim" / "veri" / "kubbe.json"
MAKAS = KOK / "araclar" / "uretim" / "veri" / "makas_63m2" / "makas_63m2.json"
ANA, CUMBA, KISA, CAPRAZ = ["MK01", "MK02", "MK03", "MK04", "MK05", "MK14", "MK06"], ["MK13", "MK07"], ["MK12", "MK11", "MK10", "MK08"], ["MK09"]


def _kur(ie_yolu, tmp):
    from motor import geometry as G
    from araclar.paket import uret
    from araclar.paket.rehber import veri
    ie = json.loads(ie_yolu.read_text(encoding="utf-8"))
    L = uret.listeler(copy.deepcopy(ie), ["ters"])["ters"]
    uret.kart_modeli(copy.deepcopy(ie), tmp, "TK-11")
    try:
        return veri.kur(copy.deepcopy(ie), tmp / "kart", "TK-11", L["satirlar"], "TK-11")
    finally:
        G.lento_ayarla({})                               # lento modül durumudur (BK-23): öteki testlere sızmaz


@pytest.fixture(scope="module")
def d(tmp_path_factory):
    return _kur(IE, tmp_path_factory.mktemp("tk11_rehber"))


@pytest.fixture(scope="module")
def mk(d):
    return {e["uretim"]: e for e in d["ek"] if e.get("uretim")}


def _koseler(c):
    """Çubuğun sekiz köşesi (cm), gerçek kesitle: sırt eksenden `c[13]`, ağız kenarı öteki yanda `c[6] − c[13]`; ağız yönü `c[11]`
    (`sahne.js`'teki enine eksen w = n × d)."""
    (px, py, pz), (qx, qy, qz), en, der, (nx, ny), s, eks = c[0:3], c[3:6], c[6], c[7], c[8:10], c[11], c[13]
    L = math.dist((px, py, pz), (qx, qy, qz))
    dx, dy, dz = (qx - px) / L, (qy - py) / L, (qz - pz) / L
    wx, wy, wz = ny * dz, -nx * dz, nx * dy - ny * dx
    return [(x + wx * a + nx * t, y + wy * a + ny * t, z + wz * a) for a in (-s * eks, s * (en - eks))
            for x, y, z in ((px, py, pz), (qx, qy, qz)) for t in (-der / 2, der / 2)]


def test_is_emri_onayli_r02_ve_iki_cati_anahtari():
    """Evin İş Emri onaylı teklifin girdisidir (r02), iki çatı anahtarıyla: kısa makas yerleri paftadan (D-156, Soru 11) ve aşık
    sıraları mahyadan (D-158, Soru 12). Başka fark yok; r02 dosyası değişmez. Liste satır satır aynı: kalem, ölçü, adet, birim."""
    from araclar.paket import uret
    yeni, r02 = (json.loads(y.read_text(encoding="utf-8")) for y in (IE, IE_R02))
    bek = copy.deepcopy(r02)
    bek["cati"]["mahal_catilari"][0]["kisa_makas_yerleri_cm"] = [425.5, 512.75, 637.75, 762.75]
    bek["cati"]["asik_siralari"] = "mahyadan"
    assert yeni == bek and HEDEF["is_emri"] == "araclar/paket/girdi/TK11_r02_cati.json"
    ozet = lambda ie: [(r["grup"], r["kalem"], r["olcu"], r["adet"], r["birim"]) for r in uret.listeler(ie, ["ters"])["ters"]["satirlar"]]   # noqa: E731
    a, b = ozet(yeni), ozet(r02)
    assert a == b and len(a) == 136
    assert [r for r in a if r[1] == "Aşık"] == [r for r in b if r[1] == "Aşık"] and [r[3] for r in a if r[1] == "Aşık"] == [41]


def test_cati_makaslari_uretim_cercevelerinden(d, mk):
    """14 makas üretim dosyasından: her çerçevenin çubuk sayısı dosyadaki parça sayısı (toplam 328); şablon makası ve kart modelinin
    makas üçgeni çizilmez; hepsi makas adımında."""
    fr = {f["cerceve"]: f for f in json.loads(MAKAS.read_text(encoding="utf-8"))}
    assert sorted(mk) == sorted(fr) == sorted(ANA + CUMBA + KISA + CAPRAZ)
    assert all(len(mk[a]["cubuk"]) == len(fr[a]["parcalar"]) for a in mk)
    assert sum(len(e["cubuk"]) for e in mk.values()) == 328
    assert Counter(e["kod"] for e in mk.values()) == {"MA-01": 2, "MA-02": 5, "MA-04": 2, "MA-06": 4, "MA-07": 1}
    assert len({e["adim"] for e in mk.values()}) == 1
    adim = d["adimlar"][next(iter(mk.values()))["adim"]]
    assert adim["ad"] == "Çatı makasları" and "Çatıda 14 makas var" in adim["p"] and "MK01–MK14" in adim["p"]
    assert d["makas"] and all(m.get("uretim") for m in d["makas"])           # şablon makası çizilmez (`sahne.js`: mk.uretim)
    assert "if (mk.uretim) return;" in (KOK / "araclar" / "paket" / "rehber" / "sahne.js").read_text(encoding="utf-8")
    assert not [e for e in d["ek"] if e["mat"] == "truss" and e.get("mesh")]


def test_makas_cubugu_dudakli_c_80x45(mk):
    """Çubuk gerçek kesitle çizilir (Lokman, 26 Kasım 2026 08:14:15 UTC, kart: "A: Evet, 80 × 45, dudak 10"): kanat 4,5, sırt 8, dudak 1,
    sac 0,08 cm. Eksen üretim dosyasının vida hattıdır: sırttan 2,7 cm (dosyadaki 54'ün yarısı; makine dosyası değişmez). Ağız yönü
    dosyanın etiketinden."""
    fr = {f["cerceve"]: f for f in json.loads(MAKAS.read_text(encoding="utf-8"))}
    for a, e in mk.items():
        for c, p in zip(e["cubuk"], fr[a]["parcalar"]):
            assert c[6:8] == [4.5, 8.0] and c[11:] == [-1 if p["yon"] == "LABEL_NRM" else 1, 0.08, 2.7, 1.0], (a, p["ad"], c)
            assert (p["kesit"], p["sirt"], p["kanat"]) == ("C", 80.0, 54.0)      # makine dosyasındaki satır aynen
        assert dict(e["satir"])["Profil"] == "C kesit: sırt 80 mm, kanat 45 mm, dudak 10 mm, sac 0,8 mm"


def test_makas_yerleri_cati_tanimindan(d, mk):
    """Yer Motor'un çatı tanımından (D-154; Lokman 05:50:56 "sen motora uy …"): ana 7, cumba 2 (biri iç uçta), kısa 4, çapraz 1.
    Baş makas duvarın dış yüzünden 3,7 cm içeride (şablon), iç uç makası kalkan betopanına dayalı (duvar yüzü + 5,1)."""
    x = lambda a: mk[a]["cubuk"][0][0]                                       # noqa: E731
    assert [x(a) for a in ANA] == HEDEF["makaslar"]["ana_x"] == [3.7, 67.75, 193.25, 318.75, 444.25, 569.75, 633.8]
    assert [x(a) for a in CUMBA] == HEDEF["makaslar"]["cumba_x"] == [642.6, 759.3]
    assert [mk[a]["cubuk"][0][1] for a in KISA] == HEDEF["makaslar"]["kisa_y"] == [425.5, 512.75, 637.75, 762.75]   # paftadaki yerler (D-156)
    assert HEDEF["makaslar"]["uretim"] == {"ana": ANA, "cumba": CUMBA, "kisa": KISA, "capraz": CAPRAZ}
    for a in ANA + CUMBA:                                                    # düzlemi x = sabit
        assert {c[0] for c in mk[a]["cubuk"]} == {c[3] for c in mk[a]["cubuk"]} == {x(a)}
    ic = [m for m in d["makas"] if m.get("ic_uc")]
    assert [(m["uretim"], m["konum"]) for m in ic] == [("MK13", 642.6)]
    assert all(e["x1"] - e["x0"] >= 1 for e in d["izo"]["ek"])               # iç uç makasıyla duvar arasında izolasyon şeridi yok


def test_makasin_ustu_asik_oturma_yuzunde(d, mk):
    """Çerçevenin üst başlığının üstü rehberin aşık oturma yüzünde (duvar üstü 250 + 0,25 + topuk 10 = 260,25'ten eğimle). Ölçü üst
    başlığın alçak ucunda (beşikte iki üst başlık mahyada birbirini 0,8 cm geçer)."""
    def fark(ad, yuzey, tan):
        out = []
        for x0, y0, z0, x1, y1, z1, *_, eksen, _dudak in mk[ad]["cubuk"]:
            h = math.hypot(x1 - x0, y1 - y0)
            if h > 1 and abs(abs(z1 - z0) / h - tan) < 0.002:               # üst başlık: eğimi çatınınki
                x, y, z = (x0, y0, z0) if z0 < z1 else (x1, y1, z1)
                out.append(z + eksen * math.hypot(1, tan) - yuzey(x, y))     # sırt eksenden 2,7 cm dışarıda (vida hattı)
        return out

    def besik(R):
        return lambda x, y: 260.25 + (y - R["L"] if y <= R["M"] else R["R"] - y) * R["tan"]
    for ad, R in (("MK03", d["R"]["AN"]), ("MK06", d["R"]["AN"]), ("MK13", d["R"]["C1"])):
        f = fark(ad, besik(R), R["tan"])
        assert len(f) == 2 and max(abs(v) for v in f) < 0.05, (ad, f)
    V, E = d["R"]["V1"], d["yuz"]["M1"]["E"][0]                            # veranda yüzü makaslarla birlikte kayık (saçak çizgisi 794,24)
    for ad in KISA:
        f = fark(ad, lambda x, y: 260.25 + (E - x) * V["tan"], V["tan"])
        assert len(f) == 1 and abs(f[0]) < 0.05, (ad, f)


def test_veranda_makaslari_son_ana_makasa_ust_baslik_ucuyla_deger(d, mk):
    """Soru 14 (Lokman, 26 Kasım 2026 23:33:13 UTC, kart "B: Son ana makasa, paftadaki gibi") ve Soru 16 (27 Kasım 2026 06:03:53 UTC, kart
    "A: Üretim dosyası aynı kalsın"; kartın sonucu: "Makas 0,9 cm geride durur; ana makasa üst başlığın ucuyla değer. Alt başlıkta 0,9 cm
    boşluk kalır."): 4 kısa makas ve çapraz makas son ana makasın yüzüne (637,8) üst başlığın ucuyla değer, içine girmez. Çerçeve
    üretim dosyasındaki boyda (155,5 ve 179,9 cm); alt başlığın ucu yüzden 0,94 cm geride."""
    yuz = mk["MK06"]["cubuk"][0][0] + 4.0                                    # son ana makasın verandaya bakan yüzü
    assert yuz == 637.8 and max(p[0] for c in mk["MK06"]["cubuk"] for p in _koseler(c)) <= yuz + 1e-6
    for a in KISA + CAPRAZ:
        dy = mk[a]["dayanak"]
        assert dy == HEDEF["dayanak"][a] and dy["yuz"] == yuz
        assert abs(min(p[0] for c in mk[a]["cubuk"] for p in _koseler(c)) - yuz) < 0.01, a      # değer: ne boşluk ne çakışma
        assert "Üst başlığın ucu ana makasa değer. Alt başlık ile ana makas arasında 0,9 cm boşluk kalır." in dict(mk[a]["satir"])["Dayanak"]
    assert {(mk[a]["dayanak"]["kayma"], mk[a]["dayanak"]["tasma"]) for a in KISA} == {(1.238, 0.938)}
    assert (mk["MK09"]["dayanak"]["kayma"], mk["MK09"]["dayanak"]["tasma"]) == (1.581, 0.905)
    alt = lambda a: next(c for c in mk[a]["cubuk"] if c[2] == c[5] and abs(c[1] - c[4]) < 1e-9 and c[2] < 255)       # noqa: E731
    assert [(alt(a)[0], alt(a)[3]) for a in KISA] == [(638.74, 794.24)] * 4                # alt başlık 155,5 cm; ucu yüzden 0,94 cm geride
    assert dict(mk["MK12"]["satir"])["Bu parça"] == "MK12 · alt başlık 1555 mm · 11 çubuk"
    assert dict(mk["MK09"]["satir"])["Bu parça"] == "MK09 · alt başlık 1799 mm · 11 çubuk"


def test_kalkan_betopani_makasin_gectigi_yerde_kesilir(d):
    """Soru 14 (B): betopan veranda makaslarının geçtiği yerde 8 cm kesilir (alttan makasın üstüne kadar). 4. kısa makas ile çapraz
    makasın kesimi arasında 5,9 cm şerit kalır; makasın eninden (8 cm) dar şerit bırakılmaz, iki kesim tek kesimdir: 17,75 cm
    (koordinatör, 27 Kasım 2026 00:15 UTC: not Lokman'a yazıldı; Soru 6 onayında itiraz yok). Kesim yalnız ana çatının sağ kalkanında."""
    yar = {k["ad"]: k.get("yarik") for k in d["kalkan"]}
    assert yar == {"ana çatı sol kalkanı (MKS01)": None, "sağ cumba sağ kalkanı (MKS09)": None, "ana çatı sağ kalkanı (MKS07)": HEDEF["kesimler"]}
    assert HEDEF["kesimler"] == [[421.5, 429.5, 291.36, "MK12"], [508.75, 516.75, 291.36, "MK11"], [633.75, 641.75, 291.36, "MK10"],
                                 [758.75, 776.5, 291.36, "MK08 + MK09"]]
    assert [round(b - a, 2) for a, b, *_ in HEDEF["kesimler"]] == [8.0, 8.0, 8.0, 17.75]


def test_veranda_catisi_sablonun_yuzu(d):
    """Köşe kırması şablonun yüzü: aşık sıraları kart modelinden (4 sıra), levha boyu listeden; kart modelinin aşık ve kaplama üçgeni
    çizilmez. Dere ve iniş kart modelinden, rehberin kotunda (kart modeli 9,75 cm yukarıda çizer)."""
    Y, R, V = d["yuz"]["M1"], d["R"]["V1"], HEDEF["veranda_yuzu"]
    assert Y["R"] == "V1" and R == V["R"] == {"L": 0, "R": 311.28, "M": 155.64, "tan": 0.2}
    # yüz üretim makaslarıyla birlikte 1,24 cm saçağa doğru (Motor'un saçak çizgisi 793): aşık makasın üst başlığına oturur
    assert Y["ad"] == "veranda çatısı yüzü" and Y["eksen"] == "y" and Y["d"] == [-1, 0] and Y["E"] == V["E"] == [794.24, 0]
    assert Y["serit"] == V["serit"] == {"ad": "L 1690 (veranda çatısı)", "bas": 865.75, "son": 326.83, "yon": -1}
    assert Y["poly"] == V["poly"] == [[638.6, 771.08], [795.54, 866.54], [795.54, 422.29], [638.6, 326.83]]   # yüksek kenar kalkan betopanında
    assert not [e for e in d["ek"] if e["ad"] in ("Aşık (omega)", "Trapez sac")]
    dere = [e for e in d["ek"] if e["ad"] == "Metal dere"]
    assert len(dere) == 1 and max(dere[0]["mesh"]["v"][2::3]) == 260.25
    assert [min(dere[0]["mesh"]["v"][0::3]), max(dere[0]["mesh"]["v"][0::3])] == V["dere_x"] == [794.24, 809.24]   # dere makasın saçak ucunda
    assert len([e for e in d["ek"] if e["ad"] == "Metal dere inişi"]) == 2


def test_asik_siralari_mahyadan(d):
    """D-158 (Soru 12, Lokman 26 Kasım 2026 23:34:15 UTC, kart "A: Yalnız bu evde mahyadan"): 4 yüzde 26 sıra (paftadaki gibi; anahtarsız
    27). Her yüzde ilk sıra üst kenarda; sıraların saçaktan uzaklığı çatı tanımından (kart modeli). Adım yazısı kuralı söyler."""
    assert d["asik"]["yuzler"] == HEDEF["asik"]
    assert {k: len(v["sira"]) for k, v in d["asik"]["yuzler"].items()} == {"Y1": 4, "Y2": 9, "Y3": 9, "M1": 4}
    assert d["asik"]["yuzler"]["M1"] == {"sira": [4.44, 38.58, 98.58, 154.14], "pafta": [[410.0, 34.25]] * 4, "bas": "max"}
    p = next(a for a in d["adimlar"] if a.get("ad") == "Aşıklar")["p"]
    assert "her yüzde ilk sıra yüzün üst kenarında (mahya), sonra 60 cm arayla aşağı, saçakta bir sıra, 4 yüzde 26 sıra" in p


def test_kubbe_uretim_cercevelerinden(d):
    """Kubbenin 3 duvarı, üst bandı ve 3 makası üretim dosyasından; her çerçevenin çubuk sayısı dosyadaki parça sayısı."""
    fr = json.loads(URETIM.read_text(encoding="utf-8"))
    kb = [e for e in d["ek"] if e["ad"].startswith(("Kubbe duvarı", "Kubbe üst bandı", "Kubbe makası"))]
    assert len(kb) == 7
    assert sorted(len(e["cubuk"]) for e in kb) == sorted(len(f["parcalar"]) for f in fr)
    duvar = {e["adim"] for e in kb if not e["ad"].startswith("Kubbe makası")}
    assert len(duvar) == 1                                # kubbe duvarları ve bandı kubbenin odasının adımında


def test_osb_adimi(d):
    """İş Emri OSB yazar: OSB ve nem bariyeri adımı aşıklardan sonra, saçak sacından önce; verandanın yüzü de şablonun yüzü olduğu için
    OSB'lidir (her yüzde bir levha)."""
    ad = [a.get("ad") for a in d["adimlar"]]
    i = ad.index("OSB ve nem bariyeri")
    assert ad[i - 1] == "Aşıklar" and ad[i + 1] == "Saçak sacı"
    assert d["kaplama"]["osb"] == {"kal": 1.1, "nem": 0.05}
    assert sorted(d["yuz"]) == ["M1", "Y1", "Y2", "Y3"]


def test_13_makasli_is_emri_rehber_kurmaz(tmp_path):
    """Mühürlü r01 İş Emri 13 makas sayar (cumbada 1); üretim dosyasında cumbanın 2 makası var. Sayı tutmazsa rehber kurulmaz (yok
    sayılmaz): rehber 14 makaslı İş Emri'nden üretilir."""
    from araclar.paket.rehber import veri
    with pytest.raises(veri.Desteklenmiyor, match="üretim dosyasında 2 cumba makası, çatı tanımında 1"):
        _kur(IE_R01, tmp_path)


def test_cati_anahtarsiz_r02_rehber_kurmaz(tmp_path):
    """Onaylı teklifin İş Emri (r02) aynı numarayı taşır ama iki çatı anahtarını yazmaz: kısa makaslar eşit aralıkta kalır, ilk veranda
    makası cumba makaslarını keser (Lokman'ın reddettiği yerleşim). Evin kaydı anahtarları ister; rehber kurulmaz (yanlış çatıyla
    çıkmaz): rehber `araclar/paket/girdi/TK11_r02_cati.json`'dan üretilir."""
    from araclar.paket.rehber import ek, veri
    kayit = json.loads(ek.MAKAS_KAYDI.read_text(encoding="utf-8"))["evler"]["PM-TK11-63M2"]["cati_anahtarlari"]
    assert (kayit["cati"], kayit["mahal_catilari"]) == (["asik_siralari"], ["kisa_makas_yerleri_cm"])
    with pytest.raises(veri.Desteklenmiyor, match="asik_siralari, kisa_makas_yerleri_cm yazan İş Emri'nden kurulur"):
        _kur(IE_R02, tmp_path)


@pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber denetimi: {iz.hazir()}")
def test_sahnede_makaslar_ve_veranda(d, tmp_path):
    """Sahnede (sayfanın izi): makas adımında 14 üretim makası ve kubbenin 3 makası, şablon makası yok; verandanın yüzünde 8 aşık parçası,
    listedeki 5 levha (L 1690), OSB ve nem bariyeri; sayfa hatasız."""
    from araclar.paket.rehber import sayfa
    z = iz.al(sayfa.yaz(d, tmp_path / "rehber.html"), tmp_path / "iz.json")
    assert z["hatalar"] == []
    S = d["S"]
    makas = Counter(p["ad"].split(" · ")[0] for p in z["parts"] if p["s"] == S["makas"])
    assert makas == {"Makas (baş)": 2, "Makas (orta)": 5, "Cumba makası": 2, "Kısa makas (köşe kırması)": 4, "Çapraz makas (köşe kırması)": 1,
                     "Kubbe makası": 3}
    assert not [p for p in z["parts"] if p["s"] == S["makas"] and any(s[0] == "İç çubuklar" for s in p["satir"])]
    ver = Counter((p["s"], p["ad"]) for p in z["parts"] if any(s[0] == "Bu parça" and s[1].startswith("veranda çatısı yüzü") for s in p["satir"]))
    assert ver[(S["asik"], "Aşık (omega)")] == 8
    assert ver[(S["kaplama"], "Trapez sac L 1690 (veranda çatısı)")] == 5    # liste: Trapez sac · VERANDA çatısı L 1690 · 5 adet
    assert ver[(S["osb"], "OSB 11 mm")] == 1 and ver[(S["osb"], "Nem bariyeri")] == 1
    assert sum(1 for p in z["parts"] if p["s"] == S["asik"] and p["ad"] == "Aşık (omega)") == 48   # kart modelinin aşık parçaları (D-158)
    bet = [p for p in z["parts"] if p["s"] == S["kalkan"] and any(s[0] == "Kesim" for s in p["satir"])]
    kesim = sorted(dict(p["satir"])["Kesim"] for p in bet)                   # 4 kesim, 3 levhada (ilk levhada iki kesim)
    assert len(kesim) == 3 and all(k.endswith(": veranda makasının geçtiği yer") for k in kesim)
    assert kesim[0].startswith("421,5–429,5 cm arası alttan 44,36 cm (MK12); 508,75–516,75 cm arası alttan 44,36 cm (MK11)")
    assert kesim[2].startswith("758,75–776,5 cm arası alttan 44,36 cm (MK08 + MK09)")


@pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber izi: {iz.hazir()}")
def test_rehberin_butunu_onayli_ornek(tmp_path):
    """D-160 (D-28 madde 2 ve 3): rehberin bütünü Lokman'ın onayladığı sayfadır (27 Kasım 2026 21:42:26 UTC, kart "Soru 18: 63 m2 evin
    montaj rehberi bu çatıyla son hâli olsun mu?": "A: Onaylıyorum"). Komut (`python -m araclar.paket TK-11 <çıktı> --is-emri
    araclar/paket/girdi/TK11_r02_cati.json --tavan ters`) sayfayı yazar; sayfanın izi (her parçanın adımı, sırası, kartı, yazısı ve
    köşeleri; adımların metni, satırları ve kamerası) onaylanan sayfanın iziyle aynıdır. İz yalnız Lokman'ın onayıyla yeniden alınır
    (D-02; `testler/paket/rehber_tk11_63/README.md`)."""
    from motor import geometry as G
    from araclar.paket import uret
    try:
        assert uret.main(["TK-11", str(tmp_path / "Modeller"), "--is-emri", str(IE), "--tavan", "ters", "--gecici", str(tmp_path / "gecici")]) == 0
    finally:
        G.lento_ayarla({})                               # lento modül durumudur (BK-23): öteki testlere sızmaz
    klasor = tmp_path / "Modeller" / "prefabrik" / "TK-11"
    html = klasor / "TK-11_montaj_rehberi.html"
    assert html.is_file(), (klasor / "TK-11_bilgi.md").read_text(encoding="utf-8")
    a = json.loads(REHBER_IZI.read_text(encoding="utf-8"))
    b = iz.al(html, tmp_path / "iz.json")
    assert a["hatalar"] == [] and b["hatalar"] == []
    assert (a["N"], a["parca"], len(a["adimlar"])) == (20, 429, 21)        # 20 adım ve bitmiş bina; 429 parça
    for k in ("N", "liste", "ilerleme", "parca"):
        assert a[k] == b[k], k
    fark = [(i, {k: (x[k], y.get(k)) for k in x if x[k] != y.get(k)}) for i, (x, y) in enumerate(zip(a["parts"], b["parts"])) if x != y]
    assert not fark, f"{len(fark)} parça farklı; ilk: {fark[:3]}"
    fark = [(x["i"], k) for x, y in zip(a["adimlar"], b["adimlar"]) for k in x if x[k] != y.get(k)]
    assert not fark, f"adımlarda fark: {fark[:10]}"
    assert a == b                                        # izin bütünü
