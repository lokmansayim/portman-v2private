"""Saçak sacının tırnağı aşağı kıvrık, saçak omegasının dudağının içinde (Lokman, 28 Kasım 2026).

Lokman çizimi 28.11.2026 15:38:25 UTC (18:38 İstanbul; PF `Teklif_Calisma/TK-11/rehber_bakim/2026-11-28_Lokman_sacak_cizimi_1838.pdf`),
sözü: "saçak omegasını ve saçağı çizdim yeniden yani anlamıyorum nasıl şimdiye kadar montaj rehberi olsun github olsun hep hatalı
çizdin". Eskiz r07 kartı 16:05:32 UTC: "Doğru; uç alınla aynı hizada". Kayıt `kurallar/yerlesim/prefabrik.json › sacak_saci_yerlesimi
› tirnak` (durum lokman), çizen tek kod `araclar/paket/rehber/sahne.js` › Saçak sacı. Bütün evlerin saçak sacı bu koddan çizilir.

Önce (25 Ekim varsayımı) tırnak omeganın üstünde yataydı (`lb(-2.8, 30.2, …)`). Şimdi:
1. Omeganın üstünde saçak sacı yok: duvarın içinden aşağı inen ışın önce saçak omegasına çarpar.
2. Tırnak omeganın dış kanadının dışında, dudağın içinde: dudağın içinden duvara doğru atılan yatay ışın önce saçak sacına çarpar.
3. Tırnak aşağı iner: saçak altının 2,5 cm altında da tırnak var.
Denetim 62 m² hedef örneğinin verisiyle (`testler/paket/rehber62/veri.json`), arka saçak boyunca, `bakis.js` ile.
Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister; yoksa atlanır, CI'da kurulur (`dogrulama.yml`).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz  # noqa: E402

B = KOK / "testler" / "paket" / "rehber62"
JS = KOK / "araclar" / "paket" / "rehber"
IKI = r"^(100’lük saçak omegası · |Saçak sacı · arka saçak)"

pytestmark = pytest.mark.skipif(iz.hazir() is not None, reason=f"rehber denetimi: {iz.hazir()}")


@pytest.fixture(scope="module")
def sayfa(tmp_path_factory):
    from araclar.paket.rehber import sayfa as S
    d = json.loads((B / "veri.json").read_text(encoding="utf-8"))
    tmp = tmp_path_factory.mktemp("sacak_tirnagi")
    return {"html": S.yaz(d, tmp / "62.html").resolve(), "dis": d["dis"], "h": d["h"], "tmp": tmp}


def _bak(sayfa, ad, istek):
    (sayfa["tmp"] / f"{ad}.json").write_text(json.dumps(istek, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run(["node", str(JS / "bakis.js"), str(sayfa["html"]), str(sayfa["tmp"] / f"{ad}.json"),
                        str(sayfa["tmp"] / f"{ad}_sonuc.json")], capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-2000:]
    d = json.loads((sayfa["tmp"] / f"{ad}_sonuc.json").read_text(encoding="utf-8"))
    assert d["hatalar"] == [], d["hatalar"]
    return d


def _ilk(d, onek):
    return sum(n for k, n in d["ilk"].items() if k.startswith(onek))


def _pencere(sayfa, u_cm, h_cm, nv=5):
    """Arka saçakta (duvar dış yüzü y = derinlik) dışa doğru u cm'de, h cm yükseklik aralığında, x 100–800 cm boyunca dikey pencere."""
    dis, X = sayfa["dis"], (lambda x: x / 100 - sayfa["dis"][0] / 200)
    z = dis[1] / 200 - (dis[1] + u_cm) / 100
    return {"bas": [X(100), h_cm[0] / 100, z], "u": [X(800) - X(100), 0, 0], "v": [0, (h_cm[1] - h_cm[0]) / 100, 0], "nu": 40, "nv": nv}


def test_omeganin_ustunde_sacak_saci_yok(sayfa):
    dis, X, H = sayfa["dis"], (lambda x: x / 100 - sayfa["dis"][0] / 200), sayfa["h"]
    z0, z1 = dis[1] / 200 - (dis[1] - 2.5) / 100, dis[1] / 200 - (dis[1] - 0.5) / 100   # duvarın 0,5–2,5 cm içi, omeganın üstü
    istek = {"bas": [X(100), (H + 5) / 100, z0], "u": [X(800) - X(100), 0, 0], "v": [0, 0, z1 - z0], "nu": 40, "nv": 5,
             "yon": [0, -1, 0], "dahil": IKI}
    d = _bak(sayfa, "ust", istek)
    assert _ilk(d, "Saçak sacı") == 0, f"omeganın üstünde saçak sacı var: {d['ilk']}"
    assert _ilk(d, "100’lük saçak omegası") >= 0.9 * d["isin"], d["ilk"]


def test_tirnak_dudagin_icinde_kanadin_disinda(sayfa):
    H = sayfa["h"]
    istek = {**_pencere(sayfa, 1.0, (H - 1.3, H - 0.3)), "yon": [0, 0, 1], "dahil": IKI}   # dudağın içinden duvara doğru
    d = _bak(sayfa, "dudak", istek)
    assert _ilk(d, "Saçak sacı") >= 0.9 * d["isin"], f"dudağın içinde önce tırnak görünmeli: {d['ilk']}"


def test_tirnak_asagi_iner(sayfa):
    H = sayfa["h"]
    istek = {**_pencere(sayfa, 0.42, (H - 2.5, H - 1.5)), "yon": [0, 0, 1], "dahil": IKI}  # saçak altının 2,5 cm altına kadar
    d = _bak(sayfa, "boy", istek)
    assert _ilk(d, "Saçak sacı") >= 0.9 * d["isin"], f"tırnak aşağı inmeli: {d['ilk']}"
