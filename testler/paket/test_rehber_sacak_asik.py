"""Saçak sacının makasa doğru 10 cm kıvrımı son aşığın üstünde, trapez sacın altında (D-78, 11 Kasım 2026).

Lokman, 11.11.2026 UTC: 15:34 "saçak sacı son koyulan aşığın üzerine gelecek"; 15:38 "ADIM 16 da gelen sacak sacı aşığın altında kalıyor
gibi". 15:59 önce/sonra eskizine kart: "Doğru, böyle yap".

Önce kıvrımın orta çizgisi aşık oturma yüzünden 2,87 cm yukarıdaydı: aşığın üst kanadının (2,9–3,0 cm) altından, aşığın içinden geçiyordu.
Şimdi kıvrımın alt yüzü aşığın üstünde (3,0 cm), trapez sacın altında (`araclar/paket/rehber/sahne.js` › saçak sacı). Denetim kampanyalı
evde (TK-04 r08) `bakis.js` ile: saçak sacının kıvrımının üstünden aşağı paralel ışınlar, yalnız aşıklar ve saçak sacları sayılır (kaplama
yokmuş gibi). İlk çarpılan parça hep saçak sacıdır; aynı ışınların hepsi aşığa da çarpar (kıvrım aşığın üstündedir, yanında değil).
Eski kodda arka saçakta 1.900 ışının 855'inde ilk çarpılan aşıktı.
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
IKI = r"^(Aşık \(omega\)|Saçak sacı) · "
ASIK = r"^Aşık \(omega\) · "

pytestmark = pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber denetimi: {iz.hazir()}")


@pytest.fixture(scope="module")
def sayfa(tmp_path_factory):
    from motor import geometry as G, kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import sayfa as S, veri
    ie = json.loads(IE.read_text(encoding="utf-8"))
    kart = tmp_path_factory.mktemp("tk04_sacak")
    kart_model.uret(copy.deepcopy(ie), kart, "TK04")
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    d = veri.kur(copy.deepcopy(ie), kart, "TK04", L, "TK-04")
    G.lento_ayarla({})                                   # lento modül durumudur (BK-23): öteki testlere sızmaz
    yield {"html": S.yaz(d, kart / "TK-04.html").resolve(), "dis": d["dis"], "tmp": kart}


def _bak(sayfa, ad, istek):
    (sayfa["tmp"] / f"{ad}.json").write_text(json.dumps(istek, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(["node", str(JS / "bakis.js"), str(sayfa["html"]), str(sayfa["tmp"] / f"{ad}.json"),
                        str(sayfa["tmp"] / f"{ad}_sonuc.json")], capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]
    d = json.loads((sayfa["tmp"] / f"{ad}_sonuc.json").read_text(encoding="utf-8"))
    assert d["hatalar"] == [], d["hatalar"]
    return d


# Pencereler duvarın dış yüzünden 22–29,8 cm dışarıda (kıvrım 20,7–30,2 cm, aşık 21,6–30,8 cm), saçak boyunca; 3 m yükseklikten aşağı.
# Arka saçak: ana çatının arka duvarı. Ön saçak: cumbanın sağında ana çatının ön duvarı, cumbanın 37,5 cm gerisinde.
SACAKLAR = {
    "arka": lambda X, Z, dis: ([X(-25), 3.0, Z(dis[1] + 22)], [X(dis[0] + 25) - X(-25), 0, 0], [0, 0, Z(dis[1] + 29.8) - Z(dis[1] + 22)], 95),
    "on": lambda X, Z, dis: ([X(424.4), 3.0, Z(37.5 - 22)], [X(914.4) - X(424.4), 0, 0], [0, 0, Z(37.5 - 29.8) - Z(37.5 - 22)], 50),
}


@pytest.mark.parametrize("yer", list(SACAKLAR))
def test_kivrim_son_asigin_ustunde(sayfa, yer):
    X = lambda x: x / 100 - sayfa["dis"][0] / 200    # plan (cm) → dünya (m), sahne.js'teki gibi
    Z = lambda y: sayfa["dis"][1] / 200 - y / 100
    bas, u, v, nu = SACAKLAR[yer](X, Z, sayfa["dis"])
    istek = {"bas": bas, "u": u, "v": v, "nu": nu, "nv": 20, "yon": [0, -1, 0]}
    iki = _bak(sayfa, f"{yer}_iki", {**istek, "dahil": IKI})
    asik = _bak(sayfa, f"{yer}_asik", {**istek, "dahil": ASIK})
    ustte = {k: n for k, n in iki["ilk"].items() if not k.startswith("Saçak sacı · ")}
    assert not ustte, f"{yer} saçakta kıvrımın üstünde başka parça: {ustte}"
    assert sum(asik["ilk"].get(k, 0) for k in asik["ilk"] if k) >= 0.9 * asik["isin"], asik["ilk"]   # pencere aşığın üstünde
