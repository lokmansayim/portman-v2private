"""Montaj rehberi ön-sol köşeden dizilen evi de kurar (17 Kasım 2026; 85 m² katalog evi, İş Emri `is_emri/P8501_r05.json`).

Hata: rehber üreteci (`rehber/veri.py` › `oda_sirasi`) yalnız arka-sol köşeden dizilen evi kuruyordu (`dizilim.baslangic: arka-sol`;
TK-01…TK-05). Motor'un varsayılanı ön-sol (`baslangic` yazılmazsa); katalog evlerinin İş Emri'si bunu yazmaz, rehber "Yok: dizilim
başlangıcı {'x': 'min', 'y': 'min'}" diyordu. Lokman, 17 Kasım 2026 07:41 UTC: "bana başka bir sohbette montaj paftasını oluşturur musun?"

Düzeltme: ön-sol başlangıçta oda sırası aynı kuralla, planın y'si aynalanarak (ön duvara değen odalar soldan sağa, sağ duvara değenler
önden arkaya, arka duvara değenler sağdan sola, sol duvara değenler arkadan öne); oda içinde sıra odanın ön-sol köşesinden; ilk odanın
yazısı "ön sol köşesinden". Arka-sol evlerin rehberi değişmez (`test_rehber.py`, `test_paket.py`, `test_tk05_rehber.py`).

Ön-sol cumba köşesi (r05): r04'te ana makaslar cumbanın içinden öne uzanıyordu; rehberde köşede 9 parça birbirine giriyordu (cumbanın alın
sacı ana çatının içinden çıkıyordu). Lokman, 17 Kasım 2026 08:27:29 UTC: "daha önce 80 m² kampanyalıda buna çalışmıştık yine aynı şekilde
yapar mısın ... aynı orası gibi olsun". r05 kampanyalı evin (TK-04 r08) çözümüyle: ana makaslar cumba makasının arkasında biter
(`ana_makas: cumba_makasindan`, D-53); ana çatının alın sacı köşede düz biter, saçak altı omeganın arka yüzünde dik aşağı bükülür
(`sahne.js` › `alinKapak`; `test_rehber_cumba_kose.py`). Kalan çakışmalar kampanyalı evdeki açık konu (D-73 › Açık kalan).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz, veri  # noqa: E402

IE = KOK / "is_emri" / "P8501_r05.json"
JS = KOK / "araclar" / "paket" / "rehber"
SOL_ALIN = "ana çatı sol kalkanı (MKS01) · ön/sol yüz"


def _kutu(ad, x0, y0, x1, y1):
    return {"ad": ad, "poligon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


ODALAR = [_kutu("ON SOL", 0, 0, 100, 100), _kutu("ON SAG", 100, 0, 200, 100),
          _kutu("ARKA SOL", 0, 100, 100, 200), _kutu("ARKA SAG", 100, 100, 200, 200)]


def test_oda_sirasi_arka_sol_aynen():
    assert veri.oda_sirasi(copy.deepcopy(ODALAR), {"x": "min", "y": "max"})[0] == ["ARKA SOL", "ARKA SAG", "ON SAG", "ON SOL"]


def test_oda_sirasi_on_sol_aynali():
    assert veri.oda_sirasi(copy.deepcopy(ODALAR), {"x": "min", "y": "min"})[0] == ["ON SOL", "ON SAG", "ARKA SAG", "ARKA SOL"]


@pytest.mark.parametrize("bas", [{"x": "max", "y": "max"}, {"x": "max", "y": "min"}])
def test_sag_kose_desteklenmiyor(bas):
    with pytest.raises(veri.Desteklenmiyor):
        veri.oda_sirasi(copy.deepcopy(ODALAR), bas)


@pytest.fixture(scope="module")
def p8501(tmp_path_factory):
    from motor import geometry as G, kart_model, prefabrik_liste as PL
    ie = json.loads(IE.read_text(encoding="utf-8"))
    assert "baslangic" not in ie["yapi"]["dizilim"]                     # Motor'un varsayılanı: ön-sol
    kart = tmp_path_factory.mktemp("p8501_rehber")
    kart_model.uret(copy.deepcopy(ie), kart, "P8501")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    d = veri.kur(copy.deepcopy(ie), kart, "P8501", L, "KP-85")
    G.lento_ayarla({})
    yield d
    G.lento_ayarla({})


def test_p8501_rehber_kurulur(p8501):
    d = p8501
    assert d["N"] == 21 and len(d["panels"]) == 49 and len(d["rooms"]) == 6
    oda = [a for a in d["adimlar"] if a.get("oda")]
    assert oda[0]["oda"] == "yasamalani"                                # ön-sol köşedeki oda ilk
    assert [x for x in d["panels"] + d["hs"] + d["posts"] if not (x.get("card") or x.get("ad"))] == []


def test_p8501_ilk_oda_yazisi_on_sol(p8501):
    assert "ön sol köşesinden" in json.dumps(p8501, ensure_ascii=False)
    assert "arka sol köşesinden" not in json.dumps(p8501, ensure_ascii=False)


# ---------------------------------------------------------------- ön-sol cumba köşesi (r05; kampanyalı evle aynı denetim)
# Kampanyalı evdeki açık çakışmalar (`test_rehber_cumba_kose.py` › ACIK): en çok bu kadar nokta.
ACIK = {
    ("Baş makas Z'si", "Yavru makas (çapraz cumba)"): 4,
    ("C kapama", "Yavru makas (çapraz cumba)"): 2,
    ("Alın sacı", "Yavru makas (çapraz cumba)"): 2,
    ("Alın sacı", "Trapez sac L 2410 (cumba)"): 11,
}


@pytest.fixture(scope="module")
def sayfa(p8501, tmp_path_factory):
    if iz.hazir() is not None:
        pytest.skip(f"rehber denetimi: {iz.hazir()}")
    from araclar.paket.rehber import sayfa as S
    tmp = tmp_path_factory.mktemp("p8501_kose")
    return {"html": S.yaz(p8501, tmp / "P8501.html").resolve(), "dis": p8501["dis"], "tmp": tmp}


def _node(*a):
    import subprocess
    r = subprocess.run(["node", *map(str, a)], capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]


def test_r05_ana_makas_cumba_makasindan():
    ie = json.loads(IE.read_text(encoding="utf-8"))
    r04 = json.loads((KOK / "is_emri" / "P8501_r04.json").read_text(encoding="utf-8"))
    assert ie["cati"]["cumbalar"][0]["ana_makas"] == "cumba_makasindan"
    ie["cati"]["cumbalar"][0].pop("ana_makas")
    assert {k: v for k, v in ie.items() if k not in ("revizyon", "varsayimlar")} == \
        {k: v for k, v in r04.items() if k not in ("revizyon", "varsayimlar")}      # plan ve öteki her şey r04 ile aynı


def test_r05_arkadan_cumba_gorunmez(sayfa):
    """Köşenin 1,5 m arkasından kalkan boyunca öne (kampanyalı evdeki pencere): ilk görülen cumbanın hiçbir parçası değildir."""
    X = lambda x: x / 100 - sayfa["dis"][0] / 200
    Z = lambda y: sayfa["dis"][1] / 200 - y / 100
    istek = {"bas": [X(-30.17), 2.4693, Z(150)], "u": [0.2904, 0, 0], "v": [0, 0.111, 0], "nu": 61, "nv": 23, "yon": [0, 0, 1]}
    (sayfa["tmp"] / "istek.json").write_text(json.dumps(istek), encoding="utf-8")
    _node(JS / "bakis.js", sayfa["html"], sayfa["tmp"] / "istek.json", sayfa["tmp"] / "bakis.json")
    d = json.loads((sayfa["tmp"] / "bakis.json").read_text(encoding="utf-8"))
    assert d["hatalar"] == [] and d["isin"] == 61 * 23
    cumba = {k: n for k, n in d["ilk"].items() if "MKS09" in k or "cumba" in k}
    assert not cumba, f"arkadan cumbanın parçası görünüyor: {cumba}"
    alin = sum(n for k, n in d["ilk"].items() if k.startswith(f"Alın sacı · {SOL_ALIN}"))
    assert alin >= 0.95 * d["isin"], d["ilk"]


def test_r05_kosede_alin_sacina_giren_yok(sayfa):
    _node(JS / "cakisma.js", sayfa["html"], sayfa["tmp"] / "cakisma.json")
    d = json.loads((sayfa["tmp"] / "cakisma.json").read_text(encoding="utf-8"))
    assert d["hatalar"] == []
    say: dict[tuple[str, str], int] = {}
    for p in d["parcalar"]:
        for k, n in p["cakisan"].items():
            assert "MKS01" in p["bu"], (p["ad"], p["bu"], k)
            o = k.split(" · ")[0]
            assert not o.startswith(("Saçak sacı", "Metal dere", "Baş makas omegası", "Alın sacı")), (p["ad"], p["bu"], k, n)
            say[(p["ad"], o)] = say.get((p["ad"], o), 0) + n
    fazla = {k: n for k, n in say.items() if n > ACIK.get(k, 0)}
    assert not fazla, f"açık konu dışında çakışma ya da artış: {fazla}"


def test_r05_kosede_alin_yazisi(sayfa):
    z = iz.al(sayfa["html"], sayfa["tmp"] / "iz.json")
    sat = [dict(p["satir"]) for p in z["parts"] if p["ad"] == "Alın sacı" and SOL_ALIN in dict(p["satir"])["Bu parça"]]
    assert any(s["Bu parça"].endswith("köşede düz biter, derenin ucu açık kalır") for s in sat), sat
    assert any(s.get("Köşede", "").startswith("saçak altı baş makas omegasının arka yüzünde dik aşağı bükülür") for s in sat), sat
