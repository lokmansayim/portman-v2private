"""İE-15 · K5b · Gövdeden taşan verandanın çatısı (BK-14), tek kat çatı paneli ve dikey baş makas betopanı (plan
`Kimlik_Karti_Modeli/K5_yeni_catilar_plani.md`; CIO onayı 27 Ekim 23:11).

- Kabul (TK-01, `testler/motor/veri/TK01.json`): kart modeli ile liste üreteci yan yana. K5'teki sekiz farkın veranda çatısından gelen
  yedisinde beşi K5b-1'de kapandı (CK-02, CK-03, CK-06, DR-01, DR-02); AS-01, BT-01 ve veranda kalkanının Z'si (CK-04) liste PR'ında
  (İE-09 hattının arkasında; CIO onayı 30 Ekim 14:20): aşık sırası beşikte karar C, tek koddan (`prefabrik_liste.asik_mesafeleri`); baş makas
  betopanı ve Z kirişli veranda kalkanında da (D-32 madde 2). Saçak omegası (CK-01) saçak ucundan ucuna, liste gibi (Lokman, 31 Ekim 13:40
  "gerçek listeye uy": gerçek PK-01, PK-02, PK-03 listeleri saçak boyuyla tutuyor; K3b'deki fark kapandı). On dört kalem aynı. "Kural yok" 0
  (K5'te 8). OM-01 veranda çatısından değil (kapsam dışı).
- Kör protokolü: gerçek liste açılmaz; kıyas liste üretecimizin çıktısıyla (CIO, 27 Ekim 22:02).
- Kural birimleri: kaplamanın okunması (sandviç, tek kat, varsayılan tek kat ve uyarı, trapez ve kiremit "kural yok"); taşan veranda
  kaplaması iki yüz birlikte (⌈2 × mahya boyu ÷ kapatma⌉, artanlar bir panele sığarsa bir panelden, sığmazsa duvarda kesilir); dikey
  betopan (H5 sayısı, levhalar örtüşmez, artan uçları kapatır, uç en dıştaki levhanın); dere kesimi hatlar arasında (PK-01 6, TK-01 7);
  yavru makas (J8 sayısı, ilki dış kirişte, sonuncusu duvar dibinde); tek yön ve çapraz veranda çatısı "kural yok" (K6).
- Adlar: veranda parçaları `VERANDA_` önekli, kendi sırasıyla; ana çatının adları değişmez (montaj rehberi ana çatıyı adıyla okur).
- Çizim: yavru makas makas planında, veranda kalkanı betopan sayfasında, tek kat panel kaplama sayfasında, kenar notu yedinci sayfada.
- PK-01 değişmez (öteki test dosyaları; burada yeni kartlar 0).
"""
from __future__ import annotations

import copy
import json
import math
import re
import sys
from pathlib import Path

import ifcopenshell
import pytest
from shapely.geometry import Polygon
from shapely.ops import unary_union

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor import ifc_uret  # noqa: E402
from motor import kart_model as KM  # noqa: E402
from motor import prefabrik_liste as PL  # noqa: E402
from motor import yerlesim as Y  # noqa: E402
from motor.yerlesim import cati, kenar, kesim, veranda  # noqa: E402

MOTOR_VERI = KOK / "testler" / "motor" / "veri"
TK01 = MOTOR_VERI / "TK01.json"
ESIT = ("MA-01", "MA-02", "MA-03", "KP-02", "DR-01", "DR-02", "CK-01", "CK-02", "CK-03", "CK-04", "CK-06", "SR-01", "AS-01", "BT-01")


def _oku(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


class _Liste:
    """Liste üretecinin satırları; kartın listedeki adıyla (montaj rehberinin eşlemesi: ek yazı " (…)" ya da " · çatı" eşlemeyi bozmaz)."""
    def __init__(self, ie: dict):
        self.satirlar = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]

    def __getitem__(self, ad: str) -> list[dict]:
        return [x for x in self.satirlar if x["kalem"] == ad or x["kalem"].startswith((ad + " (", ad + " ·"))]


def _metre(formul: str, ad: str) -> float:
    return float(re.search(rf"{ad} ([\d,]+) m", formul).group(1).replace(",", "."))


@pytest.fixture(scope="module")
def tk01(tmp_path_factory):
    d = tmp_path_factory.mktemp("k5b")
    assert KM.main([str(TK01), str(d), "--kod", "TK01"]) == 0                  # kural yok yok: komut 0
    ie = _oku(TK01)
    return {"ie": ie, "say": _oku(d / "TK01_kart_sayim.json"), "klasor": d, "liste": _Liste(ie)}


def _katmanlar(ie: dict, klasor: Path, ad: str) -> dict:
    bugunku = klasor / f"{ad}.ifc"
    assert ifc_uret.uret(ie, bugunku)["sema_hatasi"] == 0
    return Y.katmanlar(ie, ifc_uret.hazirla(ie), KM.makaslar(ifcopenshell.open(str(bugunku)), KM._Kutular()), _oku(KM.YERLESIM),
                       _oku(KM.LISTE_KURALLARI))


@pytest.fixture(scope="module")
def tk01_k(tmp_path_factory):
    return _katmanlar(_oku(TK01), tmp_path_factory.mktemp("k5b_k"), "TK01")


def _parcalar(say: dict, kod: str, cati_: str | None = "*") -> list[dict]:
    return [p for p in say["yerlesim"]["parcalar"] + say["kenar"]["parcalar"] if p["kart"] == kod and (cati_ == "*" or p["bilgi"].get("Cati") == cati_)]


# ----------------------------------------------------------------------------- kabul: TK-01'de model ile liste
def test_tk01_kural_yok_yok(tk01):
    say = tk01["say"]
    assert say["kural_yok"] == [] and say["sema_hatasi"] == {"bugunku_ifc": 0, "kart_modeli": 0}
    assert {p["bilgi"].get("Cati") for p in say["yerlesim"]["parcalar"]} == {None, "ÖN VERANDA", "ARKA VERANDA"}
    assert [u for u in say["yerlesim"]["uyarilar"] if u["katman"] == "çatı kaplaması"] == [
        {"katman": "çatı kaplaması", "metin": "İş Emri'nin çatı kaplaması \"yazılı değil\"; tek kat panel sayıldı (liste üreteciyle aynı okuma)"}]


def test_tk01_model_liste_ile_ayni(tk01):
    """Veranda çatısından gelen farklar kapandı: makaslar, yavru makas, kaplama, aşık, betopan ve Z listeyle aynı; saçak omegası da (saçak boyu)."""
    say, L = tk01["say"], tk01["liste"]
    kartlar = {k["kod"]: k for k in _oku(KM.KARTLAR)["kartlar"]}
    model = {k["kod"]: say["kesim_plani"][k["kod"]]["stok"] if k["kod"] in say["kesim_plani"] else k.get("sabit", k["adet"]) for k in say["kartlar"]}
    liste = {kod: sum(s["adet"] for s in L[kartlar[kod]["liste"]["satirlar"][0]]) for kod in ESIT}
    assert {k: model[k] for k in ESIT} == {k: liste[k] for k in ESIT}
    assert {k: model[k] for k in ESIT} == {"MA-01": 2, "MA-02": 6, "MA-03": 5, "KP-02": 29, "DR-01": 7, "DR-02": 10, "CK-01": 11, "CK-02": 12,
                                           "CK-03": 13, "CK-04": 12, "CK-06": 6, "SR-01": 7, "AS-01": 52, "BT-01": 10}
    assert [(s["kalem"], s["adet"]) for s in L["Yavru makas"]] == [("Yavru makas · ön veranda çatısı", 3), ("Yavru makas · arka veranda çatısı", 2)]
    assert {(p["bilgi"]["Cati"], p["bilgi"]["MakasAdedi"]) for p in _parcalar(say, "MA-03")} == {("ÖN VERANDA", 3), ("ARKA VERANDA", 2)}
    assert [s["adet"] for s in L["Tek kat çatı paneli"]] == [20, 5, 4]
    assert [len(_parcalar(say, "KP-02", c)) for c in (None, "ÖN VERANDA", "ARKA VERANDA")] == [20, 5, 4]


def test_tk01_asik_sirasi_tek_koddan(tk01):
    """AS-01: listenin ve modelin sıraları aynı koddan (karar C: mahyadan 60, saçakta bir sıra; `prefabrik_liste.asik_mesafeleri`). Her çatıda
    modelin sıraları o işlevin verdiği uzaklıklar, saçak eşiği liste kuralından (`asik_sacak_esigi_m`, 0,30 m; BK-19); listenin aşık boyu
    modelin sıralarının boyu. %27,5'te arka verandada saçak sırası eski P2 formülüne göre bir sıra fazla (son aralık sırasından saçağa 46,5 cm
    kalıyor); ana çatı (17 cm: o sıra konmaz) ve ön veranda (51,3 cm) P2 ile aynı."""
    say, L = tk01["say"], tk01["liste"]
    satir = L["Aşık"][0]
    assert "karar C" in satir["formul"] and "en yakın" not in satir["formul"]
    toplam, fark = 0.0, {}
    for c in (None, "ÖN VERANDA", "ARKA VERANDA"):
        A = _parcalar(say, "AS-01", c)
        egik = max(p["bilgi"]["MahyadanEgik_cm"] for p in A)
        d = PL.asik_mesafeleri(egik, 60, 100 * PL._pr(PL.kurallari_oku()["prefabrik"], "asik_sacak_esigi_m"))
        assert sorted({p["bilgi"]["MahyadanEgik_cm"] for p in A if p["bilgi"]["Yuz"] == "sol"}) == [round(x, 2) for x in d]
        boy = sum(p["boy_cm"] for p in A if p["bilgi"]["Yuz"] == "sol" and p["bilgi"]["Sira"] == 1)     # sıranın boyu (mahya boyu)
        toplam += 2 * len(d) * boy
        fark[c] = len(d) - (round((egik - 20) / 60) + 1)
    assert abs(toplam / 100 - _metre(satir["formul"], "aşık boyları")) < 0.06
    assert fark == {None: 0, "ÖN VERANDA": 0, "ARKA VERANDA": 1}


def test_tk01_sacak_omegasi_sacak_boyu(tk01):
    """CK-01: model saçak omegasını saçak ucundan ucuna kurar, liste de saçak boyunca sayar (Lokman, 31 Ekim 13:40 "gerçek listeye uy";
    gerçek PK-01, PK-02, PK-03 listeleri saçak boyuyla tutuyor). Listenin saçak boyu modelin saçak omegası hatlarının ve saçak sacının
    boyudur. Hat baş makas betopanında ve aynı hatta devam eden veranda omegasında kesilir (CIO onayı 31 Ekim 16:58, seçenek a): parçalar
    hattın parçası, sayı hattın tamamından."""
    say, L = tk01["say"], tk01["liste"]
    m = {k["kod"]: k.get("metre") for k in say["kartlar"]}
    sacak = _metre(L["100'lük saçak omegası"][0]["formul"], "saçak kenarları")
    kp = say["kesim_plani"]["CK-01"]
    assert abs(kp["toplam_m"] - sacak) < 0.01 and abs(m["CK-02"] - sacak) < 0.01
    for c in (None, "ÖN VERANDA", "ARKA VERANDA"):                             # her çatıda saçak omegası hattı saçak sacıyla aynı boyda
        hat = {p["bilgi"].get("Hat", i): p["bilgi"].get("HatBoyu_cm", p["boy_cm"]) for i, p in enumerate(_parcalar(say, "CK-01", c))}
        assert sorted(hat.values()) == sorted(p["boy_cm"] for p in _parcalar(say, "CK-02", c)), c
    kesik = [p for p in _parcalar(say, "CK-01") if "Hat" in p["bilgi"]]
    assert [(p["bilgi"].get("Cati"), p["bilgi"]["Yuz"], p["boy_cm"]) for p in kesik] == [
        (None, "sol", 28.8), (None, "sol", 888.5), (None, "sag", 28.8), (None, "sag", 888.5), (None, "sag", 28.8),
        ("ÖN VERANDA", "sol", 209.8), ("ÖN VERANDA", "sag", 209.8), ("ARKA VERANDA", "sol", 128.8), ("ARKA VERANDA", "sol", 28.8), ("ARKA VERANDA", "sag", 128.8), ("ARKA VERANDA", "sag", 28.8)]
    assert kp["stok"] == math.ceil(kp["toplam_m"] / 2.5 - 1e-9) == L["100'lük saçak omegası"][0]["adet"] == 11 and kp["hat"] == 6


def _prizmalar(p: dict) -> list[dict]:
    return [q for q in (p["geo"]["parcalar"] if p["geo"]["tip"] == "coklu" else [p["geo"]]) if q["tip"] == "prizma"]


def _cakisir(p: dict, q: dict) -> bool:
    """Aynı düzlemli iki prizma (`p`'nin kesitinin zarfı) `v` boyunca da kesitte de üst üste biniyor mu."""
    return any(a["duzlem"] == b["duzlem"] and min(a["a1"], b["a1"]) - max(a["a0"], b["a0"]) > 1e-6
               and Polygon(a["noktalar"]).envelope.intersection(Polygon(b["noktalar"])).area > 1e-6
               for a in _prizmalar(p) for b in _prizmalar(q))


@pytest.mark.parametrize("ad, yol", [("TK01", TK01), ("PK01", MOTOR_VERI / "PK01.json"), ("ALTIN", KOK / "is_emri" / "ALTIN_2plus1_6x8.json"),
                                     ("YAN_VERANDALI", KOK / "is_emri" / "YAN_VERANDALI_2plus1_6x8p5.json"), ("TK03", MOTOR_VERI / "TK03.json")])
def test_sacak_omegasi_betopanla_ve_omegayla_cakismaz(ad, yol, tmp_path):
    """Saçak omegası saçak ucuna uzayınca (BK-19) dikey betopan levhasının ucu omeganın kesitine iner: hat levhada kesilir, levha geçer
    (CIO onayı 31 Ekim 16:58, seçenek a; geometri hakemi BK-19). Ana çatının omegası aynı hatta devam eden veranda omegasının üstüne binmez.
    Kesik hattın parçaları hattın boyunu taşır: hatların toplamı saçak boyu (liste), kesik kısım da içinde. Girintili gövdede (TK-03, İE-24)
    de: dört saçak kenarı dört hat, her parçanın baş makas betopanında kesik."""
    ie = _oku(yol)
    S = _katmanlar(ie, tmp_path, ad)
    y, liste = _oku(KM.YERLESIM), _oku(KM.LISTE_KURALLARI)
    D = Y.degerler(y, liste)
    N = kenar.katman(ie, S["girdi"], D, D["gosterim"]["kesit_cm"], y["kurallar"])
    bt = [p for p in S["parcalar"] if p["kural"] == "bas_makas_betopani_yerlesimi"]
    om = [p for p in N["parcalar"] if p["parca"] == "sacak_omegasi"]
    assert bt and om
    assert [(o["aciklama"], b["aciklama"]) for o in om for b in bt if _cakisir(o, b)] == []
    assert [(o["aciklama"], p["aciklama"]) for i, o in enumerate(om) for p in om[i + 1:] if _cakisir(o, p)] == []
    hat = {(p["bilgi"].get("Cati"), p["bilgi"].get("Hat", i)): p["bilgi"].get("HatBoyu_cm", p["boy_cm"]) for i, p in enumerate(om)}
    sac = [p for p in N["parcalar"] if p["parca"] == "sacak_saci"]
    assert sorted(hat.values()) == sorted(p["boy_cm"] for p in sac)
    assert any("Hat" in p["bilgi"] for p in om) == (ad != "PK01")             # PK-01'in levhaları yatık, mahyaya ortalı: omegaya inmez


def test_tk01_betopan_veranda_kalkani(tk01):
    """BT-01: ana kalkanlar dikey levhalarla H5 sayısı (8); veranda kalkanlarında da H5 (kalkan başına 1, yatık). Liste kirişli veranda
    kalkanını da sayar (D-32 madde 2): 8 + 2; kirişsiz açık parça N1 ile sayılmaz."""
    say, L = tk01["say"], tk01["liste"]
    assert "dış kirişindeki dahil" in L["Baş makas betopanı"][0]["formul"]
    ana, ver = _parcalar(say, "BT-01", None), [p for p in _parcalar(say, "BT-01") if p["bilgi"].get("Cati")]
    assert len(ana) == 8 and len(ana) + len(ver) == L["Baş makas betopanı"][0]["adet"] == 10 and all(p["bilgi"]["Dizilim"] == "dikey" for p in ana)
    assert sorted(p["bilgi"]["Makas"] for p in ver) == ["ARKA VERANDA kalkanı", "ÖN VERANDA kalkanı"]
    assert all("Dizilim" not in p["bilgi"] for p in ver)


def test_tk01_kenarlar_verandada(tk01):
    """Veranda kalkanında alın sacı, Z ve C kapama var (rehberdeki gibi dört kalkanda; model atölyesi, 30 Ekim; Z kirişli kalkanda, liste
    O7 de sayar); saçak sacı ve mahya saçak ucundan ucuna."""
    say = tk01["say"]
    for c, boy in (("ÖN VERANDA", 211), ("ARKA VERANDA", 160)):
        A, C = _parcalar(say, "CK-03", c), _parcalar(say, "CK-05", c)
        assert len(A) == len(C) == len(_parcalar(say, "CK-04", c)) == 2
        assert sorted(p["bilgi"]["Yuz"] for p in C) == ["sag", "sol"] and {p["boy_cm"] for p in C} == {p["boy_cm"] for p in A}
        assert [p["boy_cm"] for p in _parcalar(say, "CK-02", c)] == [boy, boy] and [p["boy_cm"] for p in _parcalar(say, "CK-06", c)] == [boy]
    assert sorted(p["bilgi"]["Yer"] for p in _parcalar(say, "DR-02") if p["bilgi"].get("Cati")) == ["dış uç"] * 4


# ----------------------------------------------------------------------------- kural birimleri
@pytest.mark.parametrize("yazi, tur, uyari", [("Sandviç Panel", "sandvi", False), ("Tek Kat Panel", "tek kat", False), ("", "tek kat", True),
                                              ("Antrasit", "tek kat", True), ("Trapez Sac", None, False), ("Metal Kiremit", None, False)])
def test_kaplama_okumasi(yazi, tur, uyari):
    D = Y.degerler(_oku(KM.YERLESIM), _oku(KM.LISTE_KURALLARI))["cati_kaplamasi"]
    u = []
    t, neden = Y.kaplama_turu({"ozellikler": {"Çatı Kaplaması": yazi} if yazi else {}}, D, u)
    assert t == tur and bool(u) == uyari and (neden is None) == (tur is not None)
    if tur is None:
        assert "kartı yok" in neden
    assert Y.kaplama_degerleri(D, "tek kat", {"asik": [3, 8.7], "kaplama": 6})["kapatma_cm"] == 100


@pytest.mark.parametrize("m", [100, 160, 200, 211, 249, 250, 251, 300, 349.5])
def test_kaplama_iki_yuz(m):
    """Taşan verandanın kaplaması iki yüz birlikte ⌈2 × mahya boyu ÷ kapatma⌉ (liste üretecinin ek çatı parçası sayısı); şeritler çatının
    içinde (taşmaz), artanlar bir panele sığarsa iki prizmalı tek panel."""
    eg, A, s = 0.3, 300, 30
    F = {"mx": True, "ou": 1000, "aciklik": A, "boy": m - s, "s": s, "eg": eg, "zs": 260, "um": A / 2, "kos": 1 / math.sqrt(1 + eg * eg),
         "egik": (A / 2 + s) * math.sqrt(1 + eg * eg), "v0": -m, "v1": 0, "v_bas": "min"}
    K = {"kesit_asik": [3, 8.7], "kalinlik_kaplama": 6, "tasma_m": 0.05, "yuvarlama_mm": 10, "kapatma_cm": 100}
    P = cati.kaplama({}, K, F, iki_yuz=True)
    assert len(P) == math.ceil(2 * m / 100 - 1e-9)
    r = m - 100 * math.floor(m / 100 + 1e-9)
    iki = [p for p in P if p["bilgi"]["Yuz"] == "iki"]
    assert len(iki) == (1 if 0 < 2 * r <= 100 else 0) and all(p["bilgi"]["Tasma_cm"] == 0 for p in P)
    kesik = [p for p in P if "Kesim_cm" in p["bilgi"]]
    assert len(kesik) == (0 if r < 1e-6 else 1 if 2 * r <= 100 else 2) and all(p["bilgi"]["Kesim_cm"] == pytest.approx(r) for p in kesik)
    for p in P:
        for g in (p["geo"]["parcalar"] if p["geo"]["tip"] == "coklu" else [p["geo"]]):
            assert -m - 1e-6 <= g["a0"] < g["a1"] <= 1e-6 and min(x for x, _z in g["noktalar"]) > 1000 - s - 10      # u dünyada `ou`'dan


def test_dikey_betopan_uclari_artanla_kapanir(tk01_k):
    """Ana kalkan (üçgen 125'ten yüksek): H5 sayısı kadar dikey 125 × 250 levha, mahyadan iki yana; levhalar örtüşmez; levhalar ve artan
    parçalar saçaklı üçgeni örter; uç parçası o yandaki en dıştaki levhanın, artanı levhaların kesilen kısmından küçük."""
    F = tk01_k["cerceve"]
    B = [p for p in tk01_k["parcalar"] if p["parca"] == "levha" and "Cati" not in p["bilgi"]]
    assert len(B) == 8 and {p["bilgi"]["LevhaAdedi"] for p in B} == {4}
    lu, lz = 250, 125
    for ad in {p["bilgi"]["Makas"] for p in B}:
        L = [p for p in B if p["bilgi"]["Makas"] == ad]
        govde = lambda p: [Polygon(g["noktalar"]) for g in (p["geo"]["parcalar"] if p["geo"]["tip"] == "coklu" else [p["geo"]])]   # noqa: E731
        kutular = [(p["bilgi"]["LevhaU0_cm"], p["bilgi"]["LevhaU1_cm"]) for p in L]
        assert all(b - a == pytest.approx(lz) for a, b in kutular)
        assert sorted(kutular) == [(F["um"] + k * lz, F["um"] + (k + 1) * lz) for k in (-2, -1, 0, 1)]     # mahyadan iki yana
        z0 = 250
        ucgen = Polygon([(-F["s"], z0), (F["aciklik"] + F["s"], z0), (F["aciklik"] + F["s"], cati._ust(F, F["aciklik"] + F["s"])),
                         (F["um"], cati._ust(F, F["um"])), (-F["s"], cati._ust(F, -F["s"]))])
        hepsi = [q for p in L for q in govde(p)]
        assert unary_union(hepsi).symmetric_difference(ucgen).area < 1.0
        assert sum(q.area for q in hepsi) == pytest.approx(unary_union(hepsi).area, abs=1.0)                # örtüşme yok
        uclu = [p for p in L if "ArtanUc_m2" in p["bilgi"]]
        assert sorted(p["bilgi"]["Levha"] for p in uclu) == [3, 4]                    # en dıştakiler (sağda 3., solda 4.)
        artan = sum(lu * lz - govde(p)[0].area for p in L) / 1e4
        assert sum(p["bilgi"]["ArtanUc_m2"] for p in uclu) <= artan


def test_dere_kesimi_hatlar_arasinda():
    """Dere hattı bindirmeyle parçalara bölünür, parçalar stok boylarına en uzun önce (bir hattın artanı başka hatta): PK-01 6, TK-01 7."""
    assert kesim.dere_karti([1059.8, 1059.8], 400, 20)["stok"] == 6
    k = kesim.dere_karti([948.5, 948.5, 211, 211, 160, 160], 400, 20)
    assert k["stok"] == 7 and k["hat_basina"] == [3, 3, 1, 1, 1, 1] and sorted(map(len, k["dizilim"])) == [1, 1, 1, 1, 2, 2, 2]


def test_yavru_makas_yeri(tk01_k):
    """Sayı J8 (ön 3, arka 2); ilki dış kirişin ekseninde, sonuncusu gövde duvarının dış yüzünden 5 cm dışarıda, aralar eşit."""
    g = tk01_k["girdi"]
    for F in veranda.cerceveler(g)[0]:
        P = veranda.yavru_makaslar(g, F, {"makas_aralik": 125.5, "makas_yarim_cm": 5, "kesit_cm": {"kalinlik": 5, "baslik": 10, "dikme": 6}})
        v = [(p["geo"]["parcalar"][0]["a0"] + p["geo"]["parcalar"][0]["a1"]) / 2 for p in P]
        if F["ad"] == "ÖN VERANDA":
            assert v == pytest.approx([-176, -90.5, -5]) and [p["bilgi"]["Yer"] for p in P] == ["dış kiriş", "ara", "duvar dibi"]
        else:
            assert v == pytest.approx([1013.5, 893.5])
        assert all(p["bilgi"]["Aciklik_cm"] == F["aciklik"] + 2 * F["s"] for p in P)


@pytest.mark.parametrize("degisiklik, neden", [({"cati": {"tip": "tek_yon", "egim_yuzde": 15}}, "tek yön"),
                                               ({"cephe": "sol", "bas_cm": 200, "bit_cm": 500}, "çapraz")])
def test_veranda_catisi_kurulmazsa_kural_yok(tmp_path, degisiklik, neden):
    """Tek yön ve çapraz (ana çatının saçak yüzünde) veranda çatısı K6'da: "kural yok", öteki veranda kurulur."""
    ie = _oku(TK01)
    ie["verandalar"][0].update(degisiklik)
    k = _katmanlar(ie, tmp_path, "v")
    yok = [x for x in k["kural_yok"] if x["parca"].startswith("veranda çatısı")]
    assert [x["parca"] for x in yok] == ["veranda çatısı (ÖN VERANDA)"] and "K6" in yok[0]["neden"]
    assert {p["bilgi"].get("Cati") for p in k["parcalar"]} == {None, "ARKA VERANDA"}
    if neden == "tek yön":
        assert "\"tek_yon\"" in yok[0]["neden"]
    else:
        assert "dik" in yok[0]["neden"]


# ----------------------------------------------------------------------------- adlar, çizim, PK-01
def test_adlar_onekli(tk01):
    f = ifcopenshell.open(str(tk01["klasor"] / "TK01_model.ifc"))
    adlar = [e.Name for e in f.by_type("IfcProduct") if (e.Name or "").startswith(("ASIK_", "KAPLAMA_", "VERANDA_"))]
    assert sum(a.startswith("ASIK_") for a in adlar) == len(_parcalar(tk01["say"], "AS-01", None)) == 54    # ana çatının adları sırayla (BK-19: saçak eşiği 30 cm, yüz başına 9 sıra)
    assert sorted(a for a in adlar if a.startswith("VERANDA_YAVRU")) == [f"VERANDA_YAVRU_MAKAS_{i:03d}" for i in range(1, 6)]
    assert "VERANDA_ASIK_001" in adlar and "VERANDA_KAPLAMA_001" in adlar and "KAPLAMA_021" not in adlar


def test_cizim(tk01):
    import pymupdf
    metin = [" ".join(p.get_text().split()) for p in pymupdf.open(tk01["klasor"] / "TK01_yerlesim_planlari.pdf")]
    assert len(metin) == 7 and not any("EKSİK" in s for s in metin)
    assert "MA-03 Yavru makas: 5 (Y; veranda çatısı)" in metin[1]
    assert "ÖN VERANDA kalkanı, dış yüzden görünüş" in metin[2] and "MAKAS_01 (baş makas)" in metin[2] and "ÖN VERANDA kalkanı: 1" in metin[2]
    assert "KP-02 Tek kat çatı paneli" in metin[4] and "29 panel" in metin[4]
    assert "Veranda kalkanında Z ve C kapama var" in metin[6] and "Z yok" not in metin[6]


def test_pk01_veranda_yok(tmp_path):
    ie = _oku(MOTOR_VERI / "PK01.json")
    assert ifc_uret.uret(ie, tmp_path / "PK01.ifc")["sema_hatasi"] == 0
    say = KM.kart_modeli(tmp_path / "PK01.ifc", tmp_path / "PK01_model.ifc", "besik", is_emri=ie, plan=ifc_uret.hazirla(ie), kenar=True)
    adet = {k["kod"]: k["adet"] for k in say["kartlar"]}
    assert adet["KP-02"] == adet["MA-03"] == 0 and adet["KP-01"] == 22 and say["kural_yok"] == []
    assert not any(p["bilgi"].get("Cati") for p in say["yerlesim"]["parcalar"])
