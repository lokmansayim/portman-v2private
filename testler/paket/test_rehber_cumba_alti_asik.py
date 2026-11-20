"""Montaj rehberinde çapraz cumbanın altında ana çatının aşıkları kesilmez (D-141, BK-67; 20 Kasım 2026).

Lokman, 20 Kasım 2026 11:22 UTC (85 m² rehberinin 18. adım resmine yorum): "bir önceki adım yani 17 adımda tam buraya bak ana çatıdaki
aşıklar iki baş makas arasında başladığı gibi devam edecek sonra cumba makasının aşıkları dikey olarak ana çatının aşıklarına binecek yani
iki ana çatı makası arasında aşık kesintisi yok". Önce/sonra kartı 12:20:39: "Resimdeki gibi".

Kök: liste, kart modeli ve montaj paftası ana çatının aşıklarını D-135'ten beri kalkandan kalkana sayar (`cati_prefabrik.ana_karkasi`);
rehber (`capraz.py`, `sahne.js`) aşığı ana çatının görünen yüzünde kesiyordu. Düzeltme: ana çatının cumbalı yüzünün aşığı Motor'un
karkasında (`poly_asik`); kaplama, dere ve kenarlar görünen yüzden aynen. İki ev: 85 m² katalog evi (P8501 r05, ön-sol) ve kampanyalı
80 m² 2+1 (TK-04 r08, arka-sol). Denetim: cumbanın altından yukarıdan aşağı ışın; yalnız ana çatının aşıkları sayılır (`bakis.js` › `dahil`).
Node, Playwright ve three.js 0.160.0 (`THREE_DIR`) ister; yoksa atlanır, CI'da kurulur (`dogrulama.yml`).
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from shapely.geometry import Polygon

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from araclar.paket.rehber import iz  # noqa: E402

JS = KOK / "araclar" / "paket" / "rehber"
EVLER = {"P8501": KOK / "is_emri" / "P8501_r05.json", "TK04": KOK / "testler" / "motor" / "veri" / "TK04_r08.json"}


@pytest.fixture(scope="module", params=sorted(EVLER))
def ev(request, tmp_path_factory):
    from motor import geometry as G, kart_model, prefabrik_liste as PL
    from araclar.paket.rehber import veri
    ie = json.loads(EVLER[request.param].read_text(encoding="utf-8"))
    kart = tmp_path_factory.mktemp(f"{request.param}_asik")
    kart_model.uret(copy.deepcopy(ie), kart, request.param)
    L = PL.is_emrinden(copy.deepcopy(ie))["satirlar"]
    d = veri.kur(copy.deepcopy(ie), kart, request.param, L, "KP-85" if request.param == "P8501" else "TK-04")
    G.lento_ayarla({})                                   # lento modül durumudur (BK-23): öteki testlere sızmaz
    yield {"ad": request.param, "d": d, "tmp": kart}
    G.lento_ayarla({})


def _yuz(d, k):
    return d["cati"]["yuz"][k] if "cati" in d and "yuz" in d["cati"] else d["yuz"][k]


def _yuzler(d):
    y = d["cati"]["yuz"] if "cati" in d and "yuz" in d["cati"] else d["yuz"]
    return {k: y[k] for k in ("MFL", "MFR") if k in y}


def test_asik_yuzu_cumbanin_altini_da_ortur(ev):
    """Ana çatının cumbalı yüzünün iki parçasında aşığın yüzü görünen yüzden büyük: cumbanın altındaki üçgen de içinde, dikdörtgen."""
    Y = _yuzler(ev["d"])
    assert set(Y) == {"MFL", "MFR"}, list(Y)
    for k, y in Y.items():
        gor, asik = Polygon(y["poly"]), Polygon(y["poly_asik"])
        assert asik.area > gor.area + 1000 and asik.buffer(0.5).contains(gor), k
        assert abs(asik.area - asik.minimum_rotated_rectangle.area) < 1.0, k     # cumbanın altı dahil tam dikdörtgen


def test_cumbanin_altinda_ana_cati_asigi_cizilir(ev):
    """Cumbanın altındaki üçgenin ortasından yukarıdan aşağı, eğim boyunca 2 m'lik ışın şeridi: ana çatının aşıklarına çarpar
    (düzeltmeden önce bu şerit boştu)."""
    if iz.hazir() is not None:
        pytest.skip(f"rehber denetimi: {iz.hazir()}")
    from araclar.paket.rehber import sayfa as S
    d = ev["d"]
    html = S.yaz(d, ev["tmp"] / "rehber.html").resolve()
    X = lambda x: x / 100 - d["dis"][0] / 200            # plan (cm) → dünya (m), sahne.js'teki gibi
    Z = lambda y: d["dis"][1] / 200 - y / 100
    for k, y in _yuzler(d).items():
        alt = Polygon(y["poly_asik"]).difference(Polygon(y["poly"]))
        c = alt.representative_point()
        (_x0, y0, _x1, y1) = alt.bounds
        istek = {"bas": [X(c.x - 1), 8.0, Z(y0 + 1)], "u": [0.02, 0, 0], "v": [0, 0, Z(y1 - 1) - Z(y0 + 1)], "nu": 3, "nv": 121,
                 "yon": [0, -1, 0], "dahil": "^Aşık \\(omega\\) · " + re.escape(y["ad"])}
        (ev["tmp"] / "istek.json").write_text(json.dumps(istek), encoding="utf-8")
        r = subprocess.run(["node", str(JS / "bakis.js"), str(html), str(ev["tmp"] / "istek.json"), str(ev["tmp"] / "bakis.json")],
                           capture_output=True, text=True, timeout=900)
        assert r.returncode == 0, r.stderr[-2000:]
        b = json.loads((ev["tmp"] / "bakis.json").read_text(encoding="utf-8"))
        assert b["hatalar"] == []
        vurus = sum(n for kk, n in b["ilk"].items() if kk.startswith("Aşık (omega) · "))
        assert vurus >= 3, (ev["ad"], k, b["ilk"])


def test_asik_metni(ev):
    assert "Ana çatının aşıkları cumbanın altında kesilmez, kalkandan kalkana sürer." in json.dumps(ev["d"], ensure_ascii=False)
