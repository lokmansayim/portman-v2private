"""Kampanyalı ev (TK-04 r08) ön-sol köşe: cumbanın kısa yan saçağı ana çatının sol kalkanının devamında (11 Kasım 2026).

Lokman, 10.11.2026 21:26 UTC: "asıl sorun diğer tarafta cumbanın ana çatının alın sacı ile birleştiği yerde arkadan bakınca bir boşluk
oluşuyor ... montajcılar binanın ana makaslarının alın sacını alttan uzun bırakıyor ki saçak sacını kapatsın derenin o kısmı açıkta kalıyor
orayı kapatmıyoruz". 11.11.2026 08:52 UTC: "alın sacı tek formda ... alın sacının altındaki parçayı aşağı doğru uzatacaksın yani tam arkadan
bakınca baş makas omegası ve cumba makası görünmeyecek". 10:06 UTC eskiz kartı: "Doğru, böyle yap".

Çözüm (`araclar/paket/rehber/sahne.js` › `alinKapak`, `alinUzun`): ana çatının alın sacının saçak altı baş makas omegasının arka yüzünde
biter ve dik aşağı bükülür, omeganın altına iner; alın köşede düz biter, derenin ucu açık kalır. Denetim iki araçla:
- `bakis.js`: köşenin arkasından kalkan boyunca paralel ışınlar; ilk çarpılan parça cumbanın hiçbir parçası değildir.
- `cakisma.js`: ana çatının sol alın sacı saçak sacına, dereye ve omegaya girmez. Kalan çakışmalar bu köşenin dışındaki açık konudur
  (cumba makasının kalkana 0,4 cm girmesi, cumbanın trapez sacı; D-73 › Açık kalan); sayıları artmaz.
Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister; yoksa atlanır, CI'da kurulur (`dogrulama.yml`).
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz  # noqa: E402

IE = KOK / "testler" / "motor" / "veri" / "TK04_r08.json"
JS = KOK / "araclar" / "paket" / "rehber"
SOL_ALIN = "ana çatı sol kalkanı (MKS01) · ön/sol yüz"
# Bu köşenin dışında kalan açık çakışmalar (D-73 › Açık kalan): en çok bu kadar nokta.
ACIK = {
    ("Baş makas Z'si", "Yavru makas (çapraz cumba)"): 4,
    ("C kapama", "Yavru makas (çapraz cumba)"): 2,
    ("Alın sacı", "Yavru makas (çapraz cumba)"): 2,
    ("Alın sacı", "Trapez sac L 2410 (cumba)"): 11,
}

pytestmark = pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber denetimi: {iz.hazir()}")


@pytest.fixture(scope="module")
def sayfa(tmp_path_factory):
    from motor import geometry as G, kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import sayfa as S, veri
    ie = json.loads(IE.read_text(encoding="utf-8"))
    kart = tmp_path_factory.mktemp("tk04_kose")
    kart_model.uret(copy.deepcopy(ie), kart, "TK04")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    d = veri.kur(copy.deepcopy(ie), kart, "TK04", L, "TK-04")
    G.lento_ayarla({})                                   # lento modül durumudur (BK-23): öteki testlere sızmaz
    yield {"html": S.yaz(d, kart / "TK-04.html").resolve(), "dis": d["dis"], "tmp": kart}


def _node(*a):
    r = subprocess.run(["node", *map(str, a)], capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]


def test_tam_arkadan_omega_ve_cumba_makasi_gorunmez(sayfa):
    """Köşenin 1,5 m arkasından kalkan boyunca ön tarafa: duvarın dış yüzünden alına (1,13–30,17 cm dışarıda), omeganın altından saçak
    altına (246,93–258,03 cm) 61 × 23 ışın. Pencere milimetre çizgisine denk gelmesin diye 0,2–0,3 mm kaydırılmış (değen yüzlerin arası)."""
    X = lambda x: x / 100 - sayfa["dis"][0] / 200    # plan (cm) → dünya (m), sahne.js'teki gibi
    Z = lambda y: sayfa["dis"][1] / 200 - y / 100
    istek = {"bas": [X(-30.17), 2.4693, Z(150)], "u": [0.2904, 0, 0], "v": [0, 0.111, 0], "nu": 61, "nv": 23, "yon": [0, 0, 1]}
    (sayfa["tmp"] / "istek.json").write_text(json.dumps(istek), encoding="utf-8")
    _node(JS / "bakis.js", sayfa["html"], sayfa["tmp"] / "istek.json", sayfa["tmp"] / "bakis.json")
    d = json.loads((sayfa["tmp"] / "bakis.json").read_text(encoding="utf-8"))
    assert d["hatalar"] == [] and d["isin"] == 61 * 23
    cumba = {k: n for k, n in d["ilk"].items() if "MKS09" in k or "cumba" in k}
    assert not cumba, f"arkadan cumbanın parçası görünüyor: {cumba}"
    alt = d["ilk"].get(f"Alın sacı · {SOL_ALIN} · L 485 cm", 0)
    assert alt >= 0.95 * d["isin"], d["ilk"]          # görünen: ana çatının alın sacının aşağı bükülen saçak altı
    assert set(d["ilk"]) <= {f"Alın sacı · {SOL_ALIN} · L 485 cm", f"Baş makas Z'si · {SOL_ALIN} · 1/2. parça · L 280 cm", "(parçanın içinden)"}, d["ilk"]


def test_kosede_alin_sacina_giren_yok(sayfa):
    _node(JS / "cakisma.js", sayfa["html"], sayfa["tmp"] / "cakisma.json")
    d = json.loads((sayfa["tmp"] / "cakisma.json").read_text(encoding="utf-8"))
    assert d["hatalar"] == []
    say: dict[tuple[str, str], int] = {}
    for p in d["parcalar"]:
        for k, n in p["cakisan"].items():
            assert "MKS01" in p["bu"], (p["ad"], p["bu"], k)
            o = k.split(" · ")[0]
            assert not o.startswith(("Saçak sacı", "Metal dere", "Baş makas omegası")), (p["ad"], p["bu"], k, n)
            say[(p["ad"], o)] = say.get((p["ad"], o), 0) + n
    fazla = {k: n for k, n in say.items() if n > ACIK.get(k, 0)}
    assert not fazla, f"açık konu dışında çakışma ya da artış: {fazla}"


def test_parca_yazisi(sayfa):
    """Köşedeki alın sacının kartı: alın düz biter, saçak altı aşağı bükülür."""
    z = iz.al(sayfa["html"], sayfa["tmp"] / "iz.json")
    sat = [dict(p["satir"]) for p in z["parts"] if p["ad"] == "Alın sacı" and SOL_ALIN in dict(p["satir"])["Bu parça"]]
    assert any(s["Bu parça"].endswith("köşede düz biter, derenin ucu açık kalır") for s in sat), sat
    assert any(s.get("Köşede", "").startswith("saçak altı baş makas omegasının arka yüzünde dik aşağı bükülür") for s in sat), sat
