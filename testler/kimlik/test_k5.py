"""İE-15 · K5 · İE-17'nin yeni çatı tipleri kart modelinde: cumbalı beşik (`besik_cumba`) ve kırma (`kirma`) (plan
`Kimlik_Karti_Modeli/K5_yeni_catilar_plani.md`; CIO onayı 27 Ekim 22:02, sıra ve dosya sınırı aynen).

- Kabul: İE-17'nin üç evi (`testler/cizim/evler/`; AP-13 ve AP-16 cumbalı beşik, AP-01 kırma) ve her birinin beşik ikizi (aynı İş Emri,
  `cati.tip` "besik", tipin alanı silinmiş). Çatıya bağlı olmayan kartlar (pano, H dışındaki parçalar, tavan omegası, elektrik, alt
  çerçeve, sabit paketler) ikizle aynı sayılır: adet, metre, kesim planı. Çatıya bağlı kartlar (eşlemesinde ya da kuralında
  `cati_tipleri` olan) 0; parçaları "kural yok", nedeninde çatının kodu ve okunur adı, `cati` alanında kodu.
- Liste: liste üreteci kırma ana çatıda liste yazmaz (`PL.ListeYazilmaz`); kart modelinin liste sütununda sayı yok ("yazılmaz", nedeni
  üretecinki), çatı kenarı kartları "kurulmadı". İkizde liste sütunu üretecin sayısı. Kör protokolü: gerçek liste açılmaz; kıyas liste
  üretecimizin çıktısıyla ve İE-17'nin İş Emri'siyle (CIO, 27 Ekim 22:02). İE-29: çıkıntısız çapraz cumbada (AP-13, AP-16) liste yazılır
  (makas planı paftayla kıyaslandı); kart modelinin liste sütunu üretecin sayısı, çatı kenarı kartları modelde yine "kurulmadı" (K6).
- Çizim ve Excel: yedi sayfa; çatı sayfalarında bugünkü IFC'nin beşik makasları çizilmez, yerine çatının adı ve nedeni; yedinci sayfada
  "kurulmadı" ve "liste yazılmaz", "≠" yok. Excel'de aynısı ve nedeni. Komut 1 döner (kural yok). Örnek ev AP-01 (kırma; İE-29'a kadar
  AP-13'tü, cumbada liste artık yazılıyor).
- BK-14'ün taşan verandası (TK-01): zemin kartsız (kapsam dışı); çatı yüzü ve alın dolgusu K5'te "kural yok"tu, K5b'de kartsız (çatının
  parçaları kartlı kuruldu; `test_k5b.py`).
- Beşikte de kuralı kurulmayan çatı kenarı kartı "kurulmadı" yazar (İE-15 K6'ya kadar trapez kaplamada mahya; şimdi mahya kuralı testte "kural yok"a çevrilir).
- PK-01'in K1–K3b'si değişmez: öteki test dosyaları aynen geçer (K5'te yalnız Değişiklik (K5)'te yazılı üç vaka değişti).
- İE-15 K6 (D-53; Lokman, 4 Kasım 2026 20:51): beşik + çıkıntısız çapraz cumbanın (AP-13, AP-16) çatısı kart modelinde kurulur
  (`motor/cati_capraz.py`; çatı kuralları ve MA-01/MA-02 eşlemesi "besik_cumba"da da, yavru makas MA-05). Bu dosyada cumbalı iki ev için
  "kural yok" ve "kurulmadı" beklentisi kalktı: çatıya bağlı kartlar kurulur, yerleşen adetle sayılanlar listeyle aynı, kural yok boş.
  Kırma (AP-01) aynen. TK-04'ün çatı kartları listeyle `test_k6.py`'de.
- İE-33 PR-2 (6 Kasım 2026; Lokman AP-01'in çizimini 21:23'te onayladı): iki ucu kırmada (AP-01) liste yazılır, makas planı paftadan
  (`testler/motor/test_ie33_kirma_liste.py`). Kart modelinin liste sütunu üretecin sayısı (nedeni yok), çatı kenarı kartları modelde yine
  "kurulmadı" (kırmanın kartları kart modelinin işi, ayrı). Bu dosyanın üç vakası buna göre değişti (`test_kirmada_liste_yazilir`,
  `test_komut_cizim`, `test_komut_excel`); "liste yazılmaz" çiziminin örneği `test_k3b.py`'de (PK-01 kırma: mahya y boyunca, liste yazılmaz).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import ifc_uret  # noqa: E402
from motor import kart_model as KM  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402
from motor.cati_prefabrik import TIP_ADI  # noqa: E402
from motor.yerlesim import cizim, girdi  # noqa: E402

EVLER = KOK / "testler" / "cizim" / "evler"
MOTOR_VERI = KOK / "testler" / "motor" / "veri"
TIP = {"AP13": "besik_cumba", "AP16": "besik_cumba", "AP01": "kirma"}
KIRMA = [e for e, t in TIP.items() if t == "kirma"]
CUMBA = [e for e, t in TIP.items() if t == "besik_cumba"]
CATI_KENARI = ("CK-01", "CK-02", "CK-03", "CK-04", "CK-05", "CK-06")


def _oku(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _ikiz(ie: dict) -> dict:
    t = copy.deepcopy(ie)
    t["cati"]["tip"] = "besik"
    for alan in ("cumbalar", "kirma_egimleri"):
        t["cati"].pop(alan, None)
    return t


def _model(ie: dict, klasor: Path, ad: str) -> dict:
    bugunku = klasor / f"{ad}.ifc"
    assert ifc_uret.uret(ie, bugunku)["sema_hatasi"] == 0
    return KM.kart_modeli(bugunku, klasor / f"{ad}_model.ifc", ie["cati"]["tip"], is_emri=ie, plan=ifc_uret.hazirla(ie), elektrik=True,
                          kenar=True)


def _catiya_bagli() -> set[str]:
    """Kartın eşlemesinde ya da yerleşim kuralında çatı tipi sınırı varsa çatıya bağlı (veri dosyalarından; burada liste yazılmaz)."""
    kartlar, yerlesim = _oku(KM.KARTLAR), _oku(KM.YERLESIM)
    out = set()
    for k in kartlar["kartlar"]:
        kural = k.get("yerlesim", {}).get("kural")
        if any(KM._cati_sinirlari(m, yerlesim) for m in k.get("bugunku_ifc", [])) or (kural and yerlesim["kurallar"][kural].get("cati_tipleri")):
            out.add(k["kod"])
    return out


@pytest.fixture(scope="module")
def evler(tmp_path_factory):
    d = tmp_path_factory.mktemp("k5")
    out = {}
    for ev in TIP:
        ie = _oku(EVLER / f"{ev}.json")
        assert ie["cati"]["tip"] == TIP[ev]
        out[ev] = {"ie": ie, "say": _model(ie, d, ev), "ikiz": _model(_ikiz(ie), d, f"{ev}_ikiz")}
    return out


def _sayilar(say: dict) -> dict:
    return {k["kod"]: (k["adet"], k.get("metre"), k.get("sabit"), json.dumps(say["kesim_plani"].get(k["kod"]), sort_keys=True))
            for k in say["kartlar"]}


# ----------------------------------------------------------------------------- kabul: çatıdan bağımsız katmanlar ikizle aynı
@pytest.mark.parametrize("ev", list(TIP))
def test_catiya_bagli_olmayan_kartlar_ikizle_ayni(evler, ev):
    bagli = _catiya_bagli()
    a, b = _sayilar(evler[ev]["say"]), _sayilar(evler[ev]["ikiz"])
    assert set(a) == set(b)
    assert {k: v for k, v in a.items() if k not in bagli} == {k: v for k, v in b.items() if k not in bagli}
    assert {k for k, v in b.items() if k not in bagli and v[0]} >= {"OM-01", "AC-01", "AC-02"}       # ikizde de kurulan katmanlar
    if TIP[ev] == "kirma":
        assert all(a[k][0] == 0 and a[k][3] == "null" for k in bagli), ev
    else:                                                                   # İE-15 K6 (D-53): çapraz cumbanın çatısı kurulur
        assert {k for k in bagli if a[k][0]} >= {"MA-01", "MA-02", "MA-05", "AS-01", "KP-02", "BT-01", "DR-01", "DR-02", "IZ-01", *CATI_KENARI}, ev
    assert {k for k in bagli if b[k][0]} >= {"MA-01", "MA-02", "AS-01", "DR-01", "DR-02", *CATI_KENARI}      # ikizde çatı kurulur


def test_catiya_bagli_kartlar():
    """Çatıya bağlı kartlar veri dosyalarından: makaslar, makasa göre ayrılan dış H'ler, K2'nin dört çatı katmanı, K3b'nin altı çatı kenarı;
    K5b'de tek kat panel (KP-02) ve yavru makas (MA-03); K5b-2'de çatı izolasyonu (IZ-01); İE-24'te cumba makası (MA-04, beşikte); K6'da
    çapraz cumbanın yavru makası (MA-05, beşik + cumbada), trapez sac (KP-03) ve trapez sac mahyası (CK-07; trapez çatıda CK-06'nın yerine,
    "kurulmadı" listesine trapez dışında girmez)."""
    assert _catiya_bagli() == {"MA-01", "MA-02", "H-01", "H-02", "H-04", "H-05", "H-08", "H-09", "AS-01", "KP-01", "BT-01", "DR-01", "DR-02",
                               "KP-02", "MA-03", "IZ-01", "MA-04", "MA-05", "KP-03", "CK-07", *CATI_KENARI}


@pytest.mark.parametrize("ev", KIRMA)
def test_kural_yok_catinin_adiyla(evler, ev):
    """Kırmada çatının parçaları "kural yok"; nedende kuralın çatı tipleri (K6'dan beri beşik ve beşik + cumba; D-53)."""
    tip, say = TIP[ev], evler[ev]["say"]
    assert say["cati_tipi"] == tip and say["yerlesim"]["cati_tipi"] == tip
    assert say["kural_yok"] and all(x.get("cati") == tip for x in say["kural_yok"])
    for x in say["kural_yok"]:
        assert f"İş Emri'nin çatısı \"{tip}\" ({TIP_ADI[tip]}); " in x["neden"]
        assert "yalnız \"besik\" (beşik), \"besik_cumba\" (beşik + cumba) çatıda" in x["neden"], x
        assert x["neden"].endswith(girdi.cati_sonra(tip))
    adlar = {x["parca"] for x in say["kural_yok"]}
    assert {"aşık", "çatı kaplaması", "baş makas betopanı", "dere ve iniş", "saçak omegası", "saçak sacı", "alın sacı", "baş makas Z'si",
            "C kapama", "mahya"} <= adlar
    assert not any("cati" in x for x in evler[ev]["ikiz"]["kural_yok"])    # ikizin kural yoku (kaplama yazılı değil, betopan) çatı tipinden değil


@pytest.mark.parametrize("ev", CUMBA)
def test_capraz_cumbada_kural_yok_yok(evler, ev):
    """İE-15 K6 (D-53): çıkıntısız çapraz cumbada çatının bütün parçaları kartlı kurulur; kural yok boş (bugünkü IFC'nin şeması `_model`'de)."""
    say = evler[ev]["say"]
    assert say["cati_tipi"] == say["yerlesim"]["cati_tipi"] == "besik_cumba"
    assert say["kural_yok"] == []


def test_cati_adi_ve_nedeni():
    assert [girdi.cati_adi(t) for t in ("besik", "besik_cumba", "kirma", "tek_egim")] == ["beşik", "beşik + cumba", "kırma", "tek_egim"]
    assert girdi.cati_disi("kirma", "aşık sırası", ["besik"]) == ("İş Emri'nin çatısı \"kirma\" (kırma); aşık sırası yalnız \"besik\" (beşik) "
                                                                  "çatıda; kırma çatıda prefabrik kitabında kural yok")
    assert girdi.cati_disi("tek_egim", "x", ["besik", "besik_cumba"]) == ("İş Emri'nin çatısı \"tek_egim\"; x yalnız \"besik\" (beşik), "
                                                                          "\"besik_cumba\" (beşik + cumba) çatıda; bugünkü IFC çatıyı hep beşik çizer")
    assert "İE-17 PR-1b, İE-15 K6" in girdi.cati_sonra("besik_cumba")


# ----------------------------------------------------------------------------- liste sütunu
@pytest.mark.parametrize("ev", [e for e, t in TIP.items() if t == "kirma"])
def test_kirmada_liste_yazilir(evler, ev):
    """İE-33 PR-2: iki ucu kırmada liste yazılır; kart modelinin liste sütunu üretecin sayısı, çatı kenarı kartları yine "kurulmadı"."""
    k, t = evler[ev]["say"]["kenar"], evler[ev]["ikiz"]["kenar"]
    Lk = PL.is_emrinden(copy.deepcopy(evler[ev]["ie"]))
    sk: dict = {}
    for x in Lk["satirlar"]:
        sk[x["kalem"]] = sk.get(x["kalem"], 0) + x["adet"]
    kalem_k = {c["kod"]: (c["liste"]["satirlar"] or [None])[0] for c in _oku(KM.KARTLAR)["kartlar"] if c["kod"] in k["liste"]}
    assert k["liste"] == {kod: (sk.get(ad, 0) if ad else None) for kod, ad in kalem_k.items()} and set(k["liste"]) == set(t["liste"])
    assert KM.LISTE_YAZILMAZ not in k["liste"].values() and "liste_yazilmaz" not in k
    assert k["kurulmadi"] == list(CATI_KENARI)
    L = PL.is_emrinden(_ikiz(evler[ev]["ie"]))                             # ikizde liste üretecinin sayısı (kör protokolü: gerçek liste açılmaz)
    satir = {}
    for x in L["satirlar"]:
        satir[x["kalem"]] = satir.get(x["kalem"], 0) + x["adet"]
    kalem = {c["kod"]: (c["liste"]["satirlar"] or [None])[0] for c in _oku(KM.KARTLAR)["kartlar"] if c["kod"] in t["liste"]}
    assert t["liste"] == {kod: (satir.get(ad, 0) if ad else None) for kod, ad in kalem.items()}
    assert t["liste"]["CK-05"] is None and all(isinstance(n, int) for kod, n in t["liste"].items() if kod != "CK-05")
    assert "liste_yazilmaz" not in t and "kurulmadi" not in t


@pytest.mark.parametrize("ev", CUMBA)
def test_cikintisiz_cumbada_liste_yazilir(evler, ev):
    """İE-29: çıkıntısız çapraz cumbada liste yazılır (üç evin makas planı paftayla kıyaslandı, IE-29.md); kart modelinin liste sütunu
    üretecin sayısı, nedeni yok. K6'dan beri (D-53) çatı kenarı kartları modelde kurulur ("kurulmadı" yok); yerleşen adetle sayılan çatı
    kartları listeyle aynı: makaslar (yavru makas MA-05, listede "Yavru makas · cumba"), tek kat panel, betopan, iniş."""
    k = evler[ev]["say"]["kenar"]
    L = PL.is_emrinden(copy.deepcopy(evler[ev]["ie"]))
    satir = {}
    for x in L["satirlar"]:
        satir[x["kalem"]] = satir.get(x["kalem"], 0) + x["adet"]
    kalem = {c["kod"]: (c["liste"]["satirlar"] or [None])[0] for c in _oku(KM.KARTLAR)["kartlar"] if c["kod"] in k["liste"]}
    assert k["liste"] == {kod: (satir.get(ad, 0) if ad else None) for kod, ad in kalem.items()}
    assert KM.LISTE_YAZILMAZ not in k["liste"].values() and "liste_yazilmaz" not in k
    assert "kurulmadi" not in k
    adet = {x["kod"]: x["adet"] for x in evler[ev]["say"]["kartlar"]}
    assert (adet["MA-01"], adet["MA-02"], adet["MA-05"], adet["KP-02"], adet["BT-01"], adet["DR-02"]) == (
        satir["Makas (baş) · ana çatı"], satir["Makas (orta) · ana çatı"], satir["Yavru makas · cumba"],
        sum(n for a, n in satir.items() if a.startswith("Tek kat çatı paneli")), satir["Baş makas betopanı"], satir["Metal dere inişi aparatı"])


# ----------------------------------------------------------------------------- komut: çizim ve Excel
@pytest.fixture(scope="module")
def komut(tmp_path_factory):
    d = tmp_path_factory.mktemp("k5_komut")
    ie = _oku(EVLER / "AP01.json")
    (d / "ikiz.json").write_text(json.dumps(_ikiz(ie), ensure_ascii=False), encoding="utf-8")
    return {"kod": KM.main([str(EVLER / "AP01.json"), str(d / "c"), "--kod", "AP01"]), "ikiz_kod": KM.main([str(d / "ikiz.json"), str(d / "i"), "--kod", "AP01"]),
            "c": d / "c", "i": d / "i"}


def test_komut_cizim(komut):
    import pymupdf
    assert komut["kod"] == 1
    metin = [" ".join(p.get_text().split()) for p in pymupdf.open(komut["c"] / "AP01_yerlesim_planlari.pdf")]
    ikiz = [" ".join(p.get_text().split()) for p in pymupdf.open(komut["i"] / "AP01_yerlesim_planlari.pdf")]
    assert len(metin) == len(ikiz) == 7
    notu = "Çatı: kırma (İş Emri'nde \"kirma\") Çatı parçaları kurulmadı (kural yok):"
    assert [notu in s for s in metin] == [False, True, True, True, True, False, True]
    assert all("Bugünkü IFC çatıyı beşik çizer; o makaslar sayılmaz, çizilmez." in metin[i] for i in (1, 2, 3, 4, 6))
    assert not any("Çatı:" in s for s in ikiz)
    assert "MAKAS_01 (baş)" in ikiz[1] and "MAKAS" not in metin[1].replace("MAKAS VE DERE", "")     # beşik makaslar çizilmez
    ikiz_makas = _makas_dolgusu(komut["i"] / "AP01_yerlesim_planlari.pdf")
    assert _makas_dolgusu(komut["c"] / "AP01_yerlesim_planlari.pdf") == [0] * 7 and ikiz_makas[1] and ikiz_makas[6]   # 2. ve 7. sayfa
    assert "baş makas yok" not in metin[2]
    liste = _oku(komut["c"] / "AP01_kart_sayim.json")["kenar"]["liste"]          # İE-33 PR-2: iki ucu kırmada liste yazılır
    for kod in ("AC-01", "AC-02"):
        assert f"model {_stok(komut, kod)} boy · liste {liste[kod]}" in metin[6]
    assert metin[6].count("model kurulmadı") == 6 and "C kapama model kurulmadı · listede yok" in metin[6]
    assert "liste yazılmaz" not in metin[6] and "Liste üreteci:" not in metin[6]
    for ad in ("saçak omegası", "saçak sacı", "alın sacı", "baş makas Z'si", "C kapama", "mahya"):
        assert f"Kurulmadı: {ad}: kırma çatı" in metin[6]
    for i, ad in ((1, "dere ve iniş"), (2, "baş makas betopanı"), (3, "aşık"), (4, "çatı kaplaması")):
        assert f"Kurulmadı: {ad}: kırma çatı" in metin[i], ad
    assert all("EKSİK" in s for s in metin)


def _makas_dolgusu(pdf: Path) -> list[int]:
    """Sayfa başına makas rengindeki dolgu sayısı (makaslar ve baş makas üyeleri `cizim.RENK["makas"]` ile çizilir)."""
    import pymupdf
    r = tuple(int(cizim.RENK["makas"][i:i + 2], 16) / 255 for i in (1, 3, 5))
    return [sum(1 for g in s.get_drawings() if g.get("fill") and all(abs(a - b) < 0.01 for a, b in zip(g["fill"], r)))
            for s in pymupdf.open(pdf)]


def _stok(komut, kod: str) -> int:
    return _oku(komut["c"] / "AP01_kart_sayim.json")["kesim_plani"][kod]["stok"]


def test_komut_excel(komut):
    from openpyxl import load_workbook
    ws = load_workbook(komut["c"] / "AP01_kart_katalogu.xlsx")["Alt çerçeve ve çatı kenarı"]
    satir = [[c.value for c in r] for r in ws.iter_rows()]
    ozet = {r[0]: (r[1], r[2]) for r in satir[satir.index(["Kart", "Model (kesim planı)", "Liste üreteci", None, None, None]) + 1:]}
    liste = _oku(komut["c"] / "AP01_kart_sayim.json")["kenar"]["liste"]          # İE-33 PR-2: iki ucu kırmada liste yazılır
    assert "Liste yazılmaz" not in ozet
    assert ozet == {"AC-01": (_stok(komut, "AC-01"), liste["AC-01"]), "AC-02": (_stok(komut, "AC-02"), liste["AC-02"]),
                    **{k: ("kurulmadı", "listede yok" if liste[k] is None else liste[k]) for k in CATI_KENARI}}
    wi = load_workbook(komut["i"] / "AP01_kart_katalogu.xlsx")["Alt çerçeve ve çatı kenarı"]
    assert not any(c.value in ("kurulmadı", "liste yazılmaz", "Liste yazılmaz") for r in wi.iter_rows() for c in r)


# ----------------------------------------------------------------------------- BK-14'ün taşan verandası
def test_tasan_veranda_siniflanir(tmp_path):
    """TK-01'in iki taşan verandası (BK-14): zemin kartsız (kapsam dışı, ana zemin gibi); çatı yüzü ve alın dolgusu K5'te "kural yok"tu,
    K5b'de kartsız: çatının parçaları (kaplama, aşık, yavru makas, betopan, kenarlar, dere ve iniş) kartlı kuruldu, bugünkü IFC'nin
    gösterimi sayılmaz (nedeni kart dosyasından). "Kural yok" kalmaz (K5'te 8: altı veranda parçası, tek kat kaplama, betopan)."""
    kartlar = _oku(KM.KARTLAR)
    say = _model(_oku(KOK / "testler" / "motor" / "veri" / "TK01.json"), tmp_path, "TK01")
    v = lambda alan: {x["parca"]: x["neden"] for x in say[alan] if x["parca"].startswith("VERANDA_")}
    zemin = next(k["neden"] for k in kartlar["kartsiz"] if "VERANDA_ZEMINI" in k.get("ad", ""))
    kab = next(k["neden"] for k in kartlar["kartsiz"] if k["sinif"] == "IfcRoof")
    yuz = next(k["neden"] for k in kartlar["kartsiz"] if "VERANDA_CATI_" in k.get("ad", ""))
    alin = next(k["neden"] for k in kartlar["kartsiz"] if "VERANDA_ALIN_" in k.get("ad", ""))
    assert v("kartsiz") == {"VERANDA_CATISI_1": kab, "VERANDA_CATISI_2": kab, "VERANDA_ZEMINI_1": zemin, "VERANDA_ZEMINI_2": zemin,
                            **{f"VERANDA_CATI_{i}_{j}": yuz for i in (1, 2) for j in (1, 2)}, "VERANDA_ALIN_1": alin, "VERANDA_ALIN_2": alin}
    assert "K5b" in yuz and "K5b" in alin and "Kapsam dışı" in zemin
    assert kartlar["kural_yok"] == [] and say["kural_yok"] == []


# ----------------------------------------------------------------------------- beşikte "kurulmadı"
def test_besikte_kurulmayan_kenar_karti(tmp_path, monkeypatch):
    """Beşikte de kuralı kurulmayan çatı kenarı kartı "kurulmadı" yazar: sayımda `kenar.kurulmadi`, yedinci sayfanın lejantında ve
    Excel'de; liste sütunu üretecin sayısı (beşikte liste yazılır). Sayılar değişmez. (İE-15 K6'ya, D-53, kadar bu durumu trapez kaplamada
    mahya veriyordu; trapez sac mahyası (CK-07) artık kurulduğu için mahya kuralı burada "kural yok"a çevrilir.)"""
    from motor.yerlesim import kenar as KE
    asil = KE.katman

    def mahyasiz(*a, **kw):
        s = asil(*a, **kw)
        return s | {"parcalar": [p for p in s["parcalar"] if p["kural"] != "mahya_yerlesimi"],
                    "kural_yok": s["kural_yok"] + [{"parca": KE.CATI_ADI["mahya_yerlesimi"], "sinif": "IfcCovering", "neden": "test: kurulmadı"}]}
    monkeypatch.setattr(KE, "katman", mahyasiz)
    (tmp_path / "pk01.json").write_text((MOTOR_VERI / "PK01.json").read_text(encoding="utf-8"), encoding="utf-8")
    assert KM.main([str(tmp_path / "pk01.json"), str(tmp_path / "c"), "--kod", "T"]) == 1
    say = _oku(tmp_path / "c" / "T_kart_sayim.json")
    assert say["kenar"]["kurulmadi"] == ["CK-06"] and "liste_yazilmaz" not in say["kenar"] and isinstance(say["kenar"]["liste"]["CK-06"], int)
    import pymupdf
    metin = " ".join(pymupdf.open(tmp_path / "c" / "T_yerlesim_planlari.pdf")[6].get_text().split())
    assert f"CK-06 Metal kiremit mahyası L 2800 model kurulmadı · liste {say['kenar']['liste']['CK-06']}" in metin
    assert metin.count("model kurulmadı") == 1 and "liste yazılmaz" not in metin and "Çatı:" not in metin
    from openpyxl import load_workbook
    ws = load_workbook(tmp_path / "c" / "T_kart_katalogu.xlsx")["Alt çerçeve ve çatı kenarı"]
    ozet = {r[0].value: r[1].value for r in ws.iter_rows() if r[0].value in ("AC-01", "CK-05", "CK-06")}
    assert ozet == {"AC-01": 9, "CK-05": "13.9002 m", "CK-06": "kurulmadı"}
